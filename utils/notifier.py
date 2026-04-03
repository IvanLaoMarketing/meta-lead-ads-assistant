"""
utils/notifier.py
Layer di notifica multi-canale: Telegram, WhatsApp Business, Make webhook, n8n webhook.
Il canale viene scelto dalla variabile NOTIFICATION_CHANNEL nel .env.
"""

import requests
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("notifier")


def _send_telegram(message: str):
    """Invia un messaggio via Telegram Bot API."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("[Notifier] Telegram non configurato. Salto notifica.")
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logger.info("[Notifier] Notifica Telegram inviata.")
    except Exception as e:
        logger.error(f"[Notifier] Errore Telegram: {e}")


def _send_whatsapp(message: str):
    """Invia un messaggio di testo via WhatsApp Business Cloud API (Meta)."""
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        logger.warning("[Notifier] WhatsApp non configurato. Salto notifica.")
        return
    url = f"https://graph.facebook.com/v19.0/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": settings.whatsapp_recipient_number,
        "type": "text",
        "text": {"body": message}
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        logger.info("[Notifier] Notifica WhatsApp inviata.")
    except Exception as e:
        logger.error(f"[Notifier] Errore WhatsApp: {e}")


def _send_make_webhook(event: str, data: dict):
    """Chiama il webhook Make.com per l'evento specificato."""
    webhook_url = ""
    if event == "campagna_creata":
        webhook_url = settings.make_webhook_campagna_creata
    elif event == "alert_kpi":
        webhook_url = settings.make_webhook_alert_kpi

    if not webhook_url:
        logger.warning(f"[Notifier] Webhook Make per '{event}' non configurato.")
        return
    try:
        r = requests.post(webhook_url, json=data, timeout=10)
        r.raise_for_status()
        logger.info(f"[Notifier] Webhook Make '{event}' chiamato.")
    except Exception as e:
        logger.error(f"[Notifier] Errore Make webhook: {e}")


def _send_n8n_webhook(event: str, data: dict):
    """Chiama il webhook n8n per l'evento specificato."""
    webhook_url = ""
    if event == "campagna_creata":
        webhook_url = settings.n8n_webhook_campagna_creata
    elif event == "alert_kpi":
        webhook_url = settings.n8n_webhook_alert_kpi

    if not webhook_url:
        logger.warning(f"[Notifier] Webhook n8n per '{event}' non configurato.")
        return
    try:
        r = requests.post(webhook_url, json=data, timeout=10)
        r.raise_for_status()
        logger.info(f"[Notifier] Webhook n8n '{event}' chiamato.")
    except Exception as e:
        logger.error(f"[Notifier] Errore n8n webhook: {e}")


def notify(message: str, event: str = "generico", data: dict = None):
    """
    Invia una notifica sul canale configurato in NOTIFICATION_CHANNEL.

    Args:
        message: Testo della notifica.
        event: Tipo evento ('campagna_creata', 'alert_kpi', 'generico').
        data: Payload JSON aggiuntivo per webhook Make/n8n.
    """
    channel = settings.notification_channel.lower()
    data = data or {}

    if channel == "telegram":
        _send_telegram(message)
    elif channel == "whatsapp":
        _send_whatsapp(message)
    elif channel == "make":
        _send_make_webhook(event, {"message": message, **data})
    elif channel == "n8n":
        _send_n8n_webhook(event, {"message": message, **data})
    elif channel == "tutti":
        _send_telegram(message)
        _send_whatsapp(message)
        _send_make_webhook(event, {"message": message, **data})
        _send_n8n_webhook(event, {"message": message, **data})
    else:
        logger.warning(f"[Notifier] Canale '{channel}' non riconosciuto.")
