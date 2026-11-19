"""Bad-block causes: final cause per block (round 1 + round 2), counts by cause x segment for option 1 and option 6,
verbatim examples, and the font-counted bad-block share once the panel's "actually code" blocks are taken out.
Final cause: round-1 consensus (>=3 of 4) if settled there; else round-2 consensus (>=3 of 4); else "unresolved".
Terminal output / logs are code under the code-label audit's rules but "non-code monospace" in the request's cause
list, so the adjusted bad-block share is given both ways.
    python3 final_report.py <out_dir> <a4_options.json>"""
import collections, json, os, sys
BD, A4 = sys.argv[1:3]
MODELS = ["opus-4-6", "opus-4-7", "opus-4-8", "opus-5-5"]
CAUSES = ("all_prose", "code_plus_prose_edge", "split_fragment", "merged_blocks", "noncode_monospace", "terminal_output_or_log", "actually_code", "other")
t1 = json.load(open(os.path.join(BD, "round1_tally.json"))); index = json.load(open(os.path.join(BD, "round1_index.json")))
items = {x["id"]: x for p in "AB" for x in json.load(open(os.path.join(BD, f"round1_sheet_{p}.json")))["items"]}
r2_ids = {x["id"] for x in json.load(open(os.path.join(BD, "round2_sheet.json")))["items"]}
v2, notes2, problems = collections.defaultdict(dict), collections.defaultdict(dict), []
for m in MODELS:
    f = os.path.join(BD, f"round2_causes_{m}.json"); v = json.load(open(f))
    ff = os.path.join(BD, f"round2_fill_causes_{m}.json")            # blocks the reviewer skipped, asked again
    if os.path.exists(ff):
        fv = json.load(open(ff)); fill = {x["id"] for x in json.load(open(os.path.join(BD, f"round2_fill_sheet_{m}.json")))["items"]}
        if fv.get("model") != f"claude-{m}" or set(fv["blocks"]) != fill: problems.append(f"{ff}: bad fill file")
        assert not set(fv["blocks"]) & set(v["blocks"]); v["blocks"].update(fv["blocks"])
    if v.get("model") != f"claude-{m}": problems.append(f"{f}: model {v.get('model')}")
    if set(v["blocks"]) != r2_ids: problems.append(f"{f}: ids differ")
    for iid, x in v["blocks"].items():
        if x.get("cause") not in CAUSES: problems.append(f"{f}: {iid} cause {x.get('cause')}")
        v2[iid][m] = x.get("cause")
        if x.get("note"): notes2[iid][m] = x["note"]
assert not problems, problems
def fleiss(vs):
    n = len(MODELS); N = len(vs); pj = collections.Counter(); Pi = 0
    for v in vs:
        c = collections.Counter(v.values()); pj.update(c); Pi += (sum(x * x for x in c.values()) - n) / (n * (n - 1))
    Pe = sum((pj[k] / (N * n)) ** 2 for k in CAUSES); return round((Pi / N - Pe) / (1 - Pe), 3)
def cons(v):
    top, c = collections.Counter(v.values()).most_common(1)[0]; return top if c >= 3 else None
final, rnd = {}, {}
for iid, c1 in t1["consensus_round1"].items():
    if c1: final[iid], rnd[iid] = c1, 1
    else:
        c2 = cons(v2[iid]); final[iid], rnd[iid] = (c2, 2) if c2 else ("unresolved", None)
check = t1["round2_items"]["check"]; check_agree = sum(cons(v2[i]) == t1["consensus_round1"][i] for i in check)
GROUP = {"book": "code-bearing", "short": "code-bearing", "tiny": "code-bearing", "40-book key": "40-book key", "lowcode": "low-code", "codefree": "code-free"}
table = {}
for opt in ("option 1", "option 6"):
    c = collections.defaultdict(collections.Counter)
    for iid, e in index.items():
        if opt in e["options"]: c[GROUP[e["segment"]]][final[iid]] += 1; c["all"][final[iid]] += 1
    table[opt] = {g: dict(v) for g, v in c.items()}
# adjusted bad-block share per segment: font-bad blocks minus those the panel calls code, over all blocks
a4 = json.load(open(A4))["metrics"]; A4N = {"option 1": "1 HGB + gate, balanced", "option 6": "6 Blend + KR, strict"}
adjusted = {}
for opt, a4name in A4N.items():
    seg = a4[a4name]["segments"]; out = {}
    for g in ("code-bearing", "40-book key", "low-code", "code-free"):
        members = [s for s, gg in GROUP.items() if gg == g]
        blocks = sum(seg[s]["blocks"] for s in members); bad = sum(seg[s]["bad_blocks"] for s in members)
        cc = table[opt].get(g, {}); code = cc.get("actually_code", 0); log_ = cc.get("terminal_output_or_log", 0); unres = cc.get("unresolved", 0)
        out[g] = {"blocks": blocks, "font_bad": bad, "font_bad_share": round(bad / blocks, 3) if blocks else None,
                  "panel_actually_code": code, "panel_terminal_output_or_log": log_, "unresolved": unres,
                  "adjusted_bad_share": round((bad - code) / blocks, 3) if blocks else None,
                  "adjusted_bad_share_if_output_is_code": round((bad - code - log_) / blocks, 3) if blocks else None}
    adjusted[opt] = out
examples = {}
for cause in CAUSES:
    ids = sorted(i for i, c in final.items() if c == cause)
    unanimous = [i for i in ids if rnd[i] == 1 and len(set(t1["votes"][i].values())) == 1]
    picks = (unanimous or ids)[:3]
    examples[cause] = [{"id": i, "book": items[i]["book"], "segment": index[i]["segment"], "options": index[i]["options"],
                        "block_first_lines": items[i]["BLOCK"][:4], "block_lines": len(items[i]["BLOCK"]),
                        "notes": {**t1["notes"].get(i, {}), **notes2.get(i, {})}} for i in picks]
res = {"fleiss_kappa_round1": t1["fleiss_kappa_round1"], "fleiss_kappa_round2": fleiss(list(v2.values())), "items": len(final),
       "settled_round1": sum(r == 1 for r in rnd.values()), "settled_round2": sum(r == 2 for r in rnd.values()),
       "unresolved": sum(c == "unresolved" for c in final.values()), "check_agreement": f"{check_agree}/{len(check)}",
       "final_counts": dict(collections.Counter(final.values())), "cause_by_segment": table, "adjusted_bad_share": adjusted,
       "examples": examples, "definition": "bad block = at least one font-labelled line and no font-labelled code line (the scorer's definition)",
       "per_item": {i: {"votes_round1": t1["votes"][i], "votes_round2": v2.get(i), "final": final[i], "settled_round": rnd[i],
                        "segment": index[i]["segment"], "options": index[i]["options"], "stem": index[i]["stem"], "lines": index[i]["lines"]} for i in final}}
json.dump(res, open(os.path.join(BD, "causes_results.json"), "w"), indent=1, ensure_ascii=False)
with open(os.path.join(BD, "causes_report.txt"), "w") as fh:
    P = lambda *a: print(*a, file=fh)
    P(f"Bad-block causes (MEASURED, four-reviewer blind panel). kappa r1 {res['fleiss_kappa_round1']}, r2 {res['fleiss_kappa_round2']}; "
      f"settled r1 {res['settled_round1']}, r2 {res['settled_round2']}, unresolved {res['unresolved']}; check agreement {res['check_agreement']}\n")
    for opt, t in table.items():
        P(f"{opt}: cause x segment")
        segs = [g for g in ("code-bearing", "40-book key", "low-code", "code-free", "all") if g in t]
        P(f"  {'cause':24s}" + "".join(f"{g:>14s}" for g in segs))
        for cause in CAUSES + ("unresolved",):
            P(f"  {cause:24s}" + "".join(f"{t[g].get(cause, 0):14d}" for g in segs))
        P("  adjusted bad-block share (font-bad minus panel 'actually code'; and also minus terminal output/log):")
        for g, v in adjusted[opt].items():
            P(f"    {g:14s} blocks {v['blocks']:5d}  font {v['font_bad_share']}  adjusted {v['adjusted_bad_share']}  if output is code {v['adjusted_bad_share_if_output_is_code']}")
        P("")
    for cause, ex in examples.items():
        P(f"== {cause}")
        for e in ex:
            P(f"  [{e['id']}] {e['book'][:70]} ({e['segment']}; {', '.join(e['options'])}; {e['block_lines']} lines){'  note: ' + str(e['notes']) if e['notes'] else ''}")
            for l in e["block_first_lines"]: P(f"      | {l[:110]}")
print({k: v for k, v in res.items() if k not in ("per_item", "examples")})
