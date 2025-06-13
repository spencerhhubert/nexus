#!/bin/bash

sudo arduino-cli core uninstall arduino:avr
#sudo arduino-cli core install arduino:avr@1.8.3
sudo arduino-cli core install arduino:avr

sudo arduino-cli lib install firmata
sudo arduino-cli lib install servo
sudo arduino-cli lib install "Adafruit BusIO"
sudo arduino-cli lib install --git-url https://github.com/adafruit/Adafruit-PWM-Servo-Driver-Library
#sudo arduino-cli lib install --git-url https://github.com/firmata/ConfigurableFirmata
sudo arduino-cli lib install --git-url https://github.com/spencerhhubert/ConfigurableFirmata
sudo arduino-cli lib install ArduinoSTL
#sudo arduino-cli compile --fqbn arduino:avr:nano
