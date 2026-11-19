"""Improvement round for the prose fix, graded against the PDF-font answer key over five book-level splits.
Variants: baseline, (a), (a2) code-shaped colon headers, (a)+(c), (a2)+(c), (a2)+(c)+trim, (e) line classifier over
every line with neighbour context. No embedding model is loaded.
    cd Code-Orchestrator-Service && python3 <this> answer_key.json report_v2.json"""
import hashlib, json, math, os, re, sys
sys.path.insert(0, os.getcwd())
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from src.extractors.code_block_extractor import HeuristicCodeDetector

KEY, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "compare_prose_fix.py")).read()
exec(src[src.index("class NarrowColonDetector"):src.index("key = json.load(open(KEY))")])   # NarrowColonDetector, features, book_text, spans, score

KW = set("def return func fn let var const public private protected static void int char float double class struct import "
         "include package using namespace echo fi then elif done esac select insert update delete where from print printf "
         "puts my sub foreach while for if else switch case break continue try catch except finally raise throw new "
         "lambda yield async await interface enum impl mut pub use mod go chan defer type val object extends implements "
         "function end begin local export alias sudo apt cd ls grep cat mkdir docker kubectl git npm pip".split())
STOPW = set("the a an of to in and or is are was were be been for on with as by that this it its from at which can will "
            "we you they not but if then than so such these those there their our your into also may each when what".split())


def code_shaped(line):
    """A colon line that is itself code: starts with a keyword or identifier call, few prose words."""
    s = line.strip()
    words = re.findall(r"[A-Za-z]+", s.lower())
    if not words:
        return False
    stop = sum(w in STOPW for w in words) / len(words)
    return (words[0] in KW or bool(re.match(r"^[\w.]+\s*\(.*\)\s*:?$", s))) and stop < 0.3 and len(words) <= 12


class CodeShapedColonDetector(NarrowColonDetector):
    """(a2): a colon line is code when it opens an indented body or is itself code-shaped."""

    def detect_candidates(self, text):
        lines = text.split("\n")
        self._prose_colon = set()
        for i, line in enumerate(lines):
            if line.rstrip().endswith(":"):
                nxt = next((l for l in lines[i + 1:i + 6] if l.strip()), None)
                opens = nxt is not None and self._get_indent_level(nxt) > self._get_indent_level(line)
                if not opens and not code_shaped(line):
                    self._prose_colon.add(line)
        return HeuristicCodeDetector.detect_candidates(self, text)


def line_feats(line):
    s = line.strip(); n = len(s)
    if not s:
        return [0.0] * 16
    words = re.findall(r"[A-Za-z_]+", s); lw = [w.lower() for w in words]
    sym = sum(ch in "{}()[];=<>+-*/&|!#$@%^~\\\"'`:,." for ch in s) / n
    return [np.log1p(n), float(line[:1] in " \t"), sym, sum(w in STOPW for w in lw) / max(1, len(lw)),
            sum(w in KW for w in lw) / max(1, len(lw)), float(s[-1:] in ";{})"), float(s[-1:] == ":"), float(s[-1:] == "."),
            float(s[:1].isupper()), float(s[:1].islower()), float(not s[:1].isalnum()),
            float(bool(re.search(r"\w\(", s))), float(bool(re.search(r"[a-z][A-Z]|\w_\w", s))),
            sum(ch.isdigit() for ch in s) / n, len(words) / max(1, n / 5), float(bool(re.search(r"(->|=>|::|:=|\$\w|<\w+>)", s)))]


def context_matrix(lines):
    base = np.array([line_feats(l) for l in lines])
    nz = [i for i, l in enumerate(lines) if l.strip()]
    prev = np.zeros_like(base); nxt = np.zeros_like(base); prev2 = np.zeros_like(base); nxt2 = np.zeros_like(base)
    for k, i in enumerate(nz):
        if k > 0: prev[i] = base[nz[k - 1]]
        if k > 1: prev2[i] = base[nz[k - 2]]
        if k + 1 < len(nz): nxt[i] = base[nz[k + 1]]
        if k + 2 < len(nz): nxt2[i] = base[nz[k + 2]]
    return np.hstack([base, prev, nxt, prev2, nxt2])


def runs(pred, lines):
    """Contiguous predicted lines (a single blank line may sit inside) → (start, end) spans."""
    out, i = [], 0
    while i < len(pred):
        if pred[i]:
            j = i
            while j + 1 < len(pred) and (pred[j + 1] or (not lines[j + 1].strip() and j + 2 < len(pred) and pred[j + 2])):
                j += 1
            out.append((i, j, None)); i = j + 1
        else:
            i += 1
    return out


key = json.load(open(KEY)); books = key["books"]
for bk in books:
    bk["_t"] = book_text(bk)
    _, lines, _ = bk["_t"]; bk["_X"] = context_matrix(lines)
dets = {"base": HeuristicCodeDetector(), "a": NarrowColonDetector(), "a2": CodeShapedColonDetector()}
cands = {k: {} for k in dets}
for bk in books:
    text, lines, _ = bk["_t"]
    for k, d in dets.items():
        cands[k][bk["stem"]] = spans(text, lines, d.detect_candidates(text))


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


def fit_line_model(train):
    X = np.vstack([b["_X"] for b in train]); y = np.array([bool(l) for b in train for l in b["_t"][2]])
    m = np.array([l is not None for b in train for l in b["_t"][2]])
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, class_weight="balanced", random_state=0).fit(X[m], y[m])
    return clf


def trim(bk, accepted, clf, t):
    _, lines, _ = bk["_t"]; p = clf.predict_proba(bk["_X"])[:, 1]; out = []
    for a, b, c in accepted:
        while a <= b and (not lines[a].strip() or p[a] < t): a += 1
        while b >= a and (not lines[b].strip() or p[b] < t): b -= 1
        if a <= b: out.append((a, b, c))
    return out


def line_variant(bk, clf, t):
    _, lines, _ = bk["_t"]; p = clf.predict_proba(bk["_X"])[:, 1]
    return runs([pi >= t and bool(l.strip()) for pi, l in zip(p, lines)], lines)


def line_runs_filtered(bk, clf, t, t_run):
    _, lines, _ = bk["_t"]; p = clf.predict_proba(bk["_X"])[:, 1]
    out = []
    for a, b, c in runs([pi >= t and bool(l.strip()) for pi, l in zip(p, lines)], lines):
        idx = [i for i in range(a, b + 1) if lines[i].strip()]
        if idx and float(np.mean([p[i] for i in idx])) >= t_run:
            out.append((a, b, c))
    return out


results = {}
for seed in range(5):
    split = lambda s: int(hashlib.sha256(f"{seed}:{s}".encode()).hexdigest(), 16) % 5 < 2       # 40% train, 60% test
    train = [b for b in books if split(b["stem"])]; test = [b for b in books if not split(b["stem"])]
    acc_ac, t_ac = fit_block_lr(train, "a"); acc_a2c, t_a2c = fit_block_lr(train, "a2")
    clf = fit_line_model(train)
    t_trim = max((score(train, {b["stem"]: trim(b, acc_a2c(b, t_a2c), clf, t) for b in train})["f1"], t) for t in np.arange(0.1, 0.91, 0.1))[1]
    t_line = max((score(train, {b["stem"]: line_variant(b, clf, t) for b in train})["f1"], t) for t in np.arange(0.1, 0.91, 0.05))[1]
    t_run = max((score(train, {b["stem"]: line_runs_filtered(b, clf, t_line, tr) for b in train})["f1"] - 0.5 * score(train, {b["stem"]: line_runs_filtered(b, clf, t_line, tr) for b in train})["prose_only_share"], tr) for tr in np.arange(0.3, 0.96, 0.05))[1]
    v = {"baseline": {b["stem"]: cands["base"][b["stem"]] for b in test},
         "(a)": {b["stem"]: cands["a"][b["stem"]] for b in test},
         "(a2) code-shaped colon": {b["stem"]: cands["a2"][b["stem"]] for b in test},
         "(a)+(c)": {b["stem"]: acc_ac(b, t_ac) for b in test},
         "(a2)+(c)": {b["stem"]: acc_a2c(b, t_a2c) for b in test},
         "(a2)+(c)+trim": {b["stem"]: trim(b, acc_a2c(b, t_a2c), clf, t_trim) for b in test},
         "(e) line classifier, all lines": {b["stem"]: line_variant(b, clf, t_line) for b in test},
         "(e)+run filter": {b["stem"]: line_runs_filtered(b, clf, t_line, t_run) for b in test}}
    for k, acc in v.items():
        results.setdefault(k, []).append(score(test, acc))
    print(f"split {seed}: train {len(train)} test {len(test)}", flush=True)

summary = {}
for k, rs in results.items():
    summary[k] = {m: (round(float(np.mean([r[m] for r in rs])), 3), round(float(np.std([r[m] for r in rs])), 3))
                  for m in ("precision", "recall", "f1", "prose_only_share", "leadin_share")}
json.dump({"books": len(books), "splits": 5, "summary": summary, "per_split": results}, open(OUT, "w"), indent=1)
print(f"{'variant':34s} {'precision':>14s} {'recall':>14s} {'F1':>14s} {'prose-only':>14s} {'lead-ins':>14s}")
for k, s in summary.items():
    print(f"{k:34s} " + " ".join(f"{s[m][0]:.3f} ±{s[m][1]:.3f}".rjust(14) for m in ("precision", "recall", "f1", "prose_only_share", "leadin_share")))
