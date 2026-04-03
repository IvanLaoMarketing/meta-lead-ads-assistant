"""
agents/grafico.py
Agente Grafico — genera asset visivi (immagini e video) per inserzioni Meta Lead Ads.

Flusso:
1. GPT-4 (via OpenRouter) costruisce il prompt visivo ottimizzato per Meta Ads
   basandosi sul brief, sullo stile brand e sul copy già generato
2. Manus genera l'immagine (o il video) tramite tool AI integrato
3. L'asset viene salvato localmente in data/output/
4. Viene restituito il percorso file per il Campaign Manager

Formati supportati:
- Immagine: 1080x1080 (1:1) e 1080x1350 (4:5) — ottimali per Feed e Stories
- Video: breve (15-30s) per Reels e Stories

Stile brand Ivan Lao (applicato di default se non diversamente specificato):
- Sfondo: #0d0d0d (dark)
- Accenti: #E1306C (rosa), #833AB4 (viola), #FCAF45 (oro)
- Mood: tech-forward, professionale, no stock photo
"""

import os
import json
from datetime import datetime
from utils.openrouter_client import chat
from utils.logger import get_logger

logger = get_logger("agente_grafico")

os.makedirs("data/output", exist_ok=True)

# ─────────────────────────────────────────────
# SYSTEM PROMPT — costruttore di prompt visivi per Meta Ads
# ─────────────────────────────────────────────
SYSTEM_PROMPT_PROMPT_BUILDER = """Sei un art director specializzato in Meta Ads ad alta conversione.

Il tuo compito è costruire un prompt dettagliato per la generazione AI di un'immagine pubblicitaria.

REGOLE CREATIVE:
- Formato: 1080x1080px (feed) o 1080x1350px (4:5 per mobile)
- Stile: professionale, dark tech, no stock photo feel
- Testo sull'immagine: massimo 6 parole (regola Meta 20% testo)
- Il visual deve comunicare il beneficio principale in modo immediato
- Evita volti generici, immagini di persone sorridenti in modo forzato, sfondi bianchi

STRUTTURA PROMPT OUTPUT:
- Descrivi la scena principale (cosa si vede)
- Specifica colori, illuminazione, mood
- Indica eventuali testi sovrapposti (max 6 parole)
- Specifica il formato (1:1 o 4:5)

OUTPUT RICHIESTO (JSON puro):
{
  "prompt_immagine": "...",
  "prompt_video": "...",
  "formato": "1:1",
  "testo_sovrapposto": "...",
  "rationale": "..."
}
"""


def _costruisci_prompt_visivo(brief: dict, copy: dict = None) -> dict:
    """
    Usa GPT-4 per costruire il prompt visivo ottimizzato.

    Args:
        brief: Dati della campagna.
        copy: Copy già generato (opzionale, per coerenza visiva).

    Returns:
        Dizionario con prompt_immagine, prompt_video, formato, testo_sovrapposto.
    """
    headline = ""
    if copy and copy.get("headline_varianti"):
        headline = copy["headline_varianti"][0]["testo"]

    user_prompt = f"""Costruisci il prompt visivo per questa inserzione Meta Ads:

PRODOTTO/SERVIZIO: {brief.get('descrizione_prodotto', '')}
TARGET: {brief.get('target_ideale', '')}
STILE VISIVO RICHIESTO: {brief.get('stile_visivo', 'dark tech, sfondo scuro, accenti rosa e viola')}
HEADLINE COPY: {headline}
CTA: {brief.get('cta_principale', '')}
GENERA VIDEO: {brief.get('genera_video', False)}

Restituisci SOLO il JSON richiesto."""

    raw = chat(
        system_prompt=SYSTEM_PROMPT_PROMPT_BUILDER,
        user_prompt=user_prompt,
        temperature=0.8
    )
    raw = raw.strip().lstrip("```json").rstrip("```").strip()
    return json.loads(raw)


def genera_asset(brief: dict, copy: dict = None) -> dict:
    """
    Genera l'asset grafico (immagine e/o video) per la campagna.

    NOTA IMPLEMENTATIVA:
    La generazione effettiva dell'immagine avviene tramite il tool AI di Manus
    (nano banana / generate mode). Questo agente costruisce il prompt ottimizzato
    e prepara la struttura dati. La generazione viene poi eseguita dall'orchestratore
    Manus che ha accesso diretto ai tool di generazione media.

    Args:
        brief: Dati della campagna.
        copy: Copy già generato (per coerenza visiva).

    Returns:
        Dizionario con prompt_generazione, percorso_file_atteso, metadati.
    """
    logger.info("[Grafico] Costruzione prompt visivo...")

    try:
        prompt_data = _costruisci_prompt_visivo(brief, copy)
    except Exception as e:
        logger.error(f"[Grafico] Errore costruzione prompt: {e}")
        raise

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_progetto = brief.get("nome_progetto", "campagna").replace(" ", "_")
    output_dir = f"data/output/{nome_progetto}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    percorso_immagine = f"{output_dir}/creative_1x1.png"
    percorso_video = f"{output_dir}/creative_video.mp4" if brief.get("genera_video") else None

    # Salva i prompt per riferimento e per la generazione Manus
    prompt_file = f"{output_dir}/prompts.json"
    with open(prompt_file, "w", encoding="utf-8") as f:
        json.dump(prompt_data, f, ensure_ascii=False, indent=2)

    logger.info(f"[Grafico] Prompt salvato in: {prompt_file}")
    logger.info(f"[Grafico] Prompt immagine: {prompt_data.get('prompt_immagine', '')[:100]}...")

    risultato = {
        "prompt_immagine": prompt_data.get("prompt_immagine"),
        "prompt_video": prompt_data.get("prompt_video") if brief.get("genera_video") else None,
        "formato": prompt_data.get("formato", "1:1"),
        "testo_sovrapposto": prompt_data.get("testo_sovrapposto"),
        "percorso_immagine": percorso_immagine,
        "percorso_video": percorso_video,
        "output_dir": output_dir,
        "prompt_file": prompt_file,
        "genera_video": brief.get("genera_video", False),
        # Flag per Manus: indica che la generazione media deve essere eseguita
        "richiede_generazione_manus": True
    }

    logger.info("[Grafico] Struttura asset pronta. In attesa di generazione Manus.")
    return risultato
