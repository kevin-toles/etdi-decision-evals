"""(i) Per-language detector recall on the profiled blocks, from held-out predictions: the v4 key is split into four
document folds (the compare_v3 'curve' hash), and each fold is predicted by (e)+ng+run trained on the other three.
(ii) Blind low-code sheet: the fold-0 model (trained on folds 1-3, as eval_segments) predicts the low-code stratum;
150 lines it calls code that the font labels call not code, plus 50 control lines it calls not code, are shuffled
into an audit sheet (TARGET line with 3 context lines either side); which is which goes to the hidden file.
    cd Code-Orchestrator-Service && python3 <this> BLOCK_RUN_DIR LOWCODE_OUT_DIR"""
import collections, hashlib, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BLOCKS, LOWOUT = sys.argv[1], sys.argv[2]
sys.argv = ["compare_v3", "none", "none"]
src = open(os.path.join(HERE, "compare_v3.py")).read()
exec(src[:src.index('if MODE == "round":')])
import numpy as np

key = load(os.path.join(HERE, "answer_key_v4.jsonl")); prep(key)
low = load(os.path.join(HERE, "strata_lowcode.jsonl")); prep(low)
fold = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4
where = json.load(open(os.path.join(BLOCKS, "block_positions.json")))
need = {w["stem"] for w in where.values()}
pred = {}
for k in range(4):
    tr = [b for b in key if fold(b["stem"]) != k]
    te = [b for b in key if fold(b["stem"]) == k and b["stem"] in need]
    others = te + (low if k == 0 else [])
    probs, t, t_run = line_model(tr, others, True)
    for b in others:
        acc = predict_runs(b, probs[b["stem"]], t, t_run); p = [False] * len(b["_t"][1])
        for a, e, _ in acc:
            for i in range(a, e + 1): p[i] = True
        pred[b["stem"]] = p
    print(f"fold {k}: trained on {len(tr)}, predicted {len(others)}", flush=True)

# (i) per-language recall. block_positions index lines as make_block_sheet flattened them (no page separators);
# book_text inserts one separator line between pages, so map flat index -> book_text index.
def flat_to_bt(bk):
    m, j = [], 0
    for k, pg in enumerate(bk["pages"]):
        if k: j += 1
        for _ in pg["lines"]:
            m.append(j); j += 1
    return m
by_stem = {b["stem"]: b for b in key}
rep = json.load(open(os.path.join(BLOCKS, "block_report.json")))["blocks"]
agg = {"language": collections.defaultdict(lambda: [0, 0, 0]), "kind": collections.defaultdict(lambda: [0, 0, 0])}
for bid, w in where.items():
    bk = by_stem[w["stem"]]; m = flat_to_bt(bk); labels = bk["_t"][2]; p = pred[w["stem"]]
    idx = [m[i] for i in range(w["start"], w["end"] + 1)]
    code = [i for i in idx if labels[i]]; found = sum(p[i] for i in code)
    for field in ("language", "kind"):
        a = agg[field][rep[bid][field]]; a[0] += 1; a[1] += len(code); a[2] += found
out = {}
for field in ("language", "kind"):
    print(f"\n{field:22s} blocks  code lines  recall")
    for name, (nb, nl, nf) in sorted(agg[field].items(), key=lambda x: -x[1][0]):
        print(f"  {name:22s} {nb:5d} {nl:10d}  {nf / max(1, nl):6.1%}")
    out[field] = {k: {"blocks": v[0], "code_lines": v[1], "found": v[2], "recall": round(v[2] / max(1, v[1]), 3)} for k, v in agg[field].items()}
json.dump(out, open(os.path.join(BLOCKS, "detector_recall_by_language.json"), "w"), indent=1)

# (ii) low-code sheet
fp, ctrl = [], []
for b in low:
    lines, labels = b["_t"][1], b["_t"][2]; p = pred[b["stem"]]
    for i, (l, lab) in enumerate(zip(lines, labels)):
        if lab is None or not l.strip(): continue
        if p[i] and not lab: fp.append((b, i))
        elif not p[i]: ctrl.append((b, i))
rng = random.Random(20261102)
picks = [(x, "model_code") for x in rng.sample(fp, min(150, len(fp)))] + [(x, "model_not_code") for x in rng.sample(ctrl, 50)]
rng.shuffle(picks); sheet, hidden = [], {}
for n, ((b, i), grp) in enumerate(picks, 1):
    lines = b["_t"][1]; iid = f"Q{n:03d}"
    sheet.append({"id": iid, "before": lines[max(0, i - 3):i], "TARGET": lines[i], "after": lines[i + 1:i + 4]})
    hidden[iid] = {"stem": b["stem"], "line_index": i, "kind": grp, "font_label": "not_code"}
os.makedirs(LOWOUT, exist_ok=True)
json.dump({"instructions": "Judge only TARGET. Context lines are for reading only.", "items": sheet}, open(os.path.join(LOWOUT, "audit_sheet.json"), "w"), indent=1, ensure_ascii=False)
json.dump(hidden, open(os.path.join(LOWOUT, "font_labels_HIDDEN.json"), "w"), indent=1)
print(f"\nlow-code sheet: {len(sheet)} items ({len(fp)} model-code / font-not-code lines available, {len(ctrl)} controls available)")
