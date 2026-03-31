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
from docx.enum.text import WD_ALIGN_PARAGRAPH
import plotly.graph_objects as go
import json
import datetime
import os
from pathlib import Path
import qrcode
from PIL import Image
import tempfile

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en):
    return en if lang == "English" else es
# ─────────────────────────────────────────────

st.set_page_config(page_title=_t("Diagramas de Interacción Biaxial", "Biaxial Interaction Diagrams"), layout="wide")

# ─────────────────────────────────────────────
# FIX BUG #4: Manejo seguro de BASE_DIR para Streamlit Cloud
# ─────────────────────────────────────────────
try:
    BASE_DIR = Path(__file__).parent.parent
except NameError:
    BASE_DIR = Path(os.getcwd())

header_img_path = BASE_DIR / "assets" / "columnas_pm_header_1773261175144.png"
if header_img_path.exists():
    st.image(str(header_img_path), use_container_width=False, width=700)
else:
    st.image("https://via.placeholder.com/700x100?text=Columnas+PM+Biaxial", width=700)

st.title(_t("🏗️ Diagrama de Interacción P–M (Biaxial) y Diseño de Estribos", "🏗️ P-M (Biaxial) Interaction Diagram & Tie Design"))
st.markdown(_t(
    "Generador interactivo de capacidad a flexocompresión **biaxial** para **Columnas Cuadradas, Rectangulares y Circulares**.",
    "Interactive **biaxial** flexure-compression capacity generator for **Square, Rectangular and Circular Columns**."
))

with st.expander("📺 ¿Cómo usar esta herramienta?"):
    st.markdown("""
    **Modo de Uso:**
    1. **📍 Sidebar:** Selecciona Norma, nivel sísmico, f'c, fy, geometría (cuadrada, rectangular o circular)
    2. **🏗️ Armadura:** Define varillas longitudinales y estribos (o espiral)
    3. **🚦 Solicitaciones:** Ingresa Momentos (Mux, Muy) y Carga Axial (Pu)
    4. **📊 Resultados:** Diagrama P-M biaxial 3D + verificación Bresler
    5. **📦 Exportar:** Memoria DOCX completa, DXF con rótulo ICONTEC, Excel, etc.
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
# FUNCIONES DE DIBUJO PARA FIGURADO
# ─────────────────────────────────────────────
_MM_TO_BAR = {
    6.0:  "#2 (1/4\")",  6.35: "#2 (1/4\")",
    8.0:  "#2.5 (5/16\")",
    9.53: "#3 (3/8\")",  10.0: "#3 (3/8\")",
    12.0: "#4 (1/2\")",  12.70: "#4 (1/2\")",
    14.0: "#4.5 (9/16\")",
    15.88: "#5 (5/8\")", 16.0: "#5 (5/8\")",
    18.0: "#5.7 (11/16\")",
    19.05: "#6 (3/4\")", 20.0: "#6 (3/4\")",
    22.0: "#7 (7/8\")",  22.23: "#7 (7/8\")",
    25.0: "#8 (1\")",    25.40: "#8 (1\")",
    28.0: "#9 (1 1/8\")",28.65: "#9 (1 1/8\")",
    32.0: "#10 (1 1/4\")",32.26: "#10 (1 1/4\")",
}

def _bar_label(diam_mm):
    best = min(_MM_TO_BAR.keys(), key=lambda k: abs(k - diam_mm))
    if abs(best - diam_mm) <= 2.0:
        return f"{_MM_TO_BAR[best]}  Ø{diam_mm:.1f} mm"
    return f"Ø{diam_mm:.1f} mm"

def draw_longitudinal_bar(total_len_cm, straight_len_cm, hook_len_cm, bar_diam_mm, bar_name=None):
    label = bar_name if bar_name else _bar_label(bar_diam_mm)
    fig, ax = plt.subplots(figsize=(max(6, total_len_cm/20), 2))
    ax.set_aspect('equal')
    ax.plot([0, straight_len_cm], [0, 0], 'k-', linewidth=2)
    ax.plot([0, 0], [0, hook_len_cm], 'k-', linewidth=2)
    ax.plot([straight_len_cm, straight_len_cm], [0, -hook_len_cm], 'k-', linewidth=2)
    ax.annotate(f"{straight_len_cm:.0f} cm", xy=(straight_len_cm/2, 0.3), ha='center', fontsize=8)
    ax.annotate(f"Gancho 12db = {hook_len_cm:.0f} cm", xy=(0, hook_len_cm/2), ha='right', fontsize=8)
    ax.annotate(f"Gancho 12db", xy=(straight_len_cm, -hook_len_cm/2), ha='left', fontsize=8)
    ax.set_xlim(-hook_len_cm*0.2, straight_len_cm + hook_len_cm*0.2)
    ax.set_ylim(-hook_len_cm*1.2, hook_len_cm*1.2)
    ax.axis('off')
    ax.set_title(f"Varilla L1 — {label} — Longitud total {total_len_cm:.0f} cm", fontsize=9, fontweight='bold')
    return fig

def draw_stirrup(b_cm, h_cm, hook_len_cm, bar_diam_mm, bar_name=None):
    import math as _math
    label = bar_name if bar_name else _bar_label(bar_diam_mm)
    fig, ax = plt.subplots(figsize=(max(5, b_cm/12), max(4, h_cm/12)))
    ax.set_aspect('equal')
    x0, y0 = 0, 0
    ax.plot([x0, x0+b_cm], [y0, y0], 'k-', linewidth=2.5)
    ax.plot([x0+b_cm, x0+b_cm], [y0, y0+h_cm], 'k-', linewidth=2.5)
    ax.plot([x0+b_cm, x0], [y0+h_cm, y0+h_cm], 'k-', linewidth=2.5)
    ax.plot([x0, x0], [y0+h_cm, y0], 'k-', linewidth=2.5)
    angle_rad = _math.radians(45)
    vis_hook = min(hook_len_cm, b_cm/4.0, h_cm/4.0)
    hx = vis_hook * _math.cos(angle_rad)
    hy = -vis_hook * _math.sin(angle_rad)
    ax.plot([x0, x0 + hx], [y0+h_cm, y0+h_cm + hy], 'k-', linewidth=2.5)
    ax.plot([x0+b_cm, x0+b_cm - hx], [y0+h_cm, y0+h_cm + hy], 'k--', linewidth=1.5, alpha=0.5)
    ax.annotate(f"{b_cm:.0f} cm", xy=(b_cm/2, y0-0.8), ha='center', fontsize=9, fontweight='bold')
    ax.annotate(f"{h_cm:.0f} cm", xy=(x0-0.8, h_cm/2), ha='right', va='center', fontsize=9, fontweight='bold')
    ax.annotate(f"Gancho 135°\n6d_e = {6*bar_diam_mm/10:.1f} cm",
                xy=(x0 + hx + 0.2, y0+h_cm + hy - 0.2), fontsize=7.5, color='darkred',
                va='top', ha='left')
    ax.set_xlim(x0 - hook_len_cm*0.3, b_cm + hook_len_cm*0.6)
    ax.set_ylim(y0 - hook_len_cm*0.5, h_cm + hook_len_cm*0.9)
    ax.axis('off')
    ax.set_title(f"Estribo E1 — {label} — Perímetro {2*(b_cm+h_cm):.0f} cm", fontsize=9, fontweight='bold')
    return fig

def draw_crosstie(len_cm, hook_len_cm, bar_diam_mm, bar_name=None):
    label = bar_name if bar_name else _bar_label(bar_diam_mm)
    fig, ax = plt.subplots(figsize=(max(6, len_cm/15), 2))
    ax.set_aspect('equal')
    ax.plot([0, len_cm], [0, 0], 'k-', linewidth=2)
    ax.plot([0, -hook_len_cm*0.7], [0, -hook_len_cm*0.7], 'k-', linewidth=2)
    ax.plot([len_cm, len_cm + hook_len_cm*0.7], [0, -hook_len_cm*0.7], 'k-', linewidth=2)
    ax.annotate(f"{len_cm:.0f} cm", xy=(len_cm/2, 0.3), ha='center', fontsize=8)
    ax.annotate(f"Gancho 135°", xy=(0, -hook_len_cm*0.5), ha='right', fontsize=8)
    ax.annotate(f"Gancho 135°", xy=(len_cm, -hook_len_cm*0.5), ha='left', fontsize=8)
    ax.set_xlim(-hook_len_cm*1.2, len_cm + hook_len_cm*1.2)
    ax.set_ylim(-hook_len_cm*1.5, hook_len_cm*0.5)
    ax.axis('off')
    ax.set_title(f"Crosstie C1 — {label} — Longitud {len_cm:.0f} cm", fontsize=9, fontweight='bold')
    return fig

def draw_spiral(D_cm, paso_cm, bar_diam_mm, bar_name=None):
    """Dibujo esquemático de espiral para columnas circulares"""
    label = bar_name if bar_name else _bar_label(bar_diam_mm)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_aspect('equal')
    circle = plt.Circle((0, 0), D_cm/2, fill=False, edgecolor='black', linewidth=2)
    ax.add_patch(circle)
    theta = np.linspace(0, 4*np.pi, 200)
    r = D_cm/2 - bar_diam_mm/10
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    ax.plot(x, y, 'k-', linewidth=1.5)
    ax.annotate(f"Espiral {label}", xy=(0, D_cm/2 + 2), ha='center', fontsize=9)
    ax.annotate(f"Paso = {paso_cm:.1f} cm", xy=(0, -D_cm/2 - 3), ha='center', fontsize=8)
    ax.set_xlim(-D_cm/2 - 5, D_cm/2 + 5)
    ax.set_ylim(-D_cm/2 - 8, D_cm/2 + 5)
    ax.axis('off')
    ax.set_title(f"Espiral — {label}", fontsize=9, fontweight='bold')
    return fig

# ─────────────────────────────────────────────
# PARÁMETROS POR NORMA (con límites por nivel sísmico)
# ─────────────────────────────────────────────
CODES = {
    "NSR-10 (Colombia)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 6.0, "rho_max_dmo": 4.0, "rho_max_des": 4.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["DMI — Disipación Mínima", "DMO — Disipación Moderada", "DES — Disipación Especial"],
        "ref": "NSR-10 Título C",
    },
    "ACI 318-25 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary", "IMF — Intermediate", "SMF — Special"],
        "ref": "ACI 318-25",
    },
    "ACI 318-19 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary", "IMF — Intermediate", "SMF — Special"],
        "ref": "ACI 318-19",
    },
    "ACI 318-14 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary", "IMF — Intermediate", "SMF — Special"],
        "ref": "ACI 318-14",
    },
    "NEC-SE-HM (Ecuador)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["GS — Grado Reducido", "GM — Grado Moderado", "GA — Grado Alto"],
        "ref": "NEC-SE-HM",
    },
    "E.060 (Perú)": {
        "phi_tied": 0.70, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 6.0, "rho_max_dmo": 5.0, "rho_max_des": 5.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["PO — Pórtico Ordinario", "PM — Pórtico Moderado", "PE — Pórtico Especial"],
        "ref": "E.060 Perú",
    },
    "NTC-EM (México)": {
        "phi_tied": 0.70, "phi_spiral": 0.80, "phi_tension": 0.85,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 6.0, "rho_max_dmo": 5.0, "rho_max_des": 5.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["MDL — Ductilidad Limitada", "MROD — Ductilidad Ordinaria", "MRLE — Ductilidad Alta"],
        "ref": "NTC-EM México",
    },
    "COVENIN 1753-2006 (Venezuela)": {
        "phi_tied": 0.70, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 6.0, "rho_max_dmo": 5.0, "rho_max_des": 5.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["PO — Pórtico Ordinario", "PM — Pórtico Moderado", "PE — Pórtico Especial"],
        "ref": "COVENIN 1753",
    },
    "NB 1225001-2020 (Bolivia)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["DO — Diseño Ordinario", "DM — Ductilidad Moderada", "DE — Diseño Especial"],
        "ref": "NB 1225001",
    },
    "CIRSOC 201-2025 (Argentina)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["GE — Grado Estándar", "GM — Ductilidad Moderada", "GA — Ductilidad Alta"],
        "ref": "CIRSOC 201",
    },
}

# ─────────────────────────────────────────────
# PRESENTACIONES DE CEMENTO POR PAÍS
# ─────────────────────────────────────────────
CEMENT_BAGS = {
    "NSR-10 (Colombia)": [{"label": "Cemento gris (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "ACI 318-25 (EE.UU.)": [{"label": "Type I/II (94 lb / 42.6 kg)", "kg": 42.6}, {"label": "Type III (47 lb / 21.3 kg)", "kg": 21.3}],
    "ACI 318-19 (EE.UU.)": [{"label": "Type I/II (94 lb / 42.6 kg)", "kg": 42.6}, {"label": "Type III (47 lb / 21.3 kg)", "kg": 21.3}],
    "ACI 318-14 (EE.UU.)": [{"label": "Type I/II (94 lb / 42.6 kg)", "kg": 42.6}, {"label": "Type III (47 lb / 21.3 kg)", "kg": 21.3}],
    "NEC-SE-HM (Ecuador)": [{"label": "Cemento Holcim (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "E.060 (Perú)": [{"label": "Cemento Andino (42.5 kg)", "kg": 42.5}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "NTC-EM (México)": [{"label": "Cemento Cemex (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "COVENIN 1753-2006 (Venezuela)": [{"label": "Cemento (42.5 kg)", "kg": 42.5}],
    "NB 1225001-2020 (Bolivia)": [{"label": "Cemento (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "CIRSOC 201-2025 (Argentina)": [{"label": "Cemento (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
}

# ─────────────────────────────────────────────
# TABLA DE DOSIFICACIÓN ACI 211
# ─────────────────────────────────────────────
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
    if fc_mpa <= MIX_DESIGNS[0]["fc_mpa"]: return MIX_DESIGNS[0]
    if fc_mpa >= MIX_DESIGNS[-1]["fc_mpa"]: return MIX_DESIGNS[-1]
    for i in range(len(MIX_DESIGNS)-1):
        lo, hi = MIX_DESIGNS[i], MIX_DESIGNS[i+1]
        if lo["fc_mpa"] <= fc_mpa <= hi["fc_mpa"]:
            t = (fc_mpa - lo["fc_mpa"]) / (hi["fc_mpa"] - lo["fc_mpa"])
            return {k: lo[k] + t*(hi[k]-lo[k]) for k in ("cem", "agua", "arena", "grava", "wc")}
    return MIX_DESIGNS[-1]

def get_beta1(fc):
    if fc <= 28: return 0.85
    return max(0.85 - 0.05*(fc-28)/7.0, 0.65)

def get_development_length(db_mm, fy, fc, lambda_=1.0, psi_t=1.0, psi_e=1.0, psi_s=1.0, psi_g=1.0, cb_ktr=2.5):
    if db_mm <= 0: return 0
    ld = (3/40) * (fy / (lambda_ * math.sqrt(fc))) * (psi_t * psi_e * psi_s * psi_g / cb_ktr) * db_mm
    return max(ld, 300)

# ─────────────────────────────────────────────
# FUNCIONES PARA CÁLCULO DE CAPACIDAD UNIAXIAL
# ─────────────────────────────────────────────
def compute_uniaxial_capacity(b, h, d_prime, layers, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza):
    eps_cu = 0.003
    eps_y = fy / Es
    beta_1 = get_beta1(fc)
    
    Ag = b * h
    Ast = sum([layer['As'] for layer in layers])
    Po_kN = (0.85 * fc * (Ag * 100 - Ast * 100) + fy * Ast * 100) / 1000.0
    
    c_vals = np.concatenate([np.linspace(1e-5, h, 120), np.linspace(h, h * 12, 60)])
    P_n_list = []; M_n_list = []; phi_P_n_list = []; phi_M_n_list = []
    eps_t_vals = []
    
    b_mm = b * 10
    h_mm = h * 10
    
    for c_cm in c_vals:
        c_mm = c_cm * 10
        a_mm = min(beta_1 * c_mm, h_mm)
        Cc = 0.85 * fc * a_mm * b_mm
        Mc = Cc * (h_mm / 2.0 - a_mm / 2.0)
        
        Ps = 0.0; Ms = 0.0; eps_t = 0.0
        for layer in layers:
            d_i_mm = layer['d'] * 10
            As_i = layer['As'] * 100
            eps_s = eps_cu * (c_mm - d_i_mm) / c_mm
            if d_i_mm >= max(l['d'] * 10 for l in layers):
                eps_t = eps_s
            fs = max(-fy, min(fy, Es * eps_s))
            if a_mm > d_i_mm and fs > 0:
                fs -= 0.85 * fc
            Ps += As_i * fs
            Ms += As_i * fs * (h_mm / 2.0 - d_i_mm)
        
        Pn = (Cc + Ps) / 1000.0
        Mn = abs((Mc + Ms) / 1_000_000.0)
        eps_t_tens = -eps_t
        
        if eps_t_tens <= eps_y:
            phi = phi_c_max
        elif eps_t_tens >= eps_full:
            phi = phi_tension
        else:
            phi = phi_c_max + (phi_tension - phi_c_max) * (eps_t_tens - eps_y) / (eps_full - eps_y)
        
        Pn_max_val = p_max_factor * Po_kN
        phi_Pn_max_val = phi_c_max * Pn_max_val
        
        Pn = min(Pn, Pn_max_val)
        phi_Pn = min(phi * Pn, phi_Pn_max_val)
        phi_Mn = phi * Mn
        
        P_n_list.append(Pn)
        M_n_list.append(Mn)
        phi_P_n_list.append(phi_Pn)
        phi_M_n_list.append(phi_Mn)
        eps_t_vals.append(eps_t_tens)
    
    c_balance = None
    P_balance = None
    M_balance = None
    for i, eps in enumerate(eps_t_vals):
        if abs(eps - eps_y) < 0.0001 or (i > 0 and eps_t_vals[i-1] <= eps_y <= eps):
            idx = i if abs(eps - eps_y) < 0.0001 else i-1
            c_balance = c_vals[idx]
            P_balance = P_n_list[idx] * factor_fuerza
            M_balance = M_n_list[idx] * factor_fuerza
            break
    
    return {
        'M_n': np.array(M_n_list) * factor_fuerza,
        'P_n': np.array(P_n_list) * factor_fuerza,
        'phi_M_n': np.array(phi_M_n_list) * factor_fuerza,
        'phi_P_n': np.array(phi_P_n_list) * factor_fuerza,
        'Po': Po_kN * factor_fuerza,
        'Pn_max': p_max_factor * Po_kN * factor_fuerza,
        'phi_Pn_max': phi_c_max * p_max_factor * Po_kN * factor_fuerza,
        'c_balance': c_balance,
        'P_balance': P_balance,
        'M_balance': M_balance,
    }

def compute_uniaxial_capacity_circular(D, d_prime, layers, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza):
    """Para sección circular"""
    eps_cu = 0.003
    eps_y = fy / Es
    beta_1 = get_beta1(fc)
    
    r = D / 2
    Ag = math.pi * r**2
    Ast = sum([layer['As'] for layer in layers])
    Po_kN = (0.85 * fc * (Ag * 100 - Ast * 100) + fy * Ast * 100) / 1000.0
    
    c_vals = np.concatenate([np.linspace(1e-5, D, 120), np.linspace(D, D * 12, 60)])
    P_n_list = []; M_n_list = []; phi_P_n_list = []; phi_M_n_list = []
    eps_t_vals = []
    
    for c_cm in c_vals:
        c_mm = c_cm * 10
        if c_mm >= D * 10:
            a_mm = D * 10
        else:
            a_mm = beta_1 * c_mm
        a_cm = a_mm / 10
        if a_cm >= D:
            Ac_comp = Ag
        else:
            h_seg = a_cm
            Ac_comp = r**2 * math.acos((r - h_seg)/r) - (r - h_seg) * math.sqrt(2*r*h_seg - h_seg**2)
        
        Cc = 0.85 * fc * Ac_comp * 100
        if a_cm >= D:
            y_cent = r
        else:
            y_cent = (4*r * math.sin((math.acos((r - a_cm)/r))/2)**3) / (3*(math.acos((r - a_cm)/r) - math.sin(math.acos((r - a_cm)/r))*math.cos(math.acos((r - a_cm)/r))))
        Mc = Cc * (r - y_cent) / 10
        
        Ps = 0.0; Ms = 0.0; eps_t = 0.0
        for layer in layers:
            d_i_mm = layer['d'] * 10
            As_i = layer['As'] * 100
            eps_s = eps_cu * (c_mm - d_i_mm) / c_mm
            if d_i_mm >= max(l['d'] * 10 for l in layers):
                eps_t = eps_s
            fs = max(-fy, min(fy, Es * eps_s))
            Ps += As_i * fs
            Ms += As_i * fs * (r - d_i_mm/10) / 10
        
        Pn = (Cc + Ps) / 1000.0
        Mn = abs((Mc + Ms) / 1000.0)
        eps_t_tens = -eps_t
        
        if eps_t_tens <= eps_y:
            phi = phi_c_max
        elif eps_t_tens >= eps_full:
            phi = phi_tension
        else:
            phi = phi_c_max + (phi_tension - phi_c_max) * (eps_t_tens - eps_y) / (eps_full - eps_y)
        
        Pn_max_val = p_max_factor * Po_kN
        phi_Pn_max_val = phi_c_max * Pn_max_val
        
        Pn = min(Pn, Pn_max_val)
        phi_Pn = min(phi * Pn, phi_Pn_max_val)
        phi_Mn = phi * Mn
        
        P_n_list.append(Pn)
        M_n_list.append(Mn)
        phi_P_n_list.append(phi_Pn)
        phi_M_n_list.append(phi_Mn)
        eps_t_vals.append(eps_t_tens)
    
    c_balance = None
    P_balance = None
    M_balance = None
    for i, eps in enumerate(eps_t_vals):
        if abs(eps - eps_y) < 0.0001 or (i > 0 and eps_t_vals[i-1] <= eps_y <= eps):
            idx = i if abs(eps - eps_y) < 0.0001 else i-1
            c_balance = c_vals[idx]
            P_balance = P_n_list[idx] * factor_fuerza
            M_balance = M_n_list[idx] * factor_fuerza
            break
    
    return {
        'M_n': np.array(M_n_list) * factor_fuerza,
        'P_n': np.array(P_n_list) * factor_fuerza,
        'phi_M_n': np.array(phi_M_n_list) * factor_fuerza,
        'phi_P_n': np.array(phi_P_n_list) * factor_fuerza,
        'Po': Po_kN * factor_fuerza,
        'Pn_max': p_max_factor * Po_kN * factor_fuerza,
        'phi_Pn_max': phi_c_max * p_max_factor * Po_kN * factor_fuerza,
        'c_balance': c_balance,
        'P_balance': P_balance,
        'M_balance': M_balance,
    }

# ─────────────────────────────────────────────
# FUNCIÓN PARA VERIFICACIÓN BIAXIAL (BRESLER)
# ─────────────────────────────────────────────
def biaxial_bresler(Pu, Mux, Muy, capacity_x, capacity_y, Po, phi_factor):
    phi_Mx = capacity_x['phi_M_n']
    phi_Px = capacity_x['phi_P_n']
    idx_sort = np.argsort(phi_Mx)
    phi_Mx_sorted = phi_Mx[idx_sort]
    phi_Px_sorted = phi_Px[idx_sort]
    
    if Mux <= phi_Mx_sorted[0]:
        phi_Pnx = phi_Px_sorted[0]
    elif Mux >= phi_Mx_sorted[-1]:
        phi_Pnx = phi_Px_sorted[-1]
    else:
        idx = np.searchsorted(phi_Mx_sorted, Mux)
        phi_Pnx = np.interp(Mux, phi_Mx_sorted[idx-1:idx+1], phi_Px_sorted[idx-1:idx+1])
    
    phi_My = capacity_y['phi_M_n']
    phi_Py = capacity_y['phi_P_n']
    idx_sort_y = np.argsort(phi_My)
    phi_My_sorted = phi_My[idx_sort_y]
    phi_Py_sorted = phi_Py[idx_sort_y]
    
    if Muy <= phi_My_sorted[0]:
        phi_Pny = phi_Py_sorted[0]
    elif Muy >= phi_My_sorted[-1]:
        phi_Pny = phi_Py_sorted[-1]
    else:
        idx = np.searchsorted(phi_My_sorted, Muy)
        phi_Pny = np.interp(Muy, phi_My_sorted[idx-1:idx+1], phi_Py_sorted[idx-1:idx+1])
    
    phi_P0 = phi_factor * Po
    
    if phi_Pnx > 0 and phi_Pny > 0 and phi_P0 > 0:
        phi_Pni = 1 / (1/phi_Pnx + 1/phi_Pny - 1/phi_P0)
    else:
        phi_Pni = 0
    
    ratio = Pu / phi_Pni if phi_Pni > 0 else float('inf')
    ok = Pu <= phi_Pni
    
    return {
        'phi_Pnx': phi_Pnx,
        'phi_Pny': phi_Pny,
        'phi_P0': phi_P0,
        'phi_Pni': phi_Pni,
        'ratio': ratio,
        'ok': ok
    }

# ─────────────────────────────────────────────
# FUNCIÓN PARA ESBELTEZ (NSR-10 C.10.10 / ACI 6.6)
# ─────────────────────────────────────────────
def check_slenderness(L, b, h, k, Pu, M1, M2, fc, fy, Es, factor_fuerza):
    r = min(b, h) / math.sqrt(12)
    kl = k * L
    kl_r = kl / r if r > 0 else 999
    
    if kl_r <= 22:
        slender = False
        classification = "Columna corta (sin efectos de segundo orden)"
        delta_ns = 1.0
    elif kl_r <= 100:
        slender = True
        classification = "Columna esbelta (requiere magnificación de momentos)"
        Ec = 4700 * math.sqrt(fc)
        Ig = b * h**3 / 12
        Ig_mm4 = Ig * 1e4
        EI = 0.4 * Ec * Ig_mm4 / (1 + 0.0)
        Pc = math.pi**2 * EI / (kl * 1000)**2
        Pc = Pc / 1000
        Cm = 0.6 + 0.4 * (M1/M2) if abs(M2) > 0 else 1.0
        Cm = max(0.4, Cm)
        delta_ns = Cm / (1 - Pu / (0.75 * Pc))
        delta_ns = max(delta_ns, 1.0)
    else:
        slender = True
        classification = "Columna muy esbelta (kl/r > 100) — requiere análisis no lineal según NSR-10 C.10.10.7"
        delta_ns = 1.0
    
    return {
        'kl_r': kl_r,
        'slender': slender,
        'classification': classification,
        'delta_ns': delta_ns,
        'r': r,
        'kl': kl
    }

# =============================================================================
# SIDEBAR - ENTRADAS DEL USUARIO
# =============================================================================
st.sidebar.header(_t("0. Norma de Diseño", "0. Design Code"))
norma_options = list(CODES.keys())
norma_sel = st.sidebar.selectbox(_t("Norma", "Code"), norma_options, key="c_pm_norma")
code = CODES[norma_sel]

nivel_sismico = st.sidebar.selectbox(
    _t("Nivel Sísmico / Ductilidad:", "Seismic / Ductility Level:"),
    code["seismic_levels"],
    key="c_pm_nivel_sismico"
)

nivel_lower = nivel_sismico.lower()
es_des = any(k in nivel_lower for k in ["des", "disipación especial", "smf", "special", "ga", "ductilidad alta", "pe", "pórtico especial", "de", "diseño especial", "mrle", "alta"])
es_dmo = any(k in nivel_lower for k in ["dmo", "imf", "intermediate", "gm", "moderada", "pm", "mrod", "media", "moderado"]) and not es_des
es_dmi = not (es_des or es_dmo)

if es_des:
    rho_max = code["rho_max_des"]
elif es_dmo:
    rho_max = code["rho_max_dmo"]
else:
    rho_max = code["rho_max_dmi"]
rho_min = code["rho_min"]

st.sidebar.caption(f"📖 {_t('Referencia', 'Reference')}: {code['ref']}")
st.sidebar.caption(f"📊 ρ máx según nivel: {rho_max}% | ρ mín: {rho_min}%")

st.sidebar.header(_t("1. Materiales", "1. Materials"))
fc_unit = st.sidebar.radio(_t("Unidad de f'c:", "f'c Unit:"), ["MPa", "PSI", "kg/cm²"], horizontal=True, key="c_pm_fc_unit")

if fc_unit == "PSI":
    psi_options = {"2500 PSI (≈ 17.2 MPa)": 2500, "3000 PSI (≈ 20.7 MPa)": 3000,
                   "3500 PSI (≈ 24.1 MPa)": 3500, "4000 PSI (≈ 27.6 MPa)": 4000,
                   "4500 PSI (≈ 31.0 MPa)": 4500, "5000 PSI (≈ 34.5 MPa)": 5000,
                   "Personalizado": None}
    psi_choice = st.sidebar.selectbox("Resistencia f'c [PSI]", list(psi_options.keys()), key="c_pm_psi_choice")
    fc_psi = float(psi_options[psi_choice]) if psi_options[psi_choice] is not None else st.sidebar.number_input("f'c personalizado [PSI]", 2000.0, 12000.0, 3000.0, 100.0, key="c_pm_fc_psi_custom")
    fc = fc_psi * 0.00689476
elif fc_unit == "kg/cm²":
    kgcm2_options = {"175 kg/cm² (≈ 17.2 MPa)": 175, "210 kg/cm² (≈ 20.6 MPa)": 210,
                     "250 kg/cm² (≈ 24.5 MPa)": 250, "280 kg/cm² (≈ 27.5 MPa)": 280,
                     "350 kg/cm² (≈ 34.3 MPa)": 350, "420 kg/cm² (≈ 41.2 MPa)": 420,
                     "Personalizado": None}
    kgcm2_choice = st.sidebar.selectbox("Resistencia f'c [kg/cm²]", list(kgcm2_options.keys()), key="c_pm_kgcm2_choice")
    fc_kgcm2 = float(kgcm2_options[kgcm2_choice]) if kgcm2_options[kgcm2_choice] is not None else st.sidebar.number_input("f'c personalizado [kg/cm²]", 100.0, 1200.0, 210.0, 10.0, key="c_pm_fc_kgcm2_custom")
    fc = fc_kgcm2 / 10.1972
else:
    fc = st.sidebar.number_input("Resistencia del Concreto (f'c) [MPa]", 15.0, 80.0, 21.0, 1.0, key="c_pm_fc_mpa")

fy = st.sidebar.number_input("Fluencia del Acero (fy) [MPa]", 240.0, 500.0, 420.0, 10.0, key="c_pm_fy")
Es = 200000.0

st.sidebar.header(_t("2. Geometría de la Sección", "2. Section Geometry"))
seccion_type = st.sidebar.selectbox(_t("Tipo de sección", "Section type"), 
                                    [_t("Rectangular / Cuadrada", "Rectangular / Square"), 
                                     _t("Circular (con espiral)", "Circular (with spiral)")],
                                    key="c_pm_seccion_type")
es_circular = "Circular" in seccion_type

if es_circular:
    D = st.sidebar.number_input(_t("Diámetro (D) [cm]", "Diameter (D) [cm]"), 15.0, 150.0, 40.0, 5.0, key="c_pm_D")
    b = D
    h = D
    st.sidebar.caption("ℹ️ Para columnas circulares se usa espiral en lugar de estribos")
else:
    b = st.sidebar.number_input(_t("Base (b) [cm]", "Width (b) [cm]"), 15.0, 150.0, 30.0, 5.0, key="c_pm_b")
    h = st.sidebar.number_input(_t("Altura (h) [cm]", "Height (h) [cm]"), 15.0, 150.0, 40.0, 5.0, key="c_pm_h")

d_prime = st.sidebar.number_input(_t("Recubrimiento al centroide (d') [cm]", "Cover to centroid (d') [cm]"), 2.0, 15.0, 5.0, 0.5, key="c_pm_dprime")
L_col = st.sidebar.number_input(_t("Altura libre de la columna (L) [cm]", "Column clear height (L) [cm]"), 50.0, 1000.0, 300.0, 25.0, key="c_pm_L")

st.sidebar.header(_t("3. Refuerzo Longitudinal", "3. Longitudinal Reinforcement"))
unit_system = st.sidebar.radio(_t("Sistema de Unidades de las Varillas:", "Bar Unit System:"), 
                               [_t("Pulgadas (EE. UU.)", "Inches (US)"), 
                                _t("Milímetros (SI)", "Millimeters (SI)")], 
                               key="c_pm_unit_system")

rebar_dict = REBAR_US if "Pulgadas" in unit_system or "Inches" in unit_system else REBAR_MM
default_rebar = "#5 (5/8\")" if "Pulgadas" in unit_system else "16 mm"
rebar_type = st.sidebar.selectbox(_t("Diámetro de las Varillas", "Bar Diameter"), list(rebar_dict.keys()), key="c_pm_rebar_type")
rebar_area = rebar_dict[rebar_type]["area"]
rebar_diam = rebar_dict[rebar_type]["diam_mm"]

if es_circular:
    n_barras = st.sidebar.number_input(_t("Número de varillas longitudinales", "Number of longitudinal bars"), 4, 20, 8, 2, key="c_pm_n_barras_circ")
    Ast = n_barras * rebar_area
    layers = []
    angulos = np.linspace(0, 2*np.pi, n_barras, endpoint=False)
    radio_centro = D/2 - d_prime
    for i, ang in enumerate(angulos):
        x_pos = radio_centro * math.cos(ang)
        y_pos = radio_centro * math.sin(ang)
        layers.append({'d': D/2 + y_pos, 'As': rebar_area, 'x': x_pos, 'y': y_pos})
else:
    num_filas_h = st.sidebar.number_input(_t("# de filas Acero Horiz (Superior e Inferior)", "# of horizontal rows (Top & Bottom)"), 2, 15, 2, 1, key="c_pm_num_h")
    num_filas_v = st.sidebar.number_input(_t("# de filas Acero Vert (Laterales)", "# of vertical rows (Sides)"), 2, 15, 2, 1, key="c_pm_num_v")
    
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
    n_barras = n_barras_total

Ag = (math.pi * (D/2)**2) if es_circular else (b * h)
cuantia = Ast / Ag * 100

st.sidebar.markdown(f"**Total varillas:** {n_barras} | **Ast:** {Ast:.2f} cm² | **ρ = {cuantia:.2f}%**")

if cuantia < rho_min or cuantia > rho_max:
    st.sidebar.error(f"❌ CUANTÍA FUERA DE LÍMITES: ρ = {cuantia:.2f}% (límites: {rho_min}% - {rho_max}%)")
    st.stop()

st.sidebar.header(_t("4. Refuerzo Transversal", "4. Transverse Reinforcement"))

if es_circular:
    col_type = _t("Espiral (Spiral)", "Spiral")
    stirrup_dict = STIRRUP_MM if "Milímetros" in unit_system else STIRRUP_US
    default_stirrup = "8 mm" if "Milímetros" in unit_system else "#3 (3/8\")"
    spiral_type = st.sidebar.selectbox(_t("Diámetro de la Espiral", "Spiral Diameter"), list(stirrup_dict.keys()), key="c_pm_spiral_type")
    stirrup_area = stirrup_dict[spiral_type]["area"]
    stirrup_diam = stirrup_dict[spiral_type]["diam_mm"]
    paso_espiral = st.sidebar.number_input(_t("Paso de la espiral (s) [cm]", "Spiral pitch (s) [cm]"), 2.0, 20.0, 7.5, 0.5, key="c_pm_paso")
else:
    col_type_options = [_t("Estribos (Tied)", "Tied"), _t("Espiral (Spiral)", "Spiral")]
    col_type = st.sidebar.selectbox(_t("Tipo de Columna", "Column Type"), col_type_options, key="c_pm_col_type")
    stirrup_dict = STIRRUP_US if "Pulgadas" in unit_system else STIRRUP_MM
    default_stirrup = "#3 (3/8\")" if "Pulgadas" in unit_system else "8 mm"
    stirrup_type = st.sidebar.selectbox(_t("Diámetro del Estribo", "Stirrup Diameter"), list(stirrup_dict.keys()), key="c_pm_stirrup_type")
    stirrup_area = stirrup_dict[stirrup_type]["area"]
    stirrup_diam = stirrup_dict[stirrup_type]["diam_mm"]

if "Espiral" in col_type or es_circular:
    phi_c_max = code["phi_spiral"]
    p_max_factor = code["pmax_spiral"]
else:
    phi_c_max = code["phi_tied"]
    p_max_factor = code["pmax_tied"]
phi_tension = code["phi_tension"]
eps_full = code["eps_tension_full"]

st.sidebar.header(_t("5. Solicitaciones (Biaxiales)", "5. Loads (Biaxial)"))
unidades_salida = st.sidebar.radio(_t("Unidades del Diagrama:", "Output Units:"), 
                                   [_t("KiloNewtons (kN, kN-m)", "KiloNewtons (kN, kN-m)"), 
                                    _t("Toneladas Fuerza (tonf, tonf-m)", "Tons Force (tonf, tonf-m)")], 
                                   key="c_pm_output_units")

if unidades_salida == _t("Toneladas Fuerza (tonf, tonf-m)", "Tons Force (tonf, tonf-m)"):
    factor_fuerza = 0.1019716
    unidad_fuerza = "tonf"
    unidad_mom = "tonf-m"
else:
    factor_fuerza = 1.0
    unidad_fuerza = "kN"
    unidad_mom = "kN-m"

st.sidebar.markdown(f"Cargas últimas en **{unidad_fuerza}** y **{unidad_mom}**:")
Mux_input = st.sidebar.number_input(f"Momento Último Mux [{unidad_mom}]", value=st.session_state.get("c_pm_mux", round(45.0 * factor_fuerza, 2)), step=round(10.0 * factor_fuerza, 2), key="c_pm_mux")
Muy_input = st.sidebar.number_input(f"Momento Último Muy [{unidad_mom}]", value=st.session_state.get("c_pm_muy", round(25.0 * factor_fuerza, 2)), step=round(10.0 * factor_fuerza, 2), key="c_pm_muy")
Pu_input = st.sidebar.number_input(f"Carga Axial Última (Pu) [{unidad_fuerza}]", value=st.session_state.get("c_pm_pu", round(2700.0 * factor_fuerza, 2)), step=round(50.0 * factor_fuerza, 2), key="c_pm_pu")

st.sidebar.header(_t("6. Esbeltez", "6. Slenderness"))
k_factor = st.sidebar.selectbox(_t("Factor de longitud efectiva (k)", "Effective length factor (k)"),
                                [("Ambos extremos articulados", 1.0),
                                 ("Un extremo articulado, otro empotrado", 0.7),
                                 ("Ambos extremos empotrados", 0.5),
                                 ("Voladizo (base empotrada, libre arriba)", 2.0)],
                                format_func=lambda x: x[0],
                                key="c_pm_k")[1]

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: gray; font-size: 11px;">
    © 2026 Todos los derechos reservados.<br>
    <b>Realizado por:</b><br>
    Ing. Msc. César Augusto Giraldo Chaparro<br><br>
    <i>⚠️ Nota Legal: Herramienta de apoyo profesional.</i>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# CÁLCULOS DE CAPACIDAD UNIAXIAL (X y Y)
# =============================================================================
if es_circular:
    cap_x = compute_uniaxial_capacity_circular(D, d_prime, layers, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza)
    cap_y = cap_x
else:
    cap_x = compute_uniaxial_capacity(b, h, d_prime, layers, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza)
    
    layers_y = []
    layers_y.append({'d': d_prime, 'As': num_filas_v * rebar_area})
    num_capas_intermedias_y = num_filas_h - 2
    if num_capas_intermedias_y > 0:
        espacio_y = (b - 2 * d_prime) / (num_capas_intermedias_y + 1)
        for i in range(1, num_capas_intermedias_y + 1):
            layers_y.append({'d': d_prime + i * espacio_y, 'As': 2 * rebar_area})
    layers_y.append({'d': b - d_prime, 'As': num_filas_v * rebar_area})
    
    cap_y = compute_uniaxial_capacity(h, b, d_prime, layers_y, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza)

phi_factor = phi_c_max if Pu_input > 0 else phi_tension
bresler = biaxial_bresler(Pu_input, Mux_input, Muy_input, cap_x, cap_y, cap_x['Po'], phi_factor)

if es_circular:
    slenderness = check_slenderness(L_col, D, D, k_factor, Pu_input, Mux_input, Mux_input, fc, fy, Es, factor_fuerza)
else:
    slenderness = check_slenderness(L_col, b, h, k_factor, Pu_input, Mux_input, Mux_input, fc, fy, Es, factor_fuerza)

Mux_magnified = Mux_input * slenderness['delta_ns']
Muy_magnified = Muy_input * slenderness['delta_ns']

# =============================================================================
# CÁLCULO DE ESTRIBOS Y VERIFICACIÓN Ash
# =============================================================================
if not es_circular:
    recub_cm = max(d_prime - rebar_diam / 20.0, 2.5)
    bc = b - 2 * recub_cm
    Ach = bc * (h - 2 * recub_cm)
    
    s1 = 16 * rebar_diam / 10
    s2 = 48 * stirrup_diam / 10
    s3 = min(b, h)
    s_basico = min(s1, s2, s3)
    
    Lo_conf = max(max(b, h), L_col / 6.0, 45.0)
    
    if es_des:
        s_conf = min(8 * rebar_diam / 10, 24 * stirrup_diam / 10, min(b, h) / 3, 15.0)
        s_centro = min(6 * rebar_diam / 10, s_basico)
        s_centro = max(s_centro, s_conf)
    elif es_dmo:
        s_conf = min(8 * rebar_diam / 10, 24 * stirrup_diam / 10, min(b, h) / 2, 20.0)
        s_centro = s_basico
    else:
        s_conf = s_basico
        s_centro = s_basico
        Lo_conf = 0
    
    fyt = fy
    Ash_req = max(
        0.3 * s_conf * bc * fc / fyt * (Ag / Ach - 1),
        0.09 * s_conf * bc * fc / fyt
    )
    Ash_prov = 2 * stirrup_area
    ash_ok = Ash_prov >= Ash_req
    
    if es_des or es_dmo:
        n_est_por_Lo = math.ceil(Lo_conf / s_conf)
        n_estribos_zona = n_est_por_Lo * 2
        longitud_zona_libre = max(0, L_col - 2 * Lo_conf)
        n_estribos_centro = max(0, math.ceil(longitud_zona_libre / s_centro) - 1) if longitud_zona_libre > 0 else 0
        n_estribos_total = n_estribos_zona + n_estribos_centro + 1
    else:
        n_estribos_total = math.ceil(L_col / s_basico) + 1
        s_conf = s_basico
        Lo_conf = 0
    
    ld_mm = get_development_length(rebar_diam, fy, fc)
    splice_length_mm = 1.3 * ld_mm
    splice_zone_height = splice_length_mm / 10
    splice_start = max(L_col / 3, 0)
    splice_end = splice_start + splice_zone_height
    if splice_end > L_col:
        splice_end = L_col
        splice_start = max(0, L_col - splice_zone_height)
    
    # Para usar en despiece
    perim_estribo = 2 * (b - 2 * recub_cm) + 2 * (h - 2 * recub_cm) + 12 * stirrup_diam / 10
else:
    recub_cm = max(d_prime - rebar_diam / 20.0, 2.5)
    dc = D - 2 * recub_cm
    Ach = math.pi * (dc/2)**2
    Ag_circ = math.pi * (D/2)**2
    
    rho_s_req = 0.45 * (Ag_circ / Ach - 1) * fc / fy
    rho_s_req = max(rho_s_req, 0.12 * fc / fy)
    
    area_spiral = stirrup_area
    rho_s_prov = (4 * area_spiral) / (dc * paso_espiral)
    ash_ok = rho_s_prov >= rho_s_req
    n_estribos_total = math.ceil(L_col / paso_espiral) + 1
    
    ld_mm = get_development_length(rebar_diam, fy, fc)
    splice_length_mm = 1.3 * ld_mm
    splice_zone_height = splice_length_mm / 10
    splice_start = max(L_col / 3, 0)
    splice_end = splice_start + splice_zone_height
    if splice_end > L_col:
        splice_end = L_col
        splice_start = max(0, L_col - splice_zone_height)
    
    # Para usar en despiece circular
    long_espiral_vuelta = math.sqrt((math.pi * dc)**2 + paso_espiral**2)
    long_espiral_total = long_espiral_vuelta * (L_col / paso_espiral)

# =============================================================================
# CANTIDADES DE MATERIALES
# =============================================================================
vol_concreto_m3 = (Ag / 10000) * (L_col / 100) if not es_circular else (math.pi * (D/2)**2 / 10000) * (L_col / 100)
peso_acero_long_kg = Ast * (L_col * 10) * 7.85e-3

if not es_circular:
    peso_unit_estribo = (perim_estribo / 100.0) * (stirrup_area * 100) * 7.85e-3
    peso_total_estribos_kg = n_estribos_total * peso_unit_estribo
else:
    peso_total_estribos_kg = long_espiral_total / 100 * (stirrup_area * 100) * 7.85e-3

peso_total_acero_kg = peso_acero_long_kg + peso_total_estribos_kg

# =============================================================================
# GRÁFICO 3D BIAXIAL
# =============================================================================
def create_biaxial_3d_plot(cap_x, cap_y, Pu, Mux, Muy):
    Mx_vals = np.linspace(0, max(cap_x['phi_M_n']) * 1.1, 30)
    My_vals = np.linspace(0, max(cap_y['phi_M_n']) * 1.1, 30)
    Mx_grid, My_grid = np.meshgrid(Mx_vals, My_vals)
    P_grid = np.zeros_like(Mx_grid)
    
    for i in range(len(Mx_vals)):
        for j in range(len(My_vals)):
            res = biaxial_bresler(Pu, Mx_grid[i,j], My_grid[i,j], cap_x, cap_y, cap_x['Po'], phi_c_max)
            P_grid[i,j] = res['phi_Pni'] if res['phi_Pni'] > 0 else 0
    
    fig = go.Figure()
    fig.add_trace(go.Surface(x=Mx_grid, y=My_grid, z=P_grid, colorscale='Viridis', opacity=0.85,
                             name='Superficie de Interacción', showscale=True,
                             colorbar=dict(title=f"φPn [{unidad_fuerza}]")))
    fig.add_trace(go.Scatter3d(x=[Mux], y=[Muy], z=[Pu], mode='markers',
                               marker=dict(size=8, color='red', symbol='circle'),
                               name=f'Punto de Diseño (Mux={Mux:.1f}, Muy={Muy:.1f}, Pu={Pu:.1f})'))
    fig.update_layout(title=_t("Superficie de Interacción Biaxial (Método de Bresler)", "Biaxial Interaction Surface (Bresler Method)"),
                      scene=dict(xaxis_title=f"Mux [{unidad_mom}]", yaxis_title=f"Muy [{unidad_mom}]",
                                 zaxis_title=f"φPn [{unidad_fuerza}]", aspectmode='manual', aspectratio=dict(x=1, y=1, z=0.8)),
                      height=600, margin=dict(l=0, r=0, b=0, t=40))
    return fig

def create_pm_2d_plot(cap_x, Pu, Mu, unidad_mom, unidad_fuerza):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(cap_x['M_n'], cap_x['P_n'], 'b--', linewidth=1.5, label=r"Resistencia Nominal ($P_n, M_n$)")
    ax.plot(cap_x['phi_M_n'], cap_x['phi_P_n'], 'r-', linewidth=2.5, label=r"Resistencia de Diseño ($\phi P_n, \phi M_n$)")
    if cap_x['M_balance'] is not None and cap_x['P_balance'] is not None:
        ax.plot(cap_x['M_balance'], cap_x['P_balance'], 'ro', markersize=8, markeredgecolor='black',
                label=f"Punto de Balance\nM={cap_x['M_balance']:.1f} {unidad_mom}\nP={cap_x['P_balance']:.1f} {unidad_fuerza}")
    ax.plot(Mu, Pu, 'o', markersize=9, color='lime', markeredgecolor='black', zorder=6,
            label=f"Punto de Diseño (Mu={Mu:.1f}, Pu={Pu:.1f})")
    ax.axhline(y=0, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlabel(f"Momento Flector M [{unidad_mom}]")
    ax.set_ylabel(f"Carga Axial P [{unidad_fuerza}]")
    ax.set_title(f"Diagrama de Interacción P-M — {norma_sel}\n" +
                 f"Columna {b:.0f}×{h:.0f} cm | f'c={fc:.1f} MPa | fy={fy:.0f} MPa")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=8)
    return fig

fig_pm_2d = create_pm_2d_plot(cap_x, Pu_input, Mux_input, unidad_mom, unidad_fuerza)
pm_2d_img = io.BytesIO()
fig_pm_2d.savefig(pm_2d_img, format='png', dpi=150, bbox_inches='tight')
pm_2d_img.seek(0)
fig_3d = create_biaxial_3d_plot(cap_x, cap_y, Pu_input, Mux_input, Muy_input)

# =============================================================================
# TABS PRINCIPALES
# =============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    _t("📊 Diagrama P-M Biaxial", "📊 Biaxial P-M Diagram"),
    _t("🔲 Sección & Estribos", "🔲 Section & Ties"),
    _t("📦 Cantidades y APU", "📦 Quantities & APU"),
    _t("📄 Memoria de Cálculo", "📄 Calculation Report")
])

# =============================================================================
# TAB 1: DIAGRAMA P-M BIAXIAL
# =============================================================================
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(_t("📈 Diagrama P-M 2D (Eje X)", "📈 P-M 2D Diagram (X-Axis)"))
        st.pyplot(fig_pm_2d)
        st.subheader(_t("🌐 Superficie de Interacción Biaxial 3D", "🌐 Biaxial Interaction Surface 3D"))
        st.plotly_chart(fig_3d, use_container_width=True)
    with col2:
        st.subheader(_t("📋 Verificación Biaxial (Bresler)", "📋 Biaxial Verification (Bresler)"))
        st.markdown(f"""
        | Parámetro | Valor |
        |-----------|-------|
        | **φPnx** (para Mux={Mux_input:.1f}) | {bresler['phi_Pnx']:.2f} {unidad_fuerza} |
        | **φPny** (para Muy={Muy_input:.1f}) | {bresler['phi_Pny']:.2f} {unidad_fuerza} |
        | **φP0** (axial pura) | {bresler['phi_P0']:.2f} {unidad_fuerza} |
        | **φPni** (Bresler) | {bresler['phi_Pni']:.2f} {unidad_fuerza} |
        | **Pu** solicitante | {Pu_input:.2f} {unidad_fuerza} |
        | **Relación Pu/φPni** | {bresler['ratio']:.3f} |
        """)
        if bresler['ok']:
            st.success(f"✅ **VERIFICACIÓN BIAXIAL CUMPLE**\n\nPu ({Pu_input:.1f}) ≤ φPni ({bresler['phi_Pni']:.1f})")
        else:
            st.error(f"❌ **VERIFICACIÓN BIAXIAL NO CUMPLE**\n\nPu ({Pu_input:.1f}) > φPni ({bresler['phi_Pni']:.1f})")
        st.markdown("---")
        st.subheader(_t("📊 Verificación de Esbeltez", "📊 Slenderness Verification"))
        st.markdown(f"""
        | Parámetro | Valor | Estado |
        |-----------|-------|--------|
        | **kl/r** | {slenderness['kl_r']:.1f} | |
        | **Clasificación** | {slenderness['classification']} | |
        | **δns (magnificación)** | {slenderness['delta_ns']:.3f} | |
        | **Mux magnificado** | {Mux_magnified:.2f} {unidad_mom} | |
        | **Muy magnificado** | {Muy_magnified:.2f} {unidad_mom} | |
        """)
        if slenderness['kl_r'] > 100:
            st.warning("⚠️ **kl/r > 100** — Se requiere análisis no lineal según NSR-10 C.10.10.7")
        st.markdown("---")
        st.subheader(_t("🔧 Verificación de Estribos / Espiral", "🔧 Tie / Spiral Verification"))
        if not es_circular:
            st.markdown(f"""
            | Parámetro | Valor | Requerido | Estado |
            |-----------|-------|-----------|--------|
            | **Ash requerido** | {Ash_req:.3f} cm² | | |
            | **Ash provisto** | {Ash_prov:.3f} cm² | ≥ {Ash_req:.3f} | {'✅' if ash_ok else '❌'} |
            | **s_conf** | {s_conf:.1f} cm | {'≤ 15' if es_des else '≤ 20' if es_dmo else '≤ min(b,h)'} | |
            | **Lo_conf** | {Lo_conf:.1f} cm | ≥ max(b,h,L/6,45) | {'✅' if Lo_conf >= max(b,h,L_col/6,45) else '❌'} |
            | **N° estribos** | {n_estribos_total} | | |
            """)
        else:
            st.markdown(f"""
            | Parámetro | Valor | Requerido | Estado |
            |-----------|-------|-----------|--------|
            | **ρs requerido** | {rho_s_req:.4f} | | |
            | **ρs provisto** | {rho_s_prov:.4f} | ≥ {rho_s_req:.4f} | {'✅' if ash_ok else '❌'} |
            | **Paso espiral** | {paso_espiral:.1f} cm | ≤ min(D/5, 8 cm) | {'✅' if paso_espiral <= min(D/5, 8) else '❌'} |
            | **N° vueltas** | {n_estribos_total} | | |
            """)
        st.caption(f"📖 Ref: {code['ref']} | Nivel Sísmico: {nivel_sismico}")

# =============================================================================
# TAB 2: SECCIÓN Y ESTRIBOS (con DXF y RÓTULO ICONTEC)
# =============================================================================
with tab2:
    st.subheader(_t("🧊 Visualización 3D de la Columna", "🧊 3D Column Visualization"))
    fig3d_col = go.Figure()
    if es_circular:
        theta = np.linspace(0, 2*np.pi, 50)
        z = np.linspace(0, L_col, 20)
        theta_grid, z_grid = np.meshgrid(theta, z)
        x_grid = (D/2) * np.cos(theta_grid)
        y_grid = (D/2) * np.sin(theta_grid)
        fig3d_col.add_trace(go.Surface(x=x_grid, y=y_grid, z=z_grid, opacity=0.3, colorscale='Greys', showscale=False))
    else:
        x_c = [-b/2, b/2, b/2, -b/2, -b/2, b/2, b/2, -b/2]
        y_c = [-h/2, -h/2, h/2, h/2, -h/2, -h/2, h/2, h/2]
        z_c = [0, 0, 0, 0, L_col, L_col, L_col, L_col]
        fig3d_col.add_trace(go.Mesh3d(x=x_c, y=y_c, z=z_c, alphahull=0, opacity=0.15, color='gray', name='Concreto'))
    fig3d_col.update_layout(scene=dict(aspectmode='data', xaxis_title='b (cm)', yaxis_title='h (cm)', zaxis_title='L (cm)'),
                            height=450, margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig3d_col, use_container_width=True)
    st.markdown("---")
    st.subheader(_t("📐 Sección Transversal", "📐 Cross Section"))
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        fig_sec, ax_s = plt.subplots(figsize=(5, 5))
        ax_s.set_aspect('equal')
        ax_s.set_facecolor('#1a1a2e')
        fig_sec.patch.set_facecolor('#1a1a2e')
        if es_circular:
            circle = plt.Circle((0, 0), D/2, linewidth=2, edgecolor='white', facecolor='#4a4a6a', fill=True)
            ax_s.add_patch(circle)
            circle_rec = plt.Circle((0, 0), D/2 - recub_cm, linewidth=1.5, edgecolor='#00d4ff', facecolor='none', linestyle='--')
            ax_s.add_patch(circle_rec)
            radio_centro = D/2 - d_prime
            for layer in layers:
                x_pos = layer.get('x', 0)
                y_pos = layer.get('y', 0)
                ax_s.add_patch(plt.Circle((x_pos, y_pos), rebar_diam/20, color='#ff6b35', zorder=5))
            ax_s.set_xlim(-D/2 - 5, D/2 + 5)
            ax_s.set_ylim(-D/2 - 5, D/2 + 5)
        else:
            ax_s.add_patch(patches.Rectangle((0, 0), b, h, linewidth=2, edgecolor='white', facecolor='#4a4a6a'))
            ax_s.add_patch(patches.Rectangle((recub_cm, recub_cm), b-2*recub_cm, h-2*recub_cm,
                linewidth=1.5, edgecolor='#00d4ff', facecolor='none', linestyle='--'))
            r_bar = rebar_diam / 20.0
            xs = np.linspace(d_prime, b - d_prime, num_filas_h) if num_filas_h > 1 else [b/2]
            for x in xs:
                ax_s.add_patch(plt.Circle((x, h - d_prime), r_bar, color='#ff6b35', zorder=5))
                ax_s.add_patch(plt.Circle((x, d_prime), r_bar, color='#ff6b35', zorder=5))
            if num_capas_intermedias > 0:
                esp = (h - 2*d_prime) / (num_capas_intermedias + 1)
                for i in range(1, num_capas_intermedias + 1):
                    y_int = d_prime + i * esp
                    ax_s.add_patch(plt.Circle((d_prime, y_int), r_bar, color='#ff6b35', zorder=5))
                    ax_s.add_patch(plt.Circle((b - d_prime, y_int), r_bar, color='#ff6b35', zorder=5))
            ax_s.set_xlim(-5, b + 5)
            ax_s.set_ylim(-5, h + 5)
        ax_s.axis('off')
        ax_s.set_title(f"Sección {'Circular' if es_circular else 'Rectangular'} — {n_barras} varillas Ø{rebar_diam:.0f}mm", color='white', fontsize=9)
        st.pyplot(fig_sec)
    with col_s2:
        st.subheader(_t("📝 Resumen de Verificaciones", "📝 Verification Summary"))
        checks_data = {
            "Verificación": ["Cuantía longitudinal", "Verificación biaxial", "Esbeltez (kl/r ≤ 22)",
                             f"Ash {'espiral' if es_circular else 'estribos'}", "Longitud confinamiento Lo", "Separación máxima"],
            "Estado": ["✅" if rho_min <= cuantia <= rho_max else "❌", "✅" if bresler['ok'] else "❌",
                       "✅" if slenderness['kl_r'] <= 22 else "⚠️", "✅" if ash_ok else "❌",
                       "✅" if (es_des or es_dmo) and Lo_conf >= max(b,h,L_col/6,45) else "✅" if not (es_des or es_dmo) else "❌",
                       "✅" if (es_des and s_conf <= 15) or (es_dmo and s_conf <= 20) or es_dmi else "❌"]
        }
        st.dataframe(pd.DataFrame(checks_data), use_container_width=True, hide_index=True)
        st.markdown("---")
        st.subheader(_t("💾 Exportar Plano DXF (ICONTEC)", "💾 Export DXF (ICONTEC)"))
        try:
            doc_dxf = ezdxf.new('R2010')
            doc_dxf.units = ezdxf.units.CM
            for lay, col in [('CONCRETO', 7), ('ESTRIBOS', 4), ('VARILLAS', 1), ('TEXTO', 3), 
                             ('EMPALME', 6), ('COTAS', 5), ('ROTULO', 2), ('MARGEN', 8)]:
                if lay not in doc_dxf.layers:
                    doc_dxf.layers.add(lay, color=col)
            msp = doc_dxf.modelspace()
            ancho_plano = 29.7
            alto_plano = 21.0
            msp.add_lwpolyline([(0, 0), (ancho_plano, 0), (ancho_plano, alto_plano), (0, alto_plano), (0, 0)], 
                               dxfattribs={'layer': 'MARGEN', 'color': 8})
            corte_x = 2.5
            msp.add_line((corte_x, 0), (corte_x, alto_plano), dxfattribs={'layer': 'MARGEN', 'linetype': 'DASHED', 'color': 8})
            rotulo_w = 18.0
            rotulo_h = 6.0
            rotulo_x = ancho_plano - rotulo_w
            rotulo_y = 0
            msp.add_lwpolyline([(rotulo_x, rotulo_y), (rotulo_x + rotulo_w, rotulo_y),
                                (rotulo_x + rotulo_w, rotulo_y + rotulo_h), (rotulo_x, rotulo_y + rotulo_h), (rotulo_x, rotulo_y)],
                               dxfattribs={'layer': 'ROTULO', 'color': 2})
            if 'ROMANS' not in doc_dxf.styles:
                doc_dxf.styles.new('ROMANS', font='romans.shx')
            campos = {"EMPRESA": "INGENIERÍA ESTRUCTURAL SAS", "PROYECTO": "Proyecto Estructural", "N° PLANO": "COL-001",
                      "ESCALA": "1:20", "FECHA": datetime.datetime.now().strftime("%d/%m/%Y"), "REVISIÓN": "0",
                      "ELABORÓ": "Ing. César Giraldo", "REVISÓ": "Ing. Revisor", "APROBÓ": "Ing. Aprobador", "HOJA": "1/1"}
            celdas = [("EMPRESA", rotulo_x + 0.5, rotulo_y + 5.0, 8.0, 1.0), ("PROYECTO", rotulo_x + 0.5, rotulo_y + 4.0, 8.0, 1.0),
                      ("N° PLANO", rotulo_x + 9.0, rotulo_y + 5.0, 3.0, 1.0), ("ESCALA", rotulo_x + 12.5, rotulo_y + 5.0, 2.5, 1.0),
                      ("FECHA", rotulo_x + 15.0, rotulo_y + 5.0, 2.5, 1.0), ("REVISIÓN", rotulo_x + 9.0, rotulo_y + 4.0, 2.5, 1.0),
                      ("ELABORÓ", rotulo_x + 11.5, rotulo_y + 4.0, 3.0, 1.0), ("REVISÓ", rotulo_x + 14.5, rotulo_y + 4.0, 3.0, 1.0),
                      ("APROBÓ", rotulo_x + 17.5, rotulo_y + 4.0, 2.0, 1.0), ("HOJA", rotulo_x + 9.0, rotulo_y + 3.0, 2.5, 1.0)]
            for campo, x, y, w, h in celdas:
                msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], dxfattribs={'layer': 'ROTULO'})
                msp.add_text(campos[campo], dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 
                            'height': 0.35 if "EMPRESA" in campo else 0.25, 'insert': (x + w/2, y + h/2)}).set_placement('middle_center')
            qr_url = st.text_input(_t("URL para QR (proyecto en la nube)", "QR URL (cloud project)"), 
                                   value="https://github.com/tuproyecto", key="qr_url")
            if qr_url:
                try:
                    qr = qrcode.QRCode(box_size=2, border=1)
                    qr.add_data(qr_url)
                    qr.make(fit=True)
                    st.caption("✅ QR generado - se incrustará en el DXF como texto")
                except Exception as e:
                    st.warning(f"No se pudo generar QR: {e}")
            if es_circular:
                msp.add_circle((15, 15), D/2, dxfattribs={'layer': 'CONCRETO'})
                msp.add_circle((15, 15), D/2 - recub_cm, dxfattribs={'layer': 'ESTRIBOS'})
                radio_centro = D/2 - d_prime
                for ang in np.linspace(0, 2*np.pi, n_barras, endpoint=False):
                    x = 15 + radio_centro * math.cos(ang)
                    y = 15 + radio_centro * math.sin(ang)
                    msp.add_circle((x, y), rebar_diam/20, dxfattribs={'layer': 'VARILLAS'})
            else:
                msp.add_lwpolyline([(5, 5), (5+b, 5), (5+b, 5+h), (5, 5+h), (5, 5)], dxfattribs={'layer': 'CONCRETO'})
                msp.add_lwpolyline([(5+recub_cm, 5+recub_cm), (5+b-recub_cm, 5+recub_cm), 
                                   (5+b-recub_cm, 5+h-recub_cm), (5+recub_cm, 5+h-recub_cm), (5+recub_cm, 5+recub_cm)], 
                                   dxfattribs={'layer': 'ESTRIBOS'})
                r_bar = rebar_diam / 20
                xs = np.linspace(5+d_prime, 5+b-d_prime, num_filas_h) if num_filas_h > 1 else [5+b/2]
                for x in xs:
                    msp.add_circle((x, 5+h-d_prime), r_bar, dxfattribs={'layer': 'VARILLAS'})
                    msp.add_circle((x, 5+d_prime), r_bar, dxfattribs={'layer': 'VARILLAS'})
                if num_capas_intermedias > 0:
                    esp = (h - 2*d_prime) / (num_capas_intermedias + 1)
                    for i in range(1, num_capas_intermedias + 1):
                        y_int = 5 + d_prime + i * esp
                        msp.add_circle((5+d_prime, y_int), r_bar, dxfattribs={'layer': 'VARILLAS'})
                        msp.add_circle((5+b-d_prime, y_int), r_bar, dxfattribs={'layer': 'VARILLAS'})
            msp.add_text(f"SECCION - Columna {b:.0f}x{h:.0f} cm", dxfattribs={'layer': 'TEXTO', 'height': 0.4, 'insert': (15, 30)})
            dxf_buffer = io.StringIO()
            doc_dxf.write(dxf_buffer)
            st.download_button(label=_t("📥 Descargar DXF (ICONTEC)", "📥 Download DXF (ICONTEC)"),
                               data=dxf_buffer.getvalue().encode('utf-8'),
                               file_name=f"Columna_{b:.0f}x{h:.0f}_ICONTEC.dxf", mime="application/dxf")
        except Exception as e:
            st.error(f"Error al generar DXF: {e}")
            st.info("Asegúrate de tener instalado ezdxf: pip install ezdxf")

# =============================================================================
# TAB 3: CANTIDADES, DESPIECE Y APU
# =============================================================================
with tab3:
    st.subheader(f"📦 Cantidades de Materiales — {'Circular' if es_circular else 'Rectangular'}, L={L_col:.0f} cm")
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric(_t("Concreto", "Concrete"), f"{vol_concreto_m3:.4f} m³")
    col_c2.metric(_t("Acero Total", "Total Steel"), f"{peso_total_acero_kg:.2f} kg")
    col_c3.metric(_t("Acero Longitudinal", "Long. Steel"), f"{peso_acero_long_kg:.2f} kg")
    col_c4.metric(_t("Acero Estribos", "Tie Steel"), f"{peso_total_estribos_kg:.2f} kg")
    st.markdown("---")
    st.subheader(_t("📏 Despiece de Acero", "📏 Bar Bending Schedule"))
    
    if es_circular:
        long_bar = (L_col + 2 * (ld_mm/10) + 2 * (12*rebar_diam/10)) / 100
        peso_long = n_barras * long_bar * (rebar_area * 100) * 7.85e-3
        
        despiece_data = {
            "Marca": ["L1", "E1 (Espiral)"],
            "Cantidad": [n_barras, 1],
            "Diámetro": [_bar_label(rebar_diam), _bar_label(stirrup_diam)],
            "Longitud (m)": [long_bar, long_espiral_total/100],
            "Longitud Total (m)": [n_barras * long_bar, long_espiral_total/100],
            "Peso (kg)": [peso_long, peso_total_estribos_kg]
        }
        long_bar_m = long_bar
    else:
        long_bar_m = (L_col + 2 * (ld_mm/10) + 2 * (12*rebar_diam/10)) / 100
        peso_long_total = n_barras_total * long_bar_m * (rebar_area * 100) * 7.85e-3
        
        despiece_data = {
            "Marca": ["L1", "E1"],
            "Cantidad": [n_barras_total, n_estribos_total],
            "Diámetro": [_bar_label(rebar_diam), _bar_label(stirrup_diam)],
            "Longitud (m)": [long_bar_m, perim_estribo/100],
            "Longitud Total (m)": [n_barras_total * long_bar_m, n_estribos_total * perim_estribo/100],
            "Peso (kg)": [peso_long_total, peso_total_estribos_kg]
        }
    
    df_despiece = pd.DataFrame(despiece_data)
    st.dataframe(df_despiece.style.format({"Longitud (m)": "{:.2f}", "Longitud Total (m)": "{:.2f}", "Peso (kg)": "{:.1f}"}), 
                 use_container_width=True)
    
    fig_bars, ax_bars = plt.subplots(figsize=(6, 4))
    ax_bars.bar(df_despiece["Marca"], df_despiece["Peso (kg)"], color=['#ff6b35', '#4caf50'])
    ax_bars.set_xlabel(_t("Elemento", "Element"))
    ax_bars.set_ylabel(_t("Peso (kg)", "Weight (kg)"))
    ax_bars.set_title(_t("Distribución de pesos", "Weight distribution"))
    ax_bars.grid(True, alpha=0.3)
    st.pyplot(fig_bars)
    
    with st.expander(_t("📐 Dibujo de Figurado para Taller", "📐 Shop Drawing Details"), expanded=False):
        st.markdown(_t("Formas reales de las barras con ganchos y dimensiones.", "Actual bar shapes with hooks and dimensions."))
        hook_len_cm = 12 * rebar_diam / 10
        if es_circular:
            straight_len_cm = long_bar_m * 100 - 2 * hook_len_cm
            fig_l1 = draw_longitudinal_bar(long_bar_m*100, straight_len_cm, hook_len_cm, rebar_diam, _bar_label(rebar_diam))
            st.pyplot(fig_l1)
            fig_spiral = draw_spiral(D, paso_espiral, stirrup_diam, _bar_label(stirrup_diam))
            st.pyplot(fig_spiral)
        else:
            straight_len_cm = long_bar_m * 100 - 2 * hook_len_cm
            fig_l1 = draw_longitudinal_bar(long_bar_m*100, straight_len_cm, hook_len_cm, rebar_diam, _bar_label(rebar_diam))
            st.pyplot(fig_l1)
            inside_b = b - 2 * recub_cm
            inside_h = h - 2 * recub_cm
            hook_len_est = 12 * stirrup_diam / 10
            fig_e1 = draw_stirrup(inside_b, inside_h, hook_len_est, stirrup_diam, _bar_label(stirrup_diam))
            st.pyplot(fig_e1)
    
    with st.expander(_t("💰 Presupuesto APU", "💰 APU Budget"), expanded=False):
        st.markdown(_t("Ingrese precios unitarios para calcular el costo total.", "Enter unit prices to calculate total cost."))
        with st.form(key="apu_form"):
            moneda = st.text_input(_t("Moneda", "Currency"), value=st.session_state.get("apu_moneda", "COP"))
            col_apu1, col_apu2 = st.columns(2)
            with col_apu1:
                precio_cemento = st.number_input(_t("Precio por bulto cemento", "Price per cement bag"), value=st.session_state.get("apu_cemento", 28000.0), step=1000.0)
                precio_acero = st.number_input(_t("Precio por kg acero", "Price per kg steel"), value=st.session_state.get("apu_acero", 7500.0), step=100.0)
                precio_arena = st.number_input(_t("Precio por m³ arena", "Price per m³ sand"), value=st.session_state.get("apu_arena", 120000.0), step=5000.0)
                precio_grava = st.number_input(_t("Precio por m³ grava", "Price per m³ gravel"), value=st.session_state.get("apu_grava", 130000.0), step=5000.0)
            with col_apu2:
                precio_mo = st.number_input(_t("Costo mano de obra (día)", "Labor cost per day"), value=st.session_state.get("apu_mo", 70000.0), step=5000.0)
                pct_aui = st.number_input(_t("% A.I.U.", "% A.I.U."), value=st.session_state.get("apu_aui", 30.0), step=5.0) / 100.0
            submitted = st.form_submit_button(_t("Calcular Presupuesto", "Calculate Budget"))
            if submitted:
                st.session_state.apu_config = {"moneda": moneda, "cemento": precio_cemento, "acero": precio_acero,
                    "arena": precio_arena, "grava": precio_grava, "costo_dia_mo": precio_mo, "pct_aui": pct_aui}
                st.success(_t("Precios guardados.", "Prices saved."))
                st.rerun()
        if "apu_config" in st.session_state:
            apu = st.session_state.apu_config
            mix = get_mix_for_fc(fc)
            bag_kg = CEMENT_BAGS.get(norma_sel, CEMENT_BAGS["NSR-10 (Colombia)"])[0]["kg"]
            bultos_col = vol_concreto_m3 * mix["cem"] / bag_kg
            costo_cemento = bultos_col * apu["cemento"]
            costo_acero = peso_total_acero_kg * apu["acero"]
            costo_arena = (mix["arena"] * vol_concreto_m3 / 1500) * apu["arena"]
            costo_grava = (mix["grava"] * vol_concreto_m3 / 1600) * apu["grava"]
            costo_mo = (peso_total_acero_kg * 0.04 + vol_concreto_m3 * 0.4) * apu["costo_dia_mo"]
            costo_directo = costo_cemento + costo_acero + costo_arena + costo_grava + costo_mo
            aiu = costo_directo * apu["pct_aui"]
            total = costo_directo + aiu
            st.metric(_t("💰 Total Proyecto", "💰 Total Project"), f"{total:,.0f} {apu['moneda']}")
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                df_apu = pd.DataFrame({
                    "Item": ["Cemento", "Acero", "Arena", "Grava", "Mano de Obra", "A.I.U.", "TOTAL"],
                    "Cantidad": [bultos_col, peso_total_acero_kg, mix["arena"]*vol_concreto_m3/1500, 
                                 mix["grava"]*vol_concreto_m3/1600, peso_total_acero_kg*0.04 + vol_concreto_m3*0.4, "", ""],
                    "Unidad": [f"bultos ({bag_kg}kg)", "kg", "m³", "m³", "días", "%", ""],
                    "Subtotal": [costo_cemento, costo_acero, costo_arena, costo_grava, costo_mo, aiu, total]
                })
                df_apu.to_excel(writer, index=False, sheet_name='APU')
                workbook = writer.book
                worksheet = writer.sheets['APU']
                money_fmt = workbook.add_format({'num_format': '#,##0.00'})
                worksheet.set_column('D:D', 15, money_fmt)
            output_excel.seek(0)
            st.download_button(_t("📥 Descargar Presupuesto Excel", "📥 Download Budget Excel"), 
                               data=output_excel, file_name=f"APU_Columna_{b:.0f}x{h:.0f}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============================================================================
# TAB 4: MEMORIA DE CÁLCULO COMPLETA
# =============================================================================
with tab4:
    st.subheader(_t("📄 Generar Memoria de Cálculo Completa", "📄 Generate Complete Calculation Report"))
    if st.button(_t("📝 Generar Memoria DOCX", "📝 Generate DOCX Report"), type="primary"):
        doc = Document()
        doc.add_heading(f"Memoria de Cálculo — Columna {'Circular' if es_circular else 'Rectangular'}", 0)
        doc.add_paragraph(f"Norma: {norma_sel}")
        doc.add_paragraph(f"Nivel Sísmico: {nivel_sismico}")
        doc.add_paragraph(f"Fecha: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
        doc.add_paragraph(f"Ingeniero: Ing. Msc. César Augusto Giraldo Chaparro")
        doc.add_heading("1. CRITERIOS NORMATIVOS", level=1)
        doc.add_paragraph(f"El diseño se realiza según la norma {norma_sel}. Nivel sísmico: {nivel_sismico}. "
                         f"Factores de reducción: φ compresión = {phi_c_max}, φ tensión = {phi_tension}.")
        doc.add_heading("2. PROPIEDADES MECÁNICAS DE MATERIALES", level=1)
        Ec = 4700 * math.sqrt(fc)
        doc.add_paragraph(f"Concreto: f'c = {fc:.1f} MPa, Ec = {Ec:.0f} MPa\nAcero: fy = {fy:.0f} MPa, Es = {Es:.0f} MPa")
        doc.add_heading("3. GEOMETRÍA Y ARMADO", level=1)
        if es_circular:
            doc.add_paragraph(f"Diámetro: D = {D:.0f} cm | Área bruta: Ag = {Ag:.1f} cm²")
        else:
            doc.add_paragraph(f"Base: b = {b:.0f} cm | Altura: h = {h:.0f} cm | Área bruta: Ag = {Ag:.1f} cm²")
        doc.add_paragraph(f"Refuerzo longitudinal: {n_barras} varillas {rebar_type} (Ast = {Ast:.2f} cm², ρ = {cuantia:.2f}%)")
        sec_img = io.BytesIO()
        fig_sec.savefig(sec_img, format='png', dpi=150, bbox_inches='tight')
        sec_img.seek(0)
        doc.add_picture(sec_img, width=Inches(4))
        doc.add_heading("4. DIAGRAMA DE INTERACCIÓN P-M", level=1)
        doc.add_picture(pm_2d_img, width=Inches(5))
        doc.add_heading("5. VERIFICACIÓN DE ESBELTEZ", level=1)
        doc.add_paragraph(f"Factor de longitud efectiva: k = {k_factor}\nRadio de giro: r = {slenderness['r']:.1f} cm\nkl/r = {slenderness['kl_r']:.1f}\nClasificación: {slenderness['classification']}\nFactor de magnificación δns = {slenderness['delta_ns']:.3f}")
        doc.add_heading("6. VERIFICACIÓN BIAXIAL (MÉTODO DE BRESLER)", level=1)
        doc.add_paragraph(f"φPnx (para Mux={Mux_input:.1f}) = {bresler['phi_Pnx']:.2f} {unidad_fuerza}\nφPny (para Muy={Muy_input:.1f}) = {bresler['phi_Pny']:.2f} {unidad_fuerza}\nφP0 = {bresler['phi_P0']:.2f} {unidad_fuerza}\nφPni (Bresler) = {bresler['phi_Pni']:.2f} {unidad_fuerza}\nPu solicitante = {Pu_input:.2f} {unidad_fuerza}\n\n**Resultado: {'CUMPLE' if bresler['ok'] else 'NO CUMPLE'}**")
        doc.add_heading("7. DISEÑO DE ESTRIBOS", level=1)
        if not es_circular:
            doc.add_paragraph(f"Diámetro estribo: Ø{stirrup_diam:.0f} mm\nAsh requerido: {Ash_req:.3f} cm²\nAsh provisto: {Ash_prov:.3f} cm²\nEspaciamiento zona confinada: s_conf = {s_conf:.1f} cm\nLongitud zona confinada: Lo = {Lo_conf:.1f} cm\nN° total de estribos: {n_estribos_total}")
        else:
            doc.add_paragraph(f"Diámetro espiral: Ø{stirrup_diam:.0f} mm\nPaso espiral: s = {paso_espiral:.1f} cm\nρs requerido: {rho_s_req:.4f}\nρs provisto: {rho_s_prov:.4f}\nN° vueltas: {n_estribos_total}")
        doc.add_heading("8. LONGITUDES DE DESARROLLO Y EMPALMES", level=1)
        doc.add_paragraph(f"Longitud de desarrollo (ld): {ld_mm/10:.1f} cm\nLongitud de empalme (Clase B): {splice_length_mm/10:.1f} cm\nZona de empalme: {splice_start:.0f} cm - {splice_end:.0f} cm desde la base")
        doc.add_heading("9. COMBINACIONES DE CARGA APLICADAS", level=1)
        doc.add_paragraph("Según NSR-10 B.2.4 / ACI 318:\n- 1.4D\n- 1.2D + 1.6L\n- 1.2D + 1.0E + 0.5L\n- 0.9D + 1.0E")
        doc.add_heading("10. FIGURADO DE ACERO", level=1)
        hook_len_cm = 12 * rebar_diam / 10
        if es_circular:
            straight_len_cm = long_bar_m * 100 - 2 * hook_len_cm
            fig_l1_mem = draw_longitudinal_bar(long_bar_m*100, straight_len_cm, hook_len_cm, rebar_diam, _bar_label(rebar_diam))
            l1_img = io.BytesIO()
            fig_l1_mem.savefig(l1_img, format='png', dpi=150, bbox_inches='tight')
            l1_img.seek(0)
            doc.add_picture(l1_img, width=Inches(5))
        else:
            straight_len_cm = long_bar_m * 100 - 2 * hook_len_cm
            fig_l1_mem = draw_longitudinal_bar(long_bar_m*100, straight_len_cm, hook_len_cm, rebar_diam, _bar_label(rebar_diam))
            l1_img = io.BytesIO()
            fig_l1_mem.savefig(l1_img, format='png', dpi=150, bbox_inches='tight')
            l1_img.seek(0)
            doc.add_picture(l1_img, width=Inches(5))
            inside_b = b - 2 * recub_cm
            inside_h = h - 2 * recub_cm
            hook_len_est = 12 * stirrup_diam / 10
            fig_e1_mem = draw_stirrup(inside_b, inside_h, hook_len_est, stirrup_diam, _bar_label(stirrup_diam))
            e1_img = io.BytesIO()
            fig_e1_mem.savefig(e1_img, format='png', dpi=150, bbox_inches='tight')
            e1_img.seek(0)
            doc.add_picture(e1_img, width=Inches(4))
        doc.add_heading("11. CANTIDADES DE OBRA", level=1)
        doc.add_paragraph(f"Concreto: {vol_concreto_m3:.4f} m³\nAcero total: {peso_total_acero_kg:.1f} kg\nRelación acero/concreto: {peso_total_acero_kg/vol_concreto_m3:.1f} kg/m³")
        doc.add_heading("FIRMA Y SELLO DEL INGENIERO RESPONSABLE", level=1)
        doc.add_paragraph(" ")
        doc.add_paragraph(" ")
        doc.add_paragraph("_________________________________________")
        doc.add_paragraph("Ing. Msc. César Augusto Giraldo Chaparro")
        doc.add_paragraph("Matrícula Profesional: _______________")
        doc_mem = io.BytesIO()
        doc.save(doc_mem)
        doc_mem.seek(0)
        st.success(_t("✅ Memoria generada exitosamente.", "✅ Report generated successfully."))
        st.download_button(label=_t("📥 Descargar Memoria DOCX", "📥 Download DOCX Report"),
                           data=doc_mem, file_name=f"Memoria_Columna_{b:.0f}x{h:.0f}_{datetime.datetime.now().strftime('%Y%m%d')}.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    
    st.markdown("---")
    st.subheader(_t("📊 Exportar Verificaciones a Excel", "📊 Export Verifications to Excel"))
    if st.button(_t("📥 Exportar a Excel", "📥 Export to Excel")):
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df_verif = pd.DataFrame({
                "Verificación": ["Cuantía", "Biaxial", "Esbeltez", "Ash", "Lo", "Separación"],
                "Valor": [f"{cuantia:.2f}%", f"{bresler['ratio']:.3f}", f"{slenderness['kl_r']:.1f}", 
                          f"{Ash_prov:.3f}/{Ash_req:.3f}" if not es_circular else f"{rho_s_prov:.4f}/{rho_s_req:.4f}",
                          f"{Lo_conf:.1f}" if not es_circular else "N/A", f"{s_conf:.1f}" if not es_circular else f"{paso_espiral:.1f}"],
                "Límite": [f"{rho_min}% - {rho_max}%", "≤ 1.0", "≤ 22", "≥ 1.0", "≥ max(b,h,L/6,45)", "≤ 15/20"],
                "Cumple": ["SÍ" if rho_min <= cuantia <= rho_max else "NO",
                           "SÍ" if bresler['ok'] else "NO",
                           "SÍ" if slenderness['kl_r'] <= 22 else "NO",
                           "SÍ" if ash_ok else "NO",
                           "SÍ" if (es_des or es_dmo) and Lo_conf >= max(b,h,L_col/6,45) else "SÍ" if not (es_des or es_dmo) else "NO",
                           "SÍ" if (es_des and s_conf <= 15) or (es_dmo and s_conf <= 20) or es_dmi else "NO"]
            })
            df_verif.to_excel(writer, sheet_name='Verificaciones', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Verificaciones']
            green_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
            red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            for row, val in enumerate(df_verif["Cumple"], start=2):
                cell = f"D{row}"
                if val == "SÍ":
                    worksheet.write(cell, val, green_format)
                else:
                    worksheet.write(cell, val, red_format)
            df_despiece.to_excel(writer, sheet_name='Despiece', index=False)
            df_cant = pd.DataFrame({
                "Material": ["Concreto", "Acero Longitudinal", "Acero Estribos", "Acero Total"],
                "Cantidad": [vol_concreto_m3, peso_acero_long_kg, peso_total_estribos_kg, peso_total_acero_kg],
                "Unidad": ["m³", "kg", "kg", "kg"]
            })
            df_cant.to_excel(writer, sheet_name='Cantidades', index=False)
        excel_buffer.seek(0)
        st.download_button(label=_t("📥 Descargar Excel", "📥 Download Excel"),
                           data=excel_buffer, file_name=f"Verificaciones_Columna_{b:.0f}x{h:.0f}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")