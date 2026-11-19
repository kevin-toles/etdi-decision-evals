"""A2 / A3 worked examples, step 3 (HTC env, no model): file the extra theory/SE chapters with the real HTC UnitScorer
(nomic-v2 anchors, T 0.03 / ratio 0.6) and report each chapter's primary + secondary subjects and its cosine to the
named subjects' anchors (information theory; gossip protocols, network-theory foundations).
    cd htc-multidim-classification-service && python3 <this>"""
import asyncio, json, os, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, os.getcwd())
import numpy as np
import search_sim as S
from src.features.ClassifyCorpus.assembly.piece_score_pooler import PieceScorePooler
from src.features.ClassifyCorpus.assembly.profile_assembler import ProfileAssembler
from src.features.ClassifyCorpus.assembly.score_normalizer import ScoreNormalizer
from src.features.ClassifyCorpus.assembly.secondary_tag_resolver import SecondaryTagResolver
from src.features.ClassifyCorpus.assembly.signal_share_adjuster import SignalShareAdjuster
from src.features.ClassifyCorpus.assembly.unit_scorer import UnitScorer
from src.features.ClassifyCorpus.taxonomy.taxonomy_anchor_index import TaxonomyAnchorIndex
from src.shared.embedded_piece import EmbeddedPiece
meta = json.loads((HERE / "candidates_extra.json").read_text())
a = np.load(S.E / "anchors.npz"); av = {str(s): v / np.linalg.norm(v) for s, v in zip(a["sub_slugs"], a["sub_vectors"])}
names = [s for s in ("information-theory", "gossip-protocols", "network-theory-foundations", "network-science", "complex-networks") if s in av]
print("anchors present:", names)
async def go():
    idx = TaxonomyAnchorIndex(); await idx.build(S.M, S._C())
    sc = UnitScorer(S._C(), idx, ProfileAssembler(ScoreNormalizer(temperature=0.03), SecondaryTagResolver(ratio=0.6), SignalShareAdjuster()), PieceScorePooler())
    out = []
    for k, m in meta.items():
        z = np.load(HERE / "pieces" / f"{k}.npz")
        su = sc.score_pieces([EmbeddedPiece(v.astype(np.float64).tolist(), int(t), 0, 0) for v, t in zip(z["vectors"], z["tokens"])], "", k)
        v = np.asarray(su.vector, dtype=np.float64); v /= np.linalg.norm(v); p = su.profile
        out.append(dict(m, id=k, filed=f"{p.primary_domain}/{p.primary_subdomain}", sec=sorted({t.subdomain for t in p.secondary_tags}),
                        anchor_cos={n: round(float(v @ av[n]), 3) for n in names}))
    (HERE / "extra_filed.json").write_text(json.dumps(out, indent=1))
    for o in out: print(o["q"], o["book"][:55], "|", o["chapter"][:25], o["pages"], "|", o["filed"], o["sec"][:4], o["anchor_cos"])
asyncio.run(go())
