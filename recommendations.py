"""Agente analítico de recomendações para ajuste da estratégia.

Esse módulo simula a análise de um agente especialista: ele lê as métricas,
o histórico de trades, a curva de equity e os sinais recentes e produz
recomendações acionáveis com prioridade e justificativa.
"""

from __future__ import annotations

import pandas as pd

from metrics import calc_equity_drawdown, calc_trade_metrics


def _pct(value: float) -> str:
    return f"{value:.2f}%"


def generate_recommendations(
    trades: pd.DataFrame,
    equity: pd.DataFrame,
    signals: pd.DataFrame,
    state: dict,
    settings: dict,
) -> list[dict]:
    """Retorna lista de recomendações com ``title``, ``priority``, ``category`` e ``message``."""
    recs: list[dict] = []

    metrics = calc_trade_metrics(trades)
    total = metrics["total_trades"]

    # ------------------------------------------------------------------
    # 1. Volume de trades
    # ------------------------------------------------------------------
    if total == 0:
        recs.append(
            {
                "title": "Nenhum trade fechado ainda",
                "category": "volume",
                "priority": "média",
                "message": (
                    "O bot ainda não registrou trades fechados. Verifique se o modo paper está rodando "
                    "e se os sinais estão atingindo o score mínimo. Considere reduzir ``min_score`` "
                    "temporariamente para observar mais operações."
                ),
            }
        )
    elif total < 10:
        recs.append(
            {
                "title": "Amostra pequena de trades",
                "category": "volume",
                "priority": "baixa",
                "message": (
                    f"Apenas {total} trades fechados. As métricas ainda não são estatisticamente significativas. "
                    "Continue operando em paper antes de avaliar live."
                ),
            }
        )

    # ------------------------------------------------------------------
    # 2. Win rate
    # ------------------------------------------------------------------
    win_rate = metrics["win_rate"]
    if total >= 10:
        if win_rate < 35:
            recs.append(
                {
                    "title": "Win rate muito baixo",
                    "category": "acerto",
                    "priority": "alta",
                    "message": (
                        f"Win rate de {_pct(win_rate)} está abaixo de 35%. A estratégia está errando muito. "
                        "Recomendações: (a) aumente ``min_score`` para filtrar sinais fracos; "
                        "(b) teste estratégias individuais (rsi_reversal, ema_crossover, macd) separadamente; "
                        "(c) adicione um filtro de tendência de maior prazo (ex: preço acima da EMA200)."
                    ),
                }
            )
        elif win_rate < 45:
            recs.append(
                {
                    "title": "Win rate abaixo da zona saudável",
                    "category": "acerto",
                    "priority": "média",
                    "message": (
                        f"Win rate de {_pct(win_rate)} pode ser lucrativo se o payoff for alto, "
                        "mas é arriscado. Aumente a razão risco/retorno (TP maior ou SL menor) "
                        "ou exija score mais alto para entrada."
                    ),
                }
            )
        elif win_rate > 65:
            recs.append(
                {
                    "title": "Win rate alto — verifique overfitting",
                    "category": "acerto",
                    "priority": "baixa",
                    "message": (
                        f"Win rate de {_pct(win_rate)} é alto. Confirme se não houve overfitting em paper. "
                        "Verifique se o payoff médio ainda é positivo e se a amostra cobriu diferentes regimes de mercado."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # 3. Payoff e profit factor
    # ------------------------------------------------------------------
    pf = metrics["profit_factor"]
    payoff = metrics["payoff_ratio"]
    if total >= 5:
        if pf < 1.0:
            recs.append(
                {
                    "title": "Profit factor abaixo de 1 — estratégia perdedora",
                    "category": "rentabilidade",
                    "priority": "alta",
                    "message": (
                        f"Profit factor {pf:.2f} indica que as perdas superam os ganhos. "
                        "Pare imediatamente de escalar. Reveja stop loss / take profit, "
                        "reduza operações e valide em backtest antes de continuar."
                    ),
                }
            )
        elif pf < 1.5:
            recs.append(
                {
                    "title": "Profit factor frágil",
                    "category": "rentabilidade",
                    "priority": "média",
                    "message": (
                        f"Profit factor {pf:.2f} é positivo mas frágil. Uma sequência de perdas pode zerar os ganhos. "
                        "Aumente o payoff (TP/SL) ou reduza o número de trades de baixa qualidade."
                    ),
                }
            )
        if payoff < 1.0 and metrics["avg_loss"] != 0:
            recs.append(
                {
                    "title": "Payoff médio negativo",
                    "category": "rentabilidade",
                    "priority": "alta",
                    "message": (
                        f"Média de ganho ({metrics['avg_win']:.2f}) é menor que média de perda ({abs(metrics['avg_loss']:.2f)}). "
                        "Ajuste para TP/SL maior que 2:1. Exemplo: SL 2% e TP 4%+."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # 4. Drawdown
    # ------------------------------------------------------------------
    if not equity.empty and "balance_usdt" in equity.columns:
        dd_df = calc_equity_drawdown(equity)
        max_dd = dd_df["drawdown_pct"].min()
        if max_dd <= -10:
            recs.append(
                {
                    "title": "Drawdown máximo crítico",
                    "category": "risco",
                    "priority": "alta",
                    "message": (
                        f"Drawdown máximo de {_pct(max_dd)} ultrapassa 10% do capital. "
                        "Reduza ``max_position_pct`` ou ``max_open_positions``, "
                        "ative ``trailing_stop_pct`` e revise o kill switch diário."
                    ),
                }
            )
        elif max_dd <= -5:
            recs.append(
                {
                    "title": "Drawdown elevado",
                    "category": "risco",
                    "priority": "média",
                    "message": (
                        f"Drawdown máximo de {_pct(max_dd)} merece atenção. "
                        "Considere reduzir o tamanho das posições ou aumentar o intervalo entre análises."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # 5. Sinais recentes
    # ------------------------------------------------------------------
    if not signals.empty:
        recent = signals.sort_values("timestamp").drop_duplicates(subset=["symbol"], keep="last")
        buy_count = (recent["signal"] == "BUY").sum()
        sell_count = (recent["signal"] == "SELL").sum()
        hold_count = (recent["signal"] == "HOLD").sum()
        if buy_count == 0 and sell_count == 0:
            recs.append(
                {
                    "title": "Mercado sem sinais claros",
                    "category": "sinais",
                    "priority": "baixa",
                    "message": (
                        "Todos os ativos monitorados estão em HOLD. Isso pode indicar mercado de consolidação. "
                        "Avalie reduzir ``min_score`` ou adicionar mais pares."
                    ),
                }
            )
        if buy_count >= len(recent) * 0.7:
            recs.append(
                {
                    "title": "Muitos sinais de compra simultâneos",
                    "category": "sinais",
                    "priority": "média",
                    "message": (
                        f"{buy_count} de {len(recent)} ativos estão em BUY. Isso pode expor o capital demais. "
                        "Confirme se ``max_open_positions`` limita o risco e evite FOMO."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # 6. Estado geral
    # ------------------------------------------------------------------
    if state.get("offline_fallback"):
        recs.append(
            {
                "title": "Bot está em modo offline/fallback",
                "category": "infra",
                "priority": "alta",
                "message": (
                    "O último ciclo usou preços simulados (fallback offline). Resultados não refletem o mercado real. "
                    "Verifique conectividade com a Binance e as chaves de API."
                ),
            }
        )

    if state.get("daily", {}).get("kill_switch_active"):
        recs.append(
            {
                "title": "Kill switch ativo hoje",
                "category": "risco",
                "priority": "alta",
                "message": (
                    "O bot pausou compras hoje por drawdown diário. Reveja as perdas antes de reativar. "
                    "Não desative o kill switch sem entender a causa raiz."
                ),
            }
        )

    if not recs:
        recs.append(
            {
                "title": "Estratégia em linha",
                "category": "geral",
                "priority": "baixa",
                "message": (
                    "Nenhum problema crítico detectado. Continue coletando dados em paper e "
                    "monitore win rate, profit factor e drawdown conforme a amostra cresce."
                ),
            }
        )

    return recs
