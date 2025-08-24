#define ARDUINO_AVR_MEGA2560

// Debug level - 0 = no debug, 1+ = debug prints
int DEBUG_LEVEL = 1;

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
#define TURN_OFF_SERVO 0x09

//Digital Pin Controller SysEx commands
#define DIGITAL_PIN 0x03 //identifier for all digital pin commands
//subcommands
#define SET_PIN_MODE_DIGITAL 0x01
#define WRITE_DIGITAL_PIN 0x02
#define WRITE_PWM_PIN 0x03

//Encoder SysEx commands
#define ENCODER 0x50 //identifier for all encoder commands
//subcommands
#define ENCODER_SETUP 0x01
#define ENCODER_READ 0x02
#define ENCODER_RESET 0x03

//Break Beam Sensor SysEx commands
#define BREAK_BEAM 0x60 //identifier for all break beam sensor commands
//subcommands
#define BREAK_BEAM_SETUP 0x01
#define BREAK_BEAM_QUERY 0x02

#define SERVOMIN  100
#define SERVOMAX  477
#define SERVO_FREQ 50

// Servo timeout settings
#define SERVO_HOLD_TIME_MS 2000  // Hold position for 2 seconds then turn off
#define MAX_ACTIVE_SERVOS 32     // Maximum number of servos we can track

// Maximum number of PWM boards we'll support
#define MAX_PWM_BOARDS 8

// Motor control pins - automatically disabled when break beam is triggered
// This is done in firmware to reduce latency since serial communication is too slow
#define FIRST_VIBRATION_HOPPER_ENABLE_PIN 3
#define FIRST_VIBRATION_HOPPER_INPUT1_PIN 22
#define FIRST_VIBRATION_HOPPER_INPUT2_PIN 24
#define SECOND_VIBRATION_HOPPER_ENABLE_PIN 6
#define SECOND_VIBRATION_HOPPER_INPUT1_PIN 30
#define SECOND_VIBRATION_HOPPER_INPUT2_PIN 32
#define MAIN_CONVEYOR_ENABLE_PIN 5      // Defined for consistency but NOT auto-disabled by break beam
#define MAIN_CONVEYOR_INPUT1_PIN 26     // Defined for consistency but NOT auto-disabled by break beam
#define MAIN_CONVEYOR_INPUT2_PIN 28     // Defined for consistency but NOT auto-disabled by break beam
#define FEEDER_CONVEYOR_ENABLE_PIN 9
#define FEEDER_CONVEYOR_INPUT1_PIN 34
#define FEEDER_CONVEYOR_INPUT2_PIN 36

// Custom implementation to replace std::map
struct PwmBoardEntry {
    byte addr;
    bool active;
    Adafruit_PWMServoDriver driver;
};

// Servo timeout tracking
struct ServoTimeout {
    byte board_addr;
    byte channel;
    unsigned long timeout_ms;
    bool active;
};

// Array of board entries instead of std::map
PwmBoardEntry pwm_boards[MAX_PWM_BOARDS];

// Array to track servo timeouts
ServoTimeout servo_timeouts[MAX_ACTIVE_SERVOS];

// Encoder variables
volatile long encoderPosition = 0;
volatile int lastCLK = 0;
int encoderCLKPin = -1;
int encoderDTPin = -1;
bool encoderEnabled = false;

// Break beam sensor variables
const int BREAK_BEAM_PING_INTERVAL_MS = 1;
const int BREAK_BEAM_HISTORY_DURATION_MS = 150;
const int BREAK_BEAM_HISTORY_SIZE = BREAK_BEAM_HISTORY_DURATION_MS / BREAK_BEAM_PING_INTERVAL_MS;

int breakBeamSensorPin = -1;
bool breakBeamEnabled = false;
unsigned long breakBeamReadings[BREAK_BEAM_HISTORY_SIZE];
unsigned long breakBeamTimestamps[BREAK_BEAM_HISTORY_SIZE];
int breakBeamHistoryIndex = 0;
unsigned long lastBreakBeamPing = 0;

// Initialize all board entries as inactive
void initPwmBoards() {
    for (int i = 0; i < MAX_PWM_BOARDS; i++) {
        pwm_boards[i].active = false;
    }
}

// Initialize servo timeout tracking
void initServoTimeouts() {
    for (int i = 0; i < MAX_ACTIVE_SERVOS; i++) {
        servo_timeouts[i].active = false;
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
    if (DEBUG_LEVEL > 0) {
        char debugMsg[80];
        sprintf(debugMsg, "makeBoard: addr=0x%02X", addr);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    int idx = findBoardIndex(addr);
    if (idx >= 0) {
        if (DEBUG_LEVEL > 0) {
            Firmata.sendString(STRING_DATA, "Board already exists");
        }
        return;
    }

    idx = findEmptyBoardSlot();
    if (idx < 0) {
        if (DEBUG_LEVEL > 0) {
            Firmata.sendString(STRING_DATA, "No space for new board");
        }
        return;
    }

    pwm_boards[idx].addr = addr;
    pwm_boards[idx].active = true;
    pwm_boards[idx].driver = Adafruit_PWMServoDriver(addr);

    if (DEBUG_LEVEL > 0) {
        Firmata.sendString(STRING_DATA, "Calling driver.begin()");
    }
    pwm_boards[idx].driver.begin();

    if (DEBUG_LEVEL > 0) {
        Firmata.sendString(STRING_DATA, "Setting oscillator frequency");
    }
    pwm_boards[idx].driver.setOscillatorFrequency(27000000);

    if (DEBUG_LEVEL > 0) {
        Firmata.sendString(STRING_DATA, "Setting PWM frequency");
    }
    pwm_boards[idx].driver.setPWMFreq(SERVO_FREQ);

    if (DEBUG_LEVEL > 0) {
        Firmata.sendString(STRING_DATA, "makeBoard completed successfully");
    }
}

void moveServoToAngle(byte addr, byte channel, uint16_t angle) {
    int idx = findBoardIndex(addr);
    if (idx >= 0) {
        pwm_boards[idx].driver.setPWM(channel, 0, angleToPulse(angle));
        scheduleServoTimeout(addr, channel);
    }
}

// Schedule a servo to be turned off after SERVO_HOLD_TIME_MS
void scheduleServoTimeout(byte addr, byte channel) {
    // First check if this servo already has a timeout scheduled
    for (int i = 0; i < MAX_ACTIVE_SERVOS; i++) {
        if (servo_timeouts[i].active &&
            servo_timeouts[i].board_addr == addr &&
            servo_timeouts[i].channel == channel) {
            // Update existing timeout
            servo_timeouts[i].timeout_ms = millis() + SERVO_HOLD_TIME_MS;
            return;
        }
    }

    // Find empty slot for new timeout
    for (int i = 0; i < MAX_ACTIVE_SERVOS; i++) {
        if (!servo_timeouts[i].active) {
            servo_timeouts[i].board_addr = addr;
            servo_timeouts[i].channel = channel;
            servo_timeouts[i].timeout_ms = millis() + SERVO_HOLD_TIME_MS;
            servo_timeouts[i].active = true;
            return;
        }
    }

    if (DEBUG_LEVEL > 0) {
        Firmata.sendString(STRING_DATA, "Warning: No space for servo timeout");
    }
}

// Turn off a servo by setting PWM to 0
void turnOffServo(byte addr, byte channel) {
    int idx = findBoardIndex(addr);
    if (idx >= 0) {
        pwm_boards[idx].driver.setPWM(channel, 0, 0);
        if (DEBUG_LEVEL > 0) {
            char debugMsg[80];
            sprintf(debugMsg, "Turned off servo: addr=0x%02X, channel=%d", addr, channel);
            Firmata.sendString(STRING_DATA, debugMsg);
        }
    }
}

// Check for servos that should be turned off
void checkServoTimeouts() {
    unsigned long current_time = millis();

    for (int i = 0; i < MAX_ACTIVE_SERVOS; i++) {
        if (servo_timeouts[i].active && current_time >= servo_timeouts[i].timeout_ms) {
            turnOffServo(servo_timeouts[i].board_addr, servo_timeouts[i].channel);
            servo_timeouts[i].active = false;
        }
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
        case TURN_OFF_SERVO: {
            turnOffServo(argv[0], argv[1]);
            break;
        }
    }
}

void setPinModeDigital(byte pin, byte mode) {
    if (DEBUG_LEVEL > 0) {
        char debugMsg[50];
        sprintf(debugMsg, "Pin mode: pin=%d, mode=%d", pin, mode);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    pinMode(pin, mode);
}

void writeDigitalPin(byte pin, byte value) {
    if (DEBUG_LEVEL > 0) {
        char debugMsg[50];
        sprintf(debugMsg, "Digital write: pin=%d, value=%d", pin, value);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    digitalWrite(pin, value);
}

void writePwmPin(byte pin, byte value) {
    if (DEBUG_LEVEL > 0) {
        char debugMsg[50];
        sprintf(debugMsg, "PWM write: pin=%d, value=%d", pin, value);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    analogWrite(pin, value);
}

void parseDigitalPinCommand(byte command, byte argc, byte *argv) {
    if (DEBUG_LEVEL > 0) {
        char debugMsg[80];
        sprintf(debugMsg, "Digital cmd: %d, argc: %d", command, argc);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    switch (command) {
        case SET_PIN_MODE_DIGITAL: {
            if (DEBUG_LEVEL > 0) {
                Firmata.sendString(STRING_DATA, "SET_PIN_MODE_DIGITAL");
            }
            setPinModeDigital(argv[0], argv[1]);
            break;
        }
        case WRITE_DIGITAL_PIN: {
            if (DEBUG_LEVEL > 0) {
                Firmata.sendString(STRING_DATA, "WRITE_DIGITAL_PIN");
            }
            writeDigitalPin(argv[0], argv[1]);
            break;
        }
        case WRITE_PWM_PIN: {
            if (DEBUG_LEVEL > 0) {
                Firmata.sendString(STRING_DATA, "WRITE_PWM_PIN");
            }
            writePwmPin(argv[0], argv[1]);
            break;
        }
        default: {
            if (DEBUG_LEVEL > 0) {
                char debugMsg[80];
                sprintf(debugMsg, "Unknown digital cmd: %d", command);
                Firmata.sendString(STRING_DATA, debugMsg);
            }
            break;
        }
    }
}

void readEncoder() {
    int currentCLK = digitalRead(encoderCLKPin);

    if (currentCLK != lastCLK) {
        if (digitalRead(encoderDTPin) != currentCLK) {
            encoderPosition++;
        } else {
            encoderPosition--;
        }
    }
    lastCLK = currentCLK;
}

void setupEncoder(byte clkPin, byte dtPin) {
    if (encoderEnabled) {
        detachInterrupt(digitalPinToInterrupt(encoderCLKPin));
    }

    encoderCLKPin = clkPin;
    encoderDTPin = dtPin;
    encoderPosition = 0;

    pinMode(encoderCLKPin, INPUT_PULLUP);
    pinMode(encoderDTPin, INPUT_PULLUP);

    lastCLK = digitalRead(encoderCLKPin);

    attachInterrupt(digitalPinToInterrupt(encoderCLKPin), readEncoder, CHANGE);
    encoderEnabled = true;

    if (DEBUG_LEVEL > 0) {
        char debugMsg[50];
        sprintf(debugMsg, "Encoder setup: CLK=%d, DT=%d", clkPin, dtPin);
        Firmata.sendString(STRING_DATA, debugMsg);
    }
}

long getEncoderPosition() {
    return encoderPosition;
}

void resetEncoder() {
    encoderPosition = 0;
    if (DEBUG_LEVEL > 0) {
        char debugMsg[30];
        sprintf(debugMsg, "Encoder reset to 0");
        Firmata.sendString(STRING_DATA, debugMsg);
    }
}

void parseEncoderCommand(byte command, byte argc, byte *argv) {
    if (DEBUG_LEVEL > 0) {
        char debugMsg[80];
        sprintf(debugMsg, "Encoder cmd: %d, argc: %d", command, argc);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    switch (command) {
        case ENCODER_SETUP: {
            setupEncoder(argv[0], argv[1]);
            break;
        }
        case ENCODER_READ: {
            long position = getEncoderPosition();
            // Split position into 7-bit chunks since Firmata automatically
            // converts each byte into 2 7-bit bytes during transmission
            byte response[2];
            response[0] = position & 0x7F;        // Low 7 bits
            response[1] = (position >> 7) & 0x7F; // Next 7 bits (supports up to 16,383)
            Firmata.sendSysex(ENCODER, 2, response);
            break;
        }
        case ENCODER_RESET: {
            resetEncoder();
            break;
        }
        default: {
            if (DEBUG_LEVEL > 0) {
                char debugMsg[80];
                sprintf(debugMsg, "Unknown encoder cmd: %d", command);
                Firmata.sendString(STRING_DATA, debugMsg);
            }
            break;
        }
    }
}

void setupBreakBeamSensor(byte sensorPin) {
    breakBeamSensorPin = sensorPin;
    pinMode(breakBeamSensorPin, INPUT_PULLUP);
    breakBeamEnabled = true;
    breakBeamHistoryIndex = 0;
    lastBreakBeamPing = millis();

    for (int i = 0; i < BREAK_BEAM_HISTORY_SIZE; i++) {
        breakBeamReadings[i] = 1;
        breakBeamTimestamps[i] = 0;
    }

    if (DEBUG_LEVEL > 0) {
        char debugMsg[50];
        sprintf(debugMsg, "Break beam sensor setup on pin %d", sensorPin);
        Firmata.sendString(STRING_DATA, debugMsg);
    }
}

void updateBreakBeamSensor() {
    if (!breakBeamEnabled) return;

    unsigned long currentTime = millis();
    if (currentTime - lastBreakBeamPing >= BREAK_BEAM_PING_INTERVAL_MS) {
        int reading = digitalRead(breakBeamSensorPin);

        breakBeamReadings[breakBeamHistoryIndex] = reading;
        breakBeamTimestamps[breakBeamHistoryIndex] = currentTime;

        // Automatically disable motors when break beam is broken (reading == 0)
        // This is done in firmware for fast response since serial communication is too slow
        // NOTE: Main conveyor is NOT disabled to keep objects moving
        if (reading == 0) {
            Firmata.sendString(STRING_DATA, "BREAK BEAM TRIGGERED - EMERGENCY MOTOR STOP");

            // Stop first vibration hopper motor
            analogWrite(FIRST_VIBRATION_HOPPER_ENABLE_PIN, 0);
            digitalWrite(FIRST_VIBRATION_HOPPER_INPUT1_PIN, LOW);
            digitalWrite(FIRST_VIBRATION_HOPPER_INPUT2_PIN, LOW);

            // Stop second vibration hopper motor
            analogWrite(SECOND_VIBRATION_HOPPER_ENABLE_PIN, 0);
            digitalWrite(SECOND_VIBRATION_HOPPER_INPUT1_PIN, LOW);
            digitalWrite(SECOND_VIBRATION_HOPPER_INPUT2_PIN, LOW);

            // Stop feeder conveyor motor
            analogWrite(FEEDER_CONVEYOR_ENABLE_PIN, 0);
            digitalWrite(FEEDER_CONVEYOR_INPUT1_PIN, LOW);
            digitalWrite(FEEDER_CONVEYOR_INPUT2_PIN, LOW);
        }

        // Debug every 100th reading to avoid spam
        static int debugCounter = 0;
        if (DEBUG_LEVEL > 0 && debugCounter++ % 100 == 0) {
            char debugMsg[60];
            sprintf(debugMsg, "Break beam: pin=%d, reading=%d, time=%lu",
                   breakBeamSensorPin, reading, currentTime);
            Firmata.sendString(STRING_DATA, debugMsg);
        }

        breakBeamHistoryIndex = (breakBeamHistoryIndex + 1) % BREAK_BEAM_HISTORY_SIZE;
        lastBreakBeamPing = currentTime;
    }
}

unsigned long findBreakingSince(unsigned long sinceTimestamp) {
    unsigned long currentTime = millis();
    unsigned long earliestValidTime = (currentTime > BREAK_BEAM_HISTORY_DURATION_MS) ?
                                     (currentTime - BREAK_BEAM_HISTORY_DURATION_MS) : 0;

    if (DEBUG_LEVEL > 0) {
        char debugMsg[80];
        sprintf(debugMsg, "Search: since=%lu, earliest=%lu, current=%lu",
               sinceTimestamp, earliestValidTime, currentTime);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    if (sinceTimestamp < earliestValidTime) {
        sinceTimestamp = earliestValidTime;
    }

    int breakingCount = 0;
    for (int i = 0; i < BREAK_BEAM_HISTORY_SIZE; i++) {
        int idx = (breakBeamHistoryIndex - 1 - i + BREAK_BEAM_HISTORY_SIZE) % BREAK_BEAM_HISTORY_SIZE;

        if (breakBeamTimestamps[idx] >= sinceTimestamp) {
            if (breakBeamReadings[idx] == 0) {
                breakingCount++;
                if (DEBUG_LEVEL > 0) {
                    char debugMsg[80];
                    sprintf(debugMsg, "Found break at idx=%d, time=%lu, reading=%d",
                           idx, breakBeamTimestamps[idx], breakBeamReadings[idx]);
                    Firmata.sendString(STRING_DATA, debugMsg);
                }
                return breakBeamTimestamps[idx];
            }
        } else {
            break;
        }
    }

    if (DEBUG_LEVEL > 0) {
        char debugMsg[80];
        sprintf(debugMsg, "No breaks found in %d readings", BREAK_BEAM_HISTORY_SIZE);
        Firmata.sendString(STRING_DATA, debugMsg);
    }
    return 0xFFFFFFFF;
}

unsigned long getLatestBreakBeamTimestamp() {
    if (!breakBeamEnabled) return 0;

    int latestIdx = (breakBeamHistoryIndex - 1 + BREAK_BEAM_HISTORY_SIZE) % BREAK_BEAM_HISTORY_SIZE;
    return breakBeamTimestamps[latestIdx];
}

void parseBreakBeamCommand(byte command, byte argc, byte *argv) {
    if (DEBUG_LEVEL > 0) {
        char debugMsg[80];
        sprintf(debugMsg, "Break beam cmd: %d, argc: %d", command, argc);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    switch (command) {
        case BREAK_BEAM_SETUP: {
            setupBreakBeamSensor(argv[0]);
            break;
        }
        case BREAK_BEAM_QUERY: {
            if (argc < 5) {
                if (DEBUG_LEVEL > 0) {
                    char debugMsg[80];
                    sprintf(debugMsg, "Break beam query: got %d args, need 5 timestamp bytes", argc);
                    Firmata.sendString(STRING_DATA, debugMsg);
                }
                return;
            }

            // argv[0-4] are the 5 timestamp bytes (subcommand already stripped by sysexCallback)
            unsigned long sinceTimestamp = (unsigned long)argv[0] |
                                         ((unsigned long)argv[1] << 7) |
                                         ((unsigned long)argv[2] << 14) |
                                         ((unsigned long)argv[3] << 21) |
                                         ((unsigned long)argv[4] << 28);

            if (DEBUG_LEVEL > 0) {
                char debugMsg[80];
                sprintf(debugMsg, "Query since: %lu (bytes: %d,%d,%d,%d,%d)",
                       sinceTimestamp, argv[0], argv[1], argv[2], argv[3], argv[4]);
                Firmata.sendString(STRING_DATA, debugMsg);
            }

            unsigned long breakTimestamp = findBreakingSince(sinceTimestamp);
            unsigned long latestTimestamp = getLatestBreakBeamTimestamp();
            unsigned long currentTime = millis();

            if (DEBUG_LEVEL > 0) {
                char debugMsg[80];
                sprintf(debugMsg, "Result: break=%lu, latest=%lu, current=%lu",
                       breakTimestamp, latestTimestamp, currentTime);
                Firmata.sendString(STRING_DATA, debugMsg);
            }

            // Pack 32-bit values into 5 7-bit bytes each
            byte response[10];
            response[0] = breakTimestamp & 0x7F;
            response[1] = (breakTimestamp >> 7) & 0x7F;
            response[2] = (breakTimestamp >> 14) & 0x7F;
            response[3] = (breakTimestamp >> 21) & 0x7F;
            response[4] = (breakTimestamp >> 28) & 0x7F;

            response[5] = latestTimestamp & 0x7F;
            response[6] = (latestTimestamp >> 7) & 0x7F;
            response[7] = (latestTimestamp >> 14) & 0x7F;
            response[8] = (latestTimestamp >> 21) & 0x7F;
            response[9] = (latestTimestamp >> 28) & 0x7F;

            if (DEBUG_LEVEL > 0) {
                char debugMsg[80];
                sprintf(debugMsg, "Response bytes: [%d,%d,%d,%d,%d] [%d,%d,%d,%d,%d]",
                       response[0], response[1], response[2], response[3], response[4],
                       response[5], response[6], response[7], response[8], response[9]);
                Firmata.sendString(STRING_DATA, debugMsg);
            }

            Firmata.sendSysex(BREAK_BEAM, 10, response);
            break;
        }
        default: {
            if (DEBUG_LEVEL > 0) {
                char debugMsg[80];
                sprintf(debugMsg, "Unknown break beam cmd: %d", command);
                Firmata.sendString(STRING_DATA, debugMsg);
            }
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
    if (DEBUG_LEVEL > 0) {
        char debugMsg[80];
        sprintf(debugMsg, "Sysex cmd: 0x%02X, argc=%d", command, argc);
        Firmata.sendString(STRING_DATA, debugMsg);
    }

    // Print argv contents for debugging
    if (argc > 0) {
        if (DEBUG_LEVEL > 0) {
            char debugMsg[80];
            sprintf(debugMsg, "Argv[0]: %d", argv[0]);
            // Firmata.sendString(STRING_DATA, debugMsg);
        }
    }
    if (argc > 1) {
        if (DEBUG_LEVEL > 0) {
            char debugMsg[80];
            sprintf(debugMsg, "Argv[1]: %d", argv[1]);
            // Firmata.sendString(STRING_DATA, debugMsg);
        }
    }
    if (argc > 2) {
        if (DEBUG_LEVEL > 0) {
            char debugMsg[80];
            sprintf(debugMsg, "Argv[2]: %d", argv[2]);
            // Firmata.sendString(STRING_DATA, debugMsg);
        }
    }

    switch (command) {
        case PWM_SERVO:
            if (DEBUG_LEVEL > 0) {
                Firmata.sendString(STRING_DATA, "Processing PWM_SERVO");
            }
            parsePwmServoCommand(argv[0], argc-1, argv+1);
        break;
        case DIGITAL_PIN:
            if (DEBUG_LEVEL > 0) {
                Firmata.sendString(STRING_DATA, "Processing DIGITAL_PIN");
            }
            parseDigitalPinCommand(argv[0], argc-1, argv+1);
        break;
        case ENCODER:
            if (DEBUG_LEVEL > 0) {
                Firmata.sendString(STRING_DATA, "Processing ENCODER");
            }
            parseEncoderCommand(argv[0], argc-1, argv+1);
        break;
        case BREAK_BEAM:
            if (DEBUG_LEVEL > 0) {
                Firmata.sendString(STRING_DATA, "Processing BREAK_BEAM");
            }
            parseBreakBeamCommand(argv[0], argc-1, argv+1);
        break;
        default:
            if (DEBUG_LEVEL > 0) {
                char debugMsg[80];
                sprintf(debugMsg, "Unknown sysex command: 0x%02X", command);
                Firmata.sendString(STRING_DATA, debugMsg);
            }
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

    // Initialize servo timeout tracking
    initServoTimeouts();

    // Initialize motor control pins for automatic break beam control
    pinMode(FIRST_VIBRATION_HOPPER_ENABLE_PIN, OUTPUT);
    pinMode(FIRST_VIBRATION_HOPPER_INPUT1_PIN, OUTPUT);
    pinMode(FIRST_VIBRATION_HOPPER_INPUT2_PIN, OUTPUT);
    pinMode(SECOND_VIBRATION_HOPPER_ENABLE_PIN, OUTPUT);
    pinMode(SECOND_VIBRATION_HOPPER_INPUT1_PIN, OUTPUT);
    pinMode(SECOND_VIBRATION_HOPPER_INPUT2_PIN, OUTPUT);
    pinMode(FEEDER_CONVEYOR_ENABLE_PIN, OUTPUT);
    pinMode(FEEDER_CONVEYOR_INPUT1_PIN, OUTPUT);
    pinMode(FEEDER_CONVEYOR_INPUT2_PIN, OUTPUT);

    // Initialize motors to off state
    analogWrite(FIRST_VIBRATION_HOPPER_ENABLE_PIN, 0);
    digitalWrite(FIRST_VIBRATION_HOPPER_INPUT1_PIN, LOW);
    digitalWrite(FIRST_VIBRATION_HOPPER_INPUT2_PIN, LOW);
    analogWrite(SECOND_VIBRATION_HOPPER_ENABLE_PIN, 0);
    digitalWrite(SECOND_VIBRATION_HOPPER_INPUT1_PIN, LOW);
    digitalWrite(SECOND_VIBRATION_HOPPER_INPUT2_PIN, LOW);
    analogWrite(FEEDER_CONVEYOR_ENABLE_PIN, 0);
    digitalWrite(FEEDER_CONVEYOR_INPUT1_PIN, LOW);
    digitalWrite(FEEDER_CONVEYOR_INPUT2_PIN, LOW);

    // to get smoother operation for the dc motors running over pwm, increase the speed timers 2 and 5
    // Change PWM frequency for pins 3 & 5 (Timer 3):
    TCCR3B = TCCR3B & B11111000 | B00000001; // ~31kHz

    // Change PWM frequency for pin 6 (Timer 4):
    TCCR4B = TCCR4B & B11111000 | B00000001; // ~31kHz


    Firmata.sendString(F("Setup complete. Ready for commands."));
}

void loop() {
    while(Firmata.available()) { //only runs if message in buffer
        Firmata.processInput();
        if (!Firmata.isParsingMessage()) {
            break;
        }
    }

    // Check for servos that should be turned off
    checkServoTimeouts();

    // Update break beam sensor readings
    updateBreakBeamSensor();
}
