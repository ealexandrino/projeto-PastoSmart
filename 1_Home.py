import streamlit as st

# =====================================================
# CONFIGURAÇÃO
# =====================================================

st.set_page_config(
    page_title="Lifor",
    page_icon="🌱",
    layout="wide"
)

# =====================================================
# CABEÇALHO
# =====================================================

st.title("🌱 Lifor")
st.subheader("Plataforma de Gestão e Inteligência em Pastagens")

st.markdown("---")

# =====================================================
# APRESENTAÇÃO
# =====================================================

st.markdown("""
### Bem-vindo

A Lifor integra informações de campo, indicadores produtivos,
mapas georreferenciados e simuladores de uso das pastagens,
auxiliando produtores, técnicos e pesquisadores na tomada de decisão.

Utilize o menu lateral para acessar os módulos disponíveis.
""")

# =====================================================
# MÓDULOS
# =====================================================

st.markdown("### Módulos disponíveis")

c1, c2, c3 = st.columns(3)

with c1:

    st.info("""
🗺️ **Mapa das Pastagens**

Visualização georreferenciada de fazendas, retiros, módulos e divisões.
""")

with c2:

    st.info("""
📈 **Simulador do Uso das Pastagens**

Simulação da capacidade de suporte, lotação e cenários de manejo.
""")

with c3:

    st.info("""
📊 **Lifor Analítico**

Indicadores produtivos, análises históricas e acompanhamento das avaliações.
""")

# =====================================================
# FUTURAS FUNCIONALIDADES
# =====================================================

st.markdown("---")

st.markdown("### Próximas funcionalidades")

c4, c5, c6 = st.columns(3)

with c4:

    st.success("""
📷 Análise de Imagens

Monitoramento de pastagens por imagens de campo, drones e satélites.
""")

with c5:

    st.success("""
🤖 Inteligência Artificial

Modelos preditivos para suporte à tomada de decisão.
""")

with c6:

    st.success("""
🐂 Gestão do Rebanho

Integração entre animais, pastagens e desempenho produtivo.
""")

# =====================================================
# CRÉDITOS
# =====================================================

st.markdown("---")

st.markdown("""
### Desenvolvimento e Coordenação Científica

**Professor Titular Dr. Emerson Alexandrino**  
Universidade Federal do Norte do Tocantins (UFNT)

### Apoio

**Nepral**  
Núcleo de Ensino, Pesquisa e Extensão em Ruminantes da Amazônia Legal

**PastoSmart**  
Inovação Tecnológica para Gestão Inteligente de Pastagens
""")

# =====================================================
# RODAPÉ
# =====================================================

st.markdown("---")

st.caption(
    "Lifor • Plataforma de Gestão e Inteligência em Pastagens • Versão 1.0"
)