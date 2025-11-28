#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 DASHBOARD DE ESTUDOS - CÂMARA MUNICIPAL DE GOIÂNIA
================================================================================
VERSÃO: 6.0 - LAYOUT FINAL
DATA: 2025-11-28 15:57

FUNCIONALIDADES:
✓ Header: Logo à esquerda (95% altura), título centralizado, info à direita
✓ Sidebar com configurações
✓ Cards de progresso com donuts integrados
✓ Sem Pomodoro, sem tabs
✓ Layout limpo e profissional
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

def calcular_insights_revisao(df: pd.DataFrame) -> str:
    """Calcula insights sobre qual matéria revisar"""
    df_estudado = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    
    if df_estudado.empty:
        return "Comece a estudar para receber insights personalizados!"
    
    hoje = datetime.now()
    df_estudado['dias_desde_estudo'] = (hoje - df_estudado['Data_Real']).dt.days
    
    revisao_disciplina = df_estudado.groupby('Disciplinas').agg({
        'dias_desde_estudo': 'min'
    }).reset_index()
    
    urgente = revisao_disciplina[revisao_disciplina['dias_desde_estudo'] > 7].sort_values('dias_desde_estudo', ascending=False)
    
    if not urgente.empty:
        disciplina = urgente.iloc[0]['Disciplinas']
        dias = int(urgente.iloc[0]['dias_desde_estudo'])
        return f"⚠️ **Revisar urgentemente:** {disciplina} (última revisão há {dias} dias)"
    else:
        proxima = revisao_disciplina.sort_values('dias_desde_estudo', ascending=False).iloc[0]
        disciplina = proxima['Disciplinas']
        dias = int(proxima['dias_desde_estudo'])
        return f"✅ **Próxima revisão:** {disciplina} (estudada há {dias} dias)"

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
    else:
        bg_main = '#f8fafc'
        bg_card = '#ffffff'
        text_main = '#1e293b'
        text_secondary = '#64748b'
        border_color = '#e2e8f0'
        hover_bg = '#f1f5f9'
    
    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{
            font-family: 'Nunito', sans-serif;
            box-sizing: border-box;
        }}

        [data-testid="stMainBlockContainer"] {{
            background-color: {bg_main};
            color: {text_main};
            padding: 2rem;
            max-width: 1600px;
            margin: 0 auto;
        }}

        #MainMenu, footer, header {{visibility: hidden;}}

        /* HEADER */
        .header-container {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 1rem 2rem;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            height: 120px;
        }}

        .header-left {{
            flex: 0 0 25%;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            height: 100%;
        }}

        .header-logo {{
            height: 95%;
            width: auto;
            object-fit: contain;
        }}

        .header-center {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
        }}

        .header-title {{
            font-size: 2rem;
            font-weight: 800;
            color: {text_main};
            margin: 0;
            text-align: center;
        }}

        .header-right {{
            flex: 0 0 25%;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            justify-content: center;
            gap: 0.25rem;
        }}

        .info-text {{
            font-size: 1.1rem;
            font-weight: 600;
            color: {text_secondary};
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

        /* CONTAINER GRÁFICOS */
        .chart-container {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .chart-title {{
            font-size: 1rem;
            font-weight: 700;
            color: {text_main};
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .chart-subtitle {{
            font-size: 0.875rem;
            color: {text_secondary};
            margin-bottom: 1rem;
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

        /* INSIGHT BOX */
        .insight-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}

        .insight-box h3 {{
            margin: 0 0 0.5rem 0;
            font-size: 1.1rem;
            font-weight: 700;
        }}

        .insight-box p {{
            margin: 0;
            font-size: 0.95rem;
            line-height: 1.6;
        }}

        /* RESPONSIVO */
        @media (max-width: 768px) {{
            .header-container {{
                flex-direction: column;
                gap: 1rem;
                padding: 1rem;
                height: auto;
            }}

            .header-title {{
                font-size: 1.5rem;
            }}

            .header-logo {{
                max-height: 80px;
            }}

            .header-right {{
                align-items: center;
            }}

            [data-testid="stMainBlockContainer"] {{
                padding: 1rem;
            }}
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
                title=None,
                axis=alt.Axis(
                    format='%d/%m',
                    labelAngle=0,
                    labelFontSize=10,
                    labelColor='#64748b'
                )
        ),
        y=alt.Y('day(Data_Real):O',
                title=None,
                axis=alt.Axis(
                    labels=False,
                    ticks=False
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
        domain=False
    )
    
    return chart

def renderizar_donut(concluido: int, total: int) -> alt.Chart:
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
                                        range=['#1e7e34', '#991b1b']),
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
# 7. MAIN
# ================================================================================

def main():
    if 'tema' not in st.session_state:
        st.session_state['tema'] = 'claro'
    
    injetar_css_profissional()
    
    agora_brasilia = obter_horario_brasilia()
    
    # Formatar data como "28/Nov"
    meses = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }
    data_formatada = f"{agora_brasilia.day}/{meses[agora_brasilia.month]}"
    temperatura = obter_clima_local()

    # SIDEBAR
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        
        tema_atual = st.session_state['tema']
        if st.button(f"🌓 Alternar Tema ({tema_atual.title()})", use_container_width=True):
            st.session_state['tema'] = 'escuro' if tema_atual == 'claro' else 'claro'
            st.rerun()
        
        st.divider()
        
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # HEADER
    st.markdown(f"""
    <div class="header-container">
        <div class="header-left">
            <img src="{LOGO_URL}" alt="Logo" class="header-logo">
        </div>
        <div class="header-center">
            <div class="header-title">Dashboard de Estudos</div>
        </div>
        <div class="header-right">
            <div class="info-text">Goiânia, GO</div>
            <div class="info-text">{data_formatada}</div>
            <div class="info-text">{temperatura}</div>
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

    # SELEÇÃO DE CARGO
    lista_cargos = sorted(df['Cargo'].unique().tolist())
    
    st.markdown("### 📋 Selecione o Cargo")
    cargo_selecionado = st.selectbox(
        "Cargo:",
        lista_cargos,
        label_visibility="collapsed"
    )

    # FILTRO
    df_cargo = df[df['Cargo'] == cargo_selecionado].copy()
    df_cargo['linha_planilha'] = df_cargo.index + 2

    # MÉTRICAS
    total_topicos = len(df_cargo)
    total_concluidos = df_cargo['Estudado'].sum()
    total_restantes = total_topicos - total_concluidos
    progresso_percentual = (total_concluidos / total_topicos * 100) if total_topicos > 0 else 0
    streak_dias = calcular_streak(df_cargo)

    # INSIGHTS
    insight = calcular_insights_revisao(df_cargo)
    st.markdown(f"""
    <div class="insight-box">
        <h3>💡 Insight Personalizado</h3>
        <p>{insight}</p>
    </div>
    """, unsafe_allow_html=True)

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
            <div class="kpi-value" style="color: #1e7e34;">{total_concluidos}</div>
            <div class="kpi-detail">{progresso_percentual:.1f}% do total</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Restantes</div>
            <div class="kpi-value" style="color: #991b1b;">{total_restantes}</div>
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

    st.markdown("---")

    # HEATMAP
    st.markdown("## 📊 Histórico de Atividades")
    
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    
    grafico_heatmap = renderizar_heatmap(df_cargo)
    
    if grafico_heatmap:
        st.altair_chart(grafico_heatmap, use_container_width=True)
    else:
        st.info("Nenhum histórico disponível.")
        
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # PROGRESSO POR DISCIPLINA
    st.markdown("## 📈 Progresso de Estudos")
    
    stats_disciplina = df_cargo.groupby('Disciplinas').agg({
        'Estudado': ['sum', 'count']
    }).reset_index()
    stats_disciplina.columns = ['Disciplina', 'Estudados', 'Total']
    
    # Grid de cards
    num_cols = len(stats_disciplina) + 1  # +1 para gráfico geral
    cols = st.columns(min(4, num_cols))
    
    # Card Geral
    with cols[0]:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">📊 Progresso Geral</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-subtitle">{total_concluidos} de {total_topicos} tópicos</div>', unsafe_allow_html=True)
        chart_geral = renderizar_donut(total_concluidos, total_topicos)
        st.altair_chart(chart_geral, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Cards por Disciplina
    for idx, row in stats_disciplina.iterrows():
        col_idx = cols[(idx + 1) % len(cols)]
        
        with col_idx:
            nome_disciplina = row['Disciplina']
            
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-title">{nome_disciplina}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chart-subtitle">{row["Estudados"]} de {row["Total"]} tópicos</div>', unsafe_allow_html=True)
            
            chart_donut = renderizar_donut(row['Estudados'], row['Total'])
            st.altair_chart(chart_donut, use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

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

    st.markdown("---")

    # RODAPÉ
    st.markdown(f"""
    <div style="text-align: center; color: #94a3b8; padding: 1rem 0; font-size: 0.813rem;">
        Dashboard v6.0 • {agora_brasilia.strftime("%d/%m/%Y às %H:%M:%S")}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
