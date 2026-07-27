import streamlit as st
from supabase import create_client, Client
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from ics import Calendar, Event

st.set_page_config(page_title="Fercitas", page_icon="📅", layout="wide")

# 1. INICIALIZAR SESIÓN (Debe ir antes de cualquier validación)
if 'user' not in st.session_state:
    st.session_state.user = None

# 2. Conexión a Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# Función global para el iCal
def generar_ical(fecha_hora_str, itinerario):
    c = Calendar()
    e = Event()
    e.name = "Cita programada (Fercitas)"
    e.begin = fecha_hora_str 
    e.description = itinerario
    c.events.add(e)
    return c.serialize()

def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.rerun() 
    except Exception as e:
        st.error("Error al iniciar sesión. Revisa tus credenciales.")

def registrar(email, password, nombre):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            supabase.table("perfiles_fercitas").insert({
                "id": res.user.id,
                "nombre": nombre,
                "email": email
            }).execute()
            st.success("Cuenta creada exitosamente. Por favor, inicia sesión.")
    except Exception as e:
        # Esto te dirá exactamente qué falló en la base de datos
        st.error(f"Error detallado al crear la cuenta: {str(e)}")

# 3. Flujo de pantalla principal
if st.session_state.user is None:
    tab_login, tab_registro = st.tabs(["Iniciar Sesión", "Crear Cuenta"])
    
    with tab_login:
        with st.form("form_login"):
            email_login = st.text_input("Correo electrónico")
            pass_login = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                login(email_login, pass_login)
                
    with tab_registro:
        with st.form("form_registro"):
            nombre_reg = st.text_input("Tu Nombre Completo")
            email_reg = st.text_input("Correo electrónico")
            pass_reg = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Registrarse"):
                registrar(email_reg, pass_reg, nombre_reg)

else:
    # 4. SISTEMA PROTEGIDO (Todo indentado bajo el 'else')
    st.write(f"Bienvenido a Fercitas. Sesión iniciada como: {st.session_state.user.email}")
    
    if st.button("Cerrar Sesión"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    tab1, tab2 = st.tabs(["Solicitar Cita", "Gestión de Citas (Citado)"])

    with tab1:
        st.title("Fercitas 📅")
        st.markdown("### Solicitar una cita")
        
        # Traer la lista de otros usuarios para poder citarlos
        respuesta_usuarios = supabase.table("perfiles_fercitas").select("id, nombre").neq("id", st.session_state.user.id).execute()
        if not respuesta_usuarios.data:
            st.warning("No hay otros usuarios registrados en el sistema aún.")
        else:
            opciones_usuarios = {user["nombre"]: user["id"] for user in respuesta_usuarios.data}
            usuario_seleccionado = st.selectbox("¿A quién quieres citar?", options=list(opciones_usuarios.keys()))
        
        # 2. Configuración del calendario moderno
        calendar_options = {
            "headerToolbar": {
                "left": "today prev,next",
                "center": "title",
                "right": "timeGridWeek,timeGridDay"
            },
            "initialView": "timeGridWeek",
            "slotMinTime": "18:00:00", 
            "slotMaxTime": "24:00:00",
            "selectable": True,
            "allDaySlot": False,
            
            # --- NUEVOS PARÁMETROS ---
            # 1. Congela la zona horaria para evitar el desfase de 6 horas
            "timeZone": "UTC", 
            
            # 2. Elimina el espacio gigante en la última celda
            "height": "auto",
            "expandRows": False,
            
            # 3. Formato visual corporativo
            "eventColor": "#D4002B" 
        }
        
        events = [] 
        cal = calendar(events=events, options=calendar_options, key="calendario_fercitas")
        
        if cal.get("dateClick"):
            fecha_iso = cal["dateClick"]["date"]
            fecha_dt = datetime.fromisoformat(fecha_iso.replace('Z', '+00:00'))
            
            st.info(f"Iniciando solicitud para: {fecha_dt.strftime('%Y-%m-%d %H:%M')}")
            
            with st.form("form_cita"):
                st.text_area("Itinerario de la cita:", key="itinerario")
                submit = st.form_submit_button("Enviar Solicitud")
        
                if submit:
                    fecha_inicio = (fecha_dt - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
                    fecha_fin = (fecha_dt + timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()
        
                    # Usar el ID real del usuario seleccionado en el menú
                    citado_id_actual = opciones_usuarios[usuario_seleccionado]
        
                    respuesta = supabase.table("citas_fercitas").select("id") \
                        .eq("citado_id", citado_id_actual) \
                        .eq("estado", "aceptada") \
                        .gte("fecha_hora", fecha_inicio) \
                        .lte("fecha_hora", fecha_fin) \
                        .execute()
        
                    if len(respuesta.data) > 0:
                        st.error("❌ No es posible agendar. Esta persona ya tiene una cita confirmada para este día, el día anterior o el siguiente.")
                    else:
                        nueva_cita = {
                            "solicitante_id": st.session_state.user.id, # Variable real sin comillas
                            "citado_id": citado_id_actual,
                            "fecha_hora": fecha_iso,
                            "itinerario": st.session_state.itinerario,
                            "estado": "pendiente"
                        }
                        supabase.table("citas_fercitas").insert(nueva_cita).execute()
                        st.success("✅ Solicitud enviada correctamente. Esperando confirmación.")

    with tab2:
        st.markdown("### Solicitudes Entrantes")
        
        mi_id_como_citado = st.session_state.user.id # Variable real sin comillas

        pendientes = supabase.table("citas_fercitas") \
            .select("*").eq("citado_id", mi_id_como_citado).eq("estado", "pendiente").execute()

        if not pendientes.data:
            st.info("No tienes solicitudes pendientes en este momento.")
        else:
            for cita in pendientes.data:
                with st.container(border=True):
                    fecha_dt = datetime.fromisoformat(cita['fecha_hora'].replace('Z', '+00:00'))
                    st.subheader(f"📅 {fecha_dt.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Itinerario:** {cita['itinerario']}")

                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button("Aceptar Cita", key=f"aceptar_{cita['id']}"):
                            
                            fecha_inicio = (fecha_dt - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
                            fecha_fin = (fecha_dt + timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat()
                            
                            validacion = supabase.table("citas_fercitas").select("id") \
                                .eq("citado_id", mi_id_como_citado).eq("estado", "aceptada") \
                                .gte("fecha_hora", fecha_inicio).lte("fecha_hora", fecha_fin).execute()

                            if len(validacion.data) > 0:
                                st.error("No puedes aceptar esta cita. Ya confirmaste otra en este día, el anterior o el siguiente.")
                            else:
                                supabase.table("citas_fercitas") \
                                    .update({"estado": "aceptada"}).eq("id", cita['id']).execute()
                                st.success("¡Cita aceptada!")
                                st.rerun()

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
                
                ical_data = generar_ical(cita['fecha_hora'], cita['itinerario'])
                
                st.download_button(
                    label="📥 Descargar para mi Calendario (.ical)",
                    data=ical_data,
                    file_name=f"Cita_Fercitas_{cita['fecha_hora'][:10]}.ics",
                    mime="text/calendar",
                    key=f"dl_{cita['id']}"
                )
