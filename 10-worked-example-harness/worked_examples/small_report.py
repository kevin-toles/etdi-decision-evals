"""Print the C9 / A10 / A9 rankings from small_cos.json with the texts they rank."""
import json, re
from pathlib import Path
H = Path(__file__).parent
S = json.loads((H / "small_cos.json").read_text()); D = json.loads((H / "diagrams.json").read_text())
EN = "<CORPUS_ROOT>/collections/software-engineering/enriched"
for k, rows in (("C9", D["C9"]), ("A10", D["A10"][:200])):
    cs = S[k]["cos"]; order = sorted(range(len(cs)), key=lambda i: -cs[i])
    print(f"\n== {k}: {S[k]['query']} ({len(cs)} texts)")
    for i in order[:12]:
        r = rows[i]; print(f"{cs[i]:.3f} toc={r['toc_like']} repr={r['repr_wrapped']} | {r['book'][:55]} | {(r['chapter'] or '')[:25]} | {' '.join(r['content'].split())[:130]}")
e = json.load(open(f"{EN}/Real-World Algorithms A Beginners Guide_enriched.json"))
blocks = [b for ch in e["chapters"] if ch["start_page"] == 375 for b in ch["code_blocks"]]
cs = S["A9"]["cos"]
print("\n== A9 (book order, cos)")
for i, b in enumerate(blocks): print(f"{i+1} {cs[i]:.3f} {b.get('language')} | {' '.join(b['content'].split())[:120]}")
print("rank by cos:", [i + 1 for i in sorted(range(len(cs)), key=lambda i: -cs[i])])
