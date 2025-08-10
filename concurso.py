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

warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

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

# --- Carregar dados da planilha com índice para atualização ---
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
        df['sheet_row'] = df['index'] + 2  # Linha real na planilha (linha 1 é o cabeçalho)
        df.drop('index', axis=1, inplace=True)

        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Falha ao carregar dados: {e}")
        return pd.DataFrame()

# --- Atualizar status na planilha com tratamento de erro ---
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

# --- Cálculo de métricas ---
def calculate_progress(df):
    df_edital = pd.DataFrame(ED_DATA)
    if df.empty:
        df_edital['Conteudos_Concluidos'] = 0
        df_edital['Conteudos_Pendentes'] = df_edital['Total_Conteudos']
        df_edital['Progresso_Ponderado'] = 0.0
        return df_edital, 0.0

    df['Concluido'] = (df['Status'] == 'True').astype(int)
    resumo = df.groupby('Disciplinas', observed=False)['Concluido'].sum().reset_index(name='Conteudos_Concluidos')

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

# --- Container título ---
def titulo_com_destaque(texto):
    st.markdown(f'''
        <div style="
            background-color: #f5f5f5;
            padding: 12px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px #a3bffa88;
            margin-bottom: 40px;
            font-weight: 700;
            font-size: 1.6rem;
            color: #2c3e50;
            display: flex; align-items: center; gap: 1rem;
        ">
            {texto}
    ''' + '</div>', unsafe_allow_html=True)

# --- Gráfico rosca geral do progresso (radial) ---
def donut_chart_progresso_geral(progresso_percentual, width=300, height=300,
                               colors=('#2ecc71', '#e74c3c'),
                               inner_radius=70, font_size=24,
                               text_color='#064820', show_tooltip=True):
    concluido = max(0, min(progresso_percentual, 100))
    pendente = 100 - concluido

    df = pd.DataFrame({
        'Status': ['Concluído', 'Pendente'],
        'Valor': [concluido, pendente]
    })

    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=list(colors))

    base = alt.Chart(df).encode(
        theta=alt.Theta(field='Valor', type='quantitative'),
        color=alt.Color('Status:N', scale=color_scale, legend=None)
    )

    if show_tooltip:
        base = base.encode(
            tooltip=[alt.Tooltip('Status'), alt.Tooltip('Valor', format='.1f')]
        )

    donut = base.mark_arc(innerRadius=inner_radius, stroke='#fff', strokeWidth=2).properties(
        width=width,
        height=height
    )

    text = alt.Chart(pd.DataFrame({'text': [f'{concluido:.1f}%']})).mark_text(
        fontSize=font_size,
        fontWeight='bold',
        color=text_color,
        dy=0
    ).encode(
        text='text:N'
    ).properties(width=width, height=height)

    chart = (donut + text).configure_view(strokeWidth=0)

    return chart

# --- Gráfico rosca por disciplina ---
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
    donut = base_chart.mark_arc(innerRadius=70, stroke='#d3d3d3', strokeWidth=3)
    text = alt.Chart(source_label).mark_text(size=20, fontWeight='bold', color='#064820').encode(
        text=alt.Text('Percentual:Q', format='.0%')
    ).properties(width=350, height=350)

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
    ).configure_view(stroke='#d3d3d3', strokeWidth=1)

    return chart

# --- Gráfico empilhado percentual ---
def create_stacked_bar(df):
    if df.empty:
        st.info("Sem dados para gráfico de barras empilhadas.")
        return

    df_group = df.groupby(['Disciplinas', 'Status']).size().reset_index(name='Qtd')
    df_pivot = df_group.pivot(index='Disciplinas', columns='Status', values='Qtd').fillna(0)
    df_pivot['Total'] = df_pivot.sum(axis=1)
    df_pivot['Pct_True'] = df_pivot.get('True', 0) / df_pivot['Total']
    df_pivot = df_pivot.sort_values('Pct_True', ascending=False).reset_index()

    df_pivot['True_Pct'] = (df_pivot['True'] / df_pivot['Total']).round(3).clip(upper=1)
    df_pivot['False_Pct'] = 1 - df_pivot['True_Pct']

    df_melt = df_pivot.melt(id_vars=['Disciplinas'], value_vars=['True_Pct', 'False_Pct'],
                            var_name='Status', value_name='Percentual')
    df_melt['Status'] = df_melt['Status'].map({'True_Pct': 'Concluído', 'False_Pct': 'Pendente'})

    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])

    chart = alt.Chart(df_melt).mark_bar().encode(
        y=alt.Y('Disciplinas:N', sort=df_pivot['Disciplinas'].tolist(), title=None, axis=alt.Axis(labels=False, ticks=False)),
        x=alt.X('Percentual:Q', title=None,
                axis=alt.Axis(format='%', tickCount=11, labels=False, ticks=False)),
        color=alt.Color('Status:N', scale=color_scale, legend=None),
        tooltip=['Disciplinas', 'Status', alt.Tooltip('Percentual', format='.1%')]
    ).properties(title='Percentual de Conteúdos Concluídos e Pendentes por Disciplina', height=600).configure_view(
        stroke='#d3d3d3', strokeWidth=1)

    st.altair_chart(chart, use_container_width=True)

# --- Gráfico barras horizontais número de questões ---
def chart_questoes(df_ordenado):
    return alt.Chart(df_ordenado).mark_bar(color='#3498db').encode(
        x=alt.X('Total_Conteudos:Q', title=None, axis=alt.Axis(labels=False, ticks=False)),
        y=alt.Y('Disciplinas:N', sort=alt.EncodingSortField(field='Total_Conteudos', order='ascending'), title=None,
                axis=alt.Axis(labels=False, ticks=False)),
        tooltip=[alt.Tooltip('Disciplinas'), alt.Tooltip('Total_Conteudos', title='Quantidade de Questões')]
    ).properties(width=350, height=350, title='Quantidade de Questões por Disciplina')

# --- Mosaic Chart peso ponderado ---
def mosaic_chart_peso_importancia():
    df = pd.DataFrame(ED_DATA)
    df['Peso_Ponderado'] = df['Total_Conteudos'] * df['Peso']
    df = df.sort_values('Peso_Ponderado', ascending=False).reset_index(drop=True)

    total_pp = df['Peso_Ponderado'].sum()
    df['start'] = df['Peso_Ponderado'].cumsum() - df['Peso_Ponderado']
    df['start_norm'] = df['start'] / total_pp
    df['end_norm'] = (df['start'] + df['Peso_Ponderado']) / total_pp

    base = alt.Chart(df).encode(
        x=alt.X('start_norm:Q', title=None, axis=None),
        x2='end_norm',
        y=alt.Y('Disciplinas:N', axis=None, title=None, labels=False, ticks=False),
    )

    bars = base.mark_rect(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=[
            alt.Tooltip('Disciplinas:N', title='Disciplina'),
            alt.Tooltip('Peso_Ponderado:Q', title='Peso Ponderado')
        ]
    )

    text_disciplina = base.mark_text(
        align='center',
        baseline='middle',
        dy=-10,
        fontWeight='bold',
        color='black'
    ).encode(
        text='Disciplinas:N',
        x='start_norm:Q'
    )

    text_valor = base.mark_text(
        align='center',
        baseline='middle',
        dy=12,
        color='black'
    ).encode(
        text=alt.Text('Peso_Ponderado:Q', format='.0f')
    )

    chart = (bars + text_disciplina + text_valor).properties(
        width=600,
        height=150,
        title='Importância Relativa das Disciplinas (Peso Ponderado)'
    ).configure_view(strokeWidth=0).configure_axis(labels=False, grid=False, domain=False)

    return chart

# --- Exposição dos gráficos lado a lado ---
def display_questoes_e_peso(df_summary):
    if df_summary.empty:
        st.info("Nenhum dado para mostrar gráficos de questões e pesos.")
        return

    df_ordenado = df_summary.sort_values('Total_Conteudos', ascending=True)

    chart_q = chart_questoes(df_ordenado)
    chart_p = mosaic_chart_peso_importancia()

    st.markdown('<div style="margin-bottom: 40px;"></div>', unsafe_allow_html=True)
    st.markdown(f'''
        <div style="
            background-color: #f5f5f5;
            padding: 12px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px #a3bffa88;
            margin-bottom: 20px;
            font-weight: 700;
            font-size: 1.6rem;
            color: #2c3e50;
            display: flex; justify-content: center; align-items: center;
        ">
            📝⚖️ Quantidade de Questões e Peso por Disciplina
        </div>
    ''', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(chart_q, use_container_width=True)
    with col2:
        st.altair_chart(chart_p, use_container_width=True)

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
        border: 1px solid #d3d3d3;
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
        margin-top: 40px;
        padding: 10px 0;
        background-color: transparent;
        text-align: center;
        font-size: 1rem;
        color: #064820;
        font-style: italic;
        font-weight: 500;
        border-top: 1px solid #a3bffa66;
        font-family: 'Inter', sans-serif;
        box-shadow: 0 -2px 8px #a3bffa33;
        user-select: none;
    }
    footer span {
        color: #355e9e;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Topbar com logo e dias faltantes ---
def render_topbar_with_logo(dias_restantes):
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: flex-start;
        height: 300px;
        background-color: #f5f5f5;
        padding: 0 40px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
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
    </div>
    """, unsafe_allow_html=True)

# --- Mostrar gráficos rosca responsivos ---
def display_responsive_donuts(df_summary):
    max_cols = 4
    num_charts = len(df_summary)
    rows = (num_charts + max_cols - 1) // max_cols
    for i in range(rows):
        start_idx = i * max_cols
        end_idx = min(start_idx + max_cols, num_charts)
        cols = st.columns(end_idx - start_idx)
        for j, idx in enumerate(range(start_idx, end_idx)):
            with cols[j]:
                st.altair_chart(create_altair_donut(df_summary.iloc[idx]), use_container_width=True)

# --- Rodapé ---
def rodape_motivacional():
    st.markdown("""
        <footer>
            "O sucesso é a soma de pequenos esforços repetidos dia após dia."
            <br><span>Mantenha o foco, você está no caminho certo!</span>
        </footer>
    """, unsafe_allow_html=True)

# --- Main ---
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso 2025", page_icon="📚", layout="wide")
    inject_css()

    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_topbar_with_logo(dias_restantes)

    df = load_data_with_row_indices()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)

    # Indicadores no topo
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

    # Título com gráfico rosca de progresso geral junto
    col_title, col_donut = st.columns([4, 1])
    with col_title:
        titulo_com_destaque("📊 Progresso por Disciplina")
    with col_donut:
        st.altair_chart(donut_chart_progresso_geral(progresso_geral, width=150, height=150), use_container_width=False)

    # Gráficos rosca por disciplina
    display_responsive_donuts(df_summary)

    st.markdown('---')

    titulo_com_destaque("📈 Percentual de Conteúdos Concluídos e Pendentes por Disciplina")
    create_stacked_bar(df)

    st.markdown('---')

    titulo_com_destaque("📚 Conteúdos por Disciplina")

    worksheet = get_worksheet()
    if df.empty or worksheet is None:
        st.info("Nenhum dado disponível para exibir conteúdos.")
    else:
        disciplinas_ordenadas = sorted(df['Disciplinas'].unique())
        for disc in disciplinas_ordenadas:
            conteudos_disciplina = df[df['Disciplinas'] == disc]
            with st.expander(f"{disc} ({len(conteudos_disciplina)} conteúdos)"):
                # Checkbox com tratamento para evitar erro e limpar cache antes do rerun
                for _, row in conteudos_disciplina.iterrows():
                    key = f"{row['Disciplinas']}_{row['Conteúdos']}_{row['sheet_row']}"
                    checked = (row['Status'] == 'True')
                    try:
                        novo_status = st.checkbox(label=row['Conteúdos'], value=checked, key=key)
                        if novo_status != checked:
                            sucesso = update_status_in_sheet(worksheet, row['sheet_row'], "True" if novo_status else "False")
                            if sucesso:
                                st.success(f"Status do conteúdo '{row['Conteúdos']}' atualizado com sucesso!")
                                load_data_with_row_indices.clear()
                                st.experimental_rerun()
                            else:
                                st.error(f"Falha ao atualizar status do conteúdo '{row['Conteúdos']}'.")
                    except Exception as e:
                        st.error(f"Erro inesperado ao atualizar: {e}")

    st.markdown('---')
    titulo_com_destaque("📝⚖️ Quantidade de Questões e Peso por Disciplina")
    display_questoes_e_peso(df_summary)

    rodape_motivacional()

if __name__ == "__main__":
    main()
