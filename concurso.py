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
CONCURSO_DATE = datetime(2025, 9, 28)
API_KEY = 'fc586eb9b69183a570e10a840b4edf09'
UFG_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/7/79/Marca_da_UFG.png"

ED_DATA = {
    'Disciplinas': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS'],
    'Total_Conteudos': [17, 14, 14, 11, 21],
    'Peso': [2, 1, 1, 1, 3],
    'Questões': [10, 5, 5, 10, 20]
}

FRASES_MOTIVACIONAIS = [
    "A aprovação é uma maratona, não um sprint. Mantenha o seu ritmo.",
    "Cada tópico estudado é um passo mais perto do seu futuro cargo.",
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
    "Sua aprovação está esperando por você no final dessa jornada.",
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
        st.error(f"❌ Erro ao autenticar no Google Sheets: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_worksheet():
    client = get_gspread_client()
    if not client: return None
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet.worksheet(WORKSHEET_NAME)
    except SpreadsheetNotFound:
        st.error("❌ Planilha não encontrada. Verifique o SPREADSHEET_ID.")
    except Exception as e:
        st.error(f"❌ Erro ao acessar a aba '{WORKSHEET_NAME}': {e}")
    return None

@st.cache_data(ttl=300, show_spinner="Carregando dados dos estudos...")
def load_data_with_row_indices():
    worksheet = get_worksheet()
    if not worksheet: return pd.DataFrame()
    try:
        data = worksheet.get_all_values()
        if len(data) < 2: return pd.DataFrame()

        df = pd.DataFrame(data[1:], columns=data[0])
        required_cols = ['Disciplinas', 'Conteúdos', 'Status']
        if not all(col in df.columns for col in required_cols):
            st.error(f"❌ Colunas obrigatórias faltando. Verifique se a planilha tem: {required_cols}")
            return pd.DataFrame()

        df = df[required_cols].copy()
        df['Disciplinas'] = df['Disciplinas'].str.strip().str.upper()
        df['Conteúdos'] = df['Conteúdos'].str.strip()
        df['Status'] = df['Status'].str.strip().str.lower().map({'true': True, 'false': False})
        df.dropna(subset=['Status'], inplace=True)

        df.reset_index(inplace=True)
        df['sheet_row'] = df['index'] + 2
        df.drop('index', axis=1, inplace=True)
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Falha ao carregar ou processar dados: {e}")
        return pd.DataFrame()

# --- Funções de Lógica e Cálculos ---
def update_status_in_sheet(sheet, row_number, new_status):
    try:
        header = sheet.row_values(1)
        if 'Status' not in header:
            st.error("❌ Coluna 'Status' não encontrada na planilha.")
            return False

        status_col_index = header.index('Status') + 1
        sheet.update_cell(row_number, status_col_index, new_status)
        return True
    except APIError as e:
        st.error(f"❌ Erro na API do Google Sheets durante a atualização: {e}")
        return False
    except Exception as e:
        st.error(f"❌ Erro inesperado ao atualizar planilha: {e}")
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
        
    return {
        'dias_restantes': dias_restantes, 
        'concluidos': int(concluidos),
        'pendentes': int(pendentes), 
        'topicos_por_dia': topicos_por_dia,
        'maior_prioridade': maior_prioridade
    }
    
# --- Funções para buscar dados de clima real ---
@st.cache_data(ttl=10)  # Armazena em cache por 10 segundos para atualização rápida
def get_weather_data(city_name):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={API_KEY}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()

        if weather_data.get("cod") == 200:
            main_data = weather_data.get("main")
            status = weather_data.get("weather")[0].get("main")
            temperature = main_data.get("temp")

            weather_emojis = {
                'Clear': '☀️', 'Clouds': '☁️', 'Rain': '🌧️',
                'Drizzle': '🌦️', 'Thunderstorm': '⛈️', 'Snow': '❄️',
                'Mist': '🌫️', 'Fog': '🌫️', 'Haze': '🌫️',
                'Smoke': '💨', 'Dust': '💨', 'Sand': '💨',
                'Ash': '🌋', 'Squall': '🌪️', 'Tornado': '🌪️',
            }
            emoji = weather_emojis.get(status, '🌍')
            
            return {
                "temperature": f"{temperature:.0f}°C",
                "emoji": emoji
            }
        
        else:
            return {
                "temperature": "N/A",
                "emoji": "🤷"
            }

    except requests.exceptions.RequestException as e:
        return {
            "temperature": "N/A",
            "emoji": "🤷"
        }

# --- Funções de Interface e Visualização ---
def titulo_com_destaque(texto, cor_lateral="#8e44ad"):
    st.markdown(f"""
    <div class="title-container animated-fade-in" style="
        border-left: 6px solid {cor_lateral};
        background: linear-gradient(to right, #fdfdfe, #f9f9f9);
    ">
        <h2 style="color: #2c3e50; font-family: 'Livvic', sans-serif; font-weight: 700;">
            {texto}
        </h2>
    </div>""", unsafe_allow_html=True)


def render_top_container(dias_restantes):
    weather_data = get_weather_data('Goiania, BR')
    
    st.markdown(f"""
    <style>
        .header-container {{
            width: 100%;
            height: 300px;
            background: linear-gradient(135deg, #e0f0ff, #f0f8ff);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            border: 1px solid #d3d3d3;
            padding: 20px 40px;
            display: grid;
            grid-template-columns: 1fr 2fr 1fr;
            grid-template-rows: 1fr 1fr;
            grid-template-areas:
                "logo info-top info-top"
                "logo center-title days-countdown";
            align-items: center;
            position: relative;
            overflow: hidden;
            margin-bottom: 2rem;
        }}
        
        .header-logo {{
            grid-area: logo;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }}
        .header-logo img {{
            height: 100px;
            max-width: 150px;
            object-fit: contain;
        }}

        .header-info-top {{
            grid-area: info-top;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            text-align: right;
            font-size: 1.1rem;
            color: #777;
            font-weight: 400;
        }}
        .header-info-top .weather-emoji {{
            margin-left: 0.5rem;
        }}

        .header-center-title {{
            grid-area: center-title;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }}
        .header-center-title h1 {{
            font-size: 3.5rem;
            font-weight: 800;
            color: #2c3e50;
            margin: 0;
            line-height: 1.1;
        }}
        .header-center-title h2 {{
            font-size: 1.8rem;
            font-weight: 600;
            color: #777;
            margin: 0;
            font-style: italic;
            margin-top: -0.5rem;
        }}

        .header-days-countdown {{
            grid-area: days-countdown;
            display: flex;
            justify-content: flex-end;
            align-items: center;
        }}
        .days-countdown {{
            font-size: 2.5rem;
            font-weight: 900;
            color: #e74c3c;
            line-height: 1;
            position: relative;
            display: inline-block;
            overflow: visible;
            animation: pulse 2s infinite ease-in-out;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1); }}
        }}
        .days-countdown .flames {{
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 120%;
            height: 40px;
            background: radial-gradient(ellipse at center, rgba(255,100,0,0.8) 0%, rgba(255,200,0,0.5) 50%, transparent 70%);
            z-index: -1;
            filter: blur(10px);
            animation: fire-flicker 2s infinite ease-in-out;
            opacity: 0.7;
        }}
        @keyframes fire-flicker {
            0%, 100% { opacity: 0.7; transform: scale(1) translateX(-50%); }
            25% { opacity: 0.9; transform: scale(1.1) translateX(-50%); }
            50% { opacity: 0.8; transform: scale(1.05) translateX(-50%); }
            75% { opacity: 0.85; transform: scale(1.08) translateX(-50%); }
        }
        .days-countdown .pennants {{
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 150px;
            height: 30px;
            display: flex;
            justify-content: space-between;
            z-index: 2;
        }}
        .days-countdown .pennant {{
            width: 20px;
            height: 30px;
            background: #e74c3c;
            clip-path: polygon(0 0, 100% 0, 50% 100%);
            animation: wave 3s infinite ease-in-out;
        }}
        .days-countdown .pennant:nth-child(1) { animation-delay: 0s; }
        .days-countdown .pennant:nth-child(2) { animation-delay: 0.2s; }
        .days-countdown .pennant:nth-child(3) { animation-delay: 0.4s; }
        .days-countdown .pennant:nth-child(4) { animation-delay: 0.6s; }
        .days-countdown .pennant:nth-child(5) { animation-delay: 0.8s; }
        @keyframes wave {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-5px) rotate(5deg); }
        }
        
        /* Estilos responsivos para telas menores */
        @media (max-width: 768px) {
            .header-container {
                height: auto;
                grid-template-columns: 1fr;
                grid-template-rows: auto auto auto auto;
                grid-template-areas:
                    "logo"
                    "info-top"
                    "center-title"
                    "days-countdown";
                gap: 1rem;
                padding: 1rem;
            }
            .header-logo, .header-center-title, .header-days-countdown, .header-info-top {
                justify-content: center;
                text-align: center;
            }
            .header-info-top {
                flex-direction: column;
            }
            .header-info-top .weather-emoji {
                margin-left: 0;
            }
        }

        /* ==================================== */
        /* ======== TÍTULOS MELHORADOS ======== */
        /* ==================================== */
        .title-container {
            border-left: 6px solid #8e44ad;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin: 2rem 0 1.5rem 0;
            background: linear-gradient(to right, #ffffff, #f9f9f9);
            box-shadow: 0 6px 15px rgba(0,0,0,0.08);
        }
        
        .title-container h2 {
            font-weight: 700;
            font-size: 1.6rem;
            color: #2c3e50;
            margin: 0;
        }
        
        /* ==================================== */
        /* ======== MÉTRICAS EM DESTAQUE ======== */
        /* ==================================== */
        [data-testid="stMetricValue"] {
            font-size: 1.8rem;
            font-weight: bold;
            color: #333;
        }
        [data-testid="stMetricLabel"] {
            font-size: 1rem;
            font-weight: 500;
            color: #666;
        }
        
        /* ==================================== */
        /* ======== CHECKBOXES SEM ANIMAÇÃO ======== */
        /* ==================================== */
        .stCheckbox > label {
            transition: none !important;
        }
        .stCheckbox > label:hover {
            background-color: inherit;
        }
        
        /* Centralização de altair charts */
        .st-emotion-cache-1v0mbdj {
            display: block;
            margin: 0 auto;
        }

        /* ==================================== */
        /* ======== ESTILOS PARA BOTÕES CUSTOMIZADOS ======== */
        /* ==================================== */
        .stButton > button {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.2);
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }
        
        .stButton > button:active {
            transform: translateY(0);
        }
    </style>
    """, unsafe_allow_html=True)
    
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_top_container(dias_restantes)

    df = load_data_with_row_indices()

    if df.empty:
        st.info("👋 Bem-vindo! Parece que sua planilha de estudos está vazia. Adicione os conteúdos na sua Google Sheet para começar a monitorar seu progresso aqui.")
        st.stop()
        
    # --- Somente aqui os cálculos são feitos ---
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df_summary)
    
    # Exibe os componentes com os dados calculados
    display_progress_bar(progresso_geral)
    display_simple_metrics(stats)

    titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#9b59b6")
    # A função agora recebe df_summary para usar os cálculos prontos
    display_conteudos_com_checkboxes(df, df_summary)
    
    titulo_com_destaque("📊 Progresso Detalhado por Disciplina", cor_lateral="#3498db")
    st.altair_chart(create_altair_stacked_bar(df_summary), use_container_width=True)
    
    titulo_com_destaque("📈 Visão Geral do Progresso", cor_lateral="#2ecc71")
    display_donuts_grid(df_summary, progresso_geral)
    
    titulo_com_destaque("📝 Análise Estratégica da Prova", cor_lateral="#e67e22")
    colA, colB = st.columns([2, 3])
    with colA:
        st.altair_chart(bar_questoes_padronizado(ED_DATA), use_container_width=True)
    with colB:
        st.altair_chart(bar_relevancia_customizado(ED_DATA), use_container_width=True)
    
    rodape_motivacional()

if __name__ == "__main__":
    main()
