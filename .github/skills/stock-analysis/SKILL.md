---
name: "stock-analysis-complete-workflow"
description: "Use when: running the complete stock analysis pipeline from data refresh through report generation. Bundles the multi-step workflow for updating market data, calculating technical indicators (Supertrend, VWAP, ATR), analyzing bullish/bearish signals, and serving the analysis report via HTTP."
---

# Complete Stock Analysis Workflow

Complete pipeline for updating market data, performing technical analysis, and serving interactive reports.

## What This Skill Does

Automates the workflow for:
- Refreshing market data from Yahoo Finance
- Calculating advanced technical indicators
- Generating bullish/bearish analysis tables
- Serving analysis reports via HTTP server

## Quick Start Checklist

### 1. Update Market Data
- **Command**: `python update_data.py`
- **What it does**: Fetches fresh stock data from Yahoo Finance, updates `market_data.pkl`
- **When to run**: Before analysis to ensure current data
- **Expected output**: CSV reports and pickle data file

### 2. Generate Analysis Report
- **Command**: `python bullish_bearish_table_report.py`
- **What it does**: Calculates technical indicators (Supertrend, VWAP, ATR), generates bullish/bearish analysis table
- **What it creates**: `stock_analysis_table_report.json` and `stock_analysis_table_report.html`
- **Expected output**: Analysis table with signals grouped by market sentiment

### 3. Serve the Report
- **Command**: `python server.py`
- **What it does**: Starts HTTP server on port 5000 serving the analysis report
- **Access**: Open browser to `http://localhost:5000`
- **Features**: Click "Refresh Data" button to update analysis without restarting

### 4. Stop the Server
- **Action**: Press `Ctrl+C` in terminal running server

## Decision Points

**Do you need fresh data?**
- Yes → Run `update_data.py` first
- No (using existing data) → Skip to step 2

**Do you want an interactive report?**
- Yes → Run `server.py` and access via browser
- No (just generate report file) → Run step 2 only, skip step 3

## Key Files & Outputs

| File | Purpose | Output |
|------|---------|--------|
| `update_data.py` | Fetch and cache market data | `market_data.pkl`, CSV files |
| `bullish_bearish_table_report.py` | Calculate indicators & signals | `stock_analysis_table_report.json`, `.html` |
| `server.py` | Serve interactive report | HTTP server on port 5000 |

## Technical Indicators Used

- **ATR (Average True Range)**: Volatility measurement (14-period default)
- **Supertrend**: Trend reversal signals with multiplier (10-period, 3x ATR)
- **VWAP**: Volume-weighted average price for support/resistance
- **Bullish/Bearish Signals**: Combined indicator analysis

## Completion Criteria

✓ Market data updated with fresh Yahoo Finance data
✓ Technical indicators calculated for all symbols
✓ HTML report generated and accessible
✓ Server running and responding to refresh requests
✓ Bullish/bearish analysis table properly formatted

## Troubleshooting

**No data in report?**
- Ensure `EQUITY_L.csv` exists or `market_data.pkl` was created
- Run `update_data.py` to fetch initial data

**Server won't start?**
- Check if port 5000 is already in use
- Try `netstat -ano | findstr :5000` to find conflicting process

**Indicators showing zero/null?**
- Insufficient historical data for symbol
- Verify symbol exists in market data
- Run `update_data.py` again

## Related Skills

- Performance analysis & backtesting (future)
- Real-time price alerts (future)
