"""Golden set (OQ#18 pilot): one model-neutral keyword index over every chapter of the [CLEANED] corpus, so candidate
answers are found by BM25 (SQLite FTS5, porter stemming), never by an embedding model under test. Chapters are split
by HTC's own `raw_chapters` (same `{stem}#{number}` refs as heldout.json). Contentless index: text is re-read from raw.
    cd htc-multidim-classification-service && python3 <this> <out.sqlite>"""
import json, os, sqlite3, sys, time
from multiprocessing import Pool
sys.path.insert(0, os.getcwd())
from src.features.ClassifyCorpus.taxonomy.anchor_text_miner import raw_chapters

BASE = "<CORPUS_ROOT>/collections"
COLLS = ["software-engineering", "theoretical-foundations"]

def load(arg):
    coll, path = arg
    stem = os.path.basename(path)[:-5]
    try:
        doc = json.load(open(path))
    except Exception as e:
        return coll, stem, None, repr(e)[:200]
    out = []
    titles = {}
    for i, ch in enumerate(doc.get("chapters") or [], start=1):
        titles[f"{stem}#{ch.get('number', ch.get('chapter_id', i))}"] = ch.get("title") or ""
    for ref, text in raw_chapters(doc, stem, max_chars=10**9):
        out.append((ref, titles.get(ref, ""), len(text), text))
    return coll, stem, out, None

def main(dst):
    db = sqlite3.connect(dst)
    db.executescript("""PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;
      CREATE TABLE IF NOT EXISTS chapter(id INTEGER PRIMARY KEY, ref TEXT UNIQUE, stem TEXT, collection TEXT, title TEXT, chars INTEGER);
      CREATE TABLE IF NOT EXISTS failed(collection TEXT, stem TEXT, error TEXT);
      CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(title, body, content='', tokenize='porter unicode61 remove_diacritics 2');""")
    jobs = [(c, e.path) for c in COLLS for e in os.scandir(f"{BASE}/{c}/raw") if e.name.endswith(".json")]
    if len(sys.argv) > 2:
        jobs = jobs[: int(sys.argv[2])]
    print("files", len(jobs), flush=True)
    done = {r[0] for r in db.execute("SELECT DISTINCT stem FROM chapter")} | {r[0] for r in db.execute("SELECT stem FROM failed")}
    jobs = [j for j in jobs if os.path.basename(j[1])[:-5] not in done]   # resumable
    print("to do", len(jobs), flush=True)
    t0, n_ch, k = time.time(), 0, 0
    with Pool(4) as pool:
        for b in range(0, len(jobs), 200):   # bounded batches: the writer is the bottleneck, so never queue more than one batch
            for coll, stem, chs, err in pool.imap_unordered(load, jobs[b:b + 200], chunksize=4):
                k += 1
                if err:
                    db.execute("INSERT INTO failed VALUES(?,?,?)", (coll, stem, err)); continue
                for ref, title, chars, text in chs:
                    cur = db.execute("INSERT OR IGNORE INTO chapter(ref,stem,collection,title,chars) VALUES(?,?,?,?,?)", (ref, stem, coll, title, chars))
                    if cur.rowcount:
                        db.execute("INSERT INTO fts(rowid,title,body) VALUES(?,?,?)", (cur.lastrowid, title, text)); n_ch += 1
            db.commit()
            if k % 5000 < 200:
                print(k, n_ch, int(time.time() - t0), "s", flush=True)
    db.commit(); db.execute("INSERT INTO fts(fts) VALUES('optimize')"); db.commit()
    print("done files", len(jobs), "chapters", n_ch, int(time.time() - t0), "s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1])
