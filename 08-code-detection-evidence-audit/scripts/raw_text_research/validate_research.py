"""Mechanical check of research_<batch>.json files against their sheets (no model, no judgement):
  model id; batch id; span kinds; quote_first / quote_last verbatim at the cited page and line (against the sheet JSON,
  which holds the raw JSON page text); every non-blank page line covered by exactly one span; every item has an entry;
  every lead verdict names a real lead. Prints one row per batch and writes validation.json.
    python3 validate_research.py <dir> [batch ...]"""
import glob, json, os, sys
R = sys.argv[1]; want = sys.argv[2:]
PREFIX = os.environ.get("PREFIX", "research"); MODEL = os.environ.get("MODEL", "claude-opus-5-5")   # second blind read: PREFIX=research2 MODEL=claude-opus-4-8
KINDS = {"code", "noncode_monospace", "prose"}; out = {}
import re, unicodedata
# loose tier: the same text once non-printing characters are normalised (NBSP and other spaces -> " ", C0/C1 control and
# format characters removed, outer whitespace trimmed). Anything that still differs is a failed quote.
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())   # + compatibility forms, private-use glyphs
files = sorted(glob.glob(os.path.join(R, f"{PREFIX}_B*.json")))
for f in files:
    bid = os.path.basename(f)[len(PREFIX) + 1:-5]
    if want and bid not in want: continue
    sheet = json.load(open(os.path.join(R, f"sheet_{bid}.json"))); probs = []
    try: r = json.load(open(f), strict=False)   # agents sometimes write a raw tab inside a quoted line; read it as written
    except Exception as e: out[bid] = {"ok": False, "problems": [f"unreadable: {e}"]}; print(bid, "UNREADABLE", e); continue
    if r.get("model") != MODEL: probs.append(f"model {r.get('model')}")
    if r.get("batch") != bid: probs.append(f"batch {r.get('batch')}")
    pages = {(d["doc"], p["page"]): {l["n"]: l["text"] for l in p["lines"]} for d in sheet["documents"] for p in d["pages"]}
    cover = {k: {n: 0 for n, t in v.items() if loose(t)} for k, v in pages.items()}   # lines with only invisible characters count as blank
    bad_quote = 0; loose_only = 0
    for i, s in enumerate(r.get("spans", [])):
        k = (s.get("doc"), s.get("page"))
        if k not in pages: probs.append(f"span {i}: unknown doc/page {k}"); continue
        if s.get("kind") not in KINDS: probs.append(f"span {i}: kind {s.get('kind')}")
        a, z = s.get("line_start"), s.get("line_end")
        if not (isinstance(a, int) and isinstance(z, int) and a <= z and a in pages[k] and z in pages[k]): probs.append(f"span {i}: lines {a}-{z}"); continue
        for q, n in ((s.get("quote_first"), a), (s.get("quote_last"), z)):
            if pages[k][n] == q: continue
            if loose(pages[k][n]) == loose(q): loose_only += 1
            else: bad_quote += 1
        for n in range(a, z + 1):
            if n in cover[k]: cover[k][n] += 1
    if bad_quote: probs.append(f"{bad_quote} quotes that differ from the cited line even after invisible-character normalising")
    unc = sum(1 for v in cover.values() for c in v.values() if c == 0); dbl = sum(1 for v in cover.values() for c in v.values() if c > 1)
    if unc: probs.append(f"{unc} non-blank lines not covered")
    if dbl: probs.append(f"{dbl} lines covered by more than one span")
    item_ids = {it["item"] for d in sheet["documents"] for it in d["items"]}
    lead_ids = {ld["lead_id"] for d in sheet["documents"] for it in d["items"] for ld in it["leads"]}
    got = {x.get("item") for x in r.get("items", [])}
    if item_ids - got: probs.append(f"{len(item_ids - got)} items without an entry")
    badl = [x.get("lead_id") for x in r.get("leads", []) if x.get("lead_id") not in lead_ids]
    if badl: probs.append(f"{len(badl)} lead verdicts naming unknown leads")
    out[bid] = {"ok": not probs, "problems": probs, "spans": len(r.get("spans", [])), "nonblank_lines": sum(len(v) for v in cover.values()),
                "uncovered": unc, "double": dbl, "bad_quotes": bad_quote, "quotes_exact_after_invisible_chars": loose_only, "items": len(item_ids), "leads_judged": len(r.get("leads", [])), "leads": len(lead_ids)}
    print(bid, "OK" if not probs else "PROBLEMS", out[bid]["spans"], "spans;", f"{loose_only} quotes match only after invisible-character normalising;" if loose_only else "", "; ".join(probs))
json.dump(out, open(os.path.join(R, f"{PREFIX}_validation.json" if not want else f"{PREFIX}_validation_partial.json"), "w"), indent=1)
