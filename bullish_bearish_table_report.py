#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Bullish/Bearish Analysis with Table Format, Filters, and Advanced Indicators
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import json

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

def analyze_all(market_data):
    """Analyze all stocks"""
    stocks_data = market_data['data']
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
        
        results.append({
            'symbol': symbol,
            'sentiment': sentiment,
            'bullish_score': bull_score,
            'bearish_score': bear_score,
            'indicators': ind,
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
            min-width: 2000px;
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
    
    html_parts.append(f'''
    <div class="header">
        <h1>📊 Stock Analysis Report - Bullish & Bearish Indicators</h1>
        <p>Comprehensive Technical Analysis with Filtering and Sorting</p>
        <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
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
                </tr>
            </thead>
            <tbody id="tableBody">
    ''')
    
    for stock in sorted(results, key=lambda x: (x['sentiment'] != 'BULLISH', -x['bullish_score'])):
        ind = stock['indicators']
        sent_class = stock['sentiment'].lower()
        
        # Pre-calculate formatted values to avoid f-string issues
        ma20_val = f"₹{ind['ma20']:.2f}" if ind['ma20'] else 'N/A'
        ma50_val = f"₹{ind['ma50']:.2f}" if ind['ma50'] else 'N/A'
        ret5_class = 'positive' if ind['ret_5d'] >= 0 else 'negative'
        ret20_class = 'positive' if ind['ret_20d'] >= 0 else 'negative'
        
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
        });
        
        function applyFilters() {
            const filterSymbol = document.getElementById('filterSymbol').value.toUpperCase();
            const filterSentiment = document.getElementById('filterSentiment').value.toUpperCase();
            const filterRSI = document.getElementById('filterRSI').value;
            const filterPrice = document.getElementById('filterPrice').value;
            const filterVol = document.getElementById('filterVol').value;
            
            let visibleCount = 0;
            
            allRows.forEach(row => {
                let show = true;
                
                // Symbol filter
                if (filterSymbol && !row.cells[0].textContent.includes(filterSymbol)) {
                    show = false;
                }
                
                // Sentiment filter
                if (show && filterSentiment && !row.cells[1].textContent.includes(filterSentiment)) {
                    show = false;
                }
                
                // RSI filter
                if (show && filterRSI) {
                    const rsi = parseFloat(row.cells[7].textContent);
                    if (filterRSI.includes('>')) {
                        const val = parseFloat(filterRSI.substring(1));
                        if (!(rsi > val)) show = false;
                    } else if (filterRSI.includes('<')) {
                        const val = parseFloat(filterRSI.substring(1));
                        if (!(rsi < val)) show = false;
                    }
                }
                
                // Price filter
                if (show && filterPrice) {
                    const price = parseFloat(row.cells[4].textContent);
                    if (filterPrice.includes('>')) {
                        const val = parseFloat(filterPrice.substring(1));
                        if (!(price > val)) show = false;
                    } else if (filterPrice.includes('<')) {
                        const val = parseFloat(filterPrice.substring(1));
                        if (!(price < val)) show = false;
                    }
                }
                
                // Volume trend filter
                if (show && filterVol) {
                    const vol = parseFloat(row.cells[11].textContent);
                    if (filterVol.includes('>')) {
                        const val = parseFloat(filterVol.substring(1));
                        if (!(vol > val)) show = false;
                    } else if (filterVol.includes('<')) {
                        const val = parseFloat(filterVol.substring(1));
                        if (!(vol < val)) show = false;
                    }
                }
                
                row.style.display = show ? '' : 'none';
                if (show) visibleCount++;
            });
            
            document.title = `Stocks: ${visibleCount}/${allRows.length}`;
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
            applyFilters();
        }
        
        // Refresh Data functionality
        const isStaticHost = location.hostname.includes('github.io') || location.protocol === 'file:';
        const GITHUB_OWNER = 'MangalParan';
        const GITHUB_REPO = 'stock_report';
        const WORKFLOW_FILE = 'refresh-stock-data.yml';
        let refreshInProgress = false;

        function getGitHubToken() {{
            return localStorage.getItem('gh_pat') || '';
        }}

        function promptForToken() {{
            const token = prompt(
                'Enter your GitHub Personal Access Token (PAT) with "Actions: write" permission.\\n\\n' +
                'Create one at: https://github.com/settings/tokens?type=beta\\n' +
                'Select repo: ' + GITHUB_OWNER + '/' + GITHUB_REPO + '\\n' +
                'Permission needed: Actions → Read and write\\n\\n' +
                'The token is stored only in your browser (localStorage).'
            );
            if (token && token.trim()) {{
                localStorage.setItem('gh_pat', token.trim());
                return token.trim();
            }}
            return null;
        }}

        async function triggerWorkflow(token) {{
            const url = 'https://api.github.com/repos/' + GITHUB_OWNER + '/' + GITHUB_REPO + '/actions/workflows/' + WORKFLOW_FILE + '/dispatches';
            const resp = await fetch(url, {{
                method: 'POST',
                headers: {{
                    'Authorization': 'Bearer ' + token,
                    'Accept': 'application/vnd.github+json'
                }},
                body: JSON.stringify({{ ref: 'main' }})
            }});
            if (resp.status === 204) return true;
            if (resp.status === 401 || resp.status === 403) {{
                localStorage.removeItem('gh_pat');
                throw new Error('Invalid or expired token. Please try again.');
            }}
            const err = await resp.json().catch(() => ({{}}));
            throw new Error(err.message || 'Failed to trigger workflow (HTTP ' + resp.status + ')');
        }}

        async function pollWorkflowRun(token) {{
            const listUrl = 'https://api.github.com/repos/' + GITHUB_OWNER + '/' + GITHUB_REPO + '/actions/workflows/' + WORKFLOW_FILE + '/runs?per_page=1';
            const headers = {{ 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json' }};
            await new Promise(r => setTimeout(r, 4000));
            for (let i = 0; i < 120; i++) {{
                const resp = await fetch(listUrl, {{ headers }});
                if (!resp.ok) throw new Error('Failed to check workflow status');
                const data = await resp.json();
                const run = data.workflow_runs && data.workflow_runs[0];
                if (!run) {{ await new Promise(r => setTimeout(r, 5000)); continue; }}
                if (run.status === 'completed') {{
                    if (run.conclusion === 'success') return 'success';
                    throw new Error('Workflow finished with: ' + run.conclusion);
                }}
                let pct = run.status === 'in_progress' ? 50 : 5;
                showProgress(pct, 'processing', 'Workflow ' + run.status + '...');
                await new Promise(r => setTimeout(r, 5000));
            }}
            throw new Error('Workflow timed out');
        }}

        async function startRefresh() {{
            if (!isStaticHost) {{
                // Local server mode
                if (refreshInProgress) return;
                refreshInProgress = true;
                const refreshBtn = document.getElementById('refreshBtn');
                const progressContainer = document.getElementById('progressContainer');
                refreshBtn.disabled = true;
                refreshBtn.style.opacity = '0.6';
                progressContainer.style.display = 'block';
                try {{
                    const response = await fetch('/refresh-data', {{method: 'POST'}});
                    const result = await response.json();
                    if (result.status !== 'success') {{
                        showProgress(0, 'error', 'Error: ' + result.message);
                        refreshInProgress = false;
                        return;
                    }}
                    await trackLocalProgress();
                }} catch (error) {{
                    showProgress(0, 'error', 'Failed to start refresh: ' + error.message);
                }} finally {{
                    refreshBtn.disabled = false;
                    refreshBtn.style.opacity = '1';
                    refreshInProgress = false;
                }}
                return;
            }}

            // GitHub Pages mode
            if (refreshInProgress) return;
            let token = getGitHubToken();
            if (!token) {{ token = promptForToken(); if (!token) return; }}

            refreshInProgress = true;
            const refreshBtn = document.getElementById('refreshBtn');
            const progressContainer = document.getElementById('progressContainer');
            refreshBtn.disabled = true;
            refreshBtn.style.opacity = '0.6';
            progressContainer.style.display = 'block';
            showProgress(0, 'processing', 'Triggering data refresh workflow...');

            try {{
                await triggerWorkflow(token);
                showProgress(10, 'processing', 'Workflow triggered. Waiting for completion...');
                await pollWorkflowRun(token);
                showProgress(100, 'completed', 'Refresh complete! Reloading page...');
                setTimeout(() => {{ window.location.href = window.location.pathname + '?t=' + Date.now(); }}, 3000);
            }} catch (error) {{
                showProgress(0, 'error', 'Error: ' + error.message);
                refreshBtn.disabled = false;
                refreshBtn.style.opacity = '1';
                refreshInProgress = false;
            }}
        }}
        
        async function trackLocalProgress() {{
            const maxAttempts = 300;
            let attempts = 0;
            
            while (attempts < maxAttempts) {{
                try {{
                    const response = await fetch('/progress');
                    const progress = await response.json();
                    
                    const pct = progress.percentage || 0;
                    showProgress(pct, progress.status || 'processing', progress.message || '');
                    
                    if (progress.status === 'completed' || progress.status === 'error') {{
                        if (progress.status === 'completed') {{
                            setTimeout(() => {{
                                location.reload();
                            }}, 2000);
                        }}
                        return;
                    }}
                    
                    await new Promise(resolve => setTimeout(resolve, 500));
                    attempts++;
                    
                }} catch (error) {{
                    console.error('Error tracking progress:', error);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    attempts++;
                }}
            }}
            
            showProgress(0, 'error', 'Update timeout - please check server');
        }}
        
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
    
    print(f"Analyzing {len(market_data['data'])} stocks...")
    results = analyze_all(market_data)
    
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
    json_data = {
        'timestamp': market_data['timestamp'].isoformat(),
        'total_analyzed': len(results),
        'bullish_count': bullish,
        'bearish_count': bearish,
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
    print(f"  [OK] 16 columns with complete indicators")
    print(f"  [OK] Real-time filtering on 5 key columns")
    print(f"  [OK] Click headers to sort any column")
    print(f"  [OK] Supertrend (Upper/Lower Bands)")
    print(f"  [OK] VWAP (Volume Weighted Average Price)")
    print(f"  [OK] Responsive design")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
