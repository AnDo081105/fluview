from __future__ import annotations

from app.app import _analysis, app


def test_dash_index_loads() -> None:
    response = app.server.test_client().get("/")
    assert response.status_code == 200
    assert b"FluView Pulse" in response.data


def test_analysis_table_keeps_content_inside_its_scroll_container() -> None:
    table = _analysis().children[2]

    assert table.style_table["width"] == "100%"
    assert table.style_table["maxWidth"] == "100%"
    assert table.style_table["maxHeight"] == "640px"
    assert table.style_table["overflowY"] == "auto"
    assert table.style_cell["width"] == "140px"
    assert table.style_cell["maxWidth"] == "140px"
    assert table.style_cell["overflow"] == "hidden"
    assert table.style_cell["textOverflow"] == "ellipsis"
