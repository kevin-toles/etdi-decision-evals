"""Golden set full run, step 1: candidate question pool (deterministic, read-only on the extract).
Keeps primary-route, unclosed questions whose thread has key-source answers (accepted, or score >= 10) with >= 400 chars,
question score >= 25 on stackoverflow / >= 10 elsewhere. Each question is mapped to taxonomy (domain, subdomain) targets by
its tags (exact subdomain slug, a language alias, or a slug component unique to one subdomain) and to reference domains
(site table + tags matching exactly one domain's anchor text). Writes, per subdomain, the top 12 questions by score.
python3 -I <this> <out.json>"""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sites import SITE
G = "<ETL_RAW_ROOT>/data/stackexchange"
EV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tax = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
pilot = {q["qid"] for q in json.load(open(f"{EV}/questions_pilot.json"))["questions"]}
SUB = {}; comp = collections.defaultdict(set)
for d in tax["domains"]:
    for s in d["subdomains"]:
        SUB[s["slug"]] = (d["slug"], s["slug"])
        for c in s["slug"].split("-"): comp[c].add((d["slug"], s["slug"]))
ALIAS = {"c++": "cpp", "c#": "csharp", "f#": "fsharp", "objective-c": "objective-c", "golang": "go", "vb.net": "visual-basic-dotnet",
         "shell": "bash-shell", "bash": "bash-shell", "node.js": "javascript", "reactjs": "frontend-frameworks",
         "kubernetes": "containers-kubernetes", "docker": "containers-kubernetes", "elasticsearch": "lucene-elasticsearch-solr",
         "lucene": "lucene-elasticsearch-solr", "solr": "lucene-elasticsearch-solr", "llvm": "llvm-ecosystem",
         "garbage-collection": "garbage-collector-implementation", "jit": "jit-compilation", "regex": "string-algorithms",
         "cobol": "mainframe-zos", "jcl": "jcl-batch-processing", "cics": "cics-transaction-processing", "rpgle": "as400-rpg-ecosystem",
         "verilog": "verilog-systemverilog", "vhdl": "vhdl", "fpga": "fpga-development", "solidity": "solidity", "graphql": "graphql",
         "grpc": "grpc", "rest": "rest", "paxos": "consensus-algorithms", "raft": "consensus-algorithms", "cap-theorem": "cap-theorem"}
STOP = {"and", "design", "engineering", "systems", "system", "programming", "development", "foundations", "testing", "data",
        "performance", "optimization", "architecture", "security", "management", "theory", "algorithms", "patterns",
        "processing", "computing", "language", "languages", "tools", "tooling", "process", "platform", "engineering", "web",
        "network", "networking", "app", "release", "store", "models", "model", "learning", "deep", "code", "software"}
idx = [(d["slug"], (d["name"] + " " + d["anchor_text"]).lower()) for d in tax["domains"]] + \
      [(d["slug"], (s["name"] + " " + s.get("anchor_text", "")).lower()) for d in tax["domains"] for s in d["subdomains"]]
dcache = {}
def tag_domain(t):
    if t not in dcache:
        w = t.replace("-", " ").replace(".", " ").lower(); w = w[:-1] if w.endswith("s") else w
        h = {d for d, txt in idx if re.search(r"\b" + re.escape(w) + r"s?\b", txt)}
        dcache[t] = h if len(h) == 1 else set()
    return dcache[t]
def tag_subs(t):
    t = t.lower(); s = ALIAS.get(t, t)
    if s in SUB: return {SUB[s]}
    if t not in STOP and len(comp.get(t, ())) == 1 and len(t) >= 3: return set(comp[t])
    return set()
pool = collections.defaultdict(list); n_seen = n_kept = 0
files = [("stackoverflow.jsonl", 25)] + [(f"primary/{f}", 10) for f in sorted(os.listdir(f"{G}/primary")) if f.endswith(".jsonl")]
for f, min_score in files:
    for line in open(f"{G}/{f}"):
        n_seen += 1
        try: d = json.loads(line)
        except Exception: continue
        if d.get("route") != "primary" or d.get("closed_date") or int(d.get("score", 0)) < min_score: continue
        qid = f"{d['site'].split('.')[0] if d['site'] != 'stackoverflow.com' else 'stackoverflow.com'}:{d['id']}"
        if qid in pilot: continue
        tags = d["tags"]; subs = set().union(*[tag_subs(t) for t in tags]) if tags else set()
        site = d["site"].replace(".stackexchange.com", "")
        ref = set().union(*[tag_domain(t) for t in tags]) if tags else set()
        if site in SITE: ref.add(SITE[site])
        if not subs and not ref: continue
        ans = d["answers"]; acc = str(d.get("accepted_answer_id") or "")
        keys = [a for a in ans if (str(a["id"]) == acc or int(a["score"]) >= 10) and len(a["body"]) >= 400]
        if not keys: continue
        n_kept += 1
        row = {"qid": qid, "file": f, "id": d["id"], "site": site, "title": d["title"], "score": int(d["score"]), "tags": tags,
               "ref_domains": sorted(ref), "n_key_answers": len(keys)}
        targets = subs or {(r, None) for r in ref}
        for dom, sub in targets:
            key = f"{dom}/{sub or '*'}"
            pool[key].append(row)
            if len(pool[key]) > 60: pool[key] = sorted(pool[key], key=lambda r: -r["score"])[:12]
    print(f, n_seen, n_kept, flush=True)
out = {k: sorted(v, key=lambda r: -r["score"])[:12] for k, v in pool.items()}
json.dump({"built": "2026-11-15", "rule": __doc__.strip(), "pool": out}, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
print("subdomain targets with questions:", len(out))
