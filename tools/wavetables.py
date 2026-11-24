"""The factory wavetable bank: written as WAV files into the patch's waves/factory/ folder at each build, from
harmonic recipes (no sampled data). Each frame is CYCLE samples with guard points around it (STRIDE = CYCLE + 3:
the last sample before, the first two after), so [tabread4~] interpolates cleanly across the cycle's end.

PPG- and Miniwave-style tables recreate a character (harmonic sweeps, stepped frames, 8-bit), not the original
ROM data, which is not openly licensed: those can be dropped into waves/ as WAVs (a later milestone)."""
import math
import os
import struct
import wave

CYCLE = 2048
STRIDE = CYCLE + 3
NH = 48            # harmonics in the band-limited recipes


def additive(amps, phases=None):
    out = [0.0] * CYCLE
    for n, amp in enumerate(amps, start=1):
        if not amp:
            continue
        ph = phases[n - 1] if phases else 0.0
        w = 2 * math.pi * n / CYCLE
        for i in range(CYCLE):
            out[i] += amp * math.sin(w * i + ph)
    return out


def norm(x):
    m = max(abs(v) for v in x) or 1.0
    return [v / m for v in x]


def amble_frames():
    A = {1: 1, 2: 0.25, 3: 0.4, 4: 0.08, 5: 0.22, 7: 0.15, 9: 0.1}
    B = {1: 0.6, 3: 0.15, 4: 0.35, 6: 0.3, 8: 0.38, 11: 0.25, 13: 0.2, 16: 0.12}
    return [additive([d.get(n, 0) for n in range(1, 17)]) for d in (A, B)]


def basic_frames():
    sine = additive([1])
    tri = additive([(8 / math.pi ** 2) * ((-1) ** ((n - 1) // 2)) / n ** 2 if n % 2 else 0 for n in range(1, NH + 1)])
    saw = additive([2 / (math.pi * n) * (-1) ** (n + 1) for n in range(1, NH + 1)])
    sq = additive([4 / (math.pi * n) if n % 2 else 0 for n in range(1, NH + 1)])
    return [sine, tri, saw, sq]


def reson_frames(k=16):
    """a saw-like body with a resonant peak walking up the harmonics (the PPG's resonant sweeps)"""
    out = []
    for f in range(k):
        c = 1.5 + 30 * (f / (k - 1)) ** 1.6
        out.append(additive([(1 / n) * (0.3 + 6 * math.exp(-((n - c) / 1.6) ** 2)) for n in range(1, NH + 1)]))
    return out


def pulse_frames(k=16):
    """pulse width 50 % -> 3 %, band-limited"""
    out = []
    for f in range(k):
        w = 0.5 - 0.47 * f / (k - 1)
        out.append(additive([math.sin(math.pi * n * w) / n for n in range(1, NH + 1)], [math.pi / 2] * NH))
    return out


def formant_frames(k=16):
    """two formant peaks moving apart (an 'ah' to an 'ee'), on a buzzy source"""
    out = []
    for f in range(k):
        t = f / (k - 1)
        f1, f2 = 3.5 - 1.5 * t, 5 + 14 * t
        out.append(additive([(1 / n ** 0.5) * (math.exp(-((n - f1) / 1.2) ** 2) + 0.7 * math.exp(-((n - f2) / 2) ** 2) + 0.02)
                             for n in range(1, NH + 1)]))
    return out


def harmon_frames(k=16):
    """drawbars pulled out one harmonic at a time (the PPG's organ-like steps)"""
    out = []
    for f in range(k):
        out.append(additive([(1 / n ** 0.6 if n <= f + 1 else 0) for n in range(1, NH + 1)]))
    return out


def mini_frames(k=16):
    """Miniwave-style: hard-synced sines (a slave ratio rising), drawn in time: raw, gritty edges"""
    out = []
    for f in range(k):
        r = 1 + f * 0.55
        out.append([math.sin(2 * math.pi * r * i / CYCLE) * (1 - i / CYCLE) for i in range(CYCLE)])
    return out


TABLES = [(name, [norm(fr) for fr in fn()], desc) for name, fn, desc in (
    ("amble", amble_frames, "Amble's glass: a soft body, then sparse high harmonics"),
    ("basic", basic_frames, "sine, triangle, saw, square"),
    ("reson", reson_frames, "PPG-style: a resonant peak sweeping up"),
    ("pulse", pulse_frames, "PPG-style: pulse width 50 % to 3 %"),
    ("formnt", formant_frames, "PPG-style: two formants moving apart"),
    ("harmon", harmon_frames, "PPG-style: harmonics added one by one"),
    ("mini", mini_frames, "Miniwave-style: synced sines, raw"),
)]


def write(folder):
    os.makedirs(folder, exist_ok=True)
    for name, frames, _ in TABLES:
        data = []
        for fr in frames:
            data += [fr[-1]] + fr + fr[:2]
        with wave.open(os.path.join(folder, f"{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32767)) for v in data))
