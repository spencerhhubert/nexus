#define ARDUINO_AVR_MEGA2560


#include <ConfigurableFirmata.h>
#include <DigitalInputFirmata.h>
DigitalInputFirmata digitalInput;
#include <DigitalOutputFirmata.h>
DigitalOutputFirmata digitalOutput;
#include <AnalogInputFirmata.h>
AnalogInputFirmata analogInput;
#include <AnalogOutputFirmata.h>
AnalogOutputFirmata analogOutput;
#include <Wire.h>
#include <I2CFirmata.h>
I2CFirmata i2c;
#include <Wire.h>
#include <SpiFirmata.h>
#include <SerialFirmata.h>
SerialFirmata serial;

//what is this
#include <FirmataExt.h>
FirmataExt firmataExt;

#include <stdint.h>
#include <math.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <stdarg.h>
#include <ArduinoSTL.h>
#include <map>

#include <AccelStepper.h>

uint16_t SevenBitToInt16(byte *bytes) {
    return (bytes[0] & 0x7F) | ((bytes[1] & 0x7F) << 7);
}
//PWM Servo Controller SysEx commands #define PWM_SERVO 0x01 //identifer for all PWM Servo commands
#define PWM_SERVO 0x01 //identifer for all PWM Servo commands
//subcommands
#define MAKE_BOARD 0x07
#define MOVE_SERVO_TO_ANGLE 0x08

#define SERVOMIN  100
#define SERVOMAX  477
#define SERVO_FREQ 50

//there are probably mutliple boards, eached addressed by a byte. the default for the first board is 0x40 and they go up from there
std::map<byte, Adafruit_PWMServoDriver> pwm_boards;

int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void makeBoard(byte addr) {
    pwm_boards[addr] = Adafruit_PWMServoDriver(addr);
    pwm_boards[addr].begin();
    pwm_boards[addr].setOscillatorFrequency(27000000);
    pwm_boards[addr].setPWMFreq(SERVO_FREQ);
}

void moveServoToAngle(byte addr, byte channel, uint16_t angle) {
    pwm_boards[addr].setPWM(channel, 0, angleToPulse(angle));
}

void parsePwmServoCommand(byte command, byte argc, byte *argv) {
    switch (command) {
        case MAKE_BOARD: {
            makeBoard(argv[0]);
            break;
        }
        case MOVE_SERVO_TO_ANGLE: {
            moveServoToAngle(argv[0], argv[1], SevenBitToInt16(argv + 2));
            break;
        }
    }
}

#define STEPPER_COMMAND 0x02
#define MAKE_STEPPER 0x01
#define RUN_STEPPER 0x02
#define STOP_STEPPER 0x03

std::map<byte, AccelStepper> steppers;

void makeStepper(byte id, int dir_pin, int step_pin, int steps_per_rev) {
    Firmata.sendString(F("Making stepper with id:"), id);
    Firmata.sendString(F("Direction pin:"), dir_pin);
    Firmata.sendString(F("Step pin:"), step_pin);
    steppers[id] = AccelStepper(AccelStepper::DRIVER, step_pin, dir_pin);
}

void runStepper(byte id, int speed) {
    Firmata.sendString(F("Running stepper at constant speed:"), speed);
    speed = 3000;
    steppers[id].setMaxSpeed(speed);
    steppers[id].setAcceleration(1000);
    steppers[id].setSpeed(speed);
}

void stopStepper(byte id) {
    steppers[id].stop();
    steppers[id].setSpeed(0);
}

void updateSteppers() {
    if (steppers.size() == 0) {
        return;
    }
    for (int i = 0; i < steppers.size(); i++) {
        Firmata.sendString(F("Running stepper:"), i);
        steppers[i].runSpeed();
    }
}



void parseStepperCommand(byte command, byte argc, byte *argv) {
    switch (command) {
        case MAKE_STEPPER: {
            makeStepper(argv[0], argv[1], argv[2], SevenBitToInt16(argv + 3));
            break;
        }
        case RUN_STEPPER: {
            runStepper(argv[0], SevenBitToInt16(argv + 1));
            break;
        }
        case STOP_STEPPER: {
            stopStepper(argv[0]);
            break;
        }
    }
}

void systemResetCallback() {
    for (byte i = 0; i < TOTAL_PINS; i++) {
        if (IS_PIN_ANALOG(i)) {
            Firmata.setPinMode(i, PIN_MODE_ANALOG);
        } else if (IS_PIN_DIGITAL(i)) {
            Firmata.setPinMode(i, PIN_MODE_OUTPUT);
        }
    }
    firmataExt.reset();
}

void sysexCallback(byte command, byte argc, byte *argv) {
    Firmata.sendString(F("Parsing a sysex command"));
    switch (command) {
        case PWM_SERVO:
            parsePwmServoCommand(argv[0], argc-1, argv+1);
        case STEPPER_COMMAND:
            parseStepperCommand(argv[0], argc-1, argv+1);
            break;
        break;
    }
}

void initFirmata() {
    Firmata.setFirmwareNameAndVersion("ConfigurableFirmata", FIRMATA_FIRMWARE_MAJOR_VERSION, FIRMATA_FIRMWARE_MINOR_VERSION);
    firmataExt.addFeature(digitalInput);
    firmataExt.addFeature(digitalOutput);
    firmataExt.addFeature(analogInput);
    firmataExt.addFeature(analogOutput);
    firmataExt.addFeature(i2c);
    firmataExt.addFeature(serial);
    Firmata.attach(SYSTEM_RESET, systemResetCallback);
    Firmata.attach(START_SYSEX, sysexCallback);
}

void setup() {
    Firmata.begin(57600);
	Firmata.sendString(F("Booting device. Stand by..."));
	initFirmata();
	Firmata.parse(SYSTEM_RESET);
}

void loop() {
    while(Firmata.available()) { //only runs if message in buffer
        Firmata.processInput();
        if (!Firmata.isParsingMessage()) {
            break;
        }
    }
    updateSteppers();
}
