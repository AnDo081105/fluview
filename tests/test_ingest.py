from __future__ import annotations

import pandas as pd
import pytest

from fluview.ingest.flusurv import normalize_flusurv
from fluview.ingest.ilinet import normalize_ilinet


def test_normalize_ilinet_assigns_season_and_metric() -> None:
    raw = pd.DataFrame(
        {
            "REGION TYPE": ["National", "HHS Regions"],
            "REGION": ["X", "Region 1"],
            "YEAR": [2025, 2026],
            "WEEK": [40, 1],
            "% WEIGHTED ILI": [2.1, 3.2],
            "ILITOTAL": [21, 32],
        }
    )
    result = normalize_ilinet(raw)
    assert result["season"].tolist() == ["2025-26", "2025-26"]
    assert result["season_week"].tolist() == [1, 15]
    assert result["geography_type"].tolist() == ["national", "hhs"]
    assert result["region"].tolist()[0] == "National"


def test_normalize_ilinet_rejects_schema_drift() -> None:
    with pytest.raises(ValueError, match="schema drift"):
        normalize_ilinet(pd.DataFrame({"YEAR": [2025], "WEEK": [40]}))


def test_normalize_flusurv_preserves_age_and_coverage() -> None:
    raw = pd.DataFrame(
        {
            "season": ["2025-26"],
            "date": ["2025-10-04"],
            "age_category": ["65+ yr"],
            "state": ["Overall"],
            "estimate": ["1.5"],
            "estimate_type": ["Rate per 100,000"],
            "rate_type": ["Observed"],
        }
    )
    result = normalize_flusurv(raw)
    assert result.loc[0, "region"] == "FluSurv-NET"
    assert result.loc[0, "geography_type"] == "network"
    assert result.loc[0, "age_group"] == "65+ yr"
    assert result.loc[0, "value"] == 1.5
