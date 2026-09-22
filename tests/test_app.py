from __future__ import annotations

from collections.abc import Iterator

import plotly.graph_objects as go

from app import figures
from app.app import _analysis, _figure_panel, _overview, app
from app.figures import _finish


def _component_tree(component: object) -> Iterator[object]:
    if isinstance(component, list | tuple):
        for child in component:
            yield from _component_tree(child)
        return

    if not hasattr(component, "to_plotly_json"):
        return

    yield component
    yield from _component_tree(getattr(component, "children", None))


def _class_names(component: object) -> set[str]:
    return {
        class_name
        for item in _component_tree(component)
        for class_name in str(getattr(item, "className", "")).split()
    }


def _component_with_class(component: object, class_name: str) -> object:
    return next(
        item
        for item in _component_tree(component)
        if class_name in str(getattr(item, "className", "")).split()
    )


def _component_with_id(component: object, component_id: str) -> object:
    return next(
        item for item in _component_tree(component) if getattr(item, "id", None) == component_id
    )


def _assert_figure_contract(
    overview: object,
    graph_id: str,
    number: str,
    title: str,
    caption: str,
) -> None:
    panel = next(
        item
        for item in _component_tree(overview)
        if "figure-panel" in str(getattr(item, "className", "")).split()
        and any(
            getattr(descendant, "id", None) == graph_id
            for descendant in _component_tree(item)
        )
    )

    assert _component_with_id(panel, graph_id).config == {"displayModeBar": False}
    assert _component_with_class(panel, "figure-number").children == f"FIG. {number}"
    assert next(
        item for item in _component_tree(panel) if item.__class__.__name__ == "H2"
    ).children == title
    assert _component_with_class(panel, "figure-caption").children == caption


def test_dash_index_loads() -> None:
    response = app.server.test_client().get("/")
    assert response.status_code == 200
    assert b"FluView Pulse" in response.data


def test_analysis_table_keeps_content_inside_its_scroll_container() -> None:
    table = _analysis().children[2]

    assert table.style_table["width"] == "100%"
    assert table.style_table["maxWidth"] == "100%"
    assert table.style_table["maxHeight"] == "640px"
    assert table.style_table["overflowX"] == "auto"
    assert table.style_table["overflowY"] == "auto"
    assert table.style_cell["width"] == "140px"
    assert table.style_cell["maxWidth"] == "140px"
    assert table.style_cell["overflow"] == "hidden"
    assert table.style_cell["textOverflow"] == "ellipsis"


def test_layout_exposes_indexed_figure_plate_structure() -> None:
    running_head = _component_with_class(app.layout, "running-head")
    source_ledger = _component_with_class(app.layout, "source-ledger")
    tabs = _component_with_class(app.layout, "figure-tabs")
    toolbar = _component_with_class(app.layout, "plate-toolbar")

    assert running_head.className == "running-head"
    assert source_ledger.className == "source-ledger"
    assert tabs.className == "figure-tabs"
    assert toolbar.className == "plate-toolbar"
    assert "observation-line" in _class_names(running_head)
    assert _component_with_id(toolbar, "header-download").id == "header-download"
    assert _component_with_id(toolbar, "season-filter").id == "season-filter"
    assert (
        app.layout.to_plotly_json()["props"]["data-direction"]
        == "indexed-figure-plate-8304678e"
    )
    guided_overview = _overview()
    assert "observation-line" not in _class_names(guided_overview)
    assert {
        "opening-plate",
        "supporting-figures",
        "continuation-plate",
    } <= _class_names(guided_overview)

    opening_plate = _component_with_class(guided_overview, "opening-plate")
    supporting_figures = _component_with_class(guided_overview, "supporting-figures")
    continuation_plate = _component_with_class(guided_overview, "continuation-plate")

    assert "figure-01" in _class_names(opening_plate)
    assert {
        item.id
        for item in _component_tree(supporting_figures)
        if item.__class__.__name__ == "Graph"
    } == {"hhs-momentum", "hhs-heatmap"}
    assert {
        item.id
        for item in _component_tree(continuation_plate)
        if item.__class__.__name__ == "Graph"
    } == {"hosp-context", "hosp-age", "aligned"}

    figure_contracts = [
        (
            "ili-context",
            "01",
            "Outpatient respiratory illness in seasonal context",
            "National ILINet compared with recent influenza seasons.",
        ),
        (
            "hhs-momentum",
            "02",
            "Largest recent increases by HHS region",
            "Latest three-week change in outpatient ILI percentage points.",
        ),
        (
            "hhs-heatmap",
            "03",
            "Regional intensity across the selected season",
            "Weekly outpatient ILI percentages by HHS region.",
        ),
        (
            "hosp-context",
            "04",
            "FluSurv-NET hospitalization rate",
            "The selected season compared with recent seasons.",
        ),
        (
            "hosp-age",
            "05",
            "Age groups are affected unevenly",
            "Latest weekly hospitalization rates by age group.",
        ),
        (
            "aligned",
            "06",
            "Parallel signals, not a combined severity index",
            "ILINet and FluSurv-NET shown separately with their own units.",
        ),
    ]
    for contract in figure_contracts:
        _assert_figure_contract(guided_overview, *contract)


def test_figure_panel_exposes_number_title_caption_and_graph() -> None:
    title = "Outpatient respiratory illness in seasonal context"
    caption = "National ILINet compared with recent influenza seasons."
    panel = _figure_panel(
        "ili-context",
        "01",
        title,
        caption,
        "figure-01",
    )

    assert "figure-panel" in panel.className
    assert "figure-01" in panel.className
    assert _component_with_class(panel, "figure-number").children == "FIG. 01"
    assert next(
        item for item in _component_tree(panel) if item.__class__.__name__ == "H2"
    ).children == title
    assert _component_with_id(panel, "ili-context").config == {"displayModeBar": False}
    assert _component_with_class(panel, "figure-caption").children == caption


def test_shared_figure_theme_uses_publication_palette() -> None:
    figure = _finish(go.Figure(), "Field observation")

    assert figure.layout.paper_bgcolor == figures.STOCK
    assert figure.layout.plot_bgcolor == figures.STOCK
    assert figure.layout.font.color == figures.INK
    assert figure.layout.hoverlabel.bgcolor == figures.STOCK
    assert figures.CURRENT == "#315C78"
    assert figures.EMPHASIS == "#9A483D"
