"""Seeded sample of SE raw chapters with real jina-v3 token counts and a code-line ratio — no model, tokenizer only."""
import json, os, random, re, sys
from transformers import AutoTokenizer
RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
tok = AutoTokenizer.from_pretrained("jinaai/jina-embeddings-v3", local_files_only=True)
names = [e.name for e in os.scandir(RAW) if e.name.endswith(".json") and "[DUPE]" not in e.name]
random.Random(20261026).shuffle(names)
CODE = re.compile(r"^\s{2,}\S|[{};]\s*$|^\s*(def|class|import|return|public|private|func|fn|let|var|const)\b")
rows = []
for n in names[:400]:
    try:
        d = json.load(open(os.path.join(RAW, n)))
    except Exception:
        continue
    for c in (d.get("chapters") or [])[:40]:
        text = c.get("content") or ""
        if len(text) < 400:
            continue
        lines = [l for l in text.splitlines() if l.strip()]
        code = sum(1 for l in lines if CODE.search(l)) / max(len(lines), 1)
        rows.append({"file": n, "chapter": c.get("number"), "title": (c.get("title") or "")[:70],
                     "tokens": len(tok(text, add_special_tokens=False)["input_ids"]), "code_ratio": round(code, 2),
                     "chars": len(text)})
    if len(rows) > 1500:
        break
json.dump(rows, open(sys.argv[1], "w"))
toks = sorted(r["tokens"] for r in rows)
q = lambda p: toks[int(p * (len(toks) - 1))]
print(f"files read: {len(set(r['file'] for r in rows))}, chapters: {len(rows)}")
print(f"tokens median {q(.5)}, p90 {q(.9)}, p99 {q(.99)}, max {toks[-1]}; >8160: {sum(t > 8160 for t in toks)} ({sum(t > 8160 for t in toks)/len(toks):.1%}); >512: {sum(t>512 for t in toks)/len(toks):.1%}")
print(f"code_ratio > 0.5: {sum(r['code_ratio'] > 0.5 for r in rows)}")
