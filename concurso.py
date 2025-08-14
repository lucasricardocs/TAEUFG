# -*- coding: utf-8 -*-
"""
App Streamlit - Dashboard de Estudos TAE UFG 2025
Versão completa com:
- Conexão segura ao Google Sheets (Service Account via st.secrets)
- Cache de recursos e dados
- UI moderna com CSS customizado
- Gráficos Altair (barras empilhadas percentuais, rosca de progresso, pizza de relevância, barras de questões)
- Checklist com atualização direta no Sheets e expanders inteligentes com ícones ▶ / ▼
- Sugestões de estudo do dia
- Simulação de cronograma até a prova (distribuição de pendências)
- Projeção de progresso por dia (mini forecast determinístico simples)
- Exportações (CSV e JSON)
- Rodapé motivacional aleatório
"""

# =============================================================================
# Imports
# =============================================================================
import warnings
warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

import os
import json
import math
import random
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import altair as alt
import streamlit as st

import gspread
from gspread.exceptions import SpreadsheetNotFound, APIError
from google.oauth2.service_account import Credentials

# =============================================================================
# Localização (datas em pt-BR)
# =============================================================================
try:
    import locale
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except Exception:
    pass

# =============================================================================
# Configurações globais do App
# =============================================================================
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
CONCURSO_DATE = datetime(2025, 9, 28)

ED_DATA = {
    'Disciplinas': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS'],
    'Total_Conteudos': [17, 14, 14, 11, 21],
    'Peso': [2, 1, 1, 1, 3],
    'Questões': [10, 5, 5, 10, 20]
}

MOTIVATIONAL_QUOTES = [
    "🚀 O sucesso é a soma de pequenos esforços repetidos dia após dia.",
    "🎯 O único lugar onde o sucesso vem antes do trabalho é no dicionário.",
    "💡 Acredite em si mesmo, e você já está no meio do caminho.",
    "🏃 A persistência é o caminho do êxito.",
    "🌟 O futuro pertence àqueles que acreditam na beleza de seus sonhos.",
    "🏆 A dedicação de hoje é a vitória de amanhã.",
    "🌱 Pequenos passos, grandes conquistas.",
    "🔥 Nunca pare de lutar pelo que você quer na vida.",
    "🧠 Estude com disciplina e vença com facilidade.",
    "✨ Não espere pela sorte, crie-a com seu esforço."
]

# =============================================================================
# Utilitários
# =============================================================================
def format_date_br(date_obj: datetime) -> str:
    """Retorna data no formato 'dd de mês de aaaa' em pt-BR."""
    meses_pt = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    try:
        return date_obj.strftime(f'%d de {meses_pt[date_obj.month-1]} de %Y')
    except Exception:
        return date_obj.strftime('%d/%m/%Y')


def clamp(value, min_v=0.0, max_v=100.0):
    """Limita valor entre min_v e max_v."""
    return max(min_v, min(max_v, value))


def pct(numerador, denominador):
    """Retorna percentual seguro."""
    return (numerador / denominador * 100.0) if denominador else 0.0


# =============================================================================
# Autenticação e acesso ao Google Sheets
# =============================================================================
@st.cache_resource(show_spinner="Conectando ao Google Sheets...")
def get_gspread_client():
    """Autentica usando Service Account via st.secrets."""
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/spreadsheets.readonly'
    ]
    try:
        credentials_dict = st.secrets["gcp_service_account"]
    except Exception as e:
        st.error("❌ st.secrets['gcp_service_account'] não configurado. Adicione as credenciais no painel de Secrets.")
        return None
    try:
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Erro ao autenticar no Google Sheets: {e}")
        return None


@st.cache_resource(show_spinner=False)
def get_worksheet():
    """Abre a planilha e retorna a aba WORKSHEET_NAME."""
    client = get_gspread_client()
    if not client:
        return None
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet.worksheet(WORKSHEET_NAME)
    except SpreadsheetNotFound:
        st.error("❌ Planilha não encontrada. Verifique o SPREADSHEET_ID.")
    except Exception as e:
        st.error(f"❌ Erro ao acessar a aba '{WORKSHEET_NAME}': {e}")
    return None


# =============================================================================
# Carregamento e transformação de dados
# =============================================================================
@st.cache_data(ttl=300, show_spinner="Carregando dados dos estudos...")
def load_data_with_row_indices() -> pd.DataFrame:
    """Lê dados do Sheets e retorna DataFrame padronizado + sheet_row."""
    worksheet = get_worksheet()
    if not worksheet:
        return pd.DataFrame()

    try:
        data = worksheet.get_all_values()
        if len(data) < 2:
            return pd.DataFrame()

        df = pd.DataFrame(data[1:], columns=data[0])
        required_cols = ['Disciplinas', 'Conteúdos', 'Status']
        if not all(col in df.columns for col in required_cols):
            st.error(f"❌ Colunas obrigatórias faltando. Verifique se a planilha tem: {required_cols}")
            return pd.DataFrame()

        df = df[required_cols].copy()
        df['Disciplinas'] = df['Disciplinas'].str.strip().str.upper()
        df['Conteúdos'] = df['Conteúdos'].str.strip()
        df['Status'] = df['Status'].astype(str).str.strip().str.lower().map({'true': True, 'false': False, '1': True, '0': False})
        df.dropna(subset=['Status'], inplace=True)

        # sheet_row = índice real na planilha (cabeçalho é linha 1)
        df.reset_index(inplace=True)
        df['sheet_row'] = df['index'] + 2
        df.drop('index', axis=1, inplace=True)

        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Falha ao carregar ou processar dados: {e}")
        return pd.DataFrame()


# =============================================================================
# Escrita no Google Sheets
# =============================================================================
def update_status_in_sheet(sheet, row_number: int, new_status: str) -> bool:
    """Atualiza coluna 'Status' na linha informada."""
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


def handle_checkbox_change(worksheet, row_number, key, conteudo_nome):
    """Callback do Streamlit para atualizar status e recarregar cache."""
    novo_status = st.session_state.get(key, False)
    if update_status_in_sheet(worksheet, row_number, "TRUE" if novo_status else "FALSE"):
        st.toast(f"✅ Status de '{conteudo_nome}' atualizado!", icon="✅")
        st.cache_data.clear()
        st.experimental_rerun()  # st.rerun() (para versões mais novas)
    else:
        st.toast(f"❌ Falha ao atualizar '{conteudo_nome}'.", icon="❌")
        st.session_state[key] = not novo_status


# =============================================================================
# Cálculos de progresso e estatísticas
# =============================================================================
def calculate_progress(df: pd.DataFrame):
    """Calcula progresso por disciplina ponderado por 'Peso'."""
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


def calculate_stats(df_summary: pd.DataFrame, df_full: pd.DataFrame):
    """Resumo de métricas rápidas."""
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    concluidos = int(df_summary['Conteudos_Concluidos'].sum())
    pendentes = int(df_summary['Conteudos_Pendentes'].sum())
    topicos_por_dia = round(pendentes / dias_restantes, 1) if dias_restantes > 0 else 0

    maior_prioridade = "N/A"
    if pendentes > 0:
        df_summary = df_summary.copy()
        df_summary['Progresso_Percentual'] = (df_summary['Conteudos_Concluidos'] / df_summary['Total_Conteudos'].replace(0, 1)) * 100
        df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Percentual']) * df_summary['Peso']
        maior_prioridade = df_summary.loc[df_summary['Prioridade_Score'].idxmax()]['Disciplinas']

    return {
        'dias_restantes': dias_restantes,
        'concluidos': int(concluidos),
        'pendentes': int(pendentes),
        'topicos_por_dia': topicos_por_dia,
        'maior_prioridade': maior_prioridade,
    }


# =============================================================================
# UI / CSS
# =============================================================================
def render_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        html, body, [class*="st-"] { font-family: 'Roboto', sans-serif; }
        .top-bar-container {
            display: flex; align-items: center; justify-content: space-between;
            background: linear-gradient(135deg, #F8F9FE 0%, #EAEFFF 100%);
            border: 1px solid #d1d9e6; border-radius: 16px; padding: 1.25rem 2rem;
            margin-bottom: 2.0rem; box-shadow: 0 8px 32px rgba(90,97,125,0.1);
        }
        .logo-title-group { display: flex; align-items: center; gap: 1.5rem; }
        .logo-title-group img { height: 65px; }
        .title-text h1 { color: #1e2a38; margin: 0; font-size: 1.9rem; font-weight: 700; }
        .title-text p { color: #5a677d; margin: 0; font-weight: 500; }
        .countdown-group { text-align: right; }
        .countdown-box {
            background-color: #e74c3c; color: white; padding: 0.7rem 1.2rem;
            border-radius: 12px; font-size: 1.6rem; font-weight: bold;
            margin-bottom: 0.5rem; display: inline-block;
        }
        .date-text { margin: 0; font-weight: 500; color: #5a677d; font-size: 0.9rem; }
        .section-title { border-left: 5px solid #8e44ad; padding: 0.5rem 1rem; background: #F0F2F6;
            border-radius: 8px; margin: 2rem 0 1.5rem 0; }
        .section-title h2 { color: #2c3e50; margin-block-start: 0; margin-block-end: 0; }
        .study-suggestion-box {
            background-color: #e8f5e9; border-left: 5px solid #2ecc71; padding: 1rem;
            border-radius: 8px; margin-top: 1.0rem; margin-bottom: 2rem;
        }
        .metric-container { background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e0e0e0; }
        .expander-title-ok { color: #2ecc71; font-weight: 700; }
        .expander-title-pending { color: #e67e22; font-weight: 700; }
        .pill {
            display:inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.8rem;
            border: 1px solid #d1d9e6; background: #fff; color: #333; margin-left: 6px;
        }
    </style>
    """, unsafe_allow_html=True)


def titulo_com_destaque(texto, cor_lateral="#8e44ad"):
    st.markdown(
        f"""
        <div class="section-title" style="border-left-color:{cor_lateral}">
            <h2>{texto}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_topbar_with_logo(dias_restantes):
    st.markdown(f"""
    <div class="top-bar-container">
        <div class="logo-title-group">
            <img src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG"/>
            <div class="title-text">
                <h1>Dashboard de Estudos</h1>
                <p>Concurso TAE UFG 2025</p>
            </div>
        </div>
        <div class="countdown-group">
            <div class="countdown-box">⏰ Faltam {dias_restantes} dias!</div>
            <p class="date-text">{format_date_br(datetime.now())}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def display_containers_metricas(stats, progresso_geral):
    cols = st.columns(5)
    cols[0].metric("🎯 Progresso Ponderado", f"{progresso_geral:.1f}%")
    cols[1].metric("✅ Concluídos", f"{stats['concluidos']}")
    cols[2].metric("⏳ Pendentes", f"{stats['pendentes']}")
    cols[3].metric("🏃 Ritmo Necessário", f"{stats['topicos_por_dia']} tópicos/dia")
    foco = stats['maior_prioridade'].title() if isinstance(stats['maior_prioridade'], str) else str(stats['maior_prioridade'])
    cols[4].metric("⭐ Foco Principal", foco)


# =============================================================================
# Gráficos Altair
# =============================================================================
def create_percentual_conclusao_por_disciplina(df_summary):
    df_melted = df_summary.melt(
        id_vars=['Disciplinas'],
        value_vars=['Conteudos_Concluidos', 'Conteudos_Pendentes'],
        var_name='Status',
        value_name='Contagem'
    )
    df_melted['Status'] = df_melted['Status'].map({
        'Conteudos_Concluidos': 'Concluído',
        'Conteudos_Pendentes': 'Pendente'
    })
    df_melted['Percentual'] = df_melted.groupby('Disciplinas')['Contagem'].transform(lambda x: x / x.sum())

    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])

    base = alt.Chart(df_melted).encode(
        y=alt.Y('Disciplinas:N', sort=None, axis=alt.Axis(title=None)),
        color=alt.Color('Status:N', scale=color_scale, legend=None),
        tooltip=[
            alt.Tooltip('Disciplinas:N', title='Disciplina'),
            alt.Tooltip('Status:N', title='Status'),
            alt.Tooltip('Percentual:Q', title='Percentual', format='.1%'),
            alt.Tooltip('Contagem:Q', title='Quantidade')
        ]
    )

    bars = base.mark_bar(stroke='#d3d3d3', strokeWidth=2).encode(
        x=alt.X('Percentual:Q', stack='normalize', axis=alt.Axis(format='%', title=None, labels=False))
    )

    text = base.mark_text(
        align='center',
        baseline='middle',
        color='black',
        fontWeight='bold',
        fontSize=14
    ).encode(
        x=alt.X('Percentual:Q', stack='normalize'),
        text=alt.Text('Percentual:Q', format='.0%')
    ).transform_filter(
        alt.datum.Contagem > 0
    )

    chart = (bars + text).properties(
        height=420,
        title=alt.TitleParams(text='Evolução por Disciplina', anchor='middle', fontSize=18)
    ).configure_axis(
        grid=False,
        tickSize=0,
        domain=False
    ).configure_view(
        strokeWidth=0
    )
    return chart


def create_progress_donut(source_df, title):
    total = float(source_df['Valor'].sum())
    concl = float(source_df.loc[source_df['Status'] == 'Concluído', 'Valor'].sum())
    percent_text = f"{(concl / total * 100) if total > 0 else 0:.1f}%"

    base = alt.Chart(source_df).mark_arc(
        innerRadius=55, cornerRadius=5, stroke='#d3d3d3', strokeWidth=1
    ).encode(
        theta=alt.Theta("Valor:Q"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c']), legend=None),
        tooltip=['Status', alt.Tooltip('Valor', title="Conteúdos")]
    )
    text = alt.Chart(pd.DataFrame({'text': [percent_text]})).mark_text(size=24, fontWeight='bold').encode(text='text:N')
    return (base + text).properties(title=alt.TitleParams(text=title, anchor='middle', fontSize=16, dy=-10))


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
                    chart_info = charts_data[i + j]
                    donut = create_progress_donut(chart_info['df'], chart_info['title'])
                    st.altair_chart(donut, use_container_width=True)
            else:
                cols[j].empty()


def create_questoes_bar_chart(ed_data):
    df = pd.DataFrame(ed_data)
    bars = alt.Chart(df).mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4, stroke='#d3d3d3', strokeWidth=1
    ).encode(
        x=alt.X('Disciplinas:N', sort=None, title=None, axis=None),
        y=alt.Y('Questões:Q', title=None, axis=None),
        color=alt.Color('Disciplinas:N', legend=alt.Legend(title="Disciplinas", orient="bottom")),
        tooltip=['Disciplinas', 'Questões']
    )
    text = bars.mark_text(align='center', baseline='bottom', dy=-5, color='black', fontWeight='bold').encode(
        text='Questões:Q'
    )
    return (bars + text).properties(
        height=420,
        title=alt.TitleParams("Número de Questões", anchor='middle', fontSize=18)
    )


def create_relevancia_pie_chart(ed_data):
    df = pd.DataFrame(ed_data)
    df['Relevancia'] = df['Peso'] * df['Questões']
    df['Percentual'] = (df['Relevancia'] / df['Relevancia'].sum()) * 100
    base = alt.Chart(df).encode(
        theta=alt.Theta("Relevancia:Q", stack=True),
        color=alt.Color("Disciplinas:N", legend=alt.Legend(
            orient="bottom", title="Disciplinas", titleFontSize=14, labelFontSize=12
        )),
        order=alt.Order("Relevancia:Q", sort="descending"),
        tooltip=[alt.Tooltip('Disciplinas:N', title='Disciplina'),
                 alt.Tooltip('Percentual:Q', title='Percentual', format='.1f%%'),
                 alt.Tooltip('Relevancia:Q', title='Relevância (Peso×Questões)')]
    )
    pie = base.mark_arc(innerRadius=70, cornerRadius=5, stroke='#d3d3d3', strokeWidth=1)
    text = base.mark_text(radius=85, size=12, color="black", fontWeight='bold').encode(
        text=alt.Text('Percentual:Q', format='.1f%'),
        theta=alt.Theta("Relevancia:Q", stack=True)
    )
    return (pie + text).properties(
        height=420,
        title=alt.TitleParams("Relevância (Peso × Questões)", anchor='middle', fontSize=18)
    )


# =============================================================================
# Checklist com expanders ▶ / ▼ e título colorido
# =============================================================================
def expander_title(disciplina: str, concluidos: int, total: int) -> str:
    """Monta o título do expander com ícone e cor."""
    if concluidos < total:
        icon = "▼"
        css_class = "expander-title-pending"
    else:
        icon = "▶"
        css_class = "expander-title-ok"

    ratio = f"{concluidos} / {total} concluídos"
    pill = f"<span class='pill'>{ratio}</span>"
    return f"<span class='{css_class}'>{icon} <strong>{disciplina.title()}</strong></span> {pill}"


def display_conteudos_com_checkboxes(df):
    """Renderiza os conteúdos por disciplina com checkboxes e atualiza no Sheets."""
    worksheet = get_worksheet()
    if not worksheet:
        return

    resumo_disciplina = df.groupby('Disciplinas')['Status'].agg(['sum', 'count']).reset_index()
    resumo_disciplina['sum'] = resumo_disciplina['sum'].astype(int)

    for disc in sorted(df['Disciplinas'].unique()):
        conteudos_disciplina = df[df['Disciplinas'] == disc]
        resumo_disc = resumo_disciplina[resumo_disciplina['Disciplinas'] == disc]
        concluidos = int(resumo_disc['sum'].iloc[0])
        total = int(resumo_disc['count'].iloc[0])

        expandir_automatico = concluidos < total
        header_html = expander_title(disc, concluidos, total)

        with st.expander(label=None, expanded=expandir_automatico):
            st.markdown(header_html, unsafe_allow_html=True)
            st.markdown("---")
            for _, row in conteudos_disciplina.iterrows():
                checkbox_key = f"cb_{int(row['sheet_row'])}"
                st.checkbox(
                    label=row['Conteúdos'],
                    value=bool(row['Status']),
                    key=checkbox_key,
                    on_change=handle_checkbox_change,
                    kwargs={
                        'worksheet': worksheet,
                        'row_number': int(row['sheet_row']),
                        'key': checkbox_key,
                        'conteudo_nome': row['Conteúdos']
                    }
                )


# =============================================================================
# Sugestão de estudo e rodapé motivacional
# =============================================================================
def display_study_suggestion(stats, df_summary):
    """Exibe sugestão baseada na maior prioridade e no ritmo necessário."""
    foco = stats['maior_prioridade']
    if not isinstance(foco, str) or foco == "N/A":
        foco_texto = "Escolha qualquer disciplina para começar e ganhar tração."
    else:
        # opcional: pegar os tópicos pendentes dessa disciplina
        linha = df_summary[df_summary['Disciplinas'] == foco]
        if not linha.empty:
            pend = int(linha['Conteudos_Pendentes'].iloc[0])
            foco_texto = f"Priorize **{foco.title()}**. Há **{pend}** tópicos pendentes."
        else:
            foco_texto = f"Priorize **{foco.title()}**."

    st.markdown(f"""
    <div class="study-suggestion-box">
        <strong>📌 Foco de hoje:</strong> {foco_texto}
        <br>
        Ritmo recomendado: <strong>{stats['topicos_por_dia']}</strong> tópicos/dia até a prova.
    </div>
    """, unsafe_allow_html=True)


def rodape_motivacional():
    """Mensagem motivacional aleatória."""
    frase = random.choice(MOTIVATIONAL_QUOTES)
    st.markdown(f"""
    <div style="margin-top: 2rem; padding: 1rem; text-align: center;
                font-size: 1.05rem; color: #555; background-color: #f9f9f9;
                border-radius: 8px; border: 1px solid #eee;">
        {frase}
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# Projeções e simulações
# =============================================================================
def simulate_schedule(df_summary: pd.DataFrame, start_date: datetime, end_date: datetime, max_per_day: int = 5):
    """
    Simula a distribuição dos tópicos pendentes por dia, simples e determinística.
    Retorna DataFrame: data, disciplina, alocado_no_dia.
    """
    if start_date > end_date:
        return pd.DataFrame(columns=['data', 'disciplina', 'alocado_no_dia'])

    dias = (end_date - start_date).days + 1
    calendar = []
    pendencias = []

    # Gera lista de pendências por disciplina, ponderando por Peso
    for _, row in df_summary.iterrows():
        disc = row['Disciplinas']
        pend = int(row['Conteudos_Pendentes'])
        peso = int(row['Peso'])
        if pend > 0:
            pendencias.append({'disc': disc, 'pend': pend, 'peso': peso})

    # Ordena por maior peso (prioridade)
    pendencias.sort(key=lambda x: (-x['peso'], x['disc']))

    # Distribui dia a dia
    pointer = 0
    for d in range(dias):
        quota = max_per_day
        dia = start_date + timedelta(days=d)
        alocados = []
        while quota > 0 and any(p['pend'] > 0 for p in pendencias):
            blocos = [p for p in pendencias if p['pend'] > 0]
            if not blocos:
                break
            # round-robin entre as maiores prioridades
            bloco = blocos[pointer % len(blocos)]
            bloco['pend'] -= 1
            quota -= 1
            alocados.append(bloco['disc'])
            pointer += 1
        for disc in alocados:
            calendar.append({'data': dia.date(), 'disciplina': disc, 'alocado_no_dia': 1})

    return pd.DataFrame(calendar)


def build_progress_projection(df_summary: pd.DataFrame, start_date: datetime, end_date: datetime, max_per_day=5):
    """
    Projeta o % de conclusão acumulado ao longo dos dias com base na simulação.
    """
    sched = simulate_schedule(df_summary, start_date, end_date, max_per_day)
    if sched.empty:
        return pd.DataFrame(columns=['data', 'progresso_pct'])

    total_conteudos = int(df_summary['Total_Conteudos'].sum())
    concl_iniciais = int(df_summary['Conteudos_Concluidos'].sum())

    df_proj = sched.groupby('data')['alocado_no_dia'].sum().reset_index()
    df_proj = df_proj.sort_values('data')

    acumulado = []
    soma = 0
    for _, row in df_proj.iterrows():
        soma += int(row['alocado_no_dia'])
        pct_ = pct(concl_iniciais + soma, total_conteudos)
        acumulado.append({'data': row['data'], 'progresso_pct': clamp(pct_, 0, 100)})

    return pd.DataFrame(acumulado)


def plot_projection_chart(df_proj: pd.DataFrame):
    if df_proj.empty:
        st.info("Sem dados para projeção.")
        return
    chart = alt.Chart(df_proj).mark_line(point=True).encode(
        x=alt.X('data:T', title='Data'),
        y=alt.Y('progresso_pct:Q', title='Progresso projetado (%)'),
        tooltip=[alt.Tooltip('data:T', title='Data', format='%d/%m/%Y'),
                 alt.Tooltip('progresso_pct:Q', title='Progresso (%)', format='.1f')]
    ).properties(
        height=360,
        title=alt.TitleParams("Projeção de Progresso até a prova", anchor='middle', fontSize=18)
    )
    st.altair_chart(chart, use_container_width=True)


# =============================================================================
# Exportações
# =============================================================================
def export_dataframes(df_raw: pd.DataFrame, df_summary: pd.DataFrame):
    """Cria botões para exportar CSV/JSON do status atual."""
    col1, col2 = st.columns(2)
    # RAW
    csv_raw = df_raw.to_csv(index=False).encode('utf-8')
    json_raw = df_raw.to_json(orient='records', force_ascii=False).encode('utf-8')
    col1.download_button("⬇️ Exportar RAW (CSV)", csv_raw, file_name="estudos_raw.csv", mime="text/csv")
    col1.download_button("⬇️ Exportar RAW (JSON)", json_raw, file_name="estudos_raw.json", mime="application/json")

    # SUMMARY
    csv_sum = df_summary.to_csv(index=False).encode('utf-8')
    json_sum = df_summary.to_json(orient='records', force_ascii=False).encode('utf-8')
    col2.download_button("⬇️ Exportar RESUMO (CSV)", csv_sum, file_name="estudos_resumo.csv", mime="text/csv")
    col2.download_button("⬇️ Exportar RESUMO (JSON)", json_sum, file_name="estudos_resumo.json", mime="application/json")


# =============================================================================
# Sidebar
# =============================================================================
def render_sidebar(df_summary):
    st.sidebar.header("⚙️ Configurações")
    hoje = datetime.now().date()
    st.sidebar.write(f"Hoje: **{format_date_br(datetime.now())}**")

    max_per_day = st.sidebar.slider("Tópicos máximos por dia (simulação)", 1, 20, 5, step=1)
    start_date = st.sidebar.date_input("Início simulação", hoje)
    end_date = st.sidebar.date_input("Fim simulação", CONCURSO_DATE.date())

    st.sidebar.markdown("---")
    disciplina_focus = st.sidebar.selectbox("Filtrar disciplina (gráficos e checklist)", ['Todas'] + df_summary['Disciplinas'].tolist())
    st.sidebar.markdown("---")
    st.sidebar.caption("Dica: marque/desmarque itens no checklist para atualizar os gráficos em tempo real.")

    return max_per_day, start_date, end_date, disciplina_focus


# =============================================================================
# Main
# =============================================================================
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso TAE", page_icon="📚", layout="wide")
    render_custom_css()

    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_topbar_with_logo(dias_restantes)

    # Dados
    df_raw = load_data_with_row_indices()
    if df_raw.empty:
        st.info("👋 Bem-vindo! Parece que sua planilha de estudos está vazia. Adicione os conteúdos na sua Google Sheet para começar a monitorar seu progresso aqui.")
        st.stop()

    # Resumo e progresso
    df_summary, progresso_geral = calculate_progress(df_raw)

    # Sidebar
    max_per_day, start_date, end_date, disciplina_focus = render_sidebar(df_summary)

    # Filtro opcional por disciplina
    if disciplina_focus and disciplina_focus != 'Todas':
        df_raw_filtered = df_raw[df_raw['Disciplinas'] == disciplina_focus]
        df_summary_filtered = df_summary[df_summary['Disciplinas'] == disciplina_focus]
    else:
        df_raw_filtered = df_raw.copy()
        df_summary_filtered = df_summary.copy()

    # Métricas
    stats = calculate_stats(df_summary, df_raw)
    display_containers_metricas(stats, progresso_geral)

    # Gráfico percentual por disciplina
    titulo_com_destaque("📊 Compleção por Disciplina", cor_lateral="#3498db")
    st.altair_chart(create_percentual_conclusao_por_disciplina(df_summary_filtered), use_container_width=True)

    # Donuts
    titulo_com_destaque("📈 Progresso Individual", cor_lateral="#3498db")
    display_donuts_grid(df_summary_filtered, progresso_geral if disciplina_focus == 'Todas' else pct(
        df_summary_filtered['Conteudos_Concluidos'].sum(),
        df_summary_filtered['Total_Conteudos'].sum()
    ))

    # Checklist
    titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#8e44ad")
    display_conteudos_com_checkboxes(df_raw_filtered)

    # Análise Estratégica
    titulo_com_destaque("📝 Análise Estratégica da Prova", cor_lateral="#e67e22")
    colA, colB = st.columns(2, gap="large")
    with colA:
        st.altair_chart(create_questoes_bar_chart(ED_DATA), use_container_width=True)
    with colB:
        st.altair_chart(create_relevancia_pie_chart(ED_DATA), use_container_width=True)

    # Sugestão do dia
    titulo_com_destaque("💡 Sugestão de Estudo para Hoje", cor_lateral="#2ecc71")
    display_study_suggestion(stats, df_summary)

    # Projeção
    titulo_com_destaque("📅 Projeção de Progresso", cor_lateral="#9b59b6")
    df_proj = build_progress_projection(df_summary, datetime.combine(start_date, datetime.min.time()),
                                        datetime.combine(end_date, datetime.min.time()), max_per_day=max_per_day)
    plot_projection_chart(df_proj)

    # Exportações
    titulo_com_destaque("⬇️ Exportações", cor_lateral="#2c3e50")
    export_dataframes(df_raw, df_summary)

    # Rodapé motivacional
    rodape_motivacional()


# =============================================================================
# Execução
# =============================================================================
if __name__ == "__main__":
    main()
