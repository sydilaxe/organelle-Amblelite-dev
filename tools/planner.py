"""The web editor: docs/planner.html, a page to load, edit and save Amble Lite's pieces (pieces.txt) and snapshots
(saves.txt) on a computer, page by page as on the Organelle - every parameter of every layer and engine, the layers in,
the latches, the FAV pages, the tapped rhythms and (a piece's) roadmap. Built from the same tables as the patch
(model.py, features.py, roadmap.py), so the files it writes are the ones the patch reads: one line a slot, the numbers
the patch keeps (each parameter 0..1), '-1' for an empty slot.  python3 planner.py [out.html]

CORE (the files and values, no page) is kept apart so check.py can run it in node against files Pd wrote."""
import json
import os
import sys
import model as M
import roadmap as R
import korg
import midi

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs",
                                                         "planner.html")

ROLE_NAMES = ["emerge", "establish", "develop", "intensify", "climax", "break", "return", "dissolve"]
ARC_NAMES = ["arch", "build", "waves", "twin", "journey"]


def engfix():
    """the engine change, for an older line (features.engine_fix, the same in the page)"""
    ks, _, _ = M.knob_table()
    li, nl = M.LAYERS.index("sub"), len(M.LAYERS)
    st = dict(M.engines("pad"))["string"]
    fav = [[M.NSLOTS + 2 * nl + (li * M.MAXENG + ei) * 4 + k, ks[((li * M.MAXENG + ei) * M.MAXPAGES) * 4 + k]]
           for ei in range(M.OLD_ENGINES["sub"], len(M.engines("sub"))) for k in range(4)]
    vo = lambda k: M.S("pad", "voice", k)
    lc = M.LAYERS.index("cloud")
    cfav = [[M.NSLOTS + 2 * nl + (lc * M.MAXENG + ei) * 4 + k, ks[((lc * M.MAXENG + ei) * M.MAXPAGES) * 4 + k]]
            for ei in range(M.CLOUD_OLD_ENGINES, len(M.engines("cloud"))) for k in range(4)]
    return dict(cloudEng=M.S("cloud", None, "Engine"), nCloud=len(M.engines("cloud")), cloudFav=cfav, cloudUpto=M.CLOUD_FIX_UPTO,
                subEng=M.S("sub", None, "Engine"), oldSub=M.OLD_ENGINES["sub"], nSub=len(M.engines("sub")),
                padEng=M.S("pad", None, "Engine"), nPad=len(M.engines("pad")), choir=M.CHOIR_INDEX,
                voice=M.VOICE_INDEX, src=vo("Source"), vowel=vo("Vowel"), motion=vo("Motion"), breath=vo("Breath"),
                string=[M.S("pad", "string", p.key) for p in st], stringDef=[p.default for p in st], fav=fav)


def data():
    import features as F
    from control import IN_AT_START, FIRST_LANE, MODE_SLOT, SCALE_SLOT
    ks, _, _ = M.knob_table()
    nl = len(M.LAYERS)
    slots = []
    for key, p in M.SLOTS:
        t = "tgt" if p.target else "opt" if p.opts else "num" if p.lo is not None else "pct"
        slots.append(dict(n=p.name, t=t, o=p.opts or None, lo=p.lo, hi=p.hi, d=round(p.default, 6), L=key[0], e=key[1]))
    layers = []
    for li, L in enumerate(M.LAYERS):
        engs = [e for e, _ in M.engines(L)]
        layers.append(dict(id=L, label=M.LAYER_LABEL[L], short=M.SHORT[L], engines=engs, eng=M.S(L, None, "Engine"),
                           latch=li < FIRST_LANE, pages={e: [[n, s] for n, s in M.pages(L, e)] for e in engs},
                           targets={e: M.targets(L, e) for e in engs}))
    fav0 = [ks[((li * M.MAXENG + ei) * M.MAXPAGES) * 4 + k] for li in range(nl) for ei in range(M.MAXENG)
            for k in range(4)]
    import roadmap as RM
    gpages = [[n, [M.global_slot(p) for p in ps], [M.global_label(p) for p in ps]] for n, ps in M.GLOBAL_PAGES]
    gpages += [[n, [M.S(L, None, k) for L, k in refs], [M.LAYERS.index(L) if L != "g" else -1 for L, _ in refs]]
               for n, refs in M.MIX_PAGES]
    rhythm = []
    for L in M.NOTE_LAYERS:
        lane = L in M.LANES
        ps = M.S(L, None, "Patt") if lane else M.S(L, None, "Gate")
        rhythm.append(dict(layer=M.LAYERS.index(L), steps=M.S(L, None, "Steps"), patt=ps, tapped=1 if lane else 2))
    names = [n for n, _, _ in M.STORIES]
    nslots = M.NSLOTS
    lay = dict(nslots=nslots, history=M.SLOT_HISTORY, nl=nl, maxeng=M.MAXENG, latch=nslots, inn=nslots + nl, fav=nslots + 2 * nl,
               favn=F.FAVN, tap=nslots + 2 * nl + F.FAVN, tapn=F.TAPN, snap=F.SNAP, piece=F.PIECE, maxsec=M.MAXSEC,
               pieces=F.PIECES, saves=F.SAVE_SLOTS, saveLines=F.SCRATCH + 2, loopLayers=F.LOOP_LAYERS, freeMs=M.FREE_MS,
               maxev=F.MAXEV, maxclk=F.MAXCLK, bar=F.BAR)
    assert lay["tap"] + lay["tapn"] == F.SNAP and F.SNAP + 1 + 4 * M.MAXSEC == F.PIECE
    return dict(
        capt=RM.capturable(), maxch=RM.MAXCH, engfix=engfix(),
        slots=slots, layers=layers, fav0=fav0, latch0=[1 if li < FIRST_LANE else 0 for li in range(nl)],
        in0=[1 if L in IN_AT_START else 0 for L in M.LAYERS], gpages=gpages, rhythm=rhythm, layout=lay,
        modeSlot=MODE_SLOT, scaleSlot=SCALE_SLOT, scaleModes=[[n for n, _ in ms] for _, ms in M.SCALES],
        key=M.S("g", None, "Key"), tempo=M.S("g", None, "Tempo"),
        roles=ROLE_NAMES, arcs=ARC_NAMES, arcRoles=[M.ARC_ROLES[a] for a in M.ARCS], weights=R.WEIGHTS,
        tension=R.TENSION, masks=R.MASKS, pools=[[names.index(n) for n in p] for p in R.POOLS], stories=names,
        llabels=[M.LAYER_LABEL[L] for L in M.LAYERS], short=[M.SHORT[L] for L in M.LAYERS],
        midi=dict(devices=korg.tables(), keys=[midi.slot_key(i) for i in range(M.NSLOTS)],
                  noteLayers=len(M.NOTE_LAYERS)))


# ---- the files and values (no page): parse / write the patch's text files, read and set parameters as the patch
# shows them. Runs in the page and, for the checks, in node.
CORE = r"""
const C = (() => {
  const Y = D.layout;
  const q = v => Math.abs(v) < 5e-7 ? "0" : String(+(+v).toPrecision(6));
  const lix = {}; D.layers.forEach((l, i) => lix[l.id] = i);
  function defaults(kind) {
    const r = new Array(kind === "piece" ? Y.piece : Y.snap).fill(0);
    D.slots.forEach((s, i) => r[i] = s.d);
    D.latch0.forEach((v, i) => r[Y.latch + i] = v);
    D.in0.forEach((v, i) => r[Y.inn + i] = v);
    D.fav0.forEach((v, i) => r[Y.fav + i] = v);
    return r;
  }
  // a file's lines as Pd reads it ('read -c'): a ';' or a newline ends a line, so slot k is line k - an empty
  // line is an empty slot (an older file, ';' then a newline at each line's end, reads as a line and an empty one)
  function lines(text) {
    const t = text.replace(/\r/g, "").split(/[;\n]/);
    if (t.length && t[t.length - 1].trim() === "") t.pop();
    return t.map(l => l.trim());
  }
  // a file: a record a line; '-1' (or an empty line) an empty slot. A line from before the SHAPE page (its slots
  // came after the others: the line that much shorter) gets their defaults where they sit now
  // (Y.history: the slot counts before each addition - the added slots always come after the others)
  function widen(a, len) {
    for (const [i, h] of Y.history.entries())
      if (a.length === len - (Y.nslots - h))
        return fixEngines([...a.slice(0, h), ...D.slots.slice(h).map(s => s.d), ...a.slice(h)], i);
    return a;
  }
  // an older line, after the engine change: the sub's Engine was 1 of 4 (now more, the first four the same); a pad
  // on choir becomes voice from glottal pulses with choir's vowel, drift and breath (its slots are string's now:
  // back to their defaults); the sub's FAV pages for its new engines take their defaults (features.engine_fix)
  function fixEngines(r, i) {
    const E = D.engfix;
    // (the layouts before the cloud's engines: its engine grains - one of one then - its new engines' FAV pages their
    // defaults; later layouts only take their new slots' defaults)
    if (i >= E.cloudUpto) return r;
    r[E.cloudEng] = 0.5 / E.nCloud; E.cloudFav.forEach(([pos, v]) => { r[pos] = v; });
    if (i > 2) return r;            // (the sub and choir: only those from before the engine change)
    r[E.subEng] = (Math.min(E.oldSub - 1, Math.floor(r[E.subEng] * E.oldSub)) + 0.5) / E.nSub;
    if (Math.min(E.nPad - 1, Math.floor(r[E.padEng] * E.nPad)) === E.choir) {
      r[E.padEng] = (E.voice + 0.5) / E.nPad; r[E.src] = 1;
      r[E.vowel] = r[E.string[0]]; r[E.motion] = r[E.string[1]]; r[E.breath] = r[E.string[3]];
      E.string.forEach((s, i) => { r[s] = E.stringDef[i]; });
    }
    E.fav.forEach(([pos, v]) => { r[pos] = v; });
    return r;
  }
  const olderLen = len => Y.history.map(h => len - (Y.nslots - h));
  function parse(text, len) {
    return lines(text).map(l => {
      const a = widen(l ? l.split(/\s+/).map(Number) : [], len);
      return a.length === len && a.every(Number.isFinite) ? a : null;
    });
  }
  let kindOf = function (text) {
    const lens = lines(text).filter(Boolean).map(l => l.split(/\s+/).length);
    if ([Y.piece, ...olderLen(Y.piece)].some(n => lens.includes(n))) return "piece";
    if ([Y.snap, ...olderLen(Y.snap)].some(n => lens.includes(n))) return "snap";
    return null;
  };
  function write(recs) { return recs.map(r => r ? r.map(q).join(" ") : "-1").join("\n") + "\n"; }
  function asPiece(r) {
    const p = defaults("piece");
    r.forEach((v, i) => { if (i < Y.piece) p[i] = v; });
    return p;
  }
  const asSnap = r => r.slice(0, Y.snap);
  // values, as the patch reads them
  const layerOf = s => D.slots[s].L === "g" ? -1 : lix[D.slots[s].L];
  function count(s, rec) {
    if (s === D.modeSlot) return D.scaleModes[optIndex(D.scaleSlot, rec)].length;
    return D.slots[s].o.length;
  }
  function optIndex(s, rec) { const n = count(s, rec); return Math.min(n - 1, Math.floor(rec[s] * n)); }
  const engine = (rec, li) => D.layers[li].engines[optIndex(D.layers[li].eng, rec)];
  const targets = (rec, li) => D.layers[li].targets[engine(rec, li)];
  function targetIndex(s, rec) { const t = targets(rec, layerOf(s)); return Math.min(t.length, Math.floor(rec[s] * (t.length + 1))); }
  function choices(s, rec) {
    const sl = D.slots[s];
    if (s === D.modeSlot) return D.scaleModes[optIndex(D.scaleSlot, rec)];
    if (sl.t === "opt") return sl.o;
    if (sl.t === "tgt") return ["off", ...targets(rec, layerOf(s)).map(name)];
    return null;
  }
  function name(s) { const sl = D.slots[s]; return sl.e ? `${sl.n} (${sl.e})` : sl.n; }
  function index(s, rec) { return D.slots[s].t === "tgt" ? targetIndex(s, rec) : optIndex(s, rec); }
  function number(s, rec) {
    const sl = D.slots[s];
    return sl.t === "num" ? Math.trunc(sl.lo + rec[s] * (sl.hi - sl.lo) + 0.5) : Math.trunc(rec[s] * 100 + 0.5);
  }
  function text(s, rec) { const c = choices(s, rec); return c ? c[index(s, rec)] : String(number(s, rec)); }
  function setIndex(s, rec, i) {
    const n = D.slots[s].t === "tgt" ? targets(rec, layerOf(s)).length + 1 : count(s, rec);
    rec[s] = +((i + 0.5) / n).toFixed(6);
  }
  function setNumber(s, rec, x) {
    const sl = D.slots[s];
    rec[s] = sl.t === "num" ? +((x - sl.lo) / (sl.hi - sl.lo)).toFixed(6) : +(x / 100).toFixed(6);
  }
  // the FAV page of a layer with an engine: 4 slots (-1: none)
  const favAt = (li, ei, k) => Y.fav + (li * Y.maxeng + ei) * 4 + k;
  // a piece's roadmap: its sections
  function road(rec) {
    const n = Math.max(0, Math.min(Y.maxsec, Math.trunc(rec[Y.snap] || 0))), b = Y.snap + 1, out = [];
    for (let i = 0; i < n; i++)
      out.push({ bars: rec[b + i], story: rec[b + Y.maxsec + i], mask: rec[b + 2 * Y.maxsec + i], role: rec[b + 3 * Y.maxsec + i] });
    return out;
  }
  function setRoad(rec, secs) {
    const b = Y.snap + 1;
    rec[Y.snap] = secs.length;
    for (let i = 0; i < Y.maxsec; i++) {
      const s = secs[i] || { bars: 0, story: 0, mask: 0, role: 0 };
      rec[b + i] = s.bars; rec[b + Y.maxsec + i] = s.story; rec[b + 2 * Y.maxsec + i] = s.mask; rec[b + 3 * Y.maxsec + i] = s.role;
    }
  }
  // loops.txt: a line a piece and layer: state length count, times, notes, velocities, roots (count each), the
  // breath line's length and values
  const okLoop = a => a.length >= 4 && a.every(Number.isFinite) && a[2] >= 0 && a.length === 4 + 4 * a[2] + (a[3 + 4 * a[2]] || 0);
  function parseLoops(text) {
    const ls = lines(text).map(l => l ? l.split(/\s+/).map(Number) : []);
    return Array.from({ length: Y.pieces * Y.loopLayers }, (_, i) => ls[i] && okLoop(ls[i]) ? ls[i] : [0, 0, 0, 0]);
  }
  function isLoops(text) {
    const ls = lines(text).filter(Boolean).map(l => l.split(/\s+/).map(Number));
    return ls.length > 0 && ls.every(okLoop);
  }
  function loop(a) {
    const n = a[2], bn = a[3 + 4 * n] || 0, at = k => a.slice(3 + k * n, 3 + (k + 1) * n);
    // (a free loop: its state + 10 - its times in ticks of its own clock, Y.freeMs each)
    return { state: a[0] % 10, free: a[0] >= 10, len: a[1], n, t: at(0), note: at(1), vel: at(2), root: at(3), bn, breath: a.slice(4 + 4 * n, 4 + 4 * n + bn) };
  }
  // sections.txt: each piece's sections' parameter changes, a line a piece and section: 'n slot value ...'
  const okSec = a => a.length >= 1 && a.every(Number.isFinite) && a.length === 1 + 2 * a[0];
  function parseSecs(text) {
    const ls = lines(text).map(l => l ? l.split(/\s+/).map(Number) : [0]);
    return Array.from({ length: Y.pieces * Y.maxsec }, (_, i) => {
      const a = ls[i] && okSec(ls[i]) ? ls[i] : [0], out = [];
      for (let k = 0; k < a[0]; k++) if (a[1 + 2 * k] >= 0 && a[1 + 2 * k] < Y.nslots) out.push([a[1 + 2 * k], a[2 + 2 * k]]);
      return out;
    });
  }
  const writeSecs = secs => secs.map(c => [c.length, ...c.flat()].map(q).join(" ")).join("\n") + "\n";
  function isSecs(text) {
    const ls = lines(text).filter(Boolean).map(l => l.split(/\s+/).map(Number));
    return ls.length === Y.pieces * Y.maxsec && ls.every(okSec);
  }
  const _kind = kindOf;
  kindOf = text => _kind(text) || (isLoops(text) ? "loops" : isSecs(text) ? "secs" : null);
  return { Y, defaults, parse, widen, kindOf, write, parseLoops, parseSecs, writeSecs, loop, asPiece, asSnap, layerOf, engine, targets, choices, name, index, number,
           text, setIndex, setNumber, favAt, road, setRoad, optIndex };
})();
"""

PAGE = r"""<title>Amble Lite Editor</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: a hardware-panel tool - the library of slots as a strip of numbered keys, then the open piece or snapshot as
   the Organelle's own pages (four knobs each) under layer tabs, the files at the foot. Colours: an OLED-ink dark /
   paper light pair, one cool accent, a muted hue per roadmap role. */
:root {
  --bg: #f3f4f1; --panel: #ffffff; --ink: #1b1f1d; --muted: #5d6762; --line: #d5dad6; --accent: #1f6f78;
  --accent-ink: #ffffff; --chip: #e6ebe8; --warn: #9a5a12;
  --r0: #9db6c3; --r1: #8fb39a; --r2: #b8c68a; --r3: #d8b46a; --r4: #d98a6a; --r5: #a9a1c7; --r6: #8fb3b0; --r7: #b3a99c;
  --display: "Space Grotesk", "Helvetica Neue", Arial, sans-serif;
  --body: "Inter", "Helvetica Neue", Arial, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f1312; --panel: #171c1b; --ink: #e4ebe7; --muted: #93a19a; --line: #2a3331; --accent: #5cc3cc;
  --accent-ink: #0f1312; --chip: #222a28; --warn: #e0a458;
  --r0: #4d6a78; --r1: #4b6e55; --r2: #6c7a3e; --r3: #8b6b2c; --r4: #8f4f37; --r5: #5f5883; --r6: #456e6a; --r7: #6b6257;
  color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #0f1312; --panel: #171c1b; --ink: #e4ebe7; --muted: #93a19a; --line: #2a3331; --accent: #5cc3cc;
  --accent-ink: #0f1312; --chip: #222a28; --warn: #e0a458;
  --r0: #4d6a78; --r1: #4b6e55; --r2: #6c7a3e; --r3: #8b6b2c; --r4: #8f4f37; --r5: #5f5883; --r6: #456e6a; --r7: #6b6257;
  color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: var(--body); line-height: 1.5; }
.wrap { max-width: 1120px; margin: 0 auto; padding-block: 28px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 22px; }
h1 { font-family: var(--display); font-weight: 600; font-size: 1.7rem; margin: 0; text-wrap: balance; }
h2 { font-family: var(--display); font-weight: 600; font-size: 1.05rem; margin: 0; text-wrap: balance; }
h3 { font-family: var(--display); font-weight: 600; font-size: .85rem; letter-spacing: .06em; margin: 0; }
.lede { color: var(--muted); margin: 4px 0 0; max-width: 68ch; }
.label { font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
section.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 18px; display: grid; gap: 14px; min-width: 0; }
section.panel[hidden] { display: none; }
.field { display: grid; gap: 6px; min-width: 0; }
input[type=number], select, textarea { font: inherit; color: var(--ink); background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; min-width: 0; }
input[type=range] { width: 100%; accent-color: var(--accent); }
button { font: 500 .9rem var(--body); border-radius: 6px; padding: 8px 14px; border: 1px solid var(--line); background: var(--chip); color: var(--ink); cursor: pointer; }
button.primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
button:disabled { opacity: .5; cursor: default; }
button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible, .seg:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.between { justify-content: space-between; }
.summary { font-family: var(--mono); font-size: .85rem; color: var(--muted); }
.note { color: var(--muted); font-size: .85rem; max-width: 72ch; margin: 0; }
.og:not([hidden]) { display: grid; gap: 8px; margin-top: 10px; }
.status { font-size: .85rem; color: var(--accent); min-height: 1.2em; }
.warn { color: var(--warn); }
/* library: numbered slot keys */
.lib { display: grid; gap: 12px; }
.keys { display: flex; flex-wrap: wrap; gap: 6px; }
.key { font: 500 .85rem var(--mono); width: 40px; height: 40px; padding: 0; border-radius: 6px; background: transparent; color: var(--muted); border: 1px dashed var(--line); font-variant-numeric: tabular-nums; }
.key.full { background: var(--chip); color: var(--ink); border-style: solid; }
.key.cur { border: 2px solid var(--accent); color: var(--ink); }
/* editor */
.tabs { display: flex; flex-wrap: wrap; gap: 4px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }
.tab { font: 600 .75rem var(--display); letter-spacing: .06em; padding: 7px 10px; background: transparent; border-color: transparent; color: var(--muted); }
.tab[aria-selected="true"] { background: var(--chip); color: var(--ink); border-color: var(--line); }
.tab.out { text-decoration: line-through; text-decoration-color: var(--muted); }
.pages { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.page { border: 1px solid var(--line); border-radius: 8px; padding: 12px; display: grid; gap: 10px; align-content: start; min-width: 0; }
.page h3 { display: flex; justify-content: space-between; gap: 8px; }
.page h3 span { font: .7rem var(--mono); color: var(--muted); letter-spacing: 0; }
.knob { display: grid; grid-template-columns: 64px 1fr 44px; gap: 8px; align-items: center; min-width: 0; }
.knob .nm { font-size: .8rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.knob .val { font: .8rem var(--mono); text-align: right; font-variant-numeric: tabular-nums; }
.knob select { grid-column: 2 / 4; font-size: .85rem; padding: 4px 6px; }
.knob.empty .nm { opacity: .4; }
.layerbar { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; }
.toggle { display: inline-flex; gap: 8px; align-items: center; font-size: .9rem; }
.toggle input { accent-color: var(--accent); width: 18px; height: 18px; }
/* rhythms */
.rh { display: grid; gap: 8px; }
.rhrow { display: grid; grid-template-columns: 70px 1fr; gap: 10px; align-items: center; }
.steps { display: grid; grid-template-columns: repeat(16, minmax(0, 1fr)); gap: 3px; max-width: 560px; }
.step { height: 28px; padding: 0; border-radius: 4px; background: transparent; }
.step.on { background: var(--accent); border-color: var(--accent); }
.step.off { opacity: .35; }
.step:nth-child(4n+1) { border-color: var(--muted); }
/* roadmap */
.setup { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 14px 18px; align-items: end; }
.timeline { display: flex; gap: 3px; height: 56px; }
.seg { border-radius: 4px; display: flex; flex-direction: column; justify-content: space-between; padding: 6px; min-width: 0; overflow: hidden; color: var(--ink); border: 2px solid transparent; cursor: pointer; }
.seg.sel { border-color: var(--accent); }
.seg b { font: 600 .75rem var(--display); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.seg span { font: .7rem var(--mono); white-space: nowrap; }
.tablewrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; min-width: 760px; font-size: .9rem; }
th { text-align: left; font-weight: 500; color: var(--muted); font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; padding: 6px 8px; border-bottom: 1px solid var(--line); }
td { padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: middle; }
tr.sel td { background: color-mix(in srgb, var(--accent) 10%, transparent); }
td.num { font-family: var(--mono); font-variant-numeric: tabular-nums; }
td input[type=number] { width: 72px; }
.chips { display: flex; gap: 4px; flex-wrap: nowrap; }
.chip { font: 500 .75rem var(--mono); width: 28px; height: 26px; border-radius: 5px; border: 1px solid var(--line); background: transparent; color: var(--muted); padding: 0; }
.chip.on { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
/* files */
.files { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
textarea { width: 100%; box-sizing: border-box; font-family: var(--mono); font-size: .75rem; min-height: 90px; }
textarea.out { height: 120px; white-space: pre; overflow: auto; }
details summary { cursor: pointer; color: var(--muted); font-size: .9rem; }
@media (prefers-reduced-motion: no-preference) { .seg { transition: flex-grow .2s ease; } }
@media (max-width: 480px) { .knob { grid-template-columns: 56px 1fr 40px; } .rhrow { grid-template-columns: 1fr; } }
</style>

<div class="wrap">
  <header>
    <h1>Amble Lite Editor</h1>
    <p class="lede">Edit any piece or snapshot page by page as on the Organelle - a piece also holds its roadmap and its loops - and what your KORG controllers do. Open this page from the Organelle over WiFi (its web server) and it reads and saves the AmbleLite folder's files there.</p>
  </header>

  <section class="panel" aria-labelledby="h-lib">
    <div class="row between"><h2 id="h-lib">Library</h2>
      <label class="toggle" for="file"><span class="label">Open pieces.txt, saves.txt, loops.txt or sections.txt</span><input id="file" type="file" accept=".txt,text/plain" multiple></label></div>
    <div class="lib">
      <div class="field"><span class="label">Pieces (pieces.txt)</span><div class="keys" id="kp"></div></div>
      <div class="field"><span class="label">Snapshots (saves.txt)</span><div class="keys" id="ks"></div></div>
    </div>
    <details><summary>Paste a file's text instead</summary>
      <div style="display:grid;gap:10px;margin-top:10px">
        <textarea id="paste" placeholder="Paste the text of pieces.txt or saves.txt here"></textarea>
        <div class="row"><button id="loadpaste" type="button">Load pasted text</button></div>
      </div></details>
    <div class="og" id="og" hidden>
      <p class="note">Opened from your Organelle's web server: this page reads and saves the files in <b id="ogdir"></b>.
        Saving keeps each file's previous version beside it (pieces.txt.bak ...). The patch reads its files when it loads,
        and writes them when you save on the Organelle - so reload the patch after saving here.</p>
      <div class="row">
        <button id="ogload" type="button">Load from the Organelle</button>
        <button class="primary" id="ogsave" type="button">Save and reload the patch</button>
        <button id="ogsaveonly" type="button">Save only</button>
      </div>
      <p class="note warn" id="ogconfirm" hidden></p>
    </div>
    <p class="status" id="libstatus" role="status"></p>
  </section>

  <section class="panel" aria-labelledby="h-ed">
    <div class="row between"><div><h2 id="h-ed">—</h2><div class="summary" id="sum"></div></div>
      <div class="row">
        <button id="fresh" type="button">Reset to defaults</button>
        <button id="clear" type="button">Empty this slot</button>
        <label class="toggle"><span class="label">Copy to</span><select id="copyto"></select></label>
        <button id="copygo" type="button">Copy</button>
      </div></div>
    <p class="note warn" id="confirm" hidden></p>
    <div id="editor"></div>
  </section>

  <section class="panel" aria-labelledby="h-midi">
    <div class="row between"><h2 id="h-midi">Controllers</h2>
      <div class="row">
        <label class="toggle"><span class="label">Controller</span><select id="mdev"></select></label>
        <label class="toggle"><span class="label">Scene</span><select id="mscene"></select></label>
        <button id="mreset" type="button">Back to the Amble Lite set</button>
      </div></div>
    <p class="note">Write the Amble Lite set to your KORG with KORG KONTROL Editor first (docs/controllers in the repository: AmbleLite.nktrl_st_set, AmbleLite.nanokey_st_set). Then change what any control does here, copy user.txt into the AmbleLite folder's controllers folder, and choose Profil: user on the MIDI page. user.txt holds both controllers.</p>
    <p class="summary" id="mabout"></p>
    <div id="mgrid" class="pages"></div>
    <div class="field"><span class="label">controllers/user.txt</span><textarea class="out" id="outm" readonly></textarea>
      <div class="row"><button class="primary" id="cpm" type="button">Copy user.txt</button><button id="dlm" type="button">Download</button>
        <button class="ogonly" id="ogsavem" type="button" hidden>Save user.txt to the Organelle</button></div></div>
  </section>

  <section class="panel" aria-labelledby="h-files" id="files">
    <h2 id="h-files">Save to the Organelle</h2>
    <p class="note">Easiest: open this page from the Organelle itself (planner.html in the AmbleLite folder, through the Organelle's web server - see the manual); then Save at the top writes these files there. Otherwise copy a file's text and save it over the file of the same name in the AmbleLite folder on the Organelle (keep a copy of the old one). The patch reads them when it loads.</p>
    <div class="files">
      <div class="field"><span class="label">pieces.txt</span><textarea class="out" id="outp" readonly></textarea>
        <div class="row"><button class="primary" id="cpp" type="button">Copy pieces.txt</button><button id="dlp" type="button">Download</button></div></div>
      <div class="field"><span class="label">saves.txt</span><textarea class="out" id="outs" readonly></textarea>
        <div class="row"><button class="primary" id="cps" type="button">Copy saves.txt</button><button id="dls" type="button">Download</button></div></div>
      <div class="field"><span class="label">loops.txt</span><textarea class="out" id="outl" readonly></textarea>
        <div class="row"><button class="primary" id="cpl" type="button">Copy loops.txt</button><button id="dll" type="button">Download</button></div></div>
      <div class="field"><span class="label">sections.txt</span><textarea class="out" id="outc" readonly></textarea>
        <div class="row"><button class="primary" id="cpc" type="button">Copy sections.txt</button><button id="dlc" type="button">Download</button></div></div>
    </div>
    <p class="status" id="filestatus" role="status"></p>
  </section>
</div>

<script>
const D = __DATA__;
__CORE__
const $ = id => document.getElementById(id);
const el = (tag, props = {}, ...kids) => { const e = Object.assign(document.createElement(tag), props); e.append(...kids); return e; };
const Y = C.Y;
let lib = { pieces: new Array(Y.pieces).fill(null), saves: new Array(Y.saveLines).fill(null), loops: null, secs: null };
const noSecs = () => Array.from({ length: Y.pieces * Y.maxsec }, () => []);
const noLoops = () => Array.from({ length: Y.pieces * Y.loopLayers }, () => [0, 0, 0, 0]);
let cur = { kind: "piece", idx: 0 }, tab = "g", sel = 0, example = false, pending = null;

const rec = () => cur.kind === "piece" ? lib.pieces[cur.idx] : lib.saves[cur.idx];
function setRec(r) { if (cur.kind === "piece") lib.pieces[cur.idx] = r; else lib.saves[cur.idx] = r; }

// ---- persistence (this browser only)
function store() { try { localStorage.setItem("al-lib", JSON.stringify({ lib, cur, tab })); } catch (e) {} }
function restore() {
  try {
    const s = JSON.parse(localStorage.getItem("al-lib") || "null");
    if (s && s.lib && Array.isArray(s.lib.pieces) && Array.isArray(s.lib.saves)) {
      s.lib.pieces = s.lib.pieces.map(r => r && C.widen(r, Y.piece));
      s.lib.saves = s.lib.saves.map(r => r && C.widen(r, Y.snap));
    }
    if (s && s.lib && s.lib.pieces.length === Y.pieces && s.lib.saves.length === Y.saveLines &&
        [...s.lib.pieces, ...s.lib.saves].every(r => r === null || r.length === Y.piece || r.length === Y.snap)) {
      lib = s.lib; if (!Array.isArray(lib.loops) || lib.loops.length !== Y.pieces * Y.loopLayers) lib.loops = null;
      cur = s.cur || cur; tab = s.tab || tab; return true;
    }
  } catch (e) {}
  return false;
}

// ---- library
function keys() {
  const mk = (box, kind, n) => {
    box.replaceChildren();
    for (let i = 0; i < n; i++) {
      const full = !!(kind === "piece" ? lib.pieces[i] : lib.saves[i]), on = cur.kind === kind && cur.idx === i;
      const b = el("button", { type: "button", className: "key" + (full ? " full" : "") + (on ? " cur" : ""), textContent: i + 1,
        title: `${kind === "piece" ? "Piece" : "Snapshot"} ${i + 1}${full ? "" : " (empty)"}` });
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.onclick = () => { cur = { kind, idx: i }; sel = 0; if ((tab === "road" || tab === "loops") && kind !== "piece") tab = "g"; render(); };
      box.append(b);
    }
  };
  mk($("kp"), "piece", Y.pieces); mk($("ks"), "snap", Y.saves);
}

function load(text, fname) {
  const k = /section/i.test(fname || "") ? "secs" : C.kindOf(text) || (/save/i.test(fname || "") ? "snap" : /piece/i.test(fname || "") ? "piece" : /loop/i.test(fname || "") ? "loops" : null);
  if (!k) { $("libstatus").textContent = "That file holds no pieces, snapshots or loops. Open pieces.txt, saves.txt or loops.txt from the AmbleLite folder."; return; }
  if (k === "secs") {
    lib.secs = C.parseSecs(text);
    const n = lib.secs.filter(c => c.length).length;
    $("libstatus").textContent = `Loaded sections.txt: ${n} section${n === 1 ? "" : "s"} with parameter changes.`;
    render(); store(); return;
  }
  if (k === "loops") {
    lib.loops = C.parseLoops(text);
    const n = lib.loops.filter(a => a[0] > 0).length;
    $("libstatus").textContent = `Loaded loops.txt: ${n} loop${n === 1 ? "" : "s"} across the pieces.`;
    if (cur.kind === "piece") tab = "loops";
    render(); store(); return;
  }
  const recs = C.parse(text, k === "piece" ? Y.piece : Y.snap);
  if (k === "piece") { lib.pieces = Array.from({ length: Y.pieces }, (_, i) => recs[i] || null); cur = { kind: "piece", idx: Math.max(0, lib.pieces.findIndex(Boolean)) }; }
  else { lib.saves = Array.from({ length: Y.saveLines }, (_, i) => recs[i] || null); cur = { kind: "snap", idx: Math.max(0, lib.saves.findIndex((r, i) => r && i < Y.saves)) }; }
  example = false;
  const n = (k === "piece" ? lib.pieces.slice(0, Y.pieces) : lib.saves.slice(0, Y.saves)).filter(Boolean).length;
  $("libstatus").textContent = `Loaded ${k === "piece" ? "pieces.txt" : "saves.txt"}: ${n} ${k === "piece" ? "pieces" : "snapshots"}.`;
  sel = 0; if ((tab === "road" || tab === "loops") && k !== "piece") tab = "g"; render();
}
$("file").onchange = e => {
  [...e.target.files].forEach(f => { const r = new FileReader(); r.onload = () => load(r.result, f.name); r.readAsText(f); });
  e.target.value = "";
};
$("loadpaste").onclick = () => load($("paste").value, "");

// ---- the editor
function tabs() {
  const r = rec(), bar = el("div", { className: "tabs", role: "tablist" });
  const list = [["g", "GLOBAL"], ...D.layers.map((l, i) => [String(i), l.label]), ["rh", "RHYTHMS"]];
  if (cur.kind === "piece") list.push(["loops", "LOOPS"], ["road", "ROADMAP"]);
  list.forEach(([id, txt]) => {
    const b = el("button", { type: "button", className: "tab", textContent: txt, id: `tab-${id}` });
    b.setAttribute("role", "tab"); b.setAttribute("aria-selected", tab === id ? "true" : "false");
    if (/^\d+$/.test(id) && r && !r[Y.inn + +id]) { b.classList.add("out"); b.title = "Out of the mix"; }
    b.onclick = () => { tab = id; sel = 0; render(); };
    bar.append(b);
  });
  return bar;
}

function knob(s, label) {
  const r = rec();
  if (s < 0) return el("div", { className: "knob empty" }, el("span", { className: "nm", textContent: "—" }));
  const sl = D.slots[s], ch = C.choices(s, r), id = `k-${s}`;
  const nm = el("label", { className: "nm", htmlFor: id, textContent: label || sl.n, title: label || C.name(s) });
  if (ch) {
    const se = el("select", { id });
    ch.forEach((c, i) => se.add(new Option(c, i)));
    se.value = C.index(s, r);
    se.onchange = () => { C.setIndex(s, r, +se.value); changed(sl.n === "Engine" || s === D.scaleSlot || s === D.layers[C.layerOf(s)]?.eng); };
    return el("div", { className: "knob" }, nm, se);
  }
  const lo = sl.t === "num" ? sl.lo : 0, hi = sl.t === "num" ? sl.hi : 100;
  const rg = el("input", { type: "range", id, min: lo, max: hi, step: 1, value: C.number(s, r) });
  const val = el("output", { className: "val", textContent: C.number(s, r) });
  rg.oninput = () => { C.setNumber(s, r, +rg.value); val.textContent = C.number(s, r); changed(false); };
  return el("div", { className: "knob" }, nm, rg, val);
}

function page(title, slots, labels, extra) {
  const p = el("div", { className: "page" }, el("h3", { textContent: title }));
  if (extra) p.querySelector("h3").append(el("span", { textContent: extra }));
  slots.forEach((s, k) => p.append(knob(s, labels ? labels[k] : null)));
  return p;
}

function favPage(li) {
  const r = rec(), L = D.layers[li], ei = C.optIndex(L.eng, r), e = L.engines[ei];
  const cand = [...(L.engines.length > 1 ? [L.eng] : []), ...L.targets[e]];
  const p = el("div", { className: "page" }, el("h3", { textContent: "FAV" }, el("span", { textContent: "your four" })));
  for (let k = 0; k < 4; k++) {
    const at = C.favAt(li, ei, k), id = `fav-${li}-${k}`;
    const se = el("select", { id });
    se.add(new Option("—", -1));
    cand.forEach(s => se.add(new Option(s === L.eng ? "Engine" : C.name(s), s)));
    se.value = cand.includes(r[at]) ? r[at] : -1;
    se.onchange = () => { r[at] = +se.value; changed(false); };
    p.append(el("div", { className: "knob" }, el("label", { className: "nm", htmlFor: id, textContent: `Knob ${k + 1}` }), se));
  }
  return p;
}

function layerTab(li) {
  const r = rec(), L = D.layers[li], box = el("div", { style: "display:grid;gap:14px" });
  const bar = el("div", { className: "layerbar" });
  const inn = el("input", { type: "checkbox", id: `in-${li}`, checked: !!r[Y.inn + li] });
  inn.onchange = () => { r[Y.inn + li] = inn.checked ? 1 : 0; changed(true); };
  bar.append(el("label", { className: "toggle", htmlFor: `in-${li}` }, inn, "In the mix"));
  if (L.latch) {
    const la = el("input", { type: "checkbox", id: `latch-${li}`, checked: !!r[Y.latch + li] });
    la.onchange = () => { r[Y.latch + li] = la.checked ? 1 : 0; changed(false); };
    bar.append(el("label", { className: "toggle", htmlFor: `latch-${li}` }, la, "Latched (holds its notes)"));
  }
  bar.append(el("span", { className: "summary", textContent: `engine: ${C.engine(r, li)}` }));
  box.append(bar);
  const grid = el("div", { className: "pages" });
  D.layers[li].pages[C.engine(r, li)].forEach(([n, sl], i) => grid.append(i === 0 ? favPage(li) : page(n, sl)));
  box.append(grid);
  return box;
}

function globalTab() {
  const r = rec(), grid = el("div", { className: "pages" });
  D.gpages.forEach(([n, sl, lab]) => grid.append(page(n, sl, sl.map((s, k) => lab[k] >= 0 ? `${D.short[lab[k]]} ${D.slots[s].n}` : null))));
  return grid;
}

function rhythmTab() {
  const r = rec(), box = el("div", { className: "rh" });
  box.append(el("p", { className: "note", textContent: "Tapped rhythms: a lane plays its own when MOTION > Patt is 'tapped'; the drone, sub and pads when GATE > Gate is 'tapped'. Steps past the layer's Steps are ignored." }));
  D.rhythm.forEach((h, ri) => {
    const n = C.number(h.steps, r), on = C.index(h.patt, r) === h.tapped, row = el("div", { className: "steps" });
    for (let k = 0; k < 16; k++) {
      const at = Y.tap + ri * 16 + k, b = el("button", { type: "button", className: "step" + (r[at] ? " on" : "") + (k >= n ? " off" : ""), title: `Step ${k + 1}` });
      b.setAttribute("aria-pressed", r[at] ? "true" : "false");
      b.onclick = () => { r[at] = r[at] ? 0 : 1; changed(true); };
      row.append(b);
    }
    const lab = el("div", {}, el("b", { textContent: D.llabels[h.layer] }), el("div", { className: "summary", textContent: on ? "tapped" : C.text(h.patt, r) }));
    box.append(el("div", { className: "rhrow" }, lab, row));
  });
  return box;
}

// ---- a piece's loops (loops.txt): each layer's, drawn as notes over the cycle
const STATES = { 0: "none", 2: "playing", 4: "stopped" };
function loopsTab() {
  const box = el("div", { style: "display:grid;gap:12px" });
  if (!lib.loops) {
    box.append(el("p", { className: "note", textContent: "Open loops.txt from the AmbleLite folder to see this piece's loops. Without it, pieces.txt still saves everything else; the loops already on the Organelle stay as they are." }));
    return box;
  }
  box.append(el("p", { className: "note", textContent: "Loops are recorded on the Organelle. Here you can see them, stop or start them for when the piece loads, and clear them." }));
  for (let li = 0; li < Y.loopLayers; li++) {
    const at = cur.idx * Y.loopLayers + li, lp = C.loop(lib.loops[at]);
    const row = el("div", { className: "rhrow" });
    const head = el("div", {}, el("b", { textContent: D.llabels[li] }),
      el("div", { className: "summary", textContent: lp.state ? `${STATES[lp.state] || lp.state} · ${lp.free ? `free · ${(lp.len * Y.freeMs / 1000).toFixed(1)} s` : `${+(lp.len / Y.bar).toFixed(2)} bars`} · ${lp.n} events` : "no loop" }));
    const right = el("div", { style: "display:grid;gap:6px;min-width:0" });
    if (lp.state) {
      right.append(roll(lp));
      const st = el("select", { id: `lstate-${li}` }); st.add(new Option("plays when loaded", 2)); st.add(new Option("stopped when loaded", 4));
      st.value = lp.state === 4 ? 4 : 2;
      st.onchange = () => { lib.loops[at][0] = +st.value + (lp.free ? 10 : 0); changed(true); };
      const clr = el("button", { type: "button", textContent: "Clear loop" });
      clr.onclick = () => { lib.loops[at] = [0, 0, 0, 0]; changed(true); };
      right.append(el("div", { className: "row" }, st, clr));
    }
    row.append(head, right);
    box.append(row);
  }
  return box;
}
function roll(lp) {
  const ns = "http://www.w3.org/2000/svg", len = Math.max(1, lp.len), on = [];
  const notes = lp.note.filter((_, i) => lp.vel[i] > 0), lo = Math.min(...notes, 127), hi = Math.max(...notes, 0), span = Math.max(12, hi - lo + 1);
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${len} ${span}`); svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", `${notes.length} notes over ${+(len / Y.bar).toFixed(2)} bars`);
  svg.style.cssText = "width:100%;height:56px;background:var(--bg);border:1px solid var(--line);border-radius:4px";
  for (let b = Y.bar; !lp.free && b < len; b += Y.bar) {
    const l = document.createElementNS(ns, "line");
    l.setAttribute("x1", b); l.setAttribute("x2", b); l.setAttribute("y1", 0); l.setAttribute("y2", span);
    l.setAttribute("stroke", "var(--line)"); l.setAttribute("vector-effect", "non-scaling-stroke"); svg.append(l);
  }
  lp.t.forEach((t, i) => {
    if (lp.vel[i] <= 0) return;
    let end = len;
    for (let j = 1; j <= lp.n; j++) { const k = (i + j) % lp.n; if (lp.note[k] === lp.note[i] && lp.vel[k] <= 0) { end = lp.t[k] >= t ? lp.t[k] : lp.t[k] + len; break; } }
    const r = document.createElementNS(ns, "rect");
    r.setAttribute("x", t); r.setAttribute("y", hi - lp.note[i]); r.setAttribute("width", Math.max(2, Math.min(end, len) - t)); r.setAttribute("height", 1);
    r.setAttribute("fill", "var(--accent)"); r.setAttribute("opacity", 0.4 + 0.6 * lp.vel[i]); svg.append(r);
  });
  return svg;
}

// ---- the roadmap (the patch's own rule: roadmap.py, al-rgen)
const int = x => Math.trunc(x);
const fmt = sec => `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`;
function roadTab() {
  const r = rec(), secs = C.road(r), tempo = C.number(D.tempo, r), box = el("div", { style: "display:grid;gap:14px" });
  const setup = el("div", { className: "setup" });
  const f = (lab, input) => el("label", { className: "field" }, el("span", { className: "label", textContent: lab }), input);
  const mins = el("input", { type: "number", id: "mins", min: 4, max: 30, value: 12 });
  const arc = el("select", { id: "arc" }); D.arcs.forEach((a, i) => arc.add(new Option(a, i)));
  const tens = el("input", { type: "range", id: "tens", min: 0, max: 100, value: 40 });
  const dens = el("input", { type: "range", id: "dens", min: 0, max: 100, value: 50 });
  const varia = el("input", { type: "number", id: "varia", min: 0, max: 15, value: 0 });
  setup.append(f("Minutes", mins), f("Arc", arc), f("Tension", tens), f("Density", dens), f("Variation", varia));
  const build = el("button", { type: "button", className: "primary", textContent: "Build roadmap" });
  build.onclick = () => {
    const a = +arc.value, roles = D.arcRoles[a], tot = +mins.value * tempo / 4, t = tens.value / 100, d = dens.value / 100, v = +varia.value;
    const sw = roles.reduce((s, x) => s + D.weights[x], 0), dt = Math.min(2, int(d * 2.99));
    C.setRoad(r, roles.map((ro, i) => ({ role: ro, bars: Math.max(4, int(tot * D.weights[ro] / sw / 4 + 0.5) * 4), mask: D.masks[ro][dt],
      story: D.pools[Math.min(2, int(t * D.tension[ro] * 2.2))][(v * 5 + i * 3 + a) % 8] })));
    sel = 0; changed(true);
  };
  const total = secs.reduce((s, x) => s + x.bars, 0);
  box.append(setup, el("div", { className: "row" }, build, el("span", { className: "summary", textContent: secs.length ? `${secs.length} sections, ${total} bars, ${fmt(total * 4 * 60 / tempo)} at ${tempo} bpm` : "No roadmap in this piece yet." })));
  if (!secs.length) return box;
  // each section's parameter changes (sections.txt) travel with it when sections are added or removed
  const base = cur.idx * Y.maxsec;
  secs.forEach((x, i) => { x.ch = lib.secs ? lib.secs[base + i] : []; });
  const save = () => {
    C.setRoad(r, secs);
    if (lib.secs) for (let i = 0; i < Y.maxsec; i++) lib.secs[base + i] = i < secs.length ? secs[i].ch : [];
    changed(true);
  };
  const tl = el("div", { className: "timeline", role: "list" });
  secs.forEach((s, i) => {
    const d = el("div", { className: "seg" + (i === sel ? " sel" : ""), tabIndex: 0 });
    d.setAttribute("role", "listitem"); d.style.flexGrow = s.bars; d.style.background = `var(--r${s.role})`;
    d.append(el("b", { textContent: D.roles[s.role] }), el("span", { textContent: `${s.bars} bars` }));
    d.onclick = () => { sel = i; render(); };
    d.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sel = i; render(); } };
    tl.append(d);
  });
  const add = el("button", { type: "button", textContent: "Add section", disabled: secs.length >= Y.maxsec });
  add.onclick = () => { secs.splice(sel + 1, 0, { ...secs[sel], ch: [] }); sel++; save(); };
  const del = el("button", { type: "button", textContent: "Remove selected", disabled: secs.length <= 1 });
  del.onclick = () => { secs.splice(sel, 1); sel = Math.max(0, sel - 1); save(); };
  const tb = el("tbody");
  secs.forEach((s, i) => {
    const tr = el("tr", { className: i === sel ? "sel" : "" });
    tr.onclick = e => { if (e.target === tr || e.target.tagName === "TD") { sel = i; render(); } };
    const rs = el("select", { id: `role-${i}` }); D.roles.forEach((x, k) => rs.add(new Option(x, k))); rs.value = s.role;
    rs.onchange = () => { s.role = +rs.value; save(); };
    const dot = el("span", { className: "dot" }); dot.style.background = `var(--r${s.role})`;
    const b = el("input", { type: "number", id: `bars-${i}`, min: 4, max: 64, step: 4, value: s.bars });
    b.onchange = () => { s.bars = Math.max(4, Math.min(64, +b.value || 4)); save(); };
    const st = el("select", { id: `story-${i}` }); D.stories.forEach((n, k) => st.add(new Option(n, k))); st.value = s.story;
    st.onchange = () => { s.story = +st.value; save(); };
    const ch = el("div", { className: "chips" });
    D.short.forEach((n, k) => {
      const on = (s.mask >> k) & 1, t = el("button", { type: "button", className: "chip" + (on ? " on" : ""), textContent: n, title: D.llabels[k] + (on ? " in" : " out") });
      t.setAttribute("aria-pressed", on ? "true" : "false");
      t.onclick = () => { s.mask ^= (1 << k); save(); };
      ch.append(t);
    });
    tr.append(el("td", { className: "num", textContent: i + 1 }), el("td", {}, dot, rs), el("td", {}, b),
              el("td", { className: "num", textContent: fmt(s.bars * 4 * 60 / tempo) }), el("td", {}, st), el("td", {}, ch),
              el("td", { className: "num", textContent: s.ch.length || "—" }));
    tb.append(tr);
  });
  const head = el("tr"); ["#", "Role", "Bars", "Time", "Story", "Layers in", "Changes"].forEach(h => head.append(el("th", { textContent: h })));
  box.append(tl, el("div", { className: "row" }, add, del));
  box.append(el("div", { className: "tablewrap" }, el("table", {}, el("thead", {}, head), tb)));
  box.append(changesPanel(r, secs, Math.min(sel, secs.length - 1), save));
  const txt = secs.map(s => `${s.bars} ${s.story} ${s.mask} ${s.role};`).join("\n");
  const cp = el("button", { type: "button", textContent: "Copy as roadmap.txt" });
  cp.onclick = () => copy(txt, null, "Copied roadmap.txt.");
  box.append(el("details", {}, el("summary", { textContent: "This roadmap as roadmap.txt (for the patch's ROAD pages without a piece)" }),
    el("div", { style: "display:grid;gap:8px;margin-top:8px" }, el("textarea", { className: "out", readOnly: true, value: txt }), el("div", { className: "row" }, cp))));
  return box;
}

// a section's parameter changes: applied when it starts (Road auto), on top of the sound as it is then - knob
// values glide over Morph, choices switch at once. Captured on the Organelle (SECTN page, top A#) or made here
let paramOptions = null;
function paramSelect(value, id) {
  if (!paramOptions) {
    paramOptions = [["GLOBAL", []], ...D.layers.map(l => [l.label, []])];
    D.slots.forEach((sl, i) => { if (D.capt[i]) paramOptions[sl.L === "g" ? 0 : 1 + D.layers.findIndex(l => l.id === sl.L)][1].push(i); });
  }
  const se = el("select", { id });
  paramOptions.forEach(([g, ks]) => { const og = el("optgroup", { label: g }); ks.forEach(k => og.append(new Option(C.name(k), k))); se.append(og); });
  se.value = String(value);
  return se;
}
function valueControl(r, s, v, set, id) {
  const tmp = r.slice(); tmp[s] = v;
  const ch = C.choices(s, tmp);
  if (ch) {
    const se = el("select", { id }); ch.forEach((c, i) => se.add(new Option(c, i))); se.value = C.index(s, tmp);
    se.onchange = () => { C.setIndex(s, tmp, +se.value); set(tmp[s], false); };
    return se;
  }
  const sl = D.slots[s], lo = sl.t === "num" ? sl.lo : 0, hi = sl.t === "num" ? sl.hi : 100;
  const rg = el("input", { type: "range", id, min: lo, max: hi, step: 1, value: C.number(s, tmp) });
  const out = el("output", { className: "val", textContent: C.number(s, tmp) });
  rg.oninput = () => { C.setNumber(s, tmp, +rg.value); out.textContent = C.number(s, tmp); set(tmp[s], true); };
  return el("span", { className: "row" }, rg, out);
}
function changesPanel(r, secs, i, save) {
  const s = secs[i], box = el("div", { className: "field" });
  box.append(el("span", { className: "label", textContent: `Section ${i + 1}: parameter changes (applied as it starts, on top of the sound as it is - knobs glide over Morph)` }));
  if (!lib.secs) {
    box.append(el("p", { className: "note", textContent: "Open sections.txt from the AmbleLite folder (or open this page from the Organelle) to edit the sections' changes." }));
    return box;
  }
  const list = el("div", { style: "display:grid;gap:6px" });
  s.ch.forEach((p, k) => {
    const ps = paramSelect(p[0], `chp-${i}-${k}`);
    ps.onchange = () => { p[0] = +ps.value; p[1] = r[p[0]]; save(); };
    const vc = valueControl(r, p[0], p[1], (v, live) => { p[1] = v; if (live) { files(); store(); } else save(); }, `chv-${i}-${k}`);
    const rm = el("button", { type: "button", textContent: "Remove" });
    rm.onclick = () => { s.ch.splice(k, 1); save(); };
    list.append(el("div", { className: "row" }, ps, vc, rm));
  });
  if (!s.ch.length) list.append(el("p", { className: "note", textContent: "No changes: this section plays on with the sound as it is." }));
  const add = el("button", { type: "button", textContent: "Add a change", disabled: s.ch.length >= D.maxch });
  add.onclick = () => {
    const used = new Set(s.ch.map(p => p[0]));
    const f = D.slots.findIndex(sl => sl.L === "g" && sl.n === "Filter"), k = !used.has(f) ? f : D.capt.findIndex((c, x) => c && !used.has(x));
    s.ch.push([k, r[k]]); save();
  };
  box.append(list, el("div", { className: "row" }, add, el("span", { className: "summary", textContent: `${s.ch.length} of ${D.maxch}` })));
  return box;
}

// ---- one render for everything
function render() {
  keys();
  const r = rec(), name = `${cur.kind === "piece" ? "Piece" : "Snapshot"} ${cur.idx + 1}`;
  $("h-ed").textContent = name + (r ? "" : " (empty)");
  $("sum").textContent = r ? `${C.text(D.key, r)} ${C.text(D.modeSlot, r)} · ${C.number(D.tempo, r)} bpm · in: ${D.layers.filter((l, i) => r[Y.inn + i]).map(l => l.short).join(" ")}` +
    (example ? " · example: the patch's defaults" : "") : "";
  $("fresh").textContent = r ? "Reset to defaults" : "Start from defaults";
  $("clear").disabled = !r;
  const ct = $("copyto"); ct.replaceChildren();
  for (let i = 0; i < Y.pieces; i++) ct.add(new Option(`Piece ${i + 1}${lib.pieces[i] ? "" : " (empty)"}`, `piece:${i}`));
  for (let i = 0; i < Y.saves; i++) ct.add(new Option(`Snapshot ${i + 1}${lib.saves[i] ? "" : " (empty)"}`, `snap:${i}`));
  $("copygo").disabled = !r;
  const ed = $("editor"); ed.replaceChildren();
  if (!r) {
    ed.append(el("p", { className: "note", textContent: `${name} is empty. Start it from the patch's defaults, or copy another piece or snapshot into it.` }));
  } else {
    ed.append(tabs(), el("div", { style: "margin-top:14px" }, tab === "g" ? globalTab() : tab === "rh" ? rhythmTab() : tab === "road" ? roadTab() : tab === "loops" ? loopsTab() : layerTab(+tab)));
  }
  files();
}

function changed(redraw) { example = false; if (redraw) render(); else { files(); $("sum").textContent = $("sum").textContent.replace(" · example: the patch's defaults", ""); } store(); }
function files() {
  $("outp").value = C.write(lib.pieces); $("outs").value = C.write(lib.saves);
  $("outl").value = lib.loops ? C.write(lib.loops) : "(open loops.txt to edit the loops: until then, keep the one on the Organelle)";
  $("cpl").disabled = $("dll").disabled = !lib.loops;
  $("outc").value = lib.secs ? C.writeSecs(lib.secs) : "(open sections.txt to edit the sections' changes: until then, keep the one on the Organelle)";
  $("cpc").disabled = $("dlc").disabled = !lib.secs;
}

// slot actions, with a confirmation in the page for anything that replaces a slot
function ask(msg, go) {
  const c = $("confirm"); c.replaceChildren(msg + " ");
  const yes = el("button", { type: "button", textContent: "Replace" }), no = el("button", { type: "button", textContent: "Keep" });
  yes.onclick = () => { c.hidden = true; go(); }; no.onclick = () => { c.hidden = true; };
  c.append(yes, " ", no); c.hidden = false;
}
$("fresh").onclick = () => {
  const go = () => { setRec(C.defaults(cur.kind)); noLoopsHere(); changed(true); };
  rec() ? ask("Reset every setting in this slot to the patch's defaults?", go) : go();
};
function noLoopsHere() {
  if (cur.kind === "piece" && lib.loops) for (let li = 0; li < Y.loopLayers; li++) lib.loops[cur.idx * Y.loopLayers + li] = [0, 0, 0, 0];
  if (cur.kind === "piece" && lib.secs) for (let i = 0; i < Y.maxsec; i++) lib.secs[cur.idx * Y.maxsec + i] = [];
}
$("clear").onclick = () => ask("Empty this slot? It saves as empty (-1), and a piece's loops go too.", () => { setRec(null); noLoopsHere(); tab = "g"; changed(true); });
$("copygo").onclick = () => {
  const [kind, i] = $("copyto").value.split(":"), idx = +i, r = rec();
  const go = () => {
    const out = kind === "piece" ? C.asPiece(r.slice()) : C.asSnap(r);
    if (kind === "piece") lib.pieces[idx] = out; else lib.saves[idx] = out;
    if (kind === "piece" && lib.loops) for (let li = 0; li < Y.loopLayers; li++)
      lib.loops[idx * Y.loopLayers + li] = cur.kind === "piece" ? lib.loops[cur.idx * Y.loopLayers + li].slice() : [0, 0, 0, 0];
    if (kind === "piece" && lib.secs) for (let i = 0; i < Y.maxsec; i++)
      lib.secs[idx * Y.maxsec + i] = cur.kind === "piece" ? lib.secs[cur.idx * Y.maxsec + i].map(p => p.slice()) : [];
    cur = { kind, idx }; if ((tab === "road" || tab === "loops") && kind !== "piece") tab = "g"; changed(true);
  };
  const full = kind === "piece" ? lib.pieces[idx] : lib.saves[idx];
  full ? ask(`${kind === "piece" ? "Piece" : "Snapshot"} ${idx + 1} holds a sound. Replace it?`, go) : go();
};

function copy(text, area, done) {
  navigator.clipboard.writeText(text).then(() => $("filestatus").textContent = done, () => {
    if (area) { area.focus(); area.select(); }
    $("filestatus").textContent = "Selected: copy it with your keyboard.";
  });
}
function download(text, name) {
  const a = el("a", { href: URL.createObjectURL(new Blob([text], { type: "text/plain" })), download: name });
  document.body.append(a); a.click(); a.remove();
  $("filestatus").textContent = `Downloading ${name}. If nothing happens here, use Copy.`;
}
$("cpp").onclick = () => copy($("outp").value, $("outp"), "Copied pieces.txt.");
$("cps").onclick = () => copy($("outs").value, $("outs"), "Copied saves.txt.");
$("dlp").onclick = () => download($("outp").value, "pieces.txt");
$("dls").onclick = () => download($("outs").value, "saves.txt");
$("cpl").onclick = () => copy($("outl").value, $("outl"), "Copied loops.txt.");
$("dll").onclick = () => download($("outl").value, "loops.txt");
$("cpc").onclick = () => copy($("outc").value, $("outc"), "Copied sections.txt.");
$("dlc").onclick = () => download($("outc").value, "sections.txt");

// ---- on the Organelle: this page opened through Organelle OS's web server (port 8080) as
// /get_file?fpath=<card>/Patches/<folder>/planner.html - its /get_file reads the folder's files, /save writes them,
// /reload_patch reloads the patch. Saving keeps the old text as <name>.bak; a file changed on the Organelle since it
// was loaded here (a save there) is only overwritten when you say so
const OG = (() => {
  if (!/\/get_file$/.test(location.pathname)) return null;
  const f = new URLSearchParams(location.search).get("fpath");
  return f ? { dir: f.replace(/^\/+/, "").replace(/\/[^/]*$/, "") } : null;
})();
const ogSeen = {};
async function ogGet(name) {
  const r = await fetch(`/get_file?fpath=${encodeURIComponent(OG.dir + "/" + name)}&_=${Date.now()}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${name}: ${r.status}`);
  return r.text();
}
async function ogPut(name, text) {
  const r = await fetch("/save", { method: "POST", body: new URLSearchParams({ fpath: OG.dir + "/" + name, content: text }) });
  if (!r.ok) throw new Error(`${name}: ${r.status}`);
}
async function ogLoad() {
  const got = [], none = [];
  for (const name of ["sections.txt", "loops.txt", "saves.txt", "pieces.txt"]) {     // (pieces last: it opens on a piece)
    // (a fresh install has none of them until something is saved on the Organelle)
    try { const t = await ogGet(name); ogSeen[name] = t; if (t.trim()) { load(t, name); got.push(name); } else none.push(name); }
    catch (e) { ogSeen[name] = null; none.push(name); }
    // (none there yet: made empty here, so saving creates them)
    if (none.includes(name) && name === "loops.txt") lib.loops = noLoops();
    if (none.includes(name) && name === "sections.txt") lib.secs = noSecs();
  }
  try { ogSeen["controllers/user.txt"] = await ogGet("controllers/user.txt"); } catch (e) { ogSeen["controllers/user.txt"] = null; }
  $("libstatus").textContent = (got.length ? `Loaded ${got.join(", ")} from the Organelle.` : "Connected to the Organelle.") +
    (none.length ? ` Not there yet: ${none.join(", ")} (nothing saved yet) - saving here creates ${none.length > 1 ? "them" : "it"}.` : "");
}
async function ogSave(files, reload, status, then) {
  const now = {};
  for (const name of Object.keys(files)) { try { now[name] = await ogGet(name); } catch (e) { now[name] = null; } }
  const moved = Object.keys(files).filter(n => n in ogSeen && now[n] !== null && now[n] !== (ogSeen[n] ?? null));
  const go = async () => {
    try {
      for (const [name, text] of Object.entries(files)) {
        if (now[name] !== null && now[name] !== text) await ogPut(name + ".bak", now[name]);
        await ogPut(name, text); ogSeen[name] = text;
      }
      if (reload) await fetch("/reload_patch", { method: "POST", body: new URLSearchParams({ path: "/" + OG.dir }) });
      status.textContent = `Saved ${Object.keys(files).join(", ")} on the Organelle` +
        (reload ? " and reloaded the patch." : ` (${then || "the patch takes them when it next loads"}).`);
    } catch (e) { status.textContent = `Saving failed: ${e.message}. Nothing else was changed.`; }
  };
  if (!moved.length) return go();
  const c = $("ogconfirm");
  c.replaceChildren(`${moved.join(", ")} changed on the Organelle since you loaded ${moved.length > 1 ? "them" : "it"} here (a save there?). Save over ${moved.length > 1 ? "them" : "it"}? (The Organelle's version is kept as .bak.) `);
  const yes = el("button", { type: "button", textContent: "Save over" }), no = el("button", { type: "button", textContent: "Cancel" });
  yes.onclick = () => { c.hidden = true; go(); }; no.onclick = () => { c.hidden = true; status.textContent = "Not saved."; };
  c.append(yes, " ", no); c.hidden = false;
}
if (OG) {
  $("og").hidden = false; $("ogdir").textContent = "/" + OG.dir; $("ogsavem").hidden = false;
  $("files").hidden = true;        // (copying the files by hand: only when the page is opened elsewhere)
  // (loops.txt and sections.txt only once they are loaded or made here - never the placeholder text)
  const lib3 = () => ({ "pieces.txt": $("outp").value, "saves.txt": $("outs").value,
                        ...(lib.loops ? { "loops.txt": $("outl").value } : {}), ...(lib.secs ? { "sections.txt": $("outc").value } : {}) });
  $("ogload").onclick = ogLoad;
  $("ogsave").onclick = () => ogSave(lib3(), true, $("libstatus"));
  $("ogsaveonly").onclick = () => ogSave(lib3(), false, $("libstatus"));
  $("ogsavem").onclick = () => ogSave({ "controllers/user.txt": $("outm").value }, false, $("filestatus"), "choose Profil: user on the MIDI page");
  ogLoad();
}

// ---- controllers: the KORGs' controls, what each does (korg.py's design to start), user.txt
const MD = D.midi;
const ACTS = [["", "—"], ["knob", "Page knob"], ["level", "Layer level"], ["param", "A parameter"], ["engp", "Engine parameter"],
  ["breath", "Breath"], ["toggle", "Layer in / out"], ["show", "Show layer"], ["loopl", "Layer's loop key"],
  ["start", "Start"], ["stop", "Stop"], ["startstop", "Start / stop"], ["chordnext", "Next chord"], ["chordprev", "Previous chord"],
  ["loop", "Loop key"], ["loopstop", "Loop stop"], ["loopclear", "Loop clear"], ["pgnext", "Next page"], ["pgprev", "Previous page"],
  ["play", "Play view"], ["mix", "MIX view"], ["shape", "SHAPE page"], ["pattern", "Pattern view"]];
const fresh = () => JSON.parse(JSON.stringify(Object.fromEntries(Object.entries(MD.devices).map(([k, d]) => [k, d.scenes.map(x => x.map)]))));
let mmap = fresh(), mdev = "nanoktl", mscene = 0;
try { const m = JSON.parse(localStorage.getItem("al-midi") || "null"); if (m && m.nanoktl && m.nanokey) mmap = m; } catch (e) {}
const mstore = () => { try { localStorage.setItem("al-midi", JSON.stringify(mmap)); } catch (e) {} };
const keyName = k => { const i = MD.keys.indexOf(k); if (i < 0) return k; const sl = D.slots[i], li = D.layers.findIndex(l => l.id === sl.L);
  return `${li >= 0 ? D.llabels[li] : "GLOBAL"} · ${sl.e ? `${sl.n} (${sl.e})` : sl.n}`; };
function argControl(act, arg, set, id) {
  const sel = el("select", { id });
  if (act === "knob") for (let k = 1; k <= 8; k++) sel.add(new Option(`Knob ${k}`, k));
  else if (["level", "toggle", "show"].includes(act)) D.llabels.forEach((n, i) => sel.add(new Option(n, i + 1)));
  else if (act === "loopl") D.llabels.slice(0, MD.noteLayers).forEach((n, i) => sel.add(new Option(n, i + 1)));
  else if (act === "engp") D.llabels.forEach((n, i) => { for (let k = 1; k <= 8; k++) sel.add(new Option(`${n} ${k}`, (i + 1) * 10 + k)); });
  else if (act === "param") {
    const groups = {};
    MD.keys.forEach(k => { const g = k.split(".")[0]; (groups[g] = groups[g] || []).push(k); });
    Object.entries(groups).forEach(([g, ks]) => {
      const og = el("optgroup", { label: g === "g" ? "GLOBAL" : D.llabels[D.layers.findIndex(l => l.id === g)] });
      ks.forEach(k => og.append(new Option(keyName(k), k))); sel.append(og);
    });
  } else return null;
  if (arg !== null && arg !== undefined) sel.value = String(arg);
  if (sel.value === "" && sel.options.length) sel.selectedIndex = 0;
  sel.onchange = () => set(act === "param" ? sel.value : +sel.value);
  return sel;
}
function midiRender() {
  const dev = MD.devices[mdev], ds = $("mdev"), sc = $("mscene");
  if (!ds.options.length) Object.entries(MD.devices).forEach(([k, d]) => ds.add(new Option(d.name, k)));
  ds.value = mdev;
  sc.replaceChildren(); dev.scenes.forEach((x, i) => sc.add(new Option(`${i + 1} ${x.name}`, i)));
  mscene = Math.min(mscene, dev.scenes.length - 1); sc.value = mscene;
  const scene = dev.scenes[mscene], map = mmap[mdev][mscene];
  $("mabout").textContent = `${scene.about}. Channel ${scene.ch}${scene.padch ? `, pads on channel ${scene.padch}` : ""}.`;
  const groups = {};
  dev.controls.forEach(c => { const g = /^(Play|Stop|Rec|Rew|FF|Cycle|Button \d+|Marker.*|Track.*)$/.test(c.name) ? "Transport" : c.name.replace(/ \d+$/, "");
    (groups[g] = groups[g] || []).push(c); });
  const grid = $("mgrid"); grid.replaceChildren();
  Object.entries(groups).forEach(([g, cs]) => {
    const p = el("div", { className: "page" }, el("h3", { textContent: g.toUpperCase() }, el("span", { textContent: cs[0].kind === "pad" ? `notes, ch ${scene.padch}` : `CC, ch ${scene.ch}` })));
    cs.forEach(c => {
      const cur = map[c.name] || ["", null], id = `m-${mdev}-${c.name.replace(/\W/g, "")}`;
      const act = el("select", { id }); ACTS.forEach(([v, t]) => act.add(new Option(t, v))); act.value = cur[0];
      const set = (a, arg) => { if (a) map[c.name] = [a, arg]; else delete map[c.name]; mstore(); midiFile(); };
      act.onchange = () => { const a = act.value, ac = argControl(a, null, () => {}, "x"); set(a, ac ? (a === "param" ? ac.value : +ac.value) : null); midiRender(); };
      const row = el("div", { className: "knob", style: "grid-template-columns:100px 1fr" },
        el("label", { className: "nm", htmlFor: id, textContent: `${c.name.replace(/^(Knob|Slider|Pad) /, "")} · ${c.num}`, title: `${c.name}: ${c.kind === "pad" ? "note" : "CC"} ${c.num}` }), act);
      p.append(row);
      const ac = argControl(cur[0], cur[1], v => set(cur[0], v), id + "-arg");
      if (ac) { ac.style.gridColumn = "2"; p.append(el("div", { className: "knob", style: "grid-template-columns:100px 1fr" }, el("span", { className: "nm" }), ac)); }
    });
    grid.append(p);
  });
  midiFile();
}
function midiFile() {
  const out = ["comment your profile (Amble Lite Editor): the KORGs with the Amble Lite sets;"];
  Object.entries(MD.devices).forEach(([k, dev]) => dev.scenes.forEach((scene, si) => {
    if (k === "nanokey") out.push("chcc 1 1 breath;");
    dev.controls.forEach(c => {
      const m = mmap[k][si][c.name]; if (!m || !m[0]) return;
      const tail = m[1] !== null && m[1] !== undefined ? ` ${m[1]}` : "";
      out.push(c.kind === "pad" ? `note ${scene.padch} ${c.num} ${m[0]}${tail};` : `chcc ${scene.ch} ${c.num} ${m[0]}${tail};`);
    });
  }));
  $("outm").value = out.join("\n") + "\n";
}
$("mdev").onchange = () => { mdev = $("mdev").value; mscene = 0; midiRender(); };
$("mscene").onchange = () => { mscene = +$("mscene").value; midiRender(); };
$("mreset").onclick = () => { mmap = fresh(); mstore(); midiRender(); };
$("cpm").onclick = () => copy($("outm").value, $("outm"), "Copied user.txt.");
$("dlm").onclick = () => download($("outm").value, "user.txt");
midiRender();

if (!restore()) { lib.pieces[0] = C.defaults("piece"); example = true; }
render();
</script>
"""


def main(out=OUT):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(PAGE.replace("__DATA__", json.dumps(data(), separators=(",", ":"))).replace("__CORE__", CORE))
    return out


if __name__ == "__main__":
    print(main())
