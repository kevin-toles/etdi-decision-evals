"""Make-up sheets for the second blind read (research2_<batch>.json, claude-opus-4-8). Two kinds of entry, one page each:
  RECITE  a span whose quote_first / quote_last differ from the cited line even after invisible-character normalising.
          The span is shown as written; the reviewer re-cites it (kind unchanged unless the text shows otherwise).
  GAP     non-blank lines no valid span covers (skipped pages, out-of-range spans, stray lines). The reviewer marks
          spans covering exactly those lines, judging from the page text. It is not shown the other read's kinds.
Items with no entry in a research2 file are listed so their lines are covered by a GAP entry for the item's page.
Pages are grouped into make-up sheets of at most ~20 pages / ~120K characters (makeup2_Mxx.txt + makeup2_index.json).
    python3 build_makeup2.py <dir>"""
import glob, json, os, sys, unicodedata
R = sys.argv[1]
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())
entries = []; missing_items = []
for f in sorted(glob.glob(os.path.join(R, "research2_B*.json"))):
    bid = os.path.basename(f)[10:-5]; s = json.load(open(os.path.join(R, f"sheet_{bid}.json"))); r = json.load(open(f), strict=False)
    P = {(d["doc"], p["page"]): {l["n"]: l["text"] for l in p["lines"]} for d in s["documents"] for p in d["pages"]}
    cov = {k: set() for k in P}
    for i, x in enumerate(r.get("spans", [])):
        k = (x.get("doc"), x.get("page")); L = P.get(k); a, z = x.get("line_start"), x.get("line_end")
        if not L or not (isinstance(a, int) and isinstance(z, int) and a <= z and a in L and z in L): continue   # invalid span: its lines fall to GAP
        cov[k].update(range(a, z + 1))
        bad = [q for q, n in (("quote_first", a), ("quote_last", z)) if loose(L[n]) != loose(x.get(q))]
        if bad: entries.append({"id": f"{bid}-S{i}", "type": "RECITE", "batch": bid, "doc": k[0], "page": k[1], "span_index": i, "span_as_written": x, "failing": bad})
    docix = {d["doc"]: j for j, d in enumerate(s["documents"], 1)}
    for k, L in P.items():
        gap = sorted(n for n, t in L.items() if loose(t) and n not in cov[k])
        if gap:
            runs = [];
            for n in gap:
                if runs and n == runs[-1][1] + 1: runs[-1][1] = n
                else: runs.append([n, n])
            entries.append({"id": f"{bid}-D{docix[k[0]]}-G{k[1]}", "type": "GAP", "batch": bid, "doc": k[0], "page": k[1], "runs": runs, "lines": len(gap)})
    got = {x.get("item") for x in r.get("items", [])}
    for d in s["documents"]:
        for it in d["items"]:
            if it["item"] not in got: missing_items.append({"batch": bid, "item": it["item"], "doc": d["doc"], "page": it["page_start"], "line_start": it["line_start"], "line_end": it["line_end"]})
pages = {}
for e in entries: pages.setdefault((e["batch"], e["doc"], e["page"]), []).append(e)
sheets, cur, size = [], [], 0
for key, es in pages.items():
    b, doc, pg = key; L = {(d["doc"], p["page"]): p["lines"] for d in json.load(open(os.path.join(R, f"sheet_{b}.json")))["documents"] for p in d["pages"]}[(doc, pg)]
    n = sum(len(l["text"]) + 12 for l in L)
    if cur and (len(cur) >= 20 or size + n > 120000): sheets.append(cur); cur, size = [], 0
    cur.append((key, es, L)); size += n
if cur: sheets.append(cur)
index = []
for si, sh in enumerate(sheets, 1):
    mid = f"M{si:02d}"; out = []
    for (b, doc, pg), es, L in sh:
        out.append(f"######## PAGE: batch {b} | DOCUMENT: {doc} | page {pg}")
        for e in es:
            if e["type"] == "RECITE":
                x = e["span_as_written"]
                out.append(f"--- RECITE {e['id']}: span as written lines {x.get('line_start')}-{x.get('line_end')} kind {x.get('kind')}; failing {', '.join(e['failing'])}")
                out.append(f"    quote_first as written | {x.get('quote_first')}"); out.append(f"    quote_last as written  | {x.get('quote_last')}")
                if x.get("note"): out.append(f"    note as written | {x.get('note')}")
            else:
                out.append(f"--- GAP {e['id']}: mark spans covering exactly lines " + ", ".join(f"{a}-{z}" if a != z else f"{a}" for a, z in e["runs"]))
        for l in L: out.append(f"p{pg} L{l['n']} | {l['text']}")
        out.append("")
        index.append({"sheet": mid, "batch": b, "doc": doc, "page": pg, "entries": [e["id"] for e in es]})
    open(os.path.join(R, f"makeup2_{mid}.txt"), "w").write("\n".join(out))
json.dump({"entries": entries, "missing_items": missing_items, "index": index}, open(os.path.join(R, "makeup2_index.json"), "w"), indent=1, ensure_ascii=False)
print(f"{sum(e['type']=='RECITE' for e in entries)} RECITE spans, {sum(e['type']=='GAP' for e in entries)} GAP pages ({sum(e.get('lines',0) for e in entries)} lines), {len(missing_items)} items without entry, {len(sheets)} sheets")
