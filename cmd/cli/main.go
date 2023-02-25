package main 

import (
    "fmt"
    "github.com/spencerhhubert/go-firmata"
    "time"
    r "github.com/spencerhhubert/nexus/robot/actuators"
    u "github.com/spencerhhubert/nexus/utils"
)

var feeder_stepper_dir_pin uint8 = 2 
var feeder_stepper_step_pin uint8 = 3
var main_conveyor_stepper_dir_pin uint8 = 4
var main_conveyor_stepper_step_pin uint8 = 5
var vibration_motor_pin uint8 = 9

func loopServoTest(mc *firmata.FirmataClient) {
    r.NewPCA9685(mc, 0x40)
    servo := r.NewServo(mc, 0x40, byte(15))
    servo2 := r.NewServo(mc, 0x40, byte(0))
    for {
        servo.SetAngle(0)
        time.Sleep(time.Second * 3)
        servo.SetAngle(180)
        time.Sleep(time.Second * 3)
        servo2.SetAngle(0)
        time.Sleep(time.Second * 3)
        servo2.SetAngle(180)
        time.Sleep(time.Second * 3)
    }
}

func main() {
    //mc, error := firmata.NewClient("/dev/ttyUSB1", 57600) 
    mc, error := firmata.NewClient("/dev/ttyACM0", 57600) 
    defer mc.Close()
    if error != nil {
        fmt.Println("Error connecting to Arduino")
        panic(error)
    }
    go u.WaitForKillCommand(mc)

    feeder_stepper := r.NewStepper(mc, 2, 3, 200*(1/16))
    main_conveyor_stepper := r.NewStepper(mc, 4, 5, 200*(1/4))
//    vibration_motor := NewVibrationMotor(mc, vibration_motor_pin)

    go feeder_stepper.Run(true, 50000)
    go main_conveyor_stepper.Run(true, 50000)
//    go vibration_motor.Run(255)
//    go loopServoTest(mc)

    for {
        fmt.Println("Running")
        time.Sleep(time.Second * 10)
    }
}
