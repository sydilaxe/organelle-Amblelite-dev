AMBLE LITE
==========

Drone, sub, pads and four percussion lanes for real-time building. Loads silent: top C starts and stops.

THE LAYERS: the low white keys, one each. A tap: the layer in / out (it fades over the PERFRM page's
Fade time; out, a loop keeps its place, silent). Held (400 ms): its parameter pages.
AUX TAPPED: home - the play view, from any page or view. Pages you open stay until then; the page a
knob pops up in the play view closes 3 s after the last turn.
  low C    DRONE
  low D    SUB
  low E    PADS
  low F    PERC1
  low G    PERC2
  low A    PERC3
  low B    PERC4
  top G    CLOUD

THE OTHER KEYS (one press each): the low black keys the views, the top octave playing
  low C#   the play view (back from MIX / pattern / pages)
  low D#   the MIX view: knobs set levels (again: the next mix page); its top line shows the CPU (cpu: this second, pk: the highest of the last ten, % of one core)
  low F#   the pattern view (every gate and lane as steps), then the roadmap view, then neither
  low G#   the global pages: MAIN (key, tempo, scale, mode), LAYERS and LANES (each layer's engine), STORY, SYNC, MIDI, MIDI 2, PERFRM, HARMNY, ROAD, ROAD 2, SECTN (again: the next one)
  low A#   page forward
  top C    start / stop
  top C#   clear the shown layer (back to its default)
  top D    previous chord
  top D#   the shown layer's looper: record, then play, overdub, play ...
  top E    next chord
  top F    page back
  top F#   the shown layer's loop: stop / play
  top G#   clear the shown layer's loop
  top A    latch on / off for the shown layer (drone, sub, pads)
  top B    notes mode: the Organelle keys play the shown layer (again: back to functions)
  top A#   held + a key from low C to top D#: recall snapshot 1 - 16 (with aux: save it);
           tapped alone: COMPARE (back to the sound before the recall; again: forward)

AUX held + key
  low C    show the DRONE pages
  low D    show the SUB pages
  low E    show the PADS pages
  low F    show the PERC1 pages
  low G    show the PERC2 pages
  low A    show the PERC3 pages
  low A#   page back
  low B    show the PERC4 pages
  top C    start / stop
  top C#   build the roadmap (the ROAD page's settings)
  top D    clear your own story
  top E    the HARMNY page's suggestion: played now, added to your own story
  top F#   hold the roadmap's section (again: let it go)
  top G    show the CLOUD pages
  top G#   the roadmap's next section
  top B    notes mode: the Organelle keys play the shown layer (again: back to functions)
  aux tap  home: the play view
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
moves with the chord story; exact), Vel. Records what you play into the layer, and its breath.

GATE: each gate has its own envelope (GATENV). FEEL: Swing and its feel (swing, lilt, drag, limp) on
the gates and the lanes. MORPH (PERFRM page): how long a recalled snapshot glides (0 = at once).

ARTICULATION: artic (every note restarts), legato (overlapping notes don't), porta (overlapping notes
slide), slide (every note slides). Glide sets the slide time.

MIDI (the MIDI and MIDI 2 global pages):
  Chans layers: channel 1 plays the shown layer; 2 drone, 3 sub, 4 pads, 5 - 8 perc 1 - 4, 9 cloud.
  Chans mpe: every channel plays, each note its own pitch bend (Bend: its range) and pressure (Press:
  expr = the note's level, breath = the breath) - the DM48X.
  Zones on: the keyboard split - a note goes to the first layer whose zone (its BREATH page: ZoneLo,
  ZoneHi) holds it. Each zone's breath shapes its own layer, and the loop key then records every zoned
  layer at once: their notes and their breath.
  BREATH page (each layer): Target (any of its parameters) and Depth.
  Profil: the controller - generic, nanokey (nanoKEY Studio), nanoktl (nanoKONTROL Studio), dm48x, user -
  read from controllers/<name>.txt: 'cc <n> <action> [arg];' or 'note <ch> <n> <action> [arg];'. Actions:
  knob 1-8, level / toggle / show <layer 1-8>, breath, start, stop, startstop, chordnext, chordprev,
  loop, loopstop, loopclear, pgnext, pgprev, play, mix, pattern. LastCC shows the last CC that came in;
  controllers/user.txt is kept when a new version is copied over.
  Clock in (SYNC: ext) and out (SYNC: ClkOut).

SCALES (MAIN page): Scale picks the family - modes (the seven church modes), harmin (harmonic minor),
melmin (melodic minor), pent (pentatonic) - and Mode which of its modes, by name (dorian, phrdom ...).
Everything follows them: the chords, the lanes' scale runs, the counterpoint and the suggestions.

THE CHORD STORY (STORY page): a progression in the key and mode, the pads, sub and percussion
following it; Bars sets how often it moves on (manual: top D / top E).

ENGINES
  DRONE  analog, fm, spectr, frost, choir, bowed, gendy
  SUB    sine, warm, pulse, fm
  PAD    sine, fm, saws, pwm, wave, vox, part, fold, pulsr, sync, cz, choir, vosim, lissa, chip, vector
  PERC   blip, lpg, bowl, wood, metal, wave
