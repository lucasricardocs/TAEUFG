# -*- coding: utf--8 -*-
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
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet.worksheet(WORKSHEET_NAME)
    except SpreadsheetNotFound:
        st.error("Planilha não encontrada. Verifique o SPREADSHEET_ID.")
    except Exception as e:
        st.error(f"Erro ao acessar a aba '{WORKSHEET_NAME}': {e}")
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
def titulo_com_destaque(texto, cor_lateral="#0066cc", animation_delay="0s"):
    st.markdown(f"""
    <div class="title-container animated-slide-in" style="border-left: 6px solid {cor_lateral}; animation-delay: {animation_delay};"><h2>{texto}</h2></div>
    """, unsafe_allow_html=True)

def render_top_container(dias_restantes):
    weather_data = get_weather_data('Goiania, BR')
    st.markdown(f"""
    <div class="header-wrapper">
        <div class="smoke-wrapper">
            <span class="smoke-particle"></span>
            <span class="smoke-particle"></span>
            <span class="smoke-particle"></span>
            <span class="smoke-particle"></span>
            <span class="smoke-particle"></span>
            <span class="smoke-particle"></span>
            <span class="smoke-particle"></span>
            <span class="smoke-particle"></span>
        </div>
        <div class="header-container animated-fade-in">
            <div class="header-left"><img src="{GOIAS_FOMENTO_LOGO_URL}" alt="Logo Goiás Fomento"/></div>
            <div class="header-center">
                <h1>Dashboard de Estudos</h1>
                <h2 class="concurso-title">Concurso Escriturário - Goiás Fomento 2025</h2>
            </div>
            <div class="header-right">
                <div class="header-info-top"><span class="location-date">{datetime.now().strftime('Goiânia, Brasil | %d de %B de %Y')} | {weather_data['emoji']} {weather_data['temperature']}</span></div>
                <div class="header-info-bottom"><div class="days-countdown pulse-effect"><span class="countdown-text">Faltam {dias_restantes} dias!</span><span class="sparkle"></span></div></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_progress_bar(progresso_geral):
    st.markdown(f"""
    <div class="animated-fade-in" style="margin: 0.5rem 0 1.5rem 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
            <span style="font-weight: 500; color: #2c3e50;">Progresso Geral</span>
            <span style="font-weight: 600; color: #2c3e50;">{progresso_geral:.1f}%</span>
        </div>
        <div style="height: 12px; background: linear-gradient(90deg, #f8f9fa, #e9ecef); border-radius: 10px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
            <div style="height: 100%; width: {progresso_geral}%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 10px; transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);"></div>
        </div>
    </div>""", unsafe_allow_html=True)

def display_simple_metrics(stats):
    cols = st.columns(4)
    with cols[0]: st.metric("✅ Concluídos", f"{stats['concluidos']}")
    with cols[1]: st.metric("⏳ Pendentes", f"{stats['pendentes']}")
    with cols[2]: st.metric("🏃 Ritmo", f"{stats['topicos_por_dia']}/dia")
    with cols[3]: st.metric("⭐ Prioridade", stats['maior_prioridade'].title())

def create_altair_stacked_bar(df_summary):
    df_percent = df_summary.copy()
    df_percent['Concluido (%)'] = (df_percent['Conteudos_Concluidos'] / df_percent['Total_Conteudos']) * 100
    df_percent['Pendente (%)'] = (df_percent['Conteudos_Pendentes'] / df_percent['Total_Conteudos']) * 100
    df_melted = df_percent.melt(id_vars=['Disciplinas'], value_vars=['Concluido (%)', 'Pendente (%)'], var_name='Status', value_name='Percentual')
    df_melted['Status'] = df_melted['Status'].map({'Concluido (%)': 'Concluido', 'Pendente (%)': 'Pendente'})
    df_melted['Percentual_norm'] = df_melted['Percentual'] / 100
    df_melted['Posicao_norm'] = df_melted.groupby('Disciplinas')['Percentual_norm'].cumsum() - (df_melted['Percentual_norm'] / 2)
    df_melted['PercentText'] = df_melted['Percentual'].apply(lambda x: f"{x:.1f}%")
    df_melted['LabelColor'] = df_melted['Percentual'].apply(lambda x: 'white' if x > 5 else 'transparent')
    bars = alt.Chart(df_melted).mark_bar(stroke='#e9ecef', strokeWidth=2).encode(
        y=alt.Y('Disciplinas:N', sort=None, title=None, axis=alt.Axis(labelColor='#2c3e50', labelFont='Nunito')),
        x=alt.X('Percentual_norm:Q', stack="normalize", axis=alt.Axis(title=None, labels=False)),
        color=alt.Color('Status:N', scale=alt.Scale(domain=['Concluido', 'Pendente'], range=['#28a745', '#dc3545']), legend=None)
    )
    labels = alt.Chart(df_melted).mark_text(align='center', baseline='middle', fontWeight='bold', fontSize=12, font='Nunito').encode(
        y=alt.Y('Disciplinas:N', sort=None), x=alt.X('Posicao_norm:Q'), text=alt.Text('PercentText:N'), color=alt.Color('LabelColor:N', scale=None)
    )
    return (bars + labels).properties(height=350, title=alt.TitleParams(text="Percentual de Conclusão por Disciplina", anchor='middle', fontSize=18, font='Nunito', color='#2c3e50')).configure_view(stroke=None).configure(background='transparent')

def create_progress_donut(source_df, title):
    total = source_df['Valor'].sum()
    concluido_val = source_df[source_df['Status'] == 'Concluido']['Valor'].iloc[0] if 'Concluido' in source_df['Status'].values else 0
    percent_text = f"{(concluido_val / total * 100) if total > 0 else 0:.1f}%"
    base = alt.Chart(source_df).mark_arc(innerRadius=55, cornerRadius=5, stroke='#e9ecef', strokeWidth=2).encode(
        theta=alt.Theta("Valor:Q"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=['Concluido', 'Pendente'], range=['#28a745', '#dc3545']), legend=None),
        order=alt.Order('Status:N', sort='descending'),
        tooltip=['Status', alt.Tooltip('Valor', title="Conteúdos")]
    )
    text = alt.Chart(pd.DataFrame({'text': [percent_text]})).mark_text(size=24, fontWeight='bold', color='#2c3e50', font='Nunito').encode(text='text:N')
    return (base + text).properties(title=alt.TitleParams(text=title, anchor='middle', fontSize=26, dy=-10, color='#2c3e50', font='Nunito')).configure_view(stroke=None).configure(background='transparent')

def display_donuts_grid(df_summary, progresso_geral):
    st.markdown('<div class="animated-fade-in">', unsafe_allow_html=True)
    charts_data = [{'df': pd.DataFrame([{'Status': 'Concluido', 'Valor': progresso_geral}, {'Status': 'Pendente', 'Valor': 100 - progresso_geral}]), 'title': 'Progresso Geral'}]
    for _, row in df_summary.iterrows():
        charts_data.append({'df': pd.DataFrame([{'Status': 'Concluido', 'Valor': row['Conteudos_Concluidos']}, {'Status': 'Pendente', 'Valor': row['Conteudos_Pendentes']}]), 'title': row['Disciplinas'].title()})
    for i in range(0, len(charts_data), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(charts_data):
                with col:
                    st.altair_chart(create_progress_donut(charts_data[i+j]['df'], charts_data[i+j]['title']), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def on_checkbox_change(worksheet, row_number, key, disciplina):
    novo_status = st.session_state.get(key, False)
    if update_status_in_sheet(worksheet, row_number, "TRUE" if novo_status else "FALSE"):
        st.toast("Status atualizado!", icon="✅")
        st.session_state[f"expanded_{disciplina}"] = True
        load_data_with_row_indices.clear()
    else:
        st.toast("Falha ao atualizar.", icon="❌")

def display_conteudos_com_checkboxes(df, df_summary):
    worksheet = get_worksheet()
    if not worksheet: return
    for disc in sorted(df_summary['Disciplinas'].unique()):
        conteudos_disciplina = df[df['Disciplinas'] == disc]
        disc_stats = df_summary[df_summary['Disciplinas'] == disc].iloc[0]
        concluidos = disc_stats['Conteudos_Concluidos']
        total = disc_stats['Total_Conteudos']
        progresso = (concluidos / total) * 100 if total > 0 else 0
        st.markdown(f"""
            <div style="margin: 0.5rem 0;">
                <b style="color: #495057;">{disc.title()}</b> — {int(concluidos)}/{int(total)} ({progresso:.1f}%)
                <div style="background: linear-gradient(90deg, #f8f9fa, #e9ecef); border-radius:8px; height:10px; margin-top:4px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"><div style="width:{progresso}%; background: linear-gradient(90deg, #28a745, #20c997); height:10px; border-radius:8px; transition: width 0.5s ease;"></div></div>
            </div>""", unsafe_allow_html=True)
        expanded_key = f"expanded_{disc}"
        with st.container():
            if st.button(f"Ver conteúdos de {disc.title()}", key=f"btn_{disc}"):
                st.session_state[expanded_key] = not st.session_state.get(expanded_key, False)
            if st.session_state.get(expanded_key, False):
                st.markdown('<div style="padding: 15px; border-left: 4px solid #6c757d; margin-left: 10px; background: linear-gradient(135deg, #f8f9fa, #ffffff); border-radius: 0 8px 8px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">', unsafe_allow_html=True)
                for _, row in conteudos_disciplina.iterrows():
                    key = f"cb_{row['sheet_row']}"
                    st.checkbox(label=row['Conteúdos'], value=bool(row['Status']), key=key, on_change=on_checkbox_change, args=(worksheet, row['sheet_row'], key, disc))
                st.markdown('</div>', unsafe_allow_html=True)

def bar_questoes_padronizado(ed_data):
    df = pd.DataFrame(ed_data)
    PALETA_CORES = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
    bars = alt.Chart(df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, stroke='#e9ecef', strokeWidth=2).encode(
        x=alt.X('Disciplinas:N', sort=None, title=None, axis=alt.Axis(labelAngle=0, labelFont='Nunito', labelColor='#2c3e50')),
        y=alt.Y('Questões:Q', title=None, axis=alt.Axis(labels=False, ticks=True)),
        color=alt.Color('Disciplinas:N', scale=alt.Scale(range=PALETA_CORES), legend=None)
    )
    labels = bars.mark_text(align='center', baseline='bottom', dy=-5, color='#2c3e50', fontWeight='bold', font='Nunito').encode(text='Questões:Q')
    return (bars + labels).properties(width=500, height=500, title=alt.TitleParams(text='Distribuição de Questões', anchor='middle', fontSize=18, font='Nunito', color='#2c3e50')).configure_view(stroke=None).configure(background='transparent')

def bar_relevancia_customizado(ed_data):
    df = pd.DataFrame(ed_data)
    df['Relevancia'] = df['Peso'] * df['Questões']
    df['Percentual'] = df['Relevancia'] / df['Relevancia'].sum() * 100
    df['custom_label'] = df.apply(lambda row: f"{row['Disciplinas']} ({row['Percentual']:.1f}%)", axis=1)
    color_scale = alt.Scale(domain=[df['Relevancia'].min(), df['Relevancia'].max()], range=['#e3f2fd', '#1976d2'])
    bars = alt.Chart(df).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3, stroke='#e9ecef', strokeWidth=2, size=70).encode(
        y=alt.Y('Disciplinas:N', sort='-x', title=None, axis=alt.Axis(labels=False)),
        x=alt.X('Relevancia:Q', title=None, axis=alt.Axis(labels=False, grid=False)),
        color=alt.Color('Relevancia:Q', scale=color_scale, legend=None),
        tooltip=['Disciplinas:N', 'Peso:Q', 'Questões:Q', 'Relevancia:Q', alt.Tooltip('Percentual:Q', format='.1f')]
    )
    text = bars.mark_text(align='left', baseline='middle', dx=3, color='#2c3e50', fontWeight='bold', fontSize=12, font='Nunito').encode(
        y=alt.Y('Disciplinas:N', sort='-x', title=None, axis=alt.Axis(labelColor='#e9ecef')),
        x=alt.X('Relevancia:Q'),
        text='custom_label:N'
    )
    return (bars + text).properties(width=500, height=500, title=alt.TitleParams(text='Relevância das Disciplinas', anchor='middle', fontSize=18, font='Nunito', color='#2c3e50')).configure_view(stroke=None).configure(background='transparent')

def rodape_motivacional():
    frase_aleatoria = random.choice(FRASES_MOTIVACIONAIS)
    st.markdown("<hr style='margin: 0.5rem 0; border: 1px solid #e9ecef;'>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align: center; color: #6c757d;'><p>{frase_aleatoria}</p></div>", unsafe_allow_html=True)

# --- Função Principal da Aplicação ---
def main():
    st.set_page_config(
        page_title="Dashboard de Estudos - Goiás Fomento",
        page_icon="📚", layout="wide", initial_sidebar_state="collapsed"
    )
    alt.themes.enable('none')
    
    # CSS com animações nos containers de título e esquema de cores melhorado
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * { font-family: 'Nunito', sans-serif !important; }
        .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); color: #2c3e50; }
        
        /* Animações */
        @keyframes fadeIn { 
            from { opacity: 0; transform: translateY(30px); } 
            to { opacity: 1; transform: translateY(0); } 
        }
        @keyframes slideInLeft { 
            from { opacity: 0; transform: translateX(-50px); } 
            to { opacity: 1; transform: translateX(0); } 
        }
        @keyframes slideInRight { 
            from { opacity: 0; transform: translateX(50px); } 
            to { opacity: 1; transform: translateX(0); } 
        }
        @keyframes bounceIn { 
            0% { opacity: 0; transform: scale(0.3); }
            50% { opacity: 1; transform: scale(1.05); }
            70% { transform: scale(0.9); }
            100% { opacity: 1; transform: scale(1); }
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2); }
            50% { box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4); }
        }
        
        .animated-fade-in { animation: fadeIn 1s ease-out; }
        .animated-slide-in { animation: slideInLeft 0.8s ease-out; }
        .animated-bounce-in { animation: bounceIn 1.2s ease-out; }
        
        .header-wrapper { 
            position: relative; 
            margin-bottom: 2rem; 
            overflow: hidden;
            border-radius: clamp(15px, 2vw, 20px);
        }
        
        .header-container {
            width: 100%; min-height: 200px; height: clamp(200px, 22vh, 280px);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: clamp(15px, 2vw, 20px); 
            box-shadow: 0 15px 35px rgba(102, 126, 234, 0.3);
            border: 1px solid rgba(255,255,255,0.2); 
            padding: clamp(15px, 2vw, 25px) clamp(20px, 3vw, 40px);
            display: flex; justify-content: space-between; align-items: center;
            position: relative; z-index: 2;
            animation: glow 3s ease-in-out infinite;
        }
        .header-left, .header-center, .header-right { display: flex; align-items: center; height: 100%; }
        .header-left { flex: 1.2; justify-content: flex-start; }
        .header-left img { max-width: clamp(160px, 18vw, 260px); height: auto; object-fit: contain; }
        .header-center { flex: 2; flex-direction: column; justify-content: center; text-align: center; }
        .header-center h1 { font-size: clamp(1.6rem, 3.5vw, 2.5rem); font-weight: 800; color: #ffffff; margin: 0; line-height: 1.1; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }
        .header-center .concurso-title { font-size: clamp(0.9rem, 2vw, 1.3rem); font-weight: 600; margin: 0.2rem 0 0 0; font-style: italic; color: #f8f9fa; line-height: 1.1; text-shadow: 0 1px 2px rgba(0,0,0,0.2); }
        
        .header-right { flex: 1.2; flex-direction: column; justify-content: space-between; align-items: flex-end; text-align: right; height: 90%; }
        .header-info-top, .header-info-bottom { width: 100%; }
        .header-info-top .location-date { font-size: clamp(0.65rem, 1vw, 0.85rem); color: #f8f9fa; text-shadow: 0 1px 2px rgba(0,0,0,0.2); }
        .days-countdown { font-size: clamp(1.2rem, 2.5vw, 2.2rem); font-weight: 700; color: #ffd700; animation: pulse 2s infinite ease-in-out; position: relative; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }
        
        .sparkle::before { content: '✨'; font-size: clamp(1rem, 2vw, 1.8rem); position: absolute; right: -15px; top: 50%; transform: translateY(-50%); animation: sparkle-anim 1.5s infinite; }
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        @keyframes sparkle-anim { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }

        /* Efeito de fumaça aprimorado */
        .smoke-wrapper { 
            position: absolute; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%; 
            z-index: 1; 
            pointer-events: none; 
            overflow: hidden;
            border-radius: clamp(15px, 2vw, 20px);
        }
        
        .smoke-particle {
            position: absolute;
            bottom: -100px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, rgba(200, 220, 255, 0.2) 40%, rgba(160, 180, 220, 0.1) 70%, transparent 100%);
            border-radius: 50%;
            filter: blur(20px);
            animation: smoke-rise linear infinite;
        }
        
        .smoke-particle:nth-child(1) { left: 2%; width: 120px; height: 120px; animation-duration: 18s; animation-delay: -2s; }
        .smoke-particle:nth-child(2) { left: 15%; width: 180px; height: 180px; animation-duration: 22s; animation-delay: -8s; }
        .smoke-particle:nth-child(3) { left: 28%; width: 140px; height: 140px; animation-duration: 20s; animation-delay: -5s; }
        .smoke-particle:nth-child(4) { left: 42%; width: 200px; height: 200px; animation-duration: 25s; animation-delay: -12s; }
        .smoke-particle:nth-child(5) { left: 58%; width: 160px; height: 160px; animation-duration: 19s; animation-delay: -3s; }
        .smoke-particle:nth-child(6) { left: 72%; width: 190px; height: 190px; animation-duration: 24s; animation-delay: -10s; }
        .smoke-particle:nth-child(7) { left: 85%; width: 150px; height: 150px; animation-duration: 21s; animation-delay: -6s; }
        .smoke-particle:nth-child(8) { left: 95%; width: 130px; height: 130px; animation-duration: 17s; animation-delay: -1s; }
        
        @keyframes smoke-rise { 
            0% { transform: translateY(0) translateX(0) scale(0.8) rotate(0deg); opacity: 0.6; } 
            25% { transform: translateY(-150px) translateX(20px) scale(1.2) rotate(90deg); opacity: 0.4; }
            50% { transform: translateY(-300px) translateX(-10px) scale(1.8) rotate(180deg); opacity: 0.25; }
            75% { transform: translateY(-450px) translateX(30px) scale(2.4) rotate(270deg); opacity: 0.1; }
            100% { transform: translateY(-600px) translateX(-20px) scale(3.0) rotate(360deg); opacity: 0; } 
        }

        @media (max-width: 768px) {
            .header-container { flex-direction: column; height: auto; min-height: auto; gap: 20px; padding: 20px; }
            .header-left, .header-center, .header-right { width: 100%; text-align: center; height: auto; }
            .header-right { align-items: center; justify-content: center; gap: 10px; }
            .smoke-particle { display: none; }
        }
        
        /* Containers de título com animações */
        .title-container { 
            border: 1px solid #e9ecef; 
            border-left: 6px solid #667eea; 
            padding: 1.2rem 1.8rem; 
            border-radius: 12px; 
            margin: 2rem 0 1.5rem 0; 
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); 
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .title-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
            transition: left 0.5s;
        }
        
        .title-container:hover::before {
            left: 100%;
        }
        
        .title-container:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.15);
        }
        
        .title-container h2 { 
            font-weight: 700; 
            font-size: clamp(1.2rem, 2vw, 1.6rem); 
            color: #2c3e50; 
            margin: 0; 
            position: relative;
            z-index: 1;
        }
        
        /* Métricas com cores melhoradas */
        [data-testid="stMetricValue"] { 
            font-size: clamp(1.2rem, 2vw, 1.8rem); 
            font-weight: bold; 
            color: #495057;
        }
        [data-testid="stMetricLabel"] { 
            font-size: clamp(0.8rem, 1.2vw, 1rem); 
            color: #6c757d;
        }
        
        /* Botões com gradiente melhorado */
        .stButton > button { 
            width: 100%; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            border: none; 
            border-radius: 10px; 
            padding: 0.8rem 1.2rem; 
            font-weight: 600; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.25);
            position: relative;
            overflow: hidden;
        }
        
        .stButton > button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }
        
        .stButton > button:hover::before {
            left: 100%;
        }
        
        .stButton > button:hover { 
            transform: translateY(-3px); 
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); 
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%); 
        }
        
        /* Checkboxes com estilo melhorado */
        .stCheckbox > label > div:first-child {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border: 2px solid #dee2e6;
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        
        .stCheckbox > label > div:first-child:hover {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_top_container(dias_restantes)

    df = load_data_with_row_indices()
    if df.empty:
        st.info("👋 Bem-vindo! Sua planilha de estudos parece estar vazia. Adicione os conteúdos na Google Sheet para começar.")
        st.stop()
        
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df_summary)
    
    display_progress_bar(progresso_geral)
    display_simple_metrics(stats)

    titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#28a745", animation_delay="0.2s")
    display_conteudos_com_checkboxes(df, df_summary)
    
    titulo_com_destaque("📊 Progresso Detalhado", cor_lateral="#667eea", animation_delay="0.4s")
    st.altair_chart(create_altair_stacked_bar(df_summary), use_container_width=True)
    
    titulo_com_destaque("📈 Visão Geral do Progresso", cor_lateral="#764ba2", animation_delay="0.6s")
    display_donuts_grid(df_summary, progresso_geral)
    
    titulo_com_destaque("📝 Análise Estratégica da Prova", cor_lateral="#f093fb", animation_delay="0.8s")
    colA, colB = st.columns([2, 3])
    with colA:
        st.altair_chart(bar_questoes_padronizado(ED_DATA), use_container_width=True)
    with colB:
        st.altair_chart(bar_relevancia_customizado(ED_DATA), use_container_width=True)
    
    rodape_motivacional()

if __name__ == "__main__":
    main()
