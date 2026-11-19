"""Check one verdict file against its sheet: every item graded, rubric.validate clean. python3 -I <this> <tag-n> [run=full]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rubric
H = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(H)
run = sys.argv[2] if len(sys.argv) > 2 else "full"
for name in sys.argv[1].split(","):
    sh = json.load(open(f"{H}/sheets/{run}/{name}.json")); vp = f"{H}/verdicts/{run}/{name}.json"
    if not os.path.exists(vp): print(name, "MISSING"); continue
    v = json.load(open(vp))["verdicts"]; ids = {i["item_id"]: i for i in sh["items"]}
    missing = sorted(set(ids) - set(v)); bad = {}
    for iid, a in v.items():
        it = ids.get(iid)
        if not it: bad[iid] = ["unknown item"]; continue
        p = rubric.validate(a, {"key_points": [{"id": k} for k in it["key_point_ids"]]})
        if p: bad[iid] = p
    print(name, f"{len(v)}/{len(ids)}", "missing", missing[:5], "invalid", len(bad), list(bad.items())[:2])
