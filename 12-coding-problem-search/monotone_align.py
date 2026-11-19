"""Refine the TF-IDF statement->problem matches with the row-order constraint.

The dataset's rows are ordered by problem number. Keep each row's top-K text matches, then pick the
maximum-total-similarity chain in which problem ids strictly increase with row index (each row matched at
most once; rows may be left unmatched). Weighted increasing-subsequence DP with a Fenwick tree for prefix max.
Status per row: confirmed (chain pick == best text match), order-resolved (chain pick is a lower-ranked
text match), unmatched (no candidate fits the order).
Usage: python3 -I monotone_align.py <doocs_extractions_dir> <out_jsonl> [K]
"""
import glob, json, os, re, sys
import numpy as np
from datasets import Dataset
from sklearn.feature_extraction.text import TfidfVectorizer

EXT, OUT = sys.argv[1], sys.argv[2]; TOPK = int(sys.argv[3]) if len(sys.argv) > 3 else 5
H = os.path.expanduser("~/.cache/huggingface/datasets")
A = Dataset.from_file(glob.glob(H + "/Alishohadaee___leetcode-problems-dataset/**/*.arrow", recursive=True)[0])
K = Dataset.from_file(glob.glob(H + "/kaysss___leetcode-problem-set/**/*.arrow", recursive=True)[0])
probs = {int(r["frontendQuestionId"]): {"title": r["title"], "slug": r["titleSlug"], "tags": r["topicTags"], "kw": ""} for r in K}
for f in glob.glob(EXT + "/solution_*_README_EN.md.json"):
    m = re.search(r"_(\d{4})\.", os.path.basename(f))
    if m and int(m.group(1)) in probs:
        probs[int(m.group(1))]["kw"] = " ".join(k["term"] for k in json.load(open(f)).get("keywords", []))
ids = sorted(probs)
profile = [" ".join([probs[i]["title"]] * 3) + " " + probs[i]["kw"] for i in ids]
stmts = [re.sub(r"^.{0,140}?:\s*'", "", q, count=1, flags=re.S) for q in A["user_queries"]]
vec = TfidfVectorizer(sublinear_tf=True, stop_words="english", ngram_range=(1, 2)).fit(profile + stmts)
sim = (vec.transform(stmts) @ vec.transform(profile).T).toarray()
cand = np.argsort(-sim, axis=1)[:, :TOPK]

M = len(ids)
tree_v = np.zeros(M + 1); tree_n = np.full(M + 1, -1, dtype=np.int64)
def query(j):                     # best (value, node) over columns < j  (1-based Fenwick on columns)
    v, nd = 0.0, -1
    while j > 0:
        if tree_v[j] > v: v, nd = tree_v[j], tree_n[j]
        j -= j & -j
    return v, nd
def update(j, v, nd):
    j += 1
    while j <= M:
        if v > tree_v[j]: tree_v[j], tree_n[j] = v, nd
        j += j & -j
nodes = []                        # (row, col, total, parent)
for i in range(len(stmts)):
    pend = []
    for c in cand[i]:
        best, par = query(int(c))
        pend.append((i, int(c), best + float(sim[i, c]), par))
    for nd in pend:               # update after the whole row so one row cannot chain to itself
        nodes.append(nd); update(nd[1], nd[2], len(nodes) - 1)
k = int(np.argmax([n[2] for n in nodes])); chain = {}
while k >= 0:
    r, c, _, k2 = nodes[k]; chain[r] = c; k = k2
rows = []
for i in range(len(stmts)):
    c = chain.get(i); top = int(cand[i][0])
    st = "unmatched" if c is None else ("confirmed" if c == top else "order-resolved")
    c = top if c is None else c
    rows.append({"row": i, "status": st, "id": ids[c], "slug": probs[ids[c]]["slug"], "title": probs[ids[c]]["title"],
                 "tags": probs[ids[c]]["tags"], "score": round(float(sim[i, c]), 4),
                 "rank": int(np.where(cand[i] == c)[0][0]) + 1 if c in cand[i] else None,
                 "statement": stmts[i]})
with open(OUT, "w") as fh:
    for r in rows: fh.write(json.dumps(r) + "\n")
from collections import Counter
print(Counter(r["status"] for r in rows), "distinct ids among matched",
      len({r["id"] for r in rows if r["status"] != "unmatched"}))
