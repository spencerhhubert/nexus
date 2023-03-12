package utils

import (
    "os"
    "github.com/spencerhhubert/go-firmata"
    "os/signal"
    "syscall"
    "time"
    "encoding/binary"
    "math"
    "fmt"
)

func UInt8To7BitBytes(i uint8) []byte {
    var b [2]byte
    b[0] = byte(i & 0x7F)
    b[1] = byte(i >> 7)
    return b[:]
}

func Float32To7BitBytes(f float32) []byte {
    bits := math.Float32bits(f)
    bytes := make([]byte, 4)
    binary.LittleEndian.PutUint32(bytes, bits)
    var out []byte
    for _, b := range bytes {
        out = append(out, []byte{b & 0x7f, (b >> 7) & 0x7f}...)
    }
    return out

}

func EncodeIEEE754To7BitBytes(f float32) []byte {
    // Extract the sign bit, exponent, and mantissa from the float32 value
    bits := math.Float32bits(f)
    sign := (bits >> 31) & 0x1
    exponent := ((bits >> 23) & 0xff)
    mantissa := bits & 0x7fffff
    fmt.Println("sign: %d, exponent: %d, mantissa: %d", sign, exponent, mantissa)
    
    // Add the implicit leading bit to the mantissa
    mantissa |= 0x800000
    
    // Convert the sign, exponent, and mantissa to five 7-bit bytes
    bytes := make([]byte, 5)
    bytes[0] = byte((exponent >> 6) & 0x7f)
    bytes[1] = byte(((exponent & 0x3f) << 1) | ((mantissa >> 22) & 0x01))
    bytes[2] = byte((mantissa >> 15) & 0x7f)
    bytes[3] = byte((mantissa >> 8) & 0x7f)
    bytes[4] = byte(mantissa & 0x7f)
    
    // Set the sign bit in the first byte if the value is negative
    if sign == 1 {
        bytes[0] |= 0x80
    }
    
    return bytes
}

func WaitForKillCommand(dev *firmata.FirmataClient) {
    //it's annoying to reconnect to the microcontroller if you don't .Close()
    sigs := make(chan os.Signal, 1)
    signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
    go func () {
        <-sigs
        dev.Close()
        fmt.Println("Killing")
        time.Sleep(5000 * time.Millisecond)
        os.Exit(0)
    }()
}
