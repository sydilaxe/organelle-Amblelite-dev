"""Control: parameters, knobs (with pickup), pages, the Organelle keys, MIDI in, notes to voices, the transport and
clock, the percussion pattern and the chord story. Written in pdlib steps (proc / V / T / If / Loop / SendL):
[r name] -> steps in order, over global [value]s (al<word>) and arrays."""
from pdlib import Canvas, proc, X, V, T, Send, Call, SendL, If, Loop, run_steps, Later
import model as M
from model import S, LAYERS, MAXENG, MAXPAGES, GLOBAL_LAYER, NSLOTS

LX = {"drone": "d", "sub": "s", "pad": "p", "perc": "c"}
NV = M.VOICES
# globals and their start values (each gets a [v name])
GLOBALS = dict(allayer=0, alview=0, alpage=0, alrun=0, alnotes=0, alaux=0, alauxu=0, alpop=0, altick=-1, alc24=-1,
               alstep=0, alclock=0, alrr=0, alpc=0, alphc=0, alptn=0, alptv=0, alpkey=-1, alpj=0, alpbest=0, alj=0,
               alss=0, alsv=0, alkn=0, alkvel=0, almn=0, almv=0, almc=0, alcs=0, alcr=0, alcq=0, alnxr=0, alnxq=0,
               aldn=0, aldv=0, aldhc=0, aldon=0, aldtn=0, aldtv=0, alsn=0, alsv2=0, alshc=0, alson=0, alstn=0,
               alstv=0, alcn=0, alcv=0, alpn=0, alpv2=0, alext=0, alcur0=-1, alcur1=-1, ali=0, alci=0, alcd=0)
for k in range(4):
    GLOBALS.update({f"alsl{k}": -1, f"allat{k}": 0, f"alpv{k}": -1})
ARRAYS = dict(alp=NSLOTS, aln=NSLOTS, allo=NSLOTS, alhi=NSLOTS, alob=NSLOTS, alks=0, alnp=0, aleng=4, alusr=4,
              allatch=4, almute=4, alpvn=4, alpg=4, alpa=4, alpt=4, alpk=4, alch=4, alct=4, alsc=len(M.MODES) * 7,
              alscn=len(M.MODES), alsd=len(M.STORIES) * 8, alsdl=len(M.STORIES), alsm=len(M.MODES) * 8,
              alsml=len(M.MODES))


def opt(slot, n=None):
    """the option index of a choice slot"""
    n = n or len(M.SLOTS[slot][1].opts)
    return f"min({n - 1}, int(alp[{slot}]*{n}))"


def num(slot):
    p = M.SLOTS[slot][1]
    return f"int({p.lo} + alp[{slot}]*{p.hi - p.lo} + 0.5)"


def octave(L):
    return f"12*({opt(S(L, None, 'Octave'))} - 3)"


def ctx():
    """the knob table index of the shown pages: (layer or the global pages) x engine"""
    return f"(if(alview, {GLOBAL_LAYER}, allayer)*{MAXENG} + if(alview, 0, aleng[allayer]))"


def npages():
    return f"alnp[{ctx()}]"


# ---------------------------------------------------------------------------------------------- tables at load
def tables(c):
    ks, np_, pnames = M.knob_table()
    n, lo, hi, ob, opts, names = M.slot_meta()
    rows = dict(alp=[p.default for _, p in M.SLOTS], aln=n, allo=lo, alhi=hi, alob=ob, alks=ks, alnp=np_)
    sc, scn, sm, sml = [], [], [], []
    for name, iv in M.MODES:
        sc += (iv + iv)[:7]
        scn.append(len(iv))
        deg, ln = M.story_degrees(None, name)
        sm += deg
        sml.append(ln)
    sd, sdl = [], []
    for name, st in M.STORIES:
        deg, ln = M.story_degrees(st or [0], "ionian")
        sd += deg
        sdl.append(ln)
    rows.update(alsc=sc, alscn=scn, alsm=sm, alsml=sml, alsd=sd, alsdl=sdl, allatch=[1, 1, 1, 1])
    c.comment("the tables: parameters (alp) and their kinds, the knob pages, scales and chord stories (tools/model.py)")
    for name, size in ARRAYS.items():
        size = size or len(rows[name])
        c.obj(f"array define {name} {size}")
    init = c.ch(c.recv("al-init"), "t b b b")
    for name, vals in rows.items():
        c.c(c.m((init, 2), " ".join(f"{v:g}" for v in vals)), 0, c.obj(f"array set {name}"), 0)
    for t in ("al-words",):
        tx = c.obj(f"text define {t}")
        c.c(c.m((init, 1), f"read -c {t}.txt"), 0, tx, 0)
    # the wavetable bank
    from wavetables import TABLES
    for tn, _, _ in TABLES:
        c.obj(f"array define alwt-{tn} 2051")
        sf = c.obj("soundfiler")
        c.c(c.m((init, 0), f"read -resize waves/factory/{tn}.wav alwt-{tn}"), 0, sf, 0)


def words():
    """the screen's words, one per line of al-words.txt: slot names, options, page names, notes, modes, layers,
    chord qualities. Returns (lines, offsets)"""
    n, lo, hi, ob, opts, names = M.slot_meta()
    ks, np_, pnames = M.knob_table()
    off, lines = {}, []
    for key, items in (("name", names), ("opt", opts), ("page", pnames), ("note", M.NOTE_NAMES),
                       ("mode", [m for m, _ in M.MODES]), ("layer", [M.LAYER_LABEL[L] for L in LAYERS]),
                       ("qual", QUALS), ("misc", ["-", "RUN", "STOP", "M", ">", "NOTES", "LAT"])):
        off[key] = len(lines)
        lines += [w if w else "-" for w in items]
    for L in LAYERS:
        off["eng-" + L] = len(lines)
        lines += [e for e, _ in M.ENGINES[L]]
    return lines, off


QUALS = ["", "m", "dim", "+", "sus"]


# ---------------------------------------------------------------------------------------------- parameters
def params(c):
    c.comment("al-set 'slot value': store it, send it to [r al-s<slot>], redraw")
    r = c.ch(c.recv("al-set"), "unpack f f")
    val = c.obj("f")
    c.c((r, 1), 0, val, 1)
    t = c.to((r, 0), "t b b f f")
    tw = c.obj("tabwrite alp")
    snd = c.obj("s")
    c.c((t, 3), 0, tw, 1)
    c.c(c.to((t, 2), "makefilename al-s%d"), 0, snd, 1)
    c.c((t, 1), 0, val, 0)
    vt = c.to(val, "t f f")
    c.c((vt, 1), 0, tw, 0)
    c.c((vt, 0), 0, snd, 0)
    c.c((t, 0), 0, c.obj("s al-redraw"), 0)
    # every parameter out once at load
    proc(c, "al-sendall", [Loop(str(NSLOTS), "ali", [SendL("al-set", ["ali", "alp[ali]"])])])
    # an engine change: the layer's pages change - keep the page in range, pick up the knobs again
    for li, L in enumerate(LAYERS):
        ne = len(M.ENGINES[L])
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
    proc(c, "al-pickreset", [V(f"allat{k}", "0") for k in range(4)] + [Call("al-redraw")])
    for k in range(4):
        sc = Canvas(f"knob{k + 1}", w=1200)
        c.sub(sc)
        t = sc.ch(sc.recv(f"knob{k + 1}"), "t f f f")
        sl = sc.obj(f"expr alsl{k} = alks[({ctx()}*{MAXPAGES} + alpage)*4 + {k}]")
        sc.c(t, 2, sl, 0)
        dec = sc.obj(f"expr allat{k} = if(alsl{k} < 0, 0, allat{k} || abs($f1 - alp[alsl{k}]) < 0.025 || "
                     f"(alpv{k} >= 0 && (alpv{k} - alp[alsl{k}])*($f1 - alp[alsl{k}]) <= 0))")
        sc.c(t, 1, dec, 0)
        t2 = sc.to((t, 0), "t f f")
        sc.c((t2, 1), 0, sc.obj(f"v alpv{k}"), 0)
        g = sc.ch((t2, 0), f"expr if(allat{k}, $f1, -1)", "moses 0")
        tt = sc.to((g, 1), "t f b b")
        lp = sc.obj("list prepend")
        sc.c(sc.to((tt, 2), f"expr alsl{k}"), 0, lp, 1)
        sc.c((tt, 1), 0, sc.obj("s al-popup"), 0)
        sc.c((tt, 0), 0, lp, 0)
        sc.c(lp, 0, sc.obj("s al-set"), 0)
    proc(c, "al-popup", [V("alpop", "1"), Later("al-popoff", 5000)])
    proc(c, "al-popoff", [V("alpop", "0"), Call("al-redraw")])


# ---------------------------------------------------------------------------------------------- pages, layers
def pages(c):
    proc(c, "al-pgnext", [V("alpage", f"(alpage + 1) % {npages()}"), Call("al-pickreset"), Call("al-popup")])
    proc(c, "al-pgprev", [V("alpage", f"(alpage + {npages()} - 1) % {npages()}"), Call("al-pickreset"),
                          Call("al-popup")])
    for li, L in enumerate(LAYERS):
        proc(c, f"al-sel-{L}", [V("allayer", str(li)), V("alview", "0"), V("alpage", "0"), Call("al-pickreset"),
                                Call("al-popup")])
        proc(c, f"al-mute-{L}", [T("almute", str(li), f"1 - almute[{li}]"), SendL(f"al-mute{li}", [f"almute[{li}]"]),
                                 Call("al-redraw")])
    proc(c, "al-global", [If("alview", [V("alpage", f"(alpage + 1) % {len(M.GLOBAL_PAGES)}")],
                             [V("alview", "1"), V("alpage", "0")]), Call("al-pickreset"), Call("al-popup")])
    proc(c, "al-latch", [T("allatch", "allayer", "1 - allatch[allayer]"),
                         If("allatch[allayer] == 0", [Call("al-unlatch")]), Call("al-redraw")])
    proc(c, "al-unlatch", [
        If("allayer == 0 && aldhc == 0 && aldon", [SendL("al-drone-g", ["0", "0"]), V("aldon", "0")]),
        If("allayer == 1 && alshc == 0 && alson", [SendL("al-sub-g", ["0", "0"]), V("alson", "0")]),
        If("allayer == 2 && alphc == 0", [Call("al-prelall")])])
    proc(c, "al-clear", [
        T("alusr", "allayer", "0"),
        If("allayer == 0", [SendL("al-drone-g", ["0", "0"]), V("aldon", "0"), V("aldhc", "0")]),
        If("allayer == 1", [SendL("al-sub-g", ["0", "0"]), V("alson", "0"), V("alshc", "0")]),
        If("allayer == 2", [Call("al-prelall"), V("alphc", "0")]),
        If("alrun", [Call("al-chord")]), Call("al-redraw")])
    proc(c, "al-notesmode", [V("alnotes", "1 - alnotes"), Call("al-redraw")])


# ---------------------------------------------------------------------------------------------- Organelle keys
# one press each; aux held: the second set. Unlisted keys do nothing yet (later milestones).
KEYS = {60: "al-sel-drone", 61: "al-mute-drone", 62: "al-sel-sub", 63: "al-mute-sub", 64: "al-sel-pad",
        65: "al-sel-perc", 66: "al-mute-pad", 67: "al-global", 68: "al-mute-perc", 69: "al-pgprev", 70: "al-latch",
        71: "al-pgnext", 72: "al-startstop", 73: "al-clear", 74: "al-chordprev", 76: "al-chordnext",
        77: "al-popoff", 83: "al-notesmode"}
AUX_KEYS = {60: "al-sel-drone", 62: "al-sel-sub", 64: "al-sel-pad", 65: "al-sel-perc", 69: "al-pgprev",
            71: "al-pgnext", 72: "al-startstop", 83: "al-notesmode"}


def organelle(c):
    c.comment("the Organelle's keys: functions (KEYS), aux held: AUX_KEYS; in notes mode they play the shown layer")
    r = c.ch(c.recv("notesRaw"), "t b l")
    up = c.to((r, 1), "unpack f f")
    c.c((up, 1), 0, c.obj("v alkvel"), 0)
    c.c((up, 0), 0, c.obj("v alkn"), 0)
    run_steps(c, (r, 0), [If("alnotes && alaux == 0", [
        SendL("al-note", ["allayer", "alkn", "alkvel/127"])], [If("alkvel > 0", [
            V("alauxu", "if(alaux, 1, alauxu)"), Send("al-keyfn")])])])
    fn = c.ch(c.recv("al-keyfn"), "expr alkn + 100*alaux")
    sel = c.obj("sel " + " ".join(str(k) for k in KEYS) + " " + " ".join(str(k + 100) for k in AUX_KEYS))
    c.c(fn, 0, sel, 0)
    for i, name in enumerate(list(KEYS.values()) + list(AUX_KEYS.values())):
        c.c((sel, i), 0, c.obj(f"s {name}"), 0)
    a = c.ch(c.recv("aux"), "t f f")
    c.c(c.to((a, 1), "expr $f1 > 0"), 0, c.obj("v alaux"), 0)
    tap = c.ch((a, 0), "sel 0")
    run_steps(c, (tap, 0), [If("alauxu == 0", [Call("al-pgnext")])])
    run_steps(c, (tap, 1), [V("alauxu", "0")])


# ---------------------------------------------------------------------------------------------- MIDI in
def midi_in(c):
    c.comment("MIDI notes: channel 1 (and 6 - 16) play the shown layer; channels 2 - 5 the drone, sub, pads, "
              "percussion. [r al-midi] 'note vel ch' also lets the tests play.")
    n = c.obj("notein")
    pk = c.obj("pack f f f")
    c.c((n, 2), 0, pk, 2)
    c.c((n, 1), 0, pk, 1)
    c.c((n, 0), 0, pk, 0)
    c.c(pk, 0, c.obj("s al-midi"), 0)
    r = c.ch(c.recv("al-midi"), "t b l")
    up = c.to((r, 1), "unpack f f f")
    for i, nm in enumerate(("almn", "almv", "almc")):
        c.c((up, i), 0, c.obj(f"v {nm}"), 0)
    run_steps(c, (r, 0), [SendL("al-note", ["if(almc >= 2 && almc <= 5, almc - 2, allayer)", "almn", "almv/127"])])
    rt = c.ch(c.recv("al-note"), "route 0 1 2 3")
    for i, L in enumerate(LAYERS):
        c.c((rt, i), 0, c.obj(f"s al-in-{L}"), 0)


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
    return opt(S(L, None, "Artic"))


def mono(c, L):
    x = LX[L]
    li = LAYERS.index(L)
    n, v, hc, on, tn, tv = (f"al{x}n", f"al{x}v" if x != "s" else "alsv2", f"al{x}hc", f"al{x}on", f"al{x}tn",
                            f"al{x}tv")
    _entry(c, f"al-in-{L}", [n, v], f"al-in-{L}-do")
    proc(c, f"al-in-{L}-do", [If(f"{v} > 0", [
        T("alusr", str(li), "1"), V(tn, f"{n} + {octave(L)}"), V(tv, v), Call(f"al-mono-{L}"), V(hc, f"{hc} + 1")],
        [V(hc, f"max(0, {hc} - 1)"),
         If(f"allatch[{li}] == 0 && {hc} == 0 && {on}", [SendL(f"al-{L}-g", ["0", "0"]), V(on, "0")])])])
    ov = f"({hc} > 0 || (allatch[{li}] && {on}))"
    proc(c, f"al-mono-{L}", [
        SendL(f"al-{L}-n", ["0", tn, f"if({zone(L)} == 3 || ({zone(L)} == 2 && {ov}), {glide_ms(L)}, 0)"]),
        If(f"{zone(L)} == 0 || {ov} == 0 || {on} == 0", [SendL(f"al-{L}-g", ["0", tv]), V(on, "1")]),
        V(f"alcur{li}", tn), Call("al-redraw")])


def pads(c):
    _entry(c, "al-in-pad", ["alpn", "alpv2"], "al-in-pad-do")
    proc(c, "al-in-pad-do", [If("alpv2 > 0", [
        T("alusr", "2", "1"), If("alphc == 0", [Call("al-pbegin")]), V("alphc", "alphc + 1"),
        V("alptn", f"alpn + {octave('pad')}"), V("alptv", "alpv2"), V("alpkey", "alpn"), Call("al-pnote")],
        [V("alphc", "max(0, alphc - 1)"),
         If("allatch[2] == 0", [Loop("4", "alj", [If("alpk[alj] == alpn && alpg[alj]", [
             SendL("al-pad-g", ["alj", "0"]), T("alpg", "alj", "0"), T("alpk", "alj", "-1")])])],
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
        If(f"{z} == 0 || {ov} == 0", [SendL("al-pad-g", ["alpj", "alptv"])]),
        T("alpg", "alpj", "1"), T("alpvn", "alpj", "alptn"), T("alpa", "alpj", "1"), T("alpk", "alpj", "alpkey"),
        V("alclock", "alclock + 1"), T("alpt", "alpj", "alclock")])
    proc(c, "al-pend", [Loop("4", "alj", [If("alpa[alj] == 0 && alpg[alj]", [
        SendL("al-pad-g", ["alj", "0"]), T("alpg", "alj", "0")])])])
    proc(c, "al-prelall", [Loop("4", "alj", [If("alpg[alj]", [SendL("al-pad-g", ["alj", "0"]), T("alpg", "alj", "0")])])])


def perc(c):
    _entry(c, "al-in-perc", ["alcn", "alcv"], "al-in-perc-do")
    dec = f"50*pow(600, alp[{S('perc', None, 'Decay')}])"
    velo = f"alp[{S('perc', None, 'Velo')}]"
    proc(c, "al-in-perc-do", [If("alcv > 0", [V("alrr", f"(alrr + 1) % {NV['perc']}"),
                                              SendL("al-perc-hit", ["alrr", f"alcn + {octave('perc')}",
                                                                    f"1 - {velo}*(1 - alcv)", dec])])])


# ---------------------------------------------------------------------------------------------- transport, clock
def transport(c):
    c.comment("the clock: 24 a beat (MIDI clock), the layers' rhythm in 32nds (every 3). Sync: internal, or an "
              "incoming MIDI clock (start / stop follow it)")
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
                      If("alc24 % 3 == 0", [Call("al-tick")])])
    proc(c, "al-startstop", [If("alrun", [Call("al-stop")], [Call("al-start")])])
    proc(c, "al-start", [If("alrun == 0", [
        V("alrun", "1"), V("altick", "-1"), V("alc24", "-1"), V("alstep", "0"), Call("al-chord"),
        If(f"{opt(clk)} == 1", [Send("al-midibyte", "250")]),
        If(f"{opt(sync)} == 0", [Send("al-clock", "1")]), Call("al-redraw")])])
    proc(c, "al-stop", [If("alrun", [
        V("alrun", "0"), Send("al-clock", "0"), If(f"{opt(clk)} == 1", [Send("al-midibyte", "252")]),
        SendL("al-drone-g", ["0", "0"]), SendL("al-sub-g", ["0", "0"]), Call("al-prelall"),
        V("aldon", "0"), V("alson", "0"), V("aldhc", "0"), V("alshc", "0"), V("alphc", "0"),
        Loop("4", "alj", [T("alusr", "alj", "0")]), Call("al-redraw")])])
    # each 32nd: the percussion pattern (Euclidean: hits spread evenly over steps, rotated) and the story's bars
    hits, steps, rot, rate = (S("perc", None, n) for n in ("Hits", "Steps", "Rotate", "Rate"))
    div = "if(%s == 0, 8, if(%s == 1, 4, if(%s == 2, 2, 1)))" % ((opt(rate),) * 3)
    bars = S("g", None, "Bars")
    nb = "if(%s == 1, 1, if(%s == 2, 2, if(%s == 3, 4, if(%s == 4, 8, 16))))" % ((opt(bars),) * 4)
    idx = f"((altick/{div} + {num(rot)}) % {num(steps)})"
    proc(c, "al-tick", [
        V("altick", "altick + 1"),
        If(f"allatch[3] && altick % {div} == 0 && ({idx}*{num(hits)}) % {num(steps)} < {num(hits)}", [
            V("alpc", "(alpc + 1) % 4"),
            SendL("al-in-perc", ["alch[alpc]",
                                 f"if({idx} == 0, 1, 0.72)"])]),
        If(f"{opt(bars)} > 0 && altick > 0 && altick % (32*{nb}) == 0", [Call("al-chordnext")])])


# ---------------------------------------------------------------------------------------------- the chord story
def story(c):
    key, mode, st, sub_to, voic = (S("g", None, n) for n in ("Key", "Mode", "Story", "SubTo", "Voicng"))
    m, k = opt(mode), opt(key)
    ln = f"if({opt(st)} == 0, alsml[{m}], alsdl[{opt(st)}])"
    deg = f"if({opt(st)} == 0, alsm[{m}*8 + alcs % {ln}], alsd[{opt(st)}*8 + alcs % {ln}])"
    nsc = f"alscn[{m}]"

    def pc(i):
        return f"(alsc[{m}*7 + (alcd + {2 * i}) % {nsc}] + 12*int((alcd + {2 * i})/{nsc}))"
    # al-chordcalc: chord number alcs -> its root (pitch class, alcr), quality (alcq) and 4 tones (alct, from C4)
    third, fifth = f"(({pc(1)} - {pc(0)}) % 12)", f"(({pc(2)} - {pc(0)}) % 12)"
    vo = f"alp[{voic}]"
    proc(c, "al-chordcalc", [
        V("alcd", deg),
        V("alcr", f"({k} + alsc[{m}*7 + alcd % {nsc}]) % 12"),
        V("alcq", f"if({third} == 3 && {fifth} == 7, 1, if({third} == 4 && {fifth} == 7, 0, if({third} == 3 && "
                  f"{fifth} == 6, 2, if({third} == 4 && {fifth} == 8, 3, 4))))"),
        # the voicing: close; drop-2 (the third voice an octave down); open (the second an octave up)
        T("alct", "0", f"60 + {k} + {pc(0)}"),
        T("alct", "1", f"60 + {k} + {pc(1)} + 12*({vo} >= 0.66)"),
        T("alct", "2", f"60 + {k} + {pc(2)} - 12*({vo} >= 0.33 && {vo} < 0.66)"),
        T("alct", "3", f"60 + {k} + {pc(3)}")])
    sub_base = f"48 + if({opt(sub_to)} == 1, alcr, {k}) + {octave('sub')}"
    proc(c, "al-chord", [
        V("alcs", f"alstep + 1"), Call("al-chordcalc"), V("alnxr", "alcr"), V("alnxq", "alcq"),
        V("alcs", "alstep"), Call("al-chordcalc"),
        Loop("4", "alj", [T("alch", "alj", f"alct[alj] + {octave('pad')}")]),
        If("alrun", [
            If("alusr[0] == 0", [V("aldtn", f"48 + {k} + {octave('drone')}"), V("aldtv", "0.85"),
                                 Call("al-mono-drone")]),
            If("alusr[1] == 0", [V("alstn", sub_base), V("alstv", "0.85"), Call("al-mono-sub")]),
            If("alusr[2] == 0", [Call("al-pbegin"),
                                 Loop("4", "alci", [V("alptn", "alch[alci]"), V("alptv", "0.7"), V("alpkey", "-1"),
                                                    Call("al-pnote")]),
                                 Call("al-pend")])]),
        Call("al-redraw")])
    proc(c, "al-chordnext", [V("alstep", f"(alstep + 1) % ({ln.replace('alcs', 'alstep')})"), Call("al-chord")])
    proc(c, "al-chordprev", [V("alstep", f"(alstep + {ln} - 1) % ({ln})"), Call("al-chord")])
    # key, mode, story, voicing or the sub's target changed: the chord again
    for sl in (key, mode, st, sub_to, voic):
        c.c(c.ch(c.recv(f"al-s{sl}"), "t b"), 0, c.obj("s al-chord-later"), 0)
    c.c(c.ch(c.recv("al-chord-later"), "delay 5"), 0, c.obj("s al-chord"), 0)


def build(c):
    for fn in (tables, params, knobs, pages, organelle, midi_in, transport, story):
        sc = Canvas(fn.__name__, w=2600)
        c.sub(sc)
        fn(sc)
    for L in ("drone", "sub"):
        sc = Canvas(f"notes-{L}", w=2600)
        c.sub(sc)
        mono(sc, L)
    for fn in (pads, perc):
        sc = Canvas(f"notes-{fn.__name__}", w=2600)
        c.sub(sc)
        fn(sc)
    vals = Canvas("values")
    c.sub(vals)
    for name, v0 in GLOBALS.items():
        vals.obj(f"v {name}")
    lb = vals.obj("loadbang")
    m = vals.m(lb, "; " + "; ".join(f"al-v-{n} {v0}" for n, v0 in GLOBALS.items() if v0 != 0) or "")
    for name, v0 in GLOBALS.items():
        if v0 != 0:
            vals.c(vals.recv(f"al-v-{name}"), 0, vals.obj(f"v {name}"), 0)
