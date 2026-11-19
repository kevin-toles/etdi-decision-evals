"""Golden set pilot: pull the frozen pilot questions (id, site) with their accepted answer from the local Stack Exchange
extract, with the answers a key point may cite (accepted, or score >= 10). Read-only.   python3 -I <this> <out.json>"""
import ast, json, sys
G = "<ETL_RAW_ROOT>/data/stackexchange"
PICK = {  # qid: (site file, tier)
 "11227809": ("stackoverflow.jsonl", "senior"), "211": ("primary/security.jsonl", "senior"),
 "24068": ("primary/networkengineering.jsonl", "senior"), "27860": ("primary/cs.jsonl", "senior"),
 "144": ("primary/dba.jsonl", "senior"),
 "202": ("primary/crypto.jsonl", "principal"), "3": ("primary/cs.jsonl", "principal"),
 "447": ("primary/devops.jsonl", "principal"), "10188": ("primary/datascience.jsonl", "principal"),
 "12346326": ("stackoverflow.jsonl", "principal"),
 "12156517": ("stackoverflow.jsonl", "distinguished"), "2812": ("primary/langdev.jsonl", "distinguished"),
 "2106": ("primary/quantumcomputing.jsonl", "distinguished"), "3921": ("primary/cstheory.jsonl", "distinguished"),
 "45486": ("primary/cs.jsonl", "distinguished"),
}
out = []
for f in sorted({v[0] for v in PICK.values()}):
    want = {q for q, v in PICK.items() if v[0] == f}
    for line in open(f"{G}/{f}"):
        d = json.loads(line)
        if d["id"] not in want: continue
        ans = d["answers"] if isinstance(d["answers"], list) else ast.literal_eval(d["answers"])
        acc = next((a for a in ans if str(a["id"]) == str(d["accepted_answer_id"])), None)
        key_src = [a for a in sorted(ans, key=lambda a: -int(a["score"])) if a is acc or int(a["score"]) >= 10][:4]
        out.append({"qid": f"{d['site']}:{d['id']}", "site": d["site"], "tier": PICK[d["id"]][1], "title": d["title"],
                    "body": d["body"], "tags": d["tags"], "score": int(d["score"]),
                    "accepted_answer_id": str(d["accepted_answer_id"]),
                    # key points may cite only these: the accepted answer and answers scoring >= 10 (human-vetted ground truth)
                    "key_source_answers": [{"id": str(a["id"]), "score": int(a["score"]), "accepted": a is acc, "body": a["body"]} for a in key_src]})
        want.discard(d["id"])
        if not want: break
print(len(out), "of", len(PICK))
json.dump(out, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
