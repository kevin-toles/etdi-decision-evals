"""Golden set: merge pilot + full-run consensus records and export the RetrievalQualityHarness file (ETDI design
§5.1.9.32: JSON list of {query_id, text, relevant: {chapter_id: 0-3}}). chapter_ref '<stem>#<n>' -> chapter_id
'<stem>:ch<n>' (BEH-01.09: book_id = raw stem). Copies (user decision 2026-11-18, OQ#18 (b)): a copy verified by
copies_verify.py (>= 90% of the graded chapter's 8-word shingles plus every evidence span) takes the graded chapter's
grade; an unverified or unreadable copy is listed under `excluded` — neither relevant nor a miss. Also writes golden_set_v1.jsonl (every graded record, both runs,
with votes and HTC labels).   python3 -I <this>"""
import json, os, collections
EV = os.path.dirname(os.path.abspath(__file__))
recs = [json.loads(l) for l in open(f"{EV}/records_pilot_graded.jsonl")] + [json.loads(l) for l in open(f"{EV}/records_full_graded.jsonl")]
qs = {q["qid"]: q for q in json.load(open(f"{EV}/questions_pilot.json"))["questions"]}
qs.update({q["qid"]: q for q in json.load(open(f"{EV}/questions_full.json"))["questions"]})
def cid(ref):
    stem, n = ref.rsplit("#", 1); return f"{stem}:ch{n}"
copies = [json.loads(l) for l in open(f"{EV}/copies_verified.jsonl")]
# Evidence-decided grades (user 2026-11-18, OQ#18 (c)): research + independent verifier + verbatim quote check override the panel.
overrides = {o["record_id"]: o for o in json.load(open(f"{EV}/evidence_2026-11-18/evidence_overrides.json"))}
for r in recs:
    if r["record_id"] in overrides:
        o = overrides[r["record_id"]]
        r["panel"] = {**r["panel"], "grade": o["grade"], "role": o["role"], "resolution": "evidence", "evidence": o}
# Evidence overrides (OQ#18 cited-source rule (c), user 2026-11-18): grades decided by verified evidence replace the panel's
overrides = {o["record_id"]: o for o in json.load(open(f"{EV}/evidence_2026-11-18/evidence_overrides.json"))}
for r in recs:
    if r["record_id"] in overrides:
        o = overrides[r["record_id"]]; r["panel"] = {**r["panel"], "grade": o["grade"], "role": o["role"], "evidence_override": o}
out = collections.OrderedDict()
for r in recs:
    q = qs[r["qid"]]
    e = out.setdefault(r["qid"], {"query_id": r["qid"], "text": q["query"], "tier": q["tier"], "relevant": {}})
    k = cid(r["chapter_ref"]); g = r["panel"]["grade"]
    e["relevant"][k] = max(g, e["relevant"].get(k, 0))
for c in copies:
    e = out[c["qid"]]; k = cid(c["copy_ref"])
    if c["verified"]:
        e["relevant"][k] = max(c["grade"], e["relevant"].get(k, 0))
for c in copies:
    e = out[c["qid"]]; k = cid(c["copy_ref"])
    if not c["verified"] and k not in e["relevant"]:
        e.setdefault("excluded", [])
        if k not in e["excluded"]: e["excluded"].append(k)
json.dump(list(out.values()), open(f"{EV}/golden_queries.json", "w"), indent=1, ensure_ascii=False)
print("verified copies added", sum(c["verified"] for c in copies), "| excluded ids", sum(len(e.get("excluded", [])) for e in out.values()))
with open(f"{EV}/golden_set_v1.jsonl", "w") as f:
    for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
G = collections.Counter(g for e in out.values() for g in e["relevant"].values())
print("queries", len(out), "| judgments", sum(G.values()), "| grades", sorted(G.items()),
      "| queries with a grade-3", sum(3 in e["relevant"].values() for e in out.values()),
      "| with no grade>=2", [e["query_id"] for e in out.values() if max(e["relevant"].values()) < 2])
print("tiers", dict(collections.Counter(e["tier"] for e in out.values())))
