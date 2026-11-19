"""Embed docs_v2 + queries with one model, then score. One model per process (memory).
Metrics (gold queries, title stripped):
  LC pool   : rank of the gold LeetCode problem among the 2,780 LeetCode statements -> top1, top5, MRR
  full pool : same among LeetCode + TACO + CodeContests (42,833 docs)
Tag agreement (all FastPrep coding queries): Jaccard between FastPrep topics and LeetCode tags of the top-1
LeetCode neighbour (normalised lowercase_underscore).
Usage: HF_HUB_OFFLINE=1 python3 -I embed_eval.py <xref_dir> <model_key>
"""
import json, os, sys, time, ast
import numpy as np

X, KEY = sys.argv[1], sys.argv[2]
CFG = {
  "minilm-l6":      dict(name="sentence-transformers/all-MiniLM-L6-v2"),
  "nomic-v1.5":     dict(name="nomic-ai/nomic-embed-text-v1.5", trust=True, qpre="search_query: ", dpre="search_document: "),
  "nomic-v2-moe":   dict(name="nomic-ai/nomic-embed-text-v2-moe", trust=True, qkw=dict(prompt_name="query"), dkw=dict(prompt_name="passage"),
                         device="cpu"),  # MoE fallback (no megablocks on Mac) leaks MPS memory per batch: 7 GB after 2 batches, 33 GB in the full run; CPU stays flat at 2.4 GB
  "bge-large-v1.5": dict(name="BAAI/bge-large-en-v1.5", qpre="Represent this sentence for searching relevant passages: "),
  "bge-m3":         dict(name="BAAI/bge-m3"),
  "e5-large-ml":    dict(name="intfloat/multilingual-e5-large", qpre="query: ", dpre="passage: "),
  "jina-v3":        dict(name="jinaai/jina-embeddings-v3", trust=True, qkw=dict(task="retrieval.query", prompt_name="retrieval.query"),
                         dkw=dict(task="retrieval.passage", prompt_name="retrieval.passage"),
                         empty_cache=True),  # MPS memory grows per batch (4.0 -> 8.5 GB in 2 batches; 15 GB in the full run); clearing the cache each batch holds 5.2 GB
  "jina-v5-small":  dict(name="jinaai/jina-embeddings-v5-text-small", trust=True, qkw=dict(task="retrieval", prompt_name="query"),
                         dkw=dict(task="retrieval", prompt_name="document")),
}
c = CFG[KEY]
load = lambda n: [json.loads(l) for l in open(f"{X}/{n}.jsonl")]
docs, qg, qa = load("docs_v2"), load("queries_gold"), load("queries_all")
E = f"{X}/emb/{KEY}"; os.makedirs(E, exist_ok=True)

from sentence_transformers import SentenceTransformer
import torch
dev = c.get("device") or ("mps" if torch.backends.mps.is_available() else "cpu")
m = SentenceTransformer(c["name"], device=dev, trust_remote_code=c.get("trust", False))
m.max_seq_length = min(512, m.max_seq_length or 512)

def enc(texts, pre, kw, path):
    if os.path.exists(path): return np.load(path).astype(np.float32)
    t0 = time.time()
    if c.get("empty_cache") and dev == "mps":   # encode one batch at a time and release the MPS cache after each
        parts = []
        for b in range(0, len(texts), 32):
            parts.append(m.encode([pre + t for t in texts[b:b + 32]], batch_size=32, normalize_embeddings=True,
                                  show_progress_bar=False, convert_to_numpy=True, **kw))
            torch.mps.empty_cache()
        v = np.concatenate(parts)
    else:
        v = m.encode([pre + t for t in texts], batch_size=32, normalize_embeddings=True, show_progress_bar=False,
                     convert_to_numpy=True, **kw)
    np.save(path, v.astype(np.float16)); print(f"{KEY} {os.path.basename(path)} {len(texts)} in {time.time()-t0:.0f}s", flush=True)
    return v.astype(np.float32)

Dv = enc([d["text"] for d in docs], c.get("dpre", ""), c.get("dkw", {}), f"{E}/docs.npy")
Qa = enc([q["text"] for q in qa], c.get("qpre", ""), c.get("qkw", {}), f"{E}/queries_all.npy")
idx = {q["query_id"]: i for i, q in enumerate(qa)}
Qg = Qa[[idx[q["query_id"]] for q in qg]]
ids = [d["doc_id"] for d in docs]; pos = {d: i for i, d in enumerate(ids)}
lc_mask = np.array([d["source"] == "leetcode" for d in docs])

def ranks(S, gold_cols):
    g = S[np.arange(len(gold_cols)), gold_cols]
    return (S > g[:, None]).sum(1) + 1
gold = np.array([pos[q["gold"]] for q in qg])
S_full = Qg @ Dv.T
r_full = ranks(S_full, gold)
lc_cols = np.where(lc_mask)[0]; lc_pos = {c_: i for i, c_ in enumerate(lc_cols)}
r_lc = ranks(S_full[:, lc_cols], np.array([lc_pos[g_] for g_ in gold]))
m_ = lambda r: dict(top1=float((r == 1).mean()), top5=float((r <= 5).mean()), mrr=float((1 / r).mean()))

nt = lambda s: s.strip().lower().replace(" ", "_").replace("-", "_")
def tagset(t):
    if isinstance(t, str):
        try: t = ast.literal_eval(t)
        except Exception: t = [t]
    return {nt(x) for x in (t or [])}
lcd = [docs[i] for i in lc_cols]
top1 = (Qa @ Dv[lc_cols].T).argmax(1)
jac = []
for q, j in zip(qa, top1):
    a, b = {nt(x) for x in q["topics"]}, tagset(lcd[j]["tags"])
    if a and b: jac.append(len(a & b) / len(a | b))
res = {"model": KEY, "n_gold": len(qg), "n_all": len(qa), "lc_pool": m_(r_lc), "full_pool": m_(r_full),
       "tag_jaccard_top1": float(np.mean(jac)), "n_tag": len(jac), "dim": int(Dv.shape[1]), "device": dev}
json.dump(res, open(f"{E}/scores.json", "w"), indent=1); print(json.dumps(res), flush=True)
