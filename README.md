# WebLogic server-start Changes
Do you need to automate the process to update the server-start arguments of hundreds of WebLogic Managed Servers? This is a great place to start.
I wrote this script to specifically add in the -javaagent argument with the unique path to the correct NewRelic agent jar file for each Managed 
Server in an environment of 250 Managed Servers.

For a more detailed overview, please see: <http://blog.thiele.pro/2018/07/09/Automated-Weblogic-Server-Start-Changes.html>

### Update 7/13/2018
My first attempt at the script didn't work as expected. We had to shutdown the WebLogic instances first before running the script for it to work.
I have renamed that script to be change-javaagent-viaconfigxml.py. I cloned it to a new script named change-javaagent-vianodemanager.py and tweaked 
that to work with some other files that can be edited while WebLogic is running and restarted by another team based on their own time, which was
the whole goal. :-D I also include some logic to backup the files and actually replace them with the new files that included the new arguments.

# Execution

```shell
ssh $SERVER
dzdo su -
python change-javaagent-vianodemanager.py -p sample.csv -H /u01/app/Oracle/Middleware/Oracle_Home/
```
