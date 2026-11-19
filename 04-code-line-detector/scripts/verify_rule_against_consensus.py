"""Re-label the audited lines with a candidate labeller and compare with the four-reviewer consensus of an audit run.
The consensus is fixed, so a labelling rule can be measured without re-running the reviewers.
    python3 verify_rule_against_consensus.py RUN_DIR LABELLER.py PDF_INDEX.json"""
import collections, importlib.util, json, sys
from multiprocessing import Pool

lab = None


def load_labeller(path):
    global lab
    argv, sys.argv = sys.argv, ["labeller", "/dev/null", "0"]       # the labeller reads argv at import
    spec = importlib.util.spec_from_file_location("lab", path); lab = importlib.util.module_from_spec(spec); spec.loader.exec_module(lab)
    sys.argv = argv


def relabel(stem_pdf):
    why, rec = lab.label(stem_pdf)
    return stem_pdf[0], why, ([l for p in rec["pages"] for _, l in p["lines"]] if rec else None)


if __name__ == "__main__":
    RUN, LAB, INDEX = sys.argv[1:4]
    hidden = json.load(open(f"{RUN}/font_labels_HIDDEN.json")); rep = json.load(open(f"{RUN}/audit_report.json"))
    names = rep["reviewers"]; revs = {n: json.load(open(f"{RUN}/verdicts_{n}.json"))["verdicts"] for n in names}
    cons = {}
    for iid in hidden:
        top, c = collections.Counter(revs[n][iid] for n in names).most_common(1)[0]
        cons[iid] = top if c >= (3 if len(names) == 4 else len(names) // 2 + 1) else "no_consensus"
    pdfs = json.load(open(INDEX))
    with Pool(8, initializer=load_labeller, initargs=(LAB,)) as pool:
        res = {s: (w, l) for s, w, l in pool.map(relabel, [(s, pdfs[s]) for s in sorted({h["stem"] for h in hidden.values()})])}
    tab = collections.defaultdict(collections.Counter); changes = []
    for iid, h in hidden.items():
        c = cons[iid]
        if c not in ("code", "not_code"):
            continue
        why, labels = res[h["stem"]]
        new = "doc_dropped:" + why if labels is None else {True: "code", False: "not_code", None: "unknown"}[labels[h["line_index"]]]
        s = (h["kind"], h["font_label"])
        tab[s]["old_" + ("agree" if h["font_label"] == c else "disagree")] += 1
        tab[s]["new_" + ("agree" if new == c else "unknown" if new == "unknown" else "dropped" if new.startswith("doc_dropped") else "disagree")] += 1
        if new != h["font_label"]:
            changes.append((iid, h["kind"], h["font_label"], new, c))
    print(f"{'stratum':18s} {'old err':>8s} {'new err':>8s}  new: agree disagree unknown dropped")
    for s in sorted(tab):
        t = tab[s]; o = t["old_disagree"] / max(1, t["old_agree"] + t["old_disagree"]); n = t["new_disagree"] / max(1, t["new_agree"] + t["new_disagree"])
        print(f"{s[0] + '/' + s[1]:18s} {o:8.1%} {n:8.1%}  {t['new_agree']:9d} {t['new_disagree']:8d} {t['new_unknown']:7d} {t['new_dropped']:7d}")
    sheet = {i["id"]: i["TARGET"] for i in json.load(open(f"{RUN}/audit_sheet.json"))["items"]}
    print(f"\n{len(changes)} audited lines changed label:")
    for iid, k, old, new, c in changes:
        print(f"  {'OK ' if new == c else 'unk' if new == 'unknown' else 'BAD'} {k:5s} {old:8s} -> {new:10s} consensus {c:8s} | {sheet[iid][:70]!r}")
