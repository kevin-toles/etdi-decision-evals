"""Option 4: a human labelling sheet (CSV) for a gold set, split into a TRAIN part (lines from training documents,
for retraining) and a TEST part (lines from evaluation documents, for grading). Each part is stratified so the noisy
areas are well covered: short-document lines the fonts call code, books, low-code documents, and a slice of lines
the fonts call prose. Consensus documents of the reviewer audits are excluded. The labeller sees the target line with
three context lines either side and fills `label` with code / not_code / ambiguous; the font label and the source
go to a separate key file.
    python3 make_human_gold_sheet.py SCRATCH_DIR OUT_DIR [PER_PART=600]"""
import csv, hashlib, json, os, random, sys

S, OUT = sys.argv[1], sys.argv[2]
PER = int(sys.argv[3]) if len(sys.argv) > 3 else 600
fold = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4
gold = set(json.load(open(os.path.join(S, "gold_docs.json"))))
load = lambda f: [json.loads(l) for l in open(os.path.join(S, f))]
key = load("answer_key_v5.jsonl")
parts = {"TRAIN": [d for d in key if fold(d["stem"]) != 0] + load("train_v5_lowcode.jsonl"),
         "TEST": [d for d in key if fold(d["stem"]) == 0] + load("strata_v5_books.jsonl") + load("strata_v5_lowcode.jsonl") + load("strata_v5_tiny.jsonl")}
mix = {"short/code": 0.30, "short/not_code": 0.15, "book/code": 0.15, "book/not_code": 0.10, "lowcode/code": 0.10, "lowcode/not_code": 0.20}
rng = random.Random(20261111); rows, key_rows = [], []
for part, docs in parts.items():
    pool = {}
    for d in docs:
        if d["stem"] in gold: continue
        seg = "lowcode" if d.get("segment") == "lowcode" else ("book" if d["doc_pages"] >= 60 else "short")
        lines = [t for p in d["pages"] for t, _ in p["lines"]]; labs = [l for p in d["pages"] for _, l in p["lines"]]
        for i, lab in enumerate(labs):
            if lab is not None and lines[i].strip():
                pool.setdefault(f"{seg}/{'code' if lab else 'not_code'}", []).append((d["stem"], i, lines))
    for stratum, share in mix.items():
        for stem, i, lines in rng.sample(pool.get(stratum, []), min(len(pool.get(stratum, [])), round(PER * share))):
            rows.append([part, stem, i, stratum, lines[max(0, i - 3):i], lines[i], lines[i + 1:i + 4]])
rng.shuffle(rows)
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "gold_sheet.csv"), "w", newline="") as fh, open(os.path.join(OUT, "gold_sheet_KEY.json"), "w") as kh:
    w = csv.writer(fh); w.writerow(["id", "part", "context_before", "TARGET", "context_after", "label"])
    keyd = {}
    for n, (part, stem, i, stratum, before, target, after) in enumerate(rows, 1):
        iid = f"H{n:04d}"
        w.writerow([iid, part, "\n".join(before), target, "\n".join(after), ""])
        keyd[iid] = {"part": part, "stem": stem, "line_index": i, "stratum": stratum}
    json.dump(keyd, kh, indent=1)
print(len(rows), "lines;", {p: sum(1 for r in rows if r[0] == p) for p in parts})
