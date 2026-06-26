import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("Teste de Conexão")
st.write("Tentando conectar na planilha...")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Dados_limpos")
    st.success("Conectado com sucesso!")
    st.dataframe(df)

except Exception as e:
    st.error(f"Erro ao conectar: {e}")
