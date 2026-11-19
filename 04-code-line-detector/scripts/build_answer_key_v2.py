"""Larger answer key for the code-line detector: same labelling rule and filters as build_answer_key.py (a JSON line is
code when every span on the matching PDF line is monospace; scans, typewritten bodies, page-count mismatches, poor
alignment and code-free windows are skipped), but run in parallel, streamed to JSONL so any prefix can be evaluated,
and covering short documents too (the detector runs on every document, not only books). Window: WINDOW pages from 30%
into documents of >= 60 pages, else from page 1. The PDFs are used only to make labels.
    python3 build_answer_key_v2.py out.jsonl TARGET"""
import json, os, random, re, sys, unicodedata
from multiprocessing import Pool
import fitz

RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
PDF_ROOT = "<RAW_ROOT>/[PROCESSED]"
OUT, TARGET = sys.argv[1], int(sys.argv[2])
WINDOW, MIN_PAGES, SEED, WORKERS = 25, 8, 20261028, 8
MONO = re.compile(r"(?i)mono|courier|consol|menlo|inconsolata|typewriter|cmtt|lmmono|andale|sourcecode|source ?code|fira ?code|letter ?gothic|\bcode\b|lucida ?console")
INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_index.json")


def norm(s):
    return " ".join(unicodedata.normalize("NFKC", s).split())


def label(stem_pdf):
    stem, pdf = stem_pdf
    try:
        raw = json.load(open(os.path.join(RAW, stem + ".json")))
        pages = raw.get("pages") or []
        if len(pages) < MIN_PAGES:
            return "short", None
        doc = fitz.open(pdf)
        if doc.page_count != len(pages):
            return "page_count", None
        start = int(len(pages) * 0.3) if len(pages) >= 60 else 0
        win = range(start, min(start + WINDOW, doc.page_count))
        def scanned(pg):
            area = abs(pg.rect)
            return any(abs(fitz.Rect(i["bbox"]) & pg.rect) >= 0.8 * area for i in pg.get_image_info())
        if sum(scanned(doc[i]) for i in win) >= 0.5 * len(win):
            return "scanned", None
        out_pages, found, total, mono, mono_chars, body_chars = [], 0, 0, 0, 0, 0
        for pg in pages[start:start + WINDOW]:
            labels = {}
            for b in doc[pg["page_number"] - 1].get_text("dict")["blocks"]:
                for ln in b.get("lines", []):
                    spans = [s for s in ln["spans"] if s["text"].strip()]
                    if not spans:
                        continue
                    t = norm("".join(s["text"] for s in ln["spans"]))
                    is_mono = all((s["flags"] & 8) or MONO.search(s["font"]) for s in spans)
                    labels[t] = labels.get(t, False) or is_mono
                    for s in spans:
                        n = len(s["text"].strip())
                        if (s["flags"] & 8) or MONO.search(s["font"]): mono_chars += n
                        else: body_chars += n
            rows = []
            for line in (pg.get("text") or "").split("\n"):
                t = norm(line)
                if not t:
                    rows.append([line, None]); continue
                total += 1
                if t in labels:
                    found += 1; mono += labels[t]; rows.append([line, bool(labels[t])])
                else:
                    rows.append([line, None])
            out_pages.append({"page_number": pg["page_number"], "lines": rows})
        if mono_chars >= body_chars:
            return "typewriter_body", None
        if total == 0 or found / total < 0.85:
            return "alignment", None
        if mono / found < 0.02:
            return "no_code", None
        return "kept", {"stem": stem, "pdf": pdf, "doc_pages": len(pages), "pages": out_pages,
                        "matched_share": round(found / total, 3), "code_line_share": round(mono / found, 3)}
    except Exception:
        return "error", None


if __name__ == "__main__":
    if os.path.exists(INDEX):
        pdfs = json.load(open(INDEX))
    else:
        pdfs = {}
        for r, _, files in os.walk(PDF_ROOT):
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdfs.setdefault(f[:-4], os.path.join(r, f))
        json.dump(pdfs, open(INDEX, "w"))
    stems = sorted(e.name[:-5] for e in os.scandir(RAW) if e.name.endswith(".json") and e.name[:-5] in pdfs)
    random.Random(SEED).shuffle(stems)
    old = {b["stem"] for b in json.load(open(os.path.join(os.path.dirname(INDEX), "answer_key.json")))["books"]}
    stems = [s for s in stems if s not in old]           # keep the 40-book key independent
    skips, kept, tried = {}, 0, 0
    with Pool(WORKERS) as pool, open(OUT, "w") as fh:
        for why, rec in pool.imap(label, ((s, pdfs[s]) for s in stems), chunksize=4):
            tried += 1
            skips[why] = skips.get(why, 0) + 1
            if rec:
                fh.write(json.dumps(rec) + "\n"); fh.flush(); kept += 1
                print(f"{kept:>4} kept  tried {tried}  pages {rec['doc_pages']:>4}  code {rec['code_line_share']:.0%}  {rec['stem'][:50]!r}", flush=True)
            if kept >= TARGET:
                pool.terminate(); break
    json.dump({"tried": tried, "kept": kept, "skips": skips}, open(OUT + ".meta.json", "w"))
    print("tried", tried, "kept", kept, "skips", skips)
