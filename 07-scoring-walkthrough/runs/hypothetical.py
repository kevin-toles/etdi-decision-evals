"""Hypothetical CAP-11 scenarios scored with the real HTC atoms. Each option's rule is applied exactly as written in
the write-up; T is illustrative (0.02) until OQ#24 calibrates it. Raw similarities are derived from the intended
shares so the reader sees both (real cosines bunch: a few thousandths apart)."""
import json, math, sys
sys.path.insert(0, "<HTC_REPO>")
from src.features.ClassifyCorpus.assembly.score_normalizer import ScoreNormalizer
from src.features.ClassifyCorpus.assembly.secondary_tag_resolver import SecondaryTagResolver
from src.features.ClassifyCorpus.assembly.profile_assembler import ProfileAssembler
from src.features.ClassifyCorpus.assembly.piece_score_pooler import PieceScorePooler
from src.shared.embedded_piece import EmbeddedPiece

T = 0.02
M = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
DOMAIN_OF = {s["slug"]: d["slug"] for d in M["domains"] for s in d["subdomains"]}
KFS = ["role-definition", "implementation-ref-spec", "failure-mode-limitation", "supporting-papers"]
KF_W, SUB_W, KF_FLOOR = 0.25, 0.15, 0.2
norm, pool = ScoreNormalizer(T), PieceScorePooler()


def raw_from(shares, top_raw):
    top = max(shares.values())
    return {k: round(top_raw + T * math.log(v / top), 4) for k, v in shares.items()}


def fill(shares, n_other=12, start=0):
    others = [s for s in DOMAIN_OF if s not in shares][start:start + n_other]
    left = 1 - sum(shares.values())
    return {**shares, **{s: left / len(others) for s in others}}


def adjust(shares, boosts):
    out = dict(shares)
    for k, w in boosts.items():
        out[k] = out.get(k, 0.0) + w
    tot = sum(out.values())
    return {k: v / tot for k, v in out.items()}


def top(d, n=4):
    return ", ".join(f"{k} {v:.3f}" for k, v in sorted(d.items(), key=lambda x: -x[1])[:n])


def tags(ts, n=6):
    return "; ".join(f"({t.domain} / {t.subdomain} / {t.kf}) {t.score:.3f}" for t in ts[:n]) + (f"; … +{len(ts)-n} more" if len(ts) > n else "") if ts else "none"


def profile(D, S, K, ratio=0.6, primary=None):
    """assemble on the given shares; `primary` forces (sub, kf) the way Option B's old components would."""
    a = ProfileAssembler(norm, SecondaryTagResolver(ratio=ratio))
    p = a.assemble(D, S, K, DOMAIN_OF, "1.2", "x")
    if primary is None:
        return p.primary_domain, p.primary_subdomain, p.primary_kf, S[p.primary_subdomain] * K[p.primary_kf], p.secondary_tags
    sub, kf = primary
    sec = SecondaryTagResolver(ratio=ratio).resolve(S, K, DOMAIN_OF, (sub, kf))
    return max(D, key=D.get), sub, kf, S[sub] * K[kf], sec


def show(title, D, S, K, rawK, rawS=None, kf_signals=(), sub_signals=(), code_ratio=0.0, ratio=0.6):
    print(f"\n### {title}\n")
    print(f"- Domain shares: {top(D,3)}")
    print(f"- Subdomain shares (whole taxonomy): {top(S,5)}")
    print(f"- KF raw similarity: {top(rawK)} → shares at T={T}: {top(K)}")
    if kf_signals or sub_signals or code_ratio:
        print(f"- Signals: KF {list(kf_signals) or '—'}, subdomain {list(sub_signals) or '—'}, code ratio {code_ratio:.2f}")
    # A — pure argmax of pooled shares
    a = profile(D, S, K, ratio)
    # B — old components choose: KF = top raw (unassigned below floor; code>0.5 → impl); subdomain = top raw in domain + raw weights
    pd = max(D, key=D.get)
    kfB = "unassigned" if max(rawK.values()) < KF_FLOOR else ("implementation-ref-spec" if code_ratio > 0.5 else max(rawK, key=rawK.get))
    rs = {s: v for s, v in (rawS or {}).items() if DOMAIN_OF[s] == pd}
    for sig in sub_signals:
        rs[sig] = rs.get(sig, 0.0) + SUB_W               # SubdomainResolver adds even a foreign slug to its map
    subB = max(rs, key=rs.get) if rs else a[1]
    if kfB == "unassigned":
        b = (pd, subB, kfB, None, [])
    else:
        b = profile(D, S, K, ratio, primary=(subB if DOMAIN_OF.get(subB) else a[1], kfB))
    # C — fold: KF signals + code-dense as +0.25, subdomain signals +0.15, renormalize; unassigned on raw floor
    kb = {}
    for s in kf_signals:
        kb[s] = kb.get(s, 0) + KF_W
    if code_ratio > 0.5:
        kb["implementation-ref-spec"] = kb.get("implementation-ref-spec", 0) + KF_W
    Kc, Sc = adjust(K, kb), adjust(S, {s: SUB_W * list(sub_signals).count(s) for s in set(sub_signals)})
    if max(rawK.values()) < KF_FLOOR:
        c = (pd, profile(D, Sc, Kc, ratio)[1], "unassigned", None, [])
    else:
        c = profile(D, Sc, Kc, ratio)
    print("\n| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |\n|---|---|---|---|")
    for name, r in (("A pure", a), ("B old components", b), ("C fold", c)):
        sc = "—" if r[3] is None else f"{r[3]:.3f}"
        print(f"| {name} | {r[0]} / {r[1]} / {r[2]} | {sc} | {tags(r[4])} |")
    if code_ratio > 0.5 or kf_signals:
        print(f"\nC's adjusted KF shares: {top(Kc)}")
    if sub_signals:
        print(f"\nC's adjusted subdomain shares: {top(Sc,5)}")


KF4 = lambda r, i, f, p: {"role-definition": r, "implementation-ref-spec": i, "failure-mode-limitation": f, "supporting-papers": p}
DSE = "distributed-systems-engineering"

print("## Q1 — primary KF/subdomain rule\n")
S = fill({"consensus-algorithms": 0.62, "leader-election": 0.08, "replication": 0.06})
K = KF4(0.05, 0.86, 0.06, 0.03)
show("H1 · Single-topic chapter (Raft explained)", {DSE: 0.81, "storage-systems": 0.07, "software-architecture": 0.04},
     S, K, raw_from(K, 0.47), raw_from(S, 0.58))

S = fill({"consensus-algorithms": 0.40, "leader-election": 0.30, "replication": 0.10})
K = KF4(0.03, 0.55, 0.40, 0.02)
show("H2 · Same-domain secondaries (consensus with a failure-handling section)", {DSE: 0.70, "storage-systems": 0.15, "software-architecture": 0.08},
     S, K, raw_from(K, 0.46), raw_from(S, 0.56))

S = fill({"consensus-algorithms": 0.40, "replication": 0.12, "leader-election": 0.08})
K = KF4(0.41, 0.38, 0.15, 0.06)
show("H3 · Code-heavy chapter (70% listings; anchors lean role-definition)", {DSE: 0.66, "software-architecture": 0.18, "storage-systems": 0.08},
     S, K, raw_from(K, 0.48), raw_from(S, 0.55), code_ratio=0.70)

S = fill({"consensus-algorithms": 0.30, "replication": 0.20, "leader-election": 0.15})
K = KF4(0.30, 0.28, 0.24, 0.18)
show("H4 · Table-of-contents fragment (nothing matches well: best KF cosine 0.15)", {DSE: 0.40, "software-architecture": 0.30, "storage-systems": 0.20},
     S, K, raw_from(K, 0.15), raw_from(S, 0.18))

S = fill({"rest": 0.34, "grpc": 0.14, "api-gateways": 0.10, "sre-reliability": 0.08})
K = KF4(0.06, 0.70, 0.20, 0.04)
show("H5 · CRE unit: HTTP client with retry_loop + timeout_guard (signal subdomain in ANOTHER domain)",
     {"apis-integration-messaging": 0.64, "devops-cloud-platform-engineering": 0.20, "software-engineering-design": 0.08},
     S, K, raw_from(K, 0.50), raw_from(S, 0.52), sub_signals=("sre-reliability", "sre-reliability"))

sed_subs = [s for s in DOMAIN_OF if DOMAIN_OF[s] == "software-engineering-design"][:3]
S = fill({sed_subs[0]: 0.40, "software-quality": 0.22, sed_subs[1]: 0.10})
K = KF4(0.10, 0.60, 0.25, 0.05)
show(f"H6 · CRE unit: validator with two validation_guard signals (signal subdomain INSIDE the primary domain; anchor top {sed_subs[0]})",
     {"software-engineering-design": 0.58, "testing-quality-assurance": 0.22, "security-privacy": 0.10},
     S, K, raw_from(K, 0.50), raw_from(S, 0.53), sub_signals=("software-quality", "software-quality"))

S = fill({"consensus-algorithms": 0.40, "leader-election": 0.30})
K = KF4(0.05, 0.50, 0.42, 0.03)
show("H7 · Exception-heavy CRE unit (exception_handler + raise_site → failure-mode-limitation)",
     {DSE: 0.70, "storage-systems": 0.15, "software-architecture": 0.08},
     S, K, raw_from(K, 0.47), raw_from(S, 0.55), kf_signals=("failure-mode-limitation", "failure-mode-limitation"))

print("\n## Pooling — a long two-topic chapter (two pieces)\n")
p1 = EmbeddedPiece([1.0, 0.0], 8160, 0, 30000); p2 = EmbeddedPiece([0.0, 1.0], 3900, 30000, 45000)
S1 = fill({"consensus-algorithms": 0.60, "storage-engines": 0.05}); S2 = fill({"storage-engines": 0.65, "consensus-algorithms": 0.04})
pooled = pool.pool_scores([p1, p2], [S1, S2])
print(f"- Piece 1 (8,160 tokens): {top(S1,2)}\n- Piece 2 (3,900 tokens): {top(S2,2)}\n- Pooled (token-weighted): {top(pooled,3)}")
K = KF4(0.05, 0.80, 0.12, 0.03)
D = {DSE: 0.55, "storage-systems": 0.35, "software-architecture": 0.05}
for ratio in (0.6, 0.45):
    r = profile(D, pooled, K, ratio)
    print(f"- ratio {ratio}: primary {r[1]} ({r[3]:.3f}); secondaries {tags(r[4])}")
