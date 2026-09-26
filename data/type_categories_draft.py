import csv, collections, re, sys
rows=list(csv.DictReader(open('data/modules.tsv'),delimiter='\t'))
counts=collections.Counter(r['type'] for r in rows)

# ordered (regex, tags). All matching rules apply; tags accumulate (d's ruling 2026-09-26 13:20: multiple tags).
R=[
 (r'\b(VCO|DCO|oscillator|Atari Punk|Benjolin|sub-?oscillator|sub-octave|wavetable)\b', 'oscillator'),
 (r'\b(VCF|filter|resonator|resonant equalizer|EQ)\b', 'filter'),
 (r'\bLPG\b', 'lpg'),
 (r'\b(VCA|ducker|ducking|dynamics|compressor)\b', 'vca'),
 (r'(?<!phase-)(?<!phase )\b(modulation|meta-modulator)\b', 'lfo'),
 (r'\b(envelope(?! follower)|EG|ADSR|function generator|slope generator|tidal modulator|segment generator|one-shot|burst generator)\b', 'envelope'),
 (r'\b(function generator|tidal modulator)\b', 'lfo'),
 (r'\bLFO\b', 'lfo'),
 (r'\b(sequencer|sequential gate|arpeggiator|Euclidean|Turing Machine|melody generator|pattern|keyframer)\b', 'sequencer'),
 (r'\b(clock|divider|counter|multiplier \(shuffling\)|tap tempo|Ableton Link|ratchet)\b', 'clock'),
 (r'\b(logic|comparator|gate to trigger|trigger to gate|gate delay|gate utility|Bernoulli|latch|flip)\b', 'logic'),
 (r'(?<!Perlin )\b(noise)\b', 'noise'),
 (r'\b(random|S&H|sample & hold|sample-and-hold|T&H|chaos|chaotic|Bernoulli|Turing Machine|Wogglebug|stochastic|Perlin|Geiger|probability|shift register)\b', 'random'),
 (r'\b(quantizer)\b', 'quantizer'),
 (r'\b(drum|kick|snare|hi-hat|clap|cymbal|toms|rimshot|percussion|TR-808|TR-909|TR82)\b', 'drum'),
 (r'\b(delay|reverb|chorus|flanger|phaser|phase shifter|distortion|fuzz|overdrive|drive|bitcrusher|granular|effects?|FV-1|multi-effect|harmonic enhancer|pitch shift|looping delay|echo|BBD|PT2399)\b', 'effect'),
 (r'\b(wave ?folder|wavefolding|waveshaper|wave shaper|wave distortion|ring modulator|multiplier \(4-quadrant|four-quadrant multiplier|rectifier|timbre|exponential converter)\b', 'waveshaper'),
 (r'\b(mixer|attenumixer|crossfader|panner|panning|scanner|mute)\b', 'mixer'),
 (r'\b(attenuator|attenuverter|attenuverting|offset|multiple|mult\b|adder|slew|switch|converter|polarizer|inverter|octave shift|semitone|transpose|glide|utility|distributor|voltage source|manual gate|voltage doubler|DAC|CV processor|CV utility|CV mixer|scale / offset|Kinks|Links|precision|envelope follower|trigger / gate generator|processor \(multimode)\b', 'utility'),
 (r'\b(MIDI|OSC-to-CV)\b', 'midi'),
 (r'\b(output|headphone|line input|audio input|line level|audio interface|preamp|microphone|instrument amplifier|I/O\)|pedal interface|footswitch|level shifter)\b', 'io'),
 (r'\b(power|bus board|PSU|busboard)\b', 'power'),
 (r'\b(platform|programmable|dev board|Daisy|Pico|RP2040|RP2350|Arduino platform|multifunction|scriptable|livecodeable|Raspberry Pi|Teensy|norns|sound computer|analogue computer)\b', 'platform'),
 (r'\b(expander|breakout|Teletype)\b', 'expander'),
 (r'\b(controller|touch|fader controller|keyboard|gesture|drum pad|drumpad|biodata|heartbeat|sensor|CV interface|voltage source \(4 manual)\b', 'controller'),
 (r'\b(synth voice|synthesizer \(voice|voice \(|voice chip|sound generator|sound module|engine sound|modal synth|meta-modulator|chord organ|TB-303 voice|x0x)\b', 'voice'),
 (r'\b(sampler|sample player|sample streamer|sample playback)\b', 'sampler'),
 (r'\b(oscilloscope|tuner|tester|meter|VU meter|spectrum|display)\b', 'tool'),
 (r'\b(motor|servo|solenoid|LED strip|pyrotechnic|igniter|patch bay|patch matrix|cable|computer mount|case-to-case|breadboard|mount)\b', 'other'),
]
out=[]
for t,n in sorted(counts.items(), key=lambda kv: kv[0].lower()):
    tags=[]
    for rx,tag in R:
        if re.search(rx,t,re.I) and tag not in tags: tags.append(tag)
    out.append((t,n,tags))
un=[(t,n) for t,n,tags in out if not tags and t]
print('unmatched',len(un)); 
for t,n in un: print(' ',n,t)
if len(sys.argv)>1:
    with open(sys.argv[1],'w',newline='') as f:
        w=csv.writer(f,delimiter='\t',lineterminator='\n'); w.writerow(['type','rows','tags','status','note'])
        for t,n,tags in out: w.writerow([t,n,', '.join(tags),'draft' if tags else 'UNMAPPED',''])
