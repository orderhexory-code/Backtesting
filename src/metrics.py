"""Calculates performance statistics, drawdowns, and distribution breakdowns."""
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from src.models import Trade


class PerformanceMetrics:
    @staticmethod
    def calculate(trades: List[Trade], initial_balance: float = 10000.0) -> Dict[str, Any]:
        if not trades:
            return {
                "total_trades": 0,
                "net_profit": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "max_drawdown_pct": 0.0,
                "average_R": 0.0,
                "expectancy_R": 0.0
            }

        df = pd.DataFrame([t.to_dict() for t in trades])
        wins = df[df["net_pnl"] > 0]
        losses = df[df["net_pnl"] <= 0]

        total_trades = len(df)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0

        gross_profit = float(wins["net_pnl"].sum()) if not wins.empty else 0.0
        gross_loss = abs(float(losses["net_pnl"].sum())) if not losses.empty else 0.0
        net_profit = float(df["net_pnl"].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

        # Equity Curve and Drawdown
        df["cum_pnl"] = df["net_pnl"].cumsum()
        df["equity"] = initial_balance + df["cum_pnl"]
        df["peak_equity"] = df["equity"].cummax()
        df["drawdown"] = df["peak_equity"] - df["equity"]
        df["drawdown_pct"] = (df["drawdown"] / df["peak_equity"]) * 100

        max_dd = float(df["drawdown"].max())
        max_dd_pct = float(df["drawdown_pct"].max())

        avg_r = float(df["r_multiple"].mean())
        median_r = float(df["r_multiple"].median())
        max_r = float(df["r_multiple"].max())
        min_r = float(df["r_multiple"].min())

        # Expectancy = (Win% * Avg Win R) - (Loss% * Avg Loss R)
        win_r = float(wins["r_multiple"].mean()) if not wins.empty else 0.0
        loss_r = abs(float(losses["r_multiple"].mean())) if not losses.empty else 0.0
        expectancy_r = ((win_rate / 100.0) * win_r) - (((100.0 - win_rate) / 100.0) * loss_r)

        return {
            "total_trades": total_trades,
            "long_trades": int((df["direction"] == "LONG").sum()),
            "short_trades": int((df["direction"] == "SHORT").sum()),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_profit": round(net_profit, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "average_R": round(avg_r, 2),
            "median_R": round(median_r, 2),
            "max_R": round(max_r, 2),
            "min_R": round(min_r, 2),
            "expectancy_R": round(expectancy_r, 2),
            "avg_holding_minutes": round(float(df["holding_minutes"].mean()), 1)
        }