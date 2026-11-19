"""One pass over a random SE raw sample plus all TF raw: per term, how many books / chapters mention it, total hits,
top books, and real snippets. Feeds CURRENT-OPEN-QUESTIONS.md examples (2026-11-09). Read-only."""
import json, os, random, re, sys, collections, itertools

ROOT = "<CORPUS_ROOT>/collections"
N_SE = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
TERMS = {  # key: regex
    "rag_full": r"retrieval[- ]augmented generation", "rag_abbr": r"\bRAG\b", "retrieval": r"\bretrieval\b",
    "reward_hacking": r"reward hacking", "network_partition": r"network partition", "consensus": r"\bconsensus\b",
    "replication": r"\breplication\b", "gossip": r"gossip protocol|epidemic (protocol|broadcast|dissemination)",
    "degree_distribution": r"degree distribution", "information_theory": r"information theory", "entropy": r"\bentropy\b",
    "huffman": r"\bhuffman\b", "econometric": r"econometric", "bloom_filter": r"bloom filter", "idempotent_consumer": r"idempotent (consumer|receiver)",
    "xml_etree": r"xml\.etree|ElementTree", "defusedxml": r"defusedxml", "xxe": r"\bXXE\b|XML external entit", "lmdb": r"\bLMDB\b",
    "figure_load_balancer": r"Figure [0-9]+[-.][0-9]+\.? [^\n]{0,60}load balanc", "fence": r"^```", "vault_dynamic_secrets": r"dynamic secrets",
    "two_phase_commit": r"two-phase commit|\b2PC\b", "strain_displacement": r"strain[- ]displacement", "secret_management": r"secrets? management",
}
RX = {k: re.compile(v, re.I | re.M) for k, v in TERMS.items()}


def scan(paths, label):
    stats = {k: {"books": 0, "chapters": 0, "hits": 0, "top": collections.Counter(), "snips": []} for k in TERMS}
    by_method = collections.Counter(); fence_by_method = collections.Counter(); books = 0; chapters = 0
    for p in paths:
        try: d = json.load(open(p))
        except Exception: continue
        books += 1
        meth = (d.get("metadata") or {}).get("extraction_method") or "?"; by_method[meth] += 1
        name = os.path.basename(p)[:-5]
        chs = d.get("chapters") or []
        pages = {}
        for pg in d.get("pages") or []:
            try: pages[int(pg.get("page_number"))] = pg.get("text") or ""
            except Exception: pass
        units = []
        for c in chs:
            s, e = c.get("start_page") or 0, c.get("end_page") or 0
            units.append(((c.get("title") or "")[:60], "\n".join(pages.get(i, "") for i in range(s, e + 1))))
        if not units: units = [("(whole)", "\n".join(pages.values()))]
        chapters += len(units)
        seen = set()
        for title, txt in units:
            for k, rx in RX.items():
                hits = rx.findall(txt) if k != "fence" else rx.findall(txt)
                if not hits: continue
                n = len(hits); st = stats[k]; st["chapters"] += 1; st["hits"] += n; st["top"][name] += n
                if k == "fence": fence_by_method[meth] += n
                if k not in seen: st["books"] += 1; seen.add(k)
                if len(st["snips"]) < 4:
                    m = rx.search(txt); a = max(0, m.start() - 220); b = min(len(txt), m.end() + 220)
                    st["snips"].append({"book": name[:80], "chapter": title, "text": " ".join(txt[a:b].split())})
    out = {"label": label, "books": books, "chapters": chapters, "by_method": dict(by_method), "fence_by_method": dict(fence_by_method), "terms": {}}
    for k, st in stats.items():
        out["terms"][k] = {"books": st["books"], "chapters": st["chapters"], "hits": st["hits"], "top": st["top"].most_common(5), "snips": st["snips"]}
    return out


se_files = [e.path for e in itertools.islice(os.scandir(f"{ROOT}/software-engineering/raw"), 0, 400000) if e.name.endswith(".json")]
random.seed(1109); se_sample = random.sample(se_files, N_SE)
tf_files = [os.path.join(dp, f) for dp, _, fs in os.walk(f"{ROOT}/theoretical-foundations/raw") for f in fs if f.endswith(".json")]
res = {"se": scan(se_sample, f"SE raw, random {N_SE} of {len(se_files)}"), "tf": scan(tf_files, f"TF raw, all {len(tf_files)}")}
json.dump(res, open(sys.argv[2], "w"), indent=1)
print("done")
