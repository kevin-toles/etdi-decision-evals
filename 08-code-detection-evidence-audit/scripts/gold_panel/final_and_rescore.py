"""Gold panel: final labels (round 1 + round 2) and the six A4 options rescored against them.
Final label per TEST item:
  settled in round 1 (>=3 of 4 code/not_code)   -> round-1 consensus; if the item was in the 10% check sample, the
                                                   round-2 result is recorded beside it (agreement reported)
  open after round 1                            -> round-2 consensus if >=3 of 4, else "unresolved" (excluded)
Rescoring (MEASURED, saved predictions only, thresholds as in worked_examples/a4_options.py):
  per option: line-level P / R against the panel labels, stratum-weighted by the gold sheet's TEST pool sizes
  (recomputed exactly as make_human_gold_sheet.py drew them), overall and per segment (short / book / lowcode);
  the font-label error rate per stratum (panel label != font label).
  Bad blocks cannot be measured from a 600-line sample; see bad_block_causes_2026-11-17 for the block-level view.
    cd Code-Orchestrator-Service && python3 final_and_rescore.py <work_dir> <panel_dir>"""
import collections, hashlib, json, os, pickle, sys
W, G = sys.argv[1], sys.argv[2]
MODELS = ["opus-4-6", "opus-4-7", "opus-4-8", "opus-5-5"]; CATS = ("code", "not_code", "ambiguous")
t1 = json.load(open(os.path.join(G, "round1_tally.json")))
r2_ids = {x["id"] for x in json.load(open(os.path.join(G, "round2_sheet.json")))["items"]}
v2, problems = collections.defaultdict(dict), []
for m in MODELS:
    f = os.path.join(G, f"round2_verdicts_{m}.json"); v = json.load(open(f))
    if v.get("model") != f"claude-{m}": problems.append(f"{f}: model {v.get('model')}")
    if set(v["verdicts"]) != r2_ids: problems.append(f"{f}: ids differ, missing {sorted(r2_ids - set(v['verdicts']))}")
    for iid, lab in v["verdicts"].items():
        if lab not in CATS: problems.append(f"{f}: {iid} label {lab}")
        v2[iid][m] = lab
assert not problems, problems
def fleiss(vs):
    n = len(MODELS); N = len(vs); pj = collections.Counter(); Pi = 0
    for v in vs:
        c = collections.Counter(v.values()); pj.update(c); Pi += (sum(x * x for x in c.values()) - n) / (n * (n - 1))
    Pe = sum((pj[k] / (N * n)) ** 2 for k in CATS); return round((Pi / N - Pe) / (1 - Pe), 3)
def cons(v):
    top, c = collections.Counter(v.values()).most_common(1)[0]
    return top if c >= 3 and top in ("code", "not_code") else None
final, rnd = {}, {}
for iid, c1 in t1["consensus_round1"].items():
    if c1: final[iid], rnd[iid] = c1, 1
    else:
        c2 = cons(v2[iid]); final[iid], rnd[iid] = (c2, 2) if c2 else ("unresolved", None)
check = t1["round2_items"]["check"]
check_agree = sum(cons(v2[i]) == t1["consensus_round1"][i] for i in check)
GKEY = json.load(open(os.path.join(os.path.dirname(G), "human_gold_2026-10-29", "gold_sheet_KEY.json")))   # not key: phase D's exec reassigns key

# ---- phase D machinery and the six options (as in a4_options.py)
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
SRC["hgb+KR"] = restack(SRC["hgb"], True, "hgb+KR"); SRC["blend+KR"] = restack(SRC["blend"], True, "blend+KR")
CONFIGS = [("1 HGB + gate, balanced", "hgb", "G+O1<=15%"), ("2 Blend + gate, balanced", "blend", "G+O1<=15%"),
           ("3 HGB + gate, strict", "hgb", "G+O1<=10%"), ("4 Blend + gate, strict", "blend", "G+O1<=10%"),
           ("5 HGB + KR, strict", "hgb+KR", "G+O1<=10%"), ("6 Blend + KR, strict", "blend+KR", "G+O1<=10%")]
gates, keeps = {}, {}
for name, s_, pt in CONFIGS:
    if s_ not in gates: gates[s_], _ = make_gate(s_, False)
    t, tr, h = choose(s_, gates[s_]).pop("_points")["gate"][pt]; keeps[name] = sel(s_, t, tr, gates[s_], h)

# ---- the gold sheet's TEST pools (same construction as make_human_gold_sheet.py), for stratum weights
fold = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4
loadj = lambda f: [json.loads(l) for l in open(os.path.join(W, f))]
gold_stems = set(json.load(open(os.path.join(W, "gold_docs.json"))))
test_docs = [d for d in loadj("answer_key_v5.jsonl") if fold(d["stem"]) == 0] + loadj("strata_v5_books.jsonl") + loadj("strata_v5_lowcode.jsonl") + loadj("strata_v5_tiny.jsonl")
pool = collections.Counter()
for d in test_docs:
    if d["stem"] in gold_stems: continue
    seg = "lowcode" if d.get("segment") == "lowcode" else ("book" if d["doc_pages"] >= 60 else "short")
    for p in d["pages"]:
        for t, lab in p["lines"]:
            if lab is not None and t.strip(): pool[f"{seg}/{'code' if lab else 'not_code'}"] += 1

def flat_to_t(st, i):                      # gold-sheet line index (pages concatenated) -> _t index (page breaks)
    j = 0; seen = 0
    for k, pg in enumerate(DOCS[st]["pages"]):
        if k: j += 1
        n = len(pg["lines"])
        if i < seen + n: return j + (i - seen)
        seen += n; j += n
    raise IndexError
rows = []
for iid, lab in final.items():
    k = GKEY[iid]; st = k["stem"]; ti = flat_to_t(st, k["line_index"])
    rows.append((iid, k["stratum"], st, ti, lab))
IDX = json.load(open(os.path.join(G, "round1_index.json")))
SHEET = {x["id"]: x for p in "AB" for x in json.load(open(os.path.join(G, f"round1_sheet_{p}.json")))["items"]}
bad_map = [iid for iid, _, st, ti, _ in rows if DOCS[st]["_t"][1][ti] != SHEET[iid]["TARGET"]]
assert not bad_map, f"{len(bad_map)} items map to a different line"

n_str = collections.Counter(s for _, s, _, _, l in rows if l != "unresolved")
def score_opt(keep, seg=None, yardstick="panel"):
    tp = fp = fn = 0.0; kept_cache = {}
    for iid, s, st, ti, lab in rows:
        if lab == "unresolved" or (seg and not s.startswith(seg + "/")): continue
        if yardstick == "font": lab = s.split("/")[1]          # same items and weights, font label instead of panel
        if st not in kept_cache: kept_cache[st] = {int(i) for b in keep(st) for i in b}
        on = ti in kept_cache[st]; w = pool[s] / n_str[s]
        tp += w * (on and lab == "code"); fp += w * (on and lab == "not_code"); fn += w * ((not on) and lab == "code")
    P = tp / max(1e-9, tp + fp); R = tp / max(1e-9, tp + fn)
    return {"P": round(P, 3), "R": round(R, 3), "F1": round(2 * P * R / max(1e-9, P + R), 3)}
font_err = {}
for s in sorted(n_str):
    labs = [l for _, s2, _, _, l in rows if s2 == s and l != "unresolved"]
    font = s.split("/")[1]; font_err[s] = {"n": len(labs), "panel_disagrees_with_font": sum(l != font for l in labs),
                                           "error_rate": round(sum(l != font for l in labs) / len(labs), 3), "pool": pool[s]}
res = {"problems": problems, "fleiss_kappa_round1": t1["fleiss_kappa_round1"], "fleiss_kappa_round2": fleiss(list(v2.values())),
       "items": len(final), "settled_round1": sum(r == 1 for r in rnd.values()), "settled_round2": sum(r == 2 for r in rnd.values()),
       "unresolved": sum(l == "unresolved" for l in final.values()), "check_sample": len(check), "check_agreement": f"{check_agree}/{len(check)}",
       "final_counts": dict(collections.Counter(final.values())), "font_label_error_by_stratum": font_err, "pools": dict(pool),
       "options_vs_panel": {name: {"all": score_opt(keeps[name]), **{sg: score_opt(keeps[name], sg) for sg in ("short", "book", "lowcode")}} for name, *_ in CONFIGS},
       "options_vs_font_same_items": {name: {"all": score_opt(keeps[name], None, "font"), **{sg: score_opt(keeps[name], sg, "font") for sg in ("short", "book", "lowcode")}} for name, *_ in CONFIGS},
       "weighting": "each stratum (segment x font label) weighted by its TEST pool size / labelled items; covers the short, book and low-code segments only (no code-free or transcript lines in the gold sheet), so these are not the census-weighted corpus figures",
       "per_item": {iid: {"votes_round1": t1["votes"][iid], "votes_round2": v2.get(iid), "final": final[iid], "settled_round": rnd[iid],
                          "stratum": GKEY[iid]["stratum"], "stem": GKEY[iid]["stem"], "line_index": GKEY[iid]["line_index"]} for iid in final},
       "not_measured": ["bad blocks against the panel (a 600-line sample cannot measure block-level errors)",
                        "the TRAIN half of the gold sheet (600 rows; only the TEST half was labelled)"]}
json.dump(res, open(os.path.join(G, "panel_results.json"), "w"), indent=1)
print({k: v for k, v in res.items() if k not in ("per_item", "pools")})
