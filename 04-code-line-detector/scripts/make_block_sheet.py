"""Block-level profile sheet: samples PER_STRATUM code blocks (runs of >= 2 non-blank code-labelled lines, a blank or
unlabelled line inside a run allowed) from books and from short documents of an answer key, with two context lines
either side. Blocks longer than 25 lines are cut to their first 25. Block positions go to a separate file.
    python3 make_block_sheet.py KEY.jsonl OUT_DIR [PER_STRATUM=100] [--seed N]"""
import json, os, random, sys

opt = lambda name: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None
pos = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and not sys.argv[i - 1].startswith("--")]
KEY, OUT = pos[0], pos[1]
PER, SEED, MAXL = int(pos[2]) if len(pos) > 2 else 100, int(opt("--seed") or 20261031), 25
pool = {"book": [], "short": []}
for line in open(KEY):
    d = json.loads(line); kind = "book" if d["doc_pages"] >= 60 else "short"
    lines = [t for p in d["pages"] for t, _ in p["lines"]]; labs = [l for p in d["pages"] for _, l in p["lines"]]
    i = 0
    while i < len(lines):
        if labs[i]:
            j = i
            while j + 1 < len(lines) and (labs[j + 1] or (not labs[j + 1] and labs[j + 1] is None and j + 2 < len(lines) and labs[j + 2])):
                j += 1
            if sum(1 for k in range(i, j + 1) if labs[k] and lines[k].strip()) >= 2:
                pool[kind].append((d["stem"], i, j, lines))
            i = j + 1
        else:
            i += 1
rng = random.Random(SEED); items, where = [], {}
for kind in ("book", "short"):
    for stem, a, b, lines in rng.sample(pool[kind], PER):
        items.append((kind, stem, a, b, lines))
rng.shuffle(items); sheet = []
for n, (kind, stem, a, b, lines) in enumerate(items, 1):
    bid = f"B{n:03d}"
    where[bid] = {"stem": stem, "start": a, "end": b, "kind": kind, "lines": b - a + 1}
    sheet.append({"id": bid, "before": lines[max(0, a - 2):a], "BLOCK": lines[a:min(b + 1, a + MAXL)],
                  "truncated": b - a + 1 > MAXL, "after": lines[b + 1:b + 3]})
os.makedirs(OUT, exist_ok=True)
json.dump({"instructions": "Profile each BLOCK. Context lines are for reading only.", "items": sheet}, open(os.path.join(OUT, "block_sheet.json"), "w"), indent=1, ensure_ascii=False)
json.dump(where, open(os.path.join(OUT, "block_positions.json"), "w"), indent=1)
print(len(sheet), "blocks;", {k: len(v) for k, v in pool.items()}, "blocks available")
