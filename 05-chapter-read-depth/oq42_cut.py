"""OQ#42: whole chapter vs the 8,000-character cut, on recorded nomic-v2 pieces (no model)."""
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
PDIR, CUT = E / "nomic-v2", 8000
MANIFEST = TaxonomyManifest.from_dict(json.loads(Path("config/taxonomy_manifest.json").read_text()))
anchors = np.load(PDIR / "anchors.npz")
subs = {s.slug: s.anchor_text for d in MANIFEST.domains for s in d.subdomains}
by_text = {subs[str(s)]: v for s, v in zip(anchors["sub_slugs"], anchors["sub_vectors"])}
kft = {k.slug: k.anchor_text for k in MANIFEST.kf_definitions}
by_text.update({kft[str(s)]: v for s, v in zip(anchors["kf_slugs"], anchors["kf_vectors"])})
for d in MANIFEST.domains:
    by_text.setdefault(d.anchor_text, anchors["sub_vectors"].mean(axis=0))
domain_of = {s.slug: d.slug for d in MANIFEST.domains for s in d.subdomains}
held = json.loads((E / "heldout.json").read_text())
text_of = {ref: t for slug in held for ref, t in held[slug]}
cases = json.loads((PDIR / "cases.json").read_text())

class COS:
    async def encode_batch(self, texts, task="search_document"):
        return [np.asarray(by_text[t], dtype=np.float64) for t in texts]

def prefix(vecs, toks, chars):
    cpt = chars / max(1, int(toks.sum()))          # this chapter's characters per token
    budget, out = CUT / cpt, []
    for v, t in zip(vecs, toks):
        if budget <= 0: break
        out.append((v, int(min(t, budget)))); budget -= t
    return out

async def main():
    index = TaxonomyAnchorIndex(); await index.build(MANIFEST, COS())
    T = float(sys.argv[1]) if len(sys.argv) > 1 else 0.03
    scorer = UnitScorer(COS(), index, ProfileAssembler(ScoreNormalizer(temperature=T), SecondaryTagResolver(ratio=0.6), SignalShareAdjuster()), PieceScorePooler())
    rows = []
    for i, (slug, ref) in enumerate(cases):
        z = np.load(PDIR / "pieces" / f"{i}.npz"); V, K = z["vectors"].astype(np.float64), z["tokens"]
        r = {"slug": slug, "ref": ref, "chars": len(text_of[ref]), "pieces": len(K)}
        for mode, ps in (("whole", list(zip(V, K))), ("cut", prefix(V, K, len(text_of[ref])))):
            p = scorer.score_pieces([EmbeddedPiece(v.tolist(), int(t), 0, 0) for v, t in ps], "", ref).profile
            r[mode] = {"sub": p.primary_subdomain, "dom": p.primary_domain, "sec": [t.subdomain for t in p.secondary_tags], "n": len(ps)}
        rows.append(r)
    out = Path(sys.argv[2]); out.write_text(json.dumps(rows))
    for mode in ("whole", "cut"):
        n = len(rows)
        top1 = sum(r[mode]["sub"] == r["slug"] for r in rows) / n
        dom = sum(r[mode]["dom"] == domain_of[r["slug"]] for r in rows) / n
        either = sum(r[mode]["sub"] == r["slug"] or r["slug"] in r[mode]["sec"] for r in rows) / n
        print(f"T={T} {mode}: domain {dom:.1%}  subdomain top-1 {top1:.1%}  primary-or-secondary {either:.1%}  pieces/chapter {np.mean([r[mode]['n'] for r in rows]):.1f}")
    long = [r for r in rows if r["chars"] > CUT]
    a = sum(r["whole"]["sub"] == r["slug"] and r["cut"]["sub"] != r["slug"] for r in long)
    b = sum(r["cut"]["sub"] == r["slug"] and r["whole"]["sub"] != r["slug"] for r in long)
    print(f"chapters >8k: {len(long)}; whole right / cut wrong {a}; cut right / whole wrong {b}; primaries differ {sum(r['whole']['sub'] != r['cut']['sub'] for r in long)}")
asyncio.run(main())
