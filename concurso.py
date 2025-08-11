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
import random

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
        st.error(f"❌ Erro inesperado ao atualizar planilha: {e}")
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
    df_merged['Ponto_por_Conteudo'] = df_merged.apply(lambda row: row['Peso'] / row['Total_Conteudos'] if row['Total_Conteudos'] > 0 else 0, axis=1)
    df_merged['Pontos_Concluidos'] = df_merged['Conteudos_Concluidos'] * df_merged['Ponto_por_Conteudo']
    df_merged['Progresso_Ponderado'] = np.where(df_merged['Peso'] > 0, (df_merged['Pontos_Concluidos'] / df_merged['Peso']) * 100, 0).round(1)
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

def titulo_com_destaque(texto, cor_lateral="#8e44ad"):
    st.markdown(f"""
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
        position: relative;
    ">
        {texto}
        <div style="
            position: absolute;
            top: 8px;
            right: 16px;
            font-size: 11px;
            color: #2c3e50;
            font-weight: 600;
            user-select: none;
        ">
            Goiânia, {datetime.now().strftime('%d/%m/%Y')}
        </div>
    </div>""", unsafe_allow_html=True)

def render_topbar_with_logo(dias_restantes):
    hoje_texto = datetime.now().strftime('%d de %B de %Y')
    st.markdown(f"""
    <div style="
        display: flex;
        align-items: center;
        background-color: #f5f5f5;
        border-radius: 12px;
        padding: 0 3vw;
        min-height: 250px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.25);
        margin-bottom: 20px;
        font-family: 'Inter', sans-serif;
        flex-wrap: wrap;
        gap: 1rem;
        position: relative;
    ">
        <img src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG"
             style="height: 150px; margin-right: 2vw; flex-shrink: 0;">
        <div style="
            font-size: clamp(1.8rem, 3vw, 3rem);
            font-weight: 700;
            color: #2c3e50;
            white-space: nowrap;
            line-height: 1.2;
            flex-grow: 1;
            min-width: 200px;
        ">
            ⏰ Faltam {dias_restantes} dias para o concurso de TAE
        </div>
        <div style="
            position: absolute;
            top: 8px;
            right: 16px;
            font-size: 11px;
            font-weight: 600;
            color: #2c3e50;
            user-select: none;
            white-space: nowrap;
        ">
            Goiânia, {hoje_texto}
        </div>
    </div>""", unsafe_allow_html=True)

def display_lista_numero_questoes():
    df = pd.DataFrame(ED_DATA)
    css = """
    <style>
    .questao-item {
        margin: 5px 0;
        padding: 8px 12px;
        border-radius: 8px;
        transition: background-color 0.3s, color 0.3s;
        cursor: pointer;
        font-weight: 600;
        font-size: 1.05rem;
        user-select: none;
    }
    .questao-item:hover {
        background-color: #d0e4ff;
        color: #064270;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    for _, row in df.iterrows():
        st.markdown(f'<div class="questao-item"><strong>{row["Disciplinas"].title()}</strong>: {row["Questões"]} questões</div>', unsafe_allow_html=True)

def pie_chart_peso_vezes_questoes_com_labels(width=600, height=600):
    df = pd.DataFrame(ED_DATA)
    df['Peso_vezes_Questoes'] = df['Peso'] * df['Questões']
    total = df['Peso_vezes_Questoes'].sum()
    df['Percentual'] = df['Peso_vezes_Questoes'] / total

    base = alt.Chart(df).encode(
        theta=alt.Theta("Peso_vezes_Questoes:Q", stack=True),
        color=alt.Color("Disciplinas:N", legend=None)
    )

    pie = base.mark_arc(outerRadius=120, stroke='#fff', strokeWidth=2)

    # Rótulos externos horizontais alinhados para fácil leitura
    text_labels = alt.Chart(df).mark_text(
        align='left',
        baseline='middle',
        dx=5,
        fontSize=13,
        fontWeight='bold',
        color='black'
    ).encode(
        theta=alt.Theta('Peso_vezes_Questoes:Q', stack=True),
        radius=alt.value(150),
        text=alt.Text('Disciplinas:N')
    )

    text_perc = alt.Chart(df).mark_text(
        align='left',
        baseline='middle',
        dx=5,
        dy=14,
        fontSize=12,
        color='#2ecc71'
    ).encode(
        theta=alt.Theta('Peso_vezes_Questoes:Q', stack=True),
        radius=alt.value(150),
        text=alt.Text('Percentual:Q', format='.1%')
    )

    chart = (pie + text_labels + text_perc).properties(width=width, height=height)
    return chart

def display_conteudos_com_checkboxes(df):
    worksheet = get_worksheet()
    if df.empty or worksheet is None:
        st.info("Nenhum dado disponível para exibir conteúdos.")
        return

    titulo_com_destaque("📚 Conteúdos por Disciplina", cor_lateral="#8e44ad")

    disciplinas_ordenadas = sorted(df['Disciplinas'].unique())
    for disc in disciplinas_ordenadas:
        conteudos_disciplina = df[df['Disciplinas'] == disc]
        with st.expander(f"{disc} ({len(conteudos_disciplina)} conteúdos)"):
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

def donut_chart_progresso_geral(progresso_percentual, width=280, height=280,
                               colors=('#2ecc71', '#e74c3c'),
                               inner_radius=70, font_size=22,
                               text_color='#2ecc71', show_tooltip=True):
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
        base = base.encode(tooltip=[alt.Tooltip('Status'), alt.Tooltip('Valor', format='.1f')])
    donut = base.mark_arc(innerRadius=inner_radius, stroke='#d3d3d3', strokeWidth=3).properties(width=width, height=height)
    text = alt.Chart(pd.DataFrame({'text': [f'{concluido:.1f}%']})).mark_text(
        fontSize=font_size, fontWeight='bold', color=text_color, dy=0
    ).encode(text='text:N').properties(width=width, height=height)
    return (donut + text).configure_view(strokeWidth=0)

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
    text = alt.Chart(source_label).mark_text(
        size=22, fontWeight='bold', color='#2ecc71'
    ).encode(text=alt.Text('Percentual:Q', format='.0%')).properties(width=280, height=280)
    return (donut + text).properties(width=280, height=280).configure_view(stroke='#d3d3d3', strokeWidth=3)

def display_6_charts_responsive_with_titles(df_summary, progresso_geral, max_cols=3):
    total_charts = len(df_summary) + 1
    rows = (total_charts + max_cols - 1) // max_cols
    disciplina_charts = [create_altair_donut(df_summary.iloc[i]) for i in range(len(df_summary))]
    disciplina_charts.append(donut_chart_progresso_geral(progresso_geral, width=280, height=280, font_size=22, text_color='#2ecc71'))
    chart_index = 0
    for _ in range(rows):
        cols = st.columns(max_cols, gap="medium")
        for c in range(max_cols):
            if chart_index >= total_charts:
                break
            with cols[c]:
                nome = "Progresso Geral" if chart_index == len(df_summary) else df_summary.iloc[chart_index]['Disciplinas'].title()
                st.markdown(f'<h3 style="text-align:center;">{nome}</h3>', unsafe_allow_html=True)
                st.altair_chart(disciplina_charts[chart_index], use_container_width=True)
            chart_index += 1

def create_stacked_bar_with_global_progress(df, progresso_geral):
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
    if 'False' not in df_pivot.columns:
        df_pivot['False'] = 0

    df_pivot['Pct_True'] = df_pivot['True'] / df_pivot['Total']
    df_pivot['Pct_False'] = df_pivot['False'] / df_pivot['Total']
    df_pivot = df_pivot.sort_values('Pct_True', ascending=False).reset_index()

    df_melt = df_pivot.melt(
        id_vars=['Disciplinas'], value_vars=['Pct_True', 'Pct_False'],
        var_name='Status', value_name='Percentual'
    )
    df_melt['Status'] = df_melt['Status'].map({'Pct_True': 'Concluído', 'Pct_False': 'Pendente'})

    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])

    base = alt.Chart(df_melt).encode(
        y=alt.Y('Disciplinas:N', sort=df_pivot['Disciplinas'].tolist(), title=None, axis=alt.Axis(labels=True, ticks=True)),
        x=alt.X('Percentual:Q', axis=alt.Axis(format='%', tickCount=11, labels=True, ticks=True)),
        color=alt.Color('Status:N', scale=color_scale, legend=None)
    )

    bars = base.mark_bar(stroke='#d3d3d3', strokeWidth=3)

    text_true = base.transform_filter(
        alt.datum.Status == 'Concluído'
    ).mark_text(
        color='white',
        fontWeight='bold',
        fontSize=12
    ).encode(
        text=alt.Text('Percentual:Q', format='.0%'),
        x=alt.X('Percentual:Q', stack='normalize', offset='center')
    )

    text_false = base.transform_filter(
        alt.datum.Status == 'Pendente'
    ).mark_text(
        color='white',
        fontWeight='bold',
        fontSize=12
    ).encode(
        text=alt.Text('Percentual:Q', format='.0%'),
        x=alt.X('Percentual:Q', stack='normalize', offset='center')
    )

    df_total = pd.DataFrame({
        'Disciplinas': ['Progresso Geral'],
        'Concluido': [progresso_geral / 100],
        'Pendente': [1 - (progresso_geral / 100)]
    }).melt(id_vars=['Disciplinas'], value_vars=['Concluido', 'Pendente'], var_name='Status', value_name='Percentual')
    df_total['Status'] = df_total['Status'].map({'Concluido': 'Concluído', 'Pendente': 'Pendente'})

    base_total = alt.Chart(df_total).encode(
        y=alt.Y('Disciplinas:N', sort=['Progresso Geral'], axis=alt.Axis(labels=True, ticks=False)),
        x=alt.X('Percentual:Q', axis=alt.Axis(format='%', tickCount=11)),
        color=alt.Color('Status:N', scale=color_scale, legend=None)
    )

    bars_total = base_total.mark_bar(stroke='#d3d3d3', strokeWidth=3)

    text_total_true = base_total.transform_filter(
        alt.datum.Status == 'Concluído'
    ).mark_text(
        color='white',
        fontWeight='bold',
        fontSize=12
    ).encode(
        text=alt.Text('Percentual:Q', format='.0%'),
        x=alt.X('Percentual:Q', stack='normalize', offset='center')
    )

    text_total_false = base_total.transform_filter(
        alt.datum.Status == 'Pendente'
    ).mark_text(
        color='white',
        fontWeight='bold',
        fontSize=12
    ).encode(
        text=alt.Text('Percentual:Q', format='.0%'),
        x=alt.X('Percentual:Q', stack='normalize', offset='center')
    )

    final_chart = alt.vconcat(
        bars_total + text_total_true + text_total_false,
        bars + text_true + text_false
    ).resolve_scale(
        y='independent',
        color='independent'
    ).properties(
        height=700,
        title="Percentual de Conteúdos Concluídos e Pendentes por Disciplina (com Progresso Geral)"
    ).configure_view(
        stroke=None
    )

    st.altair_chart(final_chart, use_container_width=True)

def inject_css_e_fireworks():
    st.markdown("""
    <style>
    /* Fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

    body, html, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        margin: 0; padding: 0;
        min-height: 100vh;
        background: #ffffff;
        color: #222831;
        overflow-x: hidden;
    }
    .metric-container {
        background: #f0f5ff;
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 15px #a3bffa90;
        color: #2c3e50;
        text-align: center;
        font-weight: 700;
        transition: box-shadow 0.3s ease;
    }
    .metric-container:hover {
        box-shadow: 0 0 30px #6a8edecc;
    }
    .metric-value {
        font-size: clamp(2.5rem, 5vw, 3rem);
        color: #355e9e;
        margin-bottom: 0.25rem;
        line-height: 1;
    }
    .metric-label {
        font-weight: 600;
        font-size: clamp(1rem, 1.25vw, 1.1rem);
        color: #566e95;
    }
    .altair-chart {
        border: 1px solid #d3d3d3 !important;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 0 15px #a3bffa88;
        background: #e0e9ff;
        margin-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    .streamlit-expanderContent > div {
        color: #2c3e50;
        font-weight: 400;
    }
    footer {
        font-size: 11px !important;
        color: #064820 !important;
        font-weight: 600 !important;
        margin-top: 10px !important;
        text-align: center !important;
        user-select: none !important;
        font-family: 'Inter', sans-serif !important;
        position: relative;
        padding-bottom: 70px; /* espaço para fogos */
    }
    .questao-item {
        margin: 5px 0;
        padding: 9px 14px;
        border-radius: 10px;
        transition: background-color 0.3s ease;
        cursor: pointer;
        font-weight: 600;
        font-size: 1.1rem;
        user-select: none;
    }
    .questao-item:hover {
        background-color: #d0e4ff;
        color: #064270;
    }

    /* Fogos animação no rodapé, subindo até o topo */
    #fireworks-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100vw;
        height: 100vh; /* ocupa toda altura para a animação subir até o topo */
        pointer-events: none;
        z-index: 1;
        overflow: visible;
        background: transparent;
        overflow-x: hidden;
    }
    .firework-footer {
        position: absolute;
        bottom: 0;
        width: 6px;
        height: 6px;
        background: #ff4141;
        border-radius: 50%;
        box-shadow:
            0 0 10px 2px rgba(255, 65, 65, 0.8),
            0 0 20px 5px rgba(255, 99, 99, 0.6);
        animation: rise-footer 4s ease-out infinite, flicker-footer 0.6s linear infinite;
    }
    @keyframes rise-footer {
        0% {
            transform: translateY(0) scale(1);
            opacity: 1;
        }
        100% {
            transform: translateY(-100vh) scale(0.6);
            opacity: 0;
        }
    }
    @keyframes flicker-footer {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.4;
        }
    }
    .firework-footer::after {
        content: "";
        position: absolute;
        left: 50%;
        top: 50%;
        width: 2px;
        height: 12px;
        background: #ffadad;
        border-radius: 1px;
        transform-origin: bottom center;
        box-shadow:
            0 0 6px 1px #ff6f6f;
        animation: spark-footer 0.6s ease-out infinite;
    }
    @keyframes spark-footer {
        0% {
            transform: rotate(0deg) translateY(0);
            opacity: 1;
        }
        100% {
            transform: rotate(25deg) translateY(-14px);
            opacity: 0;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def inject_fireworks_footer():
    st.markdown("<div id='fireworks-footer'></div>", unsafe_allow_html=True)

def add_fireworks_footer(num=30):
    fireworks_html = ""
    for _ in range(num):
        left = random.uniform(0, 98)
        delay = random.uniform(0, 3)
        duration = random.uniform(3.5, 5.0)
        fireworks_html += f"""
        <div class="firework-footer" style="
            left: {left}vw;
            animation-delay: {delay}s;
            animation-duration: {duration}s;
        "></div>
        """
    st.markdown(f"<div style='position:fixed;bottom:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:1;overflow:visible;'>{fireworks_html}</div>", unsafe_allow_html=True)

def rodape_motivacional():
    st.markdown("""
    <footer>
        🚀 Feito com muito amor, coragem e motivação para você! ✨
    </footer>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="📚 Dashboard de Estudos - Concurso 2025",
        page_icon="📚",
        layout="wide"
    )

    # Injeta css geral + animação fogos subindo do rodapé até topo
    inject_css_e_fireworks()
    inject_fireworks_footer()
    add_fireworks_footer(num=30)

    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_topbar_with_logo(dias_restantes)

    df = load_data_with_row_indices()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)

    cols = st.columns(5)
    with cols[0]:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{progresso_geral:.1f}%</div>
                <div class="metric-label">Progresso Geral</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['concluidos']}</div>
                <div class="metric-label">Conteúdos Concluídos</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['pendentes']}</div>
                <div class="metric-label">Conteúdos Pendentes</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['topicos_por_dia']}</div>
                <div class="metric-label">Tópicos/Dia Necessários</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[4]:
        st.markdown(f"""
            <div class="metric-container" style="font-size:1.1rem;">
                <div class="metric-value" style="font-size:1.7rem;">{stats['maior_prioridade']}</div>
                <div class="metric-label">Disciplina Prioritária</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    titulo_com_destaque("📊 Progresso por Disciplina", cor_lateral="#3498db")
    display_6_charts_responsive_with_titles(df_summary, progresso_geral, max_cols=3)

    st.markdown("---")

    titulo_com_destaque("📈 Percentual de Conteúdos Concluídos e Pendentes por Disciplina", cor_lateral="#2980b9")
    create_stacked_bar_with_global_progress(df, progresso_geral)

    st.markdown("---")

    display_conteudos_com_checkboxes(df)

    st.markdown("---")

    titulo_com_destaque("📊 Número de Questões e Peso por Disciplina", cor_lateral="#8e44ad")
    col1, col2 = st.columns([1, 3], gap='medium')

    with col1:
        display_lista_numero_questoes()

    with col2:
        chart_pie = pie_chart_peso_vezes_questoes_com_labels()
        st.altair_chart(chart_pie, use_container_width=True)

    st.markdown("---")

    rodape_motivacional()

if __name__ == "__main__":
    main()
