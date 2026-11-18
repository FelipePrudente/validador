from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


def enviar_email(
    config: dict[str, Any],
    assunto: str,
    corpo_texto: str,
    corpo_html: str,
) -> None:
    if not config.get("enabled", True):
        return

    mensagem = MIMEMultipart("alternative")
    mensagem["Subject"] = assunto
    mensagem["From"] = config["from_addr"]
    mensagem["To"] = ", ".join(config["to_addrs"])
    mensagem.attach(MIMEText(corpo_texto, "plain", "utf-8"))
    mensagem.attach(MIMEText(corpo_html, "html", "utf-8"))

    host = config["smtp_host"]
    port = int(config.get("smtp_port", 25))
    user = config.get("smtp_user") or None
    password = config.get("smtp_password") or None
    use_tls = bool(config.get("use_tls", False))

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.sendmail(config["from_addr"], config["to_addrs"], mensagem.as_string())
