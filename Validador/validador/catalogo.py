from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Secao:
    nome: str
    api_suffix: str


@dataclass(frozen=True)
class Caderno:
    nome: str
    secoes: tuple[Secao, ...]


CADERNOS: tuple[Caderno, ...] = (
    Caderno(
        "Executivo",
        (
            Secao("Atos Normativos", "Atos_Normativos"),
            Secao("Atos de Pessoal", "Atos_de_Pessoal"),
            Secao("Atos de Gestão e Despesas", "Atos_de_Gestão_e_Despesas"),
        ),
    ),
    Caderno(
        "Legislativo",
        (
            Secao(
                "Atos Legislativos e Parlamentares da Assembleia",
                "Atos_Legislativos_e_Parlamentares_da_Assembleia",
            ),
            Secao(
                "Atos Administrativos da Assembleia",
                "Atos_Administrativos_da_Assembleia",
            ),
        ),
    ),
    Caderno("Municípios", (Secao("Atos Municipais", "Atos_Municipais"),)),
    Caderno(
        "Empresarial",
        (
            Secao("Atos Empresariais", "Atos_Empresariais"),
            Secao("Atos da Jucesp", "Atos_da_Jucesp"),
        ),
    ),
)

STATUS_PRONTO = "Pronto"
STATUS_NAO_PROCESSADO = "Não Processado"
STATUS_SEM_MATERIAS = "Sem matérias"


def edition_api_name(caderno: str, secao_suffix: str) -> str:
    return f"{caderno}_{secao_suffix}"


def expected_regular_editions() -> list[str]:
    names: list[str] = []
    for caderno in CADERNOS:
        for secao in caderno.secoes:
            names.append(edition_api_name(caderno.nome, secao.api_suffix))
    return names


def normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return without_accents.lower().replace(" ", "_")
