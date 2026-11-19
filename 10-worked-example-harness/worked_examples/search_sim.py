"""Worked examples, step 3 (HTC env, no model): the ported search pipeline from c1_demo/run_options.py, made reusable.
file(): every pool chapter through the real HTC UnitScorer (nomic-v2 anchors; T / ratio as given).
respond(): Ring 0 hit + pool, Ring 1 (hit subject x Ring-1 facets, top 2 each), Ring 2 (secondaries include the hit
subject), Ring 3 (cross-area secondaries of the hit and pool above the floor), RRF, today's cascade merge, MMR
(ScoreProxy by default, or real cosine, or same-chapter penalty) and the budget trim — rules ported from
unified-search-rs (file:line in c1_demo/run_options.py). Hooks: exclude ids (A5 partial load), mmr mode (A6), extra
Ring-1 items (A7 warnings), drop a ring (B4).
Simplified as in the C1 demo: the pool is what a keyword scan of 20,000 SE books found; a chapter's vector is HTC's
token-weighted mean of its pieces; no code (CRE), graph, passages or Rings 4-5."""
import asyncio, json, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
os.environ.update({"HTC_NOISE_FLOOR": "-1", "HTC_KF_FLOOR": "-1"})
import numpy as np
from src.features.ClassifyCorpus.assembly.piece_score_pooler import PieceScorePooler
from src.features.ClassifyCorpus.assembly.profile_assembler import ProfileAssembler
from src.features.ClassifyCorpus.assembly.score_normalizer import ScoreNormalizer
from src.features.ClassifyCorpus.assembly.secondary_tag_resolver import SecondaryTagResolver
from src.features.ClassifyCorpus.assembly.signal_share_adjuster import SignalShareAdjuster
from src.features.ClassifyCorpus.assembly.unit_scorer import UnitScorer
from src.features.ClassifyCorpus.taxonomy.taxonomy_anchor_index import TaxonomyAnchorIndex
from src.shared.embedded_piece import EmbeddedPiece
from src.shared.taxonomy_manifest import TaxonomyManifest

HERE = Path(__file__).parent
E = HERE.parent.parent / "three_way_eval" / "nomic-v2"
RRF_K = 60.0
RING1_KFS = ["role-definition", "implementation-ref-spec", "failure-mode-limitation", "supporting-papers"]
RING2_KFS = RING3_KFS = ["role-definition", "implementation-ref-spec"]
POOL_SIZE = 50
MMR_LAMBDA, MMR_TOP_K = 0.7, 43
RING_CAPS = {1: 14, 2: 12, 3: 8, 4: 4, 5: 3}; TOTAL_CAP = 43
M = TaxonomyManifest.from_dict(json.loads(Path("config/taxonomy_manifest.json").read_text()))
_a = np.load(E / "anchors.npz")
_subs = {s.slug: s.anchor_text for d in M.domains for s in d.subdomains}
BY_TEXT = {_subs[str(s)]: v for s, v in zip(_a["sub_slugs"], _a["sub_vectors"])}
_kft = {k.slug: k.anchor_text for k in M.kf_definitions}
BY_TEXT.update({_kft[str(s)]: v for s, v in zip(_a["kf_slugs"], _a["kf_vectors"])})
for _d in M.domains:
    BY_TEXT.setdefault(_d.anchor_text, _a["sub_vectors"].mean(axis=0))


class _C:
    model_id = "nomic-v2"
    async def encode_batch(self, texts, task="search_document"):
        return [np.asarray(BY_TEXT[t], dtype=np.float64) for t in texts]


def load_pool(q, T=0.03, ratio=0.6, drop=None):
    """drop: a subdomain slug removed from the anchor index (A1 failure-1 simulation)."""
    meta = json.loads((HERE / "candidates.json").read_text())
    cands = {k: dict(meta["candidates"][k]) for k in meta["pools"][q]}
    qv = np.load(HERE / "queries" / f"{q}.npy").astype(np.float64); qv /= np.linalg.norm(qv)

    async def go():
        man = M
        if drop:
            md = json.loads(Path("config/taxonomy_manifest.json").read_text())
            for d in md["domains"]:
                d["subdomains"] = [x for x in d["subdomains"] if x["slug"] != drop]
            man = TaxonomyManifest.from_dict(md)
        idx = TaxonomyAnchorIndex(); await idx.build(man, _C())
        sc = UnitScorer(_C(), idx, ProfileAssembler(ScoreNormalizer(temperature=T), SecondaryTagResolver(ratio=ratio),
                                                    SignalShareAdjuster()), PieceScorePooler())
        for k, c in list(cands.items()):
            p = HERE / "pieces" / f"{k}.npz"
            if not p.exists():
                del cands[k]; continue
            z = np.load(p)
            su = sc.score_pieces([EmbeddedPiece(v.astype(np.float64).tolist(), int(t), 0, 0) for v, t in zip(z["vectors"], z["tokens"])], "", k)
            v = np.asarray(su.vector, dtype=np.float64); v /= np.linalg.norm(v); pr = su.profile
            c.update(vec=v, cos=float(v @ qv), domain=pr.primary_domain, subdomain=pr.primary_subdomain, kf=pr.primary_kf,
                     secondaries=[(t.domain, t.subdomain, t.kf) for t in pr.secondary_tags], pieces=z["vectors"].astype(np.float64))
    asyncio.run(go())
    return cands, qv


def respond(cands, exclude=(), mmr="score_proxy", ring1_extra=(), drop_ring=None, rga_k=1.0):
    live = {k: c for k, c in cands.items() if k not in set(exclude)}
    ranked = sorted(live.values(), key=lambda c: -c["cos"])
    if not ranked:
        return {"hit": None, "rings": {}, "delivered": []}

    def search(pred, k):
        return [dict(id=c["id"], score=c["cos"]) for c in ranked if pred(c)][:k]
    hit, pool = ranked[0], ranked[:POOL_SIZE]
    floor = float(np.clip(pool[0]["cos"] - rga_k * np.std([c["cos"] for c in pool]), 0, 1))
    ring1 = [r for kf in RING1_KFS for r in search(lambda c, kf=kf: c["subdomain"] == hit["subdomain"] and c["kf"] == kf, 2)]
    ring1 += [dict(x) for x in ring1_extra]
    ring2 = search(lambda c: c["kf"] in RING2_KFS and any(s == hit["subdomain"] for _, s, _ in c["secondaries"]), 2)
    targets = []
    for c in [hit] + [p for p in pool if p["cos"] >= floor]:
        for d, s, _ in c["secondaries"]:
            if d != c["domain"] and s not in targets:
                targets.append(s)
    ring3, seen = [], set()
    for t in targets:
        for r in search(lambda c, t=t: c["subdomain"] == t and c["kf"] in RING3_KFS, 2):
            if r["id"] not in seen:
                seen.add(r["id"]); ring3.append(r)
    rings = {n: [dict(r, ring=n) for r in lst] for n, lst in ((1, ring1), (2, ring2), (3, ring3)) if lst and n != drop_ring}

    def rrf(lists):
        acc, first = {}, {}
        for lst in lists:
            for rank, r in enumerate(lst):
                acc[r["id"]] = acc.get(r["id"], 0.0) + 1.0 / (RRF_K + rank)
                first.setdefault(r["id"], r)
        return [dict(first[i], score=s) for i, s in sorted(acc.items(), key=lambda kv: -kv[1])]
    fused = rrf(list(rings.values()))

    def vec(r):
        return live[r["id"]]["vec"] if r["id"] in live else None

    def sim(a, b):
        if mmr == "real_cosine":
            va, vb = vec(a), vec(b)
            return float(va @ vb) if va is not None and vb is not None else 0.0
        if mmr == "same_chapter":
            ca, cb = live.get(a["id"]), live.get(b["id"])
            return 1.0 if ca and cb and ca["book"] == cb["book"] else 0.0
        return max(0.0, 1 - abs(a["score"] - b["score"]))       # ScoreProxy (today)

    sel, rem = [], list(fused)
    for _ in range(min(MMR_TOP_K, len(rem))):
        best = max(range(len(rem)), key=lambda i: MMR_LAMBDA * rem[i]["score"] - (1 - MMR_LAMBDA) * max([sim(rem[i], s) for s in sel] or [0.0]))
        sel.append(rem.pop(best))
    groups, out, s = {}, [], set()
    for r in sel:
        if r["id"] in s: continue
        s.add(r["id"]); groups.setdefault(r.get("ring", 0), []).append(r)
    out = [r for g in sorted(groups) for r in groups[g][:RING_CAPS.get(g, TOTAL_CAP)]][:TOTAL_CAP]
    return {"hit": hit["id"], "floor": floor, "rings": {n: [r["id"] for r in l] for n, l in rings.items()}, "fused": fused, "delivered": out}


def label(c):
    b = c["book"].replace("_", ": ", 1) if c["book"].count("_") else c["book"]
    return f"{b[:80]} — {c['chapter'].strip()[:50]} (pp. {c['pages']})"
