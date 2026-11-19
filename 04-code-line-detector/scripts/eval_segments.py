"""Segment-level scoring of the code-line detector on the v4 key plus the extra strata, weighted to the corpus by the
census. Trains on the v4 key's curve pool (the same held-out quarter as compare_v3 curve stays out), then scores:
  code segments  (book, short, tiny, lowcode, 40-book key): line precision / recall / F1
  code-free segments (codefree PDFs, transcripts): false-positive lines per 1,000 lines, share of documents with a
                                                   false block
Corpus-weighted figures scale each segment's per-document counts by its census share; segments the labeller cannot
reach (scanned, code not in monospace, low-code PDFs, other no-PDF) are listed as unmeasured.
    cd Code-Orchestrator-Service && python3 <this> census_v4.json out.json"""
import collections, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS, OUT_PATH = sys.argv[1], sys.argv[2]   # compare_v3's header reassigns OUT
sys.argv = ["compare_v3", "none", "none"]
src = open(os.path.join(HERE, "compare_v3.py")).read()
exec(src[:src.index('if MODE == "round":')])
import numpy as np

key = load(os.path.join(HERE, "answer_key_v4.jsonl")); prep(key)
held = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4 == 0
train = [b for b in key if not held(b["stem"])]
segs = {"book": [b for b in key if held(b["stem"]) and b["_kind"] == "book"],
        "short": [b for b in key if held(b["stem"]) and b["_kind"] == "short"]}
for name, f in (("book", "strata_books.jsonl"), ("tiny", "strata_tiny.jsonl"), ("lowcode", "strata_lowcode.jsonl"), ("codefree", "strata_codefree.jsonl"),
                ("transcript", "strata_transcript.jsonl"), ("40-book key", "answer_key_v4_old40.jsonl")):
    docs = load(os.path.join(HERE, f)); prep(docs); segs.setdefault(name, []).extend(docs)
test = [b for v in segs.values() for b in v]
print({k: len(v) for k, v in segs.items()}, "test docs;", len(train), "train docs", flush=True)

probs, t, tr = line_model(train, test, True)
base = HeuristicCodeDetector()
variants = {"baseline": {b["stem"]: spans(b["_t"][0], b["_t"][1], base.detect_candidates(b["_t"][0])) for b in test}}
variants["(e)+ng"], variants["(e)+ng+run"] = evaluate_line(test, probs, t, tr)


def counts(docs, acc):
    out = []
    for bk in docs:
        lines, labels = bk["_t"][1], bk["_t"][2]; pred = [False] * len(lines); blocks = false_blocks = 0
        for a, b, _ in acc[bk["stem"]]:
            for i in range(a, b + 1): pred[i] = True
            labs = [labels[i] for i in range(a, b + 1) if labels[i] is not None]
            if labs:
                blocks += 1; false_blocks += not any(labs)
        tp = sum(p and l for p, l in zip(pred, labels) if l is not None); fp = sum(p and not l for p, l in zip(pred, labels) if l is not None)
        fn = sum((not p) and l for p, l in zip(pred, labels) if l is not None); n = sum(l is not None for l in labels)
        out.append((tp, fp, fn, n, false_blocks))
    return np.array(out, dtype=float)


census = json.load(open(CENSUS)); N = census["N"]; cc = collections.Counter()
for k, v in census["counts"].items():
    cls, band = k.split("|")
    seg = {"code": band, "codefree": "codefree", "transcript": "transcript", "low_code": "lowcode"}.get(cls, f"unmeasured: {cls}")
    cc[seg] += v / N
report = {"census_share": dict(cc), "threshold": t, "run_threshold": tr, "segments": {}, "weighted": {}}
print("\ncensus shares:", ", ".join(f"{k} {v:.1%}" for k, v in sorted(cc.items(), key=lambda x: -x[1])))
for vname, acc in variants.items():
    print(f"\n== {vname}")
    W = np.zeros(5)
    for sname, docs in segs.items():
        c = counts(docs, acc); tp, fp, fn, n, fb = c.sum(0)
        if sname in ("codefree", "transcript"):
            r = {"docs": len(docs), "fp_per_1k_lines": round(1000 * fp / max(1, n), 2), "docs_with_false_block": round(float((c[:, 4] > 0).mean()), 3)}
            print(f"  {sname:12s} n={len(docs):4d}  false-positive lines per 1k: {r['fp_per_1k_lines']:7.2f}   docs with a false block: {r['docs_with_false_block']:.1%}")
        else:
            p = tp / max(1, tp + fp); rc = tp / max(1, tp + fn)
            r = {"docs": len(docs), "precision": round(p, 3), "recall": round(rc, 3), "f1": round(2 * p * rc / max(1e-9, p + rc), 3)}
            r["fp_per_1k_lines"] = round(1000 * fp / max(1, n), 2)
            print(f"  {sname:12s} n={len(docs):4d}  P {p:.3f}  R {rc:.3f}  F1 {r['f1']:.3f}   false-positive lines per 1k: {r['fp_per_1k_lines']:7.2f}")
        report["segments"].setdefault(vname, {})[sname] = r
        if sname in cc: W += cc[sname] * c.mean(0)
    p = W[0] / max(1e-9, W[0] + W[1]); rc = W[0] / max(1e-9, W[0] + W[2])
    covered = sum(v for k, v in cc.items() if k in segs)
    report["weighted"][vname] = {"precision": round(p, 3), "recall": round(rc, 3), "f1": round(2 * p * rc / max(1e-9, p + rc), 3), "corpus_share_measured": round(covered, 3)}
    print(f"  corpus-weighted (measured segments, {covered:.0%} of corpus): P {p:.3f}  R {rc:.3f}  F1 {report['weighted'][vname]['f1']:.3f}")
json.dump(report, open(OUT_PATH, "w"), indent=1)
