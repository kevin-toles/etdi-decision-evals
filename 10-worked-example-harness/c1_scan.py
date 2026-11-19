"""C1 (#40) worked example: real SE chapters for "How should I rotate database credentials?" — a keyword scan over a
random SE raw sample stands in for search (the stores are empty). Per term: chapters ranked by mentions, with book,
chapter title, mentions and a snippet. Read-only.   python3 <this> <n_books> <out.json>"""
import json, os, random, re, sys, itertools, collections
ROOT = "<CORPUS_ROOT>/collections/software-engineering/raw"
N = int(sys.argv[1])
TERMS = {
    "credential_rotation": r"(credential|secret|password|key)s? rotation|rotat\w* (the |your |of )?(database |db )?(credentials?|secrets?|passwords?)",
    "dynamic_secrets": r"dynamic secrets?",
    "vault": r"HashiCorp Vault|Vault (server|agent|secrets? engine|policy|token)",
    "secrets_manager": r"AWS Secrets Manager|Azure Key Vault|Google Secret Manager|GCP Secret Manager",
    "database_credentials": r"database (user )?credentials|DB credentials",
    "short_lived": r"short[- ]lived (credentials?|tokens?|certificates?)",
}
RX = {k: re.compile(v, re.I) for k, v in TERMS.items()}
files = [e.path for e in os.scandir(ROOT) if e.name.endswith(".json")]
random.seed(1112); sample = random.sample(files, N)
hits = {k: [] for k in TERMS}
for n, p in enumerate(sample):
    if n % 2000 == 0: print(n, flush=True)
    try: d = json.load(open(p))
    except Exception: continue
    pages = {}
    for pg in d.get("pages") or []:
        try: pages[int(pg.get("page_number"))] = pg.get("text") or ""
        except Exception: pass
    chs = d.get("chapters") or [{"title": "(whole)", "start_page": min(pages or [0]), "end_page": max(pages or [0])}]
    book = os.path.basename(p)[:-5]
    for c in chs:
        txt = "\n".join(pages.get(i, "") for i in range((c.get("start_page") or 0), (c.get("end_page") or 0) + 1))
        if not txt: continue
        for k, rx in RX.items():
            ms = rx.findall(txt)
            if ms:
                m = rx.search(txt); a, b = max(0, m.start() - 200), min(len(txt), m.end() + 200)
                hits[k].append({"book": book, "chapter": (c.get("title") or "")[:90], "pages": f"{c.get('start_page')}-{c.get('end_page')}",
                                "mentions": len(ms), "chars": len(txt), "snippet": " ".join(txt[a:b].split())})
out = {"books_scanned": N, "of": len(files), "terms": {k: sorted(v, key=lambda x: -x["mentions"])[:40] for k, v in hits.items()},
       "chapter_counts": {k: len(v) for k, v in hits.items()}}
json.dump(out, open(sys.argv[2], "w"), indent=1); print("done", out["chapter_counts"])
