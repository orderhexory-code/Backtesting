"""Plotly chart generator for standalone and trade audit visualization."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import plotly.graph_objects as go
from src.models import Trade


class Visualizer:
    @staticmethod
    def chart_single_trade(trade: Trade, output_path: Optional[Path | str] = None) -> go.Figure:
        fig = go.Figure()

        # Audit timeline steps
        events = trade.audit_trail
        times = [e.timestamp for e in events]
        prices = [e.price for e in events]
        labels = [f"{e.event}: {e.details}" for e in events]

        fig.add_trace(go.Scatter(
            x=times,
            y=prices,
            mode='lines+markers+text',
            text=labels,
            textposition="top center",
            name=f"Trade {trade.trade_id}"
        ))

        # Reference Levels
        fig.add_hline(y=trade.reference_high, line_dash="dash", line_color="green", annotation_text="1H Ref High")
        fig.add_hline(y=trade.reference_low, line_dash="dash", line_color="red", annotation_text="1H Ref Low")

        fig.update_layout(
            title=f"Audit Timeline for Trade {trade.trade_id} ({trade.direction.value} {trade.setup_type.value})",
            xaxis_title="Time",
            yaxis_title="Price",
            template="plotly_dark"
        )

        if output_path:
            fig.write_html(str(output_path))

        return fig