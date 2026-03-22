#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Bullish/Bearish Analysis with Table Format, Filters, and Advanced Indicators
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import json

IST = timezone(timedelta(hours=5, minutes=30))

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values
    
    tr_list = []
    tr_list.append(high[0] - low[0])
    
    for i in range(1, len(close)):
        tr1 = high[i] - low[i]
        tr2 = abs(high[i] - close[i-1])
        tr3 = abs(low[i] - close[i-1])
        tr_list.append(max(tr1, tr2, tr3))
    
    tr = np.array(tr_list)
    atr = np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)
    
    return float(atr)

def calculate_supertrend(df, period=10, multiplier=3):
    """Calculate Supertrend indicator"""
    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values
    
    hl2 = (high + low) / 2
    atr = calculate_atr(df, period)
    
    basic_ub = hl2 + multiplier * atr
    basic_lb = hl2 - multiplier * atr
    
    final_ub = basic_ub[-1]
    final_lb = basic_lb[-1]
    
    return float(final_ub), float(final_lb), close[-1]

def calculate_vwap(df):
    """Calculate Volume Weighted Average Price"""
    high = df['High'].values
    low = df['Low'].values
    close = df['Close'].values
    volume = df['Volume'].values
    
    typical_price = (high + low + close) / 3
    cum_tp_vol = np.cumsum(typical_price * volume)
    cum_vol = np.cumsum(volume)
    
    vwap = cum_tp_vol[-1] / cum_vol[-1] if cum_vol[-1] > 0 else close[-1]
    
    return float(vwap)

def calculate_indicators(df):
    """Calculate all technical indicators for a stock"""
    if len(df) < 20:
        return None
    
    close_vals = df['Close'].values
    current_price = close_vals[-1]
    
    # Moving Averages
    ma20 = np.mean(close_vals[-20:]) if len(close_vals) >= 20 else None
    ma50 = np.mean(close_vals[-50:]) if len(close_vals) >= 50 else None
    
    # RSI
    deltas = np.diff(close_vals)
    seed = deltas[:14]
    up = np.sum(seed[seed >= 0]) / 14 if len(seed) > 0 else 0
    down = -np.sum(seed[seed < 0]) / 14 if len(seed) > 0 else 0
    
    if down != 0:
        rs = up / down
        rsi = 100 - (100 / (1 + rs))
    else:
        rsi = 50
    
    for delta in deltas[14:]:
        if delta > 0:
            up = (up * 13 + delta) / 14
            down = (down * 13) / 14
        else:
            up = (up * 13) / 14
            down = (down * 13 - delta) / 14
        rs = up / down if down != 0 else 0
        rsi = 100 - (100 / (1 + rs))
    
    # Returns
    ret_5d = ((current_price - close_vals[-6]) / close_vals[-6] * 100) if len(close_vals) >= 6 else 0
    ret_20d = ((current_price - close_vals[-21]) / close_vals[-21] * 100) if len(close_vals) >= 21 else 0
    
    # Volatility
    returns = np.diff(close_vals) / close_vals[:-1]
    volatility = np.std(returns) * np.sqrt(252) * 100 if len(returns) > 0 else 0
    
    # Volume
    volumes = df['Volume'].values
    current_vol = volumes[-1]
    avg_vol = np.mean(volumes[-20:])
    vol_trend = current_vol / avg_vol if avg_vol > 0 else 1
    
    # Market cap proxy
    market_cap_proxy = current_price * avg_vol
    
    # Supertrend
    st_up, st_down, price = calculate_supertrend(df)
    
    # VWAP
    vwap = calculate_vwap(df)
    
    return {
        'current_price': current_price,
        'ma20': ma20,
        'ma50': ma50,
        'rsi': rsi,
        'ret_5d': ret_5d,
        'ret_20d': ret_20d,
        'volatility': volatility,
        'vol_trend': vol_trend,
        'market_cap_proxy': market_cap_proxy,
        'open': float(df['Open'].values[-1]),
        'high': float(df['High'].values[-1]),
        'low': float(df['Low'].values[-1]),
        'st_upper': st_up,
        'st_lower': st_down,
        'vwap': vwap,
    }

def get_sentiment(indicators):
    """Determine bullish/bearish sentiment"""
    bullish_score = 0
    bearish_score = 0
    
    price = indicators['current_price']
    ma20 = indicators['ma20']
    ma50 = indicators['ma50']
    rsi = indicators['rsi']
    ret_20d = indicators['ret_20d']
    vol_trend = indicators.get('vol_trend', 1)
    vwap = indicators['vwap']
    st_lower = indicators['st_lower']
    st_upper = indicators['st_upper']
    
    # RSI signals
    if rsi < 30:
        bullish_score += 2
    elif rsi < 40:
        bullish_score += 1
    elif rsi > 70:
        bearish_score += 2
    elif rsi > 60:
        bearish_score += 1
    
    # Price vs MA signals
    if ma20 and price > ma20:
        bullish_score += 1
    elif ma20 and price < ma20:
        bearish_score += 1
    
    if ma50 and price > ma50:
        bullish_score += 1
    elif ma50 and price < ma50:
        bearish_score += 1
    
    # Return signals
    if ret_20d > 5:
        bullish_score += 1
    elif ret_20d < -5:
        bearish_score += 1
    
    # Volume signals
    if vol_trend > 1.5:
        bullish_score += 0.5
    
    # VWAP signals
    if price > vwap:
        bullish_score += 0.5
    else:
        bearish_score += 0.5
    
    # Supertrend signals
    if price > st_upper:
        bullish_score += 1
    elif price < st_lower:
        bearish_score += 1
    
    if bullish_score > bearish_score:
        return 'BULLISH', bullish_score, bearish_score
    elif bearish_score > bullish_score:
        return 'BEARISH', bullish_score, bearish_score
    else:
        return 'NEUTRAL', bullish_score, bearish_score


def get_fundamental_score(fund_data):
    """Score fundamental data and return (label, bull, bear)"""
    if not fund_data:
        return 'N/A', 0, 0

    def to_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    bull = 0
    bear = 0

    pe = to_float(fund_data.get('trailingPE'))
    if pe is not None:
        if 0 < pe <= 15:
            bull += 2
        elif 15 < pe <= 25:
            bull += 1
        elif pe > 40:
            bear += 1
        elif pe < 0:
            bear += 2

    eps = to_float(fund_data.get('trailingEps'))
    if eps is not None:
        if eps > 0:
            bull += 1
        elif eps < 0:
            bear += 1

    bv = to_float(fund_data.get('bookValue'))
    if bv is not None and bv > 0:
        bull += 0.5

    dy = to_float(fund_data.get('dividendYield'))
    if dy is not None:
        if dy > 0.03:
            bull += 1
        elif dy > 0.01:
            bull += 0.5

    roe = to_float(fund_data.get('returnOnEquity'))
    if roe is not None:
        if roe > 0.15:
            bull += 1.5
        elif roe > 0.10:
            bull += 0.5
        elif roe < 0.05:
            bear += 1

    pm = to_float(fund_data.get('profitMargins'))
    if pm is not None:
        if pm > 0.15:
            bull += 1
        elif pm > 0.08:
            bull += 0.5
        elif pm < 0:
            bear += 1

    de = to_float(fund_data.get('debtToEquity'))
    if de is not None:
        if de < 50:
            bull += 1
        elif de > 150:
            bear += 1
        elif de > 300:
            bear += 2

    revenue = to_float(fund_data.get('totalRevenue'))
    if revenue is not None and revenue > 0:
        bull += 0.5

    # Determine label
    if bull > bear + 2:
        label = 'STRONG'
    elif bull > bear:
        label = 'GOOD'
    elif bear > bull:
        label = 'WEAK'
    else:
        label = 'NEUTRAL'

    # If no data was scored at all
    has_any = any(fund_data.get(f) is not None for f in [
        'trailingPE', 'trailingEps', 'returnOnEquity', 'profitMargins', 'debtToEquity'
    ])
    if not has_any:
        return 'N/A', 0, 0

    return label, bull, bear


def get_overall_score(tech_bull, tech_bear, fund_bull, fund_bear, fund_label):
    """Combine technical and fundamental into overall score"""
    if fund_label == 'N/A':
        # Only technical available
        tech_max = 8
        net = (tech_bull - tech_bear) / tech_max  # -1 to +1
    else:
        tech_max = 8
        fund_max = 9
        tech_norm = (tech_bull - tech_bear) / tech_max  # -1 to +1
        fund_norm = (fund_bull - fund_bear) / fund_max
        net = 0.5 * tech_norm + 0.5 * fund_norm

    if net > 0.4:
        return 'STRONG BUY'
    elif net > 0.1:
        return 'BUY'
    elif net > -0.1:
        return 'HOLD'
    elif net > -0.4:
        return 'SELL'
    else:
        return 'STRONG SELL'


def analyze_all(market_data, fundamentals=None):
    """Analyze all stocks"""
    stocks_data = market_data['data']
    if fundamentals is None:
        fundamentals = {}
    results = []
    
    for idx, (symbol, df) in enumerate(stocks_data.items()):
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{len(stocks_data)}")
        
        ind = calculate_indicators(df)
        if not ind:
            continue
        
        if ind['market_cap_proxy'] <= 10000:
            continue
        
        sentiment, bull_score, bear_score = get_sentiment(ind)

        fund_data = fundamentals.get(symbol, {})
        fund_label, fund_bull, fund_bear = get_fundamental_score(fund_data)
        overall = get_overall_score(bull_score, bear_score, fund_bull, fund_bear, fund_label)
        
        results.append({
            'symbol': symbol,
            'sentiment': sentiment,
            'bullish_score': bull_score,
            'bearish_score': bear_score,
            'indicators': ind,
            'fund_data': fund_data if fund_data else {},
            'fund_score': fund_label,
            'fund_bull': fund_bull,
            'fund_bear': fund_bear,
            'overall_score': overall,
        })
    
    return results

def generate_html_table(results):
    """Generate comprehensive HTML report with table and filters"""
    
    html_parts = []
    html_parts.append('<!DOCTYPE html>')
    html_parts.append('<html><head>')
    html_parts.append('<meta charset="UTF-8">')
    html_parts.append('<title>Stock Analysis Report - Bullish/Bearish Indicators</title>')
    html_parts.append('<style>')
    html_parts.append('''
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #f5f5f5; 
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-box {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-box h3 { font-size: 0.9em; color: #667eea; margin-bottom: 10px; }
        .stat-box .value { font-size: 2em; font-weight: bold; }
        
        .table-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow-x: auto;
            overflow-y: visible;
            margin-bottom: 30px;
        }
        
        .filter-row {
            padding: 15px;
            background: #f9f9f9;
            border-bottom: 2px solid #eee;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .filter-input {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.85em;
            flex: 1;
            min-width: 150px;
        }
        
        .filter-input::placeholder { color: #999; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 3200px;
        }
        
        thead {
            background: #667eea;
            color: white;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.9em;
            border-right: 1px solid rgba(255,255,255,0.2);
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }
        
        th:hover { background: #5568d3; }
        th::after { content: ' ↕'; opacity: 0.5; font-size: 0.8em; }
        
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            font-size: 0.9em;
        }
        
        tr:hover { background: #f9f9f9; }
        tr:nth-child(even) { background: #fafafa; }
        
        .symbol { font-weight: 600; color: #667eea; font-family: monospace; }
        .positive { color: #4CAF50; font-weight: 500; }
        .negative { color: #f44336; font-weight: 500; }
        .neutral { color: #ff9800; font-weight: 500; }
        
        .bullish { background: #c8e6c9; color: #2e7d32; }
        .bearish { background: #ffcdd2; color: #c62828; }
        .neutral-bg { background: #ffe0b2; color: #e65100; }
        
        .num { text-align: right; font-family: 'Courier New', monospace; }
        
        .badge-strong-buy { background: #1b5e20; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        .badge-buy { background: #4CAF50; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        .badge-hold { background: #ff9800; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        .badge-sell { background: #f44336; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        .badge-strong-sell { background: #b71c1c; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        
        .badge-fund-strong { background: #1b5e20; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        .badge-fund-good { background: #66bb6a; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        .badge-fund-neutral { background: #ffa726; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        .badge-fund-weak { background: #ef5350; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        .badge-fund-na { background: #bdbdbd; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8em; }
        
        .na-val { color: #999; font-style: italic; }
        
        .hidden { display: none; }
        
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 0.9em;
            color: #1565c0;
        }
        
        .footer {
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 30px;
            padding: 20px;
            border-top: 1px solid #ddd;
        }
    ''')

    html_parts.append('</style>')
    html_parts.append('</head><body>')
    
    # Generate data for filters and sorting
    bullish_count = sum(1 for r in results if r['sentiment'] == 'BULLISH')
    bearish_count = sum(1 for r in results if r['sentiment'] == 'BEARISH')
    neutral_count = sum(1 for r in results if r['sentiment'] == 'NEUTRAL')
    strong_buy_count = sum(1 for r in results if r['overall_score'] == 'STRONG BUY')
    buy_count = sum(1 for r in results if r['overall_score'] == 'BUY')
    hold_count = sum(1 for r in results if r['overall_score'] == 'HOLD')
    sell_count = sum(1 for r in results if r['overall_score'] == 'SELL')
    strong_sell_count = sum(1 for r in results if r['overall_score'] == 'STRONG SELL')
    
    html_parts.append(f'''
    <div class="header">
        <h1>📊 Stock Analysis Report - Bullish & Bearish Indicators</h1>
        <p>Comprehensive Technical Analysis with Filtering and Sorting</p>
        <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now(IST).strftime('%d-%b-%Y %I:%M:%S %p IST')}</p>
        <p style="font-size: 0.85em; margin-top: 5px; opacity: 0.9;">AI Generated by Mangal</p>
    </div>
    
    <div class="summary">
        <div class="stat-box">
            <h3>Total Stocks</h3>
            <div class="value">{len(results)}</div>
        </div>
        <div class="stat-box">
            <h3>Bullish</h3>
            <div class="value positive">{bullish_count}</div>
        </div>
        <div class="stat-box">
            <h3>Bearish</h3>
            <div class="value negative">{bearish_count}</div>
        </div>
        <div class="stat-box">
            <h3>Neutral</h3>
            <div class="value neutral">{neutral_count}</div>
        </div>
        <div class="stat-box">
            <h3>Strong Buy</h3>
            <div class="value" style="color:#1b5e20">{strong_buy_count}</div>
        </div>
        <div class="stat-box">
            <h3>Buy</h3>
            <div class="value" style="color:#4CAF50">{buy_count}</div>
        </div>
        <div class="stat-box">
            <h3>Hold</h3>
            <div class="value" style="color:#ff9800">{hold_count}</div>
        </div>
        <div class="stat-box">
            <h3>Sell</h3>
            <div class="value" style="color:#f44336">{sell_count}</div>
        </div>
    </div>
    
    <div class="info-box">
        <strong>📌 Instructions:</strong> Click column headers to sort. Use filter boxes to search by column values.
        All prices in ₹. RSI scale: 0-100. Volatility in %. Market Cap Proxy = Price × Avg Volume.
    </div>
    
    <div class="table-container">
        <div class="filter-row">
            <input type="text" class="filter-input" id="filterSymbol" placeholder="Filter Symbol...">
            <input type="text" class="filter-input" id="filterSentiment" placeholder="Filter Sentiment (BULLISH/BEARISH/NEUTRAL)...">
            <input type="text" class="filter-input" id="filterRSI" placeholder="Filter RSI (e.g., >50, <30)...">
            <input type="text" class="filter-input" id="filterPrice" placeholder="Filter Price (e.g., >100, <500)...">
            <input type="text" class="filter-input" id="filterVol" placeholder="Filter Volume Trend (e.g., >1.5)...">
            <input type="text" class="filter-input" id="filterPE" placeholder="Filter PE (e.g., <25)...">
            <input type="text" class="filter-input" id="filterROE" placeholder="Filter ROE% (e.g., >15)...">
            <input type="text" class="filter-input" id="filterDE" placeholder="Filter D/E (e.g., <100)...">
            <input type="text" class="filter-input" id="filterOverall" placeholder="Filter Overall (STRONG BUY/BUY/HOLD/SELL)...">
            <button onclick="resetFilters()" style="padding: 8px 16px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500;">Reset Filters</button>
            <button id="refreshBtn" onclick="startRefresh()" style="padding: 8px 16px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500;">🔄 Refresh Data</button>
        </div>
        
        <!-- Progress Bar -->
        <div id="progressContainer" style="display: none; padding: 15px; background: #f0f7ff; border-bottom: 1px solid #ddd;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span id="progressLabel" style="font-weight: 600; color: #2196f3;">Loading...</span>
                <span id="progressPercent" style="color: #2196f3; font-weight: 600;">0%</span>
            </div>
            <div style="width: 100%; height: 24px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">
                <div id="progressBar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #2196f3, #4CAF50); transition: width 0.3s ease; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: bold;">0%</div>
            </div>
        </div>
        
        <table id="dataTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Symbol</th>
                    <th onclick="sortTable(1)" class="num">Sentiment</th>
                    <th onclick="sortTable(2)" class="num">Bull Score</th>
                    <th onclick="sortTable(3)" class="num">Bear Score</th>
                    <th onclick="sortTable(4)" class="num">Price</th>
                    <th onclick="sortTable(5)" class="num">MA20</th>
                    <th onclick="sortTable(6)" class="num">MA50</th>
                    <th onclick="sortTable(7)" class="num">RSI</th>
                    <th onclick="sortTable(8)" class="num">5D Return %</th>
                    <th onclick="sortTable(9)" class="num">20D Return %</th>
                    <th onclick="sortTable(10)" class="num">Volatility %</th>
                    <th onclick="sortTable(11)" class="num">Vol Trend</th>
                    <th onclick="sortTable(12)" class="num">VWAP</th>
                    <th onclick="sortTable(13)" class="num">ST Upper</th>
                    <th onclick="sortTable(14)" class="num">ST Lower</th>
                    <th onclick="sortTable(15)" class="num">Market Cap Proxy</th>
                    <th onclick="sortTable(16)" class="num">PE Ratio</th>
                    <th onclick="sortTable(17)" class="num">EPS</th>
                    <th onclick="sortTable(18)" class="num">ROE %</th>
                    <th onclick="sortTable(19)" class="num">D/E</th>
                    <th onclick="sortTable(20)" class="num">Div Yield %</th>
                    <th onclick="sortTable(21)" class="num">Profit Margin %</th>
                    <th onclick="sortTable(22)" class="num">Fund Score</th>
                    <th onclick="sortTable(23)" class="num">Overall</th>
                </tr>
            </thead>
            <tbody id="tableBody">
    ''')
    
    for stock in sorted(results, key=lambda x: ({'STRONG BUY': 0, 'BUY': 1, 'HOLD': 2, 'SELL': 3, 'STRONG SELL': 4}.get(x['overall_score'], 2), x['sentiment'] != 'BULLISH', -x['bullish_score'])):
        ind = stock['indicators']
        sent_class = stock['sentiment'].lower()
        fd = stock.get('fund_data', {})
        
        # Pre-calculate formatted values to avoid f-string issues
        ma20_val = f"₹{ind['ma20']:.2f}" if ind['ma20'] else 'N/A'
        ma50_val = f"₹{ind['ma50']:.2f}" if ind['ma50'] else 'N/A'
        ret5_class = 'positive' if ind['ret_5d'] >= 0 else 'negative'
        ret20_class = 'positive' if ind['ret_20d'] >= 0 else 'negative'

        # Fundamental values - safe float conversion for yfinance data
        def _ff(v):
            if v is None: return None
            try: return float(v)
            except (ValueError, TypeError): return None

        _pe = _ff(fd.get('trailingPE'))
        _eps = _ff(fd.get('trailingEps'))
        _roe = _ff(fd.get('returnOnEquity'))
        _de = _ff(fd.get('debtToEquity'))
        _dy = _ff(fd.get('dividendYield'))
        _pm = _ff(fd.get('profitMargins'))

        pe_val = f"{_pe:.1f}" if _pe is not None else 'N/A'
        eps_val = f"₹{_eps:.2f}" if _eps is not None else 'N/A'
        roe_val = f"{_roe*100:.1f}" if _roe is not None else 'N/A'
        de_val = f"{_de:.1f}" if _de is not None else 'N/A'
        dy_val = f"{_dy*100:.2f}" if _dy is not None else 'N/A'
        pm_val = f"{_pm*100:.1f}" if _pm is not None else 'N/A'

        pe_class = 'na-val' if _pe is None else ''
        eps_class = 'na-val' if _eps is None else ('positive' if _eps > 0 else 'negative')
        roe_class = 'na-val' if _roe is None else ('positive' if _roe > 0.10 else '')
        de_class = 'na-val' if _de is None else ''
        dy_class = 'na-val' if _dy is None else ''
        pm_class = 'na-val' if _pm is None else ('positive' if _pm > 0 else 'negative')

        # Fund score badge
        fs = stock['fund_score']
        fund_badge_class = {'STRONG': 'badge-fund-strong', 'GOOD': 'badge-fund-good', 'NEUTRAL': 'badge-fund-neutral', 'WEAK': 'badge-fund-weak'}.get(fs, 'badge-fund-na')

        # Overall badge
        ov = stock['overall_score']
        overall_badge_class = {'STRONG BUY': 'badge-strong-buy', 'BUY': 'badge-buy', 'HOLD': 'badge-hold', 'SELL': 'badge-sell', 'STRONG SELL': 'badge-strong-sell'}.get(ov, 'badge-hold')
        
        html_parts.append(f'''
                <tr class="data-row">
                    <td class="symbol">{stock['symbol']}</td>
                    <td class="num {sent_class}">{stock['sentiment']}</td>
                    <td class="num positive">{stock['bullish_score']:.1f}</td>
                    <td class="num negative">{stock['bearish_score']:.1f}</td>
                    <td class="num">₹{ind['current_price']:.2f}</td>
                    <td class="num">{ma20_val}</td>
                    <td class="num">{ma50_val}</td>
                    <td class="num">{ind['rsi']:.1f}</td>
                    <td class="num {ret5_class}">{ind['ret_5d']:.2f}%</td>
                    <td class="num {ret20_class}">{ind['ret_20d']:.2f}%</td>
                    <td class="num">{ind['volatility']:.2f}%</td>
                    <td class="num">{ind['vol_trend']:.2f}x</td>
                    <td class="num">₹{ind['vwap']:.2f}</td>
                    <td class="num">₹{ind['st_upper']:.2f}</td>
                    <td class="num">₹{ind['st_lower']:.2f}</td>
                    <td class="num">{ind['market_cap_proxy']:.0f}</td>
                    <td class="num {pe_class}">{pe_val}</td>
                    <td class="num {eps_class}">{eps_val}</td>
                    <td class="num {roe_class}">{roe_val}</td>
                    <td class="num {de_class}">{de_val}</td>
                    <td class="num {dy_class}">{dy_val}</td>
                    <td class="num {pm_class}">{pm_val}</td>
                    <td class="num"><span class="{fund_badge_class}">{fs}</span></td>
                    <td class="num"><span class="{overall_badge_class}">{ov}</span></td>
                </tr>
        ''')
    
    html_parts.append('''
            </tbody>
        </table>
    </div>
    
    <div class="footer">
        <p><strong>Indicators Explained:</strong></p>
        <p>RSI (Relative Strength Index) • MA (Moving Averages) • VWAP (Volume Weighted Average Price) • ST (Supertrend)</p>
        <p>Bull/Bear Score indicates the strength of bullish/bearish signals detected by the system.</p>
    </div>
    
    <script>
        let allRows = [];
        let sortColumn = 0;
        let sortAscending = true;
        
        document.addEventListener('DOMContentLoaded', function() {
            allRows = Array.from(document.querySelectorAll('.data-row'));
            
            // Set up filter listeners
            document.getElementById('filterSymbol').addEventListener('keyup', applyFilters);
            document.getElementById('filterSentiment').addEventListener('keyup', applyFilters);
            document.getElementById('filterRSI').addEventListener('keyup', applyFilters);
            document.getElementById('filterPrice').addEventListener('keyup', applyFilters);
            document.getElementById('filterVol').addEventListener('keyup', applyFilters);
            document.getElementById('filterPE').addEventListener('keyup', applyFilters);
            document.getElementById('filterROE').addEventListener('keyup', applyFilters);
            document.getElementById('filterDE').addEventListener('keyup', applyFilters);
            document.getElementById('filterOverall').addEventListener('keyup', applyFilters);
        });
        
        function applyFilters() {
            const filterSymbol = document.getElementById('filterSymbol').value.toUpperCase();
            const filterSentiment = document.getElementById('filterSentiment').value.toUpperCase();
            const filterRSI = document.getElementById('filterRSI').value;
            const filterPrice = document.getElementById('filterPrice').value;
            const filterVol = document.getElementById('filterVol').value;
            const filterPE = document.getElementById('filterPE').value;
            const filterROE = document.getElementById('filterROE').value;
            const filterDE = document.getElementById('filterDE').value;
            const filterOverall = document.getElementById('filterOverall').value.toUpperCase();
            
            function numericFilter(cellText, filterVal) {
                const num = parseFloat(cellText.replace(/[^0-9.-]/g, ''));
                if (cellText.trim() === 'N/A' || isNaN(num)) return false;
                if (filterVal.includes('>')) {
                    const val = parseFloat(filterVal.substring(1));
                    return num > val;
                } else if (filterVal.includes('<')) {
                    const val = parseFloat(filterVal.substring(1));
                    return num < val;
                }
                return true;
            }
            
            let visibleCount = 0;
            
            allRows.forEach(row => {
                let show = true;
                
                if (filterSymbol && !row.cells[0].textContent.includes(filterSymbol)) show = false;
                if (show && filterSentiment && !row.cells[1].textContent.includes(filterSentiment)) show = false;
                if (show && filterRSI && !numericFilter(row.cells[7].textContent, filterRSI)) show = false;
                if (show && filterPrice && !numericFilter(row.cells[4].textContent, filterPrice)) show = false;
                if (show && filterVol && !numericFilter(row.cells[11].textContent, filterVol)) show = false;
                if (show && filterPE && !numericFilter(row.cells[16].textContent, filterPE)) show = false;
                if (show && filterROE && !numericFilter(row.cells[18].textContent, filterROE)) show = false;
                if (show && filterDE && !numericFilter(row.cells[19].textContent, filterDE)) show = false;
                if (show && filterOverall && !row.cells[23].textContent.toUpperCase().includes(filterOverall)) show = false;
                
                row.style.display = show ? '' : 'none';
                if (show) visibleCount++;
            });
            
            document.title = 'Stocks: ' + visibleCount + '/' + allRows.length;
        }
        
        function sortTable(columnIndex) {
            if (sortColumn === columnIndex) {
                sortAscending = !sortAscending;
            } else {
                sortColumn = columnIndex;
                sortAscending = true;
            }
            
            const tableBody = document.getElementById('tableBody');
            const rows = Array.from(tableBody.querySelectorAll('tr'));
            
            rows.sort((a, b) => {
                let aVal = a.cells[columnIndex].textContent.trim();
                let bVal = b.cells[columnIndex].textContent.trim();
                
                // N/A always sorts to bottom
                const aNA = aVal === 'N/A';
                const bNA = bVal === 'N/A';
                if (aNA && bNA) return 0;
                if (aNA) return 1;
                if (bNA) return -1;
                
                // Try numeric comparison
                const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return sortAscending ? aNum - bNum : bNum - aNum;
                }
                
                // Text comparison
                return sortAscending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            });
            
            tableBody.innerHTML = '';
            rows.forEach(row => tableBody.appendChild(row));
            applyFilters();
        }
        
        function resetFilters() {
            document.getElementById('filterSymbol').value = '';
            document.getElementById('filterSentiment').value = '';
            document.getElementById('filterRSI').value = '';
            document.getElementById('filterPrice').value = '';
            document.getElementById('filterVol').value = '';
            document.getElementById('filterPE').value = '';
            document.getElementById('filterROE').value = '';
            document.getElementById('filterDE').value = '';
            document.getElementById('filterOverall').value = '';
            applyFilters();
        }
        
        // Refresh Data functionality
        const isStaticHost = location.hostname.includes('github.io') || location.protocol === 'file:';
        const GITHUB_OWNER = 'MangalParan';
        const GITHUB_REPO = 'stock_report';
        const WORKFLOW_FILE = 'refresh-stock-data.yml';
        let refreshInProgress = false;

        function getGitHubToken() {
            return localStorage.getItem('gh_pat') || '';
        }

        function promptForToken() {
            const token = prompt(
                'Enter your GitHub Personal Access Token (PAT) with "Actions: write" permission.\\n\\n' +
                'Create one at: https://github.com/settings/tokens?type=beta\\n' +
                'Select repo: ' + GITHUB_OWNER + '/' + GITHUB_REPO + '\\n' +
                'Permission needed: Actions → Read and write\\n\\n' +
                'The token is stored only in your browser (localStorage).'
            );
            if (token && token.trim()) {
                localStorage.setItem('gh_pat', token.trim());
                return token.trim();
            }
            return null;
        }

        async function triggerWorkflow(token) {
            const url = 'https://api.github.com/repos/' + GITHUB_OWNER + '/' + GITHUB_REPO + '/actions/workflows/' + WORKFLOW_FILE + '/dispatches';
            const resp = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Accept': 'application/vnd.github+json'
                },
                body: JSON.stringify({ ref: 'main' })
            });
            if (resp.status === 204) return true;
            if (resp.status === 401 || resp.status === 403) {
                localStorage.removeItem('gh_pat');
                throw new Error('Invalid or expired token. Please try again.');
            }
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.message || 'Failed to trigger workflow (HTTP ' + resp.status + ')');
        }

        async function waitForNewRun(token, triggerTime) {
            const listUrl = 'https://api.github.com/repos/' + GITHUB_OWNER + '/' + GITHUB_REPO + '/actions/workflows/' + WORKFLOW_FILE + '/runs?per_page=5';
            const headers = { 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json' };
            for (let i = 0; i < 30; i++) {
                await new Promise(r => setTimeout(r, 3000));
                const resp = await fetch(listUrl, { headers });
                if (!resp.ok) continue;
                const data = await resp.json();
                const runs = data.workflow_runs || [];
                const newRun = runs.find(r => new Date(r.created_at).getTime() >= triggerTime);
                if (newRun) return newRun.id;
                showProgress(5, 'processing', 'Waiting for workflow to start...');
            }
            throw new Error('Workflow did not start. Check GitHub Actions.');
        }

        async function pollRunProgress(token, runId) {
            const runUrl = 'https://api.github.com/repos/' + GITHUB_OWNER + '/' + GITHUB_REPO + '/actions/runs/' + runId;
            const jobsUrl = runUrl + '/jobs';
            const headers = { 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json' };
            for (let i = 0; i < 180; i++) {
                const resp = await fetch(runUrl, { headers });
                if (!resp.ok) throw new Error('Failed to check run status');
                const run = await resp.json();
                if (run.status === 'completed') {
                    if (run.conclusion === 'success') return;
                    throw new Error('Workflow failed: ' + run.conclusion);
                }
                let pct = 10;
                let msg = 'Workflow ' + run.status + '...';
                try {
                    const jResp = await fetch(jobsUrl, { headers });
                    if (jResp.ok) {
                        const jData = await jResp.json();
                        const job = jData.jobs && jData.jobs[0];
                        if (job && job.steps && job.steps.length) {
                            const total = job.steps.length;
                            const done = job.steps.filter(s => s.status === 'completed').length;
                            const current = job.steps.find(s => s.status === 'in_progress');
                            pct = Math.min(95, Math.round((done / total) * 100));
                            if (current) msg = '\u2699\ufe0f ' + current.name;
                        }
                    }
                } catch (e) { /* use defaults */ }
                showProgress(pct, 'processing', msg);
                await new Promise(r => setTimeout(r, 5000));
            }
            throw new Error('Workflow timed out');
        }

        async function startRefresh() {
            if (!isStaticHost) {
                // Local server mode
                if (refreshInProgress) return;
                refreshInProgress = true;
                const refreshBtn = document.getElementById('refreshBtn');
                const progressContainer = document.getElementById('progressContainer');
                refreshBtn.disabled = true;
                refreshBtn.style.opacity = '0.6';
                progressContainer.style.display = 'block';
                try {
                    const response = await fetch('/refresh-data', {method: 'POST'});
                    const result = await response.json();
                    if (result.status !== 'success') {
                        showProgress(0, 'error', 'Error: ' + result.message);
                        refreshInProgress = false;
                        return;
                    }
                    await trackLocalProgress();
                } catch (error) {
                    showProgress(0, 'error', 'Failed to start refresh: ' + error.message);
                } finally {
                    refreshBtn.disabled = false;
                    refreshBtn.style.opacity = '1';
                    refreshInProgress = false;
                }
                return;
            }

            // GitHub Pages mode
            if (refreshInProgress) return;
            let token = getGitHubToken();
            if (!token) { token = promptForToken(); if (!token) return; }

            refreshInProgress = true;
            const refreshBtn = document.getElementById('refreshBtn');
            const progressContainer = document.getElementById('progressContainer');
            refreshBtn.disabled = true;
            refreshBtn.style.opacity = '0.6';
            progressContainer.style.display = 'block';
            showProgress(0, 'processing', 'Triggering data refresh workflow...');

            try {
                const triggerTime = Date.now() - 30000;
                await triggerWorkflow(token);
                showProgress(5, 'processing', 'Workflow dispatched. Waiting for run to start...');
                const runId = await waitForNewRun(token, triggerTime);
                showProgress(10, 'processing', 'Workflow started. Tracking progress...');
                await pollRunProgress(token, runId);
                showProgress(100, 'completed', 'Refresh complete! Reloading page...');
                setTimeout(() => { window.location.href = window.location.pathname + '?t=' + Date.now(); }, 3000);
            } catch (error) {
                showProgress(0, 'error', 'Error: ' + error.message);
                refreshBtn.disabled = false;
                refreshBtn.style.opacity = '1';
                refreshInProgress = false;
            }
        }
        
        async function trackLocalProgress() {
            const maxAttempts = 300;
            let attempts = 0;
            
            while (attempts < maxAttempts) {
                try {
                    const response = await fetch('/progress');
                    const progress = await response.json();
                    
                    const pct = progress.percentage || 0;
                    showProgress(pct, progress.status || 'processing', progress.message || '');
                    
                    if (progress.status === 'completed' || progress.status === 'error') {
                        if (progress.status === 'completed') {
                            setTimeout(() => {
                                location.reload();
                            }, 2000);
                        }
                        return;
                    }
                    
                    await new Promise(resolve => setTimeout(resolve, 500));
                    attempts++;
                    
                } catch (error) {
                    console.error('Error tracking progress:', error);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    attempts++;
                }
            }
            
            showProgress(0, 'error', 'Update timeout - please check server');
        }
        
        function showProgress(percentage, status, message) {
            const progressPercent = document.getElementById('progressPercent');
            const progressBar = document.getElementById('progressBar');
            const progressLabel = document.getElementById('progressLabel');
            
            progressPercent.textContent = percentage + '%';
            progressBar.style.width = percentage + '%';
            progressBar.textContent = percentage > 10 ? percentage + '%' : '';
            
            let label = message || status;
            if (status === 'downloading') label = '📥 ' + label;
            else if (status === 'saving') label = '💾 ' + label;
            else if (status === 'generating_report') label = '📊 ' + label;
            else if (status === 'completed') label = '✅ ' + label;
            else if (status === 'error') label = '❌ ' + label;
            
            progressLabel.textContent = label;
            
            if (status === 'error') {
                document.getElementById('progressContainer').style.background = '#ffebee';
                progressBar.style.background = '#f44336';
                progressPercent.style.color = '#f44336';
                progressLabel.style.color = '#f44336';
            } else if (status === 'completed') {
                document.getElementById('progressContainer').style.background = '#e8f5e9';
                progressBar.style.background = '#4CAF50';
            }
        }
    </script>
    ''')
    
    html_parts.append('</body></html>')
    
    return '\n'.join(html_parts)

def main():
    print("\n" + "="*70)
    print("COMPREHENSIVE STOCK ANALYSIS - TABLE REPORT WITH FILTERS")
    print("="*70)
    
    print("\nLoading market data...")
    with open('market_data.pkl', 'rb') as f:
        market_data = pickle.load(f)
    
    fundamentals = market_data.get('fundamentals', {})
    print(f"Analyzing {len(market_data['data'])} stocks (fundamentals available for {len(fundamentals)})...")
    results = analyze_all(market_data, fundamentals)
    
    print(f"\nStocks analyzed: {len(results)}")
    bullish = sum(1 for r in results if r['sentiment'] == 'BULLISH')
    bearish = sum(1 for r in results if r['sentiment'] == 'BEARISH')
    print(f"  Bullish: {bullish}")
    print(f"  Bearish: {bearish}")
    
    print("\nGenerating comprehensive table report...")
    html = generate_html_table(results)
    
    with open('stock_analysis_table_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("[OK] Saved: stock_analysis_table_report.html")
    
    # Save JSON with all data
    strong_buy = sum(1 for r in results if r['overall_score'] == 'STRONG BUY')
    buy = sum(1 for r in results if r['overall_score'] == 'BUY')
    hold = sum(1 for r in results if r['overall_score'] == 'HOLD')
    sell = sum(1 for r in results if r['overall_score'] == 'SELL')
    strong_sell = sum(1 for r in results if r['overall_score'] == 'STRONG SELL')

    json_data = {
        'timestamp': datetime.now(IST).strftime('%d-%b-%Y %I:%M:%S %p IST'),
        'total_analyzed': len(results),
        'bullish_count': bullish,
        'bearish_count': bearish,
        'overall_counts': {
            'strong_buy': strong_buy,
            'buy': buy,
            'hold': hold,
            'sell': sell,
            'strong_sell': strong_sell,
        },
        'stocks': [
            {
                'symbol': r['symbol'],
                'sentiment': r['sentiment'],
                'bullish_score': r['bullish_score'],
                'bearish_score': r['bearish_score'],
                'price': r['indicators']['current_price'],
                'ma20': r['indicators']['ma20'],
                'ma50': r['indicators']['ma50'],
                'rsi': r['indicators']['rsi'],
                'ret_5d': r['indicators']['ret_5d'],
                'ret_20d': r['indicators']['ret_20d'],
                'volatility': r['indicators']['volatility'],
                'vol_trend': r['indicators']['vol_trend'],
                'vwap': r['indicators']['vwap'],
                'st_upper': r['indicators']['st_upper'],
                'st_lower': r['indicators']['st_lower'],
                'market_cap_proxy': r['indicators']['market_cap_proxy'],
                'pe': r.get('fund_data', {}).get('trailingPE'),
                'eps': r.get('fund_data', {}).get('trailingEps'),
                'roe': r.get('fund_data', {}).get('returnOnEquity'),
                'debt_to_equity': r.get('fund_data', {}).get('debtToEquity'),
                'dividend_yield': r.get('fund_data', {}).get('dividendYield'),
                'profit_margin': r.get('fund_data', {}).get('profitMargins'),
                'fund_score': r['fund_score'],
                'overall_score': r['overall_score'],
            }
            for r in results
        ]
    }
    
    with open('stock_analysis_table_report.json', 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print("[OK] Saved: stock_analysis_table_report.json")
    print("\n" + "="*70)
    print("REPORT COMPLETE")
    print("="*70)
    print(f"Features:")
    print(f"  [OK] All {len(results)} stocks in interactive table")
    print(f"  [OK] 24 columns with technical + fundamental indicators")
    print(f"  [OK] Real-time filtering on 9 key columns")
    print(f"  [OK] Click headers to sort any column")
    print(f"  [OK] Technical Score + Fundamental Score + Overall Score")
    print(f"  [OK] Supertrend (Upper/Lower Bands)")
    print(f"  [OK] VWAP (Volume Weighted Average Price)")
    print(f"  [OK] Responsive design")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
