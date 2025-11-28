#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 DASHBOARD DE ESTUDOS - CÂMARA MUNICIPAL DE GOIÂNIA
================================================================================
VERSÃO: 5.0 - POMODORO, METODOLOGIAS, SIDEBAR E RELOGIO
DATA: 2025-11-28 08:34

MELHORIAS v5.0:
✓ Relógio em tempo real (até segundos)
✓ Pomodoro Timer (30 min) com notificação sonora
✓ Sidebar com seleção de cargo
✓ Aba com metodologias de estudo
✓ Informações de local, data e horário em containers translúcidos centralizados
✓ Fonte Nunito em todo o site
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
import pytz
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
    page_title="Dashboard de Estudos",
    page_icon="📊",
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
    'LÍNGUA PORTUGUESA': '#2563eb',
    'RLM': '#059669',
    'REALIDADE DE GOIÁS': '#7c3aed',
    'LEGISLAÇÃO APLICADA': '#dc2626',
    'CONHECIMENTOS ESPECÍFICOS': '#ea580c'
}

TIMEZONE_BRASILIA = pytz.timezone('America/Sao_Paulo')

# ================================================================================
# 3. FUNÇÕES UTILITÁRIAS
# ================================================================================

def obter_horario_brasilia():
    """Retorna datetime atual no fuso de Brasília"""
    return datetime.now(TIMEZONE_BRASILIA)

# ================================================================================
# 4. CSS PROFISSIONAL
# ================================================================================

def injetar_css_profissional():
    tema = st.session_state.get('tema', 'claro')
    
    if tema == 'escuro':
        bg_main = '#0f172a'
        bg_card = '#1e293b'
        text_main = '#f1f5f9'
        text_secondary = '#94a3b8'
        border_color = '#334155'
        hover_bg = '#334155'
        header_bg = 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)'
        header_text = '#f1f5f9'
    else:
        bg_main = '#f8fafc'
        bg_card = '#ffffff'
        text_main = '#1e293b'
        text_secondary = '#64748b'
        border_color = '#e2e8f0'
        hover_bg = '#f1f5f9'
        header_bg = 'linear-gradient(135deg, #f8fafc 0%, #e0e7ff 50%, #dbeafe 100%)'
        header_text = '#1e293b'
    
    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * {{
            font-family: 'Nunito', sans-serif;
            box-sizing: border-box;
        }}

        [data-testid="stMainBlockContainer"] {{
            background-color: {bg_main};
            color: {text_main};
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }}

        #MainMenu, footer, header {{visibility: hidden;}}

        /* SIDEBAR */
        [data-testid="stSidebar"] {{
            background-color: {bg_card};
            border-right: 2px solid {border_color};
        }}

        [data-testid="stSidebar"] .stSelectbox {{
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }}

        [data-testid="stSidebar"] .stSelectbox label {{
            color: white !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
        }}

        /* HEADER */
        .header-container {{
            background: {header_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 2rem 2.5rem;
            margin-bottom: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}

        .header-container:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }}

        .header-logo img {{
            max-width: 220px;
            height: auto;
            transition: transform 0.3s ease;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
            animation: spin 4s linear infinite;
        }}

        .header-logo img:hover {{
            transform: scale(1.05);
        }}

        .header-title {{
            font-size: 1.8rem;
            font-weight: 700;
            color: {header_text};
            margin: 0;
        }}

        .header-subtitle {{
            font-size: 1.1rem;
            color: {text_secondary};
            margin: 0;
        }}

        .header-info {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 1rem;
            margin-top: 1rem;
        }}

        .info-item {{
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            font-weight: 600;
            color: {text_secondary};
            text-align: center;
            min-width: 120px;
        }}

        .info-item:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}

        /* KPI CARDS */
        .kpi-card {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 1.5rem;
            transition: all 0.3s ease;
            cursor: pointer;
            min-height: 140px;
            max-height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }}

        .kpi-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            border-color: #2563eb;
        }}

        .kpi-label {{
            font-size: 0.75rem;
            font-weight: 600;
            color: {text_secondary};
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem;
        }}

        .kpi-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: {text_main};
            line-height: 1;
            margin-bottom: 0.5rem;
        }}

        .kpi-detail {{
            font-size: 0.813rem;
            color: {text_secondary};
        }}

        /* PROGRESS BAR */
        .progress-bar-container {{
            margin: 1rem 0;
            background: {bg_main};
            border-radius: 8px;
            height: 12px;
            overflow: hidden;
            border: 1px solid {border_color};
        }}

        .progress-bar-fill {{
            height: 100%;
            transition: width 0.6s ease;
            border-radius: 8px;
        }}

        .progress-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
        }}

        .progress-label {{
            font-weight: 600;
            color: {text_main};
        }}

        .progress-percentage {{
            font-weight: 700;
            color: {text_secondary};
        }}

        /* TOPIC ITEM */
        .topic-item {{
            display: flex;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid {border_color};
            transition: all 0.2s ease;
        }}

        .topic-item:hover {{
            background: {hover_bg};
            padding-left: 0.5rem;
            border-left: 3px solid #2563eb;
        }}

        .topic-item:last-child {{
            border-bottom: none;
        }}

        .topic-text {{
            flex: 1;
            font-size: 0.938rem;
            color: {text_main};
            line-height: 1.5;
        }}

        .topic-text.done {{
            color: {text_secondary};
            text-decoration: line-through;
        }}

        .topic-date {{
            font-size: 0.813rem;
            color: {text_secondary};
            background: {bg_main};
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            margin-left: 1rem;
            transition: all 0.2s ease;
        }}

        .topic-date:hover {{
            background: #2563eb;
            color: white;
        }}

        /* CHECKBOX */
        input[type="checkbox"] {{
            width: 18px;
            height: 18px;
            border: 2px solid {border_color};
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        input[type="checkbox"]:hover {{
            border-color: #2563eb;
            transform: scale(1.1);
        }}

        /* BOTÃO */
        .stButton > button {{
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 0.625rem 1.5rem;
            font-weight: 600;
            font-size: 0.875rem;
            transition: all 0.2s ease;
        }}

        .stButton > button:hover {{
            background: #1d4ed8;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
        }}

        /* DONUT */
        .donut-wrapper {{
            background: transparent;
            padding: 1.5rem;
            border-radius: 8px;
            border: 2px solid #e5e7eb;
            transition: all 0.3s ease;
        }}

        .donut-wrapper:hover {{
            transform: scale(1.03);
            border-color: #2563eb;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
        }}

        .donut-title {{
            font-size: 1rem;
            font-weight: 600;
            color: {text_main};
            margin-bottom: 0.75rem;
            text-align: center;
        }}

        .donut-stats {{
            text-align: center;
            font-size: 0.875rem;
            color: {text_secondary};
            margin-bottom: 1rem;
            font-weight: 500;
        }}

        /* RESPONSIVO */
        @media (max-width: 1024px) {{
            .kpi-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 768px) {{
            .header-container {{
                flex-direction: column;
                gap: 1.5rem;
            }}

            .header-info {{
                flex-direction: column;
                text-align: center;
            }}

            [data-testid="stMainBlockContainer"] {{
                padding: 1rem;
            }}
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
    """, unsafe_allow_html=True)

# ================================================================================
# 5. BACKEND
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
        st.error(f"Erro na conexão: {e}")
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
        st.error(f"Erro ao carregar dados: {e}")
        return None

def atualizar_lote(client, updates: List[Dict]) -> bool:
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        agora_brasilia = obter_horario_brasilia()
        
        for update in updates:
            linha = update['linha']
            status = 'TRUE' if update['status'] else 'FALSE'
            data = agora_brasilia.strftime('%d/%m/%Y') if update['status'] else ''
            
            range_celulas = f"D{linha}:E{linha}"
            ws.update(range_celulas, [[status, data]])
        
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
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
# 6. VISUALIZAÇÃO
# ================================================================================

def renderizar_heatmap(df: pd.DataFrame) -> Optional[alt.Chart]:
    df_validos = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    
    if df_validos.empty:
        return None
    
    dados_agrupados = df_validos.groupby('Data_Real').agg({
        'Disciplinas': lambda x: ', '.join(sorted(set(x))),
        'Conteúdos': 'count'
    }).reset_index()
    
    dados_agrupados.columns = ['Data_Real', 'Materias', 'Quantidade']
    
    chart = alt.Chart(dados_agrupados).mark_rect(
        cornerRadius=3,
        stroke='#d1d5db',
        strokeWidth=1.5
    ).encode(
        x=alt.X('yearmonthdate(Data_Real):O',
                title='Data',
                axis=alt.Axis(
                    format='%d/%m',
                    labelAngle=0,
                    labelFontSize=10,
                    labelColor='#64748b',
                    titleFontSize=12,
                    titleFontWeight=600
                )
        ),
        y=alt.Y('day(Data_Real):O',
                title='Dia da Semana',
                axis=alt.Axis(
                    labelFontSize=10,
                    labelColor='#64748b',
                    titleFontSize=12,
                    titleFontWeight=600
                )
        ),
        color=alt.Color('Quantidade:Q',
                        scale=alt.Scale(
                            domain=[1, 3, 6, 10, 15],
                            range=['#9be9a8', '#40c463', '#30a14e', '#216e39', '#0d4429']
                        ),
                        legend=None
        ),
        tooltip=[
            alt.Tooltip('Data_Real:T', title='Data', format='%d/%m/%Y (%A)'),
            alt.Tooltip('Quantidade:Q', title='Total de Tópicos'),
            alt.Tooltip('Materias:N', title='Matérias Estudadas')
        ]
    ).properties(
        height=220,
        width='container'
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        grid=False,
        domain=True,
        domainColor='#e2e8f0',
        domainWidth=1
    )
    
    return chart

def renderizar_donut(concluido: int, total: int, cor_hex: str) -> alt.Chart:
    restante = total - concluido
    dados = pd.DataFrame({
        'Status': ['Concluído', 'Pendente'],
        'Valor': [concluido, restante]
    })
    
    base = alt.Chart(dados).encode(
        theta=alt.Theta("Valor:Q", stack=True)
    )
    
    pie = base.mark_arc(
        outerRadius=90,
        innerRadius=65,
        stroke='#e5e7eb',
        strokeWidth=2
    ).encode(
        color=alt.Color("Status:N",
                        scale=alt.Scale(domain=['Concluído', 'Pendente'],
                                        range=[cor_hex, '#f3f4f6']),
                        legend=None),
        tooltip=[
            alt.Tooltip('Status:N', title='Status'),
            alt.Tooltip('Valor:Q', title='Quantidade')
        ]
    )
    
    pct = int(concluido/total*100) if total > 0 else 0
    texto = base.mark_text(
        radius=0,
        size=24,
        color='#1e293b',
        fontWeight='bold',
        font='Nunito'
    ).encode(
        text=alt.value(f"{pct}%")
    )
    
    return (pie + texto).properties(
        width=220,
        height=220,
        background='transparent'
    ).configure_view(
        strokeWidth=0
    )

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
# 7. POMODORO TIMER
# ================================================================================

def pomodoro_timer():
    st.header("⏱️ Pomodoro Timer")
    
    if 'pomodoro_running' not in st.session_state:
        st.session_state.pomodoro_running = False
        st.session_state.pomodoro_time = 30 * 60  # 30 minutos em segundos
        st.session_state.pomodoro_end = None
    
    if st.button("Iniciar Pomodoro"):
        st.session_state.pomodoro_running = True
        st.session_state.pomodoro_time = 30 * 60
        st.session_state.pomodoro_end = time.time() + 30 * 60
    
    if st.session_state.pomodoro_running:
        tempo_restante = int(st.session_state.pomodoro_end - time.time())
        
        if tempo_restante > 0:
            mins, secs = divmod(tempo_restante, 60)
            st.write(f"Tempo restante: {mins:02d}:{secs:02d}")
            time.sleep(1)
            st.rerun()
        else:
            st.session_state.pomodoro_running = False
            st.success("Pomodoro concluído!")
            st.audio("https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3", autoplay=True)

# ================================================================================
# 8. METODOLOGIAS DE ESTUDO
# ================================================================================

def metodologias_estudo():
    st.header("📚 Principais Metodologias de Estudo")
    
    st.markdown("### 1. Pomodoro")
    st.markdown("Técnica de gerenciamento de tempo que divide o trabalho em blocos de 25 minutos, com pausas curtas entre eles.")
    
    st.markdown("### 2. Feynman")
    st.markdown("Ensine o que aprendeu como se estivesse explicando para uma criança, simplificando o conteúdo.")
    
    st.markdown("### 3. Cornell")
    st.markdown("Organize anotações em três colunas: anotações, resumo e perguntas.")
    
    st.markdown("### 4. Mapas Mentais")
    st.markdown("Organize informações em diagramas visuais para facilitar a memorização.")
    
    st.markdown("### 5. Spaced Repetition")
    st.markdown("Revise o conteúdo em intervalos crescentes para melhorar a retenção.")

# ================================================================================
# 9. MAIN
# ================================================================================

def main():
    if 'tema' not in st.session_state:
        st.session_state['tema'] = 'claro'
    
    injetar_css_profissional()
    
    agora_brasilia = obter_horario_brasilia()
    data_hoje = agora_brasilia.strftime('%d/%m/%Y')
    hora_atual = agora_brasilia.strftime('%H:%M:%S')
    temperatura = obter_clima_local()

    # HEADER
    st.markdown("""
    <div class="header-container">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Logo Câmara Municipal">
        </div>
        <div>
            <h1 class="header-title">Dashboard de Estudos</h1>
            <p class="header-subtitle">Câmara Municipal de Goiânia</p>
        </div>
        <div class="header-info">
            <div class="info-item">📍 Goiânia - GO</div>
            <div class="info-item">📅 {data_hoje}</div>
            <div class="info-item">⏰ {hora_atual}</div>
            <div class="info-item">🌡️ {temperatura}</div>
        </div>
    </div>
    """.format(LOGO_URL=LOGO_URL, data_hoje=data_hoje, hora_atual=hora_atual, temperatura=temperatura), unsafe_allow_html=True)

    # SIDEBAR
    with st.sidebar:
        st.markdown("### 📋 SELEÇÃO DE CARGO")
        st.markdown("---")
        
        client = conectar_google_sheets()
        if not client:
            st.stop()
            
        df = carregar_dados(client)
        if df is None:
            st.warning("Carregando dados...")
            st.stop()
        
        lista_cargos = sorted(df['Cargo'].unique().tolist())
        cargo_selecionado = st.selectbox(
            "Escolha o cargo:",
            lista_cargos,
            help="Selecione o cargo para visualizar os dados",
            key="select_cargo"
        )
        
        st.markdown("---")
        st.info(f"**Cargo Selecionado:**\n\n{cargo_selecionado}")
        
        st.markdown("---")
        st.markdown("### ⚙️ Configurações")
        
        tema_atual = st.session_state['tema']
        if st.button(f"🌓 Tema: {tema_atual.title()}", use_container_width=True):
            st.session_state['tema'] = 'escuro' if tema_atual == 'claro' else 'claro'
            st.rerun()
        
        st.divider()
        
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.markdown("### 🎯 Técnicas de Estudo")
        if st.button("Pomodoro Timer", use_container_width=True):
            st.session_state['pagina'] = 'pomodoro'
            st.rerun()
        
        if st.button("Metodologias", use_container_width=True):
            st.session_state['pagina'] = 'metodologias'
            st.rerun()

    # FILTRO
    df_cargo = df[df['Cargo'] == cargo_selecionado].copy()
    df_cargo['linha_planilha'] = df_cargo.index + 2

    # MÉTRICAS
    total_topicos = len(df_cargo)
    total_concluidos = df_cargo['Estudado'].sum()
    total_restantes = total_topicos - total_concluidos
    progresso_percentual = (total_concluidos / total_topicos * 100) if total_topicos > 0 else 0
    streak_dias = calcular_streak(df_cargo)

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total de Tópicos</div>
            <div class="kpi-value">{total_topicos}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Concluídos</div>
            <div class="kpi-value" style="color: #059669;">{total_concluidos}</div>
            <div class="kpi-detail">{progresso_percentual:.1f}% do total</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Restantes</div>
            <div class="kpi-value" style="color: #dc2626;">{total_restantes}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Sequência Atual</div>
            <div class="kpi-value" style="color: #2563eb;">{streak_dias}</div>
            <div class="kpi-detail">dias consecutivos</div>
        </div>
        """, unsafe_allow_html=True)

    # SEPARADOR
    st.markdown("---")

    # PÁGINA PRINCIPAL OU POMODORO/METODOLOGIAS
    pagina = st.session_state.get('pagina', 'principal')
    
    if pagina == 'pomodoro':
        pomodoro_timer()
    elif pagina == 'metodologias':
        metodologias_estudo()
    else:
        # HEATMAP
        st.markdown("## 📊 Histórico de Atividades")
        
        grafico_heatmap = renderizar_heatmap(df_cargo)
        
        if grafico_heatmap:
            st.altair_chart(grafico_heatmap, use_container_width=True)
        else:
            st.info("Nenhum histórico disponível. Marque tópicos para visualizar seu heatmap estilo GitHub!")

        # SEPARADOR
        st.markdown("---")

        # PROGRESSO POR DISCIPLINA
        st.markdown("## 📈 Progresso por Disciplina")
        st.markdown("<hr style='border:none;border-top:1px solid rgba(148,163,184,0.4);margin:0.25rem auto 1rem auto;width:60%;'>", unsafe_allow_html=True)
        
        stats_disciplina = df_cargo.groupby('Disciplinas').agg({
            'Estudado': ['sum', 'count']
        }).reset_index()
        stats_disciplina.columns = ['Disciplina', 'Estudados', 'Total']
        
        # Gráfico de barras horizontal grande
        dados_grafico = []
        for _, row in stats_disciplina.iterrows():
            dados_grafico.append({
                'Disciplina': row['Disciplina'],
                'Status': 'Concluído',
                'Percentual': row['Estudados'] / row['Total'] * 100 if row['Total'] > 0 else 0
            })
            dados_grafico.append({
                'Disciplina': row['Disciplina'],
                'Status': 'Pendente',
                'Percentual': 100 - (row['Estudados'] / row['Total'] * 100) if row['Total'] > 0 else 0
            })
        
        df_grafico = pd.DataFrame(dados_grafico)
        
        chart = alt.Chart(df_grafico).mark_bar(size=20).encode(
            y=alt.Y('Disciplina:N', title=None, axis=alt.Axis(labelFontSize=12)),
            x=alt.X('Percentual:Q', title='Percentual', axis=alt.Axis(labelFontSize=10)),
            color=alt.Color('Status:N',
                           scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#16a34a', '#dc2626']),
                           legend=None),
            tooltip=[
                alt.Tooltip('Disciplina:N', title='Disciplina'),
                alt.Tooltip('Percentual:Q', title='Percentual', format='.1f')
            ]
        ).properties(
            height=280,
            width='container'
        ).configure_axis(
            grid=False
        )
        
        st.altair_chart(chart, use_container_width=True)

        # SEPARADOR
        st.markdown("---")

        # DONUTS
        st.markdown("## 🍩 Progresso por Disciplina")
        
        cols = st.columns(min(3, len(stats_disciplina)))
        
        for idx, row in stats_disciplina.iterrows():
            col_idx = cols[idx % len(cols)]
            
            with col_idx:
                nome_disciplina = row['Disciplina']
                cor_tema = CORES_DISCIPLINAS.get(nome_disciplina, '#2563eb')
                
                st.markdown(f"""
                <div class="donut-wrapper">
                    <div class="donut-title">{nome_disciplina}</div>
                    <div class="donut-stats">{row["Estudados"]} de {row["Total"]} tópicos</div>
                </div>
                """, unsafe_allow_html=True)
                
                chart_donut = renderizar_donut(row['Estudados'], row['Total'], cor_tema)
                st.altair_chart(chart_donut, use_container_width=True)

        # SEPARADOR
        st.markdown("---")

        # CHECKLIST
        st.markdown("## ✓ Conteúdo Programático")

        for disciplina in sorted(df_cargo['Disciplinas'].unique()):
            sub_df = df_cargo[df_cargo['Disciplinas'] == disciplina]
            cor_tema = CORES_DISCIPLINAS.get(disciplina, '#2563eb')
            
            concluidos = sub_df['Estudado'].sum()
            total = len(sub_df)
            percentual = (concluidos / total * 100) if total > 0 else 0
            
            with st.expander(f"**{disciplina}** ({concluidos}/{total})", expanded=False):
                st.markdown(f"""
                <div class="progress-info">
                    <span class="progress-label">{disciplina}</span>
                    <span class="progress-percentage">{percentual:.1f}%</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" style="width: {percentual}%; background: {cor_tema};"></div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form(key=f"form_{disciplina}"):
                    updates_pendentes = []
                    
                    for _, row in sub_df.iterrows():
                        col_check, col_texto = st.columns([0.05, 0.95])
                        
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
                            data_str = row['Data_Real'].strftime('%d/%m/%Y')
                            badge_data_html = f"<span class='topic-date'>{data_str}</span>"
                        
                        col_texto.markdown(f"""
                        <div class="topic-item">
                            <div class="topic-text {classe_css}">
                                {row['Conteúdos']}
                            </div>
                            {badge_data_html}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    submitted = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                    
                    if submitted and updates_pendentes:
                        with st.spinner("Salvando..."):
                            sucesso = atualizar_lote(client, updates_pendentes)
                            
                            if sucesso:
                                st.success("✅ Alterações salvas!")
                                time.sleep(1)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("❌ Erro ao salvar")

    # SEPARADOR
    st.markdown("---")

    # RODAPÉ
    st.markdown(f"""
    <div style="text-align: center; color: #94a3b8; padding: 1rem 0; font-size: 0.813rem;">
        Dashboard v5.0 • Horário de Brasília: {agora_brasilia.strftime("%d/%m/%Y às %H:%M:%S")}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
