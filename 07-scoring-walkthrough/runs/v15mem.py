import os, sys, time, resource
os.environ.update({"TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "4"})
import torch; torch.set_num_threads(4)
from sentence_transformers import SentenceTransformer
V15 = os.path.expanduser("~/.cache/huggingface/hub/models--nomic-ai--nomic-embed-text-v1.5/snapshots/e5cf08aadaa33385f5990def41f7a23405aec398")
rss = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9
m = SentenceTransformer(V15, device="cpu", trust_remote_code=True, local_files_only=True)
print(f"loaded, peak {rss():.2f} GB", flush=True)
text = "Raft elects a leader, replicates a log, and commits entries once a majority acknowledges them. " * 600
for n in [int(x) for x in sys.argv[1:]]:
    piece = m.tokenizer.decode(m.tokenizer(text, add_special_tokens=False)["input_ids"][:n])
    t = time.time(); v = m.encode(["search_document: " + piece]); 
    print(f"{n} tokens → {v.shape[1]} dims in {time.time()-t:.1f}s; peak {rss():.2f} GB", flush=True)
