"""
agents/analista.py
Agente Analista KPI — monitora le performance delle campagne Meta attive.

Funzionalità:
- Recupera Insights da Meta Marketing API (CPC, CPM, CTR, CPA, Lead, Spesa)
- Analizza i dati con GPT-4 per identificare problemi e opportunità
- Genera report sintetici in italiano
- Invia alert automatici se i KPI scendono sotto soglia
- Salva i dati storici su Baserow per trend analysis

KPI monitorati:
- CPL (Costo per Lead) — metrica principale
- CTR (Click-Through Rate) — qualità del copy/creativa
- CPC (Costo per Click) — efficienza della spesa
- Frequenza — rischio di ad fatigue
- ROAS (se pixel configurato)

Soglie di alert (configurabili nel brief):
- CPL > soglia_cpl → alert "Costo lead troppo alto"
- CTR < 0.5% → alert "Copy o creativa da rivedere"
- Frequenza > 3.0 → alert "Ad fatigue: ruota le creatività"
"""

import json
from datetime import datetime, timedelta
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adaccount import AdAccount
from utils.meta_api_client import init_meta_api, safe_meta_call
from utils.openrouter_client import chat
from utils.notifier import notify
from utils.gsheets_client import salva_kpi
from utils.logger import get_logger
from config.settings import settings

logger = get_logger("agente_analista")

# Soglie di alert di default
SOGLIE_DEFAULT = {
    "cpl_max": 20.0,       # CPL massimo accettabile in EUR
    "ctr_min": 0.5,        # CTR minimo in %
    "frequenza_max": 3.0,  # Frequenza massima prima di ad fatigue
    "cpc_max": 2.0         # CPC massimo in EUR
}

SYSTEM_PROMPT_ANALISI = """Sei un esperto di performance marketing Meta Ads.

Analizza i dati KPI forniti e produci:
1. Una valutazione sintetica delle performance (2-3 frasi)
2. I 2-3 problemi principali identificati (se presenti)
3. Le azioni correttive consigliate (specifiche e operative)
4. Un giudizio complessivo: OTTIMO / BUONO / DA OTTIMIZZARE / CRITICO

REGOLE:
- Sii diretto e operativo, no linguaggio vago
- Ogni raccomandazione deve essere un'azione concreta
- Confronta sempre i KPI con i benchmark del settore
- Tieni conto del budget giornaliero nella valutazione

OUTPUT RICHIESTO (JSON puro):
{
  "valutazione": "...",
  "problemi": ["...", "..."],
  "azioni_correttive": ["...", "..."],
  "giudizio": "BUONO",
  "priorita_intervento": "ALTA | MEDIA | BASSA"
}
"""


def _recupera_insights(campaign_id: str, giorni: int = 7) -> dict:
    """
    Recupera i dati di performance dalla Meta Marketing API.

    Args:
        campaign_id: ID della campagna Meta.
        giorni: Numero di giorni da analizzare (default: ultimi 7 giorni).

    Returns:
        Dizionario con i KPI aggregati.
    """
    init_meta_api()

    data_fine = datetime.now().strftime("%Y-%m-%d")
    data_inizio = (datetime.now() - timedelta(days=giorni)).strftime("%Y-%m-%d")

    params = {
        "fields": [
            "campaign_name",
            "spend",
            "impressions",
            "clicks",
            "ctr",
            "cpc",
            "cpm",
            "frequency",
            "actions",
            "cost_per_action_type",
            "reach"
        ],
        "time_range": {
            "since": data_inizio,
            "until": data_fine
        },
        "level": "campaign"
    }

    try:
        campaign = Campaign(campaign_id)
        insights = safe_meta_call(campaign.get_insights, params=params)

        if not insights or len(insights) == 0:
            logger.warning(f"[Analista] Nessun dato per campagna {campaign_id} negli ultimi {giorni} giorni.")
            return {}

        dati = insights[0]

        # Estrai lead dalle actions
        lead_count = 0
        cpl = 0.0
        actions = dati.get("actions", [])
        cost_per_action = dati.get("cost_per_action_type", [])

        for action in actions:
            if action.get("action_type") in ["lead", "onsite_conversion.lead_grouped"]:
                lead_count = int(action.get("value", 0))

        for cpa in cost_per_action:
            if cpa.get("action_type") in ["lead", "onsite_conversion.lead_grouped"]:
                cpl = float(cpa.get("value", 0))

        spesa = float(dati.get("spend", 0))
        impressioni = int(dati.get("impressions", 0))
        click = int(dati.get("clicks", 0))
        ctr = float(dati.get("ctr", 0))
        cpc = float(dati.get("cpc", 0))
        cpm = float(dati.get("cpm", 0))
        frequenza = float(dati.get("frequency", 0))
        reach = int(dati.get("reach", 0))

        kpi = {
            "campaign_id": campaign_id,
            "campaign_name": dati.get("campaign_name", ""),
            "periodo": f"{data_inizio} → {data_fine}",
            "spesa_eur": round(spesa, 2),
            "impressioni": impressioni,
            "reach": reach,
            "click": click,
            "ctr_pct": round(ctr, 2),
            "cpc_eur": round(cpc, 2),
            "cpm_eur": round(cpm, 2),
            "frequenza": round(frequenza, 2),
            "lead": lead_count,
            "cpl_eur": round(cpl, 2)
        }

        logger.info(f"[Analista] KPI recuperati: {lead_count} lead | CPL €{cpl:.2f} | CTR {ctr:.2f}%")
        return kpi

    except Exception as e:
        logger.error(f"[Analista] Errore recupero insights: {e}")
        raise


def _verifica_soglie(kpi: dict, soglie: dict) -> list:
    """
    Verifica se i KPI superano le soglie di alert.

    Returns:
        Lista di alert attivi.
    """
    alert = []

    if kpi.get("cpl_eur", 0) > soglie.get("cpl_max", 20) and kpi.get("lead", 0) > 0:
        alert.append(f"⚠️ CPL €{kpi['cpl_eur']:.2f} supera la soglia di €{soglie['cpl_max']:.2f}")

    if kpi.get("ctr_pct", 0) < soglie.get("ctr_min", 0.5) and kpi.get("impressioni", 0) > 1000:
        alert.append(f"⚠️ CTR {kpi['ctr_pct']:.2f}% sotto la soglia minima del {soglie['ctr_min']}%")

    if kpi.get("frequenza", 0) > soglie.get("frequenza_max", 3.0):
        alert.append(f"⚠️ Frequenza {kpi['frequenza']:.1f} — rischio ad fatigue (soglia: {soglie['frequenza_max']})")

    if kpi.get("cpc_eur", 0) > soglie.get("cpc_max", 2.0) and kpi.get("click", 0) > 10:
        alert.append(f"⚠️ CPC €{kpi['cpc_eur']:.2f} supera la soglia di €{soglie['cpc_max']:.2f}")

    return alert


def _analizza_con_gpt(kpi: dict) -> dict:
    """
    Usa GPT-4 per analizzare i KPI e generare raccomandazioni.

    Returns:
        Dizionario con valutazione, problemi, azioni e giudizio.
    """
    user_prompt = f"""Analizza questi KPI di una campagna Meta Lead Ads (ultimi 7 giorni):

Campagna: {kpi.get('campaign_name', 'N/A')}
Periodo: {kpi.get('periodo', 'N/A')}
Spesa: €{kpi.get('spesa_eur', 0):.2f}
Impressioni: {kpi.get('impressioni', 0):,}
Reach: {kpi.get('reach', 0):,}
Click: {kpi.get('click', 0):,}
CTR: {kpi.get('ctr_pct', 0):.2f}%
CPC: €{kpi.get('cpc_eur', 0):.2f}
CPM: €{kpi.get('cpm_eur', 0):.2f}
Frequenza: {kpi.get('frequenza', 0):.2f}
Lead generati: {kpi.get('lead', 0)}
CPL (Costo per Lead): €{kpi.get('cpl_eur', 0):.2f}

Benchmark settore marketing automation B2B Italia:
- CPL target: €5-15
- CTR buono: >1%
- Frequenza ottimale: 1.5-2.5

Restituisci SOLO il JSON richiesto."""

    try:
        raw = chat(
            system_prompt=SYSTEM_PROMPT_ANALISI,
            user_prompt=user_prompt,
            temperature=0.3
        )
        raw = raw.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[Analista] Errore analisi GPT-4: {e}")
        return {
            "valutazione": "Analisi non disponibile.",
            "problemi": [],
            "azioni_correttive": [],
            "giudizio": "N/A",
            "priorita_intervento": "N/A"
        }


def analizza_campagna(campaign_id: str, giorni: int = 7, soglie: dict = None) -> dict:
    """
    Analizza i KPI di una campagna Meta attiva.

    Args:
        campaign_id: ID della campagna Meta da analizzare.
        giorni: Numero di giorni da analizzare.
        soglie: Soglie personalizzate per gli alert (opzionale).

    Returns:
        Report completo con KPI, analisi GPT e alert.
    """
    logger.info(f"[Analista] Avvio analisi campagna {campaign_id} (ultimi {giorni} giorni)...")
    soglie = soglie or SOGLIE_DEFAULT

    # 1. Recupera KPI da Meta
    kpi = _recupera_insights(campaign_id, giorni)
    if not kpi:
        return {"errore": "Nessun dato disponibile per questa campagna nel periodo selezionato."}

    # 2. Verifica soglie e genera alert
    alert_attivi = _verifica_soglie(kpi, soglie)

    # 3. Analisi GPT-4
    analisi = _analizza_con_gpt(kpi)

    # 4. Salva KPI su Baserow
    salva_kpi({
        "ID Campagna Meta": campaign_id,
        "Nome Campagna": kpi.get("campaign_name"),
        "Periodo": kpi.get("periodo"),
        "Spesa EUR": kpi.get("spesa_eur"),
        "Lead": kpi.get("lead"),
        "CPL EUR": kpi.get("cpl_eur"),
        "CTR": kpi.get("ctr_pct"),
        "CPC EUR": kpi.get("cpc_eur"),
        "Frequenza": kpi.get("frequenza"),
        "Giudizio": analisi.get("giudizio"),
        "Data Analisi": datetime.now().strftime("%Y-%m-%d")
    })

    # 5. Invia notifica se ci sono alert
    if alert_attivi:
        messaggio_alert = (
            f"🚨 *Alert KPI — {kpi.get('campaign_name')}*\n\n"
            + "\n".join(alert_attivi)
            + f"\n\n📊 Giudizio: *{analisi.get('giudizio')}*"
            + f"\n🎯 Priorità: {analisi.get('priorita_intervento')}"
        )
        notify(messaggio_alert, event="alert_kpi", data={
            "campaign_id": campaign_id,
            "alert": alert_attivi,
            "kpi": kpi
        })

    # 6. Costruisci report finale
    report = {
        "campaign_id": campaign_id,
        "kpi": kpi,
        "alert": alert_attivi,
        "analisi_gpt": analisi,
        "generato_il": datetime.now().isoformat()
    }

    logger.info(f"[Analista] Report completato. Giudizio: {analisi.get('giudizio')} | Alert: {len(alert_attivi)}")
    return report


def stampa_report(report: dict):
    """Stampa il report in formato leggibile nel terminale."""
    kpi = report.get("kpi", {})
    analisi = report.get("analisi_gpt", {})
    alert = report.get("alert", [])

    print("\n" + "=" * 60)
    print(f"📊 REPORT KPI — {kpi.get('campaign_name', 'N/A')}")
    print(f"📅 Periodo: {kpi.get('periodo', 'N/A')}")
    print("=" * 60)
    print(f"💰 Spesa:        €{kpi.get('spesa_eur', 0):.2f}")
    print(f"👥 Reach:        {kpi.get('reach', 0):,}")
    print(f"🖱️  Click:        {kpi.get('click', 0):,}")
    print(f"📈 CTR:          {kpi.get('ctr_pct', 0):.2f}%")
    print(f"💵 CPC:          €{kpi.get('cpc_eur', 0):.2f}")
    print(f"🔁 Frequenza:    {kpi.get('frequenza', 0):.2f}")
    print(f"🎯 Lead:         {kpi.get('lead', 0)}")
    print(f"📌 CPL:          €{kpi.get('cpl_eur', 0):.2f}")
    print("-" * 60)
    print(f"🏆 Giudizio:     {analisi.get('giudizio', 'N/A')}")
    print(f"⚡ Priorità:     {analisi.get('priorita_intervento', 'N/A')}")
    print(f"\n💬 Valutazione:\n{analisi.get('valutazione', '')}")

    if analisi.get("azioni_correttive"):
        print("\n🔧 Azioni consigliate:")
        for i, azione in enumerate(analisi["azioni_correttive"], 1):
            print(f"  {i}. {azione}")

    if alert:
        print("\n🚨 Alert attivi:")
        for a in alert:
            print(f"  {a}")

    print("=" * 60 + "\n")
