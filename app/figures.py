from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

STOCK = "#F4F5F3"
INK = "#17232D"
MUTED = "#66727B"
CURRENT = "#315C78"
EMPHASIS = "#9A483D"
GRID = "#D7DCDE"
HISTORY = "#C8CED0"
TYPEFACE = "Public Sans, Segoe UI, sans-serif"
AGE_BANDS = ["0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", "65-74 yr", "75-84 yr", "85+ yr"]


def _finish(figure: go.Figure, title: str, height: int = 410) -> go.Figure:
    del title
    figure.update_layout(
        height=height,
        margin={"l": 54, "r": 20, "t": 18, "b": 48},
        paper_bgcolor=STOCK,
        plot_bgcolor=STOCK,
        font={"family": TYPEFACE, "color": INK, "size": 11},
        title={"text": None},
        legend={
            "orientation": "h",
            "y": -0.22,
            "font": {"size": 10},
            "bgcolor": "rgba(0,0,0,0)",
        },
        coloraxis_colorbar={"outlinewidth": 0, "tickfont": {"size": 10, "color": MUTED}},
        hoverlabel={
            "bgcolor": STOCK,
            "bordercolor": INK,
            "font_color": INK,
            "font_family": TYPEFACE,
        },
    )
    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=GRID,
        tickcolor=GRID,
        title_font={"size": 11, "color": MUTED},
        tickfont={"size": 10, "color": MUTED},
    )
    figure.update_yaxes(
        gridcolor=GRID,
        zeroline=False,
        linecolor=GRID,
        tickcolor=GRID,
        title_font={"size": 11, "color": MUTED},
        tickfont={"size": 10, "color": MUTED},
    )
    return figure


def ilinet_season_context(frame: pd.DataFrame, season: str) -> go.Figure:
    data = frame.query("region == 'National'").copy()
    history = data[data["season"] != season]
    recent_seasons = sorted(history["season"].unique())[-5:]
    recent = history[history["season"].isin(recent_seasons)]
    band = recent.groupby("season_week")["value"].agg(["min", "max", "median"])
    figure = go.Figure()
    if not band.empty:
        figure.add_trace(
            go.Scatter(
                x=list(band.index) + list(band.index[::-1]),
                y=list(band["max"]) + list(band["min"][::-1]),
                fill="toself",
                fillcolor="rgba(200,206,208,0.38)",
                line={"width": 0, "color": HISTORY},
                name="Prior-season range",
                hoverinfo="skip",
                showlegend=True,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=band.index,
                y=band["median"],
                mode="lines",
                line={"color": MUTED, "width": 1.4, "dash": "dash"},
                name="Prior-season median",
                hovertemplate="Median<br>Season week %{x}<br>%{y:.2f}%<extra></extra>",
            )
        )
    current = data[data["season"] == season]
    figure.add_trace(
        go.Scatter(
            x=current["season_week"],
            y=current["value"],
            mode="lines+markers",
            line={"color": CURRENT, "width": 2.5},
            marker={"size": 5, "color": CURRENT, "symbol": "circle"},
            name=season,
            hovertemplate="Season week %{x}<br>%{y:.2f}%<extra></extra>",
        )
    )
    if not current.empty:
        latest = current.sort_values("season_week").iloc[-1]
        figure.add_annotation(
            x=latest["season_week"],
            y=latest["value"],
            text=f"{latest['value']:.2f}%",
            showarrow=False,
            xanchor="left",
            xshift=8,
            font={"family": TYPEFACE, "size": 12, "color": CURRENT},
        )
    figure.update_xaxes(title="Season week (week 40 = 1)")
    figure.update_yaxes(title="Outpatient visits meeting ILI definition (%)")
    return _finish(figure, "Outpatient respiratory illness in seasonal context", height=470)


def hhs_momentum(frame: pd.DataFrame, season: str) -> go.Figure:
    current = frame.query("season == @season and geography_type == 'hhs'")
    current = (
        current.sort_values("week_ending")
        .groupby("region", as_index=False)
        .tail(1)
        .dropna(subset=["momentum_3wk"])
        .sort_values("momentum_3wk")
    )
    peak = current["momentum_3wk"].max()
    colors = [
        EMPHASIS if value == peak and value > 0 else CURRENT
        for value in current["momentum_3wk"]
    ]
    figure = go.Figure(
        go.Bar(
            x=current["momentum_3wk"],
            y=current["region"],
            orientation="h",
            marker={
                "color": colors,
                "line": {"width": 0},
            },
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
    return _finish(figure, "Largest recent increases by HHS region", height=190)


def hhs_heatmap(frame: pd.DataFrame, season: str) -> go.Figure:
    current = frame.query("season == @season and geography_type == 'hhs'").copy()
    pivot = current.pivot_table(
        index="region", columns="season_week", values="value", aggfunc="last"
    )
    figure = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=["#E7ECEC", CURRENT, EMPHASIS],
        labels={"x": "Season week", "y": "", "color": "ILI %"},
    )
    figure.update_traces(hovertemplate="%{y}<br>Season week %{x}<br>%{z:.2f}%<extra></extra>")
    return _finish(figure, f"Regional intensity across {season}", height=190)


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
                line={
                    "color": EMPHASIS if active else HISTORY,
                    "width": 2.5 if active else 1,
                    "dash": "solid" if active else "dot",
                },
                marker={"size": 5, "symbol": "diamond", "color": EMPHASIS},
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
            marker_color=CURRENT,
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
            line={"color": CURRENT, "width": 2.5},
            marker={"size": 4, "symbol": "circle", "color": CURRENT},
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
            line={"color": EMPHASIS, "width": 2.5},
            marker={"size": 4, "symbol": "diamond", "color": EMPHASIS},
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
