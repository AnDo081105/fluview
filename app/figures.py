from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

INK = "#14213d"
MUTED = "#718096"
TEAL = "#007c83"
CORAL = "#e76f51"
GOLD = "#e9c46a"
GRID = "#e8edf2"
AGE_BANDS = ["0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", "65-74 yr", "75-84 yr", "85+ yr"]


def _finish(figure: go.Figure, title: str, height: int = 410) -> go.Figure:
    figure.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left"},
        height=height,
        margin={"l": 52, "r": 24, "t": 70, "b": 48},
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter, Arial, sans-serif", "color": INK},
        legend={"orientation": "h", "y": -0.2},
        hoverlabel={"bgcolor": "white", "font_color": INK},
    )
    figure.update_xaxes(showgrid=False, zeroline=False)
    figure.update_yaxes(gridcolor=GRID, zeroline=False)
    return figure


def ilinet_season_context(frame: pd.DataFrame, season: str) -> go.Figure:
    data = frame.query("region == 'National'").copy()
    history = data[data["season"] != season]
    recent_seasons = sorted(history["season"].unique())[-5:]
    figure = go.Figure()
    for name in recent_seasons:
        subset = history[history["season"] == name]
        figure.add_trace(
            go.Scatter(
                x=subset["season_week"],
                y=subset["value"],
                mode="lines",
                line={"color": "#d7dee7", "width": 1},
                name=name,
                hovertemplate=f"{name}<br>Season week %{{x}}<br>%{{y:.2f}}%<extra></extra>",
            )
        )
    current = data[data["season"] == season]
    figure.add_trace(
        go.Scatter(
            x=current["season_week"],
            y=current["value"],
            mode="lines+markers",
            line={"color": TEAL, "width": 3},
            marker={"size": 5},
            name=season,
            hovertemplate="Season week %{x}<br>%{y:.2f}%<extra></extra>",
        )
    )
    figure.update_xaxes(title="Season week (week 40 = 1)")
    figure.update_yaxes(title="Outpatient visits meeting ILI definition (%)")
    return _finish(figure, "Outpatient respiratory illness in seasonal context")


def hhs_momentum(frame: pd.DataFrame, season: str) -> go.Figure:
    current = frame.query("season == @season and geography_type == 'hhs'")
    current = (
        current.sort_values("week_ending")
        .groupby("region", as_index=False)
        .tail(1)
        .dropna(subset=["momentum_3wk"])
        .sort_values("momentum_3wk")
    )
    colors = [CORAL if value > 0 else TEAL for value in current["momentum_3wk"]]
    figure = go.Figure(
        go.Bar(
            x=current["momentum_3wk"],
            y=current["region"],
            orientation="h",
            marker_color=colors,
            customdata=current[["value", "historical_percentile", "historical_n"]],
            hovertemplate=(
                "%{y}<br>3-week change: %{x:+.2f} pp"
                "<br>Latest: %{customdata[0]:.2f}%"
                "<br>Historical percentile: %{customdata[1]:.0f}"
                " (n=%{customdata[2]})<extra></extra>"
            ),
        )
    )
    figure.add_vline(x=0, line_color=MUTED, line_width=1)
    figure.update_xaxes(title="Latest 3-week mean minus preceding 3-week mean (pp)")
    figure.update_yaxes(title="")
    return _finish(figure, "Largest recent increases by HHS region")


def hhs_heatmap(frame: pd.DataFrame, season: str) -> go.Figure:
    current = frame.query("season == @season and geography_type == 'hhs'").copy()
    pivot = current.pivot_table(
        index="region", columns="season_week", values="value", aggfunc="last"
    )
    figure = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=["#f3f7f7", GOLD, CORAL],
        labels={"x": "Season week", "y": "", "color": "ILI %"},
    )
    figure.update_traces(hovertemplate="%{y}<br>Season week %{x}<br>%{z:.2f}%<extra></extra>")
    return _finish(figure, f"Regional intensity across {season}", height=430)


def hospitalization_context(frame: pd.DataFrame, season: str) -> go.Figure:
    data = frame.query("region == 'FluSurv-NET' and age_group == 'Overall'").copy()
    seasons = sorted(data["season"].unique())
    compare = [name for name in seasons if name != season][-4:] + [season]
    figure = go.Figure()
    for name in compare:
        subset = data[data["season"] == name]
        active = name == season
        figure.add_trace(
            go.Scatter(
                x=subset["season_week"],
                y=subset["value"],
                mode="lines+markers" if active else "lines",
                line={"color": CORAL if active else "#d7dee7", "width": 3 if active else 1},
                marker={"size": 5},
                name=name,
                hovertemplate=f"{name}<br>Season week %{{x}}<br>%{{y:.2f}} per 100k<extra></extra>",
            )
        )
    figure.update_xaxes(title="Season week (week 40 = 1)")
    figure.update_yaxes(title="Weekly hospitalizations per 100,000")
    return _finish(figure, "FluSurv-NET hospitalization rate")


def hospitalization_by_age(frame: pd.DataFrame, season: str) -> go.Figure:
    data = frame.query(
        "season == @season and region == 'FluSurv-NET' and age_group in @AGE_BANDS"
    )
    latest = (
        data.sort_values("week_ending")
        .groupby("age_group", as_index=False)
        .tail(1)
        .sort_values("value", ascending=False)
    )
    figure = go.Figure(
        go.Bar(
            x=latest["age_group"],
            y=latest["value"],
            marker_color=TEAL,
            customdata=latest[["historical_percentile", "historical_n"]],
            hovertemplate=(
                "%{x}<br>%{y:.2f} per 100k"
                "<br>Historical percentile: %{customdata[0]:.0f}"
                " (n=%{customdata[1]})<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(
        title="Age group",
        categoryorder="array",
        categoryarray=AGE_BANDS,
    )
    figure.update_yaxes(title="Weekly hospitalizations per 100,000")
    return _finish(figure, "Age groups are affected unevenly")


def aligned_indicators(
    ilinet: pd.DataFrame, flusurv: pd.DataFrame, season: str
) -> go.Figure:
    ili = ilinet.query("season == @season and region == 'National'")
    hosp = flusurv.query(
        "season == @season and region == 'FluSurv-NET' and age_group == 'Overall'"
    )
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.16,
        subplot_titles=("ILINet outpatient respiratory illness", "FluSurv-NET hospitalizations"),
    )
    figure.add_trace(
        go.Scatter(
            x=ili["season_week"],
            y=ili["value"],
            line={"color": TEAL, "width": 3},
            name="ILINet",
            hovertemplate="Season week %{x}<br>%{y:.2f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=hosp["season_week"],
            y=hosp["value"],
            line={"color": CORAL, "width": 3},
            name="FluSurv-NET",
            hovertemplate="Season week %{x}<br>%{y:.2f} per 100k<extra></extra>",
        ),
        row=2,
        col=1,
    )
    figure.update_yaxes(title="ILI visits (%)", row=1, col=1)
    figure.update_yaxes(title="Rate per 100k", row=2, col=1)
    figure.update_xaxes(title="Season week", row=2, col=1)
    return _finish(figure, "Parallel signals, not a combined severity index", height=540)
