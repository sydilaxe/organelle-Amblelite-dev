"""The PDF manual and the one-page key chart, built from the same tables as the patch:
    python3 tools/manual.py [VERSION]      ->  docs/AmbleLite-manual.pdf, docs/AmbleLite-keys.pdf

Every key, page, knob, engine, scale and chord story is read from the generator (model, control, features), and
each must have a description here: a control added to the patch without one stops the build (check_complete).
The PDFs are written byte-for-byte the same for the same input (reportlab's invariant mode), so the committed
copies can be checked against the generator like the patch."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from reportlab import rl_config
rl_config.invariant = 1
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.pdfgen import canvas as pdfcanvas

import model as M
import control as C
import features as F

VERSION = sys.argv[1] if len(sys.argv) > 1 else "dev"
DOCS = os.path.join(HERE, "..", "docs")
SHOTS = os.path.join(DOCS, "shots")

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def key_name(k):
    return ("low " if k < 72 else "top ") + NAMES[k % 12]


# the SHAPE page's knobs (model.SHAPE)
SHAPE_DESC = {
    "Filter": "One sweep from high-pass to low-pass. Left of the middle a high-pass rises from 20 Hz to 6 kHz "
              "(thinner); at the middle (50) nothing is filtered; right of it a low-pass falls from 20 kHz to 100 Hz "
              "(darker).",
    "Reso": "The filter's resonance: a peak at the moving cutoff, rising as Filter leaves the middle - up high it "
            "sings.",
    "Drive": "Soft saturation of the whole mix, a little lopsided for even harmonics: warm at first, raw and electric "
             "turned up. The level is held about where it was.",
    "Blur": "A diffuse smear: the sound spread into a short, wide wash; turned up, more of it and a longer, darker "
            "tail (up to about 4 s) that drifts between the sides.",
}


# ---------------------------------------------------------------------------------------------- the keys
# what each function does: a short label (the key chart) and a sentence (the manual)
FUNCS = {
    "al-layerview": ("HOME", "Home: the play view (also from MIX, pattern and roadmap views)."),
    "al-mix": ("MIX", "The MIX view: the knobs set the layers' levels; again: the next mix page (MIX 1, MIX 2, "
                      "MIX 3, SHAPE). Held: the SHAPE page at once - Filter, Reso, Drive, Blur on the whole sound. "
                      "Its top line shows the CPU (cpu: this second, pk: the highest of the last ten)."),
    "al-patview": ("PATT", "The pattern view (every gate and lane as steps, a playhead under each), then the "
                              "roadmap view, then neither."),
    "al-global": ("GLOB", "The global pages (MAIN first); again: the next one."),
    "al-notesmode": ("NOTES", "Notes mode (N at the play view's right edge): the Organelle keys play the shown layer; aux + low A# goes back to "
                              "functions."),
    "al-startstop": ("START", "Start / stop the clock (the patch loads silent and waits for it)."),
    "al-pgprev": ("PAGE <", "Page back (the shown layer's or the global pages)."),
    "al-pgnext": ("PAGE >", "Page forward."),
    "al-chordprev": ("CHORD <", "The chord story's previous chord."),
    "al-chordnext": ("CHORD >", "The chord story's next chord."),
    "al-loop": ("LOOP", "The shown layer's looper: arm, the first pass, overdub, play (see Looping)."),
    "al-loopstop": ("STOP", "Stop / play the shown layer's loop."),
    "al-loopclear": ("CLR LOOP", "Clear the shown layer's loop (or cancel an armed one)."),
    "al-latch": ("LATCH", "Latch on / off for the shown layer (drone, sub, pads): notes keep sounding."),
    "al-clear": ("CLEAR", "Clear the shown layer: back to its default notes."),
    "al-vis": ("VISUAL", "The visualizer: an abstract oscilloscope, each shape moved by its layer's waveform - the "
                         "master's trace across the screen, the drone a closed shape whose outline is its waveform, "
                         "the sub its waveform along the bottom, the pads a Lissajous of their sides, the cloud points "
                         "rings sent out from the drone's shape; each lane's hit a rock falling into water, a spreading ring. "
                         "Aux tap: home."),
    "al-panic": ("PANIC", "Panic: everything fades out over 1.5 s, then the clock stops and every note is released "
                          "(latched ones too); silent - the cloud too - until Start. Loops are kept."),
    "al-taprec": ("TAP", "Tapped rhythm for the shown layer: arm, every cycle takes your taps, again: play."),
    "al-ownclear": ("OWN CLR", "Clear your own chord story (the suggestions you accepted)."),
    "al-sugaccept": ("ACCEPT", "Play the HARMNY page's suggestion now and add it to your own story."),
    "al-rgen": ("ROAD BUILD", "Build the roadmap from the ROAD pages' settings."),
    "al-rnext": ("ROAD NEXT", "The roadmap's next section."),
    "al-rhold": ("HOLD SECT", "Hold the roadmap's section (again: let it go)."),
    **{f"al-sel-{L}": (M.LAYER_LABEL[L], f"Show the {M.LAYER_LABEL[L]} pages at once.") for L in M.LAYERS},
}
SLOT_TEXT = ("SNAP CMP", "Held + a key from low C to top D#: recall snapshot 1-16 (aux held too: save it). Alone: "
                           "COMPARE - a tap flips between the snapshot as saved and your sound since, a hold hears the "
                           "saved one until you let go. On the PIECE page: load the piece (aux: save it).")


# ---------------------------------------------------------------------------------------------- the engines
ENGINE_DESC = {
    ("drone", "analog"): "Two oscillators that each morph sine - triangle - saw - square, A phase-modulated by B "
                         "(XMod), ringed together (Ring), a square an octave down (Sub); each side through its own "
                         "resonant low-pass that follows the note and sweeps slowly. Width: the right side a moving "
                         "delayed copy.",
    ("drone", "fm"): "Classic 2-operator FM: a modulator at Ratio (and Fine) into a sine carrier, its index moving "
                     "slowly (Motion, MoRate), feedback for grit. Width as the analog drone.",
    ("drone", "spectr"): "Spectral: eight harmonics, each swelling on its own slow cycle, odd ones left and even "
                         "ones right - the spectrum keeps shifting while the note holds.",
    ("drone", "frost"): "Three detuned saws drifting on their own through a resonant low-pass, with noise through "
                        "three glassy resonators on the note (after Frasil).",
    ("drone", "choir"): "Three voices a side - the note, a hair apart, and the fifth - glottal pulses through two "
                        "vowel formants that move slowly between ah, oh and oo.",
    ("drone", "bowed"): "A cello on the note: a saw with a slow bow-pressure swell and vibrato through the body's "
                        "resonances.",
    ("drone", "gendy"): "Xenakis' dynamic stochastic synthesis, gently: a wave of 12 breakpoints that each take a "
                        "small step every 30 ms, so the timbre breathes while the pitch holds (seeded: the same "
                        "walk each time).",
    ("sub", "sine"): "A sine, with harmonics from a soft saturation (Harm 0: pure).",
    ("sub", "warm"): "A rounder saturation and the octave above.",
    ("sub", "pulse"): "A pulse of adjustable width, low-passed twice.",
    ("sub", "fm"): "2-operator FM with a slow growl in its index.",
    ("pad", "sine"): "A sine with up to 8 harmonics built from it (Chebyshev), their slope and odd / even balance; "
                     "Chorus detunes the right side.",
    ("pad", "fm"): "Classic 2-operator FM with an index envelope at each note (EnvAmt, EnvDec).",
    ("pad", "saws"): "Three detuned saws (low left, high right, the centre in the middle) through a resonant "
                     "low-pass on the note that sweeps slowly, each side on its own cycle.",
    ("pad", "pwm"): "A pulse whose width breathes (Depth, Rate), the right side mirrored (Spread), through a slowly "
                    "sweeping low-pass - a Juno-like string.",
    ("pad", "wave"): "A wavetable from the shared bank: Pos scans its frames, 8-bit or smooth, a shimmer an octave "
                     "up, the right side detuned.",
    ("pad", "vox"): "A saw through two vowel formants that drift; the right side sings the mirror vowel.",
    ("pad", "part"): "Four sines at a set of ratios (harmonic, bell, fifths, odd, stretched), each swelling on its "
                     "own cycle, placed left and right.",
    ("pad", "fold"): "A sine wavefolded and ringed by its sub-octave; Bias makes the fold lopsided (even "
                     "harmonics).",
    ("pad", "pulsr"): "Pulsar synthesis: each period a short burst of a few sine cycles at a formant that sweeps "
                      "- between an insect and a choir.",
    ("pad", "sync"): "A hard-synced saw, the slave's ratio sweeping slowly - an electric lead.",
    ("pad", "cz"): "Phase distortion (the Casio CZ): a bent-phase wave on the left, the resonant wave on the "
                   "right, crossed by Mix.",
    ("pad", "choir"): "Glottal pulses and breath through two formants wandering through nine vowels; each side its "
                      "own vowel.",
    ("pad", "vosim"): "VOSIM: three sin-squared pulses each period at a formant, each weaker than the last - "
                      "vowel-like, a little nasal.",
    ("pad", "lissa"): "Lissajous: the note on the left, a ratio of it on the right drifting in phase, so the "
                      "stereo image turns.",
    ("pad", "chip"): "A game console's channels, raw: a stepped-duty pulse and a 4-bit triangle, the sample rate "
                     "held down (Crush), a late vibrato.",
    ("pad", "vector"): "Vector synthesis (as the Prophet VS): a sine, saw, pulse and triangle at the corners, mixed "
                       "by a point (X, Y) that circles (Orbit, Rate); each side a quarter turn apart.",
    ("cloud", "grains"): "Four grain streams from an 8 s recording of the other layers (or the input), each "
                         "transposed by the pitch set, placed across the stereo field.",
    ("perc", "blip"): "An analog blip: a saw and a sub sine with a pitch flick through a resonant low-pass that "
                      "closes.",
    ("perc", "lpg"): "A low-pass gate (Buchla-like): a wavefolded tone through a vactrol-style gate.",
    ("perc", "bowl"): "A singing bowl: inharmonic partials with a beating pair, long decay.",
    ("perc", "wood"): "A wooden bar - marimba to woodblock - with a mallet knock.",
    ("perc", "metal"): "A metallophone: vibraphone modes, a beating twin, a motor tremolo.",
    ("perc", "wave"): "A struck wavetable: a bright frame at the strike settling to its body frame, with a faint "
                      "octave shimmer.",
}

# ---------------------------------------------------------------------------------------------- the knobs
# by name, or by context: 'page:Name' (a layer page), 'kind/engine/Name' (an engine), 'g:PAGE:Name' (global)
DESC = {
    # layer controls
    "LAYER:Engine": "The layer's sound engine (also on the LAYERS / LANES global pages).",
    "LAYER:Level": "The layer's level in the mix (as its MIX column).",
    "LAYER:Cutoff": "The layer's low-pass filter: 20 Hz .. fully open (then bypassed). It moves smoothly at audio "
                    "rate.",
    "LAYER:Reso": "The filter's resonance: a peak at the cutoff.",
    "ENV:Attack": "Envelope for the notes you play: attack, 1 ms .. 8 s.",
    "ENV:Decay": "Decay to the sustain level, 5 ms .. 15 s.",
    "ENV:Sustn": "Sustain level.",
    "ENV:Releas": "Release after the note ends, 5 ms .. 20 s (FadeBy env: how the layer leaves).",
    "GATENV:Attack": "The gate's own envelope (its hits, apart from the notes you play): attack.",
    "GATENV:Decay": "The gate envelope's decay.",
    "GATENV:Sustn": "The gate envelope's sustain level.",
    "GATENV:Releas": "The gate envelope's release.",
    "PLAY:Artic": "Articulation: artic (every note restarts), legato (overlapping notes don't), porta "
                  "(overlapping notes slide), slide (every note slides).",
    "PLAY:Glide": "The slide time (the same for a step or a leap).",
    "PLAY:Octave": "The layer's octave.",
    "PLAY:Pan": "Its place left - right.",
    "GATE:Gate": "The gate sequencer: off (the layer sustains), on (Euclidean), tapped (your tapped rhythm).",
    "GATE:Hits": "Hits in the pattern.",
    "GATE:Steps": "Steps in the pattern's cycle (2-16).",
    "GATE:Rotate": "Where the pattern starts.",
    "GATE 2:Rate": "The step length: 1/4 .. 1/32, triplets too.",
    "GATE 2:Length": "How long each gate stays open (a share of the step).",
    "GATE 2:Comp": "Complementary: gate in the gaps of another layer's pattern (drone, sub or pads).",
    "GATE 2:Accent": "How much stronger the cycle's first hit is.",
    "LINES:Lines": "Counterpoint: how often a pad voice steps away from its chord tone and back.",
    "LINES:Rate": "Its step length.",
    "LINES:Voices": "Which voices move: top, inner, all, bass.",
    "LINES:Style": "Neighbour notes or passing notes.",
    "FEEL:Swing": "Swing on the gates and lanes.",
    "FEEL:Feel": "The swing's shape: swing, lilt, drag, limp.",
    "LFO 1:Target": "What the LFO moves: the loaded engine's own parameters first (Table, Bright, Vowel ...), "
                    "then the layer's filter, level, place, envelopes, gate length and swing. The knob's whole "
                    "turn covers just this engine's list. On the percussion lanes most parameters are taken at "
                    "each hit; these also move a hit while it rings: blip Cutoff and Reso, lpg Open and Reso, "
                    "bowl Beat and Strtch, wood Matrl, metal Beat, TremR and TremD, wave Pos and Bright.",
    "LFO 1:Rate": "Its speed: loop (one cycle per loop or pattern), bars, or Hz.",
    "LFO 1:Depth": "How far it moves.",
    "LFO 1:Shape": "sine, tri, saw up / down, square, steps, random smooth, random stepped (the same 'random' "
                   "every time).",
    "BREATH:Target": "What the breath controller (or MPE pressure) moves on this layer: the same list as the LFOs'.",
    "BREATH:Depth": "How far.",
    "BREATH:ZoneLo": "Keyboard zone (MIDI Zones on): the lowest note this layer takes.",
    "BREATH:ZoneHi": "The highest note.",
    "EVOLVE:Evolve": "Slow, never-random movement of the engine's character, the filter and a breathing in level "
                     "(0: still).",
    "EVOLVE:Pace": "How slow: 5 minutes .. 25 s a cycle.",
    "EVOLVE:EvSync": "Free, or locked to the clock.",
    "EVOLVE:Drift": "A slight pitch wander (0: exact).",
    "LOOP:Len": "Loop length: auto (rounded to bars), free (as played), or 1-16 bars.",
    "LOOP:Quant": "Recording quantised to: off, 1/16, 1/8, 1/8T, 1/4.",
    "LOOP:Follow": "chord: the loop moves with the chord story; exact: as played.",
    "LOOP:Vel": "The loop's playback level.",
    "HIT:Decay": "How long each strike rings.",
    "HIT:Velo": "How much the strikes' loudness varies.",
    "HIT:Octave": "The lane's octave.",
    "HIT:Pitch": "Where its notes come from: the chord up, down, up-down, root, fifth, the scale up / down, the "
                 "chord stacked, or a motif.",
    "RHYTHM:Hits": "Euclidean hits: spread as evenly as they go over Steps.",
    "RHYTHM:Steps": "The cycle's length (2-16): different lengths in different lanes interlock.",
    "RHYTHM:Rotate": "Where the pattern starts.",
    "RHYTHM:Rate": "The step length: 1/4 .. 1/32, triplets too.",
    "MOTION:Phase": "The lane drifts against the others and comes back in line after 1-16 bars (Reich).",
    "MOTION:Spread": "How far the lane's voices fan out in stereo.",
    "MOTION:Accent": "How much stronger the cycle's first hit is.",
    "MOTION:Patt": "euclid, or your tapped pattern.",
    "MOTIF:Source": "The layer whose loop the lane plays as a motif (Pitch: motif).",
    "MOTIF:Transf": "The motif as is, inverted, reversed, up a 5th or an octave, down an octave.",
    # global pages
    "g:MAIN:Key": "The key.",
    "g:MAIN:Tempo": "The tempo, 30-200 BPM.",
    "g:MAIN:Scale": "The scale family: modes (the church modes), harmin (harmonic minor), melmin (melodic minor), "
                    "pent (pentatonic).",
    "g:MAIN:Mode": "Which of its modes, by name (dorian, phrdom, lydaug ...).",
    "g:PIECE:Piece": "The piece slot: top A# loads it, aux + top A# saves to it.",
    "g:PIECE:Fade": "How long layers take to enter and leave (FadeBy time).",
    "g:PIECE:FadeBy": "time: every layer over Fade; env: the drone, sub and pads by their own Attack / Release.",
    "g:INPUT:Mode": "The audio input: off (ignored, no CPU); reso - four strings on the chord, rung by it; cloud - "
                    "into the granular cloud; bands - eight bands on the key and mode, breathing; morph - a vocoder: "
                    "it makes the pads speak; octave - with an octave below and above. Its pitch is heard in every "
                    "mode (HARMNY Listen).",
    "g:INPUT:Gain": "The input's level into its mode.",
    "g:INPUT:Amount": "reso: how long the strings ring; bands: how narrow; morph: how much vocoder; octave: below .. "
                      "above.",
    "g:STORY:Story": "The chord story: a progression from the library (traditional, modal, ambient, "
                     "experimental) or your own.",
    "g:STORY:Bars": "How often it moves on (manual: the chord keys).",
    "g:STORY:SubTo": "The sub: a pedal on the key's root, or each chord's root.",
    "g:STORY:Voicng": "How the pad voicing spreads.",
    "g:SYNC:Sync": "The clock: internal, or an external MIDI clock.",
    "g:SYNC:ClkOut": "Send MIDI clock out.",
    "g:MIDI:Profil": "The controller profile: generic, nanokey (nanoKEY Studio), nanoktl (nanoKONTROL Studio), "
                     "dm48x, user (controllers/<name>.txt), korg (both KORGs at once). The KORG ones expect the "
                     "Amble Lite sets (docs/controllers) written to the controllers with KORG KONTROL Editor.",
    "g:MIDI:Chans": "layers: channel 1 plays the shown layer, 2-9 one layer each; mpe: every channel plays, each "
                    "note its own bend and pressure (the DM48X).",
    "g:MIDI:Zones": "Keyboard zones: each layer takes its own range (its BREATH page), each zone's breath its own.",
    "g:MIDI:LastCC": "The last CC number that came in (to find what a controller sends).",
    "g:MIDI 2:Bend": "Pitch bend range in semitones.",
    "g:MIDI 2:Press": "MPE pressure: off, a note's level (expr), or the breath.",
    "g:MIDI 2:NoteOt": "Notes out (off / on): every note the layers play goes out to MIDI, each layer on its own channel - 2 drone, 3 sub, 4 pads, 5-8 the lanes (the cloud has no notes). The drone, sub and pads as their gates open and close (a new chord under an open gate: the old note off, the new one on); the lanes as they are struck. A controller that echoes notes back (MIDI thru) would play them again: turn its thru off.",
    "g:PERFRM:Evolve": "The master Evolve: scales every layer's.",
    "g:PERFRM:Morph": "How long a recalled snapshot glides (0: at once).",
    "g:PERFRM:Volume": "The master volume (also MIX 3).",
    "g:PERFRM:CmpGl": "How fast COMPARE glides between saved and yours (0: at once .. 4 s).",
    "g:HARMNY:Sugg": "The suggested next chords, ranked: aux + top E plays the shown one and adds it to your story.",
    "g:HARMNY:Group": "Which suggestions: in the mode, borrowed, moves to a new key, or all.",
    "g:HARMNY:Listen": "Listening: notes you hold pull the next chord to contain them.",
    "g:ROAD:Mins": "The roadmap's length in minutes.",
    "g:ROAD:Arc": "Its shape: arch, build, waves, twin, journey.",
    "g:ROAD:Tensn": "Tension: how far the harmony travels.",
    "g:ROAD:Densty": "How many layers play.",
    "g:ROAD 2:Road": "off; guide (the screen says what is next, you play it); auto (it happens, you can hold or "
                     "skip).",
    "g:ROAD 2:Varia": "Variation: another, equally repeatable roadmap from the same settings.",
    "g:SECTN:Sect": "The section to edit (layer keys toggle its layers; top A# captures your changes into it, aux + top A# clears them).",
    "g:SECTN:Bars": "Its length in bars.",
    "g:SECTN:Story": "Its chord story.",
    "g:SECTN:Role": "Its role: emerge, establish, develop, intensify, climax, break, return, dissolve.",
    # engines
    "drone/analog/WaveA": "Oscillator A's shape: sine - triangle - saw - square.",
    "drone/analog/WaveB": "Oscillator B's shape.",
    "drone/analog/Intvl": "B's interval above A.",
    "drone/analog/Detune": "B detuned, up to 30 cents.",
    "drone/analog/XMod": "Cross modulation: B modulates A's phase.",
    "drone/analog/Ring": "A ringed by B.",
    "drone/analog/Sub": "The square an octave down.",
    "drone/analog/Mix": "A against B.",
    "Bright": "Brightness: where the low-pass sits above the note (or the brighter frame / partials).",
    "drone/analog/Reso": "The sweeping filter's resonance.",
    "pad/saws/Reso": "The sweeping filter's resonance.",
    "Sweep": "How far the slow sweep moves.",
    "Width": "Stereo width (drones) / pulse width (sub, pwm).",
    "Ratio": "Frequency ratio (FM modulator, sync slave, Lissajous right side).",
    "Fine": "Fine tune of the ratio.",
    "Index": "FM depth.",
    "Fdbk": "Modulator feedback: towards a saw.",
    "Motion": "Slow movement depth.",
    "MoRate": "Its speed.",
    "Upper": "The upper harmonics' level.",
    "Drift": "Drift depth (slow, per side or partial).",
    "DrRate": "Drift speed.",
    "OddEv": "Odd against even harmonics.",
    "Tilt": "The spectrum's slope.",
    "Strtch": "Stretched (inharmonic) partials.",
    "Glass": "The glassy resonators' level.",
    "Vowel": "The vowel.",
    "Breath": "Breathiness.",
    "Fifth": "The fifth voice's level.",
    "Press": "Bow pressure.",
    "Body": "The body / tone filter.",
    "Vib": "Vibrato depth.",
    "Swell": "Slow swell depth.",
    "Steps": "The breakpoints' step size (roughness of the walk).",
    "Rough": "Smoothing: low = soft, high = rough.",
    "Spread": "Stereo spread.",
    "Harm": "Harmonics added.",
    "Octave": "The octave above.",
    "Growl": "Slow index wobble.",
    "Slope": "How fast the harmonics fall off.",
    "Count": "How many harmonics.",
    "Chorus": "The right side detuned.",
    "EnvAmt": "Index envelope depth at each note.",
    "EnvDec": "Index envelope decay.",
    "Detune": "Detune.",
    "Centre": "The centre saw's level.",
    "Depth": "Modulation depth.",
    "Rate": "Modulation speed.",
    "Table": "The wavetable: the factory bank, then user1-8 (your WAVs in waves/, in name order).",
    "Pos": "Position in the table's frames.",
    "Mode": "8-bit (stepped, nearest frame) or smooth.",
    "Shimr": "An octave shimmer.",
    "Reso": "Resonance.",
    "Set": "The partials' ratio set: harmonic, bell, fifths, odd, stretched.",
    "Swell": "Each partial's slow swell.",
    "Fold": "Fold drive.",
    "Sub": "Sub-octave amount.",
    "Bias": "The fold's symmetry (even harmonics).",
    "Formnt": "The formant frequency.",
    "Cycles": "Sine cycles per burst.",
    "Bend": "Phase bend: sine towards saw.",
    "Mix": "The resonant wave's share.",
    "Decay": "Each pulse weaker than the last.",
    "Cross": "Each side into the other.",
    "Duty": "The pulse's duty cycle.",
    "Tri": "The triangle crossed into the pulse.",
    "Crush": "Sample rate held down.",
    "X": "The point's X (sine - saw / pulse - triangle).",
    "Y": "The point's Y.",
    "Orbit": "How far the point circles.",
    "Size": "Grain length, 30 ms .. 2 s.",
    "Densty": "How many grain streams (1-4).",
    "Pitch": "The streams' transpositions: unison, octaves, fifths, the chord, shimmer.",
    "Scan": "How far back in the 8 s buffer the grains read.",
    "Jitter": "How far around Scan each grain starts.",
    "Revrse": "How many grains play backwards.",
    "Source": "What the cloud records: the layers, the input, or both.",
    "Cutoff": "Filter cutoff.",
    "Flick": "The pitch flick at the strike.",
    "FlTime": "Its time.",
    "FEnv": "Filter envelope depth.",
    "FoldDc": "The fold's decay.",
    "Open": "How far the gate opens.",
    "Vactrl": "The vactrol's slowness.",
    "Hard": "Mallet hardness.",
    "Beat": "Beating between partials.",
    "Strike": "Strike brightness.",
    "Mallet": "Mallet hardness.",
    "Matrl": "Material: marimba .. woodblock.",
    "Knock": "The knock's level.",
    "TremR": "Tremolo speed.",
    "TremD": "Tremolo depth.",
}
for n in (2,):
    for nm in ("Target", "Rate", "Depth", "Shape"):
        DESC[f"LFO {n}:{nm}"] = DESC[f"LFO 1:{nm}"]


def desc(ctx_keys):
    for k in ctx_keys:
        if k in DESC:
            return DESC[k]
    return None


def value_text(p):
    if p.target:
        return "a parameter"
    if p.opts:
        return " / ".join(p.opts) if len(p.opts) <= 9 else f"{p.opts[0]} .. {p.opts[-1]} ({len(p.opts)})"
    if p.lo is not None:
        return f"{p.lo}-{p.hi}"
    return "0-100"


def default_text(p):
    if p.target:
        return "off"
    if p.opts:
        return p.opts[min(len(p.opts) - 1, int(p.default * len(p.opts)))]
    if p.lo is not None:
        return f"{p.lo + p.default * (p.hi - p.lo):.0f}"
    return f"{p.default * 100:.0f}"


def check_complete():
    """every control in the patch has a description here (a new one without stops the build)"""
    missing = []
    for k, engs in M.ENGINES.items():
        for e, ps in engs:
            if (k, e) not in ENGINE_DESC:
                missing.append(f"engine {k}/{e}")
            for p in ps:
                if not desc([f"{k}/{e}/{p.name}", p.name]):
                    missing.append(f"{k}/{e}/{p.name}")
    for L in M.LAYERS:
        front, back = M.LAYER_PAGES[L]
        for title, ps in front + back:
            for p in ps:
                if not desc([f"{title}:{p.name}"]):
                    missing.append(f"{L} {title}:{p.name}")
    for title, ps in M.GLOBAL_PAGES:
        for p in ps:
            if isinstance(p, M.Param) and not desc([f"g:{title}:{p.name}"]):
                missing.append(f"g:{title}:{p.name}")
    for f in list(C.KEYS.values()) + list(C.AUX_KEYS.values()):
        if f not in FUNCS:
            missing.append(f"key {f}")
    assert not missing, "manual.py: no description for " + ", ".join(missing)


# ---------------------------------------------------------------------------------------------- styles
SS = getSampleStyleSheet()
BODY = ParagraphStyle("b", parent=SS["BodyText"], fontName="Helvetica", fontSize=9.5, leading=12.5, spaceAfter=4)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=8, leading=10, spaceAfter=0)
H1 = ParagraphStyle("h1", parent=SS["Heading1"], fontName="Helvetica-Bold", fontSize=17, spaceBefore=6, spaceAfter=8)
H2 = ParagraphStyle("h2", parent=SS["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, spaceBefore=10, spaceAfter=4)
H3 = ParagraphStyle("h3", parent=SS["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=6, spaceAfter=2)
TITLE = ParagraphStyle("t", parent=H1, fontSize=30, leading=36, spaceAfter=4)
INK, GRID, HEAD = colors.HexColor("#1c1c1c"), colors.HexColor("#c8c8c8"), colors.HexColor("#ececec")


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def P(t, st=BODY):
    return Paragraph(t, st)


def table(rows, widths, head=True):
    data = [[P(esc(c) if not str(c).startswith("<") else c, SMALL) for c in r] for r in rows]
    t = Table(data, colWidths=[w * inch for w in widths], repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), HEAD), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(st))
    return t


def shot(name, w=2.6):
    path = os.path.join(SHOTS, name + ".png")
    if not os.path.exists(path):
        return Spacer(1, 1)
    return Image(path, width=w * inch, height=w * inch / 2)


# ---------------------------------------------------------------------------------------------- the keyboard
WHITE = [k for k in range(60, 84) if k % 12 in (0, 2, 4, 5, 7, 9, 11)]
BLACK = [k for k in range(60, 84) if k not in WHITE]


def key_labels(k):
    """(top line: what a tap does, a second line: held / aux) for key k"""
    if k in C.LAYER_KEYS:
        L = C.LAYER_KEYS[k]
        return M.LAYER_LABEL[L], "tap in/out", "hold: pages"
    if k == C.SLOT_KEY:
        return SLOT_TEXT[0], "+key: snap", "aux: save"
    tap = FUNCS[C.KEYS[k]][0] if k in C.KEYS else ""
    aux = FUNCS[C.AUX_KEYS[k]][0] if k in C.AUX_KEYS and C.AUX_KEYS[k] != C.KEYS.get(k) else ""
    return tap, "", ("aux: " + aux) if aux else ""


def keyboard(width, fs=1.0, tall=3.1):
    """the Organelle's 24 keys with their functions (fs: the text's scale; tall: height / key width)"""
    ww = width / len(WHITE)
    h = ww * tall
    d = Drawing(width, h + 4)
    for i, k in enumerate(WHITE):
        d.add(Rect(i * ww, 0, ww - 1.5, h, fillColor=colors.white, strokeColor=INK, strokeWidth=0.8))
        a, b, c_ = key_labels(k)
        d.add(String(i * ww + 3, 6, key_name(k), fontName="Helvetica", fontSize=5.5 * fs, fillColor=colors.grey))
        # (an aux function on two lines: 'aux:', then its name - a white key is narrow too)
        lines = [a, b] + (["aux:", c_[5:]] if c_.startswith("aux: ") else [c_])
        for j, txt in enumerate(lines):
            if txt:
                d.add(String(i * ww + 3, h * 0.34 - j * 8 * fs, txt, fontName="Helvetica-Bold" if j == 0 else "Helvetica",
                             fontSize=(6.2 if j == 0 else 5.4) * fs, fillColor=INK))
    bw = ww * 0.66
    for k in BLACK:
        wi = WHITE.index(k - 1)
        x = (wi + 1) * ww - bw / 2 - 0.75
        d.add(Rect(x, h * 0.42, bw, h * 0.58, fillColor=INK, strokeColor=INK))
        a, b, c_ = key_labels(k)
        y = h - 10 * fs
        # (each word its own line: a black key is narrow)
        for j, txt in enumerate(t for t in (a, c_) if t):
            for part in txt.split(" "):
                d.add(String(x + 2, y, part, fontName="Helvetica-Bold" if j == 0 else "Helvetica",
                             fontSize=(5.6 if j == 0 else 5) * fs, fillColor=colors.white))
                y -= 7 * fs
            y -= 2 * fs
        d.add(String(x + 2, h * 0.42 + 3, key_name(k).split()[1], fontName="Helvetica", fontSize=5 * fs,
                     fillColor=colors.grey))
    return d


# ---------------------------------------------------------------------------------------------- the manual
def story():
    s = []
    s += [P("Amble Lite", TITLE), P(f"for the Critter &amp; Guitari Organelle M - version {esc(VERSION)}", BODY),
          Spacer(1, 6),
          P("A stripped-back, performance-focused instrument for building ambient, drone and experimental pieces in "
            "real time: a drone, a sub, pads, four interlocking percussion lanes and a granular cloud, each with "
            "its own engines, patterns, looper and slow evolving movement, over a chord story in any key and mode. "
            "Raw, present sound - no reverb or character effects - and controls fast enough to play."),
          Spacer(1, 4), keyboard(7.0 * inch), P("The Organelle's keys and what they do (the key chart has this alone, "
                                                "bigger).", SMALL)]
    s += [P("Quick start", H2)]
    for i, t in enumerate((
            "Load the patch: it starts silent. Press <b>top C</b> to start the clock.",
            "The drone, sub and pads come in and play the chord story. Tap a <b>low white key</b> to take a layer "
            "out or bring it in (drone low C, sub D, pads E, the lanes F G A B; the cloud top G).",
            "<b>Hold</b> a layer key to open its pages; the knobs set the four parameters shown. <b>Top D#</b> / "
            "<b>top C#</b> page forward / back. <b>Tap aux</b> to go home to the play view.",
            "The first page (FAV) has the <b>engine</b> on knob 1. Try the engines; each moves slowly on its own "
            "(Evolve).",
            "<b>Low D#</b>: the MIX view - the knobs are the layers' levels; again for the lanes and the master. "
            "<b>Hold</b> it for SHAPE: a filter, drive and blur over everything.",
            "<b>Low G#</b>: the global pages - MAIN (key, tempo, scale, mode), LAYERS and LANES (every layer's "
            "engine), PIECE ...",
            "Play: <b>low A#</b> turns the Organelle keys into notes for the shown layer (or play a MIDI keyboard). "
            "<b>Top F</b> loops what you play.",
            "Save a snapshot: hold <b>top A#</b>, hold aux, press a key from low C. Recall: hold top A# and press "
            "the key.")):
        s.append(P(f"{i + 1}. {t}"))
    # ---- keys
    s += [PageBreak(), P("The keys", H1)]
    rows = [["Key", "Tap", "Held / with aux"]]
    for k in range(60, 84):
        if k in C.LAYER_KEYS:
            L = C.LAYER_KEYS[k]
            rows.append([key_name(k), f"{M.LAYER_LABEL[L]} in / out (fades: PIECE page)",
                         f"held {C.LAYER_HOLD} ms or aux: its pages"])
        elif k == C.SLOT_KEY:
            rows.append([key_name(k), "COMPARE (tap: flip, hold: hear the saved one); PIECE page: load",
                         "held + key: recall snapshot; + aux: save (PIECE page: save the piece)"])
        else:
            tap = FUNCS[C.KEYS[k]][1] if k in C.KEYS else "-"
            aux = FUNCS[C.AUX_KEYS[k]][1] if k in C.AUX_KEYS and C.AUX_KEYS[k] != C.KEYS.get(k) else \
                ("the same (in notes mode)" if k in C.AUX_KEYS else "-")
            rows.append([key_name(k), tap, aux])
    s.append(table(rows, [0.7, 3.4, 3.2]))
    s += [P("Aux", H3), P("Tapped alone: home (the play view), from any page or view. Held with a knob on a "
                          "layer's pages: ASSIGN - that knob's place on the FAV page takes another of the layer's "
                          "parameters (the knob chooses). Held alone while a loop or tapped rhythm records: ERASE "
                          "(see Looping). In notes mode, aux + key reaches the functions."),
          P("Knobs", H3), P("The four parameters of the page on screen. A knob takes over once it passes the stored "
                            "value (no jumps). Turning one in the play view pops up its page for 3 s.")]
    # ---- screens
    s += [PageBreak(), P("Screens", H1)]
    shots = [("1-play", "Play view (home): key, mode, tempo, RUN / STOP (RUN*: changed since the snapshot); the "
                        "chord now and next. With a roadmap: the section (n / count), the time left counting down "
                        "and the piece's whole length, and the roadmap as a strip - a box a section, as wide as its "
                        "bars, the playing one filled, a playhead moving through it. Then a sign a layer, filled when "
                        "it is in, an outline when out: the drone a triangle, the sub a wave, the pads a figure of "
                        "eight, the lanes a stone in its ring, the cloud a square; under each its letter (the shown "
                        "layer's inverted) and a loop's state beside it (R recording, P playing, O overdub, s "
                        "stopped); at the right edge the MIDI-in light and N in notes mode."),
             ("2-layer-fav", "A layer's pages: the layer and engine, the page (n / count), the four knobs."),
             ("4-layer-lfo", "An LFO page: its target is any of the layer's parameters."),
             ("6-mix", "MIX: each layer's level as a column (hollow: out), V the master; cpu / pk on top."),
             ("7-pattern", "Pattern view: every gate and lane as steps, a playhead under each."),
             ("8-story", "A global page (STORY)."),
             ("10-roadmap", "Roadmap view: the sections as a strip, the current one filled, the layers in it, the "
                            "next role."),
             ("11-visual", "The visualizer (aux + low C#): the master's trace; the drone's outline, the sub's trace, "
                           "the pads' Lissajous, each from its own waveform; the hits' ripples; the cloud's rings.")]
    rows = []
    for i in range(0, len(shots), 2):
        cells = []
        for name, cap in shots[i:i + 2]:
            cells += [[shot(name), P(esc(cap), SMALL)]]
        rows.append(cells + [[Spacer(1, 1)]] * (2 - len(cells)))
    t = Table(rows, colWidths=[3.6 * inch, 3.6 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    s.append(t)
    # ---- layers
    s += [PageBreak(), P("Layers", H1),
          P("Eight layers, each in or out on its own key: <b>drone</b> (one voice, a held root with colour), "
            "<b>sub</b> (one voice, a pedal or the chord roots), <b>pads</b> (four voices, the chords, voice-led), "
            "four <b>percussion lanes</b> (three voices each: Euclidean or tapped patterns, cascading and "
            "interlocking down to 1/32) and the <b>cloud</b> (grains of the other layers or the input)."),
          P("A layer's pages: FAV (your four - Engine and the engine's first three at first), LAYER, the engine's "
            "parameters four a page, then the layer's own pages:")]
    for kind, L in (("drone, sub, pads", "pad"), ("percussion lanes", "perc1"), ("cloud", "cloud")):
        front, back = M.LAYER_PAGES[L]
        rows = [["Page", "Knob", "Range", "Default", "What it does"]]
        for title, ps in front + back:
            for p in ps:
                rows.append([title, p.name, value_text(p), default_text(p), desc([f"{title}:{p.name}"])])
        s += [P(f"Pages of the {kind}", H2), table(rows, [0.7, 0.65, 1.35, 0.6, 4.0])]
    # ---- engines
    s += [PageBreak(), P("Engines", H1),
          P("Each engine's own knobs follow the LAYER page, four a page. Only the selected engine runs (the others "
            "cost no CPU). Every engine moves slowly by itself - each side and voice on its own cycle - and Evolve "
            "moves its main character knobs further.")]
    for k, title in (("drone", "Drone"), ("sub", "Sub"), ("pad", "Pads"), ("perc", "Percussion lanes"),
                     ("cloud", "Cloud")):
        s.append(P(title, H2))
        for e, ps in M.ENGINES[k]:
            rows = [["Knob", "Range", "Default", "What it does"]]
            for p in ps:
                rows.append([p.name, value_text(p), default_text(p), desc([f"{k}/{e}/{p.name}", p.name])])
            s.append(KeepTogether([P(f"{e}", H3), P(esc(ENGINE_DESC[(k, e)]), BODY), table(rows, [0.75, 1.6, 0.6, 4.3])]))
    # ---- global pages
    s += [PageBreak(), P("Global pages", H1), P("Low G# opens them (MAIN first); low G# again or top D# / C# moves "
                                               "between them.")]
    for title, ps in M.GLOBAL_PAGES:
        rows = [["Knob", "Range", "Default", "What it does"]]
        for p in ps:
            if isinstance(p, M.Param):
                rows.append([p.name, value_text(p), default_text(p), desc([f"g:{title}:{p.name}"])])
            else:
                rows.append([M.LAYER_LABEL[p[0]], "its engines" if p[1] == "Engine" else "layers / input / both",
                             "", f"The {M.LAYER_LABEL[p[0]]}'s {p[1].lower()} (as on its own pages)."])
        s += [KeepTogether([P(title, H3), table(rows, [0.75, 1.9, 0.6, 4.0])])]
    # ---- SHAPE
    rows = [["Knob", "Range", "Default", "What it does"]]
    for p in M.SHAPE:
        rows.append([p.name, value_text(p), default_text(p), SHAPE_DESC[p.key]])
    s += [KeepTogether([P("SHAPE (the MIX view's last page)", H3),
                        P("The whole sound at once, for playing live. Hold <b>low D#</b> to open it (or press low D# "
                          "until it shows); a controller's <i>shape</i> action opens it too, and <i>param g.Filter</i> "
                          "(g.Reso, g.Drive, g.Blur) puts a knob on a fader. In order on the master: Drive, Blur, "
                          "then the Filter over both, the tail included. At neutral (Filter at 50, Drive and Blur at "
                          "0) each is switched off and costs nothing. Saved with snapshots and pieces; older saves "
                          "load with SHAPE at neutral.", BODY),
                        table(rows, [0.75, 1.9, 0.6, 4.0])])]
    # ---- looping
    s += [PageBreak(), P("Looping and tapped rhythms", H1),
          P("<b>Top F</b> (aux + top F in notes mode) is the shown layer's looper. Each layer has its own, with its "
            "own length - loops of different lengths drift against each other."),
          table([["", "Press", "Then"],
                 ["Arm", "the first press", "it starts on the next bar (Len free: on your first note); a second "
                                            "press starts it at once, even with nothing played - a blank loop"],
                 ["First pass", "-", "Len bars, or (auto / free) until your next press sets the length"],
                 ["Overdub", "automatic after the first pass", "pass after pass, until a press"],
                 ["Play", "a press", "a press again: overdub"],
                 ["Stop / clear", "top F# / top G#", "top G# also cancels an armed loop"]], [1.0, 1.9, 4.3]),
          Spacer(1, 6),
          P("<b>Erase</b>: while anything records, hold aux alone for a moment. What passes under the playhead is "
            "erased, and what you play meanwhile replaces it (in notes mode the keys play while aux erases). Let go: "
            "it overdubs again."),
          P("<b>Tapped rhythms</b>: aux + top F# arms the shown layer's pattern the same way; every cycle (Steps x "
            "Rate) takes the notes you play on it, snapped to the nearest step, until aux + top F# switches it to "
            "play. A lane's Patt (MOTION page) or a gate's Gate turns to 'tapped'; euclid / on goes back, keeping "
            "it. Tapped rhythms rotate, swing and phase, and are kept in snapshots and pieces."),
          P("Loop settings (each layer's LOOP page): Len, Quant, Follow (the loop moves with the chord story, or "
            "stays exact), Vel. With MIDI Zones on, the loop key records every zoned layer at once, and their "
            "breath.")]
    # ---- saves
    s += [P("Snapshots, COMPARE and pieces", H1),
          table([["", "Snapshots", "Pieces"],
                 ["How many", "16 (saves.txt)", "8 (pieces.txt)"],
                 ["What they hold", "everything: every parameter (key, tempo, scale, mode, engines), the layers in, "
                                    "FAV pages, tapped rhythms", "the same, the roadmap and every layer's loop (loops.txt)"],
                 ["Save", "hold top A#, hold aux, press a key (low C .. top D#)", "PIECE page: aux + top A#"],
                 ["Load", "hold top A#, press the key - it glides over Morph", "PIECE page: top A# - at once"],
                 ["For", "quick changes while playing", "a whole composition, ready to play"]], [1.1, 3.1, 3.0]),
          Spacer(1, 6),
          P("<b>COMPARE</b> (top A# alone): the snapshot as saved or recalled against your sound since. A tap flips "
            "between them - switch between two variations of a mix or a timbre - and a hold hears the saved one "
            "until you let go. Both glide over CmpGl (PERFRM page). RUN* / STOP* on the play view: changed since "
            "the snapshot."),
          P("<b>Fade</b> (PIECE page): FadeBy time - layers enter and leave over Fade; env - the drone, sub and "
            "pads by their own envelope (Attack in, Release out), the lanes and cloud by Fade.")]
    # ---- harmony
    s += [PageBreak(), P("Harmony", H1), P("Scales (MAIN page)", H2)]
    rows = [["Scale", "Its modes (Mode knob)"]] + [[n, ", ".join(m for m, _ in ms)] for n, ms in M.SCALES]
    s += [table(rows, [0.9, 6.3]),
          P("Everything follows the key, scale and mode: the chords, the lanes' scale runs, the counterpoint, the "
            "suggestions."),
          P("The chord story (STORY page)", H2),
          P("A progression in the key, moving on every Bars (or by the chord keys). <i>modal</i> uses the mode's own "
            "characteristic move; the others come from the library (written as scale degrees or as moves from the "
            "key, so each works in any key); <i>own</i> is the chords you accepted from the suggestions.")]
    rows = [["Story", "Chords"]]
    for name, kind_, data in M.STORIES:
        if kind_ == "deg":
            txt = "the mode's own move" if data is None else " - ".join("i ii iii iv v vi vii".split()[d % 7] for d in data)
        else:
            txt = " - ".join(f"{NAMES[r]}{'' if t == 'maj' else t}" for r, t in data) + " (from C)"
        rows.append([name, txt])
    s += [table(rows, [0.9, 6.3]),
          P("The assistant (HARMNY page)", H2),
          P("After each chord, the next chords ranked by function, voice leading and modal colour: in the mode, "
            "borrowed from the parallel mode, or moves to a new key. Aux + top E plays the shown suggestion and adds "
            "it to your own story (aux + top D clears it). Listen on: notes you hold pull the next chord to contain "
            "them. Counterpoint: the pads' LINES page. Motifs: a lane plays another layer's loop, transformed "
            "(MOTIF page).")]
    # ---- roadmap
    s += [P("The roadmap", H1),
          P("A plan of sections built from a few settings (ROAD page: minutes, arc, tension, density) - each section "
            "a length, a role, a chord story and which layers play. Aux + top A builds it; ROAD 2: off, guide (the "
            "screen says what is next) or auto (it happens: aux + low F# holds a section, aux + top B moves on). "
            "SECTN edits a section: its length, story and role, and the layer keys toggle its layers. A piece "
            "keeps its roadmap."),
          P("<b>A section's parameter changes.</b> Each section can also change up to 32 parameters when it starts "
            "(Road auto): any layer's, MAIN, INPUT, Evolve, Volume, SHAPE, the story's Bars, SubTo and Voicing. They "
            "are cumulative - applied on top of the sound as it is then, so a piece's sound travels from section to "
            "section; knob values glide over Morph, choices switch at once. To capture them on the Organelle: on "
            "the SECTN page choose the section (Sect), shape the sound, and tap <b>top A#</b> - what you changed "
            "since the section started (or since you chose it, or the last capture) is added to it (CAPTURED and "
            "its count; FULL past 32). <b>Aux + top A#</b> clears its changes. The web editor shows and edits them "
            "too (ROADMAP tab: the Changes column, and the list under the table for the chosen section). A piece "
            "saves and loads its sections' changes with it (sections.txt; the roadmap's own: roadchg.txt).")]
    # ---- the web editor
    s += [P("The web editor", H1),
          P("Amble Lite Editor (planner.html in the AmbleLite folder) opens pieces.txt, saves.txt, loops.txt and "
            "sections.txt from the AmbleLite folder and edits any piece or snapshot page by page, as on the Organelle: "
            "every parameter of every layer and engine, the layers in, the latches, the FAV pages, the tapped rhythms, "
            "a piece's roadmap and its loops (shown as notes; each can be stopped, started or cleared). Copy the files "
            "back over the ones in the AmbleLite folder (keep copies of the old ones); the patch reads them when it "
            "loads."),
          P("<b>From the Organelle itself</b> (Organelle OS with its web server, 5.x): the editor is in the AmbleLite "
            "folder as planner.html. Join the Organelle to your WiFi (or its own hotspot) and start the web server "
            "from the WiFi menu; on your phone or computer open "
            "<b>http://&lt;the Organelle's address&gt;:8080/get_file?fpath=sdcard/Patches/AmbleLite/planner.html</b> "
            "(usbdrive in place of sdcard when the patch is on a USB stick; the address is shown in the WiFi menu). "
            "It reads the folder's files at once. <b>Save and reload</b> writes them and reloads the patch (the "
            "sound stops for a moment); <b>Save only</b> writes them while the patch plays on - the patch takes them "
            "when it next loads. Each save keeps the old file as .bak beside it, and a file the patch saved since "
            "you opened the page is only overwritten when you say so. The Controllers section saves "
            "controllers/user.txt the same way (choose Profil: user). The patch plays on while the web server runs; "
            "stop it from the WiFi menu when you are done.")]
    # ---- the input
    s += [P("Audio input", H1), P(esc(DESC["g:INPUT:Mode"])), P(esc("Amount: " + DESC["g:INPUT:Amount"])),
          P("Off by default: the input is ignored and costs nothing until a mode is chosen.")]
    # ---- MIDI
    s += [P("MIDI and controllers", H1),
          P("Chans (MIDI page): <b>layers</b> - channel 1 plays the shown layer, 2-9 one layer each (2 drone, 3 sub, "
            "4 pads, 5-8 the lanes, 9 the cloud); <b>mpe</b> - every channel plays, each note its own bend and "
            "pressure (the DM48X). Zones: each layer takes its own key range, and each zone's breath shapes its own "
            "layer. Clock in and out (SYNC page)."),
          P("Profil chooses a controller profile, read from controllers/&lt;name&gt;.txt: lines 'cc &lt;n&gt; "
            "&lt;action&gt; [arg];' (any channel), 'chcc &lt;channel&gt; &lt;n&gt; &lt;action&gt; [arg];' or 'note "
            "&lt;ch&gt; &lt;n&gt; &lt;action&gt; [arg];'. Actions: knob 1-8 (the page shown and the next), level / "
            "toggle / show &lt;layer 1-8&gt;, loopl &lt;layer&gt; (its loop key), param &lt;name&gt; (one parameter, "
            "always: drone.Cutoff, pad.fm.Index, g.Tempo - the names are in slots.txt), engp &lt;layer x 10 + k&gt; "
            "(the layer's engine's k-th parameter, whichever engine it plays), breath, start, stop, startstop, "
            "chordnext, chordprev, loop, loopstop, loopclear, pgnext, pgprev, play, mix, pattern. LastCC shows the "
            "last CC that came in; controllers/user.txt is kept when a new version is copied over."),
          P("<b>The KORG sets.</b> docs/controllers holds a scene set for each KORG: AmbleLite.nktrl_st_set "
            "(nanoKONTROL Studio) and AmbleLite.nanokey_st_set (nanoKEY Studio). Open it in KORG KONTROL Editor and "
            "write it to the controller; then choose Profil nanoktl, nanokey or korg (both). nanoKONTROL Studio: a "
            "strip a layer (drone, sub, pads, perc 1-4, cloud) - S / Select show it, M takes it in / out, R is its "
            "loop key; the scenes: 1 Mix (levels, filters), 2 Tone (each engine's first two parameters), 3 Move "
            "(Evolve, LFO 1 depth), 4 Space (resonance, release / decay), 5 Pages (the page knobs, levels); the "
            "transport: play, stop, rec (loop), cycle (loop stop), rew / ff (the chord), track &lt; &gt; (the pages), "
            "marker set / &lt; / &gt; (MIX, play view, pattern view). nanoKEY Studio: the knobs the page shown and "
            "the next; the pads layers 1-5 in / out, start / stop, loop, MIX. The web editor's MIDI tab changes any "
            "of it and writes controllers/user.txt.")]
    s += [P("Files", H2),
          table([["File", "Holds", "Kept over an update"],
                 ["saves.txt", "the 16 snapshots", "yes (not in the release zip)"],
                 ["pieces.txt", "the 8 pieces", "yes"],
                 ["loops.txt", "the pieces' loops (a line a piece and layer)", "yes"],
                 ["roadmap.txt", "the roadmap", "yes"],
                 ["controllers/", "controller profiles (user.txt: yours)", "user.txt yes"],
                 ["waves/", "the factory bank (waves/factory) and your WAVs: user1-8, in name order - frames of 2048 "
                            "samples or a single cycle", "yours yes"]], [1.2, 3.4, 2.6])]
    return s


def footer(cv, doc):
    cv.saveState()
    cv.setFont("Helvetica", 7.5)
    cv.setFillColor(colors.grey)
    cv.drawString(0.6 * inch, 0.45 * inch, f"Amble Lite {VERSION}")
    cv.drawRightString(letter[0] - 0.6 * inch, 0.45 * inch, str(doc.page))
    cv.restoreState()


def keychart(path):
    """one landscape page: the keyboard, aux, knobs and the views"""
    W, H = landscape(letter)
    cv = pdfcanvas.Canvas(path, pagesize=(W, H), invariant=1)
    cv.setTitle("Amble Lite - keys")
    cv.setFont("Helvetica-Bold", 20)
    cv.drawString(0.5 * inch, H - 0.75 * inch, "Amble Lite - keys")
    cv.setFont("Helvetica", 9)
    cv.drawString(0.5 * inch, H - 0.98 * inch, f"version {VERSION} - the Organelle M's keys, low C (left) to top B")
    d = keyboard(W - 1.0 * inch, fs=1.45, tall=4.4)
    from reportlab.graphics import renderPDF
    renderPDF.draw(d, cv, 0.5 * inch, H - 1.25 * inch - d.height)
    y = H - 1.5 * inch - d.height
    blocks = [
        ("Aux", ["tap alone: HOME (the play view)", "held + a key: the key's aux function (and every function in "
                 "notes mode)", "held + a knob on a layer's pages: ASSIGN to FAV",
                 "held alone while recording: ERASE (play to replace)"]),
        ("Layers", ["the low white keys and top G", "tap: in / out (Fade / FadeBy)", f"hold {C.LAYER_HOLD} ms: its pages",
                                            "pages: FAV (Engine first), LAYER, engine, ENV / HIT, PLAY / RHYTHM, ..."]),
        ("Top A#", ["held + key low C..top D#: recall snapshot 1-16", "held + aux + key: save", "alone - tap: COMPARE "
                    "flip; hold: hear saved", "PIECE page: load (aux: save)"]),
        ("Looper (top F)", ["arm - next bar (free: first note)", "again: start now", "first pass -> overdub",
                            "press: play / overdub", "aux + top F#: tapped rhythm"]),
        ("Views", ["low C# HOME", "low D# MIX (levels)", "low F# PATTERN, ROADMAP", "low G# GLOBAL pages",
                   "low A# NOTES mode"]),
    ]
    colw = (W - 1.0 * inch) / len(blocks)
    for i, (title, lines) in enumerate(blocks):
        x = 0.5 * inch + i * colw
        cv.setFont("Helvetica-Bold", 10)
        cv.drawString(x, y, title)
        cv.setFont("Helvetica", 8)
        yy = y - 13
        for ln in lines:
            for part in _wrap(ln, 34):
                cv.drawString(x, yy, part)
                yy -= 10.5
            yy -= 2
    cv.setFont("Helvetica", 7.5)
    cv.setFillColor(colors.grey)
    cv.drawString(0.5 * inch, 0.45 * inch, "Global pages: " + ", ".join(t for t, _ in M.GLOBAL_PAGES) +
                  "   -   MIX pages: " + ", ".join(t for t, _ in M.MIX_PAGES))
    cv.showPage()
    cv.save()


def _wrap(t, n):
    out, cur = [], ""
    for w in t.split():
        if len(cur) + len(w) + 1 > n and cur:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return out + ([cur] if cur else [])


def main():
    check_complete()
    os.makedirs(DOCS, exist_ok=True)
    man = os.path.join(DOCS, "AmbleLite-manual.pdf")
    doc = SimpleDocTemplate(man, pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.7 * inch, title="Amble Lite", author="Amble Lite")
    doc.build(story(), onFirstPage=footer, onLaterPages=footer)
    keychart(os.path.join(DOCS, "AmbleLite-keys.pdf"))
    return man


if __name__ == "__main__":
    print(main())
