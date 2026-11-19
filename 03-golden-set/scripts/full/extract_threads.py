"""Golden set full run: copy every pool question's full thread into full/threads.jsonl (one pass over the extract) so
proposers never scan the 15 GB file. Read-only on the extract.   python3 -I <this>"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
G = "<ETL_RAW_ROOT>/data/stackexchange"
pool = json.load(open(f"{HERE}/pool.json"))["pool"]
want = collections.defaultdict(dict)
for rows in pool.values():
    for r in rows: want[r["file"]][r["id"]] = r["qid"]
n = 0
with open(f"{HERE}/threads.jsonl", "w") as out:
    for f, ids in want.items():
        left = dict(ids)
        for line in open(f"{G}/{f}"):
            i = line.find('"id": "'); qid = line[i + 7:line.find('"', i + 7)] if i >= 0 else None
            if qid not in left: continue
            d = json.loads(line); d["qid"] = left.pop(qid)
            for k in ("body_html",): d.pop(k, None)
            out.write(json.dumps(d, ensure_ascii=False) + "\n"); n += 1
            if not left: break
        print(f, len(ids) - len(left), "of", len(ids), flush=True)
print("threads", n)
