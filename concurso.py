#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🎯 DASHBOARD VISUAL COM ANÁLISES - CONCURSO CÂMARA DE GOIÂNIA
================================================================================
🎨 Design Limpo e Profissional com:
- Cores vibrantes (verde estudado, vermelho não estudado)
- Pizza charts na seção de análise visual
- Layout simples e elegante
- Containers menores para disciplinas
- UI/UX minimalista

Tecnologias:
- Streamlit (interface)
- Altair (gráficos)
- gspread + OAuth2 (Google Sheets API)
- Requests (weather API)

Data: 2025-11-27
SPREADSHEET_ID: 17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM ✅ CONFIGURADO
================================================================================
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import warnings
import json
import time
import requests
import locale

warnings.filterwarnings('ignore')

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass

# ================================================================================
# CONFIGURAÇÕES
# ================================================================================

st.set_page_config(
    page_title="Dashboard de Estudos - Câmara de Goiânia",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================================
# CSS CUSTOMIZADO
# ================================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    html, body {
        background: linear-gradient(135deg, #f5f7fa 0%, #f0f4f8 100%);
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Header */
    .header-container {
        background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 15px 50px rgba(13, 71, 161, 0.3);
        display: flex;
        align-items: center;
        gap: 2rem;
    }

    .logo-section {
        flex: 0 0 auto;
    }

    .logo-section img {
        max-width: 200px;
        height: auto;
        filter: drop-shadow(0 4px 10px rgba(0,0,0,0.2));
    }

    .header-content {
        flex: 1;
    }

    .header-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }

    .header-subtitle {
        font-size: 1rem;
        opacity: 0.95;
        font-weight: 400;
        margin-top: 0.3rem;
    }

    .header-info {
        flex: 0 0 auto;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 1.2rem 1.8rem;
        border: 1px solid rgba(255,255,255,0.2);
    }

    .info-item {
        margin: 0.5rem 0;
        line-height: 1.3;
    }

    .info-label {
        opacity: 0.85;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    .info-value {
        font-size: 1.1rem;
        font-weight: 700;
        margin-top: 0.1rem;
    }

    .temp-display {
        font-size: 1.8rem;
        font-weight: 800;
    }

    /* Métricas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        border-top: 4px solid #1a73e8;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .metric-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 45px rgba(0,0,0,0.12);
    }

    .metric-value {
        font-size: 2.8rem;
        font-weight: 800;
        color: #1a73e8;
        line-height: 1;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #5f6368;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 0.6rem;
        font-weight: 600;
    }

    /* Disciplinas Container Simples */
    .disciplina-simples {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        border-left: 5px solid var(--cor-principal);
        transition: all 0.2s ease;
    }

    .disciplina-simples:hover {
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        transform: translateX(4px);
    }

    .disciplina-info {
        flex: 1;
    }

    .disciplina-nome {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--cor-principal);
        margin: 0;
    }

    .disciplina-stats {
        font-size: 0.85rem;
        color: #5f6368;
        margin-top: 0.3rem;
    }

    .progress-bar-container {
        background: #e8f0fe;
        border-radius: 8px;
        height: 6px;
        overflow: hidden;
        flex: 1;
        margin: 0 1rem;
        min-width: 100px;
    }

    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #1a73e8, #34a853);
        border-radius: 8px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Conteúdo Card Simples */
    .conteudo-item {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        border-left: 3px solid #e8eaed;
        transition: all 0.2s ease;
        font-size: 0.95rem;
    }

    .conteudo-item:hover {
        background: #f0f4f8;
        border-left-color: #1a73e8;
    }

    .conteudo-item.estudado {
        background: #e6f4ea;
        border-left-color: #34a853;
        opacity: 0.85;
    }

    .conteudo-item.estudado span {
        text-decoration: line-through;
        color: #80868b;
    }

    /* Seções */
    .section-header {
        font-size: 1.6rem;
        font-weight: 800;
        color: #202124;
        margin: 2rem 0 1.2rem 0;
        padding-bottom: 0.8rem;
        border-bottom: 3px solid #1a73e8;
        display: flex;
        align-items: center;
        gap: 1rem;
        letter-spacing: -0.5px;
    }

    .chart-container {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }

    /* Footer */
    .footer-text {
        text-align: center;
        color: #80868b;
        padding: 2rem 0 1rem;
        font-size: 0.85rem;
        border-top: 2px solid #e8eaed;
        margin-top: 3rem;
    }

    @media (max-width: 768px) {
        .header-container {
            flex-direction: column;
            text-align: center;
        }

        .header-info {
            text-align: center;
        }

        .logo-section img {
            max-width: 120px;
        }

        .disciplina-simples {
            flex-direction: column;
            align-items: flex-start;
        }
    }
</style>
""", unsafe_allow_html=True)

# ================================================================================
# CONFIGURAÇÕES
# ================================================================================

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

CORES_DISCIPLINAS = {
    'LÍNGUA PORTUGUESA': {'principal': '#d33427', 'emoji': '📖'},
    'RLM': {'principal': '#1f7c5c', 'emoji': '🧮'},
    'REALIDADE DE GOIÁS': {'principal': '#0d47a1', 'emoji': '🗺️'},
    'LEGISLAÇÃO APLICADA': {'principal': '#6d28d9', 'emoji': '⚖️'},
    'CONHECIMENTOS ESPECÍFICOS': {'principal': '#f57c00', 'emoji': '💡'}
}

# ================================================================================
# FUNÇÕES
# ================================================================================

def obter_data_formatada():
    hoje = datetime.now()
    meses = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
             7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    return f"{hoje.day} de {meses[hoje.month]} de {hoje.year}"

@st.cache_data(ttl=600)
def obter_temperatura_goiania():
    try:
        response = requests.get(
            'https://api.open-meteo.com/v1/forecast',
            params={'latitude': -15.8267, 'longitude': -48.9626, 'current': 'temperature_2m',
                    'temperature_unit': 'celsius', 'timezone': 'America/Sao_Paulo'},
            timeout=5
        )
        if response.status_code == 200:
            return round(response.json()['current']['temperature_2m'], 1)
    except:
        pass
    return "N/A"

@st.cache_resource
def conectar_google_sheets():
    try:
        if 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets["gcp_service_account"])
        else:
            with open('credentials.json', 'r') as f:
                credentials_dict = json.load(f)
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        return gspread.authorize(credentials)
    except:
        st.error("❌ Erro ao conectar com Google Sheets")
        return None

@st.cache_data(ttl=60)
def carregar_dados_sheets(_client, spreadsheet_id, worksheet_name):
    try:
        worksheet = _client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        df = pd.DataFrame(worksheet.get_all_records())
        df['Status'] = df['Status'].astype(str).str.upper()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES'])
        return df
    except:
        return None

def atualizar_status_sheets(client, spreadsheet_id, worksheet_name, linha, novo_status):
    try:
        client.open_by_key(spreadsheet_id).worksheet(worksheet_name).update_cell(linha, 4, str(novo_status))
        return True
    except:
        return False

def calcular_estatisticas(df, cargo):
    df_cargo = df[df['Cargo'] == cargo].copy()
    if len(df_cargo) == 0:
        return None

    total = len(df_cargo)
    estudados = df_cargo['Estudado'].sum()
    faltam = total - estudados
    percentual = (estudados / total * 100) if total > 0 else 0

    stats_disc = df_cargo.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
    stats_disc.columns = ['Disciplina', 'Estudados', 'Total']
    stats_disc['Faltam'] = stats_disc['Total'] - stats_disc['Estudados']
    stats_disc['Percentual'] = (stats_disc['Estudados'] / stats_disc['Total'] * 100).round(1)

    return {
        'total': int(total),
        'estudados': int(estudados),
        'faltam': int(faltam),
        'percentual': float(percentual),
        'por_disciplina': stats_disc,
        'df_cargo': df_cargo
    }

def criar_card_metrica(valor, label, icon="📊", cor="#1a73e8"):
    return f"""
    <div class="metric-card">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 3rem;">{icon}</div>
            <div>
                <div class="metric-value" style="color: {cor};">{valor}</div>
                <div class="metric-label">{label}</div>
            </div>
        </div>
    </div>
    """

def criar_grafico_pizza_disciplina(estudados, total):
    data = pd.DataFrame({
        'Status': ['Estudado', 'Faltando'],
        'Quantidade': [estudados, total - estudados]
    })

    chart = alt.Chart(data).mark_arc(innerRadius=40, stroke=None).encode(
        theta=alt.Theta('Quantidade:Q'),
        color=alt.Color('Status:N', scale=alt.Scale(domain=['Estudado', 'Faltando'], 
                                                      range=['#34a853', '#ef5350']))
    ).properties(width=120, height=120)

    return chart

def criar_grafico_pizza_geral(estudados, faltam):
    data = pd.DataFrame({
        'Categoria': ['Estudados', 'Faltando'],
        'Quantidade': [estudados, faltam]
    })

    chart = alt.Chart(data).mark_arc(innerRadius=60, cornerRadius=8, stroke=None).encode(
        theta=alt.Theta('Quantidade:Q'),
        color=alt.Color('Categoria:N', scale=alt.Scale(domain=['Estudados', 'Faltando'], 
                                                        range=['#34a853', '#ef5350']))
    ).properties(width=250, height=250)

    return chart

def criar_grafico_barras(stats):
    df = stats['por_disciplina'].sort_values('Percentual', ascending=True)

    chart = alt.Chart(df).mark_bar(cornerRadius=6, stroke=None).encode(
        x=alt.X('Percentual:Q', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y('Disciplina:N', sort='-x'),
        color=alt.Color('Percentual:Q', scale=alt.Scale(scheme='greens'))
    ).properties(width=500, height=280)

    return chart

# ================================================================================
# INTERFACE PRINCIPAL
# ================================================================================

def main():
    data_hoje = obter_data_formatada()
    temperatura = obter_temperatura_goiania()

    # Header
    st.markdown(f"""
    <div class="header-container">
        <div class="logo-section">
            <img src="{LOGO_URL}" alt="Câmara Municipal de Goiânia">
        </div>

        <div class="header-content">
            <div class="header-title">📚 Dashboard de Estudos</div>
            <div class="header-subtitle">Acompanhamento Visual com Análises - Concurso Câmara de Goiânia</div>
        </div>

        <div class="header-info">
            <div class="info-item">
                <div class="info-label">📍 Localização</div>
                <div class="info-value">Goiânia - GO</div>
            </div>
            <div class="info-item">
                <div class="info-label">📅 Data</div>
                <div class="info-value">{data_hoje}</div>
            </div>
            <div class="info-item">
                <div class="info-label">🌡️ Temperatura</div>
                <div class="temp-display">{temperatura}°C</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        cargo_selecionado = st.selectbox("Seu cargo:", ["Analista Técnico Legislativo", "Agente Administrativo"])
        st.markdown("---")
        if st.button("🔄 Recarregar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    client = conectar_google_sheets()
    if client is None:
        st.stop()

    with st.spinner("📥 Carregando dados..."):
        df = carregar_dados_sheets(client, SPREADSHEET_ID, WORKSHEET_NAME)

    if df is None or len(df) == 0:
        st.error("❌ Nenhum dado encontrado")
        st.stop()

    stats = calcular_estatisticas(df, cargo_selecionado)
    if stats is None:
        st.warning(f"⚠️ Sem dados para: {cargo_selecionado}")
        st.stop()

    # Métricas
    st.markdown('<div class="section-header">📊 Visão Geral</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(criar_card_metrica(stats['total'], "Total", "📚", "#1a73e8"), unsafe_allow_html=True)
    with col2:
        st.markdown(criar_card_metrica(stats['estudados'], "Estudados", "✅", "#34a853"), unsafe_allow_html=True)
    with col3:
        st.markdown(criar_card_metrica(stats['faltam'], "Faltando", "⏳", "#ef5350"), unsafe_allow_html=True)
    with col4:
        st.markdown(criar_card_metrica(f"{stats['percentual']:.1f}%", "Progresso", "🎯", "#1a73e8"), unsafe_allow_html=True)

    # Análise Visual
    st.markdown('<div class="section-header">📈 Análise Visual</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.5, 1.5, 1])

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.altair_chart(criar_grafico_pizza_geral(stats['estudados'], stats['faltam']), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.altair_chart(criar_grafico_barras(stats), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("**Pizza Charts por Disciplina**")

        for _, row in stats['por_disciplina'].iterrows():
            st.altair_chart(criar_grafico_pizza_disciplina(int(row['Estudados']), int(row['Total'])), 
                          use_container_width=True)
            st.caption(f"{row['Disciplina']}: {row['Percentual']:.0f}%")

        st.markdown('</div>', unsafe_allow_html=True)

    # Disciplinas
    st.markdown('<div class="section-header">📚 Conteúdos por Disciplina</div>', unsafe_allow_html=True)

    disciplinas_disponiveis = sorted(stats['df_cargo']['Disciplinas'].unique().tolist())
    disciplina_filtro = st.selectbox("Filtrar:", ["Todas"] + disciplinas_disponiveis, key="filtro_disc")

    df_cargo = stats['df_cargo'].copy()
    df_cargo['linha_planilha'] = df_cargo.index + 2

    if disciplina_filtro != "Todas":
        df_cargo = df_cargo[df_cargo['Disciplinas'] == disciplina_filtro]

    for disciplina in sorted(df_cargo['Disciplinas'].unique()):
        cores = CORES_DISCIPLINAS.get(disciplina, {'principal': '#1a73e8', 'emoji': '📖'})
        df_disc = df_cargo[df_cargo['Disciplinas'] == disciplina].copy()
        n_estudados = df_disc['Estudado'].sum()
        n_total = len(df_disc)
        pct = (n_estudados / n_total * 100) if n_total > 0 else 0

        # Container simples da disciplina
        st.markdown(f"""
        <div class="disciplina-simples" style="--cor-principal: {cores['principal']};">
            <div class="disciplina-info">
                <p class="disciplina-nome">{cores['emoji']} {disciplina}</p>
                <div class="disciplina-stats">✓ {n_estudados}/{n_total} ({pct:.0f}%)</div>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: {pct}%; background: {cores['principal']};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Accordion
        with st.expander(f"📋 Ver {n_total} conteúdos", expanded=False):
            for idx, row in df_disc.iterrows():
                col_check, col_text = st.columns([0.06, 0.94])

                with col_check:
                    checked = st.checkbox("✓", value=bool(row['Estudado']), key=f"check_{idx}", 
                                        label_visibility="collapsed")

                    if checked != bool(row['Estudado']):
                        with st.spinner("💾"):
                            if atualizar_status_sheets(client, SPREADSHEET_ID, WORKSHEET_NAME, 
                                                      int(row['linha_planilha']), 'TRUE' if checked else 'FALSE'):
                                time.sleep(0.2)
                                st.cache_data.clear()
                                st.rerun()

                with col_text:
                    classe = "estudado" if row['Estudado'] else ""
                    st.markdown(f"""
                    <div class="conteudo-item {classe}">
                        <span>{'✓ ' if row['Estudado'] else ''}{row['Conteúdos']}</span>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("")

    st.markdown(f'<div class="footer-text">✨ Dashboard Interativo | Câmara Municipal de Goiânia | {datetime.now().strftime("%H:%M:%S")}</div>', 
               unsafe_allow_html=True)

if __name__ == "__main__":
    main()
