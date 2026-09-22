from __future__ import annotations

from app.app import app


def test_dash_index_loads() -> None:
    response = app.server.test_client().get("/")
    assert response.status_code == 200
    assert b"FluView Pulse" in response.data
