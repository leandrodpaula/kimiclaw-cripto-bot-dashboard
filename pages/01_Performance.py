"""Página de performance detalhada."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from data_loader import load_all
from metrics import calc_daily_pnl, calc_equity_drawdown, calc_trade_metrics

st.set_page_config(page_title="Performance", page_icon="📊", layout="wide")

st.title("📊 Performance Detalhada")

modo = st.selectbox("Modo", ["paper", "testnet", "live"], index=0)


@st.cache_data(ttl=30)
def _load(mode: str):
    return load_all(mode)


data = _load(modo)
state = data["state"]
history = data["history"]
equity = data["equity"]
settings = data["settings"]

metrics = calc_trade_metrics(history)

# KPIs expandidos
st.markdown("---")
cols = st.columns(5)
cols[0].metric("Total de Trades", metrics["total_trades"])
cols[1].metric("Win Rate", f"{metrics['win_rate']:.2f}%")
cols[2].metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
cols[3].metric("Payoff Ratio", f"{metrics['payoff_ratio']:.2f}")
cols[4].metric("Média P&L / Trade", f"${metrics['avg_pnl']:.2f}")

cols2 = st.columns(5)
cols2[0].metric("Média de Ganho", f"${metrics['avg_win']:.2f}")
cols2[1].metric("Média de Perda", f"${metrics['avg_loss']:.2f}")
cols2[2].metric("Total P&L", f"${metrics['total_pnl']:.2f}")
cols2[3].metric("Drawdown Máx.", f"{metrics['max_drawdown_pct']:.2f}%")
max_dd = metrics["max_drawdown_pct"]
cols2[4].metric("Risco / Retorno Est.", f"{abs(metrics['avg_win'] / metrics['avg_loss']):.2f}" if metrics["avg_loss"] != 0 else "—")

# Equity + drawdown
st.markdown("---")
st.subheader("Equity Curve & Drawdown")

if not equity.empty and "balance_usdt" in equity.columns:
    dd_df = calc_equity_drawdown(equity)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dd_df["timestamp"], y=dd_df["balance_usdt"], mode="lines", name="Equity", line=dict(color="#22c55e")))
    fig.add_trace(go.Scatter(x=dd_df["timestamp"], y=dd_df["peak"], mode="lines", name="Peak", line=dict(color="#3b82f6", dash="dash")))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Data", yaxis_title="USDT")
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=dd_df["timestamp"], y=dd_df["drawdown_pct"], marker_color="#ef4444", name="Drawdown %"))
    fig2.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Data", yaxis_title="Drawdown %")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Sem dados de equity. Execute o bot para começar a acumular snapshots.")

# P&L diário
st.markdown("---")
st.subheader("P&L Diário")

daily = calc_daily_pnl(history)
if not daily.empty:
    fig3 = go.Figure()
    colors = ["#22c55e" if x >= 0 else "#ef4444" for x in daily["pnl_usdt"]]
    fig3.add_trace(go.Bar(x=daily["date"].astype(str), y=daily["pnl_usdt"], marker_color=colors, name="P&L"))
    fig3.update_layout(template="plotly_dark", height=360, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Data", yaxis_title="USDT")
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(daily, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum trade fechado ainda.")
