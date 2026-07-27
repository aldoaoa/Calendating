import streamlit as st
from supabase import create_client, Client
from streamlit_calendar import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="Fercitas", page_icon="📅", layout="wide")

# 1. Conexión a Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

st.title("Fercitas 📅")
st.markdown("### Solicitar una cita")

# 2. Configuración del calendario moderno
calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "timeGridWeek,timeGridDay"
    },
    "initialView": "timeGridWeek",
    "slotMinTime": "18:00:00", # Bloquea visualmente las horas antes de las 6pm
    "slotMaxTime": "23:59:00",
    "selectable": True,
    "allDaySlot": False,
}

# Aquí cargaremos las citas de Supabase para mostrarlas bloqueadas
events = [] 

# 3. Renderizar el calendario interactivo
cal = calendar(events=events, options=calendar_options, key="calendario_fercitas")

# 4. Capturar la selección del usuario
if cal.get("dateClick"):
    fecha_iso = cal["dateClick"]["date"]
    
    # FullCalendar devuelve formato ISO con 'Z' al final (UTC)
    fecha_dt = datetime.fromisoformat(fecha_iso.replace('Z', '+00:00'))
    
    st.info(f"Iniciando solicitud para: {fecha_dt.strftime('%Y-%m-%d %H:%M')}")
    
    with st.form("form_cita"):
        st.text_area("Itinerario de la cita:", key="itinerario")
        submit = st.form_submit_button("Enviar Solicitud")

        if submit:
            # 1. Definir la ventana de bloqueo (Día anterior 00:00 hasta Día siguiente 23:59)
            fecha_inicio = (fecha_dt - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
            fecha_fin = (fecha_dt + timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()

            # ID temporal para pruebas (luego lo conectaremos al perfil real seleccionado)
            citado_id_actual = "ID_DEL_USUARIO_AL_QUE_SE_CITA" 

            # 2. Consultar a Supabase si hay citas aceptadas en esa ventana de 3 días
            respuesta = supabase.table("citas_fercitas").select("id") \
                .eq("citado_id", citado_id_actual) \
                .eq("estado", "aceptada") \
                .gte("fecha_hora", fecha_inicio) \
                .lte("fecha_hora", fecha_fin) \
                .execute()

            # 3. Validar e insertar
            if len(respuesta.data) > 0:
                st.error("❌ No es posible agendar. Esta persona ya tiene una cita confirmada para este día, el día anterior o el siguiente.")
            else:
                nueva_cita = {
                    "solicitante_id": "TU_ID_COMO_SOLICITANTE", 
                    "citado_id": citado_id_actual,
                    "fecha_hora": fecha_iso,
                    "itinerario": st.session_state.itinerario,
                    "estado": "pendiente"
                }
                supabase.table("citas_fercitas").insert(nueva_cita).execute()
                st.success("✅ Solicitud de cita enviada correctamente. Esperando confirmación.")
