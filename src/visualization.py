import matplotlib
matplotlib.use('Agg')
import alphalens as al
import io
from contextlib import redirect_stdout
import matplotlib.pyplot as plt
import pandas as pd
from . import config
from .utils import logger
from pathlib import Path

def generate_all_reports(clean_factor_data: pd.DataFrame):
    """Explicitly invokes Alphalens components to ensure safe rendering and export of plots/tables."""
    logger.info("==================================================")
    logger.info("Starting Explicit Component-Based Visualization Pipeline")
    logger.info("==================================================")

    # Setup output directory structure
    plots_dir = config.REPORTS_DIR / "plots"
    tables_dir = config.REPORTS_DIR / "tables"
    for sub in ["01_returns", "02_ic", "03_turnover"]:
        (plots_dir / sub).mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    # =================================================================
    # 1. Returns Analysis
    # =================================================================
    logger.info("Rendering Returns Analysis Plots...")
    mean_ret_quantile, _ = al.performance.mean_return_by_quantile(clean_factor_data, by_date=False, by_group=True)
    mean_ret_quantile.to_csv(tables_dir / "01_returns_mean_by_quantile.csv")

    mean_ret_quant_daily, _ = al.performance.mean_return_by_quantile(clean_factor_data, by_date=True, by_group=False)

    al.plotting.plot_quantile_returns_bar(mean_ret_quantile, by_group=True)
    plt.gcf().savefig(plots_dir / "01_returns" / "01_quantile_returns_bar.png", bbox_inches='tight', dpi=150)
    plt.close('all')

    for period in config.FORWARD_PERIODS:
        al.plotting.plot_cumulative_returns_by_quantile(mean_ret_quant_daily, period=f"{period}D")
        plt.gcf().savefig(plots_dir / "01_returns" / f"02_cumulative_returns_{period}D.png", bbox_inches='tight', dpi=150)
        plt.close('all')

    # =================================================================
    # 2. Information Coefficient (IC) Analysis
    # =================================================================
    logger.info("Rendering IC Analysis Plots...")
    ic = al.performance.factor_information_coefficient(clean_factor_data)
    ic.to_csv(tables_dir / "02_ic_timeseries.csv")

    al.plotting.plot_ic_ts(ic)
    plt.gcf().savefig(plots_dir / "02_ic" / "01_ic_timeseries.png", bbox_inches='tight', dpi=150)
    plt.close('all')

    al.plotting.plot_ic_hist(ic)
    plt.gcf().savefig(plots_dir / "02_ic" / "02_ic_histogram.png", bbox_inches='tight', dpi=150)
    plt.close('all')

    al.plotting.plot_ic_qq(ic)
    plt.gcf().savefig(plots_dir / "02_ic" / "03_ic_qq_plot.png", bbox_inches='tight', dpi=150)
    plt.close('all')

    # =================================================================
    # 3. Turnover & Autocorrelation Analysis
    # =================================================================
    logger.info("Rendering Turnover Analysis Plots...")
    fra = al.performance.factor_rank_autocorrelation(clean_factor_data)
    fra.to_csv(tables_dir / "03_turnover_fra.csv")

    al.plotting.plot_factor_rank_auto_correlation(fra)
    plt.gcf().savefig(plots_dir / "03_turnover" / "01_factor_rank_autocorrelation.png", bbox_inches='tight', dpi=150)
    plt.close('all')

    # =================================================================
    # 4. Statistical Summary Extraction (Tear Sheets)
    # =================================================================
    logger.info("Extracting pure text statistical summaries...")
    summary_text = io.StringIO()

    original_show = plt.show
    plt.show = lambda: None  # Suppress pop-up windows
    try:
        with redirect_stdout(summary_text):
            al.tears.create_returns_tear_sheet(clean_factor_data, by_group=True)
            print("\n" + "=" * 50 + "\n")
            al.tears.create_information_tear_sheet(clean_factor_data, by_group=True)
    finally:
        plt.show = original_show
        plt.close('all')

    with open(config.REPORTS_DIR / "summary_metrics.txt", "w") as f:
        f.write(summary_text.getvalue())

    logger.info("==================================================")
    logger.info(f"[SUCCESS] All explicit PNGs correctly rendered to {config.REPORTS_DIR}/plots")
    logger.info("==================================================")


def render_realistic_equity_curve(results: pd.DataFrame, benchmark_path: Path, output_dir: Path):
    """Renders the realistic backtest equity curve against a specified benchmark."""
    logger.info("Rendering Strategy vs Benchmark Equity Curve...")

    benchmark_curve = None
    if benchmark_path.exists():
        try:
            # Load and align benchmark data
            qqq_df = pd.read_csv(benchmark_path)
            qqq_df['timestamp'] = pd.to_datetime(qqq_df['timestamp'], utc=True)
            qqq_df.set_index('timestamp', inplace=True)
            qqq_df.index = qqq_df.index.tz_convert('America/New_York').tz_localize(None)

            qqq_1h = qqq_df.between_time('09:30', '15:59').resample('1h').agg({'close': 'last'}).dropna()

            strategy_index = results.index
            qqq_aligned = qqq_1h.reindex(strategy_index).ffill()
            benchmark_returns = qqq_aligned['close'].pct_change().fillna(0)
            benchmark_curve = (1 + benchmark_returns).cumprod()
        except Exception as e:
            logger.warning(f"Failed to process benchmark: {e}")

    plt.figure(figsize=(12, 6))

    # Updated label to reflect V17 Long-Short architecture
    results['Equity Curve'].plot(label="Strategy (V17 Long-Short)", color='darkred', linewidth=2.0)
    if benchmark_curve is not None:
        benchmark_curve.plot(label="Nasdaq 100 Baseline (QQQ)", color='gray', linestyle='--', linewidth=1.5, alpha=0.8)

    plt.title("Strategy Performance vs Nasdaq 100 Baseline (1H Freq, Net of Fees)")
    plt.ylabel("Cumulative Returns")
    plt.legend(loc="upper left")
    plt.grid(True, linestyle='--', alpha=0.6)

    output_dir.mkdir(parents=True, exist_ok=True)
    equity_curve_path = output_dir / "realistic_equity_curve_1H_with_benchmark.png"
    plt.savefig(equity_curve_path, bbox_inches='tight', dpi=200)
    plt.close()

    logger.info(f"Equity curve correctly saved to: {equity_curve_path}")