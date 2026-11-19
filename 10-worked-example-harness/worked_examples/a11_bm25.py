"""A11 (USS-OQ-10) worked example: what a keyword (BM25) search ranks first for "RAG chunking strategies" under each
option's token stream — (c) as typed [rag, chunking, strategies]; (b) today's filter if switched on, which REPLACES
"rag" with the first word of its expansion [retrieval, chunking, strategies] (uss-analysis/src/token_filter.rs:85);
(a) every word [retrieval, augmented, generation, chunking, strategies]. Corpus: every chapter of 4,000 random SE books
(seed 1112) mentioning "retrieval" or "RAG". BM25 k1 1.2, b 0.75 over lowercased word tokens. Read-only.
    python3 -I <this> <out.json>"""
import json, math, os, random, re, sys
from collections import Counter
ROOT = "<CORPUS_ROOT>/collections/software-engineering/raw"
files = sorted(e.path for e in os.scandir(ROOT) if e.name.endswith(".json")); random.seed(1112); sample = random.sample(files, 4000)
TOK = re.compile(r"[a-z0-9]+")
docs = []
for p in sample:
    try: d = json.load(open(p))
    except Exception: continue
    pages = {}
    for pg in d.get("pages") or []:
        try: pages[int(pg.get("page_number"))] = pg.get("text") or ""
        except Exception: pass
    for c in d.get("chapters") or [{"title": "(whole)", "start_page": min(pages or [0]), "end_page": max(pages or [0])}]:
        s, e = c.get("start_page") or 0, c.get("end_page") or 0
        t = "\n".join(pages.get(i, "") for i in range(s, e + 1))
        if not t or len(t) > 600_000: continue
        low = t.lower()
        if "retrieval" not in low and not re.search(r"\brag\b", low): continue
        tf = Counter(TOK.findall(low))
        docs.append({"book": os.path.basename(p)[:-5], "chapter": (c.get("title") or "")[:60], "pages": f"{s}-{e}", "tf": tf, "len": sum(tf.values())})
N = len(docs); avg = sum(d["len"] for d in docs) / max(1, N)
df = Counter(w for d in docs for w in set(d["tf"]))
def bm25(q, d):
    return sum(math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5)) * d["tf"][w] * 2.2 / (d["tf"][w] + 1.2 * (0.25 + 0.75 * d["len"] / avg)) for w in q if d["tf"][w])
Q = {"c_as_typed": ["rag", "chunking", "strategies"], "b_first_word": ["retrieval", "chunking", "strategies"],
     "a_every_word": ["retrieval", "augmented", "generation", "chunking", "strategies"]}
out = {"chapters": N, "books_scanned": 4000, "df": {w: df[w] for w in {x for q in Q.values() for x in q}}, "top": {}}
for k, q in Q.items():
    sc = sorted(((bm25(q, d), d) for d in docs), key=lambda x: -x[0])[:10]
    out["top"][k] = [{"score": round(s, 2), "book": d["book"], "chapter": d["chapter"], "pages": d["pages"],
                      "rag": d["tf"]["rag"], "retrieval": d["tf"]["retrieval"], "chunking": d["tf"]["chunking"]} for s, d in sc]
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(N, out["df"])
for k, v in out["top"].items():
    print("==", k)
    for r in v[:8]: print(f"  {r['score']:6.2f} rag={r['rag']:3d} retr={r['retrieval']:3d} chunk={r['chunking']:3d} | {r['book'][:70]} | {r['chapter'][:30]}")
