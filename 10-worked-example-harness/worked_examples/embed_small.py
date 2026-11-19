"""Worked examples (COS env): nomic-v2 embeddings of short real texts — the C9 load-balancer "diagrams", a sample of
A10 box-drawn tables, the A9 chapter's stored code blocks — plus their questions (task query). Texts are embedded as
one piece each (task document), as V016/V006 load them. Memory guard as embed_pools.py.
    cd Code-Orchestrator-Service && HF_HUB_OFFLINE=1 .venv/bin/python <this>"""
import json, os, subprocess, sys, time
from pathlib import Path
os.environ.update({"TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "4"})
import numpy as np, torch
torch.set_num_threads(4)
sys.path.insert(0, os.getcwd())
from src.models.embedding.embedding_profiles import EmbeddingProfileRegistry
from src.models.embedding.profile_embedder import ProfileEmbedder
HERE = Path(__file__).parent
EN = "<CORPUS_ROOT>/collections/software-engineering/enriched"


def free_gb():
    pages = {l.split(":")[0]: int(l.split(":")[1].strip().rstrip(".")) for l in subprocess.run(["vm_stat"], capture_output=True, text=True).stdout.splitlines()[1:] if ":" in l}
    return sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative")) * 16384 / 1e9


while free_gb() < 2.0:
    print("waiting for memory", flush=True); time.sleep(60)
D = json.loads((HERE / "diagrams.json").read_text())
e = json.load(open(f"{EN}/Real-World Algorithms A Beginners Guide_enriched.json"))
a9 = [b for ch in e["chapters"] if ch["start_page"] == 375 for b in ch["code_blocks"]]
sets = {
    "C9": {"query": "Show me a load-balancer architecture diagram.", "texts": [r["content"] for r in D["C9"]]},
    "A10": {"query": "Show me what MySQL's SHOW TABLES output looks like.", "texts": [r["content"] for r in D["A10"][:200]]},
    "A9": {"query": "How do I tune a bloom filter's false-positive rate?", "texts": [b["content"] for b in a9]},
}
emb = ProfileEmbedder(profile=EmbeddingProfileRegistry.PROFILES["nomic-v2"], device="cpu")
assert emb.is_loaded, emb.unavailable_reason
out = {}
for k, s in sets.items():
    q = np.asarray(emb.embed_text(s["query"], task="query").embedding, dtype=np.float32)
    vs = np.asarray([emb.embed_text(t[:4000] or " ", task="document").embedding for t in s["texts"]], dtype=np.float32)
    q /= np.linalg.norm(q); vs /= np.linalg.norm(vs, axis=1, keepdims=True)
    out[k] = {"query": s["query"], "cos": [float(x) for x in vs @ q]}
    print(k, len(s["texts"]), flush=True)
(HERE / "small_cos.json").write_text(json.dumps(out, indent=1)); print("done")
