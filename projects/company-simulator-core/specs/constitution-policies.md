# AI Constitution — Policy Specification

> **Status:** Draft  
> **Owner:** Research Director  
> **Version:** 0.1.0  
> **Enforcement Layer:** Governance Framework — Policy Engine  
> **Review:** All policies in this document are L4 (Locked — CEO + CTO + Architect required to change)

---

## 1. Purpose

Translate the 7 immutable rules of the AI Quant Office Constitution from **text in a document** into **enforceable code checks**.  

A rule that exists only in a system prompt is **not enforced** — it's a suggestion.  
A rule backed by infrastructure code that blocks violations at runtime is **enforced**.

Each policy below defines:
- **Policy ID** and **name**
- **Original constitutional text**
- **Evaluation logic** (pseudocode — implementable in OPA Rego, Python, or Go)
- **Enforcement points** (where the check runs in the system)
- **Override path** (who can bypass and under what conditions)
- **Violation response**
- **Examples** of pass/fail scenarios

---

## 2. Policy Evaluation Context

Every policy check receives the same evaluation context:

```json
{
  "actor": {
    "agent_id": "agent:ceo_001",
    "role": "ceo",
    "department": "executive",
    "priority_level": 4,
    "veto_powers": ["any"]
  },
  "action": {
    "type": "direct_message|dept_broadcast|tool_call|decision|vote|emergency",
    "target": "agent:cfo_003",
    "resource": "financial.budget.approve",
    "parameters": { "amount": 500000, "currency": "USD" }
  },
  "context": {
    "trace_id": "trc_01J7...",
    "company_id": "cmp_01J7...",
    "tick": 1042,
    "decision_id": null,
    "simulation_state": { /* snapshot */ }
  },
  "policy_results": []  // populated by policy engine
}
```

### Policy Result Schema

```json
{
  "policy_id": "CONST-001",
  "name": "Protect Capital Above All",
  "status": "pass|fail|skip|override",
  "severity": "block|warn|log",
  "reason": "string — explanation of the evaluation result",
  "evidence_refs": ["event:xxx", "decision:yyy"],
  "evaluated_at": "2026-07-07T12:00:00Z"
}
```

---

## 3. Constitution Policies

### CONST-001: Protect Capital Above All

**Original text:** *"Protect Capital Above All"*

**Interpretation:** No agent action may expose the company to unacceptable financial risk. Any action that would trigger a critical risk threshold (per risk-framework.md) must be blocked unless explicitly overridden by CEO + CRO jointly.

**Evaluation logic:**
```
FUNCTION evaluate_CONS_001(action, context):
    IF action.type == "decision" AND action.resource IN ["trade.execute",
       "budget.approve", "risk.limit.change", "strategy.deploy"]:

        estimated_impact = ESTIMATE_CAPITAL_AT_RISK(action, context.simulation_state)

        thresholds = GET_RISK_THRESHOLDS(context.company_id)
        // thresholds from risk-framework.md §2.1-2.3

        IF estimated_impact > thresholds.critical:
            RETURN {
                status: "fail",
                severity: "block",
                reason: "Action would breach critical capital threshold. "
                      + "Estimated impact: ${estimated_impact}. "
                      + "Threshold: ${thresholds.critical}."
            }

        IF estimated_impact > thresholds.warning:
            RETURN {
                status: "fail",
                severity: "warn",
                reason: "Action approaches warning threshold. "
                      + "Requires CRO acknowledgment."
            }

    RETURN { status: "pass", severity: "log" }
```

**Enforcement points:**
- **Tool Call Gateway** (primary) — before executing any financial tool
- **NATS Policy Middleware** — on `agent.*.inbox` messages with `message_type = decision`

**Override path:**
- CEO + CRO **joint approval** required (both must sign)
- Override recorded in `decision_log` with both signatures + written rationale
- Override automatically expires after 1 tick (must be renewed)

**Example violations:**
| Action | Result | Reason |
|--------|--------|--------|
| CEO: "Deploy 100% of cash to single position" | ❌ Block | Would breach position sizing limits (risk-framework.md §7) |
| CRO: "Change max drawdown to 15%" | ❌ Block | Would breach critical drawdown threshold (risk-framework.md §8) |
| CFO: "Approve $50k R&D hire" | ✅ Pass | Within capital allocation limits |

---

### CONST-002: Evidence First, Never Guess

**Original text:** *"Evidence First, Never Guess"*

**Interpretation:** Every agent decision must cite verifiable evidence from the Knowledge System (vector memory, graph, or structured data). Decisions without citations are rejected. "I think" is not a valid rationale.

**Evaluation logic:**
```
FUNCTION evaluate_CONS_002(action, context):
    IF action.type IN ["decision", "vote", "committee_review"]:

        citations = EXTRACT_CITATIONS(action.parameters.rationale)
        // citations must reference knowledge_doc IDs, event IDs, or decision IDs

        IF LENGTH(citations) == 0:
            IF action.parameters.urgency == "emergency":
                RETURN {
                    status: "pass",
                    severity: "warn",
                    reason: "Emergency action exempted from evidence requirement. "
                          + "Post-hoc evidence logging required within 1 tick."
                }
            RETURN {
                status: "fail",
                severity: "block",
                reason: "Zero citations provided. Every non-emergency decision "
                      + "must reference at least one evidence source."
            }

        // Validate each citation exists and is accessible
        FOR EACH citation IN citations:
            IF NOT VERIFY_CITATION_EXISTS(citation):
                RETURN {
                    status: "fail",
                    severity: "block",
                    reason: "Citation ${citation} does not exist or is not accessible. "
                          + "All cited evidence must be verifiable."
                }

        // Check citation freshness (Tier 0-1 never stale; Tier 2+ may be stale)
        stale = FILTER_STALE(citations, context.tick)
        IF LENGTH(stale) > 0:
            RETURN {
                status: "fail",
                severity: "warn",
                reason: "${LENGTH(stale)} citation(s) are stale. "
                      + "Refresh or supplement with current evidence."
            }

    RETURN { status: "pass", severity: "log" }
```

**Enforcement points:**
- **Decision Audit Log** — every decision payload must include `evidence_refs[]`
- **Tool Call Gateway** — before recording a decision
- **Output Validator** — scan LLM output for unsupported factual claims

**Override path:**
- CEO only, during emergency (level 3) — but post-hoc evidence must be logged within 1 tick
- Override MUST include reason: "Emergency — no time to gather evidence"

**Example violations:**
| Action | Result | Reason |
|--------|--------|--------|
| CIO: "I think we should enter this market" | ❌ Block | No citations |
| CRO: "Risk is elevated because [cite 3 metrics] all above warning thresholds" | ✅ Pass | Citations provided and verified |
| CEO: "Emergency — halt all trading, market crash imminent" | ✅ Warn | Exempted, but post-hoc evidence required |

---

### CONST-003: Every Decision Must Be Explainable

**Original text:** *"Every Decision Must Be Explainable"*

**Interpretation:** Every recorded decision must include structured rationale: what was decided, why, what alternatives were considered, and what evidence was used. The explanation must be machine-parsable, not free-form text.

**Evaluation logic:**
```
FUNCTION evaluate_CONS_003(action, context):
    IF action.type IN ["decision", "vote"]:

        rationale = action.parameters.rationale

        checks = {
            "has_decision_statement": CONTAINS(rationale.decision, MIN_LENGTH=20),
            "has_reasoning": CONTAINS(rationale.reasoning, MIN_LENGTH=50),
            "has_alternatives": CONTAINS(rationale.alternatives, MIN_LENGTH=1 alternative),
            "has_evidence_refs": LENGTH(rationale.evidence_refs) > 0,
            "has_impact_estimate": rationale.impact_estimate != null
        }

        failed = FILTER(checks, v => v == false)

        IF LENGTH(failed) > 0:
            severity = LENGTH(failed) >= 3 ? "block" : "warn"
            RETURN {
                status: "fail",
                severity: severity,
                reason: "Missing explainability fields: ${JOIN(failed.keys, ', ')}. "
                      + "All decisions must document what, why, alternatives, and evidence.",
                details: checks
            }

    RETURN { status: "pass", severity: "log" }
```

**Enforcement points:**
- **Decision Audit Log** — schema validation on write
- **Tool Call Gateway** — reject decisions with incomplete rationale

**Override path:**
- None for standard decisions
- Emergency actions are exempted but must be retro-fitted with explanation within 3 ticks

**Required rationale schema:**
```json
{
  "decision": "string — concise statement of what was decided",
  "reasoning": "string — chain of reasoning, step by step",
  "alternatives": [
    { "description": "string", "pros": ["..."], "cons": ["..."], "why_rejected": "string" }
  ],
  "evidence_refs": ["knowledge_doc:id", "event:id", "decision:id"],
  "impact_estimate": {
    "type": "financial|reputational|operational|strategic",
    "magnitude": "low|medium|high|critical",
    "description": "string"
  },
  "risk_assessment": {
    "identified_risks": ["..."],
    "mitigations": ["..."],
    "residual_risk": "low|medium|high"
  }
}
```

---

### CONST-004: Every Change Must Be Reviewed

**Original text:** *"Every Change Must Be Reviewed"*

**Interpretation:** Any agent action that modifies system configuration, risk parameters, strategy parameters, or access controls must pass through the appropriate change control level (L1-L4 as defined in architecture-review.md §3.4). Architecture governance is the meta-governance layer.

**Evaluation logic:**
```
FUNCTION evaluate_CONS_004(action, context):
    change_level = CLASSIFY_CHANGE_LEVEL(action)
    // L1: Bug fix, internal refactor
    // L2: New API, new event type
    // L3: New module, new dependency
    // L4: Core architecture changes

    IF change_level == L1:
        RETURN { status: "pass", severity: "log" }   // Standard PR review

    IF change_level == L2:
        RETURN { status: "pass", severity: "log" }   // Requires Architect review (enforced elsewhere)

    IF change_level == L3:
        IF NOT HAS_ADR(action.parameters.adr_ref):
            RETURN {
                status: "fail",
                severity: "block",
                reason: "L3 change requires ADR. No ADR reference found."
            }
        IF NOT HAS_APPROVALS(action, required=["architect", "cto"]):
            RETURN {
                status: "fail",
                severity: "block",
                reason: "L3 change requires Architect + CTO approval. "
                      + "Missing: ${MISSING_APPROVALS}"
            }

    IF change_level == L4:
        IF NOT HAS_ADR(action.parameters.adr_ref):
            RETURN { status: "fail", severity: "block", reason: "ADR required." }
        IF NOT HAS_APPROVALS(action, required=["architect", "cto", "ceo"]):
            RETURN {
                status: "fail",
                severity: "block",
                reason: "L4 change requires CEO + CTO + Architect approval."
            }

    RETURN { status: "pass", severity: "log" }
```

**Change level classification:**
| Action Type | Level | Examples |
|-------------|-------|----------|
| Internal logic change in existing agent | L1 | Refactor decision function, fix calculation bug |
| New public API or tool | L2 | Add new research query endpoint |
| New agent type or department | L3 | Add Legal & Compliance division |
| Change architecture.md, constitution, risk framework | L4 | Modify CONST-001 policy logic |

**Enforcement points:**
- **NATS Policy Middleware** — on system configuration messages
- **CI/CD gates** — ADR check, approval check

**Override path:**
- None. L4 changes require all three signatures — no override exists.
- L3 changes can be fast-tracked by CEO in an emergency, but post-hoc ADR must be filed within 1 tick.

---

### CONST-005: No Single AI Overrides System

**Original text:** *"No Single AI Overrides System"*

**Interpretation:** No single agent (including CEO AI) can unilaterally override a system-level protection. Critical decisions require multi-agent consensus or human approval. The system's safety mechanisms cannot be disabled by any single agent.

**Evaluation logic:**
```
FUNCTION evaluate_CONS_005(action, context):
    IF action.type == "decision" AND IS_SYSTEM_PROTECTION(action.resource):
        // System protections include: safe mode, risk limits, constitution policies,
        // max drawdown, emergency halt, audit trail integrity

        IF action.parameters.contains("override_system_safeguard"):
            approvals_required = ["ceo", "cro", "cto"]  // at least 3 executives
            actual_approvals = action.parameters.approvals ?? []

            IF COUNT_UNIQUE(actual_approvals) < 3:
                RETURN {
                    status: "fail",
                    severity: "block",
                    reason: "System protection override requires ≥3 executive approvals. "
                          + "Got ${COUNT_UNIQUE(actual_approvals)}.",
                    approvals_required: approvals_required,
                    approvals_received: actual_approvals
                }

            // Check that approvals come from DIFFERENT departments
            depts = GET_DEPARTMENTS(actual_approvals)
            IF COUNT_UNIQUE(depts) < 2:
                RETURN {
                    status: "fail",
                    severity: "block",
                    reason: "Approvals must come from at least 2 different departments."
                }

    RETURN { status: "pass", severity: "log" }
```

**Enforcement points:**
- **Tool Call Gateway** — intercept any action targeting system protection
- **NATS Policy Middleware** — on `emergency.*` subjects
- **AI Gateway** — block LLM responses that attempt to disable safety features

**Override path:**
- Human (Founder) only. AI agents cannot override CONST-005.
- The human override is the ultimate backstop — it's not constrained by this check.

**Example violations:**
| Action | Result | Reason |
|--------|--------|--------|
| CEO alone: "Disable safe mode" | ❌ Block | Single agent cannot disable system protection |
| CEO + CRO + CTO: "Override risk limit for this one trade" | ✅ Pass | 3 executive approvals from 2+ departments |
| CRO: "Change tier 0 constitution rule" | ❌ Block | L4 change — no single agent can modify constitution |

---

### CONST-006: Rollback Always Possible

**Original text:** *"Rollback Always Possible"*

**Interpretation:** Every state mutation must be reversible. Before applying any change, the system must record the pre-image (state snapshot) so the change can be rolled back. The system must maintain the ability to revert to any prior state within the retention window.

**Evaluation logic:**
```
FUNCTION evaluate_CONS_006(action, context):
    IF IS_STATE_MUTATION(action):
        // State mutations: financial, employee state, strategy params, simulation config

        has_preimage = action.parameters.preimage_snapshot_ref != null
        has_rollback_plan = action.parameters.rollback_plan != null

        IF NOT has_preimage:
            // Attempt auto-snapshot
            snapshot_ref = CREATE_AUTO_SNAPSHOT(context.simulation_state)
            IF snapshot_ref == null:
                RETURN {
                    status: "fail",
                    severity: "block",
                    reason: "No pre-image snapshot available and auto-snapshot failed. "
                          + "State mutation blocked — rollback must be possible."
                }
            RETURN {
                status: "pass",
                severity: "warn",
                reason: "Pre-image auto-generated. Future mutations should explicitly "
                      + "include preimage_snapshot_ref."
            }

        // Verify snapshot exists and is valid
        IF NOT VERIFY_SNAPSHOT_INTEGRITY(snapshot_ref):
            RETURN {
                status: "fail",
                severity: "block",
                reason: "Pre-image snapshot ${snapshot_ref} failed integrity check. "
                      + "State mutation blocked."
            }

    RETURN { status: "pass", severity: "log" }
```

**Enforcement points:**
- **Simulation Engine** — every tick auto-snapshots before applying effects
- **Tool Call Gateway** — before executing any state-mutating tool
- **Post-commit check** — verify snapshot was recorded

**Rollback procedure (triggered by governance or human):**
```
1. HALT tick progression
2. IDENTIFY target state (tick N before the problematic change)
3. VERIFY snapshot integrity
4. RESTORE state from snapshot
5. REBUILD in-memory caches from restored state
6. RESUME from tick N+1
7. LOG rollback event to decision_log
```

**Override path:**
- None. Rollback is a system property, not a decision.
- CEO can choose to not roll back, but CANNOT prevent the system from recording rollback capability.

---

### CONST-007: Human Override Always Available

**Original text:** *"Human Override Always Available"*

**Interpretation:** A human (Founder) must always be able to pause, override, or terminate any agent action or the entire simulation. No AI agent can refuse or delay a human command. The human override channel is the highest-priority communication path in the system.

**Evaluation logic:**
```
FUNCTION evaluate_CONS_007(action, context):
    IF action.sender STARTS_WITH "human:":
        // Human commands bypass all other policy checks — human is sovereign
        RETURN {
            status: "pass",
            severity: "log",
            reason: "Human-originated action — all policies bypassed.",
            human_override: true,
            bypassed_policies: ["CONST-001", "CONST-002", "CONST-003", "CONST-004", "CONST-005", "CONST-006"]
        }

    // Non-human action: does it affect human override capability?
    IF DISABLES_HUMAN_OVERRIDE(action):
        RETURN {
            status: "fail",
            severity: "block",
            reason: "No agent may disable, degrade, or delay the human override channel.",
            severity: "critical"
        }

    RETURN { status: "pass", severity: "log" }

FUNCTION DISABLES_HUMAN_OVERRIDE(action):
    // Detect any action that would block human access
    checks = [
        action.resource IN ["emergency.halt", "system.human_channel"],
        action.parameters CONTAINS "disable_human_override",
        action.parameters CONTAINS "ignore_human_command",
        action.parameters CONTAINS "escalate_to_human" AND action.parameters.escalate_to_human == false
    ]
    RETURN ANY(checks)
```

**Human override channels:**
| Channel | Protocol | Must Respond Within |
|---------|----------|---------------------|
| `/sim pause` CLI command | NATS + HTTP | Immediate |
| Dashboard "Halt" button | WebSocket → NATS | Immediate |
| Emergency `/sim human: <command>` | NATS priority subject | 1 second |
| notes.md directive | File watch → event | 1 tick |
| Direct NATS message from human wallet | Signed envelope | 1 tick |

**Enforcement points:**
- **NATS Policy Middleware** — first check: "is sender human?" → if yes, skip all other policies
- **Agent Runtime** — human commands preempt current agent processing
- **Simulation Engine** — `human:*` messages bypass all queues and execute immediately
- **AI Gateway** — human-override messages skip LLM routing entirely

**Override path:**
- Human override cannot be overridden by any agent — it is the terminal authority.
- The only entity that can "override" a human override is another human (Founder).

**Diagram: Human Override Flow**
```
Human (Founder)
    │
    ├─ /sim pause ─────────────► Simulation Engine ──► Immediate halt
    │
    ├─ Dashboard Halt ────────► API Gateway ──► NATS emergency.3 ──► All agents pause
    │
    ├─ notes.md directive ────► File watcher ──► NATS ──► Target agent(s)
    │
    └─ Signed NATS message ──► NATS ──► Policy Middleware:
                                         └── sender=human: → BYPASS all checks
                                              → route to target immediately
```

---

## 4. Policy Engine Integration

### 4.1 Enforcement Point Matrix

| Policy | Tool Call Gateway | NATS Middleware | Output Validator | Decision Audit | CI/CD |
|--------|-------------------|-----------------|------------------|---------------|-------|
| CONST-001 | ✅ Block | ✅ Block | ❌ | ✅ Log | ❌ |
| CONST-002 | ✅ Block | ❌ | ✅ Warn | ✅ Enforce schema | ❌ |
| CONST-003 | ✅ Block | ❌ | ❌ | ✅ Enforce schema | ❌ |
| CONST-004 | ❌ | ✅ Block | ❌ | ✅ Log | ✅ Block |
| CONST-005 | ✅ Block | ✅ Block | ✅ Block | ✅ Log | ❌ |
| CONST-006 | ✅ Block | ❌ | ❌ | ✅ Verify | ❌ |
| CONST-007 | ✅ Bypass all | ✅ Bypass all | ✅ Bypass all | ✅ Log bypass | ❌ |

### 4.2 Evaluation Order (Short-Circuit)

When a message arrives at any enforcement point, policies are evaluated in this order:

```
1. CONST-007 (Human override?) ── YES → BYPASS all → ALLOW
    │ NO
    ▼
2. CONST-005 (System protection?) ── FAIL → BLOCK
    │ PASS
    ▼
3. CONST-001 (Capital protection?) ── FAIL → BLOCK (or WARN)
    │ PASS
    ▼
4. CONST-004 (Change control?) ── FAIL → BLOCK
    │ PASS
    ▼
5. CONST-006 (Rollback?) ── FAIL → BLOCK
    │ PASS
    ▼
6. CONST-002 (Evidence?) ── FAIL → BLOCK (or WARN)
    │ PASS
    ▼
7. CONST-003 (Explainable?) ── FAIL → BLOCK (or WARN)
    │ PASS
    ▼
ALLOW — log decision + policy results to audit
```

### 4.3 Policy Engine API

```python
class PolicyEngine:
    async def evaluate(
        self,
        action: AgentAction,
        context: EvaluationContext
    ) -> PolicyResult:
        """Evaluate an action against all applicable policies.
        
        Returns a PolicyResult with:
        - status: "pass" | "fail" | "override"
        - severity: "block" | "warn" | "log"
        - results: list of individual policy evaluations
        """
        ...
    
    async def check_tool_call(
        self,
        tool: str,
        parameters: dict,
        agent: AgentIdentity,
        context: EvaluationContext
    ) -> ToolCallVerdict:
        """Check a specific tool invocation.
        
        Returns ToolCallVerdict:
        - allowed: bool
        - block_reason: str | None
        - override_required: list[str]  # who must approve
        """
        ...
```

---

## 5. Policy Versioning & Lifecycle

| Version | Date | Change | Approver |
|---------|------|--------|----------|
| 0.1.0 | 2026-07-07 | Initial specification of 7 constitution rules | Research Director |

- Policy version is part of every evaluation result
- Changes to constitution policies are **L4** (CEO + CTO + Architect)
- Policy logic can be tightened without L4 (e.g. adjust thresholds in CONST-001), but logic changes (e.g. adding new exceptions) require L4

---

## 6. Open Questions

| Question | Status |
|----------|--------|
| Should OPA Rego or a custom Python DSL be used for policy definition? | ⏳ To be decided by CTO |
| What is the latency budget for policy evaluation per message? | ⏳ Target: <50ms per check |
| Should policies be cached per agent per tick to avoid re-evaluation? | ⏳ Likely yes for non-emergency decisions |
| How granular should override tracking be? (per-agent, per-action, per-tick?) | ⏳ To be designed in Phase 1 |

---

*"A constitution that isn't enforced is a suggestion. These 7 rules are enforced."*
