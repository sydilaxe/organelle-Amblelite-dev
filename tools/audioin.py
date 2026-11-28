"""The audio input (INPUT global page): Mode, Gain, Amount. Off: the input is ignored and its DSP switched off.
  reso    four resonant strings tuned to the pads' voices (the chord), rung by the input; Amount: how long they ring
  cloud   the input into the granular cloud (its Source to input, the cloud in); Amount: unused
  bands   eight bands tuned to the key and mode (every other degree, two octaves), each breathing slowly; Amount:
          how narrow
  morph   a 4-band vocoder: the input's bands shape the pads' (the pads speak); Amount: how much
  octave  the input with an octave below (a sine on its tracked pitch, following its level) and an octave above (the
          rectified input); Amount: below .. above
In every mode its pitch is tracked (an autocorrelation tracker, Pd's own objects): with the HARMNY page's Listen on, a steady pitch counts as a held note
and pulls the next chord to contain it."""
from pdlib import Canvas, proc, V, T, If, Call, run_steps
from dsp import mul, add, sub, prm
import model as M
from model import S

MODES = ["off", "reso", "cloud", "bands", "morph", "octave"]
VOC = [220, 600, 1500, 3600]           # the vocoder's band centres (Hz)
GLOBALS = dict(alinclr=0, alini2=0, alinm=0, alinp=0, alinl=-1, alinc=0, alinh=-1, alinlv=0)


def P(name):
    return S("g", None, name)


def mode_is(k):
    n = len(MODES)
    return f"(min({n - 1}, int(alp[{P('InMode')}]*{n})) == {k})"


def build(c):
    c.comment("the audio input: off (nothing - its DSP off) / reso / cloud / bands / morph / octave; its pitch heard")
    d = Canvas("input-dsp", w=2400, h=1200)
    node = c.sub(d)
    # on while the mode isn't off (off after a moment, so the last of it fades)
    on = c.ch(c.recv(f"al-s{P('InMode')}"), f"expr !{mode_is(0)}", "change")
    c.c(on, 0, node, 0)
    # entering cloud mode: the cloud records the input, and comes in
    run_steps(c, (c.ch(c.recv(f"al-s{P('InMode')}"), f"expr {mode_is(2)}", "change", "sel 1"), 0), [
        Call("al-incloud")])
    cl = M.LAYERS.index("cloud")
    cs = S("cloud", "grains", "Source")
    from pdlib import SendL
    proc(c, "al-incloud", [SendL("al-set", [str(cs), f"{(1 + 0.5) / 3:.6f}"]), SendL("al-inset", [str(cl), "1"])])
    _dsp(d)
    listening(c)


def _dsp(d):
    sw = d.obj("switch~")
    on = d.ch(d.obj("inlet", 20, 5), "sel 0")
    dly = d.obj("delay 80")
    d.c(on, 0, dly, 0)
    d.c(d.m(dly, "0"), 0, sw, 0)
    tb = d.to((on, 1), "t b b")
    d.c(d.m((tb, 1), "stop"), 0, dly, 0)
    d.c(d.m((tb, 0), "1"), 0, sw, 0)
    d.c(d.m(d.obj("loadbang"), "0"), 0, sw, 0)
    d.cx, d.cy = 20, 60
    g = d.ch(d.recv(f"al-s{P('InGain')}"), "expr 4*$f1*$f1", "pack f 40", "line~")
    x = mul(d, d.ch(add(d, d.obj("r~ inL"), d.obj("r~ inR")), "*~ 0.5", "hip~ 20"), g)
    amt = prm(d, P("InAmt"))

    def gate(k):
        return d.ch(d.recv(f"al-s{P('InMode')}"), f"expr {mode_is(k)}", "pack f 60", "line~")
    L, R = d.obj("*~ 1"), d.obj("*~ 1")
    # ---- reso: four strings on the pads' voices
    d.col(300)
    wr = gate(1)
    q = d.ch(d.recv(f"al-s{P('InAmt')}"), "expr 10 + 190*$f1*$f1")
    for v in range(4):
        hz = d.ch(d.recv("al-pad-n"), f"route {v}", "unpack f f", "mtof", "pack f 50", "line~")
        r = d.obj("vcf~ 40")
        d.c(x, 0, r, 0)
        d.c(hz, 0, r, 1)
        d.c(q, 0, r, 2)
        o = mul(d, d.to(r, "*~ 6"), wr)
        d.c(o, 0, L if v % 2 == 0 else R, 0)
        d.c(d.to(o, "*~ 0.35"), 0, R if v % 2 == 0 else L, 0)
    # ---- bands: eight bands on the scale (every other degree from the key, two octaves up from C3)
    d.col(300)
    wb = gate(3)
    qb = d.ch(d.recv(f"al-s{P('InAmt')}"), "expr 3 + 40*$f1*$f1")
    from control import opt
    key, mode = P("Key"), P("Mode")
    m, k_ = opt(mode), opt(key)
    for i in range(8):
        note = f"48 + {k_} + alsc[{m}*7 + ({2 * i}) % alscn[{m}]] + 12*int({2 * i}/alscn[{m}])"
        nx = d.obj(f"expr 8.17579891564*exp(0.0577622650467*({note}))")      # (mtof, as plain arithmetic)
        for sl in (key, mode, P("Scale")):
            d.c(d.ch(d.recv(f"al-s{sl}"), "t b"), 0, nx, 0)
        d.c(d.recv("al-init"), 0, nx, 0)
        hz = d.ch(nx, "pack f 200", "line~")
        r = d.obj("vcf~ 8")
        d.c(x, 0, r, 0)
        d.c(hz, 0, r, 1)
        d.c(qb, 0, r, 2)
        br = d.ch(d.obj(f"osc~ {0.031 + 0.017 * i:.3f}"), "*~ 0.4", "+~ 0.6")
        o = mul(d, mul(d, d.to(r, "*~ 2.5"), br), wb)
        d.c(o, 0, L if i % 2 == 0 else R, 0)
        d.c(d.to(o, "*~ 0.3"), 0, R if i % 2 == 0 else L, 0)
    # ---- the pitch and the level (octave mode, listening)
    d.col(300)
    # (the level in dB, and the pitch: Amble's autocorrelation tracker - Pd's own objects only, no extra)
    d.c(d.ch(x, "env~ 2048 1024"), 0, d.obj("s al-inenv"), 0)
    tr = d.sub(_tracker(), 1200, 40)
    d.c(x, 0, tr, 0)
    sg = d.recv("al-inpitch")
    lvl = d.ch(x, "abs~", "lop~ 12", "*~ 1.6")
    # ---- octave: below (a sine on the tracked pitch, at the input's level), above (rectified)
    wo = gate(5)
    dn = d.ch(sg, "moses 1")
    f2 = d.ch((dn, 1), "mtof", "* 0.5", "pack f 30", "line~", "osc~")
    below = mul(d, mul(d, f2, lvl), d.ch(amt, "*~ -1", "+~ 1"))
    above = mul(d, d.ch(x, "abs~", "hip~ 60", "*~ 1.4"), amt)
    oc = mul(d, add(d, add(d, d.to(x, "*~ 0.6"), below), above), wo)
    d.c(oc, 0, L, 0)
    d.c(oc, 0, R, 0)
    # ---- morph: the input's four bands' levels, for the pads (gen.mix: pad_morph)
    for i, f in enumerate(VOC):
        b = d.obj(f"vcf~ 4")
        d.c(x, 0, b, 0)
        d.c(d.obj(f"sig~ {f}"), 0, b, 1)
        d.c(d.ch(b, "abs~", "lop~ 20", "*~ 6"), 0, d.obj(f"s~ al-venv{i}"), 0)
    d.c(L, 0, d.obj("throw~ al-input-L"), 0)
    d.c(R, 0, d.obj("throw~ al-input-R"), 0)


def _tracker():
    """FFT autocorrelation pitch tracker (Amble's), at half rate (22.05 kHz): 2048-point blocks of 1024 windowed
    samples (zero padded), every 1024 (46 ms). The strongest lag in 20..280 (79 Hz - 1.1 kHz), parabolic
    interpolation -> al-inpitch (MIDI; -1 when unclear or quiet)"""
    from pdlib import X
    p = Canvas("pitch", w=1400)
    p.comment("autocorrelation by FFT: |X|^2 -> inverse FFT; the strongest lag in 20..280 is the period")
    p.c(p.ch(p.obj("loadbang"), "f 1"), 0, p.obj("switch~ 2048 2 0.5"), 0)
    import math
    win = [0.5 - 0.5 * math.cos(2 * math.pi * i / 1024) for i in range(1024)] + [0.0] * 1024
    p.obj("array define alinwin 2048")
    p.obj("array define alinacf 2048")
    p.c(p.m(p.obj("loadbang"), " ".join(f"{v:.5f}" for v in win)), 0, p.obj("array set alinwin"), 0)
    x = p.obj("inlet~", 20, 5)
    w = mul(p, x, p.obj("tabreceive~ alinwin"))
    ff = p.to(w, "rfft~")
    pw = add(p, mul(p, (ff, 0), (ff, 0)), mul(p, (ff, 1), (ff, 1)))
    p.c(p.to(pw, "rifft~"), 0, p.obj("tabsend~ alinacf"), 0)
    p.col()
    mx = p.obj("array max alinacf 20 260")
    p.c(p.obj("bang~"), 0, mx, 0)
    pk = p.obj("pack f f")
    p.c(mx, 1, pk, 1)
    p.c(mx, 0, pk, 0)
    e = p.to(pk, "expr $f2; $f1/max(1e-09, alinacf[0])")
    p.c(e, 1, p.obj("v alinclr"), 0)
    tb = p.to(e, "t b f")
    p.c(tb, 1, p.obj("v alini2"), 0)
    y0, y1, y2 = "alinacf[int(alini2)-1]", "alinacf[int(alini2)]", "alinacf[int(alini2)+1]"
    den = f"({y0} - 2*{y1} + {y2})"
    run_steps(p, (tb, 0), [X(f"if(alinclr > 0.35 && alinlv > 48, 17.3123405046*log(0.12231220585*22050/(alini2 + max(-1, min(1, if({den} < -1e-09, "
                             f"0.5*({y0} - {y2})/{den}, 0))))), -1)", "s al-inpitch")])        # (ftom, as plain arithmetic)
    return p


def pad_morph(c, sides):
    """the pads through the vocoder (morph mode, by Amount): each of their four bands at the input's level there.
    Off (any other mode): the vocoder's subpatch switched off, the pads dry"""
    m = c.ch(c.recv(f"al-s{P('InMode')}"), f"expr {mode_is(4)}")
    # (the vocoder's share: Amount, in morph mode only - recomputed when either changes)
    ax = c.obj(f"expr alp[{P('InAmt')}]*{mode_is(4)}")
    for sl in (P("InAmt"), P("InMode")):
        c.c(c.ch(c.recv(f"al-s{sl}"), "t b"), 0, ax, 0)
    amt = c.ch(ax, "pack f 60", "line~")
    v = Canvas("vocoder", w=1600)
    ins = [v.obj("inlet~", 20 + 200 * i, 5) for i in range(len(sides))]
    sw = v.obj("switch~")
    v.c(v.m(v.obj("loadbang"), "0"), 0, sw, 0)
    v.c(v.obj("inlet", 600, 5), 0, sw, 0)
    v.cx, v.cy = 20, 40
    for i, x in enumerate(ins):
        sm = v.obj("*~ 1.5")
        for j, f in enumerate(VOC):
            b = v.obj("vcf~ 4")
            v.c(x, 0, b, 0)
            v.c(v.obj(f"sig~ {f}"), 0, b, 1)
            v.c(mul(v, b, v.obj(f"r~ al-venv{j}")), 0, sm, 0)
        v.c(sm, 0, v.obj("outlet~", 20 + 200 * i, 880), 0)
        v.col(300)
    node = c.sub(v)
    for i, x in enumerate(sides):
        c.c(x, 0, node, i)
    c.c(m, 0, node, len(sides))
    dry = c.ch(amt, "*~ -1", "+~ 1")
    return [add(c, mul(c, x, dry), mul(c, (node, i), amt)) for i, x in enumerate(sides)]


def listening(c):
    """the input's pitch as a held note: steady (the same note over two of the tracker's steps, about 0.1 s) and loud
    enough - it holds that pitch class in the listening (harmony.py alhpc) until the pitch changes or it goes quiet"""
    rel = [If("alinh >= 0", [T("alhpc", "alinh % 12", "max(0, alhpc[alinh % 12] - 1)"), V("alhcnt", "max(0, alhcnt - 1)"),
                             V("alinh", "-1")])]
    c.c(c.recv("al-inenv"), 0, c.obj("v alinlv"), 0)
    p = c.ch(c.recv("al-inpitch"), "t f")
    c.c(p, 0, c.obj("v alinp"), 0)
    run_steps(c, (c.to(p, "t b"), 0), [
        If(f"!{mode_is(0)} && alinlv > 55 && alinp > 20", [
            If("int(alinp + 0.5) == alinl", [V("alinc", "alinc + 1")], [V("alinc", "0"), V("alinl", "int(alinp + 0.5)")]),
            If("alinc == 2 && alinl != alinh", rel + [
                V("alinh", "alinl"), T("alhpc", "alinh % 12", "alhpc[alinh % 12] + 1"), V("alhcnt", "alhcnt + 1")])],
           rel + [V("alinl", "-1"), V("alinc", "0")])])
