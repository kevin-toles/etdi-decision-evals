"""Mix planted control pairs into the pooled blind pairs and cut grading sheets.

Planted controls (judges cannot tell them apart from real pairs: same text sources, same hashed ids, shuffled in):
  same     : every exact-match title in the gold 'select' split (never 'holdout'): its FastPrep statement (title
             removed, as in the queries) vs its aligned LeetCode statement -> expected grade 3.
  different: half as many 'select' titles, each paired with a random LeetCode statement sharing no topic tag
             with the true match -> expected grade 0 (1 tolerated by the gate, see agreement thresholds).
Sheets and keys are written on the SSD (FastPrep text never enters this repo).

Usage: python3 -I build_pair_sheets.py <xref_dir> [sheet_size]
"""
import ast, hashlib, json, os, random, sys

X = sys.argv[1]; SIZE = int(sys.argv[2]) if len(sys.argv) > 2 else 50
LS = f"{X}/label_sample"; SALT = "fastprep-pattern-pairs-2026-11-16"
rng = random.Random(SALT + "|planted")
docs = [json.loads(l) for l in open(f"{X}/docs_v2.jsonl")]
pos = {d["doc_id"]: d for d in docs}
qall = {q["query_id"]: q for q in (json.loads(l) for l in open(f"{X}/queries_all.jsonl"))}
gold = {q["query_id"]: q["gold"] for q in (json.loads(l) for l in open(f"{X}/queries_gold.jsonl"))}
select = [g for g in (json.loads(l) for l in open(f"{LS}/gold_split.jsonl")) if g["split"] == "select"]
tags = lambda d: set(ast.literal_eval(d["tags"]) if isinstance(d["tags"], str) else d["tags"] or [])
lc = [d for d in docs if d["source"] == "leetcode"]
pid = lambda a, b: hashlib.sha256(f"{SALT}|{a}|{b}".encode()).hexdigest()[:12]

items = [json.loads(l) for l in open(f"{LS}/pairs_blind.jsonl")]
seen = {p["pair_id"] for p in items}
planted = []
for g in select:
    qid = next(q for q in g["query_ids"] if q in gold)
    d = pos[gold[qid]]
    planted.append(("same", qid, d["doc_id"]))
for g in rng.sample(select, len(select) // 2):
    qid = next(q for q in g["query_ids"] if q in gold)
    t = tags(pos[gold[qid]])
    cand = [d for d in lc if not (tags(d) & t)]
    planted.append(("different", qid, rng.choice(cand)["doc_id"]))
pkey = []
for kind, qid, did in planted:
    i = pid(qid, did)
    if i in seen: continue          # already a real pooled pair: keep the real one only
    items.append({"pair_id": i, "problem_a": qall[qid]["text"], "problem_b": pos[did]["text"]})
    pkey.append({"pair_id": i, "planted": kind, "query_id": qid, "doc_id": did}); seen.add(i)
rng.shuffle(items)
os.makedirs(f"{LS}/sheets", exist_ok=True)
n = 0
for s in range(0, len(items), SIZE):
    chunk = items[s:s + SIZE]; n += 1
    json.dump({"sheet": f"pp-{n:04d}", "items": [{"item_id": p["pair_id"], "problem_a": p["problem_a"],
               "problem_b": p["problem_b"]} for p in chunk]}, open(f"{LS}/sheets/pp-{n:04d}.json", "w"))
with open(f"{LS}/planted_key.jsonl", "w") as fh:
    for k in pkey: fh.write(json.dumps(k) + "\n")
from collections import Counter
print("items", len(items), "| planted", Counter(k["planted"] for k in pkey), "| sheets", n, "of up to", SIZE)
