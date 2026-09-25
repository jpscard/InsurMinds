"""Interface Streamlit da Plataforma D&O.

Execute:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from do_platform.config import ROOT_DIR, get_settings
from do_platform.ingestion import SUPPORTED_EXT, IngestionError
from do_platform.llm import PROVIDERS, LLMError, get_provider
from do_platform.pipeline import Pipeline
from do_platform.schema import ApoliceDO
from do_platform.storage import Repository
from do_platform.utils import fmt_money

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
st.set_page_config(page_title="Análise de Apólices D&O", page_icon="📑", layout="wide")

SAMPLES_DIR = ROOT_DIR / "samples"
settings = get_settings()


# --------------------------------------------------------------------------- setup
@st.cache_resource
def get_repo() -> Repository:
    return Repository(settings.database_path)


def _settings_with_key(prov: str):
    """Configuração com a chave digitada na sessão (se houver) no lugar da do .env."""
    s = settings.model_copy()
    if prov != "offline" and (key := st.session_state.get(f"api_key_{prov}")):
        setattr(s, f"{prov}_api_key", key)
    return s


@st.cache_data(ttl=3600, show_spinner=False)
def list_models(prov: str, key_fingerprint: str, _settings) -> list[tuple[str, str]]:
    """Modelos do provedor, em cache por provedor + chave (só o hash da chave entra no cache)."""
    return get_provider(prov, settings=_settings).list_models()


def build_pipeline() -> Pipeline | None:
    prov = st.session_state.get("provider", settings.llm_provider)
    model = st.session_state.get("llm_model") or None
    s = _settings_with_key(prov)
    try:
        llm = get_provider(prov, model, settings=s)
    except LLMError as exc:
        st.sidebar.error(str(exc))
        return None
    return Pipeline(llm=llm, settings=s, repo=get_repo())


OTHER_MODEL = "Outro (digitar)…"


def model_picker(prov: str) -> None:
    """Escolha do modelo: lista os modelos do provedor assim que houver chave de API."""
    default = settings.llm_model or PROVIDERS[prov].default_model
    st.session_state.llm_model = default
    s = _settings_with_key(prov)
    key = getattr(s, f"{prov}_api_key")
    if not key:
        st.sidebar.caption(f"Informe a chave para escolher o modelo. Padrão: `{default}`")
        return

    try:
        with st.sidebar, st.spinner("Buscando modelos…"):
            models = list_models(prov, hashlib.sha256(key.encode()).hexdigest()[:16], s)
    except LLMError as exc:
        if "chave de API inválida" in str(exc):
            st.sidebar.error(str(exc))
            return
        st.sidebar.warning(f"{exc}\n\nEscolha “{OTHER_MODEL}” para digitar o nome do modelo.")
        models = []

    labels = dict(models)
    ids = list(labels)
    if default not in labels:
        ids.insert(0, default)
    choice = st.sidebar.selectbox(
        "Modelo", ids + [OTHER_MODEL], index=ids.index(default), key=f"model_sel_{prov}",
        format_func=lambda m: f"{labels[m]} ({m})" if labels.get(m, m) != m else m,
        help=f"{len(models)} modelos disponíveis para esta chave." if models else None,
    )
    if choice == OTHER_MODEL:
        typed = st.sidebar.text_input("Nome do modelo", key=f"model_txt_{prov}", placeholder=default)
        st.session_state.llm_model = typed.strip() or default
    else:
        st.session_state.llm_model = choice


def sidebar() -> str:
    st.sidebar.title("📑 Apólices D&O")
    page = st.sidebar.radio("Navegação", ["Enviar apólices", "Apólices armazenadas", "Comparar",
                                          "Consultar", "Sobre a solução"], label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.subheader("Modelo de IA")
    provs = list(PROVIDERS)
    st.sidebar.selectbox("Provedor", provs, key="provider",
                         index=provs.index(settings.llm_provider) if settings.llm_provider in provs else 0,
                         help="Padrão definido em LLM_PROVIDER no .env. 'offline' usa regras, sem IA.")
    prov = st.session_state.provider
    if prov != "offline":
        has_env = bool(getattr(settings, f"{prov}_api_key"))
        st.sidebar.text_input("Chave de API", key=f"api_key_{prov}", type="password",
                              placeholder="usando a chave do .env" if has_env else "cole a chave aqui",
                              help="Fica só na memória desta sessão; não é gravada em disco.")
        model_picker(prov)
    else:
        st.sidebar.info("Modo offline: extração por regras, sem IA generativa. "
                        "Útil para testar a interface; selecione um provedor para a análise real.")
    return page


def alert_box(alertas: list[dict]) -> None:
    for a in alertas:
        {"erro": st.error, "aviso": st.warning}.get(a["nivel"], st.info)(a["mensagem"])


def show_trace(trace) -> None:
    df = pd.DataFrame([vars(s) for s in trace.steps]).rename(
        columns={"agente": "Agente", "acao": "Ação", "duracao_s": "Tempo (s)", "detalhe": "Detalhe"})
    st.dataframe(df, hide_index=True, use_container_width=True)


def short(value: float | None, moeda: str | None = "BRL") -> str:
    """Formato compacto para cartões de métrica: R$ 25,0 mi."""
    if value is None:
        return "—"
    prefix = {"BRL": "R$", "USD": "US$", "EUR": "€"}.get(moeda or "BRL", moeda or "")
    if abs(value) >= 1_000_000:
        return f"{prefix} {value / 1_000_000:,.1f} mi".replace(".", ",")
    if abs(value) >= 1_000:
        return f"{prefix} {value / 1_000:,.1f} mil".replace(".", ",")
    return fmt_money(value, moeda)


def val(v) -> str:
    if not v:
        return "—"
    return fmt_money(v.valor, v.moeda) if v.valor is not None else (v.texto or "—")


def show_policy(ap: ApoliceDO) -> None:
    idt = ap.identificacao
    c1, c2, c3, c4 = st.columns(4)
    lmg, pr = ap.limite_maximo_garantia, ap.premio_total
    c1.metric("Limite Máximo de Garantia", short(lmg.valor, lmg.moeda) if lmg and lmg.valor else val(lmg))
    c2.metric("Prêmio total", short(pr.valor, pr.moeda) if pr and pr.valor else val(pr))
    c3.metric("Coberturas", len(ap.coberturas))
    c4.metric("Exclusões", len(ap.exclusoes))

    geral = {
        "Seguradora": idt.seguradora, "Nº da apólice": idt.numero_apolice, "Produto": idt.produto,
        "Processo SUSEP": idt.processo_susep, "Tomador": idt.tomador, "CNPJ": idt.cnpj_tomador,
        "Corretor": idt.corretor, "Vigência": f"{idt.vigencia_inicio or '?'} a {idt.vigencia_fim or '?'}",
        "Base de cobertura": ap.base_cobertura, "Retroatividade": ap.data_retroatividade,
        "Prazo complementar": ap.prazo_complementar, "Territorialidade": ap.territorialidade,
        "Custos de defesa": ap.custos_defesa,
    }
    st.dataframe(pd.DataFrame({"Campo": geral.keys(), "Valor": [v or "—" for v in geral.values()]}),
                 hide_index=True, use_container_width=True)

    t1, t2, t3, t4, t5 = st.tabs(["Coberturas", "Exclusões", "Franquias", "Segurados e cláusulas", "JSON"])
    with t1:
        st.dataframe(pd.DataFrame([{"Cobertura": c.nome, "Categoria": c.categoria, "Limite": val(c.limite),
                                    "Franquia": val(c.franquia), "Trecho-fonte": c.trecho_fonte}
                                   for c in ap.coberturas]), hide_index=True, use_container_width=True)
    with t2:
        st.dataframe(pd.DataFrame([{"Exclusão": e.titulo, "Categoria": e.categoria, "Descrição": e.descricao}
                                   for e in ap.exclusoes]), hide_index=True, use_container_width=True)
    with t3:
        st.dataframe(pd.DataFrame([{"Aplicação": f.aplicacao, "Valor": val(f.valor)} for f in ap.franquias]),
                     hide_index=True, use_container_width=True)
    with t4:
        st.markdown("**Segurados**")
        for s_ in ap.segurados:
            st.markdown(f"- {s_}")
        st.markdown("**Cláusulas relevantes**")
        for c in ap.clausulas_relevantes:
            st.markdown(f"- {c}")
        if ap.observacoes:
            st.caption(ap.observacoes)
    with t5:
        st.json(ap.model_dump(), expanded=False)


def process_files(files: list[tuple[str, bytes]], force: bool) -> None:
    pipe = build_pipeline()
    if not pipe:
        return
    for name, data in files:
        with st.status(f"Processando **{name}** com {pipe.llm.describe()}…", expanded=True) as status:
            try:
                r = pipe.process(name, data, force=force)
            except (IngestionError, LLMError, ValueError) as exc:
                status.update(label=f"❌ {name}: {exc}", state="error")
                continue
            except Exception as exc:  # noqa: BLE001
                logging.exception("Falha inesperada")
                status.update(label=f"❌ {name}: erro inesperado ({exc})", state="error")
                continue
            if r.reaproveitado:
                st.info("Documento já processado anteriormente; resultado carregado do banco. "
                        "Marque 'Reprocessar' para extrair de novo.")
            for a in r.avisos:
                st.warning(a)
            show_trace(r.trace)
            alert_box(r.alertas)
            status.update(label=f"✅ {name} → apólice #{r.apolice_id}", state="complete", expanded=False)
        with st.expander(f"Resultado: {name}", expanded=len(files) == 1):
            show_policy(r.apolice)


# --------------------------------------------------------------------------- páginas
def page_upload() -> None:
    st.header("Enviar apólices")
    st.write("Envie apólices D&O em **PDF** (digital ou digitalizado) ou **imagem**. "
             "Cada documento passa por ingestão/OCR, triagem, extração, validação e armazenamento.")
    files = st.file_uploader("Arquivos", type=[e.strip(".") for e in SUPPORTED_EXT],
                             accept_multiple_files=True)
    force = st.checkbox("Reprocessar mesmo se o arquivo já estiver no banco")
    c1, c2 = st.columns([1, 3])
    if c1.button("Processar", type="primary", disabled=not files):
        process_files([(f.name, f.getvalue()) for f in files], force)
    samples = sorted(p for p in SAMPLES_DIR.glob("*") if p.suffix.lower() in SUPPORTED_EXT)
    if samples and c2.button(f"Processar {len(samples)} apólices de exemplo (fictícias)"):
        process_files([(p.name, p.read_bytes()) for p in samples], force)


def page_list() -> None:
    st.header("Apólices armazenadas")
    repo = get_repo()
    rows = repo.list()
    if not rows:
        st.info("Nenhuma apólice ainda. Envie documentos na página **Enviar apólices**.")
        return
    df = pd.DataFrame(rows)
    df["lmg"] = df.apply(lambda r: fmt_money(r["lmg"], r["moeda"]), axis=1)
    df["premio"] = df.apply(lambda r: fmt_money(r["premio"], r["moeda"]), axis=1)
    st.dataframe(df.drop(columns=["moeda"]).rename(columns={
        "id": "ID", "arquivo": "Arquivo", "seguradora": "Seguradora", "numero_apolice": "Nº apólice",
        "tomador": "Tomador", "vigencia_inicio": "Início", "vigencia_fim": "Fim", "lmg": "LMG",
        "premio": "Prêmio", "provedor_llm": "Extraído por", "criado_em": "Processado em",
        "n_coberturas": "Coberturas", "n_exclusoes": "Exclusões"}), hide_index=True, use_container_width=True)

    opts = {r["id"]: f"#{r['id']} · {r['seguradora'] or r['arquivo']} · {r['numero_apolice'] or ''}" for r in rows}
    aid = st.selectbox("Detalhar apólice", list(opts), format_func=opts.get)
    row = repo.get_row(aid)
    ap = repo.get(aid)
    alert_box(json.loads(row["alertas_json"] or "[]"))
    show_policy(ap)

    with st.expander("✏️ Corrigir dados extraídos (revisão humana)"):
        st.caption("Edite o JSON e salve. As correções substituem a extração no banco.")
        txt = st.text_area("JSON", ap.model_dump_json(indent=2), height=350, key=f"edit_{aid}")
        if st.button("Salvar correções"):
            try:
                repo.update_data(aid, ApoliceDO.model_validate_json(txt))
                st.success("Correções salvas.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"JSON inválido: {exc}")
    with st.expander("📄 Texto extraído do documento"):
        for p in repo.pages(aid):
            st.markdown(f"**Página {p['numero']}** · via {p['metodo']}")
            st.text(p["texto"])
    if st.button("🗑️ Excluir esta apólice"):
        repo.delete(aid)
        st.rerun()


def _highlight_diff(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    def style(row):
        color = "background-color: rgba(255, 196, 0, 0.18)" if row.get("Diferente") else ""
        return [color] * len(row)
    return df.style.apply(style, axis=1)


def _situacao_style(df: pd.DataFrame):
    def style(row):
        s = str(row.get("Situação", ""))
        if s.startswith(("Ausente", "Só em")):
            return ["background-color: rgba(255, 80, 80, 0.12)"] * len(row)
        if s.startswith("Limites"):
            return ["background-color: rgba(255, 196, 0, 0.15)"] * len(row)
        return [""] * len(row)
    return df.style.apply(style, axis=1)


def comparison_report_md(res, analise) -> str:
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


def page_compare() -> None:
    st.header("Comparar apólices")
    repo = get_repo()
    rows = repo.list()
    if len(rows) < 2:
        st.info("São necessárias pelo menos duas apólices armazenadas.")
        return
    opts = {r["id"]: f"#{r['id']} · {r['seguradora'] or r['arquivo']} · {r['numero_apolice'] or ''}" for r in rows}
    ids = st.multiselect("Apólices", list(opts), default=sorted(opts)[:2], format_func=opts.get)
    if st.button("Comparar", type="primary", disabled=len(ids) < 2):
        pipe = build_pipeline()
        if pipe:
            with st.spinner(f"Comparando com {pipe.llm.describe()}…"):
                try:
                    st.session_state.cmp = pipe.compare(ids)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha na comparação: {exc}")
    if "cmp" not in st.session_state:
        return
    res, analise, trace = st.session_state.cmp

    # Métricas lado a lado
    cols = st.columns(len(res.labels))
    for col, lb in zip(cols, res.labels):
        m = res.metricas[lb]
        col.markdown(f"**{lb}**")
        col.metric("LMG", short(m["lmg"]))
        col.metric("Prêmio", short(m["premio"]))
        col.metric("Prêmio / LMG", f"{m['taxa_pct']:.3f}%" if m["taxa_pct"] is not None else "—")
        col.caption(f"{m['coberturas']} coberturas · {m['exclusoes']} exclusões")

    chart = pd.DataFrame({lb: {"Coberturas": m["coberturas"], "Exclusões": m["exclusoes"]}
                          for lb, m in res.metricas.items()}).T
    st.bar_chart(chart, horizontal=True, stack=False, height=60 + 50 * len(res.labels))

    st.subheader("Análise")
    st.info(analise.get("resumo_executivo", ""))
    dk = analise.get("diferencas_chave", [])
    if dk:
        icon = {"alto": "🔴 alto", "medio": "🟡 médio", "médio": "🟡 médio", "baixo": "🟢 baixo"}
        st.dataframe(pd.DataFrame([{"Tema": d.get("tema"), "Impacto": icon.get(str(d.get("impacto")).lower(), d.get("impacto")),
                                    "Favorece": d.get("favorece"), "Descrição": d.get("descricao")} for d in dk]),
                     hide_index=True, use_container_width=True)
    if analise.get("pontos_de_atencao"):
        st.markdown("**Pontos de atenção**")
        for p in analise["pontos_de_atencao"]:
            st.markdown(f"- ⚠️ {p}")
    if analise.get("recomendacao"):
        st.markdown("**Recomendação**")
        st.write(analise["recomendacao"])

    st.subheader("Detalhamento")
    t1, t2, t3, t4 = st.tabs(["Dados gerais", "Coberturas", "Exclusões", "Franquias"])
    with t1:
        st.dataframe(_highlight_diff(pd.DataFrame(res.geral)), hide_index=True, use_container_width=True)
        st.caption("Linhas destacadas diferem entre as apólices.")
    with t2:
        st.dataframe(_situacao_style(pd.DataFrame(res.coberturas)), hide_index=True, use_container_width=True)
    with t3:
        st.dataframe(_situacao_style(pd.DataFrame(res.exclusoes)), hide_index=True, use_container_width=True)
    with t4:
        st.dataframe(pd.DataFrame(res.franquias), hide_index=True, use_container_width=True)

    with st.expander("Etapas executadas"):
        show_trace(trace)

    c1, c2 = st.columns(2)
    xls = io.BytesIO()
    with pd.ExcelWriter(xls, engine="openpyxl") as w:
        pd.DataFrame(res.geral).to_excel(w, sheet_name="Dados gerais", index=False)
        pd.DataFrame(res.coberturas).to_excel(w, sheet_name="Coberturas", index=False)
        pd.DataFrame(res.exclusoes).to_excel(w, sheet_name="Exclusões", index=False)
        pd.DataFrame(res.franquias).to_excel(w, sheet_name="Franquias", index=False)
        pd.DataFrame(analise.get("diferencas_chave", [])).to_excel(w, sheet_name="Análise", index=False)
    c1.download_button("⬇️ Baixar planilha (.xlsx)", xls.getvalue(), "comparacao_do.xlsx")
    c2.download_button("⬇️ Baixar relatório (.md)", comparison_report_md(res, analise), "comparacao_do.md")


EXEMPLOS_SQL = {
    "Apólices por LMG": "SELECT id, seguradora, numero_apolice, lmg, premio, ROUND(premio*100.0/lmg, 3) AS taxa_pct "
                        "FROM apolices ORDER BY lmg DESC",
    "Quem cobre Lado C?": "SELECT a.seguradora, c.nome, c.limite, c.franquia FROM coberturas c "
                          "JOIN apolices a ON a.id = c.apolice_id WHERE c.categoria = 'Lado C'",
    "Exclusões por categoria": "SELECT e.categoria, COUNT(*) AS qtd, GROUP_CONCAT(DISTINCT a.seguradora) AS seguradoras "
                               "FROM exclusoes e JOIN apolices a ON a.id = e.apolice_id GROUP BY e.categoria ORDER BY qtd DESC",
    "Maiores franquias de cobertura": "SELECT a.seguradora, c.nome, c.franquia FROM coberturas c JOIN apolices a "
                                      "ON a.id = c.apolice_id WHERE c.franquia IS NOT NULL ORDER BY c.franquia DESC LIMIT 10",
}


def page_query() -> None:
    st.header("Consultar")
    repo = get_repo()
    rows = repo.list()
    if not rows:
        st.info("Nenhuma apólice armazenada.")
        return
    t1, t2 = st.tabs(["Pergunta em linguagem natural", "Consulta estruturada (SQL)"])
    with t1:
        opts = {r["id"]: f"#{r['id']} · {r['seguradora'] or r['arquivo']}" for r in rows}
        ids = st.multiselect("Apólices consideradas", list(opts), default=list(opts), format_func=opts.get)
        q = st.text_input("Pergunta", placeholder="Ex.: Qual apólice tem o maior prazo complementar? "
                                                   "Alguma cobre multas administrativas?")
        if st.button("Perguntar", type="primary", disabled=not (q and ids)):
            pipe = build_pipeline()
            if pipe:
                with st.spinner("Consultando…"):
                    try:
                        out, _ = pipe.ask(q, ids)
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Falha na consulta: {exc}")
                        return
                st.markdown(out["resposta"])
                with st.expander(f"Trechos usados ({len(out['trechos'])})"):
                    for t in out["trechos"]:
                        st.markdown(f"**{t['rotulo']} · pág. {t['pagina']}**")
                        st.text(t["texto"])
    with t2:
        ex = st.selectbox("Exemplos", list(EXEMPLOS_SQL))
        sql = st.text_area("SQL (somente SELECT)", EXEMPLOS_SQL[ex], height=100)
        st.caption("Tabelas: apolices, coberturas, exclusoes, paginas, comparacoes.")
        if st.button("Executar"):
            try:
                st.dataframe(pd.DataFrame(repo.query(sql)), hide_index=True, use_container_width=True)
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))


def page_about() -> None:
    st.header("Sobre a solução")
    doc = ROOT_DIR / "docs" / "ARQUITETURA.md"
    st.markdown(doc.read_text(encoding="utf-8") if doc.exists() else "Veja o README.md.")


PAGES = {"Enviar apólices": page_upload, "Apólices armazenadas": page_list, "Comparar": page_compare,
         "Consultar": page_query, "Sobre a solução": page_about}

PAGES[sidebar()]()
