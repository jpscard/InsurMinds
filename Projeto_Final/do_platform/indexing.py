"""Índice hierárquico do documento (abordagem PageIndex).

Em vez de picotar a apólice em pedaços para busca por similaridade, o documento vira uma
árvore de seções, parecida com um sumário: cada nó tem título, páginas, um resumo curto e o
texto da seção. Na consulta, o LLM lê a árvore e decide quais seções abrir, como um
especialista folhearia a apólice.

A estrutura é detectada sem LLM, pelo layout típico de apólices brasileiras:
- títulos em MAIÚSCULAS ("EXCLUSÕES", "CLÁUSULAS PARTICULARES", "CLÁUSULA 5 – ...");
- cláusulas e itens numerados ("1. Atos dolosos: ...", "5.3 Segurado contra Segurado").
Sem estrutura reconhecível, cada página vira um nó. O LLM (IndexAgent) só escreve os resumos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_NUMBERED = re.compile(r"^(?P<num>\d{1,2}(?:\.\d{1,2}){0,3})(?:[.)]\s+|\s+(?=[A-ZÀ-Ý]))(?P<rest>\S.*)$")
_CLAUSE = re.compile(r"^(CL[ÁA]USULA|CAP[ÍI]TULO|SE[ÇC][ÃA]O|ANEXO|ART(IGO|\.))\b", re.IGNORECASE)
MAX_NODE_CHARS = 6000


@dataclass
class Node:
    id: str
    titulo: str
    nivel: int
    pagina_inicio: int
    pagina_fim: int
    texto: str = ""
    resumo: str = ""
    filhos: list["Node"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "titulo": self.titulo, "nivel": self.nivel,
                "pagina_inicio": self.pagina_inicio, "pagina_fim": self.pagina_fim,
                "resumo": self.resumo, "texto": self.texto, "filhos": [f.to_dict() for f in self.filhos]}


def _is_upper_heading(line: str) -> bool:
    s = line.strip()
    if not 3 <= len(s) <= 110 or s.endswith((",", ";")):
        return False
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 4 or "R$" in s:
        return False
    if ":" in s and s.split(":", 1)[1].strip():
        return False  # "CNPJ: 00.000...": rótulo com valor, não título
    if sum(c.isdigit() for c in s) > len(letters):
        return False
    return sum(c.isupper() for c in letters) / len(letters) >= 0.85


def _numbered_title(rest: str) -> str:
    head = rest.split(":", 1)[0] if ":" in rest[:90] else rest
    head = head.strip()
    return head if len(head) <= 80 else head[:77].rstrip() + "…"


def build_tree(pages: list[tuple[int, str]]) -> dict:
    """`pages`: [(número, texto)]. Devolve {"metodo": ..., "nos": [árvore]}."""
    counter = 0

    def new_id() -> str:
        nonlocal counter
        counter += 1
        return f"{counter:04d}"

    roots: list[Node] = []
    stack: list[Node] = []           # caminho atual da raiz até o nó aberto
    section_level = 0                # nível do último título em maiúsculas
    last_was_heading = False
    headings = 0
    preamble: list[tuple[int, str]] = []

    def open_node(title: str, level: int, page: int, first_line: str) -> None:
        nonlocal headings
        node = Node(new_id(), title, level, page, page, first_line)
        while stack and stack[-1].nivel >= level:
            stack.pop()
        (stack[-1].filhos if stack else roots).append(node)
        stack.append(node)
        headings += 1

    for page, text in pages:
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            m = _NUMBERED.match(line)
            if _is_upper_heading(line) or (_CLAUSE.match(line) and len(line) <= 110):
                if last_was_heading and stack and stack[-1].texto.strip() == stack[-1].titulo:
                    # título quebrado em várias linhas: junta no mesmo nó
                    stack[-1].titulo = f"{stack[-1].titulo} {line}"
                    stack[-1].texto = stack[-1].titulo
                else:
                    section_level = 1
                    open_node(line, 1, page, line)
                last_was_heading = True
                continue
            last_was_heading = False
            if m:
                depth = m.group("num").count(".") + 1
                open_node(f"{m.group('num')}. {_numbered_title(m.group('rest'))}".replace("..", "."),
                          section_level + depth, page, line)
                continue
            if stack:
                stack[-1].texto += "\n" + line
                for n in stack:
                    n.pagina_fim = max(n.pagina_fim, page)
            else:
                preamble.append((page, line))

    if headings < 2:
        nodes = [Node(new_id(), f"Página {p}", 1, p, p, t.strip()) for p, t in pages if t.strip()]
        metodo = "paginas"
    else:
        nodes = roots
        if preamble:
            first = preamble[0][0]
            nodes.insert(0, Node("0000", "Preâmbulo", 1, first, preamble[-1][0], "\n".join(l for _, l in preamble)))
        metodo = "estrutura"

    _renumber(nodes)
    for n in flatten(nodes):
        n.texto = n.texto.strip()[:MAX_NODE_CHARS]
        n.resumo = heuristic_summary(n)
    return {"metodo": metodo, "nos": [n.to_dict() for n in nodes]}


def _renumber(nodes: list[Node], nivel: int = 1) -> None:
    """Nível = profundidade real na árvore. Sem isso, "CLÁUSULA 5" → "5.1" → "5.1.1" viraria
    1 → 3 → 4, e o navegador (que vê até o nível 3) perderia os subitens."""
    for n in nodes:
        n.nivel = nivel
        _renumber(n.filhos, nivel + 1)


def heuristic_summary(node: Node | dict, limit: int = 160) -> str:
    """Resumo sem LLM: o texto da seção sem o título, cortado numa frase."""
    titulo = node.titulo if isinstance(node, Node) else node["titulo"]
    texto = node.texto if isinstance(node, Node) else node["texto"]
    body = texto[len(titulo):] if texto.startswith(titulo) else texto
    body = re.sub(r"^\s*[:\-–—]\s*", "", body.replace("\n", " ")).strip()
    if not body:
        return ""
    return body if len(body) <= limit else body[:limit].rsplit(" ", 1)[0] + "…"


def flatten(nodes: list) -> list:
    """Percorre a árvore (Node ou dict) em pré-ordem."""
    out = []
    for n in nodes:
        out.append(n)
        out.extend(flatten(n.filhos if isinstance(n, Node) else n.get("filhos", [])))
    return out


def find(tree: dict, node_id: str) -> dict | None:
    return next((n for n in flatten(tree.get("nos", [])) if n["id"] == node_id), None)


def subtree_text(node: dict, limit: int = MAX_NODE_CHARS) -> str:
    """Texto do nó com o de todas as subseções (abrir 'EXCLUSÕES' traz todos os itens)."""
    parts = [n["texto"] for n in flatten([node])]
    text = "\n".join(p for p in parts if p)
    return text if len(text) <= limit else text[:limit] + "\n[…]"


def outline(tree: dict, max_depth: int = 3, with_summary: bool = True) -> str:
    """Árvore em texto compacto para o LLM navegar (sem o texto das seções)."""
    lines = []
    for n in flatten(tree.get("nos", [])):
        if n["nivel"] > max_depth:
            continue
        pag = f"p.{n['pagina_inicio']}" + (f"-{n['pagina_fim']}" if n["pagina_fim"] != n["pagina_inicio"] else "")
        resumo = f" — {n['resumo']}" if with_summary and n.get("resumo") else ""
        lines.append(f"{'  ' * (n['nivel'] - 1)}- [{n['id']}] {n['titulo']} ({pag}){resumo}")
    return "\n".join(lines)
