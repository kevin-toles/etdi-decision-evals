# Option 6 (Blend + KR, strict): the pipeline as the proof-of-concept code runs it

This spec was written from the saved code and logs only. No new runs were made.

**Paths.**
- `W` = `<CORPUS_ROOT>/evaluation/cos-code-line-answer-key/work_seeds_2026-11-12`.
- `CL` = `ETDI-1.0/_evidence/code_label_audit`.
- All scripts run from `Code-Orchestrator-Service`, which supplies `HeuristicCodeDetector` (used for the "today" baseline only).

**Execution order.** The configuration is assembled by `CL/gold_panel_2026-11-17/final_and_rescore.py` (and the identical
`ETDI-1.0/_evidence/open_questions_2026-11-12/worked_examples/a4_options.py`). Both execute
`W/options_phase_d.py` up to `def main()`, which in turn executes:
- `W/options_phase_a.py`;
- `W/eval_segments_v5.py` up to `TS = np.round`;
- `W/compare_v3.py`, which pulls in `compare_v2.py` and `compare_prose_fix.py`.

**Stages.** Six steps, each detailed in the sections below:
1. HGB line probabilities, from `hgb_holdout.py`.
2. UniXcoder line probabilities, from `encoder_line_model.py`.
3. A 50/50 blend of the two.
4. A kind-recogniser restack.
5. A document gate.
6. Thresholded runs as blocks. There is no edge repair in option 6.

---

## 1. Inputs

**Per document** (JSONL record, `answer_key_v5.jsonl` and the strata files):
- `stem`;
- `pages[]`, each with `lines[]` of `[text, font_label]`;
- `doc_pages`;
- `segment`, on the strata files.

**Text assembly.** `book_text()` (`W/compare_prose_fix.py:73-80`) concatenates the pages, puts one empty line between
pages and returns `(text, lines, labels)`.

**Per line.**
- **Raw text**, including leading whitespace. It is the only model input.
- **`font_label`** (`True` code / `False` not code / `None` unlabelled). It is used only as the training and tuning target, never as a feature.
- **Not used:** x-position, font name or size, bounding boxes, and page number (except page breaks, as the extra empty line).
- **The one document-level field used as a feature** is `doc_pages`, in the gate (§5).

**Book vs short.** The split `"book" if doc_pages >= 60 else "short"` (`compare_v3.py:prep`, line ~44) is used only for segment reporting.

---

## 2. HGB line model (source `hgb`)

**Output.** `W/hgb_holdout_probs.pkl`, a symlink to `../predictions/hgb_holdout_probs.pkl` of 14.6 MB: one probability per line per document, as `{stem: float32[n_lines]}`.

**Training script.** `W/hgb_holdout.py:13-26`:
- train on v5 key folds 1–3, plus `train_v5_lowcode.jsonl` and `train_v5_codefree.jsonl`, minus the 626 consensus documents (`gold_docs.json`);
- that leaves 975 training documents;
- it predicts 1,731 documents (`hgb_holdout.log`).

**Features per line.** 85 columns in total.
- **Hand features, 80 columns.** `line_feats()` (`W/compare_v2.py:52-62`) gives 16 features:
  - log length;
  - leading-whitespace flag;
  - symbol share;
  - stop-word share;
  - code-keyword share (`KW`, lines 18-22);
  - ends with `;{})`, ends with `:`, ends with `.`;
  - starts upper-case, starts lower-case, starts with a non-alphanumeric character;
  - `\w(` call pattern;
  - camelCase or snake_case;
  - digit share;
  - word density;
  - arrow or scope tokens (`-> => :: := $x <x>`).

  `context_matrix()` (lines 65-74) stacks these 16 features for the line, the previous and next non-blank lines, and the second previous and second next non-blank lines.
- **N-gram feature, 5 columns** (`W/compare_v3.py:26, 46-76`):
  - `HashingVectorizer(char_wb, 2–4-grams, 2^18 features)`, then TF-IDF (sublinear), then logistic regression (balanced, liblinear, C=1);
  - its probability for the line and its ±1/±2 non-blank neighbours;
  - out-of-fold over 3 document folds for training documents.

**Classifier.** `HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, class_weight="balanced", random_state=0)` (`compare_v3.py:79-81`), trained on every labelled line.

**Base thresholds.** The base model's own thresholds, `t 0.90` and `t_run 0.95` (`phase_d_2026-11-03/hgb_holdout_meta.json`), are not used by option 6. Option 6 re-tunes after the restack (§7).

---

## 3. UniXcoder line model and the blend

**Checkpoint and fine-tuning.**
- **Base:** `microsoft/unixcoder-base`, a 12-layer RoBERTa with a sequence-classification head of 2 labels.
- **Script:** `W/encoder_line_model.py`.
- **Command used** (from the session transcript):
  - `ENCODER=microsoft/unixcoder-base LR=2e-5 BS=16 MAXLEN=96`
  - `INFER_BS=64 MIN_FREE_RAM_PCT=20`
  - `CASCADE_FROM=hgb_holdout_probs.pkl CASCADE_MIN=0.15`
  - `GOLD_DOCS=gold_docs.json`
  - `FREEZE_LAYERS=6`
  - `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.6 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.4`
  - `python3 encoder_line_model.py 120000`
  - seeds are set with `SEED=101/202/303`.
- **Frozen layers:** the embeddings plus the bottom 6 of 12 encoder layers (lines 76-82). 43,119,362 parameters remain trainable (`encoder_unixcoder_s*.log`).
- **Optimiser:** AdamW (weight decay 0.01), 200-step linear warm-up then linear decay, gradient clipping at 1.0 (lines 83-93).
- **Length:** one epoch of 7,500 steps at batch 16.

**Training sample** (lines 55-64).
- Only labelled, non-blank lines from the same documents as the HGB model are used.
- Positives available: 32,207 code lines; negatives: 1,028,753.
- The target is 60,000 positives in a 120,000-line sample, but only 32,207 exist, so all of them are used, plus 87,793 sampled negatives.
- This positive count is the "32K" figure. It is the number of font-labelled code lines in the training documents, not a configured cap.

**Input window** (`ctx()`, lines 50-53):
```
<2 previous non-blank lines> \n >>> <line> <<< \n <2 next non-blank lines>
```
The two neighbours on each side come from within ±8 lines. The window is truncated to 96 tokens.

**Output and the cascade.**
- The output is a softmax probability that the line is code.
- Only lines with an HGB probability of at least 0.15 are sent to the encoder (lines 102-103). Every other line gets 0.
- **Prediction files:** `W/encoder_probs_unixcoder_s{101,202,303}.pkl`, and `../predictions/encoder_probs_unixcoder.pkl` for the Nov10 run. Each is 7.4 MB.

**Blend.**
- Formed at `CL/gold_panel_2026-11-17/final_and_rescore.py:54-55`: `blend[line] = 0.5 * hgb[line] + 0.5 * unixcoder_s202[line]`.
- Because of the cascade, any line below 0.15 on HGB has a blended probability under 0.075.

**Saved weights.**
- `W/models/unixcoder_s101|s202|s303/` and `…/cos-code-line-answer-key/models/unixcoder/` (Nov10).
- Each holds `model.safetensors` (fp32) plus the tokenizer and config, 485 MB per checkpoint.

---

## 4. Kind recognisers: features into a second-stage model, not overrides

**The recognisers.** `KIND` (`W/options_phase_d.py:47-57`) is a set of 11 regular expressions, evaluated per line by `kinds()` (lines 60-64):

| Kind | What it matches |
|---|---|
| prompt | shell / REPL / database prompts: `$ # % >>> ... > In[n]: Out[n]: PS C:\> user@host$ mysql> postgres=# sqlite> irb() scala> ghci>` |
| log | ISO timestamps, `hh:mm:ss`, INFO / WARN / ERROR / DEBUG / TRACE / FATAL / SEVERE, `[tag]` prefixes |
| trace | `at pkg.Cls(...)`, `Traceback (most recent call last)`, `File "...", line n`, `XxxError:` / `XxxException:`, `Caused by:` |
| compiler | `path:line[:col]: error / warning / note / fatal`, `error[Ennn]:` |
| listing | `ls -l` permission strings, `total n` |
| diff | `+++ `, `--- `, `@@ … @@`, `+x` / `-x` |
| kv | `key: value` / `key = value` |
| columns | 3 or more fields separated by runs of 2 or more spaces |
| pseudo | lines starting `if / for / while / repeat / until / return / procedure / function / begin / end / else / then / do` |
| closer | a line of closing brackets only |
| caption | `Listing / Example / Figure / Fig. / Table / Output / Code / Program <n>` |

**How they are used.** The flags feed the restack, `stack_feats(..., with_kind=True)` (lines 67-96). It has 34 features per non-blank line:
- the blended probability at offsets −3 … +3;
- the mean over an 11-line window;
- line length, indent, and the blank-line gap before the line;
- the 11 kind flags;
- the 11 kind flags of the ±2 neighbours;
- the distance in non-blank lines since the last prompt line, capped at 50.

**The restack model.** `restack()` (lines 99-128) is `HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, random_state=0)` with no class weighting.
- **Training documents:** tune-half segment documents only, 537 of them, with the consensus documents excluded (`phase_d_full.log`).
- **Tune documents** get 2-fold cross-fitted scores, so the thresholds are chosen on out-of-fold probabilities.
- **Every other document** is scored by the model fitted on all tune documents.
- **Training labels:** the font labels.
- **Its output, `blend+KR`, is the line probability used from here on.**

---

## 5. Document gate (G) and the G+O1 operating point

**The gate.** `make_gate(src, with_ft=False)` (`W/options_phase_d.py:250-269`) fits a document-level `HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, random_state=0)`.
- **Its target:** the document has at least 5 font-labelled code lines.
- **Its 13 features**, computed on the `blend+KR` probabilities by `doc_feats` (lines 232-247):
  - number of non-blank lines;
  - share of lines above 0.5, above 0.8 and above 0.95;
  - mean of the top 20 line probabilities;
  - maximum line probability;
  - number of runs at t = 0.8;
  - maximum and mean run length;
  - maximum run mean;
  - number of runs with mean of at least 0.94;
  - number of runs of 5 or more lines;
  - `doc_pages`.
- **Scores:** tune documents get 3-fold out-of-fold scores; every other document is scored by the full model.
- **What it does:** a document whose gate score is below the threshold `h` produces no blocks (`sel()`, lines 373-378).
- **Quality** on the s202 run, test documents: precision 0.935 and recall 0.892 at 0.5 (`a4_option6_runs.log`).

**G+O1 ≤10% ("strict").** This is the operating point chosen by `choose()` (lines 387-406), described in §7.

**Why the gate threshold is 0.50 in s202 and 0.80 in the other runs.** `h` is a grid value from {0.2, 0.35, 0.5, 0.65, 0.8}, picked per run together with `t` and `run`:
- the pick maximises tune-half recall, subject to a tune-half bad-block share of at most 10%;
- ties go to the highest `(t, run, h)` (`RK`, line 370);
- the gate's own scores come from each run's probabilities, so they move with the seed;
- in s202, `h = 0.50` gave strictly more tune-half recall within the 10% limit than 0.65 or 0.80; in the other runs 0.80 won or tied.

It is a per-seed tuning outcome, not a design difference. The resulting spread is small (§7).

---

## 6. Block assembly

`runs()` (`W/options_phase_d.py:139-155`):
1. A line is "on" when `p >= t` and it is not blank.
2. A run is a sequence of on lines. **One** blank line may sit inside a run when the line after it is on again. Two blank lines, or one blank line followed by an off line, end the run.
3. The block is the run's non-blank lines. Its score is their mean `p`.
4. The block is kept when its mean is at least the run threshold `tr`, and the document passes the gate.

There is no minimum or maximum length, no caption trimming, no brace matching and no edge repair. Edge repair (`edge_repair`, lines 283-318) and parse-based repair (`ts_repair`, lines 342-363) exist, but they are not part of option 6.

---

## 7. Thresholds per training run

**How they are tuned** (`choose()`, `options_phase_d.py:367-406`):
- **Grids:**
  - line `t` from 0.50 to 0.98 in steps of 0.04;
  - run `tr` from {none, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98};
  - gate `h` from {0.2, 0.35, 0.5, 0.65, 0.8}, on every second `(t, tr)` point.
- **Objective:** on the **tune half** of the segment documents (`half = sha256("tune:"+stem) % 2 == 0`, `eval_segments_v5.py:17`), maximise corpus-weighted recall subject to a corpus-weighted bad-block share of at most 10%.
- **Bad block:** a block with no font-labelled code line.
- **Corpus weights:** the census shares (`eval_segments_v5.py:37-40`).

**Results per run** (`a4_option6_runs.json`; measurements on the test half and the consensus documents):

| Run | UniXcoder predictions | t | run | gate | consensus P / R | corpus F1 | bad: code-bearing / low-code |
|---|---|---|---|---|---|---|---|
| Nov10 | `predictions/encoder_probs_unixcoder.pkl` | 0.50 | 0.80 | 0.80 | 0.986 / 0.743 | 0.680 | 0.088 / 0.742 |
| s101 | `encoder_probs_unixcoder_s101.pkl` | 0.62 | 0.85 | 0.80 | 0.993 / 0.715 | 0.661 | 0.079 / 0.739 |
| **s202** | `encoder_probs_unixcoder_s202.pkl` | **0.50** | **0.80** | **0.50** | 0.986 / 0.732 | 0.676 | 0.082 / 0.686 |
| s303 | `encoder_probs_unixcoder_s303.pkl` | 0.58 | 0.80 | 0.80 | 0.986 / 0.731 | 0.678 | 0.095 / 0.711 |

These bad shares are on the font yardstick. On the research labels, with output counted as negative, s202 gives a strict bad-block rate on code-bearing documents of **0.056**: contamination 0.023 plus boundary error 0.034 (`raw_text_research_2026-11-18/evidence_81/bad_share_v2.json`).

**Which to ship.** Ship **s202 with its own thresholds** (t 0.50, run 0.80, gate 0.50). It is the checkpoint behind every research-label measurement: the gold rescore, the block-level scores and the bad-block rates. The seed spread is small:
- consensus R: 0.715–0.743;
- code-bearing bad share on the font yardstick: 0.079–0.095.

One caveat: the thresholds were tuned against the **font** bad-block share, not against the strict research-label target BEH-01.12 now uses. Re-tuning against research labels needs research-labelled tune documents, and the current research labels cover only the 668 bad blocks and the 600 gold lines.

---

## 8. Training data

**Answer key.** `answer_key_v5.jsonl`, font-labelled.

**Folds.** `fold = sha256("curve:"+stem) % 4`:
- fold 0 is the held-out test fold;
- folds 1–3 plus `train_v5_lowcode.jsonl` and `train_v5_codefree.jsonl` are the training data;
- the 626 consensus documents are removed (`hgb_holdout.py:15-17`, `encoder_line_model.py:37-46`);
- that leaves 975 training documents.

**Evaluation documents.** 1,731 in total: fold 0, plus `strata_v5_books`, `tiny`, `lowcode`, `codefree` and `transcript`, plus `answer_key_v5_old40`, plus the consensus documents.

**Tune and test halves.** The halves (`half()`) split those evaluation documents. The restack and the gate train on the tune half only.

**Block examples.** None of the research-audit block examples comes from a training file. They come from the fold-0 test documents, the consensus documents, the evaluation strata and the 40-book key.

**"32K".** 32,207 is the number of code-labelled lines in the 975 training documents (`encoder_unixcoder_s*.log`). The encoder uses all of them; HGB uses every labelled line, with balanced class weights.

**Full-data retrain (4c).** It is listed under `not_reproduced` in `a4_option6_runs.json`, so nothing about it is measured. What it would change by construction:
- training on all v5 folds and strata, and on the consensus documents, raises the code-line count above 32K;
- the restack and gate would be refitted;
- the thresholds would have to be re-tuned;
- the held-out test half, the consensus set and the research gold lines would stop being held out;
- a fresh, document-level held-out sample would then be needed to measure the shipped model.

---

## 9. Runtime cost (only what the logs record)

| Stage | Hardware | Measured | Source |
|---|---|---|---|
| UniXcoder inference | MPS (Apple GPU), INFER_BS 64, MAXLEN 96 | 481,907 cascaded lines in 2,487–2,671 s, about **5.2–5.5 s per 1,000 lines sent** | `encoder_unixcoder_s101/s202.log` |
| UniXcoder training (one-off) | MPS, BS 16, 6 layers frozen | 7,500 steps in 1,860–2,210 s; about 1 h 20 m per seed including prediction | same logs, `seeds_chain.log` |
| Free RAM during UniXcoder training | 17 GB machine | 42–63% free throughout (the run aborts below 20%) | same logs |
| UniXcoder weights | disk | 485 MB fp32 per checkpoint | `models/` |
| Restack + gate + thresholds for 6 options, whole corpus | CPU | about 2 min per full rescore run | `rescore_chain.log`, `a4_option6_runs.log` |

**Not measured.** The logs don't record any of the following:
- UniXcoder on CPU;
- HGB line-model training or inference time per 1,000 lines;
- peak process memory for either model.

**The cascade affects the per-line cost.** Only lines with an HGB probability of at least 0.15 reach UniXcoder, so its share of the documents' lines depends on the corpus.

---

## 10. The low-code gap

On the research labels, option 6's low-code contamination is 0.457 against 0.265 for option 1, and all of it is technical notation. Earlier measurements bear on it as follows. None of them is a measured fix for option 6.

1. **Option 5 (HGB + KR strict, no UniXcoder)** has the lowest low-code bad share of the six options on the font yardstick: 0.40, against 0.686 for option 6 (`a4_options.json`). Its recall is lower: low-code R 0.124 against 0.202, code-bearing R 0.601 for option 6. It has not been scored on the research labels' contamination split.
2. **Phase D (`phase_d_2026-11-03/options_phase_d.json`)** tested the fastText gate (`G+FT`), edge repair (`ER`) and parse-based repair (`TS-ER`) on `blend+KR`. In phase D the blend was HGB + DistilBERT, not UniXcoder. At the strict point, none of the three lowered low-code bad below the plain gate: `blend+KR` kept no low-code blocks at all (bad 1.0, R 0). On `hgb+KR` strict, `G+FT` and `ER` / `TS-ER` held low-code bad at 0.40 and changed precision and recall only slightly.
3. **The cause seen in the audit:** the contaminating low-code blocks are typeset maths and notation, so the gold v2 class is `noncode_technical_notation`. None of the 11 kind recognisers targets maths or notation, and the restack was trained on font labels, where much of that notation is marked as code.

**Unmeasured candidates.** These are for the design to weigh:
- a per-segment gate or threshold for low-code documents;
- a notation recogniser feature, for example a share of Unicode maths symbols or Greek letters, or `⊢ ⇒ ∈ ::=`;
- retraining the restack on the research labels.
