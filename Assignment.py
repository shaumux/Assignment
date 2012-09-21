#! /usr/bin/env python

import apt
import os,sys
import socket
import urllib2
import zipfile
import shutil
import getpass
import subprocess
import re
import grp
import pwd

def sanitycheck():
    if not os.getuid()== 0:
        sys.exit('Script must be run as root')

def chkPackageInstStatus(cache,packageName):
    return cache[packageName].is_installed

def installPackage(cache,packageName):
    pkg = cache[packageName]
    print packageName,' is trusted:', pkg.candidate.origins[0].trusted
    pkg.mark_install()
    print packageName,' is marked for install:', pkg.marked_install
    print packageName,' is (summary):', pkg.candidate.summary
    cache.commit()
    
def updateSourcesList():
    with open("/etc/apt/sources.list.d/ondrej-php5-precise.list", "w") as php5Source:
        php5Source.write("deb http://ppa.launchpad.net/ondrej/php5/ubuntu precise main")
        php5Source.write("deb-src http://ppa.launchpad.net/ondrej/php5/ubuntu precise main")
                    
def updateCache(cache):
    cache.update()
    cache.open(None)
    cache.commit(apt.progress.TextFetchProgress(),apt.progress.InstallProgress())
    return cache

def domainConf(dmn):
    localip=socket.gethostbyname(socket.gethostname())
    with open("/etc/hosts", "r") as hosts:
        domains=hosts.readlines()
    for domain in domains:
        if dmn in domain:
            print "Domain Seems to be already configure\nProceeding"
            configured=True
            break
        else:
            configured=False
    
    if not configured:
        with open("/etc/hosts", "w") as hosts:
            hosts.write("%s %s"%(localip,dmn))
    os.symlink("/etc/nginx/sites-available/"+dmn, "/etc/nginx/sites-enabled/")
    
    
def nginxConf(dmn):
    if not os.path.exists("/etc/nginx/sites-available/%s"%dmn):
        with open("/etc/nginx/sites-available/%s"%dmn, "w") as conf:
            conf.write("""server {
    server_name %s *.%s;
    access_log   /var/log/nginx/$dnm.access.log;
    error_log    /var/log/nginx/$dnm.error.log;

    index index.php;
        root /var/www/$dnm/htdocs;
        

        location / {
                try_files \$uri \$uri/ /index.php?\$args; 
        }

        location ~ \.php$ {
                include fastcgi_params;
        fastcgi_pass 127.0.0.1:9000;
        }
}"""%(dmn,dmn))

def wpconf(dmn):
    if not os.path.exists("/var/www/"+dmn+"/htdocs/"):
        os.makedirs("/var/www/"+dmn+"/htdocs/",0755)
    print "Fetching latest version of Wordprerss"
    f = urllib2.urlopen("http://wordpress.org/latest.zip")
    with open("latest.zip", "wb") as code:
        code.write(f.read())
    zipfile.ZipFile.extractall("/var/www/"+dmn+"/htdocs/")
    shutil.move("/var/www/"+dmn+"/htdocs/wordpress", "/var/www/"+dmn+"/htdocs/")
    uname=raw_input("Please Enter the Username of an existing user for database login")
    password=getpass.getpass(prompt="Please Enter the password of an existing user for database login")    
    p = subprocess.Popen(['mysql', '-u', uname, '-p'+password, '-e \'create database examplecom_db\''], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err =p.communicate
    print out
    print err
    #shutil.copy("/var/www/"+dmn+"/htdocs/wp-config-sample.php", "/var/www/"+dmn+"/htdocs/wp-config.php")
    salt = urllib2.urlopen("https://api.wordpress.org/secret-key/1.1/salt/")
    with open("/var/www/"+dmn+"/htdocs/wp-config-sample.php", "r") as sample:
        lines = sample.readlines()
        with open("/var/www/"+dmn+"/htdocs/wp-config.php", "w") as config:
            for line in lines:
                config.write(re.sub(r'database_name_here', 'examplecom_db', line))
                config.write(re.sub(r'username_here', uname, line))
                config.write(re.sub(r'password_here', password, line))
                config.write(re.sub(r'#@+.*?#@-', salt.read(), line,flags=re.DOTALL))
    for root, dirs, files in os.walk("/var/www/"+dmn):
        for momo in dirs:
            os.chown(os.path.join(root, momo), pwd.getpwnam("www-data")[3], grp.getgrnam("www-data"))
        for momo in files:
            os.chown(os.path.join(root, momo), pwd.getpwnam("www-data")[3], grp.getgrnam("www-data"))
            
def restart(service):
    p = subprocess.Popen(['service', 'restart', service], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err =p.communicate
    print out
    print err


def main():
    sanitycheck()
    print
    cache=apt.Cache()
    dmn=raw_input("Please Enter Domain Name:")
    reqPackages=("php5-cgi","php5-mysql","php5-fpm","nginx","mysql-server")
    for version in cache["php5-cgi"].versions:
        if version.version.split("-")[0]>="5.4":
            hasslistver=True;
        else:
            hasslistver=False;
    if hasslistver == False:
        updateSourcesList()
        cache=updateCache()
        
    for package in reqPackages:
        print "Checking Package Install Status:"
        if chkPackageInstStatus(cache,package):
            installPackage(cache,package)
    domainConf(dmn)
    nginxConf()
    wpconf(dmn)
    restart("php5-fpm")
    restart("mysql")
    restart("nginx")
    print "Open %s in your Browser"%dmn
    
    
if __name__ == "__main__":
    main()
    