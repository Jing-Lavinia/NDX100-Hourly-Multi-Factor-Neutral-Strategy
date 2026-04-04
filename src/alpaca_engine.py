import pandas as pd
from pathlib import Path
from .utils import logger
from . import config


def load_and_clean_alpaca_data(
    csv_dir_path: str,
    resample_freq: str = "1h",
    start_date: str = None,
    end_date: str = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load, clean, and resample Alpaca 5-minute bar CSVs into wide-format price and volume matrices.

    Args:
        csv_dir_path: Path to directory containing *_5min.csv files.
        resample_freq: Pandas offset alias for resampling (e.g. '1h', '5min').
        start_date: ISO date string for pre-resampling truncation (reduces memory footprint).
        end_date: ISO date string for pre-resampling truncation.

    Returns:
        Tuple of (prices_df, volumes_df) aligned to US Eastern market hours.
    """
    logger.info(f"Loading Alpaca data | freq={resample_freq} | range=[{start_date}, {end_date}]")

    csv_dir = Path(csv_dir_path)
    all_files = list(csv_dir.glob("*_5min.csv"))
    if not all_files:
        raise FileNotFoundError(f"No CSV files found in: {csv_dir}")

    close_dict: dict[str, pd.Series] = {}
    volume_dict: dict[str, pd.Series] = {}

    for i, f in enumerate(all_files):
        ticker = f.stem.split("_")[0]

        df = pd.read_csv(f)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.set_index("timestamp", inplace=True)
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)

        if start_date:
            df = df.loc[start_date:]
        if end_date:
            df = df.loc[:end_date]

        df_market = df.between_time("09:30", "15:59")

        if resample_freq:
            resampled = df_market.resample(resample_freq).agg({"close": "last", "volume": "sum"}).dropna()
            close_dict[ticker] = resampled["close"]
            volume_dict[ticker] = resampled["volume"]
        else:
            close_dict[ticker] = df_market["close"]
            volume_dict[ticker] = df_market["volume"]

        if (i + 1) % 20 == 0:
            logger.info(f"  Processed {i + 1}/{len(all_files)} files...")

    logger.info("Assembling wide-format matrices...")
    prices_df = pd.DataFrame(close_dict).sort_index()
    volumes_df = pd.DataFrame(volume_dict).sort_index()

    prices_df = prices_df.dropna(how="all").ffill()
    volumes_df = volumes_df.dropna(how="all").fillna(0)

    logger.info(f"Data loaded successfully | shape={prices_df.shape}")
    return prices_df, volumes_df
