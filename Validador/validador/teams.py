from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def enviar_teams(config: dict[str, Any], payload: dict[str, Any]) -> None:
    if not config.get("enabled", False):
        return

    webhook_url = (config.get("webhook_url") or "").strip()
    if not webhook_url:
        raise ValueError(
            "URL do webhook do Teams não configurada em config.json (teams.webhook_url)."
        )

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status not in (200, 202):
                raise RuntimeError(f"Teams respondeu com HTTP {response.status}.")
            run_id = response.headers.get("x-ms-workflow-run-id")
            if run_id:
                print(f"Power Automate aceitou o disparo (run-id: {run_id}).")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Falha ao enviar para o Teams (HTTP {error.code}): {detail}"
        ) from error
