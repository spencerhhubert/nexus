# The Nexus
A machine that sorts LEGO®
![the nexus logo](https://github.com/spencerhhubert/nexus/blob/main/assets/nexus_logo_original_res_green.png)

## Contributing and Bounties
The Nexus is not good yet. It's not reliable enough that I can legitmately use it, let alone suggest other people try to. We're totally open to PRs and collaboration, to get involved, join the [Discord server](https://discord.gg/N8FS2dN79p).

I'm also posting bounties to get the limiting problems solved. You should join the Discord first and we can talk as long as need be about how to attack these problems. Work from the bounties will be open sourced in this repo with the goal of making a good open source LEGO® sorting machine.
#### Mechanical
- Bigger and better feeder
    - $500
    - Requirements:
        - the user can dump a bin of pieces between the sizes of a 1x1 round plate and an 8x8 plate into the feeder, and the feeder automatically gets those pieces onto the conveyor belt one-by-one at a rate under 0.2 pieces/second
        - reliable enough that it can run for an hour without massive failure
        - largely off the shelf parts or 3D printable
#### Software
none right now

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

![demo of lego sorting machine gif](https://github.com/spencerhhubert/nexus/blob/main/assets/nexus%20demo%202023-4-8%2003.gif?raw=true)
![nexus lego sorting machine prototype 1 overview](https://raw.githubusercontent.com/spencerhhubert/nexus/main/assets/nexus_prototype0103.jpg)
![nexus lego sorting machine prototype 1 overview 2](https://raw.githubusercontent.com/spencerhhubert/nexus/main/assets/nexus_prototype0104.jpg)

## The state of this project
The Nexus is very much an alpha stage prototype. It is not yet a machine I would recommend anyone else try to build it. This will come in the future after more hardware and software bugs have been ironed out.

I'm planning another big push for a beta prototype this ~June where the focus will be on improving mechanical reliability and more real-to-life renders of digital pieces for classification training.

## Future goals and todo
- Make reliable
- Rate >~1 piece/second
- Low noise
- Open source CAD models
    - The physical design is where the most near-term work is. Some big design updates need to be made before it's reliable enough that I'd trust it to sort my entire collection and not janky enough that someone else would be able to recreate it
- Put entire host system on a smartphone
    - Good GPU, CPU, memory, camera, LED, UI, and reliability package per dollar
