import streamlit as st
from supabase import create_client, Client
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from ics import Calendar, Event

st.set_page_config(page_title="Fercitas", page_icon="📅", layout="wide")

# 1. Conexión a Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

tab1, tab2 = st.tabs(["Solicitar Cita", "Gestión de Citas (Citado)"])

with tab1:
    # AQUÍ VA TODO EL CÓDIGO DEL CALENDARIO Y ENVÍO QUE HICIMOS ANTES
    st.write("Vista del solicitante...")
    st.title("Fercitas 📅")
    st.markdown("### Solicitar una cita")
    
    def generar_ical(fecha_hora_str, itinerario):
        c = Calendar()
        e = Event()
        e.name = "Cita programada (Fercitas)"
        # La librería ics acepta el formato ISO directamente
        e.begin = fecha_hora_str 
        e.description = itinerario
        c.events.add(e)
        return c.serialize()
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

with tab2:
    st.markdown("### Solicitudes Entrantes")
    
    # ID temporal para pruebas (simulando que tú iniciaste sesión y ves lo que te enviaron)
    mi_id_como_citado = "ID_DEL_USUARIO_AL_QUE_SE_CITA"

    # Traer solicitudes pendientes de Supabase
    pendientes = supabase.table("citas_fercitas") \
        .select("*").eq("citado_id", mi_id_como_citado).eq("estado", "pendiente").execute()

    if not pendientes.data:
        st.info("No tienes solicitudes pendientes en este momento.")
    else:
        for cita in pendientes.data:
            # Usamos un expander o container para que se vea ordenado
            with st.container(border=True):
                # Formatear fecha para lectura
                fecha_dt = datetime.fromisoformat(cita['fecha_hora'].replace('Z', '+00:00'))
                st.subheader(f"📅 {fecha_dt.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**Itinerario:** {cita['itinerario']}")

                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("Aceptar Cita", key=f"aceptar_{cita['id']}"):
                        
                        # 1. RE-VALIDAR LA REGLA DE 2 DÍAS ANTES DE ACTUALIZAR
                        fecha_inicio = (fecha_dt - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
                        fecha_fin = (fecha_dt + timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()
                        
                        validacion = supabase.table("citas_fercitas").select("id") \
                            .eq("citado_id", mi_id_como_citado).eq("estado", "aceptada") \
                            .gte("fecha_hora", fecha_inicio).lte("fecha_hora", fecha_fin).execute()

                        if len(validacion.data) > 0:
                            st.error("No puedes aceptar esta cita. Ya confirmaste otra en este día, el anterior o el siguiente.")
                        else:
                            # 2. ACTUALIZAR ESTADO A ACEPTADA
                            supabase.table("citas_fercitas") \
                                .update({"estado": "aceptada"}).eq("id", cita['id']).execute()
                            st.success("¡Cita aceptada!")
                            st.rerun() # Refresca la interfaz para quitarla de pendientes

                with col2:
                    if st.button("Rechazar", key=f"rechazar_{cita['id']}"):
                        supabase.table("citas_fercitas") \
                            .update({"estado": "rechazada"}).eq("id", cita['id']).execute()
                        st.warning("Cita rechazada.")
                        st.rerun()

    st.markdown("---")
    st.markdown("### Mis Citas Confirmadas")
    
    aceptadas = supabase.table("citas_fercitas") \
        .select("*").eq("citado_id", mi_id_como_citado).eq("estado", "aceptada").execute()
        
    for cita in aceptadas.data:
        with st.container():
            st.write(f"**{cita['fecha_hora'][:10]}** - {cita['itinerario'][:30]}...")
            
            # Generar el contenido del archivo
            ical_data = generar_ical(cita['fecha_hora'], cita['itinerario'])
            
            # Botón nativo de Streamlit para descargas
            st.download_button(
                label="📥 Descargar para mi Calendario (.ical)",
                data=ical_data,
                file_name=f"Cita_Fercitas_{cita['fecha_hora'][:10]}.ics",
                mime="text/calendar",
                key=f"dl_{cita['id']}"
            )
