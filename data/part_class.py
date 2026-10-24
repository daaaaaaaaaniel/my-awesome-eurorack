#!/usr/bin/env python3
"""One part classifier for every footprint source (detector v27, 2026-10-24; tested in STATE.md "Shared-classifier test").
Before v27 the KiCad, EasyEDA, Eagle and iBOM paths of components.sh each kept their own panel-name list, IC test and
not-a-part filter; the lists drifted apart and Eagle misread ~19 rows. Every path now sends its parts here.

stdin: one part per line, name<TAB>ref<TAB>mount<TAB>pads[<TAB>value] - from kicad_parts.py, easyeda_parts.py,
eagle_parts.py or ibom_parts.py. mount is smd | tht | th | none | '' ('' = no pad data, e.g. EasyEDA schematic JSON).
stdout: one line, "smd tht tht_ic tht_to smd_ic panel panel_smd unknown<TAB>unknown names" (smd includes smd_ic;
panel counts panel parts, mechanical parts and non-parts excluded). With -v, first one line per part: category<TAB>part.

Order of tests, the same for every source:
 1. not a part: no pads, or one pad; holes, fiducials, logos, test points, net ties, vias, solder / wire / touch pads,
    jumpers (by name, or reference TP / FID / MH / H / JP / REF**), board outlines (a footprint named *pcb* / outline);
 2. mechanical: heatsinks and known_parts.tsv 'mechanical' numbers (v18);
 3. THT IC: a package that SAYS DIP / DIL / SIP plus a pin count (not SIL: a pin header in older libraries), socketed or not, never on a panel reference
    (ruling 2026-09-26: only DIP/SIP are THT ICs). Checked before panel, so a DIP socket footprint still counts;
 4. panel hardware: one name list (pots, faders, trimmers, jacks, switches, buttons, encoders, LEDs, displays,
    connectors, headers, sockets, power headers, dev boards, knobs, screws), tested on the footprint name AND the value,
    or a panel reference (J, SW, S, RV, VR, LED, BAR, DS, BTN, P, CN, CON, FADE, FDR). An SMD panel part is panel_smd:
    it means SMD soldering, so components.sh counts it as "SMD present" (v22 already refused THT for such boards);
 5. mounting from the pads; with no pad data, from the package name (SMD / THT patterns); neither -> unknown;
 6. smd: smd_ic when the package is SO / SOIC / SSOP / TSSOP / QFN / QFP / MSOP (a sub-count, never a verdict input);
 7. tht: TO-92 / TO-220 / TO-3 by name -> tht_to (never decides); a Q part, or a U/IC part with 3 pads, whose package
    names nothing -> tht_to; anything else -> one THT part toward the limit of 5. A through-hole part whose package does
    not say DIP/SIP is never a THT IC (user, 2026-10-24, on p1111's 7-segment display: such a part never decides SMD vs
    both) - DC-DC bricks, tubes and unnamed U parts count as one THT part."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
I = re.I
NOTPART = re.compile(r"(^|[^a-z])wpad|loch|schraub|bohrung|(^|[:_])sj[-_]?[0-9]|fiducial|logo|symbol|solder_?(wire_?)?(jumper|bridge|pad|point)|"
                     r"wire_?pad|touch_?pad|(^|[^a-z])jumper|test_?point|testpoint|test-|mount(ing)?_?hole|(^|[^a-z])hole|net_?tie|(^|:)frame|"
                     r"docu|weee|rohs|oshw|(^|[^a-z])slot|(^|[^a-z])via([^a-z]|$)|^none$", I)
OUTLINE = re.compile(r"pcb|outline", I)   # tested on the footprint's own name, not its library ('PCB_Lib:R0805' is a part)
NOTREF = re.compile(r"^(REF\*\*|TP|FID|MH|H|LOGO|G|NT|JP)[0-9*]", I)
DEVB = r"arduino|teensy|daisy|(^|[^a-z])pico|esp32|blue_?pill|breakout|module:"   # dev boards: mounted on headers
PANEL = re.compile(r"(^|[^a-z])hdr|mhps|res-adj|adj-res|(^|[^a-z])pt[abfl][0-9]{2}|pj[-_ ]?3[0-9]{2}|piher|potentiometer|(^|[^a-z])pot([^a-z]|$)|"
                   r"pots?_|_pot|trim(mer|pot)?|(^|[^0-9])(3296|3362|3386)[a-z0-9]|rd90[0-9]|rk0?9|alps|fader|slide|"
                   r"jack|pj-?3|pj-|thonk|(^|[^a-z])sw[-_]|switch|button|tact|key|encoder|"
                   r"(^|[^a-z])leds?([^a-z]|$)|led([^a-z]|$)|led_|bar_?graph|hdsp|display|oled|lcd|"
                   r"connector|(^|[^a-z])conn?([^a-z]|$)|con-|terminal|header|pinhd|pin_?socket|socket|idc|box_?header|jst|usb|midi|"
                   r"(^|[:_ -])eurorack[-_ ]?(power|pwr|bus|hdr|header|conn|[0-9])|eurorack_[0-9]+hp|power_?(16|10)|europwr|euro_power|board_?conv|"
                   r":[0-9]+x[0-9]+|(^|_)[12]x[0-9]+|(^|[^a-z])sil[-_ ]?[0-9]|(^|[^a-z])(fe|ma)[0-9]{2}(-[0-9])?([^0-9]|$)|pak[0-9]{3}|knob|torx|screw|standoff|nut([^a-z]|$)|spacer|" + DEVB, I)
PANELREF = re.compile(r"^(J|SW|S|RV|VR|LED|BAR|DS|BTN|P|CN|CON|FADE|FDR)[0-9]", I)
IC = re.compile(r"(^|[^a-z])(p?dip|dil|sip)[-_ ]?([0-9]+)", I)   # not SIL: in KiCad 4 and Eagle libraries SIL-n is a pin header
TO = re.compile(r"to-?92|to-?220|to-?3([^0-9]|$)", I)
SMDN = re.compile(r"(^|[^a-z])smd[-_]|_smd|smd_|-smd|package_so|soic|sot-?23|sot23|sot-?223|sot-?89|sod-|ssop|tssop|qfn|qfp|lqfp|tqfp|tsop|msop|"
                  r"vssop|(^|[^0-9])(0201|0402|0603|0805|1206|1210)([^0-9]|$)|case-[a-e]|sma_|smb_|smc_", I)
THTN = re.compile(r"_tht|dip-|dip_|to-?92|to-?220|do-?41|do-?35|radial|axial|rad-|resistor-vertical|cap-th|c_disc|7mm_resistor|cap-d", I)
SMDIC = re.compile(r"package_so|soic|(^|[^a-z])so-?[0-9]|ssop|tssop|qfn|qfp|msop|sop", I)
_k = [l.split("\t")[0] for l in open(os.path.join(HERE, "known_parts.tsv")).read().splitlines()[1:] if "\tmechanical" in l]
MECH = re.compile("heat ?-?sink" + "".join("|" + re.escape(x) for x in _k), I)
CATS = ["smd", "tht", "tht_ic", "tht_to", "smd_ic", "panel", "panel_smd", "unknown", "mech", "notpart"]
def classify(name, ref, mount, pads="", value=""):
    mount = {"th": "tht"}.get(mount, mount)
    if mount == "none" or str(pads) == "1": return "notpart"   # a one-pad footprint is a wire / test / mounting pad
    if NOTPART.search(name) or NOTREF.match(ref) or OUTLINE.search(name.split(":")[-1]): return "notpart"
    if MECH.search(name) or MECH.search(value): return "mech"
    m = IC.search(name)
    # a DIP/SIP package with 4+ pins (a 3-pin SIP is a regulator module, like a TO-220: it never decides); never a
    # display or LED in a DIL package (SparkFun-Displays:DIL12)
    if m and mount in ("tht", "") and not PANELREF.match(ref) and not re.search(r"display|segment|led|oled|lcd", name + " " + value, I):
        if int(m.group(3)) >= 4: return "tht_ic"
        return "tht_to"
    if PANEL.search(name) or PANELREF.match(ref) or PANEL.search(value):
        # an SMD panel part (SMD LED, SMD switch) still needs SMD soldering: panel_smd counts as "SMD present" in the
        # verdict, never in the SMD count; a dev board goes on with pin headers whatever its pads say
        return "panel_smd" if mount == "smd" and not re.search(DEVB, name + " " + value, I) else "panel"
    if not mount:
        mount = "smd" if SMDN.search(name) else ("tht" if THTN.search(name) else "")
        if not mount: return "unknown"
    if mount == "smd": return "smd_ic" if SMDIC.search(name) else "smd"
    if TO.search(name): return "tht_to"
    named = SMDN.search(name) or THTN.search(name) or re.search(r"dc-?dc|converter|regulator|module", name, I)
    if not named and (re.match(r"Q[0-9]", ref) or (re.match(r"(U|IC)[0-9]", ref) and str(pads) == "3")): return "tht_to"
    return "tht"
if __name__ == "__main__":
    c = dict.fromkeys(CATS, 0); unk = {}
    for l in sys.stdin:
        p = l.rstrip("\n").split("\t")
        if not p[0] and len(p) < 2: continue
        p += [""] * (5 - len(p))
        k = classify(*p[:5]); c[k] += 1
        if k == "unknown": unk[p[0]] = unk.get(p[0], 0) + 1
        if "-v" in sys.argv: print(f"{k}\t" + "\t".join(p[:4]))
    names = " ".join(f"{n}x{q}" for n, q in list(unk.items())[:5])
    print(f"{c['smd'] + c['smd_ic']} {c['tht']} {c['tht_ic']} {c['tht_to']} {c['smd_ic']} {c['panel'] + c['panel_smd']} {c['panel_smd']} {c['unknown']}\t{names}")
