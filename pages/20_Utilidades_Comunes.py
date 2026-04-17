import streamlit as st

# ─── BANNER ESTANDAR DIAMANTE ───────────────────────────────
st.markdown("""<div style="width:100%;overflow:hidden;border-radius:14px;margin-bottom:18px;box-shadow:0 4px 32px #0008;"><svg viewBox="0 0 1100 220" xmlns="http://www.w3.org/2000/svg" style="width:100%;display:block;background:linear-gradient(135deg,#0a1128 0%,#1c2541 100%);"><g opacity="0.1" stroke="#38bdf8" stroke-width="0.5"><line x1="0" y1="55" x2="1100" y2="55"/><line x1="0" y1="110" x2="1100" y2="110"/><line x1="0" y1="165" x2="1100" y2="165"/><line x1="220" y1="0" x2="220" y2="220"/><line x1="440" y1="0" x2="440" y2="220"/><line x1="660" y1="0" x2="660" y2="220"/></g><rect x="0" y="0" width="1100" height="3" fill="#3b82f6" opacity="0.9"/><rect x="0" y="217" width="1100" height="3" fill="#3b82f6" opacity="0.7"/><g transform="translate(560,0)"><rect x="0" y="28" width="4" height="165" rx="2" fill="#3b82f6"/><text x="18" y="66" font-family="Arial,sans-serif" font-size="28" font-weight="bold" fill="#ffffff">UTILIDADES COMUNES</text><text x="18" y="94" font-family="Arial,sans-serif" font-size="14" font-weight="300" fill="#93c5fd" letter-spacing="2">CONVERSIONES · TABLAS NORMATIVAS · CALCULADORA</text><rect x="18" y="102" width="480" height="1" fill="#3b82f6" opacity="0.5"/><rect x="18" y="115" width="127" height="22" rx="11" fill="#0c1a2e" stroke="#3b82f6" stroke-width="1"/><text x="81" y="130" text-anchor="middle" font-family="Arial,sans-serif" font-size="9" font-weight="bold" fill="#93c5fd">CONVERSIONES SI</text><rect x="153" y="115" width="106" height="22" rx="11" fill="#052e16" stroke="#10b981" stroke-width="1"/><text x="206" y="130" text-anchor="middle" font-family="Arial,sans-serif" font-size="9" font-weight="bold" fill="#6ee7b7">TABLAS REBAR</text><rect x="267" y="115" width="92" height="22" rx="11" fill="#1e1b4b" stroke="#8b5cf6" stroke-width="1"/><text x="313" y="130" text-anchor="middle" font-family="Arial,sans-serif" font-size="9" font-weight="bold" fill="#c4b5fd">MATERIALES</text><rect x="367" y="115" width="99" height="22" rx="11" fill="#291400" stroke="#f59e0b" stroke-width="1"/><text x="416" y="130" text-anchor="middle" font-family="Arial,sans-serif" font-size="9" font-weight="bold" fill="#fcd34d">CALCULADORA</text><text x="18" y="156" font-family="Arial,sans-serif" font-size="11" fill="#94a3b8">Herramientas de soporte para el suite estructural: tablas de propiedades de acero</text><text x="18" y="172" font-family="Arial,sans-serif" font-size="11" fill="#94a3b8">de refuerzo (ASTM A615/A706), conversion de unidades SI-Imperial, propiedades</text><text x="18" y="188" font-family="Arial,sans-serif" font-size="11" fill="#94a3b8">de materiales por norma (concretos, aceros, maderas) y calculadora cientifica.</text></g></svg></div>""", unsafe_allow_html=True)

with st.expander(" Guia Profesional — Utilidades y Tablas de Referencia", expanded=False):
    st.markdown("""
    ### Herramientas de Soporte del Suite Estructural
    Modulo auxiliar que centraliza tablas de referencia, conversores de unidades y datos de materiales necesarios para el diseño en cualquiera de los modulos del suite.

    ####  1. Tablas de Varillas de Refuerzo
    - Propiedades completas de barras ASTM A615 Gr40/60/80 y A706: diametro nominal, area transversal y peso por metro lineal.
    - Tabla de doblado: radios minimos de doblez en ganchos estandar y de gancho sismico (NSR-10 C.7.2).

    ####  2. Conversion de Unidades SI / Imperial
    - Convertidor bidireccional para: fuerzas (kN, tonf, kip, lbf), longitudes (m, cm, ft, in), presiones (MPa, kPa, psi, kgf/cm2) y momentos.
    - Especialmente util para verificar datos de informes de laboratorio en unidades distintas a la norma activa.

    ####  3. Propiedades de Materiales
    - Tabla de f'c vs f'r (modulo de ruptura) segun norma seleccionada (NSR-10, ACI, E.060).
    - Modulo de elasticidad del concreto: Ec = 4700*sqrt(f'c) [MPa] y variaciones segun peso unitario.
    - Propiedades del acero estructural (A36, A572 Gr50, A588) para el modulo de Estructuras Metalicas.

    ####  4. Calculadora Cientifica y Formulario
    - Calculadora de propiedades de seccion: A, I, Z, S para secciones rectangulares, circulares, T, I y L.
    - Formulario interactivo de ecuaciones de diseño frecuentes (NSR-10, ACI, AISC).
""")

import pandas as pd
import requests
import math
import io
from datetime import datetime

# 
# IDIOMA GLOBAL
try:
    from normas_referencias import mostrar_referencias_norma
except ImportError:
    def mostrar_referencias_norma(*a, **kw): pass
norma_sel = st.session_state.get("norma_sel", "NSR-10 (Colombia)")
mostrar_referencias_norma(norma_sel, "utilidades")
lang = st.session_state.get("idioma", "Español")
def _t(es, en):
    return en if lang == "English" else es

st.set_page_config(page_title=_t("Utilidades Comunes", "Common Utilities"), layout="wide")
st.title(_t("Herramientas Comunes", "Common Tools"))
st.markdown(_t("Transformación de Unidades Estructurales, Conversión de Moneda y Utilidades Rápidas.", "Structural Unit Conversion, Currency Exchange, and Quick Utilities."))

# 
# FUNCIONES AUXILIARES
# 
def get_exchange_rate(base_currency, target_currency):
    """
    Obtiene tasa de cambio desde una API gratuita (exchangerate-api.com).
    Si falla, devuelve valores aproximados de respaldo.
    """
    try:
        # Usamos una API pública sin clave (limitada pero suficiente para demo)
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if response.status_code == 200 and target_currency in data['rates']:
            return data['rates'][target_currency]
    except:
        pass
    # Valores de respaldo (aproximados a enero 2026)
    backup_rates = {
        ("USD", "COP"): 4200.0,
        ("COP", "USD"): 1/4200.0,
        ("USD", "MXN"): 18.5,
        ("MXN", "USD"): 1/18.5,
        ("USD", "ARS"): 1250.0,
        ("ARS", "USD"): 1/1250.0,
        ("USD", "PEN"): 3.8,
        ("PEN", "USD"): 1/3.8,
        ("USD", "EUR"): 0.92,
        ("EUR", "USD"): 1.087,
        ("USD", "CLP"): 950.0,
        ("CLP", "USD"): 1/950.0,
        ("USD", "BOB"): 6.9,
        ("BOB", "USD"): 1/6.9,
        ("USD", "UYU"): 42.0,
        ("UYU", "USD"): 1/42.0,
    }
    return backup_rates.get((base_currency, target_currency), 1.0)

# 
# DICCIONARIO DE CONVERSIONES (UNIDADES)
# 
CONV_DICT = {
    _t("Longitud", "Length"): {
        "Base": "m",
        "m": 1.0,
        "cm": 0.01,
        "mm": 0.001,
        "km": 1000.0,
        "in (pulgada)": 0.0254,
        "ft (pie)": 0.3048,
        "yd (yarda)": 0.9144,
        "milla (mi)": 1609.34,
    },
    _t("Área", "Area"): {
        "Base": "m²",
        "m²": 1.0,
        "cm²": 0.0001,
        "mm²": 1e-6,
        "km²": 1e6,
        "in²": 0.00064516,
        "ft²": 0.092903,
        "yd²": 0.836127,
        "hectárea (ha)": 10000.0,
    },
    _t("Fuerza", "Force"): {
        "Base": "N",
        "N": 1.0,
        "kN": 1000.0,
        "MN": 1e6,
        "kgf": 9.80665,
        "tonf": 9806.65,
        "lbf": 4.44822,
        "kip (kips)": 4448.22,
    },
    _t("Esfuerzo / Presión", "Stress / Pressure"): {
        "Base": "Pa",
        "Pa": 1.0,
        "kPa": 1000.0,
        "MPa": 1e6,
        "GPa": 1e9,
        "kgf/cm²": 98066.5,
        "kgf/m²": 9.80665,
        "tonf/m²": 9806.65,
        "psi": 6894.76,
        "ksi": 6894760.0,
        "psf": 47.8803,
        "bar": 1e5,
        "atm": 101325.0,
    },
    _t("Momento / Torque", "Moment / Torque"): {
        "Base": "N·m",
        "N·m": 1.0,
        "kN·m": 1000.0,
        "kgf·m": 9.80665,
        "tonf·m": 9806.65,
        "lbf·ft": 1.355818,
        "lbf·in": 0.1129848,
        "kip·ft": 1355.818,
        "kip·in": 112.9848,
    },
    _t("Carga Distribuida Lineal", "Linear Load"): {
        "Base": "N/m",
        "N/m": 1.0,
        "kN/m": 1000.0,
        "kgf/m": 9.80665,
        "tonf/m": 9806.65,
        "lbf/ft (plf)": 14.5939,
        "kip/ft (klf)": 14593.9,
    },
    _t("Momento de Inercia", "Moment of Inertia"): {
        "Base": "cm⁴",
        "cm⁴": 1.0,
        "mm⁴": 0.0001,
        "m⁴": 1e8,
        "in⁴": 41.623,
    },
    _t("Módulo de Sección", "Section Modulus"): {
        "Base": "cm³",
        "cm³": 1.0,
        "mm³": 0.001,
        "m³": 1e6,
        "in³": 16.3871,
    },
    _t("Velocidad", "Velocity"): {
        "Base": "m/s",
        "m/s": 1.0,
        "km/h": 0.277778,
        "mph": 0.44704,
        "ft/s": 0.3048,
        "nudo": 0.514444,
    },
    _t("Masa", "Mass"): {
        "Base": "kg",
        "kg": 1.0,
        "g": 0.001,
        "tonelada (métrica)": 1000.0,
        "lb": 0.453592,
        "oz": 0.0283495,
        "slug": 14.5939,
    },
    _t("Densidad", "Density"): {
        "Base": "kg/m³",
        "kg/m³": 1.0,
        "g/cm³": 1000.0,
        "lb/ft³": 16.0185,
        "lb/in³": 27679.9,
    },
}

# 
# PESTAÑAS PRINCIPALES
# 
tab1, tab2, tab3 = st.tabs([
    _t(" 1. Conversor de Unidades", " 1. Unit Converter"),
    _t(" 2. Conversor de Moneda", " 2. Currency Converter"),
    _t(" 3. Utilidades Rápidas", " 3. Quick Utilities")
])

# =============================================================================
# TAB 1: CONVERSOR DE UNIDADES
# =============================================================================
with tab1:
    st.header(_t("Conversor de Unidades para Ingeniería Estructural", "Unit Converter for Structural Engineering"))
    
    col_cv1, col_cv2, col_cv3 = st.columns([1, 1, 1])
    
    with col_cv1:
        cat_opts = list(CONV_DICT.keys())
        categoria = st.selectbox(_t("Categoría de Magnitud", "Magnitude Category"), cat_opts,
                                 index=cat_opts.index(st.session_state.get("ut_cat", cat_opts[0])),
                                 key="ut_cat")
        unidades = [k for k in CONV_DICT[categoria].keys() if k != "Base"]
    
    with col_cv2:
        unit_in = st.selectbox(_t("Unidad de Origen (De)", "From Unit"), unidades,
                               index=unidades.index(st.session_state.get("ut_unit_in", unidades[0])) if st.session_state.get("ut_unit_in", unidades[0]) in unidades else 0,
                               key="ut_unit_in")
        val_in = st.number_input(_t("Valor a Convertir", "Value to Convert"), value=st.session_state.get("ut_val_in", 1.0), key="ut_val_in")
        
    with col_cv3:
        unit_out = st.selectbox(_t("Unidad de Destino (A)", "To Unit"), unidades,
                                 index=unidades.index(st.session_state.get("ut_unit_out", unidades[1] if len(unidades)>1 else unidades[0])) if st.session_state.get("ut_unit_out", unidades[1] if len(unidades)>1 else unidades[0]) in unidades else (1 if len(unidades)>1 else 0),
                                 key="ut_unit_out")
        # Conversión
        val_base = val_in * CONV_DICT[categoria][unit_in]
        val_out = val_base / CONV_DICT[categoria][unit_out]
        st.markdown(f"### **{_t('Resultado:', 'Result:')}**")
        st.markdown(f"### <span style='color:green'>{val_out:,.6g}</span> **{unit_out}**", unsafe_allow_html=True)

    # Tabla rápida de equivalencias
    st.markdown("---")
    st.write(_t("**Tabla Rápida de Equivalencias (1 unidad base):**", " **Quick Equivalency Table (1 base unit):**"))
    quick_dict = {}
    for target in unidades:
        v_base = 1.0 * CONV_DICT[categoria][unit_in]
        v_out = v_base / CONV_DICT[categoria][target]
        quick_dict[target] = v_out
    df_quick = pd.DataFrame([quick_dict], index=[f"1.0 {unit_in} {_t('equivale a:', 'equals:')}"])
    st.dataframe(df_quick.style.format("{:,.5g}"), use_container_width=True)
    
    # Botón exportar tabla a Excel
    if st.button(_t("Exportar tabla de conversión a Excel", "Export conversion table to Excel")):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Hoja de conversión actual
            df_quick.to_excel(writer, sheet_name=f"{categoria}_{unit_in}")
            # Hoja con todas las categorías y factores
            all_factors = []
            for cat, factors in CONV_DICT.items():
                base = factors["Base"]
                for unit, factor in factors.items():
                    if unit != "Base":
                        all_factors.append({"Categoría": cat, "Unidad": unit, "Factor a Base": factor, "Base": base})
            df_all = pd.DataFrame(all_factors)
            df_all.to_excel(writer, sheet_name="Todos los factores", index=False)
        output.seek(0)
        st.download_button(_t("Descargar Excel", "Download Excel"), data=output,
                           file_name=f"Conversiones_{categoria}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============================================================================
# TAB 2: CONVERSOR DE MONEDA
# =============================================================================
with tab2:
    st.header(_t("Conversor de Moneda con Tasas Actualizadas", "Currency Converter with Live Rates"))
    st.markdown(_t("Las tasas se actualizan automáticamente desde exchangerate-api.com (aproximadamente cada hora). En caso de falla, se usan valores de respaldo.", 
                   "Rates are automatically updated from exchangerate-api.com (approx. hourly). If the API fails, backup values are used."))
    
    # Lista de monedas comunes en Latinoamérica + principales
    monedas = [
        "USD (Dólar EE.UU.)", "COP (Peso Colombiano)", "MXN (Peso Mexicano)", 
        "ARS (Peso Argentino)", "PEN (Sol Peruano)", "CLP (Peso Chileno)", 
        "BOB (Boliviano)", "UYU (Peso Uruguayo)", "EUR (Euro)", "BRL (Real Brasileño)",
        "GBP (Libra Esterlina)", "CAD (Dólar Canadiense)"
    ]
    # Extraer códigos
    codes = [c.split()[0] for c in monedas]
    moneda_dict = dict(zip(monedas, codes))
    
    col_cur1, col_cur2, col_cur3 = st.columns([1, 1, 1])
    with col_cur1:
        moneda_base = st.selectbox(_t("Moneda de origen", "Base currency"), monedas,
                                   index=monedas.index(st.session_state.get("cur_base", monedas[0])),
                                   key="cur_base")
        base_code = moneda_dict[moneda_base]
    with col_cur2:
        moneda_target = st.selectbox(_t("Moneda de destino", "Target currency"), monedas,
                                     index=monedas.index(st.session_state.get("cur_target", monedas[1])),
                                     key="cur_target")
        target_code = moneda_dict[moneda_target]
        monto = st.number_input(_t("Cantidad a convertir", "Amount to convert"), value=st.session_state.get("cur_monto", 1.0), key="cur_monto")
    with col_cur3:
        # Obtener tasa
        if st.button(_t("Actualizar tasa", "Update rate"), key="update_rate"):
            st.session_state.cur_rate = get_exchange_rate(base_code, target_code)
            st.rerun()
        if "cur_rate" not in st.session_state:
            st.session_state.cur_rate = get_exchange_rate(base_code, target_code)
        tasa = st.session_state.cur_rate
        resultado = monto * tasa
        st.markdown(f"### **{_t('Resultado:', 'Result:')}**")
        st.markdown(f"### <span style='color:green'>{resultado:,.2f}</span> **{target_code}**", unsafe_allow_html=True)
        st.caption(f"Tasa: 1 {base_code} = {tasa:.6f} {target_code} ({_t('actualizada', 'updated')}: {datetime.now().strftime('%H:%M:%S')})")
    
    # Mostrar tasas cruzadas
    st.markdown("---")
    st.write(_t("**Tasas de cambio cruzadas (frente al USD):**", " **Cross exchange rates (vs USD):**"))
    # Obtener tasas para todas las monedas respecto al USD (o a la base)
    rates_usd = {}
    for cur in monedas:
        code = cur.split()[0]
        if code == "USD":
            rates_usd[cur] = 1.0
        else:
            try:
                rate = get_exchange_rate("USD", code)
                rates_usd[cur] = rate
            except:
                rates_usd[cur] = 0.0
    df_rates = pd.DataFrame(list(rates_usd.items()), columns=[_t("Moneda", "Currency"), _t("Tasa USD", "Rate USD")])
    df_rates = df_rates.sort_values(_t("Tasa USD", "Rate USD"), ascending=False)
    st.dataframe(df_rates.style.format({_t("Tasa USD", "Rate USD"): "{:.6f}"}), use_container_width=True, hide_index=True)
    
    # Exportar a Excel
    if st.button(_t("Exportar tasas de cambio a Excel", "Export exchange rates to Excel")):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_rates.to_excel(writer, sheet_name="Tasas USD", index=False)
            # También guardar la conversión actual
            df_conv = pd.DataFrame({
                "Moneda Origen": [base_code],
                "Moneda Destino": [target_code],
                "Monto Origen": [monto],
                "Monto Destino": [resultado],
                "Tasa": [tasa]
            })
            df_conv.to_excel(writer, sheet_name="Conversión", index=False)
        output.seek(0)
        st.download_button(_t("Descargar Excel", "Download Excel"), data=output,
                           file_name="Tasas_Cambio.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============================================================================
# TAB 3: UTILIDADES RÁPIDAS
# =============================================================================
with tab3:
    st.header(_t("Utilidades Rápidas", "Quick Utilities"))
    
    # Sub-pestañas dentro de utilidades
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        _t(" Áreas de Figuras Simples", " Areas of Simple Shapes"),
        _t(" Propiedades de Perfiles Comunes", " Common Profile Properties"),
        _t(" Cálculos Rápidos", " Quick Calculations")
    ])
    
    with sub_tab1:
        st.write(_t("Cálculo de área para figuras geométricas simples.", "Area calculation for simple geometric shapes."))
        shape_type = st.selectbox(_t("Forma", "Shape"), 
                                  [_t("Rectángulo", "Rectangle"), _t("Círculo", "Circle"), _t("Triángulo", "Triangle"), _t("Trapecio", "Trapezoid")],
                                  key="area_shape")
        if shape_type == _t("Rectángulo", "Rectangle"):
            a = st.number_input(_t("Base (b) [m]", "Width (b) [m]"), 0.0, 1000.0, 1.0, key="rect_b")
            b = st.number_input(_t("Altura (h) [m]", "Height (h) [m]"), 0.0, 1000.0, 1.0, key="rect_h")
            area = a * b
            st.success(f"**{_t('Área:', 'Area:')}** {area:.4f} m²")
        elif shape_type == _t("Círculo", "Circle"):
            r = st.number_input(_t("Radio (r) [m]", "Radius (r) [m]"), 0.0, 1000.0, 1.0, key="circ_r")
            area = math.pi * r**2
            st.success(f"**{_t('Área:', 'Area:')}** {area:.4f} m²")
        elif shape_type == _t("Triángulo", "Triangle"):
            b = st.number_input(_t("Base (b) [m]", "Base (b) [m]"), 0.0, 1000.0, 1.0, key="tri_b")
            h = st.number_input(_t("Altura (h) [m]", "Height (h) [m]"), 0.0, 1000.0, 1.0, key="tri_h")
            area = 0.5 * b * h
            st.success(f"**{_t('Área:', 'Area:')}** {area:.4f} m²")
        else:  # Trapecio
            b1 = st.number_input(_t("Base mayor (B) [m]", "Long base (B) [m]"), 0.0, 1000.0, 2.0, key="trap_B")
            b2 = st.number_input(_t("Base menor (b) [m]", "Short base (b) [m]"), 0.0, 1000.0, 1.0, key="trap_b")
            h = st.number_input(_t("Altura (h) [m]", "Height (h) [m]"), 0.0, 1000.0, 1.0, key="trap_h")
            area = (b1 + b2) / 2 * h
            st.success(f"**{_t('Área:', 'Area:')}** {area:.4f} m²")
    
    with sub_tab2:
        st.write(_t("Propiedades de perfiles metálicos comunes (IPN, IPE, etc.) - valores aproximados.", 
                    "Common steel profile properties (IPN, IPE, etc.) - approximate values."))
        perfil_tipo = st.selectbox(_t("Tipo de perfil", "Profile type"), 
                                   ["IPE", "HEA", "HEB", "C (Canal)", "L (Angular)"],
                                   key="perfil_tipo")
        altura = st.number_input(_t("Altura del perfil [mm]", "Profile height [mm]"), 80.0, 1000.0, 200.0, step=10.0, key="perfil_h")
        # Simulación rápida (valores aproximados para IPE)
        if perfil_tipo == "IPE":
            # Fórmulas aproximadas (solo para demostración)
            A = altura * 0.008  # m² aproximado
            Ix = altura**4 / 100000  # cm⁴ aproximado
            Wx = Ix / (altura/2) * 10  # cm³
            st.write(f"**Área aproximada:** {A*10000:.1f} cm²")
            st.write(f"**Momento de inercia Ix:** {Ix:.1f} cm⁴")
            st.write(f"**Módulo de sección Wx:** {Wx:.1f} cm³")
            st.caption(_t("Nota: Valores estimados. Para diseño, consulte tablas oficiales.", "Note: Estimated values. For design, refer to official tables."))
        else:
            st.info(_t("Para otros perfiles, consulte tablas de fabricantes.", "For other profiles, consult manufacturer tables."))
    
    with sub_tab3:
        st.write(_t("Cálculos rápidos de ingeniería.", "Quick engineering calculations."))
        # Tensión a partir de fuerza y área
        st.subheader(_t("Tensión Normal", "Normal Stress"))
        f = st.number_input(_t("Fuerza [kN]", "Force [kN]"), 0.0, 1e6, 100.0, key="calc_f")
        a = st.number_input(_t("Área [cm²]", "Area [cm²]"), 0.0, 1e6, 10.0, key="calc_a")
        if a > 0:
            sigma = f * 1000 / (a * 100)  # MPa
            st.success(f"σ = {sigma:.2f} MPa")
        
        # Deflexión simple
        st.subheader(_t("Deflexión de viga simplemente apoyada (carga puntual central)", "Simple beam deflection (center point load)"))
        P = st.number_input(_t("Carga P [kN]", "Load P [kN]"), 0.0, 1e6, 10.0, key="def_P")
        L = st.number_input(_t("Luz L [m]", "Span L [m]"), 0.0, 100.0, 4.0, key="def_L")
        E = st.number_input(_t("Módulo de elasticidad E [MPa]", "Modulus of elasticity E [MPa]"), 1e5, 2.5e5, 200000.0, key="def_E")
        I = st.number_input(_t("Momento de inercia I [cm⁴]", "Moment of inertia I [cm⁴]"), 0.0, 1e8, 1000.0, key="def_I")
        if I > 0:
            delta = (P * 1000 * (L*1000)**3) / (48 * E * I * 1e4)  # mm
            st.success(f"Δ = {delta:.2f} mm")