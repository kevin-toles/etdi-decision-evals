"""Second make-up round: entries of makeup2_index.json that failed validate_makeup2.py or were left unanswered get a
copy with id suffix -r2 on sheet M07 (same text format as build_makeup2.py). The failed first answers stay unapplied.
    python3 build_makeup2_round2.py <dir>"""
import json, os, sys
R = sys.argv[1]; ix = json.load(open(os.path.join(R, "makeup2_index.json"))); v = json.load(open(os.path.join(R, "makeup2_validation.json")))
redo = [e for e in ix["entries"] if not e["id"].endswith("-r2") and not v["entries"].get(e["id"], {}).get("ok")]
pages = {}
for e in redo: pages.setdefault((e["batch"], e["doc"], e["page"]), []).append(dict(e, id=e["id"] + "-r2"))
out = []
for (b, doc, pg), es in pages.items():
    L = {(d["doc"], p["page"]): p["lines"] for d in json.load(open(os.path.join(R, f"sheet_{b}.json")))["documents"] for p in d["pages"]}[(doc, pg)]
    out.append(f"######## PAGE: batch {b} | DOCUMENT: {doc} | page {pg}")
    for e in es:
        x = e["span_as_written"]
        out.append(f"--- RECITE {e['id']}: span as written lines {x.get('line_start')}-{x.get('line_end')} kind {x.get('kind')}; failing {', '.join(e['failing'])}")
        out.append(f"    quote_first as written | {x.get('quote_first')}"); out.append(f"    quote_last as written  | {x.get('quote_last')}")
        if x.get("note"): out.append(f"    note as written | {x.get('note')}")
    out += [f"p{pg} L{l['n']} | {l['text']}" for l in L] + [""]
    ix["entries"] += es; ix["index"].append({"sheet": "M07", "batch": b, "doc": doc, "page": pg, "entries": [e["id"] for e in es]})
assert all(e["type"] == "RECITE" for e in redo)
open(os.path.join(R, "makeup2_M07.txt"), "w").write("\n".join(out)); json.dump(ix, open(os.path.join(R, "makeup2_index.json"), "w"), indent=1, ensure_ascii=False)
print(len(redo), "entries on", len(pages), "pages:", [e["id"] for e in redo])
