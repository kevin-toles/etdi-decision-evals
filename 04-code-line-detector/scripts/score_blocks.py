"""Consensus language and kind per block (>= 3 of 4 reviewers agree, else no_consensus), with agreement and the
resulting distributions by stratum. Each block in block_report.json carries its stratum (book / short) and its
consensus language and kind.
    python3 score_blocks.py OUT_DIR"""
import collections, glob, json, os, sys

OUT = sys.argv[1]
where = json.load(open(os.path.join(OUT, "block_positions.json")))
revs = {os.path.basename(f)[8:-5]: json.load(open(f))["blocks"] for f in sorted(glob.glob(os.path.join(OUT, "profile_*.json")))}
names = sorted(revs); need = 3 if len(names) == 4 else len(names) // 2 + 1
report = {"reviewers": names, "missing": {n: sorted(set(where) - set(revs[n])) for n in names}, "blocks": {}}
for field in ("language", "kind"):
    dist = {"book": collections.Counter(), "short": collections.Counter()}; agree = 0
    for bid, w in where.items():
        votes = collections.Counter(revs[n].get(bid, {}).get(field, "missing") for n in names)
        top, c = votes.most_common(1)[0]
        cons = top if c >= need else "no_consensus"; agree += cons != "no_consensus"
        report["blocks"].setdefault(bid, {"stem": w["stem"], "start": w["start"], "end": w["end"], "stratum": w["kind"], "lines": w["lines"]})[field] = cons
        dist[w["kind"]][cons] += 1
    print(f"\n{field}: consensus on {agree}/{len(where)} blocks")
    report[f"{field}_distribution"] = {}
    for k, c in dist.items():
        n = sum(c.values()); report[f"{field}_distribution"][k] = dict(c.most_common())
        print(f"  {k:5s} (n={n}): " + ", ".join(f"{x} {v/n:.0%}" for x, v in c.most_common(16)))
json.dump(report, open(os.path.join(OUT, "block_report.json"), "w"), indent=1)
