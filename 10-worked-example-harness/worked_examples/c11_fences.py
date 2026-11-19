"""C11 worked example: the fenced blocks of two real SE-library papers, with today's fixed 0.85, the fence's language
tag, and the COS HeuristicCodeDetector's own judgement of the block's content (option (a)'s main signal; highest
candidate confidence, 0 when it finds no code). No model.   cd Code-Orchestrator-Service && .venv/bin/python <this>"""
import json, os, re, sys
sys.path.insert(0, os.getcwd())
from src.extractors.code_block_extractor import HeuristicCodeDetector
RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
det = HeuristicCodeDetector()
for f in ("Self-Explained Keywords Empower Large Language Models for Code Generation", "MultiTEND A Multilingual Benchmark for Natural Language to NoSQL Query Translation"):
    d = json.load(open(f"{RAW}/{f}.json")); t = "\n".join((p.get("text") or "") for p in d["pages"])
    print(f"\n## {f}")
    for lang, b in re.findall(r"```(\w*)\n(.*?)```", t, re.S):
        cs = det.detect_candidates(b); conf = max((c.confidence for c in cs), default=0.0)
        print(f"tag={lang or '(none)':10s} lines={len([l for l in b.splitlines() if l.strip()]):3d} detector={conf:.2f} | {' '.join(b.split())[:150]}")
