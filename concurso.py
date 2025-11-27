#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🚀 DASHBOARD DE ESTUDOS ULTIMATE - CÂMARA MUNICIPAL DE GOIÂNIA
================================================================================
VERSÃO: ULTIMATE EXTENDED
AUTOR: Perplexity AI Assistant
DATA: 2025-11-27

DESCRIÇÃO:
Este dashboard é uma aplicação web completa desenvolvida com Streamlit para
acompanhamento de estudos para concursos públicos. Ele integra funcionalidades
avançadas de visualização de dados, gamificação e gestão de tarefas.

FUNCIONALIDADES PRINCIPAIS:
1.  Conexão segura e autenticada com Google Sheets API.
2.  Interface de usuário responsiva e moderna (Tema Claro).
3.  Sistema de partículas (fagulhas) animadas em JavaScript puro.
4.  Gamificação com sistema de Badges e Conquistas.
5.  Heatmap de Produtividade Real baseado em histórico de datas.
6.  Gráficos interativos de alta performance com Altair.
7.  Check-list de conteúdos com atualização em tempo real na nuvem.
8.  Visual clean e minimalista para máxima legibilidade.

REQUISITOS:
- Python 3.8+
- Bibliotecas: streamlit, pandas, altair, gspread, google-auth
- Arquivo 'credentials.json' (Google Service Account)
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

# ================================================================================
# 1. CONFIGURAÇÃO INICIAL DO AMBIENTE
# ================================================================================

# Suprimir avisos desnecessários do Pandas/Streamlit
warnings.filterwarnings('ignore')

# Tentar configurar locale para português (datas formatadas)
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except Exception:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except:
        pass  # Fallback para padrão do sistema

# Configuração da Página Streamlit
st.set_page_config(
    page_title="Dashboard Ultimate",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': """
        ### Dashboard de Estudos Ultimate
        Desenvolvido para alta performance em concursos.
        """
    }
)

# ================================================================================
# 2. ESTILOS CSS AVANÇADOS (LAYOUT & ANIMAÇÕES)
# ================================================================================

st.markdown("""
<style>
    /* 
    ==========================================================================
    2.1. IMPORTAÇÃO DE FONTES E RESET
    ==========================================================================
    */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        box-sizing: border-box;
    }

    /* 
    ==========================================================================
    2.2. CONFIGURAÇÃO DO CONTAINER PRINCIPAL
    ==========================================================================
    */
    [data-testid="stMainBlockContainer"] {
        background-color: #f8fafc;
        color: #0f172a;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* Remove elementos padrão do Streamlit para visual limpo */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 
    ==========================================================================
    2.3. ANIMAÇÕES (KEYFRAMES)
    ==========================================================================
    */
    
    /* Entrada suave de baixo para cima */
    @keyframes slideUpFade {
        0% {
            opacity: 0;
            transform: translateY(20px);
        }
        100% {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Efeito de "Pop" para Badges */
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

    /* Flutuação de partículas */
    @keyframes floatUp { 
        0% { 
            transform: translateY(100vh) scale(0.5); 
            opacity: 0; 
        } 
        20% { 
            opacity: 0.8; 
        } 
        100% { 
            transform: translateY(-10vh) scale(0.5); 
            opacity: 0; 
        } 
    }

    /* 
    ==========================================================================
    2.4. COMPONENTES DO HEADER (FIXO & SÓLIDO)
    ==========================================================================
    */

    .header-container {
        display: flex;
        align-items: center;
        justify-content: center;
        
        /* Gradiente Azul Profundo */
        background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
        
        padding: 2rem 3rem;
        border-radius: 20px;
        margin-bottom: 3rem;
        
        /* Borda Branca Grossa (Solicitado) */
        border: 5px solid #ffffff;
        box-shadow: 0 15px 35px -10px rgba(30, 64, 175, 0.4);
        
        position: relative;
        z-index: 10;
        overflow: hidden;
        color: white;
    }

    .header-logo {
        position: absolute;
        left: 2rem;
        top: 50%;
        transform: translateY(-50%);
    }

    .header-logo img { 
        max-width: 260px; 
        height: auto;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3)); 
        transition: transform 0.3s ease;
    }
    
    .header-logo img:hover {
        transform: scale(1.02);
    }

    .header-content { 
        text-align: center; 
        z-index: 1;
    }

    .header-content h1 { 
        font-size: 2.6rem; 
        font-weight: 800; 
        margin: 0; 
        color: #ffffff; /* Branco Sólido */
        letter-spacing: -0.02em;
    }
    
    .header-content p {
        margin-top: 0.5rem;
        font-size: 1.1rem;
        color: #ffffff;
        opacity: 0.9;
        font-weight: 500;
    }

    /* Informações no Canto Superior Direito */
    .header-info { 
        position: absolute;
        top: 1.2rem;
        right: 1.5rem;
        text-align: right;
        z-index: 2;
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }
    
    .info-row {
        font-size: 0.7rem; /* Tamanho pequeno */
        color: rgba(255,255,255,0.95);
        font-weight: 700;
        line-height: 1.4;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-family: 'JetBrains Mono', monospace;
    }

    /* 
    ==========================================================================
    2.5. LISTA DE CONTEÚDOS (ESTILO CLEAN)
    ==========================================================================
    */

    .topic-row {
        display: flex;
        align-items: flex-start;
        padding: 12px 0;
        border-bottom: 1px solid rgba(0,0,0,0.05); /* Linha sutil */
        transition: background-color 0.2s ease;
    }
    
    .topic-row:hover {
        background-color: #f1f5f9;
        border-radius: 4px;
    }
    
    .topic-text {
        flex: 1;
        font-size: 0.95rem;
        color: #334155;
        padding-left: 12px;
        line-height: 1.5;
        font-weight: 400;
    }
    
    .topic-text.done {
        color: #94a3b8; /* Cinza claro */
        text-decoration: line-through;
    }
    
    .topic-date {
        font-size: 0.7rem;
        color: #64748b;
        background-color: #e2e8f0;
        padding: 2px 8px;
        border-radius: 12px;
        margin-left: 10px;
        white-space: nowrap;
        vertical-align: middle;
        font-weight: 600;
    }

    /* 
    ==========================================================================
    2.6. CARDS DE MÉTRICAS (KPIs)
    ==========================================================================
    */

    .metric-card { 
        background: white; 
        padding: 1.8rem; 
        border-radius: 20px; 
        border: 1px solid #e2e8f0; 
        text-align: center; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); 
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    
    .metric-card:hover { 
        transform: translateY(-5px); 
        border-color: #3b82f6;
        box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.1);
    }
    
    .metric-value { 
        font-size: 2.8rem; 
        font-weight: 800; 
        color: #0f172a;
        line-height: 1;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* 
    ==========================================================================
    2.7. GAMIFICAÇÃO (BADGES)
    ==========================================================================
    */

    .badge-container { 
        display: flex; 
        gap: 12px; 
        justify-content: center; 
        flex-wrap: wrap; 
        margin-bottom: 30px; 
        padding: 10px;
    }
    
    .badge { 
        background: linear-gradient(135deg, #FFD700, #FFA500); 
        color: #fff; 
        padding: 8px 20px; 
        border-radius: 50px; 
        font-weight: 700; 
        font-size: 0.85rem; 
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 4px 10px rgba(255, 165, 0, 0.3); 
        animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        opacity: 0;
    }
    
    .badge:nth-child(1) { animation-delay: 0.2s; }
    .badge:nth-child(2) { animation-delay: 0.4s; }
    .badge:nth-child(3) { animation-delay: 0.6s; }

    /* 
    ==========================================================================
    2.8. EFEITOS VISUAIS (PARTÍCULAS)
    ==========================================================================
    */

    #sparkles-container { 
        position: fixed; 
        top: 0; 
        left: 0; 
        width: 100%; 
        height: 100%; 
        pointer-events: none; 
        z-index: 0; 
        overflow: hidden;
    }
    
    .spark { 
        position: absolute; 
        border-radius: 50%; 
        opacity: 0; 
        animation: floatUp linear forwards; 
    }

    /* 
    ==========================================================================
    2.9. CONTAINERS DE GRÁFICOS
    ==========================================================================
    */
    
    .heatmap-container {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    /* Responsividade */
    @media (max-width: 768px) {
        .header-container {
            flex-direction: column;
            padding: 1.5rem;
            text-align: center;
        }
        .header-logo {
            position: static;
            margin-bottom: 1rem;
            transform: none;
        }
        .header-info {
            position: static;
            margin-top: 1rem;
            text-align: center;
            width: 100%;
        }
        .metric-card {
            margin-bottom: 1rem;
        }
    }
</style>

<!-- SCRIPT JAVASCRIPT PARA GERAR FAGULHAS DINÂMICAS -->
<div id="sparkles-container"></div>
<script>
    function createSparkle() {
        const container = document.getElementById('sparkles-container');
        if (!container) return;
        
        const el = document.createElement('div');
        el.classList.add('spark');
        
        // Cores suaves e modernas
        const colors = [
            'rgba(37, 99, 235, 0.3)',  // Azul
            'rgba(22, 163, 74, 0.3)',  // Verde
            'rgba(234, 88, 12, 0.3)',  // Laranja
            'rgba(147, 51, 234, 0.3)'  // Roxo
        ];
        el.style.background = colors[Math.floor(Math.random() * colors.length)];
        
        // Tamanho aleatório
        const size = Math.random() * 12 + 4;
        el.style.width = size + 'px';
        el.style.height = size + 'px';
        
        // Posição e Duração
        el.style.left = Math.random() * 100 + 'vw';
        el.style.animationDuration = (Math.random() * 5 + 5) + 's';
        
        container.appendChild(el);
        
        // Remover elemento após animação para não pesar memória
        setTimeout(() => el.remove(), 10000);
    }
    
    // Iniciar loop de criação
    setInterval(createSparkle, 300);
</script>
""", unsafe_allow_html=True)

# ================================================================================
# 3. CONFIGURAÇÕES GERAIS & CONSTANTES
# ================================================================================

# IDs de Conexão
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'

# URL da Logo Oficial
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

# Paleta de Cores por Disciplina
CORES = {
    'LÍNGUA PORTUGUESA': '#ef4444',       # Vermelho
    'RLM': '#10b981',                     # Verde
    'REALIDADE DE GOIÁS': '#3b82f6',      # Azul
    'LEGISLAÇÃO APLICADA': '#8b5cf6',     # Roxo
    'CONHECIMENTOS ESPECÍFICOS': '#f59e0b'# Laranja
}

# Pesos para cálculo ponderado (Futuro uso)
PESOS = {
    'LÍNGUA PORTUGUESA': 1,
    'RLM': 1,
    'REALIDADE DE GOIÁS': 1,
    'LEGISLAÇÃO APLICADA': 2,
    'CONHECIMENTOS ESPECÍFICOS': 2
}

# ================================================================================
# 4. MÓDULO DE INTEGRAÇÃO (BACKEND)
# ================================================================================

def conectar_google_sheets():
    """
    Estabelece conexão segura com a API do Google Sheets.
    Retorna o objeto cliente autenticado.
    """
    try:
        # Tenta carregar segredos do Streamlit Secrets
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            # Fallback para arquivo local
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
        st.error(f"Erro crítico na conexão com Google Sheets: {e}")
        return None

@st.cache_data(ttl=15)
def carregar_dados_planilha(_client):
    """
    Carrega dados da planilha, aplica tratamentos de tipos e datas.
    Utiliza cache para otimizar performance.
    """
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        dados = ws.get_all_records()
        df = pd.DataFrame(dados)
        
        if df.empty:
            return None
            
        # Normalização de Status (Booleano)
        df['Status'] = df['Status'].astype(str).str.upper().str.strip()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES', 'OK'])
        
        # Identificação Inteligente da Coluna de Data
        coluna_data = None
        
        # Tenta encontrar pelo nome
        possiveis_nomes = ['Data', 'Data Estudo', 'Data Conclusão', 'Date']
        for nome in possiveis_nomes:
            if nome in df.columns:
                coluna_data = nome
                break
        
        # Se não achar pelo nome, pega a 5ª coluna (índice 4) se existir
        if not coluna_data and len(df.columns) >= 5:
            coluna_data = df.columns[4]
            
        # Processamento da Coluna de Data
        if coluna_data:
            df['Data_Real'] = pd.to_datetime(df[coluna_data], format='%d/%m/%Y', errors='coerce')
        else:
            df['Data_Real'] = pd.NaT
            
        return df
        
    except Exception as e:
        st.error(f"Erro ao processar dados da planilha: {e}")
        return None

def atualizar_status(client, linha_planilha, novo_status_bool):
    """
    Atualiza o status e a data na planilha.
    linha_planilha: Índice real na planilha (começa em 2).
    novo_status_bool: True ou False.
    """
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        
        # Converte booleano para string aceita
        status_str = 'TRUE' if novo_status_bool else 'FALSE'
        
        # Atualiza Coluna 4 (Status)
        ws.update_cell(linha_planilha, 4, status_str)
        
        # Atualiza Coluna 5 (Data)
        if novo_status_bool:
            data_hoje = datetime.now().strftime('%d/%m/%Y')
            ws.update_cell(linha_planilha, 5, data_hoje)
        else:
            # Se desmarcar, limpa a data
            ws.update_cell(linha_planilha, 5, '')
            
        return True
        
    except Exception as e:
        st.error(f"Falha ao salvar na nuvem: {e}")
        return False

@st.cache_data(ttl=600)
def obter_temperatura_local():
    """
    Consulta API externa para temperatura em tempo real.
    Cache de 10 minutos para evitar bloqueio da API.
    """
    try:
        url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': -15.8267, # Coordenadas de Goiânia
            'longitude': -48.9626,
            'current': 'temperature_2m',
            'timezone': 'America/Sao_Paulo'
        }
        r = requests.get(url, params=params, timeout=2)
        if r.status_code == 200:
            return round(r.json()['current']['temperature_2m'], 1)
    except:
        pass
    return "--"

# ================================================================================
# 5. MÓDULO DE VISUALIZAÇÃO DE DADOS (GRÁFICOS)
# ================================================================================

def criar_heatmap_produtividade(df):
    """
    Gera um heatmap estilo GitHub baseado nas datas reais de estudo.
    """
    # Filtra apenas itens estudados com data válida
    df_filtrado = df[df['Estudado'] & df['Data_Real'].notnull()].copy()
    
    if df_filtrado.empty:
        return None
        
    # Agrega contagem por dia
    contagem_diaria = df_filtrado.groupby('Data_Real').size().reset_index(name='count')
    
    # Configuração do Gráfico Altair
    chart = alt.Chart(contagem_diaria).mark_rect(
        cornerRadius=3, 
        stroke='white', 
        strokeWidth=1
    ).encode(
        x=alt.X('yearmonthdate(Data_Real):O', 
                title=None, 
                axis=alt.Axis(format='%d/%m', labelFontSize=10, labelColor='#64748b')
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
            alt.Tooltip('count', title='Tópicos Concluídos')
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

def criar_grafico_donut(concluido, total, cor_primaria):
    """
    Cria um gráfico de Donut minimalista sem legenda.
    """
    restante = total - concluido
    
    dados = pd.DataFrame({
        'Categoria': ['Concluído', 'Restante'],
        'Valor': [concluido, restante]
    })
    
    base = alt.Chart(dados).encode(
        theta=alt.Theta("Valor", stack=True)
    )
    
    # Arco Principal
    pie = base.mark_arc(
        outerRadius=75, 
        innerRadius=58, 
        stroke='white', 
        strokeWidth=3,
        cornerRadius=4
    ).encode(
        color=alt.Color("Categoria", 
                        scale=alt.Scale(domain=['Concluído', 'Restante'], 
                                        range=[cor_primaria, '#e2e8f0']), 
                        legend=None),
        tooltip=["Categoria", "Valor"]
    )
    
    # Texto Central (Porcentagem)
    percentual = int(concluido/total*100) if total > 0 else 0
    texto = base.mark_text(
        radius=0, 
        size=20, 
        color=cor_primaria, 
        fontWeight='bold',
        font='Inter'
    ).encode(
        text=alt.value(f"{percentual}%")
    )
    
    return (pie + texto).properties(width=180, height=180)

# ================================================================================
# 6. APLICAÇÃO PRINCIPAL (FRONTEND)
# ================================================================================

def main():
    # 6.1. DADOS DO HEADER
    temp_atual = obter_temperatura_local()
    data_atual = datetime.now().strftime('%d/%m/%Y')
    
    # 6.2. RENDERIZAÇÃO DO HEADER
    st.markdown(f"""
    <div class="header-container">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Logo Câmara de Goiânia">
        </div>
        <div class="header-content">
            <h1>DASHBOARD ULTIMATE</h1>
            <p>Performance • Constância • Aprovação</p>
        </div>
        <div class="header-info">
            <div class="info-row">📍 GOIÂNIA - GO</div>
            <div class="info-row">📅 {data_atual}</div>
            <div class="info-row">🌡️ {temp_atual}°C</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 6.3. INICIALIZAÇÃO E CARREGAMENTO
    client = conectar_google_sheets()
    if not client:
        st.stop()
    
    # Carregamento com Feedback
    df = carregar_dados_planilha(client)
    
    if df is None:
        st.warning("Aguardando dados...")
        st.stop()

    # 6.4. SIDEBAR E FILTROS
    cargos_disponiveis = df['Cargo'].unique()
    
    # Seletor de Cargo (Padrão no Sidebar)
    cargo_selecionado = st.sidebar.selectbox("Selecione o Cargo:", cargos_disponiveis)
    
    # Filtra DataFrame pelo cargo
    df_cargo = df[df['Cargo'] == cargo_selecionado].copy()
    
    # Adiciona índice original para permitir atualização correta
    # O índice do pandas começa em 0, o gspread começa em 1, e temos cabeçalho (linha 1)
    # Logo, linha real = index + 2
    df_cargo['linha_planilha'] = df_cargo.index + 2

    # 6.5. CÁLCULOS DE KPIs
    total_topicos = len(df_cargo)
    total_concluidos = df_cargo['Estudado'].sum()
    total_restantes = total_topicos - total_concluidos
    progresso_geral = (total_concluidos / total_topicos * 100) if total_topicos > 0 else 0

    # 6.6. SISTEMA DE GAMIFICAÇÃO (BADGES)
    lista_badges = []
    if progresso_geral >= 10: lista_badges.append("🚀 Start (10%)")
    if progresso_geral >= 25: lista_badges.append("🏃 Em Ritmo (25%)")
    if progresso_geral >= 50: lista_badges.append("🔥 Halfway (50%)")
    if progresso_geral >= 75: lista_badges.append("💎 Elite (75%)")
    if total_concluidos > 100: lista_badges.append("📚 Legend (100+)")
    
    html_badges = '<div class="badge-container">'
    for badge in lista_badges:
        html_badges += f'<div class="badge">✨ {badge}</div>'
    html_badges += '</div>'
    st.markdown(html_badges, unsafe_allow_html=True)

    # 6.7. CARDS DE MÉTRICAS
    col1, col2, col3, col4 = st.columns(4)
    
    col1.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#3b82f6">{total_topicos}</div>
        <div class="metric-label">Total de Tópicos</div>
    </div>
    """, unsafe_allow_html=True)
    
    col2.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#22c55e">{total_concluidos}</div>
        <div class="metric-label">Concluídos</div>
    </div>
    """, unsafe_allow_html=True)
    
    col3.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#ef4444">{total_restantes}</div>
        <div class="metric-label">Restantes</div>
    </div>
    """, unsafe_allow_html=True)
    
    col4.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#8b5cf6">{progresso_geral:.0f}%</div>
        <div class="metric-label">Progresso Geral</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("") # Espaçamento

    # 6.8. HEATMAP DE PRODUTIVIDADE REAL
    st.markdown("### 🔥 Seu Ritmo de Estudos (Dados Reais)")
    st.markdown('<div class="heatmap-container">', unsafe_allow_html=True)
    
    grafico_heatmap = criar_heatmap_produtividade(df_cargo)
    
    if grafico_heatmap:
        st.altair_chart(grafico_heatmap, use_container_width=True)
    else:
        st.info("⚠️ Histórico vazio. Marque tópicos hoje para começar a visualizar seu ritmo!")
        
    st.markdown('</div>', unsafe_allow_html=True)

    # 6.9. GRÁFICOS DE PIZZA POR DISCIPLINA
    st.markdown("### 🍩 Progresso por Disciplina")
    
    # Agrupamento de dados
    stats_disciplina = df_cargo.groupby('Disciplinas').agg({
        'Estudado': ['sum', 'count']
    }).reset_index()
    stats_disciplina.columns = ['Disciplina', 'Estudados', 'Total']
    
    # Grid de 3 colunas
    grid_cols = st.columns(3)
    
    for index, row in stats_disciplina.iterrows():
        coluna_atual = grid_cols[index % 3]
        
        with coluna_atual:
            nome_disc = row['Disciplina']
            cor_disc = CORES.get(nome_disc, '#64748b')
            
            st.markdown(f"""
            <div style='text-align:center; font-weight:700; color:{cor_disc}; margin-bottom:10px;'>
                {nome_disc}
            </div>
            """, unsafe_allow_html=True)
            
            chart = criar_grafico_donut(row['Estudados'], row['Total'], cor_disc)
            st.altair_chart(chart, use_container_width=True)

    # 6.10. CHECKLIST DE CONTEÚDOS (CLEAN TABLE)
    st.markdown("### 📚 Conteúdo Programático Detalhado")
    
    # Filtro de Disciplina
    lista_disciplinas = sorted(df_cargo['Disciplinas'].unique().tolist())
    filtro_disc = st.selectbox("Filtrar por Disciplina:", ["Todas"] + lista_disciplinas)
    
    # Aplica filtro na visualização
    if filtro_disc != "Todas":
        view_df = df_cargo[df_cargo['Disciplinas'] == filtro_disc]
    else:
        view_df = df_cargo

    # Loop por Disciplina
    for disciplina in view_df['Disciplinas'].unique():
        sub_df = view_df[view_df['Disciplinas'] == disciplina]
        cor_tema = CORES.get(disciplina, '#333')
        
        # Header da Seção da Disciplina
        st.markdown(f"""
        <div style="margin-top:30px; border-bottom:2px solid {cor_tema}; padding-bottom:5px; margin-bottom:15px;">
            <strong style="color:{cor_tema}; font-size:1.1rem">{disciplina}</strong>
            <span style="float:right; color:#94a3b8; font-size:0.9rem">
                {sub_df['Estudado'].sum()}/{len(sub_df)}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Renderização das Linhas (Tabela Clean)
        for idx, row in sub_df.iterrows():
            col_check, col_text = st.columns([0.05, 0.95])
            
            with col_check:
                # Checkbox nativo
                is_checked = st.checkbox(
                    "Concluído", 
                    value=bool(row['Estudado']), 
                    key=f"chk_{idx}_{row['linha_planilha']}", 
                    label_visibility="collapsed"
                )
            
            # LÓGICA DE ATUALIZAÇÃO (SÓ EXECUTA SE HOUVER MUDANÇA)
            if is_checked != bool(row['Estudado']):
                with st.spinner("Sincronizando..."):
                    sucesso = atualizar_status(
                        client, 
                        int(row['linha_planilha']), 
                        is_checked
                    )
                    
                    if sucesso:
                        st.toast("Status Salvo com Sucesso!", icon="💾")
                        time.sleep(0.5) # Pequeno delay para UX
                        st.cache_data.clear() # Limpa cache para recarregar dados novos
                        st.rerun() # Recarrega a interface
                    else:
                        st.error("Falha na sincronização.")

            # Formatação Visual do Texto
            classe_css = "done" if row['Estudado'] else ""
            
            # Badge de Data (Se existir)
            badge_data = ""
            if row['Estudado'] and pd.notnull(row['Data_Real']):
                data_str = row['Data_Real'].strftime('%d/%m')
                badge_data = f"<span class='topic-date'>Concluído em: {data_str}</span>"
            
            col_text.markdown(f"""
            <div class="topic-row">
                <div class="topic-text {classe_css}">
                    {row['Conteúdos']} {badge_data}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 6.11. FOOTER
    st.markdown(f"""
    <div style="text-align:center; color:#94a3b8; padding:4rem 0 2rem 0; font-size:0.8rem; border-top:1px solid #e2e8f0; margin-top:3rem;">
        Dashboard Ultimate v3.0 • Desenvolvido com Python & Streamlit <br>
        Atualizado em {datetime.now().strftime("%H:%M:%S")}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
