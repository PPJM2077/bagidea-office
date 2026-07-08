# AI Quant Office — Capability Matrix v1.0

> **AI-Native Format:** Machine-parseable table of every module, its capabilities,
> input/output schemas, success criteria, and AI role bindings. Designed for
> AI agents to self-discover what the system can do and whom to call.

---

## How to Read This Matrix

Each row defines one **module capability** with:
- **Module** — which module provides it
- **Capability** — what it does (verb-oriented)
- **Input** — what data it consumes
- **Output** — what it produces
- **Success Criteria** — how to measure success
- **AI Roles** — which AI roles invoke this
- **Latency** — typical response time
- **Criticality** — impact if unavailable

---

## 1. Core Layer Capabilities

### 1.1 Office Kernel

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Register AI Identity** | `{name, role, department, model, skills, version}` | `{identity_id, credentials, status}` | AI available in registry within 1s, unique ID assigned | All roles | <500ms | System |
| **Authenticate Agent** | `{identity_id, token}` | `{session_id, permissions, expires_at}` | Valid session created, permissions loaded | All roles | <200ms | System |
| **Check Permission** | `{agent_id, action, resource}` | `{allowed: bool, reason}` | Correct RBAC decision in <100ms | All roles | <100ms | System |
| **Get Department Tree** | `{department_id?}` | `{tree: [{dept, parent, members, head}]}` | Complete org chart returned, cached for 5s | CEO, CTO, HR | <300ms | High |
| **Update Presence** | `{agent_id, status, current_task}` | `{broadcast_to_subscribers}` | Presence visible to all within 500ms | All roles | <200ms | Medium |
| **Rotate Credentials** | `{agent_id, reason}` | `{new_token, old_expires_at}` | Old token invalidated, new token active | CTO, Founder | <1s | Critical |

### 1.2 Event Bus

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Publish Event** | `{channel, type, payload, source, priority}` | `{event_id, delivery_count}` | Event delivered to all subscribers within 100ms | All roles | <50ms | System |
| **Subscribe to Channel** | `{agent_id, channels[], filters?}` | `{subscription_ids[]}` | Agent receives matching events in real-time | All roles | <100ms | System |
| **Replay Events** | `{channel, start_time, end_time, filter?}` | `{events[]}` | All matching events returned in order, <1s per 1000 events | All roles | <1s | High |
| **Create Channel** | `{name, type, permissions, ttl?}` | `{channel_id}` | Channel available for pub/sub within 200ms | CTO, CEO | <200ms | High |

### 1.3 Communication Engine

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Send DM** | `{from, to, content, priority}` | `{message_id, delivered: bool}` | Message delivered to recipient's inbox within 200ms | All roles | <200ms | High |
| **Start Meeting** | `{title, agenda, attendees[], scheduled_time, mode}` | `{meeting_id, join_link, calendar_event}` | All attendees notified, meeting room ready | CEO, any chair | <1s | High |
| **Conduct Debate** | `{topic, participants[], rounds, rules}` | `{debate_id, transcript, verdict}` | Structured pro/con exchange, verdict produced | CEO, CIO | <5s per round | Medium |
| **Committee Vote** | `{proposal, members[], weights, quorum}` | `{vote_id, tally, result, dissenting}` | All eligible members voted, quorum met, result computed | CEO, any chair | <3s | High |
| **Broadcast** | `{from, content, audience, priority}` | `{broadcast_id, delivery_count}` | All intended recipients receive within 500ms | CEO, CRO (emergency) | <500ms | High |
| **Search Conversation** | `{query, date_range?, participants?}` | `{results[{message, sender, timestamp, context}]}` | Relevant messages found, ranked by relevance | All roles | <2s | Medium |

### 1.4 Memory System

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Store Memory** | `{agent_id, type, content, ttl?, tags?}` | `{memory_id, stored}` | Persisted within 500ms, searchable immediately | All roles | <500ms | System |
| **Search Memory** | `{query, agent_id?, type?, limit}` | `{results[{content, timestamp, source, confidence}]}` | Relevant results ranked by relevance score, <2s | All roles | <2s | High |
| **Query Knowledge Graph** | `{entity, relationship?, depth}` | `{graph: {nodes, edges}}` | Complete subgraph returned, <3s for 1000 nodes | All roles | <3s | High |
| **Replay Timeline** | `{start, end, agents?, symbols?}` | `{events[{timestamp, type, agent, decision, context}]}` | Chronological replay with full context, <1s per 100 events | All roles | Varies | Medium |
| **Compress Memory** | `{agent_id, older_than}` | `{archive_id, summary, size_saved}` | Memory reduced by >60%, summary preserves key facts | System (auto) | <5s | Medium |
| **Forget Memory (GC)** | `{criteria}` | `{deleted_count, freed_space}` | Stale/low-confidence memories removed, capacity maintained | System (auto) | <10s | Low |

### 1.5 Task System

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Create Task** | `{title, description, assignee?, priority, deadline, depends_on[]?}` | `{task_id, status: "pending"}` | Task created, added to queue, dependent tasks blocked | All roles | <300ms | High |
| **Assign Task** | `{task_id, agent_id, skill_match?}` | `{assignment_confirmed}` | Agent notified, skill match verified >80% | CEO, PM | <500ms | High |
| **Get Task Queue** | `{agent_id?, department?, status?}` | `{tasks[{id, title, priority, status, deadline}]}` | Tasks sorted by priority, dependencies shown | All roles | <500ms | High |
| **Complete Task** | `{task_id, result, evidence}` | `{task_closed, downstream_unblocked}` | Dependencies checked, dependent tasks unblocked | All roles | <300ms | High |
| **Start Sprint** | `{name, tasks[], start, end, goal}` | `{sprint_id, board}` | All tasks in sprint tracked, burndown available | CEO, PM | <500ms | Medium |
| **Approve/Reject** | `{task_id, reviewer, decision, comment}` | `{status_update, notification}` | Status updated, downstream notified, audit logged | Reviewers | <1s | High |

### 1.6 Governance Engine

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Check Constitution** | `{action, context}` | `{compliant: bool, violated_articles[], severity}` | All relevant articles checked, correct verdict | All roles | <500ms | Critical |
| **Submit Proposal** | `{title, change, evidence, change_level, impact_analysis}` | `{proposal_id, workflow_step}` | Proposal enters review pipeline, committee notified | Any AI | <1s | High |
| **Vote on Proposal** | `{proposal_id, voter, decision, rationale}` | `{vote_recorded, updated_tally}` | Vote recorded, tally updated, quorum check run | Committee members | <500ms | High |
| **Execute Change** | `{proposal_id, approval_evidence}` | `{change_id, old_config, new_config, rollback_command}` | Change applied, audit trail created, rollback ready | System | <2s | Critical |
| **Audit Trail** | `{time_range?, actor?, action?, resource?}` | `{entries[{timestamp, actor, action, resource, old, new, approved_by}]}` | Immutable log, all changes traceable | Founder, CRO, Compliance | <3s | Critical |
| **Rollback Change** | `{change_id, reason, authorized_by}` | `{rollback_id, status, affected_modules}` | State restored to pre-change, dependent modules notified | CTO, Founder | <5s | Critical |

### 1.7 AI Gateway

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Route Request** | `{task_type, prompt, context, preferred_model?, budget?}` | `{response, provider_used, token_count, cost, latency_ms}` | Task routed to optimal provider, response in expected time | All roles via SDK | Varies by provider | System |
| **Get Provider Status** | `{provider_id?}` | `{providers[{name, online, latency, cost_per_token, error_rate}]}` | All providers health-checked within last 60s | CTO, Gateway | <200ms | High |
| **Execute Ensemble** | `{prompt, providers[], strategy}` | `{responses[], aggregate, confidence}` | All providers called, results aggregated, consensus computed | Decision Engine | Max(provider latencies) | High |
| **Check Budget** | `{task_type, cost_estimate}` | `{allowed: bool, remaining_budget, alternative_suggestion?}` | Budget not exceeded, alternative suggested if over | All roles | <100ms | High |
| **Register Provider** | `{provider_config}` | `{provider_id, test_result}` | Provider responds to test query, health check setup | CTO, DevOps | <3s | Medium |

### 1.8 Plugin SDK

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Install Plugin** | `{plugin_id, source, version}` | `{plugin_id, status: "sandbox"}` | Plugin sandboxed, dependencies resolved | CTO, Architect | <5s | High |
| **Enable Plugin** | `{plugin_id}` | `{status: "active", capabilities_registered}` | Plugin functions registered, hot-reloaded | CTO | <1s | High |
| **Disable Plugin** | `{plugin_id}` | `{status: "disabled", cleanup_done}` | Plugin stopped gracefully, no data loss | CTO | <2s | High |
| **Get Plugin Manifest** | `{plugin_id}` | `{manifest, capabilities, dependencies}` | Complete plugin metadata returned | System, Gateway | <200ms | Medium |

### 1.9 Workflow Engine

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Execute Workflow** | `{workflow_id, trigger_data}` | `{run_id, status: "running"}` | Workflow steps initiated in order | Any AI | <500ms | High |
| **Get Workflow Status** | `{run_id}` | `{current_step, progress%, blocked?, error?}` | Real-time status with step-level detail | All roles | <200ms | Medium |
| **Pause/Resume** | `{run_id, action}` | `{status: "paused" | "running"}` | State preserved, idempotent resume | CTO, Operator | <500ms | Medium |

---

## 2. Knowledge Layer Capabilities

### 2.1 Knowledge OS

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Query RAG** | `{query, tier_filter?, sources[]?}` | `{answer, sources[{content, tier, confidence}], citations[]}` | Answer cites at least 2 independent sources, confidence scored | All roles | <3s | High |
| **Add Knowledge Entry** | `{content, tier, source, tags, confidence?}` | `{entry_id, indexed}` | Entry added to knowledge graph, searchable within 2s | All roles | <500ms | High |
| **Fact Check** | `{claim, required_evidence_strength}` | `{supported: bool, supporting_sources[], conflicting_sources[], confidence}` | At least 2 independent sources confirm or refute | QA, Compliance, any | <5s | High |
| **Get Knowledge Graph** | `{entity, depth, relation_types?}` | `{nodes[], edges[]}` | Complete subgraph with all relationships | All roles | <3s | High |
| **Check Citation** | `{statement, expected_source?}` | `{has_citation, source_tier, confidence, verified}` | Source exists and tier is appropriate | Compliance, Audit | <2s | High |
| **Calibrate Confidence** | `{prediction, actual_outcome}` | `{calibration_adjustment, new_calibration_score}` | Calibration curve updated, precision improved over time | System (auto) | <500ms | Medium |

### 2.2 Company Wiki

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Create Page** | `{title, content, tags, parent?}` | `{page_id, url, version: 1}` | Page created, searchable, permissions set | All roles | <500ms | Medium |
| **Search Wiki** | `{query, filters?}` | `{results[{title, snippet, tags, last_updated}]}` | Relevant results with context snippets | All roles | <1s | Medium |
| **Update Page** | `{page_id, content, reason}` | `{new_version, diff}` | Version history maintained, changelog updated | All roles | <500ms | Medium |

---

## 3. Employee Layer Capabilities

### 3.1 AI Employee System

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Get Employee Profile** | `{agent_id}` | `{name, role, skills, experience, kpi, cost, reputation}` | Complete profile with metrics | CEO, HR | <300ms | Medium |
| **Update KPI** | `{agent_id, metric, value}` | `{kpi_updated, new_score, trend}` | KPI updated, performance trend recalculated | System (auto) | <200ms | Medium |
| **Get Reputation Score** | `{agent_id}` | `{score, factors[{factor, weight, contribution}], trend}` | Weighted score with explanation | CEO, Committee | <200ms | Medium |
| **Assign Training** | `{agent_id, course_id}` | `{training_scheduled, estimated_completion}` | Training added to agent's queue, mentor notified | CEO, HR | <1s | Low |

### 3.2 HR & Recruitment

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Benchmark Model** | `{model_id, test_suite}` | `{score, metrics[{accuracy, latency, cost, coding, reasoning}], ranking}` | All benchmarks run, compared to existing models | HR, CTO | <30s | Medium |
| **Run Interview** | `{model_id, role, questions[]}` | `{transcript, scores, recommendation}` | Structured interview completed, scored against rubric | HR | <60s | Low |
| **Onboard AI** | `{model_id, role, department}` | `{employee_id, credentials, training_plan}` | Identity created, permissions set, initial training queued | HR, System | <5s | High |

---

## 4. Intelligence Layer Capabilities

### 4.1 Market Intelligence

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Analyze Technical** | `{symbol, timeframes[], indicators[]}` | `{trend, structure, levels, momentum, volatility, confidence}` | Multi-timeframe analysis with all requested indicators | Market Analyst | <5s | High |
| **Detect Regime** | `{symbol, window?}` | `{regime, confidence, evidence}` | Regime correctly classified with supporting metrics | Market Analyst, Strategy | <3s | High |
| **Get Market Heatmap** | `{symbols[]}` | `{map[{symbol, change, volume, regime, ai_confidence}]}` | All symbols analyzed, ranked by movement | Dashboard, CEO | <5s | High |
| **Analyze Correlation** | `{symbols[], window?}` | `{matrix[{pair, correlation, direction, strength, change}]}` | Pairwise correlations with trend detection | Portfolio, Risk | <3s | High |
| **Get News Sentiment** | `{symbol, sources[], timeframe?}` | `{overall_sentiment, confidence, top_stories[], source_breakdown}` | Multi-source sentiment with cross-reference check | Market Analyst, CEO | <2s | Medium |

### 4.2 Quant Research

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Run Backtest** | `{strategy_config, data_range, parameters}` | `{report[{sharpe, sortino, dd, win_rate, profit_factor, trades[]}], equity_curve}` | Backtest with transaction costs, min 5 years data | Research Director | <60s | High |
| **Walk Forward** | `{strategy_config, data, windows}` | `{windows[{sharpe, dd}], aggregate_score, stability_metric}` | 24+ windows, OOS performance consistent | Research Director | <120s | High |
| **Monte Carlo** | `{strategy_config, n_simulations, parameters}` | `{pass_rate, distribution, expected_value, worst_case}` | 1000+ simulations, confidence intervals reported | Research Director | <120s | High |
| **Optimize** | `{strategy_config, parameter_space, metric}` | `{best_params, improvement, sensitivity_analysis}` | Bayesian optimization exhaustive, top-5 parameter sets | Strategy AI | <300s | High |
| **Register Experiment** | `{hypothesis, methodology, parameters}` | `{experiment_id, registry_entry}` | Experiment tracked, reproducible, linked to strategy | Research Director | <500ms | High |
| **Analyze Factor** | `{data, factors[]}` | `{factor_returns[], correlations, ic, sharpe_by_factor}` | Factor significance tested, IC reported | Research Director | <30s | Medium |

### 4.3 Strategy Engine

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Deploy Strategy** | `{strategy_package, version}` | `{deployment_id, status: "sandbox"}` | Strategy loaded into sandbox, health check passes | Strategy AI | <3s | High |
| **Get Strategy Health** | `{strategy_id}` | `{health_score, risk_score, performance_score, confidence_score}` | All scores computed from trailing metrics | CEO, CIO, Portfolio | <500ms | High |
| **Dynamic Reallocate** | `{strategy_performance[]}` | `{new_weights[{strategy, weight, rationale}]}` | Weights optimized for current performance, correlation respected | CIO, Portfolio | <5s | High |
| **Activate Kill Switch** | `{strategy_id, trigger}` | `{strategy_disabled, positions_closed?}` | Strategy stopped, positions closed if necessary, metrics logged | Risk, System (auto) | <2s | Critical |
| **Run Canary** | `{strategy_id, allocation_percent}` | `{canary_id, status, metrics}` | Strategy running on small capital, metrics tracked | CIO, Research | <5s | High |
| **Evolve Strategy** | `{parent_strategies[], crossover_params}` | `{child_strategy, dna, initial_backtest}` | Genetic algorithm produces viable offspring | Research, Strategy AI | <120s | Medium |

### 4.4 Decision Engine

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Aggregate Signals** | `{signals[]}` | `{aggregate_signal, confidence, consensus_level}` | All signals considered, weighted by source reputation | CEO, Decision | <2s | Critical |
| **Compute Confidence** | `{signal, historical_accuracy, market_conditions}` | `{confidence, calibrated, uncertainty_range}` | Historical calibration applied, uncertainty quantified | Decision | <1s | Critical |
| **Run Devil's Advocate** | `{proposal}` | `{survives, flaws[], mitigations[]}` | Every assumption challenged, weakest links identified | Decision | <5s | High |
| **Generate Explanation** | `{decision, contributing_factors[]}` | `{explanation_report, factor_breakdown, trace_id}` | Decision fully explainable, factor contributions quantified | All roles (read) | <2s | High |
| **Route Decision** | `{decision, change_level}` | `{next_step, assigned_to, deadline}` | Decision routed to correct approval channel | Decision | <500ms | Critical |

### 4.5 Risk Engine

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Calculate Position Size** | `{equity, risk_percent, atr, correlation, news_factor}` | `{recommended_lots, size_adjustments[], final_risk_percent}` | All adjustment factors applied, formula correct | Risk Manager | <500ms | Critical |
| **Monitor Drawdown** | `{portfolio_equity_series}` | `{current_dd, max_dd, dd_duration, trend}` | Drawdown calculated from peak, trend direction | Risk, CRO | <200ms | Critical |
| **Compute VaR** | `{positions, confidence_level, horizon}` | `{var, cvar, component_var, stress_scenario}` | VaR computed via historical + parametric, stress-tested | Risk | <3s | Critical |
| **Check Exposure** | `{portfolio}` | `{total_exposure, by_symbol, by_broker, by_strategy, limits_status}` | All exposure dimensions computed, limits checked | Risk, Portfolio | <500ms | Critical |
| **Detect Anomaly** | `{price_tick, volume, spread, historical_distribution}` | `{is_anomaly, type, severity, recommended_action}` | Statistical anomaly detection, false positive rate <1% | Risk, DevOps | <100ms | Critical |
| **Activate Safe Mode** | `{trigger, level}` | `{safe_mode_active, actions_taken[], affected_modules[]}` | All trading halted, positions protected, Founder notified | Risk, CRO | <1s | Critical |
| **Run Stress Test** | `{portfolio, scenarios[]}` | `{impacts[{scenario, pnl, dd, margin_call_risk}], worst_case}` | All scenarios computed with full revaluation | Risk | <30s | High |

### 4.6 Portfolio Engine

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Get Unified View** | `{include_brokers[], include_assets?}` | `{total_equity, total_exposure, by_broker, by_symbol, correlation, pnl}` | All accounts consolidated, real-time | Portfolio, CEO, CRO | <2s | Critical |
| **Optimize Allocation** | `{strategies, constraints, objective}` | `{optimal_weights, efficient_frontier, constraint_sensitivity}` | Optimization converges, constraints satisfied | Portfolio, CIO | <10s | High |
| **Lock Profit** | `{amount, lock_percentage, method}` | `{profit_locked, remaining_risk, lock_expiry}` | Profit secured, lock adjusted for trend strength | Portfolio | <2s | High |
| **Simulate Scenario** | `{current_state, actions[], market_assumptions}` | `{outcomes[{action, expected_value, risk, probability}], recommended}` | All actions simulated, recommendation with EV calculation | Portfolio | <15s | High |
| **Rebalance** | `{target_weights, current_positions, constraints}` | `{rebalance_plan[{action, symbol, broker, size, reason}], expected_impact}` | Minimal trades to reach target, cost-aware | Portfolio | <5s | High |
| **Recover Portfolio** | `{current_state, options[]}` | `{optimal_actions[{option, expected_value, risk}], recommendation}` | Best recovery path identified with scenario simulation | Portfolio | <10s | High |

---

## 5. Execution Layer Capabilities

### 5.1 Execution Engine

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Place Order** | `{symbol, side, type, lots, broker?, sl?, tp?}` | `{order_id, broker_order_id, status, filled_price?}` | Order accepted by broker, fill confirmation received | Execution AI | <2s | Critical |
| **Cancel Order** | `{order_id}` | `{status: "cancelled", confirmation}` | Order removed from broker, confirmed | Execution AI | <1s | Critical |
| **Get Order Status** | `{order_id?}` | `{orders[{id, status, filled, remaining, price}]}` | All active orders with real-time status | Execution, Portfolio | <500ms | High |
| **Get Execution Quality** | `{timeframe?}` | `{metrics[{slippage_avg, fill_rate, latency_avg, rejection_rate}]}` | Execution quality metrics by broker and symbol | Broker AI, CTO | <2s | High |

### 5.2 Broker Integration

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Connect Broker** | `{broker_config}` | `{connection_id, status, account_info}` | Broker connected, account verified, heartbeats started | Broker AI, DevOps | <5s | Critical |
| **Get Broker Health** | `{broker_id?}` | `{brokers[{name, connected, latency, spread, fill_rate, score}]}` | All brokers health-checked, score computed | Broker AI, Dashboard | <500ms | High |
| **Recommend Broker** | `{symbol, side, lots}` | `{best_broker, reason, comparison[]}` | Best broker selected based on current conditions | Broker AI, Execution | <1s | High |
| **Check Compliance** | `{broker_id, order}` | `{compliant: bool, rules_checked[], violations[]}` | All broker-specific rules validated | Compliance, Broker AI | <300ms | Critical |

---

## 6. Monitoring Layer Capabilities

### 6.1 System Health

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Get System Health** | `{scope?}` | `{overall_score, components[{name, status, metric, threshold, alert?}]}` | All components reporting within last 60s | DevOps, CTO, CEO | <1s | High |
| **Get AI Health** | `{agent_id?}` | `{agents[{name, status, accuracy, latency, cost, hallucination_rate}]}` | All AI agents with trailing metrics | CTO, CEO | <2s | High |
| **Get Trading Metrics** | `{symbol?, timeframe?}` | `{metrics[{win_rate, rr, sharpe, dd, exposure, profit_factor}]}` | Trading KPIs computed from journal | CEO, CIO, Portfolio | <3s | High |
| **Trigger Alert** | `{severity, module, message, data}` | `{alert_id, routed_to[], acknowledged[]}` | Correct routing (L1-L5), first response within SLA | DevOps, System | <200ms | High |
| **Self-Heal** | `{incident_id, procedure}` | `{healed: bool, actions_taken[], status}` | Procedure executed, system stable, incident logged | DevOps, System | <10s | Critical |

---

## 7. Simulation Layer Capabilities

### 7.1 Company Simulator

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Create Digital Twin** | `{production_state_snapshot}` | `{twin_id, synced, lag_ms}` | Twin mirrors production with <100ms lag | System | <5s initial | High |
| **Run Scenario** | `{scenario_parameters, duration, metrics}` | `{simulation_id, results, comparison_to_production}` | Simulation complete with all requested metrics | Research, Risk, Portfolio | <60s | High |
| **Time Travel Replay** | `{timestamp, symbol?, agent?}` | `{state, decisions, market_data, agent_reasoning}` | Exact state reconstructed, replay step-by-step | Any role (debug) | <5s | Medium |
| **Sandbox Isolation** | `{experiment_config}` | `{sandbox_id, status: "running"}` | Sandbox isolated from production, no side effects | QA, Research | <3s | High |

---

## 8. Evolution Layer Capabilities

### 8.1 Self-Improvement

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Generate Improvement Proposal** | `{area, performance_data, comparison}` | `{proposal, expected_impact, evidence, change_level}` | Proposal has quantified impact and clear evidence | CEO, Research, any AI | <10s | Medium |
| **Run A/B Test** | `{control, variant, metrics, duration}` | `{results[{metric, control_value, variant_value, significant}]}` | Statistical significance at 95% confidence | Research, QA | <60s | Medium |
| **Detect Regression** | `{module, performance_series}` | `{regression_detected, metric, magnitude, p_value}` | Significant regression flagged, compared to baseline | System | <5s | High |
| **Conduct Weekly Review** | `{weekly_data}` | `{evolution_report, decisions, action_items}` | All agenda items covered, decisions actionable | CEO | <30s | Medium |

---

## 9. UX Layer Capabilities

### 9.1 Dashboard

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Get Dashboard** | `{section, user_level}` | `{widgets, data, layout}` | Dashboard renders in <2s, correct for access level | Founder (human) | <2s | High |
| **Global Search** | `{query, scope?}` | `{results_by_category[]}` | All scopes searched, results ranked | Founder (human) | <2s | Medium |
| **Get AI Presence** | `{department?}` | `{agents[{name, status, task, progress, color}]}` | All agents shown with live status | Founder (human) | <1s | Medium |

### 9.2 Collaboration UI

| Capability | Input | Output | Success Criteria | AI Roles | Latency | Criticality |
|---|---|---|---|---|---|---|
| **Open Meeting Room** | `{meeting_id}` | `{room_state, participants[], whiteboard}` | Meeting room ready, all participants joined | All roles | <3s | Medium |
| **Get Meeting Replay** | `{meeting_id}` | `{transcript, decisions, timeline, participants}` | Full meeting recorded and searchable | Founder (human) | <2s | Low |
| **Send Mail** | `{to, subject, body, attachments?}` | `{mail_id, delivered}` | Mail in recipient's inbox | All roles | <1s | Low |

---

## Capability Access by Role — Quick Reference

| Role | Market Analysis | Risk Assessment | Portfolio Mgmt | Research | Strategy | Execution | Governance | Knowledge | Employee Mgmt | System Admin |
|---|---|---|---|---|---|---|---|---|---|---|
| CEO AI | R | R | R | R | R | R | W | R | W | R |
| CIO AI | R | R | W | W | W | R | W | R | R | - |
| CRO AI | R | W | W | R | R | W | W | R | R | R |
| CFO AI | - | R | R | - | - | - | R | R | R | R |
| CTO AI | - | - | - | - | - | - | W | W | R | W |
| Market Analyst | W | - | - | R | R | - | - | W | - | - |
| Risk Manager | R | W | R | - | R | W | W | R | - | - |
| Portfolio Mgr | R | R | W | R | W | W | W | R | - | - |
| Research Director | R | R | R | W | W | - | W | W | - | - |
| Strategy AI | R | R | - | W | W | - | - | W | - | - |
| Execution AI | - | R | R | - | - | W | - | - | - | - |
| Broker AI | R | R | R | - | - | W | R | - | - | R |
| News AI | W | - | - | R | - | - | - | W | - | - |
| Compliance | - | W | R | - | - | W | W | R | - | R |
| QA | - | - | - | W | W | W | W | W | - | W |
| Architect | - | - | - | - | - | - | W | W | - | W |
| DevOps | - | - | - | - | - | - | - | - | - | W |
| Founder (Human) | R | R | R | R | R | R | W | R | W | W |

**Legend:** W = Write/Execute, R = Read/Monitor, - = No access

---

## Capability Groups by Purpose

| Group | Capabilities | Owner(s) |
|---|---|---|
| **Signal Generation** | Technical Analysis, Macro Analysis, News Sentiment, Regime Detection, Correlation Analysis | Market Analyst, News AI |
| **Risk Control** | Position Sizing, Drawdown Monitor, VaR Calculation, Exposure Check, Anomaly Detection, Safe Mode | Risk Manager, CRO |
| **Portfolio Mgmt** | Unified View, Optimization, Profit Lock, Scenario Sim, Rebalance, Recovery | Portfolio Manager |
| **Research** | Backtest, Walk Forward, Monte Carlo, Optimization, Experiment Registry, Factor Analysis | Research Director |
| **Strategy Mgmt** | Deploy, Health Check, Dynamic Allocation, Kill Switch, Canary, Evolution | Strategy AI, CIO |
| **Decision & Execution** | Signal Aggregation, Confidence Scoring, Devil's Advocate, Explainability, Order Placement | Decision, Execution |
| **Governance** | Constitution Check, Proposal, Voting, Change Execution, Audit, Rollback | Governance Engine |
| **Knowledge** | RAG, Knowledge Graph, Fact Check, Citation, Wiki | Knowledge OS, Wiki |
| **AI Operations** | Identity, Presence, Task, KPI, Reputation, Training, Recruitment | Kernel, Employee System |

---

## Latency Budget by Criticality

| Criticality | Max Acceptable | SLA Target | Monitoring |
|---|---|---|---|
| **System** (must always work) | <500ms | <200ms p95 | Every call tracked |
| **Critical** (trading impact) | <2s | <500ms p95 | Alert if >1s |
| **High** (business impact) | <5s | <2s p95 | Alert if >3s |
| **Medium** (operational) | <30s | <5s p95 | Logged |
| **Low** (non-urgent) | <120s | <30s p95 | Logged |

---

*End of Capability Matrix v1.0 — AI Quant Office*
