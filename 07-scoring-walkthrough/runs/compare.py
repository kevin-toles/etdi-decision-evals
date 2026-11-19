import json, sys
from collections import Counter
sys.path.insert(0, "<HTC_REPO>")
from src.features.ClassifyCorpus.assembly.score_normalizer import ScoreNormalizer
from src.features.ClassifyCorpus.assembly.secondary_tag_resolver import SecondaryTagResolver
from src.features.ClassifyCorpus.assembly.profile_assembler import ProfileAssembler
from src.features.ClassifyCorpus.assembly.piece_score_pooler import PieceScorePooler
from src.shared.embedded_piece import EmbeddedPiece
M = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
DOMAIN_OF = {s["slug"]: d["slug"] for d in M["domains"] for s in d["subdomains"]}
short = lambda s: s.replace("-systems-programming-operating-systems", "-sys").replace("engineering-management-organizational-design", "eng-management").replace("artificial-intelligence-machine-learning", "ai-ml")
runs = {"jina-v3": json.load(open("realrun.json")), "nomic-v2": json.load(open("realrun_nomic.json")), "nomic-v1.5": json.load(open("realrun_nomic15_full.json"))}
T = 0.02
print("| Chapter | Model | Section closeness: 1st, 2nd (gap) | Top 3 shelves (their section) | Sections of top 5 shelves | Current rule: primary · # extra copies | Shelf-first: primary · # extra copies | Best KF closeness |")
print("|---|---|---|---|---|---|---|---|")
for i in range(len(runs["jina-v3"])):
    for model, recs in runs.items():
        r = recs[i]; pieces = [EmbeddedPiece([0.0], t, 0, 0) for t in r["pieces"]]
        # closeness averaged over pieces (token-weighted), for the "how clear is it" view
        w = r["pieces"]; tot = sum(w)
        avg = lambda key: {k: sum(p[key][k] * wi for p, wi in zip(r["raw"], w)) / tot for k in r["raw"][0][key]}
        D_raw, S_raw, K_raw = avg("D"), avg("S"), avg("K")
        d = sorted(D_raw.items(), key=lambda x: -x[1]); s = sorted(S_raw.items(), key=lambda x: -x[1])
        n = ScoreNormalizer(T); a = ProfileAssembler(n, SecondaryTagResolver(ratio=0.6)); pool = PieceScorePooler()
        D = pool.pool_scores(pieces, [n.normalize(x["D"]) for x in r["raw"]])
        SK = [a.piece_shares(x["S"], x["K"]) for x in r["raw"]]
        S = pool.pool_scores(pieces, [x for x, _ in SK]); K = pool.pool_scores(pieces, [k for _, k in SK])
        p = a.assemble(D, S, K, DOMAIN_OF, "1.2", "x")
        kf = max(K, key=K.get); best = max(S, key=S.get)
        sec2 = SecondaryTagResolver(ratio=0.6).resolve(S, K, DOMAIN_OF, (best, kf))
        secs5 = Counter(DOMAIN_OF[x] for x, _ in s[:5])
        print(f"| {r['label']} | {model} | {short(d[0][0])} {d[0][1]:.3f}, {short(d[1][0])} {d[1][1]:.3f} ({d[0][1]-d[1][1]:.3f}) | "
              + ", ".join(f"{x} {v:.3f} ({short(DOMAIN_OF[x])})" for x, v in s[:3])
              + f" | {len(secs5)} section(s) | {short(p.primary_domain)}/{p.primary_subdomain} · {len(p.secondary_tags)} | {short(DOMAIN_OF[best])}/{best} · {len(sec2)} | {max(K_raw.values()):.3f} |")
