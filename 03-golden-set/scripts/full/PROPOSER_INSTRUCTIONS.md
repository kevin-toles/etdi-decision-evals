# Golden set full run — proposer instructions (ETDI-1.0 OQ#18, 2026-11-15)

You are the **proposer** for one taxonomy domain. You choose questions, write their key points from human-vetted answers,
and research candidate passages in the platform's book/paper/talk corpus. You never grade: a separate blind panel grades
everything you propose. Work only inside `<EVIDENCE>/golden_set_2026-11-13`
(below: `EV`). Write exactly one file: `EV/full/proposals/<domain>.json`. Do not edit any other file.

## Tools (Bash, run from EV)
- `python3 -I full/show_q.py '<qid>'` — the thread: title, body, tags, and the **key-source answers** (accepted, or score >= 10) with ids. Answers are cut at ~2,000 chars.
- `./gs '<FTS5 query>' [k=15] ['term|term' window terms]` — model-neutral BM25 keyword search over all 3.5M corpus chapters. Prints each hit's ref, title, collection, split, and the best-matching windows with their character offsets. Quote hyphenated or dotted tokens: `"fault-tolerant"`, `"SHA-1"`. Use `AND`, `OR`, `NEAR(a b, 10)`, `"exact phrase"`.
- `./gv '<ref>' 'term|term' [n=3] [width=600]` — more windows from one chapter; `./gv '<ref>' @start:len` — an exact span.
- `python3 -I full/validate_proposal.py full/proposals/<domain>.json` — must print `OK` before you finish.
- `panel/rubric.py` holds the taxonomy (domain → subdomain slugs) and the four knowledge-function definitions. Read it.
- **Never** use the platform's semantic/embedding/hybrid search, any MCP search tool, or the web. BM25 only: candidates must not favour any embedding model.

## Step 1 — choose questions
Your slice is `EV/full/slices/<domain>.json`: `allocation` (how many questions to pick) and `targets` (per subdomain, the
highest-scored candidate questions with their tags). Pick exactly `allocation` questions:
- **Spread**: as many distinct subdomains as the allocation allows; prefer questions that bridge into a second domain.
- **Tier mix** across your picks (at least one of each when allocation >= 3):
  - `senior` — explain an established mechanism or practice a senior engineer must know (why X is faster, how Y works).
  - `principal` — trade-offs or design across several concepts/components; the answer weighs options.
  - `distinguished` — theory, proofs, research results, or deep cross-domain synthesis.
- **Knowledge-function mix**: include questions about failure modes/limitations and about concrete implementation, not only definitions.
- **Reject** (and list in `rejected` with a reason): tool/version-specific troubleshooting with no transferable concept, opinion or
  product-recommendation questions, answers that are mostly links or code with no explanation, threads whose key-source answers
  have under ~400 characters of substance. If a slice runs short, say so in `notes` — never pick a weak question to fill it.

## Step 2 — key points
For each picked question write 2–7 key points. Each is **one claim a key-source answer states**, with `src` = the answer
id(s) that state it. Never add a claim the answers do not make, never from your own knowledge, never from a low-score
answer. Order them so K1 is the core of the answer. `query` = the question as a searcher would type it (the title, lightly
cleaned). `intended_domains` = the domains you expect relevant passages to sit in (a plan, not a label).

## Step 3 — research candidates (6–10 per question)
Search several ways per key point: the answer's own terms, the underlying theory terms, named sources the answers cite
(paper titles, authors, theorems), and synonyms. Read windows before proposing. For each question propose:
- **≥ 3 `direct`** passages that state one or more key points for this question;
- **≥ 1 `foundation`** passage when one exists — the theory, definition, proof or paper the answer rests on (search for any source an answer cites; put `cited by answer <id>` in `note` when it is one);
- **exactly 1 `distractor`** — a passage with the question's vocabulary that does **not** answer it (adjacent concept, different question). Choose one that clearly answers nothing; a partly relevant one is not a distractor.
Prefer chapters whose split is `unseen`; `heldout` and `anchor_evidence` are allowed but note them. One candidate per chapter ref.
`spans`: 1–3 `[start, length]` windows (length ≈ 600) from the gs/gv offsets that show the evidence.

## Labels (per candidate — the PASSAGE's own subject, not the question's)
- `primary` = {domain, subdomain}; `secondary` = 0–3 more {domain, subdomain} the passage also substantively belongs to — use these to bridge domains. Slugs must exist in `panel/rubric.py` (subdomain under its own domain).
- `kf` = one of `role-definition`, `implementation-ref-spec`, `failure-mode-limitation`, `supporting-papers`; `kf_alt` = a second plausible one or null.
- `covers` = key point ids the passage substantively states. `note` = one sentence on why.
- Taxonomy gaps (no fitting subdomain): pick the closest, and add `TAXONOMY GAP: <what is missing>` to `note`.

## Output file `EV/full/proposals/<domain>.json`
```json
{"domain": "<domain>", "proposer": "claude-opus-5-5",
 "questions": [{"qid": "...", "tier": "senior", "query": "...", "intended_domains": ["..."],
                "key_points": [{"id": "K1", "src": ["<answer id>"], "text": "..."}]}],
 "candidates": [{"qid": "...", "ref": "<chapter ref exactly as gs prints it>", "spans": [[1234, 600]],
                 "covers": ["K1"], "role": "direct", "kf": "role-definition", "kf_alt": null,
                 "primary": {"domain": "...", "subdomain": "..."}, "secondary": [], "note": "..."}],
 "rejected": [{"qid": "...", "reason": "..."}],
 "notes": "anything the orchestrator should know (short slice, taxonomy gaps, uncovered key points)"}
```
Run the validator and fix every problem it prints. Finish with a 3-line summary: questions picked (tiers), candidates by role, uncovered key points.
