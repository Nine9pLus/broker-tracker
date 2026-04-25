"""Parse the BROKERS env var into Broker entries."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Broker:
    a: str
    b: str
    label: str

    @property
    def key(self) -> str:
        return f"{self.a}_{self.b}"


def parse(value: str) -> list[Broker]:
    """Parse 'a:b:label,a:b:label,...' into Broker list."""
    entries: list[Broker] = []
    for raw in value.split(","):
        token = raw.strip()
        if not token:
            continue
        parts = token.split(":")
        if len(parts) < 3:
            raise ValueError(f"Bad BROKERS entry: {token!r} (expect a:b:label)")
        a, b, *label_parts = parts
        label = ":".join(label_parts).strip()
        entries.append(Broker(a=a.strip(), b=b.strip(), label=label))
    if not entries:
        raise ValueError("BROKERS is empty")
    return entries


def from_env() -> list[Broker]:
    return parse(os.getenv("BROKERS", "9800:9800:元大證券"))
