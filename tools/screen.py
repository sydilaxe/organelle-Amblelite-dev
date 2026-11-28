"""The OLED (128 x 64), drawn with /oled/g* messages to mother ([s oscOut]). Words come from al-words.txt (one per
line: control.words()), so the screen never builds strings at run time.

PLAY (home)                                  LAYER (5 s after a knob turns or a page changes)
  y 0   key mode tempo RUN/STOP [NOTES]        y 0   layer and engine (or GLOBAL)
  y 11  chord > next chord                     y 11  page name and its place (2/5)
  y 22-52  a row per layer: > selected,        y 22-52  the 4 knobs: name, value, a bar
        name, engine, + / M (muted), level bar
Redraws are throttled: at most one every 60 ms, however fast knobs turn."""
from pdlib import Canvas, proc, If, Call, SendL, Send, run_steps, T, Arm
import model as M
from model import S, LAYERS
from control import words, opt, num, ctx, npages, clocks, QUALS, MODE_SLOT, VIEW_GLOBAL, VIEW_MIX

OSC = "oscOut"


def Fill(x, y, w, h, c=1):
    return SendL(OSC, [str(x), str(y), str(w), str(h), str(c)], "/oled/gFillArea 3 $1 $2 $3 $4 $5")


def gen_dz():
    import gen
    return gen.FILTER_DZ


def _sym(c, w, dest):
    """a word as a symbol (a word that reads as a number - an option like 0.5 or 16 - comes out of [text get] as a
    float)"""
    r = c.to(w, "route float symbol")
    c.c(c.to(r, "makefilename %g"), 0, dest[0], dest[1])
    c.c((r, 1), 0, dest[0], dest[1])


def row(c, name, x, y, parts):
    """[r name] -> a line of words at x, y. parts: ('w', line_expr) a word of al-words; ('n', expr, fmt) a number;
    ('v', k) knob k's value (a word for a choice, else a number)"""
    sc = Canvas(name, w=1600)
    c.sub(sc)
    n = len(parts)
    t = sc.ch(sc.recv(name), "t " + " ".join(["b"] * n))
    pk = sc.obj("pack " + " ".join(["s"] * n))
    for i, p in enumerate(parts):
        src = (t, i)          # (t fires right to left: the first word, the hot inlet, last)
        if p[0] == "w":
            w = sc.ch(sc.to(src, "expr " + p[1]), "text get al-words")
            _sym(sc, w, (pk, i))
        elif p[0] == "n":
            sc.c(sc.ch(sc.to(src, "expr " + p[1]), f"makefilename {p[2]}"), 0, pk, i)
        else:
            k = p[1]
            sl = f"alsl{k}"
            # (an LFO's target: the name of the parameter it moves, or 'off')
            tgi = M.target_index(f"alp[{sl}]", f"allayer*{M.MAXENG} + aleng[allayer]")
            tg = M.target_slot(f"alp[{sl}]", f"allayer*{M.MAXENG} + aleng[allayer]")
            sug = S("g", None, "Sugg")
            so = f"min(3, int(alp[{sug}]*4))"
            mode_w = f"{OFF['mode']} + {opt(MODE_SLOT)}"          # (the Mode knob: its mode's name)
            # (the cloud delay's Time, synced: the subdivision it picks)
            import cloud as _cl
            dt, dsy = S("cloud", "delay", "Time"), S("cloud", "delay", "Sync")
            dly = f"if({sl} == {dt} && alp[{dsy}] >= 0.5, {OFF['ddiv']} + {_cl.delay_div()}, "
            wl = sc.to(src, f"expr {dly}if({sl} == {MODE_SLOT}, {mode_w}, if({sl} == {sug}, {OFF['chord']} + alsuR[{so}]*{len(QUALS)} + altq[alsuT[{so}]], "
                            f"if({sl} < 0, {OFF['misc']}, if(aln[{sl}] == -2, if({tgi} == 0, {OFF['off']}, "
                            f"if({tg} < 0, {OFF['misc']}, {OFF['name']} + {tg})), if(aln[{sl}] > 0, {OFF['opt']} + "
                            f"alob[{sl}] + min(aln[{sl}] - 1, int(alp[{sl}]*aln[{sl}])), -1))))))")
            mo = sc.to(wl, "moses 0")
            _sym(sc, sc.ch((mo, 1), "text get al-words"), (pk, i))
            # (SHAPE's Filter: its place from the middle - minus: low-pass, plus: high-pass, 0 in the neutral zone)
            fsl, dz = S("g", None, "Filter"), gen_dz()
            fpos = (f"if(abs(alp[{sl}] - 0.5) <= {dz}, 0, if(alp[{sl}] < 0.5, -int((0.5 - alp[{sl}])*100 + 0.5), "
                    f"int((alp[{sl}] - 0.5)*100 + 0.5)))")
            nv = sc.to(sc.to((mo, 0), "t b"),
                       f"expr if({sl} == {fsl}, {fpos}, if(aln[{sl}] < 0, int(allo[{sl}] + alp[{sl}]*(alhi[{sl}] - allo[{sl}]) + 0.5), "
                       f"int(alp[{sl}]*100 + 0.5)))")
            sc.c(sc.to(nv, "makefilename %d"), 0, pk, i)
    lp = sc.ch(pk, f"list prepend /oled/gPrintln 3 {x} {y} 8 1", "list trim")
    sc.c(lp, 0, sc.obj("s " + OSC), 0)


LINES, OFF = words()


def chord_words():
    """every chord name (12 roots x QUALS), appended to al-words"""
    return [n + q for n in M.NOTE_NAMES for q in QUALS]


OFF["chord"] = len(LINES)
LINES += chord_words()
OFF["frac"] = len(LINES)
LINES += [f"{p}/{n}" for n in range(1, M.MAXPAGES + 1) for p in range(1, M.MAXPAGES + 1)]
MISC = {"-": 0, "RUN": 1, "STOP": 2, "M": 3, ">": 4, "NOTES": 5, "LAT": 6, "RUN*": 7, "STOP*": 8, "N": 9}
LINES.append("+")
OFF["plus"] = len(LINES) - 1
LINES.append("GLOBAL")
OFF["global"] = len(LINES) - 1
LINES.append("off")
OFF["off"] = len(LINES) - 1
OFF["ddiv"] = len(LINES)                    # (the cloud delay's subdivisions: its Time, synced)
LINES += [n for n, _ in M.DELAY_DIVS]
LINES.append("out")
OFF["out"] = len(LINES) - 1
from features import TOASTS
OFF["toast"] = len(LINES)
LINES += TOASTS
OFF["loopst"] = len(LINES)
LINES += ["+", "R", "P", "O", "s"]          # a layer's loop: none, recording, playing, overdub, stopped
for _w in ("road", "hold", "next"):
    OFF[_w] = len(LINES)
    LINES.append({"road": "ROAD", "hold": "HOLD", "next": "next:"}[_w])
OFF["role"] = len(LINES)
LINES += M.ROLES
OFF["lanes"] = len(LINES)
LINES += ["".join(str(i + 1) if b & (1 << i) else "." for i in range(len(M.LANES))) + ("c" if b & 16 else "")
          for b in range(2 ** (len(M.LANES) + 1))]


def misc(w):
    return str(OFF["misc"] + MISC[w])


PAT_X, PAT_W = 16, 7         # the pattern view: cells from x 16, 7 pixels each (16 steps)
MIX_X0, MIX_DX, MIX_W = 1, 13, 9    # the MIX view's columns (the 8 layers; the master volume at x 112)
# the play view: the roadmap strip, then the layer tiles (8 across, x 0 .. 118), a bar under the shown one, the
# loops' states under that
INFO_Y, ROAD_Y, ROAD_H = 22, 32, 7
TILE_DX, TILE_W, TILE_Y, TILE_H = 15, 13, 36, 11
ICON_Y, LABEL_Y = 45, 54


def layer_icon(L, cx, cy):
    """a layer's icon on the play view: (steps when it is in - bold or filled, steps when out - a thin outline).
    drone a triangle; sub a wave; pads two circles (a figure of eight: their Lissajous in the visualizer); a lane a
    stone's ring with the stone; the cloud a square"""
    def ln(pts, dy=0):
        return [Send(OSC, f"/oled/gLine 3 {x1} {y1 + dy} {x2} {y2 + dy} 1") for (x1, y1), (x2, y2) in zip(pts, pts[1:])]
    circ = lambda r, fill=False, dx=0: Send(OSC, f"/oled/{'gFilledCircle' if fill else 'gCircle'} 3 {cx + dx} {cy} {r} 1")
    k = M.kind(L)
    if L == "drone":            # (apex up, 11 px wide and tall; filled: a line a row)
        tri = [(cx, cy - 5), (cx + 5, cy + 5), (cx - 5, cy + 5), (cx, cy - 5)]
        rows = [Send(OSC, f"/oled/gLine 3 {cx - k // 2} {cy - 5 + k} {cx + k // 2} {cy - 5 + k} 1") for k in range(11)]
        return rows, ln(tri)
    if L == "sub":
        wave = [(cx - 6, cy), (cx - 4, cy - 3), (cx - 1, cy + 3), (cx + 2, cy - 3), (cx + 5, cy + 3), (cx + 6, cy)]
        return ln(wave) + ln(wave, 1), ln(wave)
    if L == "pad":
        return [circ(3, True, -3), circ(3, True, 3)], [circ(3, False, -3), circ(3, False, 3)]
    if L == "cloud":
        return [Fill(cx - 5, cy - 5, 11, 11, 1)], [Send(OSC, f"/oled/gBox 3 {cx - 5} {cy - 5} 11 11 1")]
    return [circ(5), circ(1, True)], [circ(4)]                 # (a lane)
PAT_LAYERS = M.NOTE_LAYERS          # the pattern view's rows (the cloud has no pattern)


def rows_tables(c):
    """per pattern-view row (the 7 layers): the slots of its pattern, so one loop draws them all"""
    import model as M
    sl = lambda n: [S(L, None, n) for L in PAT_LAYERS]
    tabs = dict(alrh=sl("Hits"), alrs=sl("Steps"), alro=sl("Rotate"), alrr=sl("Rate"),
                alrg=[S(L, None, "Gate") if L in ("drone", "sub", "pad") else -1 for L in PAT_LAYERS],
                alrp=[S(L, None, "Patt") if L in M.LANES else -1 for L in PAT_LAYERS])
    for name, vals in tabs.items():
        c.obj(f"array define {name} {len(vals)}")
        c.c(c.m(c.recv("al-init"), " ".join(str(v) for v in vals)), 0, c.obj(f"array set {name}"), 0)


def build(c):
    from pdlib import V, Loop
    c.comment("the screen: al-redraw (any change) -> at most every 60 ms (120 while the CPU is above 70 %) -> al-draw")
    sp = c.obj("spigot 1")
    c.c(c.ch(c.recv("al-redraw"), "t b"), 0, sp, 0)
    tb = c.to(sp, "t b b b")
    c.c(c.m((tb, 2), "0"), 0, sp, 1)
    # (fewer frames when busy: the OLED's messages travel to its program on the same core - under load some are
    # lost or late, and half-drawn frames show as lines; the sound is never slowed by the screen)
    dl = c.obj("delay 60")
    c.c(c.to((tb, 1), "expr if(alcpu > 70, 120, 60)"), 0, dl, 1)
    c.c((tb, 0), 0, dl, 0)
    d = c.to(dl, "t b b")
    c.c(c.m((d, 1), "1"), 0, sp, 1)
    c.c(d, 0, c.obj("s al-draw"), 0)
    lb = c.ch(c.recv("al-init"), "t b")
    c.c(c.m(lb, "/oled/gShowInfoBar 3 0"), 0, c.obj("s " + OSC), 0)
    rows_tables(c)
    tempo, key, mode = S("g", None, "Tempo"), S("g", None, "Key"), S("g", None, "Mode")
    nl = len(M.LANES)
    fl = LAYERS.index(M.LANES[0])
    # ---- play view
    row(c, "al-r-head", 0, 0, [("w", f"{OFF['note']} + {opt(key)}"), ("w", f"{OFF['mode']} + {opt(mode)}"),
                               ("n", num(tempo), "%d"), ("w", f"if(alrun, {misc('RUN')}, {misc('STOP')}) + 6*alchg")])      # (*: changed since the snapshot)
    # (at most 21 characters - the small font is 6 px a character, and a longer line wraps: so the tempo without
    # 'bpm'; notes mode is an N at the right edge, below)
    row(c, "al-r-chord", 0, 11, [("w", f"{OFF['chord']} + alcr*{len(QUALS)} + alcq"), ("w", misc(">")),
                                 ("w", f"{OFF['chord']} + alnxr*{len(QUALS)} + alnxq")])
    # the layers as tiles (D S P 1 2 3 4 C): in - filled from the bottom as high as its Level; out - an empty outline.
    # Under each its letter (the shown layer's inverted), and a loop's state (R recording, P playing, O overdub,
    # s stopped). The right edge: the MIDI-in light, N in notes mode
    for li in range(len(M.NOTE_LAYERS)):
        row(c, f"al-r-lp{li}", TILE_DX * li + 8, LABEL_Y, [("w", f"{OFF['loopst']} + allps[{li}]")])
    row(c, "al-r-toast", 0, 0, [("w", f"{OFF['toast']} + altw"), ("n", "altn", "%d")])
    row(c, "al-r-toast0", 0, 0, [("w", f"{OFF['toast']} + altw")])
    play = [If("altw >= 0", [If("altn >= 0", [Call("al-r-toast")], [Call("al-r-toast0")])], [Call("al-r-head")]),
            Call("al-r-chord")]
    for li, L in enumerate(LAYERS):
        x = TILE_DX * li
        lab = M.SHORT[L][1] if M.kind(L) == "perc" else M.SHORT[L][0]
        on, off = layer_icon(L, x + TILE_W // 2, ICON_Y)
        if M.kind(L) == "perc":
            # (a lane: its ring, and the stone in it - the centre dot - lit while a hit's gate is open: half its step)
            lane = M.LANES.index(L)
            on = [on[0], If(f"alhitp[{lane}]", [on[1]])]
        if L in ("drone", "sub", "pad"):
            # (its gate's rhythm playing: the icon flashes with it - shown while the gate is open, gone between)
            on = [If(f"alrun && {opt(S(L, None, 'Gate'))} >= 1 && algt[{li}] == 0", [], on)]
        # (a loop: recording or overdubbing (allps 1, 3) - the sign blinks on the 8ths; playing or overdubbing
        # (2, 3) - a line under it fills as the loop goes round; stopped (4) - a dot there)
        sign = [If(f"alin[{li}]", on, off)]
        if li < len(M.NOTE_LAYERS):
            ph = f"((max(0, alc24) - allp0[{li}]) % max(1, allpl[{li}]))/max(1, allpl[{li}])"
            sign = [If(f"(allps[{li}] == 1 || allps[{li}] == 3) && int(max(0, altick)/4) % 2", [], sign),
                    If(f"(allps[{li}] == 2 || allps[{li}] == 3) && allpl[{li}] > 0",
                       [SendL(OSC, [f"max(1, int({ph}*{TILE_W}))"], f"/oled/gFillArea 3 {x} {ICON_Y + 6} $1 1 1")]),
                    If(f"allps[{li}] == 4", [Fill(x + TILE_W // 2, ICON_Y + 6, 1, 1, 1)])]
        play += sign + [
                 Send(OSC, f"/oled/gPrintln 3 {x + 2} {LABEL_Y} 8 1 {lab}"),
                 If(f"allayer == {li}", [Send(OSC, f"/oled/gInvertArea 3 {x} {LABEL_Y - 1} 8 9")])]     # (the letter only: a loop's beside it stays clear)
        if li < len(M.NOTE_LAYERS):
            play += [If(f"allps[{li}] > 0", [Call(f"al-r-lp{li}")])]
    play += [If("alnotes", [Send(OSC, f"/oled/gPrintln 3 121 {LABEL_Y} 8 1 N")])]
    # the roadmap, when there is one and Road isn't off: an info line (the section n/count; the time left, counting
    # down, and the piece's whole length) and the roadmap as a strip
    road = S("g", None, "Road")
    tempo_ = S("g", None, "Tempo")
    secs = f"*240/{num(tempo_)}"            # (bars to seconds: 4 beats a bar)

    def clock(x_end, var, minus):
        """m:ss of var seconds, right-aligned to x_end (6 px a character): one message - the minutes, then the
        seconds' two digits"""
        w = f"(altcm >= 10) + {4 + (1 if minus else 0)}"
        return [V("altcm", f"int({var}/60)"), V("altcs", f"int({var}) % 60"),
                SendL(OSC, [f"{x_end} - 6*({w})", "altcm", "int(altcs/10)", "altcs % 10"],
                      f"/oled/gPrintln 3 $1 {INFO_Y} 8 1 {'-' if minus else ''}$2:$3$4")]
    play += [If(f"alrn > 0 && {opt(road)} > 0", [
        V("alrtot", "0"), V("alrsw", "0"),
        Loop("alrn", "alri", [If("alri < alrc", [V("alrsw", "alrsw + alrsL[alri]")]), V("alrtot", "alrtot + alrsL[alri]")]),
        V("alrsw", "alrsw + min(alrsL[alrc], max(0, altick/32 - alrb0))"),
        # (the info line: the section n/count, then the time left in the piece and its whole length)
        SendL(OSC, ["alrc + 1", "alrn"], f"/oled/gPrintln 3 0 {INFO_Y} 8 1 $1/$2"),
        *clock(92, f"max(0, alrtot - alrsw){secs}", True), *clock(128, f"alrtot{secs}", False),
        # (each section a box as wide as its bars - the playing one filled - and the playhead: an inverted line)
        V("alrt", "alrsw"), V("alrsw", "0"),
        Loop("alrn", "alri", [
            If("alri == alrc", [SendL(OSC, ["int(alrsw*127/alrtot)", "max(2, int(alrsL[alri]*127/alrtot))"],
                                      f"/oled/gFillArea 3 $1 {ROAD_Y} $2 {ROAD_H} 1")],
               [SendL(OSC, ["int(alrsw*127/alrtot)", "max(2, int(alrsL[alri]*127/alrtot) + 1)"],
                      f"/oled/gBox 3 $1 {ROAD_Y} $2 {ROAD_H} 1")]),
            V("alrsw", "alrsw + alrsL[alri]")]),
        SendL(OSC, ["min(126, int(alrt*127/alrtot))"], f"/oled/gInvertArea 3 $1 {ROAD_Y + 2} 2 {ROAD_H - 4}")])]
    # the MIDI-in light: a small square at the bottom right, on while a MIDI note is held (and 150 ms after each)
    play += [If("alminh > 0 || altime - almint < 0.15", [Fill(122, ICON_Y - 2, 5, 5, 1)])]
    # ---- layer view
    lay = [If(f"alview == {VIEW_MIX}", [Send(OSC, "/oled/gPrintln 3 0 0 8 1 MIX")],
              [If("alview", [Call("al-r-ghead")], [Call("al-r-lhead")])]), Call("al-r-page")]
    row(c, "al-r-ghead", 0, 0, [("w", f"{OFF['global']}")])
    row(c, "al-r-lhead", 0, 0, [("w", f"if(alview, {OFF['global']}, {OFF['layer']} + allayer)"),
                                ("w", f"if(alview, {misc('-')}, {eng_word('allayer')})")])
    row(c, "al-r-page", 0, 11, [("w", f"{OFF['page']} + {ctx()}*{M.MAXPAGES} + alpage"),
                                ("w", f"{OFF['frac']} + ({npages()} - 1)*{M.MAXPAGES} + alpage")])
    for k in range(4):
        # (a global page's knob that is a layer's: the layer's name)
        gl = f"algl[alpage*4 + {k}]"
        row(c, f"al-r-k{k}", 0, 22 + 10 * k, [("w", f"if(alsl{k} < 0, {misc('-')}, if(alview == {VIEW_GLOBAL} && {gl} >= 0, "
                                                    f"{OFF['layer']} + {gl}, {OFF['name']} + alsl{k}))"),
                                              ("v", k)])
        fsl = S("g", None, "Filter")
        y = 23 + 10 * k
        # (SHAPE's Filter: a mark at the middle, its bar from there to the left (low-pass) or the right (high-pass))
        fpx = f"(80 + int(alp[{fsl}]*46))"
        lay += [Call(f"al-r-k{k}"),
                If(f"alsl{k} == {fsl}", [Fill(103, y - 1, 1, 7, 1),
                                         SendL(OSC, [f"min(103, {fpx})", f"max(1, abs({fpx} - 103))"],
                                               f"/oled/gFillArea 3 $1 {y + 1} $2 3 1")],
                   [If(f"alsl{k} >= 0 && (aln[alsl{k}] == 0 || aln[alsl{k}] == -1)",
                       [SendL(OSC, [str(y), f"max(1, int(alp[alsl{k}]*46))"],
                              "/oled/gFillArea 3 80 $1 $2 5 1")])])]
    # ---- mix view: every layer's level as a column, the master volume at the right; the shown page's columns
    # underlined
    row(c, "al-r-mixhead", 0, 0, [("w", f"{OFF['page']} + {ctx()}*{M.MAXPAGES} + alpage"),
                                  ("w", f"{OFF['frac']} + ({npages()} - 1)*{M.MAXPAGES} + alpage"),
                                  ("n", "alcpu", "cpu%d"), ("n", "alcpux", "pk%d")])
    # the CPU meter: Pd's own CPU time over each second of its time, as a share of one core (the patch runs on one);
    # the peak: the highest second of the last ten. While the MIX view shows, it redraws every second.
    met = c.obj("metro 1000")
    c.c(c.m(c.recv("al-init"), "1"), 0, met, 0)
    cb = c.to(met, "t b b")
    ct = c.obj("cputime")
    c.c((cb, 1), 0, ct, 1)          # (the second's CPU time read, then the count restarted)
    c.c((cb, 0), 0, ct, 0)
    c.c(c.ch(ct, "expr min(100, int($f1/10 + 0.5))"), 0, c.obj("s al-cpu"), 0)
    cpu_in = c.ch(c.recv("al-cpu"), "t f f")
    c.c((cpu_in, 1), 0, c.obj("v alcpu"), 0)
    from pdlib import V as _V
    run_steps(c, (c.to(cpu_in, "t b"), 0), [
        _V("alcpuh", "alcpuh + 1"), _V("alcpux", "if(alcpuh % 10 == 1, alcpu, max(alcpux, alcpu))"),
        If("alview == 2", [Call("al-redraw")])])
    mixv = [Call("al-r-mixhead")]
    for li, L in enumerate(LAYERS):
        lvl = S(L, None, "Level")
        x = MIX_X0 + MIX_DX * li
        # (a layer out: its column hollow)
        mixv += [If(f"alin[{li}]", [SendL(OSC, [f"{x}", f"52 - int(alp[{lvl}]*38)", f"max(1, int(alp[{lvl}]*38))"],
                                          f"/oled/gFillArea 3 $1 $2 {MIX_W} $3 1")],
                    [SendL(OSC, [f"{x}", f"52 - int(alp[{lvl}]*38)", f"max(2, int(alp[{lvl}]*38))"],
                           f"/oled/gBox 3 $1 $2 {MIX_W} $3 1")]),
                 If("almixok == 0", [Send(OSC, f"/oled/gPrintln 3 {x} 55 8 1 {M.SHORT[L][1] if M.kind(L) == 'perc' else M.SHORT[L][0]}")])]
    vol = S("g", None, "Volume")
    mixv += [SendL(OSC, [f"52 - int(alp[{vol}]*38)", f"max(1, int(alp[{vol}]*38))"], "/oled/gFillArea 3 112 $1 14 $2 1")]
    mixv += [If("almixok == 0", [Send(OSC, "/oled/gPrintln 3 114 55 8 1 V")]), V("almixok", "1")]
    # (the columns the knobs turn now: a line under them)
    for k in range(4):
        terms = " + ".join(f"(alsl{k} == {S(L, None, 'Level')})*{li}" for li, L in enumerate(LAYERS))
        col = f"if(alsl{k} == {vol}, 112, {MIX_X0} + {MIX_DX}*({terms}))"
        mixv += [If(f"alsl{k} >= 0", [SendL(OSC, [col], f"/oled/gFillArea 3 $1 54 {MIX_W + 2} 1 1")])]
    # ---- pattern view: a row per layer (its gate or lane pattern), hits as boxes, the length as a tick; a
    # playhead under each row, moved every 16th (al-patmark)
    def row_on(r):
        return f"alin[{r}] && if({r} < 3, int(alp[max(0, alrg[{r}])]*3) >= 1, 1)"
    hits = "int(1 + alp[alrh[alpr]]*15 + 0.5)"
    steps = "int(2 + alp[alrs[alpr]]*14 + 0.5)"
    # (a tapped row: its tapped steps)
    # (alrg / alrp are -1 where a row has no such knob: read as slot 0, never outside the array)
    tap = "if(alpr < 3, int(alp[max(0, alrg[alpr])]*3) == 2, alp[max(0, alrp[alpr])] >= 0.5)"
    cell = f"if({tap}, altap[alpr*16 + alpc2] > 0, (alpc2*{hits}) % {steps} < {hits})"
    patv = [Loop(str(len(PAT_LAYERS)), "alpr", [
        If(row_on("alpr"), [
            Loop(steps, "alpc2", [If(cell, [SendL(OSC, [f"{PAT_X} + alpc2*{PAT_W}", "alpr*9 + 1"],
                                                    f"/oled/gFillArea 3 $1 $2 {PAT_W - 1} 6 1")])]),
            SendL(OSC, [f"{PAT_X} + {steps}*{PAT_W}", "alpr*9"], "/oled/gFillArea 3 $1 $2 1 8 1")])])]
    for li, L in enumerate(PAT_LAYERS):
        patv.append(Send(OSC, f"/oled/gPrintln 3 0 {li * 9} 8 1 {M.SHORT[L]}"))
    rate = f"{pick_clocks('alrr[alpr]')}"
    cur = (f"((int(max(0, alc24)/{rate}) + int(alp[alro[alpr]]*15 + 0.5) + if(alpr >= {fl}, allrot[alpr - {fl}], 0))"
           f" % {steps})")
    mark = [Loop(str(len(PAT_LAYERS)), "alpr", [
        SendL(OSC, ["alpr*9 + 7"], f"/oled/gFillArea 3 {PAT_X} $1 {16 * PAT_W} 1 0"),
        If(row_on("alpr"), [SendL(OSC, [f"{PAT_X} + {cur}*{PAT_W}", "alpr*9 + 7"],
                                  f"/oled/gFillArea 3 $1 $2 {PAT_W - 1} 1 1")])]),
        Send(OSC, "/oled/gFlip 3")]
    proc(c, "al-patmark", [If("alpatv == 1 && alpop == 0 && altick % 2 == 0", mark)])
    roadv = road_view(c)
    pulses(c)
    # (the MIX view, after its first frame: only the header and the columns cleared and drawn - its labels stay)
    shape = f"alview == {VIEW_MIX} && alpage == {M.SHAPE_PAGE}"     # (SHAPE: drawn as a page of knobs)
    mixing = f"alpop == 0 && alview == 2 && ({shape}) == 0"
    import vis
    VIS, visv = vis.VIEW_VIS, vis.frame()
    proc(c, "al-draw", [If(f"{mixing} && almixok", [Fill(0, 0, 128, 55, 0)], [Fill(0, 0, 128, 64, 0), V("almixok", "0")]),
                        If(f"alpop || ({shape})", lay, [If(f"alview == 2", mixv, [If(f"alview == {VIS}", visv, [If("alpatv == 1", patv,
                                                                       [If("alpatv == 2", roadv, play)])])])]),
                        If(f"({mixing}) == 0", [V("almixok", "0")]),
                        Send(OSC, "/oled/gFlip 3")])


def pulses(c):
    """the play view's rhythm: each lane's hit (its centre dot, lit for half its step) and the gates (control.gates) redraw it - only
    while it shows (the redraws are throttled as every other: al-redraw)"""
    proc(c, "al-playdraw", [If("alview == 0 && alpatv == 0 && alpop == 0", [Call("al-redraw")])])
    for i, L in enumerate(M.LANES):
        hv = c.ch(c.recv(f"al-{L}-hit"), "unpack f f f f")
        tb = c.to((hv, 2), "t b f")
        c.c((tb, 1), 0, c.obj("v alhitv"), 0)
        gate = f"max(40, 0.5*{clocks(S(L, None, 'Rate'))}*60000/({num(S('g', None, 'Tempo'))}*24))"
        run_steps(c, (tb, 0), [T("alhitp", str(i), "1"), Call("al-playdraw"), Arm(f"al-hitoff{i}", gate)])
        proc(c, f"al-hitoff{i}", [T("alhitp", str(i), "0"), Call("al-playdraw")])


def road_view(c):
    """the roadmap: section n/count and its role (HOLD while held); its story and the bar within it; the sections as
    a strip (widths by their bars, the current one filled, a playhead); the layers in it; the next one's role"""
    from pdlib import V, Loop
    st = S("g", None, "Story")
    row(c, "al-r-road", 0, 0, [("w", str(OFF["road"])), ("w", f"{OFF['frac']} + max(0, alrn - 1)*{M.MAXPAGES} + alrc"),
                               ("w", f"{OFF['role']} + alrsR[alrc]"), ("w", f"if(alrhold, {OFF['hold']}, {OFF['plus']})")])
    row(c, "al-r-road2", 0, 11, [("w", f"{OFF['opt']} + alob[{st}] + alrsS[alrc]"),
                                 ("n", "max(0, altick/32 - alrb0) + 1", "%d"), ("n", "alrsL[alrc]", "/%d")])
    row(c, "al-r-road3", 0, 54, [("w", str(OFF["next"])), ("w", f"{OFF['role']} + alrsR[min(alrc + 1, alrn - 1)]")])
    steps = [If("alrn == 0", [Send(OSC, "/oled/gPrintln 3 0 0 8 1 ROAD: aux + top C#")], [
        Call("al-r-road"), Call("al-r-road2"),
        V("alrtot", "0"), Loop("alrn", "alri", [V("alrtot", "alrtot + alrsL[alri]")]), V("alrsw", "0"),
        Loop("alrn", "alri", [
            If("alri == alrc", [SendL(OSC, ["int(alrsw*127/alrtot)", "max(2, int(alrsL[alri]*127/alrtot))"],
                                      "/oled/gFillArea 3 $1 24 $2 10 1")],
               [SendL(OSC, ["int(alrsw*127/alrtot)", "max(2, int(alrsL[alri]*127/alrtot))"],
                      "/oled/gBox 3 $1 24 $2 10 1")]),
            V("alrsw", "alrsw + alrsL[alri]")])])]
    for li, L in enumerate(LAYERS):
        x = 1 + 16 * li
        lab = M.SHORT[L][1] if M.kind(L) == "perc" else M.SHORT[L][0]
        steps.append(If(f"alrn > 0 && int(alrsM[alrc]/{2 ** li}) % 2",
                        [Fill(x, 38, 11, 10, 1), Send(OSC, f"/oled/gPrintln 3 {x + 3} 39 8 0 {lab}")],
                        [If("alrn > 0", [Send(OSC, f"/oled/gPrintln 3 {x + 3} 39 8 1 {lab}")])]))
    steps.append(If("alrn > 1", [Call("al-r-road3")]))
    return steps


def pick_clocks(slot_expr):
    out = str(M.RATE_CLOCKS[-1])
    n = len(M.RATE_CLOCKS)
    idx = f"min({n - 1}, int(alp[{slot_expr}]*{n}))"
    for i in range(n - 2, -1, -1):
        out = f"if({idx} == {i}, {M.RATE_CLOCKS[i]}, {out})"
    return out


def eng_word(layer_expr):
    """the engine's name of the layer at layer_expr: each layer's engine list sits at its own offset"""
    out = f"{OFF['eng-' + LAYERS[-1]]} + aleng[{layer_expr}]"
    for li in range(len(LAYERS) - 2, -1, -1):
        out = f"if({layer_expr} == {li}, {OFF['eng-' + LAYERS[li]]} + aleng[{li}], {out})"
    return out
