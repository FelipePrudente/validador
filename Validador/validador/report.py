from __future__ import annotations

from validador.catalogo import STATUS_PRONTO, STATUS_SEM_MATERIAS
from validador.validator import ResultadoValidacao


def render_console(resultado: ResultadoValidacao, sumario_url: str) -> str:
    linhas: list[str] = []
    data_fmt = resultado.data_referencia.strftime("%d/%m/%Y")

    linhas.append("=" * 72)
    linhas.append("VALIDADOR DOE-SP — Cadernos e Seções")
    linhas.append("=" * 72)
    linhas.append(f"Data verificada: {data_fmt}")
    linhas.append(f"Fonte: {sumario_url}")
    linhas.append("")

    if resultado.ignorado:
        linhas.append(f"Status: IGNORADO")
        linhas.append(f"Motivo: {resultado.motivo_ignorado}")
        linhas.append("=" * 72)
        return "\n".join(linhas)

    status = "APROVADO" if resultado.sucesso else "FALHA"
    linhas.append(f"Status geral: {status}")
    linhas.append("")

    regulares = [item for item in resultado.itens if item.tipo == "Regular"]
    suplementos = [item for item in resultado.itens if item.tipo == "Suplemento"]

    linhas.append("EDIÇÕES REGULARES")
    linhas.append("-" * 72)
    linhas.extend(_render_itens(regulares))
    linhas.append("")

    linhas.append("SUPLEMENTOS")
    linhas.append("-" * 72)
    if suplementos:
        linhas.extend(_render_itens(suplementos))
    else:
        linhas.append("Nenhum suplemento ativo para esta data.")
    linhas.append("")

    if resultado.falhas:
        linhas.append("FALHAS DETECTADAS")
        linhas.append("-" * 72)
        for falha in resultado.falhas:
            linhas.append(f"  • {falha}")
        linhas.append("")

    if resultado.avisos:
        linhas.append("AVISOS")
        linhas.append("-" * 72)
        for aviso in resultado.avisos:
            linhas.append(f"  • {aviso}")
        linhas.append("")

    linhas.append("=" * 72)
    return "\n".join(linhas)


def render_email_html(resultado: ResultadoValidacao, sumario_url: str) -> str:
    data_fmt = resultado.data_referencia.strftime("%d/%m/%Y")

    if resultado.ignorado:
        return f"""
        <html><body style="font-family:Segoe UI,Arial,sans-serif">
          <h2>Validador DOE-SP</h2>
          <p><strong>Data:</strong> {data_fmt}</p>
          <p><strong>Status:</strong> Ignorado</p>
          <p>{resultado.motivo_ignorado}</p>
        </body></html>
        """

    status = "Aprovado" if resultado.sucesso else "Falha"
    cor = "#1b7f3b" if resultado.sucesso else "#c62828"

    linhas_tabela = []
    for item in resultado.itens:
        linhas_tabela.append(
            "<tr>"
            f"<td>{item.tipo}</td>"
            f"<td>{item.caderno}</td>"
            f"<td>{item.secao}</td>"
            f"<td>{item.status}</td>"
            f"<td>{'' if item.publicacoes is None else item.publicacoes}</td>"
            f"<td>{item.codigo_autenticidade or ''}</td>"
            "</tr>"
        )

    falhas_html = "".join(f"<li>{falha}</li>" for falha in resultado.falhas)

    return f"""
    <html>
      <body style="font-family:Segoe UI,Arial,sans-serif;color:#222">
        <h2 style="color:{cor}">Validador DOE-SP — {status}</h2>
        <p><strong>Data verificada:</strong> {data_fmt}</p>
        <p><strong>Fonte:</strong> <a href="{sumario_url}">{sumario_url}</a></p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%">
          <thead style="background:#f5f5f5">
            <tr>
              <th>Tipo</th><th>Caderno</th><th>Seção</th><th>Status</th><th>Publicações</th><th>Código</th>
            </tr>
          </thead>
          <tbody>
            {''.join(linhas_tabela)}
          </tbody>
        </table>
        {"<h3>Falhas</h3><ul>" + falhas_html + "</ul>" if falhas_html else ""}
      </body>
    </html>
    """


def render_teams_card(resultado: ResultadoValidacao, sumario_url: str) -> dict:
    data_fmt = resultado.data_referencia.strftime("%d/%m/%Y")
    sucesso = resultado.sucesso

    if sucesso:
        titulo = f"Validador DOE-SP — Tudo OK em {data_fmt}"
        cor = "1B7F3B"
        status_label = "Aprovado"
        linhas_texto = _render_teams_resumo_itens(resultado.itens, apenas_problemas=False)
        if resultado.avisos:
            linhas_texto.append("")
            linhas_texto.append("**Avisos:**")
            linhas_texto.extend(f"- {aviso}" for aviso in resultado.avisos)
    else:
        titulo = f"Validador DOE-SP — Falha em {data_fmt}"
        cor = "C62828"
        status_label = "Falha"
        linhas_texto = [f"- {falha}" for falha in resultado.falhas]
        itens_com_problema = [
            item
            for item in resultado.itens
            if item.status not in (STATUS_PRONTO, STATUS_SEM_MATERIAS)
        ]
        if itens_com_problema:
            linhas_texto.append("")
            linhas_texto.append("**Itens com problema:**")
            linhas_texto.extend(
                _render_teams_linha_item(item) for item in itens_com_problema
            )

    regulares = sum(1 for item in resultado.itens if item.tipo == "Regular")
    suplementos = sum(1 for item in resultado.itens if item.tipo == "Suplemento")
    corpo = "\n".join(linhas_texto)
    texto_plano = (
        f"{titulo}\n"
        f"Data verificada: {data_fmt}\n"
        f"Status: {status_label}\n"
        f"Regulares: {regulares} | Suplementos: {suplementos}\n"
        f"Sumário: {sumario_url}\n\n"
        f"{corpo}"
    ).strip()

    # Inclui campos de raiz (text/message) para Power Automate,
    # além do MessageCard usado por Incoming Webhook clássico.
    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": cor,
        "summary": titulo,
        "title": titulo,
        "text": texto_plano,
        "message": texto_plano,
        "status": status_label,
        "data": data_fmt,
        "sections": [
            {
                "activityTitle": "Diário Oficial do Estado de São Paulo",
                "facts": [
                    {"name": "Data verificada", "value": data_fmt},
                    {"name": "Status", "value": status_label},
                    {"name": "Regulares", "value": str(regulares)},
                    {"name": "Suplementos", "value": str(suplementos)},
                    {"name": "Sumário", "value": f"[Abrir DOE-SP]({sumario_url})"},
                ],
                "text": corpo,
                "markdown": True,
            }
        ],
    }


def _render_teams_linha_item(item) -> str:
    pubs = (
        f" ({item.publicacoes} publicações)"
        if item.publicacoes is not None
        else ""
    )
    return f"- [{item.tipo}] {item.caderno} > {item.secao}: **{item.status}**{pubs}"


def _render_teams_resumo_itens(itens: list, *, apenas_problemas: bool) -> list[str]:
    linhas: list[str] = []
    for item in itens:
        if apenas_problemas and item.status in (STATUS_PRONTO, STATUS_SEM_MATERIAS):
            continue
        linhas.append(_render_teams_linha_item(item))
    return linhas


def _render_itens(itens: list) -> list[str]:
    linhas: list[str] = []
    for item in itens:
        marcador = "OK" if item.status in (STATUS_PRONTO, STATUS_SEM_MATERIAS) else "!!"
        pubs = "" if item.publicacoes is None else f" | publicações: {item.publicacoes}"
        codigo = f" | código: {item.codigo_autenticidade}" if item.codigo_autenticidade else ""
        linhas.append(
            f"[{marcador}] {item.caderno} > {item.secao} — {item.status}{pubs}{codigo}"
        )
    return linhas
