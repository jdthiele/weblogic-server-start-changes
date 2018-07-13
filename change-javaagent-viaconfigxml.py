# imports
#import xml.etree.ElementTree as ET
import lxml.etree as ET
import csv
import socket
import os.path
import sys
import argparse

# handle the arguments
csv_file = ""
config_file = ""
summary_help = ("""automate the process to update the server-start arguments of hundreds of WebLogic Managed Servers.
  see https://github.com/jdthiele/weblogic-server-start-changes for more details""")
paths_help = ("""Provide the path to the csv file that contains 3 columns:
  1) hostname
  2) managed server name
  3) path to the 'javaagent'""")
config_help = ("Provide the path to the weblogic domain's config.xml file")

parser = argparse.ArgumentParser(description = summary_help)
parser.add_argument('-p', '--paths_csv', help=paths_help, nargs=1, required=True)
parser.add_argument('-c', '--config_file', help=config_help, nargs=1, required=True)
args=parser.parse_args()

# constants
wls_config = args.config_file[0]
wls_config_output = 'out.xml'
apm_agent_path = args.paths_csv[0]
print(wls_config, apm_agent_path)

#variables
correct_path = ""
current_path = ""
write_new_file = 0
hostname = socket.gethostname()

# open the csv file to check against
csv_file = csv.reader(open(apm_agent_path, "rb"), dialect='excel')
csv_list = list(csv_file)
#with open(apm_agent_path, "rb") as f1: 
#  csv_file = csv.DictReader(f1, dialect='excel')

# open and load the weblogic config.xml file
f = open(wls_config,'r+')
tree = ET.parse(f)
root = tree.getroot()
namespace="http://xmlns.oracle.com/weblogic/domain"
servers = tree.findall('.//{%s}server' % namespace)

## Loop through the managed servers we found
for server in servers:
  #print "New SERVER node detected:"
  for child in server:
    javaagent_exists = 0
    tag = child.tag
    arg = child.text
    if child.tag == "{" + namespace + "}name":
      jvmname = child.text
      print("JVM name is: %s" % (jvmname))
    #print tag, val
    if child.tag == "{" + namespace + "}server-start":
      for args in child:
        argtag = args.tag
        argval = args.text
        argval2 = str(argval).split()
        #argval2 = ET.tostring(argval).split()
        for i, arg3 in enumerate(argval2):
          arg2 = argval2[i].split(":")
          #print(arg2tag)
          if arg2[0] == '-javaagent':
            javaagent_exists = 1
            current_path = arg2[1]
            for row in csv_list:
              #print (row[1], jvmname)
              if row[0] == hostname and row[1] == jvmname:
                if row[1]:
                  correct_path = row[3]
            # compare the paths. If not matching, put the correct one in place
            if current_path != correct_path:
              arg2[1] = correct_path
              # if a change is made, write the string back into the argval variable .fromstring()
              print("changing current path %s to correct path to %s" % (current_path, arg2[1]))
              argval2[i] = ":".join(arg2)
              newargval = " ".join(argval2)
              args.text = newargval
              write_new_file = 1
            else:
              print("current path %s is ACCURATE. Yay!" % (current_path))
        # if this server doesn't have a javaagent argument, add it
        if javaagent_exists == 0:
          for row in csv_list:
            if row[0] == hostname and row[1] == jvmname:
              if row[1]:
                correct_path = row[3]
                # check if the file in correct_path exists
                if os.path.isfile(correct_path) == False:
                  print("WARNING: the file %s does NOT exist" % (correct_path))
                javaagent_arg = "-javaagent:" + correct_path
                argval2.append(javaagent_arg)
                newargval = " ".join(argval2)
                args.text = newargval
                print("New arg line is:\n" + args.text)
                write_new_file = 1

  print

if write_new_file == 1:
  tree.write(wls_config_output, pretty_print=True, encoding='UTF-8', xml_declaration=True)
  print("Wrote a new file to %s with the changes. Copy this over the existing %s" % (wls_config_output, wls_config))
elif write_new_file == 0:
  print("No need to make any changes here")

# all done!
