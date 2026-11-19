"""Blind audit sheet for the COS code-line answer key (v3 font labels). Samples PER_STRATUM labelled lines from each
of four strata (book/short document x font label code/not code), shows each with 3 lines of context either side, and
writes the font labels to a separate file the reviewers never see. --exclude-run RUN_DIR[,RUN_DIR...] leaves out every
document audited in those earlier runs (so a labelling rule tuned on that run is measured on unseen documents).
    python3 make_audit_sheet.py KEY.jsonl OUT_DIR [PER_STRATUM=75] [--seed N] [--exclude-run RUN_DIR]"""
import json, os, random, sys

opt = lambda name: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None
pos = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and not sys.argv[i - 1].startswith("--")]
KEY, OUT = pos[0], pos[1]
PER, SEED, CTX = int(pos[2]) if len(pos) > 2 else 75, int(opt("--seed") or 20261028), 3
EXCLUDE = {h["stem"] for r in (opt("--exclude-run") or "").split(",") if r
           for h in json.load(open(os.path.join(r, "font_labels_HIDDEN.json"))).values()}
docs = [d for d in (json.loads(l) for l in open(KEY)) if d["stem"] not in EXCLUDE]
pool = {}
for d in docs:
    kind = "book" if d["doc_pages"] >= 60 else "short"
    lines = [t for p in d["pages"] for t, _ in p["lines"]]
    labels = [lab for p in d["pages"] for _, lab in p["lines"]]
    for i, lab in enumerate(labels):
        if lab is not None and lines[i].strip():
            pool.setdefault((kind, lab), []).append((d["stem"], i, lines, lab))
rng = random.Random(SEED); items, hidden = [], {}
for stratum in sorted(pool):
    for stem, i, lines, lab in rng.sample(pool[stratum], PER):
        items.append({"stem": stem, "line_index": i, "before": lines[max(0, i - CTX):i], "target": lines[i],
                      "after": lines[i + 1:i + 1 + CTX], "_stratum": stratum, "_label": lab})
rng.shuffle(items)
sheet = []
for n, it in enumerate(items, 1):
    iid = f"L{n:03d}"
    hidden[iid] = {"stem": it["stem"], "line_index": it["line_index"], "kind": it["_stratum"][0], "font_label": "code" if it["_label"] else "not_code"}
    sheet.append({"id": iid, "before": it["before"], "TARGET": it["target"], "after": it["after"]})
os.makedirs(OUT, exist_ok=True)
json.dump({"instructions": "Judge only TARGET. Context lines are for reading only.", "items": sheet}, open(os.path.join(OUT, "audit_sheet.json"), "w"), indent=1, ensure_ascii=False)
json.dump(hidden, open(os.path.join(OUT, "font_labels_HIDDEN.json"), "w"), indent=1)
print(len(sheet), "items;", len(EXCLUDE), "documents excluded;", {f"{k[0]}/{'code' if k[1] else 'not_code'}": len(v) for k, v in pool.items()}, "lines available per stratum")
