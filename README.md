# Decision evals for an AI knowledge platform

My platform files about 3.5 million chapters from software-engineering books, talks and papers onto 461 subjects, then loads them into search so engineers and AI coding agents can retrieve chapters, passages, code and diagrams. Much of that pipeline was first written by AI coding agents. The code compiled and the tests passed, but behaviour had drifted from the design across services.

Before rebuilding it, I settled each open design question with a small, isolated experiment run on real data with the platform's real code. This repository holds four of them. Each study has the scripts exactly as run, the results, and what the result decided.

Two rules applied throughout:

- **No number unless it was measured.** Placeholder scores, invented counts and illustrative rankings are not allowed in a decision.
- **No LLM in the pipeline.** The platform's own components use embedding models, TF-IDF and classical classifiers. LLMs appear here only offline, to build and audit evaluation sets, and they never decide a result alone.

| Study | Question | What it found |
|---|---|---|
| [01 Embedding bake-off](01-embedding-bakeoff/) | Which embedding model files chapters best? | nomic-v2 leads at 79.9% on the right subject; the two "winning" numbers were artefacts |
| [02 Pre-load gate](02-preload-gate-fault-injection/) | Does the filing check catch a bad run before a multi-day load? | Average-based checks miss a subject that silently disappears |
| [03 Golden set](03-golden-set/) | How do we know search actually got better? | 228 questions, 1,734 graded passages, ground truth from human-vetted answers |
| [04 Code-line detector](04-code-line-detector/) | Which lines in technical books are real code? | The font-derived answer key was itself badly wrong on short documents |

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

---

## Running the scripts

The scripts are published exactly as run, for review. They import the platform's private classification and extraction code and read a corpus that is not distributed, so they will not run outside it. Private paths are shown as placeholders such as `<CORPUS_ROOT>` and `<HTC_REPO>`.

## Licence

Code and documents: MIT. The Stack Exchange questions and key points in `03-golden-set/data/` are derived from Stack Exchange content and are licensed CC BY-SA 4.0; each question carries its site and question id, linking to the original post and its authors.
