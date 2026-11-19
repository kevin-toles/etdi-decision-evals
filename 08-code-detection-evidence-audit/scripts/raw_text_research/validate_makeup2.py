"""Mechanical check of makeup2_research_<sheet>.json against makeup2_index.json and the batch sheets (no judgement):
model id; every entry answered once; kinds; lines on the page; quotes verbatim (loose tier as validate_research.py);
GAP spans cover exactly the gap lines (each non-blank gap line once, nothing outside). Writes makeup2_validation.json.
    python3 validate_makeup2.py <dir>"""
import glob, json, os, sys, unicodedata
R = sys.argv[1]; MODEL = "claude-opus-4-8"; KINDS = {"code", "noncode_monospace", "prose"}
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())
ix = json.load(open(os.path.join(R, "makeup2_index.json"))); E = {e["id"]: e for e in ix["entries"]}
sheet_of = {eid: r["sheet"] for r in ix["index"] for eid in r["entries"]}
pages = {}
def page(b, doc, pg):
    if b not in pages: pages[b] = {(d["doc"], p["page"]): {l["n"]: l["text"] for l in p["lines"]} for d in json.load(open(os.path.join(R, f"sheet_{b}.json")))["documents"] for p in d["pages"]}
    return pages[b][(doc, pg)]
def qok(L, x):
    a, z = x.get("line_start"), x.get("line_end")
    if not (isinstance(a, int) and isinstance(z, int) and a <= z and a in L and z in L): return "lines"
    if x.get("kind") not in KINDS: return "kind"
    if loose(L[a]) != loose(x.get("quote_first")) or loose(L[z]) != loose(x.get("quote_last")): return "quote"
    return None
out = {"sheets": {}, "entries": {}}; answered = set()
for f in sorted(glob.glob(os.path.join(R, "makeup2_research_M*.json"))):
    sid = os.path.basename(f)[17:-5]; probs = []
    try: m = json.load(open(f), strict=False)
    except Exception as e: out["sheets"][sid] = [f"unreadable: {e}"]; print(sid, "UNREADABLE", e); continue
    if m.get("model") != MODEL: probs.append(f"model {m.get('model')}")
    for x in m.get("recites", []):
        e = E.get(x.get("id"))
        if not e or e["type"] != "RECITE" or sheet_of.get(e["id"]) != sid: probs.append(f"unknown recite {x.get('id')}"); continue
        answered.add(e["id"]); err = qok(page(e["batch"], e["doc"], e["page"]), x)
        out["entries"][e["id"]] = {"ok": err is None, "problem": err, "changed": x.get("changed")}
    for g in m.get("gaps", []):
        e = E.get(g.get("id"))
        if not e or e["type"] != "GAP" or sheet_of.get(e["id"]) != sid: probs.append(f"unknown gap {g.get('id')}"); continue
        answered.add(e["id"]); L = page(e["batch"], e["doc"], e["page"])
        want = {n for a, z in e["runs"] for n in range(a, z + 1) if loose(L.get(n, ""))}; got = []; errs = []
        for s in g.get("spans", []):
            err = qok(L, s)
            if err: errs.append(err); continue
            got += [n for n in range(s["line_start"], s["line_end"] + 1) if loose(L[n])]
        extra = set(got) - want; dup = len(got) - len(set(got)); miss = want - set(got)
        ok = not errs and not extra and not dup and not miss
        out["entries"][e["id"]] = {"ok": ok, "problem": None if ok else f"span errors {errs}; {len(miss)} gap lines missing; {len(extra)} outside gap; {dup} doubled"}
    bad = [k for k, v in out["entries"].items() if sheet_of.get(k) == sid and not v["ok"]]
    out["sheets"][sid] = probs + ([f"{len(bad)} entries failing: {bad}"] if bad else [])
    print(sid, "OK" if not out["sheets"][sid] else "PROBLEMS", "; ".join(out["sheets"][sid]))
miss = sorted(set(E) - answered); out["unanswered"] = miss
print(len(answered), "of", len(E), "entries answered;", sum(v["ok"] for v in out["entries"].values()), "pass;", "unanswered:", miss[:20])
json.dump(out, open(os.path.join(R, "makeup2_validation.json"), "w"), indent=1)
