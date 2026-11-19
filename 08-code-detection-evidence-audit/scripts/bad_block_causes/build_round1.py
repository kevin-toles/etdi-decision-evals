"""Bad-block causes, round 1: every test-document block that option 1 (HGB + gate, balanced) or option 6 (blend +
kind recognisers, strict; UniXcoder seed 202) counts as bad (no font-labelled code line, at least one labelled line).
Thresholds are re-derived exactly as in worked_examples/a4_options.py (phase D scorer, tune half). Blocks found by
both options are one item. Sheets show the JSON lines only: title, pages, 3 lines before, the BLOCK, 3 lines after.
round1_index.json keeps stem, line range, segment, options and font labels out of the sheets.
    cd Code-Orchestrator-Service && python3 build_round1.py <work_dir> <out_dir>"""
import collections, json, os, pickle, random, sys
W, BOUT = sys.argv[1], sys.argv[2]
src = open(os.path.join(W, "options_phase_d.py")).read().split("\ndef main():")[0]
for c in [('if os.path.exists(os.path.join(S, "encoder_probs_distilbert.pkl")):\n'
           '    SRC["distil"] = pickle.load(open(os.path.join(S, "encoder_probs_distilbert.pkl"), "rb"))\n'
           '    SRC["blend hgb+distil"] = {k: 0.5 * SRC["hgb"][k] + 0.5 * SRC["distil"][k] for k in SRC["hgb"] if k in SRC["distil"]}\n'),
          ('SRC["hgb+S0"] = restack(SRC["hgb"], False, "hgb+S0")\n'
           'SRC["hgb+KR"] = restack(SRC["hgb"], True, "hgb+KR")\n'
           'if "blend hgb+distil" in SRC:\n'
           '    SRC["blend+KR"] = restack(SRC["blend hgb+distil"], True, "blend+KR")\n')]:
    assert src.count(c) == 1; src = src.replace(c, "")
__file__ = os.path.join(W, "options_phase_d.py"); exec(src, globals())
enc = pickle.load(open(os.path.join(W, "encoder_probs_unixcoder_s202.pkl"), "rb"))
SRC["blend"] = {k: 0.5 * SRC["hgb"][k] + 0.5 * enc[k] for k in SRC["hgb"] if k in enc}
SRC["blend+KR"] = restack(SRC["blend"], True, "blend+KR")
keeps = {}
for name, s_, pt in (("option 1", "hgb", "G+O1<=15%"), ("option 6", "blend+KR", "G+O1<=10%")):
    gate, _ = make_gate(s_, False); ch = choose(s_, gate); t, tr, h = ch.pop("_points")["gate"][pt]
    keeps[name] = sel(s_, t, tr, gate, h); log(name, t, tr, h)
blocks = {}
for s, docs in segs.items():
    for b in docs:
        st = b["stem"]
        if half(st) != 1: continue
        code, prose = LAB[st]
        for name, keep in keeps.items():
            for idx in keep(st):
                idx = tuple(int(i) for i in idx); nc, npr = int(code[list(idx)].sum()), int(prose[list(idx)].sum())
                if nc == 0 and npr > 0:
                    e = blocks.setdefault((st, idx), {"stem": st, "segment": s, "lines": list(idx), "options": [], "font_prose": npr,
                                                      "font_unlabelled": len(idx) - npr})
                    e["options"].append(name)
def page_of(st):
    out, j = {}, 0
    for k, pg in enumerate(DOCS[st]["pages"]):
        if k: j += 1
        for _ in pg["lines"]: out[j] = pg.get("page", k + 1); j += 1
    return out
items, index = [], {}
for n, ((st, idx), e) in enumerate(sorted(blocks.items(), key=lambda x: (x[0][0], x[0][1][0])), 1):
    L = DOCS[st]["_t"][1]; po = page_of(st); a, z = idx[0], idx[-1]
    nb = lambda r: [L[i] for i in r if L[i].strip()]
    iid = f"K{n:04d}"; pages = sorted({po.get(i) for i in idx if po.get(i) is not None})
    items.append({"id": iid, "book": st, "pages": pages, "before": nb(range(max(0, a - 6), a))[-3:], "BLOCK": [L[i] for i in idx],
                  "after": nb(range(z + 1, min(len(L), z + 7)))[:3]})
    index[iid] = e
random.Random(20261117).shuffle(items)
json.dump({"items": items}, open(os.path.join(BOUT, "round1_sheet.json"), "w"), indent=1, ensure_ascii=False)
json.dump(index, open(os.path.join(BOUT, "round1_index.json"), "w"), indent=1)
c = collections.Counter((e["segment"], tuple(e["options"])) for e in index.values())
print(len(items), "unique bad blocks;", dict(c))
