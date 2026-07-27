import streamlit as st
from supabase import create_client, Client
from streamlit_calendar import calendar

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
    fecha_seleccionada = cal["dateClick"]["date"]
    st.success(f"Iniciando solicitud para: {fecha_seleccionada}")
    
    # Aquí irá el formulario para el itinerario
    with st.form("form_cita"):
        st.text_area("Itinerario de la cita:", key="itinerario")
        st.form_submit_button("Enviar Solicitud")
