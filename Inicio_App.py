import streamlit as st
import json
import pandas as pd
import datetime

from auth import sign_up_user, sign_in_user, sign_out_user, get_current_user, save_project_to_db, get_projects_from_db

st.set_page_config(
    page_title="Reinforced Concrete Suite",
    page_icon="🏗️",
    layout="wide",
)

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

def login_view():
    st.title("StructoPro")
    st.subheader("Acceso a la plataforma")

    tab1, tab2 = st.tabs(["Iniciar sesión", "Registrarse"])

    with tab1:
        email_login = st.text_input("Correo electrónico", key="login_email")
        password_login = st.text_input("Contraseña", type="password", key="login_password")

        if st.button("Ingresar", use_container_width=True):
            try:
                response = sign_in_user(email_login, password_login)
                if response.user:
                    st.session_state.auth_user = response.user
                    st.success("Inicio de sesión correcto")
                    st.rerun()
                else:
                    st.error("No se pudo iniciar sesión")
            except Exception as e:
                st.error(f"Error de acceso: {e}")

    with tab2:
        email_register = st.text_input("Correo electrónico", key="register_email")
        password_register = st.text_input("Contraseña", type="password", key="register_password")
        password_confirm = st.text_input("Confirmar contraseña", type="password", key="register_password_confirm")

        if st.button("Crear cuenta", use_container_width=True):
            if password_register != password_confirm:
                st.warning("Las contraseñas no coinciden")
            elif len(password_register) < 6:
                st.warning("La contraseña debe tener al menos 6 caracteres")
            else:
                try:
                    response = sign_up_user(email_register, password_register)
                    if response.user:
                        st.success("Cuenta creada correctamente. Revisa tu correo para confirmar el registro si Supabase lo solicita.")
                    else:
                        st.error("No se pudo crear la cuenta")
                except Exception as e:
                    st.error(f"Error de registro: {e}")

def logout_button():
    if st.sidebar.button("Cerrar sesión"):
        try:
            sign_out_user()
        except:
            pass
        st.session_state.auth_user = None
        st.rerun()

try:
    current_user = get_current_user()
    if current_user and getattr(current_user, "user", None):
        st.session_state.auth_user = current_user.user
except:
    pass

if not st.session_state.auth_user:
    login_view()
    st.stop()

st.sidebar.success(f"Sesión iniciada: {st.session_state.auth_user.email}")
logout_button()

st.sidebar.info("📍 Servidor ejecutándose desde: C:\\Users\\cagch\\Desktop\\Diagrama_NSR10")

st.title("🏗️ Suite de Diseño — Hormigón Armado (Multi-Norma)")
st.markdown("---")

st.markdown("""
### Bienvenido a la Suite Profesional de Diseño Estructural
A la izquierda encontrarás el menú de navegación con las herramientas agrupadas:

1. **[Columnas P–M y Circulares]** - Generación interactiva de diagramas de interacción y 3D en tiempo real. Exportación DXF/DOCX.
2. **[Vigas y Losas]** - Diseño a flexión, cortante, deflexiones, y punzonamiento de placas.
3. **[Otras Estructuras]** - Ménsulas, Capacidad Axial Corta, Cortante a distancia x y Losas 2D.
4. **[Cimentaciones y Muros]** - Esfuerzos, Estabilidad, Zapatas y Muros de contención.
5. **[Presupuesto APU Mercado]** - Web scraping en vivo para cotizar materiales, salarios y AIU.

👈 **Selecciona una herramienta en el menú lateral para comenzar.**
""")

# ─────────────────────────────────────────────
# ESTADO GLOBAL (SESIÓN)
# ─────────────────────────────────────────────
st.sidebar.header("🌎 Configuración Global del Proyecto")

# IMPORTANTE: Las llaves deben coincidir EXACTAMENTE con los diccionarios CODES de cada página
# No incluir emojis de banderas en las llaves — se muestran solo en la UI
NORMAS_DISPONIBLES = [
    "NSR-10 (Colombia)",
    "ACI 318-25 (EE.UU.)",
    "ACI 318-19 (EE.UU.)",
    "ACI 318-14 (EE.UU.)",
    "NEC-SE-HM (Ecuador)",
    "E.060 (Perú)",
    "NTC-EM (México)",
    "COVENIN 1753-2006 (Venezuela)",
    "NB 1225001-2020 (Bolivia)",
    "CIRSOC 201-2025 (Argentina)",
]

# Mapa visual limpio para el selectbox
NORMA_DISPLAY = {
    "NSR-10 (Colombia)":           "NSR-10 (Colombia)",
    "ACI 318-25 (EE.UU.)":         "ACI 318-25 (EE.UU.)",
    "ACI 318-19 (EE.UU.)":         "ACI 318-19 (EE.UU.)",
    "ACI 318-14 (EE.UU.)":         "ACI 318-14 (EE.UU.)",
    "NEC-SE-HM (Ecuador)":         "NEC-SE-HM (Ecuador)",
    "E.060 (Perú)":                "E.060 (Perú)",
    "NTC-EM (México)":             "NTC-EM (México)",
    "COVENIN 1753-2006 (Venezuela)": "COVENIN 1753-2006 (Venezuela)",
    "NB 1225001-2020 (Bolivia)":   "NB 1225001-2020 (Bolivia)",
    "CIRSOC 201-2025 (Argentina)": "CIRSOC 201-2025 (Argentina)",
}

if "norma_sel" not in st.session_state or st.session_state.norma_sel not in NORMAS_DISPONIBLES:
    st.session_state.norma_sel = NORMAS_DISPONIBLES[0]

# Mostrar limpio en UI
_norm_displayed = st.sidebar.selectbox(
    "Selecciona la Normativa de Diseño:",
    options=NORMAS_DISPONIBLES,
    format_func=lambda k: NORMA_DISPLAY.get(k, k),
    index=NORMAS_DISPONIBLES.index(st.session_state.get("norma_sel", NORMAS_DISPONIBLES[0])),
    key="norma_sel"
)

# Guardar la bandera (Imagen HD) en session_state para que la usen todas las páginas
_NORMA_FLAG_URL = {
    "NSR-10 (Colombia)":           "https://flagcdn.com/w80/co.png",
    "ACI 318-25 (EE.UU.)":         "https://flagcdn.com/w80/us.png",
    "ACI 318-19 (EE.UU.)":         "https://flagcdn.com/w80/us.png",
    "ACI 318-14 (EE.UU.)":         "https://flagcdn.com/w80/us.png",
    "NEC-SE-HM (Ecuador)":         "https://flagcdn.com/w80/ec.png",
    "E.060 (Perú)":                "https://flagcdn.com/w80/pe.png",
    "NTC-EM (México)":             "https://flagcdn.com/w80/mx.png",
    "COVENIN 1753-2006 (Venezuela)": "https://flagcdn.com/w80/ve.png",
    "NB 1225001-2020 (Bolivia)":   "https://flagcdn.com/w80/bo.png",
    "CIRSOC 201-2025 (Argentina)": "https://flagcdn.com/w80/ar.png",
}

st.session_state.norma_flag_url = _NORMA_FLAG_URL.get(st.session_state.norma_sel, "https://flagcdn.com/w80/un.png")

# Mostrar cuadro de exito con imagen HTML
html_flag = f"""
<div style="display: flex; align-items: center; background-color: #1e1e1e; padding: 10px; border-radius: 5px; border-left: 5px solid #4CAF50;">
    <img src="{st.session_state.norma_flag_url}" width="40" style="margin-right: 15px; border-radius: 3px;">
    <div>
        <span style="font-size: 12px; color: gray;">Norma Activa:</span><br>
        <strong style="color: white; font-size: 16px;">{st.session_state.norma_sel}</strong>
    </div>
</div>
<br>
"""
st.sidebar.markdown(html_flag, unsafe_allow_html=True)

if "idioma" not in st.session_state:
    st.session_state.idioma = "Español"

if "ACI 318" in st.session_state.norma_sel:
    st.session_state.idioma = st.sidebar.radio(
        "🌎 Idioma / Language:",
        ["Español", "English"],
        index=0 if st.session_state.idioma == "Español" else 1,
        horizontal=True
    )
else:
    st.session_state.idioma = "Español" # Forzar español para otras normas si no es ACI

# -----------------------------------------------------------------------------
# GESTOR GLOBAL DE PROYECTOS (NUBE / LOCAL)
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("☁️ Menú Mis Proyectos")

with st.sidebar.expander("📥 Cargar de la Nube", expanded=False):
    st.write("Selecciona tus cálculos previos:")
    if st.button("↻ Refrescar Lista", use_container_width=True):
        st.rerun()
        
    try:
        if st.session_state.get("auth_user"):
            proyectos_cloud = get_projects_from_db(st.session_state.auth_user)
            if proyectos_cloud:
                for p in proyectos_cloud:
                    with st.container():
                        st.markdown(f"**{p['nombre_proyecto']}**")
                        st.caption(f"{p['created_at'][:10]} | Resp: {p.get('propietario', '')}")
                        if st.button("Cargar ⬇️", key=f"load_{p['id']}", use_container_width=True):
                            project_data = p.get('estado_json', {})
                            if isinstance(project_data, str):
                                project_data = json.loads(project_data)
                            for k, v in project_data.items():
                                if isinstance(v, dict) and v.get("__type__") == "dataframe":
                                    st.session_state[k] = pd.DataFrame(v["data"])
                                else:
                                    st.session_state[k] = v
                            st.success(f"¡{p['nombre_proyecto']} Cargado Exitósamente!")
                    st.divider()
            else:
                st.info("No tienes proyectos en la nube.")
    except Exception as e:
        err_str = str(e)
        if "404" in err_str and "proyectos" in err_str:
            st.error("❌ La tabla 'proyectos' no existe en tu base de datos de Supabase.")
            with st.expander("🛠️ ¿Cómo solucionar este error?"):
                st.markdown("Ve a tu panel de **Supabase**, entra a **SQL Editor**, copia y ejecuta este código para crear la tabla necesaria:")
                st.code('''CREATE TABLE proyectos (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references auth.users not null,
  nombre_proyecto text not null,
  propietario text,
  direccion text,
  telefono text,
  estado_json jsonb,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Configura RLS (Row Level Security) para que cada usuario vea sólo lo suyo
alter table proyectos enable row level security;

create policy "Usuarios ven sus propios proyectos"
on proyectos for select
using ( auth.uid() = user_id );

create policy "Usuarios insertan sus proyectos"
on proyectos for insert
with check ( auth.uid() = user_id );

create policy "Usuarios actualizan sus proyectos"
on proyectos for update
using ( auth.uid() = user_id );''', language='sql')
        else:
            st.error(f"Error nube: {e}")

st.sidebar.subheader("📂 Guardar Estado Actual")

project_name = st.sidebar.text_input("Nombre del Proyecto:", value=st.session_state.get("project_name", "Mi_Edificio"), key="project_name")
project_owner = st.sidebar.text_input("Propietario / Cliente:", value=st.session_state.get("project_owner", ""), key="project_owner")
project_address = st.sidebar.text_input("Dirección de Obra:", value=st.session_state.get("project_address", ""), key="project_address")
project_phone = st.sidebar.text_input("Teléfono de Contacto:", value=st.session_state.get("project_phone", ""), key="project_phone")

def serialize_state_dict():
    state_dict = {}
    for k, v in st.session_state.items():
        if k in ["auth_user"]: # Omitir el usuario autenticado para no sobreescribir tokens
            continue
        if isinstance(v, pd.DataFrame):
            state_dict[k] = {"__type__": "dataframe", "data": v.to_dict(orient="records")}
        elif isinstance(v, (int, float, str, bool, list, dict)):
            state_dict[k] = v
    return state_dict

if project_name and project_owner and project_address and project_phone:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("☁️ Nube", help="Guardar en Supabase", use_container_width=True):
            try:
                save_project_to_db(
                    st.session_state.auth_user,
                    project_name, project_owner, project_address, project_phone,
                    serialize_state_dict()
                )
                st.success("¡Guardado Correcto en DB!")
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    with col2:
        st.download_button(
            label="💾 Local",
            data=json.dumps(serialize_state_dict(), indent=4),
            file_name=f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
            help="Descargar archivo JSON a tu Equipo"
        )
else:
    st.sidebar.info("✍️ Llena los datos arriba para habilitar el guardado.")

uploaded_project = st.sidebar.file_uploader("📥 Cargar Archivo Local (.json)", type=['json'])
if uploaded_project is not None:
    try:
        project_data = json.load(uploaded_project)
        for k, v in project_data.items():
            if isinstance(v, dict) and v.get("__type__") == "dataframe":
                st.session_state[k] = pd.DataFrame(v["data"])
            else:
                st.session_state[k] = v
        st.sidebar.success(f"Archivo Local Cargado ✅")
    except Exception as e:
        st.sidebar.error(f"Error al cargar: {e}")


# Inicializar APU global por si entran directo a otra pagina
if "apu_config" not in st.session_state:
    st.session_state.apu_config = {
        "moneda": "COP$",
        "cemento": 32000.0,
        "acero": 4500.0,
        "arena": 70000.0,
        "grava": 80000.0,
        "costo_dia_mo": 69333.33, # asumiendo smmlv+prestaciones basico
        "pct_herramienta": 0.05,
        "pct_aui": 0.30,
        "iva": 0.19,
        "pct_util": 0.05
    }

st.info("💡 Cada herramienta incluye Códigos Normativos en LaTeX, Paneles de Ayuda (Modo de uso), Generación de planos 3D y presupuestos APU locales.")

# ─────────────────────────────────────────────
# PIE DE PÁGINA / DERECHOS RESERVADOS
# ─────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: gray; font-size: 11px;">
    © 2026 Todos los derechos reservados.<br>
    <b>Realizado por:</b><br>
    Ing. Msc. César Augusto Giraldo Chaparro<br><br>
    <i>⚠️ Nota Legal: Esta herramienta es un apoyo profesional. El uso de los resultados es responsabilidad exclusiva del ingeniero diseñador.</i>
</div>
""", unsafe_allow_html=True)
