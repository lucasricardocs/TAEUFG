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
        'CONHECIMENTOS ESPECÍFICOS'
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

    df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
    maior_prioridade = df_summary.loc[df_summary['Prioridade_Score'].idxmax()]['Disciplinas'] if not df_summary.empty else ""

    return {
        'dias_restantes': dias_restantes,
        'total_conteudos': total_conteudos,
        'concluidos': int(concluidos),
        'pendentes': int(pendentes),
        'percentual_geral': percentual_geral,
        'topicos_por_dia': topicos_por_dia,
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

    df_group = df.groupby(['Disciplinas', 'Status']).size().reset_index(name='Qtd')
    df_pivot = df_group.pivot(index='Disciplinas', columns='Status', values='Qtd').fillna(0)
    df_pivot['Total'] = df_pivot.sum(axis=1)
    df_pivot['Pct_True'] = df_pivot.get('True', 0) / df_pivot['Total']
    df_pivot = df_pivot.sort_values('Pct_True', ascending=False).reset_index()

    df_pivot['True_Pct'] = (df_pivot['True'] / df_pivot['Total'] * 100).round(1)
    df_pivot['False_Pct'] = (df_pivot['False'] / df_pivot['Total'] * 100).round(1)

    df_melt = df_pivot.melt(id_vars=['Disciplinas', 'Pct_True'], value_vars=['True_Pct', 'False_Pct'], var_name='Status', value_name='Percentual')
    df_melt['Status'] = df_melt['Status'].map({'True_Pct':'Concluído', 'False_Pct':'Pendente'})

    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])

    chart = (
        alt.Chart(df_melt)
        .mark_bar()
        .encode(
            y=alt.Y('Disciplinas:N', sort=df_pivot['Disciplinas'].tolist(), title='Disciplina'),
            x=alt.X('Percentual:Q', title='Percentual (%)', axis=alt.Axis(format='%')),
            color=alt.Color('Status:N', scale=color_scale, legend=alt.Legend(title="Status")),
            tooltip=['Disciplinas', 'Status', alt.Tooltip('Percentual', format='.1f')]
        )
        .properties(title='Percentual de Conteúdos Concluídos e Pendentes por Disciplina', width=900, height=450)
    )
    st.markdown('<div style="overflow-x: auto;">', unsafe_allow_html=True)
    st.altair_chart(chart, use_container_width=False)
    st.markdown('</div>', unsafe_allow_html=True)

# --- CSS claro e animado ---
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    /* BODY E BACKGROUND */
    body, html, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        margin: 0; padding: 0;
        height: 100%;
        background: #e6f0ff;
        overflow-x: hidden;
        color: #222831;
        position: relative;
    }

    /* Contêiner para partículas animadas */
    #animated-background {
        pointer-events: none;
        position: fixed;
        top: 0; left: 0;
        width: 100vw;
        height: 100vh;
        z-index: -1;
        background: radial-gradient(circle at center, #ffffff 0%, #d0e2ff 80%);
        overflow: hidden;
    }

    /* Partículas com tom escuro para contraste */
    .stars {
        width: 3px;
        height: 3px;
        background: #334960;
        border-radius: 50%;
        position: absolute;
        animation: twinkle 3s infinite ease-in-out alternate;
    }

    .stars::before {
        content: "";
        position: absolute;
        width: 3px; height: 3px;
        background: #334960;
        border-radius: 50%;
        box-shadow:
            15vw 15vh #334960,
            40vw 75vh #334960,
            70vw 25vh #334960,
            85vw 85vh #334960,
            20vw 65vh #334960,
            60vw 55vh #334960,
            80vw 15vh #334960,
            35vw 12vh #334960,
            55vw 37vh #334960,
            12vw 90vh #334960;
        animation: twinkle 3s infinite ease-in-out alternate 1.5s;
    }

    @keyframes twinkle {
        0% {opacity: 0.3;}
        50% {opacity: 1;}
        100% {opacity: 0.3;}
    }

    /* Container do Streamlit com fundo branco translúcido */
    .reportview-container, 
    .main, 
    .block-container {
        background-color: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(10px);
        color: #222831;
    }

    /* Cabeçalhos e textos escuros */
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }

    /* Estilo dos cards */
    .metric-container {
        background: #f0f5ff;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 15px #a3bffa90;
        color: #2c3e50;
        transition: box-shadow 0.3s ease;
    }
    .metric-container:hover {
        box-shadow: 0 0 30px #6a8edecc;
    }

    /* Títulos e valores */
    .metric-value {
        font-size: 3rem;
        font-weight: 700;
        color: #355e9e;
    }
    .metric-label {
        font-weight: 600;
        font-size: 1.1rem;
        color: #566e95;
    }

    /* Scroll horizontal para gráficos e conteúdos */
    .scroll-container {
        overflow-x: auto;
        white-space: nowrap;
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }

    /* Gráficos inline com sombra e fundo translúcido */
    .altair-chart {
        display: inline-block !important;
        vertical-align: top;
        margin-right: 2rem;
        background: #e0e9ff;
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 0 0 15px #a3bffa88;
    }

    /* Expansores de disciplinas */
    [data-baseweb="accordion"] > div > div {
        background: #f2f7ff !important;
        border-radius: 14px !important;
        color: #355e9e !important;
        font-weight: 500;
        transition: background 0.3s ease;
    }
    [data-baseweb="accordion"] > div > div:hover {
        background: #a3bffa55 !important;
    }

    /* Conteúdo dentro dos expansores */
    .streamlit-expanderContent > div {
        color: #2c3e50;
        font-weight: 400;
    }

    /* Tabela dentro expansores */
    table {
        width: 100% !important;
        border-collapse: collapse !important;
        color: #2c3e50;
    }
    th, td {
        border: 1px solid #a3bffa;
        padding: 8px; 
        text-align: left;
    }
    th {
        background: #a3bffa22;
    }
    tr:nth-child(even) {
        background: #cbdcff55;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Injeta o background animado ---
def inject_animated_background():
    st.markdown("""
        <div id="animated-background">
            <div class="stars"></div>
        </div>
    """, unsafe_allow_html=True)

# --- Função Principal ---
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso 2025", page_icon="📚", layout="wide")
    inject_css()
    inject_animated_background()

    # Calcular dias restantes
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)

    # Caixa principal de dias restantes (destacada com gradiente)
    st.markdown(f'<div class="metric-container" style="background: linear-gradient(135deg, #6574FF, #304FFE); font-size:2.7rem; font-weight:700; text-align:center; margin-bottom: 2rem;">⏰ Faltam {dias_restantes} dias para o Concurso 2025</div>', unsafe_allow_html=True)

    # Carregar dados e calcular métricas
    df = load_data()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)

    # Métricas principais em colunas
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

    # Gráficos de rosca lado a lado com st.columns
    st.markdown('### Progresso por Disciplina')
    num_graficos = len(df_summary)
    max_por_linha = 4
    linhas = (num_graficos + max_por_linha - 1) // max_por_linha
    for i in range(linhas):
        inicio = i * max_por_linha
        fim = min(inicio + max_por_linha, num_graficos)
        cols = st.columns(fim - inicio)
        for j, idx in enumerate(range(inicio, fim)):
            with cols[j]:
                st.altair_chart(create_altair_donut(df_summary.iloc[idx]), use_container_width=True)

    st.markdown('---')

    # Gráfico empilhado horizontal maior com scroll
    st.markdown('### Percentual de Conteúdos Concluídos e Pendentes por Disciplina')
    create_stacked_bar(df)

    st.markdown('---')

    # Containers expansíveis para os conteúdos por disciplina
    st.markdown('### 📚 Conteúdos por Disciplina')
    if df.empty:
        st.info("Nenhum dado disponível para exibir conteúdos.")
    else:
        disciplinas_ordenadas = sorted(df['Disciplinas'].unique())
        for disc in disciplinas_ordenadas:
            conteudos_disciplina = df[df['Disciplinas'] == disc]
            with st.expander(f"{disc} ({len(conteudos_disciplina)} conteúdos)"):
                df_disp = conteudos_disciplina.copy()
                df_disp['Ícone'] = df_disp['Status'].apply(lambda x: "✅" if x == 'True' else "❌")
                df_disp_display = df_disp[['Conteúdos', 'Status', 'Ícone']].rename(columns={
                    'Conteúdos': 'Conteúdo',
                    'Status': 'Status',
                    'Ícone': 'Ícone'
                })
                st.dataframe(df_disp_display, use_container_width=True)


if __name__ == "__main__":
    main()
