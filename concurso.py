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

    # Percentual para rótulos
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

    # Agrupar dados por disciplina e status
    df_group = df.groupby(['Disciplinas', 'Status']).size().reset_index(name='Qtd')
    df_pivot = df_group.pivot(index='Disciplinas', columns='Status', values='Qtd').fillna(0)
    df_pivot['Total'] = df_pivot.sum(axis=1)
    df_pivot['Pct_True'] = df_pivot.get('True', 0) / df_pivot['Total']
    df_pivot = df_pivot.sort_values('Pct_True', ascending=False).reset_index()

    # Em percentual para gráfico de barras horizontais empilhadas
    df_pivot['True_Pct'] = (df_pivot['True'] / df_pivot['Total'] * 100).round(1)
    df_pivot['False_Pct'] = (df_pivot['False'] / df_pivot['Total'] * 100).round(1)

    # Preparar dados para Altair
    df_melt = df_pivot.melt(id_vars=['Disciplinas', 'Pct_True'], value_vars=['True_Pct', 'False_Pct'], var_name='Status', value_name='Percentual')

    # Mapeando nomes para legendas
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
    # Usar scroll horizontal para o container do gráfico
    st.markdown('<div style="overflow-x: auto;">', unsafe_allow_html=True)
    st.altair_chart(chart, use_container_width=False)
    st.markdown('</div>', unsafe_allow_html=True)

# --- CSS com background animado e estilos bons ---
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    body, html, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background: #0e0e2c url('https://www.script-tutorials.com/demos/360/images/stars.png') repeat center top;
        animation: moveBackground 200s linear infinite;
        color: #F5F5F5;
        overflow-x: hidden;
    }

    @keyframes moveBackground {
        from {background-position: 0 0;}
        to {background-position: -10000px 5000px;}
    }

    h1, h2, h3 {
        color: #8ab4f8;
        font-weight: 600;
    }

    .days-remaining-box {
        background: linear-gradient(135deg, #6574FF, #304FFE);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        color: white;
        font-weight: 700;
        font-size: 2.5rem;
        box-shadow: 0 6px 25px rgba(101, 116, 255, 0.7);
        margin-bottom: 2rem;
    }

    .metric-container {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 1.3rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(101, 116, 255, 0.7);
        text-align: center;
        backdrop-filter: blur(10px);
        color: #f5f5f5;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .metric-container:hover {
        transform: translateY(-7px);
        box-shadow: 0 8px 30px rgba(101, 116, 255, 0.9);
    }

    .metric-value {
        font-size: 3rem;
        font-weight: 700;
        color: #a3bffa;
        margin-bottom: 0.2rem;
    }

    .metric-label {
        font-weight: 600;
        color: #d6d6f5;
        font-size: 1.1rem;
    }

    /* Scroll horizontal para containers de gráficos e listas */
    .scroll-container {
        overflow-x: auto;
        white-space: nowrap;
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }

    /* Estilo para os gráficos Altair dentro dos containers */
    .altair-chart {
        display: inline-block !important;
        vertical-align: top;
        margin-right: 2rem;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(101, 116, 255, 0.5);
    }

    /* Expansive containers para conteúdos das disciplinas */
    [data-baseweb="accordion"] > div > div {
        background: rgba(255, 255, 255, 0.1) !important;
        border-radius: 14px !important;
        color: #e0e0ff !important;
        font-weight: 500;
        transition: background 0.3s ease;
    }
    [data-baseweb="accordion"] > div > div:hover {
        background: rgba(101, 116, 255, 0.3) !important;
    }

    /* Conteúdo das linhas das tabelas dentro dos expansives */
    .streamlit-expanderContent > div {
        color: #e0e0ff;
        font-weight: 400;
    }

    /* Table styles inside detail */
    table {
        width: 100% !important;
        border-collapse: collapse !important;
        color: #cfcfff;
    }
    th, td {
        border: 1px solid #444; padding: 8px; text-align: left;
    }
    th {
        background: rgba(101, 116, 255, 0.3);
    }
    tr:nth-child(even) {
        background: rgba(101, 116, 255, 0.15);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Função Principal ---
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso 2025", page_icon="📚", layout="wide")
    inject_css()

    # Calcular dias restantes
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)

    # Caixa principal de dias restantes
    st.markdown(f'<div class="days-remaining-box">⏰ Faltam {dias_restantes} dias para o Concurso 2025</div>', unsafe_allow_html=True)

    # Carregar dados e cálculos
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

    # Mostrar gráficos de donut com scroll horizontal
    st.markdown('### Progresso por Disciplina')
    with st.container():
        st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
        num_cols = min(len(df_summary), 10)
        for idx, row in df_summary.iterrows():
            st.markdown(f'<div class="altair-chart" style="width:360px; display:inline-block;">', unsafe_allow_html=True)
            st.altair_chart(create_altair_donut(row), use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('---')

    # Gráfico de barras empilhadas horizontal com scroll
    st.markdown('### Percentual de Conteúdos Concluídos e Pendentes por Disciplina')
    create_stacked_bar(df)

    st.markdown('---')

    # Containers expansíveis para os conteúdos das disciplinas
    st.markdown('### 📚 Conteúdos por Disciplina')
    if df.empty:
        st.info("Nenhum dado disponível para exibir conteúdos.")
    else:
        disciplinas_ordenadas = sorted(df['Disciplinas'].unique())
        for disc in disciplinas_ordenadas:
            conteudos_disciplina = df[df['Disciplinas'] == disc]
            with st.expander(f"{disc} ({len(conteudos_disciplina)} conteúdos)"):
                # Mostrar tabela estilizada com ícones
                df_disp = conteudos_disciplina.copy()
                df_disp['Ícone'] = df_disp['Status'].apply(lambda x: "✅" if x=='True' else "❌")
                df_disp_display = df_disp[['Conteúdos', 'Status', 'Ícone']].rename(columns={
                    'Conteúdos': 'Conteúdo',
                    'Status': 'Status',
                    'Ícone': 'Ícone'
                })
                st.dataframe(df_disp_display, use_container_width=True)

if __name__ == "__main__":
    main()
