# broker-tracker — 券商分點買超選股工具

每天收盤後抓富邦 e 證券「券商進出排行」（zgb0），把**今日買超前 N 名**與**連續 N 個交易日都進前 K 名**的股票推到 Telegram。每個券商各發一封獨立訊息。

## 設計

- **資料源**：`https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a=<broker>&b=<branch>&c=B&e=<date>&f=<date>`
  - `c=B` 表示金額（單位：仟元）
  - **多券商**：在 `.env` 用 `BROKERS=a:b:label,a:b:label,...` 列舉
  - 頁面為 Big5 編碼；憑證缺 SKI，因此用 `verify=False` 抓取
- **歷史**：每個券商一個檔 `data/<a>_<b>.json`（`{"YYYY-MM-DD": [{rank, code, name, buy, sell, net}, ...]}`）
- **訊息**：`notify.py` 直接 import 同目錄的 `telegram_outbound.py`，純文字 ≤4096 字

## 檔案

| 檔案 | 用途 |
|------|------|
| `fetch_ranking.py` | 抓 URL + 解析 HTML（買超表，前 50 列）|
| `brokers.py` | 解析 `BROKERS` env，產生多券商清單 |
| `store.py` | 讀寫 `data/<a>_<b>.json` |
| `analyze.py` | `top_n` 與 `consecutive_in_top(days, top_n)` |
| `notify.py` | 從 `.env` 讀 token/target，呼叫 `telegram_outbound.send_message_via_bot` |
| `telegram_outbound.py` | Bot API sendMessage（stdlib only）|
| `daily_run.py` | 每日入口：對每個券商各跑一次（各自存、各自分析、各發一封 Telegram）|
| `backfill_test.py` | 測試入口：兩家券商各跑 2026-04-20 ~ 04-24 |
| `find_chat_id.py` | 從 Bot `getUpdates` 列出可用的 chat_id |
| `send_test.py` | 發一則測試訊息驗證 token + chat_id 可用 |
| `register_task.ps1` | 註冊 Windows Task Scheduler（週一~五 15:00，任務名 `BrokerTracker_1500`）|

## 安裝

需要 Python 3.10+（本機用 uv 安裝的 3.14）。

```
cd /d E:\broker-tracker
"C:\Users\ShihTH\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe" -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## 建立新 Telegram bot

1. 在 Telegram 找 [`@BotFather`](https://t.me/BotFather)，傳 `/newbot`，依指示命名（建議 username 含 `broker` 或 `tracker`）。
2. 取得 token（形如 `123456:ABC-DEF...`），填入 `.env` 的 `TG_BOT_TOKEN=`。
3. 把新 bot 加入要接收訊息的群組，**或**直接 DM bot 一次 `/start`。
4. 列出 chat_id：
   ```
   .venv\Scripts\python find_chat_id.py
   ```
   群組 id 通常是負數（如 `-1001234567890`）；DM 是正數。把要送的 id 填入 `.env` 的 `TG_TARGET=`。
5. 發測試訊息驗證：
   ```
   .venv\Scripts\python send_test.py
   ```
   Telegram 收到 `[broker-tracker test] Telegram bot is working...` 就成功。

## 設定（`.env`）

```
TG_BOT_TOKEN=<新 bot 的 token>
TG_TARGET=<chat_id>
BROKERS=9800:9800:元大證券,9200:9268:凱基-台北
DAILY_TOP_N=5
CONSECUTIVE_DAYS=5
CONSECUTIVE_TOP_N=10
```

## 使用

**單日抓取（不發 Telegram）**
```
.venv\Scripts\python fetch_ranking.py --date 2026-4-24 --broker-a 9800 --broker-b 9800 --top 10
```

**測試 5 日 backfill（會發 Telegram，每家券商一封）**
```
.venv\Scripts\python backfill_test.py
```

**今日入口（會發 Telegram，遇假日自動退到上一個交易日）**
```
.venv\Scripts\python daily_run.py
```

**註冊每日 15:00 排程**
```
powershell -ExecutionPolicy Bypass -File .\register_task.ps1
```

**移除排程**
```
Unregister-ScheduledTask -TaskName 'BrokerTracker_1500' -Confirm:$false
```

## 訊息格式範例

每個券商獨立發送一封：

```
【元大證券 買超排行】2026-04-24（五）
券商分點：a=9800 b=9800　單位：仟元

─ 今日前5 ─
1. 2330 台積電  +2,952,812
2. 3189 景碩  +1,735,808
3. 0050 元大台灣50  +1,305,149
4. 00631L 元大台灣50正2  +1,191,960
5. 2454 聯發科  +976,341

─ 連3日入榜前10 ─
(無)

─ 連5日入榜前10 ─
(無)
```

## 驗證

| 動作 | 預期結果 |
|------|----------|
| `fetch_ranking.py --date 2026-4-24 ...` | 印出 10 列（中文正常需 `PYTHONIOENCODING=utf-8 PYTHONUTF8=1`）|
| `send_test.py` | Telegram 收到測試訊息 |
| `backfill_test.py` | `data/9800_9800.json` 與 `data/9200_9268.json` 各有 5 個日期 key；Telegram 收到 2 封測試報告 |
| `Get-ScheduledTask -TaskName 'BrokerTracker_*'` | 任務 Ready |
