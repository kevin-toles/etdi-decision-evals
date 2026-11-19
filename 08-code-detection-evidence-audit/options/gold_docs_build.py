"""Collect every document holding a four-reviewer consensus line (runs a, b, d and c), from the key version that
run sampled, into gold_docs.json {stem: doc record}. Line indices in the runs refer to these records."""
import json, os, sys
S = os.path.dirname(os.path.abspath(__file__))
E = sys.argv[1]
src = {"run_2026-10-28": "answer_key_v3.jsonl", "run_2026-10-28b": "answer_key_v4.jsonl", "run_2026-10-29d": "answer_key_v5.jsonl", "run_2026-10-28c_lowcode": "strata_lowcode.jsonl"}
want = {}
for run, key in src.items():
    for v in json.load(open(os.path.join(E, run, "font_labels_HIDDEN.json"))).values():
        want.setdefault(key, set()).add(v["stem"])
docs = {}
for key, stems in want.items():
    for line in open(os.path.join(S, key)):
        d = json.loads(line)
        if d["stem"] in stems and d["stem"] not in docs:
            docs[d["stem"]] = d
json.dump(docs, open(os.path.join(S, "gold_docs.json"), "w"))
print(len(docs), "gold documents;", sum(len(v) for v in want.values()), "requested (with overlaps)")
