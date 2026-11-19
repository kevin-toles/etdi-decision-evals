"""Options phase A on the cached v5+extra line model (test halves; every threshold chosen on the tune halves):
  G   document gate: per-document classifier on prediction statistics ('has code blocks'), suppresses extraction
  O1  operating points: (t, t_run) that maximise corpus-weighted recall subject to a bad-block target (20/15/10/5%)
  O2  confidence downstream: extract at a recall-oriented setting, store every block with its block confidence and
      the document gate score; serve a block only when both clear thresholds (stored vs served figures)
  combinations: G+O1, G+O2 (O2 already uses the gate score), and the reference rows (today's detector, current best).
Writes options_phase_a.json and the per-run tables used by phase B/C.
    cd Code-Orchestrator-Service && python3 <this>"""
import collections, hashlib, json, os, pickle, sys
S = os.path.dirname(os.path.abspath(__file__))


def main():
    sys.argv = ["x", os.path.join(S, "census_v5.json"), os.path.join(S, "report_segments_v5_extra.json")]
    os.environ["TRAIN_EXTRA"] = "train_v5_lowcode.jsonl,train_v5_codefree.jsonl"
    src = open(os.path.join(S, "eval_segments_v5.py")).read()
    exec(src[:src.index("TS = np.round")], globals())
    ENC = os.environ.get("ENCODER_PROBS"); W_HGB = float(os.environ.get("BLEND_HGB", "0"))
    TAG = os.environ.get("TAG", "a")
    global T_MIN
    T_MIN = float(os.environ.get("T_MIN", "0.5"))     # 0.58 keeps a 0.15 encoder cascade exact for 50/50 blends
    BASE = os.environ.get("BASE_PROBS")
    if BASE:                                      # e.g. the consensus-holdout gradient-boosted model
        base_p = pickle.load(open(BASE, "rb"))
        for k in list(probs):
            probs[k] = base_p[k]
    if ENC:                                       # phase B: encoder line probabilities, alone or blended
        enc = pickle.load(open(ENC, "rb"))
        for k in list(probs):
            probs[k] = W_HGB * probs[k] + (1 - W_HGB) * enc[k]
    from sklearn.ensemble import HistGradientBoostingClassifier
    WS = [s for s in segs if s in share]

    runs_cache = {}
    def runs_for(b, t):
        key = (b["stem"], round(t, 3))
        if key not in runs_cache:
            rid, means = doc_arrays(b, t)
            runs_cache[key] = [(np.where(rid == r)[0], float(means[r])) for r in range(len(means))]
        return runs_cache[key]

    def score(part, keep, segs_only=None):
        """keep(b) -> list of index arrays. Corpus-weighted P/R/F1/bad-block share, plus per segment."""
        W = np.zeros(5); per = {}
        for s, docs in segs.items():
            docs = [b for b in docs if half(b["stem"]) == part]
            if not docs: continue
            acc = np.zeros(5)
            for b in docs:
                code, prose = LAB[b["stem"]]; pred = np.zeros(len(code), bool); blocks = bad = 0
                for idx in keep(b):
                    pred[idx] = True; nc, npr = code[idx].sum(), prose[idx].sum()
                    if nc + npr: blocks += 1; bad += nc == 0
                acc += [(pred & code).sum(), (pred & prose).sum(), (~pred & code).sum(), blocks, bad]
            tp, fp, fn, bl, bd = acc; p = tp / max(1, tp + fp); r = tp / max(1, tp + fn)
            per[s] = {"P": round(p, 3), "R": round(r, 3), "F1": round(2 * p * r / max(1e-9, p + r), 3), "blocks": int(bl), "bad": round(bd / max(1, bl), 3)}
            if s in share: W += share[s] * acc / len(docs)
        p = W[0] / max(1e-9, W[0] + W[1]); r = W[0] / max(1e-9, W[0] + W[2])
        return {"P": round(p, 3), "R": round(r, 3), "F1": round(2 * p * r / max(1e-9, p + r), 3), "bad": round(W[4] / max(1e-9, W[3]), 3)}, per

    rules = {}

    class Rows(dict):                             # records the rule (keep function) behind every row
        def __setitem__(self, k, v):
            rules[k] = score.last
            super().__setitem__(k, v)
    rows = Rows()
    _score = score
    def score(part, keep, segs_only=None):        # wraps the scorer to remember each row's rule for phase C
        score.last = keep
        return _score(part, keep, segs_only)
    det = HeuristicCodeDetector(); base = {}
    for docs in segs.values():
        for b in docs:
            if half(b["stem"]) == 1:
                base[b["stem"]] = [np.arange(a, e + 1) for a, e, _ in spans(b["_t"][0], b["_t"][1], det.detect_candidates(b["_t"][0]))]
    rows["today: HeuristicCodeDetector"] = score(1, lambda b: base.get(b["stem"], []))
    cur = lambda b, t=0.8, tr=0.94: [idx for idx, m in runs_for(b, t) if m >= tr]
    rows["current best: (e)+ng+run .80/.94"] = score(1, cur)

    # best corpus-weighted F1 point for these probabilities (tune half), for a like-for-like model comparison
    _grid = [(t, tr) for t in [round(x, 2) for x in np.arange(T_MIN, 0.981, 0.04)] for tr in [None] + [round(x, 2) for x in np.arange(0.5, 0.991, 0.03)]]
    _bt, _btr = max(_grid, key=lambda x: score(0, lambda b: [idx for idx, m in runs_for(b, x[0]) if x[1] is None or m >= x[1]])[0]["F1"])
    rows[f"best-F1 point for these probabilities (t {_bt}, run {_btr})"] = score(1, lambda b: [idx for idx, m in runs_for(b, _bt) if _btr is None or m >= _btr])

    # ---- O1: operating points by bad-block target (chosen on tune half)
    TS = [round(x, 2) for x in np.arange(T_MIN, 0.981, 0.04)]; TR = [None] + [round(x, 2) for x in np.arange(0.5, 0.991, 0.03)]
    grid = {}
    for t in TS:
        for tr in TR:
            k = lambda b, t=t, tr=tr: [idx for idx, m in runs_for(b, t) if tr is None or m >= tr]
            grid[(t, tr)] = score(0, k)[0]
    o1 = {}
    for target in (0.20, 0.15, 0.10, 0.05):
        ok = [(v["R"], key) for key, v in grid.items() if v["bad"] <= target]
        if not ok: continue
        _, (t, tr) = max(ok); o1[target] = (t, tr)
        rows[f"O1 bad<={target:.0%} (t {t}, run {tr})"] = score(1, lambda b, t=t, tr=tr: [idx for idx, m in runs_for(b, t) if tr is None or m >= tr])

    # ---- G: document gate
    def doc_feats(b):
        p = probs[b["stem"]]; lines = b["_t"][1]; nz = np.array([bool(l.strip()) for l in lines]); p = p[nz] if nz.any() else p
        rs = runs_for(b, 0.8); lens = [len(i) for i, _ in rs]; ms = [m for _, m in rs]
        top = np.sort(p)[-20:] if len(p) else np.zeros(1)
        return [len(p), (p > 0.5).mean() if len(p) else 0, (p > 0.8).mean() if len(p) else 0, (p > 0.95).mean() if len(p) else 0,
                float(top.mean()), float(p.max()) if len(p) else 0, len(rs), max(lens, default=0), float(np.mean(lens)) if lens else 0,
                max(ms, default=0), sum(m >= 0.94 for m in ms), sum(l >= 5 for l in lens), b.get("doc_pages", 0)]
    docs_all = [b for v in segs.values() for b in v]
    F = {b["stem"]: doc_feats(b) for b in docs_all}
    has_code = {b["stem"]: int(LAB[b["stem"]][0].sum() >= 5) for b in docs_all}
    tune = [b for b in docs_all if half(b["stem"]) == 0]; test = [b for b in docs_all if half(b["stem"]) == 1]
    Xt = np.array([F[b["stem"]] for b in tune]); yt = np.array([has_code[b["stem"]] for b in tune])
    fold = np.array([int(hashlib.sha256(b["stem"].encode()).hexdigest(), 16) % 3 for b in tune]); oof = np.zeros(len(tune))
    for k in range(3):
        g = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, random_state=0).fit(Xt[fold != k], yt[fold != k])
        oof[fold == k] = g.predict_proba(Xt[fold == k])[:, 1]
    gate_clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, random_state=0).fit(Xt, yt)
    gscore = {b["stem"]: s for b, s in zip(tune, oof)}
    gscore.update({b["stem"]: s for b, s in zip(test, gate_clf.predict_proba(np.array([F[b["stem"]] for b in test]))[:, 1])})
    best_g = max(np.arange(0.05, 0.96, 0.05), key=lambda h: score(0, lambda b: cur(b) if gscore[b["stem"]] >= h else [])[0]["F1"])
    rows[f"G gate (>= {best_g:.2f}) + current best"] = score(1, lambda b: cur(b) if gscore[b["stem"]] >= best_g else [])
    # gate quality itself
    gt = np.array([has_code[b["stem"]] for b in test]); gp = np.array([gscore[b["stem"]] >= best_g for b in test])
    gate_quality = {"docs": len(test), "has_code": int(gt.sum()), "gate_kept": int(gp.sum()),
                    "precision": round(float((gp & (gt == 1)).sum() / max(1, gp.sum())), 3), "recall": round(float((gp & (gt == 1)).sum() / max(1, gt.sum())), 3)}

    # ---- G+O1: gate on top of each bad-block target, operating point re-chosen with the gate on (tune half)
    for target in (0.20, 0.15, 0.10, 0.05):
        cands = []
        for (t, tr) in grid:
            for h in (0.2, 0.35, 0.5, 0.65, 0.8):
                k = lambda b, t=t, tr=tr, h=h: [idx for idx, m in runs_for(b, t) if tr is None or m >= tr] if gscore[b["stem"]] >= h else []
                cands.append(((t, tr, h), k))
        scored = [(score(0, k)[0], key, k) for key, k in cands[::3]]          # thinned grid for speed
        ok = [(v["R"], key, k) for v, key, k in scored if v["bad"] <= target]
        if not ok: continue
        _, key, k = max(ok, key=lambda x: x[0])
        rows[f"G+O1 bad<={target:.0%} (t {key[0]}, run {key[1]}, gate {key[2]})"] = score(1, k)

    # ---- O2: store recall-oriented blocks; serve by block confidence x gate score
    store = lambda b: [idx for idx, m in runs_for(b, 0.7)]
    rows["O2 stored (t .70, no run filter, all kept)"] = score(1, store)
    serve_grid = [(a, h) for a in np.arange(0.70, 0.991, 0.03) for h in (0.0, 0.2, 0.35, 0.5, 0.65, 0.8)]
    sv = lambda a, h: (lambda b: [idx for idx, m in runs_for(b, 0.7) if m >= a] if gscore[b["stem"]] >= h else [])
    a_b, h_b = max(serve_grid, key=lambda x: score(0, sv(*x))[0]["F1"])
    rows[f"O2 served best-F1 (block conf {a_b:.2f}, gate {h_b})"] = score(1, sv(a_b, h_b))
    for target in (0.10, 0.05):
        ok = [(score(0, sv(a, h))[0]["R"], (a, h)) for a, h in serve_grid if score(0, sv(a, h))[0]["bad"] <= target]
        if ok:
            _, (a, h) = max(ok); rows[f"O2 served bad<={target:.0%} (block conf {a:.2f}, gate {h})"] = score(1, sv(a, h))

    print(f"gate quality on test docs: {gate_quality}")
    gold_eval = phase_c(rows, rules, probs, F_fn=doc_feats, gate_clf=gate_clf, gscore=gscore, runs_for=runs_for, best_g=best_g) if os.environ.get("GOLD") else None
    print(f"\n{'configuration (test half, corpus-weighted)':62s} {'P':>6s} {'R':>6s} {'F1':>6s} {'bad blk':>8s}")
    for k, (w, _) in rows.items():
        print(f"{k:62s} {w['P']:6.3f} {w['R']:6.3f} {w['F1']:6.3f} {w['bad']:8.1%}")
    print("\nper segment, bad-block share / recall:")
    segnames = list(next(iter(rows.values()))[1].keys())
    print(f"{'':62s}" + "".join(f"{s[:9]:>15s}" for s in segnames))
    for k, (_, per) in rows.items():
        print(f"{k[:62]:62s}" + "".join(f"{per[s]['bad']:7.0%}/{per[s]['R']:.2f}  " if s in per else " " * 15 for s in segnames))
    json.dump({"gold": gold_eval, "gate_quality": gate_quality, "rows": {k: {"weighted": w, "segments": p} for k, (w, p) in rows.items()},
               "gate_threshold": float(best_g)}, open(os.path.join(S, f"options_phase_{TAG}.json"), "w"), indent=1, default=float)
    pickle.dump({"gscore": gscore, "has_code": has_code}, open(os.path.join(S, f"options_gate_scores_{TAG}.pkl"), "wb"))


E_DIR = "<EVIDENCE>/code_label_audit"
RUN_KEYS = {"run_2026-10-28": ("answer_key_v3.jsonl", []), "run_2026-10-28b": ("answer_key_v4.jsonl", ["run_2026-10-28"]),
            "run_2026-10-29d": ("answer_key_v5.jsonl", ["run_2026-10-28", "run_2026-10-28b"])}


def consensus(run):
    h = json.load(open(os.path.join(E_DIR, run, "font_labels_HIDDEN.json")))
    revs = [json.load(open(os.path.join(E_DIR, run, f)))["verdicts"] for f in sorted(os.listdir(os.path.join(E_DIR, run))) if f.startswith("verdicts_")]
    out = {}
    for iid, v in h.items():
        top, c = collections.Counter(r[iid] for r in revs).most_common(1)[0]
        if c >= 3 and top in ("code", "not_code"):
            out[iid] = {**v, "consensus": top}
    return out


def pool_sizes(run):
    """Labelled non-blank lines per (kind, font label) in the pool the run sampled from (its key minus excluded runs)."""
    cache = os.path.join(S, f"pool_{run}.json")
    if os.path.exists(cache):
        return {tuple(k.split("|")): v for k, v in json.load(open(cache)).items()}
    keyf, excl = RUN_KEYS[run]
    ex = {v["stem"] for r in excl for v in json.load(open(os.path.join(E_DIR, r, "font_labels_HIDDEN.json"))).values()}
    c = collections.Counter()
    for line in open(os.path.join(S, keyf)):
        d = json.loads(line)
        if d["stem"] in ex: continue
        kind = "book" if d["doc_pages"] >= 60 else "short"
        for p in d["pages"]:
            for t, lab in p["lines"]:
                if lab is not None and t.strip(): c[(kind, "code" if lab else "not_code")] += 1
    json.dump({"|".join(k): v for k, v in c.items()}, open(cache, "w"))
    return dict(c)


def phase_c(rows, rules, probs, F_fn, gate_clf, gscore, runs_for, best_g):
    """Score every row's rule against the four-reviewer consensus (documents never trained on)."""
    gold = json.load(open(os.path.join(S, "gold_docs.json")))
    srcs = [pickle.load(open(f, "rb")) for f in (os.environ.get("BASE_PROBS"), os.environ.get("ENCODER_PROBS")) if f]
    w = float(os.environ.get("BLEND_HGB", "0"))
    for st, d in gold.items():
        d["_t"] = book_text(d)
        if os.environ.get("ENCODER_PROBS") and os.environ.get("BASE_PROBS"):
            probs[st] = w * srcs[0][st] + (1 - w) * srcs[1][st]
        else:
            probs[st] = srcs[-1][st]
    for st, d in gold.items():
        gscore[st] = float(gate_clf.predict_proba(np.array([F_fn(d)]))[0, 1])
    det = HeuristicCodeDetector()
    flat = {}
    for st, d in gold.items():
        m, j = [], 0
        for k, pg in enumerate(d["pages"]):
            if k: j += 1
            for _ in pg["lines"]:
                m.append(j); j += 1
        flat[st] = m
    cons = {r: consensus(r) for r in list(RUN_KEYS) + ["run_2026-10-28c_lowcode"]}
    pools = {r: pool_sizes(r) for r in RUN_KEYS}
    out = {}
    for name, keep in rules.items():
        pred = {}
        for st, d in gold.items():
            v = np.zeros(len(d["_t"][1]), bool)
            idxs = ([np.arange(a, e + 1) for a, e, _ in spans(d["_t"][0], d["_t"][1], det.detect_candidates(d["_t"][0]))]
                    if name.startswith("today") else keep(d))
            for idx in idxs: v[idx] = True
            pred[st] = v
        res = {}
        Ps, Rs = [], []
        for r in RUN_KEYS:
            n = collections.Counter(); hits = collections.Counter()
            for it in cons[r].values():
                s_ = (it["kind"], it["font_label"]); n[s_] += 1
                hits[(s_, bool(pred[it["stem"]][flat[it["stem"]][it["line_index"]]]), it["consensus"] == "code")] += 1
            tp = fp = fn = 0.0
            for s_ in n:
                wgt = pools[r].get(s_, 0) / n[s_]
                tp += wgt * hits[(s_, True, True)]; fp += wgt * hits[(s_, True, False)]; fn += wgt * hits[(s_, False, True)]
            P = tp / max(1e-9, tp + fp); R = tp / max(1e-9, tp + fn); Ps.append(P); Rs.append(R)
            res[r] = {"P": round(P, 3), "R": round(R, 3)}
        res["mean_code_bearing"] = {"P": round(float(np.mean(Ps)), 3), "R": round(float(np.mean(Rs)), 3)}
        lc = collections.Counter()
        for it in cons["run_2026-10-28c_lowcode"].values():
            lc[(it["consensus"], bool(pred[it["stem"]][flat[it["stem"]][it["line_index"]]]))] += 1
        res["lowcode"] = {"true_code_kept": lc[("code", True)], "true_code_total": lc[("code", True)] + lc[("code", False)],
                          "prose_kept": lc[("not_code", True)], "prose_total": lc[("not_code", True)] + lc[("not_code", False)]}
        out[name] = res
    print(f"\nPHASE C, against the four-reviewer consensus (documents never trained on; stratified estimates)")
    print(f"{'configuration':62s} {'P':>6s} {'R':>6s}   {'low-code: code kept':>20s} {'prose kept':>11s}")
    for name, r in out.items():
        m, l = r["mean_code_bearing"], r["lowcode"]
        print(f"{name:62s} {m['P']:6.3f} {m['R']:6.3f}   {l['true_code_kept']:>9d}/{l['true_code_total']:<9d} {l['prose_kept']:>4d}/{l['prose_total']}")
    return out


if __name__ == "__main__":
    main()
