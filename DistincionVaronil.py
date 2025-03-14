import streamlit as st
import pandas as pd
import altair as alt
import plotly.graph_objects as go
import requests
import certifi  # Para verificación SSL
import gspread
from google.oauth2.service_account import Credentials
import time  # Para medir tiempos

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

def scrape_and_update():
    """
    Ejecuta el webscraping en las URLs de Transfermarkt, procesa la información 
    y actualiza la hoja de Google Sheets. Se muestran dos barras de progreso:
      - Una para el scraping
      - Otra para la actualización en la hoja
    """
    tiempo_inicio_total = time.time()
    
    # Configuración de la API de Google Sheets
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credenciales.json", scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(GOOGLE_SHEET_EDIT_URL).worksheet(SHEET_NAME)
    
    # Cargar datos desde Google Sheets (versión CSV)
    df = pd.read_csv(SHEET_URL)
    
    if "Transfermarkt URL" not in df.columns:
        st.error("La columna 'Transfermarkt URL' no se encontró en la hoja de cálculo.")
        return
    elif "Nombre" not in df.columns:
        st.error("La columna 'Nombre' no se encontró en la hoja de cálculo.")
        return
    else:
        resultados = []  # Lista para almacenar los resultados de cada jugador
        
        # Barra de progreso para el scraping
        total_jugadores = len(df)
        progress_scrape = st.progress(0)
        progress_text = st.empty()
        
        for i, (idx, fila) in enumerate(df.iterrows()):
            tm_url = fila["Transfermarkt URL"]
            nombre = fila["Nombre"]
    
            if not (isinstance(tm_url, str) and (tm_url.startswith("http://") or tm_url.startswith("https://"))):
                st.warning(f"La URL para {nombre} no es válida: {tm_url}")
                progress_scrape.progress(int((i + 1) / total_jugadores * 100))
                progress_text.text(f"Scraping: {int((i + 1) / total_jugadores * 100)}% completado")
                continue
    
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                response = requests.get(tm_url, headers=headers, verify=certifi.where())
            except requests.exceptions.SSLError as ssl_err:
                st.error(f"Error SSL al acceder a {nombre}: {ssl_err}")
                progress_scrape.progress(int((i + 1) / total_jugadores * 100))
                progress_text.text(f"Scraping: {int((i + 1) / total_jugadores * 100)}% completado")
                continue
    
            if response.status_code == 200:
                try:
                    tablas = pd.read_html(response.text)
                    if len(tablas) > 1:
                        tabla = tablas[1].iloc[:, [0, 2, 3]]
                        tabla.iloc[:, 2] = pd.to_numeric(tabla.iloc[:, 2], errors="coerce").fillna(0)
    
                        suma = {
                            "Liga MX": 0,
                            "Concacaf": 0,
                            "Mundial": 0,
                            "Libertadores": 0,
                            "Leagues Cup": 0,
                            "C. Campeones": 0,
                            "Campeones Cup": 0,
                            "Copa MX": 0
                        }
    
                        for _, row_table in tabla.iterrows():
                            competencia = str(row_table.iloc[1])
                            valor = row_table.iloc[2]
    
                            if "Liga MX" in competencia or "Liguilla" in competencia:
                                suma["Liga MX"] += valor
                            if "CONCACAF" in competencia:
                                suma["Concacaf"] += valor
                            if "Club World Cup" in competencia:
                                suma["Mundial"] += valor
                            if "Libertadores" in competencia:
                                suma["Libertadores"] += valor
                            if "Leagues Cup" in competencia:
                                suma["Leagues Cup"] += valor
                            if "Campeón de Campeones" in competencia or "Supercopa MX" in competencia:
                                suma["C. Campeones"] += valor
                            if "Campeones Cup" in competencia:
                                suma["Campeones Cup"] += valor
                            if "Copa MX" in competencia:
                                suma["Copa MX"] += valor
    
                        total_pj = sum(suma.values())
    
                        resultado = {
                            "Nombre": nombre,
                            "Liga MX": suma["Liga MX"],
                            "Concacaf": suma["Concacaf"],
                            "Mundial": suma["Mundial"],
                            "Libertadores": suma["Libertadores"],
                            "Leagues Cup": suma["Leagues Cup"],
                            "C. Campeones": suma["C. Campeones"],
                            "Campeones Cup": suma["Campeones Cup"],
                            "Copa MX": suma["Copa MX"],
                            "Total PJ": total_pj,
                            "Transfermarkt URL": tm_url
                        }
                        resultados.append(resultado)
                    else:
                        st.warning(f"No se encontró la tabla esperada en la página de {nombre}.")
                except Exception as e:
                    st.error(f"Error al procesar la página de {nombre}: {e}")
            else:
                st.error(f"Error al acceder a la página de {nombre}. Código de estado: {response.status_code}")
    
            progress_scrape.progress(int((i + 1) / total_jugadores * 100))
            progress_text.text(f"Scraping: {int((i + 1) / total_jugadores * 100)}% completado")
    
        progress_text.text("Scraping completado.")
    
        # Actualización en Google Sheets
        if resultados:
            df_final = pd.DataFrame(resultados)
            columnas = ["Nombre", "Liga MX", "Concacaf", "Mundial", "Libertadores", 
                        "Leagues Cup", "C. Campeones", "Campeones Cup", "Copa MX", 
                        "Total PJ", "Transfermarkt URL"]
            df_final = df_final[columnas]
    
            st.write("Actualizando Google Sheets...")
    
            total_actualizaciones = len(df_final)
            progress_update = st.progress(0)
            update_text = st.empty()
    
            for j, row in df_final.iterrows():
                try:
                    cell = sheet.find(row["Nombre"])
                    row_number = cell.row
                    new_values = []
                    for col in columnas[:-1]:
                        value = row[col]
                        new_values.append(int(value) if isinstance(value, (int, float)) else value)
                    sheet.update(f"B{row_number}", [new_values])
                    st.write(f"Actualizado: {row['Nombre']} en la fila {row_number}")
                except Exception as e:
                    st.warning(f"No se pudo actualizar {row['Nombre']}: {e}")
    
                update_text.text(f"Actualizando hoja: {int((j + 1) / total_actualizaciones * 100)}% completado")
                progress_update.progress(int((j + 1) / total_actualizaciones * 100))
    
            update_text.text("Actualización de Google Sheets completada.")
            st.success("Actualización de Google Sheets completada.")
        else:
            st.info("No se procesaron resultados.")
    
    tiempo_total = time.time() - tiempo_inicio_total
    st.caption(f"Tiempo total de ejecución: {tiempo_total:.2f} segundos")

def app():
    st.markdown('<p class="main-title">Seguimiento de Partidos</p>', unsafe_allow_html=True)
    
    st.sidebar.header("Controles")
    
    # Botón para ejecutar el webscraping y actualizar Google Sheets
    if st.sidebar.button("Actualizar datos Transfermarkt", key="actualizar_transfermarkt"):
        scrape_and_update()
        load_data.clear()
        st.rerun()
    
    # Cargar datos desde Google Sheets
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

    df_display = df[['#', 'Nombre', 'Total PJ']].copy()
    if not df_display['#'].is_unique:
        df_display['temp_count'] = df_display.groupby('#').cumcount()
        df_display['#'] = df_display['#'].astype(str) + '-' + df_display['temp_count'].astype(str)
        df_display.drop(columns=['temp_count'], inplace=True)
    
    df_display = df_display.loc[:, ~df_display.columns.duplicated()]
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
