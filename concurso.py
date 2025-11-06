import streamlit as st
import pandas as pd
import altair as alt

# Função para gerenciar progresso
def update_progress(completed_items, total_items):
    return round((completed_items / total_items) * 100, 2)

# Tópicos do concurso baseados no edital
topics = {
    "Língua Portuguesa": [
        "Interpretação de texto", "Ortografia oficial", "Acentuação gráfica", "Pontuação",
        "Classes de palavras", "Vozes verbais", "Concordância verbal e nominal", "Regência verbal e nominal",
        "Sintaxe", "Ocorrência de crase", "Sinônimos e antônimos", "Sentido próprio e figurado das palavras", 
        "Reorganização de orações", "Redação"
    ],
    "Raciocínio Lógico, Matemática Financeira e Estatística": [
        "Estrutura lógica", "Compreensão da lógica", "Lógica de relações", "Juros simples", "Juros compostos", 
        "Descontos simples e compostos", "Amortizações", "Fluxo de caixa", "Estatística descritiva", "Probabilidade"
    ],
    "Direito Constitucional": [
        "Constituição de 1988", "Aplicabilidade das normas constitucionais", "Direitos e garantias fundamentais", 
        "Organização do Estado", "Administração Pública", "Poderes do Estado", "Controle de constitucionalidade"
    ],
    "Direito Administrativo": [
        "Estado e Administração Pública", "Ato administrativo", "Agentes públicos", "Poderes da Administração Pública", 
        "Responsabilidade civil do Estado", "Serviços Públicos", "Licitações", "Improbidade administrativa"
    ],
    "Direito Tributário": [
        "Sistema Tributário Nacional", "Princípios gerais", "Impostos da União", "Impostos dos Estados", 
        "Impostos dos Municípios", "Obrigação tributária", "Responsabilidade tributária", "Crédito tributário"
    ],
    "Tecnologia da Informação": [
        "Fundamentos de Banco de Dados", "Administração de banco de dados", "Modelagem de dados", "Backup e restauração", 
        "Big Data", "Data Mining", "Sistemas NoSQL", "Gestão de Projetos", "Metodologias Ágeis", "Machine Learning"
    ],
    "Auditoria": [
        "Planejamento de Auditoria", "Amostragem em Auditoria", "Testes de observância", "Evidências de auditoria", 
        "Testes substantivos", "Identificação de fraudes", "Auditoria nas contas de resultado"
    ],
    "Contabilidade Avançada e de Custos": [
        "Mensuração a Valor Justo", "Instrumentos financeiros", "Ativo Imobilizado", "Redução ao valor recuperável", 
        "Demonstrações contábeis", "Custos controláveis", "Custo padrão", "Análise de custo x volume x lucro"
    ],
    "Legislação Tributária Estadual": [
        "Lei nº 11.651/1991", "Lei nº 16.469/09", "Processo administrativo tributário", "Substituição tributária do ICMS", 
        "Benefícios fiscais", "Lei Complementar nº 87/1996", "ICMS DIFAL-SN", "Nota Fiscal Eletrônica", "EFD ICMS/IPI"
    ]
}

# Organizar os dados em um DataFrame
def create_study_df():
    data = []
    for subject, subtopics in topics.items():
        for topic in subtopics:
            data.append([subject, topic, False])
    df = pd.DataFrame(data, columns=["Matéria", "Tópico", "Concluído"])
    return df

# Função para mostrar gráficos de progresso com animação usando Altair
def plot_progress(df):
    # Agrupar por matéria e calcular progresso
    progress_df = df.groupby("Matéria")["Concluído"].mean().reset_index()
    progress_df["Progresso (%)"] = progress_df["Concluído"] * 100

    # Criar gráfico interativo com animação
    chart = alt.Chart(progress_df).mark_bar().encode(
        x=alt.X("Progresso (%):Q", title="Progresso (%)", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("Matéria:N", sort='-x', title="Matérias"),
        color="Matéria:N",
        tooltip=["Matéria:N", "Progresso (%):Q"]
    ).properties(
        title="Progresso de Estudo por Matéria"
    ).configure_mark(
        opacity=0.7
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

# Inicializando a sessão do Streamlit
st.title("Dashboard de Estudo - Concurso Auditor Fiscal")

# Carregar o DataFrame
df = create_study_df()

# Sidebar para seleção de materiais
st.sidebar.header("Marque os Tópicos Estudados")
selected_subject = st.sidebar.selectbox("Escolha a Matéria", df["Matéria"].unique())

# Filtrar os tópicos selecionados pela matéria
selected_topics = df[df["Matéria"] == selected_subject]

# Exibir tópicos da matéria selecionada
for idx, row in selected_topics.iterrows():
    completed = st.checkbox(f"{row['Tópico']}", value=row['Concluído'], key=row['Tópico'])
    df.loc[idx, 'Concluído'] = completed

# Exibir gráficos de progresso com animação
st.header("Progresso de Estudo")
plot_progress(df)

# Exibir tabela de progresso detalhado
st.subheader("Detalhes do Progresso")
st.dataframe(df)

# Exibir a quantidade de tópicos estudados
completed_topics = df['Concluído'].sum()
total_topics = len(df)
study_progress = update_progress(completed_topics, total_topics)

st.markdown(f"### Progresso Total de Estudo: {study_progress}%")
