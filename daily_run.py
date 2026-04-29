"""Daily entry: fetch each broker's ranking, persist, analyze, send one Telegram per broker."""

from __future__ import annotations

import os
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

import analyze
import brokers
import notify
import store
from fetch_ranking import StockRow, fetch

WEEKDAY_LABEL = ["一", "二", "三", "四", "五", "六", "日"]


def build_message(
    broker: brokers.Broker,
    target_date: date,
    top: list[StockRow],
    windows: list[tuple[int, list[analyze.ConsecutiveHit]]],
    daily_top_n: int,
    consecutive_top_n: int,
) -> str:
    lines: list[str] = []
    lines.append(
        f"【{broker.label} 買超排行】{target_date:%Y-%m-%d}（{WEEKDAY_LABEL[target_date.weekday()]}）"
    )
    lines.append(f"券商分點：a={broker.a} b={broker.b}　單位：仟元")
    lines.append("")
    lines.append(f"─ 今日前{daily_top_n} ─")
    if not top:
        lines.append("(查無資料)")
    else:
        for r in top:
            lines.append(f"{r['rank']}. {r['code']} {r['name']}  +{r['net']:,}")

    for days, hits in windows:
        lines.append("")
        lines.append(f"─ 連{days}日入榜前{consecutive_top_n} ─")
        if not hits:
            lines.append("(無)")
        else:
            for h in hits:
                lines.append(
                    f"{h['code']} {h['name']}（連{h['days_in_row']}日，最新買超 +{h['latest_net']:,}）"
                )

    return "\n".join(lines)


def parse_days_list(raw: str) -> list[int]:
    return [int(p.strip()) for p in raw.split(",") if p.strip()]


def previous_weekdays(target_date: date, n: int) -> list[date]:
    """Return the `n` weekdays strictly before `target_date`, oldest first."""
    out: list[date] = []
    d = target_date - timedelta(days=1)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


def ensure_history(broker: brokers.Broker, target_date: date, lookback_days: int) -> None:
    """Backfill any missing weekday snapshots in the [target-lookback, target-1] window."""
    history = store.load(broker.a, broker.b)
    for d in previous_weekdays(target_date, lookback_days):
        if history.get(d.isoformat()):
            continue
        try:
            rows = fetch(d, broker.a, broker.b)
        except Exception as e:
            print(f"  backfill {broker.label} {d} failed: {e}", file=sys.stderr)
            continue
        if rows:
            store.save(broker.a, broker.b, d, rows)
            print(f"  backfilled {broker.label} {d}: {len(rows)} rows")


def run_one(broker: brokers.Broker, target_date: date, settings: dict) -> None:
    lookback = max(settings["consecutive_days"]) if settings["consecutive_days"] else 5
    ensure_history(broker, target_date, lookback)

    rows = fetch(target_date, broker.a, broker.b)
    store.save(broker.a, broker.b, target_date, rows)

    history = store.load(broker.a, broker.b)
    top = analyze.top_n(rows, settings["daily_top_n"])
    windows = [
        (
            days,
            analyze.consecutive_in_top(
                history, days=days, top_n=settings["consecutive_top_n"], as_of=target_date
            ),
        )
        for days in settings["consecutive_days"]
    ]
    text = build_message(
        broker, target_date, top, windows,
        settings["daily_top_n"], settings["consecutive_top_n"],
    )
    notify.send(text)
    print(text)
    print()


def main() -> int:
    load_dotenv(Path(__file__).parent / ".env")
    broker_list = brokers.from_env()
    settings = {
        "daily_top_n": int(os.getenv("DAILY_TOP_N", "5")),
        "consecutive_days": parse_days_list(os.getenv("CONSECUTIVE_DAYS", "5")),
        "consecutive_top_n": int(os.getenv("CONSECUTIVE_TOP_N", "10")),
    }

    today = date.today()
    while today.weekday() >= 5:
        today -= timedelta(days=1)

    rc = 0
    for broker in broker_list:
        try:
            run_one(broker, today, settings)
        except Exception:
            rc = 1
            tb = traceback.format_exc()[-3000:]
            print(tb, file=sys.stderr)
            try:
                notify.send(f"[trading 執行失敗] {broker.label} {today}\n{tb}")
            except Exception as e:
                print(f"notify failed for {broker.label}: {e}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
