# -*- coding: utf-8 -*-
import json
import pandas as pd
import numpy as np
import streamlit as st
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import warnings
import plotly.graph_objects as go

warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

try:
    import locale
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass

# Configurações globais
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
CONCURSO_DATE = datetime(2025, 9, 28)

ED_DATA = {
    'Disciplinas': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS'],
    'Total_Conteudos': [20, 15, 10, 15, 30],
    'Peso': [2, 1, 1, 1, 3],
    'Questões': [10, 5, 5, 10, 20]
}

# --- Google Sheets client and data loading ----
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

# --- Cálculo dos dados ---
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

# --- Estilo e containers ---
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
    </div>""", unsafe_allow_html=True)

def render_topbar_with_logo(dias_restantes):
    hoje_texto = datetime.now().strftime('%d de %B de %Y')
    st.markdown(f"""
    <style>
        .topbar-container {{
            display: flex;
            align-items: center;
            background-color: #f5f5f5;
            border-radius: 12px;
            padding: 0 3vw;
            min-height: 180px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25);
            margin-bottom: 10px;
            font-family: 'Inter', sans-serif;
            flex-wrap: wrap;
            gap: 1rem;
            position: relative;
        }}
        .topbar-logo {{
            height: 120px;
            flex-shrink: 0;
            margin-right: 2vw;
        }}
        .topbar-text {{
            font-size: clamp(1.4rem, 3vw, 2.5rem);
            font-weight: 700;
            color: #2c3e50;
            white-space: nowrap;
            line-height: 1.2;
            flex-grow: 1;
            min-width: 150px;
        }}
        .topbar-date {{
            position: absolute;
            top: 8px;
            right: 16px;
            font-size: clamp(9px, 1vw, 11px);
            font-weight: 600;
            color: #2c3e50;
            user-select: none;
            white-space: nowrap;
        }}
        @media (max-width: 600px) {{
            .topbar-container {{
                min-height: 140px;
                padding: 0 2vw;
            }}
            .topbar-logo {{
                height: 90px;
                margin-right: 1vw;
            }}
            .topbar-text {{
                font-size: clamp(1.1rem, 4vw, 2rem);
                white-space: normal;
            }}
            .topbar-date {{
                font-size: clamp(8px, 1.5vw, 10px);
            }}
        }}
    </style>
    <div class="topbar-container">
        <img class="topbar-logo" src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG" />
        <div class="topbar-text">⏰ Faltam {dias_restantes} dias para o concurso de TAE</div>
        <div class="topbar-date">Goiânia, {hoje_texto}</div>
    </div>
    """, unsafe_allow_html=True)

def display_containers_metricas(stats, progresso_geral):
    cores_metricas = [
        "#cbe7f0",
        "#fdd8d6",
        "#d1f2d8",
        "#fdebd0",
        "#d7c7f7",
    ]
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');
            .metric-container {
                font-family: 'Inter', sans-serif !important;
                background: var(--bg-color);
                border-radius: 16px;
                padding: 1rem 1.2rem;
                box-shadow: 0 4px 15px #a3bffa90;
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
                cursor: default;
                transition: box-shadow 0.3s ease, transform 0.3s ease;
                margin-bottom: 10px;
            }
            .metric-container:hover {
                box-shadow: 0 8px 30px #5275e1cc;
                transform: scale(1.05);
                z-index: 10;
            }
            .metric-value {
                color: #355e9e;
                margin-bottom: 0.25rem;
                font-size: 16px !important;
            }
            .metric-label {
                font-weight: 600;
                color: #566e95;
                font-size: 16px !important;
            }
            @media(max-width: 768px) {
                .metric-row {
                    flex-direction: column !important;
                    height: auto !important;
                }
                .metric-container {
                    height: 130px !important;
                    margin-bottom: 12px !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="display:flex; gap:1rem; justify-content:center;" class="metric-row">', unsafe_allow_html=True)
    cols = st.columns(5, gap="small")
    values_labels = [
        (f"{progresso_geral:.1f}%", "Progresso Geral"),
        (f"{stats['concluidos']}", "Conteúdos Concluídos"),
        (f"{stats['pendentes']}", "Conteúdos Pendentes"),
        (f"{stats['topicos_por_dia']}", "Tópicos/Dia Necessários"),
        (stats['maior_prioridade'], "Disciplina Prioritária"),
    ]
    for idx, col in enumerate(cols):
        valor, label = values_labels[idx]
        cor = cores_metricas[idx]
        with col:
            st.markdown(
                f"""
                <div class="metric-container" style="background: {cor};">
                    <div class="metric-value">{valor}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

# --- Gráfico histograma horizontal sem título, largura e altura adaptáveis ---
def create_histograma_horizontal_simplificado(df):
    disciplinas = df['Disciplinas'].tolist()
    concluidos = df['Conteudos_Concluidos'].tolist()
    pendentes = df['Conteudos_Pendentes'].tolist()
    total = np.array(concluidos) + np.array(pendentes)
    pct_concluidos = np.divide(concluidos, total, out=np.zeros_like(concluidos, dtype=float), where=total != 0) * 100
    pct_pendentes = 100 - pct_concluidos

    fig = go.Figure(data=[
        go.Bar(y=disciplinas, x=pct_concluidos, name='Concluídos', marker_color='#2ecc71', orientation='h', text=[f"{val:.1f}%" for val in pct_concluidos], textposition='inside', textfont=dict(color='white')),
        go.Bar(y=disciplinas, x=pct_pendentes, name='Pendentes', marker_color='#e74c3c', orientation='h', text=[f"{val:.1f}%" for val in pct_pendentes], textposition='inside', textfont=dict(color='white'))
    ])

    fig.update_layout(
        barmode='stack',
        margin=dict(l=100, r=40, t=40, b=20),
        showlegend=False,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=True, showgrid=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title={
            'text': "Percentual de Conteúdos Concluídos e Pendentes por Disciplina",
            'x': 0.5,
            'xanchor': 'center',
            'font': dict(family='Arial, sans-serif', size=18, color='#2c3e50', weight='bold'),
        }
    )

    return fig

def display_histograma_horizontal_simplificado(fig):
    st.plotly_chart(fig, use_container_width=True)

# --- Containers animados para 'Número de Questões e Peso por Disciplina' ---
def display_containers_questoes_peso(ed_data):
    df = pd.DataFrame(ed_data)
    cores_metricas = [
        "#cbe7f0",
        "#fdd8d6",
        "#d1f2d8",
        "#fdebd0",
        "#d7c7f7",
    ]
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');
            .question-weight-container {
                font-family: 'Inter', sans-serif !important;
                background: var(--bg-color);
                border-radius: 16px;
                padding: 1rem 1.2rem;
                box-shadow: 0 4px 15px #a3bffa90;
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
                cursor: default;
                transition: box-shadow 0.3s ease, transform 0.3s ease;
                margin-bottom: 10px;
            }
            .question-weight-container:hover {
                box-shadow: 0 8px 30px #5275e1cc;
                transform: scale(1.05);
                z-index: 10;
            }
            .question-weight-value {
                color: #355e9e;
                margin-bottom: 0.25rem;
                font-size: 24px !important;
            }
            .question-weight-label {
                font-weight: 600;
                color: #566e95;
                font-size: 16px !important;
            }
            @media(max-width: 768px) {
                .question-weight-row {
                    flex-direction: column !important;
                    height: auto !important;
                }
                .question-weight-container {
                    height: 130px !important;
                    margin-bottom: 12px !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div style="display:flex; gap:1rem; justify-content:center;" class="question-weight-row">', unsafe_allow_html=True)
    cols = st.columns(5, gap="small")
    for i, col in enumerate(cols):
        d = df.iloc[i]
        with col:
            st.markdown(
                f"""
                <div class="question-weight-container" style="background: {cores_metricas[i]};">
                    <div class="question-weight-value">{d['Questões']}</div>
                    <div class="question-weight-label">{d['Disciplinas'].title()}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

# --- Gráfico de rosca animado e interativo usando Plotly ---
def pie_chart_peso_vezes_questoes_animado(ed_data):
    df = pd.DataFrame(ed_data)
    df['Peso_vezes_Questoes'] = df['Peso'] * df['Questões']
    total = df['Peso_vezes_Questoes'].sum()
    df['Percentual'] = df['Peso_vezes_Questoes'] / total
    df = df.sort_values('Peso_vezes_Questoes', ascending=False).reset_index(drop=True)

    cores = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']

    num_frames = 40
    labels_final = df.apply(lambda r: f"{r['Disciplinas']}<br>({r['Percentual']:.1%})", axis=1).tolist()

    frames = []
    for i in range(num_frames):
        animated_values = []
        for idx, val in enumerate(df['Peso_vezes_Questoes']):
            slice_start_frame = idx * (num_frames // len(df))
            if i >= slice_start_frame:
                slice_progress = min(1.0, (i - slice_start_frame) / (num_frames // len(df)))
                animated_values.append(val * slice_progress)
            else:
                animated_values.append(0)

        texts = labels_final if i >= (num_frames - 5) else [""] * len(df)

        frame = go.Frame(
            data=[go.Pie(
                labels=df['Disciplinas'],
                values=animated_values,
                hole=0.4,
                text=texts,
                textinfo='text',
                textposition='inside',
                textfont=dict(size=14, color='black', family='sans-serif'),
                marker=dict(colors=cores[:len(df)], line=dict(color='#d3d3d3', width=3)),
                hovertemplate='<b>%{label}</b><br>Valor: %{value}<br>Percentual: %{percent}<extra></extra>',
                rotation=90
            )],
            name=str(i)
        )
        frames.append(frame)

    fig = go.Figure(data=frames[0].data, frames=frames)
    fig.update_layout(
        title={
            'text': "Número de Questões e Peso por Disciplina",
            'x': 0.5,
            'xanchor': 'center',
            'font': dict(family='Arial, sans-serif', size=18, color='#2c3e50', weight='bold'),
        },
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05,
            font=dict(color='black', size=12, family='sans-serif'),
            traceorder='normal'
        ),
        margin=dict(t=40, b=20, l=20, r=20),
        font=dict(family="sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig

def streamlit_plotly_autoplay_once(fig, height=None, width=None, frame_duration=80):
    fig_json = fig.to_json()
    width_style = f'{width}px' if width else '100%'
    height_style = f'{height}px' if height else '100%'
    html = f"""
    <div id="plotly-div" style="width:{width_style}; height:{height_style};"></div>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script>
    (function() {{
        const figure = JSON.parse(`{fig_json}`);
        let plot = null;

        Plotly.newPlot('plotly-div', figure.data, figure.layout).then(function(p) {{
            plot = p;
            if (figure.frames && figure.frames.length > 0) {{
                Plotly.addFrames(plot, figure.frames);
                const animOpts = {{
                    frame: {{duration: {frame_duration}, redraw: true}},
                    transition: {{duration: 50}},
                    mode: 'immediate'
                }};
                Plotly.animate(plot, figure.frames, animOpts);
            }}
        }});
    }})();
    </script>
    """
    st.components.v1.html(html, height=height or 600, width=width or None, scrolling=False)

# --- Conteúdos com checkboxes ---
def display_conteudos_com_checkboxes(df):
    worksheet = get_worksheet()
    if df.empty or worksheet is None:
        st.info("Nenhum dado disponível para exibir conteúdos.")
        return
        
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
    st.set_page_config(
        page_title="📚 Dashboard de Estudos - Concurso 2025",
        page_icon="📚",
        layout="wide"
    )

    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)

    with st.container():
        render_topbar_with_logo(dias_restantes)

    df = load_data_with_row_indices()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)

    display_containers_metricas(stats, progresso_geral)

    st.markdown("---")

    # Histograma horizontal responsivo com título centralizado e fonte padrão
    fig_hist = create_histograma_horizontal_simplificado(df_summary)
    display_histograma_horizontal_simplificado(fig_hist)

    st.markdown("---")

    titulo_com_destaque("📚 Conteúdos por Disciplina", cor_lateral="#8e44ad")
    display_conteudos_com_checkboxes(df)

    st.markdown("---")

    titulo_com_destaque("📊 Número de Questões e Peso por Disciplina", cor_lateral="#8e44ad")
    display_containers_questoes_peso(ED_DATA)

    fig_pie = pie_chart_peso_vezes_questoes_animado(ED_DATA)
    streamlit_plotly_autoplay_once(fig_pie, height=700)  # largura adaptável

    st.markdown("---")

    rodape_motivacional()

if __name__ == "__main__":
    main()
