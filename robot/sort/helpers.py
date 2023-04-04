import os
import json
import math

def incrementBins(category:str, dms:list) -> tuple:
    for dm in dms:
        for bin in dm.bins:
            if bin.category == category:
                print(f"Reusing bin for {category}")
                return dm, bin, dms
            if bin.category == None:
                print(f"Making new bins for {category}")
                bin.category = category
                return dm, bin, dms
    print("out of bins, using last bin in last distribution module")
    return (dms[-1], dms[-1].bins[-1], dms)

def speed(steps_per_rev, step_ratio, steps_per_sec, diameter):
    revs_per_sec = (steps_per_sec / steps_per_rev) * step_ratio
    speed = revs_per_sec * diameter * math.pi
    return speed
