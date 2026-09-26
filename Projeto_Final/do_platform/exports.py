"""Exportação da comparação de apólices (Excel, Markdown e PDF).

Recebe o resultado já calculado, então exportar não chama o LLM de novo.
"""
from __future__ import annotations

import io

import pandas as pd

from .comparison import ComparisonResult


def comparison_xlsx(res: ComparisonResult, analise: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame(res.geral).to_excel(w, sheet_name="Dados gerais", index=False)
        pd.DataFrame(res.coberturas).to_excel(w, sheet_name="Coberturas", index=False)
        pd.DataFrame(res.exclusoes).to_excel(w, sheet_name="Exclusões", index=False)
        pd.DataFrame(res.franquias).to_excel(w, sheet_name="Franquias", index=False)
        pd.DataFrame(analise.get("diferencas_chave", [])).to_excel(w, sheet_name="Análise", index=False)
    return buf.getvalue()


def comparison_markdown(res: ComparisonResult, analise: dict) -> str:
    out = ["# Comparação de apólices D&O", "", "## Resumo executivo", analise.get("resumo_executivo", ""), "",
           "## Diferenças-chave"]
    for d in analise.get("diferencas_chave", []):
        out.append(f"- **{d.get('tema')}** ({d.get('impacto')}, favorece: {d.get('favorece')}): {d.get('descricao')}")
    out += ["", "## Pontos de atenção"] + [f"- {p}" for p in analise.get("pontos_de_atencao", [])]
    out += ["", "## Recomendação", analise.get("recomendacao", ""), ""]
    for titulo, tab in [("Dados gerais", res.geral), ("Coberturas", res.coberturas),
                        ("Exclusões", res.exclusoes), ("Franquias", res.franquias)]:
        out += [f"## {titulo}", pd.DataFrame(tab).to_markdown(index=False), ""]
    return "\n".join(out)


# ─── PDF ─────────────────────────────────────────────────────────────────────
# Gerado com reportlab (sem Word/LibreOffice), para funcionar também no servidor Linux do deploy.
_AZUL, _CIANO, _AZUL_ESCURO, _CINZA = "#2563eb", "#06b6d4", "#0f2b48", "#64748b"
_IMPACTO = {"alto": ("Alto", "#dc2626"), "medio": ("Médio", "#d97706"), "médio": ("Médio", "#d97706"),
            "baixo": ("Baixo", "#059669")}
_ORDEM = {"alto": 0, "medio": 1, "médio": 1, "baixo": 2}


def _txt(v) -> str:
    """Texto seguro para o Paragraph do reportlab: escapa XML, põe datas no formato brasileiro e remove
    símbolos sem glifo na fonte padrão."""
    import re
    from xml.sax.saxutils import escape

    s = "—" if v is None or v == "" else str(v)
    s = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", r"\3/\2/\1", s)
    return escape(s.replace("✓ ", "").replace("✗ ", "").replace("✓", "").replace("✗", ""))


def _mi(v) -> str:
    if v is None:
        return "—"
    txt = f"R$ {v / 1e6:,.1f} mi" if abs(v) >= 1e6 else f"R$ {v / 1e3:,.1f} mil"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def _logo(canvas, x: float, y: float, tam: float) -> None:
    """Marca do Apólis (web/img/logo-mark.svg) em vetor: quadrado arredondado com degradê azul→ciano,
    o "A" cuja barra é a linha de comparação e o ponto da IA. (x, y) é o canto inferior esquerdo."""
    from reportlab.lib import colors

    u = tam / 48  # o SVG usa uma grade de 48 × 48

    def pt(px, py):  # coordenadas do SVG (y para baixo) → página (y para cima)
        return x + px * u, y + (48 - py) * u

    canvas.saveState()
    caminho = canvas.beginPath()
    caminho.roundRect(x, y, tam, tam, 13 * u)
    canvas.clipPath(caminho, stroke=0, fill=0)
    canvas.linearGradient(x, y + tam, x + tam, y, (colors.HexColor(_AZUL), colors.HexColor(_CIANO)), extend=True)
    canvas.restoreState()

    canvas.saveState()
    canvas.setStrokeColor(colors.white)
    canvas.setLineCap(1)
    canvas.setLineJoin(1)
    canvas.setLineWidth(3.6 * u)
    a = canvas.beginPath()
    a.moveTo(*pt(13.5, 36))
    a.lineTo(*pt(24, 11.2))
    a.lineTo(*pt(34.5, 36))
    canvas.drawPath(a, stroke=1, fill=0)
    canvas.setLineWidth(3.2 * u)
    canvas.setStrokeAlpha(0.85)
    canvas.line(*pt(18, 27.5), *pt(30, 27.5))
    canvas.setFillColor(colors.white)
    canvas.circle(*pt(36, 12), 3.2 * u, fill=1, stroke=0)
    canvas.restoreState()


def comparison_pdf(res: ComparisonResult, analise: dict) -> bytes:
    from datetime import datetime

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    labels = res.labels
    pagina = landscape(A4) if len(labels) > 3 else A4  # muitas apólices: página deitada
    margem = 1.6 * cm
    largura = pagina[0] - 2 * margem
    gerado = datetime.now().strftime("%d/%m/%Y às %H:%M")
    por_regras = analise.get("modo") == "regras"
    faixa = 4.2 * cm  # altura da faixa de capa na 1ª página

    base = ParagraphStyle("base", parent=getSampleStyleSheet()["BodyText"], fontName="Helvetica", fontSize=9,
                          leading=12.5, textColor=colors.HexColor("#1f2937"))
    st = {
        "sub": ParagraphStyle("s", parent=base, fontSize=8.3, leading=11, textColor=colors.HexColor(_CINZA)),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=12.5, leading=16, spaceBefore=16,
                             spaceAfter=7, textColor=colors.HexColor(_AZUL_ESCURO)),
        "cel": ParagraphStyle("c", parent=base, fontSize=7.8, leading=10),
        "cab": ParagraphStyle("h", parent=base, fontName="Helvetica-Bold", fontSize=7.8, leading=10, textColor=colors.white),
        "aviso": ParagraphStyle("a", parent=base, fontSize=8.5, leading=11.5, textColor=colors.HexColor("#1e3a8a")),
        "kpi_v": ParagraphStyle("kv", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=18,
                                textColor=colors.HexColor(_AZUL_ESCURO)),
        "kpi_l": ParagraphStyle("kl", parent=base, fontSize=7.5, leading=9.5, textColor=colors.HexColor(_CINZA)),
    }
    secao_n = [0]

    def secao(titulo):
        """Título numerado; só começa a seção se couber um trecho dela na página (evita título órfão)."""
        secao_n[0] += 1
        return CondPageBreak(3.5 * cm), Paragraph(f'<font color="{_AZUL}">{secao_n[0]:02d}</font>&nbsp;&nbsp;{_txt(titulo)}', st["h2"])

    def tabela(cabecalho, linhas, larguras, destaques=None):
        """Tabela com cabeçalho azul e linhas alternadas. `destaques`: {índice da linha: cor de fundo}."""
        dados = [[Paragraph(_txt(c), st["cab"]) for c in cabecalho]]
        dados += [[c if isinstance(c, Paragraph) else Paragraph(_txt(c), st["cel"]) for c in lin] for lin in linhas]
        estilo = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                  ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
                  ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                  ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]
        estilo += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8fafc" if i % 2 else "#ffffff"))
                   for i in range(1, len(dados))]
        estilo += [("BACKGROUND", (0, i + 1), (-1, i + 1), colors.HexColor(cor)) for i, cor in (destaques or {}).items()]
        t = Table(dados, colWidths=larguras, repeatRows=1)
        t.setStyle(TableStyle(estilo))
        return t

    def larguras(fixas: list[float], finais: list[float] | None = None) -> list[float]:
        """Colunas fixas (frações da largura) antes e depois; o restante dividido entre as apólices."""
        finais = finais or []
        resto = largura * (1 - sum(fixas) - sum(finais)) / len(labels)
        return [largura * f for f in fixas] + [resto] * len(labels) + [largura * f for f in finais]

    def rodape(canvas, doc):
        w, _ = pagina
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor(_CINZA))
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.line(margem, 1.35 * cm, w - margem, 1.35 * cm)
        canvas.drawString(margem, 0.95 * cm, f"Apólis · gerado em {gerado} · análise automatizada: a decisão final "
                                             "exige revisão por especialista")
        canvas.drawRightString(w - margem, 0.95 * cm, f"Página {doc.page}")

    def capa(canvas, doc):
        """1ª página: faixa com degradê, logo, nome do software e título do relatório."""
        w, h = pagina
        canvas.saveState()
        recorte = canvas.beginPath()
        recorte.rect(0, h - faixa, w, faixa)
        canvas.clipPath(recorte, stroke=0, fill=0)
        canvas.linearGradient(0, h, w, h - faixa, (colors.HexColor(_AZUL_ESCURO), colors.HexColor("#1e3a8a")), extend=True)
        canvas.restoreState()
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(_CIANO))
        canvas.rect(0, h - faixa, w, 0.12 * cm, fill=1, stroke=0)
        _logo(canvas, margem, h - 2.55 * cm, 1.35 * cm)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawString(margem + 1.7 * cm, h - 1.78 * cm, "Apólis")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#bfdbfe"))
        canvas.drawString(margem + 1.72 * cm, h - 2.38 * cm, "Análise e comparação de apólices D&O com IA")
        canvas.setFont("Helvetica-Bold", 15)
        canvas.setFillColor(colors.white)
        canvas.drawRightString(w - margem, h - 1.78 * cm, "Relatório de comparação")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#bfdbfe"))
        canvas.drawRightString(w - margem, h - 2.38 * cm, f"{len(labels)} apólices · {gerado}")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(margem, h - 3.55 * cm, "Seguro de Responsabilidade Civil de Administradores e Diretores (D&O)")
        canvas.restoreState()
        rodape(canvas, doc)

    def demais(canvas, doc):
        """Páginas seguintes: cabeçalho discreto com a logo e o nome."""
        w, h = pagina
        _logo(canvas, margem, h - 1.5 * cm, 0.55 * cm)
        canvas.setFont("Helvetica-Bold", 10.5)
        canvas.setFillColor(colors.HexColor(_AZUL_ESCURO))
        canvas.drawString(margem + 0.72 * cm, h - 1.3 * cm, "Apólis")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor(_CINZA))
        canvas.drawRightString(w - margem, h - 1.3 * cm, "Relatório de comparação de apólices D&O")
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.line(margem, h - 1.72 * cm, w - margem, h - 1.72 * cm)
        rodape(canvas, doc)

    m = res.metricas

    def melhor(chave, maior):
        vals = {lb: m[lb][chave] for lb in labels if m[lb][chave] is not None}
        return (max if maior else min)(vals, key=vals.get) if len(set(vals.values())) > 1 else None

    dk = sorted(analise.get("diferencas_chave") or [], key=lambda d: _ORDEM.get(str(d.get("impacto")).lower(), 3))
    altos = sum(1 for d in dk if str(d.get("impacto")).lower() == "alto")
    maior_lmg = melhor("lmg", True)

    # Resumo em números, logo abaixo da faixa de capa
    cartoes = [(str(len(labels)), "apólices comparadas"), (str(len(res.diferencas)), "diferenças objetivas"),
               (str(altos), "diferenças de alto impacto"),
               (_mi(m[maior_lmg]["lmg"]) if maior_lmg else "—", f"maior LMG: {maior_lmg.split(' · ')[0]}" if maior_lmg else "maior LMG")]
    kpis = Table([[[Paragraph(_txt(v), st["kpi_v"]), Paragraph(_txt(r), st["kpi_l"])] for v, r in cartoes]],
                 colWidths=[largura / 4] * 4)
    kpis.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbeafe")),
                              ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbeafe")),
                              ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fbff")),
                              ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                              ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    el = [Spacer(1, faixa - 2.0 * cm), kpis]

    ident = {r["Campo"]: r for r in res.geral}
    el += [*secao("Apólices comparadas"),
           tabela(["Rótulo", "Seguradora", "Nº da apólice", "Tomador", "Vigência"],
                  [[lb] + [ident.get(c, {}).get(lb) for c in ("Seguradora", "Nº da apólice", "Tomador", "Vigência")]
                   for lb in labels], [largura * f for f in (0.18, 0.22, 0.17, 0.22, 0.21)])]

    linhas = []
    for nome, chave, fmt, maior in (("Limite Máximo de Garantia", "lmg", _mi, True),
                                    ("Prêmio total", "premio", _mi, False),
                                    ("Prêmio / LMG", "taxa_pct", lambda v: "—" if v is None else f"{v:.3f}%".replace(".", ","), False),
                                    ("Coberturas", "coberturas", str, True), ("Exclusões", "exclusoes", str, False)):
        venc = melhor(chave, maior)
        linhas.append([Paragraph(f"<b>{nome}</b>", st["cel"])] +
                      [Paragraph(f'<font color="#059669"><b>{_txt(fmt(m[lb][chave]))}</b></font>'
                                 if lb == venc else _txt(fmt(m[lb][chave])), st["cel"]) for lb in labels])
    el += [*secao("Métricas lado a lado"), tabela(["Métrica"] + labels, linhas, larguras([0.26])), Spacer(1, 3),
           Paragraph("Em verde, o valor mais favorável: maior limite e número de coberturas; menor prêmio, "
                     "custo relativo e número de exclusões.", st["sub"])]

    el += secao("Análise executiva")
    if por_regras:
        el += [Table([[Paragraph("<b>Análise por regras (modo offline).</b> As diferenças foram classificadas "
                                 "automaticamente pelo impacto. Com um modelo de IA configurado no Apólis, o relatório "
                                 "traz o resumo executivo redigido e uma recomendação.", st["aviso"])]], colWidths=[largura],
                     style=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                            ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(_AZUL)),
                            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                            ("LEFTPADDING", (0, 0), (-1, -1), 9)]),
               Spacer(1, 7)]
    el.append(Paragraph(_txt(analise.get("resumo_executivo")), base))
    if analise.get("recomendacao") and not por_regras:
        el += [Spacer(1, 5), Paragraph(f"<b>Recomendação.</b> {_txt(analise['recomendacao'])}", base)]

    pontos = analise.get("pontos_de_atencao") or []
    if pontos:
        el += secao("Pontos de atenção")
        el += [Paragraph(f'<font color="#d97706"><b>!</b></font>&nbsp;&nbsp;{_txt(p)}',
                         ParagraphStyle("pt", parent=base, leftIndent=12, firstLineIndent=-12, spaceAfter=4))
               for p in pontos]

    if dk:
        linhas = []
        for d in dk:
            rot, cor = _IMPACTO.get(str(d.get("impacto")).lower(), (str(d.get("impacto") or "—"), _CINZA))
            linhas.append([Paragraph(f"<b>{_txt(d.get('tema'))}</b>", st["cel"]),
                           Paragraph(f'<font color="{cor}"><b>{_txt(rot)}</b></font>', st["cel"]),
                           d.get("favorece"), d.get("descricao")])
        el += [*secao("Diferenças-chave, por impacto"),
               tabela(["Tema", "Impacto", "Favorece", "Descrição"], linhas, [largura * f for f in (0.22, 0.09, 0.2, 0.49)])]

    el += [*secao("Dados gerais"),
           tabela(["Campo"] + labels, [[Paragraph(f"<b>{_txt(r['Campo'])}</b>", st["cel"])] + [r.get(lb) for lb in labels]
                                       for r in res.geral], larguras([0.2]),
                  {i: "#fef3c7" for i, r in enumerate(res.geral) if r.get("Diferente")}),
           Spacer(1, 3), Paragraph("Linhas destacadas diferem entre as apólices.", st["sub"])]

    def cor_situacao(s):
        s = str(s or "")
        return "#fee2e2" if s.startswith(("Ausente", "Só em")) else "#fef3c7" if s.startswith("Limites") else None

    for titulo, itens, chave in (("Coberturas", res.coberturas, "Cobertura"), ("Exclusões", res.exclusoes, "Exclusão")):
        if itens:
            el += [*secao(titulo),
                   tabela([chave, "Categoria"] + labels + ["Situação"],
                          [[Paragraph(f"<b>{_txt(r[chave])}</b>", st["cel"]), r.get("Categoria")] +
                           [r.get(lb) for lb in labels] + [r.get("Situação")] for r in itens],
                          larguras([0.2, 0.11], [0.16]),
                          {i: c for i, r in enumerate(itens) if (c := cor_situacao(r.get("Situação")))}),
                   Spacer(1, 3), Paragraph("Vermelho: ausente em alguma apólice. Amarelo: limites diferentes.", st["sub"])]
    if res.franquias:
        el += [*secao("Franquias"),
               tabela(["Aplicação"] + labels, [[Paragraph(f"<b>{_txt(r['Aplicação'])}</b>", st["cel"])] +
                                               [r.get(lb) for lb in labels] for r in res.franquias], larguras([0.3]))]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagina, leftMargin=margem, rightMargin=margem, topMargin=2.2 * cm,
                            bottomMargin=1.8 * cm, title="Relatório de comparação de apólices D&O — Apólis",
                            author="Apólis", subject="Comparação de apólices D&O")
    doc.build(el, onFirstPage=capa, onLaterPages=demais)
    return buf.getvalue()
