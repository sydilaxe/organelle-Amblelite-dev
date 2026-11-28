"""Offline checks in Pure Data: python3 check.py. Each check builds nothing new (one build, reused) and prints
PASS / FAIL with what it measured."""
import os
import sys
import time
import numpy as np
import harness as H
import model as M

SR = 44100
START = (200, "notesRaw 72 100")
FAILS = []


def features_piece_len():
    import features
    return features.PIECE


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
                          (52, f"al-set {M.S('pad', 'wave', 'Table')} {(M.WAVE_TABLES.index('reson') + 0.5) / len(M.WAVE_TABLES)}"),
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
    lt, lr, ld = (M.S("pad", None, k) for k in ("L1Tgt", "L1Rate", "L1Dep"))
    lfo = [(40, f"al-set {lt} {M.target_value('pad', M.engines('pad')[0][0], 'Level')}"), (41, f"al-set {lr} {opt_v(13, 16)}"), (42, f"al-set {ld} 1"),
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

    # an LFO on a percussion lane's engine (its blip's Flick): the knob reaches it and it moves
    fl = M.S("perc1", "blip", "Flick")
    pl = [(40, f"al-set {M.S('perc1', None, 'Engine')} {M.engine_value('perc1', 'blip')}"),
          (41, f"al-set {M.S('perc1', None, 'L1Tgt')} {M.target_value('perc1', 'blip', 'Flick')}"),
          (42, f"al-set {M.S('perc1', None, 'L1Rate')} {opt_v(13, 16)}"), (43, f"al-set {M.S('perc1', None, 'L1Dep')} 1")]
    log, _ = H.run(pl + [START], 2, d=d, keep=True, prints=(f"al-s{fl}",))
    vals = {l.split(":")[-1].strip() for l in log.splitlines() if l.startswith(f"al-s{fl}:")}
    check("an LFO moves a percussion engine's own parameter", len(vals) > 10, f"{len(vals)} values of Flick")

    # ... and it moves a hit while it rings: one long bowl hit, its upper partial swept by an LFO on Strtch (1 Hz)
    def upper(lfo_on):
        ev = [(10, "al-sel-perc1 bang"), (20, f"al-set {M.S('perc1', None, 'Engine')} {M.engine_value('perc1', 'bowl')}"),
              (21, f"al-set {M.S('perc1', None, 'Decay')} 1"), (22, f"al-set {M.S('perc1', None, 'Evolve')} 0")]
        if lfo_on:
            ev += [(30, f"al-set {M.S('perc1', None, 'L1Tgt')} {M.target_value('perc1', 'bowl', 'Strtch')}"),
                   (31, f"al-set {M.S('perc1', None, 'L1Rate')} {opt_v(13, 16)}"), (32, f"al-set {M.S('perc1', None, 'L1Dep')} 1")]
        _, a = run(ev + [(500, "al-midi 69 100 1")], 2.8)
        out = []
        for t in np.arange(0.7, 2.5, 0.2):
            m = seg(a, t, t + 4096 / SR).mean(axis=1)
            sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
            f = np.fft.rfftfreq(len(m), 1 / SR)
            band = (f > 1800) & (f < 5500)
            out.append(round(float(f[band][np.argmax(sp[band])])))
        return out
    still, moved = upper(False), upper(True)
    check("an LFO moves a ringing hit (bowl Strtch)", len(set(still)) == 1 and max(moved) - min(moved) > 150,
          f"upper partial {min(moved)} .. {max(moved)} Hz (off: {sorted(set(still))})")

    # a long Decay: the lane's voices are struck again while they ring - faded out first, never a step (a click)
    ev = solo("perc1") + [(30, f"al-set {M.S('perc1', None, 'Engine')} {M.engine_value('perc1', 'wood')}"),
                          (31, f"al-set {M.S('perc1', None, 'Decay')} 0.9"), (32, f"al-set {M.S('perc1', 'wood', 'Knock')} 0"),
                          (33, f"al-set {M.S('perc1', None, 'Evolve')} 0"), START]
    _, a = run(ev, 8)
    st = np.abs(np.diff(seg(a, 1, 7.9).mean(axis=1), 2))
    check("a ringing voice struck again doesn't click", st.max() < 0.03,
          f"largest step {st.max():.4f} (a click: > 0.03; before the fix 0.11)")

    # assign: aux held, knob 1 - the FAV page's first place takes another parameter
    # (the pads' page opened again after aux is let go - which goes home - shows knob 1's new parameter)
    log, _ = H.run([(100, "al-sel-pad bang"), (300, "aux 1"), (400, "knob1 0.95"), (500, "aux 0"),
                    (700, "al-sel-pad bang")], 1, d=d, keep=True)
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

    # snapshots: save 1, change the pads' engine and level, recall 1 (morph 0): back as it was
    eng, lv = M.S("pad", None, "Engine"), M.S("pad", None, "Level")
    ev = [(50, f"al-set {M.S('g', None, 'Morph')} 0"), START, (500, "notesRaw 82 100"), (510, "aux 1"),
          (520, "notesRaw 60 100"), (530, "aux 0"), (540, "notesRaw 82 0"),
          (800, f"al-set {eng} 0.3"), (810, f"al-set {lv} 0.1"),
          (1500, "notesRaw 82 100"), (1510, "notesRaw 60 100"), (1520, "notesRaw 82 0")]
    log, a = H.run(solo("pad") + ev, 2.5, d=d, keep=True, prints=("oscOut",))
    heads = [l for l in log.splitlines() if "gPrintln 3 0 0 " in l]
    r1, r2 = H.rms_db(seg(a, 1.2, 1.5)), H.rms_db(seg(a, 2.0, 2.4))
    check("save, change, recall", r2 - r1 > 6 and any("SAVED" in l for l in heads) and any("LOADED" in l for l in heads),
          f"level {r1:.1f} -> recalled {r2:.1f} dB")

    # COMPARE (as Amble): save, turn the level down (the header: RUN*); top A# tapped: the saved sound (loud), tapped
    # again: yours (quiet); held: the saved one while held, yours again when let go
    ev = [START, (500, "notesRaw 82 100"), (510, "aux 1"), (520, "notesRaw 60 100"), (530, "aux 0"),
          (540, "notesRaw 82 0"), (800, f"al-set {lv} 0.1"),
          (1500, "notesRaw 82 100"), (1550, "notesRaw 82 0"), (2500, "notesRaw 82 100"), (2550, "notesRaw 82 0"),
          (3200, "notesRaw 82 100"), (4300, "notesRaw 82 0")]
    log, a = H.run(solo("pad") + ev, 6.8, d=d, keep=True, prints=("oscOut",))
    heads = [l for l in log.splitlines() if "gPrintln 3 0 0 " in l]
    lv_ = [H.rms_db(seg(a, t0, t1)) for t0, t1 in ((1.1, 1.45), (2.0, 2.45), (2.95, 3.15), (3.8, 4.25), (4.75, 5.1))]
    ok = lv_[1] - lv_[0] > 6 and lv_[1] - lv_[2] > 6 and lv_[3] - lv_[2] > 6 and lv_[3] - lv_[4] > 6
    check("compare: a tap flips saved / yours, a hold hears the saved one", ok and any("RUN*" in l for l in heads),
          " > ".join(f"{x:.0f}" for x in lv_) + " dB (yours, saved, yours, held, yours)"
          + ("" if any("RUN*" in l for l in heads) else "; no RUN* mark"))

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
    ev3 = solo("sub") + q + [START, (998, "notesRaw 77 100"), (1000, "notesRaw 77 100"), (1001, "al-midi 69 100 1"), (1500, "al-midi 69 0 1"),
                             (2400, "al-midi 76 100 1"), (2900, "al-midi 76 0 1"), (3700, "notesRaw 77 100")]
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
    # a profile: the nanoKONTROL Studio with the Amble Lite set (korg.py) - scene 5 (channel 15): slider 1 the drone's
    # level, M 1 takes it out, knob 2 the page's second knob; scene 1 (channel 11): knob 2 the sub's filter (a
    # parameter by name); scene 2 (channel 12): knob 1 the drone's engine's first parameter; the same CC on channel 1
    # does nothing
    ki = M.PROFILES.index("nanoktl")
    log, _ = H.run([(100, f"al-set {pr} {(ki + 0.5) / len(M.PROFILES)}"), (300, "al-cc 20 2 15"), (400, "al-cc 127 21 15"),
                    (500, "al-cc 100 14 15"), (600, "al-cc 64 14 11"), (700, "al-cc 32 13 12"), (800, "al-cc 90 14 1")],
                   1, d=d, keep=True, prints=("al-set", "al-inset"))
    got = [l for l in log.splitlines() if l.startswith("al-set:")]
    want = [f"al-set: {S_('drone', None, 'Level')} 0.15748", f"al-set: {S_('sub', None, 'Cutoff')} 0.503937",
            f"al-set: {S_('drone', 'analog', 'WaveA')} 0.251969"]
    ok = all(w in got for w in want) and "al-inset: 0 0" in log and any(l.endswith(" 0.787402") for l in got) \
        and not any(l.endswith(" 0.708661") for l in got)
    check("controller profile (nanoKONTROL Studio, Amble Lite set)", ok,
          "slider, M button, page knob, a named parameter, an engine's parameter, channels apart" if ok else
          f"missing: {[w for w in want if w not in got]}")

    # MPE: a note on channel 3 bent up a semitone (range 2) on its own, then its pressure lowers its level
    mp = solo("sub") + [(50, f"al-set {chans} 0.75"), (51, f"al-set {bend} 0.1"), (52, "al-sel-sub bang"), START,
                        (900, "al-bendin 12288 3"), (1000, "al-midi 69 100 3"), (3000, "al-touchin 20 3")]
    _, a = run(mp, 4.5)
    hz = peak_hz(seg(a, 1.8, 2.8), 30, 400)
    l1, l2 = H.rms_db(seg(a, 2.0, 2.8)), H.rms_db(seg(a, 3.6, 4.4))
    check("MPE: a note's own bend and pressure", abs(hz - 116.5) < 2 and l1 - l2 > 6,
          f"{hz:.1f} Hz (116.5), pressure {l1:.1f} -> {l2:.1f} dB")

    # breath (the generic profile: CC 2) -> the pads' cutoff (their BREATH page): brighter as it blows
    bt = [(50, f"al-set {S_('pad', None, 'BTgt')} {M.target_value('pad', 'saws', 'Cutoff')}"), (51, f"al-set {S_('pad', None, 'BDep')} 1"),
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

    # SHAPE (the MIX view's last page): the filter's two sides, Drive and Blur on the saws' chord
    fl, dr, bl = (M.S("g", None, n) for n in ("Filter", "Drive", "Blur"))
    saws = solo("pad") + [(52, f"al-set {M.S('pad', None, 'Evolve')} 0"),
                          (54, f"al-set {M.S('pad', None, 'Engine')} {M.engine_value('pad', 'saws')}"), START]
    shp = {}
    for name, ev in (("flat", []), ("lp", [(60, f"al-set {fl} 0.15")]), ("hp", [(60, f"al-set {fl} 1")]),
                     ("drive", [(60, f"al-set {dr} 1")]), ("blur", [(60, f"al-set {bl} 1")])):
        _, x = run(saws + ev, 3)
        shp[name] = seg(x, 1.5, 3)
    br = {k: bright(v) for k, v in shp.items()}
    lvl = {k: H.rms_db(v) for k, v in shp.items()}
    sane = all(not np.isnan(v).any() and float(np.abs(v).max()) < 0.99 for v in shp.values())
    def low_db(x, hz=250):
        m = x.mean(axis=1)
        sp = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
        f = np.fft.rfftfreq(len(m), 1 / SR)
        return 10 * np.log10(sp[f < hz].sum() + 1e-12)
    lo_cut = low_db(shp["flat"]) - low_db(shp["hp"])
    check("SHAPE Filter: low-pass left, high-pass right", br["lp"] < 0.6 * br["flat"] and lo_cut > 12,
          f"brightness {br['flat']:.0f} Hz, LP {br['lp']:.0f}; HP: below 250 Hz {lo_cut:.1f} dB down")
    check("SHAPE Drive: brighter, the level kept", br["drive"] > 1.15 * br["flat"] and abs(lvl["drive"] - lvl["flat"]) < 6
          and sane, f"brightness {br['drive']:.0f} Hz, level {lvl['flat']:.1f} -> {lvl['drive']:.1f} dB")
    corr = lambda v: float(np.corrcoef(v[:, 0], v[:, 1])[0, 1])
    check("SHAPE Blur: wider, the level kept", corr(shp["blur"]) < corr(shp["flat"]) - 0.05 and
          abs(lvl["blur"] - lvl["flat"]) < 6, f"L/R correlation {corr(shp['flat']):.2f} -> {corr(shp['blur']):.2f}, "
          f"level {lvl['flat']:.1f} -> {lvl['blur']:.1f} dB")

    # notes out (MIDI 2 NoteOt): the drone, sub and pads out on channels 2, 3, 4, a lane on 5; a chord change ends
    # the old notes and starts the new; NoteOt off ends every note still out
    no_ = M.S("g", None, "NoteOut")
    log, _ = H.run([(40, f"al-set {no_} 0.75"), (45, f"al-inset {M.LAYERS.index('perc1')} 1"), START,
                    (2600, f"al-set {no_} 0.25")], 3, d=d, keep=True, prints=("al-xnote",))
    xs = [tuple(float(v) for v in l.split(": ")[1].split()) for l in log.splitlines() if l.startswith("al-xnote")]
    ons = {}
    for n_, v_, ch_ in xs:
        ons[(n_, ch_)] = ons.get((n_, ch_), 0) + (1 if v_ > 0 else -1)
    chans = sorted({int(ch_) for _, v_, ch_ in xs if v_ > 0})
    hanging = [k for k, v in ons.items() if v > 0]
    check("notes out: each layer on its channel, every note ended", chans[:4] == [2, 3, 4, 5] and not hanging and
          len(xs) > 8, f"{len(xs)} messages, channels {chans}, still on after NoteOt off: {hanging or 'none'}")
    log, _ = H.run([START], 1.5, d=d, keep=True, prints=("al-xnote",))
    check("notes out: nothing while off", "al-xnote" not in log, "silent" if "al-xnote" not in log else "sent")

    # notes mode: aux + a layer key chooses the pads; aux + top F taps arm, record, overdub, play; held 0.5 s it
    # stops the loop, held again plays it - and aux held so long in a combo never erases
    import re as _re
    tp = lambda t, k: [(t, f"notesRaw {k} 100"), (t + 60, f"notesRaw {k} 0")]
    ev = tp(100, 72) + tp(200, 70) + [(300, "aux 1")] + tp(320, 64) + [(400, "aux 0")]
    ev += [(500, "aux 1")] + tp(520, 77) + [(600, "aux 0")]
    ev += [(3000 + 200 * i, f"notesRaw {60 + i} 100") for i in range(4)] + [(3100 + 200 * i, f"notesRaw {60 + i} 0") for i in range(4)]
    ev += [(4000, "aux 1")] + tp(4020, 77) + [(4100, "aux 0"), (5000, "aux 1")] + tp(5020, 77) + [(5100, "aux 0")]
    ev += [(6000, "aux 1"), (6020, "notesRaw 77 100"), (6800, "notesRaw 77 0"), (6850, "aux 0")]
    ev += [(7500, "aux 1"), (7520, "notesRaw 77 100"), (8300, "notesRaw 77 0"), (8350, "aux 0")]
    log, _ = H.run(ev, 9, d=d, keep=True, prints=("oscOut",))
    seen = []
    for l in log.splitlines():
        m = _re.search(r"gPrintln 3 0 0 8 1 (\S+)", l)
        if m and m.group(1) in ("ARMED", "REC", "DUB", "PLAY", "STOPPED", "ERASE") and (not seen or seen[-1] != m.group(1)):
            seen.append(m.group(1))
    check("notes mode: the loop by aux + top F, held to stop and start",
          seen == ["ARMED", "REC", "DUB", "PLAY", "DUB", "STOPPED", "PLAY"], " -> ".join(seen))

    # the cloud's engines on the drone: each adds to the sound (grains, rhythm in time, the delay); the delay held
    # keeps its loop after the drone has gone - without Hold (and no feedback) it falls silent
    ce = M.S("cloud", None, "Engine")
    cl_names = [e for e, _ in M.engines("cloud")]
    dron = [(60 + i, f"al-inset {i} {1 if o in ('drone', 'cloud') else 0}") for i, o in enumerate(M.LAYERS)]
    # (measured once the drone has left - only the cloud can sound there: grains and rhythm read the recording,
    # the delay repeats)
    gone = (2600, f"al-inset {M.LAYERS.index('drone')} 0")
    lv = []
    for e in cl_names:
        _, a1 = run(dron + [(70, f"al-set {ce} {M.engine_value('cloud', e)}"), START, gone], 4)
        lv.append((e, H.rms_db(seg(a1, 3.2, 4))))
    check("every cloud engine sounds", all(v > -60 for _, v in lv), ", ".join(f"{e} {v:.0f} dB" for e, v in lv) +
          " (after the drone left)")
    dl = lambda k: M.S("cloud", "delay", k)
    held = dron + [(70, f"al-set {ce} {M.engine_value('cloud', 'delay')}"), (71, f"al-set {dl('Time')} 0.6"), START,
                   (2500, f"al-set {dl('Hold')} 0.5"), (2600, f"al-inset {M.LAYERS.index('drone')} 0")]
    _, ah = run(held, 7)
    _, af = run(held[:-2] + [(2500, f"al-set {dl('Fdbk')} 0"), (2600, f"al-inset {M.LAYERS.index('drone')} 0")], 7)
    check("the delay held keeps its loop", H.rms_db(seg(ah, 5.5, 7)) > H.rms_db(seg(af, 5.5, 7)) + 30,
          f"held {H.rms_db(seg(ah, 5.5, 7)):.0f} dB, not held {H.rms_db(seg(af, 5.5, 7)):.0f} dB, 3 s after the drone went")

    # zones: low notes to the sub, middle ones to the pads (whatever is shown)
    log, _ = H.run([(50, f"al-set {zones} 0.75"), START, (500, "al-midi 40 100 1"), (600, "al-midi 60 100 1")], 1,
                   d=d, keep=True, prints=("al-user-sub", "al-user-pad"))
    ok = "al-user-sub: 40 0.787402" in log and "al-user-pad: 60 0.787402" in log
    check("zones split the keyboard", ok, "40 -> sub, 60 -> pads" if ok else log[-200:])

    # ---- free loops (Len free): a 2.1 s loop played with the transport stopped. Lock off: it goes round on its own
    # (the transport stays stopped); clock: it locks to 1 bar at 84 bpm and starts the transport; tempo: the tempo
    # becomes 113, the loop 1 bar of it. On the clock, a loop starts from its beginning when the transport starts
    lpl_, lck_ = S_("drone", None, "LpLen"), S_("drone", None, "Lock")
    tmp_ = S_("g", None, "Tempo")

    def freeloop(lockv, more=(), secs=9):
        ev = solo("drone") + [(100, f"al-set {lpl_} {1.5 / len(M.LOOP_LENS)}"),
                              (101, f"al-set {lck_} {(lockv + 0.5) / len(M.LOOP_LOCKS)}"),
                              (300, "al-notesmode bang"), (320, "al-sel-drone bang"), (400, "al-loop bang"),
                              (1000, "notesRaw 64 100"), (1200, "notesRaw 64 0"), (1700, "notesRaw 67 100"),
                              (1900, "notesRaw 67 0"), (3100, "al-loop bang"), (8800, "h-q bang")] + list(more)
        ev += [(t, f"h-mark {t}") for t in range(0, secs * 1000, 10)]

        def probe(c):
            c.c(c.obj("r h-mark", 900, 700), 0, c.obj("print MARK", 900, 730), 0)
            c.c(c.ch(c.obj("r h-q", 900, 760), f"expr alrun*1000 + {num_(tmp_)}"), 0, c.obj("print Q", 900, 800), 0)
        log, _ = H.run(ev, secs, d=d, keep=True, prints=("al-in-drone",), extra=probe)
        cur, hits, q = 0, [], None
        for l in log.splitlines():
            if l.startswith("MARK"):
                cur = int(l.split()[-1])
            elif l.startswith("al-in-drone") and not l.endswith(" 0"):
                hits.append((cur, int(l.split()[1])))
            elif l.startswith("Q"):
                q = float(l.split()[-1])
        return hits, q
    num_ = lambda sl: f"int({M.SLOTS[sl][1].lo} + alp[{sl}]*{M.SLOTS[sl][1].hi - M.SLOTS[sl][1].lo} + 0.5)"
    # (the cycles from the first note's: the first, as played - then each repeat)
    period = lambda hits: [b[0] - a[0] for a, b in zip([h for h in hits if h[1] == 64], [h for h in hits if h[1] == 64][1:])]
    h0, q0 = freeloop(0)
    p0 = period(h0)
    check("a free loop plays on its own clock (Lock off)", q0 is not None and q0 < 1000 and len(p0) >= 3 and
          all(abs(x - 2120) <= 30 for x in p0), f"transport {'running' if q0 and q0 >= 1000 else 'stopped'}, "
          f"cycles {p0} ms (played 2.1 s)")
    h1, q1 = freeloop(1)
    p1 = period(h1)
    bar84 = 240000 / 84
    check("Lock clock: the loop fits to whole bars and starts the transport", q1 is not None and q1 >= 1000 and
          len(p1) >= 2 and abs(p1[0] - 2100) <= 30 and all(abs(x - bar84) <= 30 for x in p1[1:]),
          f"cycles {p1} ms (played 2.1 s; a bar at 84 bpm: {bar84:.0f})")
    h2, q2 = freeloop(2)
    p2 = period(h2)
    check("Lock tempo: the tempo is set so the loop is whole bars", q2 is not None and int(q2) % 1000 == 113 and
          len(p2) >= 2 and all(abs(x - 240000 / 113) <= 30 for x in p2[1:]),
          f"tempo {int(q2) % 1000 if q2 else '-'}, cycles {p2} ms")
    h3, _ = freeloop(1, [(6000, "al-startstop bang"), (7000, "al-startstop bang")], 10)
    first = [t for t, n in h3 if t >= 6990]
    check("on the clock, a loop starts from its beginning with the transport", bool(first) and first[0] <= 7040 and
          [n for t, n in h3 if t >= 6990][:1] == [64], f"first note after the restart (7000 ms): {first[:1]}")

    # a zone's breath, looped: the sub's breath (to its level) recorded with its notes in one bar; the next cycle
    # plays it back with no breath - loud where it blew, quiet where it didn't
    zb = solo("sub") + [(50, f"al-set {zones} 0.75"), (51, f"al-set {S_('sub', None, 'BTgt')} {M.target_value('sub', M.engines('sub')[0][0], 'Level')}"),
                        (52, f"al-set {S_('sub', None, 'BDep')} 1"), (53, f"al-set {S_('sub', None, 'Level')} 0.15"),
                        (54, f"al-set {S_('g', None, 'Bars')} 0.05"), START,
                        (998, "notesRaw 77 100"), (1000, "notesRaw 77 100"), (1001, "al-midi 45 100 1"), (1010, "al-cc 127 2 1"),
                        (2000, "al-cc 0 2 1"), (3800, "al-midi 45 0 1"), (3810, "notesRaw 77 100")]
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
          (100, "aux 1"), (150, "notesRaw 81 100"), (160, "notesRaw 81 0"), (200, "aux 0"), START]
    # (the first section shortened to 4 bars on the SECTN page: Bars, for the section Sect shows)
    log, _ = H.run(rd + [(300, f"al-set {g('SBars')} 0")], 9, d=d, keep=True, prints=("al-inset",))
    ins = [l for l in log.splitlines() if l.startswith("al-inset")]
    check("the roadmap runs its sections (auto)", ins[:3] == ["al-inset: 1 0", "al-inset: 2 0", "al-inset: 3 0"] and
          "al-inset: 1 1" in ins and "al-inset: 2 1" in ins, " ".join(i.split(": ")[1] for i in ins))
    keys = [(400 + 100 * i, "notesRaw 68 100") for i in range(gpages.index("SECTN") + 1)]
    log, _ = H.run(rd[:-1] + keys + [(2000, "notesRaw 71 100"), (2050, "notesRaw 71 0")], 3, d=d, keep=True)
    line1 = open(os.path.join(d, "roadmap.txt")).read().splitlines()[0]
    check("a layer key edits the section on the SECTN page", line1.split()[2] == str(1 + 64), f"section 1: {line1}")

    # ---- a section's parameter changes (roadmap.changes): on the SECTN page with section 2 chosen, Filter and the
    # pads' Cutoff turned, top A# captures them (roadchg.txt line 2); playing on, section 2 sets them again (the
    # Filter turned back in between); saving piece 1 keeps them (sections.txt), loading it brings them back
    fl_, pc_ = g("Filter"), M.S("pad", None, "Cutoff")
    sect2 = [(300 + 40 * i, "notesRaw 68 100") for i in range(gpages.index("SECTN") + 1)] + \
        [(1000, f"al-set {g('Sect')} {1 / (M.MAXSEC - 1)}"), (1200, f"al-set {fl_} 0.8"), (1210, f"al-set {pc_} 0.2"),
         (1400, "notesRaw 82 100"), (1450, "notesRaw 82 0")]
    H.run(rd[:-1] + [(250, f"al-set {g('Morph')} 0")] + sect2, 2, d=d, keep=True)
    rc = open(os.path.join(d, "roadchg.txt")).read().splitlines()
    pairs = rc[1].split() if len(rc) > 1 else []
    got = dict(zip(pairs[1::2], pairs[2::2]))
    check("a section captures its changes (SECTN, top A#)", len(rc) == M.MAXSEC and pairs[:1] == ["2"] and
          got.get(str(fl_)) == "0.8" and got.get(str(pc_)) == "0.2", f"line 2: {rc[1] if len(rc) > 1 else '-'}")
    log, _ = H.run([(50, f"al-set {g('Road')} 0.9"), (60, f"al-set {g('Morph')} 0"), START,
                    (400, f"al-set {fl_} 0.5"), (600, "al-rnext bang")], 1, d=d, keep=True, prints=("al-set",))
    after = log[log.find(f"al-set: {fl_} 0.5"):]
    check("a section sets its changes when it starts", f"al-set: {fl_} 0.8" in after and f"al-set: {pc_} 0.2" in after,
          "Filter back to 0.8, pads' Cutoff 0.2" if f"al-set: {fl_} 0.8" in after else "not applied")
    piece_keys = [(100 + 40 * i, "notesRaw 68 100") for i in range(gpages.index("PIECE") + 1)]
    H.run(piece_keys + [(800, f"al-set {g('Piece')} 0.01"), (900, "aux 1"), (950, "notesRaw 82 100"),
                        (1000, "notesRaw 82 0"), (1050, "aux 0")], 1.3, d=d, keep=True)
    sec = open(os.path.join(d, "sections.txt")).read().splitlines()
    open(os.path.join(d, "roadchg.txt"), "w").write("0\n" * M.MAXSEC)
    H.run(piece_keys + [(800, f"al-set {g('Piece')} 0.01"), (950, "notesRaw 82 100"), (1000, "notesRaw 82 0")], 1.3,
          d=d, keep=True)
    rc2 = open(os.path.join(d, "roadchg.txt")).read().splitlines()
    check("a piece keeps its sections' changes", len(sec) == 8 * M.MAXSEC and sec[1] == rc[1] and rc2[1] == rc[1],
          f"sections.txt line 2: {sec[1] if len(sec) > 1 else '-'}; loaded back: {rc2[1] if len(rc2) > 1 else '-'}")

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
          (41, f"al-set {M.S('perc1', None, 'MSrc')} {(2 + 0.5) / 7}"), START, (598, "notesRaw 77 100"), (600, "notesRaw 77 100")]
    for i, n in enumerate((57, 60, 64)):
        mo += [(700 + 400 * i, f"al-midi {n} 100 1"), (900 + 400 * i, f"al-midi {n} 0 1")]
    mo += [(2400, "notesRaw 77 100")]
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

    # ---- the filter doesn't crackle when its cutoff is turned by hand: a sine pad (no highs of its own) through a
    # resonant filter, the knob moved every 20 ms - nothing above 5 kHz grows while it moves
    ev = solo("pad") + [(30, f"al-set {M.S('pad', None, 'Evolve')} 0"), (31, f"al-set {M.S('pad', None, 'Reso')} 0.6"),
                        (32, f"al-set {M.S('pad', None, 'Cutoff')} 0.3"), START]
    ev += [(2000 + 20 * i, f"al-set {M.S('pad', None, 'Cutoff')} {0.3 + 0.45 * (i if i < 75 else 149 - i) / 74:.4f}")
           for i in range(150)]
    _, a = run(ev, 5.5)
    xm = a.mean(axis=1)

    def hf(seg_):
        sp = np.abs(np.fft.rfft(seg_ * np.hanning(len(seg_)))) ** 2
        fr = np.fft.rfftfreq(len(seg_), 1 / SR)
        return 10 * np.log10(sp[fr > 5000].sum() / (sp.sum() + 1e-20) + 1e-15)
    cr = hf(xm[int(2.0 * SR):int(5.0 * SR)]) - hf(xm[int(0.8 * SR):int(1.9 * SR)])
    check("the filter doesn't crackle when turned", cr < 8, f"highs while moving {cr:+.1f} dB (the old filter: +28)")

    # ---- pieces: on the PIECE page, aux + top A# saves (key F), the key changes (D), top A# loads it back (F)
    gp_ = [n for n, _ in M.GLOBAL_PAGES]
    key_ = M.S('g', None, 'Key')

    def pq(c):
        c.c(c.ch(c.obj("r h-q", 900, 700), f"expr int(alp[{key_}]*12)"), 0, c.obj("print PK", 900, 760), 0)
    ev = [(30, f"al-set {key_} {(5 + 0.5) / 12}")] + [(100 + 60 * i, "notesRaw 68 100") for i in range(gp_.index("PIECE") + 1)]
    ev += [(800, "aux 1"), (850, "notesRaw 82 100"), (900, "notesRaw 82 0"), (950, "aux 0"),
           (1200, f"al-set {key_} {(2 + 0.5) / 12}"), (1300, "h-q bang"),
           (1500, "notesRaw 82 100"), (1550, "notesRaw 82 0"), (1800, "h-q bang")]
    log, _ = H.run(ev, 2, d=d, keep=True, extra=pq)
    pk = [l.split()[-1] for l in log.splitlines() if l.startswith("PK")]
    check("a piece saves and loads (its key)", pk == ["2", "5"] and not H.errors(log),
          f"key after the change {pk[:1]}, after loading {pk[1:2]} (F = 5)" + (f"; {H.errors(log)[:1]}" if H.errors(log) else ""))

    # ---- the audio input: off - nothing; reso - strings only with an input; octave - an octave below and above;
    # listening - a steady A held at the input counts as a held note (HARMNY Listen)
    imode = M.S('g', None, 'InMode')

    def inrun(k, on, inp, extra_ev=(), extra=None, prints=("oscOut",)):
        ev = [(20 + i, f"al-inset {i} {1 if L in on else 0}") for i, L in enumerate(M.LAYERS)]
        ev += [(30, f"al-set {imode} {(k + 0.5) / 6}"), START] + list(extra_ev)
        return H.run(ev, 4, d=d, keep=True, inp=inp, extra=extra, prints=prints)

    def band(x, f0, w=8):
        sp = np.abs(np.fft.rfft(x * np.hanning(len(x))))
        fr = np.fft.rfftfreq(len(x), 1 / SR)
        return 20 * np.log10(sp[(fr > f0 - w) & (fr < f0 + w)].max() + 1e-9)
    _, a0 = inrun(0, [], "osc~ 220")
    quiet = [(25, f"al-set {M.S('pad', None, 'Level')} 0")]
    _, a1 = inrun(1, ["pad"], "osc~ 220", quiet)
    _, a2 = inrun(1, ["pad"], None, quiet)
    _, a5 = inrun(5, [], "osc~ 220")
    x5 = seg(a5, 2, 4).mean(axis=1)
    check("input: off is silent, reso rings with it, octave adds below and above",
          H.rms_db(seg(a0, 2, 4)) < -100 and H.rms_db(seg(a1, 2, 4)) - H.rms_db(seg(a2, 2, 4)) > 40
          and band(x5, 110) > band(x5, 1000) + 30 and band(x5, 440) > band(x5, 1000) + 30,
          f"off {H.rms_db(seg(a0, 2, 4)):.0f} dB, reso {H.rms_db(seg(a1, 2, 4)):.0f} dB (without input "
          f"{H.rms_db(seg(a2, 2, 4)):.0f}), octave 110 / 440 / 1000 Hz {band(x5, 110):.0f} / {band(x5, 440):.0f} / "
          f"{band(x5, 1000):.0f}")

    def hq(c):
        c.c(c.ch(c.obj("r h-q", 900, 700), "array get alhpc 0 12"), 0, c.obj("print HPC", 900, 760), 0)
    log, _ = inrun(3, [], "osc~ 220", [(40, f"al-set {M.S('g', None, 'Listen')} 0.75"), (3500, "h-q bang")], extra=hq)
    hp = [l.split()[1:] for l in log.splitlines() if l.startswith("HPC")]
    check("input: a steady pitch is listened to (A)", bool(hp) and float(hp[0][9]) > 0,
          f"held pitch classes {hp[0] if hp else '-'}")

    # ---- your wavetables: a 4-frame WAV and a single cycle in waves/ - user1 has 4 frames, user2 1, user3 none
    import wave as _wave
    import struct as _struct
    for nm, smp in (("a_multi", [0.4 * np.sin(2 * np.pi * i / 2048) for i in range(4 * 2048)]),
                    ("b_single", [0.8 * (2 * i / 600 - 1) for i in range(600)])):
        w = _wave.open(os.path.join(d, "waves", nm + ".wav"), "wb")
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(b"".join(_struct.pack("<h", int(32000 * v)) for v in smp))
        w.close()

    def uq(c):
        c.c(c.ch(c.obj("r h-q", 900, 700), "array get alwuf 0 3"), 0, c.obj("print UF", 900, 760), 0)
    log, a = H.run(solo("pad") + [(30, f"al-set {M.S('pad', None, 'Engine')} {M.engine_value('pad', 'wave')}"),
                                  (400, f"al-set {M.S('pad', 'wave', 'Table')} {(8 + 0.5) / len(M.WAVE_TABLES)}"),
                                  START, (600, "h-q bang")], 2.5, d=d, keep=True, extra=uq)
    uf = [l.split()[1:] for l in log.splitlines() if l.startswith("UF")]
    for nm in ("a_multi", "b_single"):
        os.remove(os.path.join(d, "waves", nm + ".wav"))
    check("your wavetables load from waves/ (and play)", uf == [["4", "1", "0"]] and H.rms_db(seg(a, 1.5, 2.5)) > -40,
          f"frames {uf[0] if uf else '-'}, user2 plays at {H.rms_db(seg(a, 1.5, 2.5)):.0f} dB")

    # ---- the visualizer (aux + low C#): its frames come, each with the scope and the drone's circle; aux tap: home.
    # PANIC (aux + low D#): the sound fades out and the clock stops, every note released
    def vq(c):
        c.c(c.ch(c.obj("r h-q", 900, 700), "expr alview*10 + alrun"), 0, c.obj("print VW", 900, 760), 0)
    ev = [(20 + i, f"al-inset {i} 1") for i in range(len(M.LAYERS))] + [START, (1000, "aux 1"), (1050, "notesRaw 61 100"),
                                                                       (1100, "notesRaw 61 0"), (1150, "aux 0"),
                                                                       (2500, "h-q bang"), (2600, "aux 1"), (2650, "aux 0"),
                                                                       (2700, "h-q bang"), (3000, "aux 1"), (3050, "notesRaw 63 100"),
                                                                       (3100, "notesRaw 63 0"), (3150, "aux 0"), (12500, "h-q bang")]
    log, a = H.run(ev, 13, d=d, keep=True, extra=vq, prints=("oscOut",))
    vw = [l.split()[-1] for l in log.splitlines() if l.startswith("VW")]
    osc = log.splitlines()
    waves = sum("gWaveform" in l for l in osc)
    lines = sum("gLine 3" in l for l in osc)
    check("visualizer: frames with the scope and the layers' waveform shapes; aux tap: home", vw[:2] == ["31", "1"] and
          waves >= 10 and lines >= 20 * waves, f"view {vw[:2]}, {waves} scope frames, {lines / max(1, waves):.0f} lines a frame")
    # (the cinematic fade: 8 s - still sounding, lower, 3 s in; silent and stopped after it)
    pre, mid, end = H.rms_db(seg(a, 2.0, 2.9)), H.rms_db(seg(a, 6.0, 6.9)), H.rms_db(seg(a, 12.0, 12.9))
    check("panic: a long fade, then stops and releases everything", vw[2:3] == ["0"] and pre > -40 and
          pre - 30 < mid < pre - 6 and end < -70,
          f"running {vw[2:3]} (0: stopped), level {pre:.0f} -> {mid:.0f} (3 s in) -> {end:.0f} dB")
    # (pressed again while it fades: the rest in 0.4 s)
    ev2 = [(20 + i, f"al-inset {i} 1") for i in range(len(M.LAYERS))] + [
        START, (1000, "aux 1"), (1050, "notesRaw 63 100"), (1100, "notesRaw 63 0"), (2000, "notesRaw 63 100"),
        (2050, "notesRaw 63 0"), (2100, "aux 0"), (3000, "h-q bang")]
    log, a = H.run(ev2, 3.5, d=d, keep=True, extra=vq)
    vw2 = [l.split()[-1] for l in log.splitlines() if l.startswith("VW")]
    check("panic pressed twice: the rest of the fade at once", vw2 == ["0"] and H.rms_db(seg(a, 2.6, 3.4)) < -70,
          f"running {vw2} (0: stopped), level after {H.rms_db(seg(a, 2.6, 3.4)):.0f} dB")

    # ---- the looper's flow (the sub, Len 1 bar): armed until the bar line, the first pass, then overdub; a press:
    # play. Aux held over the start of a pass erases the A there while the D played meanwhile replaces it
    BARMS = 96 * 60000 / (84 * 24)
    T0 = 200

    def lq(c):
        c.c(c.ch(c.obj("r h-q", 900, 700), "expr allps[1]"), 0, c.obj("print ST", 900, 760), 0)
        c.c(c.ch(c.obj("r h-n", 1100, 700), "array get allpn 256 4"), 0, c.obj("print NOTES", 1100, 760), 0)
    ev = solo("sub") + [(30, "al-sel-sub bang"), (31, f"al-set {M.S('sub', None, 'LpLen')} {(2 + 0.5) / 7}"), START,
                        (1000, "notesRaw 77 100"), (1100, "h-q bang"), (int(T0 + BARMS + 100), "h-q bang"),
                        (int(T0 + BARMS + 200), "al-midi 57 100 1"), (int(T0 + BARMS + 500), "al-midi 57 0 1"),
                        (int(T0 + 2 * BARMS + 100), "h-q bang"), (int(T0 + 2 * BARMS + 150), "h-n bang"),
                        (int(T0 + 3 * BARMS - 750), "aux 1"), (int(T0 + 3 * BARMS + 250), "al-midi 62 100 1"),
                        (int(T0 + 3 * BARMS + 600), "al-midi 62 0 1"), (int(T0 + 3 * BARMS + 900), "aux 0"),
                        (int(T0 + 4 * BARMS - 100), "h-n bang"), (int(T0 + 4 * BARMS + 100), "notesRaw 77 100"),
                        (int(T0 + 4 * BARMS + 200), "h-q bang")]
    log, _ = H.run(ev, (T0 + 4 * BARMS + 400) / 1000, d=d, keep=True, extra=lq)
    st = [l.split()[-1] for l in log.splitlines() if l.startswith("ST")]
    nt = [" ".join(l.split()[1:3]) for l in log.splitlines() if l.startswith("NOTES")]
    check("loop: armed till the bar, first pass, overdub, a press plays", st == ["5", "1", "3", "2"],
          "states " + " ".join(st) + " (5 armed, 1 first pass, 3 overdub, 2 play)")
    check("loop: aux held erases, what is played meanwhile replaces it", nt == ["57 57", "62 62"],
          f"notes before {nt[:1]}, after {nt[1:2]}")
    # a free loop starts on its first note (not on the bar line)
    ev = solo("sub") + [(30, "al-sel-sub bang"), (31, f"al-set {M.S('sub', None, 'LpLen')} {(1 + 0.5) / 7}"), START,
                        (1000, "notesRaw 77 100"), (1700, "al-midi 57 100 1"), (1800, "h-q bang")]

    def fq(c):
        c.c(c.ch(c.obj("r h-q", 900, 700), "expr allps[1]*1000 + allp0[1]"), 0, c.obj("print FR", 900, 760), 0)
    log, _ = H.run(ev, 2, d=d, keep=True, extra=fq)
    fr = [float(l.split()[-1]) for l in log.splitlines() if l.startswith("FR")]
    p0 = fr[0] - 1000 if fr else -1
    # (a free loop counts on its own clock - a tick each FREE_MS from the start: the note at 1700 ms)
    check("loop: free starts on the first note", fr and fr[0] >= 1000 and abs(p0 - 1700 / M.FREE_MS) < 3,
          f"state {int(fr[0] // 1000) if fr else '-'}, from tick {p0:.0f} of its own clock (the note: {1700 / M.FREE_MS:.0f})")

    # ---- a tapped rhythm: aux + top D# with lane 1 shown, three notes at steps 0, 3 and 5 of the cycle (8 steps of a
    # 16th): it becomes the lane's pattern - those gaps (3 2 3), and then 3 hits a cycle (2 cycles: 6)
    ev = solo("perc1") + [(30, "al-sel-perc1 bang"), (40, f"al-set {M.S('perc1', None, 'Steps')} {6 / 14}"),
                          (41, f"al-set {M.S('perc1', None, 'Rate')} {(3 + 0.5) / 6}"),
                          (43, f"al-set {M.S('perc1', None, 'Phase')} 0.01"), START,
                          (1000, "aux 1"), (1008, "notesRaw 78 100"), (1010, "notesRaw 78 100"), (1020, "aux 0")]
    step = 60000 / (84 * 4)
    ev += [(1030 + int(st * step), "al-note 3 60 0.8") for st in (0, 3, 5)]
    t_end = 1010 + 8 * step + 300
    ev += [(int(t_end) - 200, "aux 1"), (int(t_end) - 190, "notesRaw 78 100"), (int(t_end) - 180, "aux 0")]
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

    # ---- a piece keeps its loops (loops.txt), even on a fresh install (no pieces.txt, no loops.txt: each file is
    # filled out to all its slots when it loads, so piece 3 saves to piece 3's lines): a loop recorded, saved with
    # piece 3, cleared - silent - then piece 3 loaded: it plays again
    import shutil as _sh
    dl = d.rstrip("/") + "-loops"
    _sh.rmtree(dl, ignore_errors=True)
    _sh.copytree(d, dl)
    for f in ("loops.txt", "pieces.txt"):
        os.remove(os.path.join(dl, f))
    ev = [(50, f"al-set {M.S('g', None, 'Piece')} {(2 + 0.5) / 8}"), (200, "notesRaw 72 100"), (210, "notesRaw 72 0"),
          (998, "notesRaw 77 100"), (999, "notesRaw 77 0"), (1000, "notesRaw 77 100"), (1001, "notesRaw 77 0"),
          (1010, "al-midi 45 100 1"), (1300, "al-midi 45 0 1"), (1600, "al-midi 52 90 1"), (1900, "al-midi 52 0 1"),
          (3800, "notesRaw 77 100"), (3801, "notesRaw 77 0"), (3810, "notesRaw 77 100"), (3811, "notesRaw 77 0"),
          (6300, "al-psave bang"), (6600, "al-loopclear bang"), (7000, "h-mark B"), (9000, "h-mark C"),
          (9100, "al-pload bang"), (13000, "h-mark D")]

    def marks(c):
        c.c(c.obj("r h-mark", 900, 700), 0, c.obj("print MARK", 900, 730), 0)
    log, _ = H.run(ev, 13.2, d=dl, keep=True, prints=("al-in-drone",), extra=marks)
    cur, seen = "start", {}
    for l in log.splitlines():
        if l.startswith("MARK"):
            cur = l.split()[-1]
        elif l.startswith("al-in-drone"):
            seen[cur] = seen.get(cur, 0) + 1
    lines = [l for l in open(os.path.join(dl, "loops.txt")).read().split("\n") if l.strip()]
    kept = len(lines) == 56 and lines[14].split()[:3] == ["2", "96", "4"]
    check("a piece keeps its loops (fresh install too)", kept and seen.get("B", 0) == 0 and seen.get("C", 0) >= 4,
          f"loops.txt line 15: {lines[14][:24] if len(lines) > 14 else '-'}; notes after clearing {seen.get('B', 0)}, "
          f"after loading {seen.get('C', 0)}")

    # an older pieces.txt (made with ';' at each line's end - Pd read a line and an empty one - and written back so,
    # 16 lines) with a piece saved in slot 4 (line 3, as the older patch did): loaded, it is made 8 lines, the piece still slot 4 - saving piece 2 keeps it there
    old = ["-1", "", "-1", " ".join(["0.5"] * features_piece_len()), "-1", "", "-1", "", "-1", "", "-1", "", "-1", "",
           "-1", ""]
    open(os.path.join(dl, "pieces.txt"), "w").write("".join(l + "\n" for l in old))      # (as Pd wrote it)
    H.run([(50, f"al-set {M.S('g', None, 'Piece')} {(1 + 0.5) / 8}"), (300, "al-psave bang")], 0.6, d=dl, keep=True)
    pl = open(os.path.join(dl, "pieces.txt")).read().split("\n")
    pl = pl[:-1] if pl and pl[-1] == "" else pl
    lens = [len(l.split()) for l in pl]
    check("an older pieces.txt keeps its slots", len(pl) == 8 and lens[3] == features_piece_len() and
          lens[1] == features_piece_len() and lens[0] == 1, f"{len(pl)} lines, fields {lens}")

    # a saves.txt from before the SHAPE page (each line shorter by its slots): a snapshot there still loads - its
    # Volume comes back - and saved again it is written at the full length, the SHAPE knobs at their defaults
    import features as _F
    vol, added = M.S("g", None, "Volume"), M.NSLOTS - M.OLD_NSLOTS
    # (the oldest layout: before SHAPE and NoteOut)
    oldsnap = [f"{p.default:g}" for _, p in M.SLOTS[:M.OLD_NSLOTS]] + ["0"] * (_F.SNAP - M.NSLOTS)
    oldsnap[vol] = "0.3"
    open(os.path.join(dl, "saves.txt"), "w").write(" ".join(oldsnap) + "\n" + "-1\n" * (_F.SCRATCH + 1))
    H.run([(40, f"al-set {M.S('g', None, 'Morph')} 0"), (100, "notesRaw 82 100"), (120, "notesRaw 60 100"),
           (140, "notesRaw 60 0"), (300, "aux 1"), (320, "notesRaw 60 100"), (340, "notesRaw 60 0"), (360, "aux 0"),
           (380, "notesRaw 82 0")], 0.7, d=dl, keep=True)
    sv = open(os.path.join(dl, "saves.txt")).read().split("\n")[0].split()
    ok = len(sv) == _F.SNAP and abs(float(sv[vol]) - 0.3) < 1e-3 and \
        all(abs(float(sv[M.OLD_NSLOTS + i]) - p.default) < 1e-3 for i, p in enumerate(M.SHAPE))
    # (and a line from between: with SHAPE, before NoteOut - one field short)
    mid = [f"{p.default:g}" for _, p in M.SLOTS[:M.SLOT_HISTORY[1]]] + ["0"] * (_F.SNAP - M.NSLOTS)
    mid[vol] = "0.4"
    open(os.path.join(dl, "saves.txt"), "w").write(" ".join(mid) + "\n" + "-1\n" * (_F.SCRATCH + 1))
    H.run([(40, f"al-set {M.S('g', None, 'Morph')} 0"), (100, "notesRaw 82 100"), (120, "notesRaw 60 100"),
           (140, "notesRaw 60 0"), (300, "aux 1"), (320, "notesRaw 60 100"), (340, "notesRaw 60 0"), (360, "aux 0"),
           (380, "notesRaw 82 0")], 0.7, d=dl, keep=True)
    sv2 = open(os.path.join(dl, "saves.txt")).read().split("\n")[0].split()
    ok = ok and len(sv2) == _F.SNAP and abs(float(sv2[vol]) - 0.4) < 1e-3
    check("an older saves.txt still loads (SHAPE added)", ok,
          f"{len(sv)} fields (of {_F.SNAP}; older {_F.SNAP - added}), Volume {sv[vol] if len(sv) > vol else '-'}")

    # a saves.txt from before the engine change (596 slots: the layout recorded in layout_v2.json): a pad on choir
    # (its four values) and the sub on pulse - loaded and saved again: the pad on voice from glottal pulses with
    # choir's vowel, drift and breath; the sub still on pulse (1 of 7 now)
    import json as _json
    lay2 = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "layout_v2.json")))
    old = [f"{v:g}" for v in lay2["defaults"]] + ["0"] * (_F.SNAP - M.NSLOTS)
    pe_, se_ = M.S("pad", None, "Engine"), M.S("sub", None, "Engine")
    st_ = [M.S("pad", "string", p.key) for p in dict(M.engines("pad"))["string"]]
    old[pe_], old[se_] = f"{11.5 / 16:g}", f"{2.5 / 4:g}"
    for sl, v in zip(st_, ("0.8", "0.7", "0.2", "0.6")):
        old[sl] = v
    open(os.path.join(dl, "saves.txt"), "w").write(" ".join(old) + "\n" + "-1\n" * (_F.SCRATCH + 1))
    H.run([(40, f"al-set {M.S('g', None, 'Morph')} 0"), (100, "notesRaw 82 100"), (120, "notesRaw 60 100"),
           (140, "notesRaw 60 0"), (300, "aux 1"), (320, "notesRaw 60 100"), (340, "notesRaw 60 0"), (360, "aux 0"),
           (380, "notesRaw 82 0")], 0.7, d=dl, keep=True)
    sv3 = [float(x) for x in open(os.path.join(dl, "saves.txt")).read().split("\n")[0].split()]
    vo_ = lambda k: sv3[M.S("pad", "voice", k)]
    names_p, names_s = [e for e, _ in M.engines("pad")], [e for e, _ in M.engines("sub")]
    pad_e, sub_e = names_p[min(15, int(sv3[pe_] * 16))], names_s[min(6, int(sv3[se_] * 7))]
    cl_n = [e for e, _ in M.engines("cloud")]
    cl_e = cl_n[min(len(cl_n) - 1, int(sv3[M.S("cloud", None, "Engine")] * len(cl_n)))]
    ok = (len(sv3) == _F.SNAP and pad_e == "voice" and sub_e == "pulse" and cl_e == "grains" and abs(vo_("Source") - 1) < 1e-3 and
          abs(vo_("Vowel") - 0.8) < 1e-3 and abs(vo_("Motion") - 0.7) < 1e-3 and abs(vo_("Breath") - 0.6) < 1e-3)
    check("an older save: choir becomes voice, the sub keeps its engine", ok,
          f"pad {pad_e} (Source {vo_('Source'):g}, Vowel {vo_('Vowel'):g}, Motion {vo_('Motion'):g}, "
          f"Breath {vo_('Breath'):g}), sub {sub_e}, cloud {cl_e}")

    # a save from before AAFilt (and Lock): 626 slots - the cloud on delay, the layers' latch and in as saved. Loaded
    # and saved again: the cloud still on delay, AAFilt and Lock at their defaults, the latch and in in their places
    h626 = M.SLOT_HISTORY[4]
    nl_ = len(M.LAYERS)
    l626 = [f"{p.default:g}" for _, p in M.SLOTS[:h626]] + ["0"] * (_F.SNAP - M.NSLOTS)
    ce_ = M.S("cloud", None, "Engine")
    l626[ce_] = f"{2.5 / 3:g}"
    latch_ = ["0", "1"] + ["0"] * (nl_ - 2)
    in_ = ["1", "0"] + ["1"] * (nl_ - 2)
    l626[h626:h626 + 2 * nl_] = latch_ + in_
    open(os.path.join(dl, "saves.txt"), "w").write(" ".join(l626) + "\n" + "-1\n" * (_F.SCRATCH + 1))
    H.run([(40, f"al-set {M.S('g', None, 'Morph')} 0"), (100, "notesRaw 82 100"), (120, "notesRaw 60 100"),
           (140, "notesRaw 60 0"), (300, "aux 1"), (320, "notesRaw 60 100"), (340, "notesRaw 60 0"), (360, "aux 0"),
           (380, "notesRaw 82 0")], 0.7, d=dl, keep=True)
    sv4 = open(os.path.join(dl, "saves.txt")).read().split("\n")[0].split()
    cl4 = cl_n[min(len(cl_n) - 1, int(float(sv4[ce_]) * len(cl_n)))]
    aa_ = M.S("cloud", "delay", "AAFilt")
    lk_ = [M.S(L, None, "Lock") for L in M.NOTE_LAYERS]
    ok = (len(sv4) == _F.SNAP and cl4 == "delay" and abs(float(sv4[aa_]) - M.SLOTS[aa_][1].default) < 1e-3 and
          all(abs(float(sv4[k]) - M.SLOTS[k][1].default) < 1e-3 for k in lk_) and
          sv4[M.NSLOTS:M.NSLOTS + 2 * nl_] == latch_ + in_)
    check("a save from before AAFilt loads in place", ok,
          f"cloud {cl4}, AAFilt {sv4[aa_]}, latch / in {' '.join(sv4[M.NSLOTS:M.NSLOTS + 2 * nl_])}")

    # ... and the web editor reads that loops.txt (the loop: 4 events, playing) and writes it back the same
    import shutil as _sh2
    if _sh2.which("node"):
        import json as _js
        import subprocess as _sp
        import planner as _pl
        open(os.path.join(dl, "tl.js"), "w").write("const D = " + _js.dumps(_pl.data()) + ";\n" + _pl.CORE + r"""
const fs = require("fs"), t = fs.readFileSync(process.argv[2] + "/loops.txt", "utf8");
const a = C.parseLoops(t), b = C.parseLoops(C.write(a)), lp = C.loop(a[14]);
console.log(JSON.stringify({ kind: C.kindOf(t), n: lp.n, state: lp.state, bars: lp.len / C.Y.bar, same: JSON.stringify(a) === JSON.stringify(b) }));
""")
        o = _js.loads(_sp.run(["node", os.path.join(dl, "tl.js"), dl], capture_output=True, text=True).stdout)
        check("web editor: reads and writes loops.txt", o == dict(kind="loops", n=4, state=2, bars=1, same=True), str(o))

    # ---- the web editor (planner.py) reads what the patch saves and writes what it loads: Pd saves its defaults (a
    # piece, a snapshot) - the page's own defaults must be them; the page edits the piece and writes pieces.txt - Pd
    # loads it and saves it again, unchanged (but the SECTN knobs, which show the roadmap's first section)
    import shutil
    import json
    import subprocess
    if shutil.which("node"):
        import planner
        dw = d.rstrip("/") + "-web"            # (a copy of the build: its pieces.txt and saves.txt its own)
        shutil.rmtree(dw, ignore_errors=True)
        shutil.copytree(d, dw)
        for f in ("pieces.txt", "saves.txt"):
            open(os.path.join(dw, f), "w").write("-1\n" * (8 if f == "pieces.txt" else 18))
        open(os.path.join(dw, "roadmap.txt"), "w").write("")       # (no roadmap left by the checks above)
        H.run([(100, "al-psave bang"), (200, "al-save bang")], 0.5, d=dw, keep=True)
        core = "const D = " + json.dumps(planner.data()) + ";\n" + planner.CORE + r"""
const fs = require("fs"), dir = process.argv[2], step = process.argv[3];
const near = (a, b, skip) => a.map((v, i) => [i, v, b[i]]).filter(([i, v, w]) => !skip.includes(i) && Math.abs(v - w) > 1e-5);
const li = n => D.layers.findIndex(l => l.id === n);
if (step === "1") {
  const p = C.parse(fs.readFileSync(dir + "/pieces.txt", "utf8"), C.Y.piece), s = C.parse(fs.readFileSync(dir + "/saves.txt", "utf8"), C.Y.snap);
  const dp = near(p[0], C.defaults("piece"), []), ds = near(s[0], C.defaults("snap"), []);
  const r = p[0];
  C.setNumber(D.tempo, r, 120);
  C.setIndex(D.layers[li("pad")].eng, r, D.layers[li("pad")].engines.indexOf("fm"));
  r[C.Y.inn + li("drone")] = 0; r[C.Y.inn + li("perc2")] = 1; r[C.Y.latch + li("sub")] = 0; r[C.Y.tap + 3 * 16 + 5] = 1;
  C.setIndex(D.slots.findIndex(x => x.L === "perc1" && x.n === "Target" && x.e === null), r, 2);
  r[C.favAt(li("pad"), C.optIndex(D.layers[li("pad")].eng, r), 3)] = C.targets(r, li("pad"))[4];
  C.setRoad(r, [{bars: 8, story: 2, mask: 7, role: 0}, {bars: 16, story: 3, mask: 255, role: 4}]);
  fs.writeFileSync(dir + "/pieces.txt", C.write(p)); fs.writeFileSync(dir + "/edited.json", JSON.stringify(r));
  console.log(JSON.stringify({ pieces: p.length, saves: s.length, dp: dp.length, ds: ds.length }));
} else {
  const a = JSON.parse(fs.readFileSync(dir + "/edited.json", "utf8"));
  const b = C.parse(fs.readFileSync(dir + "/pieces.txt", "utf8"), C.Y.piece)[0];
  console.log(JSON.stringify({ diff: b ? near(a, b, [__SECTN__]).length : -1 }));
}
""".replace("__SECTN__", ", ".join(str(M.S("g", None, k)) for k in ("Sect", "SBars", "SStory", "SRole")))
        open(os.path.join(dw, "t.js"), "w").write(core)
        o1 = json.loads(subprocess.run(["node", os.path.join(dw, "t.js"), dw, "1"], capture_output=True, text=True).stdout)
        H.run([(300, "al-pload bang"), (2500, "al-psave bang")], 3, d=dw, keep=True)
        o2 = json.loads(subprocess.run(["node", os.path.join(dw, "t.js"), dw, "2"], capture_output=True, text=True).stdout)
        check("web editor: reads the patch's files, its defaults are the patch's", o1 == dict(pieces=8, saves=18, dp=0, ds=0), str(o1))
        check("web editor: a piece it edits loads on the Organelle as edited", o2["diff"] == 0,
              f"{o2['diff']} values differ after Pd loaded and saved it again")
    else:
        print("(no node: the web editor's checks skipped)")

    # ---- only Pd's core objects: nothing from 'extra' (sigmund~, bonk~ ...), which some installs leave out
    import glob as _glob
    extra = ("sigmund~", "bonk~", "fiddle~", "bob~", "choice", "loop~", "lrshift~", "pique", "pd~", "stdout")
    found = sorted({w for f in _glob.glob(os.path.join(d, "*.pd")) for ln in open(f)
                    for w in ln.replace(";", " ").split()[4:5] if w in extra})
    check("only Pd's core objects (nothing from extra)", not found, ", ".join(found) or "none")

    # ... and nothing newer than the Organelle's Pd: a signal into [lop~] / [hip~] / [bp~]'s cutoff is Pd 0.54's
    # (older, the connection fails without a word and the filter sits closed - silence); dsp.lop does it instead
    sigcut = []
    for f in _glob.glob(os.path.join(d, "*.pd")):
        objs = [[]]
        for ln in open(f).read().split(";\n"):
            ln = ln.strip()
            if ln.startswith("#N canvas"):
                objs.append([])
            elif ln.startswith("#X restore"):
                objs.pop()
                objs[-1].append("subpatch")
            elif ln.startswith(("#X obj", "#X msg", "#X text", "#X floatatom", "#X symbolatom", "#X array")):
                w = ln.split()
                objs[-1].append(" ".join(w[4:]) if w[1] == "obj" else w[1])
            elif ln.startswith("#X connect"):
                a_, _, b_, bi = map(int, ln.split()[2:6])
                o = objs[-1]
                if bi >= 1 and o[b_].split()[:1] in (["lop~"], ["hip~"], ["bp~"]) and o[a_].split()[0].endswith("~"):
                    sigcut.append(f"{os.path.basename(f)}: {o[a_]} -> {o[b_]}")
    check("no signal cutoffs into lop~ / hip~ / bp~ (the Organelle's Pd)", not sigcut, "; ".join(sigcut[:3]) or "none")
    # ... and [expr] only with functions of long standing (not the newer mtof / ftom / dbtorms ...: their arithmetic)
    import re as _re
    known = {"abs", "cos", "sin", "tan", "sqrt", "fmod", "if", "int", "max", "min", "pow", "random", "exp", "log",
             "atan", "atan2", "floor", "ceil", "rint", "log10"}
    used = set()
    for f in _glob.glob(os.path.join(d, "*.pd")):
        for ln in open(f).read().split(";\n"):
            w = ln.split()
            if len(w) > 4 and w[0] == "#X" and w[1] == "obj" and w[4] in ("expr", "expr~", "fexpr~"):
                used |= set(_re.findall(r"([A-Za-z_][A-Za-z_0-9]*)\s*\(", " ".join(w[5:])))
    check("expr: only long-standing functions (the Organelle's Pd)", used <= known, ", ".join(sorted(used - known)) or "none new")

    # ---- every engine of every layer sounds (one second each, in turn), and nothing in Pd complains
    for L in ("drone", "sub", "pad", "perc1"):
        names = [e for e, _ in M.engines(L)]
        ev = solo(L) + [START] + [(1000 + 1000 * i, f"al-set {M.S(L, None, 'Engine')} {M.engine_value(L, e)}")
                                  for i, e in enumerate(names)]
        log, a = H.run(ev, 1.2 + len(names), d=d, keep=True)
        lv = [H.rms_db(seg(a, 1.5 + i, 1.95 + i)) for i in range(len(names))]
        quiet = [f"{e} {v:.0f}" for e, v in zip(names, lv) if v < -50]
        check(f"every {M.kind(L)} engine sounds ({len(names)})", not quiet and not H.errors(log),
              f"quietest {min(lv):.0f} dB" + (f"; silent: {quiet}" if quiet else "") + (f"; {H.errors(log)[:1]}" if H.errors(log) else ""))

    # nothing piles up over a long session: the four lanes (the busiest messages) for 8 minutes - the last minutes'
    # CPU no more than the first's (a strike sent to every engine queued in the switched-off ones' [vline~]s: the CPU
    # doubled in 25 minutes)
    def clock(c):
        met = c.obj("metro 60000", 900, 700)
        c.c(c.obj("loadbang", 900, 680), 0, met, 0)
        rt = c.obj("realtime", 900, 730)
        tb = c.to(met, "t b b")
        c.c((tb, 0), 0, rt, 0)
        c.c((tb, 1), 0, rt, 1)
        c.c(rt, 0, c.obj("print RT", 900, 760), 0)
    lanes = [(20 + i, f"al-inset {i} {1 if L in M.LANES else 0}") for i, L in enumerate(M.LAYERS)]
    log, _ = H.run(lanes + [START], 8 * 60 + 1, d=d, keep=True, extra=clock, prints=())
    rts = [float(l.split()[-1]) for l in log.splitlines() if l.startswith("RT")][1:]
    first, last = sum(rts[:2]) / 2, sum(rts[-2:]) / 2
    check("nothing piles up over a long session", len(rts) >= 6 and last < first * 1.25,
          f"minutes 1-2: {first / 600:.2f} %, minutes 7-8: {last / 600:.2f} %")

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
