# imports
#import xml.etree.ElementTree as ET
import lxml.etree as ET
import csv
import socket
import sys
import argparse

# handle the arguments
summary_help = ("""automate the process to update the server-start arguments of hundreds of WebLogic Managed Servers.
  see https://github.com/jdthiele/weblogic-server-start-changes for more details""")
paths_help = ("""Provide the path to the csv file that contains 3 columns:
  1) hostname
  2) managed server name
  3) path to the 'javaagent'""")
config_help = ("Provide the path to the weblogic domain's config.xml file")

parser = argparse.ArgumentParser(description = summary_help)
parser.add_argument('-p', '--paths_csv', help=paths_help, nargs=1, metavar="CSV_FILE", required=True)
parser.add_argument('-c', '--config_file', help=config_help, nargs=1, metavar="CONFIG_FILE", required=True)
args=parser.parse_args()

# constants
wls_config = CONFIG_FILE
wls_config_output = 'out.xml'
apm_agent_path = CSV_FILE

#variables
correct_path = ""
current_path = ""

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
    tag = child.tag
    arg = child.text
    if child.tag == "{" + namespace + "}name":
      jvmname = child.text
      print("jvmname is: %s" % (jvmname))
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
            current_path = arg2[1]
            #get the correct path from the spreadsheet
            hostname = socket.gethostname()
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
            else:
              print("current path %s is ACCURATE. Yay!" % (current_path))
  print

tree.write(wls_config_output, pretty_print=True, encoding='UTF-8', xml_declaration=True)

# all done!
