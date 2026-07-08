"""
AI Quant Office OS — Data Ingestion Service

Multi-source market data ingestion for the Data Division.
Pulls from FRED (macro), TwelveData (equities / forex / crypto),
and Binance (crypto depth) with a unified interface.

Usage::

    config = DataIngestionConfig(
        fred_api_key="...",
        twelvedata_api_key="...",
    )
    manager = DataIngestionManager(config)

    # Pull daily BTC/USDT from Binance
    btc = await manager.fetch_ohlcv("BTC/USDT", "1day", source="binance")

    # Pull GDP from FRED
    gdp = await manager.fetch_economic("GDP")
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.models.market_data import (
    DataSource,
    EconomicIndicator,
    MarketDataType,
    OHLCV,
    Quote,
    TimeInterval,
    TimeSeries,
)

log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────


@dataclass
class DataIngestionConfig:
    """Credentials and tuning knobs for every supported source."""

    # API keys
    fred_api_key: str = ""
    twelvedata_api_key: str = ""

    # Rate‑limiting (calls per second — conservative defaults)
    fred_rate: float = 5.0
    twelvedata_rate: float = 4.0
    binance_rate: float = 10.0

    # HTTP
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_backoff_base: float = 1.5

    # Binance
    binance_rest_url: str = "https://api.binance.com"

    # TwelveData
    twelvedata_rest_url: str = "https://api.twelvedata.com"

    # FRED
    fred_rest_url: str = "https://api.stlouisfed.org/fred"


# ── Rate Limiter ───────────────────────────────────────────────


class _RateLimiter:
    """Simple token‑bucket rate limiter for a single client."""

    def __init__(self, calls_per_second: float) -> None:
        self._min_interval = 1.0 / max(calls_per_second, 0.1)
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


# ── Base API Client ────────────────────────────────────────────


class _BaseClient(ABC):
    """Shared retry logic, session management, and error handling."""

    def __init__(self, config: DataIngestionConfig, rate: float) -> None:
        self._cfg = config
        self._limiter = _RateLimiter(rate)
        self._client: httpx.AsyncClient | None = None

    # ── Session ────────────────────────────────────────────

    async def _session(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._cfg.timeout_seconds),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Retry Logic ────────────────────────────────────────

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """HTTP request with rate‑limiting, retry, and structured error reporting."""
        last_exc: Exception | None = None

        for attempt in range(1, self._cfg.max_retries + 1):
            await self._limiter.acquire()
            try:
                client = await self._session()
                resp = await client.request(method, url, params=params, json=json_body)

                # ── Status‑based retry ──
                if resp.status_code in {429, 503, 520, 529} and attempt < self._cfg.max_retries:
                    retry_after = _parse_retry_after(resp.headers) or (
                        self._cfg.retry_backoff_base**attempt
                    )
                    log.warning(
                        "HTTP %s on %s — retry %d/%d after %.1fs",
                        resp.status_code,
                        url,
                        attempt,
                        self._cfg.max_retries,
                        retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                resp.raise_for_status()
                body: dict = resp.json()
                _check_api_error(body, url)
                return body

            except httpx.TimeoutException as exc:
                last_exc = exc
                log.warning("Timeout on %s — retry %d/%d", url, attempt, self._cfg.max_retries)
                if attempt < self._cfg.max_retries:
                    await asyncio.sleep(self._cfg.retry_backoff_base**attempt)

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if attempt < self._cfg.max_retries and exc.response.status_code in {
                    429,
                    503,
                    520,
                    529,
                }:
                    retry_after = _parse_retry_after(exc.response.headers) or (
                        self._cfg.retry_backoff_base**attempt
                    )
                    await asyncio.sleep(retry_after)
                    continue
                raise

            except Exception as exc:
                last_exc = exc
                if attempt < self._cfg.max_retries:
                    await asyncio.sleep(self._cfg.retry_backoff_base**attempt)

        raise IOError(
            f"Request to {url} failed after {self._cfg.max_retries} attempts"
        ) from last_exc

    async def _request_json(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        return await self._request(method, url, **kwargs)

    # ── Lifecycle ──────────────────────────────────────────

    async def __aenter__(self) -> _BaseClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def _parse_retry_after(headers: httpx.Headers) -> float | None:
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _check_api_error(body: dict | list, url: str) -> None:
    """Some APIs embed errors in 200‑OK bodies — raise them."""
    if isinstance(body, list):
        return  # Binance klines etc. are bare arrays — no embedded error
    if body.get("status") == "error":
        msg = body.get("message") or body.get("error") or repr(body)
        raise IOError(f"API error from {url}: {msg}")
    if "error" in body and isinstance(body["error"], str) and body["error"]:
        raise IOError(f"API error from {url}: {body['error']}")


# ── FRED Client ────────────────────────────────────────────────

_SERIES_METADATA: dict[str, tuple[str, str, str]] = {
    "GDP": ("Gross Domestic Product", "Billions of $", "Quarterly"),
    "UNRATE": ("Unemployment Rate", "Percent", "Monthly"),
    "FEDFUNDS": ("Federal Funds Rate", "Percent", "Monthly"),
    "CPIAUCSL": ("Consumer Price Index", "Index 1982-84=100", "Monthly"),
    "PCE": ("Personal Consumption Expenditures", "Billions of $", "Monthly"),
    "DGS10": ("10‑Year Treasury Yield", "Percent", "Daily"),
    "DGS2": ("2‑Year Treasury Yield", "Percent", "Daily"),
    "SP500": ("S&P 500 Index", "Index", "Daily"),
    "T10YIE": ("10‑Year Breakeven Inflation Rate", "Percent", "Daily"),
    "M2SL": ("M2 Money Stock", "Billions of $", "Monthly"),
}


class FREDClient(_BaseClient):
    """Fetch macro‑economic time series from the St. Louis Fed API.

    Requires *fred_api_key* in config.
    """

    def __init__(self, config: DataIngestionConfig) -> None:
        super().__init__(config, rate=config.fred_rate)

    async def fetch_series(
        self,
        series_id: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100_000,
    ) -> list[EconomicIndicator]:
        """Retrieve observations for a FRED series.

        Parameters
        ----------
        series_id:
            FRED code such as ``"GDP"``, ``"UNRATE"``, ``"DGS10"``.
        start, end:
            Date range (inclusive).  Up to 100 k observations per call.

        Returns
        -------
        A chronologically ordered list of ``EconomicIndicator``.
        """
        params: dict[str, Any] = {
            "series_id": series_id,
            "api_key": self._cfg.fred_api_key,
            "file_type": "json",
            "sort_order": "asc",
            "limit": limit,
        }
        if start:
            params["observation_start"] = start.strftime("%Y-%m-%d")
        if end:
            params["observation_end"] = end.strftime("%Y-%m-%d")

        body = await self._request(
            "GET", f"{self._cfg.fred_rest_url}/series/observations", params=params
        )

        raw_obs = body.get("observations", [])
        meta = _SERIES_METADATA.get(series_id, ("", "", ""))

        results: list[EconomicIndicator] = []
        for obs in raw_obs:
            val_str = obs.get("value", "")
            if val_str in ("", "."):
                continue  # skip missing
            try:
                value = Decimal(val_str)
            except Exception:
                continue

            results.append(
                EconomicIndicator(
                    series_id=series_id,
                    name=meta[0] or series_id,
                    date=_parse_fred_date(obs["date"]),
                    value=value,
                    unit=meta[1],
                    frequency=meta[2],
                )
            )
        return results


def _parse_fred_date(raw: str) -> datetime:
    # FRED sends "YYYY-MM-DD"
    parts = raw.split("-")
    return datetime(int(parts[0]), int(parts[1]), int(parts[2]))


# ── TwelveData Client ──────────────────────────────────────────


_INTERVAL_MAP: dict[TimeInterval, str] = {
    TimeInterval.M1: "1min",
    TimeInterval.M5: "5min",
    TimeInterval.M15: "15min",
    TimeInterval.M30: "30min",
    TimeInterval.H1: "1h",
    TimeInterval.H4: "4h",
    TimeInterval.D1: "1day",
    TimeInterval.W1: "1week",
    TimeInterval.MN1: "1month",
}


class TwelveDataClient(_BaseClient):
    """Equity / forex / crypto quotes and OHLCV via Twelve Data.

    Requires *twelvedata_api_key* in config.
    """

    def __init__(self, config: DataIngestionConfig) -> None:
        super().__init__(config, rate=config.twelvedata_rate)

    # ── OHLCV ──────────────────────────────────────────────

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: TimeInterval | str,
        *,
        outputsize: int = 100,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[OHLCV]:
        """Historical time series.

        *interval* can be a ``TimeInterval`` enum or a raw string
        such as ``"1h"``, ``"1day"``.
        """
        ival = interval.value if isinstance(interval, TimeInterval) else interval
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": ival,
            "apikey": self._cfg.twelvedata_api_key,
            "outputsize": outputsize,
            "order": "ASC",
        }
        if start:
            params["start_date"] = start.strftime("%Y-%m-%d %H:%M:%S")
        if end:
            params["end_date"] = end.strftime("%Y-%m-%d %H:%M:%S")

        body = await self._request(
            "GET", f"{self._cfg.twelvedata_rest_url}/time_series", params=params
        )

        # Normalise: TwelveData returns a dict with key "values"
        raw = body.get("values", [])
        if not raw or not isinstance(raw, list):
            log.warning("TwelveData returned %r for symbol=%s", body.get("status"), symbol)
            return []

        return [
            OHLCV(
                timestamp=_parse_twelve_datetime(v["datetime"]),
                open=Decimal(str(v["open"])),
                high=Decimal(str(v["high"])),
                low=Decimal(str(v["low"])),
                close=Decimal(str(v["close"])),
                volume=Decimal(str(v.get("volume", 0))),
                interval=TimeInterval(ival) if isinstance(ival, str) else interval,
                source=DataSource.TWELVEDATA,
                instrument=symbol,
            )
            for v in raw
        ]

    # ── Quote ──────────────────────────────────────────────

    async def fetch_quote(self, symbol: str) -> Quote | None:
        """Latest real‑time quote for *symbol*."""
        params: dict[str, Any] = {
            "symbol": symbol,
            "apikey": self._cfg.twelvedata_api_key,
        }
        body = await self._request("GET", f"{self._cfg.twelvedata_rest_url}/quote", params=params)

        if body.get("status") == "error":
            return None

        try:
            bid = Decimal(str(body.get("bid", "0")))
            ask = Decimal(str(body.get("ask", "0")))
            mid = (bid + ask) / Decimal("2")
            return Quote(
                timestamp=_parse_twelve_datetime(body["datetime"]),
                bid=bid,
                ask=ask,
                mid=mid,
                source=DataSource.TWELVEDATA,
                instrument=symbol,
            )
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("Failed to parse quote for %s: %s", symbol, exc)
            return None


def _parse_twelve_datetime(raw: str) -> datetime:
    # TwelveData ISO format "2024-06-15 14:30:00" or with T
    raw = raw.replace("T", " ").strip()
    # Some endpoints return microseconds
    if "." in raw:
        raw = raw.split(".")[0]
    return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")


# ── Binance Client ─────────────────────────────────────────────


class BinanceClient(_BaseClient):
    """Crypto market data from Binance REST.

    Public endpoints — no API key required for reads.
    """

    def __init__(self, config: DataIngestionConfig) -> None:
        super().__init__(config, rate=config.binance_rate)

    # ── OHLCV (Klines) ─────────────────────────────────────

    async def fetch_klines(
        self,
        symbol: str,
        interval: TimeInterval | str,
        *,
        limit: int = 500,
        start: int | None = None,
        end: int | None = None,
    ) -> list[OHLCV]:
        """Kline/candlestick data from Binance.

        Parameters
        ----------
        symbol:
            Trading pair, e.g. ``"BTCUSDT"`` (no slash).
        interval:
            ``TimeInterval`` enum or raw string ``"1m"``, ``"5m"``,
            ``"1h"``, ``"1d"``, ``"1w"``, ``"1M"``.
        limit:
            Max candles to return (Binance cap: 1000).
        start, end:
            Milliseconds since epoch (UTC). If both omitted Binance
            returns the most recent candles.

        Returns
        -------
        Chronological list of ``OHLCV``.
        """
        params: dict[str, Any] = {
            "symbol": _binance_symbol(symbol),
            "interval": _binance_interval(interval),
            "limit": min(limit, 1000),
        }
        if start is not None:
            params["startTime"] = start
        if end is not None:
            params["endTime"] = end

        raw: list[list[Any]] = await self._request(
            "GET", f"{self._cfg.binance_rest_url}/api/v3/klines", params=params
        )

        return [
            OHLCV(
                timestamp=datetime.utcfromtimestamp(k[0] / 1000),
                open=Decimal(str(k[1])),
                high=Decimal(str(k[2])),
                low=Decimal(str(k[3])),
                close=Decimal(str(k[4])),
                volume=Decimal(str(k[5])),
                interval=TimeInterval(_reverse_binance_interval(interval))
                if isinstance(interval, str)
                else interval,
                source=DataSource.BINANCE,
                instrument=_human_symbol(symbol),
            )
            for k in raw
        ]

    # ── Order Book (L1) ────────────────────────────────────

    async def fetch_orderbook(self, symbol: str, limit: int = 5) -> list[dict] | None:
        """Top *limit* bid/ask levels for *symbol*."""
        params = {"symbol": _binance_symbol(symbol), "limit": min(limit, 100)}
        body = await self._request(
            "GET", f"{self._cfg.binance_rest_url}/api/v3/depth", params=params
        )

        if not isinstance(body, dict) or "bids" not in body:
            return None

        ts = datetime.utcnow()
        result: list[dict] = []
        for side, key in (("bid", "bids"), ("ask", "asks")):
            for price, qty in body.get(key, []):
                result.append(
                    {
                        "side": side,
                        "price": Decimal(str(price)),
                        "qty": Decimal(str(qty)),
                        "timestamp": ts,
                    }
                )
        return result

    # ── 24hr Ticker ────────────────────────────────────────

    async def fetch_ticker_24hr(self, symbol: str) -> dict | None:
        """24‑hour rolling ticker stats (price change, volume, etc.)."""
        params = {"symbol": _binance_symbol(symbol)}
        body = await self._request(
            "GET", f"{self._cfg.binance_rest_url}/api/v3/ticker/24hr", params=params
        )
        return body if isinstance(body, dict) else None


# ── Binance Symbol Helpers ───────────────────────────────────


def _binance_symbol(symbol: str) -> str:
    # Normalise "BTC/USDT" → "BTCUSDT"
    return symbol.replace("/", "").replace("-", "").upper()


def _human_symbol(symbol: str) -> str:
    # Inverse: "BTCUSDT" → "BTC/USDT"
    s = symbol.replace("/", "").replace("-", "").upper()
    # Heuristic: split known quote assets
    for quote in ("USDT", "USDC", "BUSD", "DAI", "BTC", "ETH", "BNB"):
        if s.endswith(quote) and len(s) > len(quote):
            return f"{s[: -len(quote)]}/{quote}"
    return s


def _binance_interval(interval: TimeInterval | str) -> str:
    mapping: dict[str, str] = {
        "1min": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "1h": "1h",
        "4h": "4h",
        "1day": "1d",
        "1week": "1w",
        "1month": "1M",
    }
    ival = interval.value if isinstance(interval, TimeInterval) else interval
    mapped = mapping.get(ival, ival)
    return mapped


# Build reverse lookup
_BINANCE_REVERSE: dict[str, str] = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1day",
    "1w": "1week",
    "1M": "1month",
}


def _reverse_binance_interval(raw: str | TimeInterval) -> str:
    if isinstance(raw, TimeInterval):
        return raw.value
    return _BINANCE_REVERSE.get(raw, raw)


# ── Manager ────────────────────────────────────────────────────


class DataIngestionManager:
    """Unified entry point for market data ingestion.

    Wraps all three API clients and delegates calls based on
    the *source* argument so the rest of the system never needs
    to know which provider is behind a symbol.

    Usage::

        mgr = DataIngestionManager(config)
        ohlcv = await mgr.fetch_ohlcv("AAPL", "1day", source="twelvedata")
        ind   = await mgr.fetch_economic("UNRATE", source="fred")
        btc   = await mgr.fetch_ohlcv("BTC/USDT", "1h", source="binance")
    """

    def __init__(self, config: DataIngestionConfig | None = None) -> None:
        self._cfg = config or DataIngestionConfig()
        self._fred = FREDClient(self._cfg)
        self._twelvedata = TwelveDataClient(self._cfg)
        self._binance = BinanceClient(self._cfg)

    # ── Public API ─────────────────────────────────────────

    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: TimeInterval | str = TimeInterval.D1,
        *,
        source: str = "twelvedata",
        **kwargs: Any,
    ) -> TimeSeries:
        """Candlestick data from the preferred *source*.

        Accepted sources: ``"twelvedata"``, ``"binance"``.
        """
        source_enum = DataSource(source)

        if source_enum == DataSource.BINANCE:
            points: list[OHLCV] = await self._binance.fetch_klines(symbol, interval, **kwargs)
        elif source_enum == DataSource.TWELVEDATA:
            points = await self._twelvedata.fetch_ohlcv(symbol, interval, **kwargs)
        else:
            raise ValueError(f"Unsupported OHLCV source: {source}")

        return TimeSeries(
            instrument=symbol,
            interval=TimeInterval(interval) if not isinstance(interval, TimeInterval) else interval,
            data_type=MarketDataType.OHLCV,
            source=source_enum,
            points=points,  # type: ignore[arg-type]
        )

    async def fetch_quote(
        self,
        symbol: str,
        *,
        source: str = "twelvedata",
    ) -> TimeSeries:
        """Latest quote for *symbol*."""
        source_enum = DataSource(source)
        if source_enum == DataSource.TWELVEDATA:
            q = await self._twelvedata.fetch_quote(symbol)
            points: list[Quote] = [q] if q else []
        else:
            raise ValueError(f"Unsupported quote source: {source}")

        return TimeSeries(
            instrument=symbol,
            data_type=MarketDataType.SPOT,
            source=source_enum,
            points=points,  # type: ignore[arg-type]
        )

    async def fetch_economic(
        self,
        series_id: str,
        *,
        source: str = "fred",
        **kwargs: Any,
    ) -> TimeSeries:
        """Macro‑economic indicator."""
        source_enum = DataSource(source)
        if source_enum == DataSource.FRED:
            points: list[EconomicIndicator] = await self._fred.fetch_series(series_id, **kwargs)
        else:
            raise ValueError(f"Unsupported economic source: {source}")

        return TimeSeries(
            instrument=series_id,
            data_type=MarketDataType.ECONOMIC,
            source=source_enum,
            points=points,  # type: ignore[arg-type]
        )

    async def fetch_orderbook(
        self,
        symbol: str,
        *,
        source: str = "binance",
        **kwargs: Any,
    ) -> dict | None:
        """Order book L1/L2 snapshot (Binance only)."""
        if DataSource(source) == DataSource.BINANCE:
            return await self._binance.fetch_orderbook(symbol, **kwargs)
        raise ValueError(f"Unsupported orderbook source: {source}")

    async def fetch_ticker_24hr(
        self,
        symbol: str,
        *,
        source: str = "binance",
    ) -> dict | None:
        """24‑hour ticker (Binance only)."""
        if DataSource(source) == DataSource.BINANCE:
            return await self._binance.fetch_ticker_24hr(symbol)
        raise ValueError(f"Unsupported ticker source: {source}")

    # ── Lifecycle ──────────────────────────────────────────

    async def close(self) -> None:
        """Close all underlying HTTP sessions."""
        await asyncio.gather(
            self._fred.close(),
            self._twelvedata.close(),
            self._binance.close(),
        )

    async def __aenter__(self) -> DataIngestionManager:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
