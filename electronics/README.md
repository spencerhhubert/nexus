# basically Sorter - Electronics
This repository contains all electronics-related assets for the project, including schematics, PCB designs, 3D models, and wire harness definitions. The workflow is designed to be fully open source (see licenses for details), reproducible, and compatible with common free tools.

---

## Overview
This folder holds all materials needed to build, modify, or inspect the project's electronics systems. It includes:
- **KiCad** projects for schematics and PCB layout
- **Onshape** 3D CAD models (this is linked to the Main project onshape doc)
- **WireViz** YAML harness definitions 
- Information on how to submit to each section will be provided in the respective subdirectory README files.

---

## KiCad Schematics & PCB
All schematics and PCB files are created using **KiCad**.

### Contents:
- `/kicad/` directory contains the KiCad project
- PCB and schematic source files (`.kicad_sch`, `.kicad_pcb`)
- Symbol and footprint libraries

### Requirements:
- KiCad **v7 or later** (recommended since we use tools in KiCad that follow this requirement)

---

## 3D Models (Onshape) (Onshape)
Mechanical components, board outlines, enclosures, and mounting hardware are modeled in **Onshape**.

### Access:
- Public Onshape document link located in `/3d/README.md`
- Exports (`.step`, `.stl`) are mirrored in the repo for convenience

### Notes:
- Any modifications should be made in Onshape and then re-exported

---

## Wire Harness Generation
This project uses the **command‑line wire harness generator** used by *LumenPnP* (project: **`wireviz`**—a YAML‑based wiring harness generator).

### Tool Used:
- **WireViz** (https://github.com/wireviz/wireviz)

### Features:
- Generates wiring diagrams from YAML files
- Produces PDF, PNG, and interactive outputs

---

##  Repository Structure
```
/electronics
   ├── kicad/               # Schematics and PCB
   ├── 3d/                  # 3D models (Onshape exports)
   ├── wire_harness/        # WireViz YAML harness definitions
   ├── assets/              # Images, diagrams, renders
   ├── bom/                 # Top level Bill of Material for all electronics
   └── README.md            # This file
```

---
## License
See the Liscense information in the main project.

---

For questions or contributions, please open an issue or pull request in the main repository.
