"""Golden set full run, second pass: a targeted pool for subdomains the first pass could not fill because automatic tag
matching collided with other meanings (lora/LoRa radio, alignment/CSS, chaos/chaos theory, contract/legal ...).
Each gap subdomain gets an explicit, reviewable list of Stack Exchange tags (GAP_TAGS below). Same thread filters as
build_pool.py (primary route, unclosed, key-source answer >= 400 chars, score >= 25 stackoverflow / >= 5 elsewhere).
Writes full/gap_pool.json (top 15 per subdomain by score) and appends the threads to full/threads.jsonl.
python3 -I <this>"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(HERE)
G = "<ETL_RAW_ROOT>/data/stackexchange"
D = "artificial-intelligence-machine-learning"
GAP_TAGS_MAIN = {
 (D, "llm-foundations"): {"large-language-model", "llm", "gpt-3", "gpt-4", "chatgpt", "language-model", "transformer"},
 (D, "llm-architecture"): {"transformer-model", "attention-mechanism", "self-attention", "transformer"},
 (D, "llm-inference"): {"llama", "llamacpp", "vllm", "inference", "kv-cache", "text-generation"},
 (D, "llm-prompting"): {"prompt-engineering", "prompt", "openai-api", "chatgpt-api", "in-context-learning"},
 (D, "llm-rag"): {"retrieval-augmented-generation", "rag", "langchain", "llama-index", "py-langchain"},
 (D, "llm-agents"): {"agents", "langchain-agents", "autogen", "function-calling", "tool-use", "ai-agents"},
 (D, "peft-lora"): {"peft", "fine-tuning", "finetuning", "lora-adapter", "qlora"},
 (D, "diffusion-models"): {"stable-diffusion", "diffusion-models", "ddpm", "latent-diffusion"},
 (D, "embedding-models"): {"word-embedding", "word2vec", "sentence-transformers", "embeddings", "sentence-embeddings", "glove", "doc2vec"},
 (D, "llm-alignment-safety"): {"rlhf", "ai-safety", "alignment", "value-alignment", "reinforcement-learning-from-human-feedback"},
 (D, "speech-audio"): {"speech-recognition", "speech-to-text", "text-to-speech", "whisper", "mfcc"},
 (D, "edge-local-inference"): {"tensorflow-lite", "onnx", "onnxruntime", "coreml", "edge-tpu", "quantization"},
 (D, "experiment-tracking"): {"mlflow", "wandb", "hyperparameter-tuning", "hyperparameter-optimization"},
 ("search-information-retrieval", "vector-search"): {"vector-database", "pgvector", "faiss", "pinecone", "qdrant", "milvus", "weaviate", "similarity-search", "cosine-similarity"},
 ("search-information-retrieval", "ann-algorithms"): {"nearest-neighbor", "approximate-nn-searching", "knn", "locality-sensitive-hash", "lsh", "hnsw", "kdtree"},
 ("search-information-retrieval", "inverted-indexes"): {"inverted-index", "full-text-search", "full-text-indexing", "tf-idf", "bm25"},
 ("search-information-retrieval", "hybrid-retrieval"): {"semantic-search", "hybrid-search", "reranking", "dense-retrieval"},
 ("search-information-retrieval", "query-expansion"): {"query-expansion", "synonyms", "stemming", "lemmatization", "spelling-correction"},
 ("apis-integration-messaging", "message-queues"): {"message-queue", "rabbitmq", "apache-kafka", "amqp", "zeromq", "activemq", "sqs", "nats"},
 ("apis-integration-messaging", "enterprise-integration-patterns"): {"enterprise-integration", "esb", "apache-camel", "integration-patterns", "saga"},
 ("apis-integration-messaging", "workflow-orchestration-bpm"): {"workflow", "temporal", "apache-airflow", "bpmn", "camunda", "orchestration"},
 ("testing-quality-assurance", "chaos-engineering"): {"chaos-engineering", "fault-injection", "chaos-monkey", "resilience"},
 ("testing-quality-assurance", "load-performance-testing"): {"load-testing", "performance-testing", "jmeter", "stress-testing", "gatling", "locust"},
 ("testing-quality-assurance", "contract-testing"): {"pact", "contract-testing", "consumer-driven-contracts"},
 ("testing-quality-assurance", "property-based-testing"): {"property-based-testing", "quickcheck", "hypothesis-test", "generative-testing"},
 ("devops-cloud-platform-engineering", "feature-flags"): {"feature-flags", "feature-toggle", "launchdarkly"},
 ("devops-cloud-platform-engineering", "service-mesh"): {"istio", "service-mesh", "envoyproxy", "linkerd", "sidecar"},
 ("data-engineering-databases", "stream-processing"): {"apache-flink", "stream-processing", "kafka-streams", "spark-streaming", "apache-beam", "event-stream-processing"},
 ("data-engineering-databases", "databases-time-series"): {"time-series-database", "influxdb", "timescaledb", "prometheus"},
 ("data-engineering-databases", "databases-key-value"): {"key-value-store", "redis", "rocksdb", "leveldb", "dynamodb", "memcached"},
 ("distributed-systems-engineering", "consistency-models"): {"eventual-consistency", "linearizability", "consistency", "causal-consistency", "crdt"},
 ("distributed-systems-engineering", "replication"): {"replication", "database-replication", "master-slave", "multi-master-replication", "quorum"},
}
GAP_TAGS_NUM = {("numerical-scientific-computing", "numerical-methods"): {"numerical-methods", "numerical-analysis", "numerical-integration", "ode", "differential-equations", "numerical-stability", "linear-solver", "finite-difference", "finite-element", "newtons-method", "runge-kutta", "floating-accuracy", "condition-number", "interpolation"}}
NUM = os.environ.get("GAP_SET") == "num"   # 2026-11-15: numerical-methods added after the first gap pass ("methods" tag collision)
GAP_TAGS = GAP_TAGS_NUM if NUM else GAP_TAGS_MAIN
pilot = {q["qid"] for q in json.load(open(f"{EV}/questions_pilot.json"))["questions"]}
taken = set()
for f in os.listdir(f"{HERE}/proposals"):
    p = json.load(open(f"{HERE}/proposals/{f}")); taken |= {q["qid"] for q in p.get("questions", [])}
by_tag = collections.defaultdict(set)
for k, ts in GAP_TAGS.items():
    for t in ts: by_tag[t].add(k)
pool = collections.defaultdict(list); keep = {}
files = [("stackoverflow.jsonl", 25)] + [(f"primary/{f}", 5) for f in (("scicomp.jsonl", "math.jsonl", "cs.jsonl", "stats.jsonl") if NUM else ("ai.jsonl", "genai.jsonl", "datascience.jsonl", "stats.jsonl", "softwareengineering.jsonl", "dba.jsonl", "devops.jsonl", "cs.jsonl", "serverfault.com.jsonl"))]
for f, min_score in files:
    if not os.path.exists(f"{G}/{f}"): print("missing", f); continue
    for line in open(f"{G}/{f}"):
        d = json.loads(line)
        if d.get("route") != "primary" or d.get("closed_date") or int(d.get("score", 0)) < min_score: continue
        hits = set().union(*[by_tag.get(t, set()) for t in d["tags"]]) if d["tags"] else set()
        if not hits: continue
        site = d["site"]; qid = f"{site if site == 'stackoverflow.com' else site.split('.')[0]}:{d['id']}"
        if qid in pilot or qid in taken: continue
        acc = str(d.get("accepted_answer_id") or "")
        if not [a for a in d["answers"] if (str(a["id"]) == acc or int(a["score"]) >= 10) and len(a["body"]) >= 400]: continue
        row = {"qid": qid, "file": f, "id": d["id"], "site": site.split(".")[0], "title": d["title"], "score": int(d["score"]), "tags": d["tags"]}
        for dom, sub in hits:
            pool[f"{dom}/{sub}"].append(row)
        d["qid"] = qid; d.pop("body_html", None); keep[qid] = d
    print(f, len(keep), flush=True)
out = {k: sorted(v, key=lambda r: -r["score"])[:15] for k, v in pool.items()}
used = {r["qid"] for v in out.values() for r in v}
have = {json.loads(l)["qid"] for l in open(f"{HERE}/threads.jsonl")}
with open(f"{HERE}/threads.jsonl", "a") as fh:
    for q in used - have: fh.write(json.dumps(keep[q], ensure_ascii=False) + "\n")
json.dump({"built": "2026-11-15", "rule": __doc__.strip(), "gap_tags": {f"{a}/{b}": sorted(t) for (a, b), t in GAP_TAGS.items()}, "pool": out},
          open(f"{HERE}/gap_pool" + ("_num" if NUM else "") + ".json", "w"), indent=1, ensure_ascii=False)
for k in sorted(GAP_TAGS): print(f"{k[0]}/{k[1]}", len(out.get(f"{k[0]}/{k[1]}", [])))
