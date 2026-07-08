"""
Risk Engine — Company Simulator
================================
Implements the full risk framework from risk-framework.md v1.0.

Components
----------
- RiskCalculator  : evaluate all 24 risk metrics (financial, operational, market, system)
- SafeModeChecker : detect automatic safe-mode triggers (SM-01 – SM-07)
- PositionSizer   : validate position sizing against stage-based limits
- DrawdownMonitor : track and escalate drawdown events

Usage
-----
    engine = RiskEngine()
    report = engine.full_assessment(state)
    if report.safe_mode_triggers:
        engine.enter_safe_mode(state)
"""

from __future__ import annotations

import enum
import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskLevel(str, enum.Enum):
    """Severity of a single risk metric evaluation."""

    INFO = "Info"
    WATCH = "Watch"
    WARNING = "Warning"
    CRITICAL = "Critical"
    SYSTEM_EMERGENCY = "SystemEmergency"

    def is_warning_or_above(self) -> bool:
        return self in (RiskLevel.WARNING, RiskLevel.CRITICAL, RiskLevel.SYSTEM_EMERGENCY)

    def is_critical_or_above(self) -> bool:
        return self in (RiskLevel.CRITICAL, RiskLevel.SYSTEM_EMERGENCY)


class AlertLevel(str, enum.Enum):
    """Escalation level per risk-framework.md §4."""

    L1_INFO = "L1"
    L2_WATCH = "L2"
    L3_WARNING = "L3"
    L4_CRITICAL = "L4"
    L5_SYSTEM_EMERGENCY = "L5"


class CompanyStage(str, enum.Enum):
    """Company maturity stage — used for position sizing limits (§7)."""

    EARLY = "early"
    GROWTH = "growth"
    MATURE = "mature"


class RiskCategory(str, enum.Enum):
    """Top-level risk categories from §2."""

    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    MARKET = "market"
    SYSTEM = "system"


class SafeModeTriggerID(str, enum.Enum):
    """Automatic safe-mode trigger identifiers (§3.1)."""

    SM01_CRITICAL_FINANCIAL = "SM-01"
    SM02_MULTI_CRITICAL = "SM-02"
    SM03_DATA_INTEGRITY = "SM-03"
    SM04_AGENT_LOOP = "SM-04"
    SM05_SIM_DRIFT = "SM-05"
    SM06_TICK_TIMEOUT = "SM-06"
    SM07_MEMORY_LEAK = "SM-07"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class RiskResult:
    """Evaluation of a single risk metric."""

    risk_id: str  # e.g. "cash_runway"
    category: RiskCategory
    label: str  # human-readable
    metric_value: float
    warning_threshold: Optional[float]  # None for boolean risks
    critical_threshold: Optional[float]
    level: RiskLevel
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SafeModeTrigger:
    """A safe-mode trigger that fired."""

    trigger_id: SafeModeTriggerID
    description: str
    risk_ids: List[str] = field(default_factory=list)


@dataclass
class PositionSizingResult:
    """Result of a position-sizing validation."""

    valid: bool
    position_size: float
    position_pct: float  # % of total capital
    sector_total_pct: float  # % of total capital in same sector
    total_exposure_pct: float  # total capital deployed
    max_single_pct: float  # limit
    max_sector_pct: float  # limit
    min_cash_pct: float  # floor
    flags: List[str] = field(default_factory=list)
    message: str = ""


@dataclass
class DrawdownResult:
    """Evaluation of drawdown metrics."""

    portfolio_drawdown_pct: float
    revenue_drawdown_pct: float
    cash_drawdown_pct: float
    portfolio_level: RiskLevel
    revenue_level: RiskLevel
    cash_level: RiskLevel
    overall_level: RiskLevel
    low_risk_mode_required: bool = False
    flags: List[str] = field(default_factory=list)
    message: str = ""


@dataclass
class RiskEvent:
    """A risk event logged to the risk event log (§6 schema)."""

    id: str
    timestamp: str
    tick: int
    company: str
    risk: str
    level: str
    metric: float
    threshold: float
    snapshot_ref: Optional[str] = None
    trigger: Optional[str] = None
    safe_mode: bool = False
    root_cause: Optional[str] = None
    action_taken: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None
    verified_by: Optional[str] = None

    @classmethod
    def create(
        cls,
        tick: int,
        company: str,
        risk: str,
        level: str,
        metric: float,
        threshold: float,
        trigger: Optional[str] = None,
        safe_mode: bool = False,
    ) -> "RiskEvent":
        now = datetime.now(timezone.utc)
        event_id = f"RISK-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        return cls(
            id=event_id,
            timestamp=now.isoformat(),
            tick=tick,
            company=company,
            risk=risk,
            level=level,
            metric=metric,
            threshold=threshold,
            trigger=trigger,
            safe_mode=safe_mode,
        )


@dataclass
class RiskReport:
    """Aggregate assessment produced by RiskEngine.full_assessment()."""

    timestamp: str
    tick: int
    company: str
    results: List[RiskResult]
    safe_mode_triggers: List[SafeModeTrigger]
    position_sizing: Optional[PositionSizingResult] = None
    drawdown: Optional[DrawdownResult] = None
    highest_level: RiskLevel = RiskLevel.INFO
    alert_level: AlertLevel = AlertLevel.L1_INFO
    low_risk_mode: bool = False
    summary: str = ""


# ---------------------------------------------------------------------------
# RiskCalculator
# ---------------------------------------------------------------------------


class RiskCalculator:
    """Evaluate all risk metrics defined in risk-framework.md §2.

    Each method accepts structured data (not DB models) and returns a
    ``RiskResult``.  The unified ``evaluate_all()`` runs every metric and
    returns a flat list.
    """

    # ── Financial (§2.1) ──────────────────────────────────────────────

    def cash_runway(self, months_of_opex_coverage: float) -> RiskResult:
        """Cash runway: warn < 6mo, critical < 3mo."""
        level = RiskLevel.INFO
        if months_of_opex_coverage < 3:
            level = RiskLevel.CRITICAL
        elif months_of_opex_coverage < 6:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="cash_runway",
            category=RiskCategory.FINANCIAL,
            label="Cash Runway",
            metric_value=months_of_opex_coverage,
            warning_threshold=6.0,
            critical_threshold=3.0,
            level=level,
            message=f"{months_of_opex_coverage:.1f} months of operating expenses covered",
        )

    def burn_rate_spike(self, mom_change_pct: float, trailing_3m_avg: float) -> RiskResult:
        """Burn-rate spike: warn +50% vs 3m avg, critical +100%."""
        if trailing_3m_avg == 0:
            return RiskResult(
                risk_id="burn_rate_spike",
                category=RiskCategory.FINANCIAL,
                label="Burn Rate Spike",
                metric_value=mom_change_pct,
                warning_threshold=50.0,
                critical_threshold=100.0,
                level=RiskLevel.INFO,
                message="No trailing data to compare",
            )
        change_vs_avg = ((mom_change_pct - trailing_3m_avg) / abs(trailing_3m_avg)) * 100
        level = RiskLevel.INFO
        if change_vs_avg >= 100:
            level = RiskLevel.CRITICAL
        elif change_vs_avg >= 50:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="burn_rate_spike",
            category=RiskCategory.FINANCIAL,
            label="Burn Rate Spike",
            metric_value=change_vs_avg,
            warning_threshold=50.0,
            critical_threshold=100.0,
            level=level,
            message=f"Burn rate change vs 3m avg: {change_vs_avg:+.1f}%",
        )

    def revenue_concentration(self, pct_from_single_customer: float) -> RiskResult:
        """Revenue concentration: warn >40%, critical >60%."""
        level = RiskLevel.INFO
        if pct_from_single_customer > 60:
            level = RiskLevel.CRITICAL
        elif pct_from_single_customer > 40:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="revenue_concentration",
            category=RiskCategory.FINANCIAL,
            label="Revenue Concentration",
            metric_value=pct_from_single_customer,
            warning_threshold=40.0,
            critical_threshold=60.0,
            level=level,
            message=f"{pct_from_single_customer:.1f}% revenue from single customer",
        )

    def debt_service_ratio(self, ratio_pct: float) -> RiskResult:
        """Debt service ratio: warn >35%, critical >50%."""
        level = RiskLevel.INFO
        if ratio_pct > 50:
            level = RiskLevel.CRITICAL
        elif ratio_pct > 35:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="debt_service_ratio",
            category=RiskCategory.FINANCIAL,
            label="Debt Service Ratio",
            metric_value=ratio_pct,
            warning_threshold=35.0,
            critical_threshold=50.0,
            level=level,
            message=f"Debt service consumes {ratio_pct:.1f}% of operating income",
        )

    def margin_erosion(self, current_gross_margin: float, trailing_3m_avg: float) -> RiskResult:
        """Margin erosion: warn -10pp, critical -20pp vs 3m avg."""
        drop_pp = trailing_3m_avg - current_gross_margin
        level = RiskLevel.INFO
        if drop_pp >= 20:
            level = RiskLevel.CRITICAL
        elif drop_pp >= 10:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="margin_erosion",
            category=RiskCategory.FINANCIAL,
            label="Margin Erosion",
            metric_value=drop_pp,
            warning_threshold=10.0,
            critical_threshold=20.0,
            level=level,
            message=f"Gross margin dropped {drop_pp:.1f}pp vs trailing 3m average",
        )

    def liquidity_crunch(self, current_ratio: float) -> RiskResult:
        """Liquidity crunch (current ratio): warn <1.5, critical <1.0."""
        level = RiskLevel.INFO
        if current_ratio < 1.0:
            level = RiskLevel.CRITICAL
        elif current_ratio < 1.5:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="liquidity_crunch",
            category=RiskCategory.FINANCIAL,
            label="Liquidity Crunch",
            metric_value=current_ratio,
            warning_threshold=1.5,
            critical_threshold=1.0,
            level=level,
            message=f"Current ratio: {current_ratio:.2f}",
        )

    # ── Operational (§2.2) ────────────────────────────────────────────

    def production_bottleneck(
        self, capacity_utilisation_pct: float, sustained_ticks: int
    ) -> RiskResult:
        """Production bottleneck: warn >85% for 3+ ticks, critical >95% sustained."""
        level = RiskLevel.INFO
        if capacity_utilisation_pct > 95 and sustained_ticks >= 3:
            level = RiskLevel.CRITICAL
        elif capacity_utilisation_pct > 85 and sustained_ticks >= 3:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="production_bottleneck",
            category=RiskCategory.OPERATIONAL,
            label="Production Bottleneck",
            metric_value=capacity_utilisation_pct,
            warning_threshold=85.0,
            critical_threshold=95.0,
            level=level,
            message=f"Capacity at {capacity_utilisation_pct:.1f}% for {sustained_ticks} ticks",
        )

    def key_person_dependency(self, critical_output_pct: float, has_backup: bool) -> RiskResult:
        """Key-person: flagged if >30% critical output; critical if +no backup."""
        if critical_output_pct <= 30:
            return RiskResult(
                risk_id="key_person_dependency",
                category=RiskCategory.OPERATIONAL,
                label="Key-Person Dependency",
                metric_value=critical_output_pct,
                warning_threshold=30.0,
                critical_threshold=None,
                level=RiskLevel.INFO,
                message="No key-person dependency detected",
            )
        level = RiskLevel.CRITICAL if not has_backup else RiskLevel.WARNING
        return RiskResult(
            risk_id="key_person_dependency",
            category=RiskCategory.OPERATIONAL,
            label="Key-Person Dependency",
            metric_value=critical_output_pct,
            warning_threshold=30.0,
            critical_threshold=None,
            level=level,
            message=f"Single employee responsible for {critical_output_pct:.1f}% of "
            f"critical output{' (no backup!)' if not has_backup else ''}",
        )

    def attrition_spike(self, annualised_turnover_pct: float) -> RiskResult:
        """Attrition: warn >20%, critical >35% annualised."""
        level = RiskLevel.INFO
        if annualised_turnover_pct > 35:
            level = RiskLevel.CRITICAL
        elif annualised_turnover_pct > 20:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="attrition_spike",
            category=RiskCategory.OPERATIONAL,
            label="Attrition Spike",
            metric_value=annualised_turnover_pct,
            warning_threshold=20.0,
            critical_threshold=35.0,
            level=level,
            message=f"Annualised turnover: {annualised_turnover_pct:.1f}%",
        )

    def supply_chain_concentration(self, pct_from_single_supplier: float) -> RiskResult:
        """Supply chain: warn >50%, critical >75% from single supplier."""
        level = RiskLevel.INFO
        if pct_from_single_supplier > 75:
            level = RiskLevel.CRITICAL
        elif pct_from_single_supplier > 50:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="supply_chain_concentration",
            category=RiskCategory.OPERATIONAL,
            label="Supply Chain Concentration",
            metric_value=pct_from_single_supplier,
            warning_threshold=50.0,
            critical_threshold=75.0,
            level=level,
            message=f"{pct_from_single_supplier:.1f}% of key input from single supplier",
        )

    def inventory_imbalance(self, dio_days: float) -> RiskResult:
        """Inventory imbalance: warn DIO >90 or <15, critical >150 or <5."""
        level = RiskLevel.INFO
        if dio_days > 150 or dio_days < 5:
            level = RiskLevel.CRITICAL
        elif dio_days > 90 or dio_days < 15:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="inventory_imbalance",
            category=RiskCategory.OPERATIONAL,
            label="Inventory Imbalance",
            metric_value=dio_days,
            warning_threshold=90.0,
            critical_threshold=150.0,
            level=level,
            message=f"Days inventory outstanding: {dio_days:.1f}",
        )

    def quality_incidents(self, defect_return_rate_pct: float) -> RiskResult:
        """Quality: warn >5%, critical >12% defect/return rate."""
        level = RiskLevel.INFO
        if defect_return_rate_pct > 12:
            level = RiskLevel.CRITICAL
        elif defect_return_rate_pct > 5:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="quality_incidents",
            category=RiskCategory.OPERATIONAL,
            label="Quality Incidents",
            metric_value=defect_return_rate_pct,
            warning_threshold=5.0,
            critical_threshold=12.0,
            level=level,
            message=f"Defect/return rate: {defect_return_rate_pct:.1f}%",
        )

    # ── Market & Competitive (§2.3) ───────────────────────────────────

    def market_share_loss(self, qoq_change_pct: float) -> RiskResult:
        """Market share loss: warn -15% QoQ, critical -30% QoQ."""
        level = RiskLevel.INFO
        if qoq_change_pct <= -30:
            level = RiskLevel.CRITICAL
        elif qoq_change_pct <= -15:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="market_share_loss",
            category=RiskCategory.MARKET,
            label="Market Share Loss",
            metric_value=qoq_change_pct,
            warning_threshold=-15.0,
            critical_threshold=-30.0,
            level=level,
            message=f"Market share change QoQ: {qoq_change_pct:+.1f}%",
        )

    def price_war_margin(self, avg_selling_price_pct_of_industry: float) -> RiskResult:
        """Price war: warn ASP <90% of industry avg, critical <75%."""
        level = RiskLevel.INFO
        if avg_selling_price_pct_of_industry < 75:
            level = RiskLevel.CRITICAL
        elif avg_selling_price_pct_of_industry < 90:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="price_war_margin",
            category=RiskCategory.MARKET,
            label="Price War Margin",
            metric_value=avg_selling_price_pct_of_industry,
            warning_threshold=90.0,
            critical_threshold=75.0,
            level=level,
            message=f"ASP at {avg_selling_price_pct_of_industry:.1f}% of industry average",
        )

    def regulatory_shift(self, compliance_cost_pct_of_revenue: float) -> RiskResult:
        """Regulatory shift: warn >3% of revenue, critical >8%."""
        level = RiskLevel.INFO
        if compliance_cost_pct_of_revenue > 8:
            level = RiskLevel.CRITICAL
        elif compliance_cost_pct_of_revenue > 3:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="regulatory_shift",
            category=RiskCategory.MARKET,
            label="Regulatory Shift",
            metric_value=compliance_cost_pct_of_revenue,
            warning_threshold=3.0,
            critical_threshold=8.0,
            level=level,
            message=f"New compliance cost: {compliance_cost_pct_of_revenue:.1f}% of revenue",
        )

    def demand_cliff(self, revenue_vs_forecast_pct: float) -> RiskResult:
        """Demand cliff: warn -25% vs forecast, critical -40%."""
        level = RiskLevel.INFO
        if revenue_vs_forecast_pct <= -40:
            level = RiskLevel.CRITICAL
        elif revenue_vs_forecast_pct <= -25:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="demand_cliff",
            category=RiskCategory.MARKET,
            label="Demand Cliff",
            metric_value=revenue_vs_forecast_pct,
            warning_threshold=-25.0,
            critical_threshold=-40.0,
            level=level,
            message=f"Revenue vs forecast: {revenue_vs_forecast_pct:+.1f}%",
        )

    def competitive_entry(
        self, new_competitor_share_pct: float, losing_share_to_them: bool
    ) -> RiskResult:
        """Competitive entry: detect if >5% share + check if losing share."""
        if new_competitor_share_pct <= 5:
            return RiskResult(
                risk_id="competitive_entry",
                category=RiskCategory.MARKET,
                label="Competitive Entry",
                metric_value=new_competitor_share_pct,
                warning_threshold=5.0,
                critical_threshold=None,
                level=RiskLevel.INFO,
                message="No significant competitor entry detected",
            )
        level = RiskLevel.CRITICAL if losing_share_to_them else RiskLevel.WARNING
        return RiskResult(
            risk_id="competitive_entry",
            category=RiskCategory.MARKET,
            label="Competitive Entry",
            metric_value=new_competitor_share_pct,
            warning_threshold=5.0,
            critical_threshold=None,
            level=level,
            message=f"New competitor at {new_competitor_share_pct:.1f}% share in core segment"
            f"{' and losing share to them' if losing_share_to_them else ''}",
        )

    # ── System & Data Integrity (§2.4) ────────────────────────────────

    def simulation_drift(self, divergence_detected: bool) -> RiskResult:
        """Sim drift: any divergence = critical (deterministic replay broke)."""
        level = RiskLevel.CRITICAL if divergence_detected else RiskLevel.INFO
        return RiskResult(
            risk_id="simulation_drift",
            category=RiskCategory.SYSTEM,
            label="Simulation Drift",
            metric_value=1.0 if divergence_detected else 0.0,
            warning_threshold=None,
            critical_threshold=None,
            level=level,
            message="Deterministic replay divergence detected!"
            if divergence_detected
            else "No simulation drift",
        )

    def agent_anomaly(self, flagged_count: int) -> RiskResult:
        """Agent anomaly: warn ≥1 flagged, critical ≥3 agents same tick."""
        level = RiskLevel.INFO
        if flagged_count >= 3:
            level = RiskLevel.CRITICAL
        elif flagged_count >= 1:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="agent_anomaly",
            category=RiskCategory.SYSTEM,
            label="Agent Anomaly",
            metric_value=float(flagged_count),
            warning_threshold=1.0,
            critical_threshold=3.0,
            level=level,
            message=f"{flagged_count} agent(s) flagged as out-of-distribution this tick",
        )

    def data_corruption(self, mismatch_count: int) -> RiskResult:
        """Data corruption: warn single mismatch, critical ≥2."""
        level = RiskLevel.INFO
        if mismatch_count >= 2:
            level = RiskLevel.CRITICAL
        elif mismatch_count >= 1:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="data_corruption",
            category=RiskCategory.SYSTEM,
            label="Data Corruption",
            metric_value=float(mismatch_count),
            warning_threshold=1.0,
            critical_threshold=2.0,
            level=level,
            message=f"{mismatch_count} checksum mismatch(es) detected",
        )

    def tick_timeout(self, ratio_vs_baseline: float, consecutive: int = 1) -> RiskResult:
        """Tick timeout: warn >2× baseline, critical >5× baseline."""
        level = RiskLevel.INFO
        if ratio_vs_baseline > 5 and consecutive >= 3:
            level = RiskLevel.CRITICAL
        elif ratio_vs_baseline > 2:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="tick_timeout",
            category=RiskCategory.SYSTEM,
            label="Tick Timeout",
            metric_value=ratio_vs_baseline,
            warning_threshold=2.0,
            critical_threshold=5.0,
            level=level,
            message=f"Tick at {ratio_vs_baseline:.1f}× baseline ({consecutive} consecutive)",
        )

    def memory_leak(self, rss_growth_pct: float, consecutive: int) -> RiskResult:
        """Memory leak: warn +10% tick-over-tick for 5 consecutive; critical +25% single tick."""
        level = RiskLevel.INFO
        if rss_growth_pct > 25:
            level = RiskLevel.CRITICAL
        elif rss_growth_pct > 10 and consecutive >= 5:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="memory_leak",
            category=RiskCategory.SYSTEM,
            label="Memory Leak",
            metric_value=rss_growth_pct,
            warning_threshold=10.0,
            critical_threshold=25.0,
            level=level,
            message=f"RSS growth: {rss_growth_pct:+.1f}% ({consecutive} consecutive ticks)",
        )

    def state_inconsistency(self, breaches: int, same_breach_consecutive: int) -> RiskResult:
        """State inconsistency: any breach = warn; same breach 2+ ticks = critical."""
        if breaches == 0:
            return RiskResult(
                risk_id="state_inconsistency",
                category=RiskCategory.SYSTEM,
                label="State Inconsistency",
                metric_value=0.0,
                warning_threshold=None,
                critical_threshold=None,
                level=RiskLevel.INFO,
                message="All cross-entity invariants hold",
            )
        level = RiskLevel.CRITICAL if same_breach_consecutive >= 2 else RiskLevel.WARNING
        return RiskResult(
            risk_id="state_inconsistency",
            category=RiskCategory.SYSTEM,
            label="State Inconsistency",
            metric_value=float(breaches),
            warning_threshold=None,
            critical_threshold=None,
            level=level,
            message=f"{breaches} invariant breach(es) detected ({same_breach_consecutive} consecutive)",
        )

    def agent_loop_detection(self, repeat_count: int) -> RiskResult:
        """Agent loop: warn >5 repeats, critical >10 repeats."""
        level = RiskLevel.INFO
        if repeat_count > 10:
            level = RiskLevel.CRITICAL
        elif repeat_count > 5:
            level = RiskLevel.WARNING
        return RiskResult(
            risk_id="agent_loop_detection",
            category=RiskCategory.SYSTEM,
            label="Agent Loop Detection",
            metric_value=float(repeat_count),
            warning_threshold=5.0,
            critical_threshold=10.0,
            level=level,
            message=f"Agent repeated same decision pattern {repeat_count} consecutive ticks",
        )

    # ── Bulk evaluation ────────────────────────────────────────────────

    def evaluate_all(self, state: Dict[str, Any]) -> List[RiskResult]:
        """Run every metric that has sufficient data in *state*.

        State keys follow the metric names above — each is optional; missing
        keys cause that metric to be skipped.
        """
        results: List[RiskResult] = []

        # Financial
        if "cash_runway_months" in state:
            results.append(self.cash_runway(state["cash_runway_months"]))
        if "burn_rate_mom_pct" in state and "burn_rate_trailing_3m_avg" in state:
            results.append(
                self.burn_rate_spike(state["burn_rate_mom_pct"], state["burn_rate_trailing_3m_avg"])
            )
        if "revenue_concentration_pct" in state:
            results.append(self.revenue_concentration(state["revenue_concentration_pct"]))
        if "debt_service_ratio_pct" in state:
            results.append(self.debt_service_ratio(state["debt_service_ratio_pct"]))
        if "current_gross_margin" in state and "trailing_3m_gross_margin" in state:
            results.append(
                self.margin_erosion(
                    state["current_gross_margin"], state["trailing_3m_gross_margin"]
                )
            )
        if "current_ratio" in state:
            results.append(self.liquidity_crunch(state["current_ratio"]))

        # Operational
        if "capacity_utilisation_pct" in state:
            sustained = state.get("bottleneck_sustained_ticks", 1)
            results.append(self.production_bottleneck(state["capacity_utilisation_pct"], sustained))
        if "key_person_critical_output_pct" in state:
            has_backup = state.get("key_person_has_backup", False)
            results.append(
                self.key_person_dependency(state["key_person_critical_output_pct"], has_backup)
            )
        if "attrition_rate_pct" in state:
            results.append(self.attrition_spike(state["attrition_rate_pct"]))
        if "supply_concentration_pct" in state:
            results.append(self.supply_chain_concentration(state["supply_concentration_pct"]))
        if "dio_days" in state:
            results.append(self.inventory_imbalance(state["dio_days"]))
        if "defect_rate_pct" in state:
            results.append(self.quality_incidents(state["defect_rate_pct"]))

        # Market
        if "market_share_qoq_pct" in state:
            results.append(self.market_share_loss(state["market_share_qoq_pct"]))
        if "asp_vs_industry_pct" in state:
            results.append(self.price_war_margin(state["asp_vs_industry_pct"]))
        if "compliance_cost_pct" in state:
            results.append(self.regulatory_shift(state["compliance_cost_pct"]))
        if "revenue_vs_forecast_pct" in state:
            results.append(self.demand_cliff(state["revenue_vs_forecast_pct"]))
        if "new_competitor_share_pct" in state:
            losing = state.get("losing_share_to_competitor", False)
            results.append(self.competitive_entry(state["new_competitor_share_pct"], losing))

        # System
        if "sim_drift_detected" in state:
            results.append(self.simulation_drift(state["sim_drift_detected"]))
        if "agent_anomaly_count" in state:
            results.append(self.agent_anomaly(state["agent_anomaly_count"]))
        if "data_corruption_count" in state:
            results.append(self.data_corruption(state["data_corruption_count"]))
        if "tick_timeout_ratio" in state:
            consecutive = state.get("tick_timeout_consecutive", 1)
            results.append(self.tick_timeout(state["tick_timeout_ratio"], consecutive))
        if "memory_rss_growth_pct" in state:
            consecutive = state.get("memory_leak_consecutive", 1)
            results.append(self.memory_leak(state["memory_rss_growth_pct"], consecutive))
        if "state_inconsistency_breaches" in state:
            same = state.get("state_inconsistency_consecutive", 1)
            results.append(self.state_inconsistency(state["state_inconsistency_breaches"], same))
        if "agent_loop_repeats" in state:
            results.append(self.agent_loop_detection(state["agent_loop_repeats"]))

        return results


# ---------------------------------------------------------------------------
# SafeModeChecker
# ---------------------------------------------------------------------------


class SafeModeChecker:
    """Evaluate automatic safe-mode triggers from risk-framework.md §3.1.

    Call ``check(results)`` with the output of ``RiskCalculator.evaluate_all()``
    to determine which triggers (SM-01 through SM-07) have fired.
    """

    TRIGGER_SPECS: Dict[SafeModeTriggerID, str] = {
        SafeModeTriggerID.SM01_CRITICAL_FINANCIAL: "Any critical financial threshold breached",
        SafeModeTriggerID.SM02_MULTI_CRITICAL: "≥2 critical thresholds of any type breached simultaneously",
        SafeModeTriggerID.SM03_DATA_INTEGRITY: "Data integrity mismatch at critical level",
        SafeModeTriggerID.SM04_AGENT_LOOP: "Agent loop detection at critical level (10+ repeats)",
        SafeModeTriggerID.SM05_SIM_DRIFT: "Simulation drift detected",
        SafeModeTriggerID.SM06_TICK_TIMEOUT: "Tick timeout >5× baseline consecutively",
        SafeModeTriggerID.SM07_MEMORY_LEAK: "Memory leak at critical threshold",
    }

    # Risk IDs that map to each trigger for auto-correlation
    _TRIGGER_RISK_MAP: Dict[SafeModeTriggerID, List[str]] = {
        SafeModeTriggerID.SM01_CRITICAL_FINANCIAL: [
            "cash_runway",
            "burn_rate_spike",
            "revenue_concentration",
            "debt_service_ratio",
            "margin_erosion",
            "liquidity_crunch",
        ],
        SafeModeTriggerID.SM03_DATA_INTEGRITY: ["data_corruption"],
        SafeModeTriggerID.SM04_AGENT_LOOP: ["agent_loop_detection"],
        SafeModeTriggerID.SM05_SIM_DRIFT: ["simulation_drift"],
        SafeModeTriggerID.SM06_TICK_TIMEOUT: ["tick_timeout"],
        SafeModeTriggerID.SM07_MEMORY_LEAK: ["memory_leak"],
    }

    def check(self, results: List[RiskResult]) -> List[SafeModeTrigger]:
        """Return all safe-mode triggers that fire given the risk results."""
        triggers: List[SafeModeTrigger] = []
        critical_risks = [r for r in results if r.level == RiskLevel.CRITICAL]

        # SM-01: any critical financial
        critical_financial = [r for r in critical_risks if r.category == RiskCategory.FINANCIAL]
        if critical_financial:
            triggers.append(
                SafeModeTrigger(
                    trigger_id=SafeModeTriggerID.SM01_CRITICAL_FINANCIAL,
                    description=self.TRIGGER_SPECS[SafeModeTriggerID.SM01_CRITICAL_FINANCIAL],
                    risk_ids=[r.risk_id for r in critical_financial],
                )
            )

        # SM-02: ≥2 critical thresholds of ANY type
        risk_types_with_critical = len(set(r.risk_id for r in critical_risks))
        if risk_types_with_critical >= 2:
            triggers.append(
                SafeModeTrigger(
                    trigger_id=SafeModeTriggerID.SM02_MULTI_CRITICAL,
                    description=self.TRIGGER_SPECS[SafeModeTriggerID.SM02_MULTI_CRITICAL],
                    risk_ids=[r.risk_id for r in critical_risks],
                )
            )

        # SM-03: data integrity at critical
        self._check_mapped_triggers(results, critical_risks, triggers)

        # SM-04 through SM-07 are caught by the mapped check above
        return triggers

    def _check_mapped_triggers(
        self,
        all_results: List[RiskResult],
        critical_risks: List[RiskResult],
        triggers: List[SafeModeTrigger],
    ) -> None:
        """Check triggers that map one-to-one with critical risk results."""
        critical_ids = {r.risk_id for r in critical_risks}
        for trigger_id, risk_ids in self._TRIGGER_RISK_MAP.items():
            if trigger_id in (
                SafeModeTriggerID.SM01_CRITICAL_FINANCIAL,
                SafeModeTriggerID.SM02_MULTI_CRITICAL,
            ):
                continue  # handled above
            matched = [rid for rid in risk_ids if rid in critical_ids]
            if matched:
                triggers.append(
                    SafeModeTrigger(
                        trigger_id=trigger_id,
                        description=self.TRIGGER_SPECS[trigger_id],
                        risk_ids=matched,
                    )
                )

    def should_enter_safe_mode(self, triggers: List[SafeModeTrigger]) -> bool:
        """Return True if at least one automatic safe-mode trigger fired."""
        return len(triggers) > 0


# ---------------------------------------------------------------------------
# PositionSizer
# ---------------------------------------------------------------------------


class PositionSizer:
    """Position-sizing validator per risk-framework.md §7.

    Stage-based limits:

    | Stage  | Max Single | Max Sector | Min Cash |
    |--------|------------|------------|----------|
    | Early  | 15%        | 30%        | 15%      |
    | Growth | 20%        | 35%        | 15%      |
    | Mature | 25%        | 40%        | 15%      |
    """

    _STAGE_LIMITS: Dict[CompanyStage, Dict[str, float]] = {
        CompanyStage.EARLY: {
            "max_single_pct": 15.0,
            "max_sector_pct": 30.0,
            "min_cash_pct": 15.0,
        },
        CompanyStage.GROWTH: {
            "max_single_pct": 20.0,
            "max_sector_pct": 35.0,
            "min_cash_pct": 15.0,
        },
        CompanyStage.MATURE: {
            "max_single_pct": 25.0,
            "max_sector_pct": 40.0,
            "min_cash_pct": 15.0,
        },
    }

    CONCENTRATION_FLAG_PCT = 15.0  # any single position > 15% → flag

    def get_limits(self, stage: CompanyStage) -> Dict[str, float]:
        """Return the position limit dict for a given company stage."""
        return self._STAGE_LIMITS[stage]

    def validate(
        self,
        capital: float,
        position_size: float,
        sector_total: float,
        total_exposure: float,
        stage: CompanyStage,
    ) -> PositionSizingResult:
        """Validate a proposed (or current) position against stage limits.

        Parameters
        ----------
        capital : float
            Total deployable capital.
        position_size : float
            Size of the single position being checked.
        sector_total : float
            Total deployed in the same sector.
        total_exposure : float
            Total capital deployed across all positions.
        stage : CompanyStage
            Maturity stage of the company.

        Returns
        -------
        PositionSizingResult
        """
        limits = self._STAGE_LIMITS[stage]

        if capital <= 0:
            return PositionSizingResult(
                valid=False,
                position_size=position_size,
                position_pct=0.0,
                sector_total_pct=0.0,
                total_exposure_pct=0.0,
                max_single_pct=limits["max_single_pct"],
                max_sector_pct=limits["max_sector_pct"],
                min_cash_pct=limits["min_cash_pct"],
                flags=["Zero or negative capital"],
                message="Cannot validate position: capital <= 0",
            )

        position_pct = (position_size / capital) * 100
        sector_pct = (sector_total / capital) * 100
        exposure_pct = (total_exposure / capital) * 100
        cash_pct = 100 - exposure_pct

        flags: List[str] = []
        valid = True

        # Check single-position limit
        if position_pct > limits["max_single_pct"]:
            flags.append(
                f"Single position {position_pct:.1f}% exceeds limit {limits['max_single_pct']:.0f}%"
            )
            valid = False

        # Check sector concentration
        if sector_pct > limits["max_sector_pct"]:
            flags.append(
                f"Sector total {sector_pct:.1f}% exceeds limit {limits['max_sector_pct']:.0f}%"
            )
            valid = False

        # Check cash reserve floor
        if cash_pct < limits["min_cash_pct"]:
            flags.append(f"Cash reserves {cash_pct:.1f}% below floor {limits['min_cash_pct']:.0f}%")
            valid = False

        # Concentration check flag (non-blocking)
        if position_pct > self.CONCENTRATION_FLAG_PCT:
            flags.append(
                f"Concentration flag: single position at {position_pct:.1f}% "
                f"exceeds {self.CONCENTRATION_FLAG_PCT:.0f}% review threshold"
            )

        message = "Position within limits" if valid else "; ".join(flags)
        return PositionSizingResult(
            valid=valid,
            position_size=position_size,
            position_pct=position_pct,
            sector_total_pct=sector_pct,
            total_exposure_pct=exposure_pct,
            max_single_pct=limits["max_single_pct"],
            max_sector_pct=limits["max_sector_pct"],
            min_cash_pct=limits["min_cash_pct"],
            flags=flags,
            message=message,
        )


# ---------------------------------------------------------------------------
# DrawdownMonitor
# ---------------------------------------------------------------------------


class DrawdownMonitor:
    """Drawdown tracking and escalation per risk-framework.md §8.

    Maintains peak tracker for portfolio value so drawdown can be computed
    from the last known peak.
    """

    def __init__(self) -> None:
        self._peak_portfolio: Optional[float] = None
        self._peak_revenue_4q: Optional[float] = None
        self._peak_cash: Optional[float] = None
        self._consecutive_low_risk_ticks: int = 0

    # ── Peak tracking ─────────────────────────────────────────────────

    @property
    def peak_portfolio(self) -> Optional[float]:
        return self._peak_portfolio

    @peak_portfolio.setter
    def peak_portfolio(self, value: float) -> None:
        if self._peak_portfolio is None or value > self._peak_portfolio:
            self._peak_portfolio = value

    @property
    def peak_revenue_4q(self) -> Optional[float]:
        return self._peak_revenue_4q

    @peak_revenue_4q.setter
    def peak_revenue_4q(self, value: float) -> None:
        if self._peak_revenue_4q is None or value > self._peak_revenue_4q:
            self._peak_revenue_4q = value

    @property
    def peak_cash(self) -> Optional[float]:
        return self._peak_cash

    @peak_cash.setter
    def peak_cash(self, value: float) -> None:
        if self._peak_cash is None or value > self._peak_cash:
            self._peak_cash = value

    # ── Core checks ───────────────────────────────────────────────────

    def check_portfolio_drawdown(self, current_value: float) -> Tuple[RiskLevel, float]:
        """Check portfolio drawdown from peak.  Warn at -15%, critical at -25%."""
        if self._peak_portfolio is None or self._peak_portfolio == 0:
            self._peak_portfolio = current_value
            return RiskLevel.INFO, 0.0
        # Update peak if current exceeds it (no drawdown to report)
        if current_value > self._peak_portfolio:
            self._peak_portfolio = current_value
            return RiskLevel.INFO, 0.0
        drawdown = ((current_value - self._peak_portfolio) / self._peak_portfolio) * 100
        if drawdown <= -25:
            return RiskLevel.CRITICAL, drawdown
        if drawdown <= -15:
            return RiskLevel.WARNING, drawdown
        return RiskLevel.INFO, drawdown

    def check_revenue_drawdown(self, current_4q_avg: float) -> Tuple[RiskLevel, float]:
        """Check revenue drawdown from trailing-4Q peak.  Warn -20%, critical -35%."""
        if self._peak_revenue_4q is None or self._peak_revenue_4q == 0:
            self._peak_revenue_4q = current_4q_avg
            return RiskLevel.INFO, 0.0
        drawdown = ((current_4q_avg - self._peak_revenue_4q) / self._peak_revenue_4q) * 100
        if drawdown <= -35:
            return RiskLevel.CRITICAL, drawdown
        if drawdown <= -20:
            return RiskLevel.WARNING, drawdown
        return RiskLevel.INFO, drawdown

    def check_cash_drawdown(
        self, current_cash: float, previous_cash: float
    ) -> Tuple[RiskLevel, float]:
        """Check cash reserve MoM drawdown.  Warn -30%, critical -50%."""
        if previous_cash == 0:
            return RiskLevel.INFO, 0.0
        mom_change = ((current_cash - previous_cash) / previous_cash) * 100
        if mom_change <= -50:
            return RiskLevel.CRITICAL, mom_change
        if mom_change <= -30:
            return RiskLevel.WARNING, mom_change
        return RiskLevel.INFO, mom_change

    # ── Aggregate ─────────────────────────────────────────────────────

    def evaluate(
        self,
        portfolio_value: float,
        revenue_4q_avg: float,
        current_cash: float,
        previous_cash: float,
    ) -> DrawdownResult:
        """Run all three drawdown checks and return an aggregate result.

        Updates peak trackers as a side-effect.
        """
        port_level, port_dd = self.check_portfolio_drawdown(portfolio_value)
        rev_level, rev_dd = self.check_revenue_drawdown(revenue_4q_avg)
        cash_level, cash_dd = self.check_cash_drawdown(current_cash, previous_cash)

        flags: List[str] = []
        if port_level == RiskLevel.CRITICAL:
            flags.append("Portfolio drawdown critical")
        if rev_level == RiskLevel.CRITICAL:
            flags.append("Revenue drawdown critical")
        if cash_level == RiskLevel.CRITICAL:
            flags.append("Cash drawdown critical")

        # Overall level = worst of the three
        levels = [port_level, rev_level, cash_level]
        overall = max(levels, key=lambda l: list(RiskLevel).index(l))

        low_risk_required = overall == RiskLevel.CRITICAL

        message_parts = [
            f"Portfolio: {port_dd:+.1f}% ({port_level.value})",
            f"Revenue: {rev_dd:+.1f}% ({rev_level.value})",
            f"Cash: {cash_dd:+.1f}% ({cash_level.value})",
        ]
        message = " | ".join(message_parts)

        return DrawdownResult(
            portfolio_drawdown_pct=port_dd,
            revenue_drawdown_pct=rev_dd,
            cash_drawdown_pct=cash_dd,
            portfolio_level=port_level,
            revenue_level=rev_level,
            cash_level=cash_level,
            overall_level=overall,
            low_risk_mode_required=low_risk_required,
            flags=flags,
            message=message,
        )

    # ── Low-risk mode (§8, §9) ────────────────────────────────────────

    def tick_in_low_risk_mode(self) -> None:
        """Record one tick in low-risk mode (for recovery countdown)."""
        self._consecutive_low_risk_ticks += 1

    def reset_low_risk_ticks(self) -> None:
        """Reset the low-risk tick counter (e.g. if a new breach occurs)."""
        self._consecutive_low_risk_ticks = 0

    @property
    def low_risk_ticks_elapsed(self) -> int:
        return self._consecutive_low_risk_ticks

    def low_risk_mode_complete(self, required_ticks: int = 4) -> bool:
        """Check whether enough low-risk ticks have elapsed to exit."""
        return self._consecutive_low_risk_ticks >= required_ticks

    @staticmethod
    def low_risk_mode_constraints() -> Dict[str, str]:
        """Return the low-risk mode constraints from §9."""
        return {
            "new_hires": "Freeze except critical replacements",
            "capex": "Maintenance only; no expansion",
            "dividends_buybacks": "Suspended",
            "debt": "No new debt; existing must be serviced",
            "mergers_acquisitions": "Prohibited",
            "cash_reserve_target": "Raise to ≥ 6 months runway",
        }


# ---------------------------------------------------------------------------
# RiskEngine (orchestrator)
# ---------------------------------------------------------------------------


class RiskEngine:
    """Top-level risk orchestrator.

    Wires together RiskCalculator, SafeModeChecker, PositionSizer, and
    DrawdownMonitor into a single ``full_assessment()`` call.

    Also manages the risk-event log (§6).
    """

    def __init__(self, event_log_path: Optional[str] = None) -> None:
        self.calculator = RiskCalculator()
        self.safe_mode_checker = SafeModeChecker()
        self.position_sizer = PositionSizer()
        self.drawdown_monitor = DrawdownMonitor()
        self._event_log_path = event_log_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "risk-events.jsonl"
        )
        self._in_safe_mode: bool = False
        self._low_risk_mode: bool = False

    # ── Main assessment ───────────────────────────────────────────────

    def full_assessment(self, state: Dict[str, Any]) -> RiskReport:
        """Run the complete risk assessment for the current tick.

        Steps:
        1. Evaluate all risk metrics.
        2. Check safe-mode triggers.
        3. Validate position sizing (if position data in state).
        4. Evaluate drawdown.
        5. Determine highest level & alert level.
        """
        company = state.get("company", "unknown")
        tick = state.get("tick", 0)

        # 1. Risk metrics
        results = self.calculator.evaluate_all(state)

        # 2. Safe mode triggers
        safe_mode_triggers = self.safe_mode_checker.check(results)
        if safe_mode_triggers:
            self._in_safe_mode = True

        # 3. Position sizing
        position_result: Optional[PositionSizingResult] = None
        if all(
            k in state
            for k in ("capital", "position_size", "sector_total", "total_exposure", "company_stage")
        ):
            stage = CompanyStage(state["company_stage"])
            position_result = self.position_sizer.validate(
                capital=state["capital"],
                position_size=state["position_size"],
                sector_total=state["sector_total"],
                total_exposure=state["total_exposure"],
                stage=stage,
            )

        # 4. Drawdown
        drawdown_result: Optional[DrawdownResult] = None
        if all(
            k in state
            for k in ("portfolio_value", "revenue_4q_avg", "cash_balance", "previous_cash_balance")
        ):
            drawdown_result = self.drawdown_monitor.evaluate(
                portfolio_value=state["portfolio_value"],
                revenue_4q_avg=state["revenue_4q_avg"],
                current_cash=state["cash_balance"],
                previous_cash=state["previous_cash_balance"],
            )
            if drawdown_result.low_risk_mode_required:
                self._low_risk_mode = True

        # 5. Determine highest level
        highest_level = RiskLevel.INFO
        for r in results:
            if self._severity_index(r.level) > self._severity_index(highest_level):
                highest_level = r.level

        alert_level = self._risk_level_to_alert(highest_level, safe_mode_triggers)
        summary = self._build_summary(
            highest_level, len(results), len(safe_mode_triggers), position_result, drawdown_result
        )

        return RiskReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            tick=tick,
            company=company,
            results=results,
            safe_mode_triggers=safe_mode_triggers,
            position_sizing=position_result,
            drawdown=drawdown_result,
            highest_level=highest_level,
            alert_level=alert_level,
            low_risk_mode=self._low_risk_mode,
            summary=summary,
        )

    # ── Safe mode management ──────────────────────────────────────────

    @property
    def in_safe_mode(self) -> bool:
        return self._in_safe_mode

    def enter_safe_mode(self, state: Dict[str, Any]) -> None:
        """Enter safe mode: pause tick, block writes, snapshot."""
        self._in_safe_mode = True
        logger.warning(
            "SAFE MODE ENTERED | company=%s tick=%s",
            state.get("company", "?"),
            state.get("tick", "?"),
        )

    def resume_from_safe_mode(self) -> None:
        """Resume normal operation after CEO explicit command."""
        self._in_safe_mode = False
        logger.info("Safe mode cleared — normal operation resumed")

    @property
    def low_risk_mode(self) -> bool:
        return self._low_risk_mode

    def exit_low_risk_mode(self) -> None:
        """Exit low-risk mode (CEO directive ``/sim risk-mode normal``)."""
        self._low_risk_mode = False
        logger.info("Low-risk mode exited via CEO directive")

    # ── Event logging (§6) ────────────────────────────────────────────

    def log_event(self, event: RiskEvent) -> None:
        """Append a risk event to the JSONL log file."""
        log_dir = os.path.dirname(self._event_log_path)
        os.makedirs(log_dir, exist_ok=True)
        line = json.dumps(asdict(event)) + "\n"
        with open(self._event_log_path, "a") as f:
            f.write(line)
        logger.info("Risk event logged: %s (%s / %s)", event.id, event.risk, event.level)

    def read_event_log(self, limit: int = 50) -> List[RiskEvent]:
        """Read the most recent *limit* events from the log."""
        if not os.path.exists(self._event_log_path):
            return []
        events: List[RiskEvent] = []
        with open(self._event_log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    events.append(RiskEvent(**data))
        return events[-limit:]

    # ── Internals ─────────────────────────────────────────────────────

    @staticmethod
    def _severity_index(level: RiskLevel) -> int:
        ordering = {
            RiskLevel.INFO: 0,
            RiskLevel.WATCH: 1,
            RiskLevel.WARNING: 2,
            RiskLevel.CRITICAL: 3,
            RiskLevel.SYSTEM_EMERGENCY: 4,
        }
        return ordering.get(level, 0)

    @staticmethod
    def _risk_level_to_alert(level: RiskLevel, triggers: List[SafeModeTrigger]) -> AlertLevel:
        if triggers:
            return AlertLevel.L5_SYSTEM_EMERGENCY
        mapping = {
            RiskLevel.INFO: AlertLevel.L1_INFO,
            RiskLevel.WATCH: AlertLevel.L2_WATCH,
            RiskLevel.WARNING: AlertLevel.L3_WARNING,
            RiskLevel.CRITICAL: AlertLevel.L4_CRITICAL,
            RiskLevel.SYSTEM_EMERGENCY: AlertLevel.L5_SYSTEM_EMERGENCY,
        }
        return mapping.get(level, AlertLevel.L1_INFO)

    @staticmethod
    def _build_summary(
        highest: RiskLevel,
        metric_count: int,
        trigger_count: int,
        position: Optional[PositionSizingResult],
        drawdown: Optional[DrawdownResult],
    ) -> str:
        parts = [f"Highest risk: {highest.value} ({metric_count} metrics evaluated)"]
        if trigger_count:
            parts.append(f"Safe mode triggers: {trigger_count}")
        if position and not position.valid:
            parts.append(f"Position sizing: {len(position.flags)} violation(s)")
        if drawdown and drawdown.overall_level.is_warning_or_above():
            parts.append(f"Drawdown: {drawdown.overall_level.value}")
        return " | ".join(parts)

    # ── Tick consumer interface ───────────────────────────────────────

    def on_tick(self, state: Dict[str, Any]) -> RiskReport:
        """Consumer entry point for the simulation tick engine.

        Called by the wiring layer when a tick completes. Delegates to
        ``full_assessment()`` and logs any risk events at WARNING or above.

        This method is the integration point between the tick engine
        (core/simulation) and the risk engine (app/services). The tick
        engine does NOT import risk_engine directly — the wiring layer
        subscribes to tick events and calls this method.

        Args:
            state: company state dict (same shape as full_assessment input)

        Returns:
            RiskReport with current risk assessment
        """
        report = self.full_assessment(state)

        # Log events for any warning-or-above risks
        for result in report.results:
            if result.level.is_warning_or_above():
                event = RiskEvent.create(
                    tick=report.tick,
                    company=report.company,
                    risk=result.risk_id,
                    level=result.level.value,
                    metric=result.metric_value,
                    threshold=(
                        result.warning_threshold
                        if result.level == RiskLevel.WARNING
                        else result.critical_threshold
                    )
                    or 0.0,
                    trigger=(
                        report.safe_mode_triggers[0].trigger_id.value
                        if report.safe_mode_triggers
                        else None
                    ),
                    safe_mode=self._in_safe_mode,
                )
                self.log_event(event)

        return report
