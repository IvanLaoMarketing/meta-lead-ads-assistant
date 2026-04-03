"""
agents/copywriter.py
Agente Copywriter — genera copy per inserzioni Meta Lead Ads.

Integra le skill Manus:
- copywriting: framework conversion-focused (Feature→Benefit→Outcome, no claim falsi)
- humanizer: rimuove pattern AI dal testo generato (no "pivotal", "crucial", "delve", ecc.)
- email-sequence: logica di nurturing per costruire urgenza e ridurre obiezioni nel copy

Produce: headline (3 varianti), primary text, description, CTA.
Tutti i testi sono conformi alle policy pubblicitarie Meta.
"""

import json
from utils.openrouter_client import chat
from utils.logger import get_logger

logger = get_logger("agente_copywriter")

# ─────────────────────────────────────────────
# SYSTEM PROMPT — integra skill copywriting + humanizer
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Sei un copywriter esperto di performance marketing, specializzato in inserzioni Meta Ads con obiettivo Lead Generation su landing page.

FRAMEWORK OBBLIGATORIO (skill copywriting):
- Ogni elemento di copy segue la struttura: Problema → Soluzione → Beneficio → CTA
- Connetti sempre: Feature → Benefit → Outcome (mai solo feature)
- Clarity over cleverness: il messaggio deve essere ovvio, non brillante
- Customer language: usa le parole che il target usa per descrivere il suo problema
- No claim falsi, no statistiche inventate, no garanzie implicite
- Una sola idea per elemento (headline = un messaggio, non tre)
- CTA action-oriented: descrivi cosa ottiene l'utente, non cosa deve fare

REGOLE ANTI-AI (skill humanizer):
- Vietato usare: "pivotal", "crucial", "delve", "landscape", "testament", "underscore", "vibrant", "showcase", "foster", "enhance", "additionally"
- Niente rule of three forzata (es. "veloce, semplice e potente")
- Niente negative parallelisms (es. "Non è solo X, è Y")
- Niente -ing endings superficiali (es. "garantendo risultati eccellenti")
- Frasi corte. Ritmo variato. Tono diretto e concreto.

CONFORMITÀ META ADS POLICY:
- Niente linguaggio discriminatorio o che implichi caratteristiche personali sensibili
- Niente promesse di guadagno garantito
- Niente urgenza falsa (es. "Solo oggi!")
- Il copy deve essere coerente con la landing page indicata

OUTPUT RICHIESTO (JSON puro, nessun testo aggiuntivo):
{
  "headline_varianti": [
    {"testo": "...", "rationale": "..."},
    {"testo": "...", "rationale": "..."},
    {"testo": "...", "rationale": "..."}
  ],
  "primary_text": "...",
  "description": "...",
  "cta_label": "...",
  "note_policy": "..."
}
"""


def genera_copy(brief: dict) -> dict:
    """
    Genera il copy completo per un'inserzione Meta Lead Ads.

    Args:
        brief: Dizionario con i dati della campagna (da brief.json).

    Returns:
        Dizionario con headline_varianti, primary_text, description, cta_label, note_policy.
    """
    logger.info("[Copywriter] Avvio generazione copy...")

    user_prompt = f"""Crea il copy per questa inserzione Meta Lead Ads:

PRODOTTO/SERVIZIO: {brief.get('descrizione_prodotto', '')}
TARGET IDEALE: {brief.get('target_ideale', '')}
URL LANDING PAGE: {brief.get('url_landing_page', '')}
TONO RICHIESTO: {brief.get('tono_copy', 'diretto, professionale, orientato ai risultati')}
CTA PRINCIPALE: {brief.get('cta_principale', 'Scopri di più')}
NOTE AGGIUNTIVE: {brief.get('note_aggiuntive', '')}

Ricorda:
- Headline: max 40 caratteri (limite Meta)
- Primary Text: max 125 caratteri per la preview, ma puoi scrivere fino a 500 caratteri
- Description: max 30 caratteri
- Il copy deve portare il lettore a cliccare sulla landing page, NON compilare un modulo Meta integrato

Restituisci SOLO il JSON richiesto, senza markdown o testo aggiuntivo."""

    try:
        raw = chat(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.75
        )

        # Pulizia risposta (rimuove eventuali blocchi markdown)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        copy_data = json.loads(raw)
        logger.info(f"[Copywriter] Copy generato. Headline selezionata: {copy_data['headline_varianti'][0]['testo']}")
        return copy_data

    except json.JSONDecodeError as e:
        logger.error(f"[Copywriter] Errore parsing JSON risposta LLM: {e}")
        logger.debug(f"[Copywriter] Risposta grezza: {raw}")
        raise
    except Exception as e:
        logger.error(f"[Copywriter] Errore generazione copy: {e}")
        raise
