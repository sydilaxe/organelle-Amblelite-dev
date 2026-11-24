# Amble Lite: controllable parameters per engine

Each engine gets **4 engine knobs**. Pick 4 per engine, by letter: for example `analog: A B D F`.

- **★** marks the original Amble's two SHAPE knobs for that engine (knobs 3 and 4). **(b)** marks something that
  follows the layer's brightness.
- Anything you don't pick stays fixed at its designed value. Every value listed here exists in the code as a
  constant or a slow internal LFO, so any of them can become a knob.
- Breath, MPE pressure / slide, and the two LFOs per layer can be routed to any of the 4 engine knobs, and to the
  layer controls below.

## Layer controls (shared by every engine in a layer, not part of the 4)

| Control | Notes |
|---|---|
| Level, Pan / width | |
| Filter: cutoff, resonance | one filter per layer, after the engine |
| Envelope: attack, decay, sustain, release | each layer gets default shapes (pad swell, pluck, gate, drone hold) plus custom |
| Glide | 0 = hard note changes, for a walking bass |
| Octave / transpose | |
| LFO 1 and LFO 2 | rate (free in Hz, or synced from 32 bars to 1/32), shape, depth, target |

---

## Drone (7)

**analog** (redesigned): two oscillators with cross modulation, a sub-octave square, a resonant low-pass
- A Wave A: a continuous morph, sine → triangle → saw → square
- B Wave B: the same morph, for oscillator B
- C ★ Detune (B against A; B can also be set to an interval, such as a fifth or an octave)
- D Cross-mod: B frequency-modulates A (linear FM, a growl that grows as it opens)
- E Ring: A × B mixed in (metallic and sideband tones)
- F Sub: level of the square an octave down
- G Cutoff (b), H Resonance
- I ★ Sweep depth, J Sweep rate (the filter's slow movement)

**fm** (redesigned): a 4-operator FM engine (operators A B C D, A always a carrier), shared by the drone and the pads
- Algorithm (how the operators connect; 2 to 4 operators sound):
  1. 2-op: B → A
  2. 3-op stack: C → B → A
  3. 4-op stack: D → C → B → A
  4. three into one: B + C + D → A
  5. two pairs: B → A and D → C (two carriers, one per side, or blended)
  6. stack and sine: C → B → A, with D as a pure carrier underneath
- Ratio B, Ratio C, Ratio D (each snapping to useful ratios: 0.5, 1, 1.5, 2, 3, 3.5, 4, 5, 7, plus fine detune)
- Index B, Index C, Index D (how much each modulator modulates)
- Feedback on the top operator (sine → saw-like → noisy)
- Index motion: a slow cycle on all the indexes (depth, rate) - the drone's growl

**frost**: three detuned saws through a tracking low-pass, plus noise through glassy resonators
- A ★ Detune
- B ★ Glass (resonator level)
- C Cutoff (b)
- D Resonance (now fixed at 2.5)
- E Drift rate and depth
- F Resonator Q (now 30 to 50: the glass rings longer as Q rises)

**choir**: three voices through two vowel formants
- A ★ Vowel
- B ★ Breath (pulse width)
- C Vowel motion rate (now fixed at 0.023 Hz)
- D Vibrato depth / rate
- E Fifth voice level
- F Formant Q

**bowed**: a cello through body resonances
- A ★ Pressure
- B ★ Body
- C Vibrato depth / rate
- D Pressure swell rate
- E Body low-pass
- F Detune

**spectral**: eight harmonics, each swelling on its own cycle
- A ★ Upper (level of harmonics 2 to 8)
- B ★ Drift (swell depth)
- C Drift rate
- D Odd / even balance
- E Tilt (how fast the upper harmonics fall off)
- F Stretch (harmonics pushed out of tune towards bell-like)

**gendy**: Xenakis stochastic waveform
- A ★ Steps (random walk size)
- B ★ Rough (low-pass)
- C Step rate (now fixed at every 30 ms)
- D Breakpoints (now 12: fewer is buzzier, more is smoother)
- E Edge (amplitude limit of the walk)
- F Stereo detune

## Sub (4: sine, warm, pulse, fm)

The four sub engines share one set of controls.
- A ★ Character: sine harmonics / warm octave / pulse width / fm growl
- B ★ Body (low-pass)
- C Saturation (default 0 on sine: a pure sine; up, the soft harmonics small speakers hear)
- D Bar pulse depth
- E FM growl rate (fm only)
- F Pulse filter (pulse only, now fixed at 220 Hz × 2)

## Pads (15)

**fm** (redesigned): a 4-operator FM engine (operators A B C D, A always a carrier), shared by the drone and the pads
- Algorithm (how the operators connect; 2 to 4 operators sound):
  1. 2-op: B → A
  2. 3-op stack: C → B → A
  3. 4-op stack: D → C → B → A
  4. three into one: B + C + D → A
  5. two pairs: B → A and D → C (two carriers, one per side, or blended)
  6. stack and sine: C → B → A, with D as a pure carrier underneath
- Ratio B, Ratio C, Ratio D (each snapping to useful ratios: 0.5, 1, 1.5, 2, 3, 3.5, 4, 5, 7, plus fine detune)
- Index B, Index C, Index D (how much each modulator modulates)
- Feedback on the top operator (sine → saw-like → noisy)
- Index envelope: the indexes brighter at each note's start and settling (attack depth, decay time)

**vox**: a saw through two vowel formants
- A ★ Vowel
- B ★ Resonance
- C Formant drift rate
- D Formant drift depth
- E Body level (the low end under the formants)
- F Brightness (b)

**part**: 4 additive partials
- A ★ Spread (upper partial level)
- B ★ Swell depth
- C Partial set (choose the ratios: harmonic, stretched, bell, odd...)
- D Swell rate
- E Tilt (b)
- F Stereo spread

**fold**: a wavefolder
- A ★ Fold
- B ★ Sub (ring modulation with the sub-octave)
- C Symmetry (now fixed at −0.25)
- D Low-pass (now fixed at 5000 Hz)
- E Stereo fold difference
- F Fold from brightness (b)

**pulsr**: pulsar synthesis
- A ★ Formant
- B ★ Cycles (sine cycles per burst)
- C Formant drift rate
- D Formant drift depth
- E Stereo formant offset (now fixed at 1.18)
- F Brightness (b)

**saws**: three detuned saws through a tracking low-pass
- A ★ Detune
- B ★ Filter (cutoff)
- C Resonance (now fixed at 1.6)
- D Filter key / brightness tracking (b)
- E Saw mix / stereo spread
- F Filter envelope amount (new)

**pwm**
- A ★ Width modulation depth
- B ★ Sweep (filter LFO depth)
- C PWM rate
- D Base width
- E Cutoff (b)
- F Resonance (now fixed at 2.5)

**sync**
- A ★ Sync ratio
- B ★ Sweep depth
- C Sweep rate
- D Stereo offset (now fixed at 0.11)
- E Low-pass (now fixed at 4500 Hz)
- F Sync envelope (the sweep on each note, new)

**sine** (redesigned): a pure sine, with harmonics added only when you ask
- Harmonics: 0 = a pure sine (the default), up = harmonics 2 to 8 fade in
- Slope: how fast the upper harmonics fall off (gentle 1/n, like a saw, ↔ steep, close to the sine)
- Odd / even: odd only (hollow, clarinet-like) ↔ both ↔ even only (octave-bright)
- Count: the highest harmonic, 2 to 8
- Chorus: 0 = none (the default); up = a second, detuned sine on the right
- Drawbar mode (alternative): the 4 knobs set the levels of harmonics 2, 3, 4 and 5 directly

**glass**: morph between two wavetables
- A ★ Morph
- B ★ Shimmer (octave above)
- C Drift rate (now fixed at 0.08 Hz)
- D Drift depth
- E Stereo detune

**cz**: Casio CZ-style phase distortion
- A ★ Bend
- B ★ Resonance
- C Sweep rate
- D Sweep depth
- E Left / right wave blend
- F Low-pass

**choir**: glottal pulses through three formants
- A ★ Vowel
- B ★ Breath
- C Vowel drift rate
- D Vibrato depth / rate
- E Formant Q
- F Stereo detune

**vosim**
- A ★ Formant
- B ★ Decay (of the pulse train)
- C Formant sweep depth
- D Stereo formant interval (now a 3rd)
- E Pulses per period (now 3)

**lissa**: Lissajous, the note left and its fifth right
- A ★ Ratio
- B ★ Turn (phase rotation speed)
- C Harmonics (b)
- D Crossfeed (now 0.25)

**chip**: console pulse and triangle
- A ★ Duty
- B ★ Crush (sample rate)
- C Vibrato depth
- D Vibrato delay
- E Duty step rate
- F Pulse / triangle blend (b)

## Percussive layer (5)

**Shared by all 5 engines (not part of the 4):**
- Decay: a new absolute range of about 50 ms to 30 s. Today's maximums are short: wood about 2 s, blip about 2.7 s,
  lpg about 4.5 s, metal about 11 s, bowl about 21 s.
- Velocity sensitivity
- Pitch / octave
- Voices (now 3 to 4 in rotation; more voices let long decays overlap)

**lpg**: West-coast pluck: a sine through a wavefolder and a low-pass gate
- A ★ Fold
- B Fold decay (how fast the fold falls back)
- C Filter opening (now 6 kHz at full strike)
- D Resonance (now 0.8)
- E Vactrol response (how slowly the gate closes)
- F Gate time vs level time (filter closing ahead of the level)

**bowl**: singing bowl modes
- A ★ Hardness (upper modes and strike)
- B Beating rate (the twin modes, now 0.6 / 1.1 Hz)
- C Mode stretch (bowl → bell → plate)
- D Strike noise level
- E Strike band (mallet brightness)
- F Upper mode decay (relative to the fundamental)

**wood**: mallet knock and marimba modes
- A ★ Mallet (strike brightness)
- B Material (mode ratios: marimba ↔ woodblock ↔ log drum)
- C Knock level
- D Knock band (now 2.5 × the note)
- E Upper mode decay

**blip**: a filtered analog blip
- A ★ Cutoff
- B Pitch flick amount (now a 5th)
- C Pitch flick time (now 14 ms)
- D Resonance (now 4)
- E Sub level (now 0.35)
- F Filter envelope time

**metal**: vibraphone modes with a beating twin and motor tremolo
- A ★ Bright (in the original this knob is wired to nothing for metal: a bug)
- B Beat rate (the twin, now 0.8 Hz)
- C Tremolo rate (now 5.2 Hz)
- D Tremolo depth (now 0.2)
- E Mode ratios (vibraphone ↔ glockenspiel ↔ tubular)

## Cloud (granular)

- A ★ Grain length
- B ★ Spread (stereo)
- C Density (now 4 streams)
- D Pitch set (transposition ratios: unison, octaves, fifths, the chord)
- E Reverse chance
- F Position (scan through the buffer instead of random)
- G Jitter (position randomness)
- H Source: engine output / input / both
