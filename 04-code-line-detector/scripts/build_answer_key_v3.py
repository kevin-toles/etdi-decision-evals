"""Answer key v3 for the code-line detector. Changes from v2 (label rule only; sampling, windows and filters as v2):
  1. A font is monospace when its glyphs measure monospace in this document: narrow glyphs (i l j t f . , ' ! |) are at
     least 0.85 the width of wide ones (m w M W). PyMuPDF's monospace flag and the font-name list are used only for
     fonts with too few of those glyphs to measure.
  2. A line is code when >= 80% of its letters and digits are monospace (punctuation is often set in the body font;
     punctuation-only lines count all characters), ignoring spans of <= 2 characters in a non-text font
     (Wingdings, Dingbats, Symbol: callout markers) or any 1-character span when the rest of the line is monospace.
  3. Repeated identical lines on a page take their labels in page order instead of sharing one.
  4. A document is dropped (code_not_mono) when its code is evidently not set in monospace: >= 5 code-shaped lines
     (a lone brace, a line ending in '{', or a line holding '=' or '(' that ends in ';') in
     proportional fonts and those are >= 20% of all code-shaped lines; lines set in math fonts (typeset equations) are
     not counted.
    python3 build_answer_key_v3.py out.jsonl TARGET [--stems-from answer_key.json]"""
import json, os, random, re, sys, unicodedata
from collections import defaultdict, deque
from multiprocessing import Pool
import fitz

RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
OUT, TARGET = sys.argv[1], int(sys.argv[2])
STEMS_FROM = sys.argv[sys.argv.index("--stems-from") + 1] if "--stems-from" in sys.argv else None
WINDOW, MIN_PAGES, SEED, WORKERS = 25, 8, 20261028, 8
HERE = os.path.dirname(os.path.abspath(__file__))
MONO_NAME = re.compile(r"(?i)mono|courier|consol|menlo|monaco|inconsolata|typewriter|cmtt|txtt|lmmono|andale|sourcecode|source ?code|fira ?code|letter ?gothic|lucida ?console|\bcode\b")
MATH_FONT = re.compile(r"(?i)^cm(mi|r|sy|ex|bx|ti)\d|math|msbm|msam|eufm|rsfs|stix|^mtmi|^mtsy|^txmi|^txsy|^pxmi")
GLYPH_FONT = re.compile(r"(?i)wingding|dingbat|symbol|zapf|webding")
NARROW, WIDE = set("iljtf.,'!|"), set("mwMW")
CODE_SHAPED = re.compile(r"^\s*(\}|\};|\{|\}\);|\);)\s*$|\{\s*$|[=(].*;\s*$")


def norm(s):
    return " ".join(unicodedata.normalize("NFKC", s).split())


def mono_fonts(doc, page_idx):
    widths = defaultdict(lambda: [[], []])
    flagged = {}
    for i in page_idx:
        for b in doc[i].get_text("rawdict")["blocks"]:
            for ln in b.get("lines", []):
                for s in ln["spans"]:
                    flagged[s["font"]] = flagged.get(s["font"], False) or bool(s["flags"] & 8)
                    size = s["size"] or 1
                    for ch in s["chars"]:
                        c = ch["c"]; w = (ch["bbox"][2] - ch["bbox"][0]) / size
                        if c in NARROW: widths[s["font"]][0].append(w)
                        elif c in WIDE: widths[s["font"]][1].append(w)
    out = {}
    for f in flagged:
        n, w = widths[f]
        if len(n) >= 5 and len(w) >= 5:
            out[f] = (sum(n) / len(n)) >= 0.85 * (sum(w) / len(w))
        else:
            out[f] = flagged[f] or bool(MONO_NAME.search(f))
    return out


def line_is_mono(spans, mono):
    spans = [s for s in spans if s["text"].strip()]
    rest_mono = lambda k: all(mono.get(t["font"], False) for j, t in enumerate(spans) if j != k)
    kept = [s for k, s in enumerate(spans)
            if not ((len(s["text"].strip()) <= 2 and GLYPH_FONT.search(s["font"]))
                    or (len(s["text"].strip()) == 1 and len(spans) > 1 and rest_mono(k)))]
    size = lambda s: sum(ch.isalnum() for ch in s["text"])
    if not sum(size(s) for s in kept):                   # punctuation-only line such as "}"
        size = lambda s: len(s["text"].strip())
    total = sum(size(s) for s in kept)
    return total > 0 and sum(size(s) for s in kept if mono.get(s["font"], False)) / total >= 0.8


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
        mono = mono_fonts(doc, win)
        out_pages, found, total, n_mono, mono_chars, body_chars = [], 0, 0, 0, 0, 0
        shaped_mono = shaped_prop = 0
        for pg in pages[start:start + WINDOW]:
            labels = defaultdict(deque)
            for b in doc[pg["page_number"] - 1].get_text("dict")["blocks"]:
                for ln in b.get("lines", []):
                    spans = [s for s in ln["spans"] if s["text"].strip()]
                    if not spans:
                        continue
                    t = norm("".join(s["text"] for s in ln["spans"]))
                    is_mono = line_is_mono(spans, mono)
                    labels[t].append(is_mono)
                    if CODE_SHAPED.search(t) and not any(MATH_FONT.search(x["font"]) for x in spans):
                        shaped_mono += is_mono; shaped_prop += not is_mono
                    for s in spans:
                        n = len(s["text"].strip())
                        if mono.get(s["font"], False): mono_chars += n
                        else: body_chars += n
            rows = []
            for line in (pg.get("text") or "").split("\n"):
                t = norm(line)
                if not t:
                    rows.append([line, None]); continue
                total += 1
                q = labels.get(t)
                if q:
                    lab = q.popleft() if len(q) > 1 else q[0]
                    found += 1; n_mono += lab; rows.append([line, bool(lab)])
                else:
                    rows.append([line, None])
            out_pages.append({"page_number": pg["page_number"], "lines": rows})
        if mono_chars >= body_chars:
            return "typewriter_body", None
        if total == 0 or found / total < 0.85:
            return "alignment", None
        if shaped_prop >= 5 and shaped_prop >= 0.2 * (shaped_prop + shaped_mono):
            return "code_not_mono", None
        if n_mono / found < 0.02:
            return "no_code", None
        return "kept", {"stem": stem, "pdf": pdf, "doc_pages": len(pages), "pages": out_pages,
                        "matched_share": round(found / total, 3), "code_line_share": round(n_mono / found, 3),
                        "mono_fonts": sorted(f for f, m in mono.items() if m)}
    except Exception:
        return "error", None


if __name__ == "__main__":
    pdfs = json.load(open(os.path.join(HERE, "pdf_index.json")))
    if STEMS_FROM:
        stems = [b["stem"] for b in json.load(open(STEMS_FROM))["books"]]
    else:
        stems = sorted(e.name[:-5] for e in os.scandir(RAW) if e.name.endswith(".json") and e.name[:-5] in pdfs)
        random.Random(SEED).shuffle(stems)
        old = {b["stem"] for b in json.load(open(os.path.join(HERE, "answer_key.json")))["books"]}
        stems = [s for s in stems if s not in old]
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
