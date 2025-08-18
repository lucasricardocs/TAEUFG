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

ED_DATA = {
    'Disciplinas': ['PORTUGUES', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'ESPECÍFICOS'],
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
    "Visualize seu nome na lista de aprovados. É a sua motivação final.",
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
@st.cache_data(ttl=3600)  # Armazena em cache por 1 hora
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
        <h2 style="color: #2c3e50; font-family: 'Nunito', sans-serif;">
            {texto}
        </h2>
    </div>""", unsafe_allow_html=True)

def render_topbar_with_logo(dias_restantes):
    weather_data = get_weather_data('Goiania, BR')
    
    st.markdown(f"""
    <div class="top-container">
        <div class="top-container-left">
            <img src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG" style="height: 70px; margin-right: 1.5rem;"/>
            <div class="titles-container">
                <h1 style="margin: 0;">
                    Dashboard de Estudos
                </h1>
                <p style="margin: 0;">
                    Concurso TAE UFG 2025
                </p>
            </div>
        </div>
        <div class="top-container-right">
            <div class="weather-info">
                Goiânia, Brasil | {datetime.now().strftime('%d de %B de %Y')} | {weather_data['emoji']} {weather_data['temperature']}
            </div>
            <div class="days-countdown">
                ⏰ Faltam {dias_restantes} dias!
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_progress_bar(progresso_geral):
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

def display_simple_metrics(stats):
    cols = st.columns(4)
    with cols[0]:
        st.metric("✅ Concluídos", f"{stats['concluidos']}")
    with cols[1]:
        st.metric("⏳ Pendentes", f"{stats['pendentes']}")
    with cols[2]:
        st.metric("🏃 Ritmo", f"{stats['topicos_por_dia']}/dia")
    with cols[3]:
        st.metric("⭐ Prioridade", stats['maior_prioridade'].title())

def create_altair_stacked_bar(df_summary):
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

    df_melted['PercentText'] = df_melted['Percentual'].apply(lambda x: f"{x:.1f}%")

    def label_color(row, df_row):
        if row['Percentual'] > 0:
            return 'black'
        return 'transparent'

    df_melted['LabelColor'] = df_melted.apply(lambda row: label_color(row, df_percent[df_percent['Disciplinas']==row['Disciplinas']].iloc[0]), axis=1)

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
        color=alt.Color('LabelColor:N', scale=None)
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
    ).configure_axis(
        labelFont='Nunito',
        titleFont='Nunito'
    )

def create_progress_donut(source_df, title):
    total = source_df['Valor'].sum()
    concluido_val = source_df[source_df['Status'] == 'Concluido']['Valor'].iloc[0]
    percent_text = f"{(concluido_val / total * 100) if total > 0 else 0:.1f}%"

    base = alt.Chart(source_df).mark_arc(innerRadius=55, cornerRadius=5, stroke='#d3d3d3', strokeWidth=1).encode(
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

def display_donuts_grid(df_summary, progresso_geral):
    st.markdown('<div class="animated-fade-in">', unsafe_allow_html=True)
    charts_data = []
    prog_geral_df = pd.DataFrame([
        {'Status': 'Concluido', 'Valor': progresso_geral},
        {'Status': 'Pendente', 'Valor': 100 - progresso_geral}
    ])
    charts_data.append({'df': prog_geral_df, 'title': 'Progresso Geral'})

    for _, row in df_summary.iterrows():
        df = pd.DataFrame([
            {'Status': 'Concluido', 'Valor': row['Conteudos_Concluidos']},
            {'Status': 'Pendente', 'Valor': row['Conteudos_Pendentes']}
        ])
        charts_data.append({'df': df, 'title': row['Disciplinas'].title()})

    for i in range(0, len(charts_data), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(charts_data):
                with cols[j]:
                    chart_info = charts_data[i+j]
                    donut = create_progress_donut(chart_info['df'], chart_info['title'])
                    st.altair_chart(donut, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


def on_checkbox_change(worksheet, row_number, key):
    novo_status = st.session_state[key]
    if update_status_in_sheet(worksheet, row_number, "TRUE" if novo_status else "FALSE"):
        st.toast("Status atualizado!", icon="✅")
        load_data_with_row_indices.clear()
        
    else:
        st.toast(f"Falha ao atualizar.", icon="❌")

def display_conteudos_com_checkboxes(df):
    worksheet = get_worksheet()
    if not worksheet:
        return
    
    search_query = st.text_input("🔍 Buscar conteúdos...", placeholder="Ex: Informática, RLM...").strip().upper()
    
    if search_query:
        df_filtered = df[df.apply(lambda row: search_query in row['Disciplinas'] or search_query in row['Conteúdos'].upper(), axis=1)]
    else:
        df_filtered = df

    for disc in sorted(df_filtered['Disciplinas'].unique()):
        conteudos_disciplina = df_filtered[df_filtered['Disciplinas'] == disc]
        
        concluidos = conteudos_disciplina['Status'].sum()
        total = len(conteudos_disciplina)
        progresso = (concluidos / total) * 100 if total > 0 else 0
        
        with st.expander(f"**{disc.title()}** - {concluidos}/{total} ({progresso:.1f}%)"):
            
            for _, row in conteudos_disciplina.iterrows():
                key = f"cb_{row['sheet_row']}"
                
                if key not in st.session_state:
                    st.session_state[key] = bool(row['Status'])

                st.checkbox(
                    label=row['Conteúdos'],
                    value=st.session_state[key],
                    key=key,
                    on_change=on_checkbox_change,
                    kwargs={
                        'worksheet': worksheet,
                        'row_number': row['sheet_row'],
                        'key': key
                    }
                )

# --- Gráficos ---
PALETA_CORES = ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#f1c40f']

def bar_questoes_padronizado(ed_data):
    df = pd.DataFrame(ed_data)

    bars = alt.Chart(df).mark_bar(
        cornerRadiusTopLeft=2,
        cornerRadiusTopRight=2,
        stroke='#d3d3d3',
        strokeWidth=1
    ).encode(
        x=alt.X('Disciplinas:N', sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFont='Nunito', labelColor='#000000')),
        y=alt.Y('Questões:Q', title=None, axis=alt.Axis(labels=False, ticks=True)),
        color=alt.Color('Disciplinas:N', scale=alt.Scale(range=PALETA_CORES), legend=None)
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
    ).configure_axis(
        labelFont='Nunito',
        titleFont='Nunito'
    )

def bar_relevancia_customizado(ed_data):
    df = pd.DataFrame(ed_data)
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
        y=alt.Y('Disciplinas:N', sort='-x', title=None, axis=alt.Axis(labels=False)),  # Remover rótulos do eixo Y
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
    ).configure_axis(
        labelFont='Nunito',
        titleFont='Nunito'
    )

def rodape_motivacional():
    frase_aleatoria = random.choice(FRASES_MOTIVACIONAIS)
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; margin: 0.5rem 0; padding: 1rem; color: #555;">
        <p style='font-size: 0.9rem; margin: 0; font-family: "Nunito", sans-serif;'>
            🚀 {frase_aleatoria} ✨
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- Função Principal da Aplicação ---
def main():
    st.set_page_config(
        page_title="📚 Dashboard de Estudos - Concurso TAE UFG",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Configura um tema vazio para garantir fundos transparentes
    alt.themes.enable('none')
    
    # CSS com animações e efeitos
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        /* Tipografia e cores globais */
        * {
            font-family: 'Nunito', sans-serif !important;
        }
        
        .stApp {
            background-color: #f7f9fc;
            color: #333;
        }
        
        /* Fundo transparente para todos os gráficos */
        .stApp [data-testid="stVegaLiteChart"] > div,
        .vega-embed.has-actions {
            background-color: transparent !important;
        }

        /* Animação de Fade-in */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animated-fade-in {
            animation: fadeIn 0.8s ease-out;
        }

        /* ==================================== */
        /* ======== CONTAINER DO TOPO REORGANIZADO ======== */
        /* ==================================== */
        .top-container {
            background: linear-gradient(135deg, #e0f0ff, #f0f8ff);
            border-radius: 18px;
            padding: 1.5rem 2rem;
            box-shadow: 0 8px 30px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            border: 1px solid #d3d3d3;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 250px; /* Altura fixa de 250px */
        }
        .top-container-left {
            display: flex;
            align-items: center;
            flex: 1;
            height: 100%;
            justify-content: center;
        }
        .titles-container {
            text-align: center;
        }
        .titles-container h1 {
            color: #2c3e50;
            margin: 0;
            font-size: 2.8rem;
            font-weight: 700;
            line-height: 1.2;
        }
        .titles-container p {
            color: #555;
            margin: 0;
            font-size: 1.6rem;
            font-weight: 500;
        }
        .top-container-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            justify-content: space-between;
            height: 100%;
            flex: 1;
        }
        .weather-info {
            font-size: 1.1rem;
            color: #777;
            margin-bottom: 0.5rem;
            font-weight: 400;
        }

        /* ==================================== */
        /* ======== DESTAQUE PARA CONTADOR DE DIAS ======== */
        /* ==================================== */
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .days-countdown {
            animation: pulse 2s infinite;
            color: #e74c3c;
            font-weight: 800;
            font-size: 4rem;
            margin: 0;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.15);
            line-height: 1.1;
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
        /* ======== REMOÇÃO COMPLETA DAS SETAS ======== */
        /* ==================================== */
        .streamlit-expanderHeader::before {
            display: none;
        }
        .streamlit-expanderHeader svg {
            display: none !important;
        }
        .streamlit-expanderHeader {
            padding-left: 1rem !important;
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
    </style>
    """, unsafe_allow_html=True)
    
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_topbar_with_logo(dias_restantes)

    df = load_data_with_row_indices()

    if df.empty:
        st.info("👋 Bem-vindo! Parece que sua planilha de estudos está vazia. Adicione os conteúdos na sua Google Sheet para começar a monitorar seu progresso aqui.")
        st.stop()
        
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df_summary)

    display_progress_bar(progresso_geral)
    display_simple_metrics(stats)

    st.divider()
    titulo_com_destaque("📊 Progresso Detalhado por Disciplina", cor_lateral="#3498db")
    st.altair_chart(create_altair_stacked_bar(df_summary), use_container_width=True)
    
    st.divider()
    titulo_com_destaque("📈 Visão Geral do Progresso", cor_lateral="#2ecc71")
    display_donuts_grid(df_summary, progresso_geral)
    
    st.divider()
    titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#9b59b6")
    display_conteudos_com_checkboxes(df)
    
    st.divider()
    titulo_com_destaque("📝 Análise Estratégica da Prova", cor_lateral="#e67e22")
    colA, colB = st.columns([2, 3])
    with colA:
        st.altair_chart(bar_questoes_padronizado(ED_DATA), use_container_width=True)
    with colB:
        st.altair_chart(bar_relevancia_customizado(ED_DATA), use_container_width=True)
    
    rodape_motivacional()

if __name__ == "__main__":
    main()
