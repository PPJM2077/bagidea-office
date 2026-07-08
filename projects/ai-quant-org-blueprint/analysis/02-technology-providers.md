# AI Quant Office - Technology Providers Analysis

## 1. AI/LLM Providers

### Primary Choice: OpenRouter (Multi-Provider Gateway)
- **Pros:** Single API for all major models, automatic fallback, cost control, no vendor lock-in
- **Cons:** Additional latency layer, dependent on third-party uptime
- **Fallback:** Direct API per provider
- **Why:** Document explicitly requires multi-provider support with fallback routing

### LLM Models (Ranked by Role)

| Role | Primary | Fallback | Why |
|------|---------|----------|-----|
| Reasoning/Strategy | Claude Sonnet 5 / Opus 4.8 | GPT-5.5 Pro | Best reasoning, context window |
| Market Analysis | Gemini 3.5 Flash | DeepSeek V4 Flash | Speed + cost + accuracy |
| Coding | DeepSeek V4 Pro / Claude Sonnet 5 | GPT-5.5 Codex | Code generation quality |
| Risk Analysis | Claude Sonnet 5 | GPT-5.5 Pro | Conservative, explainable |
| News/Sentiment | Gemini 3.5 Flash | DeepSeek V4 Flash | High throughput, low cost |
| Local Inference | Qwen 3.5 / DeepSeek V3.2 | Mistral Small 3.2 | Zero API cost, privacy |
| Vision/Multi-modal | Gemini 3.5 Flash | GPT-5.5 Image | Best vision capabilities |

## 2. Embedding & Reranking Models

### Embedding
| Model | Dimensions | Use Case | Cost |
|-------|-----------|----------|------|
| voyage-3-large | 1024 | Knowledge base RAG | Medium |
| text-embedding-3-large | 3072 | Semantic search | Medium |
| bge-m3 (BAAI) | 1024 | Local embedding | Free |
| e5-mistral-7b | 4096 | High-quality local | Free (self-host) |

### Reranking
| Model | Best For | Cost |
|-------|----------|------|
| Cohere Rerank v3 | General purpose | Per-query |
| BGE Reranker v2 | Local deployment | Free |
| Voyage Rerank | Long context | Per-query |

**Primary:** Voyage (cloud) + BGE (local fallback)
**Why:** Knowledge OS needs both speed (local) and quality (cloud)

## 3. Database & Storage

### Vector Database
| Option | Pros | Cons | Primary/Fallback |
|--------|------|------|-----------------|
| Qdrant | Fast, Python SDK, OSS, self-host | Less ecosystem | PRIMARY |
| Milvus | Enterprise features, scaling | Heavy infra | FALLBACK |
| ChromaDB | Lightweight, dev-friendly | Not production-ready | Dev only |
| Pinecone | Managed, no ops | Expensive | Cloud option |

### Relational Database
| Option | Use Case | Why |
|--------|----------|-----|
| PostgreSQL | Main database, transactions | ACID, extensions, reliability |
| DuckDB | Analytics, Feature Store, Backtest | Columnar, fast aggregation |
| SQLite | Local cache, offline | Zero config, embedded |

### Storage
| Service | Use Case |
|---------|----------|
| MinIO (Primary) | S3-compatible object storage, self-hosted |
| S3 / Backblaze B2 (Fallback) | Cloud object storage |
| Parquet | Columnar format for Data Lake |

## 4. Cache & Message Queue

### Cache
| Option | Why |
|--------|-----|
| Redis (Primary) | Cache, session, pub/sub, rate limiting |
| Dragonfly (Fallback) | Redis-compatible, higher performance |

### Message Queue
| Option | Pros | Cons | Primary/Fallback |
|--------|------|------|-----------------|
| NATS | Lightweight, fast, cloud-native | Less features | PRIMARY |
| Redis Streams | Simple, Redis-native | No persistence | PRIMARY for simple |
| Kafka | Enterprise, durable, replay | Heavy ops | FALLBACK for scale |

## 5. Workflow Engine
| Option | Why | Primary/Fallback |
|--------|-----|-----------------|
| Temporal | Durable execution, retries, long-running | PRIMARY |
| n8n | Visual workflow builder, non-technical | Dev tool |
| Prefect | Python-native, scheduler | FALLBACK |
| LangGraph | AI agent workflow | PRIMARY for AI |


## 6. Monitoring & Observability

| Function | Primary | Fallback | Rationale |
|----------|---------|----------|-----------|
| **Metrics** | Prometheus + Grafana (self-host) | Grafana Cloud / Datadog | OSS, K8s-native, large ecosystem; Grafana Cloud when no infra team |
| **Logging** | Loki + Grafana (self-host) | ELK Stack / Axiom | Loki 10x cheaper than ES for structured logs; ELK when deep full-text search needed |
| **Tracing** | OpenTelemetry + Jaeger | Sentry Performance / Datadog APM | OTel = industry standard; Jaeger is lightweight |
| **Alerting** | Alertmanager + Grafana OnCall | PagerDuty / Opsgenie | OSS free; PagerDuty when large team needs escalation |
| **Uptime** | Uptime Kuma (self-host) | Checkly / Better Uptime | Free, easy config, synthetic monitoring |
| **APM/Errors** | Sentry (self-host cloud) | Datadog RUM | Most mature error tracking; Datadog for all-in-one with budget |
| **LLM Obs.** | LangFuse (self-host) | LangSmith / Weights and Biases | LLM-specific tracing, prompt versioning, cost tracking |

**Primary Stack:** Prometheus + Loki + OpenTelemetry + Sentry + LangFuse
**Fallback:** Grafana Cloud (managed) + Datadog (enterprise)
**Why:** Self-host OSS covers 80% free; Datadog/Grafana Cloud when infra team overflow


## 7. Authentication & Security

| Function | Primary | Fallback | Rationale |
|----------|---------|----------|-----------|
| **Identity** | Authentik (self-host) | Keycloak / Clerk | Authentik lighter than Keycloak, full OAuth/OIDC/SAML/LDAP |
| **OAuth** | NextAuth.js (Auth.js) | Auth0 / Supabase Auth | Open source, Next.js native |
| **API Auth** | Clerk + JWT | Supabase Auth | Great DX, automatic session management |
| **Secrets** | Infisical (self-host) | HashiCorp Vault | Modern UX vs Vault; Vault for high compliance |
| **WAF** | Cloudflare WAF | AWS WAF / Palo Alto | 30M+ request rate, 0-day protection, cheaper than AWS WAF |
| **DDoS** | Cloudflare | AWS Shield Advanced | Best absorption capacity |
| **TLS** | Let's Encrypt + cert-manager | Cloudflare SSL / ZeroSSL | Auto-renew on K8s |

**Primary Stack:** Authentik + NextAuth.js + Infisical + Cloudflare + cert-manager
**Fallback:** Clerk (managed Auth) + HashiCorp Vault (enterprise secrets)
**Why:** OSS-first, cost-effective, works well on K8s


## 8. Cloud Infrastructure

| Function | Primary | Fallback | Rationale |
|----------|---------|----------|-----------|
| **Cloud** | Hetzner Cloud | AWS / GCP / Azure | 3-5x cheaper than hyperscaler; AWS for managed services |
| **Container** | Docker + K3s | Nomad / EKS | K3s = production K8s under 512MB RAM |
| **CI/CD** | GitHub Actions | GitLab CI / Woodpecker | GitHub ecosystem; Woodpecker OSS self-host when Actions expensive |
| **Source** | GitHub | GitLab / Gitea | Community; Gitea for self-host privacy |
| **IaC** | OpenTofu + Pulumi | Ansible / Crossplane | OpenTofu = free Terraform fork; Pulumi uses general languages |

**Primary Stack:** Hetzner + K3s + GitHub + OpenTofu
**Fallback:** AWS (managed infra) + Nomad (when K8s too much)
**Why:** Hetzner + K3s = 1/5 hyperscaler cost; scale up only when managed service needed

## 9. GPU Cloud Providers and Model Serving

| Provider | GPU Type | Pricing | Strengths | Weaknesses |
|----------|----------|---------|-----------|------------|
| **RunPod (Primary)** | A100 80G, H100, L40S | /usr/bin/bash.79/hr H100 | Auto-scaling serverless, PyTorch templates | NVIDIA only, no fast inter-node |
| **Vast.ai (Fallback)** | A100, H100, RTX 6000 | ~/usr/bin/bash.50-0.70/hr H100 | Lowest cost, wide GPU range | Unreliable, high network latency |
| **Lambda Labs** | A100, H100, GH200 | .29/hr H100 | Stable uptime, great docs | Pricier, fewer datacenters |
| **TensorDock** | A100 80G, RTX 4090 | ~/usr/bin/bash.60/hr A100 | Mid-range, batch discount | No auto-scaling |
| **AWS/GCP** | H100, TPU v5p | -4/hr H100 | Full managed, VPC | 3-4x RunPod price |

### Local Inference Engines

| Engine | Role | Rationale |
|--------|------|-----------|
| **vLLM** | PRIMARY (production) | PagedAttention, continuous batching, highest throughput |
| **SGLang** | PRIMARY (structured gen) | JSON/grammar constrained output, lower latency than vLLM |
| **Ollama** | DEV/TESTING | Easiest setup, auto model management |
| **LM Studio** | RESEARCH | Desktop GUI, researcher-friendly |
| **TensorRT-LLM** | NVIDIA OPTIMIZED | 2x throughput, complex setup |

**Rule:** constrained output -> SGLang; free-form throughput -> vLLM; dev -> Ollama
**Policy:** RunPod serverless for inference; spot for batch; Vast.ai fallback

## 10. AI/ML Tools -- Expanded Analysis

### 10.1 Speech-to-Text

| Criteria | Whisper (Primary) | Deepgram (Fallback) | Azure Speech (Cloud alt) |
|----------|-------------------|---------------------|--------------------------|
| **Type** | OSS / OpenAI API | Cloud API | Cloud API |
| **Languages** | 100+ | 30+ | 100+ |
| **Latency** | ~1x real-time (GPU) | 0.5x streaming | ~1x |
| **Accuracy** | ~95-97% (large-v3) | ~94-96% (Nova-2) | ~94-96% |
| **Cost** | Free local / /usr/bin/bash.006/min API | /usr/bin/bash.004/min | /usr/bin/bash.007/min |
| **Diarization** | Separate model | Native | Native |
| **Custom Vocab** | Fine-tune needed | Built-in boost | Built-in |

**SUB: Speech-to-Text**
**Primary:** Whisper (OpenAI API or self-host large-v3 via vLLM)
**Fallback:** Deepgram (streaming use case, better diarization)
**Why:** Whisper gives highest multilingual accuracy and can self-host free; Deepgram excels at real-time streaming with lower latency

### 10.2 Text-to-Speech

| Criteria | ElevenLabs (Primary) | OpenAI TTS (Fallback) | Edge-TTS (Free tier) |
|----------|---------------------|----------------------|----------------------|
| **Voice Quality** | Best-in-class | Good | Fair |
| **Languages** | 29 | 6 | 60+ |
| **Voice Cloning** | Yes (instant/professional) | No | No |
| **Cost** | /usr/bin/bash.30/char (Turbo) | /usr/bin/bash.015/char (HD) | Free |
| **Emotion/Style** | 28 tone presets | 6 voices | Limited |

**SUB: Text-to-Speech**
**Primary:** ElevenLabs Turbo v2 (best quality + latency for user-facing)
**Fallback:** OpenAI TTS-1 HD (20x cheaper for batch synthesis)
**Edge-TTS:** dev/testing/low-importance audio only (free)
**Why:** ElevenLabs still leads in natural voice quality and cloning; OpenAI TTS is the cost-efficient batch alternative

