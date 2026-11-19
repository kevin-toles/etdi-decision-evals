"""Stage 1 of the pattern-match labelling sample: choose the problems and fix the splits.

Model-independent, so it can run before the embedder is chosen and cannot be tuned to any model.

Unit = distinct normalised FastPrep title (the same problem is listed under several companies; all of a
title's records stay together so no problem lands on both sides of a split).

  unmatched population = FastPrep coding titles that are not a LeetCode problem title
  sample               = stratified by difficulty (proportional), ordered by sha256(salt + title)
  split                = 'measure' (never trained on; gives the measured match share) or 'train'
  gold split           = the exact-match titles (embedder test set) split 'select' / 'holdout'.
                         All of them serve model selection now; only 'select' may ever be trained on,
                         'holdout' is kept for judging a fine-tune.

Usage: python3 -I draw_label_sample.py <guidelines_etl_data_dir> <out_dir> [n_measure] [n_train]
"""
import collections, glob, hashlib, json, os, re, sys

B, OUT = sys.argv[1], sys.argv[2]
N_MEASURE = int(sys.argv[3]) if len(sys.argv) > 3 else 400   # +/-4.9 pts at 95% for a share near 50%
N_TRAIN = int(sys.argv[4]) if len(sys.argv) > 4 else 200
SALT = "fastprep-pattern-sample-2026-11-16"
norm = lambda s: re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
h = lambda s: hashlib.sha256((SALT + s).encode()).hexdigest()

aligned = {json.loads(l)["slug"] for l in open(f"{B}/data/Fastprep_public/xref/leetcode_statements_aligned.jsonl")
           if json.loads(l)["status"] != "unmatched"}
from datasets import Dataset
H = os.path.expanduser("~/.cache/huggingface/datasets")
K = Dataset.from_file(glob.glob(H + "/kaysss___leetcode-problem-set/**/*.arrow", recursive=True)[0])
lc_titles = {norm(r["title"]) for r in K} | {r["titleSlug"] for r in K}

groups = collections.defaultdict(list)
for f in sorted(glob.glob(f"{B}/data/Fastprep_public/records/problems__*.json")):
    p = json.load(open(f))["record"]
    t = norm(p.get("title"))
    if t: groups[t].append(p)

def summary(t, recs):
    diff = collections.Counter(r.get("difficulty") or "unknown" for r in recs).most_common(1)[0][0]
    return {"title_norm": t, "query_ids": sorted(r["id"] for r in recs), "difficulty": diff,
            "problem_types": sorted({r.get("problemType") or "unknown" for r in recs}),
            "topics": sorted({x for r in recs for x in (r.get("topics") or [])})}

unmatched = [summary(t, r) for t, r in groups.items() if t not in lc_titles]
strata = collections.defaultdict(list)
for u in unmatched: strata[u["difficulty"]].append(u)
for s in strata.values(): s.sort(key=lambda u: h(u["title_norm"]))

def take(n, offset_by):  # proportional allocation, largest-remainder rounding
    tot = len(unmatched); raw = {k: n * len(v) / tot for k, v in strata.items()}
    alloc = {k: int(x) for k, x in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - alloc[k], reverse=True)[: n - sum(alloc.values())]: alloc[k] += 1
    return {k: strata[k][offset_by.get(k, 0): offset_by.get(k, 0) + a] for k, a in alloc.items()}, alloc

m, am = take(N_MEASURE, {})
t, at = take(N_TRAIN, am)
sample = [{**u, "split": "measure"} for v in m.values() for u in v] + [{**u, "split": "train"} for v in t.values() for u in v]

gold = sorted({t for t in groups if t in aligned})
gold_split = [{"title_norm": g, "query_ids": sorted(r["id"] for r in groups[g]),
               "split": "select" if int(h("gold:" + g), 16) % 2 == 0 else "holdout"} for g in gold]

os.makedirs(OUT, exist_ok=True)
for name, rows in (("sample", sample), ("gold_split", gold_split)):
    with open(f"{OUT}/{name}.jsonl", "w") as fh:
        for r in rows: fh.write(json.dumps(r) + "\n")
plan = {"salt": SALT, "unit": "distinct normalised FastPrep title", "population_unmatched_titles": len(unmatched),
        "strata_population": {k: len(v) for k, v in strata.items()},
        "measure_alloc": am, "train_alloc": at,
        "gold_titles": len(gold), "gold_split": dict(collections.Counter(g["split"] for g in gold_split)),
        "gold_records": dict(collections.Counter(g["split"] for g in gold_split for _ in g["query_ids"]))}
json.dump(plan, open(f"{OUT}/sample_plan.json", "w"), indent=2)
print(json.dumps(plan, indent=2))
