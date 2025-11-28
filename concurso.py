#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📊 DASHBOARD DE ESTUDOS - CÂMARA MUNICIPAL DE GOIÂNIA
================================================================================
VERSÃO: 7.0 - FINAL ULTIMATE
DATA: 2025-11-28 17:30

FUNCIONALIDADES COMPLETAS:
1. Header Premium:
   - Altura 300px
   - Logo 95% altura (esquerda)
   - Título centralizado absoluto
   - Infos (Cidade, Data, Clima) na direita superior em linha única
2. Layout de Gráficos:
   - Cards brancos com sombra (Container CSS)
   - Título da matéria + Subtítulo dentro do card
   - Gráfico Donut Grande (Verde/Vermelho) dentro do card
3. Funcionalidades:
   - Heatmap sem labels poluídos
   - Checklist funcional com salvamento
   - KPIs no topo
   - Sidebar para configurações
   - Fonte Nunito global
================================================================================
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
import locale
import pytz
from typing import Optional, List, Dict

# ================================================================================
# 1. CONFIGURAÇÃO INICIAL
# ================================================================================

warnings.filterwarnings('ignore')

# Configuração de Localidade para Data (Português)
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except:
        pass

# Configuração da Página Streamlit
st.set_page_config(
    page_title="Dashboard de Estudos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================================
# 2. CONSTANTES E VARIÁVEIS GLOBAIS
# ================================================================================

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

# Cores para os gráficos
COR_CONCLUIDO = '#15803d'  # Verde Escuro
COR_PENDENTE = '#b91c1c'   # Vermelho Escuro
COR_AZUL_CTA = '#2563eb'   # Azul para destaques

TIMEZONE_BRASILIA = pytz.timezone('America/Sao_Paulo')

# ================================================================================
# 3. CSS PROFISSIONAL E ESTILIZAÇÃO (O "GROSSO" DO DESIGN)
# ================================================================================

def injetar_css_profissional():
    """Injeta o CSS global para transformar o visual do Streamlit"""
    
    tema = st.session_state.get('tema', 'claro')
    
    if tema == 'escuro':
        bg_main = '#0f172a'
        bg_card = '#1e293b'
        text_main = '#f1f5f9'
        text_secondary = '#94a3b8'
        border_color = '#334155'
        header_bg = 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)'
        shadow_card = '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
    else:
        bg_main = '#f8fafc'
        bg_card = '#ffffff'
        text_main = '#1e293b'
        text_secondary = '#64748b'
        border_color = '#e2e8f0'
        # Gradiente azulado suave solicitado
        header_bg = 'linear-gradient(135deg, #f8fafc 0%, #e0e7ff 50%, #dbeafe 100%)'
        shadow_card = '0 10px 15px -3px rgba(0, 0, 0, 0.1)'

    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        /* RESET E FONTE GLOBAL */
        * {{
            font-family: 'Nunito', sans-serif !important;
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

        /* =========================================
           HEADER CUSTOMIZADO (300px)
           ========================================= */
        .header-container {{
            background: {header_bg};
            border: 1px solid {border_color};
            border-radius: 24px;
            padding: 0 3rem;
            margin-bottom: 3rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: {shadow_card};
            height: 300px; /* Altura solicitada */
            position: relative;
            overflow: hidden;
        }}

        /* LOGO À ESQUERDA */
        .header-left {{
            flex: 0 0 30%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            z-index: 2;
        }}

        .header-logo {{
            height: 90%; /* 95% da altura do container */
            width: auto;
            max-width: 100%;
            object-fit: contain;
            transition: transform 0.3s ease;
        }}
        
        .header-logo:hover {{
            transform: scale(1.02);
        }}

        /* TÍTULO CENTRALIZADO (ABSOLUTO) */
        .header-center {{
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none; /* Deixar clicar através se precisar */
            z-index: 1;
        }}

        .header-title {{
            font-size: 3rem;
            font-weight: 800;
            color: {text_main};
            text-transform: uppercase;
            letter-spacing: -1px;
            text-align: center;
            text-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}

        /* INFOS À DIREITA (SUPERIOR) */
        .header-right {{
            flex: 0 0 30%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            justify-content: flex-start; /* Alinhado ao topo */
            padding-top: 2rem;
            z-index: 2;
        }}

        .info-pill {{
            background: rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(8px);
            padding: 0.75rem 1.25rem;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.4);
            display: flex;
            align-items: center;
            gap: 1rem;
            font-weight: 700;
            font-size: 1.1rem;
            color: {text_secondary};
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}

        /* =========================================
           CARDS E GRÁFICOS
           ========================================= */
        
        /* Classe Wrapper para o Card do Donut */
        .card-wrapper {{
            background-color: {bg_card};
            border-radius: 20px;
            border: 1px solid {border_color};
            box-shadow: {shadow_card};
            padding: 2rem 1rem;
            height: 100%;
            min-height: 400px; /* Garante altura uniforme */
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            transition: transform 0.3s ease;
        }}

        .card-wrapper:hover {{
            transform: translateY(-5px);
            border-color: {COR_AZUL_CTA};
        }}

        .card-title {{
            font-size: 1.1rem;
            font-weight: 800;
            color: {text_main};
            text-align: center;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            min-height: 3.5rem; /* Altura fixa para títulos de 2 linhas */
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .card-subtitle {{
            font-size: 0.9rem;
            color: {text_secondary};
            font-weight: 600;
            margin-bottom: 1.5rem;
            background: {bg_main};
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
        }}

        /* KPI Cards (Topo) */
        .kpi-box {{
            background-color: {bg_card};
            border: 1px solid {border_color};
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: {shadow_card};
            transition: all 0.2s ease;
        }}
        .kpi-box:hover {{ transform: translateY(-3px); }}
        .kpi-label {{ font-size: 0.85rem; font-weight: 700; color: {text_secondary}; text-transform: uppercase; }}
        .kpi-value {{ font-size: 2.5rem; font-weight: 800; color: {text_main}; margin: 0.5rem 0; }}
        .kpi-sub {{ font-size: 0.9rem; color: {text_secondary}; }}

        /* =========================================
           CHECKLIST E OUTROS
           ========================================= */
        .stExpander {{
            background-color: {bg_card};
            border-radius: 12px;
            border: 1px solid {border_color};
            margin-bottom: 1rem;
            overflow: hidden;
        }}
        
        .streamlit-expanderHeader {{
            font-weight: 700;
            font-size: 1.1rem;
            color: {text_main};
        }}

        .topic-row {{
            display: flex;
            align-items: center;
            padding: 0.75rem;
            border-bottom: 1px solid {border_color};
            transition: background 0.2s;
        }}
        .topic-row:hover {{ background-color: {bg_main}; }}
        .topic-content {{ flex: 1; margin-left: 1rem; font-size: 0.95rem; }}
        .topic-done {{ text-decoration: line-through; color: {text_secondary}; }}
        .topic-date {{ 
            font-size: 0.75rem; font-weight: 700; 
            background: {COR_AZUL_CTA}; color: white; 
            padding: 2px 8px; border-radius: 4px; 
        }}

        /* RESPONSIVIDADE */
        @media (max-width: 992px) {{
            .header-container {{
                height: auto;
                flex-direction: column;
                padding: 2rem;
                gap: 1.5rem;
            }}
            .header-left, .header-right, .header-center {{
                position: static;
                width: 100%;
                justify-content: center;
                text-align: center;
                align-items: center;
            }}
            .header-logo {{ height: 80px; }}
            .header-title {{ font-size: 2rem; }}
        }}
    </style>
    """, unsafe_allow_html=True)

# ================================================================================
# 4. FUNÇÕES DE BACKEND
# ================================================================================

def conectar_google_sheets() -> Optional[gspread.Client]:
    """Conecta à API do Google Sheets"""
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
        st.error(f"Erro de Conexão: {e}")
        return None

@st.cache_data(ttl=10)
def carregar_dados(_client) -> Optional[pd.DataFrame]:
    """Carrega dados da planilha e trata tipos"""
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        dados_raw = ws.get_all_records()
        df = pd.DataFrame(dados_raw)
        
        if df.empty: return None
        
        # Tratamento de Status
        df['Status'] = df['Status'].astype(str).str.upper().str.strip()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES', 'OK'])
        
        # Tratamento de Data
        coluna_data = None
        possiveis_nomes = ['Data', 'Data Estudo', 'Date', 'Conclusão']
        for nome in possiveis_nomes:
            if nome in df.columns:
                coluna_data = nome
                break
        
        # Fallback se não achar nome conhecido
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
    """Atualiza múltiplas linhas no Google Sheets de uma vez"""
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        agora = datetime.now(TIMEZONE_BRASILIA)
        
        for update in updates:
            linha = update['linha']
            status = 'TRUE' if update['status'] else 'FALSE'
            data = agora.strftime('%d/%m/%Y') if update['status'] else ''
            
            # Atualiza colunas D (Status) e E (Data)
            ws.update(f"D{linha}:E{linha}", [[status, data]])
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

@st.cache_data(ttl=600)
def obter_clima() -> str:
    """Pega temperatura atual de Goiânia via API"""
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

def calcular_insights(df: pd.DataFrame) -> str:
    """Gera frase de insight baseada em tempo de revisão"""
    df_ok = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    if df_ok.empty: return "Comece seus estudos para gerar insights!"
    
    hoje = datetime.now()
    df_ok['dias'] = (hoje - df_ok['Data_Real']).dt.days
    
    agrupado = df_ok.groupby('Disciplinas')['dias'].min().reset_index()
    urgente = agrupado[agrupado['dias'] > 7].sort_values('dias', ascending=False)
    
    if not urgente.empty:
        disc = urgente.iloc[0]['Disciplinas']
        dias = int(urgente.iloc[0]['dias'])
        return f"🚨 Atenção: **{disc}** não é revisada há {dias} dias!"
    
    return "✅ Seu ciclo de revisões está em dia. Continue assim!"

# ================================================================================
# 5. COMPONENTES VISUAIS (GRÁFICOS)
# ================================================================================

def plot_heatmap(df: pd.DataFrame) -> Optional[alt.Chart]:
    """Heatmap estilo GitHub limpo"""
    df_ok = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    if df_ok.empty: return None
    
    dados = df_ok.groupby('Data_Real').size().reset_index(name='Qtd')
    
    return alt.Chart(dados).mark_rect(
        cornerRadius=4, stroke='white', strokeWidth=2
    ).encode(
        x=alt.X('yearmonthdate(Data_Real):O', title=None, axis=alt.Axis(format='%d/%m', labelFontSize=10, labelColor='#94a3b8')),
        y=alt.Y('day(Data_Real):O', title=None, axis=alt.Axis(labels=False, ticks=False, domain=False)),
        color=alt.Color('Qtd:Q', scale=alt.Scale(range=['#dcfce7', '#166534']), legend=None),
        tooltip=[alt.Tooltip('Data_Real', title='Data', format='%d/%m'), alt.Tooltip('Qtd', title='Tópicos')]
    ).properties(height=180, width='container').configure_view(strokeWidth=0).configure_axis(grid=False)

def plot_donut(concluido: int, total: int) -> alt.Chart:
    """Donut Chart Grosso e Arredondado (Verde/Vermelho)"""
    pendente = total - concluido
    source = pd.DataFrame({
        'Category': ['Concluído', 'Pendente'],
        'Value': [concluido, pendente]
    })
    
    base = alt.Chart(source).encode(theta=alt.Theta("Value:Q", stack=True))
    
    # Arco principal
    pie = base.mark_arc(outerRadius=100, innerRadius=75, cornerRadius=5).encode(
        color=alt.Color("Category:N", scale=alt.Scale(domain=['Concluído', 'Pendente'], range=[COR_CONCLUIDO, COR_PENDENTE]), legend=None),
        order=alt.Order("Category", sort="descending"),
        tooltip=["Category", "Value"]
    )
    
    # Fundo cinza (track)
    bg = base.mark_arc(outerRadius=100, innerRadius=75, color='#f1f5f9').encode(
        order=alt.value(0)
    )
    
    # Texto central
    pct = int(concluido/total*100) if total > 0 else 0
    text = base.mark_text(radius=0, size=36, color='#334155', fontWeight=800, font='Nunito').encode(
        text=alt.value(f"{pct}%")
    )
    
    return (bg + pie + text).properties(width=220, height=220, background='transparent').configure_view(strokeWidth=0)

# ================================================================================
# 6. EXECUÇÃO PRINCIPAL
# ================================================================================

def main():
    # Estado inicial
    if 'tema' not in st.session_state: st.session_state['tema'] = 'claro'
    
    # CSS
    injetar_css_profissional()
    
    # Dados de Tempo e Clima
    agora = obter_horario_brasilia()
    meses = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
    data_txt = f"{agora.day}/{meses[agora.month]}"
    clima = obter_clima()

    # SIDEBAR
    with st.sidebar:
        st.markdown("### ⚙️ Configurações")
        if st.button("🌓 Alternar Tema", use_container_width=True):
            st.session_state['tema'] = 'escuro' if st.session_state['tema'] == 'claro' else 'claro'
            st.rerun()
        
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.info("ℹ️ Use esta barra para configurações do sistema.")

    # ================= HEADER =================
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

    # CARREGAMENTO DE DADOS
    client = conectar_google_sheets()
    if not client: st.stop()
    df = carregar_dados(client)
    if df is None: st.warning("Carregando planilha..."); st.stop()

    # SELETOR DE CARGO
    cargos = sorted(df['Cargo'].unique().tolist())
    st.markdown("### 📋 Seleção de Cargo")
    cargo_sel = st.selectbox("Cargo", cargos, label_visibility="collapsed")
    
    # Filtro
    df_filtro = df[df['Cargo'] == cargo_sel].copy()
    df_filtro['linha_planilha'] = df_filtro.index + 2

    # CÁLCULO DE MÉTRICAS
    total_items = len(df_filtro)
    items_ok = df_filtro['Estudado'].sum()
    items_nok = total_items - items_ok
    pct_ok = (items_ok / total_items * 100) if total_items > 0 else 0
    
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-box"><div class="kpi-label">Total Tópicos</div><div class="kpi-value">{total_items}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-box"><div class="kpi-label">Concluídos</div><div class="kpi-value" style="color:{COR_CONCLUIDO}">{items_ok}</div><div class="kpi-sub">{pct_ok:.1f}%</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-box"><div class="kpi-label">Restantes</div><div class="kpi-value" style="color:{COR_PENDENTE}">{items_nok}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-box"><div class="kpi-label">Insight</div><div class="kpi-sub" style="margin-top:1rem">{calcular_insights(df_filtro)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # HEATMAP
    st.markdown("### 📅 Histórico de Atividades")
    grafico_heat = plot_heatmap(df_filtro)
    if grafico_heat:
        st.altair_chart(grafico_heat, use_container_width=True)
    else:
        st.info("Nenhuma atividade registrada ainda.")

    st.markdown("---")

    # ÁREA DE GRÁFICOS (GRID DE DONUTS)
    st.markdown("### 📈 Progresso por Disciplina")
    
    # Agrupar dados
    stats = df_filtro.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
    stats.columns = ['Disciplina', 'Feito', 'Total']
    
    # Adicionar "Geral" na lista
    cards_data = [{'Disciplina': 'PROGRESSO GERAL', 'Feito': items_ok, 'Total': total_items}]
    for _, row in stats.iterrows():
        cards_data.append(row.to_dict())
    
    # Renderizar em Grid de 3 colunas
    cols_grid = st.columns(3)
    
    for index, card in enumerate(cards_data):
        col = cols_grid[index % 3]
        with col:
            # AQUI ESTÁ O SEGREDO: HTML Container + Gráfico dentro
            st.markdown(f"""
            <div class="card-wrapper">
                <div class="card-title">{card['Disciplina']}</div>
                <div class="card-subtitle">{card['Feito']} de {card['Total']} tópicos</div>
            """, unsafe_allow_html=True)
            
            fig = plot_donut(card['Feito'], card['Total'])
            st.altair_chart(fig, use_container_width=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # CHECKLIST (EXPANDERS)
    st.markdown("### ✓ Checklist Detalhado")
    
    materias = sorted(df_filtro['Disciplinas'].unique())
    
    for materia in materias:
        sub_df = df_filtro[df_filtro['Disciplinas'] == materia]
        m_feito = sub_df['Estudado'].sum()
        m_total = len(sub_df)
        
        with st.expander(f"**{materia}** ({m_feito}/{m_total})"):
            with st.form(key=f"form_{materia}"):
                updates = []
                for _, row in sub_df.iterrows():
                    cols = st.columns([0.05, 0.95])
                    chk_key = f"chk_{row['linha_planilha']}"
                    checked = cols[0].checkbox("", value=bool(row['Estudado']), key=chk_key)
                    
                    if checked != bool(row['Estudado']):
                        updates.append({'linha': int(row['linha_planilha']), 'status': checked})
                    
                    classe = "topic-done" if row['Estudado'] else ""
                    data_badge = ""
                    if row['Estudado'] and pd.notnull(row['Data_Real']):
                        data_badge = f"<span class='topic-date'>{row['Data_Real'].strftime('%d/%m')}</span>"
                    
                    cols[1].markdown(f"""
                    <div class="topic-row">
                        <div class="topic-content {classe}">{row['Conteúdos']}</div>
                        {data_badge}
                    </div>
                    """, unsafe_allow_html=True)
                
                if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                    if updates:
                        if atualizar_lote(client, updates):
                            st.success("Salvo com sucesso!")
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Erro ao salvar.")
                    else:
                        st.info("Nenhuma alteração detectada.")

    # RODAPÉ
    st.markdown(f"""
    <div style="text-align: center; color: #94a3b8; padding: 2rem 0; border-top: 1px solid #e2e8f0; margin-top: 3rem;">
        Dashboard de Estudos v7.0 • Atualizado em: {agora.strftime("%d/%m/%Y %H:%M")}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
