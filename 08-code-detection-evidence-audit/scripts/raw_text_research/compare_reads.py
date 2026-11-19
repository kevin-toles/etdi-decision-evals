"""Line-level comparison of the two blind raw-text reads (research_<b>.json by claude-opus-5-5, research2_<b>.json by
claude-opus-4-8). Every non-blank page line (invisible-only lines count as blank) gets one kind from each read
(code / noncode_monospace / prose; "uncovered" if a read left it out). Reports agreement and Cohen's kappa overall and
on item lines, per-item outcome (both reads agree -> decided; else unresolved), and writes line_kinds.jsonl.
Make-up quotes (makeup_research.json) only repair citations; kinds and lines were unchanged, so they do not enter here.
    python3 compare_reads.py <dir> [batch ...]"""
import collections, glob, json, os, sys, unicodedata
R = sys.argv[1]; want = set(sys.argv[2:])
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())
idx = json.load(open(os.path.join(R, "sheet_index.json")))["index"]
# second-read make-up (makeup2_*): a validated RECITE replaces its span; validated GAP spans fill lines no span covered.
# Entries that failed validation are not applied, so their lines stay as first written (or uncovered -> unresolved).
MK = {}
if os.path.exists(os.path.join(R, "makeup2_validation.json")):
    mv = json.load(open(os.path.join(R, "makeup2_validation.json")))["entries"]; mi = {e["id"]: e for e in json.load(open(os.path.join(R, "makeup2_index.json")))["entries"]}
    for f in glob.glob(os.path.join(R, "makeup2_research_M*.json")):
        m = json.load(open(f), strict=False)
        for x in m.get("recites", []) + [dict(s, id=g["id"]) for g in m.get("gaps", []) for s in g.get("spans", [])]:
            e = mi.get(x.get("id"))
            if e and mv.get(e["id"], {}).get("ok"): MK.setdefault(e["batch"], []).append((e, dict(x, doc=e["doc"], page=e["page"])))
def kinds(path, pages, batch=None):
    k = {}
    if not os.path.exists(path): return None
    spans = json.load(open(path), strict=False).get("spans", []); mk = MK.get(batch, []) if batch else []
    drop = {e["span_index"] for e, _ in mk if e["type"] == "RECITE"}
    spans = [s for i, s in enumerate(spans) if i not in drop] + [x for e, x in mk if e["type"] == "RECITE"] + [x for e, x in mk if e["type"] == "GAP"]
    for s in spans:
        key = (s.get("doc"), s.get("page"))
        if key not in pages or not isinstance(s.get("line_start"), int) or not isinstance(s.get("line_end"), int): continue
        for n in range(s["line_start"], s["line_end"] + 1):
            if n in pages[key]: k.setdefault((key, n), s.get("kind"))
    return k
pairs, item_out, per_batch = [], {}, {}
out = open(os.path.join(R, "line_kinds.jsonl" if not want else "line_kinds_partial.jsonl"), "w")
for f in sorted(glob.glob(os.path.join(R, "sheet_B*.json"))):
    b = os.path.basename(f)[6:-5]
    if want and b not in want: continue
    sheet = json.load(open(f))
    pages = {(d["doc"], p["page"]): {l["n"]: l["text"] for l in p["lines"] if loose(l["text"])} for d in sheet["documents"] for p in d["pages"]}
    k1 = kinds(os.path.join(R, f"research_{b}.json"), pages); k2 = kinds(os.path.join(R, f"research2_{b}.json"), pages, b)
    if k1 is None or k2 is None: per_batch[b] = "missing read"; continue
    agree = tot = 0
    for key, L in pages.items():
        for n in L:
            a, c = k1.get((key, n), "uncovered"), k2.get((key, n), "uncovered"); pairs.append((a, c)); tot += 1; agree += a == c
            out.write(json.dumps({"batch": b, "doc": key[0], "page": key[1], "line": n, "read1": a, "read2": c}, ensure_ascii=False) + "\n")
    per_batch[b] = round(agree / tot, 4) if tot else None
    for d in sheet["documents"]:
        for it in d["items"]:
            key = (d["doc"], it["page_start"]); lines = [n for n in range(it["line_start"], it["line_end"] + 1) if n in pages.get(key, {})] if it["page_start"] == it["page_end"] else None
            if lines is None:                                   # item crossing a page break: both pages' lines
                lines = [(d["doc"], it["page_start"], n) for n in pages.get((d["doc"], it["page_start"]), {}) if n >= it["line_start"]] + \
                        [(d["doc"], it["page_end"], n) for n in pages.get((d["doc"], it["page_end"]), {}) if n <= it["line_end"]]
                r1 = [k1.get(((x[0], x[1]), x[2]), "uncovered") for x in lines]; r2 = [k2.get(((x[0], x[1]), x[2]), "uncovered") for x in lines]
            else:
                r1 = [k1.get((key, n), "uncovered") for n in lines]; r2 = [k2.get((key, n), "uncovered") for n in lines]
            item_out[it["item"]] = {"kind": it["kind"], "batch": b, "read1": r1, "read2": r2,
                                    "outcome": "decided" if r1 == r2 and "uncovered" not in r1 else "unresolved"}
out.close()
def kappa(ps):
    n = len(ps); cats = sorted({x for p in ps for x in p}); po = sum(a == b for a, b in ps) / n
    c1 = collections.Counter(a for a, _ in ps); c2 = collections.Counter(b for _, b in ps); pe = sum(c1[c] * c2[c] for c in cats) / (n * n)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None
conf = collections.Counter(pairs)
res = {"lines": len(pairs), "agreement": round(sum(a == b for a, b in pairs) / len(pairs), 4) if pairs else None, "cohen_kappa": kappa(pairs) if pairs else None,
       "confusion": {f"{a}|{b}": v for (a, b), v in sorted(conf.items())},
       "code_vs_rest_kappa": kappa([("code" if a == "code" else "other", "code" if b == "code" else "other") for a, b in pairs]) if pairs else None,
       "items": dict(collections.Counter((v["kind"], v["outcome"]) for v in item_out.values()).items()) if item_out else {},
       "per_batch_agreement": per_batch}
res["items"] = {f"{k[0]}|{k[1]}": v for k, v in res["items"].items()}
json.dump({"summary": res, "items": item_out}, open(os.path.join(R, "compare_reads.json" if not want else "compare_reads_partial.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "per_batch_agreement"}, indent=1))
