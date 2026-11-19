"""ETDI-1.0.742 phase A (HTC env, no model): the 1,049 held-out chapters of the 2026-10-20 anchor curation run
(AnchorCurationPackets.merge_verdicts — the set the promoted anchors never saw), each with its WHOLE raw text
(user decision 2026-10-26: read in pieces through UnitScorer; the curation gate's 2,000-char cut does not apply).
    cd htc-multidim-classification-service && python3 <this> <out.json>"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
from src.features.ClassifyCorpus.taxonomy.anchor_curation_packets import AnchorCurationPackets
from src.features.ClassifyCorpus.taxonomy.anchor_text_miner import raw_chapters
from src.features.ClassifyCorpus.taxonomy.parse_appendix import parse_appendix

RUN = Path("output/anchor_curation/2026-10-20")
RAW = Path("<CORPUS_ROOT>/collections/software-engineering/raw")
APPENDIX = Path("../ai-platform-documentation/SDLC/Complete/HTC-MULTIDIM-2.0_ Dynamic Multi-Dimensional Classification System — Design Document.md")
appendix = parse_appendix(APPENDIX)
names = {s: " ".join(s.split("-")) for d in appendix.domains for s in d.subdomain_slugs}
merge = AnchorCurationPackets().merge_verdicts(RUN / "packets", RUN / "verdicts", appendix, names)
by_stem = {}
for refs in merge.held_out.values():
    for ref in refs:
        by_stem.setdefault(ref.rsplit("#", 1)[0], set()).add(ref)
text_of = {}
for stem, wanted in by_stem.items():
    path = RAW / f"{stem}.json"
    if path.exists():
        text_of.update({r: t for r, t in raw_chapters(json.loads(path.read_text()), stem, max_chars=10**9) if r in wanted})
held = {slug: [(r, text_of[r]) for r in refs if r in text_of] for slug, refs in merge.held_out.items()}
held = {s: v for s, v in held.items() if v}
n = sum(len(v) for v in held.values())
json.dump(held, open(sys.argv[1], "w"), ensure_ascii=False)
lens = sorted(len(t) for v in held.values() for _, t in v)
print(json.dumps({"chapters": n, "subdomains": len(held), "missing": sum(len(v) for v in merge.held_out.values()) - n,
                  "chars_median": lens[len(lens) // 2], "chars_p90": lens[int(len(lens) * .9)], "chars_max": lens[-1]}))
