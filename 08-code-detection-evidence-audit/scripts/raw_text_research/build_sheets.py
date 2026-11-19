"""Raw-text research, step 2 sheets. Locates every item (600 gold lines, 668 bad blocks) in its document's raw JSON
(collections/*/raw/<stem>.json, page_number + text split on newlines, lines numbered from 1 per page) by its own text
and surrounding lines -- not by page number, which differs between the answer key and the raw JSON for some
documents. Pages read = each item's raw page plus one page either side. Batches of about 20 pages keep a document's
pages together. Each sheet holds the numbered page text, the items located on those pages (as pointers only: no panel
label, no font label, no candidate class) and step 1's leads for those items with their context.
    python3 build_sheets.py <code_label_audit_dir> <out_dir>"""
import collections, json, os, sys
CL, OUT = sys.argv[1:3]
COLL = "<CORPUS_ROOT>/collections"
raw = {}
for c in sorted(os.listdir(COLL)):
    d = os.path.join(COLL, c, "raw")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"): raw.setdefault(f[:-5], os.path.join(d, f))
S = lambda x: x.strip()
gidx = json.load(open(os.path.join(CL, "gold_panel_2026-11-17", "round1_index.json")))
gsheet = {x["id"]: x for p in "AB" for x in json.load(open(os.path.join(CL, "gold_panel_2026-11-17", f"round1_sheet_{p}.json")))["items"]}
bc = json.load(open(os.path.join(CL, "bad_block_causes_2026-11-17", "causes_results.json")))["per_item"]
bsheet = {x["id"]: x for p in "AB" for x in json.load(open(os.path.join(CL, "bad_block_causes_2026-11-17", f"round1_sheet_{p}.json")))["items"]}
items = []
for iid, v in gidx.items():
    s = gsheet[iid]; items.append({"id": iid, "kind": "line", "stem": v["stem"], "seq": [s["TARGET"]], "before": s["before"], "after": s["after"]})
for iid, v in bc.items():
    s = bsheet[iid]; items.append({"id": iid, "kind": "block", "stem": v["stem"], "seq": s["BLOCK"], "before": s["before"], "after": s["after"]})
docs = {}
def doc(stem):
    if stem not in docs:
        d = json.load(open(raw[stem])); docs[stem] = [(p["page_number"], p["text"].split("\n")) for p in d["pages"]]
    return docs[stem]
located, unlocated = [], []
for it in items:
    flat = [(pn, i + 1, l) for pn, L in doc(it["stem"]) for i, l in enumerate(L)]
    nb = [k for k, (_, _, l) in enumerate(flat) if S(l)]          # non-blank positions
    texts = [S(flat[k][2]) for k in nb]; seq = [S(x) for x in it["seq"] if S(x)]
    best = None
    for j in range(len(texts) - len(seq) + 1):
        if texts[j:j + len(seq)] != seq: continue
        score = sum(S(a) == b for a, b in zip(reversed(it["before"]), reversed(texts[max(0, j - len(it["before"])):j]))) + \
                sum(S(a) == b for a, b in zip(it["after"], texts[j + len(seq):j + len(seq) + len(it["after"])]))
        if best is None or score > best[0]: best = (score, j)
    if best is None: unlocated.append(it["id"]); continue
    a, z = nb[best[1]], nb[best[1] + len(seq) - 1]
    it.update({"raw_path": raw[it["stem"]], "page_start": flat[a][0], "line_start": flat[a][1], "page_end": flat[z][0], "line_end": flat[z][1], "context_score": best[0]})
    located.append(it)
# step 1 leads (pointers to corroborate), top 4 per item, with context
leads = collections.defaultdict(list)
mp = os.path.join(CL, "evidence_coverage_2026-11-17", "matches.jsonl")
CAP = {"CRE": 2, "corpus": 2, "ETL_raw": 1}                       # a varied set per item, not the first hits
seen_repo = collections.defaultdict(set); taken = collections.defaultdict(collections.Counter)
if os.path.exists(mp):
    for l in open(mp):
        r = json.loads(l)
        if not r.get("context") or taken[r["item"]][r["source"]] >= CAP[r["source"]]: continue
        if r["source"] == "CRE":
            repo = "/".join(r["path"].split("/")[5:8])                  # <domain>/<group>/<repo> under the CRE root
            if repo in seen_repo[r["item"]]: continue
            seen_repo[r["item"]].add(repo)
        taken[r["item"]][r["source"]] += 1
        leads[r["item"]].append({"lead_id": f"{r['item']}-L{len(leads[r['item']]) + 1}", "source": r["source"],
                                 "where": r.get("path") or r.get("raw_path"), "line_or_chapter": r.get("line") or r.get("ref"),
                                 "page": r.get("page"), "matched": r.get("matched_text") or r.get("matched_line"), "context": r["context"],
                                 "flags": {k: r[k] for k in ("doc_file", "in_comment_or_docstring", "contiguous_run") if k in r}})
pages = collections.defaultdict(set)
for it in located:
    have = {pn for pn, _ in doc(it["stem"])}
    for p in range(it["page_start"] - 1, it["page_end"] + 2):
        if p in have: pages[it["stem"]].add(p)
MAXP, MAXC = 20, 120_000                                         # per batch: at most 20 pages and ~120K characters
batches, cur, n, c = [], [], 0, 0
for stem in sorted(pages):
    D = dict(doc(stem)); ps = sorted(pages[stem]); chunk, cc = [], 0
    for p in ps:
        pc = sum(len(t) + 1 for t in D[p])
        if chunk and (len(chunk) >= MAXP or cc + pc > MAXC):
            if cur and (n + len(chunk) > MAXP or c + cc > MAXC): batches.append(cur); cur, n, c = [], 0, 0
            cur.append((stem, chunk)); n += len(chunk); c += cc; chunk, cc = [], 0
        chunk.append(p); cc += pc
    if chunk:
        if cur and (n + len(chunk) > MAXP or c + cc > MAXC): batches.append(cur); cur, n, c = [], 0, 0
        cur.append((stem, chunk)); n += len(chunk); c += cc
if cur: batches.append(cur)
os.makedirs(OUT, exist_ok=True); index = {}
for b, chunks in enumerate(batches, 1):
    bid = f"B{b:03d}"; sheet = {"batch": bid, "documents": []}
    for stem, chunk in chunks:
        D = dict(doc(stem)); its = [it for it in located if it["stem"] == stem and it["page_start"] in chunk]
        sheet["documents"].append({"doc": stem, "raw_path": raw[stem],
            "pages": [{"page": p, "lines": [{"n": i + 1, "text": t} for i, t in enumerate(D[p])]} for p in chunk],
            "items": [{"item": it["id"], "kind": it["kind"], "page_start": it["page_start"], "line_start": it["line_start"],
                       "page_end": it["page_end"], "line_end": it["line_end"], "leads": leads.get(it["id"], [])} for it in its]})
        for it in its: index[it["id"]] = {"batch": bid, **{k: it[k] for k in ("stem", "kind", "raw_path", "page_start", "line_start", "page_end", "line_end", "context_score")}}
    json.dump(sheet, open(os.path.join(OUT, f"sheet_{bid}.json"), "w"), indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, f"sheet_{bid}.txt"), "w") as fh:          # the agents' reading copy (same content)
        fh.write(f"BATCH {bid}\n")
        for d in sheet["documents"]:
            fh.write(f"\n######## DOCUMENT: {d['doc']}\n######## raw_path: {d['raw_path']}\n")
            for pg in d["pages"]:
                fh.write(f"\n=== page {pg['page']} ===\n")
                for ln in pg["lines"]: fh.write(f"p{pg['page']} L{ln['n']:>3} | {ln['text']}\n")
            fh.write("\n--- ITEMS (pointers only: places your spans must cover) ---\n")
            for it in d["items"]:
                fh.write(f"{it['item']} [{it['kind']}] page {it['page_start']} line {it['line_start']} to page {it['page_end']} line {it['line_end']}\n")
                for ld in it["leads"]:
                    fh.write(f"  LEAD {ld['lead_id']} source={ld['source']} where={ld['where']} at={ld['line_or_chapter']}"
                             f"{' page=' + str(ld['page']) if ld.get('page') else ''} flags={ld['flags']}\n    matched: {ld['matched']}\n")
                    for cl in ld["context"]: fh.write(f"    | {cl}\n")
json.dump({"index": index, "unlocated": unlocated, "batches": len(batches), "pages": sum(len(v) for v in pages.values()),
           "documents": len(pages)}, open(os.path.join(OUT, "sheet_index.json"), "w"), indent=1)
print({"items": len(items), "located": len(located), "unlocated": len(unlocated), "documents": len(pages),
       "pages": sum(len(v) for v in pages.values()), "batches": len(batches), "items_with_leads": sum(1 for it in located if leads.get(it["id"]))})
