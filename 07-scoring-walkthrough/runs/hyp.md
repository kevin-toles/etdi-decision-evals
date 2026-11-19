## Q1 — primary KF/subdomain rule


### H1 · Single-topic chapter (Raft explained)

- Domain shares: distributed-systems-engineering 0.810, storage-systems 0.070, software-architecture 0.040
- Subdomain shares (whole taxonomy): consensus-algorithms 0.620, leader-election 0.080, replication 0.060, discrete-mathematics 0.020, linear-algebra 0.020
- KF raw similarity: implementation-ref-spec 0.470, failure-mode-limitation 0.417, role-definition 0.413, supporting-papers 0.403 → shares at T=0.02: implementation-ref-spec 0.860, failure-mode-limitation 0.060, role-definition 0.050, supporting-papers 0.030

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.533 | none |
| B old components | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.533 | none |
| C fold | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.533 | none |

### H2 · Same-domain secondaries (consensus with a failure-handling section)

- Domain shares: distributed-systems-engineering 0.700, storage-systems 0.150, software-architecture 0.080
- Subdomain shares (whole taxonomy): consensus-algorithms 0.400, leader-election 0.300, replication 0.100, discrete-mathematics 0.017, linear-algebra 0.017
- KF raw similarity: implementation-ref-spec 0.460, failure-mode-limitation 0.454, role-definition 0.402, supporting-papers 0.394 → shares at T=0.02: implementation-ref-spec 0.550, failure-mode-limitation 0.400, role-definition 0.030, supporting-papers 0.020

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.220 | (distributed-systems-engineering / leader-election / implementation-ref-spec) 0.165; (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.160 |
| B old components | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.220 | (distributed-systems-engineering / leader-election / implementation-ref-spec) 0.165; (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.160 |
| C fold | distributed-systems-engineering / consensus-algorithms / implementation-ref-spec | 0.220 | (distributed-systems-engineering / leader-election / implementation-ref-spec) 0.165; (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.160 |

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

### H4 · Table-of-contents fragment (nothing matches well: best KF cosine 0.15)

- Domain shares: distributed-systems-engineering 0.400, software-architecture 0.300, storage-systems 0.200
- Subdomain shares (whole taxonomy): consensus-algorithms 0.300, replication 0.200, leader-election 0.150, discrete-mathematics 0.029, linear-algebra 0.029
- KF raw similarity: role-definition 0.150, implementation-ref-spec 0.149, failure-mode-limitation 0.145, supporting-papers 0.140 → shares at T=0.02: role-definition 0.300, implementation-ref-spec 0.280, failure-mode-limitation 0.240, supporting-papers 0.180

| Option | Primary (domain / subdomain / KF) | Primary score | Secondaries (score) |
|---|---|---|---|
| A pure | distributed-systems-engineering / consensus-algorithms / role-definition | 0.090 | (distributed-systems-engineering / consensus-algorithms / implementation-ref-spec) 0.084; (distributed-systems-engineering / consensus-algorithms / failure-mode-limitation) 0.072; (distributed-systems-engineering / replication / role-definition) 0.060; (distributed-systems-engineering / replication / implementation-ref-spec) 0.056; (distributed-systems-engineering / consensus-algorithms / supporting-papers) 0.054 |
| B old components | distributed-systems-engineering / consensus-algorithms / unassigned | — | none |
| C fold | distributed-systems-engineering / consensus-algorithms / unassigned | — | none |

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

## Pooling — a long two-topic chapter (two pieces)

- Piece 1 (8,160 tokens): consensus-algorithms 0.600, storage-engines 0.050
- Piece 2 (3,900 tokens): storage-engines 0.650, consensus-algorithms 0.040
- Pooled (token-weighted): consensus-algorithms 0.419, storage-engines 0.244, discrete-mathematics 0.028
- ratio 0.6: primary consensus-algorithms (0.335); secondaries none
- ratio 0.45: primary consensus-algorithms (0.335); secondaries (data-engineering-databases / storage-engines / implementation-ref-spec) 0.195
