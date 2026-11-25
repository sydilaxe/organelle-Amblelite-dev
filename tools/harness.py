"""Run the patch offline in Pd (pd -batch) with timed events, and record it.

run(events, seconds) -> (log, stereo float array). events: (time_ms, "receiver args"), e.g. (0, "notesRaw 72 100")
(the Organelle's top C: Start), (500, "al-midi 60 100 1"), (100, "knob1 0.5"), (0, "aux 1")."""
import os
import shutil
import subprocess
import tempfile
import numpy as np
from pdlib import Canvas

SR = 44100


def build_tmp():
    import gen
    d = tempfile.mkdtemp(prefix="alpd-")
    gen.build(d)
    return d


def run(events, seconds, prints=("oscOut",), d=None, keep=False, extra=None, inp=None):
    """inp: a signal for the audio input, e.g. 'osc~ 220' (default: silence)"""
    own = d is None
    if own:
        d = build_tmp()
    ev = sorted(events, key=lambda e: e[0])
    lines, prev = [], 0
    for t, s in ev:
        lines.append(f"{t - prev} {s};")
        prev = t
    lines.append(f"{max(0, seconds * 1000 - prev)} h-stop bang;")
    lines.append("0 pd quit;")
    open(os.path.join(d, "h_events.txt"), "w").write("\n".join(lines) + "\n")
    c = Canvas()
    lb = c.obj("loadbang", 20, 20)
    tb = c.obj("t b b b", 20, 45)
    c.c(lb, 0, tb, 0)
    dsp = c.msg("; pd dsp 1", 200, 70)
    c.c(tb, 2, dsp, 0)
    wm = c.msg("open h.wav, start", 300, 70)
    c.c(tb, 1, wm, 0)
    qm = c.msg("read h_events.txt, tempo 1 msec, bang", 20, 70)
    c.c(tb, 0, qm, 0)
    ws = c.obj("writesf~ 2", 300, 150)
    c.c(wm, 0, ws, 0)
    q = c.obj("qlist", 20, 150)
    c.c(qm, 0, q, 0)
    cl, cr = c.obj("catch~ outL", 300, 100), c.obj("catch~ outR", 400, 100)
    c.c(cl, 0, ws, 0)
    c.c(cr, 0, ws, 1)
    sm = c.msg("stop", 500, 125)
    c.c(c.obj("r h-stop", 500, 100), 0, sm, 0)
    c.c(sm, 0, ws, 0)
    z = c.obj("sig~ 0", 700, 60) if not inp else c.ch(c.obj(inp, 700, 30), "*~ 0.3")
    if inp:
        nz = c.ch(c.obj("noise~", 900, 30), "*~ 0.03")
        c.c(nz, 0, z, 0)
    c.c(z, 0, c.obj("s~ inL", 700, 90), 0)
    c.c(z, 0, c.obj("s~ inR", 800, 90), 0)
    c.obj("main", 20, 250)
    if extra:
        extra(c)
    for n in prints:
        c.c(c.obj("r " + n), 0, c.obj("print " + n), 0)
    c.save(os.path.join(d, "h_test.pd"))
    res = subprocess.run(["pd", "-nosound", "-nomidi", "-batch", "-stderr", "-open", "h_test.pd"], cwd=d,
                         capture_output=True, text=True, timeout=1800)
    a = audio(os.path.join(d, "h.wav"))
    if own and not keep:
        shutil.rmtree(d, ignore_errors=True)
    return res.stderr, a


def audio(path):
    b = open(path, "rb").read()
    i = b.index(b"data") + 8
    n = (len(b) - i) // 4 * 4
    return np.frombuffer(b[i:i + n], dtype="<i2").reshape(-1, 2).astype(float) / 32768


def errors(log):
    bad = []
    for l in log.splitlines():
        low = l.lower()
        if ("error" in low or "no such" in low or "couldn't create" in low or "bad arguments" in low
                or "no method" in low or "inlet: expected" in low or "dsp loop" in low or "out of range" in low
                or "stack overflow" in low or "can't" in low or "unknown" in low):
            bad.append(l)
    return bad


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
