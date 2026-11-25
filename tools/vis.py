"""The visualizer (aux + low C#): an abstract oscilloscope, each layer a piece of simple geometry moved by its sound.
  the master   an oscilloscope trace across the screen (one gWaveform message)
  drone        a closed shape in the middle: its size the drone's level, its outline the drone's waveform
  sub          its waveform as a short trace along the bottom
  pads         a Lissajous figure - the pads' left against their right - so it turns with their stereo movement
  lanes        a box in each corner, jumping with each hit and shrinking back
  cloud        points placed by its waveform (its phase portrait), more as it gets louder
The mix (gen.mix) sends each layer's sound on s~ al-vs<n> (and the pads' sides, the master); here they are measured
only while the view shows (its DSP is off otherwise). About 10 frames a second (fewer when the CPU is busy:
screen.build's throttle), about 35 screen messages each."""
from pdlib import Canvas, proc, V, T, If, Loop, Send, SendL, Call, run_steps
from dsp import mul, add
import math
import model as M

VIEW_VIS = 3
OSC = "oscOut"
CORNERS = [(1, 1), (1, 0), (0, 1), (0, 0)]       # the lanes' boxes: (right?, bottom?)
GLOBALS = dict(alvon=0, alvfr=0, alvi=0, **{f"alvh{i}": 0 for i in range(4)},
               **{f"alvl{i}": 0 for i in range(len(M.LAYERS))})


def taps(c, li, L, oL, oR):
    """(in gen.mix) a layer's sound out to the visualizer"""
    c.c(add(c, oL, oR), 0, c.obj(f"s~ al-vs{li}"), 0)
    if L == "pad":
        c.c(oL, 0, c.obj("s~ al-vpl"), 0)
        c.c(oR, 0, c.obj("s~ al-vpr"), 0)


def build(c):
    c.comment("the visualizer: measured only while it shows; the frames come from al-draw (screen.py)")
    d = Canvas("vis-dsp", w=2000)
    node = c.sub(d)
    c.c(c.recv("al-vison"), 0, node, 0)
    sw = d.obj("switch~")
    d.c(d.obj("inlet", 20, 5), 0, sw, 0)
    d.c(d.m(d.obj("loadbang"), "0"), 0, sw, 0)
    d.cx, d.cy = 20, 40
    # each layer's level (env~: dB, 100 = full scale)
    for li in range(len(M.LAYERS)):
        d.c(d.ch(d.obj(f"r~ al-vs{li}"), "env~ 1024 512"), 0, d.obj(f"v alvl{li}"), 0)
    d.col(260)
    # the scope: the master at a quarter of the rate, 128 samples (11.6 ms), scaled to the screen's rows
    s = Canvas("scope", w=900)
    sx = s.obj("inlet~", 20, 5)
    s.obj("block~ 128 1 0.25")
    y = s.ch(sx, "*~ -30", "+~ 32.5", "clip~ 1 62")
    yi = s.obj("-~")
    s.c(y, 0, yi, 0)
    s.c(s.to(y, "wrap~"), 0, yi, 1)
    tw = s.obj("tabwrite~ alvisw")
    s.c(yi, 0, tw, 0)
    s.c(s.recv("al-visgrab"), 0, tw, 0)
    sn = d.sub(s)
    d.c(add(d, d.obj("r~ outL-vis"), d.obj("r~ outR-vis")), 0, sn, 0)
    # the pads' sides: 16 samples at an eighth of the rate (a Lissajous of 1.5 ms ... their shape)
    p = Canvas("lissa", w=900)
    pl, pr = p.obj("inlet~", 20, 5), p.obj("inlet~", 200, 5)
    p.obj("block~ 64 1 0.125")
    for x, a in ((pl, "alvpl"), (pr, "alvpr")):
        t = p.obj(f"tabwrite~ {a}")
        p.c(x, 0, t, 0)
        p.c(p.recv("al-visgrab"), 0, t, 0)
    pn = d.sub(p)
    d.c(d.obj("r~ al-vpl"), 0, pn, 0)
    d.c(d.obj("r~ al-vpr"), 0, pn, 1)
    # the drone's, sub's and cloud's waveforms: 16 samples each at 1/32 of the rate (11.6 ms, about one period of a
    # low note) - their shapes drawn from these
    w = Canvas("shapes", w=900)
    wins = [w.obj("inlet~", 20 + 180 * i, 5) for i in range(3)]
    w.obj("block~ 64 1 0.03125")
    for x, a in zip(wins, ("alvdw", "alvsw", "alvcw")):
        t = w.obj(f"tabwrite~ {a}")
        w.c(x, 0, t, 0)
        w.c(w.recv("al-visgrab"), 0, t, 0)
    wn = d.sub(w)
    for i, L in enumerate(("drone", "sub", "cloud")):
        d.c(d.obj(f"r~ al-vs{M.LAYERS.index(L)}"), 0, wn, i)
    for a, n in (("alvisw", 128), ("alvpl", 16), ("alvpr", 16), ("alvdw", 16), ("alvsw", 16), ("alvcw", 16)):
        c.obj(f"array define {a} {n}")
    # the waveform message: the scope's 128 rows in one
    c.c(c.ch(c.recv("al-viswave"), f"array get alvisw", "list prepend /oled/gWaveform 3", "list trim"), 0,
        c.obj(f"s {OSC}"), 0)
    # the lanes' hits: each lane's box jumps to its strike's velocity
    for i, L in enumerate(M.LANES):
        hv = c.ch(c.recv(f"al-{L}-hit"), "unpack f f f f")
        c.c(c.to((hv, 2), f"expr alvh{i} = max(alvh{i}, $f1)"), 0, c.obj("f"), 0)
    # the clock: while the view shows, its DSP on and a frame every 80 ms; off when it goes
    met = c.obj("metro 100")
    c.c(c.m(c.recv("al-init"), "1"), 0, met, 0)
    run_steps(c, (met, 0), [If(f"alview == {VIEW_VIS}", [
        If("alvon == 0", [V("alvon", "1"), Send("al-vison", "1")]),
        V("alvfr", "alvfr + 1"), Call("al-redraw")] + [V(f"alvh{i}", f"alvh{i}*0.72") for i in range(4)],
        [If("alvon", [V("alvon", "0"), Send("al-vison", "0")])])])
    proc(c, "al-vis", [V("alview", str(VIEW_VIS)), V("alpage", "0"), V("alpop", "0"), V("alpatv", "0"),
                       V("alstick", "0"), Call("al-redraw")])


def rms(li):
    return f"dbtorms(alvl{li})"


def frame():
    """the steps of one frame (al-draw, the screen already cleared)"""
    LI = M.LAYERS.index
    steps = [Send("al-viswave")]
    # drone: a closed shape round the middle - its radius the drone's level, its outline the drone's waveform
    #   (10 points round the circle, each pushed out or in by a sample)
    rd = f"(3 + 80*{rms(LI('drone'))})"
    nd = f"(0.6/max(0.004, 1.4*{rms(LI('drone'))}))"
    NP = 10
    ang = [(math.cos(2 * math.pi * i / NP), math.sin(2 * math.pi * i / NP)) for i in range(NP + 1)]
    def dp(i):
        r = f"min(31, {rd}*(1 + {nd}*alvdw[{(i % NP) + 3}]))"
        return f"int(64 + {ang[i][0]:.4f}*{r})", f"int(32 + {ang[i][1]:.4f}*0.9*{r})"
    steps.append(If(f"{rms(LI('drone'))} > 0.001", [
        SendL(OSC, [*dp(i), *dp(i + 1)], "/oled/gLine 3 $1 $2 $3 $4 1") for i in range(NP)]))
    # sub: its waveform as a short trace along the bottom (6 segments), as tall as it is loud
    ns = f"(min(5, 60*{rms(LI('sub'))})/max(0.004, 1.4*{rms(LI('sub'))}))"
    sp = lambda i: (str(4 + 20 * i), f"int(max(52, min(63, 58 - {ns}*alvsw[{2 * i + 2}])))")
    steps.append(If(f"{rms(LI('sub'))} > 0.001", [
        SendL(OSC, [*sp(i), *sp(i + 1)], "/oled/gLine 3 $1 $2 $3 $4 1") for i in range(6)]))
    # pads: a Lissajous of their sides, scaled to their level so it fills a steady size
    g = f"(22/max(0.01, 1.4*{rms(LI('pad'))}))"
    pt = lambda a, i, c0, k: f"int(max(1, min({2 * c0 - 1}, {c0} + {k}*{g}*{a}[{i}])))"
    steps.append(If(f"{rms(LI('pad'))} > 0.001", [
        SendL(OSC, [pt("alvpl", i, 64, 1.6), pt("alvpr", i, 32, 1), pt("alvpl", i + 1, 64, 1.6),
                    pt("alvpr", i + 1, 32, 1)], "/oled/gLine 3 $1 $2 $3 $4 1") for i in range(8)]))
    # lanes: a box in each corner, its size the last hit (decaying)
    for i, (rx, by) in enumerate(CORNERS):
        sz = f"int(1 + 13*min(1, alvh{i}))"
        steps.append(If(f"alvh{i} > 0.05", [SendL(OSC, [f"{127} - {sz}" if rx else "1", f"{63} - {sz}" if by else "1", sz],
                                                    "/oled/gBox 3 $1 $2 $3 $3 1")]))
    # cloud: points placed by its waveform (a sample against one a little later: its phase portrait), more as it
    # gets louder
    n = f"int(min(7, 120*{rms(LI('cloud'))}))"
    ncw = f"(1/max(0.004, 1.4*{rms(LI('cloud'))}))"
    steps.append(Loop(n, "alvi", [SendL(OSC, [f"int(max(0, min(125, 63 + 55*{ncw}*alvcw[alvi*2])))",
                                              f"int(max(0, min(61, 31 + 28*{ncw}*alvcw[alvi*2 + 1])))"],
                                        "/oled/gFillArea 3 $1 $2 2 2 1")]))
    # (the next frame's scope and Lissajous: grabbed now, ready by then)
    steps.append(Send("al-visgrab"))
    return steps
