# Raw-text research: what to do with one sheet

You are reading the extracted text of technical documents (books, papers, articles) exactly as stored in the corpus
JSON. Your job is to decide, from the text itself, what is code and what is not. No font label, detector output or
other reviewer's opinion is given to you, and you must not rely on any. Judge only from what you read.

## Input

The sheet is a text file (`sheet_<batch>.txt`). For each document it gives a `######## DOCUMENT:` header (use that
exact title as `doc`), then every page as numbered lines written `p<page> L<line> | <verbatim text>`; the text after
`| ` is the line exactly as stored (it may be empty). Lines are numbered from 1 on each page.

- The `--- ITEMS ---` list under each document gives pointers to places you must cover (one line, or a block of
  lines). They say where to look, nothing about what the answer is.
- `LEAD` entries under an item are search hits found elsewhere: in the Code Reference Engine (real source
  repositories), in ETL raw code sets, or in other corpus documents, each with its own context lines (`| ...`). They
  are hints to check, not evidence.

## What to write

Mark spans on every page of the sheet. Cover every non-blank line of every page with exactly one span. A span is a
run of consecutive lines on one page that share one kind:

- `code`: program source, a shell or terminal command, a configuration or data file (JSON, YAML, XML, SQL, diff,
  Dockerfile, unit file), a formal specification or modelling language, or pseudocode written as code lines. A
  command line itself (for example `$ ls -l`, `PS> Get-Help`, `>>> x = 1`) is `code`.
- `output_or_log`: text a program printed: command or REPL output, logs, status lines, test results, timings,
  profiler output, screen captures of program output. It is `output_or_log` whether or not the command that produced
  it is shown; the command line itself stays `code`.
- `noncode_monospace`: text set out like code but neither code nor program output: tables of values or results,
  maths, raw data rows, LLM prompt text.
- `prose`: sentences, headings, captions, figure and table labels, bullet text, references, page furniture (page
  numbers, running headers), URLs on their own.

Inline code inside a sentence is still prose. A code span should cover one whole real code block: its correct start
and end lines. Where one real block runs over a page break, mark the part on each page and set `continues: true` on
the first part.

For every item, add an entry saying, in a few words, what the item's lines are. For a block item, also say whether
its line range matches the real code block's boundaries, is part of a larger block, or mixes code and prose. For
every lead you looked at, say whether it `supports`, `challenges` or is `irrelevant` to your call, and why. Quote the
lead line you relied on, verbatim.

Write exactly one JSON file, at the output path you are given:

```json
{"model": "<your exact model id>", "batch": "<batch id>",
 "spans": [{"doc": "...", "page": 12, "line_start": 3, "line_end": 9, "kind": "code | output_or_log | noncode_monospace | prose",
            "quote_first": "<line 3 verbatim>", "quote_last": "<line 9 verbatim>", "continues": false, "note": "..."}],
 "items": [{"item": "H0123", "what": "...", "boundary": "exact | part_of_larger | mixed | n/a"}],
 "leads": [{"lead_id": "H0123-L1", "verdict": "supports | challenges | irrelevant", "quote": "...", "why": "..."}]}
```

`quote_first` and `quote_last` must be copied character for character from the cited lines; a script checks them.
`note` is optional. Cover every page and every item in the sheet. Read only the sheet; do not run commands, search
or open other files. Then reply with one line: the number of spans written.
