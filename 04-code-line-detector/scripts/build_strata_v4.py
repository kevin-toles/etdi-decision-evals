"""Extra answer-key strata (v4 labelling rules) for segment-level scoring. MODE (env):
  code      : documents with code, as build_answer_key_v4.py, limited to MIN_PAGES..MAX_PAGES (books, or tiny docs)
  codefree  : PDF documents whose window holds no monospace text at all; every line is labelled not code
  lowcode   : PDF documents with some monospace text but under 2% code lines (the main key's 2% floor left these out)
  transcript: YouTube transcripts (metadata.source_type == youtube_transcript, no PDF); every line labelled not code,
              on the assumption that spoken text carries no code formatting
Sampling uses SEED and skips every document in the EXCLUDE_KEYS files (comma-separated JSONL keys).
    MODE=code MIN_PAGES=60 TARGET=300 python3 build_strata_v4.py out.jsonl
Base rules (from build_answer_key_v4.py):
Answer key v4 for the code-line detector. v4 adds rule 5 to v3, from the four-reviewer audit (run_2026-10-28: 48% of
short-document code labels were URLs, DOIs, e-mails, table numbers and figure or table identifiers set in monospace):
  5. Within each run of consecutive monospace lines on a PDF page: a URL / DOI / e-mail / bare domain line is not code;
     a pure number is not code when no line in the run carries code punctuation; a line of <= 2 tokens is unknown
     (left out of scoring) when no line in the run carries code punctuation and it does not open with a code keyword. Runs with code punctuation are unchanged.
v3 changes from v2 (label rule only; sampling, windows and filters as v2):
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
OUT = sys.argv[1]
MODE, TARGET = os.environ.get("MODE", "code"), int(os.environ.get("TARGET", "200"))
MAX_PAGES = int(os.environ.get("MAX_PAGES", "100000"))
WINDOW, WORKERS = 25, 8
MIN_PAGES, SEED = int(os.environ.get("MIN_PAGES", "8")), int(os.environ.get("SEED", "20261030"))
HERE = os.path.dirname(os.path.abspath(__file__))
MONO_NAME = re.compile(r"(?i)mono|courier|consol|menlo|monaco|inconsolata|typewriter|cmtt|txtt|lmmono|andale|sourcecode|source ?code|fira ?code|letter ?gothic|lucida ?console|\bcode\b")
MATH_FONT = re.compile(r"(?i)^cm(mi|r|sy|ex|bx|ti)\d|math|msbm|msam|eufm|rsfs|stix|^mtmi|^mtsy|^txmi|^txsy|^pxmi")
GLYPH_FONT = re.compile(r"(?i)wingding|dingbat|symbol|zapf|webding")
NARROW, WIDE = set("iljtf.,'!|"), set("mwMW")
LINKISH = re.compile(r"^\W*\d*\s*(https?://|www\.|//[\w-]+\.[\w.-]+/|doi[:.]|URL\s)|^\S+@\S+\.\w+$|^[\w.-]+\.(com|org|net|io|edu|gov|ai|dev|uk|de)/\S*$", re.I)
NUMBER = re.compile(r"^[-−+]?\(?[\d.,]+\)?%?$")
LEAD_KW = set("import from cd return end else elif fi done esac pass break continue def class use package include require echo ls sudo git npm pip docker kubectl go mod let var const".split())
CODE_PUNCT = re.compile(r"[(){}\[\];=<>\"'#$@|&*+`\\]|->|::")
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


def run_rules(plines):
    """Rule 5 over one page's PDF lines [(text, is_mono)] in reading order -> True / False / None per line."""
    out = [m for _, m in plines]
    i = 0
    while i < len(plines):
        if not plines[i][1]:
            i += 1; continue
        j = i
        while j + 1 < len(plines) and plines[j + 1][1]:
            j += 1
        run = range(i, j + 1)
        has_code = any(CODE_PUNCT.search(plines[k][0]) and not LINKISH.search(plines[k][0]) and not NUMBER.match(plines[k][0]) for k in run)
        for k in run:
            t = plines[k][0]
            if LINKISH.search(t): out[k] = False
            elif NUMBER.match(t) and not has_code: out[k] = False
            elif not has_code and len(t.split()) <= 2 and t.split()[0] not in LEAD_KW: out[k] = None
        i = j + 1
    return out


def label(stem_pdf):
    stem, pdf = stem_pdf
    try:
        raw = json.load(open(os.path.join(RAW, stem + ".json")))
        pages = raw.get("pages") or []
        if len(pages) < MIN_PAGES:
            return "short", None
        if len(pages) > MAX_PAGES:
            return "long", None
        if MODE == "transcript":
            if (raw.get("metadata") or {}).get("source_type") != "youtube_transcript":
                return "not_transcript", None
            win_pages = pages[:WINDOW]
            rows = [{"page_number": pg["page_number"], "lines": [[l, False if l.strip() else None] for l in (pg.get("text") or "").split("\n")]} for pg in win_pages]
            return "kept", {"stem": stem, "pdf": None, "doc_pages": len(pages), "segment": "transcript", "pages": rows,
                            "matched_share": 1.0, "code_line_share": 0.0, "mono_fonts": []}
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
            labels, plines = defaultdict(deque), []
            for b in doc[pg["page_number"] - 1].get_text("dict")["blocks"]:
                for ln in b.get("lines", []):
                    spans = [s for s in ln["spans"] if s["text"].strip()]
                    if not spans:
                        continue
                    t = norm("".join(s["text"] for s in ln["spans"]))
                    is_mono = line_is_mono(spans, mono)
                    plines.append((t, is_mono))
                    if CODE_SHAPED.search(t) and not any(MATH_FONT.search(x["font"]) for x in spans):
                        shaped_mono += is_mono; shaped_prop += not is_mono
                    for s in spans:
                        n = len(s["text"].strip())
                        if mono.get(s["font"], False): mono_chars += n
                        else: body_chars += n
            for (t, _), lab in zip(plines, run_rules(plines)):
                labels[t].append(lab)
            rows = []
            for line in (pg.get("text") or "").split("\n"):
                t = norm(line)
                if not t:
                    rows.append([line, None]); continue
                total += 1
                q = labels.get(t)
                if q:
                    lab = q.popleft() if len(q) > 1 else q[0]
                    found += 1; n_mono += bool(lab); rows.append([line, None if lab is None else bool(lab)])
                else:
                    rows.append([line, None])
            out_pages.append({"page_number": pg["page_number"], "lines": rows})
        if mono_chars >= body_chars:
            return "typewriter_body", None
        if total == 0 or found / total < 0.85:
            return "alignment", None
        if shaped_prop >= 5 and shaped_prop >= 0.2 * (shaped_prop + shaped_mono):
            return "code_not_mono", None
        if MODE == "codefree":
            if mono_chars or n_mono:
                return "has_mono", None
            for pg in out_pages:
                pg["lines"] = [[l, None if lab is None else False] for l, lab in pg["lines"]]
            return "kept", {"stem": stem, "pdf": pdf, "doc_pages": len(pages), "segment": "codefree", "pages": out_pages,
                            "matched_share": round(found / total, 3), "code_line_share": 0.0, "mono_fonts": []}
        if MODE == "lowcode":
            if not (mono_chars or n_mono): return "codefree_doc", None
            if n_mono / found >= 0.02: return "code_doc", None
            return "kept", {"stem": stem, "pdf": pdf, "doc_pages": len(pages), "segment": "lowcode", "pages": out_pages,
                            "matched_share": round(found / total, 3), "code_line_share": round(n_mono / found, 4),
                            "mono_fonts": sorted(f for f, m in mono.items() if m)}
        if n_mono / found < 0.02:
            return "no_code", None
        return "kept", {"stem": stem, "pdf": pdf, "doc_pages": len(pages), "segment": "book" if len(pages) >= 60 else ("tiny" if len(pages) < 8 else "short"), "pages": out_pages,
                        "matched_share": round(found / total, 3), "code_line_share": round(n_mono / found, 3),
                        "mono_fonts": sorted(f for f, m in mono.items() if m)}
    except Exception:
        return "error", None


if __name__ == "__main__":
    pdfs = json.load(open(os.path.join(HERE, "pdf_index.json")))
    excl = set()
    for k in filter(None, os.environ.get("EXCLUDE_KEYS", "").split(",")):
        excl |= {json.loads(l)["stem"] for l in open(k)}
    excl |= {b["stem"] for b in json.load(open(os.path.join(HERE, "answer_key.json")))["books"]}
    names = sorted(e.name[:-5] for e in os.scandir(RAW) if e.name.endswith(".json"))
    stems = [n for n in names if (n not in pdfs) == (MODE == "transcript") and n not in excl]
    random.Random(SEED).shuffle(stems)
    skips, kept, tried = {}, 0, 0
    with Pool(WORKERS) as pool, open(OUT, "w") as fh:
        for b0 in range(0, len(stems), 64):                 # fixed batches: no pool.terminate() mid-iteration
            for why, rec in pool.map(label, [(s, pdfs.get(s)) for s in stems[b0:b0 + 64]]):
                tried += 1
                skips[why] = skips.get(why, 0) + 1
                if rec and kept < TARGET:
                    fh.write(json.dumps(rec) + "\n"); fh.flush(); kept += 1
                    print(f"{kept:>4} kept  tried {tried}  pages {rec['doc_pages']:>4}  {rec['segment']}  {rec['stem'][:50]!r}", flush=True)
            if kept >= TARGET:
                break
    json.dump({"tried": tried, "kept": kept, "skips": skips}, open(OUT + ".meta.json", "w"))
    print("tried", tried, "kept", kept, "skips", skips)
