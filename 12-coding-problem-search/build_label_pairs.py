"""Stage 2 of the pattern-match labelling sample: build the blind pair sheets.

Equal-depth pooling (TREC style, user decision 2026-11-18): for each sampled title (label_sample/sample.jsonl)
take one representative FastPrep record (first query_id present in queries_all.jsonl) and pool the top-K
neighbours of EVERY compared model, so each model is later scored on its own top-K. The 813 TACO copies of
LeetCode problems are excluded from the candidates.

Sheets are blind: pair ids are hashed, pairs are shuffled, no model name, rank or score. The key file
(models, ranks, scores per pair) is written separately and must not be shown to judges.

Usage: python3 -I build_label_pairs.py <xref_dir> <model> [<model> ...] [--k 5]
"""
import hashlib, json, random, sys
import numpy as np

args = sys.argv[1:]
K = 5
if "--k" in args:
    i = args.index("--k"); K = int(args[i + 1]); del args[i:i + 2]
X, models = args[0], args[1:]
SALT = "fastprep-pattern-pairs-2026-11-16"

docs = [json.loads(l) for l in open(f"{X}/docs_v2.jsonl")]
qall = [json.loads(l) for l in open(f"{X}/queries_all.jsonl")]
row = {q["query_id"]: i for i, q in enumerate(qall)}
sample = [json.loads(l) for l in open(f"{X}/label_sample/sample.jsonl")]
excl = set(json.load(open(f"{X}/taco_leetcode_style.json"))["doc_ids"])   # TACO copies of LeetCode problems
keep = np.array([d["doc_id"] not in excl for d in docs])

items = []
for u in sample:
    qid = next((q for q in u["query_ids"] if q in row), None)
    if qid: items.append((u, qid, row[qid]))
qi = np.array([r for _, _, r in items])

pool = {i: {} for i in range(len(items))}
for model in models:   # one model's vectors in memory at a time
    D = np.load(f"{X}/emb/{model}/docs.npy").astype(np.float32)
    Q = np.load(f"{X}/emb/{model}/queries_all.npy")[qi].astype(np.float32)
    s = Q @ D.T; s[:, ~keep] = -np.inf
    idx = np.argsort(-s, axis=1)[:, :K]; sc = np.take_along_axis(s, idx, axis=1)
    for i in range(len(items)):
        for rank, (d, v) in enumerate(zip(idx[i], sc[i]), 1):
            pool[i].setdefault(int(d), []).append({"model": model, "rank": rank, "score": round(float(v), 5)})
    del D, Q, s

pairs, key = [], []
for i, (u, qid, r) in enumerate(items):
    for d, hits in pool[i].items():
        pid = hashlib.sha256(f"{SALT}|{qid}|{docs[d]['doc_id']}".encode()).hexdigest()[:12]
        pairs.append({"pair_id": pid, "problem_a": qall[r]["text"], "problem_b": docs[d]["text"]})
        key.append({"pair_id": pid, "split": u["split"], "title_norm": u["title_norm"], "query_id": qid,
                    "doc_id": docs[d]["doc_id"], "doc_source": docs[d]["source"], "hits": hits})
random.Random(SALT).shuffle(pairs)
with open(f"{X}/label_sample/pairs_blind.jsonl", "w") as fh:
    for p in pairs: fh.write(json.dumps(p) + "\n")
with open(f"{X}/label_sample/pairs_key.jsonl", "w") as fh:
    for k in key: fh.write(json.dumps(k) + "\n")
json.dump({"models": models, "k": K, "problems": len(items), "pairs": len(pairs)},
          open(f"{X}/label_sample/pairs_plan.json", "w"), indent=2)
print("models", models, "k", K, "| problems", len(items), "of", len(sample), "| pairs", len(pairs))
