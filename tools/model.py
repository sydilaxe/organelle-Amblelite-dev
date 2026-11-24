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
# chord types for the library: 4 voices (semitones from the root), and the name shown after the root (QUALS)
CHORD_TYPES = {"maj": ([0, 4, 7, 14], 0), "min": ([0, 3, 7, 14], 1), "dim": ([0, 3, 6, 9], 2), "aug": ([0, 4, 8, 12], 3),
               "sus2": ([0, 2, 7, 12], 5), "sus4": ([0, 5, 7, 12], 6), "maj7": ([0, 4, 7, 11], 7),
               "m7": ([0, 3, 7, 10], 8), "7": ([0, 4, 7, 10], 9), "q4": ([0, 5, 10, 15], 10),
               "add2": ([0, 2, 4, 7], 11), "madd2": ([0, 2, 3, 7], 12), "6/9": ([0, 4, 9, 14], 13)}
TYPE_NAMES = list(CHORD_TYPES)
QUALS = ["", "m", "dim", "+", "sus", "sus2", "sus4", "maj7", "m7", "7", "4ths", "add2", "madd2", "6/9"]
# STORIES: ("name", "deg", [scale degrees]) - stacked thirds in the current mode (modal: each mode's own move);
#          ("name", "chr", [(semitones from the key, type)]) - the library: fixed chords, any mode
STORIES = [("modal", "deg", None), ("home", "deg", [0, 3, 0, 4]), ("descend", "deg", [0, 6, 5, 4]),
           ("circle", "deg", [0, 3, 6, 2, 5, 1, 4, 0]), ("pedal", "deg", [0, 1, 0, 6]), ("rise", "deg", [0, 1, 2, 3]),
           ("still", "deg", [0]),
           # ---- traditional
           ("axis", "chr", [(0, "maj"), (7, "maj"), (9, "min"), (5, "maj")]),
           ("canon", "chr", [(0, "maj"), (7, "maj"), (9, "min"), (4, "min"), (5, "maj"), (0, "maj"), (5, "maj"), (7, "maj")]),
           ("ii-V-I", "chr", [(2, "m7"), (7, "7"), (0, "maj7"), (0, "maj7")]),
           ("circle7", "chr", [(9, "m7"), (2, "m7"), (7, "7"), (0, "maj7")]),
           ("plagal", "chr", [(0, "maj"), (5, "maj")]),
           ("andalus", "chr", [(0, "min"), (10, "maj"), (8, "maj"), (7, "maj")]),
           ("epic", "chr", [(0, "min"), (8, "maj"), (3, "maj"), (10, "maj")]),
           ("minor4", "chr", [(0, "min"), (5, "min"), (10, "maj"), (3, "maj")]),
           # ---- modal vamps
           ("dorvamp", "chr", [(0, "m7"), (5, "7")]), ("mixvamp", "chr", [(0, "maj"), (10, "maj"), (5, "maj"), (0, "maj")]),
           ("lydfloat", "chr", [(0, "maj7"), (2, "maj"), (0, "maj7"), (11, "min")]),
           ("phrvamp", "chr", [(0, "min"), (1, "maj")]),
           ("aeolvmp", "chr", [(0, "min"), (10, "maj"), (8, "maj"), (10, "maj")]),
           # ---- ambient and new age: suspended, added tones, slow plagal and mediant moves, no pull to resolve
           ("float", "chr", [(0, "maj7"), (5, "maj7")]),                         # Ionian / Lydian floating
           ("gymno", "chr", [(5, "maj7"), (0, "maj7")]),                         # after Satie's Gymnopedie
           ("suspend", "chr", [(0, "sus2"), (7, "sus2"), (5, "sus2"), (0, "sus4")]),
           ("newage", "chr", [(0, "add2"), (4, "m7"), (5, "maj7"), (0, "6/9")]),
           ("still6", "chr", [(0, "6/9"), (9, "madd2"), (5, "6/9"), (7, "sus2")]),
           ("mediant", "chr", [(0, "maj"), (3, "maj"), (0, "maj"), (8, "maj")]),
           ("diamed", "chr", [(0, "maj"), (4, "min"), (0, "maj"), (9, "min")]),
           ("minimal", "chr", [(0, "min"), (8, "maj"), (5, "min"), (7, "sus4")]),   # a minimalist loop
           ("planing", "chr", [(0, "sus2"), (2, "sus2"), (3, "sus2"), (5, "sus2")]),
           ("sus", "chr", [(0, "sus2"), (0, "sus4"), (10, "sus2"), (5, "sus2")]),
           # ---- experimental: symmetrical cycles and non-tertian chords
           ("neoriem", "chr", [(0, "maj"), (0, "min"), (8, "maj"), (5, "min")]),     # P, L, R: one note moves
           ("hexaton", "chr", [(0, "maj"), (0, "min"), (8, "maj"), (8, "min"), (4, "maj"), (4, "min")]),
           ("thirds", "chr", [(0, "maj7"), (4, "maj7"), (8, "maj7")]),          # major-third cycle
           ("octaton", "chr", [(0, "maj"), (3, "maj"), (6, "maj"), (9, "maj")]),  # minor-third cycle
           ("tritone", "chr", [(0, "maj"), (6, "maj")]),
           ("quartal", "chr", [(0, "q4"), (2, "q4"), (5, "q4"), (7, "q4")]),
           ("wholetn", "chr", [(0, "aug"), (2, "aug"), (4, "aug"), (6, "aug")])]
STORY_LEN = 8          # a story is stored as 8 chords (repeated to fill)


def story_degrees(story, mode):
    d = MODAL[mode] if story is None else story
    return [d[i % len(d)] for i in range(STORY_LEN)], len(d)


def story_chords(chords):
    """a library story as (roots, type indices), STORY_LEN each, and its length"""
    return ([chords[i % len(chords)][0] for i in range(STORY_LEN)],
            [TYPE_NAMES.index(chords[i % len(chords)][1]) for i in range(STORY_LEN)], len(chords))


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
# rates in MIDI clocks (24 a beat): triplets included
RATES = ["1/4", "1/8", "1/8T", "1/16", "1/16T", "1/32"]
RATE_CLOCKS = [24, 12, 8, 6, 4, 3]
BARS = ["manual", "1", "2", "4", "8", "16"]
BAR_N = [0, 1, 2, 4, 8, 16]
SUBMODES = ["pedal", "root"]
PITCHES = ["up", "down", "updown", "root", "fifth", "scl up", "scl dn", "stack"]
PHASES = ["off", "16bar", "8bar", "4bar", "2bar", "1bar"]
PHASE_BARS = [0, 16, 8, 4, 2, 1]
COMPS = ["none", "drone", "sub", "pads"]

LANES = ["perc1", "perc2", "perc3", "perc4"]
OCT_DEFAULT = dict(drone=2, sub=1, pad=3, perc1=4, perc2=4, perc3=3, perc4=5)      # -1, -2, 0, +1 ...
# the lanes' defaults: a cascade that interlocks (engine, hits, steps, rotate, rate, pitch, phase, decay)
LANE_DEFAULT = dict(perc1=(3, 5, 8, 0, 3, 0, 0, 0.45), perc2=(4, 3, 8, 2, 1, 4, 0, 0.5),
                    perc3=(2, 2, 5, 0, 0, 3, 0, 0.75), perc4=(1, 7, 16, 0, 3, 2, 2, 0.4))


def kind(layer):
    """the engines a layer plays: the percussion lanes share theirs"""
    return "perc" if layer.startswith("perc") else layer


def layer_controls(layer, engines=()):
    perc = kind(layer) == "perc"
    d = LANE_DEFAULT.get(layer)
    eng = Param("Engine", d[0] if d else 0, opts=list(engines))
    common = [eng, Param("Level", 0.5), Param("Cutoff", 1.0), Param("Reso", 0.1)]
    evolve = ("EVOLVE", [Param("Evolve", 0.4), Param("Pace", 0.4), Param("EvSync", 0, opts=["free", "bars"])]
               + ([] if perc else [Param("Drift", 0.0)]))
    if perc:
        return [("LAYER", common),
                ("HIT", [Param("Decay", d[7]), Param("Velo", 0.5), Param("Octave", OCT_DEFAULT[layer], opts=OCTAVES),
                         Param("Pitch", d[5], opts=PITCHES)]),
                ("RHYTHM", [Param("Hits", d[1], lo=1, hi=16), Param("Steps", d[2], lo=2, hi=16),
                            Param("Rotate", d[3], lo=0, hi=15), Param("Rate", d[4], opts=RATES)]),
                ("MOTION", [Param("Phase", d[6], opts=PHASES), Param("Spread", 0.6), Param("Accent", 0.3)]), evolve]
    return [("LAYER", common),
            ("ENV", [Param("Attack", 0.45), Param("Decay", 0.6), Param("Sustn", 0.85), Param("Releas", 0.55)]),
            ("PLAY", [Param("Artic", 2, opts=ARTIC), Param("Glide", 0.45), Param("Octave", OCT_DEFAULT[layer], opts=OCTAVES),
                      Param("Pan", 0.5)]), evolve,
            ("GATE", [Param("Gate", 0, opts=ONOFF), Param("Hits", 3, lo=1, hi=16), Param("Steps", 8, lo=2, hi=16),
                      Param("Rotate", 0, lo=0, hi=15)]),
            ("GATE 2", [Param("Rate", 1, opts=RATES), Param("Length", 0.5), Param("Comp", 0, opts=COMPS),
                        Param("Accent", 0.3)])]


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
LAYERS = ["drone", "sub", "pad"] + LANES
LAYER_LABEL = {"drone": "DRONE", "sub": "SUB", "pad": "PADS", "perc1": "PERC1", "perc2": "PERC2", "perc3": "PERC3",
               "perc4": "PERC4"}
SHORT = {"drone": "Dr", "sub": "Sb", "pad": "Pd", "perc1": "P1", "perc2": "P2", "perc3": "P3", "perc4": "P4"}
VOICES = {"drone": 1, "sub": 1, "pad": 4, "perc1": 3, "perc2": 3, "perc3": 3, "perc4": 3}

GLOBAL_PAGES = [("MAIN", [Param("Tempo", 84, lo=30, hi=200), Param("Key", 0, opts=NOTE_NAMES),
                          Param("Mode", 1, opts=[m for m, _ in MODES]), Param("Volume", 0.55)]),
                ("STORY", [Param("Story", 0, opts=[n for n, _, _ in STORIES]), Param("Bars", 3, opts=BARS),
                           Param("SubTo", 1, opts=SUBMODES), Param("Voicng", 0.4)]),
                ("SYNC", [Param("Sync", 0, opts=["int", "ext"]), Param("ClkOut", 1, opts=ONOFF)]),
                ("PERFRM", [Param("Evolve", 1.0)])]
# the MIX view's pages: existing slots (layer, name)
MIX_PAGES = [("MIX 1", [("drone", "Level"), ("sub", "Level"), ("pad", "Level"), ("g", "Volume")]),
             ("MIX 2", [(L, "Level") for L in LANES])]

# ---- Evolve: what moves in each engine, and how far (a weight: the share of the knob's range at Evolve 100 %).
# ("Cutoff", None) is the layer's filter. Each target moves on two slow sines of its own (control.evolve).
EVOLVE = {
    ("drone", "analog"): [("WaveA", 0.6), ("WaveB", 0.6), ("XMod", 0.3), ("Mix", 0.5), (None, 0.25)],
    ("drone", "fm"): [("Index", 0.5), ("Fdbk", 0.3), ("Fine", 0.08), (None, 0.25)],
    ("drone", "spectr"): [("Upper", 0.5), ("Tilt", 0.4), ("OddEv", 0.5), (None, 0.2)],
    ("sub", "sine"): [("Harm", 0.3), ("Body", 0.3)],
    ("sub", "warm"): [("Octave", 0.4), ("Body", 0.3)],
    ("sub", "pulse"): [("Width", 0.5), ("Body", 0.3)],
    ("sub", "fm"): [("Index", 0.4), ("Growl", 0.3)],
    ("pad", "sine"): [("Harm", 0.5), ("Slope", 0.4), ("OddEv", 0.5), (None, 0.3)],
    ("pad", "fm"): [("Index", 0.5), ("Fdbk", 0.3), ("EnvAmt", 0.3), (None, 0.3)],
    ("pad", "saws"): [("Detune", 0.3), ("Spread", 0.4), ("Centre", 0.4), (None, 0.4)],
    ("pad", "pwm"): [("Width", 0.5), ("Depth", 0.3), ("Rate", 0.2), (None, 0.4)],
    ("pad", "wave"): [("Pos", 0.8), ("Shimr", 0.3), ("Detune", 0.3), (None, 0.3)],
    ("perc", "blip"): [("Cutoff", 0.5), ("Flick", 0.3), ("FEnv", 0.3)],
    ("perc", "lpg"): [("Fold", 0.5), ("Open", 0.5), ("Vactrl", 0.3)],
    ("perc", "bowl"): [("Hard", 0.5), ("Beat", 0.4), ("Strtch", 0.2)],
    ("perc", "wood"): [("Mallet", 0.5), ("Matrl", 0.4), ("Knock", 0.3)],
    ("perc", "metal"): [("Bright", 0.5), ("Beat", 0.4), ("TremD", 0.3)],
}
EVOLVE_MAX = max(len(v) for v in EVOLVE.values())


def engines(layer):
    return ENGINES[kind(layer)]

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
    LAYER_PAGES[L] = layer_controls(L, [e for e, _ in engines(L)])
    for _, ps in LAYER_PAGES[L]:
        for p in ps:
            _add((L, None, p.name), p)
    for e, ps in engines(L):
        for p in ps:
            _add((L, e, p.name), p)
NSLOTS = len(SLOTS)


def S(layer, engine, name):
    """a slot by name: S('g', None, 'Tempo'), S('pad', None, 'Cutoff'), S('pad', 'fm', 'Index')"""
    return SLOT[(layer, engine, name)]


def pages(layer, engine):
    """the knob pages of a layer with an engine: its layer pages, then the engine's parameters 4 a page"""
    out = [(n, [S(layer, None, p.name) for p in ps]) for n, ps in LAYER_PAGES[layer]]
    eps = dict(engines(layer))[engine]
    for k in range(0, len(eps), 4):
        chunk = [S(layer, engine, p.name) for p in eps[k:k + 4]]
        out.append((f"{engine.upper()} {k // 4 + 1}", chunk + [-1] * (4 - len(chunk))))
    return out


MAXPAGES = max(len(pages(L, e)) for L in LAYERS for e, _ in engines(L))
MAXENG = max(len(engines(L)) for L in LAYERS)
GLOBAL_LAYER = len(LAYERS)          # the "layer" index the MAIN / STORY pages use; + 1: the MIX pages


def knob_table():
    """alks[((layer*MAXENG + engine)*MAXPAGES + page)*4 + knob] = slot (-1 none); alnp[layer*MAXENG + engine] = pages;
    the global pages as layer GLOBAL_LAYER, engine 0"""
    ks = [-1] * ((len(LAYERS) + 2) * MAXENG * MAXPAGES * 4)
    np_ = [0] * ((len(LAYERS) + 2) * MAXENG)
    pnames = [""] * ((len(LAYERS) + 2) * MAXENG * MAXPAGES)
    for li, L in enumerate(LAYERS):
        for ei, (e, _) in enumerate(engines(L)):
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
    np_[(GLOBAL_LAYER + 1) * MAXENG] = len(MIX_PAGES)
    for pi, (pn, refs) in enumerate(MIX_PAGES):
        pnames[((GLOBAL_LAYER + 1) * MAXENG) * MAXPAGES + pi] = pn
        for k, (L, n) in enumerate(refs):
            ks[(((GLOBAL_LAYER + 1) * MAXENG) * MAXPAGES + pi) * 4 + k] = S(L, None, n)
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
