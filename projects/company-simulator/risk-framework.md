# Risk Framework — Company Simulator

> Document owner: **Risk Analyst**
> Version: 1.0
> Last updated: 2026-07-07

---

## 1. Purpose & Scope

This framework defines:

- **Risk criteria** the Risk Analyst monitors continuously (both in-game and system-level).
- **Thresholds & triggers** that escalate to alerts, safe mode, or emergency halt.
- **Procedures** when a risk breach is detected.
- **Recovery & post-mortem** workflow.

It applies across all simulation runs and all AI agent activity within the simulator. Every simulated company inherits this baseline; per-run risk parameters may tighten but never loosen below these floors.

---

## 2. Risk Categories & Criteria

### 2.1 Financial Risks (In-Simulation)

| Risk | Metric | Warning Threshold | Critical Threshold | Frequency |
|------|--------|-------------------|-------------------|-----------|
| **Cash runway** | Months of operating expenses covered by liquid reserves | < 6 months | < 3 months | Every tick |
| **Burn rate spike** | MoM change in net cash burn | +50% vs 3‑month avg | +100% vs 3‑month avg | Every tick |
| **Revenue concentration** | % of revenue from single customer | > 40% | > 60% | Monthly |
| **Debt service ratio** | (Interest + principal) / Operating income | > 35% | > 50% | Every tick |
| **Margin erosion** | Gross margin drop vs trailing 3‑month avg | -10 pp | -20 pp | Monthly |
| **Liquidity crunch** | Current ratio (CA / CL) | < 1.5 | < 1.0 | Every tick |

### 2.2 Operational Risks (In-Simulation)

| Risk | Metric | Warning Threshold | Critical Threshold | Frequency |
|------|--------|-------------------|-------------------|-----------|
| **Production bottleneck** | Capacity utilisation vs sustainable cap | > 85% for 3+ ticks | > 95% sustained | Every tick |
| **Key‑person dependency** | Single employee responsible for > 30% of critical output | Flagged | + no backup identified | Quarterly |
| **Attrition spike** | Voluntary turnover rate (annualised) | > 20% | > 35% | Monthly |
| **Supply chain concentration** | % of key input from single supplier | > 50% | > 75% | Monthly |
| **Inventory imbalance** | Days of inventory outstanding (DIO) | > 90 or < 15 | > 150 or < 5 | Monthly |
| **Quality incidents** | Defect / return rate | > 5% | > 12% | Every tick |

### 2.3 Market & Competitive Risks (In-Simulation)

| Risk | Metric | Warning Threshold | Critical Threshold | Frequency |
|------|--------|-------------------|-------------------|-----------|
| **Market share loss** | QoQ market share change | -15% | -30% | Quarterly |
| **Price war margin** | Avg. selling price vs industry avg | < 90% | < 75% | Monthly |
| **Regulatory shift** | New compliance cost as % of revenue | > 3% projected | > 8% projected | On event |
| **Demand cliff** | Revenue drop vs forecast | -25% in one tick | -40% in one tick | Every tick |
| **Competitive entry** | New competitor with > 5% share in core segment | Detect | Detect + losing share to them | On event |

### 2.4 System & Data Integrity Risks (Real)

| Risk | Metric | Warning Threshold | Critical Threshold | Frequency |
|------|--------|-------------------|-------------------|-----------|
| **Simulation drift** | Deterministic replay diverges from recorded state | Any divergence detected | — | After every tick |
| **Agent anomaly** | AI agent produces out-of-distribution decision | ≥ 1 flagged | ≥ 3 agents flagged same tick | Every tick |
| **Data corruption** | Checksum mismatch on persisted state | Single mismatch | ≥ 2 mismatches | On save/load |
| **Tick timeout** | Simulation tick exceeds max wall‑clock | > 2× baseline | > 5× baseline | Every tick |
| **Memory leak** | Process RSS growth across ticks | +10% tick‑over‑tick, 5 consecutive | +25% in single tick | Every tick |
| **State inconsistency** | Cross‑entity invariant broken (e.g. Σ assets ≠ Σ liabilities + equity) | Any breach | Same breach across 2+ ticks | Every tick |
| **Agent loop detection** | Agent repeats same decision pattern > N consecutive ticks | > 5 repeats | > 10 repeats | Every tick |

---

## 3. Safe Mode Triggers

When **any** of the following fires, the system enters **Safe Mode** — tick progression pauses, write operations are blocked, and a full diagnostic snapshot is taken before any recovery action.

### 3.1 Automatic Triggers

| ID | Trigger | Rationale |
|----|---------|-----------|
| SM‑01 | Any **Critical** financial threshold breached | Company could enter death spiral; manual override required |
| SM‑02 | ≥ 2 Critical thresholds of any type breached simultaneously | Systemic cascading risk |
| SM‑03 | Data integrity mismatch (any Critical-level) | State cannot be trusted — freeze before corruption spreads |
| SM‑04 | Agent loop detection at Critical level (10+ repeats) | Agent stuck or gamed the sim; halt to inspect |
| SM‑05 | Simulation drift detected | Replay safety net triggered — state no longer reproducible |
| SM‑06 | Tick timeout > 5× baseline consecutively | Engine or agent infrastructure degraded |
| SM‑07 | Memory leak at Critical threshold | Process health at risk |

### 3.2 Manual Triggers (CEO / Admin)

| ID | Trigger | Action |
|----|---------|--------|
| SM‑08 | CEO calls `/sim pause` | Immediate safe‑mode entry, no threshold needed |
| SM‑09 | Manual freeze via dashboard button | Same as SM‑08 |
| SM‑10 | Post‑mortem override | CEO can keep simulation in safe mode after review to prevent re‑entry |

### 3.3 Safe Mode Behaviour

| Aspect | Behaviour |
|--------|-----------|
| **Tick engine** | Paused — no new events processed |
| **Agent writes** | Blocked — agents become read‑only |
| **User reads** | Fully available — dashboard, logs, diagnostics |
| **Snapshot** | Automatic full state dump before any mutation |
| **Alert** | All active offices pinged with risk summary |
| **Exit** | Only via CEO explicit command `/sim resume` after review |

---

## 4. Alerting & Escalation Levels

| Level | Label | Response Time | Who Notified | Action |
|-------|-------|---------------|-------------|--------|
| L1 | **Info** | End of tick | Risk Analyst log | Logged; no action |
| L2 | **Watch** | Within 1 tick | Risk Analyst | Analyst reviews and may tighten monitoring |
| L3 | **Warning** | Immediate | Risk Analyst + CEO | Analyst recommends action; CEO decides |
| L4 | **Critical** | Immediate + halt | All offices + CEO | Auto safe‑mode unless overridden; CEO must acknowledge |
| L5 | **System Emergency** | Immediate + full freeze | All offices + CEO | Safe mode + data dump; CEO + Analyst joint review |

---

## 5. Procedures

### 5.1 On Risk Breach (Warning or above)

```
1. DETECT   — Risk Analyst receives alert with breach details + snapshot.
2. TRIAGE   — Within 1 tick: classify severity, check for concurrent breaches.
3. NOTIFY   — Push alert to CEO via office notes.md + direct message.
4. DIAGNOSE — Pull current state, trace root cause (runway calc, supplier chain, etc.).
5. RECOMMEND— Propose corrective action(s) ranked by impact/effort.
6. EXECUTE  — CEO approves action; implement in simulation.
7. VERIFY   — Confirm metric returns below warning threshold within 2 ticks.
8. LOG      — Append to risk‑event log (see §6).
```

### 5.2 On Safe Mode Entry

```
1. FREEZE       — Tick engine stops; snapshot written atomically.
2. DIAGNOSE     — Full system health check + state verification.
3. BREACH REPORT— Risk Analyst writes structured report (see §6 template).
4. PRESENT      — Send to CEO with recommended next steps.
5. RESOLVE      — CEO either:
                  a) Corrects state and resumes (`/sim resume`)
                  b) Rolls back to last known good snapshot
                  c) Aborts simulation run entirely
6. POST-MORTEM  — Within 24h: root‑cause analysis, framework update if needed.
```

### 5.3 On System Emergency (L5)

Same as safe‑mode procedure, plus:

- **All** agents across all offices receive freeze signal.
- CEO and Risk Analyst hold synchronous review before any resume.
- If data corruption is confirmed, **do not resume** — roll back to last clean snapshot.
- Framework version is bumped and diff is communicated to all offices.

---

## 6. Risk Event Log

Every breach (Watch and above) is recorded. Each entry follows this schema:

```json
{
  "id": "RISK-20260707-001",
  "timestamp": "2026-07-07T14:30:00Z",
  "tick": 142,
  "company": "SimCo Alpha",
  "risk": "cash_runway",
  "level": "Critical",
  "metric": 2.1,
  "threshold": 3.0,
  "snapshot_ref": "snapshots/20260707_143000_state.json",
  "trigger": "SM-01",
  "safe_mode": true,
  "root_cause": "Overinvestment in R&D without revenue milestone",
  "action_taken": "Frozen hiring + divested non‑core unit",
  "resolved": true,
  "resolved_at": "2026-07-07T15:15:00Z",
  "verified_by": "Risk Analyst"
}
```

Log file location: `data/risk-events.jsonl`

---

## 7. Position Sizing Guidelines

For any investment or resource allocation decision within the simulation:

| Context | Max Single Position | Max Sector | Max Total Exposure |
|---------|---------------------|------------|-------------------|
| Early stage (revenue < 1M) | 15% of capital | 30% | — |
| Growth stage | 20% of capital | 35% | — |
| Mature stage | 25% of capital | 40% | — |
| Cash reserves (floor) | — | — | 15% of total assets minimum |

**Concentration check**: If any single position exceeds 15% of total capital, flag for review.

---

## 8. Drawdown Monitoring

| Metric | Warn | Critical |
|--------|------|----------|
| Portfolio drawdown from peak | -15% | -25% |
| Revenue drawdown from trailing 4Q avg | -20% | -35% |
| Cash reserve drawdown (MoM) | -30% | -50% |

**Drawdown recovery rule**: After a Critical drawdown, the simulation must operate in **low‑risk mode** (no new expansion, no M&A, no debt) for 4 consecutive ticks before full operations resume.

---

## 9. Low‑Risk Mode (Post‑Crisis)

When active (triggered by drawdown recovery rule or CEO directive):

| Constraint | Limit |
|------------|-------|
| New hires | Freeze except critical replacements |
| Capex | Maintenance only; no expansion |
| Dividends / buybacks | Suspended |
| Debt | No new debt; existing must be serviced |
| M&A | Prohibited |
| Cash reserve target | Raise to ≥ 6 months runway |

Exit condition: CEO confirms via `/sim risk-mode normal` after metric review.

---

## 10. Framework Maintenance

- **Review cadence**: Every 50 simulation ticks, or immediately after any L4/L5 event.
- **Versioning**: Breaking changes increment minor version; threshold tweaks increment patch.
- **Amendment process**: Risk Analyst proposes change → CEO approves → framework updated → changelog appended.

### Changelog

| Date | Version | Author | Change |
|------|---------|--------|--------|
| 2026-07-07 | 1.0 | Risk Analyst | Initial framework |

---

*"Vigilant — not paranoid. Every number has a story; we read it before it becomes a headline."*
