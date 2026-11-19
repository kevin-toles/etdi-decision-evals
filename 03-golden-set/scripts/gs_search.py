"""Golden set: model-neutral candidate search. BM25 (SQLite FTS5) over the [CLEANED] chapter index built by
build_fts.py, then shows each hit's best-matching windows re-read from raw through HTC's `raw_chapters`.
Also flags each chapter's split: heldout (three_way_eval/heldout.json), anchor_evidence (seen by the 2026-10-20
anchor curation), or unseen.   cd htc-multidim-classification-service &&
    python3 <this> '<fts5 query>' [k=15] [window_terms='a|b|c'] [max_chars=600000]"""
import json, os, re, sqlite3, sys
sys.path.insert(0, os.getcwd())
from src.features.ClassifyCorpus.taxonomy.anchor_text_miner import raw_chapters

DB = os.environ.get("GS_DB", "<WORK_DIR>/chapters_fts_v2.sqlite")
BASE = "<CORPUS_ROOT>/collections"
EV = os.path.dirname(os.path.abspath(__file__)) + "/.."
_split = None

def split_of(ref):
    global _split
    if _split is None:
        _split = {}
        for slug, rows in json.load(open(f"{EV}/three_way_eval/heldout.json")).items():
            for r, _ in rows: _split[r] = "heldout"
        pk = "output/anchor_curation/2026-10-20/packets"
        for f in os.listdir(pk):
            for s in json.load(open(f"{pk}/{f}"))["subdomains"]:
                for e in s.get("evidence") or []:
                    _split.setdefault(e["ref"], "anchor_evidence")
    return _split.get(ref, "unseen")

def chapter_text(coll, stem, ref):
    doc = json.load(open(f"{BASE}/{coll}/raw/{stem}.json"))
    return dict(raw_chapters(doc, stem, max_chars=10**9)).get(ref, "")

def windows(text, terms, width=int(os.environ.get("GS_W", 700)), n=int(os.environ.get("GS_N", 2))):
    rx = re.compile("|".join(terms), re.I)
    pos = [m.start() for m in rx.finditer(text)]
    if not pos: return []
    # densest windows: score each hit by hits within `width`
    scored = sorted(((sum(1 for q in pos if p <= q < p + width), p) for p in pos), reverse=True)
    out, used = [], []
    for c, p in scored:
        if any(abs(p - u) < width for u in used): continue
        used.append(p); s = max(0, p - 150)
        out.append((s, c, re.sub(r"\s+", " ", text[s:s + width])))
        if len(out) == n: break
    return out

def main():
    q = sys.argv[1]; k = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    if len(sys.argv) > 3 and sys.argv[3]:
        terms = sys.argv[3].split("|")
    else:
        terms = [re.escape(t) for t in re.findall(r'"([^"]+)"', q)] or [re.escape(t) for t in q.split() if t not in ("AND", "OR", "NOT")]
    maxc = int(sys.argv[4]) if len(sys.argv) > 4 else 600_000
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = db.execute("""SELECT c.ref, c.stem, c.collection, c.title, c.chars, f.r FROM
        (SELECT rowid, bm25(fts, 2.0, 1.0) r FROM fts WHERE fts MATCH ? ORDER BY r LIMIT ?) f
        JOIN chapter c ON c.id = f.rowid WHERE c.chars <= ? ORDER BY f.r""", (q, k * 3, maxc)).fetchall()[:k]
    for i, (ref, stem, coll, title, chars, r) in enumerate(rows, 1):
        print(f"\n[{i}] bm25={-r:.1f} {coll} | {ref} | '{title}' | {chars} chars | {split_of(ref)}")
        for s, c, w in windows(chapter_text(coll, stem, ref), terms):
            print(f"    @{s} ({c} hits) {w}")

if __name__ == "__main__":
    main()
