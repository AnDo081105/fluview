from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest


def test_ilinet_three_week_momentum() -> None:
    fixture = pd.DataFrame(
        {
            "source": ["ILINet"] * 6,
            "season": ["2025-26"] * 6,
            "season_start": [2025] * 6,
            "year": [2025] * 6,
            "week": list(range(40, 46)),
            "season_week": list(range(1, 7)),
            "week_ending": pd.date_range("2025-10-04", periods=6, freq="7D"),
            "geography_type": ["national"] * 6,
            "region": ["National"] * 6,
            "metric": ["ILI"] * 6,
            "unit": ["percent"] * 6,
            "value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "preliminary": [True] * 6,
        }
    )
    sql_path = Path(__file__).parents[1] / "sql" / "models" / "ilinet_metrics.sql"
    con = duckdb.connect()
    try:
        con.register("ilinet", fixture)
        result = con.execute(sql_path.read_text(encoding="utf-8")).df()
    finally:
        con.close()
    latest = result.sort_values("season_week").iloc[-1]
    assert latest["trailing_3wk"] == pytest.approx(5.0)
    assert latest["previous_3wk"] == pytest.approx(2.0)
    assert latest["momentum_3wk"] == pytest.approx(3.0)
    assert latest["historical_n"] == 0


def test_processed_percentiles_have_valid_bounds() -> None:
    path = Path(__file__).parents[1] / "data" / "processed" / "ilinet_metrics.parquet"
    frame = pd.read_parquet(path)
    observed = frame["historical_percentile"].dropna()
    assert observed.between(0, 100).all()
    assert frame["historical_n"].between(0, 10).all()
