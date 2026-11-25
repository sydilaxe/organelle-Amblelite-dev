"""Milestone 3: the LFOs, assign mode, the snapshots (save, recall, morph, compare), the looper and the toasts.

LFOs: two per layer (its LFO 1 / LFO 2 pages): a target among the layer's parameters (model.targets), a rate (free in
Hz, synced in bars and beats, or 'loop': one cycle per loop - or per pattern cycle when nothing is recorded), a depth
and a shape. Every 20 ms each active LFO writes its movement (alfm: LFO 1, alfn: LFO 2) and the value the sound hears
(alpe = stored + Evolve + LFOs) goes out again when it moved.

Snapshots: 16, in saves.txt (one line each: every parameter, the latches, the mutes and the FAV pages). Hold top A#
and press a key (low C .. top D#) to recall, with aux to save. Recall morphs: the choices (engines, key, mode, story
...) switch at once, every other parameter glides over the Morph time (PERFRM page; 0 = at once). A tap of top A#
alone: COMPARE - back to the sound before the last recall, and again forward to it (morphing too).

Looper: one per layer, on the shown layer. Top D#: record, then play, then overdub, then play. Top F#: loop stop /
play. Top G#: clear. LOOP page: Len (auto: the recording rounded to bars; free: exactly as long as it was; or 1 - 16
bars), Quant (off .. 1/4), Follow (chord: the loop moves with the chord story, transposed at each cycle; exact),
Vel. What you play into a layer is recorded (not its pattern or the story's chords)."""
from pdlib import Canvas, proc, V, T, Send, Call, SendL, If, Loop, run_steps, Later, ACopy
import model as M
from model import S, LAYERS, MAXENG, MAXPAGES, NSLOTS, MAXC
from control import opt, num, pick, clocks, ctx, NL

BAR = 96                    # clocks in a 4/4 bar
MAXCLK = 16 * BAR           # the longest breath line a loop keeps (16 bars)
MAXEV = 256                 # events a loop holds
SAVE_SLOTS = 16
SCRATCH = SAVE_SLOTS        # (line 16 of saves.txt: the sound before the last recall, for COMPARE)
FAVN = NL * MAXENG * 4
SNAP = NSLOTS + 2 * NL + FAVN


def tables(c):
    """the LFOs' and assign mode's candidate parameters per layer and engine; the LFO slots per LFO"""
    cand = [-1] * (NL * MAXENG * MAXC)
    cnt = [0] * (NL * MAXENG)
    for li, L in enumerate(LAYERS):
        for ei, (e, _) in enumerate(M.engines(L)):
            t = M.targets(L, e)
            cnt[li * MAXENG + ei] = len(t)
            for i, sl in enumerate(t):
                cand[(li * MAXENG + ei) * MAXC + i] = sl
    lf = dict(allfT=[], allfR=[], allfD=[], allfS=[])
    for L in LAYERS:
        for n in (1, 2):
            for k, key in (("allfT", "Tgt"), ("allfR", "Rate"), ("allfD", "Dep"), ("allfS", "Shp")):
                lf[k].append(S(L, None, f"L{n}{key}"))
    rows = dict(alcand=cand, alccnt=cnt, allft=[-1] * (2 * NL), alstp=M.LFO_STEPS,
                allfbeats=[b or 0 for b in M.LFO_BEATS], allfsecs=M.LFO_SECS, **lf)
    for name, vals in rows.items():
        c.obj(f"array define {name} {len(vals)}")
        c.c(c.m(c.recv("al-init"), " ".join(f"{v:g}" for v in vals)), 0, c.obj(f"array set {name}"), 0)


# ---------------------------------------------------------------------------------------------- LFOs
def lfo(c):
    c.comment("the LFOs: every 40 ms, each active one moves its target (alfm / alfn)")
    met = c.obj("metro 40")
    c.c(c.recv("al-init"), 0, met, 0)
    c.c(met, 0, c.obj("s al-lfo"), 0)
    mc = MAXC
    li = "int(allq/2)"
    tgi = f"min({mc - 1}, int(alp[allfT[allq]]*{mc}))"
    tgt = f"if({tgi} == 0, -1, alcand[({li}*{MAXENG} + aleng[{li}])*{mc} + {tgi} - 1])"
    nr = len(M.LFO_RATES)
    r = f"min({nr - 1}, int(alp[allfR[allq]]*{nr}))"
    # 'loop': the layer's loop, or its pattern's cycle (steps x the step's clocks)
    pat = (f"max(1, int(2 + alp[alrs[{li}]]*14 + 0.5)*"
           f"{pick(M.RATE_CLOCKS, f'min({len(M.RATE_CLOCKS) - 1}, int(alp[alrr[{li}]]*{len(M.RATE_CLOCKS)}))')})")
    cyc = f"if(allpl[{li}] > 0, allpl[{li}], {pat})"
    ph = (f"if({r} == 0, max(0, alc24)/{cyc}, if({r} < 8, max(0, alc24)/(24*allfbeats[{r}]), "
          f"altime/allfsecs[{r} - 8] + 0.13*allq))")
    sh = f"min({len(M.LFO_SHAPES) - 1}, int(alp[allfS[allq]]*{len(M.LFO_SHAPES)}))"
    p1 = "(alfph - int(alfph))"
    # random: a new value each cycle (a hash of the cycle's number and the LFO's: the same settings give the same
    # 'random' line every time); stepped holds it, smooth glides to the next (smoothstep)
    def rnd(n):
        return f"(2*fmod(abs(sin(({n})*12.9898 + allq*78.233)*43758.5453), 1) - 1)"
    cy = "int(alfph)"
    sm = f"({p1}*{p1}*(3 - 2*{p1}))"
    val = (f"if({sh} == 0, sin(6.28319*{p1}), if({sh} == 1, 4*abs({p1} - 0.5) - 1, if({sh} == 2, 2*{p1} - 1, "
           f"if({sh} == 3, 1 - 2*{p1}, if({sh} == 4, if({p1} < 0.5, 1, -1), if({sh} == 5, alstp[int({p1}*8) % 8], "
           f"if({sh} == 6, {rnd(cy)} + ({rnd(cy + ' + 1')} - {rnd(cy)})*{sm}, {rnd(cy)})))))))")
    eff = "max(0, min(1, alp[alftg] + alem[alftg] + alfm[alftg] + alfn[alftg] + alfb[alftg]))"

    def refresh(slot):
        return [V("alfnew", eff.replace("alftg", slot)), If(f"abs(alfnew - alpe[{slot}]) > 0.0008", [
            T("alpe", slot, "alfnew"), SendL("al-out", [slot])])]
    proc(c, "al-lfo", [Loop(str(2 * NL), "allq", [If(f"allft[allq] >= 0 || alp[allfT[allq]] >= {1 / mc:.5f}", [
        V("alftg", tgt),
        # a new target: the old one let go
        If("alftg != allft[allq] && allft[allq] >= 0", [
            V("alfold", "allft[allq]"),
            If("allq % 2", [T("alfn", "alfold", "0")], [T("alfm", "alfold", "0")])] + refresh("alfold")),
        T("allft", "allq", "alftg"),
        If("alftg >= 0", [
            V("alfph", ph), V("alfv", f"alp[allfD[allq]]*0.5*({val})"),
            If("allq % 2", [T("alfn", "alftg", "alfv")], [T("alfm", "alftg", "alfv")])] + refresh("alftg"))])])])


# ---------------------------------------------------------------------------------------------- assign
def assign(c):
    """aux held + a knob: that knob's place on the FAV page takes a parameter of the layer (the knob chooses among
    them), and the FAV page shows"""
    for k in range(4):
        row = f"(allayer*{MAXENG} + aleng[allayer])"
        proc(c, f"al-assign{k}", [If("alview == 0", [
            V("alauxu", "1"), V("alpage", "0"),
            T("alks", f"({row}*{MAXPAGES})*4 + {k}",
              f"alcand[{row}*{MAXC} + min(alccnt[{row}] - 1, int(alasv*alccnt[{row}]))]"),
            V(f"allat{k}", "0"), V(f"alsl{k}", f"alks[({row}*{MAXPAGES})*4 + {k}]"), Call("al-popup")])])


# ---------------------------------------------------------------------------------------------- toasts
TOASTS = ["SAVED", "LOADED", "EMPTY", "COMPARE", "BACK", "REC", "PLAY", "DUB", "STOPPED", "CLEARED", "ASSIGN",
          "ROAD", "NEXT", "SECTION", "HOLD"]


def toast(name, number=None):
    """a short message over the play view's first line for 2 s"""
    return [V("altw", str(TOASTS.index(name))), V("altn", number if number is not None else "-1"),
            Send("al-toastarm"), Call("al-redraw")]


def toasts(c):
    # (one timer for every toast: a new one restarts it)
    c.c(c.ch(c.recv("al-toastarm"), "delay 2000"), 0, c.obj("s al-toastoff"), 0)
    proc(c, "al-toastoff", [V("altw", "-1"), Call("al-redraw")])


# ---------------------------------------------------------------------------------------------- snapshots
def saves(c):
    c.comment("the snapshots: saves.txt, a line each (parameters, latches, mutes, FAV pages); line 16: COMPARE's")
    tx = c.obj("text define al-saves")
    c.c(c.m(c.recv("al-init"), "read -c saves.txt"), 0, tx, 0)
    c.c(c.m(c.recv("al-savewrite"), "write -c saves.txt"), 0, tx, 0)
    for name, n in (("alsnap", SNAP), ("almf", NSLOTS), ("almt", NSLOTS), ("almi", NSLOTS)):
        c.obj(f"array define {name} {n}")
    # gather: the parameters, latches, mutes and FAV pages into alsnap
    fav = [((li * MAXENG + ei) * MAXPAGES) * 4 + k for li in range(NL) for ei in range(MAXENG) for k in range(4)]
    c.obj(f"array define alfavix {len(fav)}")
    c.c(c.m(c.recv("al-init"), " ".join(str(x) for x in fav)), 0, c.obj("array set alfavix"), 0)
    proc(c, "al-gather", [
        ACopy("alp", 0, NSLOTS, "alsnap", 0), ACopy("allatch", 0, NL, "alsnap", NSLOTS),
        ACopy("alin", 0, NL, "alsnap", NSLOTS + NL),
        Loop(str(FAVN), "alsi", [T("alsnap", f"{NSLOTS + 2 * NL} + alsi", "alks[alfavix[alsi]]")])])
    # write line n of saves.txt from alsnap (array get -> text set: the line replaced), then the file
    wr = c.to(c.recv("al-snapwrite"), "t b f")
    ts = c.obj("text set al-saves")
    c.c((wr, 1), 0, ts, 1)
    c.c(c.ch((wr, 0), "array get alsnap"), 0, ts, 0)
    c.c(c.ch(c.recv("al-snapwrite"), "t b", "delay 0"), 0, c.obj("s al-savewrite"), 0)
    # read line n into alsnap: alsnv = 1 if the line holds a snapshot
    rd = c.to(c.recv("al-snapread"), "t f b")
    c.c(c.m((rd, 1), "0"), 0, c.obj("v alsnv"), 0)
    tg = c.obj("text get al-saves")
    c.c((rd, 0), 0, tg, 0)
    ln = c.to(tg, "t l l")
    c.c(c.ch((ln, 1), "list length", f"expr $f1 == {SNAP}"), 0, c.obj("v alsnv"), 0)
    sp = c.obj("list split " + str(SNAP))
    c.c((ln, 0), 0, sp, 0)
    c.c(sp, 0, c.obj("array set alsnap"), 0)

    morph = S("g", None, "Morph")
    mms = f"if(alp[{morph}] < 0.02, 0, 100*pow(200, alp[{morph}]))"
    proc(c, "al-save", [Call("al-gather"), SendL("al-snapwrite", ["alslot"])] + toast("SAVED", "alslot + 1"))
    proc(c, "al-recall", [
        # the sound now kept for COMPARE, then the slot read
        Call("al-gather"), SendL("al-snapwrite", [str(SCRATCH)]), V("alcmp", "0"),
        SendL("al-snapread", ["alslot"]),
        If("alsnv", [V("allast", "alslot"), Call("al-apply")] + toast("LOADED", "alslot + 1"), toast("EMPTY"))])
    proc(c, "al-compare", [If("allast >= 0", [
        If("alcmp == 0", [Call("al-gather"), SendL("al-snapwrite", [str(SCRATCH + 1)]),
                          SendL("al-snapread", [str(SCRATCH)]), V("alcmp", "1")] + toast("COMPARE"),
           [SendL("al-snapread", [str(SCRATCH + 1)]), V("alcmp", "0")] + toast("BACK")),
        If("alsnv", [Call("al-apply")])])])
    # apply alsnap: latches, mutes, FAV pages at once; the choices at once; the rest glides (or all at once)
    proc(c, "al-apply", [
        Loop(str(NL), "alsi", [T("allatch", "alsi", f"alsnap[{NSLOTS} + alsi]"),
                               # (layers in or out: each fades with the Fade time)
                               If(f"alin[alsi] != alsnap[{NSLOTS + NL} + alsi]", [
                                   SendL("al-inset", ["alsi", f"alsnap[{NSLOTS + NL} + alsi]"])])]),
        Loop(str(FAVN), "alsi", [T("alks", "alfavix[alsi]", f"alsnap[{NSLOTS + 2 * NL} + alsi]")]),
        V("almcnt", "0"), V("almdur", mms),
        Loop(str(NSLOTS), "alsi", [If("abs(alsnap[alsi] - alp[alsi]) > 0.0005", [
            If("aln[alsi] != 0 || almdur == 0", [SendL("al-set", ["alsi", "alsnap[alsi]"])],
               [T("almi", "almcnt", "alsi"), T("almf", "almcnt", "alp[alsi]"), T("almt", "almcnt", "alsnap[alsi]"),
                V("almcnt", "almcnt + 1")])])]),
        Call("al-pickreset"),
        If("almcnt > 0", [V("almt0", "altime"), Send("al-morphclock", "1")])])
    met = c.obj("metro 50")
    c.c(c.recv("al-morphclock"), 0, met, 0)
    c.c(met, 0, c.obj("s al-morph"), 0)
    sm = "(almp*almp*(3 - 2*almp))"
    proc(c, "al-morph", [
        V("almp", "min(1, (altime - almt0)*1000/max(1, almdur))"),
        Loop("almcnt", "alsi", [SendL("al-set", ["almi[alsi]", f"almf[alsi] + (almt[alsi] - almf[alsi])*{sm}"])]),
        If("almp >= 1", [Send("al-morphclock", "0"), V("almcnt", "0")])])


# ---------------------------------------------------------------------------------------------- the looper
def looper(c):
    c.comment("the looper: one per layer. al-user-<layer> (what you play) is recorded, then goes to al-in-<layer>")
    for name in ("allpt", "allpn", "allpv", "allpq"):
        c.obj(f"array define {name} {NL * MAXEV}")
    for name in ("allpc", "allpl", "allps", "allp0", "allpi", "allpx", "allpr"):
        c.obj(f"array define {name} {NL}")
    # each layer's breath line: one value a clock (breath + 1; 0 = nothing recorded there), up to 16 bars
    c.obj(f"array define albk {NL * MAXCLK}")
    nl, ql, ll = len(M.LOOP_LENS), len(M.QUANTS), len(M.LOOP_BARS)

    def p(L, key):
        return S(L, None, key)
    for li, L in enumerate(M.NOTE_LAYERS):
        # the tap: store a note while recording or overdubbing (its time quantised, its chord root kept)
        r = c.ch(c.recv(f"al-user-{L}"), "t l l")
        c.c((r, 0), 0, c.obj(f"s al-in-{L}"), 0)
        up = c.to((r, 1), "unpack f f")
        c.c((up, 1), 0, c.obj(f"v allrv{li}"), 0)
        c.c((up, 0), 0, c.obj(f"v allrn{li}"), 0)
        c.c(c.to((r, 1), "t b"), 0, c.obj(f"s al-lrec{li}"), 0)
        q = pick(M.QUANT_CLOCKS, opt(p(L, "Quant")))
        tq = f"(int((alc24 - allp0[{li}])/{q} + 0.5)*{q})"
        tm = f"if(allpl[{li}] > 0, {tq} % allpl[{li}], {tq})"
        base = f"{li}*{MAXEV}"
        # insert in time order: shift the later events up one place
        proc(c, f"al-lrec{li}", [If(f"(allps[{li}] == 1 || allps[{li}] == 3) && allpc[{li}] < {MAXEV}", [
            V("allrt", tm), V("allk", f"allpc[{li}]"),
            Loop(f"allpc[{li}]", "alli", [If(f"allpt[{base} + allpc[{li}] - 1 - alli] > allrt", [
                V("allk", f"allpc[{li}] - 1 - alli"),
                T("allpt", f"{base} + allk + 1", f"allpt[{base} + allk]"),
                T("allpn", f"{base} + allk + 1", f"allpn[{base} + allk]"),
                T("allpv", f"{base} + allk + 1", f"allpv[{base} + allk]"),
                T("allpq", f"{base} + allk + 1", f"allpq[{base} + allk]")])]),
            T("allpt", f"{base} + allk", "allrt"), T("allpn", f"{base} + allk", f"allrn{li}"),
            T("allpq", f"{base} + allk", "alcr"),
            T("allpv", f"{base} + allk", f"allrv{li}"), T("allpc", str(li), f"allpc[{li}] + 1"),
            # (an event before the play pointer: the pointer moves past it, so this cycle doesn't play it twice)
            If(f"allk < allpi[{li}]", [T("allpi", str(li), f"allpi[{li}] + 1")])])])
    # the loop key on the shown layer: empty -> record -> play -> overdub -> play ...
    lb = f"{pick(M.LOOP_BARS, opt_layer('LpLen', nl))}"
    # the loop key: the shown layer's looper - or, with zones on, every zoned layer's together (one pass across the
    # keyboard records each zone's notes and breath)
    zones = S("g", None, "Zones")
    zoned = " || ".join(f"(alzl == {li} && {num(S(L, None, 'ZnLo'))} <= {num(S(L, None, 'ZnHi'))})"
                        for li, L in enumerate(M.NOTE_LAYERS))
    proc(c, "al-loop", [If(f"{opt(zones)} == 1", [
        Loop(str(len(M.NOTE_LAYERS)), "alzl", [If(zoned, [V("allx", "alzl"), Call("al-loopone")])])],
        [If(f"allayer < {len(M.NOTE_LAYERS)}", [V("allx", "allayer"), Call("al-loopone")])])])
    proc(c, "al-loopone", [
        If("alrun == 0", [Call("al-start")]),
        If("allps[allx] == 0", [T("allps", "allx", "1"), T("allp0", "allx", "max(0, alc24)"), T("allpc", "allx", "0"),
                                T("allpl", "allx", f"{lb}*{BAR}"), T("allpi", "allx", "0")] + toast("REC"),
           [If("allps[allx] == 1", [Call("al-loopclose")] + toast("PLAY"),
               [If("allps[allx] == 2", [T("allps", "allx", "3")] + toast("DUB"),
                   [T("allps", "allx", "2")] + toast("PLAY"))])])])
    # closing the first recording: its length (auto: rounded to bars; free: as played)
    proc(c, "al-loopclose", [
        V("allsz", "max(1, alc24 - allp0[allx])"),
        If("allpl[allx] == 0", [T("allpl", "allx", f"if({opt_layer('LpLen', nl)} == 1, allsz, "
                                                  f"max({BAR}, int(allsz/{BAR} + 0.5)*{BAR}))")]),
        Loop("allpc[allx]", "alli", [T("allpt", f"allx*{MAXEV} + alli", f"allpt[allx*{MAXEV} + alli] % allpl[allx]")]),
        T("allps", "allx", "2"), T("allpi", "allx", "0"), Call("al-redraw")])
    proc(c, "al-loopstop", [If("allps[allayer] == 2 || allps[allayer] == 3", [
        T("allps", "allayer", "4"), Call("al-loopnotesoff")] + toast("STOPPED"),
        [If("allps[allayer] == 4", [T("allps", "allayer", "2"), T("allpi", "allayer", "0")] + toast("PLAY"))])])
    # (clearing: the layer's breath line too - zeros: no breath recorded)
    clr = c.obj("array set albk")
    c.c(c.m(c.recv("al-bkclear"), " ".join(["0"] * MAXCLK)), 0, clr, 0)
    c.c(c.ch(c.recv("al-bkclearat"), f"* {MAXCLK}"), 0, clr, 1)
    proc(c, "al-loopclear", [SendL("al-bkclearat", ["allayer"]), Send("al-bkclear"), T("alblp", "allayer", "0"),
                             Call("al-breathapply"),
                             T("allps", "allayer", "0"), T("allpc", "allayer", "0"), T("allpl", "allayer", "0"),
                             Call("al-loopnotesoff")] + toast("CLEARED"))
    proc(c, "al-loopnotesoff", [Send("al-clear")])
    # playback, each clock: the events at this point of the cycle (up to 6 at one clock), transposed with the
    # chord (worked out at the cycle's start)
    steps = []
    for li, L in enumerate(M.NOTE_LAYERS):
        base = f"{li}*{MAXEV}"
        fol = opt(S(L, None, "Follow"))
        playing = f"(allps[{li}] == 2 || allps[{li}] == 3) && allpl[{li}] > 0"
        steps.append(If(f"allps[{li}] >= 1 && allps[{li}] <= 3", [
            # the point in the cycle (a first recording: since it began)
            V("allpos", f"if(allpl[{li}] > 0, (alc24 - allp0[{li}]) % max(1, allpl[{li}]), alc24 - allp0[{li}])"),
            If(playing, [
                If("allpos == 0", [T("allpi", str(li), "0"), T("allpx", str(li), "alcr")]),
                Loop("6", "alli", [If(f"allpi[{li}] < allpc[{li}] && allpt[{base} + allpi[{li}]] == allpos", [
                    # (follow: moved by the nearest step from the chord it was played over to the cycle's chord;
                    # a layer out: its loop keeps its place, silent)
                    If(f"alin[{li}]", [SendL(f"al-in-{L}", [f"allpn[{base} + allpi[{li}]] + if({fol} == 0, "
                                         f"(allpx[{li}] - allpq[{base} + allpi[{li}]] + 18) % 12 - 6, 0)",
                                         f"allpv[{base} + allpi[{li}]]*alpe[{S(L, None, 'LpVel')}]/0.8"])]),
                    T("allpi", str(li), f"allpi[{li}] + 1")])]),
                # its breath line, played where it holds one
                If(f"allpos < {MAXCLK} && albk[{li}*{MAXCLK} + allpos] > 0 && "
                   f"abs(albk[{li}*{MAXCLK} + allpos] - 1 - alblp[{li}]) > 0.002",
                   [T("alblp", str(li), f"albk[{li}*{MAXCLK} + allpos] - 1"), V("albdirty", "1")])]),
            # the breath line recorded: all through a first recording, and in an overdub where it breathes
            If(f"allpos < {MAXCLK} && (allps[{li}] == 1 || (allps[{li}] == 3 && albll[{li}] > 0.01))",
               [T("albk", f"{li}*{MAXCLK} + allpos", f"albll[{li}] + 1")]),
            # a first recording with a set length closes by itself
            If(f"allps[{li}] == 1 && allpl[{li}] > 0 && alc24 - allp0[{li}] >= allpl[{li}]", [
                V("allx", str(li)), Call("al-loopclose")])]))
    proc(c, "al-loops", [V("albdirty", "0")] + steps + [If("albdirty", [Call("al-breathapply")])])


def opt_layer(key, n):
    """an option of the shown layer's slot by key (the slot looked up by layer)"""
    sl = pick([S(L, None, key) for L in M.NOTE_LAYERS], "allx")
    return f"min({n - 1}, int(alp[{sl}]*{n}))"


GLOBALS = dict(allq=0, alftg=-1, alfold=0, alfnew=0, alfph=0, alfv=0, altw=-1, altn=-1, alslot=0, allast=-1,
               alcmp=0, alsnv=0, alsi=0, almdur=0, almt0=0, almp=0, almcnt=0, alslh=0, alslu=0, alasv=0,
               allx=0, allrt=0, allk=0, alli=0, allsz=0, allpos=0, alzl=0, allbp=0, albdirty=0)
for _li in range(NL):
    GLOBALS.update({f"allrn{_li}": 0, f"allrv{_li}": 0})


def build(c):
    for fn in (tables, lfo, assign, toasts, saves, looper):
        sc = Canvas("m3-" + fn.__name__, w=2600)
        c.sub(sc)
        fn(sc)
