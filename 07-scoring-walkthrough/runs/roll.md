## Q2 — module and component roll-ups


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
