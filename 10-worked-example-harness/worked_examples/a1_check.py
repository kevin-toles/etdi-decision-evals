"""A1 (#51) worked example: what each filing check reports for real filing runs of the 1,049 test chapters (recorded
nomic-v2 pieces, real HTC UnitScorer, T 0.03 / ratio 0.6, floors off):
  baseline   — today's anchors;
  failure 1  — simulated taxonomy edit: the quantum-algorithms subject's anchor removed from the index;
  failure 2  — real model mismatch: shelf descriptions (anchors) embedded with nomic-v1.5, chapters with nomic-v2
               (both 768 numbers, so the run does not crash).
Per run: per-chapter filing, accuracy, macro-F1 (sklearn, the ClassificationQualityHarness metric), primary-or-secondary.
Numpy + sklearn only.   cd htc-multidim-classification-service && python3 <this> <out.json>"""
import asyncio, json, os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
os.environ.update({"HTC_NOISE_FLOOR": "-1", "HTC_KF_FLOOR": "-1"})
import numpy as np
from sklearn.metrics import f1_score
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
MD = json.loads(Path("config/taxonomy_manifest.json").read_text())
cases = json.loads((E / "nomic-v2" / "cases.json").read_text())
PIECES = []
for i, (slug, ref) in enumerate(cases):
    z = np.load(E / "nomic-v2" / "pieces" / f"{i}.npz")
    PIECES.append([EmbeddedPiece(v.astype(np.float64).tolist(), int(t), 0, 0) for v, t in zip(z["vectors"], z["tokens"])])


async def run(anchor_model, drop=None):
    md = json.loads(json.dumps(MD))
    if drop:
        for d in md["domains"]:
            d["subdomains"] = [s for s in d["subdomains"] if s["slug"] != drop]
    M = TaxonomyManifest.from_dict(md)
    a = np.load(E / anchor_model / "anchors.npz")
    subs = {s.slug: s.anchor_text for d in M.domains for s in d.subdomains}
    by_text = {subs[str(s)]: v for s, v in zip(a["sub_slugs"], a["sub_vectors"]) if str(s) in subs}
    kft = {k.slug: k.anchor_text for k in M.kf_definitions}
    by_text.update({kft[str(s)]: v for s, v in zip(a["kf_slugs"], a["kf_vectors"])})
    for d in M.domains:
        by_text.setdefault(d.anchor_text, a["sub_vectors"].mean(axis=0))

    class C:
        model_id = "nomic-v2"
        async def encode_batch(self, texts, task="search_document"):
            return [np.asarray(by_text[t], dtype=np.float64) for t in texts]

    idx = TaxonomyAnchorIndex(); await idx.build(M, C())
    s = UnitScorer(C(), idx, ProfileAssembler(ScoreNormalizer(temperature=0.03), SecondaryTagResolver(ratio=0.6),
                                              SignalShareAdjuster()), PieceScorePooler())
    dom = {sd["slug"]: d["slug"] for d in MD["domains"] for sd in d["subdomains"]}
    rows = []
    for (slug, ref), ps in zip(cases, PIECES):
        p = s.score_pieces(ps, "", ref).profile
        rows.append({"ref": ref, "truth": slug, "truth_domain": dom[slug], "sub": p.primary_subdomain, "domain": p.primary_domain,
                     "sec": sorted({t.subdomain for t in p.secondary_tags})})
    yt, yp = [r["truth"] for r in rows], [r["sub"] for r in rows]
    dt, dp = [r["truth_domain"] for r in rows], [r["domain"] for r in rows]
    labs = sorted(set(yt)); dlabs = sorted(set(dt))
    return {"rows": rows,
            "subject_accuracy": float(np.mean([a == b for a, b in zip(yt, yp)])),
            "domain_accuracy": float(np.mean([a == b for a, b in zip(dt, dp)])),
            "subject_macro_f1": float(f1_score(yt, yp, labels=labs, average="macro", zero_division=0)),
            "domain_macro_f1": float(f1_score(dt, dp, labels=dlabs, average="macro", zero_division=0)),
            "primary_or_secondary": float(np.mean([r["truth"] == r["sub"] or r["truth"] in r["sec"] for r in rows]))}


async def main():
    out = {"baseline": await run("nomic-v2"), "failure1_quantum_algorithms_dropped": await run("nomic-v2", "quantum-algorithms"),
           "failure2_v15_anchors": await run("nomic-v1.5")}
    json.dump(out, open(sys.argv[1], "w"), indent=0)
    for k, v in out.items():
        print(k, {m: round(x, 4) for m, x in v.items() if m != "rows"})

asyncio.run(main())
