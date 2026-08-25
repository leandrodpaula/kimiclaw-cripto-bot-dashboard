"""Cálculo de métricas de performance a partir do histórico de trades."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _safe(value, default=0.0):
    return value if pd.notna(value) and np.isfinite(value) else default


def calc_trade_metrics(trades: pd.DataFrame) -> dict:
    """Retorna métricas básicas a partir de um DataFrame de trades fechados."""
    if trades.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "payoff_ratio": 0.0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "max_drawdown_pct": 0.0,
        }

    pnls = trades["pnl_usdt"].astype(float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]

    total = len(pnls)
    win_count = len(wins)
    loss_count = len(losses)

    win_rate = win_count / total * 100 if total else 0.0
    loss_rate = loss_count / total * 100 if total else 0.0

    avg_win = wins.mean() if not wins.empty else 0.0
    avg_loss = losses.mean() if not losses.empty else 0.0

    gross_profit = wins.sum() if not wins.empty else 0.0
    gross_loss = abs(losses.sum()) if not losses.empty else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (np.inf if gross_profit > 0 else 0.0)

    payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

    cumulative = pnls.cumsum()
    running_max = cumulative.cummax()
    drawdown = cumulative - running_max
    max_drawdown = drawdown.min()
    max_drawdown_pct = 0.0
    if running_max.max() > 0:
        max_drawdown_pct = (max_drawdown / running_max.max()) * 100

    return {
        "total_trades": int(total),
        "win_rate": _safe(win_rate),
        "loss_rate": _safe(loss_rate),
        "avg_win": _safe(avg_win),
        "avg_loss": _safe(avg_loss),
        "profit_factor": _safe(profit_factor, np.inf),
        "payoff_ratio": _safe(payoff_ratio, np.inf),
        "total_pnl": _safe(pnls.sum()),
        "avg_pnl": _safe(pnls.mean()),
        "max_drawdown_pct": _safe(max_drawdown_pct),
    }


def calc_daily_pnl(trades: pd.DataFrame) -> pd.DataFrame:
    """Agrupa P&L realizado por dia."""
    if trades.empty or "closed_at" not in trades.columns:
        return pd.DataFrame(columns=["date", "pnl_usdt", "trades"])
    df = trades.copy()
    df["date"] = df["closed_at"].dt.tz_convert(None).dt.date
    grouped = df.groupby("date").agg(pnl_usdt=("pnl_usdt", "sum"), trades=("pnl_usdt", "size")).reset_index()
    return grouped


def calc_equity_drawdown(equity: pd.DataFrame, balance_col: str = "balance_usdt") -> pd.DataFrame:
    """Adiciona colunas de peak e drawdown percentual ao DataFrame de equity."""
    df = equity.copy()
    if df.empty or balance_col not in df.columns:
        return df
    df["peak"] = df[balance_col].cummax()
    df["drawdown_pct"] = ((df[balance_col] - df["peak"]) / df["peak"]) * 100
    return df
