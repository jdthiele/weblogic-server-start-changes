# imports
#import xml.etree.ElementTree as ET
import csv
import socket
import os
import sys
import argparse
import datetime
import shutil

# handle the arguments
csv_file = ""
config_file = ""
summary_help = ("""automate the process to update the server-start arguments of hundreds of WebLogic Managed Servers.
  see https://github.com/jdthiele/weblogic-server-start-changes for more details""")
paths_help = ("""Provide the path to the csv file that contains 3 columns:
  1) hostname
  2) managed server name
  3) path to the 'javaagent'""")
home_help = ("Provide the path to the weblogic home base - something like /app/oracle/Oracle/Middleware/Oracle_Home/")

parser = argparse.ArgumentParser(description = summary_help)
parser.add_argument('-p', '--paths_csv', help=paths_help, nargs=1, required=True)
parser.add_argument('-H', '--home_path', help=home_help, nargs=1, required=True)
args=parser.parse_args()

# constants
wls_home = os.path.normpath(args.home_path[0]) #normpath strips any trailing slashes for cleaner output later
apm_agent_path = args.paths_csv[0]
#print(wls_config, apm_agent_path)

#variables
overwrite_file = False
hostname = socket.gethostname()

# open the csv file to check against
csv_file = open(apm_agent_path, "rb")
csv_reader = csv.reader(csv_file, dialect='excel')
csv_list = list(csv_reader)

# find all the managed servers in wls_home/user_projects/domains/base_domain/servers minus AdminServer and domain_bak
managed_servers = os.listdir(wls_home + "/user_projects/domains/base_domain/servers")
#managed_servers.remove("AdminServer")
managed_servers.remove("domain_bak")

# define the files to work with
startWebLogic_file = wls_home + "/user_projects/domains/base_domain/bin/startWebLogic.sh"

# for each managed server, go do some stuff
for managed_server in managed_servers:
  print(managed_server)
  # set some unique variables conditionally based on which managed server we're looking at
  if managed_server == "AdminServer":
    input_file = startWebLogic_file
    line_search = "export JAVA_OPTIONS="
    arg_search = '-javaagent'
    arg_join = ':'
    java_arghead = '-javaagent:'
    line_end = '"'
  else:
    startup_prop_file = wls_home + "/user_projects/domains/base_domain/servers/" + managed_server + "/data/nodemanager/startup.properties"
    input_file = startup_prop_file
    line_search = "Arguments="
    arg_search = '-javaagent\\'
    arg_join = '\:'
    java_arghead = '-javaagent\:'
    line_end = ''
  bkup_file = input_file + ".orig"
  output_file = input_file + ".new"
  # open the input_file and start parsing
  if os.path.isfile(input_file) == False:
    print("this managed server doesn't have a startup.properties file")
    print
    continue
  # remove any existing "new" files from previous executions
  if os.path.isfile(output_file):
    os.remove(output_file)
  #open startup.properties
  with open(input_file) as old_file:
    # get the contents for unique handling by AdminServer missing an argline
    oldfile_contents = ""
    oldfile_contents = old_file.readlines()
    # open the new_file
    new_file = open(output_file, 'w')
    # define some variables that reset in each managed server loop
    argline_exists = False
    exists_in_csv = False
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
        javaagent_exists = 0
        args = line.replace(line_search,"").split()
        args_count = len(args)
        for i, arg in enumerate(args):
          arg2 = args[i].split(":")
          # if the javaagent argument exists, do the following
          if arg2[0] == arg_search:
            javaagent_exists = 1
            current_path = arg2[1]
            # remove a trailing double quote that is often there in the startWebLogic.sh file
            if current_path.endswith('"'):
              current_path = current_path[1:-1]
              print(current_path)
            for row in csv_list:
              #print (row[1], jvmname)
              if row[0] == hostname and row[1] == managed_server:
                exists_in_csv = True
                correct_path = row[2]
            if exists_in_csv == False:
              print("This managed server or host isn't in the CSV spreadsheet")
              print
              continue
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
        if javaagent_exists == 0:
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
        continue
      javaagent_arg = java_arghead + correct_path
      args.append(javaagent_arg)
      newargs = " ".join(args)
      if managed_server == "AdminServer":
        new_line = line_search + '"' + newargs + '"'
        print("New arg line is:\n" + new_line)
        #old_file.seek(0)
        #for i, line in enumerate(old_file):
        for i, line in enumerate(oldfile_contents):
          if line.startswith("DOMAIN_HOME="):
            line_num = i 
            line_num += 1 
        oldfile_contents.insert(line_num, new_line + "\n")
        oldfile_contents = "".join(oldfile_contents)
        # wipe out the output_file
        new_file.seek(0)
        new_file.write(oldfile_contents)
      else:
        new_line = line_search + newargs
        print("New arg line is:\n" + new_line)
        new_file.write(new_line + "\n")
      overwrite_file = True

    new_file.close()
  old_file.close()

  #'''
  # if we made changes move the files around
  if overwrite_file == True:
    #backup the original file
    if os.path.isfile(bkup_file) == False:
      shutil.copy2(input_file, bkup_file)
      print("created backup: " + bkup_file)
    else:
      bkup_file = input_file + "." + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
      shutil.copy2(input_file, bkup_file)
      print("created backup: " + bkup_file)
    #copy the new file over the old file
    shutil.copy2(output_file, input_file)
    print("copied the new file over " + input_file)
  #'''

  print

#close the opened files
csv_file.close()

# all done!