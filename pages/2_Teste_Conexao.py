import streamlit as st
from conexao_google import carregar_planilha

st.title("Teste de Conexão")

try:

    df = carregar_planilha("Dados_limpos")

    st.success("✅ Conectado com sucesso!")

    st.write(f"Linhas: {len(df)}")

    st.dataframe(df.head())

except Exception as e:

    st.error(e)
