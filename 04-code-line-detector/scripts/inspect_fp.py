import sys, os, random, collections
sys.argv = ["x", "none", "none"]
S = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(S, "compare_v3.py")).read()
exec(src[:src.index('if MODE == "round":')])
docs = load(os.path.join(S, "answer_key_v2.jsonl"), 200); prep(docs)
train = [b for i, b in enumerate(docs) if i % 5 < 2]; test = [b for i, b in enumerate(docs) if i % 5 >= 2]
probs, t, tr = line_model(train, test, True)
rng = random.Random(0); fps = {"short": [], "book": []}; fns = {"short": [], "book": []}
for b in test:
    acc = predict_runs(b, probs[b["stem"]], t, tr); lines, labels = b["_t"][1], b["_t"][2]
    pred = [False] * len(lines)
    for a, e, _ in acc:
        for i in range(a, e + 1): pred[i] = True
    for i, (p, lab) in enumerate(zip(pred, labels)):
        if lab is None: continue
        if p and not lab: fps[b["_kind"]].append((b["stem"][:40], i, lines[i]))
        if lab and not p: fns[b["_kind"]].append((b["stem"][:40], i, lines[i]))
for k in ("short", "book"):
    print(f"\n=== {k}: {len(fps[k])} false positives, {len(fns[k])} misses; FP lines by doc (top 8):")
    for s, n in collections.Counter(x[0] for x in fps[k]).most_common(8): print(f"  {n:5d}  {s}")
    print("  sample FP lines:")
    for s, i, l in rng.sample(fps[k], min(40, len(fps[k]))): print(f"    {s[:22]:22s} | {l[:110]}")
    print("  sample missed code lines:")
    for s, i, l in rng.sample(fns[k], min(15, len(fns[k]))): print(f"    {s[:22]:22s} | {l[:110]}")
