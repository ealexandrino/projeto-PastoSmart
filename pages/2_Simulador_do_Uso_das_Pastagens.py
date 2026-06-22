import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
import urllib.parse
import json
import os

# Tenta importar folium para o mapa GeoJSON
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_DISPONIVEL = True
except ImportError:
    FOLIUM_DISPONIVEL = False

# =====================================================
# CONFIGURAÇÃO DA PÁGINA
# =====================================================
st.set_page_config(page_title="Planejamento das Pastagens", page_icon="📈", layout="wide")

# =====================================================
# INICIALIZAÇÃO DA MEMÓRIA TEMPORÁRIA
# =====================================================
if "simulacoes_salvas" not in st.session_state: st.session_state["simulacoes_salvas"] = []
if "contador_filtros" not in st.session_state: st.session_state["contador_filtros"] = 0

# =====================================================
# CABEÇALHO
# =====================================================
st.title("📈 Planejamento das Pastagens")
st.subheader("Simulador Métrico Completo - Com WhatsApp, PDF e Satélite")
st.markdown("---")

# =====================================================
# GOOGLE SHEETS (LEITURA DE DADOS)
# =====================================================
SHEET_ID = "1DFy0jTJbv5Mv1n-KtJkTeUuz4uXNjp-khKhPZpQ1m6w"
GID = "853924016"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data
def carregar_dados():
    df = pd.read_csv(URL)
    df = df.dropna(how="all")
    df["Data avaliacao"] = pd.to_datetime(df["Data avaliacao"], format="%d/%m/%Y", errors="coerce")
    df["Area util"] = pd.to_numeric(df["Area util"].astype(str).str.replace(",", "."), errors="coerce")
    df["Massa seca"] = pd.to_numeric(df["Massa seca"].astype(str).str.replace(",", ""), errors="coerce")
    return df

df = carregar_dados()

def fmt_br(valor, decimais=0):
    return format(valor, f",.{decimais}f").replace(",", "X").replace(".", ",").replace("X", ".")

# =====================================================
# 1. SELEÇÃO DA FAZENDA BASE
# =====================================================
st.markdown("### 1. Escolha a Fazenda para Iniciar o Planejamento")
lista_todas_fazendas = sorted(df["Fazenda"].dropna().astype(str).unique())
fazenda_base = st.selectbox("Selecione a Fazenda Alvo:", lista_todas_fazendas, key="fazenda_base_select")

df_fazenda_atual = df[df["Fazenda"].astype(str) == fazenda_base]
todas_divisoes_fazenda = set(df_fazenda_atual["Divisao"].dropna().astype(str).unique())

divisoes_ja_simuladas = set()
for sim in st.session_state["simulacoes_salvas"]:
    if sim["Fazenda"] == fazenda_base:
        divisoes_ja_simuladas.update([d.strip() for d in str(sim["Divisões"]).split(",") if d.strip()])

# =====================================================
# 4. MAPA VISUAL (CORRIGIDO)
# =====================================================
st.markdown("---")
st.markdown("### 🗺️ 4. Mapa Visual em Imagem de Satélite")

# Determina o caminho da pasta mapas independentemente de onde o script estiver
base_dir = os.path.dirname(os.path.abspath(__file__))
if "pages" in base_dir:
    pasta_mapas = os.path.abspath(os.path.join(base_dir, "..", "mapas"))
else:
    pasta_mapas = os.path.join(base_dir, "mapas")

caminho_completo_mapa = os.path.join(pasta_mapas, f"{fazenda_base.upper()}.geojson")

if FOLIUM_DISPONIVEL:
    if os.path.exists(caminho_completo_mapa):
        with open(caminho_completo_mapa, "r", encoding="utf-8") as f:
            dados_geojson = json.load(f)
        
        # Lógica de renderização do mapa
        centro = [-15.0, -50.0] # Padrão centro do Brasil
        m = folium.Map(location=centro, zoom_start=14, tiles=None)
        
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Satélite'
        ).add_to(m)
        
        folium.GeoJson(dados_geojson).add_to(m)
        st_folium(m, width=1300, height=550)
    else:
        st.warning(f"Arquivo {fazenda_base.upper()}.geojson não encontrado em: {pasta_mapas}")