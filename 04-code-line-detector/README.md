# COS code-line detector: answer key, audits and evaluation (2026-10-27 → 2026-10-29)

Evidence for replacing the Code-Orchestrator-Service `HeuristicCodeDetector` (Python/JS/Java patterns, TCE AC-TCE2.2)
with a trained, language-neutral line classifier (scikit-learn; no LLM in the pipeline). The LLM reviewers used
below audited the answer key offline; they are not part of any pipeline component.

## Data (not in git)

`<CORPUS_ROOT>/evaluation/cos-code-line-answer-key/` (460 MB).
Checksums: `DATA_MANIFEST.sha256` here (same file as `MANIFEST.sha256` there).

| Folder | Contents |
|---|---|
| `keys/` | `answer_key.json` (v1, 40 books), `answer_key_v2..v5.jsonl` (1,000 docs each), `answer_key_v3..v5_old40.jsonl` (the 40 v1 books relabelled), `*.meta.json` (tried / kept / skip reasons) |
| `strata/` | v4 strata `strata_{books,tiny,lowcode,codefree,transcript}.jsonl`; v5 strata `strata_v5_*.jsonl` (transcript and code-free strata are font-independent, copied from v4) |
| `train/` | `train_v5_{lowcode,codefree}.jsonl`: extra training documents, disjoint from every test document |
| `census/` | `census_v4.json`, `census_v5.json`: 3,000 uniformly sampled corpus documents classified by segment |
| `index/` | `pdf_index.json`: raw-JSON stem → PDF path (the PDFs were used only to make labels) |
| `predictions/` | cached line probabilities of the two v5 models (`report_segments_v5_{base,extra}.json.probs.pkl`) |

A key record is one document: `stem`, `pdf`, `doc_pages`, `pages[{page_number, lines[[text, label]]}]` with label
`true` (code) / `false` (not code) / `null` (unmatched or unknown, not scored), plus `segment` in strata files.

## Labelling rules by version (scripts/build_answer_key_v*.py)

| Version | Rule added |
|---|---|
| v1/v2 | JSON line = code when every span on the matching PDF line is monospace (flag or font-name list); skips scans, typewritten bodies, page-count mismatches, < 85% alignment, < 2% code. v2: parallel, short documents included, 25-page window |
| v3 | monospace measured from glyph widths (narrow ≥ 0.85 × wide); ≥ 80% of letters/digits monospace; callout glyphs ignored; repeated lines labelled in order; documents whose code is not set in monospace dropped (math-font lines excluded) |
| v4 | within monospace runs: URLs / DOIs / e-mails → not code; numbers → not code when the run has no code punctuation; ≤ 2-token lines → unknown |
| v5 | table rows (cells on one baseline, none with code punctuation), number-heavy runs, prose-like runs and e-mail lists → not code |

## Audits (four reviewers: claude-opus-4-6, -4-7, -4-8, -5-5; consensus = ≥ 3 of 4)

| Run | What | Kappa | Key result |
|---|---|---|---|
| `run_2026-10-28/` | 300 lines, v3 key | 0.856 | short-doc code labels 47.8% wrong (URLs, table numbers, identifiers) |
| `run_2026-10-28b/` | 300 lines, v4 key, documents unseen by run 1 | 0.882 | short-doc code labels 35.1% wrong; book 4.2% / 0% |
| `run_2026-10-28c_lowcode/` | 150 detector false positives in low-code docs + 50 controls | 0.749 | 36% of the false positives are real code the fonts miss; controls 0% |
| `run_2026-10-29d/` | 300 lines, v5 key, documents unseen by runs 1–2 | 0.853 | short-doc code labels 24.6% wrong; book 8.2% / 0%; not-code 0% |
| `blocks_2026-10-28/` | 200 code blocks profiled by language and kind (`block-profiler-*` agents) | — | 29 named languages; Python 11%; 22% of short-doc "blocks" not code; per-language recall in `detector_recall_by_language.json` |

Runs 1 and 2 were used to tune v4/v5, so only each run's own version measured on it unseen is unbiased:
v4 on run 2, v5 on run 4. Agent definitions: see the claude-code-agent-kit repository (label-auditor, block-profiler).

## Reports (reports/)

| File | Content |
|---|---|
| `report.json`, `report_v2.json` | rounds 1–2 on the 40-book key (baseline, (a), (a)+(c), (e), …) |
| `report_v3_round200.json`, `report_v3k_*`, `report_v4k_*`, `v3k_*.log`, `v4k_*.log` | 200-document rounds and learning curves on the v2/v3/v4 keys |
| `segments_v4.log` | segment-weighted evaluation on the v4 key (its JSON was lost to the `OUT` bug noted below; the log is complete) |
| `report_segments_v5_{base,extra}.json`, `segments_v5_*.log` | final segment-weighted evaluation on the v5 key, without / with the extra training strata, three threshold settings |
| `census_v*.log`, `build_v*.log`, `strata*.log` | census tables and build tallies |
| `verify_*.log` | v4 / v5 rules re-scored against the run 1 and run 2 consensus |
| `lang_lowcode.log` | per-language recall and the low-code sheet build |

## Re-running

Scripts are kept exactly as run. They read sibling scripts and data from their own folder (`HERE`), so copy
`scripts/` and the data folders' files into one working folder and run from `Code-Orchestrator-Service` (for
`src.extractors.code_block_extractor`). Raw JSON is read from the CLEANED collections volume; PDFs from the
processed PDF tree (labelling only). No embedding model is loaded by any script.

Known defects, left as run: `eval_segments.py` and the first `eval_segments_v5.py` runs wrote their output to a file
named `none` because the `compare_v3` header reassigns `OUT` (fixed in the final `eval_segments_v5.py` with `OUT_PATH`).

`scripts/lang_and_lowcode.py` (candidate for deletion, not deleted).
