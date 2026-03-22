#!/usr/bin/env python3
"""
Update Stock Market Data
Downloads OHLCV data from Yahoo Finance for NSE stocks listed in EQUITY_L.csv
Saves to market_data.pkl with progress tracking via progress.json
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
import time
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

FUNDAMENTAL_FIELDS = [
    'trailingPE', 'trailingEps', 'bookValue', 'dividendYield',
    'marketCap', 'totalRevenue', 'profitMargins', 'returnOnEquity', 'debtToEquity'
]

PROGRESS_FILE = 'progress.json'


def save_progress(percentage, status, message):
    """Save progress to JSON file for UI tracking"""
    progress = {
        "percentage": int(percentage),
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
    except Exception:
        pass


def fetch_fundamentals_for_symbol(symbol):
    """Fetch fundamental data for a single symbol via yfinance Ticker.info"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        fund = {}
        for field in FUNDAMENTAL_FIELDS:
            fund[field] = info.get(field)
        return symbol, fund
    except Exception:
        return symbol, {field: None for field in FUNDAMENTAL_FIELDS}


def update_stock_data():
    """Fetch fresh stock data from yfinance and save to market_data.pkl"""
    print("\n" + "="*70)
    print("UPDATING STOCK MARKET DATA FROM YAHOO FINANCE")
    print("="*70)

    try:
        save_progress(0, "initializing", "Loading stock symbol list from EQUITY_L.csv...")

        if not os.path.exists('EQUITY_L.csv'):
            print("ERROR: EQUITY_L.csv not found")
            save_progress(0, "error", "EQUITY_L.csv not found")
            return False

        # Read EQUITY_L.csv and extract SYMBOL column, append .NS for yfinance
        equity_df = pd.read_csv('EQUITY_L.csv')
        raw_symbols = equity_df['SYMBOL'].dropna().unique().tolist()
        symbols = [s.strip() + '.NS' for s in raw_symbols if isinstance(s, str) and s.strip()]

        print(f"\nLoaded {len(symbols)} stock symbols from EQUITY_L.csv")

        if not symbols:
            save_progress(0, "error", "No symbols found in EQUITY_L.csv")
            return False

        stock_data = {}
        BATCH_SIZE = 50
        chunks = [symbols[i:i + BATCH_SIZE] for i in range(0, len(symbols), BATCH_SIZE)]

        print(f"Downloading data for {len(symbols)} stocks in {len(chunks)} batches")
        print("This may take 5-15 minutes...\n")

        save_progress(5, "downloading", f"Starting download of {len(symbols)} stocks in {len(chunks)} batches")

        for batch_num, chunk in enumerate(chunks, 1):
            try:
                batch_progress = 5 + (batch_num / len(chunks)) * 55
                save_progress(int(batch_progress), "downloading",
                              f"Batch {batch_num}/{len(chunks)}: Downloading {len(chunk)} stocks...")

                print(f"Batch {batch_num}/{len(chunks)}: Downloading {len(chunk)} stocks...", end=" ")

                data = yf.download(
                    chunk,
                    period="1y",
                    group_by='ticker',
                    threads=True,
                    progress=False,
                    auto_adjust=True
                )

                batch_count = 0
                if not data.empty:
                    if isinstance(data.columns, pd.MultiIndex):
                        for sym in chunk:
                            if sym in data.columns.levels[0]:
                                df = data[sym].copy()
                                if not df.empty:
                                    df = df.dropna(how='all')
                                    if len(df) > 10:
                                        stock_data[sym] = df
                                        batch_count += 1
                    else:
                        if len(chunk) == 1:
                            df = data.copy()
                            if not df.empty and len(df) > 10:
                                stock_data[chunk[0]] = df
                                batch_count += 1

                print(f"Saved {batch_count} stocks")

                # Small delay between batches to avoid rate limiting
                if batch_num < len(chunks):
                    time.sleep(1)

            except Exception as e:
                print(f"Error: {str(e)[:80]}")
                continue

        # --- Phase 2: Fetch fundamental data ---
        print(f"\nFetching fundamental data for {len(stock_data)} stocks...")
        save_progress(62, "fundamentals", f"Starting fundamental data fetch for {len(stock_data)} stocks...")

        fundamentals = {}
        symbols_to_fetch = list(stock_data.keys())
        total_fund = len(symbols_to_fetch)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_fundamentals_for_symbol, sym): sym for sym in symbols_to_fetch}
            done_count = 0
            for future in as_completed(futures):
                sym, fund_data = future.result()
                fundamentals[sym] = fund_data
                done_count += 1
                if done_count % 100 == 0 or done_count == total_fund:
                    pct = 62 + int((done_count / total_fund) * 30)
                    print(f"  Fundamentals: {done_count}/{total_fund}")
                    save_progress(pct, "fundamentals",
                                  f"Fundamentals: {done_count}/{total_fund} stocks")

        print(f"Fundamental data fetched for {len(fundamentals)} stocks")

        # --- Phase 3: Save ---
        print(f"\nSaving {len(stock_data)} stocks to market_data.pkl...")
        save_progress(95, "saving", f"Saving {len(stock_data)} stocks to disk...")

        payload = {
            "timestamp": datetime.now(),
            "data": stock_data,
            "fundamentals": fundamentals
        }

        with open('market_data.pkl', 'wb') as f:
            pickle.dump(payload, f)

        print(f"SUCCESS: Updated market_data.pkl with {len(stock_data)} stocks + fundamentals")
        print(f"Timestamp: {payload['timestamp']}")
        print("="*70)

        save_progress(100, "completed", f"Successfully saved {len(stock_data)} stocks with fundamentals")
        return True

    except Exception as e:
        error_msg = f"ERROR: {str(e)}"
        print(error_msg)
        save_progress(0, "error", error_msg)
        return False


if __name__ == '__main__':
    update_stock_data()
