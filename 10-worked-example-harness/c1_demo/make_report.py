"""Render every demo_result_*.json variant as one markdown comparison (C1 / ETDI #40)."""
import json, glob, re
OPT = {"today": "Today (current code)", "a": "(a) after the bridge", "b": "(b) rank score near the bridge",
       "c": "(c) merged into Ring 3 before fusion", "d": "(d) re-ranked by similarity to the question", "e": "(e) re-fused, floor-admitted"}
def title(m, cid):
    c = m[cid]; b = re.sub(r"^(HashiCorp, an IBM Company|infoq-case-studies|Confreaks|edureka!|freeCodeCamp\.org|Abhishek\.Veeramalla|DevOps & AI Toolkit|Neo4j)_", r"\1: ", c["book"])
    ch = c["chapter"].strip().rstrip(".")
    return f"{b[:70]} — {ch[:45]}"
out = ["# C1 / ETDI #40 demo — what each option delivers",
       "", "Question: **How should I rotate database credentials?** — 164 real SE chapters (keyword scan of 20,000 books), embedded with nomic-v2, filed by the real HTC scorer, rings + cascade + RRF + MMR (ScoreProxy) + budget trim ported from unified-search-rs. `cos` = similarity to the question. Ring 0* = a result the cascade returned without a ring tag (today's code files it under ring 0).", ""]
files = sorted(glob.glob("demo_result_T*.json"))
out += ["## Variants", "", "| Variant | Pool floor | Ring 1 / 2 / 3 results | Ring 3 target subjects | Bridges | Follow-ons (distinct / new) | Delivered: today / (a) / (d) / (e) |", "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
for f in files:
    j = json.load(open(f)); v = f[len("demo_result_"):-5].replace("_", " ")
    rings = {k: len(x) for k, x in j["rings"].items()}
    fol = {x for l in j["follow_ons"].values() for x in l}; inring = {r["id"] for l in j["rings"].values() for r in l}
    out.append(f"| {v} | {j['floor']:.3f} | {rings.get('1',0)} / {rings.get('2',0)} / {rings.get('3',0)} | {len(j['ring3_targets'])} | {len(j['bridges'])} | {len(fol)} / {len(fol - inring)} | "
               + " / ".join(str(len(j['delivered'][k])) for k in ('today','a','d','e')) + " |")
for f in files:
    j = json.load(open(f)); m = j["meta"]; v = f[len("demo_result_"):-5].replace("_", " ")
    out += ["", f"## {v}", "", f"Best match (Ring 0, shown separately): **{title(m, j['hit'])}** — cos {m[j['hit']]['cos']:.3f}, filed under `{j['hit_filing'][1]}`.", ""]
    if not j["bridges"]:
        out += ["No Ring 3 results, so no cascade: **every option delivers the same response.**", ""]
        keys = ["today"]
    else:
        keys = list(OPT)
    for k in keys:
        out += [f"**{OPT[k] if j['bridges'] else 'All options'}** — {len(j['delivered'][k])} results", "", "| # | Ring | Result | Filed under | cos |", "| :--- | :--- | :--- | :--- | :--- |"]
        for i, r in enumerate(j["delivered"][k][:15]):
            ring = r.get("ring", 0); tag = "0*" if ring == 0 else str(ring)
            via = f" (follow-on of {title(m, r['via'])[:40]}…)" if "via" in r and r["via"] != r["id"] else ""
            out.append(f"| {i+1} | {tag} | {title(m, r['id'])}{via} | `{m[r['id']]['subdomain']}` | {m[r['id']]['cos']:.3f} |")
        if len(j["delivered"][k]) > 15:
            out.append(f"| … | | {len(j['delivered'][k]) - 15} more | | |")
        out.append("")
open("C1_DEMO_RESULTS.md", "w").write("\n".join(out)); print("ok", len(out))
