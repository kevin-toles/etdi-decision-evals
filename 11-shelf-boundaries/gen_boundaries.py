"""ETDI-1.0.720: config/subdomain_boundaries.json from the accepted SUBDOMAIN-CANONICALIZATION-CANDIDATES.md rev 3
(§4 group boundaries, §5 scope pairs; the §6 domain note is carried unchanged — rev 3 §11 changes P109 and P118 only).
    python3 gen_boundaries.py <candidates.md> <current boundaries.json> <out.json>"""
import json, re, sys
md, current, out = sys.argv[1:4]
text = open(md, encoding="utf-8").read()
section = lambda n: text.split(f"\n## {n}.", 1)[1].split("\n## ", 1)[0]
slugs = lambda cell: re.findall(r"`([a-z0-9-]+)`", cell)
cells = lambda line: [c.strip() for c in line.strip().strip("|").split("|")]
groups = []
for line in section(4).splitlines():
    if re.match(r"\| G\d+ \|", line):
        gid, name, members, boundary = cells(line)[:4]
        groups.append({"id": gid, "name": name, "members": slugs(members), "boundary": boundary})
pairs, bounds = [], {}
for line in section(5).splitlines():
    if re.match(r"\| P\d+ \|", line):
        _, a, b, why = cells(line)[:4]
        (a,), (b,) = slugs(a), slugs(b)
        pairs.append([a, b]); bounds[f"{a}|{b}"] = why
prior = json.load(open(current))
doc = {"source": "HTC-MULTIDIM-2.0 Appendix A v1.2 — accepted SUBDOMAIN-CANONICALIZATION-CANDIDATES.md rev 3 (2026-10-21); generated, do not edit",
       "groups": groups, "scope_pairs": pairs, "scope_boundaries": bounds, "domain_notes": prior["domain_notes"]}
json.dump(doc, open(out, "w"), ensure_ascii=False, indent=1)
old = prior
print(json.dumps({"groups": len(groups), "pairs": len(pairs),
                  "groups_changed": [g["id"] for g, o in zip(groups, old["groups"]) if g != o],
                  "pairs_changed": [k for k in bounds if bounds[k] != old["scope_boundaries"].get(k)],
                  "pairs_added": [k for k in bounds if k not in old["scope_boundaries"]],
                  "pairs_removed": [k for k in old["scope_boundaries"] if k not in bounds]}, indent=1))
