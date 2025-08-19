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
from typing import Dict, Tuple, Optional, List
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ignora avisos futuros do pandas
warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

# Configura a localidade para português do Brasil
try:
    import locale
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    logger.warning("Não foi possível configurar localidade pt_BR.UTF-8")

# --- Constantes de Configuração ---
class Config:
    SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
    WORKSHEET_NAME = 'Registro'
    CONCURSO_DATE = datetime(2025, 9, 28)
    WEATHER_API_KEY = 'fc586eb9b69183a570e10a840b4edf09'
    
    ED_DATA = {
        'Disciplinas': ['PORTUGUES', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'ESPECÍFICOS'],
        'Total_Conteudos': [17, 14, 14, 11, 21],
        'Peso': [2, 1, 1, 1, 3],
        'Questões': [10, 5, 5, 10, 20]
    }
    
    PALETA_CORES = ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#f1c40f']
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/spreadsheets.readonly'
    ]

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
    "Visualize seu nome na lista de aprovados. É a sua motivação final.",
    "A preparação é a chave para a confiança. Estude, revise, vença.",
    "Transforme o 'e se' em 'e daí, eu consegui!'.",
    "Não estude até dar certo. Estude até não ter mais como dar errado."
]

# --- Classes para melhor organização ---
class GoogleSheetsManager:
    """Gerencia conexões e operações com Google Sheets"""
    
    def __init__(self):
        self.client = None
        self.worksheet = None
    
    @st.cache_resource(show_spinner="Conectando ao Google Sheets...")
    def get_client(_self):
        try:
            credentials_dict = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(
                credentials_dict, 
                scopes=Config.SCOPES
            )
            _self.client = gspread.authorize(creds)
            return _self.client
        except Exception as e:
            st.error(f"❌ Erro ao autenticar no Google Sheets: {e}")
            logger.error(f"Erro de autenticação: {e}")
            return None
    
    @st.cache_resource(show_spinner=False)
    def get_worksheet(_self):
        client = _self.get_client()
        if not client:
            return None
        
        try:
            spreadsheet = client.open_by_key(Config.SPREADSHEET_ID)
            _self.worksheet = spreadsheet.worksheet(Config.WORKSHEET_NAME)
            return _self.worksheet
        except SpreadsheetNotFound:
            st.error("❌ Planilha não encontrada. Verifique o SPREADSHEET_ID.")
            logger.error("Planilha não encontrada")
        except Exception as e:
            st.error(f"❌ Erro ao acessar a aba '{Config.WORKSHEET_NAME}': {e}")
            logger.error(f"Erro ao acessar worksheet: {e}")
        return None
    
    def update_status(self, row_number: int, new_status: str) -> bool:
        """Atualiza o status de um item na planilha"""
        try:
            worksheet = self.get_worksheet()
            if not worksheet:
                return False
            
            header = worksheet.row_values(1)
            if 'Status' not in header:
                st.error("❌ Coluna 'Status' não encontrada na planilha.")
                return False

            status_col_index = header.index('Status') + 1
            worksheet.update_cell(row_number, status_col_index, new_status)
            return True
        except APIError as e:
            st.error(f"❌ Erro na API do Google Sheets: {e}")
            logger.error(f"Erro de API: {e}")
            return False
        except Exception as e:
            st.error(f"❌ Erro inesperado ao atualizar planilha: {e}")
            logger.error(f"Erro inesperado: {e}")
            return False

class DataProcessor:
    """Processa e valida dados da planilha"""
    
    @staticmethod
    @st.cache_data(ttl=300, show_spinner="Carregando dados dos estudos...")
    def load_data_with_row_indices() -> pd.DataFrame:
        sheets_manager = GoogleSheetsManager()
        worksheet = sheets_manager.get_worksheet()
        if not worksheet:
            return pd.DataFrame()
        
        try:
            data = worksheet.get_all_values()
            if len(data) < 2:
                logger.warning("Planilha vazia ou sem dados suficientes")
                return pd.DataFrame()

            df = pd.DataFrame(data[1:], columns=data[0])
            required_cols = ['Disciplinas', 'Conteúdos', 'Status']
            
            if not all(col in df.columns for col in required_cols):
                st.error(f"❌ Colunas obrigatórias faltando: {required_cols}")
                logger.error(f"Colunas faltando: {required_cols}")
                return pd.DataFrame()

            # Limpeza e processamento dos dados
            df = df[required_cols].copy()
            df['Disciplinas'] = df['Disciplinas'].str.strip().str.upper()
            df['Conteúdos'] = df['Conteúdos'].str.strip()
            
            # Mapeia status de string para boolean de forma mais robusta
            status_mapping = {
                'true': True, 'false': False, '1': True, '0': False,
                'sim': True, 'não': False, 'yes': True, 'no': False
            }
            df['Status'] = df['Status'].str.strip().str.lower().map(status_mapping)
            
            # Remove linhas com status inválido
            df = df.dropna(subset=['Status']).reset_index(drop=True)
            
            # Adiciona índice da linha na planilha
            df['sheet_row'] = df.index + 2  # +2 porque o índice começa em 0 e há cabeçalho
            
            return df
            
        except Exception as e:
            st.error(f"❌ Falha ao carregar dados: {e}")
            logger.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def calculate_progress(df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
        """Calcula o progresso geral e por disciplina"""
        df_edital = pd.DataFrame(Config.ED_DATA)
        
        if df.empty:
            df_edital['Conteudos_Concluidos'] = 0
            df_edital['Conteudos_Pendentes'] = df_edital['Total_Conteudos']
            return df_edital, 0.0

        # Agrupa e conta conteúdos concluídos por disciplina
        resumo = df.groupby('Disciplinas', observed=True)['Status'].sum().reset_index(name='Conteudos_Concluidos')
        df_merged = pd.merge(df_edital, resumo, how='left', on='Disciplinas').fillna(0)
        df_merged['Conteudos_Concluidos'] = df_merged['Conteudos_Concluidos'].astype(int)
        df_merged['Conteudos_Pendentes'] = df_merged['Total_Conteudos'] - df_merged['Conteudos_Concluidos']
        
        # Calcula pontos baseados no peso
        df_merged['Pontos_Concluidos'] = (
            df_merged['Peso'] / df_merged['Total_Conteudos'].replace(0, 1)
        ) * df_merged['Conteudos_Concluidos']
        
        # Progresso total ponderado
        total_peso = df_merged['Peso'].sum()
        total_pontos = df_merged['Pontos_Concluidos'].sum()
        progresso_total = (total_pontos / total_peso * 100) if total_peso > 0 else 0
        
        return df_merged, round(progresso_total, 1)
    
    @staticmethod
    def calculate_stats(df_summary: pd.DataFrame) -> Dict:
        """Calcula estatísticas de estudo"""
        dias_restantes = max((Config.CONCURSO_DATE - datetime.now()).days, 0)
        concluidos = df_summary['Conteudos_Concluidos'].sum()
        pendentes = df_summary['Conteudos_Pendentes'].sum()
        topicos_por_dia = round(pendentes / dias_restantes, 1) if dias_restantes > 0 else 0
        
        maior_prioridade = "N/A"
        if pendentes > 0 and not df_summary.empty:
            df_summary = df_summary.copy()
            df_summary['Progresso_Percentual'] = (
                df_summary['Conteudos_Concluidos'] / 
                df_summary['Total_Conteudos'].replace(0, 1)
            ) * 100
            df_summary['Prioridade_Score'] = (
                (100 - df_summary['Progresso_Percentual']) * df_summary['Peso']
            )
            if not df_summary['Prioridade_Score'].empty:
                maior_prioridade = df_summary.loc[
                    df_summary['Prioridade_Score'].idxmax()
                ]['Disciplinas']
            
        return {
            'dias_restantes': dias_restantes, 
            'concluidos': int(concluidos),
            'pendentes': int(pendentes), 
            'topicos_por_dia': topicos_por_dia,
            'maior_prioridade': maior_prioridade
        }

class WeatherService:
    """Serviço para buscar dados meteorológicos"""
    
    @staticmethod
    @st.cache_data(ttl=3600)  # Cache por 1 hora
    def get_weather_data(city_name: str) -> Dict[str, str]:
        """Busca dados do clima atual"""
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': city_name,
            'appid': Config.WEATHER_API_KEY,
            'units': 'metric'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            weather_data = response.json()

            if weather_data.get("cod") == 200:
                main_data = weather_data.get("main", {})
                weather_info = weather_data.get("weather", [{}])[0]
                status = weather_info.get("main", "Unknown")
                temperature = main_data.get("temp", 0)

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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar dados do clima: {e}")
        
        return {"temperature": "N/A", "emoji": "🤷"}

class UIComponents:
    """Componentes de interface do usuário"""
    
    @staticmethod
    def setup_page_config():
        """Configura a página do Streamlit"""
        st.set_page_config(
            page_title="📚 Dashboard de Estudos - Concurso TAE UFG",
            page_icon="📚",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        # Configura tema do Altair
        alt.themes.enable('none')
    
    @staticmethod
    def load_custom_css():
        """Carrega CSS customizado"""
        st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * {
                font-family: 'Nunito', sans-serif !important;
            }
            
            .stApp {
                background-color: #f7f9fc;
                color: #333;
            }
            
            .stApp [data-testid="stVegaLiteChart"] > div,
            .vega-embed.has-actions {
                background-color: transparent !important;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .animated-fade-in {
                animation: fadeIn 0.8s ease-out;
            }

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
            
            /* Customização dos expanders */
            .st-expander-header [data-testid="stExpander-header-action-icon"] {
                display: none;
            }

            .st-expander-header button::before {
                content: "+";
                display: inline-block;
                margin-right: 8px;
                font-size: 1.2rem;
                font-weight: bold;
                color: #9b59b6;
            }

            .st-expander-header[aria-expanded="true"] button::before {
                content: "-";
            }
            
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
            
            .stCheckbox > label {
                transition: none !important;
            }
            .stCheckbox > label:hover {
                background-color: inherit;
            }
            
            /* 🎯 CONTAINER PRINCIPAL - ALTERE AQUI A ALTURA */
            .responsive-topbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                height: 120px; /* 👈 ALTERE ESTA LINHA PARA MUDAR A ALTURA */
                padding: 1rem 2rem;
                background: linear-gradient(135deg, #e0f0ff, #f0f8ff);
                border-radius: 12px;
                margin-bottom: 1.5rem;
                border: 1px solid #d3d3d3;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }
            
            /* 🖼️ LOGO - OCUPA 20% E FICA NO CANTO ESQUERDO */
            .topbar-logo {
                width: 20%; /* 👈 LOGO OCUPA 20% DO ESPAÇO */
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: flex-start; /* 👈 ALINHA NO CANTO ESQUERDO */
            }
            
            /* 📝 TÍTULOS - CENTRALIZADOS HORIZONTAL E VERTICALMENTE */
            .topbar-titles {
                width: 50%; /* 👈 TÍTULOS OCUPAM 50% DO ESPAÇO */
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center; /* 👈 CENTRALIZA VERTICALMENTE */
                align-items: center; /* 👈 CENTRALIZA HORIZONTALMENTE */
                text-align: center;
            }
            
            /* 🌤️ INFO DIREITA - LAYOUT VERTICAL */
            .topbar-info {
                width: 30%; /* 👈 INFO OCUPA 30% DO ESPAÇO */
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: space-between; /* 👈 DISTRIBUI ELEMENTOS */
                align-items: flex-end; /* 👈 ALINHA À DIREITA */
            }
            
            /* 🏙️ INFORMAÇÕES DE CIDADE/CLIMA - CANTO SUPERIOR DIREITO */
            .weather-info {
                font-size: clamp(0.8rem, 1.3vw, 1rem);
                color: #777;
                text-align: right; /* 👈 ALINHA TEXTO À DIREITA */
                margin-top: 0; /* 👈 COLA NO TOPO */
            }
            
            /* ⏰ CONTADOR DE DIAS - CENTRO DO CANTO DIREITO */
            .days-countdown {
                color: #e74c3c;
                font-weight: 800;
                font-size: clamp(1.5rem, 3vw, 2.5rem);
                animation: pulse 2s infinite ease-in-out;
                text-align: center; /* 👈 CENTRALIZA O TEXTO */
                align-self: center; /* 👈 CENTRALIZA NO EIXO VERTICAL DA ÁREA DIREITA */
            }
            
            /* 📱 RESPONSIVIDADE PARA MOBILE */
            @media (max-width: 768px) {
                .responsive-topbar {
                    flex-direction: column;
                    height: auto; /* 👈 ALTURA AUTOMÁTICA NO MOBILE */
                    padding: 1rem;
                }
                .topbar-logo, .topbar-titles, .topbar-info {
                    width: 100%;
                    text-align: center;
                    margin-bottom: 1rem;
                }
            }
            
            /* 🎨 ESTILOS DOS TÍTULOS */
            .main-title {
                margin: 0;
                font-size: clamp(1.5rem, 2.5vw, 2rem);
                color: #2c3e50;
                line-height: 1.2;
            }
            
            .sub-title {
                margin: 0.3rem 0 0;
                font-size: clamp(1rem, 1.8vw, 1.4rem);
                color: #555;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_topbar(dias_restantes: int):
        """Renderiza a barra superior com layout customizado"""
        weather_data = WeatherService.get_weather_data('Goiânia, BR')
        
        # Teste simples primeiro
        st.write("🧪 Teste: Se você vê esta mensagem, o Streamlit está funcionando")
        
        st.markdown(f"""
        <div class="responsive-topbar">
            <div class="topbar-logo">
                <img src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" 
                     alt="Logo UFG" 
                     style="height: auto; max-width: 100%; max-height: 100%;"/>
            </div>
            
            <div class="topbar-titles">
                <h1 class="main-title">Dashboard de Estudos</h1>
                <p class="sub-title">Concurso TAE UFG 2025</p>
            </div>
            
            <div class="topbar-info">
                <div class="weather-info">
                    Goiânia, Brasil | {datetime.now().strftime('%d de %B de %Y')} | {weather_data['emoji']} {weather_data['temperature']}
                </div>
                <div class="days-countdown">
                    ⏰ Faltam {dias_restantes} dias!
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def titulo_com_destaque(texto: str, cor_lateral: str = "#8e44ad"):
        """Renderiza título com destaque lateral"""
        st.markdown(f"""
        <div class="title-container animated-fade-in" style="border-left-color: {cor_lateral};">
            <h2>{texto}</h2>
        </div>""", unsafe_allow_html=True)
    
    @staticmethod
    def display_progress_bar(progresso_geral: float):
        """Exibe barra de progresso geral"""
        st.markdown(f"""
        <div class="animated-fade-in" style="margin: 0.5rem 0 1.5rem 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
                <span style="font-weight: 500; color: #3498db; font-family: 'Nunito', sans-serif;">Progresso Geral</span>
                <span style="font-weight: 600; color: #2c3e50; font-family: 'Nunito', sans-serif;">{progresso_geral:.1f}%</span>
            </div>
            <div style="height: 12px; background: #e0e0e0; border-radius: 10px; overflow: hidden;">
                <div style="height: 100%; width: {progresso_geral}%;
                            background: linear-gradient(90deg, #3498db, #1abc9c);
                            border-radius: 10px; transition: width 0.5s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def display_metrics(stats: Dict):
        """Exibe métricas principais"""
        cols = st.columns(4)
        with cols[0]:
            st.metric("✅ Concluídos", f"{stats['concluidos']}")
        with cols[1]:
            st.metric("⏳ Pendentes", f"{stats['pendentes']}")
        with cols[2]:
            st.metric("🏃 Ritmo", f"{stats['topicos_por_dia']}/dia")
        with cols[3]:
            st.metric("⭐ Prioridade", stats['maior_prioridade'].title())
    
    @staticmethod
    def rodape_motivacional():
        """Exibe frase motivacional no rodapé"""
        frase_aleatoria = random.choice(FRASES_MOTIVACIONAIS)
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align: center; margin: 0.5rem 0; padding: 1rem; color: #555;">
            <p style='font-size: 0.9rem; margin: 0; font-family: "Nunito", sans-serif;'>
                🚀 {frase_aleatoria} ✨
            </p>
        </div>
        """, unsafe_allow_html=True)

class ChartGenerator:
    """Gerador de gráficos"""
    
    @staticmethod
    def create_stacked_bar(df_summary: pd.DataFrame):
        """Cria gráfico de barras empilhadas do progresso"""
        df_percent = df_summary.copy()
        df_percent['Concluido (%)'] = (df_percent['Conteudos_Concluidos'] / df_percent['Total_Conteudos']) * 100
        df_percent['Pendente (%)'] = (df_percent['Conteudos_Pendentes'] / df_percent['Total_Conteudos']) * 100

        df_melted = df_percent.melt(
            id_vars=['Disciplinas'],
            value_vars=['Concluido (%)', 'Pendente (%)'],
            var_name='Status',
            value_name='Percentual'
        )

        status_map = {'Concluido (%)': 'Concluido', 'Pendente (%)': 'Pendente'}
        df_melted['Status'] = df_melted['Status'].map(status_map)
        df_melted['Percentual_norm'] = df_melted['Percentual'] / 100
        df_melted['Posicao_norm'] = df_melted.groupby('Disciplinas')['Percentual_norm'].cumsum() - (df_melted['Percentual_norm'] / 2)
        df_melted['PercentText'] = df_melted['Percentual'].apply(lambda x: f"{x:.1f}%" if x > 0 else "")

        bars = alt.Chart(df_melted).mark_bar(
            stroke='#d3d3d3',
            strokeWidth=1
        ).encode(
            y=alt.Y('Disciplinas:N', sort=None, title=None, axis=alt.Axis(labelColor='#000000', labelFont='Nunito')),
            x=alt.X('Percentual_norm:Q', stack="normalize", axis=alt.Axis(title=None, labels=False)),
            color=alt.Color('Status:N',
                            scale=alt.Scale(domain=['Concluido', 'Pendente'], range=['#2ecc71', '#e74c3c']),
                            legend=None)
        )

        labels = alt.Chart(df_melted).mark_text(
            align='center',
            baseline='middle',
            fontWeight='bold',
            fontSize=12,
            font='Nunito'
        ).encode(
            y=alt.Y('Disciplinas:N', sort=None),
            x=alt.X('Posicao_norm:Q'),
            text=alt.Text('PercentText:N'),
            color=alt.value('black')
        )

        return (bars + labels).properties(
            height=350,
            title=alt.TitleParams(
                text="Percentual de Conclusão por Disciplina",
                anchor='middle',
                fontSize=18,
                font='Nunito',
                color='#000000'
            )
        ).configure_view(
            stroke=None,
            fill='transparent'
        ).configure(
            background='transparent'
        )
    
    @staticmethod
    def create_donut_chart(data: pd.DataFrame, title: str):
        """Cria gráfico de rosca"""
        total = data['Valor'].sum()
        if total == 0:
            concluido_val = 0
        else:
            concluido_val = data[data['Status'] == 'Concluido']['Valor'].iloc[0] if len(data[data['Status'] == 'Concluido']) > 0 else 0
        
        percent_text = f"{(concluido_val / total * 100) if total > 0 else 0:.1f}%"

        base = alt.Chart(data).mark_arc(
            innerRadius=55, 
            cornerRadius=5, 
            stroke='#d3d3d3', 
            strokeWidth=1
        ).encode(
            theta=alt.Theta("Valor:Q"),
            color=alt.Color("Status:N",
                            scale=alt.Scale(domain=['Concluido', 'Pendente'], range=['#2ecc71', '#e74c3c']),
                            legend=None),
            tooltip=['Status', alt.Tooltip('Valor', title="Conteúdos")]
        )
        
        text = alt.Chart(pd.DataFrame({'text': [percent_text]})).mark_text(
            size=24,
            fontWeight='bold',
            color='#000000',
            font='Nunito'
        ).encode(text='text:N')

        return (base + text).properties(
            title=alt.TitleParams(
                text=title,
                anchor='middle',
                fontSize=26,
                dy=-10,
                color='#000000',
                font='Nunito'
            )
        ).configure_view(
            stroke=None,
            fill='transparent'
        ).configure(
            background='transparent'
        )

class StudyManager:
    """Gerencia operações de estudo (checklist)"""
    
    def __init__(self):
        self.sheets_manager = GoogleSheetsManager()
    
    def on_checkbox_change(self, row_number: int, key: str, expander_key: str):
        """Callback para mudança de checkbox"""
        novo_status = st.session_state.get(key, False)
        
        if self.sheets_manager.update_status(row_number, "TRUE" if novo_status else "FALSE"):
            st.toast("Status atualizado!", icon="✅")
            # Mantém o expander aberto
            st.session_state[expander_key] = True
            # Limpa cache para recarregar dados
            DataProcessor.load_data_with_row_indices.clear()
        else:
            st.toast("Falha ao atualizar.", icon="❌")
    
    def display_checklist(self, df: pd.DataFrame):
        """Exibe checklist de conteúdos com busca"""
        if df.empty:
            st.info("📝 Nenhum conteúdo encontrado para exibir.")
            return
        
        # Campo de busca
        search_query = st.text_input(
            "🔍 Buscar conteúdos...", 
            placeholder="Ex: Informática, RLM...",
            help="Digite parte do nome da disciplina ou conteúdo para filtrar"
        ).strip().upper()
        
        # Filtra dados baseado na busca
        if search_query:
            df_filtered = df[
                df.apply(
                    lambda row: search_query in row['Disciplinas'] or 
                               search_query in row['Conteúdos'].upper(), 
                    axis=1
                )
            ]
            if df_filtered.empty:
                st.warning(f"🔍 Nenhum resultado encontrado para '{search_query}'")
                return
        else:
            df_filtered = df

        # Exibe conteúdos por disciplina
        for disc in sorted(df_filtered['Disciplinas'].unique()):
            conteudos_disciplina = df_filtered[df_filtered['Disciplinas'] == disc]
            
            concluidos = conteudos_disciplina['Status'].sum()
            total = len(conteudos_disciplina)
            progresso = (concluidos / total) * 100 if total > 0 else 0
            
            # Controle do estado do expander
            expander_key = f"expander_{disc}"
            if expander_key not in st.session_state:
                st.session_state[expander_key] = True

            with st.expander(
                f"**{disc.title()}** - {concluidos}/{total} ({progresso:.1f}%)", 
                expanded=st.session_state[expander_key]
            ):
                st.session_state[expander_key] = True
                
                for _, row in conteudos_disciplina.iterrows():
                    key = f"cb_{row['sheet_row']}"
                    
                    # Inicializa estado do checkbox se não existir
                    if key not in st.session_state:
                        st.session_state[key] = bool(row['Status'])

                    st.checkbox(
                        label=row['Conteúdos'],
                        value=st.session_state[key],
                        key=key,
                        on_change=self.on_checkbox_change,
                        args=(row['sheet_row'], key, expander_key),
                        help=f"Disciplina: {disc.title()}"
                    )

# --- Funções de gráficos específicos ---
def create_questions_bar_chart():
    """Cria gráfico de barras para distribuição de questões"""
    df = pd.DataFrame(Config.ED_DATA)

    bars = alt.Chart(df).mark_bar(
        cornerRadiusTopLeft=2,
        cornerRadiusTopRight=2,
        stroke='#d3d3d3',
        strokeWidth=1
    ).encode(
        x=alt.X('Disciplinas:N', sort=None, title=None, 
                axis=alt.Axis(labelAngle=0, labelFont='Nunito', labelColor='#000000')),
        y=alt.Y('Questões:Q', title=None, axis=alt.Axis(labels=False, ticks=True)),
        color=alt.Color('Disciplinas:N', scale=alt.Scale(range=Config.PALETA_CORES), legend=None)
    )

    labels = bars.mark_text(
        align='center',
        baseline='bottom',
        dy=-5,
        color='#000000',
        fontWeight='bold',
        font='Nunito'
    ).encode(
        text='Questões:Q'
    )

    return (bars + labels).properties(
        width=500,
        height=500,
        title=alt.TitleParams(
            text='Distribuição de Questões',
            anchor='middle',
            fontSize=18,
            font='Nunito',
            color='#000000'
        )
    ).configure_view(
        stroke=None,
        fill='transparent'
    ).configure(
        background='transparent'
    )

def create_relevance_bar_chart():
    """Cria gráfico de barras para relevância das disciplinas"""
    df = pd.DataFrame(Config.ED_DATA)
    df['Relevancia'] = df['Peso'] * df['Questões']
    df['Percentual'] = df['Relevancia'] / df['Relevancia'].sum() * 100
    df['custom_label'] = df.apply(lambda row: f"{row['Disciplinas']} ({row['Percentual']:.1f}%)", axis=1)

    color_scale = alt.Scale(
        domain=[df['Relevancia'].min(), df['Relevancia'].max()],
        range=['#cce6ff', '#004c99']
    )

    bars = alt.Chart(df).mark_bar(
        cornerRadiusTopRight=2,
        cornerRadiusBottomRight=2,
        stroke='#d3d3d3',
        strokeWidth=1,
        size=40
    ).encode(
        y=alt.Y('Disciplinas:N', sort='-x', title=None, axis=alt.Axis(labels=False)),
        x=alt.X('Relevancia:Q', title=None, axis=alt.Axis(labels=False, grid=False)),
        color=alt.Color('Relevancia:Q', scale=color_scale, legend=None),
        tooltip=[
            alt.Tooltip('Disciplinas:N'),
            alt.Tooltip('Peso:Q'),
            alt.Tooltip('Questões:Q'),
            alt.Tooltip('Relevancia:Q', title='Relevância'),
            alt.Tooltip('Percentual:Q', format='.1f', title='Percentual (%)')
        ]
    )
    
    text = bars.mark_text(
        align='left',
        baseline='middle',
        dx=3,
        color='#000000',
        fontWeight='bold',
        fontSize=12,
        font='Nunito'
    ).encode(
        y=alt.Y('Disciplinas:N', sort='-x', title=None, axis=alt.Axis(labelColor='#000000')),
        x=alt.X('Relevancia:Q'),
        text='custom_label:N'
    )

    return (bars + text).properties(
        width=500,
        height=500,
        title=alt.TitleParams(
            text='Relevância das Disciplinas',
            anchor='middle',
            fontSize=18,
            font='Nunito',
            color='#000000'
        )
    ).configure_view(
        stroke=None,
        fill='transparent'
    ).configure(
        background='transparent'
    )

def display_donut_grid(df_summary: pd.DataFrame, progresso_geral: float):
    """Exibe grade de gráficos de rosca"""
    st.markdown('<div class="animated-fade-in">', unsafe_allow_html=True)
    
    charts_data = []
    
    # Gráfico de progresso geral
    prog_geral_df = pd.DataFrame([
        {'Status': 'Concluido', 'Valor': progresso_geral},
        {'Status': 'Pendente', 'Valor': 100 - progresso_geral}
    ])
    charts_data.append({'df': prog_geral_df, 'title': 'Progresso Geral'})

    # Gráficos por disciplina
    for _, row in df_summary.iterrows():
        df = pd.DataFrame([
            {'Status': 'Concluido', 'Valor': row['Conteudos_Concluidos']},
            {'Status': 'Pendente', 'Valor': row['Conteudos_Pendentes']}
        ])
        charts_data.append({'df': df, 'title': row['Disciplinas'].title()})

    # Exibe em grade de 3 colunas
    for i in range(0, len(charts_data), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(charts_data):
                with cols[j]:
                    chart_info = charts_data[i+j]
                    donut = ChartGenerator.create_donut_chart(
                        chart_info['df'], 
                        chart_info['title']
                    )
                    st.altair_chart(donut, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- Função Principal ---
def main():
    """Função principal da aplicação"""
    try:
        # Configuração inicial
        UIComponents.setup_page_config()
        UIComponents.load_custom_css()
        
        # Cálculo de dias restantes
        dias_restantes = max((Config.CONCURSO_DATE - datetime.now()).days, 0)
        
        # Renderiza interface
        UIComponents.render_topbar(dias_restantes)

        # Carrega e processa dados
        df = DataProcessor.load_data_with_row_indices()

        if df.empty:
            st.info("""
            👋 **Bem-vindo ao Dashboard de Estudos!** 
            
            Parece que sua planilha de estudos está vazia ou não foi possível carregar os dados. 
            
            **Para começar:**
            1. Verifique se a planilha do Google Sheets está configurada corretamente
            2. Certifique-se de que as colunas 'Disciplinas', 'Conteúdos' e 'Status' existem
            3. Adicione seus conteúdos de estudo na planilha
            
            Após adicionar os dados, atualize esta página para ver seu progresso!
            """)
            st.stop()
            
        # Calcula progresso e estatísticas
        df_summary, progresso_geral = DataProcessor.calculate_progress(df)
        stats = DataProcessor.calculate_stats(df_summary)

        # Exibe componentes principais
        UIComponents.display_progress_bar(progresso_geral)
        UIComponents.display_metrics(stats)

        # Seções do dashboard
        st.divider()
        UIComponents.titulo_com_destaque("📊 Progresso Detalhado por Disciplina", cor_lateral="#3498db")
        st.altair_chart(ChartGenerator.create_stacked_bar(df_summary), use_container_width=True)
        
        st.divider()
        UIComponents.titulo_com_destaque("📈 Visão Geral do Progresso", cor_lateral="#2ecc71")
        display_donut_grid(df_summary, progresso_geral)
        
        st.divider()
        UIComponents.titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#9b59b6")
        study_manager = StudyManager()
        study_manager.display_checklist(df)
        
        st.divider()
        UIComponents.titulo_com_destaque("📝 Análise Estratégica da Prova", cor_lateral="#e67e22")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.altair_chart(create_questions_bar_chart(), use_container_width=True)
        with col2:
            st.altair_chart(create_relevance_bar_chart(), use_container_width=True)
        
        # Rodapé motivacional
        UIComponents.rodape_motivacional()
        
        # Informações de debug (apenas em desenvolvimento)
        if st.secrets.get("debug_mode", False):
            with st.expander("🔧 Informações de Debug"):
                st.write("**Dados carregados:**", len(df), "registros")
                st.write("**Progresso geral:**", f"{progresso_geral}%")
                st.write("**Estatísticas:**", stats)
                st.dataframe(df_summary)
        
    except Exception as e:
        st.error(f"""
        ❌ **Erro inesperado na aplicação**
        
        Detalhes técnicos: {str(e)}
        
        **Possíveis soluções:**
        1. Recarregue a página
        2. Verifique sua conexão com a internet
        3. Confirme se as credenciais do Google Sheets estão corretas
        4. Entre em contato com o suporte se o problema persistir
        """)
        logger.error(f"Erro na aplicação principal: {e}", exc_info=True)

if __name__ == "__main__":
    main()
