#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🚀 DASHBOARD DE ESTUDOS ULTIMATE v3.2 - UI/UX PREMIUM
================================================================================
VERSÃO: 3.2 - REDESIGN COMPLETO
DATA: 2025-11-28 00:01

MELHORIAS v3.2:
✨ Paleta de cores profissional (Tailwind + gradientes sutis)
✨ Animações suaves e naturais (ease-out, spring)
✨ Glassmorphism nos cards (backdrop-blur)
✨ Microinterações refinadas (scale, opacity, shadow)
✨ Sombras profissionais multi-camadas
✨ Transições coordenadas (stagger animations)
✨ Design System coeso e moderno
✨ Dark mode premium (OLED friendly)
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
    page_title="Dashboard Ultimate v3.2",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================================
# 2. CONSTANTES
# ================================================================================

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

# Paleta Premium (Tons pastéis + vibrantes sutis)
CORES_DISCIPLINAS = {
    'LÍNGUA PORTUGUESA': '#FF6B6B',      # Coral suave
    'RLM': '#4ECDC4',                    # Turquesa
    'REALIDADE DE GOIÁS': '#5B8FF9',     # Azul royal suave
    'LEGISLAÇÃO APLICADA': '#9B59B6',    # Roxo lavanda
    'CONHECIMENTOS ESPECÍFICOS': '#F7B731' # Ouro suave
}

# ================================================================================
# 3. CSS PREMIUM (REDESIGN COMPLETO)
# ================================================================================

def injetar_css_premium():
    tema = st.session_state.get('tema', 'claro')
    
    if tema == 'escuro':
        bg_main = '#0a0e27'
        bg_card = 'rgba(20, 25, 45, 0.6)'
        text_main = '#e8eaf6'
        text_secondary = '#9fa8da'
        border_color = 'rgba(100, 120, 200, 0.2)'
        shadow_color = 'rgba(0, 0, 0, 0.5)'
        bg_hover = 'rgba(30, 35, 60, 0.8)'
    else:
        bg_main = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
        bg_card = 'rgba(255, 255, 255, 0.85)'
        text_main = '#2d3748'
        text_secondary = '#718096'
        border_color = 'rgba(226, 232, 240, 0.8)'
        shadow_color = 'rgba(0, 0, 0, 0.1)'
        bg_hover = 'rgba(255, 255, 255, 0.95)'
    
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

        * {{
            font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
            box-sizing: border-box;
        }}

        /* BACKGROUND GRADIENTE ANIMADO */
        [data-testid="stMainBlockContainer"] {{
            background: {bg_main};
            color: {text_main};
            padding: 1.5rem 2rem 4rem 2rem;
            min-height: 100vh;
            position: relative;
        }}
        
        [data-testid="stMainBlockContainer"]::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3), transparent 50%),
                        radial-gradient(circle at 80% 80%, rgba(99, 102, 241, 0.2), transparent 50%);
            pointer-events: none;
            z-index: -1;
            animation: gradientShift 15s ease infinite;
        }}
        
        @keyframes gradientShift {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.8; transform: scale(1.1); }}
        }}

        #MainMenu, footer, header {{visibility: hidden;}}

        /* HEADER GLASSMORPHISM */
        .header-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            padding: 2rem 2.5rem;
            border-radius: 24px;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37),
                        inset 0 1px 0 0 rgba(255, 255, 255, 0.5);
            position: relative;
            overflow: hidden;
            animation: slideDown 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .header-container::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            animation: shimmer 3s infinite;
        }}
        
        @keyframes shimmer {{
            to {{ left: 100%; }}
        }}

        .header-logo {{
            position: absolute;
            left: 2rem;
            top: 50%;
            transform: translateY(-50%);
            animation: floatLogo 3s ease-in-out infinite;
        }}
        
        @keyframes floatLogo {{
            0%, 100% {{ transform: translateY(-50%) translateX(0); }}
            50% {{ transform: translateY(-50%) translateX(5px); }}
        }}

        .header-logo img {{ 
            max-width: 240px;
            height: auto;
            filter: drop-shadow(0 4px 12px rgba(0,0,0,0.2));
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }}
        
        .header-logo img:hover {{
            transform: scale(1.05) rotate(-2deg);
            filter: drop-shadow(0 8px 24px rgba(99, 102, 241, 0.4));
        }}

        .header-content {{ 
            text-align: center;
            z-index: 1;
        }}

        .header-content h1 {{ 
            font-size: 2.8rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #fff 0%, #f0e7ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.03em;
            font-family: 'Space Grotesk', sans-serif;
            animation: textShine 2s ease-in-out infinite;
        }}
        
        @keyframes textShine {{
            0%, 100% {{ filter: brightness(1); }}
            50% {{ filter: brightness(1.2); }}
        }}
        
        .header-content p {{
            margin-top: 0.5rem;
            font-size: 1.05rem;
            color: rgba(255,255,255,0.95);
            font-weight: 500;
            letter-spacing: 0.15em;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}

        .header-info {{ 
            position: absolute;
            top: 1.5rem;
            right: 2rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }}
        
        .info-row {{
            font-size: 0.7rem;
            color: rgba(255,255,255,0.9);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 0.3rem 0.8rem;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }}
        
        .info-row:hover {{
            background: rgba(255, 255, 255, 0.25);
            transform: translateX(-3px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        /* TOPIC ROW - MINIMALISTA E ELEGANTE */
        .topic-row {{
            display: flex;
            align-items: center;
            padding: 0.7rem 0.4rem;
            margin-bottom: 0.3rem;
            border-radius: 10px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border-left: 3px solid transparent;
        }}
        
        .topic-row:hover {{
            background: {bg_hover};
            backdrop-filter: blur(10px);
            transform: translateX(6px);
            border-left-color: #667eea;
            box-shadow: 0 4px 16px {shadow_color};
        }}
        
        .topic-text {{
            flex: 1;
            font-size: 0.95rem;
            color: {text_main};
            padding-left: 0.4rem;
            line-height: 1.5;
            font-weight: 400;
            transition: all 0.3s ease;
        }}
        
        .topic-text.done {{
            color: {text_secondary};
            text-decoration: line-through;
            opacity: 0.6;
        }}
        
        .topic-date {{
            font-size: 0.7rem;
            color: #667eea;
            background: rgba(102, 126, 234, 0.1);
            padding: 0.25rem 0.7rem;
            border-radius: 20px;
            margin-left: 1rem;
            font-weight: 600;
            border: 1px solid rgba(102, 126, 234, 0.2);
            transition: all 0.3s ease;
        }}
        
        .topic-date:hover {{
            background: rgba(102, 126, 234, 0.2);
            transform: scale(1.05);
        }}

        /* METRIC CARDS - GLASSMORPHISM */
        .metric-card {{ 
            background: {bg_card};
            backdrop-filter: blur(16px) saturate(180%);
            -webkit-backdrop-filter: blur(16px) saturate(180%);
            padding: 2rem 1.5rem;
            border-radius: 20px;
            border: 1px solid {border_color};
            text-align: center;
            box-shadow: 0 8px 32px 0 {shadow_color},
                        inset 0 1px 0 0 rgba(255, 255, 255, 0.5);
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 150px;
            position: relative;
            overflow: hidden;
        }}
        
        .metric-card::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            opacity: 0;
            transition: opacity 0.4s ease;
        }}
        
        .metric-card:hover::before {{
            opacity: 1;
        }}
        
        .metric-card:hover {{ 
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 16px 48px 0 rgba(99, 102, 241, 0.25),
                        inset 0 1px 0 0 rgba(255, 255, 255, 0.7);
            border-color: rgba(102, 126, 234, 0.5);
        }}
        
        .metric-value {{ 
            font-size: 3.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
            margin-bottom: 0.6rem;
            font-family: 'Space Grotesk', sans-serif;
            animation: countUp 0.6s ease-out;
        }}
        
        @keyframes countUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .metric-label {{
            font-size: 0.8rem;
            font-weight: 600;
            color: {text_secondary};
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}

        /* BADGES - MODERNA E VIBRANTE */
        .badge-container {{ 
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 2rem;
            padding: 1rem;
        }}
        
        .badge {{ 
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: #fff;
            padding: 0.7rem 1.5rem;
            border-radius: 50px;
            font-weight: 700;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            box-shadow: 0 4px 20px rgba(245, 87, 108, 0.4);
            animation: badgeFloat 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
            opacity: 0;
            border: 2px solid rgba(255,255,255,0.4);
            position: relative;
            overflow: hidden;
        }}
        
        .badge::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255,255,255,0.3), transparent);
            transform: rotate(45deg);
            animation: badgeShine 2s infinite;
        }}
        
        @keyframes badgeShine {{
            0% {{ transform: translateX(-100%) rotate(45deg); }}
            100% {{ transform: translateX(100%) rotate(45deg); }}
        }}
        
        @keyframes badgeFloat {{
            0% {{ opacity: 0; transform: translateY(30px) scale(0.5) rotate(-10deg); }}
            60% {{ transform: translateY(-5px) scale(1.05) rotate(2deg); }}
            100% {{ opacity: 1; transform: translateY(0) scale(1) rotate(0deg); }}
        }}
        
        .badge:nth-child(1) {{ animation-delay: 0.1s; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .badge:nth-child(2) {{ animation-delay: 0.2s; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .badge:nth-child(3) {{ animation-delay: 0.3s; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        .badge:nth-child(4) {{ animation-delay: 0.4s; background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }}
        .badge:nth-child(5) {{ animation-delay: 0.5s; background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }}
        .badge:nth-child(6) {{ animation-delay: 0.6s; background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); }}
        .badge:nth-child(7) {{ animation-delay: 0.7s; background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }}

        /* CHECKBOX CUSTOM */
        input[type="checkbox"] {{
            appearance: none;
            width: 22px;
            height: 22px;
            border: 2px solid #667eea;
            border-radius: 6px;
            background: rgba(102, 126, 234, 0.1);
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            position: relative;
        }}
        
        input[type="checkbox"]:hover {{
            background: rgba(102, 126, 234, 0.2);
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
            transform: scale(1.15);
        }}
        
        input[type="checkbox"]:checked {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: #764ba2;
            animation: checkBounce 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }}
        
        @keyframes checkBounce {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.2); }}
            100% {{ transform: scale(1); }}
        }}
        
        input[type="checkbox"]:checked::after {{
            content: '✓';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 14px;
            font-weight: bold;
            animation: checkMark 0.3s ease;
        }}
        
        @keyframes checkMark {{
            from {{ opacity: 0; transform: translate(-50%, -50%) scale(0); }}
            to {{ opacity: 1; transform: translate(-50%, -50%) scale(1); }}
        }}

        /* PARTICLES - SUTIS */
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
            animation: floatUp 8s ease-in-out forwards;
            filter: blur(1px);
        }}
        
        @keyframes floatUp {{ 
            0% {{ 
                transform: translateY(100vh) translateX(0) scale(0); 
                opacity: 0; 
            }} 
            10% {{ 
                opacity: 0.6; 
            }}
            90% {{
                opacity: 0.6;
            }}
            100% {{ 
                transform: translateY(-10vh) translateX(50px) scale(1); 
                opacity: 0; 
            }} 
        }}

        /* HEATMAP CONTAINER */
        .heatmap-container {{
            background: {bg_card};
            backdrop-filter: blur(16px);
            padding: 1.5rem;
            border-radius: 20px;
            border: 1px solid {border_color};
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px 0 {shadow_color};
            animation: fadeInUp 0.6s ease-out;
        }}
        
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* CONFETTI */
        .confetti {{
            position: fixed;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: confettiFall 4s ease-out forwards;
        }}
        
        @keyframes confettiFall {{
            to {{ 
                transform: translateY(100vh) translateX(var(--x-offset)) rotate(720deg); 
                opacity: 0; 
            }}
        }}

        /* SECTION HEADERS */
        .section-header {{
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1.5rem;
            font-family: 'Space Grotesk', sans-serif;
            letter-spacing: -0.02em;
            animation: fadeInUp 0.6s ease-out;
        }}

        /* FORM BUTTON */
        .stButton > button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.8rem 2rem;
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.05em;
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        
        .stButton > button:hover {{
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
        }}

        /* RESPONSIVE */
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
                flex-direction: row;
                justify-content: center;
            }}
            .header-content h1 {{ font-size: 2rem; }}
            .metric-card {{ min-height: 130px; padding: 1.5rem 1rem; }}
            .metric-value {{ font-size: 2.5rem; }}
        }}
    </style>
    """, unsafe_allow_html=True)

def injetar_javascript_particulas_premium():
    st.markdown("""
    <div id="sparkles-container"></div>
    <script>
        function createSparkle() {
            const container = document.getElementById('sparkles-container');
            if (!container) return;
            
            const el = document.createElement('div');
            el.classList.add('spark');
            
            const colors = [
                'rgba(102, 126, 234, 0.6)',
                'rgba(118, 75, 162, 0.6)',
                'rgba(240, 147, 251, 0.6)',
                'rgba(245, 87, 108, 0.6)',
                'rgba(67, 233, 123, 0.6)'
            ];
            el.style.background = colors[Math.floor(Math.random() * colors.length)];
            
            const size = Math.random() * 6 + 2;
            el.style.width = size + 'px';
            el.style.height = size + 'px';
            el.style.left = Math.random() * 100 + 'vw';
            el.style.animationDuration = (Math.random() * 6 + 6) + 's';
            
            container.appendChild(el);
            setTimeout(() => el.remove(), 12000);
        }
        
        setInterval(createSparkle, 400);
    </script>
    """, unsafe_allow_html=True)

def criar_confetti_premium():
    st.markdown("""
    <script>
        function launchConfetti() {
            const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#43e97b', '#4facfe'];
            for(let i = 0; i < 200; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.classList.add('confetti');
                    confetti.style.left = Math.random() * 100 + 'vw';
                    confetti.style.top = '-20px';
                    confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                    confetti.style.setProperty('--x-offset', (Math.random() * 200 - 100) + 'px');
                    confetti.style.animationDelay = Math.random() * 0.5 + 's';
                    confetti.style.animationDuration = (Math.random() * 2 + 3) + 's';
                    document.body.appendChild(confetti);
                    setTimeout(() => confetti.remove(), 5000);
                }, i * 15);
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
# 5. VISUALIZAÇÃO (GRÁFICOS PREMIUM)
# ================================================================================

def renderizar_heatmap(df: pd.DataFrame) -> Optional[alt.Chart]:
    df_validos = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    
    if df_validos.empty:
        return None
        
    dados_heatmap = df_validos.groupby('Data_Real').size().reset_index(name='count')
    
    chart = alt.Chart(dados_heatmap).mark_rect(
        cornerRadius=6,
        stroke='white',
        strokeWidth=2
    ).encode(
        x=alt.X('yearmonthdate(Data_Real):O',
                title=None,
                axis=alt.Axis(format='%d/%m', labelColor='#667eea', labelFontSize=11, labelFontWeight=600)
        ),
        y=alt.Y('day(Data_Real):O',
                title=None,
                axis=alt.Axis(labels=False, ticks=False)
        ),
        color=alt.Color('count:Q',
                        scale=alt.Scale(scheme='purples'),
                        legend=None
        ),
        tooltip=[
            alt.Tooltip('Data_Real', title='Data', format='%d/%m/%Y'),
            alt.Tooltip('count', title='Estudos')
        ]
    ).properties(
        height=130,
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
        outerRadius=75,
        innerRadius=58,
        stroke='white',
        strokeWidth=4,
        cornerRadius=8
    ).encode(
        color=alt.Color("Estado",
                        scale=alt.Scale(domain=['Concluído', 'Restante'],
                                        range=[cor_hex, 'rgba(200,200,200,0.3)']),
                        legend=None),
        tooltip=["Estado", "Valor"]
    )
    
    pct = int(concluido/total*100) if total > 0 else 0
    texto = base.mark_text(
        radius=0,
        size=24,
        color=cor_hex,
        fontWeight='bold',
        font='Space Grotesk'
    ).encode(
        text=alt.value(f"{pct}%")
    )
    
    return (pie + texto).properties(width=170, height=170)

# ================================================================================
# 6. GAMIFICAÇÃO
# ================================================================================

def calcular_conquistas(total_estudado: int, percentual: float) -> List[str]:
    badges = []
    
    if percentual >= 10: badges.append("🚀 Iniciante")
    if percentual >= 25: badges.append("🏃 Acelerado")
    if percentual >= 50: badges.append("🔥 Metade")
    if percentual >= 75: badges.append("💎 Avançado")
    if percentual >= 90: badges.append("👑 Mestre")
    if total_estudado >= 50: badges.append("📚 Dedicado")
    if total_estudado >= 100: badges.append("🧠 Expert")
    
    return badges

def calcular_streak(df: pd.DataFrame) -> int:
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
    if 'tema' not in st.session_state:
        st.session_state['tema'] = 'claro'
    
    injetar_css_premium()
    injetar_javascript_particulas_premium()
    
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    temperatura = obter_clima_local()

    # HEADER
    st.markdown(f"""
    <div class="header-container">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Logo">
        </div>
        <div class="header-content">
            <h1>DASHBOARD PREMIUM</h1>
            <p>EXCELÊNCIA • DISCIPLINA • VITÓRIA</p>
        </div>
        <div class="header-info">
            <div class="info-row">📍 GOIÂNIA</div>
            <div class="info-row">📅 {data_hoje}</div>
            <div class="info-row">🌡️ {temperatura}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    client = conectar_google_sheets()
    if not client:
        st.stop()
        
    df = carregar_dados(client)
    if df is None:
        st.warning("⏳ Carregando dados...")
        st.stop()

    # SIDEBAR
    with st.sidebar:
        st.markdown('<p class="section-header" style="font-size:1.2rem;">⚙️ Controles</p>', unsafe_allow_html=True)
        
        tema_atual = st.session_state['tema']
        if st.button(f"🌓 {tema_atual.title()}", use_container_width=True):
            st.session_state['tema'] = 'escuro' if tema_atual == 'claro' else 'claro'
            st.rerun()
        
        st.divider()
        
        lista_cargos = df['Cargo'].unique()
        cargo_selecionado = st.selectbox("📋 Cargo:", lista_cargos)
        
        st.divider()
        
        if st.button("🔄 Atualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.caption("✨ v3.2 Premium UI/UX")

    df_cargo = df[df['Cargo'] == cargo_selecionado].copy()
    df_cargo['linha_planilha'] = df_cargo.index + 2

    total_topicos = len(df_cargo)
    total_concluidos = df_cargo['Estudado'].sum()
    total_restantes = total_topicos - total_concluidos
    progresso_percentual = (total_concluidos / total_topicos * 100) if total_topicos > 0 else 0
    streak_dias = calcular_streak(df_cargo)

    if progresso_percentual >= 100 and 'confetti_100' not in st.session_state:
        criar_confetti_premium()
        st.session_state['confetti_100'] = True
    elif progresso_percentual < 100 and 'confetti_100' in st.session_state:
        del st.session_state['confetti_100']

    # BADGES
    conquistas = calcular_conquistas(total_concluidos, progresso_percentual)
    
    html_badges = '<div class="badge-container">'
    if conquistas:
        for badge in conquistas:
            html_badges += f'<div class="badge">{badge}</div>'
    else:
        html_badges += '<div class="badge" style="background:linear-gradient(135deg, #cbd5e1 0%, #94a3b8 100%);">🔒 Comece a estudar</div>'
    html_badges += '</div>'
    
    st.markdown(html_badges, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_topicos}</div>
            <div class="metric-label">Total</div>
        </div>""", unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_concluidos}</div>
            <div class="metric-label">Concluídos</div>
        </div>""", unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_restantes}</div>
            <div class="metric-label">Faltam</div>
        </div>""", unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{progresso_percentual:.0f}%</div>
            <div class="metric-label">Progresso</div>
        </div>""", unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{streak_dias}</div>
            <div class="metric-label">🔥 Sequência</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

    # HEATMAP
    st.markdown('<p class="section-header">📊 Atividade de Estudos</p>', unsafe_allow_html=True)
    st.markdown('<div class="heatmap-container">', unsafe_allow_html=True)
    
    grafico_heatmap = renderizar_heatmap(df_cargo)
    
    if grafico_heatmap:
        st.altair_chart(grafico_heatmap, use_container_width=True)
    else:
        st.info("💡 Comece a marcar tópicos para visualizar seu histórico!")
        
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

    # DONUTS
    st.markdown('<p class="section-header">🎯 Visão por Matéria</p>', unsafe_allow_html=True)
    
    stats_disciplina = df_cargo.groupby('Disciplinas').agg({
        'Estudado': ['sum', 'count']
    }).reset_index()
    stats_disciplina.columns = ['Disciplina', 'Estudados', 'Total']
    
    colunas_grid = st.columns(min(3, len(stats_disciplina)))
    
    for idx, row in stats_disciplina.iterrows():
        coluna_atual = colunas_grid[idx % len(colunas_grid)]
        
        with coluna_atual:
            nome_disciplina = row['Disciplina']
            cor_tema = CORES_DISCIPLINAS.get(nome_disciplina, '#667eea')
            
            st.markdown(f"""
            <div style='text-align:center; font-weight:700; color:{cor_tema}; margin-bottom:1rem; font-size:0.95rem; font-family:"Space Grotesk", sans-serif;'>
                {nome_disciplina}
            </div>
            """, unsafe_allow_html=True)
            
            chart_donut = renderizar_donut(row['Estudados'], row['Total'], cor_tema)
            st.altair_chart(chart_donut, use_container_width=True)

    st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

    # CHECKLIST
    st.markdown('<p class="section-header">✅ Lista de Conteúdos</p>', unsafe_allow_html=True)
    
    todas_disciplinas = sorted(df_cargo['Disciplinas'].unique().tolist())
    filtro_disciplina = st.selectbox("🔍 Filtrar por:", ["Todas as Matérias"] + todas_disciplinas)
    
    if filtro_disciplina != "Todas as Matérias":
        df_visualizacao = df_cargo[df_cargo['Disciplinas'] == filtro_disciplina]
    else:
        df_visualizacao = df_cargo

    for disciplina in df_visualizacao['Disciplinas'].unique():
        sub_df = df_visualizacao[df_visualizacao['Disciplinas'] == disciplina]
        cor_titulo = CORES_DISCIPLINAS.get(disciplina, '#667eea')
        
        st.markdown(f"""
        <div style="margin-top:2rem; padding-bottom:0.5rem; margin-bottom:1rem; border-bottom:2px solid {cor_titulo};">
            <strong style="color:{cor_titulo}; font-size:1.2rem; font-family:'Space Grotesk', sans-serif;">{disciplina}</strong>
            <span style="float:right; color:#94a3b8; font-size:0.9rem; font-weight:600;">
                {sub_df['Estudado'].sum()} / {len(sub_df)}
            </span>
        </div>
        """, unsafe_allow_html=True)

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
                    badge_data_html = f"<span class='topic-date'>✓ {data_str}</span>"
                
                col_texto.markdown(f"""
                <div class="topic-row">
                    <div class="topic-text {classe_css}">
                        {row['Conteúdos']} {badge_data_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
            
            if submitted and updates_pendentes:
                with st.spinner("⏳ Sincronizando..."):
                    sucesso = atualizar_lote(client, updates_pendentes)
                    
                    if sucesso:
                        st.toast("✅ Salvo!", icon="✅")
                        time.sleep(0.8)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Erro ao salvar")

    st.markdown("<div style='margin-bottom:2rem'></div>", unsafe_allow_html=True)

    # RODAPÉ
    st.markdown(f"""
    <div style="text-align:center; color:rgba(148, 163, 184, 0.8); padding:3rem 0 1.5rem 0; font-size:0.75rem; border-top:1px solid rgba(226, 232, 240, 0.3); margin-top:3rem;">
        ✨ Dashboard Premium v3.2 - UI/UX Redesign<br>
        Desenvolvido com Python & Streamlit • {datetime.now().year}<br>
        Última atualização: {datetime.now().strftime("%H:%M:%S")}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
