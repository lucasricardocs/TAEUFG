# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import numpy as np
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import warnings
import altair as alt
import locale

warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    pass

# --- Configurações ---
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
CONCURSO_DATE = datetime(2025, 9, 28)

ED_DATA = {
    'Disciplinas': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS'],
    'Total_Conteudos': [20, 15, 10, 15, 30],
    'Peso': [2, 1, 1, 1, 3],
    'Questões': [10, 5, 5, 10, 20]
}

def inject_common_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');
        /* Containers métricas e questões */
        .metric-container, .questao-container {
            font-family: 'Inter', sans-serif !important;
            background: var(--bg-color);
            border-radius: 16px;
            padding: 1rem 1.2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
            font-weight: 700;
            color: #2c3e50;
            height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            font-size: 16px !important;
            line-height: 1.1;
            user-select: none;
            cursor: pointer;
            transition: box-shadow 0.3s ease, transform 0.3s ease, background-color 0.3s ease;
            margin-bottom: 10px;
        }
        .metric-container:hover, .questao-container:hover {
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            transform: scale(1.05);
            background-color: #f0f8ff;
            z-index: 10;
        }
        .metric-value, .questao-numero {
            color: #355e9e;
            margin-bottom: 0.25rem;
            font-size: 18px !important;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        }
        .metric-label, .questao-label {
            font-weight: 600;
            color: #566e95;
            font-size: 16px !important;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        }
        .metric-row, .questoes-row {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 30px;
        }
        @media(max-width: 768px) {
            .metric-container, .questao-container {
                height: 130px !important;
                margin-bottom: 12px !important;
            }
            .questao-container {
                min-width: 100% !important;
                max-width: 100% !important;
            }
            .metric-row {
                flex-direction: column !important;
                height: auto !important;
            }
        }
        /* Topbar estilos */
        .topbar-container {
            display: flex;
            align-items: center;
            background-color: #f5f5f5;
            border-radius: 12px;
            padding: 0 3vw;
            min-height: 220px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25);
            margin-bottom: 20px;
            font-family: 'Inter', sans-serif;
            gap: 1.5rem;
            flex-wrap: wrap;
            justify-content: center;
            position: relative;
        }
        .topbar-logo {
            height: 140px;
            flex-shrink: 0;
            margin-right: 1.5rem;
        }
        .topbar-text {
            font-size: clamp(1.4rem, 3vw, 2.5rem);
            font-weight: 700;
            color: #2c3e50;
            line-height: 1.2;
            flex-grow: 1;
            min-width: 200px;
            display: flex;
            align-items: center;
        }
        .topbar-date {
            position: absolute;
            top: 12px;
            right: 24px;
            font-size: clamp(10px, 1vw, 12px);
            font-weight: 600;
            color: #2c3e50;
            user-select: none;
            white-space: nowrap;
        }
        @media (max-width: 768px) {
            .topbar-container {
                min-height: 160px;
                padding: 0 2vw;
                flex-direction: column;
                align-items: center;
            }
            .topbar-logo {
                height: 110px;
                margin-right: 0;
                margin-bottom: 12px;
            }
            .topbar-text {
                font-size: clamp(1.1rem, 4vw, 2rem);
                min-width: auto;
                justify-content: center;
            }
            .topbar-date {
                position: static;
                margin-top: 4px;
                font-size: clamp(8px, 1.5vw, 10px);
            }
        }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/spreadsheets.readonly'
    ]
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Credenciais do Google Cloud ('gcp_service_account') não configuradas.")
            return None
        credentials_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Erro ao autenticar no Google Sheets: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_worksheet():
    client = get_gspread_client()
    if client is None:
        return None
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        return worksheet
    except SpreadsheetNotFound:
        st.error("❌ Planilha não encontrada com o ID informado.")
    except Exception as e:
        st.error(f"❌ Erro ao acessar a aba '{WORKSHEET_NAME}': {e}")
    return None

@st.cache_data(ttl=600, show_spinner=False)
def load_data_with_row_indices():
    worksheet = get_worksheet()
    if worksheet is None:
        return pd.DataFrame()
    try:
        data = worksheet.get_all_values()
        if len(data) < 2:
            st.warning("⚠️ Planilha está vazia ou com poucos dados.")
            return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        required_cols = ['Disciplinas', 'Conteúdos', 'Status']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ Colunas obrigatórias faltando: {missing}")
            return pd.DataFrame()
        df = df[required_cols].copy()
        df['Disciplinas'] = df['Disciplinas'].str.strip().str.upper()
        df['Conteúdos'] = df['Conteúdos'].str.strip()
        df['Status'] = df['Status'].str.strip().str.lower()
        df = df[df['Status'].isin(['true', 'false'])].copy()
        df['Status'] = df['Status'].str.title()
        df.reset_index(inplace=True)
        df['sheet_row'] = df['index'] + 2
        df.drop('index', axis=1, inplace=True)
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Falha ao carregar dados: {e}")
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
        st.error(f"❌ Erro inesperado ao atualizar a planilha: {e}")
        return False

def calculate_progress(df):
    df_edital = pd.DataFrame(ED_DATA)
    if df.empty:
        df_edital['Conteudos_Concluidos'] = 0
        df_edital['Conteudos_Pendentes'] = df_edital['Total_Conteudos']
        df_edital['Progresso_Ponderado'] = 0.0
        return df_edital, 0.0
    df['Concluido'] = (df['Status'] == 'True').astype(int)
    resumo = df.groupby('Disciplinas', observed=True)['Concluido'].sum().reset_index(name='Conteudos_Concluidos')
    df_merged = pd.merge(df_edital, resumo, how='left', on='Disciplinas').fillna(0)
    df_merged['Conteudos_Pendentes'] = df_merged['Total_Conteudos'] - df_merged['Conteudos_Concluidos']
    df_merged['Ponto_por_Conteudo'] = df_merged.apply(
        lambda row: row['Peso'] / row['Total_Conteudos'] if row['Total_Conteudos'] > 0 else 0, axis=1)
    df_merged['Pontos_Concluidos'] = df_merged['Conteudos_Concluidos'] * df_merged['Ponto_por_Conteudo']
    df_merged['Progresso_Ponderado'] = np.where(
        df_merged['Peso'] > 0,
        (df_merged['Pontos_Concluidos'] / df_merged['Peso']) * 100,
        0
    ).round(1)
    total_peso = df_merged['Peso'].sum()
    total_pontos = df_merged['Pontos_Concluidos'].sum()
    progresso_total = (total_pontos / total_peso * 100) if total_peso > 0 else 0
    return df_merged, round(progresso_total, 1)

def calculate_stats(df, df_summary):
    now = datetime.now()
    dias_restantes = max((CONCURSO_DATE - now).days, 0)
    total_conteudos = df_summary['Total_Conteudos'].sum() if not df_summary.empty else 0
    concluidos = df_summary['Conteudos_Concluidos'].sum() if not df_summary.empty else 0
    pendentes = df_summary['Conteudos_Pendentes'].sum() if not df_summary.empty else 0
    percentual_geral = round((concluidos / total_conteudos) * 100, 1) if total_conteudos > 0 else 0
    topicos_por_dia = round(pendentes / dias_restantes, 1) if dias_restantes > 0 else 0
    if not df_summary.empty:
        df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
        maior_prioridade = df_summary.loc[df_summary['Prioridade_Score'].idxmax()]['Disciplinas']
    else:
        maior_prioridade = ""
    return {
        'dias_restantes': dias_restantes,
        'total_conteudos': total_conteudos,
        'concluidos': int(concluidos),
        'pendentes': int(pendentes),
        'percentual_geral': percentual_geral,
        'topicos_por_dia': topicos_por_dia,
        'maior_prioridade': maior_prioridade
    }

def titulo_com_destaque(texto, cor_lateral="#3498db"):
    st.markdown(f'''
    <div style="
        display: flex;
        align-items: center;
        border-left: 6px solid {cor_lateral};
        padding-left: 16px;
        background-color: #f5f5f5;
        padding-top: 12px;
        padding-bottom: 12px;
        border-radius: 12px;
        box-shadow: 0 4px 10px #a3bffa88;
        margin-bottom: 40px;
        font-weight: 700;
        font-size: 1.6rem;
        color: #2c3e50;
    ">
        {texto}
    </div>
    ''', unsafe_allow_html=True)

def render_topbar_with_logo(dias_restantes):
    hoje_texto = datetime.now().strftime('%d de %B de %Y')
    st.markdown(f"""
    <div style="
        position: relative;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        height: 250px;
        background-color: #f5f5f5;
        padding: 0 40px;
        border-radius: 12px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        margin-bottom: 20px;
        font-family: 'Inter', sans-serif;
    ">
        <img src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG"
             style="height: 150px; margin-right: 40px;">
        <div style="
            font-size: 3rem;
            font-weight: 700;
            color: #2c3e50;
            white-space: nowrap;
            line-height: 1.2;
        ">
            ⏰ Faltam {dias_restantes} dias para o concurso de TAE
        </div>
        <div style="
            position: absolute;
            top: 8px;
            right: 16px;
            font-size: 15px;
            font-weight: 600;
            color: #2c3e50;
            user-select: none;
        ">
            Goiânia, {hoje_texto}
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Gráfico 1: Questões horizontais ---
def chart_questoes_horizontal(df_ed: pd.DataFrame, height=400):
    chart = alt.Chart(df_ed).mark_bar(stroke='#d3d3d3', strokeWidth=3, cornerRadius=5).encode(
        y=alt.Y('Disciplinas:N', sort='-x', title=None),
        x=alt.X('Questões:Q', title='Quantidade de Questões'),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=[alt.Tooltip('Disciplinas'), alt.Tooltip('Questões', title='Quantidade')]
    ).properties(
        height=height,
        width='container'
    )

    text = alt.Chart(df_ed).mark_text(
        align='left',
        baseline='middle',
        dx=3,
        fontWeight='bold',
        fontSize=12,
        color='black'
    ).encode(
        y=alt.Y('Disciplinas:N', sort='-x'),
        x='Questões:Q',
        text='Questões:Q'
    )

    return (chart + text).configure_view(stroke=None)

# --- Gráfico 2: Peso percentual horizontais ---
def chart_peso_ponderado_percentual(df_ed: pd.DataFrame, height=400):
    df_ed = df_ed.copy()
    df_ed['Valor'] = df_ed['Peso'] * df_ed['Questões']
    total = df_ed['Valor'].sum()
    df_ed['Percentual'] = df_ed['Valor'] / total

    chart = alt.Chart(df_ed).mark_bar(stroke='#d3d3d3', strokeWidth=3, cornerRadius=5).encode(
        y=alt.Y('Disciplinas:N', sort='-x', title=None),
        x=alt.X('Percentual:Q', title='Peso ponderado (%)', axis=alt.Axis(format='%')),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=[alt.Tooltip('Disciplinas'), alt.Tooltip('Percentual', title='Percentual', format='.1%')]
    ).properties(
        height=height,
        width='container'
    )

    text = alt.Chart(df_ed).mark_text(
        align='left',
        baseline='middle',
        dx=3,
        fontWeight='bold',
        fontSize=12,
        color='black'
    ).encode(
        y=alt.Y('Disciplinas:N', sort='-x'),
        x='Percentual:Q',
        text=alt.Text('Percentual:Q', format='.1%')
    )

    return (chart + text).configure_view(stroke=None)

def display_conteudos_com_checkboxes(df):
    worksheet = get_worksheet()
    if df.empty or worksheet is None:
        st.info("Nenhum dado disponível para exibir conteúdos.")
        return
    titulo_com_destaque("📚 Conteúdos por Disciplina", cor_lateral="#8e44ad")
    disciplinas_ordenadas = sorted(df['Disciplinas'].unique())
    alterou = False
    for disc in disciplinas_ordenadas:
        conteudos_disciplina = df[df['Disciplinas'] == disc]
        with st.expander(f"{disc} ({len(conteudos_disciplina)} conteúdos)"):
            for _, row in conteudos_disciplina.iterrows():
                key = f"{row['Disciplinas']}_{row['Conteúdos']}_{row['sheet_row']}".replace(" ", "_").replace(".", "_")
                checked = (row['Status'] == 'True')
                novo_status = st.checkbox(label=row['Conteúdos'], value=checked, key=key)
                if novo_status != checked:
                    sucesso = update_status_in_sheet(worksheet, row['sheet_row'], "True" if novo_status else "False")
                    if sucesso:
                        st.success(f"Status do conteúdo '{row['Conteúdos']}' atualizado com sucesso!")
                        alterou = True
                    else:
                        st.error(f"Falha ao atualizar status do conteúdo '{row['Conteúdos']}'.")
    if alterou:
        load_data_with_row_indices.clear()
        st.experimental_rerun()

def rodape_motivacional():
    st.markdown("""
    <footer style='font-size: 11px; color: #064820; font-weight: 600; margin-top: 12px; text-align: center; user-select: none; font-family: Inter, sans-serif;'>
        🚀 Feito com muito amor, coragem e motivação para você! ✨
    </footer>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso 2025", page_icon="📚", layout="wide")

    inject_common_css()

    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_topbar_with_logo(dias_restantes)

    df = load_data_with_row_indices()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)

    display_containers_metricas(stats, progresso_geral)

    st.markdown("---")

    titulo_com_destaque("📊 Progresso por Disciplina", cor_lateral="#3498db")
    # Use sua função de progresso com donuts aqui (não mostrada para brevidade; mantenha a sua implementada)

    st.markdown("---")

    titulo_com_destaque("📈 Percentual de Conteúdos Concluídos e Pendentes por Disciplina", cor_lateral="#2980b9")
    # Use sua função de histograma empilhado aqui (não mostrada para brevidade; mantenha a sua implementada)

    st.markdown("---")

    display_conteudos_com_checkboxes(df)

    st.markdown("---")

    titulo_com_destaque("📊 Número de Questões por Disciplina", cor_lateral="#8e44ad")
    df_ed = pd.DataFrame(ED_DATA)
    chart_q = chart_questoes_horizontal(df_ed)
    st.altair_chart(chart_q, use_container_width=True)

    st.markdown("---")

    titulo_com_destaque("📊 Peso ponderado por Disciplina (%)", cor_lateral="#8e44ad")
    chart_p = chart_peso_ponderado_percentual(df_ed)
    st.altair_chart(chart_p, use_container_width=True)

    st.markdown("---")

    rodape_motivacional()

if __name__ == "__main__":
    main()
