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
    "Não desista. O caminho pode ser difícil, mas a vitória vale a pena."
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

# ✅ FUNÇÃO CRÍTICA MODIFICADA - Remove cache para atualização instantânea
def load_data_with_row_indices():
    """
    IMPORTANTE: Removido @st.cache_data para permitir atualização instantânea
    """
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

# ✅ FUNÇÃO CRÍTICA MODIFICADA - Força atualização instantânea dos gráficos
def on_checkbox_change(worksheet, row_number, key):
    """
    Atualiza o Google Sheets E força recarga instantânea dos gráficos
    """
    novo_status = st.session_state.get(key, False)
    
    # Atualiza na planilha
    if update_status_in_sheet(worksheet, row_number, "TRUE" if novo_status else "FALSE"):
        # ✅ SOLUÇÃO: Recarrega dados sem cache
        st.session_state['df_data'] = load_data_with_row_indices()
        
        # ✅ SOLUÇÃO: Marca timestamp da última atualização
        st.session_state['last_update'] = time.time()
        
        st.toast("✅ Gráficos atualizados!", icon="📊")
    else:
        st.toast("❌ Erro na atualização", icon="⚠️")
        # Reverte o checkbox se falhou
        st.session_state[key] = not novo_status

# --- Funções de Lógica e Cálculos ---
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

# --- Funções para buscar dados de clima ---
@st.cache_data(ttl=3600)
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
                'Mist': '🌫️', 'Fog': '🌫️', 'Haze': '🌫️'
            }
            emoji = weather_emojis.get(status, '🌍')
            
            return {"temperature": f"{temperature:.0f}°C", "emoji": emoji}
        else:
            return {"temperature": "N/A", "emoji": "🤷"}
    except:
        return {"temperature": "N/A", "emoji": "🤷"}

# --- Funções de Interface ---
def render_topbar_with_logo(dias_restantes):
    weather_data = get_weather_data('Goiania, BR')
    st.markdown(f"""
    <div class="top-container">
        <div class="top-container-main">
            <img src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG" style="height: 90px;"/>
            <div class="titles-container">
                <h1>Dashboard de Estudos</h1>
                <p>Concurso TAE UFG 2025</p>
            </div>
        </div>
        <div class="top-container-info">
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

    bars = alt.Chart(df_melted).mark_bar(
        stroke='#d3d3d3',
        strokeWidth=2
    ).encode(
        y=alt.Y('Disciplinas:N', sort=None, title=None),
        x=alt.X('Percentual_norm:Q', stack="normalize", axis=alt.Axis(title=None, labels=False)),
        color=alt.Color('Status:N',
                        scale=alt.Scale(domain=['Concluido', 'Pendente'], range=['#2ecc71', '#e74c3c']),
                        legend=None)
    )

    labels = alt.Chart(df_melted).mark_text(
        align='center',
        baseline='middle',
        fontWeight='bold',
        fontSize=12
    ).encode(
        y=alt.Y('Disciplinas:N', sort=None),
        x=alt.X('Posicao_norm:Q'),
        text=alt.Text('PercentText:N'),
        color=alt.value('black')
    )

    return (bars + labels).properties(
        height=350,
        title="📊 Progresso por Disciplina (ATUALIZADO INSTANTANEAMENTE)"
    )

def display_conteudos_com_checkboxes(df):
    """
    ✅ FUNÇÃO MODIFICADA para atualização instantânea
    """
    worksheet = get_worksheet()
    if not worksheet: return
    
    search_query = st.text_input("🔍 Buscar conteúdos...", placeholder="Ex: Informática, RLM").strip().upper()
    
    df_filtered = df
    if search_query:
        df_filtered = df[df.apply(
            lambda row: (search_query in row['Disciplinas'].upper()) or 
                        (search_query in row['Conteúdos'].upper()),
            axis=1
        )]
        if df_filtered.empty:
            st.warning("Nenhum conteúdo encontrado.")
            return

    df_filtered['Status'] = df_filtered['Status'].astype(str).str.upper().map({"TRUE": True, "FALSE": False})
    
    for disc in sorted(df_filtered['Disciplinas'].unique()):
        conteudos_disciplina = df_filtered[df_filtered['Disciplinas'] == disc]
        
        concluidos = conteudos_disciplina['Status'].sum()
        total = len(conteudos_disciplina)
        progresso = (concluidos / total) * 100 if total > 0 else 0
        
        st.markdown(f"""
            <div style="margin: 0.5rem 0;">
                <b>{disc.title()}</b> — {concluidos}/{total} ({progresso:.1f}%)
                <div style="background:#eee; border-radius:8px; height:10px; margin-top:4px;">
                    <div style="width:{progresso}%; background:#4CAF50; height:10px; border-radius:8px;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            is_expanded = st.session_state.get(f"expanded_{disc}", False)
            if st.button(f"📁 {'Fechar' if is_expanded else 'Ver'} conteúdos de {disc.title()}", key=f"btn_{disc}"):
                st.session_state[f"expanded_{disc}"] = not is_expanded
                st.rerun()
            
            if st.session_state.get(f"expanded_{disc}", False):
                st.markdown('<div style="padding: 10px; border-left: 3px solid #ddd; margin-left: 10px;">', unsafe_allow_html=True)
                for _, row in conteudos_disciplina.iterrows():
                    key = f"cb_{row['sheet_row']}"
                    # ✅ CRÍTICO: Usa callback que força atualização instantânea
                    st.checkbox(
                        label=row['Conteúdos'],
                        value=bool(row['Status']),
                        key=key,
                        on_change=on_checkbox_change,
                        args=(worksheet, row['sheet_row'], key)
                    )
                st.markdown('</div>', unsafe_allow_html=True)

# --- Função Principal (Modificada para atualização instantânea) ---
def main():
    st.set_page_config(
        page_title="📚 Dashboard de Estudos - Concurso TAE UFG",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # CSS do dashboard
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { font-family: 'Nunito', sans-serif !important; }
        .stApp { background-color: #f7f9fc; color: #333; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .animated-fade-in { animation: fadeIn 0.5s ease-out; }
        .top-container { 
            background: linear-gradient(135deg, #e0f0ff, #f0f8ff); 
            border-radius: 18px; padding: 1rem 2rem; 
            box-shadow: 0 8px 30px rgba(0,0,0,0.1); 
            margin-bottom: 2rem; display: flex; 
            justify-content: space-between; align-items: center; 
        }
        .top-container-main { display: flex; align-items: center; }
        .titles-container { margin-left: 2rem; }
        .titles-container h1 { color: #2c3e50; margin: 0; font-size: 2.2rem; font-weight: 700; }
        .titles-container p { color: #555; margin: 0; font-size: 1.2rem; }
        .days-countdown { color: #e74c3c; font-weight: 600; font-size: 2rem; }
        .weather-info { color: #777; font-size: 1rem; margin-bottom: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)
    
    # ✅ INICIALIZAÇÃO MODIFICADA - Sempre recarrega dados frescos
    if 'last_update' not in st.session_state:
        st.session_state['last_update'] = 0
    
    # ✅ CRÍTICO: Sempre carrega dados sem cache para atualização instantânea
    df = load_data_with_row_indices()
    st.session_state['df_data'] = df
    
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_topbar_with_logo(dias_restantes)
    
    if df.empty:
        st.info("👋 Bem-vindo! Sua planilha está vazia. Adicione conteúdos na Google Sheet.")
        if st.button("🔄 Recarregar Planilha"):
            st.rerun()
        st.stop()
        
    # ✅ RECALCULA SEMPRE com dados atuais
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df_summary)

    # Interface principal
    display_progress_bar(progresso_geral)
    display_simple_metrics(stats)

    st.markdown("---")
    st.markdown("### ✅ **Marque os conteúdos estudados** (Gráficos atualizam instantaneamente!)")
    display_conteudos_com_checkboxes(df)

    st.markdown("---")
    st.markdown("### 📊 **Progresso Detalhado** (Atualização em Tempo Real)")
    st.altair_chart(create_altair_stacked_bar(df_summary), use_container_width=True)
    
    # Mostrar timestamp da última atualização
    if st.session_state.get('last_update', 0) > 0:
        update_time = datetime.fromtimestamp(st.session_state['last_update'])
        st.caption(f"🕒 Última atualização: {update_time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
