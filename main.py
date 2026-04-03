"""
main.py
Entry point del sistema META Lead ADS Assistant.

Utilizzo:
  python main.py                          # Avvio interattivo (wizard primo avvio)
  python main.py crea                     # Crea campagna da brief.json
  python main.py crea --brief custom.json # Crea campagna da file custom
  python main.py analizza --id ID         # Analizza KPI campagna
  python main.py --check                  # Verifica configurazione
  python main.py --setup                  # Riesegui wizard configurazione

META Lead ADS Assistant — by Ivan Lao (laoivan.com)
"""

import sys
import os
import json
import argparse
from datetime import datetime

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("main")

# ─────────────────────────────────────────────
# COSTANTI BRANDING
# ─────────────────────────────────────────────
BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║        META LEAD ADS ASSISTANT  ·  by Ivan Lao                  ║
║                                                                  ║
║   Marketing Automation Specialist  |  Make Certified Partner    ║
║   n8n Expert  |  Meta Tech Provider  |  laoivan.com             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""

FUNZIONALITA = """
  COSA PUOI FARE CON QUESTO SISTEMA:
  ───────────────────────────────────────────────────────────────
  ✦  Crea campagne Meta Lead Ads su landing page esterna (ABO/CBO)
  ✦  Genera copy persuasivo (headline, primary text, description)
     con framework AIDA/PAS, ottimizzato per policy Meta
  ✦  Trova automaticamente gli interessi Meta piu' rilevanti
     per il tuo pubblico target tramite AI + Targeting Search API
  ✦  Genera immagini e video AI ottimizzati per le inserzioni
  ✦  Pubblica la campagna su Meta (in bozza o attiva)
  ✦  Abbina la pagina Instagram all'inserzione
  ✦  Configura lingua delle inserzioni (default: Italiano)
  ✦  Monitora i KPI (CPL, CTR, CPC, frequenza) e ricevi alert
     automatici su Telegram quando le soglie vengono superate
  ✦  Salva storico campagne e KPI su Google Sheets
  ───────────────────────────────────────────────────────────────

  Seguimi per aggiornamenti e nuove funzionalita':
  ▸ Instagram  ->  @ivanlaomarketing
  ▸ Telegram   ->  t.me/IvanLaoMarketingAutomation
  ▸ YouTube    ->  @IvanLaoMarketing
  ▸ Sito       ->  laoivan.com
"""

SETUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".setup_done")


# ─────────────────────────────────────────────
# WIZARD DI PRIMO AVVIO
# ─────────────────────────────────────────────

def _input_obbligatorio(prompt: str, nascosto: bool = False) -> str:
    """Chiede un valore obbligatorio finche' non viene inserito."""
    while True:
        if nascosto:
            import getpass
            val = getpass.getpass(prompt)
        else:
            val = input(prompt).strip()
        if val:
            return val
        print("  ⚠  Campo obbligatorio. Inserisci un valore valido.")


def _input_opzionale(prompt: str, default: str = "") -> str:
    """Chiede un valore opzionale con default."""
    val = input(f"{prompt} [{default}]: ").strip()
    return val if val else default


def _scrivi_env(variabili: dict):
    """Scrive le variabili nel file .env."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    righe_esistenti = {}

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for riga in f:
                riga = riga.strip()
                if riga and not riga.startswith("#") and "=" in riga:
                    k, v = riga.split("=", 1)
                    righe_esistenti[k.strip()] = v.strip()

    righe_esistenti.update(variabili)

    with open(env_path, "w") as f:
        f.write("# META Lead ADS Assistant — by Ivan Lao (laoivan.com)\n")
        f.write(f"# Configurato il: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        for k, v in righe_esistenti.items():
            f.write(f"{k}={v}\n")

    print(f"\n  Configurazione salvata in .env\n")


def wizard_primo_avvio():
    """Wizard interattivo di configurazione al primo avvio."""
    print(BANNER)
    print(FUNZIONALITA)

    print("  ════════════════════════════════════════════════════════════")
    print("  BENVENUTO — CONFIGURAZIONE GUIDATA")
    print("  ════════════════════════════════════════════════════════════")
    print("  Questo wizard configura il sistema in pochi minuti.")
    print("  Avrai bisogno di: Meta Access Token, Ad Account ID,")
    print("  Page ID e una chiave API per l'LLM (OpenRouter consigliato).\n")

    input("  Premi INVIO per iniziare la configurazione -> ")
    print()

    variabili = {}

    # ── META ADS ──────────────────────────────────────────────────
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  STEP 1 — Credenziali Meta Ads                          │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("  Dove trovare il token: Meta for Developers -> Graph API Explorer")
    print("  Dove trovare l'Account ID: Business Manager -> Account pubblicitari\n")

    variabili["META_ACCESS_TOKEN"] = _input_obbligatorio("  Meta Access Token (EAAxx...): ", nascosto=True)
    variabili["META_AD_ACCOUNT_ID"] = _input_obbligatorio("  Ad Account ID (act_123456789): ")
    if not variabili["META_AD_ACCOUNT_ID"].startswith("act_"):
        variabili["META_AD_ACCOUNT_ID"] = "act_" + variabili["META_AD_ACCOUNT_ID"]
        print(f"  -> Corretto automaticamente in: {variabili['META_AD_ACCOUNT_ID']}")

    variabili["META_PAGE_ID"] = _input_obbligatorio("  Facebook Page ID: ")

    instagram_id = _input_opzionale("  Instagram Account ID (opzionale, lascia vuoto per saltare)", "")
    if instagram_id:
        variabili["META_INSTAGRAM_ACTOR_ID"] = instagram_id
        print("  ✓ Pagina Instagram abbinata.")

    pixel_id = _input_opzionale("  Meta Pixel ID (opzionale)", "")
    if pixel_id:
        variabili["META_PIXEL_ID"] = pixel_id

    print()

    # ── LLM ───────────────────────────────────────────────────────
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  STEP 2 — Modello AI (LLM)                              │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("  Scegli il provider LLM:")
    print("  1. OpenRouter — GPT-4, Claude, Gemini in un'unica API (consigliato)")
    print("  2. OpenAI — GPT-4 diretto")
    print("  3. Anthropic — Claude diretto\n")

    scelta_llm = _input_opzionale("  Scelta (1/2/3)", "1")

    if scelta_llm == "2":
        variabili["OPENROUTER_API_KEY"] = _input_obbligatorio("  OpenAI API Key (sk-...): ", nascosto=True)
        variabili["OPENROUTER_BASE_URL"] = "https://api.openai.com/v1"
        modello_default = "gpt-4o"
    elif scelta_llm == "3":
        variabili["OPENROUTER_API_KEY"] = _input_obbligatorio("  Anthropic API Key: ", nascosto=True)
        variabili["OPENROUTER_BASE_URL"] = "https://api.anthropic.com/v1"
        modello_default = "claude-3-5-sonnet-20241022"
    else:
        variabili["OPENROUTER_API_KEY"] = _input_obbligatorio("  OpenRouter API Key (sk-or-v1-...): ", nascosto=True)
        variabili["OPENROUTER_BASE_URL"] = "https://openrouter.ai/api/v1"
        modello_default = "openai/gpt-4"

    modello = _input_opzionale(f"  Modello da usare", modello_default)
    variabili["OPENROUTER_MODEL"] = modello
    print()

    # ── NOTIFICHE ─────────────────────────────────────────────────
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  STEP 3 — Notifiche                                     │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("  Scegli il canale per ricevere notifiche e alert KPI:")
    print("  1. Telegram (consigliato)")
    print("  2. Make.com webhook")
    print("  3. n8n webhook")
    print("  4. Nessuna notifica\n")

    scelta_notifiche = _input_opzionale("  Scelta (1/2/3/4)", "1")

    if scelta_notifiche == "1":
        variabili["NOTIFICATION_CHANNEL"] = "telegram"
        variabili["TELEGRAM_BOT_TOKEN"] = _input_obbligatorio("  Telegram Bot Token: ", nascosto=True)
        variabili["TELEGRAM_CHAT_ID"] = _input_obbligatorio("  Telegram Chat ID: ")
        print("  ✓ Notifiche Telegram configurate.")
    elif scelta_notifiche == "2":
        variabili["NOTIFICATION_CHANNEL"] = "make"
        variabili["MAKE_WEBHOOK_CAMPAGNA_CREATA"] = _input_obbligatorio("  Make Webhook URL (campagna creata): ")
        variabili["MAKE_WEBHOOK_ALERT_KPI"] = _input_opzionale("  Make Webhook URL (alert KPI)", "")
        print("  ✓ Notifiche Make.com configurate.")
    elif scelta_notifiche == "3":
        variabili["NOTIFICATION_CHANNEL"] = "n8n"
        variabili["N8N_WEBHOOK_CAMPAGNA_CREATA"] = _input_obbligatorio("  n8n Webhook URL (campagna creata): ")
        variabili["N8N_WEBHOOK_ALERT_KPI"] = _input_opzionale("  n8n Webhook URL (alert KPI)", "")
        print("  ✓ Notifiche n8n configurate.")
    else:
        variabili["NOTIFICATION_CHANNEL"] = "nessuno"
        print("  -> Notifiche disabilitate.")

    print()

    # ── GOOGLE SHEETS ─────────────────────────────────────────────
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  STEP 4 — Google Sheets CRM (opzionale)                 │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("  Salva storico campagne e KPI su Google Sheets.")
    print("  Richiede un Service Account Google (JSON key).\n")

    usa_gsheets = _input_opzionale("  Configurare Google Sheets? (s/n)", "n").lower()
    if usa_gsheets in ("s", "si", "y", "yes"):
        variabili["GOOGLE_SERVICE_ACCOUNT_JSON"] = _input_obbligatorio(
            "  Path al file JSON del Service Account: "
        )
        variabili["GOOGLE_SPREADSHEET_ID"] = _input_obbligatorio(
            "  ID del Google Spreadsheet (dall'URL): "
        )
        print("  ✓ Google Sheets configurato.")
    else:
        print("  -> Google Sheets saltato. Configurabile in seguito nel file .env.")

    print()

    # ── SALVATAGGIO ───────────────────────────────────────────────
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  Configurazione completata!                              │")
    print("  └─────────────────────────────────────────────────────────┘")
    _scrivi_env(variabili)

    # Marca setup come completato
    with open(SETUP_FILE, "w") as f:
        f.write(datetime.now().isoformat())

    print("  Il sistema e' pronto. Puoi ora creare la tua prima campagna.")
    print("  Comando: python main.py crea\n")


# ─────────────────────────────────────────────
# HELPER: DOMANDE INTERATTIVE PRE-CAMPAGNA
# ─────────────────────────────────────────────

def _chiedi_status_campagna() -> str:
    """Chiede se pubblicare la campagna o lasciarla in bozza."""
    print("\n  ┌─────────────────────────────────────────────────────────┐")
    print("  │  Stato campagna dopo la creazione                        │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("  1. BOZZA — Campagna in pausa, revisione manuale su Meta Ads Manager (consigliato)")
    print("  2. ATTIVA — Campagna pubblicata immediatamente\n")
    scelta = _input_opzionale("  Scelta (1/2)", "1")
    if scelta == "2":
        conferma = input("  ⚠  Confermi la pubblicazione immediata? La campagna andra' in spesa. (s/n): ").strip().lower()
        if conferma in ("s", "si", "y"):
            print("  -> Campagna verra' pubblicata ATTIVA.")
            return "ACTIVE"
        else:
            print("  -> Annullato. Campagna in BOZZA.")
    print("  -> Campagna verra' creata in BOZZA (PAUSED).")
    return "PAUSED"


def _chiedi_lingua() -> str:
    """Chiede la lingua delle inserzioni."""
    print("\n  ┌─────────────────────────────────────────────────────────┐")
    print("  │  Lingua delle inserzioni                                 │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("  Esempi: it (Italiano), en (Inglese), es (Spagnolo), fr (Francese)\n")
    lingua = _input_opzionale("  Lingua", "it")
    print(f"  -> Lingua impostata: {lingua.upper()}")
    return lingua


def _suggerisci_interessi(brief: dict) -> list:
    """Usa il LLM per suggerire interessi Meta rilevanti basandosi sul brief."""
    try:
        from utils.openrouter_client import chiedi_llm
        import re

        prompt = (
            "Sei un esperto di Meta Ads. Basandoti su questo brief di campagna:\n\n"
            f"Prodotto/Servizio: {brief.get('descrizione_prodotto', '')}\n"
            f"Target ideale: {brief.get('target_ideale', '')}\n"
            f"Location: {brief.get('location', ['IT'])}\n\n"
            "Suggerisci esattamente 8 interessi Meta Ads specifici e rilevanti per questo target.\n"
            "Rispondi SOLO con una lista JSON di stringhe, senza spiegazioni.\n"
            'Esempio: ["Marketing digitale", "Automazione aziendale", "Imprenditoria"]'
        )

        risposta = chiedi_llm(prompt, temperatura=0.3)
        match = re.search(r'\[.*?\]', risposta, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []
    except Exception as e:
        logger.warning(f"[Main] Impossibile generare suggerimenti interessi: {e}")
        return []


def _chiedi_interessi(brief: dict) -> list:
    """Chiede se aggiungere interessi manuali e suggerisce quelli rilevanti via LLM."""
    print("\n  ┌─────────────────────────────────────────────────────────┐")
    print("  │  Interessi Meta                                          │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("  L'agente Targeting trovera' automaticamente gli interessi ottimali.")
    print("  Vuoi aggiungere anche interessi specifici da includere obbligatoriamente?\n")

    aggiungi = _input_opzionale("  Aggiungere interessi manuali? (s/n)", "n").lower()
    if aggiungi not in ("s", "si", "y", "yes"):
        print("  -> Targeting completamente automatico.")
        return []

    print("\n  Genero suggerimenti basati sul tuo brief...\n")
    suggeriti = _suggerisci_interessi(brief)

    if suggeriti:
        print("  Interessi suggeriti per il tuo target:")
        for i, interesse in enumerate(suggeriti, 1):
            print(f"    {i}. {interesse}")
        print()
        print("  Seleziona i numeri separati da virgola (es: 1,3,5)")
        print("  oppure digita interessi personalizzati separati da virgola.")
        print("  Premi INVIO per usare tutti i suggeriti.\n")

        scelta = input("  Selezione: ").strip()

        if not scelta:
            interessi_scelti = suggeriti
        else:
            parti = [p.strip() for p in scelta.split(",")]
            try:
                indici = [int(p) - 1 for p in parti]
                interessi_scelti = [suggeriti[i] for i in indici if 0 <= i < len(suggeriti)]
            except ValueError:
                interessi_scelti = parti
    else:
        print("  Inserisci gli interessi separati da virgola:")
        testo = input("  Interessi: ").strip()
        interessi_scelti = [i.strip() for i in testo.split(",") if i.strip()]

    print(f"\n  ✓ Interessi aggiunti: {', '.join(interessi_scelti)}")
    return interessi_scelti


# ─────────────────────────────────────────────
# WIZARD COMPILAZIONE BRIEF INTERATTIVO
# ─────────────────────────────────────────────

def wizard_brief_interattivo() -> dict:
    """
    Guida l'utente nella compilazione del brief direttamente da terminale.
    Restituisce un dizionario brief pronto per la pipeline.
    Rende il file brief.json opzionale.
    """
    print("\n  ┌─────────────────────────────────────────────────────────┐")
    print("  │  COMPILAZIONE BRIEF — Nuova Campagna                     │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("  Compila i dati della campagna. Premi INVIO per usare il valore suggerito.\n")

    brief = {}

    # ── Dati base ────────────────────────────────────────────────
    brief["nome_progetto"] = _input_obbligatorio(
        "  Nome progetto (es. Lancio_Corso_Maggio_2026): "
    ).replace(" ", "_")

    brief["url_landing_page"] = _input_obbligatorio(
        "  URL Landing Page (es. https://tuosito.com/offerta): "
    )

    # ── Budget ───────────────────────────────────────────────────
    print()
    tipo_budget = _input_opzionale("  Tipo budget — ABO (per Ad Set) o CBO (per Campagna)", "CBO").upper()
    brief["tipo_budget"] = tipo_budget if tipo_budget in ("ABO", "CBO") else "CBO"

    while True:
        try:
            budget_str = _input_opzionale("  Budget giornaliero in EUR (es. 50)", "50")
            brief["budget_giornaliero"] = float(budget_str)
            break
        except ValueError:
            print("  ⚠  Inserisci un numero valido (es. 50 o 30.50)")

    # ── Date ─────────────────────────────────────────────────────
    data_inizio = _input_opzionale(
        "  Data inizio campagna (YYYY-MM-DD, lascia vuoto per oggi)", ""
    )
    brief["data_inizio"] = data_inizio if data_inizio else datetime.now().strftime("%Y-%m-%d")
    brief["data_fine"] = _input_opzionale("  Data fine campagna (YYYY-MM-DD, opzionale)", "") or None
    brief["valuta"] = "EUR"

    # ── Prodotto e target ─────────────────────────────────────────
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  Descrizione prodotto e target                           │")
    print("  └─────────────────────────────────────────────────────────┘")
    brief["descrizione_prodotto"] = _input_obbligatorio(
        "  Descrivi il prodotto/servizio (2-3 righe): "
    )
    brief["target_ideale"] = _input_obbligatorio(
        "  Descrivi il target ideale (eta', professione, interessi): "
    )

    # Location
    location_str = _input_opzionale("  Paese target (es. IT, IT,CH per piu' paesi)", "IT")
    brief["location"] = [l.strip().upper() for l in location_str.split(",") if l.strip()]

    # ── Copy e creativita' ────────────────────────────────────────
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  Stile copy e creativita'                                │")
    print("  └─────────────────────────────────────────────────────────┘")
    brief["tono_copy"] = _input_opzionale(
        "  Tono del copy",
        "diretto, professionale, orientato ai risultati"
    )
    brief["stile_visivo"] = _input_opzionale(
        "  Stile visivo per le immagini",
        "professionale, colori brand aziendali, sfondo chiaro"
    )
    brief["cta_principale"] = _input_opzionale(
        "  CTA principale (es. Scopri di piu', Iscriviti, Richiedi info)",
        "Scopri di piu'"
    )

    # Video
    genera_video_str = _input_opzionale("  Generare anche un video? (s/n)", "n").lower()
    brief["genera_video"] = genera_video_str in ("s", "si", "y", "yes")

    brief["note_aggiuntive"] = _input_opzionale(
        "  Note aggiuntive per gli agenti (opzionale)", ""
    )

    # ── Riepilogo ─────────────────────────────────────────────────
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  RIEPILOGO BRIEF                                         │")
    print("  └─────────────────────────────────────────────────────────┘")
    print(f"  Progetto    : {brief['nome_progetto']}")
    print(f"  Landing     : {brief['url_landing_page']}")
    print(f"  Budget      : EUR {brief['budget_giornaliero']}/giorno ({brief['tipo_budget']})")
    print(f"  Location    : {', '.join(brief['location'])}")
    print(f"  Inizio      : {brief['data_inizio']}")
    print(f"  Prodotto    : {brief['descrizione_prodotto'][:60]}...")
    print(f"  Target      : {brief['target_ideale'][:60]}...")
    print(f"  CTA         : {brief['cta_principale']}")
    print(f"  Video       : {'Si' if brief['genera_video'] else 'No'}")
    print()

    conferma = _input_opzionale("  Confermi il brief? (s/n)", "s").lower()
    if conferma not in ("s", "si", "y", "yes"):
        print("  -> Brief annullato. Riavvia con: python main.py crea\n")
        sys.exit(0)

    # Salva opzionalmente il brief come JSON per riutilizzo futuro
    salva = _input_opzionale("  Salvare il brief come file JSON per riutilizzarlo? (s/n)", "s").lower()
    if salva in ("s", "si", "y", "yes"):
        nome_file = f"data/brief_{brief['nome_progetto']}.json"
        os.makedirs("data", exist_ok=True)
        with open(nome_file, "w", encoding="utf-8") as f:
            json.dump(brief, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Brief salvato in: {nome_file}")

    print()
    return brief


# ─────────────────────────────────────────────
# COMANDI
# ─────────────────────────────────────────────

def carica_brief(percorso: str) -> dict:
    """Carica e valida il file brief JSON."""
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            brief = json.load(f)
        logger.info(f"[Main] Brief caricato: {brief.get('nome_progetto', 'N/A')}")
        return brief
    except FileNotFoundError:
        logger.error(f"[Main] File brief non trovato: {percorso}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"[Main] Errore parsing brief JSON: {e}")
        sys.exit(1)


def cmd_crea(args):
    """Comando: crea una nuova campagna con wizard interattivo."""
    from agents.orchestrator import esegui_pipeline

    print("\n" + "=" * 66)
    print("  CREAZIONE CAMPAGNA — META Lead ADS Assistant")
    print("=" * 66)

    # Scelta modalita' brief
    brief_esiste = os.path.exists(args.brief)
    if brief_esiste:
        print(f"  Trovato file brief: {args.brief}")
        print("  1. Usa il file brief esistente")
        print("  2. Compila un nuovo brief da terminale")
        print("  3. Compila da terminale e sovrascrivi il file esistente\n")
        scelta_brief = _input_opzionale("  Scelta (1/2/3)", "1")
    else:
        print(f"  File brief non trovato ({args.brief}).")
        print("  Avvio compilazione guidata del brief...\n")
        scelta_brief = "2"

    if scelta_brief == "1":
        brief = carica_brief(args.brief)
        print(f"  Progetto : {brief.get('nome_progetto')}")
        print(f"  Budget   : EUR {brief.get('budget_giornaliero')}/giorno ({brief.get('tipo_budget', 'CBO')})")
        print(f"  Obiettivo: Lead Generation -> {brief.get('url_landing_page')}")
    else:
        brief = wizard_brief_interattivo()
        if scelta_brief == "3":
            with open(args.brief, "w", encoding="utf-8") as f:
                json.dump(brief, f, indent=2, ensure_ascii=False)
            print(f"  \u2713 Brief salvato in: {args.brief}")

    print("=" * 66)

    # ── Domande interattive ────────────────────────────────────────
    status_campagna = _chiedi_status_campagna()
    lingua = _chiedi_lingua()
    interessi_manuali = _chiedi_interessi(brief)

    # Inietta i parametri nel brief
    brief["_status_campagna"] = status_campagna
    brief["lingua"] = lingua
    if interessi_manuali:
        brief["_interessi_manuali"] = interessi_manuali

    # Abbina Instagram se configurato
    instagram_id = os.getenv("META_INSTAGRAM_ACTOR_ID", "")
    if instagram_id:
        brief["_instagram_actor_id"] = instagram_id
        print(f"\n  ✓ Pagina Instagram abbinata (ID: {instagram_id})")

    print(f"\n  Avvio pipeline...\n")

    # ── Esecuzione pipeline ────────────────────────────────────────
    report = esegui_pipeline(brief)

    print("\n" + "=" * 66)
    if report.get("successo"):
        stato_label = "ATTIVA" if status_campagna == "ACTIVE" else "BOZZA (PAUSED)"
        print(f"  Campagna creata con successo!")
        print(f"  ID Meta    : {report.get('campagna_id')}")
        print(f"  Status     : {stato_label}")
        print(f"  Lingua     : {lingua.upper()}")
        print(f"  Durata     : {report.get('durata')}")
        if status_campagna == "PAUSED":
            print(f"\n  -> Revisiona e attiva manualmente da Meta Ads Manager.")
    else:
        print(f"  Pipeline completata con errori:")
        for errore in report.get("errori", []):
            print(f"     [{errore['agente']}] {errore['errore']}")
    print("=" * 66 + "\n")


def cmd_analizza(args):
    """Comando: analizza i KPI di una campagna."""
    from agents.analista import analizza_campagna, stampa_report

    print(f"\n  Analisi KPI — Campagna {args.id} (ultimi {args.giorni} giorni)\n")
    report = analizza_campagna(campaign_id=args.id, giorni=args.giorni)
    stampa_report(report)


def cmd_check(args):
    """Comando: verifica la configurazione del sistema."""
    print(BANNER)
    print("  Verifica configurazione...\n")

    checks = [
        ("META_ACCESS_TOKEN", settings.meta_access_token, True),
        ("META_AD_ACCOUNT_ID", settings.meta_ad_account_id, True),
        ("META_PAGE_ID", settings.meta_page_id, True),
        ("OPENROUTER_API_KEY", settings.openrouter_api_key, True),
        ("OPENROUTER_MODEL", settings.openrouter_model, False),
        ("NOTIFICATION_CHANNEL", settings.notification_channel, False),
        ("TELEGRAM_BOT_TOKEN", settings.telegram_bot_token, False),
        ("GOOGLE_SPREADSHEET_ID", settings.google_spreadsheet_id, False),
        ("META_INSTAGRAM_ACTOR_ID", os.getenv("META_INSTAGRAM_ACTOR_ID", ""), False),
    ]

    tutti_ok = True
    for nome, valore, obbligatorio in checks:
        if valore:
            valore_display = valore[:8] + "..." if len(valore) > 8 else valore
            print(f"  OK  {nome:<35} {valore_display}")
        elif obbligatorio:
            print(f"  ERR {nome:<35} MANCANTE (obbligatorio)")
            tutti_ok = False
        else:
            print(f"  --  {nome:<35} non configurato (opzionale)")

    print()
    if tutti_ok:
        print("  Configurazione completa. Il sistema e' pronto.\n")
    else:
        print("  Alcune variabili obbligatorie mancano.")
        print("  Esegui: python main.py --setup  per avviare il wizard di configurazione.\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    # Primo avvio senza argomenti: wizard di configurazione
    if not os.path.exists(SETUP_FILE) and len(sys.argv) == 1:
        wizard_primo_avvio()
        return

    # Avvio senza argomenti dopo il setup: mostra banner + help
    if len(sys.argv) == 1:
        print(BANNER)
        print(FUNZIONALITA)
        print("  Comandi disponibili:")
        print("  ▸ python main.py crea                  Crea una nuova campagna")
        print("  ▸ python main.py analizza --id ID      Analizza KPI campagna")
        print("  ▸ python main.py --check               Verifica configurazione")
        print("  ▸ python main.py --setup               Riesegui wizard configurazione\n")
        return

    parser = argparse.ArgumentParser(
        description="META Lead ADS Assistant — by Ivan Lao (laoivan.com)",
        add_help=True
    )
    parser.add_argument("--check", action="store_true", help="Verifica la configurazione del sistema")
    parser.add_argument("--setup", action="store_true", help="Riesegui il wizard di configurazione")

    subparsers = parser.add_subparsers(dest="comando")

    # Comando: crea
    parser_crea = subparsers.add_parser("crea", help="Crea una nuova campagna Meta Lead Ads")
    parser_crea.add_argument(
        "--brief",
        default="data/brief.json",
        help="Percorso del file brief JSON (default: data/brief.json)"
    )

    # Comando: analizza
    parser_analizza = subparsers.add_parser("analizza", help="Analizza i KPI di una campagna attiva")
    parser_analizza.add_argument("--id", required=True, help="ID della campagna Meta da analizzare")
    parser_analizza.add_argument(
        "--giorni", type=int, default=7,
        help="Numero di giorni da analizzare (default: 7)"
    )

    args = parser.parse_args()

    # --setup: riesegui wizard
    if args.setup:
        if os.path.exists(SETUP_FILE):
            os.remove(SETUP_FILE)
        wizard_primo_avvio()
        return

    # --check: verifica configurazione
    if args.check:
        cmd_check(args)
        return

    # Validazione variabili d'ambiente per comandi operativi
    try:
        settings.validate_required()
    except EnvironmentError as e:
        print(f"\n  {e}\n")
        print("  Esegui: python main.py --setup  per riconfigurare il sistema.\n")
        sys.exit(1)

    if args.comando == "crea":
        cmd_crea(args)
    elif args.comando == "analizza":
        cmd_analizza(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
