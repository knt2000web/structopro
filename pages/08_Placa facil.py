import streamlit as st
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import pandas as pd
import math
import io
import ezdxf
from ezdxf.math import Vec2
from ezdxf import colors
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors as rl_colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es
# ─────────────────────────────────────────────

st.set_page_config(page_title=_t("Placa Fácil", "Easy Slab"), layout="wide")
st.title(_t("Placa Fácil – Sistema de Vigueta y Bloques", "Easy Slab – Joist & Block System"))
st.markdown(_t("Diseño de losas con vigueta metálica y bloques de concreto (Placa Fácil). Verificación según NSR-10 (Colombia) y normas internacionales.", 
               "Design of slabs with metal joists and concrete blocks (Easy Slab). Verification according to NSR-10 (Colombia) and international codes."))

# ─────────────────────────────────────────────
# DATOS DE MATERIALES (Colombia) – basados en detalles.pdf
# ─────────────────────────────────────────────
BLOCK_DATA = {
    "nombre": "Bloquelón Santafé",
    "largo": 0.80,      # m
    "ancho": 0.23,      # m
    "alto": 0.08,       # m
    "peso_unitario": 13,  # kg
    "rendimiento_por_m2": 5.18,
    "color": "#C19A6B",
    "pestana": 0.015,   # m
}
PROFILE_DATA = {
    "nombre": "Perfil Colmena",
    "alto_total": 0.080,     # m (80 mm)
    "ancho_alma": 0.040,     # m (40 mm)
    "espesor_alma": 0.002,   # m (2 mm)
    "ancho_ala": 0.025,      # m (25 mm)
    "espesor_ala": 0.002,    # m (2 mm)
    "peso_por_m": 9.8,       # kg/m
    "color": "#C0C0C0",
}
MESH_DATA = {
    "nombre": "Malla Electrosoldada Q2",
    "diametro": 0.00635,   # m (1/4")
    "espaciado_largo": 0.25,   # m (25 cm)
    "espaciado_corto": 0.40,   # m (40 cm)
    "traslapo": 0.15,         # m
    "peso_por_m2": 3.0,
}
CONCRETE_DATA = {
    "resistencia": 21,   # MPa
    "densidad": 2400,    # kg/m³
    "cemento_por_m3": 350,  # kg/m³
}
SYSTEM_DATA = {
    "peso_por_m2": 175,   # kg/m²
    "absorcion_agua": "Alta (se debe humedecer antes de fundir)",
    "aislamiento_termico": "U ≈ 2.10 W/m²K",
}
CARGA_VIVA = {
    "Residencial": 1.8,
    "Comercial": 2.5,
    "Industrial": 3.5,
    "Oficinas": 2.4,
}
NORMAS_PLACA = {
    "NSR-10 (Colombia)": {
        "luz_max": 4.2,
        "topping_min": 0.04,
        "concreto_min": 21,
        "requiere_viga_borde": True,
        "ref": "NSR-10 Capítulo C.21 y Título E",
    },
    "E.060 (Perú)": {
        "luz_max": 4.2,
        "topping_min": 0.04,
        "concreto_min": 21,
        "requiere_viga_borde": True,
        "ref": "E.060 / NTE E.030",
    },
    "ACI 318-25 (EE.UU.)": {
        "luz_max": 4.2,
        "topping_min": 0.04,
        "concreto_min": 21,
        "requiere_viga_borde": True,
        "ref": "ACI 318-25 Capítulo 7",
    },
}

# Función para inercia del perfil Colmena (real)
def profile_inertia():
    h = PROFILE_DATA["alto_total"]
    b_web = PROFILE_DATA["ancho_alma"]
    t_web = PROFILE_DATA["espesor_alma"]
    b_flange = PROFILE_DATA["ancho_ala"]
    t_flange = PROFILE_DATA["espesor_ala"]
    h_cm = h * 100
    b_web_cm = b_web * 100
    t_web_cm = t_web * 100
    b_flange_cm = b_flange * 100
    t_flange_cm = t_flange * 100
    A_web = b_web_cm * t_web_cm
    A_flange = b_flange_cm * t_flange_cm
    y_web = h_cm / 2
    y_flange = t_flange_cm / 2
    I_web = (b_web_cm * t_web_cm**3) / 12
    I_flange = (b_flange_cm * t_flange_cm**3) / 12
    d_web = y_web - (h_cm / 2)
    d_flange = y_flange - (h_cm / 2)
    I_total = (I_web + A_web * d_web**2) + 2 * (I_flange + A_flange * d_flange**2)
    return I_total / 10000  # m⁴

# ─────────────────────────────────────────────
# SIDEBAR – CONFIGURACIÓN DEL PROYECTO
# ─────────────────────────────────────────────
norma_sel = st.sidebar.selectbox(_t("Norma de diseño", "Design code"), list(NORMAS_PLACA.keys()), index=0)
norma = NORMAS_PLACA[norma_sel]

st.sidebar.header(_t("Datos del proyecto", "Project data"))
proyecto_nombre = st.sidebar.text_input(_t("Nombre del proyecto", "Project name"), "Placa Fácil - Ejemplo")
proyecto_direccion = st.sidebar.text_input(_t("Dirección de obra", "Site address"), "Calle 123, Bogotá")
proyecto_cliente = st.sidebar.text_input(_t("Cliente / Propietario", "Client / Owner"), "Constructora XYZ")
num_pisos = st.sidebar.number_input(_t("Número de pisos", "Number of floors"), 1, 10, 1, 1)
uso_placa = st.sidebar.selectbox(_t("Uso de la placa", "Slab use"), list(CARGA_VIVA.keys()), index=0)
carga_viva_kn = CARGA_VIVA[uso_placa]

st.sidebar.header(_t("Geometría de la placa", "Slab geometry"))
Lx = st.sidebar.number_input(_t("Luz X (m)", "Span X (m)"), 2.0, 12.0, 6.0, 0.1)
Ly = st.sidebar.number_input(_t("Luz Y (m)", "Span Y (m)"), 2.0, 12.0, 5.0, 0.1)
orientacion = st.sidebar.selectbox(_t("Dirección de los perfiles", "Profile direction"), ["Paralelo a X", "Paralelo a Y"], index=0)

st.sidebar.header(_t("Parámetros de diseño", "Design parameters"))
espesor_torta = st.sidebar.number_input(_t("Espesor de la torta de concreto (cm)", "Concrete topping thickness (cm)"), 4.0, 10.0, 5.0, 0.5) / 100.0
fc_concreto = st.sidebar.number_input(_t("Resistencia f'c concreto (MPa)", "Concrete strength f'c (MPa)"), 18.0, 35.0, 21.0, 0.5)
perfil_espaciado = st.sidebar.number_input(_t("Separación entre perfiles (cm)", "Profile spacing (cm)"), 70.0, 100.0, 89.0, 1.0) / 100.0
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

st.sidebar.header(_t("Datos del plano", "Drawing data"))
plano_numero = st.sidebar.text_input(_t("Número de plano", "Drawing number"), "PL-01")
escala_plano = st.sidebar.text_input(_t("Escala", "Scale"), "1:50")
revisado = st.sidebar.text_input(_t("Revisado por", "Reviewed by"), "J. Pérez")
aprobado = st.sidebar.text_input(_t("Aprobado por", "Approved by"), "C. Giraldo")

# ─────────────────────────────────────────────
# CÁLCULOS DE CANTIDADES
# ─────────────────────────────────────────────
area_total = Lx * Ly * num_pisos
if orientacion == "Paralelo a X":
    perfil_largo = Lx
    perfil_ancho = Ly
else:
    perfil_largo = Ly
    perfil_ancho = Lx

n_profiles = math.ceil(perfil_ancho / perfil_espaciado) + 1
longitud_total_perfiles = n_profiles * perfil_largo
longitud_total_perfiles_desp = longitud_total_perfiles * (1 + desp_perfiles) * num_pisos

if orientacion == "Paralelo a X":
    n_hileras = n_profiles - 1
    bloques_por_hilera = math.ceil(Lx / BLOCK_DATA["largo"])
else:
    n_hileras = n_profiles - 1
    bloques_por_hilera = math.ceil(Ly / BLOCK_DATA["largo"])
n_bloques = n_hileras * bloques_por_hilera
n_bloques_desp = math.ceil(n_bloques * (1 + desp_bloques)) * num_pisos

vol_torta = area_total * espesor_torta
vol_vigas = 0
if incluir_vigas:
    vol_vigas = (2 * (Lx + Ly)) * viga_b * viga_h * num_pisos
vol_concreto_total = vol_torta + vol_vigas
vol_concreto_total_desp = vol_concreto_total * (1 + desp_concreto)

area_malla = area_total * (1 + desp_malla + 0.15)

peso_bloques_kg = n_bloques * BLOCK_DATA["peso_unitario"]
peso_concreto_kg = vol_concreto_total * CONCRETE_DATA["densidad"]
peso_perfiles_kg = longitud_total_perfiles * PROFILE_DATA["peso_por_m"] * num_pisos
peso_total_kg = peso_bloques_kg + peso_concreto_kg + peso_perfiles_kg
carga_muerta_kgm2 = peso_total_kg / (Lx * Ly * num_pisos) if (Lx * Ly * num_pisos) > 0 else 0

total_cemento_kg = CONCRETE_DATA["cemento_por_m3"] * vol_concreto_total_desp
bultos_cemento = math.ceil(total_cemento_kg / 50)

# Alertas
if perfil_largo > 3.5 and perfil_largo <= 4.2:
    st.warning(f"⚠️ La luz de los perfiles es {perfil_largo:.2f} m. Está cerca del máximo de {norma['luz_max']} m.")
elif perfil_largo > norma["luz_max"]:
    st.error(f"❌ La luz de los perfiles ({perfil_largo:.2f} m) excede el máximo permitido ({norma['luz_max']} m). Se requiere viga intermedia.")

# ─────────────────────────────────────────────
# CÁLCULOS ESTRUCTURALES DE LA PLACA
# ─────────────────────────────────────────────
g = 9.81
Wd_kg = carga_muerta_kgm2
Wd_kn = Wd_kg * g / 1000
Wu_kn = 1.2 * Wd_kn + 1.6 * carga_viva_kn
Wu_lin = Wu_kn * perfil_espaciado
Mu = Wu_lin * perfil_largo**2 / 8

I_real = profile_inertia()
E_concreto = 4700 * math.sqrt(fc_concreto * 1000) * 1e6
Wserv_kn = Wd_kn + carga_viva_kn
Wserv_lin = Wserv_kn * perfil_espaciado
delta_max = perfil_largo / 360
delta_calc = (5 * Wserv_lin * perfil_largo**4) / (384 * E_concreto * I_real) if I_real > 0 else 0
cumple_deflexion = delta_calc <= delta_max

As_min = 0.0018 * BLOCK_DATA["ancho"] * espesor_torta
As_malla = MESH_DATA["diametro"]**2 * math.pi / 4 * 1000 / MESH_DATA["espaciado_largo"]
cumple_malla = As_malla >= As_min

Vu = Wu_lin * perfil_largo / 2
Vc = 0.17 * math.sqrt(fc_concreto * 1000) * BLOCK_DATA["ancho"] * (BLOCK_DATA["alto"] + espesor_torta) / 1000
cumple_cortante = Vu <= Vc

# ─────────────────────────────────────────────
# DISEÑO DE LA VIGA DE BORDE
# ─────────────────────────────────────────────
# Carga sobre la viga de borde: proviene de la losa + peso propio
# Ancho tributario: mitad del primer vano (perfil_espaciado/2) más el borde.
# Para simplificar, asumimos carga uniforme por metro lineal:
W_beam_kn = Wu_kn * (perfil_espaciado/2 + 0.5)  # kN/m (ancho tributario medio)
# Luz de la viga de borde: la mayor entre Lx y Ly (la longitud de la viga)
beam_span = max(Lx, Ly)
# Momento y cortante en la viga de borde (simplemente apoyada)
Mu_beam = W_beam_kn * beam_span**2 / 8
Vu_beam = W_beam_kn * beam_span / 2

# Resistencia a flexión de la viga (sección rectangular)
d_beam = viga_h - 0.05  # peralte efectivo (m)
b_beam = viga_b
# Cálculo del acero requerido (simplificado, asumiendo sección sub-reforzada)
# Rn = Mu / (φ * b * d²) con φ = 0.9
Rn = Mu_beam / (0.9 * b_beam * d_beam**2) * 1e6  # en MPa
rho = (0.85 * fc_concreto / 420) * (1 - math.sqrt(1 - 2 * Rn / (0.85 * fc_concreto))) if Rn > 0 else 0
As_beam = rho * b_beam * d_beam * 1e4  # cm²
As_min_beam = 0.0018 * b_beam * viga_h * 1e4  # cm²
As_beam = max(As_beam, As_min_beam)
# Selección de varillas: 2#4 (1.29 cm² cada) + 1#5 (1.99 cm²) = 4.57 cm²
As_prov_beam = 4.57
# Estribos: separación máxima = d/2 = 0.2 m aprox, se usa @0.20 m
s_beam = 0.20

# Verificaciones de la viga
Vc_beam = 0.17 * math.sqrt(fc_concreto * 1000) * b_beam * d_beam / 1000
cumple_cortante_beam = Vu_beam <= Vc_beam
cumple_flexion_beam = As_prov_beam >= As_beam
ref_beam = f"2#4 + 1#5 (As={As_prov_beam:.2f} cm²)"

# Diagramas de momento y cortante de la viga
x_vals = np.linspace(0, beam_span, 100)
M_vals = W_beam_kn * x_vals * (beam_span - x_vals) / 2
V_vals = W_beam_kn * (beam_span/2 - x_vals)

# ─────────────────────────────────────────────
# VERIFICACIONES NORMATIVAS (incluyendo viga)
# ─────────────────────────────────────────────
verificaciones = []
verificaciones.append({
    "item": "Luz máxima de perfiles",
    "referencia": norma['ref'],
    "requerido": f"≤ {norma['luz_max']:.2f} m",
    "calculado": f"{perfil_largo:.2f} m",
    "cumple": perfil_largo <= norma["luz_max"],
    "obs": "Ok" if perfil_largo <= norma["luz_max"] else "Excede → requiere viga intermedia"
})
verificaciones.append({
    "item": "Espesor de torta de concreto",
    "referencia": "NSR-10 C.21.6.4.1",
    "requerido": f"≥ {norma['topping_min']*100:.0f} cm",
    "calculado": f"{espesor_torta*100:.1f} cm",
    "cumple": espesor_torta >= norma["topping_min"],
    "obs": "Ok" if espesor_torta >= norma["topping_min"] else "Incrementar espesor"
})
verificaciones.append({
    "item": "Resistencia del concreto",
    "referencia": "NSR-10 C.21.3.1",
    "requerido": f"≥ {norma['concreto_min']} MPa",
    "calculado": f"{fc_concreto:.1f} MPa",
    "cumple": fc_concreto >= norma["concreto_min"],
    "obs": "Ok" if fc_concreto >= norma["concreto_min"] else "Usar concreto de mayor resistencia"
})
verificaciones.append({
    "item": "Deflexión (L/360)",
    "referencia": "NSR-10 C.9.5.2",
    "requerido": f"≤ {delta_max*1000:.1f} mm",
    "calculado": f"{delta_calc*1000:.1f} mm",
    "cumple": cumple_deflexion,
    "obs": "Ok" if cumple_deflexion else "Aumentar peralte o reducir luz"
})
verificaciones.append({
    "item": "Cortante en apoyo (placa)",
    "referencia": "NSR-10 C.11",
    "requerido": f"Vu ≤ {Vc:.2f} kN",
    "calculado": f"Vu = {Vu:.2f} kN",
    "cumple": cumple_cortante,
    "obs": "Ok" if cumple_cortante else "Aumentar sección de viga"
})
verificaciones.append({
    "item": "Acero mínimo de malla",
    "referencia": "NSR-10 C.7.12",
    "requerido": f"As ≥ {As_min*100:.2f} cm²/m",
    "calculado": f"As = {As_malla:.2f} cm²/m",
    "cumple": cumple_malla,
    "obs": "Ok" if cumple_malla else "Aumentar diámetro o reducir espaciamiento"
})
verificaciones.append({
    "item": "Viga de borde - Momento",
    "referencia": "NSR-10 C.21.6",
    "requerido": f"As ≥ {As_beam:.2f} cm²",
    "calculado": f"As prov = {As_prov_beam:.2f} cm²",
    "cumple": cumple_flexion_beam,
    "obs": "Ok" if cumple_flexion_beam else "Aumentar acero"
})
verificaciones.append({
    "item": "Viga de borde - Cortante",
    "referencia": "NSR-10 C.11",
    "requerido": f"Vu ≤ {Vc_beam:.2f} kN",
    "calculado": f"Vu = {Vu_beam:.2f} kN",
    "cumple": cumple_cortante_beam,
    "obs": "Ok" if cumple_cortante_beam else "Aumentar sección o estribos"
})
altura_total = BLOCK_DATA["alto"] + espesor_torta
h_min = 0.13
verificaciones.append({
    "item": "Altura total de la placa",
    "referencia": "Práctica constructiva",
    "requerido": f"≥ {h_min*100:.0f} cm",
    "calculado": f"{altura_total*100:.1f} cm",
    "cumple": altura_total >= h_min,
    "obs": "Ok" if altura_total >= h_min else "Aumentar espesor de bloque o torta"
})
if norma.get("requiere_viga_borde", False) and incluir_vigas:
    verificaciones.append({
        "item": "Vigas de borde",
        "referencia": "NSR-10 C.21.6.4",
        "requerido": "Incluidas",
        "calculado": "Sí",
        "cumple": True,
        "obs": "Ok"
    })
else:
    verificaciones.append({
        "item": "Vigas de borde",
        "referencia": "NSR-10 C.21.6.4",
        "requerido": "Requerido para diafragma rígido",
        "calculado": "No incluidas",
        "cumple": False,
        "obs": "Se recomienda incluir vigas de borde"
    })

# ─────────────────────────────────────────────
# PRESUPUESTO APU
# ─────────────────────────────────────────────
costo_bloques = n_bloques_desp * precio_bloque
costo_perfiles = longitud_total_perfiles_desp * precio_perfil
costo_malla = area_malla * precio_malla
costo_concreto = vol_concreto_total_desp * precio_concreto
dias_mo = area_total * 0.8
costo_mo = dias_mo * precio_mo
costo_directo = costo_bloques + costo_perfiles + costo_malla + costo_concreto + costo_mo
herramienta = costo_mo * pct_herramienta
aiu = costo_directo * pct_aui
utilidad = costo_directo * pct_util
iva_util = utilidad * iva
total_proyecto = costo_directo + herramienta + aiu + iva_util

costo_maciza = vol_concreto_total * 1.2 * precio_concreto
ahorro = total_proyecto - costo_maciza if total_proyecto < costo_maciza else 0
sobrecosto = total_proyecto - costo_maciza if total_proyecto > costo_maciza else 0

actividades = ["Instalación de perfiles", "Colocación de bloques", "Colocación de malla", "Fundida de concreto", "Curado"]
duracion_dias = [0.5 * area_total / 100, 1.0 * area_total / 100, 0.3 * area_total / 100, 1.5 * area_total / 100, 0.5]
cronograma = pd.DataFrame({"Actividad": actividades, "Duración (días)": [max(1, round(d)) for d in duracion_dias]})

# ─────────────────────────────────────────────
# FUNCIONES DE DIBUJO
# ─────────────────────────────────────────────
def create_3d_model(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo,
                    espesor_torta, incluir_vigas, viga_b, viga_h):
    fig = go.Figure()
    def add_prism(x0, y0, z0, dx, dy, dz, color, opacity=0.8):
        x = [x0, x0+dx, x0+dx, x0, x0, x0+dx, x0+dx, x0]
        y = [y0, y0, y0+dy, y0+dy, y0, y0, y0+dy, y0+dy]
        z = [z0, z0, z0, z0, z0+dz, z0+dz, z0+dz, z0+dz]
        i = [0,0,4,4,1,5,2,6,3,7,0,4]
        j = [1,2,5,6,5,6,6,7,7,4,4,7]
        k = [2,3,6,7,6,7,7,4,4,5,1,3]
        fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=opacity, showlegend=False))
    def add_profile_c(x0, y0, z0, length, color):
        w_web = PROFILE_DATA["ancho_alma"]
        w_flange = PROFILE_DATA["ancho_ala"]
        h = PROFILE_DATA["alto_total"]
        add_prism(x0, y0 - w_web/2, z0, length, w_web, h, color, 0.9)
        add_prism(x0, y0 - w_flange/2, z0 + h - PROFILE_DATA["espesor_ala"], length, w_flange, PROFILE_DATA["espesor_ala"], color, 0.9)
        add_prism(x0, y0 - w_flange/2, z0, length, w_flange, PROFILE_DATA["espesor_ala"], color, 0.9)
    if orientacion == "Paralelo a X":
        y_positions = np.linspace(0, Ly, n_profiles)
        for y in y_positions:
            add_profile_c(0, y, 0, Lx, PROFILE_DATA["color"])
        for i in range(len(y_positions)-1):
            y1 = y_positions[i]
            y2 = y_positions[i+1]
            n_blocks_x = math.ceil(Lx / BLOCK_DATA["largo"])
            for j in range(n_blocks_x):
                x1 = j * BLOCK_DATA["largo"]
                x2 = min(x1 + BLOCK_DATA["largo"], Lx)
                add_prism(x1, y1, 0, x2-x1, y2-y1, BLOCK_DATA["alto"], BLOCK_DATA["color"], 0.8)
    else:
        x_positions = np.linspace(0, Lx, n_profiles)
        for x in x_positions:
            add_profile_c(x, 0, 0, Ly, PROFILE_DATA["color"])
        for i in range(len(x_positions)-1):
            x1 = x_positions[i]
            x2 = x_positions[i+1]
            n_blocks_y = math.ceil(Ly / BLOCK_DATA["largo"])
            for j in range(n_blocks_y):
                y1 = j * BLOCK_DATA["largo"]
                y2 = min(y1 + BLOCK_DATA["largo"], Ly)
                add_prism(x1, y1, 0, x2-x1, y2-y1, BLOCK_DATA["alto"], BLOCK_DATA["color"], 0.8)
    add_prism(0, 0, BLOCK_DATA["alto"], Lx, Ly, espesor_torta, "lightgray", 0.4)
    if incluir_vigas:
        for y0 in [0, Ly]:
            add_prism(0, y0 - viga_b/2, 0, Lx, viga_b, viga_h, "darkgray", 0.7)
        for x0 in [0, Lx]:
            add_prism(x0 - viga_b/2, 0, 0, viga_b, Ly, viga_h, "darkgray", 0.7)
    spacing = MESH_DATA["espaciado_largo"]
    lines_x, lines_y, lines_z = [], [], []
    for y in np.arange(0, Ly+spacing, spacing):
        lines_x.extend([0, Lx, None]); lines_y.extend([y, y, None]); lines_z.extend([BLOCK_DATA["alto"]+espesor_torta+0.01, BLOCK_DATA["alto"]+espesor_torta+0.01, None])
    for x in np.arange(0, Lx+spacing, spacing):
        lines_x.extend([x, x, None]); lines_y.extend([0, Ly, None]); lines_z.extend([BLOCK_DATA["alto"]+espesor_torta+0.01, BLOCK_DATA["alto"]+espesor_torta+0.01, None])
    fig.add_trace(go.Scatter3d(x=lines_x, y=lines_y, z=lines_z, mode='lines', line=dict(color='black', width=2), showlegend=False))
    fig.update_layout(
        scene=dict(xaxis_title='X (m)', yaxis_title='Y (m)', zaxis_title='Z (m)', aspectmode='data', bgcolor='#1a1a2e'),
        margin=dict(l=0, r=0, b=0, t=0), height=500, plot_bgcolor='black', paper_bgcolor='#1e1e1e'
    )
    return fig

def generate_dxf(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo,
                 incluir_vigas, viga_b, viga_h, proyecto_nombre, proyecto_direccion, proyecto_cliente,
                 plano_numero, escala_plano, revisado, aprobado, ref_beam):
    doc_dxf = ezdxf.new('R2010')
    doc_dxf.units = ezdxf.units.M
    msp = doc_dxf.modelspace()
    
    # Definir estilo de cotas (no se usa add_linear_dim, lo haremos manual)
    # Capas
    capas = [
        ('ROTULO', 7), ('ROTULO_TEXTO', 5), ('COTAS', 3), ('ACHURADO', 253),
        ('REFUERZO', 1), ('EJES', 2), ('CORTE', 4), ('NOTAS', 8), ('CONCRETO', 7),
        ('PERFILES', 4), ('BLOQUES', 2), ('MALLA', 1)
    ]
    for lay, col in capas:
        if lay not in doc_dxf.layers:
            doc_dxf.layers.add(lay, color=col)
    
    # Rótulo profesional
    rot_x, rot_y = 0, -2.8
    rot_w, rot_h = 10, 2.5
    msp.add_lwpolyline([(rot_x, rot_y), (rot_x+rot_w, rot_y), (rot_x+rot_w, rot_y+rot_h), (rot_x, rot_y+rot_h), (rot_x, rot_y)], dxfattribs={'layer':'ROTULO', 'color':7})
    col1_w, col2_w, col3_w = 2.5, 5.0, 2.5
    msp.add_line((rot_x+col1_w, rot_y), (rot_x+col1_w, rot_y+rot_h), dxfattribs={'layer':'ROTULO', 'color':7})
    msp.add_line((rot_x+col1_w+col2_w, rot_y), (rot_x+col1_w+col2_w, rot_y+rot_h), dxfattribs={'layer':'ROTULO', 'color':7})
    fila_h = rot_h / 5
    for i in range(1, 5):
        yf = rot_y + i * fila_h
        msp.add_line((rot_x, yf), (rot_x+rot_w, yf), dxfattribs={'layer':'ROTULO', 'color':7})
    textos = [
        ("PROYECTO:", proyecto_nombre, "PLANO Nº:", plano_numero),
        ("CLIENTE:", proyecto_cliente, "ESCALA:", escala_plano),
        ("DIRECCIÓN:", proyecto_direccion, "NORMA:", norma_sel),
        ("FECHA:", datetime.now().strftime('%d/%m/%Y'), "REVISIÓN:", "00"),
        ("ELABORÓ:", "C. Giraldo", "APROBÓ:", aprobado),
    ]
    for i, (txt1, val1, txt2, val2) in enumerate(textos):
        y_txt = rot_y + (i+0.5) * fila_h
        msp.add_text(txt1, dxfattribs={'layer':'ROTULO_TEXTO', 'height':0.15, 'insert':(rot_x+0.1, y_txt)})
        msp.add_text(val1, dxfattribs={'layer':'ROTULO_TEXTO', 'height':0.15, 'insert':(rot_x+0.1, y_txt-0.2)})
        msp.add_text(txt2, dxfattribs={'layer':'ROTULO_TEXTO', 'height':0.15, 'insert':(rot_x+col1_w+0.1, y_txt)})
        msp.add_text(val2, dxfattribs={'layer':'ROTULO_TEXTO', 'height':0.15, 'insert':(rot_x+col1_w+0.1, y_txt-0.2)})
        msp.add_text(val1, dxfattribs={'layer':'ROTULO_TEXTO', 'height':0.15, 'insert':(rot_x+col1_w+col2_w+0.1, y_txt-0.1)})
    
    # Contorno de losa
    msp.add_lwpolyline([(0,0), (Lx,0), (Lx,Ly), (0,Ly), (0,0)], dxfattribs={'layer':'CONCRETO', 'color':7})
    
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
            msp.add_line((0, y), (Lx, y), dxfattribs={'layer':'PERFILES', 'color':4})
    else:
        x_positions = np.linspace(0, Lx, n_profiles)
        for x in x_positions:
            msp.add_line((x, 0), (x, Ly), dxfattribs={'layer':'PERFILES', 'color':4})
    
    # Malla con círculos
    spacing_x = MESH_DATA["espaciado_largo"]
    spacing_y = MESH_DATA["espaciado_corto"]
    for x in np.arange(0, Lx, spacing_x):
        msp.add_line((x, 0), (x, Ly), dxfattribs={'layer':'MALLA', 'color':1})
    for y in np.arange(0, Ly, spacing_y):
        msp.add_line((0, y), (Lx, y), dxfattribs={'layer':'MALLA', 'color':1})
    for x in np.arange(0, Lx, spacing_x):
        for y in np.arange(0, Ly, spacing_y):
            msp.add_circle((x, y), 0.02, dxfattribs={'layer':'MALLA', 'color':1})
    
    # Detalle Corte A-A
    off_x = Lx + 1
    # Concreto
    msp.add_lwpolyline([(off_x, 0), (off_x+1.5, 0), (off_x+1.5, espesor_torta), (off_x, espesor_torta), (off_x, 0)], dxfattribs={'layer':'CONCRETO'})
    # Bloque
    msp.add_lwpolyline([(off_x, espesor_torta), (off_x+1.5, espesor_torta), (off_x+1.5, espesor_torta+BLOCK_DATA["alto"]), (off_x, espesor_torta+BLOCK_DATA["alto"]), (off_x, espesor_torta)], dxfattribs={'layer':'BLOQUES'})
    # Perfil Colmena
    perfil_x0 = off_x + 0.5
    w_web = PROFILE_DATA["ancho_alma"]
    w_flange = PROFILE_DATA["ancho_ala"]
    h = PROFILE_DATA["alto_total"]
    msp.add_lwpolyline([(perfil_x0, espesor_torta), (perfil_x0+w_web, espesor_torta), (perfil_x0+w_web, espesor_torta+h), (perfil_x0, espesor_torta+h), (perfil_x0, espesor_torta)], dxfattribs={'layer':'PERFILES'})
    # Alas (simplificadas)
    msp.add_lwpolyline([(perfil_x0 - (w_flange-w_web)/2, espesor_torta+h-PROFILE_DATA["espesor_ala"]), (perfil_x0+w_web+(w_flange-w_web)/2, espesor_torta+h-PROFILE_DATA["espesor_ala"]), (perfil_x0+w_web+(w_flange-w_web)/2, espesor_torta+h), (perfil_x0 - (w_flange-w_web)/2, espesor_torta+h), (perfil_x0 - (w_flange-w_web)/2, espesor_torta+h-PROFILE_DATA["espesor_ala"])], dxfattribs={'layer':'PERFILES'})
    msp.add_lwpolyline([(perfil_x0 - (w_flange-w_web)/2, espesor_torta), (perfil_x0+w_web+(w_flange-w_web)/2, espesor_torta), (perfil_x0+w_web+(w_flange-w_web)/2, espesor_torta+PROFILE_DATA["espesor_ala"]), (perfil_x0 - (w_flange-w_web)/2, espesor_torta+PROFILE_DATA["espesor_ala"]), (perfil_x0 - (w_flange-w_web)/2, espesor_torta)], dxfattribs={'layer':'PERFILES'})
    
    # Achurados
    hatch_concrete = msp.add_hatch(color=colors.BLUE)
    hatch_concrete.paths.add_polyline_path([Vec2(off_x, 0), Vec2(off_x+1.5, 0), Vec2(off_x+1.5, espesor_torta), Vec2(off_x, espesor_torta)], is_closed=True)
    hatch_concrete.set_pattern_fill(name='ANSI31', scale=0.1, color=colors.BLUE)
    
    hatch_block = msp.add_hatch(color=colors.RED)
    hatch_block.paths.add_polyline_path([Vec2(off_x, espesor_torta), Vec2(off_x+1.5, espesor_torta), Vec2(off_x+1.5, espesor_torta+BLOCK_DATA["alto"]), Vec2(off_x, espesor_torta+BLOCK_DATA["alto"])], is_closed=True)
    hatch_block.set_pattern_fill(name='AR-CONC', scale=0.1, color=colors.RED)
    
    # Cota manual
    # Línea vertical de cota
    msp.add_line((off_x-0.2, 0), (off_x-0.2, espesor_torta+BLOCK_DATA["alto"]), dxfattribs={'layer':'COTAS'})
    msp.add_line((off_x-0.2, 0), (off_x-0.15, 0), dxfattribs={'layer':'COTAS'})
    msp.add_line((off_x-0.2, espesor_torta+BLOCK_DATA["alto"]), (off_x-0.15, espesor_torta+BLOCK_DATA["alto"]), dxfattribs={'layer':'COTAS'})
    msp.add_text(f"{altura_total*100:.0f} cm", dxfattribs={'layer':'COTAS', 'height':0.12, 'insert':(off_x-0.4, (espesor_torta+BLOCK_DATA["alto"])/2)})
    
    # Detalle viga de borde
    off_x2 = off_x + 2
    msp.add_lwpolyline([(off_x2, 0), (off_x2+viga_b, 0), (off_x2+viga_b, viga_h), (off_x2, viga_h), (off_x2, 0)], dxfattribs={'layer':'EDGE_BEAMS'})
    hatch_viga = msp.add_hatch(color=colors.BLUE)
    hatch_viga.paths.add_polyline_path([Vec2(off_x2, 0), Vec2(off_x2+viga_b, 0), Vec2(off_x2+viga_b, viga_h), Vec2(off_x2, viga_h)], is_closed=True)
    hatch_viga.set_pattern_fill(name='ANSI31', scale=0.1, color=colors.BLUE)
    # Refuerzo
    msp.add_circle((off_x2+0.05, 0.05), 0.01, dxfattribs={'layer':'REFUERZO'})
    msp.add_circle((off_x2+viga_b-0.05, 0.05), 0.01, dxfattribs={'layer':'REFUERZO'})
    msp.add_circle((off_x2+viga_b/2, viga_h-0.05), 0.012, dxfattribs={'layer':'REFUERZO'})
    for y in np.arange(0.1, viga_h, 0.25):
        msp.add_line((off_x2+0.03, y), (off_x2+viga_b-0.03, y), dxfattribs={'layer':'REFUERZO'})
    msp.add_text("2#4", dxfattribs={'layer':'NOTAS', 'height':0.1, 'insert':(off_x2+viga_b/2, 0.1)})
    msp.add_text("1#5", dxfattribs={'layer':'NOTAS', 'height':0.1, 'insert':(off_x2+viga_b/2, viga_h-0.05)})
    msp.add_text(f"Estribos ∅1/4\" @ {s_beam*100:.0f} cm", dxfattribs={'layer':'NOTAS', 'height':0.1, 'insert':(off_x2+viga_b/2, viga_h/2)})
    
    # Notas técnicas
    notas = [
        f"CONCRETO: f'c = {fc_concreto:.1f} MPa ({fc_concreto*1000/9.81:.0f} PSI)",
        f"MALLA: {MESH_DATA['nombre']} ∅{MESH_DATA['diametro']*1000:.0f}mm @ {MESH_DATA['espaciado_largo']*100:.0f}×{MESH_DATA['espaciado_corto']*100:.0f} cm",
        f"PERFIL COLMENA: 80×90×1.5 mm",
        f"NORMA: {norma_sel} – {norma['ref']}",
        f"VIGA BORDE: {ref_beam}, estribos @{s_beam*100:.0f} cm"
    ]
    for i, nota in enumerate(notas):
        msp.add_text(nota, dxfattribs={'layer':'NOTAS', 'height':0.15, 'insert':(0.2, rot_y-0.3 - i*0.3)})
    
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
    doc.add_paragraph(f"Altura bloque: {BLOCK_DATA['alto']*100:.1f} cm")
    doc.add_paragraph(f"Separación perfiles: {perfil_espaciado*100:.0f} cm")
    doc.add_paragraph(f"Concreto: f'c = {fc_concreto:.1f} MPa")
    doc.add_paragraph(f"Número de pisos: {num_pisos}")
    doc.add_paragraph(f"Uso: {uso_placa} – Carga viva: {carga_viva_kn} kN/m²")
    
    doc.add_heading("2. Especificaciones técnicas de materiales", level=1)
    doc.add_paragraph(f"**Bloquelón:** {BLOCK_DATA['largo']*100:.0f}×{BLOCK_DATA['ancho']*100:.0f}×{BLOCK_DATA['alto']*100:.0f} cm, peso unitario {BLOCK_DATA['peso_unitario']:.0f} kg, color arcilla. Pestaña de apoyo: {BLOCK_DATA['pestana']*100:.1f} cm.")
    doc.add_paragraph(f"**Perfil metálico:** altura {PROFILE_DATA['alto_total']*100:.0f} mm, ancho alma {PROFILE_DATA['ancho_alma']*100:.0f} mm, alas {PROFILE_DATA['ancho_ala']*100:.0f} mm, peso {PROFILE_DATA['peso_por_m']:.1f} kg/m.")
    doc.add_paragraph(f"**Malla electrosoldada:** diámetro {MESH_DATA['diametro']*1000:.0f} mm, espaciado {MESH_DATA['espaciado_largo']*100:.0f}×{MESH_DATA['espaciado_corto']*100:.0f} cm, traslapo {MESH_DATA['traslapo']*100:.0f} cm.")
    doc.add_paragraph(f"**Concreto:** resistencia {CONCRETE_DATA['resistencia']} MPa, densidad {CONCRETE_DATA['densidad']} kg/m³.")
    doc.add_paragraph(f"**Peso del sistema instalado:** {SYSTEM_DATA['peso_por_m2']} kg/m² (aprox).")
    
    doc.add_heading("3. Verificaciones normativas", level=1)
    table = doc.add_table(rows=1+len(verificaciones), cols=5)
    table.style = 'Table Grid'
    header = table.rows[0].cells
    header[0].text = "Verificación"
    header[1].text = "Referencia"
    header[2].text = "Requerido"
    header[3].text = "Calculado"
    header[4].text = "Estado"
    for i, v in enumerate(verificaciones):
        row = table.rows[i+1].cells
        row[0].text = v['item']
        row[1].text = v['referencia']
        row[2].text = v['requerido']
        row[3].text = v['calculado']
        estado = "✅ CUMPLE" if v['cumple'] else "❌ NO CUMPLE"
        row[4].text = estado
    
    doc.add_heading("4. Resultados estructurales", level=1)
    doc.add_paragraph(f"Momento último por perfil: Mu = {Mu:.2f} kN·m")
    doc.add_paragraph(f"Deflexión máxima: δ = {delta_calc*1000:.1f} mm (límite {delta_max*1000:.1f} mm)")
    doc.add_paragraph(f"Cortante en apoyo (placa): Vu = {Vu:.2f} kN, Vc = {Vc:.2f} kN")
    doc.add_paragraph(f"Acero de malla: As = {As_malla:.2f} cm²/m (mínimo {As_min*100:.2f} cm²/m)")
    doc.add_paragraph(f"Viga de borde - Momento: Mu = {Mu_beam:.2f} kN·m, As requerido = {As_beam:.2f} cm², As prov = {As_prov_beam:.2f} cm²")
    doc.add_paragraph(f"Viga de borde - Cortante: Vu = {Vu_beam:.2f} kN, Vc = {Vc_beam:.2f} kN")
    doc.add_paragraph(f"Refuerzo viga de borde: {ref_beam}, estribos @{s_beam*100:.0f} cm")
    
    # Diagramas de momento y cortante de la viga
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(x_vals, M_vals, 'b-', linewidth=2)
    ax1.fill_between(x_vals, 0, M_vals, alpha=0.3, color='blue')
    ax1.set_xlabel("Distancia (m)")
    ax1.set_ylabel("Momento (kN·m)")
    ax1.set_title("Diagrama de Momento - Viga Borde")
    ax1.grid(True, alpha=0.3)
    ax2.plot(x_vals, V_vals, 'r-', linewidth=2)
    ax2.fill_between(x_vals, 0, V_vals, alpha=0.3, color='red')
    ax2.set_xlabel("Distancia (m)")
    ax2.set_ylabel("Cortante (kN)")
    ax2.set_title("Diagrama de Cortante - Viga Borde")
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    buf_diag = io.BytesIO()
    plt.savefig(buf_diag, format='png', dpi=150, bbox_inches='tight')
    buf_diag.seek(0)
    doc.add_heading("5. Diagramas de momento y cortante (viga de borde)", level=1)
    doc.add_picture(buf_diag, width=Inches(5.5))
    plt.close()
    
    doc.add_heading("6. Cantidades de materiales", level=1)
    doc.add_paragraph(f"Área de placa: {area_total:.2f} m²")
    doc.add_paragraph(f"Número de bloques: {n_bloques_desp} unidades (incluye desperdicio)")
    doc.add_paragraph(f"Longitud total de perfiles: {longitud_total_perfiles_desp:.1f} m")
    doc.add_paragraph(f"Área de malla: {area_malla:.2f} m² (incluye desperdicio y traslapo)")
    doc.add_paragraph(f"Volumen concreto: {vol_concreto_total_desp:.2f} m³")
    doc.add_paragraph(f"Cemento Portland: {bultos_cemento} bultos de 50 kg")
    
    doc.add_heading("7. Presupuesto", level=1)
    doc.add_paragraph(f"Costo bloques: {moneda} {costo_bloques:,.0f}")
    doc.add_paragraph(f"Costo perfiles: {moneda} {costo_perfiles:,.0f}")
    doc.add_paragraph(f"Costo malla: {moneda} {costo_malla:,.0f}")
    doc.add_paragraph(f"Costo concreto: {moneda} {costo_concreto:,.0f}")
    doc.add_paragraph(f"Mano de obra: {moneda} {costo_mo:,.0f}")
    doc.add_paragraph(f"Herramienta menor: {moneda} {herramienta:,.0f}")
    doc.add_paragraph(f"A.I.U.: {moneda} {aiu:,.0f}")
    doc.add_paragraph(f"IVA s/Utilidad: {moneda} {iva_util:,.0f}")
    doc.add_paragraph(f"**TOTAL PROYECTO: {moneda} {total_proyecto:,.0f}**")
    
    # Anexo gráfico 3D
    fig_3d = create_3d_model(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo,
                              espesor_torta, incluir_vigas, viga_b, viga_h)
    img_bytes = fig_3d.to_image(format="png", width=800, height=500)
    img_buffer = io.BytesIO(img_bytes)
    doc.add_heading("8. Anexo gráfico – Modelo 3D", level=1)
    doc.add_picture(img_buffer, width=Inches(5.5))
    
    return doc

# ─────────────────────────────────────────────
# RESUMEN EJECUTIVO PDF
# ─────────────────────────────────────────────
def generate_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"Resumen Ejecutivo – Placa Fácil", styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Proyecto: {proyecto_nombre}", styles['Normal']))
    story.append(Paragraph(f"Cliente: {proyecto_cliente}", styles['Normal']))
    story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Paragraph(f"Norma: {norma_sel}", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("1. Resultados clave", styles['Heading1']))
    story.append(Paragraph(f"Área de placa: {area_total:.2f} m²", styles['Normal']))
    story.append(Paragraph(f"Volumen concreto: {vol_concreto_total_desp:.2f} m³", styles['Normal']))
    story.append(Paragraph(f"Cemento: {bultos_cemento} bultos", styles['Normal']))
    story.append(Paragraph(f"Costo total: {moneda} {total_proyecto:,.0f}", styles['Normal']))
    story.append(Paragraph(f"Costo por m²: {moneda} {total_proyecto/area_total:,.0f}", styles['Normal']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("2. Verificaciones normativas", styles['Heading1']))
    data = [["Verificación", "Estado"]]
    for v in verificaciones:
        estado = "✔" if v['cumple'] else "✘"
        data.append([v['item'], estado])
    table = Table(data, colWidths=[10*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), rl_colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), rl_colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, rl_colors.black),
    ]))
    story.append(table)
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

# ─────────────────────────────────────────────
# INTERFAZ PRINCIPAL (PESTAÑAS)
# ─────────────────────────────────────────────
tab_res, tab_3d, tab_dxf, tab_mem, tab_qty, tab_apu, tab_resumen = st.tabs([
    "📊 Resultados", "🧊 Modelo 3D", "📏 DXF", "📄 Memoria", "📦 Cantidades", "💰 APU", "📑 Resumen Ejecutivo"
])

with tab_res:
    st.subheader("Resultados del diseño")
    st.write(f"**Área de placa (total):** {area_total:.2f} m²")
    st.write(f"**Número de perfiles:** {n_profiles}")
    st.write(f"**Longitud total de perfiles:** {longitud_total_perfiles_desp:.1f} m")
    st.write(f"**Número de bloques:** {n_bloques_desp} unidades")
    st.write(f"**Volumen de concreto:** {vol_concreto_total_desp:.2f} m³")
    st.write(f"**Área de malla:** {area_malla:.2f} m² (incluye traslapo)")
    st.write(f"**Carga muerta estimada:** {carga_muerta_kgm2:.0f} kg/m²")
    st.write(f"**Cemento necesario:** {bultos_cemento} bultos de 50 kg")
    st.write(f"**Momento último por perfil:** Mu = {Mu:.2f} kN·m")
    st.write(f"**Deflexión máxima:** {delta_calc*1000:.1f} mm (límite {delta_max*1000:.1f} mm)")
    st.write(f"**Cortante en apoyo (placa):** Vu = {Vu:.2f} kN, Vc = {Vc:.2f} kN")
    st.write(f"**Viga de borde - Momento:** Mu = {Mu_beam:.2f} kN·m, As requerido = {As_beam:.2f} cm², As prov = {As_prov_beam:.2f} cm²")
    st.write(f"**Viga de borde - Cortante:** Vu = {Vu_beam:.2f} kN, Vc = {Vc_beam:.2f} kN")
    st.write(f"**Refuerzo viga de borde:** {ref_beam}, estribos @{s_beam*100:.0f} cm")
    
    # Diagramas de momento y cortante de la viga
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(x_vals, M_vals, 'b-', linewidth=2)
    ax1.fill_between(x_vals, 0, M_vals, alpha=0.3, color='blue')
    ax1.set_xlabel("Distancia (m)")
    ax1.set_ylabel("Momento (kN·m)")
    ax1.set_title("Diagrama de Momento - Viga Borde")
    ax1.grid(True, alpha=0.3)
    ax2.plot(x_vals, V_vals, 'r-', linewidth=2)
    ax2.fill_between(x_vals, 0, V_vals, alpha=0.3, color='red')
    ax2.set_xlabel("Distancia (m)")
    ax2.set_ylabel("Cortante (kN)")
    ax2.set_title("Diagrama de Cortante - Viga Borde")
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()
    
    st.markdown("### Verificaciones normativas")
    for v in verificaciones:
        if v['cumple']:
            st.success(f"✅ {v['item']}: {v['calculado']} – {v['obs']}")
        else:
            st.error(f"❌ {v['item']}: {v['calculado']} – {v['obs']}")
        st.caption(f"Referencia: {v['referencia']}")

with tab_3d:
    st.subheader("Modelo 3D de la placa")
    fig_3d = create_3d_model(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo,
                              espesor_torta, incluir_vigas, viga_b, viga_h)
    st.plotly_chart(fig_3d, use_container_width=True)

with tab_dxf:
    st.subheader("Exportar plano DXF profesional")
    st.info("El DXF incluye rótulo ICONTEC, cotas manuales, detalles de corte con achurados, perfil Colmena real, malla con círculos y vigas de borde reforzadas.")
    if st.button("Generar archivo DXF"):
        dxf_data = generate_dxf(Lx, Ly, orientacion, n_profiles, perfil_espaciado, perfil_largo,
                                incluir_vigas, viga_b, viga_h, proyecto_nombre, proyecto_direccion, proyecto_cliente,
                                plano_numero, escala_plano, revisado, aprobado, ref_beam)
        st.download_button("📥 Descargar DXF", data=dxf_data, file_name=f"PlacaFacil_{proyecto_nombre}.dxf", mime="application/dxf")

with tab_mem:
    st.subheader("Memoria de cálculo")
    if st.button("Generar memoria DOCX"):
        doc = generate_memory()
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        st.download_button("📥 Descargar Memoria", data=buf, file_name=f"Memoria_PlacaFacil_{proyecto_nombre}.docx", 
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with tab_qty:
    st.subheader("Cantidades detalladas")
    qty_data = [
        ("Bloques (unidades)", n_bloques, n_bloques_desp, f"{desp_bloques*100:.0f}%"),
        ("Perfiles (m)", longitud_total_perfiles, longitud_total_perfiles_desp, f"{desp_perfiles*100:.0f}%"),
        ("Malla (m²)", area_total, area_malla, f"{desp_malla*100:.0f}% + traslapo"),
        ("Concreto (m³)", vol_concreto_total, vol_concreto_total_desp, f"{desp_concreto*100:.0f}%"),
        ("Cemento (bultos 50 kg)", "-", bultos_cemento, "-"),
    ]
    df_qty = pd.DataFrame(qty_data, columns=["Material", "Neto", "Con desperdicio", "Desperdicio"])
    st.dataframe(df_qty, use_container_width=True, hide_index=True)
    st.write(f"**Volumen de torta de concreto:** {vol_torta:.2f} m³")
    if incluir_vigas:
        st.write(f"**Volumen de vigas de borde:** {vol_vigas:.2f} m³")

with tab_apu:
    st.subheader("Presupuesto APU")
    cost_data = [
        ("Bloques", n_bloques_desp, precio_bloque, costo_bloques),
        ("Perfiles", f"{longitud_total_perfiles_desp:.1f} m", precio_perfil, costo_perfiles),
        ("Malla", f"{area_malla:.2f} m²", precio_malla, costo_malla),
        ("Concreto", f"{vol_concreto_total_desp:.2f} m³", precio_concreto, costo_concreto),
        ("Mano de obra", f"{dias_mo:.1f} días", precio_mo, costo_mo),
        ("Herramienta menor", f"{pct_herramienta*100:.0f}% MO", "", herramienta),
        ("A.I.U.", f"{pct_aui*100:.0f}% CD", "", aiu),
        ("IVA s/Utilidad", f"{iva*100:.0f}% Util", "", iva_util),
        ("TOTAL", "", "", total_proyecto),
    ]
    df_costo = pd.DataFrame(cost_data, columns=["Concepto", "Cantidad", "Precio unitario", "Subtotal"])
    for col in ["Precio unitario", "Subtotal"]:
        df_costo[col] = pd.to_numeric(df_costo[col], errors="ignore")
    st.dataframe(
        df_costo.style.format({"Subtotal": "{:,.0f}", "Precio unitario": "{:,.0f}"}, na_rep=""),
        use_container_width=True,
        hide_index=True
    )
    st.metric(f"💎 Gran Total Proyecto ({moneda})", f"{total_proyecto:,.0f}")
    st.metric(f"💰 Costo por m²", f"{total_proyecto/area_total:,.0f} {moneda}")
    if ahorro > 0:
        st.success(f"💡 Ahorro vs losa maciza: {ahorro:,.0f} {moneda}")
    elif sobrecosto > 0:
        st.warning(f"⚠️ Sobrecosto vs losa maciza: {sobrecosto:,.0f} {moneda}")
    
    st.subheader("Cronograma estimado de actividades")
    st.dataframe(cronograma, use_container_width=True, hide_index=True)
    
    if st.button("Exportar presupuesto a Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_costo.to_excel(writer, sheet_name="Presupuesto", index=False)
            df_qty.to_excel(writer, sheet_name="Cantidades", index=False)
            cronograma.to_excel(writer, sheet_name="Cronograma", index=False)
        output.seek(0)
        st.download_button("📥 Descargar Excel", data=output, file_name=f"Presupuesto_PlacaFacil_{proyecto_nombre}.xlsx", 
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with tab_resumen:
    st.subheader("Resumen Ejecutivo (PDF)")
    st.info("Este resumen incluye datos del proyecto, resultados clave y verificaciones normativas en formato PDF listo para imprimir.")
    if st.button("Generar PDF"):
        pdf_data = generate_pdf()
        st.download_button("📥 Descargar Resumen PDF", data=pdf_data, file_name=f"Resumen_PlacaFacil_{proyecto_nombre}.pdf", mime="application/pdf")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
> **Placa Fácil – Sistema de Vigueta y Bloques**  
> Norma activa: `{norma_sel}`  
> f'c = {fc_concreto:.1f} MPa | Espesor torta = {espesor_torta*100:.1f} cm | Altura total = {altura_total*100:.1f} cm  
> **Referencia:** {norma['ref']}  
> ⚠️ *Las herramientas son de apoyo para el diseño. Verifique siempre con la norma vigente del país.*
""")