"""Worked examples, step 1: one keyword scan of the same 20,000 random SE books as C1 (seed 1112) collecting candidate
chapters for every open question whose options change search results. Search would choose by meaning over all 3.5M
chapters; the scan only assembles a real candidate pool, which embed_pools.py then embeds with the platform's model.
Per question: chapters matching ANY of its terms, ranked by total mentions, top 120 (chapters > 600k characters left
out: chapter-boundary defects, OQ#50). Read-only.   python3 <this> <out.json>"""
import json, os, random, re, sys
ROOT = "<CORPUS_ROOT>/collections/software-engineering/raw"
Q = {
 "A1": [r"quantum error correction", r"surface codes?", r"stabili[sz]er codes?", r"logical qubits?"],
 "A3": [r"gossip(-based)? protocols?", r"epidemic (broadcast|protocol|dissemination)", r"\bSWIM\b protocol", r"membership (protocol|changes?|list)"],
 "A5": [r"consumer groups?", r"(partition|consumer) rebalanc\w*", r"rebalanc\w* (protocol|listener|the consumer)"],
 "A7": [r"xml\.etree|ElementTree", r"\blxml\b", r"xml\.dom\.minidom|xml\.sax", r"defusedxml", r"\bXXE\b|XML external entit(y|ies)"],
 "A9": [r"bloom filters?", r"false[- ]positive (rate|probability)"],
 "A10": [r"\+-{8,}\+", r"SHOW TABLES", r"[┌└├│─]{3,}"],
 "A11": [r"\bRAG\b", r"retrieval[- ]augmented generation", r"chunking strateg\w*", r"chunk (size|overlap)"],
 "B3": [r"idempoten(t|cy)", r"idempotent (consumer|receiver|handler)", r"exactly[- ]once (processing|delivery|semantics)", r"deduplicat\w+ (of )?messages?"],
 "B5": [r"reward hacking", r"reward (model )?(over-?optimi[sz]ation|exploitation|gaming)", r"specification gaming"],
 "B6": [r"Gameplay Ability System|GameplayAbility|GameplayEffect", r"Unreal Engine", r"ability system"],
 "D1": [r"aws:SourceIp", r"\"Condition\"\s*:", r"IpAddress"],
 "E3": [r"knowledge graphs?", r"GraphRAG|graph RAG|graph-based retrieval", r"hybrid (retrieval|search)", r"vector (search|database|store)"],
}
RX = {q: [re.compile(t, re.I if q not in ("A10",) else 0) for t in ts] for q, ts in Q.items()}
REQ = {"A11": 0, "E3": 0, "A5": 0, "A9": 0}   # questions whose first term must match (keeps the pool on-question)
files = [e.path for e in os.scandir(ROOT) if e.name.endswith(".json")]
random.seed(1112); sample = random.sample(files, int(sys.argv[2]) if len(sys.argv) > 2 else 20000)
hits = {q: [] for q in Q}
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
        s, e = (c.get("start_page") or 0), (c.get("end_page") or 0)
        txt = "\n".join(pages.get(i, "") for i in range(s, e + 1))
        if not txt or len(txt) > 600_000: continue
        for q, rxs in RX.items():
            counts = [len(rx.findall(txt)) for rx in rxs]
            if not sum(counts) or (q in REQ and not counts[REQ[q]]): continue
            m = next(rx.search(txt) for rx, k in zip(rxs, counts) if k)
            a, b = max(0, m.start() - 200), min(len(txt), m.end() + 200)
            hits[q].append({"book": book, "chapter": (c.get("title") or "")[:90], "pages": f"{s}-{e}", "counts": counts,
                            "mentions": sum(counts), "chars": len(txt), "snippet": " ".join(txt[a:b].split())})
out = {"books_scanned": len(sample), "of": len(files), "terms": Q,
       "pools": {q: sorted(v, key=lambda x: -x["mentions"])[:120] for q, v in hits.items()},
       "chapter_counts": {q: len(v) for q, v in hits.items()}}
json.dump(out, open(sys.argv[1], "w"), indent=1); print("done", out["chapter_counts"])
