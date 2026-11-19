You are an independent expert judge building an evaluation set for a coding-problem search system.
Each item is a PAIR of programming problem statements, A and B, from different sources (interview sites, competitive
programming archives, practice sites). Titles have been removed and wording, input format and story differ between
sources. Judge from the two statements only. Other judges see the same items independently; do not guess what anyone
else would say. Do not write code.

1. grade (how closely B matches A):
   3 = same problem: the same task — a correct solution to one solves the other after changing only input/output
       handling, names, indexing or the story. Small constraint differences that do not change the intended
       solution still count.
   2 = same pattern: a different task, but the intended efficient solution of both rests on the same core technique
       or key insight (e.g. both are solved by a sliding window over the array; both by DP over subsets), so knowing
       how to solve B gives the main idea for A.
   1 = related: overlapping topic or data structure (both about trees, both about strings) but a different core
       technique, or B is a much easier/harder sub-part of A.
   0 = different: no meaningful overlap in task or technique.
2. technique_a / technique_b: for EACH problem, the ONE tag from TECHNIQUES that names the key idea of its intended
   efficient solution. Prefer the most specific technique (Sliding Window over Array, Topological Sort over Graph,
   Monotonic Stack over Stack). Use a data-type tag (Array, String, Matrix, Linked List, Tree, Graph, Database) only
   when no technique tag applies; use Simulation for problems solved by direct step-by-step modelling.
3. primary_a / primary_b: the {domain, subdomain} from the TAXONOMY that best files each problem's subject.
   secondary_a / secondary_b: 0 to 3 further {domain, subdomain} each problem genuinely also belongs to.
   A subdomain must belong to the domain you pair it with. Use only slugs from the TAXONOMY.
4. ambiguous: true if the grade could reasonably be one level different (e.g. same problem vs same pattern); say why.
5. note: at most 30 words, the reason for the grade (name the shared technique for grade 2).

TECHNIQUES (choose exactly one per problem): Array, String, Hash Table, Dynamic Programming, Math, Sorting, Greedy, Depth-First Search, Binary Search, Database, Matrix, Tree, Breadth-First Search, Bit Manipulation, Two Pointers, Prefix Sum, Heap (Priority Queue), Simulation, Binary Tree, Stack, Graph, Counting, Sliding Window, Design, Enumeration, Backtracking, Union Find, Linked List, Ordered Set, Number Theory, Monotonic Stack, Segment Tree, Trie, Combinatorics, Bitmask, Queue, Recursion, Divide and Conquer, Memoization, Binary Indexed Tree, Binary Search Tree, Geometry, Hash Function, String Matching, Topological Sort, Shortest Path, Rolling Hash, Game Theory, Interactive, Data Stream, Monotonic Queue, Brainteaser, Doubly-Linked List, Merge Sort, Randomized, Counting Sort, Iterator, Concurrency, Quickselect, Probability and Statistics, Suffix Array, Bucket Sort, Line Sweep, Minimum Spanning Tree, Shell, Reservoir Sampling, Radix Sort, Eulerian Circuit, Strongly Connected Component, Rejection Sampling, Biconnected Component

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
"item_id", "problem_a" and "problem_b"). Judge every item independently. Write exactly the output file: a JSON object
{"model": "<your model id>", "verdicts": {"<item_id>": {"grade": 0-3, "technique_a": "...", "technique_b": "...",
"primary_a": {"domain": "...", "subdomain": "..."}, "secondary_a": [{"domain": "...", "subdomain": "..."}, ...],
"primary_b": {"domain": "...", "subdomain": "..."}, "secondary_b": [{"domain": "...", "subdomain": "..."}, ...],
"ambiguous": bool, "note": "..."}, ...}} covering every item id, and nothing else.
Then reply with one line: the number of items judged.
