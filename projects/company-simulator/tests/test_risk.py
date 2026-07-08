"""
Tests for the Risk Engine module (app/services/risk_engine.py).

Covers all four components plus the orchestrator:
- RiskCalculator  — every metric boundary and edge case
- SafeModeChecker — all automatic triggers (SM-01 – SM-07)
- PositionSizer   — stage limits, concentration flags
- DrawdownMonitor — drawdown checks, peak tracking, low-risk mode
- RiskEngine      — full assessment pipeline, event logging, lifecycle
"""

from __future__ import annotations

import os
import tempfile

import pytest

from app.services.risk_engine import (
    AlertLevel,
    CompanyStage,
    DrawdownMonitor,
    PositionSizer,
    RiskCalculator,
    RiskCategory,
    RiskEngine,
    RiskEvent,
    RiskLevel,
    RiskReport,
    RiskResult,
    SafeModeChecker,
    SafeModeTrigger,
    SafeModeTriggerID,
)


# ======================================================================
# RiskCalculator — every metric, boundary values, edge cases
# ======================================================================


class TestCashRunway:
    def test_healthy(self):
        calc = RiskCalculator()
        r = calc.cash_runway(12.0)
        assert r.level == RiskLevel.INFO
        assert r.risk_id == "cash_runway"

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.cash_runway(4.5)
        assert r.level == RiskLevel.WARNING

    def test_warning_boundary_just_below_6(self):
        calc = RiskCalculator()
        r = calc.cash_runway(5.99)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.cash_runway(2.0)
        assert r.level == RiskLevel.CRITICAL

    def test_critical_boundary_just_below_3(self):
        calc = RiskCalculator()
        r = calc.cash_runway(2.99)
        assert r.level == RiskLevel.CRITICAL

    def test_exactly_6_is_info(self):
        calc = RiskCalculator()
        r = calc.cash_runway(6.0)
        assert r.level == RiskLevel.INFO

    def test_exactly_3_is_warning(self):
        calc = RiskCalculator()
        r = calc.cash_runway(3.0)  # threshold is strictly < 3
        assert r.level == RiskLevel.WARNING

    def test_zero_runway(self):
        calc = RiskCalculator()
        r = calc.cash_runway(0.0)
        assert r.level == RiskLevel.CRITICAL

    def test_negative_runway(self):
        calc = RiskCalculator()
        r = calc.cash_runway(-1.0)
        assert r.level == RiskLevel.CRITICAL


class TestBurnRateSpike:
    def test_normal(self):
        calc = RiskCalculator()
        r = calc.burn_rate_spike(mom_change_pct=10.0, trailing_3m_avg=10.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        # 10 vs 10 avg → 0% change. To get +50% we need (x-10)/10 = 0.50 → x=15
        # Actually: change_vs_avg = (15 - 10)/10 * 100 = 50%
        r = calc.burn_rate_spike(mom_change_pct=15.0, trailing_3m_avg=10.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        # (20 - 10)/10 * 100 = 100%
        r = calc.burn_rate_spike(mom_change_pct=20.0, trailing_3m_avg=10.0)
        assert r.level == RiskLevel.CRITICAL

    def test_warning_slightly_above_50(self):
        calc = RiskCalculator()
        r = calc.burn_rate_spike(mom_change_pct=15.1, trailing_3m_avg=10.0)
        assert r.level == RiskLevel.WARNING

    def test_no_trailing_data(self):
        calc = RiskCalculator()
        r = calc.burn_rate_spike(mom_change_pct=999.0, trailing_3m_avg=0.0)
        assert r.level == RiskLevel.INFO
        assert "No trailing data" in r.message

    def test_burn_decrease_is_info(self):
        calc = RiskCalculator()
        r = calc.burn_rate_spike(mom_change_pct=5.0, trailing_3m_avg=10.0)
        assert r.level == RiskLevel.INFO


class TestRevenueConcentration:
    def test_diversified(self):
        calc = RiskCalculator()
        r = calc.revenue_concentration(20.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.revenue_concentration(45.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.revenue_concentration(75.0)
        assert r.level == RiskLevel.CRITICAL

    def test_warning_boundary(self):
        calc = RiskCalculator()
        r = calc.revenue_concentration(40.1)
        assert r.level == RiskLevel.WARNING

    def test_critical_boundary(self):
        calc = RiskCalculator()
        r = calc.revenue_concentration(60.1)
        assert r.level == RiskLevel.CRITICAL

    def test_exactly_100(self):
        calc = RiskCalculator()
        r = calc.revenue_concentration(100.0)
        assert r.level == RiskLevel.CRITICAL


class TestDebtServiceRatio:
    def test_healthy(self):
        calc = RiskCalculator()
        r = calc.debt_service_ratio(20.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.debt_service_ratio(40.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.debt_service_ratio(55.0)
        assert r.level == RiskLevel.CRITICAL

    def test_over_100(self):
        calc = RiskCalculator()
        r = calc.debt_service_ratio(150.0)
        assert r.level == RiskLevel.CRITICAL


class TestMarginErosion:
    def test_stable(self):
        calc = RiskCalculator()
        r = calc.margin_erosion(current_gross_margin=60.0, trailing_3m_avg=62.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.margin_erosion(current_gross_margin=50.0, trailing_3m_avg=62.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.margin_erosion(current_gross_margin=40.0, trailing_3m_avg=62.0)
        assert r.level == RiskLevel.CRITICAL

    def test_no_drop_is_info(self):
        calc = RiskCalculator()
        r = calc.margin_erosion(current_gross_margin=70.0, trailing_3m_avg=65.0)
        assert r.level == RiskLevel.INFO


class TestLiquidityCrunch:
    def test_healthy(self):
        calc = RiskCalculator()
        r = calc.liquidity_crunch(2.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.liquidity_crunch(1.2)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.liquidity_crunch(0.8)
        assert r.level == RiskLevel.CRITICAL

    def test_exactly_1_dot_5(self):
        calc = RiskCalculator()
        r = calc.liquidity_crunch(1.5)
        assert r.level == RiskLevel.INFO

    def test_exactly_1_dot_0_is_warning(self):
        calc = RiskCalculator()
        r = calc.liquidity_crunch(1.0)  # threshold is strictly < 1.0
        assert r.level == RiskLevel.WARNING

    def test_near_zero(self):
        calc = RiskCalculator()
        r = calc.liquidity_crunch(0.1)
        assert r.level == RiskLevel.CRITICAL


class TestProductionBottleneck:
    def test_normal_load(self):
        calc = RiskCalculator()
        r = calc.production_bottleneck(70.0, sustained_ticks=5)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.production_bottleneck(90.0, sustained_ticks=3)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.production_bottleneck(96.0, sustained_ticks=3)
        assert r.level == RiskLevel.CRITICAL

    def test_high_but_not_sustained(self):
        calc = RiskCalculator()
        r = calc.production_bottleneck(96.0, sustained_ticks=1)
        assert r.level == RiskLevel.INFO

    def test_warning_but_not_sustained(self):
        calc = RiskCalculator()
        r = calc.production_bottleneck(90.0, sustained_ticks=1)
        assert r.level == RiskLevel.INFO

    def test_max_capacity(self):
        calc = RiskCalculator()
        r = calc.production_bottleneck(100.0, sustained_ticks=5)
        assert r.level == RiskLevel.CRITICAL


class TestKeyPersonDependency:
    def test_no_dependency(self):
        calc = RiskCalculator()
        r = calc.key_person_dependency(critical_output_pct=25.0, has_backup=True)
        assert r.level == RiskLevel.INFO

    def test_flagged_with_backup(self):
        calc = RiskCalculator()
        r = calc.key_person_dependency(critical_output_pct=40.0, has_backup=True)
        assert r.level == RiskLevel.WARNING

    def test_critical_no_backup(self):
        calc = RiskCalculator()
        r = calc.key_person_dependency(critical_output_pct=40.0, has_backup=False)
        assert r.level == RiskLevel.CRITICAL

    def test_exactly_30_is_safe(self):
        calc = RiskCalculator()
        r = calc.key_person_dependency(critical_output_pct=30.0, has_backup=False)
        assert r.level == RiskLevel.INFO

    def test_100_percent_no_backup(self):
        calc = RiskCalculator()
        r = calc.key_person_dependency(critical_output_pct=100.0, has_backup=False)
        assert r.level == RiskLevel.CRITICAL


class TestAttritionSpike:
    def test_normal(self):
        calc = RiskCalculator()
        r = calc.attrition_spike(10.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.attrition_spike(25.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.attrition_spike(40.0)
        assert r.level == RiskLevel.CRITICAL

    def test_boundary_warning(self):
        calc = RiskCalculator()
        r = calc.attrition_spike(20.1)
        assert r.level == RiskLevel.WARNING

    def test_boundary_critical(self):
        calc = RiskCalculator()
        r = calc.attrition_spike(35.1)
        assert r.level == RiskLevel.CRITICAL


class TestSupplyChainConcentration:
    def test_diversified(self):
        calc = RiskCalculator()
        r = calc.supply_chain_concentration(30.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.supply_chain_concentration(60.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.supply_chain_concentration(80.0)
        assert r.level == RiskLevel.CRITICAL


class TestInventoryImbalance:
    def test_normal(self):
        calc = RiskCalculator()
        r = calc.inventory_imbalance(45.0)
        assert r.level == RiskLevel.INFO

    def test_warning_high(self):
        calc = RiskCalculator()
        r = calc.inventory_imbalance(100.0)
        assert r.level == RiskLevel.WARNING

    def test_critical_high(self):
        calc = RiskCalculator()
        r = calc.inventory_imbalance(160.0)
        assert r.level == RiskLevel.CRITICAL

    def test_warning_low(self):
        calc = RiskCalculator()
        r = calc.inventory_imbalance(10.0)
        assert r.level == RiskLevel.WARNING

    def test_critical_low(self):
        calc = RiskCalculator()
        r = calc.inventory_imbalance(4.0)
        assert r.level == RiskLevel.CRITICAL

    def test_exactly_15_is_info(self):
        calc = RiskCalculator()
        r = calc.inventory_imbalance(15.0)
        assert r.level == RiskLevel.INFO

    def test_exactly_90_is_info(self):
        calc = RiskCalculator()
        r = calc.inventory_imbalance(90.0)  # threshold is strictly > 90
        assert r.level == RiskLevel.INFO

    def test_negative_dio(self):
        calc = RiskCalculator()
        r = calc.inventory_imbalance(-1.0)
        assert r.level == RiskLevel.CRITICAL


class TestQualityIncidents:
    def test_low(self):
        calc = RiskCalculator()
        r = calc.quality_incidents(2.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.quality_incidents(8.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.quality_incidents(15.0)
        assert r.level == RiskLevel.CRITICAL


class TestMarketShareLoss:
    def test_growing(self):
        calc = RiskCalculator()
        r = calc.market_share_loss(5.0)
        assert r.level == RiskLevel.INFO

    def test_slight_loss(self):
        calc = RiskCalculator()
        r = calc.market_share_loss(-10.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.market_share_loss(-20.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.market_share_loss(-35.0)
        assert r.level == RiskLevel.CRITICAL

    def test_exactly_15_is_warning(self):
        calc = RiskCalculator()
        r = calc.market_share_loss(-15.0)
        assert r.level == RiskLevel.WARNING

    def test_exactly_30_is_critical(self):
        calc = RiskCalculator()
        r = calc.market_share_loss(-30.0)
        assert r.level == RiskLevel.CRITICAL


class TestPriceWarMargin:
    def test_healthy(self):
        calc = RiskCalculator()
        r = calc.price_war_margin(95.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.price_war_margin(85.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.price_war_margin(70.0)
        assert r.level == RiskLevel.CRITICAL


class TestRegulatoryShift:
    def test_low(self):
        calc = RiskCalculator()
        r = calc.regulatory_shift(1.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.regulatory_shift(5.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.regulatory_shift(10.0)
        assert r.level == RiskLevel.CRITICAL


class TestDemandCliff:
    def test_on_track(self):
        calc = RiskCalculator()
        r = calc.demand_cliff(0.0)
        assert r.level == RiskLevel.INFO

    def test_slight_miss(self):
        calc = RiskCalculator()
        r = calc.demand_cliff(-10.0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.demand_cliff(-30.0)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.demand_cliff(-45.0)
        assert r.level == RiskLevel.CRITICAL

    def test_exactly_25_is_warning(self):
        calc = RiskCalculator()
        r = calc.demand_cliff(-25.0)
        assert r.level == RiskLevel.WARNING

    def test_exactly_40_is_critical(self):
        calc = RiskCalculator()
        r = calc.demand_cliff(-40.0)
        assert r.level == RiskLevel.CRITICAL


class TestCompetitiveEntry:
    def test_no_entry(self):
        calc = RiskCalculator()
        r = calc.competitive_entry(3.0, losing_share_to_them=False)
        assert r.level == RiskLevel.INFO

    def test_warning_detected(self):
        calc = RiskCalculator()
        r = calc.competitive_entry(10.0, losing_share_to_them=False)
        assert r.level == RiskLevel.WARNING

    def test_critical_losing_share(self):
        calc = RiskCalculator()
        r = calc.competitive_entry(10.0, losing_share_to_them=True)
        assert r.level == RiskLevel.CRITICAL

    def test_exactly_5_is_info(self):
        calc = RiskCalculator()
        r = calc.competitive_entry(5.0, losing_share_to_them=True)
        assert r.level == RiskLevel.INFO


class TestSimulationDrift:
    def test_no_drift(self):
        calc = RiskCalculator()
        r = calc.simulation_drift(False)
        assert r.level == RiskLevel.INFO

    def test_drift_critical(self):
        calc = RiskCalculator()
        r = calc.simulation_drift(True)
        assert r.level == RiskLevel.CRITICAL
        assert "divergence" in r.message.lower()


class TestAgentAnomaly:
    def test_none(self):
        calc = RiskCalculator()
        r = calc.agent_anomaly(0)
        assert r.level == RiskLevel.INFO

    def test_warning_one(self):
        calc = RiskCalculator()
        r = calc.agent_anomaly(1)
        assert r.level == RiskLevel.WARNING

    def test_critical_three(self):
        calc = RiskCalculator()
        r = calc.agent_anomaly(3)
        assert r.level == RiskLevel.CRITICAL

    def test_critical_many(self):
        calc = RiskCalculator()
        r = calc.agent_anomaly(10)
        assert r.level == RiskLevel.CRITICAL


class TestDataCorruption:
    def test_clean(self):
        calc = RiskCalculator()
        r = calc.data_corruption(0)
        assert r.level == RiskLevel.INFO

    def test_warning_one(self):
        calc = RiskCalculator()
        r = calc.data_corruption(1)
        assert r.level == RiskLevel.WARNING

    def test_critical_two(self):
        calc = RiskCalculator()
        r = calc.data_corruption(2)
        assert r.level == RiskLevel.CRITICAL

    def test_critical_many(self):
        calc = RiskCalculator()
        r = calc.data_corruption(5)
        assert r.level == RiskLevel.CRITICAL


class TestTickTimeout:
    def test_normal(self):
        calc = RiskCalculator()
        r = calc.tick_timeout(1.0, consecutive=1)
        assert r.level == RiskLevel.INFO

    def test_warning_above_2x(self):
        calc = RiskCalculator()
        r = calc.tick_timeout(3.0, consecutive=1)
        assert r.level == RiskLevel.WARNING

    def test_critical_above_5x_consecutive(self):
        calc = RiskCalculator()
        r = calc.tick_timeout(6.0, consecutive=3)
        assert r.level == RiskLevel.CRITICAL

    def test_high_ratio_but_not_consecutive(self):
        calc = RiskCalculator()
        r = calc.tick_timeout(6.0, consecutive=1)
        assert r.level == RiskLevel.WARNING  # >2x → warning at minimum


class TestMemoryLeak:
    def test_stable(self):
        calc = RiskCalculator()
        r = calc.memory_leak(2.0, consecutive=1)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.memory_leak(12.0, consecutive=5)
        assert r.level == RiskLevel.WARNING

    def test_not_consecutive_enough(self):
        calc = RiskCalculator()
        r = calc.memory_leak(12.0, consecutive=3)
        assert r.level == RiskLevel.INFO

    def test_critical_single_tick(self):
        calc = RiskCalculator()
        r = calc.memory_leak(30.0, consecutive=1)
        assert r.level == RiskLevel.CRITICAL


class TestStateInconsistency:
    def test_clean(self):
        calc = RiskCalculator()
        r = calc.state_inconsistency(0, 0)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.state_inconsistency(1, 1)
        assert r.level == RiskLevel.WARNING

    def test_critical_consecutive(self):
        calc = RiskCalculator()
        r = calc.state_inconsistency(2, 2)
        assert r.level == RiskLevel.CRITICAL


class TestAgentLoopDetection:
    def test_normal(self):
        calc = RiskCalculator()
        r = calc.agent_loop_detection(3)
        assert r.level == RiskLevel.INFO

    def test_warning(self):
        calc = RiskCalculator()
        r = calc.agent_loop_detection(8)
        assert r.level == RiskLevel.WARNING

    def test_critical(self):
        calc = RiskCalculator()
        r = calc.agent_loop_detection(12)
        assert r.level == RiskLevel.CRITICAL


class TestEvaluateAll:
    """Integration-style test for the bulk evaluation method."""

    def test_empty_state(self):
        calc = RiskCalculator()
        results = calc.evaluate_all({})
        assert results == []

    def test_partial_state(self):
        calc = RiskCalculator()
        results = calc.evaluate_all({"cash_runway_months": 2.0})
        assert len(results) == 1
        assert results[0].risk_id == "cash_runway"
        assert results[0].level == RiskLevel.CRITICAL

    def test_full_financial_state(self):
        calc = RiskCalculator()
        state = {
            "cash_runway_months": 12.0,
            "burn_rate_mom_pct": 5.0,
            "burn_rate_trailing_3m_avg": 5.0,
            "revenue_concentration_pct": 20.0,
            "debt_service_ratio_pct": 25.0,
            "current_gross_margin": 60.0,
            "trailing_3m_gross_margin": 62.0,
            "current_ratio": 2.0,
        }
        results = calc.evaluate_all(state)
        assert len(results) == 6  # 6 financial metrics
        for r in results:
            assert r.category == RiskCategory.FINANCIAL

    def test_all_system_risks(self):
        calc = RiskCalculator()
        state = {
            "sim_drift_detected": False,
            "agent_anomaly_count": 0,
            "data_corruption_count": 0,
            "tick_timeout_ratio": 1.0,
            "memory_rss_growth_pct": 2.0,
            "memory_leak_consecutive": 1,
            "state_inconsistency_breaches": 0,
            "state_inconsistency_consecutive": 0,
            "agent_loop_repeats": 2,
        }
        results = calc.evaluate_all(state)
        assert len(results) == 7  # 7 system metrics
        for r in results:
            assert r.category == RiskCategory.SYSTEM
            assert r.level == RiskLevel.INFO


# ======================================================================
# SafeModeChecker
# ======================================================================


class TestSafeModeChecker:
    """Test all automatic safe-mode triggers (SM-01 through SM-07)."""

    def make_result(
        self, risk_id: str, category: RiskCategory, level: RiskLevel = RiskLevel.CRITICAL
    ) -> RiskResult:
        return RiskResult(
            risk_id=risk_id,
            category=category,
            label=risk_id.replace("_", " ").title(),
            metric_value=1.0,
            warning_threshold=None,
            critical_threshold=None,
            level=level,
        )

    def test_sm01_critical_financial(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("cash_runway", RiskCategory.FINANCIAL, RiskLevel.CRITICAL),
        ]
        triggers = checker.check(results)
        assert any(t.trigger_id == SafeModeTriggerID.SM01_CRITICAL_FINANCIAL for t in triggers)

    def test_sm02_multi_critical(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("cash_runway", RiskCategory.FINANCIAL, RiskLevel.CRITICAL),
            self.make_result("attrition_spike", RiskCategory.OPERATIONAL, RiskLevel.CRITICAL),
        ]
        triggers = checker.check(results)
        assert any(t.trigger_id == SafeModeTriggerID.SM02_MULTI_CRITICAL for t in triggers)

    def test_sm03_data_corruption(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("data_corruption", RiskCategory.SYSTEM, RiskLevel.CRITICAL),
        ]
        triggers = checker.check(results)
        assert any(t.trigger_id == SafeModeTriggerID.SM03_DATA_INTEGRITY for t in triggers)

    def test_sm04_agent_loop(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("agent_loop_detection", RiskCategory.SYSTEM, RiskLevel.CRITICAL),
        ]
        triggers = checker.check(results)
        assert any(t.trigger_id == SafeModeTriggerID.SM04_AGENT_LOOP for t in triggers)

    def test_sm05_sim_drift(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("simulation_drift", RiskCategory.SYSTEM, RiskLevel.CRITICAL),
        ]
        triggers = checker.check(results)
        assert any(t.trigger_id == SafeModeTriggerID.SM05_SIM_DRIFT for t in triggers)

    def test_sm06_tick_timeout(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("tick_timeout", RiskCategory.SYSTEM, RiskLevel.CRITICAL),
        ]
        triggers = checker.check(results)
        assert any(t.trigger_id == SafeModeTriggerID.SM06_TICK_TIMEOUT for t in triggers)

    def test_sm07_memory_leak(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("memory_leak", RiskCategory.SYSTEM, RiskLevel.CRITICAL),
        ]
        triggers = checker.check(results)
        assert any(t.trigger_id == SafeModeTriggerID.SM07_MEMORY_LEAK for t in triggers)

    def test_no_triggers_with_info(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("cash_runway", RiskCategory.FINANCIAL, RiskLevel.INFO),
            self.make_result("attrition_spike", RiskCategory.OPERATIONAL, RiskLevel.INFO),
        ]
        triggers = checker.check(results)
        assert triggers == []

    def test_warning_not_enough_for_sm01(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("cash_runway", RiskCategory.FINANCIAL, RiskLevel.WARNING),
        ]
        triggers = checker.check(results)
        assert len(triggers) == 0

    def test_should_enter_safe_mode(self):
        checker = SafeModeChecker()
        assert checker.should_enter_safe_mode(
            [SafeModeTrigger(SafeModeTriggerID.SM01_CRITICAL_FINANCIAL, "test")]
        )
        assert not checker.should_enter_safe_mode([])

    def test_multiple_triggers_simultaneously(self):
        checker = SafeModeChecker()
        results = [
            self.make_result("cash_runway", RiskCategory.FINANCIAL, RiskLevel.CRITICAL),
            self.make_result("simulation_drift", RiskCategory.SYSTEM, RiskLevel.CRITICAL),
        ]
        triggers = checker.check(results)
        ids = {t.trigger_id for t in triggers}
        assert SafeModeTriggerID.SM01_CRITICAL_FINANCIAL in ids
        assert SafeModeTriggerID.SM05_SIM_DRIFT in ids
        # SM-02 also fires because 2 critical
        assert SafeModeTriggerID.SM02_MULTI_CRITICAL in ids


# ======================================================================
# PositionSizer
# ======================================================================


class TestPositionSizer:
    def test_get_limits(self):
        sizer = PositionSizer()
        limits = sizer.get_limits(CompanyStage.EARLY)
        assert limits["max_single_pct"] == 15.0
        assert limits["max_sector_pct"] == 30.0
        assert limits["min_cash_pct"] == 15.0

    def test_early_valid(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=1_000_000,
            position_size=100_000,
            sector_total=200_000,
            total_exposure=600_000,
            stage=CompanyStage.EARLY,
        )
        assert r.valid
        assert r.position_pct == 10.0
        assert r.sector_total_pct == 20.0
        assert r.total_exposure_pct == 60.0
        assert r.message == "Position within limits"

    def test_early_exceeds_single(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=1_000_000,
            position_size=200_000,
            sector_total=300_000,
            total_exposure=800_000,
            stage=CompanyStage.EARLY,
        )
        assert not r.valid
        assert "exceeds limit" in r.message

    def test_early_exceeds_sector(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=1_000_000,
            position_size=100_000,
            sector_total=400_000,
            total_exposure=700_000,
            stage=CompanyStage.EARLY,
        )
        assert not r.valid
        assert any("sector" in f.lower() for f in r.flags)

    def test_cash_reserve_floor(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=1_000_000,
            position_size=100_000,
            sector_total=200_000,
            total_exposure=900_000,
            stage=CompanyStage.EARLY,
        )
        assert not r.valid
        assert any("cash" in f.lower() for f in r.flags)

    def test_growth_stage_limits(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=1_000_000,
            position_size=220_000,  # 22% → exceeds growth limit of 20%
            sector_total=300_000,
            total_exposure=700_000,
            stage=CompanyStage.GROWTH,
        )
        assert not r.valid

    def test_mature_stage_limits(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=1_000_000,
            position_size=260_000,  # 26% → exceeds mature limit of 25%
            sector_total=350_000,
            total_exposure=800_000,
            stage=CompanyStage.MATURE,
        )
        assert not r.valid

    def test_mature_stage_valid_at_limit(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=1_000_000,
            position_size=250_000,  # 25% → exactly at limit
            sector_total=400_000,  # 40% → exactly at limit
            total_exposure=850_000,
            stage=CompanyStage.MATURE,
        )
        assert r.valid

    def test_concentration_flag(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=1_000_000,
            position_size=160_000,  # 16% → exceeds 15% concentration flag
            sector_total=200_000,
            total_exposure=600_000,
            stage=CompanyStage.MATURE,
        )
        # Still valid against mature limits (25% max single), but flagged
        assert r.valid
        assert any("concentration" in f.lower() for f in r.flags)

    def test_zero_capital(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=0,
            position_size=0,
            sector_total=0,
            total_exposure=0,
            stage=CompanyStage.EARLY,
        )
        assert not r.valid
        assert "capital <= 0" in r.message

    def test_negative_capital(self):
        sizer = PositionSizer()
        r = sizer.validate(
            capital=-1000,
            position_size=0,
            sector_total=0,
            total_exposure=0,
            stage=CompanyStage.EARLY,
        )
        assert not r.valid

    def test_stage_specific_limits_all_stages(self):
        sizer = PositionSizer()
        # Same absolute position across stages — should pass for mature,
        # fail for early
        r_early = sizer.validate(
            capital=1_000_000,
            position_size=180_000,
            sector_total=250_000,
            total_exposure=750_000,
            stage=CompanyStage.EARLY,
        )
        r_growth = sizer.validate(
            capital=1_000_000,
            position_size=180_000,
            sector_total=250_000,
            total_exposure=750_000,
            stage=CompanyStage.GROWTH,
        )
        r_mature = sizer.validate(
            capital=1_000_000,
            position_size=180_000,
            sector_total=250_000,
            total_exposure=750_000,
            stage=CompanyStage.MATURE,
        )
        assert not r_early.valid  # 18% > 15%
        assert r_growth.valid  # 18% < 20%
        assert r_mature.valid  # 18% < 25%


# ======================================================================
# DrawdownMonitor
# ======================================================================


class TestDrawdownMonitor:
    def test_portfolio_first_call_no_drawdown(self):
        monitor = DrawdownMonitor()
        level, dd = monitor.check_portfolio_drawdown(1_000_000)
        assert level == RiskLevel.INFO
        assert dd == 0.0

    def test_portfolio_drawdown_healthy(self):
        monitor = DrawdownMonitor()
        monitor.check_portfolio_drawdown(1_000_000)
        level, dd = monitor.check_portfolio_drawdown(950_000)
        assert level == RiskLevel.INFO
        assert dd == pytest.approx(-5.0)

    def test_portfolio_drawdown_warning(self):
        monitor = DrawdownMonitor()
        monitor.check_portfolio_drawdown(1_000_000)
        level, dd = monitor.check_portfolio_drawdown(820_000)
        assert level == RiskLevel.WARNING
        assert dd == pytest.approx(-18.0)

    def test_portfolio_drawdown_critical(self):
        monitor = DrawdownMonitor()
        monitor.check_portfolio_drawdown(1_000_000)
        level, dd = monitor.check_portfolio_drawdown(700_000)
        assert level == RiskLevel.CRITICAL
        assert dd == pytest.approx(-30.0)

    def test_portfolio_updates_peak_on_higher_value(self):
        monitor = DrawdownMonitor()
        monitor.check_portfolio_drawdown(1_000_000)
        level, dd = monitor.check_portfolio_drawdown(1_200_000)
        assert level == RiskLevel.INFO
        assert dd == 0.0  # new peak
        # Now drawdown from new peak
        level2, dd2 = monitor.check_portfolio_drawdown(1_100_000)
        assert level2 == RiskLevel.INFO
        assert dd2 == pytest.approx(-8.33, rel=0.01)

    def test_revenue_drawdown(self):
        monitor = DrawdownMonitor()
        monitor.check_revenue_drawdown(500_000)
        level, dd = monitor.check_revenue_drawdown(350_000)
        assert level == RiskLevel.WARNING  # -30% > -35% threshold

    def test_revenue_drawdown_critical(self):
        monitor = DrawdownMonitor()
        monitor.check_revenue_drawdown(500_000)
        level, dd = monitor.check_revenue_drawdown(300_000)
        assert level == RiskLevel.CRITICAL  # -40%

    def test_cash_drawdown(self):
        monitor = DrawdownMonitor()
        level, dd = monitor.check_cash_drawdown(current_cash=70_000, previous_cash=100_000)
        assert level == RiskLevel.WARNING  # -30%

    def test_cash_drawdown_critical(self):
        monitor = DrawdownMonitor()
        level, dd = monitor.check_cash_drawdown(current_cash=40_000, previous_cash=100_000)
        assert level == RiskLevel.CRITICAL  # -60%

    def test_cash_no_previous_change(self):
        monitor = DrawdownMonitor()
        level, dd = monitor.check_cash_drawdown(current_cash=100_000, previous_cash=100_000)
        assert level == RiskLevel.INFO
        assert dd == 0.0

    def test_cash_zero_previous(self):
        monitor = DrawdownMonitor()
        level, dd = monitor.check_cash_drawdown(current_cash=100_000, previous_cash=0)
        assert level == RiskLevel.INFO

    def test_evaluate_aggregate_all_healthy(self):
        monitor = DrawdownMonitor()
        monitor.peak_portfolio = 1_000_000
        monitor.peak_revenue_4q = 500_000
        result = monitor.evaluate(
            portfolio_value=950_000,
            revenue_4q_avg=480_000,
            current_cash=200_000,
            previous_cash=210_000,
        )
        assert result.overall_level == RiskLevel.INFO
        assert not result.low_risk_mode_required

    def test_evaluate_aggregate_critical(self):
        monitor = DrawdownMonitor()
        monitor.peak_portfolio = 1_000_000
        monitor.peak_revenue_4q = 500_000
        result = monitor.evaluate(
            portfolio_value=700_000,
            revenue_4q_avg=300_000,
            current_cash=50_000,
            previous_cash=200_000,
        )
        assert result.overall_level == RiskLevel.CRITICAL
        assert result.low_risk_mode_required

    def test_low_risk_mode_tracking(self):
        monitor = DrawdownMonitor()
        assert monitor.low_risk_ticks_elapsed == 0
        monitor.tick_in_low_risk_mode()
        monitor.tick_in_low_risk_mode()
        monitor.tick_in_low_risk_mode()
        monitor.tick_in_low_risk_mode()
        assert monitor.low_risk_mode_complete()
        assert monitor.low_risk_ticks_elapsed == 4

    def test_low_risk_mode_incomplete(self):
        monitor = DrawdownMonitor()
        monitor.tick_in_low_risk_mode()
        monitor.tick_in_low_risk_mode()
        assert not monitor.low_risk_mode_complete()

    def test_reset_low_risk_ticks(self):
        monitor = DrawdownMonitor()
        monitor.tick_in_low_risk_mode()
        monitor.tick_in_low_risk_mode()
        monitor.reset_low_risk_ticks()
        assert monitor.low_risk_ticks_elapsed == 0

    def test_low_risk_mode_constraints(self):
        constraints = DrawdownMonitor.low_risk_mode_constraints()
        assert "new_hires" in constraints
        assert "capex" in constraints
        assert "debt" in constraints
        assert "mergers_acquisitions" in constraints

    def test_peak_trackers_from_properties(self):
        monitor = DrawdownMonitor()
        monitor.peak_portfolio = 1_000_000
        monitor.peak_portfolio = 800_000  # should not decrease
        assert monitor.peak_portfolio == 1_000_000
        monitor.peak_portfolio = 1_500_000  # new high
        assert monitor.peak_portfolio == 1_500_000


# ======================================================================
# RiskEngine (orchestrator)
# ======================================================================


class TestRiskEngine:
    def test_full_assessment_healthy(self):
        engine = RiskEngine()
        state = {
            "company": "TechCo",
            "tick": 42,
            "cash_runway_months": 12.0,
            "current_ratio": 2.0,
            "attrition_rate_pct": 10.0,
            "defect_rate_pct": 2.0,
        }
        report = engine.full_assessment(state)
        assert isinstance(report, RiskReport)
        assert report.company == "TechCo"
        assert report.tick == 42
        assert report.highest_level == RiskLevel.INFO
        assert report.alert_level == AlertLevel.L1_INFO
        assert len(report.results) == 4
        assert report.safe_mode_triggers == []

    def test_full_assessment_with_critical(self):
        engine = RiskEngine()
        state = {
            "company": "BurnCo",
            "tick": 10,
            "cash_runway_months": 1.5,  # critical
            "current_ratio": 0.8,  # critical
        }
        report = engine.full_assessment(state)
        assert report.highest_level == RiskLevel.CRITICAL
        assert len(report.safe_mode_triggers) > 0
        # SM-01 and potentially SM-02
        trigger_ids = {t.trigger_id for t in report.safe_mode_triggers}
        assert SafeModeTriggerID.SM01_CRITICAL_FINANCIAL in trigger_ids

    def test_full_assessment_with_system_emergency(self):
        """Sim drift is Critical → triggers safe mode → alert L5."""
        engine = RiskEngine()
        state = {
            "company": "DriftCo",
            "tick": 5,
            "sim_drift_detected": True,
            "cash_runway_months": 4.0,
        }
        report = engine.full_assessment(state)
        assert report.highest_level == RiskLevel.CRITICAL
        assert report.alert_level == AlertLevel.L5_SYSTEM_EMERGENCY
        assert any(
            t.trigger_id == SafeModeTriggerID.SM05_SIM_DRIFT for t in report.safe_mode_triggers
        )

    def test_full_assessment_with_position_sizing(self):
        engine = RiskEngine()
        state = {
            "company": "PosCo",
            "tick": 20,
            "capital": 1_000_000,
            "position_size": 100_000,
            "sector_total": 200_000,
            "total_exposure": 600_000,
            "company_stage": "growth",
            "cash_runway_months": 12.0,
        }
        report = engine.full_assessment(state)
        assert report.position_sizing is not None
        assert report.position_sizing.valid

    def test_full_assessment_with_drawdown(self):
        engine = RiskEngine()
        state = {
            "company": "DrawCo",
            "tick": 30,
            "portfolio_value": 800_000,
            "revenue_4q_avg": 400_000,
            "cash_balance": 100_000,
            "previous_cash_balance": 120_000,
            "cash_runway_months": 6.0,
        }
        report = engine.full_assessment(state)
        assert report.drawdown is not None
        assert report.drawdown.portfolio_drawdown_pct == 0.0  # first call — peak set

    def test_lifecycle_safe_mode(self):
        engine = RiskEngine()
        assert not engine.in_safe_mode
        engine.enter_safe_mode({"company": "X", "tick": 1})
        assert engine.in_safe_mode
        engine.resume_from_safe_mode()
        assert not engine.in_safe_mode

    def test_lifecycle_low_risk_mode(self):
        engine = RiskEngine()
        assert not engine.low_risk_mode
        # Trigger low-risk mode via drawdown
        state = {
            "company": "RecoveryCo",
            "tick": 5,
            "portfolio_value": 500_000,
            "revenue_4q_avg": 300_000,
            "cash_balance": 30_000,
            "previous_cash_balance": 100_000,
            "cash_runway_months": 8.0,
        }
        engine.drawdown_monitor.peak_portfolio = 1_000_000  # prime peak
        engine.drawdown_monitor.peak_revenue_4q = 500_000
        _ = engine.full_assessment(state)
        assert engine.low_risk_mode
        engine.exit_low_risk_mode()
        assert not engine.low_risk_mode

    def test_event_logging(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "risk-events.jsonl")
            engine = RiskEngine(event_log_path=log_path)
            event = RiskEvent.create(
                tick=42,
                company="TestCo",
                risk="cash_runway",
                level="Critical",
                metric=2.0,
                threshold=3.0,
                trigger="SM-01",
                safe_mode=True,
            )
            engine.log_event(event)
            # Read it back
            events = engine.read_event_log()
            assert len(events) == 1
            assert events[0].id == event.id
            assert events[0].risk == "cash_runway"

    def test_event_log_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "risk-events.jsonl")
            engine = RiskEngine(event_log_path=log_path)
            for i in range(10):
                event = RiskEvent.create(
                    tick=i,
                    company="C",
                    risk=f"risk_{i}",
                    level="Watch",
                    metric=float(i),
                    threshold=5.0,
                )
                engine.log_event(event)
            events = engine.read_event_log(limit=3)
            assert len(events) == 3
            assert events[0].tick == 7  # most recent 3: ticks 7, 8, 9

    def test_no_event_log_yet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "nonexistent.jsonl")
            engine = RiskEngine(event_log_path=log_path)
            events = engine.read_event_log()
            assert events == []

    def test_risk_event_create(self):
        event = RiskEvent.create(
            tick=100,
            company="SimCo",
            risk="liquidity_crunch",
            level="Warning",
            metric=1.2,
            threshold=1.5,
        )
        assert event.id.startswith("RISK-")
        assert event.company == "SimCo"
        assert event.tick == 100
        assert not event.safe_mode
        assert event.trigger is None

    def test_risk_level_helpers(self):
        assert RiskLevel.WARNING.is_warning_or_above()
        assert RiskLevel.CRITICAL.is_warning_or_above()
        assert RiskLevel.SYSTEM_EMERGENCY.is_warning_or_above()
        assert not RiskLevel.INFO.is_warning_or_above()
        assert not RiskLevel.WATCH.is_warning_or_above()

        assert RiskLevel.CRITICAL.is_critical_or_above()
        assert RiskLevel.SYSTEM_EMERGENCY.is_critical_or_above()
        assert not RiskLevel.WARNING.is_critical_or_above()

    def test_risk_result_to_dict(self):
        r = RiskResult(
            risk_id="test",
            category=RiskCategory.SYSTEM,
            label="Test",
            metric_value=1.0,
            warning_threshold=5.0,
            critical_threshold=10.0,
            level=RiskLevel.INFO,
            message="ok",
        )
        d = r.to_dict()
        assert d["risk_id"] == "test"
        assert d["level"] == "Info"

    def test_engine_resume_from_safe_mode_no_state(self):
        engine = RiskEngine()
        engine.enter_safe_mode({"company": "C", "tick": 1})
        engine.resume_from_safe_mode()
        assert not engine.in_safe_mode

    def test_healthy_state_produces_summary(self):
        engine = RiskEngine()
        report = engine.full_assessment(
            {
                "company": "Test",
                "tick": 1,
                "cash_runway_months": 12.0,
            }
        )
        assert "Highest risk: Info" in report.summary
        assert report.summary != ""

    def test_critical_state_in_summary(self):
        engine = RiskEngine()
        report = engine.full_assessment(
            {
                "company": "Test",
                "tick": 1,
                "cash_runway_months": 2.0,
            }
        )
        assert "Critical" in report.summary

    def test_on_tick_consumer_healthy(self):
        """Test on_tick() consumer entry point with healthy state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "risk-events.jsonl")
            engine = RiskEngine(event_log_path=log_path)
            state = {
                "company": "ConsumerCo",
                "tick": 42,
                "cash_runway_months": 12.0,
                "current_ratio": 2.0,
            }
            report = engine.on_tick(state)
            assert report.company == "ConsumerCo"
            assert report.tick == 42
            assert report.highest_level == RiskLevel.INFO
            # No events logged for INFO level
            events = engine.read_event_log()
            assert len(events) == 0

    def test_on_tick_consumer_logs_warnings(self):
        """Test on_tick() logs events for WARNING+ risks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "risk-events.jsonl")
            engine = RiskEngine(event_log_path=log_path)
            state = {
                "company": "RiskyCo",
                "tick": 10,
                "cash_runway_months": 4.5,  # WARNING
                "current_ratio": 1.2,  # WARNING
            }
            report = engine.on_tick(state)
            assert report.highest_level == RiskLevel.WARNING
            # Should log 2 events (one per WARNING risk)
            events = engine.read_event_log()
            assert len(events) == 2
            assert all(e.level == "Warning" for e in events)
            assert {e.risk for e in events} == {"cash_runway", "liquidity_crunch"}

    def test_on_tick_consumer_logs_criticals(self):
        """Test on_tick() logs events for CRITICAL risks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "risk-events.jsonl")
            engine = RiskEngine(event_log_path=log_path)
            state = {
                "company": "CriticalCo",
                "tick": 5,
                "cash_runway_months": 1.5,  # CRITICAL
            }
            report = engine.on_tick(state)
            assert report.highest_level == RiskLevel.CRITICAL
            events = engine.read_event_log()
            assert len(events) == 1
            assert events[0].level == "Critical"
            assert events[0].risk == "cash_runway"
