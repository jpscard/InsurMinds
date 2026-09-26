"""Apólices D&O FICTÍCIAS longas: condições particulares + condições gerais com cláusulas numeradas.

Complementa scripts/gerar_amostras.py com documentos maiores (6 a 20 páginas), que exercitam o
índice hierárquico (cláusulas, subitens e exceções), a extração em blocos e o OCR de vários páginas.
Todos os nomes, números e valores são inventados.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ─── Condições gerais: texto das cláusulas, parametrizado por seguradora ──────────
DEFINICOES = [
    ("Administrador", "pessoa física eleita ou nomeada para cargo de diretor, conselheiro de administração ou "
     "membro de órgão estatutário da Sociedade, inclusive quando o cargo for exercido de fato."),
    ("Apólice", "documento que formaliza o contrato de seguro, composto por estas Condições Gerais, pelas "
     "Condições Especiais e pelas Condições Particulares, além de eventuais endossos."),
    ("Ato Danoso", "qualquer ato, omissão, erro, declaração inexata ou violação de dever praticado pelo "
     "Segurado no exercício de suas funções de gestão, real ou alegado."),
    ("Custos de Defesa", "honorários advocatícios, periciais e demais despesas razoáveis e necessárias incorridas "
     "na defesa do Segurado em Reclamação coberta, com anuência prévia da Seguradora."),
    ("Franquia", "valor ou percentual, previsto nas Condições Particulares, que fica a cargo da Sociedade ou do "
     "Segurado em cada Reclamação, antes do pagamento da indenização."),
    ("Limite Máximo de Garantia", "valor máximo, agregado para todo o período de vigência, que a Seguradora "
     "pagará em decorrência de todas as Reclamações cobertas, incluídos os Custos de Defesa."),
    ("Perda", "valor que o Segurado seja legalmente obrigado a pagar em razão de sentença judicial, laudo arbitral "
     "ou acordo aprovado pela Seguradora, inclusive Custos de Defesa."),
    ("Período de Retroatividade", "período anterior ao início de vigência dentro do qual deve ter ocorrido o Ato "
     "Danoso para que a Reclamação esteja coberta."),
    ("Prazo Complementar", "período, contado do fim da vigência, durante o qual o Segurado pode apresentar "
     "Reclamações referentes a Atos Danosos ocorridos durante a vigência."),
    ("Reclamação", "procedimento judicial, arbitral ou administrativo, ou notificação escrita, em que se atribua "
     "ao Segurado a responsabilidade por um Ato Danoso."),
    ("Segurado", "o Administrador, o empregado em cargo de gestão quando corréu com Administrador e as demais "
     "pessoas indicadas nas Condições Particulares."),
    ("Sociedade", "a pessoa jurídica Tomadora do seguro e suas Subsidiárias relacionadas no Anexo I."),
    ("Subsidiária", "sociedade na qual a Tomadora detenha, direta ou indiretamente, mais de 50% do capital "
     "votante, ou o direito de eleger a maioria dos administradores."),
    ("Tomador", "a pessoa jurídica que contrata o seguro em favor dos Segurados e é responsável pelo pagamento "
     "do prêmio."),
    ("Valores Mobiliários", "ações, debêntures, bônus de subscrição e demais títulos definidos na legislação "
     "do mercado de capitais, emitidos pela Sociedade."),
]

COBERTURAS_BASICAS = [
    ("Cobertura A – Pagamento direto aos Segurados", "A Seguradora pagará, em nome do Segurado, as Perdas decorrentes "
     "de Reclamações por Atos Danosos quando a Sociedade não o indenizar, por impedimento legal ou insolvência.",
     [("Condição", "a cobertura aplica-se ainda que a Sociedade esteja em recuperação judicial ou falência."),
      ("Prioridade", "esta cobertura tem prioridade de pagamento sobre as demais, conforme a Cláusula de Ordem de Pagamento.")]),
    ("Cobertura B – Reembolso à Sociedade", "A Seguradora reembolsará a Sociedade pelos valores que esta tenha "
     "pago ao Segurado, a título de indenização por Perdas cobertas, quando permitido por lei ou pelo estatuto.",
     [("Franquia", "aplica-se a franquia indicada nas Condições Particulares para esta cobertura.")]),
    ("Cobertura C – Reclamações contra a Sociedade", "Quando contratada, a Seguradora pagará as Perdas da própria "
     "Sociedade decorrentes de Reclamações relativas a Valores Mobiliários por ela emitidos.",
     [("Abrangência", "a cobertura compreende Reclamações de investidores, acionistas e órgãos reguladores do "
       "mercado de capitais.")]),
]

COBERTURAS_ADICIONAIS = [
    ("Custos Emergenciais", "custos de defesa incorridos antes da anuência da Seguradora, quando a urgência "
     "impedir a consulta prévia, limitados ao sublimite das Condições Particulares."),
    ("Penhora on-line e bloqueio de bens", "valores bloqueados judicialmente em contas ou bens do Segurado em "
     "razão de Reclamação coberta, até a decisão definitiva."),
    ("Custos de Publicidade", "despesas com assessoria de comunicação para mitigar danos à reputação do Segurado "
     "decorrentes de Reclamação coberta."),
    ("Extensão a Cônjuges, Herdeiros e Espólio", "Reclamações contra cônjuges, companheiros, herdeiros ou espólio "
     "do Segurado exclusivamente em razão de Ato Danoso deste."),
    ("Investigações", "custos de defesa em inquéritos e investigações conduzidos por autoridades e órgãos "
     "reguladores, ainda que não exista acusação formal."),
]

RISCOS_EXCLUIDOS = [
    ("Atos dolosos ou fraudulentos", "Reclamações decorrentes de atos dolosos, fraudulentos ou praticados com a "
     "intenção de obter vantagem pessoal indevida.",
     "a exclusão só se aplica após decisão judicial ou arbitral definitiva que reconheça o ato; até lá, os Custos "
     "de Defesa são adiantados."),
    ("Danos corporais e materiais", "Reclamações por danos corporais, morte, doença, danos materiais ou destruição "
     "de bens.", "ficam cobertos os Custos de Defesa em reclamações de acionistas relacionadas a esses eventos."),
    ("Reclamações prévias e circunstâncias conhecidas", "Reclamações ou circunstâncias conhecidas pelos Segurados "
     "antes do início de vigência, ou já notificadas em apólice anterior.", None),
    ("Multas e penalidades", "Multas, penalidades e tributos impostos ao Segurado.",
     "ficam cobertas as multas civis e administrativas aplicadas ao Segurado quando o reembolso for permitido "
     "pela legislação e contratada a cobertura adicional correspondente."),
    ("Poluição ambiental", "Reclamações relativas a poluição ou contaminação ambiental.",
     "ficam cobertos os Custos de Defesa do Segurado, até o sublimite das Condições Particulares."),
    ("Segurado contra Segurado", "Reclamações movidas por um Segurado ou pela Sociedade contra outro Segurado.",
     "não se aplica a ações derivativas de acionistas minoritários, a reclamações de ex-administradores e às "
     "movidas por administrador judicial em recuperação ou falência."),
    ("Remuneração indevida", "Reclamações por remuneração, gratificação ou benefício recebido pelo Segurado sem "
     "a aprovação dos órgãos societários competentes.", None),
    ("Guerra e terrorismo", "Perdas decorrentes de guerra, invasão, atos de inimigo estrangeiro, rebelião ou "
     "terrorismo.", None),
    ("Contratos", "Reclamações por descumprimento de obrigação contratual assumida pela Sociedade.",
     "a exclusão não se aplica à responsabilidade pessoal do Segurado que decorra de Ato Danoso na gestão do contrato."),
]


def clausulas_gerais(p: dict) -> list[tuple[str, list]]:
    """Capítulos das condições gerais. `p`: prazos e percentuais de cada seguradora."""
    exc = [e for e in RISCOS_EXCLUIDOS if e[0] not in p.get("sem_exclusoes", [])] + p.get("exclusoes_extra", [])
    return [
        ("CLÁUSULA 1 – OBJETO DO SEGURO", [
            ("1.1", f"Este seguro garante ao Segurado, até o Limite Máximo de Garantia, o pagamento das Perdas "
                    f"decorrentes de Reclamações apresentadas durante a vigência ou o Prazo Complementar, por Atos "
                    f"Danosos praticados no exercício de suas funções."),
            ("1.2", "A cobertura é concedida à base de reclamações (claims made): importa a data em que a Reclamação "
                    "é apresentada, e não a data do Ato Danoso, observado o Período de Retroatividade."),
            ("1.3", "As Condições Particulares prevalecem sobre as Especiais, e estas sobre as Gerais."),
        ]),
        ("CLÁUSULA 2 – DEFINIÇÕES", [(f"2.{i}", f"{t}: {d}") for i, (t, d) in enumerate(DEFINICOES, 1)]),
        ("CLÁUSULA 3 – COBERTURAS BÁSICAS", [
            item for i, (t, d, subs) in enumerate(COBERTURAS_BASICAS, 1)
            for item in [(f"3.{i}", f"{t}: {d}")] + [(f"3.{i}.{j}", f"{st}: {sd}") for j, (st, sd) in enumerate(subs, 1)]
        ]),
        ("CLÁUSULA 4 – COBERTURAS ADICIONAIS", [("4.0", "Aplicam-se somente quando indicadas nas Condições Particulares, "
                                                         "com os sublimites ali previstos.")] +
         [(f"4.{i}", f"{t}: {d}") for i, (t, d) in enumerate(COBERTURAS_ADICIONAIS, 1)]),
        ("CLÁUSULA 5 – RISCOS EXCLUÍDOS", [("5.0", "Este seguro não cobre Perdas decorrentes de:")] + [
            item for i, (t, d, ex) in enumerate(exc, 1)
            for item in [(f"5.{i}", f"{t}: {d}")] + ([(f"5.{i}.1", f"Exceção: {ex}")] if ex else [])
        ]),
        ("CLÁUSULA 6 – FRANQUIA", [
            ("6.1", "A franquia prevista nas Condições Particulares será deduzida de cada Reclamação, incluindo os "
                    "Custos de Defesa, e ficará a cargo da Sociedade."),
            ("6.2", "Não se aplica franquia à Cobertura A – Pagamento direto aos Segurados."),
            ("6.3", "Reclamações decorrentes do mesmo Ato Danoso ou de Atos Danosos relacionados serão consideradas "
                    "uma única Reclamação, com uma única franquia."),
        ]),
        ("CLÁUSULA 7 – LIMITE MÁXIMO DE GARANTIA", [
            ("7.1", "O Limite Máximo de Garantia é agregado e único para todas as coberturas, Segurados e Reclamações "
                    "do período de vigência, salvo limites adicionais expressamente previstos."),
            ("7.2", f"Os Custos de Defesa {p['custos_lmg']}."),
            ("7.3", "Os sublimites das coberturas adicionais integram o Limite Máximo de Garantia e não o ampliam."),
        ]),
        ("CLÁUSULA 8 – RETROATIVIDADE E PRAZO COMPLEMENTAR", [
            ("8.1", "Estão cobertos os Atos Danosos ocorridos a partir da data de retroatividade indicada nas "
                    "Condições Particulares."),
            ("8.2", f"Em caso de não renovação, o Tomador poderá contratar Prazo Complementar de {p['complementar']}, "
                    f"mediante solicitação em até 30 dias do fim da vigência."),
            ("8.3", f"Será concedido Prazo Suplementar gratuito de {p['suplementar']}, que não se soma ao Prazo "
                    f"Complementar contratado."),
        ]),
        ("CLÁUSULA 9 – AVISO DE RECLAMAÇÃO", [
            ("9.1", f"O Segurado deverá comunicar à Seguradora qualquer Reclamação em até {p['aviso']} dias do seu "
                    f"conhecimento, e em qualquer caso antes do fim do Prazo Complementar."),
            ("9.2", "O Segurado poderá notificar circunstâncias que possam originar Reclamação; a Reclamação "
                    "posterior será considerada apresentada na data da notificação."),
            ("9.3", "O descumprimento dos prazos só afasta a indenização se causar prejuízo à Seguradora."),
        ]),
        ("CLÁUSULA 10 – ADIANTAMENTO DE CUSTOS DE DEFESA", [
            ("10.1", f"A Seguradora adiantará os Custos de Defesa em até {p['adiantamento']} dias da apresentação "
                     f"dos comprovantes, mesmo antes de definida a cobertura."),
            ("10.2", "Se ficar comprovado que a Perda não estava coberta, os valores adiantados deverão ser "
                     "devolvidos pelo Segurado."),
            ("10.3", "A escolha dos advogados cabe ao Segurado, com anuência da Seguradora, que não poderá ser "
                     "negada sem justificativa."),
        ]),
        ("CLÁUSULA 11 – ALOCAÇÃO", [
            ("11.1", f"Em Reclamações que envolvam partes cobertas e não cobertas, {p['alocacao']}."),
            ("11.2", "Na falta de acordo sobre a alocação, a questão será submetida a arbitragem, sem prejuízo do "
                     "adiantamento dos Custos de Defesa."),
        ]),
        ("CLÁUSULA 12 – ORDEM DE PAGAMENTO", [
            ("12.1", "Havendo Perdas simultâneas, a Seguradora pagará primeiro as Perdas da Cobertura A, depois as "
                     "da Cobertura B e, por último, as da Cobertura C."),
        ]),
        ("CLÁUSULA 13 – SUB-ROGAÇÃO", [
            ("13.1", "Paga a indenização, a Seguradora sub-roga-se nos direitos do Segurado contra terceiros "
                     "responsáveis, exceto contra outro Segurado, salvo em caso de dolo reconhecido."),
        ]),
        ("CLÁUSULA 14 – PERDA DE DIREITOS", [
            ("14.1", "O Segurado perderá o direito à indenização se agravar intencionalmente o risco, fizer "
                     "declarações inexatas que influam na aceitação da proposta ou deixar de comunicar a Reclamação."),
            ("14.2", "Não-imputação: as declarações e o conhecimento de um Segurado não serão imputados aos demais "
                     "para fins de perda de direitos."),
        ]),
        ("CLÁUSULA 15 – CANCELAMENTO", [
            ("15.1", f"O seguro poderá ser cancelado pelo Tomador a qualquer tempo, com devolução do prêmio "
                     f"{p['cancelamento']}."),
            ("15.2", "Em caso de alteração de controle da Sociedade durante a vigência, a cobertura permanece para "
                     "Atos Danosos anteriores à alteração, cessando para os posteriores."),
        ]),
        ("CLÁUSULA 16 – FORO", [
            ("16.1", "Fica eleito o foro do domicílio do Segurado para dirimir questões oriundas deste contrato."),
        ]),
    ]


def condicoes_especiais(nome: str, p: dict) -> list[tuple[str, str]]:
    """Condições especiais de uma cobertura (texto padrão parametrizado pelo nome da cobertura)."""
    return [
        ("1", f"Objeto: esta Condição Especial garante, nos termos das Condições Gerais, a cobertura de {nome}, "
              f"quando indicada no Quadro de Coberturas das Condições Particulares."),
        ("2", f"Riscos cobertos: Perdas decorrentes de Reclamações relacionadas a {nome.lower()}, apresentadas durante "
              f"a vigência ou o Prazo Complementar, por Atos Danosos ocorridos após a data de retroatividade."),
        ("3", "Riscos excluídos: além das exclusões da Cláusula 5 das Condições Gerais, não estão cobertas Perdas "
              "já indenizadas por outra cobertura desta apólice, nem valores sem relação direta com a Reclamação."),
        ("4", "Limite: o sublimite desta cobertura é o indicado no Quadro de Coberturas; ele integra o Limite "
              "Máximo de Garantia e não o amplia."),
        ("5", "Franquia: aplica-se a franquia indicada no Quadro de Coberturas, por Reclamação; não havendo "
              "indicação, a cobertura é concedida sem franquia."),
        ("6", f"Documentos para indenização: aviso de Reclamação em até {p['aviso']} dias, cópia integral da "
              f"Reclamação, comprovantes das despesas e manifestação do Segurado sobre os fatos."),
        ("7", "Ratificação: permanecem inalteradas as demais disposições das Condições Gerais que não tenham sido "
              "expressamente modificadas por esta Condição Especial."),
    ]


QUESTIONARIO = [
    "A Sociedade possui ações negociadas em bolsa no Brasil ou no exterior?",
    "Há previsão de oferta pública de Valores Mobiliários nos próximos 12 meses?",
    "A Sociedade realizou fusão, aquisição ou cisão nos últimos 24 meses?",
    "Algum Administrador responde a processo relacionado à sua gestão?",
    "Existe Reclamação, investigação ou circunstância conhecida que possa gerar Reclamação?",
    "A Sociedade possui comitê de auditoria e auditoria independente?",
    "As demonstrações financeiras dos últimos 3 anos tiveram ressalvas?",
    "A Sociedade está em recuperação judicial ou extrajudicial?",
    "Há operações relevantes nos Estados Unidos ou no Canadá?",
    "A Sociedade possui programa de integridade (compliance) formalizado?",
    "Houve demissão de Administrador por justa causa nos últimos 3 anos?",
    "A Sociedade trata dados pessoais em larga escala?",
    "Existem passivos ambientais conhecidos?",
    "Houve autuação de órgão regulador nos últimos 5 anos?",
    "Qual o número de empregados e o faturamento anual consolidado?",
]


# ─── Documentos longos ───────────────────────────────────────────────────────
LONGAS = {
    "equinocio": dict(
        arquivo="apolice_equinocio_do.pdf",
        seguradora="Equinócio Seguros S.A. (FICTÍCIA)", numero="4400.771205",
        susep="15414.000004/2026-44 (fictício)", tomador="Grupo Varanda Energia S.A. (fictícia)",
        cnpj="00.000.004/0001-44", corretor="Norte Sul Corretora de Seguros Ltda. (fictícia)",
        vig=("15/04/2026", "15/04/2027"), lmg="R$ 50.000.000,00", premio="R$ 412.800,00",
        base="À base de reclamações (claims made), com notificação de circunstâncias",
        retro="15/04/2016", complementar="36 meses, mediante pagamento de prêmio adicional",
        territorio="Mundial", custos="Fora do LMG, com adiantamento em até 10 dias",
        coberturas=[
            ("Cobertura A – Pagamento direto aos Segurados", "R$ 50.000.000,00", "Não há"),
            ("Cobertura B – Reembolso à Sociedade", "R$ 50.000.000,00", "R$ 200.000,00"),
            ("Custos de Defesa", "R$ 50.000.000,00", "Não há"),
            ("Custos Emergenciais", "R$ 5.000.000,00", "Não há"),
            ("Penhora on-line e bloqueio de bens", "R$ 10.000.000,00", "Não há"),
            ("Custos de Publicidade", "R$ 2.000.000,00", "Não há"),
            ("Extensão a Cônjuges, Herdeiros e Espólio", "R$ 50.000.000,00", "Não há"),
            ("Investigações", "R$ 10.000.000,00", "R$ 50.000,00"),
            ("Responsabilidade Ambiental – Custos de Defesa", "R$ 5.000.000,00", "R$ 100.000,00"),
            ("Limite adicional para Administradores independentes (Lado A)", "R$ 5.000.000,00", "Não há"),
        ],
        franquias=[("Reembolso à Sociedade (Cobertura B)", "R$ 200.000,00"),
                   ("Investigações", "R$ 50.000,00"), ("Reclamações ambientais", "R$ 100.000,00")],
        segurados=["Diretores estatutários e conselheiros de administração, eleitos ou nomeados",
                   "Membros do Conselho Fiscal e de comitês de assessoramento",
                   "Empregados em cargo de gestão, quando corréus com Administradores",
                   "Administradores das Subsidiárias relacionadas no Anexo I",
                   "Representantes indicados pela Sociedade em conselhos de entidades sem fins lucrativos"],
        exclusoes_particulares=[("Obrigações regulatórias do setor elétrico", "Reclamações por descumprimento de "
                                 "metas de continuidade fixadas pelo órgão regulador do setor elétrico, exceto quanto "
                                 "aos Custos de Defesa.")],
        clausulas_particulares=["Custos de defesa fora do LMG: pagos em adição ao Limite Máximo de Garantia.",
                                "Não-imputação ampla: aplicável a declarações da proposta e a conhecimento prévio.",
                                "Renúncia à sub-rogação contra Administradores independentes."],
        gerais=dict(custos_lmg="são pagos em adição ao Limite Máximo de Garantia, quando assim previsto nas Condições "
                               "Particulares; caso contrário, integram o limite",
                    complementar="36 meses", suplementar="90 dias", aviso=60, adiantamento=10,
                    alocacao="a Seguradora arcará com 100% dos Custos de Defesa e com a parcela de Perdas "
                              "atribuível aos Segurados", cancelamento="proporcional ao prazo decorrido"),
        subsidiarias=[("Varanda Geração Ltda. (fictícia)", "100%"), ("Varanda Transmissão S.A. (fictícia)", "80%"),
                      ("Varanda Comercializadora Ltda. (fictícia)", "100%"), ("Solar Pampa Energia Ltda. (fictícia)", "51%")],
    ),
    "meridiana": dict(
        arquivo="apolice_meridiana_do.pdf",
        seguradora="Meridiana Seguradora S.A. (FICTÍCIA)", numero="ME-2026-000517",
        susep="15414.000005/2026-55 (fictício)", tomador="Lumen Varejo Digital S.A. (fictícia)",
        cnpj="00.000.005/0001-55", corretor="Atlântica Corretora de Seguros Ltda. (fictícia)",
        vig=("01/07/2026", "01/07/2027"), lmg="R$ 80.000.000,00", premio="R$ 736.000,00",
        base="À base de reclamações (claims made)", retro="Ilimitada",
        complementar="72 meses, mediante pagamento de prêmio adicional", territorio="Mundial, inclusive Estados Unidos e Canadá",
        custos="Dentro do LMG, com adiantamento em até 5 dias",
        coberturas=[
            ("Cobertura A – Pagamento direto aos Segurados", "R$ 80.000.000,00", "Não há"),
            ("Cobertura B – Reembolso à Sociedade", "R$ 80.000.000,00", "R$ 500.000,00"),
            ("Cobertura C – Reclamações contra a Sociedade (Valores Mobiliários)", "R$ 60.000.000,00", "R$ 1.000.000,00"),
            ("Custos de Defesa", "R$ 80.000.000,00", "Não há"),
            ("Investigações de órgãos reguladores (CVM e SEC)", "R$ 20.000.000,00", "Não há"),
            ("Custos Emergenciais", "R$ 8.000.000,00", "Não há"),
            ("Multas civis e administrativas", "R$ 10.000.000,00", "R$ 100.000,00"),
            ("Custos de Publicidade e Gerenciamento de Crise", "R$ 3.000.000,00", "Não há"),
            ("Extensão a Cônjuges, Herdeiros e Espólio", "R$ 80.000.000,00", "Não há"),
            ("Oferta pública de Valores Mobiliários (IPO/follow-on)", "R$ 30.000.000,00", "R$ 1.000.000,00"),
            ("Responsabilidade por dados pessoais (LGPD) – Custos de Defesa", "R$ 5.000.000,00", "R$ 150.000,00"),
        ],
        franquias=[("Reembolso à Sociedade (Cobertura B)", "R$ 500.000,00"),
                   ("Reclamações contra a Sociedade (Cobertura C)", "R$ 1.000.000,00"),
                   ("Reclamações nos Estados Unidos e Canadá", "R$ 2.500.000,00"),
                   ("Reclamações relacionadas à LGPD", "R$ 150.000,00")],
        segurados=["Diretores estatutários e conselheiros de administração, eleitos ou nomeados",
                   "Membros do Conselho Fiscal, do Comitê de Auditoria e demais comitês estatutários",
                   "Diretor de Relações com Investidores e Diretor de Governança de Dados",
                   "Empregados em cargo de gestão, quando corréus com Administradores",
                   "Administradores das Subsidiárias relacionadas no Anexo I"],
        exclusoes_particulares=[("Exclusão de reclamações nos EUA por grandes acionistas", "Reclamações movidas nos "
                                 "Estados Unidos ou no Canadá por acionista titular de mais de 10% do capital, exceto "
                                 "ações derivativas sem participação ativa da Sociedade.")],
        clausulas_particulares=["Cobertura C restrita a Reclamações relativas a Valores Mobiliários.",
                                "Limite de Custos de Defesa nos EUA e Canadá: 40% do LMG.",
                                "Ordem de pagamento: prioridade à Cobertura A, depois B e por último C.",
                                "Cláusula de alocação: 80% dos custos de defesa alocados aos Segurados em reclamações mistas."],
        gerais=dict(custos_lmg="integram o Limite Máximo de Garantia e o reduzem", complementar="72 meses",
                    suplementar="60 dias", aviso=30, adiantamento=5,
                    alocacao="os Custos de Defesa serão alocados 80% aos Segurados e 20% à Sociedade, e as demais "
                              "Perdas conforme a exposição relativa de cada parte",
                    cancelamento="de acordo com a tabela de prazo curto da SUSEP",
                    exclusoes_extra=[("Informações privilegiadas", "Reclamações decorrentes de negociação de Valores "
                                      "Mobiliários com uso de informação privilegiada pelo Segurado.",
                                      "ficam cobertos os Custos de Defesa até a decisão definitiva."),
                                     ("Legislação trabalhista e previdenciária", "Reclamações baseadas em legislação "
                                      "trabalhista, previdenciária ou de planos de pensão.",
                                      "cobertas as reclamações por assédio e discriminação contra Administradores.")]),
        subsidiarias=[("Lumen Logística Ltda. (fictícia)", "100%"), ("Lumen Pagamentos S.A. (fictícia)", "100%"),
                      ("Lumen Marketplace Ltda. (fictícia)", "100%"), ("Lumen Tecnologia Inc. (fictícia, EUA)", "100%"),
                      ("Casa Lumen Móveis Ltda. (fictícia)", "70%"), ("Lumen Crédito S.A. (fictícia)", "60%")],
    ),
    "pampa": dict(
        arquivo="apolice_pampa_digitalizada.pdf", digitalizada=True,
        seguradora="Pampa Seguros Gerais S.A. (FICTÍCIA)", numero="PS-88.2026.1142",
        susep="15414.000006/2026-66 (fictício)", tomador="Cooperativa Agroindustrial Coxilha (fictícia)",
        cnpj="00.000.006/0001-66", corretor="Campanha Corretora de Seguros Ltda. (fictícia)",
        vig=("01/08/2026", "01/08/2027"), lmg="R$ 8.000.000,00", premio="R$ 58.400,00",
        base="À base de reclamações (claims made)", retro="01/08/2023",
        complementar="12 meses, mediante prêmio adicional", territorio="Brasil",
        custos="Dentro do LMG, reembolso após aprovação prévia da Seguradora",
        coberturas=[
            ("Cobertura A – Pagamento direto aos Segurados", "R$ 8.000.000,00", "Não há"),
            ("Cobertura B – Reembolso à Sociedade", "R$ 8.000.000,00", "R$ 80.000,00"),
            ("Custos de Defesa", "R$ 8.000.000,00", "Não há"),
            ("Penhora on-line e bloqueio de bens", "R$ 800.000,00", "Não há"),
            ("Extensão a Cônjuges, Herdeiros e Espólio", "R$ 8.000.000,00", "Não há"),
        ],
        franquias=[("Reembolso à Sociedade (Cobertura B)", "R$ 80.000,00"), ("Reclamações trabalhistas", "R$ 40.000,00")],
        segurados=["Conselheiros de administração e diretores eleitos pela Assembleia Geral",
                   "Membros do Conselho Fiscal da Cooperativa"],
        exclusoes_particulares=[("Crédito rural", "Reclamações decorrentes de inadimplência em operações de crédito "
                                 "rural contratadas pela Cooperativa.")],
        clausulas_particulares=["Consentimento prévio: acordos dependem de anuência escrita da Seguradora.",
                                "Seguro de cooperativa: aplicam-se as regras da Lei 5.764/1971 quanto aos órgãos sociais."],
        gerais=dict(custos_lmg="integram o Limite Máximo de Garantia e o reduzem", complementar="12 meses",
                    suplementar="30 dias", aviso=15, adiantamento=30,
                    alocacao="os Custos de Defesa serão alocados proporcionalmente entre partes cobertas e não cobertas",
                    cancelamento="de acordo com a tabela de prazo curto da SUSEP",
                    sem_exclusoes=["Remuneração indevida", "Guerra e terrorismo", "Contratos"]),
        capitulos=range(0, 11),  # documento menor: só os 11 primeiros capítulos das condições gerais
        subsidiarias=[],
    ),
}


def _styles():
    ss = getSampleStyleSheet()
    return dict(
        h1=ParagraphStyle("h1", parent=ss["Title"], fontSize=13, leading=16),
        h2=ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11, spaceBefore=12, spaceAfter=4),
        body=ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=12.5, spaceAfter=3),
        sub=ParagraphStyle("sub", parent=ss["BodyText"], fontSize=9.5, leading=12.5, leftIndent=14, spaceAfter=3),
        small=ParagraphStyle("s", parent=ss["BodyText"], fontSize=8, textColor=colors.grey),
    )


def _tabela(linhas, larguras):
    t = Table(linhas, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _gerais(el: list, st: dict, p: dict, capitulos=None) -> None:
    caps = clausulas_gerais(p)
    for i, (titulo, itens) in enumerate(caps):
        if capitulos is not None and i not in capitulos:
            continue
        el.append(Paragraph(titulo, st["h2"]))
        for num, texto in itens:
            if num.endswith(".0"):
                el.append(Paragraph(texto, st["body"]))
            else:
                style = st["sub"] if num.count(".") >= 2 else st["body"]
                el.append(Paragraph(f"{num} {texto}", style))


def build_apolice_longa(d: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=1.8 * cm, title=f"Apólice D&O {d['numero']} (fictícia)")
    st = _styles()
    el = [Paragraph(d["seguradora"].upper(), st["h1"]),
          Paragraph("APÓLICE DE SEGURO DE RESPONSABILIDADE CIVIL DE ADMINISTRADORES E DIRETORES – D&amp;O", st["h1"]),
          Paragraph("Documento fictício gerado para fins acadêmicos. Não possui validade jurídica.", st["small"]),
          Paragraph("DADOS DA APÓLICE", st["h2"])]
    for k, v in [("Seguradora", d["seguradora"]), ("Apólice nº", d["numero"]),
                 ("Produto", "RC D&amp;O – Responsabilidade Civil de Administradores"), ("Processo SUSEP nº", d["susep"]),
                 ("Tomador", d["tomador"]), ("CNPJ", d["cnpj"]), ("Corretor", d["corretor"]),
                 ("Vigência", f"das 24h de {d['vig'][0]} às 24h de {d['vig'][1]}"),
                 ("Limite Máximo de Garantia (LMG)", f"{d['lmg']} (agregado, por reclamação e no período)"),
                 ("Prêmio Total", f"{d['premio']} (incluso IOF)"), ("Base de cobertura", d["base"]),
                 ("Data de retroatividade", d["retro"]), ("Prazo complementar", d["complementar"]),
                 ("Territorialidade", d["territorio"]), ("Tratamento dos custos de defesa", d["custos"])]:
        el.append(Paragraph(f"{k}: {v}", st["body"]))
    el += [Paragraph("QUADRO DE COBERTURAS E LIMITES", st["h2"]),
           _tabela([["Cobertura", "Limite", "Franquia"]] + [list(c) for c in d["coberturas"]], [9.3 * cm, 4 * cm, 3.7 * cm]),
           Paragraph("FRANQUIAS", st["h2"])]
    el += [Paragraph(f"{i}. {k}: {v} por reclamação", st["body"]) for i, (k, v) in enumerate(d["franquias"], 1)]
    el.append(Paragraph("SEGURADOS", st["h2"]))
    el += [Paragraph(f"{i}. {s}", st["body"]) for i, s in enumerate(d["segurados"], 1)]
    el.append(Paragraph("EXCLUSÕES ESPECÍFICAS", st["h2"]))
    el.append(Paragraph("Além dos riscos excluídos na Cláusula 5 das Condições Gerais, este seguro não cobre:", st["body"]))
    el += [Paragraph(f"{i}. {t}: {x}", st["body"]) for i, (t, x) in enumerate(d["exclusoes_particulares"], 1)]
    el.append(Paragraph("CLÁUSULAS PARTICULARES", st["h2"]))
    el += [Paragraph(f"{i}. {c}", st["body"]) for i, c in enumerate(d["clausulas_particulares"], 1)]

    el += [PageBreak(), Paragraph("CONDIÇÕES GERAIS DO SEGURO D&amp;O", st["h1"]),
           Paragraph(f"{d['seguradora']} – aplicáveis a esta apólice.", st["small"])]
    _gerais(el, st, d["gerais"], d.get("capitulos"))

    # Uma Condição Especial por cobertura contratada (exceto as básicas, já descritas na Cláusula 3)
    especiais = [c[0] for c in d["coberturas"] if not c[0].startswith(("Cobertura A", "Cobertura B", "Custos de Defesa"))]
    if especiais:
        el += [PageBreak(), Paragraph("CONDIÇÕES ESPECIAIS", st["h1"])]
        for nome in especiais:
            el.append(Paragraph(f"CONDIÇÕES ESPECIAIS – {nome.upper()}", st["h2"]))
            el += [Paragraph(f"{n}. {t}", st["body"]) for n, t in condicoes_especiais(nome, d["gerais"])]

    if d.get("subsidiarias"):
        el += [PageBreak(), Paragraph("ANEXO I – SOCIEDADES COBERTAS", st["h2"]),
               _tabela([["Sociedade", "Participação da Tomadora"]] + [list(s) for s in d["subsidiarias"]],
                       [11 * cm, 6 * cm])]
    el += [Spacer(1, 12), Paragraph("DISPOSIÇÕES FINAIS", st["h2"]), Paragraph(
        "As Condições Gerais, Especiais e Particulares integram esta apólice. Em caso de divergência, prevalecem as "
        "Condições Particulares.", st["small"])]
    doc.build(el)
    return buf.getvalue()


def build_condicoes_gerais() -> bytes:
    """Documento que NÃO é uma apólice: condições gerais completas (testa a triagem e volumes grandes)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=1.8 * cm, title="Condições Gerais D&O – Equinócio (fictícias)")
    st = _styles()
    el = [Paragraph("CONDIÇÕES GERAIS – SEGURO DE RESPONSABILIDADE CIVIL DE ADMINISTRADORES E DIRETORES (D&amp;O)", st["h1"]),
          Paragraph("EQUINÓCIO SEGUROS S.A. (FICTÍCIA) · Processo SUSEP nº 15414.000004/2026-44 (fictício) · Versão 3.2",
                    st["small"]),
          Paragraph("Documento fictício gerado para fins acadêmicos. Não possui validade jurídica.", st["small"]),
          Paragraph("ÍNDICE", st["h2"])]
    p = LONGAS["equinocio"]["gerais"] | {"exclusoes_extra": LONGAS["meridiana"]["gerais"]["exclusoes_extra"]}
    for titulo, _ in clausulas_gerais(p):
        el.append(Paragraph(titulo.title(), st["body"]))
    el.append(PageBreak())
    _gerais(el, st, p)
    extras = [
        ("CLÁUSULA 17 – OBRIGAÇÕES DO SEGURADO", [
            ("17.1", "Colaborar com a Seguradora na defesa, fornecendo documentos e informações solicitados."),
            ("17.2", "Não admitir responsabilidade, fazer acordos ou assumir obrigações sem anuência da Seguradora."),
            ("17.3", "Adotar as medidas razoáveis para reduzir as consequências do Ato Danoso."),
            ("17.4", "Informar à Seguradora, durante a vigência, alterações relevantes no risco, como fusões, "
                     "aquisições, emissão de Valores Mobiliários e mudança de controle."),
        ]),
        ("CLÁUSULA 18 – LIQUIDAÇÃO DE SINISTROS", [
            ("18.1", "A Seguradora pagará a indenização em até 30 dias da entrega de todos os documentos necessários."),
            ("18.2", "Documentos básicos: aviso de Reclamação, cópia da Reclamação, contratos de honorários, "
                     "comprovantes de despesas e, quando houver, sentença, laudo ou acordo."),
            ("18.2.1", "A Seguradora poderá solicitar documentos complementares uma única vez, suspendendo o prazo "
                       "até o seu recebimento."),
            ("18.3", "O não pagamento no prazo sujeita a Seguradora a atualização monetária e juros de mora."),
        ]),
        ("CLÁUSULA 19 – CONCORRÊNCIA DE APÓLICES", [
            ("19.1", "Havendo outros seguros para o mesmo risco, esta apólice responderá proporcionalmente, salvo "
                     "quando contratada como apólice de excesso."),
            ("19.2", "Para a Cobertura A, esta apólice atuará em excesso de qualquer outro seguro válido e cobrável."),
        ]),
        ("CLÁUSULA 20 – PRESCRIÇÃO", [
            ("20.1", "Os prazos prescricionais são os previstos no Código Civil para as relações de seguro."),
        ]),
        ("CLÁUSULA 21 – DISPOSIÇÕES GERAIS", [
            ("21.1", "A aceitação do seguro está sujeita à análise do risco pela Seguradora."),
            ("21.2", "O registro deste plano na SUSEP não implica incentivo ou recomendação à sua comercialização."),
            ("21.3", "O Segurado poderá consultar a situação cadastral do corretor e da Seguradora no site da SUSEP."),
        ]),
    ]
    for titulo, itens in extras:
        el.append(Paragraph(titulo, st["h2"]))
        for num, texto in itens:
            el.append(Paragraph(f"{num} {texto}", st["sub"] if num.count(".") >= 2 else st["body"]))
    el += [PageBreak(), Paragraph("CONDIÇÕES ESPECIAIS", st["h1"])]
    for nome, *_ in COBERTURAS_BASICAS[2:] + [(c[0],) for c in COBERTURAS_ADICIONAIS]:
        el.append(Paragraph(f"CONDIÇÕES ESPECIAIS – {nome.upper()}", st["h2"]))
        el += [Paragraph(f"{n}. {t}", st["body"]) for n, t in condicoes_especiais(nome, p)]
    el += [PageBreak(), Paragraph("ANEXO – QUESTIONÁRIO DE AVALIAÇÃO DE RISCO", st["h2"]),
           Paragraph("A proposta deve ser acompanhada deste questionário, respondido e assinado pelo representante "
                     "legal da Sociedade. Respostas inexatas podem acarretar a perda de direitos (Cláusula 14).", st["body"])]
    el += [Paragraph(f"{i}. {q} Resposta: ____________________________", st["body"]) for i, q in enumerate(QUESTIONARIO, 1)]
    el += [PageBreak(), Paragraph("GLOSSÁRIO COMPLEMENTAR", st["h2"])]
    for t, d in DEFINICOES:
        el.append(KeepTogether([Paragraph(f"<b>{t}.</b> {d} Este termo, quando grafado com inicial maiúscula, "
                                          f"tem o significado aqui atribuído em todas as Condições.", st["body"])]))
    doc.build(el)
    return buf.getvalue()
