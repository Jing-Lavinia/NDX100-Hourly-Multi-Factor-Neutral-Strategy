import os
import time
from datetime import datetime, timedelta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# Initialize Alpaca client
API_KEY = 'PKHHXR4WCUXWCPXEFUD72BG5V2'
SECRET_KEY = '8CyLefa7PCZCc3cBqbdfsunGpcuQV3w4jwZNfzX8SSnQ'
client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# Ensure target directory exists
SAVE_DIR = "ndx100_5min_csv"
os.makedirs(SAVE_DIR, exist_ok=True)

# Nasdaq 100 component universe
tickers = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "ALNY", "AMAT", "AMD",
    "AMGN", "AMZN", "APP", "ARM", "ASML", "AVGO", "AXON", "BKNG", "BKR", "CCEP",
    "CDNS", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO", "CSGP", "CSX",
    "CTAS", "CTSH", "DASH", "DDOG", "DXCM", "EA", "EXC", "FANG", "FAST", "FER",
    "FTNT", "GEHC", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "INSM", "INTC", "INTU",
    "ISRG", "KDP", "KHC", "KLAC", "LIN", "LRCX", "MAR", "MCHP", "MDLZ", "MELI",
    "META", "MNST", "MPWR", "MRVL", "MSFT", "MSTR", "MU", "NFLX", "NVDA", "NXPI",
    "ODFL", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP", "PLTR", "PYPL", "QCOM",
    "REGN", "ROP", "ROST", "SBUX", "SHOP", "SNPS", "STX", "TEAM", "TMUS", "TSLA",
    "TTWO", "TXN", "VRSK", "VRTX", "WBD", "WDC", "WDAY", "WMT", "XEL", "ZS"
]

# Set timeframe: 5 years of 5-minute resolution data
end_date = datetime(2026, 3, 28)
start_date = end_date - timedelta(days=5 * 365)
timeframe = TimeFrame(amount=5, unit=TimeFrameUnit.Minute)

print(f"Starting download for {len(tickers)} tickers...")
print(f"Timeframe: {start_date.date()} to {end_date.date()}\n" + "-" * 50)

for ticker in tickers:
    file_path = f"{SAVE_DIR}/{ticker}_5min.csv"

    # Resume capability: skip if already downloaded
    if os.path.exists(file_path):
        print(f"[{ticker}] CSV exists, skipping...")
        continue

    print(f"Downloading [{ticker}]...")
    request_params = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=timeframe,
        start=start_date,
        end=end_date
    )

    try:
        # Fetch data (Alpaca SDK handles background pagination automatically)
        bars = client.get_stock_bars(request_params)

        if bars.df.empty:
            print(f"[{ticker}] No historical data found.")
            continue

        bars_df = bars.df

        # Convert standard UTC to US Eastern Time (New York)
        bars_df.index = bars_df.index.set_levels(
            bars_df.index.levels[1].tz_convert('America/New_York'),
            level=1
        )

        bars_df.to_csv(file_path)
        print(f"[{ticker}] Download complete! Rows: {len(bars_df)} -> {file_path}")

    except Exception as e:
        print(f"[{ticker}] Error during download: {e}")

    # Rate limit handling for Alpaca free tier
    time.sleep(1)

print("-" * 50)
print("Data pipeline execution finished.")