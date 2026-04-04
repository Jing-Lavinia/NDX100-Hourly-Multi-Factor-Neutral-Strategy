import pandas as pd

from src.utils import logger
from src import config, features, backtest, visualization, realistic_backtest
from src.alpaca_engine import load_and_clean_alpaca_data


def main() -> None:
    logger.info("=== Quantitative Intraday Factor Pipeline (V17 Long-Short) ===")

    # --- Data Loading ---
    logger.info(f"Loading data from {config.DATA_START_DATE} (includes warm-up window)...")
    prices_1h, volumes_1h = load_and_clean_alpaca_data(
        csv_dir_path=config.ALPACA_CSV_DIR,
        resample_freq="1h",
        start_date=config.DATA_START_DATE,
        end_date=config.END_DATE,
    )

    # --- Universe Filtering ---
    tech_tickers = [t for t, s in config.SECTOR_MAP.items() if s == "Tech"]
    prices_1h = prices_1h.reindex(columns=tech_tickers).dropna(axis=1, how="all")
    volumes_1h = volumes_1h.reindex(columns=prices_1h.columns).loc[prices_1h.index]
    logger.info(f"Tech universe filtered | tradable stocks={prices_1h.shape[1]}")

    # --- VIX Macro Data ---
    vix_data = None
    if config.VIX_DATA_FILE.exists():
        vix_raw = pd.read_csv(config.VIX_DATA_FILE, index_col=0, parse_dates=True)
        if vix_raw.index.tz is not None:
            vix_raw.index = vix_raw.index.tz_convert("America/New_York").tz_localize(None)
        vix_series = vix_raw["VIX"] if "VIX" in vix_raw.columns else vix_raw.iloc[:, 0]
        vix_data = vix_series.reindex(prices_1h.index, method="ffill")
        logger.info("VIX macro data loaded and aligned.")
    else:
        logger.warning(f"VIX file not found at {config.VIX_DATA_FILE} — running without macro scaling.")

    # --- Factor Generation ---
    logger.info("Generating multi-period factor pool...")
    factor_pool = {
        "Momentum_420": features.calc_momentum(prices_1h, window=420),
        "Momentum_140": features.calc_momentum(prices_1h, window=140),
        "LowVol_90": features.calc_low_volatility(prices_1h, window=90),
    }

    factor_pool_1h = {
        name: df.resample("1h").last().reindex(prices_1h.index)
        for name, df in factor_pool.items()
    }

    combined_factor = features.dynamic_factor_synthesis(
        factors_dict=factor_pool_1h,
        prices_df=prices_1h,
    )

    # --- Warm-Up Trim ---
    logger.info(f"Trimming to backtest window from {config.BACKTEST_START_DATE}...")
    prices_1h = prices_1h.loc[config.BACKTEST_START_DATE:]
    combined_factor = combined_factor.loc[config.BACKTEST_START_DATE:]
    if vix_data is not None:
        vix_data = vix_data.loc[config.BACKTEST_START_DATE:]

    if prices_1h.empty or combined_factor.isnull().all().all():
        logger.error("FATAL: Empty data after warm-up trim. Check BACKTEST_START_DATE.")
        return

    # --- Alphalens Evaluation ---
    logger.info("Running theoretical factor evaluation via Alphalens...")
    factor_data = backtest.prepare_alphalens_data(prices_1h, combined_factor, config.SECTOR_MAP)
    visualization.generate_all_reports(factor_data)

    # --- Realistic Backtest ---
    logger.info("Running realistic market-neutral long-short backtest...")
    results_df, weights_df, metrics_dict = realistic_backtest.run_realistic_backtest(
        prices_df=prices_1h,
        factor_df=combined_factor,
        holding_periods=28,
        base_transaction_cost=0.0002,
        stop_loss_pct=0.08,
        vix_series=vix_data,
    )

    # --- Export Ledgers ---
    logger.info("Exporting backtest ledgers and metrics...")
    export_dir = config.REPORTS_DIR / "data_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(export_dir / "timeseries_ledger_1H.csv")
    weights_df.to_csv(export_dir / "portfolio_weights_matrix.csv")
    pd.Series(metrics_dict, name="Metrics").to_csv(export_dir / "performance_metrics.csv")

    # --- Extended Visualizations ---
    logger.info("Rendering extended visualization suite...")
    plots_dir = config.REPORTS_DIR / "plots"

    visualization.render_equity_curve(
        results=results_df,
        benchmark_path=config.BENCHMARK_CSV_PATH,
        output_dir=plots_dir,
    )
    visualization.render_performance_dashboard(
        results=results_df,
        output_dir=plots_dir,
    )
    visualization.render_risk_decomposition(
        results=results_df,
        portfolio_weights=weights_df,
        output_dir=plots_dir,
    )
    visualization.render_factor_diagnostics(
        factor_df=combined_factor,
        prices_df=prices_1h,
        output_dir=plots_dir,
    )
    visualization.render_drawdown_analysis(
        results=results_df,
        output_dir=plots_dir,
    )

    logger.info("=== Pipeline complete. ===")


if __name__ == "__main__":
    main()
