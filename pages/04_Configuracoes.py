"""Página de configuração do bot via MongoDB Atlas."""

from __future__ import annotations

import streamlit as st

from data_loader import check_mongodb_status, load_coins, load_settings, save_coins, save_settings

st.set_page_config(page_title="Configurações", page_icon="⚙️", layout="wide")

st.title("⚙️ Configurações do Bot")

modo = st.selectbox("Modo", ["paper", "testnet", "live"], index=0)

status = check_mongodb_status()
if status["ok"]:
    st.sidebar.success("🟢 MongoDB Atlas")
else:
    st.sidebar.error(f"🔴 MongoDB: {status['message']}")
    st.warning(f"⚠️ Sem conexão com o MongoDB Atlas: {status['message']}")
    st.stop()

settings = load_settings(modo)
coins_doc = load_coins(modo)

# ---------------------------------------------------------------------------
# Settings gerais
# ---------------------------------------------------------------------------
st.subheader("Gerais")

col1, col2, col3 = st.columns(3)
with col1:
    mode_default = settings.get("mode", modo)
    new_mode = st.selectbox("Modo padrão", ["paper", "testnet", "live"], index=["paper", "testnet", "live"].index(mode_default))
with col2:
    confirm_live = st.toggle("Confirmar modo live", value=settings.get("confirm_live", False))
with col3:
    interval_seconds = st.number_input(
        "Intervalo entre ciclos (s)",
        min_value=60,
        max_value=86400,
        value=int(settings.get("interval_seconds", 3600)),
        step=60,
    )

# ---------------------------------------------------------------------------
# Estratégia
# ---------------------------------------------------------------------------
st.subheader("Estratégia")
strategy = settings.get("strategy", {})

col1, col2 = st.columns(2)
with col1:
    strategy_name = st.selectbox(
        "Nome",
        ["composite", "rsi_reversal", "ema_crossover", "macd"],
        index=["composite", "rsi_reversal", "ema_crossover", "macd"].index(strategy.get("name", "composite")),
    )
with col2:
    min_score = st.slider("Score mínimo", 0, 100, int(strategy.get("min_score", 60)))

col1, col2, col3 = st.columns(3)
with col1:
    rsi_period = st.number_input("RSI período", min_value=2, max_value=100, value=int(strategy.get("rsi_period", 14)))
    rsi_oversold = st.number_input("RSI sobrevenda", min_value=0, max_value=100, value=int(strategy.get("rsi_oversold", 30)))
    rsi_overbought = st.number_input("RSI sobrecompra", min_value=0, max_value=100, value=int(strategy.get("rsi_overbought", 70)))
with col2:
    ema_fast = st.number_input("EMA rápida", min_value=2, max_value=500, value=int(strategy.get("ema_fast", 9)))
    ema_slow = st.number_input("EMA lenta", min_value=2, max_value=500, value=int(strategy.get("ema_slow", 21)))
    ema_trend = st.number_input("EMA tendência", min_value=2, max_value=1000, value=int(strategy.get("ema_trend", 200)))
with col3:
    macd_fast = st.number_input("MACD rápido", min_value=2, max_value=100, value=int(strategy.get("macd_fast", 12)))
    macd_slow = st.number_input("MACD lento", min_value=2, max_value=100, value=int(strategy.get("macd_slow", 26)))
    macd_signal = st.number_input("MACD sinal", min_value=2, max_value=100, value=int(strategy.get("macd_signal", 9)))

# ---------------------------------------------------------------------------
# Risco
# ---------------------------------------------------------------------------
st.subheader("Risco")
risk = settings.get("risk", {})

col1, col2, col3 = st.columns(3)
with col1:
    stop_loss_pct = st.number_input("Stop Loss (%)", min_value=0.0, max_value=100.0, value=float(risk.get("stop_loss_pct", 3.0)), step=0.1)
    take_profit_pct = st.number_input("Take Profit (%)", min_value=0.0, max_value=1000.0, value=float(risk.get("take_profit_pct", 6.0)), step=0.1)
    trailing_stop_pct = st.number_input("Trailing Stop (%)", min_value=0.0, max_value=100.0, value=float(risk.get("trailing_stop_pct", 0.0)), step=0.1)
with col2:
    max_position_pct = st.number_input("Máx % por posição", min_value=0.0, max_value=100.0, value=float(risk.get("max_position_pct", 10.0)), step=0.1)
    fixed_order_usdt = st.number_input("Valor fixo por ordem (USDT)", min_value=0.0, value=float(risk.get("fixed_order_usdt", 0.0)), step=10.0)
    max_open_positions = st.number_input("Máx posições abertas", min_value=1, max_value=50, value=int(risk.get("max_open_positions", 5)))
with col3:
    cooldown_hours = st.number_input("Cooldown pós-stop (h)", min_value=0.0, max_value=168.0, value=float(risk.get("cooldown_hours", 4.0)), step=0.5)
    max_daily_drawdown_pct = st.number_input("Max drawdown diário (%)", min_value=0.0, max_value=100.0, value=float(risk.get("max_daily_drawdown_pct", 10.0)), step=0.1)

# ---------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------
st.subheader("Paper Trading")
paper = settings.get("paper", {})
initial_balance_usdt = st.number_input(
    "Saldo inicial (USDT)",
    min_value=0.0,
    value=float(paper.get("initial_balance_usdt", 10000.0)),
    step=100.0,
)

# ---------------------------------------------------------------------------
# Moedas
# ---------------------------------------------------------------------------
st.subheader("Moedas monitoradas")

coins = coins_doc.get("coins", [])

# Sempre mantém pelo menos uma linha vazia para adicionar.
if not coins:
    coins = [{"symbol": "", "active": True, "overrides": {}}]

edited_coins = []
for i, coin in enumerate(coins):
    cols = st.columns([3, 1, 2, 1])
    with cols[0]:
        symbol = st.text_input(f"Symbol {i+1}", value=coin.get("symbol", ""), key=f"symbol_{i}")
    with cols[1]:
        active = st.toggle(f"Ativo {i+1}", value=coin.get("active", True), key=f"active_{i}")
    with cols[2]:
        overrides_raw = st.text_input(
            f"Overrides {i+1} (JSON)",
            value=str(coin.get("overrides", {})),
            key=f"overrides_{i}",
            help='Exemplo: {"stop_loss_pct": 2.5, "take_profit_pct": 5.0}',
        )
    with cols[3]:
        st.write("")
        st.write("")
        remove = st.button("🗑️", key=f"remove_{i}")

    overrides = coin.get("overrides", {})
    try:
        import ast
        overrides_parsed = ast.literal_eval(overrides_raw)
        if isinstance(overrides_parsed, dict):
            overrides = overrides_parsed
    except Exception:
        pass

    if symbol and not remove:
        edited_coins.append({"symbol": symbol, "active": active, "overrides": overrides})

if st.button("➕ Adicionar moeda"):
    edited_coins.append({"symbol": "", "active": True, "overrides": {}})
    st.rerun()

# ---------------------------------------------------------------------------
# Salvar
# ---------------------------------------------------------------------------
st.markdown("---")

new_settings = {
    "mode": new_mode,
    "confirm_live": confirm_live,
    "interval_seconds": interval_seconds,
    "strategy": {
        "name": strategy_name,
        "min_score": min_score,
        "rsi_period": rsi_period,
        "rsi_oversold": rsi_oversold,
        "rsi_overbought": rsi_overbought,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "ema_trend": ema_trend,
        "macd_fast": macd_fast,
        "macd_slow": macd_slow,
        "macd_signal": macd_signal,
    },
    "risk": {
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct,
        "trailing_stop_pct": trailing_stop_pct,
        "max_position_pct": max_position_pct,
        "fixed_order_usdt": fixed_order_usdt,
        "max_open_positions": max_open_positions,
        "cooldown_hours": cooldown_hours,
        "max_daily_drawdown_pct": max_daily_drawdown_pct,
    },
    "paper": {"initial_balance_usdt": initial_balance_usdt},
}

if st.button("💾 Salvar configurações", type="primary"):
    ok_settings = save_settings(modo, new_settings)
    ok_coins = save_coins(modo, {"coins": edited_coins})
    if ok_settings and ok_coins:
        st.success("Configurações salvas no MongoDB Atlas. O bot lerá esses valores no próximo ciclo.")
    else:
        st.error("Falha ao salvar configurações. Verifique a conexão com o MongoDB Atlas.")
