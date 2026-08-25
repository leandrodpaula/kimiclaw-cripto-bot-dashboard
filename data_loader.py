"""Carrega dados do MongoDB Atlas.

O dashboard lê exclusivamente do Atlas usando ``MONGODB_URI`` e ``MONGODB_DB``.
A configuração pode vir do ``.env`` local (desenvolvimento) ou dos secrets do
Streamlit Cloud (produção). Se o MongoDB estiver indisponível, as funções retornam
estruturas vazias e ``check_mongodb_status()`` expõe o estado da conexão para o
frontend.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Carrega .env antes de qualquer coisa.
load_dotenv()


def _get_secret(key: str) -> str | None:
    """Lê uma configuração dos secrets do Streamlit Cloud ou do ambiente local."""
    try:
        value = st.secrets.get(key)
        if value:
            return str(value)
    except Exception:
        pass
    return os.environ.get(key)


def _mongodb_uri() -> str | None:
    return _get_secret("MONGODB_URI")


def _mongodb_db() -> str:
    return _get_secret("MONGODB_DB") or "kimi_trader"


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "kimiclaw-cripto-bot" / "data"


def _load_json(path: Path, default: dict | None = None) -> dict:
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (Exception,):
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
_mongodb_status: dict | None = None


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


def check_mongodb_status(force: bool = False) -> dict:
    """Retorna {"ok": bool, "message": str} sobre a conexão com o Atlas.

    O resultado é cacheado por sessão a menos que ``force=True``.
    """
    global _mongodb_status
    if not force and _mongodb_status is not None:
        return _mongodb_status

    if _mongodb_uri() is None:
        _mongodb_status = {
            "ok": False,
            "message": "MONGODB_URI não configurado no .env",
        }
        return _mongodb_status

    try:
        _get_client().admin.command("ping")
        _mongodb_status = {"ok": True, "message": "Conectado ao MongoDB Atlas"}
    except Exception as exc:
        _mongodb_status = {
            "ok": False,
            "message": f"MongoDB indisponível: {exc}",
        }
    return _mongodb_status


def _safe_load(collection_name: str, mode: str, sort: dict | None = None) -> list[dict]:
    """Carrega documentos de uma collection com tratamento de erro."""
    try:
        if not check_mongodb_status()["ok"]:
            return []
        coll = _db()[collection_name]
        query = {"mode": mode}
        cursor = coll.find(query, {"_id": 0})
        if sort:
            cursor = cursor.sort(sort)
        return list(cursor)
    except Exception as exc:
        print(f"[data_loader] Erro ao carregar {collection_name}: {exc}")
        return []


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_bot_state(mode: str = "paper") -> dict:
    try:
        if not check_mongodb_status()["ok"]:
            return {}
        doc = _db()["bot_state"].find_one({"mode": mode}, sort={"updated_at": -1})
        if doc:
            doc.pop("_id", None)
            return doc
    except Exception as exc:
        print(f"[data_loader] Erro ao carregar bot_state: {exc}")
    return {}


def load_positions(mode: str = "paper") -> pd.DataFrame:
    rows = _safe_load("positions", mode)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    numeric_cols = [
        "entry_price", "quantity", "invested_usdt", "stop_loss",
        "take_profit", "trailing_peak", "score",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "opened_at" in df.columns:
        df["opened_at"] = pd.to_datetime(df["opened_at"], errors="coerce", utc=True)
    return df


def load_history(mode: str = "paper") -> pd.DataFrame:
    rows = _safe_load("trades", mode, sort={"closed_at": -1})
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
    rows = _safe_load("equity_snapshots", mode, sort={"timestamp": 1})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    numeric_cols = [
        "balance_usdt", "realized_pnl_usdt", "unrealized_pnl_usdt", "total_pnl_usdt",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "mode" not in df.columns:
        df["mode"] = mode
    return df


def load_signals_history(mode: str = "paper") -> pd.DataFrame:
    rows = _safe_load("signal_cycles", mode, sort={"timestamp": 1})

    out = []
    for cycle in rows:
        ts = cycle.get("timestamp")
        for symbol, info in cycle.get("signals", {}).items():
            out.append(
                {
                    "timestamp": ts,
                    "mode": cycle.get("mode", mode),
                    "symbol": symbol,
                    "signal": info.get("signal"),
                    "score": info.get("score"),
                    "price": info.get("price"),
                }
            )
    df = pd.DataFrame(out)
    if df.empty:
        return df
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df


def load_settings(mode: str = "paper") -> dict:
    """Carrega configurações do modo no MongoDB Atlas."""
    try:
        if not check_mongodb_status()["ok"]:
            return {}
        doc = _db()["settings"].find_one({"mode": mode}, {"_id": 0})
        if doc:
            doc.pop("mode", None)
            doc.pop("updated_at", None)
            return doc
    except Exception as exc:
        print(f"[data_loader] Erro ao carregar settings: {exc}")
    return {}


def save_settings(mode: str, settings: dict) -> bool:
    """Salva configurações do modo no MongoDB Atlas."""
    try:
        if not check_mongodb_status(force=True)["ok"]:
            return False
        payload = dict(settings)
        payload["mode"] = mode
        _db()["settings"].replace_one({"mode": mode}, payload, upsert=True)
        return True
    except Exception as exc:
        print(f"[data_loader] Erro ao salvar settings: {exc}")
        return False


def load_coins(mode: str = "paper") -> dict:
    """Carrega lista de moedas do modo no MongoDB Atlas."""
    try:
        if not check_mongodb_status()["ok"]:
            return {"coins": []}
        doc = _db()["coins"].find_one({"mode": mode}, {"_id": 0})
        if doc:
            doc.pop("mode", None)
            doc.pop("updated_at", None)
            return doc
    except Exception as exc:
        print(f"[data_loader] Erro ao carregar coins: {exc}")
    return {"coins": []}


def save_coins(mode: str, coins: dict) -> bool:
    """Salva lista de moedas do modo no MongoDB Atlas."""
    try:
        if not check_mongodb_status(force=True)["ok"]:
            return False
        payload = dict(coins)
        payload["mode"] = mode
        _db()["coins"].replace_one({"mode": mode}, payload, upsert=True)
        return True
    except Exception as exc:
        print(f"[data_loader] Erro ao salvar coins: {exc}")
        return False


def load_all(mode: str = "paper") -> dict:
    return {
        "state": load_bot_state(mode),
        "positions": load_positions(mode),
        "history": load_history(mode),
        "equity": load_equity(mode),
        "signals": load_signals_history(mode),
        "settings": load_settings(mode),
        "coins": load_coins(mode),
    }
