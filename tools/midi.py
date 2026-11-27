"""MIDI in (milestone 4): notes, MPE, breath, keyboard zones and controller profiles.

Notes. Chans 'layers': channel 1 plays the shown layer, channels 2-9 one layer each (drone, sub, pads, perc 1-4,
cloud). Chans 'mpe': every channel plays, and each note keeps its own pitch bend (Bend: its range on channels 2-16;
channel 1 bends 2) and pressure (Press: expr = the note's level, breath = the breath). Zones on: a note goes to the
first layer whose zone (its BREATH page: ZoneLo .. ZoneHi) holds it - a split keyboard - instead of the shown layer.

Breath (the profile's 'breath' CCs, or pressure with Press = breath): each layer's BREATH page sends it to one of its
parameters (Target, Depth), as the LFOs do (alfb: the breath's movement). With zones on, a layer hears the breath
only while one of its zone's notes is held (so each zone's breath shapes its own layer) - and its looper records it
(features.looper: the breath as a line in the loop).

Controller profiles (MIDI page Profil): controllers/<name>.txt in the patch folder, read when chosen. A line:
    cc <number> <action> [argument];        note <channel> <number> <action> [argument];      mode <layers|mpe>;
actions: knob 1-8 (1-4 the page shown, 5-8 the next page), level <layer 1-8>, toggle <layer> (in / out), show
<layer>, breath, start, stop, startstop, chordnext, chordprev, loop, loopstop, loopclear, pgnext, pgprev, play, mix,
pattern. A note that is mapped does that instead of playing. LastCC (MIDI page) shows the last CC that came in."""
import os
from pdlib import Canvas, proc, V, T, Send, Call, SendL, If, Loop, run_steps
import model as M
import korg
from model import S, LAYERS, NOTE_LAYERS, MAXENG, MAXPAGES, MAXC
from control import opt, num, ctx, npages, NL

ACTIONS = ["knob", "level", "toggle", "show", "breath", "start", "stop", "startstop", "chordnext", "chordprev",
           "loop", "loopstop", "loopclear", "pgnext", "pgprev", "play", "mix", "pattern",
           # param <key>: one parameter, always (its key: layer.Name, layer.engine.Name, g.Name - slots.txt);
           # engp <layer*10 + k>: the layer's engine's k-th parameter, whichever engine it plays; loopl <layer>: that
           # layer's loop key (shown, then the loop pressed)
           "param", "engp", "loopl",
           # shape: the MIX view's SHAPE page (Filter, Reso, Drive, Blur) at once
           "shape"]
# what the one-press actions call
CALLS = dict(start="al-start", stop="al-stop", startstop="al-startstop", chordnext="al-chordnext",
             chordprev="al-chordprev", loop="al-loop", loopstop="al-loopstop", loopclear="al-loopclear",
             pgnext="al-pgnext", pgprev="al-pgprev", play="al-layerview", mix="al-mix", pattern="al-patview",
             shape="al-shape")

# the factory profiles. Korg's factory settings differ between versions and scenes: LastCC (MIDI page) shows what
# yours sends - edit controllers/user.txt (kept across updates) to match.
PROFILES = {
    "generic": ["# a general keyboard: the mod wheel and CC 2 as breath; CC 70-77 the 8 knobs",
                "cc 1 breath;", "cc 2 breath;"] + [f"cc {70 + k} knob {k + 1};" for k in range(8)],
    # (the KORG controllers with the Amble Lite sets: korg.py)
    "nanokey": korg.profile_key(),
    "nanoktl": korg.profile_ktl(),
    "korg": ["# both KORGs at once, with the Amble Lite sets (their channels apart): the nanoKEY Studio and the",
             "# nanoKONTROL Studio as in nanokey.txt and nanoktl.txt"]
            + [l for l in korg.profile_key() + korg.profile_ktl() if not l.startswith("#")],
    "dm48x": ["# Lekholm DM48X (MPE): every channel plays, each note its own bend and pressure; breath on CC 2",
              "# (and CC 11)", "mode mpe;", "cc 2 breath;", "cc 11 breath;"],
    "user": ["# your own profile: kept when a new version is copied over (edit it to match your controller)",
             "cc 1 breath;"],
}


def slot_key(i):
    """a parameter's name in a profile: layer.Name, layer.engine.Name (an engine's), g.Name (a global one)"""
    L, e, k = M.SLOTS[i][0]
    return f"{L}.{e}.{k}" if e else f"{L}.{k}"


def write_profiles(out):
    d = os.path.join(out, "controllers")
    os.makedirs(d, exist_ok=True)
    # (the parameters' names, a line each in slot order: 'param <key>' finds its slot here)
    open(os.path.join(out, "slots.txt"), "w").write("".join(slot_key(i) + "\n" for i in range(M.NSLOTS)))
    keys = {slot_key(i) for i in range(M.NSLOTS)}
    for name, lines in PROFILES.items():
        for l in lines:
            w = l.rstrip(";").split()
            if "param" in w:
                assert w[w.index("param") + 1] in keys, (name, l)
        p = os.path.join(d, f"{name}.txt")
        if name == "user" and os.path.exists(p):
            continue
        # (Pd's text reads ';' as the end of a line; '#' lines are comments - kept out of the parse below)
        open(p, "w").write("\n".join(l if not l.startswith("#") else "comment " + l[1:].replace(",", "").replace(";", "") + ";"
                                     for l in lines) + "\n")


GLOBALS = dict(alcch=1, alpch=0, alpcc=0, almlay=0, albr=0, alcv2=0, alcc2=0, alact=0, alarg=0, alpl=0, albrq=0, albtg=-1, albl=0, alpfx=0,
               alpfn=0)


def build(c):
    for fn in (tables, notes, expression, breath, profiles, ccs):
        sc = Canvas("midi-" + fn.__name__, w=2600)
        c.sub(sc)
        fn(sc)


def tables(c):
    # (each layer and engine: how many parameters its engine has - engp k goes no further)
    nep = [0] * (NL * MAXENG)
    for li, L in enumerate(LAYERS):
        for ei, (e, ps) in enumerate(M.engines(L)):
            nep[li * MAXENG + ei] = len(ps)
    rows = dict(alnep=nep, albrT=[S(L, None, "BTgt") for L in LAYERS], albrD=[S(L, None, "BDep") for L in LAYERS],
                alznL=[S(L, None, "ZnLo") for L in LAYERS], alznH=[S(L, None, "ZnHi") for L in LAYERS])
    for name, vals in rows.items():
        c.obj(f"array define {name} {len(vals)}")
        c.c(c.m(c.recv("al-init"), " ".join(str(v) for v in vals)), 0, c.obj(f"array set {name}"), 0)
    # per channel (1-16): the layer and voice its note went to, its bend; per layer: notes held in its zone, the
    # breath it hears (live / from its loop), the breath's target last moved
    for name, n in (("alchl", 17), ("alchv", 17), ("alchb", 17), ("alzh", NL), ("albll", NL), ("alblp", NL),
                    ("albtl", NL), ("alfb", M.NSLOTS)):
        c.obj(f"array define {name} {n}")
    c.c(c.m(c.recv("al-init"), " ".join(["-1"] * NL)), 0, c.obj("array set albtl"), 0)


def zone_of(note):
    """the first layer whose zone holds the note, or -1"""
    out = "-1"
    for li in range(NL - 1, -1, -1):
        out = f"if({note} >= {num(S(LAYERS[li], None, 'ZnLo'))} && {note} <= {num(S(LAYERS[li], None, 'ZnHi'))}, {li}, {out})"
    return out


def notes(c):
    c.comment("MIDI notes: a mapped note does its action; else to a layer (channel, zone or the shown layer)")
    n = c.obj("notein")
    pk = c.obj("pack f f f")
    for i in (2, 1, 0):
        c.c(n, i, pk, i)
    c.c(pk, 0, c.obj("s al-midi"), 0)
    r = c.ch(c.recv("al-midi"), "t b l")
    up = c.to((r, 1), "unpack f f f")
    for i, nm in enumerate(("almn", "almv", "almc")):
        c.c((up, i), 0, c.obj(f"v {nm}"), 0)
    chans, zones = S("g", None, "Chans"), S("g", None, "Zones")
    mpe = f"{opt(chans)} == 1"
    lay = (f"if({opt(zones)} == 1 && {zone_of('almn')} >= 0, {zone_of('almn')}, "
           f"if({mpe} == 0 && almc >= 2 && almc <= {NL + 1}, almc - 2, allayer))")
    run_steps(c, (r, 0), [
        V("almc", "(almc - 1) % 16 + 1"),
        If(f"alnta[(almc - 1)*128 + almn] > 0", [If("almv > 0", [V("alact", "alnta[(almc - 1)*128 + almn]"),
                                                                 V("alarg", "alntb[(almc - 1)*128 + almn]"),
                                                                 V("alcv2", "127"), Call("al-action")])], [
            V("almlay", lay),
            # (a note in a zone: held there, so the zone's layer hears the breath)
            If(f"{opt(zones)} == 1 && {zone_of('almn')} >= 0",
               [T("alzh", "almlay", "max(0, alzh[almlay] + if(almv > 0, 1, -1))")]),
            SendL("al-note", ["almlay", "almn", "almv/127"]),
            # MPE: the channel remembers its layer and voice (bend and pressure follow the note)
            If(f"{mpe} && almv > 0", [T("alchl", "almc", "almlay"),
                                      T("alchv", "almc", "if(almlay == 2, alpj, if(almlay >= 3 && almlay <= 6, "
                                                         "allrr[almlay - 3], 0))"),
                                      SendL("al-bend", ["almlay", "alchv[almc]", "alchb[almc]"]),
                                      SendL("al-press", ["almlay", "alchv[almc]", "1"])])])])
    rt = c.ch(c.recv("al-note"), "route " + " ".join(str(i) for i in range(NL)))
    for i, L in enumerate(LAYERS):
        c.c((rt, i), 0, c.obj(f"s al-user-{L}"), 0)


def expression(c):
    c.comment("MPE: pitch bend per channel -> the note's voice (al-<layer>-b 'voice semitones'); pressure -> its "
              "level (al-<layer>-x 'voice gain') or the breath")
    b = c.obj("bendin")
    bp = c.obj("pack f f")
    c.c(b, 1, bp, 1)
    c.c(b, 0, bp, 0)
    c.c(bp, 0, c.obj("s al-bendin"), 0)
    bend = S("g", None, "Bend")
    rng = f"if(almc == 1, 2, if({opt(bend)} == 0, 2, if({opt(bend)} == 1, 12, if({opt(bend)} == 2, 24, 48))))"
    r = c.ch(c.recv("al-bendin"), "t b l")
    up = c.to((r, 1), "unpack f f")
    c.c((up, 1), 0, c.obj("v alpfx"), 0)
    c.c((up, 0), 0, c.obj("v alpfn"), 0)
    run_steps(c, (r, 0), [V("almc", "(alpfx - 1) % 16 + 1"), T("alchb", "almc", f"(alpfn - 8192)/8192*{rng}"),
                          If(f"{opt(S('g', None, 'Chans'))} == 1 || almc == 1",
                             [SendL("al-bend", ["alchl[almc]", "alchv[almc]", "alchb[almc]"])])])
    tch = c.obj("touchin")
    tp = c.obj("pack f f")
    c.c(tch, 1, tp, 1)
    c.c(tch, 0, tp, 0)
    c.c(tp, 0, c.obj("s al-touchin"), 0)
    pr = S("g", None, "Press")
    r = c.ch(c.recv("al-touchin"), "t b l")
    up = c.to((r, 1), "unpack f f")
    c.c((up, 1), 0, c.obj("v alpfx"), 0)
    c.c((up, 0), 0, c.obj("v alpfn"), 0)
    run_steps(c, (r, 0), [V("almc", "(alpfx - 1) % 16 + 1"),
                          If(f"{opt(pr)} == 1", [SendL("al-press", ["alchl[almc]", "alchv[almc]", "alpfn/127"])]),
                          If(f"{opt(pr)} == 2", [SendL("al-breath", ["alpfn/127"])])])
    for name in ("al-bend", "al-press"):
        rt = c.ch(c.recv(name), "route " + " ".join(str(i) for i in range(len(NOTE_LAYERS))))
        for i, L in enumerate(NOTE_LAYERS):
            c.c((rt, i), 0, c.obj(f"s al-{L}-{'b' if name == 'al-bend' else 'x'}"), 0)


def breath(c):
    """the breath: live (al-breath 0..1) -> each layer that hears it (zones: only while a zone note is held) -> its
    target (alfb), with the layer's loop line if it plays one (albll: live, alblp: from the loop)"""
    c.comment("breath -> each layer's BREATH target (alfb), live or from its loop")
    tb = c.to(c.recv("al-breath"), "t b f")
    c.c((tb, 1), 0, c.obj("v albr"), 0)
    zones = S("g", None, "Zones")
    c.c(tb, 0, c.obj("s al-breathapply"), 0)
    tgt = M.target_slot("alp[albrT[albl]]", f"albl*{MAXENG} + aleng[albl]")
    eff = "max(0, min(1, alp[albtg] + alem[albtg] + alfm[albtg] + alfn[albtg] + alfb[albtg]))"
    proc(c, "al-breathapply", [Loop(str(NL), "albl", [
        T("albll", "albl", f"if({opt(zones)} == 0 || alzh[albl] > 0, albr, 0)"),
        V("albtg", tgt),
        # a new target: the old one let go
        If("albtg != albtl[albl] && albtl[albl] >= 0", [T("alfb", "albtl[albl]", "0"),
                                                        SendL("al-set", ["albtl[albl]", "alp[albtl[albl]]"])]),
        T("albtl", "albl", "albtg"),
        If("albtg >= 0", [T("alfb", "albtg", "max(albll[albl], alblp[albl])*alp[albrD[albl]]"),
                          V("albrq", eff),
                          If("abs(albrq - alpe[albtg]) > 0.002", [T("alpe", "albtg", "albrq"),
                                                                  SendL("al-out", ["albtg"])])])])])


def profiles(c):
    """the profile: controllers/<name>.txt read into the maps (alcca / alccb per CC, alnta / alntb per channel and
    note) when it is chosen. Each line in turn: [list append 0] gives every line an argument, [unpack] spreads it
    (right to left: the argument, the action, the number), [sel] turns the action's word into its number."""
    c.comment("controller profiles: controllers/<name>.txt -> the CC and note maps")
    for name, n in (("alcca", 16 * 128), ("alccb", 16 * 128), ("alnta", 16 * 128), ("alntb", 16 * 128)):
        c.obj(f"array define {name} {n}")
    tx = c.obj("text define al-ctl")
    keys = c.obj("text define al-keys")
    c.c(c.m(c.recv("al-init"), "read -c slots.txt"), 0, keys, 0)
    prof = S("g", None, "Profil")
    sel = c.ch(c.recv(f"al-s{prof}"), f"expr min({len(M.PROFILES) - 1}, int($f1*{len(M.PROFILES)}))", "change -1",
               "t f f")
    names = c.to((sel, 1), "sel " + " ".join(str(i) for i in range(len(M.PROFILES))))
    for i, name in enumerate(M.PROFILES):
        c.c(c.m((names, i), f"read controllers/{name}.txt"), 0, tx, 0)
    # (then: the maps cleared, each line parsed)
    go = c.to((sel, 0), "t b b b")
    c.c(c.m((go, 2), " ".join(["0"] * (16 * 128))), 0, c.obj("array set alcca"), 0)
    c.c(c.m((go, 1), " ".join(["0"] * (16 * 128))), 0, c.obj("array set alnta"), 0)
    sz = c.to(c.to((go, 0), "text size al-ctl"), "t f b")
    cnt = c.obj("f")
    c.c(c.m((sz, 1), "0"), 0, cnt, 1)
    u = c.to((sz, 0), "until")
    c.c(u, 0, cnt, 0)
    c.c(c.to(cnt, "+ 1"), 0, cnt, 1)
    rt = c.ch(cnt, "text get al-ctl", "list trim", "route cc note mode chcc")
    sels = "sel " + " ".join(ACTIONS)
    # cc <n> <action> [arg] (every channel), chcc <channel> <n> <action> [arg]: the argument first - a number, or a
    # parameter's name looked up in slots.txt - then the action, the CC, the channel (0: all), and the map is set
    cm = c.obj("list append 0")
    c.c(c.to((rt, 0), "list prepend 0"), 0, cm, 0)
    c.c((rt, 3), 0, cm, 0)
    head = c.to(cm, "list split 3")
    argv = c.to(c.to((head, 1), "list split 1"), "route float")
    av = c.obj("v alarg")
    c.c((argv, 0), 0, av, 0)
    c.c(c.to((argv, 1), "text search al-keys"), 0, av, 0)
    tl = c.to((head, 0), "t l b")
    c.c(c.m((tl, 1), "0"), 0, c.obj("v alact"), 0)        # (an action it doesn't know: none)
    hu = c.to(tl, "unpack f f s")
    _codes(c, c.to((hu, 2), sels))
    c.c((hu, 1), 0, c.obj("v alpcc"), 0)
    hc = c.to((hu, 0), "t b f")
    c.c((hc, 1), 0, c.obj("v alpch"), 0)
    c.c((hc, 0), 0, c.obj("s al-ccmap"), 0)
    proc(c, "al-ccmap", [If("alpch == 0", [Loop("16", "alj", [T("alcca", "alj*128 + alpcc", "alact"),
                                                               T("alccb", "alj*128 + alpcc", "alarg")])],
                            [T("alcca", "(alpch - 1)*128 + alpcc", "alact"), T("alccb", "(alpch - 1)*128 + alpcc", "alarg")])])
    # note <ch> <n> <action> [arg]
    nu = c.ch((rt, 1), "t l b")
    c.c(c.m((nu, 1), "0"), 0, c.obj("v alact"), 0)
    up = c.ch((nu, 0), "list append 0", "unpack f f s f")
    c.c((up, 3), 0, c.obj("v alarg"), 0)
    _codes(c, c.to((up, 2), sels))
    c.c((up, 1), 0, c.obj("v alpl"), 0)
    c.c((up, 0), 0, c.obj("expr alnta[($f1 - 1)*128 + alpl] = alact; alntb[($f1 - 1)*128 + alpl] = alarg"), 0)
    # mode layers | mpe
    md = c.to((rt, 2), "route layers mpe")
    chans = S("g", None, "Chans")
    c.c(c.m(md, f"{chans} 0.25"), 0, c.obj("s al-set"), 0)
    c.c(c.m((md, 1), f"{chans} 0.75"), 0, c.obj("s al-set"), 0)


def _codes(c, sel):
    """[sel action ...] -> alact = the action's number (1 ..)"""
    v = c.obj("v alact")
    for i in range(len(ACTIONS)):
        c.c(c.m((sel, i), str(i + 1)), 0, v, 0)


def ccs(c):
    c.comment("CCs: the profile's map (alcca, alccb) -> its action; every CC shown as LastCC")
    cc = c.obj("ctlin")
    cp = c.obj("pack f f f")
    for i in (2, 1, 0):
        c.c(cc, i, cp, i)
    c.c(cp, 0, c.obj("s al-cc"), 0)
    r = c.ch(c.recv("al-cc"), "t b l")
    up = c.to((r, 1), "unpack f f f")
    c.c((up, 2), 0, c.obj("v alcch"), 0)
    c.c((up, 1), 0, c.obj("v alcc2"), 0)
    c.c((up, 0), 0, c.obj("v alcv2"), 0)
    last = S("g", None, "LastCC")
    at = "((alcch - 1) % 16)*128 + alcc2"
    run_steps(c, (r, 0), [
        T("alp", str(last), "alcc2/127"), Call("al-redraw"),
        If(f"alcca[{at}] > 0", [V("alact", f"alcca[{at}]"), V("alarg", f"alccb[{at}]"), Call("al-action")])])
    # the actions: alact (1 ..), alarg its argument, alcv2 the value (0 .. 127)
    knob = ACTIONS.index("knob") + 1
    steps = [
        # knob 1-4: the page shown; 5-8: the next page - set at once (a controller's knob jumps)
        If(f"alact == {knob} && alarg >= 1 && alarg <= 8", [
            V("alpl", f"alks[({ctx()}*{MAXPAGES} + if(alarg <= 4, alpage, (alpage + 1) % {npages()}))*4 + (alarg - 1) % 4]"),
            If("alpl >= 0", [SendL("al-set", ["alpl", "alcv2/127"]), Call("al-popup")])]),
        If(f"alact == {ACTIONS.index('level') + 1} && alarg >= 1 && alarg <= {NL}",
           [SendL("al-set", [_pick([S(L, None, 'Level') for L in LAYERS], "alarg - 1"), "alcv2/127"])]),
        If(f"alact == {ACTIONS.index('breath') + 1}", [SendL("al-breath", ["alcv2/127"])]),
        If(f"alact == {ACTIONS.index('param') + 1} && alarg >= 0", [SendL("al-set", ["alarg", "alcv2/127"])]),
        # (an engine's k-th parameter: its pages come after FAV and LAYER, four a page)
        If(f"alact == {ACTIONS.index('engp') + 1} && alarg >= 11 && alarg <= {NL}8 && alarg % 10 >= 1 && "
           f"alarg % 10 <= alnep[(int(alarg/10) - 1)*{MAXENG} + aleng[int(alarg/10) - 1]]", [
            V("alpl", f"alks[(((int(alarg/10) - 1)*{MAXENG} + aleng[int(alarg/10) - 1])*{MAXPAGES} + 2 + "
                      f"int((alarg % 10 - 1)/4))*4 + (alarg % 10 - 1) % 4]"),
            If("alpl >= 0", [SendL("al-set", ["alpl", "alcv2/127"])])]),
        # the buttons act on a press (64 and up)
        If("alcv2 >= 64", [
            If(f"alact == {ACTIONS.index('toggle') + 1} && alarg >= 1 && alarg <= {NL}",
               [SendL("al-togn", ["alarg - 1"])]),
            If(f"alact == {ACTIONS.index('show') + 1} && alarg >= 1 && alarg <= {NL}",
               [SendL("al-shown", ["alarg - 1"])]),
            If(f"alact == {ACTIONS.index('loopl') + 1} && alarg >= 1 && alarg <= {len(NOTE_LAYERS)}",
               [SendL("al-shown", ["alarg - 1"]), Call("al-loop")])] +
           [If(f"alact == {ACTIONS.index(a) + 1}", [Call(cl)]) for a, cl in CALLS.items()])]
    proc(c, "al-action", steps)
    for name, pre in (("al-togn", "al-tog-"), ("al-shown", "al-sel-")):
        rt = c.ch(c.recv(name), "route " + " ".join(str(i) for i in range(NL)))
        for i, L in enumerate(LAYERS):
            c.c((rt, i), 0, c.obj(f"s {pre}{L}"), 0)


def _pick(values, idx):
    out = str(values[-1])
    for i in range(len(values) - 2, -1, -1):
        out = f"if({idx} == {i}, {values[i]}, {out})"
    return out
