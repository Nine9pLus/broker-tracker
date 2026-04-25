"""Print chat_id from Bot getUpdates.

Use after creating the bot and either:
  (a) sending /start to the bot in a DM, or
  (b) adding the bot to a group/channel and sending any message there.

Then run:  python find_chat_id.py

Copy the chat_id you want into TG_TARGET in .env.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    load_dotenv(Path(__file__).parent / ".env")
    token = os.getenv("TG_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: TG_BOT_TOKEN missing in .env", file=sys.stderr)
        return 1

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    if not d.get("ok"):
        print(d)
        return 1

    seen: dict[int, tuple[str, str]] = {}
    for up in d.get("result") or []:
        msg = up.get("message") or up.get("channel_post") or up.get("edited_message")
        if not msg:
            continue
        ch = msg.get("chat") or {}
        cid = ch.get("id")
        if cid is None:
            continue
        title = (
            ch.get("title")
            or ch.get("username")
            or ch.get("first_name")
            or ""
        )
        typ = ch.get("type") or ""
        seen[int(cid)] = (typ, title)

    if not seen:
        print(
            "No updates. Send a message to the bot (DM /start, or post in the group), "
            "then run again. Note: getUpdates only shows the last ~24h of messages."
        )
        return 0

    print("Use one of these as TG_TARGET in .env:\n")
    for cid, (typ, title) in sorted(seen.items(), key=lambda x: x[0]):
        print(f"  chat_id={cid}  type={typ}  title={title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
