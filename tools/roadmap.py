"""The roadmap (milestone 6): a piece as sections, built from a few settings, edited, and played along.

Build (aux + top C#; the ROAD page): Mins (the piece's length), Arc (the roles of its sections: arch, build, waves,
twin, journey), Tension (how far its harmony goes: calm stories - float, suspend, modal ... - to experimental ones -
mediants, hexatonic, the tritone ...; climaxes reach further, the ends less), Density (how many layers play), Varia
(another, equally repeatable, plan). Rules, no dice: the same settings give the same roadmap.

A section: its bars, its story, its role, the layers in it. Road (ROAD 2): off; guide (a toast says what is next,
the roadmap view shows it - you play it); auto (at each section the layers fade in and out and the story changes).
aux + top F#: hold the section (again: let it go); aux + top G#: on to the next. The SECTN page edits a section
(Sect chooses it; Bars, Story, Role); while it shows, the layer keys toggle the layers in that section.

The roadmap is kept in roadmap.txt (a line a section: bars story mask role) - read at load, written when built or
edited; the web planner writes the same file."""
from pdlib import Canvas, proc, V, T, Send, Call, SendL, If, Loop, ACopy
import model as M
from model import S, LAYERS
from control import opt, num, pick
from features import toast

NL = len(LAYERS)
WEIGHTS = [1, 1, 1.5, 1, 1, 0.7, 1, 1]          # each role's share of the piece
# the layers each role brings in (a mask over LAYERS), for low / middle / high density
_L = {L: 1 << i for i, L in enumerate(LAYERS)}
D, Sb, P, P1, P2, P3, P4, Cl = (_L[k] for k in ("drone", "sub", "pad", "perc1", "perc2", "perc3", "perc4", "cloud"))
MASKS = [  # emerge, establish, develop, intensify, climax, break, return, dissolve
    [D, D, D | Sb],
    [D | Sb | P, D | Sb | P, D | Sb | P | P1],
    [D | Sb | P | Cl, D | Sb | P | P1 | Cl, D | Sb | P | P1 | P2 | Cl],
    [D | Sb | P | P1, D | Sb | P | P1 | P2 | P3, D | Sb | P | P1 | P2 | P3 | P4],
    [D | Sb | P | P1 | Cl, D | Sb | P | P1 | P2 | P3 | Cl, (1 << NL) - 1],
    [D | Cl, D | P | Cl, D | P | P2 | Cl],
    [D | Sb | P, D | Sb | P | P1, D | Sb | P | P1 | P3],
    [D, D | Cl, D | P | Cl]]
TENSION = [0.6, 0.8, 1.0, 1.2, 1.4, 0.9, 0.8, 0.5]   # how far each role's harmony reaches (x Tension)
POOLS = [["float", "suspend", "still6", "modal", "pedal", "gymno", "planing", "sus"],
         ["modal", "dorvamp", "mixvamp", "lydfloat", "minimal", "diamed", "axis", "home"],
         ["mediant", "neoriem", "hexaton", "thirds", "octaton", "epic", "andalus", "tritone"]]
MAXR = 8


def tables(c):
    names = [n for n, _, _ in M.STORIES]
    rows = dict(alrarc=[r for a in M.ARCS for r in (M.ARC_ROLES[a] + [-1] * MAXR)[:MAXR]],
                alrarn=[len(M.ARC_ROLES[a]) for a in M.ARCS], alrw=WEIGHTS, alrten=TENSION,
                alrmsk=[m for role in MASKS for m in role],
                alrpool=[names.index(n) for p in POOLS for n in p])
    for name, vals in rows.items():
        c.obj(f"array define {name} {len(vals)}")
        c.c(c.m(c.recv("al-init"), " ".join(f"{v:g}" for v in vals)), 0, c.obj(f"array set {name}"), 0)
    for name in ("alrsL", "alrsS", "alrsM", "alrsR"):
        c.obj(f"array define {name} {M.MAXSEC}")


GLOBALS = dict(alrn=0, alrc=0, alrb0=0, alrhold=0, alri=0, alrtot=0, alrsw=0, alrt=0, alrdn=0, alrl=0, alrsec=0,
               alrq=0, alrbar=0, alrcn=0, alrcj=0, alrck=0, alrcf=0, alrcs=0)


def build(c):
    for fn in (tables, generate, run, edit, store, changes):
        sc = Canvas("road-" + fn.__name__, w=2600)
        c.sub(sc)
        fn(sc)


def generate(c):
    mins, arc, ten, dens, var = (S("g", None, k) for k in ("Mins", "Arc", "Tensn", "RDens", "Varia"))
    tempo = S("g", None, "Tempo")
    a = opt(arc)
    role = f"alrarc[{a}*{MAXR} + alri]"
    tier = f"min(2, int(alp[{ten}]*alrten[{role}]*2.2))"
    dt = f"min(2, int(alp[{dens}]*2.99))"
    proc(c, "al-rgen", [
        V("alrn", f"alrarn[{a}]"),
        # the bars: the piece's length at its tempo, shared by the roles' weights, in 4s
        V("alrtot", f"{num(mins)}*{num(tempo)}/4"), V("alrsw", "0"),
        Loop("alrn", "alri", [V("alrsw", f"alrsw + alrw[{role}]")]),
        Loop("alrn", "alri", [
            T("alrsR", "alri", role),
            T("alrsL", "alri", f"max(4, int(alrtot*alrw[{role}]/alrsw/4 + 0.5)*4)"),
            T("alrsM", "alri", f"alrmsk[{role}*3 + {dt}]"),
            T("alrsS", "alri", f"alrpool[{tier}*8 + ({num(var)}*5 + alri*3 + {a}) % 8]")]),
        V("alrc", "0"), V("alrb0", "0"), Call("al-rsave"), Call("al-rsectload")] + toast("ROAD") + [
        Call("al-redraw")])


def run(c):
    road = S("g", None, "Road")
    st = S("g", None, "Story")
    auto = f"{opt(road)} == 2"
    # applying a section (auto): each layer in or out as its mask says; its story from the first chord
    proc(c, "al-rapply", [If(f"{auto} && alrn > 0", [
        Loop(str(NL), "alrl", [If("alin[alrl] != (int(alrsM[alrc]/pow(2, alrl)) % 2)", [
            SendL("al-inset", ["alrl", "int(alrsM[alrc]/pow(2, alrl)) % 2"])])]),
        V("alstep", "0"),
        SendL("al-set", [str(st), f"(alrsS[alrc] + 0.5)/{len(M.STORIES)}"]), Call("al-rcapply")])])
    # each bar: the section ends? on to the next (unless held); guide: a toast a bar before
    proc(c, "al-rbar", [If(f"{opt(road)} > 0 && alrn > 0", [
        V("alrbar", "altick/32"),
        If(f"{opt(road)} == 1 && alrbar - alrb0 == alrsL[alrc] - 1 && alrc + 1 < alrn", toast("NEXT", "alrc + 2")),
        If("alrhold == 0 && alrbar - alrb0 >= alrsL[alrc]", [Call("al-rnext")]),
        # (the play view's roadmap line moves on each bar)
        If("alview == 0 && alpop == 0 && alpatv == 0", [Call("al-redraw")])])])
    proc(c, "al-rnext", [If("alrn > 0", [
        V("alrc", "if(alrc + 1 < alrn, alrc + 1, alrc)"), V("alrb0", "max(0, altick/32)"),
        Call("al-rapply")] + toast("SECTION", "alrc + 1") + [Call("al-redraw")])])
    proc(c, "al-rhold", [V("alrhold", "1 - alrhold")] + toast("HOLD") + [Call("al-redraw")])
    # Start: the first section
    proc(c, "al-rstart", [V("alrc", "0"), V("alrb0", "0"), V("alrhold", "0"), Call("al-rapply")])


def edit(c):
    """SECTN page: Sect chooses the section (its values loaded into Bars, Story, Role); turning those writes them
    back; with the page shown, a layer key toggles that layer in the section"""
    sect, bars, story, role = (S("g", None, k) for k in ("Sect", "SBars", "SStory", "SRole"))
    ns, nr = len(M.STORIES), len(M.ROLES)
    proc(c, "al-rsectload", [V("alrsec", f"min(max(0, alrn - 1), {num(sect)} - 1)"), If("alrn > 0", [
        SendL("al-set", [str(bars), f"(alrsL[alrsec] - 4)/60"]),
        SendL("al-set", [str(story), f"(alrsS[alrsec] + 0.5)/{ns}"]),
        SendL("al-set", [str(role), f"(alrsR[alrsec] + 0.5)/{nr}"])])])
    c.c(c.ch(c.recv(f"al-s{sect}"), "t b"), 0, c.obj("s al-rsectload"), 0)
    for sl, arr, val in ((bars, "alrsL", num(bars)), (story, "alrsS", opt(story)), (role, "alrsR", opt(role))):
        proc(c, f"al-rw-{arr}", [If("alrn > 0 && alrsec < alrn", [T(arr, "alrsec", val), Call("al-rsavelater")])])
        c.c(c.ch(c.recv(f"al-s{sl}"), "t b"), 0, c.obj(f"s al-rw-{arr}"), 0)
    _entry_toggle(c)


def _entry_toggle(c):
    # a layer key while the SECTN page shows: that layer in / out of the section (from control's al-tog-<layer>)
    proc(c, "al-rtog", [If("alrn > 0 && alrsec < alrn", [
        T("alrsM", "alrsec", "if(int(alrsM[alrsec]/pow(2, alrq)) % 2, alrsM[alrsec] - pow(2, alrq), "
                             "alrsM[alrsec] + pow(2, alrq))"),
        Call("al-rsavelater"), Call("al-redraw")])])


def store(c):
    """roadmap.txt: a line a section 'bars story mask role'"""
    tx = c.obj("text define al-road")
    c.c(c.m(c.recv("al-init"), "read roadmap.txt"), 0, tx, 0)
    # at load: the sections from the file (if it holds any)
    ld = c.ch(c.recv("al-init"), "delay 20", "t b b")
    sz = c.ch((ld, 1), "text size al-road", "t f f")
    c.c((sz, 1), 0, c.obj(f"expr alrn = min({M.MAXSEC}, $f1)"), 0)
    u = c.to((sz, 0), "until")
    cnt = c.obj("f")
    c.c(c.m(c.recv("al-init"), "0"), 0, cnt, 1)
    c.c(u, 0, cnt, 0)
    c.c(c.to(cnt, "+ 1"), 0, cnt, 1)
    tcnt = c.to(cnt, "t f f")
    up = c.ch((tcnt, 1), "text get al-road", "list append 0 0 0 0", "unpack f f f f")
    e = c.obj("expr alrsL[$f1] = $f2; alrsS[$f1] = $f3; alrsM[$f1] = $f4; alrsR[$f1] = $f5")
    for i in (3, 2, 1):
        c.c((up, i), 0, e, i + 1)
    c.c((up, 0), 0, e, 1)
    c.c(tcnt, 0, e, 0)
    c.c(c.ch((ld, 0), "t b", "expr alrn = if(alrsL[0] < 1, 0, alrn)"), 0, c.obj("s al-rsectload"), 0)
    # write: every section, then the file (a little after an edit, so a turning knob writes once)
    c.c(c.ch(c.recv("al-rsavelater"), "delay 400"), 0, c.obj("s al-rsave"), 0)
    # (no sections: one line of zeros - Pd can't write an empty file - read back as none)
    proc(c, "al-rsave", [Send("al-roadclear"), Loop("alrn", "alri", [SendL(
        "al-roadline", ["alri", "alrsL[alri]", "alrsS[alri]", "alrsM[alri]", "alrsR[alri]"])]),
        If("alrn == 0", [SendL("al-roadline", ["0", "0", "0", "0", "0"])]), Send("al-roadwrite")])
    c.c(c.m(c.recv("al-roadclear"), "clear"), 0, tx, 0)
    c.c(c.m(c.recv("al-roadwrite"), "write roadmap.txt"), 0, tx, 0)
    # (one line at a time, appended: [text insert] at the end)
    li = c.ch(c.recv("al-roadline"), "list split 1")
    ins = c.obj("text insert al-road 1e+06")
    c.c((li, 1), 0, ins, 0)


# ---------------------------------------------------------------------------------------------- section changes
MAXCH = 32          # parameter changes a section holds
# the parameters a section's changes may hold: the sound's - every layer's, MAIN, INPUT, Evolve and Volume, SHAPE,
# the story's Bars, SubTo and Voicing - not the settings (pieces, roadmap, MIDI, sync, the assistant, Morph ...) nor
# the Story, which the section sets itself
_KEEP_PAGES = {"MAIN", "INPUT", "STORY"}
_DROP = {("g", None, k) for k in ("Story", "Morph", "CmpGl")}


def capturable():
    gp = {("g", None, p.key): n for n, ps in M.GLOBAL_PAGES for p in ps if isinstance(p, M.Param)}
    return [0 if key in _DROP or (key in gp and gp[key] not in _KEEP_PAGES and key[2] not in ("Evolve", "Volume"))
            else 1 for key, _ in M.SLOTS]


def changes(c):
    """Each section's parameter changes, cumulative: when a section starts (Road auto) its changes are applied on
    top of the sound as it is - knob values glide over Morph (as a recall does), choices switch at once.
    roadchg.txt: the roadmap's, a line a section: 'n slot value slot value ...' (n pairs); sections.txt: each
    piece's, a line a piece and section (piece*MAXSEC + section) - saved and loaded with the piece.
    Capture (SECTN page, top A#): what you changed since the section started, since you chose it on the SECTN page
    or since the last capture, merged into the chosen section's changes; aux + top A#: that section's changes
    cleared."""
    import features as F
    n = 1 + 2 * MAXCH
    c.obj(f"array define alrct {n}")
    c.obj(f"array define alrbase {M.NSLOTS}")
    c.obj(f"array define alrcx {M.NSLOTS}")
    c.c(c.m(c.recv("al-init"), " ".join(str(v) for v in capturable())), 0, c.obj("array set alrcx"), 0)
    for name, fname, lines in (("al-roadchg", "roadchg.txt", M.MAXSEC),
                               ("al-sections", "sections.txt", F.PIECES * M.MAXSEC)):
        tx = c.obj(f"text define {name}")
        F.read_padded(c, tx, name, fname, lines, "0")
        c.c(c.m(c.recv(f"{name}-write"), f"write -c {fname}"), 0, tx, 0)
        c.col(300)
    # a line into alrct ('al-rcget line': alrct[0] the count, then the pairs); alrct back into a line
    g = c.ch(c.recv("al-rcget"), "text get al-roadchg", "list append 0")
    c.c(g, 0, c.obj("array set alrct"), 0)
    # ('al-rcput line': alrct's count and pairs as that line - the line number first, then the list: the whole
    # array, split after the count's pairs)
    put = c.to(c.recv("al-rcput"), "t b b f")
    ts = c.obj("text set al-roadchg")
    c.c((put, 2), 0, ts, 1)
    sp = c.obj("list split 1")
    c.c(c.to((put, 1), "expr 1 + 2*alrct[0]"), 0, sp, 1)
    c.c(c.to((put, 0), "array get alrct"), 0, sp, 0)
    c.c(sp, 0, ts, 0)
    # a piece's lines and the roadmap's: 'al-rc2p from to' (roadmap -> piece), 'al-p2rc from to'
    for rcv, src, dst in (("al-rc2p", "al-roadchg", "al-sections"), ("al-p2rc", "al-sections", "al-roadchg")):
        u = c.to(c.recv(rcv), "unpack f f")
        tset = c.obj(f"text set {dst}")
        c.c((u, 1), 0, tset, 1)
        c.c(c.ch((u, 0), f"text get {src}"), 0, tset, 0)
    morph = S("g", None, "Morph")
    mms = f"if(alp[{morph}] < 0.02, 0, 100*pow(200, alp[{morph}]))"
    slot, val = "alrct[1 + 2*alrcj]", "alrct[2 + 2*alrcj]"
    # applying: the playing section's changes (choices at once, the rest over Morph), then the baseline for capture
    proc(c, "al-rcapply", [
        SendL("al-rcget", ["alrc"]), V("alrcn", f"min({MAXCH}, alrct[0])"),
        V("almcnt", "0"), V("almdur", mms), V("alapl", "1"),
        Loop("alrcn", "alrcj", [If(f"{slot} >= 0 && {slot} < {M.NSLOTS}", [
            If(f"aln[int({slot})] != 0 || almdur == 0", [SendL("al-set", [slot, val])],
               [T("almi", "almcnt", slot), T("almf", "almcnt", f"alp[int({slot})]"), T("almt", "almcnt", val),
                V("almcnt", "almcnt + 1")])])]),
        V("alapl", "0"), If("almcnt > 0", [V("almt0", "altime"), Send("al-morphclock", "1")]),
        ACopy("alp", 0, M.NSLOTS, "alrbase", 0),
        Loop("alrcn", "alrcj", [If(f"{slot} >= 0 && {slot} < {M.NSLOTS}", [T("alrbase", f"int({slot})", val)])])])
    # the baseline: also when a section is chosen on the SECTN page (and at load, at a piece's load)
    proc(c, "al-rcbase", [ACopy("alp", 0, M.NSLOTS, "alrbase", 0)])
    c.c(c.ch(c.recv("al-rsectload"), "t b"), 0, c.obj("s al-rcbase"), 0)
    # capture: each changed parameter (that may be held) into the chosen section - its pair updated, else added
    proc(c, "al-rccapture", [If("alrn > 0 && alrsec < alrn", [
        SendL("al-rcget", ["alrsec"]), V("alrcn", f"min({MAXCH}, alrct[0])"), V("alrcf", "0"),
        Loop(str(M.NSLOTS), "alrck", [If("alrcx[alrck] && abs(alp[alrck] - alrbase[alrck]) > 0.0005", [
            V("alrcs", "-1"),
            Loop("alrcn", "alrcj", [If(f"{slot} == alrck", [V("alrcs", "alrcj")])]),
            If("alrcs >= 0", [T("alrct", "2 + 2*alrcs", "alp[alrck]")],
               [If(f"alrcn < {MAXCH}", [T("alrct", "1 + 2*alrcn", "alrck"), T("alrct", "2 + 2*alrcn", "alp[alrck]"),
                                       V("alrcn", "alrcn + 1")], [V("alrcf", "1")])])])]),
        T("alrct", "0", "alrcn"), SendL("al-rcput", ["alrsec"]), Send("al-roadchg-write"), Call("al-rcbase")]
        + toast("CAPTURED", "alrcn") + [If("alrcf", toast("FULL"))], toast("NO ROAD"))])
    proc(c, "al-rcclear", [If("alrn > 0 && alrsec < alrn", [
        T("alrct", "0", "0"), SendL("al-rcput", ["alrsec"]), Send("al-roadchg-write"), Call("al-rcbase")]
        + toast("CLEARED"))])
    # with a piece: saved from the roadmap's (features.pieces: al-psave), loaded into it (al-pload)
    pc = opt(S("g", None, "Piece"))
    proc(c, "al-rcpsave", [Loop(str(M.MAXSEC), "alrcj", [SendL("al-rc2p", ["alrcj", f"{pc}*{M.MAXSEC} + alrcj"])]),
                           Send("al-sections-write")])
    proc(c, "al-rcpload", [Loop(str(M.MAXSEC), "alrcj", [SendL("al-p2rc", [f"{pc}*{M.MAXSEC} + alrcj", "alrcj"])]),
                           Send("al-roadchg-write")])
