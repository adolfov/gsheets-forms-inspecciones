""" CREACIÓN DE FORMULARIO WEB CON STREAMLIT """

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
import time

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_worksheet_data(_conn, worksheet_name):
    """Simple cached function to get worksheet data"""
    return _conn.read(worksheet=worksheet_name)

def clean_dataframe_for_display(df):
    """Safely clean dataframe for display by handling data type issues"""
    df_clean = df.copy()
    
    # Convert problematic columns to string to avoid display issues
    if 'numero_economico' in df_clean.columns:
        df_clean['numero_economico'] = df_clean['numero_economico'].astype(str)
    
    # Handle any other potential type issues
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            # Convert mixed types to string
            df_clean[col] = df_clean[col].astype(str)
            # Replace "nan" strings and empty strings with None for cleaner display
            df_clean[col] = df_clean[col].replace(['nan', ''], None)
    
    return df_clean



def safe_gsheets_update(conn, worksheet_name, new_data, existing_data=None):
    """
    Safely update Google Sheets worksheet with data validation and backup
    
    Args:
        conn: GSheetsConnection object
        worksheet_name: Name of the worksheet to update
        new_data: New data to append
        existing_data: Existing data (if None, will be read from worksheet)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read existing data if not provided
        if existing_data is None:
            existing_data = conn.read(worksheet=worksheet_name, ttl=0)
        
        # Validate existing data
        if existing_data is None or existing_data.empty:
            st.error(f"❌ No se pudieron leer los datos existentes de {worksheet_name}")
            return False
        
        if not isinstance(existing_data, pd.DataFrame):
            st.error(f"❌ Los datos existentes de {worksheet_name} no tienen el formato esperado")
            return False
        
        # Create backup
        backup_data = existing_data.copy()
        
        # Ensure data type consistency
        for col in new_data.columns:
            if col in existing_data.columns:
                if existing_data[col].dtype != new_data[col].dtype:
                    try:
                        new_data[col] = new_data[col].astype(existing_data[col].dtype)
                    except:
                        existing_data[col] = existing_data[col].astype(str)
                        new_data[col] = new_data[col].astype(str)
        
        # Concatenate data
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        
        # Final validation
        if len(updated_data) < len(existing_data):
            st.error(f"❌ La operación resultaría en pérdida de datos en {worksheet_name}")
            return False
        
        # Update worksheet
        conn.update(worksheet=worksheet_name, data=updated_data)
        return True
        
    except Exception as e:
        st.error(f"❌ Error en safe_gsheets_update: {str(e)}")
        return False

# Conexión a la Base de datos en Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Consulta de la información en la Base de datos con cache simple
    inspecciones = get_worksheet_data(conn, "inspecciones")
    vehiculos = get_worksheet_data(conn, "vehiculos")
    rutas = get_worksheet_data(conn, "rutas")
    rutas["numero_ruta"] = rutas["numero_ruta"].astype(int)
    partes = get_worksheet_data(conn, "partes")
    partes_unicas = partes["parte"].unique()
    
    # Título de la página web
    st.title("Inspecciones de vehículos de transporte público Va-y-Ven")
    st.success("🌐 Conectado a Google Sheets")
    
    # Simple refresh button
    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()
    
except Exception as e:
    st.error(f"❌ Error conectando a Google Sheets: {str(e)}")
    st.info("💡 Verifica la configuración en Streamlit Secrets")
    st.stop()

# Pestañas de la página web
tab_1, tab_2, tab_3, tab_4 = st.tabs(["Formulario de inspecciones", "Consulta de Inspecciones",
                               "Vehículos", "Estado de los Datos"])

# Pestaña 1: Formulario de inspecciones

with tab_1:

    # Datos de Inspección
    st.subheader("Datos de la Inspección")
    col_1, col_2 = st.columns(2)
    folio_inspeccion = col_1.text_input("Folio de inspección", key="folio_inspeccion")
    modalidad_inspeccion = col_2.selectbox("Molidad de inspección",
                                           options=("ALEATORIA", "DIRIGIDA"),
                                           key="modalidad_inspeccion")
    fecha_inspeccion = col_1.date_input("Fecha de inspección", format="YYYY-MM-DD",
                                        key="fecha_inspeccion")
    hora_inspeccion = col_2.time_input("Hora de inspección", value=None, step=60,
                                       key="hora_inspeccion")
    inspector = st.text_input("Nombre del inspector", key="inspector")
    st.divider()

    # Creación de Listas de selección con sincronización automática
    if "numero_ruta" not in st.session_state:
        st.session_state.numero_ruta = rutas["numero_ruta"].iloc[0]
    if "nombre_ruta" not in st.session_state:
        st.session_state.nombre_ruta = rutas["ruta"].iloc[0]
    if "numero_economico" not in st.session_state:
        st.session_state.numero_economico = vehiculos["numero_economico"].iloc[0]
    if "placa" not in st.session_state:
        st.session_state.placa = vehiculos["placa"].iloc[0]
    if "empresa" not in st.session_state:
        st.session_state.empresa = vehiculos["empresa"].iloc[0]

    def on_ruta_change():
        nuevo_numero = rutas[rutas["ruta"] == st.session_state.nombre_ruta][
            "numero_ruta"].values[0]
        st.session_state.numero_ruta = nuevo_numero

    def on_numero_ruta_change():
        nuevo_nombre = rutas[rutas["numero_ruta"] == st.session_state.numero_ruta][
            "ruta"].values[0]
        st.session_state.nombre_ruta = nuevo_nombre

    def on_numero_economico_change():
        fila = vehiculos[vehiculos["numero_economico"] == st.session_state.numero_economico].iloc[0]
        st.session_state.placa = fila["placa"]
        st.session_state.empresa = fila["empresa"]

    def on_placa_change():
        fila = vehiculos[vehiculos["placa"] == st.session_state.placa].iloc[0]
        st.session_state.numero_economico = fila["numero_economico"]
        st.session_state.empresa = fila["empresa"]

    def on_empresa_change():
        fila = vehiculos[vehiculos["empresa"] == st.session_state.empresa].iloc[0]
        st.session_state.numero_economico = fila["numero_economico"]
        st.session_state.placa = fila["placa"]

    # Datos de la Ruta & Unidad
    st.subheader("Datos de la Unidad Va-y-Ven")
    col_1, col_2 = st.columns([1, 3])
    numero_ruta = col_1.selectbox("Número de ruta", rutas["numero_ruta"], key="numero_ruta",
                                  on_change=on_numero_ruta_change)
    ruta = col_2.selectbox("Ruta", rutas["ruta"], key="nombre_ruta", on_change=on_ruta_change)

    col_1, col_2, col_3 = st.columns([1, 1, 2])
    numero_economico = col_1.selectbox("Número económico", vehiculos["numero_economico"],
                                       key="numero_economico",
                                       on_change=on_numero_economico_change)
    placa = col_2.selectbox("Placa", vehiculos["placa"], key="placa", on_change=on_placa_change)
    empresa = col_3.selectbox("Empresa", vehiculos["empresa"].unique(), key="empresa",
                              on_change=on_empresa_change)
    st.divider()

    # Datos de Eventos de las Partes dañadas (descripción del evento)
    st.subheader("Datos de las Partes dañadas")
    partes_danadas = st.multiselect('Selecciona las partes dañadas', partes_unicas,
                                    key="partes_danadas")

    eventos_parte = {}

    for parte in partes_danadas:
        st.divider()
        col_1, col_2 = st.columns([1, 3])
        ubicaciones_parte = partes.loc[partes["parte"] == parte, "ubicacion_parte"].unique()
        key_ubicaciones = f"ubicaciones_{parte}"
        ubicaciones_seleccionadas = col_1.multiselect(f"Ubicación de {parte}", ubicaciones_parte,
                                                      key=key_ubicaciones)

        for ubicacion in ubicaciones_seleccionadas:
            key_observacion = f"observacion_{parte}_{ubicacion}"
            observacion = col_2.text_area(f"Observación para {parte} en {ubicacion}",
                                          key=key_observacion)
            eventos_parte[(parte, ubicacion)] = observacion

    inspeccion = []

    for parte in partes_unicas:

        if parte in partes_danadas:
            for (parte_danada, ubicacion), observacion in eventos_parte.items():
                ubicaciones_parte = ubicacion
                estado = "MAL ESTADO"
                if parte_danada == parte:
                    parte_inspeccionada = {
                        "folio_inspeccion": folio_inspeccion,
                        "modalidad_inspeccion": modalidad_inspeccion,
                        "fecha_inspeccion": fecha_inspeccion,
                        "hora_inspeccion": hora_inspeccion,
                        "inspector": inspector,
                        "numero_ruta": numero_ruta,
                        "ruta": ruta,
                        "numero_economico": numero_economico,
                        "placa": placa,
                        "empresa": empresa,
                        "parte": parte,
                        "ubicacion_parte": ubicacion,
                        "estado_parte": estado,
                        "descripcion_evento": observacion,
                        "fuente_evento" : "INSPECCIÓN"
                    }
                    inspeccion.append(parte_inspeccionada)

        else:
            estado = "BUEN ESTADO"
            ubicaciones_parte = partes.loc[partes["parte"] == parte, "ubicacion_parte"].unique()
            ubicaciones_validas = [str(ubicacion) for ubicacion in ubicaciones_parte if
                                   pd.notnull(ubicacion)]
            if ubicaciones_validas:
                ubicacion_parte = min(ubicaciones_validas, key=len)
            else:
                ubicacion_parte = np.nan

            parte_inspeccionada = {
                "folio_inspeccion" : folio_inspeccion,
                "modalidad_inspeccion" : modalidad_inspeccion,
                "fecha_inspeccion" : fecha_inspeccion,
                "hora_inspeccion" : hora_inspeccion,
                "inspector" : inspector,
                "numero_ruta" : numero_ruta,
                "ruta" : ruta,
                "numero_economico" : numero_economico,
                "placa" : placa,
                "empresa" : empresa,
                "parte" : parte,
                "ubicacion_parte" : ubicacion_parte,
                "estado_parte" : estado,
                "descripcion_evento" : "",
                "fuente_evento": "INSPECCIÓN"
            }
            inspeccion.append(parte_inspeccionada)

    df_inspeccion = pd.DataFrame(inspeccion)

    # Vista previa de la inspección
    # st.divider()
    # st.dataframe(inspeccion)

    # Guardar datos de la inspección
    st.divider()
    if st.button("Registrar datos de la inspección en Google Drive"):
        if not folio_inspeccion or not st.session_state.numero_economico:
            st.error("Por favor indica el número de folio y el número económico del vehículo.")
        else:
            inspecciones_sin_cache = conn.read(worksheet="inspecciones", ttl=0)
            inspecciones_actualizadas = pd.concat([inspecciones_sin_cache, df_inspeccion],
                                                  ignore_index=True)
            conn.update(worksheet="inspecciones", data=inspecciones_actualizadas)
            st.success("Inspección guardada exitosamente. ✅")
            # for key in ["folio_inspeccion", "modalidad_inspeccion", "fecha_inspeccion",
            #             "hora_inspeccion", "inspector", "numero_ruta", "nombre_ruta",
            #             "numero_economico", "placa", "empresa", "partes_danadas"]:
            #     if key in st.session_state:
            #         del st.session_state[key]
            #
            # for key in list(st.session_state.keys()):
            #     if key.startswith("observacion_") or key.startswith("ubicaciones_"):
            #         del st.session_state[key]
            #
            # st.rerun()

# Pestaña 2: Consulta de Inspecciones

with tab_2:

    st.subheader("Consulta de historial de partes dañadas")

    # Selección de vehículo
    empresas_disponibles = inspecciones["empresa"].unique()
    empresa = st.selectbox("Selecciona la empresa", empresas_disponibles)

    # Filtrar datos
    historial_danios = inspecciones[
        (inspecciones["empresa"] == empresa) &
        (inspecciones["estado_parte"] == "MAL ESTADO")
    ].sort_values(by="fecha_inspeccion", ascending=False, ignore_index=True)

    st.write(f"Historial de partes dañadas para la persona concesionaria {empresa}:")
    
    # Safe DataFrame display using helper function
    try:
        display_columns = ["fecha_inspeccion", "numero_economico", "parte", "ubicacion_parte",
                           "descripcion_evento", "fecha_oficio", "respuesta_empresa", "fecha_verificacion"]
        
        # Filter columns that exist in the DataFrame
        available_columns = [col for col in display_columns if col in historial_danios.columns]
        display_df = historial_danios[available_columns]
        
        # Clean DataFrame for safe display (this already fixes mixed types)
        clean_display_df = clean_dataframe_for_display(display_df)
        
        st.dataframe(clean_display_df, hide_index=True,
                     column_config={
                        "fecha_inspeccion" : "Fecha de inspección",
                        "numero_economico" : "Unidad",
                        "parte" : "Parte",
                        "ubicacion_parte" : "Ubicación",
                        "descripcion_evento" : "Observación",
                        "fecha_oficio" : "Fecha del oficio",
                        "respuesta_empresa" : "Respuesta del concesionario",
                        "fecha_verificacion" : "Fecha de verificación"
                     })
    except Exception as e:
        st.error(f"Error displaying data: {str(e)}")
        st.info("Try refreshing the page or check your data")

# Pestaña 3: Base de datos de inspecciones

with tab_3:

    st.subheader("Base de datos de vehículos Va-y-Ven")
    # Clean DataFrame for safe display
    vehiculos_clean = clean_dataframe_for_display(vehiculos)
    st.dataframe(vehiculos_clean)

# Pestaña 4: Estado de los Datos

with tab_4:
    
    st.subheader("📊 Estado Actual de los Datos")
    
    # Check current data status using cached data
    try:
        inspecciones_actuales = inspecciones
        vehiculos_actuales = vehiculos
        rutas_actuales = rutas
        
        st.metric("Inspecciones", len(inspecciones_actuales))
        st.metric("Vehículos", len(vehiculos_actuales))
        st.metric("Rutas", len(rutas_actuales))
        
        # Check for data integrity issues
        if inspecciones_actuales is None or inspecciones_actuales.empty:
            st.error("❌ No se pueden leer las inspecciones")
        else:
            st.success("✅ Datos de inspecciones accesibles")
            
    except Exception as e:
        st.error(f"❌ Error al verificar datos: {str(e)}")

    # Data validation and repair
    st.divider()
    st.subheader("🔍 Validación y Reparación de Datos")
    
    if st.button("🔍 Verificar Integridad de Datos"):
        try:
            issues_found = []
            
            # Check for missing data
            if inspecciones_actuales is None or inspecciones_actuales.empty:
                issues_found.append("❌ No hay datos de inspecciones")
            
            # Check for data type issues
            if inspecciones_actuales is not None and not inspecciones_actuales.empty:
                for col in inspecciones_actuales.columns:
                    if inspecciones_actuales[col].dtype == 'object':
                        # Check for mixed types
                        sample_values = inspecciones_actuales[col].dropna().head(10)
                        if len(sample_values) > 0:
                            types = [type(val).__name__ for val in sample_values]
                            if len(set(types)) > 1:
                                issues_found.append(f"⚠️ Columna '{col}' tiene tipos mixtos: {set(types)}")
            
            if issues_found:
                st.error("Problemas encontrados:")
                for issue in issues_found:
                    st.write(issue)
                
                # Offer to fix data type issues
                # if st.button("🔧 Reparar Tipos de Datos"):
                #     try:
                #         # Convert all columns to string to avoid type conflicts
                #         inspecciones_reparadas = inspecciones_actuales.astype(str)
                #         conn.update(worksheet="inspecciones", data=inspecciones_reparadas)
                #         st.success("✅ Tipos de datos reparados")
                #         st.rerun()
                #     except Exception as e:
                #         st.error(f"❌ Error al reparar: {str(e)}")
            else:
                st.success("✅ No se encontraron problemas de integridad")
                
        except Exception as e:
            st.error(f"❌ Error en validación: {str(e)}")
