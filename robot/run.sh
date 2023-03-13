#! /bin/sh

export MC_USB="/dev/ttyACM0"
#export ROOT_DIR="/home/spencer/code/nexus"
export ROOT_DIR="/nexus"

export PATH=$PATH:/usr/local/go/bin

#if $1=firmware then it compiles new firmware, otherwise just uploads what's already compiled
cd $ROOT_DIR/embedded/firmata
./compile_and_upload.sh $1

cd $ROOT_DIR
#./utils/droidcam/run_droidcam.sh

cd $ROOT_DIR/robot
python main.py
