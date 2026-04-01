import pandas as pd
import os
from pathlib import Path
from .utils import logger
from . import config


def load_and_clean_alpaca_data(csv_dir_path: str, resample_freq: str = '1h',
                               start_date: str = None, end_date: str = None):
    """
    High-performance cleaning and merging engine for Alpaca 5-min data (supports low-level time slicing).
    """
    logger.info(f"Loading and cleaning local Alpaca data. Target frequency: {resample_freq}")
    csv_dir = Path(csv_dir_path)
    all_files = list(csv_dir.glob("*_5min.csv"))

    if not all_files:
        raise FileNotFoundError(f"No CSV files found in {csv_dir}!")

    close_dict = {}
    volume_dict = {}

    for i, f in enumerate(all_files):
        ticker = f.stem.split('_')[0]

        df = pd.read_csv(f)

        # Standardize timezone to US Eastern Time (tz-naive) for seamless alignment
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df.set_index('timestamp', inplace=True)
        df.index = df.index.tz_convert('America/New_York').tz_localize(None)

        # CRITICAL: Truncate time series before resampling to drastically reduce memory footprint and CPU load
        if start_date:
            df = df.loc[start_date:]
        if end_date:
            df = df.loc[:end_date]

        # Filter for regular market hours to eliminate pre/post-market low-liquidity noise
        df_market_hours = df.between_time('09:30', '15:59')

        if resample_freq:
            resampled = df_market_hours.resample(resample_freq).agg({
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            close_dict[ticker] = resampled['close']
            volume_dict[ticker] = resampled['volume']
        else:
            close_dict[ticker] = df_market_hours['close']
            volume_dict[ticker] = df_market_hours['volume']

        if (i + 1) % 20 == 0:
            logger.info(f"Processed {i + 1}/{len(all_files)} stocks...")

    logger.info("Assembling data into wide-format matrices...")
    prices_df = pd.DataFrame(close_dict).sort_index()
    volumes_df = pd.DataFrame(volume_dict).sort_index()

    # Forward fill prices to handle missing K-lines; fill missing volumes with 0
    prices_df = prices_df.dropna(how='all').ffill()
    volumes_df = volumes_df.dropna(how='all').fillna(0)

    logger.info(f"Data processing complete! Shape: {prices_df.shape}")
    return prices_df, volumes_df