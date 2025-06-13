## Setup Arduino
```
brew install arduino-cli
```

```
arduino-cli config init
```

Add
```
library:
    enable_unsafe_install: true
```
to the path `init` returns so we can install Firmata and the Adafruit libraries from their GitHub repos.

Run
```
arduino-cli board list
```
to find the device path for the Arduino, something that looks like `/dev/cu.usbmodem14201`

```
cd /embedded/firmata
sudo ./setup.sh
MC_PATH="the_device_path_from_above" ./compile_and_upload.sh
```

It was at this point something was not working and I used the regular Arduino IDE to compile/upload

```
brew install arduino-ide
```
and copy the `embedded/firmata/firmata.ino` into it

## Setup Python
[pyFirmata](https://github.com/tino/pyFirmata) needs to be installed from source, not pip.

After that,
```
cd robot
python -m pip install -r requirements.txt
```

## Camera
Right now I'm using the "Logitech BRIO" or "Logitech Pro 4k Webcam". It seems like the only way I can control the focus is through their G HUB software, so I manually set the focus there before running everything. Such is life until a new camera.
