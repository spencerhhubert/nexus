package sort 

import (
    c "github.com/spencerhhubert/nexus/classification"
    i "github.com/spencerhhubert/nexus/identification"
    "github.com/owulveryck/onnx-go"
    "gorgonia.org/tensor"
//    "github.com/spencerhhubert/nexus/robot/actuators"
//    "github.com/spencerhhubert/go-firmata"
)

//actually runs motors and sorts
func Sort(profile *c.Profile, model *onnx.Model) {
    fresh_bin := c.Bin{Column: 0, Row: 0}
    model := onnx.NewModel()
    for {
        //get pic
        img := camera.GetImage()
        ten := i.ImageToTensor(img)
        piece = identification.Identify(ten, model)
        SendHome(piece, profile)
    }
}

func Classify(piece *c.Piece, profile *c.Profile) c.Category {
    //
}

func SendHome(piece *c.Piece, profile *c.Profile) {
    //
} 

