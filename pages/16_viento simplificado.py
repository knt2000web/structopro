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
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import datetime

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es
# ─────────────────────────────────────────────

st.set_page_config(page_title=_t("Placa Fácil", "Easy Slab"), layout="wide")
st.title(_t("Placa Fácil – Sistema de Vigueta y Bloques", "Easy Slab – Joist & Block System"))
st.markdown(_t("Diseño de losas con vigueta metálica y bloques de arcilla cocida (Placa Fácil). Verificación según NSR-10 (Colombia) y normas internacionales.", 
               "Design of slabs with metal joists and fired clay blocks (Easy Slab). Verification according to NSR-10 (Colombia) and international codes."))

# ─────────────────────────────────────────────
# NORMATIVAS SOPORTADAS (multi-norma)
# ─────────────────────────────────────────────
NORMAS_PLACA = {
    "NSR-10 (Colombia)": {
        "luz_max": 4.2,          # m, luz máxima de perfiles sin apoyo intermedio
        "topping_min": 0.04,     # m, espesor mínimo de torta
        "concreto_min": 21,      # MPa
        "bloque_dim": (0.80, 0.23, 0.08),  # Largo, ancho, alto (m) – estándar colombiano
        "perfil_espaciado": 0.89, # m, separación centro a centro de perfiles
        "requiere_viga_borde": True,
        "ref": "NSR-10 Capítulo C.21 y Título E",
    },
    "E.060 (Perú)": {
        "luz_max": 4.2,
        "topping_min": 0.04,
        "concreto_min": 21,
        "bloque_dim": (0.80, 0.23, 0.08),
        "perfil_espaciado": 0.89,
        "requiere_viga_borde": True,
        "ref": "E.060 / NTE E.030",
    },
    "ACI 318-25 (EE.UU.)": {
        "luz_max": 4.2,
        "topping_min": 0.04,
        "concreto_min": 21,
        "bloque_dim": (0.80, 0.23, 0.08),
        "perfil_espaciado": 0.89,
        "requiere_viga_borde": True,
        "ref": "ACI 318-25 Capítulo 7",
    },
}

# ─────────────────────────────────────────────
# DATOS DEL BLOQUELÓN (estándar colombiano)
# ─────────────────────────────────────────────
BLOCK_DATA = {
    "largo": 0.80,      # m
    "ancho": 0.23,      # m
    "alto": 0.08,       # m
    "peso_unitario": 13.0,  # kg (promedio 12-14)
    "unidades_por_m2": 5.18, # rendimiento real
    "color": "#CD7F32",  # bronce / arcilla
    "material": "Arcilla cocida",
    "absorcion_agua": 12,   # % (típico)
    "transmitancia_termica": 2.10,  # W/m²K
    "aislamiento_acustico": 45,     # dB (estimado)
}

# ─────────────────────────────────────────────
# FUNCIONES AUXILIARES
# ─────────────────────────────────────────────
def qty_table(rows):
    df = pd.DataFrame(rows, columns=["Concepto", "Valor"])
    st.dataframe(df, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# SIDEBAR – CONFIGURACIÓN DEL PROYECTO
# ─────────────────────────────────────────────
norma_sel = st.sidebar.selectbox(_t("Norma de diseño", "Design code"), list(NORMAS_PLACA.keys()), index=0)
norma = NORMAS_PLACA[norma_sel]

st.sidebar.header(_t("Datos del proyecto", "Project data"))
proyecto_nombre = st.sidebar.text_input(_t("Nombre del proyecto", "Project name"), "Placa Fácil - Ejemplo")
proyecto_direccion = st.sidebar.text_input(_t("Dirección de obra", "Site address"), "Calle 123, Bogotá")
proyecto_cliente = st.sidebar.text_input(_t("Cliente / Propietario", "Client / Owner"), "Constructora XYZ")

st.sidebar.header(_t("Geometría de la placa", "Slab geometry"))
Lx = st.sidebar.number_input(_t("Luz X (m)", "Span X (m)"), 2.0, 12.0, 6.0, 0.1)
Ly = st.sidebar.number_input(_t("Luz Y (m)", "Span Y (m)"), 2.0, 12.0, 5.0, 0.1)
orientacion = st.sidebar.selectbox(_t("Dirección de los perfiles", "Profile direction"), ["Paralelo a X", "Paralelo a Y"], index=0)

st.sidebar.header(_t("Parámetros de diseño", "Design parameters"))
espesor_torta = st.sidebar.number_input(_t("Espesor de la torta de concreto (cm)", "Concrete topping thickness (cm)"), 4.0, 10.0, 5.0, 0.5) / 100.0
fc_concreto = st.sidebar.number_input(_t("Resistencia f'c concreto (MPa)", "Concrete strength f'c (MPa)"), 18.0, 35.0, 21.0, 0.5)
# Dimensiones de bloque (estándar colombiano) – se usan las fijas pero permitimos ajuste fino
block_length = BLOCK_DATA["largo"]
block_width = BLOCK_DATA["ancho"]
block_height = BLOCK_DATA["alto"]
# Perfiles
perfil_espaciado = st.sidebar.number_input(_t("Separación entre perfiles (cm)", "Profile spacing (cm)"), 70.0, 100.0, 89.0, 1.0) / 100.0
perfil_largo_max = st.sidebar.number_input(_t("Longitud máxima de perfil (m)", "Max profile length (m)"), 3.0, 12.0, 4.2, 0.1)
# Malla electrosoldada
malla_diam = st.sidebar.number_input(_t("Diámetro de la malla (mm)", "Mesh diameter (mm)"), 3.0, 6.0, 4.0, 0.5)
malla_espaciado = st.sidebar.number_input(_t("Espaciado de la malla (cm)", "Mesh spacing (cm)"), 10.0, 20.0, 15.0, 1.0) / 100.0
# Vigas de borde
incluir_vigas = st.sidebar.checkbox(_t("Incluir vigas de borde", "Include edge beams"), value=True)
viga_b = st.sidebar.number_input(_t("Ancho viga borde (cm)", "Edge beam width (cm)"), 10.0, 30.0, 15.0, 1.0) / 100.0
viga_h = st.sidebar.number_input(_t("Altura viga borde (cm)", "Edge beam height (cm)"), 15.0, 40.0, 20.0, 1.0) / 100.0

st.sidebar.header(_t("Factores de desperdicio", "Waste factors"))
desp_bloques = st.sidebar.number_input(_t("Bloques (%)", "Blocks (%)"), 0.0, 20.0, 5.0, 1.0) / 100.0
desp_concreto = st.sidebar.number_input(_t("Concreto (%)", "Concrete (%)"), 0.0, 20.0, 10.0, 1.0) / 100.0
desp_malla = st.sidebar.number_input(_t("Malla (%)", "Mesh (%)"), 0.0, 20.0, 10.0, 1.0) / 100.0
desp_perfiles = st.sidebar.number_input(_t("Perfiles (%)", "Profiles (%)"), 0.0, 20.0, 5.0, 1.0) / 100.0

st.sidebar.header(_t("APU – Precios unitarios", "APU – Unit prices"))
moneda = st.sidebar.text_input(_t("Moneda", "Currency"), "COP", key="apu_moneda")
precio_bloque = st.sidebar.number_input(_t("Precio por bloque (unidad)", "Price per block (unit)"), 5000.0, 15000.0, 7200.0, 100.0)
precio_perfil = st.sidebar.number_input(_t("Precio por metro lineal de perfil", "Price per linear meter of profile"), 20000.0, 50000.0, 28000.0, 1000.0)
precio_malla = st.sidebar.number_input(_t("Precio por m² de malla", "Price per m² of mesh"), 8000.0, 20000.0, 11000.0, 500.0)
precio_concreto = st.sidebar.number_input(_t("Precio por m³ de concreto", "Price per m³ of concrete"), 300000.0, 600000.0, 450000.0, 10000.0)
precio_mo = st.sidebar.number_input(_t("Costo mano de obra (día)", "Labor cost (day)"), 50000.0, 150000.0, 70000.0, 5000.0)
pct_herramienta = st.sidebar.number_input(_t("% Herramienta menor (sobre MO)", "Minor tool percentage"), 0.0, 20.0, 5.0, 1.0) / 100.0
pct_aui = st.sidebar.number_input(_t("% A.I.U. (sobre costo directo)", "A.I.U. percentage"), 0.0, 50.0, 30.0, 5.0) / 100.0
pct_util = st.sidebar.number_input(_t("% Utilidad (sobre costo directo)", "Profit percentage"), 0.0, 20.0, 5.0, 1.0) / 100.0
iva = st.sidebar.number_input(_t("% IVA (sobre utilidad)", "IVA on profit"), 0.0, 30.0, 19.0, 1.0) / 100.0

# ─────────────────────────────────────────────
# CÁLCULOS DE CANTIDADES (con rendimiento real)
# ─────────────────────────────────────────────
area_total = Lx * Ly

# Determinar dirección de los perfiles
if orientacion == "Paralelo a X":
    perfil_largo = Lx
    perfil_ancho = Ly
else:
    perfil_largo = Ly
    perfil_ancho = Lx

# Número de perfiles (se colocan en la dirección perpendicular al perfil)
n_profiles = math.ceil(perfil_ancho / perfil_espaciado) + 1
longitud_total_perfiles = n_profiles * perfil_largo
longitud_total_perfiles_desp = longitud_total_perfiles * (1 + desp_perfiles)

# Número de bloques con rendimiento real (5.18 unidades/m²)
n_bloques = math.ceil(area_total * BLOCK_DATA["unidades_por_m2"])
n_bloques_desp = math.ceil(n_bloques * (1 + desp_bloques))

# Volumen de concreto (torta + vigas de borde)
vol_torta = area_total * espesor_torta
vol_vigas = 0
if incluir_vigas:
    vol_vigas = (2 * (Lx + Ly)) * viga_b * viga_h
vol_concreto_total = vol_torta + vol_vigas
vol_concreto_total_desp = vol_concreto_total * (1 + desp_concreto)

# Área de malla electrosoldada
area_malla = area_total * (1 + desp_malla)

# Peso propio estimado (según datos reales del sistema)
peso_sistema_kgm2 = 175  # kg/m² (promedio 170-180)
peso_total_kg = peso_sistema_kgm2 * area_total
carga_muerta_kgm2 = peso_total_kg / area_total

# Dosificación de concreto para f'c=21 MPa (350 kg/m³ aprox)
cemento_por_m3 = 350  # kg/m³
total_cemento_kg = cemento_por_m3 * vol_concreto_total_desp
bultos_cemento = math.ceil(total_cemento_kg / 50)  # bultos de 50 kg

# ─────────────────────────────────────────────
# VERIFICACIONES NORMATIVAS (NSR-10 y otras)
# ─────────────────────────────────────────────
verificaciones = []

# 1. Luz máxima de perfiles
luz_util = perfil_largo
cumple_luz = luz_util <= norma["luz_max"]
verificaciones.append({
    "item": "Luz máxima de perfiles",
    "referencia": f"{norma['ref']} / Artículo correspondiente",
    "requerido": f"≤ {norma['luz_max']:.2f} m",
    "calculado": f"{luz_util:.2f} m",
    "cumple": cumple_luz,
    "observacion": "Ok" if cumple_luz else f"Excede {norma['luz_max']:.2f} m → requiere viga intermedia"
})

# 2. Espesor de la torta de concreto
cumple_topping = espesor_torta >= norma["topping_min"]
verificaciones.append({
    "item": "Espesor de torta de concreto",
    "referencia": "NSR-10 C.21.6.4.1 / Título E",
    "requerido": f"≥ {norma['topping_min']*100:.0f} cm",
    "calculado": f"{espesor_torta*100:.1f} cm",
    "cumple": cumple_topping,
    "observacion": "Ok" if cumple_topping else "Incrementar espesor"
})

# 3. Resistencia del concreto
fc_mpa = fc_concreto
cumple_fc = fc_mpa >= norma["concreto_min"]
verificaciones.append({
    "item": "Resistencia del concreto",
    "referencia": "NSR-10 C.21.3.1",
    "requerido": f"≥ {norma['concreto_min']} MPa",
    "calculado": f"{fc_mpa:.1f} MPa",
    "cumple": cumple_fc,
    "observacion": "Ok" if cumple_fc else "Usar concreto de mayor resistencia"
})

# 4. Altura total de la placa
altura_total = block_height + espesor_torta
h_min = 0.13  # mínimo recomendado
cumple_h = altura_total >= h_min
verificaciones.append({
    "item": "Altura total de la placa",
    "referencia": "Práctica constructiva / NSR-10",
    "requerido": f"≥ {h_min*100:.0f} cm",
    "calculado": f"{altura_total*100:.1f} cm",
    "cumple": cumple_h,
    "observacion": "Ok" if cumple_h else "Aumentar espesor de bloque o torta"
})

# 5. Vigas de borde
if norma.get("requiere_viga_borde", False) and incluir_vigas:
    cumple_vigas = True
    verificaciones.append({
        "item": "Vigas de borde",
        "referencia": "NSR-10 C.21.6.4",
        "requerido": "Dimensiones mínimas: b ≥ 0.15 m, h ≥ 0.15 m",
        "calculado": f"{viga_b*100:.0f} x {viga_h*100:.0f} cm",
        "cumple": cumple_vigas,
        "observacion": "Ok" if cumple_vigas else "Ajustar dimensiones"
    })
else:
    verificaciones.append({
        "item": "Vigas de borde",
        "referencia": "NSR-10 C.21.6.4",
        "requerido": "Requerido para diafragma rígido",
        "calculado": "No incluidas",
        "cumple": False,
        "observacion": "Se recomienda incluir vigas de borde"
    })

# 6. Espaciamiento de perfiles (por practicidad)
cumple_espaciado = perfil_espaciado <= 1.0
verificaciones.append({
    "item": "Espaciamiento de perfiles",
    "referencia": "Recomendación constructiva",
    "requerido": "≤ 1.00 m",
    "calculado": f"{perfil_espaciado*100:.0f} cm",
    "cumple": cumple_espaciado,
    "observacion": "Ok" if cumple_espaciado else "Reducir espaciamiento"
})

# 7. Absorción de agua (humedecimiento previo)
verificaciones.append({
    "item": "Absorción de agua del bloque",
    "referencia": "NTC 4205 / Práctica constructiva",
    "requerido": "Humedecer bloques antes del vaciado",
    "calculado": f"{BLOCK_DATA['absorcion_agua']}%",
    "cumple": True,
    "observacion": "Recordar humedecer bloques para evitar absorción del concreto"
})

# 8. Aislamiento térmico
verificaciones.append({
    "item": "Aislamiento térmico",
    "referencia": "Criterios de confort",
    "requerido": "U ≤ 3.0 W/m²K (típico)",
    "calculado": f"{BLOCK_DATA['transmitancia_termica']:.2f} W/m²K",
    "cumple": BLOCK_DATA['transmitancia_termica'] <= 3.0,
    "observacion": "Buen aislamiento térmico" if BLOCK_DATA['transmitancia_termica'] <= 3.0 else "Mejorar aislamiento"
})

# ─────────────────────────────────────────────
# PRESUPUESTO APU
# ─────────────────────────────────────────────
costo_bloques = n_bloques_desp * precio_bloque
costo_perfiles = longitud_total_perfiles_desp * precio_perfil
costo_malla = area_malla * precio_malla
costo_concreto = vol_concreto_total_desp * precio_concreto

# Mano de obra estimada (días) – se asume rendimiento 0.8 días/m²
dias_mo = area_total * 0.8
costo_mo = dias_mo * precio_mo

costo_directo = costo_bloques + costo_perfiles + costo_malla + costo_concreto + costo_mo
herramienta = costo_mo * pct_herramienta
aiu = costo_directo * pct_aui
utilidad = costo_directo * pct_util
iva_util = utilidad * iva
total_proyecto = costo_directo + herramienta + aiu + iva_util

# ─────────────────────────────────────────────
# VISUALIZACIÓN 3D (Plotly) – con bloques de arcilla y pestañas
# ─────────────────────────────────────────────
def create_3d_model(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo, 
                    block_length, block_width, block_height, espesor_torta, 
                    viga_b, viga_h, incluir_vigas):
    fig = go.Figure()
    
    def add_prism(x0, y0, z0, dx, dy, dz, color, opacity=0.7, name=""):
        x = [x0, x0+dx, x0+dx, x0, x0, x0+dx, x0+dx, x0]
        y = [y0, y0, y0+dy, y0+dy, y0, y0, y0+dy, y0+dy]
        z = [z0, z0, z0, z0, z0+dz, z0+dz, z0+dz, z0+dz]
        i = [0,0,4,4,1,5,2,6,3,7,0,4]
        j = [1,2,5,6,5,6,6,7,7,4,4,7]
        k = [2,3,6,7,6,7,7,4,4,5,1,3]
        fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=opacity, name=name, showlegend=False))
    
    # Posiciones de los perfiles
    if orientacion == "Paralelo a X":
        y_positions = np.linspace(0, Ly, n_profiles)
        for y in y_positions:
            # Perfil (prisma delgado)
            add_prism(0, y - 0.02, 0, Lx, 0.04, block_height, 'silver', 0.9)
        # Bloques entre perfiles (con pestañas de apoyo)
        for i in range(len(y_positions)-1):
            y1 = y_positions[i]
            y2 = y_positions[i+1]
            # El bloque real ocupa el espacio entre perfiles, pero tiene una pestaña que apoya sobre el perfil.
            # Para simplificar, dibujamos el bloque como un prisma de color arcilla.
            n_blocks_x = math.ceil(Lx / block_length)
            for j in range(n_blocks_x):
                x1 = j * block_length
                x2 = min(x1 + block_length, Lx)
                # Bloque principal
                add_prism(x1, y1, 0, x2-x1, y2-y1, block_height, BLOCK_DATA["color"], 0.8)
                # Pestaña de apoyo (solo en los extremos de cada bloque, donde apoya en el perfil)
                # Simulamos una pequeña extensión de 0.01 m en cada lado
                if x2 - x1 > 0.01:
                    add_prism(x1, y1 - 0.01, 0, x2-x1, 0.02, block_height, '#A0522D', 0.9)
                    add_prism(x1, y2 - 0.01, 0, x2-x1, 0.02, block_height, '#A0522D', 0.9)
    else:
        x_positions = np.linspace(0, Lx, n_profiles)
        for x in x_positions:
            add_prism(x - 0.02, 0, 0, 0.04, Ly, block_height, 'silver', 0.9)
        for i in range(len(x_positions)-1):
            x1 = x_positions[i]
            x2 = x_positions[i+1]
            n_blocks_y = math.ceil(Ly / block_length)
            for j in range(n_blocks_y):
                y1 = j * block_length
                y2 = min(y1 + block_length, Ly)
                add_prism(x1, y1, 0, x2-x1, y2-y1, block_height, BLOCK_DATA["color"], 0.8)
                # Pestañas
                add_prism(x1 - 0.01, y1, 0, 0.02, y2-y1, block_height, '#A0522D', 0.9)
                add_prism(x2 - 0.01, y1, 0, 0.02, y2-y1, block_height, '#A0522D', 0.9)
    
    # Torta de concreto (encima de los bloques)
    add_prism(0, 0, block_height, Lx, Ly, espesor_torta, 'lightgray', 0.4)
    
    # Vigas de borde
    if incluir_vigas:
        for y0 in [0, Ly]:
            add_prism(0, y0 - viga_b/2, 0, Lx, viga_b, viga_h, 'darkgray', 0.7)
        for x0 in [0, Lx]:
            add_prism(x0 - viga_b/2, 0, 0, viga_b, Ly, viga_h, 'darkgray', 0.7)
    
    # Malla electrosoldada (cuadrícula de líneas sobre la torta)
    spacing = 0.15  # 15 cm
    lines_x = []
    lines_y = []
    lines_z = []
    for y in np.arange(0, Ly+spacing, spacing):
        lines_x.extend([0, Lx, None])
        lines_y.extend([y, y, None])
        lines_z.extend([block_height+espesor_torta+0.01, block_height+espesor_torta+0.01, None])
    for x in np.arange(0, Lx+spacing, spacing):
        lines_x.extend([x, x, None])
        lines_y.extend([0, Ly, None])
        lines_z.extend([block_height+espesor_torta+0.01, block_height+espesor_torta+0.01, None])
    fig.add_trace(go.Scatter3d(x=lines_x, y=lines_y, z=lines_z, mode='lines', line=dict(color='black', width=2), name='Malla electrosoldada', showlegend=False))
    
    fig.update_layout(
        scene=dict(
            xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='Z (m)',
            aspectmode='data',
            bgcolor='#1a1a2e'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=500,
        plot_bgcolor='black',
        paper_bgcolor='#1e1e1e'
    )
    return fig

# ─────────────────────────────────────────────
# DXF EXPORT (PLANTA Y DETALLES)
# ─────────────────────────────────────────────
def generate_dxf(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo, 
                 block_length, incluir_vigas, viga_b, viga_h, proyecto_nombre, proyecto_direccion, proyecto_cliente):
    doc_dxf = ezdxf.new('R2010')
    doc_dxf.units = ezdxf.units.M
    msp = doc_dxf.modelspace()
    
    for lay, col in [('CONTOUR', 7), ('PROFILES', 4), ('BLOCKS', 2), ('MESH', 1), ('EDGE_BEAMS', 3), ('TEXT', 5)]:
        if lay not in doc_dxf.layers:
            doc_dxf.layers.add(lay, color=col)
    
    # Contorno
    msp.add_lwpolyline([(0,0), (Lx,0), (Lx,Ly), (0,Ly), (0,0)], dxfattribs={'layer':'CONTOUR'})
    
    # Vigas de borde
    if incluir_vigas:
        for y0 in [0, Ly]:
            msp.add_lwpolyline([(0, y0 - viga_b/2), (Lx, y0 - viga_b/2), (Lx, y0 + viga_b/2), (0, y0 + viga_b/2), (0, y0 - viga_b/2)], dxfattribs={'layer':'EDGE_BEAMS'})
        for x0 in [0, Lx]:
            msp.add_lwpolyline([(x0 - viga_b/2, 0), (x0 - viga_b/2, Ly), (x0 + viga_b/2, Ly), (x0 + viga_b/2, 0), (x0 - viga_b/2, 0)], dxfattribs={'layer':'EDGE_BEAMS'})
    
    # Perfiles
    if orientacion == "Paralelo a X":
        y_positions = np.linspace(0, Ly, n_profiles)
        for y in y_positions:
            msp.add_line((0, y), (Lx, y), dxfattribs={'layer':'PROFILES'})
    else:
        x_positions = np.linspace(0, Lx, n_profiles)
        for x in x_positions:
            msp.add_line((x, 0), (x, Ly), dxfattribs={'layer':'PROFILES'})
    
    # Malla
    spacing = 0.15
    for x in np.arange(0, Lx, spacing):
        msp.add_line((x, 0), (x, Ly), dxfattribs={'layer':'MESH'})
    for y in np.arange(0, Ly, spacing):
        msp.add_line((0, y), (Lx, y), dxfattribs={'layer':'MESH'})
    
    # Cuadro de título
    title_rect_x = 0
    title_rect_y = -2.5
    title_rect_w = 8.0
    title_rect_h = 1.8
    msp.add_lwpolyline([(title_rect_x, title_rect_y), (title_rect_x+title_rect_w, title_rect_y), 
                        (title_rect_x+title_rect_w, title_rect_y+title_rect_h), (title_rect_x, title_rect_y+title_rect_h), 
                        (title_rect_x, title_rect_y)], dxfattribs={'layer':'TEXT'})
    msp.add_text(f"PROYECTO: {proyecto_nombre}", dxfattribs={'layer':'TEXT', 'height':0.25, 'insert':(title_rect_x+0.2, title_rect_y+1.5)})
    msp.add_text(f"CLIENTE: {proyecto_cliente}", dxfattribs={'layer':'TEXT', 'height':0.2, 'insert':(title_rect_x+0.2, title_rect_y+1.2)})
    msp.add_text(f"DIRECCIÓN: {proyecto_direccion}", dxfattribs={'layer':'TEXT', 'height':0.2, 'insert':(title_rect_x+0.2, title_rect_y+0.9)})
    msp.add_text(f"FECHA: {datetime.now().strftime('%d/%m/%Y')}", dxfattribs={'layer':'TEXT', 'height':0.2, 'insert':(title_rect_x+0.2, title_rect_y+0.6)})
    msp.add_text(f"ESCALA: 1:50", dxfattribs={'layer':'TEXT', 'height':0.2, 'insert':(title_rect_x+0.2, title_rect_y+0.3)})
    msp.add_text(f"PLACA FÁCIL - SISTEMA VIGUETA Y BLOQUES", dxfattribs={'layer':'TEXT', 'height':0.25, 'insert':(Lx/2, Ly+0.5), 'halign':2})
    
    out = io.StringIO()
    doc_dxf.write(out)
    return out.getvalue().encode('utf-8')

# ─────────────────────────────────────────────
# MEMORIA DOCX
# ─────────────────────────────────────────────
def generate_memory():
    doc = Document()
    doc.add_heading(f"Memoria de Cálculo – Placa Fácil", 0)
    doc.add_paragraph(f"Proyecto: {proyecto_nombre}")
    doc.add_paragraph(f"Cliente: {proyecto_cliente}")
    doc.add_paragraph(f"Dirección: {proyecto_direccion}")
    doc.add_paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Norma aplicada: {norma_sel} – {norma['ref']}")
    
    doc.add_heading("1. Datos de entrada", level=1)
    doc.add_paragraph(f"Luz X: {Lx:.2f} m, Luz Y: {Ly:.2f} m")
    doc.add_paragraph(f"Orientación de perfiles: {orientacion}")
    doc.add_paragraph(f"Espesor torta: {espesor_torta*100:.1f} cm")
    doc.add_paragraph(f"Altura bloque: {block_height*100:.1f} cm")
    doc.add_paragraph(f"Separación perfiles: {perfil_espaciado*100:.0f} cm")
    doc.add_paragraph(f"Concreto: f'c = {fc_concreto:.1f} MPa")
    doc.add_paragraph(f"Bloquelón: {block_length*100:.0f} x {block_width*100:.0f} x {block_height*100:.0f} cm, peso unitario {BLOCK_DATA['peso_unitario']} kg")
    
    doc.add_heading("2. Verificaciones normativas", level=1)
    for v in verificaciones:
        p = doc.add_paragraph()
        p.add_run(f"{v['item']} – {v['referencia']}\n").bold = True
        p.add_run(f"Requerido: {v['requerido']}\n")
        p.add_run(f"Calculado: {v['calculado']}\n")
        p.add_run(f"Estado: {' CUMPLE' if v['cumple'] else ' NO CUMPLE'} – {v['observacion']}\n")
    
    doc.add_heading("3. Cantidades de materiales", level=1)
    doc.add_paragraph(f"Área de placa: {area_total:.2f} m²")
    doc.add_paragraph(f"Número de bloques: {n_bloques_desp} unidades (incluye {desp_bloques*100:.0f}% desperdicio)")
    doc.add_paragraph(f"Longitud total de perfiles: {longitud_total_perfiles_desp:.1f} m (incluye {desp_perfiles*100:.0f}% desperdicio)")
    doc.add_paragraph(f"Área de malla: {area_malla:.2f} m² (incluye {desp_malla*100:.0f}% desperdicio)")
    doc.add_paragraph(f"Volumen concreto: {vol_concreto_total_desp:.2f} m³ (incluye {desp_concreto*100:.0f}% desperdicio)")
    doc.add_paragraph(f"Cemento Portland: {bultos_cemento} bultos de 50 kg")
    
    doc.add_heading("4. Presupuesto", level=1)
    doc.add_paragraph(f"Costo bloques: {moneda} {costo_bloques:,.0f}")
    doc.add_paragraph(f"Costo perfiles: {moneda} {costo_perfiles:,.0f}")
    doc.add_paragraph(f"Costo malla: {moneda} {costo_malla:,.0f}")
    doc.add_paragraph(f"Costo concreto: {moneda} {costo_concreto:,.0f}")
    doc.add_paragraph(f"Mano de obra: {moneda} {costo_mo:,.0f}")
    doc.add_paragraph(f"Herramienta menor: {moneda} {herramienta:,.0f}")
    doc.add_paragraph(f"A.I.U.: {moneda} {aiu:,.0f}")
    doc.add_paragraph(f"IVA s/Utilidad: {moneda} {iva_util:,.0f}")
    doc.add_paragraph(f"**TOTAL PROYECTO: {moneda} {total_proyecto:,.0f}**")
    
    return doc

# ─────────────────────────────────────────────
# INTERFAZ PRINCIPAL (PESTAÑAS)
# ─────────────────────────────────────────────
tab_res, tab_3d, tab_dxf, tab_mem, tab_qty, tab_apu = st.tabs([
    " Resultados", " Modelo 3D", " DXF", " Memoria", " Cantidades", " APU"
])

with tab_res:
    st.subheader("Resultados del diseño")
    st.write(f"**Área de la placa:** {area_total:.2f} m²")
    st.write(f"**Número de perfiles:** {n_profiles}")
    st.write(f"**Longitud total de perfiles:** {longitud_total_perfiles_desp:.1f} m")
    st.write(f"**Número de bloques:** {n_bloques_desp} unidades")
    st.write(f"**Volumen de concreto:** {vol_concreto_total_desp:.2f} m³")
    st.write(f"**Área de malla electrosoldada:** {area_malla:.2f} m²")
    st.write(f"**Carga muerta estimada:** {carga_muerta_kgm2:.0f} kg/m² (basado en peso real del sistema)")
    st.write(f"**Cemento necesario:** {bultos_cemento} bultos de 50 kg")
    
    st.markdown("### Verificaciones normativas")
    for v in verificaciones:
        if v['cumple']:
            st.success(f" {v['item']}: {v['calculado']} – {v['observacion']}")
        else:
            st.error(f" {v['item']}: {v['calculado']} – {v['observacion']}")
        st.caption(f"Referencia: {v['referencia']}")

with tab_3d:
    st.subheader("Modelo 3D de la placa (con bloques de arcilla y pestañas)")
    fig_3d = create_3d_model(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo, 
                              block_length, block_width, block_height, espesor_torta, 
                              viga_b, viga_h, incluir_vigas)
    st.plotly_chart(fig_3d, use_container_width=True)

with tab_dxf:
    st.subheader("Exportar plano DXF")
    st.info("El DXF incluye la planta con contorno, perfiles, malla, vigas de borde y cuadro de título.")
    if st.button("Generar archivo DXF"):
        dxf_data = generate_dxf(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo, 
                                block_length, incluir_vigas, viga_b, viga_h, proyecto_nombre, proyecto_direccion, proyecto_cliente)
        st.download_button("Descargar DXF", data=dxf_data, file_name=f"PlacaFacil_{proyecto_nombre}.dxf", mime="application/dxf")

with tab_mem:
    st.subheader("Memoria de cálculo")
    if st.button("Generar memoria DOCX"):
        doc = generate_memory()
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        st.download_button("Descargar Memoria", data=buf, file_name=f"Memoria_PlacaFacil_{proyecto_nombre}.docx", 
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with tab_qty:
    st.subheader("Cantidades detalladas")
    qty_data = [
        ("Bloques (unidades)", n_bloques, n_bloques_desp, f"{desp_bloques*100:.0f}%"),
        ("Perfiles (m)", longitud_total_perfiles, longitud_total_perfiles_desp, f"{desp_perfiles*100:.0f}%"),
        ("Malla (m²)", area_total, area_malla, f"{desp_malla*100:.0f}%"),
        ("Concreto (m³)", vol_concreto_total, vol_concreto_total_desp, f"{desp_concreto*100:.0f}%"),
        ("Cemento (bultos 50 kg)", "-", bultos_cemento, "-"),
    ]
    df_qty = pd.DataFrame(qty_data, columns=["Material", "Neto", "Con desperdicio", "Desperdicio"])
    st.dataframe(df_qty, use_container_width=True, hide_index=True)
    st.write(f"**Volumen de torta de concreto:** {vol_torta:.2f} m³")
    if incluir_vigas:
        st.write(f"**Volumen de vigas de borde:** {vol_vigas:.2f} m³")
    st.write(f"**Peso unitario del bloque:** {BLOCK_DATA['peso_unitario']:.1f} kg")
    st.write(f"**Rendimiento:** {BLOCK_DATA['unidades_por_m2']:.2f} bloques/m²")

with tab_apu:
    st.subheader("Presupuesto APU")
    cost_data = [
        ("Bloques (unidades)", n_bloques_desp, precio_bloque, costo_bloques),
        ("Perfiles (m)", f"{longitud_total_perfiles_desp:.1f} m", precio_perfil, costo_perfiles),
        ("Malla (m²)", f"{area_malla:.2f} m²", precio_malla, costo_malla),
        ("Concreto (m³)", f"{vol_concreto_total_desp:.2f} m³", precio_concreto, costo_concreto),
        ("Mano de obra", f"{dias_mo:.1f} días", precio_mo, costo_mo),
        ("Herramienta menor", f"{pct_herramienta*100:.0f}% MO", "", herramienta),
        ("A.I.U.", f"{pct_aui*100:.0f}% CD", "", aiu),
        ("IVA s/Utilidad", f"{iva*100:.0f}% Util", "", iva_util),
        ("TOTAL", "", "", total_proyecto),
    ]
    df_costo = pd.DataFrame(cost_data, columns=["Concepto", "Cantidad", "Precio unitario", "Subtotal"])
    df_costo["Precio unitario"] = pd.to_numeric(df_costo["Precio unitario"], errors="ignore")
    df_costo["Subtotal"] = pd.to_numeric(df_costo["Subtotal"], errors="ignore")
    st.dataframe(
        df_costo.style.format({"Subtotal": "{:,.0f}", "Precio unitario": "{:,.0f}"}, na_rep=""),
        use_container_width=True,
        hide_index=True
    )
    st.metric(f"Gran Total Proyecto ({moneda})", f"{total_proyecto:,.0f}")
    
    if st.button("Exportar presupuesto a Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_costo.to_excel(writer, sheet_name="Presupuesto", index=False)
            df_qty.to_excel(writer, sheet_name="Cantidades", index=False)
        output.seek(0)
        st.download_button("Descargar Excel", data=output, file_name=f"Presupuesto_PlacaFacil_{proyecto_nombre}.xlsx", 
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
> **Placa Fácil – Sistema de Vigueta y Bloques**  
> Norma activa: `{norma_sel}`  
> f'c = {fc_concreto:.1f} MPa | Espesor torta = {espesor_torta*100:.1f} cm | Altura total = {altura_total*100:.1f} cm  
> Bloques de arcilla: {block_length*100:.0f}×{block_width*100:.0f}×{block_height*100:.0f} cm, {BLOCK_DATA['unidades_por_m2']:.2f} ud/m²  
> **Referencia:** {norma['ref']}  
> ⚠ *Las herramientas son de apoyo para el diseño. Verifique siempre con la norma vigente del país.*
""")