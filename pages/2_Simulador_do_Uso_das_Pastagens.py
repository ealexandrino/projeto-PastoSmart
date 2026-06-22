import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
import urllib.parse
import json
import os
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_DISPONIVEL = True
except ImportError:
    FOLIUM_DISPONIVEL = False

st.set_page_config(page_title="Planejamento das Pastagens", page_icon="📈", layout="wide")

if "simulacoes_salvas" not in st.session_state: st.session_state["simulacoes_salvas"] = []
if "contador_filtros" not in st.session_state: st.session_state["contador_filtros"] = 0

st.title("📈 Planejamento das Pastagens")
st.markdown("---")

SHEET_ID = "1DFy0jTJbv5Mv1n-KtJkTeUuz4uXNjp-khKhPZpQ1m6w"
GID = "853924016"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data
def carregar_dados():
    df = pd.read_csv(URL).dropna(how="all")
    df["Data avaliacao"] = pd.to_datetime(df["Data avaliacao"], format="%d/%m/%Y", errors="coerce")
    df["Area util"] = pd.to_numeric(df["Area util"].astype(str).str.replace(",", "."), errors="coerce")
    df["Massa seca"] = pd.to_numeric(df["Massa seca"].astype(str).str.replace(",", ""), errors="coerce")
    return df

df = carregar_dados()

def fmt_br(valor, decimais=0):
    return f"{valor:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

fazenda_base = st.selectbox("Selecione a Fazenda Alvo:", sorted(df["Fazenda"].unique()))
df_fazenda = df[df["Fazenda"] == fazenda_base]

col_ret, col_mod, col_div = st.columns(3)
retiros = st.multiselect("Retiros", df_fazenda["Retiro"].unique())
modulos = st.multiselect("Módulos", df_fazenda["Modulo"].unique())
divisoes = st.multiselect("Divisões", df_fazenda["Divisao"].unique())

df_filtrado = df_fazenda.copy()
if retiros: df_filtrado = df_filtrado[df_filtrado["Retiro"].isin(retiros)]
if modulos: df_filtrado = df_filtrado[df_filtrado["Modulo"].isin(modulos)]
if divisoes: df_filtrado = df_filtrado[df_filtrado["Divisao"].isin(divisoes)]

# PARÂMETROS
col1, col2, col3, col4 = st.columns(4)
massa_final = col1.number_input("Massa final (kg/ha)", value=3000)
taxa_acumulo = col1.number_input("Taxa acúmulo (kg/ha/dia)", value=40.0)
periodo_dias = col2.number_input("Dias", value=30)
data_inicio = col2.date_input("Início", value=date.today())
cms = col3.number_input("cMS (%PV)", value=2.5, format="%.1f")
ofertado = col3.number_input("Ofertado (n)", value=4.0, format="%.1f")
peso_inicio = col4.number_input("Peso início (kg)", value=450)
gmd = col4.number_input("GMD (kg/dia)", value=0.60)

# CÁLCULOS
area_total = df_filtrado["Area util"].sum()
massa_atual = (df_filtrado["Massa seca"] * df_filtrado["Area util"]).sum() / area_total if area_total > 0 else 0

st.metric("Massa Atual (kg/ha)", fmt_br(massa_atual, 0))

if st.button("➕ Adicionar Bloco"):
    st.session_state["simulacoes_salvas"].append({
        "Fazenda": fazenda_base, "Módulo": "Multi", "Divisões": "Multi", 
        "Área (ha)": area_total, "Data Início": data_inicio.strftime("%d/%m/%Y"), 
        "Data Fim": (data_inicio + timedelta(days=int(periodo_dias))).strftime("%d/%m/%Y"), 
        "Dias": periodo_dias, "UA Total": 0, "Cabeças": 0, "TL (UA/ha)": 0
    })
    st.rerun()

# TABELA E RELATÓRIO
if st.session_state["simulacoes_salvas"]:
    df_temp = pd.DataFrame(st.session_state["simulacoes_salvas"])
    st.dataframe(df_temp)
    
    html_base = f"<html><head><style>@page{{size:landscape;}}</style></head><body><h2>Relatório {fazenda_base}</h2></body></html>"
    c1, c2, c3 = st.columns(3)
    c1.download_button("📄 Relatório", html_base, "relatorio.html", "text/html")
    c2.download_button("📊 Completo", html_base, "completo.html", "text/html")
    if c3.button("🗑️ Limpar"):
        st.session_state["simulacoes_salvas"] = []
        st.rerun()

# MAPA
st.markdown("---")
st.markdown("### 🗺️ Mapa Visual")
caminho_mapa = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mapas", f"{fazenda_base.upper()}.geojson")
if os.path.exists(caminho_mapa):
    m = folium.Map(location=[-10, -50], zoom_start=14)
    with open(caminho_mapa, "r", encoding="utf-8") as f: folium.GeoJson(json.load(f)).add_to(m)
    st_folium(m, width=1300, height=500)
else:
    st.warning("Mapa não encontrado na pasta raiz/mapas")