"""Golden-set panel: write blind item sheets (one shuffled order and opaque item ids per panelist) and the pinned-model
grader agent definitions whose instructions are rubric.SYSTEM verbatim. Sheets carry only question, key points and
passage text — never the proposer's grade, covers, role, labels or notes.   python3 -I <this>"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rubric

HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE)
RUN = os.environ.get("GS_RUN", "pilot")          # "full" (2026-11-15): sheets/full/, item_key_full.json, agent files untouched
records = [json.loads(l) for l in open(f"{EV}/records_{RUN}.jsonl")]
qs = {q["qid"]: q for q in json.load(open(f"{EV}/questions_{RUN}.json"))["questions"]}
SD = f"{HERE}/sheets" + ("" if RUN == "pilot" else f"/{RUN}")
PANEL = {"sonnet-5-5": "claude-sonnet-5-5", "opus-4-8": "claude-opus-4-8", "fable-5-2": "claude-fable-5-2"}
SHEET_SIZE = 32
os.makedirs(SD, exist_ok=True); os.makedirs(SD.replace("/sheets", "/verdicts"), exist_ok=True)
key = {}
for p, (tag, model) in enumerate(PANEL.items()):
    rng = random.Random((20261113 if RUN == "pilot" else 20261115) + p)
    order = records[:]; rng.shuffle(order)
    ids = [f"{tag[:2]}{rng.randrange(16**6):06x}" for _ in order]
    for s in range(0, len(order), SHEET_SIZE):
        items = [{"item_id": i, "text": rubric.item_message(r, qs[r["qid"]]),
                  "key_point_ids": [k["id"] for k in qs[r["qid"]]["key_points"]]}
                 for i, r in zip(ids[s:s + SHEET_SIZE], order[s:s + SHEET_SIZE])]
        json.dump({"panelist": tag, "items": items}, open(f"{SD}/{tag}-{s // SHEET_SIZE + 1}.json", "w"), indent=1, ensure_ascii=False)
    key[tag] = {i: r["record_id"] for i, r in zip(ids, order)}
json.dump(key, open(f"{HERE}/item_key" + ("" if RUN == "pilot" else f"_{RUN}") + ".json", "w"), indent=1)   # opaque id -> record id; never shown to panelists
agent_dir = "<AGENTS_DIR>"
for tag, model in (PANEL.items() if RUN == "pilot" else []):   # agent files are frozen with the rubric
    body = rubric.SYSTEM.replace("Answer with one JSON object only, exactly matching the schema.", "") + f"""
OUTPUT: you will be given a sheet path and an output path. Read the sheet (a JSON object with "items", each with
"item_id", "text" and "key_point_ids"). Grade every item independently. Write exactly the output file: a JSON object
{{"model": "{model}", "verdicts": {{"<item_id>": {{"grade": 0-3, "covers": [...], "beyond_key_points": bool,
"role": "direct"|"foundation"|"none", "primary": {{"domain": "...", "subdomain": "..."}}, "secondary": [...],
"knowledge_function": "...", "ambiguous": bool, "note": "..."}}, ...}}}} covering every item id, and nothing else.
Then reply with one line: the number of items graded.
"""
    open(f"{agent_dir}/panel-grader-{tag}.md", "w").write(
        f"---\nname: panel-grader-{tag}\ndescription: Blind grader for the ETDI golden-set panel ({model}). Reads an item sheet, grades each passage against the question's key points and files it in the HTC taxonomy, writes verdicts JSON.\nmodel: {model}\ntools: Read, Write\n---\n{body}")
print("sheets", len(os.listdir(SD)), "in", SD)
