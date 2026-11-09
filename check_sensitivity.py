"""Bounded re-check of loop_vs_graph.py's sensitivity ranking.
Uses the script's OWN function definitions (exec of the prefix before the
print section) so nothing is re-implemented. Original file is not modified."""
import math, statistics
src = open('loop_vs_graph.py').read()
prefix = src.split("P0 = Params()")[0]
ns = {}
exec(prefix, ns)
Params, replace, measure, rates = ns['Params'], ns['replace'], ns['measure'], ns['rates']

P0 = Params()
T = 8000

def adv(P, trials=T):
    m = measure(P, trials); return (m['loop'] - m['graph']) * 100, m

print("A) Reproduce the script's own ranking at n=12 (should match the run):")
knobs=[("p_silent",dict(p_silent=0.01),dict(p_silent=0.08)),
       ("coverage",dict(coverage=0.70),dict(coverage=1.00)),
       ("guard",   dict(guard=0.30),   dict(guard=0.95)),
       ("n",       dict(n=4),          dict(n=30)),
       ("rot",     dict(rot=1.00),     dict(rot=0.70)),
       ("retries", dict(retries=0),    dict(retries=4))]
for name,lo,hi in knobs:
    a,_=adv(replace(P0,**lo)); b,_=adv(replace(P0,**hi))
    print(f"   {name:<9} {a:+6.0f} -> {b:+6.0f}   swing {abs(b-a):4.0f}")

print("\nB) Same knobs, but at several task lengths n (swing in pts):")
print("   knob      " + "".join(f"n={n:<6}" for n in (5,8,12,20,30,45)))
for name,lo,hi in knobs:
    if name=="n": continue
    row=[]
    for n in (5,8,12,20,30,45):
        a,_=adv(replace(P0,n=n,**lo)); b,_=adv(replace(P0,n=n,**hi))
        row.append(abs(b-a))
    print(f"   {name:<9} " + "".join(f"{v:5.0f}   " for v in row))

print("\nC) Context rot pushed much harder than the script tries (rot=0.5 => p_silent doubles per 30k tokens):")
for n in (12,20,30,45):
    base,_=adv(replace(P0,n=n,rot=1.0)); hard,_=adv(replace(P0,n=n,rot=0.5)); vhard,_=adv(replace(P0,n=n,rot=0.35))
    print(f"   n={n:<3} rot=1.0 {base:+6.0f} | rot=0.5 {hard:+6.0f} | rot=0.35 {vhard:+6.0f}   (swing 1.0->0.5 = {abs(hard-base):.0f}, 1.0->0.35 = {abs(vhard-base):.0f})")

print("\nD) What context length does the loop actually reach? (mean steps at finish -> ctx tokens, and p_silent there)")
for n in (5,12,20,30,45):
    _,m=adv(replace(P0,n=n))
    ctx = P0.S + m['lsteps']*P0.step
    s,c = rates(P0, ctx)
    print(f"   n={n:<3} mean loop steps {m['lsteps']:5.1f} -> ctx ~{ctx:,.0f} tok -> p_silent {s:.4f} (fresh {P0.p_silent})")

print("\nE) Normalised check: each knob moved by the SAME relative amount (x0.5 and x2 of default, clipped to valid range) at n=12:")
def clip(v, lo, hi): return max(lo, min(hi, v))
norm=[("p_silent", lambda f: dict(p_silent=clip(0.03*f,0.001,0.5))),
      ("p_caught", lambda f: dict(p_caught=clip(0.06*f,0.001,0.5))),
      ("coverage", lambda f: dict(coverage=clip(1-(0.10*f),0.0,1.0))),  # miss-rate x0.5 / x2
      ("guard",    lambda f: dict(guard=clip(1-(0.30*f),0.0,1.0))),     # leak-rate x0.5 / x2
      ("rot",      lambda f: dict(rot=clip(1-(0.15*f),0.01,1.0))),      # rot strength x0.5 / x2
      ("retries",  lambda f: dict(retries=int(round(2*f))))]
for name,fn in norm:
    a,_=adv(replace(P0,**fn(0.5))); b,_=adv(replace(P0,**fn(2.0)))
    print(f"   {name:<9} half {a:+6.0f}  double {b:+6.0f}   swing {abs(b-a):4.0f}   ({fn(0.5)} / {fn(2.0)})")

print("\nF) Silent-vs-caught: hold total error rate fixed at 9%, vary the VISIBLE share (n=12):")
for sil in (0.00,0.01,0.03,0.05,0.07,0.09):
    a,m=adv(replace(P0,p_silent=sil,p_caught=0.09-sil))
    print(f"   p_silent={sil:.2f} p_caught={0.09-sil:.2f}  loop {m['loop']*100:5.1f}%  graph {m['graph']*100:5.1f}%  (loop-graph {a:+5.0f})")
