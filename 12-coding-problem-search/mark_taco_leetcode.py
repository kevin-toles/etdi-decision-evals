"""List TACO records that are LeetCode problems: starter_code is a LeetCode `class Solution` signature.
Also counts how many carry solutions. Output: taco_leetcode_style.json {doc_ids, n_with_solutions}.
Usage: python3 -I mark_taco_leetcode.py <data_dir> <xref_dir>
"""
import ast, glob, json, os, sys
B, X = sys.argv[1], sys.argv[2]
ids, nsol = [], 0
for f in sorted(glob.glob(f"{B}/taco/taco-*.json")):
    d = json.load(open(f)); c = d.get("content")
    try: c = ast.literal_eval(c) if isinstance(c, str) else c
    except Exception: continue
    if isinstance(c, dict) and str(c.get("starter_code", "")).lstrip().startswith("class Solution"):
        ids.append(f"taco:{d['reference_id']}")
        try: nsol += bool(json.loads(c.get("solutions") or "[]"))
        except Exception: pass
json.dump({"doc_ids": ids, "n_with_solutions": nsol}, open(f"{X}/taco_leetcode_style.json", "w"))
print("TACO LeetCode-style", len(ids), "with solutions", nsol)
