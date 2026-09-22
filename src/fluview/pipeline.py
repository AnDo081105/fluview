from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

from fluview.config import MANIFEST_PATH, PROCESSED_DIR, RAW_DIR, SQL_DIR, SourceStatus
from fluview.ingest.common import latest_snapshot
from fluview.ingest.flusurv import fetch_flusurv
from fluview.ingest.ilinet import fetch_ilinet, load_last_valid_ilinet


def _surveillance_through(frame: pd.DataFrame) -> str | None:
    if frame.empty or "week_ending" not in frame:
        return None
    value = pd.to_datetime(frame["week_ending"], errors="coerce").max()
    return None if pd.isna(value) else value.date().isoformat()


def _cached(source: str) -> tuple[pd.DataFrame, Path]:
    path = latest_snapshot(RAW_DIR / source, source)
    if path is None:
        raise FileNotFoundError(f"No cached {source} snapshot is available")
    return pd.read_csv(path, parse_dates=["week_ending"]), path


def _load_source(source: str, offline: bool) -> tuple[pd.DataFrame, SourceStatus]:
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
    if offline:
        frame, path = _cached(source)
        return frame, SourceStatus(
            source=source,
            ok=True,
            retrieved_at=str(frame.get("retrieved_at", pd.Series([retrieved_at])).iloc[-1]),
            surveillance_through=_surveillance_through(frame),
            snapshot=str(path.relative_to(RAW_DIR.parent)),
            rows=len(frame),
            message="Loaded cached snapshot in offline mode.",
        )
    try:
        if source == "ilinet":
            frame, path, retrieved_at = fetch_ilinet(RAW_DIR)
        else:
            frame, path, retrieved_at = fetch_flusurv(RAW_DIR)
        return frame, SourceStatus(
            source=source,
            ok=True,
            retrieved_at=retrieved_at,
            surveillance_through=_surveillance_through(frame),
            snapshot=str(path.relative_to(RAW_DIR.parent)),
            rows=len(frame),
        )
    except Exception as error:
        if source == "ilinet":
            frame, path = load_last_valid_ilinet(RAW_DIR)
        else:
            frame, path = _cached(source)
        return frame, SourceStatus(
            source=source,
            ok=False,
            retrieved_at=str(frame.get("retrieved_at", pd.Series([retrieved_at])).iloc[-1]),
            surveillance_through=_surveillance_through(frame),
            snapshot=str(path.relative_to(RAW_DIR.parent)),
            rows=len(frame),
            message=f"Refresh failed; retained last valid snapshot: {error}",
        )


def _build_marts(ilinet: pd.DataFrame, flusurv: pd.DataFrame) -> dict[str, int]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.register("ilinet", ilinet)
        con.register("flusurv", flusurv)
        outputs: dict[str, int] = {}
        for name, frame in (("ilinet", ilinet), ("flusurv", flusurv)):
            path = PROCESSED_DIR / f"{name}.parquet"
            frame.to_parquet(path, index=False)
            outputs[name] = len(frame)
        for model in ("ilinet_metrics", "flusurv_metrics"):
            sql = (SQL_DIR / f"{model}.sql").read_text(encoding="utf-8")
            result = con.execute(sql).df()
            result.to_parquet(PROCESSED_DIR / f"{model}.parquet", index=False)
            outputs[model] = len(result)
        return outputs
    finally:
        con.close()


def refresh(offline: bool = False) -> dict:
    ilinet, ilinet_status = _load_source("ilinet", offline)
    flusurv, flusurv_status = _load_source("flusurv", offline)
    outputs = _build_marts(ilinet, flusurv)
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sources": {
            status.source: {
                "ok": status.ok,
                "retrieved_at": status.retrieved_at,
                "surveillance_through": status.surveillance_through,
                "snapshot": status.snapshot,
                "rows": status.rows,
                "message": status.message,
            }
            for status in (ilinet_status, flusurv_status)
        },
        "outputs": outputs,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh FluView Pulse data.")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Rebuild processed data from the latest cached snapshots.",
    )
    args = parser.parse_args()
    print(json.dumps(refresh(offline=args.offline), indent=2))


if __name__ == "__main__":
    main()
