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

# Ignora avisos futuros do pandas que não são relevantes aqui
warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

# Configura a localidade para português do Brasil para exibir as datas corretamente
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

# --- Funções de Conexão com Google Sheets (com cache) ---

@st.cache_resource(show_spinner="Conectando ao Google Sheets...")
def get_gspread_client():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/spreadsheets.readonly']
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
    """
    Função corrigida para encontrar o índice da coluna e atualizar a célula.
    """
    try:
        # Retornando ao método original e confiável para encontrar a coluna
        header = sheet.row_values(1)
        if 'Status' not in header:
            st.error("❌ Coluna 'Status' não encontrada na planilha.")
            return False
        
        # .index() é 0-based, colunas do gspread são 1-based, por isso +1
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
    # Usando o fuso horário correto para garantir que o dia seja calculado corretamente
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
        'dias_restantes': dias_restantes, 'concluidos': int(concluidos),
        'pendentes': int(pendentes), 'topicos_por_dia': topicos_por_dia,
        'maior_prioridade': maior_prioridade
    }

# --- Funções de Interface e Visualização ---

def titulo_com_destaque(texto, cor_lateral="#8e44ad"):
    st.markdown(f"""
    <div style="border-left: 5px solid {cor_lateral}; padding: 0.5rem 1rem; background-color: #F0F2F6; border-radius: 8px; margin: 2rem 0 1.5rem 0;">
        <h2 style="color: #2c3e50; margin-block-start: 0; margin-block-end: 0;">{texto}</h2>
    </div>""", unsafe_allow_html=True)

def render_topbar_with_logo(dias_restantes):
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; background-color: #ffffff; border-radius: 12px; padding: 1rem 2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 2rem;">
        <div style="display: flex; align-items: center;">
            <img src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG" style="height: 70px; margin-right: 1.5rem;"/>
            <div>
                <h1 style="color: #2c3e50; margin: 0; font-size: 1.8rem; font-weight: 700;">Dashboard de Estudos</h1>
                <p style="color: #555; margin: 0;">Concurso TAE UFG 2025</p>
            </div>
        </div>
        <div style="text-align: right;">
            <p style="color: #e74c3c; font-weight: bold; font-size: 1.5rem; margin: 0;">⏰ Faltam {dias_restantes} dias!</p>
            <p style="margin:0; font-weight: 500; color: #555; font-size: 0.9rem;">{datetime.now().strftime('%d de %B de %Y')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_containers_metricas(stats, progresso_geral):
    cols = st.columns(5)
    cols[0].metric("🎯 Progresso Ponderado", f"{progresso_geral:.1f}%")
    cols[1].metric("✅ Concluídos", f"{stats['concluidos']}")
    cols[2].metric("⏳ Pendentes", f"{stats['pendentes']}")
    cols[3].metric("🏃 Ritmo Necessário", f"{stats['topicos_por_dia']} tópicos/dia")
    cols[4].metric("⭐ Foco Principal", stats['maior_prioridade'].title())

def create_altair_stacked_bar(df_summary):
    df_melted = df_summary.melt(id_vars=['Disciplinas'], value_vars=['Conteudos_Concluidos', 'Conteudos_Pendentes'], var_name='Status', value_name='Contagem')
    df_melted['Status'] = df_melted['Status'].map({'Conteudos_Concluidos': 'Concluído', 'Conteudos_Pendentes': 'Pendente'})

    return alt.Chart(df_melted).mark_bar().encode(
        y=alt.Y('Disciplinas:N', sort=None, title=None),
        x=alt.X('sum(Contagem):Q', stack='normalize', axis=alt.Axis(format='%', title='Percentual')),
        color=alt.Color('Status:N', scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c']), legend=alt.Legend(title=None)),
        tooltip=[alt.Tooltip('Disciplinas:N'), alt.Tooltip('Status:N'), alt.Tooltip('sum(Contagem):Q', title='Nº de Conteúdos')]
    ).properties(height=350, title=alt.TitleParams(text="Percentual de Conclusão por Disciplina", anchor='middle', fontSize=18))

def create_progress_donut(source_df, title):
    # Calcula o percentual para exibir no centro
    total = source_df['Valor'].sum()
    concluido_val = source_df[source_df['Status'] == 'Concluído']['Valor'].iloc[0]
    percent_text = f"{(concluido_val / total * 100) if total > 0 else 0:.1f}%"
    
    base = alt.Chart(source_df).mark_arc(innerRadius=55, cornerRadius=5).encode(
        theta=alt.Theta("Valor:Q"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c']), legend=None),
        tooltip=['Status', alt.Tooltip('Valor', title="Conteúdos")]
    )
    text = alt.Chart(pd.DataFrame({'text': [percent_text]})).mark_text(size=24, fontWeight='bold').encode(text='text:N')
    return (base + text).properties(title=alt.TitleParams(text=title, anchor='middle', fontSize=16, dy=-10))

def display_donuts_grid(df_summary, progresso_geral):
    charts_data = []
    # Primeiro, o progresso geral
    prog_geral_df = pd.DataFrame([
        {'Status': 'Concluído', 'Valor': progresso_geral},
        {'Status': 'Pendente', 'Valor': 100 - progresso_geral}
    ])
    charts_data.append({'df': prog_geral_df, 'title': 'Progresso Geral'})

    # Depois, cada disciplina
    for _, row in df_summary.iterrows():
        df = pd.DataFrame([
            {'Status': 'Concluído', 'Valor': row['Conteudos_Concluidos']},
            {'Status': 'Pendente', 'Valor': row['Conteudos_Pendentes']}
        ])
        charts_data.append({'df': df, 'title': row['Disciplinas'].title()})

    # Cria o grid 2x3
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
        with st.expander(f"{disc.title()} ({len(conteudos_disciplina)} conteúdos)"):
            for _, row in conteudos_disciplina.iterrows():
                key = f"cb_{row['sheet_row']}"
                st.checkbox(
                    label=row['Conteúdos'], value=bool(row['Status']), key=key,
                    on_change=handle_checkbox_change,
                    kwargs={'worksheet': worksheet, 'row_number': row['sheet_row'], 'key': key, 'conteudo_nome': row['Conteúdos']}
                )

def create_questoes_bar_chart(ed_data):
    df = pd.DataFrame(ed_data)
    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X('Disciplinas:N', sort=None, title=None),
        y=alt.Y('Questões:Q', title='Número de Questões'),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=['Disciplinas', 'Questões']
    )
    text = chart.mark_text(align='center', baseline='bottom', dy=-5, color='black').encode(text='Questões:Q')
    return (chart + text).properties(height=350, title=alt.TitleParams("Distribuição de Questões", anchor='middle', fontSize=18))

def create_relevancia_pie_chart(ed_data):
    df = pd.DataFrame(ed_data)
    df['Relevancia'] = df['Peso'] * df['Questões']
    return alt.Chart(df).mark_arc(innerRadius=70, cornerRadius=5).encode(
        theta=alt.Theta("Relevancia:Q"),
        color=alt.Color("Disciplinas:N", legend=alt.Legend(title="Disciplinas", orient="top", titleFontSize=14, labelFontSize=12)),
        tooltip=['Disciplinas', 'Peso', 'Questões', 'Relevancia']
    ).properties(height=350, title=alt.TitleParams("Relevância (Peso × Questões)", anchor='middle', fontSize=18))

def rodape_motivacional():
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 14px; color: #555;'>🚀 Feito com Streamlit para impulsionar seus estudos. Foco na aprovação! ✨</p>", unsafe_allow_html=True)

# --- Função Principal da Aplicação ---
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso TAE", page_icon="📚", layout="wide")

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
    
    # Gráfico de barras ocupando a largura total
    st.altair_chart(create_altair_stacked_bar(df_summary), use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Grid 2x3 de gráficos donut
    display_donuts_grid(df_summary, progresso_geral)
    
    titulo_com_destaque("📝 Análise Estratégica da Prova", cor_lateral="#e67e22")
    colA, colB = st.columns(2, gap="large")
    with colA:
        st.altair_chart(create_questoes_bar_chart(ED_DATA), use_container_width=True)
    with colB:
        st.altair_chart(create_relevancia_pie_chart(ED_DATA), use_container_width=True)

    titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#8e44ad")
    display_conteudos_com_checkboxes(df)

    rodape_motivacional()

if __name__ == "__main__":
    main()
