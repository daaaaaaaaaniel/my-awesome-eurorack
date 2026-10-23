# Handwritten rows vs their stand-ins - review

Generated 2026-10-22 for d's review. Each handwritten row (the CSV's original rows) has a stand-in row in
`data/modules.tsv`, built from the repo the way every other row is. Below: only the fields where they differ, with
the stand-in's evidence. Nothing here changes the CSV yet (`data/handwritten-map.tsv`).

**37 differences** across 15 stand-ins.

**Decide per difference:** keep the stand-in's value (repo evidence), or keep the handwritten value (recorded as your ruling).

Also waiting: suessspeise's **VCF-1 (modified)** (CSV row 18) - a modified Skull & Circuits design in the DEFERRED repo
`suessspeise/sdiy` ([PDF](https://github.com/suessspeise/sdiy/blob/main/pdf/skull_vcf-1.pdf)); the original VCF-1 moved to the commercial table (c770). IN or OUT?

## Voxmachina · Cha Cha - CSV row 11 -> p1131

Repo: [musicdevghost/eurorack](https://github.com/musicdevghost/eurorack/tree/main/Cha%20Cha%20-%20VCLFO) @ `46ea69c`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| License | *(blank)* | `MIT` | LICENSE (repo root - none in module) "MIT License" |
| schematic? | `x` | [control_pcb.pdf](https://github.com/musicdevghost/eurorack/blob/main/Cha%20Cha%20-%20VCLFO/Schematics/control_pcb.pdf) |  |
| components | `THT` | *(blank)* | no .kicad_pcb, EasyEDA JSON, Eagle .brd, iBOM, machine-readable BOM or decisive gerbers in scope; gerbers have no paste layer (proves nothing) |

## Voxmachina · Kra Pao - CSV row 12 -> p1132

Repo: [musicdevghost/eurorack](https://github.com/musicdevghost/eurorack/tree/main/KRA%20PAO%20-%20RESONANT%20LOW%20PASS%20GATE) @ `46ea69c`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| creator | `Voxmachina` | `Thomas White + Voxmachina` | repo README table: 'Buttery resonant LPG/VCA/VCF based on the original design from Thomas White, core design used with permission'; Voxmachina from handwritten row 12 |
| License | *(blank)* | `MIT` | LICENSE (repo root - none in module) "MIT License" |
| schematic? | `x` | [control_board.pdf](https://github.com/musicdevghost/eurorack/blob/main/KRA%20PAO%20-%20RESONANT%20LOW%20PASS%20GATE/Schematics/control_board.pdf) |  |
| components | `THT` | *(blank)* | no .kicad_pcb, EasyEDA JSON, Eagle .brd, iBOM, machine-readable BOM or decisive gerbers in scope; gerbers have no paste layer (proves nothing) |

## Voxmachina · Leo Leo - CSV row 13 -> p1133

Repo: [musicdevghost/eurorack](https://github.com/musicdevghost/eurorack/tree/main/LEO%20LEO%20-%20MATRIX%20STAGE%20PROGRAMMER) @ `46ea69c`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| creator | `Voxmachina` | `Serge + Voxmachina` | README ''Leo Leo' ... is a programmer/sequencer module based on the first original Serge Programmer from the 70s'; Voxmachina from handwritten row 13 |
| License | *(blank)* | `MIT` | LICENSE (repo root - none in module) "MIT License" |
| schematic? | `x` | [control_pcb_schematic.pdf](https://github.com/musicdevghost/eurorack/blob/main/LEO%20LEO%20-%20MATRIX%20STAGE%20PROGRAMMER/Schematics/control_pcb_schematic.pdf) |  |
| components | `THT` | *(blank)* | no .kicad_pcb, EasyEDA JSON, Eagle .brd, iBOM, machine-readable BOM or decisive gerbers in scope; gerbers have no paste layer (proves nothing) |

## Voxmachina · Mak Mak - CSV row 14 -> p1134

Repo: [musicdevghost/eurorack](https://github.com/musicdevghost/eurorack/tree/main/Mak%20Mak%20-%20QUAD%20VCA-ATT-MIXER) @ `46ea69c`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| License | *(blank)* | `MIT` | LICENSE (repo root - none in module) "MIT License" |
| schematic? | `x` | [control_pcb.pdf](https://github.com/musicdevghost/eurorack/blob/main/Mak%20Mak%20-%20QUAD%20VCA-ATT-MIXER/Schematics/control_pcb.pdf) |  |
| components | `THT` | *(blank)* | no .kicad_pcb, EasyEDA JSON, Eagle .brd, iBOM, machine-readable BOM or decisive gerbers in scope; gerbers have no paste layer (proves nothing) |

## Voxmachina · Sigma - CSV row 15 -> p1135

Repo: [musicdevghost/eurorack](https://github.com/musicdevghost/eurorack/tree/main/Sigma%20-%20Function%20Generator) @ `46ea69c`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| Type of Module | `function generaor` | `function generator` | README 'Sigma - Function/Slope Generator'; handwritten row 15 (its typo 'generaor' corrected) |
| License | *(blank)* | `MIT` | LICENSE (repo root - none in module) "MIT License" |
| schematic? | `x` | [control_pcb.pdf](https://github.com/musicdevghost/eurorack/blob/main/Sigma%20-%20Function%20Generator/Schematics/control_pcb.pdf) |  |
| components | `THT` | *(blank)* | no .kicad_pcb, EasyEDA JSON, Eagle .brd, iBOM, machine-readable BOM or decisive gerbers in scope; gerbers have no paste layer (proves nothing) |

## Voxmachina · Tom Yum - CSV row 16 -> p1136

Repo: [musicdevghost/eurorack](https://github.com/musicdevghost/eurorack/tree/main/TOM%20YUM%20-%20VCO) @ `46ea69c`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| License | *(blank)* | `MIT` | LICENSE (repo root - none in module) "MIT License" |
| schematic? | `x` | [control_board.pdf](https://github.com/musicdevghost/eurorack/blob/main/TOM%20YUM%20-%20VCO/Schematics/control_board.pdf) |  |
| components | `THT` | *(blank)* | no .kicad_pcb, EasyEDA JSON, Eagle .brd, iBOM, machine-readable BOM or decisive gerbers in scope; gerbers have no paste layer (proves nothing) |

## Mutable Instruments + Karltron · Crimps - CSV row 10 -> p1137

Repo: [kstammits/crimps](https://github.com/kstammits/crimps/tree/main/crimps) @ `765b16f`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| License | *(blank)* | `CC BY-SA` | README 'it's cc-by-sa so copyleft' (no version stated) |
| schematic? | `x` | [schematic.121.pdf](https://github.com/kstammits/crimps/blob/main/crimps/schematic.121.pdf) |  |
| link | [crimps](https://github.com/kstammits/crimps) | [crimps](https://github.com/kstammits/crimps/tree/main/crimps) |  |

## Rene Schmitz + Divergent Waves · YASH (modified) - CSV row 4 -> p1138

Repo: [tpcarlson/synth-diy](https://github.com/tpcarlson/synth-diy/tree/main/yash) @ `6e7a119`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| schematic? | *(blank)* | `x` |  |

## York Modular · Vac LPG - CSV row 20 -> p1139

Repo: [yorkmodular/vaclpg-rev2](https://github.com/yorkmodular/vaclpg-rev2) @ `754c8d6`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| schematic? | `x` | [vaclpg-rev2-schematic.png](https://github.com/yorkmodular/vaclpg-rev2/blob/main/vaclpg-rev2-schematic.png) |  |
| layout | `n/a` | *(blank)* |  |
| link | [main](https://github.com/yorkmodular/vaclpg-rev2/tree/main) | [vaclpg-rev2](https://github.com/yorkmodular/vaclpg-rev2) |  |

## m0xpd · Flip - CSV row 22 -> p1140

Repo: [m0xpd/FLIP](https://github.com/m0xpd/FLIP) @ `3ea4e61`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| License | `Creative Commons CC BY-SA 4.0` | `CC BY-SA 4.0` | LICENSE.txt "Attribution-ShareAlike 4.0 International" |

## m0xpd · Encore! - CSV row 23 -> p1141

Repo: [m0xpd/encore](https://github.com/m0xpd/encore) @ `6f8dad9`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| License | `Creative Commons BY-SA 4.0` | `CC BY-SA 4.0` | LICENSE.txt "Attribution-ShareAlike 4.0 International" |

## thismatters · GateDelay - CSV row 24 -> p1142

Repo: [thismatters/EurorackGateDelay](https://github.com/thismatters/EurorackGateDelay) @ `21be914`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| schematic? | `x` | [gate-delay.pdf](https://github.com/thismatters/EurorackGateDelay/blob/main/gate-delay.pdf) |  |

## m0xpd · Sample and Hold - CSV row 6 -> p1143

Repo: [m0xpd/sample-and-hold](https://github.com/m0xpd/sample-and-hold/tree/main/PCB) @ `4b49a95`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| License | *(blank)* | `CC BY-SA 4.0` | LICENSE.txt "Attribution-ShareAlike 4.0 International" |

## YuSynth + thismatters · SampleHold - CSV row 8 -> p1144

Repo: [thismatters/EurorackSampleHold](https://github.com/thismatters/EurorackSampleHold) @ `1873475`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| schematic? | `x` | [output.pdf](https://github.com/thismatters/EurorackSampleHold/blob/main/output.pdf) |  |
| layout | `kidcad` | `kicad` |  |
| components | `SMD` | `both` | kicad footprints (files=1: sample-hold.kicad_pcb): smd=57 tht_passive=16 tht_to=1 tht_ic=0 (panel excluded) smd_ic=3 panel=21 |

## York Modular · Opto3.5 - CSV row 21 -> p1145

Repo: [yorkmodular/opto3.5](https://github.com/yorkmodular/opto3.5) @ `7f921bb`

| field | handwritten | stand-in | stand-in's evidence |
|---|---|---|---|
| schematic? | `x` | [opto35-schematic.png](https://github.com/yorkmodular/opto3.5/blob/main/opto35-schematic.png) |  |
| layout | `n/a` | *(blank)* |  |

