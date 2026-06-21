import streamlit as st
import pandas as pd

# =====================================================
# CONFIGURAÇÃO DA PÁGINA (Sempre no topo)
# =====================================================
st.set_page_config(
    page_title="Lifor - Planejamento das Pastagens",
    page_icon="🌱",
    layout="wide"
)

# =====================================================
# CABEÇALHO
# =====================================================
st.title("📈 Planejamento das Pastagens")
st.subheader("Ajuste de carga dinâmico")
st.markdown("---")

# =====================================================
# GOOGLE SHEETS
# =====================================================
SHEET_ID = "1DFy0jTJbv5Mv1n-KtJkTeUuz4uXNjp-khKhPZpQ1m6w"
GID = "853924016"

URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =====================================================
# CARREGAMENTO
# =====================================================
@st.cache_data
def carregar_dados():
    df = pd.read_csv(URL)
    df = df.dropna(how="all")
    
    df["Data avaliacao"] = pd.to_datetime(
        df["Data avaliacao"],
        format="%d/%m/%Y",
        errors="coerce"
    )
    
    # Garantir conversão correta de formatos numéricos antes dos cálculos
    for campo in ["Area", "Area util", "Massa seca"]:
        if campo in df.columns:
            df[campo] = (
                df[campo]
                .astype(str)
                .str.strip()
                .str.replace(",", ".", regex=False)
            )
            df[campo] = pd.to_numeric(df[campo], errors="coerce")
            
    return df

df = carregar_dados()

# =====================================================
# FILTROS
# =====================================================
st.subheader("Filtros")

# CORRIGIDO: alterado co17 para col7
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

with col1:
    fazendas = sorted(df["Fazenda"].dropna().astype(str).unique())
    fazenda = st.selectbox("Fazenda", fazendas)

df_filtrado = df[df["Fazenda"].astype(str) == fazenda]

with col2:
    periodo = st.selectbox(
        "Período",
        ["Última avaliação", "Todas as avaliações", "Personalizado"]
    )

# Segurança para o caso de df_filtrado estar vazio
if df_filtrado.empty:
    data_inicial = pd.Timestamp.now().date()
    data_final = pd.Timestamp.now().date()
    with col3:
        st.write("Sem dados")
else:
    if periodo == "Última avaliação":
        data_final = df_filtrado["Data avaliacao"].max().date()
        data_inicial = data_final
        with col3:
            st.write(f"📅 {data_final.strftime('%d/%m/%Y')}")

    elif periodo == "Todas as avaliações":
        data_inicial = df_filtrado["Data avaliacao"].min().date()
        data_final = df_filtrado["Data avaliacao"].max().date()
        with col3:
            st.write("Todas")

    else:
        with col2:
            data_inicial = st.date_input(
                "Data Inicial",
                value=df_filtrado["Data avaliacao"].min().date()
            )
        with col3:
            data_final = st.date_input(
                "Data Final",
                value=df_filtrado["Data avaliacao"].max().date()
            )

df_filtrado = df_filtrado[
    (df_filtrado["Data avaliacao"].dt.date >= data_inicial) &
    (df_filtrado["Data avaliacao"].dt.date <= data_final)
]

with col4:
    retiros = ["Todos"] + sorted(df_filtrado["Retiro"].dropna().astype(str).unique().tolist())
    retiro = st.selectbox("Retiro", retiros)

if retiro != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Retiro"].astype(str) == retiro]

with col5:
    modulos = ["Todos"] + sorted(df_filtrado["Modulo"].dropna().astype(str).unique().tolist())
    modulo = st.selectbox("Modulo", modulos)

if modulo != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Modulo"].astype(str) == modulo]

with col6:
    divisoes = ["Todas"] + sorted(df_filtrado["Divisao"].dropna().astype(str).unique().tolist())
    divisao = st.selectbox("Divisão", divisoes)

if divisao != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Divisao"].astype(str) == divisao]


# =====================================================
# AVALIAÇÕES
# =====================================================
df_sim = df_filtrado.copy()

if not df_sim.empty:
    # Última avaliação de cada divisão
    ultima_avaliacao = (
        df_sim
        .sort_values("Data avaliacao")
        .groupby("Divisao", as_index=False)
        .tail(1)
    )

    # Massa global por divisão
    ultima_avaliacao["Massa global"] = (
        ultima_avaliacao["Area util"] * ultima_avaliacao["Massa seca"]
    )
else:
    ultima_avaliacao = pd.DataFrame(columns=["Divisao", "Data avaliacao", "Area util", "Massa seca", "Massa global"])

# =====================================================
# AVALIAÇÕES UTILIZADAS
# =====================================================
st.markdown("---")
st.markdown("### 📋 Avaliações Utilizadas")

if not ultima_avaliacao.empty:
    tabela_avaliacoes = (
        ultima_avaliacao[
            [
                "Divisao",
                "Data avaliacao",
                "Area util",
                "Massa seca",
                "Massa global"
            ]
        ]
        .sort_values("Divisao")
    )
    
    # Formatação visual da data na tabela
    tabela_avaliacoes["Data avaliacao"] = tabela_avaliacoes["Data avaliacao"].dt.strftime("%d/%m/%Y")

    st.dataframe(
        tabela_avaliacoes,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Nenhuma avaliação encontrada para os filtros aplicados.")

# =====================================================
# INDICADORES AUTOMÁTICOS
# =====================================================
if not ultima_avaliacao.empty:
    area_util = ultima_avaliacao["Area util"].sum()
    massa_global = ultima_avaliacao["Massa global"].sum()
    massa_inicial = (massa_global / area_util) if area_util > 0 else 0
else:
    area_util = 0
    massa_global = 0
    massa_inicial = 0

i1, i2, i3 = st.columns(3)

i1.metric("Massa inicial (kg MS/ha)", f"{massa_inicial:,.0f}")
i2.metric("Área útil total (ha)", f"{area_util:,.2f}")
i3.metric("Massa global (kg MS)", f"{massa_global:,.0f}")

# =====================================================
# PARÂMETROS
# =====================================================
st.markdown("---")
st.markdown("### ⚙️ Parâmetros da Simulação")

p1, p2, p3 = st.columns(3)

with p1:
    taxa_acumulo = st.number_input(
        "Taxa de acúmulo (kg MS/ha/dia)",
        value=40.0,
        step=1.0
    )
    periodo_dias = st.number_input(
        "Período (dias)",
        value=30,
        step=1
    )

with p2:
    massa_final_desejada = st.number_input(
        "Massa final desejada (kg MS/ha)",
        value=3000,
        step=100
    )
    cms = st.number_input(
        "cMS (%PV)",
        value=2.5,
        step=0.1
    )

with p3:
    ofertado = st.number_input(
        "Ofertado",
        value=4.0,
        step=0.1
    )
    peso_medio = st.number_input(
        "Peso médio do lote (kg)",
        value=450,
        step=10
    )

# =====================================================
# RESULTADOS
# =====================================================
st.markdown("---")
st.markdown("### 📊 Resultados")

r1, r2, r3, r4 = st.columns(4)

# Campos preparados para receberem as variáveis calculadas futuramente
r1.metric("TL (UA/ha)", "-")
r2.metric("TL (cab/ha)", "-")
r3.metric("UA Total", "-")
r4.metric("Cabeças", "-")

# =====================================================
# GRÁFICO
# =====================================================
st.markdown("---")
st.markdown("### 📈 Evolução da Massa de Forragem")

st.info(
    "O gráfico será exibido após a implementação dos cálculos matemáticos."
)