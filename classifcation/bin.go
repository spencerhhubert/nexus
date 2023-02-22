package classifcation

type Bin struct {
    Column int
    Row int
}

//fresh bin is rolling
func WhatBin(piece *Piece, profile *Profile, fresh_bin *Bin) *Bin {
    if (profile.WhereGo[piece.Id].Bin.Column != -1 &&
        profile.WhereGo[piece.Id].Bin.Row != -1) {
        return profile.WhereGo[piece.Id].Bin
    } else {
        profile.WhereGo[piece.Id].Bin := fresh_bin //duplicate in memory
        if fresh_bin.Column >= 7 {
            fresh_bin.Column = 0
            fresh_bin.Row++
        } else {
            fresh_bin.Column++
        } 
        return &profile.WhereGo[piece.Id].Bin
    }
}
