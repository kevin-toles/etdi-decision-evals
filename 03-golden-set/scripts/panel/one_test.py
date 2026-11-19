import json, sys, time, urllib.request, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import rubric
EV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r = [json.loads(l) for l in open(f"{EV}/records_pilot.jsonl")][0]
q = {x["qid"]: x for x in json.load(open(f"{EV}/questions_pilot.json"))["questions"]}[r["qid"]]
base = f"http://127.0.0.1:{sys.argv[1]}"
for _ in range(120):
    try:
        if urllib.request.urlopen(base + "/health", timeout=5).status == 200: break
    except Exception: time.sleep(5)
t = time.time()
body = {"messages": [{"role": "system", "content": rubric.SYSTEM}, {"role": "user", "content": rubric.item_message(r, q)}],
        "temperature": 0, "max_tokens": 900, "cache_prompt": True, "chat_template_kwargs": {"enable_thinking": False}, "json_schema": rubric.SCHEMA,
        "response_format": {"type": "json_schema", "json_schema": {"name": "verdict", "schema": rubric.SCHEMA}}}
try:
    out = json.load(urllib.request.urlopen(urllib.request.Request(base + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=900))
    print(round(time.time() - t, 1), "s", out["choices"][0]["message"]["content"][:700], out.get("usage"))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:600])
