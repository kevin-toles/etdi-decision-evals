# Code-line labelling audit: consolidated report for external review

Status at 2026-11-18. Everything below is **measured** from saved files unless marked *provisional* or *open*. The aim
of this document is to let an outside reviewer check the method, the numbers and the open decisions. File names are
given so each figure can be traced, but the report is written to be read on its own.

---

## 1. What problem this is solving

A detector decides, line by line, which lines of extracted book and paper text are **code**. It works on technical
documents stored as raw JSON page text. Its scores were first measured against a *font label*: monospace font counted
as code. That yardstick is known to be wrong in places. Monospace tables, maths, logs and LLM prompts count as "code",
and code set in a proportional font is missed.

Two hand-built answer sets were used instead:

| Set | Size | What each item is |
|---|---|---|
| Gold lines | 600 | single lines sampled from a held-out TEST pool, stratified by segment (short / book / low-code) and font label |
| Bad blocks | 668 | every block that detector options 1 and 6 output and that the font label calls "bad" (at least one font-labelled line, no font-code line) |

An earlier **4-model panel** (opus-4-6, 4-7, 4-8, 5-5) labelled both sets by voting:
- gold lines: Fleiss κ 0.836;
- block causes: κ 0.674.

The user rejected majority voting as the deciding rule: *"evidence decides, not the panel"*. This audit re-derives every
label from the **raw text itself**, using independent blind reads, and settles disagreements only with cited evidence.

### Ground rules applied throughout
- Labels come from the raw page text only. No font label, detector output or panel label is shown to any reader.
- Two **independent blind reads** by different models. A label stands only when both reads agree. There is no
  majority vote and no tie-break reader.
- Every citation is a quoted line. A script checks every quote character for character against the stored text, with
  an invisible-character-normalised fallback.
- When a read leaves lines out, or a quote fails, **make-up sheets** re-ask only for those lines. Make-up answers are
  validated the same way.
- No LLM is used in any scoring or matching step. Scoring is deterministic Python. Similarity uses character n-gram
  TF-IDF.

---

## 2. Step 2: two blind full reads of the item pages

**Scope.** Each of the 1,268 items was located in its document's raw JSON by its own text plus context, not by page
number. Each item's page was read together with the pages either side. That gave 2,183 pages and 155,896 non-blank
lines in 125 batches.

**Readers.** Read 1 was claude-opus-5-5 and read 2 was claude-opus-4-8. Each marked every non-blank line as one of:
- `code`: program source, a shell command, a config or data file, a formal spec or modelling language, pseudocode. A
  command's printed output shown with the command was code in this first pass.
- `noncode_monospace`: tables, maths, data rows, LLM prompt text, output shown without a command.
- `prose`.

**Faults found in read 2.** The opus-4-8 reader had several faults. Make-up rounds fixed them:
- it skipped whole pages while reporting full coverage;
- it cited spans past the end of a page;
- line numbers drifted by one;
- it "repaired" words that were split across lines.

Three make-up rounds were needed. All 164 original failing entries ended with a script-verified answer, and read 2 ended
with 0 uncovered lines.

**Verification against the raw JSON** (`verify_raw.py`, `verify_outputs.py`):
- all 2,183 sheet pages are identical to the raw JSON;
- all 1,268 item pointers hold the item's exact text;
- the per-line kinds, gold outcomes, block causes and example set were recomputed by separate code and matched.

**Line agreement** across all 155,896 lines:

| Metric | Value |
|---|---|
| Agreement | 0.9416 |
| Cohen's κ (3 kinds) | 0.8932 |
| Code vs not-code κ | 0.9554 |

The largest disagreements:

| Read 1 kind | Read 2 kind | Lines | What the text usually is |
|---|---|---|---|
| prose | noncode_monospace | 6,473 | figure labels, axis ticks, table cells, maths |
| noncode_monospace | code | 1,582 | formal semantics or typing rules, command output, screen captures |
| noncode_monospace | prose | 806 | same zones |

### Example set built from step 2
`step2_block_examples.jsonl` holds two kinds of block:
- **good**: 1,542 code blocks both reads drew with identical boundaries, 19,305 lines in total;
- **bad**: 1,831 blocks, of two sorts:
  - 1,280 noncode_monospace blocks both reads drew identically: code look-alikes;
  - 551 bad-block items decided as all prose, noncode_monospace, split fragment, code with a prose edge, or merged.

Each example carries `line_refs`, its exact lines. For 70 blocks that run over a page break, the page furniture between
the two parts is excluded.

---

## 3. User decision: program output and logs are neither code nor bad

The first pass counted a command's printed output as code. The user decided that **command output, logs,
profiler/status output and screen captures are excluded from scoring**. This applies whether they appear alone or
under a command. A fourth kind, `output_or_log`, was added. The command line itself stays `code`.

### 3a. Targeted four-kind re-tag (part B)

**Targets.** 2,562 lines on 216 pages, re-read by the same two models, blind:
- the noncode_monospace↔code zone (1,667 lines);
- the 21 gold lines the panel called code but both reads called not code, plus the 10 unresolved gold lines;
- every line of the 203 blocks whose cause involved noncode_monospace.

**Results.** All target lines have verified tags from both reads, and an independent recount matched.

| Re-tag outcome | Lines |
|---|---|
| both `output_or_log`, excluded | 355 (short 181, book 162, 40-book key 7, low-code 5) |
| only one read `output_or_log`, an output disagreement held out of gold | 26 |
| still noncode_monospace (read 1) vs code (read 2) | 617 → see §5 |

**Effect on the gold lines and blocks:**
- 12 of the 21 panel-code / read-not-code gold lines turned out to be output or logs and are now excluded. Examples:
  Get-Help attribute output, mainframe status lines, hex dumps.
- 16 blocks previously caused by noncode_monospace are now excluded as output.

### 3b. Blind four-kind pass on the 200 profiled blocks' pages (part A)

An older profile of 200 code blocks (by language and kind, using 4 profilers) was tested on its own pages:
- 557 pages from 145 documents, in 32 batches;
- the same two blind readers, now with four kinds;
- read 2 needed three make-up rounds;
- all 557 pages are identical to the raw JSON and all 200 items hold their exact text;
- 1 line is still uncovered, because one make-up quote failed.

| Metric (36,883 lines) | Value |
|---|---|
| Agreement | 0.950 |
| κ (4 kinds) | 0.925 |
| Code vs not-code κ | 0.991 |
| Excluded as output (both reads) | 2,128 lines |
| Output disagreements | 65 lines |

| Block outcome (200 blocks) | Count |
|---|---|
| code | 138 |
| noncode_monospace | 24 |
| excluded output | 15 (14 of them in books) |
| code plus non-code | 9 |
| all prose | 4 |
| unresolved | 10 |

**Against the profilers' consensus**, for reference only; it is not used to decide anything:
- The 35 blocks profiled as *terminal output/log* break down as 13 excluded output, 20 code (command plus output) and
  2 code plus non-code.
- The 25 blocks profiled as *not code* break down as 13 noncode_monospace, 3 all prose, 7 unresolved and 2 code.

---

## 4. Settling the 81 unresolved items (10 gold lines, 71 blocks)

The user's decision ran in order (a), (b), (c). Nothing was settled by majority vote or by a third reader.

| Path | Items | Outcome |
|---|---|---|
| Resolved by the output re-tag | 17 | read-agreed labels |
| **(a)** both reads' causes contain no code (all prose vs noncode_monospace) | 37 blocks | scored "bad, no code"; cause `prose_or_noncode` |
| **(a)** both reads' causes contain code but disagree on boundaries | 7 blocks | scored "contains code"; cause `code_boundary_dispute` |
| **(b)** evidence research | 20 (16 blocks, 4 gold lines) | 19 not code, 1 excluded as output |
| **(c)** still unclear | 0 | — |

**(b) method.** One agent researched each item:
- it read the raw page;
- it searched the corpus full-text index, with every hit read back from the raw JSON;
- it searched the CRE source repositories and ETL raw code sets;
- it argued code or not code, citing path and lines.

A second, independent agent was given the citations without the first agent's verdict. It re-read every citation and
decided on its own. A script checked every quote. An item counted as decided only when both agents agreed and at least
one verified citation supported the verdict.

**Caveat.** All 20 (b) decisions rest on the items' own documents, for example the figure caption or the surrounding
definition. Neither agent found outside corroboration in the corpus, CRE or ETL. These are recorded separately as
*"own-document evidence only, no outside corroboration"*.

### Final labels after (a)–(c), before the formal-notation rule

| Set | Result | Earlier 4-model panel |
|---|---|---|
| Gold lines (600) | 339 not code, 240 code, 15 excluded as output, 6 invisible-only lines, 0 unresolved | 330 not code, 260 code, 10 unresolved |
| Bad blocks (668) | 346 contain code, 304 bad with no code, 18 excluded output, 0 unresolved | causes: split fragment 219, noncode_monospace 156, all prose 127, actually code 77, code+prose edge 36, merged 9, output 3, unresolved 41 |

The 6 "invisible-only" gold lines contain only control or private-use characters, so they cannot be judged from text.

---

## 5. Open question: is formal notation code? (the 617 lines)

After the re-tag, 617 lines (60 items, from 11 documents) are still split. Read 1 (opus-5-5) calls them **maths**;
read 2 (opus-4-8) calls them **formal specification**. Most come from two documents: a Coq-verified derivation of the
STG machine (251 lines) and *Practical Optional Types for Clojure* (237 lines). They consist of natural-semantics
inference rules, typing judgements, grammar productions and protocol notation.

**Test.** The aim was to see whether these lines read like real repository code.

1. **CRE reference sample.** 1,682 real-repository snippets of 8–24 lines, with comments and docstrings removed and
   path and line range recorded:
   - Language-matched: 1,082 snippets from 24 formal or functional languages, 50 per language where available. The
     languages are Coq, Lean, Agda, Isabelle, TLA+, Alloy, Haskell, OCaml, F#, SML, Clojure, Racket, Scheme, K, Why3,
     SMT-LIB, BNF, Yacc, ANTLR, Elm, PureScript, Idris (9), Dafny (19) and Prolog (4; most of the CRE's `.pl` files
     are Perl). Coq files were checked by content, because Verilog shares the `.v` extension.
   - Language-agnostic: 600 snippets drawn uniformly at random from about 6 million source files.
2. **Retrieval.** For each item: the top 5 per stratum by character n-gram TF-IDF (3–5-grams), plus 3 random controls.
3. **Grading.** A pinned claude-fable-5-2 agent graded every item. Its model ID was confirmed by ping. It saw the item,
   the page context and the CRE snippets, but no reader labels. All 120 of its CRE citations were verified verbatim
   against the repository files.

**Results**

| Measure | Value |
|---|---|
| Items with a close CRE match (pre-registered cosine ≥ 0.50) | **0 of 60** (median best 0.07, maximum 0.276) |
| Fable: not code (typeset or mathematical notation) | 50 items / 602 lines |
| Fable: code | 5 items / 9 lines |
| Fable: unclear | 5 items / 6 lines |
| Agrees with read 1 (maths) | 50 / 60 |
| Agrees with read 2 (formal spec) | 5 / 60 |

- **Formal-semantics items:** every item from the formal-semantics documents came out not code. These are the STG/Coq
  rules, the typed-Clojure rules, REST-fuzzing notation, the LNCS grammars and SAT-DIFF.
- **Fable's 5 "code" items** are not formal notation. They are machine-readable text inside LLM prompts:
  - HTML `<div>`/`<p>` markup;
  - the DSL token `filter_color[green]`;
  - a JSON tool-schema line, `{"type": "function", "function":`;
  - the tag `</tool_call>`.
- **The 5 "unclear" items:**
  - an SQL `--` comment carrying a prompt instruction;
  - a lone `<short_summary>` tag;
  - three Casper headers (`# Protocol Description`, `# Specification`, `# System`) that appear only as cells in a prose
    table.

**Example** of what was judged not code, from the STG derivation, page 3 (flattened inference rules):
```
Γ : C pi ↓Γ : C pi
CON
Γ{p 7→λN x1 . . . xm.e} : p p1 . . . pn ↓Γ : p p1 . . . pn where n < m
```

**Conflicts with step (b), recorded and not applied:**
- Fable says code where (b) said not code: gold lines H0551, H1182 and H0021, and blocks K0112 and K0113. These are
  the LLM-prompt markup and JSON items.
- Fable is unclear on K0303, K0304 and K0305 (the Casper headers).
- Fable agrees with (b) on the 7 formal-semantics block items.

**Decision needed (open):** should formal or typeset notation in documents (inference rules, judgements, grammar
productions written for a human reader) count as code or not code? A second question is close to it: machine-readable
fragments inside LLM prompts (HTML, JSON tool schemas, tool-call tags). Are they code, or prompt text
(noncode_monospace)? Nothing has been applied to the gold set yet.

---

## 6. Detector rescoring (*provisional*: waits on the §5 rule)

The six options are the A4 detector configurations. Their machinery and thresholds are unchanged. They were rescored
from saved predictions only, with `output_or_log` excluded throughout.

### 6a. Line precision and recall against the final gold lines
The figures are stratum-weighted by TEST pool size and cover the short, book and low-code segments.

| Option | Final P | Final R | Final F1 | Earlier panel P / R | Font label P / R (same items) |
|---|---|---|---|---|---|
| 1 HGB + gate, balanced | 0.709 | 0.742 | 0.725 | 0.710 / 0.743 | 0.655 / 0.771 |
| 2 Blend + gate, balanced | 0.742 | 0.720 | 0.731 | 0.746 / 0.729 | 0.763 / 0.832 |
| 3 HGB + gate, strict | 0.980 | 0.229 | 0.371 | 0.993 / 0.226 | 1.000 / 0.263 |
| 4 Blend + gate, strict | 0.878 | 0.617 | 0.725 | 0.887 / 0.618 | 0.898 / 0.710 |
| 5 HGB + KR, strict | 0.980 | 0.444 | 0.611 | 0.997 / 0.439 | 1.000 / 0.509 |
| 6 Blend + KR, strict | 0.940 | 0.682 | 0.791 | 0.950 / 0.682 | 0.962 / 0.784 |

All options move by about 0.01 or less against the earlier panel. The font label flatters every option except option 1.

### 6b. Block level against the revised example set

**Revision.** Examples holding a line that both re-tag reads tagged as output were dropped (37). Bad-block items took
their final scores.

**Scored subset.** Only examples whose document is in the detector's document set could be scored: 1,426 good and
1,664 bad. 115 good and 131 bad examples could not be located there.

**Rules.** A good block counts as found when at least half its lines are kept. A bad block counts as flagged when any
of its lines is kept.

| Option | Good found | Good exact boundaries | Bad flagged |
|---|---|---|---|
| 1 | 0.585 | 0.183 | 0.325 |
| 2 | 0.710 | 0.221 | 0.293 |
| 3 | 0.149 | 0.068 | 0.070 |
| 4 | 0.570 | 0.313 | 0.198 |
| 5 | 0.363 | 0.163 | 0.072 |
| 6 | 0.612 | 0.380 | 0.225 |

### 6c. Bad-block share by segment (options 1 and 6 only; only their blocks were cause-labelled)
Two definitions are given, because the result depends heavily on which is used:
- **Panel definition:** only blocks that are wholly correct code are removed from "bad", as the earlier panel figure did.
- **Any code counts as good:** split fragments, prose-edge, merged and boundary-dispute blocks are also removed.

| Option | Segment | Font label | Panel definition | Any code counts as good | Earlier panel |
|---|---|---|---|---|---|
| 1 | code-bearing | 0.104 | 0.096 | 0.043 | 0.094 |
| 1 | 40-book key | 0.072 | 0.069 | 0.053 | 0.072 |
| 1 | low-code | 0.694 | 0.660 | 0.234 | 0.633 |
| 1 | code-free | 1.000 | 0.947 | 0.421 | 0.842 |
| 6 | code-bearing | 0.064 | 0.055 | 0.022 | 0.055 |
| 6 | 40-book key | 0.043 | 0.032 | 0.016 | 0.038 |
| 6 | low-code | 0.686 | 0.686 | 0.457 | 0.600 |
| 6 | code-free | 1.000 | 0.857 | 0.357 | 0.786 |

On the panel's definition the shares barely move: the final labels find fewer wholly correct code blocks than the panel
did (46 vs 77). Most of the remaining "bad" blocks are split fragments: real code with the wrong boundaries.

**Not measured:**
- bad-block share for options 2–5, whose bad blocks were never cause-labelled;
- output inside good examples whose lines were not in the re-tag targets.

---

## 7. Known limitations and risks (for the reviewers)

1. **Both readers are Anthropic models** (opus-5-5 and opus-4-8), and the grader is Fable, also Anthropic. Agreement
   between them may share blind spots. No reader from another model family took part.
2. **Read 2 (opus-4-8) was unreliable at citing.** It skipped pages, cited past page ends and drifted line numbers.
   Make-up rounds fixed coverage. However, the make-up answers for those lines came from the same model, reading them a
   second time.
3. **Step (b) evidence is own-document only.** No outside corroboration was found for the 20 settled items.
4. **The formal-notation rule is undecided.** The 617 lines, and possibly the 5 LLM-prompt-markup items, could move
   between code and not code depending on the rule. Rescoring is provisional until then.
5. **The "close CRE match" threshold (0.50) was fixed in advance, and nothing reached it.** Character n-gram TF-IDF may
   simply be a weak similarity measure for Unicode-heavy notation. The Fable verdicts do not depend on the similarity
   score.
6. **Block-level scoring covers only examples whose documents are in the detector's document set**: 1,426 of 1,542 good
   and 1,664 of 1,831 bad.
7. **Bad-block share depends on the definition** (§6c). Reviewers should say which definition fits the purpose.
8. **Unicode NUL inside formulas.** A few quotes failed because the text uses NUL as a word separator and the reader
   typed a space. The affected spans keep their original lines and kinds, so the labels are unaffected.

---

## 8. Questions for reviewers

1. Is the **two-blind-reads-must-agree** rule, with evidence-only settling and no majority vote, a sound basis for a
   gold set? What would you add? For example: a third model family, or human spot checks on a stratified sample.
2. Should **formal or typeset notation** (inference rules, judgements, BNF written for readers) count as code for a
   code-line detector whose output feeds code search and retrieval? And what about **machine-readable fragments inside
   LLM prompts**?
3. Is excluding **program output and logs** from both sides of the score the right call, or should output be its own
   scored class?
4. For bad-block share, which definition is right? Should a split fragment, which is real code with wrong boundaries,
   count as a bad block?
5. Do the detector conclusions hold up? On line F1 option 6 is best on every yardstick. Strict options 3 and 5 trade
   recall for precision. Option 6 matches good block boundaries exactly most often, 38%.
6. Is anything in the method likely to bias the labels towards the detector, or against it?

---

## 9. File index (all under `ETDI-1.0/_evidence/code_label_audit/`)

| Area | Folder / file |
|---|---|
| Step 2 reads, verification, sets | `raw_text_research_2026-11-17/`: `step2_report.txt`, `step2_sets.json`, `line_kinds.jsonl`, `step2_block_examples.jsonl`, `verify_raw.py`, `verify_outputs.py` |
| Output re-tag (part B) | `raw_text_research_2026-11-18/retag/`: `retag_sets.json`, `score_retag.py` |
| Profiled-block pass (part A) | `raw_text_research_2026-11-18/profiled_200/`: `profiled_sets.json`, `score_profiled.py` |
| 81-item settling | `raw_text_research_2026-11-18/evidence_81/`: `settled_a.json`, `decided_b.json`, `final_sets.json`, `evidence_A_*.json`, `evidence_B_*.json` |
| Formal-notation test | `raw_text_research_2026-11-18/cre_617/`: `fable_report.txt`, `fable_results.json`, `cre_sample.jsonl`, `retrieval.json` |
| Provisional rescore | `raw_text_research_2026-11-18/evidence_81/`: `rescore_final.json`, `bad_share_both.json` |
| Earlier panel (for comparison) | `gold_panel_2026-11-17/panel_results.json`, `bad_block_causes_2026-11-17/causes_report.txt` |
