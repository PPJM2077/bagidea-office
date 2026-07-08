# AI Quant Office — Integration Guide v1.0

> **AI-Native Format:** This guide is designed for both **human developers** and
> **AI agents** to read and understand how to load, configure, and use the
> AQIOS package. Every section includes machine-readable configuration blocks,
> API schemas, and example invocations for any AI model provider.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Package Anatomy](#2-package-anatomy)
3. [Integration Methods](#3-integration-methods)
   - [Method A: Direct API Integration](#method-a-direct-api-integration)
   - [Method B: AI Gateway Proxy](#method-b-ai-gateway-proxy)
   - [Method C: SDK Import](#method-c-sdk-import)
   - [Method D: Plugin Loading](#method-d-plugin-loading)
   - [Method E: Container Deployment](#method-e-container-deployment)
   - [Method F: Anthropic/OpenAI/Gemini Client Init](#method-f-cross-provider-client-init)
4. [Role Loading — Assigning AI Roles to Models](#4-role-loading)
5. [Context Schema — Inter-Agent Communication](#5-context-schema)
6. [Event Integration — Pub/Sub Message Formats](#6-event-integration)
7. [Authentication & Security](#7-authentication--security)
8. [Testing Your Integration](#8-testing-your-integration)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Quick Start

```bash
# 1. Clone/extract the AQIOS package
tar -xzf aqios-1.0.0.tar.gz
cd aqios-1.0.0/

# 2. Install core dependencies
pip install -r requirements.txt
# or: npm install   (for Node.js gateway)

# 3. Configure your AI provider keys
cp config/gateway.example.yaml config/gateway.yaml
# Edit config/gateway.yaml with your API keys

# 4. Start the AI Gateway
python -m aqios.gateway --config config/gateway.yaml

# 5. Load a role and run
python -m aqios.shell --role market-analyst --symbol XAUUSD
```

**Or via Docker:**
```bash
docker compose up -d        # starts gateway + event bus + memory + all core modules
docker compose logs -f      # watch the AI office come alive
```

---

## 2. Package Anatomy

```
aqios-1.0.0/
├── 04_package_manifest.yaml       # ← THIS FILE — package manifest
├── 05_prompt_library.md           # ← THIS FILE — prompt templates
├── 06_capability_matrix.md        # ← THIS FILE — capability definitions
├── 07_integration_guide.md        # ← THIS FILE — you are here
│
├── aqios/                          # Python package
│   ├── __init__.py
│   ├── gateway/                    # AI Gateway — multi-provider router
│   │   ├── provider_claude.py
│   │   ├── provider_gemini.py
│   │   ├── provider_openai.py
│   │   └── router.py
│   ├── kernel/                     # Office Kernel
│   │   ├── identity.py
│   │   ├── permission.py
│   │   └── presence.py
│   ├── communication/              # AI Communication Bus
│   │   ├── event_bus.py
│   │   ├── chat.py
│   │   ├── meeting.py
│   │   └── debate.py
│   ├── memory/                     # Memory System
│   │   ├── store.py
│   │   ├── knowledge_graph.py
│   │   └── timeline.py
│   ├── knowledge/                  # Knowledge OS
│   │   ├── rag.py
│   │   ├── wiki.py
│   │   └── citation.py
│   ├── risk/                       # Risk Engine
│   │   ├── position_sizer.py
│   │   ├── drawdown.py
│   │   └── var.py
│   ├── portfolio/                  # Portfolio Engine
│   │   ├── unified_view.py
│   │   ├── optimizer.py
│   │   └── profit_lock.py
│   ├── execution/                  # Execution Engine
│   │   └── order_manager.py
│   ├── intelligence/               # Market & Research
│   │   ├── technical.py
│   │   ├── regime.py
│   │   ├── backtest.py
│   │   └── optimizer.py
│   ├── governance/                 # AI Constitution
│   │   ├── constitution.py
│   │   ├── committee.py
│   │   └── audit.py
│   ├── employee/                   # AI Employee System
│   │   ├── registry.py
│   │   ├── kpi.py
│   │   └── reputation.py
│   └── simulation/                 # Digital Twin
│       ├── sandbox.py
│       └── scenario.py
│
├── config/                         # Configuration templates
│   ├── gateway.yaml
│   ├── constitution.yaml
│   ├── risk_policies.yaml
│   └── roles.yaml
│
├── prompts/                        # Prompt library (individual files)
│   ├── ceo-ai.md
│   ├── market-analyst.md
│   ├── risk-manager.md
│   ├── portfolio-manager.md
│   ├── research-director.md
│   └── ... (all roles from prompt library)
│
├── sdk/                            # Strategy SDK
│   ├── strategy_base.py
│   ├── indicators/
│   └── examples/
│
├── plugins/                        # Plugin directory
│   └── example/                    # Example plugin
│
├── tests/                          # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docker-compose.yml              # Full stack deployment
├── requirements.txt                # Python dependencies
└── README.md                       # Top-level documentation
```

---

## 3. Integration Methods

AQIOS supports **6 integration methods**, from simplest (call an API) to
most complete (deploy the full OS). Choose based on your use case:

| Method | Depth | Setup Time | Use Case |
|---|---|---|---|
| A. Direct API | Low | 5 min | Call specific capabilities from any AI |
| B. AI Gateway Proxy | Medium | 15 min | Route tasks through AQIOS smart router |
| C. SDK Import | High | 30 min | Build custom AQIOS-compatible modules |
| D. Plugin Loading | Full | 10 min per plugin | Extend AQIOS with new capabilities |
| E. Container Deployment | Full | 1 hr | Run the complete AI Office |
| F. Provider Client Init | Low | 5 min | Load AQIOS as context into any AI chat session |

---

### Method A: Direct API Integration

Best for: **any AI model (Claude, GPT, Gemini, DeepSeek) that needs to call
AQIOS capabilities from its own conversation.**

Each AQIOS module exposes a REST API. Any AI can call it via HTTP:

```python
import requests
import json

# 1. Get authentication token
auth_resp = requests.post(
    "http://localhost:8080/auth/token",
    json={"identity_id": "market-analyst-1", "secret": "your-secret"}
)
token = auth_resp.json()["token"]

# 2. Call a capability
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8080/api/v1/market/analyze",
    headers=headers,
    json={
        "symbol": "XAUUSD",
        "timeframes": ["H1", "H4", "D1"],
        "indicators": ["EMA", "RSI", "VWAP", "ATR"]
    }
)

analysis = response.json()
print(json.dumps(analysis, indent=2))
```

**From any AI (Claude, GPT, etc.):**
You can instruct the AI to make HTTP calls to the AQIOS API. Provide this
instruction in your system prompt:

```markdown
You have access to the AQIOS API at http://localhost:8080/api/v1/
Available endpoints:
- POST /market/analyze        — Market analysis
- POST /risk/assess           — Risk assessment
- POST /portfolio/view        — Portfolio status
- POST /knowledge/query       — RAG query
- POST /governance/check      — Constitution compliance check

Authenticate with: Authorization: Bearer {{token}}
Use these endpoints to gather data before making decisions.
```

**API Endpoint Reference:**

| Endpoint | Method | Description | Request Body | Response |
|---|---|---|---|---|
| `/api/v1/auth/token` | POST | Get auth token | `{identity_id, secret}` | `{token, expires_at}` |
| `/api/v1/market/analyze` | POST | Full market analysis | `{symbol, timeframes[], indicators[]}` | Analysis report |
| `/api/v1/market/regime` | POST | Detect market regime | `{symbol}` | `{regime, confidence}` |
| `/api/v1/market/news` | POST | News & sentiment | `{symbol, sources[]?}` | `{sentiment, stories[]}` |
| `/api/v1/risk/assess` | POST | Risk assessment | `{symbol, side, lots, context}` | Risk report |
| `/api/v1/risk/size` | POST | Position sizing | `{equity, risk_percent, atr, adjustments}` | `{recommended_lots}` |
| `/api/v1/risk/safe-mode` | POST | Toggle safe mode | `{action: "activate" \| "deactivate", reason}` | `{status}` |
| `/api/v1/portfolio/view` | POST | Unified portfolio | `{}` | Portfolio snapshot |
| `/api/v1/portfolio/scenario` | POST | Run scenario | `{actions[], assumptions}` | Scenario results |
| `/api/v1/decision/compute` | POST | Compute decision | `{signals[], context}` | `{decision, confidence}` |
| `/api/v1/decision/devils-advocate` | POST | Adversarial review | `{proposal}` | `{flaws[], survives}` |
| `/api/v1/knowledge/query` | POST | RAG query | `{query, tier_filter?}` | `{answer, sources[]}` |
| `/api/v1/knowledge/fact-check` | POST | Fact check claim | `{claim}` | `{supported, sources[]}` |
| `/api/v1/governance/check` | POST | Constitution check | `{action, context}` | `{compliant, violations[]}` |
| `/api/v1/governance/propose` | POST | Submit proposal | `{title, change, evidence}` | `{proposal_id}` |
| `/api/v1/strategy/deploy` | POST | Deploy strategy | `{strategy_package, version}` | `{deployment_id}` |
| `/api/v1/strategy/health` | GET | Strategy health | `{strategy_id}` | Health report |
| `/api/v1/employee/profile` | GET | Employee profile | `{agent_id}` | Profile data |
| `/api/v1/employee/kpi` | PUT | Update KPI | `{agent_id, metric, value}` | `{new_score}` |
| `/api/v1/system/health` | GET | System health | `{}` | Health dashboard |

---

### Method B: AI Gateway Proxy

Best for: **Intelligent routing across multiple AI providers with cost
optimization and fallback.**

The AI Gateway acts as a proxy between your application and any AI provider.
It automatically selects the best model for each task based on quality, cost,
and availability.

```yaml
# config/gateway.yaml
gateway:
  port: 8080
  default_ttl: 30s
  
  providers:
    - name: claude
      type: anthropic
      api_key: "${ANTHROPIC_API_KEY}"
      model: claude-sonnet-4-6
      roles: [reasoning, coding, risk-analysis, decision]
      weight: 1.0
      cost_limit_per_day: 50
      fallback: [gemini, deepseek]

    - name: gemini
      type: google
      api_key: "${GEMINI_API_KEY}"
      model: gemini-2.5-pro
      roles: [vision, market-analysis, sentiment, local]
      weight: 0.8
      cost_limit_per_day: 30
      fallback: [deepseek, claude]

    - name: deepseek
      type: deepseek
      api_key: "${DEEPSEEK_API_KEY}"
      model: deepseek-v4
      roles: [analysis, coding, backup]
      weight: 0.6
      cost_limit_per_day: 20

    - name: ollama
      type: local
      endpoint: http://localhost:11434
      model: qwen2.5:32b
      roles: [local-backup, simple-tasks]
      weight: 0.3
      free: true

  routing:
    strategy: cost_quality_optimized  # or: least_latency, cheapest, highest_quality
    parallel_threshold: 0.7            # use parallel ensemble if disagreement > 30%
    budget_alert_at: 0.8               # alert at 80% budget usage
```

**Python client usage:**
```python
from aqios.gateway import AIGateway

gateway = AIGateway("config/gateway.yaml")

# The gateway selects the best provider automatically
response = gateway.request(
    task_type="market_analysis",
    prompt="Analyze XAUUSD technical structure on H1 timeframe",
    context={"symbol": "XAUUSD", "timeframes": ["H1"]}
)

# Or force a specific provider
response = gateway.request(
    task_type="risk_assessment",
    prompt="Calculate position size for 1% risk on $10,000 account",
    context={"equity": 10000, "risk_percent": 1.0},
    preferred_provider="claude"  # override: use Claude for risk
)

print(f"Response from {response.provider}: {response.text}")
print(f"Cost: ${response.cost:.4f}, Latency: {response.latency_ms}ms")
```

**Ensemble mode — ask multiple AIs and aggregate:**
```python
responses = gateway.ensemble(
    prompt="What is the market bias for XAUUSD today?",
    providers=["claude", "gemini", "deepseek"],
    strategy="consensus_weighted"
)

print(f"Consensus: {responses.consensus}")
print(f"Agreement: {responses.agreement_level}%")
for r in responses.results:
    print(f"  {r.provider}: {r.bias} (confidence: {r.confidence})")
```

---

### Method C: SDK Import

Best for: **Building custom AQIOS-compatible agents, strategies, or modules.**

```python
from aqios.kernel import Identity, Permission
from aqios.communication import EventBus, Chat
from aqios.memory import MemoryStore
from aqios.knowledge import RAGEngine
from aqios.risk import PositionSizer, DrawdownMonitor
from aqios.intelligence import MarketAnalyzer, BacktestEngine
from aqios.governance import Constitution, Committee

# Create a new AI agent with full AQIOS identity
agent = Identity.register(
    name="custom-analyst",
    role="market-analyst",
    department="investment",
    model="claude-sonnet-4-6",
    skills=["technical-analysis", "pattern-recognition", "risk-assessment"]
)

# Subscribe to events
event_bus = EventBus("nats://localhost:4222")
event_bus.subscribe("market.data.updated", agent.handle_market_update)
event_bus.subscribe("risk.limit.breached", agent.handle_risk_alert)

# Use AQIOS capabilities
memory = MemoryStore()
rag = RAGEngine()

# Run analysis
analyzer = MarketAnalyzer()
report = analyzer.analyze("XAUUSD", timeframes=["H1", "H4", "D1"])

# Save to memory
memory.store(agent.id, "analysis", report)

# Check constitution
constitution = Constitution()
if constitution.check("trade", {"side": "buy", "lots": 0.5}).compliant:
    # Risk assessment
    sizer = PositionSizer()
    position = sizer.calculate(
        equity=10000, risk_percent=1.0, atr=25.0, 
        correlation=0.3, news_factor=0.5
    )
    print(f"Recommended position: {position.lots} lots")
```

**Strategy SDK — implement a custom strategy:**
```python
from aqios.sdk import StrategyBase

class MyTrendStrategy(StrategyBase):
    def initialize(self, config):
        self.ma_fast = config.get("ma_fast", 20)
        self.ma_slow = config.get("ma_slow", 100)
        self.rsi_period = config.get("rsi_period", 14)
    
    def analyze(self, market_data):
        # Market analysis logic
        return {"signal": "buy", "confidence": 75}
    
    def score(self, analysis):
        # Score/rank the signal
        score = analysis["confidence"]
        if analysis.get("volume_confirmation"):
            score += 10
        return {"score": score, "max": 100}
    
    def entry(self, score, risk_params):
        if score["score"] > 70:
            return {"action": "buy", "lots": risk_params["size"]}
        return {"action": "wait"}
    
    def exit(self, position, market_data):
        if market_data["rsi"] > 70:
            return {"action": "close"}
        return {"action": "hold"}
    
    def manage(self, position, market_data):
        # Trailing stop, etc.
        return {"adjust_sl": market_data["atr"] * 2}
    
    def cleanup(self):
        pass

# Register the strategy
strategy = MyTrendStrategy({"ma_fast": 20, "ma_slow": 100})
deployment = strategy.deploy()  # enters sandbox → shadow → canary pipeline
```

---

### Method D: Plugin Loading

Best for: **Adding new capabilities without modifying core code.**

Every AQIOS plugin follows a standard manifest format:

```yaml
# plugins/quant-oscillator/plugin.json
{
  "id": "quant-oscillator",
  "version": "1.0.0",
  "name": "Quant Oscillator Suite",
  "type": "indicator",
  "depends_on": ["core.kernel", "core.event-bus"],
  "capabilities": ["oscillator_analysis", "divergence_detection"],
  "permissions": ["knowledge:write", "market:read"],
  "entry_point": "main.py"
}
```

```bash
# Install a plugin
curl -X POST http://localhost:8080/plugins/install \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"source": "plugins/quant-oscillator", "enable": true}'

# Response:
# {"plugin_id": "quant-oscillator", "status": "sandbox", "dependencies_resolved": true}

# After testing, promote to active:
curl -X POST http://localhost:8080/plugins/quant-oscillator/enable \
  -H "Authorization: Bearer ${TOKEN}"
```

---

### Method E: Container Deployment

Best for: **Running the complete AI Office as a production system.**

```yaml
# docker-compose.yml (core services)
version: "3.8"
services:
  nats:
    image: nats:2.10-alpine
    ports: ["4222:4222"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["./data/qdrant:/qdrant/storage"]

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: aqios
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: ["./data/postgres:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  aqios-gateway:
    build: ./aqios/gateway
    ports: ["8080:8080"]
    depends_on: [nats, redis]
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
    volumes: ["./config:/app/config"]

  aqios-memory:
    build: ./aqios/memory
    depends_on: [nats, qdrant, postgres]

  aqios-risk:
    build: ./aqios/risk
    depends_on: [nats, redis]

  aqios-portfolio:
    build: ./aqios/portfolio
    depends_on: [nats, postgres]

  aqios-dashboard:
    build: ./ui/dashboard
    ports: ["3000:3000"]
    depends_on: [aqios-gateway]
```

---

### Method F: Cross-Provider Client Init

Best for: **Loading AQIOS as context into any AI chat session (Claude/GPT/Gemini/DeepSeek).**

This method doesn't require running any server — you just provide the package
files as context to any AI model, and it can understand and use the AQIOS
framework autonomously.

#### For Anthropic Claude:

```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-...")

# Load the AQIOS package files as context
with open("aqios-1.0.0/04_package_manifest.yaml") as f:
    manifest = f.read()
with open("aqios-1.0.0/05_prompt_library.md") as f:
    prompts = f.read()
with open("aqios-1.0.0/06_capability_matrix.md") as f:
    matrix = f.read()

response = client.messages.create(
    model="claude-sonnet-4-6-20250601",
    max_tokens=4096,
    system=f"""You are an AI analyst in the AQIOS (AI Quant Office OS).

You have been loaded with the AQIOS package. You understand:
- 26+ modules across 9 layers
- 18 AI roles with defined responsibilities
- The AI Constitution with 7 articles
- Full capability matrix with input/output schemas

Immediately available knowledge:
{manifest[:2000]}
{prompts[:5000]}

Use the AQIOS framework to structure your analysis and decisions.
When asked about any financial/trading topic, adopt the appropriate
AI role from the organization and respond with evidence-based analysis.""",
    messages=[
        {"role": "user", "content": "Analyze XAUUSD using the Market Analyst framework."}
    ]
)
```

#### For OpenAI GPT:

```python
from openai import OpenAI

client = OpenAI(api_key="sk-...")

# Same file loading as above...

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": f"""You are running AQIOS (AI Quant Office OS).
Loaded modules: market intelligence, risk engine, portfolio management, governance.
{prompts[:5000]}"""},
        {"role": "user", "content": "What is the current risk assessment for a proposed gold trade?"}
    ]
)
```

#### For Google Gemini:

```python
import google.generativeai as genai

genai.configure(api_key="AIza...")

with open("aqios-1.0.0/04_package_manifest.yaml") as f:
    manifest = f.read()
with open("aqios-1.0.0/05_prompt_library.md") as f:
    prompts = f.read()

model = genai.GenerativeModel(
    model_name="gemini-2.5-pro-exp-03-25",
    system_instruction=f"""You are the Risk Manager AI in AQIOS.
Organization: AI Quant Office
Constitution: Capital Protection, Evidence First

{prompts[:4000]}"""
)

response = model.generate_content("Calculate position size for a $10,000 account with 1% risk, ATR at 25 points.")
```

#### For DeepSeek:

```python
from openai import OpenAI  # DeepSeek uses OpenAI-compatible API

client = OpenAI(
    api_key="sk-...",
    base_url="https://api.deepseek.com/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": f"AQIOS Market Analyst loaded.\n{manifest[:3000]}"},
        {"role": "user", "content": "Analyze BTCUSD with multi-timeframe structure analysis."}
    ]
)
```

#### For Local Ollama/OpenAI-compatible:

```python
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # not used for local
)

response = client.chat.completions.create(
    model="qwen2.5:32b",
    messages=[
        {"role": "system", "content": "AQIOS Constitution: Article 1: Protect Capital. You are CRO AI."},
        {"role": "user", "content": "Run a stress test on the current portfolio."}
    ]
)
```

---

## 4. Role Loading — Assigning AI Roles to Models

Each AI model instance can be assigned an AQIOS role. This gives it the
correct system prompt, permissions, and capability access.

```yaml
# config/roles.yaml
agents:
  - name: "Alice"
    role: "market-analyst"
    model: "gemini-2.5-pro"
    department: "investment"
    skills:
      technical_analysis: 95
      pattern_recognition: 88
      macro_analysis: 82
    permissions:
      - "signal:publish"
      - "analysis:write"
    budget: { monthly: 30, currency: "USD" }

  - name: "Bob"
    role: "risk-manager"
    model: "claude-sonnet-4-6"
    department: "risk"
    skills:
      risk_assessment: 97
      var_calculation: 94
      portfolio_risk: 90
    permissions:
      - "risk:monitor"
      - "position:size"
      - "trade:veto"
    budget: { monthly: 40, currency: "USD" }

  - name: "Eva"
    role: "research-director"
    model: "claude-opus-4-8"
    department: "research"
    skills:
      backtesting: 96
      statistical_analysis: 93
      strategy_design: 91
    permissions:
      - "research:propose"
      - "backtest:run"
    budget: { monthly: 60, currency: "USD" }
```

**Loading roles programmatically:**
```python
from aqios.kernel import RoleLoader

roles = RoleLoader("config/roles.yaml")
for agent_config in roles.agents:
    # Get the system prompt for this role
    prompt = roles.get_system_prompt(agent_config.role)
    
    # Register with AI Gateway
    gateway.register_agent(
        name=agent_config.name,
        role=agent_config.role,
        system_prompt=prompt,
        preferred_model=agent_config.model,
        permissions=agent_config.permissions
    )
    
    # Launch the agent
    gateway.launch_agent(agent_config.name)
```

---

## 5. Context Schema — Inter-Agent Communication

AI agents in AQIOS communicate through structured context objects. Every
message, event, and decision follows these schemas.

### 5.1 Signal Context (Market Analysis → Decision Engine)

```yaml
signal:
  $schema: "https://aqios.io/schemas/signal-v1"
  type: object
  required: [signal_id, source, symbol, bias, confidence, evidence, timestamp]
  properties:
    signal_id: { type: string, pattern: "^SIG-\\d{14}-\\w{8}$" }
    source: { type: string, enum: ["market-analyst", "news-ai", "strategy-ai", "macro-ai"] }
    symbol: { type: string }
    bias: { type: string, enum: ["bullish", "bearish", "neutral"] }
    confidence: { type: integer, minimum: 0, maximum: 100 }
    evidence:
      type: array
      items:
        type: object
        required: [type, value, source_tier]
        properties:
          type: { type: string }
          value: { type: string }
          source_tier: { type: integer, enum: [0, 1, 2, 3, 4] }
    supporting_analysis:
      type: object
      properties:
        timeframe_breakdown: { type: object }
        key_levels: { type: object }
        momentum: { type: object }
        volatility: { type: object }
    risk_factors: { type: array, items: { type: string } }
    timestamp: { type: string, format: "date-time" }
```

### 5.2 Decision Context (Decision Engine → Execution)

```yaml
decision:
  $schema: "https://aqios.io/schemas/decision-v1"
  type: object
  required: [decision_id, action, confidence, evidence_summary, approved_by]
  properties:
    decision_id: { type: string, pattern: "^DEC-\\d{14}-\\d{4}$" }
    action:
      type: object
      required: [type, symbol, side, lots]
      properties:
        type: { type: string, enum: ["market", "limit", "stop", "oco"] }
        symbol: { type: string }
        side: { type: string, enum: ["buy", "sell"] }
        lots: { type: number, minimum: 0.01 }
        sl: { type: number }
        tp: { type: number }
    confidence: { type: integer, minimum: 0, maximum: 100 }
    consensus_level: { type: string, enum: ["unanimous", "majority", "split", "override"] }
    evidence_summary: { type: string }
    contributing_signals:
      type: array
      items: { $ref: "#/signal" }
    devil_advocate_review:
      type: object
      properties:
        survives_scrutiny: { type: boolean }
        flaws: { type: array, items: { type: string } }
        mitigations: { type: array, items: { type: string } }
    approved_by:
      type: array
      items:
        type: object
        properties:
          role: { type: string }
          vote: { type: string, enum: ["approve", "reject", "abstain"] }
          timestamp: { type: string, format: "date-time" }
    timestamp: { type: string, format: "date-time" }
```

### 5.3 Risk Context (Risk Manager → Decision Engine)

```yaml
risk_assessment:
  $schema: "https://aqios.io/schemas/risk-v1"
  type: object
  required: [assessment_id, risk_level, position_size_recommendation, constitution_compliant]
  properties:
    assessment_id: { type: string }
    risk_level: { type: string, enum: ["low", "medium", "high", "critical"] }
    position_size_recommendation: { type: string }
    position_size_lots: { type: number }
    max_position_size_lots: { type: number }
    risk_per_trade: { type: number, description: "Percentage of portfolio" }
    adjustments:
      type: array
      items:
        type: object
        properties:
          factor: { type: string }
          multiplier: { type: number }
          reason: { type: string }
    constitution_compliant: { type: boolean }
    violations: { type: array, items: { type: string } }
    veto: { type: boolean }
    veto_reason: { type: string }
    safe_mode_recommended: { type: boolean }
```

### 5.4 Proposal Context (Any AI → Governance)

```yaml
proposal:
  $schema: "https://aqios.io/schemas/proposal-v1"
  type: object
  required: [proposal_id, title, change, change_level, evidence, proposer]
  properties:
    proposal_id: { type: string, pattern: "^PRO-\\d{14}$" }
    title: { type: string, maxLength: 200 }
    change:
      type: object
      properties:
        target: { type: string }
        old_value: { type: string }
        new_value: { type: string }
        module: { type: string }
    change_level:
      type: string
      enum: ["auto", "review", "owner_approval", "locked"]
    evidence:
      type: array
      items:
        type: object
        properties:
          type: { type: string }
          source: { type: string }
          data: { type: string }
          confidence: { type: number }
    impact_analysis:
      type: object
      properties:
        expected_improvement: { type: string }
        downside_risk: { type: string }
        affected_modules: { type: array, items: { type: string } }
    proposer: { type: string }
    timestamp: { type: string, format: "date-time" }
```

### 5.5 Meeting Context (CEO → All Departments)

```yaml
meeting:
  $schema: "https://aqios.io/schemas/meeting-v1"
  type: object
  required: [meeting_id, title, chair, agenda, attendees]
  properties:
    meeting_id: { type: string }
    title: { type: string }
    chair: { type: string }
    agenda:
      type: array
      items:
        type: object
        properties:
          item: { type: string }
          presenter: { type: string }
          duration_minutes: { type: integer }
    attendees: { type: array, items: { type: string } }
    mode: { type: string, enum: ["sync", "async"] }
    minutes:
      type: object
      properties:
        discussions: { type: array }
        decisions: { type: array }
        action_items: { type: array }
    transcript_url: { type: string, format: "uri" }
```

---

## 6. Event Integration — Pub/Sub Message Formats

All AQIOS events follow a standard envelope format when published to the
Event Bus (NATS/Redis Streams):

```json
{
  "event_id": "evt_2xK9mR4qW8",
  "type": "market.data.updated",
  "version": "1",
  "source": "market-data-service",
  "source_agent": "broker-ai-1",
  "timestamp": "2026-07-08T09:30:00.000Z",
  "payload": { /* type-specific content */ },
  "priority": "normal",
  "correlation_id": "corr_8HnP3sT5",
  "ttl_seconds": 300
}
```

**Key event types and their payloads:**

| Event Type | Payload | Publishers | Subscribers |
|---|---|---|---|
| `market.data.updated` | `{symbol, bid, ask, spread, volume, timestamp}` | Broker AI | Market Analyst, Risk, Dashboard |
| `market.regime.changed` | `{symbol, regime, confidence, evidence}` | Market Analyst | Strategy, Risk, Portfolio |
| `analysis.signal.published` | Signal context (see §5.1) | Market Analyst, News | Decision Engine, CEO, CIO |
| `risk.limit.breached` | `{metric, limit, current_value, severity}` | Risk Manager | CEO, CRO, DevOps |
| `risk.safe-mode.activated` | `{trigger, level, actions}` | Risk, CRO | All roles, Dashboard |
| `decision.proposed` | Decision context with status "proposed" | Decision Engine | CEO, Committee members |
| `decision.approved` | Decision context with status "approved" | CEO, Committee | Execution, Portfolio |
| `order.placed` | Execution report (see Capability Matrix) | Execution AI | Portfolio, Risk, Journal |
| `order.filled` | Execution report with fill details | Broker AI | Portfolio, Risk, Dashboard |
| `portfolio.updated` | Portfolio snapshot | Portfolio Manager | CEO, CIO, Dashboard |
| `strategy.decay.detected` | `{strategy_id, metric, old, new, threshold}` | Risk, System | CIO, Research |
| `employee.kpi.updated` | `{agent_id, metric, new_value, trend}` | System (auto) | CEO, HR |
| `incident.reported` | Incident report | DevOps, any | CEO, CTO, War Room |
| `proposal.submitted` | Proposal context | Any AI | CEO, Committee |
| `change.rolled-back` | `{change_id, reason, success}` | Governance | CTO, all affected modules |
| `meeting.scheduled` | Meeting context | CEO, any chair | All attendees |
| `system.self-healed` | `{component, action, result}` | DevOps | CTO, Dashboard |

**Subscribing from any language:**
```python
# Python — subscribe to risk events
import nats

async def main():
    nc = await nats.connect("nats://localhost:4222")
    sub = await nc.subscribe("risk.*")
    
    async for msg in sub.messages:
        event = json.loads(msg.data)
        if event["type"] == "risk.limit.breached":
            print(f"⚠️ RISK BREACH: {event['payload']['metric']}")
            # Take automatic action
            if event["payload"]["severity"] == "critical":
                await nc.publish("risk.safe-mode.activate", json.dumps({
                    "trigger": event["payload"]["metric"],
                    "initiated_by": "auto-subscriber"
                }))
```

---

## 7. Authentication & Security

### API Authentication

```python
# Every API call requires a bearer token
headers = {"Authorization": "Bearer aqios_xxxxxxxxxxxx"}

# Tokens are role-scoped — a Risk Manager token cannot execute trades
# Token types and their scopes:
# - agent_token: scoped to one AI agent's role
# - service_token: full access for inter-module communication
# - founder_token: human owner — can override all restrictions
```

### Permission Levels per Role

| Role | Can Execute Trades? | Can Modify Risk Policy? | Can Approve New AI? | Can Access All Memory? |
|---|---|---|---|---|
| CEO AI | After committee | Propose only | Yes | Yes |
| CIO AI | Via delegation | No | Recommend | Investment data |
| CRO AI | Veto only | Propose only | No | Risk full access |
| CTO AI | No | No | Infrastructure | System data |
| Market Analyst | No | No | No | Market data |
| Risk Manager | Veto only | No | No | Risk + positions |
| Portfolio Mgr | Via delegation | No | No | Portfolio full |
| Execution AI | Execute only | No | No | Orders only |
| Founder | Full override | Full override | Full override | Full access |

### Secrets Management

```yaml
# .secrets.yaml (encrypted — never in git)
api_keys:
  anthropic: "sk-ant-xxxxxxxxxxxxxxxx"
  google: "AIzaxxxxxxxxxxxxxxxx"
  deepseek: "sk-xxxxxxxxxxxxxxxx"
  openai: "sk-xxxxxxxxxxxxxxxx"

# Secrets are loaded at runtime and never exposed to AI agents
# Agents interact through the API, never with raw keys
```

---

## 8. Testing Your Integration

### Health Check

```bash
# Check if the gateway is running
curl http://localhost:8080/health
# → {"status": "ok", "modules": ["kernel", "memory", "risk", "portfolio"], "uptime": "3h12m"}

# Check AI provider connectivity
curl http://localhost:8080/health/providers
# → {"claude": "up", "gemini": "up", "deepseek": "rate_limited", "ollama": "up"}
```

### Smoke Test — Full Decision Pipeline

```python
"""Test the complete decision pipeline:
Market Analysis → Risk Assessment → Portfolio Check → Decision → Execution
"""
import requests
import json

BASE = "http://localhost:8080/api/v1"
TOKEN = "your-test-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Step 1: Analyze market
analysis = requests.post(f"{BASE}/market/analyze", headers=HEADERS, json={
    "symbol": "XAUUSD", "timeframes": ["H1", "H4", "D1"],
    "indicators": ["EMA", "RSI", "VWAP", "ATR", "VOLUME"]
}).json()
print(f"Analysis: {analysis['overall_bias']} (confidence: {analysis['confidence']})")

# Step 2: Assess risk
risk = requests.post(f"{BASE}/risk/assess", headers=HEADERS, json={
    "symbol": "XAUUSD", "side": "buy", "lots": 1.0,
    "account_equity": 10000, "daily_loss": -120
}).json()
print(f"Risk: {risk['risk_level']}, Recommended size: {risk['position_size_recommendation']}")

# Step 3: Check portfolio impact
portfolio = requests.post(f"{BASE}/portfolio/view", headers=HEADERS).json()
print(f"Portfolio: equity={portfolio['total_equity']}, exposure={portfolio['total_exposure']}%")

# Step 4: Run devil's advocate
devil = requests.post(f"{BASE}/decision/devils-advocate", headers=HEADERS, json={
    "proposal": f"BUY XAUUSD {risk['position_size_recommendation']} lots"
}).json()
print(f"Devil's Advocate: survives={devil['survives_scrutiny']}, flaws={len(devil['flaws'])}")

# Step 5: Check constitution
compliance = requests.post(f"{BASE}/governance/check", headers=HEADERS, json={
    "action": "trade",
    "context": {"side": "buy", "lots": risk['position_size_lots']}
}).json()
print(f"Constitution: compliant={compliance['compliant']}")

# Step 6: Make decision
if (analysis['confidence'] > 70 and 
    risk['risk_level'] == 'low' and 
    devil['survives_scrutiny'] and 
    compliance['compliant']):
    print("✅ All checks passed — trade decision approved")
else:
    print("❌ Trade blocked. Reasons:")
    if analysis['confidence'] <= 70: print("  - Low market confidence")
    if risk['risk_level'] != 'low': print("  - Elevated risk level")
    if not devil['survives_scrutiny']: print("  - Failed adversarial review")
    if not compliance['compliant']: print("  - Constitution violation")
```

### Integration Test Suite

```bash
# Run the full integration test suite
pytest tests/integration/ -v

# Expected output:
# tests/integration/test_market_analysis.py::test_full_analysis PASSED
# tests/integration/test_risk_pipeline.py::test_position_sizing PASSED
# tests/integration/test_decision_flow.py::test_committee_vote PASSED
# tests/integration/test_execution.py::test_order_routing PASSED
# tests/integration/test_governance.py::test_proposal_workflow PASSED
# tests/integration/test_knowledge.py::test_rag_query PASSED
# tests/integration/test_simulation.py::test_digital_twin PASSED
```

---

## 9. Troubleshooting

### Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| Provider returns 401 | Invalid API key | Check `config/gateway.yaml` API keys |
| Event bus messages not received | NATS not running | `docker compose up -d nats` |
| Memory search slow | Vector DB index not built | Run `python -m aqios.memory.reindex` |
| Constitution check fails unexpectedly | Policy too restrictive | Check `config/constitution.yaml` |
| Decision engine timeout | Provider latency | Check provider health, set shorter timeout |
| AI agent context too large | Prompt + memory overflow | Reduce context window or switch to larger model |
| Safe mode stuck active | Trigger condition not cleared | Manually run `/api/v1/risk/safe-mode deactivate` |

### Debug Mode

```bash
# Enable verbose logging
export AQIOS_LOG_LEVEL=DEBUG
python -m aqios.gateway --config config/gateway.yaml --debug

# Watch event bus traffic
python -m aqios.tools.event-inspector --subscribe "*"

# Inspect agent state
python -m aqios.tools.agent-inspector --agent "Alice" --show-memory --show-task
```

### Getting Help

```markdown
# AQIOS itself includes a self-help capability:
curl http://localhost:8080/api/v1/system/diagnose
# Returns a diagnostic report of all 26 modules, their status,
# and any configuration issues detected.

# Or ask any AI agent loaded with AQIOS:
"Check the system health and diagnose any issues."
```

---

## Appendix: Integration Checklist

- [ ] **Step 1:** Clone/extract the AQIOS package
- [ ] **Step 2:** Configure AI provider API keys in `config/gateway.yaml`
- [ ] **Step 3:** Start core infrastructure (NATS, Qdrant, PostgreSQL, Redis)
- [ ] **Step 4:** Start the AI Gateway
- [ ] **Step 5:** Verify health endpoint returns `{"status": "ok"}`
- [ ] **Step 6:** Run smoke test on one capability (e.g., market analysis)
- [ ] **Step 7:** Register AI agents with roles from the prompt library
- [ ] **Step 8:** Test the decision pipeline (analysis → risk → execution)
- [ ] **Step 9:** Subscribe to key events (risk alerts, trade executions, etc.)
- [ ] **Step 10:** Deploy custom strategies via the Strategy SDK
- [ ] **Step 11:** Set up governance (constitution, committee, change control)
- [ ] **Step 12:** Enable the self-improvement engine (weekly reviews, evolution)
- [ ] **Step 13:** Run integration test suite
- [ ] **Step 14:** Configure monitoring and alerting
- [ ] **Step 15:** Go live with paper trading first

---

*End of Integration Guide v1.0 — AI Quant Office*
