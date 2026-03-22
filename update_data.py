#!/usr/bin/env python3
"""
Update Market Data Script for Commodities
Updates commodity_market_data.pkl with fresh commodity data from Yahoo Finance
Run this script to refresh all commodity data
Supports progress tracking by writing to progress.json
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
import yfinance as yf

PROGRESS_FILE = 'progress.json'

# Mapping of MCX commodities to yfinance futures symbols
MCX_TO_YFINANCE = {
    'GOLD': 'GC=F',           # Gold futures (COMEX)
    'SILVER': 'SI=F',         # Silver futures (COMEX)
    'CRUDEOIL': 'CL=F',       # Crude Oil (NYMEX)
    'NATURALGAS': 'NG=F',     # Natural Gas (NYMEX)
    'COPPER': 'HG=F',         # Copper (COMEX)
    'ZINC': 'ZN=F',           # Zinc (COMEX)
    'LEAD': 'PB=F',           # Lead (COMEX)
    'NICKEL': 'PA=F',         # Palladium (COMEX)
    'ALUMINUM': 'ALI=F',      # Aluminum (if available)
}

# Fallback commodity data if CSV can't be read
DEFAULT_COMMODITIES = [
    ('Gold', 'GOLD', 100, 'grams', 'Precious Metals', 'Gold futures - primary precious metal contract'),
    ('Silver', 'SILVER', 30, 'kg', 'Precious Metals', 'Silver futures - secondary precious metal contract'),
    ('Crude Oil', 'CRUDEOIL', 100, 'barrels', 'Energy', 'Indian crude oil benchmark'),
    ('Natural Gas', 'NATURALGAS', 1000, 'MMBtu', 'Energy', 'Natural gas futures contract'),
    ('Copper', 'COPPER', 1000, 'kg', 'Industrial Metals', 'Copper futures for industrial use'),
    ('Zinc', 'ZINC', 25000, 'kg', 'Industrial Metals', 'Zinc futures contract'),
    ('Lead', 'LEAD', 25000, 'kg', 'Industrial Metals', 'Lead futures contract'),
    ('Nickel', 'NICKEL', 1000, 'kg', 'Industrial Metals', 'Nickel futures for stainless steel'),
]

def save_progress(percentage, status, message=""):
    """Save progress to JSON file for server to read"""
    progress_data = {
        "percentage": min(100, max(0, percentage)),
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress_data, f)

def load_commodity_data(filename='commodity_market_data.pkl'):
    """Load commodity market data from pickle file"""
    if not os.path.exists(filename):
        return {'timestamp': datetime.now(), 'data': {}}
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data

def recreate_commodity_csv(filename='Commodity_L.csv'):
    """Recreate Commodity_L.csv from scratch if corrupted"""
    print(f"\nRecreating {filename} from default commodity list...")
    try:
        df = pd.DataFrame(DEFAULT_COMMODITIES, 
                         columns=['Commodity_Name', 'MCX_Symbol', 'Lot_Size', 'Unit', 'Category', 'Description'])
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"✓ Successfully created {filename}")
        return df
    except Exception as e:
        print(f"ERROR creating {filename}: {e}")
        raise

def read_csv_with_encoding(filename):
    """Try reading CSV with multiple encodings, including exotic ones"""
    encodings = [
        'utf-8',
        'iso-8859-1',
        'latin1',
        'cp1252',
        'utf-16',
        'shift_jis',
        'gb2312',
        'big5',
        'ascii',
        'utf-32',
    ]
    
    for encoding in encodings:
        try:
            df = pd.read_csv(filename, encoding=encoding)
            print(f"✓ Successfully read {filename} with encoding: {encoding}")
            return df
        except Exception:
            continue
    
    # Try reading with error handling
    try:
        print("Attempting to read with error='ignore'...")
        df = pd.read_csv(filename, encoding='utf-8', on_bad_lines='skip', engine='python')
        print(f"✓ Successfully read {filename} with error handling")
        return df
    except Exception:
        pass
    
    # Last resort: recreate from scratch
    print(f"Could not read {filename} - file may be corrupted.")
    try:
        return recreate_commodity_csv(filename)
    except Exception as e:
        raise Exception(f"Failed to read or recreate {filename}: {e}")

def update_market_data():
    """Update market data by fetching fresh commodity data from yfinance"""
    print("\n" + "="*70)
    print("UPDATING COMMODITY MARKET DATA FROM YAHOO FINANCE")
    print("="*70)
    
    try:
        save_progress(0, "initializing", "Loading commodity symbol list...")
        
        # Load commodity symbols from Commodity_L.csv
        if os.path.exists('Commodity_L.csv'):
            try:
                commodity_df = read_csv_with_encoding('Commodity_L.csv')
                mcx_symbols = commodity_df['MCX_Symbol'].tolist()
                mcx_symbols = [s.strip() for s in mcx_symbols if isinstance(s, str)]
                print(f"\nLoaded {len(mcx_symbols)} MCX symbols from Commodity_L.csv")
                print(f"Commodities: {', '.join(mcx_symbols[:10])}{'...' if len(mcx_symbols) > 10 else ''}")
            except Exception as e:
                print(f"ERROR reading Commodity_L.csv: {e}")
                print("Creating default commodity list...")
                try:
                    commodity_df = recreate_commodity_csv('Commodity_L.csv')
                    mcx_symbols = commodity_df['MCX_Symbol'].tolist()
                    mcx_symbols = [s.strip() for s in mcx_symbols if isinstance(s, str)]
                    print(f"Loaded {len(mcx_symbols)} default MCX symbols")
                except Exception as e2:
                    save_progress(0, "error", f"Failed to load commodities: {e2}")
                    return False
        else:
            print("Commodity_L.csv not found. Creating from default list...")
            try:
                commodity_df = recreate_commodity_csv('Commodity_L.csv')
                mcx_symbols = commodity_df['MCX_Symbol'].tolist()
                mcx_symbols = [s.strip() for s in mcx_symbols if isinstance(s, str)]
                print(f"Loaded {len(mcx_symbols)} default MCX symbols")
            except Exception as e:
                save_progress(0, "error", f"Failed to create Commodity_L.csv: {e}")
                return False
        
        # Map MCX symbols to yfinance futures symbols
        yfinance_symbols = []
        symbol_map = {}
        unmapped = []
        
        for mcx_sym in mcx_symbols:
            yf_sym = MCX_TO_YFINANCE.get(mcx_sym)
            if yf_sym:
                yfinance_symbols.append(yf_sym)
                symbol_map[yf_sym] = mcx_sym
            else:
                unmapped.append(mcx_sym)
        
        if unmapped:
            print(f"\nWarning: {len(unmapped)} commodities not mapped to yfinance: {unmapped}")
        
        if not yfinance_symbols:
            print("ERROR: No commodities could be mapped to yfinance symbols")
            save_progress(0, "error", "No commodities mapped to yfinance")
            return False
        
        # Download fresh data in batches
        commodity_data = {}
        BATCH_SIZE = 5  # Very small batch for reliability
        chunks = [yfinance_symbols[i:i + BATCH_SIZE] for i in range(0, len(yfinance_symbols), BATCH_SIZE)]
        
        print(f"\nDownloading data for {len(yfinance_symbols)} commodity futures in {len(chunks)} batches")
        print("This may take 5-15 minutes depending on internet speed...\n")
        
        save_progress(5, "downloading", f"Starting download of {len(yfinance_symbols)} commodities in {len(chunks)} batches")
        
        for batch_num, chunk in enumerate(chunks, 1):
            try:
                # Calculate progress (5% for init + 90% for downloads)
                batch_progress = 5 + (batch_num / len(chunks)) * 90
                save_progress(int(batch_progress), "downloading", 
                            f"Batch {batch_num}/{len(chunks)}: Downloading {len(chunk)} commodities...")
                
                print(f"Batch {batch_num}/{len(chunks)}: Downloading {len(chunk)} commodities...", end=" ")
                
                # Download with yfinance
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
                    # Parse Result
                    if isinstance(data.columns, pd.MultiIndex):
                        for yf_sym in chunk:
                            if yf_sym in data.columns.levels[0]:
                                df = data[yf_sym].copy()
                                if not df.empty:
                                    df = df.dropna(how='all')
                                    if len(df) > 10:
                                        mcx_sym = symbol_map.get(yf_sym, yf_sym)
                                        commodity_data[mcx_sym] = df
                                        batch_count += 1
                    else:
                        # Single symbol case
                        if len(chunk) == 1:
                            yf_sym = chunk[0]
                            df = data.copy()
                            if not df.empty and len(df) > 10:
                                mcx_sym = symbol_map.get(yf_sym, yf_sym)
                                commodity_data[mcx_sym] = df
                                batch_count += 1
                
                print(f"Saved {batch_count} commodities")
                
            except Exception as e:
                print(f"Error: {str(e)[:80]}")
                continue
        
        # Save to disk
        print(f"\nSaving {len(commodity_data)} commodities to commodity_market_data.pkl...")
        save_progress(95, "saving", f"Saving {len(commodity_data)} commodities to disk...")
        
        payload = {
            "timestamp": datetime.now(),
            "data": commodity_data
        }
        
        with open('commodity_market_data.pkl', 'wb') as f:
            pickle.dump(payload, f)
        
        print(f"SUCCESS: Updated commodity_market_data.pkl with {len(commodity_data)} commodities")
        print(f"Timestamp: {payload['timestamp']}")
        print("="*70)
        
        save_progress(100, "completed", f"Successfully saved {len(commodity_data)} commodities")
        
        return True
        
    except Exception as e:
        error_msg = f"ERROR: {str(e)}"
        print(error_msg)
        print("="*70 + "\n")
        save_progress(0, "error", error_msg)
        return False

if __name__ == '__main__':
    update_market_data()
