"""The KORG nanoKONTROL Studio and nanoKEY Studio, set up for Amble Lite: one design table per controller gives
  - the scene set for KORG KONTROL Editor (docs/controllers/AmbleLite.nktrl_st_set / .nanokey_st_set): load it in
    the editor and write it to the controller,
  - the patch's profile for it (controllers/nanoktl.txt, nanokey.txt: midi.PROFILES),
  - the web editor's MIDI tab (planner.py: the controls, their CCs and what they do).

The set files are KORG's own (from KONTROL Editor, tools/korg/factory.*): a header, then a block a scene - a name
and an 8-byte entry a control: MIDI channel (0-15; 0x10 the global channel), a type, the CC or note number. Only the
channels, the names and (the nanoKEY's pads) the channel are changed here; the CC numbers are the factory ones.

nanoKONTROL Studio: its five scenes on channels 11-15 (each scene its own channel, so the patch tells them apart,
and none clashes with the nanoKEY on channel 1 or its pads on 10). Each strip is a layer (drone, sub, pads, perc 1-4,
cloud); the scenes differ in what the knobs and sliders move. nanoKEY Studio: the keys and knobs on channel 1 (the
knobs: the page shown and the next), the pads on channel 10 (so they are not the keys' notes)."""
import os
import model as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "controllers")
LAYER_N = {L: i + 1 for i, L in enumerate(M.LAYERS)}           # (a profile names a layer by its number, 1-8)

# ---- nanoKONTROL Studio: the controls in the file's order (60 entries), with their factory CCs
KTL_KNOBS = list(range(13, 21))
KTL_SLIDERS = [2, 3, 4, 5, 6, 8, 9, 12]
KTL_SOLO = [29, 30, 31, 33, 34, 35, 36, 37]
KTL_MUTE = list(range(21, 29))
KTL_REC = list(range(38, 46))
KTL_SELECT = list(range(46, 54))
# (the transport's CCs in the file's order; the names are KORG's layout as best known - LastCC on the MIDI page
# shows what a button sends)
KTL_TRANSPORT = [(80, "Play"), (63, "Stop"), (81, "Rec"), (58, "Rew"), (59, "FF"), (54, "Cycle"), (62, "Button 62"),
                 (55, "Marker set"), (56, "Marker <"), (57, "Marker >"), (60, "Track <"), (61, "Track >")]
KTL_CONTROLS = ([("knob", f"Knob {i + 1}", cc) for i, cc in enumerate(KTL_KNOBS)]
                + [("slider", f"Slider {i + 1}", cc) for i, cc in enumerate(KTL_SLIDERS)]
                + [("button", f"S {i + 1}", cc) for i, cc in enumerate(KTL_SOLO)]
                + [("button", f"M {i + 1}", cc) for i, cc in enumerate(KTL_MUTE)]
                + [("button", f"R {i + 1}", cc) for i, cc in enumerate(KTL_REC)]
                + [("button", f"Select {i + 1}", cc) for i, cc in enumerate(KTL_SELECT)]
                + [("button", name, cc) for cc, name in KTL_TRANSPORT])
assert len(KTL_CONTROLS) == 60
KTL_FIRST_CH = 11


def _strips(knob, slider):
    """a scene: knob / slider of strip n (layer n) -> (action, arg); the buttons the same in every scene"""
    out = {}
    for n, L in enumerate(M.LAYERS, 1):
        out[f"Knob {n}"] = knob(L, n)
        out[f"Slider {n}"] = slider(L, n)
        out[f"S {n}"] = ("show", n)
        out[f"M {n}"] = ("toggle", n)
        if L in M.NOTE_LAYERS:
            out[f"R {n}"] = ("loopl", n)
        out[f"Select {n}"] = ("show", n)
    out.update({"Play": ("start", None), "Stop": ("stop", None), "Rec": ("loop", None), "Cycle": ("loopstop", None),
                "Rew": ("chordprev", None), "FF": ("chordnext", None), "Track <": ("pgprev", None),
                "Track >": ("pgnext", None), "Marker set": ("mix", None), "Marker <": ("play", None),
                "Marker >": ("pattern", None)})
    return out


def _rel(L):
    """the layer's tail: its release (drone, sub, pads), its decay (a lane); the cloud: its grains' size"""
    return f"{L}.Releas" if L in ("drone", "sub", "pad") else f"{L}.Decay" if M.kind(L) == "perc" else "cloud.grains.Size"


KTL_SCENES = [
    ("AL Mix", "levels on the sliders, each layer's filter on its knob",
     _strips(lambda L, n: ("param", f"{L}.Cutoff"), lambda L, n: ("level", n))),
    ("AL Tone", "each layer's engine: its first parameter on the knob, its second on the slider",
     _strips(lambda L, n: ("engp", n * 10 + 1), lambda L, n: ("engp", n * 10 + 2))),
    ("AL Move", "each layer's Evolve on the knob, its LFO 1 depth on the slider",
     _strips(lambda L, n: ("param", f"{L}.Evolve"), lambda L, n: ("param", f"{L}.L1Dep"))),
    ("AL Space", "each layer's resonance on the knob, its release (lanes: decay) on the slider",
     _strips(lambda L, n: ("param", f"{L}.Reso"), lambda L, n: ("param", _rel(L)))),
    ("AL Pages", "the knobs: the page shown and the next (as the Organelle's); levels on the sliders",
     _strips(lambda L, n: ("knob", n), lambda L, n: ("level", n))),
]

# ---- nanoKEY Studio: the knobs (factory CC 20-27, channel 1) and the 8 pads (their factory notes, moved to channel 10)
KEY_KNOBS = list(range(20, 28))
KEY_PADS = [43, 48, 50, 49, 36, 38, 42, 46]
KEY_PAD_CH = 10
KEY_CONTROLS = ([("knob", f"Knob {i + 1}", cc) for i, cc in enumerate(KEY_KNOBS)]
                + [("pad", f"Pad {i + 1}", n) for i, n in enumerate(KEY_PADS)])
KEY_SCENE = {**{f"Knob {k}": ("knob", k) for k in range(1, 9)},
             **{f"Pad {k}": ("toggle", k) for k in range(1, 6)},
             "Pad 6": ("startstop", None), "Pad 7": ("loop", None), "Pad 8": ("mix", None)}


def _line(kind, ch, num, act):
    a, arg = act
    tail = f" {arg}" if arg is not None else ""
    if kind == "pad":
        return f"note {ch} {num} {a}{tail};"
    return f"chcc {ch} {num} {a}{tail};"


def profile_ktl():
    lines = ["# Korg nanoKONTROL Studio with the Amble Lite set (docs/controllers/AmbleLite.nktrl_st_set): its five",
             "# scenes on channels 11-15. Each strip is a layer (drone, sub, pads, perc 1-4, cloud): S / Select show",
             "# it, M takes it in / out, R is its loop key. " + "; ".join(f"Scene {i + 1} {n}: {d}"
                                                                        for i, (n, d, _) in enumerate(KTL_SCENES))]
    for si, (_, _, design) in enumerate(KTL_SCENES):
        for kind, name, cc in KTL_CONTROLS:
            if name in design:
                lines.append(_line(kind, KTL_FIRST_CH + si, cc, design[name]))
    return lines


def profile_key():
    return (["# Korg nanoKEY Studio with the Amble Lite set (docs/controllers/AmbleLite.nanokey_st_set): the knobs",
             "# (channel 1) the page shown and the next; the pads (channel 10): layers 1-5 in / out, start / stop,",
             "# loop, MIX; the X-Y pad's CC 1 the breath",
             "chcc 1 1 breath;"]
            + [_line(kind, 1 if kind != "pad" else KEY_PAD_CH, num, KEY_SCENE[name])
               for kind, name, num in KEY_CONTROLS if name in KEY_SCENE])


# ---- the set files
def _name(b, at, text, n=12):
    raw = text.encode("ascii")[:n]
    b[at:at + n] = raw + b"\x00" * (n - len(raw))


def set_ktl():
    b = bytearray(open(os.path.join(HERE, "korg", "factory.nktrl_st_set"), "rb").read())
    size = 32 + 0x230
    for si, (name, _, _) in enumerate(KTL_SCENES):
        o = 32 + si * size
        assert b[o:o + 8] == b"1482ScnD", "not a nanoKONTROL Studio scene set"
        _name(b, o + 32, name)
        for e, (_, _, cc) in enumerate(KTL_CONTROLS):
            at = o + 48 + e * 8
            assert b[at + 2] == cc, (si, e, b[at + 2], cc)
            b[at] = KTL_FIRST_CH + si - 1
    return bytes(b)


def set_key():
    b = bytearray(open(os.path.join(HERE, "korg", "factory.nanokey_st_set"), "rb").read())
    size = 32 + 0xf0
    first = None
    for si in range(8):
        o = 32 + si * size
        assert b[o:o + 8] == b"1480ScnD", "not a nanoKEY Studio scene set"
        if first is None:
            first = bytes(b[o + 48:o + size])
        # every scene the same: scene 1's controls (knobs CC 20-27), its pads on channel 10
        b[o + 48:o + size] = first
        _name(b, o + 32, "Amble Lite")
        b[o + 48] = KEY_PAD_CH - 1                       # (the pads' channel)
        for e in range(2, 10):
            assert b[o + 48 + e * 8 + 2] == KEY_PADS[e - 2]
            b[o + 48 + e * 8] = KEY_PAD_CH - 1
        for e in range(11, 19):
            assert b[o + 48 + e * 8 + 2] == KEY_KNOBS[e - 11]
    return bytes(b)


def tables():
    """for the web editor's MIDI tab"""
    return dict(
        nanoktl=dict(name="nanoKONTROL Studio", scenes=[dict(name=n, about=d, ch=KTL_FIRST_CH + i,
                                                             map={k: list(v) for k, v in design.items()})
                                                        for i, (n, d, design) in enumerate(KTL_SCENES)],
                     controls=[dict(kind=k, name=n, num=cc) for k, n, cc in KTL_CONTROLS]),
        nanokey=dict(name="nanoKEY Studio", scenes=[dict(name="Amble Lite", about="the knobs: the page shown and the "
                                                         "next; the pads: layers in / out, start, loop, MIX", ch=1,
                                                         padch=KEY_PAD_CH, map={k: list(v) for k, v in KEY_SCENE.items()})],
                     controls=[dict(kind=k, name=n, num=num) for k, n, num in KEY_CONTROLS]))


def main():
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "AmbleLite.nktrl_st_set"), "wb").write(set_ktl())
    open(os.path.join(OUT, "AmbleLite.nanokey_st_set"), "wb").write(set_key())
    return OUT


if __name__ == "__main__":
    print(main())
