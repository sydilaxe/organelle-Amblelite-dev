"""The model: layers, engines, their parameters and the knob pages - one table, so a control is added or removed in
one place. Every parameter is a *slot*: a value 0..1 in the array alp (alp[slot]), sent on [s al-s<slot>] when it
changes. Engines read their slots as signals (dsp.prm) or as control values (alp[slot] in an [expr]).

Kinds of parameter:
  Param("Name", default)                      a plain 0..1 (shown as 0..100)
  Param("Name", default_index, opts=[...])    a choice: the knob is divided between the options
  Param("Name", default_value, lo=, hi=)      a number shown in its own units (tempo)
"""

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MODES = [("ionian", [0, 2, 4, 5, 7, 9, 11]), ("dorian", [0, 2, 3, 5, 7, 9, 10]),
         ("phrygian", [0, 1, 3, 5, 7, 8, 10]), ("lydian", [0, 2, 4, 6, 7, 9, 11]),
         ("mixolyd", [0, 2, 4, 5, 7, 9, 10]), ("aeolian", [0, 2, 3, 5, 7, 8, 10]),
         ("locrian", [0, 1, 3, 5, 6, 8, 10]), ("majpent", [0, 2, 4, 7, 9]), ("minpent", [0, 3, 5, 7, 10])]

# the chord story: chords as scale degrees (0 = the tonic chord), stacked in thirds within the mode.
# "modal" uses each mode's own characteristic move (dorian's IV, lydian's II, mixolydian's bVII ...)
MODAL = {"ionian": [0, 3, 5, 4], "dorian": [0, 3, 6, 4], "phrygian": [0, 1, 6, 1], "lydian": [0, 1, 4, 1],
         "mixolyd": [0, 6, 3, 0], "aeolian": [0, 5, 2, 6], "locrian": [0, 1, 5, 6], "majpent": [0, 3, 1, 4],
         "minpent": [0, 2, 4, 1]}
STORIES = [("modal", None), ("home", [0, 3, 0, 4]), ("descend", [0, 6, 5, 4]), ("circle", [0, 3, 6, 2, 5, 1, 4, 0]),
           ("pedal", [0, 1, 0, 6]), ("rise", [0, 1, 2, 3]), ("still", [0])]
STORY_LEN = 8          # a story is stored as 8 degrees (repeated to fill)


def story_degrees(story, mode):
    d = MODAL[mode] if story is None else story
    return [d[i % len(d)] for i in range(STORY_LEN)], len(d)


class Param:
    def __init__(self, name, default=0.5, opts=None, lo=None, hi=None):
        assert len(name) <= 6, name
        self.name, self.opts, self.lo, self.hi = name, opts, lo, hi
        if opts:
            self.default = (default + 0.5) / len(opts)       # the middle of the option's share of the knob
        elif lo is not None:
            self.default = (default - lo) / (hi - lo)
        else:
            self.default = default


OCTAVES = ["-3", "-2", "-1", "0", "+1", "+2", "+3"]
ARTIC = ["artic", "legato", "porta", "slide"]
ONOFF = ["off", "on"]
RATES = ["1/4", "1/8", "1/16", "1/32"]
RATE_TICKS = [8, 4, 2, 1]         # the clock runs in 32nds
BARS = ["manual", "1", "2", "4", "8", "16"]
BAR_N = [0, 1, 2, 4, 8, 16]
SUBMODES = ["pedal", "root"]


OCT_DEFAULT = dict(drone=2, sub=1, pad=3, perc=4)      # -1, -2, 0, +1 octaves


def layer_controls(layer, engines=()):
    perc = layer == "perc"
    eng = Param("Engine", 0, opts=list(engines))
    common = [eng, Param("Level", 0.5), Param("Cutoff", 1.0), Param("Reso", 0.1)]
    if perc:
        return [("LAYER", common),
                ("HIT", [Param("Decay", 0.45), Param("Velo", 0.5), Param("Octave", OCT_DEFAULT[layer], opts=OCTAVES),
                         Param("Spread", 0.6)]),
                ("RHYTHM", [Param("Hits", 5, lo=1, hi=16), Param("Steps", 8, lo=2, hi=16),
                            Param("Rotate", 0, lo=0, hi=15), Param("Rate", 2, opts=RATES)])]
    return [("LAYER", common),
            ("ENV", [Param("Attack", 0.45), Param("Decay", 0.6), Param("Sustn", 0.85), Param("Releas", 0.55)]),
            ("PLAY", [Param("Artic", 2, opts=ARTIC), Param("Glide", 0.45), Param("Octave", OCT_DEFAULT[layer], opts=OCTAVES),
                      Param("Pan", 0.5)])]


# ---- engines: (name, [Param ...]); the DSP of each is in eng_<layer>.py under the same name
WAVE_TABLES = ["amble", "basic", "reson", "pulse", "formnt", "harmon", "mini"]

ENGINES = {
    "drone": [
        ("analog", [Param("WaveA", 0.67), Param("WaveB", 0.67), Param("Intvl", 0, opts=["unison", "5th", "oct", "-oct", "4th"]),
                    Param("Detune", 0.35), Param("XMod", 0.0), Param("Ring", 0.0), Param("Sub", 0.3), Param("Mix", 0.5)]),
        ("fm", [Param("Ratio", 1, opts=["0.5", "1", "1.5", "2", "3", "3.5", "4", "5", "7"]), Param("Fine", 0.5),
                Param("Index", 0.35), Param("Fdbk", 0.0), Param("Motion", 0.3), Param("MoRate", 0.3)]),
        ("spectr", [Param("Upper", 0.5), Param("Drift", 0.5), Param("DrRate", 0.4), Param("OddEv", 0.5),
                    Param("Tilt", 0.5), Param("Strtch", 0.0)]),
    ],
    "sub": [
        ("sine", [Param("Harm", 0.0), Param("Body", 0.5)]),
        ("warm", [Param("Octave", 0.5), Param("Body", 0.5)]),
        ("pulse", [Param("Width", 0.5), Param("Body", 0.5)]),
        ("fm", [Param("Ratio", 1, opts=["0.5", "1", "1.5", "2", "3"]), Param("Index", 0.3), Param("Fdbk", 0.0),
                Param("Growl", 0.3)]),
    ],
    "pad": [
        ("sine", [Param("Harm", 0.0), Param("Slope", 0.5), Param("OddEv", 0.5), Param("Count", 6, opts=[str(n) for n in range(2, 9)]),
                  Param("Chorus", 0.0)]),
        ("fm", [Param("Ratio", 1, opts=["0.5", "1", "1.5", "2", "3", "3.5", "4", "5", "7"]), Param("Fine", 0.5),
                Param("Index", 0.3), Param("Fdbk", 0.0), Param("EnvAmt", 0.4), Param("EnvDec", 0.5)]),
        ("saws", [Param("Detune", 0.4), Param("Spread", 0.6), Param("Centre", 0.6)]),
        ("pwm", [Param("Width", 0.5), Param("Depth", 0.4), Param("Rate", 0.3), Param("Spread", 0.6)]),
        ("wave", [Param("Table", 0, opts=WAVE_TABLES), Param("Pos", 0.3), Param("Mode", 1, opts=["8bit", "smooth"]),
                  Param("Shimr", 0.0), Param("Detune", 0.3)]),
    ],
    "perc": [
        ("blip", [Param("Cutoff", 0.5), Param("Flick", 0.5), Param("FlTime", 0.3), Param("Reso", 0.4),
                  Param("Sub", 0.5), Param("FEnv", 0.5)]),
        ("lpg", [Param("Fold", 0.5), Param("FoldDc", 0.5), Param("Open", 0.5), Param("Reso", 0.2), Param("Vactrl", 0.5)]),
        ("bowl", [Param("Hard", 0.5), Param("Beat", 0.5), Param("Strtch", 0.0), Param("Strike", 0.5)]),
        ("wood", [Param("Mallet", 0.5), Param("Matrl", 0.0), Param("Knock", 0.5)]),
        ("metal", [Param("Bright", 0.5), Param("Beat", 0.5), Param("TremR", 0.5), Param("TremD", 0.4)]),
    ],
}
LAYERS = ["drone", "sub", "pad", "perc"]
LAYER_LABEL = {"drone": "DRONE", "sub": "SUB", "pad": "PADS", "perc": "PERC"}
VOICES = {"drone": 1, "sub": 1, "pad": 4, "perc": 6}

GLOBAL_PAGES = [("MAIN", [Param("Tempo", 84, lo=30, hi=200), Param("Key", 0, opts=NOTE_NAMES),
                          Param("Mode", 1, opts=[m for m, _ in MODES]), Param("Volume", 0.55)]),
                ("STORY", [Param("Story", 0, opts=[n for n, _ in STORIES]), Param("Bars", 3, opts=BARS),
                           Param("SubTo", 1, opts=SUBMODES), Param("Voicng", 0.4)]),
                ("SYNC", [Param("Sync", 0, opts=["int", "ext"]), Param("ClkOut", 1, opts=ONOFF)])]

# ---- slots
SLOTS = []              # [(key, Param)]
SLOT = {}               # key -> slot index; keys: ("g", name), (layer, None, name), (layer, engine, name)


def _add(key, p):
    SLOT[key] = len(SLOTS)
    SLOTS.append((key, p))


for _, ps in GLOBAL_PAGES:
    for p in ps:
        _add(("g", None, p.name), p)
LAYER_PAGES = {}
for L in LAYERS:
    LAYER_PAGES[L] = layer_controls(L, [e for e, _ in ENGINES[L]])
    for _, ps in LAYER_PAGES[L]:
        for p in ps:
            _add((L, None, p.name), p)
    for e, ps in ENGINES[L]:
        for p in ps:
            _add((L, e, p.name), p)
NSLOTS = len(SLOTS)


def S(layer, engine, name):
    """a slot by name: S('g', None, 'Tempo'), S('pad', None, 'Cutoff'), S('pad', 'fm', 'Index')"""
    return SLOT[(layer, engine, name)]


def pages(layer, engine):
    """the knob pages of a layer with an engine: its layer pages, then the engine's parameters 4 a page"""
    out = [(n, [S(layer, None, p.name) for p in ps]) for n, ps in LAYER_PAGES[layer]]
    eps = dict(ENGINES[layer])[engine]
    for k in range(0, len(eps), 4):
        chunk = [S(layer, engine, p.name) for p in eps[k:k + 4]]
        out.append((f"{engine.upper()} {k // 4 + 1}", chunk + [-1] * (4 - len(chunk))))
    return out


MAXPAGES = max(len(pages(L, e)) for L in LAYERS for e, _ in ENGINES[L])
MAXENG = max(len(ENGINES[L]) for L in LAYERS)
GLOBAL_LAYER = len(LAYERS)          # the "layer" index the MAIN / STORY pages use


def knob_table():
    """alks[((layer*MAXENG + engine)*MAXPAGES + page)*4 + knob] = slot (-1 none); alnp[layer*MAXENG + engine] = pages;
    the global pages as layer GLOBAL_LAYER, engine 0"""
    ks = [-1] * ((len(LAYERS) + 1) * MAXENG * MAXPAGES * 4)
    np_ = [0] * ((len(LAYERS) + 1) * MAXENG)
    pnames = [""] * ((len(LAYERS) + 1) * MAXENG * MAXPAGES)
    for li, L in enumerate(LAYERS):
        for ei, (e, _) in enumerate(ENGINES[L]):
            pg = pages(L, e)
            np_[li * MAXENG + ei] = len(pg)
            for pi, (pn, sl) in enumerate(pg):
                pnames[(li * MAXENG + ei) * MAXPAGES + pi] = pn
                for k, s in enumerate(sl):
                    ks[((li * MAXENG + ei) * MAXPAGES + pi) * 4 + k] = s
    np_[GLOBAL_LAYER * MAXENG] = len(GLOBAL_PAGES)
    for pi, (pn, ps) in enumerate(GLOBAL_PAGES):
        pnames[(GLOBAL_LAYER * MAXENG) * MAXPAGES + pi] = pn
        for k, p in enumerate(ps):
            ks[((GLOBAL_LAYER * MAXENG) * MAXPAGES + pi) * 4 + k] = S("g", None, p.name)
    return ks, np_, pnames


def slot_meta():
    """per slot: n options (0 = plain, -1 = number), lo, hi, first line in the options text; and the texts"""
    n, lo, hi, ob, opts, names = [], [], [], [], [], []
    for key, p in SLOTS:
        names.append(p.name)
        if p.opts:
            n.append(len(p.opts))
            ob.append(len(opts))
            opts.extend(p.opts)
        elif p.lo is not None:
            n.append(-1)
            ob.append(0)
        else:
            n.append(0)
            ob.append(0)
        lo.append(p.lo if p.lo is not None else 0)
        hi.append(p.hi if p.hi is not None else 1)
    return n, lo, hi, ob, opts, names
