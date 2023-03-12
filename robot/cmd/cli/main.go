package main 

import (
    "fmt"
    "os"
    "github.com/spencerhhubert/go-firmata"
    "time"
    irl "github.com/spencerhhubert/nexus/robot/irl/actuators"
    u "github.com/spencerhhubert/nexus/robot/utils"
)

var feeder_stepper_dir_pin uint8 = 2 
var feeder_stepper_step_pin uint8 = 3
var main_conveyor_stepper_dir_pin uint8 = 4
var main_conveyor_stepper_step_pin uint8 = 5
var vibration_motor_1_pin uint8 = 9
var vibration_motor_2_pin uint8 = 10

func loopServoTest(mc *firmata.FirmataClient) {
    irl.NewPCA9685(mc, 0x40)
    irl.NewPCA9685(mc, 0x41)
    servo2 := irl.NewServo(mc, 0x41, byte(15))
    for {
        servo2.SetAngle(45)
        time.Sleep(time.Second * 3)
        servo2.SetAngle(88)
        time.Sleep(time.Second * 3)
    }
}

func main() {
    fmt.Println(os.Getenv("MC_USB"))
    fmt.Println("Starting")
    mc, error := firmata.NewClient(os.Getenv("MC_USB"), 57600)
    fmt.Println("Connecting to Arduino")
    defer mc.Close()
    if error != nil {
        fmt.Println("Error connecting to Arduino")
        panic(error)
    }
    go u.WaitForKillCommand(mc)
    fmt.Println("Starting")

    feeder_stepper := irl.NewStepper(mc, 2, 3, 200*16)
    main_conveyor_stepper := irl.NewStepper(mc, 4, 5, 200*16)
    vibration_motor1 := irl.NewVibrationMotor(mc, vibration_motor_1_pin)
    vibration_motor2 := irl.NewVibrationMotor(mc, vibration_motor_2_pin)

    go feeder_stepper.Run(true, 5000)
    go main_conveyor_stepper.Run(true, 25000)
    go vibration_motor1.Run(255)
    go vibration_motor2.Run(0)

    for {
        fmt.Println("Running")
        time.Sleep(time.Second * 10)
    }
}
