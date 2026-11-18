from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from validador.api import DoeApiClient, EditionRecord
from validador.catalogo import (
    CADERNOS,
    STATUS_NAO_PROCESSADO,
    STATUS_PRONTO,
    STATUS_SEM_MATERIAS,
    edition_api_name,
    normalize_key,
)
from validador.sumario import SumarioClient


@dataclass
class ItemResultado:
    caderno: str
    secao: str
    tipo: str
    status: str
    publicacoes: int | None = None
    codigo_autenticidade: str | None = None
    detalhe: str | None = None


@dataclass
class ResultadoValidacao:
    data_referencia: date
    ignorado: bool = False
    motivo_ignorado: str | None = None
    sucesso: bool = True
    itens: list[ItemResultado] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def possui_falha(self) -> bool:
        return not self.ignorado and not self.sucesso


def validar_doe(
    client: DoeApiClient,
    data_referencia: date,
    *,
    ignorar_fim_de_semana: bool = True,
) -> ResultadoValidacao:
    resultado = ResultadoValidacao(data_referencia=data_referencia)

    if ignorar_fim_de_semana and data_referencia.weekday() >= 5:
        resultado.ignorado = True
        resultado.motivo_ignorado = "Fim de semana — validação não aplicável."
        return resultado

    edition_date = data_referencia.isoformat()
    status_code, regulares = client.fetch_editions_status(edition_date)
    if status_code == 404:
        resultado.ignorado = True
        resultado.motivo_ignorado = "Não há edição publicada para esta data."
        return resultado
    if status_code != 200:
        resultado.sucesso = False
        if status_code == 599:
            resultado.falhas.append(
                "Falha de rede/timeout ao consultar edições regulares da API do DOE."
            )
        else:
            resultado.falhas.append(
                f"Falha ao consultar edições regulares (HTTP {status_code})."
            )
        return resultado

    _validar_regulares(resultado, regulares)

    sup_code, suplementos = client.fetch_supplementary_status(edition_date)
    if sup_code == 404:
        resultado.avisos.append("Nenhum suplemento encontrado para esta data.")
    elif sup_code != 200:
        resultado.sucesso = False
        resultado.falhas.append(
            f"Falha ao consultar suplementos (HTTP {sup_code})."
        )
    else:
        _validar_suplementos(resultado, suplementos)

    resultado.sucesso = len(resultado.falhas) == 0
    return resultado


def _validar_regulares(
    resultado: ResultadoValidacao,
    registros: list[EditionRecord],
) -> None:
    por_nome = _indexar_por_nome(registros)
    sumario = SumarioClient()
    mapa_secoes = sumario.carregar_mapa_secoes(resultado.data_referencia)

    for caderno in CADERNOS:
        for secao in caderno.secoes:
            api_name = edition_api_name(caderno.nome, secao.api_suffix)
            registro = por_nome.get(normalize_key(api_name))

            if registro is None:
                if sumario.secao_sem_materias(
                    caderno.nome,
                    secao.nome,
                    resultado.data_referencia,
                    mapa_secoes,
                ):
                    resultado.itens.append(
                        ItemResultado(
                            caderno=caderno.nome,
                            secao=secao.nome,
                            tipo="Regular",
                            status=STATUS_SEM_MATERIAS,
                            publicacoes=0,
                            detalhe=(
                                "Não existem matérias para esta data "
                                f"({resultado.data_referencia.strftime('%d/%m/%Y')})."
                            ),
                        )
                    )
                    continue

                resultado.sucesso = False
                resultado.falhas.append(
                    f"[Regular] {caderno.nome} > {secao.nome}: não publicado."
                )
                resultado.itens.append(
                    ItemResultado(
                        caderno=caderno.nome,
                        secao=secao.nome,
                        tipo="Regular",
                        status="Ausente",
                        detalhe="Seção não encontrada na API.",
                    )
                )
                continue

            ok = registro.status == STATUS_PRONTO
            if not ok:
                resultado.sucesso = False
                resultado.falhas.append(
                    f"[Regular] {caderno.nome} > {secao.nome}: status '{registro.status}'."
                )

            resultado.itens.append(
                ItemResultado(
                    caderno=caderno.nome,
                    secao=secao.nome,
                    tipo="Regular",
                    status=registro.status,
                    publicacoes=registro.publications,
                    codigo_autenticidade=registro.edition_auth_code,
                    detalhe=None if ok else "Seção regular não está pronta.",
                )
            )


def _validar_suplementos(
    resultado: ResultadoValidacao,
    registros: list[EditionRecord],
) -> None:
    relevantes = [
        registro
        for registro in registros
        if not (
            registro.status == STATUS_NAO_PROCESSADO and registro.publications == 0
        )
    ]

    if not relevantes:
        resultado.avisos.append("Suplementos listados, porém nenhum item ativo.")
        return

    for registro in relevantes:
        caderno, secao = _resolver_caderno_secao(registro.edition_name)
        ok = registro.status == STATUS_PRONTO
        if not ok:
            resultado.sucesso = False
            resultado.falhas.append(
                f"[Suplemento] {caderno} > {secao}: status '{registro.status}'."
            )

        resultado.itens.append(
            ItemResultado(
                caderno=caderno,
                secao=secao,
                tipo="Suplemento",
                status=registro.status,
                publicacoes=registro.publications,
                codigo_autenticidade=registro.edition_auth_code,
                detalhe=None if ok else "Suplemento não está pronto.",
            )
        )


def _indexar_por_nome(registros: list[EditionRecord]) -> dict[str, EditionRecord]:
    indice: dict[str, EditionRecord] = {}
    for registro in registros:
        indice[normalize_key(registro.edition_name)] = registro
    return indice


def _resolver_caderno_secao(edition_name: str) -> tuple[str, str]:
    for caderno in CADERNOS:
        for secao in caderno.secoes:
            api_name = edition_api_name(caderno.nome, secao.api_suffix)
            if normalize_key(api_name) == normalize_key(edition_name):
                return caderno.nome, secao.nome

    if "_" in edition_name:
        caderno, secao = edition_name.split("_", 1)
        return caderno, secao.replace("_", " ")

    return "Desconhecido", edition_name
