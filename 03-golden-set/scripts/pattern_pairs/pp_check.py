"""Validate, gate and resolve pattern-pair verdicts. Thresholds pre-registered 2026-11-18 (user-approved) before any verdict.

  check  <verdict.json> <sheet.json>        -> problems found (missing ids, bad grade, technique or slug not in lists)
  gate   <label_sample_dir> <model>         -> planted-pair gate for one judge over all its verdict files
  route  <label_sample_dir>                 -> items needing Fable (Sonnet and Opus grades disagree) -> fable_queue.json
  final  <label_sample_dir>                 -> consensus.jsonl

Resolution rule (b): Fable 5.2 judges only items whose two grades disagree; final grade = majority of three, Fable
breaks a three-way tie. technique / primary per problem = the two judges' value when they agree, else recorded as
split (both values kept, not resolved). Secondaries: union of the two judges' lists, each tagged with its votes.
"""
import glob, json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
INS = open(os.path.join(HERE, "PAIR_GRADER_INSTRUCTIONS.md")).read()
TECH = {t.strip() for t in re.search(r"TECHNIQUES \(choose exactly one per problem\): (.*)", INS).group(1).split(", ")}
TAX = {}
for m in re.finditer(r"^- ([a-z0-9-]+): (.*)$", INS[INS.index("TAXONOMY"):], re.M):
    TAX[m.group(1)] = {s.strip() for s in m.group(2).split(",")}
GATE = {"same_grade3_min": 0.90, "different_grade0_min": 0.90, "different_grade0or1_min": 0.97}
J = {"sonnet": "claude-sonnet-5-5", "opus": "claude-opus-4-8", "fable": "claude-fable-5-2"}

def norm_slug(x):   # pilot sheets wrote secondaries as "domain/subdomain" strings before the format was spelled out
    if isinstance(x, str) and x.count("/") == 1: d, s = x.split("/"); return {"domain": d, "subdomain": s}
    return x
def slug_ok(x):
    x = norm_slug(x); return isinstance(x, dict) and x.get("domain") in TAX and x.get("subdomain") in TAX[x["domain"]]

def check(vpath, spath):
    v = json.load(open(vpath))["verdicts"]; ids = [i["item_id"] for i in json.load(open(spath))["items"]]
    bad = [f"missing {i}" for i in ids if i not in v]
    for i in ids:
        if i not in v: continue
        r = v[i]
        if r.get("grade") not in (0, 1, 2, 3): bad.append(f"{i} grade {r.get('grade')}")
        for s in "ab":
            if r.get(f"technique_{s}") not in TECH: bad.append(f"{i} technique_{s} {r.get(f'technique_{s}')}")
            if not slug_ok(r.get(f"primary_{s}")): bad.append(f"{i} primary_{s} {r.get(f'primary_{s}')}")
            for x in r.get(f"secondary_{s}") or []:
                if not slug_ok(x): bad.append(f"{i} secondary_{s} {x}")
    return bad

def load(ls, model):
    out = {}
    for f in sorted(glob.glob(f"{ls}/verdicts/{model}/pp-*.json")):
        out.update(json.load(open(f))["verdicts"])
    return out

def gate(ls, model):
    v = load(ls, model); pk = [json.loads(l) for l in open(f"{ls}/planted_key.jsonl")]
    g = {k: [v[p["pair_id"]]["grade"] for p in pk if p["planted"] == k and p["pair_id"] in v] for k in ("same", "different")}
    res = {"model": model, "n_same": len(g["same"]), "n_different": len(g["different"]),
           "same_grade3": sum(x == 3 for x in g["same"]) / max(1, len(g["same"])),
           "different_grade0": sum(x == 0 for x in g["different"]) / max(1, len(g["different"])),
           "different_grade0or1": sum(x <= 1 for x in g["different"]) / max(1, len(g["different"]))}
    res["pass"] = (res["same_grade3"] >= GATE["same_grade3_min"] and res["different_grade0"] >= GATE["different_grade0_min"]
                   and res["different_grade0or1"] >= GATE["different_grade0or1_min"])
    res["thresholds"] = GATE
    return res

def route(ls):
    s, o = load(ls, "sonnet"), load(ls, "opus")
    q = sorted(i for i in s if i in o and s[i]["grade"] != o[i]["grade"])
    json.dump(q, open(f"{ls}/fable_queue.json", "w")); return {"both_judged": sum(i in o for i in s), "to_fable": len(q)}

def final(ls):
    s, o, f = load(ls, "sonnet"), load(ls, "opus"), load(ls, "fable")
    n = Counter()
    with open(f"{ls}/consensus.jsonl", "w") as fh:
        for i in sorted(set(s) & set(o)):
            a, b = s[i], o[i]
            if a["grade"] == b["grade"]: g, how = a["grade"], "agree"
            elif i in f:
                c = Counter([a["grade"], b["grade"], f[i]["grade"]]).most_common(1)[0]
                g, how = (c[0], "majority") if c[1] >= 2 else (f[i]["grade"], "fable-tiebreak")
            else: n["awaiting_fable"] += 1; continue
            rec = {"pair_id": i, "grade": g, "grade_resolution": how,
                   "votes": {"sonnet": a["grade"], "opus": b["grade"], **({"fable": f[i]["grade"]} if i in f else {})}}
            for side in "ab":
                for fld in (f"technique_{side}", f"primary_{side}"):
                    rec[fld] = a[fld] if a[fld] == b[fld] else {"split": [a[fld], b[fld]]}
                sec = Counter(json.dumps(norm_slug(x), sort_keys=True) for x in (a.get(f"secondary_{side}") or []) + (b.get(f"secondary_{side}") or []))
                rec[f"secondary_{side}"] = [{**json.loads(k), "votes": c} for k, c in sec.items()]
            rec["ambiguous_votes"] = sum(bool(x.get("ambiguous")) for x in (a, b))
            fh.write(json.dumps(rec) + "\n"); n[how] += 1
    return dict(n)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "check": r = check(sys.argv[2], sys.argv[3]); print(len(r), "problems"); print("\n".join(r[:40]))
    elif cmd == "gate": print(json.dumps(gate(sys.argv[2], sys.argv[3]), indent=1))
    elif cmd == "route": print(route(sys.argv[2]))
    elif cmd == "final": print(final(sys.argv[2]))
