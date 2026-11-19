"""Corpus census for segment weights: a uniform random sample of every raw JSON, each classified as transcript,
no-PDF other, or a PDF document by page band (tiny < 8, short 8-59, book >= 60) and v4 labelling outcome
(code / low_code / codefree / scanned / code_not_mono / other). Uses build_strata_v4.label.
    python3 census_v4.py N out.json"""
import collections, importlib.util, json, os, random, sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
lab = None


def init():
    global lab
    argv, sys.argv = sys.argv, ["x", "/dev/null"]
    os.environ["MIN_PAGES"] = "1"
    spec = importlib.util.spec_from_file_location("st", os.path.join(HERE, os.environ.get("STRATA_BUILDER", "build_strata_v4.py"))); lab = importlib.util.module_from_spec(spec); spec.loader.exec_module(lab)
    sys.argv = argv


def classify(sp):
    stem, pdf = sp
    try:
        d = json.load(open(os.path.join(RAW, stem + ".json"))); n = len(d.get("pages") or [])
    except Exception:
        return "unreadable", "-"
    band = "tiny" if n < 8 else ("book" if n >= 60 else "short")
    if pdf is None:
        return ("transcript" if (d.get("metadata") or {}).get("source_type") == "youtube_transcript" else "no_pdf_other"), band
    lab.MODE = "code"; why, _ = lab.label((stem, pdf))
    if why == "kept": return "code", band
    if why == "no_code":
        lab.MODE = "codefree"; why2, _ = lab.label((stem, pdf))
        return ("codefree" if why2 == "kept" else "low_code"), band
    if why in ("scanned", "code_not_mono"): return why, band
    return "other_unlabellable", band


if __name__ == "__main__":
    N, OUT = int(sys.argv[1]), sys.argv[2]
    pdfs = json.load(open(os.path.join(HERE, "pdf_index.json")))
    names = sorted(e.name[:-5] for e in os.scandir(RAW) if e.name.endswith(".json"))
    smp = random.Random(20261101).sample(names, N)
    with Pool(4, initializer=init) as pool:
        res = pool.map(classify, [(s, pdfs.get(s)) for s in smp], chunksize=8)
    c = collections.Counter(res)
    json.dump({"N": N, "corpus_size": len(names), "counts": {f"{a}|{b}": v for (a, b), v in c.items()}}, open(OUT, "w"), indent=1)
    for (a, b), v in sorted(c.items(), key=lambda x: -x[1]):
        print(f"  {a:20s} {b:6s} {v:5d}  {v / N:6.1%}")
