"""Offline checks in Pure Data: python3 check.py. Each check builds nothing new (one build, reused) and prints
PASS / FAIL with what it measured."""
import sys
import time
import numpy as np
import harness as H
import model as M

SR = 44100
START = (200, "notesRaw 72 100")
FAILS = []


def solo(L, t=60):
    """only L in (every other layer out; L in)"""
    return [(t + i, f"al-inset {i} {1 if o == L else 0}") for i, o in enumerate(M.LAYERS)]


def seg(a, t0, t1):
    return a[int(t0 * SR):int(t1 * SR)]


def peak_hz(x, lo=20, hi=5000):
    m = x.mean(axis=1) if x.ndim == 2 else x
    w = np.hanning(len(m))
    sp = np.abs(np.fft.rfft(m * w))
    f = np.fft.rfftfreq(len(m), 1 / SR)
    k = (f > lo) & (f < hi)
    return f[k][np.argmax(sp[k])]


def env(x, w=0.02):
    m = np.abs(x.mean(axis=1))
    n = int(w * SR)
    return m[: len(m) // n * n].reshape(-1, n).mean(axis=1)


def check(name, ok, info):
    print(("PASS " if ok else "FAIL ") + name + ": " + info, flush=True)
    if not ok:
        FAILS.append(name)


def main():
    d = H.build_tmp()
    run = lambda ev, s: H.run(ev, s, d=d, keep=True)

    log, a = run([], 1)
    check("loads without errors", not H.errors(log), "; ".join(H.errors(log)[:3]) or "clean")
    check("silent until Start", H.rms_db(a) < -90, f"{H.rms_db(a):.1f} dB")

    log, a = run([START], 3)
    check("Start plays the defaults", H.rms_db(seg(a, 1.5, 3)) > -30, f"{H.rms_db(seg(a, 1.5, 3)):.1f} dB")
    check("no clipping, no NaN", float(np.abs(a).max()) < 0.99 and not np.isnan(a).any(),
          f"peak {float(np.abs(a).max()):.2f}")

    # the sub on MIDI channel 3: a note sets its pitch (A4, MIDI 69; the sub's octave -2 puts it at 110 Hz)
    log, a = run(solo("sub") + [START, (1000, "al-midi 69 100 3"), (1100, "al-midi 69 0 3")], 3)
    hz = peak_hz(seg(a, 2, 3), 15, 300)
    check("sub plays a MIDI note (ch 3), latched", abs(hz - 110) < 2, f"{hz:.1f} Hz (110 expected)")

    # Stop: everything released and silent after the release
    log, a = run([START, (1500, "notesRaw 72 100")], 6)
    check("Stop releases everything", H.rms_db(seg(a, 5.5, 6)) < -70, f"{H.rms_db(seg(a, 5.5, 6)):.1f} dB")

    # the drone: articulation 'slide' and a long glide - the pitch moves between the two notes
    art, gl = M.S("drone", None, "Artic"), M.S("drone", None, "Glide")
    ev = solo("drone") + [(50, f"al-set {art} 0.9"), (51, f"al-set {gl} 0.75"), (52, f"al-set {M.S('drone', None, 'Engine')} 0"),
                          (53, f"al-set {M.S('drone', 'analog', 'WaveA')} 0"), (54, f"al-set {M.S('drone', 'analog', 'WaveB')} 0"),
                          (55, f"al-set {M.S('drone', 'analog', 'Sub')} 0"),
                          START, (1000, "al-midi 69 100 2"), (1050, "al-midi 69 0 2"), (3000, "al-midi 81 100 2")]
    log, a = run(ev, 6)
    h1, hmid, h2 = peak_hz(seg(a, 2.5, 3)), peak_hz(seg(a, 3.2, 3.5)), peak_hz(seg(a, 5.5, 6))
    check("drone glides (slide)", abs(h1 - 220) < 4 and abs(h2 - 440) < 6 and 230 < hmid < 430,
          f"{h1:.0f} -> {hmid:.0f} -> {h2:.0f} Hz")

    # pads: a chord played on channel 4 replaces the default and stays latched after the keys are up
    ev = solo("pad") + [START] + [(1000 + 10 * i, f"al-midi {n} 100 4") for i, n in enumerate((57, 61, 64))] + \
        [(1500 + 10 * i, f"al-midi {n} 0 4") for i, n in enumerate((57, 61, 64))]
    log, a = run(ev, 4)
    x = seg(a, 3, 4).mean(axis=1)
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    tops = sorted(f[np.argsort(sp)[-12:]])
    want = [220.0, 277.2, 329.6]
    found = all(any(abs(t - w) < 3 for t in tops) for w in want)
    check("pads latch a played chord", found and H.rms_db(x) > -40, f"peaks {[round(t) for t in tops][:8]}")

    # the percussion pattern: 5 hits in 8 sixteenths at 84 bpm, counted as strikes
    log, a = H.run(solo("perc1") + [START], 5, d=d, keep=True, prints=("al-perc1-hit",))
    hits = sum(1 for l in log.splitlines() if l.startswith("al-perc1-hit"))
    expect = 4.8 / (60 / 84 / 4) * 5 / 8
    check("percussion plays its Euclidean pattern", abs(hits - expect) <= 2, f"{hits} strikes ({expect:.0f} expected)")

    # the chord story: next chord changes the pads
    log, a = run(solo("pad") + [START, (2000, "notesRaw 76 100")], 4)
    h1, h2 = peak_hz(seg(a, 1.5, 2)), peak_hz(seg(a, 3.5, 4))
    check("next chord moves the pads", abs(h1 - h2) > 5, f"{h1:.0f} -> {h2:.0f} Hz")

    # Evolve: the pads' wave engine at full Evolve, fast pace - its brightness moves; at 0 (or the master at 0) it
    # holds still; and the same settings move the same way every time
    pe, pp = M.S("pad", None, "Evolve"), M.S("pad", None, "Pace")
    base = solo("pad") + [(50, f"al-set {M.S('pad', None, 'Engine')} {M.engine_value('pad', 'wave')}"), (51, f"al-set {pp} 1"),
                          (52, f"al-set {M.S('pad', 'wave', 'Table')} 0.35"),
                          (53, f"al-set {M.S('g', None, 'Bars')} 0.05"), START]      # (Bars: manual - one chord)

    def centroids(a):
        out = []
        for t in range(2, 20, 2):
            x = seg(a, t, t + 1).mean(axis=1)
            sp = np.abs(np.fft.rfft(x * np.hanning(len(x))))
            f = np.fft.rfftfreq(len(x), 1 / SR)
            out.append(float((sp * f).sum() / (sp.sum() + 1e-9)))
        return np.array(out)
    _, a1 = run(base + [(55, f"al-set {pe} 1")], 20)
    _, a1b = run(base + [(55, f"al-set {pe} 1")], 20)
    _, a0 = run(base + [(55, f"al-set {pe} 0")], 20)
    _, am = run(base + [(55, f"al-set {pe} 1"), (56, f"al-set {M.S('g', None, 'Evolve')} 0")], 20)
    c1, c0, cm = centroids(a1), centroids(a0), centroids(am)
    check("Evolve moves the sound", np.std(c1) > 60, f"brightness spread {np.std(c1):.0f} Hz")
    # (what is left at 0 is the wave's own stereo detune beating, not Evolve)
    check("Evolve 0 holds still", np.std(c0) < np.std(c1) / 8, f"brightness spread {np.std(c0):.1f} Hz")
    check("master Evolve 0 calms the layer", np.std(cm) < np.std(c1) / 8, f"brightness spread {np.std(cm):.1f} Hz")
    n = min(len(a1), len(a1b)) - SR      # (the file writer stops at a slightly different point: compare the overlap)
    same = np.allclose(a1[:n], a1b[:n])
    check("Evolve is repeatable", same, "two renders identical" if same else "renders differ")

    # Drift: the drone's pitch wanders a little
    dd = M.S("drone", None, "Drift")
    ev = solo("drone") + [(50, f"al-set {M.S('drone', 'analog', 'WaveA')} 0"), (51, f"al-set {M.S('drone', 'analog', 'WaveB')} 0"),
                          (52, f"al-set {M.S('drone', 'analog', 'Sub')} 0"), (53, f"al-set {dd} 1"),
                          (54, f"al-set {M.S('drone', None, 'Evolve')} 0"), START]
    _, a = run(ev, 12)
    hz = [peak_hz(seg(a, t, t + 1.5), 40, 200) for t in (2, 4, 6, 8, 10)]
    check("Drift bends the pitch", max(hz) - min(hz) > 0.4, f"{[round(h, 1) for h in hz]} Hz")

    # the lanes: all four on, each at its own density (perc2 3/8 in 8ths, perc3 2/5 in quarters stacked, perc4
    # 7/16 in 16ths); perc1 in 8th triplets
    on = [(20 + i, f"al-inset {M.LAYERS.index(L)} 1") for i, L in enumerate(M.LANES[1:])]
    on += [(40, f"al-set {M.S('perc1', None, 'Rate')} {(2 + 0.5) / 6}"),
           (41, f"al-set {M.S('perc3', None, 'Pitch')} {(7 + 0.5) / len(M.PITCHES)}")]
    log, a = H.run(on + [START], 5, d=d, keep=True, prints=tuple(f"al-{L}-hit" for L in M.LANES))
    n = {L: sum(1 for l in log.splitlines() if l.startswith(f"al-{L}-hit")) for L in M.LANES}
    beats = 4.8 * 84 / 60
    want = dict(perc1=beats * 3 * 5 / 8, perc2=beats * 2 * 3 / 8, perc3=3 * beats * 2 / 5, perc4=beats * 4 * 7 / 16)
    ok = all(abs(n[L] - want[L]) <= max(2, 0.2 * want[L]) for L in M.LANES)
    check("four lanes interlock (triplets, a stack)", ok, ", ".join(f"{L} {n[L]} ({want[L]:.0f})" for L in M.LANES))
    check("all lanes together: no clipping", float(np.abs(a).max()) < 0.99, f"peak {float(np.abs(a).max()):.2f}")

    # the gate sequencer on the pads: their level pulses in 8ths; then the sub gated where the pads' pattern is
    # silent (Comp): the two alternate
    gp = [(30, f"al-set {M.S('pad', None, 'Gate')} 0.5"), (31, f"al-set {M.S('pad', None, 'Attack')} 0.1"),
          (32, f"al-set {M.S('pad', None, 'Releas')} 0.2")]
    _, a = run(solo("pad") + gp + [START], 4)
    e1 = env(seg(a, 1.5, 4))
    check("gate sequencer pulses the pads", np.std(e1) / (np.mean(e1) + 1e-9) > 0.4, f"variation {np.std(e1) / (np.mean(e1) + 1e-9):.2f}")
    gs = [(33, f"al-set {M.S('sub', None, 'Gate')} 0.5"), (34, f"al-set {M.S('sub', None, 'Comp')} {(3 + 0.5) / 4}"),
          (35, f"al-set {M.S('sub', None, 'Attack')} 0.1"), (36, f"al-set {M.S('sub', None, 'Releas')} 0.2")]
    _, b = run(solo("sub") + gp + gs + [START], 4)
    e2 = env(seg(b, 1.5, 4))
    k = min(len(e1), len(e2))
    r = float(np.corrcoef(e1[:k], e2[:k])[0, 1])
    check("complementary gates alternate", r < -0.2, f"correlation {r:.2f}")

    # the chord library: quartal on C - C F Bb Eb (Bb dropped an octave by the voicing)
    _, a = run(solo("pad") + [(40, f"al-set {M.S('g', None, 'Story')} {(35 + 0.5) / len(M.STORIES)}"), START], 3)
    x = seg(a, 2, 3).mean(axis=1)
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    tops = f[np.argsort(sp)[-16:]]
    want = [261.6, 349.2, 233.1, 622.3]
    found = all(any(abs(t - w) < 4 for t in tops) for w in want)
    check("library chord (quartal)", found, f"peaks {sorted(round(t) for t in tops)[:10]}")

    # ---- milestone 3
    def opt_v(i, n):
        return (i + 0.5) / n
    mc = M.MAXC
    lev = 2          # (the targets: off, Cutoff, Level ...)
    lt, lr, ld = (M.S("pad", None, k) for k in ("L1Tgt", "L1Rate", "L1Dep"))
    lfo = [(40, f"al-set {lt} {opt_v(lev, mc)}"), (41, f"al-set {lr} {opt_v(13, 16)}"), (42, f"al-set {ld} 1"),
           (43, f"al-set {M.S('pad', None, 'Evolve')} 0")]
    _, a = run(solo("pad") + lfo + [START], 5)
    e = env(seg(a, 2, 5), 0.05)
    _, b = run(solo("pad") + lfo[1:] + [START], 5)
    e0 = env(seg(b, 2, 5), 0.05)
    v1, v0 = np.std(e) / np.mean(e), np.std(e0) / np.mean(e0)
    check("LFO moves the pads' level (1 Hz)", v1 > 3 * v0 and v1 > 0.2, f"variation {v1:.2f} (off: {v0:.2f})")

    # random LFOs: smooth glides between new values each cycle, stepped holds them; both repeat with the same
    # settings
    ls = M.S("pad", None, "L1Shp")
    res = {}
    for shp in (6, 7):
        ev_ = lfo + [(44, f"al-set {ls} {opt_v(shp, len(M.LFO_SHAPES))}"), (45, f"al-set {lr} {opt_v(12, 16)}")]
        _, a = run(solo("pad") + ev_ + [START], 8)
        e = env(seg(a, 2, 8), 0.05)
        res[shp] = (e, np.std(e) / np.mean(e), np.mean(np.abs(np.diff(e))) / np.mean(e))
    _, a2 = run(solo("pad") + lfo + [(44, f"al-set {ls} {opt_v(7, len(M.LFO_SHAPES))}"),
                                     (45, f"al-set {lr} {opt_v(12, 16)}"), START], 8)
    e2 = env(seg(a2, 2, 8), 0.05)
    same = np.allclose(res[7][0][:len(e2)], e2[:len(res[7][0])], atol=1e-4)
    check("random LFOs (smooth, stepped)", res[6][1] > 0.15 and res[7][1] > 0.15 and res[7][2] > res[6][2] and same,
          f"variation {res[6][1]:.2f} / {res[7][1]:.2f}, jumps {res[6][2]:.3f} / {res[7][2]:.3f}, repeatable {same}")

    # assign: aux held, knob 1 - the FAV page's first place takes another parameter
    log, _ = H.run([(100, "al-sel-pad bang"), (300, "aux 1"), (400, "knob1 0.95"), (500, "aux 0")], 1, d=d,
                   keep=True)
    lines = [l for l in log.splitlines() if "gPrintln 3 0 22" in l]
    check("assign mode puts a parameter on FAV", len(lines) >= 2 and lines[-1] != lines[0], lines[-1][-30:] if lines else "-")
    fav = [l for l in lines if " 1 Engine " in l or l.endswith(" 1 Engine")]
    check("FAV starts with the engine choice", bool(fav), fav[0][-30:] if fav else "-")

    # navigation: a held layer key opens its pages; an aux tap (alone) goes home to the play view
    def popq(c):
        c.c(c.ch(c.obj("r h-q", 900, 700), "expr alpop*10 + alview"), 0, c.obj("print NAV", 900, 760), 0)
    log, _ = H.run([(100, "notesRaw 64 100"), (700, "notesRaw 64 0"), (800, "h-q bang"), (6000, "h-q bang"),
                    (6100, "aux 1"), (6150, "aux 0"), (6200, "h-q bang"),
                    (6300, "notesRaw 68 100"), (6350, "notesRaw 68 0"), (6400, "h-q bang"),
                    (6500, "aux 1"), (6550, "aux 0"), (6600, "h-q bang"),
                    (7000, "knob3 0.1"), (7100, "knob3 0.9"), (7200, "h-q bang"), (11000, "h-q bang")],
                   12, d=d, keep=True, extra=popq)
    nav = [l.split()[-1] for l in log.splitlines() if l.startswith("NAV")]
    check("a hold opens the pages (they stay), an aux tap goes home; a knob's pop-up closes by itself",
          nav[:2] == ["10", "10"] and nav[2:3] == ["0"] and nav[3:4] != ["0"] and nav[4:5] == ["0"]
          and nav[5:6] == ["10"] and nav[6:7] == ["0"], " ".join(nav))

    # snapshots: save 1, change the pads' engine and level, recall 1 (morph 0): back as it was; COMPARE: the change
    eng, lv = M.S("pad", None, "Engine"), M.S("pad", None, "Level")
    ev = [(50, f"al-set {M.S('g', None, 'Morph')} 0"), START, (500, "notesRaw 82 100"), (510, "aux 1"),
          (520, "notesRaw 60 100"), (530, "aux 0"), (540, "notesRaw 82 0"),
          (800, f"al-set {eng} 0.3"), (810, f"al-set {lv} 0.1"),
          (1500, "notesRaw 82 100"), (1510, "notesRaw 60 100"), (1520, "notesRaw 82 0"),
          (2500, "notesRaw 82 100"), (2510, "notesRaw 82 0")]
    log, a = H.run(solo("pad") + ev, 3.5, d=d, keep=True, prints=("oscOut",))
    heads = [l for l in log.splitlines() if "gPrintln 3 0 0 " in l]
    rows = [l for l in log.splitlines() if "gPrintln 3 0 42" in l]
    r1, r2, r3 = H.rms_db(seg(a, 1.2, 1.5)), H.rms_db(seg(a, 2.0, 2.4)), H.rms_db(seg(a, 3.0, 3.4))
    check("save, change, recall", r2 - r1 > 6 and any("SAVED" in l for l in heads) and any("LOADED" in l for l in heads),
          f"level {r1:.1f} -> recalled {r2:.1f} dB")
    check("compare goes back to the change", r2 - r3 > 6 and any("COMPARE" in l for l in heads), f"{r3:.1f} dB")

    # morph: a slow morph (Morph 70 %: about 4 s) - the level glides
    ev2 = [(50, f"al-set {M.S('g', None, 'Morph')} 0.7"), START, (300, f"al-set {lv} 0.1"), (500, "notesRaw 82 100"),
           (510, "aux 1"), (520, "notesRaw 61 100"), (530, "aux 0"), (540, "notesRaw 82 0"), (800, f"al-set {lv} 0.8"),
           (1500, "notesRaw 82 100"), (1510, "notesRaw 61 100"), (1520, "notesRaw 82 0")]
    _, a = run(solo("pad") + ev2, 7)
    steps_ = [H.rms_db(seg(a, t, t + 0.3)) for t in (1.3, 2.5, 3.5, 4.5, 6.5)]
    mono_ = all(steps_[i] >= steps_[i + 1] - 0.5 for i in range(4))
    check("morph glides", mono_ and steps_[0] - steps_[-1] > 10 and steps_[1] - steps_[-1] > 2,
          " > ".join(f"{x:.1f}" for x in steps_) + " dB")

    # the looper: on the sub, A then E recorded in one bar; the next cycles play them again
    q = [(30, f"al-set {M.S('g', None, 'Bars')} 0.05"), (31, "al-sel-sub bang")]
    ev3 = solo("sub") + q + [START, (1000, "notesRaw 75 100"), (1001, "al-midi 69 100 1"), (1500, "al-midi 69 0 1"),
                             (2400, "al-midi 76 100 1"), (2900, "al-midi 76 0 1"), (3700, "notesRaw 75 100")]
    _, a = run(ev3, 9.5)
    # (a bar is 2.86 s: the 2nd cycle starts at 3.86 s - A, then E 1.4 s later; the 3rd at 6.71 s)
    h1, h2, h3 = peak_hz(seg(a, 4.2, 5.0), 30, 400), peak_hz(seg(a, 5.6, 6.4), 30, 400), peak_hz(seg(a, 7.0, 7.8), 30, 400)
    check("looper replays the phrase", abs(h1 - 110) < 3 and abs(h2 - 164.8) < 3 and abs(h3 - 110) < 3,
          f"{h1:.0f}, {h2:.0f}, {h3:.0f} Hz (A 110, E 165, A 110)")

    # swing: perc1 in 16ths with full swing - the gaps between strikes alternate long and short
    sw = [(30, f"al-set {M.S('perc1', None, 'Swing')} 1"), (31, f"al-set {M.S('perc1', None, 'Hits')} 1"),
          (32, f"al-set {M.S('perc1', None, 'Steps')} 0"), (33, f"al-set {M.S('perc1', None, 'Decay')} 0.05"),
          (34, f"al-set {M.S('perc1', None, 'Evolve')} 0")]
    _, a = run(solo("perc1") + sw + [START], 4)
    m_ = np.abs(seg(a, 1, 4).mean(axis=1))
    hop = 220
    blk = m_[: len(m_) // hop * hop].reshape(-1, hop).max(axis=1)
    on_ = [i for i in range(1, len(blk)) if blk[i] > 0.02 and blk[i] > 3 * blk[i - 1]]
    gaps = np.diff(on_) * hop / SR
    alt = np.mean(np.abs(np.diff(gaps))) if len(gaps) > 3 else 0
    check("swing alternates the steps", alt > 0.04, f"gaps {[round(g, 3) for g in gaps[:6]]} s")

    # in / out: a tap on low C takes the drone out (it fades over Fade: about 1.8 s), another brings it back; a
    # hold (on low D) shows the sub's pages and leaves it in
    ev4 = solo("drone") + [START, (2000, "notesRaw 60 100"), (2050, "notesRaw 60 0"), (6000, "notesRaw 60 100"),
                           (6050, "notesRaw 60 0"), (6500, "notesRaw 62 100"), (7100, "notesRaw 62 0")]
    log, a = H.run(ev4, 9, d=d, keep=True, prints=("oscOut",))
    r1, r2, r3 = H.rms_db(seg(a, 1.5, 2)), H.rms_db(seg(a, 4.5, 5.5)), H.rms_db(seg(a, 8.3, 8.9))
    held = any("gPrintln 3 0 0 8 1 SUB" in l for l in log.splitlines())
    check("a tap takes a layer out and back in; a hold shows its pages", r1 > -40 and r2 < -80 and r3 > -40 and held,
          f"{r1:.1f} -> out {r2:.1f} -> in {r3:.1f} dB, hold shows pages: {held}")

    # the cloud: it records the other layers and grains them - the pads go out, the cloud keeps sounding them for
    # a few seconds (its grains read up to about 4 s back); without the cloud, silence
    ci, pi = M.LAYERS.index("cloud"), M.LAYERS.index("pad")
    cl = solo("pad") + [(80, f"al-set {M.S('g', None, 'Fade')} 0"), START, (6000, f"al-inset {pi} 0")]
    _, a = run(cl + [(81, f"al-inset {ci} 1")], 7.5)
    _, b = run(cl, 7.5)
    rc, r0 = H.rms_db(seg(a, 6.3, 7.3)), H.rms_db(seg(b, 6.3, 7.3))
    check("the cloud grains the layers (and outlives them)", rc > -50 and r0 < -80, f"after the pads left: {rc:.1f} dB with the cloud, {r0:.1f} without")

    # ---- milestone 4: controllers, MPE, breath, zones
    S_ = M.S
    pr, chans, zones, bend = (S_("g", None, k) for k in ("Profil", "Chans", "Zones", "Bend"))
    # a profile: the nanoKONTROL Studio's slider 1 sets the drone's level, its M button 1 takes it out, knob 1 the
    # first parameter on the page shown
    log, _ = H.run([(100, f"al-set {pr} {(2 + 0.5) / 5}"), (300, "al-cc 20 0 1"), (400, "al-cc 127 48 1"),
                    (500, "al-cc 100 16 1")], 1, d=d, keep=True, prints=("al-set", "al-inset"))
    lv = f"al-set: {S_('drone', None, 'Level')} 0.15748"
    check("controller profile (nanoKONTROL Studio)", lv in log and "al-inset: 0 0" in log and
          any(l.startswith("al-set:") and l.endswith(" 0.787402") for l in log.splitlines()), "slider, M button, knob")

    # MPE: a note on channel 3 bent up a semitone (range 2) on its own, then its pressure lowers its level
    mp = solo("sub") + [(50, f"al-set {chans} 0.75"), (51, f"al-set {bend} 0.1"), (52, "al-sel-sub bang"), START,
                        (900, "al-bendin 12288 3"), (1000, "al-midi 69 100 3"), (3000, "al-touchin 20 3")]
    _, a = run(mp, 4.5)
    hz = peak_hz(seg(a, 1.8, 2.8), 30, 400)
    l1, l2 = H.rms_db(seg(a, 2.0, 2.8)), H.rms_db(seg(a, 3.6, 4.4))
    check("MPE: a note's own bend and pressure", abs(hz - 116.5) < 2 and l1 - l2 > 6,
          f"{hz:.1f} Hz (116.5), pressure {l1:.1f} -> {l2:.1f} dB")

    # breath (the generic profile: CC 2) -> the pads' cutoff (their BREATH page): brighter as it blows
    bt = [(50, f"al-set {S_('pad', None, 'BTgt')} {(1 + 0.5) / M.MAXC}"), (51, f"al-set {S_('pad', None, 'BDep')} 1"),
          (52, f"al-set {S_('pad', None, 'Cutoff')} 0.35"), (53, f"al-set {S_('pad', None, 'Evolve')} 0"),
          (54, f"al-set {S_('pad', None, 'Engine')} {M.engine_value('pad', 'saws')}")]      # (the saws: harmonics to filter)
    _, a = run(solo("pad") + bt + [START, (2000, "al-cc 127 2 1")], 3.5)

    def bright(x):
        m = x.mean(axis=1)
        sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
        f = np.fft.rfftfreq(len(m), 1 / SR)
        return float((sp * f).sum() / (sp.sum() + 1e-9))
    b1, b2 = bright(seg(a, 1.2, 1.9)), bright(seg(a, 2.6, 3.4))
    check("breath moves a layer's target", b2 > b1 * 1.3, f"brightness {b1:.0f} -> {b2:.0f} Hz")

    # zones: low notes to the sub, middle ones to the pads (whatever is shown)
    log, _ = H.run([(50, f"al-set {zones} 0.75"), START, (500, "al-midi 40 100 1"), (600, "al-midi 60 100 1")], 1,
                   d=d, keep=True, prints=("al-user-sub", "al-user-pad"))
    ok = "al-user-sub: 40 0.787402" in log and "al-user-pad: 60 0.787402" in log
    check("zones split the keyboard", ok, "40 -> sub, 60 -> pads" if ok else log[-200:])

    # a zone's breath, looped: the sub's breath (to its level) recorded with its notes in one bar; the next cycle
    # plays it back with no breath - loud where it blew, quiet where it didn't
    zb = solo("sub") + [(50, f"al-set {zones} 0.75"), (51, f"al-set {S_('sub', None, 'BTgt')} {(2 + 0.5) / M.MAXC}"),
                        (52, f"al-set {S_('sub', None, 'BDep')} 1"), (53, f"al-set {S_('sub', None, 'Level')} 0.15"),
                        (54, f"al-set {S_('g', None, 'Bars')} 0.05"), START,
                        (1000, "notesRaw 75 100"), (1001, "al-midi 45 100 1"), (1010, "al-cc 127 2 1"),
                        (2000, "al-cc 0 2 1"), (3800, "al-midi 45 0 1"), (3810, "notesRaw 75 100")]
    _, a = run(zb, 7.2)
    hi_, lo_ = H.rms_db(seg(a, 4.0, 4.7)), H.rms_db(seg(a, 5.2, 6.4))
    check("a zone's breath loops", hi_ - lo_ > 8, f"replayed: {hi_:.1f} dB where it blew, {lo_:.1f} after")

    # ---- milestone 6: the harmony assistant
    sg, lis = M.S("g", None, "Sugg"), M.S("g", None, "Listen")

    def peaks(x, n=16):
        m = x.mean(axis=1)
        sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
        f = np.fft.rfftfreq(len(m), 1 / SR)
        return f[np.argsort(sp)[-n:]]

    def has(tops, hz):
        return any(abs(t - hz) < 3 for t in tops)
    # accept: from Cm in C dorian the 2nd suggestion is F7 (dorian's IV) - played at once on the pads
    acc = solo("pad") + [(50, f"al-set {sg} {(1 + 0.5) / 4}"), (55, f"al-set {M.S('g', None, 'Bars')} 0.05"), START,
                         (1500, "aux 1"), (1600, "notesRaw 76 100"), (1700, "aux 0")]
    _, a = run(acc, 3.5)
    t = peaks(seg(a, 2.5, 3.5))
    check("a suggestion accepted plays at once (F7)", has(t, 349.2) and has(t, 440.0), f"peaks {sorted(round(x) for x in t)[:10]}")
    # listening: an E held (on the sub) - the next chord holds E
    li = solo("pad") + [(50, f"al-set {lis} 0.75"), (55, f"al-set {M.S('g', None, 'Bars')} 0.05"), START,
                        (1200, "al-midi 64 100 3"), (1500, "notesRaw 76 100")]
    _, a = run(li, 3.5)
    t = peaks(seg(a, 2.5, 3.5), 20)
    e = any(has(t, 329.63 * r) for r in (0.5, 1, 2))
    check("listening: the next chord holds the note held", e, f"peaks {sorted(round(x) for x in t)[:12]}")

    # ---- the roadmap: built (aux + top C#) at 200 bpm from 4 minutes - its first section 'emerge' brings only the
    # drone; 4 bars later (4.8 s) 'establish' brings the sub and pads in. On the SECTN page a layer key edits the
    # section (the file roadmap.txt)
    import os
    g = lambda k: M.S("g", None, k)
    gpages = [n for n, _ in M.GLOBAL_PAGES]
    rd = [(50, f"al-set {g('Road')} 0.9"), (51, f"al-set {g('Mins')} 0"), (52, f"al-set {g('Tempo')} 1"),
          (100, "aux 1"), (150, "notesRaw 73 100"), (160, "notesRaw 73 0"), (200, "aux 0"), START]
    # (the first section shortened to 4 bars on the SECTN page: Bars, for the section Sect shows)
    log, _ = H.run(rd + [(300, f"al-set {g('SBars')} 0")], 9, d=d, keep=True, prints=("al-inset",))
    ins = [l for l in log.splitlines() if l.startswith("al-inset")]
    check("the roadmap runs its sections (auto)", ins[:3] == ["al-inset: 1 0", "al-inset: 2 0", "al-inset: 3 0"] and
          "al-inset: 1 1" in ins and "al-inset: 2 1" in ins, " ".join(i.split(": ")[1] for i in ins))
    keys = [(400 + 100 * i, "notesRaw 68 100") for i in range(gpages.index("SECTN") + 1)]
    log, _ = H.run(rd[:-1] + keys + [(2000, "notesRaw 71 100"), (2050, "notesRaw 71 0")], 3, d=d, keep=True)
    line1 = open(os.path.join(d, "roadmap.txt")).read().splitlines()[0]
    check("a layer key edits the section on the SECTN page", line1.split()[2] == str(1 + 64), f"section 1: {line1}")

    # ---- counterpoint: the pads' top voice steps to a neighbour and back on every 8th (Lines 100 %); at 0, still
    pl = M.S("pad", None, "Lines")
    log, _ = H.run(solo("pad") + [(50, f"al-set {pl} 1"), START], 3, d=d, keep=True, prints=("al-pad-n",))
    moves = [l for l in log.splitlines() if l.startswith("al-pad-n") and l.endswith(" 80")]
    log0, _ = H.run(solo("pad") + [START], 3, d=d, keep=True, prints=("al-pad-n",))
    still = [l for l in log0.splitlines() if l.startswith("al-pad-n") and l.endswith(" 80")]
    notes_ = sorted({int(float(l.split()[2])) for l in moves})
    # (Cm7's top voice is Bb (70): its neighbours in C dorian, C above and A below, in turn)
    check("counterpoint: a voice steps away and back", len(moves) >= 8 and not still and notes_ == [69, 70, 72],
          f"{len(moves)} moves between {notes_}, {len(still)} at Lines 0")

    # ---- motif: the pads' loop (A, C, E) played by percussion lane 1 (Pitch motif, Source pads), an octave up
    mo = [(30, "al-sel-pad bang"), (40, f"al-set {M.S('perc1', None, 'Pitch')} {(8 + 0.5) / len(M.PITCHES)}"),
          (41, f"al-set {M.S('perc1', None, 'MSrc')} {(2 + 0.5) / 7}"), START, (600, "notesRaw 75 100")]
    for i, n in enumerate((57, 60, 64)):
        mo += [(700 + 400 * i, f"al-midi {n} 100 1"), (900 + 400 * i, f"al-midi {n} 0 1")]
    mo += [(2400, "notesRaw 75 100")]
    log, _ = H.run(mo, 6, d=d, keep=True, prints=("al-perc1-hit",))
    hits_ = [int(float(l.split()[2])) for l in log.splitlines() if l.startswith("al-perc1-hit")]
    late = hits_[len(hits_) // 2:]
    check("motif: a lane plays another layer's loop", late and set(late) <= {69, 72, 76} and len(set(late)) >= 2,
          f"lane notes {sorted(set(late))} (69 72 76)")

    # ---- the global pages: MAIN (key, tempo, scale, mode - its name from the scale), then LAYERS (the layers' engines)
    sc_, md_ = M.S('g', None, 'Scale'), M.S('g', None, 'Mode')
    ev = [(100, "notesRaw 68 100"), (150, "notesRaw 68 0"), (300, f"al-set {sc_} {(1 + 0.5) / len(M.SCALES)}"),
          (310, f"al-set {md_} {(4 + 0.5) / M.MAX_MODES}"), (400, "knob1 0.5"), (1000, "notesRaw 68 100"),
          (1050, "notesRaw 68 0")]
    log, _ = H.run(ev, 1.5, d=d, keep=True)
    scr = " | ".join(l.split(" 8 1 ", 1)[1] for l in log.splitlines() if "gPrintln 3 0 " in l and " 8 1 " in l)
    want = ["Key C", "Tempo 84", "Scale harmin", "Mode phrdom", "LAYERS", "DRONE analog", "PADS sine"]
    check("MAIN: key, tempo, scale, mode; LAYERS: the engines", all(w in scr for w in want),
          ", ".join(w for w in want if w not in scr) or "all shown")
    # a lane playing the scale (Pitch 'scl up') in C harmonic minor: its notes and only its notes
    ev = solo("perc1") + [(30, f"al-set {sc_} {(1 + 0.5) / len(M.SCALES)}"), (31, f"al-set {md_} {0.5 / M.MAX_MODES}"),
                          (32, f"al-set {M.S('perc1', None, 'Pitch')} {(5 + 0.5) / len(M.PITCHES)}"), START]
    log, _ = H.run(ev, 5, d=d, keep=True, prints=("al-perc1-hit",))
    pcs = sorted({int(float(l.split()[2])) % 12 for l in log.splitlines() if l.startswith("al-perc1-hit")})
    check("the scale and mode reach the notes (C harmonic minor)", set(pcs) <= {0, 2, 3, 5, 7, 8, 11} and
          {8, 11} <= set(pcs), f"pitch classes {pcs}")

    # ---- a tapped rhythm: aux + top D# with lane 1 shown, three notes at steps 0, 3 and 5 of the cycle (8 steps of a
    # 16th): it becomes the lane's pattern - those gaps (3 2 3), and then 3 hits a cycle (2 cycles: 6)
    ev = solo("perc1") + [(30, "al-sel-perc1 bang"), (40, f"al-set {M.S('perc1', None, 'Steps')} {6 / 14}"),
                          (41, f"al-set {M.S('perc1', None, 'Rate')} {(3 + 0.5) / 6}"),
                          (43, f"al-set {M.S('perc1', None, 'Phase')} 0.01"), START,
                          (1000, "aux 1"), (1010, "notesRaw 75 100"), (1020, "aux 0")]
    step = 60000 / (84 * 4)
    ev += [(1030 + int(st * step), "al-note 3 60 0.8") for st in (0, 3, 5)]
    t_end = 1010 + 8 * step + 300
    ev += [(int(t_end), "h-q bang"), (int(t_end + 16 * step), "h-q bang")]

    def tapq(c):
        c.c(c.ch(c.obj("r h-q", 900, 700), "array get altap 48 8"), 0, c.obj("print TAP", 900, 760), 0)
        c.c(c.obj("r h-q", 1100, 700), 0, c.obj("print MARK", 1100, 760), 0)
    log, _ = H.run(ev, t_end / 1000 + 16 * step / 1000 + 0.3, d=d, keep=True, extra=tapq, prints=("al-perc1-hit",))
    tl = [l for l in log.splitlines() if l.startswith("TAP")]
    tsteps = [i for i, v in enumerate(tl[0].split()[1:]) if float(v) > 0] if tl else []
    gaps = sorted((tsteps[(i + 1) % len(tsteps)] - tsteps[i]) % 8 for i in range(len(tsteps))) if tsteps else []
    seq = [l for l in log.splitlines() if l.startswith(("MARK", "al-perc1-hit"))]
    m = [i for i, l in enumerate(seq) if l.startswith("MARK")]
    between = sum(1 for l in seq[m[0] + 1:m[1]] if l.startswith("al-perc1-hit")) if len(m) == 2 else -1
    check("a tapped rhythm becomes the lane's pattern", gaps == [2, 3, 3] and between == 6,
          f"steps {tsteps} (gaps {gaps}), {between} hits in 2 cycles")

    # ---- every engine of every layer sounds (one second each, in turn), and nothing in Pd complains
    for L in ("drone", "pad", "perc1"):
        names = [e for e, _ in M.engines(L)]
        ev = solo(L) + [START] + [(1000 + 1000 * i, f"al-set {M.S(L, None, 'Engine')} {M.engine_value(L, e)}")
                                  for i, e in enumerate(names)]
        log, a = H.run(ev, 1.2 + len(names), d=d, keep=True)
        lv = [H.rms_db(seg(a, 1.5 + i, 1.95 + i)) for i in range(len(names))]
        quiet = [f"{e} {v:.0f}" for e, v in zip(names, lv) if v < -50]
        check(f"every {M.kind(L)} engine sounds ({len(names)})", not quiet and not H.errors(log),
              f"quietest {min(lv):.0f} dB" + (f"; silent: {quiet}" if quiet else "") + (f"; {H.errors(log)[:1]}" if H.errors(log) else ""))

    # CPU: everything playing, offline speed vs real time (x86; the Organelle's CM3 is roughly 10-15x slower)
    t0 = time.time()
    run(on + [(25, f"al-inset {M.LAYERS.index('cloud')} 1"), START], 30)        # (all four lanes and the cloud in)
    rt = (time.time() - t0) / 30
    # (a report more than a test: machines differ - it fails only when something has gone badly wrong)
    check("CPU", rt < 0.5, f"{100 * rt:.1f} % of real time on this machine")
    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: {', '.join(FAILS)}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
