"""Control: parameters, knobs (with pickup), pages and views, the Organelle keys, MIDI in, notes to voices, the
transport and clock, the percussion lanes' patterns, the gates, the chord story and Evolve. Written in pdlib steps
(proc / V / T / If / Loop / SendL): [r name] -> steps in order, over global [value]s (al<word>) and arrays.

Layers by number: 0 drone, 1 sub, 2 pads, 3..6 the percussion lanes (model.LAYERS)."""
from pdlib import Canvas, proc, V, T, Send, Call, SendL, If, Loop, run_steps, Later, Arm
import model as M
from model import S, LAYERS, LANES, MAXENG, MAXPAGES, GLOBAL_LAYER, NSLOTS

NL = len(LAYERS)
EVOLVE_MS = 150             # Evolve's step (the parameters' ramps are as long: dsp.prm)
LX = {"drone": "d", "sub": "s"}
FIRST_LANE = LAYERS.index(LANES[0])
VIEW_LAYER, VIEW_GLOBAL, VIEW_MIX = 0, 1, 2
SECTN_PAGE = [n for n, _ in M.GLOBAL_PAGES].index("SECTN")
MODE_SLOT, SCALE_SLOT = S("g", None, "Mode"), S("g", None, "Scale")
IN_AT_START = ("drone", "sub", "pad", "perc1")      # the layers in when the patch loads (the others out)
# globals and their start values (each gets a [v name])
GLOBALS = dict(alstick=0, allayer=0, alview=0, alpage=0, alrun=0, alnotes=0, alaux=0, alauxu=0, alpop=0, altick=-1, alc24=-1,
               alstep=0, alclock=0, alphc=0, alptn=0, alptv=0, alpkey=-1, alpj=0, alpbest=0, alj=0,
               alkn=0, alkvel=0, almn=0, almv=0, almc=0, alcs=0, alcr=0, alcq=0, alnxr=0, alnxq=0, alcb=0,
               aldn=0, aldv=0, aldhc=0, aldon=0, aldtn=0, aldtv=0, alsn=0, alsv2=0, alshc=0, alson=0, alstn=0,
               alstv=0, alpn=0, alpv2=0, alcur0=-1, alcur1=-1, ali=0, alci=0, alcd=0, alcst=0,
               altime=0, alel=0, alek=0, aled=0, alep=100, alet2=0, alesl=0, alenew=0, alplane=FIRST_LANE,
               alln=0, allv=0, allr=0, allm=0, alpatv=0, alprow=0, alpc2=0, alil=0, aliv=0, alhk=-1, alhd=0,
               aldk=0, alsk=0,
               alcpu=0, alcpux=0, alcpuh=0)
for k in range(4):
    GLOBALS.update({f"alsl{k}": -1, f"allat{k}": 0, f"alpv{k}": -1})
for L in LANES:
    GLOBALS.update({f"al{L}n": 0, f"al{L}v": 0})
ARRAYS = dict(alp=NSLOTS, aln=NSLOTS, allo=NSLOTS, alhi=NSLOTS, alob=NSLOTS, alks=0, alnp=0, aleng=NL, alusr=NL,
              allatch=NL, alin=NL, alprm=4, alpvn=4, alpg=4, alpa=4, alpt=4, alpk=4, alch=4, alct=4, alsc=len(M.MODES) * 7,
              alscn=len(M.MODES), alsk=0, alsd=0, alsr=0, alsy=0, alsdl=0, alsm=len(M.MODES) * 8,
              alsml=len(M.MODES), alty=0, altq=0, alpe=NSLOTS, alem=NSLOTS, alet=0, alew=0, alevs=0, alevp=0,
              alevy=0, algl=0, aleo=NL, alepo=NL, allane=4, allrot=4, allrr=4, alfo=0, alfm=NSLOTS, alfn=NSLOTS)


def opt(slot, n=None):
    """the option index of a choice slot. The Mode knob's is the mode in model.MODES: its Scale's modes from
    SCALE_START, the knob choosing among them (a 5-note scale has 5)"""
    if slot == MODE_SLOT and n is None:
        sc = opt(SCALE_SLOT)
        start, count = pick(M.SCALE_START, sc), pick(M.SCALE_COUNT, sc)
        return f"(({start}) + min(({count}) - 1, int(alp[{slot}]*({count}))))"
    n = n or len(M.SLOTS[slot][1].opts)
    return f"min({n - 1}, int(alp[{slot}]*{n}))"


def num(slot):
    p = M.SLOTS[slot][1]
    return f"int({p.lo} + alp[{slot}]*{p.hi - p.lo} + 0.5)"


def octave(L):
    return f"12*({opt(S(L, None, 'Octave'))} - 3)"


def pick(values, idx):
    out = str(values[-1])
    for i in range(len(values) - 2, -1, -1):
        out = f"if({idx} == {i}, {values[i]}, {out})"
    return out


def ctx():
    """the knob table index of the shown pages: (a layer, the global pages or the mix pages) x engine"""
    return (f"(if(alview == {VIEW_GLOBAL}, {GLOBAL_LAYER}, if(alview == {VIEW_MIX}, {GLOBAL_LAYER + 1}, allayer))"
            f"*{MAXENG} + if(alview, 0, aleng[allayer]))")


def npages():
    return f"alnp[{ctx()}]"


def clocks(slot):
    """a Rate choice as MIDI clocks a step"""
    return pick(M.RATE_CLOCKS, opt(slot))


def euclid(L, step):
    """whether step (an expression) is a hit of layer L's pattern: hits spread evenly over steps, rotated"""
    hits, steps, rot = (S(L, None, n) for n in ("Hits", "Steps", "Rotate"))
    idx = f"((({step}) + {num(rot)}) % {num(steps)})"
    return f"(({idx}*{num(hits)}) % {num(steps)} < {num(hits)})"


# ---------------------------------------------------------------------------------------------- tables at load
def tables(c):
    ks, np_, pnames = M.knob_table()
    n, lo, hi, ob, opts, names = M.slot_meta()
    rows = dict(alp=[p.default for _, p in M.SLOTS], alpe=[p.default for _, p in M.SLOTS], aln=n, allo=lo, alhi=hi,
                alob=ob, alks=ks, alnp=np_)
    sc, scn, sm, sml = [], [], [], []
    for name, iv in M.MODES:
        sc += (iv + iv)[:7]
        scn.append(len(iv))
        deg, ln = M.story_degrees(None, name)
        sm += deg
        sml.append(ln)
    sk, sd, sr, sy, sdl = [], [], [], [], []
    for name, k, data in M.STORIES:
        if k == "deg":
            deg, ln = M.story_degrees(data or [0], "ionian")
            sk.append(0)
            sd += deg
            sr += [0] * M.STORY_LEN
            sy += [0] * M.STORY_LEN
        else:
            roots, types, ln = M.story_chords(data)
            sk.append(1)
            sd += [0] * M.STORY_LEN
            sr += roots
            sy += types
        sdl.append(ln)
    ty, tq = [], []
    for name in M.TYPE_NAMES:
        iv, q = M.CHORD_TYPES[name]
        ty += iv
        tq.append(q)
    rows.update(alsc=sc, alscn=scn, alsm=sm, alsml=sml, alsk=sk, alsd=sd, alsr=sr, alsy=sy, alsdl=sdl, alty=ty,
                altq=tq, allatch=[1, 1, 1] + [0] * len(LANES), alin=[1 if L in IN_AT_START else 0 for L in LAYERS])
    et = [-1] * ((NL + 2) * MAXENG * M.EVOLVE_MAX)
    ew = [0] * ((NL + 2) * MAXENG * M.EVOLVE_MAX)
    for li, L in enumerate(LAYERS):
        for ei, (e, _) in enumerate(M.engines(L)):
            for k, (pn, w) in enumerate(M.EVOLVE[(M.kind(L), e)]):
                et[(li * MAXENG + ei) * M.EVOLVE_MAX + k] = S(L, None, "Cutoff") if pn is None else S(L, e, pn)
                ew[(li * MAXENG + ei) * M.EVOLVE_MAX + k] = w
    rows.update(alfo=[x for f in M.FEEL_OFFSETS for x in f])
    # the global pages' knobs that are another layer's (LAYERS, LANES): the layer, shown as their name
    rows.update(algl=[M.global_label(ps[k]) if k < len(ps) else -1 for _, ps in M.GLOBAL_PAGES for k in range(4)])
    rows.update(alet=et, alew=ew, alevs=[S(L, None, "Evolve") for L in LAYERS],
                alevp=[S(L, None, "Pace") for L in LAYERS], alevy=[S(L, None, "EvSync") for L in LAYERS])
    c.comment("the tables: parameters (alp) and their kinds, the knob pages, scales, chord stories (tools/model.py)")
    for name, size in ARRAYS.items():
        size = size or len(rows[name])
        c.obj(f"array define {name} {size}")
    init = c.ch(c.recv("al-init"), "t b b b")
    for name, vals in rows.items():
        c.c(c.m((init, 2), " ".join(f"{v:g}" for v in vals)), 0, c.obj(f"array set {name}"), 0)
    tx = c.obj("text define al-words")
    c.c(c.m((init, 1), "read -c al-words.txt"), 0, tx, 0)
    from wavetables import TABLES
    for tn, _, _ in TABLES:
        c.obj(f"array define alwt-{tn} 2051")
        sf = c.obj("soundfiler")
        c.c(c.m((init, 0), f"read -resize waves/factory/{tn}.wav alwt-{tn}"), 0, sf, 0)


def words():
    """the screen's words, one per line of al-words.txt. Returns (lines, offsets)"""
    n, lo, hi, ob, opts, names = M.slot_meta()
    ks, np_, pnames = M.knob_table()
    off, lines = {}, []
    for key, items in (("name", names), ("opt", opts), ("page", pnames), ("note", M.NOTE_NAMES),
                       ("mode", [m for m, _ in M.MODES]), ("layer", [M.LAYER_LABEL[L] for L in LAYERS]),
                       ("short", [M.SHORT[L] for L in LAYERS]), ("qual", M.QUALS),
                       ("misc", ["-", "RUN", "STOP", "M", ">", "NOTES", "LAT"])):
        off[key] = len(lines)
        lines += [w if w else "-" for w in items]
    for L in LAYERS:
        off["eng-" + L] = len(lines)
        lines += [e for e, _ in M.engines(L)]
    return lines, off


QUALS = M.QUALS


# ---------------------------------------------------------------------------------------------- parameters
def params(c):
    c.comment("al-set 'slot value': store it (alp), add Evolve's movement (alem) for the value the sound hears "
              "(alpe), send that to [r al-s<slot>], redraw. al-out 'slot': send alpe[slot] again.")
    t = c.to(c.recv("al-set"), "t b l l l")
    c.c((t, 3), 0, c.obj("expr alp[$f1] = $f2"), 0)
    c.c((t, 2), 0, c.obj("expr alpe[$f1] = max(0, min(1, $f2 + alem[$f1] + alfm[$f1] + alfn[$f1] + alfb[$f1]))"), 0)
    c.c(c.to((t, 1), "list split 1"), 0, c.obj("s al-out"), 0)
    c.c((t, 0), 0, c.obj("s al-redraw"), 0)
    o = c.to(c.recv("al-out"), "t f f")
    snd = c.obj("s")
    c.c(c.to((o, 1), "makefilename al-s%d"), 0, snd, 1)
    c.c(c.to((o, 0), "expr alpe[$f1]"), 0, snd, 0)
    proc(c, "al-sendall", [Loop(str(NSLOTS), "ali", [SendL("al-set", ["ali", "alp[ali]"])])])
    # an engine change: the layer's pages change - keep the page in range, pick up the knobs again
    for li, L in enumerate(LAYERS):
        ne = len(M.engines(L))
        e = c.ch(c.recv(f"al-s{S(L, None, 'Engine')}"), f"expr min({ne - 1}, int($f1*{ne}))")
        tw2 = c.obj("tabwrite aleng")
        c.c(c.m(c.obj("loadbang"), str(li)), 0, tw2, 1)
        te = c.to(e, "t b f")
        c.c((te, 1), 0, tw2, 0)
        c.c((te, 0), 0, c.obj("s al-engchg"), 0)
    proc(c, "al-engchg", [V("alpage", f"min(alpage, {npages()} - 1)"), Call("al-pickreset")])


# ---------------------------------------------------------------------------------------------- knobs
def knobs(c):
    c.comment("the 4 knobs: each acts on its slot on the shown page once it has passed the stored value (pickup)")
    proc(c, "al-pickreset", [V(f"allat{k}", "0") for k in range(4)] +
         [V(f"alsl{k}", f"alks[({ctx()}*{MAXPAGES} + alpage)*4 + {k}]") for k in range(4)] + [Call("al-redraw")])
    for k in range(4):
        sc = Canvas(f"knob{k + 1}", w=1200)
        c.sub(sc)
        # aux held (on a layer's pages): assign mode instead (features.assign)
        ka = sc.to(sc.recv(f"knob{k + 1}"), "t f b f")
        sc.c((ka, 2), 0, sc.obj("v alasv"), 0)
        lp0 = sc.obj("list prepend")
        sc.c(sc.to((ka, 1), "expr alaux && alview == 0"), 0, lp0, 1)
        sc.c((ka, 0), 0, lp0, 0)
        rt0 = sc.to(lp0, "route 0 1")
        sc.c(sc.to((rt0, 1), "t b"), 0, sc.obj(f"s al-assign{k}"), 0)
        t = sc.to(rt0, "t f f f")
        sc.c(t, 2, sc.obj(f"expr alsl{k} = alks[({ctx()}*{MAXPAGES} + alpage)*4 + {k}]"), 0)
        sc.c(t, 1, sc.obj(f"expr allat{k} = if(alsl{k} < 0, 0, allat{k} || abs($f1 - alp[alsl{k}]) < 0.025 || "
                          f"(alpv{k} >= 0 && (alpv{k} - alp[alsl{k}])*($f1 - alp[alsl{k}]) <= 0))"), 0)
        t2 = sc.to((t, 0), "t f f")
        sc.c((t2, 1), 0, sc.obj(f"v alpv{k}"), 0)
        g = sc.ch((t2, 0), f"expr if(allat{k}, $f1, -1)", "moses 0")
        tt = sc.to((g, 1), "t f b b")
        lp = sc.obj("list prepend")
        sc.c(sc.to((tt, 2), f"expr alsl{k}"), 0, lp, 1)
        sc.c((tt, 1), 0, sc.obj("s al-popup"), 0)
        sc.c((tt, 0), 0, lp, 0)
        sc.c(lp, 0, sc.obj("s al-set"), 0)
    # pages opened on purpose (a held layer key, the global key, paging) stay until an aux tap (alstick); the
    # pop-up a knob gives in the play view closes 3 s after the last turn
    proc(c, "al-popup", [If(f"alview != {VIEW_MIX}", [V("alpop", "1"), Later("al-popoff", 3000)],
                            [Call("al-redraw")])])
    proc(c, "al-popoff", [If("alstick == 0", [V("alpop", "0"), Call("al-redraw")])])


# ---------------------------------------------------------------------------------------------- in / out
def fade_ms():
    f = S("g", None, "Fade")
    return f"if(alp[{f}] < 0.02, 0, 50*pow(400, alp[{f}]))"


def layer_switches(c):
    """each layer is in or out (alin). In: its level fades up (the PERFRM page's Fade) and it plays - the drone,
    sub and pads their default or latched notes, a lane its pattern. Out: its level fades down, then its notes
    release (remembered, to come back with it); a loop keeps its place, silent. al-inset 'layer 0|1' sets one,
    al-tog-<layer> toggles it."""
    _entry(c, "al-inset", ["alil", "aliv"], "al-inset-do")
    rt = c.ch(c.recv("al-inset-do"), "t b", "expr alil", "route " + " ".join(str(i) for i in range(NL)))
    for li, L in enumerate(LAYERS):
        c.c((rt, li), 0, c.obj(f"s al-inset-{L}"), 0)
        # (while the SECTN page shows, the key edits the section instead: roadmap.py)
        proc(c, f"al-tog-{L}", [If(f"alview == {VIEW_GLOBAL} && alpage == {SECTN_PAGE}",
                                   [V("alrq", str(li)), Call("al-rtog")],
                                   [SendL("al-inset", [str(li), f"1 - alin[{li}]"])])])
        # (the level's fade: 'in fade_ms' to the mix)
        proc(c, f"al-inset-{L}", [
            If(f"aliv != alin[{li}]", [
                T("alin", str(li), "aliv"), SendL(f"al-in{li}", ["aliv", fade_ms()]),
                If("aliv", [Send(f"al-outstop-{L}"), Call(f"al-inon-{L}")],
                   [Arm(f"al-outrel-{L}", f"{fade_ms()} + 20", stop=f"al-outstop-{L}")]),
                Call("al-redraw")])])
        if L in ("drone", "sub"):
            x = LX[L]
            proc(c, f"al-outrel-{L}", [If(f"alin[{li}] == 0 && al{x}on", [
                SendL(f"al-{L}-g", ["0", "0", "0"]), V(f"al{x}on", "0"), V(f"al{x}k", "1")])])
            proc(c, f"al-inon-{L}", [If(f"al{x}on == 0", [
                If(f"al{x}k", [V(f"al{x}k", "0"), V(f"al{x}tv", "0.85"), Call(f"al-mono-{L}")],
                   [If(f"alrun && alusr[{li}] == 0", [Call(f"al-def-{L}")])])])])
        elif L == "pad":
            proc(c, "al-outrel-pad", [If("alin[2] == 0", [Loop("4", "alj", [If("alpg[alj]", [
                T("alprm", "alj", "1"), SendL("al-pad-g", ["alj", "0", "0"]), T("alpg", "alj", "0")])])])])
            proc(c, "al-inon-pad", [
                V("alj", "alprm[0] + alprm[1] + alprm[2] + alprm[3]"),
                If("alj > 0", [Loop("4", "alj", [If("alprm[alj]", [
                    T("alprm", "alj", "0"), SendL("al-pad-n", ["alj", "alpvn[alj]", "0"]),
                    SendL("al-pad-g", ["alj", "0.7", "0"]), T("alpg", "alj", "1")])])],
                   [If("alrun && alusr[2] == 0", [Call("al-def-pad")])])])
        else:
            proc(c, f"al-outrel-{L}", [])
            proc(c, f"al-inon-{L}", [])


# ---------------------------------------------------------------------------------------------- pages, layers
def pages(c):
    proc(c, "al-pgnext", [V("alstick", "1"), V("alpage", f"(alpage + 1) % {npages()}"), Call("al-pickreset"),
                          Call("al-popup")])
    proc(c, "al-pgprev", [V("alstick", "1"), V("alpage", f"(alpage + {npages()} - 1) % {npages()}"),
                          Call("al-pickreset"), Call("al-popup")])
    for li, L in enumerate(LAYERS):
        proc(c, f"al-sel-{L}", [V("alstick", "1"), V("allayer", str(li)), V("alview", "0"), V("alpage", "0"), Call("al-pickreset"),
                                Call("al-popup")] + ([V("alplane", str(li))] if L in LANES else []))
    layer_switches(c)
    proc(c, "al-global", [V("alstick", "1"), If(f"alview == {VIEW_GLOBAL}", [V("alpage", f"(alpage + 1) % {len(M.GLOBAL_PAGES)}")],
                             [V("alview", str(VIEW_GLOBAL)), V("alpage", "0")]), Call("al-pickreset"), Call("al-popup")])
    proc(c, "al-mix", [V("alstick", "0"), If(f"alview == {VIEW_MIX}", [V("alpage", f"(alpage + 1) % {len(M.MIX_PAGES)}")],
                          [V("alview", str(VIEW_MIX)), V("alpage", "0")]), V("alpop", "0"), Call("al-pickreset")])
    proc(c, "al-layerview", [V("alstick", "0"), V("alview", "0"), V("alpage", "0"), V("alpop", "0"), V("alpatv", "0"),
                             Call("al-pickreset")])
    # (low F#: the pattern view, then the roadmap view, then neither)
    proc(c, "al-patview", [V("alpatv", "(alpatv + 1) % 3"), V("alview", "if(alview == 2, 0, alview)"), V("alpop", "0"),
                           Call("al-pickreset")])
    proc(c, "al-latch", [If(f"allayer < {FIRST_LANE}", [T("allatch", "allayer", "1 - allatch[allayer]")]),
                         If("allatch[allayer] == 0", [Call("al-unlatch")]), Call("al-redraw")])
    proc(c, "al-unlatch", [
        If("allayer == 0 && aldhc == 0 && aldon", [SendL("al-drone-g", ["0", "0", "0"]), V("aldon", "0")]),
        If("allayer == 1 && alshc == 0 && alson", [SendL("al-sub-g", ["0", "0", "0"]), V("alson", "0")]),
        If("allayer == 2 && alphc == 0", [Call("al-prelall")])])
    proc(c, "al-clear", [
        T("alusr", "allayer", "0"),
        If("allayer == 0", [SendL("al-drone-g", ["0", "0", "0"]), V("aldon", "0"), V("aldhc", "0")]),
        If("allayer == 1", [SendL("al-sub-g", ["0", "0", "0"]), V("alson", "0"), V("alshc", "0")]),
        If("allayer == 2", [Call("al-prelall"), V("alphc", "0")]),
        If("alrun && alin[allayer]", [Call("al-chord")]), Call("al-redraw")])
    proc(c, "al-notesmode", [V("alnotes", "1 - alnotes"), Call("al-redraw")])


# ---------------------------------------------------------------------------------------------- Organelle keys
# one press each; aux held: the second set. Unlisted keys do nothing yet (later milestones).
# the low white keys: the seven layers - a tap: in / out; held (LAYER_HOLD ms): its pages
LAYER_KEYS = {60: "drone", 62: "sub", 64: "pad", 65: "perc1", 67: "perc2", 69: "perc3", 71: "perc4", 79: "cloud"}
LAYER_HOLD = 400
# the low black keys: the views; the top octave: playing
KEYS = {61: "al-layerview", 63: "al-mix", 66: "al-patview", 68: "al-global", 70: "al-pgnext",
        72: "al-startstop", 73: "al-clear", 74: "al-chordprev", 75: "al-loop", 76: "al-chordnext",
        77: "al-pgprev", 78: "al-loopstop", 80: "al-loopclear", 81: "al-latch",
        83: "al-notesmode"}
SLOT_KEY = 82          # held: the keys from low C to top D# recall a snapshot (with aux: save); tapped: COMPARE
# aux held + a layer key: its pages at once (in notes mode too); aux + a few others
AUX_KEYS = {**{k: f"al-sel-{L}" for k, L in LAYER_KEYS.items()}, 70: "al-pgprev", 72: "al-startstop",
            73: "al-rgen", 74: "al-ownclear", 76: "al-sugaccept", 78: "al-rhold", 80: "al-rnext", 83: "al-notesmode"}


def organelle(c):
    c.comment("the Organelle's keys: functions (KEYS), aux held: AUX_KEYS; in notes mode they play the shown layer")
    r = c.ch(c.recv("notesRaw"), "t b l")
    up = c.to((r, 1), "unpack f f")
    c.c((up, 1), 0, c.obj("v alkvel"), 0)
    c.c((up, 0), 0, c.obj("v alkn"), 0)
    lk = " || ".join(f"alkn == {k}" for k in LAYER_KEYS)
    # a layer key pressed: wait - held LAYER_HOLD ms shows its pages; let go before: a tap toggles it in / out
    key_down = [If(f"alaux == 0 && ({lk})",
                   [V("alhk", "alkn"), V("alhd", "0"), Arm("al-khold", str(LAYER_HOLD), stop="al-khstop")],
                   [V("alauxu", "if(alaux, 1, alauxu)"), Send("al-keyfn")])]
    key_up = [If("alkn == alhk", [Send("al-khstop"), If("alhd == 0", [SendL("al-togk", ["alkn"])]),
                                  V("alhk", "-1")])]
    normal = [If("alnotes && alaux == 0", [SendL("al-note", ["allayer", "alkn", "alkvel/127"])],
                 [If("alkvel > 0", key_down, key_up)])]
    slots = [If("alslh && alkvel > 0 && alkn >= 60 && alkn <= 75",
                [V("alslot", "alkn - 60"), V("alslu", "1"), V("alauxu", "if(alaux, 1, alauxu)"),
                 If("alaux", [Call("al-save")], [Call("al-recall")])], normal)]
    run_steps(c, (r, 0), [If(f"alkn == {SLOT_KEY}",
                             [If("alkvel > 0", [V("alslh", "1"), V("alslu", "0")],
                                 [V("alslh", "0"), If("alslu == 0", [Call("al-compare")])])], slots)])
    tg = c.ch(c.recv("al-togk"), "route " + " ".join(str(k) for k in LAYER_KEYS))
    hx = c.ch(c.recv("al-khold"), "t b", "expr alhd = 1; alhk")
    hl = c.to((hx, 1), "route " + " ".join(str(k) for k in LAYER_KEYS))
    for i, (k, L) in enumerate(LAYER_KEYS.items()):
        c.c((tg, i), 0, c.obj(f"s al-tog-{L}"), 0)
        c.c((hl, i), 0, c.obj(f"s al-sel-{L}"), 0)
    fn = c.ch(c.recv("al-keyfn"), "expr alkn + 100*alaux")
    sel = c.obj("sel " + " ".join(str(k) for k in KEYS) + " " + " ".join(str(k + 100) for k in AUX_KEYS))
    c.c(fn, 0, sel, 0)
    for i, name in enumerate(list(KEYS.values()) + list(AUX_KEYS.values())):
        c.c((sel, i), 0, c.obj(f"s {name}"), 0)
    a = c.ch(c.recv("aux"), "t f f")
    c.c(c.to((a, 1), "expr $f1 > 0"), 0, c.obj("v alaux"), 0)
    tap = c.ch((a, 0), "sel 0")
    # an aux tap (aux not used with a key or knob): home - the play view, from any page or view
    run_steps(c, (tap, 0), [If("alauxu == 0", [Call("al-layerview"), Call("al-redraw")])])
    run_steps(c, (tap, 1), [V("alauxu", "0")])


# ---------------------------------------------------------------------------------------------- notes to voices
def _entry(c, recv, names, then):
    r = c.ch(c.recv(recv), "t b l")
    up = c.to((r, 1), "unpack " + " ".join(["f"] * len(names)))
    for i, nm in enumerate(names):
        c.c((up, i), 0, c.obj(f"v {nm}"), 0)
    c.c(r, 0, c.obj(f"s {then}"), 0)


def glide_ms(L):
    return f"5*pow(800, alp[{S(L, None, 'Glide')}])"


def zone(L):
    """the articulation: 0 artic, 1 legato, 2 porta, 3 slide. With the gate on, every note restarts (the gate needs
    the envelope)"""
    return f"if({opt(S(L, None, 'Gate'))} == 1, 0, {opt(S(L, None, 'Artic'))})"


def mono(c, L):
    x = LX[L]
    li = LAYERS.index(L)
    n, v, hc, on, tn, tv = (f"al{x}n", f"al{x}v" if x != "s" else "alsv2", f"al{x}hc", f"al{x}on", f"al{x}tn",
                            f"al{x}tv")
    _entry(c, f"al-in-{L}", [n, v], f"al-in-{L}-do")
    proc(c, f"al-in-{L}-do", [If(f"{v} > 0", [
        T("alusr", str(li), "1"), V(tn, f"{n} + {octave(L)}"), V(tv, v), Call(f"al-mono-{L}"), V(hc, f"{hc} + 1")],
        [V(hc, f"max(0, {hc} - 1)"),
         If(f"allatch[{li}] == 0 && {hc} == 0 && {on}", [SendL(f"al-{L}-g", ["0", "0", "0"]), V(on, "0")])])])
    ov = f"({hc} > 0 || (allatch[{li}] && {on}))"
    proc(c, f"al-mono-{L}", [
        SendL(f"al-{L}-n", ["0", tn, f"if({zone(L)} == 3 || ({zone(L)} == 2 && {ov}), {glide_ms(L)}, 0)"]),
        If(f"{zone(L)} == 0 || {ov} == 0 || {on} == 0", [SendL(f"al-{L}-g", ["0", tv, "0"]), V(on, "1")]),
        V(f"alcur{li}", tn), Call("al-redraw")])


def pads(c):
    _entry(c, "al-in-pad", ["alpn", "alpv2"], "al-in-pad-do")
    proc(c, "al-in-pad-do", [If("alpv2 > 0", [
        T("alusr", "2", "1"), If("alphc == 0", [Call("al-pbegin")]), V("alphc", "alphc + 1"),
        V("alptn", f"alpn + {octave('pad')}"), V("alptv", "alpv2"), V("alpkey", "alpn"), Call("al-pnote")],
        [V("alphc", "max(0, alphc - 1)"),
         If("allatch[2] == 0", [Loop("4", "alj", [If("alpk[alj] == alpn && alpg[alj]", [
             SendL("al-pad-g", ["alj", "0", "0"]), T("alpg", "alj", "0"), T("alpk", "alj", "-1")])])],
            [If("alphc == 0", [Call("al-pend")])])])])
    proc(c, "al-pbegin", [Loop("4", "alj", [T("alpa", "alj", "0")])])
    # the voice: latched (or a chord from the story) - the nearest sounding voice not yet in this chord, so chords
    # move by the smallest steps; else the oldest free voice, or the oldest of all
    nearest = "if(alpa[alj], 1e9, if(alpg[alj], abs(alpvn[alj] - alptn), 200 + alpt[alj]*1e-6))"
    oldest = "if(alpg[alj], 1000 + alpt[alj]*1e-6, alpt[alj]*1e-6)"
    ov = "alpg[alpj]"
    z = zone("pad")
    proc(c, "al-pnote", [
        V("alpbest", "1e10"), V("alpj", "0"),
        Loop("4", "alj", [If(f"if(allatch[2] || alpkey < 0, {nearest}, {oldest}) < alpbest", [
            V("alpbest", f"if(allatch[2] || alpkey < 0, {nearest}, {oldest})"), V("alpj", "alj")])]),
        SendL("al-pad-n", ["alpj", "alptn", f"if({z} == 3 || ({z} == 2 && {ov}), {glide_ms('pad')}, 0)"]),
        If(f"{z} == 0 || {ov} == 0", [SendL("al-pad-g", ["alpj", "alptv", "0"])]),
        T("alpg", "alpj", "1"), T("alpvn", "alpj", "alptn"), T("alpa", "alpj", "1"), T("alpk", "alpj", "alpkey"),
        T("alplh", "alpj", "alptn"), T("alpls", "alpj", "0"),      # (the voice's home, for counterpoint: lines.py)
        V("alclock", "alclock + 1"), T("alpt", "alpj", "alclock")])
    proc(c, "al-pend", [Loop("4", "alj", [If("alpa[alj] == 0 && alpg[alj]", [
        SendL("al-pad-g", ["alj", "0", "0"]), T("alpg", "alj", "0")])])])
    proc(c, "al-prelall", [Loop("4", "alj", [If("alpg[alj]", [SendL("al-pad-g", ["alj", "0", "0"]), T("alpg", "alj", "0")])])])


def lanes(c):
    """each lane: a note-on strikes its next voice (round robin) with the lane's decay and velocity response"""
    for i, L in enumerate(LANES):
        li = LAYERS.index(L)
        n, v = f"al{L}n", f"al{L}v"
        _entry(c, f"al-in-{L}", [n, v], f"al-in-{L}-do")
        dec = f"50*pow(600, alpe[{S(L, None, 'Decay')}])"
        velo = f"alpe[{S(L, None, 'Velo')}]"
        proc(c, f"al-in-{L}-do", [If(f"{v} > 0", [
            T("allrr", str(i), f"(allrr[{i}] + 1) % {M.VOICES[L]}"),
            SendL(f"al-{L}-hit", [f"allrr[{i}]", f"{n} + {octave(L)}", f"1 - {velo}*(1 - {v})", dec])])])


# ---------------------------------------------------------------------------------------------- transport, clock
def transport(c):
    c.comment("the clock: 24 a beat (MIDI clock). Each lane and gate steps at its own rate (in clocks: triplets "
              "too); the story counts bars in 32nds (every 3 clocks). Sync: internal, or an incoming MIDI clock")
    tempo, sync, clk = S("g", None, "Tempo"), S("g", None, "Sync"), S("g", None, "ClkOut")
    met = c.obj("metro 30")
    c.c(c.recv("al-clock"), 0, met, 0)
    c.c(c.ch(c.recv(f"al-s{tempo}"), f"expr 60000/({num(tempo)}*24)"), 0, met, 1)
    c.c(met, 0, c.obj("s al-24"), 0)
    rti = c.obj("midirealtimein")
    rsel = c.to(rti, "sel 248 250 252")
    run_steps(c, (rsel, 0), [If(f"{opt(sync)} == 1 && alrun", [Call("al-24")])])
    run_steps(c, (rsel, 1), [If(f"{opt(sync)} == 1", [Call("al-start")])])
    run_steps(c, (rsel, 2), [If(f"{opt(sync)} == 1", [Call("al-stop")])])
    mo = c.obj("midiout")
    c.c(c.recv("al-midibyte"), 0, mo, 0)
    proc(c, "al-24", [V("alc24", "alc24 + 1"),
                      If(f"{opt(clk)} == 1", [Send("al-midibyte", "248")]),
                      Call("al-lanes"), Call("al-gates"), Call("al-loops"), Call("al-lines"),
                      If("alc24 % 3 == 0", [Call("al-tick")])])
    proc(c, "al-startstop", [If("alrun", [Call("al-stop")], [Call("al-start")])])
    proc(c, "al-start", [If("alrun == 0", [
        V("alrun", "1"), V("altick", "-1"), V("alc24", "-1"), V("alstep", "0"), Call("al-rstart"),
        Loop("4", "alj", [T("allane", "alj", "-1"), T("allrot", "alj", "0")]), Call("al-chord"),
        If(f"{opt(clk)} == 1", [Send("al-midibyte", "250")]),
        If(f"{opt(sync)} == 0", [Send("al-clock", "1")]), Call("al-redraw")])])
    proc(c, "al-stop", [If("alrun", [
        V("alrun", "0"), Send("al-clock", "0"), If(f"{opt(clk)} == 1", [Send("al-midibyte", "252")]),
        SendL("al-drone-g", ["0", "0", "0"]), SendL("al-sub-g", ["0", "0", "0"]), Call("al-prelall"),
        V("aldon", "0"), V("alson", "0"), V("aldhc", "0"), V("alshc", "0"), V("alphc", "0"),
        Loop(str(NL), "alj", [T("alusr", "alj", "0")]), Call("al-redraw")])])
    bars = S("g", None, "Bars")
    nb = pick(M.BAR_N, opt(bars))
    proc(c, "al-tick", [
        V("altick", "altick + 1"),
        If(f"{opt(bars)} > 0 && altick > 0 && altick % (32*{nb}) == 0", [Call("al-chordnext")]),
        # each bar: the lanes with a Phase move one step against the others (Reich's phasing, in steps)
        If("altick > 0 && altick % 32 == 0", [Call("al-phase")]),
        If("altick % 32 == 0", [Call("al-rbar")]),
        If("alpatv", [Call("al-patmark")])])
    proc(c, "al-phase", [If(f"{opt(S(L, None, 'Phase'))} > 0 && (altick/32) % "
                            f"{pick(M.PHASE_BARS, opt(S(L, None, 'Phase')))} == 0",
                            [T("allrot", str(i), f"allrot[{i}] + 1")]) for i, L in enumerate(LANES)])


def lane_patterns(c):
    """each lane: on its steps (its Rate), a hit of its Euclidean pattern (moved on by its phase) strikes a note
    from its pitch source: the chord's tones up / down / up and down, the root, the fifth, the scale up / down, or
    the chord stacked (three voices at once). The first step accented."""
    key, mode = S("g", None, "Key"), S("g", None, "Mode")
    m, k = opt(mode), opt(key)
    steps = []
    for i, L in enumerate(LANES):
        li = LAYERS.index(L)
        rc = clocks(S(L, None, "Rate"))
        stp = f"(alc24/{rc} + allrot[{i}])"
        acc = f"if(((alc24/{rc} + {num(S(L, None, 'Rotate'))} + allrot[{i}]) % {num(S(L, None, 'Steps'))}) == 0, 1, " \
              f"1 - 0.6*alp[{S(L, None, 'Accent')}])"
        pm = opt(S(L, None, "Pitch"))
        scl = (f"(48 + {k} + alsc[{m}*7 + (allane[{i}] % 8) % alscn[{m}]] + "
               f"12*int((allane[{i}] % 8)/alscn[{m}]))")
        note = (f"if({pm} <= 2, alch[if({pm} == 2, if(allane[{i}] % 6 < 4, allane[{i}] % 6, 6 - allane[{i}] % 6), "
                f"allane[{i}] % 4)] - 12, if({pm} == 3, alch[0] - 12, if({pm} == 4, alch[2] - 12, {scl})))")
        steps.append(If(f"alin[{li}] && alc24 % {rc} == 0 && {euclid(L, f'alc24/{rc} + allrot[{i}]')}", [
            T("allane", str(i), f"if({pm} == 1 || {pm} == 6, allane[{i}] + 7, allane[{i}] + 1)"),
            V("allv", acc),
            V("allr", swing_ms(L)),
            If(f"{pm} == 7", [SendL(f"al-sw-{L}", [f"alch[{j}] - 12", "allv", "allr"]) for j in range(3)],
               [If(f"{pm} == 8", [Call(f"al-motif{i}"), SendL(f"al-sw-{L}", ["allmn", "allv", "allr"])],
                   [SendL(f"al-sw-{L}", [note, "allv", "allr"])])])]))
        # swing: the step's notes after their delay ([pipe] keeps each one's own)
        pp = c.ch(c.recv(f"al-sw-{L}"), "pipe f f 0")
        pk = c.obj("pack f f")
        c.c(pp, 1, pk, 1)
        c.c(pp, 0, pk, 0)
        c.c(pk, 0, c.obj(f"s al-in-{L}"), 0)
    proc(c, "al-lanes", steps)


def swing_ms(L):
    """how late this step sounds: Swing x the feel's offset for the step's place in 4 x half a step"""
    tempo = S("g", None, "Tempo")
    rc = clocks(S(L, None, "Rate"))
    return (f"alpe[{S(L, None, 'Swing')}]*alfo[{opt(S(L, None, 'Feel'))}*4 + (alc24/{rc}) % 4]*0.5*{rc}*"
            f"60000/({num(tempo)}*24)")


def gate_hit(L):
    """whether layer L's gate opens on this clock: a hit of its own pattern, or (Comp) where another layer's pattern
    is silent - complementary rhythms"""
    def step_of(O):
        return f"alc24/{clocks(S(O, None, 'Rate'))}"
    own = euclid(L, step_of(L))
    others = [f"(1 - {euclid(O, step_of(O))})" for O in ("drone", "sub", "pad")]
    return pick([own] + others, opt(S(L, None, "Comp")))


def gates(c):
    """the gate sequencer on the drone, sub and pads: on each hit of its pattern (or, with Comp, where another
    layer's pattern is silent) the layer's notes restart their envelope; Length later (a share of the step) they
    release. Off: they sustain again."""
    tempo = S("g", None, "Tempo")
    cms = f"60000/({num(tempo)}*24)"
    for L in ("drone", "sub", "pad"):
        rc = clocks(S(L, None, "Rate"))
        gate = S(L, None, "Gate")
        acc = (f"if(((alc24/{rc} + {num(S(L, None, 'Rotate'))}) % {num(S(L, None, 'Steps'))}) == 0, 1, "
               f"1 - 0.5*alp[{S(L, None, 'Accent')}])")
        if L == "pad":
            on = [Loop("4", "alj", [If("alpg[alj]", [SendL("al-pad-g", ["alj", f"0.7*{acc}", "1"])])])]
            off = [Loop("4", "alj", [If("alpg[alj]", [SendL("al-pad-g", ["alj", "0", "1"])])])]
            hold = [Loop("4", "alj", [If("alpg[alj]", [SendL("al-pad-g", ["alj", "0.7", "0"])])])]
        else:
            x = LX[L]
            on = [If(f"al{x}on", [SendL(f"al-{L}-g", ["0", f"0.85*{acc}", "1"])])]
            off = [If(f"al{x}on", [SendL(f"al-{L}-g", ["0", "0", "1"])])]
            hold = [If(f"al{x}on", [SendL(f"al-{L}-g", ["0", "0.85", "0"])])]
        proc(c, f"al-gate-{L}", on + [Arm(f"al-gaterel-{L}", f"max(20, alp[{S(L, None, 'Length')}]*{rc}*{cms})",
                                          stop=f"al-gatestop-{L}")])
        proc(c, f"al-gaterel-{L}", [If(f"{opt(gate)} == 1", off)])
        proc(c, f"al-gateoff-{L}", [Send(f"al-gatestop-{L}"), If(f"{opt(gate)} == 0 && alrun", hold)])
        c.c(c.ch(c.recv(f"al-s{gate}"), "t b"), 0, c.obj(f"s al-gateoff-{L}"), 0)
    proc(c, "al-gates", [If(f"alrun && alin[{LAYERS.index(L)}] && {opt(S(L, None, 'Gate'))} == 1 && alc24 % {clocks(S(L, None, 'Rate'))} == 0 "
                            f"&& {gate_hit(L)}", [SendL(f"al-gsw-{L}", ["0", swing_ms(L)])])
                         for L in ("drone", "sub", "pad")])
    for L in ("drone", "sub", "pad"):
        c.c(c.ch(c.recv(f"al-gsw-{L}"), "pipe", "t b"), 0, c.obj(f"s al-gate-{L}"), 0)


# ---------------------------------------------------------------------------------------------- the chord story
def story(c):
    key, mode, st, sub_to, voic = (S("g", None, n) for n in ("Key", "Mode", "Story", "SubTo", "Voicng"))
    m, k, s_ = opt(mode), opt(key), opt(st)
    ln = f"if({s_} == 0, alsml[{m}], alsdl[{s_}])"
    deg = f"if({s_} == 0, alsm[{m}*8 + alcs % {ln}], alsd[{s_}*8 + alcs % {ln}])"
    nsc = f"alscn[{m}]"

    def pc(i):
        return f"(alsc[{m}*7 + (alcd + {2 * i}) % {nsc}] + 12*int((alcd + {2 * i})/{nsc}))"
    third, fifth = f"(({pc(1)} - {pc(0)}) % 12)", f"(({pc(2)} - {pc(0)}) % 12)"
    vo = f"alp[{voic}]"
    # a library chord: its root (semitones from the key) and type
    lroot = f"alsr[{s_}*8 + alcs % {ln}]"
    ltype = f"alsy[{s_}*8 + alcs % {ln}]"
    proc(c, "al-chordcalc", [If("alov && alcs == alstep", [
        # (listening chose the chord: the best suggestion holding the notes you hold)
        V("alcst", "alovT"), V("alcr", "alovR"), V("alcq", "altq[alcst]"), V("alcb", "60 + alovR"),
        Loop("4", "alj", [T("alct", "alj", "alty[alcst*4 + alj]")])], [
        If(f"alsk[{s_}] == 0", [
            # in the mode: thirds stacked on the degree
            V("alcd", deg),
            V("alcr", f"({k} + alsc[{m}*7 + alcd % {nsc}]) % 12"),
            V("alcq", f"if({third} == 3 && {fifth} == 7, 1, if({third} == 4 && {fifth} == 7, 0, if({third} == 3 && "
                      f"{fifth} == 6, 2, if({third} == 4 && {fifth} == 8, 3, 4))))"),
            V("alcb", f"60 + {k} + {pc(0)}"),
            T("alct", "0", "0"), T("alct", "1", f"{pc(1)} - {pc(0)}"), T("alct", "2", f"{pc(2)} - {pc(0)}"),
            T("alct", "3", f"{pc(3)} - {pc(0)}")],
            [V("alcst", ltype), V("alcr", f"({k} + {lroot}) % 12"), V("alcq", "altq[alcst]"),
             V("alcb", f"60 + ({k} + {lroot}) % 12"),
             Loop("4", "alj", [T("alct", "alj", "alty[alcst*4 + alj]")])])]),
        # keep the chord near middle C; the voicing: close; drop-2 (the third voice down); open (the second up)
        V("alcb", "alcb - 12*(alcb >= 67)"),
        T("alct", "0", "alcb + alct[0]"), T("alct", "1", f"alcb + alct[1] + 12*({vo} >= 0.66)"),
        T("alct", "2", f"alcb + alct[2] - 12*({vo} >= 0.33 && {vo} < 0.66)"), T("alct", "3", "alcb + alct[3]")])
    sub_base = f"48 + if({opt(sub_to)} == 1, alcr, {k}) + {octave('sub')}"
    proc(c, "al-chord", [
        V("alcs", "alstep + 1"), Call("al-chordcalc"), V("alnxr", "alcr"), V("alnxq", "alcq"),
        V("alcs", "alstep"), Call("al-chordcalc"),
        Loop("4", "alj", [T("alch", "alj", f"alct[alj] + {octave('pad')}")]), Call("al-cloudratios"),
        Call("al-suggest"),
        If("alrun", [If(f"alusr[{i}] == 0 && alin[{i}]", [Call(f"al-def-{L}")]) for i, L in enumerate(("drone", "sub", "pad"))]),
        Call("al-redraw")])
    proc(c, "al-def-drone", [V("aldtn", f"48 + {k} + {octave('drone')}"), V("aldtv", "0.85"), Call("al-mono-drone")])
    proc(c, "al-def-sub", [V("alstn", sub_base), V("alstv", "0.85"), Call("al-mono-sub")])
    proc(c, "al-def-pad", [Call("al-pbegin"),
                           Loop("4", "alci", [V("alptn", "alch[alci]"), V("alptv", "0.7"), V("alpkey", "-1"),
                                              Call("al-pnote")]),
                           Call("al-pend")])
    # the next chord: the story's - or, listening while you hold notes, the best suggestion holding them
    lis = S("g", None, "Listen")
    proc(c, "al-chordnext", [If(f"{opt(lis)} == 1 && alhcnt > 0", [
        Call("al-suggest"), V("alov", "1"), V("alovR", "alsuR[0]"), V("alovT", "alsuT[0]"), Call("al-chord")],
        [V("alov", "0"), V("alstep", f"(alstep + 1) % ({ln})"), Call("al-chord")])])
    proc(c, "al-chordprev", [V("alstep", f"(alstep + {ln} - 1) % ({ln})"), Call("al-chord")])
    for sl in (key, mode, st, sub_to, voic):
        c.c(c.ch(c.recv(f"al-s{sl}"), "t b"), 0, c.obj("s al-chord-later"), 0)
    c.c(c.ch(c.recv("al-chord-later"), "delay 5"), 0, c.obj("s al-chord"), 0)


def evolve(c):
    """Evolve: every 150 ms, each layer's targets (model.EVOLVE, for its engine) move on two slow sines of their own -
    periods unrelated (x1, x1.37, x1.71 ... and x1.618 of those), so they phase against each other and the sound
    rarely repeats, yet the same settings always move the same way. Time runs free (since the patch loaded) or locked
    to the clock (from Start). The base period: Pace 0 = 5 minutes .. 1 = 25 s. Depth: the layer's Evolve x the
    master Evolve (PERFRM page) x each target's weight. Each layer's depth and period also go to its voices
    (al-evd<n> 'depth period': the pads' breathing and orbit, the drone's and sub's breathing)."""
    c.comment(" ".join(evolve.__doc__.split(" - ")[0].split()))    # (one line: the same on every Python)
    met = c.obj(f"metro {EVOLVE_MS}")
    c.c(c.recv("al-init"), 0, met, 0)
    tm = c.obj("timer")
    c.c(c.recv("al-init"), 0, tm, 0)
    tb = c.to(met, "t b b")
    c.c((tb, 1), 0, tm, 1)
    c.c(c.to(tm, "/ 1000"), 0, c.obj("v altime"), 0)
    c.c(tb, 0, c.obj("s al-evolve"), 0)
    master = S("g", None, "Evolve")
    tempo = S("g", None, "Tempo")
    em = M.EVOLVE_MAX
    sl = f"alet[(alel*{MAXENG} + aleng[alel])*{em} + alek]"
    w = f"alew[(alel*{MAXENG} + aleng[alel])*{em} + alek]"
    per = "25*pow(12, 1 - alp[alevp[alel]])"
    tt = f"if(alp[alevy[alel]] >= 0.5, max(0, altick)*60/({num(tempo)}*8), altime)"
    mod = (f"aled*{w}*0.5*(0.65*sin(6.28319*(alet2/(alep*(1 + 0.37*alek + 0.11*alel)) + 0.31*alek + 0.17*alel)) + "
           f"0.35*sin(6.28319*(alet2/(alep*1.618*(1 + 0.37*alek + 0.11*alel)) + 0.7*alek)))")
    proc(c, "al-evolve", [Loop(str(NL), "alel", [
        V("aled", f"alp[alevs[alel]]*alp[{master}]"), V("alep", per), V("alet2", tt),
        # (to the voices only when it changed)
        If("abs(aled - aleo[alel]) > 0.002 || abs(alep - alepo[alel]) > 0.5",
           [T("aleo", "alel", "aled"), T("alepo", "alel", "alep"), SendL("al-evd", ["alel", "aled", "alep"])]),
        Loop(str(em), "alek", [If(f"{sl} >= 0", [
            V("alesl", sl), T("alem", "alesl", mod), V("alenew", "max(0, min(1, alp[alesl] + alem[alesl] + alfm[alesl] + alfn[alesl] + alfb[alesl]))"),
            If("abs(alenew - alpe[alesl]) > 0.002", [T("alpe", "alesl", "alenew"), SendL("al-out", ["alesl"])])])])])])
    rt = c.ch(c.recv("al-evd"), "route " + " ".join(str(i) for i in range(NL)))
    for i in range(NL):
        c.c(rt, i, c.obj(f"s al-evd{i}"), 0)


def build(c):
    for fn in (tables, params, knobs, pages, organelle, transport, lane_patterns, gates, story, evolve):
        sc = Canvas(fn.__name__, w=2600)
        c.sub(sc)
        fn(sc)
    for L in ("drone", "sub"):
        sc = Canvas(f"notes-{L}", w=2600)
        c.sub(sc)
        mono(sc, L)
    for fn in (pads, lanes):
        sc = Canvas(f"notes-{fn.__name__}", w=2600)
        c.sub(sc)
        fn(sc)
    vals = Canvas("values")
    c.sub(vals)
    import features
    import midi
    import harmony
    import roadmap
    import lines
    for g in (features.GLOBALS, midi.GLOBALS, harmony.GLOBALS, roadmap.GLOBALS, lines.GLOBALS):
        for k, v in g.items():
            assert k not in GLOBALS, k
        GLOBALS.update(g)
    for name, v0 in GLOBALS.items():
        vals.obj(f"v {name}")
    lb = vals.obj("loadbang")
    vals.m(lb, "; " + "; ".join(f"al-v-{n} {v0}" for n, v0 in GLOBALS.items() if v0 != 0))
    for name, v0 in GLOBALS.items():
        if v0 != 0:
            vals.c(vals.recv(f"al-v-{name}"), 0, vals.obj(f"v {name}"), 0)
