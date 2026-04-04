import pandas as pd
import numpy as np
from .utils import logger

BARS_PER_YEAR_1H = 252 * 7


def run_realistic_backtest(
    prices_df: pd.DataFrame,
    factor_df: pd.DataFrame,
    holding_periods: int = 28,
    base_transaction_cost: float = 0.0002,
    stop_loss_pct: float = 0.08,
    vix_series: pd.Series = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Execute a vectorized market-neutral long-short backtest with realistic execution modeling.

    Pipeline:
        1. Cross-sectional ranking (long top decile, short bottom decile).
        2. Continuous VIX-based exposure scaling.
        3. Dynamic volatility targeting (15% annualized, max 1.5x leverage).
        4. Asymmetric hard stop-loss per position.
        5. TWAP execution simulation via rolling-window weight smoothing.
        6. Micro-structural slippage and transaction cost model.

    Args:
        prices_df: Wide-format hourly close prices.
        factor_df: Wide-format composite factor scores (same shape as prices_df).
        holding_periods: TWAP smoothing window (bars) and stop-loss lookback.
        base_transaction_cost: One-way cost per unit of turnover.
        stop_loss_pct: Maximum allowable drawdown per position before forced exit.
        vix_series: Optional hourly VIX series for macro risk scaling.

    Returns:
        Tuple of (results_df, portfolio_weights, metrics_dict).
    """
    logger.info("=== Realistic Vectorized Backtest (V17: Market-Neutral Long-Short) ===")

    delayed_factor = factor_df.shift(1)

    # --- Step 1: Cross-Sectional Ranking ---
    logger.info("Step 1 | Cross-sectional ranking (long top 10%, short bottom 10%)...")
    ranks = delayed_factor.rank(axis=1, pct=True, ascending=True)

    long_mask = ranks >= 0.90
    short_mask = ranks <= 0.10

    long_weights = long_mask.div(long_mask.sum(axis=1), axis=0).fillna(0)
    short_weights = short_mask.div(short_mask.sum(axis=1), axis=0).fillna(0) * -1.0
    raw_weights = long_weights + short_weights

    # --- Step 2: VIX Exposure Scaling ---
    logger.info("Step 2 | Applying continuous VIX defense scaling...")
    if vix_series is not None:
        aligned_vix = vix_series.reindex(prices_df.index).ffill()
        risk_scaling = (30.0 / aligned_vix).clip(upper=1.0, lower=0.0)
        target_weights = raw_weights.multiply(risk_scaling.shift(1).fillna(1.0), axis=0)
    else:
        target_weights = raw_weights

    # --- Step 3: Dynamic Volatility Targeting ---
    logger.info("Step 3 | Volatility targeting (target=15% ann., max leverage=1.5x)...")
    market_returns = prices_df.pct_change(1).mean(axis=1)
    rolling_ann_vol = market_returns.rolling(window=10, min_periods=5).std() * np.sqrt(BARS_PER_YEAR_1H)

    target_annual_vol = 0.15
    vol_multiplier = (target_annual_vol / (rolling_ann_vol + 1e-6)).clip(upper=1.5).fillna(1.0)
    risk_adjusted_weights = target_weights.multiply(vol_multiplier, axis=0)

    # --- Step 4: Asymmetric Hard Stop-Loss ---
    logger.info(f"Step 4 | Hard stop-loss at {stop_loss_pct:.0%}...")
    rolling_max = prices_df.rolling(window=holding_periods, min_periods=1).max()
    rolling_min = prices_df.rolling(window=holding_periods, min_periods=1).min()

    valid_long = ((prices_df / rolling_max) - 1.0) > -stop_loss_pct
    valid_short = (1.0 - (prices_df / rolling_min)) > -stop_loss_pct

    prev_valid_long = valid_long.shift(1).fillna(True)
    prev_valid_short = valid_short.shift(1).fillna(True)

    risk_adjusted_weights = risk_adjusted_weights.where(
        (risk_adjusted_weights <= 0) | prev_valid_long, 0
    )
    risk_adjusted_weights = risk_adjusted_weights.where(
        (risk_adjusted_weights >= 0) | prev_valid_short, 0
    )

    # --- Step 5: TWAP Execution Simulation ---
    logger.info("Step 5 | TWAP simulation via rolling weight smoothing...")
    portfolio_weights = risk_adjusted_weights.rolling(window=holding_periods, min_periods=1).mean()

    # --- Step 6: Cost Model ---
    logger.info("Step 6 | Applying micro-structural slippage and cost model...")
    stock_turnover = portfolio_weights.diff().abs()
    total_turnover = stock_turnover.sum(axis=1) / 2.0
    cost_series = (stock_turnover * base_transaction_cost).sum(axis=1)

    current_bar_returns = prices_df.pct_change(1).fillna(0)
    gross_returns = (portfolio_weights.shift(1) * current_bar_returns).sum(axis=1)
    net_returns = gross_returns - cost_series
    cumulative_returns = (1 + net_returns).cumprod()

    # --- Performance Metrics ---
    total_bars = len(cumulative_returns)

    # --- New Calculations ---
    total_return = cumulative_returns.iloc[-1] - 1.0 if total_bars > 0 else 0.0

    try:
        monthly_returns = net_returns.resample('ME').sum()
        avg_monthly_return = monthly_returns.mean()
    except TypeError:
        avg_monthly_return = net_returns.mean() * (BARS_PER_YEAR_1H / 12)

    gross_wins = gross_returns[gross_returns > 0].sum()
    gross_losses = abs(gross_returns[gross_returns < 0].sum())
    profit_factor = gross_wins / gross_losses if gross_losses != 0 else float('inf')

    expectancy = net_returns.mean()

    total_gross_profit = gross_returns.sum()
    total_turnover_units = stock_turnover.sum(axis=1).sum()
    break_even_cost = total_gross_profit / total_turnover_units if total_turnover_units != 0 else 0

    # --- Original Calculations ---
    if total_bars > 0 and cumulative_returns.iloc[-1] > 0:
        cagr = (cumulative_returns.iloc[-1] ** (BARS_PER_YEAR_1H / total_bars)) - 1
    else:
        cagr = net_returns.mean() * BARS_PER_YEAR_1H

    ann_volatility = net_returns.std() * np.sqrt(BARS_PER_YEAR_1H)
    sharpe_ratio = cagr / ann_volatility if ann_volatility != 0 else 0

    rolling_max_eq = cumulative_returns.cummax()
    drawdowns = (cumulative_returns - rolling_max_eq) / rolling_max_eq
    max_drawdown = drawdowns.min()

    win_rate = (
        (net_returns > 0).sum() / (net_returns != 0).sum()
        if (net_returns != 0).sum() > 0
        else 0
    )

    downside_returns = net_returns[net_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(BARS_PER_YEAR_1H)
    sortino_ratio = cagr / downside_vol if downside_vol != 0 else 0
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0

    # --- Combined Metrics Dictionary ---
    metrics_dict = {
        # --- Original Metrics ---
        "Geometric CAGR": f"{cagr:.4%}",
        "Annualized Volatility": f"{ann_volatility:.4%}",
        "Sharpe Ratio": f"{sharpe_ratio:.4f}",
        "Sortino Ratio": f"{sortino_ratio:.4f}",
        "Calmar Ratio": f"{calmar_ratio:.4f}",
        "Max Drawdown": f"{max_drawdown:.4%}",
        "Win Rate (Per Bar)": f"{win_rate:.4%}",
        "Average Turnover (Per Bar)": f"{total_turnover.mean():.4%}",

        # --- New Absolute Return Metrics ---
        "Total Period Return": f"{total_return:.4%}",
        "Average Monthly Profit": f"{avg_monthly_return:.4%}",

        # --- New High-Frequency Diagnostics ---
        "Profit Factor": f"{profit_factor:.4f}",
        "Expectancy (Per Bar)": f"{expectancy:.6%}",
        "Break-Even Cost": f"{break_even_cost:.6f} ({break_even_cost * 10000:.1f} bps)",
    }

    logger.info("=" * 55)
    logger.info("BACKTEST PERFORMANCE SUMMARY (V17 L/S)")
    logger.info("=" * 55)
    for k, v in metrics_dict.items():
        logger.info(f"  {k:<32}: {v}")
    logger.info("=" * 55)

    results_df = pd.DataFrame({
        "Gross Return": gross_returns,
        "Friction Costs": cost_series,
        "Net Return": net_returns,
        "Equity Curve": cumulative_returns,
        "Drawdown": drawdowns,
        "Turnover": total_turnover,
    })

    return results_df, portfolio_weights, metrics_dict