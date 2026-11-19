"""Mechanical check of check_<batch>.json files (no judgement): model id, batch id, one verdict per research span
(index 0..n-1, no gaps or extras), allowed verdicts, corrected kind / lines present and on the page when a verdict
says kind_wrong / boundary_wrong, lead checks name real lead verdicts. Prints one row per batch, writes
check_validation.json.
    python3 validate_checks.py <dir> [batch ...]"""
import glob, json, os, sys
R = sys.argv[1]; want = sys.argv[2:]
KINDS = {"code", "noncode_monospace", "prose"}; V = {"confirm", "kind_wrong", "boundary_wrong"}; out = {}
for f in sorted(glob.glob(os.path.join(R, "check_B*.json"))):
    bid = os.path.basename(f)[6:-5]
    if want and bid not in want: continue
    probs = []
    try: c = json.load(open(f), strict=False)
    except Exception as e: out[bid] = {"ok": False, "problems": [f"unreadable: {e}"]}; print(bid, "UNREADABLE", e); continue
    r = json.load(open(os.path.join(R, f"research_B{bid[1:]}.json")), strict=False)
    sheet = json.load(open(os.path.join(R, f"sheet_{bid}.json")))
    pages = {(d["doc"], p["page"]): {l["n"] for l in p["lines"]} for d in sheet["documents"] for p in d["pages"]}
    if c.get("model") != "claude-opus-5-5": probs.append(f"model {c.get('model')}")
    if c.get("batch") != bid: probs.append(f"batch {c.get('batch')}")
    n = len(r.get("spans", [])); idx = [x.get("index") for x in c.get("span_checks", [])]
    if sorted(i for i in idx if isinstance(i, int)) != list(range(n)): probs.append(f"span_checks cover {len(set(i for i in idx if isinstance(i, int)) & set(range(n)))}/{n} spans ({len(idx)} entries)")
    bad = 0
    for x in c.get("span_checks", []):
        v = x.get("verdict")
        if v not in V: bad += 1; continue
        i = x.get("index")
        if not isinstance(i, int) or not 0 <= i < n: continue
        s = r["spans"][i]
        if v == "kind_wrong" and x.get("kind") not in KINDS: bad += 1
        if v == "boundary_wrong":
            a, z = x.get("line_start"), x.get("line_end"); L = pages.get((s.get("doc"), s.get("page")), set())
            if not (isinstance(a, int) and isinstance(z, int) and a <= z and a in L and z in L): bad += 1
    if bad: probs.append(f"{bad} span checks with an invalid verdict or correction")
    lead_ids = {x.get("lead_id") for x in r.get("leads", [])}
    badl = [x for x in c.get("lead_checks", []) if x.get("lead_id") not in lead_ids or x.get("verdict") not in ("confirm", "dispute")]
    if badl: probs.append(f"{len(badl)} lead checks naming unknown lead verdicts or bad verdicts")
    from collections import Counter
    vc = Counter(x.get("verdict") for x in c.get("span_checks", []))
    out[bid] = {"ok": not probs, "problems": probs, "spans": n, "verdicts": dict(vc), "uncovered_reported": len(c.get("uncovered", []))}
    print(bid, "OK" if not probs else "PROBLEMS", dict(vc), "; ".join(probs))
json.dump(out, open(os.path.join(R, "check_validation.json" if not want else "check_validation_partial.json"), "w"), indent=1)
