"""Draft tags for every distinct `type` string -> data/type-categories.tsv (website Type filter).

Vocabulary (d, 2026-09-28 01:18): ModularGrid's 48 categories, exact names, plus five tags for things ModularGrid
has no category for (Audio I/O, Controller, Dev Board / Platform, Scope / Meter, Other). One concept, one tag.
Multi-function modules get several tags (d, 2026-09-26 13:20). Ordered regex rules; all matching rules apply.
Rows already marked `ok` in the existing TSV are kept as they are (d's review is never overwritten).
    python3 data/type_categories_draft.py data/type-categories.tsv
"""
import csv, collections, re, sys, os
rows = list(csv.DictReader(open('data/modules.tsv', encoding='utf-8'), delimiter='\t'))
counts = collections.Counter(r['type'] for r in rows)

MG = ["Attenuator", "Clock", "Comparator", "Delay", "Distortion", "Drum", "Dynamics", "Effect", "Envelope Follower",
      "Envelope Generator", "Equalizer", "Expander", "Filter", "Frequency Divider", "Function Generator", "Fuzz", "LFO",
      "Logic", "Looper", "Low Pass Gate (LPG)", "MIDI", "Mixer", "Noise", "Oscillator", "Panning", "Phase Shifter",
      "Pitch Shifter", "Polarizer", "Power", "PreAmp", "Precision Adder", "Quantizer", "Random", "Resonator", "Reverb",
      "Ring Modulator", "Sample and Hold", "Sampling", "Sequencer", "Shift Register", "Slew Limiter", "Switch",
      "Synth Voice", "Tube", "Tuner", "Utility", "VCA", "Waveshaper"]
EXTRA = ["Audio I/O", "Controller", "Dev Board / Platform", "Scope / Meter", "Other"]
VOCAB = MG + EXTRA

R = [
 (r'\b(VCO|DCO|oscillator|Atari Punk|APC|Benjolin|sub-?oscillator|sub-octave|wavetable|drone)\b', 'Oscillator'),
 (r'\b(VCF|filter|formant)\b', 'Filter'),
 (r'\b(resonator|resonant body|modal|Karplus|comb)\b', 'Resonator'),
 (r'\b(EQ|equali[sz]er|resonant equalizer|tilt)\b', 'Equalizer'),
 (r'\b(LPG|low[- ]pass gate|lowpass gate)\b', 'Low Pass Gate (LPG)'),
 (r'\bVCA\b|\bamplifier \(voltage', 'VCA'),
 (r'\b(compressor|limiter|ducker|ducking|dynamics|sidechain|noise gate|expander \(dynamics)\b', 'Dynamics'),
 (r'\benvelope follower\b', 'Envelope Follower'),
 (r'\b(envelope(?! follower)|EG|ADSR|ADR|AHDSR|AR|AD|attack|decay|slope generator|one-shot|burst generator|segment generator)\b', 'Envelope Generator'),
 (r'\b(function generator|slope generator|tidal modulator|Maths)\b', 'Function Generator'),
 (r'\b(LFO|modulation source|modulator \(LFO|meta-modulator)\b|(?<!phase-)(?<!phase )(?<!ring )\bmodulation\b', 'LFO'),
 (r'\b(sequencer|sequential gate|arpeggiator|Euclidean|Turing Machine|melody generator|pattern|keyframer|step)\b', 'Sequencer'),
 (r'\b(clock|tap tempo|Ableton Link|ratchet|tempo|metronome|BPM)\b', 'Clock'),
 (r'\b(divider|(?<!Geiger )counter|frequency division|octave divider)\b', 'Frequency Divider'),
 (r'\b(logic|gate to trigger|trigger to gate|gate delay|gate utility|Bernoulli|latch|flip-?flop|boolean)\b|(?-i:\b(AND|OR|XOR|NOT|NAND|NOR)\b)', 'Logic'),
 (r'\b(comparator|window comparator|schmitt)\b', 'Comparator'),
 (r'(?<!Perlin )\bnoise\b(?! gate)', 'Noise'),
 (r'\b(random|chaos|chaotic|Wogglebug|stochastic|Perlin|Geiger|probability|Bernoulli|Turing Machine|uncertainty)\b', 'Random'),
 (r'\b(S&H|S/H|sample ?& ?hold|sample[- ]and[- ]hold|T&H|track ?& ?hold|track[- ]and[- ]hold)\b', 'Sample and Hold'),
 (r'\b(shift register|ASR|Turing Machine|Rungler)\b', 'Shift Register'),
 (r'\bquanti[sz]er\b', 'Quantizer'),
 (r'\b(drum|kick|snare|hi-?hat|clap|cymbal|toms?|rimshot|percussion|TR-?808|TR-?909|TR82|cowbell|bass drum)\b', 'Drum'),
 (r'(?<!gate )\b(delay|echo|BBD|PT2399)\b', 'Delay'),
 (r'\b(reverb|spring)\b', 'Reverb'),
 (r'\b(effects?|FX|FV-1|multi-effect|chorus|flanger|bitcrusher|bit crusher|granular|harmonic enhancer|vibrato|tremolo|freeze)\b', 'Effect'),
 (r'\b(phaser|phase shifter)\b', 'Phase Shifter'),
 (r'(?<!phase )\b(distortion|overdrive|saturat\w*)\b|(?<!motor )(?<!LED )\bdrive\b(?!r)', 'Distortion'),
 (r'\bfuzz\b', 'Fuzz'),
 (r'\b(pitch shift\w*|harmoni[sz]er|frequency shifter)\b', 'Pitch Shifter'),
 (r'\b(looper|looping)\b', 'Looper'),
 (r'\b(wave ?folder|wavefold\w*|waveshaper|wave shaper|wave distortion|timbre|rectifier|exponential converter)\b', 'Waveshaper'),
 (r'\b(ring mod\w*|4-quadrant|four-quadrant|multiplier \(4)', 'Ring Modulator'),
 (r'\b(mixer|attenumixer|crossfader|cross-?fade|matrix mixer|summing)\b', 'Mixer'),
 (r'\b(panner|panning|pan|stereo field|autopan)\b', 'Panning'),
 (r'\b(attenuator|attenuverter|attenuverting|attenuation|attenumixer)\b', 'Attenuator'),
 (r'\b(polari[sz]er|attenuverter|attenuverting)\b', 'Polarizer'),
 (r'\b(precision adder|adder|octave shift|transpos\w*|semitone)\b', 'Precision Adder'),
 (r'\b(slew|glide|portamento|lag)\b', 'Slew Limiter'),
 (r'(?<!range )\b(switch|sequential switch|mute|router|routing|selector)\b', 'Switch'),
 (r'\b(multiple|mult|offset|inverter|converter|distributor|utility|voltage source|DAC|level shifter|buffer|voltage doubler|gate generator|manual gate|CV processor)\b', 'Utility'),
 (r'\b(MIDI|OSC-to-CV|CV-to-OSC)\b', 'MIDI'),
 (r'\b(preamp|pre-amp|microphone|instrument amplifier|line input|audio input|external input|input stage)\b', 'PreAmp'),
 (r'\b(power|bus ?board|PSU|busboard|\+5V|power supply)\b', 'Power'),
 (r'\b(expander|breakout|Teletype)\b', 'Expander'),
 (r'\b(synth voice|synthesizer \(voice|voice \(|voice chip|sound generator|sound module|engine sound|chord organ|TB-303|303 voice|x0x|complete voice|mono ?synth)\b', 'Synth Voice'),
 (r'\b(sampler|sample player|sample streamer|sample playback|sampling|ISD)\b', 'Sampling'),
 (r'\b(tube|valve|12AX7|pentode|triode|vacuum)\b', 'Tube'),
 (r'\btuner\b', 'Tuner'),
 # extras - no ModularGrid category
 (r'^outputs?\b|\b(output module|audio output|stereo output|master output|output stage|output amp\w*|headphone\w*|line out|line level|audio interface|I/O|pedal interface|footswitch|USB audio)\b', 'Audio I/O'),
 (r'\b(controller|touch|fader controller|keyboard|gesture|drum pad|drumpad|biodata|heartbeat|sensor|CV interface|joystick|manual CV|manual voltage)\b', 'Controller'),
 (r'\b(platform|programmable|dev board|Daisy|Pico|RP2040|RP2350|Arduino|multifunction|scriptable|livecodeable|Raspberry Pi|Teensy|norns|sound computer|analogue computer)\b', 'Dev Board / Platform'),
 (r'\b(oscilloscope|scope|meter|VU|spectrum analy[sz]er|tester|visuali[sz]er)\b|^display\b', 'Scope / Meter'),
 (r'\b(motor|servo|solenoid|LED strip|pyrotechnic|igniter|patch bay|patch matrix|cable|computer mount|case-to-case|breadboard|mount)\b', 'Other'),
]
assert all(t in VOCAB for _, t in R), [t for _, t in R if t not in VOCAB]
assert len(set(VOCAB)) == len(VOCAB)

keep = {}
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    for r in csv.DictReader(open(sys.argv[1], encoding='utf-8'), delimiter='\t'):
        if r.get('status') == 'ok': keep[r['type']] = r
out = []
for t, n in sorted(counts.items(), key=lambda kv: kv[0].lower()):
    if t in keep:
        k = keep[t]; out.append((t, n, k['tags'], 'ok', k.get('note', ''))); continue
    tags = []
    for rx, tag in R:
        if re.search(rx, t, re.I) and tag not in tags: tags.append(tag)
    out.append((t, n, ', '.join(tags), 'draft' if tags else ('UNMAPPED'), ''))
un = [(t, n) for t, n, tags, st, _ in out if not tags and t]
print('types', len(out), '| unmatched', len(un))
for t, n in un[:40]: print('  ', n, t)
if len(sys.argv) > 1:
    with open(sys.argv[1], 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(['type', 'rows', 'tags', 'status', 'note'])
        for row in out: w.writerow(row)
