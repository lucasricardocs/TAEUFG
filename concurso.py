#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 DASHBOARD DE ESTUDOS - CÂMARA MUNICIPAL DE GOIÂNIA
================================================================================
VERSÃO: 4.1 - PROFISSIONAL INTERATIVO
DATA: 2025-11-28 00:12

MELHORIAS v4.1:
✓ Containers expansíveis por disciplina
✓ Barra de progresso horizontal em cada matéria
✓ Hover effects sutis e profissionais
✓ Seleção de cargo na sidebar
✓ Design responsivo com width controlado
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

# Paleta Profissional
CORES_DISCIPLINAS = {
    'LÍNGUA PORTUGUESA': '#2563eb',
    'RLM': '#059669',
    'REALIDADE DE GOIÁS': '#7c3aed',
    'LEGISLAÇÃO APLICADA': '#dc2626',
    'CONHECIMENTOS ESPECÍFICOS': '#ea580c'
}

# ================================================================================
# 3. CSS PROFISSIONAL COM HOVER
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
    else:
        bg_main = '#f8fafc'
        bg_card = '#ffffff'
        text_main = '#1e293b'
        text_secondary = '#64748b'
        border_color = '#e2e8f0'
        hover_bg = '#f1f5f9'
    
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        * {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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

        /* HEADER PROFISSIONAL */
        .header-container {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .header-container:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }}

        .header-left {{
            display: flex;
            align-items: center;
            gap: 2rem;
        }}

        .header-logo img {{
            max-width: 220px;
            height: auto;
            transition: transform 0.3s ease;
        }}

        .header-logo img:hover {{
            transform: scale(1.05);
        }}

        .header-title {{
            font-size: 1.5rem;
            font-weight: 700;
            color: {text_main};
            margin: 0;
        }}

        .header-subtitle {{
            font-size: 0.875rem;
            color: {text_secondary};
            margin-top: 0.25rem;
        }}

        .header-info {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            text-align: right;
        }}

        .info-item {{
            font-size: 0.813rem;
            color: {text_secondary};
            font-weight: 500;
            transition: color 0.2s ease;
        }}

        .info-item:hover {{
            color: {text_main};
        }}

        /* CONTAINERS COM WIDTH */
        .content-wrapper {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        /* KPI CARDS COM HOVER */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .kpi-card {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 1.5rem;
            transition: all 0.3s ease;
            cursor: pointer;
        }}

        .kpi-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            border-color: #2563eb;
        }}

        .kpi-label {{
            font-size: 0.813rem;
            font-weight: 600;
            color: {text_secondary};
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}

        .kpi-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {text_main};
            line-height: 1;
        }}

        .kpi-detail {{
            font-size: 0.875rem;
            color: {text_secondary};
            margin-top: 0.5rem;
        }}

        /* SECTIONS COM HOVER */
        .section {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            transition: box-shadow 0.2s ease;
        }}

        .section:hover {{
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        }}

        .section-title {{
            font-size: 1.125rem;
            font-weight: 700;
            color: {text_main};
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid {border_color};
        }}

        /* PROGRESS BAR HORIZONTAL */
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

        /* EXPANDER CUSTOMIZADO */
        .streamlit-expanderHeader {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.2s ease;
        }}

        .streamlit-expanderHeader:hover {{
            background: {hover_bg};
            border-color: #2563eb;
        }}

        /* TOPIC ITEM COM HOVER */
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

        .topic-checkbox {{
            margin-right: 0.75rem;
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

        /* DONUT GRID */
        .donut-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }}

        .donut-item {{
            text-align: center;
            transition: transform 0.2s ease;
        }}

        .donut-item:hover {{
            transform: scale(1.05);
        }}

        .donut-title {{
            font-size: 0.938rem;
            font-weight: 600;
            color: {text_main};
            margin-bottom: 1rem;
        }}

        /* RESPONSIVO */
        @media (max-width: 768px) {{
            .header-container {{
                flex-direction: column;
                gap: 1.5rem;
            }}

            .header-left {{
                flex-direction: column;
                text-align: center;
            }}

            .header-info {{
                text-align: center;
            }}

            .kpi-grid {{
                grid-template-columns: 1fr;
            }}

            [data-testid="stMainBlockContainer"] {{
                padding: 1rem;
            }}
        }}
    </style>
    """, unsafe_allow_html=True)

# ================================================================================
# 4. BACKEND
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
        
        for update in updates:
            linha = update['linha']
            status = 'TRUE' if update['status'] else 'FALSE'
            data = datetime.now().strftime('%d/%m/%Y') if update['status'] else ''
            
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
# 5. VISUALIZAÇÃO
# ================================================================================

def renderizar_heatmap(df: pd.DataFrame) -> Optional[alt.Chart]:
    df_validos = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    
    if df_validos.empty:
        return None
        
    dados_heatmap = df_validos.groupby('Data_Real').size().reset_index(name='count')
    
    chart = alt.Chart(dados_heatmap).mark_rect(
        cornerRadius=2,
        stroke='white',
        strokeWidth=1
    ).encode(
        x=alt.X('yearmonthdate(Data_Real):O',
                title='Data',
                axis=alt.Axis(format='%d/%m', labelAngle=0, labelFontSize=10)
        ),
        y=alt.Y('day(Data_Real):O',
                title='Dia da Semana',
                axis=alt.Axis(labelFontSize=10)
        ),
        color=alt.Color('count:Q',
                        scale=alt.Scale(scheme='blues'),
                        legend=alt.Legend(title='Conteúdos')
        ),
        tooltip=[
            alt.Tooltip('Data_Real', title='Data', format='%d/%m/%Y'),
            alt.Tooltip('count', title='Conteúdos')
        ]
    ).properties(
        height=200,
        width='container'
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
        outerRadius=60,
        innerRadius=40,
        stroke='white',
        strokeWidth=2
    ).encode(
        color=alt.Color("Status:N",
                        scale=alt.Scale(domain=['Concluído', 'Pendente'],
                                        range=[cor_hex, '#e2e8f0']),
                        legend=None),
        tooltip=[
            alt.Tooltip('Status:N', title='Status'),
            alt.Tooltip('Valor:Q', title='Quantidade')
        ]
    )
    
    pct = int(concluido/total*100) if total > 0 else 0
    texto = base.mark_text(
        radius=0,
        size=18,
        color='#1e293b',
        fontWeight='bold',
        font='Inter'
    ).encode(
        text=alt.value(f"{pct}%")
    )
    
    return (pie + texto).properties(width=140, height=140)

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
# 6. MAIN
# ================================================================================

def main():
    if 'tema' not in st.session_state:
        st.session_state['tema'] = 'claro'
    
    injetar_css_profissional()
    
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    hora_atual = datetime.now().strftime('%H:%M')
    temperatura = obter_clima_local()

    # HEADER
    st.markdown(f"""
    <div class="header-container">
        <div class="header-left">
            <div class="header-logo">
                <img src="{LOGO_URL}" alt="Logo Câmara Municipal">
            </div>
            <div>
                <h1 class="header-title">Dashboard de Estudos</h1>
                <p class="header-subtitle">Câmara Municipal de Goiânia</p>
            </div>
        </div>
        <div class="header-info">
            <div class="info-item">📍 Goiânia - GO</div>
            <div class="info-item">📅 {data_hoje} • {hora_atual}</div>
            <div class="info-item">🌡️ {temperatura}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # CONEXÃO
    client = conectar_google_sheets()
    if not client:
        st.stop()
        
    df = carregar_dados(client)
    if df is None:
        st.warning("Carregando dados...")
        st.stop()

    # SIDEBAR - SELEÇÃO DE CARGO
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        
        # Seleção de Cargo
        lista_cargos = sorted(df['Cargo'].unique().tolist())
        cargo_selecionado = st.selectbox(
            "📋 Selecione o Cargo:",
            lista_cargos,
            help="Escolha o cargo para visualizar os dados específicos"
        )
        
        st.divider()
        
        # Toggle Tema
        tema_atual = st.session_state['tema']
        if st.button(f"🌓 Tema: {tema_atual.title()}", use_container_width=True):
            st.session_state['tema'] = 'escuro' if tema_atual == 'claro' else 'claro'
            st.rerun()
        
        st.divider()
        
        # Atualizar
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.caption(f"**Cargo Atual:** {cargo_selecionado}")
        st.caption("v4.1 - Profissional")

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
    st.markdown('<div class="content-wrapper">', unsafe_allow_html=True)
    
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

    # HEATMAP
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Histórico de Atividades</div>', unsafe_allow_html=True)
    
    grafico_heatmap = renderizar_heatmap(df_cargo)
    
    if grafico_heatmap:
        st.altair_chart(grafico_heatmap, use_container_width=True)
    else:
        st.info("Nenhum histórico disponível. Marque tópicos para visualizar.")
        
    st.markdown('</div>', unsafe_allow_html=True)

    # PROGRESSO POR DISCIPLINA
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📈 Progresso por Disciplina</div>', unsafe_allow_html=True)
    
    stats_disciplina = df_cargo.groupby('Disciplinas').agg({
        'Estudado': ['sum', 'count']
    }).reset_index()
    stats_disciplina.columns = ['Disciplina', 'Estudados', 'Total']
    
    cols = st.columns(min(3, len(stats_disciplina)))
    
    for idx, row in stats_disciplina.iterrows():
        col_idx = cols[idx % len(cols)]
        
        with col_idx:
            nome_disciplina = row['Disciplina']
            cor_tema = CORES_DISCIPLINAS.get(nome_disciplina, '#2563eb')
            
            st.markdown(f'<div class="donut-title">{nome_disciplina}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align:center; font-size:0.875rem; color:#64748b; margin-bottom:0.5rem;">{row["Estudados"]} de {row["Total"]} tópicos</div>', unsafe_allow_html=True)
            
            chart_donut = renderizar_donut(row['Estudados'], row['Total'], cor_tema)
            st.altair_chart(chart_donut, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # CHECKLIST COM EXPANDERS E PROGRESS BAR
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">✓ Conteúdo Programático</div>', unsafe_allow_html=True)

    # Para cada disciplina, criar um expander
    for disciplina in sorted(df_cargo['Disciplinas'].unique()):
        sub_df = df_cargo[df_cargo['Disciplinas'] == disciplina]
        cor_tema = CORES_DISCIPLINAS.get(disciplina, '#2563eb')
        
        concluidos = sub_df['Estudado'].sum()
        total = len(sub_df)
        percentual = (concluidos / total * 100) if total > 0 else 0
        
        with st.expander(f"**{disciplina}** ({concluidos}/{total})", expanded=False):
            # PROGRESS BAR HORIZONTAL
            st.markdown(f"""
            <div class="progress-info">
                <span class="progress-label">{disciplina}</span>
                <span class="progress-percentage">{percentual:.1f}%</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: {percentual}%; background: {cor_tema};"></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # FORM COM CHECKBOXES
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
                            st.success("✅ Alterações salvas com sucesso!")
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar alterações")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # RODAPÉ
    st.markdown(f"""
    <div style="text-align: center; color: #94a3b8; padding: 2rem 0 1rem 0; font-size: 0.813rem; border-top: 1px solid #e2e8f0; margin-top: 2rem;">
        Dashboard de Estudos v4.1 • Última atualização: {datetime.now().strftime("%d/%m/%Y às %H:%M:%S")}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
