package main 

import (
    "fmt"
    "github.com/spencerhhubert/go-firmata"
    "time"
    r "github.com/spencerhhubert/nexus/robot/irl/actuators"
    u "github.com/spencerhhubert/nexus/robot/utils"
)

var feeder_stepper_dir_pin uint8 = 2 
var feeder_stepper_step_pin uint8 = 3
var main_conveyor_stepper_dir_pin uint8 = 4
var main_conveyor_stepper_step_pin uint8 = 5
var vibration_motor_1_pin uint8 = 9
var vibration_motor_2_pin uint8 = 10

func loopServoTest(mc *firmata.FirmataClient) {
    r.NewPCA9685(mc, 0x40)
    r.NewPCA9685(mc, 0x41)
    servo2 := r.NewServo(mc, 0x41, byte(15))
    for {
        servo2.SetAngle(45)
        time.Sleep(time.Second * 3)
        servo2.SetAngle(88)
        time.Sleep(time.Second * 3)
    }
}

func main() {
    //mc, error := firmata.NewClient("/dev/ttyUSB1", 57600) 
    mc, error := firmata.NewClient("/dev/ttyACM0", 57600) 
    fmt.Println("Connecting to Arduino")
    defer mc.Close()
    if error != nil {
        fmt.Println("Error connecting to Arduino")
        panic(error)
    }
    go u.WaitForKillCommand(mc)
    fmt.Println("Starting")

    feeder_stepper := r.NewStepper(mc, 2, 3, 200*16)
    main_conveyor_stepper := r.NewStepper(mc, 4, 5, 200*16)
    vibration_motor1 := r.NewVibrationMotor(mc, vibration_motor_1_pin)
    vibration_motor2 := r.NewVibrationMotor(mc, vibration_motor_2_pin)

    go feeder_stepper.Run(true, 5000)
    go main_conveyor_stepper.Run(true, 25000)
    go vibration_motor1.Run(255)
    go vibration_motor2.Run(0)

    for {
        fmt.Println("Running")
        time.Sleep(time.Second * 10)
    }
}

func servotestmain() {
    //mc, error := firmata.NewClient("/dev/ttyUSB1", 57600) 
    mc, error := firmata.NewClient("/dev/ttyACM0", 57600) 
    fmt.Println("Connecting to Arduino")
    defer mc.Close()
    if error != nil {
        fmt.Println("Error connecting to Arduino")
        panic(error)
    }
    go u.WaitForKillCommand(mc)
    fmt.Println("Starting")
    go loopServoTest(mc)
    for {
        fmt.Println("Running")
        time.Sleep(time.Second * 10)
    }
}

