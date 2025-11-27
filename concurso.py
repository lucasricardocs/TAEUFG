#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard de Estudos - Câmara de Goiânia
VERSÃO FINAL - TEMA CLARO COM LOGO 1.5X MAIOR
COM EFEITO: fagulhas subindo ao fundo da página (integrado)
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
# CSS + JS - TEMA CLARO + FAGULHAS (INTEGRADO)
# ================================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    /* Mantém o background claro do app */
    html, body, [data-testid="stMainBlockContainer"] {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 50%, #f5f7fa 100%);
        color: #1f2937;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ============================
       CONFIG STREAMLIT Z-INDEX
       Garante que o conteúdo do app fique acima do container das fagulhas
       ============================ */
    div[data-testid="stAppViewContainer"],
    div[data-testid="stMainBlockContainer"],
    .stApp {
        position: relative;
        z-index: 1;
    }

    /* ============================
       CONTAINER DAS FAGULHAS (FUND0)
       ============================ */
    #sparkles-container {
        position: fixed;
        inset: 0;
        pointer-events: none;
        overflow: hidden;
        z-index: 0; /* atrás do conteúdo (que tem z-index:1) */
    }

    /* FAISCAS SUBINDO (estilos principais) */
    @keyframes sparkleRise {
        0% {
            transform: translateY(10vh) scale(1);
            opacity: 1;
        }
        70% {
            opacity: 0.9;
        }
        100% {
            transform: translateY(-120vh) scale(0.4);
            opacity: 0;
        }
    }

    .spark {
        position: absolute;
        bottom: -6vh;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: radial-gradient(circle at 35% 30%, rgba(255,255,200,1) 0%, rgba(255,180,60,1) 35%, rgba(255,90,20,0.9) 65%, rgba(0,0,0,0) 100%);
        filter: drop-shadow(0 0 8px rgba(255,160,50,0.75));
        will-change: transform, opacity;
        animation-name: sparkleRise;
        animation-timing-function: cubic-bezier(.12,.8,.18,1);
        animation-fill-mode: forwards;
        pointer-events: none;
        mix-blend-mode: screen;
        opacity: 0.95;
    }

    /* cores alternativas */
    .spark.green {
        background: radial-gradient(circle at 35% 30%, rgba(220,255,220,1) 0%, rgba(120,220,140,1) 35%, rgba(60,180,90,0.9) 65%, rgba(0,0,0,0) 100%);
        filter: drop-shadow(0 0 8px rgba(60,180,90,0.55));
    }

    .spark.orange {
        background: radial-gradient(circle at 35% 30%, rgba(255,230,200,1) 0%, rgba(255,160,90,1) 35%, rgba(255,100,30,0.9) 65%, rgba(0,0,0,0) 100%);
        filter: drop-shadow(0 0 8px rgba(255,120,40,0.55));
    }

    /* Pequena responsividade para tamanhos menores */
    @media (max-width: 600px) {
        .spark { width: 4px; height: 4px; }
    }

    /* ============================
       SEU CSS ORIGINAL (mantido)
       ============================ */

    /* slideIn (usado em conteúdos) */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-10px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .sparkle { /* mantém compatibilidade caso algum elemento use .sparkle */
        display: none;
    }

    .header-container {
        display: flex;
        align-items: flex-start;
        gap: 2rem;
        background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(26, 115, 232, 0.2);
        position: relative;
        z-index: 2;
    }

    .header-logo {
        flex-shrink: 0;
    }

    .header-logo img {
        max-width: 225px;
        height: auto;
        filter: drop-shadow(0 2px 8px rgba(0,0,0,0.2));
    }

    .header-content {
        flex: 1;
        color: white;
    }

    .header-content h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -1px;
    }

    .header-content p {
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
        opacity: 0.9;
        font-weight: 400;
    }

    .header-info {
        position: absolute;
        top: 1.5rem;
        right: 2rem;
        display: flex;
        gap: 2rem;
        color: white;
        font-size: 0.85rem;
    }

    .info-item {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }

    .info-label {
        font-size: 0.7rem;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    .info-value {
        font-size: 0.9rem;
        font-weight: 600;
    }

    .section-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #1f2937;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.8rem;
        border-bottom: 3px solid #1a73e8;
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }

    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        cursor: pointer;
    }

    .metric-card:hover {
        background: #f8f9fa;
        border-color: #1a73e8;
        transform: translateY(-6px);
        box-shadow: 0 12px 24px rgba(26, 115, 232, 0.15);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #34a853;
        margin: 0.5rem 0;
        line-height: 1;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    .disc-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-left: 4px solid var(--cor);
        padding: 1.2rem;
        border-radius: 10px;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    .disc-card:hover {
        background: #f8f9fa;
        transform: translateX(4px);
        border-color: var(--cor);
        box-shadow: 0 8px 16px rgba(26, 115, 232, 0.12);
    }

    .disc-name {
        flex: 1;
        color: var(--cor);
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: -0.5px;
    }

    .disc-stats {
        font-size: 0.8rem;
        color: #6b7280;
        font-weight: 500;
    }

    .progress {
        flex: 1;
        background: #e5e7eb;
        height: 5px;
        border-radius: 5px;
        overflow: hidden;
        margin: 0 1rem;
    }

    .progress-bar {
        height: 100%;
        background: var(--cor);
        border-radius: 5px;
        transition: width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
        box-shadow: 0 0 10px rgba(26, 115, 232, 0.3);
    }

    .pct {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--cor);
        min-width: 45px;
        text-align: right;
    }

    .conteudo-item {
        background: #f9fafb;
        border-left: 3px solid #e5e7eb;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 6px;
        font-size: 0.95rem;
        transition: all 0.2s ease;
        animation: slideIn 0.3s ease-out;
        color: #374151;
    }

    .conteudo-item:hover {
        background: #f3f4f6;
        border-left-color: #1a73e8;
        transform: translateX(4px);
    }

    .conteudo-item.done {
        opacity: 0.6;
        text-decoration: line-through;
        color: #6b7280;
        border-left-color: #34a853;
        background: #ecf5ea;
    }

    .chart-container {
        background: white;
        border: 1px solid #e5e7eb;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    .chart-container:hover {
        background: #f8f9fa;
        border-color: #d1d5db;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .pizza-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.8rem;
        text-align: center;
        letter-spacing: -0.5px;
    }

    .footer {
        text-align: center;
        color: #6b7280;
        padding: 2rem 0;
        margin-top: 3rem;
        border-top: 1px solid #e5e7eb;
        font-size: 0.85rem;
        font-weight: 500;
    }

    @media (max-width: 1024px) {
        .header-info {
            position: relative;
            top: auto;
            right: auto;
            gap: 1rem;
        }

        .header-container {
            flex-direction: column;
        }
    }

    @media (max-width: 768px) {
        .header-content h1 {
            font-size: 1.8rem;
        }

        .header-logo img {
            max-width: 180px;
        }

        .metric-card {
            padding: 1rem;
        }

        .metric-value {
            font-size: 2rem;
        }

        .section-title {
            font-size: 1.2rem;
        }

        .header-info {
            gap: 1rem;
            flex-wrap: wrap;
        }
    }
</style>

<!-- container das fagulhas -->
<div id="sparkles-container" aria-hidden="true"></div>

<script>
(function() {
    // cria fagulha com variações
    function createSpark() {
        const container = document.getElementById('sparkles-container');
        if (!container) return;

        const sp = document.createElement('div');
        sp.className = 'spark';

        // posição horizontal aleatória (em px)
        const left = Math.random() * window.innerWidth;
        sp.style.left = left + 'px';

        // variação de tamanho
        const size = (Math.random() * 6) + 3; // 3px a 9px
        sp.style.width = size + 'px';
        sp.style.height = size + 'px';

        // drift lateral pequeno
        const drift = (Math.random() * 240) - 120; // -120px .. +120px
        sp.style.setProperty('transform-origin', 'center bottom');
        // duração aleatória
        const duration = 2.6 + Math.random() * 2.2; // 2.6s a 4.8s
        sp.style.animationDuration = duration + 's';

        // escolher cor aleatória
        const colorPick = Math.random();
        if (colorPick < 0.12) sp.classList.add('green');
        else if (colorPick < 0.28) sp.classList.add('orange');

        // aplicar deslocamento lateral via keyframe dinamicamente (usarei CSS var hack)
        // Para compatibilidade simples, aplico um translateX por style no final (via setTimeout)
        container.appendChild(sp);

        // aplicar um pequeno translateX gradual via transition (ajuste visual)
        sp.style.transition = `transform ${duration}s linear, opacity ${duration}s linear`;
        requestAnimationFrame(() => {
            sp.style.transform = `translateY(-125vh) translateX(${drift}px) scale(0.45)`;
            sp.style.opacity = '0';
        });

        // remover ao final
        setTimeout(() => {
            sp.remove();
        }, (duration + 0.1) * 1000);
    }

    // emissor: cria várias fagulhas periodicamente
    function startEmitter() {
        // cria um lote inicial rápido pra encher o fundo
        for (let i = 0; i < 12; i++) {
            setTimeout(createSpark, i * 120);
        }
        // depois cria lotes periódicos
        return setInterval(() => {
            for (let i = 0; i < 6; i++) {
                setTimeout(createSpark, i * 90);
            }
        }, 700);
    }

    // iniciar quando a janela carregar (funciona melhor no Streamlit)
    window.addEventListener('load', () => {
        // pequena proteção: não inicializar duas vezes
        if (!window.__sparkles_started) {
            window.__sparkles_started = true;
            window.__sparkles_interval = startEmitter();
            // pause when tab hidden to economizar CPU
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    clearInterval(window.__sparkles_interval);
                    window.__sparkles_interval = null;
                } else if (!window.__sparkles_interval) {
                    window.__sparkles_interval = startEmitter();
                }
            });
        }
    });
})();
</script>
""", unsafe_allow_html=True)

# ================================================================================
# CONFIGURAÇÕES
# ================================================================================

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

CORES = {
    'LÍNGUA PORTUGUESA': '#d33427',
    'RLM': '#1f7c5c',
    'REALIDADE DE GOIÁS': '#0d47a1',
    'LEGISLAÇÃO APLICADA': '#6d28d9',
    'CONHECIMENTOS ESPECÍFICOS': '#f57c00'
}

EMOJIS = {
    'LÍNGUA PORTUGUESA': '📖',
    'RLM': '🧮',
    'REALIDADE DE GOIÁS': '🗺️',
    'LEGISLAÇÃO APLICADA': '⚖️',
    'CONHECIMENTOS ESPECÍFICOS': '💡'
}

# ================================================================================
# FUNÇÕES AUXILIARES
# ================================================================================

def obter_data():
    """Retorna data formatada em português"""
    hoje = datetime.now()
    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    return f"{hoje.day} de {meses[hoje.month]} de {hoje.year}"

@st.cache_data(ttl=600)
def obter_temp():
    """Obtém temperatura de Goiânia em tempo real"""
    try:
        r = requests.get(
            'https://api.open-meteo.com/v1/forecast',
            params={
                'latitude': -15.8267,
                'longitude': -48.9626,
                'current': 'temperature_2m',
                'temperature_unit': 'celsius',
                'timezone': 'America/Sao_Paulo'
            },
            timeout=5
        )
        if r.status_code == 200:
            return round(r.json()['current']['temperature_2m'], 1)
    except Exception:
        pass
    return "N/A"

def conectar():
    """Conecta ao Google Sheets"""
    try:
        if 'gcp_service_account' in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
        else:
            with open('credentials.json', 'r') as f:
                creds = json.load(f)
        c = Credentials.from_service_account_info(
            creds,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        return gspread.authorize(c)
    except Exception as e:
        st.error(f"❌ Erro ao conectar: {e}")
        return None

@st.cache_data(ttl=60)
def carregar_dados(_client):
    """Carrega dados da planilha - com _ no client para evitar hash"""
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        df = pd.DataFrame(ws.get_all_records())
        df['Status'] = df['Status'].astype(str).str.upper()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES'])
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return None

def atualizar(client, linha, novo_status):
    """Atualiza o status no Google Sheets"""
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        ws.update_cell(linha, 4, str(novo_status))
        return True
    except Exception as e:
        st.error(f"❌ Erro ao atualizar: {e}")
        return False

def criar_pizza_chart(estudados, total):
    """Cria gráfico de pizza sem legenda"""
    data = pd.DataFrame({
        'Status': ['Estudado', 'Faltando'],
        'Quantidade': [estudados, total - estudados]
    })

    chart = alt.Chart(data).mark_arc(
        innerRadius=50,
        stroke=None,
        cornerRadius=8
    ).encode(
        theta=alt.Theta('Quantidade:Q'),
        color=alt.Color(
            'Status:N',
            scale=alt.Scale(
                domain=['Estudado', 'Faltando'],
                range=['#34a853', '#ef5350']
            )
        ),
        tooltip=[]
    ).properties(width=200, height=200)

    return chart

def calcular_stats(df_cargo):
    """Calcula estatísticas do cargo"""
    total = len(df_cargo)
    estudados = df_cargo['Estudado'].sum()
    faltam = total - estudados
    pct = (estudados / total * 100) if total > 0 else 0

    stats_disc = df_cargo.groupby('Disciplinas').agg({
        'Estudado': ['sum', 'count']
    }).reset_index()
    stats_disc.columns = ['Disciplina', 'Estudados', 'Total']
    stats_disc['Percentual'] = (stats_disc['Estudados'] / stats_disc['Total'] * 100).round(1)

    return {
        'total': total,
        'estudados': estudados,
        'faltam': faltam,
        'percentual': pct,
        'por_disc': stats_disc
    }

# ================================================================================
# INTERFACE PRINCIPAL
# ================================================================================

def main():
    """Função principal"""
    data = obter_data()
    temp = obter_temp()

    # Header
    st.markdown(f"""
    <div style="position: relative; margin-bottom: 2rem;">
        <div class="header-container">
            <div class="header-logo">
                <img src="{LOGO_URL}" alt="Logo Câmara de Goiânia">
            </div>
            <div class="header-content">
                <h1>📚 Dashboard de Estudos</h1>
                <p>Acompanhamento - Concurso Câmara de Goiânia</p>
            </div>
        </div>
        <div class="header-info">
            <div class="info-item">
                <span class="info-label">📍 Local</span>
                <span class="info-value">Goiânia - GO</span>
            </div>
            <div class="info-item">
                <span class="info-label">📅 Data</span>
                <span class="info-value">{data}</span>
            </div>
            <div class="info-item">
                <span class="info-label">🌡️ Temp</span>
                <span class="info-value">{temp}°C</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        cargo = st.selectbox(
            "Seu Cargo:",
            ["Analista Técnico Legislativo", "Agente Administrativo"],
            key="cargo_select"
        )
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Recarregar", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("❌ Limpar", use_container_width=True):
                st.session_state.clear()
                st.rerun()

    # Conectar
    client = conectar()
    if client is None:
        st.stop()

    # Carregar dados
    with st.spinner("📥 Carregando dados..."):
        df = carregar_dados(client)

    if df is None or len(df) == 0:
        st.error("❌ Nenhum dado encontrado na planilha")
        st.stop()

    # Filtrar por cargo
    df_cargo = df[df['Cargo'] == cargo].copy()
    if len(df_cargo) == 0:
        st.warning(f"⚠️ Sem dados para: {cargo}")
        st.stop()

    # Calcular stats
    stats = calcular_stats(df_cargo)
    df_cargo['linha'] = df_cargo.index + 2

    # Métricas
    st.markdown('<div class="section-title">📊 Visão Geral</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""<div class="metric-card">
            <div style="font-size: 2.2rem;">📚</div>
            <div class="metric-value">{stats['total']}</div>
            <div class="metric-label">Total</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div class="metric-card">
            <div style="font-size: 2.2rem;">✅</div>
            <div class="metric-value">{stats['estudados']}</div>
            <div class="metric-label">Estudados</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""<div class="metric-card">
            <div style="font-size: 2.2rem;">⏳</div>
            <div class="metric-value">{stats['faltam']}</div>
            <div class="metric-label">Faltando</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""<div class="metric-card">
            <div style="font-size: 2.2rem;">🎯</div>
            <div class="metric-value">{stats['percentual']:.0f}%</div>
            <div class="metric-label">Progresso</div>
        </div>""", unsafe_allow_html=True)

    # Análise Visual
    st.markdown('<div class="section-title">📈 Análise Visual</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        data_pizza = pd.DataFrame({
            'Status': ['Estudado', 'Faltando'],
            'Quantidade': [stats['estudados'], stats['faltam']]
        })
        chart = alt.Chart(data_pizza).mark_arc(
            innerRadius=60,
            stroke=None,
            cornerRadius=8
        ).encode(
            theta=alt.Theta('Quantidade:Q'),
            color=alt.Color(
                'Status:N',
                scale=alt.Scale(domain=['Estudado', 'Faltando'],
                                range=['#34a853', '#ef5350'])
            ),
            tooltip=[]
        ).properties(width=300, height=300)
        st.altair_chart(chart, width='stretch')
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        stats_disc_sorted = stats['por_disc'].sort_values('Percentual', ascending=True)
        chart = alt.Chart(stats_disc_sorted).mark_bar(
            cornerRadius=6,
            stroke=None
        ).encode(
            x=alt.X('Percentual:Q', scale=alt.Scale(domain=[0, 100])),
            y=alt.Y('Disciplina:N', sort='-x'),
            color=alt.Color('Percentual:Q', scale=alt.Scale(scheme='greens')),
            tooltip=[]
        ).properties(width=500, height=300)
        st.altair_chart(chart, width='stretch')
        st.markdown('</div>', unsafe_allow_html=True)

    # Pizzas por Disciplina
    st.markdown('<div class="section-title">🥧 Pizzas por Disciplina</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    for idx, (_, row) in enumerate(stats['por_disc'].iterrows()):
        with cols[idx % 3]:
            cor = CORES.get(row['Disciplina'], '#1a73e8')

            st.markdown(f"""
            <div class="pizza-title" style="color: {cor};">
                {row['Disciplina']}
            </div>
            """, unsafe_allow_html=True)

            chart = criar_pizza_chart(int(row['Estudados']), int(row['Total']))
            st.altair_chart(chart, width='stretch')

            st.markdown(f"""
            <div style="text-align: center; color: {cor}; font-weight: 700; font-size: 1.4rem; margin-top: -0.5rem;">
                {row['Percentual']:.0f}%
            </div>
            """, unsafe_allow_html=True)

    # Conteúdos por Disciplina
    st.markdown('<div class="section-title">📚 Conteúdos por Disciplina</div>', unsafe_allow_html=True)

    disciplinas = sorted(df_cargo['Disciplinas'].unique().tolist())
    filtro = st.selectbox("Filtrar por Disciplina:", ["Todas"] + disciplinas, key="filtro_disc")

    if filtro != "Todas":
        df_cargo = df_cargo[df_cargo['Disciplinas'] == filtro]

    for disc in sorted(df_cargo['Disciplinas'].unique()):
        df_disc = df_cargo[df_cargo['Disciplinas'] == disc].copy()
        n_est = df_disc['Estudado'].sum()
        n_tot = len(df_disc)
        p = (n_est / n_tot * 100) if n_tot > 0 else 0
        cor = CORES.get(disc, '#1a73e8')
        emoji = EMOJIS.get(disc, '📖')

        st.markdown(f"""
        <div class="disc-card" style="--cor: {cor};">
            <div class="disc-name">{emoji} {disc}</div>
            <div class="progress">
                <div class="progress-bar" style="width: {p}%; background: {cor};"></div>
            </div>
            <div class="pct">{p:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"📋 Ver {n_tot} conteúdos ({n_est} estudados)"):
            for idx, row in df_disc.iterrows():
                col1, col2 = st.columns([0.05, 0.95])

                with col1:
                    check = st.checkbox(
                        "✓",
                        value=bool(row['Estudado']),
                        key=f"ch_{idx}",
                        label_visibility="collapsed"
                    )

                    if check != bool(row['Estudado']):
                        with st.spinner("💾 Salvando..."):
                            if atualizar(client, int(row['linha']), 'TRUE' if check else 'FALSE'):
                                time.sleep(0.3)
                                st.rerun()

                with col2:
                    classe = "done" if row['Estudado'] else ""
                    st.markdown(f"""<div class="conteudo-item {classe}">
                        {'✓ ' if row['Estudado'] else ''}{row['Conteúdos']}
                    </div>""", unsafe_allow_html=True)

    # Footer
    st.markdown(f'<div class="footer">✨ Dashboard Interativo | Câmara Municipal de Goiânia | Atualizado em {datetime.now().strftime("%H:%M:%S")}</div>', 
               unsafe_allow_html=True)

if __name__ == "__main__":
    main()
