"""Golden set pilot: turn candidates_pilot.jsonl (my proposals: ref, spans, key points, role, labels) into records.
Adds, from the corpus and HTC config only: the exact evidence text at each span (re-read via raw_chapters), chapter
metadata, split flag, copies of the same text elsewhere in the corpus (FTS phrase match on a span phrase), and a check
of every label against config/taxonomy_manifest.json. No grades: those are left empty for the review panel.
    cd htc-multidim-classification-service && python3 <this> <candidates.jsonl> <questions.json> <out.jsonl>"""
import json, os, re, sqlite3, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.getcwd())
from gs_search import DB, chapter_text, split_of

cands = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
qs = {q["qid"]: q for q in json.load(open(sys.argv[2]))["questions"]}
tax = json.load(open("config/taxonomy_manifest.json"))
subs = {d["slug"]: {s["slug"] if isinstance(s, dict) else s for s in d["subdomains"]} for d in tax["domains"]}
kfs = {k["slug"] for k in tax["kf_definitions"]}
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
out, problems = [], []

def label_ok(lab):
    if lab["domain"] not in subs: return f"unknown domain {lab['domain']}"
    if lab.get("subdomain") is None: return f"no subdomain chosen under {lab['domain']}"
    if lab["subdomain"] not in subs[lab["domain"]]: return f"subdomain {lab['subdomain']} not under {lab['domain']}"
    return None

for i, c in enumerate(cands, 1):
    row = db.execute("SELECT stem, collection, title, chars FROM chapter WHERE ref=?", (c["ref"],)).fetchone()
    if not row:
        problems.append((i, c["qid"], c["ref"], "ref not in index")); continue
    stem, coll, title, chars = row
    text = chapter_text(coll, stem, c["ref"])
    ev = [{"start": s, "len": n, "text": re.sub(r"\s+", " ", text[s:s + n]).strip()} for s, n in c["spans"]]
    # copies: 8 consecutive words from the middle of the first span, as an FTS phrase
    # consecutive ASCII word tokens only (ligatures and symbols break FTS phrase adjacency)
    toks = re.findall(r"\w+", ev[0]["text"]); copies = []
    runs = [toks[j:j + 8] for j in range(len(toks) // 3, len(toks) - 8) if all(t.isascii() and t.isalpha() for t in toks[j:j + 8])]
    if runs:
        phrase = " ".join(runs[0])
        for ref2, ch2 in db.execute("SELECT c.ref, c.chars FROM fts JOIN chapter c ON c.id = fts.rowid WHERE fts MATCH ? LIMIT 40", (f'"{phrase}"',)):
            if ref2 != c["ref"]: copies.append({"ref": ref2, "same_length": ch2 == chars, "split": split_of(ref2)})
    for lab in [c["primary"]] + c["secondary"]:
        err = label_ok(lab)
        if err: problems.append((i, c["qid"], c["ref"], err))
    if c["kf"] not in kfs or (c.get("kf_alt") and c["kf_alt"] not in kfs): problems.append((i, c["qid"], c["ref"], "bad kf"))
    bad_k = [k for k in c["covers"] if k not in {kp["id"] for kp in qs[c["qid"]]["key_points"]}]
    if bad_k: problems.append((i, c["qid"], c["ref"], f"unknown key points {bad_k}"))
    out.append({"record_id": f"{os.environ.get('GS_PREFIX', 'gs-pilot')}-{i:04d}" if os.environ.get("GS_PREFIX") else f"gs-pilot-{i:03d}", "qid": c["qid"], "tier": qs[c["qid"]]["tier"], "query": qs[c["qid"]]["query"],
                "collection": coll, "chapter_ref": c["ref"], "chapter_title": title, "chapter_chars": chars,
                "split": split_of(c["ref"]), "evidence": ev, "copies": copies,
                "proposed": {"covers_key_points": c["covers"], "role": c["role"], "knowledge_function": c["kf"],
                             "knowledge_function_alt": c.get("kf_alt"), "primary": c["primary"], "secondary": c["secondary"],
                             "note": c["note"]},
                "panel": {"grade": None, "role": None, "labels": None, "votes": []}})

with open(sys.argv[3], "w") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("records", len(out), "| problems", len(problems))
for p in problems: print("  PROBLEM", p)
print("by tier", dict(Counter(r["tier"] for r in out)))
print("by role", dict(Counter(r["proposed"]["role"] for r in out)))
print("by KF", dict(Counter(r["proposed"]["knowledge_function"] for r in out)))
print("by split", dict(Counter(r["split"] for r in out)))
print("by collection", dict(Counter(r["collection"] for r in out)))
print("records with copies", sum(1 for r in out if r["copies"]), "| total copy refs", sum(len(r["copies"]) for r in out),
      "| copies that are heldout", sum(1 for r in out for c in r["copies"] if c["split"] == "heldout"))
print("primary domains", len({r["proposed"]["primary"]["domain"] for r in out}), "| primary (domain,subdomain) cells",
      len({(r["proposed"]["primary"]["domain"], r["proposed"]["primary"]["subdomain"]) for r in out}))
allcells = {(l["domain"], l["subdomain"]) for r in out for l in [r["proposed"]["primary"]] + r["proposed"]["secondary"]}
print("all labelled (domain,subdomain) cells incl. secondary", len(allcells), "| domains", len({d for d, _ in allcells}))
for q in qs:
    rs = [r for r in out if r["qid"] == q]; cov = {k for r in rs if r["proposed"]["role"] != "distractor" for k in r["proposed"]["covers_key_points"]}
    print(f"  {q:32} n={len(rs):2}  key points covered {sorted(cov)} of {[k['id'] for k in qs[q]['key_points']]}")
