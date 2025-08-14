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
    'Total_Conteudos': [20, 15, 10, 15, 30],
    'Peso': [2, 1, 1, 1, 3],
    'Questões': [10, 5, 5, 10, 20]
}

# --- Funções de Conexão com Google Sheets (com cache) ---

@st.cache_resource(show_spinner="Conectando ao Google Sheets...")
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

@st.cache_data(ttl=300, show_spinner="Carregando dados dos estudos...")
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
        if not all(col in df.columns for col in required_cols):
            st.error(f"❌ Colunas obrigatórias faltando. Verifique se a planilha tem: {required_cols}")
            return pd.DataFrame()
            
        df = df[required_cols].copy()
        df['Disciplinas'] = df['Disciplinas'].str.strip().str.upper()
        df['Conteúdos'] = df['Conteúdos'].str.strip()
        df['Status'] = df['Status'].str.strip().str.lower()
        df = df[df['Status'].isin(['true', 'false'])].copy()
        df['Status'] = df['Status'].map({'true': True, 'false': False})
        
        # Adiciona o número da linha original da planilha para atualizações
        df.reset_index(inplace=True)
        df['sheet_row'] = df['index'] + 2
        df.drop('index', axis=1, inplace=True)
        
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Falha ao carregar dados: {e}")
        return pd.DataFrame()

# --- Funções de Lógica e Cálculos ---

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

    resumo = df.groupby('Disciplinas', observed=True)['Status'].sum().reset_index(name='Conteudos_Concluidos')
    df_merged = pd.merge(df_edital, resumo, how='left', on='Disciplinas').fillna(0)
    df_merged['Conteudos_Concluidos'] = df_merged['Conteudos_Concluidos'].astype(int)
    
    df_merged['Conteudos_Pendentes'] = df_merged['Total_Conteudos'] - df_merged['Conteudos_Concluidos']
    df_merged['Ponto_por_Conteudo'] = df_merged.apply(lambda row: row['Peso'] / row['Total_Conteudos'] if row['Total_Conteudos'] > 0 else 0, axis=1)
    df_merged['Pontos_Concluidos'] = df_merged['Conteudos_Concluidos'] * df_merged['Ponto_por_Conteudo']
    df_merged['Progresso_Ponderado'] = np.where(df_merged['Peso'] > 0, (df_merged['Pontos_Concluidos'] / df_merged['Peso']) * 100, 0).round(1)
    
    total_peso = df_merged['Peso'].sum()
    total_pontos = df_merged['Pontos_Concluidos'].sum()
    progresso_total = (total_pontos / total_peso * 100) if total_peso > 0 else 0
    
    return df_merged, round(progresso_total, 1)

def calculate_stats(df, df_summary):
    dias_restantes = max((CONCURSO_DATE - datetime.now()).days, 0)
    total_conteudos = df_summary['Total_Conteudos'].sum() if not df_summary.empty else 0
    concluidos = df_summary['Conteudos_Concluidos'].sum() if not df_summary.empty else 0
    pendentes = df_summary['Conteudos_Pendentes'].sum() if not df_summary.empty else 0
    percentual_geral = round((concluidos / total_conteudos) * 100, 1) if total_conteudos > 0 else 0
    topicos_por_dia = round(pendentes / dias_restantes, 1) if dias_restantes > 0 else 0
    
    if not df_summary.empty and pendentes > 0:
        df_summary['Prioridade_Score'] = (100 - df_summary['Progresso_Ponderado']) * df_summary['Peso']
        maior_prioridade = df_summary.loc[df_summary['Prioridade_Score'].idxmax()]['Disciplinas']
    else:
        maior_prioridade = "N/A"
        
    return {
        'dias_restantes': dias_restantes,
        'concluidos': int(concluidos),
        'pendentes': int(pendentes),
        'topicos_por_dia': topicos_por_dia,
        'maior_prioridade': maior_prioridade
    }

# --- Funções de Interface e Visualização ---

def titulo_com_destaque(texto, cor_lateral="#8e44ad"):
    st.markdown(f"""
    <div style="border-left: 6px solid {cor_lateral}; padding-left: 16px; background-color: #f5f5f5; border-radius: 8px; margin-bottom: 24px;">
        <h2 style="color: #2c3e50; font-weight: 700;">{texto}</h2>
    </div>""", unsafe_allow_html=True)

def render_topbar_with_logo(dias_restantes):
    hoje_texto = datetime.now().strftime('%d de %B de %Y')
    st.markdown(f"""
    <div style="display: flex; align-items: center; background-color: #f5f5f5; border-radius: 12px; padding: 1rem 2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 2rem;">
        <img src="https://files.cercomp.ufg.br/weby/up/1/o/UFG_colorido.png" alt="Logo UFG" style="height: 90px; margin-right: 2rem;"/>
        <div>
            <h1 style="color: #2c3e50; margin: 0; font-size: 2rem;">Dashboard de Estudos - Concurso TAE</h1>
            <p style="color: #e74c3c; font-weight: bold; font-size: 1.5rem; margin: 0;">⏰ Faltam {dias_restantes} dias para a prova!</p>
        </div>
        <div style="margin-left: auto; text-align: right; color: #555;">
            <p style="margin:0; font-weight: 600;">Goiânia, {hoje_texto}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_containers_metricas(stats, progresso_geral):
    cols = st.columns(5)
    with cols[0]:
        st.metric("🎯 Progresso Geral Ponderado", f"{progresso_geral:.1f}%")
    with cols[1]:
        st.metric("✅ Conteúdos Concluídos", f"{stats['concluidos']}")
    with cols[2]:
        st.metric("⏳ Conteúdos Pendentes", f"{stats['pendentes']}")
    with cols[3]:
        st.metric("🏃 Ritmo Necessário", f"{stats['topicos_por_dia']} tópicos/dia")
    with cols[4]:
        st.metric("⭐ Foco Principal", stats['maior_prioridade'].title())

def create_altair_donut(row):
    concluido = int(row['Conteudos_Concluidos'])
    pendente = int(row['Conteudos_Pendentes'])
    source = pd.DataFrame([{"Status": "Concluído", "Valor": concluido}, {"Status": "Pendente", "Valor": pendente}])
    
    chart = alt.Chart(source).mark_arc(innerRadius=50).encode(
        theta=alt.Theta("Valor:Q"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c']), legend=None),
        tooltip=['Status', 'Valor']
    )
    return chart

def display_progress_donuts(df_summary):
    disciplinas = df_summary['Disciplinas'].tolist()
    cols = st.columns(len(disciplinas))
    for i, col in enumerate(cols):
        with col:
            disciplina = disciplinas[i]
            dados_disciplina = df_summary[df_summary['Disciplinas'] == disciplina].iloc[0]
            st.markdown(f"<h4 style='text-align: center;'>{disciplina.title()}</h4>", unsafe_allow_html=True)
            chart = create_altair_donut(dados_disciplina)
            st.altair_chart(chart, use_container_width=True)

def create_altair_stacked_bar(df_summary):
    df_melted = df_summary.melt(
        id_vars=['Disciplinas'], value_vars=['Conteudos_Concluidos', 'Conteudos_Pendentes'],
        var_name='Status', value_name='Contagem'
    )
    df_melted['Status'] = df_melted['Status'].map({'Conteudos_Concluidos': 'Concluído', 'Conteudos_Pendentes': 'Pendente'})

    chart = alt.Chart(df_melted).mark_bar().encode(
        y=alt.Y('Disciplinas:N', sort=None, title=None),
        x=alt.X('sum(Contagem):Q', stack='normalize', axis=alt.Axis(format='%', title='Percentual')),
        color=alt.Color('Status:N', scale=alt.Scale(domain=['Concluído', 'Pendente'], range=['#2ecc71', '#e74c3c']), legend=alt.Legend(title='Status')),
        tooltip=[alt.Tooltip('Disciplinas:N'), alt.Tooltip('Status:N'), alt.Tooltip('sum(Contagem):Q', title='Nº de Conteúdos')]
    ).properties(height=300)
    return chart

def handle_checkbox_change(worksheet, row_number, key, conteudo_nome):
    novo_status = st.session_state[key]
    sucesso = update_status_in_sheet(worksheet, row_number, "TRUE" if novo_status else "FALSE")
    if sucesso:
        st.toast(f"✅ Status de '{conteudo_nome}' atualizado!", icon="✅")
        load_data_with_row_indices.clear()
    else:
        st.toast(f"❌ Falha ao atualizar '{conteudo_nome}'.", icon="❌")
        st.session_state[key] = not novo_status

def display_conteudos_com_checkboxes(df):
    worksheet = get_worksheet()
    if df.empty or worksheet is None:
        st.info("Nenhum dado disponível para exibir os conteúdos.")
        return

    disciplinas_ordenadas = sorted(df['Disciplinas'].unique())
    for disc in disciplinas_ordenadas:
        conteudos_disciplina = df[df['Disciplinas'] == disc]
        with st.expander(f"{disc.title()} ({len(conteudos_disciplina)} conteúdos)"):
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
    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('Disciplinas:N', sort=None, title=None),
        y=alt.Y('Questões:Q', title='Número de Questões'),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=['Disciplinas', 'Questões']
    )
    text = chart.mark_text(align='center', baseline='bottom', dy=-5).encode(text='Questões:Q')
    return (chart + text).properties(height=350)

def create_relevancia_pie_chart(ed_data):
    df = pd.DataFrame(ed_data)
    df['Relevancia'] = df['Peso'] * df['Questões']
    
    chart = alt.Chart(df).mark_arc(innerRadius=60).encode(
        theta=alt.Theta("Relevancia:Q"),
        color=alt.Color("Disciplinas:N", legend=alt.Legend(title="Disciplinas", orient="top")),
        tooltip=['Disciplinas', 'Peso', 'Questões', 'Relevancia']
    ).properties(height=400)
    return chart

def rodape_motivacional():
    st.markdown("""
    <footer style='font-size: 12px; color: #064820; font-weight: 600; margin-top: 2rem; text-align: center; font-family: Inter, sans-serif;'>
        🚀 Feito com Streamlit para impulsionar seus estudos! Bons estudos e boa sorte! ✨
    </footer>
    """, unsafe_allow_html=True)

# --- Função Principal da Aplicação ---
def main():
    st.set_page_config(
        page_title="📚 Dashboard de Estudos - Concurso TAE 2025",
        page_icon="📚",
        layout="wide"
    )

    render_topbar_with_logo(max((CONCURSO_DATE - datetime.now()).days, 0))
    
    df = load_data_with_row_indices()
    df_summary, progresso_geral = calculate_progress(df)
    stats = calculate_stats(df, df_summary)

    display_containers_metricas(stats, progresso_geral)
    st.markdown("---")

    titulo_com_destaque("📊 Progresso Detalhado por Disciplina", cor_lateral="#3498db")
    
    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.markdown("<h4 style='text-align: center;'>Percentual de Conclusão</h4>", unsafe_allow_html=True)
        if not df_summary.empty:
            altair_stacked_bar = create_altair_stacked_bar(df_summary)
            st.altair_chart(altair_stacked_bar, use_container_width=True)
        else:
            st.info("Não há dados de progresso para exibir o gráfico.")

    with col2:
        st.markdown("<h4 style='text-align: center;'>Progresso Individual</h4>", unsafe_allow_html=True)
        if not df_summary.empty:
            display_progress_donuts(df_summary)
    
    st.markdown("---")

    titulo_com_destaque("📝 Análise da Prova", cor_lateral="#e67e22")
    colA, colB = st.columns(2)
    with colA:
        st.markdown("<h4 style='text-align: center;'>Distribuição de Questões</h4>", unsafe_allow_html=True)
        questoes_chart = create_questoes_bar_chart(ED_DATA)
        st.altair_chart(questoes_chart, use_container_width=True)
    with colB:
        st.markdown("<h4 style='text-align: center;'>Relevância (Peso × Questões)</h4>", unsafe_allow_html=True)
        relevancia_chart = create_relevancia_pie_chart(ED_DATA)
        st.altair_chart(relevancia_chart, use_container_width=True)

    st.markdown("---")

    titulo_com_destaque("✅ Checklist de Conteúdos", cor_lateral="#8e44ad")
    display_conteudos_com_checkboxes(df)

    st.markdown("---")
    rodape_motivacional()

if __name__ == "__main__":
    main()
