"""The patch's README.txt (how to play it), from the same tables as the patch."""
import model as M
from control import KEYS, AUX_KEYS

NAMES = {60: "C", 61: "C#", 62: "D", 63: "D#", 64: "E", 65: "F", 66: "F#", 67: "G", 68: "G#", 69: "A", 70: "A#",
         71: "B"}
WHAT = {"al-sel-drone": "show the DRONE", "al-sel-sub": "show the SUB", "al-sel-pad": "show the PADS",
        "al-sel-perc": "show the PERC", "al-mute-drone": "mute the drone", "al-mute-sub": "mute the sub",
        "al-mute-pad": "mute the pads", "al-mute-perc": "mute the percussion",
        "al-global": "the MAIN / STORY / SYNC pages (again: the next one)", "al-pgprev": "page back",
        "al-pgnext": "page forward", "al-latch": "latch on / off for the shown layer (PERC: its pattern)",
        "al-startstop": "start / stop", "al-clear": "clear the shown layer (back to its default)",
        "al-chordprev": "previous chord", "al-chordnext": "next chord", "al-popoff": "the play view",
        "al-notesmode": "notes mode: the Organelle keys play the shown layer (again: back to functions)"}


def key(k):
    return ("low " if k < 72 else "top ") + NAMES[60 + (k - 60) % 12]


def text():
    out = ["AMBLE LITE", "==========", "",
           "Drone, sub, pads and percussion for real-time building. Loads silent: top C starts and stops.", "",
           "ORGANELLE KEYS (one press each)"]
    out += [f"  {key(k):8} {WHAT[v]}" for k, v in sorted(KEYS.items())]
    out += ["", "AUX held + key"]
    out += [f"  {key(k):8} {WHAT[v]}" for k, v in sorted(AUX_KEYS.items())]
    out += ["  aux tap  page forward", "",
            "KNOBS: the 4 parameters of the page on screen. A knob takes over once it passes the stored value.", "",
            "PAGES of each layer: LAYER (engine, level, cutoff, reso), ENV (attack, decay, sustain, release) or HIT",
            "(decay, velocity, octave, spread), PLAY (articulation, glide, octave, pan) or RHYTHM (hits, steps,",
            "rotate, rate), then the engine's parameters, 4 a page.", "",
            "ARTICULATION: artic (every note restarts), legato (overlapping notes don't), porta (overlapping notes",
            "slide), slide (every note slides). Glide sets the slide time.", "",
            "MIDI: channel 1 plays the shown layer; 2 drone, 3 sub, 4 pads, 5 percussion. Clock in (SYNC: ext)",
            "and out (SYNC: ClkOut).", "",
            "THE CHORD STORY (STORY page): a progression in the key and mode, the pads, sub and percussion",
            "following it; Bars sets how often it moves on (manual: top D / top E).", "",
            "ENGINES"]
    for L in M.LAYERS:
        out.append(f"  {M.LAYER_LABEL[L]:6} " + ", ".join(e for e, _ in M.ENGINES[L]))
    return "\n".join(out) + "\n"
