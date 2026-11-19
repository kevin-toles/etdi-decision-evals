"""Step 2 scorer: derives the three sets from the two blind raw-text reads (read 1 research_<b>.json, claude-opus-5-5;
read 2 research2_<b>.json, claude-opus-4-8, with its validated make-up applied as in compare_reads.py). Only text-derived
span kinds and boundaries are used. Per item, each read gives its own answer; the item is DECIDED only when both answers
are equal and no line is uncovered, otherwise UNRESOLVED (no majority, no tie-break, panel labels never used to decide).
  1. gold lines (600): answer = code | not_code (noncode_monospace and prose are both not_code; the three-way kind is kept).
     The earlier panel label is reported alongside for comparison only.
  2. bad-block causes (668), from the block's non-blank lines and the code spans each read drew around them:
       all_prose          every line prose
       noncode_monospace  no code line, at least one noncode_monospace line
       code_plus_prose_edge  code lines plus prose/noncode lines
       actually_code      all code, lines = exactly one code block (span chain across page breaks via continues)
       split_fragment     all code, strictly inside one code block
       merged_blocks      all code, lines from two or more code blocks
     terminal output/log cannot be told apart from the line kinds (command output shown with its command is `code` by the
     instructions), so it is not re-decided; the earlier panel cause is reported alongside.
  3. good/bad code-block examples: GOOD = code blocks both reads drew with the same kind and identical boundaries;
     BAD = monospace look-alikes both reads drew identically as noncode_monospace blocks, plus bad-block items both reads
     decided as all_prose / noncode_monospace (not code at all) or split_fragment / code_plus_prose_edge / merged_blocks
     (code with wrong boundaries). Each example carries its doc, page, lines, text and why.
    python3 score_sets.py <dir>"""
import collections, glob, json, os, sys, unicodedata
R = sys.argv[1]; CL = os.path.dirname(os.path.abspath(R.rstrip("/")))
loose = lambda t: " ".join("".join(" " if unicodedata.category(c) == "Zs" else ("" if unicodedata.category(c) in ("Cc", "Cf", "Co") else c) for c in unicodedata.normalize("NFKC", t or "")).split())
MK = {}
mv = json.load(open(os.path.join(R, "makeup2_validation.json")))["entries"]; mi = {e["id"]: e for e in json.load(open(os.path.join(R, "makeup2_index.json")))["entries"]}
for f in glob.glob(os.path.join(R, "makeup2_research_M*.json")):
    m = json.load(open(f), strict=False)
    for x in m.get("recites", []) + [dict(s, id=g["id"]) for g in m.get("gaps", []) for s in g.get("spans", [])]:
        e = mi.get(x.get("id"))
        if e and mv.get(e["id"], {}).get("ok"): MK.setdefault(e["batch"], []).append((e, dict(x, doc=e["doc"], page=e["page"])))
def spans(path, pages, batch=None):
    sp = json.load(open(path), strict=False).get("spans", []); mk = MK.get(batch, []) if batch else []
    drop = {e["span_index"] for e, _ in mk if e["type"] == "RECITE"}
    sp = [s for i, s in enumerate(sp) if i not in drop] + [x for e, x in mk if e["type"] == "RECITE"] + [x for e, x in mk if e["type"] == "GAP"]
    line = {}; good = []
    for j, s in enumerate(sp):
        key = (s.get("doc"), s.get("page")); a, z = s.get("line_start"), s.get("line_end")
        if key not in pages or not isinstance(a, int) or not isinstance(z, int): continue
        for n in range(a, z + 1):
            if n in pages[key] and (key, n) not in line: line[(key, n)] = (s.get("kind"), j)
        good.append((j, s))
    # block id: chain spans with continues=true to the first span on the next page of the same document
    blk = {j: j for j, _ in good}; by = {j: s for j, s in good}
    for j, s in good:
        if s.get("continues") and s.get("kind") == "code":
            nxt = [(t.get("line_start"), k) for k, t in good if t.get("doc") == s.get("doc") and t.get("page") == s.get("page", 0) + 1 and t.get("kind") == s.get("kind")]
            if nxt: blk[min(nxt)[1]] = blk[j]
    def root(j):
        while blk[j] != j: j = blk[j]
        return j
    line = {k: (kd, root(j)) for k, (kd, j) in line.items()}
    members = collections.defaultdict(set)
    for k, (kd, b) in line.items(): members[b].add(k)
    return line, members, by
def lines_of(it, pages, doc):
    if it["page_start"] == it["page_end"]:
        return [((doc, it["page_start"]), n) for n in range(it["line_start"], it["line_end"] + 1) if n in pages.get((doc, it["page_start"]), {})]
    return [((doc, it["page_start"]), n) for n in sorted(pages.get((doc, it["page_start"]), {})) if n >= it["line_start"]] + \
           [((doc, it["page_end"]), n) for n in sorted(pages.get((doc, it["page_end"]), {})) if n <= it["line_end"]]
def cause(L, line, members):
    ks = [line.get(x, (None, None))[0] for x in L]
    if not L or None in ks: return "uncovered"
    if all(k == "prose" for k in ks): return "all_prose"
    if "code" not in ks: return "noncode_monospace"
    if any(k != "code" for k in ks): return "code_plus_prose_edge"
    bl = {line[x][1] for x in L}
    if len(bl) > 1: return "merged_blocks"
    return "actually_code" if set(L) == members[bl.pop()] else "split_fragment"
panel = json.load(open(os.path.join(CL, "gold_panel_2026-11-17", "panel_results.json")))["per_item"]
pcause = json.load(open(os.path.join(CL, "bad_block_causes_2026-11-17", "causes_results.json")))["per_item"]
gold, blocks, good, bad = {}, {}, [], []
for f in sorted(glob.glob(os.path.join(R, "sheet_B*.json"))):
    b = os.path.basename(f)[6:-5]; sheet = json.load(open(f))
    pages = {(d["doc"], p["page"]): {l["n"]: l["text"] for l in p["lines"] if loose(l["text"])} for d in sheet["documents"] for p in d["pages"]}
    l1, m1, s1 = spans(os.path.join(R, f"research_{b}.json"), pages); l2, m2, s2 = spans(os.path.join(R, f"research2_{b}.json"), pages, b)
    text = lambda L: [pages[k][n] for k, n in L]
    for d in sheet["documents"]:
        for it in d["items"]:
            L = lines_of(it, pages, d["doc"]); where = {"batch": b, "doc": d["doc"], "page_start": it["page_start"], "line_start": it["line_start"], "page_end": it["page_end"], "line_end": it["line_end"]}
            if it["kind"] == "line":
                k1 = [l1.get(x, ("uncovered",))[0] for x in L]; k2 = [l2.get(x, ("uncovered",))[0] for x in L]
                a1 = "uncovered" if "uncovered" in k1 or not L else ("code" if "code" in k1 else "not_code"); a2 = "uncovered" if "uncovered" in k2 or not L else ("code" if "code" in k2 else "not_code")
                gold[it["item"]] = dict(where, read1_kind=k1, read2_kind=k2, read1=a1, read2=a2, outcome="invisible_only_line" if not L else (a1 if a1 == a2 and a1 != "uncovered" else "unresolved"),
                                        kind_outcome=k1[0] if k1 == k2 and len(set(k1)) == 1 and k1[0] != "uncovered" else "unresolved", panel=panel.get(it["item"], {}).get("final"), text=text(L))
            else:
                c1, c2 = cause(L, l1, m1), cause(L, l2, m2)
                blocks[it["item"]] = dict(where, read1=c1, read2=c2, outcome=c1 if c1 == c2 and c1 != "uncovered" else "unresolved", panel=pcause.get(it["item"], {}).get("final"), text=text(L))
                o = blocks[it["item"]]["outcome"]
                if o in ("all_prose", "noncode_monospace", "split_fragment", "code_plus_prose_edge", "merged_blocks"):
                    bad.append(dict(where, source="bad_block_item", item=it["item"], why=o, line_refs=[[k[1], n] for k, n in L], text=text(L)))
    # identical blocks in both reads (same kind, same member lines)
    for b1, mem in m1.items():
        kd = l1[next(iter(mem))][0]
        if kd not in ("code", "noncode_monospace"): continue
        x = next(iter(mem)); b2 = l2.get(x, (None, None))[1]
        if b2 is None or m2[b2] != mem or l2[x][0] != kd: continue
        L = sorted(mem, key=lambda k: (k[0][1], k[1]))
        ex = {"batch": b, "doc": L[0][0][0], "page_start": L[0][0][1], "line_start": L[0][1], "page_end": L[-1][0][1], "line_end": L[-1][1], "lines": len(L), "line_refs": [[k[1], n] for k, n in L], "text": text(L)}   # line_refs: the block's own lines; a block chained over a page break skips page furniture between its parts
        (good if kd == "code" else bad).append(dict(ex, source="both_reads_identical_block", why="code block, boundaries agreed" if kd == "code" else "noncode_monospace block (code look-alike), boundaries agreed"))
C = collections.Counter
res = {"gold_lines": {"items": len(gold), "outcome": dict(C(v["outcome"] for v in gold.values())), "kind_outcome": dict(C(v["kind_outcome"] for v in gold.values())),
                      "decided_vs_panel": dict(C(f"{v['outcome']}|panel:{v['panel']}" for v in gold.values() if v["outcome"] != "unresolved")),
                      "unresolved_reads": dict(C(f"{v['read1']}|{v['read2']}" for v in gold.values() if v["outcome"] == "unresolved"))},
       "bad_block_causes": {"items": len(blocks), "outcome": dict(C(v["outcome"] for v in blocks.values())),
                            "decided_vs_panel": dict(C(f"{v['outcome']}|panel:{v['panel']}" for v in blocks.values() if v["outcome"] != "unresolved")),
                            "unresolved_reads": dict(C(f"{v['read1']}|{v['read2']}" for v in blocks.values() if v["outcome"] == "unresolved"))},
       "examples": {"good": len(good), "bad": len(bad), "bad_by_why": dict(C(x["why"] for x in bad)), "good_lines": sum(x["lines"] for x in good)}}
json.dump({"summary": res, "gold_lines": gold, "bad_block_causes": blocks}, open(os.path.join(R, "step2_sets.json"), "w"), indent=1, ensure_ascii=False)
with open(os.path.join(R, "step2_block_examples.jsonl"), "w") as o:
    for x in good: o.write(json.dumps(dict(x, label="good"), ensure_ascii=False) + "\n")
    for x in bad: o.write(json.dumps(dict(x, label="bad"), ensure_ascii=False) + "\n")
print(json.dumps(res, indent=1))
