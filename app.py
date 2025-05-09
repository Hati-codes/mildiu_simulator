
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from meteostat import Point, Daily
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Simulador de Mildiu Avanzado", layout="centered")
st.title("🌿 Simulador de Riesgo de Mildiu con Búsqueda Inteligente")

# --- BÚSQUEDA AVANZADA DE UBICACIÓN USANDO PHOTON ---
st.header("📍 Buscar ubicación")
query = st.text_input("Introduce una dirección o localidad:")

lat, lon = None, None

if query:
    photon_url = f"https://photon.komoot.io/api/?q={query}&limit=5"
    r = requests.get(photon_url)
    resultados = r.json().get("features", [])

    opciones = [f"{f['properties']['name']}, {f['properties'].get('country', '')}" for f in resultados]
    seleccion = st.selectbox("Selecciona una ubicación:", opciones) if opciones else None

    if seleccion:
        idx = opciones.index(seleccion)
        coords = resultados[idx]["geometry"]["coordinates"]
        lon, lat = coords[0], coords[1]

        st.success(f"Ubicación seleccionada: {seleccion}")
        st.write(f"Latitud: {lat:.4f}, Longitud: {lon:.4f}")

        m = folium.Map(location=[lat, lon], zoom_start=12)
        folium.Marker([lat, lon], tooltip="Ubicación seleccionada").add_to(m)
        st_folium(m, width=700, height=500)

# --- PARÁMETROS Y ANÁLISIS CON METEOSTAT ---
if lat and lon:
    st.header("📈 Análisis meteorológico con Meteostat")

    dias = st.slider("¿Cuántos días atrás deseas analizar?", 1, 30, 10)

    end = datetime.today()
    start = end - timedelta(days=dias)

    location = Point(lat, lon)
    data = Daily(location, start, end)
    data = data.fetch()

    if not data.empty:
        df = data.reset_index()
        df["fecha"] = df["time"].dt.date
        df["temperatura_media"] = (df["tmax"] + df["tmin"]) / 2
        df.rename(columns={"prcp": "precipitacion_mm", "rhum": "humedad_relativa"}, inplace=True)

        # --- RIESGO DE MILDIU ---
        def evaluar_riesgo(row):
            if (row["temperatura_media"] >= 10 and
                row["precipitacion_mm"] >= 10 and
                row.get("humedad_relativa", 90) >= 90):
                return "Riesgo ALTO"
            elif (row["temperatura_media"] >= 10 and row["precipitacion_mm"] >= 5):
                return "Riesgo MEDIO"
            else:
                return "Riesgo BAJO"

        df["riesgo_mildiu"] = df.apply(evaluar_riesgo, axis=1)

        st.subheader("📊 Resultados del análisis")
        st.dataframe(df[["fecha", "temperatura_media", "precipitacion_mm", "riesgo_mildiu"]])

        dias_alerta = df[df["riesgo_mildiu"] == "Riesgo ALTO"]["fecha"].tolist()
        if dias_alerta:
            st.warning("⚠️ Riesgo ALTO de Mildiu detectado en: " + ", ".join([str(d) for d in dias_alerta]))
        else:
            st.success("No se detectaron días con riesgo alto de Mildiu.")

        st.download_button(
            label="📥 Descargar CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="riesgo_mildiu_meteostat.csv",
            mime="text/csv"
        )
    else:
        st.error("No se encontraron datos meteorológicos para esta ubicación.")

else:
    st.info("Introduce una dirección y selecciona una ubicación para comenzar.")
