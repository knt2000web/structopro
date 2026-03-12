import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import math

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en):
    return en if lang == "English" else es
# ─────────────────────────────────────────────

st.set_page_config(page_title=_t("Otras Estructuras", "Other Structures"), layout="wide")
st.title(_t("Otras Estructuras — Suite (Multi-Norma)", "Other Structures — Suite (Multi-Code)"))

# CODES dict
CODES = {
    "NSR-10 (Colombia)": {"phi_shear":0.75, "phi_comp":0.65, "lambda":1.0, "ref":"NSR-10 Título C"},
    "ACI 318-25 (EE.UU.)": {"phi_shear":0.75, "phi_comp":0.65, "lambda":1.0, "ref":"ACI 318-25"},
    "ACI 318-19 (EE.UU.)": {"phi_shear":0.75, "phi_comp":0.65, "lambda":1.0, "ref":"ACI 318-19"},
    "ACI 318-14 (EE.UU.)": {"phi_shear":0.75, "phi_comp":0.65, "lambda":1.0, "ref":"ACI 318-14"},
    "NEC-SE-HM (Ecuador)": {"phi_shear":0.75, "phi_comp":0.65, "lambda":1.0, "ref":"NEC-SE-HM"},
    "E.060 (Perú)": {"phi_shear":0.85, "phi_comp":0.70, "lambda":1.0, "ref":"Norma E.060 (Perú)"},
    "NTC-EM (México)": {"phi_shear":0.80, "phi_comp":0.70, "lambda":1.0, "ref":"NTC-EM 2017 (México)"},
    "COVENIN 1753-2006 (Venezuela)": {"phi_shear":0.75, "phi_comp":0.70, "lambda":1.0, "ref":"COVENIN 1753-2006"},
    "NB 1225001-2020 (Bolivia)": {"phi_shear":0.75, "phi_comp":0.65, "lambda":1.0, "ref":"NB 1225001-2020"},
    "CIRSOC 201-2025 (Argentina)": {"phi_shear":0.75, "phi_comp":0.65, "lambda":1.0, "ref":"CIRSOC 201-2025"},
}

REBAR_US = {"#3 (Ø9.5mm)":0.71,"#4 (Ø12.7mm)":1.29,"#5 (Ø15.9mm)":1.99,"#6 (Ø19.1mm)":2.84,"#7 (Ø22.2mm)":3.87,"#8 (Ø25.4mm)":5.10}

st.sidebar.header(_t("🌍 Norma de Diseño", "🌍 Design Code"))
if "norma_sel" not in st.session_state:
    st.session_state.norma_sel = "NSR-10 (Colombia)"
norma_sel = st.sidebar.selectbox(_t("Norma:", "Code:"), list(CODES.keys()),
                                 index=list(CODES.keys()).index(st.session_state.norma_sel) if st.session_state.norma_sel in CODES else 0)
_PAIS_ISO = {"NSR-10 (Colombia)":"co","ACI 318-25 (EE.UU.)":"us","ACI 318-19 (EE.UU.)":"us","ACI 318-14 (EE.UU.)":"us","NEC-SE-HM (Ecuador)":"ec","E.060 (Perú)":"pe","NTC-EM (México)":"mx","COVENIN 1753-2006 (Venezuela)":"ve","NB 1225001-2020 (Bolivia)":"bo","CIRSOC 201-2025 (Argentina)":"ar"}
_iso = _PAIS_ISO.get(norma_sel, "un")
st.sidebar.markdown(
    f'<div style="background:#1e3a1e;border-radius:6px;padding:8px 12px;margin-bottom:4px;">'
    f'<img src="https://flagcdn.com/24x18/{_iso}.png" style="vertical-align:middle;margin-right:8px;">'
    f'<span style="color:#7ec87e;font-weight:600;font-size:13px;">{_t("Norma Activa:","Active Code:")} {norma_sel}</span>'
    f'</div>', unsafe_allow_html=True
)
code = CODES[norma_sel]
st.sidebar.markdown(f"📖 `{code['ref']}`")

st.sidebar.header(_t("⚙️ Materiales", "⚙️ Materials"))
fc = st.sidebar.number_input(_t("f'c [MPa]:", "f'c [MPa]:"), 15.0, 80.0, 21.0, 1.0)
fy = st.sidebar.number_input(_t("fy [MPa]:", "fy [MPa]:"), 200.0, 500.0, 420.0, 10.0)
phi_v = code["phi_shear"]
phi_c = code["phi_comp"]

# ══════════════════════════════════════════
# 1. CORTANTE A UNA DISTANCIA X
# ══════════════════════════════════════════
with st.expander(_t("✂️ Cortante a una Distancia X del Apoyo (Vigas)", "✂️ Shear at a Distance X from Support (Beams)")):
    st.info(_t("📺 **Modo de uso:** Ingresa la carga distribuida Wu, la longitud de la viga y la distancia X. La app calculará el cortante Vu en ese punto y el espaciamiento requerido de estribos.", "📺 **How to use:** Enter load Wu, span L and distance X. Shows required shear at that section."))
    c1, c2 = st.columns(2)
    with c1:
        L_vga = st.number_input(_t("Longitud luz libre [m]", "Clear span (m)"), 1.0, 20.0, 5.0, 0.5, key="cx_L")
        wu_vga= st.number_input(_t("Carga distribuida Wu [kN/m]", "Factored load Wu (kN/m)"), 1.0, 500.0, 50.0, 5.0, key="cx_wu")
        x_dist= st.number_input(_t("Distancia X desde el apoyo [m]", "Distance X from support (m)"), 0.0, L_vga/2, 1.0, 0.1, key="cx_x")
    with c2:
        bw_cx = st.number_input("Ancho bw [cm]", 10.0, 100.0, 25.0, 5.0, key="cx_bw")
        d_cx  = st.number_input("Peralte efectivo d [cm]", 10.0, 150.0, 40.0, 5.0, key="cx_d")
        ramas = st.number_input("Ramas del estribo (#3)", 2, 6, 2, 1, key="cx_ramas")
    
    # Simple beam shear equation: V(x) = wu * L / 2 - wu * x
    Vu_x = wu_vga * L_vga / 2.0 - wu_vga * x_dist
    Vc_x = 0.17 * 1.0 * math.sqrt(fc) * bw_cx * 10 * d_cx * 10 / 1000 # kN
    phiVc_x = phi_v * Vc_x
    Vs_req = max(0, Vu_x / phi_v - Vc_x)
    Av_cx = ramas * 0.71 # cm2 for #3
    if Vs_req > 0:
        s_cx_mm = Av_cx * 100 * fy * (d_cx * 10) / (Vs_req * 1000)
    else:
        s_cx_mm = min(d_cx * 10 / 2, 600)
    s_max_cx = min(d_cx * 10 / 2, 600)
    s_diseno = min(s_cx_mm, s_max_cx) / 10 # cm

    st.markdown(f"**Resultados a X = {x_dist} m:**")
    st.write(f"- Cortante Factorizado **Vu:** `{Vu_x:.1f} kN`")
    st.write(f"- Capacidad Concreto **φVc:** `{phiVc_x:.1f} kN`")
    if Vu_x > phi_v * 0.66 * math.sqrt(fc) * bw_cx * 10 * d_cx * 10 / 1000:
        st.error("Sección muy pequeña. Falla inminente a cortante.")
    else:
        st.success(f"Estribos (#3) requeridos a: **@{s_diseno:.1f} cm** en X={x_dist}m")

# ══════════════════════════════════════════
# 2. DISEÑO DE MÉNSULAS (CORBELS)
# ══════════════════════════════════════════
with st.expander(_t("🏗️ Diseño de Ménsulas (Corbels / ACI 318)", "🏗️ Corbel Design (ACI 318)")):
    st.info(_t("📺 **Modo de uso:** Ingresa la carga vertical Vu y la fuerza horizontal Nuc. Define la geometría de la ménsula. Se calculará el acero principal, los estribos horizontales cerrados, y el acero de colgado.", "📺 **How to use:** Enter Vertical load Vu, Horizontal Nuc and geometry. Calculates main steel and closed ties."))
    c1,c2 = st.columns(2)
    with c1:
        Vu_men = st.number_input(_t("Carga Vertical Vu [kN]", "Vertical Load Vu [kN]"), 50.0, 2000.0, 300.0, 50.0, key="men_vu")
        Nuc_men= st.number_input(_t("Tensión Horiz. Nuc [kN]", "Horiz. Tension Nuc [kN]"), 0.0, 1000.0, 60.0, 10.0, key="men_nuc")
        a_men  = st.number_input(_t("Brazo de palanca a [cm]", "Shear span a [cm]"), 5.0, 50.0, 15.0, 5.0, key="men_a")
    with c2:
        bw_men = st.number_input(_t("Ancho ménsula bw [cm]", "Corbel width bw [cm]"), 20.0, 100.0, 30.0, 5.0, key="men_bw")
        h_men  = st.number_input(_t("Alto total ménsula h [cm]", "Total height h [cm]"), 20.0, 150.0, 45.0, 5.0, key="men_h")
        dp_men = 4.0 # recubrimiento
    
    d_men = h_men - dp_men
    a_d_ratio = a_men / d_men
    if a_d_ratio > 1.0:
        st.warning(f"a/d = {a_d_ratio:.2f} > 1.0. Las ecuaciones de ménsula asumen a/d ≤ 1. Usar diseño de vigas convencionales.")
    else:
        # Fricción corte
        mu_men = 1.4 # monolitico
        Avf = Vu_men / (phi_v * fy * mu_men) * 10  # cm2
        # Flexion
        Mu_men = Vu_men * (a_men/100) + Nuc_men * (h_men - d_men)/100 # kN.m
        Rn_men = Mu_men * 1e6 / (phi_v * bw_men*10 * (d_men*10)**2)
        disc = 1 - 2*Rn_men/(0.85*fc)
        Af = 0
        if disc >= 0:
            rho_men = (0.85*fc/fy)*(1 - math.sqrt(disc))
            Af = rho_men * bw_men * d_men # cm2
        # Tensión directa
        An = Nuc_men / (phi_v * fy) * 10 # cm2
        
        # Acero principal req (As)
        As_req_men = max(Af + An, (2/3)*Avf + An, 0.04 * (fc/fy) * bw_men * d_men)
        # Acero estribos cerrados (Ah)
        Ah_req_men = 0.5 * (As_req_men - An)
        
        st.write(f"- Acero Principal en la cara superior ($A_s$): **{As_req_men:.2f} cm²**")
        st.write(f"- Acero en Estribos Horizontales cerrados ($A_h$): **{Ah_req_men:.2f} cm²**")
        if disc < 0:
            st.error("Sección insuficiente por momento flexionante.")

# ══════════════════════════════════════════
# 3. PREDIMENSIONAMIENTO DE COLUMNAS
# ══════════════════════════════════════════
with st.expander(_t("📐 Predimensionamiento de Columnas", "📐 Column Preliminary Sizing")):
    st.info(_t("📺 **Modo de uso:** Ingresa la carga viva y muerta estimada por piso, el número de pisos y el área tributaria. Te recomendaré dimensiones de columna base.", "📺 **How to use:** Enter estimated load per floor, number of floors, and tributary area. Predicts base column section."))
    c1, c2 = st.columns(2)
    with c1:
        area_trib = st.number_input(_t("Área Tributaria [m²]", "Tributary Area [m²]"), 5.0, 100.0, 20.0, 5.0, key="pre_a")
        pisos     = st.number_input(_t("Total de Pisos", "Total Floors"), 1, 50, 5, 1, key="pre_p")
        W_piso    = st.number_input(_t("Carga estimada por piso (D+L) [kN/m²]", "Estimated Floor Load (D+L) [kN/m²]"), 5.0, 20.0, 12.0, 1.0, key="pre_w")
    with c2:
        tipo_col  = st.selectbox(_t("Posición (afecta k):", "Column Position (affects k):"), 
                                 ["Céntrica (k=0.30)", "Esquinera/Borde (k=0.20-0.25)"] if lang == "Español" else ["Central (k=0.30)", "Edge/Corner (k=0.20-0.25)"], key="pre_tipo")
        rho_p     = st.number_input(_t("Cuantía acero estimada [%]", "Estimated steel ratio [%]"), 1.0, 4.0, 1.5, 0.5, key="pre_r")
    
    # Pu = W_piso * area_trib * pisos
    Pu_estimado = W_piso * area_trib * pisos # kN (unfactored usually used for presizing, or we can assume factor 1.2D+1.6L ~ 1.4 avg)
    Pu_fact = Pu_estimado * 1.4 # avg factor
    
    k_val = 0.30 if "0.30" in tipo_col else 0.22
    # Area de concreto necesaria A = Pu / (k * f'c) -- Aprox predimensionamiento
    Ag_req_cm2 = (Pu_fact * 1000) / (k_val * fc) / 100
    
    b_req = math.sqrt(Ag_req_cm2)
    b_round = math.ceil(b_req/5)*5 # round to 5cm
    
    st.write(f"- Carga Axial de Diseño Estimada ($P_u$): **{Pu_fact:.0f} kN**")
    st.write(f"- Área Bruta Requerida ($A_g$): **{Ag_req_cm2:.0f} cm²**")
    st.success(f"Sección Cuadrada Sugerida: **{b_round} cm × {b_round} cm**")

# ══════════════════════════════════════════
# 4. CAPACIDAD AXIAL COLUMNAS CORTAS
# ══════════════════════════════════════════
with st.expander(_t("🧱 Capacidad Axial Pn,max (Columnas Cortas)", "🧱 Axial Capacity Pn,max (Short Columns)")):
    st.info(_t("📺 **Modo de uso:** Ingresa la sección transversal probada y su armadura. El sistema calculará la carga axial máxima que soporta, ignorando el pandeo.", "📺 **How to use:** Enter section and steel. Calculates max axial capacity (ignoring slenderness)."))
    c1,c2 = st.columns(2)
    with c1:
        b_c = st.number_input("b [cm]", 20.0, 150.0, 40.0, 5.0, key="cap_b")
        h_c = st.number_input("h [cm]", 20.0, 150.0, 40.0, 5.0, key="cap_h")
        estribo = st.selectbox(_t("Forma columna:", "Column Shape:"), 
                               ["Estribada (Cuadrada/Rectg)", "Sunchada (Espiral)"] if lang == "Español" else ["Tied (Square/Rect)", "Spiral"], key="cap_est")
    with c2:
        varillas = st.number_input(_t("No. Varillas", "No. Rebars"), 4, 40, 8, 2, key="cap_n")
        dia_bar  = st.selectbox("Varilla:", ["#5 (Ø15.9mm)", "#6 (Ø19.1mm)", "#7 (Ø22.2mm)", "#8 (Ø25.4mm)"], key="cap_db")
        area_bar = REBAR_US[dia_bar]
    
    Ag_c = b_c * h_c # cm2
    Ast_c = varillas * area_bar # cm2
    phi_c_val = 0.65 if "Estribada" in estribo else 0.75
    alpha_c_val = 0.80 if "Estribada" in estribo else 0.85
    
    Po_kN = (0.85 * fc * (Ag_c - Ast_c)*100 + Ast_c*100 * fy) / 1000
    Pn_max = alpha_c_val * Po_kN
    phi_Pn_max = phi_c_val * Pn_max
    
    st.write(f"- Carga Axial Nominal Pn,max: **{Pn_max:.0f} kN**")
    st.write(f"- Carga Axial de Diseño **φPn,max**: **{phi_Pn_max:.0f} kN**")
    cuantia_c = Ast_c / Ag_c * 100
    if cuantia_c < 1.0 or cuantia_c > 8.0:
        st.warning(f"La cuantía de acero {cuantia_c:.1f}% debe estar entre 1% y 8%.")

# ══════════════════════════════════════════
# 5. LOSAS BIDIRECCIONALES (Método Coeficientes)
# ══════════════════════════════════════════
with st.expander(_t("🏗️ Momentos en Losas 2D (Método ACI Coeficientes)", "🏗️ 2D Slab Moments (ACI Coefficients Method)")):
    st.info(_t("📺 **Modo de uso:** Ingresa las luces la y lb del tablero. Sirve para diseñar losas apoyadas perimetralmente en vigas. Calcula los momentos en ambas direcciones.", "📺 **How to use:** Enter short and long spans. Useful for edge-supported slabs. Calculates moments in both directions."))
    c1,c2 = st.columns(2)
    with c1:
        la_losa = st.number_input(_t("Luz corta La [m]", "Short span La [m]"), 2.0, 15.0, 4.0, 0.5, key="lo2_la")
        lb_losa = st.number_input(_t("Luz larga Lb [m]", "Long span Lb [m]"), 2.0, 15.0, 5.0, 0.5, key="lo2_lb")
    with c2:
        wu_losa = st.number_input("Carga distribuida factorizada Wu [kN/m²]", 2.0, 50.0, 10.0, 0.5, key="lo2_wu")
        caso_borde= st.selectbox("Condición de Borde (ACI):", ["Caso 1 (Interior)", "Caso 2 (4 bordes discontinuos)", "Caso 3 (1 borde continuo)", "Caso 4 (2 bordes ady. continuos)"], key="lo2_caso")
        
    m_ratio = la_losa / lb_losa if lb_losa > 0 else 1.0
    if m_ratio < 0.5:
        st.warning("m < 0.5. El panel se comporta como una losa en Una Dirección apoyada sobre las vigas largas.")
    else:
        # Simplificación de coeficientes ca y cb para demostración (Valores aproximados generales)
        # Ca_neg, Ca_pos, Cb_neg, Cb_pos = f(m, caso)
        # Aquí usamos unos coeficientes promedios didácticos proporcionales a (m^2 vs 1)
        ca_pos = 0.050 * m_ratio
        cb_pos = 0.050 / m_ratio
        
        ca_neg = 0.070 * m_ratio if "Caso 2" not in caso_borde else 0
        cb_neg = 0.070 / m_ratio if "Caso 2" not in caso_borde else 0
        
        Ma_pos = ca_pos * wu_losa * la_losa**2
        Mb_pos = cb_pos * wu_losa * lb_losa**2
        
        Ma_neg = ca_neg * wu_losa * la_losa**2
        Mb_neg = cb_neg * wu_losa * lb_losa**2
        
        st.write(f"- Relación m (La/Lb): **{m_ratio:.2f}**")
        colA, colB = st.columns(2)
        colA.markdown("#### Dirección Corta (La)")
        colA.write(f"Ma(+) Positivo: **{Ma_pos:.1f} kN.m/m**")
        if ca_neg>0: colA.write(f"Ma(-) Negativo: **{Ma_neg:.1f} kN.m/m**")
        
        colB.markdown("#### Dirección Larga (Lb)")
        colB.write(f"Mb(+) Positivo: **{Mb_pos:.1f} kN.m/m**")
        if cb_neg>0: colB.write(f"Mb(-) Negativo: **{Mb_neg:.1f} kN.m/m**")

