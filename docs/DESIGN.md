# Amble Lite: design decisions (working notes)

A stripped-back, performance-focused fork of Amble for the Organelle M, built for composing in real time.
Source of engines: `sydilaxe/organelle-Amble-dev`.

## Build approach
- **Principle:** keep it simple, keep the audio quality; live interactivity is added step by step.
- A fresh, small Python generator in this repo, reusing Amble's `pdlib.py` and the DSP of the engines kept.
  None of the composer, form or SETUP machinery comes across unless it is asked for.

## Layers
| Layer | Engines kept |
|---|---|
| Drone | analog, fm, frost, choir, bowed, spectral, gendy (removed: pure, organ) |
| Sub | sine, warm, pulse, fm |
| Pads | fm, vox, part, fold, pulsr, saws, pwm, sync, sine, wave (was glass), cz, choir, vosim, lissa, chip, vector (new) (removed: bow, digi, tine, whistle, organ, reed, beat, air) |
| Percussive (bells and motion merged) | lpg, bowl, wood, blip, metal, wave: longer decays, more tuning |
| Cloud | granular, captures engine output or external input |
| Audio input | kept, to be refined |

## The assistant (optional, rule-based, not random)
Algorithmic help kept from Amble, each switched on or off. Rules, not dice: the same settings give the same result,
and a *Variation* number picks a different, equally repeatable result.
- **Counterpoint:** pad voices move between chord tones as lines (neighbour, passing, contrary to the bass), with
  amount, which voices, style and pace.
- **Motifs:** a motif you play (or one drawn from the chord story) carried between layers, transformed (inverted,
  reversed, transposed to the chord, augmented / diminished) by you or by the roadmap.
- **Listening:** notes you play (MIDI or audio) pull the next chord to contain them; a held note can become the key
  centre.
- **Chord recommendation:** from the key, mode and current chord, the next chords ranked (function, voice leading,
  modal colour); accept one with a key and it joins the chord story.
- **Roadmap:** from a few setup parameters (length, arc, mode, tension, density), a plan of sections: each section's
  chord story, which layers play, percussion density, motif transformations. Two ways to use it: *guide* (the screen
  shows what is next, you play it) or *auto* (it happens, and you can hold, skip or override).

## Wavetables
A shared bank (factory PPG-style and Miniwave-style tables, plus your own WAVs in `waves/`); each engine picks its own table. See `WAVETABLES.md`.

## Removed
Reverb, atmospheres, character effects, Freeze, JOURNEY, PUMP/DUCK, MOSAIC (in its old form), the 16 tuned / exotic scales.

## Decided
- Sound direction: rawer, purer. All engines will be fine-tuned later.
- 4 engine knobs per engine (chosen from `PARAMETERS.md`), plus layer controls: envelope with default shapes and
  custom, filter, glide, and 2 LFOs per layer (free or clock-synced).
- Glide, per layer, two controls:
  - **Articulation** (one knob, three zones): *articulated* (every note retriggers its envelope, no slide);
    *legato* (overlapping notes don't retrigger, the pitch jumps); *portamento* (overlapping notes slide); at the
    far end, *always slide* (every note slides, even when detached).
  - **Rate**: the slide time, from a few ms to several seconds. Constant time (not constant rate), so a big
    leap and a step take the same time.
- Harmony: from MIDI input or a step / chord sequencer. The composer becomes an optional assistant.
- Scales: 12-tone with modes (to discuss).
- Playing: select a layer and play it. Each layer has a default behaviour (for example, chords on the pads) and a
  sequencing looper: record, overwrite or overdub motifs.
- Rhythm: Euclidean patterns, live play, recorded loops, clock retrigger, and a gate sequencer with envelopes.
  The percussive layer has complex cascading, interlocking patterns down to 1/32 (gamelan-like). Interplay between
  layers comes later, as a real-time option.
- MIDI: a controller on channel 1 plays the active layer, with an optional multi-channel mode. Targets are the
  Korg nanoKEY Studio / nanoKONTROL Studio and the DM48X (MPE and breath).
- Breath: flexible routing to parameters inside each layer, not to the whole volume. Possible "breath zones" mode:
  different notes' breath on the DM48X controls different layers.
- Saves: instant save and recall (used in performance) kept. COMPARE becomes an A/B **morph**: going to the other
  sound crossfades over a time you set, never abruptly.
- CPU: no effects for now (the reverbs loaded the processor hard and made the MIX levels laggy and choppy). Every
  level and parameter change is smoothed at audio rate (line~), and the screen redraws are throttled while knobs
  turn, so mixing stays smooth. Effects may come later, with headroom kept for them.
- Parameter pages: every engine exposes its full parameter list as pages of 4, with an assign mode to put your
  favourites on the first page. All defined in one table per engine, so controls are easy to add or remove.
- Keep: the PERFORM page (reworked: a continuous tone control with normal at the centre, low-pass to the
  right, something else to the left; Sink's silence near 0 fixed).

## Open
- Pads: one engine for all 4 voices, or a 2 + 2 split.
- The screen (keep the score view, or change it).
- PERFORM's left side; Swell and Harm (keep, rework or drop); ANCHOR (drop?).
- The scale / mode list.
