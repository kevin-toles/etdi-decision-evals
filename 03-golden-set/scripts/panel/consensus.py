"""Golden-set pilot consensus. Per field: when Sonnet 5.5 and Opus 4.8 agree, that value; otherwise the majority of
Sonnet, Opus 4.8 and Fable 5.2; no majority -> Fable 5.2's value (final reviewer). Key points covered = named by at
least two graders. Secondary labels = named by at least two graders. Writes records_pilot_graded.jsonl (the proposer's
fields kept untouched alongside; votes kept per row) and prints what changed versus the proposer.   python3 -I <this>"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agreement import load, records, RUN
HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE)
S, O, F = load("sonnet-5-5")[0], load("opus-4-8")[0], load("fable-5-2")[0]
lab = lambda l: (l["domain"], l["subdomain"])
fields = {"grade": lambda v: v["grade"], "role": lambda v: v["role"], "kf": lambda v: v["knowledge_function"],
          "primary": lambda v: lab(v["primary"]), "beyond": lambda v: v["beyond_key_points"]}
out, missing_fable, stats = [], [], Counter()
for rid, r in records.items():
    votes = [("claude-sonnet-5-5", S[rid]), ("claude-opus-4-8", O[rid])] + ([("claude-fable-5-2", F[rid])] if rid in F else [])
    fin, how = {}, {}
    for name, fn in fields.items():
        vals = [fn(v) for _, v in votes]
        if vals[0] == vals[1]: fin[name], how[name] = vals[0], "agree"
        elif len(vals) == 3:
            c = Counter(vals).most_common(1)[0]
            fin[name], how[name] = (c[0], "majority") if c[1] >= 2 else (vals[2], "fable")
        else:
            fin[name], how[name] = None, "unresolved"; missing_fable.append((rid, name))
        stats[f"{name}:{how[name]}"] += 1
    k = len(votes)
    covers = sorted(kp for kp, n in Counter(kp for _, v in votes for kp in set(v["covers"])).items() if n >= 2)
    sec = sorted({s for s, n in Counter(lab(l) for _, v in votes for l in v["secondary"]).items() if n >= 2} - {fin["primary"]})
    amb = sum(v["ambiguous"] for _, v in votes)
    r2 = dict(r)
    r2["panel"] = {"grade": fin["grade"], "covers_key_points": covers, "beyond_key_points": fin["beyond"], "role": fin["role"],
                   "knowledge_function": fin["kf"],
                   "primary": {"domain": fin["primary"][0], "subdomain": fin["primary"][1]} if fin["primary"] else None,
                   "secondary": [{"domain": d, "subdomain": s} for d, s in sec], "ambiguous_votes": amb, "resolution": how,
                   "votes": [{"model": m, **v} for m, v in votes]}
    out.append(r2)
with open(f"{EV}/records_{RUN}_graded.jsonl", "w") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("records", len(out), "| unresolved fields (no Fable verdict):", len(missing_fable), missing_fable[:5])
print("resolution:", dict(sorted(stats.items())))
G = Counter(r["panel"]["grade"] for r in out); print("final grade distribution", sorted(G.items()))
print("final role", dict(Counter(r["panel"]["role"] for r in out)), "| final KF", dict(Counter(r["panel"]["knowledge_function"] for r in out)))
amb = [r for r in out if r["panel"]["ambiguous_votes"] >= 2]; print("rows flagged ambiguous by >=2 graders", len(amb))
# proposer vs final
pr = lambda r: r["proposed"]
print("\nPROPOSER vs FINAL")
print("  primary subdomain same", sum(lab(pr(r)["primary"]) == lab(r["panel"]["primary"]) for r in out), "/", len(out),
      "| primary domain same", sum(pr(r)["primary"]["domain"] == r["panel"]["primary"]["domain"] for r in out))
print("  KF same", sum(pr(r)["knowledge_function"] == r["panel"]["knowledge_function"] for r in out),
      "| role same", sum({"distractor": "none"}.get(pr(r)["role"], pr(r)["role"]) == r["panel"]["role"] for r in out))
print("  proposed distractors -> final grades", [r["panel"]["grade"] for r in out if pr(r)["role"] == "distractor"])
print("  proposed direct -> final grades", sorted(Counter(r["panel"]["grade"] for r in out if pr(r)["role"] == "direct").items()))
print("  proposed foundation -> final grades", sorted(Counter(r["panel"]["grade"] for r in out if pr(r)["role"] == "foundation").items()))
print("  'beyond key points' proposals (covers==[] non-distractor) -> final", [(r["record_id"], r["panel"]["grade"], r["panel"]["beyond_key_points"]) for r in out if not pr(r)["covers_key_points"] and pr(r)["role"] != "distractor"])
q = {}
for r in out: q.setdefault(r["qid"], []).append(r["panel"]["grade"])
print("\nper question: n, graded>=2, graded 3")
for k, g in q.items(): print(f"  {k:30} {len(g):2} {sum(x>=2 for x in g):2} {sum(x==3 for x in g):2}")
