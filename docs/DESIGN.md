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
| Pads | fm, vox, part, fold, pulsr, saws, pwm, sync, sine, glass, cz, choir, vosim, lissa, chip (removed: bow, digi, tine, whistle, organ, reed, beat, air) |
| Percussive (bells and motion merged) | lpg, bowl, wood, blip, metal: longer decays, more tuning |
| Cloud | granular, captures engine output or external input |
| Audio input | kept, to be refined |

## Removed
Reverb, atmospheres, character effects, Freeze, JOURNEY, PUMP/DUCK, MOSAIC (in its old form), the 16 tuned / exotic scales.

## Decided
- Sound direction: rawer, purer. All engines will be fine-tuned later.
- 4 engine knobs per engine (chosen from `PARAMETERS.md`), plus layer controls: envelope with default shapes and
  custom, filter, glide, and 2 LFOs per layer (free or clock-synced).
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
- Keep: saves, the PERFORM page (reworked: a continuous tone control with normal at the centre, low-pass to the
  right, something else to the left; Sink's silence near 0 fixed).

## Open
- Pads: one engine for all 4 voices, or a 2 + 2 split.
- The screen (keep the score view, or change it).
- PERFORM's left side; Swell and Harm (keep, rework or drop); ANCHOR (drop?).
- The scale / mode list.
