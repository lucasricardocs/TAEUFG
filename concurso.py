#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 DASHBOARD DE ESTUDOS - CÂMARA MUNICIPAL DE GOIÂNIA
================================================================================
VERSÃO: 7.1 - CORREÇÃO DE ERROS E DEPENDÊNCIAS
DATA: 2025-11-28 17:40
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

# Tenta configurar data para português, mas não falha se não conseguir
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

# Cores
COR_CONCLUIDO = '#15803d'  # Verde Escuro
COR_PENDENTE = '#b91c1c'   # Vermelho Escuro
COR_AZUL_CTA = '#2563eb'

# ================================================================================
# 3. FUNÇÕES UTILITÁRIAS (Backend)
# ================================================================================

def obter_horario_brasilia():
    """Retorna datetime atual no fuso de Brasília (UTC-3) sem depender de pytz"""
    # Pega hora UTC e subtrai 3 horas
    return datetime.utcnow() - timedelta(hours=3)

def obter_clima_local() -> str:
    """Pega temperatura de Goiânia"""
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
        return "--"
    return "--"

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
        st.error(f"Erro de Conexão com Planilha: {e}")
        return None

@st.cache_data(ttl=10)
def carregar_dados(_client) -> Optional[pd.DataFrame]:
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        dados_raw = ws.get_all_records()
        df = pd.DataFrame(dados_raw)
        
        if df.empty: return None
        
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
        agora = obter_horario_brasilia()
        
        for update in updates:
            linha = update['linha']
            status = 'TRUE' if update['status'] else 'FALSE'
            data = agora.strftime('%d/%m/%Y') if update['status'] else ''
            ws.update(f"D{linha}:E{linha}", [[status, data]])
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def calcular_insights_revisao(df: pd.DataFrame) -> str:
    df_estudado = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    if df_estudado.empty:
        return "Comece a estudar para receber insights!"
    
    hoje = datetime.now() # Usa data local do servidor para calculo relativo
    df_estudado['dias'] = (hoje - df_estudado['Data_Real']).dt.days
    
    agrupado = df_estudado.groupby('Disciplinas')['dias'].min().reset_index()
    urgente = agrupado[agrupado['dias'] > 7].sort_values('dias', ascending=False)
    
    if not urgente.empty:
        disc = urgente.iloc[0]['Disciplinas']
        dias = int(urgente.iloc[0]['dias'])
        return f"⚠️ **Revisar urgentemente:** {disc} (há {dias} dias sem estudo)"
    
    return "✅ **Ciclo de revisão em dia!** Continue assim."

# ================================================================================
# 4. FUNÇÕES VISUAIS (CSS e Gráficos)
# ================================================================================

def injetar_css_profissional():
    tema = st.session_state.get('tema', 'claro')
    
    if tema == 'escuro':
        bg_main, bg_card, text_main, text_sec, border = '#0f172a', '#1e293b', '#f1f5f9', '#94a3b8', '#334155'
        header_bg = 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)'
        shadow = '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
    else:
        bg_main, bg_card, text_main, text_sec, border = '#f8fafc', '#ffffff', '#1e293b', '#64748b', '#e2e8f0'
        header_bg = 'linear-gradient(135deg, #f8fafc 0%, #e0e7ff 50%, #dbeafe 100%)'
        shadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)'

    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ font-family: 'Nunito', sans-serif !important; box-sizing: border-box; }}
        [data-testid="stMainBlockContainer"] {{ background-color: {bg_main}; color: {text_main}; padding: 2rem; max-width: 1600px; margin: 0 auto; }}
        #MainMenu, footer, header {{ visibility: hidden; }}

        /* HEADER 300PX */
        .header-container {{
            background: {header_bg}; border: 1px solid {border}; border-radius: 24px;
            padding: 0 3rem; margin-bottom: 3rem; display: flex; align-items: center;
            justify-content: space-between; box-shadow: {shadow}; height: 300px; position: relative;
        }}
        .header-left {{ flex: 0 0 30%; height: 100%; display: flex; align-items: center; z-index: 2; }}
        .header-logo {{ height: 90%; width: auto; object-fit: contain; }}
        .header-center {{ position: absolute; left: 0; right: 0; top: 0; bottom: 0; display: flex; align-items: center; justify-content: center; pointer-events: none; z-index: 1; }}
        .header-title {{ font-size: 3rem; font-weight: 800; color: {text_main}; text-align: center; text-transform: uppercase; }}
        .header-right {{ flex: 0 0 30%; height: 100%; display: flex; flex-direction: column; align-items: flex-end; padding-top: 2rem; z-index: 2; }}
        
        .info-pill {{
            background: rgba(255,255,255,0.6); backdrop-filter: blur(8px); padding: 0.75rem 1.25rem;
            border-radius: 12px; display: flex; gap: 1rem; font-weight: 700; font-size: 1.1rem; color: {text_sec};
        }}

        /* CARDS */
        .card-wrapper {{
            background-color: {bg_card}; border-radius: 20px; border: 1px solid {border};
            box-shadow: {shadow}; padding: 2rem 1rem; height: 100%; min-height: 400px;
            display: flex; flex-direction: column; align-items: center;
        }}
        .card-title {{ font-size: 1.1rem; font-weight: 800; color: {text_main}; text-align: center; margin-bottom: 0.5rem; text-transform: uppercase; min-height: 3.5rem; display: flex; align-items: center; }}
        .card-subtitle {{ font-size: 0.9rem; color: {text_sec}; font-weight: 600; margin-bottom: 1.5rem; background: {bg_main}; padding: 0.25rem 0.75rem; border-radius: 20px; }}

        /* KPI */
        .kpi-box {{ background-color: {bg_card}; border: 1px solid {border}; border-radius: 16px; padding: 1.5rem; text-align: center; box-shadow: {shadow}; }}
        .kpi-label {{ font-size: 0.85rem; font-weight: 700; color: {text_sec}; text-transform: uppercase; }}
        .kpi-value {{ font-size: 2.5rem; font-weight: 800; color: {text_main}; margin: 0.5rem 0; }}
        
        /* CHECKLIST */
        .stExpander {{ background-color: {bg_card}; border-radius: 12px; border: 1px solid {border}; margin-bottom: 1rem; }}
        .topic-row {{ display: flex; align-items: center; padding: 0.75rem; border-bottom: 1px solid {border}; }}
        .topic-row:hover {{ background-color: {bg_main}; }}
        .topic-content {{ flex: 1; margin-left: 1rem; font-size: 0.95rem; color: {text_main}; }}
        .topic-done {{ text-decoration: line-through; color: {text_sec}; }}
        .topic-date {{ font-size: 0.75rem; font-weight: 700; background: {COR_AZUL_CTA}; color: white; padding: 2px 8px; border-radius: 4px; }}

        @media (max-width: 992px) {{
            .header-container {{ height: auto; flex-direction: column; padding: 2rem; gap: 1.5rem; }}
            .header-center {{ position: static; }}
            .header-left, .header-right {{ width: 100%; justify-content: center; align-items: center; }}
            .header-logo {{ height: 80px; }}
            .header-title {{ font-size: 2rem; }}
        }}
    </style>
    """, unsafe_allow_html=True)

def renderizar_donut(concluido: int, total: int) -> alt.Chart:
    restante = total - concluido
    source = pd.DataFrame({
        'Category': ['Concluído', 'Pendente'],
        'Value': [concluido, restante]
    })
    
    base = alt.Chart(source).encode(theta=alt.Theta("Value:Q", stack=True))
    
    pie = base.mark_arc(outerRadius=100, innerRadius=75, cornerRadius=5).encode(
        color=alt.Color("Category:N", scale=alt.Scale(domain=['Concluído', 'Pendente'], range=[COR_CONCLUIDO, COR_PENDENTE]), legend=None),
        order=alt.Order("Category", sort="descending"),
        tooltip=["Category", "Value"]
    )
    
    bg = base.mark_arc(outerRadius=100, innerRadius=75, color='#f1f5f9').encode(order=alt.value(0))
    pct = int(concluido/total*100) if total > 0 else 0
    text = base.mark_text(radius=0, size=36, color='#334155', fontWeight=800, font='Nunito').encode(text=alt.value(f"{pct}%"))
    
    return (bg + pie + text).properties(width=220, height=220, background='transparent').configure_view(strokeWidth=0)

def renderizar_heatmap(df: pd.DataFrame) -> Optional[alt.Chart]:
    df_validos = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    if df_validos.empty: return None
    
    dados = df_validos.groupby('Data_Real').size().reset_index(name='Qtd')
    return alt.Chart(dados).mark_rect(cornerRadius=4, stroke='white', strokeWidth=2).encode(
        x=alt.X('yearmonthdate(Data_Real):O', title=None, axis=alt.Axis(format='%d/%m', labelFontSize=10)),
        y=alt.Y('day(Data_Real):O', title=None, axis=alt.Axis(labels=False, ticks=False, domain=False)),
        color=alt.Color('Qtd:Q', scale=alt.Scale(range=['#dcfce7', '#166534']), legend=None),
        tooltip=[alt.Tooltip('Data_Real', title='Data', format='%d/%m'), alt.Tooltip('Qtd', title='Tópicos')]
    ).properties(height=180, width='container').configure_view(strokeWidth=0).configure_axis(grid=False)

# ================================================================================
# 5. MAIN
# ================================================================================

def main():
    if 'tema' not in st.session_state: st.session_state['tema'] = 'claro'
    injetar_css_profissional()
    
    agora = obter_horario_brasilia()
    meses = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
    data_txt = f"{agora.day}/{meses[agora.month]}"
    clima = obter_clima_local()

    # SIDEBAR
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        if st.button("🌓 Alternar Tema", use_container_width=True):
            st.session_state['tema'] = 'escuro' if st.session_state['tema'] == 'claro' else 'claro'
            st.rerun()
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # HEADER
    st.markdown(f"""
    <div class="header-container">
        <div class="header-left">
            <img src="{LOGO_URL}" class="header-logo">
        </div>
        <div class="header-center">
            <div class="header-title">Dashboard de Estudos</div>
        </div>
        <div class="header-right">
            <div class="info-pill">
                <span>📍 Goiânia, GO</span>
                <span>📅 {data_txt}</span>
                <span>🌡️ {clima}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # DADOS
    client = conectar_google_sheets()
    if not client: st.stop()
    df = carregar_dados(client)
    if df is None: st.warning("Carregando planilha..."); st.stop()

    # FILTRO
    cargos = sorted(df['Cargo'].unique().tolist())
    st.markdown("### 📋 Seleção de Cargo")
    cargo_sel = st.selectbox("Cargo", cargos, label_visibility="collapsed")
    df_filtro = df[df['Cargo'] == cargo_sel].copy()
    df_filtro['linha_planilha'] = df_filtro.index + 2

    # KPI
    total = len(df_filtro)
    feito = df_filtro['Estudado'].sum()
    restante = total - feito
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-box"><div class="kpi-label">Total</div><div class="kpi-value">{total}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-box"><div class="kpi-label">Feito</div><div class="kpi-value" style="color:{COR_CONCLUIDO}">{feito}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-box"><div class="kpi-label">Falta</div><div class="kpi-value" style="color:{COR_PENDENTE}">{restante}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-box"><div class="kpi-label">Status</div><div style="margin-top:1rem; font-weight:600">{calcular_insights_revisao(df_filtro)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # HEATMAP
    st.markdown("### 📅 Histórico")
    heat = renderizar_heatmap(df_filtro)
    if heat: st.altair_chart(heat, use_container_width=True)
    else: st.info("Sem dados.")

    st.markdown("---")

    # CARDS COM DONUTS
    st.markdown("### 📈 Progresso por Matéria")
    stats = df_filtro.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
    stats.columns = ['Disciplina', 'Feito', 'Total']
    
    cards_data = [{'Disciplina': 'GERAL', 'Feito': feito, 'Total': total}]
    for _, r in stats.iterrows(): cards_data.append(r.to_dict())
    
    cols = st.columns(3)
    for i, c in enumerate(cards_data):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="card-wrapper">
                <div class="card-title">{c['Disciplina']}</div>
                <div class="card-subtitle">{c['Feito']} de {c['Total']} tópicos</div>
            """, unsafe_allow_html=True)
            st.altair_chart(renderizar_donut(c['Feito'], c['Total']), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # CHECKLIST
    st.markdown("### ✓ Conteúdo")
    for materia in sorted(df_filtro['Disciplinas'].unique()):
        sub = df_filtro[df_filtro['Disciplinas'] == materia]
        done = sub['Estudado'].sum()
        tot = len(sub)
        
        with st.expander(f"**{materia}** ({done}/{tot})"):
            with st.form(key=f"f_{materia}"):
                updates = []
                for _, r in sub.iterrows():
                    c, t = st.columns([0.05, 0.95])
                    chk = c.checkbox("", value=bool(r['Estudado']), key=f"c_{r['linha_planilha']}")
                    if chk != bool(r['Estudado']): updates.append({'linha': int(r['linha_planilha']), 'status': chk})
                    
                    cls = "topic-done" if r['Estudado'] else ""
                    bdg = f"<span class='topic-date'>{r['Data_Real'].strftime('%d/%m')}</span>" if r['Estudado'] and pd.notnull(r['Data_Real']) else ""
                    t.markdown(f"<div class='topic-row'><div class='topic-content {cls}'>{r['Conteúdos']}</div>{bdg}</div>", unsafe_allow_html=True)
                
                if st.form_submit_button("Salvar"):
                    if updates:
                        if atualizar_lote(client, updates):
                            st.success("Salvo!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                        else: st.error("Erro")

    st.markdown(f"<div style='text-align:center; color:#94a3b8; padding:2rem 0;'>Atualizado: {agora.strftime('%d/%m %H:%M')}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
