"""Render the OLED screens (an offline Pd run replayed by oledemu):  python3 shots.py [outdir]  (default
../docs/shots). The emulator's font only approximates the Organelle's; the layout and what is drawn are the patch's."""
import os
import sys
from PIL import Image
from harness import run
import model as M
import oledemu

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "shots")


def snap(c):
    c.c(c.obj("r h-snap", 900, 700), 0, c.obj("print SNAP", 900, 730), 0)


def tap(t, key):
    return [(t, f"notesRaw {key} 100"), (t + 50, f"notesRaw {key} 0")]


def main():
    os.makedirs(OUT, exist_ok=True)
    S = M.S
    ev = [(10, f"al-set {S('pad', None, 'Engine')} {M.engine_value('pad', 'wave')}"), (11, f"al-set {S('pad', 'wave', 'Table')} {(2 + 0.5) / 7}"),
          (12, f"al-set {S('pad', None, 'Gate')} 0.5"), (13, f"al-set {S('perc1', None, 'Rate')} {(3 + 0.5) / 6}")]
    ev += [(20, f"al-inset {M.LAYERS.index('perc3')} 1")]
    ev += tap(200, 72)                                            # start
    ev += [(3000, "h-snap 1-play")]
    # the drone's pages: held low C, then a knob turned
    ev += [(4000, "notesRaw 60 100"), (4600, "notesRaw 60 0"), (5000, "h-snap 2-layer-fav")]
    ev += [(5200, "knob1 0.2"), (5300, "knob1 0.5"), (5400, "knob1 0.75"), (5600, "h-snap 3-layer-knob")]
    # the pads' LFO 1 page, its target set to the wavetable's position
    ev += [(7000, "notesRaw 64 100"), (7600, "notesRaw 64 0")] + sum((tap(8000 + 120 * i, 70) for i in range(10)), [])
    ev += [(9500, f"al-set {S('pad', None, 'L1Tgt')} {(14 + 0.5) / M.MAXC}"), (9600, f"al-set {S('pad', None, 'L1Dep')} 0.6"),
           (9800, "h-snap 4-layer-lfo")]
    ev += tap(11000, 61) + [(11500, "h-snap 5-play-again")]
    ev += [(11800, f"al-inset {M.LAYERS.index('cloud')} 1")] + tap(12000, 63) + [(13500, "h-snap 6-mix")]
    ev += tap(14000, 66) + [(15000, "h-snap 7-pattern")]
    ev += tap(16000, 61) + tap(16200, 68) + tap(16500, 68) + [(17000, "h-snap 8-story")]
    ev += tap(18000, 61) + [(18200, "notesRaw 82 100"), (18300, "aux 1"), (18400, "notesRaw 62 100"),
                            (18450, "notesRaw 62 0"), (18500, "aux 0"), (18600, "notesRaw 82 0"), (18800, "h-snap 9-toast")]
    # the roadmap view: built (aux + top C#), auto, then low F# twice
    ev += [(19000, f"al-set {S('g', None, 'Road')} 0.9"), (19100, "aux 1"), (19200, "notesRaw 81 100"),
           (19250, "notesRaw 81 0"), (19300, "aux 0")] + tap(21000, 66) + tap(21200, 66) + [(23000, "h-snap 10-roadmap")]
    log, _ = run(ev, 24, prints=("oscOut",), extra=snap)
    saved = oledemu.render(log, OUT)
    # a contact sheet
    ims = [Image.open(p) for p in saved]
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * 3 + 40, ((len(ims) + 2) // 3) * (h + 20) + 20), (40, 44, 52))
    for i, im in enumerate(ims):
        sheet.paste(im, (10 + (i % 3) * (w + 10), 10 + (i // 3) * (h + 20)))
    sheet.save(os.path.join(OUT, "sheet.png"))
    print("\n".join(saved + [os.path.join(OUT, "sheet.png")]))


if __name__ == "__main__":
    main()
