#!/usr/bin/env python3
"""
loop_vs_graph.py -- structural tradeoff model: agentic LOOP vs engineered GRAPH.

NOT a model-quality benchmark. It measures what the control-flow TOPOLOGY alone
forces to be true, given the explicit assumptions in Params. Change them and the
conclusions move -- that is the point of writing it down.

Failure taxonomy (this is the crux):
  p_ok      step lands correctly
  p_caught  step fails VISIBLY (exception, test fail, schema violation) -> retryable
  p_silent  step is WRONG but looks fine  -> silently poisons everything downstream
A loop retries p_caught for free (it sees the error next turn) and is defenceless
against p_silent (it builds on the mistake). A graph converts some p_silent into
p_caught at every edge -- that is what a guard/validator/evaluator node buys you.
"""
import random, math
from dataclasses import dataclass, replace

SEED = 7

@dataclass
class Params:
    n: int   = 12          # units of real work the task requires
    S: int   = 2000        # system prompt + tool schemas, tokens
    step:int = 1500        # assistant reasoning + tool result per step, tokens
    out: int = 400
    node_sys_ratio: float = 0.6
    handoff_ratio: float  = 0.15
    state_window: int     = 3
    width: int            = 3
    # reliability, fresh context:
    p_caught: float = 0.06
    p_silent: float = 0.03
    rot: float      = 0.85   # at +30k tokens of context, p_silent inflates by 1/rot
    retries: int    = 2
    # graph-only:
    coverage: float = 0.90   # fraction of inputs an authored path anticipated
    guard: float    = 0.70   # fraction of silent errors an edge/validator catches
    branches: int   = 3

def rates(P, ctx_tokens):
    """Context rot: longer context -> more silent error, slightly more caught error."""
    infl = (1.0 / P.rot) ** (ctx_tokens / 30_000)
    s = min(0.9, P.p_silent * infl)
    c = min(0.9 - s, P.p_caught * (1 + 0.3 * (infl - 1)))
    return s, c

# ---------------------------------------------------------------- token cost
def loop_tokens(P, steps):
    raw = cached = fresh = 0
    for i in range(steps):
        ctx = P.S + i * P.step
        prev = P.S + max(0, i - 1) * P.step
        raw += ctx; cached += prev; fresh += ctx - prev
    return dict(raw=raw, cached=cached, fresh=fresh)

def graph_tokens(P, nodes):
    sysx, h = P.S * P.node_sys_ratio, P.step * P.handoff_ratio
    raw = sum(sysx + min(k, P.state_window) * h + h for k in range(nodes))
    return dict(raw=raw, cached=nodes * sysx, fresh=raw - nodes * sysx)

# ------------------------------------------------------------- reliability MC
def sim_loop(P, rng):
    done = steps = 0
    budget = P.n * 3
    traj = []
    while done < P.n and steps < budget:
        ctx = P.S + steps * P.step
        s, c = rates(P, ctx)
        traj.append(rng.randrange(P.branches))
        steps += 1
        r = rng.random()
        if r < s:                    # silent: looks like progress, is not
            done += 1
            return False, steps, tuple(traj)   # answer is now wrong; run is lost
        elif r < s + c:              # caught: burns a step, keeps its context
            continue
        else:
            done += 1
    return (done >= P.n), steps, tuple(traj)

def sim_graph(P, rng):
    if rng.random() > P.coverage:
        return False, 0, ("uncovered",)
    calls = 0
    for _ in range(P.n):
        for _attempt in range(P.retries + 1):
            calls += 1
            s, c = rates(P, 0)       # fresh context per node -> no rot
            r = rng.random()
            if r < s:
                if rng.random() < P.guard:   # edge validator catches it -> retry
                    continue
                return False, calls, ("silent-escaped",)
            elif r < s + c:
                continue
            break
        else:
            return False, calls, ("node-exhausted",)
    return True, calls, ("authored",)

def measure(P, trials=20_000):
    rng = random.Random(SEED); lw = ls = 0; lt = set()
    for _ in range(trials):
        ok, st, tr = sim_loop(P, rng); lw += ok; ls += st; lt.add(tr)
    rng = random.Random(SEED); gw = gc = 0; gt = set()
    for _ in range(trials):
        ok, cl, tr = sim_graph(P, rng); gw += ok; gc += cl; gt.add(tr)
    return dict(loop=lw/trials, graph=gw/trials, lsteps=ls/trials,
                gcalls=gc/trials, lpaths=len(lt), gpaths=len(gt))

def bar(x, w=20): k = int(round(max(0,min(1,x))*w)); return "#"*k + "."*(w-k)

P0 = Params(); T = 20_000
print("="*80)
print("ASSUMPTIONS  %d work units | %d tok/step | p_silent=%.2f p_caught=%.2f (fresh ctx)"
      % (P0.n, P0.step, P0.p_silent, P0.p_caught))
print("             graph: coverage=%.2f guard=%.2f retries=%d | rot: silent x%.2f per 30k tok"
      % (P0.coverage, P0.guard, P0.retries, 1/P0.rot))
print("="*80)

print("\n[1] TOKEN COST vs TASK LENGTH  (input tokens the model must read)")
print("    %-6s %14s %14s %8s %16s" % ("steps","loop raw","graph raw","ratio","loop, cached*"))
for n in (4,8,12,20,30,50,80):
    L,G = loop_tokens(P0,n), graph_tokens(P0,n)
    eff = L["cached"]*0.10 + L["fresh"]*1.25
    print("    %-6d %14s %14s %7.1fx %16s"
          % (n, f'{L["raw"]:,}', f'{G["raw"]:,.0f}', L["raw"]/G["raw"], f"{eff:,.0f}"))
print("    * price-weighted equivalent tokens, cache read ~0.1x / cache write ~1.25x.")
print("      Caching divides the CONSTANT. The n^2 GROWTH survives it untouched.")

print("\n[2] RELIABILITY vs TASK LENGTH   (end-to-end correct, %d trials)" % T)
print("    %-5s %-26s %-26s %s" % ("n","loop","graph","winner"))
for n in (2,3,5,8,12,20,30,45):
    m = measure(replace(P0,n=n), T)
    w = "LOOP " if m["loop"] > m["graph"]+.01 else ("GRAPH" if m["graph"] > m["loop"]+.01 else "tie")
    print("    %-5d %5.1f%% %-20s %5.1f%% %-20s %s"
          % (n, m["loop"]*100, bar(m["loop"]), m["graph"]*100, bar(m["graph"]), w))
print("    ^ THE CROSSOVER. Silent errors compound multiplicatively in a loop and the")
print("      growing context makes them likelier. A graph's per-node rate never grows.")

print("\n[3] WHERE THE CROSSOVER SITS  (task length at which graph overtakes loop)")
print("    %-12s %s" % ("coverage \\ guard", "  ".join("g=%.2f" % g for g in (0.3,0.5,0.7,0.9))))
for cov in (0.70,0.80,0.90,0.95,0.99):
    cells=[]
    for g in (0.3,0.5,0.7,0.9):
        xo="never"
        for n in range(2,61):
            m=measure(replace(P0,n=n,coverage=cov,guard=g), 4000)
            if m["graph"] > m["loop"]: xo="n>=%d"%n; break
        cells.append("%-7s"%xo)
    print("    %-12.2f    %s" % (cov, " ".join(cells)))
print("    ^ read this as: 'how good must my authored paths + guards be, and how long is")
print("      the task, before the graph is worth building?'  Top-left = stay in the loop.")

m = measure(P0, T)
print("\n[4] LATENCY  (serial round-trips on the critical path)")
print("    loop : %.1f steps, strictly serial -- step i is unknown until i-1 returns" % m["lsteps"])
for w in (1,2,3,5,8):
    d = math.ceil(P0.n/w)+1
    print("    graph: width %d -> depth %2d  =  %.1fx faster" % (w,d,m["lsteps"]/d))

print("\n[5] TRAJECTORY VARIANCE  (distinct execution paths, %d runs)" % T)
print("    loop : %6d distinct paths -- control flow is SAMPLED  => a distribution => eval it"
      % m["lpaths"])
print("    graph: %6d distinct paths -- control flow is CODE     => a value        => test it"
      % m["gpaths"])

print("\n[6] SENSITIVITY  (which assumption actually moves the decision?)")
base = measure(P0,T); d0 = base["loop"]-base["graph"]
knobs=[("p_silent",dict(p_silent=0.01),dict(p_silent=0.08)),
       ("coverage",dict(coverage=0.70),dict(coverage=1.00)),
       ("guard",   dict(guard=0.30),   dict(guard=0.95)),
       ("n",       dict(n=4),          dict(n=30)),
       ("rot",     dict(rot=1.00),     dict(rot=0.70)),
       ("retries", dict(retries=0),    dict(retries=4))]
rows=[]
for name,lo,hi in knobs:
    a=measure(replace(P0,**lo),8000); b=measure(replace(P0,**hi),8000)
    da,db=a["loop"]-a["graph"], b["loop"]-b["graph"]
    rows.append((abs(db-da),name,list(lo.values())[0],list(hi.values())[0],da,db))
print("    %-10s %-8s %-8s %s" % ("knob","low","high","(loop - graph) advantage, pts"))
for sw,name,lo,hi,da,db in sorted(rows,reverse=True):
    print("    %-10s %-8s %-8s %+5.0f  ->  %+5.0f      swing %3.0f" % (name,lo,hi,da*100,db*100,sw*100))
print("    baseline (loop - graph) = %+.0f pts" % (d0*100))
print()
