# AI Quant Office — Technology Decision Log

> **สถานะ:** FINAL — อนุมัติโดย Founder + Research Director + Strategy AI
> **วันที่:** 2026-07-07
> **เวอร์ชัน:** v1.0

---

## Version Log

| Version | Date | Author | Change |
|---------|------|--------|--------|
| v1.0 | 2026-07-07 | Strategy AI + Research Director | Initial — all technology categories finalized |

---

## Decision Records

### D1: AI/LLM Gateway

| Field | Decision |
|-------|----------|
| **Primary** | **OpenRouter** |
| **Fallback** | Direct API per provider |
| **Phase** | Phase 0 (MVP) |
| **Rationale** | Single API for all major models, built-in fallback routing, cost control dashboard. Eliminates vendor lock-in. Direct API fallback when OpenRouter has sustained outage (>5min). |
| **Rejected** | Custom router (too much build effort for Phase 0), AWS Bedrock / GCP Vertex (vendor lock-in, higher cost) |
| **Risk** | Additional latency hop (~50-150ms). Mitigation: Direct API fallback for latency-sensitive paths (execution). |

### D2: LLM Models — Reasoning & Strategy

| Field | Decision |
|-------|----------|
| **Primary** | **Claude Sonnet 5** (reasoning, strategy, risk) |
| **Fallback** | Claude Opus 4.8 → GPT-5.5 Pro |
| **Phase** | Phase 0 |
| **Rationale** | Best reasoning quality + largest context window for strategy analysis. Opus 4.8 for hardest problems (constitutional review, crisis). |
| **Rejected** | GPT-5.5 Turbo (weaker reasoning), Gemini 3.5 Pro (context window不夠大) |

### D3: LLM Models — Fast / Market Analysis

| Field | Decision |
|-------|----------|
| **Primary** | **Gemini 3.5 Flash** |
| **Fallback** | DeepSeek V4 Flash |
| **Phase** | Phase 0 |
| **Rationale** | Speed + cost + accuracy sweet spot for market scanning, news sentiment, real-time analysis. DeepSeek V4 Flash is backup at similar cost. |
| **Rejected** | Claude Haiku 4.5 (slower at high throughput) |

### D4: LLM Models — Coding

| Field | Decision |
|-------|----------|
| **Primary** | **DeepSeek V4 Pro** / **Claude Sonnet 5** |
| **Fallback** | GPT-5.5 Codex |
| **Phase** | Phase 0 |
| **Rationale** | DeepSeek V4 Pro excels at code generation throughput; Claude Sonnet 5 for complex architectural code. Dual primary by task type. |
| **Rejected** | Single model (each has strengths for different coding tasks) |

### D5: LLM Models — Local Inference

| Field | Decision |
|-------|----------|
| **Primary** | **Qwen 3.5** via **vLLM** |
| **Fallback** | DeepSeek V3.2 / Ollama |
| **Phase** | Phase 1+ |
| **Rationale** | Zero API cost for private data. vLLM for production throughput. Ollama for dev/testing simplicity. Used for: local RAG, internal analysis, privacy-sensitive data. |
| **Rejected** | Cloud-only (privacy risk + cost at scale) |

### D6: Vision / Multi-modal

| Field | Decision |
|-------|----------|
| **Primary** | **Gemini 3.5 Flash** |
| **Fallback** | GPT-5.5 Image |
| **Phase** | Phase 0 |
| **Rationale** | Best vision capabilities in the market at competitive price. Used for: chart pattern recognition, document OCR, screenshot analysis. |
| **Rejected** | Claude Vision (good but lower throughput at scale) |

### D7: Embedding Models

| Field | Decision |
|-------|----------|
| **Primary** | **Voyage 3 (cloud)** + **BGE-M3 (local)** |
| **Fallback** | text-embedding-3-large |
| **Phase** | Phase 0 |
| **Rationale** | Hybrid: Voyage for precision on knowledge base RAG, BGE for local/offline embedding. Dual strategy avoids single point of failure. |
| **Rejected** | OpenAI-only (cost at scale), E5-Mistral-7b (too heavy for everyday use) |

### D8: Reranking

| Field | Decision |
|-------|----------|
| **Primary** | **Cohere Rerank v3** (cloud) / **BGE Reranker v2** (local) |
| **Fallback** | Voyage Rerank |
| **Phase** | Phase 1 |
| **Rationale** | Cohere for best quality on critical searches; BGE for local speed on routine queries. |
| **Rejected** | Single reranker (risk of downtime or cost spike) |

### D9: Vector Database

| Field | Decision |
|-------|----------|
| **Primary** | **Qdrant** (self-hosted) |
| **Fallback** | Milvus (enterprise scale) / ChromaDB (dev only) |
| **Phase** | Phase 0 |
| **Rationale** | Fast, Python SDK, OSS, self-hostable. No vendor lock-in. Milvus only when we exceed Qdrant's scaling limits. ChromaDB strictly for local dev. |
| **Rejected** | Pinecone (too expensive at scale, proprietary), Weaviate (heavier ops) |

### D10: Relational Database

| Field | Decision |
|-------|----------|
| **Primary** | **PostgreSQL** (main) + **DuckDB** (analytics) |
| **Fallback** | SQLite (embedded/cache) |
| **Phase** | Phase 0 |
| **Rationale** | PostgreSQL for ACID transactions, extensions (pgvector, TimescaleDB). DuckDB for columnar analytics, feature store, backtest results. SQLite for zero-config local cache. |
| **Rejected** | MySQL (weaker ecosystem for extensions), ClickHouse (overkill for Phase 0) |

### D11: Cache

| Field | Decision |
|-------|----------|
| **Primary** | **Redis** |
| **Fallback** | Dragonfly |
| **Phase** | Phase 0 |
| **Rationale** | Redis is the industry standard: cache, session, pub/sub, rate limiting. Dragonfly is memory-compatible fallback if Redis reaches throughput limits. |
| **Rejected** | Memcached (no pub/sub, less flexible) |

### D12: Object Storage

| Field | Decision |
|-------|----------|
| **Primary** | **MinIO** (self-hosted) |
| **Fallback** | Backblaze B2 / S3 |
| **Phase** | Phase 0 |
| **Rationale** | S3-compatible, self-hosted, zero egress fees. Backblaze B2 for offsite backup at 1/5 S3 cost. Use Parquet format for data lake. |
| **Rejected** | S3-only (egress costs too high for data-heavy quant workloads) |

### D13: Message Queue / Event Bus

| Field | Decision |
|-------|----------|
| **Primary** | **NATS** (core bus) + **Redis Streams** (simple patterns) |
| **Fallback** | **Kafka** (enterprise scale) |
| **Phase** | Phase 0 |
| **Rationale** | NATS is lightweight, fast, cloud-native — perfect for AI agent communication. Redis Streams for simple pub/sub within services. Kafka only when we need persistent replay at scale. |
| **Rejected** | RabbitMQ (heavier than NATS, less cloud-native), ZeroMQ (no persistence) |

### D14: AI Workflow Engine

| Field | Decision |
|-------|----------|
| **Primary** | **LangGraph** (AI agent workflows) |
| **Fallback** | Temporal (durable execution) / n8n (visual workflows) |
| **Phase** | Phase 0 |
| **Rationale** | LangGraph is built for AI agent orchestration — state graphs, tool calling, multi-agent. Temporal for long-running durable tasks (backtest, training). n8n for non-technical workflow building. |
| **Rejected** | Prefect (Python-only, less AI support), AutoGen (less mature) |

### D15: Authentication & Identity

| Field | Decision |
|-------|----------|
| **Primary** | **Authentik** (self-hosted IdP) + **NextAuth.js** (app auth) |
| **Fallback** | Keycloak (enterprise IdP) / Clerk (managed auth) |
| **Phase** | Phase 0 |
| **Rationale** | Authentik is lighter than Keycloak, supports OAuth/OIDC/SAML/LDAP. NextAuth.js integrates natively with Next.js frontend. Clerk as managed fallback if self-hosted ops become burdensome. |
| **Rejected** | Auth0 (expensive at scale), Supabase Auth (tied to Supabase ecosystem) |

### D16: Secrets Management

| Field | Decision |
|-------|----------|
| **Primary** | **Infisical** (self-hosted) |
| **Fallback** | HashiCorp Vault |
| **Phase** | Phase 1 |
| **Rationale** | Modern UX, CLI + SDK, auto-rotation. Vault for high-compliance needs (SOC2, ISO). |
| **Rejected** | .env files (not secure for multi-agent system) |

### D17: Monitoring & Observability

| Field | Decision |
|-------|----------|
| **Primary** | **Prometheus + Grafana + Loki + OpenTelemetry + Sentry + LangFuse** |
| **Fallback** | Grafana Cloud / Datadog |
| **Phase** | Phase 1 |
| **Rationale** | Self-host OSS stack covers 80% needs at zero license cost. LangFuse for LLM-specific tracing (prompt versioning, cost per model, latency). Sentry for error tracking. Datadog only when infra team needs all-in-one. |
| **Rejected** | ELK (Loki is 10x cheaper for structured logs), New Relic (expensive) |

### D18: Cloud Infrastructure

| Field | Decision |
|-------|----------|
| **Primary** | **Hetzner Cloud** (VPS) + **K3s** (Kubernetes) |
| **Fallback** | AWS / GCP / Azure (managed services) |
| **Phase** | Phase 1 |
| **Rationale** | Hetzner is 3-5x cheaper than hyperscalers for equivalent specs. K3s is production-grade K8s under 512MB RAM. Move to AWS only when managed services (RDS, EKS) justify 5x premium. |
| **Rejected** | DigitalOcean (limited GPU options), Linode (acquired, uncertain future) |

### D19: GPU Cloud

| Field | Decision |
|-------|----------|
| **Primary** | **RunPod** (serverless inference) |
| **Fallback** | Vast.ai (spot/batch) / Lambda Labs (stable workloads) |
| **Phase** | Phase 1+ |
| **Rationale** | RunPod has auto-scaling serverless, PyTorch templates, best price-performance for inference. Vast.ai for spot batch jobs. Lambda Labs for stable training workloads. |
| **Policy** | RunPod serverless for inference → Vast.ai spot for batch → Lambda Labs for training. Never pay hyperscaler GPU prices. |
| **Rejected** | AWS/GCP GPUs (3-4x more expensive) |

### D20: Local Inference Engine

| Field | Decision |
|-------|----------|
| **Primary** | **vLLM** (production) / **SGLang** (constrained output) |
| **Fallback** | Ollama (dev/test) / LM Studio (research) |
| **Phase** | Phase 1+ |
| **Rationale** | vLLM = highest throughput (PagedAttention, continuous batching). SGLang = best for JSON/grammar-constrained output. Ollama for local dev simplicity. |
| **Rule** | Constrained output → SGLang; free-form throughput → vLLM; dev → Ollama |

### D21: CI/CD & Source Control

| Field | Decision |
|-------|----------|
| **Primary** | **GitHub** + **GitHub Actions** |
| **Fallback** | Gitea (self-host) + Woodpecker CI |
| **Phase** | Phase 0 |
| **Rationale** | GitHub ecosystem for community, Actions for CI/CD. Gitea + Woodpecker when Actions cost exceeds $200/month or for private repos. |
| **Rejected** | GitLab (heavier ops), Jenkins (too complex for startup) |

### D22: IaC (Infrastructure as Code)

| Field | Decision |
|-------|----------|
| **Primary** | **OpenTofu** + **Pulumi** |
| **Fallback** | Ansible |
| **Phase** | Phase 1 |
| **Rationale** | OpenTofu = free Terraform fork with same HCL. Pulumi for complex infra using general languages (Python/TypeScript). Ansible for config management. |
| **Rejected** | Terraform (license change, no longer OSS) |

### D23: Speech-to-Text

| Field | Decision |
|-------|----------|
| **Primary** | **Whisper** (self-hosted large-v3 via vLLM) |
| **Fallback** | Deepgram (streaming, better diarization) |
| **Phase** | Phase 2+ |
| **Rationale** | Whisper gives highest multilingual accuracy (100+ languages) and can self-host free. Deepgram excels at real-time streaming with lower latency and native diarization. |
| **Rejected** | Azure Speech (vendor lock-in) |

### D24: Text-to-Speech

| Field | Decision |
|-------|----------|
| **Primary** | **ElevenLabs Turbo v2** |
| **Fallback** | OpenAI TTS-1 HD (batch, cheaper) / Edge-TTS (free tier, dev only) |
| **Phase** | Phase 2+ |
| **Rationale** | Best-in-class voice quality + cloning. OpenAI TTS is 20x cheaper for batch synthesis. Edge-TTS for dev/testing only. |
| **Rejected** | Google Cloud TTS (less natural) |

### D25: Browser Automation

| Field | Decision |
|-------|----------|
| **Primary** | **Playwright** |
| **Fallback** | Puppeteer |
| **Phase** | Phase 1 |
| **Rationale** | Cross-browser, auto-wait, better API, faster than Puppeteer. |
| **Rejected** | Selenium (slow, heavy) |

### D26: Email & Notification

| Field | Decision |
|-------|----------|
| **Primary** | **Resend** (transactional) / **SendGrid** (marketing) |
| **Fallback** | AWS SES |
| **Phase** | Phase 2+ |
| **Rationale** | Resend has best DX for transactional emails. SendGrid for newsletter/marketing. SES as cost-effective fallback. |
| **Rejected** | Mailgun (less reliable deliverability) |

### D27: OCR

| Field | Decision |
|-------|----------|
| **Primary** | **PaddleOCR** |
| **Fallback** | Tesseract |
| **Phase** | Phase 2+ |
| **Rationale** | PaddleOCR is more accurate than Tesseract, especially for non-English text and document layouts. |
| **Rejected** | Google Vision OCR (API cost at scale) |

### D28: Translation

| Field | Decision |
|-------|----------|
| **Primary** | **DeepL** |
| **Fallback** | LibreTranslate (self-hosted, free) |
| **Phase** | Phase 2+ |
| **Rationale** | DeepL has best translation quality for financial/technical documents. LibreTranslate for privacy-sensitive content. |
| **Rejected** | Google Translate (privacy concerns for financial data) |

### D29: Frontend / Dashboard

| Field | Decision |
|-------|----------|
| **Primary** | **Next.js** + **shadcn/ui** + **Tailwind CSS** |
| **Fallback** | React + Material UI |
| **Phase** | Phase 1 |
| **Rationale** | Next.js for SSR/SSG, file-based routing, API routes. shadcn/ui for consistent design system. Tailwind for rapid development. |
| **Rejected** | Vue (smaller ecosystem for dev tools), Streamlit (not production-grade for complex UI) |

### D30: Analytics

| Field | Decision |
|-------|----------|
| **Primary** | **PostHog** (self-hosted) |
| **Fallback** | Plausible (privacy-focused) |
| **Phase** | Phase 2+ |
| **Rationale** | PostHog self-hosted gives full product analytics, session recording, feature flags. Plausible as lightweight alternative. |
| **Rejected** | Google Analytics (privacy concerns for financial app), Mixpanel (expensive) |

---

## Architecture Rules

1. **Self-host first, cloud fallback** — OSS self-hosted services are default; migrate to managed only when ops cost > cloud premium
2. **Multi-provider for every critical path** — No single point of failure on AI models, databases, or infrastructure
3. **Zero proprietary lock-in** — All decisions favor open standards, open source, and portable formats
4. **Cost-proportional scaling** — Start lean (Hetzner + K3s), scale up to enterprise (AWS) only when revenue justifies
5. **Security by default** — Authentik + Cloudflare WAF + Infisical + cert-manager from day 1
6. **Phase-gated adoption** — Complex technologies (GPU, monitoring, analytics) deferred to appropriate phase

---

## Stack Summary (Quick Reference)

```
Layer                    Primary              Fallback
=====================================================================
AI Gateway              OpenRouter            Direct API
LLM Reasoning           Claude Sonnet 5       GPT-5.5 Pro
LLM Fast                Gemini 3.5 Flash      DeepSeek V4 Flash
LLM Local               Qwen 3.5 / vLLM       Ollama
Embedding               Voyage + BGE          text-embedding-3
Vector DB               Qdrant                Milvus / ChromaDB
Database                PostgreSQL + DuckDB   SQLite
Cache                   Redis                 Dragonfly
Object Storage          MinIO                 Backblaze B2
Message Queue           NATS + Redis Streams  Kafka
AI Workflow             LangGraph             Temporal / n8n
Auth                    Authentik + NextAuth  Keycloak / Clerk
Secrets                 Infisical             HashiCorp Vault
Monitoring              Prometheus+Grafana+   Grafana Cloud /
                        Loki+OTel+Sentry+     Datadog
                        LangFuse
Cloud                   Hetzner + K3s         AWS / GCP / Azure
GPU Cloud               RunPod                Vast.ai / Lambda Labs
CI/CD                   GitHub + Actions      Gitea + Woodpecker
IaC                     OpenTofu + Pulumi     Ansible
Speech-to-Text          Whisper               Deepgram
Text-to-Speech          ElevenLabs Turbo v2   OpenAI TTS / Edge-TTS
Frontend                Next.js + shadcn/ui   React + MUI
Browser Auto            Playwright            Puppeteer
Analytics               PostHog (self-host)   Plausible
```

---

## Sign-off

| Role | Name | Decision |
|------|------|----------|
| **Founder** | (Owner) | ✅ Approved |
| **Research Director** | (AI) | ✅ Reviewed — recommended stack validated |
| **Strategy AI** | (AI) | ✅ Compiled — all decisions logged with rationale |

---

*Technology decisions are living documents. Revisit per quarter or when major new providers enter the market.*
