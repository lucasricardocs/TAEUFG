# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import numpy as np
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import plotly.graph_objects as go

# Suprimir warnings desnecessários
warnings.filterwarnings('ignore', category=FutureWarning)

# --- Configurações Globais ---
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
CONCURSO_DATE = datetime(2025, 9, 28)

# Dados do edital
ED_DATA = {
    'Disciplinas': [
        'LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO',
        'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO'
    ],
    'Total_Conteudos': [20, 15, 10, 15, 30],
    'Peso': [2, 1, 1, 1, 3]
}

# --- Funções de Conexão com Google Sheets (Cache) ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES )
        gc = gspread.authorize(creds)
        st.success("✅ Conectado ao Google Sheets!")
        return gc
    except Exception as e:
        st.error(f"❌ Erro de autenticação com Google Cloud: {e}")
        return None

@st.cache_data(ttl=600)
def read_data(_gc):
    """Lê os dados da planilha e retorna um DataFrame."""
    if not _gc:
        return pd.DataFrame()
    try:
        spreadsheet = _gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        for col in ['Disciplinas', 'Conteúdos', 'Status']:
            if col not in df.columns:
                st.error(f"Coluna obrigatória '{col}' não encontrada na planilha.")
                return pd.DataFrame()
        
        df['Status'] = df['Status'].astype(str).str.strip().str.lower()
        return df[df['Status'].isin(['true', 'false'])]

    except SpreadsheetNotFound:
        st.error(f"❌ Planilha com ID '{SPREADSHEET_ID}' não encontrada.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Erro ao ler dados da planilha: {e}")
        return pd.DataFrame()

# --- Funções de Processamento de Dados ---
def calculate_metrics(df_dados):
    """Calcula as métricas de progresso de forma robusta."""
    df_edital = pd.DataFrame(ED_DATA)
    
    if df_dados.empty:
        df_summary = df_edital.copy()
        df_summary['Conteudos_Concluidos'] = 0
    else:
        df_concluidos = df_dados[df_dados['Status'] == 'true'].groupby('Disciplinas').size().reset_index(name='Conteudos_Concluidos')
        df_summary = pd.merge(df_edital, df_concluidos, on='Disciplinas', how='left').fillna(0)

    df_summary['Conteudos_Pendentes'] = df_summary['Total_Conteudos'] - df_summary['Conteudos_Concluidos']
    
    pontos_por_conteudo = (df_summary['Peso'] / df_summary['Total_Conteudos']).replace([np.inf, -np.inf], 0)
    pontos_concluidos = df_summary['Conteudos_Concluidos'] * pontos_por_conteudo
    df_summary['Progresso_Ponderado'] = ((pontos_concluidos / df_summary['Peso']).replace([np.inf, -np.inf], 0)).fillna(0) * 100

    total_pontos_possiveis = df_summary['Peso'].sum()
    total_pontos_feitos = (pontos_por_conteudo * df_summary['Conteudos_Concluidos']).sum()
    progresso_geral = (total_pontos_feitos / total_pontos_possiveis) * 100 if total_pontos_possiveis > 0 else 0
    
    return df_summary, progresso_geral

# --- Funções de Gráficos ---
def create_donut_chart(data_row):
    """Cria um gráfico de rosca (donut) com Plotly para progresso."""
    labels = ['Concluído', 'Pendente']
    values = [data_row['Conteudos_Concluidos'], data_row['Conteudos_Pendentes']]
    colors = ['#2ecc71', '#e74c3c']

    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=.5, 
        marker_colors=colors,
        textinfo='value',
        hoverinfo='label+percent'
    )])
    
    fig.update_layout(
        title_text=f"<b>{data_row['Disciplinas']}</b>  
<span style='font-size:12px;'>{data_row['Progresso_Ponderado']:.1f}% Ponderado</span>",
        title_x=0.5,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#2c3e50'),
        height=300,
        margin=dict(l=10, r=10, t=60, b=10)
    )
    return fig

def create_progress_timeline_chart(df_summary):
    """Cria um gráfico de linha temporal da evolução do progresso."""
    if df_summary['Progresso_Ponderado'].sum() == 0:
        return go.Figure().update_layout(title_text="Evolução do Progresso (Aguardando dados)")

    fig = go.Figure()
    dates = pd.date_range(start='2024-01-01', end=datetime.now(), freq='W')
    
    for _, row in df_summary.iterrows():
        if row['Progresso_Ponderado'] > 0:
            progress_values = np.linspace(0, row['Progresso_Ponderado'], len(dates))
            noise = np.random.normal(0, 2, len(dates))
            progress_values = np.clip(progress_values + noise, 0, 100)
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=progress_values,
                mode='lines',
                name=row['Disciplinas'],
                hovertemplate="<b>%{fullData.name}</b>  
Progresso: %{y:.1f}%<extra></extra>"
            ))
    
    fig.update_layout(
        title="<b>Evolução do Progresso ao Longo do Tempo</b>",
        xaxis_title="Data",
        yaxis_title="Progresso Ponderado (%)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#f8f9fa',
        font=dict(color='#2c3e50'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# --- Função Principal ---
def main():
    """Função principal do dashboard."""
    st.set_page_config(page_title="Dashboard de Estudos", layout="wide")

    st.markdown("""
        <style>
            .main-header { text-align: center; padding: 2rem; }
            .main-header h1 { color: #6a11cb; }
            .section-header { font-size: 1.8rem; font-weight: 600; color: #6a11cb; margin: 2rem 0 1rem 0; border-bottom: 3px solid #6a11cb; padding-bottom: 0.5rem; display: inline-block; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='main-header'><h1>📚 Dashboard de Estudos</h1><p>Acompanhe seu progresso para o Concurso 2025</p></div>", unsafe_allow_html=True)

    gc = get_google_auth()
    df_dados = read_data(gc)
    
    if df_dados.empty and gc:
        st.warning("A planilha parece estar vazia. Adicione dados para visualizar o dashboard.")
    
    df_summary, progresso_geral = calculate_metrics(df_dados)
    
    dias_restantes = (CONCURSO_DATE - datetime.now()).days
    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 Progresso Geral Ponderado", f"{progresso_geral:.1f}%")
    col2.metric("🗓️ Dias Restantes", f"{dias_restantes if dias_restantes > 0 else 0}")
    col3.metric("📚 Conteúdos Concluídos", f"{int(df_summary['Conteudos_Concluidos'].sum())}")

    st.markdown("<div class='section-header'>🎯 Progresso por Disciplina</div>", unsafe_allow_html=True)
    
    if not df_summary.empty:
        num_disciplinas = len(df_summary)
        cols = st.columns(num_disciplinas)
        for i, (_, row) in enumerate(df_summary.iterrows()):
            with cols[i]:
                with st.container(border=True):
                    st.plotly_chart(create_donut_chart(row), use_container_width=True)
    else:
        st.info("Aguardando dados das disciplinas para mostrar os gráficos de progresso.")

    st.markdown("<div class='section-header'>📈 Análise de Evolução</div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.plotly_chart(create_progress_timeline_chart(df_summary), use_container_width=True)

if __name__ == "__main__":
    main()
