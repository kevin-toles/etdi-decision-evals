"""Embedder-comparison inputs, v2: real statements on both sides.
docs  = LeetCode statements tied to problem numbers (leetcode_statements_aligned.jsonl, unmatched rows dropped)
        + TACO + CodeContests full statements from `content` (harder distractors).
queries_gold = FastPrep coding problems whose title exactly matches an aligned LeetCode problem (gold = lc:<slug>).
queries_all  = every extracted FastPrep coding problem with a statement (for the tag-agreement check).
FastPrep titles are stripped from the query text. No LLM calls.
Usage: python3 -I build_inputs_v2.py <guidelines_etl_data_dir> <xref_dir>
"""
import glob, html, json, re, sys
B, X = sys.argv[1], sys.argv[2]
norm = lambda s: re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
detag = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
lc = [json.loads(l) for l in open(f"{X}/leetcode_statements_aligned.jsonl")]
lc = [r for r in lc if r["status"] != "unmatched"]
docs = [{"doc_id": f"lc:{r['slug']}", "source": "leetcode", "tags": r["tags"], "text": r["statement"].strip()} for r in lc]
for src, pat in (("taco", "taco-*.json"), ("code-contests", "code-contests-*.json")):
    for f in sorted(glob.glob(f"{B}/data/{src}/{pat}")):
        d = json.load(open(f)); c = d.get("content") if isinstance(d.get("content"), dict) else {}
        # the ETL's `description` is cut at 500 characters for most TACO/CodeContests records (found 2026-11-18);
        # the full statement is content.question (TACO) / content.description (CodeContests)
        t = (c.get("question") or c.get("description") or d.get("description") or "").strip()
        if t: docs.append({"doc_id": f"{src}:{d['reference_id']}", "source": src, "text": t})
lcslugs = {r["slug"] for r in lc}
qa, qg = [], []
for f in sorted(glob.glob(f"{B}/data/Fastprep_public/records/problems__*.json")):
    p = json.load(open(f))["record"]; stmt = detag(p.get("problemStatement"))
    if not stmt: continue
    t = p.get("title") or ""
    q = {"query_id": p["id"], "topics": p.get("topics") or [],
         "text": re.sub(re.escape(t), " ", stmt, flags=re.I) if t else stmt}
    qa.append(q)
    if norm(t) in lcslugs: qg.append({**q, "gold": f"lc:{norm(t)}"})
for name, rows in (("docs_v2", docs), ("queries_gold", qg), ("queries_all", qa)):
    with open(f"{X}/{name}.jsonl", "w") as fh:
        for r in rows: fh.write(json.dumps(r) + "\n")
from collections import Counter
print("docs", len(docs), Counter(d["source"] for d in docs), "| gold queries", len(qg), "| all queries", len(qa))
