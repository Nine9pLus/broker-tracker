"""Backfill 5 trading days (2026-04-20 ~ 2026-04-24) for each broker, send a report each."""

from __future__ import annotations

import os
import sys
import traceback
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

import analyze
import brokers
import notify
import store
from daily_run import build_message
from fetch_ranking import fetch

DATES = [
    date(2026, 4, 20),
    date(2026, 4, 21),
    date(2026, 4, 22),
    date(2026, 4, 23),
    date(2026, 4, 24),
]


def backfill_broker(broker: brokers.Broker, settings: dict) -> None:
    for d in DATES:
        rows = fetch(d, broker.a, broker.b)
        store.save(broker.a, broker.b, d, rows)
        print(f"  {broker.label} {d}: {len(rows)} rows")

    history = store.load(broker.a, broker.b)
    latest = DATES[-1]
    top = analyze.top_n(history[latest.isoformat()], settings["daily_top_n"])
    hits = analyze.consecutive_in_top(
        history,
        days=settings["consecutive_days"],
        top_n=settings["consecutive_top_n"],
    )
    body = build_message(
        broker, latest, top, hits,
        settings["daily_top_n"], settings["consecutive_days"], settings["consecutive_top_n"],
    )
    text = (
        f"【測試報告】backfill {DATES[0]:%Y-%m-%d} ~ {DATES[-1]:%Y-%m-%d}\n"
        f"已寫入 {len(DATES)} 個交易日資料\n\n"
        f"{body}"
    )
    notify.send(text)
    print(text)
    print()


def main() -> int:
    load_dotenv(Path(__file__).parent / ".env")
    broker_list = brokers.from_env()
    settings = {
        "daily_top_n": int(os.getenv("DAILY_TOP_N", "5")),
        "consecutive_days": int(os.getenv("CONSECUTIVE_DAYS", "5")),
        "consecutive_top_n": int(os.getenv("CONSECUTIVE_TOP_N", "10")),
    }

    rc = 0
    for broker in broker_list:
        print(f"=== {broker.label} ({broker.a}/{broker.b}) ===")
        try:
            backfill_broker(broker, settings)
        except Exception:
            rc = 1
            tb = traceback.format_exc()[-3000:]
            print(tb, file=sys.stderr)
            try:
                notify.send(f"[trading backfill 執行失敗] {broker.label}\n{tb}")
            except Exception as e:
                print(f"notify failed for {broker.label}: {e}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
