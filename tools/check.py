"""Offline checks in Pure Data: python3 check.py. Each check builds nothing new (one build, reused) and prints
PASS / FAIL with what it measured."""
import sys
import time
import numpy as np
import harness as H
import model as M

SR = 44100
MUTE = {"drone": 61, "sub": 63, "pad": 66, "perc": 68}
START = (200, "notesRaw 72 100")
FAILS = []


def solo(L, t=60):
    return [(t + i, f"notesRaw {MUTE[o]} 100") for i, o in enumerate(M.LAYERS) if o != L]


def seg(a, t0, t1):
    return a[int(t0 * SR):int(t1 * SR)]


def peak_hz(x, lo=20, hi=5000):
    m = x.mean(axis=1) if x.ndim == 2 else x
    w = np.hanning(len(m))
    sp = np.abs(np.fft.rfft(m * w))
    f = np.fft.rfftfreq(len(m), 1 / SR)
    k = (f > lo) & (f < hi)
    return f[k][np.argmax(sp[k])]


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
    log, a = H.run(solo("perc") + [START], 5, d=d, keep=True, prints=("al-perc-hit",))
    hits = sum(1 for l in log.splitlines() if l.startswith("al-perc-hit"))
    expect = 4.8 / (60 / 84 / 4) * 5 / 8
    check("percussion plays its Euclidean pattern", abs(hits - expect) <= 2, f"{hits} strikes ({expect:.0f} expected)")

    # the chord story: next chord changes the pads
    log, a = run(solo("pad") + [START, (2000, "notesRaw 76 100")], 4)
    h1, h2 = peak_hz(seg(a, 1.5, 2)), peak_hz(seg(a, 3.5, 4))
    check("next chord moves the pads", abs(h1 - h2) > 5, f"{h1:.0f} -> {h2:.0f} Hz")

    # Evolve: the pads' wave engine at full Evolve, fast pace - its brightness moves; at 0 (or the master at 0) it
    # holds still; and the same settings move the same way every time
    pe, pp = M.S("pad", None, "Evolve"), M.S("pad", None, "Pace")
    base = solo("pad") + [(50, f"al-set {M.S('pad', None, 'Engine')} 0.9"), (51, f"al-set {pp} 1"),
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

    # CPU: everything playing, offline speed vs real time (x86; the Organelle's CM3 is roughly 10-15x slower)
    t0 = time.time()
    run([START], 30)
    rt = (time.time() - t0) / 30
    check("CPU", rt < 0.08, f"{100 * rt:.1f} % of real time on this machine")
    print("\n" + ("all passed" if not FAILS else f"{len(FAILS)} failed: {', '.join(FAILS)}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
