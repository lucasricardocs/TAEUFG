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
@st.cache_data(ttl=10) # Armazena em cache por 1 hora
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

def render_top_container(dias_restantes):
    weather_data = get_weather_data('Goiania, BR')
    
    st.markdown(f"""
    <div class="header-container animated-fade-in">
        <div class="header-left">
            <img src="{UFG_LOGO_URL}" alt="Logo UFG" style="height: 100px;"/>
        </div>
        <div class="header-center">
            <h1>Dashboard de Estudos</h1>
            <h2>Concurso TAE UFG 2025</h2>
        </div>
        <div class="header-right">
            <div class="header-info-top">
                <span class="location-date">Goiânia, Brasil | {datetime.now().strftime('%d de %B de %Y')}</span>
                <span class="weather-info">{weather_data['emoji']} {weather_data['temperature']}</span>
            </div>
            <div class="header-info-bottom">
                <div class="days-countdown pulse-effect">
                    <div class="fire-effect"></div>
                    <div class="flag-effect"></div>
                    FALTAM {dias_restantes} DIAS
                </div>
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
        strokeWidth=2
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

    base = alt.Chart(source_df).mark_arc(innerRadius=55, cornerRadius=5, stroke='#d3d3d3', strokeWidth=2).encode(
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

def on_checkbox_change(worksheet, row_number, key, disciplina):
    """Atualiza status no Google Sheets e recarrega dados, mantendo a seção aberta"""
    novo_status = st.session_state.get(key, False)
    if update_status_in_sheet(worksheet, row_number, "TRUE" if novo_status else "FALSE"):
        st.toast("Status atualizado!", icon="✅")
        # Marca que esta disciplina deve ficar aberta
        st.session_state[f"expanded_{disciplina}"] = True
        load_data_with_row_indices.clear()
        # Não é mais necessário, Streamlit já reinicia automaticamente
    else:
        st.toast("Falha ao atualizar.", icon="❌")

def display_conteudos_com_checkboxes(df, df_summary):
    worksheet = get_worksheet()
    if not worksheet:
        return
    
    # Removido: barra de busca e a lógica de filtragem
    df_filtered = df

    # Garante que Status seja boolean
    df_filtered['Status'] = df_filtered['Status'].astype(str).str.upper().map({"TRUE": True, "FALSE": False})

    # 🔄 Itera pelas disciplinas
    for disc in sorted(df_filtered['Disciplinas'].unique()):
        conteudos_disciplina = df_filtered[df_filtered['Disciplinas'] == disc]
        
        # Usa os dados do df_summary para evitar recálculo
        if disc in df_summary['Disciplinas'].values:
            disc_stats = df_summary[df_summary['Disciplinas'] == disc].iloc[0]
            concluidos = disc_stats['Conteudos_Concluidos']
            total = disc_stats['Total_Conteudos']
            progresso = (concluidos / total) * 100 if total > 0 else 0
        else: # Caso a disciplina não esteja no edital_data, calcula apenas para exibir
            concluidos = conteudos_disciplina['Status'].sum()
            total = len(conteudos_disciplina)
            progresso = (concluidos / total) * 100 if total > 0 else 0

        # 📊 Header com barra de progresso estilizada
        st.markdown(f"""
            <div style="margin: 0.5rem 0;">
                <b>{disc.title()}</b> — {int(concluidos)}/{int(total)} ({progresso:.1f}%)
                <div style="background:#eee; border-radius:8px; height:10px; margin-top:4px;">
                    <div style="width:{progresso}%; background:#4CAF50; height:10px; border-radius:8px;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Verifica se esta disciplina deve ficar expandida
        expanded_key = f"expanded_{disc}"
        is_expanded = st.session_state.get(expanded_key, False)

        # 📂 Container customizado que substitui o expander
        with st.container():
            # Botão para expandir/contrair
            if st.button(f"📁 Ver conteúdos de {disc.title()}", key=f"btn_{disc}"):
                st.session_state[expanded_key] = not st.session_state.get(expanded_key, False)
                # O rerun aqui é mantido para alternar o estado do container
                st.rerun()
            
            # Mostra o conteúdo se estiver expandido
            if st.session_state.get(expanded_key, False):
                st.markdown('<div style="padding: 10px; border-left: 3px solid #ddd; margin-left: 10px;">', unsafe_allow_html=True)
                for _, row in conteudos_disciplina.iterrows():
                    key = f"cb_{row['sheet_row']}"
                    st.checkbox(
                        label=row['Conteúdos'],
                        value=bool(row['Status']),
                        key=key,
                        on_change=on_checkbox_change,
                        args=(worksheet, row['sheet_row'], key, disc)
                    )
                st.markdown('</div>', unsafe_allow_html=True)


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
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
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
        /* ======== CONTAINER DO TOPO NOVO ======== */
        /* ==================================== */
        .header-container {
            width: 100%;
            height: 300px;
            background: linear-gradient(135deg, #e0f0ff, #f0f8ff);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            border: 1px solid #d3d3d3;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            overflow: hidden; /* Garante que os efeitos fiquem dentro do container */
            position: relative;
            margin-bottom: 2rem;
        }
        
        .header-left, .header-center, .header-right {
            display: flex;
            align-items: center;
            height: 100%;
        }

        .header-left {
            flex-grow: 1;
            justify-content: flex-start;
        }
        
        .header-left img {
            max-width: 150px;
            height: auto;
            object-fit: contain;
        }
        
        .header-center {
            flex-grow: 2;
            flex-direction: column;
            justify-content: center;
            text-align: center;
            line-height: 1;
        }
        
        .header-center h1 {
            font-size: 3.5rem;
            font-weight: 800;
            color: #2c3e50;
            margin: 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
        }
        
        .header-center h2 {
            font-size: 1.8rem;
            font-weight: 600;
            color: #555;
            margin: 0;
        }

        .header-right {
            flex-grow: 1;
            flex-direction: column;
            justify-content: space-between;
            align-items: flex-end;
            text-align: right;
            position: relative;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        
        .header-info-top, .header-info-bottom {
            width: 100%;
        }

        .location-date, .weather-info {
            font-size: 1rem;
            color: #777;
            font-weight: 400;
        }
        
        .weather-info {
            margin-left: 10px;
        }
        
        .days-countdown {
            font-size: 3rem;
            font-weight: 900;
            color: #e74c3c;
            line-height: 1;
            position: relative;
            display: inline-block;
            overflow: visible;
        }
        
        /* Animação de pulso */
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .pulse-effect {
            animation: pulse 2s infinite ease-in-out;
        }
        
        /* Animação de "fogo" - Sutil para evitar poluir o layout */
        .fire-effect {
            position: absolute;
            bottom: -5px;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            height: 20px;
            background: radial-gradient(ellipse at center, rgba(255,100,0,0.8) 0%, rgba(255,200,0,0.5) 50%, transparent 70%);
            z-index: -1;
            filter: blur(8px);
            animation: fire-flicker 2s infinite ease-in-out;
            opacity: 0.7;
        }
        @keyframes fire-flicker {
            0%, 100% { opacity: 0.7; transform: scale(1) translateX(-50%); }
            25% { opacity: 0.9; transform: scale(1.05) translateX(-50%); }
            50% { opacity: 0.8; transform: scale(1.02) translateX(-50%); }
            75% { opacity: 0.85; transform: scale(1.03) translateX(-50%); }
        }

        /* Animação de "flâmulas" - Linhas sutis para simular a bandeira */
        .flag-effect {
            position: absolute;
            top: 0;
            left: 50%;
            width: 120%;
            height: 100%;
            transform: translateX(-50%);
            z-index: -2;
            background-image:
                linear-gradient(rgba(255,255,255,0.2) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.2) 1px, transparent 1px);
            background-size: 20px 20px, 20px 20px;
            animation: flag-wave 6s infinite linear;
        }
        @keyframes flag-wave {
            from { background-position: 0 0; }
            to { background-position: -200px -200px; }
        }

        @media (max-width: 1200px) {
            .header-container {
                flex-direction: column;
                height: auto;
                padding: 20px;
                text-align: center;
                gap: 20px;
            }
            .header-left, .header-center, .header-right {
                flex-grow: initial;
                justify-content: center;
                width: 100%;
            }
            .header-right {
                align-items: center;
            }
            .header-info-top {
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .weather-info {
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
