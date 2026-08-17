# tabs/fiscal_tab.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Dicionário e função para enriquecer a análise de CFOP
CFOP_DESCRICOES = {
    '5102': 'Venda de mercadoria de terceiros', '6102': 'Venda de mercadoria de terceiros (outro estado)',
    '5405': 'Venda com ST (substituto)', '6404': 'Venda com ST (fora do estado)',
    '1202': 'Devolução de venda', '2202': 'Devolução de venda (outro estado)',
    '5910': 'Remessa em bonificação/brinde', '6910': 'Remessa em bonificação/brinde (outro estado)',
    '5949': 'Outra saída não especificada', '6949': 'Outra saída não especificada (outro estado)',
    '5101': 'Venda de produção própria', '6101': 'Venda de produção própria (outro estado)',
}

def get_cfop_categoria(cfop):
    cfop_str = str(cfop)
    if cfop_str.startswith(('51', '61')): return "Venda"
    if cfop_str.startswith(('12', '22')): return "Devolução"
    if cfop_str.startswith(('59', '69')): return "Outras Saídas"
    if cfop_str.startswith(('54', '64')): return "Venda com ST"
    return "Outras Operações"

def obter_coluna(df, candidatas):
    for col in candidatas:
        if col in df.columns:
            return col
    return None

# --- FUNÇÕES DE ANÁLISE ---
def analisar_consistencia(df):
    col_chave = obter_coluna(df, ['chave_de_acesso', 'chave_de_acesso_x', 'chave', 'id'])
    col_valor_nota = obter_coluna(df, ['valor_nota_fiscal', 'valor_nota_fiscal_x', 'valor_nota'])
    col_valor_total = obter_coluna(df, ['valor_total', 'valor_total_x', 'valor_item', 'total'])
    
    if not all([col_chave, col_valor_nota, col_valor_total]):
        return None
        
    check_df = df.groupby(col_chave).agg(
        valor_declarado_nota=(col_valor_nota, 'first'),
        soma_calculada_itens=(col_valor_total, 'sum')
    ).reset_index()
    
    check_df['diferenca'] = (check_df['valor_declarado_nota'] - check_df['soma_calculada_itens']).round(2)
    inconsistencias = check_df[check_df['diferenca'].abs() > 0.01].copy()
    if not inconsistencias.empty and col_chave in inconsistencias.columns:
        inconsistencias[col_chave] = inconsistencias[col_chave].astype(str)
    return inconsistencias

def analisar_operacoes_geo(df):
    col_uf_emit = obter_coluna(df, ['uf_emitente', 'uf_emitente_x', 'uf_emit'])
    col_uf_dest = obter_coluna(df, ['uf_destinatario', 'uf_destinatario_x', 'uf_dest', 'uf'])
    col_valor = obter_coluna(df, ['valor_total', 'valor_total_x', 'valor_nota_fiscal', 'total'])
    
    if not all([col_uf_emit, col_uf_dest, col_valor]):
        return None
        
    df_operacao = df.copy()
    df_operacao['tipo_de_operacao'] = np.where(df[col_uf_emit] == df[col_uf_dest], 'Interna (Mesmo Estado)', 'Interestadual (Outro Estado)')
    return df_operacao.groupby('tipo_de_operacao')[col_valor].sum()

def analisar_cfop(df):
    col_cfop = obter_coluna(df, ['cfop', 'cfop_x', 'codigo_cfop'])
    col_valor = obter_coluna(df, ['valor_total', 'valor_total_x', 'valor_nota_fiscal', 'total'])
    
    if not col_cfop or not col_valor:
        return None
        
    df_cfop = df.copy()
    df_cfop[col_cfop] = df_cfop[col_cfop].astype(str).str.replace('.0', '', regex=False)
    cfop_analysis = df_cfop.groupby(col_cfop)[col_valor].agg(['sum', 'count']).rename(
        columns={'sum': 'Valor Total', 'count': 'Qtd. de Itens'}
    ).sort_values(by='Valor Total', ascending=False)
    
    cfop_analysis['descricao'] = cfop_analysis.index.map(CFOP_DESCRICOES).fillna('Outra Operação Fiscal')
    cfop_analysis['label_grafico'] = cfop_analysis.index + ' - ' + cfop_analysis['descricao']
    cfop_analysis['categoria'] = cfop_analysis.index.map(get_cfop_categoria)
    return cfop_analysis.head(15)

# --- FUNÇÃO PRINCIPAL DE RENDERIZAÇÃO DA ABA ---
def render(df):
    st.header("Auditoria e Conformidade Fiscal")
    st.write("Verificações automáticas de integridade contábil e conformidade regulatória sobre os registros fiscais.")
    
    # Análise 1: Consistência de Valores
    st.markdown("---")
    st.subheader("1. Consistência de Valores (Valor Declarado vs. Soma dos Itens)")
    inconsistencias_df = analisar_consistencia(df)
    if inconsistencias_df is not None:
        if inconsistencias_df.empty:
            st.success("Nenhuma inconsistência identificada. Os valores declarados conferem integralmente com o somatório dos itens.")
        else:
            st.warning(f"Identificada(s) {len(inconsistencias_df)} nota(s) fiscal(is) com divergência de valores.")
            st.dataframe(inconsistencias_df)
            if st.button("Adicionar Tabela de Inconsistências ao Relatório", key="pin_inconsistencias"):
                item = {
                    "type": "dataframe", 
                    "category": "fiscal", 
                    "title": "Tabela: Inconsistências de Valor Fiscal", 
                    "content": {"titulo": "Notas com Divergência entre Valor Declarado e Soma dos Itens", "dados": inconsistencias_df}
                }
                st.session_state.report_items.append(item)
                st.success("Tabela de inconsistências adicionada com sucesso.")
                st.rerun()
    else:
        st.info("Análise de consistência indisponível (colunas de valor da nota e valor do item não identificadas).")

    # Análise 2: Natureza das Operações
    st.markdown("---")
    st.subheader("2. Distribuição Geográfica de Operações (Internas vs. Interestaduais)")
    operacoes_df = analisar_operacoes_geo(df)
    if operacoes_df is not None and not operacoes_df.empty:
        fig_operacoes = px.pie(operacoes_df, names=operacoes_df.index, values=operacoes_df.values, title='Distribuição de Faturamento por Tipo de Operação', hole=0.3)
        st.plotly_chart(fig_operacoes, use_container_width=True)
        if st.button("Adicionar Gráfico Geográfico ao Relatório", key="pin_operacoes_chart"):
            item = {
                "type": "chart", 
                "category": "fiscal", 
                "title": "Gráfico: Distribuição por Tipo de Operação", 
                "content": {"titulo": "Distribuição de Faturamento por Tipo de Operação", "fig": fig_operacoes}
            }
            st.session_state.report_items.append(item)
            st.success("Gráfico adicionado ao relatório com sucesso.")
            st.rerun()
    else:
        st.info("Análise geográfica indisponível (colunas de UF do emitente e destinatário não identificadas).")
        
    # Análise 3: Análise por CFOP
    st.markdown("---")
    st.subheader("3. Análise por Código Fiscal de Operações e Prestações (CFOP)")
    cfop_df = analisar_cfop(df)
    if cfop_df is not None and not cfop_df.empty:
        fig_cfop = px.bar(
            cfop_df, x='Valor Total', y='label_grafico', orientation='h', 
            title='Top 15 Operações Fiscais (CFOPs) por Valor Total', color='categoria', hover_data=['Qtd. de Itens']
        )
        fig_cfop.update_layout(yaxis={'categoryorder':'total ascending'}, legend_title_text='Categoria')
        st.plotly_chart(fig_cfop, use_container_width=True)
        
        if st.button("Adicionar Gráfico de CFOP ao Relatório", key="pin_cfop_chart"):
            item = {
                "type": "chart", 
                "category": "fiscal", 
                "title": "Gráfico: Top 15 Operações CFOP", 
                "content": {"titulo": "Top 15 Operações (CFOPs) por Valor Total", "fig": fig_cfop}
            }
            st.session_state.report_items.append(item)
            st.success("Gráfico de CFOP adicionado ao relatório com sucesso.")
            st.rerun()
        with st.expander("Visualizar Tabela Analítica por CFOP"):
            st.dataframe(cfop_df)
    else:
        st.info("Análise de CFOP indisponível (coluna CFOP não identificada na base de dados).")