"""B1 (#26) like-for-like: every profile scored on the same chapters jina-v5-small embedded before it was paused
(2026-11-10), through the real UnitScorer + AnchorRoutingEvaluator, at two settings. Numpy only.
    cd htc-multidim-classification-service && python3 <this> > subset144.txt"""
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
from src.features.ClassifyCorpus.taxonomy.anchor_routing_evaluator import AnchorRoutingEvaluator
from src.features.ClassifyCorpus.taxonomy.taxonomy_anchor_index import TaxonomyAnchorIndex
from src.shared.embedded_piece import EmbeddedPiece
from src.shared.taxonomy_manifest import TaxonomyManifest

E = Path("<EVIDENCE>/three_way_eval")
M = TaxonomyManifest.from_dict(json.loads(Path("config/taxonomy_manifest.json").read_text()))
held_all = json.loads((E / "heldout.json").read_text())
text_of = {ref: t for slug in held_all for ref, t in held_all[slug]}
ref_cases = json.loads((E / "jina-v5-small" / "cases.json").read_text())
keep = [i for i in range(len(ref_cases)) if (E / "jina-v5-small" / "pieces" / f"{i}.npz").exists()]
for p in ["nomic-v2", "jina-v3", "nomic-v1.5", "multilingual-e5-large", "bge-m3", "jina-v5-small"]:
    assert json.loads((E / p / "cases.json").read_text()) == ref_cases, p      # same chapter order in every profile


async def run(p):
    a = np.load(E / p / "anchors.npz")
    subs = {s.slug: s.anchor_text for d in M.domains for s in d.subdomains}
    by_text = {subs[str(s)]: v for s, v in zip(a["sub_slugs"], a["sub_vectors"])}
    kft = {k.slug: k.anchor_text for k in M.kf_definitions}
    by_text.update({kft[str(s)]: v for s, v in zip(a["kf_slugs"], a["kf_vectors"])})
    for d in M.domains:
        by_text.setdefault(d.anchor_text, a["sub_vectors"].mean(axis=0))
    pieces, held = {}, {}
    for i in keep:
        slug, ref = ref_cases[i]
        z = np.load(E / p / "pieces" / f"{i}.npz")
        pieces[text_of[ref]] = [EmbeddedPiece(v.astype(np.float64).tolist(), int(t), 0, 0) for v, t in zip(z["vectors"], z["tokens"])]
        held.setdefault(slug, []).append((ref, text_of[ref]))

    class C:
        model_id = p
        async def encode_batch(self, texts, task="search_document"):
            return [np.asarray(by_text[t], dtype=np.float64) for t in texts]
        async def encode_pieces(self, text, task="search_document"):
            return pieces[text]
    idx = TaxonomyAnchorIndex(); await idx.build(M, C())
    for t, r in [(0.03, 0.6), (0.05, 0.5)]:
        s = UnitScorer(C(), idx, ProfileAssembler(ScoreNormalizer(temperature=t), SecondaryTagResolver(ratio=r), SignalShareAdjuster()), PieceScorePooler())
        sc = await AnchorRoutingEvaluator(C()).evaluate_whole_taxonomy(held, s)
        print(f"{p:22s} T={t} ratio={r} chapters={len(keep)} domain {sc.domain_accuracy:.1%} subdomain {sc.primary_top1:.1%} "
              f"primary-or-secondary {sc.primary_or_secondary:.1%}", flush=True)


async def main():
    for p in ["jina-v5-small", "nomic-v1.5", "jina-v3", "bge-m3", "nomic-v2", "multilingual-e5-large"]:
        await run(p)
asyncio.run(main())
