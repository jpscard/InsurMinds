"""Extração e classificação por regras (modo offline, sem LLM).

Usado quando LLM_PROVIDER=offline, para demonstrar a interface e rodar testes
sem chave de API. Funciona razoavelmente em documentos com rótulos explícitos
("Limite Máximo de Garantia: R$ ...") e seções com títulos em maiúsculas,
mas é frágil diante de layouts diferentes — é exatamente a limitação que o
Agente de Extração com LLM resolve.
"""
from __future__ import annotations

import re

from ..schema import ApoliceDO, Cobertura, Exclusao, Franquia, Identificacao, Valor
from ..utils import norm_key, normalize_date, parse_money

_FIELDS = {
    "seguradora": [r"seguradora"],
    "numero_apolice": [r"ap[óo]lice\s*(?:n[º°o.]*|n[úu]mero)"],
    "produto": [r"produto", r"ramo"],
    "processo_susep": [r"processo\s+susep(?:\s*n[º°o.]*)?"],
    "tomador": [r"tomador(?:/segurado)?", r"sociedade\s+tomadora"],
    "cnpj_tomador": [r"cnpj"],
    "corretor": [r"corretor(?:a)?"],
    "lmg": [r"limite\s+m[áa]ximo\s+de\s+garantia(?:\s*\(lmg\))?", r"lmg", r"limite\s+agregado"],
    "premio": [r"pr[êe]mio\s+total", r"pr[êe]mio\s+l[íi]quido", r"pr[êe]mio"],
    "base": [r"base\s+de\s+cobertura", r"forma\s+de\s+contrata[çc][ãa]o"],
    "retro": [r"data\s+(?:limite\s+)?de\s+retroatividade", r"retroatividade"],
    "complementar": [r"prazo\s+complementar", r"per[íi]odo\s+complementar", r"prazo\s+suplementar"],
    "territorio": [r"territorialidade", r"[âa]mbito\s+geogr[áa]fico", r"abrang[êe]ncia\s+territorial"],
    "custos_defesa": [r"custos\s+de\s+defesa\s*\(tratamento\)", r"tratamento\s+dos\s+custos\s+de\s+defesa"],
}

_DATE = r"\d{2}/\d{2}/\d{4}"


def _field(text: str, key: str) -> str | None:
    for label in _FIELDS[key]:
        m = re.search(rf"^\s*{label}\s*[:\-–]\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def _valor(texto: str | None) -> Valor | None:
    if not texto:
        return None
    v, moeda = parse_money(texto)
    return Valor(valor=v, moeda=moeda or "BRL", texto=texto)


def _sections(text: str) -> list[tuple[str, list[str]]]:
    """Divide o texto em seções usando linhas em MAIÚSCULAS como títulos."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("[Página"):
            continue
        letters = [c for c in line if c.isalpha()]
        is_heading = (len(letters) >= 6 and sum(c.isupper() for c in letters) / len(letters) > 0.85
                      and len(line) < 90 and "R$" not in line)
        if is_heading:
            sections.append((line, []))
        else:
            sections[-1][1].append(line)
    return sections


_CATEGORIA_COB = [
    ("Lado A", ["lado a", "pagamento direto", "indenizacao direta"]),
    ("Lado B", ["lado b", "reembolso a sociedade", "reembolso sociedade", "reembolso tomador"]),
    ("Lado C", ["lado c", "entidade", "mercado de capitais", "valores mobiliarios"]),
    ("Custos de Defesa", ["custos defesa", "honorarios", "despesas defesa"]),
    ("Extensão", ["conjuge", "herdeiro", "espolio", "aposentad", "extensao"]),
]

_CATEGORIA_EXC = [
    ("Conduta dolosa/fraude", ["dolo", "fraud", "ma fe", "vantagem indevida", "ilicit"]),
    ("Danos corporais/materiais", ["corporais", "materiais", "danos fisicos"]),
    ("Ambiental", ["ambient", "poluic", "polu"]),
    ("Reclamações prévias", ["previa", "anterior", "pendente", "circunstancia conhecida"]),
    ("Segurado vs. Segurado", ["segurado contra segurado", "segurado versus", "insured vs"]),
    ("Multas e penalidades", ["multa", "penalidade", "tributo"]),
    ("Trabalhista", ["trabalhist", "emprego"]),
    ("Contratual", ["contrat"]),
]


def _categoria(nome: str, tabela, default: str) -> str:
    k = norm_key(nome)
    for cat, keys in tabela:
        if any(key in k for key in keys):
            return cat
    return default


def _split_title(line: str) -> tuple[str, str | None]:
    line = re.sub(r"^\s*(?:\d+(?:\.\d+)*|[a-z])[\).\-–]\s*", "", line)
    parts = re.split(r"\s*[:–]\s+|\s+-\s+", line, maxsplit=1)
    if len(parts) == 2 and len(parts[0]) < 90:
        return parts[0].strip(), parts[1].strip()
    return line[:80].strip(), line.strip()


def _merge_continuations(lines: list[str]) -> list[str]:
    """Junta linhas quebradas: uma nova entrada começa por número/letra de item."""
    item_re = re.compile(r"^\s*(?:\d+(?:\.\d+)*|[a-z])[\).\-–]\s+")
    numbered = any(item_re.match(ln) for ln in lines)
    items: list[str] = []
    for ln in lines:
        if item_re.match(ln):
            items.append(ln)
        elif items:
            items[-1] += " " + ln
        elif not numbered:  # seção sem numeração: cada linha é um item
            items.append(ln)
        # linhas introdutórias antes do 1º item numerado são descartadas
    if not numbered:
        return lines
    return items


def extract_heuristic(text: str) -> ApoliceDO:
    ident = Identificacao(
        seguradora=_field(text, "seguradora"),
        numero_apolice=_field(text, "numero_apolice"),
        produto=_field(text, "produto"),
        processo_susep=_field(text, "processo_susep"),
        tomador=_field(text, "tomador"),
        cnpj_tomador=_field(text, "cnpj_tomador"),
        corretor=_field(text, "corretor"),
    )
    if not ident.seguradora:
        m = re.search(r"^(.*SEGURADORA.*|.*SEGUROS S\.?A\.?.*)$", text, re.MULTILINE)
        if m:
            ident.seguradora = m.group(1).strip()
    vig = re.search(rf"vig[êe]ncia[^\n]*?({_DATE})[^\n]*?({_DATE})", text, re.IGNORECASE)
    if vig:
        ident.vigencia_inicio = normalize_date(vig.group(1))
        ident.vigencia_fim = normalize_date(vig.group(2))

    ap = ApoliceDO(
        identificacao=ident,
        limite_maximo_garantia=_valor(_field(text, "lmg")),
        premio_total=_valor(_field(text, "premio")),
        base_cobertura=_field(text, "base"),
        data_retroatividade=normalize_date(_field(text, "retro")),
        prazo_complementar=_field(text, "complementar"),
        territorialidade=_field(text, "territorio"),
        custos_defesa=_field(text, "custos_defesa"),
    )

    for heading, lines in _sections(text):
        h = norm_key(heading)
        if "exclus" in h:
            for item in _merge_continuations(lines):
                titulo, desc = _split_title(item)
                ap.exclusoes.append(Exclusao(
                    titulo=titulo, descricao=desc, trecho_fonte=item[:200],
                    categoria=_categoria(titulo + " " + (desc or ""), _CATEGORIA_EXC, "Outra"),
                ))
        elif "franquia" in h or "retenc" in h:
            for item in _merge_continuations(lines):
                if "R$" in item or "US$" in item:
                    titulo, desc = _split_title(item)
                    ap.franquias.append(Franquia(aplicacao=titulo, valor=_valor(desc or item)))
        elif "cobertura" in h and "base" not in h:
            for item in _merge_continuations(lines):
                money = list(re.finditer(r"(?:R\$|US\$)\s*[\d.,]+", item))
                if not money and "LMG" not in item.upper():
                    continue
                # Linha de tabela: "Nome | Limite | Franquia" ou "Nome  R$ x  R$ y"
                cells = [c.strip() for c in item.split("|")] if "|" in item else None
                if cells and len(cells) >= 2:
                    nome, lim, fr = cells[0], cells[1], (cells[2] if len(cells) > 2 else None)
                else:
                    cut = money[0].start() if money else item.upper().find("LMG")
                    nome = item[:cut].strip(" :-–")
                    lim = money[0].group(0) if money else "Até o LMG"
                    fr = money[1].group(0) if len(money) > 1 else None
                nome = re.sub(r"^\s*(?:\d+(?:\.\d+)*|[a-z])[\).\-–]\s*", "", nome)
                if not nome:
                    continue
                ap.coberturas.append(Cobertura(
                    nome=nome, trecho_fonte=item[:200],
                    categoria=_categoria(nome, _CATEGORIA_COB, "Outra"),
                    limite=_valor(lim),
                    franquia=_valor(fr) if fr and fr.strip() not in {"-", "—", "Não há", "Isenta"} else None,
                ))
        elif "segurad" in h and "definic" not in h and "exclus" not in h:
            for item in _merge_continuations(lines):
                t, _ = _split_title(item)
                if len(t) < 120:
                    ap.segurados.append(t)
        elif "clausula" in h or "condicoes especiais" in h or "condicoes particulares" in h:
            for item in _merge_continuations(lines):
                ap.clausulas_relevantes.append(item[:300])

    ap.observacoes = "Extraído em modo offline (regras heurísticas, sem LLM)."
    return ap


_DO_TERMS = ["d&o", "administradores", "diretores", "directors and officers",
             "responsabilidade civil de administradores", "conselheiros"]


def triage_heuristic(text: str) -> dict:
    low = text.lower()
    hits = sum(low.count(t) for t in _DO_TERMS)
    if "condições gerais" in low or "condicoes gerais" in low:
        tipo = "condicoes_gerais"
    elif "proposta" in low[:3000]:
        tipo = "proposta"
    elif "apólice" in low or "apolice" in low:
        tipo = "apolice"
    else:
        tipo = "outro"
    return {
        "eh_do": hits >= 3,
        "tipo_documento": tipo,
        "seguradora": _field(text, "seguradora"),
        "confianca": min(1.0, hits / 10),
        "justificativa": f"{hits} ocorrências de termos típicos de D&O (modo heurístico).",
    }
