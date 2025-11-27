
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
    page_title="Dashboard de Estudos",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================================
# CSS CORRIGIDO - GRID LAYOUT & CORES VIBRANTES
# ================================================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    /* Background Claro e Fonte Escura (Alto Contraste) */
    html, body, [data-testid="stMainBlockContainer"] {
        background: #f3f4f6; /* Cinza muito suave para contraste */
        color: #111827; /* Quase preto para leitura perfeita */
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ============================
       HEADER GRID SYSTEM (RESOLVE CENTRALIZAÇÃO)
       ============================ */
    .header-container {
        display: grid;
        /* 3 Colunas: Logo (Auto) | Título (1fr - ocupa tudo) | Info (Auto) */
        grid-template-columns: auto 1fr auto;
        align-items: center;
        gap: 1rem;
        
        /* Gradiente Azul Mais Escuro para Contraste do Texto Branco */
        background: linear-gradient(135deg, #0f5cbd 0%, #003380 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(0, 51, 128, 0.25);
        color: white;
        position: relative;
        overflow: hidden;
        z-index: 10;
    }

    /* LOGO MAIOR (1.8x) */
    .header-logo img {
        max-width: 280px; /* Aumentado significativamente */
        height: auto;
        filter: drop-shadow(0 4px 6px rgba(0,0,0,0.3));
        display: block;
    }

    /* TÍTULO CENTRALIZADO NO CONTAINER */
    .header-content {
        text-align: center; /* Força o texto a centralizar na coluna do meio */
        padding: 0 1rem;
    }

    .header-content h1 {
        margin: 0;
        font-size: 2.4rem;
        font-weight: 800;
        color: #ffffff;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        line-height: 1.2;
    }

    .header-content p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        font-weight: 500;
        color: #e0e7ff; /* Azul claríssimo para subtítulo */
    }

    /* INFO NO CANTO DIREITO (AGORA VISÍVEL) */
    .header-info {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        text-align: right;
        min-width: 140px; /* Garante espaço */
        background: rgba(0, 0, 0, 0.2); /* Fundo translúcido para garantir leitura */
        padding: 0.8rem 1.2rem;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
    }

    .info-row {
        font-size: 0.9rem;
        color: #ffffff;
        font-weight: 600;
        white-space: nowrap;
    }
    
    .info-icon { margin-right: 6px; opacity: 0.9; }

    /* ============================
       FAGULHAS (CORES ESCURAS PARA FUNDO CLARO)
       ============================ */
    #sparkles-container {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        pointer-events: none;
        z-index: 0; /* Fica atrás do conteúdo */
        overflow: hidden;
    }

    @keyframes floatUp {
        0% { transform: translateY(100vh) scale(0.5); opacity: 0; }
        20% { opacity: 0.8; }
        100% { transform: translateY(-20vh) scale(1.2); opacity: 0; }
    }

    .spark {
        position: absolute;
        border-radius: 50%;
        opacity: 0;
        animation: floatUp linear forwards;
    }

    /* Cores vibrantes que aparecem no branco */
    .spark.blue { background: rgba(37, 99, 235, 0.6); box-shadow: 0 0 10px rgba(37, 99, 235, 0.4); }
    .spark.green { background: rgba(22, 163, 74, 0.6); box-shadow: 0 0 10px rgba(22, 163, 74, 0.4); }
    .spark.orange { background: rgba(234, 88, 12, 0.6); box-shadow: 0 0 10px rgba(234, 88, 12, 0.4); }

    /* ============================
       CARDS E MÉTRICAS (CONTRASTE MELHORADO)
       ============================ */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid #e5e7eb;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-5px); border-color: #2563eb; }

    .metric-value { font-size: 2.8rem; font-weight: 800; color: #15803d; line-height: 1; }
    .metric-label { font-size: 0.9rem; color: #4b5563; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-top: 0.5rem; }

    .disc-card {
        background: white;
        padding: 1.2rem;
        border-radius: 10px;
        margin-bottom: 0.8rem;
        border: 1px solid #e5e7eb;
        border-left: 5px solid var(--cor);
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        display: flex; align-items: center; gap: 1rem;
    }
    .disc-name { color: #111827; font-weight: 700; font-size: 1.05rem; flex: 1; }
    
    .progress { background: #e5e7eb; height: 8px; border-radius: 4px; flex: 1; margin: 0 1rem; }
    .progress-bar { height: 100%; border-radius: 4px; transition: width 0.5s; }

    /* Responsividade para o Grid do Header */
    @media (max-width: 900px) {
        .header-container {
            grid-template-columns: 1fr; /* 1 coluna */
            text-align: center;
            gap: 1.5rem;
        }
        .header-content { padding: 0; }
        .header-info { 
            align-items: center; 
            text-align: center; 
            background: none;
            border: none;
            flex-direction: row;
            justify-content: center;
            flex-wrap: wrap;
        }
        .header-logo img { margin: 0 auto; max-width: 200px; }
    }
</style>

<!-- Container para Fagulhas -->
<div id="sparkles-container"></div>

<script>
    // Script de Fagulhas Otimizado para Fundo Claro
    function createSparkle() {
        const container = document.getElementById('sparkles-container');
        if (!container) return;

        const el = document.createElement('div');
        el.classList.add('spark');
        
        // Cores aleatórias
        const types = ['blue', 'green', 'orange'];
        el.classList.add(types[Math.floor(Math.random() * types.length)]);

        // Tamanho aleatório
        const size = Math.random() * 10 + 5; // 5px a 15px
        el.style.width = size + 'px';
        el.style.height = size + 'px';

        // Posição inicial
        el.style.left = Math.random() * 100 + 'vw';
        
        // Duração da animação
        const duration = Math.random() * 3 + 4; // 4s a 7s
        el.style.animationDuration = duration + 's';

        container.appendChild(el);

        // Remove element after animation
        setTimeout(() => {
            el.remove();
        }, duration * 1000);
    }

    // Iniciar loop
    setInterval(createSparkle, 300); // Cria uma fagulha a cada 300ms
</script>
""", unsafe_allow_html=True)

# ================================================================================
# CONFIGURAÇÕES & DADOS
# ================================================================================

SPREADSHEET_ID = '17yHltbtCgZfHndifV5x6tRsVQrhYs7ruwWKgrmLNmGM'
WORKSHEET_NAME = 'Registro'
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/TAEUFG/main/1_Assinatura-principal_horizontal_Camara-Municipal-de-Goiania.png"

CORES = {
    'LÍNGUA PORTUGUESA': '#d33427',
    'RLM': '#1f7c5c',
    'REALIDADE DE GOIÁS': '#0d47a1',
    'LEGISLAÇÃO APLICADA': '#6d28d9',
    'CONHECIMENTOS ESPECÍFICOS': '#e65100' # Laranja mais escuro para contraste
}

EMOJIS = {
    'LÍNGUA PORTUGUESA': '📖', 'RLM': '🧮', 'REALIDADE DE GOIÁS': '🗺️',
    'LEGISLAÇÃO APLICADA': '⚖️', 'CONHECIMENTOS ESPECÍFICOS': '💡'
}

# ================================================================================
# FUNÇÕES
# ================================================================================

def obter_data():
    hoje = datetime.now()
    meses = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho',
             7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
    return f"{hoje.day} de {meses[hoje.month]} de {hoje.year}"

@st.cache_data(ttl=600)
def obter_temp():
    try:
        r = requests.get('https://api.open-meteo.com/v1/forecast',
            params={'latitude': -15.8267, 'longitude': -48.9626, 'current': 'temperature_2m', 'timezone': 'America/Sao_Paulo'}, timeout=3)
        if r.status_code == 200:
            return round(r.json()['current']['temperature_2m'], 1)
    except:
        pass
    return "--"

def conectar():
    try:
        if 'gcp_service_account' in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
        else:
            with open('credentials.json', 'r') as f: creds = json.load(f)
        return gspread.authorize(Credentials.from_service_account_info(creds, scopes=['https://www.googleapis.com/auth/spreadsheets']))
    except Exception as e:
        st.error(f"Erro conexão: {e}")
        return None

@st.cache_data(ttl=10)
def carregar_dados(_client):
    try:
        ws = _client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        df = pd.DataFrame(ws.get_all_records())
        df['Status'] = df['Status'].astype(str).str.upper()
        df['Estudado'] = df['Status'].isin(['TRUE', 'VERDADEIRO', '1', 'SIM', 'YES'])
        return df
    except: return None

def atualizar(client, linha, novo_status):
    try:
        client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME).update_cell(linha, 4, str(novo_status))
        return True
    except: return False

@st.cache_data
def criar_pizza_chart(estudados, total):
    data = pd.DataFrame({'Status': ['Estudado', 'Faltando'], 'Quantidade': [estudados, total - estudados]})
    return alt.Chart(data).mark_arc(innerRadius=60, cornerRadius=5).encode(
        theta=alt.Theta('Quantidade:Q'),
        color=alt.Color('Status:N', scale=alt.Scale(domain=['Estudado', 'Faltando'], range=['#22c55e', '#ef4444'])),
        tooltip=['Status', 'Quantidade']
    ).properties(width=220, height=220)

# ================================================================================
# APP
# ================================================================================

def main():
    data_hoje = obter_data()
    temp = obter_temp()

    # --- HEADER ESTRUTURADO EM GRID ---
    st.markdown(f"""
    <div class="header-container">
        <div class="header-logo">
            <img src="{LOGO_URL}" alt="Logo">
        </div>
        <div class="header-content">
            <h1>📚 Dashboard de Estudos</h1>
            <p>Acompanhamento - Concurso Câmara de Goiânia</p>
        </div>
        <div class="header-info">
            <div class="info-row"><span class="info-icon">📍</span> Goiânia - GO</div>
            <div class="info-row"><span class="info-icon">📅</span> {data_hoje}</div>
            <div class="info-row"><span class="info-icon">🌡️</span> {temp}°C</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        cargo = st.selectbox("Cargo:", ["Analista Técnico Legislativo", "Agente Administrativo"])
        st.markdown("---")
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Lógica de Dados
    client = conectar()
    if not client: st.stop()
    
    df = carregar_dados(client)
    if df is None: st.warning("Carregando dados..."); st.stop()

    df_cargo = df[df['Cargo'] == cargo].copy()
    if df_cargo.empty: st.info("Selecione um cargo válido."); st.stop()

    # Cálculos
    total = len(df_cargo)
    estudados = df_cargo['Estudado'].sum()
    faltam = total - estudados
    pct = (estudados / total * 100) if total > 0 else 0
    df_cargo['linha'] = df_cargo.index + 2

    # --- KPI CARDS ---
    st.markdown("### 📊 Visão Geral")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#2563eb">{total}</div><div class="metric-label">Total Tópicos</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#16a34a">{estudados}</div><div class="metric-label">Concluídos</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#ea580c">{faltam}</div><div class="metric-label">Pendentes</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#9333ea">{pct:.0f}%</div><div class="metric-label">Progresso Geral</div></div>', unsafe_allow_html=True)

    # --- GRÁFICOS ---
    st.markdown("### 📈 Desempenho por Disciplina")
    
    # Agrupamento
    stats = df_cargo.groupby('Disciplinas').agg({'Estudado': ['sum', 'count']}).reset_index()
    stats.columns = ['Disciplina', 'Estudados', 'Total']
    stats['Percentual'] = (stats['Estudados'] / stats['Total'] * 100).round(0)
    
    # Grid de Pizzas
    cols = st.columns(3)
    for i, row in stats.iterrows():
        with cols[i % 3]:
            cor = CORES.get(row['Disciplina'], '#333')
            st.markdown(f"<div style='text-align:center; font-weight:bold; color:{cor}; margin-top:1rem'>{row['Disciplina']}</div>", unsafe_allow_html=True)
            chart = criar_pizza_chart(row['Estudados'], row['Total'])
            st.altair_chart(chart, use_container_width=True)
            st.markdown(f"<div style='text-align:center; font-size:1.5rem; font-weight:bold; margin-top:-10px'>{int(row['Percentual'])}%</div>", unsafe_allow_html=True)

    # --- LISTA DE CONTEÚDOS ---
    st.markdown("### 📚 Check-list de Conteúdos")
    filtro = st.selectbox("Filtrar Disciplina:", ["Todas"] + sorted(df_cargo['Disciplinas'].unique().tolist()))
    
    if filtro != "Todas":
        df_view = df_cargo[df_cargo['Disciplinas'] == filtro]
    else:
        df_view = df_cargo

    for disc in df_view['Disciplinas'].unique():
        df_disc = df_view[df_view['Disciplinas'] == disc]
        p_disc = (df_disc['Estudado'].sum() / len(df_disc) * 100)
        cor = CORES.get(disc, '#333')
        
        st.markdown(f"""
        <div class="disc-card" style="--cor:{cor}">
            <div class="disc-name">{EMOJIS.get(disc,'')} {disc}</div>
            <div class="progress"><div class="progress-bar" style="width:{p_disc}%; background:{cor}"></div></div>
            <div class="pct">{p_disc:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"Ver Tópicos ({len(df_disc)})"):
            for idx, row in df_disc.iterrows():
                c_check, c_text = st.columns([0.05, 0.95])
                with c_check:
                    is_checked = st.checkbox("Concluído", value=bool(row['Estudado']), key=f"chk_{idx}", label_visibility="collapsed")
                
                if is_checked != bool(row['Estudado']):
                    if atualizar(client, int(row['linha']), 'TRUE' if is_checked else 'FALSE'):
                        st.toast("Status Atualizado!", icon="✅")
                        time.sleep(0.5)
                        st.rerun()

                classe = "done" if row['Estudado'] else ""
                c_text.markdown(f'<div class="conteudo-item {classe}">{row["Conteúdos"]}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
