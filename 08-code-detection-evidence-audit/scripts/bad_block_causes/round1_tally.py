"""Bad-block causes, round 1 tally from the reviewers' files only: validate, 3-of-4 consensus on cause, Fleiss' kappa,
and the round-2 sheet (no 3-of-4 consensus, plus a random 10% of consensus items, seed 20261117) showing the block with
15 non-blank lines either side from the extracted JSON.
    cd Code-Orchestrator-Service && python3 round1_tally.py <work_dir> <out_dir>"""
import collections, json, os, random, sys
W, BD = sys.argv[1:3]
MODELS = ["opus-4-6", "opus-4-7", "opus-4-8", "opus-5-5"]
CAUSES = ("all_prose", "code_plus_prose_edge", "split_fragment", "merged_blocks", "noncode_monospace", "terminal_output_or_log", "actually_code", "other")
items = {x["id"]: x for p in "AB" for x in json.load(open(os.path.join(BD, f"round1_sheet_{p}.json")))["items"]}
votes, notes, problems = collections.defaultdict(dict), collections.defaultdict(dict), []
for m in MODELS:
    for p in "AB":
        f = os.path.join(BD, f"round1_causes_{m}_{p}.json"); v = json.load(open(f))
        ids = {x["id"] for x in json.load(open(os.path.join(BD, f"round1_sheet_{p}.json")))["items"]}
        if v.get("model") != f"claude-{m}": problems.append(f"{f}: model {v.get('model')}")
        if set(v["blocks"]) != ids: problems.append(f"{f}: ids differ")
        for iid, x in v["blocks"].items():
            if x.get("cause") not in CAUSES: problems.append(f"{f}: {iid} cause {x.get('cause')}")
            votes[iid][m] = x.get("cause")
            if x.get("note"): notes[iid][m] = x["note"]
assert not problems, problems
def fleiss(vs):
    n = len(MODELS); N = len(vs); pj = collections.Counter(); Pi = 0
    for v in vs:
        c = collections.Counter(v.values()); pj.update(c); Pi += (sum(x * x for x in c.values()) - n) / (n * (n - 1))
    Pe = sum((pj[k] / (N * n)) ** 2 for k in CAUSES); return round((Pi / N - Pe) / (1 - Pe), 3)
cons = {}
for iid, v in votes.items():
    top, c = collections.Counter(v.values()).most_common(1)[0]; cons[iid] = top if c >= 3 else None
settled = sorted(i for i, c in cons.items() if c); open_ = sorted(i for i, c in cons.items() if not c)
check = sorted(random.Random(20261117).sample(settled, round(0.10 * len(settled))))
src = open(os.path.join(W, "options_phase_d.py")).read().split("# ---------------------------------------------------------------- sources")[0]
__file__ = os.path.join(W, "options_phase_d.py"); exec(src, globals())
index = json.load(open(os.path.join(BD, "round1_index.json"))); r2 = []
for iid in open_ + check:
    e = index[iid]; L = DOCS[e["stem"]]["_t"][1]; a, z = e["lines"][0], e["lines"][-1]
    assert [L[i] for i in e["lines"]] == items[iid]["BLOCK"]
    before = [L[i] for i in range(0, a) if L[i].strip()][-15:]; after = [L[i] for i in range(z + 1, len(L)) if L[i].strip()][:15]
    r2.append({"id": iid, "book": items[iid]["book"], "pages": items[iid]["pages"], "before": before, "BLOCK": items[iid]["BLOCK"], "after": after})
random.Random(20261118).shuffle(r2)
json.dump({"items": r2}, open(os.path.join(BD, "round2_sheet.json"), "w"), indent=1, ensure_ascii=False)
out = {"problems": problems, "items": len(votes), "fleiss_kappa_round1": fleiss(list(votes.values())), "settled_round1": len(settled),
       "open_after_round1": len(open_), "consensus_check_sample": len(check), "round1_consensus_counts": dict(collections.Counter(c for c in cons.values() if c)),
       "votes": votes, "notes": notes, "consensus_round1": cons, "round2_items": {"open": open_, "check": check}}
json.dump(out, open(os.path.join(BD, "round1_tally.json"), "w"), indent=1)
print({k: v for k, v in out.items() if k not in ("votes", "notes", "consensus_round1", "round2_items")}, "round-2 sheet:", len(r2))
