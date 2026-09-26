# DIY but commercial / proprietary modules

Branch `claude/diy-commercial` (started 2026-09-26, d: "a new branch, where we'll be adding entries
for items they are primarily DIY but commercial/proprietary").

Table: `data/diy-commercial.tsv` - one row per module, kept apart from the open-source table
(`data/modules.tsv`) so its rules (licence, repo SHA, detector) do not apply here.

## Scope

- Start list: https://analogoutputblog.wordpress.com/synth-diy-repositories/ - the vendors it marks
  with an asterisk ("Some (*) also are vendors of PCBs and panels or kits but include schematics in
  the online documentation"): AI Synthesis, Barton Musical Circuits, Befaco, Look Mum No Computer,
  Music Thing Modular, Nonlinear Circuits, Winterbloom.
- Left out: Music Thing Modular and Winterbloom - the page itself calls them "explicitly open source"
  (they belong in the open-source table).
- Left out (d, 2026-09-26): circuits explicitly not in eurorack format (4U, 5U, banana, and Kosmo).
  1U tiles (Intellijel / Befaco 1U) are kept, marked in `format`.
- Look Mum No Computer: only the 4 projects stated as eurorack are rows. Stated Kosmo (skipped):
  1007 MIDIMUSO, 1114 Funky Filter, 1181 Dual VCA, 1183/1184 Quad VCA Mixer, 2001 Keyboard Sequencer,
  2399 Triple Splashback, 4051 Plexquencer (schematic file named Kosmo), 4710 Safety Valve,
  5000 Kosmo Minis, Performance Filter 1112/1113, VCLFO10. Format not stated on their pages (not rows
  yet, most LMNC projects are Kosmo): 1008 MIDI 2 Trig, 1148 Quad LFO, 1153 Bounce, 1157 Mini ADSR,
  1158 VCADSR, 1161 Buffered Multiple, 1163 Mini Mixer, 1171 OBA, 1221 Oscillator Expander,
  1222 Performance VCO, 2221 Crosfobermordulator, 2700 Twin T Drummer, Simple LPF, Simple CEM3340 VCO,
  Simplest Oscillator, Simple Envelope Generator, Valve Distorting VCA, Mixer. 2000 Megadrone is a
  standalone synth.
- Befaco: its About Us page says the designs are published under "CC-NC-SA" (non-commercial); the
  GitHub repos are mostly firmware. Not rows: Oneiroi POD (case / desktop unit), Bela Pepper
  (third-party parts kit). ARK, CV Thing and Random8 are on befaco.org but not in the DIY kit shop.
- Nonlinear Circuits: PARTS (component packs) is not a module. Barton: "7805 to LM317" is a
  regulator item, not a module.

## Columns

`type_confidence` says where `type` comes from:
- `vendor page` - the module's own page on the vendor site
- `vendor listing` - the vendor's shop / index / product title
- `secondary source` - ModularGrid (MG) or MATRIXSYNTH (MS) text, quoted in `type_basis`
- `name only` - guessed from the module name; check before relying on it
- `unknown` - function not found yet (`type` = ?)

`format` is eurorack HP where a source states it; `?` where not. Barton widths marked "(title)" or
"(URL)" come from the project title / URL only.

## Open work

- 39 rows with `type` unknown and 92 guessed from the name (mostly Nonlinear Circuits and Barton):
  open each module page.
- HP missing for most Barton and Befaco rows.
- Check overlap with the open-source table (e.g. Befaco, LMNC, NLC modules already rowed there).
