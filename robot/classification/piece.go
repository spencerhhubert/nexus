package classification

import (
    "yaml"
    "encoding/json"
)

type Id string

//at a higher level where big profiles get construted, should have "piece characteristics" map so that categories can actually just sort on characteristics
type Kind struct {
    Name string //might consider dropping some of these fields if too memory constrained
    Id int
}

type Color struct {
    Name string
    Id int //will want to make map from these Ids to what bricklink, lego, and ldraw use
}

//these describe pieces
//"tile", "one_wide", "round", etc. probably just hack all the characteristics on bricklink
type Characteristic string

type Piece struct {
    Kind Kind
    Color Color
    Characteristics []Characteristic
}

type Category struct {
    Name string
    Id int
    Contents []Piece
    Characteristics  []Characteristic //pieces in Contents will override these
}
