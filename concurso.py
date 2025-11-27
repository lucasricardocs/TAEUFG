#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🎯 DASHBOARD VISUAL COM ANÁLISES - CONCURSO CÂMARA DE GOIÂNIA
================================================================================
🎨 Design Profissional com:
- Cores vibrantes e contrastantes
- Lista de conteúdos expansível/colapsável
- Gráficos com fundo transparente
- Pizza chart para cada disciplina
- UI/UX moderno e intuitivo

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
# CSS CUSTOMIZADO - CORES VIBRANTES E PROFISSIONAIS
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
        max-width: 250px;
        height: auto;
        filter: drop-shadow(0 4px 10px rgba(0,0,0,0.2));
    }

    .header-content {
        flex: 1;
    }

    .header-title {
        font-size: 2.8rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }

    .header-subtitle {
        font-size: 1.1rem;
        opacity: 0.95;
        font-weight: 400;
        margin-top: 0.5rem;
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
        margin: 0.6rem 0;
        line-height: 1.4;
    }

    .info-label {
        opacity: 0.85;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    .info-value {
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }

    .temp-display {
        font-size: 2rem;
        font-weight: 800;
    }

    /* Métricas */
    .metric-card {
        background: white;
        padding: 2rem;
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
        font-size: 3.2rem;
        font-weight: 800;
        color: #1a73e8;
        line-height: 1;
    }

    .metric-label {
        font-size: 0.9rem;
        color: #5f6368;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 0.8rem;
        font-weight: 600;
    }

    /* Disciplinas */
    .disciplina-container {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        border-left: 6px solid var(--cor-principal);
    }

    .disciplina-header {
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        color: var(--cor-principal);
    }

    .disciplina-stats {
        font-size: 0.95rem;
        color: #5f6368;
        margin-bottom: 1.5rem;
        font-weight: 600;
    }

    .progress-bar-container {
        background: #e8f0fe;
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin-bottom: 1.5rem;
    }

    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #1a73e8, #34a853);
        border-radius: 10px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .conteudo-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        border-left: 4px solid #e8eaed;
        transition: all 0.2s ease;
    }

    .conteudo-card:hover {
        background: #f0f4f8;
        border-left-color: #1a73e8;
    }

    .conteudo-card.estudado {
        background: #e6f4ea;
        border-left-color: #34a853;
        opacity: 0.9;
    }

    .conteudo-text {
        flex: 1;
        font-size: 0.95rem;
        font-weight: 500;
    }

    .conteudo-card.estudado .conteudo-text {
        text-decoration: line-through;
        color: #5f6368;
    }

    /* Seções */
    .section-header {
        font-size: 1.8rem;
        font-weight: 800;
        color: #202124;
        margin: 2.5rem 0 1.5rem 0;
        padding-bottom: 1rem;
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

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 1rem;
        background: #f8f9fa;
        border-radius: 12px 12px 0 0;
        border: 2px solid #e8eaed;
        color: #5f6368;
    }

    .stTabs [aria-selected="true"] {
        background: #1a73e8;
        color: white !important;
        border-color: #1a73e8;
    }

    /* Footer */
    .footer-text {
        text-align: center;
        color: #80868b;
        padding: 2rem 0 1rem;
        font-size: 0.9rem;
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
            max-width: 150px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ================================================================================
# CONFIGURAÇÕES - SPREADSHEET_ID E ID REAIS
# ================================================================================

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'

# URL do logo da Câmara
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

CORES_DISCIPLINAS = {
    'LÍNGUA PORTUGUESA': {
        'principal': '#d33427',
        'secundaria': '#ea4335',
        'emoji': '📖'
    },
    'RLM': {
        'principal': '#1f7c5c',
        'secundaria': '#34a853',
        'emoji': '🧮'
    },
    'REALIDADE DE GOIÁS': {
        'principal': '#0d47a1',
        'secundaria': '#1a73e8',
        'emoji': '🗺️'
    },
    'LEGISLAÇÃO APLICADA': {
        'principal': '#6d28d9',
        'secundaria': '#7c3aed',
        'emoji': '⚖️'
    },
    'CONHECIMENTOS ESPECÍFICOS': {
        'principal': '#f57c00',
        'secundaria': '#fb8500',
        'emoji': '💡'
    }
}

# ================================================================================
# FUNÇÕES DE DATA E CLIMA
# ================================================================================

def obter_data_formatada():
    """Retorna a data dinâmica do dia que está sendo acessado"""
    hoje = datetime.now()

    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    dia = hoje.day
    mes = meses[hoje.month]
    ano = hoje.year

    return f"{dia} de {mes} de {ano}"

@st.cache_data(ttl=600)
def obter_temperatura_goiania():
    """Obtém temperatura atual de Goiânia em tempo real"""
    try:
        response = requests.get(
            'https://api.open-meteo.com/v1/forecast',
            params={
                'latitude': -15.8267,
                'longitude': -48.9626,
                'current': 'temperature_2m,weather_code',
                'temperature_unit': 'celsius',
                'timezone': 'America/Sao_Paulo'
            },
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            temp = data['current']['temperature_2m']
            return round(temp, 1)
        else:
            return "N/A"

    except Exception as e:
        return "N/A"

# ================================================================================
# CONEXÃO GOOGLE SHEETS
# ================================================================================

@st.cache_resource
def conectar_google_sheets():
    """Conecta ao Google Sheets"""
    try:
        if 'gcp_service_account' in st.secrets:
            credentials_dict = st.secrets["gcp_service_account"]
            credentials_dict = dict(credentials_dict)
        else:
            with open('credentials.json', 'r') as f:
                credentials_dict = json.load(f)

        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        return client

    except FileNotFoundError:
        st.error("❌ credentials.json não encontrado!")
        return None
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return None

@st.cache_data(ttl=60)
def carregar_dados_sheets(_client, spreadsheet_id, worksheet_name):
    """Carrega dados"""
    try:
        spreadsheet = _client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()

        if not data:
            return None

        df = pd.DataFrame(data)
        df['Status'] = df['Status'].astype(str).str.upper()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES'])

        return df

    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return None

def atualizar_status_sheets(client, spreadsheet_id, worksheet_name, linha, novo_status):
    """Atualiza status"""
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        col_status = 4
        worksheet.update_cell(linha, col_status, str(novo_status))
        return True
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False

# ================================================================================
# FUNÇÕES DE CÁLCULO
# ================================================================================

def calcular_estatisticas(df, cargo):
    """Calcula estatísticas"""
    df_cargo = df[df['Cargo'] == cargo].copy()

    if len(df_cargo) == 0:
        return None

    total = len(df_cargo)
    estudados = df_cargo['Estudado'].sum()
    faltam = total - estudados
    percentual = (estudados / total * 100) if total > 0 else 0

    stats_disc = df_cargo.groupby('Disciplinas').agg({
        'Estudado': ['sum', 'count']
    }).reset_index()
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

def gerar_insights(stats):
    """Gera insights inteligentes"""
    insights = []

    if stats['percentual'] >= 90:
        insights.append(("🏆", "Você está quase lá! Continue firme!", "#1a73e8"))
    elif stats['percentual'] >= 70:
        insights.append(("💪", "Excelente progresso! Mantenha o ritmo!", "#34a853"))
    elif stats['percentual'] >= 50:
        insights.append(("🚀", "Você já passou da metade! Força!", "#f57c00"))
    elif stats['percentual'] >= 25:
        insights.append(("📚", "Bom começo! Intensifique os estudos", "#d33427"))
    else:
        insights.append(("⚡", "É hora de acelerar! Vamos lá!", "#f57c00"))

    df_disc = stats['por_disciplina']
    disc_critica = df_disc[df_disc['Percentual'] < 40]
    if len(disc_critica) > 0:
        piores = disc_critica.sort_values('Percentual').iloc[0]
        insights.append(("⚠️", f"Foco em {piores['Disciplina']}: apenas {piores['Percentual']:.0f}%", "#d33427"))

    disc_melhor = df_disc.sort_values('Percentual', ascending=False).iloc[0]
    if disc_melhor['Percentual'] == 100:
        insights.append(("⭐", f"Perfeito em {disc_melhor['Disciplina']}!", "#34a853"))

    dias_estimados = max(1, stats['faltam'] // 5) if stats['faltam'] > 0 else 0
    if dias_estimados > 0:
        insights.append(("📅", f"Com 5 conteúdos/dia: {dias_estimados} dias para terminar", "#1a73e8"))

    return insights

def criar_card_metrica(valor, label, icon="📊", cor="#1a73e8"):
    """Cria card de métrica"""
    return f"""
    <div class="metric-card">
        <div style="display: flex; align-items: center; gap: 1.2rem;">
            <div style="font-size: 3.5rem;">{icon}</div>
            <div>
                <div class="metric-value" style="color: {cor};">{valor}</div>
                <div class="metric-label">{label}</div>
            </div>
        </div>
    </div>
    """

def criar_grafico_pizza_disciplina(estudados, total):
    """Cria gráfico de pizza para disciplina"""
    data = pd.DataFrame({
        'Status': ['Estudado', 'Faltando'],
        'Quantidade': [estudados, total - estudados]
    })

    chart = alt.Chart(data).mark_arc(innerRadius=50, stroke=None).encode(
        theta=alt.Theta('Quantidade:Q'),
        color=alt.Color('Status:N', scale=alt.Scale(domain=['Estudado', 'Faltando'], 
                                                      range=['#34a853', '#dadce0']))
    ).properties(width=150, height=150).configure_arc(cornerRadius=0)

    return chart

def criar_grafico_pizza_geral(estudados, faltam):
    """Gráfico de pizza geral"""
    data = pd.DataFrame({
        'Categoria': ['Estudados', 'Faltando'],
        'Quantidade': [estudados, faltam]
    })

    chart = alt.Chart(data).mark_arc(innerRadius=80, cornerRadius=8, stroke=None).encode(
        theta=alt.Theta('Quantidade:Q'),
        color=alt.Color('Categoria:N', scale=alt.Scale(domain=['Estudados', 'Faltando'], 
                                                        range=['#1a73e8', '#dadce0']))
    ).properties(width=300, height=300).configure_arc(cornerRadius=0)

    return chart

def criar_grafico_barras(stats):
    """Gráfico de barras"""
    df = stats['por_disciplina'].sort_values('Percentual', ascending=True)

    chart = alt.Chart(df).mark_bar(cornerRadius=6, stroke=None).encode(
        x=alt.X('Percentual:Q', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y('Disciplina:N', sort='-x'),
        color=alt.Color('Percentual:Q', scale=alt.Scale(scheme='blues'))
    ).properties(width=600, height=300)

    return chart

def criar_tabela_resumo(stats):
    """Tabela resumida"""
    df = stats['por_disciplina'].copy()
    df['Status'] = df.apply(
        lambda row: f"{'🟢' if row['Percentual'] >= 75 else '🟡' if row['Percentual'] >= 50 else '🔴'} {row['Percentual']:.1f}%",
        axis=1
    )
    df['Resumo'] = df.apply(
        lambda row: f"{int(row['Estudados'])}/{int(row['Total'])}",
        axis=1
    )
    return df[['Disciplina', 'Resumo', 'Status']].sort_values('Disciplina')

# ================================================================================
# INTERFACE PRINCIPAL
# ================================================================================

def main():
    """Interface principal"""

    # Obter informações DINÂMICAS
    data_hoje = obter_data_formatada()
    temperatura = obter_temperatura_goiania()

    # Header com logo e informações
    st.markdown(f"""
    <div class="header-container">
        <div class="logo-section">
            <img src="{LOGO_URL}" alt="Câmara Municipal de Goiânia">
        </div>

        <div class="header-content">
            <h1 class="header-title">📚 Dashboard de Estudos</h1>
            <p class="header-subtitle">Acompanhamento Visual com Análises - Concurso Câmara de Goiânia</p>
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

        cargo_selecionado = st.selectbox(
            "Seu cargo:",
            ["Analista Técnico Legislativo", "Agente Administrativo"]
        )

        st.markdown("---")

        if st.button("🔄 Recarregar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        auto_refresh = st.checkbox("Auto-refresh (30s)")

        if auto_refresh:
            time.sleep(30)
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

    # ============================================================================
    # MÉTRICAS
    # ============================================================================

    st.markdown('<div class="section-header">📊 Visão Geral</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(criar_card_metrica(stats['total'], "Total", "📚", "#1a73e8"), unsafe_allow_html=True)

    with col2:
        st.markdown(criar_card_metrica(stats['estudados'], "Estudados", "✅", "#34a853"), unsafe_allow_html=True)

    with col3:
        st.markdown(criar_card_metrica(stats['faltam'], "Faltando", "⏳", "#f57c00"), unsafe_allow_html=True)

    with col4:
        st.markdown(criar_card_metrica(f"{stats['percentual']:.1f}%", "Progresso", "🎯", "#1a73e8"), unsafe_allow_html=True)

    # ============================================================================
    # GRÁFICOS
    # ============================================================================

    st.markdown('<div class="section-header">📈 Análise Visual</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.altair_chart(criar_grafico_pizza_geral(stats['estudados'], stats['faltam']), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.altair_chart(criar_grafico_barras(stats), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================================
    # INSIGHTS
    # ============================================================================

    st.markdown('<div class="section-header">💡 Insights e Análises</div>', unsafe_allow_html=True)

    insights_list = gerar_insights(stats)

    cols = st.columns(min(3, len(insights_list)))
    for idx, (emoji, texto, cor) in enumerate(insights_list):
        with cols[idx % len(cols)]:
            st.markdown(f"""
            <div style="background: {cor}15; border-left: 4px solid {cor}; padding: 1rem; border-radius: 8px;">
                <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">{emoji}</div>
                <div style="color: #333; font-size: 0.95rem; font-weight: 500;">{texto}</div>
            </div>
            """, unsafe_allow_html=True)

    # ============================================================================
    # ANÁLISE DETALHADA
    # ============================================================================

    st.markdown('<div class="section-header">📋 Análise Detalhada</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📈 Visão Geral", "🎯 Metas", "📊 Resumo"])

    with tab1:
        st.markdown("### Progresso por Disciplina")
        df_resumo = criar_tabela_resumo(stats)

        cols = st.columns(len(df_resumo))
        for col, (_, row) in zip(cols, df_resumo.iterrows()):
            with col:
                pct = stats['por_disciplina'][stats['por_disciplina']['Disciplina'] == row['Disciplina']]['Percentual'].values[0]
                cor_card = CORES_DISCIPLINAS.get(row['Disciplina'], {}).get('principal', '#1a73e8')

                st.markdown(f"""
                <div style="background: {cor_card}15; border: 2px solid {cor_card}; border-radius: 12px; padding: 1rem; text-align: center;">
                    <div style="font-weight: 700; color: #333; margin-bottom: 0.5rem;">{row['Disciplina'].split()[0]}</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: {cor_card};">{pct:.0f}%</div>
                    <div style="font-size: 0.85rem; color: #666; margin-top: 0.5rem;">{row['Resumo']}</div>
                </div>
                """, unsafe_allow_html=True)

    with tab2:
        st.markdown("### 🎯 Metas Recomendadas")

        col1, col2, col3 = st.columns(3)

        with col1:
            conteudos_por_dia = st.slider("Conteúdos/dia", 1, 20, 5)

        with col2:
            st.metric("Faltam", stats['faltam'])

        with col3:
            dias_restantes = max(1, stats['faltam'] // conteudos_por_dia) if stats['faltam'] > 0 else 0
            st.metric("Dias até terminar", f"{dias_restantes}")

        st.markdown("---")
        st.markdown("### Disciplinas que Precisam Foco")

        df_disc = stats['por_disciplina'].sort_values('Percentual')

        for _, row in df_disc.head(3).iterrows():
            pct = row['Percentual']
            cor = '#34a853' if pct >= 75 else '#f57c00' if pct >= 50 else '#d33427'

            st.markdown(f"""
            <div style="background: {cor}15; border-left: 4px solid {cor}; padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem;">
                <div style="font-weight: 600; color: #333;">{row['Disciplina']}</div>
                <div style="font-size: 0.9rem; color: #666; margin-top: 0.5rem;">
                    {pct:.1f}% ({int(row['Estudados'])}/{int(row['Total'])})
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab3:
        st.markdown("### 📊 Resumo Estatístico")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Total", stats['total'])
            st.metric("Estudados", stats['estudados'])

        with col2:
            st.metric("Faltando", stats['faltam'])
            st.metric("Taxa (%)", f"{stats['percentual']:.1f}%")

        st.markdown("---")
        st.markdown("### Detalhes por Disciplina")

        df_detalhe = stats['por_disciplina'].copy()
        df_detalhe['Taxa'] = df_detalhe['Percentual'].apply(lambda x: f"{x:.1f}%")
        df_detalhe = df_detalhe[['Disciplina', 'Estudados', 'Faltam', 'Total', 'Taxa']]

        st.dataframe(df_detalhe, use_container_width=True, hide_index=True)

    # ============================================================================
    # DISCIPLINAS
    # ============================================================================

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

        st.markdown(f"""
        <div class="disciplina-container" style="--cor-principal: {cores['principal']};">
            <div class="disciplina-header" style="color: {cores['principal']};">
                {cores['emoji']} {disciplina}
            </div>
            <div class="disciplina-stats">
                ✓ {n_estudados}/{n_total} conteúdos ({pct:.0f}%)
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: {pct}%; background: {cores['principal']};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Layout com gráfico e accordion
        col1, col2 = st.columns([3, 1])

        with col2:
            st.altair_chart(criar_grafico_pizza_disciplina(n_estudados, n_total), use_container_width=True)

        with col1:
            # Accordion com conteúdos
            with st.expander(f"📋 Ver {n_total} conteúdos", expanded=False):
                for idx, row in df_disc.iterrows():
                    col_check, col_text = st.columns([0.08, 0.92])

                    with col_check:
                        checked = st.checkbox(
                            "✓",
                            value=bool(row['Estudado']),
                            key=f"check_{idx}",
                            label_visibility="collapsed"
                        )

                        if checked != bool(row['Estudado']):
                            with st.spinner("💾"):
                                sucesso = atualizar_status_sheets(
                                    client, SPREADSHEET_ID, WORKSHEET_NAME,
                                    int(row['linha_planilha']),
                                    'TRUE' if checked else 'FALSE'
                                )
                                if sucesso:
                                    time.sleep(0.3)
                                    st.cache_data.clear()
                                    st.rerun()

                    with col_text:
                        classe = "estudado" if row['Estudado'] else ""
                        st.markdown(f"""
                        <div class="conteudo-card {classe}">
                            <div class="conteudo-text">{'✓ ' if row['Estudado'] else ''}{row['Conteúdos']}</div>
                        </div>
                        """, unsafe_allow_html=True)

        st.markdown("")

    st.markdown(f'<div class="footer-text">✨ Dashboard Interativo com Análises | Câmara Municipal de Goiânia | {datetime.now().strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
