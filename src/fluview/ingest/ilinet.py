from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

from fluview.ingest.common import latest_snapshot, retrieval_stamp, write_snapshot

META_URL = "https://gis.cdc.gov/flu2/GetPhase02InitApp?appVersion=Public"
DOWNLOAD_URL = "https://gis.cdc.gov/flu2/PostPhase02DataDownload"
HEADERS = {
    "Origin": "https://gis.cdc.gov",
    "Referer": "https://gis.cdc.gov/grasp/fluview/fluportaldashboard.html",
    "User-Agent": "FluView-Pulse/0.1 (public-health portfolio project)",
}


def _snake(value: str) -> str:
    value = value.strip().lower().replace("%", " pct ")
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value)).strip("_")


def _read_download(content: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        frames: list[pd.DataFrame] = []
        for name in archive.namelist():
            if not name.lower().endswith(".csv"):
                continue
            raw = archive.read(name)
            frame = pd.read_csv(io.BytesIO(raw), skiprows=1)
            if len(frame.columns) < 3:
                frame = pd.read_csv(io.BytesIO(raw))
            frames.append(frame)
    if not frames:
        raise ValueError("CDC ILINet response did not contain a CSV file")
    return pd.concat(frames, ignore_index=True)


def _payload(region_type: str, season_ids: list[int]) -> dict:
    if region_type == "national":
        region_id = 3
        subregions = [{"ID": 0, "Name": ""}]
    elif region_type == "hhs":
        region_id = 1
        subregions = [{"ID": value, "Name": str(value)} for value in range(1, 11)]
    else:
        raise ValueError(f"Unsupported ILINet geography: {region_type}")
    return {
        "AppVersion": "Public",
        "DatasourceDT": [{"ID": 1, "Name": "ILINet"}],
        "RegionTypeId": region_id,
        "SeasonsDT": [{"ID": value, "Name": str(value)} for value in season_ids],
        "SubRegionsDT": subregions,
    }


def normalize_ilinet(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.columns = [_snake(str(column)) for column in result.columns]
    aliases = {
        "region_type": "region_type",
        "region": "region",
        "year": "year",
        "week": "week",
        "weighted_ili": "value",
        "weighted_pct_ili": "value",
        "pct_weighted_ili": "value",
        "unweighted_ili": "unweighted_ili",
        "pct_unweighted_ili": "unweighted_ili",
        "ili_total": "ili_total",
        "ilitotal": "ili_total",
        "num_of_providers": "providers",
        "total_patients": "total_patients",
    }
    result = result.rename(columns={key: value for key, value in aliases.items() if key in result})
    required = {"year", "week", "value"}
    missing = required - set(result.columns)
    if missing:
        raise ValueError(f"ILINet schema drift: missing columns {sorted(missing)}")

    if "region" not in result:
        result["region"] = "National"
    result["region"] = result["region"].fillna("National").astype(str)
    result["geography_type"] = result["region"].map(
        lambda value: "national" if value.lower() in {"national", "x"} else "hhs"
    )
    result.loc[result["geography_type"].eq("national"), "region"] = "National"
    result["year"] = pd.to_numeric(result["year"], errors="coerce")
    result["week"] = pd.to_numeric(result["week"], errors="coerce")
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    result = result.dropna(subset=["year", "week", "value"]).copy()
    result[["year", "week"]] = result[["year", "week"]].astype(int)
    result["season_start"] = result["year"].where(result["week"] >= 40, result["year"] - 1)
    result["season"] = result["season_start"].map(
        lambda year: f"{year}-{str(year + 1)[-2:]}"
    )
    result["season_week"] = result["week"].where(result["week"] >= 40, result["week"] + 53) - 39
    result["week_ending"] = pd.to_datetime(
        result["year"].astype(str)
        + result["week"].astype(str).str.zfill(2)
        + "6",
        format="%G%V%u",
        errors="coerce",
    )
    result["source"] = "ILINet"
    result["metric"] = "Outpatient visits meeting ILI definition (%)"
    result["unit"] = "percent"
    result["preliminary"] = True
    numeric_optional = [
        "unweighted_ili",
        "ili_total",
        "providers",
        "total_patients",
        "age_0_4",
        "age_5_24",
        "age_25_49",
        "age_50_64",
        "age_65",
    ]
    for column in numeric_optional:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")
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
        "metric",
        "unit",
        "value",
        "preliminary",
        *[column for column in numeric_optional if column in result],
    ]
    return result[columns].sort_values(["region", "year", "week"]).drop_duplicates(
        ["region", "year", "week"], keep="last"
    )


def fetch_ilinet(raw_dir: Path, timeout: int = 90) -> tuple[pd.DataFrame, Path, str]:
    metadata = requests.get(META_URL, headers=HEADERS, timeout=timeout)
    metadata.raise_for_status()
    season_ids = sorted(
        [int(item["seasonid"]) for item in metadata.json()["seasons"]], reverse=True
    )[:11]
    frames = []
    for region_type in ("national", "hhs"):
        response = requests.post(
            DOWNLOAD_URL,
            headers=HEADERS,
            json=_payload(region_type, season_ids),
            timeout=timeout,
        )
        response.raise_for_status()
        frames.append(_read_download(response.content))
    normalized = normalize_ilinet(pd.concat(frames, ignore_index=True))
    if len(normalized) < 100:
        raise ValueError(f"ILINet row count unexpectedly low: {len(normalized)}")
    retrieved_at, stamp = retrieval_stamp()
    normalized["retrieved_at"] = retrieved_at
    path, _ = write_snapshot(normalized, raw_dir / "ilinet", "ilinet", stamp)
    return normalized, path, retrieved_at


def load_last_valid_ilinet(raw_dir: Path) -> tuple[pd.DataFrame, Path]:
    path = latest_snapshot(raw_dir / "ilinet", "ilinet")
    if path is None:
        raise FileNotFoundError("No cached ILINet snapshot is available")
    return pd.read_csv(path, parse_dates=["week_ending"]), path
