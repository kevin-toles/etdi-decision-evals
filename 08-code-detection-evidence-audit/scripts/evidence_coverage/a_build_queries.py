"""Evidence coverage, step 1A: items and retrieval queries (no model, no LLM). Pre-registered rules:
  normalise: unicode minus/quotes/visible-space -> ASCII; runs of >=3 single characters separated by single spaces are
             joined ("r u l e s e t s" -> "rulesets"); whitespace collapsed; leading shell prompts stripped
             ("$ ", "% ", "> ", ">>> ", "(env) $ ")
  eligible line: >=4 word tokens ([A-Za-z0-9_]+) and >=20 characters after normalising; otherwise generic, never queried
  generic by frequency: a phrase with more than 50 FTS chapter hits is recorded as generic and gives no lead (step 1B)
  blocks: every eligible line, plus 3-line shingles of consecutive eligible lines (contiguity checked from line hits);
          split fragments also pair their first/last line with the neighbouring document line
  distinctive tokens: identifier/command-shaped tokens (dotted, snake_case, camelCase, path, --flag, call()) per item
  own document excluded later by normalised title ([DUPE] and case/punctuation removed)
    python3 a_build_queries.py <out_dir>"""
import json, os, re, sys
EV = sys.argv[1]; CL = os.path.dirname(EV)
sys.path.insert(0, EV)
from a_build_queries_lib import norm   # shared with c_fts_leads.py
WORD = re.compile(r"[A-Za-z0-9_]+")
eligible = lambda s: len(WORD.findall(s)) >= 4 and len(s) >= 20
TOK = re.compile(r"--?[A-Za-z][\w-]+|[A-Za-z_][\w]*(?:[./:][\w-]+)+|[a-z]+_[\w]+|[a-z]+[A-Z]\w*|[A-Za-z_]\w*\(")
def distinctive(lines):
    out = []
    for l in lines:
        for t in TOK.findall(l):
            t = t.rstrip("(")
            if len(t) >= 4 and t not in out: out.append(t)
    return out[:8]
items = []
gp = json.load(open(os.path.join(CL, "gold_panel_2026-11-17", "panel_results.json")))
sheet = {x["id"]: x for p in "AB" for x in json.load(open(os.path.join(CL, "gold_panel_2026-11-17", f"round1_sheet_{p}.json")))["items"]}
for iid, it in gp["per_item"].items():
    if it["final"] == "unresolved": continue
    t = norm(sheet[iid]["TARGET"])
    items.append({"id": iid, "set": "gold_line", "stem": it["stem"], "segment": it["stratum"].split("/")[0], "panel_label": it["final"],
                  "font_label": it["stratum"].split("/")[1], "lines": [sheet[iid]["TARGET"]], "norm_lines": [t],
                  "line_queries": [t] if eligible(t) else [], "shingles": [], "pair_queries": [], "tokens": distinctive([t])})
bc = json.load(open(os.path.join(CL, "bad_block_causes_2026-11-17", "causes_results.json")))
bsheet = {x["id"]: x for p in "AB" for x in json.load(open(os.path.join(CL, "bad_block_causes_2026-11-17", f"round1_sheet_{p}.json")))["items"]}
SEGMAP = {"book": "book", "short": "short", "tiny": "short", "40-book key": "book", "lowcode": "low-code", "codefree": "code-free"}
for iid, it in bc["per_item"].items():
    s = bsheet[iid]; nl = [norm(l) for l in s["BLOCK"]]; el = [l for l in nl if eligible(l)]
    sh = [nl[i:i + 3] for i in range(len(nl) - 2) if all(eligible(x) for x in nl[i:i + 3])]
    pairs = []
    if it["final"] == "split_fragment":
        if s["before"] and eligible(norm(s["before"][-1])) and el: pairs.append([norm(s["before"][-1]), nl[0]])
        if s["after"] and eligible(norm(s["after"][0])) and el: pairs.append([nl[-1], norm(s["after"][0])])
    items.append({"id": iid, "set": "bad_block", "stem": it["stem"], "segment": SEGMAP[it["segment"]], "panel_label": it["final"],
                  "options": it["options"], "lines": s["BLOCK"], "norm_lines": nl, "line_queries": sorted(set(el)), "shingles": sh,
                  "pair_queries": pairs, "neighbours": {"before": [norm(x) for x in s["before"][-3:]], "after": [norm(x) for x in s["after"][:3]]},
                  "tokens": distinctive(nl)})
pats = sorted({q for it in items for q in it["line_queries"] + [x for p in it["pair_queries"] for x in p if eligible(x)]})
json.dump(items, open(os.path.join(EV, "items.json"), "w"), indent=1, ensure_ascii=False)
open(os.path.join(EV, "line_patterns.txt"), "w").write("\n".join(pats) + "\n")
n_gold = sum(i["set"] == "gold_line" for i in items); n_blk = len(items) - n_gold
print({"gold_lines": n_gold, "gold_eligible": sum(1 for i in items if i["set"] == "gold_line" and i["line_queries"]),
       "blocks": n_blk, "blocks_with_eligible_line": sum(1 for i in items if i["set"] == "bad_block" and i["line_queries"]),
       "unique_line_patterns": len(pats), "shingles": sum(len(i["shingles"]) for i in items), "token_sets": sum(1 for i in items if i["tokens"])})
