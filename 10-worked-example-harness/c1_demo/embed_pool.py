"""C1 (#40) demo, step 1 (COS env): the platform's real nomic-v2 ProfileEmbedder embeds the question (task query) and
every candidate chapter the keyword scan found (task document, whole chapter in pieces, as V005 would). Candidates are the
chapters in ../c1_scan.json up to 600,000 characters (the two MySQL 8.4 Reference Manual "chapters", 5.1M and 10.1M
characters, are left out: chapter-boundary defects, OQ#50). Resumable; memory guard as embed_profile.py.
    cd Code-Orchestrator-Service && HF_HUB_OFFLINE=1 .venv/bin/python <this>"""
import json, os, subprocess, sys, time
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
QUESTION = "How should I rotate database credentials?"
MAX_CHARS, MIN_FREE_GB = 600_000, 1.2


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


scan = json.loads((HERE.parent / "c1_scan.json").read_text())
seen, cands = set(), []
for term, rows in scan["terms"].items():
    for r in rows:
        key = (r["book"], r["chapter"], r["pages"])
        if key in seen or r["chars"] > MAX_CHARS:
            continue
        seen.add(key); cands.append({"id": f"c{len(cands):03d}", "book": r["book"], "chapter": r["chapter"], "pages": r["pages"]})
texts = {}
for c in cands:
    d = json.loads((RAW / f"{c['book']}.json").read_text())
    pages = {int(p["page_number"]): p.get("text") or "" for p in d.get("pages") or [] if str(p.get("page_number", "")).isdigit()}
    s, e = (int(x) for x in c["pages"].split("-"))
    texts[c["id"]] = "\n".join(pages.get(i, "") for i in range(s, e + 1))
    c["chars"] = len(texts[c["id"]])
(HERE / "candidates.json").write_text(json.dumps(cands, indent=1))
print(f"{len(cands)} candidates, {sum(c['chars'] for c in cands):,} characters", flush=True)

guard()
emb = ProfileEmbedder(profile=EmbeddingProfileRegistry.PROFILES["nomic-v2"], device="cpu")
assert emb.is_loaded, emb.unavailable_reason
if not (HERE / "query.npy").exists():
    np.save(HERE / "query.npy", np.asarray(emb.embed_text(QUESTION, task="query").embedding, dtype=np.float32))
t0 = time.time()
for n, c in enumerate(cands):
    out = HERE / "pieces" / f"{c['id']}.npz"
    if out.exists() or not texts[c["id"]].strip():
        continue
    guard()
    ps = emb.embed_pieces(texts[c["id"]], task="document", batch_size=1)
    np.savez(out, vectors=np.asarray([p.embedding for p in ps], dtype=np.float32), tokens=np.array([p.token_count for p in ps]))
    print(f"{n + 1}/{len(cands)} {c['id']} {len(ps)} pieces; {time.time() - t0:.0f}s; free {free_gb():.1f} GB", flush=True)
print("done", flush=True)
