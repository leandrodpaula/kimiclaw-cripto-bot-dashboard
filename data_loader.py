"""Carrega e normaliza os dados exportados pelo kimiclaw-cripto-bot.

Por padrão lê a pasta ``../kimiclaw-cripto-bot/data``. O caminho pode ser
sobrescrito pela variável de ambiente ``BOT_DATA_PATH``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_BOT_DATA = Path(__file__).resolve().parent.parent / "kimiclaw-cripto-bot" / "data"


def _data_dir() -> Path:
    env = os.environ.get("BOT_DATA_PATH")
    if env:
        return Path(env)
    return DEFAULT_BOT_DATA


def _load_json(path: Path, default: dict | None = None) -> dict:
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def load_bot_state() -> dict:
    return _load_json(_data_dir() / "bot_state.json")


def load_positions() -> pd.DataFrame:
    raw = _load_json(_data_dir() / "positions.json", {"positions": []})
    rows = raw.get("positions", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    numeric_cols = ["entry_price", "quantity", "invested_usdt", "stop_loss", "take_profit", "trailing_peak", "score"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "opened_at" in df.columns:
        df["opened_at"] = pd.to_datetime(df["opened_at"], errors="coerce", utc=True)
    return df


def load_history() -> pd.DataFrame:
    raw = _load_json(_data_dir() / "history.json", {"trades": []})
    rows = raw.get("trades", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    numeric_cols = ["entry_price", "exit_price", "quantity", "pnl_usdt", "pnl_pct"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["opened_at", "closed_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    if "mode" not in df.columns:
        df["mode"] = "paper"
    return df


def load_equity() -> pd.DataFrame:
    raw = _load_json(_data_dir() / "equity.json", {"snapshots": []})
    rows = raw.get("snapshots", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    numeric_cols = ["balance_usdt", "realized_pnl_usdt", "unrealized_pnl_usdt"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "mode" not in df.columns:
        df["mode"] = "paper"
    return df


def load_signals_history() -> pd.DataFrame:
    raw = _load_json(_data_dir() / "signals_history.json", {"cycles": []})
    rows = []
    for cycle in raw.get("cycles", []):
        ts = cycle.get("timestamp")
        mode = cycle.get("mode", "paper")
        for symbol, info in cycle.get("signals", {}).items():
            rows.append(
                {
                    "timestamp": ts,
                    "mode": mode,
                    "symbol": symbol,
                    "signal": info.get("signal"),
                    "score": info.get("score"),
                    "price": info.get("price"),
                }
            )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df


def load_settings() -> dict:
    return _load_json(_data_dir().parent / "config" / "settings.json")


def load_coins() -> pd.DataFrame:
    raw = _load_json(_data_dir().parent / "config" / "coins.json", {"coins": []})
    return pd.DataFrame(raw.get("coins", []))


def load_all() -> dict:
    return {
        "state": load_bot_state(),
        "positions": load_positions(),
        "history": load_history(),
        "equity": load_equity(),
        "signals": load_signals_history(),
        "settings": load_settings(),
        "coins": load_coins(),
    }
