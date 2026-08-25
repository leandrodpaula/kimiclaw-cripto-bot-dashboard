"""Gera dados de demonstração realistas para o dashboard.

Uso:
    python demo/generate_demo_data.py

O script grava arquivos JSON em ``demo_data/``. Para rodar o dashboard com esses dados:
    BOT_DATA_PATH=./demo_data streamlit run app.py
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / "demo_data"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)
np.random.seed(42)


def save(name: str, data: dict) -> None:
    with open(DEMO_DIR / name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -----------------------------------------------------------------------------
# Parâmetros da simulação
# -----------------------------------------------------------------------------
MOEDAS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
INITIAL_BALANCE = 10000.0
START = datetime(2026, 7, 1, tzinfo=timezone.utc)
DAYS = 45
INTERVAL_HOURS = 1
N_POINTS = DAYS * 24 // INTERVAL_HOURS

# -----------------------------------------------------------------------------
# Estado do bot
# -----------------------------------------------------------------------------
state = {
    "last_cycle_at": (START + timedelta(hours=N_POINTS)).isoformat(),
    "mode": "paper",
    "paper_balance_usdt": INITIAL_BALANCE,
    "paper_initial_balance_usdt": INITIAL_BALANCE,
    "realized_pnl_usdt": 0.0,
    "daily": {
        "date": (START + timedelta(hours=N_POINTS)).date().isoformat(),
        "start_balance_usdt": INITIAL_BALANCE,
        "realized_pnl_usdt": 0.0,
        "kill_switch_active": False,
    },
    "cooldowns": {},
    "offline_fallback": False,
}

# -----------------------------------------------------------------------------
# Equity curve com caminho aleatório tendência positiva leve
# -----------------------------------------------------------------------------
snapshots = []
balance = INITIAL_BALANCE
for i in range(N_POINTS):
    ret = np.random.normal(0.0005, 0.004)  # retorno médio levemente positivo
    balance *= 1 + ret
    snapshots.append(
        {
            "timestamp": (START + timedelta(hours=i)).isoformat(),
            "mode": "paper",
            "balance_usdt": round(balance, 2),
            "realized_pnl_usdt": round(balance - INITIAL_BALANCE, 2),
            "unrealized_pnl_usdt": 0.0,
            "total_pnl_usdt": round(balance - INITIAL_BALANCE, 2),
        }
    )
state["paper_balance_usdt"] = round(balance, 2)
state["realized_pnl_usdt"] = round(balance - INITIAL_BALANCE, 2)

# -----------------------------------------------------------------------------
# Sinais por ciclo
# -----------------------------------------------------------------------------
signal_choices = ["BUY", "SELL", "HOLD"]
cycles = []
for i in range(N_POINTS):
    ts = START + timedelta(hours=i)
    signals = {}
    for sym in MOEDAS:
        sig = random.choices(signal_choices, weights=[0.25, 0.15, 0.6])[0]
        price = 20000 + random.random() * 5000 if sym == "BTCUSDT" else 1000 + random.random() * 500
        signals[sym] = {
            "signal": sig,
            "score": random.randint(40, 100) if sig in ("BUY", "SELL") else random.randint(0, 50),
            "price": round(price, 2),
        }
    cycles.append({"timestamp": ts.isoformat(), "mode": "paper", "signals": signals})

# -----------------------------------------------------------------------------
# Trades fechados simulados
# -----------------------------------------------------------------------------
trades = []
trade_dates = sorted(
    [START + timedelta(hours=int(i)) for i in np.random.choice(range(50, N_POINTS - 10), size=35, replace=False)]
)
for ts in trade_dates:
    sym = random.choice(MOEDAS)
    entry = 1000 + random.random() * 500
    exit_reason = random.choices(
        ["take_profit", "stop_loss", "signal_sell", "trailing_stop"],
        weights=[0.45, 0.30, 0.20, 0.05],
    )[0]

    if exit_reason == "take_profit":
        exit_price = entry * random.uniform(1.01, 1.08)
    elif exit_reason == "stop_loss":
        exit_price = entry * random.uniform(0.92, 0.985)
    elif exit_reason == "trailing_stop":
        exit_price = entry * random.uniform(0.95, 1.03)
    else:
        exit_price = entry * random.uniform(0.97, 1.05)

    qty = random.uniform(0.01, 0.5)
    pnl = (exit_price - entry) * qty
    trades.append(
        {
            "id": str(uuid.uuid4()),
            "symbol": sym,
            "side": "BUY",
            "entry_price": round(entry, 8),
            "exit_price": round(exit_price, 8),
            "quantity": round(qty, 8),
            "pnl_usdt": round(pnl, 4),
            "pnl_pct": round(((exit_price / entry) - 1) * 100, 4),
            "opened_at": (ts - timedelta(hours=random.randint(2, 72))).isoformat(),
            "closed_at": ts.isoformat(),
            "exit_reason": exit_reason,
            "strategy": "composite",
            "mode": "paper",
        }
    )

# -----------------------------------------------------------------------------
# Posições abertas simuladas
# -----------------------------------------------------------------------------
positions = []
for sym in random.sample(MOEDAS, k=2):
    entry = 1000 + random.random() * 500
    qty = random.uniform(0.01, 0.5)
    positions.append(
        {
            "id": str(uuid.uuid4()),
            "symbol": sym,
            "side": "BUY",
            "entry_price": round(entry, 8),
            "quantity": round(qty, 8),
            "invested_usdt": round(entry * qty, 2),
            "stop_loss": round(entry * 0.97, 8),
            "take_profit": round(entry * 1.06, 8),
            "trailing_peak": round(entry * 1.02, 8),
            "opened_at": (START + timedelta(hours=N_POINTS - 10)).isoformat(),
            "strategy": "composite",
            "score": random.randint(65, 95),
            "mode": "paper",
        }
    )

# -----------------------------------------------------------------------------
# Persistência dos mocks
# -----------------------------------------------------------------------------
save("bot_state.json", state)
save("equity.json", {"snapshots": snapshots})
save("signals_history.json", {"cycles": cycles})
save("history.json", {"trades": trades})
save("positions.json", {"positions": positions})

print(f"Dados de demonstração gerados em {DEMO_DIR}")
print(f"  Trades: {len(trades)} | Equity snapshots: {len(snapshots)} | Sinais: {len(cycles)} ciclos | Posições: {len(positions)}")
