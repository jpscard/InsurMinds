import streamlit as st
import pandas as pd

def render(df):
    """
    Renderiza uma aba de diagnóstico para inspecionar o DataFrame.
    """
    st.header("🐞 Painel de Diagnóstico do DataFrame")
    st.warning("O objetivo desta aba é inspecionar o estado exato do DataFrame após o carregamento e limpeza para resolver erros de 'KeyError'.")

    st.subheader("1. Lista Exata dos Nomes das Colunas")
    st.write("Estes são os nomes de colunas que o programa realmente enxerga. Procure nesta lista o nome correto da coluna de quantidade.")
    st.code(df.columns.tolist())

    st.subheader("2. Visualização das Primeiras Linhas do DataFrame")
    st.write("Verifique os dados na tabela abaixo para confirmar qual coluna contém as quantidades.")
    st.dataframe(df.head())