"""
main.py
Entry point del sistema META Lead ADS Assistant.

Utilizzo:
  # Crea campagna da brief.json
  python main.py crea

  # Crea campagna da file custom
  python main.py crea --brief data/mio_brief.json

  # Analizza KPI di una campagna attiva
  python main.py analizza --id CAMPAIGN_ID_META

  # Analizza KPI degli ultimi 14 giorni
  python main.py analizza --id CAMPAIGN_ID_META --giorni 14
"""

import sys
import json
import argparse
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("main")


def carica_brief(percorso: str) -> dict:
    """Carica e valida il file brief JSON."""
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            brief = json.load(f)
        logger.info(f"[Main] Brief caricato: {brief.get('nome_progetto', 'N/A')}")
        return brief
    except FileNotFoundError:
        logger.error(f"[Main] File brief non trovato: {percorso}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"[Main] Errore parsing brief JSON: {e}")
        sys.exit(1)


def cmd_crea(args):
    """Comando: crea una nuova campagna."""
    from agents.orchestrator import esegui_pipeline

    brief = carica_brief(args.brief)

    print("\n" + "=" * 60)
    print("🚀 META Lead ADS Assistant — Creazione Campagna")
    print(f"📌 Progetto: {brief.get('nome_progetto')}")
    print(f"💰 Budget: €{brief.get('budget_giornaliero')}/giorno ({brief.get('tipo_budget')})")
    print(f"🎯 Obiettivo: Lead Generation su {brief.get('url_landing_page')}")
    print("=" * 60 + "\n")

    report = esegui_pipeline(brief)

    if report.get("successo"):
        print(f"\n✅ Campagna creata con successo!")
        print(f"   ID Meta: {report.get('campagna_id')}")
        print(f"   Status: PAUSED (attiva manualmente da Ads Manager)")
        print(f"   Durata pipeline: {report.get('durata')}")
    else:
        print(f"\n❌ Pipeline completata con errori:")
        for errore in report.get("errori", []):
            print(f"   [{errore['agente']}] {errore['errore']}")


def cmd_analizza(args):
    """Comando: analizza i KPI di una campagna."""
    from agents.analista import analizza_campagna, stampa_report

    print(f"\n📊 Analisi KPI — Campagna {args.id} (ultimi {args.giorni} giorni)\n")
    report = analizza_campagna(
        campaign_id=args.id,
        giorni=args.giorni
    )
    stampa_report(report)


def main():
    parser = argparse.ArgumentParser(
        description="META Lead ADS Assistant — Orchestratore campagne Meta Ads"
    )
    subparsers = parser.add_subparsers(dest="comando")

    # Comando: crea
    parser_crea = subparsers.add_parser("crea", help="Crea una nuova campagna Meta Lead Ads")
    parser_crea.add_argument(
        "--brief",
        default="data/brief.json",
        help="Percorso del file brief JSON (default: data/brief.json)"
    )

    # Comando: analizza
    parser_analizza = subparsers.add_parser("analizza", help="Analizza i KPI di una campagna attiva")
    parser_analizza.add_argument("--id", required=True, help="ID della campagna Meta da analizzare")
    parser_analizza.add_argument("--giorni", type=int, default=7, help="Numero di giorni da analizzare (default: 7)")

    args = parser.parse_args()

    # Validazione variabili d'ambiente
    try:
        settings.validate_required()
    except EnvironmentError as e:
        print(f"\n{e}\n")
        sys.exit(1)

    if args.comando == "crea":
        cmd_crea(args)
    elif args.comando == "analizza":
        cmd_analizza(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
