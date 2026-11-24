AMBLE LITE
==========

Drone, sub, pads and percussion for real-time building. Loads silent: top C starts and stops.

ORGANELLE KEYS (one press each)
  low C    show the DRONE
  low C#   mute the drone
  low D    show the SUB
  low D#   mute the sub
  low E    show the PADS
  low F    show a PERC lane (again: the next lane)
  low F#   mute the pads
  low G    the MAIN / STORY / SYNC / PERFRM pages (again: the next one)
  low G#   mute the percussion lane last shown
  low A    page back
  low A#   latch on / off for the shown layer (PERC: its pattern)
  low B    page forward
  top C    start / stop
  top C#   clear the shown layer (back to its default)
  top D    previous chord
  top D#   the shown layer's looper: record, then play, overdub, play ...
  top E    next chord
  top F    the play view (back from MIX / pattern)
  top F#   the shown layer's loop: stop / play
  top G    the MIX view: knobs set levels (again: the next mix page); its top line shows the CPU (cpu: this second, pk: the highest of the last ten, % of one core)
  top G#   clear the shown layer's loop
  top A    the pattern view on / off: every gate and lane as steps
  top B    notes mode: the Organelle keys play the shown layer (again: back to functions)
  top A#   held + a key from low C to top D#: recall snapshot 1 - 16 (with aux: save it);
           tapped alone: COMPARE (back to the sound before the recall; again: forward)

AUX held + key
  low C    show the DRONE
  low D    show the SUB
  low E    show the PADS
  low F    show a PERC lane (again: the next lane)
  low A    page back
  low B    page forward
  top C    start / stop
  top B    notes mode: the Organelle keys play the shown layer (again: back to functions)
  aux tap  page forward
  aux held + a knob: ASSIGN - that knob's place on the FAV page takes a
           parameter of the layer (the knob chooses which)

KNOBS: the 4 parameters of the page on screen. A knob takes over once it passes the stored value.

PAGES of each layer: LAYER (engine, level, cutoff, reso), ENV (attack, decay, sustain, release) or HIT
(decay, velocity, octave, spread), PLAY (articulation, glide, octave, pan) or RHYTHM (hits, steps,
rotate, rate), EVOLVE (evolve, pace, sync, drift), then the engine's parameters, 4 a page.

EVOLVE: each layer changes slowly by itself - its engine's character, the filter, a breathing in level
(pads: each voice its own) - on slow cycles that phase against each other: never static, never random.
Evolve 0 = still; Pace: 5 minutes .. 25 s a cycle; EvSync: free or locked to the clock; Drift: a slight
pitch wander (0 = exact). The master Evolve (PERFRM page) scales every layer's.

LFO 1 / 2: Target (any of the layer's parameters: filter, level, place, envelopes, gate length,
swing, the engine's), Rate (loop = one cycle per loop or pattern cycle; bars; Hz), Depth, Shape (sine,
tri, saw up / down, square, steps, random smooth, random stepped: a new value each cycle).

LOOP: Len (auto: rounded to bars; free: as played; or 1 - 16 bars), Quant, Follow (chord: the loop
moves with the chord story; exact), Vel. Records what you play into the layer.

GATE: each gate has its own envelope (GATENV). FEEL: Swing and its feel (swing, lilt, drag, limp) on
the gates and the lanes. MORPH (PERFRM page): how long a recalled snapshot glides (0 = at once).

ARTICULATION: artic (every note restarts), legato (overlapping notes don't), porta (overlapping notes
slide), slide (every note slides). Glide sets the slide time.

MIDI: channel 1 plays the shown layer; 2 drone, 3 sub, 4 pads, 5 - 8 percussion lanes. Clock in (SYNC: ext)
and out (SYNC: ClkOut).

THE CHORD STORY (STORY page): a progression in the key and mode, the pads, sub and percussion
following it; Bars sets how often it moves on (manual: top D / top E).

ENGINES
  DRONE  analog, fm, spectr
  SUB    sine, warm, pulse, fm
  PAD    sine, fm, saws, pwm, wave
  PERC   blip, lpg, bowl, wood, metal
