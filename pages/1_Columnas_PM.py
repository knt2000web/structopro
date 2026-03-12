import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import math
import io
import ezdxf
from docx import Document
from docx.shared import Inches, Pt
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en):
    return en if lang == "English" else es
# ─────────────────────────────────────────────

st.set_page_config(page_title=_t("Diagramas de Interacción", "Interaction Diagrams"), layout="wide")

st.image(r"C:\Users\cagch\.gemini\antigravity\brain\d408b5ad-3eb5-4039-b011-4650dd509d7e\columnas_pm_header_1773261175144.png", use_container_width=False, width=700)
st.title(_t("🏗️ Diagrama de Interacción P–M y Diseño de Estribos", "🏗️ P-M Interaction Diagram & Tie Design"))
st.markdown(_t(
    "Generador interactivo de capacidad a flexocompresión biaxial y cortante para **Columnas Cuadradas y Rectangulares**.",
    "Interactive biaxial flexure-compression and shear capacity generator for **Square and Rectangular Columns**."
))

with st.expander("📺 ¿Cómo usar esta herramienta?"):
    st.markdown("""
    **Modo de Uso:**
    1. **📍 Sidebar (Menú Izquierdo):** Selecciona la Norma de tu país, el nivel sísmico, la resistencia del concreto (f'c), el acero (fy), y la geometría de la columna (Base, Altura).
    2. **🏗️ Armadura:** Define el diámetro y cantidad de varillas longitudinales, así como el diámetro de los estribos.
    3. **🚦 Solicitaciones:** Ingresa el Momento Último (Mu) y la Carga Axial (Pu) calculados en tu software de análisis (ej. ETABS, SAP2000).
    4. **📊 Resultados:** Revisa la primera pestaña para ver el Diagrama P-M; el punto verde debe quedar DENTRO de la curva roja (Resistencia de Diseño).
    5. **📦 Exportar:** En la pestaña "Cantidades" encontrarás tu presupuesto APU y el botón para descargar la Memoria de Cálculo (Word). En "Sección y Estribos" podrás descargar el plano en AutoCAD (DXF).
    """)

# ─────────────────────────────────────────────
# DICCIONARIOS DE BARRAS
# ─────────────────────────────────────────────
REBAR_US = {
    "#3 (3/8\")": {"area": 0.71, "diam_mm": 9.53},
    "#4 (1/2\")": {"area": 1.29, "diam_mm": 12.70},
    "#5 (5/8\")": {"area": 1.99, "diam_mm": 15.88},
    "#6 (3/4\")": {"area": 2.84, "diam_mm": 19.05},
    "#7 (7/8\")": {"area": 3.87, "diam_mm": 22.23},
    "#8 (1\")":   {"area": 5.10, "diam_mm": 25.40},
    "#9 (1 1/8\")": {"area": 6.45, "diam_mm": 28.65},
    "#10 (1 1/4\")": {"area": 7.92, "diam_mm": 32.26},
}

REBAR_MM = {
    "10 mm": {"area": 0.785, "diam_mm": 10.0},
    "12 mm": {"area": 1.131, "diam_mm": 12.0},
    "14 mm": {"area": 1.539, "diam_mm": 14.0},
    "16 mm": {"area": 2.011, "diam_mm": 16.0},
    "18 mm": {"area": 2.545, "diam_mm": 18.0},
    "20 mm": {"area": 3.142, "diam_mm": 20.0},
    "22 mm": {"area": 3.801, "diam_mm": 22.0},
    "25 mm": {"area": 4.909, "diam_mm": 25.0},
    "28 mm": {"area": 6.158, "diam_mm": 28.0},
    "32 mm": {"area": 8.042, "diam_mm": 32.0},
}

STIRRUP_US = {
    "#2 (1/4\")": {"area": 0.32, "diam_mm": 6.35},
    "#3 (3/8\")": {"area": 0.71, "diam_mm": 9.53},
    "#4 (1/2\")": {"area": 1.29, "diam_mm": 12.70},
}

STIRRUP_MM = {
    "6 mm":  {"area": 0.283, "diam_mm": 6.0},
    "8 mm":  {"area": 0.503, "diam_mm": 8.0},
    "10 mm": {"area": 0.785, "diam_mm": 10.0},
    "12 mm": {"area": 1.131, "diam_mm": 12.0},
}

# ─────────────────────────────────────────────
# PARÁMETROS POR NORMA
# ─────────────────────────────────────────────
CODES = {
    "NSR-10 (Colombia)": {
        "phi_tied": 0.65, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 4.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["DMI — Disipación Mínima (Amenaza baja)", "DMO — Disipación Moderada (Amenaza media)", "DES — Disipación Especial (Amenaza alta)"],
        "ref": "NSR-10 Título C, Cap. C.10",
    },
    "ACI 318-25 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary Moment Frame (SDC A–B, amenaza baja)", "IMF — Intermediate Moment Frame (SDC C, amenaza media)", "SMF — Special Moment Frame (SDC D–F, amenaza alta)"],
        "ref": "ACI 318-25 Section 22.4",
    },
    "ACI 318-19 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary Moment Frame (SDC A–B, amenaza baja)", "IMF — Intermediate Moment Frame (SDC C, amenaza media)", "SMF — Special Moment Frame (SDC D–F, amenaza alta)"],
        "ref": "ACI 318-19 Section 22.4",
    },
    "ACI 318-14 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary Moment Frame (SDC A–B, amenaza baja)", "IMF — Intermediate Moment Frame (SDC C, amenaza media)", "SMF — Special Moment Frame (SDC D–F, amenaza alta)"],
        "ref": "ACI 318-14 Section 22.4",
    },
    "NEC-SE-HM (Ecuador)": {
        "phi_tied": 0.65, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["GS — Grado Sísmico Reducido (Amenaza baja)", "GM — Grado Sísmico Moderado", "GA — Grado Sísmico Alto (Estructuras especiales)"],
        "ref": "NEC-SE-HM (Ecuador) Cap. 4",
    },
    "E.060 (Perú)": {
        "phi_tied": 0.70, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["PO — Pórtico Ordinario (Zona 1–2, amenaza baja)", "PE — Pórtico Especial (Zona 3–4, amenaza alta)"],
        "ref": "Norma E.060 (Perú) Art. 9.3",
    },
    "NTC-EM (México)": {
        "phi_tied": 0.70, "phi_spiral": 0.80,
        "phi_tension": 0.85,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["MDL — Marcos de Ductilidad Limitada (Zona A baja)", "MROD — Marcos de Ductilidad Ordinaria (Zona B–C)", "MRLE — Marcos de Ductilidad Alta (Zona D–E alta)"],
        "ref": "NTC-EM México Cap. 2",
    },
    "COVENIN 1753-2006 (Venezuela)": {
        "phi_tied": 0.70, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["PO — Pórtico Ordinario (Zona 1, amenaza baja)", "PM — Pórtico Moderado (Zona 2–3)", "PE — Pórtico Especial (Zona 4–7, amenaza alta)"],
        "ref": "COVENIN 1753-2006 (Venezuela) — Basada en ACI 318-05. Sísmico: COVENIN 1756:2019",
    },
    "NB 1225001-2020 (Bolivia)": {
        "phi_tied": 0.65, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["DO — Diseño Ordinario (Amenaza baja, zona 1–2)", "DE — Diseño Especial Sísmico (Amenaza alta, zona 3–4)"],
        "ref": "NB 1225001-2020 (Bolivia) — Basada en ACI 318-19",
    },
    "CIRSOC 201-2025 (Argentina)": {
        "phi_tied": 0.65, "phi_spiral": 0.75,
        "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["GE — Grado Estándar (Amenaza sísmica baja)", "GM — Ductilidad Moderada (Amenaza media)", "GA — Ductilidad Alta / Zonas especiales"],
        "ref": "CIRSOC 201-2025 (Argentina) vigente desde Res. 11/2026 — Basada en ACI 318-19",
    },
}

# ─────────────────────────────────────────────
# PRESENTACIONES DE CEMENTO POR PAÍS
# Fuentes: fabricantes locales, normas comerciales
# ─────────────────────────────────────────────
CEMENT_BAGS = {
    "NSR-10 (Colombia)": [
        {"label": "Cemento gris clásico (Argos, El Cairo, Holcim)", "kg": 50.0},
        {"label": "Cemento Estructural / Tipo III (Argos Estructural)", "kg": 42.5},
        {"label": "Bolsa pequeña (presentación 25 kg)", "kg": 25.0},
    ],
    "ACI 318-25 (EE.UU.)": [
        {"label": "Type I/II sack estándar (94 lb)", "kg": 42.6},
        {"label": "Type III bolsa (47 lb)", "kg": 21.3},
    ],
    "ACI 318-19 (EE.UU.)": [
        {"label": "Type I/II sack estándar (94 lb)", "kg": 42.6},
        {"label": "Bolsa pequeña (47 lb)", "kg": 21.3},
    ],
    "ACI 318-14 (EE.UU.)": [
        {"label": "Type I/II sack estándar (94 lb)", "kg": 42.6},
        {"label": "Bolsa pequeña (47 lb)", "kg": 21.3},
    ],
    "NEC-SE-HM (Ecuador)": [
        {"label": "Cemento Holcim / Chimborazo (bulto estándar)", "kg": 50.0},
        {"label": "Bolsa pequeña", "kg": 25.0},
    ],
    "E.060 (Perú)": [
        {"label": "Cemento Andino / Pacasmayo / Yura (bolsa estándar)", "kg": 42.5},
        {"label": "Bolsa pequeña", "kg": 25.0},
    ],
    "NTC-EM (México)": [
        {"label": "Cemento Cemex / Cruz Azul / Moctezuma (bulto estándar)", "kg": 50.0},
        {"label": "Bolsa pequeña / práctica", "kg": 25.0},
    ],
    "COVENIN 1753-2006 (Venezuela)": [
        {"label": "Cemento Cemex Venezuela / Lafarge / Holcim (bulto estándar)", "kg": 42.5},
    ],
    "NB 1225001-2020 (Bolivia)": [
        {"label": "Cemento Fancesa / Viacha / Itacamba (bolsa estándar)", "kg": 50.0},
        {"label": "Bolsa pequeña", "kg": 25.0},
    ],
    "CIRSOC 201-2025 (Argentina)": [
        {"label": "Cemento Loma Negra / Holcim / Cementos Avellaneda (bolsa)", "kg": 50.0},
        {"label": "Bolsa pequeña", "kg": 25.0},
    ],
}

# ─────────────────────────────────────────────
# TABLA DE DOSIFICACIÓN ACI 211
# Proporciones típicas para concreto no aireado,
# árido máx 19 mm, asentamiento 75–100 mm
# Ref: ACI 211.1 - Standard Practice for Selecting Proportions
# ─────────────────────────────────────────────
# Keys: f'c en MPa, Values: {cemento, agua, arena, grava} en kg/m³
MIX_DESIGNS = [
    {"fc_mpa": 14.0, "cem": 250, "agua": 205, "arena": 810, "grava": 1060, "wc": 0.82},
    {"fc_mpa": 17.0, "cem": 290, "agua": 200, "arena": 780, "grava": 1060, "wc": 0.69},
    {"fc_mpa": 21.0, "cem": 350, "agua": 193, "arena": 720, "grava": 1060, "wc": 0.55},
    {"fc_mpa": 25.0, "cem": 395, "agua": 193, "arena": 680, "grava": 1020, "wc": 0.49},
    {"fc_mpa": 28.0, "cem": 430, "agua": 190, "arena": 640, "grava": 1000, "wc": 0.44},
    {"fc_mpa": 35.0, "cem": 530, "agua": 185, "arena": 580, "grava":  960, "wc": 0.35},
    {"fc_mpa": 42.0, "cem": 620, "agua": 180, "arena": 520, "grava":  910, "wc": 0.29},
    {"fc_mpa": 56.0, "cem": 740, "agua": 175, "arena": 450, "grava":  850, "wc": 0.24},
]

def get_mix_for_fc(fc_mpa):
    """Interpolación lineal de la tabla ACI 211 para el f'c dado."""
    if fc_mpa <= MIX_DESIGNS[0]["fc_mpa"]:
        return MIX_DESIGNS[0]
    if fc_mpa >= MIX_DESIGNS[-1]["fc_mpa"]:
        return MIX_DESIGNS[-1]
    for i in range(len(MIX_DESIGNS) - 1):
        lo, hi = MIX_DESIGNS[i], MIX_DESIGNS[i + 1]
        if lo["fc_mpa"] <= fc_mpa <= hi["fc_mpa"]:
            t = (fc_mpa - lo["fc_mpa"]) / (hi["fc_mpa"] - lo["fc_mpa"])
            return {k: lo[k] + t * (hi[k] - lo[k]) for k in ("cem", "agua", "arena", "grava", "wc")}
    return MIX_DESIGNS[-1]


# ─────────────────────────────────────────────
st.sidebar.header(_t("0. Norma de Diseño", "0. Design Code"))

if "norma_sel" not in st.session_state:
    st.session_state.norma_sel = list(CODES.keys())[0]

norma_sel = st.session_state.norma_sel
_PAIS_ISO = {"NSR-10 (Colombia)":"co","ACI 318-25 (EE.UU.)":"us","ACI 318-19 (EE.UU.)":"us","ACI 318-14 (EE.UU.)":"us","NEC-SE-HM (Ecuador)":"ec","E.060 (Perú)":"pe","NTC-EM (México)":"mx","COVENIN 1753-2006 (Venezuela)":"ve","NB 1225001-2020 (Bolivia)":"bo","CIRSOC 201-2025 (Argentina)":"ar"}
_iso = _PAIS_ISO.get(norma_sel, "un")
st.sidebar.markdown(
    f'<div style="background:#1e3a1e;border-radius:6px;padding:8px 12px;margin-bottom:4px;">'  
    f'<img src="https://flagcdn.com/24x18/{_iso}.png" style="vertical-align:middle;margin-right:8px;">'
    f'<span style="color:#7ec87e;font-weight:600;font-size:13px;">{_t("Norma Activa:","Active Code:")} {norma_sel}</span>'
    f'</div>',
    unsafe_allow_html=True
)
code = CODES[norma_sel]

nivel_sismico = st.sidebar.selectbox(
    _t("Nivel Sísmico / Ductilidad:", "Seismic / Ductility Level:"),
    code["seismic_levels"],
    index=0 if "c_pm_nivel_sismico" not in st.session_state else code["seismic_levels"].index(st.session_state.c_pm_nivel_sismico) if st.session_state.c_pm_nivel_sismico in code["seismic_levels"] else 0,
    key="c_pm_nivel_sismico",
    help=_t("Afecta los requisitos de estribos de confinamiento, no el diagrama P-M.", "Affects confinement tie requirements, not the P-M diagram.")
)
st.sidebar.caption(f"📖 {_t('Referencia', 'Reference')}: {code['ref']}")

# ─────────────────────────────────────────────
# SIDEBAR — MATERIALES
# ─────────────────────────────────────────────
st.sidebar.header(_t("1. Materiales", "1. Materials"))
fc_unit = st.sidebar.radio(_t("Unidad de f'c:", "f'c Unit:"), ["MPa", "PSI", "kg/cm²"], horizontal=True, key="c_pm_fc_unit")

if fc_unit == "PSI":
    psi_options = {
        "2500 PSI (≈ 17.2 MPa)": 2500,
        "3000 PSI (≈ 20.7 MPa)": 3000,
        "3500 PSI (≈ 24.1 MPa)": 3500,
        "4000 PSI (≈ 27.6 MPa)": 4000,
        "4500 PSI (≈ 31.0 MPa)": 4500,
        "5000 PSI (≈ 34.5 MPa)": 5000,
        "Personalizado": None
    }
    psi_choice = st.sidebar.selectbox("Resistencia f'c [PSI]", list(psi_options.keys()), 
                                      index=list(psi_options.keys()).index(st.session_state.c_pm_psi_choice) if "c_pm_psi_choice" in st.session_state and st.session_state.c_pm_psi_choice in psi_options else 1,
                                      key="c_pm_psi_choice")
    fc_psi = float(psi_options[psi_choice]) if psi_options[psi_choice] is not None else st.sidebar.number_input("f'c personalizado [PSI]", min_value=2000.0, max_value=12000.0, value=st.session_state.get("c_pm_fc_psi_custom", 3000.0), step=100.0, key="c_pm_fc_psi_custom")
    fc = fc_psi * 0.00689476
    st.sidebar.info(f"f'c = {fc_psi:.0f} PSI → **{fc:.2f} MPa**")
elif fc_unit == "kg/cm²":
    kgcm2_options = {
        "175 kg/cm² (≈ 17.2 MPa)": 175,
        "210 kg/cm² (≈ 20.6 MPa)": 210,
        "250 kg/cm² (≈ 24.5 MPa)": 250,
        "280 kg/cm² (≈ 27.5 MPa)": 280,
        "350 kg/cm² (≈ 34.3 MPa)": 350,
        "420 kg/cm² (≈ 41.2 MPa)": 420,
        "Personalizado": None
    }
    kgcm2_choice = st.sidebar.selectbox("Resistencia f'c [kg/cm²]", list(kgcm2_options.keys()), 
                                        index=list(kgcm2_options.keys()).index(st.session_state.c_pm_kgcm2_choice) if "c_pm_kgcm2_choice" in st.session_state and st.session_state.c_pm_kgcm2_choice in kgcm2_options else 1,
                                        key="c_pm_kgcm2_choice")
    fc_kgcm2 = float(kgcm2_options[kgcm2_choice]) if kgcm2_options[kgcm2_choice] is not None else st.sidebar.number_input("f'c personalizado [kg/cm²]", min_value=100.0, max_value=1200.0, value=st.session_state.get("c_pm_fc_kgcm2_custom", 210.0), step=10.0, key="c_pm_fc_kgcm2_custom")
    fc = fc_kgcm2 / 10.1972
    st.sidebar.info(f"f'c = {kgcm2_choice} kg/cm² → **{fc:.2f} MPa**")
else:
    fc = st.sidebar.number_input("Resistencia del Concreto (f'c) [MPa]", min_value=15.0, max_value=80.0, value=st.session_state.get("c_pm_fc_mpa", 21.0), step=1.0, key="c_pm_fc_mpa")

fy = st.sidebar.number_input("Fluencia del Acero (fy) [MPa]", min_value=240.0, max_value=500.0, value=st.session_state.get("c_pm_fy", 420.0), step=10.0, key="c_pm_fy")
Es = 200000.0

# ─────────────────────────────────────────────
# SIDEBAR — GEOMETRÍA
# ─────────────────────────────────────────────
st.sidebar.header("2. Geometría de la Sección")
b = st.sidebar.number_input("Base (b) [cm]", min_value=15.0, value=st.session_state.get("c_pm_b", 30.0), step=5.0, key="c_pm_b")
h = st.sidebar.number_input("Altura (h) [cm]", min_value=15.0, value=st.session_state.get("c_pm_h", 40.0), step=5.0, key="c_pm_h")
d_prime = st.sidebar.number_input("Recubrimiento al centroide (d') [cm]", min_value=2.0, value=st.session_state.get("c_pm_dprime", 5.0), step=0.5, key="c_pm_dprime")
L_col = st.sidebar.number_input("Altura libre de la columna (L) [cm]", min_value=50.0, value=st.session_state.get("c_pm_L", 300.0), step=25.0, key="c_pm_L",
    help="Se usa para calcular estribos y cantidades de materiales")

# ─────────────────────────────────────────────
# SIDEBAR — REFUERZO LONGITUDINAL
# ─────────────────────────────────────────────
st.sidebar.header("3. Refuerzo Longitudinal")
unit_system = st.sidebar.radio("Sistema de Unidades de las Varillas:", ["Pulgadas (EE. UU.)", "Milímetros (SI)"], key="c_pm_unit_system")

if unit_system == "Pulgadas (EE. UU.)":
    rebar_dict = REBAR_US
    default_rebar = "#5 (5/8\")"
else:
    rebar_dict = REBAR_MM
    default_rebar = "16 mm"

rebar_type = st.sidebar.selectbox("Diámetro de las Varillas", list(rebar_dict.keys()),
    index=list(rebar_dict.keys()).index(st.session_state.c_pm_rebar_type) if "c_pm_rebar_type" in st.session_state and st.session_state.c_pm_rebar_type in rebar_dict else list(rebar_dict.keys()).index(default_rebar),
    key="c_pm_rebar_type")
rebar_area  = rebar_dict[rebar_type]["area"]    # cm²
rebar_diam  = rebar_dict[rebar_type]["diam_mm"] # mm

num_filas_h = st.sidebar.number_input("# de filas Acero Horiz (Superior e Inferior)", min_value=2, max_value=15, value=st.session_state.get("c_pm_num_h", 2), step=1, key="c_pm_num_h")
num_filas_v = st.sidebar.number_input("# de filas Acero Vert (Laterales)", min_value=2, max_value=15, value=st.session_state.get("c_pm_num_v", 2), step=1, key="c_pm_num_v")

# Armar capas
layers = []
layers.append({'d': d_prime, 'As': num_filas_h * rebar_area})
num_capas_intermedias = num_filas_v - 2
if num_capas_intermedias > 0:
    espacio_h = (h - 2 * d_prime) / (num_capas_intermedias + 1)
    for i in range(1, num_capas_intermedias + 1):
        layers.append({'d': d_prime + i * espacio_h, 'As': 2 * rebar_area})
layers.append({'d': h - d_prime, 'As': num_filas_h * rebar_area})

n_barras_total = num_filas_h * 2 + num_capas_intermedias * 2
Ast = sum([layer['As'] for layer in layers])
Ag  = b * h
st.sidebar.markdown(f"**Total varillas:** {n_barras_total} | **Ast:** {Ast:.2f} cm²")

# ─────────────────────────────────────────────
# SIDEBAR — ESTRIBOS
# ─────────────────────────────────────────────
st.sidebar.header("4. Estribos (Flejes)")
if unit_system == "Pulgadas (EE. UU.)":
    stirrup_dict = STIRRUP_US
    default_stirrup = "#3 (3/8\")"
else:
    stirrup_dict = STIRRUP_MM
    default_stirrup = "8 mm"

stirrup_type = st.sidebar.selectbox("Diámetro del Estribo", list(stirrup_dict.keys()),
    index=list(stirrup_dict.keys()).index(st.session_state.c_pm_stirrup_type) if "c_pm_stirrup_type" in st.session_state and st.session_state.c_pm_stirrup_type in stirrup_dict else list(stirrup_dict.keys()).index(default_stirrup),
    key="c_pm_stirrup_type")
stirrup_area = stirrup_dict[stirrup_type]["area"]     # cm²
stirrup_diam = stirrup_dict[stirrup_type]["diam_mm"]  # mm

# ─────────────────────────────────────────────
# SIDEBAR — TIPO DE COLUMNA Y NORMA
# ─────────────────────────────────────────────
st.sidebar.header("5. Factores de Diseño")
col_type_options = ["Estribos (Tied)", "Espiral (Spiral)"] if lang == "Español" else ["Tied", "Spiral"]
col_type = st.sidebar.selectbox(_t("Tipo de Columna", "Column Type"), 
                                col_type_options,
                                index=col_type_options.index(st.session_state.c_pm_col_type) if "c_pm_col_type" in st.session_state and st.session_state.c_pm_col_type in col_type_options else 0,
                                key="c_pm_col_type")
if "Estrib" in col_type or col_type == "Tied":
    phi_c_max  = code["phi_tied"]
    p_max_factor = code["pmax_tied"]
else:
    phi_c_max  = code["phi_spiral"]
    p_max_factor = code["pmax_spiral"]

phi_tension   = code["phi_tension"]
rho_min_code  = code["rho_min"]
rho_max_code  = code["rho_max"]
eps_full      = code["eps_tension_full"]

# -----------------------------------------------------------------------------
# GESTOR GLOBAL DE PROYECTOS (SAVE / LOAD)
# -----------------------------------------------------------------------------
import json
import datetime
st.sidebar.markdown("---")
st.sidebar.subheader("📂 Gestor de Proyectos")

project_name = st.sidebar.text_input("Nombre del Proyecto:", value=st.session_state.get("project_name", "Mi_Edificio"))
project_owner = st.sidebar.text_input("Propietario / Cliente:", value=st.session_state.get("project_owner", ""))
project_address = st.sidebar.text_input("Dirección de Obra:", value=st.session_state.get("project_address", ""))
project_phone = st.sidebar.text_input("Teléfono de Contacto:", value=st.session_state.get("project_phone", ""))

st.session_state.project_name = project_name
st.session_state.project_owner = project_owner
st.session_state.project_address = project_address
st.session_state.project_phone = project_phone

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
    st.sidebar.info("✍️ Por favor llena Nombre, Propietario, Dirección y Teléfono para habilitar el guardado.")

uploaded_project = st.sidebar.file_uploader("📥 Cargar Proyecto (.json)", type=['json'])
if uploaded_project is not None:
    try:
        project_data = json.load(uploaded_project)
        for k, v in project_data.items():
            if isinstance(v, dict) and v.get("__type__") == "dataframe":
                st.session_state[k] = pd.DataFrame(v["data"])
            else:
                st.session_state[k] = v
        st.sidebar.success(f"Proyecto Cargado ✅ (Nota: Recarga la página o cambia un dato para refrescar la visualización)")
    except Exception as e:
        st.sidebar.error(f"Error al cargar: {e}")

# ─────────────────────────────────────────────
# SIDEBAR — VERIFICACIÓN Y UNIDADES
# ─────────────────────────────────────────────
st.sidebar.header("6. Verificación de Diseño")
unidades_salida = st.sidebar.radio("Unidades del Diagrama (Resultados):", ["KiloNewtons (kN, kN-m)", "Toneladas Fuerza (tonf, tonf-m)"])

if unidades_salida == "Toneladas Fuerza (tonf, tonf-m)":
    factor_fuerza = 0.1019716
    unidad_fuerza = "tonf"
    unidad_mom    = "tonf-m"
else:
    factor_fuerza = 1.0
    unidad_fuerza = "kN"
    unidad_mom    = "kN-m"

st.sidebar.markdown(f"Cargas últimas en **{unidad_fuerza}** y **{unidad_mom}**:")
M_u_input = st.sidebar.number_input(f"Momento Último (Mu) [{unidad_mom}]",   value=round(45.0 * factor_fuerza, 2), step=round(10.0 * factor_fuerza, 2))
P_u_input = st.sidebar.number_input(f"Carga Axial Última (Pu) [{unidad_fuerza}]", value=round(2700.0 * factor_fuerza, 2), step=round(50.0 * factor_fuerza, 2))

# ─────────────────────────────────────────────
# CÁLCULO DEL DIAGRAMA P-M
# ─────────────────────────────────────────────
eps_cu = 0.003
eps_y  = fy / Es

# beta_1 (ACI / NSR-10 / todas las normas latinoamericanas)
if fc <= 28:
    beta_1 = 0.85
elif fc < 55:
    beta_1 = 0.85 - 0.05 * (fc - 28) / 7.0
else:
    beta_1 = 0.65
beta_1 = max(beta_1, 0.65)

b_mm = b * 10; h_mm = h * 10
Po_kN = (0.85 * fc * (Ag * 100 - Ast * 100) + fy * Ast * 100) / 1000.0

c_vals = np.concatenate([np.linspace(1e-5, h, 120), np.linspace(h, h * 12, 60)])
P_n_list = []; M_n_list = []; phi_P_n_list = []; phi_M_n_list = []

for c_cm in c_vals:
    c_mm = c_cm * 10
    a_mm = min(beta_1 * c_mm, h_mm)
    Cc   = 0.85 * fc * a_mm * b_mm  # N
    Mc   = Cc * (h_mm / 2.0 - a_mm / 2.0)  # N·mm

    Ps = 0.0; Ms = 0.0; eps_t = 0.0
    for layer in layers:
        d_i_mm = layer['d'] * 10
        As_i   = layer['As'] * 100  # mm²
        eps_s  = eps_cu * (c_mm - d_i_mm) / c_mm
        if d_i_mm >= max(l['d'] * 10 for l in layers):
            eps_t = eps_s
        fs = max(-fy, min(fy, Es * eps_s))
        if a_mm > d_i_mm and fs > 0:
            fs -= 0.85 * fc
        Ps += As_i * fs
        Ms += As_i * fs * (h_mm / 2.0 - d_i_mm)

    Pn = (Cc + Ps) / 1000.0  # kN
    Mn = abs((Mc + Ms) / 1_000_000.0)  # kN·m

    # φ interpolado
    eps_t_tens = -eps_t
    if eps_t_tens <= eps_y:
        phi = phi_c_max
    elif eps_t_tens >= eps_full:
        phi = phi_tension
    else:
        phi = phi_c_max + (phi_tension - phi_c_max) * (eps_t_tens - eps_y) / (eps_full - eps_y)

    Pn_max_val    = p_max_factor * Po_kN
    phi_Pn_max_val = phi_c_max * Pn_max_val

    Pn    = min(Pn, Pn_max_val)
    phi_Pn = min(phi * Pn, phi_Pn_max_val)
    phi_Mn = phi * Mn

    P_n_list.append(Pn); M_n_list.append(Mn)
    phi_P_n_list.append(phi_Pn); phi_M_n_list.append(phi_Mn)

P_n_arr     = np.array(P_n_list)   * factor_fuerza
M_n_arr     = np.array(M_n_list)   * factor_fuerza
phi_P_n_arr = np.array(phi_P_n_list) * factor_fuerza
phi_M_n_arr = np.array(phi_M_n_list) * factor_fuerza

Pt          = -fy * Ast * 100 / 1000.0 * factor_fuerza
Pn_max      = p_max_factor * Po_kN * factor_fuerza
phi_Pn_max  = phi_c_max * Pn_max / factor_fuerza * factor_fuerza  # already scaled
Po_display  = Po_kN * factor_fuerza

# ─────────────────────────────────────────────
# CÁLCULO DE ESTRIBOS
# ─────────────────────────────────────────────
# Separación básica (todos los códigos) — NSR-10 C.7.10.5 / ACI 318-25 25.7.2
s1 = 16 * rebar_diam / 10   # cm  (16 × dbl)
s2 = 48 * stirrup_diam / 10 # cm  (48 × dt)
s3 = min(b, h)               # cm  (menor dimensión)
s_basico = min(s1, s2, s3)

# Para zonas de confinamiento especial (DES/SMF/GA...) — NSR-10 C.21.6.4
s_conf = min(
    6 * rebar_diam / 10,  # 6 × dbl
    min(b, h) / 4,         # b o h / 4
    15.0                   # máx 15 cm
)

# Longitud de zona de confinamiento (Lo) — mayor de 3 condiciones
Lo_conf = max(max(b, h), L_col / 6.0, 45.0)  # cm

# Recubrimiento libre y perímetro del estribo exterior
recub_cm = max(d_prime - rebar_diam / 20.0, 2.5)
perim_estribo = 2 * (b - 2 * recub_cm) + 2 * (h - 2 * recub_cm) + 6 * stirrup_diam / 10  # cm

# ── Zona especial: SOLO DES / SMF / GA / PE / DE / MRLE (alta amenaza) ──
nivel_lower = nivel_sismico.lower()
zona_especial = any(k in nivel_lower for k in [
    "des ", "disipación especial",          # NSR-10 DES
    "smf", "special moment frame",          # ACI
    "ga —", "ductilidad alta",              # Argentina / Ecuador
    "pe —", "pórtico especial",             # Perú / Venezuela
    "de —", "diseño especial sísmico",      # Bolivia / NEC
    "mrle",                                 # México ductilidad alta
])
# DMI, IMF, MROD, GM, PM, GS = zona moderada → aplica s_basico (no confinamiento especial)

if zona_especial:
    n_estribos_zona    = math.ceil(Lo_conf / s_conf) + 1
    n_estribos_zona_dos = n_estribos_zona * 2
    longitud_zona_libre = max(0, L_col - 2 * Lo_conf)
    n_estribos_centro  = max(0, math.ceil(longitud_zona_libre / s_basico) - 1)
    n_estribos_total   = n_estribos_zona_dos + n_estribos_centro
    s_usar = s_conf
else:
    n_estribos_total = math.ceil(L_col / s_basico) + 1
    s_usar = s_basico
    Lo_conf = 0.0

# ── Flejes intermedios (crossties) — NSR-10 C.7.10.5.3 / ACI 318 R25.7.2 ──
# Requeridos cuando la separación libre entre barras lateralmente apoyadas > 15 cm
# Se colocan paralelos al estribo exterior en la dirección de b
if num_filas_h > 1:
    sep_horiz = (b - 2 * d_prime) / (num_filas_h - 1)  # separación entre barras horizontales
else:
    sep_horiz = 0.0

# Número de crossties necesarios por cara horizontal
# Cada crosstie apoya una barra intermedia que esté a > 15 cm del apoyo más cercano
n_crossties_por_estribo = 0
if num_filas_h > 2 and sep_horiz > 15.0:
    # Barras intermedias (excluir las de las esquinas)
    n_crossties_por_estribo = num_filas_h - 2  # barras internas sin apoyo lateral

# Longitud de cada crosstie (paralelo a b): libre interior + ganchos
# Gancho estándar: 6*dt (90°) + 3*dt (135°) ≈ 9*dt extendidos ≈ aprox 2 × 6dt = 12dt (dos extremos)
longitud_crosstie = (b - 2 * recub_cm) + 12 * stirrup_diam / 10  # cm

# También verificar en dirección h para barras verticales > 2 capas intermedias
if num_capas_intermedias > 0:
    sep_vert = (h - 2 * d_prime) / (num_capas_intermedias + 1)
    n_crossties_v = num_capas_intermedias if sep_vert > 15.0 else 0
    longitud_crosstie_v = (h - 2 * recub_cm) + 12 * stirrup_diam / 10
else:
    n_crossties_v = 0
    longitud_crosstie_v = 0

total_crossties_h = n_crossties_por_estribo * 2  # superior e inferior
total_crossties_v = n_crossties_v * 2             # izquierda y derecha
total_crossties_por_estribo = total_crossties_h + total_crossties_v

longitud_total_crossties_m = (
    n_estribos_total * total_crossties_h * longitud_crosstie / 100
    + n_estribos_total * total_crossties_v * longitud_crosstie_v / 100
)

# Peso total de crossties
peso_crossties_kg = longitud_total_crossties_m * stirrup_area * 100 * 7.85e-3

# ── Pesos totales ──
peso_unit_estribo     = (perim_estribo / 100.0) * (stirrup_area * 100) * 7.85e-3  # kg/estribo
peso_total_estribos_kg = n_estribos_total * peso_unit_estribo + peso_crossties_kg
longitud_total_estribos_m = n_estribos_total * perim_estribo / 100.0 + longitud_total_crossties_m


# ─────────────────────────────────────────────
# CANTIDADES DE MATERIALES
# ─────────────────────────────────────────────
vol_concreto_m3  = (b / 100) * (h / 100) * (L_col / 100)
peso_acero_long_kg = Ast * (L_col * 10) * 7.85e-3  # Ast cm² × L mm × 7.85e-3 → kg
peso_total_acero_kg = peso_acero_long_kg + peso_total_estribos_kg
relacion_acero_kg_m3 = peso_total_acero_kg / vol_concreto_m3 if vol_concreto_m3 > 0 else 0

# ─────────────────────────────────────────────
# DIAGRAMA DE SECCIÓN TRANSVERSAL
# ─────────────────────────────────────────────
def dibujar_seccion(b, h, d_prime, layers, num_filas_h, num_capas_intermedias,
                    rebar_diam, stirrup_diam, recub_cm):
    fig_s, ax_s = plt.subplots(figsize=(4, 4 * h / b))
    ax_s.set_aspect('equal')
    ax_s.set_facecolor('#1a1a2e')
    fig_s.patch.set_facecolor('#1a1a2e')

    # Sección concreto
    concreto = patches.Rectangle((0, 0), b, h, linewidth=2,
        edgecolor='white', facecolor='#4a4a6a')
    ax_s.add_patch(concreto)

    # Estribo
    st_thick = stirrup_diam / 20.0
    recub_e = recub_cm - rebar_diam / 20
    estribo = patches.Rectangle(
        (recub_e, recub_e), b - 2 * recub_e, h - 2 * recub_e,
        linewidth=max(1, st_thick), edgecolor='#00d4ff', facecolor='none', linestyle='--')
    ax_s.add_patch(estribo)

    # Barras longitudinales
    r_bar = rebar_diam / 20.0  # radio en cm

    # Capa superior: num_filas_h barras distribuidas en b
    def _draw_row(y_pos, n_bars):
        if n_bars == 1:
            xs = [b / 2]
        else:
            xs = np.linspace(d_prime, b - d_prime, n_bars)
        for x in xs:
            circ = plt.Circle((x, y_pos), r_bar, color='#ff6b35', zorder=5)
            ax_s.add_patch(circ)

    # Capa superior
    _draw_row(h - d_prime, num_filas_h)
    # Capas intermedias (2 barras laterales)
    if num_capas_intermedias > 0:
        espacio = (h - 2 * d_prime) / (num_capas_intermedias + 1)
        for i in range(1, num_capas_intermedias + 1):
            y_int = d_prime + i * espacio
            # Barra izquierda
            ax_s.add_patch(plt.Circle((d_prime, y_int), r_bar, color='#ff6b35', zorder=5))
            # Barra derecha
            ax_s.add_patch(plt.Circle((b - d_prime, y_int), r_bar, color='#ff6b35', zorder=5))
    # Capa inferior
    _draw_row(d_prime, num_filas_h)

    # Etiquetas de dimensión
    ax_s.annotate('', xy=(b, -0.8), xytext=(0, -0.8),
        arrowprops=dict(arrowstyle='<->', color='white', lw=1.5))
    ax_s.text(b / 2, -1.5, f"b = {b:.0f} cm", ha='center', va='top',
        color='white', fontsize=7)
    ax_s.annotate('', xy=(-0.8, h), xytext=(-0.8, 0),
        arrowprops=dict(arrowstyle='<->', color='white', lw=1.5))
    ax_s.text(-1.5, h / 2, f"h = {h:.0f} cm", ha='right', va='center',
        color='white', fontsize=7, rotation=90)

    ax_s.set_xlim(-3, b + 2)
    ax_s.set_ylim(-3, h + 2)
    ax_s.axis('off')
    ax_s.set_title(f"Sección Transversal\n{b:.0f}×{h:.0f} cm — {n_barras_total} varillas Ø{rebar_diam:.0f}mm",
        color='white', fontsize=8)
    return fig_s

# ─────────────────────────────────────────────
# LAYOUT PRINCIPAL
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([_t("📊 Diagrama P–M", "📊 P–M Diagram"), _t("🔲 Sección & Estribos", "🔲 Section & Ties"), _t("📦 Cantidades de Materiales", "📦 Material Quantities")])

# ══════════════ TAB 1 — DIAGRAMA ══════════════
with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Gráfica P–M — {norma_sel}")
        fig, ax = plt.subplots(figsize=(8, 6))

        idx_M_nom = np.argmax(M_n_arr);  M_nom_max = M_n_arr[idx_M_nom];  P_at_Mnom = P_n_arr[idx_M_nom]
        idx_M_dis = np.argmax(phi_M_n_arr); M_dis_max = phi_M_n_arr[idx_M_dis]

        ax.plot(M_n_arr, P_n_arr, label=r"Resistencia Nominal ($P_n, M_n$)",
            color="blue", linestyle="--")
        ax.plot(phi_M_n_arr, phi_P_n_arr, label=r"Resistencia de Diseño ($\phi P_n, \phi M_n$)",
            color="red", linewidth=2)

        # Anotaciones Pmax
        ax.annotate(f"{Pn_max:.2f} [{unidad_fuerza}]", xy=(0, Pn_max),
            xytext=(5, 5), textcoords="offset points", ha='left', va='bottom', fontsize=8, color='blue')
        phi_Pn_max_disp = phi_c_max * Pn_max
        ax.annotate(f"{phi_Pn_max_disp:.2f} [{unidad_fuerza}]", xy=(0, phi_Pn_max_disp),
            xytext=(5, -5), textcoords="offset points", ha='left', va='top', fontsize=8, color='red')

        # Momento máximo
        ax.plot([M_nom_max, M_nom_max], [0, P_at_Mnom], color='gray', linestyle='--', alpha=0.5)
        ax.annotate(f"{M_nom_max:.2f} [{unidad_mom}]", xy=(M_nom_max, 0),
            xytext=(0, -15), textcoords="offset points", ha='center', va='top', fontsize=8)
        ax.plot([M_dis_max, M_dis_max], [0, phi_P_n_arr[idx_M_dis]], color='gray', linestyle='--', alpha=0.5)
        ax.annotate(f"{M_dis_max:.2f} [{unidad_mom}]", xy=(M_dis_max, 0),
            xytext=(0, -28), textcoords="offset points", ha='center', va='top', fontsize=8)

        # Tracción pura
        ax.annotate(f"{Pt:.2f} [{unidad_fuerza}]", xy=(0, Pt),
            xytext=(5, -5), textcoords="offset points", ha='left', va='top', fontsize=8, color='blue')
        ax.annotate(f"{phi_tension * Pt:.2f} [{unidad_fuerza}]", xy=(0, phi_tension * Pt),
            xytext=(5, 5), textcoords="offset points", ha='left', va='bottom', fontsize=8, color='red')

        ax.axhline(0, color='black', linewidth=1)

        # Punto de diseño
        ax.plot(M_u_input, P_u_input, 'o', markersize=9, color='lime',
            markeredgecolor='black', zorder=6, label="Punto de Diseño (Mu, Pu)")
        ax.plot([M_u_input, M_u_input], [0, P_u_input], color='lime', linestyle=':', alpha=0.7)
        ax.plot([0, M_u_input], [P_u_input, P_u_input], color='lime', linestyle=':', alpha=0.7)
        ax.annotate(f"[{M_u_input:g} {unidad_mom} : {P_u_input:g} {unidad_fuerza}]",
            xy=(M_u_input, P_u_input), xytext=(6, 6), textcoords="offset points",
            fontsize=9, weight='bold', color='green')

        ax.set_xlabel(f"Momento Flector M [{unidad_mom}]")
        ax.set_ylabel(f"Carga Axial P [{unidad_fuerza}]")
        ax.set_xlim(left=0)
        ax.set_title(f"Diagrama de Interacción — {norma_sel}\nColumna {b:.0f}×{h:.0f} cm  |  f'c={fc:.1f} MPa  |  fy={fy:.0f} MPa  |  {nivel_sismico.split('—')[0].strip()}")
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="upper right", fontsize=8)
        st.pyplot(fig)

    with col2:
        st.subheader("Resumen")
        cuantia = Ast / Ag * 100

        st.markdown(f"**Norma:** {norma_sel}")
        st.markdown(f"**Nivel Sísmico:** {nivel_sismico}")
        st.markdown(f"**φ compresión:** {phi_c_max} | **φ tensión:** {phi_tension}")
        st.markdown("---")
        st.markdown("#### Verificación de Cuantía")
        cuantia_estado = "✅ CUMPLE" if rho_min_code <= cuantia <= rho_max_code else ("⚠️ ALTA" if cuantia > rho_max_code else "❌ NO CUMPLE")

        data_cuantia = {
            "Parámetro": [
                "Dimensiones (b × h)",
                "Área Bruta (Ag = b×h)",
                f"# Varillas Horiz. (2×{num_filas_h})",
                f"# Varillas Vert. interm. ({num_capas_intermedias}×2)",
                "Total varillas (n)",
                f"Área varilla (Ab) — {rebar_type}",
                "Área Acero (Ast = n×Ab)",
                "Cuantía ρ = Ast/Ag×100%",
                f"ρ mín ({norma_sel.split('(')[0].strip()})",
                f"ρ máx ({norma_sel.split('(')[0].strip()})",
            ],
            "Valor": [
                f"{b:.0f}×{h:.0f} cm",
                f"{Ag:.1f} cm²",
                f"{num_filas_h * 2} barras",
                f"{num_capas_intermedias * 2} barras",
                f"{n_barras_total} barras",
                f"{rebar_area:.3f} cm²",
                f"{Ast:.3f} cm²",
                f"{cuantia:.3f}%",
                f"{rho_min_code:.1f}%",
                f"{rho_max_code:.1f}%",
            ],
            "Estado": ["—"] * 7 + [cuantia_estado, "—", "—"],
        }
        st.dataframe(pd.DataFrame(data_cuantia), use_container_width=True, hide_index=True)

        st.markdown(r"**" + _t("Revisión Cuantía:", "Reinforcement Ratio Check:") + r"** $\rho_{\text{min}} \le \rho_{\text{Bruta}} \le \rho_{\text{max}}$")
        st.latex(r"\rho_{\text{Bruta}} = \frac{A_{\text{Acero}}}{A_{\text{Gruesa}}}")
        percent_rho = cuantia # Renamed for clarity with the new snippet
        rho_min = rho_min_code
        rho_max = rho_max_code
        ok_rho = rho_min <= percent_rho <= rho_max

        if ok_rho:
            st.success(_t(f"✅ Aprobado Cuantía: $\\rho_{{\\text{{Bruta}}}} = {percent_rho:.2f}\\%$ (Límites: {rho_min}% - {rho_max}%)", f"✅ Ratio OK: $\\rho_{{\\text{{Bruta}}}} = {percent_rho:.2f}\\%$ (Limits: {rho_min}% - {rho_max}%)"))
        else:
            if percent_rho < rho_min:
                st.error(_t(f"❌ No Aprobado Cuantía: $\\rho_{{\\text{{Bruta}}}} = {percent_rho:.2f}\\% < {rho_min}\\%$ $\\rightarrow$ **Aumentar acero protector o diámetro**", f"❌ Ratio Fails: $\\rho_{{\\text{{Bruta}}}} = {percent_rho:.2f}\\% < {rho_min}\\%$ $\\rightarrow$ **Increase steel or diameter**"))
            else:
                st.error(_t(f"❌ No Aprobado Cuantía: $\\rho_{{\\text{{Bruta}}}} = {percent_rho:.2f}\\% > {rho_max}\\%$ $\\rightarrow$ **Aumentar sección de concreto**", f"❌ Ratio Fails: $\\rho_{{\\text{{Bruta}}}} = {percent_rho:.2f}\\% > {rho_max}\\%$ $\\rightarrow$ **Increase concrete section**"))

        st.markdown("---")
        st.markdown("#### Puntos Clave P–M")
        # Placeholder values for phi_Pn_max_y, np.interp, pts_x, pts_y, phi_Pn_min
        # These variables are not defined in the provided context, so I'll use dummy values or assume they are meant to be derived from the existing P_n_arr, phi_P_n_arr, etc.
        # For a faithful edit, I will use the existing calculated values where possible.
        phi_Pn_max_y = phi_c_max * Pn_max # Assuming this is the max phi Pn
        phi_Pn_min = phi_tension * Pt # Assuming this is the min phi Pn (pure tension)

        # For pure moment, we need to find where P is close to 0.
        # This is a simplification as the original code doesn't explicitly calculate pure Mx and My for a 3D diagram.
        # For a 2D P-M diagram, pure moment is where P=0.
        # We'll approximate by finding the Mn value when P is near zero.
        # This part of the instruction seems to imply a 3D interaction diagram context, which is not fully present in the provided code snippet for the 2D P-M.
        # I will use a simplified approach for the 2D P-M diagram's pure moment.
        # Find the index where phi_P_n_arr is closest to 0
        idx_pure_moment = np.argmin(np.abs(phi_P_n_arr))
        pure_moment_val = phi_M_n_arr[idx_pure_moment]

        data_pm = {
            "Descripción": [
                _t("Capacidad bruta (Po)", "Gross Capacity (Po)"),
                _t(f"Pn,máx ({p_max_factor:.0%}×Po)", f"Pn,max ({p_max_factor:.0%}×Po)"),
                _t(f"φPn,máx (φ={phi_c_max}×Pn,máx)", f"φPn,max (φ={phi_c_max}×Pn,max)"),
                _t(f"Tracción pura (Pt = −fy×Ast)", f"Pure Tension (Pt = −fy×Ast)"),
                _t(f"φTracción pura (φt={phi_tension}×Pt)", f"φPure Tension (φt={phi_tension}×Pt)"),
            ],
            f"[{unidad_fuerza}]": [
                f"{Po_display:.2f}",
                f"{Pn_max:.2f}",
                f"{phi_c_max * Pn_max:.2f}",
                f"{Pt:.2f}",
                f"{phi_tension * Pt:.2f}",
            ]
        }
        st.dataframe(pd.DataFrame(data_pm), use_container_width=True, hide_index=True)
        st.caption(f"📖 Ref: {code['ref']}")

# ══════════════ TAB 2 — SECCIÓN & ESTRIBOS ══════════════
with tab2:
    st.subheader(_t("🧊 Visualización 3D y Detallado 2D", "🧊 3D Visualization & 2D Detailing"))
    # Generar 3D con Plotly
    fig3d = go.Figure()
    
    # Dibujar bloque de concreto (transparente)
    x_c = [-b/2, b/2, b/2, -b/2, -b/2, b/2, b/2, -b/2]
    y_c = [-h/2, -h/2, h/2, h/2, -h/2, -h/2, h/2, h/2]
    z_c = [0, 0, 0, 0, L_col, L_col, L_col, L_col]
    
    fig3d.add_trace(go.Mesh3d(x=x_c, y=y_c, z=z_c, alphahull=0, opacity=0.15, color='gray', name='Concreto'))
    
    # Dibujar varillas longitudinales con tamaño dinámico
    diam_reb_cm = rebar_diam / 10.0 # mm to cm
    line_width = max(4, diam_reb_cm * 3)
    
    rect_x = [-b/2 + d_prime, b/2 - d_prime]
    rect_y = [-h/2 + d_prime, h/2 - d_prime]
    
    # Func to draw a cylinder for rebar
    def add_rebar_3d(x_pos, y_pos, label_idx=0):
        # We only show legend for the first one to avoid clutter
        show_l = True if label_idx == 0 else False
        fig3d.add_trace(go.Scatter3d(x=[x_pos, x_pos], y=[y_pos, y_pos], z=[0, L_col], 
                                     mode='lines', line=dict(color='darkred', width=line_width),
                                     name=f'Long. {rebar_type}', showlegend=show_l))

    bar_count = 0
    # Inferior
    for i in range(num_filas_h):
        add_rebar_3d(rect_x[0] + i*(rect_x[1]-rect_x[0])/(num_filas_h-1) if num_filas_h>1 else 0, rect_y[0], bar_count)
        bar_count += 1
    # Superior
    for i in range(num_filas_h):
        add_rebar_3d(rect_x[0] + i*(rect_x[1]-rect_x[0])/(num_filas_h-1) if num_filas_h>1 else 0, rect_y[1], bar_count)
        bar_count += 1
    # Intermedias
    if num_capas_intermedias > 0:
        esp_y = (rect_y[1] - rect_y[0]) / (num_capas_intermedias + 1)
        for i in range(1, num_capas_intermedias + 1):
            add_rebar_3d(rect_x[0], rect_y[0] + i*esp_y, bar_count)
            bar_count += 1
            add_rebar_3d(rect_x[1], rect_y[0] + i*esp_y, bar_count)
            bar_count += 1
            
    # Estribos (Ties) - Distanciados cada 15cm por defecto ilustrativo
    tie_color = 'cornflowerblue'
    tie_width = max(2, (9.5/10.0) * 3) # Assuming 3/8" ties
    sep_ties = 15 
    # Recubrimiento externo al estribo (aprox d_prime - diam_reb_cm/2 - diam_estribo)
    # Por simplicidad geométrica usaremos el bounding de rect_x y rect_y expandido
    tt_x = [rect_x[0]-diam_reb_cm/2, rect_x[1]+diam_reb_cm/2, rect_x[1]+diam_reb_cm/2, rect_x[0]-diam_reb_cm/2, rect_x[0]-diam_reb_cm/2]
    tt_y = [rect_y[0]-diam_reb_cm/2, rect_y[0]-diam_reb_cm/2, rect_y[1]+diam_reb_cm/2, rect_y[1]+diam_reb_cm/2, rect_y[0]-diam_reb_cm/2]
    
    L_cm = int(L_col)
    for zt in range(15, L_cm, sep_ties):
        z_t_arr = [zt] * 5
        show_t_l = True if zt == 15 else False
        fig3d.add_trace(go.Scatter3d(x=tt_x, y=tt_y, z=z_t_arr, mode='lines', 
                                     line=dict(color=tie_color, width=tie_width), name='Estribo 3/8"', showlegend=show_t_l))

    fig3d.update_layout(scene=dict(aspectmode='data', 
                                   xaxis_title='b (cm)', yaxis_title='h (cm)', zaxis_title='L (cm)'),
                        margin=dict(l=0, r=0, b=0, t=0), height=450, dragmode='turntable')
    st.plotly_chart(fig3d, use_container_width=True)
    st.markdown("---")

    col_s1, col_s2 = st.columns([1, 1])

    with col_s1:
        st.subheader("Sección Transversal 2D")
        # ── Cross-section ──
        fig_sec, ax_s = plt.subplots(figsize=(4, max(3, 4 * h / b)))
        ax_s.set_aspect('equal')
        ax_s.set_facecolor('#1a1a2e')
        fig_sec.patch.set_facecolor('#1a1a2e')

        recub_cm = max(d_prime - rebar_diam / 20.0, 2.5)

        # Concreto
        ax_s.add_patch(patches.Rectangle((0, 0), b, h, linewidth=2,
            edgecolor='white', facecolor='#4a4a6a'))
        # Estribo
        ax_s.add_patch(patches.Rectangle(
            (recub_cm, recub_cm), b - 2*recub_cm, h - 2*recub_cm,
            linewidth=max(1, stirrup_diam/20), edgecolor='#00d4ff', facecolor='none', linestyle='--'))

        r_bar = rebar_diam / 20.0
        def _draw_row(y_pos, n_bars):
            xs = np.linspace(d_prime, b - d_prime, n_bars) if n_bars > 1 else [b/2]
            for x in xs:
                ax_s.add_patch(plt.Circle((x, y_pos), r_bar, color='#ff6b35', zorder=5))

        _draw_row(h - d_prime, num_filas_h)
        if num_capas_intermedias > 0:
            esp = (h - 2*d_prime) / (num_capas_intermedias + 1)
            for i in range(1, num_capas_intermedias + 1):
                y_int = d_prime + i * esp
                ax_s.add_patch(plt.Circle((d_prime, y_int), r_bar, color='#ff6b35', zorder=5))
                ax_s.add_patch(plt.Circle((b - d_prime, y_int), r_bar, color='#ff6b35', zorder=5))
        _draw_row(d_prime, num_filas_h)

        ax_s.annotate('', xy=(b, -1.5), xytext=(0, -1.5),
            arrowprops=dict(arrowstyle='<->', color='white', lw=1.2))
        ax_s.text(b/2, -2.5, f"b = {b:.0f} cm", ha='center', va='top', color='white', fontsize=7)
        ax_s.annotate('', xy=(-1.5, h), xytext=(-1.5, 0),
            arrowprops=dict(arrowstyle='<->', color='white', lw=1.2))
        ax_s.text(-2.5, h/2, f"h = {h:.0f} cm", ha='right', va='center', color='white', fontsize=7, rotation=90)
        ax_s.set_xlim(-5, b+3); ax_s.set_ylim(-5, h+3)
        ax_s.axis('off')
        ax_s.set_title(f"Sección transversal — {b:.0f}×{h:.0f} cm\n{n_barras_total} varillas Ø{rebar_diam:.0f}mm + estribo Ø{stirrup_diam:.0f}mm",
            color='white', fontsize=8)
        st.pyplot(fig_sec)

        # ── Elevation / Vertical diagram ──
        st.subheader("Alzado (Vista Vertical)")
        escala = min(1.0, 15.0 / (L_col / 10.0))  # scale column to reasonable height
        L_fig = L_col / 10.0 * escala  # cm → display units
        b_fig = b / 10.0 * escala

        fig_elev, ax_e = plt.subplots(figsize=(max(2.5, b_fig + 1.5), max(6, L_fig + 1.5)))
        ax_e.set_facecolor('#1a1a2e')
        fig_elev.patch.set_facecolor('#1a1a2e')

        # Column outline
        ax_e.add_patch(patches.Rectangle((0, 0), b_fig, L_fig, linewidth=1.5,
            edgecolor='white', facecolor='#4a4a6a'))

        # Bar lines (2 lines representing longitudinal steel)
        margin = (recub_cm / b * b_fig)
        ax_e.plot([margin, margin], [0, L_fig], color='#ff6b35', linewidth=1.5)
        ax_e.plot([b_fig - margin, b_fig - margin], [0, L_fig], color='#ff6b35', linewidth=1.5)

        # Draw stirrups along height
        def y_pos_to_fig(y_cm):
            return y_cm / L_col * L_fig

        ax_e.set_prop_cycle(None)
        stirrup_lw = 1.5

        if zona_especial:
            Lo_fig = Lo_conf / L_col * L_fig
            # Bottom confinement
            y = 0.0
            while y <= Lo_conf:
                yf = y_pos_to_fig(y)
                ax_e.plot([0, b_fig], [yf, yf], color='#00d4ff', linewidth=stirrup_lw)
                y += s_conf
            # Top confinement
            y = 0.0
            while y <= Lo_conf:
                yf = y_pos_to_fig(L_col - y)
                ax_e.plot([0, b_fig], [yf, yf], color='#00d4ff', linewidth=stirrup_lw)
                y += s_conf
            # Central zone (basic spacing)
            y = Lo_conf + s_basico
            while y < L_col - Lo_conf:
                yf = y_pos_to_fig(y)
                ax_e.plot([0, b_fig], [yf, yf], color='#7ec8e3', linewidth=stirrup_lw * 0.7)
                y += s_basico
            # Confinement zone markers
            ax_e.axhline(y=y_pos_to_fig(Lo_conf), color='yellow', linewidth=0.8, linestyle='--')
            ax_e.axhline(y=y_pos_to_fig(L_col - Lo_conf), color='yellow', linewidth=0.8, linestyle='--')
            ax_e.text(b_fig + 0.2, y_pos_to_fig(Lo_conf / 2),
                f"Lo={Lo_conf:.0f}cm\ns={s_conf:.0f}cm", color='yellow', fontsize=6, va='center')
            ax_e.text(b_fig + 0.2, y_pos_to_fig(L_col - Lo_conf / 2),
                f"Lo={Lo_conf:.0f}cm\ns={s_conf:.0f}cm", color='yellow', fontsize=6, va='center')
            ax_e.text(b_fig + 0.2, y_pos_to_fig(L_col / 2),
                f"s={s_basico:.0f}cm", color='#7ec8e3', fontsize=6, va='center')
        else:
            y = 0.0
            while y <= L_col:
                yf = y_pos_to_fig(y)
                ax_e.plot([0, b_fig], [yf, yf], color='#00d4ff', linewidth=stirrup_lw)
                y += s_basico
            ax_e.text(b_fig + 0.2, L_fig / 2,
                f"s={s_basico:.0f}cm\n(uniforme)", color='#00d4ff', fontsize=6, va='center')

        # Dimension arrows
        ax_e.annotate('', xy=(b_fig / 2, L_fig + 0.3), xytext=(b_fig / 2, 0),
            arrowprops=dict(arrowstyle='<->', color='white', lw=1.0))
        ax_e.text(b_fig / 2, L_fig / 2, f"L\n={L_col:.0f}\ncm",
            ha='center', va='center', color='white', fontsize=7,
            bbox=dict(facecolor='#4a4a6a', edgecolor='none', alpha=0.7))

        ax_e.set_xlim(-0.5, b_fig + 2.0)
        ax_e.set_ylim(-0.5, L_fig + 0.8)
        ax_e.axis('off')
        ax_e.set_title(f"Alzado — Distribución de Estribos\nL={L_col:.0f} cm  |  {n_estribos_total} estribos Ø{stirrup_diam:.0f}mm",
            color='white', fontsize=8)
        st.pyplot(fig_elev)


    with col_s2:
        st.subheader("Diseño de Estribos (Flejes)")
        st.markdown(f"**Estribo:** {stirrup_type} — Ø{stirrup_diam:.0f} mm  |  Ab = {stirrup_area:.3f} cm²")
        st.markdown(f"**Nivel Sísmico:** {nivel_sismico}")
        st.markdown("---")
        st.markdown(r"**Verificación Normativa Separación Máxima ($s_{max}$):**")
        st.latex(r"s \le \min(16d_b, 48d_t, b_{min})")
        
        data_estr = {
            "Parámetro": [
                "16 × dbl (varilla long.)",
                "48 × dt (estribo)",
                "Menor dim. de sección",
                "→ Separación básica (s)",
                "6 × dbl (zona confinada)",
                "min(b,h) / 4",
                "15 cm (límite)",
                "→ Separación confinada (s_conf)",
                "Longitud de confinamiento (Lo)",
                "Perímetro del estribo",
            ],
            "Valor [cm]": [
                f"{s1:.1f}",
                f"{s2:.1f}",
                f"{s3:.1f}",
                f"**{s_basico:.1f}**",
                f"{6 * rebar_diam / 10:.1f}",
                f"{min(b, h) / 4:.1f}",
                "15.0",
                f"**{s_conf:.1f}**" if zona_especial else "— (Zona ordinaria)",
                f"{Lo_conf:.1f}" if zona_especial else "— (no aplica)",
                f"{perim_estribo:.1f}",
            ],
        }
        st.dataframe(pd.DataFrame(data_estr), use_container_width=True, hide_index=True)

        if zona_especial:
            st.info(f"""
**Zona sísmica especial activa**
- {n_estribos_zona} estribos × 2 extremos = {n_estribos_zona_dos} estribos en zonas de confinamiento
- {n_estribos_centro} estribos en zona central
- **Total: {n_estribos_total} estribos**
""")
        else:
            st.info(f"**Zona ordinaria** — s = {s_basico:.1f} cm → **{n_estribos_total} estribos** en {L_col:.0f} cm")
        
        st.markdown("---")
        st.markdown("#### 💾 Exportar Plano (AutoCAD)")
        st.markdown("Genera el archivo `.dxf` a escala real con la geometría de la sección, estribo y varillas.")
        
        # Generar DXF
        doc_dxf = ezdxf.new('R2010')
        doc_dxf.units = ezdxf.units.CM
        msp = doc_dxf.modelspace()
        
        # Concreto (rectangulo 0,0 a b,h)
        msp.add_lwpolyline([(0,0), (b,0), (b,h), (0,h), (0,0)], dxfattribs={'color': 7, 'layer': 'CONCRETO'})
        # Estribo
        msp.add_lwpolyline([(recub_cm, recub_cm), (b-recub_cm, recub_cm), (b-recub_cm, h-recub_cm), (0+recub_cm, h-recub_cm), (recub_cm, recub_cm)], dxfattribs={'color': 4, 'layer': 'ESTRIBOS'})
        
        r_bar_cm = rebar_diam / 20.0
        # Varillas superior e inferior
        xs_sup_inf = np.linspace(d_prime, b - d_prime, num_filas_h) if num_filas_h > 1 else [b/2]
        for x in xs_sup_inf:
            msp.add_circle((x, h - d_prime), r_bar_cm, dxfattribs={'color': 1, 'layer': 'VARILLAS'})
            msp.add_circle((x, d_prime), r_bar_cm, dxfattribs={'color': 1, 'layer': 'VARILLAS'})
        # Intermedias
        if num_capas_intermedias > 0:
            esp = (h - 2*d_prime) / (num_capas_intermedias + 1)
            for i in range(1, num_capas_intermedias + 1):
                y_int = d_prime + i * esp
                msp.add_circle((d_prime, y_int), r_bar_cm, dxfattribs={'color': 1, 'layer': 'VARILLAS'})
                msp.add_circle((b - d_prime, y_int), r_bar_cm, dxfattribs={'color': 1, 'layer': 'VARILLAS'})
        
        out_stream = io.StringIO()
        doc_dxf.write(out_stream)
        dxf_str = out_stream.getvalue()
        
        st.download_button(
            label="Descargar Dibujo DXF (AutoCAD)",
            data=dxf_str,
            file_name=f"Seccion_Columna_{b:.0f}x{h:.0f}cm.dxf",
            mime="application/dxf",
            help="Columneador 3000 — Exporta el dibujo a escala para cualquier software CAD"
        )

# ══════════════ TAB 3 — CANTIDADES ══════════════
with tab3:
    st.subheader(f"📦 Cantidades de Materiales — Columna {b:.0f}×{h:.0f} cm, L={L_col:.0f} cm")
    st.markdown(f"*Norma: {norma_sel} | {nivel_sismico}*")

    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.metric("Concreto", f"{vol_concreto_m3:.4f} m³", help="b × h × L")
    col_c2.metric("Acero Total", f"{peso_total_acero_kg:.2f} kg", help="Long. + Estribos")
    col_c3.metric("Ratio Acero", f"{relacion_acero_kg_m3:.1f} kg/m³", help="Acero total / volumen concreto")

    st.markdown("---")
    st.markdown("#### Desglose Detallado")

    data_cant = {
        "Concepto": [
            "Dimensiones (b × h × L)",
            "Volumen de concreto",
            "—",
            f"Varillas longitudinales ({n_barras_total} × {rebar_type})",
            f"  Ast por unidad longitudinal",
            f"  Longitud total de barra",
            "  Peso unitario (7.85 g/cm³)",
            "  Peso acero longitudinal",
            "—",
            f"Estribos Ø{stirrup_diam:.0f}mm — {stirrup_type}",
            "  Número de estribos",
            "  Perímetro por estribo",
            "  Longitud total de estribos",
            "  Peso acero estribos",
            "—",
            "TOTAL ACERO",
            "Ratio acero / concreto",
        ],
        "Valor": [
            f"{b:.0f} × {h:.0f} × {L_col:.0f} cm",
            f"{vol_concreto_m3:.4f} m³  ({vol_concreto_m3 * 1000:.1f} litros)",
            "",
            f"{n_barras_total} barras",
            f"{Ast:.3f} cm²",
            f"{n_barras_total * L_col / 100:.2f} m  ({n_barras_total} × {L_col / 100:.2f} m)",
            f"7.85 g/cm³",
            f"{peso_acero_long_kg:.2f} kg",
            "",
            f"Tipo: {col_type}",
            f"{n_estribos_total} estribos",
            f"{perim_estribo:.1f} cm",
            f"{longitud_total_estribos_m:.2f} m",
            f"{peso_total_estribos_kg:.2f} kg",
            "",
            f"**{peso_total_acero_kg:.2f} kg**",
            f"**{relacion_acero_kg_m3:.1f} kg/m³**",
        ],
    }
    st.dataframe(pd.DataFrame(data_cant), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown(f"""
> **Notas:**
> - El volumen de concreto es el volumen bruto (sin descontar armadura).
> - El peso del acero incluye varillas longitudinales + estribos.
> - Los estribos incluyen dobladillos: +{6 * stirrup_diam / 10:.1f} cm por estribo.
> - Desarrollado con base en: **{code['ref']}**
""")

    # ══════════════ DOSIFICACIÓN DE MEZCLA ══════════════
    st.markdown("---")
    st.subheader("🧱 Dosificación de Mezcla de Concreto")
    st.markdown(f"Proporciones para **f'c = {fc:.2f} MPa** ({fc * 10.1972:.0f} kg/cm² ≈ {fc / 0.00689476:.0f} PSI) según ACI 211.1")

    # Selector de presentación de cemento
    bags_for_code = CEMENT_BAGS.get(norma_sel, CEMENT_BAGS["NSR-10 (Colombia)"])
    bag_labels = [b["label"] for b in bags_for_code]
    bag_sel_idx = st.selectbox(
        "Presentación del cemento:",
        range(len(bag_labels)),
        format_func=lambda i: bag_labels[i],
        key="bag_selector"
    )
    bag_kg = bags_for_code[bag_sel_idx]["kg"]
    st.info(f"**Peso del bulto seleccionado:** {bag_kg:.1f} kg")

    # Mezcla interpolada
    mix = get_mix_for_fc(fc)
    cem_m3   = mix["cem"]    # kg/m³
    agua_m3  = mix["agua"]   # kg/m³ = L/m³
    arena_m3 = mix["arena"]  # kg/m³
    grava_m3 = mix["grava"]  # kg/m³
    wc       = mix["wc"]

    # Bultos por m³
    bultos_por_m3 = cem_m3 / bag_kg

    # Densidades de áridos
    dens_arena = 1500  # kg/m³ suelto
    dens_grava = 1600  # kg/m³ suelto

    # Litros de cada material por m³
    litros_arena_m3 = arena_m3 / dens_arena * 1000
    litros_grava_m3 = grava_m3 / dens_grava * 1000
    litros_agua_m3  = agua_m3   # agua: 1 L = 1 kg

    # Por BULTO de cemento
    factor = 1.0 / bultos_por_m3
    arena_por_bulto = arena_m3 * factor
    grava_por_bulto = grava_m3 * factor
    agua_por_bulto  = agua_m3  * factor

    # En cuñetes de 20 L
    cunetes_arena = litros_arena_m3 * factor / 20.0
    cunetes_grava = litros_grava_m3 * factor / 20.0
    cunetes_agua  = agua_por_bulto / 20.0

    # Totales para el volumen de la columna
    bultos_col = bultos_por_m3 * vol_concreto_m3
    arena_col  = arena_m3 * vol_concreto_m3
    grava_col  = grava_m3 * vol_concreto_m3
    agua_col   = agua_m3  * vol_concreto_m3

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("#### Proporciones por m³ de concreto")
        data_m3 = {
            "Material": [
                f"Cemento (f'c = {fc:.1f} MPa)",
                "Agua de mezclado",
                "Arena (agregado fino)",
                "Grava / Piedra (agregado grueso)",
                "Relación agua/cemento (w/c)",
                "Rendimiento (aprox.)",
            ],
            "kg/m³": [
                f"{cem_m3:.0f} kg",
                f"{agua_m3:.0f} L",
                f"{arena_m3:.0f} kg",
                f"{grava_m3:.0f} kg",
                f"{wc:.2f}",
                "≈ 1 m³",
            ],
            "Bultos o cuñetes / m³": [
                f"{bultos_por_m3:.2f} bultos de {bag_kg:.0f} kg",
                f"{litros_agua_m3 / 20:.1f} cuñetes (20L)",
                f"{litros_arena_m3 / 20:.1f} cuñetes (20L)",
                f"{litros_grava_m3 / 20:.1f} cuñetes (20L)",
                "—",
                "—",
            ],
        }
        st.dataframe(pd.DataFrame(data_m3), use_container_width=True, hide_index=True)

    with col_m2:
        st.markdown(f"#### Por bulto de {bag_kg:.0f} kg de cemento")
        st.markdown("*(dosificación de campo, cuñetes de 20 L)*")
        data_bulto = {
            "Material": [
                f"🧱 Cemento",
                f"💧 Agua",
                f"🟡 Arena (fino)",
                f"🔵 Grava (grueso)",
            ],
            "Cantidad": [
                f"1 bulto = {bag_kg:.0f} kg",
                f"{agua_por_bulto:.1f} L  →  **{cunetes_agua:.2f} cuñetes**",
                f"{arena_por_bulto:.1f} kg  →  **{cunetes_arena:.2f} cuñetes**",
                f"{grava_por_bulto:.1f} kg  →  **{cunetes_grava:.2f} cuñetes**",
            ],
        }
        st.dataframe(pd.DataFrame(data_bulto), use_container_width=True, hide_index=True)

        st.success(f"""
**Dosificación resumida (por bulto {bag_kg:.0f} kg):**
🧱 1 bulto  +  💧 {cunetes_agua:.1f} cuñetes agua  +  🟡 {cunetes_arena:.1f} cuñetes arena  +  🔵 {cunetes_grava:.1f} cuñetes grava
""")

    st.markdown(f"#### Totales para la columna ({vol_concreto_m3:.4f} m³)")
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    col_t1.metric("Cemento", f"{bultos_col:.1f} bultos", f"{bultos_col * bag_kg:.0f} kg")
    col_t2.metric("Agua", f"{agua_col:.0f} L", f"{agua_col / 20:.1f} cuñetes")
    col_t3.metric("Arena", f"{arena_col:.0f} kg", f"{arena_col / dens_arena * 1000 / 20:.1f} cuñetes")
    col_t4.metric("Grava", f"{grava_col:.0f} kg", f"{grava_col / dens_grava * 1000 / 20:.1f} cuñetes")

    st.caption("""
⚠️ Proporciones según ACI 211.1. Para uso en campo verifique con ensayos de laboratorio.
Arena: densidad suelta ≈ 1500 kg/m³ · Grava: densidad suelta ≈ 1600 kg/m³ · Cuñete = 20 litros.
""")

    # ══════════════ APU (PRESUPUESTO) ══════════════
    if "apu_config" in st.session_state:
        st.markdown("---")
        st.markdown("### 💰 Presupuesto Estimado de Materiales (APU)")
        apu = st.session_state.apu_config
        mon = apu["moneda"]
        
        costo_cemento = bultos_col * apu["cemento"]
        costo_acero   = peso_total_acero_kg * apu["acero"]
        vol_arena_m3  = arena_col / dens_arena
        vol_grava_m3  = grava_col / dens_grava
        costo_arena   = vol_arena_m3 * apu["arena"]
        costo_grava   = vol_grava_m3 * apu["grava"]
        
        total_mat = costo_cemento + costo_acero + costo_arena + costo_grava
        
        # Mano de Obra (Rendimientos tipicos: Acero=0.04 d/kg, Concreto=0.4 d/m3)
        dias_acero = peso_total_acero_kg * 0.04
        dias_concreto = vol_concreto_m3 * 0.4
        total_dias_mo = dias_acero + dias_concreto
        costo_mo = total_dias_mo * apu.get("costo_dia_mo", 69333.33)
        
        # Costos Indirectos
        costo_directo = total_mat + costo_mo
        herramienta = costo_mo * apu.get("pct_herramienta", 0.05)
        aiu = costo_directo * apu.get("pct_aui", 0.30)
        utilidad = costo_directo * apu.get("pct_util", 0.05)
        iva = utilidad * apu.get("iva", 0.19)
        
        total_proyecto = costo_directo + herramienta + aiu + iva
        
        data_apu = {
            "Item": [
                "Cemento (bultos)", "Acero (kg)", "Arena (m³)", "Grava (m³)", 
                "Mano de Obra (días)", "Herramienta Menor", "A.I.U.", "IVA sobre Utilidad", "TOTAL PRESUPUESTO"
            ],
            "Cantidad": [
                f"{bultos_col:.1f}", f"{peso_total_acero_kg:.1f}", f"{vol_arena_m3:.2f}", f"{vol_grava_m3:.2f}", 
                f"{total_dias_mo:.2f}", f"{apu.get('pct_herramienta', 0.05)*100:.1f}% MO", 
                f"{apu.get('pct_aui', 0.30)*100:.1f}% CD", f"{apu.get('iva', 0.19)*100:.1f}% Util.", ""
            ],
            f"Precio Unit. [{mon}]": [
                f"{apu['cemento']:,.2f}", f"{apu['acero']:,.2f}", f"{apu['arena']:,.2f}", f"{apu['grava']:,.2f}", 
                f"{apu.get('costo_dia_mo', 69333.33):,.2f}", "-", "-", "-", ""
            ],
            f"Subtotal [{mon}]": [
                f"{costo_cemento:,.2f}", f"{costo_acero:,.2f}", f"{costo_arena:,.2f}", f"{costo_grava:,.2f}", 
                f"{costo_mo:,.2f}", f"{herramienta:,.2f}", f"{aiu:,.2f}", f"{iva:,.2f}", f"**{total_proyecto:,.2f}**"
            ]
        }
        df_apu = pd.DataFrame(data_apu)
        st.dataframe(df_apu, use_container_width=True, hide_index=True)
        
        # Exportar Excel Formula - APU
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            # Dataframe limpio sin asteriscos para Excel
            df_export = pd.DataFrame({
                "Item": ["Cemento (bultos)", "Acero (kg)", "Arena (m3)", "Grava (m3)", "Mano de Obra (dias)"],
                "Cantidad": [bultos_col, peso_total_acero_kg, vol_arena_m3, vol_grava_m3, total_dias_mo],
                "Unidad": [apu['cemento'], apu['acero'], apu['arena'], apu['grava'], apu.get('costo_dia_mo', 69333.33)]
            })
            df_export["Subtotal"] = df_export["Cantidad"] * df_export["Unidad"]
            df_export.to_excel(writer, index=False, sheet_name='APU')
            
            workbook = writer.book
            worksheet = writer.sheets['APU']
            money_fmt = workbook.add_format({'num_format': '#,##0.00'})
            bold = workbook.add_format({'bold': True})
            
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:D', 15, money_fmt)
            
            # Formatear filas extra
            row = len(df_export) + 1
            worksheet.write(row, 0, "Costo Directo (CD)", bold)
            worksheet.write_formula(row, 3, f'=SUM(D2:D{row})', money_fmt)
            
            row += 1
            worksheet.write(row, 0, "Herramienta Menor", bold)
            worksheet.write_formula(row, 3, f'=D6*{apu.get("pct_herramienta", 0.05)}', money_fmt)
            
            row += 1
            worksheet.write(row, 0, "A.I.U", bold)
            worksheet.write_formula(row, 3, f'=D{row-1}*{apu.get("pct_aui", 0.30)}', money_fmt)
            
            row += 1
            worksheet.write(row, 0, "IVA s/ Utilidad", bold)
            worksheet.write_formula(row, 3, f'=D{row-1}*{apu.get("pct_util", 0.05)/apu.get("pct_aui", 0.30)}*{apu.get("iva", 0.19)}', money_fmt)
            
            row += 1
            worksheet.write(row, 0, "TOTAL PRESUPUESTO", bold)
            worksheet.write_formula(row, 3, f'=D{row-3}+D{row-2}+D{row-1}+D{row}', money_fmt)
            
        output_excel.seek(0)
        st.download_button(label="📥 Descargar Presupuesto Excel (.xlsx)", data=output_excel, file_name=f"APU_Columna_{b:.0f}x{h:.0f}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        st.info(f"💡 Los precios unitarios provienen de la configuración en la pestaña **APU Mercado**. Moneda: {mon}.")
    else:
        st.markdown("---")
        st.info("💡 **Presupuesto APU disponible:** Ve a la herramienta 'APU Mercado' en la barra lateral para configurar moneda y extraer precios actualizados de Cemento y Acero en tu país.")

    st.markdown("---")
    st.markdown("#### 📄 Generar Memoria de Cálculo (DOCX)")

    
    # Generar docx
    doc_word = Document()
    doc_word.add_heading(f"Memoria de Cálculo — Columna {b:.0f}x{h:.0f} cm", 0)
    doc_word.add_paragraph(f"Norma Utilizada: {norma_sel}")
    doc_word.add_paragraph(f"Nivel Sísmico: {nivel_sismico}")
    
    doc_word.add_heading("1. Materiales Geometría", level=1)
    doc_word.add_paragraph(f"f'c = {fc:.1f} MPa\nfy = {fy:.0f} MPa\nBase: {b:.0f} cm\nAltura: {h:.0f} cm\nLongitud: {L_col:.0f} cm")
    
    doc_word.add_heading("2. Refuerzo", level=1)
    doc_word.add_paragraph(f"Varillas longitudinales: {n_barras_total} varillas tipo {rebar_type} ({Ast:.2f} cm²)\nCuantía logitudinal ρ: {cuantia:.2f}%\nEstribos: {stirrup_type} ({n_estribos_total} unidades)\nEspaciamiento: {s_usar:.1f} cm")
    
    doc_word.add_heading("3. Resultados de Diseño (Puntos Clave P-M)", level=1)
    doc_word.add_paragraph(f"Capacidad Axial Máx Pn,máx: {Pn_max:.1f} kN\nResistencia de Diseño φPn,máx: {phi_c_max * Pn_max:.1f} kN")
    
    doc_word.add_heading("4. Cantidades de Obra", level=1)
    doc_word.add_paragraph(f"Concreto: {vol_concreto_m3:.4f} m³\nAcero total: {peso_total_acero_kg:.1f} kg ({relacion_acero_kg_m3:.1f} kg/m³)\nCemento: {bultos_col:.1f} bultos de {bag_kg:.0f} kg")
    
    f = io.BytesIO()
    doc_word.save(f)
    f.seek(0)
    
    st.download_button(
        label="Descargar Memoria DOCX (Word)",
        data=f,
        file_name=f"Memoria_Columna_{b:.0f}x{h:.0f}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

