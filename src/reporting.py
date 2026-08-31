"""Exports clean structured JSON and CSV artifacts for the custom dashboard."""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from src.models import Trade


class ReportGenerator:
    @staticmethod
    def generate_all(
        trades: List[Trade],
        metrics: Dict[str, Any],
        output_dir: Path | str,
        meta: Dict[str, Any]
    ) -> None:
        # Results folder for raw CSV / backup
        results_out = Path("results")
        results_out.mkdir(parents=True, exist_ok=True)

        # Dashboard folder for frontend consumption
        dashboard_out = Path("dashboard")
        dashboard_out.mkdir(parents=True, exist_ok=True)

        trade_dicts = [t.to_dict() for t in trades]
        trades_df = pd.DataFrame(trade_dicts)

        # 1. Save CSV Artifacts
        trades_df.to_csv(results_out / "trades.csv", index=False)
        trades_df.to_csv(dashboard_out / "trades.csv", index=False)

        # 2. Extract analytical payload for Dashboard UI
        setup_stats = metrics.get("setup_stats", {})
        hourly_stats = metrics.get("hourly_stats", {})
        weekday_stats = metrics.get("weekday_stats", {})

        dashboard_payload = {
            "meta": meta,
            "metrics": {
                "net_profit": metrics.get("net_profit", 0.0),
                "return_pct": metrics.get("return_pct", 0.0),
                "profit_factor": metrics.get("profit_factor", 0.0),
                "win_rate": metrics.get("win_rate", 0.0),
                "total_trades": metrics.get("total_trades", 0),
                "winning_trades": metrics.get("winning_trades", 0),
                "losing_trades": metrics.get("losing_trades", 0),
                "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
                "sortino_ratio": metrics.get("sortino_ratio", 0.0),
                "max_drawdown": metrics.get("max_drawdown", 0.0),
                "max_drawdown_pct": metrics.get("max_drawdown_pct", 0.0),
                "average_R": metrics.get("average_R", 0.0),
                "expectancy_R": metrics.get("expectancy_R", 0.0),
                "max_consecutive_wins": metrics.get("max_consecutive_wins", 0),
                "max_consecutive_losses": metrics.get("max_consecutive_losses", 0),
                "avg_holding_minutes": metrics.get("avg_holding_minutes", 0.0)
            },
            "timeseries": {
                "timestamps": metrics.get("equity_times", []),
                "equity_curve": metrics.get("equity_values", []),
                "drawdown_pct": metrics.get("drawdown_values", [])
            },
            "distributions": {
                "setups": setup_stats,
                "hourly_pnl": hourly_stats,
                "weekday_pnl": weekday_stats,
                "r_multiples": metrics.get("r_multiples", []),
                "holding_minutes": metrics.get("holding_minutes_list", [])
            },
            "trades": trade_dicts
        }

        # 3. Export Pure JSON Data for HTML embed
        with open(dashboard_out / "data.json", "w", encoding="utf-8") as f:
            json.dump(dashboard_payload, f, indent=2)

        with open(results_out / "metrics.json", "w", encoding="utf-8") as f:
            json.dump({**meta, "metrics": metrics}, f, indent=2)

        print(f"[+] Clean data exported to: {dashboard_out.resolve()}/data.json")
