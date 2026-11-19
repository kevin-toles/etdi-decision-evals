import os, sys, time, resource
os.environ["EMBEDDING_PROFILE"] = "jina-v3"; os.environ.setdefault("OMP_NUM_THREADS", "4")
import torch; torch.set_num_threads(4)
sys.path.insert(0, "<COS_REPO>")
from src.models.embedding.profile_embedder import ProfileEmbedder
rss = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9   # macOS: bytes
t = time.time(); e = ProfileEmbedder(); ok = e.is_loaded
print(f"loaded={ok} reason={e.unavailable_reason!r} peak RSS {rss():.2f} GB in {time.time()-t:.0f}s", flush=True)
for n in [int(x) for x in sys.argv[1:]]:
    text = ("Raft elects a leader, replicates a log, and commits entries once a majority acknowledges them. " * 400)
    ids = e._model.tokenizer(text, add_special_tokens=False)["input_ids"][:n]
    piece = e._model.tokenizer.decode(ids)
    t = time.time(); r = e.embed_text(piece, task="document")
    print(f"{n} tokens → dim {r.dim} model {r.model}; {time.time()-t:.1f}s; peak RSS {rss():.2f} GB", flush=True)
