# Decision evals for an AI knowledge platform

My platform files about 3.5 million chapters from software-engineering books, talks and papers onto 461 subjects, then loads them into search so engineers and AI coding agents can retrieve chapters, passages, code and diagrams. Much of that pipeline was first written by AI coding agents. The code compiled and the tests passed, but behaviour had drifted from the design across services.

Before rebuilding it, I settled each open design question with a small, isolated experiment run on real data with the platform's real code: 15 proofs of concept and about 40 measured runs so far. This repository publishes the code for all of them that has code, and the results wherever they can be shared without distributing book text or third-party data. All 15 are indexed [at the end](#all-15-proofs-of-concept). Each study has the scripts exactly as run, the results, and what the result decided.

Two rules applied throughout:

- **No number unless it was measured.** Placeholder scores, invented counts and illustrative rankings are not allowed in a decision.
- **No LLM in the pipeline.** The platform's own components use embedding models, TF-IDF and classical classifiers. LLMs appear here only offline, to build and audit evaluation sets, and they never decide a result alone.

| Study | Question | What it found |
|---|---|---|
| [01 Embedding bake-off](01-embedding-bakeoff/) | Which embedding model files chapters best? | nomic-v2 leads at 79.9% on the right subject; the two "winning" numbers were artefacts |
| [02 Pre-load gate](02-preload-gate-fault-injection/) | Does the filing check catch a bad run before a multi-day load? | Average-based checks miss a subject that silently disappears |
| [03 Golden set](03-golden-set/) | How do we know search actually got better? | 228 questions, 1,734 graded passages, ground truth from human-vetted answers |
| [04 Code-line detector](04-code-line-detector/) | Which lines in technical books are real code? | The font-derived answer key was itself badly wrong on short documents |
| [05 Chapter-read depth](05-chapter-read-depth/) | Must classification read the whole chapter? | Reading only the opening costs 2.7 points on subjects |
| [06 Ingestion probes](06-ingestion-probes/) | Are the converted chapters and texts what the pipeline assumes? | 5,720 "chapters" are most of a book; 193 chapters have no text |
| [07 Scoring walkthrough](07-scoring-walkthrough/) | Which scoring rule should file a chapter? | Normalised shares always crown a primary, even when nothing matches |
| [08 Evidence-based code-label audit](08-code-detection-evidence-audit/) | What is the true label of each disputed line, without trusting a panel? | Every label re-derived from raw text by two blind reads with verified quotes; option 6 best at line F1 0.79 |
| [09 Sub-chapter floors](09-subchapter-floors/) | Can the chapter quality floors be reused below chapter level? | No: a floor that holds back 1% of chapters holds back half of all pieces |

---

## 01 Embedding bake-off

**Decision.** The embedding model sets the accuracy of every filing and every search, and changing it later means reloading the whole library, about 38 days of compute for the chapters alone on the machine this runs on. So it is chosen once, on evidence.

**Method.** Six models, 1,049 test chapters whose correct subject a person verified (427 subjects, 34 broad areas), each filed by the platform's real classification code across a grid of 15 settings.

**Result** (subject right as primary, at the default settings):

| Model | Licence | Subject right |
|---|---|---|
| nomic-v2 | Apache 2.0 | **79.9%** |
| jina-v3 | CC BY-NC 4.0 | 78.6% |
| bge-m3 | MIT | 75.4% |
| multilingual-E5-large | MIT | 69.1% |
| nomic-v1.5 | Apache 2.0 | 42.2% |
| jina-v5-small | CC BY-NC 4.0 | 144 of 1,049 chapters embedded before pausing |

**Traps the numbers contained.**
- E5 scored 99.2% on "right subject as primary or secondary", because at one setting it gave the median chapter 47 secondary subjects. Nearly every subject counted as a hit, so that 99.2% says nothing.
- jina-v5-small led nomic-v2 by 2.1 points on the 144 chapters it finished. Those 144 were the first in subject order, an easier slice (bge-m3 scores 81.9% on them against 75.4% overall), and the lead was 3 chapters.
- The test set held 25 extra copies of chapters, 8 of them verified under two different subjects, so 8 test chapters were wrong by construction.
- Both Jina models are licensed for non-commercial use only.

**Published here:** the embedding, scoring and run scripts; the per-model score files with every grid cell and every chapter's result; the test-set chapter references (no text); the duplicate list and the 144-chapter subset.

## 02 Pre-load gate, tested by fault injection

**Decision.** Before spending days loading the filed chapters into search, should the pipeline check that filing is good enough, and with which check?

**Method.** The real classification code refiled all 1,049 test chapters three times: once as-is, and twice with a realistic failure injected.

| Run | Broad areas (macro-F1) | Subjects (macro-F1) | Subjects right |
|---|---|---|---|
| Today | 0.859 | 0.750 | 79.9% |
| Failure 1: a taxonomy edit loses one small subject's description | 0.852 | 0.747 | 79.7% |
| Failure 2: shelf descriptions embedded with nomic-v1.5, chapters with nomic-v2 | 0.028 | 0.001 | 0.4% |

Failure 2 throws no error, because both models produce 768 numbers. Chapters just pile onto a few subjects (144 on role-playing games). Every check catches it.

Failure 1 passes every average-based check at the design's floors (0.80 and 0.70), because one two-chapter subject going to zero barely moves an average over 461 subjects. Yet after loading, a search on that subject returns nothing. What catches it is a per-subject comparison with the previous run ("a subject that had correct chapters now has none").

**Published here:** the fault-injection script, its full output, and the per-model filing comparison on the same chapters.

## 03 Golden set for search evaluation

**Decision.** Who decides what a correct search result is, and how do you keep that judgment independent of the system being measured?

**Method.**
- **Questions** come from Stack Exchange, tiered senior, principal and distinguished. Each question's key points come only from its accepted answer or answers scored 10 or more, and each key point cites its answer id. People decide what correct means; no model does.
- **Candidate chapters** are found by plain keyword search (SQLite FTS5, BM25) over all 3,506,882 chapters, never by the platform's own embedding search, so no embedding model is favoured.
- **Grading** is done by a blind panel. The model that proposed candidates never grades. Two Claude models grade every passage 0–3 against the key points and file it in the taxonomy; a third grades only their disagreements.
- **Local models** were tested for a panel seat against a bar set in advance (agreement with the Claude graders of at least 0.61). qwen3.5-9b and phi-4 reached 0.43–0.48 and were dropped.
- **Checks against human decisions, not model agreement.** A passage that a vetted answer cites as its source must be graded at least 2 (pilot: 5 of 5). The panel's subject must match the question's Stack Exchange tags where a tag maps to exactly one subject (pilot: 62 of 64).

**Result.** 228 questions with 1,734 graded passages, in the format the platform's retrieval-quality harness reads, so that each change to search is scored with nDCG@10, recall@50 and MRR before and after. The same labels serve as training data for classification.

A later rule tightened this further: for any golden set or label audit, the deciding factor is alignment with evidence retrieved from the corpus and the raw data, cited by file and line. A panel majority, however large, never decides on its own.

**Published here:** the question pull, keyword index, candidate search, record builder, panel instructions and scripts, agreement gate, human-anchored checks and export; the questions with their key points; the final query file with graded chapter references. Passage text is not included.

## 04 Code-line detector

**Decision.** The platform extracts code blocks from technical books, and those blocks become the examples agents retrieve when they write code. The existing detector only knew a few Python, JavaScript and Java patterns. Measured on 400 enriched books, 72% of its "python" blocks were a single English sentence ending in a colon.

**Method.** A trained, language-neutral line classifier (scikit-learn), with an answer key built from font geometry in the source PDFs (is the line set in monospace?) and refined through five rule versions. Four Claude Opus models audited samples of the key blind, with consensus at 3 of 4 (Cohen's kappa 0.75–0.88).

**Result.**
- The audits found the answer key itself was the problem on short documents: 47.8% of its code labels there were wrong (URLs, table numbers, identifiers), falling to 35.1% and then 24.6% across rule versions, measured each time on documents the earlier rounds had not seen.
- 36% of the old detector's false positives in low-code documents were real code that the fonts missed.
- On a real chapter (*Apache Iceberg: The Definitive Guide*, the bloom-filter section), the current detector returns four prose lines labelled as code and misses the SQL. The trained detector returns all three `ALTER TABLE … SET TBLPROPERTIES` statements and no prose.

Later evidence-based labelling (above) measured the font labels as 3–57% wrong depending on the document type. That led to a four-class taxonomy (code, technical notation, output or log, prose), so that typeset notation is no longer counted as code.

**Published here:** the answer-key builders for every version, the strata and census scripts, the audit sheet and scoring scripts, and every evaluation report. The answer key and documents are not included.

## 05 Chapter-read depth

**Decision.** The embedding model reads 480 tokens at a time. Should classification read a whole chapter in pieces, or only its opening?

**Method.** The same 1,049 test chapters, filed by the real scoring code from recorded nomic-v2 pieces, once reading every piece and once only the pieces inside the first 8,000 characters.

| Read | Broad area right | Subject right | Right as primary or secondary | Pieces per chapter |
|---|---|---|---|---|
| Whole chapter | 87.6% | 79.9% | 86.2% | 38.1 |
| First 8,000 characters | 85.0% | 77.2% | 82.7% | 4.5 |

950 of the chapters are longer than 8,000 characters. Reading them whole fixed 78 chapters and broke 50, and changed the primary subject of 177. **Decided:** chapters are read whole, in pieces.

## 06 Ingestion probes

Two scans of the converted library checked whether the data the pipeline receives is what its design assumes.

**Chapter boundaries.** Across 375,998 converted books (3,487,818 chapters), 5,720 "chapters" covered at least 40% of a book of 100 pages or more, and 5,274 books came out as a single chapter. *Practical Common Lisp*, for example, came out as two chapters, the first spanning pages 1–396 of 474. Every downstream tier (classification, search, citations) inherits those boundaries. **Decided:** fix the converter (PDF outline first, then printed contents, running heads and heading lines, each candidate checked) and repair the existing data from its own page text, since not every source PDF is still available.

**Units with no text.** In a sample of 8,000 books (74,234 chapters), 193 chapters in 53 books had empty content, 35 of those books entirely, and 2,379 chapters held under 200 characters. The design at the time refused a whole profile when any one unit was empty. **Decided:** a unit with no text is not loaded, and the reason is recorded.

## 07 Scoring walkthrough

**Decision.** Three candidate rules for turning similarity scores into a chapter's primary subject, secondary subjects and knowledge type: pure normalised shares, the existing components, or a fold of the two.

**Method.** Every number computed by the platform's implemented scoring components, on hypothetical scenarios designed to separate the rules and on seven real chapters of very different kinds (a code-heavy book chapter, a kernel note, a long multi-topic chapter, a business interview, a video tutorial, a lecture and OCR noise), each at three temperature settings.

**Finding.** Because shares always sum to 1, the pure rule crowns a primary and hands out secondaries even when nothing matches, while a raw-similarity test still recognises "nothing here". On a business interview the secondary count ran from 23 to 40 depending on temperature. The walkthrough fed the scoring and quarantine rules in the design.

## 08 Evidence-based code-label audit

Study 04's answer key and a four-model panel (Fleiss κ 0.836 on lines, 0.674 on block causes) were not accepted as ground truth. A majority vote is not evidence. This audit re-derived every disputed label from the raw text itself. [CONSOLIDATED_REPORT_2026-11-18.md](08-code-detection-evidence-audit/CONSOLIDATED_REPORT_2026-11-18.md) was written for outside reviewers.

**Method.**
- **Reads.** 1,268 items (600 gold lines, 668 disputed blocks) were located on their pages: 2,183 pages and 155,896 lines in all. Two different models read each page blind, with no font label, detector output or panel label shown. A label stands only when both reads agree.
- **Quotes.** Every cited line is checked character for character by a script. Make-up rounds fixed one reader's faults: skipped pages reported as covered, spans past the end of a page, drifting line numbers and silently "repaired" words.
- **Formal notation.** 617 lines of formal notation that the reads split on were tested against 1,682 real repository snippets in 24 formal and functional languages. 0 of 60 items had a close match (character n-gram cosine ≥ 0.50), so typeset inference rules read nothing like code.

**Result (provisional until the notation rule is decided).** Against the final gold lines, the blended detector with kind recognisers feeding a second-stage model (option 6) has the best line F1, 0.791 (precision 0.940, recall 0.682), and matches good block boundaries exactly most often (38%). The font label flatters every option but one.

**Published here:** the report, the option-6 pipeline spec, the detector-option scripts and metrics, the bad-block cause tables and the evidence-coverage report. The page reads and labels are not included.

## 09 Sub-chapter floors

**Question.** Chapters whose best similarity falls under a floor are held back from filing. Can the same floors apply to the units below a chapter?

**Result** (recorded 480-token pieces of the 1,049 test chapters, at a floor that holds back 1% of chapters): 50.3% of all pieces fall below. 922 chapters lose at least one piece, 348 lose more than half, and 25 lose every piece. The pieces below the floor are more often on the wrong subject (67% against 44%), but a floor that blunt would hold back half the library. Chapter floors cannot be reused unchanged below chapter level; the decision is pending.

## Scaling estimate

From the embedding run's measured rate, 0.23 s per piece. The full library is about 26 billion characters (58 GB), and the chapter tier alone is about 14 million pieces, roughly 38 days on one Mac. The pipeline embeds text about five times over (chapters, candidate windows, passages and paragraph groups), and 58 of the 1,049 test chapters exceed the 30-second piece timeout even on their own. **Decided:** the fresh run goes to a rented host, with each embedding profile pinning its model and code revision and an operator command installing them.

## Code-only folders

These hold the tools behind experiments whose outputs reproduce book or third-party text, so only the code is published.

| Folder | What the code does |
|---|---|
| [10 Worked-example harness](10-worked-example-harness/) | Runs the platform's real embedding, filing and search-ranking code on a keyword-scanned pool of real chapters, so every option in an open question gets a measured example of what an agent would get back. Includes the term-exploration scans and the prerequisite-chain sample |
| [08 scripts](08-code-detection-evidence-audit/scripts/) | The evidence-based code-label audit: sheet builders, two-read comparison, character-for-character quote verification, make-up rounds, bad-block cause tallies and evidence-coverage queries |
| [03 scripts/evidence, scripts/pattern_pairs](03-golden-set/scripts/) | Cited-source quote checks for the golden set, and the coding-problem pair sheets, grader builder and gate |
| [11 Shelf boundaries](11-shelf-boundaries/) | Builds the subject-boundary rules that keep near-duplicate subjects apart, from a reviewed canonicalisation list |
| [12 Coding-problem search](12-coding-problem-search/) | Statement alignment and embedder evaluation for finding the same or a similar coding problem across problem sets (top-1, top-5, MRR, tag overlap) |

## All 15 proofs of concept

| # | Proof of concept | Question it fed | Status | Published |
|---|---|---|---|---|
| 1 | Embedding-model evaluation | Which model (#26); scaling (#55); test-set duplicates | Open; nomic-v2 leads, jina-v5-small unfinished | [01](01-embedding-bakeoff/) |
| 2 | Scoring walkthrough | Scoring and quarantine rules | Used in the design | [07](07-scoring-walkthrough/) |
| 3 | Theory-library coverage | Whether the taxonomy has a home for theory subjects (#24, #54) | Open | Not yet |
| 4 | Code-block detection | Prose stored as code (decided); notation and low-code handling | Partly decided | [04](04-code-line-detector/), [08](08-code-detection-evidence-audit/) |
| 5 | Search golden set | Ground truth for search (#18) | Partly decided | [03](03-golden-set/); follow-up scripts (cited-source checks, pattern pairs) in [03/scripts](03-golden-set/scripts/) |
| 6 | Worked examples per open question | Every open question's options, measured | Recorded per question | Pre-load gate and filing in [02](02-preload-gate-fault-injection/); every example's code in [10](10-worked-example-harness/) |hapter text |
| 7 | SCIP symbols | Code-symbol format (#19) | Decided | Summary below |
| 8 | Coding-problem search and pattern pairs | Golden-set expansion | Rerun queued | Code in [12](12-coding-problem-search/) |
| 9 | Prerequisite-graph sample | Prerequisite chain depth (#6) | Stopped: used data the rebuild replaces | Code in [10](10-worked-example-harness/) (`c2_prereq.py`) |
| 10 | Sub-chapter floors | Floors below chapter level | Decision pending | [09](09-subchapter-floors/) |
| 11 | Chapter-read and no-text probes | Read depth (#42); empty units (#52) | Both decided | [05](05-chapter-read-depth/), [06](06-ingestion-probes/) |
| 12 | Shelf-description curation | Subject descriptions and boundaries | Open | Code in [11](11-shelf-boundaries/) |
| 13 | Converter chapter scan | Chapter boundaries (#50) | Decided | [06](06-ingestion-probes/) |
| 14 | Theory pipeline paths | Where theory books are stored (#46) | Decided | No: a reading of private code |
| 15 | Scaling estimate | Where the fresh run executes (#55) | Decided | [Above](#scaling-estimate) |

**SCIP symbols (#7), in brief.** The old builder derived code-symbol names itself. On 13,327 real code units it broke the SCIP grammar for 15% of them and labelled every non-Python unit as Python. **Decided:** symbols come only from the real language indexers, or are left empty. Measured indexer coverage on a 12-repository sample: 98.3% for languages that need no build, 72% for C, 1% for C++ (the build capture saw 6 of a Makefile's translation units), and 0% for JVM and C# repositories that do not build.

---

## Running the scripts

The scripts are published exactly as run, for review. They import the platform's private classification and extraction code and read a corpus that is not distributed, so they will not run outside it. Private paths are shown as placeholders such as `<CORPUS_ROOT>` and `<HTC_REPO>`.

## Licence

Code and documents: MIT. The Stack Exchange questions and key points in `03-golden-set/data/` are derived from Stack Exchange content and are licensed CC BY-SA 4.0; each question carries its site and question id, linking to the original post and its authors.
