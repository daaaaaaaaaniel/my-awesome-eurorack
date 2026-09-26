# Non-open-source eurorack modules ("DIY commercial" table)

Branch `claude/diy-commercial` (started 2026-09-26, d: "a new branch, where we'll be adding entries
for items they are primarily DIY but commercial/proprietary").

Table: `data/diy-commercial.tsv` - one row per module, kept apart from the open-source table
(`data/modules.tsv`) so its rules (licence, repo SHA, detector) do not apply here.

## Scope (updated 2026-09-26)

d: "the commercial table is meant for any eurorack modules that are not open source. "Commercial" was a
shorthand ... its ok to include modules with no active commercial retailer if the module is still
commercially licensed rather than open source." So: any eurorack DIY module whose design is not under an
open-source licence (proprietary, all rights reserved, private / non-commercial use only, or no licence
at all), sold or not. Explicitly open-source designs are flagged in `open_source` (North Coast) and
belong in the open-source table.

Format rule (d, 2026-09-26): "if the format is Kosmo or 5U or 4U or banana, then exclude it unless its
explicitly marked as being eurorack-compatible." Format not stated -> kept, with `format` = "?" / "not
stated".

**Exclusions are recorded** in `data/diy-commercial-excluded.tsv` (vendor, module, link, reason, checked
date) - check it before researching a maker again, so nothing is re-checked by accident.

### Original start list

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

## Batch 2 (2026-09-26, d: "add these in the commercial branch. note if any are explicitly open source")

Makers on the page without an asterisk that still sell PCBs or kits: North Coast Synthesis (own kits),
fonitronik (own PCBs), Ken Stone / CGS (PCBs by Elby Designs), YuSynth (PCBs by Soundtronics).

New column `open_source` (all rows): quotes any explicit licence statement, else "not stated".

- **Explicitly open source: North Coast Synthesis.** Maker page: "Most of the information here is free
  under the GNU GPL; check the individual documents for details of their licensing terms."
  (https://northcoastsynthesis.com/synth-diy-projects/). Per document: MSK 006 and MSK 011 GPL v3;
  MSK 010 "released under GPL"; MSK 014 firmware GPL3; MSK 007/008/009/013 pages "Fully open design -
  no lock-in"; MSK 012/015 not stated on the page (manuals probably GPL, not checked); MSK 002/003
  attribution-only permission ("happy to have people build and modify this design even commercially");
  Passive Multiples public domain. These 13 rows may belong in the open-source table instead.
- Not open source: Ken Stone / CGS via Elby ("© Copyright 2000. All rights reserved." on every Elby
  page), YuSynth ("can be used for private use only"; commercial use needs an agreement; Soundtronics
  pays Yves a share), Befaco (non-commercial CC-NC-SA per its About Us page).
- fonitronik: no licence statement found. modular.fonik.de pages could not be read (redirect loop);
  those rows rest on search titles / third-party shops. TH = Thomas Henry designs.

Skipped in batch 2:
- CGS01-CGS10 (Elby: "4U Modular Synthesizer modules") - not eurorack.
- YuSynth modules other than the Steiner VCF: yusynth.net offers "MU factor front plates" (5U) and
  Synthtopia calls the Soundtronics line "5U synth modules"; only the Steiner VCF page says "suitable
  either for 5U modulars or Eurorack modulars". The remaining ~27 YuSynth designs (VCO, ADSR, VCA,
  Moog / diode / ARP VCFs, ...) are left out as 5U - ask d if that is too strict.
- North Coast MSK 001 / 004 / 005 - unreleased or abandoned prototypes, nothing sold or published.
- fonitronik EFM section (Tom Gamble designs; schematics archive, "(c) EFM ele4music.com", PCBs sold
  off in 2007) and the MFOS Soundlab build (a synth, not a module).

## Euro-Serge (2026-09-26, d: "the Euro-Serge range are eurorack modules, so they shouldn't be excluded.
just mark them as licenses from Serge")

39 rows, vendor "Serge (Elby Designs Euro-Serge)", from https://www.elby-designs.com/webtek/euro-serge/euro-serge.htm
(ES01-ES114). `open_source` = no, made under licence from Serge ("All designs are produced under license
from Serge." - https://www.elby-designs.com/webtek/cgs/cgs.htm). CGS734 ASR, also listed there, already
has its row under Ken Stone (CGS). HP widths not read yet.

## Batch 3 (2026-09-26) - free-schematic sites and archives

Rows added: EFM / Tom Gamble boards from the fonitronik archive (66; schematics only, "(c) EFM
ele4music.com", PCBs not sold since 2007, no panel format), René Schmitz (20; no licence stated, format
not stated), Niklas Rönnberg (9; /diy/eurorack/ pages), haraldswerk (23; "free for private use only";
only the VCO section catalogued), oZoe.fr (28 eurorack modules; "(c) Jean Luc Lartigue"), Digisound 80
(15; site unreachable - everything but the names needs re-checking), Look Mum No Computer stripboard
projects (6; no panel format), YuSynth Minimoog VCF (explicit Eurorack version), Eddy Bergman (21 builds
that are eurorack-marked or have no stated format).

Excluded (see the excluded file): all Music From Outer Space (5U 3.5" x 8.75" panels), all soundbender
(Kosmo), 23 Look Mum No Computer Kosmo projects, 26 YuSynth modules (Synthesizers.com 5U; 13 of those
pages not individually checked), CGS 4U modules, CTorpin and Kosmodular Grid (Kosmo), General Guitar
Gadgets (pedals), oZoe modification notes, plus the batch 1-2 exclusions.

Open work: haraldswerk sections other than VCO; the rest of Eddy Bergman's ~69 build parts; Digisound 80
once the site loads; HP widths; the 13 unchecked YuSynth pages if anyone needs certainty.
