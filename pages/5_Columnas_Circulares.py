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

st.set_page_config(page_title=_t("Columnas Circulares P-M", "Circular Columns P-M"), layout="wide")

st.image(r"C:\Users\cagch\.gemini\antigravity\brain\d408b5ad-3eb5-4039-b011-4650dd509d7e\circular_concrete_column_header_1773322766287.png", use_container_width=False, width=700)
st.title(_t("Diagrama P-M para Columnas Circulares — Multi-Norma", "P-M Diagram for Circular Columns — Multi-Code"))
st.markdown(_t("Generación del diagrama de interacción **P–M** para columnas circulares de concreto reforzado. Soporta normativa de **Colombia, EE.UU., Ecuador, Perú, México, Venezuela, Bolivia y Argentina**.", "Generation of the **P-M** interaction diagram for reinforced concrete circular columns. Supports codes from **Colombia, USA, Ecuador, Peru, Mexico, Venezuela, Bolivia and Argentina**."))
with st.expander(_t("📺 ¿Cómo usar esta herramienta?", "📺 How to use this tool?")):
    st.markdown(_t("""
    **Modo de Uso:**
    1. **📍 Sidebar (Menú Izquierdo):** Selecciona la Norma de tu país, el nivel sísmico, y las propiedades del concreto y el acero.
    2. **🏗️ Geometría y Armadura:** Define el Diámetro D de la columna, el diámetro de varilla y cantidad total de varillas longitudinales. El acero se distribuirá simétricamente en el perímetro.
    3. **🚦 Solicitaciones:** Ingresa el Momento Último (Mu) y la Carga Axial (Pu) solicitantes.
    4. **📊 P-M:** Revisa que el punto verde de solicitación quede DENTRO de la curva roja (Resistencia de Diseño).
    """, """
    **How to use:**
    1. **📍 Sidebar (Left Menu):** Select the Country Code, seismic level, and concrete and steel properties.
    2. **🏗️ Geometry and Reinforcement:** Define Column Diameter D, rebar diameter and total number of longitudinal rebars. Steel will be distributed symmetrically on the perimeter.
    3. **🚦 Demands:** Enter the required Ultimate Moment (Mu) and Axial Load (Pu).
    4. **📊 P-M:** Check that the green demand point falls INSIDE the red curve (Design Strength).
    """))

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
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 4.0, "eps_tension_full": 0.005, "ref": "NSR-10 Título C"
    },
    "ACI 318-25 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0, "eps_tension_full": 0.005, "ref": "ACI 318-25"
    },
    "ACI 318-19 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0, "eps_tension_full": 0.005, "ref": "ACI 318-19"
    },
    "ACI 318-14 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0, "eps_tension_full": 0.005, "ref": "ACI 318-14"
    },
    "NEC-SE-HM (Ecuador)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0, "eps_tension_full": 0.005, "ref": "NEC-SE-HM (Ecuador)"
    },
    "E.060 (Perú)": {
        "phi_tied": 0.70, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 6.0, "eps_tension_full": 0.005, "ref": "Norma E.060 (Perú)"
    },
    "NTC-EM (México)": {
        "phi_tied": 0.70, "phi_spiral": 0.80, "phi_tension": 0.85, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 6.0, "eps_tension_full": 0.005, "ref": "NTC-EM México"
    },
    "COVENIN 1753-2006 (Venezuela)": {
        "phi_tied": 0.70, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 6.0, "eps_tension_full": 0.005, "ref": "COVENIN 1753-2006 (Venezuela)"
    },
    "NB 1225001-2020 (Bolivia)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0, "eps_tension_full": 0.005, "ref": "NB 1225001-2020 (Bolivia)"
    },
    "CIRSOC 201-2025 (Argentina)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90, "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max": 8.0, "eps_tension_full": 0.005, "ref": "CIRSOC 201-2025 (Argentina)"
    },
}

# ─────────────────────────────────────────────
# INPUTS
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
    f'</div>', unsafe_allow_html=True
)
code = CODES[norma_sel]

st.sidebar.header(_t("1. Materiales", "1. Materials"))
fc_unit = st.sidebar.radio(_t("Unidad de f'c:", "f'c Unit:"), ["MPa", "PSI", "kg/cm²"], horizontal=True, key="circ_fc_unit")
if fc_unit == "PSI":
    fc_psi = st.sidebar.number_input("f'c [PSI]", 2000.0, 12000.0, st.session_state.get("circ_fc_psi", 4000.0), 100.0, key="circ_fc_psi")
    fc = fc_psi * 0.00689476
elif fc_unit == "kg/cm²":
    fc_kgcm2 = st.sidebar.number_input("f'c [kg/cm²]", 100.0, 1200.0, st.session_state.get("circ_fc_kgcm2", 280.0), 10.0, key="circ_fc_kgcm2")
    fc = fc_kgcm2 / 10.1972
else:
    fc = st.sidebar.number_input(_t("Resistencia del Concreto (f'c) [MPa]", "Concrete Strength (f'c) [MPa]"), 15.0, 80.0, st.session_state.get("circ_fc_mpa", 28.0), 1.0, key="circ_fc_mpa")
fy = st.sidebar.number_input(_t("Fluencia del Acero (fy) [MPa]", "Steel Yield (fy) [MPa]"), 240.0, 500.0, st.session_state.get("circ_fy", 420.0), 10.0, key="circ_fy")
Es = 200000.0

st.sidebar.header(_t("2. Geometría", "2. Geometry"))
D_col = st.sidebar.number_input(_t("Diámetro Exterior (D) [cm]", "Outer Diameter (D) [cm]"), min_value=20.0, value=st.session_state.get("circ_D", 60.0), step=5.0, key="circ_D")
recub = st.sidebar.number_input(_t("Recubrimiento Libre (al estribo) [cm]", "Clear cover (to tie) [cm]"), min_value=1.5, value=st.session_state.get("circ_recub", 4.0), step=0.5, key="circ_recub")
L_col = st.sidebar.number_input(_t("Altura libre columna (L) [cm]", "Clear column height (L) [cm]"), min_value=50.0, value=st.session_state.get("circ_L", 300.0), step=25.0, key="circ_L")

st.sidebar.header(_t("3. Refuerzo Longitudinal", "3. Longitudinal Reinforcement"))
unit_system = st.sidebar.radio(_t("Sistema de Varillas:", "Rebar System:"), 
                               ["Pulgadas (EE. UU.)", "Milímetros (SI)"] if lang == "Español" else ["Inches (US)", "Millimeters (SI)"],
                               key="circ_unit_system")
rebar_dict = REBAR_US if "Pulgadas" in unit_system or "Inches" in unit_system else REBAR_MM
default_rebar = "#6 (3/4\")" if "Pulgadas" in unit_system or "Inches" in unit_system else "20 mm"
rebar_type = st.sidebar.selectbox(_t("Diámetro de Varillas Long.", "Longitudinal Rebars Dia."), list(rebar_dict.keys()), 
                                 index=list(rebar_dict.keys()).index(st.session_state.circ_rebar_type) if "circ_rebar_type" in st.session_state and st.session_state.circ_rebar_type in rebar_dict else list(rebar_dict.keys()).index(default_rebar),
                                 key="circ_rebar_type")
rebar_area  = rebar_dict[rebar_type]["area"]    # cm²
rebar_diam  = rebar_dict[rebar_type]["diam_mm"] # mm

n_barras_total = st.sidebar.number_input("Total de Varillas", min_value=4, max_value=40, value=st.session_state.get("circ_n_bars", 8), step=1, key="circ_n_bars")
Ast = n_barras_total * rebar_area # cm²
Ag = math.pi * (D_col / 2.0)**2     # cm²

st.sidebar.header(_t("4. Estribo / Zuncho", "4. Tie / Spiral"))
stirrup_dict = STIRRUP_US if "Pulgadas" in unit_system or "Inches" in unit_system else STIRRUP_MM
default_stirrup = "#3 (3/8\")" if "Pulgadas" in unit_system or "Inches" in unit_system else "10 mm"
stirrup_type = st.sidebar.selectbox(_t("Diámetro del Estribo/Espiral", "Tie/Spiral Diameter"), list(stirrup_dict.keys()), 
                                   index=list(stirrup_dict.keys()).index(st.session_state.circ_stirrup_type) if "circ_stirrup_type" in st.session_state and st.session_state.circ_stirrup_type in stirrup_dict else list(stirrup_dict.keys()).index(default_stirrup),
                                   key="circ_stirrup_type")
stirrup_area = stirrup_dict[stirrup_type]["area"]     # cm²
stirrup_diam = stirrup_dict[stirrup_type]["diam_mm"]  # mm

col_type_options = ["Espiral (Zunchada)", "Estribos (Tied)"] if lang == "Español" else ["Spiral", "Tied"]
col_type = st.sidebar.selectbox(_t("Tipo de Confinamiento", "Confinement Type"), 
                                col_type_options,
                                index=col_type_options.index(st.session_state.circ_col_type) if "circ_col_type" in st.session_state and st.session_state.circ_col_type in col_type_options else 0,
                                key="circ_col_type")
if "Estrib" in col_type or "Tied" in col_type:
    phi_c_max  = code["phi_tied"]
    p_max_factor = code["pmax_tied"]
else:
    phi_c_max  = code["phi_spiral"]
    p_max_factor = code["pmax_spiral"]
phi_tension   = code["phi_tension"]

st.sidebar.header(_t("5. Verificación", "5. Demands"))
M_u_input = st.sidebar.number_input(_t("Momento Último (Mu) [kN-m]", "Ultimate Moment (Mu) [kN-m]"), value=st.session_state.get("circ_mu", 100.0), step=10.0, key="circ_mu")
P_u_input = st.sidebar.number_input(_t("Carga Axial Última (Pu) [kN]", "Ultimate Axial Load (Pu) [kN]"), value=st.session_state.get("circ_pu", 800.0), step=50.0, key="circ_pu")

# ─────────────────────────────────────────────
# CÁLCULOS P-M
# ─────────────────────────────────────────────
eps_cu = 0.003
eps_y  = fy / Es

if fc <= 28:
    beta_1 = 0.85
elif fc < 55:
    beta_1 = 0.85 - 0.05 * (fc - 28) / 7.0
else:
    beta_1 = 0.65
beta_1 = max(beta_1, 0.65)

D_mm = D_col * 10
R_mm = D_mm / 2.0
As_mm2 = rebar_area * 100

Po_kN = (0.85 * fc * (Ag * 100 - Ast * 100) + fy * Ast * 100) / 1000.0

# Posiciones de las barras
Rs_mm = R_mm - (recub * 10) - stirrup_diam - (rebar_diam / 2.0)
# Distribución polar a lo largo de 360°, la primera barra en el top (y=R_s)
bar_y_pos = [] # y respecto al centro de la circunferencia
for i in range(n_barras_total):
    theta_i = (2 * math.pi * i) / n_barras_total
    bar_y_pos.append(Rs_mm * math.cos(theta_i)) # Positive is UP

c_vals = np.concatenate([np.linspace(1e-5, D_col, 120), np.linspace(D_col, D_col * 12, 60)])
P_n_list = []; M_n_list = []; phi_P_n_list = []; phi_M_n_list = []

for c_cm in c_vals:
    c_mm = c_cm * 10
    a_mm = min(beta_1 * c_mm, D_mm)
    
    # Concrete segment area & centroid (Integration approach or closed form)
    d_c = R_mm - a_mm  # distance from center to chord. 
    if d_c >= R_mm:
        Ac = 0.0; yc = 0.0
    elif d_c <= -R_mm:
        Ac = math.pi * R_mm**2; yc = 0.0
    else:
        alpha = math.acos(d_c / R_mm)
        Ac = R_mm**2 * (alpha - math.sin(alpha) * math.cos(alpha)) # mm2
        yc = (2 * R_mm**3 * math.sin(alpha)**3) / (3 * Ac) if Ac > 0 else 0 # mm (distance from center, towards top)
    
    Cc = 0.85 * fc * Ac  # N
    Mc = Cc * yc         # N·mm
    
    Ps = 0.0; Ms = 0.0; eps_t = 0.0
    for yi in bar_y_pos:
        di = R_mm - yi # distance from top compression fiber to bar i
        eps_s = eps_cu * (c_mm - di) / c_mm
        
        # Max tension strain for phi calculation is the bar furthest from compression fiber
        # which is at yi = -Rs_mm (bottom) => dt = R_mm + Rs_mm
        dt_max = R_mm + Rs_mm
        eps_t_bar = eps_cu * (c_mm - dt_max) / c_mm
        eps_t = eps_t_bar # track strain at extreme tension steel
        
        fs = max(-fy, min(fy, Es * eps_s))
        if a_mm > di and fs > 0:
            fs -= 0.85 * fc # deduct concrete replaced by steel in compression block
        Ps += As_mm2 * fs
        Ms += As_mm2 * fs * yi # moment about center
        
    Pn = (Cc + Ps) / 1000.0  # kN
    Mn = abs((Mc + Ms) / 1_000_000.0)  # kN·m
    
    eps_t_tens = -eps_t
    if eps_t_tens <= eps_y:
        phi = phi_c_max
    elif eps_t_tens >= code["eps_tension_full"]:
        phi = phi_tension
    else:
        phi = phi_c_max + (phi_tension - phi_c_max) * (eps_t_tens - eps_y) / (code["eps_tension_full"] - eps_y)
        
    Pn_max_val = p_max_factor * Po_kN
    phi_Pn_max_val = phi_c_max * Pn_max_val

    Pn    = min(Pn, Pn_max_val)
    phi_Pn = min(phi * Pn, phi_Pn_max_val)
    phi_Mn = phi * Mn

    P_n_list.append(Pn); M_n_list.append(Mn)
    phi_P_n_list.append(phi_Pn); phi_M_n_list.append(phi_Mn)

P_n_arr = np.array(P_n_list); M_n_arr = np.array(M_n_list)
phi_P_n_arr = np.array(phi_P_n_list); phi_M_n_arr = np.array(phi_M_n_list)

Pt = -fy * Ast * 100 / 1000.0
Pn_max = p_max_factor * Po_kN
phi_Pn_max_disp = phi_c_max * Pn_max

# ─────────────────────────────────────────────
# CANTIDADES DE MATERIALES
# ─────────────────────────────────────────────
vol_concreto_m3 = (math.pi*(D_col/100)**2/4) * (L_col/100)
peso_acero_long_kg = Ast * (L_col*10) * 7.85e-3 # kg
# Estribos en espiral o anillos
perim_estribo_cm = math.pi * (D_col - 2*recub)
n_estribos = math.ceil(L_col / 15.0) + 1 # estribos aprox @ 15cm para calculo base rapido
# Si es zuncho, la longitud es una espiral continua L = pi*D_e / s_espacio. Aproximaremos asumiendo anillos
longitud_total_estr = perim_estribo_cm/100 * n_estribos
peso_total_estr = longitud_total_estr * stirrup_area*100 * 7.85e-3
peso_total_acero_kg = peso_acero_long_kg + peso_total_estr
relacion_acero_kg_m3 = peso_total_acero_kg / vol_concreto_m3 if vol_concreto_m3 > 0 else 0

cuantia = Ast / Ag * 100

# ─────────────────────────────────────────────
# LAYOUT 
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Diagrama P–M", "🔲 Sección Transversal", "📦 Costos (APU) y Cantidades"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"Gráfica P–M — {norma_sel}")
        fig, ax = plt.subplots(figsize=(8, 6))

        idx_M_nom = np.argmax(M_n_arr); M_nom_max = M_n_arr[idx_M_nom]; P_at_Mnom = P_n_arr[idx_M_nom]
        idx_M_dis = np.argmax(phi_M_n_arr); M_dis_max = phi_M_n_arr[idx_M_dis]

        ax.plot(M_n_arr, P_n_arr, label=r"Resistencia Nominal ($P_n, M_n$)", color="blue", linestyle="--")
        ax.plot(phi_M_n_arr, phi_P_n_arr, label=r"Resistencia de Diseño ($\phi P_n, \phi M_n$)", color="red", linewidth=2)
        ax.plot(M_u_input, P_u_input, 'o', markersize=9, color='lime', markeredgecolor='black', zorder=6, label="Punto de Diseño (Mu, Pu)")
        
        ax.annotate(f"{Pn_max:.0f} kN", xy=(0, Pn_max), xytext=(5, 5), textcoords="offset points", color='blue')
        ax.annotate(f"{phi_Pn_max_disp:.0f} kN", xy=(0, phi_Pn_max_disp), xytext=(5, -15), textcoords="offset points", color='red')
        ax.annotate(f"[{M_u_input:g} kN·m : {P_u_input:g} kN]", xy=(M_u_input, P_u_input), xytext=(6, 6), textcoords="offset points", color='green', weight='bold')
        
        ax.plot([M_nom_max, M_nom_max], [0, P_at_Mnom], color='gray', linestyle='--', alpha=0.5)
        ax.plot([M_dis_max, M_dis_max], [0, phi_P_n_arr[idx_M_dis]], color='gray', linestyle='--', alpha=0.5)

        ax.axhline(0, color='black', linewidth=1)
        ax.set_xlabel("Momento Flector M [kN·m]")
        ax.set_ylabel("Carga Axial P [kN]")
        ax.set_xlim(left=0)
        ax.set_title(f"Columna Circular Ø{D_col:.0f} cm | f'c={fc:.1f} MPa | {n_barras_total} varillas {rebar_type}")
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend()
        st.pyplot(fig)

    with col2:
        st.subheader("Resumen de Diseño")
        st.markdown(f"**Norma:** {norma_sel}")
        st.write(f"**Cuantía ρ:** {cuantia:.2f}%")
        st.markdown(r"**Verificación Normativa:** $\rho_{min} \le \rho \le \rho_{max}$")
        if code["rho_min"] <= cuantia <= code["rho_max"]:
            st.success(f"✅ Aprobado Cuantía: {code['rho_min']:.1f}% $\\le$ {cuantia:.2f}% $\\le$ {code['rho_max']:.1f}%")
        elif cuantia > code["rho_max"]:
            st.error(f"❌ No Aprobado por Cuantía Máxima: $\\rho = {cuantia:.2f}\% > \\rho_{{max}} = {code['rho_max']:.1f}\%$ $\\rightarrow$ **Aumentar Diámetro D**")
        else:
            st.error(f"❌ No Aprobado por Cuantía Mínima: $\\rho = {cuantia:.2f}\% < \\rho_{{min}} = {code['rho_min']:.1f}\%$ $\\rightarrow$ **Aumentar acero longitudinal**")
        
        st.markdown(f"**Capacidad Máxima Pn,máx:** {Pn_max:.0f} kN")
        st.markdown(f"**Resistencia de Diseño φPn,máx:** {phi_Pn_max_disp:.0f} kN")
        st.markdown("---")
        st.metric("As Total Provisto", f"{Ast:.2f} cm²")

with tab2:
    st.subheader("🧊 Visualización 3D en Tiempo Real")
    fig3d = go.Figure()

    # Creacion del cilindro de concreto
    R_cm = D_col / 2.0
    z_c_top = L_col
    z_c_bot = 0
    theta_3d = np.linspace(0, 2 * np.pi, 24)
    x_c = R_cm * np.cos(theta_3d)
    y_c = R_cm * np.sin(theta_3d)

    # Mesh lateral top/bottom
    x_mesh = np.concatenate([x_c, x_c])
    y_mesh = np.concatenate([y_c, y_c])
    z_mesh = np.concatenate([np.full(24, z_c_bot), np.full(24, z_c_top)])
    i_idx, j_idx, k_idx = [], [], []
    for i in range(23):
        i_idx.extend([i, i+1, i+24])
        j_idx.extend([i+1, i+25, i+25])
        k_idx.extend([i+24, i+24, i+1])
    i_idx.extend([23, 0, 47])
    j_idx.extend([0, 24, 24])
    k_idx.extend([47, 47, 0])

    fig3d.add_trace(go.Mesh3d(x=x_mesh, y=y_mesh, z=z_mesh, i=i_idx, j=j_idx, k=k_idx, 
                              alphahull=-1, opacity=0.15, color='gray', name='Concreto'))

    # Lineas varillas
    diam_reb_cm = rebar_diam / 10.0 # mm to cm
    line_width = max(4, diam_reb_cm * 3)
    
    for yi, theta in zip(bar_y_pos, [i*2*math.pi/n_barras_total for i in range(n_barras_total)]):
        xi = Rs_mm/10 * math.cos(theta)  # Corrected geometry from sin back to cos for x, depending on y = R*sin(theta)
        yi_cm = Rs_mm/10 * math.sin(theta) 
        fig3d.add_trace(go.Scatter3d(x=[xi, xi], y=[yi_cm, yi_cm], z=[z_c_bot, z_c_top], 
                                     mode='lines', line=dict(color='darkred', width=line_width), name=f'Varilla'))

    # Spiral (Espiral/Estribo)
    tie_color = 'cornflowerblue'
    tie_width = max(2, (9.5/10.0) * 3)
    z_spiral = np.linspace(0, z_c_top, 200) # 200 points for spiral
    Rs_ext = R_cm - recub # Radio externo estetico para estribo
    x_spiral = Rs_ext * np.cos(z_spiral * 2 * np.pi / 20.0) # 1 loop every 20cm approx
    y_spiral = Rs_ext * np.sin(z_spiral * 2 * np.pi / 20.0)
    
    fig3d.add_trace(go.Scatter3d(x=x_spiral, y=y_spiral, z=z_spiral, mode='lines',
                                 line=dict(color=tie_color, width=tie_width), name='Espiral', showlegend=True))

    fig3d.update_layout(scene=dict(aspectmode='data', xaxis_title='X (cm)', yaxis_title='Y (cm)', zaxis_title='L (cm)'),
                        margin=dict(l=0, r=0, b=0, t=0), height=450, showlegend=False, dragmode='turntable')
    st.plotly_chart(fig3d, use_container_width=True)
    st.markdown("---")

    st.subheader("Sección Transversal 2D")
    fig_s, ax_s = plt.subplots(figsize=(5,5))
    ax_s.set_facecolor('#1a1a2e'); fig_s.patch.set_facecolor('#1a1a2e')
    # Concrete Outer Circle
    ax_s.add_patch(plt.Circle((0,0), D_col/2, edgecolor='white', facecolor='#4a4a6a', lw=2))
    # Spiral/Tie
    ax_s.add_patch(plt.Circle((0,0), D_col/2 - recub, edgecolor='#00d4ff', facecolor='none', lw=2, linestyle='--'))
    # Rebars
    for yi, theta in zip(bar_y_pos, [i*2*math.pi/n_barras_total for i in range(n_barras_total)]):
        xi = Rs_mm/10 * math.sin(theta)
        ax_s.add_patch(plt.Circle((xi, yi/10), rebar_diam/20, color='#ff6b35', zorder=5))
        
    ax_s.annotate('', xy=(-D_col/2, -D_col/2-5), xytext=(D_col/2, -D_col/2-5), arrowprops=dict(arrowstyle='<->', color='white'))
    ax_s.text(0, -D_col/2-8, f"Ø Exterior = {D_col:.0f} cm", color='white', ha='center', va='top')
    
    ax_s.set_xlim(-D_col/2-10, D_col/2+10)
    ax_s.set_ylim(-D_col/2-10, D_col/2+10)
    ax_s.set_aspect('equal')
    ax_s.axis('off')
    st.pyplot(fig_s)
    
    st.markdown("---")
    st.markdown("#### 💾 Exportar Plano (AutoCAD DXF)")
    doc_dxf = ezdxf.new('R2010')
    doc_dxf.units = ezdxf.units.CM
    msp = doc_dxf.modelspace()
    msp.add_circle((0,0), D_col/2, dxfattribs={'color': 7, 'layer': 'CONCRETO'})
    msp.add_circle((0,0), D_col/2 - recub, dxfattribs={'color': 4, 'layer': 'ESTRIBOS'})
    for yi, theta in zip(bar_y_pos, [i*2*math.pi/n_barras_total for i in range(n_barras_total)]):
        xi = Rs_mm/10 * math.sin(theta)
        msp.add_circle((xi, yi/10), rebar_diam/20, dxfattribs={'color': 1, 'layer': 'VARILLAS'})
        
    out_stream = io.StringIO()
    doc_dxf.write(out_stream)
    st.download_button(label="Descargar Dibujo DXF", data=out_stream.getvalue(), file_name=f"Columna_Circular_D{D_col:.0f}cm.dxf", mime="application/dxf")

with tab3:
    st.subheader(f"📦 Cantidades de Materiales y Costos")
    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.metric("Volumen Concreto", f"{vol_concreto_m3:.3f} m³")
    col_c2.metric("Peso Total Acero", f"{peso_total_acero_kg:.1f} kg")
    col_c3.metric("Ratio de Acero", f"{relacion_acero_kg_m3:.1f} kg/m³")

    if "apu_config" in st.session_state:
        st.markdown("---")
        st.markdown("### 💰 Presupuesto APU (En Vivo)")
        apu = st.session_state.apu_config
        mon = apu["moneda"]
        # Interpolacion cemento basica (usando sacos de 50kg)
        bultos_col = vol_concreto_m3 * 350 / 50.0 # asumiendo aprox 350 kg/m3 para 21-28 MPa
        vol_arena = vol_concreto_m3 * 0.5
        vol_grava = vol_concreto_m3 * 0.7
        
        c_cem = bultos_col * apu["cemento"]
        c_ace = peso_total_acero_kg * apu["acero"]
        c_are = vol_arena * apu["arena"]
        c_gra = vol_grava * apu["grava"]
        total_mat = c_cem + c_ace + c_are + c_gra
        
        # MO
        total_dias_mo = (peso_total_acero_kg * 0.04) + (vol_concreto_m3 * 0.4)
        costo_mo = total_dias_mo * apu.get("costo_dia_mo", 69333.33)
        
        # Indirectos
        costo_directo = total_mat + costo_mo
        herramienta = costo_mo * apu.get("pct_herramienta", 0.05)
        aiu = costo_directo * apu.get("pct_aui", 0.30)
        utilidad = costo_directo * apu.get("pct_util", 0.05)
        iva = utilidad * apu.get("iva", 0.19)
        
        total_proyecto = costo_directo + herramienta + aiu + iva
        
        data_apu = {
            "Item": ["Cemento (bultos)", "Acero (kg)", "Arena (m³)", "Grava (m³)", 
                     "Mano de Obra (días)", "Herramienta Menor", "A.I.U.", "IVA s/Utilidad", "TOTAL PRESUPUESTO"],
            "Cantidad": [f"{bultos_col:.1f}", f"{peso_total_acero_kg:.1f}", f"{vol_arena:.2f}", f"{vol_grava:.2f}", 
                         f"{total_dias_mo:.2f}", f"{apu.get('pct_herramienta', 0.05)*100:.1f}% MO", 
                         f"{apu.get('pct_aui', 0.3)*100:.1f}% CD", f"{apu.get('iva', 0.19)*100:.1f}% Util", ""],
            f"Subtotal [{mon}]": [f"{c_cem:,.2f}", f"{c_ace:,.2f}", f"{c_are:,.2f}", f"{c_gra:,.2f}", 
                                  f"{costo_mo:,.2f}", f"{herramienta:,.2f}", f"{aiu:,.2f}", f"{iva:,.2f}", f"**{total_proyecto:,.2f}**"]
        }
        st.dataframe(pd.DataFrame(data_apu), use_container_width=True, hide_index=True)
        
        # Excel
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df_export = pd.DataFrame({
                "Item": ["Cemento", "Acero", "Arena", "Grava", "Mano de Obra"],
                "Cantidad": [bultos_col, peso_total_acero_kg, vol_arena, vol_grava, total_dias_mo],
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
        st.download_button(label="📥 Descargar Presupuesto Excel (.xlsx)", data=output_excel, 
                           file_name=f"APU_ColumnaCirc_D{D_col:.0f}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("💡 Ve a la página 'APU Mercado' en la barra lateral para calcular presupuestos.")

    st.markdown("---")
    st.markdown("#### 📄 Generar Memoria de Cálculo (DOCX)")
    doc_word = Document()
    doc_word.add_heading(f"Memoria de Cálculo — Columna Circular Ø{D_col:.0f} cm", 0)
    doc_word.add_paragraph(f"Norma Utilizada: {norma_sel}")
    doc_word.add_heading("Resultados", level=1)
    doc_word.add_paragraph(f"Capacidad Axial Máx Pn,máx: {Pn_max:.1f} kN\nResistencia de Diseño φPn,máx: {phi_Pn_max_disp:.1f} kN\nCuantía ρ: {cuantia:.2f}%")
    f_io = io.BytesIO()
    doc_word.save(f_io)
    f_io.seek(0)
    st.download_button(label="Descargar Memoria DOCX", data=f_io, file_name=f"Memoria_Circular_D{D_col:.0f}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

