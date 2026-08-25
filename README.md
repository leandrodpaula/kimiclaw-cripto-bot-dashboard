# KimiClaw Crypto Dashboard

Dashboard em Streamlit para acompanhamento dos resultados do [`kimiclaw-cripto-bot`](https://github.com/leo/kimiclaw-cripto-bot).

## O que faz

- Separa resultados **paper** (simulação) de **real / testnet** (ordens reais na Binance).
- Mostra equity curve, P&L, trades, posições abertas e sinais atuais.
- Calcula métricas de performance (win rate, profit factor, drawdown, etc.).
- Executa um "agente de recomendações" que analisa os dados e sugere ajustes na estratégia.
- Indicador visual de conexão com o MongoDB Atlas.
- Edição de configurações (settings + moedas) diretamente pelo Streamlit.
- Interface visualmente limpa, com tema escuro e cards coloridos.

## Estrutura

```
.
├── app.py                  # Página principal (visão geral)
├── data_loader.py          # Leitura dos dados no MongoDB Atlas
├── metrics.py              # Cálculo de métricas financeiras
├── recommendations.py      # Agente gerador de recomendações
├── requirements.txt
└── pages/
    ├── 01_Performance.py   # Métricas e equity curve
    ├── 02_Trades.py        # Histórico e posições abertas
    ├── 03_Sinais.py        # Sinais por moeda e análise de agents
    └── 04_Configuracoes.py # Edição de settings e moedas no MongoDB
```

## Como rodar

```bash
cd kimiclaw-cripto-bot-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

O dashboard lê os dados exclusivamente do **MongoDB Atlas**. Configure a URI no `.env`
local ou nos **Secrets** do Streamlit Cloud (`Settings → Secrets`):

```toml
MONGODB_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net"
MONGODB_DB = "kimi_trader"
```

> Não se esqueça de adicionar o IP da máquina em **Network Access → IP Access List** no Atlas.

## Deploy no Streamlit Cloud

1. **Crie um repositório no GitHub** contendo apenas a pasta `kimiclaw-cripto-bot-dashboard/` (ou o conteúdo dela na raiz).
2. Acesse [share.streamlit.io](https://share.streamlit.io) e clique em **New app**.
3. Conecte sua conta do GitHub e selecione o repositório, branch e arquivo principal `app.py`.
4. Em **Advanced settings**, deixe o Python padrão (3.10+) e não adicione variáveis de ambiente manualmente.
5. Clique em **Deploy**.
6. Após o deploy, vá em **Settings → Secrets** do app e adicione:

   ```toml
   MONGODB_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net"
   MONGODB_DB = "kimi_trader"
   ```

7. No MongoDB Atlas, adicione o IP do Streamlit Cloud na whitelist:
   - Opção rápida para testes: **Network Access → Add IP Address → Allow Access from Anywhere** (`0.0.0.0/0`).
   - Opção recomendada para produção: adicione os IPs de saída específicos do Streamlit Cloud (consulte a documentação oficial ou monitore os logs de conexão).
8. Reinicie o app em **Settings → Reboot** ou faça um novo commit no repositório.
9. Acesse a URL do app. Na sidebar deve aparecer 🟢 **MongoDB Atlas** quando a conexão estiver ativa.

> **Dica:** o dashboard não usa arquivos `.env` no Streamlit Cloud. As credenciais devem estar obrigatoriamente em **Secrets**.

## Dependências

- streamlit
- plotly
- pandas
- numpy
- pymongo
- python-dotenv

## Integração com o bot

O bot persiste estado, posições, trades, equity, sinais e **configurações** no MongoDB Atlas. O dashboard lê e escreve diretamente nessas collections:

- `bot_state`
- `positions`
- `trades`
- `equity_snapshots`
- `signal_cycles`
- `settings`
- `coins`

A página **Configurações** permite ajustar `settings.json` e `coins.json` pelo Streamlit; o bot lê os novos valores no próximo ciclo.

O status de conexão é exibido na sidebar e em avisos nas páginas quando o Atlas está indisponível.
