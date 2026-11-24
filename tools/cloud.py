"""The cloud: a granular layer. An 8 s rolling recording (a delay line: [delwrite~ al-cbuf]) of its source - the
other layers (their buses after their levels), the audio input, or both - always recording, so it is ready when
the cloud comes in. Six grain streams read it back ([delread4~]): each grain a raised-cosine window of Size
(30 ms .. 2 s), read Scan back in time (plus Jitter), transposed by moving its read point (a ratio from the pitch
set: unison, octaves, fifths, the chord's tones, shimmer), some reversed (Reverse), each placed in the stereo
field (Spread). Density: how many of the six play. Its position, reversal and place are drawn at each grain's
start (a cloud is the one place where chance belongs).

Out: its grain readers are switched off once the fade is done (the recording goes on)."""
from pdlib import Canvas
from dsp import mul, add, sub, prm
import model as M
from model import S

STREAMS = 6
BUF_MS = 8000


def P(n):
    return S("cloud", "grains", n)


def build():
    c = Canvas("cloud", w=2600, h=1400)
    c.comment("the cloud's recording: its source, always")
    src = P("Source")
    gsrc = c.ch(c.recv(f"al-s{src}"), "expr min(2, int($f1*3))", "t f f")
    # (layers: 1 0; input: 0 1; both: 1 1)
    gl = c.ch((gsrc, 1), "expr $f1 != 1", "pack f 50", "line~")
    gi = c.ch((gsrc, 0), "expr $f1 >= 1", "pack f 50", "line~")
    lay = add(c, c.obj("catch~ al-csrcL"), c.obj("catch~ al-csrcR"))
    inp = add(c, c.obj("r~ inL"), c.obj("r~ inR"))
    rec = add(c, mul(c, lay, gl), mul(c, inp, gi))
    c.c(c.to(rec, "*~ 0.5"), 0, c.obj(f"delwrite~ al-cbuf {BUF_MS}"), 0)
    c.col(300)
    g = Canvas("grains", w=2600, h=1400)
    c.sub(g)
    _grains(g)
    r = Canvas("ratios", w=1600)
    c.sub(r)
    ratios(r)
    return c


def _grains(c):
    c.comment("six grain streams; switched off while the cloud is out (after its fade)")
    sw = c.obj("switch~")
    c.c(c.m(c.obj("loadbang"), "0"), 0, sw, 0)
    li = M.LAYERS.index("cloud")
    # on at once when it comes in, off once it has faded out
    ins = c.ch(c.recv(f"al-in{li}"), "unpack f f")
    sel = c.to(ins, "sel 0")
    d = c.obj("delay")
    c.c(c.to((ins, 1), "+ 100"), 0, d, 1)
    c.c(sel, 0, d, 0)
    c.c(c.m(d, "0"), 0, sw, 0)
    on = c.to((sel, 1), "t b b")
    c.c(c.m((on, 1), "stop"), 0, d, 0)
    c.c(c.m((on, 0), "1"), 0, sw, 0)
    # the grains' length (ms) and rate
    size = c.ch(c.recv(f"al-s{P('Size')}"), "expr 30*pow(66.67, $f1)", "t f f")
    rate = c.ch((size, 0), "expr 1000/$f1", "pack f 60", "line~")
    size_ms = c.ch((size, 1), "pack f 60", "line~")
    scan = c.ch(c.recv(f"al-s{P('Scan')}"), f"expr 20 + $f1*{BUF_MS - 2200}", "sig~")
    jit = c.ch(c.recv(f"al-s{P('Jitter')}"), "expr $f1*2000", "sig~")
    rev = c.ch(c.recv(f"al-s{P('Revrse')}"), "expr 1 - 2*$f1", "sig~")
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
        c.c(add(c, scan, mul(c, c.ch(c.obj("noise~"), "abs~"), jit)), 0, pos, 0)
        c.c(ph, 0, pos, 1)
        dirn = c.obj("samphold~")
        c.c(c.ch(c.obj("noise~"), "*~ 0.5", "+~ 0.5"), 0, dirn, 0)
        c.c(ph, 0, dirn, 1)
        dr = c.obj("expr~ if($v1 > ($v2 + 1)*0.5, -1, 1)")         # (reverse when the draw is above)
        c.c(dirn, 0, dr, 0)
        c.c(rev, 0, dr, 1)
        pan = c.obj("samphold~")
        c.c(c.ch(mul(c, c.obj("noise~"), spread), "*~ 0.5", "+~ 0.5"), 0, pan, 0)
        c.c(ph, 0, pan, 1)
        ratio = mul(c, c.ch(c.recv(f"al-cg{k}"), "pack f 60", "line~"), dr)
        # the read point: back by pos, moving (1 - ratio) ms each ms of the grain; kept at least 2 ms back
        dl = c.obj("expr~ max(2, $v1 + (1 - $v2)*$v3*$v4 + max(0, ($v2 - 1)*$v4))")
        c.c(pos, 0, dl, 0)
        c.c(ratio, 0, dl, 1)
        c.c(ph, 0, dl, 2)
        c.c(size_ms, 0, dl, 3)
        rd = c.to(dl, "delread4~ al-cbuf")
        gk = c.ch(dens, f"expr min(1, max(0, $f1 - {k}))", "pack f 60", "line~")
        gr = mul(c, mul(c, rd, win), gk)
        q = c.to(pan, "*~ 0.25")
        c.c(mul(c, gr, c.to(q, "cos~")), 0, L, 0)
        c.c(mul(c, gr, c.ch(q, "-~ 0.25", "cos~")), 0, R, 0)
    c.col(260)
    # the layer's filter, then the cloud's bus
    for x, side in ((L, "L"), (R, "R")):
        bq = c.obj("biquad~ 0 0 1 0 0")
        c.c(c.recv("al-cloud-bq"), 0, bq, 0)
        c.c(x, 0, bq, 0)
        c.c(bq, 0, c.obj(f"throw~ al-cloud-{side}"), 0)


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
