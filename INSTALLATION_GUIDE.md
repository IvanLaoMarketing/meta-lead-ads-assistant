# META Lead ADS Assistant — Guida Completa all'Installazione

> **Prodotto by Ivan Lao** · Marketing Automation Specialist · [laoivan.com](https://laoivan.com)
> Make Certified Partner · n8n Expert · Meta Tech Provider
> Supporto: [@ivanlaomarketing](https://www.instagram.com/ivanlaomarketing/)

---

## Prerequisiti

Prima di installare il sistema, assicurati di avere:

| Requisito | Dove ottenerlo |
|---|---|
| Account Meta Business Manager | [business.facebook.com](https://business.facebook.com) |
| Meta Access Token (lunga durata) | Meta for Developers → Graph API Explorer |
| Meta Ad Account ID | Business Manager → Account pubblicitari |
| Meta Page ID | Pagina Facebook → Info → ID pagina |
| API Key OpenRouter (consigliato) | [openrouter.ai](https://openrouter.ai) |
| Python 3.10+ | [python.org](https://python.org) |
| pip | Incluso con Python |

---

## Modalità A — Installazione su Manus (Consigliata)

Questa è la modalità più semplice. Non richiede configurazione locale, server o terminale.

**Step 1 — Crea un progetto Manus**
1. Apri [manus.im](https://manus.im) e crea un nuovo progetto
2. Assegna il nome: `META Lead ADS Assistant`
3. Aggiungi questa conversazione al progetto per dare contesto completo

**Step 2 — Attiva la skill**
1. Nella chat del progetto, scrivi: `/skill meta-ads-agent-builder`
2. Manus caricherà automaticamente tutti i template e la configurazione

**Step 3 — Configura le credenziali**
Nella chat, fornisci le tue credenziali in questo formato:

```
META_ACCESS_TOKEN=EAAxxxxxxxxx
META_AD_ACCOUNT_ID=act_123456789
META_PAGE_ID=123456789
OPENROUTER_API_KEY=sk-or-v1-...
```

**Step 4 — Prima campagna**
Scrivi nella chat:
```
Crea una campagna per [descrivi prodotto], budget [X]€/giorno, 
landing page [URL], target [descrivi audience]
```

Manus eseguirà l'intera pipeline automaticamente.

---

## Modalità B — Installazione Locale (Avanzata)

Per chi vuole eseguire il sistema sul proprio computer o server.

### B1. Clonare il repository

```bash
git clone https://github.com/IvanLaoMarketing/meta-lead-ads-assistant.git
cd meta-lead-ads-assistant
```

### B2. Creare ambiente virtuale

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### B3. Installare dipendenze

```bash
pip install -r requirements.txt
```

### B4. Configurare le variabili d'ambiente

Copia il file di esempio e compilalo:

```bash
cp .env.example .env
```

Apri `.env` con un editor di testo e inserisci le tue credenziali:

```bash
# ── META ADS ──────────────────────────────────────
META_ACCESS_TOKEN=EAAxxxxxxxxx           # Token Meta (lunga durata)
META_AD_ACCOUNT_ID=act_123456789         # DEVE iniziare con "act_"
META_PAGE_ID=123456789
META_PIXEL_ID=                           # Opzionale

# ── LLM (scegli almeno uno) ───────────────────────
OPENROUTER_API_KEY=sk-or-v1-...          # Consigliato
OPENROUTER_MODEL=openai/gpt-4            # Modello da usare

# ── NOTIFICHE (opzionale) ─────────────────────────
NOTIFICATION_CHANNEL=telegram            # telegram / whatsapp / make / n8n / tutti / nessuno
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ── BASEROW CRM (opzionale) ───────────────────────
BASEROW_TOKEN=
BASEROW_API_URL=https://api.gsheets.io
BASEROW_TABLE_CAMPAGNE=
BASEROW_TABLE_KPI=
```

### B5. Verificare la configurazione

```bash
python main.py --check
```

Output atteso:
```
✅ Meta API: connessa (Account: act_123456789)
✅ OpenRouter: connesso (Modello: openai/gpt-4)
✅ Notifiche: Telegram configurato
✅ Google Sheets: connesso
```

### B6. Prima campagna

Modifica `data/brief.json` con i dati della tua campagna, poi:

```bash
python main.py crea --brief data/brief.json
```

### B7. Analisi KPI

```bash
python main.py analizza --id 123456789 --giorni 7
```

---

## Modalità C — Installazione su Server / VPS

Per chi vuole eseguire il sistema in modo continuativo su un server remoto.

### C1. Requisiti server

- Ubuntu 22.04 LTS (o superiore)
- Python 3.10+
- 1 GB RAM minimo
- Accesso SSH

### C2. Setup server

```bash
# Connetti al server
ssh user@tuo-server.com

# Aggiorna il sistema
sudo apt update && sudo apt upgrade -y

# Installa Python e git
sudo apt install python3 python3-pip python3-venv git -y

# Clona il repository
git clone https://github.com/IvanLaoMarketing/meta-lead-ads-assistant.git
cd meta-lead-ads-assistant

# Crea ambiente virtuale e installa dipendenze
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### C3. Configurazione come servizio systemd

Crea il file di servizio:

```bash
sudo nano /etc/systemd/system/meta-ads-assistant.service
```

Contenuto:

```ini
[Unit]
Description=META Lead ADS Assistant — Ivan Lao
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/meta-lead-ads-assistant
Environment=PATH=/home/ubuntu/meta-lead-ads-assistant/venv/bin
ExecStart=/home/ubuntu/meta-lead-ads-assistant/venv/bin/python main.py daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Attiva il servizio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable meta-ads-assistant
sudo systemctl start meta-ads-assistant
```

### C4. Monitoraggio KPI automatico con cron

Per analisi KPI giornaliera automatica:

```bash
crontab -e
```

Aggiungi:

```bash
# Analisi KPI ogni giorno alle 08:00
0 8 * * * /home/ubuntu/meta-lead-ads-assistant/venv/bin/python /home/ubuntu/meta-lead-ads-assistant/main.py analizza-tutte --giorni 1
```

---

## Modalità D — Integrazione con Make o n8n

Per chi vuole integrare il sistema in un workflow di automazione esistente.

### D1. Configurazione webhook Make

1. Crea uno scenario Make con trigger **Webhook**
2. Copia l'URL del webhook
3. Nel `.env` del sistema:

```bash
NOTIFICATION_CHANNEL=make
MAKE_WEBHOOK_CAMPAGNA_CREATA=https://hook.eu1.make.com/xxxxx
MAKE_WEBHOOK_ALERT_KPI=https://hook.eu1.make.com/yyyyy
```

Il sistema invierà automaticamente i dati strutturati a Make ad ogni evento.

### D2. Configurazione webhook n8n

1. Crea un workflow n8n con nodo **Webhook**
2. Copia l'URL del webhook
3. Nel `.env`:

```bash
NOTIFICATION_CHANNEL=n8n
N8N_WEBHOOK_CAMPAGNA_CREATA=https://tuo-n8n.com/webhook/campagna
N8N_WEBHOOK_ALERT_KPI=https://tuo-n8n.com/webhook/kpi
```

### D3. Payload webhook

Ogni notifica invia questo payload JSON:

```json
{
  "message": "✅ Campagna creata con successo!",
  "event": "campagna_creata",
  "campagna_id": "123456789",
  "progetto": "NomeProgetto",
  "budget": 50.0,
  "timestamp": "2026-04-03T10:00:00"
}
```

---

## Configurazione Notifiche Telegram

1. Crea un bot con [@BotFather](https://t.me/BotFather) su Telegram
2. Copia il token del bot
3. Avvia una conversazione con il bot e ottieni il tuo Chat ID con [@userinfobot](https://t.me/userinfobot)
4. Nel `.env`:

```bash
NOTIFICATION_CHANNEL=telegram
TELEGRAM_BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=987654321
```

---

## Configurazione Google Sheets CRM

1. Vai su [Google Cloud Console](https://console.cloud.google.com) → crea un progetto
2. Abilita l'API **Google Sheets** e **Google Drive**
3. Crea un **Service Account** → scarica il file JSON delle credenziali
4. Crea un Google Sheet e condividilo con l'email del Service Account (permesso Editor)
5. Copia l'ID del foglio dall'URL: `https://docs.google.com/spreadsheets/d/**ID_QUI**/edit`
6. Nel `.env`:

```bash
# Path al file JSON del Service Account (o JSON inline come stringa)
GOOGLE_SERVICE_ACCOUNT_JSON=/percorso/al/service-account.json
GOOGLE_SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
```

I fogli **Campagne** e **KPI** vengono creati automaticamente al primo utilizzo con le intestazioni corrette.

---

## Risoluzione Problemi Comuni

| Errore | Causa | Soluzione |
|---|---|---|
| `EnvironmentError: META_ACCESS_TOKEN mancante` | `.env` non configurato | Verifica che `.env` esista e contenga il token |
| `FacebookRequestError: Error 190` | Token Meta scaduto | Rigenera il token su Meta for Developers |
| `FacebookRequestError: Error 17` | Rate limit API Meta | Il sistema riprova automaticamente. Attendi 5 minuti |
| `JSONDecodeError` in copywriter | LLM ha restituito testo non-JSON | Riprova. Se persiste, abbassa `temperature` a 0.5 |
| `act_` mancante nell'Account ID | Formato ID errato | `META_AD_ACCOUNT_ID` deve iniziare con `act_` |
| Campagna non visibile su Meta | Normale — è in stato PAUSED | Attivala manualmente da Meta Ads Manager |

---

## Supporto

Per assistenza tecnica o personalizzazioni del sistema:

- **Email**: tramite [laoivan.com](https://laoivan.com)
- **Instagram**: [@ivanlaomarketing](https://www.instagram.com/ivanlaomarketing/)
- **LinkedIn**: [Ivan Lao](https://www.linkedin.com/in/ivanlaomarketing/)
- **Canale Telegram**: [t.me/IvanLaoMarketingAutomation](https://t.me/IvanLaoMarketingAutomation)

---

*META Lead ADS Assistant è un prodotto sviluppato da Ivan Lao — Marketing Automation Specialist.*
*Tutti i diritti riservati. Vietata la redistribuzione senza autorizzazione scritta.*
