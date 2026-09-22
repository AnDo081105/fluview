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

class FluViewDash(Dash):
    def interpolate_index(self, **kwargs):
        return """<!DOCTYPE html>
<html>
    <head>
        {metas}
        <title>{title}</title>
        {favicon}
        {css}
    </head>
    <body>
        <!--
THESIS: FluView Pulse is a live scientific figure plate, not a themed
dashboard; it refuses decorative metaphor, floating cards, and branding.
OWN-WORLD: Cool stock, carbon rules, slate text, cobalt current-series
ink, muted brick emphasis, numbered figures, captions, square controls.
STORY: Read current observations, compare national and regional evidence
in one opening spread, then inspect or export exact records.
FIRST VIEWPORT: Running head with lockup and one ruled observation string;
one outlined-chip row; FIG. 01 left, FIG. 02-03 stacked right; notes close.
FORM: Indexed Figure Plate, Comparative Plate Spread, seed 8304678e;
approved comp .impeccable/mocks/comparative-spread.png.
FINISH: unreviewed and undocumented is unfinished; this build ends with
the finish review, the verdict, and DESIGN.md
-->
        {app_entry}
        {config}
        {scripts}
        {renderer}
    </body>
</html>
""".format_map(kwargs)


app = FluViewDash(__name__, title="FluView Pulse", suppress_callback_exceptions=True)
server = app.server


def _figure_panel(
    graph_id: str,
    number: str,
    title: str,
    caption: str,
    class_name: str = "",
) -> html.Section:
    classes = "figure-panel"
    if class_name:
        classes = f"{classes} {class_name}"
    return html.Section(
        [
            html.Header(
                [
                    html.Span(f"FIG. {number}", className="figure-number"),
                    html.H2(title),
                ],
                className="figure-heading",
            ),
            dcc.Graph(id=graph_id, config={"displayModeBar": False}),
            html.P(caption, className="figure-caption"),
        ],
        className=classes,
    )


def _source_status(source: str, label: str) -> html.Div:
    status = MANIFEST["sources"][source]
    state = "Current snapshot" if status["ok"] else "Last valid snapshot"
    return html.Div(
        [
            html.Span(label, className="status-source"),
            html.Span(state, className=f"status-state {'ok' if status['ok'] else 'warning'}"),
            html.Span(
                f"Through {status['surveillance_through']} · retrieved "
                f"{status['retrieved_at'][:10]}",
                className="status-date",
            ),
        ],
        className="status-item",
    )


def _observation_line(
    season: str,
    ili_latest: pd.Series,
    fastest: pd.Series,
    hosp_latest: pd.Series,
) -> list:
    season_label = str(season).replace("-", "–")
    return [
        html.Span(f"{season_label} season", className="observation-fact"),
        html.Span(
            f"National ILINet {ili_latest['value']:.2f}%, week ending "
            f"{ili_latest['week_ending']:%b %d %Y}",
            className="observation-fact",
        ),
        html.Span(
            f"{fastest['region']}, {fastest['momentum_3wk']:+.2f} percentage "
            "points over 3 weeks",
            className="observation-fact",
        ),
        html.Span(
            f"FluSurv-NET {hosp_latest['value']:.2f} per 100,000, week ending "
            f"{hosp_latest['week_ending']:%b %d %Y}",
            className="observation-fact",
        ),
    ]


def _overview() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    _figure_panel(
                        "ili-context",
                        "01",
                        "Outpatient respiratory illness in seasonal context",
                        "National ILINet compared with recent influenza seasons.",
                        "figure-01",
                    ),
                    html.Div(
                        [
                            _figure_panel(
                                "hhs-momentum",
                                "02",
                                "Largest recent increases by HHS region",
                                "Latest three-week change in outpatient ILI percentage points.",
                                "figure-02",
                            ),
                            _figure_panel(
                                "hhs-heatmap",
                                "03",
                                "Regional intensity across the selected season",
                                "Weekly outpatient ILI percentages by HHS region.",
                                "figure-03",
                            ),
                        ],
                        className="supporting-figures",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    _source_status("ilinet", "ILINet"),
                                    _source_status("flusurv", "FluSurv-NET"),
                                ],
                                className="source-ledger",
                            ),
                            html.P(
                                "Source notes: ILINet is outpatient ILI, not laboratory-confirmed "
                                "influenza. FluSurv-NET is a selected-county hospitalization "
                                "network. Values are preliminary and subject to revision.",
                                className="plate-notes",
                            ),
                        ],
                        className="spread-close",
                    ),
                ],
                className="opening-plate",
            ),
            html.Div(
                [
                    _figure_panel(
                        "hosp-context",
                        "04",
                        "FluSurv-NET hospitalization rate",
                        "The selected season compared with recent seasons.",
                    ),
                    _figure_panel(
                        "hosp-age",
                        "05",
                        "Age groups are affected unevenly",
                        "Latest weekly hospitalization rates by age group.",
                    ),
                    _figure_panel(
                        "aligned",
                        "06",
                        "Parallel signals, not a combined severity index",
                        "ILINet and FluSurv-NET shown separately with their own units.",
                    ),
                ],
                className="continuation-plate",
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
                style_table={
                    "width": "100%",
                    "maxWidth": "100%",
                    "maxHeight": "640px",
                    "overflowX": "auto",
                    "overflowY": "auto",
                },
                style_cell={
                    "fontFamily": "Public Sans, Segoe UI, sans-serif",
                    "fontSize": 13,
                    "padding": "10px",
                    "textAlign": "left",
                    "minWidth": "110px",
                    "width": "140px",
                    "maxWidth": "140px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_header={"fontWeight": 700, "backgroundColor": "#F4F5F3"},
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#ECEEE9"}
                ],
            ),
        ],
        className="analysis-panel",
    )


app.layout = html.Div(
    [
        html.Header(
            [
                html.H1("FluView Pulse"),
                html.P(id="metric-cards", className="observation-line"),
            ],
            className="running-head",
        ),
        dcc.Tabs(
            [
                dcc.Tab(label="Guided overview", children=_overview()),
                dcc.Tab(label="Analysis view", children=_analysis()),
            ],
            className="figure-tabs",
            parent_className="tab-parent",
            content_className="plate-body",
            mobile_breakpoint=0,
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Current surveillance season", htmlFor="season-filter"),
                        dcc.Dropdown(
                            id="season-filter",
                            options=[{"label": value, "value": value} for value in SEASONS],
                            value=DEFAULT_SEASON,
                            clearable=False,
                        ),
                    ],
                    className="season-control",
                ),
                html.Button(
                    "Download filtered CSV",
                    id="header-download",
                    className="button-quiet",
                ),
                html.A(
                    "Methods & source",
                    href="https://github.com/AnDo081105/fluview",
                    target="_blank",
                    className="head-link",
                ),
            ],
            className="plate-toolbar",
        ),
        dcc.Download(id="download"),
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
    **{"data-direction": "indexed-figure-plate-8304678e"},
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
    return (
        _observation_line(season, ili_latest, fastest, hosp_latest),
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
    Input("header-download", "n_clicks"),
    State("analysis-source", "value"),
    State("season-filter", "value"),
    State("analysis-region", "value"),
    prevent_initial_call=True,
)
def download_table(
    _: int | None,
    __: int | None,
    source: str,
    season: str,
    region: str,
):
    if not region:
        region = "National" if source == "ilinet" else "FluSurv-NET"
    subset = _filtered_analysis(source, season, region)
    return dcc.send_data_frame(
        subset.to_csv,
        f"fluview-pulse_{source}_{season}_{region}.csv".replace(" ", "-"),
        index=False,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8050")), debug=False)
