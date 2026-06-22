import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
import urllib.parse
import json
import os

# Tenta importar folium
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_DISPONIVEL = True
except ImportError:
    FOLIUM_DISPONIVEL = False

# Configuração da página
st.set_page_config(page_title="Planejamento das Pastagens", page_icon="📈", layout="wide")

# Inicialização da sessão
if "simulacoes_salvas" not in st.session_state: st.session_state["simulacoes_salvas"] = []
if "contador_filtros" not in st.session_state: st.session_state["contador_filtros"] = 0

st.title("📈 Planejamento das Pastagens")
st.subheader("Simulador Métrico Completo")
st.markdown("---")

# Dados
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

# --- SEÇÃO 1, 2 e 3 (Mantidas do seu código original) ---
# [Aqui entraria todo o seu código de filtros, cálculos e botões que você já tem]
# Para não ficar longo demais, vou focar na integração da Seção 4 logo abaixo:

# =====================================================
# 4. MAPA VISUAL (INTEGRAÇÃO CORRIGIDA)
# =====================================================
st.markdown("---")
st.markdown("### 🗺️ 4. Mapa Visual em Imagem de Satélite")

# Lógica de caminho robusta
base_dir = os.path.dirname(os.path.abspath(__file__))
if "pages" in base_dir:
    pasta_mapas = os.path.abspath(os.path.join(base_dir, "..", "mapas"))
else:
    pasta_mapas = os.path.join(base_dir, "mapas")

caminho_completo_mapa = os.path.join(pasta_mapas, f"{fazenda_base.upper()}.geojson")

if FOLIUM_DISPONIVEL:
    if os.path.exists(caminho_completo_mapa):
        try:
            with open(caminho_completo_mapa, "r", encoding="utf-8") as f:
                dados_geojson = json.load(f)
            
            # Centro do mapa
            centro = [-15.0, -50.0] 
            m = folium.Map(location=centro, zoom_start=14, tiles=None)
            
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Satélite'
            ).add_to(m)
            
            # Adiciona os polígonos
            folium.GeoJson(dados_geojson).add_to(m)
            
            # Exibe no Streamlit
            st_folium(m, width=1300, height=550)
        except Exception as e:
            st.error(f"Erro ao carregar mapa: {e}")
    else:
        st.warning(f"Arquivo {fazenda_base.upper()}.geojson não encontrado na pasta: {pasta_mapas}")
else:
    st.error("Biblioteca folium não instalada.")