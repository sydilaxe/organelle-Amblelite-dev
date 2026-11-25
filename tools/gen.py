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
        oL, oR = mul(c, cL, bl), mul(c, cR, br)
        c.c(oL, 0, mL, 0)
        c.c(oR, 0, mR, 0)
        if L != "cloud":            # (what the cloud records: every other layer, after its level)
            c.c(oL, 0, c.obj("throw~ al-csrcL"), 0)
            c.c(oR, 0, c.obj("throw~ al-csrcR"), 0)
        c.col(200)
    vol = c.ch(c.recv(f"al-s{M.S('g', None, 'Volume')}"), "expr $f1*$f1*2", "pack f 30", "line~")
    for x, o in ((mL, "outL"), (mR, "outR")):
        # (a soft limit above 0.8: the excess e eased to 0.2 e / (0.2 + |e|), so it never passes 1)
        y0 = c.ch(mul(c, x, vol), "hip~ 5")
        lin = c.to(y0, "clip~ -0.8 0.8")
        e = sub(c, y0, lin)
        y = add(c, lin, div(c, c.to(e, "*~ 0.2"), c.ch(e, "abs~", "+~ 0.2")))
        c.c(y, 0, c.obj("throw~ " + o), 0)
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
    sv = os.path.join(out, "saves.txt")
    if not os.path.exists(sv):
        open(sv, "w").write("-1;\n" * (features.SCRATCH + 2))
    import readme
    open(os.path.join(out, "README.txt"), "w").write(readme.text())
    return out


if __name__ == "__main__":
    print(build())
