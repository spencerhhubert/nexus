#!/bin/bash
#sudo arduino-cli compile --fqbn arduino:avr:nano
sudo arduino-cli compile --fqbn arduino:avr:mega
#sudo arduino-cli upload --port /dev/ttyUSB1 --fqbn arduino:avr:nano
sudo arduino-cli upload --port /dev/ttyACM0 --fqbn arduino:avr:mega

