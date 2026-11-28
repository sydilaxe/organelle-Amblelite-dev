"""Build the Organelle patch: python3 gen.py [outdir]  (default ../patches/AmbleLite)."""
import os
import sys
import pdlib
from pdlib import Canvas
import model as M
import control
import screen
import voice
import wavetables
import features
from dsp import mul, add, sub, div

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "patches", "AmbleLite")
TRIM = dict(drone=0.8, sub=0.9, pad=0.7, perc1=0.8, perc2=0.7, perc3=0.7, perc4=0.6, cloud=0.9)   # at Level 50 %


def level(v):
    """a Level knob (0..1) as a gain: 50 % = x1, 100 % = +6 dB, even dB steps down to -24 dB at 5 %, then silence"""
    return (f"if({v} >= 0.5, pow(10, 0.6*({v} - 0.5)), if({v} >= 0.05, pow(10, -2.6667*(0.5 - {v})), "
            f"{v}*1.2619))")


def layer_filter(c, L, *sides):
    """the layer's filter, its cutoff moving at audio rate (so a turned knob, Evolve or an LFO never steps it - the
    crackle of a [biquad~] whose coefficients jump): two one-pole low-passes in series (12 dB an octave) and,
    for the resonance, a band-pass at the same frequency added on top. Cutoff 20 Hz .. 20 kHz. Fully open, the dry
    signal (crossfaded), and the filter's subpatch switched off - it costs nothing until a cutoff closes"""
    cut, res = M.S(L, None, "Cutoff"), M.S(L, None, "Reso")
    op = c.ch(c.recv(f"al-s{cut}"), f"expr alpe[{cut}] >= 0.985", "t f f")
    opl = c.ch((op, 1), "pack f 40", "line~")
    f = Canvas(f"filter-{L}", w=1200)
    fins = [f.obj("inlet~", 20 + 200 * i, 5) for i in range(len(sides))]
    f.cx, f.cy = 20, 40
    sw = f.obj("switch~")
    on = f.ch(f.obj("inlet", 600, 5), "t f f")
    # (on at once when the cutoff closes; off once the crossfade to dry is over)
    sel = f.to((on, 0), "sel 0")
    dly = f.obj("delay 60")
    f.c(sel, 0, dly, 0)
    f.c(f.m(dly, "0"), 0, sw, 0)
    tb = f.to((sel, 1), "t b b")
    f.c(f.m((tb, 1), "stop"), 0, dly, 0)
    f.c(f.m((tb, 0), "1"), 0, sw, 0)
    f.c(f.m(f.obj("loadbang"), "0"), 0, sw, 0)
    hz = f.ch(f.recv(f"al-s{cut}"), f"expr 20*pow(1000, alpe[{cut}])", "pack f 40", "line~")
    q = f.ch(f.recv(f"al-s{res}"), f"expr 0.7 + 14*alpe[{res}]*alpe[{res}]")
    # (the band-pass peaks at 1: its share rises with Q, as a resonant low-pass's peak does)
    k = f.ch(f.recv(f"al-s{res}"), f"expr 14*alpe[{res}]*alpe[{res}]", "pack f 40", "line~")
    for i, x in enumerate(fins):
        l1 = f.obj("lop~")
        f.c(x, 0, l1, 0)
        f.c(hz, 0, l1, 1)
        l2 = f.obj("lop~")
        f.c(l1, 0, l2, 0)
        f.c(hz, 0, l2, 1)
        bp = f.obj("vcf~ 1")
        f.c(x, 0, bp, 0)
        f.c(hz, 0, bp, 1)
        f.c(q, 0, bp, 2)
        f.c(add(f, l2, mul(f, bp, k)), 0, f.obj("outlet~", 20 + 200 * i, 880), 0)
        f.col(200)
    node = c.sub(f)
    for i, x in enumerate(sides):
        c.c(x, 0, node, i)
    c.c(c.to((op, 0), "== 0"), 0, node, len(sides))
    wet = c.ch(opl, "*~ -1", "+~ 1")
    return [add(c, mul(c, (node, i), wet), mul(c, x, opl)) for i, x in enumerate(sides)]


def switched_fx(c, name, sides, slot, active, fade_ms, build):
    """an effect on the master in a subpatch of its own, switched on only while its knob is off neutral (active: an
    [expr] of the slot's value $f1): the processed signal crossfaded in over fade_ms, and once faded out the
    subpatch switched off - at neutral it costs nothing. build(f, inlets) -> the outlets' signals"""
    f = Canvas(name, w=1400)
    fins = [f.obj("inlet~", 20 + 200 * i, 5) for i in range(len(sides))]
    f.cx, f.cy = 20, 40
    sw = f.obj("switch~")
    on = f.ch(f.obj("inlet", 600, 5), "t f f")
    sel = f.to((on, 0), "sel 0")
    dly = f.obj(f"delay {fade_ms + 20}")
    f.c(sel, 0, dly, 0)
    f.c(f.m(dly, "0"), 0, sw, 0)
    tb = f.to((sel, 1), "t b b")
    f.c(f.m((tb, 1), "stop"), 0, dly, 0)
    f.c(f.m((tb, 0), "1"), 0, sw, 0)
    f.c(f.m(f.obj("loadbang"), "0"), 0, sw, 0)
    f.col(260)
    outs = build(f, fins)
    for i, y in enumerate(outs):
        f.c(y, 0, f.obj("outlet~", 20 + 200 * i, 1300), 0)
    node = c.sub(f)
    for i, x in enumerate(sides):
        c.c(x, 0, node, i)
    act = c.ch(c.recv(f"al-s{slot}"), f"expr {active}", "change", "t f f")
    c.c((act, 1), 0, node, len(sides))
    al = c.ch(c.m((act, 0), f"$1 {fade_ms}"), "line~")
    dry = c.ch(al, "*~ -1", "+~ 1")
    return [add(c, mul(c, (node, i), al), mul(c, x, dry)) for i, x in enumerate(sides)]


def shape_drive(c, sides):
    """Drive: soft saturation, y/(1 + |y|), of the signal raised up to 28 dB, with a little offset that grows with
    the knob (even harmonics: a rawer, more electric edge); a make-up gain keeps the level about where it was"""
    d = M.S("g", None, "Drive")

    def build(f, fins):
        g = f.ch(f.recv(f"al-s{d}"), f"expr 1 + 24*alpe[{d}]*alpe[{d}]", "t f f")
        gs = f.ch(f.m((g, 1), "$1 30"), "line~")
        mk = f.ch(f.m(f.to((g, 0), "expr (1 + 0.25*$f1)/$f1"), "$1 30"), "line~")
        bias = f.ch(f.recv(f"al-s{d}"), f"expr 0.15*alpe[{d}]", "pack f 30", "line~")
        outs = []
        for x in fins:
            y = add(f, mul(f, x, gs), bias)
            sat = div(f, y, f.ch(y, "abs~", "+~ 1"))
            outs.append(f.ch(mul(f, sat, mk), "hip~ 5"))
            f.col(200)
        return outs
    return switched_fx(c, "drive", sides, d, "$f1 > 0.005", 40, build)


def shape_blur(c, sides):
    """Blur: a diffuse smear. Each side through three allpasses (diffusion, the two sides' times apart: width), then
    a pair of damped delays feeding back into each other (a rotation: the tail moves between the sides). Turned
    up: more of it, a longer and darker tail (feedback 0.3 .. 0.9, damping 7 .. 3 kHz), the dry a little lower"""
    b = M.S("g", None, "Blur")
    AP = [(4.77, 3.59, 12.7), (5.37, 3.91, 13.3)]
    FDN = (61.3, 73.9)

    def build(f, fins):
        r = f.recv(f"al-s{b}")
        fb = f.ch(r, f"expr 0.6364*(0.3 + 0.6*alpe[{b}])", "pack f 50", "line~")     # (x 0.707: the rotation)
        damp = f.ch(r, f"expr 7000 - 4000*alpe[{b}]", "pack f 50", "line~")
        # (the tail's level held: the loop's build-up, 1 / (1 - fb^2) in power, taken back out)
        wetg = f.ch(r, f"expr 1.2*alpe[{b}]*sqrt(1 - pow(0.3 + 0.6*alpe[{b}], 2))", "pack f 50", "line~")
        dryg = f.ch(r, f"expr 1 - 0.6*alpe[{b}]*alpe[{b}]", "pack f 50", "line~")
        dif = []
        for side, x in enumerate(fins):
            y = x
            for n, ms in enumerate(AP[side]):
                name = f"al-blap{side}{n}"
                dd = f.obj(f"delread~ {name} {ms}")
                w = add(f, y, f.to(dd, "*~ 0.6"))
                f.c(w, 0, f.obj(f"delwrite~ {name} 20"), 0)
                y = add(f, dd, f.to(w, "*~ -0.6"))
            dif.append(y)
            f.col(200)
        aL, aR = f.obj(f"delread~ al-blfL {FDN[0]}"), f.obj(f"delread~ al-blfR {FDN[1]}")
        for i, (src, mix) in enumerate(((dif[0], add(f, aL, aR)), (dif[1], sub(f, aL, aR)))):
            lp = f.obj("lop~")
            f.c(add(f, src, mul(f, mix, fb)), 0, lp, 0)
            f.c(damp, 0, lp, 1)
            f.c(lp, 0, f.obj(f"delwrite~ al-blf{'LR'[i]} 100"), 0)
        return [add(f, mul(f, x, dryg), mul(f, wet, wetg)) for x, wet in zip(fins, (aL, aR))]
    return switched_fx(c, "blur", sides, b, "$f1 > 0.005", 400, build)


FILTER_DZ = 0.04        # (SHAPE Filter: the neutral zone each side of the middle - screen.py shows it as 0)


def shape_filter(c, sides):
    """Filter: one sweep, as a DJ filter - left of the middle a low-pass (12 dB an octave) that closes from 20 kHz to
    40 Hz at the far left; the middle open, clean (and the subpatch off); right of it a high-pass that sweeps up from
    5 Hz to 1 kHz. One cutoff, one resonance: only the side the knob is on filters - the other stage stays open.
    Reso: a band-pass at the cutoff, from the filter's own output (so a closed low-pass lets no highs back), added
    on top, growing in as the knob leaves the middle. Cutoffs at audio rate (no steps)"""
    fs, rs = M.S("g", None, "Filter"), M.S("g", None, "Reso")

    def build(f, fins):
        fv = f"alpe[{fs}]"
        # (u: how far from the neutral middle, 0 .. 1 either side, past a dead zone of FILTER_DZ - the knob
        # roughly upright is no filter at all, and the sweep starts from nothing at the zone's edge)
        u = f"(max(0, abs({fv} - 0.5) - {FILTER_DZ})/{0.5 - FILTER_DZ})"
        # (each starting where it changes nothing - a low-pass at 22 kHz, a high-pass at 5 Hz - so leaving the middle
        # is seamless: no step, no dip; the high-pass stops at 1 kHz - the drones and pads have little above it)
        lpf, hpf = f"22000*pow({40 / 22000:.6g}, {u})", f"5*pow(200, {u})"
        hz = f.obj(f"expr if({fv} > 0.5, {hpf}, 5); if({fv} < 0.5, {lpf}, 20000); "
                   f"if({fv} > 0.5, {hpf}, {lpf})")
        f.c(f.ch(f.recv(f"al-s{fs}"), "t b"), 0, hz, 0)
        hp, lp, rc = (f.ch(f.to((hz, i), "pack f 40"), "line~") for i in range(3))
        # (Reso: up to Q 30 and a peak 24 times the level - extreme near the top, a whistle; the master's soft
        # limit keeps it below clipping)
        k = f.obj(f"expr 24*alpe[{rs}]*alpe[{rs}]*min(1, {u}*{u}*4)")     # (growing in gently from the middle)
        q = f.obj(f"expr 0.7 + 30*alpe[{rs}]*alpe[{rs}]")
        for sl in (fs, rs):
            t = f.ch(f.recv(f"al-s{sl}"), "t b b")
            f.c((t, 0), 0, k, 0)
            f.c((t, 1), 0, q, 0)
        ks = f.ch(k, "pack f 40", "line~")
        outs = []
        for x in fins:
            h = x
            for _ in range(2):                  # (x - a one-pole low-pass: a one-pole high-pass, twice)
                l = f.obj("lop~")
                f.c(h, 0, l, 0)
                f.c(hp, 0, l, 1)
                h = sub(f, h, l)
            for _ in range(2):
                l = f.obj("lop~")
                f.c(h, 0, l, 0)
                f.c(lp, 0, l, 1)
                h = l
            bp = f.obj("vcf~ 1")
            f.c(h, 0, bp, 0)
            f.c(rc, 0, bp, 1)
            f.c(q, 0, bp, 2)
            outs.append(add(f, h, mul(f, bp, ks)))
            f.col(200)
        return outs
    return switched_fx(c, "mfilter", sides, fs, f"abs($f1 - 0.5) > {FILTER_DZ}", 40, build)


def mix():
    c = Canvas("mix", w=1800)
    c.comment("each layer's bus: Level (x mute, x its trim), its place (Pan, a balance); the master: Volume, a DC "
              "block, a soft limit above -2 dB; out to the Organelle (throw~ outL / outR). Every change ramps.")
    mL, mR = c.obj("+~"), c.obj("+~")
    for li, L in enumerate(M.LAYERS):
        lvl = M.S(L, None, "Level")
        g = c.obj(f"expr {level('alpe[%d]' % lvl)}*{TRIM[L]}")
        c.c(c.ch(c.recv(f"al-s{lvl}"), "t b"), 0, g, 0)
        gl0 = c.ch(g, "pack f 30", "line~")
        # in / out: 'in fade_ms' (control.layer_switches) - the layer fades up or down over the Fade time
        ins = c.ch(c.recv(f"al-in{li}"), "line~")
        c.c(c.m(c.recv("al-init"), f"{1 if L in control.IN_AT_START else 0}"), 0, ins, 0)
        gl = mul(c, gl0, ins)
        if M.kind(L) in ("perc", "cloud"):       # (no Pan page: the lanes' voices and the grains spread themselves)
            bl, br = gl, gl
        else:
            pan = M.S(L, None, "Pan")
            pb = c.obj(f"expr min(1, 2*(1 - alpe[{pan}])); min(1, 2*alpe[{pan}])")
            c.c(c.ch(c.recv(f"al-s{pan}"), "t b"), 0, pb, 0)
            bl = mul(c, gl, c.ch(pb, "pack f 30", "line~"))
            br = mul(c, gl, c.ch((pb, 1), "pack f 30", "line~"))
        cL, cR = c.obj(f"catch~ al-{L}-L"), c.obj(f"catch~ al-{L}-R")
        cL, cR = layer_filter(c, L, cL, cR)          # (the layer's filter, once on its bus)
        if L == "pad":                                # (the input's morph mode: the pads through its vocoder)
            import audioin
            cL, cR = audioin.pad_morph(c, [cL, cR])
        oL, oR = mul(c, cL, bl), mul(c, cR, br)
        import vis
        vis.taps(c, li, L, oL, oR)
        c.c(oL, 0, mL, 0)
        c.c(oR, 0, mR, 0)
        if L != "cloud":            # (what the cloud records: every other layer, after its level)
            c.c(oL, 0, c.obj("throw~ al-csrcL"), 0)
            c.c(oR, 0, c.obj("throw~ al-csrcR"), 0)
        c.col(200)
    # the audio input's modes (audioin.py), into the master
    c.c(c.obj("catch~ al-input-L"), 0, mL, 0)
    c.c(c.obj("catch~ al-input-R"), 0, mR, 0)
    # SHAPE (the MIX view's last page): Drive, Blur, then the Filter over everything - the tail included
    c.col(260)
    sh = shape_filter(c, shape_blur(c, shape_drive(c, [mL, mR])))
    vol = c.ch(c.recv(f"al-s{M.S('g', None, 'Volume')}"), "expr $f1*$f1*2", "pack f 30", "line~")
    # (PANIC, aux + low D#: everything fades out over 8 s - control.panic - then back up at Start)
    pg = c.ch(c.recv("al-panicg"), "line~")
    c.c(c.m(c.recv("al-init"), "1"), 0, pg, 0)
    # (the panic's fade cubed: a straight line in level falls away too late and then all at once; cubed it sinks
    # about evenly in loudness - -6 dB at a fifth of the way, -18 at half, -36 at three quarters - then to silence)
    vol = mul(c, vol, mul(c, pg, mul(c, pg, pg)))
    for x, o in ((sh[0], "outL"), (sh[1], "outR")):
        # (a soft limit above 0.8: the excess e eased to 0.2 e / (0.2 + |e|), so it never passes 1)
        y0 = c.ch(mul(c, x, vol), "hip~ 5")
        lin = c.to(y0, "clip~ -0.8 0.8")
        e = sub(c, y0, lin)
        y = add(c, lin, div(c, c.to(e, "*~ 0.2"), c.ch(e, "abs~", "+~ 0.2")))
        c.c(y, 0, c.obj("throw~ " + o), 0)
        c.c(y, 0, c.obj(f"s~ {o}-vis"), 0)           # (the visualizer's scope)
    return c


def main_patch():
    pdlib.PROCS.clear()
    m = Canvas(w=1200, h=700)
    m.comment("AMBLE LITE - generated by tools/gen.py: edit the generator rather than this file", 20, 5)
    lb = m.obj("loadbang", 20, 40)
    t = m.obj("t b b b b", 20, 65)
    m.c(lb, 0, t, 0)
    m.c(t, 3, m.obj("s al-init", 300, 95), 0)
    m.c(t, 2, m.obj("s al-sendall", 220, 120), 0)
    m.c(m.m((t, 1), "0"), 0, m.obj("s midiOutGate", 140, 145), 0)
    m.c(t, 0, m.obj("s al-redraw", 20, 170), 0)
    m.cx, m.cy = 20, 220
    m.comment("control and screen")
    m.cx, m.cy = 20, 245
    ctl = Canvas("control", w=1600)
    control.build(ctl)
    m.sub(ctl, 20, 250)
    scr = Canvas("screen", w=2600)
    screen.build(scr)
    m.sub(scr, 130, 250)
    m.sub(mix(), 240, 250)
    import cloud
    m.sub(cloud.build(), 510, 250)
    import audioin
    ai = Canvas("input", w=1600)
    audioin.build(ai)
    m.sub(ai, 730, 250)
    import vis
    vc = Canvas("visualizer", w=1600)
    vis.build(vc)
    m.sub(vc, 840, 250)
    import userwaves
    uw = Canvas("userwaves", w=1600)
    userwaves.build(uw)
    m.sub(uw, 620, 250)
    import harmony
    hm = Canvas("harmony", w=2600)
    harmony.build(hm)
    m.sub(hm, 690, 250)
    import lines
    ln = Canvas("lines", w=2600)
    lines.build(ln)
    m.sub(ln, 870, 250)
    import roadmap
    rd = Canvas("roadmap", w=2600)
    roadmap.build(rd)
    m.sub(rd, 780, 250)
    import midi
    mi = Canvas("midi", w=1600)
    midi.build(mi)
    m.sub(mi, 600, 250)
    m3 = Canvas("features", w=1600)
    features.build(m3)
    m.sub(m3, 420, 250)
    m.comment("voices", 20, 300)
    x = 20
    for L in M.NOTE_LAYERS:
        for k in range(M.VOICES[L]):
            m.obj(f"al-{L} {k}", x, 325 + 25 * (k % 3))
            if k % 3 == 2:
                x += 90
        x += 90
    return m


def build(out=OUT):
    os.makedirs(out, exist_ok=True)
    main = main_patch()
    voices = {L: voice.voice(L) for L in M.NOTE_LAYERS}
    pdlib.fold_patch(main, *voices.values())
    main.save(os.path.join(out, "main.pd"))
    for L, v in voices.items():
        v.save(os.path.join(out, f"al-{L}.pd"))
    # (a space escaped: a page name like WOOD 1 stays one word)
    open(os.path.join(out, "al-words.txt"), "w").write("".join(w.replace(" ", "\\ ") + "\n" for w in screen.LINES))
    wavetables.write(os.path.join(out, "waves", "factory"))
    open(os.path.join(out, "pd-opts.txt"), "w").write("-audiobuf 25\n")
    import midi
    midi.write_profiles(out)
    # the snapshots: kept across builds (an update keeps your saves); 18 empty lines the first time
    rm = os.path.join(out, "roadmap.txt")        # (the roadmap: kept across builds too)
    if not os.path.exists(rm):
        open(rm, "w").write("")
    pc = os.path.join(out, "pieces.txt")         # (the pieces: kept across builds too; 8 empty lines)
    if not os.path.exists(pc):
        open(pc, "w").write("-1\n" * features.PIECES)
    lp = os.path.join(out, "loops.txt")          # (the pieces' loops: kept across builds too)
    if not os.path.exists(lp):
        open(lp, "w").write("0 0 0 0\n" * (features.PIECES * features.LOOP_LAYERS))
    import roadmap      # (the sections' parameter changes: the roadmap's, and each piece's - kept across builds)
    for fn, lines in (("roadchg.txt", M.MAXSEC), ("sections.txt", features.PIECES * M.MAXSEC)):
        if not os.path.exists(os.path.join(out, fn)):
            open(os.path.join(out, fn), "w").write("0\n" * lines)
    sv = os.path.join(out, "saves.txt")
    if not os.path.exists(sv):
        open(sv, "w").write("-1\n" * (features.SCRATCH + 2))
    import readme
    open(os.path.join(out, "README.txt"), "w").write(readme.text())
    return out


if __name__ == "__main__":
    print(build())
