"""ETDI-1.0.742 phase C (HTC env, no model): the recorded COS outputs of one profile through the real TaxonomyAnchorIndex,
UnitScorer and AnchorRoutingEvaluator.evaluate_whole_taxonomy (§5.1.9.90 v0.19), over a temperature × secondary-ratio
grid (OQ#24), plus the per-chapter peak raw similarities the floors are calibrated from. Floors are not under test
(set to -1). --partial scores only the chapters already embedded.
Crash-safe (2026-11-12, after the 2026-11-10 crash lost an in-memory grid): each grid cell is appended to <out>.cells.jsonl as it finishes and skipped on restart; each chapter is scored once per cell (the secondaries come from the same scored profiles the evaluator used); a memory guard waits below MIN_FREE_GB and exits 3 if it does not recover.
    cd htc-multidim-classification-service && python3 <this> <profile_dir> <heldout.json> <out.json> [--partial]"""
import asyncio, json, os, subprocess, sys, time
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

PDIR, HELD, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PARTIAL = "--partial" in sys.argv
MANIFEST = TaxonomyManifest.from_dict(json.loads(Path("config/taxonomy_manifest.json").read_text()))
TEMPERATURES, RATIOS = (0.01, 0.02, 0.03, 0.05, 0.08), (0.5, 0.6, 0.7)

anchors = np.load(PDIR / "anchors.npz")
by_text = {}
subs = {s.slug: s.anchor_text for d in MANIFEST.domains for s in d.subdomains}
for slug, v in zip(anchors["sub_slugs"], anchors["sub_vectors"]):
    by_text[subs[str(slug)]] = v
kf_text = {k.slug: k.anchor_text for k in MANIFEST.kf_definitions}
for slug, v in zip(anchors["kf_slugs"], anchors["kf_vectors"]):
    by_text[kf_text[str(slug)]] = v
mean = anchors["sub_vectors"].mean(axis=0)
for d in MANIFEST.domains:            # domain anchors are not used by v0.19 scoring; the index still stores one
    by_text.setdefault(d.anchor_text, mean)

held_all = json.loads(HELD.read_text())
cases = json.loads((PDIR / "cases.json").read_text())
text_of = {ref: text for slug in held_all for ref, text in held_all[slug]}
pieces_of, held = {}, {}
for i, (slug, ref) in enumerate(cases):
    path = PDIR / "pieces" / f"{i}.npz"
    if not path.exists():
        if PARTIAL:
            continue
        raise SystemExit(f"missing {path} (not DONE; use --partial)")
    z = np.load(path)
    pieces_of[text_of[ref]] = [EmbeddedPiece(v.astype(np.float64).tolist(), int(t), 0, 0) for v, t in zip(z["vectors"], z["tokens"])]
    held.setdefault(slug, []).append((ref, text_of[ref]))


class _RecordedCOS:
    model_id = PDIR.name          # UnitScorer stamps ScoredUnit.embedding_model from the client (2026-11-10)
    async def encode_batch(self, texts, task="search_document"):
        return [np.asarray(by_text[t], dtype=np.float64) for t in texts]

    async def encode_pieces(self, text, task="search_document"):
        return pieces_of[text]


MIN_FREE_GB = 1.2


def free_gb() -> float:
    pages = {l.split(":")[0]: int(l.split(":")[1].strip().rstrip(".")) for l in subprocess.run(
        ["vm_stat"], capture_output=True, text=True).stdout.splitlines()[1:] if ":" in l}
    return sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative")) * 16384 / 1e9


def guard() -> None:
    for _ in range(30):
        if free_gb() >= MIN_FREE_GB:
            return
        print(f"memory guard: {free_gb():.2f} GB free < {MIN_FREE_GB}, waiting", flush=True)
        time.sleep(60)
    print("memory guard: no recovery in 30 min — exiting for a later resume", flush=True)
    sys.exit(3)


class _OncePerCell:
    """Wraps the real UnitScorer for one grid cell: the evaluator's score_text results are kept by ref, so the
    secondaries are read from the very profiles the evaluator scored instead of scoring every chapter a second time."""
    def __init__(self, scorer):
        self._scorer, self.units = scorer, {}

    def domain_of(self):
        return self._scorer.domain_of()

    async def score_text(self, text, taxonomy_version, text_id, **options):
        unit = await self._scorer.score_text(text, taxonomy_version, text_id, **options)
        self.units[(text_id, text)] = unit        # refs repeat in the held-out set (1,049 chapters, 1,041 refs)
        return unit


async def main():
    cos = _RecordedCOS()
    index = TaxonomyAnchorIndex()
    await index.build(MANIFEST, cos)
    cells_path = OUT.with_suffix(".cells.jsonl")
    grid = [json.loads(l) for l in cells_path.read_text().splitlines()] if cells_path.exists() else []
    done = {(c["temperature"], c["ratio"]) for c in grid}
    for t in TEMPERATURES:
        for r in RATIOS:
            if (t, r) in done:
                continue
            guard()
            assembler = ProfileAssembler(ScoreNormalizer(temperature=t), SecondaryTagResolver(ratio=r), SignalShareAdjuster())
            scorer = _OncePerCell(UnitScorer(cos, index, assembler, PieceScorePooler()))
            score = await AnchorRoutingEvaluator(cos).evaluate_whole_taxonomy(held, scorer)
            secondaries = [len(scorer.units[(ref, text)].profile.secondary_tags) for chapters in held.values() for ref, text in chapters]
            grid.append({"temperature": t, "ratio": r, "domain_accuracy": score.domain_accuracy,
                         "primary_top1": score.primary_top1, "primary_or_secondary": score.primary_or_secondary,
                         "secondaries_median": float(np.median(secondaries)), "secondaries_p90": float(np.percentile(secondaries, 90)),
                         "secondaries_zero_share": float(np.mean([n == 0 for n in secondaries]))})
            print(json.dumps(grid[-1]), flush=True)
            with cells_path.open("a") as f:
                f.write(json.dumps(grid[-1]) + "\n")
    peaks = []
    for chapters in held.values():
        for ref, text in chapters:
            ps = pieces_of[text]
            sub = max(s.score for p in ps for s in index.query_subdomains(p.vector))
            kf = max(k.confidence for p in ps for k in index.query_kfs(p.vector))
            peaks.append({"ref": ref, "pieces": len(ps), "tokens": sum(p.token_count for p in ps),
                          "peak_subdomain": round(sub, 4), "peak_kf": round(kf, 4)})
    q = lambda key: {f"p{p}": round(float(np.percentile([x[key] for x in peaks], p)), 4) for p in (1, 5, 10, 50)}
    OUT.write_text(json.dumps({"profile": PDIR.name, "chapters": len(peaks), "partial": PARTIAL, "grid": grid,
                               "peak_subdomain": q("peak_subdomain"), "peak_kf": q("peak_kf"),
                               "pieces_median": float(np.median([x["pieces"] for x in peaks])), "per_chapter": peaks}, indent=1))

asyncio.run(main())
