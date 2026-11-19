"""Q2/Q3 roll-up scenarios with the real atoms: members are unit profiles (full shares); each option aggregates them."""
import sys
from collections import Counter, defaultdict
sys.path.insert(0, "<HTC_REPO>")
sys.path.insert(0, "<SCRATCH>")
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from hypothetical import DOMAIN_OF, KF4, profile, top, tags, fill


def unit(name, lines, D, S, K, conf):
    return {"name": name, "lines": lines, "D": D, "S": fill(S, 8), "K": K, "conf": conf}


def mean(members, key, weight):
    w = [weight(m) for m in members]; tot = sum(w); out = defaultdict(float)
    for m, wi in zip(members, w):
        for k, v in m[key].items():
            out[k] += wi * v / tot
    return dict(out)


SEC_D = {"security-privacy": 0.74, "devops-cloud-platform-engineering": 0.12, "apis-integration-messaging": 0.08}
def sec_unit(i, lines=20):
    return unit(f"auth helper {i}", lines, SEC_D, {"identity-authentication": 0.55, "cryptography-applied": 0.15, "cloud-security": 0.05},
                KF4(0.08, 0.72, 0.16, 0.04), 0.74)


def run(title, members):
    print(f"\n### {title}\n")
    print("| Member | Lines | Primary domain / subdomain | Confidence |\n|---|---|---|---|")
    shown = Counter()
    for m in members:
        key = (m["lines"], max(m["S"], key=m["S"].get))
        shown[key] += 1
        if shown[key] <= 1:
            n = sum(1 for x in members if (x["lines"], max(x["S"], key=x["S"].get)) == key)
            print(f"| {m['name']}{' (×%d)' % n if n > 1 else ''} | {m['lines']} | {max(m['D'], key=m['D'].get)} / {max(m['S'], key=m['S'].get)} | {m['conf']:.2f} |")
    print("\n| Option | Primary (domain / subdomain / KF) | Domain shares | Secondaries |\n|---|---|---|---|")
    for name, wfn in (("R1 size-weighted", lambda m: m["lines"]), ("R1 confidence-weighted", lambda m: m["conf"]),
                      ("R1 equal", lambda m: 1.0)):
        D, S, K = mean(members, "D", wfn), mean(members, "S", wfn), mean(members, "K", wfn)
        r = profile(D, S, K)
        print(f"| {name} | {r[0]} / {r[1]} / {r[2]} | {top(D,2)} | {tags(r[4],3)} |")
    D, S, K = mean(members, "D", lambda m: m["lines"]), mean(members, "S", lambda m: m["lines"]), mean(members, "K", lambda m: m["lines"])
    r = profile(D, S, K, ratio=0.45)
    print(f"| R2 size-weighted, ratio 0.45 | {r[0]} / {r[1]} / {r[2]} | {top(D,2)} | {tags(r[4],3)} |")
    # R3: v0.17 vote — domain/subdomain by confidence-weighted plurality of member primaries; KF by member count
    dv, sv = defaultdict(float), defaultdict(float)
    for m in members:
        dv[max(m["D"], key=m["D"].get)] += m["conf"]; sv[max(m["S"], key=m["S"].get)] += m["conf"]
    kv = Counter(max(m["K"], key=m["K"].get) for m in members)
    pd, ps, pk = max(dv, key=dv.get), max(sv, key=sv.get), kv.most_common(1)[0][0]
    tot = sum(dv.values())
    r = profile(D, S, K, primary=(ps, pk))
    print(f"| R3 vote + secondaries from size-weighted means | {pd} / {ps} / {pk} | {', '.join(f'{k} {v/tot:.3f}' for k, v in sorted(dv.items(), key=lambda x: -x[1])[:2])} (vote) | {tags(r[4],3)} |")


print("## Q2 — module and component roll-ups\n")
metrics = unit("AuthMetrics.record_rejection", 120, {"devops-cloud-platform-engineering": 0.70, "security-privacy": 0.18, "apis-integration-messaging": 0.05},
               {"observability-logging": 0.58, "sre-reliability": 0.12, "identity-authentication": 0.08}, KF4(0.05, 0.75, 0.15, 0.05), 0.60)
run("M1 · authn.py — 15 small auth units + 1 large metrics unit", [sec_unit(i) for i in range(15)] + [metrics])

handler = unit("TokenEndpoint.post (REST handler)", 240, {"apis-integration-messaging": 0.72, "security-privacy": 0.16, "software-architecture": 0.05},
               {"rest": 0.52, "api-gateways": 0.10, "identity-authentication": 0.12}, KF4(0.04, 0.80, 0.12, 0.04), 0.72)
run("M2 · token.py — 3 tiny auth helpers (10 lines each) + 1 large REST handler", [sec_unit(i, 10) for i in range(3)] + [handler])

cloud = lambda i, n: unit(f"policy module {i}", n, {"security-privacy": 0.80, "devops-cloud-platform-engineering": 0.10, "apis-integration-messaging": 0.04},
                          {"cloud-security": 0.70, "identity-authentication": 0.18}, KF4(0.10, 0.70, 0.15, 0.05), 0.70)
iam = lambda i, n: unit(f"iam module {i}", n, {"security-privacy": 0.82, "devops-cloud-platform-engineering": 0.06, "apis-integration-messaging": 0.05},
                        {"identity-authentication": 0.62, "cloud-security": 0.20}, KF4(0.10, 0.70, 0.15, 0.05), 0.72)
run("M3 · policy_sentry component — 6 cloud-policy modules + 2 IAM modules (the SCE-11.03.04 shape)",
    [cloud(i, 300) for i in range(6)] + [iam(i, 250) for i in range(2)])
