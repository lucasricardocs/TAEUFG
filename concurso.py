import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import warnings
import json
import time
import requests

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Dashboard de Estudos - Câmara de Goiânia",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS - COM FAISCAS FUNCIONAIS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    [data-testid="stMainBlockContainer"] {
        background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 50%, #0f1419 100%);
        color: white;
        position: relative;
        overflow: hidden;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* FAISCAS SUBINDO */
    @keyframes sparkleUp {
        0% {
            bottom: -10px;
            opacity: 1;
            transform: translateX(0);
        }
        100% {
            bottom: 110vh;
            opacity: 0;
            transform: translateX(100px);
        }
    }

    .sparkle {
        position: fixed;
        width: 2px;
        height: 2px;
        background: radial-gradient(circle, #1a73e8 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
        z-index: 1;
        animation: sparkleUp var(--duration) linear infinite;
        box-shadow: 0 0 6px #1a73e8;
    }

    .sparkle.green {
        background: radial-gradient(circle, #34a853 0%, transparent 70%);
        box-shadow: 0 0 6px #34a853;
    }

    .sparkle.orange {
        background: radial-gradient(circle, #f57c00 0%, transparent 70%);
        box-shadow: 0 0 6px #f57c00;
    }

    .header-box {
        background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
        padding: 2rem;
        border-radius: 16px;
        display: flex;
        align-items: center;
        gap: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(26, 115, 232, 0.3);
    }

    .header-logo {
        flex-shrink: 0;
    }

    .header-logo img {
        max-width: 180px;
        height: auto;
    }

    .header-content {
        flex: 1;
        color: white;
    }

    .header-content h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 800;
    }

    .header-content p {
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
        opacity: 0.9;
    }

    .header-info {
        display: flex;
        gap: 1.5rem;
        background: rgba(255,255,255,0.1);
        padding: 1rem 1.5rem;
        border-radius: 12px;
    }

    .info-item {
        text-align: center;
    }

    .info-label {
        font-size: 0.75rem;
        opacity: 0.7;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    .info-value {
        font-size: 1rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }

    .section-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: white;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.8rem;
        border-bottom: 3px solid #1a73e8;
    }

    .metric-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        background: rgba(255,255,255,0.08);
        border-color: rgba(255,255,255,0.2);
        transform: translateY(-4px);
    }

    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #34a853;
        margin: 0.5rem 0;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #b0b0b0;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    .disc-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-left: 4px solid var(--cor);
        padding: 1.2rem;
        border-radius: 10px;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        transition: all 0.2s ease;
    }

    .disc-card:hover {
        background: rgba(255,255,255,0.08);
        transform: translateX(4px);
    }

    .disc-name {
        flex: 1;
        color: var(--cor);
        font-weight: 700;
        font-size: 1.05rem;
    }

    .disc-stats {
        font-size: 0.8rem;
        color: #b0b0b0;
    }

    .progress {
        flex: 1;
        background: rgba(255,255,255,0.1);
        height: 5px;
        border-radius: 5px;
        overflow: hidden;
        margin: 0 1rem;
    }

    .progress-bar {
        height: 100%;
        background: var(--cor);
        border-radius: 5px;
        transition: width 0.5s ease;
    }

    .pct {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--cor);
        min-width: 45px;
        text-align: right;
    }

    .conteudo-item {
        background: rgba(255,255,255,0.03);
        border-left: 3px solid rgba(255,255,255,0.2);
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 6px;
        font-size: 0.95rem;
        transition: all 0.2s ease;
    }

    .conteudo-item:hover {
        background: rgba(255,255,255,0.06);
        border-left-color: rgba(255,255,255,0.4);
    }

    .conteudo-item.done {
        opacity: 0.6;
        text-decoration: line-through;
        color: #80868b;
        border-left-color: #34a853;
    }

    .pizza-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .pizza-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        transition: all 0.3s ease;
    }

    .pizza-card:hover {
        background: rgba(255,255,255,0.08);
        border-color: rgba(255,255,255,0.2);
        transform: translateY(-4px);
    }

    .pizza-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.8rem;
        text-align: center;
    }

    .pizza-pct {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--cor);
        margin-top: 0.5rem;
    }

    .footer {
        text-align: center;
        color: #80868b;
        padding: 2rem 0;
        margin-top: 3rem;
        border-top: 1px solid rgba(255,255,255,0.1);
        font-size: 0.85rem;
    }

    @media (max-width: 1024px) {
        .pizza-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    @media (max-width: 640px) {
        .pizza-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<script>
function createSparkles() {
    const container = document.body;

    setInterval(() => {
        for (let i = 0; i < 5; i++) {
            const sparkle = document.createElement('div');
            sparkle.className = 'sparkle';

            const colors = ['', 'green', 'orange'];
            sparkle.classList.add(colors[Math.floor(Math.random() * colors.length)]);

            const duration = 3 + Math.random() * 2;
            sparkle.style.setProperty('--duration', duration + 's');

            const leftPos = Math.random() * window.innerWidth;
            sparkle.style.left = leftPos + 'px';

            container.appendChild(sparkle);

            setTimeout(() => sparkle.remove(), duration * 1000);
        }
    }, 500);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createSparkles);
} else {
    createSparkles();
}
</script>
""", unsafe_allow_html=True)

# CONFIGURAÇÕES
SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

CORES = {
    'LÍNGUA PORTUGUESA': '#d33427',
    'RLM': '#1f7c5c',
    'REALIDADE DE GOIÁS': '#0d47a1',
    'LEGISLAÇÃO APLICADA': '#6d28d9',
    'CONHECIMENTOS ESPECÍFICOS': '#f57c00'
}

# FUNÇÕES
def obter_data():
    hoje = datetime.now()
    meses = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
             7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    return f"{hoje.day} de {meses[hoje.month]} de {hoje.year}"

@st.cache_data(ttl=600)
def obter_temp():
    try:
        r = requests.get('https://api.open-meteo.com/v1/forecast',
                        params={'latitude': -15.8267, 'longitude': -48.9626, 'current': 'temperature_2m',
                                'temperature_unit': 'celsius', 'timezone': 'America/Sao_Paulo'}, timeout=5)
        if r.status_code == 200:
            return round(r.json()['current']['temperature_2m'], 1)
    except:
        pass
    return "N/A"

@st.cache_resource
def conectar():
    try:
        if 'gcp_service_account' in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
        else:
            with open('credentials.json', 'r') as f:
                creds = json.load(f)
        c = Credentials.from_service_account_info(creds,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
        return gspread.authorize(c)
    except Exception as e:
        st.error(f"Erro: {e}")
        return None

@st.cache_data(ttl=60)
def carregar_dados(client):
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        df = pd.DataFrame(ws.get_all_records())
        df['Status'] = df['Status'].astype(str).str.upper()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES'])
        return df
    except:
        return None

def atualizar(client, linha, novo_status):
    try:
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        ws.update_cell(linha, 4, str(novo_status))
        return True
    except:
        return False

def criar_pizza_chart(estudados, total):
    """Cria gráfico de pizza sem legenda"""
    data = pd.DataFrame({
        'Status': ['Estudado', 'Faltando'],
        'Quantidade': [estudados, total - estudados]
    })

    chart = alt.Chart(data).mark_arc(innerRadius=50, stroke=None).encode(
        theta=alt.Theta('Quantidade:Q'),
        color=alt.Color('Status:N', scale=alt.Scale(domain=['Estudado', 'Faltando'], 
                                                      range=['#34a853', '#ef5350'])),
        tooltip=[]
    ).properties(width=200, height=200).configure_arc(
        cornerRadius=8
    )

    return chart

# INTERFACE
def main():
    data = obter_data()
    temp = obter_temp()

    # Header
    st.markdown(f"""
    <div class="header-box">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Logo">
        </div>
        <div class="header-content">
            <h1>📚 Dashboard de Estudos</h1>
            <p>Acompanhamento - Concurso Câmara de Goiânia</p>
        </div>
        <div class="header-info">
            <div class="info-item">
                <div class="info-label">📍 Local</div>
                <div class="info-value">Goiânia - GO</div>
            </div>
            <div class="info-item">
                <div class="info-label">📅 Data</div>
                <div class="info-value">{data}</div>
            </div>
            <div class="info-item">
                <div class="info-label">🌡️ Temp</div>
                <div class="info-value">{temp}°C</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### ⚙️ Config")
        cargo = st.selectbox("Cargo:", ["Analista Técnico Legislativo", "Agente Administrativo"])
        st.markdown("---")
        if st.button("🔄 Recarregar"):
            st.cache_data.clear()
            st.rerun()

    client = conectar()
    if client is None:
        st.stop()

    with st.spinner("Carregando..."):
        df = carregar_dados(client)

    if df is None or len(df) == 0:
        st.error("Nenhum dado")
        st.stop()

    # Stats
    df_cargo = df[df['Cargo'] == cargo].copy()
    if len(df_cargo) == 0:
        st.warning("Sem dados")
        st.stop()

    total = len(df_cargo)
    estudados = df_cargo['Estudado'].sum()
    faltam = total - estudados
    pct = (estudados / total * 100) if total > 0 else 0

    # Métricas
    st.markdown('<div class="section-title">📊 Visão Geral</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""<div class="metric-card">
            <div style="font-size: 2rem;">📚</div>
            <div class="metric-value">{total}</div>
            <div class="metric-label">Total</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div class="metric-card">
            <div style="font-size: 2rem;">✅</div>
            <div class="metric-value">{estudados}</div>
            <div class="metric-label">Estudados</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""<div class="metric-card">
            <div style="font-size: 2rem;">⏳</div>
            <div class="metric-value">{faltam}</div>
            <div class="metric-label">Faltando</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""<div class="metric-card">
            <div style="font-size: 2rem;">🎯</div>
            <div class="metric-value">{pct:.0f}%</div>
            <div class="metric-label">Progresso</div>
        </div>""", unsafe_allow_html=True)

    # Análise Visual - Gráficos Gerais
    st.markdown('<div class="section-title">📈 Análise Visual</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        data_pizza = pd.DataFrame({
            'Status': ['Estudado', 'Faltando'],
            'Quantidade': [estudados, faltam]
        })
        chart = alt.Chart(data_pizza).mark_arc(innerRadius=60, stroke=None).encode(
            theta=alt.Theta('Quantidade:Q'),
            color=alt.Color('Status:N', scale=alt.Scale(domain=['Estudado', 'Faltando'], 
                                                          range=['#34a853', '#ef5350'])),
            tooltip=[]
        ).properties(width=300, height=300).configure_arc(cornerRadius=8)
        st.altair_chart(chart, use_container_width=True)

    with col2:
        stats_disc = df_cargo.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
        stats_disc.columns = ['Disciplina', 'Estudados', 'Total']
        stats_disc['Percentual'] = (stats_disc['Estudados'] / stats_disc['Total'] * 100).round(1)
        stats_disc = stats_disc.sort_values('Percentual', ascending=True)

        chart = alt.Chart(stats_disc).mark_bar(cornerRadius=6, stroke=None).encode(
            x=alt.X('Percentual:Q', scale=alt.Scale(domain=[0, 100])),
            y=alt.Y('Disciplina:N', sort='-x'),
            color=alt.Color('Percentual:Q', scale=alt.Scale(scheme='greens')),
            tooltip=[]
        ).properties(width=500, height=300)
        st.altair_chart(chart, use_container_width=True)

    # Pizza Charts por Disciplina em Grid 3x2
    st.markdown('<div class="section-title">🥧 Pizzas por Disciplina</div>', unsafe_allow_html=True)

    stats_disc = df_cargo.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
    stats_disc.columns = ['Disciplina', 'Estudados', 'Total']
    stats_disc['Percentual'] = (stats_disc['Estudados'] / stats_disc['Total'] * 100).round(1)

    # Criar grid de pizzas
    cols = st.columns(3)
    for idx, (_, row) in enumerate(stats_disc.iterrows()):
        with cols[idx % 3]:
            cor = CORES.get(row['Disciplina'], '#1a73e8')
            st.markdown(f"""
            <div class="pizza-card" style="--cor: {cor};">
                <div class="pizza-title">{row['Disciplina']}</div>
            </div>
            """, unsafe_allow_html=True)

            chart = criar_pizza_chart(int(row['Estudados']), int(row['Total']))
            st.altair_chart(chart, use_container_width=True)

            st.markdown(f"""
            <div style="text-align: center; color: {cor}; font-weight: 700; font-size: 1.4rem;">
                {row['Percentual']:.0f}%
            </div>
            """, unsafe_allow_html=True)

    # Disciplinas
    st.markdown('<div class="section-title">📚 Conteúdos por Disciplina</div>', unsafe_allow_html=True)

    disciplinas = sorted(df_cargo['Disciplinas'].unique().tolist())
    filtro = st.selectbox("Filtrar:", ["Todas"] + disciplinas)

    if filtro != "Todas":
        df_cargo = df_cargo[df_cargo['Disciplinas'] == filtro]

    df_cargo['linha'] = df_cargo.index + 2

    for disc in sorted(df_cargo['Disciplinas'].unique()):
        df_disc = df_cargo[df_cargo['Disciplinas'] == disc].copy()
        n_est = df_disc['Estudado'].sum()
        n_tot = len(df_disc)
        p = (n_est / n_tot * 100) if n_tot > 0 else 0
        cor = CORES.get(disc, '#1a73e8')

        st.markdown(f"""
        <div class="disc-card" style="--cor: {cor};">
            <div class="disc-name">{disc}</div>
            <div class="progress">
                <div class="progress-bar" style="width: {p}%; background: {cor};"></div>
            </div>
            <div class="pct">{p:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"📋 {n_tot} conteúdos"):
            for idx, row in df_disc.iterrows():
                col1, col2 = st.columns([0.05, 0.95])

                with col1:
                    check = st.checkbox("✓", value=bool(row['Estudado']), key=f"ch_{idx}",
                                      label_visibility="collapsed")

                    if check != bool(row['Estudado']):
                        with st.spinner("Salvando..."):
                            if atualizar(client, int(row['linha']), 'TRUE' if check else 'FALSE'):
                                time.sleep(0.2)
                                st.cache_data.clear()
                                st.rerun()

                with col2:
                    classe = "done" if row['Estudado'] else ""
                    st.markdown(f"""<div class="conteudo-item {classe}">
                        {'✓ ' if row['Estudado'] else ''}{row['Conteúdos']}
                    </div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="footer">Dashboard | Câmara Municipal de Goiânia | {datetime.now().strftime("%H:%M:%S")}</div>', 
               unsafe_allow_html=True)

if __name__ == "__main__":
    main()
