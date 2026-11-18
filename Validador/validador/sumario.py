from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

from validador.catalogo import CADERNOS, normalize_key

SEARCH_API_BASE = "https://do-api-web-search.doe.sp.gov.br"
PDF_API_BASE = "https://do-api-publication-pdf.doe.sp.gov.br"


class SumarioClient:
    def __init__(self, timeout: int = 60, retries: int = 2) -> None:
        self.timeout = timeout
        self.retries = retries
        self._mapa_secoes: dict[tuple[str, str], tuple[str, str]] | None = None
        self._mapa_data: date | None = None

    def _request(
        self, base: str, path: str, *, method: str = "GET"
    ) -> tuple[int, Any]:
        url = f"{base.rstrip('/')}{path}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ValidadorDOE/1.0",
                "Accept": "application/json",
            },
            method=method,
        )
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                    if not body:
                        return response.status, None
                    return response.status, json.loads(body)
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", errors="ignore")
                try:
                    payload = json.loads(body) if body else None
                except json.JSONDecodeError:
                    payload = None
                return error.code, payload
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt < self.retries:
                    time.sleep(2 * (attempt + 1))
                    continue
        print(f"Falha de rede ao consultar sumário ({path}): {last_error}", flush=True)
        return 599, None

    def carregar_mapa_secoes(self, edition_date: date) -> dict[tuple[str, str], tuple[str, str]]:
        if self._mapa_secoes is not None and self._mapa_data == edition_date:
            return self._mapa_secoes

        mapa: dict[tuple[str, str], tuple[str, str]] = {}
        status, payload = self._request(SEARCH_API_BASE, "/v2/journals")
        if status != 200 or not isinstance(payload, dict):
            self._mapa_secoes = mapa
            self._mapa_data = edition_date
            return mapa

        journals_por_nome = {
            normalize_key(journal["name"]): journal["id"]
            for journal in payload.get("items", [])
            if journal.get("id") and journal.get("name")
        }

        date_param = edition_date.isoformat()
        for caderno in CADERNOS:
            journal_id = journals_por_nome.get(normalize_key(caderno.nome))
            if not journal_id:
                continue

            query = urllib.parse.urlencode(
                {"JournalId": journal_id, "EditionDate": date_param}
            )
            section_status, sections_payload = self._request(
                SEARCH_API_BASE, f"/v2/sections?{query}"
            )
            if section_status != 200 or not isinstance(sections_payload, dict):
                continue

            secoes_por_nome = {
                normalize_key(section["name"]): section["id"]
                for section in sections_payload.get("items", [])
                if section.get("id") and section.get("name")
            }
            for secao in caderno.secoes:
                section_id = secoes_por_nome.get(normalize_key(secao.nome))
                if section_id:
                    chave = (normalize_key(caderno.nome), normalize_key(secao.nome))
                    mapa[chave] = (journal_id, section_id)

        self._mapa_secoes = mapa
        self._mapa_data = edition_date
        return mapa

    def secao_sem_materias(
        self,
        caderno: str,
        secao: str,
        edition_date: date,
        mapa_secoes: dict[tuple[str, str], tuple[str, str]],
    ) -> bool:
        ids = mapa_secoes.get((normalize_key(caderno), normalize_key(secao)))
        if not ids:
            return False

        journal_id, section_id = ids
        params = urllib.parse.urlencode(
            {
                "JournalId": journal_id,
                "RootSectionId": section_id,
                "EditionDate": edition_date.isoformat(),
            }
        )

        edition_status, _ = self._request(
            PDF_API_BASE, f"/v1/editions/url?{params}"
        )
        if edition_status == 200:
            return False

        supplementary_status, supplementary_payload = self._request(
            PDF_API_BASE, f"/v1/supplementary-editions/url?{params}"
        )
        if supplementary_status == 200 and isinstance(supplementary_payload, dict):
            urls = supplementary_payload.get("supplementaryEditionsUrls") or []
            if urls:
                return False

        return edition_status == 404
