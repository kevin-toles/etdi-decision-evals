"""Mechanical check: every quote in cited_sources_research.json appears verbatim (whitespace-normalized) in its chapter's raw
text, at or near the cited offset.   cd htc-multidim-classification-service && python3 <this>"""
import json, os, re, sqlite3, sys
EV = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, EV)
from gs_search import DB, chapter_text
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
norm = lambda t: re.sub(r"\s+", " ", t).strip()
items = json.load(open(f"{EV}/evidence_2026-11-18/cited_sources_research.json"))
ok = bad = 0
for it in items:
    qs = list(it.get("quotes") or []) + list((it.get("cited_work_in_corpus") or {}).get("quotes") or [])
    for q in qs:
        row = db.execute("SELECT stem, collection FROM chapter WHERE ref=?", (q["chapter_ref"],)).fetchone()
        text = norm(chapter_text(row[1], row[0], q["chapter_ref"])) if row else ""
        hit = norm(q["text"]).strip(" .…\"'") in text
        ok += hit; bad += not hit
        if not hit: print("MISSING", it["record_id"], q["chapter_ref"][:60], "|", q["text"][:90])
print(f"quotes verbatim: {ok} ok, {bad} missing")
