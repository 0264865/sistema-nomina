import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
from io import BytesIO
import re


st.set_page_config(page_title="Nómina Maquiladora", layout="wide")

# ---------- Funciones de ayuda ----------

def cargar_csv(ruta, columnas):
    if os.path.exists(ruta):
        return pd.read_csv(ruta)
    else:
        return pd.DataFrame(columns=columnas)

def guardar_csv(df, ruta):
    df.to_csv(ruta, index=False)

# ---------- Cargar datos ----------
empleados = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])
registros = cargar_csv("registros_horas.csv", ["id_trabajador", "fecha", "horas_trabajadas"])

st.title("🧵 Sistema de Nómina - Maquiladora Textil")

tabs = st.tabs(["👤 Empleados", "⏱ Registro de horas", "💰 Nómina", "📥 Importar ZKTeco"])

# ---------- TAB 1: EMPLEADOS ----------
with tabs[0]:
    st.header("Catálogo de empleados")

    st.subheader("Dar de alta empleado")

    with st.form("form_empleado"):
        id_trabajador = st.number_input("ID trabajador", min_value=1, step=1)
        nombre = st.text_input("Nombre completo")
        sueldo_hora = st.number_input("Sueldo por hora (MXN)", min_value=0.0, step=1.0)

        enviado = st.form_submit_button("Guardar empleado")

        if enviado:
            if nombre.strip() == "":
                st.error("El nombre no puede ir vacío.")
            else:
                # Verificar si ya existe
                existe = empleados[empleados["id_trabajador"] == id_trabajador]
                if not existe.empty:
                    st.error("Ya existe un trabajador con ese ID.")
                else:
                    nuevo = pd.DataFrame([{
                        "id_trabajador": int(id_trabajador),
                        "nombre": nombre.strip(),
                        "sueldo_hora": float(sueldo_hora)
                    }])
                    empleados = pd.concat([empleados, nuevo], ignore_index=True)
                    guardar_csv(empleados, "empleados.csv")
                    st.success("Empleado guardado correctamente ✅")

    st.subheader("Listado de empleados")
    st.dataframe(empleados)

# ---------- TAB 2: REGISTRO DE HORAS ----------
with tabs[1]:
    st.header("Registro de horas trabajadas")

    if empleados.empty:
        st.warning("Primero da de alta empleados en la pestaña 'Empleados'.")
    else:
        empleados["label"] = empleados["id_trabajador"].astype(str) + " - " + empleados["nombre"]
        seleccionado = st.selectbox("Selecciona empleado", empleados["label"])

        id_sel = int(seleccionado.split(" - ")[0])

        fecha_reg = st.date_input("Fecha", value=date.today())
        horas_trab = st.number_input("Horas trabajadas", min_value=0.0, step=0.5)

        if st.button("Guardar registro de horas"):
            nuevo_reg = pd.DataFrame([{
                "id_trabajador": id_sel,
                "fecha": fecha_reg.isoformat(),
                "horas_trabajadas": float(horas_trab)
            }])
            registros = pd.concat([registros, nuevo_reg], ignore_index=True)
            guardar_csv(registros, "registros_horas.csv")
            st.success("Registro de horas guardado ✅")

        st.subheader("Registros recientes")
        st.dataframe(registros.tail(20))

# ---------- TAB 3: NÓMINA ----------
with tabs[2]:
    st.header("💰 Nómina por periodo")

    # Cargar datos siempre que existan
    empleados = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])
    registros = cargar_csv("registros_horas.csv", ["id_trabajador", "fecha", "horas_trabajadas"])

    if empleados.empty:
        st.warning("Primero da de alta empleados en la pestaña 👤 Empleados.")
    elif registros.empty:
        st.warning("Aún no hay registros de horas. Importa un archivo del reloj en 📥 Importar ZKTeco.")
    else:
        # Convertir fecha
        registros["fecha"] = pd.to_datetime(registros["fecha"], errors="coerce")
        registros = registros[registros["fecha"].notna()]

        # Rango de fechas para el periodo de nómina
        fecha_min = registros["fecha"].min().date()
        fecha_max = registros["fecha"].max().date()

        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input(
                "Fecha inicial del periodo",
                value=fecha_min,
                min_value=fecha_min,
                max_value=fecha_max
            )
        with col2:
            fecha_fin = st.date_input(
                "Fecha final del periodo",
                value=fecha_max,
                min_value=fecha_min,
                max_value=fecha_max
            )

        if fecha_inicio > fecha_fin:
            st.error("La fecha inicial no puede ser mayor que la fecha final.")
        else:
            # Filtrar registros del periodo
            mask = (registros["fecha"].dt.date >= fecha_inicio) & \
                   (registros["fecha"].dt.date <= fecha_fin)
            regs_periodo = registros[mask]

            if regs_periodo.empty:
                st.warning("No hay registros de horas en ese rango de fechas.")
            else:
                # Agrupar horas por trabajador
                horas_por_trabajador = (
                    regs_periodo
                    .groupby("id_trabajador")["horas_trabajadas"]
                    .sum()
                    .reset_index()
                )

                # Unir con catálogo de empleados (para nombre y sueldo)
                nomina = horas_por_trabajador.merge(
                    empleados,
                    on="id_trabajador",
                    how="left"
                )

                # Calcular pago
                nomina["horas_trabajadas"] = nomina["horas_trabajadas"].round(2)
                nomina["sueldo_hora"] = nomina["sueldo_hora"].round(2)
                nomina["pago"] = (nomina["horas_trabajadas"] * nomina["sueldo_hora"]).round(2)

                # Ordenar columnas bonitas
                nomina = nomina[[
                    "id_trabajador",
                    "nombre",
                    "horas_trabajadas",
                    "sueldo_hora",
                    "pago"
                ]].sort_values("id_trabajador")

                # Mostrar tabla resumen (esta es la que le enseñas al jefe)
                st.subheader("Resumen de nómina por trabajador")
                st.dataframe(nomina, hide_index=True)

                # Total de la nómina
                total_nomina = nomina["pago"].sum().round(2)
                st.markdown(
                    f"### 🧾 Total de la nómina del {fecha_inicio} al {fecha_fin}: **${total_nomina:,.2f} MXN**"
                )

                # Detalle opcional por día, por si algún día lo ocupas
                with st.expander("Ver detalle por día (opcional)"):
                    detalle = regs_periodo.merge(
                        empleados[["id_trabajador", "nombre"]],
                        on="id_trabajador",
                        how="left"
                    )
                    detalle["fecha"] = detalle["fecha"].dt.date
                    detalle["horas_trabajadas"] = detalle["horas_trabajadas"].round(2)
                    st.dataframe(
                        detalle[["id_trabajador", "nombre", "fecha", "horas_trabajadas"]],
                        hide_index=True
                    )

                # Botón para descargar el reporte en Excel
                from io import BytesIO
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    nomina.to_excel(writer, index=False, sheet_name="Nomina_resumen")
                    detalle.to_excel(writer, index=False, sheet_name="Detalle_por_dia")
                buffer.seek(0)

                st.download_button(
                    label="💾 Descargar reporte de nómina en Excel",
                    data=buffer,
                    file_name=f"nomina_{fecha_inicio}_a_{fecha_fin}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
# ---------- TAB 4: IMPORTAR DESDE ZKTECO (REPORTE DE ASISTENCIA) ----------
with tabs[3]:
    st.header("Importar desde ZKTeco (Reporte de Asistencia)")

    st.write(
        "Sube el archivo **1_report.xls** (o similar) que te da el reloj, "
        "sin modificarlo. La app va a leer la hoja **'Reporte de Asistencia'**, "
        "calcular horas, detectar faltas de marcas y generar el resumen de pago."
    )

    uploaded_file = st.file_uploader(
        "Archivo de reporte (.xls, .xlsx o .csv)",
        type=["xls", "xlsx", "csv"]
    )

    if uploaded_file is not None:
        try:
            # ---------- LEER ARCHIVO COMPLETO ----------
            nombre_archivo = uploaded_file.name.lower()

            if nombre_archivo.endswith(".csv"):
                df_raw = pd.read_csv(uploaded_file, header=None)
            else:
                # Forzamos hoja "Reporte de Asistencia"
                xls = pd.ExcelFile(uploaded_file)
                if "Reporte de Asistencia" not in xls.sheet_names:
                    st.error(
                        "No encontré la hoja **'Reporte de Asistencia'** en el archivo. "
                        "Revisa que sea el reporte correcto."
                    )
                    st.stop()
                df_raw = pd.read_excel(
                    xls, sheet_name="Reporte de Asistencia", header=None
                )

            st.subheader("Vista previa del archivo original")
            st.dataframe(df_raw.head(30))

            # ---------- ENCONTRAR FILA DE DÍAS (14,15,16...) ----------
            fila_dias = None
            for i, row in df_raw.iterrows():
                vals = [v for v in row if isinstance(v, (int, float)) and not pd.isna(v)]
                if vals and all(1 <= int(v) <= 31 for v in vals):
                    fila_dias = i
                    break

            if fila_dias is None:
                st.error("No encontré la fila con los días (14,15,16,...). Revisa el formato.")
                st.stop()

            # Columnas que sí tienen día (15,16,17,...)
            columnas_dias = [
                c for c, v in df_raw.loc[fila_dias].items()
                if isinstance(v, (int, float)) and not pd.isna(v)
            ]
            dias_numeros = {
                c: int(df_raw.loc[fila_dias, c])
                for c in columnas_dias
            }

            # ---------- FECHA BASE (año y mes) ----------
            # Buscamos algo tipo "2025-11-14 ~ 2025-11-21"
            texto_periodo = ""
            for v in df_raw.iloc[fila_dias - 1]:
                if isinstance(v, str) and "Periodo" in v:
                    texto_periodo = v
                    break

            m = re.search(r"(\d{4}-\d{2}-\d{2})", texto_periodo)
            if m:
                fecha_inicio = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            else:
                # fallback: usamos año y mes actuales
                hoy = date.today()
                fecha_inicio = date(hoy.year, hoy.month, 1)

            # ---------- FUNCIONES AUXILIARES ----------

            def parse_marcas(cadena):
                """
                Recibe algo como '08:21 13:15 15:19 19:39'
                y regresa (entrada1, salida1, entrada2, salida2, observacion, minutos_trabajados)
                aplicando las reglas que quedamos.
                """
                if not isinstance(cadena, str):
                    return None, None, None, None, "SIN REGISTRO", 0

                marcas = re.findall(r"\d{2}:\d{2}", cadena)
                if len(marcas) == 0:
                    return None, None, None, None, "SIN REGISTRO", 0

                # Convertir a datetime.time
                def to_time(hhmm):
                    return datetime.strptime(hhmm, "%H:%M").time()

                obs = "OK"
                minutos = 0

                if len(marcas) >= 4:
                    e1, s1, e2, s2 = [to_time(m) for m in marcas[:4]]
                    # Bloque 1
                    minutos += (datetime.combine(date.min, s1) -
                                datetime.combine(date.min, e1)).seconds // 60
                    # Bloque 2
                    minutos += (datetime.combine(date.min, s2) -
                                datetime.combine(date.min, e2)).seconds // 60
                    obs = "COMPLETO"

                    return marcas[0], marcas[1], marcas[2], marcas[3], obs, minutos

                elif len(marcas) == 3:
                    # Falta una marca: NO calculamos nada del segundo horario
                    e1, s1 = [to_time(m) for m in marcas[:2]]
                    minutos += (datetime.combine(date.min, s1) -
                                datetime.combine(date.min, e1)).seconds // 60
                    obs = "❗ FALTA MARCA (2do horario pendiente)"

                    return marcas[0], marcas[1], marcas[2], None, obs, minutos

                elif len(marcas) == 2:
                    e1, s1 = [to_time(m) for m in marcas]
                    minutos += (datetime.combine(date.min, s1) -
                                datetime.combine(date.min, e1)).seconds // 60
                    obs = "SOLO 1 BLOQUE"

                    return marcas[0], marcas[1], None, None, obs, minutos

                else:  # solo 1 marca
                    obs = "❗ SOLO 1 MARCA (revisar)"
                    return marcas[0], None, None, None, obs, 0

            # ---------- RECORRER TODOS LOS TRABAJADORES ----------
            filas_id = df_raw.index[df_raw[0] == "ID:"].tolist()
            if not filas_id:
                st.error("No encontré filas con el encabezado 'ID:'. Revisa que sea la hoja correcta.")
                st.stop()

            registros_detalle = []  # detalle por día

            for fila in filas_id:
                # fila = donde está 'ID:'
                id_val = df_raw.loc[fila, 2]
                nombre = df_raw.loc[fila, 10]

                # fila siguiente trae las marcas de tiempo
                fila_marcas = fila + 1

                for c in columnas_dias:
                    dia = dias_numeros[c]
                    valor_celda = df_raw.loc[fila_marcas, c]

                    if pd.isna(valor_celda):
                        # No hay marcas para ese día
                        continue

                    entrada1, salida1, entrada2, salida2, obs, min_trab = parse_marcas(str(valor_celda))

                    # Construimos la fecha real (asumimos mismo mes que fecha_inicio)
                    try:
                        fecha_dia = date(fecha_inicio.year, fecha_inicio.month, dia)
                    except ValueError:
                        # Por si el periodo cruza de mes, aquí podríamos mejorar;
                        # de momento dejamos solo el número de día.
                        fecha_dia = dia

                    registros_detalle.append({
                        "id_trabajador": int(id_val) if pd.notna(id_val) else None,
                        "nombre": nombre,
                        "fecha": fecha_dia,
                        "entrada1": entrada1,
                        "salida1": salida1,
                        "entrada2": entrada2,
                        "salida2": salida2,
                        "min_trabajados": min_trab,
                        "observaciones": obs,
                    })

            if not registros_detalle:
                st.warning("No se generaron registros. Revisa el archivo.")
                st.stop()

            detalle_df = pd.DataFrame(registros_detalle)

            # ---------- CÁLCULO DE HORAS / PAGO POR TRABAJADOR ----------
            # Cargamos sueldos desde empleados.csv
            empleados = cargar_csv("empleados.csv", ["id_trabajador", "nombre", "sueldo_hora"])

            # Total de minutos trabajados por ID en el periodo
            resumen = (
                detalle_df
                .groupby(["id_trabajador", "nombre"], as_index=False)
                .agg(
                    min_trabajados_total=("min_trabajados", "sum"),
                    dias_registrados=("fecha", "nunique"),
                    faltas_marca=("observaciones", lambda s: (s.str.contains("FALTA MARCA|SOLO 1 MARCA", na=False)).sum())
                )
            )

            resumen["horas_trabajadas"] = resumen["min_trabajados_total"] / 60.0

            # Unir sueldo_hora
            resumen = resumen.merge(
                empleados[["id_trabajador", "sueldo_hora"]],
                on="id_trabajador",
                how="left"
            )

            resumen["sueldo_hora"] = resumen["sueldo_hora"].fillna(0)
            resumen["pago_periodo"] = resumen["horas_trabajadas"] * resumen["sueldo_hora"]

            total_nomina = resumen["pago_periodo"].sum()

            # ---------- MOSTRAR EN LA APP ----------
            st.subheader("Detalle por día (para revisar marcas)")
            st.dataframe(detalle_df)

            st.subheader("Resumen por trabajador (horas y pago del periodo)")
            st.dataframe(resumen)

            st.success("Registros importados, calculados y listos ✅")

            st.markdown(
                f"**Total de nómina del periodo: "
                f"${total_nomina:,.2f} MXN**"
            )

            # ---------- DESCARGA EN EXCEL PARA TU JEFE ----------
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                detalle_df.to_excel(writer, sheet_name="Detalle_por_dia", index=False)
                resumen.to_excel(writer, sheet_name="Resumen_nomina", index=False)

            buffer.seek(0)

            st.download_button(
                label="📥 Descargar reporte completo en Excel",
                data=buffer,
                file_name="reporte_nomina_periodo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo: {e}")





