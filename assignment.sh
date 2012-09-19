#!/bin/bash

#Tested on Ubuntu 12.04

checkPackageInstall()
{
	dpkg-query -s $1>/dev/null 2>&1
	return "$?"
}

installPackage()
{
	apt-get -y install $1
	return "$?"
}

PHPRepo()
{
	grep "deb http://ppa.launchpad.net/ondrej/php5/ubuntu precise main" /etc/apt/sources.list | grep -v ^#
	if [ $? -ne 0 ]
	then
		echo "PHP 5.4 Repository not added."
		echo "Adding Repository"
		add-apt-repository -y ppa:ondrej/php5
		if [ $? -ne 0 ]
		then
			echo "Adding Repository Failed"
			echo "Cannot Continue. Exiting"
			exit 1
		fi
		echo "Sucessfully added Repository"
		apt-get update
	fi
}

start()
{

	if [ $EUID -ne 0 ]
	then
 		echo "Please run as root"
		exit 1
	fi
	packages=( "php5-mysql" "php5-cgi" "php5-fpm" "nginx" "mysql-server" )
	for package in "${packages[@]}"
	{
		echo "Checking $package install status"
		if [ $package == 'php5-cgi' ]
		then
			phpver=$(dpkg-query -W -f='${Version}' $package | awk '{ print substr( $0, 1, 3 ) } ')
			nothasreq=$(expr $phpver '<' 5.4)	
			if [ $nothasreq ]
			then
				PHPRepo
			fi
		fi
		checkPackageInstall $package
		if [ $? -ne 0 ]
		then
			installPackage $package
			if [ $? -ne 0 ]
			then
				echo "Installation of $package Failed"
				echo "exiting"
				exit 1
			fi			
		fi

	}
	echo "Please Enter domain"
	read dnm
	localip=$(hostname -i)
	hostchk="grep -w \"$localip\" /etc/hosts | grep \"$dnm\""
	eval $hostchk 2>&1 >/dev/null
	if [ "$?" -ne 0 ]
	then
		echo "$localip	$dnm" >> /etc/hosts
	fi
	if [ -e "/etc/nginx/sites-available/$dnm" ]
	then
		echo "Nginx Configuration for $dnm seems to be already setup."
		echo "Skipping Configuration"
	else
		echo "Creating Configuration File for $dnm"
		echo "server {
	server_name $dnm *.$dnm;
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
}" > /etc/nginx/sites-available/$dnm

	#assusmed /var/www to be the place where site document root should be placed

		ln -s /etc/nginx/sites-available/$dnm /etc/nginx/sites-enabled/
	fi
	
	if [ ! -d "/var/www/$dnm/htdocs/" ]
	then
		mkdir -p "/var/www/$dnm/htdocs/"
	fi
	
	echo "Getting the latest version of Wordpress"
	wget "http://wordpress.org/latest.zip"
	unzip "latest.zip"
	if [ $? -ne 0 ]
	then
		echo "Error in file"
		exit 1
	fi
	cp -r wordpress/* /var/www/$dnm/htdocs/
	rm -r wordpress
	echo "Deleteing Cached Download file"
	rm "latest.zip"
	echo "Setting up MySQL Database"
	echo "Please Enter the Username of an existing user for database login"
	read usrName
	echo "Please Enter the password of an existing user for database login"
	read -s pass
	#assumed examplecom_db is to be the db name always as mentioned in instructions
	#removed “.” from example.com as Database and table names cannot contain “/”, “\”, “.”
	mysql -u $usrName -p$pass -e 'create database examplecom_db'
	if [ $? -ne 0 ]
	then
		echo "Database Setup Failed"
		exit 1
	else
		echo "Database was sucessfully setup"
	fi
	echo "Configuring Wordpress"
	wget -O salt.keys https://api.wordpress.org/secret-key/1.1/salt/
	cp /var/www/$dnm/htdocs/wp-config-sample.php /var/www/$dnm/htdocs/wp-config.php
	sed -i "s/database_name_here/examplecom_db/" /var/www/$dnm/htdocs/wp-config.php
	sed -i "s/username_here/$usrName/" /var/www/$dnm/htdocs/wp-config.php
	sed -i "s/password_here/$pass/" /var/www/$dnm/htdocs/wp-config.php
	sed -i '/#@-/r salt.keys' /var/www/$dnm/htdocs/wp-config.php
	rm salt.keys
	sed -i "/#@+/,/#@-/d" /var/www/$dnm/htdocs/wp-config.php
	chown -R www-data:www-data /var/www/$dnm/
	service php5-fpm restart
	service mysql restart
	service nginx restart
	echo "Please open $dnm in browser"
}

start
