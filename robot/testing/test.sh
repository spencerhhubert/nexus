#! /bin/sh

cd ../arduino/firmata/
./compile_and_upload.sh

cd $OLDPWD

go build test.go
sudo -s ./test
