#! /bin/sh
cd firmata/
./compile_and_upload.sh
cd $OLDPWD

go build .
sudo -s ./robot
