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
import altair as alt
import plotly.graph_objects as go
import plotly.express as px

warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

try:
    import locale
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass

# Configurações
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
CONCURSO_DATE = datetime(2025, 9, 28)

ED_DATA = {
    'Disciplinas': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS'],
    'Total_Conteudos': [20, 15, 10, 15, 30],
    'Peso': [2, 1, 1, 1, 3],
    'Questões': [10, 5, 5, 10, 20]
}

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
    df['Concluido'] = (df['Status'] == 'true').astype(int)
    resumo = df.groupby('Disciplinas')['Concluido'].sum().reset_index(name='Conteudos_Concluidos')
    df_merged = pd.merge(df_edital, resumo, how='left', on='Disciplinas').fillna(0)
    df_merged['Conteudos_Pendentes'] = df_merged['Total_Conteudos'] - df_merged['Conteudos_Concluidos']
    df_merged['Ponto_por_Conteudo'] = df_merged.apply(
        lambda row: row['Peso'] / row['Total_Conteudos'] if row['Total_Conteudos'] > 0 else 0, axis=1
    )
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
        df_summary_copy = df_summary.copy()
        df_summary_copy['Prioridade_Score'] = (100 - df_summary_copy['Progresso_Ponderado']) * df_summary_copy['Peso']
        maior_prioridade = df_summary_copy.loc[df_summary_copy['Prioridade_Score'].idxmax()]['Disciplinas']
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
    </div>""", unsafe_allow_html=True)

def render_topbar_with_logo(dias_restantes):
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        hoje_texto = datetime.now().strftime('%d de %B de %Y')
    except:
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        hoje = datetime.now()
        hoje_texto = f"{hoje.day} de {meses[hoje.month-1]} de {hoje.year}"

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
        <img class="topbar-logo" src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG">
        <div class="topbar-text">⏰ Faltam {dias_restantes} dias para o concurso de TAE</div>
        <div class="topbar-date">Goiânia, {hoje_texto}</div>
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
        font-family: 'Inter', sans-serif;
    }
    .questao-item:hover {
        background-color: #d0e4ff;
        color: #064270;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    for _, row in df.iterrows():
        st.markdown(
            f'<div class="questao-item"><strong>{row["Disciplinas"].title()}</strong>: {row["Questões"]} questões</div>',
            unsafe_allow_html=True,
        )

# NOVO: Função para criar histograma animado com as especificações do usuário
def create_animated_histogram(df_summary):
    """
    Cria um histograma animado com 700px de largura e 600px de altura
    com animação recorrente sempre que passar por ele
    """
    # Preparar dados para o histograma
    disciplinas = df_summary['Disciplinas'].tolist()
    conteudos_concluidos = df_summary['Conteudos_Concluidos'].tolist()
    conteudos_pendentes = df_summary['Conteudos_Pendentes'].tolist()
    
    # Criar frames para animação
    num_frames = 30
    frames = []
    
    for i in range(num_frames):
        # Animação crescente das barras
        progress = (i + 1) / num_frames
        
        # Valores animados
        animated_concluidos = [val * progress for val in conteudos_concluidos]
        animated_pendentes = [val * progress for val in conteudos_pendentes]
        
        frame = go.Frame(
            data=[
                go.Bar(
                    x=disciplinas,
                    y=animated_concluidos,
                    name='Concluídos',
                    marker_color='#2ecc71',
                    text=[f'{int(val)}' for val in animated_concluidos],
                    textposition='auto',
                ),
                go.Bar(
                    x=disciplinas,
                    y=animated_pendentes,
                    name='Pendentes',
                    marker_color='#e74c3c',
                    text=[f'{int(val)}' for val in animated_pendentes],
                    textposition='auto',
                )
            ],
            name=str(i)
        )
        frames.append(frame)
    
    # Criar figura inicial
    fig = go.Figure(
        data=[
            go.Bar(
                x=disciplinas,
                y=[0] * len(disciplinas),
                name='Concluídos',
                marker_color='#2ecc71'
            ),
            go.Bar(
                x=disciplinas,
                y=[0] * len(disciplinas),
                name='Pendentes',
                marker_color='#e74c3c'
            )
        ],
        frames=frames
    )
    
    # Configurar layout
    fig.update_layout(
        title={
            'text': 'Progresso por Disciplina',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#2c3e50'}
        },
        xaxis_title='Disciplinas',
        yaxis_title='Número de Conteúdos',
        barmode='stack',
        height=600,
        width=700,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        font=dict(family="Inter, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    # Configurar eixos
    fig.update_xaxes(
        tickangle=45,
        tickfont=dict(size=12),
        gridcolor='rgba(128,128,128,0.2)'
    )
    fig.update_yaxes(
        tickfont=dict(size=12),
        gridcolor='rgba(128,128,128,0.2)'
    )
    
    return fig

def display_animated_histogram_with_intersection_observer(fig):
    """
    Exibe o histograma com animação recorrente usando Intersection Observer
    """
    fig_json = fig.to_json()
    
    html = f"""
    <div id="histogram-container" style="width:700px; height:600px; margin: 0 auto;">
        <div id="histogram-plot" style="width:100%; height:100%;"></div>
    </div>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script>
    (function() {{
        const figure = {fig_json};
        let plot = null;
        let isAnimating = false;
        
        function createPlot() {{
            if (plot) {{
                Plotly.purge('histogram-plot');
            }}
            
            Plotly.newPlot('histogram-plot', figure.data, figure.layout).then(function(newPlot) {{
                plot = newPlot;
                if (figure.frames && figure.frames.length > 0) {{
                    Plotly.addFrames(plot, figure.frames);
                }}
            }});
        }}
        
        function animateHistogram() {{
            if (!plot || isAnimating) return;
            
            isAnimating = true;
            const animOpts = {{
                frame: {{duration: 50, redraw: true}},
                transition: {{duration: 30}},
                mode: 'immediate'
            }};
            
            Plotly.animate(plot, null, animOpts).then(function() {{
                setTimeout(function() {{
                    isAnimating = false;
                }}, 100);
            }});
        }}
        
        // Criar o plot inicial
        createPlot();
        
        // Configurar Intersection Observer para animação recorrente
        const observer = new IntersectionObserver(function(entries) {{
            entries.forEach(function(entry) {{
                if (entry.isIntersecting) {{
                    // Elemento está visível, iniciar animação
                    setTimeout(animateHistogram, 200);
                }}
            }});
        }}, {{
            threshold: 0.3 // Animar quando 30% do elemento estiver visível
        }});
        
        // Observar o container do histograma
        observer.observe(document.getElementById('histogram-container'));
        
        // Cleanup quando a página for recarregada
        window.addEventListener('beforeunload', function() {{
            observer.disconnect();
        }});
    }})();
    </script>
    """
    
    st.components.v1.html(html, height=650, width=750, scrolling=False)

# CORRIGIDO: Função do gráfico de pizza com correções de cor, proporção e animação
def pie_chart_peso_vezes_questoes_com_labels_animado_corrigido(ED_DATA):
    df = pd.DataFrame(ED_DATA)
    df['Peso_vezes_Questoes'] = df['Peso'] * df['Questões']
    total = df['Peso_vezes_Questoes'].sum()
    df['Percentual'] = df['Peso_vezes_Questoes'] / total
    
    # Ordenar do maior para o menor para animação correta
    df = df.sort_values('Peso_vezes_Questoes', ascending=False).reset_index(drop=True)
    
    # Cores vibrantes e distintas para cada disciplina
    cores = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
    
    num_frames = 40
    labels_final = df.apply(lambda r: f"{r['Disciplinas']}<br>({r['Percentual']:.1%})", axis=1).tolist()
    
    frames = []
    for i in range(num_frames):
        # Animação crescente do maior para o menor
        progress = (i + 1) / num_frames
        
        # Calcular valores animados baseados no progresso
        animated_values = []
        for idx, val in enumerate(df['Peso_vezes_Questoes']):
            # Cada fatia aparece em sequência baseada no tamanho
            slice_start_frame = idx * (num_frames // len(df))
            if i >= slice_start_frame:
                slice_progress = min(1.0, (i - slice_start_frame) / (num_frames // len(df)))
                animated_values.append(val * slice_progress)
            else:
                animated_values.append(0)
        
        # Mostrar labels apenas no final
        texts = labels_final if i >= (num_frames - 5) else [""] * len(df)
        
        frame = go.Frame(
            data=[go.Pie(
                labels=df['Disciplinas'],
                values=animated_values,
                hole=0.3,
                text=texts,
                textinfo='text',
                textposition='outside',
                textfont=dict(size=14, color='white', family='Inter'),
                marker=dict(
                    colors=cores[:len(df)],
                    line=dict(color='white', width=2)
                ),
                hovertemplate='<b>%{label}</b><br>Valor: %{value}<br>Percentual: %{percent}<extra></extra>',
                rotation=90
            )],
            name=str(i)
        )
        frames.append(frame)
    
    # Figura inicial
    fig = go.Figure(data=frames[0].data, frames=frames)
    
    # Layout corrigido com dimensões e alinhamento adequados
    fig.update_layout(
        title={
            'text': 'Distribuição Peso × Questões por Disciplina',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#2c3e50', 'family': 'Inter'}
        },
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05,
            font=dict(size=12)
        ),
        height=600,
        width=700,  # Largura corrigida para ocupar a coluna adequadamente
        margin=dict(t=80, b=40, l=40, r=120),  # Margens ajustadas
        font=dict(family="Inter, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig

def streamlit_plotly_autoplay_once_corrigido(fig, height=600, width=700, frame_duration=80):
    """
    Versão corrigida da função de autoplay com melhor controle de animação
    """
    fig_json = fig.to_json()
    
    html = f"""
    <div id="pie-container" style="width:{width}px; height:{height}px; margin: 0 auto;">
        <div id="pie-plot" style="width:100%; height:100%;"></div>
    </div>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script>
    (function() {{
        const figure = {fig_json};
        let plot = null;
        let isAnimating = false;
        
        function createPlot() {{
            if (plot) {{
                Plotly.purge('pie-plot');
            }}
            
            Plotly.newPlot('pie-plot', figure.data, figure.layout).then(function(newPlot) {{
                plot = newPlot;
                if (figure.frames && figure.frames.length > 0) {{
                    Plotly.addFrames(plot, figure.frames);
                }}
            }});
        }}
        
        function animatePie() {{
            if (!plot || isAnimating) return;
            
            isAnimating = true;
            const animOpts = {{
                frame: {{duration: {frame_duration}, redraw: true}},
                transition: {{duration: 50}},
                mode: 'immediate'
            }};
            
            Plotly.animate(plot, null, animOpts).then(function() {{
                setTimeout(function() {{
                    isAnimating = false;
                }}, 200);
            }});
        }}
        
        // Criar o plot inicial
        createPlot();
        
        // Configurar Intersection Observer para animação recorrente
        const observer = new IntersectionObserver(function(entries) {{
            entries.forEach(function(entry) {{
                if (entry.isIntersecting) {{
                    // Elemento está visível, iniciar animação
                    setTimeout(animatePie, 300);
                }}
            }});
        }}, {{
            threshold: 0.4 // Animar quando 40% do elemento estiver visível
        }});
        
        // Observar o container do gráfico de pizza
        observer.observe(document.getElementById('pie-container'));
        
        // Cleanup
        window.addEventListener('beforeunload', function() {{
            observer.disconnect();
        }});
    }})();
    </script>
    """
    
    st.components.v1.html(html, height=height + 50, width=width + 50, scrolling=False)

def create_altair_donut(row):
    concluido = int(row['Conteudos_Concluidos'])
    pendente = int(row['Conteudos_Pendentes'])
    total = max(concluido + pendente, 1)
    concluido_pct = round((concluido / total) * 100, 1)

    source = pd.DataFrame({
        'Status': ['Concluído', 'Pendente'],
        'Valor': [concluido, pendente],
    })
    source_label = pd.DataFrame({'text': [f'{concluido_pct:.1f}%']})
    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])
    base_chart = alt.Chart(source).encode(
        theta=alt.Theta(field='Valor', type='quantitative'),
        color=alt.Color('Status:N', scale=color_scale, legend=None),
        tooltip=[alt.Tooltip('Status:N'), alt.Tooltip('Valor:Q', format='d')]
    )
    donut = base_chart.mark_arc(innerRadius=70, stroke='#d3d3d3', strokeWidth=3)
    text = alt.Chart(source_label).mark_text(
        size=22, fontWeight='bold', color='#2ecc71'
    ).encode(text=alt.Text('text:N')).properties(width=280, height=280)
    return (donut + text).properties(width=280, height=280).configure_view(stroke='#d3d3d3', strokeWidth=3)

def display_6_charts_responsive_with_titles(df_summary, progresso_geral, max_cols=3):
    total_charts = len(df_summary) + 1
    rows = (total_charts + max_cols - 1) // max_cols
    donuts = [create_altair_donut(df_summary.iloc[i]) for i in range(len(df_summary))]

    source = pd.DataFrame({
        'Status': ['Concluído', 'Pendente'],
        'Valor': [progresso_geral, 100 - progresso_geral]
    })
    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])
    base = alt.Chart(source).encode(
        theta=alt.Theta(field='Valor', type='quantitative'),
        color=alt.Color('Status:N', scale=color_scale, legend=None)
    ).mark_arc(innerRadius=70, stroke='#d3d3d3', strokeWidth=3)
    text = alt.Chart(pd.DataFrame({'text': [f'{progresso_geral:.1f}%']})).mark_text(
        size=22, fontWeight='bold', color='#2ecc71'
    ).encode(text=alt.Text('text:N')).properties(width=280, height=280)
    donut_geral = (base + text).properties(width=280, height=280)
    donuts.append(donut_geral)

    chart_idx = 0
    for _ in range(rows):
        cols = st.columns(max_cols, gap="medium")
        for c in range(max_cols):
            if chart_idx >= total_charts:
                break
            with cols[c]:
                nome = "Progresso Geral" if chart_idx == len(df_summary) else df_summary.iloc[chart_idx]['Disciplinas'].title()
                st.markdown(f'<h3 style="text-align:center;">{nome}</h3>', unsafe_allow_html=True)
                st.altair_chart(donuts[chart_idx], use_container_width=True)
            chart_idx += 1

def display_conteudos_com_checkboxes(df):
    worksheet = get_worksheet()
    if df.empty or worksheet is None:
        st.info("Nenhum dado disponível para exibir conteúdos.")
        return

    disciplinas_ordenadas = sorted(df['Disciplinas'].unique())
    for disc in disciplinas_ordenadas:
        conteudos_disciplina = df[df['Disciplinas'] == disc]
        with st.expander(f"{disc} ({len(conteudos_disciplina)} conteúdos)"):
            for _, row in conteudos_disciplina.iterrows():
                key = f"{row['Disciplinas']}_{row['Conteúdos']}_{row['sheet_row']}"
                checked = (row['Status'] == 'true')
                try:
                    novo_status = st.checkbox(label=row['Conteúdos'], value=checked, key=key)
                    if novo_status != checked:
                        sucesso = update_status_in_sheet(worksheet, row['sheet_row'], "true" if novo_status else "false")
                        if sucesso:
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Falha ao atualizar status na planilha.")
                except Exception as e:
                    st.error(f"❌ Erro ao processar checkbox: {e}")

# Exemplo de uso das novas funções (adicionar onde apropriado no código principal):
# 
# # Para exibir o histograma animado:
# titulo_com_destaque("📊 Histograma de Progresso por Disciplina")
# hist_fig = create_animated_histogram(df_summary)
# display_animated_histogram_with_intersection_observer(hist_fig)
#
# # Para exibir o gráfico de pizza corrigido:
# titulo_com_destaque("🥧 Distribuição Peso × Questões")
# pie_fig = pie_chart_peso_vezes_questoes_com_labels_animado_corrigido(ED_DATA)
# streamlit_plotly_autoplay_once_corrigido(pie_fig)

