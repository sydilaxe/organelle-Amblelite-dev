"""Write Pure Data patches from Python.

Canvas: objects, messages, comments, subpatches and connections, with automatic layout.
Steps (proc / X / Send / Call / If / Loop ...): a tiny imperative language that compiles to
[t b b ...] chains of [expr] boxes reading and writing global [value]s and arrays. All of the
composer's control logic is written with it, so every Pd box stays vanilla (Pd 0.53).
"""


def esc(text):
    out = text.replace("$", "\\$")
    out = out.replace(",", " \\,").replace(";", " \\;")
    return out


class Ix(int):
    """a box's index, which knows its canvas (connecting a box of another canvas stops the build)"""


class Canvas:
    def __init__(self, name=None, w=1400, h=900, font=10):
        self.name, self.w, self.h, self.font = name, w, h, font
        self.items, self.conns = [], []
        self.cx, self.cy = 20, 20

    # ---- layout: objects flow down a column; col() starts a new one
    def col(self, dx=230):
        self.cx += dx
        self.cy = 20

    def _place(self, x, y):
        if x is None:
            x, y = self.cx, self.cy
            self.cy += 24
            if self.cy > 3600:
                self.col()
        return x, y

    def obj(self, text, x=None, y=None):
        x, y = self._place(x, y)
        self.items.append(("obj", (x, y, text)))
        return self._ix()

    def msg(self, text, x=None, y=None):
        x, y = self._place(x, y)
        self.items.append(("msg", (x, y, text)))
        return self._ix()

    def comment(self, text, x=None, y=None):
        x, y = self._place(x, y)
        self.items.append(("text", (x, y, text)))
        return self._ix()

    def sub(self, canvas, x=None, y=None):
        x, y = self._place(x, y)
        self.items.append(("sub", (x, y, canvas)))
        return self._ix()

    def _ix(self):
        i = Ix(len(self.items) - 1)
        i.cv = self
        return i

    # ---- wiring
    def c(self, a, ao, b, bi=0):
        if isinstance(a, tuple):
            a, ao = a
        for i in (a, b):
            assert getattr(i, "cv", self) is self, f"a connection in [pd {self.name}] to a box of [pd {i.cv.name}]"
        self.conns.append((a, ao, b, bi))

    def to(self, src, text, ao=0, bi=0):
        n = self.obj(text)
        if src is not None:
            self.c(src, ao, n, bi)
        return n

    def m(self, src, text, ao=0):
        n = self.msg(text)
        if src is not None:
            self.c(src, ao, n, 0)
        return n

    def ch(self, src, *texts, ao=0):
        prev = src
        for i, t in enumerate(texts):
            n = self.obj(t)
            if prev is not None:
                self.c(prev, ao if i == 0 else 0, n, 0)
            prev = n
        return prev

    def recv(self, name):
        return self.obj("r " + name)

    # ---- output
    def render(self, top=True, rx=0, ry=0):
        lines = []
        if top:
            lines.append(f"#N canvas 50 50 {self.w} {self.h} {self.font};")
        else:
            lines.append(f"#N canvas 50 50 {self.w} {self.h} {self.name} 0;")
        for kind, p in self.items:
            if kind == "sub":
                x, y, cv = p
                lines.extend(cv.render(top=False, rx=x, ry=y))
            else:
                x, y, t = p
                tag = {"obj": "obj", "msg": "msg", "text": "text"}[kind]
                lines.append(f"#X {tag} {x} {y} {esc(t)};")
        for a, ao, b, bi in self.conns:
            lines.append(f"#X connect {a} {ao} {b} {bi};")
        if not top:
            lines.append(f"#X restore {rx} {ry} pd {self.name};")
        return lines

    def save(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.render()) + "\n")


# ======================================================================================
# Folding: [expr] -> [v name] and [expr v; i] -> [tabwrite t] become one [expr name = ...] / [expr t[i] = v].
# Pd's expr (0.53 too) evaluates and sends its expressions one at a time, right to left, so a store at
# expression i happens exactly when the outlet used to set the [v]: before expression i-1 is evaluated. A store
# finds the [value] by name when it runs, so each stored name needs one [v name] somewhere in the patch
# (fold_patch adds the missing ones). Fewer boxes and connections: the patch loads faster.
# ======================================================================================

import re as _re

_NAME = _re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_STORE = _re.compile(r"(?<![$\\\w])([A-Za-z_]\w*)\s*=(?!=)")     # a store into a value (not tab[i] =, ==, <=, !=)


def _fold_canvas(cv, stored, declared):
    items, conns = cv.items, cv.conns
    outs, ins = {}, {}
    for k, (a, ao, b, bi) in enumerate(conns):
        outs.setdefault((a, ao), []).append(k)
        ins.setdefault(b, []).append(k)
    srcs = {a for a, _, _, _ in conns}

    def text(i):
        kind, p = items[i]
        return p[2] if kind == "obj" else None

    def lone_sink(i, cls):
        """item i is [cls name] whose only connections come in (none go out): (name, incoming conns) or None"""
        t = text(i)
        if t is None or i in srcs:
            return None
        w = t.split()
        if len(w) != 2 or w[0] not in cls or not _NAME.match(w[1]):
            return None
        return w[1], ins.get(i, [])

    dead_items, dead_conns = set(), set()
    for e, (kind, p) in enumerate(items):
        if kind != "obj" or not p[2].startswith("expr "):
            continue
        exprs = [x.strip() for x in p[2][5:].split(";")]
        # [expr v; i] -> [tabwrite t]: both outlets into the table writer, nothing else
        if len(exprs) == 2 and len(outs.get((e, 0), [])) == 1 and len(outs.get((e, 1), [])) == 1:
            k0, k1 = outs[(e, 0)][0], outs[(e, 1)][0]
            tw = conns[k0][2]
            sink = lone_sink(tw, ("tabwrite",))
            if conns[k1][2] == tw and conns[k0][3] == 0 and conns[k1][3] == 1 and sink and len(sink[1]) == 2:
                items[e] = ("obj", (p[0], p[1], f"expr {sink[0]}[{exprs[1]}] = ({exprs[0]})"))
                dead_items.add(tw)
                dead_conns |= {k0, k1}
                continue
        changed = False
        for i, x in enumerate(exprs):
            ks = outs.get((e, i), [])
            if len(ks) != 1 or conns[ks[0]][3] != 0:
                continue
            sink = lone_sink(conns[ks[0]][2], ("v", "value"))
            if not sink or len(sink[1]) != 1:
                continue
            exprs[i] = f"{sink[0]} = ({x})"
            stored.add(sink[0])
            dead_items.add(conns[ks[0]][2])
            dead_conns.add(ks[0])
            changed = True
        if changed:
            items[e] = ("obj", (p[0], p[1], "expr " + "; ".join(exprs)))
    if dead_items:
        keep = [i for i in range(len(items)) if i not in dead_items]
        new = {old: n for n, old in enumerate(keep)}
        cv.items = [items[i] for i in keep]
        cv.conns = [(new[a], ao, new[b], bi) for k, (a, ao, b, bi) in enumerate(conns) if k not in dead_conns]
    for kind, p in cv.items:
        if kind == "sub":
            _fold_canvas(p[2], stored, declared)
        elif kind == "obj":
            w = p[2].split()
            if len(w) == 2 and w[0] in ("v", "value"):
                declared.add(w[1])
            elif w[0] == "expr":
                stored.update(_STORE.findall(p[2][5:]))


_PORTS = ("inlet", "inlet~", "outlet", "outlet~")


def _wrap_canvas(cv):
    """A subpatch that resamples (switch~ N 1 0.5) still runs its inlets' and outlets' resampling every block while
    switched off (Pd adds them outside the part switch~ skips). A canvas with .wrap = a receive name goes inside an
    outer subpatch at the parent's rate whose own [switch~] that name switches (off at load): off, Pd skips all of
    it. The outer ports sit at the inner ones' x, so their order (and every connection to them) is unchanged."""
    for idx, (kind, p) in enumerate(cv.items):
        if kind != "sub":
            continue
        inner = p[2]
        _wrap_canvas(inner)
        if not getattr(inner, "wrap", None):
            continue
        ports = [(it[1][2].split()[0], it[1][0], it[1][1]) for it in inner.items
                 if it[0] == "obj" and it[1][2].split()[0] in _PORTS]
        for side in ("inlet", "outlet"):
            xs = [x for k, x, _ in ports if k.startswith(side)]
            assert len(xs) == len(set(xs)), f"[pd {inner.name}]: two {side}s at one x (their order is unclear)"
        outer = Canvas(inner.name, w=inner.w, h=inner.h)
        outer.comment(f"switched off with {inner.wrap} 0: then none of [pd {inner.name}] runs, not even its resampling")
        sw = outer.obj("switch~")
        outer.c(outer.recv(inner.wrap), 0, sw, 0)
        outer.c(outer.m(outer.obj("loadbang"), "0"), 0, sw, 0)
        n = outer.sub(inner, 20, 300)
        for side in ("inlet", "outlet"):
            mine = sorted((x, k, y) for k, x, y in ports if k.startswith(side))
            for rank, (x, k, y) in enumerate(mine):
                b = outer.obj(k, x, 5 if side == "inlet" else 600)
                if side == "inlet":
                    outer.c(b, 0, n, rank)
                else:
                    outer.c(n, rank, b, 0)
        cv.items[idx] = ("sub", (p[0], p[1], outer))


def fold_patch(main, *abstractions):
    """fold the main canvas and the abstractions (in place); every stored name keeps a [v] declaration, in a
    [pd values] subpatch of the main canvas if nothing else declares it"""
    stored, declared = set(), set()
    for cv in (main,) + abstractions:
        _wrap_canvas(cv)
        _fold_canvas(cv, stored, declared)
    missing = sorted(stored - declared)
    if missing:
        d = Canvas("values")
        d.comment("[expr name = ...] stores need the [value]: these names have no other [v]")
        for n in missing:
            d.obj("v " + n)
        main.sub(d)
    return len(stored), len(missing)


# ======================================================================================
# Steps. A step is a function (canvas, src) -> None, where src is (object, outlet) giving a bang.
# ======================================================================================

def _sink(c, src, sink):
    """Connect src to a sink: 'v name' / 's name' / any object text / (obj, inlet) / callable."""
    if sink is None:
        return
    if callable(sink):
        sink(c, src)
    elif isinstance(sink, tuple):
        c.c(src[0], src[1], sink[0], sink[1])
    else:
        c.c(src[0], src[1], c.obj(sink), 0)


def run_steps(c, src, steps):
    steps = [s for s in steps if s is not None]
    if not steps:
        return
    steps = _merge(steps)
    if len(steps) == 1:
        steps[0](c, src)
        return
    if len(steps) > CHUNK and not getattr(c, "_chunk", False):
        steps = Chunks((c.name or "main") + "-steps", steps)
    t = c.obj("t " + " ".join(["b"] * len(steps)))
    c.c(*(src if isinstance(src, tuple) else (src, 0)), t, 0)
    for i, st in enumerate(steps):
        st(c, (t, len(steps) - 1 - i))


CHUNK = 12          # a longer list of steps runs in subpatches of this many (see Sub)
MERGE = 40          # at most this many stores in one [expr] (Pd's expr takes 100)


def _stores(seq):
    """one step: [expr] with the statements of seq, the first evaluated first (expr goes right to left)"""
    def st(c, src):
        c.c(*src, c.obj("expr " + "; ".join(reversed(seq))), 0)
    st.seq = seq
    return st


def _merge(steps):
    """Consecutive store steps (V, T, X into [v]s; their .seq) become one [expr] of stores, and stores just before an
    If go into the If's [expr], ahead of its condition. Pd's expr evaluates its expressions one after another,
    right to left, each seeing the stores before it: the same order the separate boxes ran in, in one box (an
    [expr] costs about 30 times another box to create, so the patch loads faster)."""
    out, run = [], []
    for st in steps:
        seq = getattr(st, "seq", None)
        if seq is not None:
            if run and len(run) + len(seq) > MERGE:
                out.append(_stores(run))
                run = []
            run = run + list(seq)
            continue
        if run and getattr(st, "cond", None) is not None and len(run) < MERGE:
            out.append(st.after(run))
        else:
            if run:
                out.append(_stores(run))
            out.append(st)
        run = []
    if run:
        out.append(_stores(run))
    return out


def _simple(name):
    return bool(_NAME.match(name))


def Sub(name, steps):
    """steps run inside a child subpatch [pd name] (its own connections: Pd checks each new connection against every
    one already in its window, so one huge window loads in quadratic time)"""
    def st(c, src):
        sc = Canvas(name, w=2600)
        sc._chunk = len(steps) <= CHUNK
        run_steps(sc, (sc.obj("inlet"), 0), steps)
        c.c(*(src if isinstance(src, tuple) else (src, 0)), c.sub(sc), 0)
    st.size = 1
    return st


BOX = 10            # an If's branch bigger than this (see _size) runs in its own window


def _size(steps):
    """about how many boxes a list of steps makes (an If counts its branches)"""
    return sum(getattr(st, "size", 2) for st in steps if st is not None)


def _boxed(name, steps):
    """a big If branch in its own window [pd name], created where its boxes would have been: same order"""
    steps = [s for s in steps if s is not None]
    if _size(steps) <= BOX:
        return steps
    return [Sub(name, steps)]


def Chunks(name, steps, size=None):
    """steps in order, in subpatches of `size` steps each (see Sub)"""
    size = size or CHUNK
    steps = [s for s in steps if s is not None]
    return [Sub(f"{name}-{k // size + 1}", steps[k:k + size]) for k in range(0, len(steps), size)]


def window(c, name, src=None, w=2400):
    """a child window [pd name] of c, for a block that connects only to itself (Pd's connect is quadratic per
    window): returns (the child canvas, its [inlet] or None). src (obj, outlet) feeds the inlet."""
    sc = Canvas(name, w=w)
    n = c.sub(sc)
    if src is None:
        return sc, None
    c.c(*(src if isinstance(src, tuple) else (src, 0)), n, 0)
    return sc, sc.obj("inlet")


PROCS = set()


def proc(c, recv, steps, shared=False):
    """[r recv] -> steps in order. Returns the receive object. A name is one proc: two procs on one name both run
    whenever either is called, in no set order, so the build stops - unless both say shared=True (two independent
    listeners to one event, like ac-step's player and its screen mark)."""
    assert recv not in PROCS or shared, f"proc {recv} is defined twice (shared=True on both, if meant)"
    PROCS.add(recv)
    sc = Canvas(recv, w=2600)           # each proc in its own window (Pd's connect is quadratic per window)
    r = sc.recv(recv)
    run_steps(sc, (r, 0), steps)
    c.sub(sc)
    return r


def X(expr, *sinks):
    """Evaluate [expr e0; e1; ...] and send outlet i to sinks[i] (outlets fire right to left)."""
    def st(c, src):
        e = c.obj("expr " + expr)
        c.c(*src, e, 0)
        for i, s in enumerate(sinks):
            _sink(c, (e, i), s)
    # (only stores into [v]s, no $ arguments: it can join its neighbours' [expr], see _merge)
    exprs = [x.strip() for x in expr.split(";")]
    seq = []
    for i, x in enumerate(exprs):
        s = sinks[i] if i < len(sinks) else None
        if s is None:
            seq.append(x)
        elif isinstance(s, str) and s.startswith("v ") and _simple(s[2:].strip()):
            seq.append(f"{s[2:].strip()} = ({x})")
        else:
            seq = None
            break
    if seq is not None and "$" not in expr and len(sinks) <= len(exprs):
        st.seq = seq[::-1]
    return st


def V(name, expr):
    return X(expr, "v " + name)


def T(table, idx, val):
    """table[idx] = val"""
    def st(c, src):
        e = c.obj(f"expr {val}; {idx}")
        c.c(*src, e, 0)
        tw = c.obj("tabwrite " + table)
        c.c(e, 1, tw, 1)
        c.c(e, 0, tw, 0)
    if _simple(table) and "$" not in f"{idx} {val}":
        st.seq = [f"{table}[{idx}] = ({val})"]
    return st


def ACopy(src, src_on, n, dst, dst_on=0):
    """dst[dst_on + i] = src[src_on + i] for i < n, in one go: [array get] -> [array set] (the same floats as a Loop
    of T, without its per-element [until] / [expr] work, so a big copy doesn't take a long scheduler tick)"""
    def st(c, src_):
        g = c.obj(f"array get {src} {src_on} {n}")
        c.c(*src_, g, 0)
        c.c(g, 0, c.obj(f"array set {dst} {dst_on}"), 0)
    st.size = 2
    return st


def AZero(arr, on, n):
    """arr[on + i] = 0 for i < n, in one go (a message of n zeros into [array set])"""
    def st(c, src_):
        m = c.msg(" ".join(["0"] * n))
        c.c(*src_, m, 0)
        c.c(m, 0, c.obj(f"array set {arr} {on}"), 0)
    st.size = 2
    return st


def Send(name, text=None):
    """bang [s name], or send a fixed message."""
    def st(c, src):
        if text is None:
            s = c.obj("s " + name)
            c.c(*src, s, 0)
        else:
            m = c.msg(text)
            c.c(*src, m, 0)
            c.c(m, 0, c.obj("s " + name), 0)
    return st


Call = Send


def SendL(name, exprs, fmt=None):
    """Evaluate several exprs and send them as one list (optionally through a message format)."""
    def st(c, src):
        e = c.obj("expr " + "; ".join(exprs))
        c.c(*src, e, 0)
        if len(exprs) == 1:
            out = e
        else:
            out = c.obj("pack " + " ".join(["f"] * len(exprs)))
            for i in range(len(exprs)):
                c.c(e, i, out, i)
        if fmt:
            m = c.msg(fmt)
            c.c(out, 0, m, 0)
            out = m
        c.c(out, 0, c.obj("s " + name), 0)
    return st


def If(cond, steps, else_steps=None, pre=()):
    """steps if cond, else else_steps. pre: stores evaluated first, in the same [expr] (see _merge)"""
    def st(c, src):
        e = c.obj("expr " + "; ".join([cond] + list(reversed(pre))))
        c.c(*src, e, 0)
        s = c.obj("sel 0")
        c.c(e, 0, s, 0)
        if steps:
            b = c.obj("b")
            c.c(s, 1, b, 0)
            run_steps(c, (b, 0), _boxed("then", steps))
        if else_steps:
            run_steps(c, (s, 0), _boxed("else", else_steps))
    st.cond, st.then, st.els = cond, steps, else_steps
    st.size = 3 + _size(steps or []) + _size(else_steps or [])
    st.after = lambda seq: If(cond, steps, else_steps, list(seq) + list(pre))
    return st


def Loop(count, var, steps):
    """for var in 0..count-1: steps"""
    def st(c, src):
        e = c.obj("expr " + count)
        c.c(*src, e, 0)
        tf = c.obj("t f b")
        c.c(e, 0, tf, 0)
        f = c.obj("f")
        z = c.msg("0")
        c.c(tf, 1, z, 0)
        c.c(z, 0, f, 1)
        u = c.obj("until")
        c.c(tf, 0, u, 0)
        c.c(u, 0, f, 0)
        p = c.obj("+ 1")
        c.c(f, 0, p, 0)
        c.c(p, 0, f, 1)
        tb = c.obj("t b f")
        c.c(f, 0, tb, 0)
        c.c(tb, 1, c.obj("v " + var), 0)
        run_steps(c, (tb, 0), steps)
    return st


def lookup(c, src, names, dest, prefix="symbol "):
    """float index at src -> [sel 0 1 ..] -> 'symbol name' messages into dest (obj, inlet)."""
    bad = [n for n in names if any(ch in str(n) for ch in ",;$")]
    assert not bad, f"names {bad}: a comma or semicolon ends a Pd message (the screen showed only the first word)"
    s = c.obj("sel " + " ".join(str(i) for i in range(len(names))))
    c.c(*(src if isinstance(src, tuple) else (src, 0)), s, 0)
    for i, n in enumerate(names):
        m = c.msg(prefix + n.replace(" ", "\\ "))       # an escaped space keeps 'stereo wide' one symbol
        c.c(s, i, m, 0)
        c.c(m, 0, dest[0], dest[1])
    return s


def Line(recv, fmt, parts, dest):
    """Screen/text line: on [r recv] evaluate parts and send fmt (a message using $1..$n) to dest.
    parts: ('f', expr) or ('s', expr, [names])."""
    def build(c0):
        c = Canvas(recv)                # (in its own window, as a proc)
        c0.sub(c)
        r = c.recv(recv)
        n = len(parts)
        pk = c.obj("pack " + " ".join("s" if p[0] == "s" else "f" for p in parts))
        t = c.obj("t " + " ".join(["b"] * n))
        c.c(r, 0, t, 0)
        for i, p in enumerate(parts):
            e = c.obj("expr " + p[1])
            c.c(t, i, e, 0)
            if p[0] == "f":
                c.c(e, 0, pk, i)
            else:
                lookup(c, (e, 0), p[2], (pk, i))
        m = c.msg(fmt)
        c.c(pk, 0, m, 0)
        c.c(m, 0, c.obj("s " + dest), 0)
    return build


def Arm(tick, expr, stop=None):
    """(re)start a [delay] of expr ms that then bangs [s tick]; [s stop] cancels it."""
    def st(c, src):
        e = c.obj("expr " + expr)
        c.c(*src, e, 0)
        d = c.obj("delay")
        c.c(e, 0, d, 0)
        c.c(d, 0, c.obj("s " + tick), 0)
        if stop:
            c.c(c.m(c.recv(stop), "stop"), 0, d, 0)
    return st


def Later(recv, ms, stop=None):
    """[s recv] after ms (a [delay]; a repeat before it fires restarts it; [s stop] cancels it). Spreads a
    heavy update over several scheduler ticks so no single tick runs long enough to make the audio drop out."""
    def st(c, src):
        d = c.obj(f"delay {ms}")
        c.c(*src, d, 0)
        c.c(d, 0, c.obj("s " + recv), 0)
        if stop:
            c.c(c.m(c.recv(stop), "stop"), 0, d, 0)
    return st


def Toast(text):
    return Send("ac-toast", "list " + text)


RNG = Call("ac-rng")
