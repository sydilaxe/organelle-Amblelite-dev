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
            sc.c(w, 0, pk, i)
        elif p[0] == "n":
            sc.c(sc.ch(sc.to(src, "expr " + p[1]), f"makefilename {p[2]}"), 0, pk, i)
        else:
            k = p[1]
            sl = f"alsl{k}"
            wl = sc.to(src, f"expr if({sl} < 0, {OFF['misc']}, if(aln[{sl}] > 0, {OFF['opt']} + alob[{sl}] + "
                            f"min(aln[{sl}] - 1, int(alp[{sl}]*aln[{sl}])), -1))")
            mo = sc.to(wl, "moses 0")
            sc.c(sc.ch((mo, 1), "text get al-words"), 0, pk, i)
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


def misc(w):
    return str(OFF["misc"] + MISC[w])


def build(c):
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
    tempo, key, mode = S("g", None, "Tempo"), S("g", None, "Key"), S("g", None, "Mode")
    # ---- play view
    row(c, "al-r-head", 0, 0, [("w", f"{OFF['note']} + {opt(key)}"), ("w", f"{OFF['mode']} + {opt(mode)}"),
                               ("n", num(tempo), "%dbpm"), ("w", f"if(alrun, {misc('RUN')}, {misc('STOP')})"),
                               ("w", f"if(alnotes, {misc('NOTES')}, {OFF['plus']})")])
    row(c, "al-r-chord", 0, 11, [("w", f"{OFF['chord']} + alcr*{len(QUALS)} + alcq"), ("w", misc(">")),
                                 ("w", f"{OFF['chord']} + alnxr*{len(QUALS)} + alnxq")])
    for li, L in enumerate(LAYERS):
        row(c, f"al-r-l{li}", 0, 22 + 10 * li, [
            ("w", f"if(allayer == {li}, {misc('>')}, {misc('-')})"), ("w", f"{OFF['layer']} + {li}"),
            ("w", f"{OFF['eng-' + L]} + aleng[{li}]"), ("w", f"if(almute[{li}], {misc('M')}, {OFF['plus']})")])
    play = [Call("al-r-head"), Call("al-r-chord")]
    for li, L in enumerate(LAYERS):
        lvl = S(L, None, "Level")
        play += [Call(f"al-r-l{li}"),
                 SendL(OSC, [str(23 + 10 * li), f"max(1, int(alp[{lvl}]*26))"], "/oled/gFillArea 3 101 $1 $2 5 1")]
    # ---- layer view
    lay = [row_call("al-r-lhead"), row_call("al-r-page")]
    row(c, "al-r-lhead", 0, 0, [("w", f"if(alview, {OFF['global']}, {OFF['layer']} + allayer)"),
                                ("w", f"if(alview, {misc('-')}, {eng_word()})")])
    row(c, "al-r-page", 0, 11, [("w", f"{OFF['page']} + {ctx()}*{M.MAXPAGES} + alpage"),
                                ("w", f"{OFF['frac']} + ({npages()} - 1)*{M.MAXPAGES} + alpage")])
    for k in range(4):
        row(c, f"al-r-k{k}", 0, 22 + 10 * k, [("w", f"if(alsl{k} < 0, {misc('-')}, {OFF['name']} + alsl{k})"),
                                              ("v", k)])
        lay += [Call(f"al-r-k{k}"),
                If(f"alsl{k} >= 0 && aln[alsl{k}] <= 0",
                   [SendL(OSC, [str(23 + 10 * k), f"max(1, int(alp[alsl{k}]*46))"],
                          "/oled/gFillArea 3 80 $1 $2 5 1")])]
    # the knobs' slots on the shown page (the knob handlers keep them too, but a page change must show them)
    from control import MAXPAGES
    from pdlib import V
    slots = [V(f"alsl{k}", f"alks[({ctx()}*{MAXPAGES} + alpage)*4 + {k}]") for k in range(4)]
    proc(c, "al-draw", [Fill(0, 0, 128, 64, 0)] + [If("alpop", slots + lay, play)] + [Send(OSC, "/oled/gFlip 3")])


def row_call(name):
    return Call(name)


def eng_word():
    # the engine's name: each layer's engine list sits at its own offset
    out = f"{OFF['eng-perc']} + aleng[3]"
    for li in (2, 1, 0):
        out = f"if(allayer == {li}, {OFF['eng-' + LAYERS[li]]} + aleng[{li}], {out})"
    return out
