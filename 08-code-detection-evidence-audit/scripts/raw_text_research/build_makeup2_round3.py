"""Third make-up round for read 2, computed on read 2 *with* the validated make-up applied (as compare_reads.py does):
GAP  -r3  non-blank lines still covered by no span (mostly lines a make-up re-cite released when it moved a boundary);
RECITE -r3  re-cites that failed in both earlier rounds (quote mismatch only).
Also reports lines covered twice after make-up. Writes makeup2_M08.txt and appends entries to makeup2_index.json.
    python3 build_makeup2_round3.py <dir>"""
import collections, glob, json, os, sys, unicodedata
R = sys.argv[1]
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())
ix = json.load(open(os.path.join(R, "makeup2_index.json"))); v = json.load(open(os.path.join(R, "makeup2_validation.json")))["entries"]
mi = {e["id"]: e for e in ix["entries"]}; MK = collections.defaultdict(list)
for f in glob.glob(os.path.join(R, "makeup2_research_M*.json")):
    m = json.load(open(f), strict=False)
    for x in m.get("recites", []) + [dict(s, id=g["id"]) for g in m.get("gaps", []) for s in g.get("spans", [])]:
        e = mi.get(x.get("id"))
        if e and v.get(e["id"], {}).get("ok"): MK[e["batch"]].append((e, x))
new, dbl = [], []
for f in sorted(glob.glob(os.path.join(R, "research2_B*.json"))):
    b = os.path.basename(f)[10:-5]; sh = json.load(open(os.path.join(R, f"sheet_{b}.json"))); sp = json.load(open(f), strict=False)["spans"]
    docix = {d["doc"]: j for j, d in enumerate(sh["documents"], 1)}
    P = {(d["doc"], p["page"]): {l["n"]: l["text"] for l in p["lines"]} for d in sh["documents"] for p in d["pages"]}
    drop = {e["span_index"] for e, _ in MK[b] if e["type"] == "RECITE"}
    allsp = [s for i, s in enumerate(sp) if i not in drop] + [dict(x, doc=e["doc"], page=e["page"]) for e, x in MK[b]]
    cov = collections.Counter()
    for s in allsp:
        k = (s.get("doc"), s.get("page")); L = P.get(k); a, z = s.get("line_start"), s.get("line_end")
        if not L or not (isinstance(a, int) and isinstance(z, int) and a <= z and a in L and z in L): continue
        for n in range(a, z + 1):
            if loose(L[n]): cov[(k, n)] += 1
    for k, L in P.items():
        gap = sorted(n for n, t in L.items() if loose(t) and cov[(k, n)] == 0)
        dbl += [(b, k[0], k[1], n) for n in L if cov[(k, n)] > 1]
        if gap:
            runs = []
            for n in gap:
                if runs and n == runs[-1][1] + 1: runs[-1][1] = n
                else: runs.append([n, n])
            new.append({"id": f"{b}-D{docix[k[0]]}-G{k[1]}-r3", "type": "GAP", "batch": b, "doc": k[0], "page": k[1], "runs": runs, "lines": len(gap)})
base = {e["id"].removesuffix("-r2") for e in ix["entries"] if e["id"].endswith("-r2") and not v.get(e["id"], {}).get("ok")}
for i in sorted(base):
    e = mi[i]; new.append(dict(e, id=i + "-r3"))
pages = collections.defaultdict(list)
for e in new: pages[(e["batch"], e["doc"], e["page"])].append(e)
out = []
for (b, doc, pg), es in pages.items():
    L = {(d["doc"], p["page"]): p["lines"] for d in json.load(open(os.path.join(R, f"sheet_{b}.json")))["documents"] for p in d["pages"]}[(doc, pg)]
    out.append(f"######## PAGE: batch {b} | DOCUMENT: {doc} | page {pg}")
    for e in es:
        if e["type"] == "RECITE":
            x = e["span_as_written"]
            out.append(f"--- RECITE {e['id']}: span as written lines {x.get('line_start')}-{x.get('line_end')} kind {x.get('kind')}; failing {', '.join(e['failing'])}")
            out.append(f"    quote_first as written | {x.get('quote_first')}"); out.append(f"    quote_last as written  | {x.get('quote_last')}")
        else:
            out.append(f"--- GAP {e['id']}: mark spans covering exactly lines " + ", ".join(f"{a}-{z}" if a != z else f"{a}" for a, z in e["runs"]))
    out += [f"p{pg} L{l['n']} | {l['text']}" for l in L] + [""]
    ix["index"].append({"sheet": "M08", "batch": b, "doc": doc, "page": pg, "entries": [e["id"] for e in es]})
ix["entries"] += new
open(os.path.join(R, "makeup2_M08.txt"), "w").write("\n".join(out)); json.dump(ix, open(os.path.join(R, "makeup2_index.json"), "w"), indent=1, ensure_ascii=False)
print(sum(e["type"] == "GAP" for e in new), "GAP pages,", sum(e.get("lines", 0) for e in new), "lines;", sum(e["type"] == "RECITE" for e in new), "RECITE;", len(dbl), "lines covered twice:", dbl[:10])
