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

# --- Google Sheets Client ---
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

# --- Carregar dados da planilha ---
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

# --- Atualizar status na planilha ---
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

# --- Cálculo progresso ---
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
    progresso_total = round(progresso_total, 1)
    return df_merged, progresso_total

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

# --- Destaque lateral títulos ---
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

# --- Gráfico empilhado sem linhas verticais ---
def create_stacked_bar(df):
    if df.empty or 'Disciplinas' not in df.columns or 'Status' not in df.columns:
        st.info("Sem dados suficientes para gráfico de barras empilhadas.")
        return
    df_filtered = df[df['Status'].isin(['True', 'False'])].copy()
    df_group = df_filtered.groupby(['Disciplinas', 'Status'], observed=True).size().reset_index(name='Qtd')
    if df_group.empty:
        st.info("Nenhum dado válido para gráfico de barras empilhadas.")
        return
    df_pivot = df_group.pivot(index='Disciplinas', columns='Status', values='Qtd').fillna(0)
    df_pivot['Total'] = df_pivot.sum(axis=1)
    if 'True' not in df_pivot.columns:
        df_pivot['True'] = 0
    df_pivot['Pct_True'] = df_pivot['True'] / df_pivot['Total']
    df_pivot = df_pivot.sort_values('Pct_True', ascending=False).reset_index()
    df_pivot['True_Pct'] = (df_pivot['True'] / df_pivot['Total']).round(3).clip(upper=1)
    df_pivot['False_Pct'] = 1 - df_pivot['True_Pct']
    df_melt = df_pivot.melt(id_vars=['Disciplinas'], value_vars=['True_Pct', 'False_Pct'],
                            var_name='Status', value_name='Percentual')
    df_melt['Status'] = df_melt['Status'].map({'True_Pct': 'Concluído', 'False_Pct': 'Pendente'})
    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])
    chart = alt.Chart(df_melt).mark_bar(stroke='#f1f1f1', strokeWidth=3).encode(
        y=alt.Y('Disciplinas:N', sort=df_pivot['Disciplinas'].tolist(),
                title=None,
                axis=alt.Axis(labels=False, ticks=False, grid=False)
               ),
        x=alt.X('Percentual:Q', title=None,
                axis=alt.Axis(format='%', tickCount=11, labels=True, ticks=True)),
        color=alt.Color('Status:N', scale=color_scale, legend=None),
        tooltip=['Disciplinas', 'Status', alt.Tooltip('Percentual', format='.1%')]
    ).properties(
        title='Percentual de Conteúdos Concluídos e Pendentes por Disciplina',
        height=600
    ).configure_view(stroke='#f1f1f1', strokeWidth=3)
    st.altair_chart(chart, use_container_width=True)


# --- Gráfico de número de questões com cor e sem linhas verticais ---
def chart_questoes_horizontal_com_cores(df_ordenado):
    bars = alt.Chart(df_ordenado).mark_bar(stroke='#f1f1f1', strokeWidth=3).encode(
        y=alt.Y('Disciplinas:N',
                sort=alt.EncodingSortField(field='Total_Conteudos', order='ascending'),
                title=None,
                axis=alt.Axis(labels=False, ticks=False, grid=False)
               ),
        x=alt.X('Total_Conteudos:Q',
                title=None,
                axis=alt.Axis(labels=False, ticks=False)
               ),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=[alt.Tooltip('Disciplinas'), alt.Tooltip('Total_Conteudos', title='Quantidade de Questões')]
    )
    texts = alt.Chart(df_ordenado).mark_text(
        align='left',
        baseline='middle',
        dx=3,
        fontSize=12,
        color='#064820'
    ).encode(
        y=alt.Y('Disciplinas:N',
                sort=alt.EncodingSortField(field='Total_Conteudos', order='ascending')),
        x='Total_Conteudos:Q',
        text='Total_Conteudos:Q'
    )
    return (bars + texts).properties(width=600, height=600, title='Quantidade de Questões por Disciplina')


# --- Gráfico mosaico percentual sem linhas verticais ---
def mosaic_chart_peso_por_disciplina_percentual():
    df = pd.DataFrame(ED_DATA)
    total_peso = df['Peso'].sum()
    df = df.sort_values('Peso', ascending=False).reset_index(drop=True)
    df['start'] = df['Peso'].cumsum() - df['Peso']
    df['end'] = df['Peso'].cumsum()
    df['start_norm'] = df['start'] / total_peso
    df['end_norm'] = df['end'] / total_peso
    df['percentual'] = (df['Peso'] / total_peso * 100).round(1).astype(str) + '%'

    base = alt.Chart(df).encode(
        x=alt.X('start_norm:Q', title=None, axis=alt.Axis(labels=False, ticks=False)),
        x2='end_norm'
    )

    bars = base.mark_rect(
        y=0,
        y2=1,
        cornerRadiusTopLeft=5,
        cornerRadiusTopRight=5,
        stroke='#f1f1f1',
        strokeWidth=3
    ).encode(
        color=alt.Color('Disciplinas:N', legend=None)
    )

    text_disciplina = alt.Chart(df).mark_text(
        align='center',
        baseline='middle',
        dy=-10,
        fontWeight='bold',
        color='black',
        fontSize=14
    ).encode(
        x=alt.X((df['start_norm'] + (df['Peso'] / total_peso) / 2), type='quantitative'),
        y=alt.value(0.5),
        text='Disciplinas:N'
    )

    text_percentual = alt.Chart(df).mark_text(
        align='center',
        baseline='middle',
        dy=10,
        fontWeight='bold',
        color='black',
        fontSize=14
    ).encode(
        x=alt.X((df['start_norm'] + (df['Peso'] / total_peso) / 2), type='quantitative'),
        y=alt.value(0.5),
        text='percentual:N'
    )

    chart = (bars + text_disciplina + text_percentual).properties(
        width=600,
        height=600,
        title='Peso por Disciplina (%)'
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        domain=False,
        ticks=False,
        labels=False,
        grid=False
    )

    return chart


# --- Gráfico radial com valor "Concluído" dentro do arco ---
def donut_chart_radial_personalizado(concluido_percentual):
    pendente_percentual = max(0, 100 - concluido_percentual)
    source = pd.DataFrame({
        "Status": ["Concluído", "Pendente"],
        "Valor": [concluido_percentual, pendente_percentual]
    })

    base = alt.Chart(source).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        radius=alt.value(120),
        color=alt.Color("Status:N",
            scale=alt.Scale(
                domain=["Concluído", "Pendente"],
                range=["#2ecc71", "#e74c3c"]
            ),
            legend=None
        )
    )

    c1 = base.mark_arc(innerRadius=70, stroke="#f1f1f1", strokeWidth=3)

    # Texto central com percentual total
    percentual_text = f"{concluido_percentual:.1f}%"
    c2 = alt.Chart(pd.DataFrame({'text': [percentual_text]})).mark_text(
        radius=0,
        size=24,
        fontWeight="bold",
        color="#064820"
    ).encode(
        text='text:N'
    )

    # Texto com valor "Concluído" (True) dentro do segmento
    # Ângulo médio para posicionar o texto centralizado no arco de "Concluído"
    source_text = pd.DataFrame({
        "Status": ["Concluído"],
        "Valor": [concluido_percentual],
        "angle_mid": [concluido_percentual / 2],  # Meio do arco em percentual
        "radius": [95],  # Posicionado dentro dos arcos (entre innerRadius 70 e outerRadius 120)
        "text": [f"{int(round(concluido_percentual))}"]
    })

    c3 = alt.Chart(source_text).mark_text(
        size=24,
        fontWeight="bold",
        color="#064820"
    ).encode(
        theta=alt.Theta("angle_mid:Q", stack=False),
        radius=alt.Radius("radius:Q"),
        text='text:N'
    )

    chart = (c1 + c2 + c3).properties(
        width=280,
        height=280
    )

    return chart


# --- CSS ---
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    body, html, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        margin: 0; padding: 0;
        height: 100%;
        background: #ffffff;
        overflow-x: hidden;
        color: #222831;
        position: relative;
    }
    .reportview-container, .main, .block-container {
        background-color: #ffffff !important;
        color: #222831;
    }
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    .metric-container {
        background: #f0f5ff;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 15px #a3bffa90;
        color: #2c3e50;
        transition: box-shadow 0.3s ease;
        text-align: center;
    }
    .metric-container:hover {
        box-shadow: 0 0 30px #6a8edecc;
    }
    .metric-value {
        font-size: 3rem;
        font-weight: 700;
        color: #355e9e;
        margin-bottom: 0.2rem;
    }
    .metric-label {
        font-weight: 600;
        font-size: 1.1rem;
        color: #566e95;
    }
    .altair-chart {
        border: 1px solid #f1f1f1;
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 0 0 15px #a3bffa88;
        background: #e0e9ff;
        margin-bottom: 2rem;
    }
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
    .streamlit-expanderContent > div {
        color: #2c3e50;
        font-weight: 400;
    }
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
    footer {
        font-style: italic !important;
        font-size: 1.1rem !important;
        color: #064820 !important;
        opacity: 0.9 !important;
        margin-top: 40px !important;
        text-align: center !important;
        user-select: none !important;
        font-family: 'Inter', sans-serif !important;
    }
    footer span {
        font-weight: 600 !important;
        color: #355e9e !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Container topo com sombra ---
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

# --- Rodapé com emoticons e tamanho 12 (toda largura) ---
def rodape_motivacional():
    st.markdown("""
        <footer>
            🚀 "O sucesso é a soma de pequenos esforços repetidos dia após dia." 🎯
            <br><span>Mantenha o foco, você está no caminho certo! 💪📚</span>
        </footer>
    """, unsafe_allow_html=True)

# --- Mostrar os dois gráficos lado a lado com mesma altura do gráfico empilhado ---
def display_questoes_e_peso(df_summary):
    if df_summary.empty:
        st.info("Nenhum dado para mostrar gráficos de questões e pesos.")
        return
    df_ordenado = df_summary.sort_values('Total_Conteudos', ascending=True)

    col1, col2 = st.columns(2)
    with col1:
        chart_q = chart_questoes_horizontal_com_cores(df_ordenado)
        st.altair_chart(chart_q, use_container_width=True)
    with col2:
        chart_p = mosaic_chart_peso_por_disciplina_percentual()
        st.altair_chart(chart_p, use_container_width=True)

# --- Exibir os gráficos donut e radial responsivos ---
def display_6_charts_responsive_with_titles(df_summary, progresso_geral, max_cols=3):
    total_charts = len(df_summary) + 1
    rows = (total_charts + max_cols - 1) // max_cols
    disciplina_charts = [create_altair_donut(df_summary.iloc[i]) for i in range(len(df_summary))]
    # adiciona o radial modificado como o último gráfico
    radial_chart = donut_chart_radial_personalizado(progresso_geral)
    disciplina_charts.append(radial_chart)
    chart_index = 0
    for r in range(rows):
        cols = st.columns(max_cols, gap="medium")
        for c in range(max_cols):
            if chart_index >= total_charts:
                break
            with cols[c]:
                if chart_index < len(df_summary):
                    nome = df_summary.iloc[chart_index]['Disciplinas'].title()
                else:
                    nome = "Progresso Geral"
                st.markdown(f'<h3 style="text-align:center;">{nome}</h3>', unsafe_allow_html=True)
                st.altair_chart(disciplina_charts[chart_index], use_container_width=True)
            chart_index += 1

# --- Gráfico donut por disciplina sem legenda ---
def create_altair_donut(row):
    concluido = int(row['Conteudos_Concluidos'])
    pendente = int(row['Conteudos_Pendentes'])
    total = max(concluido + pendente, 1)
    concluido_pct = round((concluido / total) * 100, 1)
    pendente_pct = round((pendente / total) * 100, 1)
    source = pd.DataFrame({
        'Status': ['Concluído', 'Pendente'],
        'Valor': [concluido, pendente],
        'Percentual': [concluido_pct, pendente_pct]
    })
    source_label = pd.DataFrame({'Percentual': [concluido_pct / 100]})
    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])
    base_chart = alt.Chart(source).encode(
        theta=alt.Theta(field='Valor', type='quantitative'),
        color=alt.Color('Status:N', scale=color_scale, legend=None),
        tooltip=[alt.Tooltip('Status'), alt.Tooltip('Valor', format='d'), alt.Tooltip('Percentual', format='.1f')]
    )
    donut = base_chart.mark_arc(innerRadius=70, stroke='#f1f1f1', strokeWidth=3)
    text = alt.Chart(source_label).mark_text(
        size=24, fontWeight='bold', color='#064820'
    ).encode(
        text=alt.Text('Percentual:Q', format='.0%')
    ).properties(width=280, height=280)
    chart = (donut + text).properties(
        width=280,
        height=280
    ).configure_view(stroke='#f1f1f1', strokeWidth=3)
    return chart


# --- Main ---
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso 2025", page_icon="📚", layout="wide")
    inject_css()
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_topbar_with_logo(dias_restantes)
    df = load_data_with_row_indices()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)

    # Indicadores topo
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

    st.markdown("---")

    titulo_com_destaque("📊 Progresso por Disciplina", cor_lateral="#3498db")
    display_6_charts_responsive_with_titles(df_summary, progresso_geral, max_cols=3)

    st.markdown("---")

    titulo_com_destaque("📈 Percentual de Conteúdos Concluídos e Pendentes por Disciplina", cor_lateral="#2980b9")
    create_stacked_bar(df)

    st.markdown("---")

    titulo_com_destaque("📝⚖️ Quantidade de Questões e Peso por Disciplina", cor_lateral="#8e44ad")
    display_questoes_e_peso(df_summary)

    st.markdown("---")

    rodape_motivacional()


if __name__ == "__main__":
    main()
