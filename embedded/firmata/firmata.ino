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

uint16_t SevenBitToInt16(byte *bytes) {
    return (bytes[0] & 0x7F) | ((bytes[1] & 0x7F) << 7);
}
//PWM Servo Controller SysEx commands #define PWM_SERVO 0x01 //identifer for all PWM Servo commands
#define PWM_SERVO 0x01 //identifer for all PWM Servo commands
//subcommands
#define MAKE_BOARD 0x07
#define MOVE_SERVO_TO_ANGLE 0x08

//Digital Pin Controller SysEx commands
#define DIGITAL_PIN 0x03 //identifier for all digital pin commands
//subcommands  
#define SET_PIN_MODE_DIGITAL 0x01
#define WRITE_DIGITAL_PIN 0x02
#define WRITE_PWM_PIN 0x03

#define SERVOMIN  100
#define SERVOMAX  477
#define SERVO_FREQ 50

// Maximum number of PWM boards we'll support
#define MAX_PWM_BOARDS 8

// Custom implementation to replace std::map
struct PwmBoardEntry {
    byte addr;
    bool active;
    Adafruit_PWMServoDriver driver;
};

// Array of board entries instead of std::map
PwmBoardEntry pwm_boards[MAX_PWM_BOARDS];

// Initialize all board entries as inactive
void initPwmBoards() {
    for (int i = 0; i < MAX_PWM_BOARDS; i++) {
        pwm_boards[i].active = false;
    }
}

// Find a board by address, return index or -1 if not found
int findBoardIndex(byte addr) {
    for (int i = 0; i < MAX_PWM_BOARDS; i++) {
        if (pwm_boards[i].active && pwm_boards[i].addr == addr) {
            return i;
        }
    }
    return -1;
}

// Find first empty slot, return index or -1 if full
int findEmptyBoardSlot() {
    for (int i = 0; i < MAX_PWM_BOARDS; i++) {
        if (!pwm_boards[i].active) {
            return i;
        }
    }
    return -1;
}

int angleToPulse(int angle) {
  return map(angle, 0, 180, SERVOMIN, SERVOMAX);
}

void makeBoard(byte addr) {
    int idx = findBoardIndex(addr);
    if (idx >= 0) {
        // Board already exists, nothing to do
        return;
    }

    idx = findEmptyBoardSlot();
    if (idx < 0) {
        // No space for new board
        return;
    }

    pwm_boards[idx].addr = addr;
    pwm_boards[idx].active = true;
    pwm_boards[idx].driver = Adafruit_PWMServoDriver(addr);
    pwm_boards[idx].driver.begin();
    pwm_boards[idx].driver.setOscillatorFrequency(27000000);
    pwm_boards[idx].driver.setPWMFreq(SERVO_FREQ);
}

void moveServoToAngle(byte addr, byte channel, uint16_t angle) {
    int idx = findBoardIndex(addr);
    if (idx >= 0) {
        pwm_boards[idx].driver.setPWM(channel, 0, angleToPulse(angle));
    }
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

void setPinModeDigital(byte pin, byte mode) {
    char debugMsg[50];
    sprintf(debugMsg, "Pin mode: pin=%d, mode=%d", pin, mode);
    Firmata.sendString(STRING_DATA, debugMsg);
    
    pinMode(pin, mode);
}

void writeDigitalPin(byte pin, byte value) {
    char debugMsg[50];
    sprintf(debugMsg, "Digital write: pin=%d, value=%d", pin, value);
    Firmata.sendString(STRING_DATA, debugMsg);
    
    digitalWrite(pin, value);
}

void writePwmPin(byte pin, byte value) {
    char debugMsg[50];
    sprintf(debugMsg, "PWM write: pin=%d, value=%d", pin, value);
    Firmata.sendString(STRING_DATA, debugMsg);
    
    analogWrite(pin, value);
}

void parseDigitalPinCommand(byte command, byte argc, byte *argv) {
    char debugMsg[80];
    sprintf(debugMsg, "Digital cmd: %d, argc: %d", command, argc);
    Firmata.sendString(STRING_DATA, debugMsg);
    
    switch (command) {
        case SET_PIN_MODE_DIGITAL: {
            Firmata.sendString(STRING_DATA, "SET_PIN_MODE_DIGITAL");
            setPinModeDigital(argv[0], argv[1]);
            break;
        }
        case WRITE_DIGITAL_PIN: {
            Firmata.sendString(STRING_DATA, "WRITE_DIGITAL_PIN");
            writeDigitalPin(argv[0], argv[1]);
            break;
        }
        case WRITE_PWM_PIN: {
            Firmata.sendString(STRING_DATA, "WRITE_PWM_PIN");
            writePwmPin(argv[0], argv[1]);
            break;
        }
        default: {
            sprintf(debugMsg, "Unknown digital cmd: %d", command);
            Firmata.sendString(STRING_DATA, debugMsg);
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
    char debugMsg[80];
    sprintf(debugMsg, "Sysex cmd: 0x%02X, argc=%d", command, argc);
    Firmata.sendString(STRING_DATA, debugMsg);
    
    // Print argv contents for debugging
    if (argc > 0) {
        sprintf(debugMsg, "Argv[0]: %d", argv[0]);
        Firmata.sendString(STRING_DATA, debugMsg);
    }
    if (argc > 1) {
        sprintf(debugMsg, "Argv[1]: %d", argv[1]);
        Firmata.sendString(STRING_DATA, debugMsg);
    }
    if (argc > 2) {
        sprintf(debugMsg, "Argv[2]: %d", argv[2]);
        Firmata.sendString(STRING_DATA, debugMsg);
    }
    
    switch (command) {
        case PWM_SERVO:
            Firmata.sendString(STRING_DATA, "Processing PWM_SERVO");
            parsePwmServoCommand(argv[0], argc-1, argv+1);
        break;
        case DIGITAL_PIN:
            Firmata.sendString(STRING_DATA, "Processing DIGITAL_PIN");
            parseDigitalPinCommand(argv[0], argc-1, argv+1);
        break;
        default:
            sprintf(debugMsg, "Unknown sysex command: 0x%02X", command);
            Firmata.sendString(STRING_DATA, debugMsg);
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

    // Initialize our pwm_boards array
    initPwmBoards();

    Firmata.sendString(F("Setup complete. Ready for commands."));
}

void loop() {
    while(Firmata.available()) { //only runs if message in buffer
        Firmata.sendString(STRING_DATA, "Firmata command received");
        Firmata.processInput();
        if (!Firmata.isParsingMessage()) {
            break;
        }
    }
}
