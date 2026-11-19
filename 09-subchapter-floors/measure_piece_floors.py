"""E5 (user 2026-11-18): what the chapter filing floors would hold back below chapter level — measured on recorded data only.

Recorded data: three_way_eval/nomic-v2 (ETDI-1.0.742 run): anchors.npz (461 subdomain + 4 KF query vectors from the real
COS ProfileEmbedder) plus pieces/<i>.npz (each held-out chapter read whole in 480-token document pieces, batch 1);
heldout.json (1,049 held-out SE chapters keyed by their verified subdomain slug). No model is loaded; raw similarity is
the dot product of the recorded unit-norm vectors (the cosine TaxonomyAnchorIndex computes).

Unit measured: the recorded 480-token PIECE — the only sub-chapter unit recorded. Spans (passages) and paragraph groups
were never embedded in this run, so their own similarities do not exist; pieces are the proxy (labelled as such).
Floors: HTC_NOISE_FLOOR / HTC_KF_FLOOR have no value yet (OQ#24; the run used -1). Candidates are the chapter-level peak
percentiles the floors are calibrated from (score_nomic-v2.json peak_subdomain / peak_kf p1, p5, p10): a chapter floor
at p_k quarantines k% of chapters; the same floor is applied to each piece. A unit is below when its best subdomain
similarity < NOISE or its best KF similarity < KF (BEH-11.01 step 5). Scoring settings that do not touch floors
(T 0.03, ratio 0.6) are irrelevant to raw-similarity floors.
Kinds: a heuristic text tag (see kind()), not a judgement.
Example text: pieces carry no character offsets, so each example's text is the chapter text at the token-proportional
position of the piece (approximate boundaries, verbatim characters).
    python3 measure_piece_floors.py <three_way_eval dir> <out dir>
"""
import json, random, statistics, sys
from pathlib import Path
import numpy as np

EVAL, OUT = Path(sys.argv[1]), Path(sys.argv[2])
PDIR = EVAL / "nomic-v2"
scores = json.loads((EVAL / "scored_2026-11-10" / "score_nomic-v2.json").read_text())
FLOORS = {k: (scores["peak_subdomain"][k], scores["peak_kf"][k]) for k in ("p1", "p5", "p10")}
a = np.load(PDIR / "anchors.npz")
S, K = a["sub_vectors"].astype(np.float32), a["kf_vectors"].astype(np.float32)
sub_slugs, kf_slugs = [str(s) for s in a["sub_slugs"]], [str(s) for s in a["kf_slugs"]]
held = json.loads((EVAL / "heldout.json").read_text())
text_of = {ref: text for slug in held for ref, text in held[slug]}
cases = json.loads((PDIR / "cases.json").read_text())

import re
CODE = re.compile(r"[{};=<>()\[\]]|\b(def|class|return|import|public|void|int|func|var|const|let|printf|#include)\b")
SUMMARY = re.compile(r"\b(in this chapter|summary|we will (see|learn|discuss)|chapter \d+ (covers|introduces)|"
                     r"learning objectives|key takeaways|review questions|exercises)\b", re.I)
ABOUT = re.compile(r"\b(about the author|acknowledg|copyright|all rights reserved|isbn|foreword|preface|dedicat|"
                   r"table of contents|printed in)\b", re.I)


def kind(text: str, j: int, n: int) -> str:
    """Heuristic kind tag (labelled heuristic, first match wins): front/back matter phrases; summary/intro phrasing;
    index or reference list (digit plus comma density); OCR noise (share of non-alphanumeric, non-space characters);
    code (code-token density per 100 characters); otherwise prose."""
    t = " ".join(text.split())
    if not t:
        return "empty"
    if ABOUT.search(t):
        return "front/back matter"
    if SUMMARY.search(t):
        return "summary/intro phrasing"
    digits, commas = sum(c.isdigit() for c in t) / len(t), t.count(",") / len(t)
    if digits > 0.12 and commas > 0.03:
        return "index/reference list"
    odd = sum(not (c.isalnum() or c.isspace() or c in ".,;:'\"-()") for c in t) / len(t)
    if odd > 0.12:
        return "ocr noise/symbols"
    if len(CODE.findall(t)) / max(1, len(t)) * 100 > 2.0:
        return "code"
    return "prose"


units = []   # one row per piece
for i, (slug, ref) in enumerate(cases):
    z = np.load(PDIR / "pieces" / f"{i}.npz")
    V, tokens = z["vectors"].astype(np.float32), z["tokens"].astype(int)
    sub_sim, kf_sim = V @ S.T, V @ K.T
    text, total = text_of[ref], int(tokens.sum())
    start = 0
    for j in range(len(V)):
        lo, hi = int(len(text) * start / total), int(len(text) * (start + tokens[j]) / total)
        start += int(tokens[j])
        top = int(sub_sim[j].argmax())
        units.append({"chapter": i, "slug": slug, "ref": ref, "piece": j, "pieces": len(V), "tokens": int(tokens[j]),
                      "best_sub": float(sub_sim[j, top]), "top_sub": sub_slugs[top],
                      "best_kf": float(kf_sim[j].max()), "top_kf": kf_slugs[int(kf_sim[j].argmax())],
                      "rank_of_verified": int((sub_sim[j] > sub_sim[j, sub_slugs.index(slug)]).sum()) + 1,
                      "chars": [lo, hi], "text": text[lo:hi], "kind": kind(text[lo:hi], j, len(V))})

chapters = len(cases)
report = {"recorded_run": str(PDIR), "unit": "480-token piece (proxy: spans/paragraph groups were not recorded)",
          "chapters": chapters, "pieces": len(units), "floors": {}}
random.seed(20261118)
for name, (noise, kf) in FLOORS.items():
    for u in units:
        u["below_noise"], u["below_kf"] = u["best_sub"] < noise, u["best_kf"] < kf
        u["below"] = u["below_noise"] or u["below_kf"]
    below = [u for u in units if u["below"]]
    per_ch = [sum(u["below"] for u in units if u["chapter"] == c) for c in range(chapters)]
    share_ch = [sum(u["below"] for u in units if u["chapter"] == c) / max(1, sum(1 for u in units if u["chapter"] == c))
                for c in range(chapters)]
    wrong = lambda us: sum(u["top_sub"] != u["slug"] for u in us) / max(1, len(us))
    above = [u for u in units if not u["below"]]
    # contiguous runs of kept pieces (the passage sequence a chapter keeps)
    gaps_split = sum(1 for c in range(chapters)
                     if any(u["below"] for u in units if u["chapter"] == c and 0 < u["piece"] < u["pieces"] - 1)
                     and not all(u["below"] for u in units if u["chapter"] == c))
    position = {"first": sum(u["below"] for u in units if u["piece"] == 0),
                "last": sum(u["below"] for u in units if u["piece"] == u["pieces"] - 1 and u["pieces"] > 1),
                "middle": sum(u["below"] for u in units if 0 < u["piece"] < u["pieces"] - 1)}
    def examples(pool, n=10):
        pick = random.sample(pool, min(n, len(pool)))
        return [{k: u[k] for k in ("ref", "slug", "piece", "pieces", "best_sub", "top_sub", "best_kf", "top_kf",
                                   "rank_of_verified", "chars", "kind")} | {"text": u["text"][:600]} for u in pick]
    kinds = sorted({u["kind"] for u in units})
    report["floors"][name] = {
        "HTC_NOISE_FLOOR": noise, "HTC_KF_FLOOR": kf,
        "pieces_below": len(below), "share_below": len(below) / len(units),
        "below_noise_only": sum(u["below_noise"] and not u["below_kf"] for u in units),
        "below_kf_only": sum(u["below_kf"] and not u["below_noise"] for u in units),
        "below_both": sum(u["below_noise"] and u["below_kf"] for u in units),
        "per_chapter_count": {"median": statistics.median(per_ch), "p90": float(np.percentile(per_ch, 90))},
        "per_chapter_share": {"median": statistics.median(share_ch), "p90": float(np.percentile(share_ch, 90))},
        "chapters_with_any_below": sum(1 for x in per_ch if x),
        "chapters_losing_more_than_half": sum(1 for x in share_ch if x > 0.5),
        "chapters_losing_all": sum(1 for x in share_ch if x == 1.0),
        "chapters_with_an_interior_gap": gaps_split,
        "position_of_below_pieces": position,
        "wrong_subject_rate_below": wrong(below), "wrong_subject_rate_above": wrong(above),
        "verified_in_top5_below": sum(u["rank_of_verified"] <= 5 for u in below) / max(1, len(below)),
        "verified_in_top5_above": sum(u["rank_of_verified"] <= 5 for u in above) / max(1, len(above)),
        "by_kind": {k: {"below": sum(u["kind"] == k for u in below), "above": sum(u["kind"] == k for u in above),
                        "share_below": sum(u["kind"] == k for u in below) / max(1, sum(u["kind"] == k for u in units)),
                        "wrong_subject_below": wrong([u for u in below if u["kind"] == k]),
                        "wrong_subject_above": wrong([u for u in above if u["kind"] == k])} for k in kinds},
        "examples_below": examples(below), "examples_above": examples(above),
        "examples_below_by_kind": {k: examples([u for u in below if u["kind"] == k]) for k in kinds},
    }
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "e5_piece_floors.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
for name, f in report["floors"].items():
    print(name, {k: v for k, v in f.items() if not k.startswith("examples") and k != "by_kind"})
    for k, v in f["by_kind"].items():
        print("   ", k, {x: (round(y, 3) if isinstance(y, float) else y) for x, y in v.items()})
