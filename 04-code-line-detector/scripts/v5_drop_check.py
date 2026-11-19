import json, sys, importlib.util, collections
from multiprocessing import Pool
S, D = sys.argv[1], sys.argv[2]
mods = {}
def init():
    for v in ("v4", "v5"):
        argv, sys.argv = sys.argv, ["x", "/dev/null", "0"]
        spec = importlib.util.spec_from_file_location(v, f"{S}/build_answer_key_{v}.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); mods[v] = m
        sys.argv = argv
def run(sp):
    out = {}
    for v in ("v4", "v5"):
        why, rec = mods[v].label(sp)
        labs = [l for p in rec["pages"] for _, l in p["lines"]] if rec else None
        lines = [t for p in rec["pages"] for t, _ in p["lines"]] if rec else None
        out[v] = (why, labs, lines)
    return sp[0], out
if __name__ == "__main__":
    pdfs = json.load(open(f"{S}/pdf_index.json")); stems = set()
    for r in ("run_2026-10-28", "run_2026-10-28b"):
        for h in json.load(open(f"{D}/{r}/font_labels_HIDDEN.json")).values():
            if h["kind"] == "book": stems.add(h["stem"])
    with Pool(8, initializer=init) as p:
        res = p.map(run, [(s, pdfs[s]) for s in sorted(stems)])
    for stem, o in res:
        w4, l4, t4 = o["v4"]; w5, l5, t5 = o["v5"]
        if w4 == "kept" and w5 != "kept":
            removed = [t for t, a in zip(t4, l4) if a]
            print(f"\n## {stem[:70]}  v4 code lines {len(removed)} -> v5 {w5}")
            for t in removed[:12]: print("     ", t[:90])
