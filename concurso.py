# -*- coding: utf-8 -*-
import streamlit as st
import gspread
import pandas as pd
import numpy as np
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import altair as alt

warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

# --- Configurações e Constantes ---
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
CONCURSO_DATE = datetime(2025, 9, 28)

ED_DATA = {
    'Disciplinas': [
        'LÍNGUA PORTUGUESA',
        'RLM',
        'INFORMÁTICA',
        'LEGISLAÇÃO',
        'CONHECIMENTOS ESPECÍFICOS - ASSISTENTE EM ADMINISTRAÇÃO'
    ],
    'Total_Conteudos': [20, 15, 10, 15, 30],
    'Peso': [2, 1, 1, 1, 3]
}

# --- Conexão e Leitura da Planilha ---
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/spreadsheets.readonly'
    ]
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Credenciais do Google Cloud ('gcp_service_account') não configuradas. Configure em secrets.")
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
def load_data():
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
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Falha ao carregar dados: {e}")
        return pd.DataFrame()

# --- Processamento de Métricas ---
def calculate_progress(df):
    df_edital = pd.DataFrame(ED_DATA)
    if df.empty:
        df_edital['Conteudos_Concluidos'] = 0
        df_edital['Conteudos_Pendentes'] = df_edital['Total_Conteudos']
        df_edital['Progresso_Ponderado'] = 0.0
        return df_edital, 0.0

    df['Concluido'] = (df['Status'] == 'True').astype(int)
    resumo = df.groupby('Disciplinas', observed=False)['Concluido'].sum().reset_index(name='Conteudos_Concluidos')

    df_merged = pd.merge(df_edital, resumo, left_on='Disciplinas', right_on='Disciplinas', how='left').fillna(0)
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
    progresso_total = round(progresso_total, 1)

    return df_merged, progresso_total

def calculate_stats(df, df_summary):
    now = datetime.now()
    dias_restantes = max((CONCURSO_DATE - now).days, 0)
    total_conteudos = df_summary['Total_Conteudos'].sum()
    concluidos = df_summary['Conteudos_Concluidos'].sum()
    pendentes = df_summary['Conteudos_Pendentes'].sum()
    percentual_geral = round((concluidos / total_conteudos) * 100, 1) if total_conteudos > 0 else 0
    topicos_por_dia = round(pendentes / dias_restantes, 1) if dias_restantes > 0 else 0

    maior_prog = df_summary.loc[df_summary['Progresso_Ponderado'].idxmax()]['Disciplinas'] if not df_summary.empty else ""
    menor_prog = df_summary.loc[df_summary['Progresso_Ponderado'].idxmin()]['Disciplinas'] if not df_summary.empty else ""

    df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
    maior_prioridade = df_summary.loc[df_summary['Prioridade_Score'].idxmax()]['Disciplinas'] if not df_summary.empty else ""

    return {
        'dias_restantes': dias_restantes,
        'total_conteudos': total_conteudos,
        'concluidos': int(concluidos),
        'pendentes': int(pendentes),
        'percentual_geral': percentual_geral,
        'topicos_por_dia': topicos_por_dia,
        'maior_progresso': maior_prog,
        'menor_progresso': menor_prog,
        'maior_prioridade': maior_prioridade
    }

# --- Gráficos e Visualização ---

def create_altair_donut(row):
    concluido = int(row['Conteudos_Concluidos'])
    pendente = int(row['Conteudos_Pendentes'])
    total = concluido + pendente
    if total == 0:
        pendente = 1
        total = 1

    # Compute percentage labels
    concluido_pct = round((concluido / total) * 100, 1)
    pendente_pct = round((pendente / total) * 100, 1)

    source = pd.DataFrame({
        'Status': ['Concluído', 'Pendente'],
        'Valor': [concluido, pendente],
        'Percentual': [concluido_pct, pendente_pct]
    })
    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])
    base_chart = alt.Chart(source).encode(
        theta=alt.Theta(field='Valor', type='quantitative'),
        color=alt.Color('Status:N', scale=color_scale, legend=None),
        tooltip=[alt.Tooltip('Status'), alt.Tooltip('Valor', format="d"), alt.Tooltip('Percentual', format='.1f')]
    )
    donut = base_chart.mark_arc(innerRadius=70, stroke='#fff', strokeWidth=2)
    text = base_chart.mark_text(radius=110, size=16, fontWeight='bold', color='black').encode(
        text=alt.Text('Percentual:Q', format='.1f')
    )
    chart = (donut + text).properties(
        title=alt.TitleParams(
            text=str(row['Disciplinas']),
            subtitle=f"{row['Progresso_Ponderado']:.1f}% Progresso Ponderado",
            anchor='middle',
            fontSize=20,
            fontWeight='bold',
            color='#2c3e50',
            subtitleColor='#576574'
        ),
        width=350,
        height=350
    ).configure_view(strokeWidth=0)
    return chart

def create_stacked_bar(df):
    if df.empty:
        st.info("Sem dados para gráfico de barras empilhadas.")
        return

    # Agregar dados por disciplina e status
    df_group = df.groupby(['Disciplinas', 'Status']).size().reset_index(name='Qtd')
    # Pivot para formato apropriado para stacked bar
    df_pivot = df_group.pivot(index='Disciplinas', columns='Status', values='Qtd').fillna(0)
    df_pivot['Total'] = df_pivot.sum(axis=1)
    df_pivot['Pct_True'] = df_pivot.get('True', 0) / df_pivot['Total']
    df_pivot = df_pivot.sort_values('Pct_True', ascending=False).reset_index()

    # Preparar dados para Altair stacked bar
    df_melt = df_pivot.melt(id_vars=['Disciplinas', 'Pct_True'], value_vars=['True', 'False'], var_name='Status', value_name='Qtd')

    color_scale = alt.Scale(domain=['True', 'False'], range=['#2ecc71', '#e74c3c'])

    chart = (
        alt.Chart(df_melt)
        .mark_bar()
        .encode(
            x=alt.X('Disciplinas:N', sort=df_pivot['Disciplinas'].tolist(), title='Disciplina'),
            y=alt.Y('Qtd:Q', title='Quantidade de Conteúdos'),
            color=alt.Color('Status:N', scale=color_scale, legend=alt.Legend(title="Status")),
            tooltip=['Disciplinas', 'Status', 'Qtd']
        )
        .properties(title='Conteúdos Concluídos (True) e Pendentes (False) por Disciplina', width=800, height=400)
    )
    st.altair_chart(chart, use_container_width=True)

# --- CSS para tema bonito ---
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    body, html, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background: #f4f6fb;
        color: #222831;
    }

    h1, h2, h3 {
        color: #304FFE;
    }

    .days-remaining-box {
        background: linear-gradient(135deg, #6574FF, #304FFE);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        color: white;
        font-weight: 700;
        font-size: 2.5rem;
        box-shadow: 0 6px 20px rgba(48, 79, 254, 0.4);
        margin-bottom: 2rem;
    }

    .study-tips-box {
        background: #FFFFFF;
        border: 3px solid #6574FF;
        border-radius: 16px;
        padding: 1.5rem 2rem;
        color: #2E3A59;
        box-shadow: 0 4px 15px rgba(101, 116, 255, 0.25);
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    .study-tips-box ul {
        padding-left: 1.2rem;
        margin: 0;
    }

    .metric-container {
        background: white;
        border-radius: 12px;
        padding: 1.3rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 10px rgba(48, 79, 254, 0.15);
        text-align: center;
    }

    .metric-value {
        font-size: 2.8rem;
        font-weight: 700;
        color: #304FFE;
        margin-bottom: 0.2rem;
    }

    .metric-label {
        font-weight: 600;
        color: #6B7280;
        font-size: 1.1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Função Principal ---
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso 2025", page_icon="📚", layout="wide")
    inject_css()

    # Calcular dias restantes
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)

    # Cabeçalho
    st.markdown(f'<div class="days-remaining-box">⏰ Faltam {dias_restantes} dias para o Concurso 2025</div>', unsafe_allow_html=True)

    # Carregar dados e cálculos
    df = load_data()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)

    # Métricas principais
    cols = st.columns(5)
    with cols[0]:
        st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{progresso_geral:.1f}%</div>
                <div class="metric-label">Progresso Geral</div>
            </div>''', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{stats['concluidos']}</div>
                <div class="metric-label">Conteúdos Concluídos</div>
            </div>''', unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{stats['pendentes']}</div>
                <div class="metric-label">Conteúdos Pendentes</div>
            </div>''', unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f'''
            <div class="metric-container">
                <div class="metric-value">{stats['topicos_por_dia']}</div>
                <div class="metric-label">Tópicos/Dia Necessários</div>
            </div>''', unsafe_allow_html=True)
    with cols[4]:
        st.markdown(f'''
            <div class="metric-container" style="font-size:1rem;">
                <div class="metric-value" style="font-size:1.5rem;">{stats['maior_prioridade']}</div>
                <div class="metric-label">Disciplina Prioritária</div>
            </div>''', unsafe_allow_html=True)

    st.markdown('---')

    # Dicas de estudo baseadas na prioridade
    st.markdown('<div class="study-tips-box">')
    st.markdown('### 🎯 Dicas de Estudo Com Base nas Prioridades')
    st.markdown('<ul>')
    # Ordenar por prioridade (maior para menor)
    df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
    df_prioridades = df_summary.sort_values('Prioridade_Score', ascending=False)
    for _, row in df_prioridades.iterrows():
        st.markdown(f'<li><b>{row["Disciplinas"]}</b> (Peso {row["Peso"]}): focar nos conteúdos pendentes para avançar</li>', unsafe_allow_html=True)
    st.markdown('</ul>')
    st.markdown('</div>')

    st.markdown('---')

    # Mostrar os gráficos de donut maiores para cada disciplina, lado a lado, máximo 4 por linha
    st.markdown('### Progresso por Disciplina')
    num_cols = min(len(df_summary), 4)
    cols = st.columns(num_cols)
    for idx, row in df_summary.iterrows():
        with cols[idx % num_cols]:
            st.altair_chart(create_altair_donut(row), use_container_width=False)

    st.markdown('---')

    # Gráfico de barras empilhadas True/False ordenado por progresso
    st.markdown('### Conteúdos Concluídos e Pendentes por Disciplina')
    create_stacked_bar(df)

    st.markdown('---')

    # Tabela detalhada para os conteúdos (opcional)
    st.markdown('### 📚 Detalhamento dos Conteúdos')
    if df.empty:
        st.info("Nenhum dado disponível para exibir conteúdos.")
    else:
        df_display = df.copy()
        df_display['Ícone'] = df_display['Status'].apply(lambda x: "✅" if x=='True' else "❌")
        st.dataframe(df_display[['Disciplinas', 'Conteúdos', 'Status', 'Ícone']].sort_values(['Disciplinas', 'Status', 'Conteúdos']), use_container_width=True)


if __name__ == "__main__":
    main()
