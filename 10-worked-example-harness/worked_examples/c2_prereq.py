"""C2 (#6) worked example: PREREQUISITE_OF edges as ai-platform-data/scripts/seeding/concept_highway/
prerequisite_builder.py derives them — concept A → B when A is among chapter i's keywords and B among chapter i+1's in
the same book; hubword filter (source in > 20% of books), at least 2 books, PMI ≥ 0, at most 25 targets per source by
PMI — replayed on 3,000 random enriched SE books (seed 1112). Approximations: the concept vocabulary is the enriched
chapters' own concept terms (the builder reads Neo4j Concept nodes, empty since the cutover); no garbage-pattern or
tier filter. Then the paths a guideline traversal from one concept would follow at depth 1, 2, 3. Read-only.
    python3 -I <this> <start concept> <out.json>"""
import json, math, os, random, sys
from collections import defaultdict
EN = "<CORPUS_ROOT>/collections/software-engineering/enriched"
START, OUT = sys.argv[1].lower(), sys.argv[2]
fs = sorted(os.listdir(EN)); random.seed(1112); s = random.sample(fs, 3000)
books = {}
vocab = set()
for f in s:
    try: d = json.load(open(f"{EN}/{f}"))
    except Exception: continue
    chs = []
    for ch in d.get("chapters") or []:
        kws = [k["term"].lower().strip() for k in ch.get("keywords") or [] if k.get("term")]
        vocab.update(c["term"].lower().strip() for c in ch.get("concepts") or [] if len(c.get("term", "")) >= 4)
        chs.append((ch.get("start_page") or 0, kws))
    books[f[:-14]] = [k for _, k in sorted(chs)]
pairs = defaultdict(set); presence = defaultdict(set)
for b, chs in books.items():
    sets = [{k for k in kws if k in vocab} for kws in chs]
    for cs in sets:
        for c in cs: presence[c].add(b)
    for i in range(len(sets) - 1):
        for a in sets[i]:
            for c in sets[i + 1]:
                if a != c and len(pairs[(a, c)]) < 5: pairs[(a, c)].add(b)
N = len(books); hub = int(0.20 * N)
by_src = defaultdict(list)
for (a, c), bs in pairs.items():
    if len(presence[a]) > hub or len(bs) < 2: continue
    pmi = math.log2((len(bs) / N) / ((len(presence[a]) / N) * (len(presence[c]) / N)))
    if pmi < 0: continue
    by_src[a].append((pmi, c, len(bs)))
edges = {a: [(c, round(p, 2), n) for p, c, n in sorted(v, reverse=True)[:25]] for a, v in by_src.items()}
levels = [[(START,)]]
for depth in range(3):
    nxt = []
    for path in levels[-1]:
        for c, p, n in edges.get(path[-1], []):
            if c not in path: nxt.append(path + (c,))
    levels.append(nxt)
out = {"books": N, "vocab": len(vocab), "edges_total": sum(len(v) for v in edges.values()), "start": START,
       "start_presence_books": len(presence[START]), "depth1": edges.get(START, []),
       "paths": {d: len(levels[d]) for d in (1, 2, 3)}, "sample_paths": {d: [" → ".join(p) for p in levels[d][:40]] for d in (1, 2, 3)}}
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps({k: out[k] for k in ("books", "vocab", "edges_total", "start_presence_books", "paths")}))
print("depth1:", out["depth1"]); import collections; print("top sources:", sorted(((len(v), a) for a, v in edges.items()), reverse=True)[:30]); print("consensus-ish:", [a for a in edges if "consens" in a or "replic" in a or "partition" in a or "raft" in a or "paxos" in a])
for d in (2, 3): print(d, out["sample_paths"][d][:15])
