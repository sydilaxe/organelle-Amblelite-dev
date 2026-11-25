# Amble Lite

A stripped-back, performance-focused patch for the Critter & Guitari **Organelle M**, built from
[Amble](https://github.com/sydilaxe/organelle-Amble-dev): drone, sub, pads and percussion, played in real time.

**Status:** playable and in testing on the Organelle M - every layer and engine, lanes and gates (Euclidean or
tapped), the looper, LFOs, Evolve, snapshots with COMPARE, pieces, the chord library and scales, the assistant and
the roadmap, MIDI / MPE / breath, the audio input's modes and your own wavetables (`waves/`).

- **Manual:** [`docs/AmbleLite-manual.pdf`](docs/AmbleLite-manual.pdf) - **key chart:** [`docs/AmbleLite-keys.pdf`](docs/AmbleLite-keys.pdf)
  (both built from the patch's own tables by `tools/manual.py`; also in each release).
- Install: copy `patches/AmbleLite` into the Organelle's `Patches` folder. Quick reference: `patches/AmbleLite/README.txt`.
- Roadmap planner (a web page): `docs/planner.html` - build a roadmap on a computer, copy its roadmap.txt to the patch folder.
- Design: `docs/DESIGN.md` (decisions), `docs/PARAMETERS.md`, `docs/WAVETABLES.md`, `docs/ROADMAP.md`.

## Source (`tools/`)
The patch is generated: edit the generator, not the `.pd` files.

| File | What it builds |
|---|---|
| `model.py` | layers, engines, every parameter (one table) and the knob pages |
| `engines.py` | the engines' DSP |
| `voice.py` | the voice abstractions `al-<layer>.pd` (pitch and glide, envelope, engines, filter, place) |
| `filters.py` | each layer's low-pass coefficients |
| `control.py` | parameters, knobs (pickup), pages, the Organelle keys, MIDI, notes to voices, clock, lanes, gates, chord story, Evolve |
| `features.py` | LFOs, assign mode, snapshots (save, recall, morph, compare), the looper, toasts |
| `midi.py` | MIDI in: channels, MPE, breath, keyboard zones, controller profiles (`controllers/*.txt`) |
| `cloud.py` | the cloud: an 8 s recording of the layers or the input, grained |
| `harmony.py` | chord suggestions, your own story, listening |
| `roadmap.py` | the roadmap: sections built from a few settings, guide / auto, roadmap.txt |
| `lines.py` | counterpoint (pad lines) and motifs (lanes playing another layer's loop) |
| `planner.py` | `docs/planner.html`: the web roadmap planner, from the same tables |
| `screen.py` | the OLED |
| `wavetables.py` | the factory wavetables (WAV files) |
| `gen.py` | the patch: `python3 gen.py` |
| `check.py` | offline checks in Pd: `python3 check.py` |

## Build

```
tools/build.sh            # regenerate patches/AmbleLite from the generator
tools/build.sh --check    # and run the offline checks in Pure Data
tools/package.sh v0.3     # dist/AmbleLite-v0.3.zip (without saves.txt, so an update keeps your snapshots)
```

Requirements: Python 3.12+ with numpy, Pure Data 0.53+ (`pd` on the path), zip.

GitHub Actions (`.github/workflows/build.yml`) does the same on every push and pull request: it builds, fails if the
committed patch differs from what the generator writes, runs the checks and packages the zip. Pushing a tag such as
`v0.3`, or running the workflow by hand (Actions > Build > Run workflow), publishes a GitHub Release with the zip.
