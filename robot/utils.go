package main

import (
    "os"
    "github.com/spencerhhubert/go-firmata"
    "os/signal"
    "syscall"
    "time"
)

func UInt8To7BitBytes(i uint8) []byte {
    var b [2]byte
    b[0] = byte(i & 0x7F)
    b[1] = byte(i >> 7)
    return b[:]
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
