"""Command-line interface for the NASDAQ Strategy Backtester."""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
import click
import pandas as pd
from tabulate import tabulate

from src.config import BacktestConfig
from src.data_loader import DataLoader
from src.data_validator import DataValidator
from src.data_fetcher import FreeDataFetcher
from src.backtester import Backtester
from src.metrics import PerformanceMetrics
from src.reporting import ReportGenerator
from src.visualization import Visualizer


@click.group()
def cli():
    """NASDAQ Multi-Timeframe Strategy Backtester CLI."""
    pass


@cli.command("download-data")
@click.option("--symbol", default="NQ=F", help="Symbol to download (e.g., 'NQ=F', 'QQQ', 'MNQ=F').")
@click.option("--days", default=7, type=int, help="Number of past days of 1-minute data (max 29).")
@click.option("--output", default="data/processed/MNQ_1m.parquet", help="Output file destination.")
def download_data(symbol: str, days: int, output: str):
    """Download free 1-minute historical data from Yahoo Finance."""
    try:
        FreeDataFetcher.fetch_yfinance_1m(symbol=symbol, days=days, output_path=output)
    except Exception as e:
        click.echo(f"\n[Error] Failed to download data: {e}", err=True)
        click.echo("[Tip] If 'NQ=F' fails, try downloading NASDAQ ETF with: python main.py download-data --symbol QQQ\n", err=True)
        sys.exit(1)


@cli.command("generate-synthetic")
@click.option("--output", default="data/processed/MNQ_1m.parquet", help="Output file path.")
@click.option("--scenario", default="upside_breakout", help="Scenario: upside_breakout | upside_sweep")
@click.option("--hours", default=10, help="Number of hours of data.")
def generate_synthetic(output: str, scenario: str, hours: int):
    """Generate synthetic 1M dataset for deterministic testing."""
    start = datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc)
    df = DataLoader.generate_synthetic_data(start, hours=hours, scenario=scenario)
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)
    click.echo(f"[+] Generated {len(df)} synthetic bars -> {out_path}")


@cli.command("validate-data")
@click.option("--data", required=True, help="Path to 1M CSV or Parquet file.")
@click.option("--report-out", default="results/data_quality.json", help="Path for JSON quality report.")
def validate_data(data: str, report_out: str):
    """Validate 1M dataset integrity."""
    df = DataLoader.load_from_parquet(data) if data.endswith(".parquet") else DataLoader.load_from_csv(data)
    is_valid, report = DataValidator.validate_ohlcv_dataframe(df)
    DataValidator.save_report(report, report_out)
    click.echo(f"Validation {'PASSED' if is_valid else 'FAILED'}. Report saved to {report_out}")
    if not is_valid:
        sys.exit(1)


@cli.command("backtest")
@click.option("--data", required=True, help="Path to normalized 1M Parquet or CSV.")
@click.option("--config", default="config/strategy.yaml", help="Path to strategy YAML.")
@click.option("--start", default=None, help="Start date (YYYY-MM-DD).")
@click.option("--end", default=None, help="End date (YYYY-MM-DD).")
@click.option("--output-dir", default="results", help="Directory for artifacts.")
@click.option("--debug", is_flag=True, help="Print verbose step-by-step logs.")
def run_backtest(data: str, config: str, start: str | None, end: str | None, output_dir: str, debug: bool):
    """Run full chronological event-driven backtest."""
    cfg = BacktestConfig.from_yaml(config)
    click.echo(f"[*] Loading data from {data}...")
    df = DataLoader.load_from_parquet(data, start, end) if data.endswith(".parquet") else DataLoader.load_from_csv(data, start, end)
    
    # 1. Validate
    is_valid, quality_rep = DataValidator.validate_ohlcv_dataframe(df)
    DataValidator.save_report(quality_rep, Path(output_dir) / "data_quality.json")
    if not is_valid:
        click.echo("[!] Data validation failed! See data_quality.json for details.", err=True)
        sys.exit(1)

    candles = DataLoader.dataframe_to_candles(df)
    click.echo(f"[*] Loaded {len(candles)} 1M bars. Running Backtest engine...")

    backtester = Backtester(cfg)
    trades = backtester.run(candles)
    click.echo(f"[+] Backtest complete. Generated {len(trades)} trades.")

    # 2. Compute Metrics
    metrics = PerformanceMetrics.calculate(trades, cfg.account.initial_balance)
    
    # 3. Print Summary Table
    table_data = [[k, v] for k, v in metrics.items()]
    click.echo("\n" + tabulate(table_data, headers=["Metric", "Value"], tablefmt="fancy_grid"))

    # 4. Generate Reports and Artifacts
    meta = {
        "symbol": cfg.instrument.symbol,
        "config_hash": cfg.get_hash(),
        "execution_mode": cfg.execution.intrabar_mode,
        "data_file": data,
        "initial_balance": cfg.account.initial_balance
    }
    ReportGenerator.generate_all(trades, metrics, output_dir, meta)
    click.echo(f"\n[+] Artifacts successfully written to '{output_dir}/'")


@cli.command("audit-trade")
@click.option("--results-dir", default="results", help="Results folder containing trades.csv.")
@click.option("--trade-id", required=True, help="Trade ID to inspect (e.g. TR_0001).")
def audit_trade(results_dir: str, trade_id: str):
    """Audit the step-by-step lifecycle of a specific trade."""
    trades_path = Path(results_dir) / "trades.csv"
    if not trades_path.exists():
        click.echo(f"[!] No trades.csv found in {results_dir}", err=True)
        sys.exit(1)
    df = pd.read_csv(trades_path)
    matched = df[df["trade_id"] == trade_id]
    if matched.empty:
        click.echo(f"[!] Trade ID {trade_id} not found in trades.csv", err=True)
        sys.exit(1)
    click.echo(tabulate(matched.T.reset_index(), headers=["Field", "Value"], tablefmt="fancy_grid"))


if __name__ == "__main__":
    cli()