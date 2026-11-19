"""The v5+extra (e)+ng line model retrained with every consensus document held out of training, predicting the
evaluation documents (v5 key fold 0, all strata, the 40-book key) plus the consensus documents. Writes
hgb_holdout_probs.pkl {stem: prob per line} and hgb_holdout_meta.json (validation thresholds).
    cd Code-Orchestrator-Service && python3 <this>"""
import hashlib, json, os, pickle, sys
S = os.path.dirname(os.path.abspath(__file__))


def main():
    sys.argv = ["compare_v3", "none", "none"]
    src = open(os.path.join(S, "compare_v3.py")).read()
    exec(src[:src.index('if MODE == "round":')], globals())
    fold = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4
    gold = json.load(open(os.path.join(S, "gold_docs.json")))
    key = load(os.path.join(S, "answer_key_v5.jsonl"))
    train = [d for d in key if fold(d["stem"]) != 0] + load(os.path.join(S, "train_v5_lowcode.jsonl")) + load(os.path.join(S, "train_v5_codefree.jsonl"))
    train = [d for d in train if d["stem"] not in gold]
    others = [d for d in key if fold(d["stem"]) == 0]
    for f in ("strata_v5_books.jsonl", "strata_v5_tiny.jsonl", "strata_v5_lowcode.jsonl", "strata_v5_codefree.jsonl", "strata_v5_transcript.jsonl", "answer_key_v5_old40.jsonl"):
        others += load(os.path.join(S, f))
    have = {d["stem"] for d in others}; others += [d for st, d in gold.items() if st not in have]
    prep(train); prep(others)
    print(f"train {len(train)} docs (consensus documents removed); predict {len(others)} docs", flush=True)
    probs, t, tr = line_model(train, others, True)
    pickle.dump(probs, open(os.path.join(S, "hgb_holdout_probs.pkl"), "wb"))
    json.dump({"train_docs": len(train), "predicted_docs": len(others), "t": t, "t_run": tr}, open(os.path.join(S, "hgb_holdout_meta.json"), "w"))


if __name__ == "__main__":
    main()
