import os
import time
from datetime import datetime, timedelta

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

API_KEY = "PKHHXR4WCUXWCPXEFUD72BG5V2"
SECRET_KEY = "8CyLefa7PCZCc3cBqbdfsunGpcuQV3w4jwZNfzX8SSnQ"

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

SAVE_DIR = "data/raw/ndx100_5min_csv"
os.makedirs(SAVE_DIR, exist_ok=True)

TICKERS = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "ALNY", "AMAT", "AMD",
    "AMGN", "AMZN", "APP", "ARM", "ASML", "AVGO", "AXON", "BKNG", "BKR", "CCEP",
    "CDNS", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO", "CSGP", "CSX",
    "CTAS", "CTSH", "DASH", "DDOG", "DXCM", "EA", "EXC", "FANG", "FAST", "FER",
    "FTNT", "GEHC", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "INSM", "INTC", "INTU",
    "ISRG", "KDP", "KHC", "KLAC", "LIN", "LRCX", "MAR", "MCHP", "MDLZ", "MELI",
    "META", "MNST", "MPWR", "MRVL", "MSFT", "MSTR", "MU", "NFLX", "NVDA", "NXPI",
    "ODFL", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP", "PLTR", "PYPL", "QCOM",
    "REGN", "ROP", "ROST", "SBUX", "SHOP", "SNPS", "STX", "TEAM", "TMUS", "TSLA",
    "TTWO", "TXN", "VRSK", "VRTX", "WBD", "WDC", "WDAY", "WMT", "XEL", "ZS",
]

END_DATE = datetime(2026, 3, 28)
START_DATE = END_DATE - timedelta(days=1 * 365)
TIMEFRAME = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)


def download_ticker(ticker: str) -> None:
    file_path = f"{SAVE_DIR}/{ticker}_5min.csv"

    if os.path.exists(file_path):
        print(f"[{ticker}] Already downloaded, skipping.")
        return

    print(f"[{ticker}] Downloading...")
    request = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=TIMEFRAME,
        start=START_DATE,
        end=END_DATE,
    )

    try:
        bars = client.get_stock_bars(request)
        if bars.df.empty:
            print(f"[{ticker}] No data returned.")
            return

        df = bars.df
        df.index = df.index.set_levels(
            df.index.levels[1].tz_convert("America/New_York"),
            level=1,
        )
        df.to_csv(file_path)
        print(f"[{ticker}] Done | rows={len(df)} → {file_path}")

    except Exception as exc:
        print(f"[{ticker}] Error: {exc}")


def main() -> None:
    print(f"Downloading {len(TICKERS)} tickers | {START_DATE.date()} → {END_DATE.date()}")
    print("-" * 60)

    for ticker in TICKERS:
        download_ticker(ticker)
        time.sleep(1)

    print("-" * 60)
    print("Download pipeline complete.")


if __name__ == "__main__":
    main()
