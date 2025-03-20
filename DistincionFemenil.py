# archivo2.py
import streamlit as st
import pandas as pd
import altair as alt

def app():
    # Título del Dashboard
    st.title("Seguimiento de Partidos")

    # URL de Google Sheets convertido a CSV (asegúrate de que el documento sea público)
    sheet_url = "https://docs.google.com/spreadsheets/d/1mH9LNns0l8VuEotCGvHcdvFLDmDyeWRF9VGfyUt-oMc/export?format=csv&gid=1933926554"

    @st.cache_data
    def load_data(url):
        df = pd.read_csv(url)
        return df

    # Sidebar para filtros y actualización
    st.sidebar.header("Filtros")
    if st.sidebar.button("Actualizar datos", key="actualizar_datos2"):
        load_data.clear()  # Limpia la caché de la función load_data
        try:
            st.experimental_rerun()  # Fuerza la recarga del script si está disponible
        except AttributeError:
            pass

    # Cargar datos reales desde Google Sheets
    df = load_data(sheet_url)

    # Eliminar registros donde "Total PJ" es NaN y convertir "Total PJ" a entero
    df = df.dropna(subset=["Total PJ"])
    df["Total PJ"] = df["Total PJ"].astype(int)

    # Intentar convertir la columna "#" a entero (si es posible)
    try:
        df["#"] = df["#"].astype(int)
    except:
        pass

    # Filtro por jugador
    lista_jugadores = ['Todos'] + df['Nombre'].tolist()
    jugador_seleccionado = st.sidebar.selectbox("Selecciona Jugador", lista_jugadores)
    if jugador_seleccionado != 'Todos':
        df = df[df['Nombre'] == jugador_seleccionado]

    # Función auxiliar para determinar si un registro cumple la condición de alerta
    def is_alert(value):
        try:
            x = float(value)
        except:
            return False
        # Ignorar NaN y 0
        if pd.isna(x) or x == 0:
            return False
        next_milestone = ((int(x) // 50) + 1) * 50
        return (x % 50 == 0) or (x >= next_milestone - 5)

    # Preparar DataFrame para la tabla (conservando la columna '#' de la hoja)
    df_display = df[['#', 'Nombre', 'Total PJ']].copy()

    # Si la columna '#' no es única, se le añade un sufijo para garantizar unicidad
    if not df_display['#'].is_unique:
        df_display['temp_count'] = df_display.groupby('#').cumcount()
        df_display['#'] = df_display['#'].astype(str) + '-' + df_display['temp_count'].astype(str)
        df_display.drop(columns=['temp_count'], inplace=True)

    # Asegurarse de que las columnas sean únicas (por si acaso)
    df_display = df_display.loc[:, ~df_display.columns.duplicated()]

    # Si es posible, convertir la columna '#' a entero (manteniendo el formato numérico)
    if pd.api.types.is_numeric_dtype(df_display['#']):
        df_display['#'] = df_display['#'].astype(int)

    # Usar la columna '#' como índice para reemplazar la numeración automática
    df_display = df_display.set_index('#')
    df_display.index = df_display.index.astype(str)
    df_display = df_display[~df_display.index.duplicated(keep='first')]

    # Agregar columna de alerta para ordenar la tabla: 
    # primero se muestran los registros en alerta y luego, dentro de cada grupo, de mayor a menor "Total PJ"
    df_display['alert'] = df_display['Total PJ'].apply(is_alert)
    df_display = df_display.sort_values(by=['alert', 'Total PJ'], ascending=[False, False])
    df_display = df_display.drop(columns=['alert'])

    # Función para aplicar formato condicional a cada renglón en la tabla
    def highlight_row(row):
        try:
            x = float(row['Total PJ'])
        except:
            return ['text-align: left'] * len(row)
        # No resaltar si es NaN o 0
        if pd.isna(x) or x == 0:
            return ['text-align: left'] * len(row)
        next_milestone = ((int(x) // 50) + 1) * 50
        if (x % 50 == 0) or (x >= next_milestone - 5):
            return ['background-color: lightgreen; text-align: left'] * len(row)
        else:
            return ['text-align: left'] * len(row)

    # Aplicar el estilo condicional a la tabla
    styled_df = df_display.style.apply(highlight_row, axis=1)
    styled_df = styled_df.set_properties(subset=["Total PJ"], **{'text-align': 'left'})

    # Mostrar la tabla de datos con scroll
    st.subheader("Tabla de Partidos Jugados")
    st.dataframe(styled_df, height=390, width=800)

    # Sección de Alertas
    st.subheader("Alertas")
    def mostrar_alerta(jugador, partidos):
        if pd.isna(partidos) or int(partidos) == 0:
            return
        proximo_hito = ((int(partidos) // 50) + 1) * 50
        if int(partidos) % 50 == 0:
            st.success(f"¡{jugador} ha alcanzado {int(partidos)} partidos!")
        elif int(partidos) >= proximo_hito - 5:
            st.warning(f"{jugador} está cerca de alcanzar {proximo_hito} partidos (actual: {int(partidos)}).")

    for index, row in df.iterrows():
        mostrar_alerta(row["Nombre"], row["Total PJ"])

    # Gráfico de barras coloreado según alerta (usando Altair)
    st.subheader("Evolución de Partidos")
    df_chart = df.copy()
    df_chart['alert'] = df_chart['Total PJ'].apply(is_alert)
    chart = alt.Chart(df_chart).mark_bar().encode(
        # Ordenar el eje X de mayor a menor según "Total PJ"
        x=alt.X('Nombre:N', title='', sort=alt.SortField(field='Total PJ', order='descending'),
                axis=alt.Axis(labelAngle=-90, labelLimit=0, labelOverlap=False)),
        y=alt.Y('Total PJ:Q', title='', axis=alt.Axis(labelAngle=0)),
        color=alt.condition(
             alt.datum.alert,
             alt.value("lightgreen"),  # Color para alerta
             alt.value("steelblue")    # Color para los demás
        )
    ).properties(
        width=800,
        height=400
    )
    st.altair_chart(chart, use_container_width=True)
