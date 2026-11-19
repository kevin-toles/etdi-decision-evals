"""C1 (#40) demo, step 2 (HTC env, no model): file every candidate with the real HTC UnitScorer (nomic-v2 anchors,
today's T 0.03 / ratio 0.6), build Rings 0-3 by the unified-search-rs rules, then merge the cascade follow-ons under
today's code and under options (a)-(e), run today's MMR plus budget trim, and write the response each would deliver.

What is real: the question and chapter vectors (nomic-v2, COS ProfileEmbedder), each chapter's filing (HTC
UnitScorer), cosine similarity, and every rule below, ported from the Rust source (file:line in comments).
What is simplified: the candidate pool is the 164 chapters a keyword scan of 20,000 SE books found (search would look at
all 3.5M chapters); a chapter's search vector is HTC's token-weighted mean of its pieces (V005's vector is OQ#28);
Ring 1's code (CRE) and warning (VRE) results, Ring 2's SIMILAR_TO graph neighbours, Rings 4-5 and passage-tier widening
are absent (no code collection, graph or passages in the demo).
    cd htc-multidim-classification-service && python3 <this>"""
import asyncio, json, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
os.environ.update({"HTC_NOISE_FLOOR": "-1", "HTC_KF_FLOOR": "-1"})   # floors uncalibrated (OQ#24): none rejects a chapter, as in score_profile.py
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
T, RATIO = float(os.environ.get("DEMO_T", "0.03")), float(os.environ.get("DEMO_RATIO", "0.6"))
TAG = os.environ.get("DEMO_TAG", "")
E = HERE.parent.parent / "three_way_eval" / "nomic-v2"
RRF_K = 60.0                                                               # assembly.rs:52
RING1_KFS = ["role-definition", "implementation-ref-spec", "failure-mode-limitation", "supporting-papers"]  # kf_envelope.rs:19
RING1_TOP_K, RING2_TOP_K, RING3_TOP_K = 2, 2, 2                            # kf_envelope.rs:27, sibling_expander.rs:25, domain_bridge.rs:22
RING2_KFS = RING3_KFS = ["role-definition", "implementation-ref-spec"]     # sibling_expander.rs:22, domain_bridge.rs:19
CASCADE_KF_VARIANTS = RING1_KFS                                            # cascade.rs:70 (L1: top 1 per KF, cascade.rs:256)
POOL_SIZE, RGA_K = 50, float(os.environ.get("USS_RGA_THRESHOLD_K", "1.0"))                                                 # ring0.rs:139, assembly.rs:160
MMR_LAMBDA, MMR_TOP_K = 0.7, 43                                            # assembly.rs mmr_rerank
RING_CAPS = {1: 14, 2: 12, 3: 8, 4: 4, 5: 3}; TOTAL_CAP = 43              # budget.rs:3-13 (unlisted ring → 43)

M = TaxonomyManifest.from_dict(json.loads(Path("config/taxonomy_manifest.json").read_text()))
a = np.load(E / "anchors.npz")
subs = {s.slug: s.anchor_text for d in M.domains for s in d.subdomains}
by_text = {subs[str(s)]: v for s, v in zip(a["sub_slugs"], a["sub_vectors"])}
kft = {k.slug: k.anchor_text for k in M.kf_definitions}
by_text.update({kft[str(s)]: v for s, v in zip(a["kf_slugs"], a["kf_vectors"])})
for d in M.domains:
    by_text.setdefault(d.anchor_text, a["sub_vectors"].mean(axis=0))


class C:
    model_id = "nomic-v2"
    async def encode_batch(self, texts, task="search_document"):
        return [np.asarray(by_text[t], dtype=np.float64) for t in texts]


def unit(r):                       # one result as the response carries it
    return {k: r[k] for k in ("id", "score", "ring", "via") if k in r}


async def main():
    idx = TaxonomyAnchorIndex(); await idx.build(M, C())
    scorer = UnitScorer(C(), idx, ProfileAssembler(ScoreNormalizer(temperature=T), SecondaryTagResolver(ratio=RATIO),
                                                  SignalShareAdjuster()), PieceScorePooler())
    q = np.load(HERE / "query.npy").astype(np.float64); q /= np.linalg.norm(q)
    cands = {c["id"]: c for c in json.loads((HERE / "candidates.json").read_text())}
    for cid, c in list(cands.items()):
        p = HERE / "pieces" / f"{cid}.npz"
        if not p.exists():
            del cands[cid]; continue
        z = np.load(p)
        pieces = [EmbeddedPiece(v.astype(np.float64).tolist(), int(t), 0, 0) for v, t in zip(z["vectors"], z["tokens"])]
        su = scorer.score_pieces(pieces, "", cid)
        v = np.asarray(su.vector, dtype=np.float64); v /= np.linalg.norm(v)
        pr = su.profile
        c.update(vec=v, cos=float(v @ q), domain=pr.primary_domain, subdomain=pr.primary_subdomain, kf=pr.primary_kf,
                 secondaries=[(t.domain, t.subdomain, t.kf) for t in pr.secondary_tags])
    ranked = sorted(cands.values(), key=lambda c: -c["cos"])

    def search(pred, k):           # a filtered query-vector search at the chapter tier: top k by cosine
        return [dict(id=c["id"], score=c["cos"]) for c in ranked if pred(c)][:k]

    # Ring 0 — hit plus pool (ring0.rs), floor = top − k·std (uss-core scoring/threshold.rs:14)
    hit, pool = ranked[0], ranked[:POOL_SIZE]
    floor = float(np.clip(pool[0]["cos"] - RGA_K * np.std([c["cos"] for c in pool]), 0, 1))
    # Ring 1 — per KF, hit subdomain + that primary KF, top 2 (kf_envelope.rs)
    ring1 = [r for kf in RING1_KFS for r in search(lambda c, kf=kf: c["subdomain"] == hit["subdomain"] and c["kf"] == kf, RING1_TOP_K)]
    # Ring 2 — secondary tags include the hit subdomain, primary KF in RING2_KFS, top 2 (sibling_expander.rs:64)
    ring2 = search(lambda c: c["kf"] in RING2_KFS and any(s == hit["subdomain"] for _, s, _ in c["secondaries"]), RING2_TOP_K)
    # Ring 3 — targets: hit's cross-domain secondaries, then the pool's above the floor (domain_bridge.rs:69)
    targets = []
    for c in [hit] + [p for p in pool if p["cos"] >= floor]:
        for d, s, _ in c["secondaries"]:
            if d != c["domain"] and s not in targets:
                targets.append(s)
    ring3, seen = [], set()
    for t in targets:
        for r in search(lambda c, t=t: c["subdomain"] == t and c["kf"] in RING3_KFS, RING3_TOP_K):
            if r["id"] not in seen:
                seen.add(r["id"]); ring3.append(r)
    rings = {n: [dict(r, ring=n) for r in lst] for n, lst in ((1, ring1), (2, ring2), (3, ring3)) if lst}

    def rrf(lists):                # assembly.rs:529 — 1/(k + rank), rank from 0, summed per id, sorted, deduped
        acc, first = {}, {}
        for lst in lists:
            for rank, r in enumerate(lst):
                acc[r["id"]] = acc.get(r["id"], 0.0) + 1.0 / (RRF_K + rank)
                first.setdefault(r["id"], r)
        return [dict(first[i], score=s) for i, s in sorted(acc.items(), key=lambda kv: -kv[1])]

    fused = rrf(list(rings.values()))
    bridges = [r for r in fused if r.get("ring") == 3]          # DOMAIN_BRIDGE results trigger the cascade (enrich.rs:116)

    def follow_ons(bridge):        # cascade.rs:247 — per CASCADE_KF top 1 in the bridge's subdomain, score = cosine
        sd = cands[bridge["id"]]["subdomain"]
        return [dict(r, via=bridge["id"]) for kf in CASCADE_KF_VARIANTS
                for r in search(lambda c, kf=kf: c["subdomain"] == sd and c["kf"] == kf, 1)]

    casc = {b["id"]: follow_ons(b) for b in bridges}

    def dedup(lst):
        out, s = [], set()
        for r in lst:
            if r["id"] not in s:
                s.add(r["id"]); out.append(r)
        return out

    def mmr(lst):                  # assembly.rs mmr_rerank, ScoreProxy (the default): sim = 1 − |Δscore|
        sel, rem = [], list(lst)
        for _ in range(min(MMR_TOP_K, len(rem))):
            best = max(range(len(rem)), key=lambda i: MMR_LAMBDA * rem[i]["score"] - (1 - MMR_LAMBDA) * max(
                [max(0.0, 1 - abs(rem[i]["score"] - s["score"])) for s in sel] or [0.0]))
            sel.append(rem.pop(best))
        return sel

    def trim(lst):                 # budget.rs RingBudget::trim — group by ring (no ring → 0), cap, ring order, 43
        groups = {}
        for r in dedup(lst):
            groups.setdefault(r.get("ring", 0), []).append(r)
        out = [r for g in sorted(groups) for r in groups[g][:RING_CAPS.get(g, TOTAL_CAP)]]
        return out[:TOTAL_CAP]

    options = {}
    # Today — enrich.rs:103: fused + follow-ons (no ring tag, enrich via tiered_search::result) sorted by score, deduped
    today = dedup(sorted(fused + [dict(r) for b in bridges for r in casc[b["id"]]], key=lambda r: -r["score"]))
    options["today"] = today
    # (a) follow-ons directly after their bridge, tagged Ring 3 with the bridge as provenance
    out = []
    for r in fused:
        out.append(r)
        for i, f in enumerate(casc.get(r["id"], [])):
            out.append(dict(f, ring=3, score=r["score"] - 1e-6 * (i + 1)))
    options["a"] = dedup(out)
    # (b) follow-ons get the RRF score of the ranks just after their bridge
    out = list(fused)
    for pos, r in enumerate(fused):
        for i, f in enumerate(casc.get(r["id"], [])):
            out.append(dict(f, ring=3, score=1.0 / (RRF_K + pos + 1 + i)))
    options["b"] = dedup(sorted(out, key=lambda r: -r["score"]))
    # (c) the design's (c): follow-ons merged into Ring 3's list by query similarity before fusion
    r3 = sorted(rings.get(3, []) + [dict(f, ring=3) for b in bridges for f in casc[b["id"]]], key=lambda r: -cands[r["id"]]["cos"])
    options["c"] = rrf([lst for n, lst in rings.items() if n != 3] + [dedup(r3)])
    # (d) reviewers' unified ranking: after the cascade, everything re-ranked by similarity to the question
    pool_d = dedup(fused + [dict(f, ring=3) for b in bridges for f in casc[b["id"]]])
    options["d"] = sorted([dict(r, score=cands[r["id"]]["cos"]) for r in pool_d], key=lambda r: -r["score"])
    # (e) re-fuse: follow-ons at or above the pool floor become one more ranked list in RRF
    cl = dedup(sorted([dict(f, ring=3) for b in bridges for f in casc[b["id"]] if cands[f["id"]]["cos"] >= floor],
                      key=lambda r: -cands[r["id"]]["cos"]))
    options["e"] = rrf(list(rings.values()) + ([cl] if cl else []))

    delivered = {k: trim(mmr(v)) for k, v in options.items()}
    meta = {cid: {k: c[k] for k in ("book", "chapter", "pages", "chars", "cos", "domain", "subdomain", "kf", "secondaries")}
            for cid, c in cands.items()}
    report = {"question": "How should I rotate database credentials?", "candidates": len(cands), "floor": floor,
              "hit": hit["id"], "hit_filing": [hit["domain"], hit["subdomain"], hit["kf"]], "ring3_targets": targets,
              "rings": {n: [unit(r) for r in lst] for n, lst in rings.items()},
              "bridges": [b["id"] for b in bridges], "follow_ons": {b: [f["id"] for f in fs] for b, fs in casc.items()},
              "ranked": {k: [unit(r) for r in v] for k, v in options.items()},
              "delivered": {k: [unit(r) for r in v] for k, v in delivered.items()}, "meta": meta}
    (HERE / f"demo_result{TAG}.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("candidates", "floor", "hit", "hit_filing", "ring3_targets", "bridges", "follow_ons")}, indent=1))
    print({n: len(v) for n, v in rings.items()})

asyncio.run(main())
