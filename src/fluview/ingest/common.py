from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def retrieval_stamp(now: datetime | None = None) -> tuple[str, str]:
    value = now or datetime.now(UTC)
    return value.isoformat(timespec="seconds"), value.strftime("%Y-%m-%dT%H%M%SZ")


def write_snapshot(
    frame: pd.DataFrame,
    directory: Path,
    source: str,
    stamp: str,
) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{source}_{stamp}.csv.gz"
    frame.to_csv(path, index=False, compression="gzip")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = {
        "source": source,
        "rows": len(frame),
        "sha256": digest,
        "snapshot": path.name,
    }
    path.with_suffix(path.suffix + ".json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return path, digest


def latest_snapshot(directory: Path, source: str) -> Path | None:
    candidates = sorted(directory.glob(f"{source}_*.csv.gz"))
    return candidates[-1] if candidates else None
