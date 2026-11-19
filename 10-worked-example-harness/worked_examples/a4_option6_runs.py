"""A4 option 6 (blend + kind recognisers, strict: G+O1 bad<=10%) across the four UniXcoder training runs.
MEASURED from saved predictions; no model is loaded and nothing is retrained. Per run, exactly as in a4_options.py:
blend = 0.5 hgb + 0.5 UniXcoder run; kind-recogniser restack and document gate fitted on tune-half documents; operating
point chosen on the tune half; every figure on the test half (corpus-weighted) or the consensus documents.
Low-code consensus columns use the corrected line mapping (the low-code audit run indexes document lines directly).
Run:  cd Code-Orchestrator-Service && python3 a4_option6_runs.py <work_dir> <out_prefix>"""
import collections, json, os, pickle, sys
W, A6_OUT = sys.argv[1], sys.argv[2]   # not OUT: compare_v3 (exec'd via phase D) reassigns OUT
RUNS = [("Nov10", "encoder_probs_unixcoder.pkl"), ("s101", "encoder_probs_unixcoder_s101.pkl"),
        ("s202", "encoder_probs_unixcoder_s202.pkl"), ("s303", "encoder_probs_unixcoder_s303.pkl")]

src = open(os.path.join(W, "options_phase_d.py")).read().split("\ndef main():")[0]
for c in [('if os.path.exists(os.path.join(S, "encoder_probs_distilbert.pkl")):\n'
           '    SRC["distil"] = pickle.load(open(os.path.join(S, "encoder_probs_distilbert.pkl"), "rb"))\n'
           '    SRC["blend hgb+distil"] = {k: 0.5 * SRC["hgb"][k] + 0.5 * SRC["distil"][k] for k in SRC["hgb"] if k in SRC["distil"]}\n'),
          ('SRC["hgb+S0"] = restack(SRC["hgb"], False, "hgb+S0")\n'
           'SRC["hgb+KR"] = restack(SRC["hgb"], True, "hgb+KR")\n'
           'if "blend hgb+distil" in SRC:\n'
           '    SRC["blend+KR"] = restack(SRC["blend hgb+distil"], True, "blend+KR")\n')]:
    assert src.count(c) == 1, c[:60]
    src = src.replace(c, "")
__file__ = os.path.join(W, "options_phase_d.py")
exec(src, globals())

GROUPS = {"code-bearing": ("book", "short", "tiny"), "low-code": ("lowcode",), "code-free": ("codefree",)}
def pooled_bad(keep):
    raw = {}
    for s, docs in segs.items():
        docs = [b for b in docs if half(b["stem"]) == 1]; acc = np.zeros(2)
        for b in docs:
            code, prose = LAB[b["stem"]]
            for idx in keep(b["stem"]):
                nc, npr = code[idx].sum(), prose[idx].sum()
                if nc + npr: acc += [1, nc == 0]
        raw[s] = (acc, len(docs))
    out = {}
    for g, members in GROUPS.items():
        Wc = np.zeros(2)
        for s in members:
            acc, n = raw.get(s, (None, 0))
            if n and s in share: Wc += share[s] * acc / n
        out[g] = round(Wc[1] / Wc[0], 3) if Wc[0] else None
    cf = [b["stem"] for b in segs["codefree"] if half(b["stem"]) == 1]
    out["codefree_docs_with_any_block"] = f"{sum(1 for st in cf if keep(st))}/{len(cf)}"
    return out

LC = consensus("run_2026-10-28c_lowcode")
def lowcode_kept(keep):
    k = collections.Counter()
    for it in LC.values():
        if it["stem"] not in GOLD: continue
        on = any(it["line_index"] in set(map(int, b)) for b in keep(it["stem"]))
        k[(it["consensus"], on)] += 1
    return {"lowcode_code_kept": f"{k[('code', True)]}/{k[('code', True)] + k[('code', False)]}",
            "lowcode_prose_kept": f"{k[('not_code', True)]}/{k[('not_code', True)] + k[('not_code', False)]}"}

res = {}
for run, f in RUNS:
    enc = pickle.load(open(os.path.join(W, f), "rb"))
    SRC["blend"] = {k: 0.5 * SRC["hgb"][k] + 0.5 * enc[k] for k in SRC["hgb"] if k in enc}
    SRC["blend+KR"] = restack(SRC["blend"], True, f"blend+KR {run}")
    _rc.clear()                                                   # runs() caches by source name; sources change per run
    gate, gq = make_gate("blend+KR", False)
    ch = choose("blend+KR", gate); pts = ch.pop("_points")
    t, tr, h = pts["gate"]["G+O1<=10%"]
    keep = sel("blend+KR", t, tr, gate, h)
    w, per = score(1, keep); g = gold_score(keep)
    res[run] = {"predictions": f, "thresholds": {"line": t, "run": tr, "gate": h}, "gate_quality": gq,
                "consensus": {"P": g["P"], "R": g["R"], **lowcode_kept(keep)}, "corpus_weighted": w, "bad_by_segment": pooled_bad(keep)}
    r = res[run]
    log(f"{run:6s} t {t} run {tr} gate {h} | cons P {g['P']:.3f} R {g['R']:.3f} | F1 {w['F1']:.3f} bad {w['bad']:.1%} | {r['bad_by_segment']} | {r['consensus']}")

spread = {}
for key, get in [("consensus_P", lambda r: r["consensus"]["P"]), ("consensus_R", lambda r: r["consensus"]["R"]),
                 ("corpus_F1", lambda r: r["corpus_weighted"]["F1"]), ("bad_corpus", lambda r: r["corpus_weighted"]["bad"]),
                 ("bad_code_bearing", lambda r: r["bad_by_segment"]["code-bearing"]), ("bad_low_code", lambda r: r["bad_by_segment"]["low-code"]),
                 ("bad_code_free", lambda r: r["bad_by_segment"]["code-free"])]:
    v = [get(r) for r in res.values()]; spread[key] = {"min": min(v), "max": max(v)}
json.dump({"measured": True, "configuration": "6 Blend + KR, strict (G+O1 bad<=10%)", "runs": res, "spread": spread,
           "tuning": "each run's thresholds are chosen on that run's own tune half (same tune/test split for all runs)",
           "not_reproduced": ["full-data retrain", "fresh extraction through COS", "the unmeasured 15% of the corpus"]},
          open(A6_OUT + ".json", "w"), indent=1, default=float)
log("done")
