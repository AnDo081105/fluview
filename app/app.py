from __future__ import annotations

import os

import pandas as pd
from dash import Dash, Input, Output, State, callback, dash_table, dcc, html

from app.data import load_data
from app.figures import (
    aligned_indicators,
    hhs_heatmap,
    hhs_momentum,
    hospitalization_by_age,
    hospitalization_context,
    ilinet_season_context,
)

ILINET, FLUSURV, MANIFEST = load_data()
SEASONS = sorted(set(ILINET["season"]).intersection(FLUSURV["season"]))
DEFAULT_SEASON = SEASONS[-1]

app = Dash(__name__, title="FluView Pulse", suppress_callback_exceptions=True)
server = app.server


def _source_status(source: str, label: str) -> html.Div:
    status = MANIFEST["sources"][source]
    state = "Current snapshot" if status["ok"] else "Last valid snapshot"
    return html.Div(
        [
            html.Span(label, className="status-source"),
            html.Span(state, className=f"status-pill {'ok' if status['ok'] else 'warning'}"),
            html.Span(
                f"Through {status['surveillance_through']} · retrieved "
                f"{status['retrieved_at'][:10]}",
                className="status-date",
            ),
        ],
        className="status-item",
    )


def _card(label: str, value: str, detail: str) -> html.Div:
    return html.Div(
        [
            html.P(label, className="metric-label"),
            html.H3(value, className="metric-value"),
            html.P(detail, className="metric-detail"),
        ],
        className="metric-card",
    )


def _overview() -> html.Div:
    return html.Div(
        [
            html.Div(id="metric-cards", className="metric-grid"),
            html.Div(
                [
                    dcc.Graph(id="ili-context", config={"displayModeBar": False}),
                    dcc.Graph(id="hhs-momentum", config={"displayModeBar": False}),
                ],
                className="chart-grid",
            ),
            html.Div(
                [
                    dcc.Graph(id="hhs-heatmap", config={"displayModeBar": False}),
                    dcc.Graph(id="hosp-context", config={"displayModeBar": False}),
                ],
                className="chart-grid",
            ),
            html.Div(
                [
                    dcc.Graph(id="hosp-age", config={"displayModeBar": False}),
                    dcc.Graph(id="aligned", config={"displayModeBar": False}),
                ],
                className="chart-grid",
            ),
            html.Div(
                [
                    html.H3("Read these signals carefully"),
                    html.P(
                        "ILINet is the percentage of outpatient visits meeting the ILI "
                        "definition; it is not laboratory-confirmed influenza. FluSurv-NET "
                        "captures laboratory-confirmed hospitalizations in selected counties "
                        "across 14 states, about 10% of the U.S. population. Both feeds are "
                        "preliminary and recent weeks can be revised."
                    ),
                ],
                className="method-callout",
            ),
        ]
    )


def _analysis() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Indicator"),
                            dcc.Dropdown(
                                id="analysis-source",
                                options=[
                                    {"label": "ILINet outpatient illness", "value": "ilinet"},
                                    {
                                        "label": "FluSurv-NET hospitalizations",
                                        "value": "flusurv",
                                    },
                                ],
                                value="ilinet",
                                clearable=False,
                            ),
                        ],
                        className="control",
                    ),
                    html.Div(
                        [
                            html.Label("Geography"),
                            dcc.Dropdown(id="analysis-region", clearable=False),
                        ],
                        className="control",
                    ),
                    html.Button("Download filtered CSV", id="download-button", className="button"),
                    dcc.Download(id="download"),
                ],
                className="analysis-controls",
            ),
            html.P(
                "Use this table to inspect the values behind the guided story. Momentum is "
                "the latest trailing three-week mean minus the preceding trailing three-week "
                "mean. Historical percentiles use up to ten prior seasons.",
                className="analysis-note",
            ),
            dash_table.DataTable(
                id="analysis-table",
                page_size=20,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_cell={
                    "fontFamily": "Inter, Arial, sans-serif",
                    "fontSize": 13,
                    "padding": "10px",
                    "textAlign": "left",
                    "minWidth": "110px",
                },
                style_header={"fontWeight": 700, "backgroundColor": "#edf5f5"},
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#f8fafc"}
                ],
            ),
        ],
        className="analysis-panel",
    )


app.layout = html.Div(
    [
        html.Header(
            [
                html.Div(
                    [
                        html.P("CDC RESPIRATORY SURVEILLANCE", className="eyebrow"),
                        html.H1("FluView Pulse"),
                        html.P(
                            "Where outpatient respiratory illness is increasing—and how "
                            "influenza hospitalization rates differ by age.",
                            className="subtitle",
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Label("Season", htmlFor="season-filter"),
                        dcc.Dropdown(
                            id="season-filter",
                            options=[{"label": value, "value": value} for value in SEASONS],
                            value=DEFAULT_SEASON,
                            clearable=False,
                        ),
                    ],
                    className="season-control",
                ),
            ],
            className="hero",
        ),
        html.Div(
            [_source_status("ilinet", "ILINet"), _source_status("flusurv", "FluSurv-NET")],
            className="status-bar",
        ),
        dcc.Tabs(
            [
                dcc.Tab(label="Guided overview", children=_overview()),
                dcc.Tab(label="Analysis view", children=_analysis()),
            ],
            className="tabs",
        ),
        html.Footer(
            [
                html.Span("Public aggregate surveillance data · No PHI"),
                html.A(
                    "Methods & source",
                    href="https://github.com/AnDo081105/fluview",
                    target="_blank",
                ),
            ]
        ),
    ],
    className="page-shell",
)


@callback(
    Output("metric-cards", "children"),
    Output("ili-context", "figure"),
    Output("hhs-momentum", "figure"),
    Output("hhs-heatmap", "figure"),
    Output("hosp-context", "figure"),
    Output("hosp-age", "figure"),
    Output("aligned", "figure"),
    Input("season-filter", "value"),
)
def update_overview(season: str):
    national = ILINET.query("season == @season and region == 'National'").sort_values(
        "week_ending"
    )
    overall_hosp = FLUSURV.query(
        "season == @season and region == 'FluSurv-NET' and age_group == 'Overall'"
    ).sort_values("week_ending")
    hhs = ILINET.query("season == @season and geography_type == 'hhs'")
    latest_hhs = hhs.sort_values("week_ending").groupby("region", as_index=False).tail(1)
    fastest = latest_hhs.sort_values("momentum_3wk", ascending=False).iloc[0]
    ili_latest = national.iloc[-1]
    hosp_latest = overall_hosp.iloc[-1]
    cards = [
        _card(
            "National ILINet",
            f"{ili_latest['value']:.2f}%",
            f"Week ending {ili_latest['week_ending']:%b %d, %Y}",
        ),
        _card(
            "Largest HHS increase",
            str(fastest["region"]),
            f"{fastest['momentum_3wk']:+.2f} percentage points over 3 weeks",
        ),
        _card(
            "FluSurv-NET weekly rate",
            f"{hosp_latest['value']:.2f}",
            f"Per 100,000 · week ending {hosp_latest['week_ending']:%b %d, %Y}",
        ),
    ]
    return (
        cards,
        ilinet_season_context(ILINET, season),
        hhs_momentum(ILINET, season),
        hhs_heatmap(ILINET, season),
        hospitalization_context(FLUSURV, season),
        hospitalization_by_age(FLUSURV, season),
        aligned_indicators(ILINET, FLUSURV, season),
    )


@callback(
    Output("analysis-region", "options"),
    Output("analysis-region", "value"),
    Input("analysis-source", "value"),
)
def update_regions(source: str):
    frame = ILINET if source == "ilinet" else FLUSURV
    regions = sorted(frame["region"].dropna().unique())
    preferred = "National" if source == "ilinet" else "FluSurv-NET"
    return [{"label": value, "value": value} for value in regions], preferred


def _filtered_analysis(source: str, season: str, region: str) -> pd.DataFrame:
    frame = ILINET if source == "ilinet" else FLUSURV
    subset = frame.query("season == @season and region == @region").copy()
    columns = [
        "week_ending",
        "season",
        "region",
        *(["age_group"] if source == "flusurv" else []),
        "value",
        "trailing_3wk",
        "momentum_3wk",
        "historical_percentile",
        "historical_n",
        "unit",
    ]
    subset = subset[columns].sort_values("week_ending", ascending=False)
    subset["week_ending"] = subset["week_ending"].dt.strftime("%Y-%m-%d")
    return subset


@callback(
    Output("analysis-table", "data"),
    Output("analysis-table", "columns"),
    Input("analysis-source", "value"),
    Input("season-filter", "value"),
    Input("analysis-region", "value"),
)
def update_table(source: str, season: str, region: str):
    if not region:
        return [], []
    subset = _filtered_analysis(source, season, region)
    columns = [{"name": value.replace("_", " ").title(), "id": value} for value in subset]
    return subset.to_dict("records"), columns


@callback(
    Output("download", "data"),
    Input("download-button", "n_clicks"),
    State("analysis-source", "value"),
    State("season-filter", "value"),
    State("analysis-region", "value"),
    prevent_initial_call=True,
)
def download_table(_: int, source: str, season: str, region: str):
    subset = _filtered_analysis(source, season, region)
    return dcc.send_data_frame(
        subset.to_csv,
        f"fluview-pulse_{source}_{season}_{region}.csv".replace(" ", "-"),
        index=False,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8050")), debug=False)
