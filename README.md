# KimiClaw Crypto Dashboard

Dashboard em Streamlit para acompanhamento dos resultados do [`kimiclaw-cripto-bot`](https://github.com/leo/kimiclaw-cripto-bot).

## O que faz

- Separa resultados **paper** (simulação) de **real / testnet** (ordens reais na Binance).
- Mostra equity curve, P&L, trades, posições abertas e sinais atuais.
- Calcula métricas de performance (win rate, profit factor, drawdown, etc.).
- Executa um "agente de recomendações" que analisa os dados e sugere ajustes na estratégia.
- Interface visualmente limpa, com tema escuro e cards coloridos.

## Estrutura

```
.
├── app.py                  # Página principal (visão geral)
├── data_loader.py          # Leitura dos JSONs do bot
├── metrics.py              # Cálculo de métricas financeiras
├── recommendations.py      # Agente gerador de recomendações
├── requirements.txt
└── pages/
    ├── 01_Performance.py   # Métricas e equity curve
    ├── 02_Trades.py        # Histórico e posições abertas
    └── 03_Sinais.py        # Sinais por moeda e análise de agents
```

## Como rodar

```bash
cd kimiclaw-cripto-bot-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

O dashboard lê os dados do bot em `../kimiclaw-cripto-bot/data/` por padrão. Você pode alterar o caminho pela variável de ambiente `BOT_DATA_PATH`.

```bash
BOT_DATA_PATH=/caminho/para/o/bot/data streamlit run app.py
```

## Dependências

- streamlit
- plotly
- pandas
- numpy

## Integração com o bot

O bot salva snapshots do saldo, sinais e trades a cada ciclo em:

- `bot_state.json`
- `positions.json`
- `history.json`
- `equity.json` (série temporal do saldo)
- `signals_history.json` (histórico de sinais por ciclo)

Se o dashboard for rodado em outra máquina, basta replicar esses arquivos (via sincronização de pasta, API ou storage compartilhado).
