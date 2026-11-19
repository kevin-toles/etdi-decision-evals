"""Tie each Alishohadaee/leetcode-problems-dataset statement (no title/slug) to its LeetCode problem.

Evidence per candidate problem = its title (kaysss/leetcode-problem-set) + statement keywords from the
doocs/leetcode README_EN extraction. TF-IDF cosine between statement and each problem profile; take the
best match and its margin over the runner-up. Independent check: the dataset's rows are ordered by
problem number, so correctly matched ids should increase with row index. TF-IDF only, no LLM.
Usage: python3 -I align_leetcode_statements.py <doocs_extractions_dir> <out_jsonl>
"""
import glob, json, os, re, sys
from datasets import Dataset
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

EXT, OUT = sys.argv[1], sys.argv[2]
H = os.path.expanduser("~/.cache/huggingface/datasets")
A = Dataset.from_file(glob.glob(H + "/Alishohadaee___leetcode-problems-dataset/**/*.arrow", recursive=True)[0])
K = Dataset.from_file(glob.glob(H + "/kaysss___leetcode-problem-set/**/*.arrow", recursive=True)[0])
probs = {int(r["frontendQuestionId"]): {"id": int(r["frontendQuestionId"]), "title": r["title"],
         "slug": r["titleSlug"], "tags": r["topicTags"], "paid": r["paidOnly"], "kw": ""} for r in K}
for f in glob.glob(EXT + "/solution_*_README_EN.md.json"):
    m = re.search(r"_(\d{4})\.", os.path.basename(f))
    if m and int(m.group(1)) in probs:
        d = json.load(open(f))
        probs[int(m.group(1))]["kw"] = " ".join(k["term"] for k in d.get("keywords", []))
ids = sorted(probs)
profile = [(" ".join([probs[i]["title"]] * 3) + " " + probs[i]["kw"]) for i in ids]

# strip the paraphrased lead-in ("I have a programming problem that goes like this: '")
stmts = [re.sub(r"^.{0,140}?:\s*'", "", q, count=1, flags=re.S) for q in A["user_queries"]]
vec = TfidfVectorizer(sublinear_tf=True, stop_words="english", ngram_range=(1, 2), min_df=1)
vec.fit(profile + stmts)
P, S = vec.transform(profile), vec.transform(stmts)
sim = (S @ P.T).toarray()
top2 = np.argsort(-sim, axis=1)[:, :2]
rows = []
for i, (a, b) in enumerate(top2):
    rows.append({"row": i, "id": ids[a], "slug": probs[ids[a]]["slug"], "title": probs[ids[a]]["title"],
                 "score": round(float(sim[i, a]), 4), "margin": round(float(sim[i, a] - sim[i, b]), 4),
                 "has_kw": bool(probs[ids[a]]["kw"])})
# order check: a matched id is "in order" if it lies between its neighbours' matched ids
for i, r in enumerate(rows):
    lo = rows[i - 1]["id"] if i else 0
    hi = rows[i + 1]["id"] if i + 1 < len(rows) else 10**9
    r["in_order"] = lo < r["id"] < hi
with open(OUT, "w") as fh:
    for r in rows: fh.write(json.dumps(r) + "\n")
n = len(rows); io = sum(r["in_order"] for r in rows)
print(f"rows {n}; in order {io} ({io/n:.1%}); distinct ids {len({r['id'] for r in rows})}; "
      f"profiles with keywords {sum(bool(probs[i]['kw']) for i in ids)}/{len(ids)}")
for lo, hi in ((0, .05), (.05, .1), (.1, .2), (.2, 9)):
    sel = [r for r in rows if lo <= r["margin"] < hi]
    if sel: print(f"margin [{lo},{hi}): {len(sel)} rows, in order {sum(r['in_order'] for r in sel)/len(sel):.1%}")
