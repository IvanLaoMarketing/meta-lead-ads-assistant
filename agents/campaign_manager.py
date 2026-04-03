"""
agents/campaign_manager.py
Agente Campaign Manager — crea la struttura completa della campagna su Meta.

Struttura creata:
  Campagna (ABO o CBO)
    └── Ad Set (targeting, budget ABO, ottimizzazione LEAD)
          └── Ad Creative (immagine caricata + copy)
                └── Ad (inserzione attiva)

Obiettivo: LEAD_GENERATION con traffico su landing page esterna (no modulo Meta integrato).
Supporta sia ABO (budget a livello Ad Set) che CBO (budget a livello Campagna).

Parametri aggiuntivi letti dal brief (iniettati da main.py):
  _status_campagna    : "PAUSED" (default) o "ACTIVE"
  lingua              : codice lingua inserzioni, es. "it" (default)
  _instagram_actor_id : ID account Instagram da abbinare all'inserzione
"""

import os
import json
from datetime import datetime
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adimage import AdImage
from utils.meta_api_client import init_meta_api, get_ad_account, safe_meta_call
from utils.logger import get_logger
from config.settings import settings

logger = get_logger("agente_campaign_manager")


def _carica_immagine(percorso_file: str) -> str:
    """
    Carica un'immagine sull'account pubblicitario Meta.

    Args:
        percorso_file: Percorso locale dell'immagine.

    Returns:
        Hash dell'immagine caricata (usato per creare la creativita').
    """
    if not os.path.exists(percorso_file):
        raise FileNotFoundError(f"Immagine non trovata: {percorso_file}")

    image = AdImage(parent_id=settings.meta_ad_account_id)
    image[AdImage.Field.filename] = percorso_file

    safe_meta_call(image.remote_create)
    image_hash = image[AdImage.Field.hash]
    logger.info(f"[CampaignManager] Immagine caricata. Hash: {image_hash}")
    return image_hash


def _crea_campagna_meta(brief: dict) -> str:
    """
    Crea la campagna su Meta con obiettivo OUTCOME_LEADS.
    Rispetta il parametro _status_campagna dal brief.

    Returns:
        ID della campagna creata.
    """
    tipo_budget = brief.get("tipo_budget", "ABO").upper()
    status_richiesto = brief.get("_status_campagna", "PAUSED").upper()
    status_meta = Campaign.Status.active if status_richiesto == "ACTIVE" else Campaign.Status.paused

    params = {
        Campaign.Field.name: brief.get("nome_progetto", f"Campagna_{datetime.now().strftime('%Y%m%d')}"),
        Campaign.Field.objective: "OUTCOME_LEADS",
        Campaign.Field.status: status_meta,
        Campaign.Field.special_ad_categories: [],
    }

    # CBO: budget a livello campagna
    if tipo_budget == "CBO":
        params[Campaign.Field.daily_budget] = int(brief.get("budget_giornaliero", 50) * 100)  # in centesimi
        params[Campaign.Field.bid_strategy] = Campaign.BidStrategy.lowest_cost_without_cap

    campaign = Campaign(parent_id=settings.meta_ad_account_id)
    campaign.update(params)
    safe_meta_call(campaign.remote_create, params={"status": status_richiesto})

    campaign_id = campaign["id"]
    logger.info(f"[CampaignManager] Campagna creata. ID: {campaign_id} | Tipo: {tipo_budget} | Status: {status_richiesto}")
    return campaign_id


def _crea_ad_set(brief: dict, campaign_id: str, targeting_spec: dict) -> str:
    """
    Crea l'Ad Set con targeting, lingua e ottimizzazione per lead.

    Returns:
        ID dell'Ad Set creato.
    """
    tipo_budget = brief.get("tipo_budget", "ABO").upper()
    status_richiesto = brief.get("_status_campagna", "PAUSED").upper()
    status_meta = AdSet.Status.active if status_richiesto == "ACTIVE" else AdSet.Status.paused

    # Aggiungi lingua al targeting spec
    lingua = brief.get("lingua", "it")
    if lingua and "locales" not in targeting_spec:
        # Mappa codice lingua ISO -> ID locale Meta (principali)
        locale_map = {
            "it": 6,    # Italiano
            "en": 6,    # English (usa 6 come fallback, oppure ometti per tutti)
            "es": 8,    # Spagnolo
            "fr": 7,    # Francese
            "de": 5,    # Tedesco
            "pt": 9,    # Portoghese
        }
        locale_id = locale_map.get(lingua.lower())
        if locale_id:
            targeting_spec["locales"] = [locale_id]

    params = {
        AdSet.Field.name: f"AdSet_{brief.get('nome_progetto', 'default')}",
        AdSet.Field.campaign_id: campaign_id,
        AdSet.Field.status: status_meta,
        AdSet.Field.targeting: targeting_spec,
        AdSet.Field.optimization_goal: AdSet.OptimizationGoal.lead_generation,
        AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
        AdSet.Field.destination_type: "WEBSITE",
    }

    # ABO: budget a livello Ad Set
    if tipo_budget == "ABO":
        params[AdSet.Field.daily_budget] = int(brief.get("budget_giornaliero", 50) * 100)

    # Data di inizio
    data_inizio = brief.get("data_inizio")
    if data_inizio:
        from datetime import datetime as dt
        start_ts = int(dt.strptime(data_inizio, "%Y-%m-%d").timestamp())
        params[AdSet.Field.start_time] = start_ts

    # Data di fine (opzionale)
    data_fine = brief.get("data_fine")
    if data_fine:
        from datetime import datetime as dt
        end_ts = int(dt.strptime(data_fine, "%Y-%m-%d").timestamp())
        params[AdSet.Field.end_time] = end_ts

    ad_set = AdSet(parent_id=settings.meta_ad_account_id)
    ad_set.update(params)
    safe_meta_call(ad_set.remote_create)

    ad_set_id = ad_set["id"]
    logger.info(f"[CampaignManager] Ad Set creato. ID: {ad_set_id} | Lingua: {lingua.upper()}")
    return ad_set_id


def _crea_creative(brief: dict, copy: dict, image_hash: str) -> str:
    """
    Crea la Ad Creative assemblando immagine, copy e (opzionalmente) Instagram actor.

    Returns:
        ID della Ad Creative creata.
    """
    # Seleziona la prima headline come principale
    headline = copy["headline_varianti"][0]["testo"]

    # Struttura link_data base
    link_data = {
        "image_hash": image_hash,
        "link": brief.get("url_landing_page"),
        "message": copy.get("primary_text"),
        "name": headline,
        "description": copy.get("description", ""),
        "call_to_action": {
            "type": _mappa_cta(brief.get("cta_principale", "Scopri di piu'")),
            "value": {"link": brief.get("url_landing_page")}
        }
    }

    # Struttura object_story_spec con supporto Instagram
    instagram_actor_id = brief.get("_instagram_actor_id", "") or os.getenv("META_INSTAGRAM_ACTOR_ID", "")
    object_story_spec = {
        "page_id": settings.meta_page_id,
        "link_data": link_data
    }
    if instagram_actor_id:
        object_story_spec["instagram_actor_id"] = instagram_actor_id
        logger.info(f"[CampaignManager] Instagram actor abbinato: {instagram_actor_id}")

    creative_params = {
        AdCreative.Field.name: f"Creative_{brief.get('nome_progetto', 'default')}",
        AdCreative.Field.object_story_spec: object_story_spec,
        AdCreative.Field.degrees_of_freedom_spec: {
            "creative_features_spec": {
                "standard_enhancements": {"enroll_status": "OPT_OUT"}
            }
        }
    }

    creative = AdCreative(parent_id=settings.meta_ad_account_id)
    creative.update(creative_params)
    safe_meta_call(creative.remote_create)

    creative_id = creative["id"]
    logger.info(f"[CampaignManager] Ad Creative creata. ID: {creative_id}")
    return creative_id


def _crea_ad(brief: dict, ad_set_id: str, creative_id: str) -> str:
    """
    Crea l'inserzione finale.

    Returns:
        ID dell'Ad creato.
    """
    status_richiesto = brief.get("_status_campagna", "PAUSED").upper()
    status_meta = Ad.Status.active if status_richiesto == "ACTIVE" else Ad.Status.paused

    params = {
        Ad.Field.name: f"Ad_{brief.get('nome_progetto', 'default')}",
        Ad.Field.adset_id: ad_set_id,
        Ad.Field.creative: {"creative_id": creative_id},
        Ad.Field.status: status_meta,
        Ad.Field.tracking_specs: [{
            "action.type": ["offsite_conversion"],
            "fb_pixel": [settings.meta_pixel_id]
        }] if settings.meta_pixel_id else []
    }

    ad = Ad(parent_id=settings.meta_ad_account_id)
    ad.update(params)
    safe_meta_call(ad.remote_create)

    ad_id = ad["id"]
    logger.info(f"[CampaignManager] Ad creato. ID: {ad_id} | Status: {status_richiesto}")
    return ad_id


def _mappa_cta(cta_testo: str) -> str:
    """Mappa il testo CTA al tipo Meta API."""
    mapping = {
        "scopri di piu'": "LEARN_MORE",
        "scopri di più": "LEARN_MORE",
        "scopri il corso": "LEARN_MORE",
        "iscriviti": "SUBSCRIBE",
        "registrati": "SIGN_UP",
        "contattaci": "CONTACT_US",
        "richiedi info": "GET_QUOTE",
        "prenota": "BOOK_TRAVEL",
        "scarica": "DOWNLOAD",
        "acquista": "SHOP_NOW",
    }
    return mapping.get(cta_testo.lower(), "LEARN_MORE")


def crea_campagna(brief: dict, targeting: dict, copy: dict, asset: dict) -> str:
    """
    Crea la struttura completa della campagna su Meta.

    Args:
        brief   : Dati della campagna (include _status_campagna, lingua, _instagram_actor_id).
        targeting: Output dell'Agente Targeting.
        copy    : Output dell'Agente Copywriter.
        asset   : Output dell'Agente Grafico (con percorso immagine).

    Returns:
        ID della campagna Meta creata.
    """
    logger.info("[CampaignManager] Avvio creazione campagna su Meta...")
    init_meta_api()

    status_richiesto = brief.get("_status_campagna", "PAUSED").upper()
    lingua = brief.get("lingua", "it").upper()
    logger.info(f"[CampaignManager] Status richiesto: {status_richiesto} | Lingua: {lingua}")

    # 1. Carica immagine
    percorso_immagine = asset.get("percorso_immagine")
    if not percorso_immagine or not os.path.exists(percorso_immagine):
        raise FileNotFoundError(
            f"[CampaignManager] Immagine non trovata: {percorso_immagine}. "
            "Assicurati che l'Agente Grafico abbia completato la generazione."
        )
    image_hash = _carica_immagine(percorso_immagine)

    # 2. Crea Campagna
    campaign_id = _crea_campagna_meta(brief)

    # 3. Crea Ad Set (con lingua nel targeting)
    targeting_spec = targeting.get("targeting_spec", {})
    ad_set_id = _crea_ad_set(brief, campaign_id, targeting_spec)

    # 4. Crea Creative (con Instagram actor se disponibile)
    creative_id = _crea_creative(brief, copy, image_hash)

    # 5. Crea Ad
    ad_id = _crea_ad(brief, ad_set_id, creative_id)

    # 6. Salva riepilogo locale
    riepilogo = {
        "campaign_id": campaign_id,
        "ad_set_id": ad_set_id,
        "creative_id": creative_id,
        "ad_id": ad_id,
        "status": status_richiesto,
        "lingua": lingua,
        "instagram_abbinato": bool(brief.get("_instagram_actor_id") or os.getenv("META_INSTAGRAM_ACTOR_ID")),
        "nota": "Campagna in pausa. Attivare manualmente dopo revisione." if status_richiesto == "PAUSED" else "Campagna attiva.",
        "creato_il": datetime.now().isoformat()
    }

    output_dir = asset.get("output_dir", "data/output")
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/campagna_meta.json", "w") as f:
        json.dump(riepilogo, f, indent=2, ensure_ascii=False)

    logger.info(f"[CampaignManager] Campagna completa. ID: {campaign_id} | Status: {status_richiesto} | Lingua: {lingua}")
    if status_richiesto == "PAUSED":
        logger.info("[CampaignManager] La campagna e' in PAUSA. Attivala manualmente da Meta Ads Manager dopo la revisione.")

    return campaign_id
