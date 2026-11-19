"""Re-score every model from saved embeddings (no model load). Adds a 'clean full pool' that drops the
813 TACO records which are LeetCode problems (LeetCode `class Solution` starter code), so a distractor is
never another copy of the gold problem. Writes scores_table.json and prints a table.
Usage: python3 -I rescore.py <xref_dir>
"""
import json, os, sys, glob, ast
import numpy as np
X = sys.argv[1]
L = lambda n: [json.loads(l) for l in open(f"{X}/{n}.jsonl")]
docs, qg, qa = L("docs_v2"), L("queries_gold"), L("queries_all")
drop = set(json.load(open(f"{X}/taco_leetcode_style.json"))["doc_ids"])
pos = {d["doc_id"]: i for i, d in enumerate(docs)}; idx = {q["query_id"]: i for i, q in enumerate(qa)}
src = np.array([d["source"] for d in docs]); keep = np.array([d["doc_id"] not in drop for d in docs])
gold = np.array([pos[q["gold"]] for q in qg]); qsel = [idx[q["query_id"]] for q in qg]
nt = lambda s: s.strip().lower().replace(" ", "_").replace("-", "_")
def tagset(t):
    if isinstance(t, str):
        try: t = ast.literal_eval(t)
        except Exception: t = [t]
    return {nt(x) for x in (t or [])}
lc_cols = np.where(src == "leetcode")[0]
lc_tags = [tagset(docs[i]["tags"]) for i in lc_cols]
def metr(S, cols):
    sub = S[:, cols]; gpos = {c: i for i, c in enumerate(cols)}
    g = sub[np.arange(len(gold)), [gpos[x] for x in gold]]
    r = (sub > g[:, None]).sum(1) + 1
    return {"top1": round(float((r == 1).mean()), 3), "top5": round(float((r <= 5).mean()), 3), "mrr": round(float((1 / r).mean()), 3)}
rows = []
for E in sorted(glob.glob(f"{X}/emb/*/queries_all.npy")):
    k = E.split("/")[-2]
    if not os.path.exists(f"{X}/emb/{k}/docs.npy"): continue
    Dv = np.load(f"{X}/emb/{k}/docs.npy").astype(np.float32); Qa = np.load(E).astype(np.float32)
    S = Qa[qsel] @ Dv.T
    t1 = (Qa @ Dv[lc_cols].T).argmax(1); jac = []
    for q, j in zip(qa, t1):
        a, b = {nt(x) for x in q["topics"]}, lc_tags[j]
        if a and b: jac.append(len(a & b) / len(a | b))
    rows.append({"model": k, "lc_pool": metr(S, lc_cols), "clean_full_pool": metr(S, np.where(keep)[0]),
                 "raw_full_pool": metr(S, np.arange(len(docs))), "tag_jaccard": round(float(np.mean(jac)), 3)})
rows.sort(key=lambda r: -r["clean_full_pool"]["mrr"])
json.dump({"n_gold": len(qg), "n_all": len(qa), "n_docs": int(len(docs)), "n_dropped": len(drop), "rows": rows},
          open(f"{X}/scores_table.json", "w"), indent=1)
print(f"gold queries {len(qg)}, all queries {len(qa)}, docs {len(docs)} (clean pool drops {len(drop)})")
print(f"{'model':16} | LC top1 top5  MRR | clean top1 top5  MRR | raw top1 | tagJ")
for r in rows:
    a, b, c = r["lc_pool"], r["clean_full_pool"], r["raw_full_pool"]
    print(f"{r['model']:16} | {a['top1']:.3f} {a['top5']:.3f} {a['mrr']:.3f} | {b['top1']:.3f} {b['top5']:.3f} {b['mrr']:.3f} | {c['top1']:.3f} | {r['tag_jaccard']:.3f}")
