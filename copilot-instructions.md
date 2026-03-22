# Commodity/Stock Analysis Workspace Instructions

## Project Overview

**Purpose:** Automated Indian stock analysis platform that fetches market data from Yahoo Finance, calculates 16 technical indicators, generates bullish/bearish sentiment analysis, and serves an interactive web-based report.

**Target Audience:** Indian equity traders/analysts. Covers 2200+ stocks via NSE symbols.

**Architecture:** 3-tier pipeline:
```
Data Fetch (update_data.py) → Analysis Engine (bullish_bearish_table_report.py) → Web Server (server.py)
```

---

## Key Components & Responsibilities

### Primary Python Modules

| File | Responsibility | Key Functions |
|------|-----------------|---|
| `update_data.py` | **Data Fetcher** — Yahoo Finance integration | `download_data()`, `save_progress()`, batches 50 stocks/iteration, outputs `market_data.pkl` |
| `bullish_bearish_table_report.py` | **Analysis Engine** — Technical indicators & sentiment | `calculate_atr()`, `calculate_supertrend()`, `calculate_rsi()`, generates JSON analysis |
| `server.py` | **HTTP Server** — Report delivery & orchestration | `do_GET()`, `do_POST()`, port 5000, orchestrates full pipeline |

### Data Files

| File | Format | Purpose | Notes |
|------|--------|---------|-------|
| `EQUITY_L.csv` | CSV | BSE equity reference (symbol, name, ISIN, face value) | Source of truth for equity universe |
| `symbols.csv` | CSV (1-col) | Pre-filtered NSE stock symbols for analysis | Format: `SYMBOL.NS` (e.g., `GMRAIRPORT.NS`) |
| `market_data.pkl` | Pickle | OHLCV cache for all 2220+ stocks | Binary pandas DataFrame dict, keyed by symbol |
| `progress.json` | JSON | Real-time download progress | Fields: `percentage`, `status`, `message`, `timestamp` |
| `stock_analysis_table_report.json` | JSON | Final analysis output (2227 stocks, sentiment scores, indicators) | Consumed by HTML front-end |
| `stock_analysis_table_report.html` | HTML5+JS | Interactive sortable/filterable report | Filters: symbol, sentiment, RSI, price, volume |

---

## Build & Run Commands

### Quick Start (Local Development)

```bash
# Step 1: Download 1-year historical data for all ~2200 stocks
# ⏱️ Duration: 5-15 minutes (patience required, yfinance rate limiting)
python update_data.py

# Step 2: Calculate indicators and generate reports
# ⏱️ Duration: 2-5 minutes
python bullish_bearish_table_report.py

# Step 3: Launch web server and open browser
# 🌐 Serves at http://localhost:5000
python server.py
```

### Refresh Cycle (In-Browser)
Click **"Refresh Data"** button → Runs full pipeline in background → Progress bar updates → New report rendered.

---

## Technical Stack & Dependencies

- **Data Fetching:** `yfinance` (Yahoo Finance API wrapper)
- **Data Processing:** `pandas`, `numpy`
- **Web Server:** Built-in `http.server`, `socketserver` (no framework)
- **Caching:** Python `pickle` module
- **Frontend:** Vanilla HTML5 + JavaScript (no npm/build step)
- **Python Version:** 3.6+

**Install Dependencies:**
```bash
pip install pandas numpy yfinance
```

---

## Key Development Patterns & Conventions

### Data Flow Convention
1. **Fetch Phase:** `update_data.py` → writes `market_data.pkl` + updates `progress.json`
2. **Analysis Phase:** `bullish_bearish_table_report.py` reads `market_data.pkl` → writes `.json` + `.html`
3. **Serve Phase:** `server.py` serves `.html`, streams progress, re-runs pipeline on post request

### Progress Tracking Pattern
All long-running operations write to `progress.json`:
```python
progress_data = {
    "percentage": 0-100,
    "status": "downloading|analyzing|completed|error",
    "message": "Human-readable status",
    "timestamp": ISO 8601 or Unix timestamp
}
```

### Sentiment Scoring (Bullish/Bearish)
**Logic:**
- **Bearish dominant:** Low RSI alerts, price below key MAs (20/50), negative returns
- **Bullish signals:** RSI oversold (<30), price above MAs, positive 5d/20d returns, volume surge (>2× MA)
- **Score range:** 0-10 scale, stored in `stock_analysis_table_report.json`

### Technical Indicators Calculated
1. **MA20/MA50** — Simple moving averages
2. **RSI (14)** — Relative strength index for momentum
3. **ATR (14)** — Average true range for volatility
4. **Supertrend** — Trend direction with atr-based stops
5. **VWAP** — Volume-weighted average price
6. **Returns** — 5d/20d percentage changes
7. **Volume Trend** — Current vol vs 20d MA ratio

### Code Style Conventions
- **Shebang:** All scripts start with `#!/usr/bin/env python3`
- **Encoding:** `# -*- coding: utf-8 -*-` for UTF-8 support
- **Docstrings:** Module-level docstring describes purpose; function docstrings use triple-quotes
- **Error Handling:** Graceful error messages logged to console; progress saved to JSON on errors
- **Path Handling:** Use `Path` from `pathlib` for cross-platform compatibility

---

## Common Tasks & Recipes

### Task: Add a New Technical Indicator
1. Create function in `bullish_bearish_table_report.py`: `def calculate_my_indicator(df, period=14):`
2. Call in the analysis loop (near `calculate_rsi()`, etc.)
3. Add result to DataFrame column: `df['MyIndicator'] = my_indicator_value`
4. Include in JSON output dict: `'my_indicator': float(my_indicator_value)`
5. (Optional) Add filter to HTML table if user-facing

### Task: Filter Symbols (Change Universe)
1. Edit `symbols.csv` — remove/add NSE symbols
2. Run `python update_data.py` (only fetches symbols in file)
3. Run `python bullish_bearish_table_report.py` to regenerate
4. Refresh browser

### Task: Adjust Sentiment Thresholds
Edit logic in `bullish_bearish_table_report.py` function (search for `bullish_score` or `bearish_score`):
```python
# Example: Raise RSI oversold threshold from 30 to 35
if rsi < 35:  # was 30
    bullish_score += 2
```

### Task: Extend HTML Report Filters
1. Identify the filter logic in `stock_analysis_table_report.html` (JavaScript table filtering)
2. Add new `<input>` or `<select>` element for filter
3. Update `filterTable()` JavaScript function to apply new filter condition
4. Test in browser

---

## Potential Pitfalls & Solutions

| Pitfall | Cause | Solution |
|---------|-------|----------|
| **"No module named yfinance"** | Missing dependency | Run `pip install yfinance` |
| **Slow download (>30 min)** | Yahoo Finance rate limiting | Reduce stock count in `symbols.csv` or add delays between batches |
| **"Connection error" in update_data.py** | Network timeout or API down | Retry; Yahoo Finance can be flaky. Check internet connection |
| **Empty analysis output** | `market_data.pkl` missing/corrupted | Re-run `python update_data.py` |
| **Port 5000 already in use** | Another process on port | Change PORT in `server.py` or kill existing process |
| **Stale report in browser** | Browser cache | Hard-refresh (Ctrl+Shift+R) or clear cache |
| **Analysis incomplete (partial JSON)** | Script interrupted mid-run | Delete corrupted `.json` and re-run `python bullish_bearish_table_report.py` |

---

## Project-Specific Assumptions

1. **NSE Format:** All symbols in `symbols.csv` must be NSE format with `.NS` suffix (e.g., `INFY.NS`)
2. **1-Year History:** `update_data.py` always downloads 1 year of daily OHLCV data (hardcoded in yfinance call)
3. **Batch Size:** 50 stocks per yfinance batch call (hardcoded to avoid API throttling)
4. **Pickle Over SQL:** No database; `market_data.pkl` is the persistent data store
5. **Sentiment = Heuristic:** Bullish/bearish scores are rule-based, not ML models
6. **Server Blocks on Refresh:** Clicking refresh waits for full pipeline; no concurrent requests queued

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│  Browser (http://localhost:5000)        │
│  - Interactive HTML Table               │
│  - Filters: Symbol, Sentiment, RSI, vol │
│  - [Refresh Data] button                │
└────────────────┬────────────────────────┘
                 │
                 │ HTTP GET / POST
                 ↓
┌─────────────────────────────────────────┐
│  server.py (HTTP Handler)               │
│  - Serves stock_analysis_table_report    │
│  - Streams progress.json on /progress   │
│  - Spawns subprocess on /refresh-data   │
└────────────────┬────────────────────────┘
                 │
      ┌──────────┴──────────┐
      ↓                     ↓
┌──────────────────────┐  ┌──────────────────────────┐
│  update_data.py      │  │ bullish_bearish_table    │
│  - Fetch 1yr OHLCV   │  │ - Load market_data.pkl   │
│  - yfinance batches  │  │ - Calculate 16 indicators│
│  - Save .pkl cache   │  │ - Generate .json + .html │
│  - Write progress.json│  │ - Sentiment scoring      │
└──────────────────────┘  └──────────────────────────┘
      │                     │
      └──────────┬──────────┘
                 ↓
        ┌──────────────────────┐
        │  Data Files          │
        │ - market_data.pkl    │
        │ - progress.json      │
        │ - .json (analysis)   │
        │ - .html (report)     │
        └──────────────────────┘
```

---

## Editor & Testing Tips

- **Debugging progress:** Monitor `progress.json` in real-time while `update_data.py` runs
- **Break data fetch:** Set `symbols.csv` to 1 symbol for quick testing
- **Test sentiment logic:** Manually edit a stock row in `stock_analysis_table_report.json` and refresh HTML
- **Performance:** HTML filtering is client-side; large datasets (5000+ rows) may need pagination

---

## Maintenance & Future Enhancements

- **Potential improvements:** Add ML-based sentiment, cache refreshes at intervals, push notifications for bullish alerts
- **Known limitations:** Single-threaded server (blocks during refresh), no persistence layer beyond pickle files
- **Upgrade path:** Migrate to Flask + SQLAlchemy for scalability if needed

---

## Custom Agents

### Commodity Chatbot Agent (`/commodity`)
Specialized assistant for navigating this stock analysis system:
- **Query analysis:** Ask about bullish/bearish signals, specific stocks
- **Explain indicators:** RSI, Supertrend, MA20/50, ATR, VWAP, Bollinger Bands
- **Guide operations:** Help with data refresh, symbol management, troubleshooting
- **Add commodities:** Extend system to analyze gold, oil, silver

**Usage:** Type `/commodity` in chat to activate, or invoke via slash command with specific requests.

---

## Quick Reference

| Question | Answer |
|----------|--------|
| **How do I start?** | `python update_data.py` → `python bullish_bearish_table_report.py` → `python server.py` |
| **Where is data stored?** | `market_data.pkl` (cache), `stock_analysis_table_report.json` (analysis), `progress.json` (real-time status) |
| **How do I add new stocks?** | Edit `symbols.csv`, re-run `update_data.py` |
| **How long does a full refresh take?** | ~10-20 min (download + analysis depends on network/API) |
| **Can I run on different port?** | Edit `PORT = 5000` in `server.py` |
| **What if I need to tweak indicators?** | Edit calculation functions in `bullish_bearish_table_report.py` |
| **Browser showing old data?** | Hard-refresh (Ctrl+Shift+R) or clear cache |
| **Need chatbot help?** | Use `/commodity` agent — query data, explain indicators, guide operations |

