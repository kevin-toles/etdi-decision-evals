"""Frozen grading rubric for the golden-set panel (OQ#18 pilot, 2026-11-13). Every panelist — Claude or local — gets
exactly this system prompt and the same per-item message. Blind: no proposer labels, notes, roles, key-point claims,
or which search/model found the passage. Changing this file after grading starts invalidates the run."""
import json

TAX = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
DOMAINS = {d["slug"]: [s["slug"] if isinstance(s, dict) else s for s in d["subdomains"]] for d in TAX["domains"]}
KFS = {k["slug"]: f'{k["semantic_role"]} — {k["description"]}' for k in TAX["kf_definitions"]}

SYSTEM = """You are an independent expert grader building an evaluation set for a technical-library search system.
For each item you get a QUESTION, the KEY POINTS of its accepted, community-vetted answer, and one PASSAGE taken from a
book, paper, article or talk transcript. Judge the passage on its own text only. Other graders judge the same items
independently; do not guess what anyone else would say.

1. grade (relevance of the passage to the question):
   3 = states the core of the answer (the central key point or points) in a way a reader could act on
   2 = states part of the answer (at least one key point) but misses the core, or states it only briefly
   1 = background or related material only: useful context, states no key point
   0 = not relevant to this question (shared vocabulary only, or a different question)
2. covers: ids of the key points the passage itself substantively states (not merely mentions a term from). Empty if none.
3. beyond_key_points: true only if the passage gives a correct element of the answer that none of the key points contain.
4. role: "direct" if the passage addresses the question as asked; "foundation" if it is theory, definitions, proofs or
   research that the answer rests on without addressing the question itself; "none" if grade is 0.
5. Labels describe the PASSAGE's own subject (not the question). Use only slugs from the TAXONOMY below:
   primary = {domain, subdomain} that best files this passage; secondary = 0 to 3 further {domain, subdomain} it
   genuinely also belongs to; knowledge_function = the passage's function, one of the four KNOWLEDGE FUNCTIONS.
   A subdomain must belong to the domain you pair it with.
6. ambiguous: true if the passage could reasonably be graded or filed two different ways; say why in note.
7. note: at most 40 words, the reason for the grade.

KNOWLEDGE FUNCTIONS:
""" + "\n".join(f"- {k}: {v}" for k, v in KFS.items()) + """

TAXONOMY (domain: subdomains):
""" + "\n".join(f"- {d}: {', '.join(s)}" for d, s in DOMAINS.items()) + """

Answer with one JSON object only, exactly matching the schema."""

LABEL = {"type": "object", "additionalProperties": False, "required": ["domain", "subdomain"],
         "properties": {"domain": {"type": "string"}, "subdomain": {"type": "string"}}}
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["grade", "covers", "beyond_key_points", "role", "primary", "secondary", "knowledge_function",
                       "ambiguous", "note"],
          "properties": {"grade": {"type": "integer", "enum": [0, 1, 2, 3]},
                         "covers": {"type": "array", "items": {"type": "string"}},
                         "beyond_key_points": {"type": "boolean"},
                         "role": {"type": "string", "enum": ["direct", "foundation", "none"]},
                         "primary": LABEL, "secondary": {"type": "array", "items": LABEL},
                         "knowledge_function": {"type": "string", "enum": list(KFS)},
                         "ambiguous": {"type": "boolean"}, "note": {"type": "string"}}}

def item_message(record, question):
    kps = "\n".join(f"- {k['id']}: {k['text']}" for k in question["key_points"])
    passage = "\n[...]\n".join(e["text"] for e in record["evidence"])
    return (f"QUESTION: {question['query']}\n\nKEY POINTS:\n{kps}\n\n"
            f"PASSAGE (from: {record['chapter_ref'].rsplit('#', 1)[0]} — section '{record['chapter_title']}'):\n{passage}")

def validate(ans, question):
    """Schema-level checks the JSON schema cannot express. Returns a list of problems (empty = valid)."""
    p = []
    kp = {k["id"] for k in question["key_points"]}
    if set(ans.get("covers", [])) - kp: p.append(f"unknown key points {sorted(set(ans['covers']) - kp)}")
    for lab in [ans.get("primary", {})] + list(ans.get("secondary", [])):
        if lab.get("domain") not in DOMAINS: p.append(f"unknown domain {lab.get('domain')}")
        elif lab.get("subdomain") not in DOMAINS[lab["domain"]]: p.append(f"{lab.get('subdomain')} not under {lab['domain']}")
    if len(ans.get("secondary", [])) > 3: p.append("more than 3 secondary")
    return p
