from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFEST_PATH = DATA_DIR / "manifest.json"
SQL_DIR = ROOT / "sql" / "models"


@dataclass(frozen=True)
class SourceStatus:
    source: str
    ok: bool
    retrieved_at: str
    surveillance_through: str | None
    snapshot: str | None
    rows: int
    message: str = ""
