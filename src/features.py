import pandas as pd
from .utils import logger


def clean_factor_cross_sectionally(raw_factor: pd.DataFrame) -> pd.DataFrame:
    """Industrial-grade cross-sectional factor pipeline: MAD Winsorization + Z-Score Standardization"""

    # 1. MAD (Median Absolute Deviation) Winsorization to neutralize extreme outliers
    median = raw_factor.median(axis=1)
    mad = raw_factor.sub(median, axis=0).abs().median(axis=1)
    upper_bound = median + 5 * mad
    lower_bound = median - 5 * mad
    winsorized_factor = raw_factor.clip(lower=lower_bound, upper=upper_bound, axis=0)

    # 2. Z-Score Standardization
    mean = winsorized_factor.mean(axis=1)
    std = winsorized_factor.std(axis=1)
    return winsorized_factor.sub(mean, axis=0).div(std, axis=0)


def calc_momentum(prices_df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Calculates Intraday Momentum Factor with EWMA smoothing"""
    logger.info(f"Calculating Intraday Momentum (Window={window})...")
    mom = prices_df.pct_change(periods=window, fill_method=None)
    clean_mom = clean_factor_cross_sectionally(mom)

    # Apply EWMA to smooth signal spikes and significantly reduce turnover
    return clean_mom.ewm(span=10, adjust=False).mean()


def calc_low_volatility(prices_df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Calculates Low Volatility Factor (inverted standard deviation) with EWMA smoothing"""
    logger.info(f"Calculating Low Volatility (Window={window})...")

    # Multiply by -1 so that lower volatility yields a higher factor score
    vol = prices_df.pct_change(fill_method=None).rolling(window=window).std() * -1
    clean_vol = clean_factor_cross_sectionally(vol)

    return clean_vol.ewm(span=20, adjust=False).mean()


def dynamic_factor_synthesis(factors_dict: dict, prices_df: pd.DataFrame) -> pd.DataFrame:
    """Synthesizes the ultimate Quality-Momentum composite factor"""
    logger.info("Initializing Quality-Momentum Synthesis Engine...")
    combined_factor = pd.DataFrame(0.0, index=prices_df.index, columns=prices_df.columns)

    # Apply linear weights to the targeted factor pool
    if 'Momentum_420' in factors_dict:
        combined_factor += factors_dict['Momentum_420'] * 2.0
    if 'Momentum_140' in factors_dict:
        combined_factor += factors_dict['Momentum_140'] * 1.0
    if 'LowVol_90' in factors_dict:
        combined_factor += factors_dict['LowVol_90'] * 1.0

    logger.info("Factor synthesis complete. Re-standardizing the composite factor...")
    # Secondary cross-sectional cleaning ensures the final composite signal remains pure N(0,1)
    return clean_factor_cross_sectionally(combined_factor)