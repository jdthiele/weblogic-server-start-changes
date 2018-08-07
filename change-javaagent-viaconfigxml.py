# -*- coding: utf-8 -*-

# imports
#import xml.etree.ElementTree as ET
import lxml.etree as ET
import csv
import socket
import os
import sys
import argparse
import datetime
import shutil
import pwd
import grp

# handle the arguments
csv_file = ""
config_file = ""
summary_help = ("""automate the process to update the server-start arguments of hundreds of WebLogic Managed Servers.
  see https://github.com/jdthiele/weblogic-server-start-changes for more details""")
paths_help = ("""Provide the path to the csv file that contains 3 columns:
  1) hostname
  2) managed server name
  3) path to the 'javaagent'""")
wlshome_help = ("Provide the path to the weblogic home base - something like /app/oracle/Oracle/Middleware/Oracle_Home/")
domhome_help = ("Provide the path to the domain home - something like /u01/oracle/fmw/")

parser = argparse.ArgumentParser(description = summary_help)
parser.add_argument('-p', '--paths_csv', help=paths_help, nargs=1, required=True)
parser.add_argument('-w', '--wls_home_path', help=wlshome_help, nargs=1, required=True)
parser.add_argument('-d', '--domain_home_path', help=domhome_help, nargs=1, required=True)
args=parser.parse_args()

# variables
hostname = socket.gethostname()


# define the files to work with
working_dir = '/var/tmp/' # this needs a trailing slash, whatever the directory is
wls_home = os.path.normpath(args.wls_home_path[0]) #normpath strips any trailing slashes for cleaner output later
dom_home = os.path.normpath(args.domain_home_path[0]) #normpath strips any trailing slashes for cleaner output later
startWebLogic_file = dom_home + "/bin/startWebLogic.sh"
policy_file = wls_home + "/wlserver/server/lib/weblogic.policy"
wls_config = dom_home + '/config/config.xml'
working_files = [wls_config, startWebLogic_file, policy_file]
apm_agent_paths_csv = args.paths_csv[0]

# open the csv file to check against
csv_file = open(apm_agent_paths_csv, "rb")
csv_reader = csv.reader(csv_file, dialect='excel')
csv_list = list(csv_reader)
csv_file.close()

#####
# config.xml
#####
def process_config_file(input_file, output_file, hostname, csv_list, overwrite_file):
  # open and load the weblogic config.xml file
  f = open(input_file,'r+')
  tree = ET.parse(f)
  root = tree.getroot()
  namespace="http://xmlns.oracle.com/weblogic/domain"
  servers = tree.findall('.//{%s}server' % namespace)
  
  # collect the list of installed servers for checking against later
  installed_apps = []

  ## handle each of the managed servers we found in the config.xml file
  for server in servers:
    #print "New SERVER node detected:"
    for child in server:
      javaagent_exists = False
      if child.tag == "{" + namespace + "}name":
        jvmname = child.text
        installed_apps.append(jvmname)
        if jvmname == "AdminServer":
          break
        print("--- %s" % (jvmname))
      #print tag, val
      if child.tag == "{" + namespace + "}server-start":
        exists_in_csv = False
        for args in child:
          argtag = args.tag
          argval = args.text
          argval2 = str(argval).split()
          #argval2 = ET.tostring(argval).split()
          for i, arg3 in enumerate(argval2):
            arg2 = argval2[i].split(":")
            #print(arg2tag)
            if arg2[0] == '-javaagent':
              javaagent_exists = True
              current_path = arg2[1]
              for row in csv_list:
                if row[0] == hostname and row[1] == jvmname:
                  correct_path = row[2]
                  if correct_path == "":
                    print("This path for this managed server is blank in the CSV spreadsheet")
                    continue
                  exists_in_csv = True
              if exists_in_csv == False:
                print("This managed server or host isn't in the CSV spreadsheet")
                print
                continue
              # compare the paths. If not matching, put the correct one in place
              if current_path != correct_path:
                arg2[1] = correct_path
                # if a change is made, write the string back into the argval variable .fromstring()
                print("changing current path %s to correct path to %s" % (current_path, arg2[1]))
                argval2[i] = ":".join(arg2)
                newargval = " ".join(argval2)
                args.text = newargval
                overwrite_file = True
              else:
                print("current path %s is ACCURATE. Yay!" % (current_path))
          # if this server doesn't have a javaagent argument, add it
          if javaagent_exists == False:
            for row in csv_list:
              if row[0] == hostname and row[1] == jvmname:
                correct_path = row[2]
                if correct_path == "":
                  print("This path for this managed server is blank in the CSV spreadsheet")
                  continue
                exists_in_csv = True
                print(correct_path)
                # check if the file in correct_path exists
                if os.path.isfile(correct_path) == False:
                  print("WARNING: the file %s does NOT exist" % (correct_path))
                javaagent_arg = "-javaagent:" + correct_path
                argval2.append(javaagent_arg)
                newargval = " ".join(argval2)
                args.text = newargval
                print("New arg line is:\n" + args.text)
                overwrite_file = True
            if exists_in_csv == False:
              print("This managed server or host isn't in the CSV spreadsheet")
              print
              continue
    print
  
  # check that all of the installed servers exist in the csv spreadsheet and vice versa
  csv_apps = []
  for row in csv_list:
    if row[0] == hostname:
      csv_apps.append(row[1])
  for app in installed_apps:
    if app not in csv_apps:
      print("%s is not in the CSV file, but is installed on the host" % (app))
  for app in csv_apps:
    if app not in installed_apps:
      print("%s is not installed on this host, but is in the spreadsheet" % (app))


  # if we made changes to the startWebLogic.sh file, backup the orig and copy the new temp file over it
  if overwrite_file == True:
    tree.write(output_file, pretty_print=True, encoding='UTF-8', xml_declaration=True)
  f.close()

  return overwrite_file
  # end function


######
# startWebLogic_file
######

def process_startWebLogic_file(input_file, output_file, hostname, csv_list, overwrite_file):
  line_search = "export JAVA_OPTIONS="
  arg_search = '-javaagent'
  arg_join = ':'
  java_arghead = '-javaagent:'
  line_end = '"'
  overwrite_file = False
  managed_server = "AdminServer"
  print("---AdminServer")
  if os.path.isfile(input_file) == False:
    print("I can't find " + input_file)
    print
    sys.exit()
  # open input_file
  with open(input_file) as old_file:
    # get the contents
    oldfile_contents = ""
    oldfile_contents = old_file.readlines()
    # open the new_file
    new_file = open(output_file, 'w')
    # define some variables that reset in each managed server loop
    argline_exists = False
    exists_in_csv = False
    javaagent_exists = False
    new_line = ""
    newargs = ""
    correct_path = ""
    current_path = ""
    args = []
    arg2 = []
    i = 0
    # rewind old_file for parsing per line
    old_file.seek(0)
    for line in old_file:
      if line.startswith(line_search):
        argline_exists = True
        args = line.replace(line_search,"").split()
        args_count = len(args)
        args_count -= 1
        for i, arg in enumerate(args):
          arg2 = args[i].split(":")
          # if the javaagent argument exists, do the following
          if arg2[0] == arg_search:
            javaagent_exists = True
            current_path = arg2[1]
            # remove a trailing double quote that is often there in the startWebLogic.sh file
            if current_path.endswith('"'):
              current_path = current_path[:-1]
            for row in csv_list:
              #print (row[1], jvmname)
              if row[0] == hostname and row[1] == managed_server:
                exists_in_csv = True
                correct_path = row[2]
            if exists_in_csv == False:
              print("The AdminServer or host isn't in the CSV spreadsheet")
              print
              break
            # compare the paths. If not matching, put the correct one in place
            if current_path != correct_path:
              arg2[1] = correct_path
              # if a change is made, write the string back into the argval variable .fromstring()
              print("changing current path %s to correct path to %s" % (current_path, arg2[1]))
              args[i] = arg_join.join(arg2)
              newargs = " ".join(args)
              # if this is not the last arg in the args list, ensure a double quote is not appended (as often needed for AdminServer)
              if i != args_count:
                line_end = ""
              new_line = line_search + newargs + line_end
              print("New arg line is:\n" + new_line)
              new_file.write(new_line + "\n")
              overwrite_file = True
            else:
              print("current path %s is ACCURATE. Yay!" % (current_path))
        # if this server doesn't have a javaagent argument, add it
        if javaagent_exists == False:
          exists_in_csv = False
          for row in csv_list:
            if row[0] == hostname and row[1] == managed_server:
              if row[1]:
                exists_in_csv = True
                correct_path = row[2]
                # check if the file in correct_path exists
                if os.path.isfile(correct_path) == False:
                  print("WARNING: the agent file %s does NOT exist" % (correct_path))
                  continue
          if exists_in_csv == False:
            print("This managed server or host isn't in the CSV spreadsheet")
            print
            continue
          # remove the trailing double quote from last existing arg so we can append the newarg that will include a new ending double quote
          args_count -= 1
          if args[args_count].endswith('"'):
            args[args_count] = args[args_count][1:-1]
          # put it all back together
          javaagent_arg = java_arghead + correct_path
          args.append(javaagent_arg)
          newargs = " ".join(args)
          new_line = line_search + newargs + line_end
          print("New arg line is:\n" + new_line)
          new_file.write(new_line + "\n")
          overwrite_file = True
      # if not dealing with one of the main working lines, just write the line out so properly populate the new file with the pre-existing data
      else:
        new_file.write(line)
    # if the argument line doesn't exist, add it
    if argline_exists == False:
      for row in csv_list:
        if row[0] == hostname and row[1] == managed_server:
          if row[1]:
            exists_in_csv = True
            correct_path = row[2]
            if correct_path == "":
              print("This path for this managed server is blank in the CSV spreadsheet")
              continue
            # check if the file in correct_path exists
            if os.path.isfile(correct_path) == False:
              print("WARNING: the file %s does NOT exist" % (correct_path))
              continue
      if exists_in_csv == False:
        print("This managed server or host isn't in the CSV spreadsheet")
        print
      javaagent_arg = java_arghead + correct_path
      args.append(javaagent_arg)
      newargs = " ".join(args)
      new_line = line_search + '"' + newargs + '"'
      print("New arg line is:\n" + new_line)
      for i, line in enumerate(oldfile_contents):
        if line.startswith("DOMAIN_HOME="):
          line_num = i 
          line_num += 1 
      oldfile_contents.insert(line_num, new_line + "\n")
      oldfile_contents = "".join(oldfile_contents)
      # wipe out the output_file
      new_file.seek(0)
      new_file.write(oldfile_contents)
      overwrite_file = True
  
    new_file.close()
    print
    return overwrite_file
  # end function


######
# Policy File
######
def process_policy_file(input_file, output_file, hostname, csv_list, overwrite_file):
  print("---policy file")
  #get all of the new paths into a list so we can add them to the policy file
  new_javaagent_paths = []
  for row in csv_list:
    if row[0] == hostname:
      new_javaagent_paths.append(row[2])
  
  # open the policy file
  pol_file = open(input_file, "rb")
  new_pol_file = open(output_file, "w")
  
  # work on the policy file if a correct_path was found above
  for correct_path in new_javaagent_paths:
    # define some variables
    correct_path_dir = os.path.dirname(correct_path)
    policy_entry = 'grant codeBase "file:' + correct_path_dir + '/-" {\n  permission java.security.AllPermission;\n};\n'
    search_pol = 'grant codeBase "file:' + correct_path_dir + '/-" {\n'
    search_pol_old = 'grant codeBase "file:/files/relic/' + hostname
    pol_line_exists = False
    pol_old_line_exists = False
    write_pol_lines_once = False
    # rewind the policy file
    pol_file.seek(0)
    for line in pol_file:
      # check if we need to do anything
      if line == search_pol:
        pol_line_exists = True
        print('the entry in the policy file for %s exists already - yay!' % (correct_path_dir))
        # don't need to continue through the loop, so break
        break
  
      # check if the old path entry exists and replace it if so
      elif line == search_pol_old:
        pol_old_line_exists = True
        #write the new line instead of the 
        new_pol_file.write(search_pol)
        print("Replaced the old path in the policy file\nNew policy file: " + policy_file_new)
        overwrite_file = True
  
      # write the other remaining lines to the new file for swapping out
      else:
        # only do this once
        if write_pol_lines_once == False:
          new_pol_file.write(line)
  
    # change the write_pol_lines_once flag to true so we don't write the existing file a bunch of times
    write_pol_lines_once = True
  
    # if the exact line and the old line don't exist in pol_file, append the entry to the new policy file
    if pol_line_exists == False and pol_old_line_exists == False:
      # add new entry
      new_pol_file.write(policy_entry)
      print("Added a new entry to the policy file\nNew file: " + output_file)
      overwrite_file = True
  new_pol_file.close()
  print
  return overwrite_file


def place_new_file(input_file, output_file):
  # define the default backup file name
  bkup_file = input_file + ".orig"
  # get the uid and gid numbers for oracle:dba
  uid = pwd.getpwnam("oracle").pw_uid
  gid = grp.getgrnam("dba").gr_gid
  # if the .orig file doesn't exist, backup to there
  if os.path.isfile(bkup_file) == False:
    shutil.copy2(input_file, bkup_file)
    os.chown(bkup_file, uid, gid)
    print("created backup: " + bkup_file)
  # else backup to the timestamped file
  else:
    bkup_file = input_file + "." + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copy2(input_file, bkup_file)
    os.chown(bkup_file, uid, gid)
    print("created backup: " + bkup_file)
  # copy the new file over the old file
  shutil.copy2(output_file, input_file)
  os.chown(output_file, uid, gid)
  os.chown(input_file, uid, gid)
  # make the new startweblogic script executable
  if input_file.endswith('.sh'):
    os.chmod(input_file, 0754)
  print("copied the new file over " + input_file)
  print


#####
# Main
#####
# loop through each of the files we need to work on
for input_file in working_files:
  # define the temp file to make changes in
  output_file = working_dir + os.path.basename(input_file)
  overwrite_file = False
  # remove any pre-existing temp files
  if os.path.isfile(output_file):
    os.remove(output_file)
  # do the unique steps for config.xml
  if input_file.endswith("config.xml"):
    overwrite_file2 = process_config_file(input_file, output_file, hostname, csv_list, overwrite_file)
  # do the unique steps for startWeblogic.sh
  if input_file.endswith("startWebLogic.sh"):
    overwrite_file2 = process_startWebLogic_file(input_file, output_file, hostname, csv_list, overwrite_file)
  # do the unique steps for weblogic.policy
  if input_file.endswith("weblogic.policy"):
    overwrite_file2 = process_policy_file(input_file, output_file, hostname, csv_list, overwrite_file)
  # backup the existing file and overwrite it with the new one
  if overwrite_file2 == True:
    print("overwriting files")
    place_new_file(input_file, output_file)

# all done!
