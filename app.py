
import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
from opencage.geocoder import OpenCageGeocode
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Simulador de Mildiu", layout="centered")
st.title("🌿 Simulador de Riesgo de Mildiu en Viñedos")

st.markdown("""
Este simulador detecta condiciones favorables para infecciones primarias de Mildiu basadas en la **Regla del 10-10-24**:
- Temperatura media ≥ 10 °C
- Precipitaciones ≥ 10 mm
- Humedad relativa ≥ 90%

Usa datos meteorológicos reales desde **Open-Meteo** y búsqueda con **OpenCage Geocoder**.
""")

# --- Entrada de dirección y geolocalización con OpenCage
API_KEY = "5974c1978f29424299346fd76e0378bd"
geocoder = OpenCageGeocode(API_KEY)

address = st.text_input("Introduce una dirección o ciudad para localizar tu viñedo:")

lat, lon = None, None

if address:
    results = geocoder.geocode(address)

    if results and len(results):
        result = results[0]
        lat = result["geometry"]["lat"]
        lon = result["geometry"]["lng"]
        full_address = result["formatted"]

        st.success(f"Ubicación: {full_address}")
        st.write(f"Lat: {lat:.4f}, Lon: {lon:.4f}")

        m = folium.Map(location=[lat, lon], zoom_start=12)
        folium.Marker([lat, lon], tooltip="Ubicación del viñedo").add_to(m)
        st_folium(m, width=700, height=500)
    else:
        st.error("No se pudo encontrar la ubicación. Revisa la dirección.")

# --- Simulación si hay coordenadas
if lat and lon:
    dias = st.slider("Días atrás para analizar", 1, 14, 7)
    prediccion = st.checkbox("Incluir predicción para los próximos 3 días")

    if st.button("Obtener datos y analizar"):
        fecha_hoy = date.today()
        fecha_inicio = fecha_hoy - timedelta(days=dias)
        fecha_fin = fecha_hoy + timedelta(days=3) if prediccion else fecha_hoy

        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&start_date={fecha_inicio}&end_date={fecha_fin}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_max"
            f"&timezone=Europe/Madrid"
        )

        r = requests.get(url)
        if r.status_code != 200:
            st.error("No se pudieron obtener los datos meteorológicos.")
        else:
            data = r.json()['daily']
            df = pd.DataFrame({
                'fecha': data['time'],
                'temperatura_media': [(max_ + min_) / 2 for max_, min_ in zip(data['temperature_2m_max'], data['temperature_2m_min'])],
                'precipitacion_mm': data['precipitation_sum'],
                'humedad_relativa': data['relative_humidity_2m_max']
            })

            def evaluar_riesgo(row):
                if (row['temperatura_media'] >= 10 and
                    row['precipitacion_mm'] >= 10 and
                    row['humedad_relativa'] >= 90):
                    return "Riesgo ALTO"
                elif (row['temperatura_media'] >= 10 and row['precipitacion_mm'] >= 5):
                    return "Riesgo MEDIO"
                else:
                    return "Riesgo BAJO"

            

def interpretar_riesgo(row):
    if row['riesgo_mildiu'] == "Riesgo ALTO":
        if row['precipitacion_mm'] >= 15 and row['humedad_relativa'] >= 95:
            return "🌧️ Lluvias intensas y humedad extrema: condiciones críticas para brote."
        else:
            return "🌦️ Se cumplen los criterios clave para infección primaria de mildiu."
    elif row['riesgo_mildiu'] == "Riesgo MEDIO":
        if row['precipitacion_mm'] >= 5:
            return "💧 Humedad y temperatura favorables, pero lluvia no alcanza umbral alto."
        else:
            return "🌤️ Temperatura adecuada, pero condiciones aún no son óptimas para brote."
    else:
        return "🌞 Condiciones secas o frías: riesgo muy bajo de infección."

df['riesgo_mildiu'] = df.apply(evaluar_riesgo, axis=1)
    df['interpretacion'] = df.apply(interpretar_riesgo, axis=1)

            st.subheader("📊 Resultados del análisis")
            st.dataframe(df[['fecha', 'temperatura_media', 'precipitacion_mm', 'humedad_relativa', 'riesgo_mildiu', 'interpretacion']])

            dias_alerta = df[df['riesgo_mildiu'] == "Riesgo ALTO"]['fecha'].tolist()
            if dias_alerta:
                st.warning("⚠️ Riesgo ALTO detectado en: " + ", ".join(dias_alerta))
            else:
                st.success("No se detectaron días con riesgo alto de Mildiu.")

            st.download_button(
                label="📥 Descargar resultados en CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='riesgo_mildiu.csv',
                mime='text/csv'
            )
else:
    st.info("Introduce una ubicación válida para comenzar.")
