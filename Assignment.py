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
    print '%s is trusted:%s'%(packageName,pkg.candidate.origins[0].trusted)
    pkg.mark_install()
    print '%s is marked for install:%s'%(packageName,pkg.marked_install)
    print '%s is %s:'%(packageName, pkg.candidate.summary)

    
def updateSourcesList():
    with open("/etc/apt/sources.list.d/ondrej-php5-precise.list", "w") as php5Source:
        php5Source.write("deb http://ppa.launchpad.net/ondrej/php5/ubuntu precise main\n")
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
        with open("/etc/hosts", "a") as hosts:
            hosts.write("%s %s"%(localip,dmn))
    
    
    
def nginxConf(dmn):
    if not os.path.exists("/etc/nginx/sites-available/%s"%dmn):
        with open("/etc/nginx/sites-available/%s"%(dmn), "w") as conf:
            conf.write("""server{
	server_name %s *.%s;
	access_log   /var/log/nginx/%s.access.log;
	error_log    /var/log/nginx/%s.error.log;

	index index.php;
        root /var/www/%s/htdocs;
        

        location / {
                try_files \$uri \$uri/ /index.php?\$args; 
        }

        location ~ \.php$ {
                include fastcgi_params;
		#fastcgi_pass unix:/var/run/php5-fpm.sock;
		fastcgi_pass 127.0.0.1:9000
        }
}"""%(dmn,dmn,dmn,dmn,dmn))
	os.symlink("/etc/nginx/sites-available/%s"%dmn, "/etc/nginx/sites-enabled/%s"%dmn)

def wpconf(dmn):
    print "Fetching latest version of Wordprerss"
    f = urllib2.urlopen("http://wordpress.org/latest.zip")
    with open("latest.zip", "wb") as code:
        code.write(f.read())
    zf=zipfile.ZipFile("latest.zip")
    zf.extractall("/var/www/%s/"%dmn)
    shutil.copytree("/var/www/%s/wordpress"%dmn, "/var/www/%s/htdocs/"%dmn)
    shutil.rmtree("/var/www/%s/wordpress"%dmn)
    uname=raw_input("Please Enter the Username of an existing user for database login:")
    password=getpass.getpass(prompt="Please Enter the password of an existing user for database login:")
    os.system("mysql -u %s -p%s -e 'create database examplecom_db'"%(uname,password))
    salt = urllib2.urlopen("https://api.wordpress.org/secret-key/1.1/salt/")
    with open("/var/www/"+dmn+"/htdocs/wp-config-sample.php", "r") as sample:
        lines = sample.readlines()
        with open("/var/www/"+dmn+"/htdocs/wp-config.php", "w") as config:
            for line in lines:
                config.write(re.sub(r'database_name_here', 'examplecom_db', line))
    with open("/var/www/%s/htdocs/wp-config.php"%dmn, "r") as config:
	lines = config.readlines()
    	with open("/var/www/%s/htdocs/wp-config.php"%dmn, "w") as config:
            for line in lines:
	        config.write(re.sub(r'username_here', uname, line))
    with open("/var/www/%s/htdocs/wp-config.php"%dmn, "r") as config:
	lines = config.readlines()
    	with open("/var/www/%s/htdocs/wp-config.php"%dmn, "w") as config:
	    for line in lines:
                config.write(re.sub(r'password_here', password, line))
    with open("/var/www/%s/htdocs/wp-config.php"%dmn, "r") as config:
	block = config.read()
        with open("/var/www/%s/htdocs/wp-config.php"%dmn, "w") as config:
                config.write(re.sub(r'/\*\*\#@\+.*?\#@-\*/', salt.read(), block,flags=re.DOTALL))
    os.system("chown -R www-data:www-data /var/www/%s"%dmn)
            
def restart(service):
    p = subprocess.Popen(['service', service, 'restart'], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err =p.communicate()
    print out
    print err


def main():
    sanitycheck()
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
        cache=updateCache(cache)
        
    for package in reqPackages:
        print "Checking %s Install Status:"%package
        if not chkPackageInstStatus(cache,package):
            installPackage(cache,package)
    cache.commit()
    domainConf(dmn)
    nginxConf(dmn)
    wpconf(dmn)
    restart("php5-fpm")
    restart("mysql")
    restart("nginx")
    print "Open %s in your Browser"%dmn
    
    
if __name__ == "__main__":
    main()
    
