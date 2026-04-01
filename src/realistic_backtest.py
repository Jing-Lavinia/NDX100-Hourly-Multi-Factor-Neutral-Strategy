import pandas as pd
import numpy as np
from .utils import logger

def run_realistic_backtest(prices_df: pd.DataFrame, factor_df: pd.DataFrame,
                           holding_periods: int = 28,
                           base_transaction_cost: float = 0.0002,
                           stop_loss_pct: float = 0.08,
                           vix_series: pd.Series = None):
    logger.info("=== Starting Realistic Vectorized Backtest (V17: Market Neutral Long-Short) ===")

    delayed_factor = factor_df.shift(1)

    # 1. Cross-Sectional Ranking (Long Top 10%, Short Bottom 10%)
    logger.info("Applying Cross-Sectional Ranking...")
    ranks = delayed_factor.rank(axis=1, pct=True, ascending=True)

    long_mask = ranks >= 0.90
    short_mask = ranks <= 0.10

    long_weights = long_mask.div(long_mask.sum(axis=1), axis=0).fillna(0)
    short_weights = short_mask.div(short_mask.sum(axis=1), axis=0).fillna(0) * -1.0

    raw_weights = long_weights + short_weights

    # 2. Continuous VIX Defense Mechanism
    logger.info("Applying Continuous VIX Defense Mechanism...")
    if vix_series is not None:
        aligned_vix = vix_series.reindex(prices_df.index).ffill()
        # Smoothly deleverage when VIX > 30.0
        risk_scaling = (30.0 / aligned_vix).clip(upper=1.0, lower=0.0)
        delayed_scaling = risk_scaling.shift(1).fillna(1.0)
        target_weights = raw_weights.multiply(delayed_scaling, axis=0)
    else:
        target_weights = raw_weights

    # 3. Dynamic Volatility Targeting
    logger.info("Applying Volatility Targeting...")
    market_returns = prices_df.pct_change(1).mean(axis=1)
    bars_per_year_1h = 252 * 7
    rolling_ann_vol = market_returns.rolling(window=10, min_periods=5).std() * np.sqrt(bars_per_year_1h)

    target_annual_vol = 0.15
    vol_multiplier = (target_annual_vol / (rolling_ann_vol + 1e-6)).clip(upper=1.5).fillna(1.0)
    risk_adjusted_target_weights = target_weights.multiply(vol_multiplier, axis=0)

    # 4. Asymmetric Hard Stop-Loss
    logger.info(f"Applying Hard Stop-Loss mechanism at {stop_loss_pct * 100}%...")
    rolling_max = prices_df.rolling(window=holding_periods, min_periods=1).max()
    long_drawdown = (prices_df / rolling_max) - 1.0

    rolling_min = prices_df.rolling(window=holding_periods, min_periods=1).min()
    short_drawdown = 1.0 - (prices_df / rolling_min)

    valid_long = long_drawdown > -stop_loss_pct
    valid_short = short_drawdown > -stop_loss_pct

    # Force position to zero if stop-loss threshold is breached
    risk_adjusted_target_weights = risk_adjusted_target_weights.where(
        (risk_adjusted_target_weights <= 0) | valid_long.shift(1).fillna(True), 0
    )
    risk_adjusted_target_weights = risk_adjusted_target_weights.where(
        (risk_adjusted_target_weights >= 0) | valid_short.shift(1).fillna(True), 0
    )

    # 5. Order Flow Smoothing (TWAP Simulation)
    portfolio_weights = risk_adjusted_target_weights.rolling(window=holding_periods, min_periods=1).mean()

    # 6. Micro-Execution Slippage & Cost Model
    logger.info("Applying Micro-Execution Slippage Model...")
    stock_turnover = portfolio_weights.diff().abs()
    total_turnover = stock_turnover.sum(axis=1) / 2.0

    current_bar_returns = prices_df.pct_change(1).fillna(0)

    cost_series = (stock_turnover * base_transaction_cost).sum(axis=1)
    gross_returns = (portfolio_weights.shift(1) * current_bar_returns).sum(axis=1)
    net_returns = gross_returns - cost_series

    cumulative_returns = (1 + net_returns).cumprod()

    # 7. Performance Metrics Evaluation
    total_bars = len(cumulative_returns)
    if total_bars > 0 and cumulative_returns.iloc[-1] > 0:
        cagr = (cumulative_returns.iloc[-1] ** (bars_per_year_1h / total_bars)) - 1
    else:
        cagr = net_returns.mean() * bars_per_year_1h

    ann_volatility = net_returns.std() * np.sqrt(bars_per_year_1h)
    sharpe_ratio = cagr / ann_volatility if ann_volatility != 0 else 0

    rolling_max_eq = cumulative_returns.cummax()
    drawdowns = (cumulative_returns - rolling_max_eq) / rolling_max_eq
    max_drawdown = drawdowns.min()

    win_rate = (net_returns > 0).sum() / (net_returns != 0).sum() if (net_returns != 0).sum() > 0 else 0

    downside_returns = net_returns[net_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(bars_per_year_1h)
    sortino_ratio = cagr / downside_vol if downside_vol != 0 else 0

    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0

    avg_turnover = total_turnover.mean()

    metrics_dict = {
        "Geometric CAGR": f"{cagr:.4%}",
        "Annualized Volatility": f"{ann_volatility:.4%}",
        "Sharpe Ratio": f"{sharpe_ratio:.4f}",
        "Sortino Ratio": f"{sortino_ratio:.4f}",
        "Calmar Ratio": f"{calmar_ratio:.4f}",
        "Max Drawdown": f"{max_drawdown:.4%}",
        "Win Rate (Per Bar)": f"{win_rate:.4%}",
        "Average Turnover (Per Bar)": f"{avg_turnover:.4%}",
    }

    logger.info("=========================================")
    logger.info("📊 REALISTIC BACKTEST PERFORMANCE (V17 L/S)")
    logger.info("=========================================")
    for k, v in metrics_dict.items():
        logger.info(f"{k:<30}: {v}")
    logger.info("=========================================")

    results_df = pd.DataFrame({
        'Gross Return': gross_returns,
        'Friction Costs': cost_series,
        'Net Return': net_returns,
        'Equity Curve': cumulative_returns,
        'Drawdown': drawdowns,
        'Turnover': total_turnover
    })

    return results_df, portfolio_weights, metrics_dict