import pandas as pd
import alphalens
from .utils import logger


def _compute_forward_returns(prices: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    """
    Manually compute forward returns to bypass Alphalens frequency-inference bugs.

    Args:
        prices: Wide-format price DataFrame (index=datetime, columns=tickers).
        periods: List of bar-count horizons.

    Returns:
        Long-format DataFrame with columns named '{n}H'.
    """
    stacked = []
    for period in periods:
        ret = prices.pct_change(period, fill_method=None).shift(-period).stack()
        ret.name = f"{period}D"
        stacked.append(ret)

    forward_returns = pd.concat(stacked, axis=1)
    forward_returns.index.names = ["date", "asset"]
    return forward_returns


def prepare_alphalens_data(
    prices: pd.DataFrame,
    factor: pd.DataFrame,
    sector_map: dict,
) -> pd.DataFrame:
    """
    Format factor and price data for Alphalens ingestion.

    Args:
        prices: Wide-format price DataFrame.
        factor: Wide-format factor score DataFrame.
        sector_map: Dict mapping ticker -> sector string.

    Returns:
        Alphalens-compatible clean_factor_data DataFrame.
    """
    logger.info("Preparing Alphalens input data...")

    factor_stacked = factor.stack()
    factor_stacked.index.names = ["date", "asset"]

    tickers = factor_stacked.index.get_level_values("asset")
    sector_series = tickers.map(sector_map).fillna("Others")

    sector_labels, sector_names = pd.factorize(pd.Series(sector_series, index=factor_stacked.index))
    sector_indexed = pd.Series(sector_labels, index=factor_stacked.index)
    sector_mapping = dict(enumerate(sector_names))

    logger.info("Computing forward returns (manual, bypassing Alphalens frequency bug)...")
    forward_returns = _compute_forward_returns(prices, [1, 6, 12])

    logger.info("Merging factor with forward returns via Alphalens...")
    factor_data = alphalens.utils.get_clean_factor(
        factor=factor_stacked,
        forward_returns=forward_returns,
        groupby=sector_indexed,
        groupby_labels=sector_mapping,
        quantiles=5,
        max_loss=0.35,
    )

    logger.info("Alphalens data preparation complete.")
    return factor_data
