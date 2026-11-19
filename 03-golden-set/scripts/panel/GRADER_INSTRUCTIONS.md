You are an independent expert grader building an evaluation set for a technical-library search system.
For each item you get a QUESTION, the KEY POINTS of its accepted, community-vetted answer, and one PASSAGE taken from a
book, paper, article or talk transcript. Judge the passage on its own text only. Other graders judge the same items
independently; do not guess what anyone else would say.

1. grade (relevance of the passage to the question):
   3 = states the core of the answer (the central key point or points) in a way a reader could act on
   2 = states part of the answer (at least one key point) but misses the core, or states it only briefly
   1 = background or related material only: useful context, states no key point
   0 = not relevant to this question (shared vocabulary only, or a different question)
2. covers: ids of the key points the passage itself substantively states (not merely mentions a term from). Empty if none.
3. beyond_key_points: true only if the passage gives a correct element of the answer that none of the key points contain.
4. role: "direct" if the passage addresses the question as asked; "foundation" if it is theory, definitions, proofs or
   research that the answer rests on without addressing the question itself; "none" if grade is 0.
5. Labels describe the PASSAGE's own subject (not the question). Use only slugs from the TAXONOMY below:
   primary = {domain, subdomain} that best files this passage; secondary = 0 to 3 further {domain, subdomain} it
   genuinely also belongs to; knowledge_function = the passage's function, one of the four KNOWLEDGE FUNCTIONS.
   A subdomain must belong to the domain you pair it with.
6. ambiguous: true if the passage could reasonably be graded or filed two different ways; say why in note.
7. note: at most 40 words, the reason for the grade.

KNOWLEDGE FUNCTIONS:
- role-definition: What IS it — Theory, principles, definitions
- implementation-ref-spec: How do you BUILD it — Code, APIs, patterns
- failure-mode-limitation: What goes WRONG — Anti-patterns, CVEs, known pitfalls
- supporting-papers: What's the EVIDENCE — Research, benchmarks

TAXONOMY (domain: subdomains):
- mathematical-theoretical-foundations: discrete-mathematics, linear-algebra, calculus-analysis, probability-statistics, optimization-theory, information-theory, coding-theory, formal-logic, set-theory, number-theory, graph-theory, automata-theory, computability-theory, complexity-theory, category-theory, formal-verification, model-checking, theorem-proving, symbolic-execution, executable-specifications
- algorithms-data-structures: sorting-searching, graph-algorithms, dynamic-programming, greedy-algorithms, divide-and-conquer, randomized-algorithms, approximation-algorithms, string-algorithms, data-structures-linear, data-structures-trees, data-structures-hash, data-structures-advanced, probabilistic-data-structures, spatial-data-structures, streaming-algorithms
- programming-languages: c, cpp, rust, zig, nim, d-language, go, objective-c, swift, ada, java, csharp, kotlin, scala, groovy, visual-basic-dotnet, delphi-object-pascal, python, ruby, php, perl, lua, javascript, typescript, tcl, powershell, bash-shell, haskell, ocaml, fsharp, standard-ml, erlang, elixir, clojure, scheme, racket, common-lisp, elm, purescript, prolog, datalog, answer-set-programming, constraint-programming, fortran, matlab-octave, r-language, julia, apl, j-language, k-language, cobol, rpg, pl-i, algol, classic-basic, classic-pascal, simula
- hardware-description-digital-design: vhdl, verilog-systemverilog, chisel, fpga-development, asic-design, digital-logic-design
- compilers-language-implementation: lexing-parsing, semantic-analysis-type-checking, intermediate-representations, optimization-passes, code-generation, jit-compilation, llvm-ecosystem, interpreters-bytecode-vms, garbage-collector-implementation, static-analysis-tooling, webassembly, memory-constrained-compilation
- computer-architecture: cpu-architecture, superscalar-execution, branch-prediction, cpu-caches, cpu-pipelines, numa, simd, gpu-architecture, memory-hierarchy, instruction-set-architectures, arm, x86, power, risc-v, accelerator-hardware, tensor-processors
- kernel-systems-programming-operating-systems: kernel-development-linux, kernel-development-windows, kernel-development-bsd, device-drivers, hypervisors-virtualization, microkernels, bootloaders-boot-process, filesystems-implementation, memory-allocators, interrupt-io-handling, real-time-kernels, operating-systems-concepts, memory-management, concurrency-synchronization
- distributed-systems-engineering: consensus-algorithms, replication, consistency-models, cap-theorem, distributed-transactions, leader-election, gossip-protocols, distributed-scheduling, distributed-coordination, event-sourcing, cqrs, actor-systems
- networking-distributed-communication: network-architecture, tcp-ip, routing, switching, dns, dhcp, ipv4-ipv6, bgp, mpls, sdn, network-automation, network-virtualization, wireless-networking, cellular-5g, network-monitoring, packet-analysis, network-programming
- apis-integration-messaging: rest, graphql, grpc, openapi-asyncapi, soap-rpc, webhooks-event-apis, api-gateways, sdk-design, serialization-formats, message-queues, enterprise-integration-patterns, workflow-orchestration-bpm, systems-integration-topology
- storage-systems: block-storage, object-storage, distributed-storage-systems, raid, ssd-nvme-internals, compression-deduplication
- performance-engineering: profiling, benchmarking, latency-optimization, throughput-scalability, concurrency-tuning, cache-optimization, memory-optimization, simd-vectorization, gpu-compute-optimization, lock-free-programming
- software-architecture: clean-hexagonal-onion-architecture, microservices-architecture, soa, modular-monoliths, event-driven-architecture, architecture-decision-records, architecture-evaluation-tradeoff-analysis, quality-attributes, architecture-governance, architectural-drift-analysis, infrastructure-solution-design
- software-engineering-design: design-pattern-foundations, design-patterns-behavioral, design-patterns-creational, design-patterns-structural, domain-driven-design, debugging, refactoring, software-quality, engineering-practices, requirements-engineering, technical-debt-economics, software-maintenance-evolution, program-comprehension, software-product-lines, software-metrics, empirical-software-engineering, software-reliability-engineering, ai-code-auditing
- testing-quality-assurance: unit-testing, integration-testing, e2e-testing, property-based-testing, mutation-testing, fuzzing, load-performance-testing, chaos-engineering, test-automation-frameworks, qa-process, accessibility-testing, static-dynamic-analysis, contract-testing, concurrency-testing, security-testing, api-testing, regression-testing, golden-testing, deterministic-validation
- data-engineering-databases: data-pipelines, batch-processing, stream-processing, data-lakes, data-warehousing, data-quality-governance, databases-relational, databases-nosql, databases-columnar, databases-graph, databases-vector, databases-key-value, databases-time-series, databases-spatial, databases-newsql, caching, query-optimization, indexing, transaction-processing-oltp-olap, sharding-partitioning, storage-engines
- devops-cloud-platform-engineering: ci-cd, infrastructure-as-code, containers-kubernetes, gitops, cloud-platforms, service-mesh, sre-reliability, platform-engineering, release-engineering, feature-flags, incident-management, serverless-edge-computing, observability-logging, observability-metrics, observability-telemetry-pipelines, apm-synthetic-monitoring, alerting-dashboards, observability-tracing
- artificial-intelligence-machine-learning: ml-foundations-classical, deep-learning-foundations, deep-learning-architectures, generative-models, diffusion-models, llm-foundations, llm-architecture, llm-training, llm-inference, edge-local-inference, llm-prompting, llm-rag, llm-agents, multi-agent-orchestration, agentic-workflows, autonomous-development-cycles, context-management-services, llm-multimodal, llm-alignment-safety, llm-evaluation, model-compression-quantization-pruning-distillation, peft-lora, rlhf-dpo, synthetic-data, embedding-models, knowledge-graphs, reasoning-models, computer-vision, image-classification, image-generation, nlp-algorithms, nlp-applications, text-classification, text-generation, speech-audio, reinforcement-learning-theory, reinforcement-learning-applications, ml-pipelines, ml-serving, ml-platform, experiment-tracking, mlops, robotics-embodied-ai, recommender-systems
- search-information-retrieval: inverted-indexes, ranking-relevance, lucene-elasticsearch-solr, vector-search, ann-algorithms, hybrid-retrieval, query-expansion, ir-theory, search-engines
- security-privacy: application-security, cloud-security, network-security, web-security, memory-security, cryptography-foundations, cryptography-applied, identity-authentication, incident-response, vulnerability-research, supply-chain-security, privacy-compliance, zero-trust, ai-ml-security, reverse-engineering, malware-analysis, penetration-testing, secure-coding, threat-modeling, exploit-development, secure-sdlc, digital-forensics, hardware-security, side-channel-attacks, trusted-execution-environments
- web-frontend-development: html-css, frontend-frameworks, frontend-performance, browsers, http-protocols, mobile-responsive-design, i18n-l10n, progressive-web-apps
- mobile-development: ios-swift, android-kotlin, cross-platform-react-native-flutter, mobile-performance, app-store-release
- game-development-computer-graphics: game-engines, graphics-programming, shaders-gpu-programming, game-ai, physics-engines, rendering-pipelines, procedural-generation
- embedded-iot-real-time-systems: firmware, microcontrollers, rtos, embedded-c, hardware-software-codesign, sensor-networks-iot-protocols
- numerical-scientific-computing: numerical-methods, high-performance-computing, scientific-computing-tools, simulation-modeling, computational-science
- developer-tooling-build-systems: ides-editors, debuggers, linters-formatters, build-systems, package-managers, monorepo-polyrepo, devex, codebase-topology, ast-knowledge-graphs, semantic-code-search, graph-grounded-retrieval
- blockchain-distributed-ledger-technology: blockchain-consensus-mechanisms, smart-contracts, solidity, vyper, move-language, cairo, clarity, defi-patterns, nft-standards, zero-knowledge-proofs, layer2-scaling, tokenomics, blockchain-security, cryptocurrency-protocols
- legacy-mainframe-computing: mainframe-zos, jcl-batch-processing, cics-transaction-processing, as400-rpg-ecosystem, legacy-modernization-migration
- software-process-documentation-collaboration: agile-scrum-kanban, estimation-sprint-planning, technical-writing-docs-as-code, code-review, licensing-oss-governance
- engineering-management-organizational-design: technical-leadership, engineering-management, organizational-design, sociotechnical-systems, conways-law, platform-strategy, developer-productivity, technical-strategy, engineering-metrics, roadmap-planning, decision-making, technical-communication, postmortems
- ux-design-hci: accessibility, interaction-design, information-architecture, visual-graphic-design, design-systems, data-visualization, product-design, user-research
- standards-protocols: web-standards, api-standards, compliance-standards
- applied-verticals-industry-specific-engineering: advertising-technologies, ethics-in-tech, fintech-engineering, healthtech-engineering, govtech-engineering
- quantum-computing: quantum-algorithms, quantum-programming-languages, quantum-hardware-architectures


OUTPUT: you will be given a sheet path and an output path. Read the sheet (a JSON object with "items", each with
"item_id", "text" and "key_point_ids"). Grade every item independently. Write exactly the output file: a JSON object
{"model": "<your model id>", "verdicts": {"<item_id>": {"grade": 0-3, "covers": [...], "beyond_key_points": bool,
"role": "direct"|"foundation"|"none", "primary": {"domain": "...", "subdomain": "..."}, "secondary": [...],
"knowledge_function": "...", "ambiguous": bool, "note": "..."}, ...}} covering every item id, and nothing else.
Then reply with one line: the number of items graded.
