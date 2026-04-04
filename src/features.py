import pandas as pd
from .utils import logger


def clean_factor_cross_sectionally(raw_factor: pd.DataFrame) -> pd.DataFrame:
    """
    Cross-sectional factor cleaning pipeline:
      1. MAD Winsorization (5x MAD bounds) — robust to extreme outliers.
      2. Z-Score standardization to N(0, 1).
    """
    median = raw_factor.median(axis=1)
    mad = raw_factor.sub(median, axis=0).abs().median(axis=1)
    upper = median + 5 * mad
    lower = median - 5 * mad
    winsorized = raw_factor.clip(lower=lower, upper=upper, axis=0)

    mean = winsorized.mean(axis=1)
    std = winsorized.std(axis=1)
    return winsorized.sub(mean, axis=0).div(std, axis=0)


def calc_momentum(prices_df: pd.DataFrame, window: int) -> pd.DataFrame:
    """
    Intraday cross-sectional momentum factor.
    Raw signal: pct_change over `window` bars.
    Post-processing: MAD winsorization + Z-score + EWMA smoothing (span=10).
    """
    logger.info(f"Computing Momentum | window={window}")
    raw = prices_df.pct_change(periods=window, fill_method=None)
    cleaned = clean_factor_cross_sectionally(raw)
    return cleaned.ewm(span=10, adjust=False).mean()


def calc_low_volatility(prices_df: pd.DataFrame, window: int) -> pd.DataFrame:
    """
    Inverted rolling-volatility factor (low-vol premium).
    Raw signal: -std(returns, window).
    Post-processing: MAD winsorization + Z-score + EWMA smoothing (span=20).
    """
    logger.info(f"Computing Low Volatility | window={window}")
    raw = prices_df.pct_change(fill_method=None).rolling(window=window).std() * -1
    cleaned = clean_factor_cross_sectionally(raw)
    return cleaned.ewm(span=20, adjust=False).mean()


def dynamic_factor_synthesis(factors_dict: dict, prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Linearly combines individual alpha signals into a composite factor.
    Weights: Momentum_420 x2, Momentum_140 x1, LowVol_90 x1.
    Final pass: cross-sectional re-standardization to N(0, 1).
    """
    logger.info("Synthesizing composite factor...")
    combined = pd.DataFrame(0.0, index=prices_df.index, columns=prices_df.columns)

    weights = {
        "Momentum_420": 2.0,
        "Momentum_140": 1.0,
        "LowVol_90": 1.0,
    }

    for name, weight in weights.items():
        if name in factors_dict:
            combined += factors_dict[name] * weight

    logger.info("Re-standardizing composite factor...")
    return clean_factor_cross_sectionally(combined)
