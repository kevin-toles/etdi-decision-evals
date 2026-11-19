"""Golden set full run: split the pool into one slice per domain with its question allocation.
Allocation: 185 new questions (200 with the 15 pilot ones) — 4 per domain, the remaining 49 in proportion to subdomain
count, capped at 10. A question that maps to several domains is kept only in the slice of the domain with the fewest
distinct questions (scarce domains get first claim), so parallel proposers can never pick the same question.
python3 -I <this>"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
tax = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
pool = json.load(open(f"{HERE}/pool.json"))["pool"]
# Non-technical sites and one generic slug component ("law" -> conways-law) leak in through tag/anchor matching: drop them.
OFF_SITES = {"skeptics", "workplace", "tex", "politics", "music", "photo", "gaming", "hermeneutics", "biology", "chemistry",
             "economics", "linguistics", "mechanics", "3dprinting", "avp", "sound", "bioacoustics", "graphicdesign",
             "elementaryos", "webapps", "opendata", "hardwarerecs", "softwarerecs", "matheducators", "cseducators", "engineering",
             "meta", "ja", "es", "pt", "ru", "blender", "gis", "emacs", "vi", "apple", "askubuntu", "superuser"}
def keep(r, target):
    if r["site"].split(".")[0] in OFF_SITES or r["site"].startswith("meta"): return False
    if target.endswith("/conways-law") and not any("conway" in t for t in r["tags"]): return False
    return True
pool = {k: [r for r in v if keep(r, k)] for k, v in pool.items()}
pool = {k: v for k, v in pool.items() if v}
subs = {d["slug"]: len(d["subdomains"]) for d in tax["domains"]}
TOTAL, FLOOR, CAP = 185, 4, 10
extra = TOTAL - FLOOR * len(subs); tot = sum(subs.values())
alloc = {d: min(CAP, FLOOR + round(extra * n / tot)) for d, n in subs.items()}
os.makedirs(f"{HERE}/slices", exist_ok=True); os.makedirs(f"{HERE}/proposals", exist_ok=True)
print("allocated", sum(alloc.values()))
doms_of = {}
for k, v in pool.items():
    for r in v: doms_of.setdefault(r["qid"], set()).add(k.split("/", 1)[0])
size = {d: len({r["qid"] for k, v in pool.items() if k.split("/", 1)[0] == d for r in v}) for d in subs}
owner = {q: min(ds, key=lambda d: (size[d], d)) for q, ds in doms_of.items()}
for d in subs:
    t = {k.split("/", 1)[1]: [r for r in v if owner[r["qid"]] == d] for k, v in pool.items() if k.split("/", 1)[0] == d}
    t = {k: v for k, v in t.items() if v}
    nq = len({r["qid"] for v in t.values() for r in v})
    json.dump({"domain": d, "allocation": alloc[d], "targets": t}, open(f"{HERE}/slices/{d}.json", "w"), indent=1, ensure_ascii=False)
    print(f"{d:50} alloc {alloc[d]:2}  subdomain targets {len(t):3}  distinct questions {nq:4}")
