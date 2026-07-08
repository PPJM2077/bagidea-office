# Market Data Sources — Free & Public APIs

> **Compiled:** 2026-07-07 | **Maintainer:** Market Analyst agent
> Covers Gold, Forex, Crypto, Economic Calendar, and Macro data.
> All sources listed are free-tier accessible (most require a free API key).

---

## Table of Contents

- [1. Unified APIs (Multi-Asset)](#1-unified-apis-multi-asset)
- [2. Gold / Precious Metals](#2-gold--precious-metals)
- [3. Forex (Foreign Exchange)](#3-forex-foreign-exchange)
- [4. Crypto](#4-crypto)
- [5. Economic Calendar & Events](#5-economic-calendar--events)
- [6. Macro & Central Bank Data](#6-macro--central-bank-data)
- [7. Real-Time WebSocket Feeds (Unified)](#7-real-time-websocket-feeds-unified)
- [8. Reference Architecture](#8-reference-architecture)

---

## 1. Unified APIs (Multi-Asset)

These provide Gold, Forex, AND Crypto from a single integration point — best for simplicity.

| Provider | Gold | Forex | Crypto | Free Tier | Notes |
|----------|------|-------|--------|-----------|-------|
| **Twelvedata** | ✅ | ✅ | ✅ | 800 req/day | Modern REST + WebSocket; best balance of limit & coverage |
| **Alpha Vantage** | ✅ (XAU/USD) | ✅ | ✅ | 5 req/min, 500/day | Industry standard; very stable; includes technical indicators |
| **Financial Modeling Prep** | ✅ | ✅ | ✅ | 250 req/day | Strong financial models + SEC filings |
| **Tiingo** | ✅ (via ETFs) | ✅ | ✅ | Generous; 1000+ symbols | Cleanest historical data; data-scientist favorite |

### Twelvedata

```
GET https://api.twelvedata.com/time_series?symbol=GOLD/EUR&interval=1day&apikey=YOUR_KEY
GET https://api.twelvedata.com/time_series?symbol=EUR/USD&interval=1h&apikey=YOUR_KEY
GET https://api.twelvedata.com/time_series?symbol=BTC/USD&interval=15min&apikey=YOUR_KEY
```

- **WebSocket:** `wss://ws.twelvedata.com/v1/quotes/price?apikey=YOUR_KEY`
- **Docs:** [https://twelvedata.com/docs](https://twelvedata.com/docs)
- **Use Case:** Primary unified REST layer for daily/hourly analysis.

### Alpha Vantage

```
GET https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAU&to_currency=USD&apikey=YOUR_KEY
GET https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=EUR&to_symbol=USD&interval=5min&apikey=YOUR_KEY
GET https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_INTRADAY&symbol=BTC&market=USD&apikey=YOUR_KEY
```

- **Docs:** [https://www.alphavantage.co/documentation/](https://www.alphavantage.co/documentation/)
- **Use Case:** Reliable fallback; best for daily EOD data + technical indicators (RSI, MACD, SMA).

### Tiingo

```
GET https://api.tiingo.com/tiingo/fx/eurusd/prices?startDate=2026-01-01&endDate=2026-07-07
GET https://api.tiingo.com/tiingo/crypto/prices?tickers=btcusd&startDate=2026-01-01
```

- **Docs:** [https://www.tiingo.com/documentation](https://www.tiingo.com/documentation)
- **Use Case:** High-quality historical forex; aggregated crypto from multiple exchanges.

---

## 2. Gold / Precious Metals

Dedicated sources for spot gold, futures, and London Fix.

| Source | Data | Free Tier | Latency |
|--------|------|-----------|---------|
| **GoldAPI.io** | Spot XAU/USD + historical | 100 req/day | Real-time |
| **FRED (St. Louis Fed)** | London Fix AM/PM daily | Unlimited (free key) | T+1 |
| **Chainlink XAU/USD Feed** | Decentralized oracle price | Free to read | On-chain |
| **Pyth Network** | Gold from CME + venues | Free to read | Sub-second |

### GoldAPI.io

```
GET https://www.goldapi.io/api/XAU/USD
Header: x-access-token: YOUR_API_KEY
```

- **Website:** [https://www.goldapi.io/](https://www.goldapi.io/)
- **Use Case:** Simplest dedicated gold price API; real-time spot + 25-year history.

### FRED — London Fix

| Series ID | Description |
|-----------|-------------|
| `GOLDAMGBD228NLBM` | Gold Fixing Price 10:30 AM (USD) |
| `GOLDPMGBD228NLBM` | Gold Fixing Price 3:00 PM (USD) |

```
GET https://api.stlouisfed.org/fred/series/observations?series_id=GOLDAMGBD228NLBM&api_key=YOUR_KEY&file_type=json
```

- **Website:** [https://fred.stlouisfed.org/](https://fred.stlouisfed.org/)
- **Use Case:** Authoritative daily reference price; essential for backtesting.

---

## 3. Forex (Foreign Exchange)

| Source | Pairs | Free Tier | Real-Time? | Notes |
|--------|-------|-----------|------------|-------|
| **OANDA v20 API** | 70+ pairs | Free for retail | ✅ Yes | Institutional-grade rates; best for Forex |
| **ExchangeRate-API** | 150+ currencies | 1,500 req/month | ✅ Yes | Lightweight; great for conversion rates |
| **Frankfurter** | 30+ major pairs | Unlimited — no key | ❌ Delayed | ECB-sourced; open source |
| **FRED H.10** | Major crosses & USD index | Unlimited | ❌ T+1 | Fed official rates; daily only |
| **Dukascopy** | 50+ pairs | Free (account req) | ✅ Yes | High-frequency tick data |

### OANDA v20 (REST)

```
GET https://api-fxpractice.oanda.com/v3/accounts/{accountID}/candles?instrument=EUR_USD&granularity=M15&count=100
Header: Authorization: Bearer YOUR_API_KEY
```

- **Docs:** [http://developer.oanda.com/](http://developer.oanda.com/)
- **Use Case:** Primary forex data source for algo trading; supports 1-min to monthly candles.

### Frankfurter (ECB Data)

```
GET https://api.frankfurter.dev/latest?from=USD&to=EUR,GBP,JPY
```

- **Website:** [https://frankfurter.dev/](https://frankfurter.dev/)
- **Use Case:** No-registration-required reference rates; ECB official.

### FRED — Forex Series

| Series ID | Pair |
|-----------|------|
| `DEXUSEU` | EUR/USD |
| `DEXJPUS` | USD/JPY |
| `DEXUSUK` | GBP/USD |
| `DEXCAUS` | USD/CAD |
| `DEXSZUS` | USD/CHF |
| `DTWEXBGS` | USD Broad Trade-Weighted |

---

## 4. Crypto

| Source | Coverage | Free Tier | Real-Time? | Notes |
|--------|----------|-----------|------------|-------|
| **Binance API** | 500+ pairs | Unlimited public | ✅ WebSocket + REST | Industry standard for liquidity data |
| **CoinGecko** | 12,000+ coins | 50 req/min | ✅ | Best for altcoin coverage |
| **CoinCap.io 2.0** | Top 1,000+ | Unlimited — no key | ✅ | No API key needed |
| **Kraken API** | 100+ pairs | Unlimited public | ✅ WebSocket | Strong EUR pairs |
| **Binance Public Data** | Full trade/depth history | Free (S3) | ❌ Historical | GB-scale backtesting data |

### Binance API

```
# REST — Latest price
GET https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT

# REST — Klines (candles)
GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=100

# WebSocket — Real-time trades
wss://stream.binance.com:9443/ws/btcusdt@trade
```

- **Rate Limits:** 200 streams per WS connection; 5 connections/IP (Spot)
- **Docs:** [https://binance-docs.github.io/apidocs/](https://binance-docs.github.io/apidocs/)
- **Use Case:** Primary real-time crypto data; order book depth, trade flow, funding rates.

### CoinGecko

```
GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,thb
GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=90
```

- **Docs:** [https://www.coingecko.com/en/api](https://www.coingecko.com/en/api)
- **Use Case:** Altcoin screening, market cap rankings, on-chain metrics.

### CoinCap.io 2.0

```
GET https://api.coincap.io/v2/assets/bitcoin
GET https://api.coincap.io/v2/assets/bitcoin/history?interval=d1
```

- **Website:** [https://docs.coincap.io/](https://docs.coincap.io/)
- **Use Case:** Drop-in replacement if you want zero-registration.

---

## 5. Economic Calendar & Events

| Source | Data | Free Tier | Access Method |
|--------|------|-----------|---------------|
| **ForexFactory** | Impact ratings, actuals, consensus | Unlimited | Scrape (no official API) |
| **TradingEconomics** | 200+ countries, 20M indicators | 100 req/month | Official API |
| **Myfxbook** | Calendar + actuals | Official API (key req) | REST |
| **Finnhub** | Economic calendar + news | 60 calls/min free | REST + WebSocket |
| **Investing.com** | Full calendar + events | Unlimited | Scrape (anti-bot) |

### ForexFactory (Scrape)

ForexFactory has **no official API**. The retail-standard calendar (impact colors, consensus, actuals) is accessible via scraping the AJAX endpoint that powers the web calendar.

**Existing scrapers:**
- `forex-factory-calendar` (Python) — [GitHub search](https://github.com/search?q=forex-factory-calendar)
- `ffscraper` — various open-source forks

**Use Case:** Must-have for sentiment-aware trading; gives you the exact data every retail trader sees.

### TradingEconomics

```
GET https://api.tradingeconomics.com/calendar/country/united%20states?apikey=YOUR_KEY
GET https://api.tradingeconomics.com/calendar/indicator/nonfarm%20payrolls?apikey=YOUR_KEY
```

- **Docs:** [https://docs.tradingeconomics.com/](https://docs.tradingeconomics.com/)
- **Use Case:** Official API for global macro events; clean JSON, low-frequency dashboards.

### Finnhub

```
GET https://finnhub.io/api/v1/calendar/economic?from=2026-07-01&to=2026-07-07&token=YOUR_KEY
```

- **Website:** [https://finnhub.io/](https://finnhub.io/)
- **Use Case:** Real-time economic calendar for live trading; higher rate limit than TradingEconomics.

---

## 6. Macro & Central Bank Data

| Source | Data | Free Tier | Notes |
|--------|------|-----------|-------|
| **FRED API** | 800,000+ macro series | Free (key req) | Inflation, GDP, rates, employment — all free |
| **World Bank API** | Global development data | Free | GDP, CPI by country |
| **IMF Data** | Macro forecasts + actuals | Free | Financial statistics |
| **BLS (Bureau of Labor)** | Employment, CPI | Free | Official US labor data |
| **BEA (Bureau of Econ. Analysis)** | GDP, trade balances | Free | US economic accounts |
| **ECB SDMX API** | Eurozone rates, inflation | Free | Euro-area official data |

### FRED — Key Series for Trading

| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| `FEDFUNDS` | Federal Funds Effective Rate | Daily |
| `CPIAUCSL` | Consumer Price Index (All Items) | Monthly |
| `UNRATE` | Unemployment Rate | Monthly |
| `PAYEMS` | Nonfarm Payrolls | Monthly |
| `GDP` | Gross Domestic Product | Quarterly |
| `SP500` | S&P 500 Index | Daily |
| `T10Y2Y` | 10Y-2Y Treasury Yield Spread | Daily |
| `DGS10` | 10-Year Treasury Yield | Daily |
| `DGS2` | 2-Year Treasury Yield | Daily |

```
GET https://api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&api_key=YOUR_KEY&file_type=json&observation_start=2024-01-01&observation_end=2026-12-31
```

- **API Key:** Free at [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
- **Use Case:** Gold/Forex macro backdrop — rate decisions, inflation trends, yield curves.

---

## 7. Real-Time WebSocket Feeds (Unified)

For sub-second data in live trading, use WebSocket instead of REST polling.

```
# Binance — Crypto real-time
wss://stream.binance.com:9443/ws/btcusdt@trade
wss://stream.binance.com:9443/ws/btcusdt@kline_1m

# Kraken — Crypto + Forex (EUR pairs)
wss://ws.kraken.com

# Twelvedata — Multi-asset
wss://ws.twelvedata.com/v1/quotes/price?apikey=YOUR_KEY

# CoinCap — Crypto (no key)
wss://ws.coincap.io/prices?assets=bitcoin,ethereum

# OANDA — Forex streaming
wss://stream-fxpractice.oanda.com/v3/accounts/{accountID}/streaming/instruments
```

---

## 8. Reference Architecture

A robust free-tier stack for an automated trading/research system in 2026:

```
┌─────────────────────────────────────────────────────┐
│                   DATA LAYER                         │
├─────────────────────────────────────────────────────┤
│  PRIMARY REST    → Twelvedata (800 req/day)          │
│  CRYPTO LIVE     → Binance WebSocket (free, unlim.)  │
│  CRYPTO HIST     → Binance Public Data / CoinGecko   │
│  FOREX LIVE      → OANDA v20 API (free retail)       │
│  FOREX HIST      → Tiingo / FRED H.10 (daily)        │
│  GOLD SPOT       → GoldAPI.io (100 req/day)          │
│  GOLD REFERENCE  → FRED London Fix (free)            │
│  CALENDAR        → ForexFactory scrape / Finnhub     │
│  MACRO           → FRED API (free, unlimited)        │
│  DECENTRALIZED   → Chainlink / Pyth (on-chain ref)   │
└─────────────────────────────────────────────────────┘
```

### Failover Strategy

| Primary | Fallback 1 | Fallback 2 |
|---------|-----------|------------|
| Twelvedata | Alpha Vantage | — |
| Binance WS | Kraken WS | CoinGecko REST |
| OANDA | ExchangeRate-API | Frankfurter (ECB) |
| GoldAPI | FRED London Fix | Chainlink oracle |
| Finnhub (calendar) | TradingEconomics | ForexFactory scrape |

**Key design principles:**
1. **Never rely on a single source.** Free APIs change/break — always have a fallback.
2. **Prefer WebSocket over REST** for any real-time signal or latency-sensitive use.
3. **Cache aggressively.** FRED (macro) changes daily at most — no need to poll more than once per hour.
4. **Watch rate limits.** Most "unlimited" free tiers have hidden caps; log your consumption.

---

> **Pro tip:** For the BagIdeaOffice Quant project, start with Twelvedata (unified) + Binance WS (crypto) + GoldAPI (gold) + ForexFactory (calendar) + FRED (macro). This covers all surfaces with minimal integration overhead.
