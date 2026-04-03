"""
agents/orchestrator.py
Orchestratore centrale del sistema META Lead ADS Assistant.

Coordina la pipeline completa:
1. Targeting (analisi audience)
2. Copywriter + Grafico (in parallelo tramite threading)
3. Campaign Manager (assembla e pubblica su Meta)
4. Notifiche (Telegram / WhatsApp / Make / n8n)
5. Salvataggio su Baserow CRM

Gestisce lo stato della pipeline, il logging e la gestione degli errori.
"""

import json
import os
import threading
from datetime import datetime
from utils.logger import get_logger
from utils.notifier import notify
from utils.gsheets_client import salva_campagna

logger = get_logger("orchestrator")


class PipelineState:
    """Mantiene lo stato della pipeline durante l'esecuzione."""
    def __init__(self, brief: dict):
        self.brief = brief
        self.targeting = None
        self.copy = None
        self.asset_grafico = None
        self.campagna_id = None
        self.errori = []
        self.start_time = datetime.now()

    def ha_errori(self) -> bool:
        return len(self.errori) > 0

    def aggiungi_errore(self, agente: str, errore: str):
        self.errori.append({"agente": agente, "errore": errore, "timestamp": datetime.now().isoformat()})
        logger.error(f"[Orchestratore] Errore in {agente}: {errore}")

    def durata(self) -> str:
        delta = datetime.now() - self.start_time
        return f"{delta.seconds}s"


def _esegui_targeting(state: PipelineState):
    """Step 1: Definisce il targeting."""
    try:
        from agents.targeting import definisci_target
        logger.info("[Orchestratore] → Agente Targeting avviato")
        state.targeting = definisci_target(state.brief)
        logger.info("[Orchestratore] ✓ Targeting completato")
    except Exception as e:
        state.aggiungi_errore("targeting", str(e))


def _esegui_copywriter(state: PipelineState):
    """Step 2a (parallelo): Genera il copy."""
    try:
        from agents.copywriter import genera_copy
        logger.info("[Orchestratore] → Agente Copywriter avviato")
        state.copy = genera_copy(state.brief)
        logger.info("[Orchestratore] ✓ Copy completato")
    except Exception as e:
        state.aggiungi_errore("copywriter", str(e))


def _esegui_grafico(state: PipelineState):
    """Step 2b (parallelo): Genera l'asset grafico."""
    try:
        from agents.grafico import genera_asset
        logger.info("[Orchestratore] → Agente Grafico avviato")
        state.asset_grafico = genera_asset(state.brief)
        logger.info("[Orchestratore] ✓ Asset grafico completato")
    except Exception as e:
        state.aggiungi_errore("grafico", str(e))


def _esegui_campaign_manager(state: PipelineState):
    """Step 3: Crea la campagna su Meta."""
    try:
        from agents.campaign_manager import crea_campagna
        logger.info("[Orchestratore] → Agente Campaign Manager avviato")
        state.campagna_id = crea_campagna(
            brief=state.brief,
            targeting=state.targeting,
            copy=state.copy,
            asset=state.asset_grafico
        )
        logger.info(f"[Orchestratore] ✓ Campagna creata. ID Meta: {state.campagna_id}")
    except Exception as e:
        state.aggiungi_errore("campaign_manager", str(e))


def esegui_pipeline(brief: dict) -> dict:
    """
    Esegue la pipeline completa di creazione campagna.

    Args:
        brief: Dizionario con i dati della campagna (da brief.json).

    Returns:
        Dizionario con risultati della pipeline (campagna_id, errori, durata).
    """
    logger.info("=" * 60)
    logger.info(f"[Orchestratore] Avvio pipeline: {brief.get('nome_progetto', 'N/A')}")
    logger.info("=" * 60)

    state = PipelineState(brief)

    # ── STEP 1: Targeting (sequenziale — gli altri agenti dipendono da questo) ──
    _esegui_targeting(state)
    if state.ha_errori():
        logger.error("[Orchestratore] Targeting fallito. Pipeline interrotta.")
        notify(
            f"❌ *Pipeline interrotta*\nProgetto: {brief.get('nome_progetto')}\nErrore: Targeting fallito",
            event="generico"
        )
        return _build_report(state)

    # ── STEP 2: Copywriter + Grafico in parallelo ──
    logger.info("[Orchestratore] Avvio Copywriter e Grafico in parallelo...")
    t_copy = threading.Thread(target=_esegui_copywriter, args=(state,))
    t_grafico = threading.Thread(target=_esegui_grafico, args=(state,))
    t_copy.start()
    t_grafico.start()
    t_copy.join()
    t_grafico.join()

    if state.ha_errori():
        logger.error("[Orchestratore] Errori in fase creativa. Pipeline interrotta.")
        notify(
            f"❌ *Errore fase creativa*\nProgetto: {brief.get('nome_progetto')}\nErrori: {state.errori}",
            event="generico"
        )
        return _build_report(state)

    # ── STEP 3: Campaign Manager ──
    _esegui_campaign_manager(state)
    if state.ha_errori():
        logger.error("[Orchestratore] Campaign Manager fallito.")
        notify(
            f"❌ *Errore Campaign Manager*\nProgetto: {brief.get('nome_progetto')}",
            event="generico"
        )
        return _build_report(state)

    # ── STEP 4: Salvataggio su Baserow ──
    salva_campagna({
        "Nome Progetto": brief.get("nome_progetto"),
        "ID Campagna Meta": state.campagna_id,
        "Budget Giornaliero": brief.get("budget_giornaliero"),
        "Tipo Budget": brief.get("tipo_budget"),
        "URL Landing Page": brief.get("url_landing_page"),
        "Data Creazione": datetime.now().strftime("%Y-%m-%d"),
        "Status": {"value": "Attiva"}
    })

    # ── STEP 5: Notifica successo ──
    messaggio = (
        f"✅ *Campagna creata con successo!*\n"
        f"📌 Progetto: {brief.get('nome_progetto')}\n"
        f"🆔 ID Meta: {state.campagna_id}\n"
        f"💰 Budget: €{brief.get('budget_giornaliero')}/giorno ({brief.get('tipo_budget')})\n"
        f"⏱ Durata pipeline: {state.durata()}"
    )
    notify(messaggio, event="campagna_creata", data={
        "campagna_id": state.campagna_id,
        "progetto": brief.get("nome_progetto"),
        "budget": brief.get("budget_giornaliero")
    })

    logger.info(f"[Orchestratore] Pipeline completata in {state.durata()}.")
    return _build_report(state)


def _build_report(state: PipelineState) -> dict:
    """Costruisce il report finale della pipeline."""
    return {
        "successo": not state.ha_errori(),
        "campagna_id": state.campagna_id,
        "durata": state.durata(),
        "errori": state.errori,
        "targeting": state.targeting,
        "copy": state.copy,
        "asset_grafico": state.asset_grafico
    }
