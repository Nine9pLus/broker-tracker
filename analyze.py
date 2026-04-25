"""Selection logic: top-N today, and stocks appearing N consecutive days in top-K."""

from __future__ import annotations

from typing import TypedDict

from fetch_ranking import StockRow


class ConsecutiveHit(TypedDict):
    code: str
    name: str
    days_in_row: int
    latest_net: int


def top_n(rows: list[StockRow], n: int = 5) -> list[StockRow]:
    return rows[:n]


def consecutive_in_top(
    history: dict[str, list[StockRow]],
    days: int = 5,
    top_n: int = 10,
) -> list[ConsecutiveHit]:
    """Return stocks that appear in top-`top_n` for the most recent `days` snapshots.

    Snapshots are taken in chronological order (sorted by date key); we look at the
    last `days` snapshots regardless of calendar gaps (weekends/holidays).
    """
    sorted_dates = sorted(history.keys())
    if len(sorted_dates) < days:
        return []

    window = sorted_dates[-days:]
    daily_top: list[dict[str, StockRow]] = []
    for d in window:
        rows = history.get(d, [])[:top_n]
        daily_top.append({r["code"]: r for r in rows})

    # Codes present in EVERY day of the window
    common_codes: set[str] | None = None
    for day_map in daily_top:
        codes = set(day_map.keys())
        common_codes = codes if common_codes is None else common_codes & codes
    if not common_codes:
        return []

    latest = daily_top[-1]
    hits: list[ConsecutiveHit] = []
    for code in common_codes:
        latest_row = latest[code]
        hits.append(
            ConsecutiveHit(
                code=code,
                name=latest_row["name"],
                days_in_row=days,
                latest_net=latest_row["net"],
            )
        )
    hits.sort(key=lambda h: h["latest_net"], reverse=True)
    return hits
