"""Generate PAIR_GRADER_INSTRUCTIONS.md plus the three pair-grader agent files from one source text.
The taxonomy block is copied verbatim from panel/GRADER_INSTRUCTIONS.md (same slugs as the golden set).
Usage: python3 -I make_pair_graders.py
"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
G = open(os.path.join(HERE, "..", "panel", "GRADER_INSTRUCTIONS.md")).read()
tax = G[G.index("TAXONOMY (domain: subdomains):"):G.index("OUTPUT:")].rstrip()
TECH = ("Array, String, Hash Table, Dynamic Programming, Math, Sorting, Greedy, Depth-First Search, Binary Search, "
        "Database, Matrix, Tree, Breadth-First Search, Bit Manipulation, Two Pointers, Prefix Sum, Heap (Priority Queue), "
        "Simulation, Binary Tree, Stack, Graph, Counting, Sliding Window, Design, Enumeration, Backtracking, Union Find, "
        "Linked List, Ordered Set, Number Theory, Monotonic Stack, Segment Tree, Trie, Combinatorics, Bitmask, Queue, "
        "Recursion, Divide and Conquer, Memoization, Binary Indexed Tree, Binary Search Tree, Geometry, Hash Function, "
        "String Matching, Topological Sort, Shortest Path, Rolling Hash, Game Theory, Interactive, Data Stream, "
        "Monotonic Queue, Brainteaser, Doubly-Linked List, Merge Sort, Randomized, Counting Sort, Iterator, Concurrency, "
        "Quickselect, Probability and Statistics, Suffix Array, Bucket Sort, Line Sweep, Minimum Spanning Tree, Shell, "
        "Reservoir Sampling, Radix Sort, Eulerian Circuit, Strongly Connected Component, Rejection Sampling, "
        "Biconnected Component")
BODY = f"""You are an independent expert judge building an evaluation set for a coding-problem search system.
Each item is a PAIR of programming problem statements, A and B, from different sources (interview sites, competitive
programming archives, practice sites). Titles have been removed and wording, input format and story differ between
sources. Judge from the two statements only. Other judges see the same items independently; do not guess what anyone
else would say. Do not write code.

1. grade (how closely B matches A):
   3 = same problem: the same task — a correct solution to one solves the other after changing only input/output
       handling, names, indexing or the story. Small constraint differences that do not change the intended
       solution still count.
   2 = same pattern: a different task, but the intended efficient solution of both rests on the same core technique
       or key insight (e.g. both are solved by a sliding window over the array; both by DP over subsets), so knowing
       how to solve B gives the main idea for A.
   1 = related: overlapping topic or data structure (both about trees, both about strings) but a different core
       technique, or B is a much easier/harder sub-part of A.
   0 = different: no meaningful overlap in task or technique.
2. technique_a / technique_b: for EACH problem, the ONE tag from TECHNIQUES that names the key idea of its intended
   efficient solution. Prefer the most specific technique (Sliding Window over Array, Topological Sort over Graph,
   Monotonic Stack over Stack). Use a data-type tag (Array, String, Matrix, Linked List, Tree, Graph, Database) only
   when no technique tag applies; use Simulation for problems solved by direct step-by-step modelling.
3. primary_a / primary_b: the {{domain, subdomain}} from the TAXONOMY that best files each problem's subject.
   secondary_a / secondary_b: 0 to 3 further {{domain, subdomain}} each problem genuinely also belongs to.
   A subdomain must belong to the domain you pair it with. Use only slugs from the TAXONOMY.
4. ambiguous: true if the grade could reasonably be one level different (e.g. same problem vs same pattern); say why.
5. note: at most 30 words, the reason for the grade (name the shared technique for grade 2).

TECHNIQUES (choose exactly one per problem): {TECH}

{tax}

OUTPUT: you will be given a sheet path and an output path. Read the sheet (a JSON object with "items", each with
"item_id", "problem_a" and "problem_b"). Judge every item independently. Write exactly the output file: a JSON object
{{"model": "<MODEL>", "verdicts": {{"<item_id>": {{"grade": 0-3, "technique_a": "...", "technique_b": "...",
"primary_a": {{"domain": "...", "subdomain": "..."}}, "secondary_a": [{{"domain": "...", "subdomain": "..."}}, ...],
"primary_b": {{"domain": "...", "subdomain": "..."}}, "secondary_b": [{{"domain": "...", "subdomain": "..."}}, ...],
"ambiguous": bool, "note": "..."}}, ...}}}} covering every item id, and nothing else.
Then reply with one line: the number of items judged.
"""
open(os.path.join(HERE, "PAIR_GRADER_INSTRUCTIONS.md"), "w").write(BODY.replace("<MODEL>", "<your model id>"))
AG = os.path.expanduser("~/POC/.claude/agents")
for model in ("claude-sonnet-5-5", "claude-opus-4-8", "claude-fable-5-2"):
    name = "pair-grader-" + model.removeprefix("claude-")
    head = (f"---\nname: {name}\ndescription: Blind judge for the ETDI golden-set pattern pairs ({model}). Reads a pair sheet, "
            "grades how closely problem B matches problem A, labels each problem's technique and files it in the HTC taxonomy, "
            "writes verdicts JSON.\nmodel: " + model + "\ntools: Read, Write\n---\n")
    open(os.path.join(AG, name + ".md"), "w").write(head + BODY.replace("<MODEL>", model))
    print("wrote", name)
