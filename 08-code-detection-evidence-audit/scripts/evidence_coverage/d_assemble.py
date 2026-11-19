"""Evidence coverage, step 1D: assemble every lead into matches.jsonl and write the report. Nothing here decides a label.
Leads come from:
  CRE / ETL-raw ripgrep passes (rg_<root>.out: fixed-string line hits)  -> read back with 8 lines either side; flags:
      in_comment_or_docstring (line starts with a comment marker, or sits inside a triple-quoted string), doc_file
      (.md/.rst/.txt/.html/.adoc/.tex), contiguous (the hit is part of a run matching an item shingle or pair in order)
  FTS corpus leads (fts_leads.jsonl), with the answer-key font label where the document has one, else "font unknown"
Candidate classes (retrieval leads awaiting research, NOT evidence and NOT labels):
  code_candidate          a CRE or ETL-raw hit in a non-doc file, or a corpus hit on a line font-labelled code
  prose_candidate         a corpus hit on a line font-labelled not code, and no code-side hit
  conflicting_candidates  both of the above
  no_candidate            neither (font-unknown corpus hits and doc-file / comment hits are counted separately)
    python3 d_assemble.py <out_dir>"""
import collections, json, os, re, sys
EV = sys.argv[1]
ROOTS = {"CRE": "<SSD_PATH> Reference Engine [CRE]",
         "ETL_oreilly": "<ETL_RAW_ROOT>/data/oreilly",
         "ETL_code_contests": "<ETL_RAW_ROOT>/data/code-contests",
         "ETL_supplemental": "<ETL_RAW_ROOT>/Supplemental Data",
         "ETL_fastprep_public": "<ETL_RAW_ROOT>/data/Fastprep_public"}
DOC_EXT = {".md", ".rst", ".txt", ".html", ".htm", ".adoc", ".tex", ".markdown", ".org"}
COMMENT = re.compile(r"^\s*(#|//|/\*|\*|--|;|%|<!--|')")
items = json.load(open(os.path.join(EV, "items.json")))
by_pat = collections.defaultdict(list)
for it in items:
    for q in it["line_queries"]: by_pat[q].append(it["id"])
    for pr in it["pair_queries"]:
        for x in pr: by_pat[x].append(it["id"])
_files = {}
def file_lines(path):
    if path not in _files:
        if len(_files) > 256: _files.clear()
        try: _files[path] = open(path, encoding="utf-8", errors="replace").read().split("\n")
        except Exception: _files[path] = None
    return _files[path]
def in_docstring(L, i):
    q = 0
    for l in L[:i]: q += l.count('"""') + l.count("'''")
    return q % 2 == 1
leads = collections.defaultdict(list); stats = collections.Counter()
for root in ROOTS:
    f = os.path.join(EV, f"rg_{root}.out")
    if not os.path.exists(f): stats[f"{root}: no output file"] += 1; continue
    hits = collections.defaultdict(list)
    for raw in open(f, encoding="utf-8", errors="replace"):
        if "\0" not in raw: continue
        path, rest = raw.rstrip("\n").split("\0", 1)
        ln, _, m = rest.partition(":")
        if ln.isdigit() and m in by_pat: hits[path].append((int(ln), m))
    for path, hl in hits.items():
        L = file_lines(path); ext = os.path.splitext(path)[1].lower(); lines_hit = {ln: m for ln, m in hl}
        for ln, m in hl:
            for iid in set(by_pat[m]):
                it = next(x for x in items if x["id"] == iid) if False else None
                ctx = L[max(0, ln - 9):ln + 8] if L else None
                line_text = L[ln - 1] if L and ln - 1 < len(L) else None
                leads[iid].append({"item": iid, "source": "CRE" if root == "CRE" else "ETL_raw", "root": root, "path": path,
                                   "line": ln, "matched_text": m, "line_text": line_text, "context": ctx,
                                   "context_range": [max(1, ln - 8), ln + 8] if L else None, "doc_file": ext in DOC_EXT,
                                   "in_comment_or_docstring": bool(line_text and (COMMENT.match(line_text) or in_docstring(L, ln - 1))),
                                   "query_kind": "line", "lines_hit_in_file": sorted(lines_hit)})
        stats[f"{root}: files with hits"] += 1
# contiguity of shingles / split-fragment pairs within one file (consecutive non-blank lines in order)
ITEM = {x["id"]: x for x in items}
for iid, ls in leads.items():
    it = ITEM[iid]; seqs = [s for s in it["shingles"]] + [p for p in it["pair_queries"]]
    byfile = collections.defaultdict(dict)
    for x in ls:
        if x["source"] in ("CRE", "ETL_raw"): byfile[x["path"]][x["line"]] = x["matched_text"]
    for x in ls:
        if x["source"] not in ("CRE", "ETL_raw"): continue
        L = file_lines(x["path"]); runs = []
        for seq in seqs:
            if x["matched_text"] != seq[0]: continue
            j, ok = x["line"], True
            for want in seq[1:]:
                j += 1
                while L and j - 1 < len(L) and not L[j - 1].strip(): j += 1
                if byfile[x["path"]].get(j) != want: ok = False; break
            if ok: runs.append(len(seq))
        x["contiguous_run"] = max(runs) if runs else None
for l in open(os.path.join(EV, "fts_leads.jsonl")):
    r = json.loads(l); leads[r["item"]].append(r)
# classes
def cls(ls):
    code = any((x["source"] in ("CRE", "ETL_raw") and not x["doc_file"]) or (x["source"] == "corpus" and x.get("font_label") == "code") for x in ls)
    prose = any(x["source"] == "corpus" and x.get("font_label") == "not_code" for x in ls)
    return "conflicting_candidates" if code and prose else "code_candidate" if code else "prose_candidate" if prose else "no_candidate"
with open(os.path.join(EV, "matches.jsonl"), "w") as fh:
    for iid in sorted(leads):
        for x in leads[iid]: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
rep = {"note": "Every class is a retrieval lead awaiting research (step 2). Nothing here is evidence or decides a label.", "per_item": {}}
tab = collections.defaultdict(collections.Counter); lab = collections.defaultdict(collections.Counter); anyl = collections.Counter(); tot = collections.Counter()
unk = collections.Counter(); docc = collections.Counter(); cmt = collections.Counter()
for it in items:
    ls = leads.get(it["id"], []); c = cls(ls); key = (it["set"], it["segment"])
    tab[key][c] += 1; lab[(it["set"], it["panel_label"])][c] += 1; tot[it["set"]] += 1
    if ls: anyl[it["set"]] += 1
    nu = sum(1 for x in ls if x["source"] == "corpus" and x.get("font_label") == "font unknown" and x.get("located"))
    if nu: unk[it["set"]] += 1
    if any(x["source"] in ("CRE", "ETL_raw") and x["doc_file"] for x in ls): docc[it["set"]] += 1
    if any(x["source"] in ("CRE", "ETL_raw") and x.get("in_comment_or_docstring") for x in ls): cmt[it["set"]] += 1
    rep["per_item"][it["id"]] = {"set": it["set"], "segment": it["segment"], "panel_label": it["panel_label"], "candidate_class": c,
                                 "leads": collections.Counter(x["source"] + ("/" + x.get("font_label", "") if x["source"] == "corpus" else ("/doc" if x.get("doc_file") else "")) for x in ls),
                                 "queried": bool(it["line_queries"] or it["shingles"] or it["pair_queries"] or len(it["tokens"]) >= 2)}
rep.update({"by_segment": {f"{a}|{b}": dict(v) for (a, b), v in tab.items()}, "by_panel_label": {f"{a}|{b}": dict(v) for (a, b), v in lab.items()},
            "items": dict(tot), "items_with_any_lead": dict(anyl), "items_with_font_unknown_corpus_lead": dict(unk),
            "items_with_doc_file_hit": dict(docc), "items_with_comment_or_docstring_hit": dict(cmt), "rg_stats": dict(stats),
            "fts_stats": json.load(open(os.path.join(EV, "fts_stats.json")))})
json.dump(rep, open(os.path.join(EV, "coverage_report.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in rep.items() if k != "per_item"}, indent=1))
