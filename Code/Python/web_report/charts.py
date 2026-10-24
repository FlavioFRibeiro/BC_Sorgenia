"""Grafici di presentazione: nessun calcolo finanziario nel frontend."""
import plotly.graph_objects as go

from data_model import COUNTRIES, fmt

GREEN, RED, INK, MUTED = "#168365", "#BD5A56", "#173C37", "#6C817B"


def style(fig, height=350):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=15, t=25, b=15),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Arial, sans-serif", color=INK, size=12),
                      separators=",.", showlegend=False, hoverlabel=dict(bgcolor="white"))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#E7EEEA", zeroline=True, zerolinecolor="#ABBDB5", tickformat=",.0f")
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
        labels.append(f"{int(key[0])}-{int(key[1]):02d}" if key[0] is not None else "Data non valida")
        values.append(finance.strict_sum(contributions))
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=[GREEN if x is not None and x >= 0 else RED for x in values],
                          customdata=[fmt(x) if x is not None else "Dati incompleti" for x in values],
                          hovertemplate="%{x}<br>P&L: %{customdata} EUR<extra></extra>"))
    fig.update_yaxes(title="EUR")
    return style(fig)


def contribution_chart(values, country=False):
    values = sorted(values, key=lambda pair: (pair[1] is None, pair[1] or 0))
    labels = [COUNTRIES.get(key, key) if country else key for key, _ in values]
    amounts = [value for _, value in values]
    fig = go.Figure(go.Bar(x=amounts, y=labels, orientation="h",
                          marker_color=[GREEN if x is not None and x >= 0 else RED for x in amounts],
                          customdata=[fmt(x) if x is not None else "Dati incompleti" for x in amounts],
                          hovertemplate="%{y}<br>P&L: %{customdata} EUR<extra></extra>"))
    fig.update_xaxes(title="EUR", tickformat=",.0f", zeroline=True, zerolinecolor="#ABBDB5")
    return style(fig, height=300)


def waterfall(stats):
    fig = go.Figure(go.Waterfall(measure=["relative", "relative", "relative", "total"],
                                x=["Ricavi energia", "Ricavi servizi", "Costi energia", "Margine"],
                                y=[stats["revenue_energy"], stats["revenue_service"], -stats["cost_energy"], 0],
                                text=[fmt(stats[k]) for k in ("revenue_energy", "revenue_service", "cost_energy", "known_margin")],
                                textposition="outside", connector=dict(line=dict(color="#CAD6D0")),
                                increasing=dict(marker=dict(color=GREEN)), decreasing=dict(marker=dict(color=RED)),
                                totals=dict(marker=dict(color=INK)), hovertemplate="%{x}<br>%{text} EUR<extra></extra>"))
    fig.update_yaxes(title="EUR")
    return style(fig, height=430)
