"""Send messages to Telegram via local telegram_outbound module."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from telegram_outbound import send_message_via_bot

_ENV_LOADED = False


def _load_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    load_dotenv(Path(__file__).parent / ".env")
    _ENV_LOADED = True


def send(text: str) -> None:
    _load_env()
    token = os.getenv("TG_BOT_TOKEN", "").strip()
    target = os.getenv("TG_TARGET", "").strip()
    if not token or not target:
        raise RuntimeError("TG_BOT_TOKEN or TG_TARGET missing in broker-tracker/.env")
    if len(text) > 4096:
        text = text[:4080] + "\n…(已截斷)"
    send_message_via_bot(token, target, text)
