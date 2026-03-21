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

if any(n in norma_sel for n in ["Colombia", "EE.UU.", "Perú", "México", "Venezuela"]):
    REBAR_DICT = {
        "N.3 (3/8\")": {"area": 0.71, "db": 9.5},
        "N.4 (1/2\")": {"area": 1.29, "db": 12.7},
        "N.5 (5/8\")": {"area": 1.99, "db": 15.9},
        "N.6 (3/4\")": {"area": 2.84, "db": 19.1},
        "N.7 (7/8\")": {"area": 3.87, "db": 22.2},
        "N.8 (1\")":   {"area": 5.10, "db": 25.4},
    }
    def_idx = 1 # N.4
else:
    REBAR_DICT = {
        "10 mm": {"area": 0.785, "db": 10.0},
        "12 mm": {"area": 1.131, "db": 12.0},
        "14 mm": {"area": 1.539, "db": 14.0},
        "16 mm": {"area": 2.011, "db": 16.0},
        "18 mm": {"area": 2.545, "db": 18.0},
        "20 mm": {"area": 3.142, "db": 20.0},
        "22 mm": {"area": 3.801, "db": 22.0},
        "25 mm": {"area": 4.909, "db": 25.0},
    }
    def_idx = 1 # 12 mm

# ─────────────────────────────────────────────
# HELPER GLOBAL: BOUSSINESQ INFLUENCE FACTOR
# (defined here to be accessible from all sections)
# ─────────────────────────────────────────────
def I_z_bous(m, n):
    V1 = m**2 + n**2 + 1
    V2 = m**2 * n**2
    term1 = (2*m*n*math.sqrt(V1)) / (V1 + V2) if (V1 + V2) != 0 else 0
    term2 = (V1 + 1) / V1 if V1 != 0 else 0
    angulo = math.atan2(2*m*n*math.sqrt(V1), (V1 - V2))
    if V1 - V2 < 0:
        angulo += math.pi
    return (1 / (4 * math.pi)) * (term1 * term2 + angulo)

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
    st.info(_t(
        "📺 **Modo de uso:** Ingresa φ, c, γ y la geometría de la zapata. "
        "El módulo calcula la capacidad última de Terzaghi con influencia del NF, "
        "grafica el diagrama Vesic (1973) para tipo de falla y el bulbo de presiones.",
        "📺 **How to use:** Enter φ, c, γ and footing geometry. Module calculates "
        "Terzaghi ultimate capacity with water-table correction, Vesic failure-type chart "
        "and pressure bulb."
    ))

    # ── CONVERSOR DE UNIDADES ───────────────────────────────────────────────
    with st.container():
        st.markdown("**🔄 Conversor Rápido de Resistencia de Suelo**")
        uc1, uc2, uc3 = st.columns([1, 1, 2])
        with uc1:
            q_conv_unit = st.selectbox(_t("Unidad de entrada:", "Input Unit:"),
                ["kPa (kN/m²)", "ton/m²", "kg/cm²", "MPa", "psi", "kN/m²"],
                key="q_conv_unit_terz")
        with uc2:
            q_conv_val = st.number_input(_t("Valor:", "Value:"), value=1.0, step=0.1, key="q_conv_val_terz")
        with uc3:
            _conv = {"kPa (kN/m²)": q_conv_val, "ton/m²": q_conv_val*9.80665,
                     "kg/cm²": q_conv_val*98.0665, "MPa": q_conv_val*1000.0,
                     "psi": q_conv_val*6.89476, "kN/m²": q_conv_val}.get(q_conv_unit, q_conv_val)
            st.markdown(f"| Unidad | Valor |\n|--------|-------|\n"
                        f"| **kPa** | `{_conv:.3f}` |\n"
                        f"| **ton/m²** | `{_conv/9.80665:.3f}` |\n"
                        f"| **kg/cm²** | `{_conv/98.0665:.4f}` |\n"
                        f"| **MPa** | `{_conv/1000.0:.5f}` |\n"
                        f"| **psi** | `{_conv/6.89476:.2f}` |")
    st.divider()

    # ── ENTRADAS ────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("##### 🏔️ Parámetros Geotécnicos")
        phi_ang  = st.number_input(_t("Ángulo de fricción φ [°]","Friction angle φ [°]"),
                                   0.0, 50.0, st.session_state.get("z_phi", 30.0), 1.0, key="z_phi")
        coh_unit = st.selectbox(_t("Unidad cohesión:","Cohesion Unit:"),
                                ["kPa", "kg/cm²", "ton/m²"], key="coh_u")
        coh_val  = st.number_input(f"c [{coh_unit}]", 0.0, 200.0,
                                   st.session_state.get("coh_val", 5.0 if coh_unit=="kPa" else 0.05),
                                   0.5 if coh_unit=="kPa" else 0.01, key="coh_val")
        coh_c    = coh_val if coh_unit=="kPa" else (coh_val*98.0665 if coh_unit=="kg/cm²" else coh_val*9.80665)
        gam_unit = st.selectbox(_t("Unidad γ húmedo:","γ moist Unit:"),
                                ["kN/m³", "ton/m³", "kg/m³"], key="gam_u")
        gam_val  = st.number_input(f"γ [{gam_unit}]", 10.0,
                                   25.0 if gam_unit != "kg/m³" else 2500.0,
                                   st.session_state.get("gam_val", 18.0 if gam_unit != "kg/m³" else 1800.0),
                                   0.5, key="gam_val")
        gamma_s  = gam_val if gam_unit=="kN/m³" else (gam_val*9.80665 if gam_unit=="ton/m³" else gam_val*0.00980665)
        gamma_sat_t = st.number_input("γ saturado [kN/m³]", 16.0, 25.0, 20.0, 0.5, key="z_gsat")
        gamma_w  = 9.81
    with c2:
        st.markdown("##### 🏗️ Geometría y Carga")
        forma_zap = st.selectbox(_t("Forma de zapata","Footing shape"),
                                 ["Cuadrada", "Continua (Muro)", "Circular"] if lang=="Español"
                                 else ["Square", "Continuous (Wall)", "Circular"], key="z_shape")
        B_cp  = st.number_input(_t("Ancho B [m]","Width B [m]"), 0.5, 10.0,
                                st.session_state.get("cp_b", 2.0), 0.1, key="cp_b")
        L_cp  = st.number_input(_t("Largo L [m]","Length L [m]"), 0.5, 100.0,
                                st.session_state.get("cp_l", 2.0), 0.1, key="cp_l")
        Hz_cp = st.number_input(_t("Altura zapata Hz [m]","Footing height Hz [m]"),
                                0.1, 2.0, 0.5, 0.05, key="z_hz_cp")
        Df_cp = st.number_input(_t("Profundidad Df [m]","Depth Df [m]"), 0.0, 10.0,
                                st.session_state.get("cp_df", 1.5), 0.1, key="cp_df")
        b_col_cp = st.number_input(_t("Lado columna b [m]","Column side b [m]"), 0.1, 2.0, 0.4, 0.05, key="z_bcol_cp")
        Q_act  = st.number_input("Carga vertical actuante Q [kN]", 10.0, 50000.0, 3000.0, 100.0, key="z_Qact")
    with c3:
        st.markdown("##### 💧 Nivel Freático y FS")
        NF_prof = st.number_input("NF — Profundidad nivel freático [m]", 0.0, 20.0, 1.0, 0.5, key="z_nf")
        FS_terz = st.number_input(_t("Factor de Seguridad (FS)","Safety Factor (FS)"),
                                  1.0, 5.0, st.session_state.get("z_fs", 3.0), 0.1, key="z_fs")
        N_spt   = st.number_input("N60 campo (SPT)", 0, 100, 14, 1, key="z_spt")
        st.caption("ℹ️ N60 se usa para clasificar tipo de falla (Vesic 1973)")

    # ── CÁLCULO GEOTÉCNICO ──────────────────────────────────────────────────
    phi_rad = math.radians(phi_ang)

    # Factores capacidad — Terzaghi
    if phi_ang == 0:
        Nc, Nq, Ngamma = 5.7, 1.0, 0.0
    else:
        a_t    = math.exp((0.75*math.pi - phi_rad/2)*math.tan(phi_rad))
        Nq     = (a_t**2) / (2*math.cos(math.radians(45) + phi_rad/2)**2)
        Nc     = (Nq - 1) / math.tan(phi_rad)
        Ngamma = 2*(Nq+1)*math.tan(phi_rad) / (1 + 0.4*math.sin(4*phi_rad))

    # Factores de forma
    if forma_zap in ["Cuadrada", "Square"]:
        sc, sq, sgamma = 1.3, 1.0, 0.8
    elif forma_zap in ["Circular"]:
        sc, sq, sgamma = 1.3, 1.0, 0.6
    else:
        sc, sq, sgamma = 1.0, 1.0, 1.0

    # Corrección por nivel freático (Casos I / II / III)
    gamma_prime = gamma_sat_t - gamma_w
    if NF_prof <= Df_cp:                         # Caso I: NF sobre el desplante
        q_sob    = gamma_s*NF_prof + gamma_prime*(Df_cp - NF_prof)
        gamma_eff = gamma_prime
        caso_nf  = "I"
    elif NF_prof < Df_cp + B_cp:                 # Caso II: NF entre Df y Df+B
        z2        = NF_prof - Df_cp
        gamma_eff = gamma_s + (z2/B_cp)*(gamma_prime - gamma_s) if B_cp > 0 else gamma_s
        q_sob    = gamma_s*Df_cp
        caso_nf  = "II"
    else:                                        # Caso III: NF muy profundo
        q_sob    = gamma_s*Df_cp
        gamma_eff = gamma_s
        caso_nf  = "III"

    q_ult  = sc*coh_c*Nc + sq*q_sob*Nq + sgamma*0.5*gamma_eff*B_cp*Ngamma
    q_adm  = q_ult / FS_terz
    Q_ult  = q_ult * B_cp * L_cp
    FS_calc = Q_ult / Q_act if Q_act > 0 else 999.0
    cumplio = FS_calc >= FS_terz

    # ── RESULTADOS ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 📊 Resultados de Capacidad Portante")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.dataframe(pd.DataFrame([
            {"Parámetro": "Nc",                  "Valor": f"{Nc:.3f}"},
            {"Parámetro": "Nq",                  "Valor": f"{Nq:.3f}"},
            {"Parámetro": "Nγ",                  "Valor": f"{Ngamma:.3f}"},
            {"Parámetro": "sc / sq / sγ",         "Valor": f"{sc} / {sq} / {sgamma}"},
            {"Parámetro": f"Caso NF",             "Valor": f"Caso {caso_nf} | NF={NF_prof}m"},
            {"Parámetro": "q sobrecarga",         "Valor": f"{q_sob:.2f} kPa"},
            {"Parámetro": "γ' efectivo",          "Valor": f"{gamma_eff:.2f} kN/m³"},
            {"Parámetro": "q_ult",                "Valor": f"{q_ult:.2f} kPa"},
            {"Parámetro": "Q_ult = q_ult·B·L",   "Valor": f"{Q_ult:.1f} kN"},
            {"Parámetro": "FS calculado",         "Valor": f"{FS_calc:.3f}"},
        ]), use_container_width=True, hide_index=True)
    with col_r2:
        st.markdown("**q_adm en todas las unidades:**")
        m1,m2,m3 = st.columns(3)
        m1.metric("kPa",    f"{q_adm:.1f}")
        m2.metric("ton/m²", f"{q_adm/9.80665:.2f}")
        m3.metric("kg/cm²", f"{q_adm/98.0665:.4f}")
        m4,m5 = st.columns(2)
        m4.metric("MPa",    f"{q_adm/1000:.5f}")
        m5.metric("psi",    f"{q_adm/6.89476:.2f}")
        if cumplio:
            st.success(f"✅ q_adm = **{q_adm:.2f} kPa** | FS = {FS_calc:.2f} ≥ {FS_terz}")
        else:
            st.error(f"❌ q_adm = {q_adm:.2f} kPa | FS = {FS_calc:.2f} < {FS_terz} → Revisar dimensiones")

    # ── GRÁFICA: TIPO DE FALLA (Vesic 1973 / SPT) ──────────────────────────
    st.divider()
    st.markdown("#### 📈 Diagrama Tipo de Falla — Vesic (1973)")
    Dr_pct = min(100.0, 1.08 * math.sqrt(max(N_spt, 0) / 60.0) * 100)
    Df_B   = Df_cp / B_cp if B_cp > 0 else 0.0

    fig_ves, ax_ves = plt.subplots(figsize=(8, 5))
    ax_ves.set_facecolor("#0f1117"); fig_ves.patch.set_facecolor("#0f1117")
    Dr_arr = np.linspace(0, 100, 300)
    # Límites aproximados de Vesic (1973) expresados como -Df/B* vs Dr
    c1v = -0.6 + 0.006*Dr_arr             # Punzonamiento → Local
    c2v = -2.5 + 0.030*Dr_arr             # Local → General
    ax_ves.plot(Dr_arr, c1v, color="#4fc3f7", lw=1.8, label="Límite punz./local")
    ax_ves.plot(Dr_arr, c2v, color="#81d4fa", lw=1.8, label="Límite local/general")
    ax_ves.fill_between(Dr_arr, c2v, -5, alpha=0.18, color="#e53935")
    ax_ves.fill_between(Dr_arr, c1v, c2v, alpha=0.15, color="#fb8c00")
    ax_ves.fill_between(Dr_arr, 0, c1v, alpha=0.12, color="#43a047")
    ax_ves.text(10, -0.3, "Falla por\nPunzonamiento", color="white", fontsize=8, ha="center")
    ax_ves.text(50, -1.5, "Falla local\npor corte",   color="white", fontsize=8, ha="center")
    ax_ves.text(80, -3.5, "Falla general\npor corte", color="white", fontsize=8, ha="center")
    # Miniatura fundación
    rec_w = 15; rec_h = 0.3
    ax_ves.add_patch(patches.Rectangle((2, -Df_B - rec_h), rec_w, rec_h,
                                       fc="#888", ec="white", lw=0.8))
    ax_ves.annotate(f"B={B_cp}m\nHz={Hz_cp}m", (2+rec_w/2, -Df_B - rec_h*2),
                    color="yellow", fontsize=7, ha="center")
    # Punto actual
    ax_ves.plot(Dr_pct, -Df_B, "o", color="red", ms=11, zorder=6,
                label=f"Dr≈{Dr_pct:.0f}% | Df/B={Df_B:.2f}")
    ax_ves.set_xlim(0, 100); ax_ves.set_ylim(-5, 0)
    ax_ves.set_xlabel("Densidad relativa Dr (%)", color="white")
    ax_ves.set_ylabel("-Df / B*", color="white")
    ax_ves.set_title(f"Tipo de Falla — N60={N_spt} campo → Dr≈{Dr_pct:.0f}%  |  Df/B={Df_B:.2f}", color="white")
    ax_ves.tick_params(colors="white"); ax_ves.spines[:].set_color("#444")
    ax_ves.legend(loc="lower right", fontsize=8, facecolor="#111", labelcolor="white")
    st.pyplot(fig_ves)

    # ── GRÁFICA: BULBO DE PRESIONES / MECANISMO DE FALLA ───────────────────
    st.divider()
    st.markdown("#### 🌐 Mecanismo de Falla y Bulbo de Presiones (Terzaghi)")
    fig_tb, ax_tb = plt.subplots(figsize=(10, 7))
    ax_tb.set_facecolor("#0f1117"); fig_tb.patch.set_facecolor("#0f1117")

    half_B = B_cp / 2.0
    zap_bot = -(Df_cp + Hz_cp)

    # Suelo de relleno encima del desplante (sombreado suave)
    ax_tb.add_patch(patches.Rectangle((-B_cp*5, 0), B_cp*10, -Df_cp,
                                      fc="#2e7d32", alpha=0.18, ec="none"))
    # Zona I — Triángulo activo (bajo la zapata)
    ang_I = math.pi/4 + phi_rad/2
    tri_pts = [(-half_B, zap_bot), (half_B, zap_bot),
               (0, zap_bot - half_B*math.tan(ang_I))]
    ax_tb.add_patch(plt.Polygon(tri_pts, fc="#e8c4a0", ec="#c9956e", lw=0.8,
                                alpha=0.85, label="Zona I — Activa"))

    # Zona II — Arco logarítmico (Prandtl)
    if phi_rad > 0:
        r0 = half_B / math.cos(ang_I - math.pi/2) if math.cos(ang_I-math.pi/2) != 0 else half_B
        r0 = half_B * 1.4
        theta_arr = np.linspace(math.pi/2, math.pi, 40)
        r_arr = r0 * np.exp(theta_arr * math.tan(phi_rad))
        xs = half_B + r_arr * np.cos(theta_arr)
        ys = zap_bot + r_arr * np.sin(theta_arr)
        # Espejo
        xs2 = -half_B - r_arr * np.cos(theta_arr)
        ys2 = zap_bot + r_arr * np.sin(theta_arr)
        ax_tb.fill(np.append(xs, xs[::-1]), np.append(ys, ys[::-1]),
                   fc="#f4a261", alpha=0.55, label="Zona II — Radial", ec="none")
        ax_tb.fill(np.append(xs2, xs2[::-1]), np.append(ys2, ys2[::-1]),
                   fc="#f4a261", alpha=0.55, ec="none")

    # Zapata
    ax_tb.add_patch(patches.Rectangle((-half_B, zap_bot), B_cp, Hz_cp,
                                      fc="#546e7a", ec="white", lw=1.5, zorder=4,
                                      label=f"Zapata {B_cp}×{L_cp}m"))
    # Columna
    ax_tb.add_patch(patches.Rectangle((-b_col_cp/2, 0), b_col_cp, -Df_cp + Hz_cp*0.1,
                                      fc="#78909c", ec="white", lw=1, zorder=4))
    # Bulbo de presiones Boussinesq (isolíneas)
    _xg = np.linspace(-B_cp*3, B_cp*3, 120)
    _zg = np.linspace(zap_bot, zap_bot - B_cp*2.5, 80)
    Xg, Zg = np.meshgrid(_xg, _zg)
    q0_bulbo = q_ult
    _sigma = np.zeros_like(Xg)
    for ii in range(Xg.shape[0]):
        for jj in range(Xg.shape[1]):
            dz = abs(Zg[ii,jj] - zap_bot)
            if dz > 0.05:
                mm = (half_B) / dz; nn = (L_cp/2) / dz
                _sigma[ii,jj] = 4 * q0_bulbo * I_z_bous(mm, nn)
    cs = ax_tb.contourf(Xg, Zg, _sigma, levels=[q0_bulbo*0.1, q0_bulbo*0.2, q0_bulbo*0.4,
                         q0_bulbo*0.6, q0_bulbo*0.8], cmap="YlOrRd", alpha=0.5, zorder=1)
    fig_tb.colorbar(cs, ax=ax_tb, label="Δσz [kPa]", shrink=0.7)
    # Nivel freático
    if NF_prof < Df_cp + B_cp*2.5:
        ax_tb.axhline(-NF_prof, color="#29b6f6", lw=1.5, linestyle=":",
                      label=f"▽ NF = {NF_prof}m")
    ax_tb.axhline(zap_bot, color="#888", lw=0.8, linestyle="--")
    ax_tb.axhline(0, color="#555", lw=0.5)
    ax_tb.set_xlim(-B_cp*4, B_cp*4)
    ax_tb.set_ylim(zap_bot - B_cp*2.8, 0.5)
    ax_tb.set_xlabel("Distancia [m]", color="white")
    ax_tb.set_ylabel("Profundidad [m]", color="white")
    ax_tb.set_title(f"Bulbo de Presiones + Falla Terzaghi — q_ult={q_ult:.1f} kPa | q_adm={q_adm:.1f} kPa",
                    color="white", fontsize=11)
    ax_tb.tick_params(colors="white"); ax_tb.spines[:].set_color("#444")
    ax_tb.legend(loc="upper right", fontsize=8, facecolor="#111", labelcolor="white")
    st.pyplot(fig_tb)



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

        c1_col = st.number_input(_t("Dim. Columna c1 (dir. B) [cm]", "Column dim. c1 (B dir.) [cm]"), min_value=5.0, value=40.0, step=5.0)
        c2_col = st.number_input(_t("Dim. Columna c2 (dir. L) [cm]", "Column dim. c2 (L dir.) [cm]"), min_value=5.0, value=40.0, step=5.0)
        gamma_prom = st.number_input(_t("γ_promedio (suelo+concreto) [kN/m³]", "γ_avg (soil+concrete) [kN/m³]"), value=20.0)
        Df_z = st.number_input(_t("Desplante Df [m]", "Footing Depth Df [m]"), value=1.0, step=0.1)
        st.caption(_t("ℹ️ Si hay momento, se aplica en la dirección de L. Use Mu en la dirección B para la verificación manual.",
                      "ℹ️ Moment applied along L direction. For B-direction moment, verify manually."))

    with colC:
        st.write("#### Diseño Estructural")
        H_zap = st.number_input("Espesor H propuesto [cm]", value=50.0, step=5.0)
        recub_z = st.number_input("Recubrimiento al suelo [cm]", value=7.5, step=0.5)
        bar_z = st.selectbox("Varilla a utilizar:", list(REBAR_DICT.keys()), index=def_idx)
        A_bar_z = REBAR_DICT[bar_z]["area"] * 100 # mm2
        db_bar_z = REBAR_DICT[bar_z]["db"] # mm
        
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
    
    # ─── Validación de entradas críticas ──────────────────────────────────────
    if c1_col <= 0 or c2_col <= 0:
        st.error("❌ Las dimensiones de la columna (c1, c2) deben ser mayores a 0 cm.")
        st.stop()

    # Presion de contacto factorizada qu (momento aplicado en eje L)
    A_use = B_use * L_use
    qu_max = P_ult / A_use + (6 * M_ult / (B_use * L_use**2) if M_ult > 0 else 0)
    qu_min = P_ult / A_use - (6 * M_ult / (B_use * L_use**2) if M_ult > 0 else 0)
    # Presión promedio en la sección critica de cortante y punzonamiento
    qu_avg = (qu_max + max(qu_min, 0)) / 2.0

    # Peralte efectivo d
    d_z = H_zap - recub_z - (db_bar_z/10.0)
    d_z_m = d_z / 100.0

    # Cortante Unidireccional (Viga) a 'd' de la cara de la columna
    lv_b = (B_use - c1_col/100.0) / 2.0  # voladizo en dir. B
    lv_l = (L_use - c2_col/100.0) / 2.0  # voladizo en dir. L
    x_corte = lv_b - d_z_m
    if x_corte > 0:
        Vu_1way = qu_avg * L_use * x_corte
    else:
        Vu_1way = 0.0

    phi_Vc_1way = phi_v * 0.17 * 1.0 * math.sqrt(fc_basico) * (L_use * 1000) * (d_z * 10) / 1000.0  # kN
    ok_1way = phi_Vc_1way >= Vu_1way

    # Punzonamiento a d/2 — usando presión promedio sobre el área crítica
    bo_1 = c1_col/100.0 + d_z_m
    bo_2 = c2_col/100.0 + d_z_m
    bo_perim = 2 * (bo_1 + bo_2)
    Area_punz = bo_1 * bo_2
    Vu_punz = P_ult - qu_avg * Area_punz  # presión promedio en zona critica

    _min_col = min(c1_col, c2_col)
    beta_c = max(c1_col, c2_col) / _min_col if _min_col > 0 else 1.0
    alpha_s = 40  # columna interior por defecto
    try:
        Vc1 = 0.33 * math.sqrt(fc_basico)
        Vc2 = 0.17 * (1 + 2/beta_c) * math.sqrt(fc_basico)
        Vc3 = 0.083 * (2 + alpha_s * (d_z*10) / (bo_perim*1000)) * math.sqrt(fc_basico)
        vc_min_MPa = min(Vc1, Vc2, Vc3)
    except ZeroDivisionError:
        vc_min_MPa = 0.0
        st.warning("⚠️ División por cero al calcular resistencia a punzonamiento — revise dimensiones.")

    phi_Vc_punz = phi_v * vc_min_MPa * (bo_perim * 1000) * (d_z * 10) / 1000.0  # kN
    ok_punz = phi_Vc_punz >= Vu_punz

    # ─── Diseño a Flexión — DIRECCIÓN B (malla en dir. L) ───────────────────
    Mu_flex_B = qu_avg * L_use * (lv_b**2) / 2.0  # kN-m, ancho L
    try:
        Rn_B = (Mu_flex_B * 1e6) / (phi_f * (L_use*1000) * (d_z*10)**2)
        disc_B = 1 - 2*Rn_B/(0.85*fc_basico)
        rho_B = (0.85*fc_basico/fy_basico)*(1 - math.sqrt(max(disc_B, 0)))
    except (ZeroDivisionError, ValueError):
        rho_B = 0.02
        disc_B = 0
    rho_use_B = max(rho_B, 0.0018)
    As_req_B = rho_use_B * (L_use*100) * d_z  # cm2 para ancho L
    n_barras_B = math.ceil(As_req_B / REBAR_DICT[bar_z]["area"])
    sep_B = (B_use*100 - 2*recub_z) / max(1, n_barras_B - 1)

    # ─── Diseño a Flexión — DIRECCIÓN L (malla en dir. B) ───────────────────
    Mu_flex_L = qu_avg * B_use * (lv_l**2) / 2.0  # kN-m, ancho B
    try:
        Rn_L = (Mu_flex_L * 1e6) / (phi_f * (B_use*1000) * (d_z*10)**2)
        disc_L = 1 - 2*Rn_L/(0.85*fc_basico)
        rho_L = (0.85*fc_basico/fy_basico)*(1 - math.sqrt(max(disc_L, 0)))
    except (ZeroDivisionError, ValueError):
        rho_L = 0.02
        disc_L = 0
    rho_use_L = max(rho_L, 0.0018)
    As_req_L = rho_use_L * (B_use*100) * d_z  # cm2 para ancho B
    n_barras_L = math.ceil(As_req_L / REBAR_DICT[bar_z]["area"])
    sep_L = (L_use*100 - 2*recub_z) / max(1, n_barras_L - 1)

    # aliases for backward compat with display / DXF code
    Mu_flex = Mu_flex_B
    disc_z = disc_B
    As_req_total = As_req_B
    n_barras_Z = n_barras_B
    separacion_S = sep_B
    
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
            {"Revisión": "Presión de Contacto qu_max", "Solicitado": f"{qu_max:.2f} kPa", "Capacidad/Provisto": f"qu_min = {qu_min:.2f} kPa", "Estado": "✅ Sin tensión" if qu_min >= 0 else "⚠️ Tensión en suelo"},
            {"Revisión": "Flexión Dir. B — cara col.", "Solicitado": f"Mu_B = {Mu_flex_B:.1f} kN-m", "Capacidad/Provisto": f"As_B = {As_req_B:.1f} cm² → {n_barras_B} {bar_z} c/{sep_B:.1f}cm", "Estado": "✅ OK" if disc_B>0 else "❌ Rompe en compresión"},
            {"Revisión": "Flexión Dir. L — cara col.", "Solicitado": f"Mu_L = {Mu_flex_L:.1f} kN-m", "Capacidad/Provisto": f"As_L = {As_req_L:.1f} cm² → {n_barras_L} {bar_z} c/{sep_L:.1f}cm", "Estado": "✅ OK" if disc_L>0 else "❌ Rompe en compresión"},
        ]
        st.table(pd.DataFrame(data_res))
        
        # ── MEMORIA DE CÁLCULO COMPLETA ────────────────────────────────────
        import datetime as _dt
        doc_zap = Document()
        doc_zap.add_heading(f"MEMORIA DE CÁLCULO — ZAPATA {B_use:.2f}x{L_use:.2f} m", 0)
        doc_zap.add_paragraph(f"Fecha: {_dt.datetime.now().strftime('%d/%m/%Y %H:%M')}")
        doc_zap.add_paragraph(f"Norma Estructural: {norma_sel}")
        doc_zap.add_paragraph(f"Elaborado con: StructuroPro — Módulo Zapatas NSR-10/ACI-318/Multi-Norma")
        doc_zap.add_heading("1. MATERIALES", level=1)
        doc_zap.add_paragraph(f"  f'c = {fc_basico} MPa  |  fy = {fy_basico} MPa  |  Recubrimiento = {recub_z} cm")
        doc_zap.add_paragraph(f"  Varilla seleccionada: {bar_z}  |  Área unitaria = {REBAR_DICT[bar_z]['area']:.3f} cm²  |  db = {REBAR_DICT[bar_z]['db']:.1f} mm")
        doc_zap.add_heading("2. CARGAS APLICADAS", level=1)
        doc_zap.add_paragraph(f"  Carga de Servicio Ps = {P_svc:.1f} kN   |  Momento de Servicio Ms = {M_svc:.1f} kN·m")
        doc_zap.add_paragraph(f"  Carga Factorizada Pu = {P_ult:.1f} kN   |  Momento Factorizado Mu = {M_ult:.1f} kN·m")
        doc_zap.add_heading("3. DIMENSIONAMIENTO EN PLANTA", level=1)
        doc_zap.add_paragraph(f"  q_adm = {q_adm_z:.2f} kPa  |  γ_prom = {gamma_prom:.1f} kN/m³  |  Df = {Df_z:.2f} m")
        doc_zap.add_paragraph(f"  q_neto = {q_net:.2f} kPa  |  Área requerida = {Area_req:.2f} m²")
        doc_zap.add_paragraph(f"  Dimensiones mínimas → B = {B_zap:.2f} m, L = {L_zap:.2f} m")
        doc_zap.add_paragraph(f"  Dimensiones adoptadas → B = {B_use:.2f} m, L = {L_use:.2f} m")
        doc_zap.add_paragraph(f"  qu_max = {qu_max:.2f} kPa  |  qu_min = {qu_min:.2f} kPa  |  qu_avg = {qu_avg:.2f} kPa")
        doc_zap.add_heading("4. ESPESOR Y PERALTE EFECTIVO", level=1)
        doc_zap.add_paragraph(f"  Espesor H = {H_zap:.0f} cm  |  Recubrimiento = {recub_z:.1f} cm")
        doc_zap.add_paragraph(f"  Peralte efectivo d = H - recub - db/10 = {d_z:.1f} cm")
        doc_zap.add_heading("5. REVISIÓN DE CORTANTE", level=1)
        doc_zap.add_paragraph(f"  CORTANTE UNIDIRECCIONAL (Viga):")
        doc_zap.add_paragraph(f"    φVc = {phi_Vc_1way:.1f} kN  {'≥' if ok_1way else '<'}  Vu = {Vu_1way:.1f} kN  → {'✅ OK' if ok_1way else '❌ Aumentar H'}")
        doc_zap.add_paragraph(f"  PUNZONAMIENTO (Bidireccional):")
        doc_zap.add_paragraph(f"    bo = {bo_perim:.3f} m  |  φVc = {phi_Vc_punz:.1f} kN  {'≥' if ok_punz else '<'}  Vup = {Vu_punz:.1f} kN  → {'✅ OK' if ok_punz else '❌ Aumentar H'}")
        doc_zap.add_heading("6. DISEÑO A FLEXIÓN — ACERO DE REFUERZO", level=1)
        doc_zap.add_paragraph(f"  DIR. B (malla sobre el ancho L={L_use:.2f}m):")
        doc_zap.add_paragraph(f"    Mu_B = {Mu_flex_B:.1f} kN·m  |  As_B = {As_req_B:.2f} cm²  |  ρ_B = {rho_use_B:.4f}")
        doc_zap.add_paragraph(f"    Arreglo: {n_barras_B} varillas {bar_z}  c/ {sep_B:.1f} cm  {'✅ OK' if disc_B>0 else '❌ Aumentar H'}")
        doc_zap.add_paragraph(f"  DIR. L (malla sobre el ancho B={B_use:.2f}m):")
        doc_zap.add_paragraph(f"    Mu_L = {Mu_flex_L:.1f} kN·m  |  As_L = {As_req_L:.2f} cm²  |  ρ_L = {rho_use_L:.4f}")
        doc_zap.add_paragraph(f"    Arreglo: {n_barras_L} varillas {bar_z}  c/ {sep_L:.1f} cm  {'✅ OK' if disc_L>0 else '❌ Aumentar H'}")
        doc_zap.add_heading("7. CANTIDADES DE MATERIALES (APU)", level=1)
        _area_m2_doc = REBAR_DICT[bar_z]["area"] * 1e-4
        _pe_B = n_barras_B * (L_use + 2*H_zap/100.0) * _area_m2_doc * 7850
        _pe_L = n_barras_L * (B_use + 2*H_zap/100.0) * _area_m2_doc * 7850
        _pe_tot = _pe_B + _pe_L
        _vol_exc = (B_use + 0.5) * (L_use + 0.5) * Df_z
        _vol_conc = B_use * L_use * (H_zap/100.0)
        doc_zap.add_paragraph(f"  Excavación = {_vol_exc:.2f} m³")
        doc_zap.add_paragraph(f"  Concreto   = {_vol_conc:.2f} m³")
        doc_zap.add_paragraph(f"  Acero Dir.B = {_pe_B:.1f} kg  |  Acero Dir.L = {_pe_L:.1f} kg  |  Total = {_pe_tot:.1f} kg")
        doc_zap.add_paragraph(f"  Cuantía = {(_pe_tot/_vol_conc) if _vol_conc>0 else 0:.1f} kg/m³")
        f_zap_io = io.BytesIO()
        doc_zap.save(f_zap_io)
        f_zap_io.seek(0)
        st.download_button("📥 Descargar Memoria Completa DOCX", data=f_zap_io,
                           file_name=f"Memoria_Zapata_{B_use:.1f}x{L_use:.1f}m.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    with tab_dwg:
        st.subheader("🧊 Visualización 3D de la Fundación con Acero de Refuerzo")
        fig3d = go.Figure()

        Hz_m  = H_zap / 100.0
        rec_m = recub_z / 100.0
        db_m  = db_bar_z / 1000.0
        z_bar = rec_m + db_m / 2           # altura del acero en la zapata

        # Zapata (cuerpo sólido)
        x_z = [-B_use/2, B_use/2, B_use/2, -B_use/2, -B_use/2, B_use/2, B_use/2, -B_use/2]
        y_z = [-L_use/2, -L_use/2, L_use/2, L_use/2, -L_use/2, -L_use/2, L_use/2, L_use/2]
        z_z = [0]*4 + [Hz_m]*4
        fig3d.add_trace(go.Mesh3d(x=x_z, y=y_z, z=z_z, alphahull=0, opacity=0.25,
                                  color='steelblue', name='Zapata', showlegend=True))

        # Columna
        c1_m = c1_col/100.0; c2_m = c2_col/100.0
        x_c = [-c1_m/2, c1_m/2, c1_m/2, -c1_m/2, -c1_m/2, c1_m/2, c1_m/2, -c1_m/2]
        y_c = [-c2_m/2, -c2_m/2, c2_m/2, c2_m/2, -c2_m/2, -c2_m/2, c2_m/2, c2_m/2]
        z_c = [Hz_m]*4 + [Hz_m + 1.0]*4
        fig3d.add_trace(go.Mesh3d(x=x_c, y=y_c, z=z_c, alphahull=0, opacity=0.5,
                                  color='slategray', name='Columna', showlegend=True))

        # Varillas Dir. B (corren en dirección X = dirección L_use)
        _xs_barB = np.linspace(-B_use/2 + rec_m, B_use/2 - rec_m, n_barras_B)
        _show_B = True
        for xi in _xs_barB:
            fig3d.add_trace(go.Scatter3d(
                x=[xi, xi], y=[-L_use/2 + rec_m, L_use/2 - rec_m], z=[z_bar, z_bar],
                mode='lines', line=dict(color='#ff6b35', width=5),
                name='Acero Dir.B' if _show_B else None, showlegend=_show_B, legendgroup='aB'))
            _show_B = False

        # Varillas Dir. L (corren en dirección Y = dirección B_use)
        _ys_barL = np.linspace(-L_use/2 + rec_m, L_use/2 - rec_m, n_barras_L)
        _z_barL  = z_bar + db_m               # ligeramente encima de la malla inferior
        _show_L = True
        for yi in _ys_barL:
            fig3d.add_trace(go.Scatter3d(
                x=[-B_use/2 + rec_m, B_use/2 - rec_m], y=[yi, yi], z=[_z_barL, _z_barL],
                mode='lines', line=dict(color='#ffd54f', width=5),
                name='Acero Dir.L' if _show_L else None, showlegend=_show_L, legendgroup='aL'))
            _show_L = False

        fig3d.update_layout(
            scene=dict(aspectmode='data', xaxis_title='B (m)', yaxis_title='L (m)', zaxis_title='Z (m)',
                       bgcolor='#0f1117',
                       xaxis=dict(showgrid=True, gridcolor='#333'),
                       yaxis=dict(showgrid=True, gridcolor='#333'),
                       zaxis=dict(showgrid=True, gridcolor='#333')),
            margin=dict(l=0, r=0, b=0, t=30), height=550,
            showlegend=True, dragmode='turntable', paper_bgcolor='#0f1117', font_color='white',
            title=dict(text=f"Zapata {B_use:.2f}x{L_use:.2f}m | H={H_zap:.0f}cm | "
                           f"Dir.B: {n_barras_B}×{bar_z} c/{sep_B:.1f}cm | Dir.L: {n_barras_L}×{bar_z} c/{sep_L:.1f}cm",
                       font_color='white'))
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
        
        st.markdown("#### 💾 Exportar AutoCAD (.dxf)")
        doc_dxf = ezdxf.new('R2010')
        doc_dxf.units = ezdxf.units.CM
        msp = doc_dxf.modelspace()

        # Capa setup
        for _lay, _col in [('CONCRETO',7),('ACERO',1),('TEXTO',3),('EJES',8)]:
            if _lay not in doc_dxf.layers:
                doc_dxf.layers.add(_lay, color=_col)

        # ── ELEVACIÓN (lado izquierdo del DXF) ──────────────────────────────
        ex = 0; ey = 0   # offset elevación
        # Contorno zapata
        msp.add_lwpolyline([(ex,ey),(ex+B_use*100,ey),(ex+B_use*100,ey+H_zap),(ex,ey+H_zap),(ex,ey)],
                           close=True, dxfattribs={'layer':'CONCRETO'})
        # Columna
        msp.add_lwpolyline([(ex+pos_x_col,ey+H_zap),(ex+pos_x_col,ey+H_zap+50),
                             (ex+pos_x_col+c1_col,ey+H_zap+50),(ex+pos_x_col+c1_col,ey+H_zap)],
                           close=True, dxfattribs={'layer':'CONCRETO'})
        # Varillas Dir. B en elevación (líneas horizontales)
        for i in range(n_barras_B):
            xi = ex + recub_z + i * sep_B
            msp.add_line((xi, ey+recub_z), (xi, ey+recub_z), dxfattribs={'layer':'ACERO'})
            msp.add_circle((xi, ey+recub_z), db_bar_z/10, dxfattribs={'layer':'ACERO'})
        # Línea de acero Dir. B
        msp.add_line((ex+recub_z, ey+recub_z), (ex+B_use*100-recub_z, ey+recub_z),
                     dxfattribs={'layer':'ACERO'})
        # Cota inferior
        msp.add_mtext(f"{n_barras_B}#{bar_z}@{sep_B:.0f}cm Dir.B",
                      dxfattribs={'layer':'TEXTO','char_height':4,'insert':(ex+B_use*50, ey-8)})

        # ── PLANTA (lado derecho, offset = B*100+30cm) ──────────────────────
        px = ex + B_use*100 + 30; py = ey
        # Contorno planta
        msp.add_lwpolyline([(px,py),(px+B_use*100,py),(px+B_use*100,py+L_use*100),(px,py+L_use*100),(px,py)],
                           close=True, dxfattribs={'layer':'CONCRETO'})
        # Columna en planta
        msp.add_lwpolyline([(px+pos_x_col,py+(L_use*100-c2_col)/2),
                             (px+pos_x_col+c1_col,py+(L_use*100-c2_col)/2),
                             (px+pos_x_col+c1_col,py+(L_use*100+c2_col)/2),
                             (px+pos_x_col,py+(L_use*100+c2_col)/2)],
                           close=True, dxfattribs={'layer':'CONCRETO'})
        # Varillas Dir. B en planta (líneas paralelas al eje Y)
        for i in range(n_barras_B):
            xi = px + recub_z + i * sep_B
            msp.add_line((xi, py+recub_z), (xi, py+L_use*100-recub_z), dxfattribs={'layer':'ACERO'})
        # Varillas Dir. L en planta (líneas paralelas al eje X)
        for j in range(n_barras_L):
            yj = py + recub_z + j * sep_L
            msp.add_line((px+recub_z, yj), (px+B_use*100-recub_z, yj), dxfattribs={'layer':'ACERO'})
        msp.add_mtext(f"{n_barras_L}#{bar_z}@{sep_L:.0f}cm Dir.L",
                      dxfattribs={'layer':'TEXTO','char_height':4,'insert':(px+B_use*50, py+L_use*100+8)})

        out_stream = io.BytesIO()
        doc_dxf.write(out_stream)
        st.download_button(label="📐 Descargar Plano DXF (Elev. + Planta con Acero)",
                           data=out_stream.getvalue(),
                           file_name=f"Zapata_{B_use:.1f}x{L_use:.1f}m_Armado.dxf",
                           mime="application/dxf")

    with tab_apu:
        vol_excavacion = (B_use + 0.5) * (L_use + 0.5) * Df_z  # Sobre-excav. 25cm por lado
        vol_concreto_zap = B_use * L_use * (H_zap/100.0)
        # Peso acero: Área (cm²) * Longitud (m) * factor 7850 kg/m³ * 1e-4 (cm²→m²) = kg
        # Fórmula correcta: kg = n_barras * longitud_m * area_m2 * 7850
        # area_m2 = area_cm2 * 1e-4
        _area_m2 = REBAR_DICT[bar_z]["area"] * 1e-4
        _long_B = L_use + 2*H_zap/100.0  # Long. con gancho en dirección B
        _long_L = B_use + 2*H_zap/100.0  # Long. con gancho en dirección L
        peso_barras_B_apu = n_barras_B * _long_B * _area_m2 * 7850
        peso_barras_L_apu = n_barras_L * _long_L * _area_m2 * 7850
        peso_total_acero_zap = peso_barras_B_apu + peso_barras_L_apu
        
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

