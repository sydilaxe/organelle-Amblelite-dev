"""The sound engines, by layer. Each builder takes (s, ins) - the engine canvas and its inputs (dsp.engine_canvas) -
and returns (L, R) before the engine's own fade. Parameters by name: P(name) is the slot; prm / cx turn it into a
signal. Nothing here is random: the only movement is what the parameters ask for."""
from dsp import mul, add, sub, prm, saw_expr, pulse_expr, dt_of, blep
from model import S, ENGINES, kind

FM_RATIOS = [0.5, 1, 1.5, 2, 3, 3.5, 4, 5, 7]
SUB_FM_RATIOS = [0.5, 1, 1.5, 2, 3]


def cx(c, slots, expr, ms=60):
    """a control expression over slots (alpe[slot]: the value with Evolve's movement), recomputed when any of them
    changes, smoothed"""
    e = c.obj("expr " + expr)
    for sl in slots:
        c.c(c.ch(c.recv(f"al-s{sl}"), "t b"), 0, e, 0)
    return c.ch(e, f"pack f {ms}", "line~")


def a(slot):
    return f"alpe[{slot}]"


def pick(values, idx):
    """an [expr] if-chain picking values[idx]"""
    out = str(values[-1])
    for i in range(len(values) - 2, -1, -1):
        out = f"if({idx} == {i}, {values[i]}, {out})"
    return out


def nopt(layer, engine, name):
    p = [p for p in dict(ENGINES[layer])[engine] if p.name == name][0]
    return len(p.opts)


def fm2(c, f, ratio, index, fb):
    """classic 2-operator FM (phase modulation, as the DX7): a modulator with feedback into a sine carrier.
    ratio, index (in cycles), fb (in cycles): signals. Feedback is two fixed-point steps of y = cos(p + fb y) -
    the sound of a true one-sample feedback loop up to a saw-like tone, at the cost of three cos~"""
    pm = c.to(mul(c, f, ratio), "phasor~")
    y = c.to(pm, "cos~")
    for _ in range(2):
        y = c.to(add(c, pm, mul(c, fb, y)), "cos~")
    pc = c.to(f, "phasor~")
    return c.to(add(c, pc, mul(c, index, y)), "cos~")


# =========================================================================================== drone
WAVE_MORPH = ("max(0, 1 - abs($v3*3))*cos(6.28318*$v1) + max(0, 1 - abs($v3*3 - 1))*(1 - 4*abs($v1 - 0.5)) + "
              f"max(0, 1 - abs($v3*3 - 2))*({saw_expr()}) + max(0, 1 - abs($v3*3 - 3))*({pulse_expr(w='0.5')})")


def morph_osc(c, f, w):
    """an oscillator morphing sine -> triangle -> saw -> square (band-limited saw and square) by w~ (0..1)"""
    ph = c.to(f, "phasor~")
    return morph_from(c, ph, dt_of(c, f), w)


def morph_from(c, ph, dt, w):
    e = c.obj("expr~ " + WAVE_MORPH)
    c.c(ph, 0, e, 0)
    c.c(dt, 0, e, 1)
    c.c(w, 0, e, 2)
    return e


def drone_analog(s, ins, L):
    f, env, note = ins
    P = lambda n: S("drone", "analog", n)
    ni = nopt("drone", "analog", "Intvl")
    # B's frequency: the interval, then the detune (0 .. 30 cents, finer near 0)
    rb = cx(s, [P("Intvl"), P("Detune")], f"{pick([1, 1.5, 2, 0.5, 1.33484], f'min({ni - 1}, int({a(P('Intvl'))}*{ni}))')}"
                                           f"*pow(2, {a(P('Detune'))}*{a(P('Detune'))}*30/1200)")
    fb = mul(s, f, rb)
    B = morph_osc(s, fb, prm(s, P("WaveB")))
    # A, phase-modulated by B (cross modulation): up to 1.5 cycles
    pa = s.to(f, "phasor~")
    xm = s.ch(prm(s, P("XMod")), "expr~ $v1*$v1*1.5")
    pa2 = s.to(add(s, pa, mul(s, B, xm)), "wrap~")
    A = morph_from(s, pa2, dt_of(s, f), prm(s, P("WaveA")))
    mix = prm(s, P("Mix"))
    ga = s.ch(mix, "*~ -1", "+~ 1")
    av, bv = mul(s, A, ga), mul(s, B, mix)
    ring = mul(s, mul(s, A, B), prm(s, P("Ring")))
    fs = s.to(f, "*~ 0.5")
    subo = s.obj("expr~ " + pulse_expr(w="0.5"))
    s.c(s.to(fs, "phasor~"), 0, subo, 0)
    s.c(dt_of(s, fs), 0, subo, 1)
    subv = mul(s, subo, s.ch(prm(s, P("Sub")), "*~ 0.8"))
    core = add(s, ring, subv)
    L = s.to(add(s, add(s, av, s.to(bv, "*~ 0.75")), core), "*~ 0.5")
    R = s.to(add(s, add(s, s.to(av, "*~ 0.75"), bv), core), "*~ 0.5")
    return L, R


def drone_fm(s, ins, L):
    f, env, note = ins
    P = lambda n: S("drone", "fm", n)
    n = len(FM_RATIOS)
    ratio = cx(s, [P("Ratio"), P("Fine")], f"{pick(FM_RATIOS, f'min({n - 1}, int({a(P('Ratio'))}*{n}))')}"
                                            f"*pow(2, ({a(P('Fine'))} - 0.5)/6)")
    rate = s.ch(s.recv(f"al-s{P('MoRate')}"), "expr 0.01*pow(50, $f1)", "osc~")
    mot = add(s, s.to(mul(s, rate, prm(s, P("Motion"))), "*~ 0.5"), s.obj("sig~ 1"))
    idx = mul(s, s.ch(prm(s, P("Index")), "expr~ 1.6*$v1*$v1"), mot)
    fb = s.to(prm(s, P("Fdbk")), "*~ 0.25")
    o = s.to(fm2(s, f, ratio, idx, fb), "*~ 0.43")
    return o, o


def drone_spectr(s, ins, L):
    f, env, note = ins
    P = lambda n: S("drone", "spectr", n)
    L, R = s.obj("*~ 0.3"), s.obj("*~ 0.3")
    drift = prm(s, P("Drift"))
    for n in range(1, 9):
        # the level: 1/n^(0.3 .. 1.7 by Tilt), the upper ones x (Upper x2)^2, odd / even balance
        lv = cx(s, [P("Upper"), P("Tilt"), P("OddEv")],
                f"pow({n}, -(0.3 + 1.4*{a(P('Tilt'))}))" + ("" if n == 1 else
                f"*4*{a(P('Upper'))}*{a(P('Upper'))}*" + (f"min(1, 2 - 2*{a(P('OddEv'))})" if n % 2 else f"min(1, 2*{a(P('OddEv'))})")))
        rt = s.ch(s.recv(f"al-s{P('DrRate')}"), f"expr {0.013 * (1 + 0.37 * n):.4f}*pow(10, ($f1 - 0.4)*2)", "osc~")
        sw = s.to(mul(s, s.to(rt, "-~ 1"), s.to(drift, "*~ 0.5")), "+~ 1")
        fn = cx(s, [P("Strtch")], f"{n}*(1 + {a(P('Strtch'))}*0.02*{n - 1})")
        p = mul(s, mul(s, s.to(mul(s, f, fn), "osc~"), lv), sw)
        s.c(s.to(p, f"*~ {1.0 if n % 2 else 0.55}"), 0, L, 0)
        s.c(s.to(p, f"*~ {0.55 if n % 2 else 1.0}"), 0, R, 0)
    return L, R


# =========================================================================================== sub
def _body(s, sig, slot):
    lp = s.to(sig, "lop~ 500")
    s.c(s.ch(s.recv(f"al-s{slot}"), "expr 500*pow(4, $f1 - 0.5)"), 0, lp, 1)
    return lp


def sub_sine(s, ins, L):
    f, env, note = ins
    P = lambda n: S("sub", "sine", n)
    x = s.to(f, "osc~")
    sat = s.ch(x, "*~ 1.8", "clip~ -1 1", "*~ 0.25")
    y = add(s, s.to(x, "*~ 0.6"), mul(s, sat, s.to(prm(s, P("Harm")), "*~ 2")))     # Harm 0: a pure sine
    o = _body(s, y, P("Body"))
    return o, o


def sub_warm(s, ins, L):
    f, env, note = ins
    P = lambda n: S("sub", "warm", n)
    x = s.to(f, "osc~")
    y = add(s, s.ch(x, "*~ 3", "clip~ -1 1", "*~ 0.5"),
            mul(s, s.ch(s.to(f, "*~ 2"), "osc~", "*~ 0.18"), s.to(prm(s, P("Octave")), "*~ 2")))
    o = _body(s, y, P("Body"))
    return o, o


def sub_pulse(s, ins, L):
    f, env, note = ins
    P = lambda n: S("sub", "pulse", n)
    e = s.obj("expr~ " + pulse_expr())
    s.c(s.to(f, "phasor~"), 0, e, 0)
    s.c(dt_of(s, f), 0, e, 1)
    s.c(s.ch(prm(s, P("Width")), "*~ 0.45", "+~ 0.05"), 0, e, 2)
    y = s.ch(e, "lop~ 300", "lop~ 300", "*~ 0.75")
    o = _body(s, y, P("Body"))
    return o, o


def sub_fm(s, ins, L):
    f, env, note = ins
    P = lambda n: S("sub", "fm", n)
    n = len(SUB_FM_RATIOS)
    ratio = cx(s, [P("Ratio")], pick(SUB_FM_RATIOS, f"min({n - 1}, int({a(P('Ratio'))}*{n}))"))
    growl = add(s, s.to(mul(s, s.obj("osc~ 0.07"), prm(s, P("Growl"))), "*~ 0.5"), s.obj("sig~ 1"))
    idx = mul(s, s.ch(prm(s, P("Index")), "expr~ 1.2*$v1*$v1"), growl)
    o = s.to(fm2(s, f, ratio, idx, s.to(prm(s, P("Fdbk")), "*~ 0.2")), "*~ 0.6")
    return o, o


# =========================================================================================== pads
def pad_sine(s, ins, L):
    f, env, note = ins
    P = lambda n: S("pad", "sine", n)
    nc = nopt("pad", "sine", "Count")
    amps = [None]
    for n in range(2, 9):
        amps.append(cx(s, [P("Harm"), P("Slope"), P("OddEv"), P("Count")],
                       f"{a(P('Harm'))}*pow({n}, -(0.3 + 2.2*{a(P('Slope'))}))*"
                       + (f"min(1, 2 - 2*{a(P('OddEv'))})" if n % 2 else f"min(1, 2*{a(P('OddEv'))})")
                       + f"*({n} <= 2 + min({nc - 1}, int({a(P('Count'))}*{nc})))"))
    outs = []
    det = s.ch(prm(s, P("Chorus")), "*~ 0.006", "+~ 1")
    for side in (0, 1):
        fd = f if side == 0 else mul(s, f, det)
        # the harmonics from one cosine (Chebyshev: cos(n w) = T_n(cos w), T_n+1 = 2x T_n - T_n-1)
        x = s.ch(fd, "phasor~", "cos~")
        x2 = s.to(x, "*~ 2")
        T = [None, x, s.to(mul(s, x2, x), "-~ 1")]
        for n in range(3, 9):
            T.append(sub(s, mul(s, x2, T[n - 1]), T[n - 2]))
        sm = s.obj("*~ 0.27")
        s.c(x, 0, sm, 0)
        for n in range(2, 9):
            s.c(mul(s, T[n], amps[n - 1]), 0, sm, 0)
        outs.append(sm)
    return outs[0], outs[1]


def pad_fm(s, ins, L):
    f, env, note = ins
    P = lambda n: S("pad", "fm", n)
    n = len(FM_RATIOS)
    ratio = cx(s, [P("Ratio"), P("Fine")], f"{pick(FM_RATIOS, f'min({n - 1}, int({a(P('Ratio'))}*{n}))')}"
                                            f"*pow(2, ({a(P('Fine'))} - 0.5)/6)")
    # the index envelope: brighter at each note's start, settling (EnvAmt x2 at most, EnvDec 30 ms .. 6 s)
    ie = s.obj("vline~")
    tb = s.to(note, "t b")
    ex = s.obj(f"expr 30*pow(200, {a(P('EnvDec'))})")
    s.c(tb, 0, ex, 0)
    s.c(s.m(ex, "1, 0 $1"), 0, ie, 0)
    ienv = mul(s, mul(s, ie, ie), s.to(prm(s, P("EnvAmt")), "*~ 2"))
    idx = mul(s, s.ch(prm(s, P("Index")), "expr~ 1.6*$v1*$v1"), s.to(ienv, "+~ 1"))
    o = s.to(fm2(s, f, ratio, idx, s.to(prm(s, P("Fdbk")), "*~ 0.25")), "*~ 0.3")
    return o, o


def pad_saws(s, ins, L):
    f, env, note = ins
    P = lambda n: S("pad", "saws", n)
    d = s.ch(prm(s, P("Detune")), "expr~ $v1*$v1*0.02")
    saws = []
    for k in (-1, 0, 1):
        fk = f if k == 0 else mul(s, f, s.ch(d, f"*~ {k}", "+~ 1"))
        e = s.obj("expr~ " + saw_expr())
        s.c(s.to(fk, "phasor~"), 0, e, 0)
        s.c(dt_of(s, fk), 0, e, 1)
        saws.append(e)
    sp = s.ch(prm(s, P("Spread")), "*~ 0.5")
    hi = s.to(sp, "+~ 0.5")
    lo = s.ch(sp, "*~ -1", "+~ 0.5")
    cen = mul(s, saws[1], prm(s, P("Centre")))
    L = add(s, add(s, mul(s, saws[0], hi), mul(s, saws[2], lo)), cen)
    R = add(s, add(s, mul(s, saws[0], lo), mul(s, saws[2], hi)), cen)
    return s.to(L, "*~ 0.28"), s.to(R, "*~ 0.28")


def pad_pwm(s, ins, L):
    f, env, note = ins
    P = lambda n: S("pad", "pwm", n)
    ph = s.to(f, "phasor~")
    dt = dt_of(s, f)
    lfo = s.ch(s.recv(f"al-s{P('Rate')}"), "expr 0.05*pow(100, $f1)", "osc~")
    dep = mul(s, lfo, s.to(prm(s, P("Depth")), "*~ 0.4"))
    w0 = s.ch(prm(s, P("Width")), "*~ 0.9", "+~ 0.05")
    sp = prm(s, P("Spread"))
    # the right side's modulation: the same (Spread 0) .. mirrored (Spread 1)
    depR = mul(s, dep, s.ch(sp, "*~ -2", "+~ 1"))
    outs = []
    for d in (dep, depR):
        w = s.to(add(s, w0, d), "clip~ 0.03 0.97")
        e = s.obj("expr~ " + pulse_expr())
        s.c(ph, 0, e, 0)
        s.c(dt, 0, e, 1)
        s.c(w, 0, e, 2)
        outs.append(s.to(e, "*~ 0.2"))
    return outs[0], outs[1]


def pad_wave(s, ins, L):
    from wavetables import TABLES, STRIDE, CYCLE
    f, env, note = ins
    P = lambda n: S("pad", "wave", n)
    nt = len(TABLES)
    # the table: its array name (set on every reader) and its frame count
    tsel = s.ch(s.recv(f"al-s{P('Table')}"), f"expr min({nt - 1}, int($f1*{nt}))", "change -1")
    names = s.obj("sel " + " ".join(str(i) for i in range(nt)))
    s.c(tsel, 0, names, 0)
    readers = []
    nfr = s.obj("f 1")
    for i, (tn, frames, _) in enumerate(TABLES):
        m = s.m((names, i), f"set alwt-{tn}")
        readers.append(m)
        s.c(s.m((names, i), str(len(frames))), 0, nfr, 0)
    pos = cx(s, [P("Pos"), P("Table")], f"{a(P('Pos'))}")
    # frames - 1 as a signal (each table change)
    fm1 = s.ch(nfr, "- 1", "sig~")
    fpos = mul(s, pos, fm1)
    mode = prm(s, P("Mode"))           # 0..1: < 0.5 = 8-bit, above = smooth
    gsm = s.ch(mode, "expr~ $v1 >= 0.5")
    g8 = s.ch(gsm, "*~ -1", "+~ 1")
    shim = s.to(prm(s, P("Shimr")), "*~ 0.5")
    det = s.ch(prm(s, P("Detune")), "expr~ 1 + $v1*$v1*0.008")

    def read(fr):
        ph = s.to(fr, "phasor~")
        idx = s.to(ph, f"*~ {CYCLE}")
        lo = s.to(fpos, "expr~ floor($v1)")
        frac = sub(s, fpos, lo)
        hi2 = s.obj("expr~ min($v1 + 1, $v2)")
        s.c(lo, 0, hi2, 0)
        s.c(fm1, 0, hi2, 1)
        r = []
        for fr_i in (lo, hi2):
            t = s.obj("tabread4~ alwt-amble")
            for m in readers:
                s.c(m, 0, t, 0)
            s.c(add(s, s.to(fr_i, f"*~ {STRIDE}"), s.to(idx, "+~ 1")), 0, t, 0)
            r.append(t)
        smooth = add(s, r[0], mul(s, sub(s, r[1], r[0]), frac))
        # 8-bit: the nearest frame, the sample without interpolation, rounded to 8 bits
        rnd = s.to(fpos, "expr~ floor($v1 + 0.5)")
        t8 = s.obj("tabread~ alwt-amble")
        for m in readers:
            s.c(m, 0, t8, 0)
        s.c(add(s, s.to(rnd, f"*~ {STRIDE}"), s.ch(idx, "expr~ floor($v1) + 1")), 0, t8, 0)
        q8 = s.to(t8, "expr~ floor($v1*127 + 0.5)/127")
        return add(s, mul(s, smooth, gsm), mul(s, q8, g8))

    L0 = read(f)
    R0 = read(mul(s, f, det))
    sh = mul(s, read(s.to(f, "*~ 2")), shim)
    return s.to(add(s, L0, sh), "*~ 0.32"), s.to(add(s, R0, sh), "*~ 0.32")


# =========================================================================================== percussion
def _env(s, up, amp, att, dec, sq=True):
    """a struck envelope from the strike's [unpack f f f] (hz vel dec): peak vel x amp after att ms, then down to 0
    over dec ms (expressions; $f1 hz, $f2 vel, $f3 the layer's decay in ms). Squared: an exponential-like fall"""
    ex = s.obj(f"expr $f2*({amp}); {dec}")
    s.c((up, 2), 0, ex, 2)
    s.c((up, 1), 0, ex, 1)
    s.c((up, 0), 0, ex, 0)
    pk = s.obj("pack f f")
    s.c(ex, 1, pk, 1)
    s.c(ex, 0, pk, 0)
    e = s.ch(s.m(pk, f"$1 {att}, 0 $2 {att}"), "vline~")
    return mul(s, e, e) if sq else e


def _partials(s, up, hzs, parts, bright="1"):
    """sine partials: (ratio, amp, decay factor); the upper ones x bright"""
    sm = s.obj("*~ 1")
    for k, (r, amp, df) in enumerate(parts):
        fr = s.to((up, 0), f"* {r}") if not isinstance(r, str) else s.to((up, 0), f"expr $f1*{r}")
        o = s.ch(fr, "osc~")
        s.c(s.m(s.to((up, 0), "t b"), "0"), 0, o, 1)        # (each strike from phase 0: a clean onset)
        e = _env(s, up, f"{amp}" + (f"*{bright}" if k else ""), 1, f"$f3*{df}")
        s.c(mul(s, o, e), 0, sm, 0)
    return sm


def perc_blip(s, ins, L):
    (strike,) = ins
    P = lambda n: S(L, "blip", n)
    up = s.to(strike, "unpack f f f")
    # pitch: a flick down from up to an octave above in 2 .. 100 ms
    fl = s.obj(f"expr $f1*(1 + {a(P('Flick'))}); $f1; 2*pow(50, {a(P('FlTime'))})")
    s.c((up, 0), 0, fl, 0)
    pk = s.obj("pack f f f")
    for i in (2, 1, 0):
        s.c(fl, i, pk, i)
    fv = s.ch(s.m(pk, "$1, $2 $3"), "vline~")
    saw = s.obj("expr~ " + saw_expr())
    s.c(s.to(fv, "phasor~"), 0, saw, 0)
    s.c(dt_of(s, fv), 0, saw, 1)
    subo = mul(s, s.ch(s.to(fv, "*~ 0.5"), "osc~"), s.to(prm(s, P("Sub")), "*~ 0.7"))
    src = add(s, saw, subo)
    # the filter: from 2 .. 11 x the note (by velocity, x Cutoff) down to 1.2 x over a share of the decay
    cxp = s.obj(f"expr $f1*(2 + 9*$f2)*(0.25 + 1.5*{a(P('Cutoff'))}); $f1*1.2; $f3*(0.05 + 0.6*{a(P('FEnv'))})")
    s.c((up, 2), 0, cxp, 2)
    s.c((up, 1), 0, cxp, 1)
    s.c((up, 0), 0, cxp, 0)
    ck = s.obj("pack f f f")
    for i in (2, 1, 0):
        s.c(cxp, i, ck, i)
    cf = s.ch(s.m(ck, "$1, $2 $3"), "vline~", "clip~ 30 7000")      # (vcf~: stable below 7 kHz with Q >= 1.5)
    vf = s.obj("vcf~ 4")
    s.c(s.ch(s.recv(f"al-s{P('Reso')}"), "expr 1.5 + 10*$f1"), 0, vf, 2)
    s.c(src, 0, vf, 0)
    s.c(cf, 0, vf, 1)
    o = s.to(mul(s, (vf, 1), _env(s, up, 0.6, 2, "$f3")), "*~ 1.1")
    return o, o


def perc_lpg(s, ins, L):
    (strike,) = ins
    P = lambda n: S(L, "lpg", n)
    up = s.to(strike, "unpack f f f")
    fd = s.to(_env(s, up, f"3*2*{a(P('Fold'))}", 1, f"$f3*(0.1 + 0.9*{a(P('FoldDc'))})", sq=False), "+~ 0.6")
    o = s.to((up, 0), "osc~")
    s.c(s.m(s.to((up, 0), "t b"), "0"), 0, o, 1)
    fo = s.ch(mul(s, o, fd), "*~ 0.25", "-~ 0.25", "cos~")
    # the gate: one envelope closes the low-pass (the note + 500 .. 12000 Hz, down to the note) and the level;
    # Vactrl slows its close
    cf = s.to(add(s, s.to((up, 0), "sig~"),
                  _env(s, up, f"500 + 6500*{a(P('Open'))}*{a(P('Open'))}", 1, f"$f3*(0.3 + 0.7*{a(P('Vactrl'))})",
                       sq=False)), "clip~ 30 7000")
    lp = s.obj("vcf~ 1.5")
    s.c(s.ch(s.recv(f"al-s{P('Reso')}"), "expr 1.5 + 6*$f1"), 0, lp, 2)
    s.c(fo, 0, lp, 0)
    s.c(cf, 0, lp, 1)
    out = s.to(mul(s, (lp, 1), _env(s, up, 0.55, 1, "$f3")), "*~ 0.9")
    return out, out


BOWL = [(1, 0.45, 1.0, 0.6), (2.76, 0.26, 0.75, 1.1), (5.40, 0.13, 0.45, 0), (8.93, 0.07, 0.3, 0)]


def perc_bowl(s, ins, L):
    (strike,) = ins
    P = lambda n: S(L, "bowl", n)
    up = s.to(strike, "unpack f f f")
    st = a(P("Strtch"))
    parts = [(f"pow({r}, 1 + 0.25*{st})" if r != 1 else 1, amp, d) for r, amp, d, _ in BOWL]
    sig = _partials(s, up, None, parts, bright=f"(0.4 + 1.2*{a(P('Hard'))})")
    for r, amp, d, tw in BOWL:
        if tw:      # the mode's twin, a little up: the slow beating of a real bowl (Beat: x0 .. x2)
            fr = s.to((up, 0), f"expr $f1*pow({r}, 1 + 0.25*{st}) + {tw}*2*{a(P('Beat'))}")
            o = s.to(fr, "osc~")
            s.c(mul(s, o, _env(s, up, amp * 0.6, 2, f"$f3*{d}")), 0, sig, 0)
    kn = mul(s, s.obj("noise~"), _env(s, up, f"0.5*{a(P('Strike'))}", 0.5, "5"))
    bp = s.obj("bp~ 1000 3")
    s.c(kn, 0, bp, 0)
    s.c(s.to((up, 0), "* 2"), 0, bp, 1)
    s.c(bp, 0, sig, 0)
    o = s.to(sig, "*~ 0.5")
    return o, o


def perc_wood(s, ins, L):
    (strike,) = ins
    P = lambda n: S(L, "wood", n)
    up = s.to(strike, "unpack f f f")
    m = a(P("Matrl"))      # marimba (1, 3.93, 9.2) .. a woodblock (1, 2.4, 5.1)
    parts = [(1, 0.5, 1.0), (f"(3.93 - 1.53*{m})", 0.2, 0.2), (f"(9.2 - 4.1*{m})", 0.07, 0.06)]
    sig = _partials(s, up, None, parts, bright=f"(2*{a(P('Mallet'))})")
    kn = mul(s, s.obj("noise~"), _env(s, up, f"0.9*2*{a(P('Knock'))}", 0.5, "9"))
    bp = s.obj("bp~ 1000 2")
    s.c(kn, 0, bp, 0)
    s.c(s.to((up, 0), "* 2.5"), 0, bp, 1)
    s.c(bp, 0, sig, 0)
    o = s.to(sig, "*~ 0.6")
    return o, o


def perc_metal(s, ins, L):
    (strike,) = ins
    P = lambda n: S(L, "metal", n)
    up = s.to(strike, "unpack f f f")
    sig = _partials(s, up, None, [(1, 0.4, 1.0), (4.0, 0.12, 0.3), (10.0, 0.05, 0.08)],
                    bright=f"(2*{a(P('Bright'))})")
    tw = s.to(s.to((up, 0), f"expr $f1 + 2*{a(P('Beat'))}"), "osc~")
    s.c(mul(s, tw, _env(s, up, 0.14, 2, "$f3")), 0, sig, 0)
    rate = s.ch(s.recv(f"al-s{P('TremR')}"), "expr 2 + 7*$f1", "osc~")
    tr = add(s, mul(s, rate, s.to(prm(s, P("TremD")), "*~ 0.5")), s.ch(prm(s, P("TremD")), "*~ -0.5", "+~ 1"))
    o = s.to(mul(s, sig, tr), "*~ 0.9")
    return o, o


BUILD = {
    ("drone", "analog"): drone_analog, ("drone", "fm"): drone_fm, ("drone", "spectr"): drone_spectr,
    ("sub", "sine"): sub_sine, ("sub", "warm"): sub_warm, ("sub", "pulse"): sub_pulse, ("sub", "fm"): sub_fm,
    ("pad", "sine"): pad_sine, ("pad", "fm"): pad_fm, ("pad", "saws"): pad_saws, ("pad", "pwm"): pad_pwm,
    ("pad", "wave"): pad_wave,
    ("perc", "blip"): perc_blip, ("perc", "lpg"): perc_lpg, ("perc", "bowl"): perc_bowl, ("perc", "wood"): perc_wood,
    ("perc", "metal"): perc_metal,
}
