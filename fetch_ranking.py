"""Fetch broker buy-super stock ranking from Fubon e-broker (zgb0.djhtm).

URL pattern:
  https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm
    ?a=<broker>&b=<branch>&c=B&e=YYYY-M-D&f=YYYY-M-D

`c=B` returns amount in 仟元 (thousand TWD).
The page contains both 買超 (left table) and 賣超 (right table); we parse only 買超.

Each data row has one `<td class="t4t1">` (stock id+name) and three `<td class="t3n1">`
(buy amount, sell amount, net difference). Stock id+name appears in two forms:
  1) <SCRIPT>GenLink2stk('AS2330','台積電');</SCRIPT>  (prefix 'AS' = TWSE)
  2) <a href="javascript:Link2Stk('00631L');">00631L元大台灣50正2</a>
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import TypedDict

import requests
import urllib3
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv

# Fubon's HTTPS cert lacks Subject Key Identifier; Python's stricter checks reject it
# even though curl/browsers accept it. Disable verification for this read-only public page.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class StockRow(TypedDict):
    rank: int
    code: str
    name: str
    buy: int
    sell: int
    net: int


URL = "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_GENLINK_RE = re.compile(r"GenLink2stk\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")
_LINK2STK_RE = re.compile(r"Link2Stk\(\s*'([^']+)'\s*\)")


def _strip_market_prefix(raw_id: str) -> str:
    # 'AS2330' -> '2330'; '0050' -> '0050'; '00631L' -> '00631L'
    return re.sub(r"^[A-Z]+", "", raw_id)


def _parse_int(text: str) -> int:
    cleaned = text.replace(",", "").strip()
    if not cleaned or cleaned in ("-", "--"):
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0


def _extract_code_name(td: Tag) -> tuple[str, str] | None:
    # Form 1: <SCRIPT>GenLink2stk('AS2330','台積電');</SCRIPT>
    script = td.find("script") or td.find("SCRIPT")
    if script and script.string:
        m = _GENLINK_RE.search(script.string)
        if m:
            return _strip_market_prefix(m.group(1)), m.group(2).strip()

    # Form 2: <a href="javascript:Link2Stk('00631L');">00631L元大台灣50正2</a>
    a = td.find("a")
    if a is not None:
        text = a.get_text(strip=True)
        m = _LINK2STK_RE.search(a.get("href", ""))
        if m:
            code = m.group(1)
            name = text[len(code):].strip() if text.startswith(code) else text
            return code, name

    return None


def _find_buy_super_table(soup: BeautifulSoup) -> Tag | None:
    for header_td in soup.find_all("td", class_="t2"):
        if header_td.get_text(strip=True) == "買超":
            return header_td.find_parent("table")
    return None


def parse(html: str) -> list[StockRow]:
    soup = BeautifulSoup(html, "lxml")
    table = _find_buy_super_table(soup)
    if table is None:
        return []

    rows: list[StockRow] = []
    for tr in table.find_all("tr"):
        name_td = tr.find("td", class_="t4t1")
        if name_td is None:
            continue
        code_name = _extract_code_name(name_td)
        if code_name is None:
            continue
        num_tds = tr.find_all("td", class_="t3n1")
        if len(num_tds) < 3:
            continue
        code, name = code_name
        rows.append(
            StockRow(
                rank=len(rows) + 1,
                code=code,
                name=name,
                buy=_parse_int(num_tds[0].get_text()),
                sell=_parse_int(num_tds[1].get_text()),
                net=_parse_int(num_tds[2].get_text()),
            )
        )
    return rows


def fetch(target_date: date, broker_a: str, broker_b: str, *, timeout: int = 30) -> list[StockRow]:
    date_str = f"{target_date.year}-{target_date.month}-{target_date.day}"
    params = {
        "a": broker_a,
        "b": broker_b,
        "c": "B",
        "e": date_str,
        "f": date_str,
    }
    resp = requests.get(
        URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        verify=False,
    )
    resp.raise_for_status()
    # Page declares charset=big5; requests' guess may be wrong.
    resp.encoding = "big5"
    return parse(resp.text)


def _cli() -> int:
    load_dotenv(Path(__file__).parent / ".env")
    import os

    parser = argparse.ArgumentParser(description="Fetch Fubon broker buy-super ranking.")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--broker-a", default="9800")
    parser.add_argument("--broker-b", default="9800")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    _ = os  # keep import for future env-driven defaults

    y, m, d = (int(x) for x in args.date.split("-"))
    rows = fetch(date(y, m, d), args.broker_a, args.broker_b)
    if not rows:
        print(f"[fetch_ranking] no data for {args.date}", file=sys.stderr)
        return 1

    for r in rows[: args.top]:
        print(f"{r['rank']:>2}. {r['code']:<8} {r['name']:<16}  +{r['net']:>12,} 仟元")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
