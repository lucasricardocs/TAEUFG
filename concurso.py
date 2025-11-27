#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard de Estudos - Câmara de Goiânia
VERSÃO ULTIMATE FULL - TODAS AS FUNCIONALIDADES INTEGRADAS
Autor: Perplexity AI Assistant
Data: 2025-11-27
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

# Configuração Inicial
warnings.filterwarnings('ignore')
st.set_page_config(
    page_title="Dashboard Ultimate",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================================
# 1. CSS AVANÇADO & ANIMAÇÕES (INTEGRADO)
# ================================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }

    /* BACKGROUND & SCROLL */
    [data-testid="stMainBlockContainer"] { 
        background: #f8fafc; 
        color: #0f172a; 
        overflow-x: hidden;
    }
    
    /* --- KEYFRAMES --- */
    @keyframes slideUpFade {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes popIn {
        0% { opacity: 0; transform: scale(0.5); }
        70% { transform: scale(1.1); }
        100% { opacity: 1; transform: scale(1); }
    }
    @keyframes stripes {
        from { background-position: 20px 0; }
        to { background-position: 0 0; }
    }
    @keyframes fillUp {
        from { width: 0; }
    }
    @keyframes floatUp { 
        0% { transform: translateY(110vh) scale(0); opacity: 0; } 
        20% { opacity: 0.8; transform: translateY(80vh) scale(1); } 
        80% { opacity: 0.6; }
        100% { transform: translateY(-10vh) scale(0.5); opacity: 0; } 
    }

    /* --- HEADER --- */
    .header-container {
        display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 2rem;
        background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
        padding: 1.5rem 2rem; border-radius: 16px; margin-bottom: 2rem;
        box-shadow: 0 10px 30px -10px rgba(30, 64, 175, 0.5); color: white;
        animation: slideUpFade 0.8s ease-out forwards;
        position: relative; z-index: 10;
    }
    .header-logo img { 
        max-width: 280px; 
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.3)); 
        transition: transform 0.5s ease;
    }
    .header-logo img:hover { transform: scale(1.05) rotate(-1deg); }
    .header-content { text-align: center; }
    .header-content h1 { font-size: 2.4rem; font-weight: 800; margin: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .header-info { background: rgba(255,255,255,0.1); padding: 0.8rem 1.2rem; border-radius: 12px; text-align: right; border: 1px solid rgba(255,255,255,0.1); }

    /* --- BADGES --- */
    .badge-container { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-bottom: 20px; }
    .badge {
        background: linear-gradient(45deg, #FFD700, #FFA500);
        color: #fff; padding: 8px 20px; border-radius: 30px;
        font-weight: bold; font-size: 0.9rem; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);
        opacity: 0; animation: popIn 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
    }
    .badge:nth-child(1) { animation-delay: 0.5s; }
    .badge:nth-child(2) { animation-delay: 0.7s; }
    .badge:nth-child(3) { animation-delay: 0.9s; }

    /* --- METRIC CARDS --- */
    .metric-card { 
        background: white; padding: 1.5rem; border-radius: 16px; 
        border: 1px solid #e2e8f0; text-align: center; 
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        opacity: 0; animation: slideUpFade 0.6s ease-out forwards;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .metric-col-1 .metric-card { animation-delay: 0.2s; }
    .metric-col-2 .metric-card { animation-delay: 0.4s; }
    .metric-col-3 .metric-card { animation-delay: 0.6s; }
    .metric-col-4 .metric-card { animation-delay: 0.8s; }
    
    .metric-card:hover { 
        transform: translateY(-10px) scale(1.02); 
        box-shadow: 0 20px 30px -10px rgba(59, 130, 246, 0.25); border-color: #3b82f6;
    }
    .metric-value { font-size: 2.8rem; font-weight: 800; color: #0f172a; transition: color 0.3s; }
    .metric-card:hover .metric-value { color: #2563eb; }

    /* --- PROGRESS BARS --- */
    .bar-container { 
        background: #e2e8f0; height: 14px; border-radius: 7px; 
        overflow: hidden; margin-top: 0.5rem; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }
    .bar-fill { 
        height: 100%; border-radius: 7px; 
        background-image: linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent); 
        background-size: 20px 20px; 
        animation: stripes 1s linear infinite, fillUp 1.5s ease-out forwards;
    }

    /* --- REVIEW CARDS --- */
    .review-row { 
        display: flex; justify-content: space-between; background: #fff; 
        padding: 15px; border-bottom: 1px solid #eee; border-left: 4px solid #f59e0b; 
        margin-bottom: 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        opacity: 0; animation: slideUpFade 0.5s ease-out forwards;
        transition: transform 0.2s;
    }
    .review-row:hover { transform: translateX(5px); border-left-width: 8px; }
    .review-row:nth-child(1) { animation-delay: 1.2s; }
    .review-row:nth-child(2) { animation-delay: 1.4s; }

    /* --- LISTA CONTEÚDOS --- */
    .conteudo-item {
        background: #ffffff; border: 1px solid #e2e8f0; padding: 1rem; 
        border-radius: 8px; margin-bottom: 0.5rem; color: #334155;
        transition: all 0.2s;
    }
    .conteudo-item:hover { border-color: #3b82f6; transform: translateX(5px); }
    .conteudo-item.done {
        background: #f0fdf4; border-color: #bbf7d0; color: #15803d; 
        text-decoration: line-through; opacity: 0.8;
    }

    /* --- PARTICLES --- */
    #sparkles-container { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; }
    .spark { 
        position: absolute; border-radius: 50%; opacity: 0; 
        animation: floatUp linear forwards; filter: blur(1px);
    }

    /* Responsive */
    @media (max-width: 900px) { .header-container { grid-template-columns: 1fr; text-align: center; } }
</style>

<!-- PARTICLES ENGINE -->
<div id="sparkles-container"></div>
<script>
    function createSparkle() {
        const container = document.getElementById('sparkles-container');
        if (!container) return;
        const el = document.createElement('div');
        const colors = ['rgba(37, 99, 235, ', 'rgba(22, 163, 74, ', 'rgba(234, 88, 12, ', 'rgba(147, 51, 234, '];
        const colorBase = colors[Math.floor(Math.random() * colors.length)];
        
        el.style.background = colorBase + '0.6)';
        el.style.boxShadow = `0 0 10px ${colorBase}0.4)`;
        el.classList.add('spark');

        const size = Math.random() * 12 + 4;
        el.style.width = size + 'px'; el.style.height = size + 'px';
        el.style.left = Math.random() * 100 + 'vw';
        
        const duration = Math.random() * 5 + 5; 
        el.style.animationDuration = duration + 's';
        container.appendChild(el);
        setTimeout(() => el.remove(), duration * 1000);
    }
    setInterval(createSparkle, 200);
</script>
""", unsafe_allow_html=True)

# ================================================================================
# 2. CONFIGURAÇÃO & CONSTANTES
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
    'LÍNGUA PORTUGUESA': 1, 'RLM': 1, 'REALIDADE DE GOIÁS': 1,
    'LEGISLAÇÃO APLICADA': 2, 'CONHECIMENTOS ESPECÍFICOS': 2
}

# ================================================================================
# 3. FUNÇÕES DE BACKEND
# ================================================================================

def obter_data():
    """Retorna data formatada"""
    hoje = datetime.now()
    meses = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
    return f"{hoje.day} de {meses[hoje.month]} de {hoje.year}"

@st.cache_data(ttl=600)
def obter_temp():
    """Obtém temperatura da API"""
    try:
        r = requests.get('https://api.open-meteo.com/v1/forecast',
            params={'latitude': -15.8267, 'longitude': -48.9626, 'current': 'temperature_2m', 'timezone': 'America/Sao_Paulo'}, timeout=3)
        if r.status_code == 200: return round(r.json()['current']['temperature_2m'], 1)
    except: pass
    return "--"

def conectar():
    """Conecta ao GSheets"""
    try:
        if 'gcp_service_account' in st.secrets: creds = dict(st.secrets["gcp_service_account"])
        else: with open('credentials.json', 'r') as f: creds = json.load(f)
        return gspread.authorize(Credentials.from_service_account_info(creds, scopes=['https://www.googleapis.com/auth/spreadsheets']))
    except: return None

@st.cache_data(ttl=30)
def carregar_dados(_client):
    """Carrega dados da planilha"""
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        df = pd.DataFrame(ws.get_all_records())
        df['Status'] = df['Status'].astype(str).str.upper()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES'])
        return df
    except: return None

def atualizar(client, linha, novo_status):
    """Atualiza célula na planilha"""
    try:
        client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME).update_cell(linha, 4, str(novo_status))
        return True
    except: return False

# ================================================================================
# 4. FUNÇÕES DE GRÁFICOS & INTELIGÊNCIA
# ================================================================================

def criar_donut_chart(estudados, total, cor):
    """Cria Donut Chart com Altair"""
    df = pd.DataFrame({'category': ['Concluído', 'Restante'], 'value': [estudados, total - estudados]})
    base = alt.Chart(df).encode(theta=alt.Theta("value", stack=True))
    pie = base.mark_arc(outerRadius=80, innerRadius=60, stroke='white', strokeWidth=4).encode(
        color=alt.Color("category", scale=alt.Scale(domain=['Concluído', 'Restante'], range=[cor, '#e2e8f0']), legend=None),
        tooltip=["category", "value"]
    )
    text = base.mark_text(radius=0, size=22, color=cor, fontWeight='bold').encode(text=alt.value(f"{int(estudados/total*100)}%"))
    return (pie + text).properties(width=200, height=200)

def gerar_heatmap_simulado():
    """Gera dados simulados para o Heatmap"""
    datas = []
    hoje = datetime.now()
    for i in range(30):
        d = hoje - timedelta(days=i)
        val = random.choice([0, 1, 2, 3, 4, 2, 1, 0, 4]) 
        datas.append({'date': d.strftime('%Y-%m-%d'), 'count': val})
    return pd.DataFrame(datas)

def verificar_badges(total_estudado, pct_geral):
    """Lógica de Gamificação"""
    badges = []
    if pct_geral >= 10: badges.append("🚀 Start (10%)")
    if pct_geral >= 50: badges.append("🔥 Halfway (50%)")
    if pct_geral >= 80: badges.append("🎓 Expert (80%)")
    if total_estudado > 100: badges.append("📚 Legend (100+)")
    return badges

# ================================================================================
# 5. APLICAÇÃO PRINCIPAL (MAIN)
# ================================================================================

def main():
    # --- HEADER ---
    st.markdown(f"""
    <div class="header-container">
        <div class="header-logo"><img src="{LOGO_URL}"></div>
        <div class="header-content">
            <h1>🚀 Dashboard Ultimate</h1>
            <p>Performance • Gamificação • Estratégia</p>
        </div>
        <div class="header-info">
            <div class="info-row">📍 Goiânia - GO</div>
            <div class="info-row">📅 {datetime.now().strftime('%d/%m/%Y')}</div>
            <div class="info-row">🌡️ {obter_temp()}°C</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Configurações")
        client = conectar()
        if not client: st.stop()
        
        # Carregamento Inicial
        if 'dados' not in st.session_state:
            st.session_state['dados'] = carregar_dados(client)
        
        df = st.session_state['dados']
        if df is None: st.warning("Erro ao carregar dados."); st.stop()

        cargos = df['Cargo'].unique()
        cargo = st.selectbox("Selecione o Cargo:", cargos)
        
        st.markdown("---")
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.session_state['dados'] = carregar_dados(client)
            st.rerun()

    # Filtragem
    df_cargo = df[df['Cargo'] == cargo].copy()
    
    # Cálculos Estatísticos
    total = len(df_cargo)
    estudados = df_cargo['Estudado'].sum()
    faltam = total - estudados
    pct_geral = (estudados / total * 100) if total > 0 else 0
    
    stats = df_cargo.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
    stats.columns = ['Disciplina', 'Estudados', 'Total']
    stats['Percentual'] = (stats['Estudados'] / stats['Total'] * 100).round(0)
    df_cargo['linha'] = df_cargo.index + 2

    # --- QUADRO DE MEDALHAS (BADGES) ---
    st.markdown("<h3 style='text-align:center; animation: slideUpFade 1s ease-out;'>🎖️ Quadro de Conquistas</h3>", unsafe_allow_html=True)
    badges = verificar_badges(estudados, pct_geral)
    html_badges = '<div class="badge-container">'
    if badges:
        for b in badges: html_badges += f'<div class="badge">✨ {b}</div>'
    else: 
        html_badges += '<div class="badge" style="background:#cbd5e1; color:#64748b; box-shadow:none;">🔒 Continue estudando para desbloquear...</div>'
    html_badges += '</div>'
    st.markdown(html_badges, unsafe_allow_html=True)

    # --- KPI CARDS ---
    st.markdown("### 📊 Visão Geral")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-col-1"><div class="metric-card"><div class="metric-value" style="color:#3b82f6">{total}</div><div class="metric-label">Tópicos Totais</div></div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-col-2"><div class="metric-card"><div class="metric-value" style="color:#22c55e">{estudados}</div><div class="metric-label">Concluídos</div></div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-col-3"><div class="metric-card"><div class="metric-value" style="color:#ef4444">{faltam}</div><div class="metric-label">Restantes</div></div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-col-4"><div class="metric-card"><div class="metric-value" style="color:#8b5cf6">{pct_geral:.0f}%</div><div class="metric-label">Progresso Geral</div></div></div>', unsafe_allow_html=True)

    # --- HEATMAP ---
    st.markdown('<div style="opacity:0; animation: slideUpFade 0.8s ease-out 0.8s forwards;">', unsafe_allow_html=True)
    st.markdown("### 🔥 Ritmo de Estudos (30 dias)")
    df_heat = gerar_heatmap_simulado()
    chart_heat = alt.Chart(df_heat).mark_rect(cornerRadius=2).encode(
        x=alt.X('date:T', title=None, axis=alt.Axis(format='%d/%m', labelColor='#64748b')),
        color=alt.Color('count:Q', scale=alt.Scale(scheme='greens'), legend=None),
        tooltip=['date', 'count']
    ).properties(height=100, width='container').configure_view(strokeWidth=0)
    st.altair_chart(chart_heat, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- MODO REVISÃO ---
    st.markdown("### 🔄 Revisão Inteligente")
    topicos_rev = df_cargo[df_cargo['Estudado'] == True].sample(n=min(3, estudados)) if estudados > 0 else pd.DataFrame()
    if not topicos_rev.empty:
        c_rev, c_info = st.columns([2,1])
        with c_rev:
            for _, row in topicos_rev.iterrows():
                st.markdown(f"""<div class="review-row">
                    <div><b>{row['Disciplinas']}</b><br><span style="font-size:0.9em; color:#666">{row['Conteúdos']}</span></div>
                    <div style="align-self:center; font-size:1.5rem">🧐</div>
                </div>""", unsafe_allow_html=True)
        with c_info:
            st.info("💡 **Dica:** O algoritmo seleciona tópicos aleatórios já estudados para combater a curva do esquecimento.")
    else: st.info("Estude mais tópicos para liberar o modo revisão!")

    # --- GRÁFICOS DE PIZZA (GRID) ---
    st.markdown("### 🍩 Progresso Detalhado")
    cols = st.columns(3)
    for i, row in stats.iterrows():
        with cols[i % 3]:
            cor = CORES.get(row['Disciplina'], '#333')
            st.markdown(f"<div style='text-align:center; font-weight:600; color:{cor}; animation: popIn 0.5s ease-out forwards; animation-delay: {1.0 + (i*0.1)}s; opacity:0'>{row['Disciplina']}</div>", unsafe_allow_html=True)
            chart = criar_donut_chart(row['Estudados'], row['Total'], cor)
            st.altair_chart(chart, use_container_width=True)

    # --- LISTA DE CONTEÚDOS ---
    st.markdown("### 📚 Lista de Conteúdos")
    
    filtro_disc = st.selectbox("Filtrar Disciplina:", ["Todas"] + sorted(df_cargo['Disciplinas'].unique().tolist()))
    df_view = df_cargo if filtro_disc == "Todas" else df_cargo[df_cargo['Disciplinas'] == filtro_disc]

    for disc in df_view['Disciplinas'].unique():
        df_disc = df_view[df_view['Disciplinas'] == disc]
        p_disc = (df_disc['Estudado'].sum() / len(df_disc) * 100)
        cor = CORES.get(disc, '#333')
        emoji = EMOJIS.get(disc, '📘')

        # Barra de Progresso Animada por Matéria
        st.markdown(f"""
        <div style="margin-top: 1.5rem; margin-bottom: 0.5rem;">
            <div style="display:flex; justify-content:space-between; font-weight:700; color:#334155; font-size:1.1rem;">
                <span>{emoji} {disc}</span><span>{p_disc:.0f}%</span>
            </div>
            <div class="bar-container">
                <div class="bar-fill" style="width: {p_disc}%; background-color: {cor};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Expander com Checkboxes
        with st.expander(f"Ver {len(df_disc)} Tópicos"):
            for idx, row in df_disc.iterrows():
                c_check, c_text = st.columns([0.05, 0.95])
                with c_check:
                    is_checked = st.checkbox("Concluído", value=bool(row['Estudado']), key=f"chk_{idx}", label_visibility="collapsed")
                
                # Lógica de Atualização
                if is_checked != bool(row['Estudado']):
                    if atualizar(client, int(row['linha']), 'TRUE' if is_checked else 'FALSE'):
                        st.toast(f"Status atualizado: {row['Conteúdos'][:30]}...", icon="✅")
                        time.sleep(0.5)
                        st.cache_data.clear() # Limpa cache para atualizar dados
                        st.rerun()

                classe = "done" if row['Estudado'] else ""
                c_text.markdown(f'<div class="conteudo-item {classe}">{row["Conteúdos"]}</div>', unsafe_allow_html=True)

    # --- FOOTER ---
    st.markdown(f'<div style="text-align:center; color:#64748b; padding:3rem 0; font-size:0.85rem;">✨ Dashboard Ultimate | Atualizado em {datetime.now().strftime("%H:%M:%S")}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
