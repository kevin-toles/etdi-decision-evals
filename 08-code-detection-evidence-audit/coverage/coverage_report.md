# Evidence coverage, step 1: retrieval leads (2026-11-17)

**Every class below is a retrieval lead awaiting research. Nothing in this step is evidence, and nothing decides a label.**

## Pre-registered matching rules
- normalise: unicode minus/quotes/visible-space to ASCII; runs of >=3 single characters joined; whitespace collapsed; leading prompts stripped
- a line is queried only with >=4 word tokens and >=20 characters after normalising; FTS phrases with more than 50 chapter hits are generic and give no lead
- the item's own document (normalised title, [DUPE] removed) is excluded; blocks are also queried as 3-line shingles, and split fragments with the neighbouring line
- one fixed-string ripgrep pass per root over CRE and the ETL raw code sets; FTS5 phrase and distinctive-token queries over chapters_fts_v2

## Scale
- items: 590 gold lines, 668 bad blocks; queryable (any eligible line): gold 301, blocks 380
- CRE: 18138 files with hits; ETL supplemental: 21 files (O'Reilly examples, code-contests and FastPrep: none)
- FTS: 1723 queries; 60 generic (>50 chapters); 154 no hit; 1195 only the item's own document; 314 with leads in other documents

## Items with at least one lead
| set | items | any lead | font-unknown corpus lead | CRE/ETL doc-file hit | hit in a comment or docstring |
|---|---|---|---|---|---|
| gold_line | 590 | 71 | 44 | 9 | 8 |
| bad_block | 668 | 112 | 71 | 16 | 13 |

## Candidate class by segment
| set / segment | code_candidate | prose_candidate | conflicting_candidates | no_candidate |
|---|---|---|---|---|
| bad_block|book | 16 | 0 | 0 | 293 |
| bad_block|code-free | 4 | 0 | 0 | 26 |
| bad_block|low-code | 2 | 0 | 0 | 50 |
| bad_block|short | 8 | 1 | 0 | 268 |
| gold_line|book | 5 | 0 | 0 | 144 |
| gold_line|lowcode | 1 | 0 | 0 | 174 |
| gold_line|short | 11 | 0 | 0 | 255 |

## Candidate class by today's panel label (for orientation only)
| set / panel label | code_candidate | prose_candidate | conflicting_candidates | no_candidate |
|---|---|---|---|---|
| bad_block|actually_code | 8 | 0 | 0 | 69 |
| bad_block|all_prose | 4 | 1 | 0 | 122 |
| bad_block|code_plus_prose_edge | 5 | 0 | 0 | 31 |
| bad_block|merged_blocks | 3 | 0 | 0 | 6 |
| bad_block|noncode_monospace | 4 | 0 | 0 | 152 |
| bad_block|split_fragment | 4 | 0 | 0 | 215 |
| bad_block|terminal_output_or_log | 0 | 0 | 0 | 3 |
| bad_block|unresolved | 2 | 0 | 0 | 39 |
| gold_line|code | 15 | 0 | 0 | 245 |
| gold_line|not_code | 2 | 0 | 0 | 328 |

## Notes
- Answer-key font labels were available for only 3 corpus matches, so prose_candidate is almost empty; font-unknown corpus hits (407 located, with context) are kept as leads.
- 202 FTS hits could not be located in the chapter's raw text (tokeniser/porter differences); they are kept with `located: false`.
- CRE hits are dominated by a few patterns that match many files; no frequency cut was pre-registered for CRE, so all hits are kept and step 2 sheets take a varied subset (2 CRE repositories, 2 corpus chapters, 1 ETL hit per item).
- Not searched: Platform Data Sets [RAW] (1.2 TB, mostly PDFs); describing a block by what it does needs reading, so it is left to step 2.

Files: a_build_queries.py, a_build_queries_lib.py, b_rg_pass.zsh, c_fts_leads.py, d_assemble.py, items.json, line_patterns.txt, rg_*.out, fts_leads.jsonl, matches.jsonl (every lead with path, line or chapter id, matched text and context), coverage_report.json.
