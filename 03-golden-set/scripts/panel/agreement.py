"""Golden-set panel agreement (pilot, 2026-11-13). Loads every verdict file, maps opaque item ids back to record ids,
validates each verdict, and reports pairwise agreement per field.

PRE-REGISTERED GATE (written before any verdict was read): a local model earns a panel seat only if, against EACH Claude
panelist (Sonnet 5.5 and Opus 4.8), its quadratic-weighted kappa on grade is >= 0.8 x the Sonnet-Opus kappa AND its
primary-subdomain agreement is >= 0.8 x the Sonnet-Opus primary-subdomain agreement. Otherwise: no local seat.

Disagreement (sent to Fable 5.2): grade differs, role differs, knowledge function differs, primary subdomain differs,
beyond_key_points differs (added 2026-11-15), or either panelist flags ambiguous.   python3 -I <this> [--fable-sheet]"""
import glob, json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rubric
HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE)
RUN = os.environ.get("GS_RUN", "pilot")          # "full" (2026-11-15): verdicts/full/, sheets/full/, item_key_full.json
SFX = "" if RUN == "pilot" else f"/{RUN}"
records = {json.loads(l)["record_id"]: json.loads(l) for l in open(f"{EV}/records_{RUN}.jsonl")}
qs = {q["qid"]: q for q in json.load(open(f"{EV}/questions_{RUN}.json"))["questions"]}
key = json.load(open(f"{HERE}/item_key" + ("" if RUN == "pilot" else f"_{RUN}") + ".json"))

def load(tag):
    """record_id -> verdict for one panelist (Claude sheets via the item key; local files are keyed by record id)."""
    out, bad = {}, {}
    files = sorted(glob.glob(f"{HERE}/verdicts{SFX}/{tag}-*.json")) if not tag.startswith("local-") else [f"{HERE}/verdicts/{tag}.json"]
    for f in files:
        if not os.path.exists(f): continue
        d = json.load(open(f))
        for iid, v in d["verdicts"].items():
            rid = key.get(tag.replace("local-", ""), {}).get(iid, iid)
            if rid not in records: bad[iid] = ["unknown item id"]; continue
            p = rubric.validate(v, qs[records[rid]["qid"]])
            if p: bad[rid] = p
            out[rid] = v
    return out, bad

def qwk(a, b, k=4):
    n = len(a)
    if n == 0: return None
    O = [[0] * k for _ in range(k)]
    for x, y in zip(a, b): O[x][y] += 1
    ra = [sum(r) for r in O]; cb = [sum(O[i][j] for i in range(k)) for j in range(k)]
    num = sum(((i - j) ** 2) * O[i][j] for i in range(k) for j in range(k))
    den = sum(((i - j) ** 2) * ra[i] * cb[j] / n for i in range(k) for j in range(k))
    return 1 - num / den if den else None

def compare(A, B):
    ids = sorted(set(A) & set(B))
    g = [(A[i]["grade"], B[i]["grade"]) for i in ids]
    jac = [len(set(A[i]["covers"]) & set(B[i]["covers"])) / max(1, len(set(A[i]["covers"]) | set(B[i]["covers"]))) for i in ids]
    f = lambda fn: sum(fn(A[i]) == fn(B[i]) for i in ids) / len(ids) if ids else None
    return {"n": len(ids), "grade_exact": sum(x == y for x, y in g) / len(ids) if ids else None,
            "grade_within1": sum(abs(x - y) <= 1 for x, y in g) / len(ids) if ids else None,
            "grade_qwk": qwk([x for x, _ in g], [y for _, y in g]),
            "covers_jaccard": sum(jac) / len(jac) if jac else None,
            "role": f(lambda v: v["role"]), "kf": f(lambda v: v["knowledge_function"]),
            "primary_domain": f(lambda v: v["primary"]["domain"]),
            "primary_subdomain": f(lambda v: (v["primary"]["domain"], v["primary"]["subdomain"]))}

def proposer():
    return {rid: {"grade": None, "covers": r["proposed"]["covers_key_points"],
                  "role": {"distractor": "none"}.get(r["proposed"]["role"], r["proposed"]["role"]),
                  "knowledge_function": r["proposed"]["knowledge_function"], "primary": r["proposed"]["primary"]}
            for rid, r in records.items()}

LOCAL = ["local-qwen3.5-9b", "local-phi-4"] if RUN == "pilot" else []   # no local seat in the full run (gate failed)
panel = {t: load(t) for t in ["sonnet-5-5", "opus-4-8", "fable-5-2"] + LOCAL}
for t, (v, bad) in panel.items():
    print(f"{t:18} verdicts {len(v):3}  invalid {len(bad)}" + (f"  e.g. {list(bad.items())[:2]}" if bad else ""))
S, O = panel["sonnet-5-5"][0], panel["opus-4-8"][0]
fmt = lambda d: "  ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in d.items())
if S and O:
    so = compare(S, O); print("\nSONNET vs OPUS-4.8   ", fmt(so))
    print("grade distribution  sonnet", sorted(Counter(v["grade"] for v in S.values()).items()),
          " opus", sorted(Counter(v["grade"] for v in O.values()).items()))
    for t in LOCAL:
        L = panel[t][0]
        if not L: continue
        ls, lo = compare(L, S), compare(L, O)
        print(f"{t} vs SONNET  ", fmt(ls)); print(f"{t} vs OPUS-4.8", fmt(lo))
        ok = all(c["grade_qwk"] is not None and so["grade_qwk"] and c["grade_qwk"] >= 0.8 * so["grade_qwk"]
                 and c["primary_subdomain"] >= 0.8 * so["primary_subdomain"] for c in (ls, lo))
        print(f"  GATE {t}: {'PASS — earns a seat' if ok else 'FAIL — no seat'}  (thresholds qwk>={0.8*so['grade_qwk']:.3f}, primary_subdomain>={0.8*so['primary_subdomain']:.3f})")
    P = proposer()
    for t, V in (("sonnet", S), ("opus-4.8", O)):
        c = compare({k: {**P[k], "grade": 0} for k in P}, {k: {**v, "grade": 0} for k, v in V.items()})
        print(f"PROPOSER vs {t:9}", fmt({k: c[k] for k in ("n", "covers_jaccard", "role", "kf", "primary_domain", "primary_subdomain")}))
    dis = sorted(i for i in set(S) & set(O) if S[i]["grade"] != O[i]["grade"] or S[i]["role"] != O[i]["role"]
                 or S[i]["knowledge_function"] != O[i]["knowledge_function"]
                 or (S[i]["primary"]["domain"], S[i]["primary"]["subdomain"]) != (O[i]["primary"]["domain"], O[i]["primary"]["subdomain"])
                 or S[i]["beyond_key_points"] != O[i]["beyond_key_points"]   # added 2026-11-15: split beyond flags went unresolved
                 or S[i]["ambiguous"] or O[i]["ambiguous"])
    print(f"\ndisagreements for Fable: {len(dis)} of {len(set(S) & set(O))}")
    if "--fable-sheet" in sys.argv:
        fk = key["fable-5-2"]; inv = {r: i for i, r in fk.items()}
        items = [{"item_id": inv[r], "text": rubric.item_message(records[r], qs[records[r]["qid"]]),
                  "key_point_ids": [k["id"] for k in qs[records[r]["qid"]]["key_points"]]} for r in dis]
        import random; random.Random(7).shuffle(items)
        for s in range(0, len(items), 32):
            json.dump({"panelist": "fable-5-2", "items": items[s:s + 32]}, open(f"{HERE}/sheets{SFX}/fable-5-2-disagree-{s // 32 + 1}.json", "w"), indent=1, ensure_ascii=False)
        print("fable sheets written:", (len(items) + 31) // 32)
