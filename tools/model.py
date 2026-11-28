"""The model: layers, engines, their parameters and the knob pages - one table, so a control is added or removed in
one place. Every parameter is a *slot*: a value 0..1 in the array alp (alp[slot]), sent on [s al-s<slot>] when it
changes. Engines read their slots as signals (dsp.prm) or as control values (alp[slot] in an [expr]).

Kinds of parameter:
  Param("Name", default)                      a plain 0..1 (shown as 0..100)
  Param("Name", default_index, opts=[...])    a choice: the knob is divided between the options
  Param("Name", default_value, lo=, hi=)      a number shown in its own units (tempo)
"""

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# the scales (MAIN page: Scale), each with its modes (Mode: the scale started from each of its degrees). MODES is
# all of them in one list: a scale's modes from SCALE_START[scale]
SCALES = [("modes", [("ionian", [0, 2, 4, 5, 7, 9, 11]), ("dorian", [0, 2, 3, 5, 7, 9, 10]),
                     ("phrygian", [0, 1, 3, 5, 7, 8, 10]), ("lydian", [0, 2, 4, 6, 7, 9, 11]),
                     ("mixolyd", [0, 2, 4, 5, 7, 9, 10]), ("aeolian", [0, 2, 3, 5, 7, 8, 10]),
                     ("locrian", [0, 1, 3, 5, 6, 8, 10])]),
          ("harmin", [("harmin", [0, 2, 3, 5, 7, 8, 11]), ("locr#6", [0, 1, 3, 5, 6, 9, 10]),
                      ("ion#5", [0, 2, 4, 5, 8, 9, 11]), ("dor#4", [0, 2, 3, 6, 7, 9, 10]),
                      ("phrdom", [0, 1, 4, 5, 7, 8, 10]), ("lyd#2", [0, 3, 4, 6, 7, 9, 11]),
                      ("altbb7", [0, 1, 3, 4, 6, 8, 9])]),
          ("melmin", [("melmin", [0, 2, 3, 5, 7, 9, 11]), ("dorb2", [0, 1, 3, 5, 7, 9, 10]),
                      ("lydaug", [0, 2, 4, 6, 8, 9, 11]), ("lyddom", [0, 2, 4, 6, 7, 9, 10]),
                      ("mixob6", [0, 2, 4, 5, 7, 8, 10]), ("locr#2", [0, 2, 3, 5, 6, 8, 10]),
                      ("altered", [0, 1, 3, 4, 6, 8, 10])]),
          ("pent", [("majpent", [0, 2, 4, 7, 9]), ("suspent", [0, 2, 5, 7, 10]), ("mangong", [0, 3, 5, 8, 10]),
                    ("ritusen", [0, 2, 5, 7, 9]), ("minpent", [0, 3, 5, 7, 10])])]
MODES = [m for _, ms in SCALES for m in ms]
SCALE_START = [sum(len(ms) for _, ms in SCALES[:i]) for i in range(len(SCALES))]
SCALE_COUNT = [len(ms) for _, ms in SCALES]
MAX_MODES = max(SCALE_COUNT)

# the chord story: chords as scale degrees (0 = the tonic chord), stacked in thirds within the mode.
# "modal" uses each mode's own characteristic move (dorian's IV, lydian's II, mixolydian's bVII ...)
MODAL = {"ionian": [0, 3, 5, 4], "dorian": [0, 3, 6, 4], "phrygian": [0, 1, 6, 1], "lydian": [0, 1, 4, 1],
         "mixolyd": [0, 6, 3, 0], "aeolian": [0, 5, 2, 6], "locrian": [0, 1, 5, 6],
         "harmin": [0, 5, 3, 4], "locr#6": [0, 1, 6, 0], "ion#5": [0, 3, 1, 0], "dor#4": [0, 1, 3, 1],
         "phrdom": [0, 1, 6, 1], "lyd#2": [0, 1, 4, 1], "altbb7": [0, 1, 5, 0],
         "melmin": [0, 3, 4, 1], "dorb2": [0, 1, 6, 1], "lydaug": [0, 1, 4, 1], "lyddom": [0, 6, 1, 4],
         "mixob6": [0, 5, 3, 6], "locr#2": [0, 5, 1, 6], "altered": [0, 1, 5, 0],
         "majpent": [0, 3, 1, 4], "suspent": [0, 2, 3, 1], "mangong": [0, 2, 4, 1], "ritusen": [0, 3, 1, 2],
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
           ("wholetn", "chr", [(0, "aug"), (2, "aug"), (4, "aug"), (6, "aug")]),
           # ---- your own: the suggestions you accept (aux + top E), up to 8 (harmony.py)
           ("own", "chr", [(0, "maj")])]
OWN_STORY = len(STORIES) - 1
# the roadmap: arcs (the roles of their sections), roles, and how many sections it holds at most
ROLES = ["emerge", "establ", "develp", "intens", "climax", "break", "return", "dissol"]
ARCS = ["arch", "build", "waves", "twin", "journy"]
ARC_ROLES = {"arch": [0, 1, 2, 3, 4, 2, 7], "build": [0, 1, 2, 2, 3, 3, 4, 7], "waves": [0, 2, 5, 2, 3, 5, 4, 7],
             "twin": [0, 3, 4, 5, 3, 4, 7], "journy": [0, 1, 2, 5, 3, 4, 6, 7]}
MAXSEC = 12
STORY_LEN = 8          # a story is stored as 8 chords (repeated to fill)


def story_degrees(story, mode):
    d = MODAL[mode] if story is None else story
    return [d[i % len(d)] for i in range(STORY_LEN)], len(d)


def story_chords(chords):
    """a library story as (roots, type indices), STORY_LEN each, and its length"""
    return ([chords[i % len(chords)][0] for i in range(STORY_LEN)],
            [TYPE_NAMES.index(chords[i % len(chords)][1]) for i in range(STORY_LEN)], len(chords))


class Param:
    """name: shown on screen (6 letters at most); key: its name in the layer, when two pages show the same name
    (the two LFOs' Rate, the gate envelope's Attack ...). target=True: an LFO's target - a choice among the
    layer's parameters (model.targets)"""
    def __init__(self, name, default=0.5, opts=None, lo=None, hi=None, key=None, target=False, late=False):
        assert len(name) <= 6, name
        self.name, self.opts, self.lo, self.hi, self.key, self.target = name, opts, lo, hi, key or name, target
        self.late = late         # (a global page's parameter added later: its slot after all the others - SLOTS)
        if target:
            self.default = (default + 0.5) / MAXC
            return
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
PITCHES = ["up", "down", "updown", "root", "fifth", "scl up", "scl dn", "stack", "motif"]
MOTIF_SRC = ["drone", "sub", "pads", "perc1", "perc2", "perc3", "perc4"]
MOTIF_TRANS = ["as is", "invert", "revrse", "+5th", "+oct", "-oct"]
LINE_VOICES = ["top", "inner", "all", "bass"]
LINE_STYLES = ["neighb", "passing"]
PHASES = ["off", "16bar", "8bar", "4bar", "2bar", "1bar"]
PHASE_BARS = [0, 16, 8, 4, 2, 1]
COMPS = ["none", "drone", "sub", "pads"]
CLOUD_PITCHES = ["unison", "octaves", "fifths", "chord", "shimmr"]
# each grain stream's transposition, per pitch set (the 'chord' set is worked out from the chord: cloud.py)
CLOUD_RATIOS = [[1, 1, 1, 1, 1, 1], [1, 0.5, 2, 1, 0.5, 2], [1, 1.5, 0.75, 2, 1, 1.5], None, [1, 2, 2, 4, 1, 2]]
FEELS = ["swing", "lilt", "drag", "limp"]
# a feel: each step's delay (x Swing x half a step), over 4 steps
FEEL_OFFSETS = [[0, 1, 0, 1], [0, 0.5, 0.25, 0.75], [0, 0.25, 0.5, 0.75], [0, 0, 1, 0]]
LFO_RATES = ["loop", "16bar", "8bar", "4bar", "2bar", "1bar", "1/2", "1/4", "0.02Hz", "0.05Hz", "0.1Hz", "0.2Hz",
             "0.5Hz", "1Hz", "2Hz", "4Hz"]
LFO_BEATS = [None, 64, 32, 16, 8, 4, 2, 1]                         # the synced rates: a cycle, in beats
LFO_SECS = [50, 20, 10, 5, 2, 1, 0.5, 0.25]                        # the free rates: a cycle, in seconds
LFO_SHAPES = ["sine", "tri", "saw up", "saw dn", "square", "steps", "rnd sm", "rnd st"]   # random: smooth, stepped
LFO_STEPS = [0, 0.75, -0.5, 1, -1, 0.25, -0.25, 0.5]               # the 'steps' shape: a fixed 8-step pattern
LOOP_LENS = ["auto", "free", "1bar", "2bar", "4bar", "8bar", "16bar"]
LOOP_BARS = [0, 0, 1, 2, 4, 8, 16]
QUANTS = ["off", "1/16", "1/8", "1/8T", "1/4"]
QUANT_CLOCKS = [1, 6, 12, 8, 24]
MAXC = 32          # an LFO's targets: off + up to 31 of the layer's parameters

LANES = ["perc1", "perc2", "perc3", "perc4"]
# the keyboard zones (MIDI page Zones on): the notes each layer takes (lo, hi); (127, 0): none. The first layer
# whose zone holds a note plays it
ZONE_DEFAULT = dict(sub=(0, 47), pad=(48, 71), perc1=(72, 127))
PROFILES = ["generic", "nanokey", "nanoktl", "dm48x", "user", "korg"]      # (korg: both KORGs at once)
OCT_DEFAULT = dict(drone=2, sub=1, pad=3, perc1=4, perc2=4, perc3=3, perc4=5)      # -1, -2, 0, +1 ...
# the lanes' defaults: a cascade that interlocks (engine, hits, steps, rotate, rate, pitch, phase, decay)
LANE_DEFAULT = dict(perc1=(3, 5, 8, 0, 3, 0, 0, 0.45), perc2=(4, 3, 8, 2, 1, 4, 0, 0.5),
                    perc3=(2, 2, 5, 0, 0, 3, 0, 0.75), perc4=(1, 7, 16, 0, 3, 2, 2, 0.4))


def kind(layer):
    """the engines a layer plays: the percussion lanes share theirs"""
    return "perc" if layer.startswith("perc") else layer


# the layers with notes (a looper, a pattern or a gate); the cloud has none: it grains what the others play
NOTE_LAYERS = ["drone", "sub", "pad", "perc1", "perc2", "perc3", "perc4"]


def layer_controls(layer, engines=()):
    """the layer's own pages: (front, back) - the engine's pages go between them"""
    perc = kind(layer) == "perc"
    d = LANE_DEFAULT.get(layer)
    eng = Param("Engine", d[0] if d else 0, opts=list(engines))
    common = [eng, Param("Level", 0.5), Param("Cutoff", 1.0), Param("Reso", 0.1)]
    evolve = ("EVOLVE", [Param("Evolve", 0.6), Param("Pace", 0.55), Param("EvSync", 0, opts=["free", "bars"])]
               + ([] if perc else [Param("Drift", 0.0)]))
    feel = ("FEEL", [Param("Swing", 0.0), Param("Feel", 0, opts=FEELS)])
    lfos = [(f"LFO {n}", [Param("Target", 0, key=f"L{n}Tgt", target=True),
                          Param("Rate", 10, opts=LFO_RATES, key=f"L{n}Rate"), Param("Depth", 0.5, key=f"L{n}Dep"),
                          Param("Shape", 0, opts=LFO_SHAPES, key=f"L{n}Shp")]) for n in (1, 2)]
    loop = ("LOOP", [Param("Len", 0, opts=LOOP_LENS, key="LpLen"), Param("Quant", 1, opts=QUANTS),
                     Param("Follow", 0, opts=["chord", "exact"]), Param("Vel", 0.8, key="LpVel")])
    zone = ZONE_DEFAULT.get(layer, (127, 0))
    breath = ("BREATH", [Param("Target", 0, key="BTgt", target=True), Param("Depth", 0.5, key="BDep"),
                         Param("ZoneLo", zone[0], lo=0, hi=127, key="ZnLo"), Param("ZoneHi", zone[1], lo=0, hi=127, key="ZnHi")])
    front = [("LAYER", common)]
    if layer == "cloud":
        return front, lfos + [breath, ("EVOLVE", evolve[1][:3])]
    if perc:
        return front, [
            ("HIT", [Param("Decay", d[7]), Param("Velo", 0.5), Param("Octave", OCT_DEFAULT[layer], opts=OCTAVES),
                     Param("Pitch", d[5], opts=PITCHES)]),
            ("RHYTHM", [Param("Hits", d[1], lo=1, hi=16), Param("Steps", d[2], lo=2, hi=16),
                        Param("Rotate", d[3], lo=0, hi=15), Param("Rate", d[4], opts=RATES)]),
            ("MOTION", [Param("Phase", d[6], opts=PHASES), Param("Spread", 0.8), Param("Accent", 0.3),
                        Param("Patt", 0, opts=["euclid", "tapped"])]),
            # a motif (its Pitch 'motif'): the notes of another layer's loop, transformed
            ("MOTIF", [Param("Source", 2, opts=MOTIF_SRC, key="MSrc"), Param("Transf", 0, opts=MOTIF_TRANS, key="MTran")]),
            feel] + lfos + [breath, evolve, loop]
    return front, [
        ("ENV", [Param("Attack", 0.45), Param("Decay", 0.6), Param("Sustn", 0.85), Param("Releas", 0.55)]),
        ("PLAY", [Param("Artic", 2, opts=ARTIC), Param("Glide", 0.45), Param("Octave", OCT_DEFAULT[layer], opts=OCTAVES),
                  Param("Pan", 0.5)]),
        ("GATE", [Param("Gate", 0, opts=["off", "on", "tapped"]), Param("Hits", 3, lo=1, hi=16), Param("Steps", 8, lo=2, hi=16),
                  Param("Rotate", 0, lo=0, hi=15)]),
        ("GATE 2", [Param("Rate", 1, opts=RATES), Param("Length", 0.5), Param("Comp", 0, opts=COMPS),
                    Param("Accent", 0.3)]),
        # counterpoint (pads): on the hits of a pattern, a voice steps from its chord tone and back
        ] + ([("LINES", [Param("Lines", 0.0), Param("Rate", 1, opts=RATES, key="LnRate"),
                         Param("Voices", 0, opts=LINE_VOICES, key="LnVoic"),
                         Param("Style", 0, opts=LINE_STYLES, key="LnStyl")])] if layer == "pad" else []) + [
        # the gate's own envelope: its hits shaped apart from the notes you play
        ("GATENV", [Param("Attack", 0.15, key="GAtk"), Param("Decay", 0.4, key="GDec"),
                    Param("Sustn", 0.6, key="GSus"), Param("Releas", 0.35, key="GRel")]),
        feel] + lfos + [breath, evolve, loop]


def targets(layer, engine):
    """what an LFO or the breath can move on this layer with this engine (after 'off'): the engine's own parameters
    first, then the filter, level, place, the envelopes and the gate's length"""
    if layer == "cloud":
        own = ["Cutoff", "Level"]
    elif kind(layer) == "perc":
        own = ["Cutoff", "Level", "Spread", "Decay", "Accent", "Velo", "Swing"]
    else:
        own = ["Cutoff", "Level", "Pan", "Attack", "Decay", "Sustn", "Releas", "GAtk", "GDec", "GSus", "GRel",
               "Length", "Swing"]
    ps = dict(engines(layer))[engine]
    out = ([S(layer, engine, p.key) for p in ps if not p.late] + [S(layer, None, k) for k in own] +
           [S(layer, engine, p.key) for p in ps if p.late])      # (added later: last, so the others keep their places)
    assert len(out) < MAXC, (layer, engine, len(out))
    return out


def target_index(knob, row):
    """(Pd expr) the target a Target knob picks: 0 off, else 1 .. the row's count - the knob's whole turn spread
    over the targets this engine has (alccnt: the count of the row, a layer x engine)"""
    return f"min(alccnt[{row}], int({knob}*(alccnt[{row}] + 1)))"


def target_slot(knob, row):
    """(Pd expr) the slot a Target knob moves, or -1 (off)"""
    i = target_index(knob, row)
    return f"if({i} == 0, -1, alcand[({row})*{MAXC} + {i} - 1])"


def target_value(layer, engine, name):
    """the knob value that aims a Target at a parameter (its name; engine None: one of the layer's own)"""
    t = targets(layer, engine)
    try:
        i = t.index(S(layer, engine, name)) + 1
    except (KeyError, ValueError):
        i = t.index(S(layer, None, name)) + 1
    return (i + 0.5) / (len(t) + 1)


# ---- engines: (name, [Param ...]); the DSP of each is in eng_<layer>.py under the same name
WAVE_TABLES = ["amble", "basic", "reson", "pulse", "formnt", "harmon", "mini"] + [f"user{i + 1}" for i in range(8)]

DELAY_PITCHES = ["-12", "-7", "-5", "0", "+5", "+7", "+12"]      # (the delay's Pitch: semitones a repeat)
# (the delay's Sync: free - Time in ms - or tempo - Time steps through these, in beats at the piece's tempo)
DELAY_DIVS = [("1/16", 0.25), ("1/8T", 1 / 3), ("1/8", 0.5), ("1/8.", 0.75), ("1/4", 1), ("1/4.", 1.5), ("1/2", 2),
              ("bar", 4)]
ENGINES = {
    "drone": [
        ("analog", [Param("WaveA", 0.67), Param("WaveB", 0.67), Param("Intvl", 0, opts=["unison", "5th", "oct", "-oct", "4th"]),
                    Param("Detune", 0.35), Param("XMod", 0.0), Param("Ring", 0.0), Param("Sub", 0.3), Param("Mix", 0.5),
                    Param("Bright", 0.7), Param("Reso", 0.25), Param("Sweep", 0.4), Param("Width", 0.6)]),
        ("fm", [Param("Ratio", 1, opts=["0.5", "1", "1.5", "2", "3", "3.5", "4", "5", "7"]), Param("Fine", 0.5),
                Param("Index", 0.35), Param("Fdbk", 0.0), Param("Motion", 0.3), Param("MoRate", 0.3),
                Param("Width", 0.6)]),
        ("spectr", [Param("Upper", 0.5), Param("Drift", 0.5), Param("DrRate", 0.4), Param("OddEv", 0.5),
                    Param("Tilt", 0.5), Param("Strtch", 0.0)]),
        ("frost", [Param("Detune", 0.4), Param("Bright", 0.5), Param("Glass", 0.4), Param("Drift", 0.4)]),
        ("choir", [Param("Vowel", 0.5), Param("Breath", 0.3), Param("Fifth", 0.5), Param("Drift", 0.4)]),
        ("bowed", [Param("Press", 0.5), Param("Body", 0.5), Param("Vib", 0.4), Param("Swell", 0.4)]),
        ("gendy", [Param("Steps", 0.4), Param("Rough", 0.5), Param("Spread", 0.5)]),
    ],
    "sub": [
        ("sine", [Param("Harm", 0.0), Param("Body", 0.5)]),
        ("warm", [Param("Octave", 0.5), Param("Body", 0.5)]),
        ("pulse", [Param("Width", 0.5), Param("Body", 0.5)]),
        ("fm", [Param("Ratio", 1, opts=["0.5", "1", "1.5", "2", "3"]), Param("Index", 0.3), Param("Fdbk", 0.0),
                Param("Growl", 0.3)]),
        # (added later: their slots after all the others - late)
        ("boom", [Param("Drop", 0.5, late=True), Param("Drive", 0.4, late=True), Param("Tone", 0.4, late=True)]),
        ("reese", [Param("Detune", 0.4, late=True), Param("Tone", 0.4, late=True), Param("Drive", 0.3, late=True)]),
        ("dub", [Param("Round", 0.3, late=True), Param("Warm", 0.4, late=True), Param("Tone", 0.35, late=True),
                 Param("Swell", 0.3, late=True)]),
    ],
    "pad": [
        ("sine", [Param("Harm", 0.0), Param("Slope", 0.5), Param("OddEv", 0.5), Param("Count", 6, opts=[str(n) for n in range(2, 9)]),
                  Param("Chorus", 0.0)]),
        ("fm", [Param("Ratio", 1, opts=["0.5", "1", "1.5", "2", "3", "3.5", "4", "5", "7"]), Param("Fine", 0.5),
                Param("Index", 0.3), Param("Fdbk", 0.0), Param("EnvAmt", 0.4), Param("EnvDec", 0.5)]),
        ("saws", [Param("Detune", 0.4), Param("Spread", 0.6), Param("Centre", 0.6), Param("Bright", 0.6),
                  Param("Reso", 0.3), Param("Sweep", 0.4)]),
        ("pwm", [Param("Width", 0.5), Param("Depth", 0.4), Param("Rate", 0.3), Param("Spread", 0.6),
                 Param("Bright", 0.6), Param("Sweep", 0.4)]),
        ("wave", [Param("Table", 0, opts=WAVE_TABLES), Param("Pos", 0.3), Param("Mode", 1, opts=["8bit", "smooth"]),
                  Param("Shimr", 0.0), Param("Detune", 0.3)]),
        # voice (vox and choir together): Source from a saw to glottal pulses, Breath (both added later: late)
        ("voice", [Param("Vowel", 0.5), Param("Motion", 0.4), Param("Reso", 0.4), Param("Body", 0.4),
                   Param("Source", 0.0, late=True), Param("Breath", 0.0, late=True)]),
        ("part", [Param("Set", 0, opts=["harm", "bell", "fifths", "odd", "strtch"]), Param("Tilt", 0.5),
                  Param("Swell", 0.4), Param("Spread", 0.6)]),
        ("fold", [Param("Fold", 0.4), Param("Sub", 0.3), Param("Bias", 0.5), Param("Motion", 0.3)]),
        ("pulsr", [Param("Formnt", 0.5), Param("Cycles", 0.4), Param("Sweep", 0.4), Param("Spread", 0.5)]),
        ("sync", [Param("Ratio", 0.4), Param("Sweep", 0.4), Param("Rate", 0.3), Param("Detune", 0.3)]),
        ("cz", [Param("Bend", 0.4), Param("Reso", 0.3), Param("Mix", 0.5), Param("Sweep", 0.4)]),
        # string (in choir's place - its four slots, so nothing saved moves)
        ("string", [Param("Bow", 0.4), Param("Bright", 0.5), Param("Decay", 0.6), Param("Spread", 0.5)]),
        ("vosim", [Param("Formnt", 0.5), Param("Decay", 0.5), Param("Sweep", 0.3), Param("Spread", 0.5)]),
        ("lissa", [Param("Ratio", 1, opts=["1:1", "3:2", "2:1", "4:3", "5:4"]), Param("Drift", 0.4),
                   Param("Bright", 0.3), Param("Cross", 0.25)]),
        ("chip", [Param("Duty", 2, opts=["12%", "25%", "50%"]), Param("Tri", 0.3), Param("Crush", 0.3),
                  Param("Vib", 0.4)]),
        ("vector", [Param("X", 0.5), Param("Y", 0.5), Param("Orbit", 0.4), Param("Rate", 0.3), Param("Detune", 0.3)]),
    ],
    "cloud": [
        ("grains", [Param("Size", 0.55), Param("Densty", 1.0), Param("Pitch", 0, opts=CLOUD_PITCHES),
                    Param("Spread", 0.9), Param("Scan", 0.15), Param("Jitter", 0.7), Param("Revrse", 0.2),
                    Param("Source", 0, opts=["layers", "input", "both"])]),
        # (added later - late): grains in time with the piece, on Euclidean patterns at three subdivisions that
        # cascade one into the next (cloud.rhythm)
        ("rhythm", [Param("Size", 0.6, late=True), Param("Densty", 0.5, late=True), Param("Spread", 0.8, late=True),
                    Param("Morph", 0.0, late=True), Param("Rate", 1, opts=["1/4", "1/8", "1/16"], late=True),
                    Param("Cascad", 0.5, late=True), Param("Scan", 0.15, late=True), Param("Jitter", 0.4, late=True),
                    Param("Source", 0, opts=["layers", "input", "both"], late=True)]),
        # a digital delay after the RDS-8000: feedback (Hold: the loop kept - dub: and played into), each repeat
        # pitched (Pitch), the time wavering (Mod), the sides apart (Width) (cloud.delay)
        ("delay", [Param("Time", 0.5, late=True), Param("Fdbk", 0.45, late=True), Param("Width", 0.5, late=True),
                   Param("Mod", 0.2, late=True), Param("Pitch", 3, opts=DELAY_PITCHES, late=True),
                   Param("Hold", 0, opts=["off", "hold", "dub"], late=True),
                   Param("Sync", 0, opts=["free", "tempo"], late=True), Param("Tone", 0.6, late=True),
                   Param("Source", 0, opts=["layers", "input", "both"], late=True)]),
    ],
    "perc": [
        ("blip", [Param("Cutoff", 0.5), Param("Flick", 0.5), Param("FlTime", 0.3), Param("Reso", 0.4),
                  Param("Sub", 0.5), Param("FEnv", 0.5)]),
        ("lpg", [Param("Fold", 0.5), Param("FoldDc", 0.5), Param("Open", 0.5), Param("Reso", 0.2), Param("Vactrl", 0.5)]),
        ("bowl", [Param("Hard", 0.5), Param("Beat", 0.5), Param("Strtch", 0.0), Param("Strike", 0.5)]),
        ("wood", [Param("Mallet", 0.5), Param("Matrl", 0.0), Param("Knock", 0.5)]),
        ("metal", [Param("Bright", 0.5), Param("Beat", 0.5), Param("TremR", 0.5), Param("TremD", 0.4)]),
        ("wave", [Param("Table", 0, opts=WAVE_TABLES), Param("Pos", 0.3), Param("Bright", 0.5), Param("Shimr", 0.3)]),
    ],
}
LAYERS = ["drone", "sub", "pad"] + LANES + ["cloud"]
LAYER_LABEL = {"drone": "DRONE", "sub": "SUB", "pad": "PADS", "perc1": "PERC1", "perc2": "PERC2", "perc3": "PERC3", "cloud": "CLOUD",
               "perc4": "PERC4"}
SHORT = {"drone": "Dr", "sub": "Sb", "pad": "Pd", "perc1": "P1", "perc2": "P2", "perc3": "P3", "perc4": "P4",
         "cloud": "Cl"}
VOICES = {"drone": 1, "sub": 1, "pad": 4, "perc1": 3, "perc2": 3, "perc3": 3, "perc4": 3}

# (a page's knob is a Param of its own, or (layer, key): another layer's slot, shown with the layer's name)
GLOBAL_PAGES = [("MAIN", [Param("Key", 0, opts=NOTE_NAMES), Param("Tempo", 84, lo=30, hi=200),
                          Param("Scale", 0, opts=[n for n, _ in SCALES]),
                          Param("Mode", 1, opts=[str(i + 1) for i in range(MAX_MODES)])]),
                ("LAYERS", [("drone", "Engine"), ("sub", "Engine"), ("pad", "Engine"), ("cloud", "Engine")]),
                ("LANES", [("perc1", "Engine"), ("perc2", "Engine"), ("perc3", "Engine"), ("perc4", "Engine")]),
                # pieces (features.pieces): the slot (top A#: load it; aux + top A#: save to it), and how layers
                # enter and leave - over the Fade time, or by their own envelope (FadeBy env: Attack in, Release out)
                ("PIECE", [Param("Piece", 0, opts=[str(i + 1) for i in range(8)]), Param("Fade", 0.62),
                           Param("FadeBy", 0, opts=["time", "env"])]),
                # the audio input (audioin.py): off (ignored, no CPU), reso, cloud, bands, morph, octave
                ("INPUT", [Param("Mode", 0, opts=["off", "reso", "cloud", "bands", "morph", "octave"], key="InMode"),
                           Param("Gain", 0.5, key="InGain"), Param("Amount", 0.5, key="InAmt")]),
                ("STORY", [Param("Story", 0, opts=[n for n, _, _ in STORIES]), Param("Bars", 3, opts=BARS),
                           Param("SubTo", 1, opts=SUBMODES), Param("Voicng", 0.4)]),
                ("SYNC", [Param("Sync", 0, opts=["int", "ext"]), Param("ClkOut", 1, opts=ONOFF)]),
                # MIDI: the controller profile (controllers/<name>.txt), channels (layers: 1 the shown layer, 2-9 one
                # layer each; mpe: every channel plays, each note its own bend and pressure), keyboard zones, and the
                # last CC that came in (to find what a controller sends)
                ("MIDI", [Param("Profil", 0, opts=PROFILES), Param("Chans", 0, opts=["layers", "mpe"]),
                          Param("Zones", 0, opts=ONOFF), Param("LastCC", 0, lo=0, hi=127)]),
                # NoteOt (NoteOut): every layer's notes out to MIDI, each layer on its own channel (2 drone ... 9 cloud)
                ("MIDI 2", [Param("Bend", 3, opts=["2", "12", "24", "48"]), Param("Press", 1, opts=["off", "expr", "breath"]),
                            Param("NoteOt", 0, opts=ONOFF, key="NoteOut", late=True)]),
                ("PERFRM", [Param("Evolve", 1.0), Param("Morph", 0.3), Param("Volume", 0.55), Param("CmpGl", 0.25)]),
                # the harmony assistant: the next chords ranked (Sugg shows one by name: aux + top E plays it and
                # adds it to your own story), which kind, and listening (held notes pull the next chord)
                ("HARMNY", [Param("Sugg", 0, opts=["1", "2", "3", "4"], key="Sugg"),
                            Param("Group", 3, opts=["mode", "borrow", "moves", "all"]),
                            Param("Listen", 0, opts=ONOFF)]),
                # the roadmap (roadmap.py): what it is built from (aux + top C# builds it), how it runs, a section
                ("ROAD", [Param("Mins", 12, lo=4, hi=30), Param("Arc", 0, opts=ARCS), Param("Tensn", 0.4),
                          Param("Densty", 0.5, key="RDens")]),
                ("ROAD 2", [Param("Road", 0, opts=["off", "guide", "auto"]), Param("Varia", 0, lo=0, hi=15)]),
                ("SECTN", [Param("Sect", 1, lo=1, hi=MAXSEC), Param("Bars", 16, lo=4, hi=64, key="SBars"),
                           Param("Story", 0, opts=[n for n, _, _ in STORIES], key="SStory"),
                           Param("Role", 0, opts=ROLES, key="SRole")])]
# SHAPE: the whole sound at once, on the master (gen.master_shape) - Filter (low-pass left of the middle, neutral at
# it, high-pass right of it: a DJ filter), its Reso, Drive (saturation), Blur (a diffuse smear). Their slots come after every other
# slot (SLOTS), so snapshots and pieces saved before them still load (features.widened)
SHAPE = [Param("Filter", 0.5), Param("Reso", 0.3), Param("Drive", 0.0), Param("Blur", 0.0)]
# the MIX view's pages: existing slots (layer, name); SHAPE last (the MIX key held: straight to it)
MIX_PAGES = [("MIX 1", [("drone", "Level"), ("sub", "Level"), ("pad", "Level"), ("cloud", "Level")]),
             ("MIX 2", [(L, "Level") for L in LANES]), ("MIX 3", [("g", "Volume")]),
             ("SHAPE", [("g", p.key) for p in SHAPE])]
SHAPE_PAGE = len(MIX_PAGES) - 1

# ---- Evolve: what moves in each engine, and how far (a weight: the share of the knob's range at Evolve 100 %).
# ("Cutoff", None) is the layer's filter. Each target moves on two slow sines of its own (control.evolve).
EVOLVE = {
    ("drone", "analog"): [("WaveA", 0.6), ("WaveB", 0.6), ("XMod", 0.3), ("Mix", 0.5), ("Bright", 0.4), (None, 0.2)],
    ("drone", "fm"): [("Index", 0.5), ("Fdbk", 0.3), ("Fine", 0.08), (None, 0.25)],
    ("drone", "spectr"): [("Upper", 0.5), ("Tilt", 0.4), ("OddEv", 0.5), (None, 0.2)],
    ("sub", "sine"): [("Harm", 0.3), ("Body", 0.3)],
    ("sub", "warm"): [("Octave", 0.4), ("Body", 0.3)],
    ("sub", "pulse"): [("Width", 0.5), ("Body", 0.3)],
    ("sub", "fm"): [("Index", 0.4), ("Growl", 0.3)],
    ("sub", "boom"): [("Tone", 0.3), ("Drive", 0.2)],
    ("sub", "reese"): [("Detune", 0.4), ("Tone", 0.3)],
    ("sub", "dub"): [("Tone", 0.3), ("Round", 0.3)],
    ("pad", "sine"): [("Harm", 0.5), ("Slope", 0.4), ("OddEv", 0.5), (None, 0.3)],
    ("pad", "fm"): [("Index", 0.5), ("Fdbk", 0.3), ("EnvAmt", 0.3), (None, 0.3)],
    ("pad", "saws"): [("Detune", 0.3), ("Spread", 0.4), ("Centre", 0.4), ("Bright", 0.4), (None, 0.3)],
    ("pad", "pwm"): [("Width", 0.5), ("Depth", 0.3), ("Rate", 0.2), ("Bright", 0.4), (None, 0.3)],
    ("pad", "wave"): [("Pos", 0.8), ("Shimr", 0.3), ("Detune", 0.3), (None, 0.3)],
    ("drone", "frost"): [("Bright", 0.4), ("Glass", 0.4), ("Detune", 0.2), (None, 0.2)],
    ("drone", "choir"): [("Vowel", 0.5), ("Breath", 0.3), (None, 0.2)],
    ("drone", "bowed"): [("Press", 0.4), ("Body", 0.3), (None, 0.2)],
    ("drone", "gendy"): [("Steps", 0.4), ("Rough", 0.3), (None, 0.2)],
    ("pad", "voice"): [("Vowel", 0.4), ("Reso", 0.2), (None, 0.3)],
    ("pad", "part"): [("Tilt", 0.4), ("Swell", 0.3), (None, 0.3)],
    ("pad", "fold"): [("Fold", 0.4), ("Bias", 0.3), (None, 0.25)],
    ("pad", "pulsr"): [("Formnt", 0.4), ("Cycles", 0.3), (None, 0.3)],
    ("pad", "sync"): [("Ratio", 0.3), (None, 0.3)],
    ("pad", "cz"): [("Bend", 0.4), ("Mix", 0.3), (None, 0.3)],
    ("pad", "string"): [("Bright", 0.3), ("Bow", 0.3), (None, 0.2)],
    ("pad", "vosim"): [("Formnt", 0.4), ("Decay", 0.3), (None, 0.2)],
    ("pad", "lissa"): [("Drift", 0.3), ("Bright", 0.3), ("Cross", 0.3)],
    ("pad", "chip"): [("Tri", 0.3), ("Crush", 0.2)],
    ("pad", "vector"): [("X", 0.6), ("Y", 0.6), (None, 0.2)],
    ("perc", "wave"): [("Pos", 0.5), ("Bright", 0.3)],
    ("cloud", "grains"): [("Scan", 0.5), ("Size", 0.4), ("Spread", 0.3), ("Jitter", 0.3), (None, 0.25)],
    ("cloud", "rhythm"): [("Scan", 0.5), ("Jitter", 0.3), ("Morph", 0.15), (None, 0.25)],
    ("cloud", "delay"): [("Mod", 0.3), ("Tone", 0.3), (None, 0.25)],
    ("perc", "blip"): [("Cutoff", 0.5), ("Flick", 0.3), ("FEnv", 0.3)],
    ("perc", "lpg"): [("Fold", 0.5), ("Open", 0.5), ("Vactrl", 0.3)],
    ("perc", "bowl"): [("Hard", 0.5), ("Beat", 0.4), ("Strtch", 0.2)],
    ("perc", "wood"): [("Mallet", 0.5), ("Matrl", 0.4), ("Knock", 0.3)],
    ("perc", "metal"): [("Bright", 0.5), ("Beat", 0.4), ("TremD", 0.3)],
}
EVOLVE_MAX = max(len(v) for v in EVOLVE.values())


def engines(layer):
    return ENGINES[kind(layer)]


def engine_value(layer, name):
    """the Engine knob's value (0..1) that selects an engine by name"""
    names = [e for e, _ in engines(layer)]
    return (names.index(name) + 0.5) / len(names)

# ---- slots
SLOTS = []              # [(key, Param)]
SLOT = {}               # key -> slot index; keys: ("g", name), (layer, None, name), (layer, engine, name)


def _add(key, p):
    SLOT[key] = len(SLOTS)
    SLOTS.append((key, p))


for _, ps in GLOBAL_PAGES:
    for p in ps:
        if isinstance(p, Param) and not p.late:
            _add(("g", None, p.key), p)
LAYER_PAGES = {}
for L in LAYERS:
    LAYER_PAGES[L] = layer_controls(L, [e for e, _ in engines(L)])
    for _, ps in LAYER_PAGES[L][0] + LAYER_PAGES[L][1]:
        for p in ps:
            _add((L, None, p.key), p)
    for e, ps in engines(L):
        for p in ps:
            if not p.late:
                _add((L, e, p.key), p)
# slots added since files were first saved go after all the others, so an older file's line is only shorter: its
# slots stay where they are, and the newer ones take their defaults (features.widened, the editor's widen).
# SLOT_HISTORY: how many slots there were before each addition, oldest first
SLOT_HISTORY = [len(SLOTS)]
for p in SHAPE:
    _add(("g", None, p.key), p)
SLOT_HISTORY.append(len(SLOTS))
for _, ps in GLOBAL_PAGES:          # (NoteOut)
    for p in ps:
        if isinstance(p, Param) and p.late:
            _add(("g", None, p.key), p)
SLOT_HISTORY.append(len(SLOTS))
for L in LAYERS:                    # (voice's Source and Breath; the subs boom, reese, dub)
    if L in ("pad", "sub"):
        for e, ps in engines(L):
            for p in ps:
                if p.late:
                    _add((L, e, p.key), p)
SLOT_HISTORY.append(len(SLOTS))
for e, ps in engines("cloud"):      # (the cloud's rhythm and delay)
    for p in ps:
        if p.late:
            _add(("cloud", e, p.key), p)
NSLOTS = len(SLOTS)
# the engine change (a file from before it: the sub's Engine was 1 of 4; a pad on choir becomes voice) -
# features.engine_fix, the editor's widen
OLD_ENGINES = {"sub": 4}
# (the cloud's engines: a file from before them - SLOT_HISTORY up to the last - had the one, grains)
CLOUD_OLD_ENGINES = 1
CHOIR_INDEX, VOICE_INDEX = 11, 5
OLD_NSLOTS = SLOT_HISTORY[0]


def S(layer, engine, name):
    """a slot by name: S('g', None, 'Tempo'), S('pad', None, 'Cutoff'), S('pad', 'fm', 'Index')"""
    return SLOT[(layer, engine, name)]


def pages(layer, engine):
    """the knob pages of a layer with an engine: FAV (your four: assign mode; at first Engine and the engine's first three),
    LAYER, the engine's parameters 4 a page, then the layer's other pages"""
    front, back = LAYER_PAGES[layer]
    eps = dict(engines(layer))[engine]
    ep = []
    for k in range(0, len(eps), 4):
        chunk = [S(layer, engine, p.key) for p in eps[k:k + 4]]
        ep.append((f"{engine.upper()} {k // 4 + 1}", chunk + [-1] * (4 - len(chunk))))
    # FAV: the engine choice on knob 1 (when the layer has more than one), then the engine's first parameters
    # (the cloud: its engine's own four - its engine is on the LAYERS page and its LAYER page)
    fav = ([S(layer, None, "Engine")] + ep[0][1][:3]) if len(engines(layer)) > 1 and layer != "cloud" else list(ep[0][1])
    out = [("FAV", fav)]
    out += [(n, [S(layer, None, p.key) for p in ps] + [-1] * (4 - len(ps))) for n, ps in front]
    out += ep
    out += [(n, [S(layer, None, p.key) for p in ps] + [-1] * (4 - len(ps))) for n, ps in back]
    return out


MAXPAGES = max(len(pages(L, e)) for L in LAYERS for e, _ in engines(L))
MAXENG = max(len(engines(L)) for L in LAYERS)
GLOBAL_LAYER = len(LAYERS)          # the "layer" index the MAIN / STORY pages use; + 1: the MIX pages


def global_slot(p):
    """a global page's knob: its own slot, or (layer, key) - another layer's"""
    if isinstance(p, Param):
        return S("g", None, p.key)
    L, key = p
    return SLOT.get((L, None, key), SLOT.get((L, engines(L)[0][0], key)))


def global_label(p):
    """(layer, key) knobs show the layer's name: the index into LAYERS, else -1"""
    return -1 if isinstance(p, Param) else LAYERS.index(p[0])


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
            ks[((GLOBAL_LAYER * MAXENG) * MAXPAGES + pi) * 4 + k] = global_slot(p)
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
        if p.target:
            n.append(-2)
            ob.append(0)
        elif p.opts:
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
