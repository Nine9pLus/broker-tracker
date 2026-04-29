"""Persist daily ranking snapshots per broker (data/<a>_<b>.json)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fetch_ranking import StockRow

DATA_DIR = Path(__file__).parent / "data"


def _file_for(broker_a: str, broker_b: str) -> Path:
    return DATA_DIR / f"{broker_a}_{broker_b}.json"


def load(broker_a: str, broker_b: str) -> dict[str, list[StockRow]]:
    path = _file_for(broker_a, broker_b)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save(broker_a: str, broker_b: str, target_date: date, rows: list[StockRow]) -> None:
    if not rows:
        # Skip empty snapshots (e.g., running before market data is published)
        # so they don't pollute the consecutive-day window.
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = load(broker_a, broker_b)
    data[target_date.isoformat()] = rows
    with _file_for(broker_a, broker_b).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
