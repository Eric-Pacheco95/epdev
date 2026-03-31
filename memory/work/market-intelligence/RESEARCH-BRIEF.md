# Market Intelligence Layer -- Research Brief

> Prepared: 2026-03-30 | For: Eric P (epdev/Jarvis)
> Goal: Financial independence through AI-augmented investing beyond crypto

---

## 1. DATA SOURCES -- Ranked by Value

### Tier 1: Must-Have (free, high signal density)

| Source | What | Python Pkg | Free Limits | Notes |
|--------|------|-----------|-------------|-------|
| **FRED** | 800K+ macro time series (GDP, CPI, rates, employment, yield curves) | `fredapi` | 120 req/min, free API key | Foundation for macro regime detection. Pairs with crypto-bot's regime.py |
| **yfinance** | US/intl stocks, ETFs, options, fundamentals | `yfinance` | ~2000 calls/day, no key | Unreliable long-term (scraping-based, Yahoo can break it). Use as primary for prototyping, plan migration path |
| **CoinGecko** | Crypto prices, market caps, trending | `pycoingecko` | 30 calls/min free | Already used in crypto-bot. Extend to portfolio-level crypto tracking |
| **SEC EDGAR** | 10-K, 10-Q, 8-K filings, XBRL financials | `edgartools` | No key, no rate limit, MIT license | Free forever. Structured Python objects. Best-in-class for fundamentals |
| **Finnhub** | Real-time quotes, news, sentiment, earnings calendar | `finnhub-python` | 60 calls/min free | Most generous free tier for real-time. Good news/sentiment endpoint |

### Tier 2: High Value (free tier, some limits)

| Source | What | Python Pkg | Free Limits | Notes |
|--------|------|-----------|-------------|-------|
| **Alpha Vantage** | Stocks, forex, crypto, technicals, fundamentals | `alpha_vantage` | 25 req/day (free), 75/min ($50/mo) | Free tier very tight. Good for daily batch jobs, not real-time |
| **Polygon.io** | US stocks, options, forex, crypto | `polygon-api-client` | 5 calls/min (free) | Delayed data on free tier. Excellent websocket on paid ($29/mo) |
| **Twelve Data** | Time series, technicals, real-time | `twelvedata` | 800 req/day, 8/min | Good balance. Has MCP server for Claude integration |

### Tier 3: Niche / Supplementary

| Source | What | Cost | Notes |
|--------|------|------|-------|
| **CoinMarketCap** | Crypto rankings, listings | Free tier: 10K calls/mo | Overlaps CoinGecko. Use only if CG rate-limited |
| **NewsAPI** | Financial news headlines | Free: 100 req/day | Feed into FinBERT sentiment pipeline |
| **Reddit (pushshift/PRAW)** | r/wallstreetbets, r/investing sentiment | Free | Social sentiment source. Complement to Grok X search |
| **Alternative.me** | Fear & Greed Index (crypto + traditional) | Free, no key | Single-number regime signal |

### MCP Servers (Claude-Native Integration)

These let Jarvis query market data directly in-session:

| Server | Data | Notes |
|--------|------|-------|
| **Alpha Vantage MCP** | Stocks, forex, crypto | Official MCP, stdio transport, free key |
| **Financial Datasets MCP** | Financials, prices, news | `npx @financial-datasets/mcp-server` |
| **Twelve Data MCP** | Time series, quotes | Good for in-session analysis |

**Recommendation**: Add Alpha Vantage MCP to `.mcp.json` for on-demand in-session queries. Keep batch collection in Python scripts on Task Scheduler.

---

## 2. CLI TOOLS & DATA COLLECTION

### Terminal Monitoring

| Tool | Language | What | JSON Output |
|------|----------|------|-------------|
| `ticker` | Go | Real-time stocks/crypto in terminal | YAML config, no JSON |
| `cointop` | Go | htop-like crypto dashboard | Has API mode |
| `stonks` | Go | Terminal stock charts | Display only |

**Verdict**: These are for eyeball monitoring, not data pipelines. Build custom Python CLIs instead.

### Recommended Python CLI Architecture

```
tools/market/
  collect_prices.py      # yfinance + CoinGecko -> data/market/prices/
  collect_macro.py       # FRED indicators -> data/market/macro/
  collect_news.py        # Finnhub news -> data/market/news/
  collect_filings.py     # EDGAR new filings -> data/market/filings/
  analyze_sentiment.py   # FinBERT on collected news -> data/market/sentiment/
  generate_signals.py    # All data -> market signals -> memory/learning/signals/
  morning_brief.py       # Synthesize into daily briefing -> Slack #jarvis-inbox
```

All scripts: JSON output, Windows Task Scheduler compatible, ASCII-only terminal output (per steering rule).

### Task Scheduler Cadence

| Script | Frequency | Why |
|--------|-----------|-----|
| `collect_prices.py` | Every 15 min (market hours) | Track intraday moves |
| `collect_macro.py` | Daily 6 AM | FRED updates daily/weekly |
| `collect_news.py` | Every 30 min | News-driven sentiment |
| `collect_filings.py` | Daily 7 PM | SEC filings mostly after-hours |
| `analyze_sentiment.py` | After each news collection | Pipeline dependency |
| `generate_signals.py` | Every 30 min (market hours) | Signal freshness |
| `morning_brief.py` | Daily 7 AM | Eric's daily market read |

---

## 3. DATA INTERPRETATION METHODS

### Technical Analysis

| Library | Install | Strengths | Rec |
|---------|---------|-----------|-----|
| **pandas-ta** | `pip install pandas_ta` | 150+ indicators, Pandas native, no C deps | PRIMARY -- easiest on Windows |
| **TA-Lib** | `pip install TA-Lib` (needs C lib) | Industry standard, fastest | SECONDARY -- Windows install painful |
| **ta** (bukosabino) | `pip install ta` | Simple, fewer indicators | Good for prototyping |
| **tulipy** | `pip install tulipy` | C-backed, fast | Skip -- pandas-ta covers it |

**Pick**: pandas-ta as primary. No C compilation issues on Windows. Drop-in with existing pandas workflows.

### Sentiment Analysis

| Tool | What | How |
|------|------|-----|
| **FinBERT** (`ProsusAI/finbert`) | Financial text -> positive/negative/neutral | `transformers` pipeline, runs local, 89% accuracy on financial text |
| **finbert-tone** (`yiyanghkust/finbert-tone`) | Analyst report tone | Finer-grained than base FinBERT |
| **VADER** | General sentiment | Lightweight fallback, no GPU needed |
| **Grok X search** | Real-time social sentiment | Already in crypto-bot P2 pipeline |

**Architecture**: Finnhub news -> FinBERT scoring -> aggregate per-ticker sentiment -> feed into signal generator. FinBERT model is ~440MB, runs on CPU in ~100ms/headline. Batch 50 headlines in under 10 seconds.

### Anomaly Detection

| Method | Library | Use Case |
|--------|---------|----------|
| Z-score on volume | numpy/scipy | Unusual volume spikes |
| Rolling std deviation bands | pandas | Price breakouts |
| Isolation Forest | scikit-learn | Multi-feature anomalies |
| CUSUM | statsmodels | Regime change detection |

**Pattern**: Calculate rolling 20-day stats. Flag when current value exceeds 2.5 sigma. Cross-reference with news sentiment for confirmation. This mirrors the crypto-bot's approach but for traditional markets.

### Cross-Asset Correlation

Track rolling correlations between:
- SPY vs BTC (risk-on/risk-off regime)
- VIX vs crypto volatility
- DXY (dollar index) vs gold vs BTC
- 10Y yield vs growth stocks (QQQ)
- Sector rotation (XLF, XLK, XLE, XLV)

Library: `pandas` `.rolling().corr()` is sufficient. No special tooling needed.

---

## 4. SIGNAL GENERATION & BACKTESTING

### Signal Architecture

```
Raw Data -> Indicators -> Conditions -> Signals -> Scoring -> Ranking -> Brief
```

Market signals differ from Jarvis learning signals:

| Dimension | Learning Signals | Market Signals |
|-----------|-----------------|----------------|
| Rating | 1-10 subjective | Quantitative score (0-100) |
| Decay | Absorbed into synthesis | Expires (intraday to weekly) |
| Storage | `memory/learning/signals/` | `data/market/signals/` |
| Consumers | `/synthesize-signals` | `morning_brief.py`, alert system |
| Format | Markdown | JSON (machine-readable) |

### Signal Types to Generate

1. **Macro Regime** -- bull/bear/transition based on FRED yield curve, unemployment, PMI
2. **Sector Momentum** -- relative strength across 11 GICS sectors
3. **Sentiment Divergence** -- price up + sentiment down = warning (or vice versa)
4. **Volume Anomaly** -- unusual volume without news = institutional activity
5. **Earnings Surprise** -- post-earnings drift detection
6. **Correlation Break** -- when BTC/SPY correlation breaks, regime is shifting
7. **Fear & Greed Extreme** -- contrarian signals at extremes

### Backtesting

| Framework | Speed | Live Trading | Windows | Rec |
|-----------|-------|--------------|---------|-----|
| **vectorbt** | Fastest (NumPy/Numba) | Via StrateQueue | Yes | PRIMARY for research |
| **Backtrader** | Medium | Built-in broker support | Yes | Good for live bridge |
| **Zipline-Reloaded** | Slow | No | Tricky on Windows | Skip |
| **backtesting.py** | Fast | No | Yes | Simple alternative |

**Pick**: vectorbt for signal research and backtesting. It handles thousands of parameter combinations in seconds. If Eric wants to bridge to live stock trading later, add Backtrader or Alpaca SDK.

### Key Metrics

- **Sharpe Ratio**: >1.5 target (risk-adjusted return)
- **Sortino Ratio**: penalizes downside only, better for asymmetric strategies
- **Max Drawdown**: never exceed 20% from peak
- **Win Rate**: >45% with positive expectancy
- **Profit Factor**: >1.5 (gross profit / gross loss)

---

## 5. INTEGRATION ARCHITECTURE

### How It Fits Into Jarvis

```
                    +------------------+
                    |  Task Scheduler  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
        collect_*.py   analyze_*.py  generate_signals.py
              |              |              |
              v              v              v
        data/market/   data/market/   data/market/signals/
        prices/        sentiment/     YYYY-MM-DD_market.json
        macro/         news/
        filings/
              |              |              |
              +--------------+--------------+
                             |
                    morning_brief.py
                             |
                    +--------v---------+
                    | Slack #jarvis-   |
                    | market-brief     |
                    +------------------+
                             |
                    (Eric reads on mobile)
```

### Data Flow

1. **Collectors** run on Task Scheduler, write JSON to `data/market/`
2. **Analyzers** (sentiment, technicals) process raw data, write enriched JSON
3. **Signal Generator** produces scored market signals in `data/market/signals/`
4. **Morning Brief** synthesizes signals into a readable Slack message
5. **Alert System** pushes high-urgency signals (anomalies, extreme fear/greed) immediately
6. **MCP Servers** enable in-session deep dives ("Jarvis, analyze NVDA fundamentals")

### Market Signal Schema

```json
{
  "timestamp": "2026-03-30T07:00:00Z",
  "type": "sector_momentum",
  "ticker": "XLK",
  "score": 78,
  "direction": "bullish",
  "confidence": 0.82,
  "evidence": {
    "rsi_14": 62,
    "macd_signal": "bullish_cross",
    "volume_zscore": 1.8,
    "sentiment": 0.65
  },
  "expires": "2026-03-31T07:00:00Z",
  "source_apis": ["yfinance", "finnhub", "fred"]
}
```

### Integration with Crypto-Bot

The crypto-bot already has: regime detection, signal scoring (0-100), decay, corroboration matrix, ML weight retraining. The market intelligence layer should:

- Share the regime signal (macro regime from FRED enriches crypto-bot's BTC-only regime)
- Use the same signal scoring pattern (0-100, exponential decay, source corroboration)
- Feed cross-asset correlation data to both systems
- Keep separate execution -- crypto-bot trades crypto, market layer provides intelligence (not trades, initially)

---

## 6. PHASED BUILD PLAN

### Phase 1: Foundation (1 weekend)
- [ ] Install core packages: `yfinance`, `fredapi`, `finnhub-python`, `pandas-ta`, `edgartools`
- [ ] Build `collect_prices.py` -- top 50 stocks + major ETFs (SPY, QQQ, IWM, sector ETFs)
- [ ] Build `collect_macro.py` -- 10 key FRED series (10Y yield, CPI, unemployment, PMI, fed funds rate, M2, consumer sentiment, housing starts, retail sales, initial claims)
- [ ] Set up `data/market/` directory structure
- [ ] Schedule on Task Scheduler with basic error handling
- [ ] Verify: JSON files accumulating, no encoding errors

### Phase 2: Intelligence (1 week)
- [ ] Build `collect_news.py` using Finnhub news endpoint
- [ ] Add FinBERT sentiment pipeline (`analyze_sentiment.py`)
- [ ] Build `generate_signals.py` -- macro regime + sector momentum + volume anomaly
- [ ] Add pandas-ta indicators to price collection (RSI, MACD, Bollinger, ATR)
- [ ] Cross-asset correlation tracker (SPY/BTC, VIX, DXY)
- [ ] Verify: signals generating with scores, no false positives flooding

### Phase 3: Delivery (3-4 days)
- [ ] Build `morning_brief.py` -- daily Slack digest to `#jarvis-market-brief`
- [ ] Add urgent alert path for anomalies (>2.5 sigma moves, extreme sentiment)
- [ ] Add Alpha Vantage MCP server to `.mcp.json` for in-session queries
- [ ] Connect macro regime output to crypto-bot's regime.py as supplementary input
- [ ] Verify: morning brief arrives by 7 AM, alerts fire within 5 min of detection

### Phase 4: Backtesting & Refinement (ongoing)
- [ ] Install vectorbt, build backtesting harness for generated signals
- [ ] Backtest sector momentum signals against 5-year SPY data
- [ ] Add SEC EDGAR filing monitor for watchlist companies
- [ ] Sentiment divergence signal (price vs. FinBERT)
- [ ] Build `/market-brief` Jarvis skill for on-demand market summary
- [ ] Evaluate: Sharpe > 1.0 on backtested signals before any real allocation

### Phase 5: Advanced (future)
- [ ] Earnings surprise detection (Finnhub earnings calendar + post-earnings price action)
- [ ] Options flow analysis (if Polygon.io paid tier adopted)
- [ ] Portfolio optimization layer (Modern Portfolio Theory, risk parity)
- [ ] LLM-powered market narrative generation (why is X moving?)
- [ ] Bridge to paper trading for stocks (Alpaca free tier)

---

## 7. COST ESTIMATE

| Component | Monthly Cost |
|-----------|-------------|
| FRED API | $0 |
| yfinance | $0 |
| Finnhub (free) | $0 |
| CoinGecko (free) | $0 |
| SEC EDGAR | $0 |
| Alpha Vantage (free) | $0 |
| FinBERT (local CPU) | $0 (compute only) |
| **Total Phase 1-3** | **$0** |
| Polygon.io (if needed) | $29/mo |
| Alpha Vantage premium | $50/mo |
| **Max with upgrades** | **$79/mo** |

---

## 8. KEY RISKS & MITIGATIONS

| Risk | Mitigation |
|------|-----------|
| yfinance breaks (scraping-based) | Finnhub as fallback; Alpha Vantage MCP for in-session |
| FinBERT model too large for Eric's machine | Test first; VADER as lightweight fallback |
| Signal overload (too many alerts) | Threshold tuning; start conservative, loosen as trust builds |
| Scope creep into active trading | Phase 1-3 is intelligence only; no auto-trading stocks |
| Data staleness on weekends | Reduce collection frequency; macro data updates regardless |

---

## Sources

- [Financial Data APIs Compared (2026)](https://www.ksred.com/the-complete-guide-to-financial-data-apis-building-your-own-stock-market-data-pipeline-in-2025/)
- [Best Financial Data APIs 2026](https://www.nb-data.com/p/best-financial-data-apis-in-2026)
- [7 Best Financial Data MCP Servers (2026)](https://marketxls.com/blog/best-financial-data-mcp-servers-ai-market-data)
- [Alpha Vantage MCP](https://mcp.alphavantage.co/)
- [Financial Datasets MCP Server](https://github.com/financial-datasets/mcp-server)
- [EdgarTools - SEC EDGAR Python Library](https://github.com/dgunning/edgartools)
- [FRED API Documentation](https://fred.stlouisfed.org/docs/api/fred/)
- [fredapi PyPI](https://pypi.org/project/fredapi/)
- [ProsusAI/finbert on HuggingFace](https://huggingface.co/ProsusAI/finbert)
- [pandas-ta Documentation](https://www.pandas-ta.dev/)
- [VectorBT Documentation](https://vectorbt.dev/)
- [VectorBT vs Backtrader Comparison](https://medium.com/@trading.dude/battle-tested-backtesters-comparing-vectorbt-zipline-and-backtrader-for-financial-strategy-dee33d33a9e0)
- [ticker CLI](https://github.com/achannarasappa/ticker)
- [cointop CLI](https://github.com/cointop-sh/cointop)
- [Top Python Trading Tools (2026)](https://analyzingalpha.com/python-trading-tools)
- [AI Quant Trading Bot (2026)](https://markaicode.com/ai-quant-trading-bot-backtest-risk-live-execution/)
