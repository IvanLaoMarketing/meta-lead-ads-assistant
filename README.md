# META Lead ADS Assistant

> **by Ivan Lao** · Marketing Automation Specialist · [laoivan.com](https://laoivan.com)
> Make Certified Partner · n8n Expert · Meta Tech Provider

Sistema multi-agente Python per la creazione, pubblicazione e ottimizzazione automatica di campagne **Meta Lead Ads** (obiettivo: Lead Generation su landing page esterna, no modulo Meta integrato). Supporta ABO e CBO.

---

## Agenti Specializzati

| Agente | Funzione |
|---|---|
| **Orchestratore** | Coordina la pipeline completa con threading parallelo |
| **Copywriter** | Genera headline, primary text, description (GPT-4 + AIDA/PAS + humanizer) |
| **Targeting** | Analizza il brief e trova gli interessi Meta ottimali via Targeting Search API |
| **Grafico** | Costruisce il prompt ottimizzato per la generazione di immagini e video AI |
| **Campaign Manager** | Crea la campagna su Meta Marketing API (sempre in stato PAUSED) |
| **Analista KPI** | Monitora le performance e invia alert quando i KPI superano le soglie |

## Stack Tecnologico

- **LLM**: OpenRouter (GPT-4 default) — configurabile con Claude, Gemini, OpenAI diretto
- **Meta API**: `facebook-business` SDK con retry/backoff automatico (tenacity)
- **Storage CRM**: Google Sheets (gspread + Service Account)
- **Notifiche**: Telegram / WhatsApp Business / Make.com / n8n
- **Validazione**: Pydantic + python-dotenv

## Installazione Rapida

```bash
git clone https://github.com/IvanLaoMarketing/meta-lead-ads-assistant.git
cd meta-lead-ads-assistant
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Crea il file .env con le tue credenziali (vedi .env.example)
python main.py --check
```

## Utilizzo

```bash
# Crea una campagna
python main.py crea --brief data/brief.json

# Analizza KPI di una campagna attiva
python main.py analizza --id 123456789 --giorni 7
```

## Configurazione Minima (.env)

```bash
META_ACCESS_TOKEN=EAAxxxxxxxxx
META_AD_ACCOUNT_ID=act_123456789
META_PAGE_ID=123456789
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-4
```

Per la guida completa con tutte le modalità di installazione (Manus, locale, VPS, Make/n8n): vedi [`INSTALLATION_GUIDE.md`](INSTALLATION_GUIDE.md).

## Struttura Progetto

```
META_Lead_ADS_Assistant/
├── main.py                  ← Entry point CLI
├── agents/
│   ├── orchestrator.py      ← Pipeline principale (threading parallelo)
│   ├── copywriter.py        ← Generazione copy Meta-compliant
│   ├── targeting.py         ← Ricerca interessi Meta API
│   ├── grafico.py           ← Prompt builder per creatività AI
│   ├── campaign_manager.py  ← Creazione campagna Meta (PAUSED)
│   └── analista.py          ← Monitoraggio KPI e alert soglie
├── config/settings.py       ← Configurazione centralizzata (Pydantic)
├── data/brief.json          ← Input campagna (editabile)
└── utils/
    ├── openrouter_client.py ← Client LLM unificato
    ├── meta_api_client.py   ← Client Meta API con retry
    ├── gsheets_client.py    ← Client Google Sheets CRM
    ├── notifier.py          ← Notifiche multi-canale
    └── logger.py            ← Logger centralizzato
```

## Note sulla Sicurezza

- Non committare **mai** il file `.env` in repository pubblici
- Il token Meta deve avere solo i permessi strettamente necessari (`ads_management`, `ads_read`)
- Le campagne vengono sempre create in stato `PAUSED` — l'attivazione è sempre manuale

## Supporto e Contatti

- **Instagram**: [@ivanlaomarketing](https://www.instagram.com/ivanlaomarketing/)
- **LinkedIn**: [Ivan Lao](https://www.linkedin.com/in/ivanlaomarketing/)
- **Telegram**: [t.me/IvanLaoMarketingAutomation](https://t.me/IvanLaoMarketingAutomation)
- **YouTube**: [@IvanLaoMarketing](https://www.youtube.com/@IvanLaoMarketing)
- **Sito**: [laoivan.com](https://laoivan.com)

---

*META Lead ADS Assistant è un prodotto sviluppato da Ivan Lao — Marketing Automation Specialist, Firenze.*
*P.IVA: 04121830246 · Viale Spartaco Lavagnini, 8 — 50129 Firenze (FI)*
*Tutti i diritti riservati. Vietata la redistribuzione senza autorizzazione scritta.*
