import streamlit as st
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import math
import io
import ezdxf
from docx import Document
from docx.shared import Inches, Pt
from datetime import datetime

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es

st.set_page_config(page_title=_t("Predimensionamiento Estructural", "Structural Predimensioning"), layout="wide")

st.markdown('<div style="background-color:#1a1a2e;padding:15px;border-radius:10px;text-align:center;"><h1 style="color:#d9a05b;">🏗️ ' + _t("Predimensionamiento Estructural 3D", "3D Structural Predimensioning") + '</h1></div>', unsafe_allow_html=True)

st.markdown(_t("Módulo multinorma para estimar las secciones preliminares de Losas, Vigas y Columnas en base a tributación de cargas, número de pisos y zonas sísmicas. Generación de modelos 3D y memorias de cálculo.", 
               "Multi-code module to estimate preliminary sections for Slabs, Beams, and Columns based on tributary areas, number of stories, and seismic zones. 3D models and calculation memory generation."))

# ─────────────────────────────────────────────
# CONFIGURACIÓN LATERAL
norma_sel = st.session_state.get("norma_sel", "NSR-10 (Colombia)")
_PAIS_ISO = {"NSR-10 (Colombia)":"co","ACI 318-25 (EE.UU.)":"us","ACI 318-19 (EE.UU.)":"us","ACI 318-14 (EE.UU.)":"us","NEC-SE-HM (Ecuador)":"ec","E.060 (Perú)":"pe","NTC-EM (México)":"mx","COVENIN 1753-2006 (Venezuela)":"ve","NB 1225001-2020 (Bolivia)":"bo","CIRSOC 201-2025 (Argentina)":"ar"}
_iso = _PAIS_ISO.get(norma_sel, "un")
st.sidebar.markdown(f'<div style="background:#1e3a1e;border-radius:6px;padding:8px;margin-bottom:10px;"><img src="https://flagcdn.com/24x18/{_iso}.png" style="vertical-align:middle;margin-right:8px;"><span style="color:#7ec87e;font-weight:600;">{_t("Normativa Activa:","Code:")} {norma_sel}</span></div>', unsafe_allow_html=True)

# Unidades de salida (kN / tonf)
st.sidebar.header(_t("📊 Unidades de salida","📊 Output units"))
unidades_salida = st.sidebar.radio("Unidades de fuerza/momento:", ["kiloNewtons (kN, kN·m)", "Toneladas fuerza (tonf, tonf·m)"], key="pred_units")
if unidades_salida == "Toneladas fuerza (tonf, tonf·m)":
    factor_fuerza = 0.1019716
    unidad_fuerza = "tonf"
    unidad_mom    = "tonf·m"
else:
    factor_fuerza = 1.0
    unidad_fuerza = "kN"
    unidad_mom    = "kN·m"

with st.sidebar.expander(_t("1️⃣ GEOMETRÍA DEL PROYECTO", "1️⃣ PROJECT GEOMETRY"), expanded=True):
    num_stories = st.number_input(_t("Número de Pisos", "Number of Stories"), 1, 40, 5, 1)
    h_story = st.number_input(_t("Altura típica de entrepiso (m)", "Typical story height (m)"), 2.0, 6.0, 3.0, 0.1)
    lx = st.number_input(_t("Luz entre ejes X (m)", "Clear span X (m)"), 2.0, 15.0, 6.0, 0.1)
    ly = st.number_input(_t("Luz entre ejes Y (m)", "Clear span Y (m)"), 2.0, 15.0, 5.0, 0.1)

with st.sidebar.expander(_t("2️⃣ MATERIALES Y ZONA SÍSMICA", "2️⃣ MATERIALS & SEISMIC"), expanded=True):
    fc_val = st.selectbox(_t("Resistencia f'c (kg/cm²)", "Concrete f'c (kg/cm²)"), [210, 240, 280, 350, 420], index=2)
    fy_val = st.selectbox(_t("Fluencia acero fy (kg/cm²)", "Steel fy (kg/cm²)"), [2800, 4200, 5000], index=1)
    seismic_zone = st.selectbox(_t("Nivel de Amenaza Sísmica", "Seismic Hazard Level"), 
                                [_t("Alta", "High"), _t("Intermedia", "Intermediate"), _t("Baja", "Low")], index=0)
    # Factor α para columnas (ajuste por sismicidad)
    if "Alta" in seismic_zone: alpha_seismic = 0.65
    elif "Intermedia" in seismic_zone: alpha_seismic = 0.725
    else: alpha_seismic = 0.80

with st.sidebar.expander(_t("3️⃣ CARGAS Y USO", "3️⃣ LOADS AND OCCUPANCY"), expanded=True):
    uso_edif = st.selectbox(_t("Uso Principal", "Main Occupancy"), 
                            [_t("Residencial", "Residential"), _t("Oficinas", "Offices"), _t("Comercial", "Commercial"), _t("Almacenamiento", "Storage")])
    if "Residencial" in uso_edif:
        ll_estim = 200; dl_estim = 850
    elif "Oficinas" in uso_edif:
        ll_estim = 250; dl_estim = 900
    elif "Comercial" in uso_edif:
        ll_estim = 500; dl_estim = 950
    else:
        ll_estim = 600; dl_estim = 1000
    
    q_estimado = st.number_input(_t("Carga Total q_u (Tonf/m²)", "Total Approx Load q_u (Tonf/m²)"), 0.5, 3.0, (ll_estim + dl_estim)/1000.0, 0.1)

with st.sidebar.expander(_t("4️⃣ APU – PRECIOS", "4️⃣ APU – PRICES"), expanded=False):
    moneda = st.text_input("Moneda (ej. COP, USD)", value=st.session_state.get("apu_moneda_pred", "COP"), key="apu_moneda_pred")
    col1a, col2a = st.columns(2)
    with col1a:
        precio_cemento = st.number_input("Precio por bulto de cemento", value=st.session_state.get("apu_cemento_pred", 28000.0), step=1000.0, format="%.2f", key="apu_cemento_pred")
        precio_acero = st.number_input("Precio por kg de acero", value=st.session_state.get("apu_acero_pred", 7500.0), step=100.0, format="%.2f", key="apu_acero_pred")
        precio_concreto = st.number_input("Precio m³ concreto", value=st.session_state.get("apu_concreto_pred", 400000.0), step=10000.0, format="%.2f", key="apu_concreto_pred")
    with col2a:
        precio_mo = st.number_input("Costo mano de obra (día)", value=st.session_state.get("apu_mo_pred", 70000.0), step=5000.0, format="%.2f", key="apu_mo_pred")
        pct_herramienta = st.number_input("% Herramienta menor (sobre MO)", value=st.session_state.get("apu_herramienta_pred", 5.0), step=1.0, format="%.1f", key="apu_herramienta_pred") / 100.0
        pct_aui = st.number_input("% A.I.U. (sobre costo directo)", value=st.session_state.get("apu_aui_pred", 30.0), step=5.0, format="%.1f", key="apu_aui_pred") / 100.0
        pct_util = st.number_input("% Utilidad (sobre costo directo)", value=st.session_state.get("apu_util_pred", 5.0), step=1.0, format="%.1f", key="apu_util_pred") / 100.0
        iva = st.number_input("IVA (%) sobre utilidad", value=st.session_state.get("apu_iva_pred", 19.0), step=1.0, format="%.1f", key="apu_iva_pred") / 100.0
    if st.button("Guardar precios APU"):
        st.session_state.apu_config_pred = {
            "moneda": moneda,
            "cemento": precio_cemento,
            "acero": precio_acero,
            "concreto": precio_concreto,
            "costo_dia_mo": precio_mo,
            "pct_herramienta": pct_herramienta,
            "pct_aui": pct_aui,
            "pct_util": pct_util,
            "iva": iva
        }
        st.success("Precios guardados")
        st.rerun()

with st.sidebar.expander(_t("5️⃣ AJUSTE MANUAL DE DIMENSIONES", "5️⃣ MANUAL DIMENSION OVERRIDE"), expanded=False):
    st.caption(_t("Modifique las dimensiones calculadas para realizar verificación manual.", "Override calculated dimensions for manual verification."))
    # Se usan valores guardados en session_state; el módulo los actualiza tras calcular
    man_h_mac = st.number_input(_t("Espesor Losa Maciza (cm)", "Solid Slab h (cm)"), 10, 50, st.session_state.get("_calc_h_mac", 25), 1, key="man_h_mac") / 100.0
    man_h_ali = st.number_input(_t("Espesor Losa Nervada (cm)", "Ribbed Slab h (cm)"), 10, 50, st.session_state.get("_calc_h_ali", 30), 1, key="man_h_ali") / 100.0
    man_bvx   = st.number_input(_t("Viga X – Ancho b (cm)", "Beam X Width b (cm)"), 20, 80, st.session_state.get("_calc_bvx", 25), 5, key="man_bvx") / 100.0
    man_hvx   = st.number_input(_t("Viga X – Peralte h (cm)", "Beam X Depth h (cm)"), 30, 120, st.session_state.get("_calc_hvx", 50), 5, key="man_hvx") / 100.0
    man_bvy   = st.number_input(_t("Viga Y – Ancho b (cm)", "Beam Y Width b (cm)"), 20, 80, st.session_state.get("_calc_bvy", 25), 5, key="man_bvy") / 100.0
    man_hvy   = st.number_input(_t("Viga Y – Peralte h (cm)", "Beam Y Depth h (cm)"), 30, 120, st.session_state.get("_calc_hvy", 45), 5, key="man_hvy") / 100.0
    man_col_c = st.number_input(_t("Columna Central – Lado (cm)", "Central Column Side (cm)"), 20, 120, st.session_state.get("_calc_col_c", 40), 5, key="man_col_c")
    man_col_b = st.number_input(_t("Columna Borde – Lado (cm)", "Edge Column Side (cm)"), 20, 100, st.session_state.get("_calc_col_b", 35), 5, key="man_col_b")
    man_col_e = st.number_input(_t("Columna Esquina – Lado (cm)", "Corner Column Side (cm)"), 20, 80, st.session_state.get("_calc_col_e", 30), 5, key="man_col_e")
    usar_manual = st.checkbox(_t("Usar estas dimensiones en Modelo 3D y Memoria", "Use these in 3D model and Report"), value=False, key="usar_manual")

# Aplicar override si el checkbox está activo (DESPUÉS de los cálculos, se aplica abajo)

st.sidebar.markdown("---")
st.sidebar.markdown("""<div style="text-align: center; color: gray; font-size: 11px;">
    © 2026 Todos los derechos reservados.<br><b>Ing. Msc. César Augusto Giraldo Chaparro</b></div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FUNCIONES DE CÁLCULO MEJORADAS
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# FACTORES MULTI-NORMA
# ─────────────────────────────────────────────
_NORM_FACTORS = {
    # clave: (losa_maciza_div, losa_nerv_div, viga_div_simple, viga_div_continua, col_index, col_ref)
    # col_index = factor en fórmula Pu/(alpha * col_index * fc) — NSR-10/ACI: 0.5525
    "NSR-10 (Colombia)":         (28, 21, 10, 12, 0.5525, "NSR-10 C.9.5.2.1 / C.10.11"),
    "ACI 318-25 (EE.UU.)":       (28, 21, 10, 12, 0.5525, "ACI 318-25 Table 9.3.1.1"),
    "ACI 318-19 (EE.UU.)":       (28, 21, 10, 12, 0.5525, "ACI 318-19 Table 9.3.1.1"),
    "ACI 318-14 (EE.UU.)":       (28, 21, 10, 12, 0.5525, "ACI 318-14 Table 9.3.1.1"),
    "E.060 (Perú)":              (25, 20, 10, 12, 0.5000, "E.060 Art.9.1.2 / 10.11"),
    "NEC-SE-HM (Ecuador)":       (28, 21, 10, 12, 0.5525, "NEC-SE-HM Cap.4 / ACI adoptado"),
    "NTC-EM (México)":           (26, 20, 10, 12, 0.5200, "NTC-EM 2.2.1 / 5.1.1"),
    "COVENIN 1753-2006 (Venezuela)": (28, 21, 10, 12, 0.5525, "COVENIN 1753 Art.15 / ACI adoptado"),
    "NB 1225001-2020 (Bolivia)":  (28, 21, 10, 12, 0.5525, "NB 1225001 / ACI 318 adoptado"),
    "CIRSOC 201-2025 (Argentina)": (28, 21, 10, 12, 0.5525, "CIRSOC 201-2025 / ACI adoptado"),
}
_nf = _NORM_FACTORS.get(norma_sel, _NORM_FACTORS["NSR-10 (Colombia)"])
DIV_LOSA_MAC, DIV_LOSA_NERV, DIV_VIGA_SIMP, DIV_VIGA_CONT, COL_IDX, NORM_REF = _nf

def predimensionar_losa(lmax, tipo="maciza"):
    """Predimensiona losa según norma activa (divisor por norma)"""
    divisor = DIV_LOSA_MAC if tipo == "maciza" else DIV_LOSA_NERV
    h = lmax / float(divisor)
    h = math.ceil(h * 100 / 5) * 5 / 100
    return max(h, 0.10)

def predimensionar_viga(l_luz, posicion="simple"):
    """Predimensiona viga: h = L/divisor, b = h/2.  Divisor segun norma activa."""
    div = float(DIV_VIGA_CONT) if posicion == "continua" else float(DIV_VIGA_SIMP)
    h = math.ceil((l_luz / div) * 100 / 5) * 5 / 100
    b = math.ceil((h / 2.0) * 100 / 5) * 5 / 100
    return max(h, 0.30), max(b, 0.25)

def predimensionar_columna(area_trib, q_tot, n_pisos, alpha, fc):
    """Pu = q_tot * A_trib * n_pisos, Ac = Pu / (COL_IDX * alpha * fc). COL_IDX segun norma."""
    Pu_ton = q_tot * area_trib * n_pisos
    denom = alpha * COL_IDX * fc
    Ac_cm2 = (Pu_ton * 1000.0) / denom if denom > 0 else 400.0
    lado = math.ceil(math.sqrt(Ac_cm2) / 5.0) * 5.0
    return Pu_ton, Ac_cm2, max(lado, 30.0)

def predimensionar_muro_corte(luz_total, h_total, q_tot):
    """Predimensionamiento de muro de corte (espesor mínimo)"""
    # Espesor mínimo = h/20 (NSR-10 C.21.9.6.1)
    t_min = max(h_total / 20.0, 0.15)  # mínimo 15 cm
    # Verificar relación de aspecto
    aspect = luz_total / h_total
    if aspect < 1.0:
        # Muros cortos: se recomienda espesor mayor
        t_min = max(t_min, luz_total / 15.0)
    return t_min

# ─────────────────────────────────────────────
# CÁLCULOS PRINCIPALES
# ─────────────────────────────────────────────
l_max = max(lx, ly)

# Losas
h_mac = predimensionar_losa(l_max, "maciza")
h_ali = predimensionar_losa(l_max, "aligerada")

# Vigas
h_vx, b_vx = predimensionar_viga(lx, "continua")   # viga interior, continua
h_vy, b_vy = predimensionar_viga(ly, "continua")

# Áreas tributarias para columnas
A_central = lx * ly
A_borde = (lx * ly) / 2.0
A_esquina = (lx * ly) / 4.0

# Columnas
Pu_c, Ac_c, lado_c = predimensionar_columna(A_central, q_estimado, num_stories, alpha_seismic, fc_val)
Pu_b, Ac_b, lado_b = predimensionar_columna(A_borde, q_estimado, num_stories, alpha_seismic, fc_val)
Pu_e, Ac_e, lado_e = predimensionar_columna(A_esquina, q_estimado, num_stories, alpha_seismic, fc_val)

# Muro de corte (predimensionamiento para edificios de más de 5 pisos en zona sísmica alta)
if num_stories > 5 and "Alta" in seismic_zone:
    # Considerar un muro de corte central en cada dirección
    t_muro = predimensionar_muro_corte(l_max, num_stories * h_story, q_estimado)
    muro_sugerido = f"Espesor mínimo = {t_muro*100:.0f} cm"
else:
    t_muro = 0.15
    muro_sugerido = "No requerido según criterio preliminar"

# Verificación de deriva máxima (estimación)
# Para zona sísmica alta, se recomienda que el peralte de vigas sea al menos L/12 para control de derivas
deriva_estimada = 0.01 * h_story / (lx / 12.0)  # aproximación muy simple
if deriva_estimada > 0.01:
    warning_deriva = f"⚠️ Deriva estimada {deriva_estimada*100:.2f}% > 1% → considerar vigas más peraltadas"
else:
    warning_deriva = None

# Guardar valores calculados para que el expander manual los use como defaults
st.session_state["_calc_h_mac"] = int(h_mac * 100)
st.session_state["_calc_h_ali"] = int(h_ali * 100)
st.session_state["_calc_bvx"]   = int(b_vx * 100)
st.session_state["_calc_hvx"]   = int(h_vx * 100)
st.session_state["_calc_bvy"]   = int(b_vy * 100)
st.session_state["_calc_hvy"]   = int(h_vy * 100)
st.session_state["_calc_col_c"] = int(lado_c)
st.session_state["_calc_col_b"] = int(lado_b)
st.session_state["_calc_col_e"] = int(lado_e)

# Aplicar override manual si el usuario lo activó
if st.session_state.get("usar_manual", False):
    h_mac  = st.session_state.get("man_h_mac", h_mac)
    h_ali  = st.session_state.get("man_h_ali", h_ali)
    b_vx   = st.session_state.get("man_bvx", b_vx)
    h_vx   = st.session_state.get("man_hvx", h_vx)
    b_vy   = st.session_state.get("man_bvy", b_vy)
    h_vy   = st.session_state.get("man_hvy", h_vy)
    lado_c = st.session_state.get("man_col_c", lado_c)
    lado_b = st.session_state.get("man_col_b", lado_b)
    lado_e = st.session_state.get("man_col_e", lado_e)


# ─────────────────────────────────────────────
def draw_longitudinal_bar(total_len_cm, straight_len_cm, hook_len_cm, bar_diam_mm, bar_name=None):
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
    title = f"Varilla {bar_name or 'L1'} - Ø{bar_diam_mm:.0f} mm - Longitud total {total_len_cm:.0f} cm"
    ax.set_title(title, fontsize=9, fontweight='bold')
    return fig

def draw_stirrup(b_cm, h_cm, hook_len_cm, bar_diam_mm, bar_name=None):
    fig, ax = plt.subplots(figsize=(max(5, b_cm/12), max(4, h_cm/12)))
    ax.set_aspect('equal')
    x0, y0 = 0, 0
    ax.plot([x0, x0+b_cm], [y0, y0], 'k-', linewidth=2.5)
    ax.plot([x0+b_cm, x0+b_cm], [y0, y0+h_cm], 'k-', linewidth=2.5)
    ax.plot([x0+b_cm, x0], [y0+h_cm, y0+h_cm], 'k-', linewidth=2.5)
    ax.plot([x0, x0], [y0+h_cm, y0], 'k-', linewidth=2.5)
    vis_hook = min(hook_len_cm, b_cm/4.0, h_cm/4.0)
    hx = vis_hook * 0.707
    hy = -vis_hook * 0.707
    ax.plot([x0, x0 + hx], [y0+h_cm, y0+h_cm + hy], 'k-', linewidth=2.5)
    ax.annotate(f"Gancho 135°", xy=(x0 + hx + 0.2, y0+h_cm + hy - 0.2), fontsize=7.5, color='darkred')
    ax.annotate(f"{b_cm:.0f} cm", xy=(b_cm/2, y0-0.8), ha='center', fontsize=9)
    ax.annotate(f"{h_cm:.0f} cm", xy=(x0-0.8, h_cm/2), ha='right', va='center', fontsize=9)
    ax.set_xlim(-hook_len_cm*0.3, b_cm + hook_len_cm*0.6)
    ax.set_ylim(-hook_len_cm*0.5, h_cm + hook_len_cm*0.9)
    ax.axis('off')
    title = f"Estribo {bar_name or 'E1'} - Ø{bar_diam_mm:.0f} mm - Perímetro {2*(b_cm+h_cm):.0f} cm"
    ax.set_title(title, fontsize=9, fontweight='bold')
    return fig

# ─────────────────────────────────────────────
# INTERFAZ: PESTAÑAS PRINCIPALES
# ─────────────────────────────────────────────
tab_res, tab_3d, tab_2d, tab_dxf, tab_mem, tab_qty, tab_apu = st.tabs([
    "📊 Resultados", "🧊 Modelo 3D", "📐 Planta 2D", "📏 DXF", "📄 Memoria", "📦 Cantidades", "💰 APU"
])

with tab_res:
    st.subheader(_t("Dimensiones Recomendadas", "Recommended Dimensions"))
    
    # Mostrar advertencia de deriva si aplica
    if warning_deriva:
        st.warning(warning_deriva)
    
    st.markdown("### 🟠 Losas (Slabs)")
    c1, c2 = st.columns(2)
    c1.metric(_t("Espesor Losa Maciza", "Solid Slab Thickness"), f"{h_mac*100:.0f} cm", _t("L/28", "L/28"))
    c2.metric(_t("Espesor Losa Nervada", "Ribbed Slab Thickness"), f"{h_ali*100:.0f} cm", _t("L/21", "L/21"))
    
    st.markdown("### 🟡 Vigas (Beams)")
    c3, c4 = st.columns(2)
    c3.metric(f"Viga X (Luz {lx}m)", f"{b_vx*100:.0f} × {h_vx*100:.0f} cm", "b × h")
    c4.metric(f"Viga Y (Luz {ly}m)", f"{b_vy*100:.0f} × {h_vy*100:.0f} cm", "b × h")
    
    st.markdown("### 🏛️ Columnas (Columns)")
    df_cols = pd.DataFrame({
        _t("Tipo", "Type"): [_t("Central", "Center"), _t("Borde", "Edge"), _t("Esquina", "Corner")],
        _t("Área Trib. (m²)", "Trib Area (m²)"): [f"{A_central:.2f}", f"{A_borde:.2f}", f"{A_esquina:.2f}"],
        _t(f"Pu Estimado ({unidad_fuerza})", f"Estimated Pu ({unidad_fuerza})"): [f"{Pu_c * factor_fuerza:.1f}", f"{Pu_b * factor_fuerza:.1f}", f"{Pu_e * factor_fuerza:.1f}"],
        _t("Sección Sugerida (cm)", "Suggested Section (cm)"): [f"{lado_c:.0f} × {lado_c:.0f}", f"{lado_b:.0f} × {lado_b:.0f}", f"{lado_e:.0f} × {lado_e:.0f}"]
    })
    st.dataframe(df_cols, use_container_width=True, hide_index=True)
    
    st.markdown("### 🧱 Muros de Corte (Shear Walls)")
    st.info(f"**{muro_sugerido}**")
    if t_muro > 0.15:
        st.caption(_t("Para edificios en zonas sísmicas altas con más de 5 pisos se recomienda incorporar muros de corte.", "For high seismic zones with more than 5 stories, shear walls are recommended."))
    
    st.caption(_t("Fórmula de predimensionamiento de columnas basada en factor sísmico empírico (α) e índice de resistencia (0.5525). Las vigas se estiman con peralte L/10 a L/12.", 
                  "Column predimensioning formula based on empirical seismic factor (α) and strength index (0.5525). Beams are estimated with depth L/10 to L/12."))

with tab_3d:
    st.subheader(_t("Modelo 3D - Cuadrícula Típica (3×3 Ejes)", "3D Model - Typical Grid (3×3 Axes)"))
    
    fig3d = go.Figure()
    nx, ny = 2, 2 # number of spans -> 3x3 columns
    
    # Dibujar columnas
    for i in range(nx+1):
        for j in range(ny+1):
            cx = i * lx
            cy = j * ly
            if i in [0, nx] and j in [0, ny]:
                c_size = lado_e/100.0
            elif i in [0, nx] or j in [0, ny]:
                c_size = lado_b/100.0
            else:
                c_size = lado_c/100.0
            
            fig3d.add_trace(go.Mesh3d(
                x=[cx-c_size/2, cx+c_size/2, cx+c_size/2, cx-c_size/2, cx-c_size/2, cx+c_size/2, cx+c_size/2, cx-c_size/2],
                y=[cy-c_size/2, cy-c_size/2, cy+c_size/2, cy+c_size/2, cy-c_size/2, cy-c_size/2, cy+c_size/2, cy+c_size/2],
                z=[0, 0, 0, 0, num_stories*h_story, num_stories*h_story, num_stories*h_story, num_stories*h_story],
                i=[0,0,4,4,1,5,2,6,3,7,0,4], j=[1,2,5,6,5,6,6,7,7,4,4,7], k=[2,3,6,7,6,7,7,4,4,5,1,3],
                color='#5a7bbf', opacity=0.9, showlegend=False, hoverinfo='skip'
            ))

    # Dibujar Vigas X y Y en cada piso
    for p in range(1, int(num_stories)+1):
        z_level = p * h_story
        # Vigas en X
        for j in range(ny+1):
            cy = j * ly
            for i in range(nx):
                x1 = i * lx
                x2 = (i+1) * lx
                fig3d.add_trace(go.Mesh3d(
                    x=[x1, x2, x2, x1, x1, x2, x2, x1],
                    y=[cy-b_vx/2, cy-b_vx/2, cy+b_vx/2, cy+b_vx/2, cy-b_vx/2, cy-b_vx/2, cy+b_vx/2, cy+b_vx/2],
                    z=[z_level-h_vx, z_level-h_vx, z_level-h_vx, z_level-h_vx, z_level, z_level, z_level, z_level],
                    i=[0,0,4,4,1,5,2,6,3,7,0,4], j=[1,2,5,6,5,6,6,7,7,4,4,7], k=[2,3,6,7,6,7,7,4,4,5,1,3],
                    color='#d9a05b', opacity=0.8, showlegend=False, hoverinfo='skip'
                ))
        # Vigas en Y
        for i in range(nx+1):
            cx = i * lx
            for j in range(ny):
                y1 = j * ly
                y2 = (j+1) * ly
                fig3d.add_trace(go.Mesh3d(
                    x=[cx-b_vy/2, cx+b_vy/2, cx+b_vy/2, cx-b_vy/2, cx-b_vy/2, cx+b_vy/2, cx+b_vy/2, cx-b_vy/2],
                    y=[y1, y1, y2, y2, y1, y1, y2, y2],
                    z=[z_level-h_vy, z_level-h_vy, z_level-h_vy, z_level-h_vy, z_level, z_level, z_level, z_level],
                    i=[0,0,4,4,1,5,2,6,3,7,0,4], j=[1,2,5,6,5,6,6,7,7,4,4,7], k=[2,3,6,7,6,7,7,4,4,5,1,3],
                    color='#d9a05b', opacity=0.8, showlegend=False, hoverinfo='skip'
                ))
        # Losa (se asume maciza)
        fig3d.add_trace(go.Mesh3d(
            x=[0, nx*lx, nx*lx, 0, 0, nx*lx, nx*lx, 0],
            y=[0, 0, ny*ly, ny*ly, 0, 0, ny*ly, ny*ly],
            z=[z_level-h_mac, z_level-h_mac, z_level-h_mac, z_level-h_mac, z_level, z_level, z_level, z_level],
            i=[0,0,4,4,1,5,2,6,3,7,0,4], j=[1,2,5,6,5,6,6,7,7,4,4,7], k=[2,3,6,7,6,7,7,4,4,5,1,3],
            color='#c8c8c8', opacity=0.4, showlegend=False, hoverinfo='skip'
        ))

    # Añadir leyenda
    fig3d.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', marker=dict(color='#5a7bbf'), name=_t('Columna', 'Column')))
    fig3d.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', marker=dict(color='#d9a05b'), name=_t('Viga', 'Beam')))
    fig3d.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', marker=dict(color='#c8c8c8'), name=_t('Losa', 'Slab')))

    fig3d.update_layout(
        scene=dict(aspectmode='data', bgcolor='#1a1a2e',
                   xaxis_title='X(m)', yaxis_title='Y(m)', zaxis_title='Z(m)'),
        paper_bgcolor='#1a1a2e', font=dict(color='white'), height=650,
        margin=dict(l=0,r=0,t=40,b=0), showlegend=True,
        legend=dict(x=0,y=1,bgcolor='rgba(0,0,0,0.5)')
    )
    st.plotly_chart(fig3d, use_container_width=True)

with tab_2d:
    st.subheader(_t("Plano de Distribución y Áreas Tributarias", "Layout Plan and Tributary Areas"))
    fig2d, ax = plt.subplots(figsize=(10, 8))
    fig2d.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')

    nx, ny = 2, 2
    for i in range(nx+1):
        ax.axvline(i*lx, color='gray', linestyle='-.', lw=1, alpha=0.5)
        ax.text(i*lx, ny*ly+1.0, f"{i+1}", color='white', ha='center', va='center', bbox=dict(boxstyle='circle', fc='#d9a05b', ec='white'))
    for j in range(ny+1):
        ax.axhline(j*ly, color='gray', linestyle='-.', lw=1, alpha=0.5)
        ax.text(-1.0, j*ly, f"{chr(65+j)}", color='white', ha='center', va='center', bbox=dict(boxstyle='circle', fc='#d9a05b', ec='white'))

    # Áreas tributarias (sombrear)
    ax.add_patch(patches.Rectangle((lx/2, ly/2), lx, ly, fc='#00d4ff', alpha=0.2, ec='none'))
    ax.text(lx, ly, _t("AT Central", "Center Trib. Area"), color='#00d4ff', ha='center', fontsize=9)
    ax.add_patch(patches.Rectangle((0, ly/2), lx/2, ly, fc='#ff9500', alpha=0.2, ec='none'))
    ax.add_patch(patches.Rectangle((0, 0), lx/2, ly/2, fc='#ff2a2a', alpha=0.2, ec='none'))

    # Dibujar columnas
    for i in range(nx+1):
        for j in range(ny+1):
            if i in [0, nx] and j in [0, ny]:
                s = lado_e/100.
            elif i in [0, nx] or j in [0, ny]:
                s = lado_b/100.
            else:
                s = lado_c/100.
            ax.add_patch(patches.Rectangle((i*lx-s/2, j*ly-s/2), s, s, fc='#5a7bbf', ec='white', lw=1.5, zorder=3))

    # Vigas (líneas gruesas)
    for i in range(nx+1):
        ax.plot([i*lx, i*lx], [0, ny*ly], color='#d9a05b', lw=b_vy*20, alpha=0.7, zorder=2)
    for j in range(ny+1):
        ax.plot([0, nx*lx], [j*ly, j*ly], color='#d9a05b', lw=b_vx*20, alpha=0.7, zorder=2)

    ax.set_aspect('equal')
    ax.axis('off')
    st.pyplot(fig2d)
    buf_2d = io.BytesIO()
    fig2d.savefig(buf_2d, format='png', dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
    buf_2d.seek(0); plt.close(fig2d)

with tab_dxf:
    st.subheader(_t("Descargar Plano Estructural DXF", "Download Structural DXF Plan"))
    doc_dxf = ezdxf.new('R2010'); msp = doc_dxf.modelspace()
    for lay, c in [('EJES',1), ('VIGAS',2), ('COLUMNAS',4), ('COTAS',3), ('TEXTO',7)]:
        if lay not in doc_dxf.layers: doc_dxf.layers.add(lay, color=c)
    
    nx, ny = 2, 2
    for i in range(nx+1):
        msp.add_line((i*lx, -1), (i*lx, ny*ly+1), dxfattribs={'layer':'EJES'})
    for j in range(ny+1):
        msp.add_line((-1, j*ly), (nx*lx+1, j*ly), dxfattribs={'layer':'EJES'})
    
    for i in range(nx+1):
        for j in range(ny+1):
            if i in [0, nx] and j in [0, ny]:
                s = lado_e/100.
            elif i in [0, nx] or j in [0, ny]:
                s = lado_b/100.
            else:
                s = lado_c/100.
            msp.add_lwpolyline([(i*lx-s/2, j*ly-s/2), (i*lx+s/2, j*ly-s/2), (i*lx+s/2, j*ly+s/2), (i*lx-s/2, j*ly+s/2), (i*lx-s/2, j*ly-s/2)], dxfattribs={'layer':'COLUMNAS'})
    
    for i in range(nx+1):
        msp.add_line((i*lx-b_vy/2, 0), (i*lx-b_vy/2, ny*ly), dxfattribs={'layer':'VIGAS'})
        msp.add_line((i*lx+b_vy/2, 0), (i*lx+b_vy/2, ny*ly), dxfattribs={'layer':'VIGAS'})
    for j in range(ny+1):
        msp.add_line((0, j*ly-b_vx/2), (nx*lx, j*ly-b_vx/2), dxfattribs={'layer':'VIGAS'})
        msp.add_line((0, j*ly+b_vx/2), (nx*lx, j*ly+b_vx/2), dxfattribs={'layer':'VIGAS'})

    _out_dxf = io.StringIO(); doc_dxf.write(_out_dxf)
    st.download_button("📥 " + _t("Descargar DXF Planta", "Download Plan DXF"), data=_out_dxf.getvalue().encode('utf-8'), file_name=f"Predimensionamiento_{lx}x{ly}.dxf", mime="application/dxf")

with tab_mem:
    st.subheader(_t("Generar Memoria de Cálculo", "Generate Calculation Memory"))
    if st.button("🖨️ " + _t("Descargar Reporte DOCX", "Download DOCX Report")):
        doc = Document()
        doc.add_heading(f"PREDIMENSIONAMIENTO ESTRUCTURAL — {norma_sel}", 0)
        doc.add_paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
        
        doc.add_heading("01. Configuración del Proyecto", 1)
        for k, v in [("Pisos", num_stories), ("Altura Entrepiso", f"{h_story} m"), ("Luz X", f"{lx} m"), ("Luz Y", f"{ly} m"), ("Zona Sísmica", seismic_zone), ("f'c", f"{fc_val} kg/cm²"), ("fy", f"{fy_val} kg/cm²"), ("Carga Total Aproximada", f"{q_estimado} Ton/m²")]:
            doc.add_paragraph(f"{k}: {v}", style='List Bullet')
            
        doc.add_heading("02. Predimensionamiento Vigas y Losas", 1)
        doc.add_paragraph(f"Espesor Losa Maciza (L/28): {h_mac*100:.0f} cm")
        doc.add_paragraph(f"Espesor Losa Nervada (L/21): {h_ali*100:.0f} cm")
        doc.add_paragraph(f"Viga Eje X: {b_vx*100:.0f}×{h_vx*100:.0f} cm")
        doc.add_paragraph(f"Viga Eje Y: {b_vy*100:.0f}×{h_vy*100:.0f} cm")
        
        doc.add_heading("03. Predimensionamiento Columnas", 1)
        t = doc.add_table(rows=1, cols=4); t.style = 'Table Grid'
        hdr = t.rows[0].cells
        hdr[0].text="Tipo"; hdr[1].text="A.Trib(m²)"; hdr[2].text=f"Pu({unidad_fuerza})"; hdr[3].text="Lado(cm)"
        for t_n, a, pu, lado in [("Central", A_central, Pu_c*factor_fuerza, lado_c), ("Borde", A_borde, Pu_b*factor_fuerza, lado_b), ("Esquina", A_esquina, Pu_e*factor_fuerza, lado_e)]:
            r = t.add_row().cells
            r[0].text=t_n; r[1].text=f"{a:.2f}"; r[2].text=f"{pu:.1f}"; r[3].text=f"{lado:.0f}"
        
        # --- VERIFICACIÓN MULTI-NORMA ---
        doc.add_heading("04. Verificación por Norma Activa", 1)
        doc.add_paragraph(f"Norma seleccionada: {norma_sel}")
        doc.add_paragraph(f"Referencia de artículo: {NORM_REF}")
        doc.add_paragraph(f"Divisor de losa maciza: L/{DIV_LOSA_MAC}  →  h = {h_mac*100:.0f} cm")
        doc.add_paragraph(f"Divisor de losa nervada: L/{DIV_LOSA_NERV}  →  h = {h_ali*100:.0f} cm")
        doc.add_paragraph(f"Divisor de peralte de vigas (continua): L/{DIV_VIGA_CONT}  →  h = {h_vx*100:.0f} cm")
        doc.add_paragraph(f"Índice de resistencia de columna (φ factor): {COL_IDX:.4f}")
        is_manual = st.session_state.get("usar_manual", False)
        if is_manual:
            doc.add_paragraph("⚠ NOTA: Las dimensiones en esta memoria incluyen ajuste MANUAL del usuario.")
        # Tabla comparativa de dimensiones calculadas vs manuales
        doc.add_heading("Tabla Resumen de Dimensiones", 2)
        t2 = doc.add_table(rows=1, cols=3); t2.style = "Table Grid"
        h2 = t2.rows[0].cells; h2[0].text = "Elemento"; h2[1].text = "Calculado"; h2[2].text = "Usado en Diseño"
        data_dim = [
            ("Losa Maciza", f"h = {predimensionar_losa(l_max,'maciza')*100:.0f} cm", f"h = {h_mac*100:.0f} cm"),
            ("Losa Nervada", f"h = {predimensionar_losa(l_max,'aligerada')*100:.0f} cm", f"h = {h_ali*100:.0f} cm"),
            ("Viga X", f"{predimensionar_viga(lx,'continua')[1]*100:.0f}×{predimensionar_viga(lx,'continua')[0]*100:.0f} cm", f"{b_vx*100:.0f}×{h_vx*100:.0f} cm"),
            ("Viga Y", f"{predimensionar_viga(ly,'continua')[1]*100:.0f}×{predimensionar_viga(ly,'continua')[0]*100:.0f} cm", f"{b_vy*100:.0f}×{h_vy*100:.0f} cm"),
            ("Col. Central", f"{predimensionar_columna(A_central,q_estimado,num_stories,alpha_seismic,fc_val)[2]:.0f}×{predimensionar_columna(A_central,q_estimado,num_stories,alpha_seismic,fc_val)[2]:.0f} cm", f"{lado_c:.0f}×{lado_c:.0f} cm"),
            ("Col. Borde",   f"{predimensionar_columna(A_borde,q_estimado,num_stories,alpha_seismic,fc_val)[2]:.0f} cm", f"{lado_b:.0f} cm"),
            ("Col. Esquina", f"{predimensionar_columna(A_esquina,q_estimado,num_stories,alpha_seismic,fc_val)[2]:.0f} cm", f"{lado_e:.0f} cm"),
        ]
        for nm, calc, used in data_dim:
            r2 = t2.add_row().cells; r2[0].text = nm; r2[1].text = calc; r2[2].text = used

        doc.add_heading("05. Muros de Corte", 1)

        doc.add_paragraph(muro_sugerido)
        if warning_deriva:
            doc.add_paragraph(f"Advertencia de deriva: {warning_deriva}")
        
        try:
            buf_2d.seek(0); doc.add_heading("Esquema de Planta", 1); doc.add_picture(buf_2d, width=Inches(6.0))
        except: pass
        
        # Incluir figurado de columna típica
        doc.add_heading("05. Esquema de Figurado (Columna Típica)", 1)
        hook_len = 12 * 12  # asumir varilla Ø12mm
        straight_len = h_story * 100 - 2 * hook_len
        fig_col = draw_longitudinal_bar(h_story*100, straight_len, hook_len, 12, bar_name="Columna Central")
        buf_col = io.BytesIO()
        fig_col.savefig(buf_col, format='png', dpi=150, bbox_inches='tight')
        buf_col.seek(0)
        doc.add_picture(buf_col, width=Inches(4.5))
        plt.close(fig_col)
        
        # Estribo típico
        inside_b = lado_c - 2*4  # recubrimiento 4 cm
        inside_h = lado_c - 2*4
        fig_est = draw_stirrup(inside_b, inside_h, 12*0.6, 6, bar_name="Estribo Ø6mm")
        buf_est = io.BytesIO()
        fig_est.savefig(buf_est, format='png', dpi=150, bbox_inches='tight')
        buf_est.seek(0)
        doc.add_picture(buf_est, width=Inches(3.5))
        plt.close(fig_est)
        
        buf_doc=io.BytesIO(); doc.save(buf_doc); buf_doc.seek(0)
        st.download_button("📥 " + _t("Descargar DOCX", "Download DOCX"), data=buf_doc, file_name="Memoria_Predim.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with tab_qty:
    st.subheader(_t("Estimación de Cantidades de Materiales", "Material Quantity Estimation"))
    
    # Estimación de volúmenes para una estructura típica de 3x3 crujías
    nx, ny = 2, 2  # número de vanos en cada dirección (para un total de 3x3 columnas)
    
    # Columnas
    n_cols_c = (nx-1)*(ny-1)  # centrales
    n_cols_b = 2*(nx-1) + 2*(ny-1)  # bordes
    n_cols_e = 4  # esquinas
    n_cols_total = n_cols_c + n_cols_b + n_cols_e
    
    vol_cols = (n_cols_c*(lado_c/100.)**2 + n_cols_b*(lado_b/100.)**2 + n_cols_e*(lado_e/100.)**2) * h_story * num_stories
    
    # Vigas
    length_vigas_x = nx * lx * (ny+1)  # vigas en X
    length_vigas_y = ny * ly * (nx+1)  # vigas en Y
    length_vigas_total = length_vigas_x + length_vigas_y
    vol_vigas = length_vigas_total * b_vx * h_vx * num_stories  # simplificación con dimensiones de viga X
    
    # Losas
    area_losa = nx * lx * ny * ly * num_stories
    vol_losa = area_losa * h_mac  # se asume losa maciza para predimensionamiento
    
    vol_conc_total = vol_cols + vol_vigas + vol_losa
    
    # Acero estimado (factor ~120 kg/m³ para estructuras convencionales)
    acero_estimado = vol_conc_total * 120  # kg
    
    # Dosificación de concreto (ACI 211)
    # Conversión de f'c a MPa
    fc_mpa = fc_val * 0.0980665
    # Proporciones aproximadas para 1 m³ de concreto
    if fc_mpa <= 21:
        cem_kg = 350; agua_L = 200; arena_kg = 780; grava_kg = 1020
    elif fc_mpa <= 28:
        cem_kg = 430; agua_L = 190; arena_kg = 640; grava_kg = 1000
    else:
        cem_kg = 530; agua_L = 185; arena_kg = 580; grava_kg = 960
    
    total_cem_kg = cem_kg * vol_conc_total
    # Asumir bultos de 50 kg
    bultos_cemento = math.ceil(total_cem_kg / 50)
    total_arena_kg = arena_kg * vol_conc_total
    total_grava_kg = grava_kg * vol_conc_total
    total_agua_L = agua_L * vol_conc_total
    
    cq1, cq2 = st.columns(2)
    with cq1:
        st.markdown("#### Concreto")
        qty_table = pd.DataFrame({
            "Concepto": ["Columnas", "Vigas", "Losas", "TOTAL CONCRETO"],
            "Volumen (m³)": [f"{vol_cols:.2f}", f"{vol_vigas:.2f}", f"{vol_losa:.2f}", f"{vol_conc_total:.2f}"]
        })
        st.dataframe(qty_table, use_container_width=True, hide_index=True)
        
        st.markdown("#### Acero de Refuerzo")
        st.metric("Acero Estimado", f"{acero_estimado:,.0f} kg")
        
    with cq2:
        st.markdown("#### Dosificación de Concreto (por m³)")
        st.write(f"**f'c = {fc_val} kg/cm² ({fc_mpa:.1f} MPa)**")
        st.write(f"- Cemento: {cem_kg:.0f} kg/m³")
        st.write(f"- Agua: {agua_L:.0f} L/m³")
        st.write(f"- Arena: {arena_kg:.0f} kg/m³")
        st.write(f"- Grava: {grava_kg:.0f} kg/m³")
        st.markdown("#### Totales para la Estructura")
        st.write(f"- Cemento: {total_cem_kg:.0f} kg ({bultos_cemento} bultos de 50 kg)")
        st.write(f"- Arena: {total_arena_kg:.0f} kg")
        st.write(f"- Grava: {total_grava_kg:.0f} kg")
        st.write(f"- Agua: {total_agua_L:.0f} L")
    
    # Gráfico de volúmenes
    st.markdown("---")
    st.subheader("Distribución de Volúmenes")
    fig_bar, ax_bar = plt.subplots(figsize=(8,4))
    ax_bar.bar(["Columnas", "Vigas", "Losas"], [vol_cols, vol_vigas, vol_losa], color=['#5a7bbf', '#d9a05b', '#c8c8c8'])
    ax_bar.set_ylabel("Volumen (m³)")
    ax_bar.set_title("Distribución de Concreto por Elemento")
    ax_bar.grid(True, alpha=0.3)
    st.pyplot(fig_bar)
    buf_bar = io.BytesIO()
    fig_bar.savefig(buf_bar, format='png', dpi=150, bbox_inches='tight')
    buf_bar.seek(0); plt.close(fig_bar)

with tab_apu:
    st.subheader(_t("Presupuesto APU", "APU Budget"))
    
    if "apu_config_pred" in st.session_state:
        apu = st.session_state.apu_config_pred
        mon = apu["moneda"]
        p_cem = apu["cemento"]
        p_ace = apu["acero"]
        p_conc = apu["concreto"]
        p_mo = apu["costo_dia_mo"]
        pct_h = apu["pct_herramienta"]
        pct_aui = apu["pct_aui"]
        pct_util = apu["pct_util"]
        iva = apu["iva"]
        st.info("Precios cargados desde la configuración APU.")
    else:
        mon = "$"
        p_cem = st.number_input("Precio bulto cemento (50 kg)", value=28000.0, step=1000.0, key="apu_cem_tmp")
        p_ace = st.number_input("Precio kg acero", value=7500.0, step=100.0, key="apu_ace_tmp")
        p_conc = st.number_input("Precio m³ concreto", value=400000.0, step=10000.0, key="apu_conc_tmp")
        p_mo = st.number_input("Costo mano de obra (día)", value=70000.0, step=5000.0, key="apu_mo_tmp")
        pct_h = st.number_input("% Herramienta menor", value=5.0, step=1.0, key="apu_h_tmp") / 100.0
        pct_aui = st.number_input("% A.I.U.", value=30.0, step=5.0, key="apu_aui_tmp") / 100.0
        pct_util = st.number_input("% Utilidad", value=5.0, step=1.0, key="apu_util_tmp") / 100.0
        iva = st.number_input("% IVA", value=19.0, step=1.0, key="apu_iva_tmp") / 100.0
    
    # Calcular costos con los volúmenes estimados
    costo_concreto = vol_conc_total * p_conc
    costo_acero = acero_estimado * p_ace
    # Mano de obra estimada: 0.04 días/kg de acero + 0.4 días/m³ de concreto
    dias_mo = acero_estimado * 0.04 + vol_conc_total * 0.4
    costo_mo = dias_mo * p_mo
    costo_directo = costo_concreto + costo_acero + costo_mo
    herramienta = costo_mo * pct_h
    aiu = costo_directo * pct_aui
    utilidad = costo_directo * pct_util
    iva_util = utilidad * iva
    total_proyecto = costo_directo + herramienta + aiu + iva_util
    
    st.markdown("### 💰 Presupuesto Estimado")
    df_apu = pd.DataFrame({
        "Item": ["Concreto (m³)", "Acero (kg)", "Mano de Obra (días)", "Herramienta Menor", "A.I.U.", "IVA s/Utilidad", "TOTAL"],
        "Cantidad": [f"{vol_conc_total:.2f}", f"{acero_estimado:,.0f}", f"{dias_mo:.1f}", f"{pct_h*100:.1f}% MO", f"{pct_aui*100:.1f}% CD", f"{iva*100:.1f}% Util", ""],
        f"Subtotal ({mon})": [f"{costo_concreto:,.0f}", f"{costo_acero:,.0f}", f"{costo_mo:,.0f}", f"{herramienta:,.0f}", f"{aiu:,.0f}", f"{iva_util:,.0f}", f"{total_proyecto:,.0f}"]
    })
    st.dataframe(df_apu, use_container_width=True, hide_index=True)
    st.metric(f"💎 Gran Total Proyecto ({mon})", f"{total_proyecto:,.0f}")
    
    # Exportar Excel con cantidades y APU
    out_xl = io.BytesIO()
    with pd.ExcelWriter(out_xl, engine='xlsxwriter') as wr:
        df_apu.to_excel(wr, sheet_name='Presupuesto', index=False)
        pd.DataFrame({
            "Elemento": ["Columnas", "Vigas", "Losas", "Total"],
            "Volumen (m³)": [vol_cols, vol_vigas, vol_losa, vol_conc_total]
        }).to_excel(wr, sheet_name='Volumenes', index=False)
        pd.DataFrame({
            "Material": ["Cemento (bultos)", "Arena (kg)", "Grava (kg)", "Agua (L)", "Acero (kg)"],
            "Cantidad": [bultos_cemento, total_arena_kg, total_grava_kg, total_agua_L, acero_estimado]
        }).to_excel(wr, sheet_name='Cantidades', index=False)
    out_xl.seek(0)
    st.download_button("📥 " + _t("Descargar Excel", "Download Excel"), data=out_xl, file_name="Presupuesto_Predim.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")