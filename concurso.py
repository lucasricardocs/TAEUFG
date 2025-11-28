#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🚀 DASHBOARD DE ESTUDOS ULTIMATE - CÂMARA MUNICIPAL DE GOIÂNIA
================================================================================
VERSÃO: ULTIMATE MERGED (HIGH CONTRAST & ANIMATIONS)
DATA: 2025-11-27

DESCRIÇÃO:
Código unificado com novas animações CSS, cores de alto contraste e
gráficos de visualização ampliados.

REQUISITOS:
- Python 3.8+
- Bibliotecas: streamlit, pandas, altair, gspread, google-auth
- Arquivo 'credentials.json' (Google Service Account)
================================================================================
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import warnings
import json
import time
import requests
import locale

# ================================================================================
# 1. CONFIGURAÇÃO INICIAL DO AMBIENTE
# ================================================================================

warnings.filterwarnings('ignore')

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except Exception:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except:
        pass

st.set_page_config(
    page_title="Dashboard Ultimate",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================================
# 2. ESTILOS CSS UNIFICADOS (LAYOUT + ANIMAÇÕES + CORES NOVAS)
# ================================================================================

st.markdown("""
<style>
    /* ==========================================================================
    FONTS & RESET
    ==========================================================================
    */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        box-sizing: border-box;
    }

    [data-testid="stMainBlockContainer"] {
        background-color: #f8fafc; /* Fundo claro para contraste */
        color: #0f172a;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ==========================================================================
    ANIMAÇÕES (KEYFRAMES)
    ==========================================================================
    */
    @keyframes slideUpFade {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    @keyframes popIn {
        0% { opacity: 0; transform: scale(0.5); }
        70% { transform: scale(1.1); }
        100% { opacity: 1; transform: scale(1); }
    }

    @keyframes fillProgress {
        from { width: 0; }
        to { width: 100%; }
    }

    @keyframes shimmer {
        to { background-position: 200% center; }
    }
    
    @keyframes sectionFadeIn {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* ==========================================================================
    HEADER & LAYOUT
    ==========================================================================
    */
    .header-container {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: flex-start;
        background: #ffffff; /* Fundo Branco */
        padding: 1.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        position: relative;
        overflow: hidden;
        color: #0f172a;
        gap: 2rem;
    }

    .header-logo {
        flex-shrink: 0;
    }

    .header-logo img {
        max-width: 180px;
        height: auto;
        display: block;
    }

    .header-content {
        flex-grow: 1;
        text-align: left;
    }

    .header-content h1 { 
        font-size: 2.5rem; 
        font-weight: 800; 
        margin: 0; 
        color: #0f172a; /* Texto Escuro */
        letter-spacing: -1px;
        line-height: 1.2;
    }
    
    .header-info { 
        flex-shrink: 0;
        text-align: right;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .info-row {
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
    }

    /* ==========================================================================
    PROGRESS BAR ANIMADA (NOVO)
    ==========================================================================
    */
    .progress-bar-container {
        width: 100%;
        height: 12px;
        background: #e2e8f0;
        border-radius: 10px;
        overflow: hidden;
        margin: 20px 0;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #f59e0b, #ea580c); /* Laranja Vibrante */
        border-radius: 10px;
        animation: fillProgress 1.5s ease-out forwards;
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.6);
    }

    /* ==========================================================================
    CARDS DE MÉTRICAS
    ==========================================================================
    */
    .metric-card { 
        background: white; 
        padding: 1.5rem; 
        border-radius: 16px; 
        border: 1px solid #cbd5e1; 
        text-align: center; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); 
        transition: all 0.3s ease;
    }
    
    .metric-card:hover { 
        transform: translateY(-5px) scale(1.02); 
        border-color: #3b82f6;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }
    
    .metric-value { 
        font-size: 3.2rem; 
        font-weight: 800; 
        line-height: 1;
        margin-bottom: 0.5rem;
        letter-spacing: -2px;
    }
    
    /* ==========================================================================
    BADGES & GAMIFICAÇÃO
    ==========================================================================
    */
    .badge-container { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-bottom: 20px; }
    .badge { 
        background: linear-gradient(135deg, #10b981, #059669); 
        color: white; 
        padding: 6px 16px; 
        border-radius: 50px; 
        font-weight: 700; 
        font-size: 0.8rem; 
        box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3);
        animation: popIn 0.5s ease forwards;
    }

    /* ==========================================================================
    DISCIPLINA HEADER & LISTA
    ==========================================================================
    */
    .disciplina-header {
        margin-top: 35px;
        border-bottom: 3px solid; /* Linha mais grossa para contraste */
        padding-bottom: 8px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    
    .disciplina-header:hover {
        transform: translateX(10px);
    }

    .topic-row {
        display: flex;
        align-items: center;
        padding: 14px 10px;
        border-bottom: 1px solid #f1f5f9;
        transition: background-color 0.2s;
        border-radius: 6px;
    }
    
    .topic-row:hover {
        background-color: #e0f2fe; /* Azul muito claro no hover */
    }
    
    .topic-text {
        font-size: 1rem;
        color: #1e293b; /* Texto escuro para contraste */
        font-weight: 500;
        margin-left: 10px;
    }
    
    .topic-text.done {
        color: #94a3b8;
        text-decoration: line-through;
        opacity: 0.8;
    }

    .topic-date {
        font-size: 0.75rem;
        background-color: #dcfce7;
        color: #166534;
        padding: 2px 8px;
        border-radius: 4px;
        margin-left: 8px;
        border: 1px solid #86efac;
    }

    /* ==========================================================================
    FADE GERAL
    ==========================================================================
    */
    .section-fade {
        animation: sectionFadeIn 0.8s ease-out forwards;
        opacity: 0;
    }
    .section-fade:nth-child(1) { animation-delay: 0.1s; }
    .section-fade:nth-child(2) { animation-delay: 0.2s; }
    .section-fade:nth-child(3) { animation-delay: 0.3s; }

    /* Responsividade */
    @media (max-width: 768px) {
        .header-container { flex-direction: column; text-align: center; padding: 1.5rem; gap: 1rem; }
        .header-content { text-align: center; }
        .header-info { text-align: center; }
        .metric-value { font-size: 2.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# ================================================================================
# 3. CONFIGURAÇÕES GERAIS E PALETA DE CORES (CONTRASTE AUMENTADO)
# ================================================================================

# IDs de Conexão
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'

LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

# CORES NOVAS: Mais saturadas e com melhor contraste
CORES = {
    'LÍNGUA PORTUGUESA': '#DC2626',       # Vermelho Profundo
    'RLM': '#059669',                     # Verde Esmeralda Escuro
    'REALIDADE DE GOIÁS': '#2563EB',      # Azul Royal Vibrante
    'LEGISLAÇÃO APLICADA': '#7C3AED',     # Roxo Neon Intenso
    'CONHECIMENTOS ESPECÍFICOS': '#D97706'# Âmbar Queimado
}

# ================================================================================
# 4. BACKEND (GOOGLE SHEETS)
# ================================================================================

def conectar_google_sheets():
    try:
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            with open('credentials.json', 'r') as f:
                creds_dict = json.load(f)
        
        escopos = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credenciais = Credentials.from_service_account_info(creds_dict, scopes=escopos)
        client = gspread.authorize(credenciais)
        return client
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

@st.cache_data(ttl=15)
def carregar_dados_planilha(_client):
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        
        if df.empty: return None
            
        df['Status'] = df['Status'].astype(str).str.upper().str.strip()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES', 'OK'])
        
        coluna_data = None
        possiveis_nomes = ['Data', 'Data Estudo', 'Data Conclusão', 'Date']
        for nome in possiveis_nomes:
            if nome in df.columns:
                coluna_data = nome
                break
        if not coluna_data and len(df.columns) >= 5:
            coluna_data = df.columns[4]
            
        if coluna_data:
            df['Data_Real'] = pd.to_datetime(df[coluna_data], format='%d/%m/%Y', errors='coerce')
        else:
            df['Data_Real'] = pd.NaT
        return df
    except Exception as e:
        st.error(f"Erro nos dados: {e}")
        return None

def atualizar_status(client, linha_planilha, novo_status_bool):
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        status_str = 'TRUE' if novo_status_bool else 'FALSE'
        ws.update_cell(linha_planilha, 4, status_str)
        if novo_status_bool:
            ws.update_cell(linha_planilha, 5, datetime.now().strftime('%d/%m/%Y'))
        else:
            ws.update_cell(linha_planilha, 5, '')
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

@st.cache_data(ttl=600)
def obter_temperatura_local():
    try:
        url = 'https://api.open-meteo.com/v1/forecast?latitude=-15.8267&longitude=-48.9626&current=temperature_2m&timezone=America/Sao_Paulo'
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            return round(r.json()['current']['temperature_2m'], 1)
    except: pass
    return "--"

# ================================================================================
# 5. VISUALIZAÇÃO (GRÁFICOS AMPLIADOS)
# ================================================================================

def criar_heatmap_produtividade(df):
    df_filtrado = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    if df_filtrado.empty: return None
    
    contagem_diaria = df_filtrado.groupby('Data_Real').size().reset_index(name='count')
    
    chart = alt.Chart(contagem_diaria).mark_rect(cornerRadius=3, stroke='white', strokeWidth=2).encode(
        x=alt.X('yearmonthdate(Data_Real):O', title=None, axis=alt.Axis(format='%d/%m', labelColor='#64748b')),
        y=alt.Y('day(Data_Real):O', title=None, axis=None),
        color=alt.Color('count:Q', scale=alt.Scale(scheme='greens'), legend=None),
        tooltip=['Data_Real', 'count']
    ).properties(height=150, width='container').configure_view(strokeWidth=0).configure_axis(grid=False, domain=False)
    return chart

def criar_grafico_donut(concluido, total, cor_primaria):
    """
    Gráfico de Donut Ampliado para melhor visualização.
    Correção do erro de validação (radius removido do mark_text e texto isolado).
    """
    restante = total - concluido
    dados = pd.DataFrame({'Categoria': ['Concluído', 'Restante'], 'Valor': [concluido, restante]})
    
    base = alt.Chart(dados).encode(theta=alt.Theta("Valor", stack=True))
    
    # Arco do Donut
    pie = base.mark_arc(
        outerRadius=110,
        innerRadius=85,
        stroke='white', 
        strokeWidth=4,
        cornerRadius=6
    ).encode(
        color=alt.Color("Categoria", 
                        scale=alt.Scale(domain=['Concluído', 'Restante'], range=[cor_primaria, '#f1f5f9']), 
                        legend=None),
        tooltip=["Categoria", "Valor"],
        order=alt.Order("Categoria", sort="descending")
    )
    
    percentual = int(concluido/total*100) if total > 0 else 0
    
    # Texto Central (Criado como um gráfico independente para evitar herança de theta e erros de validação)
    texto = alt.Chart(pd.DataFrame({'dummy': [1]})).mark_text(
        size=28, 
        color=cor_primaria, 
        fontWeight='bold', 
        font='Inter'
    ).encode(
        text=alt.value(f"{percentual}%")
    )
    
    # Área do gráfico
    return (pie + texto).properties(width=280, height=280)

# ================================================================================
# 6. APP PRINCIPAL
# ================================================================================

def main():
    # Header
    temp = obter_temperatura_local()
    data_formatada = datetime.now().strftime('%d/%m')
    info_texto = f"Goiânia, {data_formatada} - {temp}º C"

    st.markdown(f"""
    <div class="header-container section-fade">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Logo">
        </div>
        <div class="header-content">
            <h1>DASHBOARD ULTIMATE</h1>
            <p style="color:#64748b; margin-top:5px; font-weight:500;">Performance • Constância • Aprovação</p>
        </div>
        <div class="header-info">
            <div class="info-row">{info_texto}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Conexão
    client = conectar_google_sheets()
    if not client: st.stop()
    
    df = carregar_dados_planilha(client)
    if df is None: st.warning("Carregando dados..."); st.stop()

    # Sidebar
    cargos = df['Cargo'].unique()
    cargo_sel = st.sidebar.selectbox("🎯 Selecione o Cargo:", cargos)
    df_cargo = df[df['Cargo'] == cargo_sel].copy()
    df_cargo['linha_planilha'] = df_cargo.index + 2

    # KPIs
    total = len(df_cargo)
    concluidos = df_cargo['Estudado'].sum()
    restantes = total - concluidos
    porcentagem = (concluidos / total * 100) if total > 0 else 0

    # Barra de Progresso Animada (NOVA)
    st.markdown(f"""
    <div class="section-fade">
        <div style="display:flex; justify-content:space-between; font-weight:700; color:#475569; margin-bottom:5px;">
            <span>Progresso Global</span>
            <span>{porcentagem:.1f}%</span>
        </div>
        <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: {porcentagem}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-card section-fade"><div class="metric-value" style="color:#3b82f6">{total}</div><div class="metric-label">Total Tópicos</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card section-fade"><div class="metric-value" style="color:#10b981">{concluidos}</div><div class="metric-label">Concluídos</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card section-fade"><div class="metric-value" style="color:#ef4444">{restantes}</div><div class="metric-label">Restantes</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card section-fade"><div class="metric-value" style="color:#8b5cf6">{porcentagem:.0f}%</div><div class="metric-label">Conquista</div></div>', unsafe_allow_html=True)

    st.write("")
    
    # Separador
    st.markdown("---")

    # Heatmap
    st.markdown("### 🔥 Ritmo de Estudos")
    grafico_heatmap = criar_heatmap_produtividade(df_cargo)
    if grafico_heatmap: st.altair_chart(grafico_heatmap, use_container_width=True)
    else: st.info("Histórico vazio. Estude hoje para marcar o gráfico!")
    
    # Separador
    st.markdown("---")

    # Gráficos de Donut Ampliados
    st.markdown("### 🍩 Progresso por Disciplina")
    stats = df_cargo.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
    stats.columns = ['Disciplina', 'Estudados', 'Total']
    
    cols = st.columns(3)
    for i, row in stats.iterrows():
        with cols[i % 3]:
            nome = row['Disciplina']
            cor = CORES.get(nome, '#475569')
            # Título do Gráfico com Cor
            st.markdown(f"<h4 style='text-align:center; color:{cor}; margin-bottom:0;'>{nome}</h4>", unsafe_allow_html=True)
            chart = criar_grafico_donut(row['Estudados'], row['Total'], cor)
            st.altair_chart(chart, use_container_width=True)

    # Separador
    st.markdown("---")

    # Lista de Conteúdos
    st.markdown("### 📚 Conteúdo Programático")
    lista_disc = sorted(df_cargo['Disciplinas'].unique().tolist())
    filtro = st.selectbox("Filtrar Disciplina:", ["Todas"] + lista_disc)
    
    view_df = df_cargo if filtro == "Todas" else df_cargo[df_cargo['Disciplinas'] == filtro]

    for disc in view_df['Disciplinas'].unique():
        sub = view_df[view_df['Disciplinas'] == disc]
        cor = CORES.get(disc, '#333')
        
        # Header da disciplina com a nova classe CSS
        st.markdown(f"""
        <div class="disciplina-header" style="border-color:{cor}; color:{cor};">
            <span style="font-size:1.3rem; font-weight:800;">{disc}</span>
            <span style="float:right; font-size:1rem; font-weight:600; background:{cor}20; padding:4px 12px; border-radius:20px;">
                {sub['Estudado'].sum()} / {len(sub)}
            </span>
        </div>
        """, unsafe_allow_html=True)

        for idx, row in sub.iterrows():
            c_chk, c_txt = st.columns([0.05, 0.95])
            
            with c_chk:
                key = f"chk_{idx}_{row['linha_planilha']}"
                val = st.checkbox("Status", value=bool(row['Estudado']), key=key, label_visibility="collapsed")
                
                if val != bool(row['Estudado']):
                    with st.spinner("💾"):
                        if atualizar_status(client, int(row['linha_planilha']), val):
                            st.toast("Salvo!", icon="✅")
                            time.sleep(0.5)
                            st.cache_data.clear()
                            st.rerun()

            css_class = "done" if row['Estudado'] else ""
            badge = f"<span class='topic-date'>Em: {row['Data_Real'].strftime('%d/%m')}</span>" if (row['Estudado'] and pd.notnull(row['Data_Real'])) else ""
            
            c_txt.markdown(f"""
            <div class="topic-row">
                <div class="topic-text {css_class}">
                    {row['Conteúdos']} {badge}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><br><div style='text-align:center; color:#cbd5e1; font-size:0.8rem;'>Dashboard Ultimate v4.1 • High Contrast Edition</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
