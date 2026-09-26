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

The draft was produced by `data/type_categories_draft.py` (ordered keyword
rules; all matching rules apply). Re-running it **overwrites the file**, so
once rows are marked `ok` the script must not be re-run blindly — edit the
TSV instead, or teach the script to keep `ok` rows.

## Vocabulary (27 tags)

| tag | covers |
|---|---|
| `oscillator` | VCO, DCO, wavetable / macro / FM / additive oscillators, sub-oscillators, Benjolin, APC |
| `filter` | VCF, fixed filters, comb, resonators, EQ |
| `lpg` | low-pass gates (vactrol etc.) — kept apart from `filter` and `vca` |
| `vca` | VCAs, duckers, compressors / dynamics |
| `envelope` | EG / ADSR / AR, function and slope generators, one-shot and burst generators |
| `lfo` | LFOs, function generators (also tagged `envelope`), "modulation source" |
| `sequencer` | step / gate / trigger / generative sequencers, Euclidean, arpeggiators, Turing Machines |
| `clock` | clocks, dividers, multipliers, counters, tap tempo, sync |
| `logic` | gates (AND/OR/…), comparators, Bernoulli gates, gate↔trigger, latches |
| `random` | S&H / T&H, random voltage, chaos, shift registers, probability |
| `noise` | noise sources (audio noise, not "Perlin noise" modulation) |
| `quantizer` | quantizers |
| `drum` | drum voices (808/909 style, kick/snare/hat…), drum sequencers |
| `effect` | delay, reverb, chorus/phaser/flanger, distortion/fuzz/overdrive, bitcrusher, granular, DSP multi-effects |
| `waveshaper` | wave folders, wave shapers, ring modulators, 4-quadrant multipliers, rectifiers |
| `mixer` | mixers, crossfaders, panners, matrix mixers |
| `utility` | attenuators/attenuverters, offsets, multiples, adders, slew, switches, converters, envelope followers, "utility" |
| `midi` | anything MIDI or USB-MIDI, OSC/CV interfaces |
| `io` | outputs, headphone amps, line/audio inputs, audio interfaces, preamps, pedal/footswitch interfaces |
| `power` | power supplies, bus boards, +5V adapters |
| `platform` | programmable / DSP platforms, dev boards (Daisy, Pico, RP2350, Teensy, OWL, Bela, norns) |
| `expander` | expanders and breakouts for a specific host module |
| `controller` | touch / fader / keyboard / gesture / sensor controllers, manual CV sources |
| `voice` | complete synth voices, sound generators, voice chips |
| `sampler` | samplers, sample players |
| `tool` | oscilloscopes, tuners, testers, meters, displays |
| `other` | motor/servo/solenoid/LED drivers, patch bays, cable testers, case hardware |

## Known soft spots in the draft (worth a look when reviewing)

- `function generator` → `envelope, lfo` every time; some are really one or the other.
- `shift register` → `random` (ASR / Turing-style); a plain digital shift register may not be.
- `counter` → `clock`; `counter / sequencer` rows also get `sequencer` from the word.
- Board-level words (`Teensy`, `Arduino platform`, `Raspberry Pi`) → `platform` even on a finished voice or sequencer.
- Two rows have an empty `type` → `UNMAPPED`; the site shows them under "not mapped".
