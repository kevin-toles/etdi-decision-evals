"""Golden set full run: check one proposer slice file before it is accepted. Prints problems; exit 1 if any.
python3 -I <this> full/proposals/<domain>.json"""
import json, os, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE)
sys.path.insert(0, f"{EV}/panel")
from rubric import DOMAINS, KFS
DB = "<WORK_DIR>/chapters_fts_v2.sqlite"
p = json.load(open(sys.argv[1])); dom = os.path.basename(sys.argv[1])[:-5]
sl = json.load(open(f"{HERE}/slices/{dom}.json"))
threads = {}
for line in open(f"{HERE}/threads.jsonl"):
    d = json.loads(line); threads[d["qid"]] = d
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
P = []
qs = p.get("questions", []); qids = [q["qid"] for q in qs]
if len(qs) != sl["allocation"]: P.append(f"{len(qs)} questions, allocation is {sl['allocation']}")
if len(set(qids)) != len(qids): P.append("duplicate qids")
slice_q = {r["qid"] for rows in sl["targets"].values() for r in rows}
for q in qs:
    t = q["qid"]
    if t not in slice_q: P.append(f"{t}: not in this slice")
    if t not in threads: P.append(f"{t}: no thread"); continue
    th = threads[t]; acc = str(th.get("accepted_answer_id") or "")
    ok_src = {str(a["id"]) for a in th["answers"] if str(a["id"]) == acc or int(a["score"]) >= 10}
    if q.get("tier") not in ("senior", "principal", "distinguished"): P.append(f"{t}: bad tier {q.get('tier')}")
    if not q.get("query"): P.append(f"{t}: no query")
    kps = q.get("key_points", [])
    if not 2 <= len(kps) <= 7: P.append(f"{t}: {len(kps)} key points (want 2-7)")
    for k in kps:
        bad = set(map(str, k.get("src", []))) - ok_src
        if not k.get("src") or bad: P.append(f"{t} {k.get('id')}: src {sorted(bad) or 'empty'} not a key-source answer {sorted(ok_src)}")
    kid = {k["id"] for k in kps}
    for d in q.get("intended_domains", []):
        if d not in DOMAINS: P.append(f"{t}: intended domain {d} unknown")
cands = p.get("candidates", [])
by_q = {}
for c in cands:
    t = c.get("qid"); by_q.setdefault(t, []).append(c)
    if t not in qids: P.append(f"candidate for unknown qid {t}"); continue
    row = db.execute("SELECT chars FROM chapter WHERE ref=?", (c.get("ref"),)).fetchone()
    if not row: P.append(f"{t}: ref not in index: {c.get('ref')!r:.90}"); continue
    for s in c.get("spans", []):
        if not (isinstance(s, list) and len(s) == 2 and 0 <= s[0] < row[0] and s[1] > 0): P.append(f"{t}: bad span {s} ({row[0]} chars) {c['ref'][:50]}")
    if not c.get("spans"): P.append(f"{t}: no spans {c['ref'][:50]}")
    kid = {k["id"] for q in qs if q["qid"] == t for k in q["key_points"]}
    if set(c.get("covers", [])) - kid: P.append(f"{t}: covers unknown {sorted(set(c['covers']) - kid)}")
    if c.get("role") not in ("direct", "foundation", "distractor"): P.append(f"{t}: bad role {c.get('role')}")
    if c.get("kf") not in KFS: P.append(f"{t}: bad kf {c.get('kf')}")
    if c.get("kf_alt") not in (None, *KFS): P.append(f"{t}: bad kf_alt {c.get('kf_alt')}")
    for lab in [c.get("primary") or {}] + list(c.get("secondary") or []):
        if lab.get("domain") not in DOMAINS: P.append(f"{t}: unknown domain {lab.get('domain')}")
        elif lab.get("subdomain") not in DOMAINS[lab["domain"]]: P.append(f"{t}: {lab.get('subdomain')} not under {lab['domain']}")
for t in qids:
    cs = by_q.get(t, []); roles = [c["role"] for c in cs]
    if len(cs) < 6: P.append(f"{t}: {len(cs)} candidates (want >= 6)")
    if roles.count("direct") < 2: P.append(f"{t}: fewer than 2 direct")
    if "distractor" not in roles: P.append(f"{t}: no distractor")
    if len({c['ref'] for c in cs}) != len(cs): P.append(f"{t}: duplicate refs")
print("\n".join(P) if P else f"OK {dom}: {len(qs)} questions, {len(cands)} candidates")
sys.exit(1 if P else 0)
