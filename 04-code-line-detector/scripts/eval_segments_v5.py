"""Segment-level scoring on the v5 key and strata, with the line threshold and the run-filter threshold chosen to
maximise corpus-weighted F1 (census shares) instead of the hand-set F1 - 0.5 x prose-only objective.
Each segment's test documents are split in half by hash: thresholds are chosen on the 'tune' half, and every figure
is reported on the 'test' half. The model is (e)+ng trained on the v5 key's folds 1-3 (fold 0 is held out), plus
any TRAIN_EXTRA files (comma-separated JSONL; e.g. low-code and code-free training strata kept apart from the test
strata).
    cd Code-Orchestrator-Service && python3 <this> census_v5.json out.json"""
import collections, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS, OUT_PATH = sys.argv[1], sys.argv[2]   # compare_v3's header reassigns OUT
sys.argv = ["compare_v3", "none", "none"]
src = open(os.path.join(HERE, "compare_v3.py")).read()
exec(src[:src.index('if MODE == "round":')])
import numpy as np

fold = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4
half = lambda s: int(hashlib.sha256(f"tune:{s}".encode()).hexdigest(), 16) % 2
key = load(os.path.join(HERE, "answer_key_v5.jsonl")); prep(key)
train = [b for b in key if fold(b["stem"]) != 0]
for f in filter(None, os.environ.get("TRAIN_EXTRA", "").split(",")):
    extra = load(os.path.join(HERE, f)); prep(extra); train += extra
segs = {"book": [b for b in key if fold(b["stem"]) == 0 and b["_kind"] == "book"],
        "short": [b for b in key if fold(b["stem"]) == 0 and b["_kind"] == "short"]}
for name, f in (("book", "strata_v5_books.jsonl"), ("tiny", "strata_v5_tiny.jsonl"), ("lowcode", "strata_v5_lowcode.jsonl"),
                ("codefree", "strata_v5_codefree.jsonl"), ("transcript", "strata_v5_transcript.jsonl"), ("40-book key", "answer_key_v5_old40.jsonl")):
    docs = load(os.path.join(HERE, f)); prep(docs); segs.setdefault(name, []).extend(docs)
alldocs = [b for v in segs.values() for b in v]
import pickle
CACHE = OUT_PATH + ".probs.pkl"                       # model predictions, so a scoring fix does not retrain
if os.path.exists(CACHE):
    probs, t_val, tr_val = pickle.load(open(CACHE, "rb"))
else:
    probs, t_val, tr_val = line_model(train, alldocs, True)
    pickle.dump((probs, t_val, tr_val), open(CACHE, "wb"))
print({k: len(v) for k, v in segs.items()}, "docs;", len(train), "train; validation-tuned t", t_val, "t_run", tr_val, flush=True)

census = json.load(open(CENSUS)); N = census["N"]; share = collections.Counter()
for k, v in census["counts"].items():
    cls, band = k.split("|")
    share[{"code": band, "codefree": "codefree", "transcript": "transcript", "low_code": "lowcode"}.get(cls, f"unmeasured: {cls}")] += v / N
weighted = [s for s in segs if s in share]


def doc_arrays(bk, t):
    """Runs of lines with p >= t (one blank allowed inside), as a run id per line and each run's mean probability."""
    lines, p = bk["_t"][1], probs[bk["stem"]]
    on = np.array([pi >= t and bool(l.strip()) for pi, l in zip(p, lines)])
    blank = np.array([not l.strip() for l in lines])
    rid = -np.ones(len(lines), int); means = []; i = 0; n = len(lines)
    while i < n:
        if on[i]:
            j = i
            while j + 1 < n and (on[j + 1] or (blank[j + 1] and j + 2 < n and on[j + 2])):
                j += 1
            idx = [k for k in range(i, j + 1) if not blank[k]]
            rid[i:j + 1] = len(means); means.append(float(np.mean(p[idx])) if idx else 0.0); i = j + 1
        else:
            i += 1
    return rid, np.array(means)


def lab_arrays(bk):
    labs = bk["_t"][2]
    return np.array([l is True for l in labs]), np.array([l is False for l in labs])


LAB = {b["stem"]: lab_arrays(b) for b in alldocs}
TS = np.round(np.arange(0.1, 0.981, 0.02), 2); TR = [None] + list(np.round(np.arange(0.3, 0.991, 0.01), 2))
cache = {}
for t in TS:
    for b in alldocs:
        cache[(b["stem"], t)] = doc_arrays(b, t)


def doc_counts(b, t, tr):
    rid, means = cache[(b["stem"], t)]; code, prose = LAB[b["stem"]]
    if not len(means):
        pred = np.zeros(len(rid), bool)
    else:
        keep = np.ones(len(means), bool) if tr is None else means >= tr
        pred = (rid >= 0) & keep[np.maximum(rid, 0)]
    false_block = 0
    for r in np.unique(rid[pred]):
        m = rid == r
        if (code[m] | prose[m]).any() and not code[m].any(): false_block = 1
    return np.array([(pred & code).sum(), (pred & prose).sum(), (~pred & code).sum(), (code | prose).sum(), false_block], float)


def seg_counts(docs, t, tr):
    return np.array([doc_counts(b, t, tr) for b in docs]) if docs else np.zeros((0, 5))


def weighted_f1(part, t, tr):
    W = np.zeros(5)
    for s in weighted:
        docs = [b for b in segs[s] if half(b["stem"]) == part]
        if docs: W += share[s] * seg_counts(docs, t, tr).mean(0)
    p = W[0] / max(1e-9, W[0] + W[1]); r = W[0] / max(1e-9, W[0] + W[2])
    return 2 * p * r / max(1e-9, p + r), p, r


best = max(((weighted_f1(0, t, tr)[0], t, tr) for t in TS for tr in TR), key=lambda x: x[0])
_, t_best, tr_best = best
print(f"corpus-weighted tuning (tune half): t {t_best}, t_run {tr_best}, tune F1 {best[0]:.3f}", flush=True)
nearest = lambda x: TS[np.argmin(abs(TS - x))]
configs = {"(e)+ng, validation-tuned t, no run filter": (nearest(t_val), None),
           "(e)+ng+run, F1-0.5*prose-only tuned (round 2-4 setting)": (nearest(t_val), min(TR[1:], key=lambda x: abs(x - tr_val))),
           "(e)+ng+run, corpus-weighted tuned": (t_best, tr_best)}
report = {"census_share": dict(share), "configs": {}}
print("\ncensus shares:", ", ".join(f"{k} {v:.1%}" for k, v in sorted(share.items(), key=lambda x: -x[1])))
for name, (t, tr) in configs.items():
    print(f"\n== {name}: t {t}, t_run {tr}   (test half)")
    rep = {"t": float(t), "t_run": None if tr is None else float(tr), "segments": {}}
    for s, docs in segs.items():
        c = seg_counts([b for b in docs if half(b["stem"]) == 1], t, tr)
        if not len(c): continue
        tp, fp, fn, n, _ = c.sum(0)
        if s in ("codefree", "transcript"):
            r = {"docs": len(c), "fp_per_1k_lines": round(1000 * fp / max(1, n), 2), "docs_with_false_block": round(float(c[:, 4].mean()), 3)}
            print(f"  {s:12s} n={len(c):4d}  false lines per 1k {r['fp_per_1k_lines']:6.2f}   docs with a false block {r['docs_with_false_block']:.1%}")
        else:
            p = tp / max(1, tp + fp); rc = tp / max(1, tp + fn)
            r = {"docs": len(c), "precision": round(p, 3), "recall": round(rc, 3), "f1": round(2 * p * rc / max(1e-9, p + rc), 3), "fp_per_1k_lines": round(1000 * fp / max(1, n), 2)}
            print(f"  {s:12s} n={len(c):4d}  P {p:.3f}  R {rc:.3f}  F1 {r['f1']:.3f}")
        rep["segments"][s] = r
    f1, p, rc = weighted_f1(1, t, tr)
    cov = sum(share[s] for s in weighted)
    rep["weighted"] = {"precision": round(p, 3), "recall": round(rc, 3), "f1": round(f1, 3), "corpus_share_measured": round(cov, 3)}
    print(f"  corpus-weighted ({cov:.0%} of corpus measured): P {p:.3f}  R {rc:.3f}  F1 {f1:.3f}")
    report["configs"][name] = rep
json.dump(report, open(OUT_PATH, "w"), indent=1)
