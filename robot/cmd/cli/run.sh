#! /bin/sh
cd ../embedded/firmata/
./compile_and_upload.sh

cd $OLDPWD
go build ./cmd/cli/main.go
sudo -s ./main
