"""
agents/targeting.py
Agente Targeting — definisce l'audience ottimale per campagne Meta Lead Ads.

Flusso:
1. GPT-4 (via OpenRouter) analizza il brief e suggerisce keyword di interesse
2. Meta Marketing API (Targeting Search) cerca gli ID degli interessi corrispondenti
3. Restituisce i parametri di targeting pronti per il Campaign Manager

Supporta: ABO (targeting per Ad Set) e CBO (targeting a livello campagna).
"""

import json
from facebook_business.adobjects.targetingsearch import TargetingSearch
from utils.openrouter_client import chat
from utils.meta_api_client import init_meta_api, safe_meta_call
from utils.logger import get_logger

logger = get_logger("agente_targeting")

SYSTEM_PROMPT_TARGETING = """Sei un esperto di Meta Ads targeting e audience research.

Il tuo compito è analizzare il brief di una campagna e suggerire:
1. Una lista di keyword di interesse da cercare su Meta (max 15, in italiano e inglese)
2. Parametri demografici ottimali (età, genere)
3. Esclusioni consigliate

REGOLE:
- Preferisci interessi specifici e verticali a quelli troppo broad
- Includi sia interessi di prodotto che di comportamento (es. "Small business owners")
- Per campagne B2B italiane: includi sempre interessi in italiano E inglese
- Suggerisci sempre un'audience "broad" (interessi ampi) E una "retargeting" (visitatori sito)

OUTPUT RICHIESTO (JSON puro):
{
  "keyword_interessi": ["...", "..."],
  "eta_min": 25,
  "eta_max": 55,
  "genere": "ALL",
  "esclusioni_suggerite": ["..."],
  "note_strategiche": "..."
}
"""


def _cerca_interessi_meta(keywords: list) -> list:
    """
    Cerca gli ID degli interessi Meta corrispondenti alle keyword fornite.

    Args:
        keywords: Lista di keyword da cercare.

    Returns:
        Lista di dizionari {id, name, audience_size} trovati su Meta.
    """
    interessi_trovati = []
    for keyword in keywords:
        try:
            params = {
                "type": "adinterest",
                "q": keyword,
                "limit": 5
            }
            risultati = safe_meta_call(
                TargetingSearch.search,
                params=params
            )
            for r in risultati:
                interessi_trovati.append({
                    "id": r["id"],
                    "name": r["name"],
                    "audience_size": r.get("audience_size", 0)
                })
            logger.info(f"[Targeting] '{keyword}': {len(risultati)} interessi trovati")
        except Exception as e:
            logger.warning(f"[Targeting] Errore ricerca interesse '{keyword}': {e}")

    # Deduplicazione per ID
    seen = set()
    unici = []
    for i in interessi_trovati:
        if i["id"] not in seen:
            seen.add(i["id"])
            unici.append(i)

    # Ordina per audience_size decrescente e prendi i top 10
    unici.sort(key=lambda x: x["audience_size"], reverse=True)
    return unici[:10]


def definisci_target(brief: dict) -> dict:
    """
    Definisce i parametri di targeting completi per la campagna.

    Args:
        brief: Dizionario con i dati della campagna.

    Returns:
        Dizionario con targeting_spec pronto per Meta API e metadati.
    """
    logger.info("[Targeting] Avvio analisi audience...")
    init_meta_api()

    # Step 1: GPT-4 suggerisce keyword e parametri demografici
    user_prompt = f"""Analizza questo brief e suggerisci il targeting ottimale per Meta Ads:

PRODOTTO/SERVIZIO: {brief.get('descrizione_prodotto', '')}
TARGET IDEALE: {brief.get('target_ideale', '')}
LOCATION: {', '.join(brief.get('location', ['IT']))}
LINGUA: {brief.get('lingua', 'it')}
NOTE: {brief.get('note_aggiuntive', '')}

Restituisci SOLO il JSON richiesto."""

    try:
        raw = chat(
            system_prompt=SYSTEM_PROMPT_TARGETING,
            user_prompt=user_prompt,
            temperature=0.4
        )
        raw = raw.strip().lstrip("```json").rstrip("```").strip()
        suggerimenti = json.loads(raw)
        logger.info(f"[Targeting] GPT-4 ha suggerito {len(suggerimenti['keyword_interessi'])} keyword")
    except Exception as e:
        logger.error(f"[Targeting] Errore analisi GPT-4: {e}")
        raise

    # Step 2: Cerca gli ID degli interessi su Meta
    # Unisci keyword GPT-4 + interessi manuali dal brief (se presenti)
    keywords_base = suggerimenti["keyword_interessi"]
    interessi_manuali = brief.get("_interessi_manuali", [])
    if interessi_manuali:
        keywords_combinate = list(dict.fromkeys(keywords_base + interessi_manuali))  # deduplicati
        logger.info(f"[Targeting] Aggiunti {len(interessi_manuali)} interessi manuali: {interessi_manuali}")
    else:
        keywords_combinate = keywords_base
    interessi = _cerca_interessi_meta(keywords_combinate)

    # Mappa lingua -> ID locale Meta
    lingua = brief.get("lingua", "it").lower()
    locale_map = {"it": 6, "en": 24, "es": 8, "fr": 7, "de": 5, "pt": 9}
    locale_id = locale_map.get(lingua, 6)

    # Step 3: Costruisci targeting_spec per Meta API
    targeting_spec = {
        "geo_locations": {
            "countries": brief.get("location", ["IT"])
        },
        "age_min": suggerimenti.get("eta_min", 25),
        "age_max": suggerimenti.get("eta_max", 55),
        "interests": [{"id": i["id"], "name": i["name"]} for i in interessi],
        "locales": [locale_id]
    }

    # Gestione genere
    genere = suggerimenti.get("genere", "ALL")
    if genere == "M":
        targeting_spec["genders"] = [1]
    elif genere == "F":
        targeting_spec["genders"] = [2]

    risultato = {
        "targeting_spec": targeting_spec,
        "interessi_trovati": interessi,
        "suggerimenti_gpt": suggerimenti,
        "note_strategiche": suggerimenti.get("note_strategiche", "")
    }

    logger.info(f"[Targeting] Completato. {len(interessi)} interessi selezionati.")
    return risultato
