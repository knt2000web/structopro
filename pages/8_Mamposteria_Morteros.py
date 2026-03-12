import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import math
import io
import plotly.graph_objects as go
from docx import Document

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en):
    return en if lang == "English" else es
# ─────────────────────────────────────────────

st.set_page_config(page_title=_t("Mampostería y Morteros", "Masonry and Mortars"), layout="wide")

st.title(_t("Mampostería y Dosificación de Morteros", "Masonry and Mortar Dosing"))
st.markdown(_t("Herramienta integral para el cálculo de cantidades de materiales en tabiquería/mampostería (ladrillos y mortero) y la dosificación exacta de mezclas según el volumen requerido.", 
               "Comprehensive tool for calculating partition/masonry materials (bricks and mortar) and exact mortar mix dosing based on required volume."))

# ─────────────────────────────────────────────
# CONFIGURACIÓN GENERAL
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
    f'<span style="color:#7ec87e;font-weight:600;font-size:13px;">{_t("Normativa Activa:","Active Code:")} {norma_sel}</span>'
    f'</div>', unsafe_allow_html=True
)

# ─────────────────────────────────────────────
# BASE DE DATOS DE LADRILLOS (MULTINORMA)
# L (largo) x W (ancho/espesor) x H (alto) en centímetros
# ─────────────────────────────────────────────
BRICK_DB = {
    "NSR-10 (Colombia)": {
        "Ladrillo Común Macizo (25x12x6)": {"L":25.0, "W":12.0, "H":6.0},
        "Ladrillo Portante (29x12x9)":     {"L":29.0, "W":12.0, "H":9.0},
        "Bloque Arcilla N5 (30x12x20)":    {"L":30.0, "W":12.0, "H":20.0},
        "Bloque Cemento (40x20x20)":       {"L":40.0, "W":20.0, "H":20.0},
    },
    "ACI": {
        "Standard Brick (19.4x9.2x5.7)":   {"L":19.4, "W":9.2, "H":5.7},
        "Modular Brick (19.4x9.2x5.7)":    {"L":19.4, "W":9.2, "H":5.7},
        "Utility Brick (29.5x9.2x9.2)":    {"L":29.5, "W":9.2, "H":9.2},
    },
    "NEC-SE-HM (Ecuador)": {
        "Ladrillo Mambrón (25x12x7)":      {"L":25.0, "W":12.0, "H":7.0},
        "Bloque Hormigón (40x20x20)":      {"L":40.0, "W":20.0, "H":20.0},
    },
    "E.060 (Perú)": {
        "King Kong 18 Huecos (24x13x9)":   {"L":24.0, "W":13.0, "H":9.0},
        "Pandereta (23x11x9)":             {"L":23.0, "W":11.0, "H":9.0},
        "Macizo (24x11.5x5.5)":            {"L":24.0, "W":11.5, "H":5.5},
    },
    "NTC-EM (México)": {
        "Rojo Recocido (24x12x5)":         {"L":24.0, "W":12.0, "H":5.0},
        "Tabicón (28x14x7)":               {"L":28.0, "W":14.0, "H":7.0},
        "Block Hormigón (40x20x15)":       {"L":40.0, "W":15.0, "H":20.0},
    },
    "COVENIN 1753-2006 (Venezuela)": {
        "Bloque Arcilla (25x15x10)":       {"L":25.0, "W":15.0, "H":10.0},
        "Bloque Concreto (40x20x15)":      {"L":40.0, "W":15.0, "H":20.0},
    },
    "NB 1225001-2020 (Bolivia)": {
        "Ladrillo Gambote (25x12x6)":      {"L":25.0, "W":12.0, "H":6.0},
        "Ladrillo 6 Huecos (24x15x10)":    {"L":24.0, "W":15.0, "H":10.0},
    },
    "CIRSOC 201-2025 (Argentina)": {
        "Ladrillo Común (24x11.5x5.5)":    {"L":24.0, "W":11.5, "H":5.5},
        "Ladrillo Hueco 8 (33x8x18)":      {"L":33.0, "W":8.0, "H":18.0},
        "Ladrillo Hueco 12 (33x12x18)":    {"L":33.0, "W":12.0, "H":18.0},
        "Ladrillo Hueco 18 (33x18x18)":    {"L":33.0, "W":18.0, "H":18.0},
    }
}

# Determine default brick list for this country
current_dict = None
if "ACI" in norma_sel:
    current_dict = BRICK_DB["ACI"]
elif norma_sel in BRICK_DB:
    current_dict = BRICK_DB[norma_sel]
else:
    current_dict = BRICK_DB["NSR-10 (Colombia)"] # fallback
    
lista_ladrillos = list(current_dict.keys()) + [_t("Típico Personalizado...", "Custom Size...")]


# ─────────────────────────────────────────────
# T1: CÁLCULO DE TABIQUE Y MAMPOSTERÍA
# ─────────────────────────────────────────────
with st.expander(_t("🧱 1. Cantidades de Mampostería (Ladrillos y Juntas)", "🧱 1. Masonry Wall Quantities (Bricks and Joints)"), expanded=True):
    st.info(_t("📺 **Modo de uso:** Ingresa las dimensiones del muro a construir y el tipo de aparejo/ladrillo (filtrado automáticamente por la norma de tu país). El sistema calculará el número exacto de ladrillos por metro cuadrado, el total, y el volumen de mortero requerido para las juntas.", 
               "📺 **How to use:** Enter wall dimensions and brick type (filtered by active country code). The system will calculate bricks per square meter, total bricks, and joint mortar volume."))
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col1:
        st.write(_t("#### Geometría del Muro", "#### Wall Geometry"))
        L_muro = st.number_input(_t("Largo del Muro (L) [m]", "Wall Length (L) [m]"), 0.5, 100.0, 5.0, 0.5)
        H_muro = st.number_input(_t("Altura del Muro (H) [m]", "Wall Height (H) [m]"), 0.5, 10.0, 2.5, 0.1)
        area_muro = L_muro * H_muro
        st.markdown(f"**Área Bruta del Muro:** {area_muro:.2f} m²")
    
    with col2:
        st.write(_t("#### Dimensiones del Ladrillo", "#### Brick Dimensions"))
        ladrillo_sel = st.selectbox(_t("Tipo de Ladrillo (Norma Activa)", "Brick Type (Active Code)"), lista_ladrillos)
        
        if ladrillo_sel == _t("Típico Personalizado...", "Custom Size..."):
            dimL_base = 24.0
            dimW_base = 12.0
            dimH_base = 6.0
        else:
            dimL_base = current_dict[ladrillo_sel]["L"]
            dimW_base = current_dict[ladrillo_sel]["W"]
            dimH_base = current_dict[ladrillo_sel]["H"]
            
        c2_1, c2_2, c2_3 = st.columns(3)
        with c2_1:
            dimL = st.number_input("Largo [cm]", 5.0, 60.0, float(dimL_base), 1.0, disabled=(ladrillo_sel != _t("Típico Personalizado...", "Custom Size...")))
        with c2_2:
            dimW = st.number_input("Ancho [cm]", 5.0, 40.0, float(dimW_base), 1.0, disabled=(ladrillo_sel != _t("Típico Personalizado...", "Custom Size...")))
        with c2_3:
            dimH = st.number_input("Alto [cm]", 3.0, 40.0, float(dimH_base), 1.0, disabled=(ladrillo_sel != _t("Típico Personalizado...", "Custom Size...")))
        
        disposicion = st.radio(_t("Disposición del muro:", "Wall Disposition:"), 
                               ["Soga (Grosor = Ancho)", "Tizón (Grosor = Largo)", "Canto (Grosor = Alto)"] if lang=="Español" else ["Stretcher (Thick = Width)", "Header (Thick = Length)", "Shiner (Thick = Height)"], 
                               horizontal=True)
        # Adapt dimensions to perspective
        if lang == "Español":
            if "Soga" in disposicion:
                ladrillo_frente_L = dimL
                ladrillo_frente_H = dimH
                espesor_muro = dimW
            elif "Tizón" in disposicion:
                ladrillo_frente_L = dimW
                ladrillo_frente_H = dimH
                espesor_muro = dimL
            else:
                ladrillo_frente_L = dimL
                ladrillo_frente_H = dimW
                espesor_muro = dimH
        else:
            if "Stretcher" in disposicion:
                ladrillo_frente_L = dimL
                ladrillo_frente_H = dimH
                espesor_muro = dimW
            elif "Header" in disposicion:
                ladrillo_frente_L = dimW
                ladrillo_frente_H = dimH
                espesor_muro = dimL
            else:
                ladrillo_frente_L = dimL
                ladrillo_frente_H = dimW
                espesor_muro = dimH
    
    with col3:
        st.write(_t("#### Juntas y Desperdicios", "#### Joints & Waste"))
        junta_h = st.number_input(_t("Espesor junta Hz. [cm]", "Horizontal joint [cm]"), 0.5, 3.0, 1.5, 0.1)
        junta_v = st.number_input(_t("Espesor junta Vt. [cm]", "Vertical joint [cm]"), 0.5, 3.0, 1.5, 0.1)
        desp_lad = st.number_input(_t("Desperdicio Ladrillos [%]", "Brick waste [%]"), 0.0, 20.0, 5.0, 1.0)
        desp_mor = st.number_input(_t("Desperdicio Mortero [%]", "Mortar waste [%]"), 0.0, 25.0, 10.0, 1.0)
        
    # --- CALCULO MATEMATICO TABIQUE ---
    # Convert parameters to meters
    L_m = ladrillo_frente_L / 100.0
    H_m = ladrillo_frente_H / 100.0
    W_m = espesor_muro / 100.0
    Jh_m = junta_h / 100.0
    Jv_m = junta_v / 100.0
    
    # Bricks per m2: 1 / ((L + Jv) * (H + Jh))
    ladrillos_por_m2_neto = 1.0 / ((L_m + Jv_m) * (H_m + Jh_m))
    ladrillos_totales_netos = ladrillos_por_m2_neto * area_muro
    ladrillos_pedidos = math.ceil(ladrillos_totales_netos * (1.0 + desp_lad/100.0))
    
    # Volume of mortar per m2: Total volume of 1m2 of wall - volume occupied by bricks in 1m2
    vol_muro_1m2 = 1.0 * 1.0 * W_m
    vol_ladrillos_1m2 = ladrillos_por_m2_neto * (L_m * H_m * W_m)
    vol_mortero_1m2_neto = vol_muro_1m2 - vol_ladrillos_1m2
    vol_mortero_total_neto = vol_mortero_1m2_neto * area_muro
    vol_mortero_pedido = vol_mortero_total_neto * (1.0 + desp_mor/100.0)
    
    st.markdown("---")
    res_1, res_2, res_3 = st.columns(3)
    res_1.metric(label=_t("Ladrillos por m² (S/Desp.)", "Bricks per m² (w/o waste)"), value=f"{ladrillos_por_m2_neto:.1f} uds")
    res_2.metric(label=_t("Ladrillos Totales (Con Desp.)", "Total Bricks (incl. waste)"), value=f"{ladrillos_pedidos} uds")
    res_3.metric(label=_t("Vol. Mortero p/ Muro (Con Desp.)", "Mortar Vol. (incl. waste)"), value=f"{vol_mortero_pedido:.3f} m³")

# ─────────────────────────────────────────────
# T2: DOSIFICACIÓN DE MORTEROS
# ─────────────────────────────────────────────
with st.expander(_t("💧 2. Dosificación y Diseño de Morteros (Cemento, Arena, Agua)", "💧 2. Mortar Dosing (Cement, Sand, Water)"), expanded=True):
    st.info(_t("📺 **Modo de uso:** Ingresa la proporción volumétrica deseada del mortero (ej. 1:3 para pegue muy resistente, o 1:4 para pegue estándar) y el volumen a producir. El sistema usa equivalencias teóricas empíricas para entregar bultos de cemento, m³ de arena y litros de agua.", 
               "📺 **How to use:** Enter mortar volumetric ratio (e.g. 1:3 for high strength, 1:4 for standard masonry) and volume. Returns bags of cement, sand volume, and water in liters."))
    
    # Valores empiricos para Produccion de 1 m3 de mortero
    # Ratio => [Cemento(kg), Arena(m3), Agua(L)]
    DOSIFICACIONES = {
        "1:1 (Revoques impermeables / muy ricos)": [908, 0.71, 250],
        "1:2 (Pañetes muros gruesos)": [610, 0.95, 250],
        "1:3 (Mampostería estructural / Pegue fuerte)": [454, 1.05, 250],
        "1:4 (Mampostería no estructural / Pañetes)": [364, 1.10, 250],
        "1:5 (Pegue baja resistencia / Plantillas)": [302, 1.13, 247],
        "1:6 (Morteros pobres)": [260, 1.16, 245],
        "1:8 (Rellenos)": [200, 1.18, 245]
    }
    
    DOSIFICACIONES_EN = {
        "1:1 (Waterproof renders)": [908, 0.71, 250],
        "1:2 (Thick plasters)": [610, 0.95, 250],
        "1:3 (Structural masonry / Strong joint)": [454, 1.05, 250],
        "1:4 (Non-structural masonry / Plasters)": [364, 1.10, 250],
        "1:5 (Low strength joints / Leveling)": [302, 1.13, 247],
        "1:6 (Poor mortars)": [260, 1.16, 245],
        "1:8 (Fillings)": [200, 1.18, 245]
    }
    
    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        mezcla_sel = st.selectbox(_t("Proporción Cemento:Arena", "Cement:Sand Ratio"), 
                                  list(DOSIFICACIONES_EN.keys()) if lang=="English" else list(DOSIFICACIONES.keys()), index=3)
        if lang=="English":
            val_mezcla = DOSIFICACIONES_EN[mezcla_sel]
        else:
            val_mezcla = DOSIFICACIONES[mezcla_sel]
            
    with dc2:
        vol_producir = st.number_input(_t("Volumen de Mortero a Fabricar [m³]", "Mortar Volume to Produce [m³]"), 
                                       0.0, 1000.0, float(vol_mortero_pedido), 0.1) # Autolinks directly to Tabique!
    with dc3:
        bulto_kg = st.selectbox(_t("Peso Bulto Cemento", "Cement Bag Weight"), ["50 kg", "42.5 kg"], index=0)
        val_bulto_kg = 50.0 if bulto_kg == "50 kg" else 42.5
        
    cemento_kg_total = vol_producir * val_mezcla[0]
    bultos_cemento = math.ceil(cemento_kg_total / val_bulto_kg)
    arena_m3_total = vol_producir * val_mezcla[1]
    agua_litros_total = vol_producir * val_mezcla[2]
    
    df_mort = pd.DataFrame([
        {_t("Material", "Material"): _t("Cemento", "Cement"), _t("Cantidad", "Quantity"): f"{bultos_cemento} {_t('Bultos', 'Bags')} ({cemento_kg_total:.1f} kg)"},
        {_t("Material", "Material"): _t("Arena de Peña/Sitio", "Sand"), _t("Cantidad", "Quantity"): f"{arena_m3_total:.2f} m³"},
        {_t("Material", "Material"): _t("Agua", "Water"), _t("Cantidad", "Quantity"): f"{agua_litros_total:.1f} {_t('Litros', 'Liters')}"},
    ])
    st.table(df_mort)

# ─────────────────────────────────────────────
# T3: PESO DE MUROS DE MAMPOSTERÍA
# ─────────────────────────────────────────────
with st.expander(_t("⚖️ 3. Peso Superficial de Muros de Mampostería", "⚖️ 3. Surface Weight of Masonry Walls"), expanded=False):
    st.info(_t("📺 **Modo de uso:** Calcula el peso real de 1 m² de muro (kg/m²) tomando en cuenta la densidad del material, el porcentaje de vacíos o huecos de la pieza, y el peso de las juntas de mortero.", 
               "📺 **How to use:** Calculates the actual weight of 1 m² of wall (kg/m²) accounting for material density, void percentage of the brick, and mortar joints weight."))
    
    col_w1, col_w2, col_w3 = st.columns(3)
    
    with col_w1:
        densidad_pieza = st.selectbox(_t("Material de la Pieza (Densidad)", "Block Material (Density)"), [
            "Arcilla Cocida (1800 kg/m³)",
            "Concreto de Peso Normal (2200 kg/m³)",
            "Concreto Liviano (1500 kg/m³)",
            "Sílico-Calcáreo (1900 kg/m³)"
        ])
        str_dens = dict(zip([_t("Arcilla Cocida", "Fired Clay"), _t("Concreto Normal", "Normal Weight Concrete"), _t("Concreto Liviano", "Lightweight Concrete"), _t("Sílico-calcáreo", "Calcium-Silicate")], [1800.0, 2200.0, 1500.0, 1900.0]))
        # Extract density implicitly
        d_p_v = 1800.0
        if "Arcilla" in densidad_pieza: d_p_v = 1800.0
        elif "Normal" in densidad_pieza: d_p_v = 2200.0
        elif "Liviano" in densidad_pieza: d_p_v = 1500.0
        elif "Sílico" in densidad_pieza: d_p_v = 1900.0
        
        huecos_pct = st.number_input(_t("Porcentaje de Huecos de la Pieza [%]", "Percentage of voids in piece [%]"), 0.0, 70.0, 30.0, 5.0)
        
    with col_w2:
        densidad_mortero = st.number_input(_t("Densidad del Mortero [kg/m³]", "Mortar Density [kg/m³]"), 1000.0, 3000.0, 2000.0, 50.0)
        st.write(f"**Volumen Neto Ladrillo/m2:** {(vol_ladrillos_1m2 * (1 - huecos_pct/100.0)):.4f} m³/m²")
        st.write(f"**Volumen Mortero/m2:** {vol_mortero_1m2_neto:.4f} m³/m²")
        
    with col_w3:
        peso_ladrillo_m2 = (vol_ladrillos_1m2 * (1 - huecos_pct/100.0)) * d_p_v
        peso_mortero_m2 = vol_mortero_1m2_neto * densidad_mortero
        peso_total_m2 = peso_ladrillo_m2 + peso_mortero_m2
        peso_total_kn = peso_total_m2 * 9.81 / 1000.0
        
        st.markdown(f"### **Peso del Muro:** <span style='color:blue'>{peso_total_m2:.1f} kg/m²</span>", unsafe_allow_html=True)
        st.markdown(f"### **Equivalencia:** <span style='color:green'>{peso_total_kn:.2f} kN/m²</span>", unsafe_allow_html=True)
        st.write(_t("*Usualmente empleado como Carga Muerta (D) en análisis estructural.*", "*Commonly used as Dead Load (D) in structural analysis.*"))

# ─────────────────────────────────────────────
# T4: APU Y EXPORTACIÓN
# ─────────────────────────────────────────────
st.markdown("---")
tab_diag, tab_3d, tab_apu = st.tabs(["📐 " + _t("Diagrama Ladrillo 2D", "2D Brick Diagram"), "🧊 " + _t("Muro 3D", "3D Wall"), "💰 " + _t("Presupuesto APU", "APU Budget")])

with tab_diag:
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.set_facecolor('#1a1a2e'); fig.patch.set_facecolor('#1a1a2e')
    
    # Dibujar bloque
    ax.add_patch(patches.Rectangle((0,0), dimL, dimH, linewidth=2, edgecolor='black', facecolor='#e2725b'))
    
    # Dibujar dimensiones (acotar)
    ax.annotate(f'L = {dimL} cm', xy=(dimL/2, -1.5), color='white', ha='center', fontsize=10)
    ax.annotate(f'H = {dimH} cm', xy=(-1.5, dimH/2), color='white', va='center', rotation=90, fontsize=10)
    ax.annotate(f'W = {dimW} cm (Profundidad)', xy=(dimL/2, dimH/2), color='white', ha='center', fontsize=9)
    
    ax.set_xlim(-5, dimL + 5)
    ax.set_ylim(-5, dimH + 5)
    ax.axis('off')
    st.pyplot(fig)

with tab_3d:
    st.write(_t("Visualización volumétrica del muro proyectado.", "Volumetric visualization of the projected wall."))
    fig3d = go.Figure()
    
    # 3D Wall Box
    X_m = L_muro
    Z_m = H_muro
    Y_m = espesor_muro / 100.0 # Grosor
    
    x_w = [0, X_m, X_m, 0, 0, X_m, X_m, 0]
    y_w = [0, 0, Y_m, Y_m, 0, 0, Y_m, Y_m]
    z_w = [0, 0, 0, 0, Z_m, Z_m, Z_m, Z_m]
    
    fig3d.add_trace(go.Mesh3d(x=x_w, y=y_w, z=z_w, alphahull=0, opacity=0.8, color='#e2725b', name=_t('Muro', 'Wall')))
    
    # Bounding lines
    lines_x = [0, X_m, X_m, 0, 0, 0, X_m, X_m, X_m, X_m, 0, 0, 0, X_m, 0, X_m]
    lines_y = [0, 0, Y_m, Y_m, 0, 0, 0, Y_m, Y_m, 0, 0, Y_m, Y_m, Y_m, Y_m, Y_m]  # This is a bit lazy, wireframe is better drawn explicitly but this gives some edges
    
    fig3d.update_layout(scene=dict(aspectmode='data', xaxis_title='L (m)', yaxis_title='Espesor (m)', zaxis_title='H (m)'),
                        margin=dict(l=0, r=0, b=0, t=0), height=450, showlegend=False, dragmode='turntable')
    st.plotly_chart(fig3d, use_container_width=True)

with tab_apu:
    st.write(_t("Basado en el cálculo de Muro de Mampostería y la mezcla de Mortero seleccionada.", 
                "Based on the Masonry Wall calculation and selected Mortar mixture."))
    if "apu_config" in st.session_state:
        apu = st.session_state.apu_config
        mon = apu["moneda"]
        
        # Asumiremos el costo de 1 unidad de ladrillo (hardcoded approx, luego el usuario debera ajustar)
        precio_l_unit = 1200.0 # COP default
        if mon != "COP$": precio_l_unit = 0.50 # 50 cents default for generic currency
            
        costo_ladrillos = ladrillos_pedidos * precio_l_unit
        costo_cem = bultos_cemento * apu["cemento"]
        costo_are = arena_m3_total * apu["arena"]
        
        st.info(_t(f"💡 El precio unitario del ladrillo usado para efecto analítico en APU es {mon} {precio_l_unit}. Puedes exportar a Excel para afinar.", 
                   f"💡 The unit price of a brick used for analytical APU is {mon} {precio_l_unit}. You can export to Excel to refine."))
        
        total_mat = costo_ladrillos + costo_cem + costo_are
        
        # MO: supongamos un rendimiento de instalacion de 12 m2 de muro al dia por oficial+ayudante
        dias_cuadrilla = area_muro / 12.0
        costo_mo = dias_cuadrilla * apu.get("costo_dia_mo", 69333.33) * 2 # Oficial + ayudante
        
        costo_directo = total_mat + costo_mo
        herramienta = costo_mo * apu.get("pct_herramienta", 0.05)
        aiu = costo_directo * apu.get("pct_aui", 0.30)
        utilidad = costo_directo * apu.get("pct_util", 0.05)
        iva = utilidad * apu.get("iva", 0.19)
        
        total_proyecto = costo_directo + herramienta + aiu + iva
        
        data_apu = {
            _t("Item", "Item"): [_t("Ladrillos (uds)", "Bricks (units)"), _t("Cemento (bultos)", "Cement (bags)"), _t("Arena (m³)", "Sand (m³)")],
            _t("Cantidad", "Quantity"): [f"{ladrillos_pedidos}", f"{bultos_cemento}", f"{arena_m3_total:.2f}"],
            f"Subtotal [{mon}]": [f"{costo_ladrillos:,.2f}", f"{costo_cem:,.2f}", f"{costo_are:,.2f}"]
        }
        st.dataframe(pd.DataFrame(data_apu), use_container_width=True, hide_index=True)
        st.markdown(f"### {_t('Presupuesto Total (Inlc. MO y AIU)', 'Total Budget (Incl. LB and AIU)')}: **{mon} {total_proyecto:,.2f}**")
        
        # Excel generator
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df_export = pd.DataFrame({
                "Item": ["Ladrillos", "Cemento", "Arena", "Mano de Obra Cuadrilla/Dias"],
                "Cantidad": [ladrillos_pedidos, bultos_cemento, arena_m3_total, dias_cuadrilla],
                "Unidad/Costo": [precio_l_unit, apu['cemento'], apu['arena'], apu.get("costo_dia_mo", 69333.33)*2]
            })
            df_export["Subtotal"] = df_export["Cantidad"] * df_export["Unidad/Costo"]
            df_export.to_excel(writer, index=False, sheet_name='APU Muro')
            
        output_excel.seek(0)
        st.download_button(label=_t("📥 Descargar Presupuesto Excel", "📥 Download Excel Budget"), data=output_excel, 
                           file_name=f"APU_Muro_{L_muro}x{H_muro}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.warning(_t("🔌 Carga los costos base en la página 'APU Mercado' primero.", "🔌 Load base costs in the 'APU Mercado' page first."))
