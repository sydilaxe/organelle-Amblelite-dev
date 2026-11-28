"""Counterpoint and motifs (milestone 6).

Counterpoint (the pads' LINES page): on the hits of a pattern (Lines: how many of 8 steps, at its Rate) one pad
voice steps from its chord tone to the next note of the mode, up or down (each voice turning the other way each time)
and back - neighbour - or on a second step and then back - passing. Voices: the top one, the inner ones, all in
turn, or the bass. A new chord brings every voice home. Rules, no dice.

Motifs (a lane's Pitch 'motif', its MOTIF page): the lane plays the notes of another layer's loop in turn - as
recorded, inverted (around its first note), reversed, a fifth or an octave up, an octave down. With no loop there,
it plays the chord as 'up' does."""
from pdlib import proc, V, T, Call, SendL, If, Loop
import model as M
from model import S, LANES, NOTE_LAYERS
from control import opt, num, pick, clocks, euclid, octave
from features import MAXEV

GLOBALS = dict(alnj=0, alnt=0, alnn=0, alnd=0, alnf=0, alnk=0, alnmx=0, alnmn=0, alnc=0, allmn=0, allms=0,
               allmc=0, allmi=0, allmf=0)


def tables(c):
    sm = []
    for _, iv in M.MODES:
        sm += [1 if pc in iv else 0 for pc in range(12)]
    for name, vals in (("alsm12", sm),):
        c.obj(f"array define {name} {len(vals)}")
        c.c(c.m(c.recv("al-init"), " ".join(str(v) for v in vals)), 0, c.obj(f"array set {name}"), 0)
    for name, n in (("alplh", 4), ("alpls", 4), ("alpld", 4), ("allmp", len(LANES))):
        c.obj(f"array define {name} {n}")
    c.c(c.m(c.recv("al-init"), "1 -1 1 -1"), 0, c.obj("array set alpld"), 0)


def build(c):
    from pdlib import Canvas
    for fn in (tables, counterpoint, motifs):
        sc = Canvas("lines-" + fn.__name__, w=2600)
        c.sub(sc)
        fn(sc)


def counterpoint(c):
    key, mode = S("g", None, "Key"), S("g", None, "Mode")
    k, m = opt(key), opt(mode)
    lines, voices, style = (S("pad", None, n) for n in ("Lines", "LnVoic", "LnStyl"))
    rc = clocks(S("pad", None, "LnRate"))
    hits = f"int(alp[{lines}]*8 + 0.5)"
    hit = f"(((alc24/{rc}) * {hits}) % 8 < {hits})"
    # the next note of the mode from alnn in the direction alnd (1 or -1)
    step = [V("alnf", "0"), Loop("4", "alnk", [If(
        f"alnf == 0 && alsm12[{m}*12 + ((alnn + alnd*(alnk + 1) - {k}) % 12 + 12) % 12]",
        [V("alnf", "alnn + alnd*(alnk + 1)")])]), V("alnn", "if(alnf, alnf, alnn)")]
    vs = opt(voices)
    choose = [
        V("alnmx", "-1"), V("alnmn", "-1"),
        Loop("4", "alnk", [If("alpg[alnk]", [
            If("alnmx < 0 || alplh[alnk] > alplh[alnmx]", [V("alnmx", "alnk")]),
            If("alnmn < 0 || alplh[alnk] < alplh[alnmn]", [V("alnmn", "alnk")])])]),
        V("alnj", "-1"), V("alnc", "alc24/" + rc),
        If(f"{vs} == 0", [V("alnj", "alnmx")]), If(f"{vs} == 3", [V("alnj", "alnmn")]),
        # (inner, all: in turn - inner leaves out the top and the bass)
        If(f"{vs} == 1 || {vs} == 2", [Loop("4", "alnk", [If(
            f"alnj < 0 && alpg[(alnc + alnk) % 4] && ({vs} == 2 || ((alnc + alnk) % 4 != alnmx && (alnc + alnk) % 4 != alnmn))",
            [V("alnj", "(alnc + alnk) % 4")])])])]
    move = [If("alnj >= 0", [
        V("alnt", "alpls[alnj]"),
        If("alnt == 0", [T("alpld", "alnj", "0 - alpld[alnj]"), V("alnd", "alpld[alnj]"), V("alnn", "alplh[alnj]")]
           + step + [T("alpls", "alnj", "1")],
           [If(f"alnt == 1 && {opt(style)} == 1", [V("alnd", "alpld[alnj]"), V("alnn", "alpvn[alnj]")] + step +
               [T("alpls", "alnj", "2")],
               [V("alnn", "alplh[alnj]"), T("alpls", "alnj", "0")])]),
        T("alpvn", "alnj", "alnn"), SendL("al-pad-n", ["alnj", "alnn", "80"])])]
    # (the cheap test first, the pattern only on its step)
    proc(c, "al-lines", [If(f"alrun && alin[2] && {hits} > 0 && alc24 % {rc} == 0", [If(hit, choose + move)])])


def motifs(c):
    """al-motif<i>: lane i's next motif note -> allmn"""
    for i, L in enumerate(LANES):
        src, tr = opt(S(L, None, "MSrc")), opt(S(L, None, "MTran"))
        base = f"{src}*{MAXEV}"
        n_ev = f"allpc[{src}]"
        idx = f"if({tr} == 2, {n_ev} - 1 - allmi, allmi)"
        proc(c, f"al-motif{i}", [If(f"{n_ev} > 0", [
            # the next note-on of the source's loop (up to 8 events on: its note-offs skipped)
            V("allmf", "0"), V("allmi", f"allmp[{i}]"),
            Loop("8", "allmc", [If("allmf == 0", [
                V("allmi", f"(allmi + 1) % {n_ev}"),
                If(f"allpv[{base} + {idx}] > 0", [V("allmf", "1")])])]),
            T("allmp", str(i), "allmi"),
            V("allmn", f"allpn[{base} + {idx}]"),
            V("allmn", f"if({tr} == 1, 2*allpn[{base}] - allmn, allmn + "
                       f"if({tr} == 3, 7, if({tr} == 4, 12, if({tr} == 5, -12, 0))))")],
            [V("allmn", f"alch[allane[{i}] % 4]")])])
