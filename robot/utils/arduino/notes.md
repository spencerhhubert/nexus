## installing arduino-cli
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
mv where/it/is/arduino-cli /usr/local/bin/

## installing firmata
`get https://github.com/firmata/arduino`
cd into it

run everything as root because upload has to access libraries that will get stored in a user dir:
```
arduino-cli lib install servo
arduino-cli lib install fermata
arduino-cli core install arduino:avr:nano

arduino-cli compile --fqbn arduino:avr:nano examples/StandardFirmata/
```
get the board /dev id:
`arduino-cli board list`

`arduino-cli upload --port /dev/{id} --fqbn arduino:avr:nano examples/StandardFirmata/`
