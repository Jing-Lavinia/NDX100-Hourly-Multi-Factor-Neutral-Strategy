import io
from contextlib import redirect_stdout
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import alphalens as al

from . import config
from .utils import logger

# ---------------------------------------------------------------------------
# Styling constants
# ---------------------------------------------------------------------------
DARK_BG = "#0d1117"
PANEL_BG = "#161b22"
ACCENT = "#58a6ff"
ACCENT2 = "#3fb950"
ACCENT3 = "#f78166"
ACCENT4 = "#d2a8ff"
TEXT_LIGHT = "#e6edf3"
TEXT_DIM = "#8b949e"
GRID_COLOR = "#21262d"
LINE_WIDTH = 1.5

_BASE_RC = {
    "figure.facecolor": DARK_BG,
    "axes.facecolor": PANEL_BG,
    "axes.edgecolor": GRID_COLOR,
    "axes.labelcolor": TEXT_LIGHT,
    "axes.titlecolor": TEXT_LIGHT,
    "axes.grid": True,
    "grid.color": GRID_COLOR,
    "grid.linewidth": 0.6,
    "xtick.color": TEXT_DIM,
    "ytick.color": TEXT_DIM,
    "text.color": TEXT_LIGHT,
    "legend.facecolor": PANEL_BG,
    "legend.edgecolor": GRID_COLOR,
    "legend.labelcolor": TEXT_LIGHT,
    "font.family": "monospace",
    "figure.dpi": 150,
}


def _apply_style() -> None:
    pass


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info(f"  Saved → {path.relative_to(config.REPORTS_DIR)}")


# ---------------------------------------------------------------------------
# Alphalens standard reports
# ---------------------------------------------------------------------------

def generate_all_reports(clean_factor_data: pd.DataFrame) -> None:
    """
    Render standard Alphalens visualizations and extract tear-sheet summaries.
    Covers returns, IC, and turnover dimensions.
    """
    logger.info("=" * 52)
    logger.info("Alphalens Visualization Pipeline")
    logger.info("=" * 52)

    plots_dir = config.REPORTS_DIR / "plots"
    tables_dir = config.REPORTS_DIR / "tables"
    for sub in ["01_returns", "02_ic", "03_turnover"]:
        (plots_dir / sub).mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Returns
    logger.info("Rendering returns analysis...")
    mean_ret_quantile, _ = al.performance.mean_return_by_quantile(
        clean_factor_data, by_date=False, by_group=True
    )
    mean_ret_quantile.to_csv(tables_dir / "01_returns_mean_by_quantile.csv")

    mean_ret_quant_daily, _ = al.performance.mean_return_by_quantile(
        clean_factor_data, by_date=True, by_group=False
    )

    al.plotting.plot_quantile_returns_bar(mean_ret_quantile, by_group=True)
    plt.gcf().savefig(plots_dir / "01_returns" / "01_quantile_returns_bar.png", bbox_inches="tight", dpi=150)
    plt.close("all")

    for period in config.FORWARD_PERIODS:
        al.plotting.plot_cumulative_returns_by_quantile(mean_ret_quant_daily, period=f"{period}D")
        plt.gcf().savefig(
            plots_dir / "01_returns" / f"02_cumulative_returns_{period}D.png",
            bbox_inches="tight", dpi=150,
        )
        plt.close("all")

    # IC
    logger.info("Rendering IC analysis...")
    ic = al.performance.factor_information_coefficient(clean_factor_data)
    ic.to_csv(tables_dir / "02_ic_timeseries.csv")

    for plot_fn, fname in [
        (al.plotting.plot_ic_ts, "01_ic_timeseries.png"),
        (al.plotting.plot_ic_hist, "02_ic_histogram.png"),
        (al.plotting.plot_ic_qq, "03_ic_qq_plot.png"),
    ]:
        plot_fn(ic)
        plt.gcf().savefig(plots_dir / "02_ic" / fname, bbox_inches="tight", dpi=150)
        plt.close("all")

    # Turnover
    logger.info("Rendering turnover analysis...")
    fra = al.performance.factor_rank_autocorrelation(clean_factor_data)
    fra.to_csv(tables_dir / "03_turnover_fra.csv")

    al.plotting.plot_factor_rank_auto_correlation(fra)
    plt.gcf().savefig(plots_dir / "03_turnover" / "01_factor_rank_autocorrelation.png", bbox_inches="tight", dpi=150)
    plt.close("all")

    # Tear-sheet summaries
    logger.info("Extracting statistical tear-sheet summaries...")
    buf = io.StringIO()
    orig_show = plt.show
    plt.show = lambda: None
    try:
        with redirect_stdout(buf):
            al.tears.create_returns_tear_sheet(clean_factor_data, by_group=True)
            print("\n" + "=" * 50 + "\n")
            al.tears.create_information_tear_sheet(clean_factor_data, by_group=True)
    finally:
        plt.show = orig_show
        plt.close("all")

    with open(config.REPORTS_DIR / "summary_metrics.txt", "w") as f:
        f.write(buf.getvalue())

    logger.info(f"Alphalens pipeline complete | output={config.REPORTS_DIR / 'plots'}")


# ---------------------------------------------------------------------------
# Equity curve + benchmark
# ---------------------------------------------------------------------------

def render_equity_curve(
    results: pd.DataFrame,
    benchmark_path: Path,
    output_dir: Path,
) -> None:
    """Render strategy equity curve against QQQ benchmark."""
    logger.info("Rendering strategy vs benchmark equity curve...")
    _apply_style()

    benchmark_curve = _load_benchmark(benchmark_path, results.index)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]})
    fig.subplots_adjust(hspace=0.08)

    ax_eq, ax_dd = axes
    eq = results["Equity Curve"]

    ax_eq.plot(eq.index, eq.values, color=ACCENT, lw=LINE_WIDTH, label="Strategy (V17 L/S)")
    if benchmark_curve is not None:
        ax_eq.plot(
            benchmark_curve.index, benchmark_curve.values,
            color=TEXT_DIM, lw=LINE_WIDTH, ls="--", alpha=0.7, label="QQQ Benchmark",
        )
    ax_eq.set_ylabel("Cumulative Return", fontsize=9)
    ax_eq.set_title("Strategy Performance vs Nasdaq 100 Benchmark  (1H, Net of Fees)", fontsize=11, pad=10)
    ax_eq.legend(fontsize=8)
    ax_eq.set_xticklabels([])

    ax_dd.fill_between(
        results.index, results["Drawdown"].values, 0,
        color=ACCENT3, alpha=0.6, label="Drawdown",
    )
    ax_dd.set_ylabel("Drawdown", fontsize=9)
    ax_dd.set_xlabel("")
    ax_dd.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=0))

    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    output_dir.mkdir(parents=True, exist_ok=True)
    _save(fig, output_dir / "equity_curve_with_benchmark.png")


def _load_benchmark(benchmark_path: Path, strategy_index: pd.Index) -> pd.Series | None:
    if not benchmark_path.exists():
        print(f"\n[error] can not find benchmark data: {benchmark_path.absolute()}\n")
        return None
    try:
        df = pd.read_csv(benchmark_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.set_index("timestamp", inplace=True)
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
        qqq_1h = df.between_time("09:30", "15:59").resample("1h").agg({"close": "last"}).dropna()
        aligned = qqq_1h.reindex(strategy_index).ffill()
        returns = aligned["close"].pct_change().fillna(0)
        return (1 + returns).cumprod()
    except Exception as exc:
        logger.warning(f"Benchmark load failed: {exc}")
        print(f"\n[error] reason: {exc}\n")
        return None


# ---------------------------------------------------------------------------
# Extended analytics dashboard
# ---------------------------------------------------------------------------

def render_performance_dashboard(results: pd.DataFrame, output_dir: Path) -> None:
    """
    Comprehensive single-page performance dashboard covering:
      - Net return distribution
      - Rolling Sharpe (annualized, 30-bar window)
      - Rolling volatility
      - Turnover time-series
      - Return autocorrelation
      - Monthly P&L heatmap
    """
    logger.info("Rendering performance dashboard...")
    _apply_style()

    fig = plt.figure(figsize=(18, 14))
    fig.suptitle("Strategy Performance Dashboard  |  V17 Market-Neutral L/S", fontsize=13, y=0.98)
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

    net_ret = results["Net Return"]
    ann_factor = config.__dict__.get("BARS_PER_YEAR_1H", 252 * 7)

    # 1. Return distribution
    ax1 = fig.add_subplot(gs[0, 0])
    _plot_return_distribution(ax1, net_ret)

    # 2. Rolling Sharpe
    ax2 = fig.add_subplot(gs[0, 1])
    _plot_rolling_sharpe(ax2, net_ret, window=30, ann_factor=ann_factor)

    # 3. Rolling volatility
    ax3 = fig.add_subplot(gs[0, 2])
    _plot_rolling_volatility(ax3, net_ret, window=30, ann_factor=ann_factor)

    # 4. Turnover
    ax4 = fig.add_subplot(gs[1, 0])
    _plot_turnover(ax4, results["Turnover"])

    # 5. Autocorrelation of returns
    ax5 = fig.add_subplot(gs[1, 1])
    _plot_return_autocorrelation(ax5, net_ret, lags=20)

    # 6. Monthly P&L heatmap
    ax6 = fig.add_subplot(gs[1, 2])
    _plot_monthly_pnl_heatmap(ax6, net_ret)

    # 7. Gross vs Net
    ax7 = fig.add_subplot(gs[2, 0:2])
    _plot_gross_vs_net(ax7, results)

    # 8. Cost decomposition
    ax8 = fig.add_subplot(gs[2, 2])
    _plot_cost_decomposition(ax8, results)

    output_dir.mkdir(parents=True, exist_ok=True)
    _save(fig, output_dir / "performance_dashboard.png")


def _plot_return_distribution(ax: plt.Axes, net_ret: pd.Series) -> None:
    ax.set_title("Net Return Distribution", fontsize=9)
    data = net_ret.dropna()
    ax.hist(data, bins=60, color=ACCENT, alpha=0.75, edgecolor="none")
    ax.axvline(data.mean(), color=ACCENT2, lw=1.2, ls="--", label=f"Mean={data.mean():.4%}")
    ax.axvline(0, color=TEXT_DIM, lw=0.8, ls=":")
    ax.set_xlabel("Return per Bar", fontsize=8)
    ax.set_ylabel("Frequency", fontsize=8)
    ax.legend(fontsize=7)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=2))


def _plot_rolling_sharpe(ax: plt.Axes, net_ret: pd.Series, window: int, ann_factor: int) -> None:
    ax.set_title(f"Rolling Sharpe Ratio  (window={window})", fontsize=9)
    roll_mean = net_ret.rolling(window).mean()
    roll_std = net_ret.rolling(window).std()
    rolling_sharpe = (roll_mean / (roll_std + 1e-9)) * np.sqrt(ann_factor)
    ax.plot(rolling_sharpe.index, rolling_sharpe.values, color=ACCENT4, lw=1.2)
    ax.axhline(0, color=TEXT_DIM, lw=0.8, ls=":")
    ax.axhline(1, color=ACCENT2, lw=0.8, ls="--", alpha=0.6, label="Sharpe=1")
    ax.set_ylabel("Annualized Sharpe", fontsize=8)
    ax.legend(fontsize=7)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))


def _plot_rolling_volatility(ax: plt.Axes, net_ret: pd.Series, window: int, ann_factor: int) -> None:
    ax.set_title(f"Rolling Annualized Volatility  (window={window})", fontsize=9)
    roll_vol = net_ret.rolling(window).std() * np.sqrt(ann_factor)
    ax.plot(roll_vol.index, roll_vol.values, color=ACCENT3, lw=1.2)
    ax.axhline(0.15, color=ACCENT2, lw=0.8, ls="--", alpha=0.6, label="Target 15%")
    ax.set_ylabel("Ann. Volatility", fontsize=8)
    ax.legend(fontsize=7)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=0))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))


def _plot_turnover(ax: plt.Axes, turnover: pd.Series) -> None:
    ax.set_title("Portfolio Turnover per Bar", fontsize=9)
    ax.plot(turnover.index, turnover.values, color=ACCENT, lw=0.8, alpha=0.8)
    ax.fill_between(turnover.index, turnover.values, 0, color=ACCENT, alpha=0.2)
    mean_to = turnover.mean()
    ax.axhline(mean_to, color=ACCENT2, lw=1.0, ls="--", label=f"Mean={mean_to:.3%}")
    ax.set_ylabel("Turnover", fontsize=8)
    ax.legend(fontsize=7)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))


def _plot_return_autocorrelation(ax: plt.Axes, net_ret: pd.Series, lags: int = 20) -> None:
    ax.set_title(f"Return Autocorrelation  (lags 1–{lags})", fontsize=9)
    data = net_ret.dropna()
    acf = [data.autocorr(lag=lag) for lag in range(1, lags + 1)]
    x = np.arange(1, lags + 1)
    colors = [ACCENT2 if v >= 0 else ACCENT3 for v in acf]
    ax.bar(x, acf, color=colors, alpha=0.8, width=0.6)
    ci = 1.96 / np.sqrt(len(data))
    ax.axhline(ci, color=TEXT_DIM, lw=0.8, ls="--")
    ax.axhline(-ci, color=TEXT_DIM, lw=0.8, ls="--")
    ax.axhline(0, color=TEXT_DIM, lw=0.5)
    ax.set_xlabel("Lag (bars)", fontsize=8)
    ax.set_ylabel("Autocorrelation", fontsize=8)


def _plot_monthly_pnl_heatmap(ax: plt.Axes, net_ret: pd.Series) -> None:
    ax.set_title("Monthly P&L Heatmap", fontsize=9)
    monthly = net_ret.resample("ME").sum()
    if monthly.empty:
        ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center", transform=ax.transAxes)
        return

    monthly_df = monthly.to_frame("pnl")
    monthly_df["year"] = monthly_df.index.year
    monthly_df["month"] = monthly_df.index.month

    pivot = monthly_df.pivot(index="year", columns="month", values="pnl")
    pivot.columns = [f"M{m}" for m in pivot.columns]

    vmax = max(abs(pivot.values[np.isfinite(pivot.values)]).max(), 1e-9)
    im = ax.imshow(
        pivot.values,
        aspect="auto",
        cmap="RdYlGn",
        vmin=-vmax,
        vmax=vmax,
    )
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=7, rotation=45)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index.astype(str), fontsize=7)

    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            val = pivot.values[r, c]
            if np.isfinite(val):
                ax.text(c, r, f"{val:.1%}", ha="center", va="center", fontsize=6.5,
                        color="black" if abs(val) < vmax * 0.6 else "white")
    plt.colorbar(im, ax=ax, fraction=0.03)


def _plot_gross_vs_net(ax: plt.Axes, results: pd.DataFrame) -> None:
    ax.set_title("Cumulative Gross vs Net Returns", fontsize=9)
    gross_cum = (1 + results["Gross Return"]).cumprod()
    net_cum = results["Equity Curve"]
    ax.plot(gross_cum.index, gross_cum.values, color=ACCENT, lw=1.2, label="Gross")
    ax.plot(net_cum.index, net_cum.values, color=ACCENT2, lw=1.2, ls="--", label="Net (after costs)")
    ax.fill_between(gross_cum.index, gross_cum.values, net_cum.values, color=ACCENT3, alpha=0.25, label="Cost drag")
    ax.set_ylabel("Cumulative Return", fontsize=8)
    ax.legend(fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))


def _plot_cost_decomposition(ax: plt.Axes, results: pd.DataFrame) -> None:
    ax.set_title("Cumulative Cost Drag", fontsize=9)
    cum_cost = results["Friction Costs"].cumsum()
    ax.plot(cum_cost.index, cum_cost.values, color=ACCENT3, lw=1.2)
    ax.fill_between(cum_cost.index, cum_cost.values, 0, color=ACCENT3, alpha=0.3)
    ax.set_ylabel("Cumulative Cost", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=2))


# ---------------------------------------------------------------------------
# Risk decomposition panel
# ---------------------------------------------------------------------------

def render_risk_decomposition(
    results: pd.DataFrame,
    portfolio_weights: pd.DataFrame,
    output_dir: Path,
) -> None:
    """
    Multi-panel risk analytics:
      - Long/short gross exposure over time
      - Net exposure (beta proxy)
      - Cross-sectional position concentration (HHI)
      - Rolling win-rate
    """
    logger.info("Rendering risk decomposition panel...")
    _apply_style()

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle("Risk Decomposition  |  V17 Market-Neutral L/S", fontsize=12, y=0.99)

    ax_exp, ax_net, ax_hhi, ax_wr = axes.flatten()

    long_exp = portfolio_weights.clip(lower=0).sum(axis=1)
    short_exp = portfolio_weights.clip(upper=0).sum(axis=1).abs()
    net_exp = portfolio_weights.sum(axis=1)

    # Long/Short gross exposure
    ax_exp.set_title("Long / Short Gross Exposure", fontsize=9)
    ax_exp.plot(long_exp.index, long_exp.values, color=ACCENT2, lw=1.2, label="Long")
    ax_exp.plot(short_exp.index, short_exp.values, color=ACCENT3, lw=1.2, label="Short")
    ax_exp.fill_between(long_exp.index, long_exp.values, color=ACCENT2, alpha=0.15)
    ax_exp.fill_between(short_exp.index, short_exp.values, color=ACCENT3, alpha=0.15)
    ax_exp.legend(fontsize=8)
    ax_exp.set_ylabel("Exposure (Gross)", fontsize=8)
    ax_exp.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # Net exposure
    ax_net.set_title("Net Portfolio Exposure (Beta Proxy)", fontsize=9)
    ax_net.plot(net_exp.index, net_exp.values, color=ACCENT4, lw=1.2)
    ax_net.fill_between(net_exp.index, net_exp.values, 0, color=ACCENT4, alpha=0.25)
    ax_net.axhline(0, color=TEXT_DIM, lw=0.8, ls="--")
    ax_net.set_ylabel("Net Exposure", fontsize=8)
    ax_net.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # Concentration (HHI of absolute weights)
    abs_w = portfolio_weights.abs()
    total_w = abs_w.sum(axis=1).replace(0, np.nan)
    normalized_w = abs_w.div(total_w, axis=0)
    hhi = (normalized_w ** 2).sum(axis=1)

    ax_hhi.set_title("Position Concentration (HHI)", fontsize=9)
    ax_hhi.plot(hhi.index, hhi.values, color=ACCENT, lw=1.2)
    ax_hhi.fill_between(hhi.index, hhi.values, 0, color=ACCENT, alpha=0.2)
    ax_hhi.set_ylabel("Herfindahl-Hirschman Index", fontsize=8)
    ax_hhi.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # Rolling win rate
    net_ret = results["Net Return"]
    win = (net_ret > 0).astype(float)
    rolling_wr = win.rolling(window=30).mean()

    ax_wr.set_title("Rolling Win Rate  (30-bar)", fontsize=9)
    ax_wr.plot(rolling_wr.index, rolling_wr.values, color=ACCENT2, lw=1.2)
    ax_wr.axhline(0.5, color=TEXT_DIM, lw=0.8, ls="--", label="50%")
    ax_wr.fill_between(rolling_wr.index, rolling_wr.values, 0.5,
                       where=(rolling_wr.values >= 0.5), color=ACCENT2, alpha=0.25)
    ax_wr.fill_between(rolling_wr.index, rolling_wr.values, 0.5,
                       where=(rolling_wr.values < 0.5), color=ACCENT3, alpha=0.25)
    ax_wr.set_ylabel("Win Rate", fontsize=8)
    ax_wr.legend(fontsize=7)
    ax_wr.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=0))
    ax_wr.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    output_dir.mkdir(parents=True, exist_ok=True)
    _save(fig, output_dir / "risk_decomposition.png")


# ---------------------------------------------------------------------------
# Factor signal diagnostic
# ---------------------------------------------------------------------------

def render_factor_diagnostics(
    factor_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """
    Factor health diagnostics:
      - Cross-sectional signal dispersion over time (std of z-scores)
      - Average factor score per decile
      - Factor score vs next-bar return scatter (sampled)
      - Top/Bottom basket spread series
    """
    logger.info("Rendering factor diagnostics...")
    _apply_style()

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle("Factor Signal Diagnostics  |  V17 Composite Factor", fontsize=12, y=0.99)

    ax_disp, ax_decile, ax_scatter, ax_spread = axes.flatten()

    fwd_ret_1 = prices_df.pct_change(1).shift(-1)
    common_idx = factor_df.index.intersection(fwd_ret_1.index)
    factor_aligned = factor_df.loc[common_idx]
    fwd_aligned = fwd_ret_1.loc[common_idx]

    # Signal Coverage
    ax_disp.set_title("Signal Coverage (Active Assets Count)", fontsize=9)
    coverage = factor_aligned.count(axis=1)
    ax_disp.plot(coverage.index, coverage.values, color=ACCENT4, lw=1.2)
    ax_disp.fill_between(coverage.index, coverage.values, 0, color=ACCENT4, alpha=0.2)
    ax_disp.set_ylabel("Valid Asset Count", fontsize=8)
    ax_disp.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # Average signal by decile (sampled from last available timestamp)
    ax_decile.set_title("Factor Score Distribution by Decile", fontsize=9)
    last_scores = factor_aligned.iloc[-1].dropna().sort_values()
    n = len(last_scores)
    decile_labels = pd.cut(range(n), bins=10, labels=False)
    decile_means = [last_scores.iloc[decile_labels == d].mean() for d in range(10)]
    colors = [ACCENT3 if v < 0 else ACCENT2 for v in decile_means]
    ax_decile.bar(range(1, 11), decile_means, color=colors, alpha=0.8, width=0.7)
    ax_decile.axhline(0, color=TEXT_DIM, lw=0.8)
    ax_decile.set_xlabel("Decile", fontsize=8)
    ax_decile.set_ylabel("Avg Factor Score", fontsize=8)
    ax_decile.set_xticks(range(1, 11))

    # Factor score vs forward 1-bar return (sampled, max 2000 points)
    ax_scatter.set_title("Factor Score vs Next-Bar Return", fontsize=9)
    sample_size = min(2000, factor_aligned.size)
    flat_factor = factor_aligned.stack().dropna()
    flat_fwd = fwd_aligned.stack().dropna()
    common = flat_factor.index.intersection(flat_fwd.index)
    if len(common) > 0:
        sampled = np.random.choice(len(common), size=min(sample_size, len(common)), replace=False)
        x = flat_factor.loc[common].iloc[sampled].values
        y = flat_fwd.loc[common].iloc[sampled].values
        ax_scatter.scatter(x, y, alpha=0.15, s=4, color=ACCENT)
        m, b = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 100)
        ax_scatter.plot(xs, m * xs + b, color=ACCENT2, lw=1.5, label=f"slope={m:.4f}")
        ax_scatter.legend(fontsize=7)
    ax_scatter.set_xlabel("Factor Score", fontsize=8)
    ax_scatter.set_ylabel("Fwd 1-Bar Return", fontsize=8)
    ax_scatter.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=2))

    # Top vs Bottom decile spread
    ax_spread.set_title("Top vs Bottom Decile Daily Spread", fontsize=9)
    ranks = factor_aligned.rank(axis=1, pct=True)
    top_ret = fwd_aligned[ranks >= 0.9].mean(axis=1)
    bot_ret = fwd_aligned[ranks <= 0.1].mean(axis=1)
    spread = top_ret - bot_ret
    spread_cum = (1 + spread.fillna(0)).cumprod()
    ax_spread.plot(spread_cum.index, spread_cum.values, color=ACCENT2, lw=1.2)
    ax_spread.fill_between(spread_cum.index, spread_cum.values, 1, color=ACCENT2, alpha=0.2)
    ax_spread.axhline(1, color=TEXT_DIM, lw=0.8, ls="--")
    ax_spread.set_ylabel("Cumulative Spread Return", fontsize=8)
    ax_spread.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    output_dir.mkdir(parents=True, exist_ok=True)
    _save(fig, output_dir / "factor_diagnostics.png")


# ---------------------------------------------------------------------------
# Drawdown analysis panel
# ---------------------------------------------------------------------------

def render_drawdown_analysis(results: pd.DataFrame, output_dir: Path) -> None:
    """
    Detailed drawdown analytics:
      - Underwater equity curve
      - Drawdown duration (bars below prior peak)
      - Return distribution: upside vs downside comparison
      - Q-Q plot of returns vs normal distribution
    """
    logger.info("Rendering drawdown analysis panel...")
    _apply_style()

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle("Drawdown & Tail Risk Analysis  |  V17 Market-Neutral L/S", fontsize=12, y=0.99)

    ax_uw, ax_dur, ax_up_down, ax_qq = axes.flatten()

    net_ret = results["Net Return"].dropna()
    eq = results["Equity Curve"]
    drawdowns = results["Drawdown"]

    # Underwater (drawdown) curve
    ax_uw.set_title("Underwater Equity Curve", fontsize=9)
    ax_uw.fill_between(drawdowns.index, drawdowns.values * 100, 0, color=ACCENT3, alpha=0.7)
    ax_uw.plot(drawdowns.index, drawdowns.values * 100, color=ACCENT3, lw=0.8)
    ax_uw.set_ylabel("Drawdown (%)", fontsize=8)
    ax_uw.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    # Drawdown duration
    ax_dur.set_title("Drawdown Duration (Bars Below Peak)", fontsize=9)
    peak = eq.cummax()
    in_dd = (eq < peak).astype(int)
    duration = in_dd * 0
    count = 0
    for i, val in enumerate(in_dd):
        count = count + 1 if val else 0
        duration.iloc[i] = count
    ax_dur.fill_between(duration.index, duration.values, 0, color=ACCENT4, alpha=0.6)
    ax_dur.set_ylabel("Consecutive Bars in DD", fontsize=8)
    ax_dur.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    # Upside vs downside return distribution overlay
    ax_up_down.set_title("Upside vs Downside Return Distribution", fontsize=9)
    pos = net_ret[net_ret > 0]
    neg = net_ret[net_ret < 0]
    shared_bins = np.histogram_bin_edges(net_ret, bins=50)
    ax_up_down.hist(pos, bins=shared_bins, color=ACCENT2, alpha=0.7, label=f"Gains (n={len(pos)})")
    ax_up_down.hist(neg, bins=shared_bins, color=ACCENT3, alpha=0.7, label=f"Losses (n={len(neg)})")
    ax_up_down.axvline(net_ret.mean(), color=TEXT_LIGHT, lw=1.2, ls="--",
                       label=f"Mean={net_ret.mean():.4%}")
    ax_up_down.legend(fontsize=7)
    ax_up_down.set_xlabel("Return per Bar", fontsize=8)
    ax_up_down.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1, decimals=2))

    # Q-Q plot
    ax_qq.set_title("Q-Q Plot vs Normal Distribution", fontsize=9)
    sorted_ret = np.sort(net_ret)
    n = len(sorted_ret)
    theoretical_quantiles = np.quantile(
        np.random.default_rng(42).standard_normal(100_000),
        np.linspace(0.001, 0.999, n),
    )
    ax_qq.scatter(theoretical_quantiles, sorted_ret, s=3, alpha=0.4, color=ACCENT)
    lims = [min(theoretical_quantiles.min(), sorted_ret.min()),
            max(theoretical_quantiles.max(), sorted_ret.max())]
    ax_qq.plot(lims, lims, color=TEXT_DIM, lw=1.0, ls="--")
    ax_qq.set_xlabel("Theoretical Normal Quantiles", fontsize=8)
    ax_qq.set_ylabel("Empirical Return Quantiles", fontsize=8)

    output_dir.mkdir(parents=True, exist_ok=True)
    _save(fig, output_dir / "drawdown_analysis.png")


# ---------------------------------------------------------------------------
# Public alias for backwards-compatible main.py call
# ---------------------------------------------------------------------------

def render_realistic_equity_curve(
    results: pd.DataFrame,
    benchmark_path: Path,
    output_dir: Path,
) -> None:
    """Wrapper retained for backwards compatibility with main.py."""
    render_equity_curve(results, benchmark_path, output_dir)
