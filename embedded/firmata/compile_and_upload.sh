#!/bin/bash
sudo arduino-cli compile --fqbn arduino:avr:mega

if [ "$1" = "firmware" ]; then
    echo "Compiling new firmware"
    sudo arduino-cli compile --fqbn arduino:avr:mega
fi

sudo arduino-cli upload --port /dev/ttyACM0 --fqbn arduino:avr:mega

