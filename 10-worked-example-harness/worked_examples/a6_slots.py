"""A6 follow-up (user 2026-11-18): test option (a2) — real cosine MMR choosing which results fill each ring's slots —
against today (score proxy, MMR before the trim) and (a1) (real cosine, same position). Same pools, filing and ported
rules as search_sim.respond; the only changes are wider per-facet candidate searches (N_CAND) plus slot-filling by MMR
with real cosine against everything already placed (rings filled in order 1, 2, 3). No model loaded.
    cd htc-multidim-classification-service && python3 <this> [POOL ...]"""
import json, os, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, os.getcwd())
import numpy as np
import search_sim as S
N_CAND = 8          # candidates fetched per facet search before slot-filling (today: 2 = the slots themselves)
SLOTS = 2           # slots per facet search, as today

def respond_slots(cands):
    live = cands; ranked = sorted(live.values(), key=lambda c: -c["cos"])
    hit, pool = ranked[0], ranked[:S.POOL_SIZE]
    floor = float(np.clip(pool[0]["cos"] - np.std([c["cos"] for c in pool]), 0, 1))
    placed = []
    def pick(pred):
        cand = [c for c in ranked if pred(c) and c["id"] not in {p["id"] for p in placed}][:N_CAND]
        out = []
        while cand and len(out) < SLOTS:
            def mmr(c):
                sims = [float(c["vec"] @ live[p["id"]]["vec"]) for p in placed + out]
                return S.MMR_LAMBDA * c["cos"] - (1 - S.MMR_LAMBDA) * (max(sims) if sims else 0.0)
            best = max(cand, key=mmr); cand.remove(best); out.append({"id": best["id"]})
        return out
    rings = {1: [], 2: [], 3: []}
    for kf in S.RING1_KFS:
        got = pick(lambda c, kf=kf: c["subdomain"] == hit["subdomain"] and c["kf"] == kf); rings[1] += got; placed += got
    got = pick(lambda c: c["kf"] in S.RING2_KFS and any(s == hit["subdomain"] for _, s, _ in c["secondaries"])); rings[2] += got; placed += got
    targets = []
    for c in [hit] + [p for p in pool if p["cos"] >= floor]:
        for d, s, _ in c["secondaries"]:
            if d != c["domain"] and s not in targets: targets.append(s)
    for t in targets:
        got = pick(lambda c, t=t: c["subdomain"] == t and c["kf"] in S.RING3_KFS); rings[3] += got; placed += got
    return [dict(r, ring=n) for n in (1, 2, 3) for r in rings[n][:S.RING_CAPS[n]]][:S.TOTAL_CAP]

def show(cands, rows):
    return [{"ring": r.get("ring", 0), "book": cands[r["id"]]["book"][:70], "chapter": cands[r["id"]]["chapter"].strip()[:60], "cos": round(cands[r["id"]]["cos"], 3)} for r in rows if r["id"] in cands]

def stats(rows):
    books = [r["book"] for r in rows]
    return {"delivered": len(rows), "distinct_sources": len(set(books)), "repeats_of_a_source": len(books) - len(set(books))}

pools = sys.argv[1:] or ["A5", "B3", "A7", "A3"]
out = {}
for p in pools:
    try: cands, _ = S.load_pool(p)
    except Exception as e: print(p, "skip:", e); continue
    today = show(cands, S.respond(cands, mmr="score_proxy")["delivered"])
    a1 = show(cands, S.respond(cands, mmr="real_cosine")["delivered"])
    a2 = show(cands, respond_slots(cands))
    out[p] = {"today": today, "a1": a1, "a2": a2, "stats": {k: stats(v) for k, v in (("today", today), ("a1", a1), ("a2", a2))}}
    print(p, json.dumps(out[p]["stats"]))
(HERE / "a6_slots.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
