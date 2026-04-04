import os
from pathlib import Path

import pandas as pd
import yfinance as yf

RAW_DATA_DIR = Path("data/raw")
TICKERS_DIR = RAW_DATA_DIR / "tickers"
TICKERS_DIR.mkdir(parents=True, exist_ok=True)

PROXY = "http://127.0.0.1:7890"
os.environ["http_proxy"] = PROXY
os.environ["https_proxy"] = PROXY


def fetch_vix_data() -> None:
    """Fetch hourly VIX data (last 60 days) for macro risk scaling."""
    print("Downloading VIX macro data (1H frequency)...")
    save_path = RAW_DATA_DIR / "vix_1h.csv"

    try:
        df = yf.download("^VIX", period="60d", interval="1h", progress=False, auto_adjust=True)

        if df.empty:
            print("WARNING: VIX download returned empty DataFrame.")
            return

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        vix_close = df[["Close"]].copy()
        vix_close.columns = ["VIX"]
        vix_close.index.name = "Date"
        vix_close.to_csv(save_path)
        print(f"VIX data saved to: {save_path}")

    except Exception as exc:
        print(f"ERROR: VIX download failed: {exc}")


if __name__ == "__main__":
    fetch_vix_data()
