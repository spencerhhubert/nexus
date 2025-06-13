#!/bin/bash
if [ "$1" = "firmware" ]; then
    echo "Compiling new firmware"
    sudo arduino-cli compile --fqbn arduino:avr:mega firmata.ino --verbose
fi

sudo arduino-cli upload --port $MC_PATH --fqbn arduino:avr:mega firmata.ino
