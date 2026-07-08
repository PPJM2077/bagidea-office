# Budget Plan — AI Quant Office

> **Owner:** CFO · **Last Updated:** 2026-07-07  
> **Scope:** All recurring costs for the AI Office + Quant Platform across phases.

---

## Executive Summary

| Category | Current (Phase 0-1) | Phase 2-3 (Research) | Phase 4+ (Live Trading) |
|---|---|---|---|
| **API / LLM** | $50–80/mo | $120–250/mo | $300–600/mo |
| **VPS / Cloud** | $25–35/mo | $50–100/mo | $150–400/mo |
| **GPU Compute** | $0–40/mo | $80–200/mo | $300–800/mo |
| **Other Services** | $5–10/mo | $15–30/mo | $50–100/mo |
| **Total Est. Monthly** | **$80–165** | **$265–580** | **$800–1,900** |

---

## 1. API / LLM Costs

### Current Setup (Phase 0-1)

The office runs on `cp-opencode-go/deepseek-v4-flash` — DeepSeek models routed through an OpenCode gateway.

| Item | Unit Cost | Est. Monthly Usage | Monthly Cost |
|---|---|---|---|
| OpenCode / cp-opencode-go subscription | $0 (self-hosted) or $20/mo (hosted Pro) | 1 subscription | **$0–20** |
| DeepSeek V4 Flash — input tokens | ~$0.15/M tokens | ~3–5M input/mo (agent threads, context load) | **$0.45–0.75** |
| DeepSeek V4 Flash — output tokens | ~$0.50/M tokens | ~1–2M output/mo (generation, coding, analysis) | **$0.50–1.00** |
| DeepSeek V4 Pro (occasional reasoning) | ~$1.50/M in / ~$6.00/M out | ~500K input + 200K output | **$1.95** |
| Gemini Flash (vision/OCR fallback) | ~$0.075/M in / ~$0.30/M out | ~200K/mo (image descriptions) | **~$0.05** |
| **Subtotal** | | | **~$50–80** |

> **Assumption:** Office processes ~100–200 agent turns/day, averaging 30K input + 10K output tokens each. 20 working days/mo. Buffer includes sub-agent parallel splits and occasional long-context research threads.

### Projected Growth (Phase 2-3: Research)

| New Load | Est. Increase | Run Rate |
|---|---|---|
| 12-20 agents daily (quant research, backtest, market) | 3–5× current | $150–250/mo |
| DeepSeek V4 Pro/Claude Sonnet for strategy reasoning | $ ad-hoc | $30–80/mo |
| Local inference via vLLM (offloaded from API) | — | — |
| **Subtotal** | | **$120–250/mo** |

### Phase 4+ (Live Trading)

| New Load | Est. Increase | Run Rate |
|---|---|---|
| 24/7 monitoring agents (market, risk, portfolio) | 2–3× Research phase | $250–500/mo |
| Real-time news/sentiment + LLM calls | heavy throughput | $50–100/mo |
| **Subtotal** | | **$300–600/mo** |

### Optimization Levers

| Lever | Est. Savings | Effort |
|---|---|---|
| Route workers to DeepSeek/V4 Flash (already done ✓) | 50–70% vs Claude | — |
| Enable prompt caching (OpenCode cache) | 20–40% on input tokens | Config change |
| Offload high-volume inference to local vLLM | 80–100% on those calls | Setup vLLM on GPU |
| Increase auto-compact threshold for agents | 10–15% | Tweak `contextBudget` |

---

## 2. VPS / Cloud Infrastructure

### Hetzner Cloud — Current (Dev / Staging)

| Resource | Spec | Monthly (€) | Monthly ($) |
|---|---|---|---|
| **CX32** (4 vCPU, 8 GB RAM) | FastAPI, Redis, NATS, Qdrant (dev) | €7.99 | ~$8.50 |
| **Storage Volume** (200 GB HDD) | MinIO, DuckDB data, logs | €8.90 | ~$9.50 |
| **Backup snapshot** | Weekly system snapshot | €2.00 | ~$2.10 |
| **Subtotal** | | **€18.89** | **~$20** |

**Services hosted on this node:**
- FastAPI backend (AI gateway + API server)
- PostgreSQL 16 + pgvector (relational + embeddings)
- Redis 7.2 (cache + pub-sub)
- NATS 2.10 (event bus with JetStream)
- Qdrant 1.10 (vector store, dev mode)
- MinIO (S3-compatible object storage)
- Monitoring: Prometheus + Grafana (light)

### Phase 2-3: Research / Staging Cluster

| Resource | Spec | Monthly (€) | Monthly ($) |
|---|---|---|---|
| **CX42** (8 vCPU, 16 GB RAM) × 2 | App + DB/queue cluster | €31.98 | ~$34 |
| **Storage Volume** (500 GB SSD) | Feature store, backtest data | €21.90 | ~$23 |
| **Subtotal** | | **€53.88** | **~$57** |

### Phase 4+: Production Cluster

| Resource | Spec | Monthly (€) | Monthly ($) |
|---|---|---|---|
| **AX102** (16 vCPU, 32 GB, NVMe) | Primary application + AI gateway | €59.00 | ~$63 |
| **AX102** (16 vCPU, 32 GB, NVMe) | Database + Qdrant cluster (3-node) | €59.00 | ~$63 |
| **CX42** (8 vCPU, 16 GB) × 2 | NATS + Redis + MinIO replicas | €31.98 | ~$34 |
| **Storage Volume** (1 TB SSD) | Data lake, Parquet, backups | €43.90 | ~$47 |
| **Subtotal** | | **€193.88** | **~$207** |

### Alternatives

| Provider | Equivalent Spec | Est. Monthly | Notes |
|---|---|---|---|
| **Hetzner** (our pick ✓) | CX42 (8vCPU/16GB) | **~$17** | Best value EU |
| **AWS EC2** (t3.large) | 2 vCPU, 8 GB | ~$70 + data | 4–5× Hetzner |
| **GCP** (e2-standard-4) | 4 vCPU, 16 GB | ~$60 + data | 3–4× Hetzner |
| **DigitalOcean** (4 vCPU, 8 GB) | 4 vCPU, 8 GB | ~$48 | 2–3× Hetzner |

---

## 3. GPU Compute

### Current — Minimal / On-Demand

RunPod serverless (pay-per-second, no reserved instance):

| GPU | Use Case | Est. Hours/Mo | Rate/hr | Monthly |
|---|---|---|---|---|
| N/A (Phase 0) | No GPU workload yet | 0 | — | **$0** |

*If experimenting with local inference:*
| A100 80G (RunPod) | vLLM evaluation, embedding test | 10–15 hr | ~$2.00/hr | **$20–30** |
| **Subtotal** | | | | **$0–30** |

### Phase 2-3: Research GPU

| GPU | Use Case | Est. Hours/Mo | Rate/hr | Monthly |
|---|---|---|---|---|
| **H100 80G** (RunPod) | vLLM inference serving (local LLM for agents) | 60 hr | ~$3.19/hr | ~$191 |
| **A100 80G** (RunPod spot) | Batch backtest compute, feature engineering | 40 hr | ~$1.50/hr (spot) | ~$60 |
| **A100 80G** (RunPod) | Model fine-tuning, embedding generation | 10 hr | ~$2.00/hr | ~$20 |
| **Subtotal** | | | | **~$80–200** |

> **Strategy:** Use RunPod serverless for inference (auto-scales to zero when idle). Use Community Cloud (spot) for batch jobs at 25–40% discount. Reserve Secure Cloud only for latency-sensitive live inference.

### Phase 4+: Production GPU

| GPU | Use Case | Est. Hours/Mo | Rate/hr | Monthly |
|---|---|---|---|---|
| **H100 80G** (RunPod reserved) | Production inference (24/7 agent brains) | 720 hr | ~$2.50/hr (reserved) | ~$1,800 |
| **A100 80G** (RunPod spot) | Research + backtest + retraining | 100 hr | ~$1.50/hr | ~$150 |
| **H100 spot** | Batch + fine-tuning | 60 hr | ~$2.00/hr | ~$120 |
| **Subtotal** | | | | **~$300–800** |

### GPU Cost Reduction

| Method | Est. Savings | When |
|---|---|---|
| Offload light inference to CPU (Ollama, quantized) | 60–80% | Always |
| Use RunPod spot endpoints for batch | 25–40% | Phase 2+ |
| Cache LLM responses at gateway (semantic cache) | 20–40% token reduction | Always |
| Batch backtest on Vast.ai spot | 30–50% vs RunPod | Phase 3+ |
| Self-host quantized local models on Hetzner (no GPU) | 100% of GPU cost for light tasks | Phase 2+ |

---

## 4. Other Services

| Service | Plan | Monthly Cost |
|---|---|---|
| **Cloudflare** (CDN + WAF + DNS) | Free tier | $0 |
| **GitHub** (source + CI/CD) | Free (2000 min/mo) | $0 |
| **Domain** (ai-quant-office.com or similar) | $10/yr → ~$0.83/mo | ~$1 |
| **Cloudflare R2** (backup object storage, 10 GB) | Free tier (10 GB egress) | $0 |
| **Sentry** (error monitoring) | Free tier (5K events/mo) | $0 |
| **PostHog** (self-hosted analytics) | On Hetzner VPS | $0 |
| **Subtotal** | | **~$5–10** |

### Phase 3+ Add-ons

| Service | Monthly Add |
|---|---|
| **Cloudflare Pro** (WAF rules, DDOS, performance) | +$20 |
| **Sentry** (Team plan, 50K events) | +$26 |
| **GitHub Team** (required for private repos > 5 users) | +$44 (4 seats × $11) |
| **Subtotal Phase 4** | **~$50–100** |

---

## 5. Cumulative Cost Projection (12 Months)

Scenarios assuming Phase 0-1 for months 1-2, Phase 2-3 for months 3-7, Phase 4+ from month 8:

| Month | Phase | Est. Monthly Burn | Cumulative (YTD) |
|---|---|---|---|
| Jul 2026 | Phase 0-1 | $100 | $100 |
| Aug 2026 | Phase 0-1 | $100 | $200 |
| Sep 2026 | Phase 2 (Research start) | $300 | $500 |
| Oct 2026 | Phase 2 (Research ramp) | $400 | $900 |
| Nov 2026 | Phase 3 (Quant platform) | $500 | $1,400 |
| Dec 2026 | Phase 3 (Backtest + Paper) | $550 | $1,950 |
| Jan 2027 | Phase 3 → 4 transition | $600 | $2,550 |
| Feb 2027 | Phase 4 (Paper → Canary) | $800 | $3,350 |
| Mar 2027 | Phase 4 (Canary live) | $1,200 | $4,550 |
| Apr 2027 | Phase 4 (Production) | $1,500 | $6,050 |
| May 2027 | Phase 4 (Scale) | $1,800 | $7,850 |
| Jun 2027 | Phase 4 (Optimize) | $1,500 | $9,350 |

> **12-month total estimate:** **$5,500–9,500** depending on GPU utilization and agent activity density.

---

## 6. Cost Reduction Recommendations

### Immediate (do now — $0 effort)

| Action | Est. Monthly Saving |
|---|---|
| ✅ **Already done** — all agents on DeepSeek Flash (not Claude) | **$200–500 saved vs Claude** |
| Turn off Director heartbeat (already minimal) | Minor |
| Verify Delegated Work = OFF (quality double-check off) | 5–10% |
| Set Social interval to 120 min or OFF | ~$5–10/mo |

### Short term (Phase 1-2)

| Action | Est. Saving | Cost to Implement |
|---|---|---|
| Enable OpenCode semantic caching | ~$10–20/mo | Config change |
| Deploy local vLLM on Hetzner + RunPod for workers | ~$30–60/mo | ~4–8 hr setup |
| Monitor per-agent spend with `bagidea stats` | Indirect (find waste) | $0 |

### Medium term (Phase 3+)

| Action | Est. Saving | Cost to Implement |
|---|---|---|
| Batch GPU on Vast.ai spot (30-50% cheaper) | ~$50–100/mo | Script adaptation |
| Quantize models (FP16 → INT8) for inference | ~30% GPU hours | 1–2 day engineering |
| Self-host embedding/reranking on CPU (BGE) | ~$20–40/mo | Docker + model download |
| Route high-volume news/sentiment to local models | ~$50–100/mo | 2–3 day integration |
| Long-term reserved RunPod instances (commit discount) | 20–30% GPU | Commitment |

---

## 7. Budget Cap Recommendations

| Phase | Suggested Monthly Cap | Triggers for Review |
|---|---|---|
| Phase 0-1 (now) | **$200** | Monitor DeepSeek token burn weekly |
| Phase 2-3 (Research) | **$600** | Alert if GPU > $250/mo |
| Phase 4 (Live) | **$2,000** | Full cost review before canary launch |
| **Emergency kill** | If any single week exceeds 2× monthly cap | Auto-review + CRO/CEO notification |

---

## 8. Tracking & Monitoring

- **Per-agent spend:** `bagidea stats` (built-in, shows last 7 days)
- **LLM cost tracking:** OpenCode dashboard + custom LiteLLM logging
- **Infra cost:** Hetzner Cloud invoice (monthly, ~€20–200)
- **GPU cost:** RunPod usage dashboard (realtime per-second billing)
- **Weekly CFO check:** Review burn rate, compare to cap, flag anomalies

---

*Budget approved by CFO. Track every dollar.*
