import streamlit as st
import pandas as pd

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es

st.set_page_config(page_title=_t("Herramientas Comunes", "Common Tools"), layout="wide")
st.title(_t("🧰 Herramientas Comunes", "🧰 Common Tools"))
st.markdown(_t("Transformación de Unidades Estructurales y Utilidades Rápidas.", "Structural Unit Conversion and Quick Utilities."))

tab_conv = st.tabs([_t("🔄 1. Transformación de Unidades", "🔄 1. Unit Conversion")])[0]

# Factores de conversion a la unidad base (Base Unit)
CONV_DICT = {
    _t("Fuerza", "Force"): {
        "Base": "N (Newtons)",
        "N (Newtons)": 1.0,
        "kN": 1000.0,
        "MN (MegaNewtons)": 1000000.0,
        "kgf": 9.80665,
        "Tonf": 9806.65,
        "lbf": 4.44822,
        "kip (kips)": 4448.22
    },
    _t("Esfuerzo / Presión", "Stress / Pressure"): {
        "Base": "Pa",
        "Pa": 1.0,
        "kPa": 1000.0,
        "MPa": 1000000.0,
        "GPa": 1000000000.0,
        "kgf/cm²": 98066.5,
        "kgf/m²": 9.80665,
        "Tonf/m²": 9806.65,
        "psi (lbf/in²)": 6894.76,
        "ksi (kip/in²)": 6894760.0,
        "psf (lbf/ft²)": 47.8803
    },
    _t("Longitud", "Length"): {
        "Base": "m",
        "m": 1.0,
        "cm": 0.01,
        "mm": 0.001,
        "in (pulgada)": 0.0254,
        "ft (pie)": 0.3048,
        "yd (yarda)": 0.9144
    },
    _t("Momento / Torque", "Moment / Torque"): {
        "Base": "N-m",
        "N-m": 1.0,
        "kN-m": 1000.0,
        "kgf-m": 9.80665,
        "Tonf-m": 9806.65,
        "lbf-ft": 1.355818,
        "lbf-in": 0.1129848,
        "kip-ft": 1355.818,
        "kip-in": 112.9848
    },
    _t("Carga Distribuida Lineal", "Line Load"): {
        "Base": "N/m",
        "N/m": 1.0,
        "kN/m": 1000.0,
        "kgf/m": 9.80665,
        "Tonf/m": 9806.65,
        "lbf/ft (plf)": 14.5939,
        "kip/ft (klf)": 14593.9
    }
}

with tab_conv:
    st.header(_t("Conversor de Unidades para Ingeniería Estructural", "Unit Converter for Structural Engineering"))
    
    col_cv1, col_cv2, col_cv3 = st.columns([1,1,1])
    
    with col_cv1:
        categoria = st.selectbox(_t("Categoría de Magnitud", "Magnitude Category"), list(CONV_DICT.keys()))
        
        # Get units for this category (excluding the "Base" key)
        unidades = [k for k in CONV_DICT[categoria].keys() if k != "Base"]
        
    with col_cv2:
        unit_in = st.selectbox(_t("Unidad de Origen (De)", "From Unit"), unidades)
        val_in = st.number_input(_t("Valor a Convertir", "Value to Convert"), value=1.0)
        
    with col_cv3:
        unit_out = st.selectbox(_t("Unidad de Destino (A)", "To Unit"), unidades, index=1 if len(unidades)>1 else 0)
        
        # Convert to Base first
        val_base = val_in * CONV_DICT[categoria][unit_in]
        # Convert from Base to Target
        val_out = val_base / CONV_DICT[categoria][unit_out]
        
        st.markdown(f"### **Resultado:**")
        st.markdown(f"### <span style='color:green'>{val_out:,.6g}</span> **{unit_out}**", unsafe_allow_html=True)

    st.markdown("---")
    st.write(_t("💡 **Tabla Rápida de Equivalencias:**", "💡 **Quick Equivalency Table:**"))
    
    # Generar tabla rápida basada en la unidad origen
    quick_dict = {}
    for target in unidades:
        v_base = 1.0 * CONV_DICT[categoria][unit_in]
        v_out = v_base / CONV_DICT[categoria][target]
        quick_dict[target] = v_out
        
    df_quick = pd.DataFrame([quick_dict], index=[f"1.0 {unit_in} equivale a:"])
    st.dataframe(df_quick.style.format("{:,.5g}"))
