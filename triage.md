# Triage — all 331 repos in the star list

Generated from `data/triage.tsv`. Nothing is discarded: every repo that does not
become a CSV row appears here with the reason.

**The exclusion test is the absence of hardware design files, never the presence of firmware.**
A description can put a repo *in*, but never on its own take one *out* — every exclusion below
was checked against the repo's actual file tree.

| bucket | count | meaning |
|---|---|---|
| IN | 289 | design files present; expands to CSV rows |
| REVIEW | 21 | hardware only as archives/documents, or scope questions — needs a ruling |
| OUT | 21 | no design files anywhere in the tree |

Projected rows from IN repos: **~1504** (mechanical count of module directories — an upper bound; see caveats in the review notes).

## OUT — no design files in the tree

| repo | reason | description |
|---|---|---|
| `newdigate/eurorack-awesome` | link list, no design files | awesome eurorack diy and opensource |
| `apfaudio/eurorack-pmod-usb-soundcard` | firmware/software only, no design files | Example of using a eurorack-pmod as an 8-channel (4in + 4out) USB soun |
| `recursinging/kxmx_bluemchen` | firmware/software only, no design files | A 4hp Eurorack module built on the Electrosmith Daisy Seed |
| `4ms/minipeg` | firmware/software only, no design files | Firmware for the MiniPEG Eurorack module |
| `benjiaomodular/EuroPanelMaker` | case/panel/rail generator - out of scope per conventions | Generate Eurorack panels using OpenSCAD |
| `benjiaomodular/EuroRailMaker` | case/panel/rail generator - out of scope per conventions | A library for making custom length Eurorack rails in OpenSCAD |
| `neutral-labs/pip` | firmware/software only, no design files | NONE |
| `bastl-instruments/eurorack` | firmware/software only, no design files | Legacy Eurorack projects' code archive. |
| `mortonkopf/Teensy-eurorack-rotating-step-divider` | firmware/software only, no design files | Simple sketch for using Teensy 3.* as eurorack rotating step divider |
| `miotislucifugis/Telex_teensy4` | firmware/software only, no design files | An adaptation of bpcmusic's Telex Teletype Expanders for Teensy 4 |
| `rppicomidi/midi2usbhost` | firmware/software only, no design files | Make a Raspberry Pi Pico a USB Host to bridge modern USB MIDI to old s |
| `finnglink/rackforge` | case/panel/rail generator - out of scope per conventions | A fully parametric 3D printable eurorack case |
| `cctvfm/covenlfo` | firmware/software only, no design files | Eurorack LFO Module based on SAMD21/ Xiao |
| `CubuSynth/6xlevel-doc` | single build-guide PDF only, no design files - guide may contain a schematic, REVIEW | NONE |
| `mxmxmx/telefuncen` | README only, no files - hardware may live elsewhere, REVIEW | 4 channel quantizer |
| `fitzgreyve/CVtoMIDI` | firmware/software only, no design files | Arduino sketches for the Fitzgreyve CV-to-MIDI eurorack module |
| `Wesemane-Industries/eurocase` | case/panel/rail generator - out of scope per conventions | DIY Eurorack / Modular synthesizer case |
| `DatanoiseTV/PicoADK-Eurorack-Module` | README only, no files - hardware may live elsewhere, REVIEW | A Eurorack Module with 8x CV ins, 6 potentiometers, OLED screen, and 3 |
| `SdkcInstruments/Bootleg1.1` | README + product image only, no design files | Bootleg #1.1 Dual Slope Generator+ |
| `ghostintranslation/drone` | firmware + user manual only, no design files | Eurorack multi-algorithm drone module |
| `glitched0xff/Midi2euroPiW` | firmware/software only, no design files | Send MIDI to Cvs from wifi |

## REVIEW — needs a ruling

| repo | reason | dirs | description |
|---|---|---|---|
| `VoltageFoundryMod/ForgeSeries-CLK` | hardware present only as archives or documents - needs a look | 0 | Eurorack collection of modules |
| `Mental-Noise/Axon` | hardware present only as archives or documents - needs a look | 0 | Arduino based MIDI to CV Eurorack Module |
| `Mental-Noise/Synapse` | hardware present only as archives or documents - needs a look | 0 | Arduino based CV to MIDI Eurorack module to control external |
| `SonicPotions/Penrose` | hardware present only as archives or documents - needs a look | 0 | Penrose eurorack Quantizer |
| `westlicht/performer` | hardware present only as archives or documents - needs a look | 0 | PER\|FORMER Eurorack Sequencer |
| `ohmtech-rdi/eurorack-blocks` | framework that GENERATES hardware from C++/Faust; dirs are samples/boards, not shipped modules | 81 | Software to Hardware Prototyping for Eurorack using C++, Max |
| `loglow/Tall-Dog-Public` | hardware present only as archives or documents - needs a look | 0 | This is the public repository for Tall Dog Electronics. |
| `MartijnVerhallen/Audio-Documentation` | hardware present only as archives or documents - needs a look | 0 | Documentation for audio projects |
| `MartijnVerhallen/Video-Documentation` | hardware present only as archives or documents - needs a look | 0 | Documentation for video projects |
| `OmsInSerial/Eurorack` | hardware present only as archives or documents - needs a look | 0 | NONE |
| `pixiemars/GMSNPure` | hardware present only as archives or documents - needs a look | 0 | Schematics, BOMS and build guides for GMSN pure, incomplete, |
| `Fihdi/Eurorack` | hardware present only as archives or documents - needs a look | 0 | Schematics and PCBs for my Eurorack modules |
| `erica-synths/diy-eurorack` | hardware present only as archives or documents - needs a look | 0 | Erica Synths DIY Eurorack Modules |
| `BastianSPCTRL/COEUR` | hardware present only as archives or documents - needs a look | 0 | 1u version of Tom Whitwell's / Music Thing Modular's Startup |
| `suessspeise/sdiy` | hardware present only as archives or documents - needs a look | 0 | schematics and protoboard layouts for synthesizer modules |
| `odeliy/schema-cave` | hardware present only as archives or documents - needs a look | 0 | Various old schematics of retired and unreleased modules. |
| `retoid/Module-Panel-Templates` | panel templates only - panels are out of scope, but verify | 62 | Modular Synthesizer Panel Templates |
| `cob333/Pico-Eurorack` | hardware present only as archives or documents - needs a look | 0 | Firmware repository for Pico / PicoFX Eurorack modules, with |
| `cob333/PicoPro-Eurorack` | hardware present only as archives or documents - needs a look | 0 | Firmware repository for PicoPro Eurorack modules. |
| `samjkent/modular-mixer` | hardware present only as archives or documents - needs a look | 0 | NONE |
| `Mental-Noise/Thal` | hardware present only as archives or documents - needs a look | 0 | Thal - Mixer and Output Eurorack Module |

## IN — top 20 by projected row count

| repo | module dirs | eda | description |
|---|---|---|---|
| `diyelectromusic/sdemp_pcbs` | 70 |  | PCB designs for SDEMProjects |
| `RebelTechnology/RebelTechnology` | 62 | eagle | Repository for Rebel Technology modules and prototypes |
| `BruteClaw/Analog-Synth` | 60 | kicad | EuroRack sytle analog synthasizer designs |
| `ThisIsNotRocketScience/Eurorack-Modules` | 55 | kicad,eagle,diptrace | This is not Rocket Science presents: Eurorack modular s |
| `spielhuus/elektrophon` | 44 | kicad,diylc | Modular analog electro acoustic noise machine |
| `bummbummgarage/bummbummgarage.github.io` | 41 | diylc,easyeda | NONE |
| `mzuelch/CATs-Eurosynth` | 39 | kicad | Analog Synth Eurorack Modules |
| `VincentPeters/Diy-Synth-Eurorack` | 38 | kicad,fritzing,diylc | Collection of files about diy synth making, mostly euro |
| `microresearch/allcolours` | 36 | kicad | all the colours of the noise |
| `Syntonie/documentation` | 35 | diptrace | NONE |
| `vauxflores/Electronics` | 33 | eagle | NONE |
| `Deftaudio/Midi-boards` | 32 | kicad | MIDI projects, thru boxes, mergers, sync |
| `tkilla64/eurorack` | 29 |  | Eurorack DIY projects |
| `AidanTek/ElectricNoodleBox` | 29 | eagle | Open Source Hardware from/with Electric Noodle Box |
| `tpcarlson/synth-diy` | 27 | kicad | Mostly Eurorack projects |
| `pichenettes/eurorack` | 27 | eagle | Eurorack modules |
| `FuturePresentLabs/mia-eurorack` | 27 | kicad,eagle | MIA - Mutable Instruments Eurorack modules |
| `PierreIsCoding/sdiy` | 23 |  | Synth DIY projects |
| `supersynthesis/eurorack` | 22 | diptrace | Schematics of Super Synthesis production modules |
| `clacktronics/EuroClack_BYOM_Modules` | 22 | kicad | NONE |

_Full data, including all 289 IN repos, in `data/triage.tsv`._
