"""Página principal do dashboard KimiClaw Crypto.

Visão geral comparativa: paper e live/testnet na mesma tela, com métricas,
equity curve, sinais e posições.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_loader import check_mongodb_status, load_all
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
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
    div[data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: #a0a0b0; }
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
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("# 🦞 KimiClaw Crypto")
st.sidebar.caption("Dashboard de acompanhamento")

modo_real = st.sidebar.selectbox("Modo real", ["live", "testnet"], index=0)

# Status de conexão com o MongoDB.
status = check_mongodb_status()
if status["ok"]:
    st.sidebar.success("🟢 MongoDB Atlas")
else:
    st.sidebar.error(f"🔴 MongoDB: {status['message']}")


@st.cache_data(ttl=30)
def _load(mode: str):
    return load_all(mode)


data_paper = _load("paper")
data_real = _load(modo_real)

state_paper = data_paper["state"]
positions_paper = data_paper["positions"]
history_paper = data_paper["history"]
equity_paper = data_paper["equity"]
signals_paper = data_paper["signals"]
settings = data_paper["settings"]

state_real = data_real["state"]
positions_real = data_real["positions"]
history_real = data_real["history"]
equity_real = data_real["equity"]
signals_real = data_real["signals"]

metrics_paper = calc_trade_metrics(history_paper)
metrics_real = calc_trade_metrics(history_real)

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
st.sidebar.caption(f"Último ciclo paper: {state_paper.get('last_cycle_at', 'nunca')}")
st.sidebar.caption(f"Último ciclo {modo_real}: {state_real.get('last_cycle_at', 'nunca')}")

# ---------------------------------------------------------------------------
# Título
# ---------------------------------------------------------------------------
st.title("🦞 KimiClaw Crypto Dashboard")
st.markdown("Visão comparativa entre **Paper** e **Real**.")

if not status["ok"]:
    st.warning(f"⚠️ Dashboard sem conexão com o MongoDB Atlas: {status['message']}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _kpi_columns(title: str, state: dict, metrics: dict, is_paper: bool, settings: dict):
    st.subheader(title)

    if is_paper:
        initial_balance = float(
            state.get("paper_initial_balance_usdt", settings.get("paper", {}).get("initial_balance_usdt", 10000.0))
        )
        current_balance = float(state.get("paper_balance_usdt", initial_balance))
        realized = float(state.get("realized_pnl_usdt", 0.0))
        roi = ((current_balance / initial_balance) - 1) * 100 if initial_balance > 0 else 0.0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Saldo", f"${current_balance:,.2f}", f"{roi:.2f}%")
        c2.metric("P&L Realizado", f"${realized:,.2f}")
        c3.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
        c4.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
        c5.metric("Drawdown Máx.", f"{metrics['max_drawdown_pct']:.2f}%")
    else:
        # Modo real: não usa saldo inicial paper; exibe P&L acumulado e métricas de trades.
        realized = float(state.get("realized_pnl_usdt", 0.0))

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("P&L Realizado", f"${realized:,.2f}")
        c2.metric("Total de Trades", f"{metrics['total_trades']}")
        c3.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
        c4.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
        c5.metric("Drawdown Máx.", f"{metrics['max_drawdown_pct']:.2f}%")


# ---------------------------------------------------------------------------
# Paper vs Real
# ---------------------------------------------------------------------------
col_paper, col_real = st.columns(2)

with col_paper:
    _kpi_columns("🟡 Paper", state_paper, metrics_paper, is_paper=True, settings=settings)

with col_real:
    real_label = "🔴 Live" if modo_real == "live" else "🔵 Testnet"
    _kpi_columns(real_label, state_real, metrics_real, is_paper=False, settings=settings)

# ---------------------------------------------------------------------------
# Recomendações do agente (combinadas)
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("🤖 Recomendações do Agente")

recommendations = generate_recommendations(history_paper, equity_paper, signals_paper, state_paper, settings)
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
# Equity curve comparativa
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("📈 Equity Curve Comparativa")

fig = go.Figure()
if not equity_paper.empty and "balance_usdt" in equity_paper.columns:
    fig.add_trace(
        go.Scatter(
            x=equity_paper["timestamp"],
            y=equity_paper["balance_usdt"],
            mode="lines",
            name="Paper",
            line=dict(width=2, color="#facc15"),
        )
    )
if not equity_real.empty and "balance_usdt" in equity_real.columns:
    fig.add_trace(
        go.Scatter(
            x=equity_real["timestamp"],
            y=equity_real["balance_usdt"],
            mode="lines",
            name=modo_real.capitalize(),
            line=dict(width=2, color="#ef4444"),
        )
    )

if fig.data:
    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Data",
        yaxis_title="Saldo / P&L (USDT)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Ainda não há snapshots de equity. Execute o bot para popular os dados.")

# ---------------------------------------------------------------------------
# Sinais atuais
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("📡 Sinais Atuais")

signals_all = pd.concat([signals_paper, signals_real], ignore_index=True)
if not signals_all.empty:
    latest = (
        signals_all.sort_values("timestamp")
        .drop_duplicates(subset=["mode", "symbol"], keep="last")
        .sort_values(["mode", "score"], ascending=[True, False])
    )
    latest["emoji"] = latest["signal"].map({"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"})
    latest_display = latest[["emoji", "mode", "symbol", "signal", "score", "price", "timestamp"]].rename(
        columns={
            "emoji": "",
            "mode": "Modo",
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

positions_all = pd.concat([positions_paper, positions_real], ignore_index=True)
if not positions_all.empty:
    if "mode" not in positions_all.columns:
        positions_all["mode"] = None
    st.dataframe(positions_all, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma posição aberta no momento.")
