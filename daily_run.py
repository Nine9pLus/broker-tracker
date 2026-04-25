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
    hits: list[analyze.ConsecutiveHit],
    daily_top_n: int,
    consecutive_days: int,
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
    lines.append("")
    lines.append(f"─ 連{consecutive_days}日入榜前{consecutive_top_n} ─")
    if not hits:
        lines.append("(無)")
    else:
        for h in hits:
            lines.append(
                f"{h['code']} {h['name']}（連{h['days_in_row']}日，最新買超 +{h['latest_net']:,}）"
            )
    lines.append("")
    lines.append("資料來源：富邦 e 證券 zgb0")
    return "\n".join(lines)


def run_one(broker: brokers.Broker, target_date: date, settings: dict) -> None:
    rows = fetch(target_date, broker.a, broker.b)
    store.save(broker.a, broker.b, target_date, rows)

    history = store.load(broker.a, broker.b)
    top = analyze.top_n(rows, settings["daily_top_n"])
    hits = analyze.consecutive_in_top(
        history,
        days=settings["consecutive_days"],
        top_n=settings["consecutive_top_n"],
    )
    text = build_message(
        broker, target_date, top, hits,
        settings["daily_top_n"], settings["consecutive_days"], settings["consecutive_top_n"],
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
