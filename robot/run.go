package main

import (
    "fmt"
    "github.com/kraman/go-firmata"
    "time"
)

var feeder_stepper_dir_pin uint8 = 2 
var feeder_stepper_step_pin uint8 = 3
var main_conveyor_stepper_dir_pin uint8 = 4
var main_conveyor_stepper_step_pin uint8 = 5

var vibration_motor_apin uint8 = 9

var led_pin uint8 = 10

func RunStepper(dev *firmata.FirmataClient, dir_pin uint8, step_pin uint8, dir bool, inverse_speed int) {
    dev.DigitalWrite(dir_pin, dir)
    for {
        dev.DigitalWrite(step_pin, true)
        time.Sleep(time.Microsecond * time.Duration(inverse_speed))
//        dev.Delay(time.Microsecond * time.Duration(speed))
        dev.DigitalWrite(step_pin, false)
        time.Sleep(time.Microsecond * time.Duration(inverse_speed))
//        dev.Delay(time.Microsecond * time.Duration(speed))
    }
}

func RunVibrationMotor(dev *firmata.FirmataClient, apin uint8, voltage byte) {
    //cast uint8 to uint because that's just how it has to be
    apinBig := uint(apin)
    dev.AnalogWrite(apinBig, voltage)
}

func TurnOnLed(dev *firmata.FirmataClient, pin uint8) {
    dev.DigitalWrite(pin, true)
}

func main() {
    client, error := firmata.NewClient("/dev/ttyUSB1", 57600) 

    if error != nil {
        fmt.Println("Error connecting to Arduino")
        panic(error)
    }

    client.SetPinMode(feeder_stepper_dir_pin, firmata.Output)
    client.SetPinMode(feeder_stepper_step_pin, firmata.Output)
    client.SetPinMode(main_conveyor_stepper_dir_pin, firmata.Output)
    client.SetPinMode(main_conveyor_stepper_step_pin, firmata.Output)
    client.SetPinMode(vibration_motor_apin, firmata.PWM)

    client.SetPinMode(led_pin, firmata.Output)

//    go RunStepper(client, feeder_stepper_dir_pin, feeder_stepper_step_pin, true, 5)
    go RunStepper(client, main_conveyor_stepper_dir_pin, main_conveyor_stepper_step_pin, true, 10000)
//    go RunVibrationMotor(client, vibration_motor_apin, 255)

//    go TurnOnLed(client, led_pin)

    for {
        fmt.Println("Running")
        time.Sleep(time.Second * 10)
    }
}
