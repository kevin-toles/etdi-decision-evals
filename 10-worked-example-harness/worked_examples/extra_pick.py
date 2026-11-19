"""A2 / A3 worked examples, step 1: pick real chapters from named theory-library (TF) and SE books — per book, the
chapters with the most mentions of the question's terms (top 2) — to be embedded and filed. Read-only.
    python3 -I <this> <out.json>"""
import json, os, re, sys
C = "<CORPUS_ROOT>/collections"
PICK = {
 "A3": {"rx": r"epidemic|gossip|SIR model|spreading", "books": [
    ("theoretical-foundations", "Complex Networks Structure Robustness and Function"), ("theoretical-foundations", "A First Course in Network Science"),
    ("theoretical-foundations", "Epidemic Processes in Complex Networks")]},
 "A2": {"rx": r"Huffman|prefix code|entropy", "books": [
    ("theoretical-foundations", "Data Compression"), ("theoretical-foundations", "Elements of Information Theory"),
    ("theoretical-foundations", "Fundamentals of Information Theory and Coding")]},
}
out = {}
for q, spec in PICK.items():
    rx = re.compile(spec["rx"], re.I); out[q] = []
    for lib, book in spec["books"]:
        p = f"{C}/{lib}/raw/{book}.json"
        if not os.path.exists(p): print("missing", p); continue
        d = json.load(open(p)); pages = {}
        for pg in d.get("pages") or []:
            try: pages[int(pg.get("page_number"))] = pg.get("text") or ""
            except Exception: pass
        rows = []
        for c in d.get("chapters") or []:
            s, e = c.get("start_page") or 0, c.get("end_page") or 0
            t = "\n".join(pages.get(i, "") for i in range(s, e + 1))
            if not t or len(t) > 600_000: continue
            rows.append({"lib": lib, "book": book, "chapter": (c.get("title") or "")[:90], "pages": f"{s}-{e}", "mentions": len(rx.findall(t)), "chars": len(t)})
        out[q] += sorted(rows, key=lambda r: -r["mentions"])[:2]
json.dump(out, open(sys.argv[1], "w"), indent=1)
for q, v in out.items():
    for r in v: print(q, r["book"][:50], "|", r["chapter"][:40], r["pages"], r["mentions"], r["chars"])
