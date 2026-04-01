import pandas as pd
from src.utils import logger
from src import config, features, backtest, visualization, realistic_backtest
from src.alpaca_engine import load_and_clean_alpaca_data

def main():
    logger.info("=== Starting Quantitative Intraday Factor Pipeline (V17 Long-Short) ===")

    # Load data including the warm-up period to ensure sufficient history for long-window factors
    logger.info(f"Loading data from {config.DATA_START_DATE} (includes warm-up)...")
    prices_1h, volumes_1h = load_and_clean_alpaca_data(
        csv_dir_path=config.ALPACA_CSV_DIR,
        resample_freq='1h',
        start_date=config.DATA_START_DATE,
        end_date=config.END_DATE
    )

    # Filter for highly elastic Tech sector stocks to construct the core trading pool
    tech_tickers = [ticker for ticker, sector in config.SECTOR_MAP.items() if sector == 'Tech']
    prices_1h = prices_1h.reindex(columns=tech_tickers).dropna(axis=1, how='all')
    volumes_1h = volumes_1h.reindex(columns=prices_1h.columns).loc[prices_1h.index]
    logger.info(f"Tech sector filtered. Remaining tradable universe: {prices_1h.shape[1]} stocks")

    # Load VIX macro data for dynamic risk scaling
    vix_data = None
    if config.VIX_DATA_FILE.exists():
        vix_raw = pd.read_csv(config.VIX_DATA_FILE, index_col=0, parse_dates=True)
        if vix_raw.index.tz is not None:
            vix_raw.index = vix_raw.index.tz_convert('America/New_York').tz_localize(None)
        vix_series = vix_raw['VIX'] if 'VIX' in vix_raw.columns else vix_raw.iloc[:, 0]
        vix_data = vix_series.reindex(prices_1h.index, method='ffill')

    # Generate targeted factor pool
    logger.info("Generating multi-period factor pool...")
    factor_pool = {
        'Momentum_420': features.calc_momentum(prices_1h, window=420),
        'Momentum_140': features.calc_momentum(prices_1h, window=140),
        'LowVol_90': features.calc_low_volatility(prices_1h, window=90)
    }

    factor_pool_1h = {
        name: f_df.resample('1h').last().reindex(prices_1h.index)
        for name, f_df in factor_pool.items()
    }

    combined_super_factor = features.dynamic_factor_synthesis(
        factors_dict=factor_pool_1h,
        prices_df=prices_1h
    )

    # CRITICAL: Discard warm-up period data; enforce strict start date for accurate backtest evaluation
    logger.info(f"Slicing data for actual backtest evaluation (From {config.BACKTEST_START_DATE})...")
    prices_1h = prices_1h.loc[config.BACKTEST_START_DATE:]
    combined_super_factor = combined_super_factor.loc[config.BACKTEST_START_DATE:]
    if vix_data is not None:
        vix_data = vix_data.loc[config.BACKTEST_START_DATE:]

    if prices_1h.empty or combined_super_factor.isnull().all().all():
        logger.error("FATAL: Data is empty or entirely NaN after slicing. Verify BACKTEST_START_DATE.")
        return

    # Theoretical factor evaluation
    logger.info("Executing theoretical analysis via Alphalens...")
    factor_data = backtest.prepare_alphalens_data(prices_1h, combined_super_factor, config.SECTOR_MAP)
    visualization.generate_all_reports(factor_data)

    # Execution of realistic Market-Neutral Long-Short backtest
    logger.info("Executing realistic trading backtest engine...")
    results_df, weights_df, metrics_dict = realistic_backtest.run_realistic_backtest(
        prices_df=prices_1h,
        factor_df=combined_super_factor,
        holding_periods=28,           # Expanded holding period to smooth execution and minimize turnover slippage
        base_transaction_cost=0.0002,
        stop_loss_pct=0.08,           # Asymmetric single-stock stop-loss threshold
        vix_series=vix_data
    )

    # Export outputs
    logger.info("Exporting backtest ledgers and performance metrics...")
    export_dir = config.REPORTS_DIR / "data_exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(export_dir / "timeseries_ledger_1H.csv")
    weights_df.to_csv(export_dir / "portfolio_weights_matrix.csv")
    pd.Series(metrics_dict, name="Metrics").to_csv(export_dir / "performance_metrics.csv")

    visualization.render_realistic_equity_curve(
        results=results_df,
        benchmark_path=config.BENCHMARK_CSV_PATH,
        output_dir=config.REPORTS_DIR
    )
    logger.info("=== Pipeline Execution Finished Successfully! ===")

if __name__ == "__main__":
    main()