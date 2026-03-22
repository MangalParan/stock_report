#!/usr/bin/env python3
"""
Update Stock Market Data
Downloads OHLCV data from Yahoo Finance for NSE stocks listed in symbols.csv
Saves to market_data.pkl with progress tracking via progress.json
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
import yfinance as yf

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


def update_stock_data():
    """Fetch fresh stock data from yfinance and save to market_data.pkl"""
    print("\n" + "="*70)
    print("UPDATING STOCK MARKET DATA FROM YAHOO FINANCE")
    print("="*70)

    try:
        save_progress(0, "initializing", "Loading stock symbol list...")

        if not os.path.exists('symbols.csv'):
            print("ERROR: symbols.csv not found")
            save_progress(0, "error", "symbols.csv not found")
            return False

        with open('symbols.csv', 'r') as f:
            symbols = [line.strip() for line in f if line.strip()]

        print(f"\nLoaded {len(symbols)} stock symbols from symbols.csv")

        if not symbols:
            save_progress(0, "error", "No symbols found in symbols.csv")
            return False

        stock_data = {}
        BATCH_SIZE = 50
        chunks = [symbols[i:i + BATCH_SIZE] for i in range(0, len(symbols), BATCH_SIZE)]

        print(f"Downloading data for {len(symbols)} stocks in {len(chunks)} batches")
        print("This may take a few minutes...\n")

        save_progress(5, "downloading", f"Starting download of {len(symbols)} stocks in {len(chunks)} batches")

        for batch_num, chunk in enumerate(chunks, 1):
            try:
                batch_progress = 5 + (batch_num / len(chunks)) * 85
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

            except Exception as e:
                print(f"Error: {str(e)[:80]}")
                continue

        print(f"\nSaving {len(stock_data)} stocks to market_data.pkl...")
        save_progress(95, "saving", f"Saving {len(stock_data)} stocks to disk...")

        payload = {
            "timestamp": datetime.now(),
            "data": stock_data
        }

        with open('market_data.pkl', 'wb') as f:
            pickle.dump(payload, f)

        print(f"SUCCESS: Updated market_data.pkl with {len(stock_data)} stocks")
        print(f"Timestamp: {payload['timestamp']}")
        print("="*70)

        save_progress(100, "completed", f"Successfully saved {len(stock_data)} stocks")
        return True

    except Exception as e:
        error_msg = f"ERROR: {str(e)}"
        print(error_msg)
        save_progress(0, "error", error_msg)
        return False


if __name__ == '__main__':
    update_stock_data()
