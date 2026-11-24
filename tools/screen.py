"""The OLED (128 x 64), drawn with /oled/g* messages to mother ([s oscOut]). Words come from al-words.txt (one per
line: control.words()), so the screen never builds strings at run time.

PLAY (home)                                  LAYER (5 s after a knob turns or a page changes)
  y 0   key mode tempo RUN/STOP [NOTES]        y 0   layer and engine (or GLOBAL)
  y 11  chord > next chord                     y 11  page name and its place (2/5)
  y 22-52  a row per layer: > selected,        y 22-52  the 4 knobs: name, value, a bar
        name, engine, + / M (muted), level bar
Redraws are throttled: at most one every 60 ms, however fast knobs turn."""
from pdlib import Canvas, proc, If, Call, SendL, Send, run_steps
import model as M
from model import S, LAYERS
from control import words, opt, num, ctx, npages, QUALS

OSC = "oscOut"


def Fill(x, y, w, h, c=1):
    return SendL(OSC, [str(x), str(y), str(w), str(h), str(c)], "/oled/gFillArea 3 $1 $2 $3 $4 $5")


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
            tgi = f"min({M.MAXC - 1}, int(alp[{sl}]*{M.MAXC}))"
            tg = f"alcand[(allayer*{M.MAXENG} + aleng[allayer])*{M.MAXC} + {tgi} - 1]"
            wl = sc.to(src, f"expr if({sl} < 0, {OFF['misc']}, if(aln[{sl}] == -2, if({tgi} == 0, {OFF['off']}, "
                            f"if({tg} < 0, {OFF['misc']}, {OFF['name']} + {tg})), if(aln[{sl}] > 0, {OFF['opt']} + "
                            f"alob[{sl}] + min(aln[{sl}] - 1, int(alp[{sl}]*aln[{sl}])), -1)))")
            mo = sc.to(wl, "moses 0")
            _sym(sc, sc.ch((mo, 1), "text get al-words"), (pk, i))
            nv = sc.to(sc.to((mo, 0), "t b"),
                       f"expr if(aln[{sl}] < 0, int(allo[{sl}] + alp[{sl}]*(alhi[{sl}] - allo[{sl}]) + 0.5), "
                       f"int(alp[{sl}]*100 + 0.5))")
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
MISC = {"-": 0, "RUN": 1, "STOP": 2, "M": 3, ">": 4, "NOTES": 5, "LAT": 6}
LINES.append("+")
OFF["plus"] = len(LINES) - 1
LINES.append("GLOBAL")
OFF["global"] = len(LINES) - 1
LINES.append("off")
OFF["off"] = len(LINES) - 1
LINES.append("out")
OFF["out"] = len(LINES) - 1
from features import TOASTS
OFF["toast"] = len(LINES)
LINES += TOASTS
OFF["loopst"] = len(LINES)
LINES += ["+", "R", "P", "O", "s"]          # a layer's loop: none, recording, playing, overdub, stopped
OFF["lanes"] = len(LINES)
LINES += ["".join(str(i + 1) if b & (1 << i) else "." for i in range(len(M.LANES))) + ("c" if b & 16 else "")
          for b in range(2 ** (len(M.LANES) + 1))]


def misc(w):
    return str(OFF["misc"] + MISC[w])


PAT_X, PAT_W = 16, 7         # the pattern view: cells from x 16, 7 pixels each (16 steps)
MIX_X0, MIX_DX, MIX_W = 1, 13, 9    # the MIX view's columns (the 8 layers; the master volume at x 112)
PAT_LAYERS = M.NOTE_LAYERS          # the pattern view's rows (the cloud has no pattern)


def rows_tables(c):
    """per pattern-view row (the 7 layers): the slots of its pattern, so one loop draws them all"""
    import model as M
    sl = lambda n: [S(L, None, n) for L in PAT_LAYERS]
    tabs = dict(alrh=sl("Hits"), alrs=sl("Steps"), alro=sl("Rotate"), alrr=sl("Rate"),
                alrg=[S(L, None, "Gate") if L in ("drone", "sub", "pad") else -1 for L in PAT_LAYERS])
    for name, vals in tabs.items():
        c.obj(f"array define {name} {len(vals)}")
        c.c(c.m(c.recv("al-init"), " ".join(str(v) for v in vals)), 0, c.obj(f"array set {name}"), 0)


def build(c):
    from pdlib import V, Loop
    c.comment("the screen: al-redraw (any change) -> at most every 60 ms -> al-draw")
    sp = c.obj("spigot 1")
    c.c(c.ch(c.recv("al-redraw"), "t b"), 0, sp, 0)
    tb = c.to(sp, "t b b")
    c.c(c.m((tb, 1), "0"), 0, sp, 1)
    d = c.ch((tb, 0), "delay 60", "t b b")
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
                               ("n", num(tempo), "%dbpm"), ("w", f"if(alrun, {misc('RUN')}, {misc('STOP')})"),
                               ("w", f"if(alnotes, {misc('NOTES')}, {OFF['plus']})")])
    row(c, "al-r-chord", 0, 11, [("w", f"{OFF['chord']} + alcr*{len(QUALS)} + alcq"), ("w", misc(">")),
                                 ("w", f"{OFF['chord']} + alnxr*{len(QUALS)} + alnxq")])
    for li in range(3):
        L = LAYERS[li]
        row(c, f"al-r-l{li}", 0, 22 + 10 * li, [
            ("w", f"if(allayer == {li}, {misc('>')}, {misc('-')})"), ("w", f"{OFF['layer']} + {li}"),
            ("w", f"{OFF['eng-' + L]} + aleng[{li}]"), ("w", f"if(alin[{li}] == 0, {OFF['out']}, {OFF['loopst']} + allps[{li}])")])
    # the percussion row: the lane last shown, its engine, and which lanes play (their numbers; '.' silent)
    ci = LAYERS.index("cloud")
    lanes_on = " + ".join(f"{2 ** i}*alin[{fl + i}]" for i in range(nl)) + f" + {2 ** nl}*alin[{ci}]"
    row(c, "al-r-perc", 0, 52, [
        ("w", f"if(allayer >= {fl}, {misc('>')}, {misc('-')})"), ("w", f"{OFF['layer']} + alplane"),
        ("w", eng_word("alplane")), ("w", f"{OFF['lanes']} + {lanes_on}")])
    row(c, "al-r-toast", 0, 0, [("w", f"{OFF['toast']} + altw"), ("n", "altn", "%d")])
    row(c, "al-r-toast0", 0, 0, [("w", f"{OFF['toast']} + altw")])
    play = [If("altw >= 0", [If("altn >= 0", [Call("al-r-toast")], [Call("al-r-toast0")])], [Call("al-r-head")]),
            Call("al-r-chord")]
    for li in range(3):
        lvl = S(LAYERS[li], None, "Level")
        play += [Call(f"al-r-l{li}"),
                 SendL(OSC, [str(23 + 10 * li), f"max(1, int(alp[{lvl}]*20))"], "/oled/gFillArea 3 106 $1 $2 5 1")]
    play += [Call("al-r-perc")]
    # ---- layer view
    lay = [If("alview", [Call("al-r-ghead")], [Call("al-r-lhead")]), Call("al-r-page")]
    row(c, "al-r-ghead", 0, 0, [("w", f"{OFF['global']}")])
    row(c, "al-r-lhead", 0, 0, [("w", f"if(alview, {OFF['global']}, {OFF['layer']} + allayer)"),
                                ("w", f"if(alview, {misc('-')}, {eng_word('allayer')})")])
    row(c, "al-r-page", 0, 11, [("w", f"{OFF['page']} + {ctx()}*{M.MAXPAGES} + alpage"),
                                ("w", f"{OFF['frac']} + ({npages()} - 1)*{M.MAXPAGES} + alpage")])
    for k in range(4):
        row(c, f"al-r-k{k}", 0, 22 + 10 * k, [("w", f"if(alsl{k} < 0, {misc('-')}, {OFF['name']} + alsl{k})"),
                                              ("v", k)])
        lay += [Call(f"al-r-k{k}"),
                If(f"alsl{k} >= 0 && (aln[alsl{k}] == 0 || aln[alsl{k}] == -1)",
                   [SendL(OSC, [str(23 + 10 * k), f"max(1, int(alp[alsl{k}]*46))"],
                          "/oled/gFillArea 3 80 $1 $2 5 1")])]
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
                 Send(OSC, f"/oled/gPrintln 3 {x} 55 8 1 {M.SHORT[L][1] if M.kind(L) == 'perc' else M.SHORT[L][0]}")]
    vol = S("g", None, "Volume")
    mixv += [SendL(OSC, [f"52 - int(alp[{vol}]*38)", f"max(1, int(alp[{vol}]*38))"], "/oled/gFillArea 3 112 $1 14 $2 1")]
    mixv += [Send(OSC, "/oled/gPrintln 3 114 55 8 1 V")]
    # (the columns the knobs turn now: a line under them)
    for k in range(4):
        terms = " + ".join(f"(alsl{k} == {S(L, None, 'Level')})*{li}" for li, L in enumerate(LAYERS))
        col = f"if(alsl{k} == {vol}, 112, {MIX_X0} + {MIX_DX}*({terms}))"
        mixv += [If(f"alsl{k} >= 0", [SendL(OSC, [col], f"/oled/gFillArea 3 $1 54 {MIX_W + 2} 1 1")])]
    # ---- pattern view: a row per layer (its gate or lane pattern), hits as boxes, the length as a tick; a
    # playhead under each row, moved every 16th (al-patmark)
    def row_on(r):
        return f"alin[{r}] && if({r} < 3, alp[alrg[{r}]] >= 0.5, 1)"
    hits = "int(1 + alp[alrh[alpr]]*15 + 0.5)"
    steps = "int(2 + alp[alrs[alpr]]*14 + 0.5)"
    cell = f"(alpc2*{hits}) % {steps} < {hits}"
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
    proc(c, "al-patmark", [If("alpatv && alpop == 0 && altick % 2 == 0", mark)])
    proc(c, "al-draw", [Fill(0, 0, 128, 64, 0),
                        If("alpop", lay, [If(f"alview == 2", mixv, [If("alpatv", patv, play)])]),
                        Send(OSC, "/oled/gFlip 3")])


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
