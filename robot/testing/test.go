package main

import (
    "fmt"
    "github.com/spencerhhubert/go-firmata"
//    "encoding/binary"
    "time"
    "os"
    "os/signal"
    "syscall"
)

func UInt8To7BitBytes(i uint8) []byte {
    var b [2]byte
    b[0] = byte(i & 0x7F)
    b[1] = byte(i >> 7)
    return b[:]
}

type Servo struct {
    dev *firmata.FirmataClient
    board_addr byte
    channel byte
    Angle uint8
}

type PCA9685 struct {
    dev *firmata.FirmataClient
    board_addr byte
    //TODO: have oscillator frequency and prescaler be set here instead of in arduino code
}

func NewPCA9685(dev *firmata.FirmataClient, board_addr byte) {
    dev.SysEx(0x01, 0x07, board_addr)
}

func NewServo(dev *firmata.FirmataClient, board_addr byte, channel byte) *Servo {
    return &Servo{dev, board_addr, channel, 0}
}

func (s *Servo) SetAngle(angle uint8) {
    s.dev.SysEx(0x01, 0x08, s.board_addr, s.channel, UInt8To7BitBytes(angle)[0], UInt8To7BitBytes(angle)[1]);
    s.Angle = angle
}

func Test(dev *firmata.FirmataClient) {
    NewPCA9685(dev, 0x40)
    time.Sleep(3000 * time.Millisecond)
    servo := NewServo(dev, 0x40, 0)
    time.Sleep(3000 * time.Millisecond)
    servo.SetAngle(90)
}

func waitForKillCommand(dev *firmata.FirmataClient) {
    //it's annoying to reconnect to the microcontroller if you don't .Close()
    sigs := make(chan os.Signal, 1)
    signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
    go func () {
        <-sigs
        dev.Close()
        time.Sleep(5000 * time.Millisecond)
        os.Exit(0)
    }()
}

func main() {
    //nano, error := firmata.NewClient("/dev/ttyUSB1", 57600) 
    nano, error := firmata.NewClient("/dev/ttyACM0", 57600) 
    defer nano.Close()
    if error != nil {
        fmt.Println("Error connecting to Arduino")
        panic(error)
    }
    go waitForKillCommand(nano)

    
    Test(nano)
    os.Exit(0)
}
