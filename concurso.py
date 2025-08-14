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

ED_DATA = {
    'Disciplinas': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS'],
    'Total_Conteudos': [17, 14, 14, 11, 21],
    'Peso': [2, 1, 1, 1, 3],
    'Questões': [10, 5, 5, 10, 20]
}

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

# --- Funções de Interface e Visualização ---

def titulo_com_destaque(texto, cor_lateral="#8e44ad"):
    st.markdown(f"""
    <div style="border-left: 5px solid {cor_lateral}; 
                padding: 0.75rem 1.5rem; 
                background: linear-gradient(to right, #f8f9fa, #ffffff);
                border-radius: 8px; 
                margin: 2rem 0 1.5rem 0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h2 style="color: #2c3e50; 
                   margin-block-start: 0; 
                   margin-block-end: 0;
                   font-weight: 600;">
            {texto}
        </h2>
    </div>""", unsafe_allow_html=True)

def render_topbar_with_logo(dias_restantes):
    st.markdown(f"""
    <div style="display: flex; 
                align-items: center; 
                justify-content: space-between; 
                background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
                border-radius: 12px; 
                padding: 1.5rem 2.5rem; 
                box-shadow: 0 6px 18px rgba(0,0,0,0.15); 
                margin-bottom: 2rem;
                color: white;">
        <div style="display: flex; align-items: center;">
            <div style="background-color: white; 
                        border-radius: 50%; 
                        padding: 8px;
                        margin-right: 1.5rem;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                <svg xmlns="http://www.w3.org/2000/svg" width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#6a11cb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                </svg>
            </div>
            <div>
                <h1 style="color: white; margin: 0; font-size: 1.9rem; font-weight: 700;">Dashboard de Estudos</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 1.05rem;">Concurso TAE UFG 2025</p>
            </div>
        </div>
        <div style="text-align: right; 
                    background: rgba(255,255,255,0.15); 
                    padding: 0.8rem 1.5rem;
                    border-radius: 10px;
                    backdrop-filter: blur(4px);">
            <p style="color: white; font-weight: bold; font-size: 1.7rem; margin: 0;">
                ⏰ Faltam {dias_restantes} dias!
            </p>
            <p style="margin:0; font-weight: 500; color: rgba(255,255,255,0.85); font-size: 0.95rem;">
                {datetime.now().strftime('%d de %B de %Y').title()}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_containers_metricas(stats, progresso_geral):
    cols = st.columns(5)
    metric_style = """
        padding: 1.2rem 0.5rem; 
        border-radius: 12px; 
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    """
    
    with cols[0]:
        st.markdown(f"<div style='{metric_style} background: linear-gradient(135deg, #3498db 0%, #1abc9c 100%); color: white;'>"
                    f"<h3 style='color:white; margin:0; font-size:1.1rem;'>🎯 Progresso</h3>"
                    f"<p style='font-size:1.8rem; margin:0; font-weight:700;'>{progresso_geral:.1f}%</p></div>", 
                    unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown(f"<div style='{metric_style} background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); color: white;'>"
                    f"<h3 style='color:white; margin:0; font-size:1.1rem;'>✅ Concluídos</h3>"
                    f"<p style='font-size:1.8rem; margin:0; font-weight:700;'>{stats['concluidos']}</p></div>", 
                    unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown(f"<div style='{metric_style} background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white;'>"
                    f"<h3 style='color:white; margin:0; font-size:1.1rem;'>⏳ Pendentes</h3>"
                    f"<p style='font-size:1.8rem; margin:0; font-weight:700;'>{stats['pendentes']}</p></div>", 
                    unsafe_allow_html=True)
    
    with cols[3]:
        st.markdown(f"<div style='{metric_style} background: linear-gradient(135deg, #f39c12 0%, #d35400 100%); color: white;'>"
                    f"<h3 style='color:white; margin:0; font-size:1.1rem;'>🏃 Ritmo</h3>"
                    f"<p style='font-size:1.8rem; margin:0; font-weight:700;'>{stats['topicos_por_dia']}/dia</p></div>", 
                    unsafe_allow_html=True)
    
    with cols[4]:
        st.markdown(f"<div style='{metric_style} background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); color: white;'>"
                    f"<h3 style='color:white; margin:0; font-size:1.1rem;'>⭐ Prioridade</h3>"
                    f"<p style='font-size:1.4rem; margin:0; font-weight:700; padding:0.2rem 0;'>{stats['maior_prioridade'].title()}</p></div>", 
                    unsafe_allow_html=True)

def create_altair_stacked_bar(df_summary):
    df_melted = df_summary.melt(id_vars=['Disciplinas'], 
                                value_vars=['Conteudos_Concluidos', 'Conteudos_Pendentes'], 
                                var_name='Status', 
                                value_name='Contagem')
    df_melted['Status'] = df_melted['Status'].map({
        'Conteudos_Concluidos': 'Concluído', 
        'Conteudos_Pendentes': 'Pendente'
    })

    return alt.Chart(df_melted).mark_bar().encode(
        y=alt.Y('Disciplinas:N', sort=None, title=None, axis=alt.Axis(labelColor='black')),
        x=alt.X('sum(Contagem):Q', stack='normalize', 
                axis=alt.Axis(format='%', title='Percentual', labelColor='black', titleColor='black')),
        color=alt.Color('Status:N', 
                       scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c']), 
                       legend=alt.Legend(title=None, labelColor='black')),
        tooltip=[alt.Tooltip('Disciplinas:N'), 
                 alt.Tooltip('Status:N'), 
                 alt.Tooltip('sum(Contagem):Q', title='Nº de Conteúdos')]
    ).properties(height=350, title=alt.TitleParams(
        text="Percentual de Conclusão por Disciplina", 
        anchor='middle', 
        fontSize=18,
        color='black'
    ))

def create_progress_donut(source_df, title):
    total = source_df['Valor'].sum()
    concluido_val = source_df[source_df['Status'] == 'Concluído']['Valor'].iloc[0]
    percent_text = f"{(concluido_val / total * 100) if total > 0 else 0:.1f}%"
    
    base = alt.Chart(source_df).mark_arc(innerRadius=55, cornerRadius=5).encode(
        theta=alt.Theta("Valor:Q"),
        color=alt.Color("Status:N", 
                       scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c']), 
                       legend=None),
        tooltip=['Status', alt.Tooltip('Valor', title="Conteúdos")]
    )
    text = alt.Chart(pd.DataFrame({'text': [percent_text]})).mark_text(
        size=24, 
        fontWeight='bold',
        color='black'
    ).encode(text='text:N')
    
    return (base + text).properties(
        title=alt.TitleParams(
            text=title, 
            anchor='middle', 
            fontSize=16, 
            dy=-10,
            color='black'
        )
    )

def display_donuts_grid(df_summary, progresso_geral):
    charts_data = []
    prog_geral_df = pd.DataFrame([
        {'Status': 'Concluído', 'Valor': progresso_geral},
        {'Status': 'Pendente', 'Valor': 100 - progresso_geral}
    ])
    charts_data.append({'df': prog_geral_df, 'title': 'Progresso Geral'})

    for _, row in df_summary.iterrows():
        df = pd.DataFrame([
            {'Status': 'Concluído', 'Valor': row['Conteudos_Concluidos']},
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

def handle_checkbox_change(worksheet, row_number, key, conteudo_nome):
    novo_status = st.session_state[key]
    if update_status_in_sheet(worksheet, row_number, "TRUE" if novo_status else "FALSE"):
        st.toast(f"✅ Status de '{conteudo_nome}' atualizado!", icon="✅")
        load_data_with_row_indices.clear()
    else:
        st.toast(f"❌ Falha ao atualizar '{conteudo_nome}'.", icon="❌")
        st.session_state[key] = not novo_status

def display_conteudos_com_checkboxes(df):
    worksheet = get_worksheet()
    if not worksheet: return

    for disc in sorted(df['Disciplinas'].unique()):
        conteudos_disciplina = df[df['Disciplinas'] == disc]
        
        # Calcula progresso da disciplina
        concluidos = conteudos_disciplina['Status'].sum()
        total = len(conteudos_disciplina)
        progresso = (concluidos / total) * 100 if total > 0 else 0
        
        with st.expander(f"📚 {disc.title()} - {concluidos}/{total} ({progresso:.1f}%)", expanded=False):
            for _, row in conteudos_disciplina.iterrows():
                key = f"cb_{row['sheet_row']}"
                status_emoji = "✅" if row['Status'] else "⏳"
                st.checkbox(
                    label=f"{status_emoji} {row['Conteúdos']}", 
                    value=bool(row['Status']), 
                    key=key,
                    on_change=handle_checkbox_change,
                    kwargs={
                        'worksheet': worksheet, 
                        'row_number': row['sheet_row'], 
                        'key': key, 
                        'conteudo_nome': row['Conteúdos']
                    }
                )

def create_questoes_bar_chart(ed_data):
    df = pd.DataFrame(ed_data)
    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X('Disciplinas:N', sort=None, title=None, axis=alt.Axis(labelColor='black')),
        y=alt.Y('Questões:Q', title='Número de Questões', axis=alt.Axis(labelColor='black', titleColor='black')),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=['Disciplinas', 'Questões']
    )
    text = chart.mark_text(
        align='center', 
        baseline='bottom', 
        dy=-5, 
        color='black',
        fontWeight='bold',
        fontSize=14
    ).encode(text='Questões:Q')
    
    return (chart + text).properties(
        height=350, 
        title=alt.TitleParams(
            "Distribuição de Questões", 
            anchor='middle', 
            fontSize=18,
            color='black'
        )
    )

def create_relevancia_pie_chart(ed_data):
    df = pd.DataFrame(ed_data)
    df['Relevancia'] = df['Peso'] * df['Questões']
    
    return alt.Chart(df).mark_arc(innerRadius=70, cornerRadius=5).encode(
        theta=alt.Theta("Relevancia:Q"),
        color=alt.Color(
            "Disciplinas:N", 
            legend=alt.Legend(
                title="Disciplinas", 
                orient="top", 
                titleFontSize=14, 
                labelFontSize=12,
                labelColor='black',
                titleColor='black'
            )
        ),
        tooltip=['Disciplinas', 'Peso', 'Questões', 'Relevancia']
    ).properties(
        height=350, 
        title=alt.TitleParams(
            "Relevância (Peso × Questões)", 
            anchor='middle', 
            fontSize=18,
            color='black'
        )
    )

def rodape_motivacional():
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; padding: 1.5rem; 
                background: linear-gradient(to right, #f8f9fa, #e9ecef);
                border-radius: 12px;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.05);">
        <p style='font-size: 1.1rem; color: #555; margin: 0; font-weight: 500;'>
            🚀 Cada tópico estudado é um passo mais perto da sua aprovação! Mantenha o foco! ✨
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
    
    # CSS customizado
    st.markdown("""
    <style>
        /* Estilos gerais */
        .stApp {
            background-color: #f8f9fa;
        }
        .stExpander {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
            border: none !important;
        }
        .stCheckbox > label {
            font-size: 1.05rem;
            padding: 0.8rem 0;
            border-bottom: 1px solid #eee;
        }
        .stCheckbox > label:last-child {
            border-bottom: none !important;
        }
        .st-b7 {
            color: #333 !important;
        }
        
        /* Melhorias no cabeçalho dos expanders */
        .st-emotion-cache-1q7spjk {
            font-size: 1.15rem !important;
            font-weight: 600 !important;
        }
        
        /* Remove espaçamento desnecessário */
        .block-container {
            padding-top: 1.5rem;
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

    display_containers_metricas(stats, progresso_geral)

    titulo_com_destaque("📊 Progresso Detalhado por Disciplina", cor_lateral="#3498db")
    st.altair_chart(create_altair_stacked_bar(df_summary), use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    titulo_com_destaque("📈 Visão Geral do Progresso", cor_lateral="#2ecc71")
    display_donuts_grid(df_summary, progresso_geral)
    
    titulo_com_destaque("📝 Análise Estratégica da Prova", cor_lateral="#e67e22")
    colA, colB = st.columns(2, gap="large")
    with colA:
        st.altair_chart(create_questoes_bar_chart(ED_DATA), use_container_width=True)
    with colB:
        st.altair_chart(create_relevancia_pie_chart(ED_DATA), use_container_width=True)

    titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#9b59b6")
    display_conteudos_com_checkboxes(df)

    rodape_motivacional()

if __name__ == "__main__":
    main()
