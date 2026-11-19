"""B2 (#24) stakeholder examples: primary + secondary tags for a few real held-out chapters under the recorded nomic-v2
pieces, through the real HTC UnitScorer, at several temperature/ratio settings. Numpy only; loads only these chapters.
    cd htc-multidim-classification-service && python3 <this> > b2_examples.txt"""
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

E = Path("<EVIDENCE>/three_way_eval")
P = E / "nomic-v2"
WANT = ["Kafka The Definitive Guide 2nd Edition#114", "The Site Reliability Workbook#46", "Site Reliability Engineering#78",
        "Text Classification in the LLM Era - Where do we stand#1", "Towards Richer Challenge Problems for Scientific Computing Correctness#1",
        "Calvin - Fast Distributed Transactions for Partitioned Database Systems#2"]
SETTINGS = [(0.03, 0.6), (0.05, 0.5), (0.08, 0.5), (0.08, 0.7)]
M = TaxonomyManifest.from_dict(json.loads(Path("config/taxonomy_manifest.json").read_text()))
a = np.load(P / "anchors.npz")
subs = {s.slug: s.anchor_text for d in M.domains for s in d.subdomains}
by_text = {subs[str(s)]: v for s, v in zip(a["sub_slugs"], a["sub_vectors"])}
kft = {k.slug: k.anchor_text for k in M.kf_definitions}
by_text.update({kft[str(s)]: v for s, v in zip(a["kf_slugs"], a["kf_vectors"])})
for d in M.domains:
    by_text.setdefault(d.anchor_text, a["sub_vectors"].mean(axis=0))
held = json.loads((E / "heldout.json").read_text())
truth = {ref: slug for slug in held for ref, _ in held[slug]}
cases = json.loads((P / "cases.json").read_text())
pieces = {}
for i, (slug, ref) in enumerate(cases):
    if ref in WANT and ref not in pieces:
        z = np.load(P / "pieces" / f"{i}.npz")
        pieces[ref] = [EmbeddedPiece(v.astype(np.float64).tolist(), int(t), 0, 0) for v, t in zip(z["vectors"], z["tokens"])]


class C:
    model_id = "nomic-v2"
    async def encode_batch(self, texts, task="search_document"):
        return [np.asarray(by_text[t], dtype=np.float64) for t in texts]


async def main():
    idx = TaxonomyAnchorIndex(); await idx.build(M, C())
    for ref in WANT:
        print(f"\n## {ref}  (verified: {truth[ref]}; {len(pieces[ref])} pieces)")
        for t, r in SETTINGS:
            s = UnitScorer(C(), idx, ProfileAssembler(ScoreNormalizer(temperature=t), SecondaryTagResolver(ratio=r), SignalShareAdjuster()), PieceScorePooler())
            p = s.score_pieces(pieces[ref], "", ref).profile
            sec = ", ".join(f"{x.subdomain}" for x in p.secondary_tags) or "(none)"
            print(f"T={t} ratio={r}: primary {p.primary_domain}/{p.primary_subdomain}; secondaries: {sec}")

asyncio.run(main())
