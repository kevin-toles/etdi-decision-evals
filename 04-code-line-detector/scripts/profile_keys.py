"""Profile answer keys: document mix, code-block kinds and guessed languages (pygments lexer guess; rough)."""
import json, re, sys, collections, warnings
from pygments.lexers import guess_lexer
warnings.filterwarnings("ignore")
SH = re.compile(r"^\s*(\$ |# |sudo |cd |ls |pip3? |npm |docker |kubectl |git |curl |wget |apt(-get)? |brew |export |mkdir |cat |echo |chmod |python3? |java |mvn |gradle |helm |az |aws |gcloud )")
SQL = re.compile(r"(?i)^\s*(select|insert|update|delete|create|alter|drop|with|from|where|join|grant)\b")
MARK = re.compile(r"^\s*(<[/!?]?[\w:-]+|[\w.-]+\s*:\s*\S|[\w.-]+\s*:\s*$|\"[\w.-]+\"\s*:|[{}\[\],]\s*$)")
OUT = re.compile(r"^[\s\d.,:%|+\-=/()]*$|^\s*\[?\d{2,4}[-/:]\d{2}")

def blocks(doc):
    lines = [t for p in doc["pages"] for t, _ in p["lines"]]; labs = [l for p in doc["pages"] for _, l in p["lines"]]
    out, cur = [], []
    for t, l in zip(lines, labs):
        if l: cur.append(t)
        elif l is None and cur and not t.strip(): continue
        else:
            if len(cur) >= 2: out.append(cur)
            cur = []
    if len(cur) >= 2: out.append(cur)
    return out

def kind(b):
    ne = [l for l in b if l.strip()]; n = len(ne)
    if sum(bool(SH.match(l)) for l in ne) >= 0.4 * n: return "shell"
    if sum(bool(SQL.match(l)) for l in ne) >= 0.3 * n: return "sql"
    if sum(bool(OUT.match(l)) for l in ne) >= 0.6 * n: return "output/table"
    if sum(bool(MARK.match(l)) for l in ne) >= 0.6 * n: return "config/markup"
    return "source"

SIG = {
 "Python": [r"^\s*def \w+\(", r"^\s*(from \w[\w.]* )?import \w", r"\bself\.", r"^\s*elif\b", r"\bprint\(", r"\bNone\b|\bTrue\b|\bFalse\b", r"^\s*(if|for|while|with|class) .*:\s*$", r">>> "],
 "Java": [r"\bpublic (static |final )?(class|void|int|String)\b", r"System\.out\.", r"@Override", r"\bprivate (static )?(final )?\w+ \w+", r"\bnew [A-Z]\w*\("],
 "JavaScript/TS": [r"\b(const|let) \w+ =", r"=>", r"console\.log", r"\brequire\(", r"\bfunction\s*\w*\(", r"^\s*import .* from ['\"]", r"\bexport (default|const|function)"],
 "C/C++": [r"#include\s*[<\"]", r"\bint main\b", r"\bprintf\(", r"std::", r"\b(unsigned|struct|typedef|sizeof|malloc)\b", r"->\w", r"\bcout\b"],
 "C#": [r"^\s*using System", r"\bnamespace \w", r"Console\.Write", r"\bpublic (async )?(Task|void) \w+\("],
 "Go": [r"^\s*func ", r"^\s*package \w+", r":= ", r"\bfmt\.", r"\bgo func\b|\bchan\b"],
 "Rust": [r"\bfn \w+", r"\blet mut\b", r"^\s*impl\b", r"\bprintln!", r"&mut\b|::new\("],
 "SQL": [r"(?i)\bselect\b.*\bfrom\b", r"(?i)^\s*(insert into|create table|update \w+ set|delete from|alter table)", r"(?i)\bwhere\b", r"(?i)\b(join|group by|order by)\b"],
 "Shell": [r"^\s*\$ ", r"^\s*(sudo|apt(-get)?|yum|brew|export|chmod|mkdir|cd|ls|cat|echo|curl|wget|docker|kubectl|git|pip3?|npm|helm) ", r"\| *(grep|awk|sed|sort)\b", r"^\s*#!"],
 "R": [r"<- ", r"\blibrary\(", r"\bfunction\(", r"\$\w+"],
 "PHP": [r"<\?php", r"\$this->", r"\$\w+ = "],
 "Ruby": [r"^\s*def \w+[^(:]*$", r"^\s*end\s*$", r"\bputs\b", r"^\s*require ['\"]", r"\.each do\b"],
 "HTML/XML": [r"^\s*<[/!?]?[\w:-]+[ >/]", r"</\w+>"],
 "JSON": [r"^\s*\"[\w.-]+\"\s*:", r"^\s*[{}\[\]],?\s*$"],
 "YAML": [r"^\s*[\w.-]+:\s*\S", r"^\s*- \w"],
 "MATLAB": [r"^\s*%", r"\bdisp\(", r"\bzeros\(|\bones\(", r"\.\*|\.\^"],
 "Lisp/Scheme": [r"^\s*\((define|defun|let|lambda|setq)\b"],
 "Assembly": [r"(?i)^\s*(mov|push|pop|jmp|call|lea|add|sub)\s+\w+,"],
 "Kotlin/Swift/Scala": [r"^\s*(fun|val|var|func|object|def) \w+.*(:|\{|=)", r"\blet \w+: \w+"],
 "COBOL/RPG/JCL": [r"(?i)^\s*(//\w+\s+(job|exec|dd)\b|\d{5,6} |identification division|procedure division|perform |move .* to )"],
}
SIGC = {k: [re.compile(x) for x in v] for k, v in SIG.items()}

def lang(b):
    ne = [l for l in b if l.strip()]
    sc = {k: sum(1 for l in ne for r in rs if r.search(l)) / len(rs) ** 0.5 for k, rs in SIGC.items()}
    k, v = max(sc.items(), key=lambda x: x[1])
    return k if v >= 1 else "unidentified"

def source(stem):
    m = re.match(r"^([a-z0-9-]+) - ", stem)
    return m.group(1) if m else ("DTIC/NASA report" if re.match(r"^(DTIC|NASA)", stem) else "book/paper (no publisher prefix)")

for path in sys.argv[1:]:
    docs = [json.loads(l) for l in open(path)]
    kinds, langs, srcs, sizes = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    nb = 0
    for d in docs:
        srcs[source(d["stem"])] += 1
        sizes["book (>=60 pp)" if d.get("doc_pages", 999) >= 60 else "short (<60 pp)"] += 1
        for b in blocks(d):
            nb += 1; k = kind(b); kinds[k] += 1
            if k == "source": langs[lang(b)] += 1
    print(f"\n=== {path.split('/')[-1]}: {len(docs)} docs, {nb} code blocks (>=2 lines)")
    print("  doc size:", dict(sizes))
    print("  doc source:", srcs.most_common(8))
    print("  block kinds:", {k: f"{v} ({v/nb:.0%})" for k, v in kinds.most_common()})
    ns = sum(langs.values())
    print("  source-block languages (keyword-signature guess):", ", ".join(f"{k} {v/ns:.0%}" for k, v in langs.most_common(14)), f"| {len(langs)} distinct")
