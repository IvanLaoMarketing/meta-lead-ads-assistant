"""
utils/openrouter_client.py
Client centralizzato per OpenRouter (GPT-4).
Usato da: Agente Copywriter, Agente Targeting.
"""

import requests
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("openrouter_client")


def chat(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """
    Chiama GPT-4 via OpenRouter e restituisce il testo generato.

    Args:
        system_prompt: Istruzioni di sistema (persona + regole).
        user_prompt: Input specifico del task.
        temperature: Creatività (0.0 = deterministico, 1.0 = creativo).

    Returns:
        Testo generato dal modello.
    """
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://laoivan.com",
        "X-Title": "META Lead ADS Assistant"
    }

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature
    }

    try:
        response = requests.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        text = result["choices"][0]["message"]["content"]
        logger.info(f"[OpenRouter] Risposta ricevuta ({len(text)} caratteri)")
        return text
    except requests.exceptions.HTTPError as e:
        logger.error(f"[OpenRouter] Errore HTTP: {e.response.status_code} — {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"[OpenRouter] Errore generico: {e}")
        raise
