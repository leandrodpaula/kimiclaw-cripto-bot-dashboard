"""Carrega dados do MongoDB Atlas ou, opcionalmente, de arquivos JSON locais.

Por padrão conecta no Atlas usando ``MONGODB_URI`` e ``MONGODB_DB`` do ``.env``.
Se ``BOT_DATA_PATH`` estiver definido, lê os JSONs locais do bot (modo legacy/fallback).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Carrega .env antes de qualquer coisa.
load_dotenv()


def _mongodb_uri() -> str | None:
    return os.environ.get("MONGODB_URI")


def _mongodb_db() -> str:
    return os.environ.get("MONGODB_DB") or "kimi_trader"


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "kimiclaw-cripto-bot" / "data"


def _data_dir() -> Path:
    env = os.environ.get("BOT_DATA_PATH")
    return Path(env) if env else _default_data_dir()


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


# ---------------------------------------------------------------------------
# MongoDB client singleton
# ---------------------------------------------------------------------------
_mongo_client = None
_mongodb_available: bool | None = None


def _get_client():
    global _mongo_client
    if _mongo_client is None:
        from pymongo import MongoClient

        uri = _mongodb_uri()
        if not uri:
            raise RuntimeError("MONGODB_URI não configurado no .env")
        _mongo_client = MongoClient(
            uri,
            maxPoolSize=10,
            minPoolSize=0,
            maxIdleTimeMS=60_000,
            connectTimeoutMS=5_000,
            serverSelectionTimeoutMS=5_000,
            socketTimeoutMS=10_000,
        )
    return _mongo_client


def _db():
    return _get_client()[_mongodb_db()]


def _check_mongodb() -> bool:
    """Tenta pingar o Atlas; em caso de erro, desativa MongoDB para a sessão."""
    global _mongodb_available
    if _mongodb_available is not None:
        return _mongodb_available
    if _mongodb_uri() is None:
        _mongodb_available = False
        return False
    try:
        _get_client().admin.command("ping")
        _mongodb_available = True
    except Exception as exc:
        print(f"[data_loader] MongoDB indisponível: {exc}")
        _mongodb_available = False
    return _mongodb_available


def _using_mongodb() -> bool:
    return _check_mongodb() and _data_dir() is None


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_bot_state(mode: str = "paper") -> dict:
    if _using_mongodb():
        doc = _db()["bot_state"].find_one({"mode": mode}, sort={"updated_at": -1})
        if doc:
            doc.pop("_id", None)
            return doc
        return {}
    path = _data_dir() / "bot_state.json"
    return _load_json(path)


def load_positions(mode: str = "paper") -> pd.DataFrame:
    if _using_mongodb():
        rows = list(_db()["positions"].find({"mode": mode}, {"_id": 0}))
    else:
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


def load_history(mode: str = "paper") -> pd.DataFrame:
    if _using_mongodb():
        rows = list(_db()["trades"].find({"mode": mode}, {"_id": 0}).sort("closed_at", -1))
    else:
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
        df["mode"] = mode
    return df


def load_equity(mode: str = "paper") -> pd.DataFrame:
    if _using_mongodb():
        rows = list(_db()["equity_snapshots"].find({"mode": mode}, {"_id": 0}).sort("timestamp", 1))
    else:
        raw = _load_json(_data_dir() / "equity.json", {"snapshots": []})
        rows = raw.get("snapshots", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    numeric_cols = ["balance_usdt", "realized_pnl_usdt", "unrealized_pnl_usdt", "total_pnl_usdt"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "mode" not in df.columns:
        df["mode"] = mode
    return df


def load_signals_history(mode: str = "paper") -> pd.DataFrame:
    if _using_mongodb():
        cycles = list(_db()["signal_cycles"].find({"mode": mode}, {"_id": 0}).sort("timestamp", 1))
    else:
        raw = _load_json(_data_dir() / "signals_history.json", {"cycles": []})
        cycles = raw.get("cycles", [])

    rows = []
    for cycle in cycles:
        ts = cycle.get("timestamp")
        for symbol, info in cycle.get("signals", {}).items():
            rows.append(
                {
                    "timestamp": ts,
                    "mode": cycle.get("mode", mode),
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
    if _using_mongodb():
        # Settings ainda é um arquivo local; se o dashboard compartilha a pasta, lê JSON.
        # Futuramente pode migrar para uma collection ``settings``.
        if _data_dir():
            return _load_json(_data_dir().parent / "config" / "settings.json")
        return {}
    path = _data_dir().parent / "config" / "settings.json"
    return _load_json(path)


def load_coins() -> pd.DataFrame:
    if _using_mongodb():
        if _data_dir():
            raw = _load_json(_data_dir().parent / "config" / "coins.json", {"coins": []})
            return pd.DataFrame(raw.get("coins", []))
        return pd.DataFrame()
    raw = _load_json(_data_dir().parent / "config" / "coins.json", {"coins": []})
    return pd.DataFrame(raw.get("coins", []))


def load_all(mode: str = "paper") -> dict:
    return {
        "state": load_bot_state(mode),
        "positions": load_positions(mode),
        "history": load_history(mode),
        "equity": load_equity(mode),
        "signals": load_signals_history(mode),
        "settings": load_settings(),
        "coins": load_coins(),
    }
