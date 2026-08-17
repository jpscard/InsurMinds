# tabs/insights_tab.py

import streamlit as st
from utils.callbacks import PolishedCallbackHandler
from utils.agent_utils import invocar_agente_com_fallback
from tenacity import retry, stop_after_attempt, wait_fixed

# Lista de perguntas pré-definidas para a análise automática de negócios
PERGUNTAS_RELEVANTES = [
    "Qual o faturamento total neste conjunto de dados? (calcule a soma dos valores totais)",
    "Qual o número total de notas fiscais únicas (use a coluna que representa a chave de acesso ou id da nota)?",
    "Qual o valor médio por nota fiscal? (calcule o faturamento total dividido pelo número de notas fiscais únicas)",
    "Quem foi o cliente (razão social ou nome do destinatário) que mais comprou em valor monetário total?",
    "Quais são os 5 produtos (descrição do produto) mais vendidos em valor total? Apresente em formato de lista ou tabela com valor.",
    "Quais são os 5 produtos mais vendidos em quantidade de itens? Apresente em formato de lista ou tabela com quantidade.",
    "Qual o número total de clientes (destinatários) únicos?",
    "Quais os 3 estados/UFs (UF do destinatário) que mais receberam valor em mercadorias? Apresente os estados e os valores.",
    "Qual a principal operação fiscal (CFOP ou natureza da operação) em termos de valor total faturado?",
    "Faça um resumo executivo sintetizando os principais destaques deste conjunto de dados em 2 a 3 frases."
]

def render(df, google_api_key, data_dict=None):
    st.header("💡 Insights Automáticos Gerados por IA")
    st.write("Clique no botão abaixo para que o agente de IA execute uma bateria de análises fundamentais de negócio sobre os dados carregados.")

    if data_dict:
        with st.expander("📖 Dicionário de Dados Carregado"):
            st.markdown(f"```\n{data_dict}\n```")

    if st.button("🚀 Gerar Relatório de Insights Automáticos", type="primary", use_container_width=True):
        if 'insights_gerados' in st.session_state:
            del st.session_state['insights_gerados']
        
        if not google_api_key:
            st.warning("⚠️ A chave de API do Google é necessária para executar o agente.")
            return

        with st.spinner("O agente está analisando os dados... Isso pode levar alguns instantes."):
            try:
                dict_context = f"\n\nContexto do Dicionário de Dados:\n{data_dict}\n" if data_dict else ""
                AGENT_PREFIX = (
                    "Você é um analista de dados sênior e auditor fiscal. "
                    "Analise o DataFrame `df` para responder com precisão matemática às perguntas solicitadas. "
                    "Formate valores monetários em padrão brasileiro (R$ 1.234,56). "
                    "Quando solicitado listas ou rankings, organize as respostas com clareza."
                    + dict_context
                )

                preferred_model = st.session_state.get('selected_model', 'gemini-2.0-flash')
                resultados = []
                progress_bar = st.progress(0, text="Iniciando análise dos dados...")

                for i, pergunta in enumerate(PERGUNTAS_RELEVANTES):
                    progresso_texto = f"Analisando ({i+1}/{len(PERGUNTAS_RELEVANTES)}): {pergunta[:45]}..."
                    progress_bar.progress((i + 1) / len(PERGUNTAS_RELEVANTES), text=progresso_texto)
                    
                    handler = PolishedCallbackHandler(agent_name=f"Analista Automático #{i+1}")
                    resposta, _ = invocar_agente_com_fallback(
                        df=df,
                        google_api_key=google_api_key,
                        prefix=AGENT_PREFIX,
                        input_data={"input": pergunta},
                        preferred_model=preferred_model,
                        temperature=0.0,
                        handler=handler
                    )
                    
                    resultados.append({"pergunta": pergunta, "resposta": resposta.get('output', 'Sem resposta.')})

                progress_bar.empty()
                st.session_state.insights_gerados = resultados
                st.rerun()

            except Exception as e:
                st.error(f"Ocorreu um erro durante a geração dos insights: {e}")
                st.session_state.insights_gerados = None

    if 'insights_gerados' in st.session_state and st.session_state.insights_gerados is not None:
        st.markdown("---")
        st.subheader("Resultados da Análise Automática")
        
        for i, resultado in enumerate(st.session_state.insights_gerados):
            with st.expander(f"**{i+1}. {resultado['pergunta']}**", expanded=(i < 3)):
                st.markdown(f"**Resposta do Agente:**\n\n{resultado['resposta']}")
                
                if st.button("📌 Adicionar Insight ao Relatório", key=f"pin_insight_{i}"):
                    item = {
                        "type": "qa", 
                        "category": "insight_ia", 
                        "title": f"Insight IA: {resultado['pergunta'][:40]}...", 
                        "content": resultado
                    }
                    if item not in st.session_state.report_items:
                        st.session_state.report_items.append(item)
                        st.success("Insight adicionado ao relatório!")
                        st.rerun()
                    else:
                        st.warning("Este insight já foi adicionado ao relatório.")