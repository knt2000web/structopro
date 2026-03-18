import streamlit as st
import json
import pandas as pd
import datetime

import os
st.set_page_config(
    page_title="Reinforced Concrete Suite",
    page_icon="🏗️",
    layout="wide",
)
st.sidebar.info(f"📍 Servidor ejecutándose desde: {os.getcwd()}")

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
# GESTOR GLOBAL DE PROYECTOS (SAVE / LOAD)
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Gestor de Proyectos")

project_name = st.sidebar.text_input("Nombre del Proyecto:", value=st.session_state.get("project_name", "Mi_Edificio"), key="project_name")
project_owner = st.sidebar.text_input("Propietario / Cliente:", value=st.session_state.get("project_owner", ""), key="project_owner")
project_address = st.sidebar.text_input("Dirección de Obra:", value=st.session_state.get("project_address", ""), key="project_address")
project_phone = st.sidebar.text_input("Teléfono de Contacto:", value=st.session_state.get("project_phone", ""), key="project_phone")

def serialize_state():
    state_dict = {}
    for k, v in st.session_state.items():
        if isinstance(v, pd.DataFrame):
            state_dict[k] = {"__type__": "dataframe", "data": v.to_dict(orient="records")}
        elif isinstance(v, (int, float, str, bool, list, dict)):
            state_dict[k] = v
    return json.dumps(state_dict, indent=4)

if project_name and project_owner and project_address and project_phone:
    st.sidebar.download_button(
        label="💾 Guardar Proyecto Local (.json)",
        data=serialize_state(),
        file_name=f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True
    )
else:
    st.sidebar.info("✍️ Por favor llena el Nombre, Propietario, Dirección y Teléfono para habilitar el guardado.")

uploaded_project = st.sidebar.file_uploader("📥 Cargar Proyecto (.json)", type=['json'])
if uploaded_project is not None:
    try:
        project_data = json.load(uploaded_project)
        for k, v in project_data.items():
            if isinstance(v, dict) and v.get("__type__") == "dataframe":
                st.session_state[k] = pd.DataFrame(v["data"])
            else:
                st.session_state[k] = v
        st.sidebar.success(f"Proyecto Cargado ✅")
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
