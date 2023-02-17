package main

import (
    "github.com/kraman/go-firmata"
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
