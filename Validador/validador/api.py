from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class EditionRecord:
    edition_id: str
    edition_name: str
    status: str
    publications: int
    edition_auth_code: str | None = None


class DoeApiClient:
    def __init__(self, base_url: str, timeout: int = 60, retries: int = 2) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries

    def _request(self, path: str) -> tuple[int, dict[str, Any] | None]:
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ValidadorDOE/1.0",
                "Accept": "application/json",
            },
        )
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                    return response.status, json.loads(body) if body else None
            except urllib.error.HTTPError as error:
                return error.code, None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt < self.retries:
                    time.sleep(2 * (attempt + 1))
                    continue
        # Timeout/rede: código sintético para o validador reportar falha e alertar.
        print(f"Falha de rede ao consultar API ({path}): {last_error}", flush=True)
        return 599, None

    def fetch_editions_status(self, edition_date: str) -> tuple[int, list[EditionRecord]]:
        status_code, payload = self._request(f"/v1/editions/status/{edition_date}")
        if status_code != 200 or not payload:
            return status_code, []
        return status_code, _parse_editions(payload)

    def fetch_supplementary_status(self, edition_date: str) -> tuple[int, list[EditionRecord]]:
        status_code, payload = self._request(
            f"/v1/supplementary-editions/status/{edition_date}"
        )
        if status_code != 200 or not payload:
            return status_code, []
        return status_code, _parse_editions(payload)


def _parse_editions(payload: dict[str, Any]) -> list[EditionRecord]:
    records: list[EditionRecord] = []
    for item in payload.get("editionsProcessed", []):
        records.append(
            EditionRecord(
                edition_id=item.get("editionId", ""),
                edition_name=item.get("editionName", ""),
                status=item.get("status", ""),
                publications=int(item.get("publications", 0) or 0),
                edition_auth_code=item.get("editionAuthCode"),
            )
        )
    return records
