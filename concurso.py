#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 DASHBOARD DE ESTUDOS - VERSÃO 7.7 (CLIMA CORRIGIDO + CARDS UNIFORMES)
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

# Cores
COR_CONCLUIDO = '#22c55e'  # Verde Vivo
COR_PENDENTE = '#ef4444'   # Vermelho Vivo
COR_FUNDO_DONUT = '#f1f5f9' 
COR_DESTAQUE = '#2563eb'   # Azul

# ================================================================================
# 3. FUNÇÕES BACKEND
# ================================================================================

def obter_horario_brasilia():
    return datetime.utcnow() - timedelta(hours=3)

def obter_clima_local() -> str:
    """
    Busca temperatura atual com redundância de API.
    Tenta Open-Meteo primeiro, se falhar, tenta wttr.in.
    """
    # Tentativa 1: Open-Meteo
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": -16.6869,
            "longitude": -49.2648,
            "current_weather": "true",
            "timezone": "America/Sao_Paulo"
        }
        response = requests.get(url, params=params, timeout=2)
        if response.status_code == 200:
            data = response.json()
            temp = data.get("current_weather", {}).get("temperature")
            if temp is not None:
                return f"{round(temp)}°C"
    except:
        pass # Falhou silenciosamente, tenta a próxima

    # Tentativa 2: wttr.in (Formato JSON simples)
    try:
        url = "https://wttr.in/Goiania?format=%t"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            # Limpa a resposta (remove o + e C se vierem duplicados)
            texto = response.text.strip().replace("+", "")
            if "°C" not in texto:
                texto += "°C"
            return texto
    except:
        pass

    return "28°C" # Valor padrão aproximado se tudo falhar (fallback)

def conectar_google_sheets() -> Optional[gspread.Client]:
    try:
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            with open('credentials.json', 'r') as f: creds_dict = json.load(f)
        
        escopos = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credenciais = Credentials.from_service_account_info(creds_dict, scopes=escopos)
        client = gspread.authorize(credenciais)
        return client
    except Exception as e:
        st.error(f"Erro conexão: {e}")
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
        
        col_data = None
        for nome in ['Data', 'Data Estudo', 'Date', 'Conclusão']:
            if nome in df.columns: col_data = nome; break
        if not col_data and len(df.columns) >= 5: col_data = df.columns[4]
        
        if col_data: df['Data_Real'] = pd.to_datetime(df[col_data], format='%d/%m/%Y', errors='coerce')
        else: df['Data_Real'] = pd.NaT
        return df
    except Exception as e:
        st.error(f"Erro dados: {e}")
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
    except:
        return False

# ================================================================================
# 4. VISUALIZAÇÃO E ESTILO
# ================================================================================

def injetar_css_profissional():
    tema = st.session_state.get('tema', 'claro')
    
    if tema == 'escuro':
        bg_main, bg_card, txt = '#0f172a', '#1e293b', '#f1f5f9'
        header_bg = 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)'
        shadow = '0 10px 15px -3px rgba(0,0,0,0.5)'
    else:
        bg_main, bg_card, txt = '#f8fafc', '#ffffff', '#1e293b'
        header_bg = 'linear-gradient(135deg, #f8fafc 0%, #e0e7ff 60%, #dbeafe 100%)'
        shadow = '0 10px 25px -5px rgba(0,0,0,0.1)'

    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"], [data-testid="stMarkdownContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {{
            font-family: 'Nunito', sans-serif;
        }}
        
        [data-testid="stMainBlockContainer"] {{ background-color: {bg_main}; padding: 2rem; max-width: 1600px; }}
        
        /* ANIMAÇÃO HEADER */
        @keyframes slideDown {{
            from {{ transform: translateY(-50px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}

        /* HEADER 300PX */
        .header-container {{
            background: {header_bg}; border-radius: 24px; padding: 0 3rem;
            margin-bottom: 3rem; display: flex; align-items: center; justify-content: space-between;
            box-shadow: {shadow}; height: 300px; position: relative; border: 1px solid rgba(0,0,0,0.05);
            animation: slideDown 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
        }}
        .header-left {{ flex: 0 0 30%; height: 100%; display: flex; align-items: center; z-index: 2; }}
        .header-logo {{ height: 90%; object-fit: contain; }}
        .header-center {{ position: absolute; left: 0; right: 0; top: 0; bottom: 0; display: flex; align-items: center; justify-content: center; pointer-events: none; }}
        .header-title {{ font-size: 3rem; font-weight: 800; color: {txt}; text-transform: uppercase; letter-spacing: -1px; }}
        .header-right {{ flex: 0 0 30%; height: 100%; display: flex; flex-direction: column; align-items: flex-end; padding-top: 2rem; z-index: 2; }}
        
        .info-pill {{
            background: rgba(255,255,255,0.65); backdrop-filter: blur(10px); padding: 0.75rem 1.5rem;
            border-radius: 16px; display: flex; gap: 1.5rem; font-weight: 800; font-size: 1.2rem; color: #475569;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }}

        /* TITULOS */
        .section-title-wrapper {{ margin: 2rem 0 1.5rem 0; display: flex; align-items: center; }}
        .section-title {{
            font-size: 1.5rem; font-weight: 800; color: {txt}; position: relative;
            padding-bottom: 8px; text-transform: uppercase; letter-spacing: -0.5px;
        }}
        .section-title::after {{
            content: ''; position: absolute; left: 0; bottom: 0; width: 100%;
            height: 4px; background: {COR_DESTAQUE}; border-radius: 2px;
        }}

        /* CARDS DE GRAFICOS */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 24px !important; border: 1px solid #e2e8f0 !important;
            background-color: {bg_card} !important; box-shadow: {shadow} !important;
            padding: 2rem 1rem !important; transition: all 0.3s ease;
        }}
        [data-testid="stVerticalBlockBorderWrapper"]:hover {{
            transform: translateY(-5px); border-color: {COR_DESTAQUE} !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1) !important;
        }}

        /* KPI CARDS UNIFORMES */
        .kpi-box {{ 
            background: {bg_card}; border-radius: 16px; padding: 1.5rem; text-align: center; 
            box-shadow: {shadow}; border: 1px solid #e2e8f0; transition: all 0.3s ease;
            /* Altura fixa para uniformidade */
            height: 160px; 
            display: flex; flex-direction: column; justify-content: center; align-items: center;
        }}
        .kpi-box:hover {{ transform: translateY(-5px); border-color: {COR_DESTAQUE}; }}
        .kpi-label {{ font-size: 0.85rem; font-weight: 800; color: #64748b; text-transform: uppercase; margin-bottom: 0.5rem; }}
        .kpi-value {{ font-size: 2.8rem; font-weight: 800; color: {txt}; line-height: 1; }}

        /* CHECKLIST */
        .stExpander {{ border-radius: 12px; border: 1px solid #e2e8f0; background: {bg_card}; }}
        .topic-row {{ padding: 0.75rem; border-bottom: 1px solid #f1f5f9; display: flex; align-items: center; }}
        .topic-content {{ flex: 1; margin-left: 1rem; font-size: 0.95rem; color: {txt}; }}
        .topic-done {{ text-decoration: line-through; color: #94a3b8 !important; }}
        .topic-date {{ font-size: 0.75rem; font-weight: 700; background: {COR_DESTAQUE}; color: white; padding: 2px 8px; border-radius: 4px; }}
        
        /* TEXTO CARD DONUT */
        .card-h1 {{ font-size: 1.1rem; font-weight: 800; text-align: center; color: {txt}; text-transform: uppercase; min-height: 3rem; display: flex; align-items: center; justify-content: center; }}
        .card-h2 {{ font-size: 0.9rem; font-weight: 600; text-align: center; color: #64748b; background: {bg_main}; border-radius: 20px; padding: 0.25rem 1rem; width: fit-content; margin: 0.5rem auto 1.5rem auto; }}

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
    
    pie = base.mark_arc(outerRadius=110, innerRadius=80, cornerRadius=5).encode(
        color=alt.Color("Category:N", scale=alt.Scale(domain=['Concluído', 'Pendente'], range=[COR_CONCLUIDO, COR_PENDENTE]), legend=None),
        order=alt.Order("Category", sort="descending"),
        tooltip=["Category", "Value"]
    )
    
    bg = base.mark_arc(outerRadius=110, innerRadius=80, color=COR_FUNDO_DONUT).encode(order=alt.value(0))
    pct = int(concluido/total*100) if total > 0 else 0
    text = base.mark_text(radius=0, size=38, color='#334155', fontWeight=800, font='Nunito').encode(text=alt.value(f"{pct}%"))
    
    return (bg + pie + text).properties(width=260, height=260, background='transparent').configure_view(strokeWidth=0)

def renderizar_heatmap(df: pd.DataFrame) -> Optional[alt.Chart]:
    df_ok = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    if df_ok.empty: return None
    dados = df_ok.groupby('Data_Real').size().reset_index(name='Qtd')
    
    return alt.Chart(dados).mark_rect(cornerRadius=4, stroke='white', strokeWidth=2).encode(
        x=alt.X('yearmonthdate(Data_Real):O', title=None, axis=alt.Axis(format='%d/%m', labelFontSize=10)),
        y=alt.Y('day(Data_Real):O', title=None, axis=alt.Axis(labels=False, ticks=False, domain=False)),
        color=alt.Color('Qtd:Q', scale=alt.Scale(range=['#dcfce7', '#15803d']), legend=None),
        tooltip=[alt.Tooltip('Data_Real', format='%d/%m')]
    ).properties(
        height=180, width='container', background='transparent'
    ).configure_view(strokeWidth=0).configure_axis(grid=False)

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

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        client = conectar_google_sheets()
        if not client: st.stop()
        df = carregar_dados(client)
        if df is None: st.warning("Carregando..."); st.stop()
        
        cargos = sorted(df['Cargo'].unique().tolist())
        st.markdown("**Selecione o Cargo:**")
        cargo_sel = st.selectbox("Cargo", cargos, label_visibility="collapsed")
        
        st.divider()
        if st.button("🌓 Alternar Tema", use_container_width=True):
            st.session_state['tema'] = 'escuro' if st.session_state['tema'] == 'claro' else 'claro'
            st.rerun()
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # FILTRAGEM
    df_filtro = df[df['Cargo'] == cargo_sel].copy()
    df_filtro['linha_planilha'] = df_filtro.index + 2

    # --- HEADER ANIMADO ---
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

    # --- KPIs (Total, Feito, Falta, Progresso Geral) ---
    total = len(df_filtro)
    feito = df_filtro['Estudado'].sum()
    rest = total - feito
    progresso_geral = (feito / total * 100) if total > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-box"><div class="kpi-label">Total Tópicos</div><div class="kpi-value">{total}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-box"><div class="kpi-label">Concluídos</div><div class="kpi-value" style="color:{COR_CONCLUIDO}">{feito}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-box"><div class="kpi-label">Pendentes</div><div class="kpi-value" style="color:{COR_PENDENTE}">{rest}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-box"><div class="kpi-label">Progresso Geral</div><div class="kpi-value" style="color:{COR_DESTAQUE}">{progresso_geral:.1f}%</div></div>', unsafe_allow_html=True)

    # --- HEATMAP ---
    st.markdown('<div class="section-title-wrapper"><div class="section-title">📅 Atividade Recente</div></div>', unsafe_allow_html=True)
    heat = renderizar_heatmap(df_filtro)
    if heat: st.altair_chart(heat, use_container_width=True)
    else: st.info("Estude para gerar histórico!")

    # --- CARDS (Donuts) ---
    st.markdown('<div class="section-title-wrapper"><div class="section-title">📈 Progresso por Disciplina</div></div>', unsafe_allow_html=True)
    stats = df_filtro.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
    stats.columns = ['Disciplina', 'Feito', 'Total']
    
    # Adiciona "Geral" primeiro
    cards = [{'Disciplina': 'GERAL', 'Feito': feito, 'Total': total}]
    for _, r in stats.iterrows(): cards.append(r.to_dict())
    
    cols = st.columns(3)
    for i, card in enumerate(cards):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"""
                <div class="card-h1">{card['Disciplina']}</div>
                <div class="card-h2">{card['Feito']} de {card['Total']} tópicos</div>
                """, unsafe_allow_html=True)
                grafico = renderizar_donut(card['Feito'], card['Total'])
                st.altair_chart(grafico, use_container_width=True)

    # --- CHECKLIST ---
    st.markdown('<div class="section-title-wrapper"><div class="section-title">✓ Checklist de Tópicos</div></div>', unsafe_allow_html=True)
    for mat in sorted(df_filtro['Disciplinas'].unique()):
        sub = df_filtro[df_filtro['Disciplinas'] == mat]
        done = sub['Estudado'].sum()
        tot = len(sub)
        
        with st.expander(f"**{mat}** ({done}/{tot})"):
            with st.form(key=f"f_{mat}"):
                updates = []
                for _, r in sub.iterrows():
                    c, t = st.columns([0.05, 0.95])
                    k = f"chk_{r['linha_planilha']}"
                    is_checked = bool(r['Estudado'])
                    val = c.checkbox("", value=is_checked, key=k)
                    
                    if val != is_checked: updates.append({'linha': int(r['linha_planilha']), 'status': val})
                    
                    cls = "topic-done" if is_checked else ""
                    dt_badge = f"<span class='topic-date'>{r['Data_Real'].strftime('%d/%m')}</span>" if is_checked and pd.notnull(r['Data_Real']) else ""
                    t.markdown(f"<div class='topic-row'><div class='topic-content {cls}'>{r['Conteúdos']}</div>{dt_badge}</div>", unsafe_allow_html=True)
                
                if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                    if updates:
                        if atualizar_lote(client, updates):
                            st.success("Salvo!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                        else: st.error("Erro")

    st.markdown(f"<div style='text-align:center;color:#94a3b8;padding:3rem 0'>Atualizado: {agora.strftime('%H:%M')}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
