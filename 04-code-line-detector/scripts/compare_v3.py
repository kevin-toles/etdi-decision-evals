"""Round 3 of the code-line detector comparison on the larger answer key (answer_key_v2.jsonl). No embedding model.
  round  N : first N docs of the v2 key, 5 doc-level splits (40% train / 60% test), every variant from round 2 plus
             (e)+ng, the line classifier with a character n-gram TF-IDF model stacked in as extra line features.
  curve    : fixed held-out test set (25% of the v2 key by hash, plus the original 40-book key reported apart);
             (e) and (e)+ng trained on 40 / 100 / 200 / 400 / all remaining docs, 3 draws per size below all.
Line-model thresholds are tuned on a 20% validation slice of the training docs, then the model is refit on all of them.
    cd Code-Orchestrator-Service && KEY=answer_key_v3.jsonl OLDKEY=answer_key_v3_old40.jsonl python3 <this> round 200 out.json | curve out.json"""
import hashlib, json, math, os, re, sys, random
sys.path.insert(0, os.getcwd())
import numpy as np
from scipy import sparse
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from src.extractors.code_block_extractor import HeuristicCodeDetector

HERE = os.path.dirname(os.path.abspath(__file__))
s1 = open(os.path.join(HERE, "compare_prose_fix.py")).read()
exec(s1[s1.index("class NarrowColonDetector"):s1.index("key = json.load(open(KEY))")])
s2 = open(os.path.join(HERE, "compare_v2.py")).read()
exec(s2[s2.index("KW = set("):s2.rindex("key = json.load(open(KEY))")])      # code_shaped, CodeShapedColonDetector, line_feats, context_matrix, runs

MODE, OUT = sys.argv[1], sys.argv[-1]
KEY = os.environ.get("KEY", "answer_key_v2.jsonl"); OLDKEY = os.environ.get("OLDKEY", "answer_key.json")
HV = HashingVectorizer(analyzer="char_wb", ngram_range=(2, 4), n_features=2 ** 18, alternate_sign=False, lowercase=False)


def load(path, n=None):
    out = []
    for line in open(path):
        out.append(json.loads(line))
        if n and len(out) >= n:
            break
    return out


def prep(docs):
    for bk in docs:
        bk["_t"] = book_text(bk); _, lines, labels = bk["_t"]
        bk["_X"] = context_matrix(lines).astype(np.float32)
        bk["_y"] = np.array([bool(l) for l in labels]); bk["_m"] = np.array([l is not None for l in labels])
        bk["_kind"] = "book" if bk.get("doc_pages", 999) >= 60 else "short"


def ngram_fit(train):
    X = sparse.vstack([HV.transform(b["_t"][1]) for b in train]).tocsr()
    y = np.concatenate([b["_y"] for b in train]); m = np.concatenate([b["_m"] for b in train])
    tf = TfidfTransformer(sublinear_tf=True).fit(X[m])
    lr = LogisticRegression(class_weight="balanced", max_iter=400, C=1.0, solver="liblinear").fit(tf.transform(X[m]), y[m])
    return lambda bk: lr.predict_proba(tf.transform(HV.transform(bk["_t"][1])))[:, 1].astype(np.float32)


def neighbour_cols(p, lines):
    nz = [i for i, l in enumerate(lines) if l.strip()]
    out = np.zeros((len(lines), 5), np.float32); out[:, 0] = p
    for k, i in enumerate(nz):
        for c, d in ((1, -1), (2, 1), (3, -2), (4, 2)):
            if 0 <= k + d < len(nz): out[i, c] = p[nz[k + d]]
    return out


def with_ngram(docs, ng_by_doc):
    return {b["stem"]: np.hstack([b["_X"], neighbour_cols(ng_by_doc[b["stem"]], b["_t"][1])]) for b in docs}


def stacked_features(train, others):
    """Out-of-fold n-gram probabilities for train docs (3 doc folds); a full-train n-gram model for the others."""
    ng = {}
    folds = [[b for i, b in enumerate(train) if i % 3 == k] for k in range(3)]
    for k in range(3):
        f = ngram_fit([b for j, fo in enumerate(folds) if j != k for b in fo])
        for b in folds[k]: ng[b["stem"]] = f(b)
    f = ngram_fit(train)
    for b in others: ng[b["stem"]] = f(b)
    return with_ngram(train + others, ng)


def fit_hgb(docs, X):
    Xs = np.vstack([X[b["stem"]][b["_m"]] for b in docs]); ys = np.concatenate([b["_y"][b["_m"]] for b in docs])
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, class_weight="balanced", random_state=0).fit(Xs, ys)


def predict_runs(bk, p, t, t_run=None):
    lines = bk["_t"][1]; out = []
    for a, b, c in runs([pi >= t and bool(l.strip()) for pi, l in zip(p, lines)], lines):
        idx = [i for i in range(a, b + 1) if lines[i].strip()]
        if t_run is None or (idx and float(np.mean([p[i] for i in idx])) >= t_run):
            out.append((a, b, c))
    return out


def line_model(train, others, use_ngram):
    """Thresholds tuned on a 20% validation slice of train, then refit on all train. Returns {stem: probs} for others."""
    val = [b for b in train if int(hashlib.sha256(b["stem"].encode()).hexdigest(), 16) % 5 == 0]
    fit = [b for b in train if b not in val]
    def feats(tr, ot):
        return stacked_features(tr, ot) if use_ngram else {b["stem"]: b["_X"] for b in tr + ot}
    Xv = feats(fit, val); clf = fit_hgb(fit, Xv)
    pv = {b["stem"]: clf.predict_proba(Xv[b["stem"]])[:, 1] for b in val}
    t = max((score(val, {b["stem"]: predict_runs(b, pv[b["stem"]], t) for b in val})["f1"], t) for t in np.arange(0.1, 0.91, 0.05))[1]
    def obj(tr):
        s = score(val, {b["stem"]: predict_runs(b, pv[b["stem"]], t, tr) for b in val}); return s["f1"] - 0.5 * s["prose_only_share"]
    t_run = max((obj(tr), tr) for tr in np.arange(0.3, 0.96, 0.05))[1]
    Xa = feats(train, others); clf = fit_hgb(train, Xa)
    return {b["stem"]: clf.predict_proba(Xa[b["stem"]])[:, 1] for b in others}, float(t), float(t_run)


def evaluate_line(test, probs, t, t_run):
    return ({b["stem"]: predict_runs(b, probs[b["stem"]], t) for b in test},
            {b["stem"]: predict_runs(b, probs[b["stem"]], t, t_run) for b in test})


def by_kind(test, acc):
    out = {"all": score(test, acc)}
    for k in ("book", "short"):
        sub = [b for b in test if b["_kind"] == k]
        if sub: out[k] = score(sub, acc)
    return out


def summarise(results):
    summary = {}
    for k, rs in results.items():
        summary[k] = {}
        for kind in ("all", "book", "short"):
            rk = [r[kind] for r in rs if kind in r]
            if rk:
                summary[k][kind] = {m: (round(float(np.mean([r[m] for r in rk])), 3), round(float(np.std([r[m] for r in rk])), 3))
                                    for m in ("precision", "recall", "f1", "prose_only_share", "leadin_share")}
    return summary


def show(summary, kinds=("all", "book", "short")):
    for kind in kinds:
        print(f"\n[{kind}]\n{'variant':34s} {'precision':>14s} {'recall':>14s} {'F1':>14s} {'prose-only':>14s} {'lead-ins':>14s}")
        for k, s in summary.items():
            if kind in s:
                print(f"{k:34s} " + " ".join(f"{s[kind][m][0]:.3f} ±{s[kind][m][1]:.3f}".rjust(14) for m in ("precision", "recall", "f1", "prose_only_share", "leadin_share")))


if MODE == "round":
    docs = load(os.path.join(HERE, KEY), int(sys.argv[2])); prep(docs)
    dets = {"base": HeuristicCodeDetector(), "a": NarrowColonDetector(), "a2": CodeShapedColonDetector()}
    cands = {k: {b["stem"]: spans(b["_t"][0], b["_t"][1], d.detect_candidates(b["_t"][0])) for b in docs} for k, d in dets.items()}

    def fit_block_lr(train, source):
        X, y = [], []
        for bk in train:
            labels = bk["_t"][2]
            for a, b, c in cands[source][bk["stem"]]:
                labs = [labels[i] for i in range(a, b + 1) if labels[i] is not None]
                if labs:
                    X.append(features(c.content, c.confidence, c.detection_signals)); y.append(sum(labs) / len(labs) >= 0.5)
        sc = StandardScaler().fit(X); lr = LogisticRegression(class_weight="balanced", max_iter=3000).fit(sc.transform(X), y)
        def accept(bk, t):
            cs = cands[source][bk["stem"]]
            if not cs: return []
            p = lr.predict_proba(sc.transform([features(c.content, c.confidence, c.detection_signals) for _, _, c in cs]))[:, 1]
            return [x for x, pi in zip(cs, p) if pi >= t]
        t = max((score(train, {b["stem"]: accept(b, t) for b in train})["f1"], t) for t in np.arange(0.05, 0.96, 0.05))[1]
        return accept, float(t)

    results = {}
    for seed in range(5):
        split = lambda s: int(hashlib.sha256(f"{seed}:{s}".encode()).hexdigest(), 16) % 5 < 2
        train = [b for b in docs if split(b["stem"])]; test = [b for b in docs if not split(b["stem"])]
        acc_ac, t_ac = fit_block_lr(train, "a"); acc_a2c, t_a2c = fit_block_lr(train, "a2")
        v = {"baseline": {b["stem"]: cands["base"][b["stem"]] for b in test},
             "(a)": {b["stem"]: cands["a"][b["stem"]] for b in test},
             "(a)+(c)": {b["stem"]: acc_ac(b, t_ac) for b in test},
             "(a2)+(c)": {b["stem"]: acc_a2c(b, t_a2c) for b in test}}
        for name, ng in (("(e)", False), ("(e)+ng", True)):
            probs, t, tr = line_model(train, test, ng)
            v[name], v[name + "+run filter"] = evaluate_line(test, probs, t, tr)
        for k, acc in v.items():
            results.setdefault(k, []).append(by_kind(test, acc))
        print(f"split {seed}: train {len(train)} test {len(test)}", flush=True)
    summary = summarise(results)
    json.dump({"docs": len(docs), "splits": 5, "summary": summary}, open(OUT, "w"), indent=1)
    show(summary)

elif MODE == "curve":
    docs = load(os.path.join(HERE, KEY))
    old = load(os.path.join(HERE, OLDKEY)) if OLDKEY.endswith(".jsonl") else json.load(open(os.path.join(HERE, OLDKEY)))["books"]
    prep(docs); prep(old)
    for b in old: b["_kind"] = "book"
    held = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4 == 0
    test = [b for b in docs if held(b["stem"])]; pool = [b for b in docs if not held(b["stem"])]
    sizes = [n for n in (40, 100, 200, 400) if n < len(pool)] + [len(pool)]
    results = {}
    for n in sizes:
        for draw in range(3 if n < len(pool) else 1):
            train = random.Random(f"{n}:{draw}").sample(pool, n)
            for name, ng in (("(e)", False), ("(e)+ng", True)):
                probs, t, tr = line_model(train, test + old, ng)
                a, af = evaluate_line(test, probs, t, tr); ao, aof = evaluate_line(old, probs, t, tr)
                for label, acc, ev in ((f"{name} n={n}", a, test), (f"{name}+run n={n}", af, test)):
                    results.setdefault(label, []).append(by_kind(ev, acc))
                for label, acc in ((f"{name} n={n} [40-book key]", ao), (f"{name}+run n={n} [40-book key]", aof)):
                    results.setdefault(label, []).append({"all": score(old, acc)})
            print(f"n={n} draw {draw} done", flush=True)
    summary = summarise(results)
    json.dump({"test_docs": len(test), "pool": len(pool), "summary": summary}, open(OUT, "w"), indent=1)
    show(summary)
