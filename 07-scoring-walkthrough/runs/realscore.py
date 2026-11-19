"""Score realrun.json with the real HTC atoms: per-piece normalization → token-weighted pooling → assembly, options A/B/C."""
import json, sys
sys.path.insert(0, "<HTC_REPO>")
from src.features.ClassifyCorpus.assembly.score_normalizer import ScoreNormalizer
from src.features.ClassifyCorpus.assembly.secondary_tag_resolver import SecondaryTagResolver
from src.features.ClassifyCorpus.assembly.profile_assembler import ProfileAssembler
from src.features.ClassifyCorpus.assembly.piece_score_pooler import PieceScorePooler
from src.shared.embedded_piece import EmbeddedPiece
M = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
DOMAIN_OF = {s["slug"]: d["slug"] for d in M["domains"] for s in d["subdomains"]}
top = lambda d, n=3: ", ".join(f"{k} {v:.3f}" for k, v in sorted(d.items(), key=lambda x: -x[1])[:n])
def spread(d): v = sorted(d.values(), reverse=True); return f"{v[0]:.3f} … {v[-1]:.3f} (1st–5th gap {v[0]-v[4]:.3f})"
recs = json.load(open(sys.argv[1]))
for r in recs:
    pieces = [EmbeddedPiece([0.0], t, 0, 0) for t in r["pieces"]]
    print(f"\n### {r['label']} — {r['title']!r}\n\n`{r['file'][:90]}` · {r['chars']:,} chars · pieces {r['pieces']} · code-line ratio {r['code_ratio']}\n")
    p0 = r["raw"][0]
    print(f"- Raw cosine, piece 1 — domains {spread(p0['D'])}; top: {top(p0['D'])}")
    print(f"- Raw cosine, piece 1 — subdomains top: {top(p0['S'],4)}; KFs: {top(p0['K'],4)}")
    if len(r["raw"]) > 1:
        print("- Each piece's best subdomain: " + "; ".join(f"#{i+1} {max(x['S'], key=x['S'].get)}" for i, x in enumerate(r["raw"])))
    print("\n| T | Option | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |\n|---|---|---|---|---|---|")
    for T in (0.01, 0.02, 0.05):
        n = ScoreNormalizer(T); a = ProfileAssembler(n, SecondaryTagResolver(ratio=0.6)); pool = PieceScorePooler()
        Ds = [n.normalize(x["D"]) for x in r["raw"]]
        SK = [a.piece_shares(x["S"], x["K"]) for x in r["raw"]]
        D = pool.pool_scores(pieces, Ds); S = pool.pool_scores(pieces, [s for s, _ in SK]); K = pool.pool_scores(pieces, [k for _, k in SK])
        rows = []
        pa = a.assemble(D, S, K, DOMAIN_OF, "1.2", "x")
        rows.append(("A pure", pa.primary_domain, pa.primary_subdomain, pa.primary_kf, S[pa.primary_subdomain] * K[pa.primary_kf], pa.secondary_tags))
        pv = r["pooled_vector_raw"]                                   # B: old components on the pooled (mean) vector
        dB = max(pv["D"], key=pv["D"].get)
        kB = "unassigned" if max(pv["K"].values()) < 0.2 else ("implementation-ref-spec" if r["code_ratio"] > 0.5 else max(pv["K"], key=pv["K"].get))
        sB = max((s for s in pv["S"] if DOMAIN_OF[s] == dB), key=pv["S"].get)
        secB = [] if kB == "unassigned" else SecondaryTagResolver(ratio=0.6).resolve(S, K, DOMAIN_OF, (sB, kB))
        rows.append(("B old components", dB, sB, kB, None if kB == "unassigned" else S[sB] * K[kB], secB))
        Kc = dict(K)                                                   # C: fold code-dense into KF shares; raw floor
        if r["code_ratio"] > 0.5:
            Kc["implementation-ref-spec"] += 0.25; tot = sum(Kc.values()); Kc = {k: v / tot for k, v in Kc.items()}
        pc = a.assemble(D, S, Kc, DOMAIN_OF, "1.2", "x")
        floor = max(max(x["K"].values()) for x in r["raw"]) < 0.2
        rows.append(("C fold", pc.primary_domain, pc.primary_subdomain, "unassigned" if floor else pc.primary_kf,
                     None if floor else S[pc.primary_subdomain] * Kc[pc.primary_kf], [] if floor else pc.secondary_tags))
        for name, d, s, k, sc, sec in rows:
            ts = "; ".join(f"{t.subdomain}/{t.kf} {t.score:.3f}" + (" ⚑" if sc is not None and t.score > sc else "") for t in sec[:3]) or "—"
            print(f"| {T} | {name} | {d} / {s} / {k} | {'—' if sc is None else f'{sc:.3f}'} | {len(sec)} | {ts} |")
        if T == 0.02:
            print(f"| | *pooled shares at T=0.02* | D: {top(D,2)} | S: {top(S,2)} | K: {top(K,2)} | |")
