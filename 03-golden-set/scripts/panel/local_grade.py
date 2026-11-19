"""Golden-set panel, local seat calibration: grade the 128 pilot items with a local model served by
inference-service-cpp's llama-server (OpenAI-compatible /v1/chat/completions), same frozen rubric.SYSTEM and per-item
message as the Claude panel, JSON schema enforced by llama.cpp's grammar. Temperature 0. Resumable (skips graded
items).   python3 -I <this> <model_tag> <port> <out.json>"""
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rubric
HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE)
tag, port, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
records = [json.loads(l) for l in open(f"{EV}/records_pilot.jsonl")]
qs = {q["qid"]: q for q in json.load(open(f"{EV}/questions_pilot.json"))["questions"]}
res = json.load(open(out)) if os.path.exists(out) else {"model": tag, "verdicts": {}, "errors": {}, "seconds": {}}
base = f"http://127.0.0.1:{port}"
for _ in range(180):                                  # wait up to 15 min for the model to load
    try:
        if urllib.request.urlopen(f"{base}/health", timeout=5).status == 200: break
    except Exception: pass
    time.sleep(5)
else:
    sys.exit("server never became healthy")

def ask(messages):
    body = {"messages": messages, "temperature": 0, "max_tokens": 900, "cache_prompt": True, "chat_template_kwargs": {"enable_thinking": False}, "json_schema": rubric.SCHEMA,
            "response_format": {"type": "json_schema", "json_schema": {"name": "verdict", "schema": rubric.SCHEMA}}}
    req = urllib.request.Request(f"{base}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))["choices"][0]["message"]["content"]

import subprocess
def pressure():
    lvl = int(subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], capture_output=True, text=True).stdout or 0)
    sw = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
    free_mb = float(sw.split("free = ")[1].split("M")[0]) if "free = " in sw else 1e9
    return lvl, free_mb
strikes = 0
for n, r in enumerate(records, 1):
    rid = r["record_id"]
    lvl, swap_free = pressure()                      # memory-safety guard (two past kernel panics)
    strikes = strikes + 1 if (lvl >= 2 or swap_free < 600) else 0
    if strikes >= 2:
        print(f"ABORT memory guard: pressure level {lvl}, swap free {swap_free:.0f} MB", flush=True); sys.exit(3)
    if rid in res["verdicts"]: continue
    q = qs[r["qid"]]
    msgs = [{"role": "system", "content": rubric.SYSTEM}, {"role": "user", "content": rubric.item_message(r, q)}]
    t0 = time.time()
    try:
        txt = ask(msgs); ans = json.loads(txt); probs = rubric.validate(ans, q)
        if probs:   # one retry with the validator's findings
            msgs += [{"role": "assistant", "content": txt},
                     {"role": "user", "content": "Invalid: " + "; ".join(probs) + ". Answer again with valid slugs and key point ids."}]
            txt = ask(msgs); ans = json.loads(txt); probs = rubric.validate(ans, q)
        res["verdicts"][rid] = ans
        if probs: res["errors"][rid] = probs
    except Exception as e:
        res["errors"][rid] = [repr(e)[:300]]
    res["seconds"][rid] = round(time.time() - t0, 1)
    json.dump(res, open(out, "w"), indent=1)
    print(n, rid, res["seconds"][rid], "s", "ERR" if rid in res["errors"] else "", flush=True)
print("done", len(res["verdicts"]), "verdicts,", len(res["errors"]), "with errors")
