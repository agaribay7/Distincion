import streamlit as st
import pandas as pd
import altair as alt
import plotly.graph_objects as go
import requests
import certifi  # Para verificación SSL
import gspread
from google.oauth2.service_account import Credentials
import time

# ==========================
# Estilos personalizados CSS
# ==========================
st.markdown(
    """
    <style>
        .main-title {
            font-size: 36px;
            text-align: center;
            color: #4CAF50;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .sub-title {
            font-size: 28px;
            text-align: center;
            color: #2E86C1;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .stDataFrame {
            border: 1px solid #ddd;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# URLs y constantes de Google Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/1mH9LNns0l8VuEotCGvHcdvFLDmDyeWRF9VGfyUt-oMc/export?format=csv&gid=1387277036"
GOOGLE_SHEET_EDIT_URL = "https://docs.google.com/spreadsheets/d/1mH9LNns0l8VuEotCGvHcdvFLDmDyeWRF9VGfyUt-oMc/edit?gid=1387277036"
SHEET_NAME = "Varonil"

@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    return df

def app():
    st.markdown('<p class="main-title">Seguimiento de Partidos</p>', unsafe_allow_html=True)
    
    # Botón para actualizar datos desde Google Sheets
    if st.sidebar.button("Actualizar datos"):
        load_data.clear()  # Limpia la caché de load_data
    
    # Al volver a ejecutar el script, se cargarán los datos actualizados
    df = load_data(SHEET_URL)
    df = df.dropna(subset=["Total PJ"])
    df["Total PJ"] = df["Total PJ"].astype(int)
    try:
        df["#"] = df["#"].astype(int)
    except:
        pass

    lista_jugadores = ['Todos'] + df['Nombre'].tolist()
    jugador_seleccionado = st.sidebar.selectbox("Selecciona Jugador", lista_jugadores)
    if jugador_seleccionado != 'Todos':
        df = df[df['Nombre'] == jugador_seleccionado]
    
    def alert_level(value):
        try:
            x = float(value)
        except:
            return 0
        if pd.isna(x) or x == 0:
            return 0
        next_milestone = ((int(x) // 50) + 1) * 50
        missing = next_milestone - x
        if (x % 50 == 0) or (missing <= 5):
            return 2
        elif missing <= 15:
            return 1
        else:
            return 0

    def is_alert(value):
        return alert_level(value) > 0

    # Preparación y ordenación de la tabla: primero alertas verdes, luego amarillas y después el resto,
    # todo ordenado por Total PJ de mayor a menor.
    df_display = df[['#', 'Nombre', 'Total PJ']].copy()
    if not df_display['#'].is_unique:
        df_display['temp_count'] = df_display.groupby('#').cumcount()
        df_display['#'] = df_display['#'].astype(str) + '-' + df_display['temp_count'].astype(str)
        df_display.drop(columns=['temp_count'], inplace=True)
    
    if pd.api.types.is_numeric_dtype(df_display['#']):
        df_display['#'] = df_display['#'].astype(int)
    df_display = df_display.set_index('#')
    df_display.index = df_display.index.astype(str)
    
    df_display['alert_level'] = df_display['Total PJ'].apply(alert_level)
    df_display = df_display.sort_values(by=['alert_level', 'Total PJ'], ascending=[False, False])
    df_alerts = df_display.copy()
    df_display = df_display.drop(columns=['alert_level'])
    
    def highlight_row(row):
        level = alert_level(row['Total PJ'])
        if level == 2:
            return ['background-color: lightgreen; text-align: left'] * len(row)
        elif level == 1:
            return ['background-color: #FFFFE0; text-align: left'] * len(row)
        else:
            return ['text-align: left'] * len(row)
    
    styled_df = df_display.style.apply(highlight_row, axis=1)
    styled_df = styled_df.set_properties(subset=["Total PJ"], **{'text-align': 'left'})
    
    st.markdown('<p class="sub-title">Tabla de Partidos Jugados</p>', unsafe_allow_html=True)
    st.dataframe(styled_df, height=390, width=800)
    
    st.markdown('<p class="sub-title">Alertas</p>', unsafe_allow_html=True)
    with st.container():
        for index, row in df_alerts.iterrows():
            level = alert_level(row["Total PJ"])
            if level > 0:
                total = int(row["Total PJ"])
                next_milestone = ((total // 50) + 1) * 50
                missing = next_milestone - total
                if level == 2:
                    if total % 50 == 0:
                        st.success(f"¡{row['Nombre']} ha alcanzado {total} partidos!")
                    else:
                        st.warning(f"{row['Nombre']} está muy cerca de alcanzar {next_milestone} partidos (actual: {total}).")
                elif level == 1:
                    st.info(f"{row['Nombre']} está a {missing} partidos de alcanzar {next_milestone} partidos (actual: {total}).")
    
    st.markdown('<p class="sub-title">Evolución de Partidos</p>', unsafe_allow_html=True)
    df_chart = df.copy()
    df_chart['alert'] = df_chart['Total PJ'].apply(is_alert)
    chart = alt.Chart(df_chart).mark_bar().encode(
        x=alt.X('Nombre:N', title='', sort=alt.SortField(field='Total PJ', order='descending'),
                axis=alt.Axis(labelAngle=-90)),
        y=alt.Y('Total PJ:Q', title=''),
        color=alt.condition(
            alt.datum.alert,
            alt.value("lightgreen"),
            alt.value("steelblue")
        )
    ).properties(width=800, height=400)
    st.altair_chart(chart, use_container_width=True)
    
    if jugador_seleccionado != 'Todos' and not df[df['Nombre'] == jugador_seleccionado].empty:
        player_row = df[df['Nombre'] == jugador_seleccionado].iloc[0]
        total_pj = int(player_row["Total PJ"])
        next_milestone = ((total_pj // 50) + 1) * 50
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=total_pj,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Progreso de {jugador_seleccionado}"},
            delta={'reference': next_milestone, 'increasing': {'color': "RebeccaPurple"}},
            gauge={
                'axis': {'range': [0, next_milestone]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, next_milestone * 0.5], 'color': "lightgray"},
                    {'range': [next_milestone * 0.5, next_milestone], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': next_milestone
                }
            }
        ))
        st.markdown('<p class="sub-title">Progreso hacia el siguiente hito</p>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    app()
