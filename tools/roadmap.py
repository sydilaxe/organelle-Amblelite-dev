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
from pdlib import Canvas, proc, V, T, Send, Call, SendL, If, Loop
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
               alrq=0, alrbar=0)


def build(c):
    for fn in (tables, generate, run, edit, store):
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
        SendL("al-set", [str(st), f"(alrsS[alrc] + 0.5)/{len(M.STORIES)}"])])])
    # each bar: the section ends? on to the next (unless held); guide: a toast a bar before
    proc(c, "al-rbar", [If(f"{opt(road)} > 0 && alrn > 0", [
        V("alrbar", "altick/32"),
        If(f"{opt(road)} == 1 && alrbar - alrb0 == alrsL[alrc] - 1 && alrc + 1 < alrn", toast("NEXT", "alrc + 2")),
        If("alrhold == 0 && alrbar - alrb0 >= alrsL[alrc]", [Call("al-rnext")])])])
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
    c.c(c.to((ld, 0), "t b"), 0, c.obj("s al-rsectload"), 0)
    # write: every section, then the file (a little after an edit, so a turning knob writes once)
    c.c(c.ch(c.recv("al-rsavelater"), "delay 400"), 0, c.obj("s al-rsave"), 0)
    proc(c, "al-rsave", [Send("al-roadclear"), Loop("alrn", "alri", [SendL(
        "al-roadline", ["alri", "alrsL[alri]", "alrsS[alri]", "alrsM[alri]", "alrsR[alri]"])]), Send("al-roadwrite")])
    c.c(c.m(c.recv("al-roadclear"), "clear"), 0, tx, 0)
    c.c(c.m(c.recv("al-roadwrite"), "write roadmap.txt"), 0, tx, 0)
    # (one line at a time, appended: [text insert] at the end)
    li = c.ch(c.recv("al-roadline"), "list split 1")
    ins = c.obj("text insert al-road 1e+06")
    c.c((li, 1), 0, ins, 0)
