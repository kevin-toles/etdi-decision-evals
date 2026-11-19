"""Writes step2_report.txt from compare_reads.json, step2_sets.json, makeup2_validation.json and verify_raw.json.
    python3 make_report.py <dir>"""
import json, os, sys
R = sys.argv[1]; J = lambda f: json.load(open(os.path.join(R, f)))
d = J("step2_sets.json"); s = d["summary"]; c = J("compare_reads.json")["summary"]; mv = J("makeup2_validation.json"); vr = J("verify_raw.json")
o = open(os.path.join(R, "step2_report.txt"), "w"); P = lambda *a: print(*a, file=o)
P("Step 2 raw-text research: two blind full reads of 2,183 pages / 155,896 non-blank lines (125 batches)")
P("read 1 claude-opus-5-5 (research_*), read 2 claude-opus-4-8 (research2_*). Text only; leads corroboration only; no font label or class.")
P(f"Raw check (verify_raw.py, data volume): pages {vr['pages']}, item pointers {vr['items']}, quotes {json.dumps(vr['quotes'])}")
P("  (failing read-1 / read-2 quotes are the ones re-cited in makeup_research.json / makeup2_research_M*.json)")
ok = [k for k, v in mv["entries"].items() if v["ok"]]
P(f"Read 2 make-up, three rounds (M01-M06, M07, M08): {len(mv['entries'])} answers, {len(ok)} verified; every originally failing re-cite and every gap now has a verified answer; read 2 uncovered lines after make-up: {sum(v for k, v in c['confusion'].items() if 'uncovered' in k)}")
P("  read 2 faults found: whole pages skipped while reporting full coverage (B073, B077, B079, B097, B108, B111), spans cited past page end (B026, B050, B051, B057, B067, B089, B094), off-by-one drift, quotes that repair word fragments. 7 lines are covered twice after make-up, each with the same kind from both spans. Item H0887 (B054) has no read-2 item note; its line kinds are present.")
P("\nLINE AGREEMENT (all pages): agreement %.4f, kappa %.4f, code-vs-rest kappa %.4f" % (c["agreement"], c["cohen_kappa"], c["code_vs_rest_kappa"]))
P("  confusion read1|read2: " + json.dumps(c["confusion"]))
P("  disputed zones: prose|noncode_monospace (figure labels, axis ticks, table cells, maths); noncode_monospace|code (formal semantics, command output, screen captures); noncode_monospace|prose")
for name in ("gold_lines", "bad_block_causes"):
    x = s[name]; items = d[name]; P(f"\n{name.upper()} ({x['items']} items)"); P("  outcome: " + json.dumps(x["outcome"]))
    if "kind_outcome" in x: P("  three-way kind outcome: " + json.dumps(x["kind_outcome"]))
    P("  decided vs earlier panel (comparison only, panel never decides): " + json.dumps(x["decided_vs_panel"]))
    P("  unresolved read1|read2: " + json.dumps(x["unresolved_reads"]))
    P("  unresolved / not judgeable items:")
    for k, v in items.items():
        if v["outcome"] in ("unresolved", "invisible_only_line"):
            P(f"    {k} {v['outcome']} r1={v.get('read1')} r2={v.get('read2')} panel={v['panel']} | {v['text'][0][:80]!r}" if v["text"] else f"    {k} {v['outcome']} panel={v['panel']}")
    if name == "gold_lines":
        P("  decided not_code where panel said code:")
        for k, v in items.items():
            if v["outcome"] == "not_code" and v["panel"] == "code": P(f"    {k} {v['read1_kind'][0]} | {v['text'][0][:80]!r}")
        P("  decided code where panel said not_code:")
        for k, v in items.items():
            if v["outcome"] == "code" and v["panel"] == "not_code": P(f"    {k} | {v['text'][0][:80]!r}")
P("\nBLOCK EXAMPLES (step2_block_examples.jsonl): good %d (%d lines), bad %d: %s" % (s["examples"]["good"], s["examples"]["good_lines"], s["examples"]["bad"], json.dumps(s["examples"]["bad_by_why"])))
P("Each example carries line_refs [[page, line], ...], its exact lines: 70 blocks chained over a page break skip the page furniture between their parts, so page_start..line_end alone is not the block.")
P("terminal_output_or_log is not re-decidable from line kinds (output shown with its command is code by the instructions).")
P("Independent output check (verify_outputs.py, separate code path): " + json.dumps({k: (v if k != "D" else {"examples": v["examples"], "problems": len(v["problems"])}) for k, v in J("verify_outputs.json").items() if k in "ABCD"}, ensure_ascii=False)[:900])
