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
            st.error("❌ Credenciais do Google Cloud ('gcp_service_account' ) não encontradas. Configure o arquivo .streamlit/secrets.toml")
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
        st.error("A conexão com a planilha falhou. Não é possível carregar dados.")
        return pd.DataFrame()

    try:
        with st.spinner("📊 Carregando dados da planilha..."):
            data = worksheet.get_all_values()
            
        if not data or len(data) < 2:
            st.warning("⚠️ Planilha vazia ou sem dados suficientes. Adicione registros para ver o dashboard.")
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
    
    if df_dados.empty:
        # Se não houver dados, retorna o df do edital com valores zerados para progresso
        df_edital['Conteudos_trues'] = 0
        df_edital['Conteudos_falses'] = df_edital['Total_Conteudos'] # Pendente é o total
        df_edital['Progresso_Ponderado'] = 0.0
        df_edital['Percentual_Concluido'] = 0.0
        df_edital['Total_Conteudos_Real'] = 0
        df_edital['Pontos_Concluidos'] = 0
        df_edital['Pontos_Totais'] = df_edital['Peso']
        return df_edital, 0.0

    df_dados = df_dados.copy()
    df_dados['Status'] = df_dados['Status'].astype(str).str.strip()
    df_dados['true'] = (df_dados['Status'].str.lower() == 'true').astype(int)
    
    df_progresso_summary = df_dados.groupby('Disciplinas', observed=False).agg(
        Conteudos_trues=('true', 'sum')
    ).reset_index()
    
    # Usar 'how=left' para garantir que todas as disciplinas do edital apareçam
    df_final = pd.merge(df_edital, df_progresso_summary, on='Disciplinas', how='left').fillna(0)
    
    # Conteúdos pendentes é o total do edital menos os concluídos
    df_final['Conteudos_falses'] = df_final['Total_Conteudos'] - df_final['Conteudos_trues']
    
    df_final['Total_Conteudos_Real'] = df_final['Conteudos_trues'] + df_final['Conteudos_falses']
    df_final['Pontos_por_Conteudo'] = np.where(
        df_final['Total_Conteudos'] > 0,
        df_final['Peso'] / df_final['Total_Conteudos'],
        0
    )
    df_final['Pontos_Concluidos'] = df_final['Conteudos_trues'] * df_final['Pontos_por_Conteudo']
    df_final['Pontos_Totais'] = df_final['Total_Conteudos'] * df_final['Pontos_por_Conteudo']
    
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
    stats['total_conteudos'] = int(df_summary['Total_Conteudos'].sum())
    stats['total_concluidos'] = int(df_summary['Conteudos_trues'].sum())
    stats['total_falses'] = int(df_summary['Conteudos_falses'].sum())
    
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
def apply_celestial_theme():
    """Aplica CSS com tema celestial de fundo branco e melhorias de UX/UI."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap' );
        
        /* Animação de fundo celestial */
        @keyframes move-twink-back {
            from {background-position:0 0;}
            to {background-position:-10000px 5000px;}
        }
        @keyframes move-clouds-back {
            from {background-position:0 0;}
            to {background-position:10000px 0;}
        }

        /* Reset e configurações globais */
        .stApp {
            background: #fff;
            color: #2c3e50; /* Cor de texto escura para contraste */
        }
        
        .stApp::before {
            content: '';
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: -2;
            background: #fff url(https://www.script-tutorials.com/demos/360/images/stars.png ) repeat top center;
            animation: move-twink-back 200s linear infinite;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #2c3e50;
        }
        
        /* Header principal */
        .main-header {
            text-align: center;
            padding: 3rem 2rem;
            background-color: #ffffff;
            border: 2px solid #e0e0e0;
            border-radius: 20px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        }
        
        .main-header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #6a11cb, #2575fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .main-header p {
            font-size: 1.3rem;
            color: #576574;
        }
        
        /* Containers de estatísticas */
        .stats-container {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.05);
            margin-bottom: 2rem;
        }
        
        /* Métricas */
        .metric-container {
            background-color: #f8f9fa;
            color: #2c3e50;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            margin: 1rem 0;
            border: 1px solid #dee2e6;
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.03);
            transition: all 0.3s ease;
        }
        
        .metric-container:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 25px rgba(0, 0, 0, 0.07);
        }
        
        .metric-value {
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: #2575fc;
        }
        
        .metric-label {
            font-size: 1.2rem;
            color: #576574;
            font-weight: 600;
        }
        
        /* Headers de seção */
        .section-header {
            font-size: 1.8rem;
            font-weight: 600;
            color: #6a11cb;
            margin: 2rem 0 1rem 0;
            border-bottom: 3px solid #6a11cb;
            padding-bottom: 0.5rem;
            display: inline-block;
        }
        
        /* Containers de gráficos */
        .chart-container {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 15px;
            padding: 1rem;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
            transition: all 0.3s ease;
            height: 350px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .chart-container:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
        }
        
        /* Container de disciplina */
        .disciplina-container {
            background-color: #ffffff;
            border: 2px solid #6a11cb;
            border-radius: 20px;
            padding: 2rem;
            margin: 2rem 0;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.06);
        }
        
        .disciplina-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #6a11cb;
            margin-bottom: 1rem;
            text-align: center;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }
        
        /* Alertas e notificações */
        .stAlert > div {
            background-color: #f1f2f6;
            border: 1px solid #ced6e0;
            border-radius: 10px;
            color: #2c3e50;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem 0;
            color: #576574;
            border-top: 1px solid #e0e0e0;
            margin-top: 3rem;
        }
        
        /* Botões */
        .stButton > button {
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
            color: #ffffff;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(106, 17, 203, 0.2);
        }
        </style>
    """, unsafe_allow_html=True)

def create_altair_radial_chart(data_row):
    """Cria um gráfico de rosca com Altair para representar o progresso."""
    concluido = int(data_row['Conteudos_trues'])
    pendente = int(data_row['Conteudos_falses'])

    # Evita divisão por zero se não houver conteúdos
    if concluido == 0 and pendente == 0:
        pendente = 1 # Adiciona um valor para exibir um gráfico completo de "Pendente"

    # Prepara o DataFrame para o Altair
    source = pd.DataFrame({
        "status": ["Concluído", "Pendente"],
        "values": [concluido, pendente]
    })

    # Define o esquema de cores
    color_scheme = alt.Scale(
        domain=["Concluído", "Pendente"],
        range=["#2ecc71", "#e74c3c"] # Verde para concluído, Vermelho para pendente
    )

    # Cria o gráfico base conforme solicitado
    base = alt.Chart(source).encode(
        alt.Theta("values:Q").stack(True),
        alt.Radius("values").scale(type="sqrt", zero=True, rangeMin=20),
        color=alt.Color("status:N", scale=color_scheme, legend=None), # Legenda removida do gráfico
        tooltip=['status', 'values']
    )

    # Camada do arco (donut chart)
    c1 = base.mark_arc(innerRadius=50, stroke="#fff", strokeWidth=2)

    # Camada de texto com os valores (só mostra se o valor for maior que 0)
    text_data = source[source['values'] > 0]
    c2 = alt.Chart(text_data).mark_text(radiusOffset=25, fill="#fff", fontSize=14, fontWeight='bold').encode(
        alt.Theta("values:Q").stack(True),
        alt.Radius("values").scale(type="sqrt", zero=True, rangeMin=20),
        text="values:Q"
    )
    
    # Combina as camadas
    chart = (c1 + c2).properties(
        title=alt.TitleParams(
            text=f"{data_row['Disciplinas']}",
            subtitle=f"{data_row['Progresso_Ponderado']:.1f}% Ponderado",
            anchor='middle',
            color='#2c3e50',
            subtitleColor='#576574'
        )
    ).configure_view(
        strokeWidth=0 # Remove a borda ao redor do gráfico
    )
    
    return chart

def create_performance_radar_chart(df_summary):
    """Cria um gráfico radar mostrando o desempenho por disciplina."""
    if df_summary.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=df_summary['Progresso_Ponderado'].tolist(),
        theta=df_summary['Disciplinas'].tolist(),
        fill='toself',
        name='Progresso Ponderado',
        line=dict(color='#2575fc', width=3),
        fillcolor='rgba(37, 117, 252, 0.2)',
        hovertemplate="<b>%{theta}</b>  
Progresso: %{r:.1f}%<extra></extra>"
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=df_summary['Percentual_Concluido'].tolist(),
        theta=df_summary['Disciplinas'].tolist(),
        fill='toself',
        name='Percentual Simples',
        line=dict(color='#6a11cb', width=2),
        fillcolor='rgba(106, 17, 203, 0.1)',
        hovertemplate="<b>%{theta}</b>  
Percentual: %{r:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color='#576574'),
                gridcolor='rgba(0,0,0,0.1)'
            ),
            angularaxis=dict(
                tickfont=dict(color='#2c3e50'),
                gridcolor='rgba(0,0,0,0.1)'
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#2c3e50'),
        title=dict(
            text="<b>Radar de Desempenho por Disciplina</b>",
            x=0.5,
            font=dict(size=18, color='#6a11cb')
        ),
        legend=dict(
            font=dict(color='#2c3e50'),
            bgcolor='#ffffff',
            bordercolor='#e0e0e0',
            borderwidth=1
        ),
        height=500
    )
    
    return fig

def create_progress_timeline_chart(df_summary):
    """Cria um gráfico de linha temporal do progresso."""
    if df_summary.empty or df_summary['Progresso_Ponderado'].sum() == 0:
        return go.Figure().update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            title=dict(text="<b>Evolução do Progresso (Aguardando Dados)</b>", x=0.5, font=dict(size=18, color='#6a11cb')),
            xaxis=dict(showgrid=False, visible=False),
            yaxis=dict(showgrid=False, visible=False)
        )
    
    fig = go.Figure()
    
    # Simular dados de progresso ao longo do tempo (para demonstração)
    dates = pd.date_range(start='2024-01-01', end=datetime.now(), freq='W')
    
    for idx, row in df_summary.iterrows():
        if row['Progresso_Ponderado'] > 0:
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
                hovertemplate="<b>%{fullData.name}</b>  
Data: %{x}  
Progresso: %{y:.1f}%<extra></extra>"
            ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#2c3e50'),
        title=dict(
            text="<b>Evolução do Progresso ao Longo do Tempo</b>",
            x=0.5,
            font=dict(size=18, color='#6a11cb')
        ),
        xaxis=dict(
            gridcolor='rgba(0,0,0,0.1)',
            tickfont=dict(color='#576574'),
            title=dict(text='Data', font=dict(color='#2c3e50'))
        ),
        yaxis=dict(
            gridcolor='rgba(0,0,0,0.1)',
            tickfont=dict(color='#576574'),
            title=dict(text='Progresso (%)', font=dict(color='#2c3e50'))
        ),
        legend=dict(
            font=dict(color='#2c3e50'),
            bgcolor='#ffffff',
            bordercolor='#e0e0e0',
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
    sizes = (df_summary['Prioridade'] / max_prioridade * 50) + 10 if max_prioridade > 0 else 10
    
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
                tickfont=dict(color='#2c3e50')
            ),
            line=dict(color='#2c3e50', width=2)
        ),
        text=[disc[:10] + '...' if len(disc) > 10 else disc for disc in df_summary['Disciplinas']],
        textposition='middle center',
        textfont=dict(color='#2c3e50', size=10),
        hovertemplate="<b>%{text}</b>  
Peso: %{x}  
Progresso: %{y:.1f}%  
Prioridade: %{customdata:.1f}<extra></extra>",
        customdata=df_summary['Prioridade']
    ))
    
    fig.update_layout
    
