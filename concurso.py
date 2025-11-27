#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🎯 DASHBOARD VISUAL COM ANÁLISES - CONCURSO CÂMARA DE GOIÂNIA
================================================================================
🎨 Design Refinado e Moderno com:
- UI/UX minimalista e elegante
- Animações suaves e sofisticadas
- Fundo com efeito de faiscas subindo
- Expansível extremamente simples
- Cores vibrantes e intuitivas

Tecnologias:
- Streamlit (interface)
- Altair (gráficos)
- gspread + OAuth2 (Google Sheets API)
- Requests (weather API)
- CSS3 Animations

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
import warnings
import json
import time
import requests

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Dashboard de Estudos - Câmara de Goiânia",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================================
# CSS CUSTOMIZADO - UI/UX PREMIUM COM ANIMAÇÕES E FUNDO DE FAISCAS
# ================================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    * {
        font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* BACKGROUND COM FAISCAS */
    @keyframes sparkle {
        0% {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
        100% {
            opacity: 0;
            transform: translateY(-100vh) scale(0);
        }
    }

    @keyframes twinkle {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 1; }
    }

    html, body {
        background: linear-gradient(135deg, #0f172a 0%, #1a1f3a 50%, #0f172a 100%);
        background-attachment: fixed;
        position: relative;
        overflow-x: hidden;
    }

    html::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(circle at 20% 50%, rgba(26, 115, 232, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(52, 168, 83, 0.1) 0%, transparent 50%);
        pointer-events: none;
        z-index: -1;
    }

    /* Faiscas */
    .sparkle {
        position: fixed;
        pointer-events: none;
        z-index: 1;
    }

    .spark {
        position: absolute;
        width: 2px;
        height: 2px;
        background: radial-gradient(circle, #1a73e8, transparent);
        border-radius: 50%;
        animation: sparkle 3s ease-out forwards;
    }

    .spark::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        background: inherit;
        border-radius: 50%;
        animation: twinkle 1.5s ease-in-out infinite;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* HEADER */
    .header-wrapper {
        animation: slideDown 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .header-container {
        background: linear-gradient(135deg, rgba(26, 115, 232, 0.95) 0%, rgba(13, 71, 161, 0.95) 100%);
        backdrop-filter: blur(20px);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 20px 60px rgba(26, 115, 232, 0.25), 
                    inset 1px 1px 0 rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        gap: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
    }

    .header-container:hover {
        box-shadow: 0 30px 80px rgba(26, 115, 232, 0.35),
                    inset 1px 1px 0 rgba(255, 255, 255, 0.15);
        transform: translateY(-2px);
    }

    .logo-section {
        flex: 0 0 auto;
    }

    .logo-section img {
        max-width: 180px;
        height: auto;
        filter: drop-shadow(0 8px 16px rgba(0,0,0,0.3));
        transition: transform 0.3s ease;
    }

    .logo-section img:hover {
        transform: scale(1.05);
    }

    .header-content {
        flex: 1;
    }

    .header-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -1px;
        background: linear-gradient(135deg, #ffffff 0%, #e0e7ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .header-subtitle {
        font-size: 0.95rem;
        opacity: 0.9;
        font-weight: 400;
        margin-top: 0.3rem;
        letter-spacing: 0.5px;
    }

    .header-info {
        flex: 0 0 auto;
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        border: 1px solid rgba(255,255,255,0.15);
        transition: all 0.3s ease;
    }

    .header-info:hover {
        background: rgba(255,255,255,0.12);
        border-color: rgba(255,255,255,0.25);
    }

    .info-item {
        margin: 0.5rem 0;
    }

    .info-label {
        opacity: 0.7;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }

    .info-value {
        font-size: 1rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }

    .temp-display {
        font-size: 1.6rem;
        font-weight: 800;
    }

    /* MÉTRICAS */
    .metric-card {
        background: white;
        padding: 1.8rem;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 1px solid rgba(26, 115, 232, 0.1);
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        animation: fadeInUp 0.6s ease-out;
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .metric-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 50px rgba(0,0,0,0.12);
        border-color: rgba(26, 115, 232, 0.3);
    }

    .metric-value {
        font-size: 2.8rem;
        font-weight: 800;
        line-height: 1;
        background: linear-gradient(135deg, #1a73e8 0%, #34a853 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .metric-label {
        font-size: 0.8rem;
        color: #5f6368;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.8rem;
        font-weight: 600;
    }

    /* DISCIPLINA SIMPLES */
    .disciplina-header {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 1.2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        border-left: 4px solid var(--cor-principal);
        cursor: pointer;
        transition: all 0.2s ease;
        animation: fadeInUp 0.6s ease-out;
    }

    .disciplina-header:hover {
        transform: translateX(4px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }

    .disciplina-info {
        flex: 1;
    }

    .disciplina-nome {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--cor-principal);
        margin: 0;
    }

    .disciplina-stats {
        font-size: 0.8rem;
        color: #80868b;
        margin-top: 0.2rem;
    }

    .progress-bar-wrapper {
        flex: 1.2;
        margin: 0 1rem;
    }

    .progress-bar-container {
        background: #f0f4f8;
        border-radius: 6px;
        height: 5px;
        overflow: hidden;
    }

    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #1a73e8, #34a853);
        border-radius: 6px;
        transition: width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    .pct-display {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--cor-principal);
        min-width: 50px;
        text-align: right;
    }

    /* CONTEÚDO SIMPLES */
    .conteudo-item {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        border-left: 3px solid #e8eaed;
        transition: all 0.2s ease;
        font-size: 0.95rem;
        animation: fadeInLeft 0.3s ease-out;
    }

    @keyframes fadeInLeft {
        from {
            opacity: 0;
            transform: translateX(-10px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .conteudo-item:hover {
        background: #f0f4f8;
        border-left-color: #1a73e8;
        transform: translateX(4px);
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

    /* SEÇÃO */
    .section-header {
        font-size: 1.5rem;
        font-weight: 800;
        color: white;
        margin: 2.5rem 0 1.5rem 0;
        padding: 1rem 1.5rem;
        background: linear-gradient(135deg, rgba(26, 115, 232, 0.9) 0%, rgba(52, 168, 83, 0.9) 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        gap: 1rem;
        letter-spacing: -0.5px;
        box-shadow: 0 8px 20px rgba(26, 115, 232, 0.2);
        animation: fadeInDown 0.6s ease-out;
    }

    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* CHART */
    .chart-container {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 1px solid rgba(26, 115, 232, 0.1);
        margin-bottom: 1.5rem;
        animation: fadeInUp 0.6s ease-out;
    }

    /* FOOTER */
    .footer-text {
        text-align: center;
        color: rgba(255,255,255,0.5);
        padding: 2rem 0 1rem;
        font-size: 0.85rem;
        border-top: 1px solid rgba(255,255,255,0.1);
        margin-top: 3rem;
    }

    /* EXPANDER SIMPLES */
    .stExpander {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }

    .stExpander > div {
        background: transparent !important;
    }

    /* RESPONSIVE */
    @media (max-width: 768px) {
        .header-container {
            flex-direction: column;
            text-align: center;
        }

        .header-info {
            text-align: center;
        }

        .disciplina-header {
            flex-direction: column;
            align-items: flex-start;
        }

        .progress-bar-wrapper {
            width: 100%;
            margin: 0.8rem 0 0 0;
        }
    }
</style>

<!-- Script para gerar faiscas -->
<script>
function createSparks() {
    const container = document.createElement('div');
    container.className = 'sparkle';
    document.body.appendChild(container);

    const sparkCount = 15;

    setInterval(() => {
        for (let i = 0; i < sparkCount; i++) {
            const spark = document.createElement('div');
            spark.className = 'spark';
            spark.style.left = Math.random() * 100 + '%';
            spark.style.bottom = '-10px';
            spark.style.background = ['#1a73e8', '#34a853', '#f57c00'][Math.floor(Math.random() * 3)];
            spark.style.animationDuration = (2 + Math.random() * 2) + 's';

            container.appendChild(spark);

            setTimeout(() => spark.remove(), 5000);
        }
    }, 800);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createSparks);
} else {
    createSparks();
}
</script>
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
# FUNÇÕES AUXILIARES
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

def criar_card_metrica(valor, label, icon="📊"):
    return f"""
    <div class="metric-card">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 2.8rem;">{icon}</div>
            <div>
                <div class="metric-value">{valor}</div>
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
    st.markdown('<div class="header-wrapper">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown(criar_card_metrica(stats['total'], "Total", "📚"), unsafe_allow_html=True)
    with col2:
        st.markdown(criar_card_metrica(stats['estudados'], "Estudados", "✅"), unsafe_allow_html=True)
    with col3:
        st.markdown(criar_card_metrica(stats['faltam'], "Faltando", "⏳"), unsafe_allow_html=True)
    with col4:
        st.markdown(criar_card_metrica(f"{stats['percentual']:.1f}%", "Progresso", "🎯"), unsafe_allow_html=True)

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
        st.markdown("**Pizzas por Disciplina**")

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

        # Header da disciplina
        st.markdown(f"""
        <div class="disciplina-header" style="--cor-principal: {cores['principal']};">
            <div class="disciplina-info">
                <p class="disciplina-nome">{cores['emoji']} {disciplina}</p>
                <div class="disciplina-stats">✓ {n_estudados}/{n_total} conteúdos</div>
            </div>
            <div class="progress-bar-wrapper">
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {pct}%; background: {cores['principal']};"></div>
                </div>
            </div>
            <div class="pct-display">{pct:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

        # Conteúdos em accordion
        with st.expander(f"📋 {n_total} conteúdos"):
            for idx, row in df_disc.iterrows():
                col_check, col_text = st.columns([0.05, 0.95])

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

    st.markdown(f'<div class="footer-text">✨ Dashboard Premium | Câmara Municipal de Goiânia | {datetime.now().strftime("%H:%M:%S")}</div>', 
               unsafe_allow_html=True)

if __name__ == "__main__":
    main()
