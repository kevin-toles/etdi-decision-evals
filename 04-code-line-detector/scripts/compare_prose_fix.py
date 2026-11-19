"""Prose-defect comparison: baseline vs (a) narrow colon fix vs (b) design 0.5 threshold vs (c) recalibrated scoring
(logistic regression over measured block features, threshold fitted on training books) vs (a)+(c), graded line by
line against the PDF-font answer key on held-out books. No model is loaded.
    cd Code-Orchestrator-Service && python3 <this> answer_key.json report.json"""
import hashlib, json, math, os, re, sys
sys.path.insert(0, os.getcwd())
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from src.extractors.code_block_extractor import HeuristicCodeDetector

KEY, OUT = sys.argv[1], sys.argv[2]


class NarrowColonDetector(HeuristicCodeDetector):
    """(a): a line ending in ':' counts as code only when the next non-blank line is indented deeper."""

    def detect_candidates(self, text):
        lines = text.split("\n")
        self._prose_colon = set()
        for i, line in enumerate(lines):
            if line.rstrip().endswith(":"):
                nxt = next((l for l in lines[i + 1:i + 6] if l.strip()), None)
                if nxt is None or self._get_indent_level(nxt) <= self._get_indent_level(line):
                    self._prose_colon.add(line)
        return super().detect_candidates(text)

    def _strip(self, line):
        return line.rstrip()[:-1] if line in getattr(self, "_prose_colon", ()) else line

    def _line_has_code_signals(self, line):
        return super()._line_has_code_signals(self._strip(line))

    def _detect_heuristic_blocks(self, text):
        lines = text.split("\n")
        stripped = "\n".join(self._strip(l) for l in lines)       # same line count, same offsets except the colons
        cands = super()._detect_heuristic_blocks(stripped)
        # restore the original content (colons) for each candidate span
        offs, o = [], 0
        for l in lines:
            offs.append(o); o += len(l) + 1
        s_offs, o = [], 0
        for l in stripped.split("\n"):
            s_offs.append(o); o += len(l) + 1
        fixed = []
        for c in cands:
            first = max(i for i, so in enumerate(s_offs) if so <= c.start_char)
            last = max(i for i, so in enumerate(s_offs) if so <= max(c.start_char, c.end_char - 1))
            content = "\n".join(lines[first:last + 1])
            fixed.append(c.model_copy(update={"content": content, "start_char": offs[first], "end_char": offs[first] + len(content)}))
        return fixed


STOP = set("the a an of to in and or is are was were be been for on with as by that this it its from at which can will "
           "we you they he she not but if then than so such these those there their our your into also may each".split())
SIGNALS = ["python_function_def", "python_class_def", "python_import", "colon_block", "return_statement", "markdown_fence"]


def features(content, conf, signals):
    ls = [l for l in content.split("\n") if l.strip()]
    n = max(1, len(ls)); chars = "".join(content.split())
    words = re.findall(r"[A-Za-z]+", content.lower())
    f = [conf, math.log(n), sum(1 for l in ls if len(l) - len(l.lstrip()) >= 2) / n,
         sum(ch in "{}()[];=<>+-*/&|!#\"'_.:" for ch in chars) / max(1, len(chars)),
         sum(1 for l in ls if l.rstrip()[-1:] in ";{})," ) / n,
         sum(w in STOP for w in words) / max(1, len(words)),
         len(words) / n, float(ls[0].rstrip().endswith(":")) if ls else 0.0,
         sum(1 for l in ls if l.strip()[:1].isupper() and l.rstrip().endswith(".")) / n,
         sum(ch.isdigit() for ch in chars) / max(1, len(chars))]
    return f + [float(s in signals) for s in SIGNALS]


def book_text(book):
    lines, labels = [], []
    for k, pg in enumerate(book["pages"]):
        if k:
            lines += ["", ""][:1]; labels += [None]          # "\n\n" join adds one empty line between pages
        for t, lab in pg["lines"]:
            lines.append(t); labels.append(lab)
    return "\n".join(lines), lines, labels


def spans(text, lines, cands):
    offs, o = [], 0
    for l in lines:
        offs.append(o); o += len(l) + 1
    out = []
    for c in cands:
        a = max(i for i, so in enumerate(offs) if so <= c.start_char)
        b = max(i for i, so in enumerate(offs) if so <= max(c.start_char, c.end_char - 1))
        out.append((a, b, c))
    return out


def score(books_eval, accepted_by_book):
    tp = fp = fn = 0; blocks = prose_only = leadin = 0
    for bk in books_eval:
        _, lines, labels = bk["_t"]
        pred = [False] * len(lines)
        for a, b, _ in accepted_by_book[bk["stem"]]:
            for i in range(a, b + 1):
                pred[i] = True
            labs = [labels[i] for i in range(a, b + 1) if labels[i] is not None]
            if labs:
                blocks += 1
                if not any(labs): prose_only += 1
                elif not labs[0] and any(labs[1:]): leadin += 1
        for p, lab in zip(pred, labels):
            if lab is None: continue
            tp += p and lab; fp += p and not lab; fn += (not p) and lab
    prec = tp / max(1, tp + fp); rec = tp / max(1, tp + fn)
    return {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(2 * prec * rec / max(1e-9, prec + rec), 3),
            "code_lines_found": tp, "prose_lines_kept": fp, "code_lines_missed": fn, "blocks": blocks,
            "prose_only_blocks": prose_only, "prose_only_share": round(prose_only / max(1, blocks), 3),
            "leadin_blocks": leadin, "leadin_share": round(leadin / max(1, blocks), 3)}


key = json.load(open(KEY)); books = key["books"]
for bk in books:
    bk["_t"] = book_text(bk)
    bk["_split"] = "train" if int(hashlib.sha256(bk["stem"].encode()).hexdigest(), 16) % 2 == 0 else "test"
train = [b for b in books if b["_split"] == "train"]; test = [b for b in books if b["_split"] == "test"]

base_det, narrow_det = HeuristicCodeDetector(), NarrowColonDetector()
cands = {"base": {}, "narrow": {}}
for bk in books:
    text, lines, _ = bk["_t"]
    cands["base"][bk["stem"]] = spans(text, lines, base_det.detect_candidates(text))
    cands["narrow"][bk["stem"]] = spans(text, lines, narrow_det.detect_candidates(text))


def fit_lr(source):
    X, y = [], []
    for bk in train:
        _, _, labels = bk["_t"]
        for a, b, c in cands[source][bk["stem"]]:
            labs = [labels[i] for i in range(a, b + 1) if labels[i] is not None]
            if not labs: continue
            X.append(features(c.content, c.confidence, c.detection_signals)); y.append(sum(labs) / len(labs) >= 0.5)
    if len(set(y)) < 2:
        return (lambda book, t: list(cands[source][book["stem"]])), 0.0, len(y)
    sc = StandardScaler().fit(X); lr = LogisticRegression(class_weight="balanced", max_iter=2000).fit(sc.transform(X), y)
    def accept(book, t):
        out = []
        for a, b, c in cands[source][book["stem"]]:
            p = lr.predict_proba(sc.transform([features(c.content, c.confidence, c.detection_signals)]))[0, 1]
            if p >= t: out.append((a, b, c))
        return out
    best = max((score(train, {b["stem"]: accept(b, t) for b in train})["f1"], t) for t in np.arange(0.05, 0.96, 0.05))
    return accept, round(float(best[1]), 2), len(y)


acc_c, t_c, n_c = fit_lr("base"); acc_ac, t_ac, n_ac = fit_lr("narrow")
variants = {
    "baseline (today)": {b["stem"]: cands["base"][b["stem"]] for b in books},
    "(a) narrow colon fix": {b["stem"]: cands["narrow"][b["stem"]] for b in books},
    "(b) design min_confidence 0.5": {b["stem"]: [x for x in cands["base"][b["stem"]] if x[2].confidence >= 0.5] for b in books},
    f"(c) recalibrated (LR, t={t_c})": {b["stem"]: acc_c(b, t_c) for b in books},
    f"(a)+(c) (LR on narrow, t={t_ac})": {b["stem"]: acc_ac(b, t_ac) for b in books},
}
report = {"books": len(books), "train_books": len(train), "test_books": len(test),
          "labelled_lines_test": sum(1 for b in test for l in b["_t"][2] if l is not None),
          "code_lines_test": sum(1 for b in test for l in b["_t"][2] if l), "lr_training_blocks": {"c": n_c, "a+c": n_ac},
          "held_out": {k: score(test, v) for k, v in variants.items()},
          "all_books_untrained_variants": {k: score(books, v) for k, v in list(variants.items())[:3]}}
json.dump(report, open(OUT, "w"), indent=1)
print(json.dumps({k: report[k] for k in ("books", "train_books", "test_books", "labelled_lines_test", "code_lines_test")}))
for k, v in report["held_out"].items():
    print(f"{k:38s} P {v['precision']:.3f} R {v['recall']:.3f} F1 {v['f1']:.3f} | prose-only blocks {v['prose_only_share']:.0%} lead-ins {v['leadin_share']:.0%} | blocks {v['blocks']}")
