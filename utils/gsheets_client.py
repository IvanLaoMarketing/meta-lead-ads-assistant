"""
utils/gsheets_client.py
Client Google Sheets — salva campagne create e KPI nel foglio CRM.

Autenticazione tramite Service Account (JSON key) oppure OAuth2.
Metodo consigliato: Service Account (nessuna interazione utente richiesta).

Struttura attesa del Google Sheet:
- Foglio "Campagne": storico campagne create
- Foglio "KPI": storico analisi KPI

META Lead ADS Assistant — by Ivan Lao (laoivan.com)
"""
import json
from datetime import datetime
from typing import Optional

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("gsheets_client")

# Scopes necessari per lettura/scrittura Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]

# Intestazioni attese nei fogli
HEADERS_CAMPAGNE = [
    "ID Campagna Meta", "Nome Progetto", "Tipo Budget", "Budget Giornaliero (€)",
    "URL Landing Page", "Status", "Modello LLM", "Data Creazione", "Note"
]

HEADERS_KPI = [
    "ID Campagna Meta", "Nome Campagna", "Periodo", "Spesa (€)", "Lead",
    "CPL (€)", "CTR (%)", "CPC (€)", "CPM (€)", "Frequenza", "Reach",
    "Impressioni", "Click", "Giudizio", "Alert", "Data Analisi"
]


def _get_client() -> Optional["gspread.Client"]:
    """
    Inizializza il client Google Sheets tramite Service Account.
    Restituisce None se non configurato.
    """
    if not GSPREAD_AVAILABLE:
        logger.warning("[GSheets] gspread non installato. Esegui: pip install gspread google-auth")
        return None

    if not settings.google_service_account_json:
        logger.warning("[GSheets] GOOGLE_SERVICE_ACCOUNT_JSON non configurato. Salto operazione.")
        return None

    try:
        # Supporta sia path a file JSON che JSON inline come stringa
        sa_info = settings.google_service_account_json.strip()
        if sa_info.startswith("{"):
            service_account_info = json.loads(sa_info)
        else:
            with open(sa_info, "r") as f:
                service_account_info = json.load(f)

        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"[GSheets] Errore autenticazione: {e}")
        return None


def _get_or_create_sheet(client: "gspread.Client", spreadsheet_id: str, sheet_name: str, headers: list) -> Optional["gspread.Worksheet"]:
    """
    Recupera un foglio esistente o lo crea con le intestazioni corrette.
    """
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
            worksheet.append_row(headers)
            logger.info(f"[GSheets] Foglio '{sheet_name}' creato con intestazioni.")
        return worksheet
    except Exception as e:
        logger.error(f"[GSheets] Errore accesso foglio '{sheet_name}': {e}")
        return None


def salva_campagna(dati: dict) -> bool:
    """
    Aggiunge una riga nella scheda 'Campagne' del Google Sheet.

    Args:
        dati: Dizionario con i dati della campagna.
    Returns:
        True se salvato con successo, False altrimenti.
    """
    if not settings.google_spreadsheet_id:
        logger.warning("[GSheets] GOOGLE_SPREADSHEET_ID non configurato. Salto salvataggio campagna.")
        return False

    client = _get_client()
    if not client:
        return False

    worksheet = _get_or_create_sheet(client, settings.google_spreadsheet_id, "Campagne", HEADERS_CAMPAGNE)
    if not worksheet:
        return False

    riga = [
        dati.get("ID Campagna Meta", ""),
        dati.get("Nome Progetto", ""),
        dati.get("Tipo Budget", ""),
        dati.get("Budget Giornaliero", ""),
        dati.get("URL Landing Page", ""),
        dati.get("Status", "PAUSED"),
        dati.get("Modello LLM", settings.openrouter_model),
        dati.get("Data Creazione", datetime.now().strftime("%Y-%m-%d %H:%M")),
        dati.get("Note", "")
    ]

    try:
        worksheet.append_row(riga, value_input_option="USER_ENTERED")
        logger.info(f"[GSheets] Campagna salvata: {dati.get('Nome Progetto')}")
        return True
    except Exception as e:
        logger.error(f"[GSheets] Errore salvataggio campagna: {e}")
        return False


def salva_kpi(dati: dict) -> bool:
    """
    Aggiunge una riga nella scheda 'KPI' del Google Sheet.

    Args:
        dati: Dizionario con i KPI della campagna.
    Returns:
        True se salvato con successo, False altrimenti.
    """
    if not settings.google_spreadsheet_id:
        logger.warning("[GSheets] GOOGLE_SPREADSHEET_ID non configurato. Salto salvataggio KPI.")
        return False

    client = _get_client()
    if not client:
        return False

    worksheet = _get_or_create_sheet(client, settings.google_spreadsheet_id, "KPI", HEADERS_KPI)
    if not worksheet:
        return False

    riga = [
        dati.get("ID Campagna Meta", ""),
        dati.get("Nome Campagna", ""),
        dati.get("Periodo", ""),
        dati.get("Spesa (€)", ""),
        dati.get("Lead", ""),
        dati.get("CPL (€)", ""),
        dati.get("CTR (%)", ""),
        dati.get("CPC (€)", ""),
        dati.get("CPM (€)", ""),
        dati.get("Frequenza", ""),
        dati.get("Reach", ""),
        dati.get("Impressioni", ""),
        dati.get("Click", ""),
        dati.get("Giudizio", ""),
        dati.get("Alert", ""),
        dati.get("Data Analisi", datetime.now().strftime("%Y-%m-%d %H:%M"))
    ]

    try:
        worksheet.append_row(riga, value_input_option="USER_ENTERED")
        logger.info(f"[GSheets] KPI salvati per campagna: {dati.get('ID Campagna Meta')}")
        return True
    except Exception as e:
        logger.error(f"[GSheets] Errore salvataggio KPI: {e}")
        return False


def lista_campagne() -> list:
    """
    Recupera tutte le campagne salvate nel Google Sheet.
    Returns:
        Lista di dizionari con i dati delle campagne.
    """
    if not settings.google_spreadsheet_id:
        return []

    client = _get_client()
    if not client:
        return []

    try:
        spreadsheet = client.open_by_key(settings.google_spreadsheet_id)
        worksheet = spreadsheet.worksheet("Campagne")
        records = worksheet.get_all_records()
        logger.info(f"[GSheets] {len(records)} campagne recuperate.")
        return records
    except Exception as e:
        logger.error(f"[GSheets] Errore lista campagne: {e}")
        return []
