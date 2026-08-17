# tabs/report_tab.py

import streamlit as st
from utils.processing import criar_documento_word
import plotly.express as px
from utils.callbacks import PolishedCallbackHandler
from utils.agent_utils import invocar_agente_com_fallback

def render(df, google_api_key):
    st.header("Montador de Relatório Executivo")
    st.write("Consolide, organize e exporte os tópicos analíticos selecionados durante a sessão.")
    st.markdown("---")

    if not st.session_state.report_items:
        st.info("Nenhum item adicionado ao relatório. Navegue pelas demais abas e selecione 'Adicionar ao Relatório' nos tópicos de interesse.")
        
    else:
        st.subheader("Itens Selecionados para o Relatório:")
        
        # Lógica de preview interativo para cada item pinado
        for i, item in enumerate(st.session_state.report_items):
            with st.container(border=True):
                col1, col2 = st.columns([0.9, 0.1])
                with col1:
                    # Exibe o conteúdo do item baseado no seu tipo
                    if item['type'] == 'qa' or item.get('category') == 'insight_ia':
                        st.info(f"**[Consulta Analítica]** - {item['title']}")
                        st.write(f"**Pergunta:** {item['content']['pergunta']}")
                        st.write(f"**Resposta:** {item['content']['resposta']}")

                    elif item['type'] == 'dataframe':
                        st.info(f"**[Tabela de Dados]** - {item['content']['titulo']}")
                        st.dataframe(item['content']['dados'])

                    elif item['type'] == 'chart':
                        st.info(f"**[Gráfico]** - {item['content']['titulo']}")
                        st.plotly_chart(item['content']['fig'], use_container_width=True, key=f"report_chart_{i}")
                    
                    elif item['type'] == 'summary':
                        st.info(f"**[Sumário Executivo]** - {item['title']}")
                        st.write(item['content']['texto'])
                
                with col2:
                    # Botão para remover o item da lista
                    if st.button("Remover", key=f"remove_{i}", use_container_width=True):
                        st.session_state.report_items.pop(i)
                        st.rerun()

    st.markdown("---")
    st.header("Finalização e Exportação")

    # --- LÓGICA DO SUMÁRIO COM IA ---
    if st.button("Gerar Sumário Executivo com IA e Adicionar ao Topo", use_container_width=True):
        if not google_api_key:
            st.warning("A chave de API do Google Gemini é necessária para esta funcionalidade.")
        else:
            with st.spinner("Processando base de dados para síntese executiva..."):
                try:
                    handler = PolishedCallbackHandler(agent_name="Analista Estratégico")
                    preferred_model = st.session_state.get('selected_model', 'gemini-2.0-flash')

                    prompt_sumario = """
                    Analisando o DataFrame como um todo, escreva um sumário executivo conciso em 2 ou 3 bullet points.
                    Destaque os insights mais importantes sobre o faturamento geral, os produtos ou clientes de maior destaque,
                    e qualquer padrão ou anomalia notável que você encontrar.
                    """
                    
                    resposta, _ = invocar_agente_com_fallback(
                        df=df,
                        google_api_key=google_api_key,
                        prefix="Você é um analista estratégico sênior. Responda em português com clareza e precisão formal.",
                        input_data={"input": prompt_sumario},
                        preferred_model=preferred_model,
                        temperature=0.2,
                        handler=handler
                    )
                    
                    # Cria o item do relatório
                    item_sumario = {
                        "type": "summary",
                        "category": "summary_ia",
                        "title": "Sumário Executivo Consolidado",
                        "content": {"texto": resposta.get('output', 'Sem resumo gerado.')}
                    }
                    
                    # Adiciona o sumário no TOPO da lista de itens
                    st.session_state.report_items.insert(0, item_sumario)
                    st.success("Sumário executivo gerado e posicionado no início do relatório.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Falha ao gerar o sumário executivo: {e}")

    # Botão de download para o documento Word
    if st.session_state.report_items:
        with st.spinner("Compilando documento executivo..."):
            word_buffer = criar_documento_word(st.session_state.report_items)
        
        st.download_button(
            label="Exportar Relatório Consolidado (.docx)",
            data=word_buffer,
            file_name="relatorio_auditoria_fiscal.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )