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

st.set_page_config(page_title=_t("Zapatas y Suelos", "Footings and Soils"), layout="wide")

st.image(r"assets/concrete_isolated_footing_1773262985104.png", use_container_width=True)
st.title(_t("Cimentaciones: Zapatas y Geotecnia", "Foundations: Footings and Geotechnics"))
st.markdown(_t("Módulo integral para diseño de cimentaciones superficiales (Zapata Aislada), capacidad portante y esfuerzos en la masa de suelo. Soporta normativa internacional ACI 318 / NSR-10 / Multi-Norma.", "Comprehensive module for shallow foundation design (Isolated Footing), bearing capacity and soil stresses. Supports international codes ACI 318 / NSR-10 / Multi-Code."))

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

# ─────────────────────────────────────────────
# CONFIGURACIÓN GENERAL Y APU
# ─────────────────────────────────────────────
st.sidebar.header(_t("⚙️ Configuración Global", "⚙️ Global Settings"))
if "norma_sel" not in st.session_state:
    st.session_state.norma_sel = "NSR-10 (Colombia)"

norma_sel = st.session_state.norma_sel
_PAIS_ISO = {"NSR-10 (Colombia)":"co","ACI 318-25 (EE.UU.)":"us","ACI 318-19 (EE.UU.)":"us","ACI 318-14 (EE.UU.)":"us","NEC-SE-HM (Ecuador)":"ec","E.060 (Perú)":"pe","NTC-EM (México)":"mx","COVENIN 1753-2006 (Venezuela)":"ve","NB 1225001-2020 (Bolivia)":"bo","CIRSOC 201-2025 (Argentina)":"ar"}
_iso = _PAIS_ISO.get(norma_sel, "un")
st.sidebar.markdown(
    f'<div style="background:#1e3a1e;border-radius:6px;padding:8px 12px;margin-bottom:4px;">'
    f'<img src="https://flagcdn.com/24x18/{_iso}.png" style="vertical-align:middle;margin-right:8px;">'
    f'<span style="color:#7ec87e;font-weight:600;font-size:13px;">{_t("Norma Activa:","Active Code:")} {norma_sel}</span>'
    f'</div>', unsafe_allow_html=True
)

# Parametros normativos base
phi_v = 0.75 # Cortante
phi_f = 0.90 # Flexión
if "E.060" in norma_sel:
    phi_v = 0.85

fc_basico = st.sidebar.number_input(_t("f'c Zapata [MPa]", "f'c Footing [MPa]"), 15.0, 50.0, st.session_state.get("z_fc", 21.0), 1.0, key="z_fc")
fy_basico = st.sidebar.number_input(_t("fy Acero [MPa]", "fy Steel [MPa]"), 240.0, 500.0, st.session_state.get("z_fy", 420.0), 10.0, key="z_fy")

# ─── CONVERSOR GLOBAL DE UNIDADES DE SUELO ← Visible en toda la página
st.sidebar.markdown("---")
st.sidebar.header(_t("🔄 Conversor Unidades de Suelo", "🔄 Soil Units Converter"))
_cu = st.sidebar.selectbox(_t("Unidad a convertir:", "Unit to convert:"), 
    ["kPa → ...", "ton/m² → ...", "kg/cm² → ...", "MPa → ...", "psi → ..."], key="conv_unit_global")
_cv = st.sidebar.number_input(_t("Valor:", "Value:"), value=1.0, step=0.1, key="conv_val_global")
_ck = {
    "kPa → ...": _cv, "ton/m² → ...": _cv * 9.80665,
    "kg/cm² → ...": _cv * 98.0665, "MPa → ...": _cv * 1000.0,
    "psi → ...": _cv * 6.89476,
}.get(_cu, _cv)
st.sidebar.markdown(f"""
| | |
|:---|---:|
| **kPa** | `{_ck:.2f}` |
| **ton/m²** | `{_ck/9.80665:.3f}` |
| **kg/cm²** | `{_ck/98.0665:.4f}` |
| **MPa** | `{_ck/1000:.5f}` |
| **psi** | `{_ck/6.89476:.2f}` |
""")

REBAR_MM = {
    "10 mm": 0.785, "12 mm": 1.131, "14 mm": 1.539, "16 mm": 2.011,
    "18 mm": 2.545, "20 mm": 3.142, "22 mm": 3.801, "25 mm": 4.909
}

# ─────────────────────────────────────────────
# T1: ESFUERZOS EN EL SUELO (BOUSSINESQ)
# ─────────────────────────────────────────────
with st.expander(_t("🌍 1. Esfuerzos en masa de suelo debajo de zapata", "🌍 1. Soil Stresses under Footing (Boussinesq)"), expanded=False):
    st.info(_t("📺 **Modo de uso:** Ingresa las dimensiones de la zapata y la carga aplicada. El programa usa la solución de Boussinesq (integración de carga rectangular) para encontrar el incremento de esfuerzo vertical a cierta profundidad Z debajo del centro de la zapata.", "📺 **How to use:** Enter footing dimensions and load. Uses Boussinesq method to find vertical stress increment at depth Z."))
    c1, c2 = st.columns(2)
    with c1:
        P_bous = st.number_input("Carga en Zapata P [kN]", 10.0, 10000.0, st.session_state.get("z_bous_P", 1000.0), 100.0, key="z_bous_P")
        B_bous = st.number_input("Ancho B [m]", 0.5, 10.0, st.session_state.get("z_bous_B", 2.0), 0.1, key="z_bous_B")
        L_bous = st.number_input("Largo L [m]", 0.5, 10.0, st.session_state.get("z_bous_L", 2.0), 0.1, key="z_bous_L")
    with c2:
        Z_bous = st.number_input("Profundidad de análisis Z [m]", 0.1, 20.0, st.session_state.get("z_bous_Z", 2.0), 0.5, key="z_bous_Z")
        q_0 = P_bous / (B_bous * L_bous) # Esfuerzo de contacto kN/m2
        st.markdown(_t(f"**Esfuerzo de contacto ($q_0$):** {q_0:.2f} kPa = {q_0/9.80665:.3f} t/m² = {q_0/98.0665:.4f} kg/cm²",
                       f"**Contact Stress ($q_0$):** {q_0:.2f} kPa = {q_0/9.80665:.3f} t/m² = {q_0/98.0665:.4f} kg/cm²"))
        
    # Fadum/Boussinesq bajo el centro: dividimos el rectangulo en 4 rectangulos de B/2 x L/2
    m = (B_bous/2.0) / Z_bous
    n = (L_bous/2.0) / Z_bous
    
    def I_z_bous(m, n):
        V1 = m**2 + n**2 + 1
        V2 = m**2 * n**2
        term1 = (2*m*n*math.sqrt(V1)) / (V1 + V2)
        term2 = (V1 + 1) / V1
        # Use atan2 to avoid division by zero when V1 == V2
        angulo = math.atan2(2*m*n*math.sqrt(V1), (V1 - V2))
        if V1 - V2 < 0:
            angulo += math.pi
        I_z = (1 / (4 * math.pi)) * (term1 * term2 + angulo)
        return I_z
        
    delta_sigma_z = 4 * q_0 * I_z_bous(m, n)
    
    st.success(f"📈 Incremento de esfuerzo vertical bajo el centro a Z={Z_bous}m: **Δσ_z = {delta_sigma_z:.2f} kPa**")
    
    # Grafica rapida de bulbo central
    fig_b, ax_b = plt.subplots(figsize=(6,3))
    zs = np.linspace(0.1, max(B_bous*3, 10), 50)
    sigmas = [4 * q_0 * I_z_bous((B_bous/2.0)/z, (L_bous/2.0)/z) for z in zs]
    ax_b.plot(sigmas, zs, color="magenta", lw=2)
    ax_b.invert_yaxis()
    ax_b.set_xlabel("Incremento de Esfuerzo Δσ_z [kPa]")
    ax_b.set_ylabel("Profundidad Z [m]")
    ax_b.set_title(f"Distribución de Esfuerzos bajo el centro (P={P_bous} kN)")
    ax_b.grid(True, linestyle="--", alpha=0.5)
    st.pyplot(fig_b)

# ─────────────────────────────────────────────
# T2: CAPACIDAD PORTANTE DE SUELO (TERZAGHI)
# ─────────────────────────────────────────────
with st.expander(_t("🛑 2. Capacidad Portante de Suelo (Terzaghi)", "🛑 2. Bearing Capacity (Terzaghi)"), expanded=False):
    st.info(_t("📺 **Modo de uso:** Ingresa el ángulo de fricción interna (φ), la cohesión (c) y el peso unitario del suelo (γ). Selecciona la forma de la zapata y la profundidad de desplante (Df) para hallar el esfuerzo admisible q_adm.", "📺 **How to use:** Enter friction angle (φ), cohesion (c), and unit weight (γ). Select shape and depth (Df) to find allowable bearing capacity q_adm."))

    # ─── CONVERSOR DE UNIDADES → Panel auxiliar siempre visible
    with st.container():
        st.markdown(_t("**🔄 Conversor Rápido de Resistencia de Suelo** — Ingresa cualquier valor y verás equivalencias automáticas:",
                       "**🔄 Quick Soil Resistance Converter** — Enter any value to see automatic equivalencies:"))
        uc1, uc2, uc3 = st.columns([1, 1, 2])
        with uc1:
            q_conv_unit = st.selectbox(_t("Unidad de entrada:", "Input Unit:"), 
                                       ["kPa (kN/m²)", "ton/m²", "kg/cm²", "MPa", "psi", "kN/m²"], 
                                       key="q_conv_unit_terz")
        with uc2:
            q_conv_val = st.number_input(_t("Valor a convertir:", "Value to convert:"), value=1.0, step=0.1, key="q_conv_val_terz")
        with uc3:
            # Convertir a kPa primero
            _conv = {
                "kPa (kN/m²)": q_conv_val,
                "ton/m²": q_conv_val * 9.80665,
                "kg/cm²": q_conv_val * 98.0665,
                "MPa": q_conv_val * 1000.0,
                "psi": q_conv_val * 6.89476,
                "kN/m²": q_conv_val,
            }.get(q_conv_unit, q_conv_val)
            st.markdown(f"""| Unidad | Valor |
|--------|-------|
| **kPa (kN/m²)** | `{_conv:.3f}` |
| **ton/m²** | `{_conv/9.80665:.3f}` |
| **kg/cm²** | `{_conv/98.0665:.4f}` |
| **MPa** | `{_conv/1000.0:.5f}` |
| **psi** | `{_conv/6.89476:.2f}` |
| **kN/m²** | `{_conv:.3f}` |""")
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        phi_ang = st.number_input(_t("Ángulo de fricción φ [°]", "Friction angle φ [°]"), 0.0, 50.0, st.session_state.get("z_phi", 30.0), 1.0, key="z_phi")
        coh_unit = st.selectbox(_t("Unidad cohesión:", "Cohesion Unit:"), ["kPa", "kg/cm²", "ton/m²"], key="coh_u")
        coh_val = st.number_input(f"c [{coh_unit}]", 0.0, 200.0, st.session_state.get("coh_val", 5.0 if coh_unit=="kPa" else 0.05), 0.5 if coh_unit=="kPa" else 0.01, key="coh_val")
        coh_c = coh_val if coh_unit=="kPa" else (coh_val*98.0665 if coh_unit=="kg/cm²" else coh_val*9.80665)
        gam_unit = st.selectbox(_t("Unidad γ:", "γ Unit:"), ["kN/m³", "ton/m³", "kg/m³"], key="gam_u")
        gam_val = st.number_input(f"γ [{gam_unit}]", 10.0, 25.0 if gam_unit!="kg/m³" else 2500.0, st.session_state.get("gam_val", 18.0 if gam_unit!="kg/m³" else 1800.0), 0.5, key="gam_val")
        gamma_s = gam_val if gam_unit=="kN/m³" else (gam_val*9.80665 if gam_unit=="ton/m³" else gam_val*0.00980665)
    with c2:
        forma_zap = st.selectbox(_t("Forma de zapata", "Footing shape"), 
                                 ["Cuadrada", "Continua (Muro)", "Circular"] if lang=="Español" else ["Square", "Continuous (Wall)", "Circular"],
                                 key="z_shape")
        B_cp = st.number_input(_t("Ancho/Diámetro B [m]", "Width/Diameter B [m]"), 0.5, 10.0, st.session_state.get("cp_b", 1.5), 0.1, key="cp_b")
        Df_cp = st.number_input(_t("Profundidad Df [m]", "Depth Df [m]"), 0.0, 10.0, st.session_state.get("cp_df", 1.0), 0.1, key="cp_df")
    with c3:
        FS_terz = st.number_input(_t("Factor de Seguridad (FS)", "Safety Factor (FS)"), 1.0, 5.0, st.session_state.get("z_fs", 3.0), 0.1, key="z_fs")
        
    phi_rad = math.radians(phi_ang)
    if phi_ang == 0:
        Nc, Nq, Ngamma = 5.7, 1.0, 0.0
    else:
        # Terzaghi exact factors
        a_t = math.exp((0.75 * math.pi - phi_rad/2) * math.tan(phi_rad))
        Nq = (a_t**2) / (2 * math.cos(math.radians(45) + phi_rad/2)**2)
        Nc = (Nq - 1) / math.tan(phi_rad)
        # Ngamma approximation (Kumbhojkar)
        Ngamma = 2 * (Nq + 1) * math.tan(phi_rad) / (1 + 0.4 * math.sin(4 * phi_rad))

    if forma_zap in ["Cuadrada", "Square"]:
        sc, sq, sgamma = 1.3, 1.0, 0.8
    elif forma_zap in ["Circular"]:
        sc, sq, sgamma = 1.3, 1.0, 0.6
    else: # Continua
        sc, sq, sgamma = 1.0, 1.0, 1.0
        
    q_ult = sc * coh_c * Nc + sq * (gamma_s * Df_cp) * Nq + sgamma * 0.5 * gamma_s * B_cp * Ngamma
    q_adm = q_ult / FS_terz
    
    df_res = pd.DataFrame([
        {_t("Parámetro", "Parameter"): _t("Factores de Capacidad", "Capacity Factors"), _t("Valor", "Value"): f"Nc={Nc:.2f}, Nq={Nq:.2f}, Nγ={Ngamma:.2f}"},
        {_t("Parámetro", "Parameter"): _t("Factores de Forma", "Shape Factors"),     _t("Valor", "Value"): f"sc={sc}, sq={sq}, sγ={sgamma}"},
        {_t("Parámetro", "Parameter"): _t("Capacidad Última (q_ult)", "Ultimate Capacity (q_ult)"),         _t("Valor", "Value"): f"{q_ult:.2f} kPa"},
        {_t("Parámetro", "Parameter"): _t("Capacidad Admisible (q_adm = q_ult/FS)", "Allowable Capacity (q_adm = q_ult/FS)"), _t("Valor", "Value"): f"{q_adm:.2f} kPa"},
    ])
    st.table(df_res)

    # Tabla de equivalencias del resultado
    st.markdown(_t("### 🔄 `q_adm` en todas las unidades:", "### 🔄 `q_adm` in all units:"))
    eq1, eq2, eq3, eq4, eq5 = st.columns(5)
    eq1.metric("kPa", f"{q_adm:.2f}")
    eq2.metric("ton/m²", f"{q_adm/9.80665:.3f}")
    eq3.metric("kg/cm²", f"{q_adm/98.0665:.4f}")
    eq4.metric("MPa", f"{q_adm/1000:.5f}")
    eq5.metric("psi", f"{q_adm/6.89476:.2f}")
    st.success(_t(f"✅ Capacidad Admisible: **{q_adm:.2f} kPa** = **{q_adm/9.80665:.2f} t/m²** = **{q_adm/98.0665:.3f} kg/cm²** = **{q_adm/6.89476:.1f} psi**",
                  f"✅ Allowable Bearing: **{q_adm:.2f} kPa** = **{q_adm/9.80665:.2f} t/m²** = **{q_adm/98.0665:.3f} kg/cm²** = **{q_adm/6.89476:.1f} psi**"))


# ─────────────────────────────────────────────
# T4: PROFUNDIDAD MÍNIMA EXPLORACIÓN
# ─────────────────────────────────────────────
with st.expander(_t("🔬 4. Profundidad Mínima de Exploración de Subsuelo", "🔬 4. Minimum Subsurface Exploration Depth")):
    st.info(_t("📺 **Modo de uso:** La norma indica que se debe explorar el suelo (perforaciones) hasta que el incremento de esfuerzo de la estructura (Δσ_z) sea menor al 10% del esfuerzo aplicado q_0. Ingresa B, L y P para hallar esta profundidad D_exploración.", "📺 **How to use:** Enter B, L, and P to find exploration depth where vertical stress increment Δσ_z drops below 10% of q_0."))
    c1, c2 = st.columns(2)
    with c1:
        P_ex = st.number_input("Carga total P [kN]", 10.0, 50000.0, 1500.0, 100.0, key="ex1")
        B_ex = st.number_input("Ancho B [m]", 0.5, 20.0, 2.0, 0.5, key="ex2")
    with c2:
        L_ex = st.number_input("Largo L [m]", 0.5, 20.0, 3.0, 0.5, key="ex3")
        
    q0_ex = P_ex / (B_ex * L_ex)
    z_target = 0.1
    # Biseccion para encontrar Z donde delta_sigma_z / q0_ex = 0.10
    z_low = 0.1
    z_high = 50.0
    for _ in range(30):
        z_mid = (z_low + z_high)/2
        m_ex = (B_ex/2.0) / z_mid
        n_ex = (L_ex/2.0) / z_mid
        rat = 4 * I_z_bous(m_ex, n_ex)
        if rat > 0.10:
            z_low = z_mid
        else:
            z_high = z_mid
            
    st.success(f"✅ La profundidad mínima sugerida de exploración (donde Δσ_z = 10% de q0) es: **Z = {z_mid:.2f} metros** debajo del nivel de fundación.")


# ─────────────────────────────────────────────
# T3 & T5: DISEÑO ESTRUCTURAL DE ZAPATA + DIBUJADOR 3000
# ─────────────────────────────────────────────
with st.expander(_t("🏗️ 3 & 5. Diseño de Acero Zapata Prismática y Dibujador 3000", "🏗️ 3 & 5. Footing Structural Design & DXF Drafter"), expanded=True):
    st.info(_t("📺 **Modo de uso:** Ingresa las Cargas de Servicio (para dimensionar BxL) y Últimas (para diseñar espesor y acero). El módulo calculará Cortante, Punzonamiento y Flexión, generará tu geometría a AutoCAD y calculará Presupuestos APU.", "📺 **How to use:** Enter Service Loads (for sizing BxL) and Ultimate Loads (for thickness and steel). Calculates Shear, Punching, Flexure, DXF and APU budgets."))
    st.markdown(f"**Norma Estructural activa:** `{norma_sel}`")
    
    colA, colB, colC = st.columns(3)
    with colA:
        st.write("#### Cargas (Servicio y Últimas)")
        P_svc = st.number_input("Carga Axial de Servicio Ps [kN]", value=800.0, step=50.0)
        M_svc = st.number_input("Momento de Servicio Ms [kN·m]", value=0.0, step=10.0)
        P_ult = st.number_input("Carga Axial Factorizada Pu [kN]", value=1120.0, step=50.0)
        M_ult = st.number_input("Momento Factorizado Mu [kN·m]", value=0.0, step=10.0)
        
    with colB:
        st.write(_t("#### Geometría y Suelo", "#### Geometry and Soil"))
        q_unit = st.selectbox(_t("Unidad q_adm:", "q_adm Unit:"), ["kPa (kN/m²)", "ton/m²", "kg/cm²", "MPa"], index=0)
        
        default_q = 200.0
        step_q = 10.0
        if q_unit == "ton/m²":
            default_q, step_q = 20.0, 1.0
        elif q_unit == "kg/cm²":
            default_q, step_q = 2.0, 0.1
        elif q_unit == "MPa":
            default_q, step_q = 0.2, 0.05
            
        q_val_input = st.number_input(_t("Capacidad Portante q_adm", "Bearing Capacity q_adm"), value=default_q, step=step_q)
        
        if q_unit == "kPa (kN/m²)":
            q_adm_z = q_val_input
        elif q_unit == "ton/m²":
            q_adm_z = q_val_input * 9.80665
        elif q_unit == "MPa":
            q_adm_z = q_val_input * 1000.0
        else: # kg/cm²
            q_adm_z = q_val_input * 98.0665

        # Mostrar equivalencias en cards compactas
        eq_c1, eq_c2, eq_c3 = st.columns(3)
        eq_c1.metric("kPa", f"{q_adm_z:.1f}")
        eq_c2.metric("ton/m²", f"{q_adm_z/9.80665:.2f}")
        eq_c3.metric("MPa / kg/cm²", f"{q_adm_z/1000:.4f} / {q_adm_z/98.0665:.3f}")

        st.caption(_t(f"🔄 **Equivalencia:** {q_adm_z:.1f} kPa | {q_adm_z/9.80665:.3f} ton/m² | {q_adm_z/98.0665:.4f} kg/cm² | {q_adm_z/6.89476:.2f} psi",
                      f"🔄 **Equivalence:** {q_adm_z:.1f} kPa | {q_adm_z/9.80665:.3f} ton/m² | {q_adm_z/98.0665:.4f} kg/cm² | {q_adm_z/6.89476:.2f} psi"))

        c1_col = st.number_input(_t("Dim. Columna c1 (dir. B) [cm]", "Column dim. c1 (B dir.) [cm]"), value=40.0, step=5.0)
        c2_col = st.number_input(_t("Dim. Columna c2 (dir. L) [cm]", "Column dim. c2 (L dir.) [cm]"), value=40.0, step=5.0)
        gamma_prom = st.number_input(_t("γ_promedio (suelo+concreto) [kN/m³]", "γ_avg (soil+concrete) [kN/m³]"), value=20.0)
        Df_z = st.number_input(_t("Desplante Df [m]", "Footing Depth Df [m]"), value=1.0, step=0.1)

    with colC:
        st.write("#### Diseño Estructural")
        H_zap = st.number_input("Espesor H propuesto [cm]", value=50.0, step=5.0)
        recub_z = st.number_input("Recubrimiento al suelo [cm]", value=7.5, step=0.5)
        bar_z = st.selectbox("Varilla a utilizar:", list(REBAR_MM.keys()), index=4)
        A_bar_z = REBAR_MM[bar_z] * 100 # mm2
        db_bar_z = float(bar_z.split(" ")[0]) # mm
        
    # Paso 1: Dimensionamiento en planta
    q_net = q_adm_z - gamma_prom * Df_z # Esfuerzo neto disponible
    Area_req = P_svc / q_net
    # Proponemos zapata cuadrada si M=0, rectangular si hay diferencia c1,c2
    L_req = math.sqrt(Area_req * (c2_col/c1_col) if c1_col>0 else Area_req)
    B_req = Area_req / L_req if L_req > 0 else 0
    # Redondeo a 5cm
    B_zap = math.ceil(B_req * 20) / 20.0
    L_zap = math.ceil(L_req * 20) / 20.0
    # Si hay momento alto, la excentricidad domina, el usuario debe ajustar B y L manually
    st.markdown(f"**Dimensiones mínimas sin excentricidad:** B = {B_zap:.2f} m, L = {L_zap:.2f} m")
    
    cB, cL = st.columns(2)
    B_use = cB.number_input("B usado para cálculo [m]", value=max(2.0, B_zap), step=0.1)
    L_use = cL.number_input("L usado para cálculo [m]", value=max(2.0, L_zap), step=0.1)
    
    # Presion de contacto factorizada qu
    A_use = B_use * L_use
    qu_max = P_ult / A_use + (6 * M_ult / (B_use * L_use**2) if M_ult > 0 else 0)
    
    # Peralte efectivo d
    d_z = H_zap - recub_z - (db_bar_z/10.0)
    d_z_m = d_z / 100.0
    
    # Cortante Unidireccional (Viga) a 'd' de la cara de la columna
    lv_b = (B_use - c1_col/100.0) / 2.0
    x_corte = lv_b - d_z_m
    if x_corte > 0:
        Vu_1way = qu_max * L_use * x_corte
    else:
        Vu_1way = 0.0
        
    phi_Vc_1way = phi_v * 0.17 * 1.0 * math.sqrt(fc_basico) * (L_use * 1000) * (d_z * 10) / 1000.0 # kN
    ok_1way = phi_Vc_1way >= Vu_1way
    
    # Punzonamiento a d/2
    bo_1 = c1_col/100.0 + d_z_m
    bo_2 = c2_col/100.0 + d_z_m
    bo_perim = 2 * (bo_1 + bo_2)
    Area_punz = bo_1 * bo_2
    Vu_punz = P_ult - qu_max * Area_punz
    
    beta_c = max(c1_col, c2_col) / min(c1_col, c2_col)
    alpha_s = 40 # interior column default
    Vc1 = 0.33 * math.sqrt(fc_basico)
    Vc2 = 0.17 * (1 + 2/beta_c) * math.sqrt(fc_basico)
    Vc3 = 0.083 * (2 + alpha_s * (d_z*10) / (bo_perim*1000)) * math.sqrt(fc_basico)
    vc_min_MPa = min(Vc1, Vc2, Vc3)
    
    phi_Vc_punz = phi_v * vc_min_MPa * (bo_perim * 1000) * (d_z * 10) / 1000.0 # kN
    ok_punz = phi_Vc_punz >= Vu_punz
    
    # Diseño a Flexión en la cara de la columna
    Mu_flex = qu_max * L_use * (lv_b**2) / 2.0 # kN-m en ancho L
    phi_Mn_max = phi_f * (0.319*fc_basico) * (L_use*1000) * (d_z*10)**2 / 1e6 # limite tope approx de falla balanceada
    
    Rn_z = (Mu_flex * 1e6) / (phi_f * (L_use*1000) * (d_z*10)**2)
    disc_z = 1 - 2*Rn_z/(0.85*fc_basico)
    if disc_z > 0:
        rho_req = (0.85*fc_basico/fy_basico)*(1 - math.sqrt(disc_z))
    else:
        rho_req = 0.02 # Falla, necesita mas peralte
    rho_min_zap = 0.0018
    rho_use = max(rho_req, rho_min_zap)
    As_req_total = rho_use * (L_use*100) * d_z # cm2
    n_barras_Z = math.ceil(As_req_total / (REBAR_MM[bar_z]))
    separacion_S = (B_use*100 - 2*recub_z) / max(1, n_barras_Z - 1)
    
    tab_res, tab_dwg, tab_apu = st.tabs(["📋 Resultados del Diseño", "📏 Plano 3000 (DXF)", "💰 Cantidades APU"])
    
    with tab_res:
        st.markdown(f"**Revisión Estructural: f'c = {fc_basico} MPa | fy = {fy_basico} MPa**")
        
        # ── EXPLICIT LATEX FORMULAS FOR CHECKS ──
        st.markdown(r"**1. Cortante Unidireccional (Tipo Viga):** $\phi V_c \ge V_u$")
        st.latex(r"\phi V_c = \phi \cdot 0.17 \lambda \sqrt{f'_c} b_w d")
        if ok_1way:
            st.success(f"✅ Aprobado Cortante 1D: $\\phi V_c = {phi_Vc_1way:.1f}$ kN $\\ge V_u = {Vu_1way:.1f}$ kN")
        else:
            st.error(f"❌ No Aprobado Cortante 1D: $\\phi V_c = {phi_Vc_1way:.1f}$ kN $< V_u = {Vu_1way:.1f}$ kN $\\rightarrow$ **Aumentar Espesor H**")

        st.markdown(r"**2. Cortante Bidireccional (Punzonamiento):** $\phi V_c \ge V_{up}$")
        st.latex(r"\phi V_c = \phi \cdot \min\left(0.33, 0.17(1+\frac{2}{\beta}), 0.083(2+\frac{\alpha_s d}{b_o})\right) \sqrt{f'_c} b_o d")
        if ok_punz:
            st.success(f"✅ Aprobado Punzonamiento: $\\phi V_c = {phi_Vc_punz:.1f}$ kN $\\ge V_{{up}} = {Vu_punz:.1f}$ kN")
        else:
            st.error(f"❌ No Aprobado Punzonamiento: $\\phi V_c = {phi_Vc_punz:.1f}$ kN $< V_{{up}} = {Vu_punz:.1f}$ kN $\\rightarrow$ **Aumentar Espesor H o sección de Columna**")
        
        st.markdown("---")
        data_res = [
            {"Revisión": "Geometría Propuesta", "Solicitado": f"Area Req = {Area_req:.2f} m²", "Capacidad/Provisto": f"Area Prov. = {A_use:.2f} m²", "Estado": "✅ OK" if A_use>=Area_req else "⚠️ Subdimensionado"},
            {"Revisión": "Esfuerzo de Contacto (qu)", "Solicitado": f"{qu_max:.2f} kPa", "Capacidad/Provisto": f"N/A", "Estado": "N/A"},
            {"Revisión": "Flexión en Cara de Col.", "Solicitado": f"Mu = {Mu_flex:.1f} kN-m", "Capacidad/Provisto": f"As_req = {As_req_total:.1f} cm²", "Estado": "✅ OK" if disc_z>0 else "❌ Rompe en compresión"},
            {"Revisión": "Distribución Acero", "Solicitado": f"Usar {n_barras_Z} vars", "Capacidad/Provisto": f"Sep. = {separacion_S:.1f} cm", "Estado": "✅ Aprobado" if separacion_S<=45 else "⚠️ Separación muy alta"},
        ]
        st.table(pd.DataFrame(data_res))
        
        # Generar Memoria
        doc_zap = Document()
        doc_zap.add_heading(f"Memoria de Cálculo — Zapata {B_use}x{L_use}m", 0)
        doc_zap.add_paragraph(f"Norma Utilizada: {norma_sel}")
        doc_zap.add_paragraph(f"Materiales: f'c = {fc_basico} MPa, fy = {fy_basico} MPa")
        doc_zap.add_heading("Resultados", level=1)
        doc_zap.add_paragraph(f"Punzonamiento φVc: {phi_Vc_punz:.1f} kN >= Vu: {Vu_punz:.1f} kN")
        doc_zap.add_paragraph(f"Acero As Requerido: {As_req_total:.1f} cm2. Arreglo: {n_barras_Z} varillas {bar_z} @ {separacion_S:.1f} cm")
        f_zap_io = io.BytesIO()
        doc_zap.save(f_zap_io)
        f_zap_io.seek(0)
        st.download_button("Descargar Memoria DOCX", data=f_zap_io, file_name="Memoria_Zapata.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    with tab_dwg:
        st.subheader("🧊 Visualización 3D de la Fundación")
        fig3d = go.Figure()
        
        # Zap
        x_z = [-B_use/2, B_use/2, B_use/2, -B_use/2, -B_use/2, B_use/2, B_use/2, -B_use/2]
        y_z = [-L_use/2, -L_use/2, L_use/2, L_use/2, -L_use/2, -L_use/2, L_use/2, L_use/2]
        z_z = [0, 0, 0, 0, H_zap/100.0, H_zap/100.0, H_zap/100.0, H_zap/100.0]
        fig3d.add_trace(go.Mesh3d(x=x_z, y=y_z, z=z_z, alphahull=0, opacity=0.3, color='steelblue', name='Zapata'))

        # Columna
        c1_m = c1_col/100.0
        c2_m = c2_col/100.0
        x_c = [-c1_m/2, c1_m/2, c1_m/2, -c1_m/2, -c1_m/2, c1_m/2, c1_m/2, -c1_m/2]
        y_c = [-c2_m/2, -c2_m/2, c2_m/2, c2_m/2, -c2_m/2, -c2_m/2, c2_m/2, c2_m/2]
        z_c = [H_zap/100.0]*4 + [H_zap/100.0 + 1.0]*4 # 1.0m height column stub
        fig3d.add_trace(go.Mesh3d(x=x_c, y=y_c, z=z_c, alphahull=0, opacity=0.6, color='gray', name='Columna'))

        fig3d.update_layout(scene=dict(aspectmode='data', xaxis_title='B (m)', yaxis_title='L (m)', zaxis_title='Z (m)'),
                            margin=dict(l=0, r=0, b=0, t=0), height=450, showlegend=True, dragmode='turntable')
        st.plotly_chart(fig3d, use_container_width=True)
        
        st.markdown("---")
        st.write("#### Geometría de Zapata 2D")
        fig_z, ax_z = plt.subplots(figsize=(6, 4))
        ax_z.set_facecolor('#1a1a2e'); fig_z.patch.set_facecolor('#1a1a2e')
        # Zapata
        ax_z.add_patch(patches.Rectangle((0,0), B_use*100, H_zap, linewidth=2, edgecolor='darkgray', facecolor='#4a4a6a'))
        # Columna
        pos_x_col = (B_use*100 - c1_col) / 2
        ax_z.add_patch(patches.Rectangle((pos_x_col, H_zap), c1_col, 50, linewidth=2, edgecolor='white', facecolor='#6a6a8a'))
        # Varillas (Sección transversal)
        for i in range(n_barras_Z):
            xi = recub_z + i * separacion_S
            ax_z.add_patch(plt.Circle((xi, recub_z), db_bar_z/10, color='#ff6b35', zorder=5))
        
        ax_z.text(B_use*100/2, H_zap/2, f"{n_barras_Z} varillas {bar_z} L={L_use}m\nSep:{separacion_S:.1f}cm", color='white', ha='center', va='center')
        ax_z.set_xlim(-20, B_use*100+20)
        ax_z.set_ylim(-10, H_zap+70)
        ax_z.axis('off')
        st.pyplot(fig_z)
        
        st.markdown("#### 💾 Exportar Autocad")
        doc_dxf = ezdxf.new('R2010')
        doc_dxf.units = ezdxf.units.CM
        msp = doc_dxf.modelspace()
        # Elevacion
        msp.add_lwpolyline([(0,0), (B_use*100,0), (B_use*100,H_zap), (0,H_zap), (0,0)], dxfattribs={'layer': 'CONCRETO', 'color': 7})
        msp.add_lwpolyline([(pos_x_col,H_zap), (pos_x_col,H_zap+50), (pos_x_col+c1_col,H_zap+50), (pos_x_col+c1_col,H_zap)], dxfattribs={'layer': 'CONCRETO', 'color': 7})
        for i in range(n_barras_Z):
            xi = recub_z + i * separacion_S
            msp.add_circle((xi, recub_z), db_bar_z/10, dxfattribs={'layer': 'ACERO', 'color': 1})
            
        out_stream = io.StringIO()
        doc_dxf.write(out_stream)
        st.download_button(label="Descargar Plano DXF (Elevación)", data=out_stream.getvalue(), file_name=f"Elevacion_Zapata_{B_use}x{L_use}.dxf", mime="application/dxf")

    with tab_apu:
        vol_excavacion = (B_use + 0.5) * (L_use + 0.5) * Df_z # Sobre excavacion de 25cm por lado
        vol_concreto_zap = B_use * L_use * (H_zap/100.0)
        # Asumiendo 2 mallas iguales (inferiores) en B y L para simplificar
        peso_barras_B = n_barras_Z * (L_use + 2*H_zap/100.0) * REBAR_MM[bar_z]*100 * 7.85e-3 # gancho
        n_barras_L = math.ceil(As_req_total / REBAR_MM[bar_z]) # simplificacion si fuera cuadrada, asumiendo misma cuantia
        peso_barras_L = n_barras_L * (B_use + 2*H_zap/100.0) * REBAR_MM[bar_z]*100 * 7.85e-3
        peso_total_acero_zap = peso_barras_B + peso_barras_L
        
        st.write(f"**Excavación:** {vol_excavacion:.2f} m³")
        st.write(f"**Concreto:** {vol_concreto_zap:.2f} m³")
        st.write(f"**Acero de Refuerzo:** {peso_total_acero_zap:.1f} kg")
        st.write(f"**Cuantía (kg/m³)** {(peso_total_acero_zap/vol_concreto_zap):.1f} kg/m³")

        if "apu_config" in st.session_state:
            st.markdown("---")
            st.markdown("### 💰 Presupuesto Estimado (Promedio de Fuentes Regionales)")
            apu = st.session_state.apu_config
            mon = apu["moneda"]
            c_excav = vol_excavacion * 25000 # Costo local asumido manual por m3
            
            bultos_zap = vol_concreto_zap * 350 / 50.0 
            vol_arena_z = vol_concreto_zap * 0.55
            vol_grava_z = vol_concreto_zap * 0.8
            
            c_cem = bultos_zap * apu["cemento"]
            c_ace = peso_total_acero_zap * apu["acero"]
            c_are = vol_arena_z * apu["arena"]
            c_gra = vol_grava_z * apu["grava"]
            total_mat = c_cem + c_ace + c_are + c_gra + c_excav
            
            # MO
            total_dias_mo = (peso_total_acero_zap * 0.04) + (vol_concreto_zap * 0.4) + (vol_excavacion * 0.3)
            costo_mo = total_dias_mo * apu.get("costo_dia_mo", 69333.33)
            
            # Indirectos
            costo_directo = total_mat + costo_mo
            herramienta = costo_mo * apu.get("pct_herramienta", 0.05)
            aiu = costo_directo * apu.get("pct_aui", 0.30)
            utilidad = costo_directo * apu.get("pct_util", 0.05)
            iva = utilidad * apu.get("iva", 0.19)
            
            total_proyecto = costo_directo + herramienta + aiu + iva
            
            data_zap_apu = {
                "Item": ["Excavación (m³)", "Cemento (bultos)", "Acero (kg)", "Arena (m³)", "Grava (m³)", 
                         "Mano de Obra (días)", "Herramienta Menor", "A.I.U.", "IVA s/Utilidad", "TOTAL PRESUPUESTO"],
                "Cantidad": [f"{vol_excavacion:.2f}", f"{bultos_zap:.1f}", f"{peso_total_acero_zap:.1f}", f"{vol_arena_z:.2f}", f"{vol_grava_z:.2f}", 
                             f"{total_dias_mo:.2f}", f"{apu.get('pct_herramienta', 0.05)*100:.1f}% MO", 
                             f"{apu.get('pct_aui', 0.3)*100:.1f}% CD", f"{apu.get('iva', 0.19)*100:.1f}% Util", ""],
                f"Subtotal [{mon}]": [f"{c_excav:,.2f}", f"{c_cem:,.2f}", f"{c_ace:,.2f}", f"{c_are:,.2f}", f"{c_gra:,.2f}", 
                                      f"{costo_mo:,.2f}", f"{herramienta:,.2f}", f"{aiu:,.2f}", f"{iva:,.2f}", f"**{total_proyecto:,.2f}**"]
            }
            st.dataframe(pd.DataFrame(data_zap_apu), use_container_width=True, hide_index=True)
            
            # Excel APU Export
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                df_export = pd.DataFrame({
                    "Item": ["Excavación", "Cemento", "Acero", "Arena", "Grava", "Mano de Obra"],
                    "Cantidad": [vol_excavacion, bultos_zap, peso_total_acero_zap, vol_arena_z, vol_grava_z, total_dias_mo],
                    "Unidad": [25000, apu['cemento'], apu['acero'], apu['arena'], apu['grava'], apu.get('costo_dia_mo', 69333.33)]
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
                worksheet.write_formula(row, 3, f'=D7*{apu.get("pct_herramienta", 0.05)}', money_fmt)
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
                               file_name=f"APU_Zapata_{B_use}x{L_use}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("💡 Ve a la página 'APU Mercado' para cargar los costos base de agregados, acero y cemento y que tu presupuesto se genere automáticamente.")

