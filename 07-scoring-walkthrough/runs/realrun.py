"""Real SE raw chapters through jina-v3 (COS ProfileEmbedder, standalone) + the real HTC scoring atoms.
Pieces capped at EMBEDDING_PIECE_TOKENS=2048 (memory: see walkthrough). Code ratio is a line heuristic (COS's
code-density endpoint is not in this standalone run)."""
import json, os, re, sys, time
PROFILE, PIECE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.environ.update({"EMBEDDING_PROFILE": "nomic-v2" if PROFILE == "nomic-v1.5" else PROFILE, "EMBEDDING_PIECE_TOKENS": PIECE, "EMBEDDING_PIECE_OVERLAP": "0",
                   "TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "4"})
import numpy as np, torch; torch.set_num_threads(4)
sys.path.insert(0, "<COS_REPO>")
from src.models.embedding.profile_embedder import ProfileEmbedder

RAW = "<CORPUS_ROOT>/collections/software-engineering/raw"
M = json.load(open("<HTC_REPO>/config/taxonomy_manifest.json"))
DOM = [d["slug"] for d in M["domains"]]; SUB = [s["slug"] for d in M["domains"] for s in d["subdomains"]]
KF = [k["slug"] for k in M["kf_definitions"]]
DOMAIN_OF = {s["slug"]: d["slug"] for d in M["domains"] for s in d["subdomains"]}
texts = [d["anchor_text"] for d in M["domains"]] + [s["anchor_text"] for d in M["domains"] for s in d["subdomains"]] + [k["anchor_text"] for k in M["kf_definitions"]]
if PROFILE == "nomic-v1.5":   # not a COS profile: the designs' original embedder, loaded from its cached snapshot
    from src.models.embedding.embedding_profile import EmbeddingProfile
    V15 = os.path.expanduser("~/.cache/huggingface/hub/models--nomic-ai--nomic-embed-text-v1.5/snapshots/e5cf08aadaa33385f5990def41f7a23405aec398")
    e = ProfileEmbedder(profile=EmbeddingProfile(name="nomic-v1.5", model_id=V15, dim=768, max_tokens=8192, task_style="prefix",
                                                 tasks={"query": "search_query: ", "document": "search_document: "}, licence="Apache-2.0"))
else:
    e = ProfileEmbedder()
assert e.is_loaded, e.unavailable_reason
t = time.time(); A = np.asarray(e.embed_texts(texts, task="query").embeddings)
print(f"anchors embedded: {len(texts)} in {time.time()-t:.0f}s", file=sys.stderr)
AD, AS, AK = A[:34], A[34:34 + len(SUB)], A[34 + len(SUB):]
CODE = re.compile(r"^\s{2,}\S|[{};]\s*$|^\s*(def|class|import|return|public|private|func|fn|let|var|const)\b")
PICKS = [("Apache Iceberg - The Definitive Guide (2).json", "33", "code-heavy book chapter"),
         ("hhp3_The xv6 Kernel (Previous Version)_xv6 Kernel-36 File-Re", None, "all-code kernel note"),
         ("LNCS 2944 - Databases, Information Systems, and Peer-to-Peer", "8", "long multi-piece chapter"),
         ("CockroachDB_The Full Package_ How Route architects its all-i", "Why Route uses CockroachDB", "business + database interview"),
         ("Net Ninja_GraphQL Tutorial_GraphQL Tutorial #6 - Setting up ", None, "video transcript"),
         ("Paul G. Allen School_Towards Principled Post-Training of Lar", None, "AI/ML lecture"),
         ("DTIC AD0737744 A Characterization of the Visibility Process ", "9", "OCR noise")]
names = os.listdir(RAW); out = []
for prefix, chap, label in PICKS:
    f = next(n for n in names if n.startswith(prefix) and "[DUPE]" not in n)
    chapters = json.load(open(os.path.join(RAW, f)))["chapters"]
    c = next((c for c in chapters if chap is None or str(c.get("number")) == chap or (c.get("title") or "").startswith(chap)), chapters[0])
    text = c["content"]
    lines = [l for l in text.splitlines() if l.strip()]
    code = sum(1 for l in lines if CODE.search(l)) / max(len(lines), 1)
    t = time.time(); ps = e.embed_pieces(text, task="document")
    V = np.asarray([p.embedding for p in ps])
    rec = {"label": label, "file": f, "title": c.get("title"), "chars": len(text), "code_ratio": round(code, 2),
           "pieces": [p.token_count for p in ps], "secs": round(time.time() - t, 1),
           "raw": [{"D": dict(zip(DOM, (v @ AD.T).tolist())), "S": dict(zip(SUB, (v @ AS.T).tolist())),
                    "K": dict(zip(KF, (v @ AK.T).tolist()))} for v in V],
           "pooled_vector_raw": None}
    mean = V.mean(axis=0); pv = mean / np.linalg.norm(mean)          # = PieceScorePooler.pool_vector
    rec["pooled_vector_raw"] = {"D": dict(zip(DOM, (pv @ AD.T).tolist())), "S": dict(zip(SUB, (pv @ AS.T).tolist())),
                                "K": dict(zip(KF, (pv @ AK.T).tolist()))}
    out.append(rec)
    print(f"{label}: {len(ps)} piece(s) {rec['pieces']} in {rec['secs']}s", file=sys.stderr)
json.dump(out, open(OUT, "w"))
