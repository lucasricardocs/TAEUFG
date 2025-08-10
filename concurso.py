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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

def build_daily_plan(df_summary):
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    if dias_restantes == 0:
        return pd.DataFrame()

    planos = []
    for _, row in df_summary.iterrows():
        restante = row['Conteudos_Pendentes']
        if restante <= 0:
            continue
        topicos_dia = round(restante / dias_restantes, 1)
        tempo_tipo = row['Peso'] * 30
        tempo_total = topicos_dia * tempo_tipo
        prioridade = row['Prioridade_Score']
        planos.append({
            'Disciplina': row['Disciplinas'],
            'Conteudos_Restantes': int(restante),
            'Topicos_Por_Dia': topicos_dia,
            'Tempo_Diario_Min': int(tempo_total),
            'Prioridade_Score': round(prioridade, 1),
            'Peso': row['Peso'],
            'Progresso': row['Progresso_Ponderado']
        })
    df_plan = pd.DataFrame(planos).sort_values(by='Prioridade_Score', ascending=False)
    return df_plan

# --- Visualização e Estilo ---
def set_celestial_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    .stApp {
        background: #fff url(https://www.script-tutorials.com/demos/360/images/stars.png) repeat center top;
        animation: move-twink-back 200s linear infinite;
        font-family: 'Inter', sans-serif;
        color: #2c3e50;
    }
    @keyframes move-twink-back {from {background-position:0 0;} to {background-position:-10000px 5000px;}}
    .main-header {text-align:center; background:#fff; padding:3rem 2rem; border-radius:18px; border:2px solid #e0e0e0; box-shadow:0 8px 30px rgba(0,0,0,0.05); margin-bottom:2rem;}
    .main-header h1 {font-weight:700; font-size:3rem; background: linear-gradient(135deg, #6a11cb, #2575fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.3rem;}
    .main-header p {font-weight:600; font-size:1.2rem; color:#576574; margin-top:0;}
    .metric-container {background:#f8f9fa; border-radius:15px; box-shadow:0 4px 20px rgba(0,0,0,0.05); padding:1.5rem; text-align:center; margin-bottom:1rem; transition: all 0.3s ease;}
    .metric-container:hover {box-shadow: 0 8px 35px rgba(106, 17, 203, 0.2); transform: translateY(-4px);}
    .metric-value {font-size:3rem; color:#2575fc; font-weight:700; margin-bottom:0.2rem;}
    .metric-label {font-weight:600; color:#576574;}
    .section-header {font-size:1.8rem; font-weight:600; color:#6a11cb; border-bottom:3px solid #6a11cb; padding-bottom:0.3rem; margin-bottom:1.5rem; display:inline-block;}
    .chart-container {background:#fff; padding:1rem; border-radius:15px; box-shadow:0 8px 25px rgba(0,0,0,0.1); margin-bottom:1.5rem; height:320px; display:flex; justify-content:center; align-items:center;}
    .discipline-container {background:#fff; border:2px solid #6a11cb; border-radius:18px; padding:1.5rem 2rem; margin:2rem 0; box-shadow:0 10px 30px rgba(0,0,0,0.07);}
    .discipline-title {font-weight:700; font-size:1.4rem; color:#6a11cb; margin-bottom:1rem; text-align:center;}
    .stAlert > div {border-radius:10px; color:#2c3e50;}
    .footer {text-align:center; padding:1.5rem 0; font-weight:500; color:#576574; border-top:1px solid #e0e0e0; margin-top:3rem;}
    .stButton > button {background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); color:#fff; font-weight:600; border-radius:10px; border:none; transition: all 0.3s ease;}
    .stButton > button:hover {box-shadow: 0 10px 25px rgba(106,17,203,0.35); transform: translateY(-3px);}
    </style>
    """, unsafe_allow_html=True)

def create_altair_donut(row):
    concluido = int(row['Conteudos_Concluidos'])
    pendente = int(row['Conteudos_Pendentes'])
    if concluido + pendente == 0:
        pendente = 1
    source = pd.DataFrame({'Status': ['Concluído', 'Pendente'], 'Valor': [concluido, pendente]})
    color_scale = alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c'])
    base_chart = alt.Chart(source).encode(
        theta=alt.Theta(field='Valor', type='quantitative'),
        color=alt.Color('Status:N', scale=color_scale, legend=None),
        tooltip=['Status', 'Valor']
    )
    donut = base_chart.mark_arc(innerRadius=50, stroke='#fff', strokeWidth=2)
    text = base_chart.mark_text(radius=75, size=14, fontWeight='bold', color='white').encode(text='Valor:Q')
    chart = (donut + text).properties(
        title=alt.TitleParams(
            text=str(row['Disciplinas']),
            subtitle=f"{row['Progresso_Ponderado']:.1f}% Progresso Ponderado",
            anchor='middle',
            fontSize=16,
            fontWeight='bold',
            color='#2c3e50',
            subtitleColor='#576574'
        ),
        width=200, height=200).configure_view(strokeWidth=0)
    return chart

def create_plotly_radar(df_summary):
    if df_summary.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=df_summary['Progresso_Ponderado'],
        theta=df_summary['Disciplinas'],
        fill='toself',
        name='Progresso Ponderado',
        line=dict(color='#2575fc', width=3),
        fillcolor='rgba(37,117,252,0.2)',
        hovertemplate="<b>%{theta}</b><br>Progresso: %{r:.1f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatterpolar(
        r=df_summary['Conteudos_Concluidos'] / df_summary['Total_Conteudos'] * 100,
        theta=df_summary['Disciplinas'],
        fill='toself',
        name='Percentual Simples',
        line=dict(color='#6a11cb', width=2),
        fillcolor='rgba(106,17,203,0.1)',
        hovertemplate="<b>%{theta}</b><br>Conclusão: %{r:.1f}%<extra></extra>"
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 100], tickfont=dict(color='#576574'), gridcolor='rgba(0,0,0,0.1)'),
            angularaxis=dict(tickfont=dict(color='#2c3e50'), gridcolor='rgba(0,0,0,0.1)'),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#2c3e50'),
        title=dict(text="<b>Radar de Desempenho por Disciplina</b>", x=0.5, font=dict(color='#6a11cb'))
    )
    return fig

def create_plotly_priority(df_summary):
    if df_summary.empty:
        return go.Figure()
    df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
    max_score = df_summary['Prioridade_Score'].max()
    sizes = ((df_summary['Prioridade_Score'] / max_score) * 50 + 15).fillna(15)
    fig = go.Figure(go.Scatter(
        x=df_summary['Peso'],
        y=df_summary['Progresso_Ponderado'],
        mode='markers+text',
        marker=dict(
            size=sizes,
            color=df_summary['Progresso_Ponderado'],
            colorscale='RdYlGn',
            colorbar=dict(title='Progresso (%)', tickfont=dict(color='#2c3e50')),
            line=dict(color='#2c3e50', width=2)
        ),
        text=[disc if len(disc) <= 10 else disc[:10] + '...' for disc in df_summary['Disciplinas']],
        textposition='middle center',
        textfont=dict(color='#2c3e50', size=11),
        customdata=df_summary['Prioridade_Score'],
        hovertemplate='<b>%{text}</b><br>Peso: %{x}<br>Progresso: %{y:.1f}%<br>Prioridade: %{customdata:.1f}<extra></extra>'
    ))
    fig.update_layout(
        title='<b>Matriz de Prioridades (Peso vs Progresso)</b>',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='Peso da Disciplina', gridcolor='rgba(0,0,0,0.1)', tickfont=dict(color='#576574')),
        yaxis=dict(title='Progresso (%)', gridcolor='rgba(0,0,0,0.1)', tickfont=dict(color='#576574')),
        font=dict(color='#2c3e50'),
        height=400
    )
    return fig

def create_plan_study_chart(df_plan):
    if df_plan.empty:
        return go.Figure().update_layout(
            title_text="<b>Plano de Estudos Diário (Sem dados para exibir)</b>",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_visible=False,
            yaxis_visible=False
        )
    fig = make_subplots(rows=2, cols=1, subplot_titles=(
        'Tópicos por Dia por Disciplina', 'Tempo Diário Estimado (minutos)'),
        vertical_spacing=0.15)
    fig.add_trace(go.Bar(
        x=df_plan['Disciplina'],
        y=df_plan['Topicos_Por_Dia'],
        name='Tópicos/Dia',
        marker=dict(color=df_plan['Prioridade_Score'], colorscale='Viridis', showscale=True, colorbar=dict(title='Prioridade')),
        text=df_plan['Topicos_Por_Dia'],
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>Tópicos/Dia: %{y}<br>Prioridade: %{customdata:.1f}<extra></extra>',
        customdata=df_plan['Prioridade_Score']
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=df_plan['Disciplina'],
        y=df_plan['Tempo_Diario_Min'],
        name='Tempo Diário (min)',
        marker_color='#2575fc',
        text=df_plan['Tempo_Diario_Min'],
        textposition='auto',
        hovertemplate='<b>%{x}</b><br>Tempo: %{y} min<br>Conteúdos Restantes: %{customdata}<extra></extra>',
        customdata=df_plan['Conteudos_Restantes']
    ), row=2, col=1)
    fig.update_layout(showlegend=False, height=600,
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      title={'text':"<b>Plano de Estudos Diário</b>", 'x':0.5},
                      font=dict(color='#2c3e50'))
    fig.update_xaxes(tickangle=45, tickfont=dict(color='#576574'),
                     gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(tickfont=dict(color='#576574'), gridcolor='rgba(0,0,0,0.1)')
    return fig

# --- Função Principal ---
def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso 2025", page_icon="📚", layout="wide")
    set_celestial_theme()

    st.markdown("""
    <div class="main-header">
        <h1>📚 Dashboard de Estudos</h1>
        <p>Acompanhe seu progresso para o Concurso 2025</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)
    plano_estudos = build_daily_plan(df_summary)

    # Filtros interativos
    st.sidebar.header("Filtros")
    disciplinas_disponiveis = sorted(df['Disciplinas'].unique()) if not df.empty else sorted(ED_DATA['Disciplinas'])
    disciplinas_selecionadas = st.sidebar.multiselect("Selecione Disciplinas", disciplinas_disponiveis, default=disciplinas_disponiveis)
    status_opcoes = ['True', 'False']
    status_selecionado = st.sidebar.multiselect("Status do Conteúdo", status_opcoes, default=status_opcoes)

    # Aplicar filtros
    df_filtrado = df[
        (df['Disciplinas'].isin(disciplinas_selecionadas)) &
        (df['Status'].isin(status_selecionado))
    ].copy()

    # Estatísticas principais
    st.markdown('<div class="section-header">📊 Estatísticas Gerais</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">{progresso_geral:.1f}%</div>
            <div class="metric-label">Progresso Geral</div>
        </div>""", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">{stats['dias_restantes']}</div>
            <div class="metric-label">Dias Restantes</div>
        </div>""", unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">{stats['concluidos']}</div>
            <div class="metric-label">Conteúdos Concluídos</div>
        </div>""", unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">{stats['total_conteudos']}</div>
            <div class="metric-label">Total de Conteúdos</div>
        </div>""", unsafe_allow_html=True)
    with cols[4]:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-value">{stats['topicos_por_dia']}</div>
            <div class="metric-label">Tópicos/Dia Necessários</div>
        </div>""", unsafe_allow_html=True)

    # Gráficos de progresso por disciplina
    st.markdown('<div class="section-header">🎯 Progresso por Disciplina</div>', unsafe_allow_html=True)
    num_cols = min(len(df_summary), 5)
    colunas = st.columns(num_cols)
    for idx, row in df_summary.iterrows():
        with colunas[idx % num_cols]:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.altair_chart(create_altair_donut(row), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Análises avançadas
    st.markdown('<div class="section-header">📈 Análises Avançadas</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(create_plotly_radar(df_summary), use_container_width=True)
    with c2:
        st.plotly_chart(create_plotly_priority(df_summary), use_container_width=True)

    # Plano de estudos
    st.markdown('<div class="section-header">📅 Plano de Estudos Diário</div>', unsafe_allow_html=True)
    if not plano_estudos.empty:
        st.plotly_chart(create_plan_study_chart(plano_estudos), use_container_width=True)

        st.markdown("### 📋 Detalhamento do Plano de Estudos")
        plano_display = plano_estudos.copy()
        plano_display['Tempo_Horas'] = (plano_display['Tempo_Diario_Min'] / 60).round(1)
        st.dataframe(plano_display[['Disciplina', 'Conteudos_Restantes', 'Topicos_Por_Dia', 'Tempo_Horas', 'Prioridade_Score']].rename(columns={
            'Disciplina': 'Disciplina',
            'Conteudos_Restantes': 'Conteúdos Restantes',
            'Topicos_Por_Dia': 'Tópicos/Dia',
            'Tempo_Horas': 'Tempo Diário (h)',
            'Prioridade_Score': 'Score Prioridade'
        }), use_container_width=True, hide_index=True)

        tempo_total_min = plano_estudos['Tempo_Diario_Min'].sum()
        st.markdown(f"""
        <div style="text-align:center; background:#f8f9fa; border-radius:10px; padding:1rem; margin-top:1rem; border:1px solid #e0e0e0;">
            <h3 style="color:#6a11cb;">⏰ Tempo Total de Estudo Diário: {tempo_total_min} minutos ({(tempo_total_min / 60):.1f} horas)</h3>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("🎉 Parabéns! Todos os conteúdos foram concluídos ou falta tempo para calcular o plano.")

    # Containers expansíveis por disciplina com conteúdos filtrados
    st.markdown('<div class="section-header">📚 Conteúdos por Disciplina</div>', unsafe_allow_html=True)
    # Preparar lista de disciplinas ordenadas
    disciplinas_para_mostrar = sorted(df_filtrado['Disciplinas'].unique())
    for disc in disciplinas_para_mostrar:
        conteudos_disciplina = df_filtrado[df_filtrado['Disciplinas'] == disc]
        with st.expander(f"{disc} ({len(conteudos_disciplina)} conteúdos)"):
            c1, c2, c3 = st.columns([6, 1, 1])
            c1.write("Conteúdo")
            c2.write("Status")
            c3.write("Ícone")
            for _, row in conteudos_disciplina.iterrows():
                status = row['Status']
                icone = "✅" if status == 'True' else "❌"
                cor = "#2ecc71" if status == 'True' else "#e74c3c"
                c1.write(row['Conteúdos'])
                c2.markdown(f"<span style='color:{cor}; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)
                c3.markdown(f"<span style='font-size:20px; color:{cor};'>{icone}</span>", unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="footer">
        <p>Dashboard desenvolvido para acompanhamento de estudos • Concurso 2025</p>
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
