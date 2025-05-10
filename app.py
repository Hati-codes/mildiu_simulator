import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

st.set_page_config(page_title="Simulador de Mildiu", layout="centered")
st.title("Simulador de Riesgo de Mildiu en Viñedo")

st.markdown("""
Este simulador detecta condiciones favorables para infecciones primarias de Mildiu basadas en la **Regla del 10-10-24**:
- Temperatura media ≥ 10 °C
- Precipitaciones ≥ 10 mm
- Humedad relativa ≥ 90%

Ahora puedes obtener datos directamente desde Open-Meteo introduciendo la latitud y longitud de tu viñedo.
""")

opcion = st.radio("Selecciona la fuente de datos:", ["Subir CSV", "Usar Open-Meteo"], horizontal=True)

if opcion == "Usar Open-Meteo":
    lat = st.number_input("Latitud del viñedo", value=41.97, format="%f")
    lon = st.number_input("Longitud del viñedo", value=3.13, format="%f")
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

            df['riesgo_mildiu'] = df.apply(evaluar_riesgo, axis=1)

            st.subheader("Resultados del análisis")
            st.dataframe(df)

            dias_alerta = df[df['riesgo_mildiu'] == "Riesgo ALTO"]['fecha'].tolist()
            if dias_alerta:
                st.warning(f"⚠️ Riesgo ALTO de Mildiu detectado en las siguientes fechas: {', '.join(dias_alerta)}")
            else:
                st.success("No se detectaron días con riesgo alto de Mildiu.")

            st.download_button(
                label="Descargar resultados en CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='riesgo_mildiu.csv',
                mime='text/csv'
            )

elif opcion == "Subir CSV":
    uploaded_file = st.file_uploader("Sube un archivo CSV con los datos meteorológicos", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("Vista previa de los datos:")
        st.dataframe(df.head())

        required_columns = {'fecha', 'temperatura_media', 'precipitacion_mm', 'humedad_relativa'}

        if not required_columns.issubset(df.columns):
            st.error(f"El CSV debe contener las columnas: {', '.join(required_columns)}")
        else:
            def evaluar_riesgo(row):
                if (row['temperatura_media'] >= 10 and
                    row['precipitacion_mm'] >= 10 and
                    row['humedad_relativa'] >= 90):
                    return "Riesgo ALTO"
                elif (row['temperatura_media'] >= 10 and row['precipitacion_mm'] >= 5):
                    return "Riesgo MEDIO"
                else:
                    return "Riesgo BAJO"

            df['riesgo_mildiu'] = df.apply(evaluar_riesgo, axis=1)

            st.subheader("Resultados del análisis")
            st.dataframe(df[['fecha', 'riesgo_mildiu']])

            dias_alerta = df[df['riesgo_mildiu'] == "Riesgo ALTO"]['fecha'].tolist()
            if dias_alerta:
                st.warning(f"⚠️ Riesgo ALTO de Mildiu detectado en las siguientes fechas: {', '.join(dias_alerta)}")
            else:
                st.success("No se detectaron días con riesgo alto de Mildiu.")

            st.download_button(
                label="Descargar resultados en CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='riesgo_mildiu.csv',
                mime='text/csv'
            )
    else:
        st.info("Esperando un archivo CSV con datos meteorológicos. Ejemplo:")
        ejemplo = pd.DataFrame({
            'fecha': ['2025-05-01', '2025-05-02'],
            'temperatura_media': [11.2, 9.5],
            'precipitacion_mm': [12.0, 3.0],
            'humedad_relativa': [92, 85]
        })
        st.dataframe(ejemplo)
