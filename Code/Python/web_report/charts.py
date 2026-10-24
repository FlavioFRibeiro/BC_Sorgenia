"""Grafici di presentazione: nessun calcolo finanziario nel frontend."""
import plotly.graph_objects as go

from data_model import COUNTRIES, MONTH_NAMES
from formatting import money, money_scale

GREEN, RED, INK, MUTED = "#168365", "#BD5A56", "#173C37", "#6C817B"


def style(fig, height=350):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=15, t=25, b=15),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Arial, sans-serif", color=INK, size=12),
                      separators=",.", showlegend=False, hoverlabel=dict(bgcolor="white"))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#E7EEEA", zeroline=True, zerolinecolor="#ABBDB5")
    return fig


def monthly_chart(monthly):
    groups = {}
    for row in monthly:
        key = (row["anno"], row["mese"])
        groups.setdefault(key, []).append(row)
    from data_model import finance
    keys = sorted(groups, key=lambda key: (key[0] is None, key))
    labels, values = [], []
    for key in keys:
        contributions = [row["pnl_energy"] for row in groups[key] if row["n_energy"] > 0]
        labels.append(f"{MONTH_NAMES[int(key[1]) - 1][:3]} {int(key[0])}" if key[0] is not None else "Data non valida")
        values.append(finance.strict_sum(contributions))
    divisor, unit = money_scale(values)
    fig = go.Figure(go.Bar(x=labels, y=[x / divisor if x is not None else None for x in values], marker_color=[GREEN if x is not None and x >= 0 else RED for x in values],
                          customdata=[money(x) if x is not None else "Dati incompleti" for x in values],
                          hovertemplate="%{x}<br>P&L: %{customdata}<extra></extra>"))
    fig.update_yaxes(title=unit, tickformat=",.1f", ticksuffix=f" {unit}")
    fig.update_xaxes(type="category")
    return style(fig)


def contribution_chart(values, country=False):
    values = sorted(values, key=lambda pair: (pair[1] is None, pair[1] or 0))
    labels = [COUNTRIES.get(key, key) if country else key for key, _ in values]
    amounts = [value for _, value in values]
    divisor, unit = money_scale(amounts)
    fig = go.Figure(go.Bar(x=[x / divisor if x is not None else None for x in amounts], y=labels, orientation="h",
                          marker_color=[GREEN if x is not None and x >= 0 else RED for x in amounts],
                          customdata=[money(x) if x is not None else "Dati incompleti" for x in amounts],
                          hovertemplate="%{y}<br>P&L: %{customdata}<extra></extra>"))
    fig.update_xaxes(title=unit, tickformat=",.1f", ticksuffix=f" {unit}", zeroline=True, zerolinecolor="#ABBDB5")
    return style(fig, height=300)


def waterfall(stats):
    amounts = [stats["revenue_energy"], stats["revenue_service"], -stats["cost_energy"], stats["known_margin"]]
    divisor, unit = money_scale(amounts)
    fig = go.Figure(go.Waterfall(measure=["relative", "relative", "relative", "total"],
                                x=["Ricavi energia", "Ricavi servizi", "Costi energia", "Margine"],
                                y=[value / divisor for value in amounts[:3]] + [0],
                                text=[money(value) for value in amounts],
                                textposition="outside", connector=dict(line=dict(color="#CAD6D0")),
                                increasing=dict(marker=dict(color=GREEN)), decreasing=dict(marker=dict(color=RED)),
                                totals=dict(marker=dict(color=INK)), hovertemplate="%{x}<br>%{text}<extra></extra>"))
    fig.update_yaxes(title=unit, tickformat=",.1f", ticksuffix=f" {unit}")
    return style(fig, height=430)
