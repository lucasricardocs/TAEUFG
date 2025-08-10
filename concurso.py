# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Suprimir warnings específicos do pandas
warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

# --- Configurações Globais e Constantes ---

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
CONCURSO_DATE = datetime(2025, 9, 28)  # Data do concurso

# Dados do edital (para calcular o progresso ponderado)
ED_DATA = {
    'Disciplinas': [
        'LÍNGUA PORTUGUESA',
        'RLM',
        'INFORMÁTICA',
        'LEGISLAÇÃO',
        'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO'
    ],
    'Total_Conteudos': [20, 15, 10, 15, 30],
    'Peso': [2, 1, 1, 1, 3]
}

# --- Funções de Cache para Acesso ao Google Sheets ---
@st.cache_resource
def get_google_auth():
    """Autoriza o acesso ao Google Sheets e retorna o cliente gspread."""
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/spreadsheets.readonly'
    ]
    
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Credenciais do Google Cloud ('gcp_service_account') não encontradas. Configure o arquivo .streamlit/secrets.toml")
            st.info("""
            **Como configurar:**
            1. Crie o arquivo `.streamlit/secrets.toml` na raiz do projeto
            2. Adicione as credenciais do GCP na seção [gcp_service_account]
            3. Para deploy no Streamlit Cloud: Settings → Secrets
            """)
            return None
        
        credentials_dict = st.secrets["gcp_service_account"]
        if not credentials_dict:
            st.error("❌ As credenciais do Google Cloud em st.secrets estão vazias.")
            return None
        
        required_keys = ['type', 'project_id', 'private_key', 'client_email', 'client_id', 'auth_uri', 'token_uri']
        missing_keys = [key for key in required_keys if key not in credentials_dict]
        
        if missing_keys:
            st.error(f"❌ Chaves obrigatórias ausentes nas credenciais: {missing_keys}")
            return None
            
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        
        try:
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            st.success("✅ Conectado ao Google Sheets com sucesso!")
        except Exception as e:
            st.warning(f"⚠️ Credenciais válidas, mas possível erro de acesso: {e}")
            
        return gc
        
    except Exception as e:
        st.error(f"❌ Erro de autenticação com Google Cloud: {e}")
        return None

@st.cache_resource
def get_worksheet():
    """Retorna o objeto worksheet da planilha especificada."""
    gc = get_google_auth()
    if gc:
        try:
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"❌ Planilha com ID '{SPREADSHEET_ID}' não encontrada.")
            return None
        except Exception as e:
            st.error(f"❌ Erro ao acessar a aba '{WORKSHEET_NAME}': {e}")
            return None
    return None

@st.cache_data(ttl=600)
def read_sales_data():
    """Lê todos os registros da planilha e retorna como DataFrame."""
    worksheet = get_worksheet()
    if not worksheet:
        # Dados de exemplo para demonstração
        sample_data = []
        np.random.seed(42)
        for disciplina in ED_DATA['Disciplinas']:
            for i in range(np.random.randint(5, 15)):
                status = 'true' if np.random.rand() < 0.5 else 'false'
                sample_data.append({'Disciplinas': disciplina, 'Conteúdos': f'Tópico {i+1}', 'Status': status})
        
        return pd.DataFrame(sample_data)

    try:
        with st.spinner("📊 Carregando dados da planilha..."):
            data = worksheet.get_all_values()
            
        if not data or len(data) < 2:
            st.warning("⚠️ Planilha vazia ou sem dados suficientes.")
            return pd.DataFrame()
            
        headers = data[0]
        records = data[1:]
        df = pd.DataFrame(records, columns=headers)
        
        required_columns = ['Disciplinas', 'Conteúdos', 'Status']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"❌ Colunas obrigatórias não encontradas: {missing_columns}")
            return pd.DataFrame()
        
        # Limpar e filtrar dados
        df['Status'] = df['Status'].astype(str).str.strip()
        df['Disciplinas'] = df['Disciplinas'].astype(str).str.strip()
        df['Conteúdos'] = df['Conteúdos'].astype(str).str.strip()
        
        # Filtrar apenas status válidos
        df_filtrado = df[df['Status'].str.lower().isin(['true', 'false'])]
        
        # Remover linhas vazias
        df_final = df_filtrado[
            (df_filtrado['Disciplinas'] != '') & 
            (df_filtrado['Disciplinas'] != 'nan') &
            (df_filtrado['Disciplinas'].notna())
        ].copy()
        
        # Padronizar o Status
        df_final['Status'] = df_final['Status'].str.lower().str.title()
        
        return df_final
        
    except Exception as e:
        st.error(f"❌ Erro ao ler dados da planilha: {e}")
        return pd.DataFrame()

# --- Funções de Processamento de Dados ---
def calculate_weighted_metrics(df_dados):
    """Calcula métricas de progresso ponderado com base no edital."""
    df_edital = pd.DataFrame(ED_DATA)
    
    if df_dados.empty or 'Disciplinas' not in df_dados.columns or 'Status' not in df_dados.columns:
        return pd.DataFrame(), 0.0

    df_dados = df_dados.copy()
    df_dados['Status'] = df_dados['Status'].astype(str).str.strip()
    df_dados['true'] = (df_dados['Status'].str.lower() == 'true').astype(int)
    df_dados['false'] = (df_dados['Status'].str.lower() == 'false').astype(int)
    
    df_progresso_summary = df_dados.groupby('Disciplinas', observed=False).agg(
        Conteudos_trues=('true', 'sum'),
        Conteudos_falses=('false', 'sum')
    ).reset_index()
    
    df_final = pd.merge(df_edital, df_progresso_summary, on='Disciplinas', how='left').fillna(0)
    
    df_final['Total_Conteudos_Real'] = df_final['Conteudos_trues'] + df_final['Conteudos_falses']
    df_final['Pontos_por_Conteudo'] = np.where(
        df_final['Total_Conteudos'] > 0,
        df_final['Peso'] / df_final['Total_Conteudos'],
        0
    )
    df_final['Pontos_Concluidos'] = df_final['Conteudos_trues'] * df_final['Pontos_por_Conteudo']
    df_final['Pontos_Totais'] = df_final['Total_Conteudos'] * df_final['Pontos_por_Conteudo']
    df_final['Pontos_falses'] = df_final['Pontos_Totais'] - df_final['Pontos_Concluidos']
    
    df_final['Progresso_Ponderado'] = np.where(
        df_final['Peso'] > 0,
        np.round(df_final['Pontos_Concluidos'] / df_final['Peso'] * 100, 1),
        0
    )
    
    # Calcular percentuais adicionais
    df_final['Percentual_Concluido'] = np.where(
        df_final['Total_Conteudos_Real'] > 0,
        np.round((df_final['Conteudos_trues'] / df_final['Total_Conteudos_Real']) * 100, 1),
        0
    )
    
    total_pontos = df_final['Peso'].sum()
    total_pontos_concluidos = df_final['Pontos_Concluidos'].sum()
    progresso_ponderado_geral = round(
        (total_pontos_concluidos / total_pontos) * 100, 1
    ) if total_pontos > 0 else 0
    
    return df_final, progresso_ponderado_geral

def calculate_statistics(df_dados, df_summary):
    """Calcula estatísticas adicionais para o dashboard."""
    stats = {}
    
    # Tempo restante para o concurso
    hoje = datetime.now()
    tempo_restante = CONCURSO_DATE - hoje
    stats['dias_restantes'] = tempo_restante.days
    stats['horas_restantes'] = tempo_restante.seconds // 3600
    
    # Total de conteúdos
    stats['total_conteudos'] = len(df_dados) if not df_dados.empty else 0
    stats['total_concluidos'] = len(df_dados[df_dados['Status'] == 'True']) if not df_dados.empty else 0
    stats['total_falses'] = len(df_dados[df_dados['Status'] == 'False']) if not df_dados.empty else 0
    
    # Percentual geral de conclusão
    if stats['total_conteudos'] > 0:
        stats['percentual_geral'] = round((stats['total_concluidos'] / stats['total_conteudos']) * 100, 1)
    else:
        stats['percentual_geral'] = 0
    
    # Cálculo de tópicos por dia
    conteudos_restantes = stats['total_falses']
    if stats['dias_restantes'] > 0 and conteudos_restantes > 0:
        stats['topicos_por_dia'] = round(conteudos_restantes / stats['dias_restantes'], 1)
    else:
        stats['topicos_por_dia'] = 0
    
    # Disciplina com maior e menor progresso
    if not df_summary.empty:
        stats['disciplina_maior_progresso'] = df_summary.loc[df_summary['Progresso_Ponderado'].idxmax(), 'Disciplinas']
        stats['disciplina_menor_progresso'] = df_summary.loc[df_summary['Progresso_Ponderado'].idxmin(), 'Disciplinas']
        
        # Disciplina com maior prioridade (menor progresso * maior peso)
        df_summary['Prioridade'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
        stats['disciplina_maior_prioridade'] = df_summary.loc[df_summary['Prioridade'].idxmax(), 'Disciplinas']
    
    return stats

def calculate_daily_study_plan(df_dados, df_summary):
    """Calcula plano de estudos diário por disciplina."""
    hoje = datetime.now()
    tempo_restante = CONCURSO_DATE - hoje
    dias_restantes = tempo_restante.days
    
    if dias_restantes <= 0:
        return pd.DataFrame()
    
    plano_estudos = []
    
    for _, row in df_summary.iterrows():
        disciplina = row['Disciplinas']
        conteudos_restantes = int(row['Conteudos_falses'])
        peso = int(row['Peso'])
        
        if conteudos_restantes > 0:
            # Calcular tópicos por dia para esta disciplina
            topicos_por_dia = round(conteudos_restantes / dias_restantes, 1)
            
            # Calcular prioridade baseada no peso e progresso
            prioridade_score = peso * (100 - row['Progresso_Ponderado'])
            
            # Estimar tempo necessário por tópico (baseado no peso)
            tempo_por_topico = peso * 30  # 30 min base * peso
            tempo_diario_disciplina = topicos_por_dia * tempo_por_topico
            
            plano_estudos.append({
                'Disciplina': disciplina,
                'Conteudos_Restantes': conteudos_restantes,
                'Topicos_Por_Dia': topicos_por_dia,
                'Tempo_Diario_Min': round(tempo_diario_disciplina),
                'Prioridade_Score': round(prioridade_score, 1),
                'Peso': peso,
                'Progresso_Atual': row['Progresso_Ponderado']
            })
    
    df_plano = pd.DataFrame(plano_estudos)
    if not df_plano.empty:
        df_plano = df_plano.sort_values('Prioridade_Score', ascending=False)
    
    return df_plano

# --- Funções de Design e Gráficos ---
def apply_dark_animated_theme():
    """Aplica CSS com tema escuro animado e melhorias de UX/UI."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Animação de fundo escuro */
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        /* Reset e configurações globais */
        .stApp {
            background: linear-gradient(-45deg, #1a1a2e, #16213e, #0f3460, #1a1a2e);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            color: #ffffff;
        }
        
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #ffffff;
        }
        
        /* Header principal */
        .main-header {
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, rgba(26, 26, 46, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            margin-bottom: 2rem;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            animation: fadeInUp 1s ease-out;
        }
        
        .main-header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #64ffda, #1de9b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .main-header p {
            font-size: 1.3rem;
            opacity: 0.8;
            color: #b0bec5;
        }
        
        /* Containers de estatísticas */
        .stats-container {
            background: linear-gradient(135deg, rgba(26, 26, 46, 0.8) 0%, rgba(22, 33, 62, 0.8) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
            margin-bottom: 2rem;
            backdrop-filter: blur(10px);
            animation: fadeInUp 1s ease-out 0.2s both;
        }
        
        .stat-card {
            text-align: center;
            padding: 1.5rem;
            background: linear-gradient(135deg, rgba(100, 255, 218, 0.1) 0%, rgba(29, 233, 182, 0.1) 100%);
            border: 1px solid rgba(100, 255, 218, 0.2);
            border-radius: 12px;
            margin: 0.5rem 0;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(100, 255, 218, 0.2);
            border-color: rgba(100, 255, 218, 0.4);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: #64ffda;
            margin-bottom: 0.25rem;
            animation: pulse 2s infinite;
        }
        
        .stat-label {
            font-size: 1rem;
            color: #b0bec5;
            font-weight: 500;
        }
        
        /* Headers de seção */
        .section-header {
            font-size: 1.8rem;
            font-weight: 600;
            color: #64ffda;
            margin: 2rem 0 1rem 0;
            border-bottom: 3px solid #64ffda;
            padding-bottom: 0.5rem;
            display: inline-block;
            animation: fadeInUp 1s ease-out 0.4s both;
        }
        
        /* Containers de gráficos */
        .chart-container {
            background: linear-gradient(135deg, rgba(26, 26, 46, 0.8) 0%, rgba(22, 33, 62, 0.8) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
            margin-bottom: 1.5rem;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
            animation: fadeInUp 1s ease-out 0.6s both;
        }
        
        .chart-container:hover {
            transform: translateY(-3px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        /* Container de disciplina */
        .disciplina-container {
            background: linear-gradient(135deg, rgba(26, 26, 46, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
            border: 2px solid rgba(100, 255, 218, 0.3);
            border-radius: 20px;
            padding: 2rem;
            margin: 2rem 0;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(15px);
            animation: fadeInUp 1s ease-out 0.8s both;
        }
        
        .disciplina-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #64ffda;
            margin-bottom: 1rem;
            text-align: center;
            padding: 1rem;
            background: linear-gradient(135deg, rgba(100, 255, 218, 0.1) 0%, rgba(29, 233, 182, 0.1) 100%);
            border-radius: 10px;
            border: 1px solid rgba(100, 255, 218, 0.2);
        }
        
        /* Grid de progresso */
        .progress-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }
        
        /* Métricas aprimoradas */
        .metric-container {
            background: linear-gradient(135deg, #64ffda 0%, #1de9b6 100%);
            color: #1a1a2e;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            margin: 1rem 0;
            box-shadow: 0 15px 35px rgba(100, 255, 218, 0.3);
            transition: all 0.3s ease;
        }
        
        .metric-container:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(100, 255, 218, 0.4);
        }
        
        .metric-value {
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            font-size: 1.2rem;
            opacity: 0.9;
            font-weight: 600;
        }
        
        /* Alertas e notificações */
        .stAlert > div {
            background: linear-gradient(135deg, rgba(26, 26, 46, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
            border: 1px solid rgba(100, 255, 218, 0.3);
            border-radius: 10px;
            color: #ffffff;
            backdrop-filter: blur(10px);
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem 0;
            color: #b0bec5;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            margin-top: 3rem;
            animation: fadeInUp 1s ease-out 1s both;
        }
        
        /* Scrollbar personalizada */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(26, 26, 46, 0.5);
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #64ffda, #1de9b6);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #1de9b6, #64ffda);
        }
        
        /* Remover elementos transparentes desnecessários */
        .stSelectbox > div > div {
            background: linear-gradient(135deg, rgba(26, 26, 46, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
            border: 1px solid rgba(100, 255, 218, 0.3);
        }
        
        .stTextInput > div > div > input {
            background: linear-gradient(135deg, rgba(26, 26, 46, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
            border: 1px solid rgba(100, 255, 218, 0.3);
            color: #ffffff;
        }
        
        /* Botões */
        .stButton > button {
            background: linear-gradient(135deg, #64ffda 0%, #1de9b6 100%);
            color: #1a1a2e;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(100, 255, 218, 0.3);
        }
        </style>
    """, unsafe_allow_html=True)

def create_radial_chart(data_row):
    """Cria um gráfico radial (polar) com cores verde para true e vermelho para false."""
    # Preparar dados
    concluido = int(data_row['Conteudos_trues'])
    nao_concluido = int(data_row['Conteudos_falses'])
    total = concluido + nao_concluido
    
    if total == 0:
        return go.Figure()
    
    # Criar dados para o gráfico radial
    theta = []
    r = []
    colors = []
    
    # Adicionar segmentos concluídos (verde)
    for i in range(concluido):
        theta.append(i * (360 / total))
        r.append(1)
        colors.append('#00ff88')
    
    # Adicionar segmentos não concluídos (vermelho)
    for i in range(nao_concluido):
        theta.append((concluido + i) * (360 / total))
        r.append(1)
        colors.append('#ff4444')
    
    # Criar o gráfico
    fig = go.Figure()
    
    # Adicionar barras radiais
    fig.add_trace(go.Barpolar(
        r=r,
        theta=theta,
        width=[360/total] * total,
        marker=dict(
            color=colors,
            line=dict(color='rgba(255,255,255,0.2)', width=1)
        ),
        hovertemplate='<b>%{theta}°</b><br>Status: %{customdata}<extra></extra>',
        customdata=['Concluído' if c == '#00ff88' else 'Pendente' for c in colors],
        showlegend=False
    ))
    
    # Configurar layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=False,
                range=[0, 1.2]
            ),
            angularaxis=dict(
                visible=False,
                direction='clockwise',
                period=360
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        title=dict(
            text=f"<b>{data_row['Disciplinas'][:30]}</b><br><span style='font-size:14px'>{data_row['Progresso_Ponderado']:.1f}% Concluído</span>",
            x=0.5,
            font=dict(size=16, color='#64ffda')
        ),
        height=300,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_performance_radar_chart(df_summary):
    """Cria um gráfico radar mostrando o desempenho por disciplina."""
    if df_summary.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Adicionar trace para progresso ponderado
    fig.add_trace(go.Scatterpolar(
        r=df_summary['Progresso_Ponderado'].tolist(),
        theta=df_summary['Disciplinas'].tolist(),
        fill='toself',
        name='Progresso Ponderado',
        line=dict(color='#64ffda', width=3),
        fillcolor='rgba(100, 255, 218, 0.2)',
        hovertemplate='<b>%{theta}</b><br>Progresso: %{r:.1f}%<extra></extra>'
    ))
    
    # Adicionar trace para percentual simples
    fig.add_trace(go.Scatterpolar(
        r=df_summary['Percentual_Concluido'].tolist(),
        theta=df_summary['Disciplinas'].tolist(),
        fill='toself',
        name='Percentual Simples',
        line=dict(color='#1de9b6', width=2),
        fillcolor='rgba(29, 233, 182, 0.1)',
        hovertemplate='<b>%{theta}</b><br>Percentual: %{r:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color='white'),
                gridcolor='rgba(255,255,255,0.2)'
            ),
            angularaxis=dict(
                tickfont=dict(color='white'),
                gridcolor='rgba(255,255,255,0.2)'
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        title=dict(
            text="<b>Radar de Desempenho por Disciplina</b>",
            x=0.5,
            font=dict(size=18, color='#64ffda')
        ),
        legend=dict(
            font=dict(color='white'),
            bgcolor='rgba(26, 26, 46, 0.8)',
            bordercolor='rgba(100, 255, 218, 0.3)',
            borderwidth=1
        ),
        height=500
    )
    
    return fig

def create_progress_timeline_chart(df_summary):
    """Cria um gráfico de linha temporal do progresso."""
    if df_summary.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Simular dados de progresso ao longo do tempo (para demonstração)
    dates = pd.date_range(start='2024-01-01', end=datetime.now(), freq='W')
    
    for idx, row in df_summary.iterrows():
        # Simular progresso crescente ao longo do tempo
        progress_values = np.cumsum(np.random.exponential(2, len(dates)))
        progress_values = (progress_values / progress_values[-1]) * row['Progresso_Ponderado']
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=progress_values,
            mode='lines+markers',
            name=row['Disciplinas'][:15],
            line=dict(width=3),
            marker=dict(size=6),
            hovertemplate='<b>%{fullData.name}</b><br>Data: %{x}<br>Progresso: %{y:.1f}%<extra></extra>'
        ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        title=dict(
            text="<b>Evolução do Progresso ao Longo do Tempo</b>",
            x=0.5,
            font=dict(size=18, color='#64ffda')
        ),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.2)',
            tickfont=dict(color='white'),
            title=dict(text='Data', font=dict(color='white'))
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.2)',
            tickfont=dict(color='white'),
            title=dict(text='Progresso (%)', font=dict(color='white'))
        ),
        legend=dict(
            font=dict(color='white'),
            bgcolor='rgba(26, 26, 46, 0.8)',
            bordercolor='rgba(100, 255, 218, 0.3)',
            borderwidth=1
        ),
        height=400
    )
    
    return fig

def create_priority_matrix_chart(df_summary):
    """Cria um gráfico de matriz de prioridades (Peso vs Progresso)."""
    if df_summary.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Calcular tamanho dos pontos baseado na prioridade
    df_summary['Prioridade'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
    max_prioridade = df_summary['Prioridade'].max()
    sizes = (df_summary['Prioridade'] / max_prioridade * 50) + 10
    
    fig.add_trace(go.Scatter(
        x=df_summary['Peso'],
        y=df_summary['Progresso_Ponderado'],
        mode='markers+text',
        marker=dict(
            size=sizes,
            color=df_summary['Progresso_Ponderado'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(
                title='Progresso (%)',
                tickfont=dict(color='white')
            ),
            line=dict(color='white', width=2)
        ),
        text=[disc[:10] + '...' if len(disc) > 10 else disc for disc in df_summary['Disciplinas']],
        textposition='middle center',
        textfont=dict(color='white', size=10),
        hovertemplate='<b>%{text}</b><br>Peso: %{x}<br>Progresso: %{y:.1f}%<br>Prioridade: %{customdata:.1f}<extra></extra>',
        customdata=df_summary['Prioridade']
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        title=dict(
            text="<b>Matriz de Prioridades (Peso vs Progresso)</b>",
            x=0.5,
            font=dict(size=18, color='#64ffda')
        ),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.2)',
            tickfont=dict(color='white'),
            title=dict(text='Peso da Disciplina', font=dict(color='white'))
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.2)',
            tickfont=dict(color='white'),
            title=dict(text='Progresso (%)', font=dict(color='white'))
        ),
        height=400
    )
    
    return fig

def create_daily_study_plan_chart(df_plano):
    """Cria um gráfico do plano de estudos diário."""
    if df_plano.empty:
        return go.Figure()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Tópicos por Dia por Disciplina', 'Tempo Diário Estimado (minutos)'),
        vertical_spacing=0.15,
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    # Gráfico de barras para tópicos por dia
    fig.add_trace(
        go.Bar(
            x=df_plano['Disciplina'],
            y=df_plano['Topicos_Por_Dia'],
            name='Tópicos/Dia',
            marker=dict(
                color=df_plano['Prioridade_Score'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title='Prioridade',
                    tickfont=dict(color='white'),
                    y=0.75
                )
            ),
            text=df_plano['Topicos_Por_Dia'],
            textposition='auto',
            textfont=dict(color='white'),
            hovertemplate='<b>%{x}</b><br>Tópicos/Dia: %{y}<br>Prioridade: %{customdata:.1f}<extra></extra>',
            customdata=df_plano['Prioridade_Score']
        ),
        row=1, col=1
    )
    
    # Gráfico de barras para tempo diário
    fig.add_trace(
        go.Bar(
            x=df_plano['Disciplina'],
            y=df_plano['Tempo_Diario_Min'],
            name='Tempo (min)',
            marker=dict(
                color='#1de9b6',
                opacity=0.8
            ),
            text=df_plano['Tempo_Diario_Min'],
            textposition='auto',
            textfont=dict(color='white'),
            hovertemplate='<b>%{x}</b><br>Tempo: %{y} min<br>Conteúdos Restantes: %{customdata}<extra></extra>',
            customdata=df_plano['Conteudos_Restantes']
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        title=dict(
            text="<b>Plano de Estudos Diário</b>",
            x=0.5,
            font=dict(size=18, color='#64ffda')
        ),
        showlegend=False,
        height=600
    )
    
    # Atualizar eixos
    fig.update_xaxes(
        tickfont=dict(color='white'),
        gridcolor='rgba(255,255,255,0.2)',
        tickangle=45
    )
    fig.update_yaxes(
        tickfont=dict(color='white'),
        gridcolor='rgba(255,255,255,0.2)'
    )
    
    return fig

# --- Função Principal ---
def main():
    """Função principal do dashboard."""
    st.set_page_config(
        page_title="📚 Dashboard de Estudos - Concurso 2025",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Aplicar tema escuro animado
    apply_dark_animated_theme()
    
    # Header principal
    st.markdown("""
        <div class="main-header">
            <h1>📚 Dashboard de Estudos</h1>
            <p>Acompanhe seu progresso para o Concurso 2025</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Carregar dados
    df_dados = read_sales_data()
    
    if df_dados.empty:
        st.error("❌ Não foi possível carregar os dados. Verifique a conexão com o Google Sheets.")
        return
    
    # Calcular métricas
    df_summary, progresso_geral = calculate_weighted_metrics(df_dados)
    stats = calculate_statistics(df_dados, df_summary)
    df_plano = calculate_daily_study_plan(df_dados, df_summary)
    
    # Seção de estatísticas principais
    st.markdown('<div class="section-header">📊 Estatísticas Gerais</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{progresso_geral:.1f}%</div>
                <div class="metric-label">Progresso Geral</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['dias_restantes']}</div>
                <div class="metric-label">Dias Restantes</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['total_concluidos']}</div>
                <div class="metric-label">Conteúdos Concluídos</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['total_conteudos']}</div>
                <div class="metric-label">Total de Conteúdos</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['topicos_por_dia']}</div>
                <div class="metric-label">Tópicos/Dia Necessários</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Seção de gráficos radiais por disciplina
    st.markdown('<div class="section-header">🎯 Progresso por Disciplina (Gráficos Radiais)</div>', unsafe_allow_html=True)
    
    # Criar grid de gráficos radiais
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_summary.iterrows()):
        with cols[idx % 3]:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig = create_radial_chart(row)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção de gráficos adicionais
    st.markdown('<div class="section-header">📈 Análises Avançadas</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        radar_fig = create_performance_radar_chart(df_summary)
        st.plotly_chart(radar_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        priority_fig = create_priority_matrix_chart(df_summary)
        st.plotly_chart(priority_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráfico de evolução temporal
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    timeline_fig = create_progress_timeline_chart(df_summary)
    st.plotly_chart(timeline_fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção do plano de estudos diário
    st.markdown('<div class="section-header">📅 Plano de Estudos Diário</div>', unsafe_allow_html=True)
    
    if not df_plano.empty:
        # Gráfico do plano de estudos
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        plano_fig = create_daily_study_plan_chart(df_plano)
        st.plotly_chart(plano_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Tabela detalhada do plano
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown("### 📋 Detalhamento do Plano de Estudos")
        
        # Formatação da tabela
        df_plano_display = df_plano.copy()
        df_plano_display['Disciplina'] = df_plano_display['Disciplina'].str[:30]
        df_plano_display['Tempo_Diario_Horas'] = (df_plano_display['Tempo_Diario_Min'] / 60).round(1)
        
        # Exibir tabela com formatação
        st.dataframe(
            df_plano_display[['Disciplina', 'Conteudos_Restantes', 'Topicos_Por_Dia', 'Tempo_Diario_Horas', 'Prioridade_Score']].rename(columns={
                'Disciplina': 'Disciplina',
                'Conteudos_Restantes': 'Conteúdos Restantes',
                'Topicos_Por_Dia': 'Tópicos/Dia',
                'Tempo_Diario_Horas': 'Tempo Diário (h)',
                'Prioridade_Score': 'Score Prioridade'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Resumo do tempo total
        tempo_total_diario = df_plano['Tempo_Diario_Min'].sum()
        st.markdown(f"""
            <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, rgba(100, 255, 218, 0.1) 0%, rgba(29, 233, 182, 0.1) 100%); border-radius: 10px; margin-top: 1rem;">
                <h3 style="color: #64ffda;">⏰ Tempo Total de Estudo Diário: {tempo_total_diario:.0f} minutos ({tempo_total_diario/60:.1f} horas)</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.info("🎉 Parabéns! Todos os conteúdos foram concluídos ou não há tempo suficiente para calcular o plano.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção de containers por disciplina
    st.markdown('<div class="section-header">📚 Detalhes por Disciplina</div>', unsafe_allow_html=True)
    
    for _, row in df_summary.iterrows():
        disciplina = row['Disciplinas']
        
        # Filtrar conteúdos da disciplina
        conteudos_disciplina = df_dados[df_dados['Disciplinas'] == disciplina]
        
        st.markdown(f"""
            <div class="disciplina-container">
                <div class="disciplina-title">{disciplina}</div>
        """, unsafe_allow_html=True)
        
        # Métricas da disciplina
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Progresso Ponderado", f"{row['Progresso_Ponderado']:.1f}%")
        
        with col2:
            st.metric("Conteúdos Concluídos", f"{int(row['Conteudos_trues'])}")
        
        with col3:
            st.metric("Conteúdos Pendentes", f"{int(row['Conteudos_falses'])}")
        
        with col4:
            st.metric("Peso", f"{int(row['Peso'])}")
        
        # Lista de conteúdos
        if not conteudos_disciplina.empty:
            st.markdown("**Conteúdos:**")
            for _, conteudo in conteudos_disciplina.iterrows():
                status_icon = "✅" if conteudo['Status'] == 'True' else "❌"
                status_color = "#00ff88" if conteudo['Status'] == 'True' else "#ff4444"
                st.markdown(f"""
                    <div style="padding: 0.5rem; margin: 0.25rem 0; background: rgba(255,255,255,0.05); border-radius: 8px; border-left: 4px solid {status_color};">
                        {status_icon} {conteudo['Conteúdos']}
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
        <div class="footer">
            <p>Dashboard desenvolvido para acompanhamento de estudos • Concurso 2025</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

