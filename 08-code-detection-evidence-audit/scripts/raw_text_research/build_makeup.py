"""Make-up sheet for research spans whose quote_first / quote_last differ from the cited line even after
invisible-character normalising (validate_research.py's failing tier). Each entry gives the span as written and the
page's numbered lines; a reviewer re-cites the span (same kind unless the text shows otherwise).
    python3 build_makeup.py <dir>"""
import glob, json, os, sys, unicodedata
R = sys.argv[1]
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())
out = []
for f in sorted(glob.glob(os.path.join(R, "research_B*.json"))):
    bid = os.path.basename(f)[9:-5]; s = json.load(open(os.path.join(R, f"sheet_{bid}.json"))); r = json.load(open(f), strict=False)
    P = {(d["doc"], p["page"]): {l["n"]: l["text"] for l in p["lines"]} for d in s["documents"] for p in d["pages"]}
    for i, x in enumerate(r["spans"]):
        L = P.get((x.get("doc"), x.get("page")))
        if not L or x.get("line_start") not in L or x.get("line_end") not in L: continue
        bad = [k for k, n in (("quote_first", "line_start"), ("quote_last", "line_end")) if loose(L[x[n]]) != loose(x.get(k))]
        if bad:
            out.append({"makeup_id": f"{bid}-S{i}", "batch": bid, "span_index": i, "doc": x["doc"], "page": x["page"], "span_as_written": x,
                        "failing": bad, "page_lines": [{"n": n, "text": t} for n, t in sorted(L.items())]})
json.dump({"items": out}, open(os.path.join(R, "makeup_sheet.json"), "w"), indent=1, ensure_ascii=False)
print(len(out), "spans:", [o["makeup_id"] for o in out])
