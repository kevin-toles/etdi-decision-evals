"""Gold panel round 1 tally, from the reviewers' files only: validate each file (model id, every item id, allowed
labels), 3-of-4 consensus per item, Fleiss' kappa, and the round-2 sheet: every item without a 3-of-4 code/not_code
consensus plus a random 10% of consensus items (seed 20261117), shown with the whole page from the extracted JSON.
    python3 round1_tally.py <work_dir> <panel_dir>"""
import collections, json, os, random, sys
W, G = sys.argv[1:3]
MODELS = ["opus-4-6", "opus-4-7", "opus-4-8", "opus-5-5"]; CATS = ("code", "not_code", "ambiguous")
items = {x["id"]: x for p in "AB" for x in json.load(open(os.path.join(G, f"round1_sheet_{p}.json")))["items"]}
votes, problems = collections.defaultdict(dict), []
for m in MODELS:
    for p in "AB":
        f = os.path.join(G, f"round1_verdicts_{m}_{p}.json"); v = json.load(open(f))
        ids = {x["id"] for x in json.load(open(os.path.join(G, f"round1_sheet_{p}.json")))["items"]}
        if v.get("model") != f"claude-{m}": problems.append(f"{f}: model {v.get('model')}")
        ff = os.path.join(G, f"round1_fill_verdicts_{m}_{p}.json")       # items the reviewer skipped, asked again blind
        if os.path.exists(ff):
            fv = json.load(open(ff)); fill_ids = {x["id"] for x in json.load(open(os.path.join(G, f"round1_fill_sheet_{m}_{p}.json")))["items"]}
            if fv.get("model") != f"claude-{m}": problems.append(f"{ff}: model {fv.get('model')}")
            if set(fv["verdicts"]) != fill_ids: problems.append(f"{ff}: ids differ")
            assert not set(fv["verdicts"]) & set(v["verdicts"]); v["verdicts"].update(fv["verdicts"])
        if set(v["verdicts"]) != ids: problems.append(f"{f}: ids differ ({len(set(v['verdicts']) ^ ids)})")
        for iid, lab in v["verdicts"].items():
            if lab not in CATS: problems.append(f"{f}: {iid} label {lab}")
            votes[iid][m] = lab
def fleiss(vs):
    n = len(MODELS); N = len(vs); pj = collections.Counter(); Pi = 0
    for v in vs:
        c = collections.Counter(v.values()); pj.update(c); Pi += (sum(x * x for x in c.values()) - n) / (n * (n - 1))
    Pbar = Pi / N; Pe = sum((pj[k] / (N * n)) ** 2 for k in CATS)
    return round((Pbar - Pe) / (1 - Pe), 3)
cons = {}
for iid, v in votes.items():
    top, c = collections.Counter(v.values()).most_common(1)[0]
    cons[iid] = top if c >= 3 and top in ("code", "not_code") else None
settled = sorted(i for i, c in cons.items() if c); open_ = sorted(i for i, c in cons.items() if not c)
check = sorted(random.Random(20261117).sample(settled, round(0.10 * len(settled))))
# round-2 sheet: the whole page around the target line, from the extracted JSON
index = json.load(open(os.path.join(G, "round1_index.json"))); docs = {}
for f in ("answer_key_v5.jsonl", "train_v5_lowcode.jsonl", "strata_v5_books.jsonl", "strata_v5_lowcode.jsonl", "strata_v5_tiny.jsonl"):
    for l in open(os.path.join(W, f)):
        d = json.loads(l); docs.setdefault(d["stem"], d)
r2 = []
for iid in open_ + check:
    k = index[iid]; d = docs[k["stem"]]; j = 0
    for pn, pg in enumerate(d["pages"]):
        lines = [t for t, _ in pg["lines"]]
        if j <= k["line_index"] < j + len(lines):
            i = k["line_index"] - j; assert lines[i] == items[iid]["TARGET"]
            r2.append({"id": iid, "book": k["stem"], "page": k["page"], "before": lines[:i], "TARGET": lines[i], "after": lines[i + 1:]}); break
        j += len(lines)
random.Random(20261118).shuffle(r2)
json.dump({"instructions": "Second, wider-context pass. Each item shows the whole page around one TARGET line (before = page lines above it, "
           "after = page lines below it). Judge only the TARGET line: code / not_code / ambiguous.", "items": r2},
          open(os.path.join(G, "round2_sheet.json"), "w"), indent=1, ensure_ascii=False)
out = {"problems": problems, "items": len(votes), "fleiss_kappa_round1": fleiss(list(votes.values())),
       "settled_round1": len(settled), "open_after_round1": len(open_), "consensus_check_sample": len(check),
       "round1_consensus_counts": dict(collections.Counter(c for c in cons.values() if c)),
       "votes": votes, "consensus_round1": cons, "round2_items": {"open": open_, "check": check}}
json.dump(out, open(os.path.join(G, "round1_tally.json"), "w"), indent=1)
print({k: v for k, v in out.items() if k not in ("votes", "consensus_round1", "round2_items")}, "round-2 sheet:", len(r2))
