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
st.set_page_config(
    page_title="Planejamento das Pastagens",
    page_icon="📈",
    layout="wide"
)

# =====================================================
# INICIALIZAÇÃO DA MEMÓRIA TEMPORÁRIA
# =====================================================
if "simulacoes_salvas" not in st.session_state:
    st.session_state["simulacoes_salvas"] = []

if "contador_filtros" not in st.session_state:
    st.session_state["contador_filtros"] = 0

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
    df["Area util"] = df["Area util"].astype(str).str.strip().str.replace(",", ".", regex=False)
    df["Area util"] = pd.to_numeric(df["Area util"], errors="coerce")
    df["Massa seca"] = df["Massa seca"].astype(str).str.strip().str.replace(",", "", regex=False)
    df["Massa seca"] = pd.to_numeric(df["Massa seca"], errors="coerce")
    return df

df = carregar_dados()

def fmt_br(valor, decimais=0):
    formato = f",.{decimais}f"
    texto = format(valor, formato)
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")

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
        partes = [d.strip() for d in str(sim["Divisões"]).split(",") if d.strip()]
        divisoes_ja_simuladas.update(partes)

# =====================================================
# 2. FILTROS DA SIMULAÇÃO
# =====================================================
st.markdown("---")
st.markdown("### ⚙️ 2. Filtrar Módulos / Divisões")

# Cálculo de progresso
divisoes_restantes = todas_divisoes_fazenda - divisoes_ja_simuladas
col_txt, col_prog = st.columns([1, 3])
with col_txt:
    st.markdown(f"**Progresso da Fazenda:**")
    st.markdown(f"🗓️ Restam **{len(divisoes_restantes)}** de **{len(todas_divisoes_fazenda)}** divisões.")
with col_prog:
    progresso = (len(divisoes_ja_simuladas) / len(todas_divisoes_fazenda)) if todas_divisoes_fazenda else 0.0
    st.progress(progresso)

col_ret, col_mod, col_div, col_per = st.columns(4)
sufixo_reset = f"_{st.session_state['contador_filtros']}"

with col_ret:
    lista_retiros = sorted(df_fazenda_atual["Retiro"].dropna().astype(str).unique().tolist())
    retiros_selecionados = st.multiselect("Retiros", options=lista_retiros, key=f"ret{sufixo_reset}")
    df_f2 = df_fazenda_atual[df_fazenda_atual["Retiro"].astype(str).isin(retiros_selecionados)] if retiros_selecionados else df_fazenda_atual.copy()

with col_mod:
    lista_modulos = sorted(df_f2["Modulo"].dropna().astype(str).unique().tolist())
    modulos_selecionados = st.multiselect("Módulos", options=lista_modulos, key=f"mod{sufixo_reset}")
    df_f3 = df_f2[df_f2["Modulo"].astype(str).isin(modulos_selecionados)] if modulos_selecionados else df_f2.copy()

# Controle de duplicação
ja_contem_duplicada = False
divisoes_conflitantes = []

with col_div:
    lista_divisoes = sorted(df_f3["Divisao"].dropna().astype(str).unique().tolist())
    divisoes_selecionadas = st.multiselect("Divisões específicas", options=lista_divisoes, key=f"div{sufixo_reset}")
    
    divisoes_analisadas = divisoes_selecionadas if divisoes_selecionadas else lista_divisoes
    for d in divisoes_analisadas:
        if d in divisoes_ja_simuladas:
            ja_contem_duplicada = True
            divisoes_conflitantes.append(d)
    
    df_filtrado = df_f3[df_f3["Divisao"].astype(str).isin(divisoes_selecionadas)] if divisoes_selecionadas else df_f3.copy()

with col_per:
    periodo_opcao = st.selectbox("Período das Avaliações", ["Última avaliação", "Todas as avaliações"], key=f"per{sufixo_reset}")

if ja_contem_duplicada:
    st.error(f"⚠️ Atenção! O bloco contém divisões já simuladas: **{', '.join(divisoes_conflitantes)}**.")

if periodo_opcao == "Última avaliação" and not df_filtrado.empty:
    df_filtrado = df_filtrado.sort_values("Data avaliacao").groupby("Divisao", as_index=False).tail(1)

# =====================================================
# 3. PARÂMETROS E CÁLCULOS
# =====================================================
st.markdown("---")
st.markdown("### 3. Ajustar Parâmetros do Lote")
p1, p2, p3, p4 = st.columns(4)

with p1:
    massa_final = st.number_input("Massa final (kg/ha)", value=3000, key="mf_aj")
    taxa_acumulo = st.number_input("Taxa de acúmulo (kg/ha/dia)", value=40.0, key="ta_aj")
with p2:
    periodo_dias = st.number_input("Dias", value=30, key="pd_aj")
    data_inicio_sim = st.date_input("Data Início", value=date.today(), key="dt_ini_aj")
    data_fim_calc = data_inicio_sim + timedelta(days=int(periodo_dias))
with p3:
    cms = st.number_input("cMS (%PV)", value=2.5, format="%.1f", key="cms_aj")
    ofertado = st.number_input("Ofertado (n)", value=4.0, format="%.1f", key="of_aj")
    oferta = cms * ofertado
with p4:
    peso_inicio = st.number_input("Peso início (kg)", value=450, key="pi_aj")
    gmd = st.number_input("GMD (kg/dia)", value=0.60, format="%.2f", key="gmd_aj")
    peso_medio = peso_inicio + (gmd * periodo_dias / 2)

# CÁLCULOS DO BLOCO
total_area_bloco, total_ua_bloco, total_cabecas_bloco, massa_vezes_area = 0.0, 0.0, 0.0, 0.0

if not df_filtrado.empty:
    for idx, row in df_filtrado.iterrows():
        d_area = float(row["Area util"]) if pd.notnull(row["Area util"]) else 0.0
        d_massa_ini = float(row["Massa seca"]) if pd.notnull(row["Massa seca"]) else 0.0
        if d_area > 0:
            producao_por_ha = taxa_acumulo * periodo_dias
            massa_teto = d_massa_ini + producao_por_ha
            perfil_pastejo = max(0.0, massa_teto - massa_final)
            desaparecimento_periodo_ua = (450 * (oferta / 100)) * periodo_dias
            d_ua_total = (perfil_pastejo / desaparecimento_periodo_ua * d_area) if desaparecimento_periodo_ua > 0 else 0.0
            total_area_bloco += d_area
            total_ua_bloco += d_ua_total
            total_cabecas_bloco += (d_ua_total / (peso_medio / 450)) if peso_medio > 0 else 0.0
            massa_vezes_area += (d_massa_ini * d_area)

# EXIBIÇÃO DE INDICADORES
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("Área Total", f"{fmt_br(total_area_bloco, 2)} ha")
with m2: st.metric("Capacidade (UA)", f"{fmt_br(total_ua_bloco, 1)} UA")
with m3: st.metric("Total Cabeças", f"{fmt_br(total_cabecas_bloco, 0)} cab")
with m4: st.metric("Produtividade", f"{fmt_br(total_cabecas_bloco * gmd * periodo_dias / total_area_bloco if total_area_bloco > 0 else 0, 1)} kg/ha")

# BOTÃO ADICIONAR
if st.button("➕ Adicionar Bloco", disabled=ja_contem_duplicada, use_container_width=True):
    novo_bloco = {"Fazenda": fazenda_base, "Divisões": ", ".join(df_filtrado["Divisao"].astype(str).unique()), "Área (ha)": total_area_bloco, "UA Total": total_ua_bloco, "Cabeças": total_cabecas_bloco}
    st.session_state["simulacoes_salvas"].append(novo_bloco)
    st.session_state["contador_filtros"] += 1
    st.rerun()

# TABELA E MAPA
if st.session_state["simulacoes_salvas"]:
    st.dataframe(pd.DataFrame(st.session_state["simulacoes_salvas"]))

st.markdown("---")
st.markdown("### 🗺️ 4. Mapa Visual")
pasta_mapas = os.path.join(os.path.dirname(__file__), "mapas")
caminho_mapa = os.path.join(pasta_mapas, f"{fazenda_base.upper()}.geojson")

if FOLIUM_DISPONIVEL and os.path.exists(caminho_mapa):
    with open(caminho_mapa, "r", encoding="utf-8") as f:
        dados_geojson = json.load(f)
    m = folium.Map(location=[-10, -50], zoom_start=14)
    folium.GeoJson(dados_geojson).add_to(m)
    st_folium(m, width=1300, height=500)
else:
    st.warning("Mapa não encontrado na pasta raiz/mapas")