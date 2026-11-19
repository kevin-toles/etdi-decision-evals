import collections
from pathlib import Path
from src.features.ClassifyCorpus.taxonomy.parse_appendix import parse_appendix
from src.features.ClassifyCorpus.taxonomy.default_domain_slug import default_domain_slug
pa=parse_appendix(Path("<EVIDENCE>/htc_appendix_a2_v1.0.md"))
D={d.domain_id:d for d in pa.domains}; home={s:d.domain_id for d in pa.domains for s in d.subdomain_slugs}
def ref(s): assert s in home,s; return f"`{s}` [{home[s]:02d}]"

# (removed_slug, target_slug, reason)
CONSOLIDATE=[
("risc-vs-cisc","instruction-set-architectures","A comparison of ISA design philosophies, not a separate body of knowledge; every RISC-vs-CISC chapter is an ISA chapter."),
("distributed-storage","distributed-storage-systems","Same subject in two domains (Ceph, HDFS, GFS, Dynamo-style stores). One home in Storage Systems; the replication/consistency theory stays in 08."),
("distributed-locking","distributed-coordination","Locks/leases/fencing tokens are coordination primitives (ZooKeeper, etcd, Chubby cover both in the same chapters)."),
("bluetooth-zigbee-lorawan","sensor-networks-iot-protocols","Low-power wireless protocols are the IoT protocol subject; both anchors would describe Zigbee/LoRaWAN/BLE."),
("ports-and-adapters","clean-hexagonal-onion-architecture","Ports-and-adapters is the original name of hexagonal architecture — the same pattern under two slugs."),
("software-archaeology","program-comprehension","Recovering intent from unfamiliar/legacy code is program comprehension; the term has no separate literature in the corpus vocabulary."),
("snapshot-testing","golden-testing","Snapshot tests and golden-master tests are the same technique (record expected output, diff on change)."),
("query-planners","query-optimization","The query planner is the query optimizer; cost models, join ordering and plan selection appear in the same chapters."),
("incident-command","incident-management","Incident command (IC roles, comms lead) is the coordination part of operational incident management; one anchor in 17. Security incident handling stays `incident-response` [20]."),
("nlp-architecture","nlp-algorithms","No usable boundary between NLP 'architecture' and NLP 'algorithms' (seq2seq, CRFs, attention models appear under both); transformer/LLM architecture is already `llm-architecture`."),
("bm25","ranking-relevance","BM25 is one ranking function; every BM25 chapter is a ranking-relevance chapter."),
("binary-exploitation","exploit-development","Binary exploitation (ROP, heap exploitation) is the main body of exploit development; one anchor. `memory-security` stays for defences (ASLR, CFI, memory-safe languages)."),
("engineering-effectiveness","developer-productivity","Same subject (SPACE, DX surveys, flow); `engineering-metrics` stays for DORA-style measurement."),
("data-interchange-formats","protocol-buffers-serialization","Serialization formats (JSON, XML, Avro, Protobuf, MessagePack) are one subject split across 10 and 16; one home in 10, renamed `serialization-formats`. Columnar file formats (Parquet/ORC) stay with `databases-columnar`/`data-lakes`."),
]
# (slug, [new slugs in place], {moved-content: target}, reason)
SPLIT=[
("kernel-development-windows-bsd",["kernel-development-windows","kernel-development-bsd"],{},"Windows NT and the BSD kernels share no code, APIs or literature; one anchor would sit between two unrelated clusters and match neither well."),
("compiler-gpu-simd-optimization",["simd-vectorization","gpu-compute-optimization"],{},"Three subjects in one slug. SIMD/auto-vectorization tuning and GPU kernel tuning (CUDA/OpenCL occupancy, memory coalescing) are separate literatures; compiler-pass internals already live in `optimization-passes` [05]."),
("concurrency-parallel-computing",["concurrency-synchronization"],{"parallel computing (MPI, OpenMP, data parallelism) — to the existing slug, nothing new is created":"high-performance-computing"},"The slug spans OS-level concurrency (threads, mutexes, condition variables) and parallel computing; the second is `high-performance-computing` [25]. The 07 slug keeps the OS part."),
("elasticsearch-elk",[],{"Elasticsearch as a search engine":"lucene-elasticsearch-solr","the ELK logging stack":"observability-logging"},"Two different uses of one product: search indexing (already `lucene-elasticsearch-solr` [19]) and log aggregation (`observability-logging` [17]). The 16 slug is dissolved."),
("bootloaders-firmware",["bootloaders-boot-process"],{"embedded firmware":"firmware"},"Bootloaders/boot process (UEFI, GRUB, secure boot) belong to the OS domain; embedded firmware is already `firmware` [24]."),
("replication-sharding",["sharding-partitioning"],{"replication protocols":"replication"},"Replication is covered by `replication` [08]; the database-specific part that is not covered elsewhere is sharding/partitioning."),
("debuggers-profilers",["debuggers"],{"profilers and profiling":"profiling"},"Profiling is `profiling` [12] (method and tools); the 26 slug keeps debugger tooling."),
]
# (slug, new_slug or None, new domain id or None, reason)
RENAME=[
("caches","cpu-caches",None,"`caches` collides with `caching` [16] and `cache-optimization` [12]; the 06 subject is hardware cache design (associativity, coherence, replacement)."),
("pipelines","cpu-pipelines",None,"`pipelines` collides with `data-pipelines`, `ml-pipelines`, `rendering-pipelines`, `observability-telemetry-pipelines`; the 06 subject is instruction pipelining."),
("databases-kv-cache","databases-key-value",None,"\"KV cache\" also means the LLM attention cache (`llm-inference` [18]); the 16 subject is key-value stores (Redis, RocksDB, DynamoDB)."),
("distributed-tracing","observability-tracing",17,"Tracing is the third observability signal next to `observability-logging`/`observability-metrics` [17]; in 08 it competes with them for every OpenTelemetry chapter."),
("protocol-buffers-serialization","serialization-formats",None,"Absorbs `data-interchange-formats` [16] (see consolidations); the name should cover JSON/Avro/MessagePack as well as Protobuf."),
("design-patterns","design-pattern-foundations",None,"The parent overlaps its own three GoF children. Renamed and scoped to pattern languages, pattern principles and anti-patterns; the behavioral/creational/structural children stay. (Alternative: merge all four into one `design-patterns` — that removes three more slugs, cancels the design-patterns scope row, and changes the total by −3.)"),
]
# (a, b, boundary)
SCOPE=[
("real-time-kernels","rtos","Real-time behaviour in general-purpose and OS kernels (PREEMPT_RT, Xenomai, real-time scheduling classes, latency analysis) vs RTOS products for microcontrollers (FreeRTOS, Zephyr, ThreadX — tasks, queues, porting)."),
("cap-theorem","consistency-models","Trade-off reasoning under partitions (CAP, PACELC, availability vs consistency choices) vs definitions and implementations of consistency models (linearizability, causal, eventual, session guarantees)."),
("rpg","as400-rpg-ecosystem","The RPG language (RPG IV/ILE syntax, free-form RPG) vs the IBM i platform around it (OS/400, DB2 for i, CL, job management) — the same language/platform split as cobol vs mainframe-zos."),
("conways-law","sociotechnical-systems","Conway's law and the inverse Conway manoeuvre (team structure mirrors architecture) vs sociotechnical theory in general (team topologies, cognitive load, socio-technical congruence)."),
("swift","ios-swift","Language (syntax, generics, concurrency model) vs iOS app development (UIKit/SwiftUI, app lifecycle)."),
("kotlin","android-kotlin","Language (coroutines, multiplatform) vs Android app development (Jetpack, activities)."),
("c","embedded-c","General C vs embedded C (MISRA, bare-metal, volatile/registers)."),
("graph-theory","graph-algorithms","Classify by the chapter's primary subject, not by whether it contains proofs: a chapter whose subject is a graph property (colouring, planarity, matchings) is theory even with an algorithm in it; a chapter whose subject is computing something (shortest paths, max-flow) is algorithms even with a correctness proof."),
("streaming-algorithms","stream-processing","Sublinear-space algorithms (sketches) vs stream-processing systems (Flink, Kafka Streams)."),
("static-analysis-tooling","static-dynamic-analysis","Building analyzers (abstract interpretation, dataflow frameworks) vs applying analysis in QA."),
("static-analysis-tooling","linters-formatters","Analyzer construction vs developer-facing lint/format tools."),
("optimization-passes","simd-vectorization","Compiler-internal passes vs performance-engineering tuning of code (split above)."),
("garbage-collector-implementation","memory-management","A language runtime reclaiming objects (tracing, generational, concurrent marking — e.g. a JVM/Go GC chapter) vs the OS managing pages and address spaces (paging, mmap, swapping). A chapter on how a GC requests memory from the OS is GC."),
("memory-allocators","memory-management","Allocator implementation (jemalloc, slab) vs virtual memory, paging, address spaces."),
("memory-hierarchy","cpu-caches","Whole hierarchy (registers to storage, TLBs, DRAM) vs cache design."),
("memory-optimization","memory-management","Reducing a program's footprint vs how the OS manages memory."),
("memory-security","exploit-development","Defences vs attacks."),
("cpu-caches","cache-optimization","Hardware design vs writing cache-friendly code."),
("cache-optimization","caching","Code-level locality vs application/data caching strategies (cache-aside, invalidation)."),
("caching","databases-key-value","Classify by what the chapter explains, not the product it names. Redis as a cache in front of a database (cache-aside, TTLs, invalidation, stampedes) → caching; Redis/RocksDB/DynamoDB as the system of record (data model, persistence, replication of the store) → databases-key-value."),
("consensus-algorithms","leader-election","Consensus protocols (Paxos, Raft) vs election as a standalone primitive (bully, ring, lease-based)."),
("consensus-algorithms","blockchain-consensus-mechanisms","Crash/Byzantine fault-tolerant consensus vs PoW/PoS/BFT in ledgers."),
("event-sourcing","event-driven-architecture","The event log as the system of record (rebuilding state by replay, snapshots, event schema evolution) vs events as the communication model between components (pub/sub topology, choreography). An event-sourced service that also publishes events is classified by which of the two the chapter is about."),
("distributed-transactions","transaction-processing-oltp-olap","Cross-node commit (2PC, sagas) vs single-database transaction processing."),
("hypervisors-virtualization","network-virtualization","Machine virtualization vs network virtualization (VXLAN, overlays)."),
("routing","bgp","Routing in general (OSPF, IS-IS, algorithms) vs BGP specifically."),
("tcp-ip","ipv4-ipv6","The TCP/IP stack vs IP addressing and the IPv6 transition."),
("network-monitoring","observability-metrics","Network device/flow monitoring (SNMP, NetFlow) vs application metrics."),
("grpc","serialization-formats","RPC framework vs wire formats."),
("openapi-asyncapi","api-standards","Description specs vs API standards in general (RFC 7807, JSON:API, OAuth/OIDC specs)."),
("message-queues","stream-processing","Brokers and delivery semantics vs stream computation."),
("workflow-orchestration-bpm","data-pipelines","Classify by what the chapter explains, not the engine it uses. Durable business/process workflows (sagas, human approval steps, Temporal/Camunda) → workflow orchestration; moving and transforming data (ETL/ELT DAGs, dbt models, backfills) → data-pipelines, even when Airflow or Temporal runs them."),
("api-gateways","service-mesh","North-south edge gateway vs east-west service-to-service mesh."),
("profiling","benchmarking","Finding where time goes vs measuring and comparing performance."),
("benchmarking","load-performance-testing","Micro/macro benchmarks vs load and stress testing of a deployed system."),
("concurrency-synchronization","lock-free-programming","Locks and OS synchronization vs lock-free/wait-free structures."),
("concurrency-tuning","concurrency-testing","Tuning contention vs finding races (TSan, model checkers)."),
("microservices-architecture","soa","Microservices vs enterprise SOA (ESB era)."),
("microservices-architecture","modular-monoliths","Distributed services vs modular single deployable."),
("architecture-governance","architectural-drift-analysis","Governance process vs detecting implementation drift from intended architecture."),
("design-pattern-foundations","enterprise-integration-patterns","Pattern principles vs integration (EIP) patterns."),
("debugging","debuggers","Debugging method vs debugger tools."),
("refactoring","technical-debt-economics","Code transformations vs debt measurement and economics."),
("software-maintenance-evolution","legacy-modernization-migration","Evolution laws and maintenance vs migrating legacy platforms."),
("software-metrics","engineering-metrics","Code/design metrics (complexity, coupling) vs delivery metrics (DORA)."),
("software-reliability-engineering","sre-reliability","Reliability theory and modelling (MTBF, fault trees, reliability growth) vs operational SRE (SLOs, error budgets, toil)."),
("software-quality","qa-process","Quality models (ISO 25010) vs the QA process."),
("contract-testing","api-testing","Consumer-driven contracts (Pact) vs functional API testing."),
("golden-testing","regression-testing","Output-diff technique vs regression strategy and suites."),
("accessibility-testing","accessibility","Testing tools and audits vs accessible design (WCAG design practice)."),
("security-testing","penetration-testing","SAST/DAST in CI vs offensive assessment."),
("fuzzing","vulnerability-research","Fuzzing technique vs the research discipline."),
("chaos-engineering","sre-reliability","Fault-injection experiments vs reliability operations."),
("batch-processing","jcl-batch-processing","Spark/Hadoop/Beam batch vs mainframe JCL."),
("indexing","inverted-indexes","Database indexes (B-trees, LSM) vs IR inverted indexes."),
("databases-graph","knowledge-graphs","Graph databases vs knowledge-graph modelling and reasoning."),
("knowledge-graphs","ast-knowledge-graphs","General KGs vs code-structure graphs."),
("databases-spatial","spatial-data-structures","Spatial databases (PostGIS) vs spatial structures (R-trees, k-d trees)."),
("storage-engines","distributed-storage-systems","Single-node engines (LSM, B-tree engines) vs distributed stores."),
("data-quality-governance","privacy-compliance","Data quality and lineage vs privacy regulation."),
("ci-cd","release-engineering","Pipelines vs release management, versioning, rollout strategy."),
("release-engineering","app-store-release","General release vs mobile store submission."),
("platform-engineering","platform-strategy","Building internal platforms vs platform strategy as an org decision."),
("platform-engineering","ml-platform","General IDP vs ML platforms."),
("incident-management","incident-response","Operational incidents (on-call, IC) vs security incidents (DFIR)."),
("incident-management","postmortems","Handling the incident vs blameless review afterwards."),
("generative-models","diffusion-models","GANs, VAEs, flows vs diffusion specifically."),
("diffusion-models","image-generation","Method vs application."),
("computer-vision","image-classification","Detection, segmentation, 3D vision vs classification."),
("llm-inference","edge-local-inference","Serving-side inference optimization vs on-device inference."),
("llm-training","peft-lora","Pre-training vs parameter-efficient fine-tuning."),
("rlhf-dpo","reinforcement-learning-theory","Preference optimization for LLMs vs RL theory."),
("llm-rag","hybrid-retrieval","LLM generation over retrieved context vs the retrieval method."),
("llm-rag","graph-grounded-retrieval","General RAG vs graph-grounded retrieval."),
("nlp-algorithms","llm-foundations","Classical/pre-LLM NLP vs LLM foundations."),
("text-generation","llm-foundations","Generation methods (decoding, seq2seq) vs LLMs as a whole."),
("llm-alignment-safety","ai-ml-security","Alignment and behavioural safety vs attacks on ML systems (prompt injection, poisoning)."),
("llm-alignment-safety","ethics-in-tech","Technical alignment vs ethics and policy."),
("ranking-relevance","ir-theory","Ranking functions and learning-to-rank vs IR models and evaluation theory."),
("search-engines","lucene-elasticsearch-solr","Search-engine architecture vs the Lucene product family."),
("reverse-engineering","malware-analysis","RE technique vs analysing malicious code."),
("cryptography-foundations","cryptography-applied","Primitives and proofs vs protocols and use (TLS, key management)."),
("cryptography-foundations","number-theory","Cryptographic constructions vs the mathematics."),
("cryptography-foundations","zero-knowledge-proofs","General crypto vs ZK systems in ledgers."),
("identity-authentication","zero-trust","AuthN/AuthZ mechanisms vs the zero-trust architecture model."),
("privacy-compliance","compliance-standards","Privacy law (GDPR, CCPA) vs security/compliance frameworks (SOC 2, ISO 27001, PCI)."),
("hardware-security","side-channel-attacks","Hardware security in general vs side channels."),
("hardware-security","trusted-execution-environments","General vs TEEs (SGX, TrustZone)."),
("supply-chain-security","package-managers","Supply-chain threats (SBOM, signing) vs package manager design."),
("http-protocols","rest","HTTP/1.1, 2, 3 protocol vs REST API design."),
("web-standards","html-css","Standards process and specs (W3C, WHATWG) vs authoring HTML/CSS."),
("mobile-responsive-design","interaction-design","Responsive layout implementation vs interaction design."),
("design-systems","frontend-frameworks","Design systems (tokens, component libraries) vs frameworks."),
("graphics-programming","shaders-gpu-programming","Graphics programming in general vs shader/GPU programming."),
("shaders-gpu-programming","rendering-pipelines","Writing shaders vs pipeline architecture (deferred/forward, ray tracing)."),
("shaders-gpu-programming","gpu-compute-optimization","Graphics shaders vs GPGPU kernel tuning."),
("game-ai","reinforcement-learning-applications","Game AI (behaviour trees, pathfinding) vs RL applications."),
("microcontrollers","embedded-c","Hardware (MCU families, peripherals) vs embedded C programming."),
("hardware-software-codesign","fpga-development","Codesign methodology vs FPGA development."),
("high-performance-computing","numerical-methods","HPC systems and parallel programming vs numerical algorithms."),
("scientific-computing-tools","matlab-octave","Scientific tool ecosystems vs the MATLAB/Octave language."),
("computational-science","simulation-modeling","The discipline (computational X) vs simulation and modelling technique."),
("devex","developer-productivity","Developer-experience tooling and ergonomics vs org-level productivity measurement."),
("codebase-topology","program-comprehension","Mapping codebase structure vs human comprehension."),
("ast-knowledge-graphs","semantic-code-search","Code graphs vs search over code."),
("smart-contracts","solidity","Contract design vs the Solidity language (likewise vyper, move-language, cairo, clarity)."),
("blockchain-security","smart-contracts","Ledger/contract attacks vs contract development."),
("cobol","mainframe-zos","The language vs the z/OS platform."),
("technical-writing-docs-as-code","technical-communication","Documentation craft plus tooling (docs pipelines, API reference, style guides, docs in the repo) vs explaining technical problems plus decisions to any audience — emails, proposals, design reviews, stakeholder updates, technical communication as a discipline, plus how framing a problem shapes the decision (rev 3)."),
("estimation-sprint-planning","roadmap-planning","Team-level estimation vs product/technical roadmaps."),
("technical-leadership","engineering-management","IC technical leadership vs people management."),
("technical-strategy","decision-making","Strategy vs decision methods."),
("organizational-design","sociotechnical-systems","Org structures vs sociotechnical theory."),
("licensing-oss-governance","compliance-standards","OSS licences vs regulatory/security compliance."),
("classic-basic","visual-basic-dotnet","1970s–90s BASIC vs VB.NET."),
("classic-pascal","delphi-object-pascal","Wirth Pascal vs Delphi/Object Pascal."),
("scheme","racket","Scheme vs the Racket platform."),
("discrete-mathematics","graph-theory","Introductory discrete maths and combinatorics vs graph theory proper (likewise set-theory, number-theory, formal-logic); set-theory includes fuzzy plus rough set theory (rev 3)."),
("information-theory","coding-theory","Entropy, channel capacity vs error-correcting codes."),
("formal-verification","model-checking","Policy: a chapter centred on one technique goes to that technique (model-checking, theorem-proving, symbolic-execution); formal-verification takes surveys, method comparisons and verification of whole systems across techniques."),
("instruction-set-architectures","risc-v","ISAs in general vs a specific ISA (likewise arm, x86, power)."),
("accelerator-hardware","tensor-processors","Accelerators in general vs TPUs/NPUs."),
]
GROUPS=[
("G1","Application security cluster",["application-security","web-security","secure-coding","secure-sdlc"],
 "application-security = the umbrella for securing an application (authn/z in the app, input handling, dependency risk, app-level threat controls) — chapters spanning several of the others go here; web-security = attacks and defences specific to browsers and HTTP (XSS, CSRF, CSP, CORS, cookie security); secure-coding = language-level rules for writing code (CERT/MISRA secure rules, unsafe APIs, integer and string handling); secure-sdlc = the organisational process (security requirements, reviews, gates, SAMM/BSIMM). Classify by the chapter's primary subject."),
("G2","Agents and orchestration cluster",["llm-agents","agentic-workflows","multi-agent-orchestration","workflow-orchestration-bpm","autonomous-development-cycles"],
 "llm-agents = a single agent's loop (tool use, planning, memory, ReAct); agentic-workflows = deterministic workflows with agent steps (fixed graphs, retries, human approval around LLM calls); multi-agent-orchestration = coordinating several agents (roles, delegation, communication protocols); workflow-orchestration-bpm = durable workflow engines with no LLM subject (Temporal, Camunda, BPMN); autonomous-development-cycles = agents running the software lifecycle (plan → code → test → PR)."),
("G3","ML operations cluster",["mlops","ml-pipelines","ml-platform","ml-serving","experiment-tracking","llm-inference"],
 "mlops = practices and lifecycle (CI/CD for models, monitoring, drift, governance); ml-pipelines = building training/feature pipelines (TFX, Kubeflow Pipelines, feature stores in pipelines); ml-platform = the internal platform that hosts them; ml-serving = deploying general models behind an endpoint (batching, autoscaling, model servers); experiment-tracking = tracking runs, metrics and artifacts (MLflow, W&B); llm-inference = LLM-specific inference optimisation (KV cache, continuous batching, speculative decoding)."),
("G4","Vector retrieval cluster",["databases-vector","vector-search","ann-algorithms"],
 "databases-vector = the database product (storage, filtering, sharding, operations — Qdrant, Milvus, pgvector); vector-search = the retrieval operation in a system (query embedding, top-k, filtering strategy, reranking); ann-algorithms = the index algorithms themselves (HNSW, IVF, PQ, recall/latency trade-offs). The three are levels, not exclusive categories: classify by the level the chapter is about."),
]
NEW=set()
for s,new,moved,_ in SPLIT: NEW.update(new)
for s,n,_,_ in RENAME: NEW.add(n)
def chk(s): assert s in home or s in NEW, s
removed={c[0] for c in CONSOLIDATE}|{s[0] for s in SPLIT}|{r[0] for r in RENAME}
for a,b,_ in SCOPE: chk(a); chk(b)
for g in GROUPS:
    for m in g[2]: chk(m)
for r,t,_ in CONSOLIDATE: assert r in home and t in home, (r,t)
assert len(removed)==len(CONSOLIDATE)+len(SPLIT)+len(RENAME), "slug in two action lists"
# final map
final=collections.OrderedDict((d,[s for s in D[d].subdomain_slugs]) for d in D)
for r,t,_ in CONSOLIDATE: final[home[r]].remove(r)
for s,new,moved,_ in SPLIT:
    i=final[home[s]].index(s); final[home[s]][i:i+1]=new
for s,n,nd,_ in RENAME:
    d=home[s]; i=final[d].index(s)
    if nd: final[d].pop(i); final[nd].append(n)
    else: final[d][i]=n
touched={m for g in GROUPS for m in g[2]}|{c[0] for c in CONSOLIDATE}|{c[1] for c in CONSOLIDATE}|{s[0] for s in SPLIT}|{r[0] for r in RENAME}|{x for a,b,_ in SCOPE for x in (a,b)}
for s,new,moved,_ in SPLIT: touched|=set(moved.values())
untouched={d:[s for s in D[d].subdomain_slugs if s not in touched] for d in D}
total=sum(len(v) for v in final.values())
L=[]
w=L.append
w("# HTC Subdomain Canonicalization — Candidate List for Review (rev 3)\n")
w("**For:** Kevin Toles · **Date:** 2026-10-19 · **Source:** HTC-MULTIDIM-2.0 Appendix A (34 domains, 474 subdomains); domain slugs per OQ#12 = builder defaults · **Rev 2:** revised after review by three external models (§9) · **Status: ACCEPTED 2026-10-19** — applied to HTC-MULTIDIM-2.0 Appendix A v1.2; boundaries generated into `htc-multidim-classification-service/config/subdomain_boundaries.json`\n")
w("**Why this exists:** HTC routes each chapter, passage and paragraph group by cosine similarity to one anchor text per subdomain, and every classification, Qdrant payload and Neo4j edge carries the slug — so the list must be settled before anchors are written and before the fresh seed. Related subjects can keep separate slugs if their anchors draw a clear boundary; the question for each slug is whether it is a useful destination of its own. Where two slugs name the same subject, the anchors cannot be separated and chapters split between them unpredictably; those are the consolidations.\n")
w("**How overlap is already handled:** HTC is not single-label. Every unit gets one primary (domain, subdomain, KF) plus secondary tags for every domain scoring ≥ 0.6 × the primary, and an ambiguity index (HTC-MULTIDIM-2.0 A.4; ETDI BEH-07.04). A chapter on tracing a multi-agent workflow gets one primary and secondaries for the others. So only same-subject duplicates are consolidated; related subjects stay, with a stated boundary.\n")
w("**Method:** every subdomain name was compared to every other (word overlap flagged 79 pairs) and each of the 474 was then read against its own domain and the related domains. Appendix A has names only, no descriptions, so each ruling is a proposal based on the name and on how the topic appears in the literature. The tables and counts below are generated by one script from the change list, which asserts every one of the 474 slugs is accounted for exactly once. Nothing has been changed in any design, manifest or code.\n")
w("## Summary\n")
w("| Action | What it means | Count |\n|---|---|---|")
w(f"| **Consolidate** | The slug is removed; its subject is covered by an existing slug | {len(CONSOLIDATE)} |")
w(f"| **Split** | One slug is replaced by narrower slugs, or its content is divided between existing homes | {len(SPLIT)} |")
w(f"| **Rename / move** | Same subject, clearer or non-colliding slug (one also moves domain) | {len(RENAME)} |")
w(f"| **Group boundary** | Three or more overlapping slugs all stay; one boundary statement covers the whole group | {len(GROUPS)} groups ({sum(len(g[2]) for g in GROUPS)} slugs) |")
w(f"| **Scope** | Both slugs of a pair stay; the anchor texts state the boundary given here | {len(SCOPE)} pairs |")
w(f"| **Untouched** | No overlap found | {sum(len(v) for v in untouched.values())} slugs |")
w(f"\nResult if every proposal is accepted: **{total} subdomains** (was 474). Domain count stays 34; two slugs change domain (R4 and the S-row content moves, §8).\n")
w("Your ruling per row: **Accept**, **Reject** (keep as is), or **Change** (say how). Rows decided on review-sensitive grounds are marked ⚖ — rule on those explicitly.\n")
JUDG={"bm25","snapshot-testing","query-planners","design-patterns"}
w("## 1. Consolidate\n")
w("| ID | Removed | Absorbed into | Why |\n|---|---|---|---|")
for i,(r,t,why) in enumerate(CONSOLIDATE,1): w(f"| C{i}{' ⚖' if r in JUDG else ''} | {ref(r)} | {ref(t)} | {why} |")
w("\n## 2. Split\n")
w("| ID | Current | Becomes (slugs in the same domain) | Content moved to an existing slug | Why |\n|---|---|---|---|---|")
for i,(sl,new,moved,why) in enumerate(SPLIT,1):
    nw=", ".join(f"`{n}` [{home[sl]:02d}]" for n in new) or "— (slug dissolved)"
    mv="; ".join(f"{k} → {ref(v)}" for k,v in moved.items()) or "—"
    w(f"| S{i} | {ref(sl)} | {nw} | {mv} | {why} |")
w("\n## 3. Rename / move\n")
w("| ID | Current | New slug | Why |\n|---|---|---|---|")
for i,(sl,n,nd,why) in enumerate(RENAME,1):
    w(f"| R{i}{' ⚖' if sl in JUDG else ''} | {ref(sl)} | `{n}` [{(nd or home[sl]):02d}]{' (moves from '+format(home[sl],'02d')+')' if nd else ''} | {why} |")
def r2(x): return f"`{x}` [{(home.get(x) or next(d for d,v in final.items() if x in v)):02d}]"
w("\n## 4. Group boundaries — all members stay\n")
w("Pairwise boundaries inside these clusters could contradict each other, so each group has one statement. Every member's anchor should be written from it. Rule: classify by the chapter's primary subject; the others become secondary tags.\n")
w("| ID | Group | Members | Boundary |\n|---|---|---|---|")
for gid,name,mem,why in GROUPS: w(f"| {gid} | {name} | {' · '.join(r2(m) for m in mem)} | {why} |")
w("\n## 5. Scope pairs — both stay, anchors state the boundary\n")
w("Slugs that are new or renamed above appear under their new name. Where one product or tool sits on both sides, the boundary says how to classify by what the chapter explains, with an example each way.\n")
w("| ID | Subdomain A | Subdomain B | Boundary the anchors must draw (A vs B) |\n|---|---|---|---|")
for i,(a,b,why) in enumerate(SCOPE,1): w(f"| P{i} | {r2(a)} | {r2(b)} | {why} |")
w("\n## 6. Domain-level authoring note\n")
w("- **Domain 07 (Kernel, Systems Programming & Operating Systems):** `operating-systems-concepts` [07] takes OS theory and textbook-level treatment (process model, scheduling theory, virtual-memory concepts). Every other 07 subdomain takes implementation of its subject in a real kernel. This applies to all 07 pairs, so it is a rule for the whole domain rather than one scope row.\n")
w("## 7. Untouched\n")
w("No overlap with any other subdomain was found for these. They keep their slug and need no boundary statement.\n")
w("| Domain | Untouched subdomains |\n|---|---|")
for d,v in untouched.items(): w(f"| {d:02d} {D[d].name} | {' · '.join('`'+x+'`' for x in v) or '— (all slugs touched by a row above)'} |")
w("\n## 8. Counts and change ledger\n")
w("Every number here is computed from the rows above. Per domain: **Now** − consolidated − slugs moved out + extra slugs from splits + slugs moved in = **After**.\n")
w("| Domain | Slug (OQ#12 default) | Now | − Consolidated | Split net | Moved out | Moved in | After |\n|---|---|---|---|---|---|---|---|")
tot=[0]*6
for d in D:
    now=len(D[d].subdomain_slugs)
    cons=sum(1 for r,_,_ in CONSOLIDATE if home[r]==d)
    spl=sum(len(new)-1 for sl,new,_,_ in SPLIT if home[sl]==d)
    mo=sum(1 for sl,_,nd,_ in RENAME if nd and home[sl]==d)
    mi=sum(1 for sl,_,nd,_ in RENAME if nd==d)
    after=now-cons+spl-mo+mi; assert after==len(final[d]),(d,after,len(final[d]))
    for k,v in enumerate((now,cons,spl,mo,mi,after)): tot[k]+=v
    w(f"| {d:02d} {D[d].name} | `{default_domain_slug(D[d].name)}` | {now} | {('−'+str(cons)) if cons else '0'} | {('+' if spl>0 else '')+str(spl)} | {mo} | {mi} | {after} |")
w(f"| **Total** | | **{tot[0]}** | **−{tot[1]}** | **{'+' if tot[2]>0 else ''}{tot[2]}** | **{tot[3]}** | **{tot[4]}** | **{tot[5]}** |")
w("\nSplits S3, S5, S6 and S7 rename one slug and move part of its content to a slug that already exists, so they change no count. S4 dissolves its slug (−1); S1 and S2 each add one (+1).\n")
w("## 9. Changes after external review (rev 1 → rev 2)\n")
w("| Row (rev 1) | Rev 1 proposal | Rev 2 | Why |\n|---|---|---|---|")
w("| C2 `real-time-kernels` | Consolidate into `rtos` | Scope pair | Real-time behaviour in general-purpose kernels and RTOS products for microcontrollers are separate practitioner communities. |")
w("| C4 `cap-theorem` | Consolidate into `consistency-models` | Scope pair | A named theorem with its own literature (Brewer, Gilbert–Lynch, PACELC); rev 1 was inconsistent with scoping `zero-knowledge-proofs`. |")
w("| C12 `agentic-workflows` | Consolidate into `llm-agents` | Group G2 | Deterministic workflows with agent steps are a real distinct case. |")
w("| C14 `ml-pipelines` | Consolidate into `mlops` | Group G3 | Pipeline construction is a sizeable topic of its own. |")
w("| C17 `rpg` | Consolidate into `as400-rpg-ecosystem` | Scope pair | Consistency: languages stay in 03, platforms in 28, as with `cobol` vs `mainframe-zos`. |")
w("| C18 `conways-law` | Consolidate into `sociotechnical-systems` | Scope pair | A distinct principle; domain 30 was losing three slugs. |")
w("| P29, P53, P54, P70, P75, P76, P81, P84, P85, P86 | Pairwise boundaries | Groups G1–G4 | Pairwise statements inside a cluster could contradict each other. |")
w("| P129 (07 OS concepts vs Linux kernel) | Scope pair | Domain note (§6) | It is a rule for the whole of domain 07, not an A-vs-B boundary. |")
w("| Tool-ambiguous pairs (caching/key-value, workflow/data-pipelines, event-sourcing/EDA, graph theory/algorithms, GC/memory management, formal verification techniques) | One-line boundary | Boundary + classification rule + examples | One product or tool can sit on both sides; classify by what the chapter explains. |")
w("| R6 alternative | Uncosted | Costed (−3) | So it can be chosen knowingly. |")
w("\nKept despite pushback (marked ⚖): C9 snapshot/golden testing (same technique, two names), C10 query planners/optimization (the planner is the optimizer in the database literature), and the `bm25` consolidation (its literature is small and always framed inside ranking; the `ranking-relevance` anchor must name BM25). The ISA/RISC-V and scheme/racket rows were flagged by one reviewer, but they are scope rows that keep both slugs, which is what the reviewer asked for.\n")
w("## 10. What accepting changes\n")
w("- **HTC-MULTIDIM-2.0 Appendix A** (the taxonomy source) gets the accepted changes. The subdomain count (474) is stated in HTC and ETDI (goal rows, the `ANCHOR_MIN_COVERAGE` default in ETDI §7, SCE/GHK text), and it moves to the new total.")
w("- **Domain moves:** `distributed-tracing` [08] becomes `observability-tracing` [17]. The S-rows move content (not slugs) to existing slugs in 17, 19, 24, 25, 08 and 12. A builder must not create a second copy of any existing slug named in a \"moved to\" cell.")
w("- **ETDI design/WBS:** the manifest builder (BEH-07.01) reads Appendix A, so no code change is needed. The anchor template and authoring guide are regenerated from the amended appendix, and `ANCHOR_MIN_COVERAGE` follows the new count.")
w("- **Anchor authoring** starts from the regenerated template. Each group boundary (§4), scope boundary (§5) and the domain note (§6) is written into the anchors of every member. Each accepted row's \"Why\" text is the seed for its anchor.")
w("- **Validation gates** (added to the design when accepted):")
w("  - Structural, at manifest build: the subdomain count equals the new total, there are 34 domains, per-domain counts equal §8 \"After\", every slug is unique, and no removed slug remains.")
w("  - Anchor separation, after anchors are drafted (needs COS): embed every anchor and flag any scoped pair or group member whose anchors are too close to separate.")
w("- **No migration:** the fresh seed writes only the new slugs, so no existing Qdrant or Neo4j reference needs migrating.")
w("- Rejected rows change nothing.")
w("## 11. Changes after anchor curation (rev 2 → rev 3, user 2026-10-21)\n")
w("| Item | Change | Why |")
w("| :--- | :--- | :--- |")
w("| P109 `technical-writing-docs-as-code` / `technical-communication` | `technical-communication` covers explaining technical problems plus decisions to any audience, including technical communication as a discipline; documentation craft plus tooling stays with `technical-writing-docs-as-code` | Reviewers had excluded 12 chapters on the discipline; the user ruled it covers both |")
w("| P118 note | `set-theory` includes fuzzy plus rough set theory | Reviewers had excluded them; no other subdomain holds them; both are set-theoretic frameworks |")
w("")
out=Path("<DOCS_REPO>")
out.write_text("\n".join(L)+"\n")
acct=sum(len(v) for v in untouched.values())+len(touched & set(home))
print("total after",total,"touched-original",len(touched&set(home)),"untouched",sum(len(v) for v in untouched.values()),"sum",acct)
