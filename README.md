# The Nexus
A machine that sorts LEGO®

![demo of lego sorting machine gif](https://github.com/spencerhhubert/nexus/blob/main/assets/nexus%20demo%202023-4-8%2003.gif?raw=true)

## Key features
- Arbitrary Versatility 
    - Dump in a pile of LEGO® pieces, ranging from 1x1 studs to 8x8 plates
    - Identify each piece as precisely what it is, BrickLink ID and color
    - Sort pieces according to not-annoying-to-setup user-defined "profiles"
        - Want to sort by BrickLink category? Want to sort by color? Something in between? All combinations are possible
- Extensible
    - Current architecture supports expanding to over 900 bins with no changes to the overall design or electronics
- Reproducible 
    - Primarily constructed 3D printable parts, 2020 aluminum extrusion, and affordable, easily obtained motors/electronics

![nexus lego sorting machine prototype 1 overview](https://raw.githubusercontent.com/spencerhhubert/nexus/main/assets/nexus_prototype0103.jpg)
![nexus lego sorting machine prototype 1 overview 2](https://raw.githubusercontent.com/spencerhhubert/nexus/main/assets/nexus_prototype0104.jpg)

## The state of this project
The Nexus is very much an alpha stage prototype. It is not yet a machine I would recommend anyone else try to build it. This will come in the future after more hardware and software bugs have been ironed out.

## Future goals and todo
- Make reliable
- Rate >~1 piece/second
- Low noise
- Open source CAD models
    - The physical design is where the most near-term work is. Some big design updates need to be made before it's reliable enough that I'd trust it to sort my entire collection and not janky enough that someone else would be able to recreate it
- Put entire host system on a smartphone
    - Good GPU, CPU, memory, camera, LED, UI, and reliability package per dollar
