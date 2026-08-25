"""Página principal do dashboard KimiClaw Crypto.

Visão geral: saldo, P&L, métricas principais, recomendações do agente e
estado atual do bot (paper vs real).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_loader import load_all
from metrics import calc_trade_metrics
from recommendations import generate_recommendations

st.set_page_config(
    page_title="KimiClaw Crypto Dashboard",
    page_icon="🦞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS customizado
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    .stMetric { background-color: #1e1e2e; border-radius: 12px; padding: 16px; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700; }
    div[data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #a0a0b0; }
    .recommendation-card {
        background-color: #1e1e2e;
        border-left: 5px solid;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }
    .priority-alta { border-left-color: #ff4b4b; }
    .priority-média { border-left-color: #ffa500; }
    .priority-baixa { border-left-color: #21c55e; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Carga de dados
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("# 🦞 KimiClaw Crypto")
st.sidebar.caption("Dashboard de acompanhamento")

modos = ["paper", "testnet", "live"]
modo_selecionado = st.sidebar.selectbox("Modo", modos, index=0)


@st.cache_data(ttl=30)
def _load(mode: str):
    return load_all(mode)


data = _load(modo_selecionado)
state = data["state"]
positions = data["positions"]
history = data["history"]
equity = data["equity"]
signals = data["signals"]
settings = data["settings"]
coins = data["coins"]

st.sidebar.markdown("---")
st.sidebar.subheader("Configuração do bot")
st.sidebar.json(
    {
        "strategy": settings.get("strategy", {}).get("name", "composite"),
        "min_score": settings.get("strategy", {}).get("min_score"),
        "SL": f"{settings.get('risk', {}).get('stop_loss_pct')}%",
        "TP": f"{settings.get('risk', {}).get('take_profit_pct')}%",
        "max_pos": settings.get("risk", {}).get("max_open_positions"),
    }
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Último ciclo: {state.get('last_cycle_at', 'nunca')}")
st.sidebar.caption(f"Offline fallback: {'sim' if state.get('offline_fallback') else 'não'}")

metrics = calc_trade_metrics(history)

# ---------------------------------------------------------------------------
# Título
# ---------------------------------------------------------------------------
col_title, col_mode = st.columns([6, 1])
with col_title:
    st.title("🦞 KimiClaw Crypto Dashboard")
with col_mode:
    cor_modo = {"paper": "🟡 Paper", "testnet": "🔵 Testnet", "live": "🔴 Live"}.get(modo_selecionado, modo_selecionado)
    st.markdown(f"### {cor_modo}")

st.markdown("Visão geral da estratégia, métricas de performance e recomendações do agente analítico.")

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
initial_balance = float(state.get("paper_initial_balance_usdt", settings.get("paper", {}).get("initial_balance_usdt", 10000.0)))
current_balance = float(state.get("paper_balance_usdt", initial_balance))
realized = float(state.get("realized_pnl_usdt", 0.0))

# Em modo live/testnet, o saldo real não está no bot_state; usamos realized como proxy.
if modo_selecionado != "paper":
    current_balance = initial_balance + realized

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Saldo", f"${current_balance:,.2f}", f"{((current_balance / initial_balance) - 1) * 100:.2f}%")
kpi2.metric("P&L Realizado", f"${metrics['total_pnl']:,.2f}")
kpi3.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
kpi4.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
kpi5.metric("Drawdown Máx.", f"{metrics['max_drawdown_pct']:.2f}%")

# ---------------------------------------------------------------------------
# Recomendações do agente
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("🤖 Recomendações do Agente")

recommendations = generate_recommendations(history, equity, signals, state, settings)
for rec in recommendations:
    priority_class = f"priority-{rec['priority']}"
    st.markdown(
        f"""
        <div class="recommendation-card {priority_class}">
            <strong>{rec['title']}</strong> <span style="color:#888">({rec['category']} | prioridade {rec['priority']})</span><br>
            {rec['message']}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Equity curve e trades recentes
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("📈 Equity Curve")

if not equity.empty and "balance_usdt" in equity.columns:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=equity["timestamp"],
            y=equity["balance_usdt"],
            mode="lines",
            name=modo_selecionado.capitalize(),
            line=dict(width=2),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Data",
        yaxis_title="Saldo (USDT)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Ainda não há snapshots de equity. O bot começará a gravar a série temporal a partir do próximo ciclo.")

# ---------------------------------------------------------------------------
# Sinais atuais
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("📡 Sinais Atuais")

if not signals.empty:
    latest = signals.sort_values("timestamp").drop_duplicates(subset=["symbol"], keep="last").sort_values("score", ascending=False)
    latest["emoji"] = latest["signal"].map({"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"})
    latest_display = latest[["emoji", "symbol", "signal", "score", "price", "timestamp"]].rename(
        columns={
            "emoji": "",
            "symbol": "Par",
            "signal": "Sinal",
            "score": "Score",
            "price": "Preço",
            "timestamp": "Atualizado",
        }
    )
    st.dataframe(latest_display, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum histórico de sinais disponível. Execute o bot para popular os dados.")

# ---------------------------------------------------------------------------
# Posições abertas
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("💼 Posições Abertas")

if not positions.empty:
    st.dataframe(positions, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma posição aberta no momento.")
