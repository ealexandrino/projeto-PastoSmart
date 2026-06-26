import streamlit as st
import pandas as pd
import plotly.express as px

from conexao_google import carregar_planilha

# =====================================================
# CONFIGURAÇÃO DA PÁGINA
# =====================================================

st.set_page_config(
    page_title="Lifor Analítico - Dados globais",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Lifor Analítico - Dados globais")
st.subheader("Gestão Inteligente em Pastagens")
st.markdown("---")

with st.sidebar:
    st.markdown("### 🌱 Lifor Analítico")
    st.markdown("---")
    st.caption("Versão 1.0")


# =====================================================
# CARREGAMENTO DOS DADOS
# =====================================================

df = carregar_planilha("Dados_limpos")

# remove linhas vazias
df = df.dropna(how="all")

# Data
df["Data avaliacao"] = pd.to_datetime(
    df["Data avaliacao"],
    format="%d/%m/%Y",
    errors="coerce"
)

# Área
for campo in ["Area", "Area util"]:
    if campo in df.columns:
        df[campo] = (
            df[campo]
            .astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
        )
        df[campo] = pd.to_numeric(df[campo], errors="coerce")

# Massa
for campo in ["Massa seca", "Massa total"]:
    if campo in df.columns:
        df[campo] = (
            df[campo]
            .astype(str)
            .str.strip()
            .str.replace(",", "", regex=False)
        )
        df[campo] = pd.to_numeric(df[campo], errors="coerce")

# =====================================================
# FILTROS
# =====================================================

st.subheader("Filtros")

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

with col1:
    fazendas = sorted(df["Fazenda"].dropna().astype(str).unique())
    fazenda = st.selectbox("Fazenda", fazendas)

df_filtrado = df[df["Fazenda"].astype(str) == fazenda]

with col2:
    periodo = st.selectbox("Período", ["Última avaliação", "Todas as avaliações", "Personalizado"])

if df_filtrado.empty:
    data_inicial = pd.Timestamp.now().date()
    data_final = pd.Timestamp.now().date()
    with col3: st.write("Sem dados")
else:
    if periodo == "Última avaliação":
        data_final = df_filtrado["Data avaliacao"].max().date()
        data_inicial = data_final
        with col3: st.write(f"📅 {data_final.strftime('%d/%m/%Y')}")
    elif periodo == "Todas as avaliações":
        data_inicial = df_filtrado["Data avaliacao"].min().date()
        data_final = df_filtrado["Data avaliacao"].max().date()
        with col3: st.write("Todas")
    else:
        with col2: data_inicial = st.date_input("Data Inicial", value=df_filtrado["Data avaliacao"].min().date())
        with col3: data_final = st.date_input("Data Final", value=df_filtrado["Data avaliacao"].max().date())

df_filtrado = df_filtrado[(df_filtrado["Data avaliacao"].dt.date >= data_inicial) & (df_filtrado["Data avaliacao"].dt.date <= data_final)]

with col4:
    retiros = ["Todos"] + sorted(df_filtrado["Retiro"].dropna().astype(str).unique().tolist())
    retiro = st.selectbox("Retiro", retiros)
if retiro != "Todos": df_filtrado = df_filtrado[df_filtrado["Retiro"].astype(str) == retiro]

with col5:
    modulos = ["Todos"] + sorted(df_filtrado["Modulo"].dropna().astype(str).unique().tolist())
    modulo = st.selectbox("Modulo", modulos)
if modulo != "Todos": df_filtrado = df_filtrado[df_filtrado["Modulo"].astype(str) == modulo]

with col6:
    divisoes = ["Todas"] + sorted(df_filtrado["Divisao"].dropna().astype(str).unique().tolist())
    divisao = st.selectbox("Divisão", divisoes)
if divisao != "Todas": df_filtrado = df_filtrado[df_filtrado["Divisao"].astype(str) == divisao]

# ... [O restante do seu código de filtros avançados e gráficos permanece igual] ...
# (Cole aqui o restante do código que você já tinha após os Filtros de Divisão)


# =====================================================
# FILTROS AVANÇADOS
# =====================================================

st.subheader("Filtros Avançados")

f1, f2, f3, f4 = st.columns(4)

with f1:
    manejos = ["Todos"] + sorted(
        df_filtrado["Manejo"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    manejo = st.selectbox(
        "Manejo",
        manejos
    )

if manejo != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Manejo"].astype(str) == manejo]

with f2:
    forrageiras = ["Todos"] + sorted(
        df_filtrado["Forrageira"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    forrageira = st.selectbox(
        "Forrageira",
        forrageiras
    )

if forrageira != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Forrageira"].astype(str) == forrageira]

with f3:
    cores = ["Todos"] + sorted(
        df_filtrado["Cor folha"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    cor = st.selectbox(
        "Cor folha",
        cores
    )

if cor != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Cor folha"].astype(str) == cor]

with f4:
    recomendacoes = ["Todos"] + sorted(
        df_filtrado["Recomendacao pastejo"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    recomendacao = st.selectbox(
        "Recomendação pastejo",
        recomendacoes
    )

if recomendacao != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Recomendacao pastejo"].astype(str) == recomendacao]


# =====================================================
# INDICADORES
# =====================================================

st.subheader("Indicadores")

area_total = df_filtrado["Area"].sum()
area_util = df_filtrado["Area util"].sum()
divisoes_unicas = df_filtrado["Divisao"].nunique()

# Proteção para média de dataframe vazio
if not df_filtrado.empty and df_filtrado["Massa seca"].notna().any():
    massa_media = df_filtrado["Massa seca"].mean()
else:
    massa_media = 0

c1, c2, c3, c4 = st.columns(4)

c1.metric("Área (ha)", f"{area_total:,.2f}")
c2.metric("Área útil (ha)", f"{area_util:,.2f}")
c3.metric("Divisões", divisoes_unicas)
c4.metric("Massa média (kg MS/ha)", f"{massa_media:,.0f}")


# =====================================================
# GRÁFICO MASSA POR DIVISÃO
# =====================================================

st.subheader("Massa seca por divisão")

if not df_filtrado.empty:
    grafico_divisao = (
        df_filtrado
        .groupby("Divisao", as_index=False)
        ["Massa seca"]
        .mean()
    )

    grafico_divisao = grafico_divisao.sort_values(
        "Massa seca",
        ascending=False
    )

    ordem_divisoes = grafico_divisao["Divisao"].astype(str).tolist()

    # Classificação das divisões
    grafico_divisao["Faixa"] = "Ideal"
    grafico_divisao.loc[grafico_divisao["Massa seca"] < 2000, "Faixa"] = "Baixa"
    grafico_divisao.loc[grafico_divisao["Massa seca"] > 6000, "Faixa"] = "Excesso"

    fig = px.bar(
        grafico_divisao,
        x="Divisao",
        y="Massa seca",
        color="Faixa",
        category_orders={
            "Divisao": ordem_divisoes,
            "Faixa": ["Baixa", "Ideal", "Excesso"]
        },
        color_discrete_map={
            "Baixa": "red",
            "Ideal": "green",
            "Excesso": "gold"
        }
    )

    fig.update_layout(
        xaxis_title="Divisão",
        yaxis_title="Massa seca (kg MS/ha)",
        height=500
    )

    fig.update_traces(
        texttemplate='%{y:.0f}',
        textposition='outside'
    )

    # Linha mínima desejada
    fig.add_hline(
        y=2000,
        line_dash="dash",
        annotation_text="Mínimo (2000)"
    )

    # Linha máxima desejada
    fig.add_hline(
        y=6000,
        line_dash="dash",
        annotation_text="Máximo (6000)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
else:
    st.warning("Nenhum dado disponível para gerar o gráfico com os filtros selecionados.")


# =====================================================
# HISTÓRICO DE AVALIAÇÕES
# =====================================================

st.markdown("### 📋 Histórico de Avaliações")

if not df_filtrado.empty:
    colunas_validas = [
        "Data avaliacao", "Retiro", "Modulo", 
        "Divisao", "Forrageira", "Massa seca", "Recomendacao pastejo"
    ]
    
    # Garante que as colunas existem antes de filtrar para a tabela
    colunas_existentes = [col for col in colunas_validas if col in df_filtrado.columns]
    
    tabela = df_filtrado[colunas_existentes].copy()

    if "Data avaliacao" in tabela.columns:
        tabela["Data avaliacao"] = pd.to_datetime(
            tabela["Data avaliacao"]
        ).dt.strftime("%d/%m/%Y")

    st.dataframe(
        tabela,
        column_config={
            "Data avaliacao": "Data",
            "Retiro": "Retiro",
            "Modulo": "Módulo",
            "Divisao": "Divisão",
            "Forrageira": "Forrageira",
            "Massa seca": st.column_config.NumberColumn(
                "Massa Seca (kg MS/ha)",
                format="%.0f"
            ),
            "Recomendacao pastejo": "Recomendação"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Nenhum histórico encontrado para os filtros selecionados.")


# =====================================================
# EVOLUÇÃO TEMPORAL
# =====================================================

st.subheader("Evolução da massa seca")

if not df_filtrado.empty:
    if divisao == "Todas":
        grafico_tempo = (
            df_filtrado
            .groupby(
                ["Data avaliacao", "Divisao"],
                as_index=False
            )["Massa seca"]
            .mean()
        )

        fig_tempo = px.line(
            grafico_tempo,
            x="Data avaliacao",
            y="Massa seca",
            color="Divisao",
            markers=True
        )
    else:
        grafico_tempo = (
            df_filtrado
            .groupby(
                "Data avaliacao",
                as_index=False
            )["Massa seca"]
            .mean()
        )

        fig_tempo = px.line(
            grafico_tempo,
            x="Data avaliacao",
            y="Massa seca",
            markers=True
        )

    fig_tempo.update_layout(
        xaxis_title="Data",
        yaxis_title="Massa seca (kg MS/ha)",
        height=500
    )

    st.plotly_chart(
        fig_tempo,
        use_container_width=True
    )
else:
    st.info("Dados insuficientes para gerar a evolução temporal.")
