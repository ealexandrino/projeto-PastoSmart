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

divisoes_restantes = todas_divisoes_fazenda - divisoes_ja_simuladas

# =====================================================
# 2. FILTROS DA SIMULAÇÃO COM CONTROLE DE PROGRESSO
# =====================================================
st.markdown("---")
st.markdown("### ⚙️ 2. Filtrar Módulos / Divisões")

col_txt, col_prog = st.columns([1, 3])
with col_txt:
    st.markdown(f"**Progresso da Fazenda:**")
    st.markdown(f"🗓️ Restam **{len(divisoes_restantes)}** de **{len(todas_divisoes_fazenda)}** divisões.")
with col_prog:
    progresso = (len(divisoes_ja_simuladas) / len(todas_divisoes_fazenda)) if todas_divisoes_fazenda else 0.0
    st.progress(progresso)

st.write("")
col_ret, col_mod, col_div, col_per = st.columns(4)
sufixo_reset = f"_{st.session_state['contador_filtros']}"

with col_ret:
    lista_retiros = sorted(df_fazenda_atual["Retiro"].dropna().astype(str).unique().tolist())
    retiros_selecionados = st.multiselect("Retiros", options=lista_retiros, placeholder="Todos", key=f"ret{sufixo_reset}")
    df_f2 = df_fazenda_atual[df_fazenda_atual["Retiro"].astype(str).isin(retiros_selecionados)] if retiros_selecionados else df_fazenda_atual.copy()

with col_mod:
    lista_modulos = sorted(df_f2["Modulo"].dropna().astype(str).unique().tolist())
    modulos_selecionados = st.multiselect("Módulos", options=lista_modulos, placeholder="Todos", key=f"mod{sufixo_reset}")
    df_f3 = df_f2[df_f2["Modulo"].astype(str).isin(modulos_selecionados)] if modulos_selecionados else df_f2.copy()

ja_contem_duplicada = False
divisoes_conflitantes = []

with col_div:
    lista_divisoes = sorted(df_f3["Divisao"].dropna().astype(str).unique().tolist())
    divisoes_selecionadas = st.multiselect("Divisões específicas", options=lista_divisoes, placeholder="Todas do bloco", key=f"div{sufixo_reset}")
    
    divisoes_analisadas = divisoes_selecionadas if divisoes_selecionadas else lista_divisoes
    for d in divisoes_analisadas:
        if d in divisoes_ja_simuladas:
            ja_contem_duplicada = True
            divisoes_conflitantes.append(d)
            
    df_filtrado = df_f3[df_f3["Divisao"].astype(str).isin(divisoes_selecionadas)] if divisoes_selecionadas else df_f3.copy()

with col_per:
    periodo_opcao = st.selectbox("Período das Avaliações", ["Última avaliação", "Todas as avaliações"], key=f"per{sufixo_reset}")

if ja_contem_duplicada:
    st.error(f"⚠️ Atenção! O bloco selecionado contém divisões que já foram incluídas anteriormente: **{', '.join(divisoes_conflitantes)}**.")

if periodo_opcao == "Última avaliação" and not df_filtrado.empty:
    df_filtrado = df_filtrado.sort_values("Data avaliacao").groupby("Divisao", as_index=False).tail(1)

# =====================================================
# 3. PARÂMETROS DA SIMULAÇÃO (ENTRADAS GERAIS)
# =====================================================
st.markdown("---")
st.markdown("### 3. Ajustar Parâmetros do Lote e Consumo")
p1, p2, p3, p4 = st.columns(4)

with p1:
    massa_final = st.number_input("Massa final desejada (kg MS/ha)", value=3000, step=100, key="mf_aj")
    taxa_acumulo = st.number_input("Taxa de acúmulo (kg MS/ha/dia)", value=40.0, step=1.0, format="%.1f", key="ta_aj")
    
with p2:
    periodo_dias = st.number_input("Período da Simulação (dias)", value=30, step=1, key="pd_aj")
    data_inicio_sim = st.date_input("Data Início", value=date.today(), format="DD/MM/YYYY", key="dt_ini_aj")
    data_fim_calc = data_inicio_sim + timedelta(days=int(periodo_dias))
    st.markdown(f"**Data Fim:** {data_fim_calc.strftime('%d/%m/%Y')}")

with p3:
    cms = st.number_input("cMS (%PV)", value=2.5, step=0.1, format="%.1f", key="cms_aj")
    ofertado = st.number_input("Ofertado (n)", value=4.0, step=0.1, format="%.1f", key="of_aj")
    oferta = cms * ofertado
    st.markdown(f"**Oferta Forragem:** {fmt_br(oferta, 1)} %PV")

with p4:
    peso_inicio = st.number_input("Peso início (kg)", value=450, step=10, key="pi_aj")
    gmd = st.number_input("GMD (kg/dia)", value=0.60, step=0.05, format="%.2f", key="gmd_aj")
    peso_fim = peso_inicio + (gmd * periodo_dias)
    peso_medio = (peso_inicio + peso_fim) / 2
    st.markdown(f"**Peso Fim:** {fmt_br(peso_fim, 2)} kg")
    st.markdown(f"**Peso Médio:** {fmt_br(peso_medio, 2)} kg")

# =====================================================
# 📊 CÁLCULOS INTERMEDIÁRIOS RESTAURADOS NA TELA
# =====================================================
st.markdown("#### 📊 Indicadores Consolidados do Bloco Atual")

total_area_bloco = 0.0
total_ua_bloco = 0.0
total_cabecas_bloco = 0.0
produtividade_media_bloco = 0.0
massa_inicial_ponderada = 0.0

if not df_filtrado.empty:
    massa_vezes_area = 0.0
    for idx, row in df_filtrado.iterrows():
        d_area = float(row["Area util"]) if pd.notnull(row["Area util"]) else 0.0
        d_massa_ini = float(row["Massa seca"]) if pd.notnull(row["Massa seca"]) else 0.0
        
        if d_area > 0:
            producao_por_ha = taxa_acumulo * periodo_dias
            massa_teto = d_massa_ini + producao_por_ha
            perfil_pastejo = max(0.0, massa_teto - massa_final)
            desaparecimento_periodo_ua = (450 * (oferta / 100)) * periodo_dias
            
            d_ua_ha = perfil_pastejo / desaparecimento_periodo_ua if desaparecimento_periodo_ua > 0 else 0.0
            d_ua_total = d_ua_ha * d_area
            eq_ua = peso_medio / 450
            d_cabecas = d_ua_total / eq_ua if eq_ua > 0 else 0.0
            
            total_area_bloco += d_area
            total_ua_bloco += d_ua_total
            total_cabecas_bloco += d_cabecas
            massa_vezes_area += (d_massa_ini * d_area)

    if total_area_bloco > 0:
        tl_media_cab_ha = total_cabecas_bloco / total_area_bloco
        produtividade_media_bloco = tl_media_cab_ha * gmd * periodo_dias
        massa_inicial_ponderada = massa_vezes_area / total_area_bloco

producao_total_ha = taxa_acumulo * periodo_dias
massa_teto_ponderada = massa_inicial_ponderada + producao_total_ha
tl_ua_ha_bloco = total_ua_bloco / total_area_bloco if total_area_bloco > 0 else 0.0
tl_cab_ha_bloco = total_cabecas_bloco / total_area_bloco if total_area_bloco > 0 else 0.0

# Renderização dos painéis de indicadores intermediários na tela
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Área Total do Bloco", f"{fmt_br(total_area_bloco, 2)} ha")
    st.metric("Massa Teto Média", f"{fmt_br(massa_teto_ponderada, 0)} kg MS/ha")
with m2:
    st.metric("Produção do Período", f"{fmt_br(producao_total_ha, 0)} kg MS/ha")
    st.metric("Capacidade Total (UA)", f"{fmt_br(total_ua_bloco, 1)} UA")
with m3:
    st.metric("Taxa de Lotação (UA/ha)", f"{fmt_br(tl_ua_ha_bloco, 2)} UA/ha")
    st.metric("Total de Cabeças", f"{fmt_br(total_cabecas_bloco, 0)} cab")
with m4:
    st.metric("Taxa de Lotação (Cab/ha)", f"{fmt_br(tl_cab_ha_bloco, 2)} cab/ha")
    st.metric("Produtividade Esperada", f"{fmt_br(produtividade_media_bloco, 1)} kg/ha")

# =====================================================
# BOTÃO DE ADICIONAR AO PLANEJAMENTO
# =====================================================
st.write("")
if st.button("➕ Adicionar Bloco ao Planejamento Temporário", use_container_width=True, disabled=ja_contem_duplicada):
    if total_area_bloco == 0:
        st.warning("Não há divisões válidas calculadas ou selecionadas.")
    else:
        modulos_string = ", ".join(sorted(df_filtrado["Modulo"].dropna().astype(str).unique().tolist()))
        divisoes_string = ", ".join(sorted(df_filtrado["Divisao"].dropna().astype(str).unique().tolist()))
        
        novo_bloco = {
            "Fazenda": fazenda_base,
            "Módulo": modulos_string,
            "Divisões": divisoes_string,
            "Área (ha)": round(total_area_bloco, 2),
            "Data Início": data_inicio_sim.strftime('%d/%m/%Y'),
            "Data Fim": data_fim_calc.strftime('%d/%m/%Y'),
            "Dias": int(periodo_dias),
            "UA Total": round(total_ua_bloco, 1),
            "Cabeças": int(round(total_cabecas_bloco, 0)),
            "TL (UA/ha)": round(tl_ua_ha_bloco, 2),
            "Peso Médio (kg)": round(peso_medio, 1),
            "Produtividade Ponderada (kg/ha)": round(produtividade_media_bloco, 1)
        }
        st.session_state["simulacoes_salvas"].append(novo_bloco)
        st.session_state["contador_filtros"] += 1
        st.toast("Bloco adicionado com sucesso!", icon="🟢")
        st.rerun()

# =====================================================
# TABELA TEMPORÁRIA ACUMULADA
# =====================================================
st.markdown("---")
st.markdown("### 📋 Planejamentos Temporários Acumulados")

if st.session_state["simulacoes_salvas"]:
    df_temp_all = pd.DataFrame(st.session_state["simulacoes_salvas"])
    df_temp_fazenda = df_temp_all[df_temp_all["Fazenda"] == fazenda_base].reset_index(drop=True)
    
    if not df_temp_fazenda.empty:
        df_editado = st.data_editor(df_temp_fazenda, use_container_width=True, hide_index=False, num_rows="dynamic", key="editor_planejamento")
        
        if len(df_editado) != len(df_temp_fazenda):
            outras_fazendas = df_temp_all[df_temp_all["Fazenda"] != fazenda_base].to_dict(orient="records")
            st.session_state["simulacoes_salvas"] = outras_fazendas + df_editado.to_dict(orient="records")
            st.rerun()

        # =====================================================
        # GERAÇÃO DE TEXTO E RELATÓRIO
        # =====================================================
        texto_wa = f"📝 *PLANEJAMENTO - FAZENDA {fazenda_base.upper()}*\n```\n"
        for idx, row in df_editado.iterrows():
            texto_wa += f"| {str(row['Divisões'])[:12]:<12} | {row['Área (ha)']:>4}ha | {row['TL (UA/ha)']:>5} UA/ha |\n"
        texto_wa += "```"
        link_whatsapp = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"

        html_pdf_base = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 30px; }}
                h2 {{ color: #1B4332; border-bottom: 2px solid #2D6A4F; padding-bottom: 8px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ border: 1px solid #DDD; padding: 10px; text-align: center; }}
                th {{ background-color: #2D6A4F; color: white; }}
                tr:nth-child(even) {{ background-color: #F9F9F9; }}
            </style>
        </head>
        <body>
            <h2>Relatório de Planejamento de Pastagens - Fazenda {fazenda_base}</h2>
            <table>
                <tr>
                    <th>Módulo</th><th>Divisões</th><th>Área (ha)</th><th>Período</th><th>Dias</th><th>UA Total</th><th>Cabeças</th><th>TL (UA/ha)</th>
                </tr>
        """
        for idx, row in df_editado.iterrows():
            html_pdf_base += f"""
                <tr>
                    <td>{row['Módulo']}</td><td>{row['Divisões']}</td><td>{fmt_br(row['Área (ha)'], 2)}</td>
                    <td>{row['Data Início']} - {row['Data Fim']}</td><td>{row['Dias']}</td>
                    <td>{fmt_br(row['UA Total'], 1)}</td><td>{row['Cabeças']}</td><td>{fmt_br(row['TL (UA/ha)'], 2)}</td>
                </tr>
            """
        
        html_pdf = html_pdf_base + "</table></body></html>"

        # =====================================================
        # BOTÕES DE AÇÃO
        # =====================================================
        col_wa, col_pdf, col_pdf_comp, col_limpar = st.columns([1.5, 1, 1, 1])
        with col_wa:
            st.markdown(f'<a href="{link_whatsapp}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; padding:10px; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">💬 Enviar via WhatsApp</button></a>', unsafe_allow_html=True)
            
        with col_pdf:
            st.download_button("📄 Baixar Relatório", data=html_pdf, file_name=f"planejamento_{fazenda_base.lower()}.html", mime="text/html", use_container_width=True)
            
        with col_pdf_comp:
            # Melhoria na injeção de parâmetros adicionais de forma limpa e isolada
            html_pdf_completo = html_pdf_base + f"""
            </table>
            <br>
            <h2>Parâmetros e Indicadores do Lote</h2>
            <ul>
                <li><b>Massa Final Desejada:</b> {fmt_br(massa_final, 0)} kg MS/ha</li>
                <li><b>Taxa de Acúmulo:</b> {fmt_br(taxa_acumulo, 1)} kg MS/ha/dia</li>
                <li><b>Consumo de Matéria Seca (cMS):</b> {fmt_br(cms, 1)} %PV</li>
                <li><b>Ofertado (n):</b> {fmt_br(ofertado, 1)}</li>
                <li><b>Oferta de Forragem:</b> {fmt_br(oferta, 1)} %PV</li>
                <li><b>Peso Início:</b> {fmt_br(peso_inicio, 0)} kg</li>
                <li><b>GMD:</b> {fmt_br(gmd, 2)} kg/dia</li>
                <li><b>Peso Médio do Lote:</b> {fmt_br(peso_medio, 2)} kg</li>
            </ul>
            </body>
            </html>
            """
            st.download_button("📊 Relatório Completo", data=html_pdf_completo, file_name=f"relatorio_completo_{fazenda_base.lower()}.html", mime="text/html", use_container_width=True)
            
        with col_limpar:
            if st.button("🗑️ Limpar Toda a Tabela Temporária", use_container_width=True):
                st.session_state["simulacoes_salvas"] = [s for s in st.session_state["simulacoes_salvas"] if s["Fazenda"] != fazenda_base]
                st.rerun()

       # =====================================================
        # 4. MAPA VISUAL (CONFIGURADO PARA O SERVIDOR)
        # =====================================================
        st.markdown("---")
        st.markdown("### 🗺️ 4. Mapa Visual em Imagem de Satélite")

        # Procura a pasta 'mapas' na mesma raiz do script
        pasta_mapas = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapas")
        
        # Constrói o nome do arquivo (ajuste para .upper() se necessário)
        nome_arquivo = f"{fazenda_base.upper()}.geojson"
        caminho_completo_mapa = os.path.join(pasta_mapas, nome_arquivo)

        if FOLIUM_DISPONIVEL:
            if os.path.exists(caminho_completo_mapa):
                try:
                    with open(caminho_completo_mapa, "r", encoding="utf-8") as f:
                        dados_geojson = json.load(f)
                    
                    # Processamento das feições (Limpeza de polígonos)
                    feicoes_limpas = [f for f in dados_geojson.get('features', []) 
                                     if f.get('geometry', {}).get('type') in ['Polygon', 'MultiPolygon']]
                    dados_geojson['features'] = feicoes_limpas

                    # Coleta de coordenadas para centralização
                    coordenadas = []
                    for feature in feicoes_limpas:
                        geom = feature['geometry']
                        # Captura as coordenadas do primeiro anel
                        coords = geom['coordinates'][0] if geom['type'] == 'Polygon' else geom['coordinates'][0][0]
                        for c in coords:
                            coordenadas.append([c[1], c[0]])

                    centro_mapa = [np.mean([c[0] for c in coordenadas]), np.mean([c[1] for c in coordenadas])] if coordenadas else [-10.0, -50.0]
                    
                    m = folium.Map(location=centro_mapa, zoom_start=14, tiles=None)
                    
                    # Camada Base Satélite
                    folium.TileLayer(
                        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                        attr='Esri', name='Satélite', overlay=False, control=True
                    ).add_to(m)

                    # Estilização
                    def estilo_modulo(feature):
                        nome = str(feature['properties'].get('Divisao') or feature['properties'].get('name') or "").strip()
                        return {'fillColor': '#22C55E' if nome in divisoes_ja_simuladas else '#EF4444', 
                                'color': '#FFFFFF', 'fillOpacity': 0.4 if nome in divisoes_ja_simuladas else 0.2, 'weight': 2}

                    folium.GeoJson(dados_geojson, style_function=estilo_modulo).add_to(m)

                    # Adição de textos (DivIcon)
                    for feature in dados_geojson['features']:
                        nome = str(feature['properties'].get('Divisao') or feature['properties'].get('name') or "").strip()
                        geom = feature['geometry']
                        pts = geom['coordinates'][0][0] if geom['type'] == 'MultiPolygon' else geom['coordinates'][0]
                        lat_p, lon_p = np.mean([p[1] for p in pts]), np.mean([p[0] for p in pts])
                        
                        html_texto = f'''<div style="font-family: Arial; font-size: 11px; font-weight: bold; color: white; 
                                        background-color: rgba(0,0,0,0.85); padding: 2px 6px; border-radius: 3px; 
                                        border: 1px solid white; white-space: nowrap;">{nome}</div>'''
                        
                        folium.Marker([lat_p, lon_p], icon=folium.DivIcon(html=html_texto)).add_to(m)

                    if coordenadas:
                        m.fit_bounds(coordenadas)

                    st_folium(m, width=1300, height=550)
                    
                except Exception as e:
                    st.error(f"Erro ao processar o mapa: {e}")
            else:
                st.error(f"Arquivo não encontrado: **{nome_arquivo}**.")
                st.write(f"Certifique-se de que o arquivo está na pasta 'mapas' com o nome exato.")
        else:
            st.warning("Biblioteca folium não disponível.")