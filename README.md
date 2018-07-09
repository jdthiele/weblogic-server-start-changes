# WebLogic server-start Changes
Do you need to automate the process to update the server-start arguments of hundreds of WebLogic Managed Servers? This is a great place to start.
I wrote this script to specifically add in the -javaagent argument with the unique path to the correct NewRelic agent jar file for each Managed 
Server in an environment of 250 Managed Servers.

For a more detailed overview, please see: <http://blog.thiele.pro/2018/07/09/Automated-Weblogic-Server-Start-Changes.html>

# Execution

```shell
ssh $SERVER
dzdo su -
cd /tmp
wget https://github.com/jdthiele/blob/master/change-server-start-weblogic.py
wget https://github.com/jdthiele/blob/master/sample.csv
cp ${WLS_HOME}/user_projects/domains/base_domain/config/config.xml .
python change-server-start-weblogic.py -c ./config.xml -p ./sample.csv
cp ${WLS_HOME}/user_projects/domains/base_domain/config/config.xml ${WLS_HOME}/user_projects/domains/base_domain/config/config.xml.bkup
cp out.xml /app/oracle/Oracle/Middleware/Oracle_Home/user_projects/domains/base_domain/config/config.xml
```
