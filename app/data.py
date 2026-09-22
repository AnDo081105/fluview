from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    processed = DATA / "processed"
    required = [
        processed / "ilinet_metrics.parquet",
        processed / "flusurv_metrics.parquet",
        DATA / "manifest.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(
            "Processed data is missing. Run `python -m fluview.pipeline` first. "
            f"Missing: {', '.join(missing)}"
        )
    ilinet = pd.read_parquet(required[0])
    flusurv = pd.read_parquet(required[1])
    manifest = json.loads(required[2].read_text(encoding="utf-8"))
    return ilinet, flusurv, manifest


def latest_rows(frame: pd.DataFrame, group_by: list[str]) -> pd.DataFrame:
    return (
        frame.sort_values("week_ending")
        .groupby(group_by, as_index=False, dropna=False)
        .tail(1)
    )
