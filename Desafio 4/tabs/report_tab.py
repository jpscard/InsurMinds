# tabs/report_tab.py

import streamlit as st
from utils.processing import criar_documento_word
import plotly.express as px
from utils.callbacks import PolishedCallbackHandler
from utils.agent_utils import invocar_agente_com_fallback

def render(df, google_api_key):
    st.header("📄 Montador de Relatório Personalizado")
    st.write("Visualize, organize e exporte os insights que você selecionou.")
    st.markdown("---")

    if not st.session_state.report_items:
        st.info("Nenhum item foi adicionado ao relatório. Navegue pelas outras abas e clique em '📌 Adicionar ao Relatório' para começar.")
        
    else:
        st.subheader("Itens Selecionados para o Relatório:")
        
        # Lógica de preview interativo para cada item pinado
        for i, item in enumerate(st.session_state.report_items):
            with st.container(border=True):
                col1, col2 = st.columns([0.9, 0.1])
                with col1:
                    # Exibe o conteúdo do item baseado no seu tipo
                    if item['type'] == 'qa' or item.get('category') == 'insight_ia':
                        st.info(f"**[Pergunta & Resposta]** - {item['title']}")
                        st.write(f"**P:** {item['content']['pergunta']}")
                        st.write(f"**R:** {item['content']['resposta']}")

                    elif item['type'] == 'dataframe':
                        st.info(f"**[Tabela de Dados]** - {item['content']['titulo']}")
                        st.dataframe(item['content']['dados'])

                    elif item['type'] == 'chart':
                        st.info(f"**[Gráfico]** - {item['content']['titulo']}")
                        st.plotly_chart(item['content']['fig'], use_container_width=True, key=f"report_chart_{i}")
                    
                    elif item['type'] == 'summary':
                        st.info(f"**[Sumário da IA]** - {item['title']}")
                        st.write(item['content']['texto'])
                
                with col2:
                    # Botão para remover o item da lista
                    if st.button("❌ Remover", key=f"remove_{i}", use_container_width=True):
                        st.session_state.report_items.pop(i)
                        st.rerun()

    st.markdown("---")
    st.header("Finalizar e Exportar")

    # --- LÓGICA DO SUMÁRIO COM IA ---
    if st.button("🤖 Gerar Sumário Executivo com IA e Adicionar ao Topo", use_container_width=True):
        if not google_api_key:
            st.warning("A chave de API do Google é necessária para esta funcionalidade.")
        else:
            with st.spinner("O agente está lendo todos os dados para criar um sumário executivo..."):
                try:
                    handler = PolishedCallbackHandler(agent_name="Analista Estratégico de IA")
                    preferred_model = st.session_state.get('selected_model', 'gemini-2.0-flash')

                    prompt_sumario = """
                    Analisando o DataFrame como um todo, escreva um sumário executivo conciso em 2 ou 3 bullet points.
                    Destaque os insights mais importantes sobre o faturamento geral, os produtos ou clientes de maior destaque,
                    e qualquer padrão ou anomalia notável que você encontrar.
                    """
                    
                    resposta, _ = invocar_agente_com_fallback(
                        df=df,
                        google_api_key=google_api_key,
                        prefix="Você é um analista estratégico sênior. Responda em português com clareza e precisão.",
                        input_data={"input": prompt_sumario},
                        preferred_model=preferred_model,
                        temperature=0.2,
                        handler=handler
                    )
                    
                    # Cria o item do relatório
                    item_sumario = {
                        "type": "summary",
                        "category": "summary_ia",
                        "title": "Sumário Executivo Gerado por IA",
                        "content": {"texto": resposta.get('output', 'Sem resumo gerado.')}
                    }
                    
                    # Adiciona o sumário no TOPO da lista de itens
                    st.session_state.report_items.insert(0, item_sumario)
                    st.success("Sumário gerado e adicionado ao topo do relatório!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Falha ao gerar o sumário: {e}")

    # Botão de download para o documento Word
    if st.session_state.report_items:
        with st.spinner("Montando seu relatório profissional..."):
            word_buffer = criar_documento_word(st.session_state.report_items)
        
        st.download_button(
            label="📥 Exportar Relatório Final para Word (.docx)",
            data=word_buffer,
            file_name="relatorio_final_analise_nfs.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )