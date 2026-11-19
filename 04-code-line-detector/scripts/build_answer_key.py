"""Answer key for the prose-defect comparison: JSON page lines labelled code / not code from the matching PDF's fonts.
A line is code when every non-blank span on the matching PDF line is set in a monospace font (font name or PyMuPDF's
monospace flag). Books are sampled at random from raw JSON books with a same-name PDF; a book is kept only when the
JSON and PDF page counts match, at least 85% of its window's JSON lines are found on the same PDF page, and the
window holds code (>= 2% monospace lines), and the window's body text is not itself monospace (typewritten reports), and most window pages are not scans (a full-page image under an OCR text layer)."""
import json, os, random, re, sys, unicodedata
import fitz

RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
PDF_ROOT = "<RAW_ROOT>/[PROCESSED]"
OUT = sys.argv[1]
TARGET, WINDOW, SEED = int(sys.argv[2]), 40, 20261027
MONO = re.compile(r"(?i)mono|courier|consol|menlo|inconsolata|typewriter|cmtt|lmmono|andale|sourcecode|source ?code|fira ?code|letter ?gothic|\bcode\b|lucida ?console")


def norm(s):
    return " ".join(unicodedata.normalize("NFKC", s).split())


pdfs = {}
for r, _, files in os.walk(PDF_ROOT):
    for f in files:
        if f.lower().endswith(".pdf"):
            pdfs.setdefault(f[:-4], os.path.join(r, f))
stems = sorted(e.name[:-5] for e in os.scandir(RAW) if e.name.endswith(".json") and e.name[:-5] in pdfs)
random.Random(SEED).shuffle(stems)

books, tried, skips = [], 0, {"scanned": 0, "typewriter_body": 0, "page_count": 0, "alignment": 0, "no_code": 0, "error": 0, "short": 0}
for stem in stems:
    if len(books) >= TARGET:
        break
    tried += 1
    try:
        raw = json.load(open(os.path.join(RAW, stem + ".json")))
        pages = raw.get("pages") or []
        doc = fitz.open(pdfs[stem])
        if len(pages) < 60:
            skips["short"] += 1; continue
        if doc.page_count != len(pages):
            skips["page_count"] += 1; continue
        start = int(len(pages) * 0.3)
        def scanned(pg):                     # one image covering >= 80% of the page: a scan with an OCR text layer
            area = abs(pg.rect)
            return any(abs(fitz.Rect(i["bbox"]) & pg.rect) >= 0.8 * area for i in pg.get_image_info())
        win = range(start, min(start + WINDOW, doc.page_count))
        if sum(scanned(doc[i]) for i in win) >= 0.5 * len(win):
            skips["scanned"] += 1; continue
        out_pages, found, total, mono = [], 0, 0, 0
        mono_chars = body_chars = 0
        for pg in pages[start:start + WINDOW]:
            idx = pg["page_number"] - 1
            labels = {}
            for b in doc[idx].get_text("dict")["blocks"]:
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
        if mono_chars >= body_chars:          # body text itself is monospace: fonts cannot tell code from prose
            skips["typewriter_body"] += 1; continue
        if total == 0 or found / total < 0.85:
            skips["alignment"] += 1; continue
        if mono / found < 0.02:
            skips["no_code"] += 1; continue
        books.append({"stem": stem, "pdf": pdfs[stem], "pages": out_pages,
                      "matched_share": round(found / total, 3), "code_line_share": round(mono / found, 3)})
        print(f"{len(books):>3} kept {stem[:60]!r} matched {found/total:.0%} code {mono/found:.0%}", flush=True)
    except Exception as e:
        skips["error"] += 1
json.dump({"books": books, "tried": tried, "skips": skips}, open(OUT, "w"))
print("tried", tried, "kept", len(books), "skips", skips)
