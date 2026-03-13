"""Plotting utilities for selected spectral regions."""
from __future__ import annotations

import plotly.graph_objects as go

DOMAIN_BANDS = [
    (400, 700, "Visible", "rgba(253, 224, 71, 0.22)"),
    (700, 1000, "NIR", "rgba(134, 239, 172, 0.22)"),
    (1000, 2500, "SWIR", "rgba(216, 180, 254, 0.22)"),
]


def plot_selected_regions(recommendations: list[dict]) -> go.Figure:
    fig = go.Figure()

    for lo, hi, label, color in DOMAIN_BANDS:
        fig.add_vrect(x0=lo, x1=hi, fillcolor=color, opacity=1.0, line_width=0)
        fig.add_annotation(
            x=(lo + hi) / 2,
            y=1.08,
            xref="x",
            yref="paper",
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(size=11),
        )

    palette = ["#1d4ed8", "#0f766e", "#9333ea", "#dc2626", "#0891b2", "#16a34a"]
    for i, rec in enumerate(recommendations):
        lo, hi = rec["range_nm"]
        label = rec["id"]
        targets = ", ".join(rec.get("target_tags", []))
        fig.add_vrect(
            x0=lo,
            x1=hi,
            fillcolor=palette[i % len(palette)],
            opacity=0.55,
            line_width=2,
            line_color=palette[i % len(palette)],
            annotation_text=f"{label}<br>{lo:.0f}-{hi:.0f} nm",
            annotation_position="top left",
        )
        fig.add_trace(
            go.Scatter(
                x=[(lo + hi) / 2],
                y=[1],
                mode="markers",
                marker=dict(size=10, color=palette[i % len(palette)]),
                hovertemplate=(
                    f"<b>{label}</b><br>Range: {lo:.0f}-{hi:.0f} nm"
                    f"<br>Targets: {targets}<br>Score: {rec.get('score', 'n/a')}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Mission Spectral Plan with Region Context",
        xaxis_title="Wavelength (nm)",
        yaxis=dict(visible=False, range=[0.8, 1.2]),
        template="plotly_white",
        margin=dict(l=30, r=30, t=85, b=35),
        height=430,
    )
    fig.update_xaxes(range=[400, 1800], gridcolor="rgba(148,163,184,0.2)")
    return fig
