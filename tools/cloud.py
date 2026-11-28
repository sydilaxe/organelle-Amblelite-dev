"""The cloud: three engines on its sources - the other layers (their buses after their levels), the audio input,
or both - one playing at a time (Engine: the LAYERS page or its LAYER page; the others switched off).

grains  an 8 s rolling recording (a delay line: [delwrite~ al-cbuf]), always recording, so it is ready when the
        cloud comes in. Grain streams read it back ([delread4~]): each grain a raised-cosine window of Size (30 ms
        .. 2 s), read Scan back in time (plus Jitter), transposed by moving its read point (a ratio from the pitch
        set: unison, octaves, fifths, the chord's tones, shimmer), some reversed (Reverse), each placed in the stereo
        field (Spread). Density: how many play. Its position, reversal and place are drawn at each grain's start.
rhythm  the same recording, read in time with the piece: three levels - Rate, then twice and four times as fine -
        each a Euclidean pattern of 8 steps (Densty: its hits) whose hits strike a grain (Size: its share of the
        step), so the levels cascade one into the next (Cascad: how many sound); Morph rotates each level its own
        amount - the patterns morph against each other. Each grain at its own place (Spread), read from Scan back
        (plus Jitter).
delay   a digital delay after the Digitech RDS-8000: Time 20 ms .. 3 s, Fdbk (to just over unity, held by a soft
        limit), Width (the right side longer, the repeats crossing between the sides), Mod (the time wavering:
        chorus to tape warble), Pitch (each repeat shifted by an interval: rising or falling cascades), Hold (hold:
        the loop kept, repeating forever, nothing new in - dub: kept, and what plays is added to it), Tone (the
        repeats darkening).

Out: each engine fades in and out over 40 ms as Engine changes, and is switched off once out (the recording
goes on)."""
from pdlib import Canvas, proc, V, T, If, Loop, SendL, Call
from dsp import mul, add, sub, div, prm
import model as M
from model import S
from control import opt, num

STREAMS = 4
BUF_MS = 8000
DEL_MS = 3600
ENGS = [e for e, _ in M.engines("cloud")]


def P(n):
    return S("cloud", "grains", n)


def build():
    c = Canvas("cloud", w=2600, h=1400)
    c.comment("the cloud's recording: its source (the playing engine's Source), always")
    eng = S("cloud", None, "Engine")
    srcs = [S("cloud", e, "Source") for e in ENGS]
    n = len(ENGS)
    pick = f"alp[{srcs[-1]}]"
    for k in range(n - 2, -1, -1):
        pick = f"if(min({n - 1}, int(alp[{eng}]*{n})) == {k}, alp[{srcs[k]}], {pick})"
    ex = c.obj(f"expr min(2, int(({pick})*3))")
    for sl in [eng] + srcs:
        c.c(c.ch(c.recv(f"al-s{sl}"), "t b"), 0, ex, 0)
    gsrc = c.to(ex, "t f f")
    # (layers: 1 0; input: 0 1; both: 1 1)
    gl = c.ch((gsrc, 1), "expr $f1 != 1", "pack f 50", "line~")
    gi = c.ch((gsrc, 0), "expr $f1 >= 1", "pack f 50", "line~")
    lr = []
    for side, inp in (("L", "inL"), ("R", "inR")):
        x = add(c, mul(c, c.obj(f"catch~ al-csrc{side}"), gl), mul(c, c.obj(f"r~ {inp}"), gi))
        c.c(x, 0, c.obj(f"s~ al-crec{side}"), 0)        # (the delay's input: stereo)
        lr.append(x)
    c.c(c.to(add(c, *lr), "*~ 0.5"), 0, c.obj(f"delwrite~ al-cbuf {BUF_MS}"), 0)
    c.col(300)
    switch(c, eng)
    for name, fn in (("grains", _grains), ("rhythm", _rhythm), ("delay", _delay)):
        g = Canvas(name, w=2600, h=1400)
        c.sub(g)
        fn(g, ENGS.index(name))
    rhythm_clock(c)
    r = Canvas("ratios", w=1600)
    c.sub(r)
    ratios(r)
    return c


def switch(c, eng):
    """al-cl<k> 'want gain ms' to each engine: want - the cloud in and this engine chosen (its DSP on; off ms
    after it stops being wanted: 60 if the engine changed, after the fade if the cloud went out); gain - this
    engine chosen (a 40 ms fade between engines; the cloud's own in and out fade on its bus)"""
    li = M.LAYERS.index("cloud")
    n = len(ENGS)
    r = c.ch(c.recv(f"al-in{li}"), "t b l")
    up = c.to((r, 1), "unpack f f")
    c.c((up, 0), 0, c.obj("v alclin"), 0)
    c.c((up, 1), 0, c.obj("v alclfade"), 0)
    c.c((r, 0), 0, c.obj("s al-cloudsw"), 0)
    c.c(c.ch(c.recv(f"al-s{eng}"), "t b"), 0, c.obj("s al-cloudsw"), 0)
    e = f"min({n - 1}, int(alp[{eng}]*{n}))"
    proc(c, "al-cloudsw", [V("alcleng", e)] + [
        SendL(f"al-cl{k}", [f"alclin && alcleng == {k}", f"alcleng == {k}", "if(alclin, 60, alclfade + 100)"])
        for k in range(n)])


def engine_switch(c, k):
    """in an engine's canvas: its switch~ and its gain (a line~) from al-cl<k>"""
    sw = c.obj("switch~")
    c.c(c.m(c.obj("loadbang"), "0"), 0, sw, 0)
    up = c.ch(c.recv(f"al-cl{k}"), "unpack f f f")
    gain = c.ch(c.m((up, 1), "$1 40"), "line~")
    d = c.obj("delay")
    c.c((up, 2), 0, d, 1)
    sel = c.to(up, "sel 0")
    c.c(sel, 0, d, 0)
    c.c(c.m(d, "0"), 0, sw, 0)
    on = c.to((sel, 1), "t b b")
    c.c(c.m((on, 1), "stop"), 0, d, 0)
    c.c(c.m((on, 0), "1"), 0, sw, 0)
    return gain


def _grains(c, k):
    c.comment("the grain streams; on while the cloud is in and grains its engine")
    gain = engine_switch(c, k)
    # the grains' length (ms) and rate
    size = c.ch(c.recv(f"al-s{P('Size')}"), "expr 30*pow(66.67, $f1)", "t f f")
    rate = c.ch((size, 0), "expr 1000/$f1", "pack f 60", "line~")
    size_ms = c.ch((size, 1), "pack f 60", "line~")
    scan = c.ch(c.recv(f"al-s{P('Scan')}"), f"expr 20 + $f1*{BUF_MS - 2200}", "sig~")
    jit = c.ch(c.recv(f"al-s{P('Jitter')}"), f"expr $f1*{BUF_MS - 2500}", "sig~")
    revt = c.ch(c.recv(f"al-s{P('Revrse')}"), "expr 1 - $f1", "sig~")      # (a grain reverses when its draw is above)
    spread = c.ch(c.recv(f"al-s{P('Spread')}"), "sig~")
    dens = c.ch(c.recv(f"al-s{P('Densty')}"), f"expr 1 + $f1*{STREAMS - 1}")
    L, R = c.obj("*~ 0.45"), c.obj("*~ 0.45")
    for k in range(STREAMS):
        c.col(260)
        ph = c.obj("phasor~")
        c.c(rate, 0, ph, 0)
        c.c(c.m(c.obj("loadbang"), f"{k / STREAMS:.4f}"), 0, ph, 1)
        win = c.ch(ph, "cos~", "*~ -0.5", "+~ 0.5")
        # at each grain's start (the phasor wraps: samphold~ takes a new value): position, reversal, place
        pos = c.obj("samphold~")
        # (anywhere from Scan back to Scan + Jitter, kept inside the buffer: wide jitter is Amble's cloud)
        c.c(c.to(add(c, scan, mul(c, c.ch(c.obj("noise~"), "abs~"), jit)), f"clip~ 20 {BUF_MS - 2300}"), 0, pos, 0)
        c.c(ph, 0, pos, 1)
        dirn = c.obj("samphold~")
        c.c(c.ch(c.obj("noise~"), "*~ 0.5", "+~ 0.5"), 0, dirn, 0)
        c.c(ph, 0, dirn, 1)
        dr = c.ch(sub(c, dirn, revt), "*~ -1e+06", "clip~ -1 1")
        pan = c.obj("samphold~")
        c.c(c.ch(mul(c, c.obj("noise~"), spread), "*~ 0.5", "+~ 0.5"), 0, pan, 0)
        c.c(ph, 0, pan, 1)
        ratio = mul(c, c.ch(c.recv(f"al-cg{k}"), "pack f 60", "line~"), dr)
        # the read point: back by pos, moving (1 - ratio) ms each ms of the grain; kept at least 2 ms back
        mv = mul(c, mul(c, c.ch(ratio, "*~ -1", "+~ 1"), ph), size_ms)
        ahead = c.ch(mul(c, c.to(ratio, "-~ 1"), size_ms), "max~ 0")
        dl = c.to(add(c, add(c, pos, mv), ahead), "max~ 2")
        rd = c.to(dl, "delread4~ al-cbuf")
        gk = c.ch(dens, f"expr min(1, max(0, $f1 - {k}))", "pack f 60", "line~")
        gr = mul(c, mul(c, rd, win), gk)
        q = c.to(pan, "*~ 0.25")
        c.c(mul(c, gr, c.to(q, "cos~")), 0, L, 0)
        c.c(mul(c, gr, c.ch(q, "-~ 0.25", "cos~")), 0, R, 0)
    c.col(260)
    # to the cloud's bus (its filter is there, as every layer's: gen.layer_filter)
    for x, side in ((L, "L"), (R, "R")):
        c.c(mul(c, x, gain), 0, c.obj(f"throw~ al-cloud-{side}"), 0)


RH = lambda n: S("cloud", "rhythm", n)
RH_LEVELS = 3
RH_STEPS = 8


def _rhythm(c, k):
    """three grain voices, one a level: each struck by 'al-rg<j> pos_ms dur_ms pan' - a constant read point (the
    recording at its own pitch), an envelope up in 3 ms and down over the grain, placed between the sides"""
    c.comment("rhythm: a grain voice a level, struck in time (rhythm_clock)")
    gain = engine_switch(c, k)
    L, R = c.obj("*~ 0.55"), c.obj("*~ 0.55")
    for j in range(RH_LEVELS):
        up = c.ch(c.recv(f"al-rg{j}"), "unpack f f f")
        rd = c.ch(c.to(up, "sig~"), "delread4~ al-cbuf")
        env = c.obj("vline~")
        c.c(c.m((up, 1), "1 3, 0 $1 3"), 0, env, 0)
        g = mul(c, rd, env)
        q = c.ch((up, 2), "* 0.25", "pack f 5", "line~")
        c.c(mul(c, g, c.to(q, "cos~")), 0, L, 0)
        c.c(mul(c, g, c.ch(q, "-~ 0.25", "cos~")), 0, R, 0)
        c.col(260)
    for x, side in ((L, "L"), (R, "R")):
        c.c(mul(c, x, gain), 0, c.obj(f"throw~ al-cloud-{side}"), 0)


def rhythm_clock(c):
    """at each 24th of a beat (control.al-24) while the cloud plays rhythm: each level j sounding (Cascad) whose
    step comes - Rate's, halved j times, never finer than a 32nd - and whose Euclidean pattern (Densty: 1 .. 8 hits
    of 8; Morph: its rotation, each level turning its own amount) has a hit there strikes its voice: a place Scan
    back plus Jitter, a length Size of the step, a place between the sides (Spread)"""
    tempo = S("g", None, "Tempo")
    rate = f"min(2, int(alp[{RH('Rate')}]*3))"
    base = f"if({rate} == 0, 24, if({rate} == 1, 12, 6))"
    hits = f"(1 + int(alp[{RH('Densty')}]*7 + 0.5))"
    steps = []
    for j in range(RH_LEVELS):
        stp = f"max(3, int({base}/{2 ** j}))"
        rot = f"int(alp[{RH('Morph')}]*{RH_STEPS - 1}*{1 + j * 0.75} + 0.5)"
        pos = f"((int(alc24/{stp}) + {rot}) % {RH_STEPS})"
        steps.append(If(f"alp[{RH('Cascad')}]*{RH_LEVELS} >= {j} - 0.001 && alc24 % {stp} == 0 && "
                        f"({pos}*{hits}) % {RH_STEPS} < {hits}", [
            SendL(f"al-rg{j}", [
                f"min({BUF_MS - 2300}, 20 + alp[{RH('Scan')}]*{BUF_MS - 2600} + random(0, 1000)/1000*alp[{RH('Jitter')}]*2000)",
                f"max(10, alp[{RH('Size')}]*{stp}*60000/({num(tempo)}*24) - 3)",
                f"0.5 + (random(0, 1000)/1000 - 0.5)*alp[{RH('Spread')}]"])]))
    eng = S("cloud", None, "Engine")
    proc(c, "al-crhythm", [If(f"alrun && alclin && min({len(ENGS) - 1}, int(alp[{eng}]*{len(ENGS)})) == "
                              f"{ENGS.index('rhythm')}", steps)])


DL = lambda n: S("cloud", "delay", n)


def delay_div():
    """(expr) which of DELAY_DIVS the Time knob picks, synced"""
    return f"min({len(M.DELAY_DIVS) - 1}, int(alp[{DL('Time')}]*{len(M.DELAY_DIVS)}))"


def delay_beats():
    d = delay_div()
    out = f"{M.DELAY_DIVS[-1][1]:.6g}"
    for i in range(len(M.DELAY_DIVS) - 2, -1, -1):
        out = f"if({d} == {i}, {M.DELAY_DIVS[i][1]:.6g}, {out})"
    return out


def _delay(c, k):
    """the delay, a side each: in (Hold: hold - nothing new in; dub and off - the source in) plus the feedback (a
    soft limit keeps a full loop from running away), darkened (Tone), into its line; read Time back (the right
    side longer by Width), the time wavering (Mod: a slow sine, each side its own phase); the feedback crosses
    between the sides by Width, and is pitched (Pitch: two read heads turning through a short window, crossfaded
    - each repeat a step further); the repeats out"""
    c.comment("delay: two lines with feedback, each repeat pitched")
    gain = engine_switch(c, k)
    np_ = len(M.DELAY_PITCHES)
    hold = f"min(2, int(alp[{DL('Hold')}]*3))"
    ps = f"min({np_ - 1}, int(alp[{DL('Pitch')}]*{np_}))"
    st = str(int(M.DELAY_PITCHES[-1]))
    for i in range(np_ - 2, -1, -1):
        st = f"if({ps} == {i}, {int(M.DELAY_PITCHES[i])}, {st})"

    def ctl(expr, slots, ms=50):
        e = c.obj(f"expr {expr}")
        for sl in slots:
            c.c(c.ch(c.recv(f"al-s{sl}"), "t b"), 0, e, 0)
        return e
    # (feedback: Hold - exactly 1; else Fdbk up to 1.05, the soft limit holding it; in: not while holding)
    fb = c.ch(ctl(f"if({hold} > 0, 1, 1.05*alp[{DL('Fdbk')}])", (DL("Hold"), DL("Fdbk"))), "pack f 50", "line~")
    ing = c.ch(ctl(f"{hold} != 1", (DL("Hold"),)), "pack f 50", "line~")
    # (the pitch: on unless 0; the heads' turn - (1 - ratio) x 1000 / the 60 ms window, in Hz)
    shift = ctl(f"{st} != 0; (1 - pow(2, ({st})/12))*1000/60", (DL("Pitch"),))
    tone = c.ch(c.recv(f"al-s{DL('Tone')}"), "expr 800*pow(15, $f1)", "pack f 50", "line~")
    # (the time: free - Time, 20 ms .. 3 s; tempo - Time steps through DELAY_DIVS, in beats at the tempo)
    tempo = S("g", None, "Tempo")
    tms = c.ch(ctl(f"min({DEL_MS - 60}, if(alp[{DL('Sync')}] >= 0.5, ({delay_beats()})*60000/{num(tempo)}, "
                   f"20*pow(150, alp[{DL('Time')}])))", (DL("Time"), DL("Sync"), tempo)), "pack f 80", "line~")
    wid = prm(c, DL("Width"))
    mod = c.ch(prm(c, DL("Mod")), "*~ 6")
    lfo = c.obj("osc~ 0.27")
    lfo2 = c.obj("osc~ 0.31")
    ys, outs = [], []
    on = c.ch((shift, 0), "pack f 40", "line~")
    pph = c.obj("phasor~")
    c.c(c.ch((shift, 1), "pack f 40", "line~"), 0, pph, 0)
    for side, name in ((0, "L"), (1, "R")):
        t_ = tms if side == 0 else mul(c, tms, c.ch(wid, "*~ 0.25", "+~ 1"))
        dt = add(c, t_, mul(c, lfo if side == 0 else lfo2, mod))
        y = c.ch(c.to(dt, f"clip~ 1 {DEL_MS - 50}"), f"vd~ al-cd{name}")
        ys.append(y)
    for side, name in ((0, "L"), (1, "R")):
        # (the feedback: this side's repeat and the other's, crossed by Width; pitched)
        w = c.to(wid, "*~ 0.5")
        mix = add(c, mul(c, ys[side], c.ch(w, "*~ -1", "+~ 1")), mul(c, ys[1 - side], w))
        c.c(mix, 0, c.obj(f"delwrite~ al-cp{name} 100"), 0)
        heads = []
        for off in (0, 0.5):
            ph = c.ch(pph, f"+~ {off}", "wrap~")
            rd = c.ch(c.ch(ph, "*~ 60", "+~ 1"), f"vd~ al-cp{name}")
            win = c.ch(ph, "cos~", "*~ -0.5", "+~ 0.5")       # (a Hann window: the two heads sum to one)
            heads.append(mul(c, rd, win))
        pitched = add(c, *heads)
        fbsig = add(c, mul(c, pitched, on), mul(c, mix, c.ch(on, "*~ -1", "+~ 1")))
        src = mul(c, c.obj(f"r~ al-crec{name}"), ing)
        x = add(c, src, mul(c, fbsig, fb))
        lp = c.obj("lop~")
        c.c(x, 0, lp, 0)
        c.c(tone, 0, lp, 1)
        lim = div(c, lp, c.ch(lp, "abs~", "*~ 0.5", "+~ 1"))
        c.c(lim, 0, c.obj(f"delwrite~ al-cd{name} {DEL_MS}"), 0)
        c.c(mul(c, c.to(ys[side], "*~ 0.8"), gain), 0, c.obj(f"throw~ al-cloud-{name}"), 0)
        c.col(300)



def ratios(c):
    """the six streams' transpositions (al-cg0 .. 5): the pitch set; 'chord' from the chord's tones over its root"""
    from pdlib import proc, SendL, If, Call
    n = len(M.CLOUD_PITCHES)
    sel = f"min({n - 1}, int(alp[{P('Pitch')}]*{n}))"
    steps = []
    for k in range(STREAMS):
        fixed = [r[k] if r else 1 for r in M.CLOUD_RATIOS]
        expr = str(fixed[-1])
        for i in range(n - 2, -1, -1):
            v = f"pow(2, (alch[{k % 4}] - alch[0])/12)*{2 if k >= 4 else 1}" if M.CLOUD_RATIOS[i] is None else fixed[i]
            expr = f"if({sel} == {i}, {v}, {expr})"
        steps.append(SendL(f"al-cg{k}", [expr]))
    proc(c, "al-cloudratios", steps)
    c.c(c.ch(c.recv(f"al-s{P('Pitch')}"), "t b"), 0, c.obj("s al-cloudratios"), 0)
