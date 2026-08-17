# tabs/dashboard_tab.py

import streamlit as st
import pandas as pd
import plotly.express as px


def formatar_numero(numero):
    """Função auxiliar para formatar números no padrão brasileiro."""
    if pd.isna(numero) or not isinstance(numero, (int, float)):
        return "N/A"
    return f"{numero:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")


def obter_coluna_relevante(df, candidatas):
    """Retorna a primeira coluna candidata encontrada no DataFrame."""
    for col in candidatas:
        if col in df.columns:
            return col
    return None


def render(df):
    """
    Renderiza a aba do Dashboard com mapeamento de colunas interno e botões de exportação.
    """
    st.header("Painel Gerencial de Indicadores")
    st.write("Visão consolidada dos principais indicadores de desempenho e métricas operacionais.")

    # Identificar colunas prováveis por heurística inicial
    cols_cliente_cand = [c for c in df.columns if any(k in c for k in ['cliente', 'destinatario', 'razao_social', 'nome', 'empresa'])]
    cols_produto_cand = [c for c in df.columns if any(k in c for k in ['produto', 'servico', 'item', 'descricao'])]
    cols_qtd_cand = [c for c in df.columns if any(k in c for k in ['quantidade', 'qtd', 'volume'])]
    cols_valor_cand = [c for c in df.columns if any(k in c for k in ['valor_total', 'valor_nota', 'total', 'faturamento', 'valor'])]

    col_cliente_default = cols_cliente_cand[0] if cols_cliente_cand else None
    col_produto_default = cols_produto_cand[0] if cols_produto_cand else None
    col_qtd_default = cols_qtd_cand[0] if cols_qtd_cand else None

    # --- 1. SEÇÃO DE MAPEAMENTO DE COLUNAS ---
    with st.expander("Configuração de Mapeamento de Colunas", expanded=True):
        st.info("Indique as colunas correspondentes às dimensões de negócio para calibrar os gráficos automáticos.")
        
        lista_colunas_disponiveis = ["Selecione uma coluna..."] + sorted(df.columns.tolist())
        
        idx_cli = lista_colunas_disponiveis.index(col_cliente_default) if col_cliente_default in lista_colunas_disponiveis else 0
        idx_prod = lista_colunas_disponiveis.index(col_produto_default) if col_produto_default in lista_colunas_disponiveis else 0
        idx_qtd = lista_colunas_disponiveis.index(col_qtd_default) if col_qtd_default in lista_colunas_disponiveis else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            col_cliente = st.selectbox(
                "Coluna de Cliente (Nome/Razão Social):",
                options=lista_colunas_disponiveis,
                index=idx_cli,
                key="map_cliente"
            )
        with col2:
            col_produto = st.selectbox(
                "Coluna de Produto (Descrição):",
                options=lista_colunas_disponiveis,
                index=idx_prod,
                key="map_produto"
            )
        with col3:
            col_quantidade = st.selectbox(
                "Coluna de Quantidade de Itens:",
                options=lista_colunas_disponiveis,
                index=idx_qtd,
                key="map_quantidade"
            )

    coluna_cliente = None if col_cliente == "Selecione uma coluna..." else col_cliente
    coluna_produto = None if col_produto == "Selecione uma coluna..." else col_produto
    coluna_quantidade = None if col_quantidade == "Selecione uma coluna..." else col_quantidade

    # Identifica a melhor coluna de valor financeiro
    coluna_valor = obter_coluna_relevante(df, ['valor_total', 'valor_total_x', 'valor_nota_fiscal', 'valor', 'total'])
    if not coluna_valor:
        colunas_num = df.select_dtypes(include='number').columns
        coluna_valor = colunas_num[0] if len(colunas_num) > 0 else None

    # Identifica chave de documento/nota
    coluna_chave = obter_coluna_relevante(df, ['chave_de_acesso', 'chave_de_acesso_x', 'chave', 'id', 'numero_x', 'numero'])

    st.markdown("---")

    # --- 2. CÁLCULOS E EXIBIÇÃO DOS KPIs ---
    st.subheader("Indicadores Chave de Desempenho (KPIs)")
    
    valor_total_faturado = df[coluna_valor].sum() if (coluna_valor and coluna_valor in df.columns) else 0.0
    quantidade_total_itens = df[coluna_quantidade].sum() if (coluna_quantidade and coluna_quantidade in df.columns) else "N/A"
    num_notas_unicas = df[coluna_chave].nunique() if (coluna_chave and coluna_chave in df.columns) else len(df)
    num_clientes_unicos = df[coluna_cliente].nunique() if (coluna_cliente and coluna_cliente in df.columns) else "N/A"

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(label="Faturamento Total", value=f"R$ {formatar_numero(valor_total_faturado)}")
    with kpi2:
        valor_itens = f"{int(quantidade_total_itens):,}".replace(",", ".") if isinstance(quantidade_total_itens, (int, float)) else quantidade_total_itens
        st.metric(label="Volume de Itens Comercializados", value=valor_itens)
    with kpi3:
        st.metric(label="Documentos / Notas Únicas", value=num_notas_unicas)
    with kpi4:
        st.metric(label="Clientes Únicos", value=num_clientes_unicos)

    st.markdown("---")
    
    # --- 3. GRÁFICOS CURADOS ---
    st.subheader("Visualizações Analíticas Principais")
    col_a, col_b = st.columns(2)

    with col_a:
        if coluna_cliente and coluna_valor:
            top_10_clientes = df.groupby(coluna_cliente)[coluna_valor].sum().nlargest(10).sort_values()
            fig_clientes = px.bar(
                top_10_clientes, x=coluna_valor, y=top_10_clientes.index, orientation='h',
                title="Top 10 Clientes por Faturamento", labels={coluna_valor: 'Valor Total (R$)', 'y': 'Cliente'}, text_auto='.2s'
            )
            fig_clientes.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_clientes, use_container_width=True)

            if st.button("Adicionar Gráfico de Clientes ao Relatório", key="pin_clientes"):
                item = {
                    "type": "chart", 
                    "category": "dashboard", 
                    "title": "Gráfico: Top 10 Clientes por Faturamento", 
                    "content": {"titulo": "Top 10 Clientes por Valor Total", "dados": top_10_clientes, "metrica": "Valor Total (R$)", "fig": fig_clientes}
                }
                st.session_state.report_items.append(item)
                st.success("Gráfico de Clientes adicionado com sucesso.")
                st.rerun()
        else:
            st.info("Mapeie a coluna de Cliente para visualizar o ranking de clientes.")

    with col_b:
        if coluna_produto and coluna_valor:
            top_10_produtos = df.groupby(coluna_produto)[coluna_valor].sum().nlargest(10).sort_values()
            fig_produtos = px.bar(
                top_10_produtos, x=coluna_valor, y=top_10_produtos.index, orientation='h',
                title="Top 10 Produtos por Faturamento", labels={coluna_valor: 'Valor Total (R$)', 'y': 'Produto'}, text_auto='.2s'
            )
            fig_produtos.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_produtos, use_container_width=True)
            
            if st.button("Adicionar Gráfico de Produtos ao Relatório", key="pin_produtos"):
                item = {
                    "type": "chart", 
                    "category": "dashboard", 
                    "title": "Gráfico: Top 10 Produtos por Faturamento", 
                    "content": {"titulo": "Top 10 Produtos por Faturamento", "dados": top_10_produtos, "metrica": "Valor Total (R$)", "fig": fig_produtos}
                }
                st.session_state.report_items.append(item)
                st.success("Gráfico de Produtos adicionado com sucesso.")
                st.rerun()
        else:
            st.info("Mapeie a coluna de Produto para visualizar o ranking de produtos.")

    # Gráfico Temporal
    coluna_data = obter_coluna_relevante(df, ['data_emissao', 'data_emissao_x', 'data', 'data_hora_evento_mais_recente'])
    if coluna_data and coluna_valor and pd.api.types.is_datetime64_any_dtype(df[coluna_data]):
        df_tempo = df.dropna(subset=[coluna_data]).copy()
        if not df_tempo.empty:
            vendas_no_tempo = df_tempo.set_index(coluna_data).resample('D')[coluna_valor].sum()
            fig_tempo = px.line(
                vendas_no_tempo, x=vendas_no_tempo.index, y=coluna_valor,
                title="Evolução do Faturamento Diário", labels={coluna_data: 'Data', coluna_valor: 'Faturamento (R$)'}, markers=True
            )
            st.plotly_chart(fig_tempo, use_container_width=True)
            
            if st.button("Adicionar Gráfico Temporal ao Relatório", key="pin_tempo"):
                item = {
                    "type": "chart", 
                    "category": "dashboard", 
                    "title": "Gráfico: Evolução do Faturamento", 
                    "content": {"titulo": "Evolução do Faturamento Diário", "dados": vendas_no_tempo, "metrica": "Faturamento (R$)", "fig": fig_tempo}
                }
                st.session_state.report_items.append(item)
                st.success("Gráfico Temporal adicionado com sucesso.")
                st.rerun()

    st.markdown("---")

    # --- 4. FERRAMENTA DE ANÁLISE DETALHADA (DEEP DIVE) ---
    with st.expander("Análise Detalhada Multidimensional (Deep Dive)"):
        st.write("Configure cruzamentos personalizados entre dimensões e métricas.")
        
        colunas_numericas_expander = df.select_dtypes(include='number').columns.tolist()
        colunas_categoricas_expander = df.select_dtypes(include=['object', 'category']).columns.tolist()
        colunas_a_remover_num = [c for c in colunas_numericas_expander if any(k in c for k in ['modelo', 'serie', 'numero_x', 'numero_y', 'numero_produto'])]
        colunas_numericas_expander = [col for col in colunas_numericas_expander if col not in colunas_a_remover_num]
        
        if colunas_categoricas_expander and colunas_numericas_expander:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                default_dimensao = coluna_cliente if (coluna_cliente and coluna_cliente in colunas_categoricas_expander) else colunas_categoricas_expander[0]
                dimensao = st.selectbox("Agrupar por (Dimensão):", options=colunas_categoricas_expander, index=colunas_categoricas_expander.index(default_dimensao))
            with c2:
                metrica_default = coluna_valor if (coluna_valor and coluna_valor in colunas_numericas_expander) else colunas_numericas_expander[0]
                metrica = st.selectbox("Calcular (Métrica):", options=colunas_numericas_expander, index=colunas_numericas_expander.index(metrica_default))
            with c3:
                top_n = st.slider("Exibir Top N:", min_value=3, max_value=20, value=5, key="slider_detalhado")
            with c4:
                tipo_grafico = st.selectbox("Tipo de Gráfico:", options=["Barras", "Pizza"], key="grafico_detalhado")

            dados_agrupados = df.groupby(dimensao)[metrica].sum().nlargest(top_n)
            titulo_grafico = f"Top {top_n} {dimensao} por Soma de {metrica}"
            
            fig_detalhada = None
            if tipo_grafico == "Barras":
                fig_detalhada = px.bar(dados_agrupados, x=dados_agrupados.index, y=dados_agrupados.values, title=titulo_grafico, labels={'x': dimensao, 'y': metrica})
            elif tipo_grafico == "Pizza":
                fig_detalhada = px.pie(dados_agrupados, names=dados_agrupados.index, values=dados_agrupados.values, title=titulo_grafico)
            
            if fig_detalhada:
                st.plotly_chart(fig_detalhada, use_container_width=True)

                if st.button("Adicionar Gráfico Personalizado ao Relatório", key="pin_chart_detalhado"):
                    item_para_adicionar = {
                        "type": "chart", 
                        "category": "dashboard", 
                        "title": f"Gráfico: {titulo_grafico[:40]}...", 
                        "content": {"titulo": titulo_grafico, "dados": dados_agrupados, "metrica": metrica, "fig": fig_detalhada}
                    }
                    if item_para_adicionar not in st.session_state.report_items:
                        st.session_state.report_items.append(item_para_adicionar)
                        st.success("Gráfico adicionado ao relatório com sucesso.")
                        st.rerun()
                    else:
                        st.warning("Este gráfico já consta no relatório.")