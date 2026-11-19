"""Verifies the step-2 work against the raw corpus JSON on the data volume (not against the sheets):
  1. every sheet page equals the raw document's page text split on newlines (same lines, same order, same characters);
  2. every item's lines (page/line pointers) hold the item's text from the gold / bad-block sheets;
  3. every span quote (read 1, read 2, read-2 make-up) matches the raw line it cites, strict or loose tier.
Writes verify_raw.json.
    python3 verify_raw.py <dir>"""
import collections, glob, json, os, sys, unicodedata
R = sys.argv[1]; CL = os.path.dirname(os.path.abspath(R.rstrip("/")))
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())
S = lambda x: x.strip()
raw, out = {}, {"pages": collections.Counter(), "page_mismatch": [], "items": collections.Counter(), "item_mismatch": [], "quotes": {}}
def rawdoc(p):
    if p not in raw: raw[p] = {pg["page_number"]: pg["text"].split("\n") for pg in json.load(open(p))["pages"]}
    return raw[p]
gs = {x["id"]: [x["TARGET"]] for p in "AB" for x in json.load(open(os.path.join(CL, "gold_panel_2026-11-17", f"round1_sheet_{p}.json")))["items"]}
bs = {x["id"]: x["BLOCK"] for p in "AB" for x in json.load(open(os.path.join(CL, "bad_block_causes_2026-11-17", f"round1_sheet_{p}.json")))["items"]}
RAWL = {}
for f in sorted(glob.glob(os.path.join(R, "sheet_B*.json"))):
    b = os.path.basename(f)[6:-5]; sh = json.load(open(f))
    for d in sh["documents"]:
        rd = rawdoc(d["raw_path"])
        for p in d["pages"]:
            same = [l["text"] for l in p["lines"]] == rd.get(p["page"])
            out["pages"]["equal" if same else "differ"] += 1
            if not same: out["page_mismatch"].append([b, d["doc"], p["page"]])
            RAWL[(b, d["doc"], p["page"])] = rd.get(p["page"], [])
        for it in d["items"]:
            want = [S(x) for x in (gs.get(it["item"]) or bs.get(it["item"]) or []) if S(x)]
            if it["page_start"] == it["page_end"]: seg = rd[it["page_start"]][it["line_start"] - 1:it["line_end"]]
            else: seg = rd[it["page_start"]][it["line_start"] - 1:] + rd[it["page_end"]][:it["line_end"]]
            ok = [S(x) for x in seg if S(x)] == want
            out["items"]["match" if ok else "differ"] += 1
            if not ok: out["item_mismatch"].append([b, it["item"]])
def check(name, rows):
    c = collections.Counter()
    for b, doc, pg, a, z, q1, q2 in rows:
        L = RAWL.get((b, doc, pg))
        if not L or not (isinstance(a, int) and isinstance(z, int) and 1 <= a <= z <= len(L)): c["lines_off_page"] += 1; continue
        for q, n in ((q1, a), (q2, z)):
            t = L[n - 1]; c["strict" if t == q else ("loose" if loose(t) == loose(q) else "fail")] += 1
    out["quotes"][name] = dict(c); print(name, dict(c))
for pre in ("research", "research2"):
    rows = []
    for f in sorted(glob.glob(os.path.join(R, f"{pre}_B*.json"))):
        b = os.path.basename(f)[len(pre) + 1:-5]
        rows += [(b, s.get("doc"), s.get("page"), s.get("line_start"), s.get("line_end"), s.get("quote_first"), s.get("quote_last")) for s in json.load(open(f), strict=False).get("spans", [])]
    check(pre, rows)
mi = {e["id"]: e for e in json.load(open(os.path.join(R, "makeup2_index.json")))["entries"]}; rows = []
for f in sorted(glob.glob(os.path.join(R, "makeup2_research_M*.json"))):
    m = json.load(open(f), strict=False)
    for x in m.get("recites", []) + [dict(s, id=g["id"]) for g in m.get("gaps", []) for s in g.get("spans", [])]:
        e = mi.get(x.get("id"))
        if e: rows.append((e["batch"], e["doc"], e["page"], x.get("line_start"), x.get("line_end"), x.get("quote_first"), x.get("quote_last")))
check("makeup2", rows)
print("pages", dict(out["pages"]), "items", dict(out["items"]), "page mismatches", out["page_mismatch"][:5], "item mismatches", out["item_mismatch"][:10])
out["pages"] = dict(out["pages"]); out["items"] = dict(out["items"])
json.dump(out, open(os.path.join(R, "verify_raw.json"), "w"), indent=1, ensure_ascii=False)
