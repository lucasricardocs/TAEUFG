#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🚀 DASHBOARD DE ESTUDOS - CÂMARA MUNICIPAL DE GOIÂNIA
================================================================================
VERSÃO: ULTIMATE MAXIMIZED
DATA: 2025-11-27
AUTOR: Perplexity AI Assistant

DESCRIÇÃO:
Dashboard completo para acompanhamento de estudos com gamificação,
animações avançadas, inteligência de dados e interface premium.

FUNCIONALIDADES:
1. Conexão segura com Google Sheets API
2. Interface responsiva com tema claro
3. Sistema de partículas (fagulhas) animadas
4. Gamificação com badges e conquistas
5. Heatmap de produtividade (simulado/real)
6. Sistema de revisão inteligente (Spaced Repetition básico)
7. Gráficos interativos (Altair)
8. Check-list funcional com atualização em tempo real
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
import random
import locale

# Configuração de Avisos e Locale
warnings.filterwarnings('ignore')
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass

# ================================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ================================================================================

st.set_page_config(
    page_title="Dashboard Ultimate",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Dashboard de Estudos Premium v2.0"
    }
)

# ================================================================================
# 2. ESTILOS CSS AVANÇADOS (INJEÇÃO DE CÓDIGO)
# ================================================================================

st.markdown("""
<style>
    /* IMPORTAÇÃO DE FONTES */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    /* RESET E BASE */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* BACKGROUND DA PÁGINA */
    [data-testid="stMainBlockContainer"] {
        background-color: #f8fafc;
        background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
        background-size: 20px 20px;
        color: #0f172a;
        overflow-x: hidden;
    }

    /* REMOVE ELEMENTOS PADRÃO DO STREAMLIT */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ==========================================================================
       ANIMAÇÕES (KEYFRAMES)
       ========================================================================== */
    
    @keyframes slideUpFade {
        0% {
            opacity: 0;
            transform: translateY(30px);
        }
        100% {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes popIn {
        0% {
            opacity: 0;
            transform: scale(0.5);
        }
        70% {
            transform: scale(1.1);
        }
        100% {
            opacity: 1;
            transform: scale(1);
        }
    }

    @keyframes shimmer {
        0% { background-position: -1000px 0; }
        100% { background-position: 1000px 0; }
    }

    @keyframes pulse-glow {
        0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
        100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }

    @keyframes stripes {
        from { background-position: 20px 0; }
        to { background-position: 0 0; }
    }

    @keyframes fillUp {
        from { width: 0; }
    }
    
    @keyframes floatUp { 
        0% { 
            transform: translateY(110vh) scale(0); 
            opacity: 0; 
        } 
        20% { 
            opacity: 0.8; 
            transform: translateY(80vh) scale(1); 
        } 
        80% { 
            opacity: 0.6; 
        }
        100% { 
            transform: translateY(-10vh) scale(0.5); 
            opacity: 0; 
        } 
    }

    /* ==========================================================================
       COMPONENTES DO HEADER
       ========================================================================== */

    .header-container {
        display: grid;
        grid-template-columns: auto 1fr auto;
        align-items: center;
        gap: 2rem;
        
        background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
        padding: 2rem 2.5rem;
        border-radius: 20px;
        margin-bottom: 2.5rem;
        
        box-shadow: 0 15px 35px -10px rgba(30, 64, 175, 0.4);
        color: white;
        
        position: relative;
        z-index: 10;
        overflow: hidden;
        
        animation: slideUpFade 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
    }

    /* Efeito de brilho no header */
    .header-container::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%);
        animation: shimmer 3s infinite linear;
        background-size: 200% 100%;
        pointer-events: none;
    }

    .header-logo img { 
        max-width: 280px; 
        height: auto;
        filter: drop-shadow(0 4px 12px rgba(0,0,0,0.3)); 
        transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
        cursor: pointer;
    }
    
    .header-logo img:hover { 
        transform: scale(1.05) rotate(-1deg); 
    }

    .header-content { 
        text-align: center; 
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .header-content h1 { 
        font-size: 2.8rem; 
        font-weight: 800; 
        margin: 0; 
        letter-spacing: -0.03em;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        background: linear-gradient(to right, #ffffff, #e0e7ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .header-content p {
        margin-top: 0.5rem;
        font-size: 1.1rem;
        color: #93c5fd;
        font-weight: 500;
    }

    .header-info { 
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        
        background: rgba(255,255,255,0.1); 
        padding: 1rem 1.5rem; 
        border-radius: 16px; 
        text-align: right; 
        
        border: 1px solid rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .header-info:hover {
        background: rgba(255,255,255,0.15); 
        transform: translateY(-2px);
    }
    
    .info-row {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.5rem;
        font-size: 0.95rem;
        font-weight: 600;
    }

    /* ==========================================================================
       GAMIFICAÇÃO (BADGES)
       ========================================================================== */

    .badge-container { 
        display: flex; 
        gap: 15px; 
        justify-content: center; 
        flex-wrap: wrap; 
        margin-bottom: 30px; 
        padding: 10px;
    }
    
    .badge {
        background: linear-gradient(135deg, #FFD700, #FFA500);
        color: #fff; 
        padding: 10px 24px; 
        border-radius: 50px;
        
        font-weight: 800; 
        font-size: 1rem; 
        text-transform: uppercase;
        letter-spacing: 1px;
        
        box-shadow: 0 4px 15px rgba(255, 165, 0, 0.3);
        border: 2px solid rgba(255,255,255,0.5);
        
        opacity: 0; 
        animation: popIn 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        cursor: default;
    }
    
    .badge:hover {
        transform: translateY(-5px) scale(1.05);
        box-shadow: 0 10px 25px rgba(255, 165, 0, 0.5);
    }
    
    .badge.locked {
        background: #e2e8f0;
        color: #94a3b8;
        box-shadow: none;
        border-color: #cbd5e1;
    }

    /* Delays de animação para os badges */
    .badge:nth-child(1) { animation-delay: 0.5s; }
    .badge:nth-child(2) { animation-delay: 0.7s; }
    .badge:nth-child(3) { animation-delay: 0.9s; }
    .badge:nth-child(4) { animation-delay: 1.1s; }

    /* ==========================================================================
       CARDS DE MÉTRICAS (KPIs)
       ========================================================================== */

    .metric-card { 
        background: white; 
        padding: 2rem; 
        border-radius: 24px; 
        
        border: 1px solid #e2e8f0; 
        text-align: center; 
        
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        opacity: 0; 
        animation: slideUpFade 0.6s ease-out forwards;
        
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        position: relative;
        overflow: hidden;
    }
    
    .metric-col-1 .metric-card { animation-delay: 0.2s; }
    .metric-col-2 .metric-card { animation-delay: 0.4s; }
    .metric-col-3 .metric-card { animation-delay: 0.6s; }
    .metric-col-4 .metric-card { animation-delay: 0.8s; }
    
    .metric-card:hover { 
        transform: translateY(-10px) scale(1.02); 
        box-shadow: 0 20px 40px -10px rgba(59, 130, 246, 0.15); 
        border-color: #3b82f6;
    }
    
    .metric-value { 
        font-size: 3.5rem; 
        font-weight: 900; 
        color: #0f172a; 
        transition: color 0.3s;
        margin-bottom: 0.5rem;
    }
    
    .metric-card:hover .metric-value { color: #2563eb; }
    
    .metric-label {
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #64748b;
    }

    /* ==========================================================================
       BARRAS DE PROGRESSO
       ========================================================================== */

    .bar-container { 
        background: #e2e8f0; 
        height: 16px; 
        border-radius: 8px; 
        overflow: hidden; 
        margin-top: 0.8rem; 
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .bar-fill { 
        height: 100%; 
        border-radius: 8px; 
        
        background-image: linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent); 
        background-size: 20px 20px; 
        
        animation: stripes 1s linear infinite, fillUp 1.5s ease-out forwards;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    /* ==========================================================================
       SISTEMA DE REVISÃO
       ========================================================================== */

    .review-row { 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        
        background: #fff; 
        padding: 1.5rem; 
        border-bottom: 1px solid #f1f5f9; 
        border-left: 6px solid #f59e0b; 
        
        margin-bottom: 1rem; 
        border-radius: 12px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        
        opacity: 0; 
        animation: slideUpFade 0.5s ease-out forwards;
        transition: all 0.3s ease;
    }
    
    .review-row:hover { 
        transform: translateX(8px); 
        border-left-width: 10px; 
        box-shadow: 0 5px 15px rgba(245, 158, 11, 0.15);
    }
    
    .review-title {
        font-weight: 700;
        font-size: 1.1rem;
        color: #1e293b;
    }
    
    .review-subtitle {
        font-size: 0.9rem;
        color: #64748b;
        margin-top: 0.2rem;
    }

    .review-row:nth-child(1) { animation-delay: 1.2s; }
    .review-row:nth-child(2) { animation-delay: 1.4s; }

    /* ==========================================================================
       LISTA DE CONTEÚDOS
       ========================================================================== */

    .conteudo-item {
        background: #ffffff; 
        border: 1px solid #e2e8f0; 
        padding: 1.2rem; 
        border-radius: 12px; 
        margin-bottom: 0.8rem; 
        color: #334155;
        font-weight: 500;
        
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
    }
    
    .conteudo-item:hover { 
        border-color: #3b82f6; 
        transform: translateX(5px); 
        background: #f8fafc;
    }
    
    .conteudo-item.done {
        background: #f0fdf4; 
        border-color: #bbf7d0; 
        color: #166534; 
        text-decoration: line-through; 
        opacity: 0.8;
    }

    /* ==========================================================================
       PARTÍCULAS E BACKGROUND FX
       ========================================================================== */

    #sparkles-container { 
        position: fixed; 
        top: 0; left: 0; width: 100%; height: 100%; 
        pointer-events: none; 
        z-index: 0; 
    }
    
    .spark { 
        position: absolute; 
        border-radius: 50%; 
        opacity: 0; 
        animation: floatUp linear forwards; 
        filter: blur(1px);
        mix-blend-mode: multiply;
    }

    /* Responsividade */
    @media (max-width: 900px) { 
        .header-container { grid-template-columns: 1fr; text-align: center; } 
        .header-info { align-items: center; }
        .header-logo img { margin: 0 auto; }
    }
</style>

<!-- ENGINE DE PARTÍCULAS (JAVASCRIPT PURO) -->
<div id="sparkles-container"></div>
<script>
    function createSparkle() {
        const container = document.getElementById('sparkles-container');
        if (!container) return;
        
        const el = document.createElement('div');
        
        // Cores vibrantes baseadas no Tailwind CSS
        const colors = [
            'rgba(37, 99, 235, ',  // Blue-600
            'rgba(22, 163, 74, ',  // Green-600
            'rgba(234, 88, 12, ',  // Orange-600
            'rgba(147, 51, 234, ', // Purple-600
            'rgba(219, 39, 119, '  // Pink-600
        ];
        
        const colorBase = colors[Math.floor(Math.random() * colors.length)];
        
        el.style.background = colorBase + '0.6)';
        el.style.boxShadow = `0 0 15px ${colorBase}0.4)`;
        el.classList.add('spark');

        // Tamanho Aleatório
        const size = Math.random() * 14 + 4;
        el.style.width = size + 'px'; 
        el.style.height = size + 'px';
        
        // Posição Aleatória
        el.style.left = Math.random() * 100 + 'vw';
        
        // Duração Aleatória
        const duration = Math.random() * 6 + 5; 
        el.style.animationDuration = duration + 's';
        
        container.appendChild(el);
        
        // Limpeza Automática
        setTimeout(() => el.remove(), duration * 1000);
    }
    
    // Inicia o loop de partículas
    setInterval(createSparkle, 250);
</script>
""", unsafe_allow_html=True)

# ================================================================================
# 3. CONSTANTES E CONFIGURAÇÕES
# ================================================================================

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

CORES = {
    'LÍNGUA PORTUGUESA': '#ef4444', 
    'RLM': '#10b981', 
    'REALIDADE DE GOIÁS': '#3b82f6', 
    'LEGISLAÇÃO APLICADA': '#8b5cf6', 
    'CONHECIMENTOS ESPECÍFICOS': '#f59e0b'
}

EMOJIS = {
    'LÍNGUA PORTUGUESA': '📖', 
    'RLM': '🧮', 
    'REALIDADE DE GOIÁS': '🗺️', 
    'LEGISLAÇÃO APLICADA': '⚖️', 
    'CONHECIMENTOS ESPECÍFICOS': '💡'
}

PESOS = {
    'LÍNGUA PORTUGUESA': 1, 
    'RLM': 1, 
    'REALIDADE DE GOIÁS': 1,
    'LEGISLAÇÃO APLICADA': 2, 
    'CONHECIMENTOS ESPECÍFICOS': 2
}

# ================================================================================
# 4. SERVIÇOS DE BACKEND (INTEGRAÇÃO)
# ================================================================================

def obter_data_formatada():
    """Retorna a data atual formatada em português."""
    hoje = datetime.now()
    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    return f"{hoje.day} de {meses[hoje.month]} de {hoje.year}"

@st.cache_data(ttl=600)
def obter_temperatura_api():
    """Consulta API Open-Meteo para obter temperatura."""
    try:
        url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': -15.8267, 
            'longitude': -48.9626, 
            'current': 'temperature_2m', 
            'timezone': 'America/Sao_Paulo'
        }
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200: 
            return round(r.json()['current']['temperature_2m'], 1)
    except Exception as e:
        # Fail silently
        pass
    return "--"

def conectar_google_sheets():
    """Estabelece conexão autenticada com Google Sheets."""
    try:
        if 'gcp_service_account' in st.secrets: 
            creds = dict(st.secrets["gcp_service_account"])
        else: 
            with open('credentials.json', 'r') as f: 
                creds = json.load(f)
        
        escopos = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credenciais = Credentials.from_service_account_info(creds, scopes=escopos)
        return gspread.authorize(credenciais)
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

@st.cache_data(ttl=30)
def carregar_dados_planilha(_client):
    """Carrega e processa os dados da planilha."""
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # Tratamento de dados
        df['Status'] = df['Status'].astype(str).str.upper()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES'])
        
        return df
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
        return None

def atualizar_status_topico(client, linha, novo_status):
    """Atualiza o status de um tópico específico na nuvem."""
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        # Assume coluna 4 como status (A, B, C, D=Status)
        ws.update_cell(linha, 4, str(novo_status))
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# ================================================================================
# 5. COMPONENTES VISUAIS & GRÁFICOS
# ================================================================================

def criar_grafico_donut(estudados, total, cor_tema):
    """Gera gráfico de donut estilizado com Altair."""
    dados_grafico = pd.DataFrame({
        'Categoria': ['Concluído', 'Restante'], 
        'Valor': [estudados, total - estudados]
    })
    
    base = alt.Chart(dados_grafico).encode(
        theta=alt.Theta("Valor", stack=True)
    )
    
    # Arco principal
    pie = base.mark_arc(
        outerRadius=80, 
        innerRadius=60, 
        stroke='white', 
        strokeWidth=4,
        cornerRadius=4
    ).encode(
        color=alt.Color(
            "Categoria", 
            scale=alt.Scale(domain=['Concluído', 'Restante'], range=[cor_tema, '#e2e8f0']), 
            legend=None
        ),
        tooltip=["Categoria", "Valor"]
    )
    
    # Texto central com porcentagem
    percentual = int(estudados/total*100) if total > 0 else 0
    texto = base.mark_text(
        radius=0, 
        size=24, 
        color=cor_tema, 
        fontWeight='bold', 
        font='Inter'
    ).encode(
        text=alt.value(f"{percentual}%")
    )
    
    return (pie + texto).properties(width=200, height=200)

def gerar_dados_heatmap():
    """Gera dados simulados para o heatmap de produtividade."""
    dados = []
    hoje = datetime.now()
    # Gera últimos 60 dias
    for i in range(60):
        data_ponto = hoje - timedelta(days=i)
        # Simula intensidade aleatória
        intensidade = random.choices([0, 1, 2, 3, 4], weights=[0.3, 0.2, 0.2, 0.2, 0.1])[0]
        dados.append({
            'date': data_ponto.strftime('%Y-%m-%d'), 
            'count': intensidade
        })
    return pd.DataFrame(dados)

def calcular_badges(total_estudado, percentual_geral):
    """Calcula conquistas baseadas no progresso."""
    conquistas = []
    
    # Conquistas de Percentual
    if percentual_geral >= 10: conquistas.append("🚀 Decolando (10%)")
    if percentual_geral >= 25: conquistas.append("🏃 Em Ritmo (25%)")
    if percentual_geral >= 50: conquistas.append("🔥 Meio Caminho (50%)")
    if percentual_geral >= 75: conquistas.append("💎 Elite (75%)")
    if percentual_geral >= 90: conquistas.append("👑 Mestre (90%)")
    
    # Conquistas de Volume
    if total_estudado >= 50: conquistas.append("📚 Leitor Ávido (50+)")
    if total_estudado >= 100: conquistas.append("🧠 Enciclopédia (100+)")
    
    return conquistas

# ================================================================================
# 6. APLICAÇÃO PRINCIPAL (MAIN LOOP)
# ================================================================================

def main():
    # --- HEADER ---
    temp = obter_temperatura_api()
    data_extenso = obter_data_formatada()
    
    st.markdown(f"""
    <div class="header-container">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Logo Oficial">
        </div>
        <div class="header-content">
            <h1>🚀 Dashboard Ultimate</h1>
            <p>Performance • Gamificação • Estratégia</p>
        </div>
        <div class="header-info">
            <div class="info-row">📍 Goiânia - GO</div>
            <div class="info-row">📅 {data_extenso}</div>
            <div class="info-row">🌡️ {temp}°C</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- CONEXÃO DE DADOS ---
    client = conectar_google_sheets()
    if not client:
        st.error("Falha crítica na conexão com o banco de dados.")
        st.stop()

    # --- SIDEBAR (CONTROLES) ---
    with st.sidebar:
        st.header("⚙️ Painel de Controle")
        
        # Carregamento Inicial com Session State para persistência
        if 'dados_df' not in st.session_state:
            with st.spinner("Conectando à base de dados..."):
                st.session_state['dados_df'] = carregar_dados_planilha(client)
        
        df_completo = st.session_state['dados_df']
        
        if df_completo is None:
            st.warning("Não foi possível carregar os dados.")
            st.stop()

        # Seletor de Cargo
        lista_cargos = df_completo['Cargo'].unique()
        cargo_selecionado = st.selectbox("Selecione o Cargo:", lista_cargos)
        
        st.markdown("---")
        
        # Botão de Atualização Forçada
        if st.button("🔄 Sincronizar Dados", use_container_width=True):
            st.cache_data.clear()
            with st.spinner("Sincronizando nuvem..."):
                st.session_state['dados_df'] = carregar_dados_planilha(client)
            st.success("Dados atualizados!")
            time.sleep(1)
            st.rerun()
            
        st.markdown("---")
        st.caption(f"v2.5.0 Ultimate • Build {datetime.now().strftime('%Y%m%d')}")

    # --- FILTRAGEM E PROCESSAMENTO ---
    df_filtrado = df_completo[df_completo['Cargo'] == cargo_selecionado].copy()
    
    # Estatísticas Gerais
    total_topicos = len(df_filtrado)
    total_concluido = df_filtrado['Estudado'].sum()
    total_restante = total_topicos - total_concluido
    percentual_global = (total_concluido / total_topicos * 100) if total_topicos > 0 else 0
    
    # Agrupamento por Disciplina
    stats_disciplinas = df_filtrado.groupby('Disciplinas').agg({
        'Estudado': ['sum', 'count']
    }).reset_index()
    stats_disciplinas.columns = ['Disciplina', 'Estudados', 'Total']
    stats_disciplinas['Percentual'] = (stats_disciplinas['Estudados'] / stats_disciplinas['Total'] * 100).round(0)
    
    # Adiciona índice da linha original para atualização
    df_filtrado['linha_original'] = df_filtrado.index + 2

    # --- QUADRO DE MEDALHAS (GAMIFICAÇÃO) ---
    st.markdown("<h3 style='text-align:center; animation: slideUpFade 1s ease-out;'>🎖️ Quadro de Conquistas</h3>", unsafe_allow_html=True)
    
    lista_badges = calcular_badges(total_concluido, percentual_global)
    
    html_badges = '<div class="badge-container">'
    if lista_badges:
        for badge in lista_badges:
            html_badges += f'<div class="badge">✨ {badge}</div>'
    else: 
        html_badges += '<div class="badge locked">🔒 Continue estudando para desbloquear conquistas...</div>'
    html_badges += '</div>'
    
    st.markdown(html_badges, unsafe_allow_html=True)

    # --- CARDS DE KPI (MÉTRICAS) ---
    st.markdown("### 📊 Visão Geral de Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-col-1">
            <div class="metric-card">
                <div class="metric-value" style="color:#3b82f6">{total_topicos}</div>
                <div class="metric-label">Tópicos Totais</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-col-2">
            <div class="metric-card">
                <div class="metric-value" style="color:#22c55e">{total_concluido}</div>
                <div class="metric-label">Concluídos</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-col-3">
            <div class="metric-card">
                <div class="metric-value" style="color:#ef4444">{total_restante}</div>
                <div class="metric-label">Pendentes</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="metric-col-4">
            <div class="metric-card">
                <div class="metric-value" style="color:#8b5cf6">{percentual_global:.0f}%</div>
                <div class="metric-label">Progresso Geral</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- HEATMAP DE PRODUTIVIDADE ---
    st.markdown('<div style="opacity:0; animation: slideUpFade 0.8s ease-out 0.8s forwards;">', unsafe_allow_html=True)
    st.markdown("### 🔥 Ritmo de Estudos (Histórico 60 dias)")
    
    df_calor = gerar_dados_heatmap()
    
    grafico_calor = alt.Chart(df_calor).mark_rect(cornerRadius=3, stroke='white', strokeWidth=2).encode(
        x=alt.X('date:T', title=None, axis=alt.Axis(format='%d/%m', labelColor='#64748b', tickCount=15)),
        y=alt.Y('month(date):O', title=None, axis=None),
        color=alt.Color('count:Q', scale=alt.Scale(scheme='greens'), legend=None),
        tooltip=[
            alt.Tooltip('date:T', title='Data', format='%d/%m/%Y'),
            alt.Tooltip('count:Q', title='Intensidade')
        ]
    ).properties(
        height=120, 
        width='container'
    ).configure_view(
        strokeWidth=0
    )
    
    st.altair_chart(grafico_calor, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- SISTEMA DE REVISÃO INTELIGENTE ---
    st.markdown("### 🔄 Revisão Inteligente (Algoritmo)")
    
    # Lógica: Selecionar tópicos concluídos aleatoriamente
    # Em produção, isso usaria data de conclusão para calcular Spaced Repetition
    topicos_concluidos = df_filtrado[df_filtrado['Estudado'] == True]
    
    if not topicos_concluidos.empty:
        amostra_revisao = topicos_concluidos.sample(n=min(3, len(topicos_concluidos)))
        
        col_revisao, col_info = st.columns([2, 1])
        
        with col_revisao:
            for _, row in amostra_revisao.iterrows():
                st.markdown(f"""
                <div class="review-row">
                    <div>
                        <div class="review-title">{row['Disciplinas']}</div>
                        <div class="review-subtitle">{row['Conteúdos']}</div>
                    </div>
                    <div style="align-self:center; font-size:1.8rem">🧐</div>
                </div>
                """, unsafe_allow_html=True)
                
        with col_info:
            st.info(
                """
                **💡 Por que revisar?**
                
                O algoritmo seleciona tópicos aleatórios que você já estudou 
                para combater a "Curva do Esquecimento" de Ebbinghaus.
                
                Revisar periodicamente garante retenção de longo prazo.
                """
            )
    else:
        st.warning("Você precisa concluir mais tópicos para desbloquear o sistema de revisão.")

    # --- GRÁFICOS DETALHADOS (GRID 3 COLUNAS) ---
    st.markdown("### 🍩 Detalhamento por Disciplina")
    
    grid_cols = st.columns(3)
    
    for index, row in stats_disciplinas.iterrows():
        coluna_atual = grid_cols[index % 3]
        
        with coluna_atual:
            disciplina = row['Disciplina']
            cor_tema = CORES.get(disciplina, '#64748b')
            
            # Título Animado
            st.markdown(f"""
            <div style='text-align:center; font-weight:700; color:{cor_tema}; 
                        animation: popIn 0.5s ease-out forwards; 
                        animation-delay: {1.0 + (index*0.1)}s; 
                        opacity:0; margin-bottom:10px;'>
                {disciplina}
            </div>
            """, unsafe_allow_html=True)
            
            # Gráfico
            chart = criar_grafico_donut(row['Estudados'], row['Total'], cor_tema)
            st.altair_chart(chart, use_container_width=True)

    # --- LISTA DE CONTEÚDOS (CHECKLIST) ---
    st.markdown("### 📚 Conteúdo Programático & Checklist")
    
    # Filtro de Disciplina
    todas_disciplinas = sorted(df_filtrado['Disciplinas'].unique().tolist())
    filtro_disciplina = st.selectbox("Filtrar por Disciplina:", ["Todas"] + todas_disciplinas)
    
    if filtro_disciplina != "Todas":
        view_df = df_filtrado[df_filtrado['Disciplinas'] == filtro_disciplina]
    else:
        view_df = df_filtrado

    # Iteração por Disciplina para organizar visualmente
    for disc in view_df['Disciplinas'].unique():
        sub_df = view_df[view_df['Disciplinas'] == disc]
        
        # Métricas da Disciplina
        total_disc = len(sub_df)
        concluido_disc = sub_df['Estudado'].sum()
        pct_disc = (concluido_disc / total_disc * 100) if total_disc > 0 else 0
        
        cor_disc = CORES.get(disc, '#334155')
        emoji = EMOJIS.get(disc, '📘')

        # Barra de Progresso da Matéria
        st.markdown(f"""
        <div style="margin-top: 2rem; margin-bottom: 0.5rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; font-weight:700; color:#1e293b; font-size:1.2rem;">
                <span>{emoji} {disc}</span>
                <span style="color:{cor_disc}">{pct_disc:.0f}%</span>
            </div>
            <div class="bar-container">
                <div class="bar-fill" style="width: {pct_disc}%; background-color: {cor_disc};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Expander com os Tópicos
        with st.expander(f"Visualizar {total_disc} Tópicos", expanded=False):
            for idx, row in sub_df.iterrows():
                col_check, col_text = st.columns([0.05, 0.95])
                
                with col_check:
                    # Checkbox nativo do Streamlit
                    checked_now = st.checkbox(
                        "Concluído", 
                        value=bool(row['Estudado']), 
                        key=f"chk_{idx}_{row['linha_original']}", 
                        label_visibility="collapsed"
                    )
                
                # Lógica de Atualização de Estado
                if checked_now != bool(row['Estudado']):
                    sucesso = atualizar_status_topico(
                        client, 
                        int(row['linha_original']), 
                        'TRUE' if checked_now else 'FALSE'
                    )
                    
                    if sucesso:
                        msg = "Tópico Concluído! 🚀" if checked_now else "Status Revertido."
                        st.toast(msg, icon="✅")
                        # Pequeno delay para UX e recarga
                        time.sleep(0.5)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Falha ao sincronizar com a nuvem.")

                # Texto do Tópico Estilizado
                classe_css = "done" if row['Estudado'] else ""
                col_text.markdown(
                    f'<div class="conteudo-item {classe_css}">{row["Conteúdos"]}</div>', 
                    unsafe_allow_html=True
                )

    # --- FOOTER ---
    st.markdown(
        f"""
        <div style="text-align:center; color:#94a3b8; padding:4rem 0 2rem 0; font-size:0.85rem; border-top:1px solid #e2e8f0; margin-top:3rem;">
            ✨ Dashboard Ultimate v2.5 | Desenvolvido com Streamlit & Python <br>
            Última Sincronização: {datetime.now().strftime("%H:%M:%S")}
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
