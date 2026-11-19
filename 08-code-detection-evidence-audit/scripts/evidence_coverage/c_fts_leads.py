"""Evidence coverage, step 1C: FTS leads (no model, no LLM). For every item query (normalised line, 3-line shingle,
split-fragment pair, distinctive-token set) run an FTS5 phrase / AND query against chapters_fts_v2 (contentless, so it
returns chapter ids only), LIMIT 51:
  > 50 chapters                -> generic (pre-registered), no lead recorded
  own document                 -> excluded (normalised title match, [DUPE] removed)
  otherwise up to 3 chapters   -> read the chapter's pages back from collections/<collection>/raw/<stem>.json, locate the
                                  first matching line, keep 8 lines either side, the page number and the chapter id;
                                  the font label of that line if the document is in an answer-key/strata JSON (a lead,
                                  not a verdict: the panel measured those labels as 3-57% wrong by segment)
Writes fts_leads.jsonl (one record per lead).
    python3 c_fts_leads.py <out_dir> <work_dir>"""
import json, os, re, sqlite3, sys, time, functools
EV, W = sys.argv[1:3]
FTS = "<DATA_PATH>"
COLL = "<CORPUS_ROOT>/collections"
sys.path.insert(0, EV)
from a_build_queries_lib import norm   # same normaliser as step 1A
TOKS = lambda s: re.findall(r"[^\W_]+", s.lower())
ntitle = lambda s: re.sub(r"[^a-z0-9]", "", s.lower().replace("[dupe]", ""))
db = sqlite3.connect(f"file:{FTS}?mode=ro", uri=True)
items = json.load(open(os.path.join(EV, "items.json")))
# answer-key / strata font labels, keyed by normalised title -> {normalised line: label}
FONT = {}
for f in ("answer_key_v5.jsonl", "answer_key_v5_old40.jsonl", "strata_v5_books.jsonl", "strata_v5_tiny.jsonl", "strata_v5_lowcode.jsonl",
          "strata_v5_codefree.jsonl", "strata_v5_transcript.jsonl", "train_v5_lowcode.jsonl", "train_v5_codefree.jsonl"):
    for l in open(os.path.join(W, f)):
        d = json.loads(l); m = FONT.setdefault(ntitle(d["stem"]), {})
        for p in d["pages"]:
            for t, lab in p["lines"]:
                m.setdefault(norm(t), lab)
@functools.lru_cache(maxsize=64)
def raw_doc(collection, stem):
    p = os.path.join(COLL, collection, "raw", stem + ".json")
    try: return json.load(open(p)), p
    except Exception: return None, p
def chapter_context(cid, needle_norm, toks):
    ref, stem, coll = db.execute("select ref, stem, collection from chapter where id=?", (cid,)).fetchone()
    d, path = raw_doc(coll, stem)
    if d is None: return {"chapter_id": cid, "ref": ref, "raw_path": path, "located": False, "why": "raw JSON not readable"}
    n = int(ref.rsplit("#", 1)[1]); ch = next((c for c in d.get("chapters", []) if c.get("number") == n), None)
    pages = [p for p in d["pages"] if ch is None or ch["start_page"] <= p["page_number"] <= ch["end_page"]]
    lines = [(p["page_number"], l) for p in pages for l in p["text"].split("\n")]
    nl = [norm(l) for _, l in lines]
    hit = None
    if needle_norm:
        hit = next((i for i, x in enumerate(nl) if needle_norm in x or (x and x in needle_norm and len(x) >= 20)), None)
    if hit is None and toks:
        hit = next((i for i, x in enumerate(nl) if all(t in x.lower() for t in toks[:3])), None)
    if hit is None: return {"chapter_id": cid, "ref": ref, "raw_path": path, "located": False, "why": "FTS hit not located in raw text (tokeniser/porter differences)"}
    a, z = max(0, hit - 8), min(len(lines), hit + 9)
    fl = FONT.get(ntitle(stem), {}).get(nl[hit]) if ntitle(stem) in FONT else None
    return {"chapter_id": cid, "ref": ref, "raw_path": path, "located": True, "page": lines[hit][0], "line_in_chapter": hit,
            "matched_line": lines[hit][1], "context": [l for _, l in lines[a:z]], "context_range": [a, z - 1],
            "font_label": ("code" if fl else "not_code") if fl is not None else ("in answer key, line not labelled" if ntitle(stem) in FONT else "font unknown")}
def run(q):
    try: return [r[0] for r in db.execute("select rowid from fts where fts match ? limit 51", (q,))]
    except sqlite3.OperationalError as e: return ("error", str(e))
out = open(os.path.join(EV, "fts_leads.jsonl"), "w"); stats = {"queries": 0, "generic": 0, "no_hit": 0, "only_own": 0, "with_leads": 0, "errors": 0}
t0 = time.time()
for k, it in enumerate(items):
    own = ntitle(it["stem"]); qs = []
    for l in it["line_queries"]: qs.append(("line", l, '"' + " ".join(TOKS(l)) + '"', l))
    for sh in it["shingles"]: qs.append(("shingle", sh, '"' + " ".join(TOKS(" ".join(sh))) + '"', sh[0]))
    for pr in it["pair_queries"]: qs.append(("pair", pr, '"' + " ".join(TOKS(" ".join(pr))) + '"', pr[0]))
    tk = [t for t in it["tokens"] if TOKS(t)]
    if len(tk) >= 2: qs.append(("tokens", tk, " AND ".join('"' + " ".join(TOKS(t)) + '"' for t in tk[:4]), None))
    for kind, query_text, fq, needle in qs:
        stats["queries"] += 1; ids = run(fq)
        if isinstance(ids, tuple): stats["errors"] += 1; continue
        if len(ids) > 50: stats["generic"] += 1; continue
        if not ids: stats["no_hit"] += 1; continue
        rows = db.execute(f"select id, stem from chapter where id in ({','.join('?' * len(ids))})", ids).fetchall()
        other = [cid for cid, stem in rows if ntitle(stem) != own]
        if not other: stats["only_own"] += 1; continue
        stats["with_leads"] += 1
        for cid in other[:3]:
            ctx = chapter_context(cid, needle, [t.lower() for t in TOKS(" ".join(query_text))] if kind == "tokens" else None)
            out.write(json.dumps({"item": it["id"], "set": it["set"], "query_kind": kind, "query": query_text, "fts_query": fq,
                                  "fts_hits_total": len(ids), "fts_hits_other_docs": len(other), "source": "corpus", **ctx}, ensure_ascii=False) + "\n")
    if k % 100 == 0: print(f"{k}/{len(items)} items, {time.time() - t0:.0f}s, {stats}", flush=True)
out.close(); json.dump(stats, open(os.path.join(EV, "fts_stats.json"), "w"), indent=1); print("done", stats, f"{time.time() - t0:.0f}s")
