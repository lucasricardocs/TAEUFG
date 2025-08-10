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
    stats['total_concluidos'] = len(df_dados[df_dados['Status'] == 'true']) if not df_dados.empty else 0
    stats['total_falses'] = len(df_dados[df_dados['Status'] == 'false']) if not df_dados.empty else 0
    
    # Percentual geral de conclusão
    if stats['total_conteudos'] > 0:
        stats['percentual_geral'] = round((stats['total_concluidos'] / stats['total_conteudos']) * 100, 1)
    else:
        stats['percentual_geral'] = 0
    
    # Disciplina com maior e menor progresso
    if not df_summary.empty:
        stats['disciplina_maior_progresso'] = df_summary.loc[df_summary['Progresso_Ponderado'].idxmax(), 'Disciplinas']
        stats['disciplina_menor_progresso'] = df_summary.loc[df_summary['Progresso_Ponderado'].idxmin(), 'Disciplinas']
        
        # Disciplina com maior prioridade (menor progresso * maior peso)
        df_summary['Prioridade'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
        stats['disciplina_maior_prioridade'] = df_summary.loc[df_summary['Prioridade'].idxmax(), 'Disciplinas']
    
    return stats

# --- Funções de Design e Gráficos ---
def apply_enhanced_theme_css():
    """Aplica CSS aprimorado para tema moderno e profissional."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .main-header {
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }
        
        .main-header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .main-header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .stats-container {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            margin-bottom: 2rem;
            border: 1px solid #f0f0f0;
        }
        
        .stat-card {
            text-align: center;
            padding: 1rem;
            background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
            border-radius: 10px;
            border: 1px solid #e8ecf7;
            margin: 0.5rem 0;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 0.25rem;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #666;
            font-weight: 500;
        }
        
        .section-header {
            font-size: 1.5rem;
            font-weight: 600;
            color: #2c3e50;
            margin: 2rem 0 1rem 0;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.5rem;
            display: inline-block;
        }
        
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            margin-bottom: 1.5rem;
            border: 1px solid #f0f0f0;
        }
        
        .progress-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin: 1.5rem 0;
        }
        
        .footer {
            text-align: center;
            padding: 2rem 0;
            color: #666;
            border-top: 1px solid #eee;
            margin-top: 3rem;
        }
        
        .stAlert > div {
            background-color: rgba(255, 255, 255, 0.95);
            border-left: 4px solid #667eea;
            border-radius: 8px;
        }
        
        /* Melhorias para métricas */
        .metric-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            margin: 1rem 0;
        }
        
        .metric-value {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        </style>
    """, unsafe_allow_html=True)

def create_enhanced_donut_chart(data_row):
    """Cria um gráfico de rosca aprimorado e animado."""
    # Preparar dados para o gráfico
    concluido = data_row['Pontos_Concluidos']
    false = data_row['Pontos_falses']
    
    df_chart = pd.DataFrame({
        'Status': ['Concluído', 'false'],
        'Pontos': [concluido, false],
        'Percentual': [data_row['Progresso_Ponderado'], 100 - data_row['Progresso_Ponderado']],
        'order': [1, 2]  # Para controlar a ordem de animação
    })
    
    # Criar seleção para interatividade
    hover = alt.selection_single(on='mouseover', empty='all')
    
    # Gráfico de rosca com animação e gradiente
    donut = alt.Chart(df_chart).add_selection(hover).mark_arc(
        outerRadius=95,
        innerRadius=65,
        stroke='white',
        strokeWidth=4,
        cornerRadius=8,
        padAngle=0.02
    ).encode(
        theta=alt.Theta('Pontos:Q', stack=True),
        color=alt.Color(
            'Status:N',
            scale=alt.Scale(
                domain=['Concluído', 'false'],
                range=['#667eea', '#e74c3c']
            ),
            legend=None
        ),
        opacity=alt.condition(
            hover,
            alt.value(1.0),
            alt.value(0.85)
        ),
        stroke=alt.condition(
            hover,
            alt.value('#ffffff'),
            alt.value('#ffffff')
        ),
        strokeWidth=alt.condition(
            hover,
            alt.value(6),
            alt.value(4)
        ),
        tooltip=[
            alt.Tooltip('Status:N', title='Status'),
            alt.Tooltip('Pontos:Q', title='Pontos', format='.2f'),
            alt.Tooltip('Percentual:Q', title='Percentual', format='.1f%')
        ],
        order=alt.Order('order:O')
    ).transform_calculate(
        # Adicionar animação baseada em ordem
        angle_start='0',
        angle_end='datum.Pontos'
    )
    
    # Texto central com o percentual - maior e mais destacado
    text_center = alt.Chart(
        pd.DataFrame({
            'text': [f"{data_row['Progresso_Ponderado']:.1f}%"],
            'subtitle': ['Concluído']
        })
    ).mark_text(
        align='center',
        baseline='middle',
        fontSize=28,
        fontWeight='bold',
        color='#2c3e50'
    ).encode(
        text=alt.Text('text:N')
    )
    
    # Subtítulo no centro
    text_subtitle = alt.Chart(
        pd.DataFrame({
            'text': ['Concluído'],
            'y_offset': [15]
        })
    ).mark_text(
        align='center',
        baseline='middle',
        fontSize=12,
        fontWeight='normal',
        color='#666666',
        dy=15
    ).encode(
        text=alt.Text('text:N')
    )
    
    # Adicionar indicadores de progresso externos
    progress_ring = alt.Chart(
        pd.DataFrame({'value': [data_row['Progresso_Ponderado']]})
    ).mark_arc(
        outerRadius=100,
        innerRadius=98,
        stroke='#667eea',
        strokeWidth=3,
        cornerRadius=2
    ).encode(
        theta=alt.Theta('value:Q', scale=alt.Scale(range=[0, 6.28])),
        color=alt.value('#667eea')
    )
    
    # Combinar todos os elementos
    chart = (progress_ring + donut + text_center + text_subtitle).properties(
        title=alt.TitleParams(
            text=[data_row['Disciplinas'][:25] + ('...' if len(data_row['Disciplinas']) > 25 else '')],
            fontSize=14,
            fontWeight='bold',
            anchor='start',
            color='#2c3e50',
            offset=10
        ),
        width=220,
        height=220
    ).resolve_scale(
        color='independent'
    )
    
    return chart

def create_overall_progress_chart(progresso_geral):
    """Cria um gráfico de progresso geral animado e atraente."""
    # Dados para o gráfico circular de progresso
    df_progress = pd.DataFrame({
        'Status': ['Concluído', 'Restante'],
        'Valor': [progresso_geral, 100 - progresso_geral],
        'Color': ['#667eea', '#f0f0f0']
    })
    
    # Criar seleção para hover
    hover = alt.selection_single(on='mouseover', empty='all')
    
    # Gráfico de rosca principal
    main_donut = alt.Chart(df_progress).add_selection(hover).mark_arc(
        outerRadius=120,
        innerRadius=90,
        stroke='white',
        strokeWidth=6,
        cornerRadius=10,
        padAngle=0.05
    ).encode(
        theta=alt.Theta('Valor:Q', stack=True),
        color=alt.Color(
            'Status:N',
            scale=alt.Scale(
                domain=['Concluído', 'Restante'],
                range=['#667eea', '#f0f0f0']
            ),
            legend=None
        ),
        opacity=alt.condition(
            hover,
            alt.value(1.0),
            alt.value(0.9)
        ),
        strokeWidth=alt.condition(
            hover,
            alt.value(8),
            alt.value(6)
        ),
        tooltip=[
            alt.Tooltip('Status:N', title='Status'),
            alt.Tooltip('Valor:Q', title='Percentual', format='.1f%')
        ]
    )
    
    # Texto central principal
    text_main = alt.Chart(
        pd.DataFrame({'text': [f"{progresso_geral:.1f}%"]})
    ).mark_text(
        align='center',
        baseline='middle',
        fontSize=36,
        fontWeight='bold',
        color='#2c3e50'
    ).encode(
        text=alt.Text('text:N')
    )
    
    # Subtítulo
    text_subtitle = alt.Chart(
        pd.DataFrame({'text': ['Progresso Geral']})
    ).mark_text(
        align='center',
        baseline='middle',
        fontSize=14,
        fontWeight='normal',
        color='#666666',
        dy=25
    ).encode(
        text=alt.Text('text:N')
    )
    
    # Anel externo decorativo
    outer_ring = alt.Chart(
        pd.DataFrame({'value': [100]})
    ).mark_arc(
        outerRadius=125,
        innerRadius=123,
        stroke='#e0e0e0',
        strokeWidth=2
    ).encode(
        theta=alt.Theta('value:Q', scale=alt.Scale(range=[0, 6.28])),
        color=alt.value('#e0e0e0')
    )
    
    # Combinar elementos
    chart = (outer_ring + main_donut + text_main + text_subtitle).properties(
        title=alt.TitleParams(
            text='Progresso Geral do Estudo',
            fontSize=18,
            fontWeight='bold',
            anchor='start',
            color='#2c3e50',
            offset=15
        ),
        width=280,
        height=280
    ).resolve_scale(
        color='independent'
    )
    
    return chart

def create_progress_bar_chart(df_summary):
    """Cria gráfico de barras de progresso aprimorado."""
    # Preparar dados
    df_chart = df_summary[['Disciplinas', 'Progresso_Ponderado', 'Peso']].copy()
    df_chart = df_chart.sort_values('Progresso_Ponderado', ascending=True)
    
    # Criar gráfico
    chart = alt.Chart(df_chart).mark_bar(
        height=25,
        cornerRadiusEnd=5
    ).encode(
        x=alt.X(
            'Progresso_Ponderado:Q',
            title='Progresso (%)',
            scale=alt.Scale(domain=[0, 100])
        ),
        y=alt.Y(
            'Disciplinas:N',
            title='',
            sort='-x'
        ),
        color=alt.Color(
            'Progresso_Ponderado:Q',
            scale=alt.Scale(
                range=['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#27ae60']
            ),
            legend=None
        ),
        tooltip=[
            alt.Tooltip('Disciplinas:N', title='Disciplina'),
            alt.Tooltip('Progresso_Ponderado:Q', title='Progresso (%)', format='.1f'),
            alt.Tooltip('Peso:Q', title='Peso')
        ]
    ).properties(
        title=alt.TitleParams(
            text='Progresso por Disciplina',
            fontSize=16,
            fontWeight='bold',
            color='#2c3e50'
        ),
        height=300,
        width=600
    )
    
    return chart

def create_priority_scatter_chart(df_summary):
    """Cria gráfico de dispersão para análise de prioridades."""
    df_chart = df_summary.copy()
    df_chart['Prioridade'] = (100 - df_chart['Progresso_Ponderado']) * df_chart['Peso'] / 100
    
    chart = alt.Chart(df_chart).mark_circle(
        size=300,
        stroke='white',
        strokeWidth=2
    ).encode(
        x=alt.X(
            'Progresso_Ponderado:Q',
            title='Progresso (%)',
            scale=alt.Scale(domain=[0, 100])
        ),
        y=alt.Y(
            'Peso:Q',
            title='Peso da Disciplina'
        ),
        color=alt.Color(
            'Prioridade:Q',
            scale=alt.Scale(
                range=['#2ecc71', '#f39c12', '#e74c3c']
            ),
            title='Prioridade'
        ),
        tooltip=[
            alt.Tooltip('Disciplinas:N', title='Disciplina'),
            alt.Tooltip('Progresso_Ponderado:Q', title='Progresso (%)', format='.1f'),
            alt.Tooltip('Peso:Q', title='Peso'),
            alt.Tooltip('Prioridade:Q', title='Prioridade', format='.2f')
        ]
    ).properties(
        title=alt.TitleParams(
            text='Análise de Prioridades (Peso vs Progresso)',
            fontSize=16,
            fontWeight='bold',
            color='#2c3e50'
        ),
        width=500,
        height=300
    )
    
    return chart

# --- Interface Principal ---
def main():
    st.set_page_config(
        page_title="Dashboard de Progresso de Estudos",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Aplicar CSS personalizado
    apply_enhanced_theme_css()
    
    # Cabeçalho principal
    st.markdown("""
        <div class="main-header">
            <h1>📊 Dashboard de Progresso de Estudos</h1>
            <p>Acompanhe seu progresso de preparação para o concurso</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Carregar dados
    df_dados = read_sales_data()
    
    if df_dados.empty:
        st.warning("⚠️ Nenhum dado encontrado. Verifique a conexão com o Google Sheets.")
        return
    
    # Calcular métricas
    df_summary, progresso_geral = calculate_weighted_metrics(df_dados)
    stats = calculate_statistics(df_dados, df_summary)
    
    # Seção de estatísticas principais
    st.markdown('<div class="section-header">📈 Estatísticas Principais</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{progresso_geral}%</div>
                <div class="metric-label">Progresso Geral</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats['dias_restantes']}</div>
                <div class="stat-label">Dias para o Concurso</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats['total_concluidos']}/{stats['total_conteudos']}</div>
                <div class="stat-label">Conteúdos Concluídos</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats['percentual_geral']}%</div>
                <div class="stat-label">Taxa de Conclusão</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Seção de progresso geral destacado
    st.markdown('<div class="section-header">🎯 Progresso Geral</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        overall_chart = create_overall_progress_chart(progresso_geral)
        st.altair_chart(overall_chart, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Estatísticas adicionais em cards
        subcol1, subcol2 = st.columns(2)
        
        with subcol1:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{stats['total_concluidos']}</div>
                    <div class="stat-label">Conteúdos Concluídos</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{stats['total_falses']}</div>
                    <div class="stat-label">Conteúdos falses</div>
                </div>
            """, unsafe_allow_html=True)
        
        with subcol2:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{stats['percentual_geral']}%</div>
                    <div class="stat-label">Taxa de Conclusão</div>
                </div>
            """, unsafe_allow_html=True)
            
            if stats['dias_restantes'] > 0:
                st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-number">{stats['dias_restantes']}</div>
                        <div class="stat-label">Dias Restantes</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="stat-card" style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white;">
                        <div class="stat-number">HOJE!</div>
                        <div class="stat-label">Dia do Concurso</div>
                    </div>
                """, unsafe_allow_html=True)
    
    # Seção de gráficos de rosca
    st.markdown('<div class="section-header">📊 Progresso por Disciplina</div>', unsafe_allow_html=True)
    
    # Organizar gráficos de rosca em grid
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_summary.iterrows()):
        with cols[idx % 3]:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            chart = create_enhanced_donut_chart(row)
            st.altair_chart(chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção de análises
    st.markdown('<div class="section-header">📊 Análises Detalhadas</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        progress_chart = create_progress_bar_chart(df_summary)
        st.altair_chart(progress_chart, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        priority_chart = create_priority_scatter_chart(df_summary)
        st.altair_chart(priority_chart, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Seção de insights
    st.markdown('<div class="section-header">💡 Insights e Recomendações</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"""
        **🎯 Disciplina com Maior Progresso:**  
        {stats.get('disciplina_maior_progresso', 'N/A')}
        """)
    
    with col2:
        st.warning(f"""
        **⚠️ Disciplina com Menor Progresso:**  
        {stats.get('disciplina_menor_progresso', 'N/A')}
        """)
    
    with col3:
        st.error(f"""
        **🚨 Maior Prioridade:**  
        {stats.get('disciplina_maior_prioridade', 'N/A')}
        """)
    
    # Tabela detalhada
    st.markdown('<div class="section-header">📋 Detalhamento por Disciplina</div>', unsafe_allow_html=True)
    
    # Preparar dados para exibição
    df_display = df_summary[['Disciplinas', 'Progresso_Ponderado', 'Percentual_Concluido', 
                           'Conteudos_trues', 'Conteudos_falses', 'Peso']].copy()
    df_display.columns = ['Disciplina', 'Progresso Ponderado (%)', 'Progresso Real (%)', 
                         'Concluídos', 'falses', 'Peso']
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )
    
    # Rodapé
    st.markdown("""
        <div class="footer">
            <p>Dashboard atualizado automaticamente • Dados sincronizados com Google Sheets</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

