"""Artifact generation: CSVs, metrics.json, data_quality.json, and interactive HTML report."""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from jinja2 import Template
from src.models import Trade
from src.metrics import PerformanceMetrics


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>NASDAQ Strategy Backtest Report</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background: #0f172a; color: #f8fafc; }
    .container { max-width: 1200px; margin: 0 auto; }
    .header { border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
    .card { background: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; }
    .card h4 { margin: 0 0 5px 0; color: #94a3b8; font-size: 13px; text-transform: uppercase; }
    .card p { margin: 0; font-size: 22px; font-weight: bold; color: #38bdf8; }
    .chart-container { background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 25px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
    th, td { padding: 10px; text-align: left; border-bottom: 1px solid #334155; }
    th { background: #334155; color: #f8fafc; }
    .win { color: #4ade80; }
    .loss { color: #f87171; }
  </style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>NASDAQ Strategy Backtest Report</h1>
      <p style="color: #94a3b8; margin: 0;">Symbol: {{ meta.symbol }} | Config Hash: {{ meta.config_hash }} | Mode: {{ meta.execution_mode }}</p>
    </div>
  </div>

  <div class="card-grid">
    <div class="card"><h4>Net Profit</h4><p class="{{ 'win' if metrics.net_profit >= 0 else 'loss' }}">${{ metrics.net_profit }}</p></div>
    <div class="card"><h4>Profit Factor</h4><p>{{ metrics.profit_factor }}</p></div>
    <div class="card"><h4>Win Rate</h4><p>{{ metrics.win_rate }}%</p></div>
    <div class="card"><h4>Total Trades</h4><p>{{ metrics.total_trades }}</p></div>
    <div class="card"><h4>Expectancy (R)</h4><p>{{ metrics.expectancy_R }}R</p></div>
    <div class="card"><h4>Max Drawdown</h4><p class="loss">{{ metrics.max_drawdown_pct }}%</p></div>
  </div>

  <div class="chart-container">
    <div id="equityChart"></div>
  </div>

  <div class="chart-container">
    <h3>Closed Trades Log</h3>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Direction</th>
          <th>Setup</th>
          <th>Entry Time</th>
          <th>Entry</th>
          <th>Exit Time</th>
          <th>Exit</th>
          <th>Max R</th>
          <th>R Realized</th>
          <th>Net P&L</th>
          <th>Exit Reason</th>
        </tr>
      </thead>
      <tbody>
        {% for t in trades %}
        <tr>
          <td>{{ t.trade_id }}</td>
          <td>{{ t.direction }}</td>
          <td>{{ t.setup_type }}</td>
          <td>{{ t.entry_time }}</td>
          <td>{{ t.entry_price }}</td>
          <td>{{ t.exit_time }}</td>
          <td>{{ t.exit_price }}</td>
          <td>{{ t.max_r }}R</td>
          <td>{{ t.r_multiple }}R</td>
          <td class="{{ 'win' if t.net_pnl > 0 else 'loss' }}">${{ t.net_pnl }}</td>
          <td>{{ t.exit_reason }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<script>
  const trace = {
    x: {{ equity_curve_x | safe }},
    y: {{ equity_curve_y | safe }},
    type: 'scatter',
    mode: 'lines',
    line: { color: '#38bdf8', width: 2 }
  };
  const layout = {
    title: 'Equity Curve ($)',
    paper_bgcolor: '#1e293b',
    plot_bgcolor: '#1e293b',
    font: { color: '#f8fafc' },
    xaxis: { gridcolor: '#334155' },
    yaxis: { gridcolor: '#334155' }
  };
  Plotly.newPlot('equityChart', [trace], layout, {responsive: true});
</script>
</body>
</html>
"""


class ReportGenerator:
    @staticmethod
    def generate_all(
        trades: List[Trade],
        metrics: Dict[str, Any],
        output_dir: Path | str,
        meta: Dict[str, Any]
    ) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        trade_dicts = [t.to_dict() for t in trades]
        trades_df = pd.DataFrame(trade_dicts)

        # 1. trades.csv
        trades_df.to_csv(out / "trades.csv", index=False)

        # 2. metrics.json
        with open(out / "metrics.json", "w", encoding="utf-8") as f:
            json.dump({**meta, "metrics": metrics}, f, indent=2)

        # 3. equity_curve.csv & daily_returns.csv
        if not trades_df.empty:
            trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
            trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"])
            trades_df.sort_values("exit_time", inplace=True)
            trades_df["cumulative_pnl"] = trades_df["net_pnl"].cumsum()
            trades_df["equity"] = meta.get("initial_balance", 10000.0) + trades_df["cumulative_pnl"]
            trades_df[["exit_time", "equity", "cumulative_pnl"]].to_csv(out / "equity_curve.csv", index=False)

            # Daily Returns
            trades_df["date"] = trades_df["exit_time"].dt.date
            daily_df = trades_df.groupby("date")["net_pnl"].sum().reset_index()
            daily_df.to_csv(out / "daily_returns.csv", index=False)

            eq_x = [d.isoformat() for d in trades_df["exit_time"]]
            eq_y = trades_df["equity"].tolist()
        else:
            eq_x = []
            eq_y = []

        # 4. report.html
        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            meta=meta,
            metrics=metrics,
            trades=trade_dicts,
            equity_curve_x=json.dumps(eq_x),
            equity_curve_y=json.dumps(eq_y)
        )
        with open(out / "report.html", "w", encoding="utf-8") as f:
            f.write(html_content)