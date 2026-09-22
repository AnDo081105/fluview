from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests

from fluview.ingest.common import retrieval_stamp, write_snapshot

API_URL = "https://data.cdc.gov/resource/kvib-3txy.json"
PAGE_SIZE = 50_000
WHERE = (
    "surveillance_network='FluSurv-NET' "
    "AND race='All' AND sex='All' AND data_type='Weekly Rate'"
)


def normalize_flusurv(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "season",
        "date",
        "age_category",
        "state",
        "estimate",
        "estimate_type",
        "rate_type",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"FluSurv-NET schema drift: missing columns {sorted(missing)}")

    result = frame.copy()
    result["value"] = pd.to_numeric(result["estimate"], errors="coerce")
    result["week_ending"] = pd.to_datetime(result["date"], errors="coerce")
    result = result.dropna(subset=["value", "week_ending"]).copy()
    iso = result["week_ending"].dt.isocalendar()
    result["year"] = iso.year.astype(int)
    result["week"] = iso.week.astype(int)
    result["season_start"] = result["season"].str.slice(0, 4).astype(int)
    result["season_week"] = result["week"].where(result["week"] >= 40, result["week"] + 53) - 39
    result["geography_type"] = result["state"].map(
        lambda value: "network" if value == "Overall" else "site"
    )
    result["region"] = result["state"].replace({"Overall": "FluSurv-NET"})
    result["age_group"] = result["age_category"]
    result["source"] = "FluSurv-NET"
    result["metric"] = "Laboratory-confirmed influenza hospitalization rate"
    result["unit"] = "per 100,000"
    result["preliminary"] = True
    columns = [
        "source",
        "season",
        "season_start",
        "year",
        "week",
        "season_week",
        "week_ending",
        "geography_type",
        "region",
        "age_group",
        "metric",
        "unit",
        "value",
        "rate_type",
        "estimate_type",
        "preliminary",
    ]
    return result[columns].sort_values(
        ["region", "age_group", "week_ending", "rate_type"]
    ).drop_duplicates(
        ["season", "week_ending", "region", "age_group"], keep="last"
    )


def fetch_flusurv(raw_dir: Path, timeout: int = 90) -> tuple[pd.DataFrame, Path, str]:
    records: list[dict] = []
    offset = 0
    while True:
        query = urlencode(
            {
                "$limit": PAGE_SIZE,
                "$offset": offset,
                "$where": WHERE,
                "$order": "date, state, age_category",
            }
        )
        response = requests.get(f"{API_URL}?{query}", timeout=timeout)
        response.raise_for_status()
        page = response.json()
        records.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    normalized = normalize_flusurv(pd.DataFrame.from_records(records))
    if len(normalized) < 100:
        raise ValueError(f"FluSurv-NET row count unexpectedly low: {len(normalized)}")
    retrieved_at, stamp = retrieval_stamp()
    normalized["retrieved_at"] = retrieved_at
    path, _ = write_snapshot(normalized, raw_dir / "flusurv", "flusurv", stamp)
    return normalized, path, retrieved_at
