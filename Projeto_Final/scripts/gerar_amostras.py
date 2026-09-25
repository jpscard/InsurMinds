"""Gera apólices D&O FICTÍCIAS para demonstração e testes.

As seguradoras, tomadores, números de apólice e processos SUSEP são inventados.
A redação segue a estrutura típica de apólices D&O do mercado brasileiro
(quadro de coberturas, franquias, exclusões, segurados, cláusulas particulares),
para que a plataforma seja exercitada com documentos realistas.

Gera:
  samples/apolice_aurora_do.pdf              PDF digital (texto selecionável)
  samples/apolice_boreal_do.pdf              PDF digital, condições mais restritivas
  samples/apolice_cruzeiro_digitalizada.pdf  PDF só com imagens (simula digitalização -> OCR)
  samples/imagem/apolice_cruzeiro_pagina1.png Imagem de uma página (entrada por imagem -> OCR)

Uso:  python scripts/gerar_amostras.py
"""
from __future__ import annotations

import io
import random
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent.parent / "samples"

EXCLUSOES_BASE = [
    ("Atos dolosos ou fraudulentos", "Reclamações decorrentes de atos dolosos, fraudulentos ou praticados com "
     "a intenção de obter vantagem pessoal indevida, reconhecidos por decisão judicial ou arbitral definitiva."),
    ("Danos corporais e materiais", "Reclamações por danos corporais, morte, doença, danos materiais ou "
     "destruição de bens, exceto quanto aos custos de defesa em reclamações de acionistas."),
    ("Reclamações prévias e circunstâncias conhecidas", "Reclamações ou circunstâncias conhecidas pelos "
     "Segurados antes do início de vigência, ou já notificadas em apólice anterior."),
    ("Multas e penalidades", "Multas, penalidades e tributos, salvo multas civis e administrativas "
     "aplicadas aos Segurados quando o reembolso for permitido pela legislação."),
    ("Poluição ambiental", "Reclamações relativas a poluição ou contaminação ambiental."),
]

APOLICES = {
    "aurora": dict(
        arquivo="apolice_aurora_do.pdf",
        seguradora="Aurora Seguros S.A. (FICTÍCIA)",
        numero="1010.0045871",
        susep="15414.000001/2026-11 (fictício)",
        tomador="Metalúrgica Horizonte S.A. (fictícia)",
        cnpj="00.000.001/0001-91",
        corretor="Prisma Corretora de Seguros Ltda. (fictícia)",
        vig=("01/03/2026", "01/03/2027"),
        lmg="R$ 20.000.000,00", premio="R$ 148.500,00",
        base="À base de reclamações (claims made), com notificação",
        retro="01/03/2019", complementar="36 meses, mediante pagamento de prêmio adicional",
        territorio="Mundial, exceto Estados Unidos e Canadá",
        custos="Dentro do LMG, com adiantamento de custos de defesa em até 15 dias",
        coberturas=[
            ("Lado A – Pagamento direto aos Segurados", "R$ 20.000.000,00", "Não há"),
            ("Lado B – Reembolso à Sociedade Tomadora", "R$ 20.000.000,00", "R$ 100.000,00"),
            ("Lado C – Mercado de Capitais (entidade)", "R$ 10.000.000,00", "R$ 250.000,00"),
            ("Custos de Defesa", "R$ 20.000.000,00", "Não há"),
            ("Custos Emergenciais", "R$ 2.000.000,00", "Não há"),
            ("Extensão a Cônjuges e Herdeiros", "R$ 20.000.000,00", "Não há"),
            ("Penhora on-line e bloqueio de bens", "R$ 3.000.000,00", "Não há"),
            ("Multas civis e administrativas", "R$ 5.000.000,00", "R$ 50.000,00"),
            ("Custos de Publicidade e Gerenciamento de Crise", "R$ 1.000.000,00", "Não há"),
        ],
        franquias=[
            ("Reclamações contra a Sociedade (Lado C)", "R$ 250.000,00"),
            ("Reembolso à Sociedade (Lado B)", "R$ 100.000,00"),
            ("Reclamações trabalhistas", "R$ 30.000,00"),
        ],
        exclusoes=EXCLUSOES_BASE,
        segurados=[
            "Diretores e membros do Conselho de Administração, eleitos ou nomeados",
            "Membros do Conselho Fiscal e de comitês estatutários",
            "Empregados em cargo de gestão, quando corréus com Administradores",
            "Administradores de subsidiárias e coligadas com participação superior a 50%",
        ],
        clausulas=[
            "Cláusula de alocação: 100% dos custos de defesa alocados à parte segurada em reclamações mistas.",
            "Ordem de pagamento: prioridade ao Lado A sobre os Lados B e C.",
            "Não-imputação: o conhecimento de um Segurado não é imputado aos demais.",
        ],
    ),
    "boreal": dict(
        arquivo="apolice_boreal_do.pdf",
        seguradora="Boreal Companhia de Seguros (FICTÍCIA)",
        numero="7702.2026.00913",
        susep="15414.000002/2026-22 (fictício)",
        tomador="Metalúrgica Horizonte S.A. (fictícia)",
        cnpj="00.000.001/0001-91",
        corretor="Prisma Corretora de Seguros Ltda. (fictícia)",
        vig=("01/03/2026", "01/03/2027"),
        lmg="R$ 15.000.000,00", premio="R$ 96.300,00",
        base="À base de reclamações (claims made)",
        retro="01/03/2022", complementar="12 meses, sem prêmio adicional",
        territorio="Brasil",
        custos="Dentro do LMG, reembolso após aprovação prévia da Seguradora",
        coberturas=[
            ("Lado A – Pagamento direto aos Segurados", "R$ 15.000.000,00", "Não há"),
            ("Lado B – Reembolso à Sociedade Tomadora", "R$ 15.000.000,00", "R$ 250.000,00"),
            ("Custos de Defesa", "R$ 15.000.000,00", "Não há"),
            ("Extensão a Cônjuges e Herdeiros", "R$ 15.000.000,00", "Não há"),
            ("Penhora on-line e bloqueio de bens", "R$ 1.000.000,00", "Não há"),
            ("Multas civis e administrativas", "R$ 2.000.000,00", "R$ 100.000,00"),
        ],
        franquias=[
            ("Reembolso à Sociedade (Lado B)", "R$ 250.000,00"),
            ("Reclamações trabalhistas", "R$ 75.000,00"),
        ],
        exclusoes=EXCLUSOES_BASE + [
            ("Segurado contra Segurado", "Reclamações movidas por um Segurado ou pela Sociedade Tomadora "
             "contra outro Segurado, exceto ações derivativas de acionistas minoritários."),
            ("Reclamações trabalhistas coletivas", "Reclamações trabalhistas coletivas ou movidas por "
             "sindicatos contra os Segurados."),
            ("Oferta pública de valores mobiliários", "Reclamações decorrentes de oferta pública de "
             "valores mobiliários realizada durante a vigência, salvo aceitação expressa."),
        ],
        segurados=[
            "Diretores e membros do Conselho de Administração, eleitos ou nomeados",
            "Membros do Conselho Fiscal",
        ],
        clausulas=[
            "Cláusula de alocação: custos de defesa alocados proporcionalmente em reclamações mistas.",
            "Consentimento prévio: acordos e custos de defesa dependem de anuência escrita da Seguradora.",
        ],
    ),
    "cruzeiro": dict(
        arquivo="apolice_cruzeiro_digitalizada.pdf",
        seguradora="Cruzeiro Austral Seguros S.A. (FICTÍCIA)",
        numero="3300.558120",
        susep="15414.000003/2026-33 (fictício)",
        tomador="Metalúrgica Horizonte S.A. (fictícia)",
        cnpj="00.000.001/0001-91",
        corretor="Prisma Corretora de Seguros Ltda. (fictícia)",
        vig=("01/03/2026", "01/03/2027"),
        lmg="R$ 25.000.000,00", premio="R$ 201.000,00",
        base="À base de reclamações (claims made)",
        retro="Ilimitada", complementar="60 meses, mediante prêmio adicional",
        territorio="Mundial",
        custos="Fora do LMG até 30% do limite, com adiantamento",
        coberturas=[
            ("Lado A – Pagamento direto aos Segurados", "R$ 25.000.000,00", "Não há"),
            ("Lado B – Reembolso à Sociedade Tomadora", "R$ 25.000.000,00", "R$ 150.000,00"),
            ("Lado C – Mercado de Capitais (entidade)", "R$ 15.000.000,00", "R$ 300.000,00"),
            ("Custos de Defesa", "R$ 25.000.000,00", "Não há"),
            ("Extensão a Cônjuges e Herdeiros", "R$ 25.000.000,00", "Não há"),
            ("Responsabilidade Ambiental – Custos de Defesa", "R$ 2.500.000,00", "R$ 50.000,00"),
            ("Investigações de órgãos reguladores", "R$ 5.000.000,00", "Não há"),
        ],
        franquias=[
            ("Reclamações contra a Sociedade (Lado C)", "R$ 300.000,00"),
            ("Reembolso à Sociedade (Lado B)", "R$ 150.000,00"),
        ],
        exclusoes=EXCLUSOES_BASE[:4],
        segurados=[
            "Diretores e membros do Conselho de Administração, eleitos ou nomeados",
            "Membros do Conselho Fiscal e de comitês estatutários",
            "Administradores de fato e gestores de fundos de pensão patrocinados",
        ],
        clausulas=[
            "Ordem de pagamento: prioridade ao Lado A.",
            "Limite adicional exclusivo para Administradores independentes: R$ 2.000.000,00.",
        ],
    ),
}


def build_pdf(d: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=f"Apólice D&O {d['numero']} (fictícia)")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=13, leading=16)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=12.5)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=colors.grey)

    el = [
        Paragraph(d["seguradora"].upper(), h1),
        Paragraph("APÓLICE DE SEGURO DE RESPONSABILIDADE CIVIL DE ADMINISTRADORES E DIRETORES – D&amp;O", h1),
        Paragraph("Documento fictício gerado para fins acadêmicos. Não possui validade jurídica.", small),
        Paragraph("DADOS DA APÓLICE", h2),
    ]
    campos = [
        ("Seguradora", d["seguradora"]), ("Apólice nº", d["numero"]),
        ("Produto", "RC D&amp;O – Responsabilidade Civil de Administradores"),
        ("Processo SUSEP nº", d["susep"]), ("Tomador", d["tomador"]), ("CNPJ", d["cnpj"]),
        ("Corretor", d["corretor"]),
        ("Vigência", f"das 24h de {d['vig'][0]} às 24h de {d['vig'][1]}"),
        ("Limite Máximo de Garantia (LMG)", f"{d['lmg']} (agregado, por reclamação e no período)"),
        ("Prêmio Total", f"{d['premio']} (incluso IOF)"),
        ("Base de cobertura", d["base"]),
        ("Data de retroatividade", d["retro"]),
        ("Prazo complementar", d["complementar"]),
        ("Territorialidade", d["territorio"]),
        ("Tratamento dos custos de defesa", d["custos"]),
    ]
    for k, v in campos:
        el.append(Paragraph(f"{k}: {v}", body))

    el.append(Paragraph("QUADRO DE COBERTURAS E LIMITES", h2))
    tab = Table([["Cobertura", "Limite", "Franquia"]] + [list(c) for c in d["coberturas"]],
                colWidths=[9.3 * cm, 4 * cm, 3.7 * cm])
    tab.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    el += [tab, Paragraph("FRANQUIAS", h2)]
    for i, (k, v) in enumerate(d["franquias"], 1):
        el.append(Paragraph(f"{i}. {k}: {v} por reclamação", body))

    el.append(Paragraph("SEGURADOS", h2))
    for i, s in enumerate(d["segurados"], 1):
        el.append(Paragraph(f"{i}. {s}", body))

    el.append(Paragraph("EXCLUSÕES", h2))
    el.append(Paragraph("Além das exclusões das Condições Gerais, este seguro não cobre:", body))
    for i, (t, desc) in enumerate(d["exclusoes"], 1):
        el.append(Paragraph(f"{i}. {t}: {desc}", body))

    el.append(Paragraph("CLÁUSULAS PARTICULARES", h2))
    for i, c in enumerate(d["clausulas"], 1):
        el.append(Paragraph(f"{i}. {c}", body))
    el += [Spacer(1, 12), Paragraph("DISPOSIÇÕES FINAIS", h2), Paragraph(
        "As Condições Gerais e Especiais do produto integram esta apólice. Em caso de divergência, "
        "prevalecem as Condições Particulares acima.", small)]
    doc.build(el)
    return buf.getvalue()


def to_scanned(pdf_bytes: bytes) -> tuple[bytes, bytes]:
    """Rasteriza o PDF, adiciona ruído/rotação leve e remonta como PDF somente-imagem."""
    import pypdfium2 as pdfium
    from PIL import Image, ImageFilter

    rnd = random.Random(42)
    pdf = pdfium.PdfDocument(pdf_bytes)
    imgs = []
    for page in pdf:
        img = page.render(scale=200 / 72).to_pil().convert("L")
        img = img.rotate(rnd.uniform(-0.6, 0.6), expand=False, fillcolor=255, resample=Image.BICUBIC)
        img = img.filter(ImageFilter.GaussianBlur(0.4))
        imgs.append(img.convert("RGB"))
    pdf.close()
    out = io.BytesIO()
    imgs[0].save(out, "PDF", save_all=True, append_images=imgs[1:], resolution=200)
    png = io.BytesIO()
    imgs[0].save(png, "PNG")
    return out.getvalue(), png.getvalue()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for key, d in APOLICES.items():
        pdf = build_pdf(d)
        if key == "cruzeiro":
            scanned, png = to_scanned(pdf)
            (OUT / d["arquivo"]).write_bytes(scanned)
            (OUT / "imagem").mkdir(exist_ok=True)
            (OUT / "imagem" / "apolice_cruzeiro_pagina1.png").write_bytes(png)
        else:
            (OUT / d["arquivo"]).write_bytes(pdf)
        print("gerado:", d["arquivo"])


if __name__ == "__main__":
    main()
