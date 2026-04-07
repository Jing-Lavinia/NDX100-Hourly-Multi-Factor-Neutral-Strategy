# Market-Neutral Quantitative Intraday Strategy
## NDX100 Full Universe · 1-Hour Frequency · Multi-Factor Long-Short · V17 Execution Framework

> **Backtest period:** January 2026 – March 2026 (3-month OOS evaluation window)
> **Warm-up period:** August 2025 – December 2025 (factor convergence only, no trading)
> **Universe:** ~100 NDX100 constituents across 9 GICS sectors
> **Data source:** Alpaca 5-minute bars, aggregated to 1-hour

---

## Strategy Summary

This pipeline builds a daily intraday cross-sectional long-short equity strategy on the
full NDX100 universe. Three alpha signals—two momentum windows and an inverted-volatility
factor—are synthesised into a composite score. Each hour, the top-decile stocks are held
long and the bottom-decile stocks are held short in equal-weight baskets. A six-step
realistic execution model applies VIX-based delevering, volatility targeting, asymmetric
stop-losses, TWAP weight smoothing, and a 2 bps per-side transaction cost before computing
net performance.

All look-ahead bias is eliminated through a one-bar signal lag (`shift(1)`) applied before
any position sizing decision.

---

## Backtest Results

### Core Performance Metrics

| Metric | Value |
|--------|-------|
| **Total Period Return** | 23.92% |
| **Geometric CAGR** | 149.9% |
| **Annualised Volatility** | 38.0% |
| **Sharpe Ratio** | **3.94** |
| **Sortino Ratio** | **4.89** |
| **Calmar Ratio** | **8.57** |
| **Max Drawdown** | −17.49% |
| **Win Rate (per bar)** | 52.9% |
| **Average Turnover (per bar)** | 3.11% |
| **Break-Even Cost** | **92.2 bps** |
| **Profit Factor** | 1.24 |

> CAGR is annualised from a 3-month window and should be interpreted with caution.
> See the risk warnings at the bottom of this document.

### Alphalens Factor Statistics

| Horizon | Mean IC | IC Std | Risk-Adj IC (ICIR) | Ann. Alpha |
|---------|---------|--------|---------------------|------------|
| 1-bar (1H) | 0.033 | 0.270 | 0.122 | 7.9% |
| 6-bar (6H) | 0.052 | 0.263 | 0.198 | 2.7% |
| 12-bar (12H) | 0.064 | 0.313 | 0.206 | 3.9% |

*Note: "1D / 6D / 12D" labels in Alphalens output refer to bar counts (1, 6, 12 hours),
not calendar days. The "D" suffix is a labelling artefact of the library.*

---

## Financial Interpretation

### 1. The factor signal is real but noisy at the bar level

The Alphalens IC summary (`plots/02_ic/01_ic_timeseries.png`) shows mean ICs of 0.033,
0.052, and 0.064 across the 1H, 6H, and 12H horizons. These figures are consistent with
a genuine predictive signal — academic literature treats IC ≥ 0.02 as economically
meaningful for high-frequency cross-sectional strategies.

Critically, IC **increases with the prediction horizon**: 0.033 at 1H, rising to 0.064
at 12H. This confirms that the composite momentum-plus-low-volatility signal carries
meaningful information over a half-trading-day window, which is precisely the target
holding period of the strategy (~28 hours via TWAP smoothing). The signal is not
a short-lived microstructure artefact that decays in the first bar.

The high IC standard deviation (≈0.27) relative to the mean indicates the signal is
volatile on any individual bar — a natural property of intraday data — but the positive
mean persists across the 3-month OOS window, providing statistical confidence.

### 2. The strategy genuinely separates from the benchmark

The equity curve (`plots/equity_curve_with_benchmark.png`) shows the strategy ending
at +23.9% while QQQ (the benchmark) lost roughly −9% over the same January–March 2026
window. The long-short structure insulates the portfolio from the broad market decline:
the Alphalens beta estimate ranges from −0.28 to −0.54 across horizons, confirming
meaningful negative market beta — the short book contributed positively precisely when
the market fell.

This is a core property of a well-constructed market-neutral strategy: it should not
move with the index. The benchmark underperformance during a down-market while the
strategy profits validates the decoupling mechanism.

### 3. Break-even cost of 92 bps provides a robust safety margin

The break-even cost metric answers: *at what transaction cost does this strategy stop
making money?* At 92.2 bps, the strategy is profitable at more than 46× the assumed
2 bps execution cost. Even under severe cost assumptions (e.g., 20 bps for a less liquid
implementation), the strategy retains a 4.6× safety buffer. This is a strong signal that
the gross alpha is not being manufactured by ignoring trading friction.

Average turnover per bar is 3.11%, meaning the cumulative cost drag over the 3-month
period is approximately 0.5% (visible in the `performance_dashboard.png` cost-drag
panel). The gap between the gross and net equity curves is negligible — costs are not
consuming the alpha.

### 4. Sector-level factor monotonicity is mixed

The quantile returns chart (`plots/01_returns/01_quantile_returns_bar.png`) breaks down
factor performance by sector. **Energy and Consumer sectors** show the clearest
monotonic separation between Q1 (worst) and Q5 (best) — the factor ranks stocks
correctly within these sectors. **Tech and Healthcare** show weaker or non-monotonic
patterns at the 1H horizon.

This is economically intuitive: momentum and low-volatility signals work better in
sectors where fundamentals drive near-term relative performance (energy prices, consumer
spending) than in sectors dominated by event-driven idiosyncratic news (healthcare
announcements, tech earnings revisions). The full-universe approach benefits from
diversifying across these sector-level alpha sources.

### 5. The maximum drawdown arrives in March 2026 and coincides with high volatility

The performance dashboard shows the rolling annualised volatility (`plots/performance_dashboard.png`)
exceeding the 15% vol-target threshold at multiple points in February–March 2026. During
the March drawdown (−17.5% maximum), the rolling Sharpe drops sharply negative. The
risk decomposition panel (`plots/risk_decomposition.png`) shows net exposure spiking
toward +0.4 in late February before being corrected by VIX delevering, suggesting the
stop-loss and VIX mechanisms were active but could not fully prevent the drawdown.

The monthly P&L heatmap in the dashboard confirms: January +17.3%, February +10.4%,
March −4.5%. The March loss is consistent with a market-neutral strategy under
directional stress when cross-sectional dispersion compresses — a known risk for
intraday factor strategies during macro-driven broad sell-offs.

---

## Architecture

```
longtime_period_data.py   ← Download 100 NDX100 tickers, 1-year 5-min bars (Alpaca)
fetch_data.py             ← Download 60-day hourly VIX (yfinance)
main.py                   ← Pipeline entry point
└── src/
    ├── config.py         ← All parameters: paths, dates, SECTOR_MAP
    ├── alpaca_engine.py  ← CSV loader → 1H price/volume matrices
    ├── features.py       ← 3 alpha factors + composite synthesis
    ├── backtest.py       ← Alphalens factor evaluation
    ├── realistic_backtest.py  ← 6-step L/S backtest engine (V17)
    ├── visualization.py  ← Full chart suite
    └── utils.py          ← Logger
```

---

## Factor Specification

| Factor | Window | Construction | Composite Weight |
|--------|--------|-------------|-----------------|
| Momentum_420 | 420 bars (~3 months) | `pct_change(420)` → MAD winsorise → z-score → EWMA(10) | **2×** |
| Momentum_140 | 140 bars (~1 month) | same pipeline | 1× |
| LowVol_90 | 90 bars (~2 weeks) | `−std(returns, 90)` → MAD winsorise → z-score → EWMA(20) | 1× |

Composite = weighted sum → cross-sectional re-standardisation → N(0,1).

---

## Six-Step Execution Model

| Step | Mechanism | Parameter |
|------|-----------|-----------|
| 1 | Signal lag — `factor_df.shift(1)` | 1 bar |
| 2 | VIX continuous delevering — `min(30/VIX, 1)` | Applied with 1-bar lag |
| 3 | Volatility targeting | Target 15% ann., cap 1.5× |
| 4 | Asymmetric hard stop-loss | Long: −8% from 28-bar high; Short: +8% from 28-bar low |
| 5 | TWAP simulation — 28-bar rolling-mean weight smoothing | 28 bars |
| 6 | Micro-structural cost model | 2 bps per-side per unit turnover |

---

## Configuration (`src/config.py`)

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `DATA_START_DATE` | 2025-08-01 | Warm-up start (factor convergence) |
| `BACKTEST_START_DATE` | 2026-01-01 | OOS evaluation start |
| `END_DATE` | 2026-03-31 | Data end |
| `FORWARD_PERIODS` | [1, 6, 12] | Alphalens IC horizons (bar counts, not days) |
| `holding_periods` | 28 | TWAP window and stop-loss lookback (bars) |
| `base_transaction_cost` | 0.0002 | 2 bps per side |
| `stop_loss_pct` | 0.08 | 8% asymmetric stop-loss |

---

## Output Files

```
reports/
├── backtest_run.log
├── data_exports/
│   ├── timeseries_ledger_1H.csv       ← per-bar P&L ledger
│   ├── portfolio_weights_matrix.csv   ← per-bar weight matrix (~700 × ~100)
│   └── performance_metrics.csv        ← 13 KPIs
└── plots/
    ├── equity_curve_with_benchmark.png
    ├── performance_dashboard.png
    ├── risk_decomposition.png
    ├── factor_diagnostics.png
    ├── drawdown_analysis.png
    ├── 01_returns/
    ├── 02_ic/
    └── 03_turnover/
```

---

## Originality Statement

This strategy is independently designed and implemented. The core contributions are:

- **Full-universe intraday cross-sectional design** — applying a factor framework across
  all 9 NDX100 GICS sectors simultaneously rather than restricting to a single sector,
  providing richer cross-sectional dispersion and natural diversification.
- **1-hour resolution with 5-minute source data** — the aggregation choice balances
  signal quality against transaction cost; the 5-min raw data is preserved for potential
  alternative aggregation frequencies.
- **Six-step realistic execution framework** — integrating VIX delevering, volatility
  targeting, asymmetric stop-losses, and TWAP simulation into a single vectorised engine.
- **Break-even cost as a primary risk metric** — framing execution robustness in terms
  of the maximum supportable cost rather than a fixed assumed cost.
- **Strict look-ahead prevention** — all signals are lagged by one bar before use;
  the warm-up window is explicitly excluded from performance measurement.

The factor construction (momentum and low-volatility), the TWAP approximation via
rolling-mean weight smoothing, and the Alphalens evaluation framework draw on established
quantitative finance practice.

---

## Risk Warning and Disclaimer

**This strategy is a research prototype and should not be used for live trading without
substantial additional validation.**

Specific risks to consider before any real-money application:

1. **Short evaluation window.** The backtest covers only 3 months (January–March 2026).
   A Sharpe ratio of 3.94 computed over ~700 hourly bars has very wide confidence
   intervals. The same strategy could produce a materially different Sharpe over a
   different 3-month window.

2. **Market-regime sensitivity.** The regime-conditional analysis shows the March 2026
   drawdown coinciding with elevated VIX and directional stress. In sustained high-VIX
   environments the VIX delevering mechanism reduces but does not eliminate losses.

3. **Transaction cost assumption.** The 2 bps per-side assumption may understate real
   costs for less liquid NDX100 constituents, particularly during volatile periods when
   bid-ask spreads widen.

4. **Capacity and market impact.** The strategy trades ~100 stocks every ~4 days.
   At meaningful capital scale, the TWAP approximation will understate actual market
   impact.

5. **Data availability in live trading.** Alpaca's free-tier data quality, corporate
   action handling, and survivorship properties differ from institutional data vendors.
   Live performance may deviate from backtest results.

6. **Model decay.** Factor efficacy can degrade as signals become crowded. The 3-month
   OOS window is insufficient to measure model decay.

*This document is for educational and research purposes only. It does not constitute
investment advice.*

---

## Quick Start

```bash
# 1. Install dependencies
pip install alpaca-trade-api alphalens-reloaded yfinance pandas numpy scipy

# 2. Download data
python longtime_period_data.py   # ~100 tickers, 1 year of 5-min bars
python fetch_data.py             # 60-day hourly VIX

# 3. Run the pipeline
python main.py
```
