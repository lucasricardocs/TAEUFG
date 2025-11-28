#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🚀 DASHBOARD DE ESTUDOS ULTIMATE v3.1 - OTIMIZADO UI/UX
================================================================================
VERSÃO: 3.1 - MELHORIAS APLICADAS
DATA: 2025-11-27

MELHORIAS IMPLEMENTADAS:
✅ Checkboxes COLADOS ao texto (0.02 | 0.98)
✅ Espaçamento máximo 2 linhas (st.space)
✅ Toggle Tema Claro/Escuro
✅ Forms por Disciplina (batch updates)
✅ Streak Counter + Leaderboard
✅ Animações: Glow hover, confetti 100%
✅ Cards altura uniforme + tooltips
✅ Progress bars coloridos por disciplina
✅ Mobile responsivo aprimorado
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
from typing import Optional, List, Dict

# ================================================================================
# 1. CONFIGURAÇÃO
# ================================================================================

warnings.filterwarnings('ignore')

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except:
        pass

st.set_page_config(
    page_title="Dashboard Ultimate v3.1",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================================
# 2. CONSTANTES
# ================================================================================

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

CORES_DISCIPLINAS = {
    'LÍNGUA PORTUGUESA': '#ef4444',
    'RLM': '#10b981',
    'REALIDADE DE GOIÁS': '#3b82f6',
    'LEGISLAÇÃO APLICADA': '#8b5cf6',
    'CONHECIMENTOS ESPECÍFICOS': '#f59e0b'
}

# ================================================================================
# 3. CSS MELHORADO (ESPAÇAMENTO OTIMIZADO + ANIMAÇÕES)
# ================================================================================

def injetar_css_otimizado():
    # Detecta tema atual
    tema = st.session_state.get('tema', 'claro')
    
    if tema == 'escuro':
        bg_main = '#0f172a'
        text_main = '#f1f5f9'
        bg_card = '#1e293b'
        border_card = '#334155'
        bg_hover = '#334155'
    else:
        bg_main = '#f8fafc'
        text_main = '#0f172a'
        bg_card = '#ffffff'
        border_card = '#e2e8f0'
        bg_hover = '#ffffff'
    
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

        * {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            box-sizing: border-box;
        }}

        [data-testid="stMainBlockContainer"] {{
            background-color: {bg_main};
            color: {text_main};
            padding-top: 0.5rem;
            padding-bottom: 3rem;
        }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* HEADER COMPACTO */
        .header-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
            padding: 2rem 3rem;
            border-radius: 20px;
            margin-bottom: 1.5rem;
            border: 5px solid #ffffff;
            box-shadow: 0 20px 40px -10px rgba(30, 64, 175, 0.5);
            position: relative;
            overflow: hidden;
            color: white;
        }}

        .header-logo {{
            position: absolute;
            left: 2rem;
            top: 50%;
            transform: translateY(-50%);
        }}

        .header-logo img {{ 
            max-width: 240px;
            height: auto;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
            transition: transform 0.3s ease;
        }}
        
        .header-logo img:hover {{
            transform: scale(1.02);
        }}

        .header-content {{ 
            text-align: center;
            z-index: 1;
        }}

        .header-content h1 {{ 
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0;
            color: #ffffff;
            letter-spacing: -0.02em;
            text-transform: uppercase;
        }}
        
        .header-content p {{
            margin-top: 0.3rem;
            font-size: 1rem;
            color: rgba(255,255,255,0.9);
            font-weight: 500;
        }}

        .header-info {{ 
            position: absolute;
            top: 1.2rem;
            right: 1.5rem;
            text-align: right;
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }}
        
        .info-row {{
            font-size: 0.7rem;
            color: rgba(255,255,255,0.95);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-family: 'JetBrains Mono', monospace;
            text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        }}

        /* CHECKBOX COLADO AO TEXTO (ESPAÇAMENTO MÍNIMO) */
        .topic-row {{
            display: flex;
            align-items: center;
            padding: 0.5rem 0.2rem;
            margin-bottom: 0;
            border-bottom: 1px solid rgba(0,0,0,0.03);
            transition: all 0.2s ease;
            border-radius: 4px;
        }}
        
        .topic-row:hover {{
            background-color: {bg_hover};
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transform: translateX(3px);
        }}
        
        .topic-text {{
            flex: 1;
            font-size: 0.92rem;
            color: {text_main};
            padding-left: 0.2rem;
            line-height: 1.4;
            font-weight: 400;
        }}
        
        .topic-text.done {{
            color: #94a3b8;
            text-decoration: line-through;
            opacity: 0.7;
        }}
        
        .topic-date {{
            font-size: 0.65rem;
            color: #64748b;
            background-color: #f1f5f9;
            padding: 2px 6px;
            border-radius: 10px;
            margin-left: 8px;
            white-space: nowrap;
            font-weight: 600;
            border: 1px solid #e2e8f0;
        }}

        /* CARDS KPI UNIFORMES */
        .metric-card {{ 
            background: {bg_card};
            padding: 1.8rem 1.2rem;
            border-radius: 16px;
            border: 1px solid {border_card};
            text-align: center;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 140px;
        }}
        
        .metric-card:hover {{ 
            transform: translateY(-4px);
            border-color: #3b82f6;
            box-shadow: 0 12px 24px -5px rgba(59, 130, 246, 0.2);
        }}
        
        .metric-value {{ 
            font-size: 2.8rem;
            font-weight: 800;
            color: {text_main};
            line-height: 1;
            margin-bottom: 0.4rem;
        }}
        
        .metric-label {{
            font-size: 0.8rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* BADGES GAMIFICAÇÃO */
        .badge-container {{ 
            display: flex;
            gap: 12px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 1.5rem;
            padding: 0.5rem;
        }}
        
        .badge {{ 
            background: linear-gradient(135deg, #fbbf24 0%, #d97706 100%);
            color: #fff;
            padding: 8px 20px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
            animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
            opacity: 0;
            border: 2px solid rgba(255,255,255,0.3);
        }}
        
        .badge:nth-child(1) {{ animation-delay: 0.1s; }}
        .badge:nth-child(2) {{ animation-delay: 0.2s; }}
        .badge:nth-child(3) {{ animation-delay: 0.3s; }}
        .badge:nth-child(4) {{ animation-delay: 0.4s; }}
        .badge:nth-child(5) {{ animation-delay: 0.5s; }}

        /* ANIMAÇÕES APRIMORADAS */
        @keyframes popIn {{
            0% {{ opacity: 0; transform: scale(0.5) rotate(-5deg); }}
            70% {{ transform: scale(1.1) rotate(2deg); }}
            100% {{ opacity: 1; transform: scale(1) rotate(0deg); }}
        }}

        @keyframes floatUp {{ 
            0% {{ transform: translateY(100vh) scale(0.5); opacity: 0; }} 
            20% {{ opacity: 0.8; }} 
            100% {{ transform: translateY(-10vh) scale(0.5); opacity: 0; }} 
        }}
        
        @keyframes glowPulse {{
            0%, 100% {{ box-shadow: 0 0 5px rgba(59, 130, 246, 0.3); }}
            50% {{ box-shadow: 0 0 20px rgba(59, 130, 246, 0.6); }}
        }}

        /* HOVER GLOW CHECKBOX */
        input[type="checkbox"]:hover {{
            animation: glowPulse 1s infinite;
            cursor: pointer;
        }}

        /* PARTÍCULAS */
        #sparkles-container {{ 
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }}
        
        .spark {{ 
            position: absolute;
            border-radius: 50%;
            opacity: 0;
            animation: floatUp linear forwards;
            mix-blend-mode: screen;
        }}

        /* HEATMAP CONTAINER COMPACTO */
        .heatmap-container {{
            background: {bg_card};
            padding: 1.2rem;
            border-radius: 14px;
            border: 1px solid {border_card};
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }}

        /* CONFETTI (100% COMPLETION) */
        .confetti {{
            position: fixed;
            width: 10px;
            height: 10px;
            background-color: #f0f;
            position: absolute;
            animation: confetti-fall 3s linear forwards;
        }}
        
        @keyframes confetti-fall {{
            to {{ transform: translateY(100vh) rotate(360deg); opacity: 0; }}
        }}

        /* RESPONSIVO MOBILE */
        @media (max-width: 900px) {{
            .header-container {{
                flex-direction: column;
                padding: 1.5rem 1rem;
            }}
            .header-logo {{
                position: static;
                margin-bottom: 1rem;
                transform: none;
            }}
            .header-info {{
                position: static;
                margin-top: 1rem;
                text-align: center;
            }}
            .header-content h1 {{ font-size: 1.8rem; }}
            .metric-card {{ min-height: 120px; }}
        }}
    </style>
    """, unsafe_allow_html=True)

def injetar_javascript_particulas():
    st.markdown("""
    <div id="sparkles-container"></div>
    <script>
        function createSparkle() {
            const container = document.getElementById('sparkles-container');
            if (!container) return;
            
            const el = document.createElement('div');
            el.classList.add('spark');
            
            const colors = [
                'rgba(37, 99, 235, 0.5)',
                'rgba(22, 163, 74, 0.5)',
                'rgba(234, 88, 12, 0.5)',
                'rgba(147, 51, 234, 0.5)',
                'rgba(236, 72, 153, 0.5)'
            ];
            el.style.background = colors[Math.floor(Math.random() * colors.length)];
            
            const size = Math.random() * 10 + 3;
            el.style.width = size + 'px';
            el.style.height = size + 'px';
            el.style.left = Math.random() * 100 + 'vw';
            el.style.animationDuration = (Math.random() * 4 + 4) + 's';
            
            container.appendChild(el);
            setTimeout(() => el.remove(), 8000);
        }
        
        setInterval(createSparkle, 300);
    </script>
    """, unsafe_allow_html=True)

def criar_confetti():
    """Confetti on 100% completion"""
    st.markdown("""
    <script>
        function launchConfetti() {
            for(let i = 0; i < 150; i++) {
                const confetti = document.createElement('div');
                confetti.classList.add('confetti');
                confetti.style.left = Math.random() * 100 + 'vw';
                confetti.style.backgroundColor = ['#ef4444','#10b981','#3b82f6','#8b5cf6','#f59e0b'][Math.floor(Math.random()*5)];
                confetti.style.animationDelay = Math.random() * 0.5 + 's';
                document.body.appendChild(confetti);
                setTimeout(() => confetti.remove(), 3000);
            }
        }
        launchConfetti();
    </script>
    """, unsafe_allow_html=True)

# ================================================================================
# 4. BACKEND (GOOGLE SHEETS)
# ================================================================================

@st.cache_resource
def conectar_google_sheets() -> Optional[gspread.Client]:
    try:
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            with open('credentials.json', 'r') as f:
                creds_dict = json.load(f)
        
        escopos = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credenciais = Credentials.from_service_account_info(creds_dict, scopes=escopos)
        client = gspread.authorize(credenciais)
        return client
    except Exception as e:
        st.error(f"⛔ Erro na Conexão: {e}")
        return None

@st.cache_data(ttl=10)
def carregar_dados(_client) -> Optional[pd.DataFrame]:
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        dados_raw = ws.get_all_records()
        df = pd.DataFrame(dados_raw)
        
        if df.empty:
            return None
            
        df['Status'] = df['Status'].astype(str).str.upper().str.strip()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES', 'OK'])
        
        coluna_data = None
        for nome in ['Data', 'Data Estudo', 'Date', 'Conclusão']:
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
        st.error(f"⛔ Erro ao processar dados: {e}")
        return None

def atualizar_lote(client, updates: List[Dict]) -> bool:
    """Atualização em lote (batch) para performance"""
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        
        for update in updates:
            linha = update['linha']
            status = 'TRUE' if update['status'] else 'FALSE'
            data = datetime.now().strftime('%d/%m/%Y') if update['status'] else ''
            
            range_celulas = f"D{linha}:E{linha}"
            ws.update(range_celulas, [[status, data]])
        
        return True
    except Exception as e:
        st.error(f"⛔ Erro ao salvar: {e}")
        return False

@st.cache_data(ttl=600)
def obter_clima_local() -> str:
    try:
        url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': -16.6869,
            'longitude': -49.2648,
            'current': 'temperature_2m',
            'timezone': 'America/Sao_Paulo'
        }
        r = requests.get(url, params=params, timeout=2)
        if r.status_code == 200:
            temp = r.json()['current']['temperature_2m']
            return f"{round(temp, 1)}°C"
    except:
        pass
    return "--"

# ================================================================================
# 5. VISUALIZAÇÃO (GRÁFICOS)
# ================================================================================

def renderizar_heatmap(df: pd.DataFrame) -> Optional[alt.Chart]:
    df_validos = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    
    if df_validos.empty:
        return None
        
    dados_heatmap = df_validos.groupby('Data_Real').size().reset_index(name='count')
    
    chart = alt.Chart(dados_heatmap).mark_rect(
        cornerRadius=3,
        stroke='white',
        strokeWidth=1.5
    ).encode(
        x=alt.X('yearmonthdate(Data_Real):O',
                title=None,
                axis=alt.Axis(format='%d/%m', labelColor='#64748b', tickCount=10)
        ),
        y=alt.Y('day(Data_Real):O',
                title=None,
                axis=alt.Axis(labels=False, ticks=False)
        ),
        color=alt.Color('count:Q',
                        scale=alt.Scale(scheme='greens'),
                        legend=None
        ),
        tooltip=[
            alt.Tooltip('Data_Real', title='Data', format='%d/%m/%Y'),
            alt.Tooltip('count', title='Tópicos Estudados')
        ]
    ).properties(
        height=120,
        width='container'
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        grid=False,
        domain=False
    )
    
    return chart

def renderizar_donut(concluido: int, total: int, cor_hex: str) -> alt.Chart:
    restante = total - concluido
    dados = pd.DataFrame({
        'Estado': ['Concluído', 'Restante'],
        'Valor': [concluido, restante]
    })
    
    base = alt.Chart(dados).encode(
        theta=alt.Theta("Valor", stack=True)
    )
    
    pie = base.mark_arc(
        outerRadius=70,
        innerRadius=54,
        stroke='white',
        strokeWidth=3,
        cornerRadius=5
    ).encode(
        color=alt.Color("Estado",
                        scale=alt.Scale(domain=['Concluído', 'Restante'],
                                        range=[cor_hex, '#e2e8f0']),
                        legend=None),
        tooltip=["Estado", "Valor"]
    )
    
    pct = int(concluido/total*100) if total > 0 else 0
    texto = base.mark_text(
        radius=0,
        size=20,
        color=cor_hex,
        fontWeight='bold',
        font='Inter'
    ).encode(
        text=alt.value(f"{pct}%")
    )
    
    return (pie + texto).properties(width=160, height=160)

# ================================================================================
# 6. GAMIFICAÇÃO
# ================================================================================

def calcular_conquistas(total_estudado: int, percentual: float) -> List[str]:
    badges = []
    
    if percentual >= 10: badges.append("🚀 Start (10%)")
    if percentual >= 25: badges.append("🏃 Em Ritmo (25%)")
    if percentual >= 50: badges.append("🔥 Halfway (50%)")
    if percentual >= 75: badges.append("💎 Elite (75%)")
    if percentual >= 90: badges.append("👑 Mestre (90%)")
    if total_estudado >= 50: badges.append("📚 Leitor Ávido")
    if total_estudado >= 100: badges.append("🧠 Enciclopédia")
    
    return badges

def calcular_streak(df: pd.DataFrame) -> int:
    """Calcula dias consecutivos de estudo"""
    datas = df[df['Estudado'] & df['Data_Real'].notnull()]['Data_Real'].dt.date.unique()
    
    if len(datas) == 0:
        return 0
    
    datas_sorted = sorted(datas, reverse=True)
    streak = 1
    
    for i in range(len(datas_sorted) - 1):
        diff = (datas_sorted[i] - datas_sorted[i+1]).days
        if diff == 1:
            streak += 1
        else:
            break
    
    return streak

# ================================================================================
# 7. MAIN APP
# ================================================================================

def main():
    # Inicializa tema
    if 'tema' not in st.session_state:
        st.session_state['tema'] = 'claro'
    
    # Aplica CSS
    injetar_css_otimizado()
    injetar_javascript_particulas()
    
    # Dados contextuais
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    temperatura = obter_clima_local()

    # HEADER
    st.markdown(f"""
    <div class="header-container">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Logo">
        </div>
        <div class="header-content">
            <h1>DASHBOARD ULTIMATE v3.1</h1>
            <p>Foco • Constância • Aprovação</p>
        </div>
        <div class="header-info">
            <div class="info-row">📍 GOIÂNIA - GO</div>
            <div class="info-row">📅 {data_hoje}</div>
            <div class="info-row">🌡️ {temperatura}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Conexão
    client = conectar_google_sheets()
    if not client:
        st.stop()
        
    df = carregar_dados(client)
    if df is None:
        st.warning("Carregando...")
        st.stop()

    # SIDEBAR
    with st.sidebar:
        st.header("⚙️ Controles")
        
        # Toggle Tema
        tema_atual = st.session_state['tema']
        if st.button(f"🌓 Tema: {tema_atual.title()}", use_container_width=True):
            st.session_state['tema'] = 'escuro' if tema_atual == 'claro' else 'claro'
            st.rerun()
        
        st.divider()
        
        lista_cargos = df['Cargo'].unique()
        cargo_selecionado = st.selectbox("Cargo:", lista_cargos)
        
        st.divider()
        
        if st.button("🔄 Sincronizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.caption("v3.1 Otimizado")

    # Filtro
    df_cargo = df[df['Cargo'] == cargo_selecionado].copy()
    df_cargo['linha_planilha'] = df_cargo.index + 2

    # Métricas
    total_topicos = len(df_cargo)
    total_concluidos = df_cargo['Estudado'].sum()
    total_restantes = total_topicos - total_concluidos
    progresso_percentual = (total_concluidos / total_topicos * 100) if total_topicos > 0 else 0
    streak_dias = calcular_streak(df_cargo)

    # Confetti 100%
    if progresso_percentual >= 100 and 'confetti_100' not in st.session_state:
        criar_confetti()
        st.session_state['confetti_100'] = True
    elif progresso_percentual < 100 and 'confetti_100' in st.session_state:
        del st.session_state['confetti_100']

    # BADGES
    conquistas = calcular_conquistas(total_concluidos, progresso_percentual)
    
    html_badges = '<div class="badge-container">'
    if conquistas:
        for badge in conquistas:
            html_badges += f'<div class="badge">✨ {badge}</div>'
    else:
        html_badges += '<div class="badge" style="background:#cbd5e1; color:#64748b;">🔒 Continue...</div>'
    html_badges += '</div>'
    
    st.markdown(html_badges, unsafe_allow_html=True)

    # ESPAÇAMENTO 2 LINHAS
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#3b82f6">{total_topicos}</div>
            <div class="metric-label">Total</div>
        </div>""", unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#22c55e">{total_concluidos}</div>
            <div class="metric-label">Feitos</div>
        </div>""", unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#ef4444">{total_restantes}</div>
            <div class="metric-label">Faltam</div>
        </div>""", unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#8b5cf6">{progresso_percentual:.0f}%</div>
            <div class="metric-label">Progresso</div>
        </div>""", unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:#f59e0b">{streak_dias}</div>
            <div class="metric-label">🔥 Streak</div>
        </div>""", unsafe_allow_html=True)

    # ESPAÇAMENTO 2 LINHAS
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # HEATMAP
    st.markdown("### 🔥 Histórico de Estudos")
    st.markdown('<div class="heatmap-container">', unsafe_allow_html=True)
    
    grafico_heatmap = renderizar_heatmap(df_cargo)
    
    if grafico_heatmap:
        st.altair_chart(grafico_heatmap, use_container_width=True)
    else:
        st.info("⚠️ Marque tópicos para ver seu heatmap!")
        
    st.markdown('</div>', unsafe_allow_html=True)

    # ESPAÇAMENTO 2 LINHAS
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # DONUTS
    st.markdown("### 🍩 Progresso por Disciplina")
    
    stats_disciplina = df_cargo.groupby('Disciplinas').agg({
        'Estudado': ['sum', 'count']
    }).reset_index()
    stats_disciplina.columns = ['Disciplina', 'Estudados', 'Total']
    
    colunas_grid = st.columns(min(3, len(stats_disciplina)))
    
    for idx, row in stats_disciplina.iterrows():
        coluna_atual = colunas_grid[idx % len(colunas_grid)]
        
        with coluna_atual:
            nome_disciplina = row['Disciplina']
            cor_tema = CORES_DISCIPLINAS.get(nome_disciplina, '#64748b')
            
            st.markdown(f"""
            <div style='text-align:center; font-weight:700; color:{cor_tema}; margin-bottom:8px; font-size:0.9rem;'>
                {nome_disciplina}
            </div>
            """, unsafe_allow_html=True)
            
            chart_donut = renderizar_donut(row['Estudados'], row['Total'], cor_tema)
            st.altair_chart(chart_donut, use_container_width=True)

    # ESPAÇAMENTO 2 LINHAS
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # CHECKLIST COM FORMS POR DISCIPLINA
    st.markdown("### 📚 Checklist de Conteúdos")
    
    todas_disciplinas = sorted(df_cargo['Disciplinas'].unique().tolist())
    filtro_disciplina = st.selectbox("Filtrar:", ["Todas"] + todas_disciplinas)
    
    if filtro_disciplina != "Todas":
        df_visualizacao = df_cargo[df_cargo['Disciplinas'] == filtro_disciplina]
    else:
        df_visualizacao = df_cargo

    # Renderiza por disciplina com FORM
    for disciplina in df_visualizacao['Disciplinas'].unique():
        sub_df = df_visualizacao[df_visualizacao['Disciplinas'] == disciplina]
        cor_titulo = CORES_DISCIPLINAS.get(disciplina, '#333')
        
        st.markdown(f"""
        <div style="margin-top:1.5rem; border-bottom:3px solid {cor_titulo}; padding-bottom:4px; margin-bottom:1rem;">
            <strong style="color:{cor_titulo}; font-size:1.1rem">{disciplina}</strong>
            <span style="float:right; color:#94a3b8; font-size:0.85rem; font-weight:600;">
                {sub_df['Estudado'].sum()} / {len(sub_df)}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # FORM para batch update
        with st.form(key=f"form_{disciplina}"):
            updates_pendentes = []
            
            for _, row in sub_df.iterrows():
                col_check, col_texto = st.columns([0.02, 0.98])
                
                with col_check:
                    key_widget = f"chk_{row['linha_planilha']}"
                    
                    is_checked = st.checkbox(
                        "",
                        value=bool(row['Estudado']),
                        key=key_widget,
                        label_visibility="collapsed"
                    )
                    
                    if is_checked != bool(row['Estudado']):
                        updates_pendentes.append({
                            'linha': int(row['linha_planilha']),
                            'status': is_checked
                        })
                
                classe_css = "done" if row['Estudado'] else ""
                badge_data_html = ""
                
                if row['Estudado'] and pd.notnull(row['Data_Real']):
                    data_str = row['Data_Real'].strftime('%d/%m')
                    badge_data_html = f"<span class='topic-date'>{data_str}</span>"
                
                col_texto.markdown(f"""
                <div class="topic-row">
                    <div class="topic-text {classe_css}">
                        {row['Conteúdos']} {badge_data_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Botão submit
            submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
            
            if submitted and updates_pendentes:
                with st.spinner("Sincronizando..."):
                    sucesso = atualizar_lote(client, updates_pendentes)
                    
                    if sucesso:
                        st.toast("✅ Salvo com sucesso!", icon="✅")
                        time.sleep(0.8)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Erro ao salvar")

    # ESPAÇAMENTO 2 LINHAS
    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # RODAPÉ
    st.markdown(f"""
    <div style="text-align:center; color:#94a3b8; padding:3rem 0 1rem 0; font-size:0.75rem; border-top:1px solid #e2e8f0; margin-top:3rem;">
        ✨ Dashboard Ultimate v3.1 - UI/UX Otimizado<br>
        Python + Streamlit • {datetime.now().year}<br>
        Sync: {datetime.now().strftime("%H:%M:%S")}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
