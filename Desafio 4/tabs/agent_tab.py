# tabs/agent_tab.py

import streamlit as st
from utils.callbacks import PolishedCallbackHandler
from utils.agent_utils import invocar_agente_com_fallback


def render(df, google_api_key, data_dict=None):
    """
    Renderiza a aba do Agente de Q&A (Perguntas e Respostas em Linguagem Natural).
    """
    st.header("💬 Converse com seus Dados")
    st.write("Faça perguntas em linguagem natural sobre o conjunto de dados carregado. O agente utilizará ferramentas de análise e Python para responder com precisão.")

    # Se houver dicionário de dados disponível, exibe para referência
    if data_dict:
        with st.expander("📖 Visualizar Dicionário de Dados do Arquivo"):
            st.markdown(f"```\n{data_dict}\n```")

    # Sugestões de perguntas rápidas para facilitar o teste
    with st.expander("💡 Sugestões de perguntas para testar"):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("- *Qual foi o faturamento total e o total de notas fiscais emitidas?*")
            st.markdown("- *Quais foram os 5 maiores clientes em valor total de compras? Formate em tabela.*")
        with col_s2:
            st.markdown("- *Qual produto apresentou o maior volume de vendas em quantidade?*")
            st.markdown("- *Quais são os 3 estados (UFs) com maior volume financeiro?*")

    # Formulário para o usuário inserir a pergunta
    with st.form(key="qa_form"):
        pergunta_usuario = st.text_input(
            "Sua pergunta sobre os dados:",
            placeholder="Ex: Quais são os 5 principais produtos vendidos em valor total? Apresente em formato de tabela.",
            key="pergunta_input"
        )
        submitted = st.form_submit_button("Perguntar ao Agente 🤖", type="primary")

    # Lógica executada quando o formulário é enviado
    if submitted and pergunta_usuario:
        if not google_api_key:
            st.warning("⚠️ A chave de API do Google é necessária para executar o agente.")
        else:
            with st.spinner("O Agente Inteligente está analisando os dados... 🧠 (Acompanhe o raciocínio no terminal)"):
                
                # Monta o prefixo do prompt com o dicionário de dados (se houver)
                prefix_dict_info = ""
                if data_dict:
                    prefix_dict_info = f"\n\nContexto adicional do Dicionário de Dados:\n{data_dict}\n"

                AGENT_PREFIX = (
                    "Você é um especialista em análise de dados e auditoria fiscal de arquivos CSV. "
                    "Sua missão é interpretar rigorosamente as perguntas do usuário e consultar o DataFrame `df` fornecido. "
                    "Regras essenciais:\n"
                    "1. Sempre execute consultas precisas em Python (usando pandas) sobre o DataFrame `df`.\n"
                    "2. Quando a resposta contiver rankings, comparações ou múltiplos itens/valores, apresente-a formatada em uma TABELA MARKDOWN clara e legível.\n"
                    "3. Formate valores monetários no padrão brasileiro (ex: R$ 1.234,56).\n"
                    "4. Baseie-se estritamente nas colunas e valores existentes nos dados, sem fazer suposições.\n"
                    + prefix_dict_info
                )
                
                try:
                    handler = PolishedCallbackHandler(agent_name="Especialista em Análise de Dados")
                    preferred_model = st.session_state.get('selected_model', 'gemini-2.0-flash')

                    resposta, modelo_utilizado = invocar_agente_com_fallback(
                        df=df,
                        google_api_key=google_api_key,
                        prefix=AGENT_PREFIX,
                        input_data={"input": pergunta_usuario},
                        preferred_model=preferred_model,
                        temperature=0.0,
                        handler=handler
                    )

                    # Adiciona a conversa ao histórico da sessão
                    st.session_state.chat_history.insert(0, {
                        "pergunta": pergunta_usuario, 
                        "resposta": resposta.get('output', 'Sem resposta gerada.'),
                        "modelo": modelo_utilizado
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"Ocorreu um erro ao executar o agente: {e}")

    st.markdown("---")

    # Exibe o histórico de conversas da sessão atual
    if st.session_state.chat_history:
        st.subheader("Histórico de Perguntas & Respostas")
        for i, conversa in enumerate(st.session_state.chat_history):
            with st.container(border=True):
                st.markdown(f"**🙋 Você perguntou:** {conversa['pergunta']}")
                st.markdown(f"**🤖 Resposta do Agente:**\n\n{conversa['resposta']}")
                
                # Botão para adicionar a conversa ao relatório final
                if st.button("📌 Adicionar ao Relatório", key=f"pin_qa_{i}"):
                    item_para_adicionar = {
                        "type": "qa", 
                        "category": "q&a",
                        "title": f"Pergunta: {conversa['pergunta'][:50]}...",
                        "content": conversa
                    }
                    if item_para_adicionar not in st.session_state.report_items:
                        st.session_state.report_items.append(item_para_adicionar)
                        st.success("Adicionado ao relatório! Veja na barra lateral.")
                        st.rerun()
                    else:
                        st.warning("Este item já foi adicionado ao relatório.")