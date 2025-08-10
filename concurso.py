import streamlit as st
import pandas as pd
import altair as alt

ED_DATA = {
    'Disciplinas': ['LÍNGUA PORTUGUESA', 'RLM', 'INFORMÁTICA', 'LEGISLAÇÃO', 'CONHECIMENTOS ESPECÍFICOS'],
    'Questões': [10, 5, 5, 10, 20],
    'Peso': [2, 1, 1, 1, 3]
}

def titulo_com_destaque(texto, cor_lateral="#8e44ad"):
    st.markdown(f'''
    <div style="
        display: flex;
        align-items: center;
        border-left: 6px solid {cor_lateral};
        padding-left: 16px;
        background-color: #f5f5f5;
        padding: 12px 16px;
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

def chart_questoes_horizontal(df_ordenado, height):
    bars = alt.Chart(df_ordenado).mark_bar(stroke='#d3d3d3', strokeWidth=3).encode(
        y=alt.Y('Disciplinas:N', sort=alt.EncodingSortField(field='Questões', order='ascending'), title=None, axis=alt.Axis(labels=True, ticks=True)),
        x=alt.X('Questões:Q', title=None, axis=alt.Axis(labels=False, ticks=False, domain=False)),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=[alt.Tooltip('Disciplinas'), alt.Tooltip('Questões', title='Quantidade de Questões')],
    )
    texts = alt.Chart(df_ordenado).mark_text(align='left', baseline='middle', dx=3, fontSize=12, color='#064820').encode(
        y=alt.Y('Disciplinas:N', sort=alt.EncodingSortField(field='Questões', order='ascending')),
        x='Questões:Q',
        text='Questões:Q'
    )
    return (bars + texts).properties(width=350, height=height, title='Quantidade de Questões por Disciplina').configure_axis(grid=False, domain=False)

def bar_chart_ponderado(height):
    df = pd.DataFrame(ED_DATA)
    df['Questoes_Ponderadas'] = df['Questões'] * df['Peso']
    chart = alt.Chart(df).mark_bar(cornerRadius=5, stroke='#d3d3d3', strokeWidth=3).encode(
        x=alt.X('Disciplinas:N', sort='-y', title=None, axis=alt.Axis(labelAngle=0, labels=False, ticks=False, domain=False)),
        y=alt.Y('Questoes_Ponderadas:Q', title=None, axis=alt.Axis(labels=False, ticks=False, grid=False, domain=False)),
        color=alt.Color('Disciplinas:N', legend=None),
        tooltip=[alt.Tooltip('Disciplinas', title='Disciplina'), alt.Tooltip('Questoes_Ponderadas', title='Peso × Questões')]
    ).properties(width=600, height=height, title='Peso × Questões por Disciplina')

    text_labels = alt.Chart(df).mark_text(dy=-10, fontWeight='bold', fontSize=12, color='black').encode(
        x=alt.X('Disciplinas:N', sort='-y'),
        y='Questoes_Ponderadas:Q',
        text=alt.Text('Questoes_Ponderadas:Q')
    )

    text_disciplinas = alt.Chart(df).mark_text(align='center', dy=12, fontWeight='bold', fontSize=12, color='black').encode(
        x=alt.X('Disciplinas:N', sort='-y'),
        y=alt.value(height - 15),
        text='Disciplinas:N'
    )
    return (chart + text_labels + text_disciplinas).configure_view(strokeWidth=0)

def display_questoes_e_peso():
    df = pd.DataFrame(ED_DATA)
    if df.empty:
        st.info("Nenhum dado para mostrar.")
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

def main():
    st.set_page_config(page_title="Dashboard Questões e Peso", layout="wide")
    display_questoes_e_peso()

if __name__ == "__main__":
    main()
