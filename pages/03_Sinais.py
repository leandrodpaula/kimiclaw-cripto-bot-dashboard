"""Página de análise de sinais e ajustes de estratégia."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data_loader import check_mongodb_status, load_all

st.set_page_config(page_title="Sinais", page_icon="📡", layout="wide")

st.title("📡 Sinais & Estratégia")

modo = st.selectbox("Modo", ["paper", "testnet", "live"], index=0)

status = check_mongodb_status()
if status["ok"]:
    st.sidebar.success("🟢 MongoDB Atlas")
else:
    st.sidebar.error(f"🔴 MongoDB: {status['message']}")
    st.warning(f"⚠️ Sem conexão com o MongoDB Atlas: {status['message']}")


@st.cache_data(ttl=30)
def _load(mode: str):
    return load_all(mode)


data = _load(modo)
signals = data["signals"]
settings = data["settings"]
coins = data["coins"]

st.markdown("---")
st.subheader("Configuração Atual da Estratégia")
strategy_cfg = settings.get("strategy", {})
risk_cfg = settings.get("risk", {})

col1, col2, col3 = st.columns(3)
col1.metric("Estratégia", strategy_cfg.get("name", "composite"))
col1.metric("Score Mínimo", strategy_cfg.get("min_score"))
col2.metric("RSI Period", strategy_cfg.get("rsi_period"))
col2.metric("RSI Oversold/Overbought", f"{strategy_cfg.get('rsi_oversold')} / {strategy_cfg.get('rsi_overbought')}")
col3.metric("EMA Fast/Slow/Trend", f"{strategy_cfg.get('ema_fast')} / {strategy_cfg.get('ema_slow')} / {strategy_cfg.get('ema_trend')}")
col3.metric("MACD Fast/Slow/Signal", f"{strategy_cfg.get('macd_fast')} / {strategy_cfg.get('macd_slow')} / {strategy_cfg.get('macd_signal')}")

st.markdown("---")
st.subheader("Risco")
cols = st.columns(4)
cols[0].metric("Stop Loss", f"{risk_cfg.get('stop_loss_pct')}%")
cols[1].metric("Take Profit", f"{risk_cfg.get('take_profit_pct')}%")
cols[2].metric("Trailing Stop", f"{risk_cfg.get('trailing_stop_pct')}%")
cols[3].metric("Máx Posições", risk_cfg.get("max_open_positions"))

# Sinais recentes
st.markdown("---")
st.subheader("Últimos Sinais por Ativo")

if not signals.empty:
    latest = signals.sort_values("timestamp").drop_duplicates(subset=["symbol"], keep="last").sort_values("score", ascending=False)
    latest["emoji"] = latest["signal"].map({"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"})
    st.dataframe(latest[["emoji", "symbol", "signal", "score", "price", "timestamp"]], use_container_width=True, hide_index=True)

    # Distribuição de sinais
    st.markdown("---")
    st.subheader("Distribuição de Sinais")
    counts = signals["signal"].value_counts().reset_index()
    counts.columns = ["signal", "count"]
    fig = go.Figure(go.Pie(labels=counts["signal"], values=counts["count"], hole=0.4))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Evolução do score
    st.markdown("---")
    st.subheader("Evolução do Score por Par")
    symbols = sorted(signals["symbol"].unique())
    selected = st.multiselect("Selecionar pares", symbols, default=symbols[:3])
    fig2 = go.Figure()
    for sym in selected:
        sub = signals[signals["symbol"] == sym].sort_values("timestamp")
        fig2.add_trace(go.Scatter(x=sub["timestamp"], y=sub["score"], mode="lines+markers", name=sym))
    fig2.add_hline(y=strategy_cfg.get("min_score", 60), line_dash="dash", line_color="red", annotation_text="min score")
    fig2.update_layout(template="plotly_dark", height=450, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Data", yaxis_title="Score")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Nenhum histórico de sinais disponível.")

# Moedas monitoradas
st.markdown("---")
st.subheader("Moedas Monitoradas")
if not coins.empty:
    st.dataframe(coins, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma moeda configurada.")
