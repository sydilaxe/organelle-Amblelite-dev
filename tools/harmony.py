"""The harmony assistant (milestone 6): suggestions for the next chord, your own story, and listening.

Suggestions: after each chord, the candidates - the chords of the mode, those borrowed from its parallel mode
(major <-> minor), and chromatic moves from the current root (mediants a third up or down, the tritone) - are scored:
smooth voice leading (each tone of the current chord to the nearest tone of the candidate), a root moving by a
fourth or fifth, and (Listen on) the notes you hold. The best four (of the HARMNY page's Group) are al-sug 0..3.

Your own story (the story 'own'): aux + top E plays the suggestion shown (Sugg) at once and adds it to the story
(up to 8 chords, then round again); aux + top D clears it. Listening: while you hold notes, a chord change takes the
best suggestion containing them instead of the story's next chord."""
from pdlib import Canvas, proc, V, T, Send, Call, SendL, If, Loop
import model as M
from model import S
from control import opt

NC = 14             # the mode's and the borrowed chords, per mode
MOVES = [(3, "maj"), (-3, "maj"), (4, "maj"), (-4, "maj"), (6, "maj")]
# (a pentatonic's chords: its parent mode's; the borrowed chords come from the parallel major or minor)
PARENT = {"majpent": "ionian", "suspent": "mixolyd", "mangong": "aeolian", "ritusen": "mixolyd", "minpent": "aeolian"}
MAJORISH = {"ionian", "lydian", "mixolyd", "ion#5", "phrdom", "lyd#2", "lydaug", "lyddom", "mixob6", "majpent",
            "suspent", "ritusen"}


def _triad(iv, d):
    n = len(iv)
    p = [iv[(d + 2 * k) % n] + 12 * ((d + 2 * k) // n) for k in range(4)]
    third, fifth, sev = (p[1] - p[0]) % 12, (p[2] - p[0]) % 12, (p[3] - p[0]) % 12
    t = {(4, 7): "maj", (3, 7): "min", (3, 6): "dim", (4, 8): "aug"}.get((third, fifth), "sus2")
    if t == "maj" and sev == 11:
        t = "maj7"
    elif t == "min" and sev == 10:
        t = "m7"
    elif t == "maj" and sev == 10:
        t = "7"
    return p[0] % 12, t


def tables():
    """per mode: its chords (group 0), then the parallel mode's that it lacks (group 1): root (from the key), type"""
    modes = dict(M.MODES)
    R, Ty, G, N = [], [], [], []
    for name, iv in M.MODES:
        own = [_triad(modes[PARENT.get(name, name)], d) for d in range(7)]
        par = modes["aeolian" if name in MAJORISH else "ionian"]
        bor = [ch for ch in (_triad(par, d) for d in range(7)) if ch not in own]
        rows = [(r, t, 0) for r, t in own] + [(r, t, 1) for r, t in bor]
        rows = rows[:NC]
        N.append(len(rows))
        rows += [(0, "maj", 9)] * (NC - len(rows))
        R += [r for r, _, _ in rows]
        Ty += [M.TYPE_NAMES.index(t) for _, t, _ in rows]
        G += [g for _, _, g in rows]
    return dict(alhgR=R, alhgT=Ty, alhgG=G, alhgN=N)


GLOBALS = dict(alhn=0, alhi=0, alhj=0, alhx=0, alhs=0, alhv=0, alhm=0, alhb=0, alhrd=0, alhr=0, alht=0, alon=0,
               alov=0, alovR=0, alovT=0, alhq=0, alhcnt=0)


def build(c):
    rows = tables()
    for name, vals in rows.items():
        c.obj(f"array define {name} {len(vals)}")
        c.c(c.m(c.recv("al-init"), " ".join(str(v) for v in vals)), 0, c.obj(f"array set {name}"), 0)
    nmax = NC + len(MOVES)
    for name, n in (("alcR", nmax), ("alcT", nmax), ("alcG", nmax), ("alcS", nmax), ("alsuR", 4), ("alsuT", 4),
                    ("alhpc", 12)):
        c.obj(f"array define {name} {n}")
    key, mode = S("g", None, "Key"), S("g", None, "Mode")
    k, m = opt(key), opt(mode)
    grp, lis = S("g", None, "Group"), S("g", None, "Listen")
    # the candidates: the mode's and the borrowed (from the tables), the moves (from the current root)
    cands = [V("alhn", "0"),
             Loop(f"alhgN[{m}]", "alhi", [
                 T("alcR", "alhn", f"({k} + alhgR[{m}*{NC} + alhi]) % 12"), T("alcT", "alhn", f"alhgT[{m}*{NC} + alhi]"),
                 T("alcG", "alhn", f"alhgG[{m}*{NC} + alhi]"), V("alhn", "alhn + 1")])]
    for d, t in MOVES:
        cands += [T("alcR", "alhn", f"(alcr + {d} + 12) % 12"), T("alcT", "alhn", str(M.TYPE_NAMES.index(t))),
                  T("alcG", "alhn", "2"), V("alhn", "alhn + 1")]
    # a candidate's score: 10 - the voice leading (each current tone to its nearest candidate tone, in semitones)
    # + 2 for a root a fourth or fifth away - 30 for the chord itself + 3 for each held note it holds; -1000 when
    # not of the Group chosen
    tone = "((alcR[alhi] + alty[alcT[alhi]*4 + alhx]) % 12)"
    dist = f"min(abs(alct[alhj] % 12 - {tone}), 12 - abs(alct[alhj] % 12 - {tone}))"
    score = [V("alhs", "10"),
             Loop("3", "alhj", [V("alhm", "12"), Loop("4", "alhx", [V("alhm", f"min(alhm, {dist})")]),
                                V("alhs", "alhs - alhm")]),
             V("alhrd", "(alcR[alhi] - alcr + 12) % 12"),
             V("alhs", "alhs + 2*(alhrd == 5 || alhrd == 7) - 30*(alhrd == 0 && altq[alcT[alhi]] == alcq)"),
             If(f"{opt(lis)} == 1", [Loop("4", "alhx", [V("alhs", f"alhs + 3*(alhpc[{tone}] > 0)")])]),
             If(f"{opt(grp)} != 3 && alcG[alhi] != {opt(grp)}", [V("alhs", "alhs - 1000")]),
             T("alcS", "alhi", "alhs")]
    pickbest = [Loop("4", "alhq", [
        V("alhb", "-1"), V("alhv", "-10000"),
        Loop("alhn", "alhi", [If("alcS[alhi] > alhv", [V("alhv", "alcS[alhi]"), V("alhb", "alhi")])]),
        If("alhb >= 0", [T("alsuR", "alhq", "alcR[alhb]"), T("alsuT", "alhq", "alcT[alhb]"),
                         T("alcS", "alhb", "-10000")])])]
    proc(c, "al-suggest", cands + [Loop("alhn", "alhi", score)] + pickbest + [Call("al-redraw")])
    # your own story: the suggestion shown, played now and added
    sugg = opt(S("g", None, "Sugg"))
    st = S("g", None, "Story")
    own = M.OWN_STORY
    proc(c, "al-sugaccept", [
        V("alhr", f"alsuR[{sugg}]"), V("alht", f"alsuT[{sugg}]"),
        T("alsr", f"{own}*8 + alon % 8", f"(alhr - {k} + 12) % 12"), T("alsy", f"{own}*8 + alon % 8", "alht"),
        V("alstep", "alon % 8"), V("alon", "alon + 1"), T("alsdl", str(own), "min(8, alon)"),
        V("alov", "0"),
        If(f"{opt(st)} != {own}", [SendL("al-set", [str(st), f"{(own + 0.5) / len(M.STORIES):.6f}"])],
           [Call("al-chord")])])
    proc(c, "al-ownclear", [V("alon", "0"), T("alsdl", str(own), "1"), T("alsr", f"{own}*8", "0"),
                            T("alsy", f"{own}*8", str(M.TYPE_NAMES.index("maj"))), V("alstep", "0"),
                            If(f"{opt(st)} == {own}", [Call("al-chord")])])
    # listening: the notes held (pitch classes), from every layer you play
    for L in M.NOTE_LAYERS:
        r = c.ch(c.recv(f"al-user-{L}"), "unpack f f")
        hv = c.obj(f"expr alhpc[$f1 % 12] = max(0, alhpc[$f1 % 12] + if($f2 > 0, 1, -1)); "
                   f"alhcnt = max(0, alhcnt + if($f2 > 0, 1, -1))")
        c.c((r, 1), 0, hv, 1)
        c.c((r, 0), 0, hv, 0)
    c.c(c.ch(c.recv(f"al-s{grp}"), "t b"), 0, c.obj("s al-suggest"), 0)
    c.c(c.ch(c.recv(f"al-s{lis}"), "t b"), 0, c.obj("s al-suggest"), 0)
