"""
config/settings.py
Caricamento e validazione centralizzata delle variabili d'ambiente.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    # --- META / FACEBOOK ---
    meta_access_token: str = Field(default_factory=lambda: os.getenv("META_ACCESS_TOKEN", ""))
    meta_ad_account_id: str = Field(default_factory=lambda: os.getenv("META_AD_ACCOUNT_ID", ""))
    meta_page_id: str = Field(default_factory=lambda: os.getenv("META_PAGE_ID", ""))
    meta_pixel_id: str = Field(default_factory=lambda: os.getenv("META_PIXEL_ID", ""))
    meta_app_id: str = Field(default_factory=lambda: os.getenv("META_APP_ID", ""))
    meta_app_secret: str = Field(default_factory=lambda: os.getenv("META_APP_SECRET", ""))

    # --- OPENROUTER (LLM: GPT-4) ---
    openrouter_api_key: str = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_model: str = Field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "openai/gpt-4"))
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # --- NOTIFICHE TELEGRAM ---
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

    # --- WHATSAPP BUSINESS (Meta Cloud API) ---
    whatsapp_access_token: str = Field(default_factory=lambda: os.getenv("WHATSAPP_ACCESS_TOKEN", ""))
    whatsapp_phone_number_id: str = Field(default_factory=lambda: os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""))
    whatsapp_recipient_number: str = Field(default_factory=lambda: os.getenv("WHATSAPP_RECIPIENT_NUMBER", ""))

    # --- GOOGLE SHEETS (CRM / Storico Campagne) ---
    google_service_account_json: str = Field(default_factory=lambda: os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""))
    google_spreadsheet_id: str = Field(default_factory=lambda: os.getenv("GOOGLE_SPREADSHEET_ID", ""))

    # --- MAKE.COM / N8N WEBHOOK ---
    make_webhook_campagna_creata: str = Field(default_factory=lambda: os.getenv("MAKE_WEBHOOK_CAMPAGNA_CREATA", ""))
    make_webhook_alert_kpi: str = Field(default_factory=lambda: os.getenv("MAKE_WEBHOOK_ALERT_KPI", ""))
    n8n_webhook_campagna_creata: str = Field(default_factory=lambda: os.getenv("N8N_WEBHOOK_CAMPAGNA_CREATA", ""))
    n8n_webhook_alert_kpi: str = Field(default_factory=lambda: os.getenv("N8N_WEBHOOK_ALERT_KPI", ""))

    # --- CANALE NOTIFICA PREFERITO ---
    notification_channel: str = Field(default_factory=lambda: os.getenv("NOTIFICATION_CHANNEL", "telegram"))

    # --- GENERALI ---
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    output_dir: str = Field(default_factory=lambda: os.getenv("OUTPUT_DIR", "data/output"))
    logs_dir: str = Field(default_factory=lambda: os.getenv("LOGS_DIR", "data/logs"))

    def validate_required(self):
        """Verifica che le variabili critiche siano presenti prima di avviare il sistema."""
        missing = []
        if not self.meta_access_token:
            missing.append("META_ACCESS_TOKEN")
        if not self.meta_ad_account_id:
            missing.append("META_AD_ACCOUNT_ID")
        if not self.meta_page_id:
            missing.append("META_PAGE_ID")
        if not self.openrouter_api_key:
            missing.append("OPENROUTER_API_KEY")
        if missing:
            raise EnvironmentError(
                f"[ERRORE] Variabili d'ambiente mancanti: {', '.join(missing)}.\n"
                f"Controlla il file .env e assicurati di aver compilato tutti i campi obbligatori."
            )


settings = Settings()
