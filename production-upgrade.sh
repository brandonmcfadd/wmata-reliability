#!/bin/sh
cd $(dirname $0)
python3 -m pip install --upgrade pip
sudo git stash
sudo git stash drop
sudo git pull
sudo chown -R brandon_brandonmcfadden_com:brandon_brandonmcfadden_com .
sudo chmod +x production-upgrade.sh
pip install -r /home/brandon_brandonmcfadden_com/wmata-reliability/requirements.txt
sudo systemctl restart wmata-reliability.service