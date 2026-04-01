import pandas as pd
import alphalens
from .utils import logger


def custom_forward_returns(prices, periods):
    """Manually calculate forward returns to bypass Alphalens frequency inference bug."""
    returns_list = []
    for period in periods:
        ret = prices.pct_change(period, fill_method=None).shift(-period)
        stacked_ret = ret.stack()
        # Format string required by Alphalens (e.g., '1D', '6D')
        stacked_ret.name = f"{period}D"
        returns_list.append(stacked_ret)

    forward_returns = pd.concat(returns_list, axis=1)
    forward_returns.index.names = ['date', 'asset']
    return forward_returns


def prepare_alphalens_data(prices: pd.DataFrame, factor: pd.DataFrame, sector_map: dict):
    """Formats factor and price data to ensure compatibility with Alphalens."""
    logger.info("Formatting factor data for Alphalens...")

    factor_stacked = factor.stack()
    factor_stacked.index.names = ['date', 'asset']

    tickers = factor_stacked.index.get_level_values('asset')
    sectors = tickers.map(sector_map).fillna('Others')

    sector_series = pd.Series(sectors, index=factor_stacked.index)
    sector_labels, sector_names = pd.factorize(sector_series)

    sector_series_indexed = pd.Series(sector_labels, index=factor_stacked.index)
    sector_mapping = dict(enumerate(sector_names))

    logger.info("Bypassing Alphalens frequency bug with custom forward returns...")
    forward_returns = custom_forward_returns(prices, [1, 6, 12])

    logger.info("Merging factor and forward returns...")
    factor_data = alphalens.utils.get_clean_factor(
        factor=factor_stacked,
        forward_returns=forward_returns,
        groupby=sector_series_indexed,
        groupby_labels=sector_mapping,
        quantiles=5,
        max_loss=0.35
    )
    logger.info("Alphalens data preparation completed!")

    return factor_data