---
name: "ai-quant-office-knowledge-domains"
description: "Complete knowledge decomposition of AI Quant Office OS"
type: "knowledge-package"
version: "1.0.0"
tags: ["ai-office", "quant", "multi-agent", "governance", "plugin-sdk"]
ai_compatible: ["chatgpt", "claude", "gemini", "deepseek", "qwen"]
---

# AI Quant Office OS — Knowledge Domains

## Domain 1: AIOS Core
**Components:** AI Identity, Lifecycle, Permission, Role/Department, Presence, Session, Auth, Interrupt
**Dependencies:** None (root)

## Domain 2: Communication Engine
**Modes:** Chat, Meeting, Broadcast, Debate, Committee, DM, Mention, Channel, Thread, Town Hall
**Priorities:** Emergency > High > Normal > Low
**Dependencies:** D1

## Domain 3: Company Memory
**Types:** Short/Long-term, Episodic, Semantic, Procedural, Team, Company
**Capabilities:** Compression, Archive, Replay, Search, Timeline
**Dependencies:** D1, D5

## Domain 4: Task System
**Workflow:** Created -> Assigned -> In Progress -> Review -> Approved -> Done
**Dependencies:** D1

## Domain 5: Knowledge OS
**Tiers:** T0 Immutable, T1 Official Docs, T2 Internal, T3 External, T4 Community
**Capabilities:** Wiki, Docs, Library, Citation, Version, Fact Check, Search, RAG, Knowledge Graph
**Dependencies:** D1, D3

## Domain 6: AI Gateway
**Providers:** OpenAI, Anthropic, Google, xAI, DeepSeek, Mistral, Qwen, Ollama, LM Studio, vLLM, OpenRouter, Custom
**Features:** API Rotation, Fallback, Cost Control, Token Tracking, Health Check (60s)
**Dependencies:** D1

## Domain 7: AI Employee System
**Features:** Resume, Skills, KPI, Reputation, Budget, Performance, Cert, Promotion, Retirement, Recruitment, Mentor
**Departments:** CEO -> CIO/CRO/CFO/CTO/COO/Research/Knowledge/HR/Legal
**Dependencies:** D1, D6

## Domain 8: Company Governance
**Constitution:** 7 Articles (Protect Capital, Evidence First, Never Direct Modify, Review, Explain, Source, No Override)
**Change Levels:** Auto L1 -> Review L2 -> Owner L3 -> Locked L4
**Workflow:** Proposal -> Evidence -> Committee -> Owner -> Canary -> Production -> Audit
**Dependencies:** D1, D5, D4

## Domain 9: Plugin SDK
**Types:** AI, Department, Tool, Knowledge Pack, Workflow, UI Widget
**Marketplace:** Install, Update, Disable, Rollback
**Dependencies:** D1

## Domain 10: Workflow Engine
**Features:** Visual drag-drop, branching, parallel, hot reload, versioning, canary
**Dependencies:** D1, D2, D4

## Domain 11: Company Dashboard
**Views:** Home, Market, AI Center, Broker, Strategy, Portfolio, Journal, 3D Office Map
**Transparency:** Basic, Advanced, Developer
**Dependencies:** All

## Domain 12: AI Developer Kit
**Flow:** Template -> Configure -> Assign -> Budget -> Go Live
**Dependencies:** D1, D7, D9

## Domain 13: Strategy Engine
**Lifecycle (13 stages):** Idea->Research->Coding->Backtest->WalkForward->Optimization->Committee->Sandbox->Shadow->Canary->Production->Monitor->Retirement
**SDK:** initialize(), analyze(), score(), entry(), exit(), manage(), cleanup()
**Features:** Genome DNA, Ranking, Router, Dynamic Allocation, Kill Switch, Auto Retirement
**Dependencies:** D6, D15, D17

## Domain 14: Decision Engine
**Consensus:** Weighted Voting, Confidence, Committee, Devil Advocate
**Dependencies:** D13, D15, D16, D2, D6

## Domain 15: Risk Engine
**12 Dimensions:** Infrastructure, Internet, Broker, FlashCrash, News, BlackSwan, Liquidity, Correlation, AI Calibration, Strategy Decay, Human Override, Audit
**Risk Committee:** Pre-order checks (exposure, DD impact, consec losses, vol)
**Dependencies:** D16, D14, D19

## Domain 16: Portfolio Engine
**Features:** Multi-asset/broker/account, Correlation, Exposure, Profit Lock, Smart Close, Scenario Engine, Universal Stop
**Constitution:** Max DD 8%, Daily Risk ≤2%, Correlation ≤0.75, Margin ≥300%
**Dependencies:** D15, D14

## Domain 17: Money Management
**8 Layers:** Risk Budget, DynamicSizing, Exposure, DailyLimit, DD Protection, Recovery, AdaptiveRR, CapitalGrowth
**Models:** Kelly, Ruin Probability, Equity Curve, Risk Score
**Dependencies:** D15, D16

## Domain 18: Execution Engine
**Architecture:** Strategy->Risk->MM->Compliance->BrokerAdapter->Broker
**Features:** Smart Router, Broker Abstraction, SL/TP, Trailing, Partial Close
**Compliance:** Hedging, FIFO, MaxPos, MaxLot, StopLevel, Hours
**Dependencies:** D15, D17, D21

## Domain 19: Broker Intelligence
**Profile:** Spread, Slippage, Requote, Execution, Fill, Commission, Swap per broker/session/symbol
**Cost:** Total = Spread+Commission+Swap+Slippage, Net<Min->Skip
**Dependencies:** D18, D15

## Domain 20: Market Regime Engine
**Regimes:** Strong/Weak Trend, Range, Expansion, Compression, Breakout, MeanRev, News, High/Low Vol
**Adaptive:** Trend->H4/H1 weight. Range->M15/M5. News->raise threshold
**Dependencies:** D14, D13

## Domain 21: Research & AI Lab
**Pipeline:** Paper->Summarize->Extract->Benchmark->Implement->Backtest->WalkForward->Stress->Committee->KB
**University:** Library, Research Center, Wiki, Lab, Mentor
**Dependencies:** D5, D6, D13

## Domain 22: Monitoring
**System:** CPU/RAM/GPU/Disk/Token. **Trading:** WinRate/RR/DD/Sharpe. **AI:** Hallucination/Accuracy/Cost
**Features:** Agent Inspector, Time Machine, Health (60s), Drift Detection, Auto-heal
**Dependencies:** All

## Domain 23: Simulation
**Pipeline:** Unit->Integration->Replay->Sandbox->Shadow->Canary->Production
**Types:** Historical Replay, Scenario Generator, Digital Twin, Monte Carlo, Stress, WalkForward
**Dependencies:** D4, D13, D5

## Domain 24: Evolution
**Weekly:** What went well/failed/improve? Training? Hire? Retire? Change workflow?
**Levels:** Auto L1, Review L2, Owner L3, Locked L4
**Dependencies:** D7, D8, D13

## Domain 25: AI Culture
**Values:** Protect Capital, Evidence First, Never Guess, Explain Everything
**Personalities:** Conservative, Bold, Experimental, Big Picture, By-the-book
**Dependencies:** D1, D2

## Domain 26: UX & Design
**Modes:** Basic, Advanced, Developer. **Platforms:** Desktop, Mobile, Telegram, Voice
**Dependencies:** D11

## Dependency Graph
    AIOS Core(D1)
     /            v          v
 Comm(D2)  AI Gateway(D6)
    |          |
    v          v
 Memory(D3) Employee(D7)
    |          |
    v          v
 KnowOS(D5)<-Govern(D8)
    |          |
    v          v
 Task(D4)  Plugin(D9)
    |          |
    v          v
 Workflow(D10) DevKit(D12)
    |
    v
 Quant Layer(D13-D24)
    |
    v
 Dashboard(D11)+UX(D26)
