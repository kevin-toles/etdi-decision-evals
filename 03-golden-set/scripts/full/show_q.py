"""Golden set full run: print one Stack Exchange thread from full/threads.jsonl (extracted once from the pool) — title,
body, tags, and the answers a key point may cite (accepted, or score >= 10), each with its id and score.
python3 -I <this> <qid e.g. dba:1285>"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
for line in open(f"{HERE}/threads.jsonl"):
    d = json.loads(line)
    if d["qid"] != sys.argv[1]: continue
    acc = str(d.get("accepted_answer_id") or "")
    print(f"# {d['qid']}  score {d['score']}  tags {d['tags']}\nTITLE: {d['title']}\nBODY: {d['body'][:3000]}\n")
    for a in sorted(d["answers"], key=lambda a: -int(a["score"])):
        if str(a["id"]) == acc or int(a["score"]) >= 10:
            print(f"--- ANSWER {a['id']}  score {a['score']}{'  ACCEPTED' if str(a['id']) == acc else ''}\n{a['body']}\n")
    break
else:
    sys.exit("not found in threads.jsonl")
