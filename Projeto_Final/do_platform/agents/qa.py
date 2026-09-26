"""Agente de Consulta: RAG por raciocínio sobre o índice das apólices (abordagem PageIndex),
orquestrado como um grafo LangGraph.

    roteador ──estruturado──────────────────────────────────────────┐
       │ documento                                                  ▼
       ├──► navegador ──► leitor ──► avaliador ──suficiente──► respondedor
       │       ▲  │ nada escolhido      │ falta algo (máx. 2 rodadas)
       │       └──┼─────────────────────┘
       └ offline  ▼
            busca_lexical (BM25 nas seções) ──────────────────────────┘

- O roteador decide se os dados estruturados bastam ou se é preciso ler o documento.
- O navegador lê o sumário (árvore de seções com resumos) e escolhe o que abrir, como um
  especialista folheando a apólice; o leitor traz o texto das seções escolhidas.
- O avaliador pode pedir mais uma rodada de navegação se faltar informação.
- Sem LLM (modo offline) ou se a navegação falhar, cai na busca por palavras-chave (BM25).
Cada passo fica registrado em `caminho`, que a interface mostra junto da resposta.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ..indexing import find, flatten, outline, subtree_text
from ..llm import LLMError
from ..utils import norm_key
from .base import Agent
from .prompts import (AVALIADOR_SYSTEM, AVALIADOR_USER, CONSULTA_SYSTEM, CONSULTA_USER, NAVEGADOR_SYSTEM,
                      NAVEGADOR_USER, ROTEADOR_SYSTEM, ROTEADOR_USER)

MAX_SECOES = 6            # seções abertas por rodada de navegação
MAX_RODADAS = 2           # rodadas de navegação (a segunda só se o avaliador pedir)
MAX_SECTION_CHARS = 4000  # texto de cada seção enviado ao respondedor
MAX_ESTRUTURADO = 60000   # caracteres dos dados estruturados no prompt


# ─── Busca lexical (BM25), usada no modo offline e como reserva ──────────────
def _tokens(text: str) -> list[str]:
    return [t for t in norm_key(text).split() if len(t) > 2]


def rank_passages(question: str, passages: list[dict], k: int = 6) -> list[dict]:
    """Ranqueia trechos (dicts com 'texto') por BM25 simplificado."""
    q = set(_tokens(question))
    if not q or not passages:
        return []
    docs = [_tokens(p["texto"]) for p in passages]
    n = len(docs)
    avg = sum(map(len, docs)) / n or 1
    df = Counter(t for d in docs for t in set(d))
    scored = []
    for p, d in zip(passages, docs):
        tf = Counter(d)
        s = 0.0
        for t in q:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(d) / avg))
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:k]]


def split_passages(pages: list[dict], size: int = 1200) -> list[dict]:
    """Divide páginas em parágrafos de ~size caracteres, mantendo a referência da página."""
    out = []
    for pg in pages:
        buf = ""
        for para in re.split(r"\n\s*\n|\n(?=\d+[\.\)])", pg["texto"]):
            if len(buf) + len(para) > size and buf:
                out.append({**pg, "texto": buf.strip()})
                buf = ""
            buf += para + "\n"
        if buf.strip():
            out.append({**pg, "texto": buf.strip()})
    return out


def _pages_label(node: dict) -> str:
    a, b = node["pagina_inicio"], node["pagina_fim"]
    return str(a) if a == b else f"{a}-{b}"


# ─── Estado do grafo ─────────────────────────────────────────────────────────
class ConsultaState(TypedDict, total=False):
    pergunta: str
    codigos: dict[str, str]        # "A1" -> rótulo da apólice
    estruturado: dict[str, dict]   # rótulo -> dados extraídos
    arvores: dict[str, dict]       # rótulo -> índice hierárquico
    paginas: list[dict]            # texto por página (reserva quando não há índice)
    rota: str
    selecionadas: list[dict]
    lidas: list[str]               # "A1:0014"
    trechos: list[dict]
    falta: str
    rodadas: int
    suficiente: bool
    resposta: str
    caminho: list[dict]


class QAAgent(Agent):
    nome = "Consulta"

    # ── API pública ──────────────────────────────────────────────────────
    def run(self, pergunta: str, apolices: dict[str, dict], paginas: list[dict],
            arvores: dict[str, dict] | None = None) -> dict:
        """`apolices`: rótulo -> dados estruturados; `paginas`: [{rotulo, pagina, texto}];
        `arvores`: rótulo -> índice hierárquico (sem índice, usa as páginas)."""
        labels = list(apolices)
        state: ConsultaState = {
            "pergunta": pergunta,
            "codigos": {f"A{i + 1}": lb for i, lb in enumerate(labels)},
            "estruturado": apolices, "arvores": arvores or {}, "paginas": paginas,
            "selecionadas": [], "lidas": [], "trechos": [], "falta": "", "rodadas": 0, "caminho": [],
        }
        out = self.graph().invoke(state)
        return {"resposta": out["resposta"], "trechos": out["trechos"], "rota": out.get("rota"),
                "caminho": out["caminho"]}

    def graph(self):
        g = StateGraph(ConsultaState)
        g.add_node("roteador", self._roteador)
        g.add_node("navegador", self._navegador)
        g.add_node("leitor", self._leitor)
        g.add_node("avaliador", self._avaliador)
        g.add_node("busca_lexical", self._busca_lexical)
        g.add_node("respondedor", self._respondedor)
        g.add_edge(START, "roteador")
        g.add_conditional_edges("roteador", lambda s: s["rota"],
                                {"estruturado": "respondedor", "documento": "navegador", "lexical": "busca_lexical"})
        g.add_conditional_edges("navegador", lambda s: "leitor" if s["selecionadas"] else
                                ("respondedor" if s["trechos"] else "busca_lexical"),
                                {"leitor": "leitor", "respondedor": "respondedor", "busca_lexical": "busca_lexical"})
        g.add_edge("leitor", "avaliador")
        g.add_conditional_edges("avaliador", lambda s: "respondedor" if s["suficiente"] else "navegador",
                                {"respondedor": "respondedor", "navegador": "navegador"})
        g.add_edge("busca_lexical", "respondedor")
        g.add_edge("respondedor", END)
        return g.compile()

    # ── Nós ──────────────────────────────────────────────────────────────
    def _step(self, state: ConsultaState, etapa: str, detalhe: str, t0: float) -> list[dict]:
        self.trace.add(self.nome, etapa, t0, detalhe)
        return [*state["caminho"], {"etapa": etapa, "detalhe": detalhe}]

    def _roteador(self, s: ConsultaState) -> dict:
        t0 = time.perf_counter()
        if self.llm.is_offline:
            return {"rota": "lexical",
                    "caminho": self._step(s, "Roteador", "Modo offline: busca por palavras-chave nas seções.", t0)}
        campos = sorted({k for d in s["estruturado"].values() for k in d})
        try:
            out = self.llm.complete_json(ROTEADOR_SYSTEM, ROTEADOR_USER.format(campos=", ".join(campos),
                                                                            pergunta=s["pergunta"]))
            out = out if isinstance(out, dict) else {}
            rota = out.get("rota") if out.get("rota") in {"estruturado", "documento"} else "documento"
            motivo = str(out.get("motivo") or "")
        except (LLMError, ValueError) as exc:
            rota, motivo = "documento", f"roteador indisponível ({exc}); lendo o documento por segurança"
        if rota == "documento" and not any(s["arvores"].values()):
            rota, motivo = "lexical", "sem índice das apólices; busca por palavras-chave"
        nome = {"estruturado": "dados estruturados", "documento": "ler o documento", "lexical": "busca por palavras"}[rota]
        return {"rota": rota, "caminho": self._step(s, "Roteador", f"Rota: {nome}. {motivo}".strip(), t0)}

    def _navegador(self, s: ConsultaState) -> dict:
        t0 = time.perf_counter()
        indices = "\n\n".join(f"### {code} · {lb}\n{outline(s['arvores'][lb])}"
                              for code, lb in s["codigos"].items() if s["arvores"].get(lb))
        falta = f"Ainda falta: {s['falta']}\n" if s["falta"] else ""
        try:
            out = self.llm.complete_json(
                NAVEGADOR_SYSTEM.format(max_secoes=MAX_SECOES),
                NAVEGADOR_USER.format(pergunta=s["pergunta"], falta=falta, indices=indices,
                                      lidas=", ".join(s["lidas"]) or "nenhuma"))
            pedidas = out.get("secoes", []) if isinstance(out, dict) else []
        except (LLMError, ValueError) as exc:
            return {"selecionadas": [], "caminho": self._step(s, "Navegador", f"Falhou ({exc}).", t0)}

        escolhidas, vistas = [], set(s["lidas"])
        for p in pedidas if isinstance(pedidas, list) else []:
            code, nid = str(p.get("apolice", "")).upper(), str(p.get("id", "")).zfill(4)
            lb = s["codigos"].get(code)
            key = f"{code}:{nid}"
            if lb and key not in vistas and find(s["arvores"].get(lb) or {}, nid):
                escolhidas.append({"codigo": code, "rotulo": lb, "id": nid, "motivo": str(p.get("motivo") or "")})
                vistas.add(key)
            if len(escolhidas) >= MAX_SECOES:
                break
        titulos = "; ".join(f"{e['rotulo']} › {find(s['arvores'][e['rotulo']], e['id'])['titulo']}" for e in escolhidas)
        detalhe = f"Abrir {len(escolhidas)} seção(ões): {titulos}" if escolhidas else "Nenhuma seção nova relevante no índice."
        return {"selecionadas": escolhidas, "caminho": self._step(s, "Navegador", detalhe, t0)}

    def _leitor(self, s: ConsultaState) -> dict:
        t0 = time.perf_counter()
        trechos, lidas = list(s["trechos"]), list(s["lidas"])
        for e in s["selecionadas"]:
            node = find(s["arvores"][e["rotulo"]], e["id"])
            trechos.append({"rotulo": e["rotulo"], "secao": node["titulo"], "id": e["id"],
                            "pagina": node["pagina_inicio"], "paginas": _pages_label(node),
                            "motivo": e["motivo"], "texto": subtree_text(node, MAX_SECTION_CHARS)})
            lidas.append(f"{e['codigo']}:{e['id']}")
        return {"trechos": trechos, "lidas": lidas, "selecionadas": [], "rodadas": s["rodadas"] + 1,
                "caminho": self._step(s, "Leitor", f"{len(s['selecionadas'])} seção(ões) lida(s); "
                                                   f"{len(trechos)} no total.", t0)}

    def _avaliador(self, s: ConsultaState) -> dict:
        t0 = time.perf_counter()
        if s["rodadas"] >= MAX_RODADAS:
            return {"suficiente": True, "caminho": self._step(s, "Avaliador", "Limite de rodadas atingido.", t0)}
        try:
            out = self.llm.complete_json(AVALIADOR_SYSTEM, AVALIADOR_USER.format(
                pergunta=s["pergunta"], apolices="; ".join(s["codigos"].values()), trechos=_fmt(s["trechos"])))
            out = out if isinstance(out, dict) else {}
            ok = bool(out.get("suficiente", True))
            falta = str(out.get("falta") or "")
        except (LLMError, ValueError):
            ok, falta = True, ""
        detalhe = "Informação suficiente." if ok else f"Falta: {falta or 'mais contexto'}. Nova navegação."
        return {"suficiente": ok, "falta": "" if ok else falta, "caminho": self._step(s, "Avaliador", detalhe, t0)}

    def _busca_lexical(self, s: ConsultaState) -> dict:
        t0 = time.perf_counter()
        passagens = []
        for lb, tree in s["arvores"].items():
            for n in flatten(tree.get("nos", [])):
                if n.get("texto"):
                    passagens.append({"rotulo": lb, "secao": n["titulo"], "id": n["id"], "pagina": n["pagina_inicio"],
                                      "paginas": _pages_label(n), "texto": n["texto"]})
        sem_indice = [p for p in s["paginas"] if not s["arvores"].get(p["rotulo"])]
        passagens += [{**p, "secao": None, "paginas": str(p["pagina"])} for p in split_passages(sem_indice)]
        trechos = rank_passages(s["pergunta"], passagens)
        return {"trechos": [*s["trechos"], *trechos],
                "caminho": self._step(s, "Busca por palavras", f"{len(trechos)} trecho(s) pelo BM25.", t0)}

    def _respondedor(self, s: ConsultaState) -> dict:
        t0 = time.perf_counter()
        if self.llm.is_offline:
            resposta = ("**Modo offline:** estas são as seções mais relevantes para a sua pergunta. "
                        "Para uma resposta redigida, com citação, configure um modelo de IA.")
            return {"resposta": resposta, "caminho": self._step(s, "Respondedor", "Sem LLM: só os trechos.", t0)}
        dados = json.dumps(s["estruturado"], ensure_ascii=False)
        caminho = s["caminho"]
        if len(dados) > MAX_ESTRUTURADO:
            dados = dados[:MAX_ESTRUTURADO]
            caminho = [*caminho, {"etapa": "Respondedor",
                                  "detalhe": "Dados estruturados cortados por tamanho: selecione menos apólices."}]
        resposta = self.llm.complete(CONSULTA_SYSTEM, CONSULTA_USER.format(
            apolices=dados, trechos=_fmt(s["trechos"]) or "(nenhuma; use os dados estruturados)", pergunta=s["pergunta"]))
        return {"resposta": resposta,
                "caminho": self._step({**s, "caminho": caminho}, "Respondedor",
                                      f"Resposta com {len(s['trechos'])} seção(ões) de apoio.", t0)}


def _fmt(trechos: list[dict]) -> str:
    return "\n\n".join(f"[{t['rotulo']}{' · ' + t['secao'] if t.get('secao') else ''} · pág. {t.get('paginas', t['pagina'])}]\n"
                       f"{t['texto']}" for t in trechos)


def consulta_mermaid() -> str:
    """Diagrama do grafo (para a documentação)."""
    from ..llm import get_provider
    return QAAgent(get_provider("offline")).graph().get_graph().draw_mermaid()
