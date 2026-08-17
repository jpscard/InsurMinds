# app.py

import sys

# Reconfigura encoding de saída para terminais Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import streamlit as st
import pandas as pd
from utils.processing import processar_arquivos, processar_zip 
from tabs import agent_tab, insights_tab, dashboard_tab, report_tab, fiscal_tab

# Configuração da página
st.set_page_config(
    page_title="Agente Inteligente - Análise de CSVs e Notas Fiscais",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Interface Inteligente para Análise de Dados e Notas Fiscais")
st.caption("Desafio 4 - Agente inteligente com capacidade de interpretar e responder perguntas em linguagem natural sobre arquivos CSV.")

# --- ESTADO DA SESSÃO ---
if 'report_items' not in st.session_state:
    st.session_state.report_items = []
if 'df' not in st.session_state:
    st.session_state.df = None
if 'data_dict' not in st.session_state:
    st.session_state.data_dict = None
if 'files_loaded' not in st.session_state:
    st.session_state.files_loaded = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'insights_gerados' not in st.session_state:
    st.session_state.insights_gerados = None

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Configurações & Credenciais")
    
    # Tenta carregar a chave de API dos secrets ou permite digitar na interface
    google_api_key = None
    try:
        google_api_key = st.secrets.get("GOOGLE_API_KEY", None)
    except Exception:
        pass

    if not google_api_key:
        google_api_key = st.text_input(
            "Google Gemini API Key:",
            type="password",
            help="Obtenha sua chave gratuita em: https://aistudio.google.com/app/apikey"
        )
        if google_api_key:
            google_api_key = google_api_key.strip().strip('"').strip("'")
            st.success("Chave de API configurada!")
    else:
        google_api_key = str(google_api_key).strip().strip('"').strip("'")
        st.success("Chave de API do Google carregada dos segredos!")

    # Seleção de Modelo Gemini
    modelos_opcoes = [
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = "gemini-2.0-flash"

    st.session_state.selected_model = st.selectbox(
        "Modelo Gemini:",
        options=modelos_opcoes,
        index=modelos_opcoes.index(st.session_state.selected_model) if st.session_state.selected_model in modelos_opcoes else 0,
        help="Selecione o modelo do Gemini desejado. Caso o modelo escolhido retorne 404, o sistema tentará os demais automaticamente."
    )

    st.markdown("---")
    st.header("🛒 Itens para o Relatório")
    if st.session_state.report_items:
        for i, item in enumerate(st.session_state.report_items):
            st.info(f"Item {i+1}: {item['title']}")
        if st.button("Limpar Itens do Relatório", use_container_width=True):
            st.session_state.report_items = []
            st.rerun()
    else:
        st.info("Nenhum item adicionado ao relatório ainda.")

    if st.session_state.df is not None:
        st.markdown("---")
        if st.button("🔄 Carregar Novo Arquivo", use_container_width=True):
            st.session_state.df = None
            st.session_state.data_dict = None
            st.session_state.files_loaded = []
            st.session_state.chat_history = []
            st.session_state.insights_gerados = None
            st.rerun()

# --- INTERFACE A: CARGA DOS DADOS (UPLOAD E PROCESSAMENTO DO ARQUIVO) ---
if st.session_state.df is None:
    upload_container = st.container(border=True)
    with upload_container:
        st.subheader("📁 Interface A – Carga dos Dados")
        st.write("Envie seus dados para análise. Você pode:")
        st.markdown("""
        - 📦 **Enviar um arquivo compactado (`.ZIP`)** contendo um ou múltiplos arquivos `.CSV` (ex: `202401_NFs.zip` ou `202505_NFe.zip`).
        - 📄 **Selecionar múltiplos arquivos `.CSV` diretamente** (ex: selecionar Cabeçalho e Itens juntos).
        - 📖 **Incluir opcionalmente um Dicionário de Dados** (`.txt`, `.md`, `.json`, `.csv`).
        """)
        
        uploaded_files = st.file_uploader(
            "Selecione o arquivo .ZIP ou os arquivos .CSV:",
            type=["zip", "csv", "txt", "md", "json"],
            accept_multiple_files=True,
            help="Você pode selecionar um arquivo .ZIP ou segurar Ctrl/Shift para selecionar múltiplos arquivos CSV ao mesmo tempo."
        )

        if uploaded_files:
            try:
                with st.spinner("Processando e integrando os dados..."):
                    df_carregado, data_dict_extraido, files_extraidos = processar_arquivos(uploaded_files)
                    st.session_state.df = df_carregado
                    st.session_state.data_dict = data_dict_extraido
                    st.session_state.files_loaded = files_extraidos

                st.success(f"✅ Sucesso! {len(df_carregado):,} registros carregados a partir de {len(files_extraidos)} arquivo(s).")
                st.rerun()

            except Exception as e:
                st.error(f"Falha ao processar o(s) arquivo(s): {e}")
                st.session_state.df = None

# --- INTERFACE B: CONSULTA & ANÁLISE COM AGENTES ---
if st.session_state.df is not None:
    df_original = st.session_state.df
    
    # Exibe badge de metadados da carga
    info_cols = st.columns([3, 1])
    with info_cols[0]:
        dict_status = "✅ Dicionário de Dados Identificado" if st.session_state.data_dict else "ℹ️ Sem dicionário de dados específico no ZIP"
        st.markdown(f"**Base Carregada:** `{', '.join(st.session_state.files_loaded)}` | **{len(df_original):,} linhas** | **{len(df_original.columns)} colunas** | *{dict_status}*")
    
    # --- SEÇÃO DE FILTROS GLOBAIS RESILIENTES ---
    # Identifica colunas de UF e Data se existirem
    col_uf = None
    for cand in ['uf_destinatario', 'uf_destinatario_x', 'uf', 'uf_emitente', 'estado']:
        if cand in df_original.columns:
            col_uf = cand
            break

    col_data = None
    for cand in ['data_emissao', 'data_emissao_x', 'data', 'data_hora_evento_mais_recente']:
        if cand in df_original.columns and pd.api.types.is_datetime64_any_dtype(df_original[cand]):
            col_data = cand
            break

    df_filtrado = df_original.copy()

    if col_uf or col_data:
        with st.expander("🔍 Filtros Globais (Opcional)", expanded=False):
            c_f1, c_f2 = st.columns([1, 2])
            
            ufs_selecionadas = None
            if col_uf:
                with c_f1:
                    ufs_disponiveis = sorted(df_original[col_uf].dropna().unique().tolist())
                    ufs_selecionadas = st.multiselect(
                        f"Filtrar por {col_uf.replace('_', ' ').title()}:",
                        options=ufs_disponiveis,
                        default=ufs_disponiveis
                    )

            data_selecionada = None
            if col_data:
                with c_f2:
                    datas_validas = df_original[col_data].dropna()
                    if not datas_validas.empty:
                        data_min = datas_validas.min().date()
                        data_max = datas_validas.max().date()
                        if data_min and data_max:
                            data_selecionada = st.date_input(
                                "Filtrar por Período:",
                                value=(data_min, data_max),
                                min_value=data_min,
                                max_value=data_max,
                            )

            # Aplica os filtros
            if ufs_selecionadas and col_uf:
                df_filtrado = df_filtrado[df_filtrado[col_uf].isin(ufs_selecionadas)]
            
            if data_selecionada and len(data_selecionada) == 2 and col_data:
                df_filtrado = df_filtrado[
                    (df_filtrado[col_data].dt.date >= data_selecionada[0]) &
                    (df_filtrado[col_data].dt.date <= data_selecionada[1])
                ]

            st.caption(f"Exibindo {len(df_filtrado):,} de {len(df_original):,} registros após filtros.")

    st.markdown("---")

    # --- ABAS DA APLICAÇÃO ---
    tab_agent, tab_insights, tab_dashboard, tab_fiscal, tab_report = st.tabs([
        "💬 Agente Q&A (Linguagem Natural)", 
        "💡 Insights Automáticos da IA",
        "📊 Painel / Dashboard", 
        "✅ Auditoria & Análise Fiscal", 
        "📄 Montador de Relatório"
    ])

    # 1. Agente Q&A
    with tab_agent:
        agent_tab.render(df_original, google_api_key, data_dict=st.session_state.data_dict)
    
    # 2. Insights Automáticos
    with tab_insights:
        insights_tab.render(df_original, google_api_key, data_dict=st.session_state.data_dict)
        
    # 3. Dashboard
    with tab_dashboard:
        dashboard_tab.render(df_filtrado) 
        
    # 4. Análise Fiscal
    with tab_fiscal:
        fiscal_tab.render(df_filtrado)
        
    # 5. Montador de Relatório
    with tab_report:
        report_tab.render(df_original, google_api_key)