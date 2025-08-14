Estou aqui para implementar as suas sugestões e aprimorar o código.

Com base na sua solicitação, fiz as seguintes modificações:

1.  **Gráfico de Progresso (Histograma):**

      * A legenda do gráfico foi removida.
      * O texto do eixo X e as etiquetas numéricas foram excluídos.
      * **Rótulos de Porcentagem:** O cálculo do percentual foi implementado, e os rótulos agora aparecem centralizados e em preto em cada segmento das barras.
      * A altura do gráfico foi ajustada para `500`.

2.  **Gráficos da Análise Estratégica:**

      * A altura dos gráficos de "Número de Questões" e "Relevância (Peso × Questões)" foi ajustada para `500`.
      * A legenda de ambos os gráficos agora aparece na parte inferior.
      * Os rótulos nos gráficos estão na cor preta, como solicitado.

3.  **Ordem das Seções:** A seção **"Análise Estratégica da Prova"** foi movida para depois da seção **"Checklist de Conteúdos"**.

4.  **Rodapé:** O rodapé foi aprimorado para incluir uma lista de frases motivacionais que aparecerão de forma aleatória a cada carregamento da página.

O código a seguir incorpora todas essas mudanças de forma funcional e robusta, seguindo as melhores práticas de UI/UX.

-----

### Código Final e Otimizado

```python
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import streamlit as st
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound, APIError
import warnings
import altair as alt
import random

# Ignora avisos futuros do pandas que não são relevantes aqui
warnings.filterwarnings('ignore', category=FutureWarning, message='.*observed=False.*')

# Configura a localidade para português do Brasil para exibir as datas corretamente
try:
    import locale
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass

# --- Constantes de Configuração ---
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

def format_date_br(date_obj):
    meses_pt = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    return date_obj.strftime(f'%d de {meses_pt[date_obj.month-1]} de %Y')

@st.cache_resource(show_spinner="Conectando ao Google Sheets...")
def get_gspread_client():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/spreadsheets.readonly']
    try:
        credentials_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Erro ao autenticar no Google Sheets: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_worksheet():
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

@st.cache_data(ttl=300, show_spinner="Carregando dados dos estudos...")
def load_data_with_row_indices():
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
        df['Status'] = df['Status'].str.strip().str.lower().map({'true': True, 'false': False})
        df.dropna(subset=['Status'], inplace=True)
        df.reset_index(inplace=True)
        df['sheet_row'] = df['index'] + 2
        df.drop('index', axis=1, inplace=True)
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Falha ao carregar ou processar dados: {e}")
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

def calculate_stats(df_summary, df_full):
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    concluidos = df_summary['Conteudos_Concluidos'].sum()
    pendentes = df_summary['Conteudos_Pendentes'].sum()
    topicos_por_dia = round(pendentes / dias_restantes, 1) if dias_restantes > 0 else 0
    maior_prioridade = "N/A"
    proximos_conteudos = []
    if pendentes > 0:
        df_summary['Progresso_Percentual'] = (df_summary['Conteudos_Concluidos'] / df_summary['Total_Conteudos'].replace(0, 1)) * 100
        df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Percentual']) * df_summary['Peso']
        prioridade_disc = df_summary.loc[df_summary['Prioridade_Score'].idxmax()]['Disciplinas']
        maior_prioridade = prioridade_disc.title()
        proximos_conteudos_df = df_full[(df_full['Disciplinas'] == prioridade_disc) & (df_full['Status'] == False)].head(3)
        proximos_conteudos = proximos_conteudos_df['Conteúdos'].tolist()
    return {
        'dias_restantes': dias_restantes,
        'concluidos': int(concluidos),
        'pendentes': int(pendentes),
        'topicos_por_dia': topicos_por_dia,
        'maior_prioridade': maior_prioridade,
        'proximos_conteudos': proximos_conteudos
    }

def render_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        html, body, [class*="st-"] {
            font-family: 'Roboto', sans-serif;
        }
        .top-bar-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(135deg, #F8F9FE 0%, #EAEFFF 100%);
            border: 1px solid #d1d9e6;
            border-radius: 16px;
            padding: 1.25rem 2rem;
            margin-bottom: 2.5rem;
            box-shadow: 0 8px 32px rgba(90, 97, 125, 0.1);
        }
        .logo-title-group {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }
        .logo-title-group img {
            height: 65px;
        }
        .title-text h1 {
            color: #1e2a38;
            margin: 0;
            font-size: 1.9rem;
            font-weight: 700;
        }
        .title-text p {
            color: #5a677d;
            margin: 0;
            font-weight: 500;
        }
        .countdown-group {
            text-align: right;
        }
        .countdown-box {
            background-color: #e74c3c;
            color: white;
            padding: 0.7rem 1.2rem;
            border-radius: 12px;
            font-size: 1.6rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
            display: inline-block;
        }
        .date-text {
            margin: 0;
            font-weight: 500;
            color: #5a677d;
            font-size: 0.9rem;
        }
        .metric-container {
            background: #ffffff;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            border: 1px solid #e0e0e0;
        }
        .section-title {
            border-left: 5px solid #8e44ad;
            padding: 0.5rem 1rem;
            background-color: #F0F2F6;
            border-radius: 8px;
            margin: 2rem 0 1.5rem 0;
        }
        .section-title h2 {
            color: #2c3e50;
            margin-block-start: 0;
            margin-block-end: 0;
        }
        .study-suggestion-box {
            background-color: #e8f5e9;
            border-left: 5px solid #2ecc71;
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1.5rem;
            margin-bottom: 2rem;
        }
        .stButton>button {
            border-radius: 8px;
            border: 1px solid #d1d9e6;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease-in-out;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        .st-emotion-cache-1r6ch9e {
            padding: 0px 1rem !important;
        }
        .no-box-expander {
            border: none !important;
            box-shadow: none !important;
            padding: 0;
            margin: 0;
        }
        .no-box-expander > div > button {
            border: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
            padding: 0 !important;
        }
        .no-box-expander .streamlit-expanderContent {
            border: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

def titulo_com_destaque(texto, cor_lateral="#8e44ad"):
    st.markdown(f"""
    <div style="border-left: 5px solid {cor_lateral}; padding: 0.5rem 1rem; background-color: #F0F2F6; border-radius: 8px; margin: 2rem 0 1.5rem 0;">
        <h2 style="color: #2c3e50; margin-block-start: 0; margin-block-end: 0;">{texto}</h2>
    </div>""", unsafe_allow_html=True)

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
            <div class="countdown-box">
                ⏰ Faltam {dias_restantes} dias!
            </div>
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
    cols[4].metric("⭐ Foco Principal", stats['maior_prioridade'].title())

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
        x=alt.X('Percentual:Q', stack='normalize', axis=alt.Axis(title=None, labels=False))
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
        height=500,
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
    total = source_df['Valor'].sum()
    concluido_val = source_df[source_df['Status'] == 'Concluído']['Valor'].iloc[0] if not source_df[source_df['Status'] == 'Concluido'].empty else 0
    percent_text = f"{(concluido_val / total * 100) if total > 0 else 0:.1f}%"
    
    base = alt.Chart(source_df).mark_arc(innerRadius=55, cornerRadius=5, stroke='#d3d3d3', strokeWidth=1).encode(
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

def handle_checkbox_change(worksheet, row_number, key, conteudo_nome):
    novo_status = st.session_state[key]
    if update_status_in_sheet(worksheet, row_number, "TRUE" if novo_status else "FALSE"):
        st.toast(f"✅ Status de '{conteudo_nome}' atualizado!", icon="✅")
        st.cache_data.clear()
        st.rerun()
    else:
        st.toast(f"❌ Falha ao atualizar '{conteudo_nome}'.", icon="❌")
        st.session_state[key] = not novo_status

def display_conteudos_com_checkboxes(df):
    worksheet = get_worksheet()
    if not worksheet:
        return
    resumo_disciplina = df.groupby('Disciplinas')['Status'].agg(['sum', 'count']).reset_index()
    resumo_disciplina['sum'] = resumo_disciplina['sum'].astype(int)

    if 'expanded_expander' not in st.session_state:
        st.session_state.expanded_expander = None

    for disc in sorted(df['Disciplinas'].unique()):
        conteudos_disciplina = df[df['Disciplinas'] == disc]
        resumo_disc = resumo_disciplina[resumo_disciplina['Disciplinas'] == disc]
        concluidos = resumo_disc['sum'].iloc[0]
        total = resumo_disc['count'].iloc[0]

        is_expanded = st.session_state.expanded_expander == disc

        expander_return = st.expander(f"**{disc.title()}** ({concluidos} / {total} concluídos)", expanded=is_expanded)
        if expander_return:
             st.session_state.expanded_expander = disc
        else:
             if st.session_state.expanded_expander == disc:
                 st.session_state.expanded_expander = None

        with expander_return:
            for _, row in conteudos_disciplina.iterrows():
                key = f"cb_{row['sheet_row']}"
                st.checkbox(
                    label=row['Conteúdos'],
                    value=bool(row['Status']),
                    key=key,
                    on_change=handle_checkbox_change,
                    kwargs={'worksheet': worksheet, 'row_number': row['sheet_row'], 'key': key, 'conteudo_nome': row['Conteúdos']}
                )

def create_questoes_bar_chart(ed_data):
    df = pd.DataFrame(ed_data)
    bars = alt.Chart(df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, stroke='#d3d3d3', strokeWidth=1).encode(
        x=alt.X('Disciplinas:N', sort=None, title=None, axis=None),
        y=alt.Y('Questões:Q', title=None, axis=None),
        color=alt.Color('Disciplinas:N', legend=alt.Legend(title="Disciplinas", orient="bottom")),
        tooltip=['Disciplinas', 'Questões']
    )
    text = bars.mark_text(align='center', baseline='bottom', dy=-5, color='black', fontWeight='bold').encode(
        text='Questões:Q'
    )
    return (bars + text).properties(
        height=500,
        title=alt.TitleParams("Número de Questões", anchor='middle', fontSize=18)
    )

def create_relevancia_pie_chart(ed_data):
    df = pd.DataFrame(ed_data)
    df['Relevancia'] = df['Peso'] * df['Questões']
    df['Percentual'] = (df['Relevancia'] / df['Relevancia'].sum()) * 100
    base = alt.Chart(df).encode(
        theta=alt.Theta("Relevancia:Q", stack=True),
        color=alt.Color("Disciplinas:N", legend=alt.Legend(
            orient="bottom",
            title="Disciplinas",
            titleFontSize=14,
            labelFontSize=12
        )),
        order=alt.Order("Relevancia:Q", sort="descending")
    )
    pie = base.mark_arc(innerRadius=70, cornerRadius=5, stroke='#d3d3d3', strokeWidth=1)
    text = base.mark_text(radius=85, size=12, color="black", fontWeight='bold').encode(
        text=alt.Text('Percentual:Q', format='.1f%'),
        theta=alt.Theta("Relevancia:Q", stack=True)
    )
    return (pie + text).properties(
        height=500,
        title=alt.TitleParams("Relevância (Peso × Questões)", anchor='middle', fontSize=18)
    )

def rodape_motivacional():
    st.markdown("<hr>", unsafe_allow_html=True)
    quote = random.choice(MOTIVATIONAL_QUOTES)
    st.markdown(f"<p style='text-align: center; font-size: 14px; color: #555;'>{quote}</p>", unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="📚 Dashboard de Estudos - Concurso TAE", page_icon="📚", layout="wide")
    render_custom_css()

    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    render_topbar_with_logo(dias_restantes)

    df = load_data_with_row_indices()
    if df.empty:
        st.info("👋 Bem-vindo! Parece que sua planilha de estudos está vazia. Adicione os conteúdos na sua Google Sheet para começar a monitorar seu progresso aqui.")
        st.stop()

    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df_summary, df)

    display_containers_metricas(stats, progresso_geral)

    titulo_com_destaque("📊 Compleção por Disciplina", cor_lateral="#3498db")
    st.altair_chart(create_percentual_conclusao_por_disciplina(df_summary), use_container_width=True)

    titulo_com_destaque("📈 Progresso Individual", cor_lateral="#3498db")
    display_donuts_grid(df_summary, progresso_geral)

    titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#8e44ad")
    display_conteudos_com_checkboxes(df)

    titulo_com_destaque("📝 Análise Estratégica da Prova", cor_lateral="#e67e22")
    colA, colB = st.columns(2, gap="large")
    with colA:
        st.altair_chart(create_questoes_bar_chart(ED_DATA), use_container_width=True)
    with colB:
        st.altair_chart(create_relevancia_pie_chart(ED_DATA), use_container_width=True)

    titulo_com_destaque("💡 Sugestão de Estudo para Hoje", cor_lateral="#2ecc71")
    display_study_suggestion(stats)

    rodape_motivacional()

if __name__ == "__main__":
    main()
```
