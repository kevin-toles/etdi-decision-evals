"""Alternative primary rules on the same real pooled shares: does the secondary explosion go away?"""
import json, sys
from collections import defaultdict
sys.path.insert(0, "<HTC_REPO>")
from src.features.ClassifyCorpus.assembly.score_normalizer import ScoreNormalizer
from src.features.ClassifyCorpus.assembly.secondary_tag_resolver import SecondaryTagResolver
from src.features.ClassifyCorpus.assembly.profile_assembler import ProfileAssembler
from src.features.ClassifyCorpus.assembly.piece_score_pooler import PieceScorePooler
from src.shared.embedded_piece import EmbeddedPiece
M = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
DOMAIN_OF = {s["slug"]: d["slug"] for d in M["domains"] for s in d["subdomains"]}
recs = json.load(open(sys.argv[1]))
print("| Chapter | T | Rule | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |\n|---|---|---|---|---|---|---|")
for r in recs:
    pieces = [EmbeddedPiece([0.0], t, 0, 0) for t in r["pieces"]]
    for T in (0.02, 0.05):
        n = ScoreNormalizer(T); a = ProfileAssembler(n, SecondaryTagResolver(ratio=0.6)); pool = PieceScorePooler()
        D = pool.pool_scores(pieces, [n.normalize(x["D"]) for x in r["raw"]])
        SK = [a.piece_shares(x["S"], x["K"]) for x in r["raw"]]
        S = pool.pool_scores(pieces, [s for s, _ in SK]); K = pool.pool_scores(pieces, [k for _, k in SK])
        kf = max(K, key=K.get); res = SecondaryTagResolver(ratio=0.6)
        rules = {}
        d0 = max(D, key=D.get); s0 = max((s for s in S if DOMAIN_OF[s] == d0), key=S.get)          # current (domain-led)
        rules["current: domain-led"] = (d0, s0)
        s1 = max(S, key=S.get); rules["H1: subdomain-led"] = (DOMAIN_OF[s1], s1)                   # best subdomain anywhere
        agg = defaultdict(float)
        for s, v in S.items(): agg[DOMAIN_OF[s]] += v
        joint = {d: D[d] * agg[d] for d in D}; d2 = max(joint, key=joint.get)                        # domain anchors × summed subdomains
        rules["H2: joint domain"] = (d2, max((s for s in S if DOMAIN_OF[s] == d2), key=S.get))
        for name, (d, s) in rules.items():
            sec = res.resolve(S, K, DOMAIN_OF, (s, kf)); ps = S[s] * K[kf]
            ts = "; ".join(f"{t.subdomain}/{t.kf} {t.score:.3f}" + (" ⚑" if t.score > ps else "") for t in sec[:3]) or "—"
            print(f"| {r['label']} | {T} | {name} | {d} / {s} / {kf} | {ps:.3f} | {len(sec)} | {ts} |")
