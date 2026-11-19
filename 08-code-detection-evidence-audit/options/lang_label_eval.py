"""Language labelling of extracted code blocks, scored against the four-reviewer block profile (blocks_2026-10-28,
200 blocks, consensus language). Methods:
  cos      COS LanguageDetector as it runs today (tree-sitter for 4 languages + keyword heuristics)
  ts       best grammar: parse with every grammar (the structural analyzer's 20 + shell, SQL, JSON, YAML, XML, HTML,
           CSS, Makefile, Dockerfile, R, LaTeX, assembly), keep the one with the fewest error lines per non-blank line
  ts+m     ts with marker rules written before scoring (not tuned on these labels): C/C++/Objective-C by the
           structural analyzer's HeaderLanguage markers; permissive grammars (bash, yaml, make, latex, r) win only with
           their own markers; a block with no grammar under 0.5 error-line share is 'no grammar' (abstain)
Also calls the live structural analyzer (/v1/analyze/skeletonize) with the ts+m language for blocks in its 20
languages and counts blocks that yield >= 1 declaration (structural enrichment coverage).
    PYTHONPATH=<tspkgs> python3 <this> <blocks dir> <COS repo>"""
import ast, collections, json, os, re, sys, urllib.request
B, COS = sys.argv[1], sys.argv[2]
sys.path.insert(0, COS)
from tree_sitter_language_pack import get_parser

CAT = {"python": "Python", "java": "Java", "c": "C", "cpp": "C++", "javascript": "JavaScript/TypeScript", "typescript": "JavaScript/TypeScript",
       "go": "Go", "rust": "Rust", "kotlin": "Kotlin", "swift": "Swift", "ruby": "Ruby", "r": "R", "bash": "Shell/Bash", "shell": "Shell/Bash",
       "sql": "SQL", "html": "HTML", "xml": "XML", "css": "CSS", "yaml": "YAML", "json": "JSON", "make": "Makefile", "latex": "LaTeX",
       "asm": "Assembly", "ocaml": "OCaml/F#", "haskell": "Haskell", "csharp": "C#", "scala": "Scala", "php": "PHP", "lua": "Lua",
       "elixir": "Elixir", "groovy": "Groovy", "objc": "Objective-C", "zig": "Zig", "dockerfile": "Dockerfile"}
SAS_LANGS = ["c", "cpp", "csharp", "go", "haskell", "java", "javascript", "kotlin", "lua", "ocaml", "php", "python", "ruby", "rust",
             "scala", "typescript", "zig", "swift", "objc", "elixir", "groovy"]
EXTRA = ["bash", "sql", "json", "yaml", "xml", "html", "css", "make", "dockerfile", "r", "latex", "asm"]
GRAMMARS = SAS_LANGS + EXTRA
PARSERS = {g: get_parser(g) for g in GRAMMARS}
PERMISSIVE = {"bash", "yaml", "make", "latex", "r", "dockerfile"}
MARK = {"bash": re.compile(r"(^|\n)\s*(\$|#)\s+\w|(^|\n)\s*(sudo|cd|ls|echo|export|apt(-get)?|yum|pip|npm|git|chmod|mkdir|cat|grep|curl|docker|kubectl)\b"),
        "yaml": re.compile(r"(^|\n)\s*(- )?[\w.-]+:\s+\S.*(\n\s+[\w.-]+:|\n\s*- )"),
        "make": re.compile(r"(^|\n)[\w.$()/-]+\s*:[^=]*\n\t"),
        "latex": re.compile(r"\\(begin|end|section|usepackage|documentclass|frac|item)\b"),
        "r": re.compile(r"<-|\blibrary\(|\bfunction\s*\(|\bdata\.frame\("),
        "dockerfile": re.compile(r"(^|\n)\s*(FROM|RUN|COPY|ENTRYPOINT|CMD|WORKDIR)\s")}
OBJC = re.compile(r"(?m)^\s*#\s*import\b|@(interface|protocol|implementation|end|property|synthesize)\b")
CPP = re.compile(r"\bnamespace\s*\w*\s*[{=]|\busing\s+namespace\b|\bclass\s+\w+\s*[:{;<]|\btemplate\s*<|\b(public|private|protected)\s*:|\w::[A-Za-z_~]|std::|cout\s*<<")


def err_lines(tree):
    bad = set(); st = [tree.root_node]
    while st:
        n = st.pop()
        if n.is_error or n.is_missing:
            bad.update(range(n.start_point[0], n.end_point[0] + 1))
        elif n.has_error:
            st.extend(n.children)
    return bad


def ts_rank(code):
    src = code.encode("utf8"); lines = code.split("\n"); nz = {i for i, l in enumerate(lines) if l.strip()} or {0}
    out = []
    for g, p in PARSERS.items():
        t = p.parse(src); e = len(err_lines(t) & nz) / len(nz)
        out.append((e, -t.root_node.named_child_count, g))
    return sorted(out)


def ts_label(code):
    return ts_rank(code)[0][2]


def ts_marker_label(code):
    rank = ts_rank(code)
    for e, _, g in rank:
        if e >= 0.5: return None                               # no grammar fits: abstain
        if g in PERMISSIVE and not MARK[g].search(code): continue
        if g in ("c", "cpp", "objc"):
            return "objc" if OBJC.search(code) else "cpp" if CPP.search(code) else "c"
        return g
    return None


def main():
    from src.extractors.language_detector import get_language_detector
    cos = get_language_detector()
    sheet = {it["id"]: it for it in json.load(open(os.path.join(B, "block_sheet.json")))["items"]}
    rep = json.load(open(os.path.join(B, "block_report.json")))["blocks"]
    known = set(CAT.values())
    res = collections.defaultdict(collections.Counter); per_lang = collections.defaultdict(collections.Counter)
    sas = collections.Counter(); abst = collections.Counter()
    for bid, meta in rep.items():
        code = "\n".join(sheet[bid]["BLOCK"])
        gold = meta["language"]
        lab_cos = CAT.get(cos.detect_language(code)[0].lower())
        lab_ts = CAT.get(ts_label(code)); g_tm = ts_marker_label(code); lab_tm = CAT.get(g_tm) if g_tm else None
        group = "named language" if gold in known else "no grammar / unnamed"
        for m, lab in (("cos", lab_cos), ("ts", lab_ts), ("ts+m", lab_tm)):
            res[(group, m)]["n"] += 1
            if group == "named language":
                res[(group, m)]["correct"] += lab == gold
                per_lang[gold][m] += lab == gold
            else:
                res[(group, m)]["abstained"] += lab is None
        if group == "named language": per_lang[gold]["n"] += 1
        if g_tm in SAS_LANGS:
            sas["called"] += 1
            try:
                req = urllib.request.Request("http://localhost:8088/v1/analyze/skeletonize", data=json.dumps({"source": code, "language": g_tm}).encode(),
                                             headers={"Content-Type": "application/json"})
                r = json.load(urllib.request.urlopen(req, timeout=30))
                nd = len(r.get("declarations") or []); sas["with_declarations"] += nd > 0; sas["declarations"] += nd
                sas[f"correct_language_called"] += lab_tm == gold
            except Exception as e:
                sas["errors"] += 1
    print(f"{'group':24s} {'method':6s} {'n':>4s} {'correct':>8s} {'abstained':>10s}")
    for (g, m), c in sorted(res.items()):
        print(f"{g:24s} {m:6s} {c['n']:4d} {c['correct']:>4d} {c['correct'] / c['n']:5.0%}" if g == "named language" else
              f"{g:24s} {m:6s} {c['n']:4d} {'':>8s} {c['abstained']:>4d} {c['abstained'] / c['n']:5.0%}")
    print("\nper language (n: cos / ts / ts+m correct)")
    for l, c in sorted(per_lang.items(), key=lambda x: -x[1]["n"]):
        print(f"  {l:24s} {c['n']:3d}: {c['cos']:3d} / {c['ts']:3d} / {c['ts+m']:3d}")
    print("\nstructural analyzer skeletonize on ts+m blocks in its languages:", dict(sas))
    json.dump({"summary": {f"{g}|{m}": dict(c) for (g, m), c in res.items()}, "per_language": {k: dict(v) for k, v in per_lang.items()}, "sas": dict(sas)},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lang_label_eval.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
