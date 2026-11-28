"""Signal helpers shared by the engines and voices.

An engine is a subpatch inside a voice abstraction (al-<layer>.pd), built by engine_canvas():
  inlets:  0 'on' (1 / 0: selected or not - it fades in or out over 30 ms and switches its DSP off when out),
           1 freq~ (Hz), 2 env~ (the voice's envelope, 0..1), 3 'note' (a control list: hz vel, at each note-on)
  outlets: 0 left~, 1 right~
Percussive engines take the strike instead of freq~ / env~: inlet 1 'hz vel decay_ms' (see eng_perc).
Parameters are slots (model.S): prm() gives a smoothed signal 0..1, prmc() the control value."""
from pdlib import Canvas


def mul(c, a, b):
    m = c.obj("*~")
    c.c(*(a if isinstance(a, tuple) else (a, 0)), m, 0)
    c.c(*(b if isinstance(b, tuple) else (b, 0)), m, 1)
    return m


def add(c, a, b):
    m = c.obj("+~")
    c.c(*(a if isinstance(a, tuple) else (a, 0)), m, 0)
    c.c(*(b if isinstance(b, tuple) else (b, 0)), m, 1)
    return m


def sub(c, a, b):
    m = c.obj("-~")
    c.c(*(a if isinstance(a, tuple) else (a, 0)), m, 0)
    c.c(*(b if isinstance(b, tuple) else (b, 0)), m, 1)
    return m


def div(c, a, b):
    m = c.obj("/~")
    c.c(*(a if isinstance(a, tuple) else (a, 0)), m, 0)
    c.c(*(b if isinstance(b, tuple) else (b, 0)), m, 1)
    return m


def lop(c, x, hz, sr=44100):
    """a one-pole low-pass whose cutoff is a signal (Hz) - as [lop~] computes it (k = 2 pi f / sr, at most 1;
    y += k (x - y)), built from [rpole~]: [lop~] takes a signal cutoff only from Pd 0.54 (older, the Organelle's,
    the connection fails without a word and the filter sits closed - silent)"""
    k = c.ch(hz, f"*~ {6.283185307 / sr:.9g}", "clip~ 0 1")
    rp = c.obj("rpole~")
    c.c(mul(c, x, k), 0, rp, 0)
    c.c(c.ch(k, "*~ -1", "+~ 1"), 0, rp, 1)
    return rp


def prm(c, slot, ms=150):
    """slot as a smoothed signal 0..1 (every change ramps over ms: no zipper noise, no steps)"""
    return c.ch(c.recv(f"al-s{slot}"), f"pack f {ms}", "line~")


def prmc(c, slot):
    return c.recv(f"al-s{slot}")


def prmx(c, slot, expr, ms=150):
    """slot through a control expression ($f1 = the value 0..1), as a smoothed signal"""
    return c.ch(c.recv(f"al-s{slot}"), "expr " + expr, f"pack f {ms}", "line~")


def choice(slot_expr, n):
    """the option index of a choice slot, inside an [expr]"""
    return f"min({n - 1}, int({slot_expr}*{n}))"


def engine_canvas(name, perc=False):
    """an engine subpatch: returns (canvas, inputs, gain~). inputs: (freq~, env~, note) or, perc, (strike,)"""
    s = Canvas(name, w=1400, h=900)
    on = s.obj("inlet", 20, 5)
    ins = [s.obj("inlet", 160, 5)] if perc else [s.obj("inlet~", 160, 5), s.obj("inlet~", 300, 5),
                                                 s.obj("inlet", 440, 5)]
    s.cx, s.cy = 20, 40
    t = s.to(on, "t f f")
    g = s.ch((t, 1), "pack f 30", "line~")
    sw = s.obj("switch~")
    s.c(s.m(s.obj("loadbang"), "0"), 0, sw, 0)
    sel = s.to((t, 0), "sel 0")
    d = s.obj("delay 60")
    s.c(sel, 0, d, 0)
    s.c(s.m(d, "0"), 0, sw, 0)
    tb = s.to((sel, 1), "t b b")
    s.c(s.m((tb, 1), "stop"), 0, d, 0)
    s.c(s.m((tb, 0), "1"), 0, sw, 0)
    s.col(200)
    return s, ins, g


def out(s, L, R, g):
    s.c(mul(s, L, g), 0, s.obj("outlet~", 20, 870), 0)
    s.c(mul(s, R, g), 0, s.obj("outlet~", 200, 870), 0)


# ---- band-limited oscillator shapes (polyBLEP): stateless, so they fit in one [expr~] from a phase and dt = f/sr
def blep(t, dt):
    """the polyBLEP residual at phase t (0..1) with step dt"""
    return (f"(if({t} < {dt}, ({t})/({dt})*2 - (({t})/({dt}))*(({t})/({dt})) - 1, "
            f"if({t} > 1 - {dt}, ((({t}) - 1)/({dt}))*((({t}) - 1)/({dt})) + 2*(({t}) - 1)/({dt}) + 1, 0)))")


def saw_expr(t="$v1", dt="$v2"):
    return f"2*{t} - 1 - {blep(t, dt)}"


def pulse_expr(t="$v1", dt="$v2", w="$v3"):
    """a pulse of width w (0..1): +1 for t < w; the edges at 0 and w smoothed"""
    t2 = f"fmod({t} + 1 - {w}, 1)"
    return f"if({t} < {w}, 1, -1) + {blep(t, dt)} - {blep(t2, dt)}"


def dt_of(c, f):
    """dt = f / sr as a signal (from freq~)"""
    sr = c.obj("samplerate~")
    c.c(c.obj("loadbang"), 0, sr, 0)
    d = c.obj("/~ 44100")
    c.c(f, 0, d, 0)
    c.c(sr, 0, d, 1)
    return d


def span(c, sig, pos):
    """equal-power pan: sig at pos (signal or float, 0 left .. 1 right) -> (L, R)"""
    q = c.to(pos, "*~ 0.25")
    return mul(c, sig, c.to(q, "cos~")), mul(c, sig, c.ch(q, "-~ 0.25", "cos~"))
