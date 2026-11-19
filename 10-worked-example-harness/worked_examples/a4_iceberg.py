"""A4 worked example: the code blocks an agent would get from real chapters under today's detector, option (a) (the
narrow colon fix, NarrowColonDetector from code_label_audit/scripts/compare_prose_fix.py) and option (b) (the design's
min_confidence 0.5). Real COS HeuristicCodeDetector + LanguageDetector on the raw chapter text. No model is loaded.
    cd Code-Orchestrator-Service && .venv/bin/python <this> > a4_iceberg.txt"""
import json, os, sys
sys.path.insert(0, os.getcwd())
from src.extractors.code_block_extractor import HeuristicCodeDetector
src = open("<EVIDENCE>/code_label_audit/scripts/compare_prose_fix.py").read()
exec(src[src.index("class NarrowColonDetector"):src.index("STOP = set(")], globals())
try:
    from src.extractors.language_detector import LanguageDetector
except Exception:
    LanguageDetector = None
RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
CH = [("Apache Iceberg - The Definitive Guide", 165, 169)] + [tuple(x) for x in json.loads(sys.argv[1])] if len(sys.argv) > 1 else [("Apache Iceberg - The Definitive Guide", 165, 169)]
ld = LanguageDetector() if LanguageDetector else None
for book, s, e in CH:
    d = json.load(open(f"{RAW}/{book}.json"))
    pg = {int(p["page_number"]): p.get("text") or "" for p in d["pages"] if str(p.get("page_number", "")).isdigit()}
    text = "\n".join(pg.get(i, "") for i in range(s, e + 1))
    print(f"\n######## {book} pp. {s}-{e}")
    for name, det, floor in (("today", HeuristicCodeDetector(), 0.0), ("(a) narrow colon", NarrowColonDetector(), 0.0), ("(b) min_confidence 0.5", HeuristicCodeDetector(), 0.5)):
        cs = [c for c in det.detect_candidates(text) if c.confidence >= floor]
        print(f"\n== {name}: {len(cs)} blocks")
        for c in cs:
            lang = ""
            if ld:
                try:
                    r = ld.detect(c.content); lang = f"{getattr(r, 'language', r)} {getattr(r, 'confidence', '')}"
                except Exception as ex:
                    lang = f"(lang err {ex})"
            print(f"-- conf {c.confidence:.2f} lang {lang}\n{c.content[:400]}")
