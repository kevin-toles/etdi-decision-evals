"""Consensus of the reviewer verdicts and the font-label error rate it implies.
Consensus per item: the verdict held by at least 3 of 4 reviewers (or a strict majority for other counts); otherwise
"no_consensus". Items whose consensus is "ambiguous" or "no_consensus" are reported but left out of the error rates.
    python3 score_audit.py OUT_DIR"""
import collections, glob, json, os, sys

OUT = sys.argv[1]
hidden = json.load(open(os.path.join(OUT, "font_labels_HIDDEN.json")))
revs = {}
for f in sorted(glob.glob(os.path.join(OUT, "verdicts_*.json"))):
    v = json.load(open(f)); revs[os.path.basename(f)[9:-5]] = v["verdicts"]
names = sorted(revs); k = len(names)
missing = {n: sorted(set(hidden) - set(revs[n])) for n in names}
cats = ("code", "not_code", "ambiguous")
cons, rows = {}, []
for iid in sorted(hidden):
    votes = collections.Counter(revs[n].get(iid, "missing") for n in names)
    top, c = votes.most_common(1)[0]
    need = 3 if k == 4 else k // 2 + 1
    cons[iid] = top if c >= need and top in cats else "no_consensus"
# Fleiss' kappa over the three categories
P, pj = [], collections.Counter()
for iid in hidden:
    cnt = collections.Counter(revs[n].get(iid) for n in names if revs[n].get(iid) in cats)
    m = sum(cnt.values())
    if m < 2: continue
    P.append((sum(x * x for x in cnt.values()) - m) / (m * (m - 1))); pj.update({c: v / m for c, v in cnt.items()})
Pbar = sum(P) / len(P); tot = sum(pj.values()); Pe = sum((v / tot) ** 2 for v in pj.values())
kappa = (Pbar - Pe) / (1 - Pe)
strata = collections.defaultdict(lambda: collections.Counter())
for iid, h in hidden.items():
    s = (h["kind"], h["font_label"]); c = cons[iid]
    strata[s][c] += 1
    strata[s]["agree" if c == h["font_label"] else ("excluded" if c in ("ambiguous", "no_consensus") else "disagree")] += 1
report = {"reviewers": names, "missing_items": missing, "fleiss_kappa": round(kappa, 3), "strata": {}}
print(f"reviewers: {names}\nFleiss' kappa: {kappa:.3f}")
print(f"{'stratum':20s} {'n':>4s} {'agree':>6s} {'disagree':>9s} {'excluded':>9s} {'label error':>12s}")
for s in sorted(strata):
    c = strata[s]; n = sum(c[x] for x in ("agree", "disagree", "excluded")); judged = c["agree"] + c["disagree"]
    err = c["disagree"] / judged if judged else float("nan")
    report["strata"][f"{s[0]}/{s[1]}"] = {"n": n, "agree": c["agree"], "disagree": c["disagree"], "excluded": c["excluded"],
                                          "label_error": round(err, 3), "consensus": {x: c[x] for x in cats + ("no_consensus",)}}
    print(f"{s[0] + '/' + s[1]:20s} {n:4d} {c['agree']:6d} {c['disagree']:9d} {c['excluded']:9d} {err:12.1%}")
report["disagreements"] = [{"id": i, **hidden[i], "consensus": cons[i], "votes": {n: revs[n].get(i) for n in names}}
                           for i in sorted(hidden) if cons[i] in ("code", "not_code") and cons[i] != hidden[i]["font_label"]]
json.dump(report, open(os.path.join(OUT, "audit_report.json"), "w"), indent=1)
