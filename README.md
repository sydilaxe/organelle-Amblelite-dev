# Amble Lite

A stripped-back, performance-focused patch for the Critter & Guitari **Organelle M**, built from
[Amble](https://github.com/sydilaxe/organelle-Amble-dev): drone, sub, pads and percussion, played in real time.

**Status: milestone 1 (playable core).** It builds and passes its offline checks in Pure Data. It has not been run on
an Organelle yet.

- Install: copy `patches/AmbleLite` into the Organelle's `Patches` folder. How to play: `patches/AmbleLite/README.txt`.
- Design: `docs/DESIGN.md` (decisions), `docs/PARAMETERS.md`, `docs/WAVETABLES.md`, `docs/ROADMAP.md`.

## Source (`tools/`)
The patch is generated: edit the generator, not the `.pd` files.

| File | What it builds |
|---|---|
| `model.py` | layers, engines, every parameter (one table) and the knob pages |
| `engines.py` | the engines' DSP |
| `voice.py` | the voice abstractions `al-<layer>.pd` (pitch and glide, envelope, engines, filter, place) |
| `filters.py` | each layer's low-pass coefficients |
| `control.py` | parameters, knobs (pickup), pages, the Organelle keys, MIDI, notes to voices, clock, chord story |
| `screen.py` | the OLED |
| `wavetables.py` | the factory wavetables (WAV files) |
| `gen.py` | the patch: `python3 gen.py` |
| `check.py` | offline checks in Pd: `python3 check.py` |

Requirements: Python 3 with numpy, Pure Data 0.53+.
