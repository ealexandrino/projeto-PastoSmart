import streamlit as st

st.title("Teste de Conexão")
st.write("Tentando conectar na planilha...")

try:
    conn = st.connection("gsheets", type="gsheets")
    df = conn.read(worksheet="Dados_limpos")
    st.success("Conectado com sucesso!")
    st.dataframe(df)
except Exception as e:
    st.error(f"Erro ao conectar: {e}")
