"""The second set of engines: the rest of the pads, the drones frost / choir / bowed / gendy, and the wave strike.
After Amble's designs, raw (no character or reverb), with only Pd's own objects (no [expr~]: see engines.py), and
each with its own slow movement: every side and every voice on a cycle of its own, so a held chord keeps shifting.
Builders take (s, ins, L) and return (left, right), as in engines.py."""
from dsp import mul, add, sub, div, prm
from model import S
from engines import cx, a, pick, nopt, saw_n, pulse_n, floor_s, sweep_lp, widen


def vosc(c, rate, spread=0.13):
    """a slow sine at rate Hz, a little different in each voice ($1, the voice's number)"""
    o = c.obj(f"osc~ {rate}")
    c.c(c.ch(c.obj("loadbang"), "f $1", f"expr {rate}*(1 + {spread}*$f1)"), 0, o, 0)
    return o


def slow01(c, rate):
    """a slow cycle 0..1"""
    return c.ch(vosc(c, rate), "*~ 0.5", "+~ 0.5")


# =========================================================================================== pads
PART_SETS = ["harm", "bell", "fifths", "odd", "strtch"]
PART_RATIOS = [[2, 3, 4], [2.76, 5.4, 8.93], [1.5, 3, 4.5], [3, 5, 7], [2.02, 3.05, 4.1]]


def pad_vox(s, ins, L):
    """a saw through two vowel formants that drift; the right side sings the mirror vowel (Amble's vox)"""
    f, env, note = ins
    P = lambda n: S("pad", "vox", n)
    saw = saw_n(s, f)
    vw = cx(s, [P("Vowel")], f"0.6 + 0.8*{a(P('Vowel'))}")
    mo = prm(s, P("Motion"))
    l1 = mul(s, vosc(s, 0.031), mo)
    l2 = mul(s, vosc(s, 0.043), mo)
    c1 = mul(s, s.ch(l1, "*~ 225", "+~ 505"), vw)
    c2 = mul(s, s.ch(l2, "*~ 500", "+~ 1400"), vw)
    rq = s.ch(s.recv(f"al-s{P('Reso')}"), "expr 3 + 9*$f1; 5 + 12*$f1")
    body = mul(s, s.ch(saw, "lop~ 600"), s.to(prm(s, P("Body")), "*~ 0.5"))
    outs = []
    for sign in (1, -1):
        cf1 = c1 if sign == 1 else s.ch(c1, "*~ -1", "+~ 1010")
        cf2 = c2 if sign == 1 else s.ch(c2, "*~ -1", "+~ 2800")
        sm = s.obj("+~")
        for j, (cf, g) in enumerate(((cf1, 1.0), (cf2, 0.7))):
            v = s.obj("vcf~ 6")
            s.c(rq, j, v, 2)
            s.c(saw, 0, v, 0)
            s.c(cf, 0, v, 1)
            s.c(s.to(v, f"*~ {g}"), 0, sm, 0)
        s.c(body, 0, sm, 1)
        outs.append(s.to(sm, "*~ 0.57"))
    return outs[0], add(s, s.to(outs[0], "*~ 0.35"), s.to(outs[1], "*~ 0.8"))


def pad_part(s, ins, L):
    """four sines at a set of ratios, each swelling on its own cycle, tilted; the fundamental in the middle, the
    upper ones placed left and right (Spread) - Amble's partials"""
    f, env, note = ins
    P = lambda n: S("pad", "part", n)
    ns = len(PART_SETS)
    si = f"min({ns - 1}, int({a(P('Set'))}*{ns}))"
    Lo, Ro = s.obj("*~ 0.24"), s.obj("*~ 0.24")
    s.c(s.to(f, "osc~"), 0, Lo, 0)
    s.c(s.to(f, "osc~"), 0, Ro, 0)
    places = [(1.45, 0.15), (0.15, 1.45), (1.3, 0.35)]
    for k in range(3):
        r = cx(s, [P("Set")], pick([rr[k] for rr in PART_RATIOS], si))
        amp = cx(s, [P("Tilt")], f"1.3*pow({k + 2}, -(0.2 + 2*{a(P('Tilt'))}))")
        sw = s.to(mul(s, s.to(vosc(s, [0.037, 0.047, 0.059][k]), "-~ 1"), s.to(prm(s, P("Swell")), "*~ 0.45")), "+~ 1")
        p = mul(s, mul(s, s.to(mul(s, f, r), "osc~"), amp), sw)
        gl, gr = places[k]
        g = cx(s, [P("Spread")], f"1 + ({gl} - 1)*{a(P('Spread'))}; 1 + ({gr} - 1)*{a(P('Spread'))}", outs=2)
        s.c(mul(s, p, g[0]), 0, Lo, 0)
        s.c(mul(s, p, g[1]), 0, Ro, 0)
    return Lo, Ro


def pad_fold(s, ins, L):
    """a sine wavefolded (the cosine of a driven sine), ring-modulated by its sub-octave; the right side folds a
    little less and a hair sharp (Amble's fold). Bias: the fold's symmetry (even harmonics)"""
    f, env, note = ins
    P = lambda n: S("pad", "fold", n)
    dr0 = cx(s, [P("Fold")], f"0.5 + 7*{a(P('Fold'))}*{a(P('Fold'))}")
    dr = mul(s, dr0, s.to(mul(s, vosc(s, 0.037), s.to(prm(s, P("Motion")), "*~ 0.4")), "+~ 1"))
    bias = cx(s, [P("Bias")], f"-0.25 + ({a(P('Bias'))} - 0.5)*0.5")
    sb = s.to(mul(s, s.ch(f, "*~ 0.5", "osc~", "-~ 1"), s.to(prm(s, P("Sub")), "*~ 0.44")), "+~ 1")
    outs = []
    for k, d in ((1, 1.0), (0.75, 1.0017)):
        x = s.to(f if d == 1.0 else s.to(f, f"*~ {d}"), "osc~")
        u = s.ch(add(s, s.to(mul(s, x, dr), f"*~ {0.25 * k}"), bias), "cos~", "hip~ 20")
        outs.append(s.ch(mul(s, u, sb), "lop~ 5000", "*~ 0.34"))
    return outs[0], add(s, s.to(outs[0], "*~ 0.45"), s.to(outs[1], "*~ 0.7"))


def pad_pulsr(s, ins, L):
    """pulsar synthesis: each period starts a short windowed burst of a few sine cycles at a formant that sweeps
    slowly - between an insect and a choir; the right side's formant higher by Spread (Amble's pulsar)"""
    f, env, note = ins
    P = lambda n: S("pad", "pulsr", n)
    fm0 = cx(s, [P("Formnt")], f"350 + 2600*{a(P('Formnt'))}*{a(P('Formnt'))}")
    fs = mul(s, fm0, s.to(mul(s, vosc(s, 0.049), s.to(prm(s, P("Sweep")), "*~ 0.45")), "+~ 1"))
    cyc = cx(s, [P("Cycles")], f"1 + 5*{a(P('Cycles'))}")
    sp = prm(s, P("Spread"))
    ph = s.to(f, "phasor~")
    fmax = s.to(f, "max~ 1")
    outs = []
    for side in (0, 1):
        fx = fs if side == 0 else mul(s, fs, s.ch(sp, "*~ 0.36", "+~ 1"))
        u = s.ch(mul(s, ph, s.to(div(s, fx, fmax), "max~ 1")), "clip~ 0 1")
        win = s.ch(u, "cos~", "*~ -0.5", "+~ 0.5")
        car = s.to(mul(s, u, cyc), "cos~")
        outs.append(s.ch(mul(s, win, car), "hip~ 30", "*~ 0.8"))
    return outs[0], outs[1]


def pad_sync(s, ins, L):
    """a hard-synced saw: a slave at Ratio x the note, restarted each period, its ratio sweeping slowly - an
    electric lead; the right side's slave runs ahead by Detune (Amble's sync)"""
    f, env, note = ins
    P = lambda n: S("pad", "sync", n)
    ph = s.to(f, "phasor~")
    r0 = cx(s, [P("Ratio")], f"1.2 + 6*{a(P('Ratio'))}")
    lfo = s.ch(s.recv(f"al-s{P('Rate')}"), "expr 0.02*pow(50, $f1)", "osc~")
    ratio = mul(s, r0, s.to(mul(s, lfo, s.to(prm(s, P("Sweep")), "*~ 0.35")), "+~ 1"))
    win = s.ch(ph, "*~ -1", "+~ 1")
    off = s.to(prm(s, P("Detune")), "*~ 0.25")
    outs = []
    for side in (0, 1):
        r = ratio if side == 0 else add(s, ratio, off)
        sl = s.ch(mul(s, ph, r), "wrap~", "-~ 0.5")
        outs.append(s.ch(mul(s, sl, win), "lop~ 4500", "hip~ 30", "*~ 1.1"))
    return outs[0], outs[1]


def pad_cz(s, ins, L):
    """phase distortion (the Casio CZ): left, a cosine read through a bent phase - a sine (no bend) towards a saw;
    right, the resonant wave - a cosine at a higher ratio under a falling ramp. Bend sweeps slowly (Amble's cz)"""
    f, env, note = ins
    P = lambda n: S("pad", "cz", n)
    ph = s.to(f, "phasor~")
    amt = s.to(add(s, prm(s, P("Bend")), mul(s, vosc(s, 0.043), s.to(prm(s, P("Sweep")), "*~ 0.3"))), "clip~ 0 1")
    d = s.ch(amt, "*~ -0.44", "+~ 0.5")                     # the knee: 0.5 (a sine) .. 0.06 (near a saw)
    # the bent phase: min of the two lines through (d, 0.5) - steep below the knee, gentle above it
    a1 = div(s, s.to(ph, "*~ 0.5"), d)
    a2 = s.to(div(s, s.to(sub(s, ph, d), "*~ 0.5"), s.ch(d, "*~ -1", "+~ 1")), "+~ 0.5")
    bent = s.obj("min~")
    s.c(a1, 0, bent, 0)
    s.c(a2, 0, bent, 1)
    bw = s.ch(bent, "cos~", "hip~ 20", "lop~ 6000", "*~ 0.29")
    r = s.to(mul(s, s.to(amt, "*~ 5"), s.to(prm(s, P("Reso")), "*~ 2")), "+~ 1")
    rw = s.ch(mul(s, s.to(mul(s, ph, r), "cos~"), s.ch(ph, "*~ -1", "+~ 1")), "hip~ 20", "lop~ 4500", "*~ 0.4")
    mx = prm(s, P("Mix"))
    rwm = mul(s, rw, s.to(mx, "*~ 1.4"))
    return add(s, bw, s.to(rwm, "*~ 0.35")), add(s, rwm, s.to(bw, "*~ 0.45"))


VOWELS = [(800, 1150), (400, 1600), (350, 2000), (450, 800), (325, 700), (600, 1700), (500, 900), (700, 1500),
          (620, 1200)]                # F1 F2 (Hz): a e i o u, then between them


def _choir_mod(P, vtab):
    """the choir's slow parts at 1/16 of the audio rate (block 4: one parent block), held back up: per side the
    vibrato (x the pitch) and two formants, the vowel wandering on two unrelated cycles (Drift) from Vowel"""
    from pdlib import Canvas
    s = Canvas("choir-mod", w=1600)
    s.obj("block~ 4 1 0.0625")
    vo = s.to(prm(s, P("Vowel")), "-~ 0.5")
    dr = prm(s, P("Drift"))
    x = 20
    for side, (d, r1, r2) in enumerate(((1.0, 0.031, 0.047), (1.0025, 0.037, 0.043))):
        vib = s.ch(s.obj(f"osc~ {5.1 + 0.4 * side}"), "*~ 0.004", f"+~ {d}")
        s.c(vib, 0, s.obj("outlet~ hold", x, 900), 0)
        x += 150
        wander = mul(s, add(s, vosc(s, r1), s.ch(vosc(s, r2), "*~ 0.7")), dr)
        idx = s.to(add(s, s.ch(wander, "*~ 0.294", "+~ 0.5", f"*~ {len(VOWELS) - 1}", "+~ 1"), s.to(vo, "*~ 8")),
                   f"clip~ 1 {len(VOWELS)}")
        for j in range(2):
            s.c(s.to(idx, f"tabread4~ {vtab}{j}"), 0, s.obj("outlet~ hold", x, 900), 0)
            x += 150
    return s


def _vowel_tables(s, vtab):
    lb = s.obj("loadbang")
    for j in range(2):
        vals = [VOWELS[-1][j]] + [v[j] for v in VOWELS] + [VOWELS[0][j], VOWELS[1][j]]
        s.obj(f"array define {vtab}{j} {len(vals)}")
        s.c(s.m(lb, " ".join(str(x) for x in vals)), 0, s.obj(f"array set {vtab}{j}"), 0)


def pad_choir(s, ins, L):
    """a glottal source (narrow pulses: Bright) and a little breath through two formants that wander through nine
    vowels; the right side sings its own vowel a little apart, a hair sharp (Amble's choir)"""
    f, env, note = ins
    P = lambda n: S("pad", "choir", n)
    vtab = "$0-pcv"
    _vowel_tables(s, vtab)
    cm = s.sub(_choir_mod(P, vtab), 20, 200)
    expo = cx(s, [P("Bright")], f"12 - 8*{a(P('Bright'))}")
    br = mul(s, s.ch(s.obj("noise~"), "hip~ 300"), s.to(prm(s, P("Breath")), "*~ 0.25"))
    outs = []
    for side in (0, 1):
        ph = s.ch(mul(s, f, (cm, 3 * side)), "phasor~", "-~ 0.5", "*~ 2", "abs~")
        src = s.obj("pow~")
        s.c(ph, 0, src, 0)
        s.c(expo, 0, src, 1)
        x = add(s, s.to(src, "hip~ 60"), br)
        sm = s.obj("*~ 1")
        for j, (q, g) in enumerate(((7, 1.0), (10, 0.6))):
            v = s.obj(f"vcf~ {q}")
            s.c(x, 0, v, 0)
            s.c((cm, 3 * side + 1 + j), 0, v, 1)
            s.c(s.to(v, f"*~ {g}"), 0, sm, 0)
        outs.append(s.to(sm, "*~ 2.0"))
    return outs[0], outs[1]


def pad_vosim(s, ins, L):
    """VOSIM: each period, a train of three sin-squared pulses at a formant, each weaker by Decay - vowel-like,
    a little nasal; the formant sweeps slowly, the right side's higher by Spread (Amble's vosim, plain arithmetic)"""
    f, env, note = ins
    P = lambda n: S("pad", "vosim", n)
    ph = s.to(f, "phasor~")
    fm0 = cx(s, [P("Formnt")], f"400 + 2000*{a(P('Formnt'))}")
    fmt = mul(s, fm0, s.to(mul(s, vosc(s, 0.041), s.to(prm(s, P("Sweep")), "*~ 0.2")), "+~ 1"))
    fmax = s.to(f, "max~ 1")
    qm1 = s.ch(prm(s, P("Decay")), "*~ 0.7", "+~ -0.7")
    qm1h = s.to(mul(s, qm1, qm1), "*~ 0.5")
    sp = prm(s, P("Spread"))
    outs = []
    for side in (0, 1):
        fx = fmt if side == 0 else mul(s, fmt, s.ch(sp, "*~ 0.5", "+~ 1"))
        x = mul(s, ph, div(s, fx, fmax))
        n = sub(s, x, s.to(x, "wrap~"))
        s2 = s.ch(x, "cos~", "*~ -0.5", "+~ 0.5")
        gate = s.ch(n, "*~ -1", "+~ 3", "clip~ 0 1")
        amp = s.to(add(s, mul(s, n, qm1), mul(s, mul(s, n, s.to(n, "-~ 1")), qm1h)), "+~ 1")
        outs.append(s.ch(mul(s, mul(s, s2, gate), amp), "hip~ 40", "*~ 0.73"))
    return outs[0], outs[1]


LISSA_RATIOS = ["1:1", "3:2", "2:1", "4:3", "5:4"]
LISSA_R = [1, 1.5, 2, 1.33333, 1.25]


def pad_lissa(s, ins, L):
    """Lissajous: the two sides are the figure's axes - the note left, a ratio of it right, drifting in phase so
    the image turns; Bright adds each side's overtone, Cross lets each side into the other (Amble's lissa)"""
    f, env, note = ins
    P = lambda n: S("pad", "lissa", n)
    nr = len(LISSA_R)
    ratio = cx(s, [P("Ratio")], pick(LISSA_R, f"min({nr - 1}, int({a(P('Ratio'))}*{nr}))"))
    x = s.to(f, "osc~")
    y = s.to(add(s, mul(s, f, ratio), cx(s, [P("Drift")], f"0.4*{a(P('Drift'))}*{a(P('Drift'))}")), "osc~")
    b = prm(s, P("Bright"))
    bx = mul(s, s.ch(s.to(f, "*~ 2"), "osc~"), s.to(b, "*~ 0.35"))
    by = mul(s, s.ch(s.to(mul(s, f, ratio), "*~ 2"), "osc~"), s.to(b, "*~ 0.3"))
    cr = prm(s, P("Cross"))
    Lo = s.to(add(s, add(s, x, bx), mul(s, y, cr)), "*~ 0.26")
    Ro = s.to(add(s, add(s, y, by), mul(s, x, cr)), "*~ 0.26")
    return Lo, Ro


CHIP_DUTY = ["12%", "25%", "50%"]


def pad_chip(s, ins, L):
    """a game console's channels, raw: left a pulse of a stepped duty, unfiltered; right the 4-bit triangle;
    Tri crosses them; Crush holds the sample rate down; a vibrato that comes in late (Amble's chip)"""
    f, env, note = ins
    P = lambda n: S("pad", "chip", n)
    late = slow01(s, 0.09)
    vib = mul(s, mul(s, s.ch(s.obj("osc~ 5.6"), "*~ 0.008"), late), prm(s, P("Vib")))
    ph = s.to(mul(s, f, s.to(vib, "+~ 1")), "phasor~")
    duty = cx(s, [P("Duty")], pick([0.125, 0.25, 0.5], f"min(2, int({a(P('Duty'))}*3))"))
    pulse = s.ch(sub(s, duty, ph), "*~ 1e+06", "clip~ 0 1", "*~ 2", "-~ 1")
    t = s.ch(ph, "*~ 4", "-~ 2", "abs~", "*~ -1", "+~ 1")              # -1..1
    tri = s.ch(floor_s(s, s.ch(t, "+~ 1", "*~ 7.99")), "*~ 0.1333", "-~ 1")
    hold = s.to(cx(s, [P("Crush")], f"22050*pow(0.125, {a(P('Crush'))})"), "phasor~")
    tr = prm(s, P("Tri"))
    mixes = (add(s, pulse, mul(s, tri, s.to(tr, "*~ 0.6"))), add(s, tri, mul(s, pulse, s.ch(tr, "*~ -0.6", "+~ 0.6"))))
    outs = []
    for x in mixes:
        sh = s.obj("samphold~")
        s.c(x, 0, sh, 0)
        s.c(hold, 0, sh, 1)
        outs.append(s.ch(sh, "hip~ 20", "*~ 0.2"))
    return outs[0], outs[1]


def pad_vector(s, ins, L):
    """vector synthesis (as the Prophet VS): four sources at the corners of a square - a sine, a saw (Detune
    apart), a 25 % pulse and a triangle an octave up - mixed by a point (X, Y) that circles (Orbit, Rate); the right
    side's point a quarter turn ahead, so the two sides hear different mixes and the image moves"""
    f, env, note = ins
    P = lambda n: S("pad", "vector", n)
    A = s.to(f, "osc~")
    B = saw_n(s, mul(s, f, cx(s, [P("Detune")], f"1 + 0.012*{a(P('Detune'))}*{a(P('Detune'))}")))
    C = pulse_n(s, s.to(f, "phasor~"), s.obj("sig~ 0.25"))
    D = s.ch(s.to(f, "*~ 2"), "phasor~", "-~ 0.5", "abs~", "*~ 4", "-~ 1")
    rate = s.ch(s.recv(f"al-s{P('Rate')}"), "expr 0.01*pow(40, $f1)", "t f f")
    oc, os_ = s.obj("osc~"), s.obj("osc~")
    s.c((rate, 1), 0, oc, 0)
    s.c((rate, 0), 0, os_, 0)
    s.c(s.m(s.obj("loadbang"), "0.25"), 0, os_, 1)         # (a quarter turn: sine against cosine)
    rad = s.to(prm(s, P("Orbit")), "*~ 0.5")
    X, Y = prm(s, P("X")), prm(s, P("Y"))
    outs = []
    for cx_, cy_ in ((oc, os_), (os_, s.to(oc, "*~ -1"))):
        x = s.to(add(s, X, mul(s, cx_, rad)), "clip~ 0 1")
        y = s.to(add(s, Y, mul(s, cy_, rad)), "clip~ 0 1")
        nx, ny = s.ch(x, "*~ -1", "+~ 1"), s.ch(y, "*~ -1", "+~ 1")
        sm = s.obj("*~ 0.55")
        for src, wx, wy in ((A, nx, ny), (B, x, ny), (C, nx, y), (D, x, y)):
            s.c(mul(s, src, mul(s, wx, wy)), 0, sm, 0)
        outs.append(sm)
    return outs[0], outs[1]


# =========================================================================================== drones
def drone_frost(s, ins, L):
    """three detuned saws - centre, a little flat left, a little sharp right - each drifting on its own, through a
    resonant low-pass on the note and Bright; under them noise through three glassy resonators on the note (x1, x2,
    x3) - Amble's frost, after Frasil"""
    f, env, note = ins
    P = lambda n: S("drone", "frost", n)
    det, drf = prm(s, P("Detune")), s.to(prm(s, P("Drift")), "*~ 0.005")
    saws = []
    for cents, rate in ((0, 0.023), (-9, 0.031), (9, 0.037)):
        dk = s.to(mul(s, s.to(det, f"*~ {2 ** (cents / 1200) - 1:.6f}"), s.obj("sig~ 1")), "+~ 1") if cents else s.obj("sig~ 1")
        dk = add(s, dk, mul(s, s.obj(f"osc~ {rate}"), drf))
        saws.append(saw_n(s, mul(s, f, dk)))
    br = cx(s, [P("Bright")], f"1.5 + 8*{a(P('Bright'))}*{a(P('Bright'))}")
    cf = s.to(mul(s, f, add(s, br, s.ch(s.obj("osc~ 0.019"), "*~ 0.6"))), "clip~ 40 6000")
    outs = []
    for side in (0, 1):
        v = s.obj("vcf~ 2.5")
        s.c(add(s, s.to(saws[0], "*~ 0.6"), saws[1 + side]), 0, v, 0)
        s.c(cf, 0, v, 1)
        outs.append(s.to((v, 1), "*~ 0.56"))
    nz = s.obj("noise~")
    gl = s.to(prm(s, P("Glass")), "*~ 2")
    for k, (h, q) in enumerate(((1, 30), (2, 40), (3, 50))):
        r = s.obj(f"vcf~ {q}")
        s.c(nz, 0, r, 0)
        s.c(s.to(f, f"*~ {h}"), 0, r, 1)
        s.c(mul(s, s.to(r, f"*~ {0.45 / h:.3f}"), gl), 0, outs[k % 2], 0)
    return outs[0], outs[1]


def drone_choir(s, ins, L):
    """three voices a side (the note, a hair apart, and the fifth: Fifth) - glottal pulses (Breath: wider,
    breathier) through two formants that move slowly between ah, oh and oo (Drift) from Vowel (Amble's choir drone)"""
    f, env, note = ins
    P = lambda n: S("drone", "choir", n)
    vw = s.to(mul(s, s.ch(s.obj("osc~ 0.023"), "*~ 0.5"), prm(s, P("Drift"))), "+~ 0.5")
    vs = cx(s, [P("Vowel")], f"0.6 + 0.8*{a(P('Vowel'))}")
    f1, f2 = mul(s, s.ch(vw, "*~ 300", "+~ 450"), vs), mul(s, s.ch(vw, "*~ 350", "+~ 800"), vs)
    pex = cx(s, [P("Breath")], f"12 - 8*{a(P('Breath'))}")
    fifth = prm(s, P("Fifth"))
    outs = []
    for side, voices in enumerate((((1.0, 4.9), (1.5, 5.3)), ((1.003, 5.1), (1.5, 5.6)))):
        src = s.obj("*~ 1")
        for ratio, vr in voices:
            vib = s.ch(s.obj(f"osc~ {vr}"), "*~ 0.004", f"+~ {ratio}")
            pw = s.obj("pow~")
            s.c(s.ch(mul(s, f, vib), "phasor~", "-~ 0.5", "*~ 2", "abs~"), 0, pw, 0)
            s.c(pex, 0, pw, 1)
            s.c(pw if ratio != 1.5 else mul(s, pw, fifth), 0, src, 0)
        sm = s.obj("+~")
        for fm, q in ((f1, 6), (f2, 9)):
            v = s.obj(f"vcf~ {q}")
            s.c(s.to(src, "hip~ 50"), 0, v, 0)
            s.c(fm, 0, v, 1)
            s.c(v, 0, sm, 0)
        outs.append(s.to(sm, "*~ 3.6"))
    return outs[0], outs[1]


def drone_bowed(s, ins, L):
    """a cello on the note: a saw with a slow bow-pressure swell (Press, Swell) and a light vibrato (Vib), through
    the body's resonances (about 200, 500 and 1300 Hz: Body) and a soft low-pass (Amble's bowed drone)"""
    f, env, note = ins
    P = lambda n: S("drone", "bowed", n)
    press, swell = prm(s, P("Press")), prm(s, P("Swell"))
    vd = s.to(prm(s, P("Vib")), "*~ 0.006")
    body = s.to(prm(s, P("Body")), "*~ 2")
    outs = []
    for d, vr, pr in ((1.0, 4.7, 0.11), (0.9985, 5.2, 0.09)):
        vib = s.to(mul(s, s.obj(f"osc~ {vr}"), vd), f"+~ {d}")
        saw = saw_n(s, mul(s, f, vib))
        sw = s.to(mul(s, s.ch(s.obj(f"osc~ {pr}"), "*~ 0.5", "-~ 0.5"), swell), "+~ 1")
        x = mul(s, mul(s, saw, sw), s.to(press, "*~ 2"))
        sm = s.obj("*~ 1")
        s.c(s.to(x, "lop~ 1600"), 0, sm, 0)
        for hz, q, g in ((200, 4, 0.6), (500, 5, 0.5), (1300, 6, 0.3)):
            bp = s.obj(f"bp~ {hz} {q}")
            s.c(x, 0, bp, 0)
            s.c(mul(s, s.to(bp, f"*~ {g}"), body), 0, sm, 0)
        outs.append(s.to(sm, "*~ 0.24"))
    return outs[0], outs[1]


GENDY_N = 12


def drone_gendy(s, ins, L):
    """GENDY (Xenakis' dynamic stochastic synthesis), gently: a wave of 12 breakpoints read at the pitch; every
    30 ms each breakpoint takes a small step (Steps; mirrored at the edges), so the timbre keeps breathing while the
    pitch holds. Its walk is seeded, so it starts the same way each time. Rough: its smoothing; Spread: the right
    side reads the same wave a little sharp"""
    from model import engines
    f, env, note = ins
    P = lambda n: S("drone", "gendy", n)
    tab = "$0-gtab"
    s.obj(f"array define {tab} {GENDY_N + 3}")
    # the walk runs only while gendy is the drone's engine
    names = [e for e, _ in engines("drone")]
    met = s.obj("metro 30")
    s.c(s.ch(s.recv(f"al-s{S('drone', None, 'Engine')}"),
             f"expr min({len(names) - 1}, int($f1*{len(names)})) == {names.index('gendy')}", "change"), 0, met, 0)
    rnd = s.to(met, "t b b b")
    cnt = s.obj("f")
    s.c(s.m((rnd, 2), "0"), 0, cnt, 1)
    s.c(s.ch(s.m((rnd, 1), str(GENDY_N)), "until"), 0, cnt, 0)
    s.c(s.to(cnt, "+ 1"), 0, cnt, 1)
    ix = s.ch(cnt, "+ 1", "t f f")
    tw = s.obj(f"tabwrite {tab}")
    s.c(ix, 1, tw, 1)
    rd = s.ch((ix, 0), f"tabread {tab}", "t f b")
    rn = s.obj("random 1000")
    s.c(s.m(s.obj("loadbang"), "seed 7"), 0, rn, 0)
    w = f"($f2/1000 - 0.5)*0.4*{a(P('Steps'))}"
    stp = s.obj(f"expr if($f1 + {w} > 0.95, 1.9 - $f1 - {w}, if($f1 + {w} < -0.95, -1.9 - $f1 - {w}, $f1 + {w}))")
    s.c(s.to((rd, 1), "t b"), 0, rn, 0)
    s.c(rn, 0, stp, 1)
    s.c((rd, 0), 0, stp, 0)
    s.c(stp, 0, tw, 0)
    g = s.to((rnd, 0), "t b b")
    s.c(s.ch(s.m((g, 1), f"{GENDY_N} 1"), f"array get {tab}"), 0, s.obj(f"array set {tab} 0"), 0)
    s.c(s.ch(s.m((g, 0), "1 2"), f"array get {tab}"), 0, s.obj(f"array set {tab} {GENDY_N + 1}"), 0)
    sp = cx(s, [P("Spread")], f"1 + 0.006*{a(P('Spread'))}")
    rough = s.ch(s.recv(f"al-s{P('Rough')}"), "expr 400*pow(16, $f1)")
    outs = []
    for side in (0, 1):
        fr = f if side == 0 else mul(s, f, sp)
        rdx = s.ch(fr, "phasor~", f"*~ {GENDY_N}", "+~ 1", f"tabread4~ {tab}")
        lp = s.to(rdx, "lop~ 1800")
        s.c(rough, 0, lp, 1)
        outs.append(s.ch(lp, "lop~ 3000", "*~ 0.55"))
    return outs[0], outs[1]


# =========================================================================================== percussion
def perc_wave(s, ins, L):
    """a struck wavetable: it strikes on a brighter frame (Bright: how far along the table) and settles to its body
    frame (Pos) over a quarter of the decay, with a faint octave shimmer (Shimr) - Amble's wave strike, on the
    shared bank (Table)"""
    from wavetables import TABLES, STRIDE, CYCLE
    from engines import _env
    (strike,) = ins
    P = lambda n: S(L, "wave", n)
    nt = len(TABLES)
    from userwaves import table_select
    readers, nfr = table_select(s, P("Table"))          # (the factory tables, then your own: user1 .. 8)
    up = s.to(strike, "unpack f f f")
    # at each strike: the two frames' starts in the table (body, bright)
    pos, bri = a(P("Pos")), a(P("Bright"))
    fr = s.obj(f"expr int({pos}*($f2 - 1) + 0.5)*{STRIDE} + 1; "
               f"min($f2 - 1, int(({pos} + {bri})*($f2 - 1) + 0.5))*{STRIDE} + 1")
    s.c(nfr, 0, fr, 1)
    s.c(s.to((up, 0), "t b"), 0, fr, 0)
    for k in ("Pos", "Bright"):         # (live: a ringing hit moves through the table as they move)
        s.c(s.ch(s.recv(f"al-s{P(k)}"), "t b"), 0, fr, 0)
    fs = s.to((up, 0), "sig~")
    ph = s.obj("phasor~")
    s.c(fs, 0, ph, 0)
    s.c(s.m(s.to((up, 0), "t b"), "0"), 0, ph, 1)
    idx = s.to(ph, f"*~ {CYCLE}")
    reads = []
    for k in (0, 1):
        t = s.obj("tabread4~ alwt-amble")
        for m in readers:
            s.c(m, 0, t, 0)
        s.c(add(s, idx, s.to((fr, k), "sig~")), 0, t, 0)
        reads.append(t)
    me = _env(s, up, "1", 1, "$f3*0.25", sq=False)
    body = add(s, reads[0], mul(s, sub(s, reads[1], reads[0]), s.to(me, "clip~ 0 1")))
    oct_ = s.obj("tabread4~ alwt-amble")
    for m in readers:
        s.c(m, 0, oct_, 0)
    ph2 = s.ch(s.to(fs, "*~ 2.003"), "phasor~", f"*~ {CYCLE}")
    s.c(add(s, ph2, s.to((fr, 1), "sig~")), 0, oct_, 0)
    sh = mul(s, oct_, s.to(prm(s, P("Shimr")), "*~ 0.3"))
    o = s.to(mul(s, add(s, body, sh), _env(s, up, 0.45, 3, "$f3")), "*~ 0.9")
    return o, o            # (mono, as every strike: the lane places its voices)


BUILD2 = {
    ("pad", "vox"): pad_vox, ("pad", "part"): pad_part, ("pad", "fold"): pad_fold, ("pad", "pulsr"): pad_pulsr,
    ("pad", "sync"): pad_sync, ("pad", "cz"): pad_cz, ("pad", "choir"): pad_choir, ("pad", "vosim"): pad_vosim,
    ("pad", "lissa"): pad_lissa, ("pad", "chip"): pad_chip, ("pad", "vector"): pad_vector,
    ("drone", "frost"): drone_frost, ("drone", "choir"): drone_choir, ("drone", "bowed"): drone_bowed,
    ("drone", "gendy"): drone_gendy,
    ("perc", "wave"): perc_wave,
}
