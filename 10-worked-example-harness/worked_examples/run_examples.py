"""Worked examples, step 4 (HTC env, no model): run search_sim on each question's real pool and write what each option
delivers. Output: examples_out.json {question: {...}}.   cd htc-multidim-classification-service && python3 <this> [Q ...]"""
import json, os, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, os.getcwd())
import numpy as np
import search_sim as S

OUT = HERE / "examples_out.json"
res = json.loads(OUT.read_text()) if OUT.exists() else {}
want = sys.argv[1:] or ["A5", "A6", "A7", "B3", "B4", "B6", "E3", "A1", "A3", "A11", "A9"]
CUT = "Gate Smashers_Machine Learning_New to ML Follow These Steps to Build Any Machine Learning Model"   # 40% of 376,000 in name order


def card(c, extra=None):
    d = {"id": c["id"], "book": c["book"], "chapter": c["chapter"], "pages": c["pages"], "cos": round(c["cos"], 3),
         "filed": f"{c['domain']}/{c['subdomain']}", "kf": c["kf"], "sec": sorted({s for _, s, _ in c["secondaries"]})}
    d.update(extra or {}); return d


def delivered(cands, r):
    return [card(cands[x["id"]], {"ring": x.get("ring", 0)}) if x["id"] in cands else dict(x) for x in r["delivered"]]


for q in want:
    pool = {"A6": "A5"}.get(q, q)
    if q == "A7":
        cands, _ = S.load_pool("A7")
        vre = [{"id": "vre_CWE-611_GHSA-pc6w-59fv-rh23", "score": 0.5, "ring": 1}, {"id": "vre_CWE-611_GHSA-f83q-2cp7-qrjg", "score": 0.5, "ring": 1}]
        res[q] = {"no_warning": delivered(cands, S.respond(cands)), "today_if_vre_answered": delivered(cands, S.respond(cands, ring1_extra=vre))}
    elif q == "A5":
        cands, _ = S.load_pool("A5")
        excl = [k for k, c in cands.items() if c["book"] > CUT]
        res[q] = {"cutoff": CUT, "excluded": len(excl), "full": delivered(cands, S.respond(cands)), "partial": delivered(cands, S.respond(cands, exclude=excl))}
    elif q == "A6":
        cands, _ = S.load_pool("A6")
        res[q] = {m: delivered(cands, S.respond(cands, mmr=m)) for m in ("score_proxy", "real_cosine", "same_chapter")}
    elif q == "B4":
        cands, _ = S.load_pool("B3")
        res[q] = {"full": delivered(cands, S.respond(cands)), "ring1_dropped": delivered(cands, S.respond(cands, drop_ring=1)),
                  "ring3_dropped": delivered(cands, S.respond(cands, drop_ring=3))}
    elif q == "B3":
        cands, qv = S.load_pool("B3")
        ch = sorted(cands.values(), key=lambda c: -c["cos"])
        pieces = []
        for c in cands.values():
            v = c["pieces"] / np.linalg.norm(c["pieces"], axis=1, keepdims=True)
            for i, s in enumerate(v @ qv):
                pieces.append({"id": f"{c['id']}#p{i}", "chapter_id": c["id"], "cos": float(s)})
        pieces.sort(key=lambda p: -p["cos"])
        mixed = sorted([{"id": c["id"], "chapter_id": c["id"], "cos": c["cos"], "tier": "chapter"} for c in ch] +
                       [dict(p, tier="passage") for p in pieces], key=lambda x: -x["cos"])
        res[q] = {"chapters_first": [card(c) for c in ch[:10]],
                  "mixed_top10": [dict(x, book=cands[x["chapter_id"]]["book"], chapter=cands[x["chapter_id"]]["chapter"]) for x in mixed[:10]],
                  "passages_top10": [dict(p, book=cands[p["chapter_id"]]["book"], chapter=cands[p["chapter_id"]]["chapter"]) for p in pieces[:10]],
                  "delivered": delivered(cands, S.respond(cands))}
    elif q == "A1x":
        cands, _ = S.load_pool("A1", drop="quantum-algorithms")
        r = S.respond(cands)
        res[q] = {"ranked": [card(c) for c in sorted(cands.values(), key=lambda c: -c["cos"])[:15]], "hit": r["hit"], "delivered": delivered(cands, r)}
    else:
        cands, _ = S.load_pool(pool)
        r = S.respond(cands)
        res[q] = {"ranked": [card(c) for c in sorted(cands.values(), key=lambda c: -c["cos"])[:15]],
                  "hit": r["hit"], "rings": r["rings"], "delivered": delivered(cands, r)}
    OUT.write_text(json.dumps(res, indent=1)); print(q, "done", flush=True)
