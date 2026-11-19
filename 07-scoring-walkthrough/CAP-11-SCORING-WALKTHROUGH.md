# CAP-11 Scoring Walkthrough — options for Q1–Q3 on hypothetical and real chapters

2026-10-26 · decision support for ETDI-1.0 design v0.18 CAP-11 (BEH-11.01/11.02, §5.1.9.91–.96). Every number was computed by the implemented HTC atoms (`ScoreNormalizer`, `SecondaryTagResolver`, `ProfileAssembler`, `PieceScorePooler`); the real chapters were embedded by COS's `ProfileEmbedder` with jina-v3. Scripts and raw outputs: `_evidence/cap11_scoring_walkthrough/` (hypothetical.py, rollups.py, sample.py, realrun.py, realscore.py, altrules.py, compare.py, v15mem.py and their outputs). This page is transient; whatever you decide goes into the design document.

**How to read the tables.** *Share* = a normalized score (a level's shares sum to 1). *Primary score* = subdomain share × KF share of the primary pair; a secondary qualifies when its own pair score ≥ ratio (0.6) × that. ⚑ marks a secondary that outscores its primary. *T* is the softmax temperature (uncalibrated — OQ#24); hypotheticals use T = 0.02.

**The three Q1 options.** **A — pure:** the primary is the top of the pooled shares; signals, code density, and the weak-match floor are dropped. **B — old components choose:** today's KFAssigner (anchor top-1, `unassigned` below raw 0.2, >50% code → implementation) and SubdomainResolver (+0.15 raw per signal, inside the primary domain) pick the primary on the pooled vector; the shares are only stored and used for secondaries. **C — fold:** after pooling, each signal adds its weight to its share (+0.25 KF, +0.15 subdomain; >50% code counts as a +0.25 implementation signal), renormalize, keep `unassigned` on the raw floor, and take the top.

## Part 1 — Q1 hypothetical scenarios

### H1 · Single-topic chapter (Raft explained)

- Domain shares: distributed-systems-engineering 0.810, storage-systems 0.070, software-architecture 0.040
- Subdomain shares (whole taxonomy): consensus-algorithms 0.620, leader-election 0.080, replication 0.060, discrete-mathematics 0.020, linear-algebra 0.020
- KF raw similarity: implementation-ref-spec 0.470, failure-mode-limitation 0.417, role-definition 0.413, supporting-papers 0.403 → shares at T=0.02: implementation-ref-spec 0.860, failure-mode-limitation 0.060, role-definition 0.050, supporting-papers 0.030

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.533 | none |
| B old components | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.533 | none |
| C fold | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.533 | none |

**Takeaway:** a clear single-topic chapter — every option agrees. The options only differ when signals, code density, or weak matches are involved.

### H2 · Same-domain secondaries (consensus with a failure-handling section)

- Domain shares: distributed-systems-engineering 0.700, storage-systems 0.150, software-architecture 0.080
- Subdomain shares (whole taxonomy): consensus-algorithms 0.400, leader-election 0.300, replication 0.100, discrete-mathematics 0.017, linear-algebra 0.017
- KF raw similarity: implementation-ref-spec 0.460, failure-mode-limitation 0.454, role-definition 0.402, supporting-papers 0.394 → shares at T=0.02: implementation-ref-spec 0.550, failure-mode-limitation 0.400, role-definition 0.030, supporting-papers 0.020

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.220 | (distributed-systems-engineering / leader-election / implementation-ref-spec) 0.165; (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.160 |
| B old components | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.220 | (distributed-systems-engineering / leader-election / implementation-ref-spec) 0.165; (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.160 |
| C fold | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.220 | (distributed-systems-engineering / leader-election / implementation-ref-spec) 0.165; (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.160 |

**Takeaway:** the multi-label rule working as intended: the second subdomain and the second KF both surface as secondaries in the primary's own domain. All options agree.

### H3 · Code-heavy chapter (70% listings; anchors lean role-definition)

- Domain shares: distributed-systems-engineering 0.660, software-architecture 0.180, storage-systems 0.080
- Subdomain shares (whole taxonomy): consensus-algorithms 0.400, replication 0.120, leader-election 0.080, discrete-mathematics 0.033, linear-algebra 0.033
- KF raw similarity: role-definition 0.480, implementation-ref-spec 0.478, failure-mode-limitation 0.460, supporting-papers 0.442 → shares at T=0.02: role-definition 0.410, implementation-ref-spec 0.380, failure-mode-limitation 0.150, supporting-papers 0.060
- Signals: KF —, subdomain —, code ratio 0.70

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | distributed-systems-engineering / consensus-algorithms / role-definition | 0.164 | (distributed-systems-engineering / consensus-algorithms / implementation-ref-spec) 0.152 |
| B old components | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.152 | (distributed-systems-engineering / consensus-algorithms / role-definition) 0.164 |
| C fold | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.202 | (distributed-systems-engineering / consensus-algorithms / role-definition) 0.131 |

C's adjusted KF shares: implementation-ref-spec 0.504, role-definition 0.328, failure-mode-limitation 0.120, supporting-papers 0.048

**Takeaway (Q1 core case):** anchors lean role-definition by a hair (0.41 vs 0.38) but the text is 70% code. **A** follows the anchors (role-definition). **B** forces implementation, so the stored data shows a secondary (0.164) *outscoring* its primary (0.152). **C** reaches the same primary as B but keeps the stored distribution consistent with it (0.202 primary, 0.131 secondary).

### H4 · Table-of-contents fragment (nothing matches well: best KF cosine 0.15)

- Domain shares: distributed-systems-engineering 0.400, software-architecture 0.300, storage-systems 0.200
- Subdomain shares (whole taxonomy): consensus-algorithms 0.300, replication 0.200, leader-election 0.150, discrete-mathematics 0.029, linear-algebra 0.029
- KF raw similarity: role-definition 0.150, implementation-ref-spec 0.149, failure-mode-limitation 0.145, supporting-papers 0.140 → shares at T=0.02: role-definition 0.300, implementation-ref-spec 0.280, failure-mode-limitation 0.240, supporting-papers 0.180

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | distributed-systems-engineering / consensus-algorithms / role-definition | 0.090 | (distributed-systems-engineering / consensus-algorithms / implementation-ref-spec) 0.084; (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.072; (distributed-systems-engineering / replication / role-definition) 0.060; (distributed-systems-engineering / replication / implementation-ref-spec) 0.056; (distributed-systems-engineering / consensus-algorithms / supporting-papers) 0.054 |
| B old components | distributed-systems-engineering / consensus-algorithms / unassigned | — | none |
| C fold | distributed-systems-engineering / consensus-algorithms / unassigned | — | none |

**Takeaway:** shares always sum to 1, so with nothing matching **A** still crowns a primary and spawns five noise secondaries. **B/C** keep today's `unassigned` rule because it tests the *raw* similarity (0.15 < 0.2), which shares can no longer see. (The real run below shows the 0.2 floor itself is wrong for jina-v3.)

### H5 · CRE unit: HTTP client with retry_loop + timeout_guard (signal subdomain in ANOTHER domain)

- Domain shares: apis-integration-messaging 0.640, devops-cloud-platform-engineering 0.200, software-engineering-design 0.080
- Subdomain shares (whole taxonomy): rest 0.340, grpc 0.140, api-gateways 0.100, sre-reliability 0.080, discrete-mathematics 0.028
- KF raw similarity: implementation-ref-spec 0.500, failure-mode-limitation 0.475, role-definition 0.451, supporting-papers 0.443 → shares at T=0.02: implementation-ref-spec 0.700, failure-mode-limitation 0.200, role-definition 0.060, supporting-papers 0.040
- Signals: KF —, subdomain ['sre-reliability', 'sre-reliability'], code ratio 0.00

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | apis-integration-messaging / rest / implementation-ref-spec | 0.238 | none |
| B old components | apis-integration-messaging / rest / implementation-ref-spec | 0.238 | none |
| C fold | apis-integration-messaging / rest / implementation-ref-spec | 0.183 | (devops-cloud-platform-engineering / sre-reliability / implementation-ref-spec) 0.205 |

C's adjusted subdomain shares: sre-reliability 0.292, rest 0.262, grpc 0.108, api-gateways 0.077, discrete-mathematics 0.022

**Takeaway:** retry/timeout signals point at `sre-reliability`, which lives in a *different* domain. **A** and **B** ignore it (B's old resolver only ranks inside the primary domain). **C** surfaces it as a cross-domain secondary — but that secondary (0.205) outscores the primary (0.183), because the primary subdomain must sit inside the primary domain while secondaries may come from anywhere. This inversion is not an A/B/C issue; see Part 3.

### H6 · CRE unit: validator with two validation_guard signals (signal subdomain INSIDE the primary domain; anchor top design-pattern-foundations)

- Domain shares: software-engineering-design 0.580, testing-quality-assurance 0.220, security-privacy 0.100
- Subdomain shares (whole taxonomy): design-pattern-foundations 0.400, software-quality 0.220, design-patterns-behavioral 0.100, discrete-mathematics 0.023, linear-algebra 0.023
- KF raw similarity: implementation-ref-spec 0.500, failure-mode-limitation 0.482, role-definition 0.464, supporting-papers 0.450 → shares at T=0.02: implementation-ref-spec 0.600, failure-mode-limitation 0.250, role-definition 0.100, supporting-papers 0.050
- Signals: KF —, subdomain ['software-quality', 'software-quality'], code ratio 0.00

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | software-engineering-design / design-pattern-foundations / implementation-ref-spec | 0.240 | none |
| B old components | software-engineering-design / software-quality / implementation-ref-spec | 0.132 | (software-engineering-design / design-pattern-foundations / implementation-ref-spec) 0.240; (software-engineering-design / design-pattern-foundations / failure-mode-limitation) 0.100 |
| C fold | software-engineering-design / software-quality / implementation-ref-spec | 0.240 | (software-engineering-design / design-pattern-foundations / implementation-ref-spec) 0.185 |

C's adjusted subdomain shares: software-quality 0.400, design-pattern-foundations 0.308, design-patterns-behavioral 0.077, discrete-mathematics 0.018, linear-algebra 0.018

**Takeaway:** signals point *inside* the primary domain. **B** and **C** flip the primary to `software-quality` as today (SCE-06.03.03); **A** ignores signals. Under **B** the old primary (0.240) is recorded as a secondary outscoring the new primary (0.132); **C** keeps them consistent.

### H7 · Exception-heavy CRE unit (exception_handler + raise_site → failure-mode-limitation)

- Domain shares: distributed-systems-engineering 0.700, storage-systems 0.150, software-architecture 0.080
- Subdomain shares (whole taxonomy): consensus-algorithms 0.400, leader-election 0.300, discrete-mathematics 0.025, linear-algebra 0.025, calculus-analysis 0.025
- KF raw similarity: implementation-ref-spec 0.470, failure-mode-limitation 0.467, role-definition 0.424, supporting-papers 0.414 → shares at T=0.02: implementation-ref-spec 0.500, failure-mode-limitation 0.420, role-definition 0.050, supporting-papers 0.030
- Signals: KF ['failure-mode-limitation', 'failure-mode-limitation'], subdomain —, code ratio 0.00

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.200 | (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.168; (distributed-systems-engineering / leader-election / implementation-ref-spec) 0.150; (distributed-systems-engineering / leader-election / failure-mode-limitation) 0.126 |
| B old components | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.200 | (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.168; (distributed-systems-engineering / leader-election / implementation-ref-spec) 0.150; (distributed-systems-engineering / leader-election / failure-mode-limitation) 0.126 |
| C fold | distributed-systems-engineering / consensus-algorithms / failure-mode-limitation | 0.245 | (distributed-systems-engineering / leader-election / failure-mode-limitation) 0.184 |

C's adjusted KF shares: failure-mode-limitation 0.613, implementation-ref-spec 0.333, role-definition 0.033, supporting-papers 0.020

**Takeaway:** two exception signals. Today (and under **A**/**B**) signals only nudge the stored KF shares and never change the primary KF (SCE-06.03.01). **C** as defined lets them *flip* the primary KF to failure-mode-limitation — a behaviour change you would be signing up for.

### Pooling a long two-topic chapter

- Piece 1 (8,160 tokens): consensus-algorithms 0.600, storage-engines 0.050
- Piece 2 (3,900 tokens): storage-engines 0.650, consensus-algorithms 0.040
- Pooled (token-weighted): consensus-algorithms 0.419, storage-engines 0.244, discrete-mathematics 0.028
- ratio 0.6: primary consensus-algorithms (0.335); secondaries none
- ratio 0.45: primary consensus-algorithms (0.335); secondaries (data-engineering-databases / storage-engines / implementation-ref-spec) 0.195

**Takeaway:** token-weighted pooling keeps both topics in the stored distribution (0.419 / 0.244), but at ratio 0.6 the second topic is not a secondary (0.244 / 0.419 = 0.58). Whether a genuine two-topic chapter should carry its second topic is a ratio question (it does at 0.45).

## Part 2 — Q2 roll-ups and Q3 storage

Members are unit profiles with full shares. **R1** = mean of member distributions, then the same assembly rule (size-, confidence-, or equal-weighted). **R2** = R1 with the ratio lowered to 0.45. **R3** = today's vote (confidence-weighted plurality of member primaries) for the primary, secondaries from the size-weighted means.

### M1 · authn.py — 15 small auth units + 1 large metrics unit

| Member | Lines | Primary domain / subdomain | Confidence |
|---|---|---|---|
| auth helper 0 (×15) | 20 | security-privacy / identity-authentication | 0.74 |
| AuthMetrics.record_rejection | 120 | devops-cloud-platform-engineering / observability-logging | 0.60 |

| Option | Primary (domain / subdomain / KF) | Domain shares | Secondaries |
|---|---|---|---|
| R1 size-weighted | security-privacy / identity-authentication / implementation-ref-spec | security-privacy 0.580, devops-cloud-platform-engineering 0.286 | none |
| R1 confidence-weighted | security-privacy / identity-authentication / implementation-ref-spec | security-privacy 0.711, devops-cloud-platform-engineering 0.150 | none |
| R1 equal | security-privacy / identity-authentication / implementation-ref-spec | security-privacy 0.705, devops-cloud-platform-engineering 0.156 | none |
| R2 size-weighted, ratio 0.45 | security-privacy / identity-authentication / implementation-ref-spec | security-privacy 0.580, devops-cloud-platform-engineering 0.286 | none |
| R3 vote + secondaries from size-weighted means | security-privacy / identity-authentication / implementation-ref-spec | security-privacy 0.949, devops-cloud-platform-engineering 0.051 (vote) | none |

**Takeaway:** a large divergent unit (the metrics recorder) never becomes a module secondary under any option at 0.6 or 0.45 — it is kept visible by the existing `is_divergent_from_parent` flag, not by secondaries. All options agree on the primary.

### M2 · token.py — 3 tiny auth helpers (10 lines each) + 1 large REST handler

| Member | Lines | Primary domain / subdomain | Confidence |
|---|---|---|---|
| auth helper 0 (×3) | 10 | security-privacy / identity-authentication | 0.74 |
| TokenEndpoint.post (REST handler) | 240 | apis-integration-messaging / rest | 0.72 |

| Option | Primary (domain / subdomain / KF) | Domain shares | Secondaries |
|---|---|---|---|
| R1 size-weighted | apis-integration-messaging / rest / implementation-ref-spec | apis-integration-messaging 0.649, security-privacy 0.224 | none |
| R1 confidence-weighted | security-privacy / identity-authentication / implementation-ref-spec | security-privacy 0.598, apis-integration-messaging 0.237 | none |
| R1 equal | security-privacy / identity-authentication / implementation-ref-spec | security-privacy 0.595, apis-integration-messaging 0.240 | none |
| R2 size-weighted, ratio 0.45 | apis-integration-messaging / rest / implementation-ref-spec | apis-integration-messaging 0.649, security-privacy 0.224 | none |
| R3 vote + secondaries from size-weighted means | security-privacy / identity-authentication / implementation-ref-spec | security-privacy 0.755, apis-integration-messaging 0.245 (vote) | (apis-integration-messaging / rest / implementation-ref-spec) 0.366 |

**Takeaway:** the options *disagree*. Size-weighting says the module is a REST endpoint (240 of 270 lines); votes and confidence-weighting say it is auth (3 of 4 units). R3 then records `rest` as a secondary that outscores its own primary (⚑-type inversion).

### M3 · policy_sentry component — 6 cloud-policy modules + 2 IAM modules (the SCE-11.03.04 shape)

| Member | Lines | Primary domain / subdomain | Confidence |
|---|---|---|---|
| policy module 0 (×6) | 300 | security-privacy / cloud-security | 0.70 |
| iam module 0 (×2) | 250 | security-privacy / identity-authentication | 0.72 |

| Option | Primary (domain / subdomain / KF) | Domain shares | Secondaries |
|---|---|---|---|
| R1 size-weighted | security-privacy / cloud-security / implementation-ref-spec | security-privacy 0.804, devops-cloud-platform-engineering 0.091 | none |
| R1 confidence-weighted | security-privacy / cloud-security / implementation-ref-spec | security-privacy 0.805, devops-cloud-platform-engineering 0.090 | none |
| R1 equal | security-privacy / cloud-security / implementation-ref-spec | security-privacy 0.805, devops-cloud-platform-engineering 0.090 | none |
| R2 size-weighted, ratio 0.45 | security-privacy / cloud-security / implementation-ref-spec | security-privacy 0.804, devops-cloud-platform-engineering 0.091 | (security-privacy / identity-authentication / implementation-ref-spec) 0.193 |
| R3 vote + secondaries from size-weighted means | security-privacy / cloud-security / implementation-ref-spec | security-privacy 1.000 (vote) | none |

**Takeaway:** this is the SCE-11.03.04 shape. Averaged (size-weighted), the component is 0.591 cloud-security / 0.276 identity-authentication (ratio 0.47), so identity-authentication is a secondary only at ratio 0.45 (R2), not at 0.6 (R1) — the scenario as written cannot hold under the default ratio.

### Q3 — where the component result lives

| Option | Qdrant `code_component` point | Neo4j | Graph traversals |
|---|---|---|---|
| O1 defer (OQ#15) | primary + every secondary in the payload (`secondary_tags`), searchable today | `CodeModule` nodes carry `component_id`; no component node or edges | can reach component membership only through modules |
| O2 `CodeComponent` now | unchanged | new `CodeComponent {component_id}` node, `IN_COMPONENT` from modules, primary + secondary `CLASSIFIED_AS` | direct — but node keys are heuristic ids such as `package_structure` that change between SAS runs |

## Part 3 — Real SE chapters (jina-v3) and what they change

Seven chapters drawn from a seeded sample of `software-engineering/raw` (1,507 chapters from 177 files profiled; jina-v3 token counts: median 758, p90 5,025, max 169,802). Pieces were capped at 2,048 tokens (see finding F3).

### Findings

- **F1 — The domain-led primary breaks multi-label scoring on real text (all options).** The primary domain comes from the 34 *domain* anchors; the subdomain must then be the best one *inside* that domain. On real chapters the strongest subdomains often belong to another domain, so the forced primary subdomain has a near-zero share, the relative threshold collapses, and dozens of secondaries qualify — every one outscoring the primary: business interview 27, AI/ML lecture 62, OCR noise 65 (at T = 0.02; 40–97 at T = 0.05). A, B, and C are identical here.
- **F2 — A subdomain-led primary removes it.** Taking the primary as the best (subdomain, KF) pair anywhere — its parent becomes the primary domain — gives 0–6 secondaries on every chapter and makes an inverted secondary impossible by construction. A joint domain rule (domain anchor share × the domain's summed subdomain shares) helps but still inverts (table below). This contradicts the current "primary selection unchanged" wording (domain first) and is therefore your decision.
- **F3 — jina-v3 at the default piece size would crash this host.** Peak memory grew 0.83 GB from 512 → 2,048 tokens; attention grows with the square of the length, so 8,160-token pieces extrapolate to ~13 GB more. `EMBEDDING_PIECE_TOKENS` must be bounded for CPU hosts (2,048 used here) or COS needs memory-efficient attention.
- **F4 — With jina-v3 most chapters are one piece.** 94.7% fit in 8,160 tokens (61.6% needed pieces under nomic-v2's 480); at the 2,048 cap used here, 26.5% need pieces. Pooling matters mainly for long chapters.
- **F5 — The KF "unassigned" floor (raw 0.2) is a nomic-era constant.** jina-v3's raw KF similarities on genuine technical chapters are 0.18–0.27, so B and C mark the Iceberg and xv6 chapters `unassigned`. The floor has to be calibrated per profile with the temperature (OQ#24) — or the KF anchor texts improved.
- **F6 — Noise needs its own guard.** Under the subdomain-led rule the OCR-noise chapter becomes a confident `vulnerability-research` (0.818). Its best raw subdomain similarity is 0.29 against 0.45–0.62 for real chapters, so a raw-similarity floor (needs_review / quarantine) — not the shares — is what can catch it.
- **F7 — Temperature matters.** At T = 0.01 shares saturate (the GraphQL transcript is 1.000 everywhere); at 0.05 they flatten and secondary counts climb. The calibration run (.671) has to choose T together with the ratio and the floors.

### Alternative primary rules on the real chapters

| Chapter | T | Rule | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |
|---|---|---|---|---|---|---|
| code-heavy book chapter | 0.02 | current: domain-led | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.704 | 0 | — |
| code-heavy book chapter | 0.02 | H1: subdomain-led | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.704 | 0 | — |
| code-heavy book chapter | 0.02 | H2: joint domain | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.704 | 0 | — |
| code-heavy book chapter | 0.05 | current: domain-led | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.142 | 0 | — |
| code-heavy book chapter | 0.05 | H1: subdomain-led | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.142 | 0 | — |
| code-heavy book chapter | 0.05 | H2: joint domain | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.142 | 0 | — |
| all-code kernel note | 0.02 | current: domain-led | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.285 | 2 | kernel-development-linux/implementation-ref-spec 0.226; memory-management/implementation-ref-spec 0.222 |
| all-code kernel note | 0.02 | H1: subdomain-led | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.285 | 2 | kernel-development-linux/implementation-ref-spec 0.226; memory-management/implementation-ref-spec 0.222 |
| all-code kernel note | 0.02 | H2: joint domain | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.285 | 2 | kernel-development-linux/implementation-ref-spec 0.226; memory-management/implementation-ref-spec 0.222 |
| all-code kernel note | 0.05 | current: domain-led | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.074 | 2 | kernel-development-linux/implementation-ref-spec 0.067; memory-management/implementation-ref-spec 0.067 |
| all-code kernel note | 0.05 | H1: subdomain-led | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.074 | 2 | kernel-development-linux/implementation-ref-spec 0.067; memory-management/implementation-ref-spec 0.067 |
| all-code kernel note | 0.05 | H2: joint domain | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.074 | 2 | kernel-development-linux/implementation-ref-spec 0.067; memory-management/implementation-ref-spec 0.067 |
| long multi-piece chapter | 0.02 | current: domain-led | apis-integration-messaging / message-queues / implementation-ref-spec | 0.060 | 5 | gossip-protocols/implementation-ref-spec 0.257 ⚑; vector-search/implementation-ref-spec 0.064 ⚑; gossip-protocols/supporting-papers 0.058 |
| long multi-piece chapter | 0.02 | H1: subdomain-led | distributed-systems-engineering / gossip-protocols / implementation-ref-spec | 0.257 | 0 | — |
| long multi-piece chapter | 0.02 | H2: joint domain | distributed-systems-engineering / gossip-protocols / implementation-ref-spec | 0.257 | 0 | — |
| long multi-piece chapter | 0.05 | current: domain-led | search-information-retrieval / vector-search / implementation-ref-spec | 0.017 | 8 | gossip-protocols/implementation-ref-spec 0.033 ⚑; message-queues/implementation-ref-spec 0.018 ⚑; graphql/implementation-ref-spec 0.015 |
| long multi-piece chapter | 0.05 | H1: subdomain-led | distributed-systems-engineering / gossip-protocols / implementation-ref-spec | 0.033 | 0 | — |
| long multi-piece chapter | 0.05 | H2: joint domain | search-information-retrieval / vector-search / implementation-ref-spec | 0.017 | 8 | gossip-protocols/implementation-ref-spec 0.033 ⚑; message-queues/implementation-ref-spec 0.018 ⚑; graphql/implementation-ref-spec 0.015 |
| business + database interview | 0.02 | current: domain-led | software-architecture / microservices-architecture / implementation-ref-spec | 0.007 | 27 | engineering-practices/implementation-ref-spec 0.176 ⚑; engineering-metrics/implementation-ref-spec 0.106 ⚑; devex/implementation-ref-spec 0.105 ⚑ |
| business + database interview | 0.02 | H1: subdomain-led | software-engineering-design / engineering-practices / implementation-ref-spec | 0.176 | 1 | engineering-metrics/implementation-ref-spec 0.106 |
| business + database interview | 0.02 | H2: joint domain | engineering-management-organizational-design / engineering-metrics / implementation-ref-spec | 0.106 | 3 | engineering-practices/implementation-ref-spec 0.176 ⚑; devex/implementation-ref-spec 0.105; databases-newsql/implementation-ref-spec 0.068 |
| business + database interview | 0.05 | current: domain-led | software-architecture / microservices-architecture / implementation-ref-spec | 0.007 | 40 | engineering-practices/implementation-ref-spec 0.027 ⚑; engineering-metrics/implementation-ref-spec 0.022 ⚑; devex/implementation-ref-spec 0.022 ⚑ |
| business + database interview | 0.05 | H1: subdomain-led | software-engineering-design / engineering-practices / implementation-ref-spec | 0.027 | 6 | engineering-metrics/implementation-ref-spec 0.022; devex/implementation-ref-spec 0.022; databases-newsql/implementation-ref-spec 0.018 |
| business + database interview | 0.05 | H2: joint domain | engineering-management-organizational-design / engineering-metrics / implementation-ref-spec | 0.022 | 7 | engineering-practices/implementation-ref-spec 0.027 ⚑; devex/implementation-ref-spec 0.022; databases-newsql/implementation-ref-spec 0.018 |
| video transcript | 0.02 | current: domain-led | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| video transcript | 0.02 | H1: subdomain-led | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| video transcript | 0.02 | H2: joint domain | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| video transcript | 0.05 | current: domain-led | apis-integration-messaging / graphql / implementation-ref-spec | 0.883 | 0 | — |
| video transcript | 0.05 | H1: subdomain-led | apis-integration-messaging / graphql / implementation-ref-spec | 0.883 | 0 | — |
| video transcript | 0.05 | H2: joint domain | apis-integration-messaging / graphql / implementation-ref-spec | 0.883 | 0 | — |
| AI/ML lecture | 0.02 | current: domain-led | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.001 | 62 | julia/supporting-papers 0.421 ⚑; llm-foundations/supporting-papers 0.140 ⚑; computational-science/supporting-papers 0.078 ⚑ |
| AI/ML lecture | 0.02 | H1: subdomain-led | programming-languages / julia / supporting-papers | 0.421 | 0 | — |
| AI/ML lecture | 0.02 | H2: joint domain | artificial-intelligence-machine-learning / llm-foundations / supporting-papers | 0.140 | 1 | julia/supporting-papers 0.421 ⚑ |
| AI/ML lecture | 0.05 | current: domain-led | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.004 | 86 | julia/supporting-papers 0.039 ⚑; llm-foundations/supporting-papers 0.025 ⚑; computational-science/supporting-papers 0.020 ⚑ |
| AI/ML lecture | 0.05 | H1: subdomain-led | programming-languages / julia / supporting-papers | 0.039 | 1 | llm-foundations/supporting-papers 0.025 |
| AI/ML lecture | 0.05 | H2: joint domain | artificial-intelligence-machine-learning / llm-foundations / supporting-papers | 0.025 | 3 | julia/supporting-papers 0.039 ⚑; computational-science/supporting-papers 0.020; llm-training/supporting-papers 0.016 |
| OCR noise | 0.02 | current: domain-led | numerical-scientific-computing / computational-science / failure-mode-limitation | 0.001 | 65 | vulnerability-research/failure-mode-limitation 0.818 ⚑; ada/failure-mode-limitation 0.021 ⚑; exploit-development/failure-mode-limitation 0.015 ⚑ |
| OCR noise | 0.02 | H1: subdomain-led | security-privacy / vulnerability-research / failure-mode-limitation | 0.818 | 0 | — |
| OCR noise | 0.02 | H2: joint domain | security-privacy / vulnerability-research / failure-mode-limitation | 0.818 | 0 | — |
| OCR noise | 0.05 | current: domain-led | numerical-scientific-computing / computational-science / failure-mode-limitation | 0.004 | 97 | vulnerability-research/failure-mode-limitation 0.071 ⚑; ada/failure-mode-limitation 0.016 ⚑; exploit-development/failure-mode-limitation 0.014 ⚑ |
| OCR noise | 0.05 | H1: subdomain-led | security-privacy / vulnerability-research / failure-mode-limitation | 0.071 | 0 | — |
| OCR noise | 0.05 | H2: joint domain | security-privacy / vulnerability-research / failure-mode-limitation | 0.071 | 0 | — |

### Options A/B/C on the real chapters (current domain-led rule)

### code-heavy book chapter — 'Section 33'

`Apache Iceberg - The Definitive Guide (2).json` · 6,803 chars · pieces [1906] · code-line ratio 0.55

- Raw cosine, piece 1 — domains 0.517 … 0.085 (1st–5th gap 0.226); top: data-engineering-databases 0.517, performance-engineering 0.426, artificial-intelligence-machine-learning 0.309
- Raw cosine, piece 1 — subdomains top: sharding-partitioning 0.521, transaction-processing-oltp-olap 0.478, batch-processing 0.476, datalog 0.466; KFs: implementation-ref-spec 0.189, supporting-papers 0.129, failure-mode-limitation 0.114, role-definition 0.047

| T | Option | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |
|---|---|---|---|---|---|
| 0.01 | A pure | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.969 | 0 | — |
| 0.01 | B old components | data-engineering-databases / sharding-partitioning / unassigned | — | 0 | — |
| 0.01 | C fold | data-engineering-databases / sharding-partitioning / unassigned | — | 0 | — |
| 0.02 | A pure | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.704 | 0 | — |
| 0.02 | B old components | data-engineering-databases / sharding-partitioning / unassigned | — | 0 | — |
| 0.02 | C fold | data-engineering-databases / sharding-partitioning / unassigned | — | 0 | — |
| | *pooled shares at T=0.02* | D: data-engineering-databases 0.989, performance-engineering 0.011 | S: sharding-partitioning 0.755, transaction-processing-oltp-olap 0.087 | K: implementation-ref-spec 0.933, supporting-papers 0.045 | |
| 0.05 | A pure | data-engineering-databases / sharding-partitioning / implementation-ref-spec | 0.142 | 0 | — |
| 0.05 | B old components | data-engineering-databases / sharding-partitioning / unassigned | — | 0 | — |
| 0.05 | C fold | data-engineering-databases / sharding-partitioning / unassigned | — | 0 | — |

### all-code kernel note — 'Intro'

`hhp3_The xv6 Kernel (Previous Version)_xv6 Kernel-36 File-Related System Calls-Part 1.json` · 707 chars · pieces [169] · code-line ratio 0.0

- Raw cosine, piece 1 — domains 0.472 … 0.017 (1st–5th gap 0.218); top: kernel-systems-programming-operating-systems 0.472, networking-distributed-communication 0.300, hardware-description-digital-design 0.299
- Raw cosine, piece 1 — subdomains top: filesystems-implementation 0.447, kernel-development-linux 0.442, memory-management 0.442, operating-systems-concepts 0.389; KFs: implementation-ref-spec 0.176, role-definition 0.143, failure-mode-limitation 0.127, supporting-papers 0.011

| T | Option | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |
|---|---|---|---|---|---|
| 0.01 | A pure | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.427 | 2 | kernel-development-linux/implementation-ref-spec 0.268; memory-management/implementation-ref-spec 0.260 |
| 0.01 | B old components | kernel-systems-programming-operating-systems / filesystems-implementation / unassigned | — | 0 | — |
| 0.01 | C fold | kernel-systems-programming-operating-systems / filesystems-implementation / unassigned | — | 0 | — |
| 0.02 | A pure | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.285 | 2 | kernel-development-linux/implementation-ref-spec 0.226; memory-management/implementation-ref-spec 0.222 |
| 0.02 | B old components | kernel-systems-programming-operating-systems / filesystems-implementation / unassigned | — | 0 | — |
| 0.02 | C fold | kernel-systems-programming-operating-systems / filesystems-implementation / unassigned | — | 0 | — |
| | *pooled shares at T=0.02* | D: kernel-systems-programming-operating-systems 1.000, networking-distributed-communication 0.000 | S: filesystems-implementation 0.365, kernel-development-linux 0.289 | K: implementation-ref-spec 0.781, role-definition 0.149 | |
| 0.05 | A pure | kernel-systems-programming-operating-systems / filesystems-implementation / implementation-ref-spec | 0.074 | 2 | kernel-development-linux/implementation-ref-spec 0.067; memory-management/implementation-ref-spec 0.067 |
| 0.05 | B old components | kernel-systems-programming-operating-systems / filesystems-implementation / unassigned | — | 0 | — |
| 0.05 | C fold | kernel-systems-programming-operating-systems / filesystems-implementation / unassigned | — | 0 | — |

### long multi-piece chapter — 'Section 8'

`LNCS 2944 - Databases, Information Systems, and Peer-to-Peer Computing.json` · 40,958 chars · pieces [2048, 2048, 2048, 2048, 2048, 37] · code-line ratio 0.0

- Raw cosine, piece 1 — domains 0.389 … 0.082 (1st–5th gap 0.057); top: apis-integration-messaging 0.389, distributed-systems-engineering 0.378, networking-distributed-communication 0.374
- Raw cosine, piece 1 — subdomains top: gossip-protocols 0.464, message-queues 0.408, distributed-coordination 0.402, distributed-storage-systems 0.398; KFs: implementation-ref-spec 0.198, role-definition 0.162, supporting-papers 0.143, failure-mode-limitation 0.073
- Each piece's best subdomain: #1 gossip-protocols; #2 gossip-protocols; #3 graphql; #4 gossip-protocols; #5 vector-search; #6 web-standards

| T | Option | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |
|---|---|---|---|---|---|
| 0.01 | A pure | apis-integration-messaging / graphql / implementation-ref-spec | 0.115 | 3 | gossip-protocols/implementation-ref-spec 0.428 ⚑; gossip-protocols/supporting-papers 0.094; vector-search/implementation-ref-spec 0.087 |
| 0.01 | B old components | apis-integration-messaging / message-queues / implementation-ref-spec | 0.038 | 6 | gossip-protocols/implementation-ref-spec 0.428 ⚑; graphql/implementation-ref-spec 0.115 ⚑; gossip-protocols/supporting-papers 0.094 ⚑ |
| 0.01 | C fold | apis-integration-messaging / graphql / implementation-ref-spec | 0.115 | 3 | gossip-protocols/implementation-ref-spec 0.428 ⚑; gossip-protocols/supporting-papers 0.094; vector-search/implementation-ref-spec 0.087 |
| 0.02 | A pure | apis-integration-messaging / message-queues / implementation-ref-spec | 0.060 | 5 | gossip-protocols/implementation-ref-spec 0.257 ⚑; vector-search/implementation-ref-spec 0.064 ⚑; gossip-protocols/supporting-papers 0.058 |
| 0.02 | B old components | apis-integration-messaging / message-queues / implementation-ref-spec | 0.060 | 5 | gossip-protocols/implementation-ref-spec 0.257 ⚑; vector-search/implementation-ref-spec 0.064 ⚑; gossip-protocols/supporting-papers 0.058 |
| 0.02 | C fold | apis-integration-messaging / message-queues / implementation-ref-spec | 0.060 | 5 | gossip-protocols/implementation-ref-spec 0.257 ⚑; vector-search/implementation-ref-spec 0.064 ⚑; gossip-protocols/supporting-papers 0.058 |
| | *pooled shares at T=0.02* | D: apis-integration-messaging 0.279, distributed-systems-engineering 0.262 | S: gossip-protocols 0.344, vector-search 0.086 | K: implementation-ref-spec 0.749, supporting-papers 0.169 | |
| 0.05 | A pure | search-information-retrieval / vector-search / implementation-ref-spec | 0.017 | 8 | gossip-protocols/implementation-ref-spec 0.033 ⚑; message-queues/implementation-ref-spec 0.018 ⚑; graphql/implementation-ref-spec 0.015 |
| 0.05 | B old components | apis-integration-messaging / message-queues / implementation-ref-spec | 0.018 | 7 | gossip-protocols/implementation-ref-spec 0.033 ⚑; vector-search/implementation-ref-spec 0.017; graphql/implementation-ref-spec 0.015 |
| 0.05 | C fold | search-information-retrieval / vector-search / implementation-ref-spec | 0.017 | 8 | gossip-protocols/implementation-ref-spec 0.033 ⚑; message-queues/implementation-ref-spec 0.018 ⚑; graphql/implementation-ref-spec 0.015 |

### business + database interview — 'Why Route uses CockroachDB'

`CockroachDB_The Full Package_ How Route architects its all-in-one post-purchase platform.j` · 3,849 chars · pieces [889] · code-line ratio 0.0

- Raw cosine, piece 1 — domains 0.365 … 0.082 (1st–5th gap 0.065); top: software-architecture 0.365, engineering-management-organizational-design 0.364, distributed-systems-engineering 0.334
- Raw cosine, piece 1 — subdomains top: engineering-practices 0.367, engineering-metrics 0.357, devex 0.357, databases-newsql 0.348; KFs: implementation-ref-spec 0.215, failure-mode-limitation 0.179, supporting-papers 0.133, role-definition 0.040

| T | Option | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |
|---|---|---|---|---|---|
| 0.01 | A pure | software-architecture / microservices-architecture / implementation-ref-spec | 0.001 | 23 | engineering-practices/implementation-ref-spec 0.428 ⚑; engineering-metrics/implementation-ref-spec 0.155 ⚑; devex/implementation-ref-spec 0.152 ⚑ |
| 0.01 | B old components | software-architecture / microservices-architecture / implementation-ref-spec | 0.001 | 23 | engineering-practices/implementation-ref-spec 0.428 ⚑; engineering-metrics/implementation-ref-spec 0.155 ⚑; devex/implementation-ref-spec 0.152 ⚑ |
| 0.01 | C fold | software-architecture / microservices-architecture / implementation-ref-spec | 0.001 | 23 | engineering-practices/implementation-ref-spec 0.428 ⚑; engineering-metrics/implementation-ref-spec 0.155 ⚑; devex/implementation-ref-spec 0.152 ⚑ |
| 0.02 | A pure | software-architecture / microservices-architecture / implementation-ref-spec | 0.007 | 27 | engineering-practices/implementation-ref-spec 0.176 ⚑; engineering-metrics/implementation-ref-spec 0.106 ⚑; devex/implementation-ref-spec 0.105 ⚑ |
| 0.02 | B old components | software-architecture / microservices-architecture / implementation-ref-spec | 0.007 | 27 | engineering-practices/implementation-ref-spec 0.176 ⚑; engineering-metrics/implementation-ref-spec 0.106 ⚑; devex/implementation-ref-spec 0.105 ⚑ |
| 0.02 | C fold | software-architecture / microservices-architecture / implementation-ref-spec | 0.007 | 27 | engineering-practices/implementation-ref-spec 0.176 ⚑; engineering-metrics/implementation-ref-spec 0.106 ⚑; devex/implementation-ref-spec 0.105 ⚑ |
| | *pooled shares at T=0.02* | D: software-architecture 0.437, engineering-management-organizational-design 0.401 | S: engineering-practices 0.207, engineering-metrics 0.125 | K: implementation-ref-spec 0.848, failure-mode-limitation 0.138 | |
| 0.05 | A pure | software-architecture / microservices-architecture / implementation-ref-spec | 0.007 | 40 | engineering-practices/implementation-ref-spec 0.027 ⚑; engineering-metrics/implementation-ref-spec 0.022 ⚑; devex/implementation-ref-spec 0.022 ⚑ |
| 0.05 | B old components | software-architecture / microservices-architecture / implementation-ref-spec | 0.007 | 40 | engineering-practices/implementation-ref-spec 0.027 ⚑; engineering-metrics/implementation-ref-spec 0.022 ⚑; devex/implementation-ref-spec 0.022 ⚑ |
| 0.05 | C fold | software-architecture / microservices-architecture / implementation-ref-spec | 0.007 | 40 | engineering-practices/implementation-ref-spec 0.027 ⚑; engineering-metrics/implementation-ref-spec 0.022 ⚑; devex/implementation-ref-spec 0.022 ⚑ |

### video transcript — a GraphQL tutorial

`Net Ninja_GraphQL Tutorial_GraphQL Tutorial #6 - Setting up GraphQL.json` · 4,582 chars · pieces [1079] · code-line ratio 0.0

- Raw cosine, piece 1 — domains 0.452 … 0.040 (1st–5th gap 0.210); top: apis-integration-messaging 0.452, data-engineering-databases 0.276, developer-tooling-build-systems 0.267
- Raw cosine, piece 1 — subdomains top: graphql 0.619, graph-grounded-retrieval 0.353, databases-graph 0.350, lucene-elasticsearch-solr 0.339; KFs: implementation-ref-spec 0.268, role-definition 0.088, supporting-papers 0.043, failure-mode-limitation 0.010

| T | Option | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |
|---|---|---|---|---|---|
| 0.01 | A pure | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| 0.01 | B old components | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| 0.01 | C fold | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| 0.02 | A pure | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| 0.02 | B old components | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| 0.02 | C fold | apis-integration-messaging / graphql / implementation-ref-spec | 1.000 | 0 | — |
| | *pooled shares at T=0.02* | D: apis-integration-messaging 1.000, data-engineering-databases 0.000 | S: graphql 1.000, graph-grounded-retrieval 0.000 | K: implementation-ref-spec 1.000, role-definition 0.000 | |
| 0.05 | A pure | apis-integration-messaging / graphql / implementation-ref-spec | 0.883 | 0 | — |
| 0.05 | B old components | apis-integration-messaging / graphql / implementation-ref-spec | 0.883 | 0 | — |
| 0.05 | C fold | apis-integration-messaging / graphql / implementation-ref-spec | 0.883 | 0 | — |

### AI/ML lecture — a recorded talk

`Paul G. Allen School_Towards Principled Post-Training of Large Language Models—Banghua Zhu` · 815 chars · pieces [196] · code-line ratio 0.0

- Raw cosine, piece 1 — domains 0.253 … 0.013 (1st–5th gap 0.032); top: mathematical-theoretical-foundations 0.253, numerical-scientific-computing 0.252, computer-architecture 0.242
- Raw cosine, piece 1 — subdomains top: julia 0.298, llm-foundations 0.276, computational-science 0.265, llm-training 0.255; KFs: supporting-papers 0.220, role-definition 0.156, implementation-ref-spec 0.073, failure-mode-limitation 0.072

| T | Option | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |
|---|---|---|---|---|---|
| 0.01 | A pure | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.000 | 57 | julia/supporting-papers 0.852 ⚑; llm-foundations/supporting-papers 0.094 ⚑; computational-science/supporting-papers 0.029 ⚑ |
| 0.01 | B old components | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.000 | 57 | julia/supporting-papers 0.852 ⚑; llm-foundations/supporting-papers 0.094 ⚑; computational-science/supporting-papers 0.029 ⚑ |
| 0.01 | C fold | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.000 | 57 | julia/supporting-papers 0.852 ⚑; llm-foundations/supporting-papers 0.094 ⚑; computational-science/supporting-papers 0.029 ⚑ |
| 0.02 | A pure | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.001 | 62 | julia/supporting-papers 0.421 ⚑; llm-foundations/supporting-papers 0.140 ⚑; computational-science/supporting-papers 0.078 ⚑ |
| 0.02 | B old components | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.001 | 62 | julia/supporting-papers 0.421 ⚑; llm-foundations/supporting-papers 0.140 ⚑; computational-science/supporting-papers 0.078 ⚑ |
| 0.02 | C fold | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.001 | 62 | julia/supporting-papers 0.421 ⚑; llm-foundations/supporting-papers 0.140 ⚑; computational-science/supporting-papers 0.078 ⚑ |
| | *pooled shares at T=0.02* | D: mathematical-theoretical-foundations 0.310, numerical-scientific-computing 0.301 | S: julia 0.439, llm-foundations 0.146 | K: supporting-papers 0.959, role-definition 0.039 | |
| 0.05 | A pure | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.004 | 86 | julia/supporting-papers 0.039 ⚑; llm-foundations/supporting-papers 0.025 ⚑; computational-science/supporting-papers 0.020 ⚑ |
| 0.05 | B old components | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.004 | 86 | julia/supporting-papers 0.039 ⚑; llm-foundations/supporting-papers 0.025 ⚑; computational-science/supporting-papers 0.020 ⚑ |
| 0.05 | C fold | mathematical-theoretical-foundations / probability-statistics / supporting-papers | 0.004 | 86 | julia/supporting-papers 0.039 ⚑; llm-foundations/supporting-papers 0.025 ⚑; computational-science/supporting-papers 0.020 ⚑ |

### OCR noise — 'Ogaiow \nAponynmbt S\nDa'

`DTIC AD0737744 A Characterization of the Visibility Process and Its Effect on Search Polic` · 3,394 chars · pieces [985] · code-line ratio 0.0

- Raw cosine, piece 1 — domains 0.196 … -0.042 (1st–5th gap 0.064); top: numerical-scientific-computing 0.196, security-privacy 0.176, ux-design-hci 0.153
- Raw cosine, piece 1 — subdomains top: vulnerability-research 0.293, ada 0.220, exploit-development 0.214, trusted-execution-environments 0.212; KFs: failure-mode-limitation 0.176, supporting-papers 0.092, implementation-ref-spec 0.048, role-definition 0.010

| T | Option | Primary (domain / subdomain / KF) | Primary score | # secondaries | Top secondaries |
|---|---|---|---|---|---|
| 0.01 | A pure | numerical-scientific-computing / computational-science / failure-mode-limitation | 0.000 | 55 | vulnerability-research/failure-mode-limitation 0.998 ⚑; ada/failure-mode-limitation 0.001 ⚑; exploit-development/failure-mode-limitation 0.000 ⚑ |
| 0.01 | B old components | numerical-scientific-computing / computational-science / unassigned | — | 0 | — |
| 0.01 | C fold | numerical-scientific-computing / computational-science / unassigned | — | 0 | — |
| 0.02 | A pure | numerical-scientific-computing / computational-science / failure-mode-limitation | 0.001 | 65 | vulnerability-research/failure-mode-limitation 0.818 ⚑; ada/failure-mode-limitation 0.021 ⚑; exploit-development/failure-mode-limitation 0.015 ⚑ |
| 0.02 | B old components | numerical-scientific-computing / computational-science / unassigned | — | 0 | — |
| 0.02 | C fold | numerical-scientific-computing / computational-science / unassigned | — | 0 | — |
| | *pooled shares at T=0.02* | D: numerical-scientific-computing 0.591, security-privacy 0.216 | S: vulnerability-research 0.831, ada 0.021 | K: failure-mode-limitation 0.984, supporting-papers 0.014 | |
| 0.05 | A pure | numerical-scientific-computing / computational-science / failure-mode-limitation | 0.004 | 97 | vulnerability-research/failure-mode-limitation 0.071 ⚑; ada/failure-mode-limitation 0.016 ⚑; exploit-development/failure-mode-limitation 0.014 ⚑ |
| 0.05 | B old components | numerical-scientific-computing / computational-science / unassigned | — | 0 | — |
| 0.05 | C fold | numerical-scientific-computing / computational-science / unassigned | — | 0 | — |

## Part 4 — Same chapters, three embedding models (the two Nomic models the designs define, plus jina-v3)

The designs define two Nomic models: `nomic-embed-text-v1.5` (the original storage embedder — 768 dims, 8,192 tokens, `search_query:`/`search_document:` prefixes, Apache 2.0; replaced on reasons HTC v1.3 later recorded as false) and `nomic-embed-text-v2-moe` (its replacement — 768 dims, 512 tokens). v1.5 is not a COS profile; it was loaded from its cached snapshot for this comparison. Pieces: jina-v3 2,048 (memory cap), nomic-v2 480 (its limit), nomic-v1.5 8,160 (its natural size). T = 0.02.

| Model | Load + 2,048-token piece | 8,192-token piece | Speed (7 chapters) |
|---|---|---|---|
| jina-v3 | 5.0–5.4 GB peak | extrapolated ~13 GB more — not run (would exhaust this 17 GB host) | 1–37 s per chapter |
| nomic-v2 | 4.6 GB peak (480-token pieces) | cannot — 512-token limit | 0.2–4 s |
| nomic-v1.5 | 1.6 GB | **1.9 GB, 7.3 s** | 0.1–15 s |

| Chapter | Model | Section closeness: 1st, 2nd (gap) | Top 3 shelves (their section) | Sections of top 5 shelves | Current rule: primary · # extra copies | Shelf-first: primary · # extra copies | Best KF closeness |
|---|---|---|---|---|---|---|---|
| code-heavy book chapter | jina-v3 | data-engineering-databases 0.517, performance-engineering 0.426 (0.091) | sharding-partitioning 0.521 (data-engineering-databases), transaction-processing-oltp-olap 0.478 (data-engineering-databases), batch-processing 0.476 (data-engineering-databases) | 3 section(s) | data-engineering-databases/sharding-partitioning · 0 | data-engineering-databases/sharding-partitioning · 0 | 0.189 |
| code-heavy book chapter | nomic-v2 | data-engineering-databases 0.440, algorithms-data-structures 0.434 (0.006) | sharding-partitioning 0.495 (data-engineering-databases), indexing 0.459 (data-engineering-databases), event-sourcing 0.458 (distributed-systems-engineering) | 4 section(s) | algorithms-data-structures/graph-algorithms · 28 | data-engineering-databases/sharding-partitioning · 0 | 0.416 |
| code-heavy book chapter | nomic-v1.5 | data-engineering-databases 0.660, algorithms-data-structures 0.620 (0.041) | query-optimization 0.682 (data-engineering-databases), sharding-partitioning 0.662 (data-engineering-databases), databases-relational 0.660 (data-engineering-databases) | 2 section(s) | data-engineering-databases/query-optimization · 0 | data-engineering-databases/query-optimization · 0 | 0.556 |
| all-code kernel note | jina-v3 | kernel-sys 0.472, networking-distributed-communication 0.300 (0.171) | filesystems-implementation 0.447 (kernel-sys), kernel-development-linux 0.442 (kernel-sys), memory-management 0.442 (kernel-sys) | 1 section(s) | kernel-sys/filesystems-implementation · 2 | kernel-sys/filesystems-implementation · 2 | 0.176 |
| all-code kernel note | nomic-v2 | kernel-sys 0.529, developer-tooling-build-systems 0.460 (0.069) | kernel-development-linux 0.530 (kernel-sys), memory-management 0.528 (kernel-sys), go 0.513 (programming-languages) | 3 section(s) | kernel-sys/kernel-development-linux · 1 | kernel-sys/kernel-development-linux · 1 | 0.480 |
| all-code kernel note | nomic-v1.5 | kernel-sys 0.715, embedded-iot-real-time-systems 0.664 (0.052) | filesystems-implementation 0.696 (kernel-sys), kernel-development-linux 0.686 (kernel-sys), memory-management 0.682 (kernel-sys) | 2 section(s) | kernel-sys/filesystems-implementation · 2 | kernel-sys/filesystems-implementation · 2 | 0.594 |
| long multi-piece chapter | jina-v3 | distributed-systems-engineering 0.404, search-information-retrieval 0.398 (0.006) | gossip-protocols 0.432 (distributed-systems-engineering), message-queues 0.411 (apis-integration-messaging), graphql 0.402 (apis-integration-messaging) | 3 section(s) | apis-integration-messaging/message-queues · 5 | distributed-systems-engineering/gossip-protocols · 0 | 0.251 |
| long multi-piece chapter | nomic-v2 | standards-protocols 0.421, networking-distributed-communication 0.420 (0.001) | enterprise-integration-patterns 0.476 (apis-integration-messaging), gossip-protocols 0.462 (distributed-systems-engineering), graphql 0.461 (apis-integration-messaging) | 3 section(s) | networking-distributed-communication/network-virtualization · 2 | distributed-systems-engineering/gossip-protocols · 2 | 0.405 |
| long multi-piece chapter | nomic-v1.5 | ai-ml 0.582, search-information-retrieval 0.568 (0.014) | ml-platform 0.594 (ai-ml), ranking-relevance 0.580 (search-information-retrieval), databases-graph 0.567 (data-engineering-databases) | 5 section(s) | ai-ml/ml-platform · 0 | ai-ml/ml-platform · 0 | 0.526 |
| business + database interview | jina-v3 | software-architecture 0.365, eng-management 0.364 (0.002) | engineering-practices 0.367 (software-engineering-design), engineering-metrics 0.357 (eng-management), devex 0.357 (developer-tooling-build-systems) | 4 section(s) | software-architecture/microservices-architecture · 27 | software-engineering-design/engineering-practices · 1 | 0.215 |
| business + database interview | nomic-v2 | distributed-systems-engineering 0.464, data-engineering-databases 0.452 (0.012) | databases-newsql 0.533 (data-engineering-databases), query-optimization 0.518 (data-engineering-databases), databases-relational 0.504 (data-engineering-databases) | 2 section(s) | distributed-systems-engineering/cqrs · 14 | data-engineering-databases/databases-newsql · 0 | 0.380 |
| business + database interview | nomic-v1.5 | distributed-systems-engineering 0.653, data-engineering-databases 0.650 (0.003) | databases-newsql 0.697 (data-engineering-databases), query-optimization 0.671 (data-engineering-databases), engineering-management 0.670 (eng-management) | 2 section(s) | distributed-systems-engineering/distributed-scheduling · 42 | data-engineering-databases/databases-newsql · 0 | 0.596 |
| video transcript | jina-v3 | apis-integration-messaging 0.452, data-engineering-databases 0.276 (0.176) | graphql 0.619 (apis-integration-messaging), graph-grounded-retrieval 0.353 (developer-tooling-build-systems), databases-graph 0.350 (data-engineering-databases) | 5 section(s) | apis-integration-messaging/graphql · 0 | apis-integration-messaging/graphql · 0 | 0.268 |
| video transcript | nomic-v2 | apis-integration-messaging 0.449, developer-tooling-build-systems 0.420 (0.029) | graphql 0.581 (apis-integration-messaging), intermediate-representations 0.499 (compilers-language-implementation), graph-algorithms 0.496 (algorithms-data-structures) | 5 section(s) | apis-integration-messaging/graphql · 0 | apis-integration-messaging/graphql · 0 | 0.433 |
| video transcript | nomic-v1.5 | apis-integration-messaging 0.657, algorithms-data-structures 0.580 (0.078) | graphql 0.700 (apis-integration-messaging), databases-graph 0.642 (data-engineering-databases), graph-algorithms 0.627 (algorithms-data-structures) | 5 section(s) | apis-integration-messaging/graphql · 0 | apis-integration-messaging/graphql · 0 | 0.566 |
| AI/ML lecture | jina-v3 | mathematical-theoretical-foundations 0.253, numerical-scientific-computing 0.252 (0.001) | julia 0.298 (programming-languages), llm-foundations 0.276 (ai-ml), computational-science 0.265 (numerical-scientific-computing) | 3 section(s) | mathematical-theoretical-foundations/probability-statistics · 62 | programming-languages/julia · 0 | 0.220 |
| AI/ML lecture | nomic-v2 | ai-ml 0.395, mathematical-theoretical-foundations 0.389 (0.006) | reasoning-models 0.465 (ai-ml), llm-prompting 0.460 (ai-ml), llm-architecture 0.453 (ai-ml) | 1 section(s) | ai-ml/reasoning-models · 2 | ai-ml/reasoning-models · 2 | 0.328 |
| AI/ML lecture | nomic-v1.5 | mathematical-theoretical-foundations 0.680, ai-ml 0.659 (0.021) | llm-foundations 0.684 (ai-ml), llm-architecture 0.682 (ai-ml), number-theory 0.666 (mathematical-theoretical-foundations) | 2 section(s) | mathematical-theoretical-foundations/number-theory · 9 | ai-ml/llm-foundations · 1 | 0.638 |
| OCR noise | jina-v3 | numerical-scientific-computing 0.196, security-privacy 0.176 (0.020) | vulnerability-research 0.293 (security-privacy), ada 0.220 (programming-languages), exploit-development 0.214 (security-privacy) | 3 section(s) | numerical-scientific-computing/computational-science · 65 | security-privacy/vulnerability-research · 0 | 0.176 |
| OCR noise | nomic-v2 | security-privacy 0.336, testing-quality-assurance 0.324 (0.012) | mutation-testing 0.394 (testing-quality-assurance), llm-alignment-safety 0.382 (ai-ml), penetration-testing 0.375 (security-privacy) | 4 section(s) | security-privacy/supply-chain-security · 7 | testing-quality-assurance/mutation-testing · 0 | 0.335 |
| OCR noise | nomic-v1.5 | ai-ml 0.634, search-information-retrieval 0.633 (0.001) | ai-ml-security 0.689 (security-privacy), penetration-testing 0.675 (security-privacy), threat-modeling 0.671 (security-privacy) | 3 section(s) | ai-ml/text-classification · 19 | security-privacy/ai-ml-security · 1 | 0.599 |

**Reading it.** (1) The section-first "dozens of extra copies" failure appears with all three models (jina-v3 27/62/65, nomic-v2 28/14/7, nomic-v1.5 42/19/9) and shelf-first removes it under all three (≤ 3) — it is a design issue, not a model issue. (2) Shelf quality on 7 chapters is mixed: nomic-v2 and v1.5 put the CockroachDB interview on `databases-newsql` and the LLM lecture on LLM shelves where jina-v3 did not; jina-v3 separates sections most decisively on clean technical text; v1.5 put the long databases/P2P paper on `ml-platform`. (3) Noise: jina-v3 keeps OCR noise far below real chapters (0.29 vs 0.43–0.62); nomic-v1.5 scores everything 0.6–0.7, noise included, so a raw-similarity noise floor would not work for it. (4) Closeness scales differ per model (KF 0.18–0.27 jina-v3, 0.33–0.48 nomic-v2, 0.56–0.64 nomic-v1.5) — every cut-off is per profile. Seven chapters cannot choose a model; the 1,049 labeled held-out chapters can.

## What needs deciding

1. **Primary rule (F1/F2):** keep domain-led, switch to subdomain-led, or joint. This is now the first-order decision; A/B/C only matter on top of it.
2. **Q1 A/B/C** — on top of the rule chosen in 1 (H3, H5–H7 show where they differ), including whether signals may flip the primary KF (H7).
3. **Q2 R1/R2/R3 and weighting** (M2 is where they disagree; M3 shows the SCE-11.03.04 ratio conflict).
4. **Q3 O1/O2.**
5. **Calibration scope (F3/F5/F6/F7):** temperature, ratio, KF floor, a raw-similarity noise floor, and a CPU-safe piece size — all in the OQ#24 run.
