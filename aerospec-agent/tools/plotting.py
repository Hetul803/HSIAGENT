"""Plotting utilities for selected spectral regions."""
from __future__ import annotations

import plotly.graph_objects as go


DOMAIN_BANDS = [
    (400, 700, "Visible"),
    (700, 1000, "NIR"),
    (1000, 2500, "SWIR"),
]


def plot_selected_regions(recommendations: list[dict]) -> go.Figure:
    fig = go.Figure()

    for lo, hi, label in DOMAIN_BANDS:
        fig.add_vrect(x0=lo, x1=hi, fillcolor="lightgray", opacity=0.09, line_width=0)
        fig.add_annotation(x=(lo + hi) / 2, y=1.07, xref="x", yref="paper", text=label, showarrow=False, font=dict(size=10))

    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    for idx, item in enumerate(recommendations):
        lo, hi = item["range_nm"]
        color = palette[idx % len(palette)]
        fig.add_trace(
            go.Bar(
                x=[(lo + hi) / 2],
                y=[1],
                width=[max(hi - lo, 10)],
                marker_color=color,
                opacity=0.65,
                text=[f"{item['id']}<br>{lo:.0f}-{hi:.0f}nm"],
                textposition="inside",
                hovertemplate=(
                    "<b>%{text}</b><br>Score: "
                    + str(item.get("score", "n/a"))
                    + "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Selected Spectral Regions (with domain context)",
        xaxis_title="Wavelength (nm)",
        yaxis=dict(visible=False, range=[0, 1.25]),
        template="plotly_white",
        margin=dict(l=30, r=30, t=65, b=30),
        height=320,
    )
    fig.update_xaxes(range=[400, 1800], tickmode="array", tickvals=[400, 550, 700, 860, 1000, 1380, 1610, 1800])
    return fig
