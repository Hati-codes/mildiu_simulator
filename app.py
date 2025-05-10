
import streamlit as st

# 🔁 Reinicio seguro si el usuario ha marcado un tratamiento
if "forzar_rerun" in st.session_state and st.session_state["forzar_rerun"]:
    st.session_state["forzar_rerun"] = False
    st.experimental_rerun()

import pandas as pd

# 🔁 Reinicio seguro tras botón de tratamiento
if st.session_state.get("forzar_rerun", False):
    st.session_state["forzar_rerun"] = False
    st.experimental_rerun()

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

    with st.container():

        dias = st.slider("📆 Días atrás a considerar", 1, 14, 7)
        prediccion = st.checkbox("📈 Incluir predicción para los próximos 3 días")

    st.markdown("## 🔬 Análisis meteorológico y riesgo de mildiu")
    
if not st.session_state.get("analisis_realizado", False):
    if st.button("🔍 Analizar riesgo"):
        st.session_state.analisis_realizado = True
        st.experimental_rerun()
if st.session_state.get("analisis_realizado", False):

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

            # 🟢 Marcar fechas tratadas en el DataFrame
            
            if "tratamientos_confirmados" not in st.session_state:
                st.session_state.tratamientos_confirmados = []

            df['tratamiento_aplicado'] = df['fecha'].apply(lambda x: '✅' if pd.to_datetime(x).strftime('%Y-%m-%d') in st.session_state.tratamientos_confirmados else '')

            # 📊 Resultados del análisis
            st.markdown("### 📊 Resultados del análisis")
            # ✅ Aseguramos que existan las columnas necesarias antes de mostrar la tabla
            if 'tratamiento_aplicado' not in df.columns:
                df['tratamiento_aplicado'] = ''
            if 'tratamiento_sugerido' not in df.columns:
                df['tratamiento_sugerido'] = ''
            st.dataframe(df[['fecha', 'temperatura_media', 'precipitacion_mm', 'humedad_relativa',
                             'riesgo_mildiu', 'interpretacion', 'tratamiento_aplicado', 'tratamiento_sugerido']], use_container_width=True)

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

            # 📈 Gráfico multivariable
            import plotly.express as px
            df_plot = df[['fecha', 'temperatura_media', 'precipitacion_mm', 'humedad_relativa']].copy()
            df_plot = df_plot.rename(columns={
                'temperatura_media': 'Temperatura media (°C)',
                'precipitacion_mm': 'Precipitación (mm)',
                'humedad_relativa': 'Humedad relativa (%)'
            })

            fig = px.line(df_plot, x='fecha', y=df_plot.columns[1:],
                          labels={'value': 'Valor', 'variable': 'Variable', 'fecha': 'Fecha'},
                          markers=True)
            fig.update_layout(height=400, legend_title_text='Variable')
            st.plotly_chart(fig, use_container_width=True)

            # 🚨 Brote unificado
            brotes_detectados = []

            # Lógica 1: riesgo alto continuado
            fechas_alto = pd.to_datetime(df[df['riesgo_mildiu'] == "Riesgo ALTO"]['fecha']).sort_values().reset_index(drop=True)
            grupo = []
            for i in range(len(fechas_alto)):
                if not grupo:
                    grupo.append(fechas_alto[i])
                elif (fechas_alto[i] - grupo[-1]).days <= 1:
                    grupo.append(fechas_alto[i])
                else:
                    if len(grupo) >= 3:
                        brotes_detectados.append((grupo[0], grupo[-1], "Riesgo ALTO continuado"))
                    grupo = [fechas_alto[i]]
            if len(grupo) >= 3:
                brotes_detectados.append((grupo[0], grupo[-1], "Riesgo ALTO continuado"))

            # Lógica 2: doble lluvia fuerte en una semana
            for i in range(len(df) - 6):
                semana = df.iloc[i:i+7]
                lluvias_fuertes = semana[semana['precipitacion_mm'] >= 10]
                if len(lluvias_fuertes) >= 2:
                    inicio = pd.to_datetime(semana.iloc[0]['fecha']).to_pydatetime()
                    fin = pd.to_datetime(semana.iloc[-1]['fecha']).to_pydatetime()
                    brotes_detectados.append((inicio, fin, "Doble lluvia intensa"))

            if brotes_detectados:
                st.markdown("### 🚨 Brotes detectados")
                for inicio, fin, causa in brotes_detectados:
                    st.error(f"Brote entre {inicio.strftime('%d/%m')} y {fin.strftime('%d/%m')} ({causa})")
            else:
                st.info("✅ No se detectaron acumulaciones de riesgo crítico que sugieran un brote.")


            df['fecha'] = pd.to_datetime(df['fecha'])
            fechas_alto = pd.to_datetime(df[df['riesgo_mildiu'] == "Riesgo ALTO"]['fecha']).sort_values().reset_index(drop=True)

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
            # ✅ Aseguramos que existan las columnas necesarias antes de mostrar la tabla
            if 'tratamiento_aplicado' not in df.columns:
                df['tratamiento_aplicado'] = ''
            if 'tratamiento_sugerido' not in df.columns:
                df['tratamiento_sugerido'] = ''
            st.dataframe(df[['fecha', 'temperatura_media', 'precipitacion_mm', 'humedad_relativa',
                             'riesgo_mildiu', 'interpretacion', 'tratamiento_aplicado', 'tratamiento_sugerido']], use_container_width=True)

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

            
            
            # 💉 Recomendación de tratamiento fitosanitario (preventivo)
            if "tratamientos_confirmados" not in st.session_state:
                st.session_state.tratamientos_confirmados = []

            dias_tratamiento = []
            ultimo_tratamiento = None
            for i in range(1, len(df)):
                dia_anterior = pd.to_datetime(df.loc[i - 1, 'fecha'])
                dia_actual = pd.to_datetime(df.loc[i, 'fecha'])
                riesgo = df.loc[i, 'riesgo_mildiu']
                lluvia = df.loc[i, 'precipitacion_mm']

                if riesgo == 'Riesgo ALTO' or lluvia >= 10:
                    if (ultimo_tratamiento is None) or ((dia_anterior - ultimo_tratamiento).days >= 10):
                        dias_tratamiento.append((dia_anterior, 'Prevención antes de brote o lluvia intensa'))
                        ultimo_tratamiento = dia_anterior

            # 🟢 Marcar en tabla los tratamientos sugeridos
            if dias_tratamiento:
                sugeridas = set([f[0].strftime('%Y-%m-%d') for f in dias_tratamiento])
            else:
                sugeridas = set()
            df['tratamiento_sugerido'] = df['fecha'].apply(
                lambda x: '💧' if pd.to_datetime(x).strftime('%Y-%m-%d') in sugeridas else ''
            )

            if dias_tratamiento:
                st.markdown("### 💉 Recomendación de tratamiento fitosanitario")
                for fecha, motivo in dias_tratamiento:
                    fecha_str = fecha.strftime('%Y-%m-%d')
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.warning(f"Aplicar caldo bordelés el {fecha.strftime('%d/%m')} ({motivo})")
                    with col2:
                        if st.button(f"✅ Tratado {fecha_str}"):
                            if fecha_str not in st.session_state.tratamientos_confirmados:
                                st.session_state.tratamientos_confirmados.append(fecha_str)
                                st.session_state["forzar_rerun"] = True

            if "tratamientos_confirmados" not in st.session_state:
                st.session_state.tratamientos_confirmados = []

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
                    fecha_str = fecha.strftime('%Y-%m-%d')
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.warning(f"Aplicar caldo bordelés el {fecha.strftime('%d/%m')} ({motivo})")
                    with col2:
                        if st.button(f"✅ Tratado {fecha_str}"):
                            if fecha_str not in st.session_state.tratamientos_confirmados:
                                st.session_state.tratamientos_confirmados.append(fecha_str)
                                st.experimental_rerun()

            # 🔁 Ajustar riesgo tras tratamiento
            if st.session_state.tratamientos_confirmados:
                for fecha_tratada_str in st.session_state.tratamientos_confirmados:
                    fecha_tratada = pd.to_datetime(fecha_tratada_str)
                    df.loc[(df['fecha'] > fecha_tratada) & (df['fecha'] <= fecha_tratada + pd.Timedelta(days=7)), 'riesgo_mildiu'] = df['riesgo_mildiu'].replace({
                        "Riesgo ALTO": "Riesgo MEDIO",
                        "Riesgo MEDIO": "Riesgo BAJO"
                    })
                    df['interpretacion'] = df.apply(interpretar_riesgo, axis=1)

            # 🟢 Marcar fechas tratadas en el DataFrame
            
            if "tratamientos_confirmados" not in st.session_state:
                st.session_state.tratamientos_confirmados = []

            df['tratamiento_aplicado'] = df['fecha'].apply(lambda x: '✅' if pd.to_datetime(x).strftime('%Y-%m-%d') in st.session_state.tratamientos_confirmados else '')



            st.download_button(
                label="📥 Descargar resultados en CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='riesgo_mildiu.csv',
                mime='text/csv'
            )
else:
    st.info("Introduce una ubicación válida y pulsa el botón para continuar.")