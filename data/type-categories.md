# Type categories — mapping `type` strings to site tags

`data/type-categories.tsv` maps every distinct value of the `type` column in
`data/modules.tsv` to one or more **tags** used by the website's Type filter.
It does not touch `modules.tsv` or the CSV; the raw `type` string is still
what the module page shows.

**Ruling (d, 2026-09-26 13:20): multi-function modules get multiple tags**,
not a single primary bucket. "S&H / Noise / Rectifier / Logic" is
`logic, noise, random, waveshaper`.

## Columns

| column | meaning |
|---|---|
| `type` | the exact raw string (one row per distinct value; the empty string is a row too) |
| `rows` | how many `modules.tsv` rows carry it |
| `tags` | comma-separated tags from the vocabulary below |
| `status` | `draft` = keyword-rule proposal, not reviewed · `ok` = d confirmed · `UNMAPPED` = no tag |
| `note` | why, when it isn't obvious |

The draft is produced by `data/type_categories_draft.py` (ordered keyword
rules; all matching rules apply). Re-running it keeps rows marked `ok` and redrafts the rest.

## Vocabulary (53 tags: ModularGrid's 48 + 5)

**d, 2026-09-28 01:18: use ModularGrid's categories**, exact names, so the site's Type filter reads like the
place most builders already browse. One concept = one tag; no synonyms. Five extras cover what ModularGrid has
no category for. The old 27 home-grown tags (oscillator, effect, io, platform, ...) are gone; `effect` split into
Delay / Reverb / Distortion / Fuzz / Phase Shifter / Pitch Shifter / Looper / Effect, `random` into Random /
Sample and Hold / Shift Register, `utility` into Attenuator / Polarizer / Precision Adder / Slew Limiter / Switch /
Utility, `clock` into Clock / Frequency Divider, `logic` into Logic / Comparator, `filter` into Filter / Resonator /
Equalizer, `vca` into VCA / Dynamics, `envelope` into Envelope Generator / Function Generator.

**ModularGrid (48):** Attenuator · Clock · Comparator · Delay · Distortion · Drum · Dynamics · Effect · Envelope
Follower · Envelope Generator · Equalizer · Expander · Filter · Frequency Divider · Function Generator · Fuzz · LFO ·
Logic · Looper · Low Pass Gate (LPG) · MIDI · Mixer · Noise · Oscillator · Panning · Phase Shifter · Pitch Shifter ·
Polarizer · Power · PreAmp · Precision Adder · Quantizer · Random · Resonator · Reverb · Ring Modulator · Sample and
Hold · Sampling · Sequencer · Shift Register · Slew Limiter · Switch · Synth Voice · Tube · Tuner · Utility · VCA ·
Waveshaper

**Extras (5):**

| tag | covers |
|---|---|
| `Audio I/O` | output modules, headphone amps, line out / line level, audio interfaces, pedal / footswitch interfaces (inputs are PreAmp) |
| `Controller` | keyboards, touch / fader / gesture controllers, drum pads, sensor and biodata interfaces, manual CV |
| `Dev Board / Platform` | programmable / scriptable platforms and dev boards (Daisy, Pico, RP2040/2350, Teensy, Arduino, Raspberry Pi, norns) |
| `Scope / Meter` | oscilloscopes, VU / level meters, spectrum analysers, testers, displays |
| `Other` | motor / servo / solenoid / LED-strip drivers, patch bays and matrices, case and mounting hardware |

The rules are in `data/type_categories_draft.py` (one regex per tag, all matching rules apply). Re-running it keeps
every row already marked `ok`.

## Known soft spots in the draft (worth a look when reviewing)

- `function generator` → `Function Generator` (and Envelope Generator when the string also says envelope/slope).
- Turing Machine → Sequencer + Random + Shift Register; a plain digital shift register gets only Shift Register.
- `counter` → Frequency Divider; `attenuverter` → Attenuator + Polarizer (ModularGrid's sense of Polarizer).
- Board-level words (`Teensy`, `Arduino`, `Raspberry Pi`) → Dev Board / Platform even on a finished voice or sequencer.
- Two rows have an empty `type` → `UNMAPPED`; the site shows them under "not mapped".
