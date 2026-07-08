"""
AI Quant Office OS — Market Data Models

Pydantic v2 schemas for all market data types consumed by the
Data Division's ingestion pipeline. Used as the single source of
truth across ingestion → feature store → analysis layers.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────


class DataSource(str, Enum):
    """Which provider a data point was sourced from."""

    TWELVEDATA = "twelvedata"
    BINANCE = "binance"
    FRED = "fred"
    ALPHA_VANTAGE = "alpha_vantage"
    GOLDAPI = "goldapi"
    POLYGON = "polygon"
    YAHOO = "yahoo"
    MANUAL = "manual"


class MarketDataType(str, Enum):
    """High-level category of a market data record."""

    SPOT = "spot"  # spot price / current quote
    OHLCV = "ohlcv"  # candlestick
    ORDERBOOK_L1 = "orderbook_l1"  # top bid/ask
    ORDERBOOK_L2 = "orderbook_l2"  # full depth
    TICK = "tick"  # individual trade
    ECONOMIC = "economic"  # macro indicator (FRED etc.)
    FUNDAMENTAL = "fundamental"  # financial report data
    SENTIMENT = "sentiment"  # derived from news / social
    DERIVED = "derived"  # computed in-house (e.g. indicators)


class TimeInterval(str, Enum):
    """Aggregation candle interval."""

    M1 = "1min"
    M5 = "5min"
    M15 = "15min"
    M30 = "30min"
    H1 = "1h"
    H4 = "4h"
    D1 = "1day"
    W1 = "1week"
    MN1 = "1month"


# ── Core Data Models ───────────────────────────────────────────


class OHLCV(BaseModel):
    """Single candlestick — open, high, low, close, volume."""

    timestamp: datetime = Field(..., description="UTC open time of the candle")
    open: Decimal = Field(..., max_digits=20, decimal_places=8)
    high: Decimal = Field(..., max_digits=20, decimal_places=8)
    low: Decimal = Field(..., max_digits=20, decimal_places=8)
    close: Decimal = Field(..., max_digits=20, decimal_places=8)
    volume: Decimal = Field(..., max_digits=28, decimal_places=8)
    interval: TimeInterval = Field(..., description="Candle aggregation period")
    source: DataSource = Field(..., description="Provider of this candle")
    instrument: str = Field(
        ..., description="Symbol, e.g. 'BTC/USDT', 'XAU/USD', 'AAPL'"
    )

    model_config = {"frozen": True}

    @property
    def spread_pct(self) -> Decimal:
        """High−low spread as a percentage of close."""
        if self.close == Decimal("0"):
            return Decimal("0")
        return (self.high - self.low) / self.close * Decimal("100")


class Quote(BaseModel):
    """Current market quote — bid, ask, mid, and metadata."""

    timestamp: datetime = Field(..., description="UTC quote time")
    bid: Decimal = Field(..., max_digits=20, decimal_places=8)
    ask: Decimal = Field(..., max_digits=20, decimal_places=8)
    mid: Decimal = Field(..., max_digits=20, decimal_places=8)
    source: DataSource
    instrument: str

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    @property
    def spread_bps(self) -> Decimal:
        """Spread in basis points of mid."""
        if self.mid == Decimal("0"):
            return Decimal("0")
        return (self.spread / self.mid) * Decimal("10000")


class EconomicIndicator(BaseModel):
    """A single observation from a macro-economic time series (FRED etc.)."""

    series_id: str = Field(..., description="FRED series ID, e.g. 'GDP', 'UNRATE'")
    name: str = Field(default="", description="Human-readable name")
    date: datetime = Field(..., description="Observation date (midnight UTC)")
    value: Decimal = Field(..., max_digits=20, decimal_places=4)
    unit: str = Field(default="", description="e.g. 'Percent', 'Billions of $'")
    frequency: str = Field(default="", description="e.g. 'Monthly', 'Quarterly'")
    source: DataSource = Field(default=DataSource.FRED)

    model_config = {"frozen": True}


class TimeSeries(BaseModel):
    """Collection of data points for one instrument + interval."""

    instrument: str
    interval: TimeInterval | None = None
    data_type: MarketDataType
    source: DataSource
    points: list[OHLCV | Quote | EconomicIndicator | dict] = Field(
        default_factory=list
    )
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    def latest(self) -> OHLCV | Quote | EconomicIndicator | dict | None:
        return self.points[-1] if self.points else None

    def __len__(self) -> int:
        return len(self.points)
