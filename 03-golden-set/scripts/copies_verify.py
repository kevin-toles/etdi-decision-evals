"""Golden set (OQ#18), user decision 2026-11-18 copies (b): a copy of a graded chapter takes its grade only when verified
by full-text comparison. Pre-registered rule: the copy chapter contains >= 90% of the graded chapter's 8-word shingles
AND every evidence span (8-word shingles, >= 90%). Text is read from the raw JSON (gs_search.chapter_text), normalized
(lower-case, alphanumeric words). Writes copies_verified.jsonl.   cd htc-multidim-classification-service && python3 <this>"""
import json, os, re, sqlite3, sys
EV = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, EV); sys.path.insert(0, os.getcwd())
from gs_search import DB, chapter_text
THRESH, K = 0.90, 8
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
def loc(ref):
    row = db.execute("SELECT stem, collection FROM chapter WHERE ref=?", (ref,)).fetchone(); return row
def sh(t):
    w = re.findall(r"[a-z0-9]+", t.lower()); return {" ".join(w[i:i + K]) for i in range(max(0, len(w) - K + 1))}
cache = {}
def text(ref):
    if ref not in cache:
        l = loc(ref)
        try: cache[ref] = chapter_text(l[1], l[0], ref) if l else None
        except FileNotFoundError: cache[ref] = None          # raw file renamed or removed since the index was built
    return cache[ref]
recs = [json.loads(l) for l in open(f"{EV}/records_pilot_graded.jsonl")] + [json.loads(l) for l in open(f"{EV}/records_full_graded.jsonl")]
out = open(f"{EV}/copies_verified.jsonl", "w"); n = v = miss = 0
for r in recs:
    if not r.get("copies"): continue
    g = text(r["chapter_ref"]); gs = sh(g or "")
    spans = [sh(e["text"]) for e in r.get("evidence") or [] if e.get("text")]
    for c in r["copies"]:
        n += 1; t = text(c["ref"])
        if t is None or not gs: miss += 1; ok, cont, span_min = False, None, None
        else:
            cs = sh(t); cont = len(gs & cs) / len(gs)
            span_min = min((len(s & cs) / len(s) for s in spans if s), default=None)
            ok = cont >= THRESH and (span_min is None or span_min >= THRESH)
        v += ok
        out.write(json.dumps({"record_id": r["record_id"], "qid": r["qid"], "graded_ref": r["chapter_ref"], "copy_ref": c["ref"],
                              "grade": r["panel"]["grade"], "containment": cont, "evidence_min": span_min, "verified": ok}) + "\n")
print(f"copy refs {n} | verified {v} | unreadable {miss} | threshold {THRESH} on {K}-word shingles")
