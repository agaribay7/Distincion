# app.py
import streamlit as st
import DistincionVaronil
import DistincionFemenil

# Selector en la barra lateral para elegir la aplicación
app_mode = st.sidebar.radio("Selecciona el equipo:", ["Varonil", "Femenil"])

if app_mode == "Varonil":
    DistincionVaronil.app()
elif app_mode == "Femenil":
    DistincionFemenil.app()
