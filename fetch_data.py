import yfinance as yf
import pandas as pd
import os
from pathlib import Path

# Configuration and network proxy setup
RAW_DATA_DIR = Path("data/raw")
TICKERS_DIR = RAW_DATA_DIR / "tickers"
TICKERS_DIR.mkdir(parents=True, exist_ok=True)

PROXY = "http://127.0.0.1:7890"
os.environ['http_proxy'] = PROXY
os.environ['https_proxy'] = PROXY


def fetch_all_tickers(ticker_list_file):
    # Implementation for downloading and merging equity price/volume data
    # (Preserving the original execution logic)
    pass


def fetch_vix_data():
    """Fetches macroscopic VIX index data for dynamic risk scaling."""
    print("\nStep 3: Downloading VIX macro data (1H Frequency)...")
    vix_save_path = RAW_DATA_DIR / "vix_1h.csv"

    try:
        # Fetch rolling 60-day, 1-hour resolution VIX data
        df = yf.download("^VIX", period="60d", interval="1h", progress=False, auto_adjust=True)

        if not df.empty:
            # Handle potential MultiIndex column returns from recent yfinance versions
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Extract 'Close' prices and standardize naming convention
            vix_close = df[['Close']].copy()
            vix_close.columns = ['VIX']
            vix_close.index.name = 'Date'

            vix_close.to_csv(vix_save_path)
            print(f"[SUCCESS] VIX macro data exported to: {vix_save_path}")
        else:
            print("WARNING: VIX download returned an empty DataFrame.")

    except Exception as e:
        print(f"ERROR: Failed to download VIX data: {e}")


if __name__ == "__main__":
    # 1. Fetch and merge equities price/volume data
    # fetch_all_tickers("nasdaq100_list.txt")

    # 2. Fetch VIX macro data
    fetch_vix_data()