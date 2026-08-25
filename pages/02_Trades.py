"""Página de histórico de trades e posições abertas."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data_loader import load_all

st.set_page_config(page_title="Trades", page_icon="💼", layout="wide")

st.title("💼 Trades & Posições")

modo = st.selectbox("Modo", ["paper", "testnet", "live"], index=0)


@st.cache_data(ttl=30)
def _load(mode: str):
    return load_all(mode)


data = _load(modo)
history = data["history"]
positions = data["positions"]

# Posições abertas
st.subheader("Posições Abertas")
if not positions.empty:
    st.dataframe(positions, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma posição aberta.")

# Histórico de trades
st.markdown("---")
st.subheader("Histórico de Trades Fechados")

if not history.empty:
    # Filtros
    symbols = sorted(history["symbol"].unique())
    reasons = sorted(history["exit_reason"].unique())
    col1, col2 = st.columns(2)
    with col1:
        selected_symbols = st.multiselect("Par", symbols, default=symbols)
    with col2:
        selected_reasons = st.multiselect("Motivo de Saída", reasons, default=reasons)

    filtered = history[
        history["symbol"].isin(selected_symbols) & history["exit_reason"].isin(selected_reasons)
    ]

    st.dataframe(filtered.sort_values("closed_at", ascending=False), use_container_width=True, hide_index=True)

    # Distribuição por motivo de saída
    st.markdown("---")
    st.subheader("Distribuição por Motivo de Saída")
    counts = filtered["exit_reason"].value_counts().reset_index()
    counts.columns = ["exit_reason", "count"]
    fig = go.Figure(go.Pie(labels=counts["exit_reason"], values=counts["count"], hole=0.4))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # P&L por par
    st.markdown("---")
    st.subheader("P&L por Par")
    pnl_by_symbol = filtered.groupby("symbol")["pnl_usdt"].sum().sort_values(ascending=True).reset_index()
    colors = ["#22c55e" if x >= 0 else "#ef4444" for x in pnl_by_symbol["pnl_usdt"]]
    fig2 = go.Figure(go.Bar(x=pnl_by_symbol["pnl_usdt"], y=pnl_by_symbol["symbol"], orientation="h", marker_color=colors))
    fig2.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="P&L USDT", yaxis_title="Par")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Nenhum trade fechado para este modo.")
