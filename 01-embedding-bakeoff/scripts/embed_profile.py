"""ETDI-1.0.742 phase B (COS env, one profile per process): the profile's real COS ProfileEmbedder (local cache only)
embeds the 461 subdomain + 4 KF anchors (task query) and reads every held-out chapter whole with embed_pieces (task
document, the profile's own tokenizer, default piece size: nomic-v2 480, nomic-v1.5 8,160, jina-v3 2,048 on CPU; v0.25 candidates multilingual-e5-large 480, bge-m3 plus jina-v5-small 2,048 on CPU).
Resumable: one pieces/<i>.npz per chapter; pieces embed one at a time (batch 1) so CPU attention memory stays bounded;
a memory guard pauses below MIN_FREE_GB and exits 3 (resume later) if memory does not recover.
    cd Code-Orchestrator-Service && python3 <this> <profile> <heldout.json> <manifest.json> <out_dir>"""
import json, os, subprocess, sys, time
from pathlib import Path
PROFILE, HELD, MANIFEST, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
os.environ.pop("EMBEDDING_PIECE_TOKENS", None)
os.environ.update({"EMBEDDING_PIECE_OVERLAP": "0", "TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "4"})
import numpy as np, torch
torch.set_num_threads(4)
sys.path.insert(0, os.getcwd())
from src.models.embedding.embedding_profiles import EmbeddingProfileRegistry
from src.models.embedding.profile_embedder import ProfileEmbedder

MIN_FREE_GB = 1.2


def free_gb() -> float:
    pages = {l.split(":")[0]: int(l.split(":")[1].strip().rstrip(".")) for l in subprocess.run(
        ["vm_stat"], capture_output=True, text=True).stdout.splitlines()[1:] if ":" in l}
    return sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative")) * 16384 / 1e9


def guard() -> None:
    for _ in range(30):
        if free_gb() >= MIN_FREE_GB:
            return
        print(f"memory guard: {free_gb():.2f} GB free < {MIN_FREE_GB}, waiting", flush=True)
        time.sleep(60)
    print("memory guard: no recovery in 30 min — exiting for a later resume", flush=True)
    sys.exit(3)


OUT.mkdir(parents=True, exist_ok=True); (OUT / "pieces").mkdir(exist_ok=True)
embedder = ProfileEmbedder(profile=EmbeddingProfileRegistry.PROFILES[PROFILE], device="cpu")
assert embedder.is_loaded, embedder.unavailable_reason
m = json.loads(MANIFEST.read_text())
if not (OUT / "anchors.npz").exists():
    subs = [(d["slug"], s["slug"], s["anchor_text"]) for d in m["domains"] for s in d["subdomains"]]
    kfs = [(k["slug"], k["anchor_text"]) for k in m["kf_definitions"]]
    guard()
    vec = np.asarray(embedder.embed_texts([t for *_, t in subs] + [t for _, t in kfs], task="query", batch_size=8).embeddings)
    np.savez(OUT / "anchors.npz", sub_vectors=vec[:len(subs)].astype(np.float32), kf_vectors=vec[len(subs):].astype(np.float32),
             sub_slugs=np.array([s for _, s, _ in subs]), sub_domains=np.array([d for d, _, _ in subs]),
             kf_slugs=np.array([k for k, _ in kfs]))
    print(f"anchors: {len(subs)} subdomains + {len(kfs)} KFs", flush=True)
held = json.loads(HELD.read_text())
cases = [(slug, ref, text) for slug in sorted(held) for ref, text in held[slug]]
json.dump([(slug, ref) for slug, ref, _ in cases], open(OUT / "cases.json", "w"))
done = sum((OUT / "pieces" / f"{i}.npz").exists() for i in range(len(cases)))
t0, chars_done, total_chars = time.time(), 0, sum(len(t) for *_, t in cases[done:])
for i, (slug, ref, text) in enumerate(cases):
    path = OUT / "pieces" / f"{i}.npz"
    if path.exists():
        continue
    guard()
    pieces = embedder.embed_pieces(text, task="document", batch_size=1)
    np.savez(path, vectors=np.asarray([p.embedding for p in pieces], dtype=np.float16),
             tokens=np.array([p.token_count for p in pieces]))
    chars_done += len(text)
    rate = chars_done / max(time.time() - t0, 1e-9)
    print(f"{i + 1}/{len(cases)} {ref[:60]!r}: {len(pieces)} piece(s); free {free_gb():.1f} GB; "
          f"ETA {(total_chars - chars_done) / rate / 3600:.1f} h", flush=True)
(OUT / "DONE").write_text(time.strftime("%Y-%m-%d %H:%M"))
print("done", flush=True)
