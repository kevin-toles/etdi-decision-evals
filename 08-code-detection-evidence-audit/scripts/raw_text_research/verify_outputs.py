"""Independent check of the step-2 outputs (not reusing compare_reads.py / score_sets.py code paths):
  A. agreement, Cohen's kappa and code-vs-rest kappa recomputed from line_kinds.jsonl with a separate implementation;
     line_kinds.jsonl itself checked to hold exactly one row per non-blank sheet line;
  B. every gold-line outcome recomputed from line_kinds.jsonl rows (code if any line code, else not_code);
  C. every bad-block cause checked for consistency with the line_kinds.jsonl kinds of its lines (all_prose -> all prose
     in both reads; noncode_monospace -> no code, some noncode; code_plus_prose_edge -> some code and some non-code;
     actually_code / split_fragment / merged_blocks -> all code in both reads);
  D. every example in step2_block_examples.jsonl re-read from the raw JSON on the volume: text equals the raw lines it
     points to (blank lines skipped), and the line kinds agree with its label (good -> all code in both reads; look-alike
     -> all noncode_monospace in both reads);
  E. code-block-profile cross-check: how many of the 200 profiled blocks' BLOCK text occurs as a consecutive run on a
     page step 2 read (same document), found by text search over the raw JSON.
Writes verify_outputs.json; prints one line per check.
    python3 verify_outputs.py <dir>"""
import collections, glob, json, os, sys, unicodedata
R = sys.argv[1]; CL = os.path.dirname(os.path.abspath(R.rstrip("/"))); res = {}
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())
rows = [json.loads(l) for l in open(os.path.join(R, "line_kinds.jsonl"))]
K = {(r["batch"], r["doc"], r["page"], r["line"]): (r["read1"], r["read2"]) for r in rows}
# A
want = set(); rawp = {}; read_pages = collections.defaultdict(set)
for f in sorted(glob.glob(os.path.join(R, "sheet_B*.json"))):
    b = os.path.basename(f)[6:-5]
    for d in json.load(open(f))["documents"]:
        rawp[d["doc"]] = d["raw_path"]
        for p in d["pages"]:
            read_pages[d["doc"]].add(p["page"])
            want |= {(b, d["doc"], p["page"], l["n"]) for l in p["lines"] if loose(l["text"])}
n = len(rows); po = sum(a == c for a, c in K.values()) / n
def kap(pairs):
    m = len(pairs); A = collections.Counter(a for a, _ in pairs); B = collections.Counter(c for _, c in pairs)
    pe = sum(A[k] * B[k] for k in set(A) | set(B)) / (m * m); p0 = sum(a == c for a, c in pairs) / m
    return round((p0 - pe) / (1 - pe), 4)
pairs = list(K.values())
res["A"] = {"rows": n, "unique_rows": len(K), "rows_equal_nonblank_lines": set(K) == want, "agreement": round(po, 4), "kappa": kap(pairs),
            "code_vs_rest_kappa": kap([("c" if a == "code" else "o", "c" if c == "code" else "o") for a, c in pairs]),
            "uncovered_rows": sum("uncovered" in v for v in pairs)}
cr = json.load(open(os.path.join(R, "compare_reads.json")))["summary"]
res["A"]["matches_compare_reads"] = (res["A"]["agreement"], res["A"]["kappa"], res["A"]["code_vs_rest_kappa"]) == (cr["agreement"], cr["cohen_kappa"], cr["code_vs_rest_kappa"])
# B, C
S = json.load(open(os.path.join(R, "step2_sets.json")))
def item_lines(v):
    ks = [k for k in K if k[0] == v["batch"] and k[1] == v["doc"] and ((v["page_start"], v["line_start"]) <= (k[2], k[3]) <= (v["page_end"], v["line_end"]))]
    return [K[k] for k in sorted(ks, key=lambda k: (k[2], k[3]))]
byb = collections.defaultdict(list)
for k in K: byb[(k[0], k[1])].append(k)
def item_lines(v):
    ks = [k for k in byb[(v["batch"], v["doc"])] if (v["page_start"], v["line_start"]) <= (k[2], k[3]) <= (v["page_end"], v["line_end"])]
    return [K[k] for k in sorted(ks, key=lambda k: (k[2], k[3]))]
bad = []
for iid, v in S["gold_lines"].items():
    L = item_lines(v)
    if not L: exp = "invisible_only_line"
    else:
        a = "code" if any(x[0] == "code" for x in L) else "not_code"; c = "code" if any(x[1] == "code" for x in L) else "not_code"
        exp = a if a == c and not any("uncovered" in x for x in L) else "unresolved"
    if exp != v["outcome"]: bad.append((iid, v["outcome"], exp))
res["B"] = {"items": len(S["gold_lines"]), "mismatches": bad}
def ok_cause(c, ks):
    if not ks or any(k == "uncovered" for k in ks): return False
    if c == "all_prose": return all(k == "prose" for k in ks)
    if c == "noncode_monospace": return "code" not in ks and "noncode_monospace" in ks
    if c == "code_plus_prose_edge": return "code" in ks and any(k != "code" for k in ks)
    return all(k == "code" for k in ks)
bad = []
for iid, v in S["bad_block_causes"].items():
    L = item_lines(v)
    for r, c in ((0, v["read1"]), (1, v["read2"])):
        if c != "uncovered" and not ok_cause(c, [x[r] for x in L]): bad.append((iid, r + 1, c))
    if (v["read1"] == v["read2"] and v["read1"] != "uncovered") != (v["outcome"] != "unresolved"): bad.append((iid, "outcome", v["outcome"]))
res["C"] = {"items": len(S["bad_block_causes"]), "inconsistent": bad}
# D
raw = {}
def rawdoc(p):
    if p not in raw: raw[p] = {pg["page_number"]: pg["text"].split("\n") for pg in json.load(open(p))["pages"]}
    return raw[p]
cnt = collections.Counter(); badd = []
for l in open(os.path.join(R, "step2_block_examples.jsonl")):
    x = json.loads(l); rd = rawdoc(rawp[x["doc"]])
    seg = [(p, n, rd[p][n - 1]) for p, n in x["line_refs"]]
    if [t for _, _, t in seg] != x["text"] or not all(loose(t) for _, _, t in seg): badd.append((x["batch"], x["doc"], x["page_start"], x["line_start"], "text")); continue
    # lines inside the start..end range that the block skips must be page furniture the reads did not call part of the block
    rng = [(p, n) for p in range(x["page_start"], x["page_end"] + 1) for n in range(1, len(rd.get(p, [])) + 1)
           if (x["page_start"], x["line_start"]) <= (p, n) <= (x["page_end"], x["line_end"]) and loose(rd[p][n - 1])]
    skipped = [k for k in rng if [k[0], k[1]] not in x["line_refs"]]
    if x["source"] == "both_reads_identical_block" and any(K.get((x["batch"], x["doc"], p, n), ("?", "?"))[0] == x_k for p, n in skipped for x_k in [("code" if x["label"] == "good" else "noncode_monospace")]):
        badd.append((x["batch"], x["doc"], x["page_start"], x["line_start"], "skipped line has block kind"))
    cnt["skips_furniture"] += bool(skipped)
    ks = [K.get((x["batch"], x["doc"], p, n)) for p, n, _ in seg]
    if x["source"] == "both_reads_identical_block":
        want_k = "code" if x["label"] == "good" else "noncode_monospace"
        if not all(k == (want_k, want_k) for k in ks): badd.append((x["batch"], x["doc"], x["page_start"], x["line_start"], "kinds"))
    cnt[(x["label"], x["source"])] += 1
res["D"] = {"examples": {("|".join(k) if isinstance(k, tuple) else k): v for k, v in cnt.items()}, "problems": badd}
# E
bs = json.load(open(os.path.join(CL, "blocks_2026-10-28", "block_sheet.json")))["items"]; pos = json.load(open(os.path.join(CL, "blocks_2026-10-28", "block_positions.json")))
hit, same_doc = [], 0
for it in bs:
    stem = pos[it["id"]]["stem"]
    if stem not in rawp: continue
    same_doc += 1; rd = rawdoc(rawp[stem]); seq = [x.strip() for x in it["BLOCK"] if x.strip()]
    for pg in sorted(read_pages[stem]):
        t = [x.strip() for x in rd.get(pg, []) if x.strip()]
        if any(t[j:j + len(seq)] == seq for j in range(len(t) - len(seq) + 1)) or (len(seq) > 1 and any(t[-k:] == seq[:k] for k in range(1, len(seq)) if t[-k:])):
            hit.append(it["id"]); break
res["E"] = {"blocks": len(bs), "stem_in_step2": same_doc, "found_on_step2_pages": len(hit), "ids": hit}
cc = json.load(open(os.path.join(CL, "blocks_2026-10-28", "crosscheck_step2.json")))["summary"]
res["E"]["child_reported"] = {"stem_is_step2_doc": cc.get("stem_is_step2_doc"), "overlap_any_line": cc.get("overlap_any_line")}
json.dump(res, open(os.path.join(R, "verify_outputs.json"), "w"), indent=1, ensure_ascii=False)
for k, v in res.items(): print(k, json.dumps(v, ensure_ascii=False)[:600])
