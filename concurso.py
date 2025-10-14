# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import streamlit as st
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import warnings
import altair as alt
import random
import requests
import time

# Ignora avisos futuros do pandas
warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

# Configura a localidade para português do Brasil
try:
    import locale
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass

# --- Constantes de Configuração ---
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
CONCURSO_DATE = datetime(2025, 10, 26)
API_KEY = 'fc586eb9b69183a570e10a840b4edf09'
GOIAS_FOMENTO_LOGO_URL = "https://www.goiasfomento.com/wp-content/uploads/2021/03/GoiasFomento-Logo.png"

# Dados do Edital - Escriturário Goiás Fomento
ED_DATA = {
    'Disciplinas': [
        'LÍNGUA PORTUGUESA',
        'MATEMÁTICA',
        'ATUALIDADES E HISTÓRIA, GEOGRAFIA E CONHECIMENTOS GERAIS DO ESTADO DE GOIÁS',
        'NOÇÕES DE INFORMÁTICA',
        'CONHECIMENTOS ESPECÍFICOS'
    ],
    'Total_Conteudos': [15, 12, 8, 10, 18],
    'Peso': [3, 2, 2, 2, 3],
    'Questões': [10, 10, 5, 5, 10]
}

FRASES_MOTIVACIONAIS = [
    "A aprovação é uma maratona, não um sprint. Mantenha o seu ritmo.",
    "Cada tópico estudado é um passo mais perto da sua carreira no Goiás Fomento.",
    "A persistência de hoje é a sua recompensa de amanhã.",
    "Foque no processo, não apenas no resultado. O sucesso virá.",
    "Seu maior concorrente é a sua distração. Vença-a todos os dias.",
    "A disciplina é a ponte entre seus objetivos e a sua realização.",
    "Acredite no seu potencial. Você é mais forte do que pensa.",
    "Pequenos progressos diários somam-se a grandes resultados.",
    "O sacrifício de hoje é a celebração de amanhã. Continue firme.",
    "Não desista. O caminho pode ser difícil, mas a vitória vale a pena.",
    "Sua dedicação é o que vai te diferenciar dos demais. Estude com paixão.",
    "Concentre-se em dominar um tópico de cada vez. O aprendizado é cumulativo.",
    "A melhor maneira de prever o futuro é criá-lo com seus estudos.",
    "O único lugar onde o sucesso vem antes do trabalho é no dicionário.",
    "Quando a vontade de desistir for grande, lembre-se do porquê começou.",
    "Sua aprovação no Goiás Fomento está esperando por você no final dessa jornada.",
    "A preparação é a chave para a confiança. Estude, revise, vença.",
    "Transforme o 'e se' em 'e daí, eu consegui!'.",
    "Não estude até dar certo. Estude até não ter mais como dar errado."
]

# --- Funções de Conexão com Google Sheets ---
@st.cache_resource(show_spinner="Conectando ao Google Sheets...")
def get_gspread_client():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/spreadsheets.readonly']
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro ao autenticar no Google Sheets: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_worksheet():
    client = get_gspread_client()
    if not client: return None
    
    max_retries = 5
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            return spreadsheet.worksheet(WORKSHEET_NAME)
        except SpreadsheetNotFound:
            st.error("Planilha não encontrada. Verifique o SPREADSHEET_ID.")
            return None
        except APIError as e:
            if e.response.status_code == 503 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                st.warning(f"⏳ Aguardando {delay}s antes de tentar novamente... (Tentativa {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            else:
                st.error(f"Erro ao acessar a aba '{WORKSHEET_NAME}': {e}")
                return None
        except Exception as e:
            st.error(f"Erro inesperado: {e}")
            return None
    
    return None

@st.cache_data(ttl=600, show_spinner="Carregando dados dos estudos...")
def load_data_with_row_indices():
    worksheet = get_worksheet()
    if not worksheet: return pd.DataFrame()
    try:
        data = worksheet.get_all_values()
        if len(data) < 2: return pd.DataFrame()

        df = pd.DataFrame(data[1:], columns=data[0])
        required_cols = ['Disciplinas', 'Conteúdos', 'Status']
        if not all(col in df.columns for col in required_cols):
            st.error(f"Colunas obrigatórias faltando. Verifique se a planilha tem: {required_cols}")
            return pd.DataFrame()

        df = df[required_cols].copy()
        df.dropna(subset=['Disciplinas', 'Conteúdos'], how='all', inplace=True)
        df['Disciplinas'] = df['Disciplinas'].str.strip().str.upper()
        df['Conteúdos'] = df['Conteúdos'].str.strip()
        df['Status'] = df['Status'].str.strip().str.lower() == 'true'
        df.reset_index(inplace=True)
        df['sheet_row'] = df['index'] + 2
        df.drop('index', axis=1, inplace=True)
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"Falha ao carregar ou processar dados: {e}")
        return pd.DataFrame()

# --- Funções de Lógica e Cálculos ---
def update_status_in_sheet(sheet, row_number, new_status):
    try:
        header = sheet.row_values(1)
        if 'Status' not in header:
            st.error("Coluna 'Status' não encontrada na planilha.")
            return False
        status_col_index = header.index('Status') + 1
        sheet.update_cell(row_number, status_col_index, new_status)
        return True
    except APIError as e:
        st.error(f"Erro na API do Google Sheets durante a atualização: {e}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado ao atualizar planilha: {e}")
        return False

def calculate_progress(df):
    df_edital = pd.DataFrame(ED_DATA)
    if df.empty:
        df_edital['Conteudos_Concluidos'] = 0
        df_edital['Conteudos_Pendentes'] = df_edital['Total_Conteudos']
        return df_edital, 0.0
    resumo = df.groupby('Disciplinas', observed=True)['Status'].sum().reset_index(name='Conteudos_Concluidos')
    df_merged = pd.merge(df_edital, resumo, how='left', on='Disciplinas').fillna(0)
    df_merged['Conteudos_Concluidos'] = df_merged['Conteudos_Concluidos'].astype(int)
    df_merged['Conteudos_Pendentes'] = df_merged['Total_Conteudos'] - df_merged['Conteudos_Concluidos']
    df_merged['Pontos_Concluidos'] = (df_merged['Peso'] / df_merged['Total_Conteudos'].replace(0, 1)) * df_merged['Conteudos_Concluidos']
    total_peso = df_merged['Peso'].sum()
    total_pontos = df_merged['Pontos_Concluidos'].sum()
    progresso_total = (total_pontos / total_peso * 100) if total_peso > 0 else 0
    return df_merged, round(progresso_total, 1)

def calculate_stats(df_summary):
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    concluidos = df_summary['Conteudos_Concluidos'].sum()
    pendentes = df_summary['Conteudos_Pendentes'].sum()
    topicos_por_dia = round(pendentes / dias_restantes, 1) if dias_restantes > 0 else 0
    maior_prioridade = "N/A"
    if pendentes > 0:
        df_summary['Progresso_Percentual'] = (df_summary['Conteudos_Concluidos'] / df_summary['Total_Conteudos'].replace(0, 1)) * 100
        df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Percentual']) * df_summary['Peso']
        maior_prioridade = df_summary.loc[df_summary['Prioridade_Score'].idxmax()]['Disciplinas']
    return {'dias_restantes': dias_restantes, 'concluidos': int(concluidos), 'pendentes': int(pendentes), 'topicos_por_dia': topicos_por_dia, 'maior_prioridade': maior_prioridade}

# --- Funções para buscar dados de clima real ---
@st.cache_data(ttl=3600)
def get_weather_data(city_name):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()
        if weather_data.get("cod") == 200:
            status = weather_data.get("weather")[0].get("main")
            temperature = weather_data.get("main").get("temp")
            weather_emojis = {'Clear': '☀️', 'Clouds': '☁️', 'Rain': '🌧️', 'Drizzle': '🌦️', 'Thunderstorm': '⛈️', 'Snow': '❄️', 'Mist': '🌫️', 'Fog': '🌫️', 'Haze': '🌫️', 'Smoke': '💨', 'Dust': '💨', 'Sand': '💨', 'Ash': '🌋', 'Squall': '🌪️', 'Tornado': '🌪️'}
            return {"temperature": f"{temperature:.0f}°C", "emoji": weather_emojis.get(status, '🌍')}
        else:
            return {"temperature": "N/A", "emoji": "🤷"}
    except requests.exceptions.RequestException:
        return {"temperature": "N/A", "emoji": "🤷"}

# --- Funções de Interface e Visualização ---
def titulo_com_destaque(texto):
    st.markdown(f"""<h2 style="color: #2c3e50; font-weight: 700; margin: 2rem 0 1.5rem 0;">{texto}</h2>""", unsafe_allow_html=True)

def render_top_container():
    weather_data = get_weather_data('Goiania, BR')
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.image(GOIAS_FOMENTO_LOGO_URL, width=150)
    with col2:
        st.markdown("<h1 style='text-align: center; color: #2c3e50;'>Dashboard de Estudos</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #34495e;'>Concurso Escriturário - Goiás Fomento 2025</h2>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='text-align: right; font-size: 0.9em; color: #7f8c8d;'>{datetime.now().strftime('Goiânia, Brasil | %d de %B de %Y')} <br> {weather_data['emoji']} {weather_data['temperature']}</div>", unsafe_allow_html=True)


# --- Layout principal do Streamlit ---
st.set_page_config(layout="wide", page_title="Dashboard de Estudos Goiás Fomento")

render_top_container()

# Carregar dados
df_estudos = load_data_with_row_indices()
worksheet = get_worksheet()

# Calcular progresso e estatísticas
df_summary, progresso_total = calculate_progress(df_estudos)
stats = calculate_stats(df_summary)

# --- Tabs para organizar o conteúdo ---
tab1, tab2, tab3 = st.tabs(["Visão Geral", "Progresso Detalhado", "Gerenciar Estudos"])

with tab1:
    st.header("Visão Geral do Progresso")
    
    # Indicador de progresso geral
    st.subheader(f"🚀 Progresso Geral: {progresso_total:.1f}%")
    st.progress(int(progresso_total))
    
    # Estatísticas principais em colunas
    col_dias, col_concluidos, col_pendentes, col_prioridade = st.columns(4)
    with col_dias:
        st.metric(label="🗓️ Dias Restantes", value=stats["dias_restantes"])
    with col_concluidos:
        st.metric(label="✅ Conteúdos Concluídos", value=stats["concluidos"])
    with col_pendentes:
        st.metric(label="⏳ Conteúdos Pendentes", value=stats["pendentes"])
    with col_prioridade:
        st.markdown(f"<div style=\"background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;\">🎯 Maior Prioridade: {stats[\"maior_prioridade\"]}</div>", unsafe_allow_html=True)
        
    st.markdown("--- ")
    
    # Frase motivacional
    st.subheader("Inspiração para o dia:")
    st.info(f"💡 {random.choice(FRASES_MOTIVACIONAIS)}")

with tab2:
    st.header("📊 Progresso Detalhado por Disciplina")
    
    # Tabela de progresso por disciplina
    st.dataframe(df_summary.style.format({
        'Progresso_Percentual': "{:.1f}%",
        'Pontos_Concluidos': "{:.1f}"
    }), use_container_width=True)
    
    # Gráfico de progresso por disciplina
    chart = alt.Chart(df_summary).mark_bar().encode(
        x=alt.X('Progresso_Percentual', title='Progresso (%)'),
        y=alt.Y('Disciplinas', sort='-x', title='Disciplina'),
        tooltip=['Disciplinas', 'Total_Conteudos', 'Conteudos_Concluidos', 'Conteudos_Pendentes', 'Progresso_Percentual']
    ).properties(
        title='Progresso por Disciplina'
    )
    st.altair_chart(chart, use_container_width=True)

with tab3:
    st.header("✍️ Gerenciar Conteúdos de Estudo")
    
    if not df_estudos.empty:
        st.write("Marque os conteúdos que você já concluiu:")
        
        # Filtro por disciplina
        disciplinas_unicas = df_estudos['Disciplinas'].unique()
        selected_disciplina = st.selectbox("Filtrar por Disciplina", ['Todas'] + list(disciplinas_unicas))
        
        df_filtered = df_estudos.copy()
        if selected_disciplina != 'Todas':
            df_filtered = df_filtered[df_filtered['Disciplinas'] == selected_disciplina]
            
        for index, row in df_filtered.iterrows():
            unique_key = f"checkbox_{row['sheet_row']}"
            new_status = st.checkbox(
                f"**{row['Disciplinas']}**: {row['Conteúdos']}", 
                value=row['Status'], 
                key=unique_key
            )
            
            if new_status != row['Status']:
                if worksheet:
                    if update_status_in_sheet(worksheet, row['sheet_row'], str(new_status).upper()):
                        st.success(f"Status de '{row['Conteúdos']}' atualizado para {'Concluído' if new_status else 'Pendente'}! ✅")
                        st.rerun()
                    else:
                        st.error("Falha ao atualizar o status no Google Sheets.")
                else:
                    st.warning("Não foi possível conectar à planilha para atualizar o status.")
    else:
        st.info("Nenhum dado de estudo encontrado. Por favor, verifique sua planilha.")

# --- Estilos CSS personalizados (mantidos do original, sem alteração de fonte) ---
st.markdown("""
<style>
    @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
    .header-wrapper {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #eee;
        margin-bottom: 20px;
    }
    .header-left img {
        max-height: 80px;
    }
    .header-center h1 {
        font-size: 2.5em;
        color: #2c3e50;
        margin: 0;
    }
    .header-center h2 {
        font-size: 1.2em;
        color: #34495e;
        margin: 0;
    }
    .header-right {
        text-align: right;
    }
    .header-info-top {
        font-size: 0.9em;
        color: #7f8c8d;
    }
    .stProgress > div > div > div > div {
        background-color: #28a745; /* Cor verde para o progresso */
    }
    .stMetric > div[data-testid="stMetricValue"] {
        font-size: 1.8em;
        color: #0066cc; /* Cor para os valores das métricas */
    }
    .stMetric > div[data-testid="stMetricLabel"] {
        font-size: 1em;
        color: #555; /* Cor para os rótulos das métricas */
    }
    /* Estilos para os tabs */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)



