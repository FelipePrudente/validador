from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from validador.api import DoeApiClient
from validador.mailer import enviar_email
from validador.report import render_console, render_email_html, render_teams_card
from validador.teams import enviar_teams
from validador.validator import validar_doe

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
CONFIG_EXAMPLE_PATH = ROOT / "config.example.json"


def carregar_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    if CONFIG_EXAMPLE_PATH.exists():
        return json.loads(CONFIG_EXAMPLE_PATH.read_text(encoding="utf-8"))

    raise FileNotFoundError(
        "Arquivo config.json não encontrado. Copie config.example.json para config.json."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida publicação dos cadernos e seções do DOE-SP."
    )
    parser.add_argument(
        "--data",
        help="Data no formato AAAA-MM-DD (padrão: hoje).",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Executa mesmo em fim de semana.",
    )
    parser.add_argument(
        "--sem-alerta",
        action="store_true",
        help="Não envia alertas externos, apenas exibe o relatório.",
    )
    return parser.parse_args()


def enviar_alertas(
    config: dict,
    resultado,
    data_referencia: date,
    sumario_url: str,
    relatorio: str,
) -> list[str]:
    erros: list[str] = []
    data_fmt = data_referencia.strftime("%d/%m/%Y")
    if resultado.sucesso:
        assunto = f"[DOE-SP] Validação OK — {data_fmt}"
    else:
        assunto = f"[DOE-SP] Falha na validação — {data_fmt}"

    teams_cfg = config.get("teams", {})
    if teams_cfg.get("enabled"):
        try:
            enviar_teams(teams_cfg, render_teams_card(resultado, sumario_url))
            if resultado.sucesso:
                print("\nAviso de sucesso enviado para o Teams.")
            else:
                print("\nAlerta de falha enviado para o Teams.")
        except Exception as error:
            erros.append(f"Teams: {error}")

    email_cfg = config.get("email", {})
    if email_cfg.get("enabled"):
        try:
            enviar_email(
                email_cfg,
                assunto=assunto,
                corpo_texto=relatorio,
                corpo_html=render_email_html(resultado, sumario_url),
            )
            print("\nE-mail de alerta enviado com sucesso.")
        except Exception as error:
            erros.append(f"E-mail: {error}")

    return erros


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = parse_args()
    config = carregar_config()

    data_referencia = (
        date.fromisoformat(args.data) if args.data else date.today()
    )

    client = DoeApiClient(config.get("api_base_url", "https://do-api-publication-pdf.doe.sp.gov.br"))
    resultado = validar_doe(
        client,
        data_referencia,
        ignorar_fim_de_semana=not args.forcar,
    )

    sumario_url = config.get("sumario_url", "https://doe.sp.gov.br/sumario")
    relatorio = render_console(resultado, sumario_url)
    print(relatorio)

    if resultado.ignorado:
        return 0

    teams_cfg = config.get("teams", {})
    deve_alertar = (
        (resultado.sucesso and teams_cfg.get("alertar_em_sucesso", True))
        or (resultado.possui_falha and teams_cfg.get("alertar_em_falha", True))
        or config.get("email", {}).get("enabled", False)
    )

    if not args.sem_alerta and deve_alertar:
        erros_alerta = enviar_alertas(
            config,
            resultado,
            data_referencia,
            sumario_url,
            relatorio,
        )
        if erros_alerta:
            for erro in erros_alerta:
                print(f"\nNão foi possível enviar alerta ({erro})", file=sys.stderr)
            return 2

    return 1 if resultado.possui_falha else 0


if __name__ == "__main__":
    raise SystemExit(main())
