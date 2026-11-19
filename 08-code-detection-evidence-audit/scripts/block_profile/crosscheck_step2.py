"""Cross-check of the 200 profiled blocks (block_sheet.json + block_positions.json + block_report.json) against the
step-2 raw-text reads (raw_text_research_2026-11-17: line_kinds.jsonl, step2_block_examples.jsonl, sheet_B*.json).
Read-only, no LLM calls. Each block is located in its document's raw JSON by its own text plus context (key lines are
raw page lines one-to-one, so a block cut to 25 lines on the sheet is extended to its full length from the positions
file). Its lines are then looked up in step 2 by (doc, page, line); a text-only search over every step-2 page catches
the same text under another document name. Nothing is relabelled and no disagreement is settled: per block, the two
reads' line kinds, the step-2 code runs around the block and any step-2 block example it touches are listed as found.
A read calls a block code when at least half its non-blank lines are 'code' in that read.
    python3 crosscheck_step2.py <code_label_audit_dir>"""
import collections, glob, json, os, sys

CL = sys.argv[1]; OUT = os.path.join(CL, "blocks_2026-10-28"); R = os.path.join(CL, "raw_text_research_2026-11-17")
COLL = "<CORPUS_ROOT>/collections"
S = lambda x: x.strip()
sheet = {x["id"]: x for x in json.load(open(os.path.join(OUT, "block_sheet.json")))["items"]}
where = json.load(open(os.path.join(OUT, "block_positions.json")))
cons = json.load(open(os.path.join(OUT, "block_report.json")))["blocks"]
raw = {}
for c in sorted(os.listdir(COLL)):
    d = os.path.join(COLL, c, "raw")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"): raw.setdefault(f[:-5], os.path.join(d, f))
kinds = {}                                                     # (doc, page, line) -> (read1, read2)
order = collections.defaultdict(list)                          # doc -> sorted (page, line) of read non-blank lines
for l in open(os.path.join(R, "line_kinds.jsonl")):
    r = json.loads(l); kinds[(r["doc"], r["page"], r["line"])] = (r["read1"], r["read2"]); order[r["doc"]].append((r["page"], r["line"]))
for d in order: order[d].sort()
rank = {(d, pl): i for d, L in order.items() for i, pl in enumerate(L)}
step2_text = collections.defaultdict(list)                     # stripped text -> [(doc, page, line)] over all read pages
for f in sorted(glob.glob(os.path.join(R, "sheet_B*.json"))):
    for d in json.load(open(f))["documents"]:
        for pg in d["pages"]:
            for ln in pg["lines"]:
                if S(ln["text"]): step2_text[S(ln["text"])].append((d["doc"], pg["page"], ln["n"]))
examples = collections.defaultdict(list)
for l in open(os.path.join(R, "step2_block_examples.jsonl")):
    e = json.loads(l); examples[e["doc"]].append(e)

def locate(bid):
    """Full block span in the raw JSON as a list of (page, line, text), found by the block's text and context."""
    it, w = sheet[bid], where[bid]
    flat = [(p["page_number"], i + 1, t) for p in json.load(open(raw[w["stem"]]))["pages"] for i, t in enumerate(p["text"].split("\n"))]
    seq, best = it["BLOCK"], None
    for j in range(len(flat) - len(seq) + 1):
        if any(flat[j + k][2] != seq[k] for k in range(len(seq))): continue
        sc = sum(a == flat[j - 1 - k][2] for k, a in enumerate(reversed(it["before"])) if j - 1 - k >= 0) + \
             sum(a == flat[j + w["lines"] + k][2] for k, a in enumerate(it["after"]) if j + w["lines"] + k < len(flat))
        if best is None or sc > best[0]: best = (sc, j)
    if best is None: return None, None
    j = best[1]; ctx_max = len(it["before"]) + len(it["after"])
    return flat[j:j + w["lines"]], {"context_score": best[0], "context_max": ctx_max,
                                    "before": [x[:2] for x in flat[max(0, j - 2):j]], "after": [x[:2] for x in flat[j + w["lines"]:j + w["lines"] + 2]]}

def run_around(doc, keys, r):
    """Read r's maximal run of consecutive 'code' lines (in step-2 read order) that touches the block's lines."""
    hit = [rank[(doc, k)] for k in keys if (doc, k) in rank and kinds[(doc,) + k][r] == "code"]
    if not hit: return None
    L = order[doc]; a, z = min(hit), max(hit)
    while a > 0 and kinds[(doc,) + L[a - 1]][r] == "code": a -= 1
    while z + 1 < len(L) and kinds[(doc,) + L[z + 1]][r] == "code": z += 1
    br = [rank[(doc, k)] for k in keys if (doc, k) in rank]
    gaps = sum(1 for i in range(min(br), max(br) + 1) if kinds[(doc,) + L[i]][r] != "code")
    return {"start": list(L[a]), "end": list(L[z]), "starts_before_block_by": min(br) - a, "ends_after_block_by": z - max(br),
            "non_code_lines_inside_block": gaps}

rows = []
for bid in sorted(where):
    w, c = where[bid], cons[bid]
    row = {"id": bid, "stratum": w["kind"], "stem": w["stem"], "consensus_language": c["language"], "consensus_kind": c["kind"],
           "truncated_on_sheet": sheet[bid]["truncated"], "step2_doc": w["stem"] in order}
    span, ctx = locate(bid)
    if span is None:
        row["located"] = False; rows.append(row); continue
    nb = [(p, l) for p, l, t in span if S(t)]
    row.update({"located": True, "raw_span": [list(span[0][:2]), list(span[-1][:2])], **ctx, "nonblank_lines": len(nb)})
    doc = w["stem"]
    cov = [k for k in nb if (doc,) + k in kinds]
    if not cov:                                                 # same text read under another document name?
        texts = [S(t) for p, l, t in span if S(t)]; alt = {}
        for d in {d for t in texts for d, _, _ in step2_text.get(t, [])}:
            L = [rank[(d, (p, l))] for t in texts for dd, p, l in step2_text[t] if dd == d and (d, (p, l)) in rank]
            pos = {t: sorted(rank[(d, (p, l))] for dd, p, l in step2_text[t] if dd == d and (d, (p, l)) in rank) for t in texts}
            longest = 0                                         # longest run of the block's lines, consecutive in that doc
            for i in range(len(texts)):
                for st in pos[texts[i]]:
                    k = 1
                    while i + k < len(texts) and st + k in pos[texts[i + k]]: k += 1
                    longest = max(longest, k)
            if longest >= 2: alt[d] = longest
        row["covered_lines"] = 0
        if alt: row["text_run_in_other_step2_docs"] = dict(sorted(alt.items(), key=lambda x: -x[1])[:3])
        rows.append(row); continue
    row["covered_lines"] = len(cov)
    for r, name in ((0, "read1"), (1, "read2")):
        cnt = collections.Counter(kinds[(doc,) + k][r] for k in cov)
        row[f"{name}_kinds"] = dict(cnt)
        row[f"{name}_block_is_code"] = cnt["code"] * 2 >= len(cov)
        row[f"{name}_code_run"] = run_around(doc, cov, r)
        row[f"{name}_context_kinds"] = {"before": [kinds.get((doc, p, l), (None, None))[r] for p, l in ctx["before"]],
                                        "after": [kinds.get((doc, p, l), (None, None))[r] for p, l in ctx["after"]]}
    keys = set(nb); ex = []
    for e in examples[doc]:
        pls = set()
        for p in range(e["page_start"], e["page_end"] + 1):
            pls |= {k for k in keys if k[0] == p and (p > e["page_start"] or k[1] >= e["line_start"]) and (p < e["page_end"] or k[1] <= e["line_end"])}
        if pls:
            ex.append({"label": e["label"], "why": e["why"], "span": [[e["page_start"], e["line_start"]], [e["page_end"], e["line_end"]]],
                       "lines": e["lines"], "shared_lines": len(pls), "same_boundaries": [e["page_start"], e["line_start"]] == list(nb[0]) and [e["page_end"], e["line_end"]] == list(nb[-1])})
    row["step2_examples"] = ex
    rows.append(row)

cov = [r for r in rows if r.get("covered_lines")]
full = [r for r in cov if r["covered_lines"] == r["nonblank_lines"]]
def code_call(r): return r["consensus_kind"] != "not_code" if r["consensus_kind"] != "no_consensus" else None
agree = collections.Counter()
for r in cov:
    k = code_call(r); a, b = r["read1_block_is_code"], r["read2_block_is_code"]
    agree[("ours=" + ("none" if k is None else "code" if k else "not_code"), "read1=" + ("code" if a else "not_code"), "read2=" + ("code" if b else "not_code"))] += 1
summary = {
    "blocks": len(rows), "located_in_raw": sum(r["located"] for r in rows), "stem_is_step2_doc": sum(r["step2_doc"] for r in rows),
    "overlap_any_line": len(cov), "overlap_all_lines": len(full),
    "overlap_by_stratum": dict(collections.Counter(r["stratum"] for r in cov)),
    "text_run_under_other_step2_doc": {r["id"]: [r["nonblank_lines"], r["text_run_in_other_step2_docs"]] for r in rows if r.get("text_run_in_other_step2_docs")},
    "code_vs_not_code": {" ".join(k): v for k, v in sorted(agree.items())},
    "not_code_blocks": {r["id"]: ("not in step 2" if not r.get("covered_lines") else {"read1": r["read1_kinds"], "read2": r["read2_kinds"]})
                        for r in rows if r["consensus_kind"] == "not_code"},
    "terminal_output_or_log_blocks": {r["id"]: ("not in step 2" if not r.get("covered_lines") else {"read1": r["read1_kinds"], "read2": r["read2_kinds"]})
                                      for r in rows if r["consensus_kind"] == "terminal_output_or_log"},
}
json.dump({"summary": summary, "blocks": rows}, open(os.path.join(OUT, "crosscheck_step2.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1, ensure_ascii=False))
