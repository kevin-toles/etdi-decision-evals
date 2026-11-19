"""A2 / A3 worked examples, step 2 (COS env): nomic-v2 pieces for the chapters in extra_pick.json plus two SE items for
A2 (the Gate Smashers Huffman lecture, the high-entropy-tokens paper — first chapter each), same method as
embed_pools.py; writes candidates_extra.json {id: meta} and pieces/<id>.npz.
    cd Code-Orchestrator-Service && HF_HUB_OFFLINE=1 .venv/bin/python <this>"""
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
C = "<CORPUS_ROOT>/collections"


def free_gb():
    pages = {l.split(":")[0]: int(l.split(":")[1].strip().rstrip(".")) for l in subprocess.run(["vm_stat"], capture_output=True, text=True).stdout.splitlines()[1:] if ":" in l}
    return sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative")) * 16384 / 1e9


pick = json.loads((HERE / "extra_pick.json").read_text())
items = [dict(r, q=q) for q, v in pick.items() for r in v]
for b in ("Gate Smashers_Design and Analysis of algorithms (DAA)_L-4.3 Huffman Coding Algorithm in Hindi with Example Greedy Techniques(Algorithm)",
          "Beyond the 8020 Rule High-Entropy Minority Tokens Drive Effective Reinforcement Learning for LLM Reasoning"):
    d = json.load(open(f"{C}/software-engineering/raw/{b}.json")); c = (d.get("chapters") or [{}])[0]
    items.append({"q": "A2", "lib": "software-engineering", "book": b, "chapter": (c.get("title") or "")[:90],
                  "pages": f"{c.get('start_page') or 1}-{c.get('end_page') or 1}"})
meta = {}
emb = None
for it in items:
    k = hashlib.sha1(f"{it['book']}|{it['chapter']}|{it['pages']}".encode()).hexdigest()[:12]
    meta[k] = it; out = HERE / "pieces" / f"{k}.npz"
    if out.exists(): continue
    d = json.load(open(f"{C}/{it['lib']}/raw/{it['book']}.json")); pages = {}
    for pg in d.get("pages") or []:
        try: pages[int(pg.get("page_number"))] = pg.get("text") or ""
        except Exception: pass
    s, e = (int(x) for x in it["pages"].split("-"))
    text = "\n".join(pages.get(i, "") for i in range(s, e + 1))
    while free_gb() < 1.2:
        print("memory guard", flush=True); time.sleep(60)
    if emb is None:
        emb = ProfileEmbedder(profile=EmbeddingProfileRegistry.PROFILES["nomic-v2"], device="cpu"); assert emb.is_loaded
    ps = emb.embed_pieces(text, task="document", batch_size=1)
    np.savez(out, vectors=np.asarray([p.embedding for p in ps], dtype=np.float32), tokens=np.array([p.token_count for p in ps]))
    print(k, it["book"][:50], len(ps), flush=True)
(HERE / "candidates_extra.json").write_text(json.dumps(meta, indent=1)); print("done")
