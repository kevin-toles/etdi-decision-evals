"""Worked examples, step 2 (COS env): the platform's real nomic-v2 ProfileEmbedder embeds each question (task query)
and the top-N candidate chapters per question from scan_all.json (task document, whole chapter in pieces, as V005
would; same method as c1_demo/embed_pool.py). Chapters shared between questions are embedded once. Resumable; memory
guard as embed_profile.py.    cd Code-Orchestrator-Service && HF_HUB_OFFLINE=1 .venv/bin/python <this> [N]"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
os.environ.pop("EMBEDDING_PIECE_TOKENS", None)
os.environ.update({"EMBEDDING_PIECE_OVERLAP": "0", "TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "4"})
import numpy as np, torch
torch.set_num_threads(4)
sys.path.insert(0, os.getcwd())
from src.models.embedding.embedding_profiles import EmbeddingProfileRegistry
from src.models.embedding.profile_embedder import ProfileEmbedder

HERE = Path(__file__).parent
RAW = Path("<CORPUS_ROOT>/collections/software-engineering/raw")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
QUESTIONS = json.loads((HERE / "questions.json").read_text())
MIN_FREE_GB = 1.2


def free_gb():
    pages = {l.split(":")[0]: int(l.split(":")[1].strip().rstrip(".")) for l in subprocess.run(
        ["vm_stat"], capture_output=True, text=True).stdout.splitlines()[1:] if ":" in l}
    return sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative")) * 16384 / 1e9


def guard():
    for _ in range(30):
        if free_gb() >= MIN_FREE_GB:
            return
        print(f"memory guard: {free_gb():.2f} GB free, waiting", flush=True); time.sleep(60)
    sys.exit(3)


def cid(book, chapter, pages):
    return hashlib.sha1(f"{book}|{chapter}|{pages}".encode()).hexdigest()[:12]


scan = json.loads((HERE / "scan_all.json").read_text())
cands, pools = {}, {}
for q in QUESTIONS:
    pools[q] = []
    for r in scan["pools"].get({"A6": "A5"}.get(q, q), [])[:N]:
        k = cid(r["book"], r["chapter"], r["pages"])
        cands.setdefault(k, {"id": k, "book": r["book"], "chapter": r["chapter"], "pages": r["pages"], "chars": r["chars"]})
        pools[q].append(k)
(HERE / "candidates.json").write_text(json.dumps({"candidates": cands, "pools": pools}, indent=1))
print(f"{len(cands)} distinct chapters, {sum(c['chars'] for c in cands.values()):,} characters", flush=True)
(HERE / "pieces").mkdir(exist_ok=True); (HERE / "queries").mkdir(exist_ok=True)
guard()
emb = ProfileEmbedder(profile=EmbeddingProfileRegistry.PROFILES["nomic-v2"], device="cpu")
assert emb.is_loaded, emb.unavailable_reason
for q, text in QUESTIONS.items():
    f = HERE / "queries" / f"{q}.npy"
    if not f.exists():
        np.save(f, np.asarray(emb.embed_text(text, task="query").embedding, dtype=np.float32))
t0 = time.time()
for n, c in enumerate(cands.values()):
    out = HERE / "pieces" / f"{c['id']}.npz"
    if out.exists():
        continue
    d = json.loads((RAW / f"{c['book']}.json").read_text())
    pages = {}
    for p in d.get("pages") or []:
        try: pages[int(p["page_number"])] = p.get("text") or ""
        except Exception: pass
    s, e = (int(x) for x in c["pages"].split("-"))
    text = "\n".join(pages.get(i, "") for i in range(s, e + 1))
    if not text.strip():
        continue
    guard()
    ps = emb.embed_pieces(text, task="document", batch_size=1)
    np.savez(out, vectors=np.asarray([p.embedding for p in ps], dtype=np.float32), tokens=np.array([p.token_count for p in ps]))
    print(f"{n + 1}/{len(cands)} {c['id']} {len(ps)} pieces; {time.time() - t0:.0f}s; free {free_gb():.1f} GB", flush=True)
print("done", flush=True)
