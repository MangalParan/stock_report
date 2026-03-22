#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Commodity Bullish/Bearish Analysis Report Generator
Calculates technical indicators for commodity futures and generates sentiment analysis
Reads from commodity_market_data.pkl and outputs JSON + HTML report
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

def calculate_atr(df, period=14):
    """Calculate Average True Range for volatility"""
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
    
    final_ub = basic_ub
    final_lb = basic_lb
    
    supertrend = np.zeros_like(close)
    
    for i in range(1, len(close)):
        if i > 0:
            if final_lb[i-1] > final_lb[i]:
                final_lb = np.append(final_lb[:i], basic_lb[i:])
        
        if close[-1] <= basic_ub[-1]:
            supertrend[-1] = basic_ub[-1]
        else:
            supertrend[-1] = basic_lb[-1]
    
    return float(supertrend[-1]) if len(supertrend) > 0 else close[-1]

def calculate_rsi(df, period=14):
    """Calculate Relative Strength Index"""
    close = df['Close'].values
    
    deltas = np.diff(close)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    
    rs = up / down if down != 0 else 0
    rsi = 100. - 100. / (1. + rs)
    
    for d in deltas[period+1:]:
        if d > 0:
            up = (up * (period - 1) + d) / period
            down = (down * (period - 1)) / period
        else:
            up = (up * (period - 1)) / period
            down = (down * (period - 1) - d) / period
        
        rs = up / down if down != 0 else 0
        rsi = np.append(rsi, 100. - 100. / (1. + rs))
    
    return float(rsi[-1]) if len(rsi) > 0 else 50.0

def calculate_ma(df, period):
    """Calculate Simple Moving Average"""
    return float(df['Close'].tail(period).mean())

def calculate_vwap(df):
    """Calculate Volume-Weighted Average Price"""
    if 'Volume' not in df.columns or df['Volume'].sum() == 0:
        return float(df['Close'].iloc[-1])
    
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (tp * df['Volume']).sum() / df['Volume'].sum()
    return float(vwap)

def calculate_bollinger_bands(df, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    close = df['Close']
    sma = close.tail(period).mean()
    std = close.tail(period).std()
    
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    
    return {
        'upper': float(upper_band),
        'middle': float(sma),
        'lower': float(lower_band)
    }

def calculate_commodity_sentiment(row):
    """Calculate bullish/bearish sentiment for commodity"""
    bullish_score = 0
    bearish_score = 0
    
    close = row.get('Close', 0)
    rsi = row.get('RSI', 50)
    ma20 = row.get('MA20', close)
    ma50 = row.get('MA50', close)
    atr = row.get('ATR', 0)
    vwap = row.get('VWAP', close)
    return_5d = row.get('Return_5D', 0)
    return_20d = row.get('Return_20D', 0)
    volume_ratio = row.get('Volume_Ratio', 1.0)
    
    if rsi < 35:
        bullish_score += 3
    elif rsi > 65:
        bearish_score += 2
    
    if close > ma20 and ma20 > ma50:
        bullish_score += 2
    elif close < ma20 and ma20 < ma50:
        bearish_score += 2
    
    if close > vwap:
        bullish_score += 1
    else:
        bearish_score += 1
    
    if return_5d > 2:
        bullish_score += 1
    elif return_5d < -2:
        bearish_score += 1
    
    if return_20d > 3:
        bullish_score += 1
    elif return_20d < -3:
        bearish_score += 1
    
    if volume_ratio > 1.5:
        bullish_score += 1
    
    if atr > close * 0.05:
        bullish_score += 0
        bearish_score += 0
    
    total = bullish_score + bearish_score
    sentiment = "BULLISH" if bullish_score > bearish_score else "BEARISH" if bearish_score > bullish_score else "NEUTRAL"
    
    return {
        'bullish_score': bullish_score,
        'bearish_score': bearish_score,
        'sentiment': sentiment
    }

def load_commodity_data(filename='commodity_market_data.pkl'):
    """Load commodity market data from pickle file"""
    if not os.path.exists(filename):
        print(f"ERROR: {filename} not found")
        return None
    
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        return data
    except Exception as e:
        print(f"ERROR loading {filename}: {e}")
        return None

def analyze_commodities():
    """Main analysis function"""
    print("\n" + "="*70)
    print("ANALYZING COMMODITY MARKET DATA")
    print("="*70)
    
    payload = load_commodity_data('commodity_market_data.pkl')
    if payload is None:
        return False
    
    market_data = payload.get('data', {})
    if not market_data:
        print("ERROR: No commodity data found in pickle file")
        return False
    
    print(f"\nAnalyzing {len(market_data)} commodities...")
    
    analysis_list = []
    
    for commodity_name, df in market_data.items():
        try:
            if df.empty or len(df) < 20:
                print(f"  ⚠ {commodity_name}: Insufficient data (need 20+ rows)")
                continue
            
            current_price = float(df['Close'].iloc[-1])
            ma20 = calculate_ma(df, 20)
            ma50 = calculate_ma(df, 50)
            rsi = calculate_rsi(df, 14)
            atr = calculate_atr(df, 14)
            supertrend = calculate_supertrend(df, 10, 3)
            vwap = calculate_vwap(df)
            
            bb = calculate_bollinger_bands(df, 20, 2)
            
            return_5d = ((current_price - df['Close'].iloc[-5]) / df['Close'].iloc[-5] * 100) if len(df) >= 5 else 0
            return_20d = ((current_price - df['Close'].iloc[-20]) / df['Close'].iloc[-20] * 100) if len(df) >= 20 else 0
            
            current_volume = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
            avg_volume = float(df['Volume'].tail(20).mean()) if 'Volume' in df.columns else 1
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            row_data = {
                'Close': current_price,
                'RSI': rsi,
                'MA20': ma20,
                'MA50': ma50,
                'ATR': atr,
                'VWAP': vwap,
                'Return_5D': return_5d,
                'Return_20D': return_20d,
                'Volume_Ratio': volume_ratio
            }
            
            sentiment_data = calculate_commodity_sentiment(row_data)
            
            analysis_row = {
                'Commodity': commodity_name,
                'Price': round(current_price, 4),
                'MA20': round(ma20, 4),
                'MA50': round(ma50, 4),
                'RSI': round(rsi, 2),
                'ATR': round(atr, 4),
                'Supertrend': round(supertrend, 4),
                'VWAP': round(vwap, 4),
                'BB_Upper': round(bb['upper'], 4),
                'BB_Middle': round(bb['middle'], 4),
                'BB_Lower': round(bb['lower'], 4),
                'Return_5D': round(return_5d, 2),
                'Return_20D': round(return_20d, 2),
                'Volume_Ratio': round(volume_ratio, 2),
                'Bullish_Score': sentiment_data['bullish_score'],
                'Bearish_Score': sentiment_data['bearish_score'],
                'Sentiment': sentiment_data['sentiment']
            }
            
            analysis_list.append(analysis_row)
            status = "[+]" if sentiment_data['sentiment'] == 'BULLISH' else "[-]" if sentiment_data['sentiment'] == 'BEARISH' else "[*]"
            print(f"  {status} {commodity_name:20} | Price: {current_price:10.2f} | RSI: {rsi:6.2f} | Sentiment: {sentiment_data['sentiment']}")
            
        except Exception as e:
            print(f"  ERROR analyzing {commodity_name}: {str(e)[:60]}")
            continue
    
    if not analysis_list:
        print("ERROR: No commodities could be analyzed")
        return False
    
    analysis_list.sort(key=lambda x: (x['Sentiment'] == 'BEARISH', -x['Bullish_Score']))
    
    print(f"\nSaving {len(analysis_list)} commodities to commodity_analysis_table_report.json...")
    
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'total_commodities': len(analysis_list),
        'bullish_count': sum(1 for x in analysis_list if x['Sentiment'] == 'BULLISH'),
        'bearish_count': sum(1 for x in analysis_list if x['Sentiment'] == 'BEARISH'),
        'neutral_count': sum(1 for x in analysis_list if x['Sentiment'] == 'NEUTRAL'),
        'commodities': analysis_list
    }
    
    with open('commodity_analysis_table_report.json', 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2)
    
    print("Generating HTML report...")
    generate_html_report(analysis_list, report_data)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"✓ JSON Report: commodity_analysis_table_report.json")
    print(f"✓ HTML Report: commodity_analysis_table_report.html")
    print(f"✓ Total Commodities: {report_data['total_commodities']}")
    print(f"✓ Bullish: {report_data['bullish_count']} | Bearish: {report_data['bearish_count']} | Neutral: {report_data['neutral_count']}")
    
    return True

def generate_html_report(analysis_list, report_data):
    """Generate interactive HTML report"""
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Commodity Market Analysis Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
        }}
        header {{
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }}
        h1 {{ color: #333; font-size: 2.2em; }}
        .refresh-btn {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .refresh-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}
        .refresh-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}
        .progress-container {{
            display: none;
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        .progress-container.active {{
            display: block;
        }}
        .progress-bar {{
            width: 100%;
            height: 25px;
            background: #ddd;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 10px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 12px;
        }}
        .progress-text {{
            font-size: 13px;
            color: #666;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-box {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-box h3 {{ font-size: 2em; margin: 10px 0; }}
        .stat-box p {{ opacity: 0.9; }}
        .controls {{
            display: flex;
            gap: 15px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        input, select {{
            padding: 10px 15px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        input:focus, select:focus {{
            outline: none;
            border-color: #667eea;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 14px;
        }}
        thead tr {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }}
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{ background: rgba(0,0,0,0.1); }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        tbody tr:hover {{ background: #f5f5f5; }}
        .bullish {{ color: #27ae60; font-weight: bold; }}
        .bearish {{ color: #c0392b; font-weight: bold; }}
        .neutral {{ color: #f39c12; font-weight: bold; }}
        .sentiment-badge {{
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-align: center;
            min-width: 70px;
        }}
        .bullish-badge {{
            background: #d5f4e6;
            color: #27ae60;
        }}
        .bearish-badge {{
            background: #fadbd8;
            color: #c0392b;
        }}
        .neutral-badge {{
            background: #fdebd0;
            color: #f39c12;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Commodity Market Analysis Report</h1>
                <p>Real-time technical analysis and sentiment scoring</p>
            </div>
            <button class="refresh-btn" id="refreshBtn" onclick="refreshData()">Refresh Data</button>
        </header>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width: 0%;">
                    <span id="progressPercent">0%</span>
                </div>
            </div>
            <div class="progress-text">
                <span id="progressStatus">Initializing...</span>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <p>Total Commodities</p>
                <h3>{report_data['total_commodities']}</h3>
            </div>
            <div class="stat-box" style="background: linear-gradient(135deg, #27ae60, #1e8449);">
                <p>Bullish</p>
                <h3 id="bullishCount">{report_data['bullish_count']}</h3>
            </div>
            <div class="stat-box" style="background: linear-gradient(135deg, #c0392b, #a93226);">
                <p>Bearish</p>
                <h3 id="bearishCount">{report_data['bearish_count']}</h3>
            </div>
            <div class="stat-box" style="background: linear-gradient(135deg, #f39c12, #d68910);">
                <p>Neutral</p>
                <h3 id="neutralCount">{report_data['neutral_count']}</h3>
            </div>
        </div>
        
        <div class="controls">
            <input type="text" id="searchBox" placeholder="Search commodity..." onkeyup="filterTable()">
            <select id="sentimentFilter" onchange="filterTable()">
                <option value="">All Sentiments</option>
                <option value="BULLISH">Bullish</option>
                <option value="BEARISH">Bearish</option>
                <option value="NEUTRAL">Neutral</option>
            </select>
        </div>
        
        <table id="dataTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Commodity</th>
                    <th onclick="sortTable(1)">Price</th>
                    <th onclick="sortTable(2)">MA20</th>
                    <th onclick="sortTable(3)">MA50</th>
                    <th onclick="sortTable(4)">RSI</th>
                    <th onclick="sortTable(5)">ATR</th>
                    <th onclick="sortTable(6)">Return 5D</th>
                    <th onclick="sortTable(7)">Return 20D</th>
                    <th onclick="sortTable(8)">Sentiment</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for row in analysis_list:
        sentiment_class = row['Sentiment'].lower()
        badge_class = f"{sentiment_class}-badge"
        html_content += f"""                <tr>
                    <td>{row['Commodity']}</td>
                    <td>{row['Price']}</td>
                    <td>{row['MA20']}</td>
                    <td>{row['MA50']}</td>
                    <td>{row['RSI']}</td>
                    <td>{row['ATR']}</td>
                    <td class="{'bullish' if row['Return_5D'] > 0 else 'bearish'}">{row['Return_5D']:+.2f}%</td>
                    <td class="{'bullish' if row['Return_20D'] > 0 else 'bearish'}">{row['Return_20D']:+.2f}%</td>
                    <td><span class="sentiment-badge {badge_class}">{row['Sentiment']}</span></td>
                </tr>
"""
    
    html_content += f"""            </tbody>
        </table>
        
        <div class="timestamp">
            Last updated: {report_data['timestamp']}
        </div>
    </div>
    
    <script>
        const isStaticHost = location.hostname.includes('github.io') || location.protocol === 'file:';
        const GITHUB_OWNER = 'MangalParan';
        const GITHUB_REPO = 'stock_report';
        const WORKFLOW_FILE = 'refresh-data.yml';
        let refreshInProgress = false;
        let progressUpdateInterval = null;

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
                let pct = 10;
                if (run.status === 'in_progress') pct = 50;
                if (run.status === 'queued') pct = 5;
                document.getElementById('progressFill').style.width = pct + '%';
                document.getElementById('progressPercent').textContent = pct + '%';
                document.getElementById('progressStatus').textContent = 'Workflow ' + run.status + '...';
                await new Promise(r => setTimeout(r, 5000));
            }}
            throw new Error('Workflow timed out');
        }}

        async function refreshData() {{
            if (!isStaticHost) {{
                // Local server mode
                if (refreshInProgress) return;
                refreshInProgress = true;
                const btn = document.getElementById('refreshBtn');
                const container = document.getElementById('progressContainer');
                btn.disabled = true;
                container.classList.add('active');
                document.getElementById('progressFill').style.width = '0%';
                document.getElementById('progressPercent').textContent = '0%';
                document.getElementById('progressStatus').textContent = 'Starting refresh...';
                try {{
                    const response = await fetch('/refresh-data', {{method: 'POST'}});
                    if (!response.ok) throw new Error('Failed to start refresh');
                    updateLocalProgress();
                    progressUpdateInterval = setInterval(updateLocalProgress, 500);
                }} catch (error) {{
                    document.getElementById('progressStatus').textContent = 'Error: ' + error.message;
                    btn.disabled = false;
                    refreshInProgress = false;
                    if (progressUpdateInterval) clearInterval(progressUpdateInterval);
                }}
                return;
            }}

            // GitHub Pages mode
            if (refreshInProgress) return;
            let token = getGitHubToken();
            if (!token) {{ token = promptForToken(); if (!token) return; }}

            refreshInProgress = true;
            const btn = document.getElementById('refreshBtn');
            const container = document.getElementById('progressContainer');
            btn.disabled = true;
            container.classList.add('active');
            document.getElementById('progressFill').style.width = '0%';
            document.getElementById('progressPercent').textContent = '0%';
            document.getElementById('progressStatus').textContent = 'Triggering data refresh workflow...';

            try {{
                await triggerWorkflow(token);
                document.getElementById('progressStatus').textContent = 'Workflow triggered. Waiting for completion...';
                document.getElementById('progressFill').style.width = '10%';
                document.getElementById('progressPercent').textContent = '10%';

                await pollWorkflowRun(token);

                document.getElementById('progressFill').style.width = '100%';
                document.getElementById('progressPercent').textContent = '100%';
                document.getElementById('progressStatus').textContent = 'Refresh complete! Reloading page...';
                setTimeout(() => {{ window.location.href = window.location.pathname + '?t=' + Date.now(); }}, 3000);
            }} catch (error) {{
                document.getElementById('progressStatus').textContent = 'Error: ' + error.message;
                btn.disabled = false;
                refreshInProgress = false;
            }}
        }}

        async function updateLocalProgress() {{
            try {{
                const response = await fetch('/progress');
                const data = await response.json();
                
                const percentage = data.percentage || 0;
                const status = data.status || 'processing';
                const message = data.message || '';
                
                document.getElementById('progressFill').style.width = percentage + '%';
                document.getElementById('progressPercent').textContent = percentage + '%';
                
                let statusText = message || status;
                if (percentage === 100) {{
                    statusText = 'Refresh complete! Reloading...';
                    if (progressUpdateInterval) clearInterval(progressUpdateInterval);
                    setTimeout(() => location.reload(), 1500);
                }}
                document.getElementById('progressStatus').textContent = statusText;
            }} catch (error) {{
                console.error('Progress update error:', error);
            }}
        }}
        
        function filterTable() {{
            const searchInput = document.getElementById('searchBox').value.toUpperCase();
            const sentimentFilter = document.getElementById('sentimentFilter').value;
            const table = document.getElementById('dataTable');
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            
            for (let i = 0; i < rows.length; i++) {{
                const commodity = rows[i].cells[0].textContent.toUpperCase();
                const sentiment = rows[i].cells[8].textContent.toUpperCase();
                
                const matchesSearch = commodity.includes(searchInput);
                const matchesSentiment = !sentimentFilter || sentiment.includes(sentimentFilter);
                
                rows[i].style.display = matchesSearch && matchesSentiment ? '' : 'none';
            }}
        }}
        
        function sortTable(colIndex) {{
            const table = document.getElementById('dataTable');
            let rows = Array.from(table.getElementsByTagName('tbody')[0].getElementsByTagName('tr'));
            
            rows.sort((a, b) => {{
                let aVal = a.cells[colIndex].textContent.trim();
                let bVal = b.cells[colIndex].textContent.trim();
                
                let aNum = parseFloat(aVal);
                let bNum = parseFloat(bVal);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return aNum - bNum;
                }}
                return aVal.localeCompare(bVal);
            }});
            
            const tbody = table.getElementsByTagName('tbody')[0];
            rows.forEach(row => tbody.appendChild(row));
        }}
    </script>
</body>
</html>"""
    
    with open('commodity_analysis_table_report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == '__main__':
    analyze_commodities()
