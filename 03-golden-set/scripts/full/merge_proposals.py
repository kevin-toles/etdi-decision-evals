"""Golden set full run: merge every validated proposal into questions_full.json + candidates_full.jsonl (inputs to
build_records.py with GS_PREFIX=gs-full). Pilot questions are not repeated here — their graded records are merged with
the full run's at the end. Refuses duplicate qids across proposals and any proposal that fails validation (except the
allowed short-slice allocation message).   python3 -I <this>"""
import json, os, subprocess, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE)
qs, cands, seen, bad = [], [], {}, []
for f in sorted(os.listdir(f"{HERE}/proposals")):
    path = f"{HERE}/proposals/{f}"
    r = subprocess.run([sys.executable, "-I", f"{HERE}/validate_proposal.py", path], capture_output=True, text=True)
    probs = [l for l in r.stdout.splitlines() if l and not l.startswith("OK") and "questions, allocation is" not in l]
    if probs: bad.append((f, probs[:3])); continue
    p = json.load(open(path))
    for q in p["questions"]:
        if q["qid"] in seen: bad.append((f, [f"duplicate {q['qid']} also in {seen[q['qid']]}"])); continue
        seen[q["qid"]] = f; qs.append({**q, "slice": p["domain"]})
    cands += [c for c in p["candidates"] if seen.get(c["qid"]) == f]
if bad:
    for b in bad: print("REFUSED", b)
    sys.exit(1)
json.dump({"frozen": "2026-11-15", "rule": "Full run. Questions chosen from per-domain slices by Opus 5.5 proposers before any grading; key points only from accepted / score >= 10 answers, each citing its answer id (extract cuts answers at ~2,000 chars). intended_domains is the coverage plan, not a label.",
           "questions": qs}, open(f"{EV}/questions_full.json", "w"), indent=1, ensure_ascii=False)
with open(f"{EV}/candidates_full.jsonl", "w") as fh:
    for c in cands: fh.write(json.dumps(c, ensure_ascii=False) + "\n")
print("questions", len(qs), "candidates", len(cands))
print("tiers", dict(collections.Counter(q["tier"] for q in qs)))
print("roles", dict(collections.Counter(c["role"] for c in cands)))
print("kf", dict(collections.Counter(c["kf"] for c in cands)))
print("primary domains", len({c["primary"]["domain"] for c in cands}), "| primary cells", len({(c["primary"]["domain"], c["primary"]["subdomain"]) for c in cands}),
      "| all labelled cells", len({(l["domain"], l["subdomain"]) for c in cands for l in [c["primary"]] + c["secondary"]}))
