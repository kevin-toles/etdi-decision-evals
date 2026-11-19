"""B1 (#26) worked example: where each candidate embedding model files the same real test chapters. The 144 test chapters
jina-v5-small finished, each model's recorded pieces + anchors, the real HTC UnitScorer at today's T 0.03 / ratio 0.6
(floors off, as score_profile.py). Numpy only, no model loaded.
    cd htc-multidim-classification-service && python3 <this> > b1_filing.json"""
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
MODELS = ["jina-v5-small", "nomic-v2", "jina-v3", "bge-m3", "multilingual-e5-large", "nomic-v1.5"]
M = TaxonomyManifest.from_dict(json.loads(Path("config/taxonomy_manifest.json").read_text()))
dom_of = {s.slug: d.slug for d in M.domains for s in d.subdomains}
subset = [ref for slug, ref in json.loads((E / "jina-v5-small" / "cases.json").read_text())[:144]]


async def run(model):
    P = E / model; a = np.load(P / "anchors.npz")
    subs = {s.slug: s.anchor_text for d in M.domains for s in d.subdomains}
    by_text = {subs[str(s)]: v for s, v in zip(a["sub_slugs"], a["sub_vectors"])}
    kft = {k.slug: k.anchor_text for k in M.kf_definitions}
    by_text.update({kft[str(s)]: v for s, v in zip(a["kf_slugs"], a["kf_vectors"])})
    for d in M.domains:
        by_text.setdefault(d.anchor_text, a["sub_vectors"].mean(axis=0))

    class C:
        model_id = model
        async def encode_batch(self, texts, task="search_document"):
            return [np.asarray(by_text[t], dtype=np.float64) for t in texts]

    idx = TaxonomyAnchorIndex(); await idx.build(M, C())
    s = UnitScorer(C(), idx, ProfileAssembler(ScoreNormalizer(temperature=0.03), SecondaryTagResolver(ratio=0.6),
                                              SignalShareAdjuster()), PieceScorePooler())
    out = {}
    for i, (slug, ref) in enumerate(json.loads((P / "cases.json").read_text())):
        if ref not in subset or ref in out:
            continue
        f = P / "pieces" / f"{i}.npz"
        if not f.exists():
            continue
        z = np.load(f)
        p = s.score_pieces([EmbeddedPiece(v.astype(np.float64).tolist(), int(t), 0, 0) for v, t in zip(z["vectors"], z["tokens"])], "", ref).profile
        out[ref] = {"truth": slug, "domain": p.primary_domain, "sub": p.primary_subdomain,
                    "sec": sorted({t.subdomain for t in p.secondary_tags} - {p.primary_subdomain})}
    return out


async def main():
    res = {m: await run(m) for m in MODELS}
    print(json.dumps({"dom_of": dom_of, "results": res}, indent=0))

asyncio.run(main())
