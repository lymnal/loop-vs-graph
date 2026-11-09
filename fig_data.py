"""Figure data for the article, computed with loop_vs_graph.py's own functions (unmodified)."""
import csv
src = open('loop_vs_graph.py').read()
ns = {}; exec(src.split("P0 = Params()")[0], ns)
Params, replace, measure = ns['Params'], ns['replace'], ns['measure']
P0 = Params(); T = 20_000
with open('fig_panelA_visibility.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['silent_share','p_silent','p_caught','loop_success','graph_success'])
    for k in range(0, 11):
        share = k/10; ps = round(0.09*share, 4); pc = round(0.09 - ps, 4)
        m = measure(replace(P0, p_silent=ps, p_caught=pc), T)
        w.writerow([share, ps, pc, round(m['loop'],4), round(m['graph'],4)]); print('A', share, ps, pc, m['loop'], m['graph'])
with open('fig_panelB_length.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['n','loop_success','graph_success'])
    for n in (2,3,4,5,6,8,10,12,15,20,25,30,35,40,45):
        m = measure(replace(P0, n=n), T)
        w.writerow([n, round(m['loop'],4), round(m['graph'],4)]); print('B', n, m['loop'], m['graph'])
