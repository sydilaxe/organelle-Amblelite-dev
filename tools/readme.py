"""The patch's README.txt (how to play it), from the same tables as the patch."""
import model as M
from control import KEYS, AUX_KEYS

NAMES = {60: "C", 61: "C#", 62: "D", 63: "D#", 64: "E", 65: "F", 66: "F#", 67: "G", 68: "G#", 69: "A", 70: "A#",
         71: "B"}
WHAT = {"al-sel-drone": "show the DRONE", "al-sel-sub": "show the SUB", "al-sel-pad": "show the PADS",
        "al-sel-perc": "show a PERC lane (again: the next lane)", "al-mute-drone": "mute the drone", "al-mute-sub": "mute the sub",
        "al-mute-pad": "mute the pads", "al-mute-perc": "mute the percussion lane last shown",
        "al-global": "the MAIN / STORY / SYNC / PERFRM pages (again: the next one)", "al-pgprev": "page back",
        "al-pgnext": "page forward", "al-latch": "latch on / off for the shown layer (PERC: its pattern)",
        "al-startstop": "start / stop", "al-clear": "clear the shown layer (back to its default)",
        "al-chordprev": "previous chord", "al-chordnext": "next chord", "al-layerview": "the play view (back from MIX / pattern)",
        "al-mix": "the MIX view: knobs set levels (again: the next mix page)",
        "al-patview": "the pattern view on / off: every gate and lane as steps",
        "al-loop": "the shown layer's looper: record, then play, overdub, play ...",
        "al-loopstop": "the shown layer's loop: stop / play", "al-loopclear": "clear the shown layer's loop",
        "al-notesmode": "notes mode: the Organelle keys play the shown layer (again: back to functions)"}


def key(k):
    return ("low " if k < 72 else "top ") + NAMES[60 + (k - 60) % 12]


def text():
    out = ["AMBLE LITE", "==========", "",
           "Drone, sub, pads and percussion for real-time building. Loads silent: top C starts and stops.", "",
           "ORGANELLE KEYS (one press each)"]
    out += [f"  {key(k):8} {WHAT[v]}" for k, v in sorted(KEYS.items())]
    out += ["  top A#   held + a key from low C to top D#: recall snapshot 1 - 16 (with aux: save it);",
            "           tapped alone: COMPARE (back to the sound before the recall; again: forward)"]
    out += ["", "AUX held + key"]
    out += [f"  {key(k):8} {WHAT[v]}" for k, v in sorted(AUX_KEYS.items())]
    out += ["  aux tap  page forward", "  aux held + a knob: ASSIGN - that knob's place on the FAV page takes a",
            "           parameter of the layer (the knob chooses which)", "",
            "KNOBS: the 4 parameters of the page on screen. A knob takes over once it passes the stored value.", "",
            "PAGES of each layer: LAYER (engine, level, cutoff, reso), ENV (attack, decay, sustain, release) or HIT",
            "(decay, velocity, octave, spread), PLAY (articulation, glide, octave, pan) or RHYTHM (hits, steps,",
            "rotate, rate), EVOLVE (evolve, pace, sync, drift), then the engine's parameters, 4 a page.", "",
            "EVOLVE: each layer changes slowly by itself - its engine's character, the filter, a breathing in level",
            "(pads: each voice its own) - on slow cycles that phase against each other: never static, never random.",
            "Evolve 0 = still; Pace: 5 minutes .. 25 s a cycle; EvSync: free or locked to the clock; Drift: a slight",
            "pitch wander (0 = exact). The master Evolve (PERFRM page) scales every layer's.", "",
            "LFO 1 / 2: Target (any of the layer's parameters: filter, level, place, envelopes, gate length,",
            "swing, the engine's), Rate (loop = one cycle per loop or pattern cycle; bars; Hz), Depth, Shape.", "",
            "LOOP: Len (auto: rounded to bars; free: as played; or 1 - 16 bars), Quant, Follow (chord: the loop",
            "moves with the chord story; exact), Vel. Records what you play into the layer.", "",
            "GATE: each gate has its own envelope (GATENV). FEEL: Swing and its feel (swing, lilt, drag, limp) on",
            "the gates and the lanes. MORPH (PERFRM page): how long a recalled snapshot glides (0 = at once).", "",
            "ARTICULATION: artic (every note restarts), legato (overlapping notes don't), porta (overlapping notes",
            "slide), slide (every note slides). Glide sets the slide time.", "",
            "MIDI: channel 1 plays the shown layer; 2 drone, 3 sub, 4 pads, 5 - 8 percussion lanes. Clock in (SYNC: ext)",
            "and out (SYNC: ClkOut).", "",
            "THE CHORD STORY (STORY page): a progression in the key and mode, the pads, sub and percussion",
            "following it; Bars sets how often it moves on (manual: top D / top E).", "",
            "ENGINES"]
    for k in ("drone", "sub", "pad", "perc"):
        out.append(f"  {k.upper():6} " + ", ".join(e for e, _ in M.ENGINES[k]))
    return "\n".join(out) + "\n"
