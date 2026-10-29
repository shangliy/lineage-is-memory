import json,glob,statistics as st,sys
def M(x): return st.mean(x) if x else float('nan')
for t in ["labels","dates","routing","replies","scone"]:
  out={}
  for row in ["seed","parent"]:
    shown_n=[];ret=[];newfix=[];pairs=0
    for f in glob.glob(f"{t}/{row}-full-first-*.jsonl"):
      C={}
      for l in open(f):
        e=json.loads(l)
        if e["event"]=="candidate" and e.get("evaluation") and e["evaluation"].get("instance_scores"): C[e["id"]]=e
      if not C: continue
      shown=set()
      for c in C.values():
        p=C.get(c["parent_id"])
        if not p: continue
        pairs+=1
        ps=p["evaluation"]["instance_scores"]; cs=c["evaluation"]["instance_scores"]
        fails=[k for k in sorted(ps) if ps[k]<1][:4]; shown|=set(fails)
        ok=[k for k in ps if ps[k]>=1]
        if ok: ret.append(sum(cs.get(k,0)>=1 for k in ok)/len(ok))
        if fails: newfix.append(sum(cs.get(k,0)>=1 for k in fails)/len(fails))
      shown_n.append(len(shown)/len(next(iter(C.values()))["evaluation"]["instance_scores"]))
    out[row]=(M(shown_n),M(ret),M(newfix),pairs)
  print(t, " | ".join(f"{r}: shown-union {a:.2f}, retention {b:.2f}, shown-fixed {c:.2f}, pairs {d}" for r,(a,b,c,d) in out.items()))
