"""A4 (c) / D1 worked example: the code-label audit's trained line detector (HGB + char n-gram stack, compare_v3.py
line_model, the 'hgb' rows of phase_d options) trained on the v5 answer key + v5 extra training docs, predicting real
chapters' lines; blocks = runs at the tuned thresholds (predict_runs). scikit-learn only; no embedding model, no LLM.
    cd Code-Orchestrator-Service && .venv/bin/python <this> '<json [[book, start, end], ...]>' > a4_trained.txt"""
import json, os, sys
sys.path.insert(0, os.getcwd())
CH = [tuple(x) for x in json.loads(sys.argv[1])]
sys.argv = ["compare_v3", "none", "none"]
S = "<EVIDENCE>/code_label_audit/scripts"
src = open(f"{S}/compare_v3.py").read()
HERE = S
exec(src[:src.index('if MODE == "round":')].replace("HERE = os.path.dirname(os.path.abspath(__file__))", f"HERE = {S!r}"), globals())
D = "<CORPUS_ROOT>/evaluation/cos-code-line-answer-key"
RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
train = load(f"{D}/keys/answer_key_v5.jsonl") + load(f"{D}/train/train_v5_lowcode.jsonl") + load(f"{D}/train/train_v5_codefree.jsonl")
others = []
for book, s, e in CH:
    d = json.load(open(f"{RAW}/{book}.json")); pages = []
    for p in d["pages"]:
        try: n = int(p["page_number"])
        except Exception: continue
        if s <= n <= e: pages.append({"page_number": n, "lines": [[l, None] for l in (p.get("text") or "").split("\n")]})
    others.append({"stem": f"{book}#{s}-{e}", "doc_pages": 999, "pages": pages})
prep(train); prep(others)
print(f"train {len(train)} docs", flush=True)
probs, t, tr = line_model(train, others, True)
print(f"thresholds: line {t:.2f}, run {tr:.2f}")
for bk in others:
    lines = bk["_t"][1]; p = probs[bk["stem"]]
    blocks = predict_runs(bk, p, t, tr)
    print(f"\n######## {bk['stem']}: {len(blocks)} blocks")
    for a, b, _ in blocks:
        body = "\n".join(l for l in lines[a:b + 1] if l.strip())
        print(f"-- lines {a}-{b}, mean p {float(np.mean([p[i] for i in range(a, b + 1) if lines[i].strip()])):.2f}\n{body[:700]}")
