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

# --- Atualizar status ---
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

# --- Calcular progresso ---
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

# --- Estatísticas ---
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

# --- Título lateral destacado ---
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

# --- Topo com logo e data ---
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

# --- Gráficos de número de questões horizontal ---
def chart_questoes_horizontal(df_ordenado, height):
    bars = alt.Chart(df_ordenado).mark_bar(
        stroke='#d3d3d3', strokeWidth=3
    ).encode(
        y=alt.Y('Disciplinas:N',
                sort=alt.EncodingSortField(field='Questões', order='ascending'),
                title=None,
                axis=alt.Axis(labels=True, ticks=True)),
        x=alt.X('Questões:Q',
                title=None,
                axis=alt.Axis(labels=False, ticks=False, domain=False)),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=[alt.Tooltip('Disciplinas'), alt.Tooltip('Questões', title='Quantidade de Questões')]
    )
    texts = alt.Chart(df_ordenado).mark_text(
        align='left', baseline='middle', dx=3, fontSize=12, color='#064820'
    ).encode(
        y=alt.Y('Disciplinas:N',
                sort=alt.EncodingSortField(field='Questões', order='ascending')),
        x='Questões:Q',
        text='Questões:Q'
    )
    return (bars + texts).properties(
        width=350,
        height=height,
        title="Quantidade de Questões por Disciplina"
    ).configure_axis(
        grid=False,
        domain=False
    )

# --- Gráfico colunas vertical ponderado (peso x questões) ---
def bar_chart_ponderado(height):
    df = pd.DataFrame(ED_DATA)
    df['Questoes_Ponderadas'] = df['Questões'] * df['Peso']

    chart = alt.Chart(df).mark_bar(
        cornerRadius=5, stroke='#d3d3d3', strokeWidth=3
    ).encode(
        x=alt.X('Disciplinas:N', sort='-y', title=None,
                axis=alt.Axis(labelAngle=0, labels=False, ticks=False, domain=False)),
        y=alt.Y('Questoes_Ponderadas:Q', title=None,
                axis=alt.Axis(labels=False, ticks=False, grid=False, domain=False)),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=[alt.Tooltip('Disciplinas', title='Disciplina'),
                 alt.Tooltip('Questoes_Ponderadas', title='Peso × Questões')]
    ).properties(
        width=600,
        height=height,
        title="Peso × Questões por Disciplina"
    )

    text_labels = alt.Chart(df).mark_text(
        dy=-10, fontWeight='bold', fontSize=12, color='black'
    ).encode(
        x=alt.X('Disciplinas:N', sort='-y'),
        y='Questoes_Ponderadas:Q',
        text=alt.Text('Questoes_Ponderadas:Q')
    )

    text_disciplinas = alt.Chart(df).mark_text(
        align='center', dy=12, fontWeight='bold', fontSize=12, color='black'
    ).encode(
        x=alt.X('Disciplinas:N', sort='-y'),
        y=alt.value(height - 15),
        text='Disciplinas:N'
    )

    return (chart + text_labels + text_disciplinas).configure_view(strokeWidth=0)

# --- Função que exibe os dois gráficos lado a lado no último título ---
def display_questoes_e_peso():
    df = pd.DataFrame(ED_DATA)
    if df.empty:
        st.info("Nenhum dado para mostrar gráficos de questões e pesos.")
        return

    titulo_com_destaque("📝 Quantidade de Questões e Peso por Disciplina", cor_lateral="#8e44ad")
    altura = 600

    chart_q = chart_questoes_horizontal(df, altura)
    chart_p = bar_chart_ponderado(altura)

    col1, col2 = st.columns(2)
    with col1:
        st.altair_chart(chart_q, use_container_width=True)
    with col2:
        st.altair_chart(chart_p, use_container_width=True)

# --- Gráfico donut para progresso geral (exemplo) ---
def donut_chart_progresso_geral(progresso_percentual, width=280, height=280,
                               colors=('#2ecc71', '#e74c3c'),
                               inner_radius=70, font_size=32,
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
        base = base.encode(tooltip=[alt.Tooltip('Status'), alt.Tooltip('Valor', format='.1f')])
    donut = base.mark_arc(innerRadius=inner_radius, stroke='#d3d3d3', strokeWidth=3).properties(width=width, height=height)
    text = alt.Chart(pd.DataFrame({'text': [f'{concluido:.1f}%']})).mark_text(
        fontSize=font_size, fontWeight='bold', color=text_color, dy=0
    ).encode(text='text:N').properties(width=width, height=height)
    return (donut + text).configure_view(strokeWidth=0)

# ... (Todas as outras funções como criação dos gráficos donut, stacked bar, checkboxes,
# títulos, CSS, rodapé etc., conforme já definido no código anterior)
# Por exemplo, para mostrar conteúdos com checkboxes:
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
                        sucesso = update_status_in_sheet(worksheet, row['sheet_row'],
                                                         "True" if novo_status else "False")
                        if sucesso:
                            st.success(f"Status do conteúdo '{row['Conteúdos']}' atualizado com sucesso!")
                            load_data_with_row_indices.clear()
                            st.experimental_rerun()
                        else:
                            st.error(f"Falha ao atualizar status do conteúdo '{row['Conteúdos']}'.")
                except Exception as e:
                    st.error(f"Erro inesperado ao atualizar: {e}")

# --- CSS e rodapé, outros gráficos (não repetidos aqui para brevidade) ---

def inject_css():
    st.markdown("""
    <style>
    /* Aqui seu CSS já detalhado */
    </style>
    """, unsafe_allow_html=True)

def rodape_motivacional():
    st.markdown("""
    <footer>
        🚀📚 "O sucesso é a soma de pequenos esforços repetidos dia após dia." 📅✨
        <br><span>Mantenha o foco, você está no caminho certo! 💪😊</span>
    </footer>
    """, unsafe_allow_html=True)

# --- Main ---
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso 2025",
                       page_icon="📚", layout="wide")
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

    st.markdown("---")

    # Aqui coloque outras seções do seu código conforme quiser

    # Última seção: os dois gráficos lado a lado
    display_questoes_e_peso()

    st.markdown("---")

    # Roda o rodapé
    rodape_motivacional()

if __name__ == "__main__":
    main()
