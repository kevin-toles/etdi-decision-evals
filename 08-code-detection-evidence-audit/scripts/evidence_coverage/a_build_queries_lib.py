"""Shared normaliser for the evidence-coverage step (pre-registered; see a_build_queries.py)."""
import re
def norm(s):
    for a, b in (("−", "-"), ("–", "-"), ("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'"), ("␣", " "), (" ", " "), ("ﬁ", "fi"), ("ﬂ", "fl")):
        s = s.replace(a, b)
    s = re.sub(r"(?<![A-Za-z0-9])(?:[A-Za-z0-9] ){2,}[A-Za-z0-9](?![A-Za-z0-9])", lambda m: m.group(0).replace(" ", ""), s)
    s = " ".join(s.split())
    s = re.sub(r"^(?:\([^)\s]{1,30}\)\s*)?(?:\$|%|>>>|>)\s+", "", s)
    return s
