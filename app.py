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
    .block-container { padding-top: 1rem; }
    .metric-card {
        background-color: #1e1e2e;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        height: 100%;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #a0a0b0;
        margin-top: 4px;
    }
    .section-paper { border-left: 4px solid #facc15; padding-left: 12px; }
    .section-real { border-left: 4px solid #ef4444; padding-left: 12px; }
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
st.caption("Visão comparativa entre **Paper** e **Real**.")

if not status["ok"]:
    st.warning(f"⚠️ Sem conexão com o MongoDB Atlas: {status['message']}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _metric_card(label: str, value: str, delta: str | None = None):
    delta_html = f'<div style="font-size:0.75rem;color:#888;">{delta}</div>' if delta else ""
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>
    """


def _render_paper_section(state: dict, metrics: dict, settings: dict):
    initial = float(state.get("paper_initial_balance_usdt", settings.get("paper", {}).get("initial_balance_usdt", 10000.0)))
    balance = float(state.get("paper_balance_usdt", initial))
    realized = float(state.get("realized_pnl_usdt", 0.0))
    roi = ((balance / initial) - 1) * 100 if initial > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_metric_card("Saldo", f"${balance:,.2f}", f"ROI {roi:+.2f}%"), unsafe_allow_html=True)
    with c2:
        st.markdown(_metric_card("P&L Realizado", f"${realized:,.2f}"), unsafe_allow_html=True)
    with c3:
        st.markdown(_metric_card("Win Rate", f"{metrics['win_rate']:.1f}%"), unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(_metric_card("Total Trades", f"{metrics['total_trades']}"), unsafe_allow_html=True)
    with c5:
        st.markdown(_metric_card("Profit Factor", f"{metrics['profit_factor']:.2f}"), unsafe_allow_html=True)
    with c6:
        st.markdown(_metric_card("Drawdown Máx.", f"{metrics['max_drawdown_pct']:.2f}%"), unsafe_allow_html=True)


def _render_real_section(state: dict, metrics: dict):
    realized = float(state.get("realized_pnl_usdt", 0.0))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_metric_card("P&L Realizado", f"${realized:,.2f}"), unsafe_allow_html=True)
    with c2:
        st.markdown(_metric_card("Win Rate", f"{metrics['win_rate']:.1f}%"), unsafe_allow_html=True)
    with c3:
        st.markdown(_metric_card("Profit Factor", f"{metrics['profit_factor']:.2f}"), unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(_metric_card("Total Trades", f"{metrics['total_trades']}"), unsafe_allow_html=True)
    with c5:
        st.markdown(_metric_card("Drawdown Máx.", f"{metrics['max_drawdown_pct']:.2f}%"), unsafe_allow_html=True)
    with c6:
        st.markdown(_metric_card("Último ciclo", state.get("last_cycle_at", "—")[:16] if state.get("last_cycle_at") else "—"), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Paper vs Real
# ---------------------------------------------------------------------------
col_paper, col_real = st.columns(2, gap="large")

with col_paper:
    st.markdown("<div class='section-paper'><h3>🟡 Paper</h3></div>", unsafe_allow_html=True)
    _render_paper_section(state_paper, metrics_paper, settings)

with col_real:
    real_label = "🔴 Live" if modo_real == "live" else "🔵 Testnet"
    st.markdown(f"<div class='section-real'><h3>{real_label}</h3></div>", unsafe_allow_html=True)
    _render_real_section(state_real, metrics_real)

# ---------------------------------------------------------------------------
# Recomendações
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("🤖 Recomendações do Agente")

recommendations = generate_recommendations(history_paper, equity_paper, signals_paper, state_paper, settings)
if recommendations:
    for rec in recommendations:
        priority_class = f"priority-{rec['priority']}"
        st.markdown(
            f"""
            <div class="recommendation-card {priority_class}">
                <strong>{rec['title']}</strong> <span style="color:#888">({rec['category']} | {rec['priority']})</span><br>
                {rec['message']}
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.info("Nenhuma recomendação no momento.")

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
        height=380,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Data",
        yaxis_title="USDT",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Ainda não há snapshots de equity.")

# ---------------------------------------------------------------------------
# Sinais e Posições (abas)
# ---------------------------------------------------------------------------
st.markdown("---")
tab_sinais, tab_posicoes = st.tabs(["📡 Sinais Atuais", "💼 Posições Abertas"])

with tab_sinais:
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
        st.info("Nenhum histórico de sinais disponível.")

with tab_posicoes:
    positions_all = pd.concat([positions_paper, positions_real], ignore_index=True)
    if not positions_all.empty:
        if "mode" not in positions_all.columns:
            positions_all["mode"] = None
        st.dataframe(positions_all, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma posição aberta no momento.")
