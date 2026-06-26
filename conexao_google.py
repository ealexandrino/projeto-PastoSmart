import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# CONEXÃO COM GOOGLE SHEETS
# =====================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


@st.cache_resource
def conectar_google():

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )

    gc = gspread.authorize(credentials)

    return gc


@st.cache_data(ttl=300)
def carregar_planilha(nome_aba):

    gc = conectar_google()

    planilha = gc.open_by_key(
        "1DFy0jTJbv5Mv1n-KtJkTeUuz4uXNjp-khKhPZpQ1m6w"
    )

    aba = planilha.worksheet(nome_aba)

    dados = aba.get_all_records()

    return pd.DataFrame(dados)
