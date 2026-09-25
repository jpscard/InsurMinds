"""Funções utilitárias de normalização (valores monetários, datas, texto)."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime

_MONEY = re.compile(
    r"(?P<moeda>R\$|US\$|USD|BRL|€|EUR)?\s*(?P<num>\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)"
    r"\s*(?P<mult>mil(?:h(?:ão|ões|ao|oes))?|bilh(?:ão|ões|ao|oes)|mi\b|MM\b)?",
    re.IGNORECASE,
)


def parse_money(text: str | None) -> tuple[float | None, str | None]:
    """'R$ 10.000.000,00' -> (10000000.0, 'BRL'); 'US$ 5 milhões' -> (5000000.0, 'USD')."""
    if not text:
        return None, None
    m = _MONEY.search(text)
    if not m:
        return None, None
    num = m.group("num").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        value = float(num)
    except ValueError:
        return None, None
    mult = (m.group("mult") or "").lower()
    if mult.startswith("bilh"):
        value *= 1_000_000_000
    elif mult.startswith("milh") or mult in {"mi", "mm"}:
        value *= 1_000_000
    elif mult == "mil":
        value *= 1_000
    cur = (m.group("moeda") or "").upper()
    moeda = {"R$": "BRL", "BRL": "BRL", "US$": "USD", "USD": "USD", "€": "EUR", "EUR": "EUR"}.get(cur)
    return value, moeda


def normalize_date(text: str | None) -> str | None:
    """Converte datas comuns para AAAA-MM-DD; devolve o texto original se não reconhecer."""
    if not text:
        return text
    t = text.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(t, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"(\d{2})[/.-](\d{2})[/.-](\d{4})", t)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return t


def fmt_money(value: float | None, moeda: str | None = "BRL") -> str:
    if value is None:
        return "—"
    prefix = {"BRL": "R$", "USD": "US$", "EUR": "€"}.get(moeda or "BRL", moeda or "")
    s = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefix} {s}"


def norm_key(text: str) -> str:
    """Chave canônica para casar nomes: sem acento, minúsculas, sem pontuação."""
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    stop = {"de", "da", "do", "das", "dos", "e", "a", "o", "para", "por", "com", "cobertura", "clausula"}
    return " ".join(w for w in t.split() if w not in stop)


def similarity(a: str, b: str) -> float:
    """Similaridade de Jaccard entre conjuntos de palavras normalizadas (0..1)."""
    sa, sb = set(norm_key(a).split()), set(norm_key(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
