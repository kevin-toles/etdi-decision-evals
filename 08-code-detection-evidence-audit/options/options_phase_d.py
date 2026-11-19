"""Phase D: lessons from the open-source review, plus two published challengers, on the same scorer as phase A/C.
Every threshold is chosen on the tune halves; corpus-weighted figures are on the test halves; the consensus figures are
on the 626 consensus documents (line models never trained on them).
  Sources (line probabilities)
    hgb       the v5+extra (e)+ng line model with the consensus documents held out (hgb_holdout_probs.pkl)
    distil    LemiSt/code-segmentor-distilbert zero-shot (encoder_probs_distilbert.pkl)
    blend     50/50 hgb + distil
    +S0       hgb restacked: a second-stage line model on the hgb probabilities of the line and its neighbours (control)
    +KR       +S0 plus kind recognisers (shell/REPL prompts, logs, stack traces, compiler messages, listings, diffs,
              config/kv lines, aligned output columns, pseudocode keywords, distance from the last prompt)
  Block post-processing
    ER        edge repair: merge runs split by <= 2 lines, extend by adjacent likely lines, closing brackets and
              unbalanced openers (brace matching), trim caption/prose edge lines
    TS-ER     edge repair by parse: each block's best strict grammar (the structural analyzer's languages plus SQL/JSON),
              then the trim/extend variant with the lowest error-line share in that grammar
  Document gate
    G         phase A's gate (prediction statistics)
    G+FT      G plus fastText code/natural-language scores of the document's candidate runs and pages
              (kenhktsui/code-natural-language-fasttext-classifier, quantized)
    cd Code-Orchestrator-Service && PYTHONPATH=<tspkgs> python3 <this>"""
import collections, hashlib, json, os, pickle, re, sys, time
S = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(S, "options_phase_a.py")).read().split("\nif __name__")[0], globals())   # consensus, pool_sizes, E_DIR, RUN_KEYS
sys.argv = ["x", os.path.join(S, "census_v5.json"), os.path.join(S, "report_segments_v5_extra.json")]
os.environ["TRAIN_EXTRA"] = "train_v5_lowcode.jsonl,train_v5_codefree.jsonl"
_src = open(os.path.join(S, "eval_segments_v5.py")).read()
exec(_src[:_src.index("TS = np.round")], globals())
from sklearn.ensemble import HistGradientBoostingClassifier
T0 = time.time()
def log(*a): print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)

GOLD = json.load(open(os.path.join(S, "gold_docs.json")))
for st, d in GOLD.items():
    d["_t"] = book_text(d)
DOCS = {b["stem"]: b for b in alldocs}
for st, d in GOLD.items():
    DOCS.setdefault(st, d)
gold_stems = set(GOLD)

# ---------------------------------------------------------------- sources
SRC = {"hgb": pickle.load(open(os.path.join(S, "hgb_holdout_probs.pkl"), "rb"))}
if os.path.exists(os.path.join(S, "encoder_probs_distilbert.pkl")):
    SRC["distil"] = pickle.load(open(os.path.join(S, "encoder_probs_distilbert.pkl"), "rb"))
    SRC["blend hgb+distil"] = {k: 0.5 * SRC["hgb"][k] + 0.5 * SRC["distil"][k] for k in SRC["hgb"] if k in SRC["distil"]}

# ---------------------------------------------------------------- kind recognisers
KIND = [("prompt", re.compile(r"^\s*(\$|#|%|>>>|\.\.\.|>|In \[\d+\]:|Out\[\d+\]:|PS [A-Za-z]:\\[^>]*>|[A-Za-z]:\\[^>]*>|[\w.-]+@[\w.-]+[^$#]*[$#]|mysql>|postgres=?[#>]|sqlite>|irb\(\w+\)|scala>|ghci>|>>)\s")),
        ("log", re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}|\b\d{2}:\d{2}:\d{2}([.,]\d+)?\b|\b(INFO|WARN|WARNING|ERROR|DEBUG|TRACE|FATAL|SEVERE)\b|^\s*\[[^\]]{2,40}\]")),
        ("trace", re.compile(r"^\s*at [\w.$<>]+\(.*\)|Traceback \(most recent call last\)|^\s*File \".*\", line \d+|^\s*\w+(\.\w+)*(Error|Exception)(:|$)|^\s*Caused by:")),
        ("compiler", re.compile(r"^[\w./\\-]+:\d+(:\d+)?:\s*(error|warning|note|fatal)\b|^\s*(error|warning)(\[\w+\])?:")),
        ("listing", re.compile(r"^[dlcbps-][rwxsStT-]{9}[.+@]?\s|^total \d+\s*$")),
        ("diff", re.compile(r"^(\+\+\+ |--- |@@ .* @@|[+-][^+\-\s])")),
        ("kv", re.compile(r"^\s*[\w.\-\[\]\"']+\s*[:=]\s*\S")),
        ("columns", re.compile(r"\S {2,}\S+ {2,}\S")),
        ("pseudo", re.compile(r"^\s*(if|for|while|repeat|until|return|procedure|function|begin|end|else|then|do)\b")),
        ("closer", re.compile(r"^\s*[}\])]+[;,]?\s*$")),
        ("caption", re.compile(r"^\s*(Listing|Example|Figure|Fig\.|Table|Output|Code|Program)\s*[\dA-Z]+([.\-:]\d+)*[.:]?\s"))]
NK = len(KIND)
_kcache = {}
def kinds(st):
    if st not in _kcache:
        lines = DOCS[st]["_t"][1]
        _kcache[st] = np.array([[bool(r.search(l)) for _, r in KIND] for l in lines], bool).reshape(len(lines), NK)
    return _kcache[st]


def stack_feats(st, p, with_kind):
    lines = DOCS[st]["_t"][1]; n = len(lines)
    blank = np.array([not l.strip() for l in lines]); nz = np.where(~blank)[0]
    # neighbour features over non-blank lines (blank lines carry no evidence)
    pos = -np.ones(n, int); pos[nz] = np.arange(len(nz)); q = p[nz]
    def sh(k):
        out = np.zeros(len(nz));
        if k > 0: out[k:] = q[:-k] if len(q) > k else 0
        elif k < 0: out[:k] = q[-k:] if len(q) > -k else 0
        else: out = q.copy()
        return out
    cols = [sh(k) for k in (-3, -2, -1, 0, 1, 2, 3)]
    win = np.array([q[max(0, i - 5):i + 6].mean() for i in range(len(q))]) if len(q) else np.zeros(0)
    ln = np.array([len(lines[i]) for i in nz]); ind = np.array([len(lines[i]) - len(lines[i].lstrip()) for i in nz])
    gap_before = np.array([(i - nz[j - 1]) if j else 0 for j, i in enumerate(nz)])
    F = [*cols, win, ln, ind, gap_before]
    if with_kind:
        K = kinds(st)[nz].astype(float)
        Kn = np.zeros_like(K)
        for k in (-2, -1, 1, 2):
            sl = np.roll(K, k, axis=0)
            if k > 0: sl[:k] = 0
            else: sl[k:] = 0
            Kn = np.maximum(Kn, sl)
        last = -10 ** 6; dist = np.zeros(len(nz))
        for j in range(len(nz)):
            if K[j, 0]: last = j
            dist[j] = min(j - last, 50)
        F += [K[:, i] for i in range(NK)] + [Kn[:, i] for i in range(NK)] + [dist]
    return nz, np.column_stack(F) if len(nz) else np.zeros((0, len(F)))


def restack(base, with_kind, name):
    """Second-stage line model on tune-half documents (consensus documents excluded), 2-fold cross-fitted on the tune
    half so thresholds chosen there see out-of-fold probabilities; test and consensus documents use the full model."""
    tune = [st for st, b in DOCS.items() if st not in gold_stems and st in LAB and half(st) == 0 and st in base]
    fold2 = {st: int(hashlib.sha256(f"stk:{st}".encode()).hexdigest(), 16) % 2 for st in tune}
    data = {}
    for st in DOCS:
        if st in base: data[st] = stack_feats(st, base[st], with_kind)
    def xy(sts):
        X, y = [], []
        for st in sts:
            nz, F = data[st]; code, prose = LAB[st]; m = code[nz] | prose[nz]
            X.append(F[m]); y.append(code[nz][m])
        return np.vstack(X), np.concatenate(y)
    out = {}
    def fit(sts):
        X, y = xy(sts); return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, random_state=0).fit(X, y)
    for k in (0, 1):
        m = fit([st for st in tune if fold2[st] != k])
        for st in tune:
            if fold2[st] == k:
                nz, F = data[st]; p = np.zeros(len(base[st]), np.float32); p[nz] = m.predict_proba(F)[:, 1] if len(nz) else 0; out[st] = p
    m = fit(tune)
    for st in data:
        if st not in out:
            nz, F = data[st]; p = np.zeros(len(base[st]), np.float32)
            if len(nz): p[nz] = m.predict_proba(F)[:, 1]
            out[st] = p
    log(f"restacked {name}: {len(tune)} tune docs")
    return out


SRC["hgb+S0"] = restack(SRC["hgb"], False, "hgb+S0")
SRC["hgb+KR"] = restack(SRC["hgb"], True, "hgb+KR")
if "blend hgb+distil" in SRC:
    SRC["blend+KR"] = restack(SRC["blend hgb+distil"], True, "blend+KR")


# ---------------------------------------------------------------- runs and scoring
_rc = {}
def runs(src, st, t):
    key = (src, st, round(t, 3))
    if key not in _rc:
        lines, p = DOCS[st]["_t"][1], SRC[src][st]
        blank = np.array([not l.strip() for l in lines]); on = (p >= t) & ~blank
        out = []; i = 0; n = len(lines)
        while i < n:
            if on[i]:
                j = i
                while j + 1 < n and (on[j + 1] or (blank[j + 1] and j + 2 < n and on[j + 2])):
                    j += 1
                idx = np.array([k for k in range(i, j + 1) if not blank[k]])
                out.append((idx, float(p[idx].mean()))); i = j + 1
            else:
                i += 1
        _rc[key] = out
    return _rc[key]


def score(part, keep):
    W = np.zeros(5); per = {}
    for s, docs in segs.items():
        docs = [b for b in docs if half(b["stem"]) == part]
        if not docs: continue
        acc = np.zeros(5)
        for b in docs:
            code, prose = LAB[b["stem"]]; pred = np.zeros(len(code), bool); blocks = bad = 0
            for idx in keep(b["stem"]):
                pred[idx] = True; nc, npr = code[idx].sum(), prose[idx].sum()
                if nc + npr: blocks += 1; bad += nc == 0
            acc += [(pred & code).sum(), (pred & prose).sum(), (~pred & code).sum(), blocks, bad]
        tp, fp, fn, bl, bd = acc; p = tp / max(1, tp + fp); r = tp / max(1, tp + fn)
        per[s] = {"P": round(p, 3), "R": round(r, 3), "bad": round(bd / max(1, bl), 3)}
        if s in share: W += share[s] * acc / len(docs)
    p = W[0] / max(1e-9, W[0] + W[1]); r = W[0] / max(1e-9, W[0] + W[2])
    return {"P": round(p, 3), "R": round(r, 3), "F1": round(2 * p * r / max(1e-9, p + r), 3), "bad": round(W[4] / max(1e-9, W[3]), 3)}, per


# consensus scorer (phase C's method)
FLAT = {}
for st, d in GOLD.items():
    m, j = [], 0
    for k, pg in enumerate(d["pages"]):
        if k: j += 1
        for _ in pg["lines"]:
            m.append(j); j += 1
    FLAT[st] = m
CONS = {r: consensus(r) for r in list(RUN_KEYS) + ["run_2026-10-28c_lowcode"]}
POOLS = {r: pool_sizes(r) for r in RUN_KEYS}


def gold_score(keep):
    pred = {}
    for st, d in GOLD.items():
        v = np.zeros(len(d["_t"][1]), bool)
        for idx in keep(st): v[idx] = True
        pred[st] = v
    Ps, Rs = [], []
    for r in RUN_KEYS:
        n = collections.Counter(); hits = collections.Counter()
        for it in CONS[r].values():
            s_ = (it["kind"], it["font_label"]); n[s_] += 1
            hits[(s_, bool(pred[it["stem"]][FLAT[it["stem"]][it["line_index"]]]), it["consensus"] == "code")] += 1
        tp = fp = fn = 0.0
        for s_ in n:
            w = POOLS[r].get(s_, 0) / n[s_]
            tp += w * hits[(s_, True, True)]; fp += w * hits[(s_, True, False)]; fn += w * hits[(s_, False, True)]
        Ps.append(tp / max(1e-9, tp + fp)); Rs.append(tp / max(1e-9, tp + fn))
    lc = collections.Counter()
    for it in CONS["run_2026-10-28c_lowcode"].values():
        lc[(it["consensus"], bool(pred[it["stem"]][FLAT[it["stem"]][it["line_index"]]]))] += 1
    return {"P": round(float(np.mean(Ps)), 3), "R": round(float(np.mean(Rs)), 3),
            "lowcode_code_kept": f"{lc[('code', True)]}/{lc[('code', True)] + lc[('code', False)]}",
            "lowcode_prose_kept": f"{lc[('not_code', True)]}/{lc[('not_code', True)] + lc[('not_code', False)]}"}


# ---------------------------------------------------------------- document gates
_ft = None
def ft_model():
    global _ft
    if _ft is None:
        import fasttext
        from huggingface_hub import hf_hub_download
        _ft = fasttext.load_model(hf_hub_download("kenhktsui/code-natural-language-fasttext-classifier", "model_quantized.bin", local_files_only=True))
    return _ft


def ft_code_prob(texts):
    if not texts: return np.zeros(0)
    labs, ps = ft_model().predict([re.sub(r"\s+", " ", t)[:4000] for t in texts], k=2)
    return np.array([dict(zip(l, p)).get("__label__Code", 0.0) for l, p in zip(labs, ps)])


def doc_feats(src, st, with_ft):
    p = SRC[src][st]; lines = DOCS[st]["_t"][1]; nzm = np.array([bool(l.strip()) for l in lines]); q = p[nzm] if nzm.any() else p
    rs = runs(src, st, 0.8); lens = [len(i) for i, _ in rs]; ms = [m for _, m in rs]
    top = np.sort(q)[-20:] if len(q) else np.zeros(1)
    f = [len(q), (q > 0.5).mean() if len(q) else 0, (q > 0.8).mean() if len(q) else 0, (q > 0.95).mean() if len(q) else 0,
         float(top.mean()), float(q.max()) if len(q) else 0, len(rs), max(lens, default=0), float(np.mean(lens)) if lens else 0,
         max(ms, default=0), sum(m >= 0.94 for m in ms), sum(l >= 5 for l in lens), DOCS[st].get("doc_pages", 0)]
    if with_ft:
        rp = ft_code_prob(["\n".join(lines[i] for i in idx) for idx, _ in rs])
        pages = [" ".join(l for l, _ in pg["lines"]) for pg in DOCS[st]["pages"]]
        pp = ft_code_prob([t for t in pages if t.strip()])
        w = np.array(lens, float)
        f += [float((rp >= 0.5).sum()), float((rp >= 0.5).mean()) if len(rp) else 0, float(rp.mean()) if len(rp) else 0,
              float((rp * w).sum() / w.sum()) if len(rp) else 0, float(rp.max()) if len(rp) else 0,
              float((pp >= 0.5).mean()) if len(pp) else 0, float(pp.mean()) if len(pp) else 0, float(np.sort(pp)[-3:].mean()) if len(pp) else 0]
    return f


def make_gate(src, with_ft):
    all_st = list(LAB)                                           # segment documents
    F = {st: doc_feats(src, st, with_ft) for st in all_st}
    for st in GOLD:
        if st not in F: F[st] = doc_feats(src, st, with_ft)
    has = {st: int(LAB[st][0].sum() >= 5) for st in all_st}
    tune = [st for st in all_st if half(st) == 0]; test = [st for st in all_st if half(st) == 1]
    Xt = np.array([F[st] for st in tune]); yt = np.array([has[st] for st in tune])
    fold = np.array([int(hashlib.sha256(st.encode()).hexdigest(), 16) % 3 for st in tune]); oof = np.zeros(len(tune))
    for k in range(3):
        g = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, random_state=0).fit(Xt[fold != k], yt[fold != k])
        oof[fold == k] = g.predict_proba(Xt[fold == k])[:, 1]
    clf = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, random_state=0).fit(Xt, yt)
    gs = dict(zip(tune, oof))
    rest = [st for st in F if st not in gs]
    gs.update(zip(rest, clf.predict_proba(np.array([F[st] for st in rest]))[:, 1]))
    gt = np.array([has[st] for st in test]); gp = np.array([gs[st] >= 0.5 for st in test])
    q = {"precision@.5": round(float((gp & (gt == 1)).sum() / max(1, gp.sum())), 3), "recall@.5": round(float((gp & (gt == 1)).sum() / max(1, gt.sum())), 3)}
    log(f"gate {src} ft={with_ft}: {q}")
    return gs, q


# ---------------------------------------------------------------- edge repair
CLOSER = re.compile(r"^\s*[}\])]+[;,]?\s*$")
CAPTION = KIND[-1][1]
PROSE = re.compile(r"^[A-Z][^{}();=<>\[\]_$#@|\\]{40,}[.?!:]$")


def balance(text):
    t = re.sub(r"\"(\\.|[^\"\\])*\"|'(\\.|[^'\\])*'", "", text)
    return sum(t.count(c) for c in "({[") - sum(t.count(c) for c in ")}]")


def edge_repair(st, src, blocks, ext_t, merge_t):
    lines, p = DOCS[st]["_t"][1], SRC[src][st]; n = len(lines)
    nb = lambda i: bool(lines[i].strip())
    bl = [list(map(int, idx)) for idx in blocks]
    if not bl: return []
    bl.sort(key=lambda x: x[0]); merged = [bl[0]]
    for b in bl[1:]:                                             # merge across short gaps of likely lines
        gap = [i for i in range(merged[-1][-1] + 1, b[0]) if nb(i)]
        if len(gap) <= 2 and all(p[i] >= merge_t for i in gap):
            merged[-1] = merged[-1] + gap + b
        else:
            merged.append(b)
    out = []
    for b in merged:
        a, e = b[0], b[-1]
        for _ in range(3):                                       # extend upward / downward by likely lines
            j = a - 1
            while j >= 0 and not nb(j): j -= 1
            if j >= 0 and (p[j] >= ext_t) and not CAPTION.search(lines[j]) and not PROSE.match(lines[j].strip()): a = j
            else: break
        for _ in range(3):
            j = e + 1
            while j < n and not nb(j): j += 1
            if j < n and (p[j] >= ext_t or CLOSER.match(lines[j])) and not PROSE.match(lines[j].strip()): e = j
            else: break
        bal = balance("\n".join(lines[a:e + 1])); k = 0           # brace matching: close unbalanced openers
        while bal > 0 and k < 8:
            j = e + 1
            while j < n and not nb(j): j += 1
            if j >= n or PROSE.match(lines[j].strip()) or p[j] < 0.1: break
            e = j; bal += balance(lines[j]); k += 1
        idx = [i for i in range(a, e + 1) if nb(i)]
        while idx and (CAPTION.search(lines[idx[0]]) or (PROSE.match(lines[idx[0]].strip()) and p[idx[0]] < 0.9)): idx = idx[1:]
        while idx and (CAPTION.search(lines[idx[-1]]) or (PROSE.match(lines[idx[-1]].strip()) and p[idx[-1]] < 0.9)): idx = idx[:-1]
        if idx: out.append(np.array(idx))
    return out


_TSP = None
STRICT = ["python", "java", "c", "cpp", "csharp", "go", "rust", "javascript", "typescript", "kotlin", "swift", "ruby", "scala", "sql", "json"]
def ts_parsers():
    global _TSP
    if _TSP is None:
        from tree_sitter_language_pack import get_parser
        _TSP = {g: get_parser(g) for g in STRICT}
    return _TSP


def err_share(parser, lines):
    code = "\n".join(lines); nzl = {i for i, l in enumerate(lines) if l.strip()} or {0}
    t = parser.parse(code.encode("utf8")); bad = set(); stck = [t.root_node]
    while stck:
        nd = stck.pop()
        if nd.is_error or nd.is_missing: bad.update(range(nd.start_point[0], nd.end_point[0] + 1))
        elif nd.has_error: stck.extend(nd.children)
    return len(bad & nzl) / len(nzl)


_tsr = {}
def ts_repair(st, src, blocks, low):
    lines, p = DOCS[st]["_t"][1], SRC[src][st]; n = len(lines); P = ts_parsers(); out = []
    nzi = [i for i in range(n) if lines[i].strip()]; pos = {i: k for k, i in enumerate(nzi)}
    for idx in blocks:
        key = (st, src, int(idx[0]), int(idx[-1]), low)
        if key not in _tsr:
            base = [lines[i] for i in idx]
            g, e0 = min(((g, err_share(P[g], base)) for g in P), key=lambda x: x[1])
            best, be = list(map(int, idx)), e0
            if e0 > 0:
                k0, k1 = pos[int(idx[0])], pos[int(idx[-1])]
                for top in (-2, -1, 0, 1, 2):                    # negative = extend upward, positive = trim
                    for bot in (-2, -1, 0, 1, 2):
                        a, b = k0 + top, k1 - bot
                        if a < 0 or b >= len(nzi) or b - a < 1 or (top == 0 and bot == 0): continue
                        cand = nzi[a:b + 1]
                        if any(p[i] < low for i in cand if i < int(idx[0]) or i > int(idx[-1])): continue
                        e = err_share(P[g], [lines[i] for i in cand])
                        if e < be - 0.05: best, be = cand, e
            _tsr[key] = np.array(best)
        out.append(_tsr[key])
    return out


# ---------------------------------------------------------------- configurations
TS_ = [round(x, 2) for x in np.arange(0.5, 0.981, 0.04)]
TR_ = [None, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98]
HS = (0.2, 0.35, 0.5, 0.65, 0.8)
RK = lambda x: (x[0],) + tuple(-1 if v is None else v for v in (x[1] or ()))   # max() tie-break as tuple order, None lowest


def sel(src, t, tr, gate=None, h=None, post=None):
    def keep(st):
        if gate is not None and gate.get(st, 0) < h: return []
        bl = [idx for idx, m in runs(src, st, t) if tr is None or m >= tr]
        return post(st, bl) if post else bl
    return keep


rows = {}
def add(name, keep):
    w, per = score(1, keep); g = gold_score(keep); rows[name] = {"weighted": w, "segments": per, "consensus": g}
    log(f"{name:70s} test P {w['P']:.3f} R {w['R']:.3f} F1 {w['F1']:.3f} bad {w['bad']:.1%} | consensus P {g['P']:.3f} R {g['R']:.3f} | lowcode {g['lowcode_code_kept']} code, {g['lowcode_prose_kept']} prose")


def choose(src, gate=None, post=None):
    """Operating points on the tune half: best F1 (no gate), G+O1 bad<=15% (balanced) and O1 bad<=10% (strict),
    with and without the gate."""
    grid = {(t, tr): score(0, sel(src, t, tr))[0] for t in TS_ for tr in TR_}
    pts = {"best-F1": max(grid, key=lambda k: grid[k]["F1"])}
    for tgt, nm in ((0.15, "O1<=15%"), (0.10, "O1<=10%")):
        ok = [(v["R"], k) for k, v in grid.items() if v["bad"] <= tgt]
        if ok: pts[nm] = max(ok, key=RK)[1]
    out = {f"{k} (t {v[0]}, run {v[1]})": sel(src, v[0], v[1], post=post) for k, v in pts.items()}
    if gate is not None:
        gg = {}
        for (t, tr), v in list(grid.items())[::2]:
            for h in HS:
                gg[(t, tr, h)] = score(0, sel(src, t, tr, gate, h))[0]
        for tgt, nm in ((0.15, "G+O1<=15%"), (0.10, "G+O1<=10%")):
            ok = [(v["R"], k) for k, v in gg.items() if v["bad"] <= tgt]
            if ok:
                t, tr, h = max(ok, key=RK)[1]; out[f"{nm} (t {t}, run {tr}, gate {h})"] = sel(src, t, tr, gate, h, post=post)
        out["_points"] = {"grid": pts, "gate": {nm: max([(v["R"], k) for k, v in gg.items() if v["bad"] <= tgt] or [(0, None)], key=RK)[1] for tgt, nm in ((0.15, "G+O1<=15%"), (0.10, "G+O1<=10%"))}}
    return out


def main():
    det = HeuristicCodeDetector(); today = {}
    for st, b in DOCS.items():
        today[st] = [np.arange(a, e + 1) for a, e, _ in spans(b["_t"][0], b["_t"][1], det.detect_candidates(b["_t"][0]))]
    add("today: HeuristicCodeDetector", lambda st: today.get(st, []))
    gates = {}
    for src in [s for s in ("hgb", "distil", "blend hgb+distil", "hgb+S0", "hgb+KR", "blend+KR") if s in SRC]:
        gates[src], _ = make_gate(src, False)
        ch = choose(src, gates[src]); ch.pop("_points", None)
        for k, keep in ch.items(): add(f"{src}: {k}", keep)
    # lessons 2 and 3 on the hgb source and on the best restacked source
    for src in [s for s in ("hgb", "hgb+KR", "blend+KR") if s in SRC]:
        g_ft, q = make_gate(src, True)
        ch = choose(src, g_ft); pts = ch.pop("_points")
        for k, keep in ch.items():
            if k.startswith("G+"): add(f"{src}: G+FT {k}", keep)
        # edge repair: parameters on the tune half at the source's own balanced and strict points
        for nm, key in (("G+O1<=15%", pts["gate"]["G+O1<=15%"]), ("G+O1<=10%", pts["gate"]["G+O1<=10%"])):
            if key is None: continue
            t, tr, h = key
            best = max(((et, mt) for et in (0.2, 0.35, 0.5) for mt in (0.2, 0.35, 0.5)),
                       key=lambda x: score(0, sel(src, t, tr, g_ft, h, post=lambda st, bl, x=x: edge_repair(st, src, bl, *x)))[0]["F1"])
            add(f"{src}: G+FT {nm} + ER (ext {best[0]}, merge {best[1]})", sel(src, t, tr, g_ft, h, post=lambda st, bl: edge_repair(st, src, bl, *best)))
            low = max((0.1, 0.3, 0.5), key=lambda lo: score(0, sel(src, t, tr, g_ft, h, post=lambda st, bl, lo=lo: ts_repair(st, src, bl, lo)))[0]["F1"])
            add(f"{src}: G+FT {nm} + TS-ER (low {low})", sel(src, t, tr, g_ft, h, post=lambda st, bl: ts_repair(st, src, bl, low)))
    json.dump(rows, open(os.path.join(S, "options_phase_d.json"), "w"), indent=1, default=float)
    log("done")


if __name__ == "__main__":
    main()
