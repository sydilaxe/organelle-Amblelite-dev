"""Your own wavetables: the WAVs in the patch's waves/ folder, read at load into the bank's user slots (user1 ..
user8, in name order). A file whose length is a whole number of 2048-sample frames (2 or more: the Serum / Vital
export) becomes a table to scan through; any other file is a single cycle, resampled to one 2048-sample frame.
Each slot's table is laid out as the factory ones (wavetables.py): frames of CYCLE samples with guard points,
STRIDE apart, so the engines read them the same way. An empty slot plays the factory 'amble' table."""
from pdlib import Canvas, proc, V, T, Loop, If
from wavetables import TABLES, STRIDE, CYCLE

USER_SLOTS = 8
USER_NAMES = [f"user{i + 1}" for i in range(USER_SLOTS)]
MAX_LEN = 64 * CYCLE            # (the longest file read: 64 frames)
GLOBALS = dict(alwk=0, alwn=0, alwf=0, alwl=0, alwi=0, alwp=0, alwq=0)


def arr(k):
    """a user slot's array (no hyphen: it is named inside [expr])"""
    return f"alwtu{k + 1}"


def build(c):
    c.comment("your wavetables: waves/*.wav (in name order) into user1 .. user8 - frames of 2048, or a single cycle")
    c.obj(f"array define alwtmp {MAX_LEN}")
    c.obj(f"array define alwuf {USER_SLOTS}")
    for k in range(USER_SLOTS):
        c.obj(f"array define {arr(k)} {STRIDE}")
    glob = c.obj("file glob")
    # (the files are read at once, one after another, then the engines hear that they are there)
    go = c.ch(c.recv("al-init"), "delay 50", "t b b")
    # (the patch's own folder - [file glob] would look in Pd's working directory, which on the Organelle isn't it)
    pc = c.obj("pdcontrol")
    c.c(c.m((go, 1), "dir"), 0, pc, 0)
    c.c(c.ch(pc, "makefilename %s/waves/*.wav"), 0, glob, 0)
    c.c((go, 0), 0, c.obj("s al-wloaded"), 0)
    cnt = c.obj("f")
    c.c(c.m(c.recv("al-init"), "0"), 0, cnt, 1)
    # each file (a list 'path isdir'): read it into alwtmp, then convert it into the next slot
    one = c.ch((glob, 0), "list split 1", "t b a")
    rd = c.ch((one, 1), "list prepend read -resize -maxsize " + str(MAX_LEN), "list append alwtmp", "list trim")
    sf = c.obj("soundfiler")
    c.c(rd, 0, sf, 0)
    tn = c.to(sf, "t b f")                       # (the length kept, then the conversion)
    c.c((tn, 1), 0, c.obj("v alwn"), 0)
    c.c((tn, 0), 0, c.obj("s al-wconv"), 0)
    # (the file's slot, alwk, is set after its conversion - [t b a] fires right to left - ready for the next file)
    c.c((one, 0), 0, cnt, 0)
    nx = c.to(cnt, "+ 1")
    c.c(nx, 0, cnt, 1)
    c.c(nx, 0, c.obj("v alwk"), 0)
    c.c(c.m(c.recv("al-init"), "0"), 0, c.obj("v alwk"), 0)
    rt = c.ch(c.recv("al-wconv"), "t b", "expr alwk", "route " + " ".join(str(k) for k in range(USER_SLOTS)))
    for k in range(USER_SLOTS):
        c.c((rt, k), 0, c.obj(f"s al-wconv{k}"), 0)
        a = arr(k)
        sz = c.obj(f"array size {a}")
        c.c(c.recv(f"al-wsize{k}"), 0, sz, 0)
        # frames: whole 2048-sample frames (2 or more), else one single cycle of the file's length
        multi = f"(alwn % {CYCLE} == 0 && alwn >= {2 * CYCLE})"
        src = f"alwtmp[alwq*alwl + int(alwp) % alwl]*(1 - (alwp - int(alwp))) + " \
              f"alwtmp[alwq*alwl + (int(alwp) + 1) % alwl]*(alwp - int(alwp))"
        proc(c, f"al-wconv{k}", [If("alwn > 1", [
            V("alwf", f"if({multi}, alwn/{CYCLE}, 1)"), V("alwl", f"if({multi}, {CYCLE}, alwn)"),
            T("alwuf", str(k), "alwf"),
            # (the array sized: frames x STRIDE - through [array size]), then every sample of every frame
            _size(k),
            Loop(f"alwf*{STRIDE}", "alwi", [
                V("alwq", f"int(alwi/{STRIDE})"),
                V("alwp", f"((alwi % {STRIDE} - 1 + {CYCLE}) % {CYCLE})/{CYCLE}*alwl"),
                T(a, "alwi", src)])])])


def _size(k):
    """a step: the slot's array resized to alwuf[k] x STRIDE"""
    from pdlib import SendL
    return SendL(f"al-wsize{k}", [f"alwuf[{k}]*{STRIDE}"])


def table_select(s, slot):
    """a wave engine's Table knob: (the 'set <array>' messages - connect each to every reader - and an [f] holding
    the table's frame count). Factory tables first, then user1 .. user8 (an empty slot: the factory 'amble')"""
    nt, nu = len(TABLES), USER_SLOTS
    held = s.obj("f")
    s.c(s.ch(s.recv(f"al-s{slot}"), f"expr min({nt + nu - 1}, int($f1*{nt + nu}))"), 0, held, 0)
    s.c(s.ch(s.recv("al-wloaded"), "t b"), 0, held, 0)              # (the user tables have just loaded)
    names = s.obj("sel " + " ".join(str(i) for i in range(nt + nu)))
    s.c(held, 0, names, 0)
    readers, nfr = [], s.obj("f 1")
    for i, (tn, frames, _) in enumerate(TABLES):
        readers.append(s.m((names, i), f"set alwt-{tn}"))
        s.c(s.m((names, i), str(len(frames))), 0, nfr, 0)
    amble = len(TABLES[0][1])
    for k in range(nu):
        n = s.ch((names, nt + k), "t b", f"expr alwuf[{k}]", "moses 1")
        readers.append(s.m((n, 0), f"set alwt-{TABLES[0][0]}"))
        s.c(s.m((n, 0), str(amble)), 0, nfr, 0)
        readers.append(s.m((n, 1), f"set {arr(k)}"))
        s.c((n, 1), 0, nfr, 0)
    return readers, nfr
