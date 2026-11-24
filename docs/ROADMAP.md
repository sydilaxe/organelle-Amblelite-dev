# The roadmap and the chord library

## Workflow
1. **Set up:** choose the piece's parameters: length, arc, key, mode, tension, density, tempo. Choose each layer's
   engine (or *auto*: the roadmap picks one and you can change it). Anything left on *auto* is decided by the plan;
   anything you set is kept.
2. **Build:** the roadmap is generated from those settings, by rules (the same settings give the same plan;
   *Variation* gives another one).
3. **Edit:** go through the sections and change anything: length, role, chord structure (from the library or
   suggested), which layers play, engines, percussion density, motif treatment.
4. **Perform:** play along it. Each item in a section is *planned* (happens by itself) or *live* (left to you), so
   some things are pre-planned and others stay in your hands. Hold, skip or repeat a section at any time.

## A section
| Field | Choices |
|---|---|
| Length | in bars |
| Role | emerge, establish, develop, intensify, climax, break, return, dissolve |
| Chords | a structure from the library, a generated one, or your own (chord sequencer) |
| Layers | per layer: on, off, enter / leave at 1/4, 1/2, 3/4 |
| Engines | per layer: keep, or change to a chosen engine |
| Percussion | density, pattern (Euclidean hits / steps / rotation), rate |
| Motif | none, state, invert, reverse, transpose, augment, diminish |
| Counterpoint | amount, voices |

## The chord library
Structures written as scale degrees or chromatic moves, so each works in any key; those marked *mode* fit one mode
best. You can pick from it, let the roadmap choose by role and tension, or ask for suggestions.

**Modal vamps:** i–IV (dorian), I–bVII (mixolydian), I–II (lydian), i–bII (phrygian), i–bVII–bVI–bVII (aeolian),
I–II–I–vii (lydian float).
**Functional:** I–IV–V–I, I–vi–IV–V, ii–V–I, vi–ii–V–I (circle), I–V–vi–iii–IV–I–IV–V (canon), I–IV–I (plagal),
I–V–vi–IV (axis).
**Minor and cinematic:** i–bVII–bVI–V (Andalusian), i–bVI–bIII–bVII, i–iv–bVII–bIII, i–bVI–iv–V.
**Colour and ambient:** I–bIII–I–bVI (chromatic mediants), I–iii–I–vi (diatonic mediants), chords over a tonic pedal,
planing (parallel chords), sus2 / sus4 cycles, neo-Riemannian moves (P, L, R: one note moving at a time).
**Generated:** from rules: tension rising and falling with the arc, tonic–subdominant–dominant function,
smoothest voice leading, or Tonnetz walks.

## Suggestions
From the current chord, the next chords ranked by function, voice leading and modal colour, in three groups you can
switch on: **in the mode**, **borrowed** (from the parallel mode), **moves** (to a new key or mode).
