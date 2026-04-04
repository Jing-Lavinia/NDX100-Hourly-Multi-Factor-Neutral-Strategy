from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"

ALPACA_CSV_DIR = DATA_DIR / "ndx100_5min_csv"
BENCHMARK_CSV_PATH = DATA_DIR / "benchmark_data" / "QQQ_5min.csv"
VIX_DATA_FILE = DATA_DIR / "vix_1h.csv"
REPORTS_DIR = BASE_DIR / "reports"

DATA_START_DATE = "2025-08-01"
BACKTEST_START_DATE = "2026-01-01"
END_DATE = "2026-03-31"

FORWARD_PERIODS = [1, 6, 12]

SECTOR_MAP = {
    "AAPL": "Tech", "MSFT": "Tech", "NVDA": "Tech", "GOOGL": "Tech", "META": "Tech",
    "GOOG": "Tech", "ADBE": "Tech", "ADI": "Tech", "ADSK": "Tech", "AMAT": "Tech",
    "AMD": "Tech", "APP": "Tech", "ARM": "Tech", "ASML": "Tech", "AVGO": "Tech",
    "CDNS": "Tech", "CRWD": "Tech", "CSCO": "Tech", "CTSH": "Tech", "DDOG": "Tech",
    "EA": "Tech", "FTNT": "Tech", "INTC": "Tech", "INTU": "Tech", "KLAC": "Tech",
    "LRCX": "Tech", "MCHP": "Tech", "MPWR": "Tech", "MRVL": "Tech", "MSTR": "Tech",
    "MU": "Tech", "NFLX": "Tech", "NXPI": "Tech", "PANW": "Tech", "PLTR": "Tech",
    "QCOM": "Tech", "ROP": "Tech", "SHOP": "Tech", "SNPS": "Tech", "STX": "Tech",
    "TEAM": "Tech", "TTWO": "Tech", "TXN": "Tech", "WBD": "Tech", "WDC": "Tech",
    "WDAY": "Tech", "ZS": "Tech", "CHTR": "Tech", "CMCSA": "Tech", "TMUS": "Tech",
    "AMZN": "Consumer", "TSLA": "Consumer", "PEP": "Consumer", "COST": "Consumer",
    "ABNB": "Consumer", "BKNG": "Consumer", "CCEP": "Consumer", "DASH": "Consumer",
    "KDP": "Consumer", "KHC": "Consumer", "MAR": "Consumer", "MDLZ": "Consumer",
    "MELI": "Consumer", "MNST": "Consumer", "ORLY": "Consumer", "PDD": "Consumer",
    "ROST": "Consumer", "SBUX": "Consumer", "WMT": "Consumer",
    "ALNY": "Healthcare", "AMGN": "Healthcare", "DXCM": "Healthcare", "GEHC": "Healthcare",
    "GILD": "Healthcare", "IDXX": "Healthcare", "INSM": "Healthcare", "ISRG": "Healthcare",
    "REGN": "Healthcare", "VRTX": "Healthcare",
    "ADP": "Industrials", "AXON": "Industrials", "CPRT": "Industrials", "CSX": "Industrials",
    "CTAS": "Industrials", "FAST": "Industrials", "FER": "Industrials", "HON": "Industrials",
    "ODFL": "Industrials", "PAYX": "Industrials", "PCAR": "Industrials", "VRSK": "Industrials",
    "AEP": "Utilities", "CEG": "Utilities", "EXC": "Utilities", "XEL": "Utilities",
    "BKR": "Energy", "FANG": "Energy",
    "PYPL": "Financials",
    "LIN": "Materials",
    "CSGP": "Real Estate",
}
