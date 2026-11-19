"""Build embedder-comparison inputs: reference docs (LeetCode guidelines, TACO, CodeContests) and
FastPrep queries whose title exactly matches a LeetCode guideline (gold = that guideline's slug).
Titles are stripped from both sides so the match must come from the text, not the name. No LLM calls.
Usage: python3 -I build_inputs.py <guidelines_etl_data_dir> <out_dir>
"""
import ast, glob, html, json, os, re, sys

B, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
norm = lambda s: re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
detag = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def lit(v):
    if isinstance(v, str) and v[:1] in "{[":
        try: return ast.literal_eval(v)
        except Exception: return v
    return v


def strip_title(text, title):
    return re.sub(re.escape(title), " ", text, flags=re.I) if title else text


# LeetCode guidelines: dedupe by slug, prefer a record carrying solution code
lg = {}
for f in sorted(glob.glob(f"{B}/data/guidelines/leetcode-guidelines/guideline_*.json")):
    d = json.load(open(f)); s = d.get("title_slug")
    if not s: continue
    if s not in lg or (str(d.get("has_solution_code")) == "True" and str(lg[s].get("has_solution_code")) != "True"):
        lg[s] = d
docs = []
for s, d in lg.items():
    sit = lit(d.get("situation")); pat = lit(d.get("pattern"))
    parts = [sit.get("summary", "") if isinstance(sit, dict) else str(sit or ""),
             d.get("guideline", ""), d.get("reasoning", ""),
             pat.get("pattern_name", "") if isinstance(pat, dict) else ""]
    docs.append({"doc_id": f"lg:{s}", "source": "leetcode-guidelines",
                 "text": strip_title(" ".join(p for p in parts if p), d.get("title"))})
for src, pat in (("taco", "taco-*.json"), ("code-contests", "code-contests-*.json")):
    for f in sorted(glob.glob(f"{B}/data/{src}/{pat}")):
        d = json.load(open(f)); t = (d.get("description") or "").strip()
        if t: docs.append({"doc_id": f"{src}:{d['reference_id']}", "source": src, "text": t})

queries = []
for f in sorted(glob.glob(f"{B}/data/Fastprep_public/records/problems__*.json")):
    r = json.load(open(f)); p = r["record"]; slug = norm(p.get("title"))
    stmt = detag(p.get("problemStatement"))
    if slug in lg and stmt:
        queries.append({"query_id": p["id"], "gold": f"lg:{slug}", "topics": p.get("topics"),
                        "text": strip_title(stmt, p.get("title"))})

with open(f"{OUT}/docs.jsonl", "w") as fh:
    for d in docs: fh.write(json.dumps(d) + "\n")
with open(f"{OUT}/queries.jsonl", "w") as fh:
    for q in queries: fh.write(json.dumps(q) + "\n")
from collections import Counter
print("docs", len(docs), Counter(d["source"] for d in docs), "queries", len(queries))
