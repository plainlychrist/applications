#!/usr/bin/env bash

echo "This is dangerous ... this will completely blow away your entire Docker installation"
echo "And this only works on Ubuntu, Debian or Amazon Linux!!!"
read -p "Do you wish to erase Docker entirely, and re-install? " yesorno
if [[ ! "$yesorno" = "y" ]]; then
  exit 1
fi

set -x

sudo /etc/init.d/docker stop
sudo yum erase docker
sudo mv /var/lib/docker/ /var/lib/docker.DELETE.$(date +%s)
sudo yum install docker
sudo /etc/init.d/docker start
sudo rm -rf /var/lib/docker.DELETE.*
