"""Render the article figure as SVG from the two CSVs. No plotting library needed."""
import csv
A = list(csv.DictReader(open('fig_panelA_visibility.csv')))
B = list(csv.DictReader(open('fig_panelB_length.csv')))

# palette (validated): surface, inks, gridline, baseline, series
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
LOOP, GRAPH = "#2a78d6", "#eb6834"
W, H = 1200, 600
FONT = "font-family='-apple-system, Helvetica Neue, Helvetica, Arial, sans-serif'"

def panel(x0, y0, w, h, xs, ys_loop, ys_graph, xlabel, xticks, xfmt, title, note, label_dx):
    px, py, pw, ph = x0+56, y0+58, w-56-24, h-58-58
    xmin, xmax = min(xs), max(xs)
    def X(v): return px + (v-xmin)/(xmax-xmin)*pw
    def Y(v): return py + (1-v)*ph
    s = []
    s.append(f"<text x='{x0}' y='{y0+18}' fill='{INK}' font-size='17' font-weight='600' {FONT}>{title}</text>")
    s.append(f"<text x='{x0}' y='{y0+38}' fill='{INK2}' font-size='12' {FONT}>{note}</text>")
    # grid + y ticks
    for t in (0,0.25,0.5,0.75,1.0):
        s.append(f"<line x1='{px}' x2='{px+pw}' y1='{Y(t):.1f}' y2='{Y(t):.1f}' stroke='{GRID}' stroke-width='1'/>")
        s.append(f"<text x='{px-8}' y='{Y(t)+4:.1f}' fill='{MUTED}' font-size='12' text-anchor='end' {FONT}>{int(t*100)}%</text>")
    s.append(f"<line x1='{px}' x2='{px+pw}' y1='{Y(0):.1f}' y2='{Y(0):.1f}' stroke='{AXIS}' stroke-width='1'/>")
    for t in xticks:
        s.append(f"<text x='{X(t):.1f}' y='{py+ph+18}' fill='{MUTED}' font-size='12' text-anchor='middle' {FONT}>{xfmt(t)}</text>")
    s.append(f"<text x='{px+pw/2:.1f}' y='{py+ph+40}' fill='{INK2}' font-size='13' text-anchor='middle' {FONT}>{xlabel}</text>")
    s.append(f"<text transform='translate({x0+14},{py+ph/2:.1f}) rotate(-90)' fill='{INK2}' font-size='13' text-anchor='middle' {FONT}>tasks completed correctly</text>")
    # lines
    for ys, col, shape in ((ys_graph, GRAPH, 'sq'), (ys_loop, LOOP, 'ci')):
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x,y in zip(xs, ys))
        s.append(f"<polyline points='{pts}' fill='none' stroke='{col}' stroke-width='2' stroke-linejoin='round'/>")
        for x,y in zip(xs, ys):
            if shape=='ci':
                s.append(f"<circle cx='{X(x):.1f}' cy='{Y(y):.1f}' r='4' fill='{col}' stroke='{SURF}' stroke-width='2'/>")
            else:
                s.append(f"<rect x='{X(x)-4:.1f}' y='{Y(y)-4:.1f}' width='8' height='8' fill='{col}' stroke='{SURF}' stroke-width='2'/>")
    # direct labels at line ends
    s.append(f"<text x='{X(xs[-1])+label_dx:.1f}' y='{Y(ys_loop[-1])+4:.1f}' fill='{INK}' font-size='13' font-weight='600' {FONT}>Loop {ys_loop[-1]*100:.0f}%</text>")
    s.append(f"<text x='{X(xs[-1])+label_dx:.1f}' y='{Y(ys_graph[-1])+4:.1f}' fill='{INK}' font-size='13' font-weight='600' {FONT}>Graph {ys_graph[-1]*100:.0f}%</text>")
    return "\n".join(s), X, Y

xsA = [float(r['silent_share']) for r in A]; lA=[float(r['loop_success']) for r in A]; gA=[float(r['graph_success']) for r in A]
xsB = [float(r['n']) for r in B];            lB=[float(r['loop_success']) for r in B]; gB=[float(r['graph_success']) for r in B]

out = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>",
       f"<rect width='{W}' height='{H}' fill='{SURF}'/>",
       f"<text x='24' y='30' fill='{INK}' font-size='20' font-weight='700' {FONT}>Loop vs graph: what decides it is whether errors are visible</text>",
       f"<text x='24' y='52' fill='{INK2}' font-size='13' {FONT}>Topology simulation, 20,000 runs per point. A loop retries errors it can see and builds on errors it cannot; a graph validates at each edge but only covers paths it anticipated.</text>"]
pA, XA, YA = panel(24, 78, 570, 470, xsA, lA, gA, "share of per-step errors that are silent (total per-step error rate held at 9%)",
                   [0,0.2,0.4,0.6,0.8,1.0], lambda t: f"{int(t*100)}%",
                   "A. Same error rate, different visibility (12-step task)", "Loop falls 100% → 30% as errors go all-visible → all-silent. Winner flips near 12.5%.", -74)
pB, XB, YB = panel(614, 78, 570, 470, xsB, lB, gB, "task length (units of real work)",
                   [2,5,10,15,20,25,30,35,40,45], lambda t: f"{int(t)}",
                   "B. Longer tasks favour the graph (model defaults)", "3% silent + 6% visible error per step; graph covers 90% of inputs, guards catch 70% of silent errors.", -74)
out += [pA, pB]
# crossover annotations
xa = 0.125; out.append(f"<line x1='{XA(xa):.1f}' x2='{XA(xa):.1f}' y1='{YA(1.0):.1f}' y2='{YA(0):.1f}' stroke='{AXIS}' stroke-width='1' stroke-dasharray='4 4'/>")
out.append(f"<text x='{XA(xa)+6:.1f}' y='{YA(0.08):.1f}' fill='{INK2}' font-size='12' {FONT}>← loop wins | graph wins →</text>")
xb = 4.6; out.append(f"<line x1='{XB(xb):.1f}' x2='{XB(xb):.1f}' y1='{YB(1.0):.1f}' y2='{YB(0):.1f}' stroke='{AXIS}' stroke-width='1' stroke-dasharray='4 4'/>")
out.append(f"<text x='{XB(xb)+6:.1f}' y='{YB(0.08):.1f}' fill='{INK2}' font-size='12' {FONT}>← loop | graph → (~5 steps)</text>")
# legend (bottom-left) + source line
ly = H-16
out.append(f"<circle cx='34' cy='{ly-4}' r='4' fill='{LOOP}' stroke='{SURF}' stroke-width='2'/><text x='44' y='{ly}' fill='{INK2}' font-size='12' {FONT}>Loop (model picks each next step from the transcript)</text>")
out.append(f"<rect x='366' y='{ly-8}' width='8' height='8' fill='{GRAPH}' stroke='{SURF}' stroke-width='2'/><text x='380' y='{ly}' fill='{INK2}' font-size='12' {FONT}>Graph (authored nodes and edges, validator at each edge)</text>")
out.append(f"<text x='{W-24}' y='{ly}' fill='{MUTED}' font-size='11' text-anchor='end' {FONT}>loop_vs_graph.py, seed 7 · simulation of control-flow topology, not a model benchmark</text>")
out.append("</svg>")
open('fig-loop-vs-graph.svg','w').write("\n".join(out))
print("wrote fig-loop-vs-graph.svg", len("\n".join(out)), "bytes")
