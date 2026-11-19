"""Gold panel round 1: blind sheets for the 600 TEST rows of human_gold_2026-10-29/gold_sheet.csv.
Context comes from the extracted JSON lines only (the answer-key / strata documents' page lines): book title, page,
3 lines before and after. No font label, no stratum, no detector output. Writes two sheets of 300 items (A, B) and
round1_index.json (item -> stem, line_index, page; kept out of the sheets).
    python3 build_round1.py <work_dir> <gold_dir> <out_dir>"""
import csv, json, os, sys, random
W, GD, OUT = sys.argv[1:4]
key = json.load(open(os.path.join(GD, "gold_sheet_KEY.json")))
rows = {r["id"]: r for r in csv.DictReader(open(os.path.join(GD, "gold_sheet.csv")))}
docs = {}
for f in ("answer_key_v5.jsonl", "train_v5_lowcode.jsonl", "strata_v5_books.jsonl", "strata_v5_lowcode.jsonl", "strata_v5_tiny.jsonl"):
    for l in open(os.path.join(W, f)):
        d = json.loads(l); docs.setdefault(d["stem"], d)
items, index = [], {}
for iid, k in sorted(key.items()):
    if k["part"] != "TEST": continue
    d = docs[k["stem"]]; flat, page_of = [], []
    for pn, p in enumerate(d["pages"]):
        for t, _ in p["lines"]: flat.append(t); page_of.append(p.get("page", pn + 1))
    i = k["line_index"]; assert flat[i] == rows[iid]["TARGET"], iid          # same line as the gold sheet
    items.append({"id": iid, "book": k["stem"], "page": page_of[i], "before": flat[max(0, i - 3):i], "TARGET": flat[i], "after": flat[i + 1:i + 4]})
    index[iid] = {"stem": k["stem"], "line_index": i, "page": page_of[i]}
random.Random(20261117).shuffle(items)
instr = ("Each item shows one TARGET line extracted from a technical document, with the book or paper title, the page, and up to "
         "3 lines before and after. Judge only the TARGET line: code / not_code / ambiguous.")
for part, chunk in (("A", items[:300]), ("B", items[300:])):
    json.dump({"instructions": instr, "items": chunk}, open(os.path.join(OUT, f"round1_sheet_{part}.json"), "w"), indent=1, ensure_ascii=False)
json.dump(index, open(os.path.join(OUT, "round1_index.json"), "w"), indent=1)
print(len(items), "items:", len(items[:300]), "+", len(items[300:]))
