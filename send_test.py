"""Send a test Telegram message to verify TG_BOT_TOKEN + TG_TARGET work."""

from __future__ import annotations

import sys
from datetime import datetime

import notify


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        notify.send(f"[broker-tracker test] Telegram bot is working. ({now})")
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    print("OK: test message sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
