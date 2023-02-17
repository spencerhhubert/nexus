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

var vibration_motor_pin uint8 = 9

func main() {
    nano, error := firmata.NewClient("/dev/ttyUSB1", 57600) 

    if error != nil {
        fmt.Println("Error connecting to Arduino")
        panic(error)
    }

    feeder_stepper := NewStepper(nano, feeder_stepper_dir_pin, feeder_stepper_step_pin, 200*(1/16))
    main_conveyor_stepper := NewStepper(nano, main_conveyor_stepper_dir_pin, main_conveyor_stepper_step_pin, 200*(1/16))
    vibration_motor := NewVibrationMotor(nano, vibration_motor_pin)

    go feeder_stepper.Run(true, 60)
    go main_conveyor_stepper.Run(true, 60)
    go vibration_motor.Run(255)

    for {
        fmt.Println("Running")
        time.Sleep(time.Second * 10)
    }
}
