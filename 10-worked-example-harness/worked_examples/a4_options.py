"""A4 worked examples: the code-detector choices (4a detector x 4b operating point), measured from saved predictions.
No model is loaded and nothing is retrained: line probabilities come from the saved pickles, and only the light
scikit-learn pieces the configurations themselves define (document gate, kind-recogniser restack) are fitted, exactly
as in phase D (options_phase_d.py, whose scorer, gate, restack and operating-point chooser are reused unchanged).

Configurations (thresholds chosen on the tune half; every figure on the test half or the consensus documents):
  1  HGB + gate, balanced         source hgb,             G+O1 bad<=15%
  2  Blend + gate, balanced       source blend,           G+O1 bad<=15%
  3  HGB + gate, strict           source hgb,             G+O1 bad<=10%
  4  Blend + gate, strict         source blend,           G+O1 bad<=10%
  5  HGB + KR, strict             source hgb+KR,          G+O1 bad<=10%
  6  Blend + KR, strict           source blend+KR,        G+O1 bad<=10%   (new)
  hgb    = gradient-boosted (e)+ng line model, consensus documents held out (hgb_holdout_probs.pkl)
  blend  = 0.5 hgb + 0.5 UniXcoder, seed 202 (encoder_probs_unixcoder_s202.pkl; the median of the three seed runs)
  +KR    = phase D restack with kind recognisers, fitted on tune-half documents only
Run:  cd Code-Orchestrator-Service && python3 a4_options.py <work_dir> <out_prefix>"""
import collections, json, os, pickle, sys
W, A4_OUT = sys.argv[1], sys.argv[2]   # not OUT: compare_v3 (exec'd via phase D) reassigns OUT
SEED = os.environ.get("A4_SEED", "202")

# ---- reuse phase D's definitions; drop its distilbert sources and its module-level restacks (not used here)
src = open(os.path.join(W, "options_phase_d.py")).read().split("\ndef main():")[0]
cut = [('if os.path.exists(os.path.join(S, "encoder_probs_distilbert.pkl")):\n'
        '    SRC["distil"] = pickle.load(open(os.path.join(S, "encoder_probs_distilbert.pkl"), "rb"))\n'
        '    SRC["blend hgb+distil"] = {k: 0.5 * SRC["hgb"][k] + 0.5 * SRC["distil"][k] for k in SRC["hgb"] if k in SRC["distil"]}\n'),
       ('SRC["hgb+S0"] = restack(SRC["hgb"], False, "hgb+S0")\n'
        'SRC["hgb+KR"] = restack(SRC["hgb"], True, "hgb+KR")\n'
        'if "blend hgb+distil" in SRC:\n'
        '    SRC["blend+KR"] = restack(SRC["blend hgb+distil"], True, "blend+KR")\n')]
for c in cut:
    assert src.count(c) == 1, c[:60]
    src = src.replace(c, "")
__file__ = os.path.join(W, "options_phase_d.py")
exec(src, globals())

enc = pickle.load(open(os.path.join(W, f"encoder_probs_unixcoder_s{SEED}.pkl"), "rb"))
SRC["blend"] = {k: 0.5 * SRC["hgb"][k] + 0.5 * enc[k] for k in SRC["hgb"] if k in enc}
SRC["hgb+KR"] = restack(SRC["hgb"], True, "hgb+KR")
SRC["blend+KR"] = restack(SRC["blend"], True, "blend+KR")

CONFIGS = [("1 HGB + gate, balanced", "hgb", "G+O1<=15%"), ("2 Blend + gate, balanced", "blend", "G+O1<=15%"),
           ("3 HGB + gate, strict", "hgb", "G+O1<=10%"), ("4 Blend + gate, strict", "blend", "G+O1<=10%"),
           ("5 HGB + KR, strict", "hgb+KR", "G+O1<=10%"), ("6 Blend + KR, strict", "blend+KR", "G+O1<=10%")]

# ---- per-segment detail, with a pooled code-bearing figure (census shares of book / short / tiny)
GROUPS = {"code-bearing": ("book", "short", "tiny"), "low-code": ("lowcode",), "code-free": ("codefree",), "transcript": ("transcript",)}
def seg_detail(keep):
    raw = {}
    for s, docs in segs.items():
        docs = [b for b in docs if half(b["stem"]) == 1]
        acc = np.zeros(5)
        for b in docs:
            code, prose = LAB[b["stem"]]; pred = np.zeros(len(code), bool); blocks = bad = 0
            for idx in keep(b["stem"]):
                pred[idx] = True; nc, npr = code[idx].sum(), prose[idx].sum()
                if nc + npr: blocks += 1; bad += nc == 0
            acc += [(pred & code).sum(), (pred & prose).sum(), (~pred & code).sum(), blocks, bad]
        raw[s] = (acc, len(docs))
    out = {}
    for s, (acc, n) in raw.items():
        tp, fp, fn, bl, bd = acc
        out[s] = {"docs": n, "blocks": int(bl), "bad_blocks": int(bd), "bad_share": round(bd / bl, 3) if bl else None,
                  "blocks_per_doc": round(bl / n, 2) if n else None, "P": round(tp / max(1, tp + fp), 3), "R": round(tp / max(1, tp + fn), 3)}
    pooled = {}
    for g, members in GROUPS.items():
        Wc = np.zeros(5); wsum = 0
        for s in members:
            acc, n = raw.get(s, (None, 0))
            if n and s in share: Wc += share[s] * acc / n; wsum += share[s]
        pooled[g] = {"census_share": round(wsum, 4), "bad_share": round(Wc[4] / Wc[3], 3) if Wc[3] else None,
                     "P": round(Wc[0] / max(1e-9, Wc[0] + Wc[1]), 3), "R": round(Wc[0] / max(1e-9, Wc[0] + Wc[2]), 3)}
    return out, pooled

gates, keeps, chosen, metrics = {}, {}, {}, {}
for name, s_, pt in CONFIGS:
    if s_ not in gates:
        gates[s_], _ = make_gate(s_, False)
    ch = choose(s_, gates[s_]); pts = ch.pop("_points")
    key = pts["gate"][pt]
    t, tr, h = key
    keeps[name] = sel(s_, t, tr, gates[s_], h); chosen[name] = {"source": s_, "target": pt, "t": t, "run": tr, "gate": h}
    w, per = score(1, keeps[name]); g = gold_score(keeps[name]); det, pooled = seg_detail(keeps[name])
    metrics[name] = {"corpus_weighted": w, "consensus": g, "segments": det, "pooled": pooled}
    log(f"{name:28s} t {t} run {tr} gate {h} | consensus P {g['P']:.3f} R {g['R']:.3f} | corpus F1 {w['F1']:.3f} bad {w['bad']:.1%} | "
        + " ".join(f"{k} {v['bad_share']}" for k, v in pooled.items()))

# ---- consensus label per (stem, line) over every audit run: 3-of-4 majority, else "no 3-of-4 agreement"
LABEL = {}
for r in list(RUN_KEYS) + ["run_2026-10-28c_lowcode"]:
    h = json.load(open(os.path.join(E_DIR, r, "font_labels_HIDDEN.json")))
    revs = [json.load(open(os.path.join(E_DIR, r, f)))["verdicts"] for f in sorted(os.listdir(os.path.join(E_DIR, r))) if f.startswith("verdicts_")]
    for iid, v in h.items():
        if v["stem"] not in GOLD: continue
        top, c = collections.Counter(x[iid] for x in revs if iid in x).most_common(1)[0]
        # the three main runs index lines flat across pages (FLAT maps them, skipping page breaks); the low-code run
        # indexes the document lines directly (verified against each run's audit_sheet TARGET text: 300/300 and 200/200)
        li = v["line_index"] if r == "run_2026-10-28c_lowcode" else FLAT[v["stem"]][v["line_index"]]
        LABEL[(v["stem"], li)] = top if c >= 3 and top in ("code", "not_code") else "no 3-of-4 agreement"

# corrected low-code consensus columns (phase A/C/D's gold_score maps the low-code run through FLAT, which lands on the
# right line for only 17 of its 200 items, so its lowcode_code_kept / lowcode_prose_kept fields are not used here)
LC = consensus("run_2026-10-28c_lowcode")
for name, *_ in CONFIGS:
    kept = collections.Counter()
    for it in LC.values():
        if it["stem"] not in GOLD: continue
        on = any(it["line_index"] in set(map(int, b)) for b in keeps[name](it["stem"]))
        kept[(it["consensus"], on)] += 1
    m = metrics[name]["consensus"]
    m["lowcode_code_kept_phaseD_mapping_WRONG"] = m.pop("lowcode_code_kept"); m["lowcode_prose_kept_phaseD_mapping_WRONG"] = m.pop("lowcode_prose_kept")
    m["lowcode_code_kept"] = f"{kept[('code', True)]}/{kept[('code', True)] + kept[('code', False)]}"
    m["lowcode_prose_kept"] = f"{kept[('not_code', True)]}/{kept[('not_code', True)] + kept[('not_code', False)]}"

# ---- example documents: test half, in a segment, also a consensus document, never in any training set
train_stems = {b["stem"] for b in train}
seg_of = {b["stem"]: s for s, v in segs.items() for b in v}
def eligible(seg_names, need_gold=True):
    out = []
    for st, s in seg_of.items():
        if s not in seg_names or half(st) != 1 or st in train_stems: continue
        if need_gold and not (st in GOLD and GOLD[st]["_t"][1] == DOCS[st]["_t"][1]): continue   # same lines in both views
        nlab = collections.Counter(v for (s2, _), v in LABEL.items() if s2 == st)
        out.append((st, s, nlab))
    return out

pick = {}
named = [x for x in eligible({"book", "short", "tiny", "40-book key"}) if any(k in x[0].lower() for k in ("iceberg", "aws cookbook", "aws_cookbook"))]
cand_a = eligible({"book", "short", "tiny"})
rule_a = "named book (Iceberg / AWS Cookbook) in a test split" if named else "no Iceberg / AWS Cookbook document is in a test split; comparable: the code-bearing test document with the most consensus-code lines"
pick["A"] = (max(named or cand_a, key=lambda x: x[2]["code"])[:2], rule_a)
pick["B"] = (max(eligible({"lowcode"}), key=lambda x: (x[2]["code"], sum(x[2].values())))[:2], "low-code test document with the most consensus-code lines (ties: most labelled lines)")
cf = eligible({"codefree"})
if cf:
    pick["C"] = (max(cf, key=lambda x: sum(x[2].values()))[:2], "code-free test document with the most consensus-labelled lines")
else:   # no code-free consensus document exists: median-length code-free test document, font labels only (all not-code)
    cf = sorted(eligible({"codefree"}, need_gold=False), key=lambda x: (sum(bool(l.strip()) for l in DOCS[x[0]]["_t"][1]), x[0]))
    pick["C"] = (cf[len(cf) // 2][:2], "no code-free document has consensus labels; median-length code-free test document "
                 "(by non-blank lines), font labels only: the code-free stratum has no monospace text, so every block is a bad block")

# code-free test documents that receive any block, per configuration (measured)
cf_test = [b["stem"] for b in segs["codefree"] if half(b["stem"]) == 1]
for name, *_ in CONFIGS:
    metrics[name]["codefree_docs_with_any_block"] = f"{sum(1 for st in cf_test if keeps[name](st))}/{len(cf_test)}"

examples = {}
for tag, (sel_, rule) in pick.items():
    if sel_ is None:
        examples[tag] = {"rule": rule, "document": None}; continue
    st, s = sel_; lines = DOCS[st]["_t"][1]; code_lab, prose_lab = LAB[st]
    cons_code = sorted(i for (s2, i), v in LABEL.items() if s2 == st and v == "code")
    ex = {"rule": rule, "document": st, "segment": s, "doc_pages": DOCS[st].get("doc_pages"),
          "split": "test half (half(stem)==1)" + (", consensus document" if st in GOLD else ", not a consensus document"),
          "in_training_set": st in train_stems, "nonblank_lines": int(sum(bool(l.strip()) for l in lines)),
          "font_code_lines": int(code_lab.sum()), "consensus_labelled_lines": dict(collections.Counter(v for (s2, _), v in LABEL.items() if s2 == st)),
          "configs": {}}
    for name, s_, pt in CONFIGS:
        c = chosen[name]; gscore = float(gates[s_].get(st, 0)); suppressed = gscore < c["gate"]
        blocks = []
        for idx in keeps[name](st):
            idx = [int(i) for i in idx]; labs = collections.Counter(LABEL.get((st, i), "no consensus label") for i in idx)
            blocks.append({"first_lines": [lines[i] for i in idx[:3]], "line_count": len(idx), "line_range": [idx[0], idx[-1]],
                           "consensus": dict(labs), "font_code_lines": int(code_lab[idx].sum()), "font_prose_lines": int(prose_lab[idx].sum())})
        kept = {i for b in keeps[name](st) for i in map(int, b)}
        ex["configs"][name] = {"gate_score": round(gscore, 3), "gate_threshold": c["gate"], "gate_suppressed": bool(suppressed),
                               "blocks": blocks, "missed_consensus_code_lines": [{"line": i, "text": lines[i]} for i in cons_code if i not in kept],
                               "font_code_lines_missed": int(sum(1 for i in np.where(code_lab)[0] if int(i) not in kept)),
                               "font_code_lines_total": int(code_lab.sum())}
    examples[tag] = ex

json.dump({"measured": True, "seed": SEED, "configs": chosen, "metrics": metrics, "examples": examples,
           "not_reproduced": ["a full-data retrain (line models here saw the v5 key folds 1-3 plus the low-code / code-free training strata, capped at 32K code lines for UniXcoder)",
                              "a fresh extraction run through COS: blocks here are runs over the already-extracted JSON lines, scored offline",
                              "the unmeasured 15% of the corpus (scans, non-monospace code, unlabellable documents)",
                              "blend figures are one seed (202); the four-run spread is in work_seeds_2026-11-12/options_blend_hgb_unixcoder_s*.log"]},
          open(A4_OUT + ".json", "w"), indent=1, default=float)

with open(A4_OUT + ".txt", "w") as fh:
    P = lambda *a: print(*a, file=fh)
    P(f"A4 worked examples (MEASURED from saved predictions; blend = UniXcoder seed {SEED}; test halves / consensus documents)\n")
    P(f"{'configuration':28s} {'t':>5s} {'run':>5s} {'gate':>5s} {'consP':>6s} {'consR':>6s} {'corpF1':>7s} {'bad':>6s} {'code-bearing':>13s} {'low-code':>9s} {'code-free':>10s}")
    for name, *_ in CONFIGS:
        c, m = chosen[name], metrics[name]; pl = m["pooled"]
        f = lambda v: f"{v:.1%}" if v is not None else "n/a"
        P(f"{name:28s} {c['t']:5} {str(c['run']):>5s} {c['gate']:5} {m['consensus']['P']:6.3f} {m['consensus']['R']:6.3f} {m['corpus_weighted']['F1']:7.3f} "
          f"{m['corpus_weighted']['bad']:6.1%} {f(pl['code-bearing']['bad_share']):>13s} {f(pl['low-code']['bad_share']):>9s} {f(pl['code-free']['bad_share']):>10s}")
    P("\ncode-free / low-code blocks per test document:")
    for name, *_ in CONFIGS:
        d = metrics[name]["segments"]
        P(f"  {name:28s} code-free {d['codefree']['blocks']} blocks in {d['codefree']['docs']} docs "
          f"({metrics[name]['codefree_docs_with_any_block']} docs get any block); low-code {d['lowcode']['blocks']} blocks "
          f"({d['lowcode']['bad_blocks']} bad) in {d['lowcode']['docs']} docs; transcript {d['transcript']['blocks']} blocks")
    for tag, ex in examples.items():
        P(f"\n=== ({tag}) {ex['rule']}")
        if not ex.get("document"): continue
        P(f"document: {ex['document']} | segment {ex['segment']} | {ex['doc_pages']} pages | {ex['split']} | in training: {ex['in_training_set']}")
        P(f"nonblank lines {ex['nonblank_lines']}, font-code lines {ex['font_code_lines']}, consensus-labelled lines {ex['consensus_labelled_lines']}")
        for name, cx in ex["configs"].items():
            P(f"\n  [{name}] gate {cx['gate_score']} vs {cx['gate_threshold']}{' -> SUPPRESSED' if cx['gate_suppressed'] else ''}; {len(cx['blocks'])} blocks")
            for b in cx["blocks"]:
                P(f"    - {b['line_count']} lines (L{b['line_range'][0]}-{b['line_range'][1]}), consensus {b['consensus']}, font code/prose {b['font_code_lines']}/{b['font_prose_lines']}")
                for l in b["first_lines"]: P(f"        | {l[:110]}")
            P(f"    font-labelled code lines missed: {cx['font_code_lines_missed']}/{cx['font_code_lines_total']}")
            if cx["missed_consensus_code_lines"]:
                P(f"    missed consensus-code lines ({len(cx['missed_consensus_code_lines'])}):")
                for m_ in cx["missed_consensus_code_lines"]: P(f"        L{m_['line']}: {m_['text'][:110]}")
log("done")
