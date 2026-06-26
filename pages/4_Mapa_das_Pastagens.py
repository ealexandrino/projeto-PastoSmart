import streamlit as st
import folium
import json
import pandas as pd
from pathlib import Path
from streamlit_folium import st_folium

# =====================================================
# CONFIGURAÇÃO
# =====================================================
st.set_page_config(
    page_title="Mapa",
    layout="wide"
)

st.title("🗺️ Mapa dos Piquetes")

# =====================================================
# GOOGLE SHEETS
# =====================================================
SHEET_ID = "1DFy0jTJbv5Mv1n-KtJkTeUuz4uXNjp-khKhPZpQ1m6w"
GID = "1975526854"

URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =====================================================
# CARREGA CADASTRO
# =====================================================
@st.cache_data
def carregar_pastagens():
    df = pd.read_csv(URL)
    df["Divisao"] = df["Divisao"].astype(str).str.strip()
    return df

cadastro = carregar_pastagens()

# =====================================================
# FILTROS
# =====================================================
f1, f2, f3, f4, f5 = st.columns(5)

# =====================================================
# GRUPO
# =====================================================
with f1:
    grupos = sorted(cadastro["Grupo"].dropna().astype(str).unique().tolist())
    grupo_sel = st.selectbox("Grupo", grupos)

# =====================================================
# FAZENDA
# =====================================================
with f2:
    fazendas = sorted(
        cadastro[cadastro["Grupo"].astype(str) == grupo_sel]["Fazenda"]
        .dropna().astype(str).unique().tolist()
    )
    fazenda_sel = st.selectbox("Fazenda", fazendas)

# =====================================================
# RETIRO
# =====================================================
with f3:
    retiros = sorted(
        cadastro[
            (cadastro["Grupo"].astype(str) == grupo_sel) &
            (cadastro["Fazenda"].astype(str) == fazenda_sel)
        ]["Retiro"].dropna().astype(str).unique().tolist()
    )
    retiro_sel = st.selectbox("Retiro", retiros)

# =====================================================
# BASE FILTRADA
# =====================================================
cadastro_filtro = cadastro.copy()
cadastro_filtro = cadastro_filtro[cadastro_filtro["Grupo"].astype(str) == grupo_sel]
cadastro_filtro = cadastro_filtro[cadastro_filtro["Fazenda"].astype(str) == fazenda_sel]
cadastro_filtro = cadastro_filtro[cadastro_filtro["Retiro"].astype(str) == retiro_sel]

cadastro_filtro["Modulo"] = (
    cadastro_filtro["Modulo"]
    .astype(str)
    .str.replace(",", ".", regex=False)
)
cadastro_filtro["Modulo"] = pd.to_numeric(cadastro_filtro["Modulo"], errors="coerce")
cadastro_filtro["Modulo"] = cadastro_filtro["Modulo"].astype("Int64")

# =====================================================
# FILTRO MÓDULO
# =====================================================
with f4:
    modulos = ["Todos"] + sorted(cadastro_filtro["Modulo"].dropna().unique().tolist())
    modulo_sel = st.selectbox("Módulo", modulos)

# =====================================================
# FILTRO DIVISÃO
# =====================================================
if modulo_sel == "Todos":
    cadastro_div = cadastro_filtro.copy()
else:
    cadastro_div = cadastro_filtro[cadastro_filtro["Modulo"] == modulo_sel]

with f5:
    divisoes = ["Todas"] + sorted(cadastro_div["Divisao"].dropna().astype(str).unique().tolist())
    divisao_sel = st.selectbox("Divisão", divisoes)

# =====================================================
# MAPA BASE
# =====================================================
tipo_mapa = st.selectbox(
    "Mapa base",
    ["Satélite", "Híbrido", "OpenStreetMap"]
)

# =====================================================
# CARREGA GEOJSON
# =====================================================
if not cadastro_filtro.empty and "Arquivo" in cadastro_filtro.columns:
    arquivo_mapa = cadastro_filtro["Arquivo"].dropna().iloc[0]
    arquivo_geojson = Path("mapas") / arquivo_mapa

    try:
        with open(arquivo_geojson, "r", encoding="utf-8") as f:
            geojson = json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo GeoJSON ({arquivo_mapa}): {e}")
        st.stop()
else:
    st.warning("Nenhum arquivo de mapa associado a estes filtros.")
    st.stop()

# =====================================================
# LIMITES DO GEOJSON
# =====================================================
coords = []
for feature in geojson["features"]:
    if feature["geometry"]["type"] != "Polygon":
        continue
    # Pega as coordenadas do anel externo do polígono
    for ponto in feature["geometry"]["coordinates"][0]:
        lon, lat = ponto[0], ponto[1]
        coords.append([lat, lon])

if not coords:
    st.error("Nenhuma coordenada válida encontrada no GeoJSON.")
    st.stop()

# =====================================================
# CONSTRUÇÃO DO MAPA FOLIUM
# =====================================================
m = folium.Map(tiles=None)

if tipo_mapa == "Satélite":
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google",
        name="Satélite"
    ).add_to(m)
elif tipo_mapa == "Híbrido":
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google",
        name="Híbrido"
    ).add_to(m)
else:
    folium.TileLayer("OpenStreetMap").add_to(m)

# =====================================================
# INTERAÇÃO E PLOTAGEM DOS POLÍGONOS (CORRIGIDO)
# =====================================================
for feature in geojson["features"]:
    if feature["geometry"]["type"] != "Polygon":
        continue

    divisao = str(feature["properties"]["name"]).strip()

    # Filtra dados para esta divisão específica do mapa
    dados = cadastro_filtro[cadastro_filtro["Divisao"].astype(str).str.strip() == divisao]

    modulo_piquete = None
    divisao_piquete = None

    if not dados.empty:
        linha = dados.iloc[0]
        try:
            modulo_piquete = int(float(linha["Modulo"]))
        except:
            modulo_piquete = None
        
        divisao_piquete = str(linha["Divisao"])

        # Tratamento seguro de nomes de colunas
        a_util_val = linha.get("Area util ha", linha.get("Area util", "-"))
        tl_est_val = linha.get("Suporte estimado UA/ha", "-")

        popup_texto = f"""
        <b><font size='4'>📍 {linha['Divisao']}</font></b><br><br>
        <b>Fazenda:</b> {linha['Fazenda']}<br>
        <b>Retiro:</b> {linha['Retiro']}<br>
        <b>Módulo:</b> {linha['Modulo']}<br>
        <b>Situação:</b> {linha.get('Situacao', '-')}<br>
        <b>Forrageira:</b> {linha['Forrageira']}<br>
        <b>A útil:</b> {a_util_val} ha<br>
        <b>TL est:</b> {tl_est_val} UA/ha
        """
    else:
        popup_texto = f"<b>{divisao}</b><br>Sem cadastro encontrado"

    # =================================================
    # ESTILIZAÇÃO DINÂMICA POR PIQUETE
    # =================================================
    cor = "#00cc44"
    borda = "#006600"
    peso = 3
    opacidade = 0.60

    # Condição de destaque do filtro de Divisão
    if divisao_sel != "Todas":
        if divisao_piquete == divisao_sel:
            cor = "#00cc44"
            borda = "#006600"
            peso = 6
            opacidade = 0.95
        else:
            cor = "#FFFFFF"
            borda = "#999999"
            peso = 1
            opacidade = 0.15

    # Condição de destaque do filtro de Módulo
    elif modulo_sel != "Todos":
        if modulo_piquete is not None and modulo_piquete == int(modulo_sel):
            cor = "#00FFFF"
            borda = "#0000FF"
            peso = 6
            opacidade = 0.90
        else:
            cor = "#FFFFFF"
            borda = "#999999"
            peso = 1
            opacidade = 0.15

    # Adiciona a geometria ao mapa dentro do laço de repetição correto
    folium.GeoJson(
        feature,
        tooltip=divisao,
        popup=folium.Popup(popup_texto, max_width=350),
        style_function=lambda x, cor=cor, borda=borda, peso=peso, opacidade=opacidade: {
            "fillColor": cor,
            "color": borda,
            "weight": peso,
            "fillOpacity": opacidade
        }
    ).add_to(m)

# =====================================================
# ENQUADRAMENTO E EXIBIÇÃO DO MAPA
# =====================================================
m.fit_bounds(coords)
st_folium(
    m,
    use_container_width=True,
    height=750
)
