"""Golden-set panel: checks against human decisions, not model agreement (pilot, 2026-11-15).
Check 2 (cited sources): passages that a vetted answer names as its source must be graded >= 2 with role direct or
foundation by the consensus panel. Check 3 (tag agreement): for passages the panel graded >= 2, the panel's primary or
secondary domain must include a domain reached from the question's Stack Exchange tags. Tags map to the taxonomy by
exact slug match only (tag == domain slug, tag == subdomain slug -> its domain); unmapped tags are reported, never
guessed.   python3 -I <this>"""
import json, os, sys, collections
EV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.environ.get("GS_RUN", "pilot")   # "all" (2026-11-15) = pilot + full run together
raw = {q["qid"]: q for q in json.load(open(f"{EV}/questions_pilot_raw.json"))}
recs = [json.loads(l) for l in open(f"{EV}/records_pilot_graded.jsonl")]
cands = {(c["qid"], c["ref"]): c for c in map(json.loads, open(f"{EV}/candidates_pilot.jsonl"))}
if RUN == "all":
    full_q = {q["qid"] for q in json.load(open(f"{EV}/questions_full.json"))["questions"]}
    for l in open(f"{EV}/full/threads.jsonl"):
        d = json.loads(l)
        if d["qid"] in full_q: raw[d["qid"]] = {"qid": d["qid"], "tags": d["tags"]}
    recs += [json.loads(l) for l in open(f"{EV}/records_full_graded.jsonl")]
    cands.update({(c["qid"], c["ref"]): c for c in map(json.loads, open(f"{EV}/candidates_full.jsonl"))})
tax = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
dom_of = {}
for d in tax["domains"]:
    dom_of[d["slug"]] = d["slug"]
    for s in d["subdomains"]: dom_of.setdefault(s["slug"], d["slug"])

# Check 2 — cited sources (marked in the proposal note as "cited by answer N" / "the paper answer N cites")
print("CHECK 2 — passages a vetted answer cites as its source")
OVR = {o["record_id"]: o for o in json.load(open(f"{EV}/evidence_2026-11-18/evidence_overrides.json"))}
for r in recs:   # evidence overrides (user 2026-11-18, OQ#18 (c)) replace the panel's grade; stand-ins are not the cited work
    if r["record_id"] in OVR: r["panel"] = {**r["panel"], "grade": OVR[r["record_id"]]["grade"], "role": OVR[r["record_id"]]["role"]}
cited = [r for r in recs if "cite" in cands.get((r["qid"], r["chapter_ref"]), {}).get("note", "").lower()
         and "answer" in cands[(r["qid"], r["chapter_ref"])]["note"].lower()
         and not OVR.get(r["record_id"], {}).get("stand_in")]
KEEP = {"gs-full-0527", "gs-full-0827"}   # citing answer contributed no key point; kept as graded (user 2026-11-18)
ok2 = dec = 0; checked = 0
for r in cited:
    p = r["panel"]
    if r["record_id"] in OVR or r["record_id"] in KEEP:   # decided by evidence or by the user: reported, not judged
        dec += 1; print(f"  DECIDED {r['record_id']} {r['qid']:28} grade {p['grade']} ({'evidence' if r['record_id'] in OVR else 'kept: no key point from the citing answer'})"); continue
    checked += 1; good = p["grade"] >= 2 and p["role"] in ("direct", "foundation"); ok2 += good
    print(f"  {'PASS' if good else 'FAIL'} {r['record_id']} {r['qid']:28} grade {p['grade']} role {p['role']:10} {r['chapter_ref'][:60]}")
print(f"  {ok2}/{checked} pass; {dec} decided by evidence or kept")

# Check 3 (rebuilt 2026-11-18, user: the ETDI documents are the source of truth) — reference domains come from the
# verified tables in evidence_2026-11-18/domain_reference.json: Stack Exchange site -> domain and tag -> domain, each mapped
# against the taxonomy manifest with a quote and confirmed by an independent verifier; disputed rows give no reference.
REF = json.load(open(f"{EV}/evidence_2026-11-18/domain_reference.json"))
print("\nCHECK 3 — panel domains vs reference domains (verified site + tag tables), passages graded >= 2")
tot = hit = 0; none = []
for qid, q in raw.items():
    site = qid.split(":")[0]
    ref = {REF["tags"][t] for t in q["tags"] if t in REF["tags"]} | ({REF["sites"][site]} if site in REF["sites"] else set())
    rel = [r for r in recs if r["qid"] == qid and r["panel"]["grade"] >= 2]
    if not ref: none.append(qid); continue
    agree = 0
    for r in rel:
        p = r["panel"]; doms = {p["primary"]["domain"]} | {x["domain"] for x in p["secondary"]}
        if doms & ref: agree += 1
        else: print(f"    miss {r['record_id']} primary {p['primary']['domain']}/{p['primary']['subdomain']} ref {sorted(ref)}")
    tot += len(rel); hit += agree
print(f"  {hit}/{tot} agree; {len(none)} questions with no reference domain")
