
import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
from opencage.geocoder import OpenCageGeocode



# ---------------------- CONFIGURACIÓN INICIAL ---------------------- #

st.set_page_config(page_title="Simulador de Mildiu", layout="centered")
st.markdown("<h1 style='text-align:center;'>🌿 Simulador de Riesgo de Mildiu</h1>", unsafe_allow_html=True)

st.markdown("""
Este simulador detecta condiciones favorables para infecciones primarias de Mildiu basadas en la **Regla del 10-10-24**:
- Temperatura media ≥ 10 °C
- Precipitaciones ≥ 10 mm
- Humedad relativa ≥ 90%
""")

# ---------------------- FUNCIONES ---------------------- #

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

# ---------------------- UBICACIÓN ---------------------- #

API_KEY = "5974c1978f29424299346fd76e0378bd"
geocoder = OpenCageGeocode(API_KEY)

if "lat" not in st.session_state:
    st.session_state.lat = None
    st.session_state.lon = None
    st.session_state.address_str = ""

address = st.text_input("📍 Introduce la dirección o localidad del viñedo:", value=st.session_state.address_str)
buscar = st.button("🔍 Buscar ubicación")

if buscar and address:
    results = geocoder.geocode(address)
    if results and len(results):
        result = results[0]
        st.session_state.lat = result["geometry"]["lat"]
        st.session_state.lon = result["geometry"]["lng"]
        st.session_state.address_str = result["formatted"]

lat, lon = st.session_state.lat, st.session_state.lon

if lat and lon:
    st.success(f"Ubicación: {st.session_state.address_str}")
    st.write(f"Lat: {lat:.4f}, Lon: {lon:.4f}")

    st.markdown(f"📍 **Ubicación:** {st.session_state.address_str}")
    st.markdown(f"🧭 **Coordenadas:** Lat {lat:.4f}, Lon {lon:.4f}")
    dias = st.slider("📆 Días atrás a considerar", 1, 14, 7)
    prediccion = st.checkbox("📈 Incluir predicción para los próximos 3 días")

    st.markdown("## 🔬 Análisis meteorológico y riesgo de mildiu")
    if st.button("🔍 Analizar riesgo"):
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

            df['riesgo_mildiu'] = df.apply(evaluar_riesgo, axis=1)
            df['interpretacion'] = df.apply(interpretar_riesgo, axis=1)

            df['fecha'] = pd.to_datetime(df['fecha'])
            fechas_alto = df[df['riesgo_mildiu'] == "Riesgo ALTO"]['fecha'].sort_values().reset_index(drop=True)

            brotes = []
            grupo = []

            for i in range(len(fechas_alto)):
                if not grupo:
                    grupo.append(fechas_alto[i])
                elif (fechas_alto[i] - grupo[-1]).days <= 1:
                    grupo.append(fechas_alto[i])
                else:
                    if len(grupo) >= 3:
                        brotes.append((grupo[0], grupo[-1]))
                    grupo = [fechas_alto[i]]

            if len(grupo) >= 3:
                brotes.append((grupo[0], grupo[-1]))

            st.markdown("### 📊 Resultados del análisis")

            # 🧠 Resumen inteligente del riesgo
            riesgo_counts = df['riesgo_mildiu'].value_counts()
            total_dias = len(df)
            resumen = []

            if 'Riesgo ALTO' in riesgo_counts:
                resumen.append(f"{riesgo_counts['Riesgo ALTO']} días con riesgo alto")
            if 'Riesgo MEDIO' in riesgo_counts:
                resumen.append(f"{riesgo_counts['Riesgo MEDIO']} días con riesgo medio")
            if 'Riesgo BAJO' in riesgo_counts:
                resumen.append(f"{riesgo_counts['Riesgo BAJO']} días con riesgo bajo")

            resumen_texto = ", ".join(resumen)
            st.markdown(f"### 🧾 Resumen del período analizado")
            st.success(f"En los últimos {total_dias} días: {resumen_texto}.")

            st.dataframe(df[['fecha', 'temperatura_media', 'precipitacion_mm', 'humedad_relativa',
                             'riesgo_mildiu', 'interpretacion']], use_container_width=True)

            df['riesgo_valor'] = df['riesgo_mildiu'].map({
                'Riesgo BAJO': 0,
                'Riesgo MEDIO': 1,
                'Riesgo ALTO': 2
            })
            st.line_chart(df.set_index('fecha')['riesgo_valor'])

            if len(df) >= 3:
                tendencia = df['riesgo_valor'].iloc[-1] - df['riesgo_valor'].iloc[0]
                if tendencia > 0:
                    st.info("🔺 Riesgo en aumento en los últimos días.")
                elif tendencia < 0:
                    st.info("🔻 Riesgo en descenso en los últimos días.")
                else:
                    st.info("⏸️ Riesgo estable.")

            if brotes:
                st.markdown("### 🧠 Detección de brote potencial")
                for inicio, fin in brotes:
                    st.error(f"🚨 Potencial brote entre {inicio.strftime('%d/%m')} y {fin.strftime('%d/%m')}")
            else:
                st.info("✅ No se detectaron acumulaciones de riesgo crítico que sugieran un brote.")

            dias_tratamiento = []
            ultimo_tratamiento = None
            for i, row in df.iterrows():
                fecha_actual = pd.to_datetime(row['fecha'])
                if row['riesgo_mildiu'] == 'Riesgo ALTO':
                    if (ultimo_tratamiento is None or (fecha_actual - ultimo_tratamiento).days >= 10):
                        dias_tratamiento.append((fecha_actual, 'Alta presión de infección'))
                        ultimo_tratamiento = fecha_actual
                elif row['precipitacion_mm'] >= 20:
                    if ultimo_tratamiento and (fecha_actual - ultimo_tratamiento).days >= 1:
                        dias_tratamiento.append((fecha_actual, 'Lluvia intensa tras tratamiento'))
                        ultimo_tratamiento = fecha_actual

            if dias_tratamiento:
                st.markdown("### 💉 Recomendación de tratamiento fitosanitario")
                for fecha, motivo in dias_tratamiento:
                    st.warning(f"Se recomienda aplicar caldo bordelés el {fecha.strftime('%d/%m')} ({motivo})")

            st.download_button(
                label="📥 Descargar resultados en CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='riesgo_mildiu.csv',
                mime='text/csv'
            )
else:
    st.info("Introduce una ubicación válida y pulsa el botón para continuar.")
