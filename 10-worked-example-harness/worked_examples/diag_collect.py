"""C9 / A10 worked examples, step 1: real stored text "diagrams" (enriched ascii_diagrams) from 3,000 random enriched SE
books (seed 1112): every diagram mentioning a load balancer (C9) or MySQL's SHOW TABLES / a box-drawn table (A10),
with book, chapter, content (the Python repr wrapper some records carry is noted and stripped). Read-only.
    python3 -I <this> <out.json>"""
import json, os, random, re, sys
EN = "<CORPUS_ROOT>/collections/software-engineering/enriched"
fs = sorted(os.listdir(EN)); random.seed(1112); s = random.sample(fs, 3000)
REPR = re.compile(r"^ExtractedASCIIDiagram\(content=(['\"])(.*)\1\)$", re.S)
out = {"C9": [], "A10": [], "stats": {"diagrams": 0, "repr_wrapped": 0, "toc_like": 0}}
for f in s:
    try: d = json.load(open(f"{EN}/{f}"))
    except Exception: continue
    for ch in d.get("chapters") or []:
        for i, g in enumerate(ch.get("ascii_diagrams") or []):
            c = g.get("content", "") if isinstance(g, dict) else str(g)
            out["stats"]["diagrams"] += 1
            m = REPR.match(c.strip()); wrapped = bool(m)
            if wrapped:
                out["stats"]["repr_wrapped"] += 1; c = m.group(2).encode().decode("unicode_escape", "ignore")
            toc = len(re.findall(r"\.{8,}\s*\d+", c)) >= 2
            out["stats"]["toc_like"] += toc
            row = {"book": f[:-14], "chapter": ch.get("title"), "chapter_id": ch.get("chapter_id"), "index": i,
                   "repr_wrapped": wrapped, "toc_like": toc, "content": c[:3000]}
            low = c.lower()
            if "load balanc" in low or "loadbalancer" in low:
                out["C9"].append(row)
            if "show tables" in low or "tables_in_" in low or re.search(r"\+-{4,}\+", c):
                out["A10"].append(row)
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(out["stats"], len(out["C9"]), len(out["A10"]))
