package actuators 

import (
    "github.com/spencerhhubert/go-firmata"
    "time"
)

type Stepper struct {
    dir_pin uint8
    step_pin uint8
    steps_per_rev float32 //1, 1/2, 1/4, 1/8, or 1/16 times 200 or whatever the motor spec says
    device *firmata.FirmataClient
}

func NewStepper(device *firmata.FirmataClient, dir_pin uint8, step_pin uint8, steps_per_rev float32) *Stepper {
    device.SetPinMode(dir_pin, firmata.Output)
    device.SetPinMode(step_pin, firmata.Output)
    return &Stepper{dir_pin, step_pin, steps_per_rev, device}
}

func (s *Stepper) Run(dir bool, rpm int) {
    var delay int = int(60e6 / float64((s.steps_per_rev * float32(rpm))))
    s.device.DigitalWrite(s.dir_pin, dir)
    for {
        s.device.DigitalWrite(s.step_pin, true)
        time.Sleep(time.Microsecond * time.Duration(delay))
        s.device.DigitalWrite(s.step_pin, false)
        time.Sleep(time.Microsecond * time.Duration(delay))
    }
}

func (s *Stepper) Step(dir bool, rpm int, steps int) {
    var delay int = int(60e6 / float64((s.steps_per_rev * float32(rpm))))
    s.device.DigitalWrite(s.dir_pin, dir)
    for i := 0; i < steps; i++ {
        s.device.DigitalWrite(s.step_pin, true)
        time.Sleep(time.Microsecond * time.Duration(delay))
        s.device.DigitalWrite(s.step_pin, false)
        time.Sleep(time.Microsecond * time.Duration(delay))
    }
}

type VibrationMotor struct {
    pwm_pin uint8
    device *firmata.FirmataClient
}

func NewVibrationMotor(device *firmata.FirmataClient, pwm_pin uint8) *VibrationMotor {
    device.SetPinMode(pwm_pin, firmata.PWM)
    return &VibrationMotor{pwm_pin, device}
}

func (v *VibrationMotor) Run(voltage byte) {
    var pin_big_int uint = uint(v.pwm_pin)
    v.device.AnalogWrite(pin_big_int, voltage)
}

type PCA9685 struct {
    dev *firmata.FirmataClient
    board_addr byte
    //TODO: have oscillator frequency and prescaler be set here instead of in arduino code
}

func NewPCA9685(dev *firmata.FirmataClient, board_addr byte) {
    dev.SysEx(0x01, 0x07, board_addr)
}

type Servo struct {
    dev *firmata.FirmataClient
    board_addr byte
    channel byte
    Angle uint8
}

func NewServo(dev *firmata.FirmataClient, board_addr byte, channel byte) *Servo {
    return &Servo{dev, board_addr, channel, 0}
}

func (s *Servo) SetAngle(angle uint8) {
    s.dev.SysEx(0x01, 0x08, s.board_addr, s.channel, UInt8To7BitBytes(angle)[0], UInt8To7BitBytes(angle)[1]);
    s.Angle = angle
}
