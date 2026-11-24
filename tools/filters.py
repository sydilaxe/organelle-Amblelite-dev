"""Each layer's filter coefficients: a 2-pole resonant low-pass (RBJ cookbook) for the voices' [biquad~]s, computed
when Cutoff or Reso move - Cutoff glides in 5 ms steps (no zipper noise) - and sent on [s al-<layer>-bq].
Cutoff 20 Hz .. 20 kHz (exponential); fully open = a true bypass. Reso: Q 0.707 (no peak) .. 16."""
from pdlib import Canvas
import model as M


def build(c):
    sr = c.ch(c.recv("al-init"), "t b", "samplerate~", "v alsr")
    for L in M.LAYERS:
        cut, res = M.S(L, None, "Cutoff"), M.S(L, None, "Reso")
        ln = c.ch(c.recv(f"al-s{cut}"), "pack f 25", "line 0 5")
        e = c.obj("expr if($f1 >= 0.985, 0, 6.28319*20*pow(1000, $f1)/max(alsr, 1)); "
                  f"0.7071 + 15*alpe[{res}]*alpe[{res}]; $f1 >= 0.985")
        c.c(ln, 0, e, 0)
        c.c(c.ch(c.recv(f"al-s{res}"), "t b", f"expr alpe[{cut}]"), 0, e, 0)
        pk = c.obj("pack f f f")
        for i in (2, 1, 0):
            c.c(e, i, pk, i)
        co = c.obj("expr if($f3, 0, 2*cos($f1)/(1 + sin($f1)/(2*$f2))); "
                   "if($f3, 0, -(1 - sin($f1)/(2*$f2))/(1 + sin($f1)/(2*$f2))); "
                   "if($f3, 1, (1 - cos($f1))/2/(1 + sin($f1)/(2*$f2))); "
                   "if($f3, 0, (1 - cos($f1))/(1 + sin($f1)/(2*$f2))); "
                   "if($f3, 0, (1 - cos($f1))/2/(1 + sin($f1)/(2*$f2)))")
        up = c.to(pk, "t l")
        c.c(up, 0, co, 0)
        out = c.obj("pack f f f f f")
        for i in (4, 3, 2, 1, 0):
            c.c(co, i, out, i)
        c.c(out, 0, c.obj(f"s al-{L}-bq"), 0)
        c.col(260)
