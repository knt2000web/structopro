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
import datetime as _dt
try:
    import ifc_export          # BIM export (opcional — requiere ifcopenshell)
    _IFC_AVAILABLE = True
except ImportError:
    ifc_export = None
    _IFC_AVAILABLE = False

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en):
    return en if lang == "English" else es
# ─────────────────────────────────────────────

st.set_page_config(page_title=_t("Zapatas y Suelos", "Footings and Soils"), layout="wide")

# ─────────────────────────────────────────────
# PERSISTENCIA SUPABASE
# ─────────────────────────────────────────────
import requests
import json
import streamlit as st

def get_supabase_rest_info():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return url, key
    except Exception as e:
        return None, None

def guardar_proyecto_supabase(nombre, estado_dict, ref):
    url, key = get_supabase_rest_info()
    if not url or not key:
        try:
            import os
            db_path = f"db_proyectos_{ref.lower()}.json"
            db = {}
            if os.path.exists(db_path):
                with open(db_path, "r", encoding="utf-8") as f: db = json.load(f)
            db[f"[{ref.upper()}] {nombre}"] = {"nombre_proyecto": f"[{ref.upper()}] {nombre}", "estado_json": json.dumps(estado_dict)}
            with open(db_path, "w", encoding="utf-8") as f: json.dump(db, f)
            return True, " Proyecto guardado (Local)"
        except Exception as e:
            return False, f" Error local: {e}"
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    payload = {
        "nombre_proyecto": f"[{ref.upper()}] {nombre}",
        "user_id": st.session_state.get("user_id", "anonimo"),
        "estado_json": json.dumps(estado_dict),
    }
    try:
        endpoint = f"{url}/rest/v1/proyectos?on_conflict=nombre_proyecto"
        res = requests.post(endpoint, headers=headers, json=payload)
        if res.status_code in [200, 201, 204]: return True, " Proyecto en la nube"
        return False, f" Error API: {res.text}"
    except Exception as e: return False, f" Error API: {e}"

def cargar_proyecto_supabase(nombre, ref):
    url, key = get_supabase_rest_info()
    full_name = f"[{ref.upper()}] {nombre}" if not nombre.startswith("[") else nombre
    if not url or not key:
        try:
            import os
            db_path = f"db_proyectos_{ref.lower()}.json"
            if os.path.exists(db_path):
                with open(db_path, "r", encoding="utf-8") as f: db = json.load(f)
                match = db.get(full_name) or db.get(nombre)
                if match:
                    estado = json.loads(match["estado_json"])
                    for k, v in estado.items(): st.session_state[k] = v
                    return True, " Proyecto cargado (Local)"
            return False, " No encontrado"
        except Exception as e: return False, str(e)
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        endpoint = f"{url}/rest/v1/proyectos?nombre_proyecto=eq.{full_name}&select=*"
        res = requests.get(endpoint, headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data:
                estado = json.loads(data[0]["estado_json"])
                for k, v in estado.items(): st.session_state[k] = v
                return True, " Proyecto cargado"
        return False, " No encontrado"
    except Exception as e: return False, str(e)

def listar_proyectos_supabase(ref):
    url, key = get_supabase_rest_info()
    if not url or not key:
        try:
            import os
            db_path = f"db_proyectos_{ref.lower()}.json"
            if os.path.exists(db_path):
                with open(db_path, "r", encoding="utf-8") as f: db = json.load(f)
                return sorted([k.replace(f"[{ref.upper()}] ", "") for k in db.keys()])
            return []
        except: return []
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        endpoint = f"{url}/rest/v1/proyectos?select=nombre_proyecto"
        res = requests.get(endpoint, headers=headers)
        if res.status_code == 200:
            return sorted([i["nombre_proyecto"].replace(f"[{ref.upper()}] ", "") for i in res.json() if f"[{ref.upper()}]" in i.get("nombre_proyecto","")])
        return []
    except: return []

def capturar_estado_module(ref):
    if ref == "zapatas":
        match = ["z_", "cp_", "apu_", "z_tipo_idx", "fc_basico", "fy_basico"]
    else:
        match = ["pi_", "p_", "apu_", "fc_pi"]
    return {k: st.session_state[k] for k in st.session_state if any(k.startswith(m) for m in match)}

# ─────────────────────────────────────────────


# 1. Banner SVG compacto
st.markdown('''
<div style="display:flex; align-items:center; gap:20px; margin-bottom:10px; background:#1e2530; padding:15px; border-radius:10px; border-left:5px solid #ffaa00;">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60" width="80" height="48">
        <path d="M40,10 L60,10 L60,35 L85,35 L90,50 L10,50 L15,35 L40,35 Z" fill="none" stroke="#ffaa00" stroke-width="2"/>
        <line x1="10" y1="50" x2="90" y2="50" stroke="#ffaa00" stroke-width="4"/>
        <line x1="50" y1="10" x2="50" y2="35" stroke="#ffaa00" stroke-width="1" stroke-dasharray="2,2"/>
    </svg>
    <div>
        <h1 style="margin:0; padding:0; font-size:28px;">Cimentaciones: Zapatas y Geotecnia</h1>
        <p style="margin:0; padding:0; color:#aaa; font-size:14px;">Módulo integral NSR-10 / ACI 318 (Diseño, punzonamiento, APU, IFC y Memorias)</p>
    </div>
</div>
''', unsafe_allow_html=True)

# 2. Panel global "Guía Rápida"
with st.expander(" ¿Qué hace este módulo? — Guía rápida", expanded=False):
    st.markdown('''
    ###  Cimentaciones — Verificaciones y Entregas
    
    | Módulo | Qué calcula | Norma |
    |--------|------------|-------|
    | **Zapata Aislada** | Dimensionamiento, cortante, flexión, punzonamiento, IFC | ACI 318 / NSR-10 |
    | **Zapata Medianera** | Viga de amarre, Rint, diagramas Vx/Mx | NSR-10 C.15 |
    | **Geotecnia** | Terzaghi/Meyerhof, Vesic, Boussinesq, asentamiento | NSR-10 H.3 |
    | **Exploración** | Profundidad mínima NSR-10 (10% q₀) | NSR-10 H.3.2.3 |
    
    **Entregables:** Memoria DOCX · Plano DXF ICONTEC · Modelo IFC BIM · Cuadro de mando multi-zapata
    ''')


# ─────────────────────────────────────────────
# PIE DE PÁGINA / DERECHOS RESERVADOS
# ─────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: gray; font-size: 11px;">
    © 2026 Todos los derechos reservados.<br>
    <b>Realizado por:</b><br>
    <br><br>
    <i>⚠ Nota Legal: Esta herramienta es un apoyo profesional. El uso de los resultados es responsabilidad exclusiva del ingeniero diseñador.</i>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONFIGURACIÓN GENERAL Y APU
# ─────────────────────────────────────────────
st.sidebar.header(_t("⚙ Configuración Global", "⚙ Global Settings"))
if "norma_sel" not in st.session_state:
    st.session_state.norma_sel = "NSR-10 (Colombia)"

norma_sel = st.session_state.norma_sel
_PAIS_ISO = {"NSR-10 (Colombia)":"co","ACI 318-25 (EE.UU.)":"us","ACI 318-19 (EE.UU.)":"us","ACI 318-14 (EE.UU.)":"us","NEC-SE-HM (Ecuador)":"ec","E.060 (Perú)":"pe","NTC-EM (México)":"mx","COVENIN 1753-2006 (Venezuela)":"ve","NB 1225001-2020 (Bolivia)":"bo","CIRSOC 201-2025 (Argentina)":"ar"}
_iso = _PAIS_ISO.get(norma_sel, "un")
st.sidebar.markdown(
    f'<div style="background:#1e3a1e;border-radius:6px;padding:8px 12px;margin-bottom:4px;">'
    f'<img src="https://flagpedia.net/data/flags/mini/{_iso}.png" style="vertical-align:middle;margin-right:8px;">'
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
st.sidebar.header(_t(" Conversor Unidades de Suelo", " Soil Units Converter"))
_cu = st.sidebar.selectbox(_t("Unidad a convertir:", "Unit to convert:"), 
    ["kPa → ...", "ton/m² → ...", "kg/cm² → ...", "MPa → ...", "psi → ..."], key="conv_unit_global")
_cv = st.sidebar.number_input(_t("Valor:", "Value:"), value=1.0, step=0.1, key="conv_val_global")
_ck = {
    "kPa → ...": _cv, "ton/m² → ...": _cv * 9.80665,
    "kg/cm² → ...": _cv * 98.0665, "MPa → ...": _cv * 1000.0,
    "psi → ...": _cv * 6.89476,
}.get(_cu, _cv)
st.sidebar.markdown(f"""

    st.sidebar.markdown("---")
    st.sidebar.subheader(" Guardar / Cargar Proyecto")
    nombre_producido = st.session_state.get(f"np_{"zapatas"}", "")
    
    st.sidebar.markdown("**Nuevo Proyecto / Guardar**")
    nombre_proy_guardar = st.sidebar.text_input("Nombre para guardar", value=nombre_producido, key=f"input_guardar_{"zapatas"}")
    
    if st.sidebar.button(" Guardar Proyecto", use_container_width=True, key=f"btn_save_{"zapatas"}"):
        if nombre_proy_guardar:
            ok, msg = guardar_proyecto_supabase(nombre_proy_guardar, capturar_estado_module("zapatas"), "zapatas")
            if ok:
                st.session_state[f"np_{"zapatas"}"] = nombre_proy_guardar
                st.sidebar.success(msg)
            else:
                st.sidebar.error(msg)
        else:
            st.sidebar.warning("Escribe un nombre de proyecto")

    st.sidebar.markdown("**Cargar Proyecto Existente**")
    lista_proyectos = listar_proyectos_supabase("zapatas")
    if lista_proyectos:
        idx_def = lista_proyectos.index(nombre_producido) if nombre_producido in lista_proyectos else 0
        nombre_proy_cargar = st.sidebar.selectbox("Selecciona un proyecto", lista_proyectos, index=idx_def, key=f"sel_load_{"zapatas"}")
        
        def on_cargar_click():
            proy = st.session_state[f"sel_load_{"zapatas"}"]
            if proy:
                ok, msg = cargar_proyecto_supabase(proy, "zapatas")
                st.session_state[f"__msg_cargar_{"zapatas"}"] = (ok, msg)
                if ok: st.session_state[f"np_{"zapatas"}"] = proy

        st.sidebar.button(" Cargar", on_click=on_cargar_click, use_container_width=True, key=f"btn_load_{"zapatas"}")

        if f"__msg_cargar_{"zapatas"}" in st.session_state:
            ok, msg = st.session_state.pop(f"__msg_cargar_{"zapatas"}")
            if ok: st.sidebar.success(msg)
            else: st.sidebar.error(msg)

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
# HELPER GLOBAL: BOUSSINESQ INFLUENCE FACTOR (version escalar y vectorizada)
# ─────────────────────────────────────────────
def I_z_bous(m, n):
    V1 = m**2 + n**2 + 1
    V2 = m**2 * n**2
    term1 = (2*m*n*np.sqrt(V1)) / (V1 + V2) if (V1 + V2) != 0 else 0
    term2 = (V1 + 1) / V1 if V1 != 0 else 0
    angulo = np.arctan2(2*m*n*np.sqrt(V1), (V1 - V2))
    # Manejo de ángulo para cuadrantes
    angulo = np.where(V1 - V2 < 0, angulo + np.pi, angulo)
    return (1 / (4 * np.pi)) * (term1 * term2 + angulo)

# Versión vectorizada para arrays de numpy
def I_z_bous_vec(m_arr, n_arr):
    V1 = m_arr**2 + n_arr**2 + 1
    V2 = m_arr**2 * n_arr**2
    term1 = (2*m_arr*n_arr*np.sqrt(V1)) / (V1 + V2)
    term1 = np.where((V1 + V2) != 0, term1, 0.0)
    term2 = (V1 + 1) / V1
    term2 = np.where(V1 != 0, term2, 0.0)
    angulo = np.arctan2(2*m_arr*n_arr*np.sqrt(V1), (V1 - V2))
    angulo = np.where(V1 - V2 < 0, angulo + np.pi, angulo)
    return (1 / (4 * np.pi)) * (term1 * term2 + angulo)

# ══════════════════════════════════════════════════════════════════════════════
# OPCIÓN B — FUNCIONES AUXILIARES GLOBALES (Fases 1-5)
# ══════════════════════════════════════════════════════════════════════════════

# ─── TABLA MULTINORMA VIGA DE AMARRE ────────────────────────────────────────
_STRAP_NORM = {
    "NSR-10 (Colombia)":          {"nombre": "Viga de amarre",    "art": "C.15.13.3",     "h_factor": 20, "F_ax_pct": 0.025, "idioma": "es"},
    "ACI 318-25 (EE.UU.)":        {"nombre": "Strap beam",        "art": "§13.3.3",       "h_factor": 15, "F_ax_pct": 0.025, "idioma": "en"},
    "ACI 318-19 (EE.UU.)":        {"nombre": "Strap beam",        "art": "§13.3.3",       "h_factor": 15, "F_ax_pct": 0.025, "idioma": "en"},
    "ACI 318-14 (EE.UU.)":        {"nombre": "Strap beam",        "art": "§13.3.3",       "h_factor": 15, "F_ax_pct": 0.025, "idioma": "en"},
    "E.060 (Perú)":               {"nombre": "Viga de conexión",  "art": "§15.13",        "h_factor": 20, "F_ax_pct": 0.025, "idioma": "es"},
    "NTC-EM (México)":            {"nombre": "Viga de liga",      "art": "§5.4",          "h_factor": 20, "F_ax_pct": 0.050, "idioma": "es"},
    "NEC-SE-HM (Ecuador)":        {"nombre": "Viga de amarre",    "art": "§5.5",          "h_factor": 20, "F_ax_pct": 0.025, "idioma": "es"},
    "COVENIN 1753-2006 (Venezuela)":{"nombre": "Viga de conexión","art": "§C.15.13",      "h_factor": 20, "F_ax_pct": 0.025, "idioma": "es"},
    "NB 1225001-2020 (Bolivia)":  {"nombre": "Viga de amarre",    "art": "§15.13",        "h_factor": 20, "F_ax_pct": 0.025, "idioma": "es"},
    "CIRSOC 201-2025 (Argentina)":{"nombre": "Viga de conexión",  "art": "§C.15.13",      "h_factor": 20, "F_ax_pct": 0.025, "idioma": "es"},
}

def _get_strap_norm(norma):
    """Retorna los parámetros normativos de la viga de amarre según la norma activa."""
    for key in _STRAP_NORM:
        if key in norma or norma in key:
            return _STRAP_NORM[key]
    return _STRAP_NORM["NSR-10 (Colombia)"]  # fallback

# ─── F1: DISTRIBUCIÓN DE PRESIONES ─────────────────────────────────────────
def calcular_distribucion_presiones(P, M_B, M_L, B, L):
    """
    Retorna qu_max, qu_min, tipo_dist, e_B, e_L para cualquier tipo de zapata.
    Convención ACI 318 / NSR-10:
      e_B = |M_B / P|  → excentricidad en dirección B (M_B voltea sobre el eje perpendicular a B)
      e_L = |M_L / P|  → excentricidad en dirección L
    """
    A = B * L
    Ix = B * L**3 / 12.0  # inercia respecto al eje paralelo a B (para M_B)
    Iy = L * B**3 / 12.0  # inercia respecto al eje paralelo a L (para M_L)
    # EC-1 CORREGIDO: M_B → e_B,  M_L → e_L  (no cruzado)
    e_B = abs(M_B / P) if P > 0 else 0.0   # excentricidad en dir. B (causada por M_B)
    e_L = abs(M_L / P) if P > 0 else 0.0   # excentricidad en dir. L (causada por M_L)
    # Presiones en las 4 esquinas con signo correcto
    def q_esq(sx, sy):
        # sx multiplica la distancia en dir. B (±B/2), sy en dir. L (±L/2)
        return P/A + (M_B * sx * B/2) / Iy + (M_L * sy * L/2) / Ix
    corners = [q_esq(sx, sy) for sx in [1, -1] for sy in [1, -1]]
    qu_max = max(corners); qu_min = min(corners)
    if qu_min >= 0:
        tipo_dist = "trapezoidal"
    elif e_B > B/6 or e_L > L/6:
        tipo_dist = "triangular"
    else:
        tipo_dist = "con_tension"
    return qu_max, qu_min, tipo_dist, e_B, e_L, Ix, Iy, A

# ─── F2: ÁREA EFECTIVA MEYERHOF ────────────────────────────────────────────
def calcular_area_efectiva_meyerhof(B, L, e_B, e_L):
    """Retorna B', L', A' para el caso qu_min < 0."""
    B_prima = max(0.1, B - 2 * e_B)
    L_prima = max(0.1, L - 2 * e_L)
    A_prima = B_prima * L_prima
    return B_prima, L_prima, A_prima

# ─── F3: MAPA DE CALOR 3D PRESIONES ────────────────────────────────────────
def render_mapa_calor_presiones(B, L, P, M_B, M_L, Ix, Iy, A, qu_max_val, qu_min_val, c1_col_cm, c2_col_cm, titulo="", q_adm=None):
    """Genera go.Figure con surface 3D de qu(x,y)."""
    _nx, _ny = 30, 30
    _xg = np.linspace(-B/2, B/2, _nx)
    _yg = np.linspace(-L/2, L/2, _ny)
    _Xm, _Ym = np.meshgrid(_xg, _yg)
    _Qm = P/A + (M_L * _Xm / Iy) + (M_B * _Ym / Ix)
    _ten = bool(np.any(_Qm < 0))
    _Qp = np.where(_Qm < 0, 0, _Qm)
    fig = go.Figure()
    _rango = max(float(np.max(_Qp)) - float(np.min(_Qp[_Qp > 0]) if np.any(_Qp > 0) else 0), 1.0)
    _cmin  = max(0.0, float(np.max(_Qp)) - _rango * 4)
    if _rango < 5.0:
        _cmin = 0.0

    fig.add_trace(go.Surface(x=_xg, y=_yg, z=_Qp, colorscale="RdYlGn_r",
                             cmin=_cmin, cmax=float(np.max(_Qp))*1.02,
                             colorbar=dict(title=dict(text="qu [kPa]", font=dict(color="white")), tickfont=dict(color="white")),
                             opacity=0.9, name="qu(x,y)"))
    
    rango_real = float(np.max(_Qp)) - float(np.min(_Qp[_Qp > 0])) if np.any(_Qp > 0) else 0
    if rango_real > 1.0:
        _imax = np.unravel_index(np.argmax(_Qm), _Qm.shape)
        fig.add_trace(go.Scatter3d(x=[_xg[_imax[1]]], y=[_yg[_imax[0]]], z=[float(_Qm[_imax])],
                                   mode="markers+text", marker=dict(color="#ff4444", size=8, symbol="diamond"),
                                   text=[f"qu_max={qu_max_val:.1f}kPa"], textfont=dict(color="white"), name=f"qu_max"))
    _c1m = c1_col_cm/100; _c2m = c2_col_cm/100
    _cx = [-_c1m/2, _c1m/2, _c1m/2, -_c1m/2, -_c1m/2]
    _cy = [-_c2m/2, -_c2m/2, _c2m/2, _c2m/2, -_c2m/2]
    _i_col = np.argmin(np.abs(_xg - 0))
    _j_col = np.argmin(np.abs(_yg - 0))
    _z_col = [float(_Qp[_j_col, _i_col]) * 1.005] * 5
    fig.add_trace(go.Scatter3d(x=_cx, y=_cy, z=_z_col, mode="lines",
                               line=dict(color="white", width=4), name="Columna"))
    if q_adm is not None and q_adm > 0:
        _z_adm = np.full(_Xm.shape, q_adm)
        fig.add_trace(go.Surface(x=_xg, y=_yg, z=_z_adm, colorscale=[[0, 'blue'], [1, 'blue']],
                                 opacity=0.35, showscale=False, name="q_adm Límite"))
    _titulo = titulo or (f"qu(x,y) | qu_max={qu_max_val:.1f} | qu_min={qu_min_val:.1f} kPa" +
                         (" | ⚠ LEVANTAMIENTO" if _ten else " |  Compresión total"))
    fig.update_layout(scene=dict(xaxis_title="B[m]", yaxis_title="L[m]", zaxis_title="qu[kPa]",
                                 bgcolor="#0f1117",
                                 xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
                                 zaxis=dict(gridcolor="#333"),
                                 camera=dict(eye=dict(x=1.8, y=1.8, z=1.6))),
                      paper_bgcolor="#0f1117", font=dict(color="white"),
                      margin=dict(l=0, r=0, b=0, t=40), height=480,
                      title=dict(text=_titulo, font=dict(color="#ffdd44" if _ten else "#44ff88")),
                      showlegend=True)
    return fig, _ten

# ─── F4: CÁLCULO VIGA DE AMARRE ────────────────────────────────────────────
def calcular_viga_amarre(R_strap_kN, L_libre_m, b_viga_cm, h_viga_cm, gamma_c=24.0):
    """
    Genera el diagrama de fuerzas, V(x) y M(x) de la viga de amarre.
    R_strap_kN : reacción que la viga recibe de la zapata exterior (kN)
    Retorna    : x_arr, V_arr, M_arr, M_max, V_max, pp_kNm, R_int, advertencia_Rint
    Nota       : gamma_c no incluye el peso del suelo sobre la viga. Si la viga
                 va enterrada con relleno encima, incrementar gamma_c_efectivo fuera de
                 esta función antes de llamarla.
    """
    pp_viga = gamma_c * (b_viga_cm/100) * (h_viga_cm/100)  # kN/m (solo hormigón)
    pp_tot  = pp_viga * L_libre_m
    R_int   = R_strap_kN - pp_tot  # reacción de la zapata interior
    # EC-2 CORREGIDO: bandera de advertencia si R_int < 0 (levantamiento potencial)
    _adv_Rint = R_int < 0
    n = 200
    x_arr = np.linspace(0, L_libre_m, n)
    V_arr = R_strap_kN - pp_viga * x_arr          # V(x)
    M_arr = R_strap_kN * x_arr - pp_viga * x_arr**2 / 2.0  # M(x)
    M_max = float(np.max(np.abs(M_arr)))
    V_max = float(np.max(np.abs(V_arr)))
    return x_arr, V_arr, M_arr, M_max, V_max, pp_viga, R_int, _adv_Rint

# ─── F5: DISEÑO VIGA DE AMARRE ─────────────────────────────────────────────
def disenar_viga_amarre(M_max_kNm, V_max_kN, F_ax_kN, b_v_cm, h_v_cm,
                        fc_MPa, fy_MPa, L_libre_m, P_total_kN, norma,
                        recub_v=4.0, bar_long="N.5 (5/8\")", bar_est="N.3 (3/8\")",
                        rebar_dict=None):
    """
    Diseña la viga de amarre: As_sup, As_inf, estribos, verificación axial.
    Retorna dict con todos los resultados.
    """
    if rebar_dict is None:
        rebar_dict = {"N.3 (3/8\")": {"area": 0.71, "db": 9.5},
                      "N.4 (1/2\")": {"area": 1.29, "db": 12.7},
                      "N.5 (5/8\")": {"area": 1.99, "db": 15.9},
                      "N.6 (3/4\")": {"area": 2.84, "db": 19.1}}
    sn = _get_strap_norm(norma)
    phi_f = 0.90; phi_v_s = 0.75
    if "E.060" in norma: phi_v_s = 0.85

    db_long = rebar_dict.get(bar_long, {"db": 15.9})["db"]
    db_est  = rebar_dict.get(bar_est, {"db": 9.5})["db"]
    As_long_unit = rebar_dict.get(bar_long, {"area": 1.99})["area"]
    As_est_unit  = rebar_dict.get(bar_est, {"area": 0.71})["area"]

    d_v = h_v_cm - recub_v - db_est/10.0 - db_long/20.0   # peralte efectivo cm
    # EC-3 CORREGIDO: d_v ≤ 0 es error de diseño, no se silencia con fallback
    if d_v <= 0:
        # Retornamos dict de error que render_medianera() detecta y muestra con st.error
        return {
            "_error": True,
            "_msg": (f" **Peralte efectivo d_v = {d_v:.1f} cm ≤ 0** con h={h_v_cm:.0f} cm, "
                     f"recub={recub_v:.1f} cm, Ø_est={db_est:.1f}mm, Ø_long={db_long:.1f}mm. "
                     "Aumente h o reduzca el recubrimiento."),
        }

    # Dimensión mínima normativa
    h_min_cm = L_libre_m * 100 / sn["h_factor"]
    ok_hmin = h_v_cm >= h_min_cm

    # Diseño flexión — As sup (momento positivo máximo) y As inf (mínimo)
    def _As_flexion(Mu_kNm, b_cm, d_cm):
        if Mu_kNm <= 0: return 0.0, True
        Rn = (Mu_kNm * 1e6) / (phi_f * (b_cm*10) * (d_cm*10)**2)  # MPa
        disc = 1 - 2*Rn / (0.85 * fc_MPa)
        disc = max(disc, 0.0)
        rho = (0.85 * fc_MPa / fy_MPa) * (1 - math.sqrt(disc))
        rho_use = max(rho, 0.0018)
        As = rho_use * (b_cm*10) * (d_cm*10) / 100.0  # cm²
        return As, disc > 0

    As_sup, ok_sup = _As_flexion(M_max_kNm, b_v_cm, d_v)
    As_inf_min = max(0.0018 * (b_v_cm*10) * (d_v*10) / 100.0,
                     (0.25 * math.sqrt(fc_MPa) / fy_MPa) * (b_v_cm*10) * (d_v*10) / 100.0)
    As_inf = As_inf_min

    # Acero mínimo 4 barras en esquinas (NSR-10 C.15.13)
    n_long_min = 4
    As_min_4barras = n_long_min * As_long_unit
    As_sup = max(As_sup, As_min_4barras)
    As_inf = max(As_inf, As_min_4barras)
    n_sup = math.ceil(As_sup / As_long_unit)
    n_inf = math.ceil(As_inf / As_long_unit)

    # Fuerza axial sísmica
    F_ax_req = sn["F_ax_pct"] * P_total_kN
    ok_Fax = F_ax_kN <= F_ax_req  # la viga debe soportar en tensión/compresión

    # Diseño cortante
    phi_Vc = phi_v_s * 0.17 * math.sqrt(fc_MPa) * (b_v_cm*10) * (d_v*10) / 1000.0  # kN
    Vs_req = max(0, V_max_kN / phi_v_s - phi_Vc / phi_v_s)
    if Vs_req > 0:
        # s = Av * fy * d / Vs (2 ramas)
        s_est_cm = (2 * As_est_unit * fy_MPa * (d_v*10)) / (Vs_req * 1000.0 / 10.0)
        s_est_cm = min(s_est_cm, d_v/2, 30.0)  # máx. d/2 y 30 cm
    else:
        s_est_cm = min(d_v/2, 30.0)
    s_est_cm = max(s_est_cm, 5.0)
    ok_cort = phi_Vc >= V_max_kN

    # Longitud de zona crítica (estribos más cerrados)
    L_crit_cm = max(2 * h_v_cm, 45.0)
    s_crit_cm = min(s_est_cm, h_v_cm/4, 6*(db_long/10.0), 15.0)

    phi_Mn_sup = phi_f * (As_sup * fy_MPa * (d_v*10) * (1 - (As_sup*fy_MPa)/(1.7*fc_MPa*(b_v_cm*10))) ) / 1e6  # kN·m
    ok_flex = phi_Mn_sup >= M_max_kNm

    return {
        "sn": sn, "d_v": d_v, "h_min_cm": h_min_cm, "ok_hmin": ok_hmin,
        "As_sup": As_sup, "n_sup": n_sup, "As_inf": As_inf, "n_inf": n_inf,
        "phi_Vc": phi_Vc, "Vs_req": Vs_req, "s_est_cm": s_est_cm,
        "s_crit_cm": s_crit_cm, "L_crit_cm": L_crit_cm,
        "ok_cort": ok_cort, "ok_flex": ok_flex, "ok_Fax": ok_Fax,
        "F_ax_req": F_ax_req, "phi_Mn_sup": phi_Mn_sup,
        "bar_long": bar_long, "bar_est": bar_est,
        "As_long_unit": As_long_unit, "As_est_unit": As_est_unit,
        "db_long": db_long, "db_est": db_est,
    }

# ─── F6: DIAGRAMA V(x) / M(x) PLOTLY ───────────────────────────────────────
def render_diagrama_VM(x_arr, V_arr, M_arr, R_strap, R_int, pp_viga, L_libre):
    """Genera figura Plotly con dos paneles: V(x) arriba y M(x) abajo."""
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("Diagrama de Cortante V(x) [kN]",
                                        "Diagrama de Momento M(x) [kN·m]"),
                        vertical_spacing=0.1)
    # V(x)
    fig.add_trace(go.Scatter(x=x_arr, y=V_arr, fill='tozeroy', fillcolor='rgba(0,200,255,0.15)',
                             line=dict(color='#00c8ff', width=2), name="V(x)"), row=1, col=1)
    fig.add_hline(y=0, line_color="white", line_width=0.5, row=1, col=1)
    # M(x)
    fig.add_trace(go.Scatter(x=x_arr, y=M_arr, fill='tozeroy', fillcolor='rgba(255,165,0,0.15)',
                             line=dict(color='#ffa500', width=2), name="M(x)"), row=2, col=1)
    fig.add_hline(y=0, line_color="white", line_width=0.5, row=2, col=1)
    # Anotaciones de reacciones
    fig.add_vline(x=0, line_color="#7fff00", line_width=1.5, line_dash="dot")
    fig.add_vline(x=L_libre, line_color="#ff6b6b", line_width=1.5, line_dash="dot")
    # FI-7 CORREGIDO: anotaciones con xref/yref en paper para posición fija y visible
    fig.add_annotation(x=0.02, y=0.95, xref="paper", yref="paper",
                       text=f"↑ R_ext = {R_strap:.1f} kN",
                       showarrow=False, font=dict(color="#7fff00", size=11),
                       bgcolor="rgba(0,0,0,0.5)", align="left")
    _Rint_lbl = f"↑ R_int = {R_int:.1f} kN" if R_int >= 0 else f"⚠ R_int = {R_int:.1f} kN (levant.)"
    _Rint_col = "#ff6b6b" if R_int >= 0 else "#ffaa00"
    fig.add_annotation(x=0.98, y=0.95, xref="paper", yref="paper",
                       text=_Rint_lbl,
                       showarrow=False, font=dict(color=_Rint_col, size=11),
                       bgcolor="rgba(0,0,0,0.5)", align="right")
    fig.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                      font=dict(color="white"), showlegend=False,
                      margin=dict(l=20, r=20, t=40, b=20), height=400,
                      xaxis2=dict(title="x [m]"),
                      yaxis=dict(gridcolor="#222"), yaxis2=dict(gridcolor="#222"))
    return fig

# ─── F7: VISTA 3D PLOTLY — SISTEMA COMPLETO ────────────────────────────────
def render_3d_sistema(zap_ext, zap_int, viga_d, dis_d, fc_col=None):
    """
    zap_ext: dict con B, L, H, x0_col, y0_col (centro zapata exterior en coords globales)
    zap_int: dict igual para zapata interior
    viga_d:  dict con b, h, L_libre, x0, y0
    dis_d:   resultado de disenar_viga_amarre()
    """
    fig = go.Figure()
    # Helper: bloque cúbico translúcido
    def _box(ox, oy, oz, w, d, h, color, name, opacity=0.25):
        x = [ox, ox+w, ox+w, ox, ox, ox+w, ox+w, ox]
        y = [oy, oy, oy+d, oy+d, oy, oy, oy+d, oy+d]
        z = [oz]*4 + [oz+h]*4
        fig.add_trace(go.Mesh3d(x=x, y=y, z=z, alphahull=0, opacity=opacity,
                                color=color, name=name, showlegend=True))
    # Zapata exterior
    zE = zap_ext
    _box(zE["x0"]-zE["B"]/2, zE["y0"]-zE["L"]/2, 0,
         zE["B"], zE["L"], zE["H"]/100, "steelblue", "Zapata Exterior")
    # Zapata interior
    zI = zap_int
    _box(zI["x0"]-zI["B"]/2, zI["y0"]-zI["L"]/2, 0,
         zI["B"], zI["L"], zI["H"]/100, "#4CAF50", "Zapata Interior")
    # Columnas
    Hz_E = zE["H"]/100; Hz_I = zI["H"]/100
    _box(zE["x0"]-zE.get("c1",40)/200, zE["y0"]-zE.get("c2",40)/200, Hz_E,
         zE.get("c1",40)/100, zE.get("c2",40)/100, 1.0, "slategray", "Col. Exterior", opacity=0.6)
    _box(zI["x0"]-zI.get("c1",40)/200, zI["y0"]-zI.get("c2",40)/200, Hz_I,
         zI.get("c1",40)/100, zI.get("c2",40)/100, 1.0, "#888", "Col. Interior", opacity=0.6)
    # Viga de amarre — EM-3 CORREGIDO: ancla en la superficie de la zapata, no en borde de columna
    # La viga de amarre está empotrada en cada zapata, no en las columnas.
    # Geométricamente va de x0_zapata_ext hasta x1_zapata_int.
    vg = viga_d
    _hv = vg["h"]/100; _bv = vg["b"]/100
    _xv0 = zE["x0"] + zE["B"]/2          # borde derecho de la zapata exterior (ancla)
    _xv1 = zI["x0"] - zI["B"]/2          # borde izquierdo de la zapata interior (ancla)
    _yv0 = -_bv/2
    _box(_xv0, _yv0, max(Hz_E, Hz_I), max(_xv1-_xv0, 0.01), _bv, _hv, "#FF9800", "Viga de Amarre", opacity=0.75)
    # Acero longitudinal de la viga (líneas)
    _rec = vg.get("recub", 4)/100
    _n_sup = dis_d["n_sup"]; _n_inf = dis_d["n_inf"]
    _db_l = dis_d["db_long"]/1000
    _z_base = max(Hz_E, Hz_I) + _rec + _db_l/2
    _z_sup  = max(Hz_E, Hz_I) + _hv - _rec - _db_l/2
    for _i, _ny in enumerate(np.linspace(-_bv/2+_rec+_db_l, _bv/2-_rec-_db_l, max(_n_sup,2))):
        _show = _i == 0
        fig.add_trace(go.Scatter3d(x=[_xv0, _xv1], y=[_ny, _ny], z=[_z_sup, _z_sup],
                                   mode="lines", line=dict(color="#ff6b35", width=4),
                                   name="Acero Sup. Viga" if _show else None, showlegend=_show, legendgroup="Asup"))
        fig.add_trace(go.Scatter3d(x=[_xv0, _xv1], y=[_ny, _ny], z=[_z_base, _z_base],
                                   mode="lines", line=dict(color="#ffd54f", width=4),
                                   name="Acero Inf. Viga" if _show else None, showlegend=_show, legendgroup="Ainf"))
    # Estribos (marcos rectangulares cada s_est_cm)
    _s_est = dis_d["s_est_cm"]/100
    _xv_range = np.arange(_xv0 + _s_est, _xv1, _s_est)
    _is_first_est = True
    for _xe in _xv_range:
        _est_x = [_xe]*5; _est_y = [-_bv/2+_rec, _bv/2-_rec, _bv/2-_rec, -_bv/2+_rec, -_bv/2+_rec]
        _est_z = [_z_base, _z_base, _z_sup, _z_sup, _z_base]
        fig.add_trace(go.Scatter3d(x=_est_x, y=_est_y, z=_est_z,
                                   mode="lines", line=dict(color="#aaa", width=2),
                                   name="Estribos Viga" if _is_first_est else None,
                                   showlegend=_is_first_est, legendgroup="est"))
        _is_first_est = False

    # FI-3: go.Surface de qu(x,y) bajo cada zapata (mapa de presiones integrado en 3D)
    def _add_pressure_surface(zap, label, colorscale="RdYlGn_r"):
        _cx = zap["x0"]; _cy = zap["y0"]
        _B = zap["B"];   _L = zap["L"]
        _nx, _ny_g = 20, 20
        _xg = np.linspace(_cx - _B/2, _cx + _B/2, _nx)
        _yg = np.linspace(_cy - _L/2, _cy + _L/2, _ny_g)
        _Xm, _Ym = np.meshgrid(_xg, _yg)
        # Distribución trapezoidal lineal entre qu_max (borde lindero) y qu_min/2 (borde opuesto)
        _qu_max = zap.get("qu_max", 150.0)
        _qu_min = max(zap.get("qu_min", 80.0), 0.0)
        # Gradiente en X desde qu_max hasta qu_min
        _Qm = _qu_max + (_qu_min - _qu_max) * (_Xm - (_cx - _B/2)) / _B
        _Qm = np.clip(_Qm, 0, None)
        # Escalar a -0.05m para que quede justo bajo la zapata (visual)
        _Z_surf = np.full_like(_Qm, -0.05)
        # Codificar qu como colormap
        fig.add_trace(go.Surface(
            x=_xg, y=_yg, z=_Z_surf,
            surfacecolor=_Qm, colorscale=colorscale,
            cmin=0, cmax=float(np.max(_Qm))*1.1,
            showscale=False, opacity=0.85,
            name=f"Presiones {label}", showlegend=True,
            hovertemplate=f"<b>{label}</b><br>qu = %{{customdata:.1f}} kPa<extra></extra>",
            customdata=_Qm,
        ))
    # Añadir superficie de presiones para cada zapata con sus qu del session_state
    _qu_data_e = fc_col or {}  # se pasa como fc_col cuando hay datos
    _zE_qu = {**zE, "qu_max": zE.get("qu_max", 150.0), "qu_min": zE.get("qu_min", 60.0)}
    _zI_qu = {**zI, "qu_max": zI.get("qu_max", 120.0), "qu_min": zI.get("qu_min", 60.0)}
    _add_pressure_surface(_zE_qu, "Z.Ext")
    _add_pressure_surface(_zI_qu, "Z.Int")

    fig.update_layout(scene=dict(aspectmode='data',
                                 xaxis_title='X [m]', yaxis_title='Y [m]', zaxis_title='Z [m]',
                                 bgcolor='#0f1117',
                                 xaxis=dict(showgrid=True, gridcolor='#333'),
                                 yaxis=dict(showgrid=True, gridcolor='#333'),
                                 zaxis=dict(showgrid=True, gridcolor='#333')),
                      margin=dict(l=0, r=0, b=0, t=40), height=600,
                      paper_bgcolor='#0f1117', font=dict(color='white'),
                      title=dict(text="Sistema Zapata Medianera + Viga de Amarre — Vista 3D",
                                 font=dict(color='white')),
                      showlegend=True, dragmode='turntable')
    return fig

# ─── F8: DXF — SISTEMA COMPLETO ────────────────────────────────────────────
def generar_dxf_sistema(zap_ext_d, zap_int_d, viga_d, dis_d, norma, fc, fy):
    """Genera doc ezdxf con planta general, corte long. y trans. de viga de amarre."""
    import datetime as _dt2
    sn = _get_strap_norm(norma)
    doc = ezdxf.new('R2010')
    doc.units = ezdxf.units.CM
    ESCALA = 25; TH = 0.06*ESCALA; TH_T = 0.10*ESCALA
    doc.header['$DIMSCALE'] = ESCALA
    doc.header['$TEXTSIZE'] = TH
    msp = doc.modelspace()
    # Layers
    for _ln, _lc in [('ZAPATA_EXT',4),('ZAPATA_INT',3),('VIGA_STRAP',1),
                     ('ACERO_LONG',2),('ACERO_EST',7),('COTAS',8),('TEXTO',2),('ROTULO',6)]:
        if _ln not in doc.layers: doc.layers.add(_ln, color=_lc)
    def _rect(ox, oy, w, h, lay):
        msp.add_lwpolyline([(ox,oy),(ox+w,oy),(ox+w,oy+h),(ox,oy+h)], close=True, dxfattribs={'layer':lay})
    def _txt(x, y, txt, lay, h=None):
        msp.add_text(txt, dxfattribs={'layer':lay,'height':h or TH,'insert':(x,y)})
    def _dim_h(x1,x2,yd,txt):
        msp.add_line((x1,yd),(x2,yd),dxfattribs={'layer':'COTAS'})
        msp.add_line((x1,yd-TH),(x1,yd+TH),dxfattribs={'layer':'COTAS'})
        msp.add_line((x2,yd-TH),(x2,yd+TH),dxfattribs={'layer':'COTAS'})
        _txt((x1+x2)/2, yd+TH*0.5, txt, 'COTAS')
    # — PLANTA GENERAL (origen 0,0) —
    Be_cm = zap_ext_d["B_cm"]; Le_cm = zap_ext_d["L_cm"]
    Bi_cm = zap_int_d["B_cm"]; Li_cm = zap_int_d["L_cm"]
    sep_cm = viga_d["L_libre_m"]*100
    # Zapata exterior en x=0
    _rect(0, -Le_cm/2, Be_cm, Le_cm, 'ZAPATA_EXT')
    _txt(Be_cm/2, Le_cm/2+TH, f"Z.EXT {Be_cm:.0f}x{Le_cm:.0f}cm", 'TEXTO', TH_T)
    # Zapata interior en x = Be_cm + sep_cm
    ox_int = Be_cm + sep_cm
    _rect(ox_int, -Li_cm/2, Bi_cm, Li_cm, 'ZAPATA_INT')
    _txt(ox_int+Bi_cm/2, Li_cm/2+TH, f"Z.INT {Bi_cm:.0f}x{Li_cm:.0f}cm", 'TEXTO', TH_T)
    # Viga de amarre
    bv_cm = viga_d["b_cm"]
    _rect(Be_cm, -bv_cm/2, sep_cm, bv_cm, 'VIGA_STRAP')
    _txt(Be_cm+sep_cm/2, bv_cm/2+TH, f"{sn['nombre']} {viga_d['b_cm']:.0f}x{viga_d['h_cm']:.0f}cm", 'TEXTO', TH)
    # Cotas planta
    _dim_h(0, Be_cm, -Le_cm/2-TH*5, f"B_ext={Be_cm:.0f}cm")
    _dim_h(ox_int, ox_int+Bi_cm, -Li_cm/2-TH*5, f"B_int={Bi_cm:.0f}cm")
    _dim_h(Be_cm, ox_int, -max(Le_cm,Li_cm)/2-TH*10, f"L_libre={sep_cm:.0f}cm")
    _txt((Be_cm+sep_cm+Bi_cm)/2, max(Le_cm,Li_cm)/2+TH_T*3,
         f"PLANTA — {sn['nombre'].upper()}  ESC 1:{ESCALA}", 'TEXTO', TH_T)
    # — CORTE LONGITUDINAL (origen 0, -Le_cm/2-TH*20) —
    oy_el = -max(Le_cm,Li_cm)/2 - TH*25
    hv_cm = viga_d["h_cm"]; hz_ext = zap_ext_d["H_cm"]; hz_int = zap_int_d["H_cm"]
    _rect(0, oy_el, Be_cm, hz_ext, 'ZAPATA_EXT')
    _rect(ox_int, oy_el, Bi_cm, hz_int, 'ZAPATA_INT')
    _rect(Be_cm, oy_el+max(hz_ext,hz_int), sep_cm, hv_cm, 'VIGA_STRAP')
    # Barras sup e inf de la viga
    rec_v = viga_d.get("recub_cm", 4)
    y_sup = oy_el+max(hz_ext,hz_int)+hv_cm - rec_v
    y_inf = oy_el+max(hz_ext,hz_int) + rec_v
    msp.add_line((Be_cm+rec_v, y_sup),(Be_cm+sep_cm-rec_v, y_sup), dxfattribs={'layer':'ACERO_LONG'})
    msp.add_line((Be_cm+rec_v, y_inf),(Be_cm+sep_cm-rec_v, y_inf), dxfattribs={'layer':'ACERO_LONG'})
    _txt(Be_cm+sep_cm+TH, y_sup, f"{dis_d['n_sup']}x{dis_d['bar_long']} (sup)", 'TEXTO', TH*0.8)
    _txt(Be_cm+sep_cm+TH, y_inf, f"{dis_d['n_inf']}x{dis_d['bar_long']} (inf)", 'TEXTO', TH*0.8)
    # Estribos en corte longitudinal (líneas verticales)
    _s_dxf = dis_d['s_est_cm']
    for _xe in np.arange(Be_cm+_s_dxf, Be_cm+sep_cm, _s_dxf):
        msp.add_line((_xe, y_inf), (_xe, y_sup), dxfattribs={'layer':'ACERO_EST'})
    _txt(Be_cm+sep_cm/2, oy_el+max(hz_ext,hz_int)+hv_cm+TH_T*2,
         f"CORTE A-A (Longitudinal) ESC 1:{ESCALA}", 'TEXTO', TH_T)
    # — CORTE TRANSVERSAL (a la derecha del corte long.) —
    ox_tr = Be_cm*2 + sep_cm + Bi_cm + 60
    oy_tr = oy_el+max(hz_ext,hz_int)
    _rect(ox_tr, oy_tr, bv_cm, hv_cm, 'VIGA_STRAP')
    # EM-5 CORREGIDO: barras dinámicas según n_sup / n_inf (no siempre 4)
    _r_bar = dis_d['db_long'] / 50.0
    _n_sup_dxf = dis_d['n_sup']
    _n_inf_dxf = dis_d['n_inf']
    # Barras superiores distribuidas horizontalmente en la sección
    _rec_est = rec_v + dis_d.get('db_est', 9.5)/20.0
    for _ki in range(_n_sup_dxf):
        _bx_s = ox_tr + _rec_est + (_ki + 0.5) * (bv_cm - 2*_rec_est) / _n_sup_dxf
        msp.add_circle((_bx_s, oy_tr+hv_cm-_rec_est), _r_bar, dxfattribs={'layer':'ACERO_LONG'})
    # Barras inferiores
    for _ki in range(_n_inf_dxf):
        _bx_i = ox_tr + _rec_est + (_ki + 0.5) * (bv_cm - 2*_rec_est) / _n_inf_dxf
        msp.add_circle((_bx_i, oy_tr+_rec_est), _r_bar, dxfattribs={'layer':'ACERO_LONG'})
    # Estribo cerrado
    _er = rec_v + dis_d['db_est']/20
    msp.add_lwpolyline([(ox_tr+_er, oy_tr+_er),(ox_tr+bv_cm-_er, oy_tr+_er),
                        (ox_tr+bv_cm-_er, oy_tr+hv_cm-_er),(ox_tr+_er, oy_tr+hv_cm-_er)],
                       close=True, dxfattribs={'layer':'ACERO_EST'})
    _txt(ox_tr+bv_cm/2, oy_tr+hv_cm+TH_T*2, "CORTE B-B (Trans.)", 'TEXTO', TH_T)
    _txt(ox_tr, oy_tr-TH*3, f"Est. {dis_d['bar_est']} @ {dis_d['s_est_cm']:.0f}/{dis_d['s_crit_cm']:.0f}cm", 'TEXTO', TH*0.8)
    # — RÓTULO —
    rot_w = 200; rot_h = 60; rot_x = ox_int*2 + 80; rot_y = oy_el - 80
    _rect(rot_x, rot_y, rot_w, rot_h, 'ROTULO')
    msp.add_line((rot_x+60, rot_y),(rot_x+60, rot_y+rot_h), dxfattribs={'layer':'ROTULO'})
    _filas = [
        ("PROYECTO", f"Zapata Medianera + {sn['nombre']}"),
        ("NORMA", f"{norma}  Art. {sn['art']}"),
        ("DISEÑÓ", "StructuroPro Zapatas"),
        ("f'c", f"{fc} MPa  |  fy = {fy} MPa"),
        ("VIGA", f"{viga_d['b_cm']:.0f}x{viga_d['h_cm']:.0f} cm — {dis_d['n_sup']}x{dis_d['bar_long']} + Est.@{dis_d['s_est_cm']:.0f}cm"),
        ("ESCALA", f"1:{ESCALA}"),
        ("FECHA", _dt2.date.today().strftime('%d/%m/%Y')),
        ("REV", "R0"),
    ]
    row_h = rot_h / len(_filas)
    for _i, (_campo, _val) in enumerate(_filas):
        _yrow = rot_y + rot_h - (_i+1)*row_h
        if _i > 0: msp.add_line((rot_x, _yrow+row_h),(rot_x+rot_w, _yrow+row_h), dxfattribs={'layer':'ROTULO'})
        _txt(rot_x+2, _yrow+row_h*0.3, _campo, 'ROTULO', TH*0.7)
        _txt(rot_x+62, _yrow+row_h*0.3, _val, 'ROTULO', TH)

    # ── RÓTULO PERIMETRAL ICONTEC (doble línea de borde de hoja) ──────────────
    _px_min = min(-50, ox_el - 50)
    _py_min = min(rot_y - 20, oy_el - 50)
    _px_max = rot_x + rot_w + 30
    _py_max = max(oy_el + zap_ext_d['H_zap'] + zap_ext_d['D_zap'] + 50,
                  oy_tr + viga_d['h_cm'] + 50,
                  rot_y + rot_h + 50)
    _rect(_px_min,   _py_min,   _px_max - _px_min,   _py_max - _py_min,   'ROTULO')
    _rect(_px_min+1, _py_min+1, _px_max - _px_min-2, _py_max - _py_min-2, 'ROTULO')

    return doc

# ─── F9: DOCX AMPLIADO ─────────────────────────────────────────────────────
def generar_docx_ampliado(zap_ext_d, zap_int_d, viga_d, dis_d, dist_d, norma, fig_vm=None):
    """Genera Document() de python-docx con la sección de viga de amarre."""
    from docx import Document as _Doc
    from docx.shared import Inches as _In, Pt as _Pt
    sn = _get_strap_norm(norma)
    doc = _Doc()
    doc.add_heading(f"MEMORIA — {sn['nombre'].upper()} ({norma})", 0)
    doc.add_paragraph(f"Norma: {norma}  |  Artículo: {sn['art']}")
    doc.add_paragraph(f"Fecha: {_dt.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    doc.add_heading("1. DATOS DE ENTRADA", level=1)
    doc.add_paragraph(f"  Zapata Exterior: B={zap_ext_d['B_cm']:.0f} cm × L={zap_ext_d['L_cm']:.0f} cm × H={zap_ext_d['H_cm']:.0f} cm")
    doc.add_paragraph(f"  Zapata Interior:  B={zap_int_d['B_cm']:.0f} cm × L={zap_int_d['L_cm']:.0f} cm × H={zap_int_d['H_cm']:.0f} cm")
    doc.add_paragraph(f"  {sn['nombre']}: {viga_d['b_cm']:.0f} cm × {viga_d['h_cm']:.0f} cm × L_libre={viga_d['L_libre_m']:.2f} m")
    doc.add_paragraph(f"  f'c = {viga_d.get('fc',21)} MPa  |  fy = {viga_d.get('fy',420)} MPa")
    doc.add_heading("2. DISTRIBUCIÓN DE PRESIONES", level=1)
    doc.add_paragraph(f"  qu_max = {dist_d.get('qu_max',0):.2f} kPa  |  qu_min = {dist_d.get('qu_min',0):.2f} kPa")
    doc.add_paragraph(f"  Tipo distribución: {dist_d.get('tipo','—')}")
    doc.add_paragraph(f"  Excentricidad e_B = {dist_d.get('e_B',0):.3f} m  |  e_L = {dist_d.get('e_L',0):.3f} m")
    mey = dist_d.get('meyerhof')
    if mey:
        doc.add_paragraph(f"  ⚠ Área Efectiva Meyerhof: B'={mey['B_prima']:.2f} m × L'={mey['L_prima']:.2f} m → qu_eff={mey['qu_eff']:.1f} kPa")
    doc.add_heading(f"3. DISEÑO {sn['nombre'].upper()}", level=1)
    doc.add_paragraph(f"  Dimensión {sn['nombre']}: {viga_d['b_cm']:.0f} × {viga_d['h_cm']:.0f} cm")
    doc.add_paragraph(f"  h_min normativo ({sn['art']}): L/{sn['h_factor']} = {dis_d['h_min_cm']:.1f} cm  →  {' Cumple' if dis_d['ok_hmin'] else ' No cumple'}")
    doc.add_paragraph(f"  Peralte efectivo d = {dis_d['d_v']:.1f} cm")
    doc.add_paragraph(f"  Acero superior: {dis_d['n_sup']}x {dis_d['bar_long']}  →  As = {dis_d['As_sup']:.2f} cm²")
    doc.add_paragraph(f"  Acero inferior: {dis_d['n_inf']}x {dis_d['bar_long']}  →  As = {dis_d['As_inf']:.2f} cm²")
    doc.add_paragraph(f"  Cortante: φVc = {dis_d['phi_Vc']:.1f} kN  →  {' Cumple' if dis_d['ok_cort'] else ' No cumple'}")
    doc.add_paragraph(f"  Estribos: {dis_d['bar_est']} @ {dis_d['s_crit_cm']:.0f}/{dis_d['s_est_cm']:.0f} cm (crítica/resto)")
    doc.add_paragraph(f"  Fuerza axial sísmica req. = {dis_d['F_ax_req']:.1f} kN  |  {sn['F_ax_pct']*100:.1f}% × ΣP  →  {'' if dis_d['ok_Fax'] else ''}")
    if fig_vm is not None:
        try:
            import io as _io
            _buf = _io.BytesIO()
            fig_vm.write_image(_buf, format="png", width=700, height=350, scale=1.5)
            _buf.seek(0)
            doc.add_heading("4. DIAGRAMA V(x) / M(x)", level=1)
            doc.add_picture(_buf, width=_In(5.5))
        except Exception:
            doc.add_paragraph("  [Diagrama V/M no disponible — instalar kaleido para imágenes Plotly]")

    # ── SECCIÓN 5: VOLCAMIENTO Y DESLIZAMIENTO ─────────────────────────────
    doc.add_heading("5. VERIFICACIÓN DE ESTABILIDAD GLOBAL", level=1)
    doc.add_paragraph("  Referencia: NSR-10 C.15 / ACI 318 §13")
    doc.add_paragraph("")

    # Pesos propios
    _fc  = viga_d.get('fc',  21)
    _fy  = viga_d.get('fy', 420)
    _gc  = 24.0   # kN/m³ concreto
    _phi = 30.0   # fricción suelo (sin datos sismicos generales)
    _Be  = zap_ext_d['B_cm'] / 100.0
    _Le  = zap_ext_d['L_cm'] / 100.0
    _He  = zap_ext_d['H_cm'] / 100.0
    _Bi  = zap_int_d['B_cm'] / 100.0
    _Li  = zap_int_d['L_cm'] / 100.0
    _Hi  = zap_int_d['H_cm'] / 100.0
    _bv  = viga_d.get('b_cm', 30) / 100.0
    _hv  = viga_d.get('h_cm', 50) / 100.0
    _Lv  = viga_d.get('L_libre_m', 4.0)

    _W_zap_e = _Be * _Le * _He * _gc
    _W_zap_i = _Bi * _Li * _Hi * _gc
    _W_viga  = _bv * _hv * _Lv * _gc
    _W_total = _W_zap_e + _W_zap_i + _W_viga

    _P_ext = dist_d.get('P_ext', dist_d.get('qu_max', 0) * _Be * _Le)
    _P_int = dist_d.get('P_int', dist_d.get('qu_max', 0) * _Bi * _Li)
    _P_total = _P_ext + _P_int + _W_total

    doc.add_paragraph(f"  Peso Zapata Exterior:    {_W_zap_e:.2f} kN")
    doc.add_paragraph(f"  Peso Zapata Interior:    {_W_zap_i:.2f} kN")
    doc.add_paragraph(f"  Peso Viga de Amarre:     {_W_viga:.2f} kN")
    doc.add_paragraph(f"  Peso Total Sistema:      {_W_total:.2f} kN")
    doc.add_paragraph(f"  Carga Vertical Total:    {_P_total:.2f} kN")
    doc.add_paragraph("")

    # Volcamiento (eje en el borde de la zapata exterior)
    _M_volc = dist_d.get('M_volc', dist_d.get('e_B', 0) * _P_ext)
    _M_rest = _P_total * (_Be / 2.0)
    _FS_v   = _M_rest / max(_M_volc, 0.001)
    _ok_v   = _FS_v >= 1.5
    doc.add_paragraph(f"  VOLCAMIENTO → M_resist = {_M_rest:.2f} kN·m  |  M_volcante = {_M_volc:.2f} kN·m")
    doc.add_paragraph(f"  FS_volcamiento = {_FS_v:.2f}  {' ≥ 1.5 NSR-10 C.15' if _ok_v else ' < 1.5 — AUMENTAR B o L'}")
    doc.add_paragraph("")

    # Deslizamiento
    import math as _math
    _V_h    = dist_d.get('V_horiz', 0.0)          # cortante en la base
    _R_dmax = _P_total * _math.tan(_math.radians(_phi))   # fricción suelo-concreto
    _FS_d   = _R_dmax / max(_V_h, 0.001)
    _ok_d   = _FS_d >= 1.5 or _V_h == 0
    doc.add_paragraph(f"  DESLIZAMIENTO → R_fricción = {_R_dmax:.2f} kN  |  V_horiz = {_V_h:.2f} kN  (φ = {_phi:.0f}°)")
    doc.add_paragraph(f"  FS_deslizamiento = {_FS_d:.2f}  {' ≥ 1.5' if _ok_d else ' < 1.5 — Considerar llave de corte'}")

    return doc

# ─────────────────────────────────────────────
# T1: ESFUERZOS EN EL SUELO (BOUSSINESQ)
# ─────────────────────────────────────────────
with st.expander(_t(" 1. Esfuerzos en masa de suelo debajo de zapata", " 1. Soil Stresses under Footing (Boussinesq)"), expanded=False):
    st.info(_t(" **Modo de uso:** Ingresa las dimensiones de la zapata y la carga aplicada. El programa usa la solución de Boussinesq (integración de carga rectangular) para encontrar el incremento de esfuerzo vertical a cierta profundidad Z debajo del centro de la zapata.", " **How to use:** Enter footing dimensions and load. Uses Boussinesq method to find vertical stress increment at depth Z."))
    c1, c2 = st.columns(2)
    with c1:
        # ── Selector de Unidades para la Carga ──────────────────────────
        _P_unidades = {
            "kN":     1.0,
            "kgf":    0.00980665,
            "tf (ton-fuerza)": 9.80665,
            "kip":    4.44822,
            "lb (lbf)": 0.00444822,
        }
        _P_unit = st.selectbox("Unidad de carga P", list(_P_unidades.keys()), key="z_bous_Punit")
        _factor = _P_unidades[_P_unit]
        # Límites dinámicos según unidad
        _P_max = {
            "kN": 10000.0, "kgf": 1_000_000.0, "tf (ton-fuerza)": 1000.0,
            "kip": 2248.0, "lb (lbf)": 2_248_000.0,
        }
        _P_def = {
            "kN": 1000.0, "kgf": 100_000.0, "tf (ton-fuerza)": 100.0,
            "kip": 224.8, "lb (lbf)": 224_800.0,
        }
        P_bous_raw = st.number_input(
            f"Carga en Zapata P [{_P_unit}]",
            min_value=0.1, max_value=_P_max[_P_unit],
            value=_P_def[_P_unit], step=_P_max[_P_unit]/100,
            key="z_bous_P"
        )
        P_bous = P_bous_raw * _factor   # siempre en kN para los cálculos
        if _P_unit != "kN":
            st.caption(f"≡ **{P_bous:,.2f} kN** | {P_bous/9.80665:.2f} tf | {P_bous*224.809:.0f} lb")
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
    
    st.success(f" Incremento de esfuerzo vertical bajo el centro a Z={Z_bous}m: **Δσ_z = {delta_sigma_z:.2f} kPa**")
    
    # --- Gráficos Analíticos Boussinesq ---
    fig_b, (ax_v, ax_h) = plt.subplots(1, 2, figsize=(12, 4.5))
    fig_b.patch.set_facecolor("#0f1117")
    ax_v.set_facecolor("#161b22")
    ax_h.set_facecolor("#161b22")

    # 1. Perfil Vertical bajo el centro
    z_max = max(B_bous*4.0, 10.0)
    zs = np.linspace(0.1, z_max, 100)
    sigmas_v = [4 * q_0 * I_z_bous((B_bous/2.0)/z, (L_bous/2.0)/z) for z in zs]
    
    q_10 = q_0 * 0.10
    # Encontrar Z_influencia donde delta_sigma <= 10% q_0
    z_inf = next((z for z, sig in zip(zs, sigmas_v) if sig <= q_10), None)

    ax_v.plot(sigmas_v, zs, color="#00ffcc", lw=2.5, label="Δσ_z bajo el centro")
    ax_v.axvline(q_10, color="#ffdd44", linestyle="-.", lw=1.5, label="10% q₀ (Influencia)")
    if z_inf:
        ax_v.axhline(z_inf, color="#ff9500", linestyle=":", lw=1.5, label=f"Z inf ≈ {z_inf:.1f} m")

    ax_v.invert_yaxis()
    ax_v.set_xlabel("Incremento de Esfuerzo Δσ_z [kPa]", color="white")
    ax_v.set_ylabel("Profundidad Z [m]", color="white")
    ax_v.set_title("Distribución Vertical", color="white", fontsize=11)
    
    # Ajuste dinámico del rango X: un poco más del maximo de los valores relevantes
    # O ignorar el valor exacto en z=0.1 si es igual a q_0, enfocar en el tramo util.
    max_sigma_plot = max(sigmas_v)
    ax_v.set_xlim(0, max_sigma_plot * 1.1)
    
    ax_v.tick_params(colors="white")
    ax_v.grid(True, linestyle=":", alpha=0.3, color="white")
    ax_v.legend(loc="lower right", facecolor="#161b22", labelcolor="white", edgecolor="none")

    # 2. Perfiles Horizontales (Transversales al eje Y)
    def sigma_x(x_arr, z_val):
        # Esfuerzo usando Superposición Múltiple de rectángulos (Fadum corner formula)
        sigmas_h = []
        y1, y2 = L_bous/2.0, -L_bous/2.0
        for x in x_arr:
            x1, x2 = B_bous/2.0 - x, -B_bous/2.0 - x
            I1 = I_z_bous_vec(abs(x1)/z_val, abs(y1)/z_val) * np.sign(x1) * np.sign(y1)
            I2 = I_z_bous_vec(abs(x2)/z_val, abs(y1)/z_val) * np.sign(x2) * np.sign(y1)
            I3 = I_z_bous_vec(abs(x1)/z_val, abs(y2)/z_val) * np.sign(x1) * np.sign(y2)
            I4 = I_z_bous_vec(abs(x2)/z_val, abs(y2)/z_val) * np.sign(x2) * np.sign(y2)
            sigmas_h.append(q_0 * abs(I1 - I2 - I3 + I4))
        return sigmas_h

    xs = np.linspace(-B_bous*2, B_bous*2, 100)
    profundidades_plot = [B_bous, B_bous*2, B_bous*3]
    colores = ["#ff5252", "#ffd740", "#69f0ae"]
    
    for zd, col in zip(profundidades_plot, colores):
        sig_x = sigma_x(xs, zd)
        ax_h.plot(xs, sig_x, color=col, lw=2, label=f"Z = {zd:.1f} m")

    # Dibujar contorno de la zapata en Z=0
    ax_h.plot([-B_bous/2, B_bous/2], [q_0, q_0], color="white", lw=2.5, linestyle="-", label="Base Zapata")

    ax_h.set_xlabel("Distancia X [m]", color="white")
    ax_h.set_ylabel("Δσ_z [kPa]", color="white")
    ax_h.set_title("Perfiles Horizontales Transversales", color="white", fontsize=11)
    ax_h.set_xlim(-B_bous*2, B_bous*2)
    ax_h.set_ylim(0, q_0 * 1.1)
    ax_h.tick_params(colors="white")
    ax_h.grid(True, linestyle=":", alpha=0.3, color="white")
    ax_h.legend(loc="upper right", facecolor="#161b22", labelcolor="white", edgecolor="none")

    fig_b.tight_layout()
    st.pyplot(fig_b)

# ─────────────────────────────────────────────
# T2: CAPACIDAD PORTANTE DE SUELO (TERZAGHI) + ASENTAMIENTOS
# ─────────────────────────────────────────────
with st.expander(_t(" 2. Capacidad Portante de Suelo (Terzaghi) y Asentamientos", " 2. Bearing Capacity (Terzaghi) and Settlements"), expanded=False):
    st.info(_t(
        " **Modo de uso:** Ingresa φ, c, γ y la geometría de la zapata. "
        "El módulo calcula la capacidad última de Terzaghi con influencia del NF, "
        "grafica el diagrama Vesic (1973) para tipo de falla y el bulbo de presiones, "
        "y opcionalmente estima el asentamiento elástico inmediato.",
        " **How to use:** Enter φ, c, γ and footing geometry. Module calculates "
        "Terzaghi ultimate capacity with water-table correction, Vesic failure-type chart, "
        "pressure bulb, and optionally estimates immediate elastic settlement."
    ))

    # ── CONVERSOR DE UNIDADES ───────────────────────────────────────────────
    with st.container():
        st.markdown("** Conversor Rápido de Resistencia de Suelo**")
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
        st.markdown("#####  Parámetros Geotécnicos")
        phi_ang  = st.number_input(_t("Ángulo de fricción φ [°]","Friction angle φ [°]"),
                                   0.0, 50.0, st.session_state.get("z_phi", 30.0), 1.0, key="z_phi")
        coh_unit = st.selectbox(_t("Unidad cohesión:","Cohesion Unit:"),
                                ["kPa", "kg/cm²", "ton/m²"], key="coh_u")
        coh_val  = st.number_input(f"Cohesión c [{coh_unit}]", 0.0, 200.0,
                                   st.session_state.get("coh_val", 5.0 if coh_unit=="kPa" else 0.05),
                                   0.5 if coh_unit=="kPa" else 0.01, key="coh_val")
        coh_c    = coh_val if coh_unit=="kPa" else (coh_val*98.0665 if coh_unit=="kg/cm²" else coh_val*9.80665)
        gam_unit = st.selectbox(_t("Unidad γ húmedo:","γ moist Unit:"),
                                ["kN/m³", "ton/m³", "kg/m³"], key="gam_u")
        gam_val  = st.number_input(f"Peso esp. húmedo γ [{gam_unit}]", 10.0,
                                   25.0 if gam_unit != "kg/m³" else 2500.0,
                                   st.session_state.get("gam_val", 18.0 if gam_unit != "kg/m³" else 1800.0),
                                   0.5, key="gam_val")
        gamma_s  = gam_val if gam_unit=="kN/m³" else (gam_val*9.80665 if gam_unit=="ton/m³" else gam_val*0.00980665)
        gamma_sat_t = st.number_input("Peso esp. saturado γ_sat [kN/m³]", 16.0, 25.0, 20.0, 0.5, key="z_gsat")
        gamma_w  = 9.81
    with c2:
        st.markdown("#####  Geometría y Carga")
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
        Q_act  = st.number_input("Carga vertical actuante Q [kN]", 10.0, 50000.0, 800.0, 100.0, key="z_Qact")
    with c3:
        st.markdown("#####  Nivel Freático y FS")
        NF_prof = st.number_input("NF — Profundidad nivel freático [m]", 0.0, 20.0, 1.0, 0.5, key="z_nf")
        FS_terz = st.number_input(_t("Factor de Seguridad (FS)","Safety Factor (FS)"),
                                  1.0, 5.0, st.session_state.get("z_fs", 3.0), 0.1, key="z_fs")
        N_spt   = st.number_input("N60 campo (SPT)", 0, 100, 14, 1, key="z_spt")
        st.caption("ℹ N60 clasifica perfil (Vesic)")
        metodo_cap = st.radio("Método de Capacidad", ["Terzaghi", "Meyerhof"], horizontal=True)

    # Parámetros para asentamiento elástico movidos abajo para unificar IO
    pass

    # ── CÁLCULO GEOTÉCNICO ──────────────────────────────────────────────────
    phi_rad = math.radians(phi_ang)

    if metodo_cap == "Terzaghi":
        # Factores capacidad — Terzaghi
        if phi_ang == 0:
            Nc, Nq, Ngamma = 5.7, 1.0, 0.0
        else:
            a_t    = math.exp((0.75*math.pi - phi_rad/2)*math.tan(phi_rad))
            Nq     = (a_t**2) / (2*math.cos(math.radians(45) + phi_rad/2)**2)
            Nc     = (Nq - 1) / math.tan(phi_rad)
            Ngamma = 2*(Nq+1)*math.tan(phi_rad) / (1 + 0.4*math.sin(4*phi_rad))

        # Factores de forma (Terzaghi simplificado)
        if forma_zap in ["Cuadrada", "Square"]:
            sc, sq, sgamma = 1.3, 1.0, 0.8
        elif forma_zap in ["Circular"]:
            sc, sq, sgamma = 1.3, 1.0, 0.6
        else:
            sc, sq, sgamma = 1.0, 1.0, 1.0
        dc, dq, dgamma = 1.0, 1.0, 1.0
            
    else:
        # Factores de Capacidad — Meyerhof (1963)
        if phi_ang == 0:
            Nc, Nq, Ngamma = 5.14, 1.0, 0.0
            sc = 1 + 0.2 * (B_cp/L_cp)
            sq, sgamma = 1.0, 1.0
            dc = 1 + 0.2 * (Df_cp/B_cp)
            dq, dgamma = 1.0, 1.0
        else:
            Nq = math.exp(math.pi * math.tan(phi_rad)) * (math.tan(math.pi/4 + phi_rad/2)**2)
            Nc = (Nq - 1) / math.tan(phi_rad)
            Ngamma = (Nq - 1) * math.tan(1.4 * phi_rad)
            # Factores de Forma y Profundidad Meyerhof
            Kp = math.tan(math.pi/4 + phi_rad/2)**2
            sc = 1 + 0.2 * Kp * (B_cp / L_cp)
            sq = 1 + 0.1 * Kp * (B_cp / L_cp) if phi_ang >= 10 else 1.0
            sgamma = sq
            
            dc = 1 + 0.2 * math.sqrt(Kp) * (Df_cp / B_cp)
            dq = 1 + 0.1 * math.sqrt(Kp) * (Df_cp / B_cp) if phi_ang >= 10 else 1.0
            dgamma = dq

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

    q_ult  = sc*dc*coh_c*Nc + sq*dq*q_sob*Nq + sgamma*dgamma*0.5*gamma_eff*B_cp*Ngamma
    q_adm  = q_ult / FS_terz
    
    Q_ult  = q_ult * B_cp * L_cp
    q_act  = Q_act / (B_cp * L_cp)
    
    FS_calc = q_ult / q_act if q_act > 0 else 999.0
    cumplio = q_act <= q_adm

    # ── RESULTADOS ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown(f"####  Resultados de Capacidad Portante ({metodo_cap})")
    col_c1, col_c2, col_c3 = st.columns(3)
    col_c1.metric("Esfuerzo Admisible (q_adm)", f"{q_adm:.2f} kPa")
    col_c2.metric("Esfuerzo Actuante (q_act)", f"{q_act:.2f} kPa", delta=f"{q_adm - q_act:.2f} kPa (Margen)", delta_color="normal")
    fs_calc_disp = "∞" if q_act == 0 else f"{FS_calc:.2f}"
    col_c3.metric("FS Calculado (q_ult / q_act)", fs_calc_disp, delta=f"Requerido: {FS_terz:.2f}", delta_color="off")
    
    if cumplio:
        st.success(f" **Verificación Exitosa:** El esfuerzo actuante ({q_act:.2f} kPa) es MENOR o IGUAL al esfuerzo admisible ({q_adm:.2f} kPa).")
    else:
        st.error(f" **Falla por Capacidad:** El esfuerzo actuante ({q_act:.2f} kPa) es MAYOR al esfuerzo admisible ({q_adm:.2f} kPa). Aumenta la sección de la zapata o reduce la carga.")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.dataframe(pd.DataFrame([
            {"Parámetro": "Método",              "Valor": metodo_cap},
            {"Parámetro": "Nc / Nq / Nγ",        "Valor": f"{Nc:.2f} / {Nq:.2f} / {Ngamma:.2f}"},
            {"Parámetro": "sc / sq / sγ",         "Valor": f"{sc:.2f} / {sq:.2f} / {sgamma:.2f}"},
            {"Parámetro": "dc / dq / dγ",         "Valor": f"{dc:.2f} / {dq:.2f} / {dgamma:.2f}"},
            {"Parámetro": f"Caso NF",             "Valor": f"Caso {caso_nf} | NF={NF_prof}m"},
            {"Parámetro": "q sobrecarga",         "Valor": f"{q_sob:.2f} kPa"},
            {"Parámetro": "γ' efectivo",          "Valor": f"{gamma_eff:.2f} kN/m³"},
        ]), use_container_width=True, hide_index=True)
    with col_r2:
        st.markdown("**Conversión Admisible:**")
        m1,m2,m3 = st.columns(3)
        m1.metric("kPa (kN/m²)",    f"{q_adm:.1f}")
        m2.metric("ton/m²", f"{q_adm/9.80665:.2f}")
        m3.metric("kg/cm²", f"{q_adm/98.0665:.3f}")

    
    # (Detector de pilotes removido de aquí, mantenemos la versión completa más abajo)
    # ITEMS 2 & 3: Calculadora ks (coeficiente de balasto) y Rigidez Lambda
    with st.expander(" Coeficiente de Balasto ks (Winkler) y Rigidez Relativa"):
        col_ks1, col_ks2 = st.columns(2)
        with col_ks1:
            Es_mpa = st.number_input("Módulo elástico suelo Es [MPa]", 1.0, 200.0, 20.0, 1.0)
            nu_ks  = st.number_input("Relación de Poisson ν", 0.10, 0.49, 0.35, 0.01)
        with col_ks2:
            # Bowles (1996)
            ks = (Es_mpa * 1000.0) / (B_cp * (1.0 - nu_ks**2)) if B_cp > 0 else 0
            st.metric("ks estimado [kN/m³]", f"{ks:,.0f}")
            st.caption("Ref: Bowles (1996) — válido para zapatas rígidas")
        
        # Rigidez rel. (Lambda)
        import math
        Ec_zap = 4700 * math.sqrt(fcbasico) * 1000 if 'fcbasico' in globals() else 21000000  # kPa
        Iz_zap = (B_cp * L_cp**3) / 12.0
        
        if Iz_zap > 0 and Ec_zap > 0:
            lambda_rel = (ks * B_cp * L_cp**4) / (4.0 * Ec_zap * Iz_zap)
            if lambda_rel < 0.1:
                tipo_rig = " **RÍGIDA** — Distribución lineal válida "
            elif lambda_rel < 1.5:
                tipo_rig = " **SEMI-RÍGIDA** — Considerar análisis Winkler detallado"
            else:
                tipo_rig = " **FLEXIBLE** — Distribución real ≠ trapezoidal. Usar losa sobre resortes."
            st.metric("λ (rigidez relativa)", f"{lambda_rel:.4f}")
            st.markdown(tipo_rig)

    # ── ASENTAMIENTO ELÁSTICO (opcional) ─────────────────────────────
    with st.expander(" Asentamiento elástico inmediato", expanded=True):
        usar_asent = st.checkbox("Calcular asentamiento inmediato", value=False)
        if usar_asent:
            c_e1, c_e2 = st.columns(2)
            E_suelo = c_e1.number_input("Módulo elasticidad E [MPa]", 1.0, 500.0, 20.0, 1.0)
            nu_suelo = c_e2.number_input("Relación de Poisson ν", 0.1, 0.5, 0.35, 0.01)
            H_estrato = st.number_input("Profundidad del estrato compressible H [m]", 1.0, 50.0, 10.0, 1.0, key="h_estrato")
            
            st.divider()
            st.markdown("####  Resultado Asentamiento Elástico")
            E_kPa = E_suelo * 1000
            m = L_cp / B_cp
            n = H_estrato / B_cp
            
            def I_f_center(m, n):
                return min(1.2, 0.8 + 0.05 * (m - 1))
                
            I_center = I_f_center(m, n)
            asentamiento = q_adm * B_cp * (1 - nu_suelo**2) / E_kPa * I_center * 1000  # en mm
            st.metric("Asentamiento inmediato estimado", f"{asentamiento:.1f} mm")
            st.caption("⚠ Cálculo aproximado usando factor de influencia empírico. Para diseño detallado, usar métodos más refinados (e.g., Steinbrenner completo).")
            # Guardar asentamiento para uso en memoria
            st.session_state['asentamiento'] = asentamiento
        else:
            st.session_state['asentamiento'] = 0.0

        # CRITERIO NSR-10 H.3 — ¿Cuándo se recomienda pilotes? (Detector Inteligente)
        _necesita_pilotes = False
        _razones_pil = []
        if q_adm < 50:
            _razones_pil.append(f"q_adm = {q_adm:.0f} kPa < 50 kPa — suelo muy blando")
        if 'asentamiento' in locals() and asentamiento > 25:
            _razones_pil.append(f"Asentamiento estimado {asentamiento:.0f} mm > 25 mm")
        if N_spt < 5:
            _razones_pil.append(f"N60 = {N_spt} golpes — suelo muy suelto/blando")
        if B_cp > 0 and (Df_cp > B_cp * 3):
            _razones_pil.append(f"Df/B = {Df_cp/B_cp:.1f} > 3 — zapata muy profunda")

        if _razones_pil:
            _necesita_pilotes = True
            st.warning("⚠ **Considera cimentación profunda (pilotes):**\n" + 
                       "\n".join(f"- {r}" for r in _razones_pil))
            st.info(" *Este módulo calcula zapatas superficiales. Para pilotes, ver módulo **10_Pilotes** (próximamente).*")

    # ── GRÁFICA: TIPO DE FALLA (Vesic 1973 / SPT) ──────────────────────────
    st.divider()
    st.markdown("####  Diagrama Tipo de Falla — Vesic (1973)")
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
    ax_ves.fill_between(Dr_arr, c2v, -5, alpha=0.35, color="#e53935")
    ax_ves.fill_between(Dr_arr, c1v, c2v, alpha=0.30, color="#fb8c00")
    ax_ves.fill_between(Dr_arr, 0, c1v, alpha=0.25, color="#43a047")
    ax_ves.text(10, -0.3, "Falla por\nPunzonamiento", color="white", fontsize=12, fontweight="bold", ha="center")
    ax_ves.text(50, -1.5, "Falla local\npor corte",   color="white", fontsize=12, fontweight="bold", ha="center")
    ax_ves.text(80, -3.5, "Falla general\npor corte", color="white", fontsize=12, fontweight="bold", ha="center")
    # Miniatura fundación
    rec_w = 15; rec_h = 0.3
    ax_ves.add_patch(patches.Rectangle((2, -Df_B - rec_h), rec_w, rec_h,
                                       fc="#888", ec="white", lw=0.8))
    ax_ves.annotate(f"B={B_cp}m\nHz={Hz_cp}m", (2+rec_w/2, -Df_B - rec_h*2),
                    color="yellow", fontsize=7, ha="center")
    # Punto actual
    ax_ves.plot(Dr_pct, -Df_B, "D", color="cyan", ms=12, zorder=6,
                label=f"Dr≈{Dr_pct:.0f}% | Df/B={Df_B:.2f}")
    ax_ves.set_xlim(0, 100); ax_ves.set_ylim(-5, 0)
    ax_ves.set_xlabel("Densidad relativa Dr (%)", color="white")
    ax_ves.set_ylabel("-Df / B*", color="white")
    ax_ves.set_title(f"Tipo de Falla — N60={N_spt} campo → Dr≈{Dr_pct:.0f}%  |  Df/B={Df_B:.2f}", color="white")
    ax_ves.tick_params(colors="white"); ax_ves.spines[:].set_color("#444")
    ax_ves.legend(loc="lower right", fontsize=8, facecolor="#111", labelcolor="white")
    st.pyplot(fig_ves)

    # ── GRÁFICA: BULBO DE PRESIONES / MECANISMO DE FALLA (VECTORIZADO) ───
    st.divider()
    st.markdown("####  Mecanismo de Falla y Bulbo de Presiones (Terzaghi)")
    fig_tb, ax_tb = plt.subplots(figsize=(10, 7))
    ax_tb.set_facecolor("#0f1117"); fig_tb.patch.set_facecolor("#0f1117")

    half_B = B_cp / 2.0
    zap_bot = -(Df_cp + Hz_cp)

    # === MECANISMO DE FALLA DE TERZAGHI (Prandtl) ===
    # Ángulos de cuña
    alpha = math.pi/4 + phi_rad/2
    H_tri = half_B * math.tan(alpha)
    pole_x = half_B
    pole_y = zap_bot
    theta_0 = math.atan2(-H_tri, -half_B)
    sweep = math.pi/2
    theta_end = theta_0 + sweep

    # Zona I — Triángulo activo central (Rosa oscuro)
    tri_pts = [(-half_B, zap_bot), (half_B, zap_bot), (0, zap_bot - H_tri)]
    ax_tb.add_patch(plt.Polygon(tri_pts, fc="#e57373", ec="black", lw=1.2, alpha=0.9, zorder=5, label="Zona I (Activa)"))

    if phi_rad >= 0.0:
        # Geometría del espiral (Arco)
        theta_arr = np.linspace(theta_0, theta_end, 40)
        r_arr = (half_B / math.cos(alpha)) * np.exp((theta_arr - theta_0) * math.tan(phi_rad))
        x_spiral = pole_x + r_arr * np.cos(theta_arr)
        y_spiral = pole_y + r_arr * np.sin(theta_arr)
        end_x = x_spiral[-1]
        end_y = y_spiral[-1]

        beta_passive = math.pi/4 - phi_rad/2
        # Prevenir error si beta_passive se hace 0 (para arcilla phi=0, beta_passive=45 deg, siempre >0)
        dist_x = abs(end_y - pole_y) / math.tan(beta_passive)
        x_top = end_x + dist_x

        # Zona II (Radial - Amarillo) - Derecha
        poly_Z2_R = [(pole_x, pole_y)] + list(zip(x_spiral, y_spiral))
        ax_tb.add_patch(plt.Polygon(poly_Z2_R, fc="#ffe082", ec="black", lw=1.2, alpha=0.85, zorder=4, label="Zona II (Radial)"))
        # Zona III (Pasiva - Naranja claro) - Derecha
        poly_Z3_R = [(pole_x, pole_y), (end_x, end_y), (x_top, pole_y)]
        ax_tb.add_patch(plt.Polygon(poly_Z3_R, fc="#ffb74d", ec="black", lw=1.2, alpha=0.85, zorder=3, label="Zona III (Pasiva)"))

        # Zonas II y III - Izquierda (Espejo simétrico)
        poly_Z2_L = [(-x, y) for (x, y) in poly_Z2_R]
        ax_tb.add_patch(plt.Polygon(poly_Z2_L, fc="#ffe082", ec="black", lw=1.2, alpha=0.85, zorder=4))
        poly_Z3_L = [(-x, y) for (x, y) in poly_Z3_R]
        ax_tb.add_patch(plt.Polygon(poly_Z3_L, fc="#ffb74d", ec="black", lw=1.2, alpha=0.85, zorder=3))

        # Sobrecarga de fosa (Suelo arriba de Df - Relleno pasivo)
        if zap_bot < 0:
            ax_tb.add_patch(patches.Rectangle((-x_top, zap_bot), 2*x_top, -zap_bot,
                                              fc="#ffebee", ec="black", lw=1, alpha=0.6, zorder=2, label="Sobrecarga"))
            # Extender limits del eje X para que abarque hasta la cuna pasiva
            ax_tb.set_xlim(-x_top * 1.2, x_top * 1.2)

    # Zapata
    ax_tb.add_patch(patches.Rectangle((-half_B, zap_bot), B_cp, Hz_cp,
                                      fc="#546e7a", ec="white", lw=1.5, zorder=4,
                                      label=f"Zapata {B_cp}×{L_cp}m"))
    # Columna
    ax_tb.add_patch(patches.Rectangle((-b_col_cp/2, 0), b_col_cp, -Df_cp + Hz_cp*0.1,
                                      fc="#78909c", ec="white", lw=1, zorder=4))

    # Bulbo de presiones Boussinesq (Teoría elástica 2D - Suma de Cuadrantes)
    _xg = np.linspace(-B_cp*3.5, B_cp*3.5, 200)
    _zg = np.linspace(zap_bot, zap_bot - B_cp*3.5, 150)
    Xg, Zg = np.meshgrid(_xg, _zg)
    q0_bulbo = q_ult
    dz = np.abs(Zg - zap_bot)
    dz = np.where(dz < 0.05, 0.05, dz)  # evitar división por cero
    
    def I_corner(X, Y, Z_arr):
        m = np.abs(X) / Z_arr
        n = np.abs(Y) / Z_arr
        m = np.clip(m, 1e-6, 1e6)
        n = np.clip(n, 1e-6, 1e6)
        return I_z_bous_vec(m, n) * np.sign(X) * np.sign(Y)

    # Suma algebraica para (x, y=0)
    x1 = half_B - Xg
    x2 = -half_B - Xg
    y1 = L_cp / 2.0
    y2 = -L_cp / 2.0

    I1 = I_corner(x1, y1, dz)
    I2 = I_corner(x2, y1, dz)
    I3 = I_corner(x1, y2, dz)
    I4 = I_corner(x2, y2, dz)
    
    sigma_arr = q0_bulbo * np.abs(I1 - I2 - I3 + I4)

    # Renderizado suave y profesional
    levels = np.linspace(q0_bulbo*0.02, q0_bulbo*0.95, 50)
    cs = ax_tb.contourf(Xg, Zg, sigma_arr, levels=levels, cmap="YlOrBr", alpha=0.9, zorder=1)
    cs_lines = ax_tb.contour(Xg, Zg, sigma_arr, levels=levels[::3], colors='white', linewidths=0.5, zorder=1, alpha=0.6)
    ax_tb.clabel(cs_lines, inline=True, fontsize=9, fmt='%1.0f')
    cbar = fig_tb.colorbar(cs, ax=ax_tb, label="Δσz [kPa]", shrink=0.7)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color="white")

    # Línea de exploración (si existe en sesión)
    if "z_exploracion" in st.session_state:
        z_ex = st.session_state.z_exploracion
        ax_tb.axhline(-(Df_cp + z_ex), color="cyan", lw=1.8, linestyle="--", label=f"Prof. exploración = {z_ex:.1f}m")

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
with st.expander(_t(" 4. Profundidad Mínima de Exploración de Subsuelo (NSR-10)", " 4. Minimum Subsurface Exploration Depth")):
    st.info(_t(
        " **Modo de uso:** Sincronizado automáticamente con las dimensiones (B, L) y carga (Q_actuante) ingresadas en el panel principal. "
        "Según la norma **NSR-10 (Título H.3.2.3)**, las perforaciones deben alcanzar una profundidad donde el incremento de "
        "esfuerzo vertical (Δσ_z) sea menor o igual al **10% del esfuerzo de contacto (q_0)** transmitido por la estructura.",
        " **How to use:** Automatically synced with main B, L and Q inputs. NSR-10 requires exploring "
        "until the stress increment drops below 10% of the contact stress (q_0)."
    ))
    
    q0_ex = Q_act / (B_cp * L_cp)
    st.markdown(f"**Dimensiones Base:** $B={B_cp}$ m, $L={L_cp}$ m | **Carga Transferida:** $Q={Q_act}$ kN | **Esfuerzo de Contacto:** $q_0 = {q0_ex:.2f}$ kPa")
    
    # Biseccion para encontrar Z donde delta_sigma_z / q0_ex = 0.10
    z_low = 0.1
    z_high = 50.0
    for _ in range(30):
        z_mid = (z_low + z_high)/2
        m_ex = (B_cp/2.0) / z_mid
        n_ex = (L_cp/2.0) / z_mid
        rat = 4 * I_z_bous(m_ex, n_ex)
        if rat > 0.10:
            z_low = z_mid
        else:
            z_high = z_mid
            
    st.success(f" La profundidad mínima normativa de exploración (donde Δσ_z = 10% de q0) es: **Z_exploración = {z_mid:.2f} m** bajo el nivel de fundación.")
    
    # Gráfica ilustrativa del descenso del esfuerzo
    fig_ex, ax_ex = plt.subplots(figsize=(8, 5))
    fig_ex.patch.set_facecolor("#0f1117")
    ax_ex.set_facecolor("#161b22")
    
    z_plot = np.linspace(0.1, z_mid * 1.5, 100)
    sig_plot = [4 * q0_ex * I_z_bous((B_cp/2.0)/z, (L_cp/2.0)/z) for z in z_plot]
    
    ax_ex.plot(sig_plot, z_plot, color="#69f0ae", lw=2.5, label="Δσ_z bajo el centro")
    if "z_exploracion" in st.session_state:
        zx = st.session_state.z_exploracion
        sz = 4 * q0_ex * I_z_bous((B_cp/2.0)/zx, (L_cp/2.0)/zx)
        ax_ex.plot(sz, zx, marker="*", color="yellow", markersize=14, zorder=10, label=f"Z={zx:.1f}m ({sz:.1f} kPa)")
        ax_ex.axhline(zx, color="yellow", linestyle=":", alpha=0.5)
    ax_ex.axvline(q0_ex * 0.10, color="#ffdd44", linestyle="-.", lw=1.5, label=f"10% q₀ ({q0_ex*0.1:.1f} kPa)")
    ax_ex.axhline(z_mid, color="#ff9500", linestyle=":", lw=1.5, label=f"Z_exploración = {z_mid:.1f} m")
    ax_ex.fill_betweenx(z_plot, sig_plot, 0, where=(z_plot <= z_mid), color="white", alpha=0.08)
    
    ax_ex.invert_yaxis()
    ax_ex.set_xlabel("Incremento de Esfuerzo Δσ_z [kPa]", color="white", fontsize=10)
    ax_ex.set_ylabel("Profundidad Z [m]", color="white", fontsize=10)
    ax_ex.set_title("Atenuación Analítica del Esfuerzo (Criterio 10% NSR-10)", color="white", fontsize=11)
    ax_ex.set_xlim(0, max(sig_plot) * 1.1)
    ax_ex.tick_params(colors="white", labelsize=9)
    ax_ex.grid(True, linestyle=":", alpha=0.3, color="white")
    ax_ex.legend(loc="lower right", facecolor="#161b22", labelcolor="white", edgecolor="none")
    
    fig_ex.tight_layout()
    st.pyplot(fig_ex)
    
    # Guardar en sesión para usarlo en gráficos
    st.session_state.z_exploracion = z_mid

# ─────────────────────────────────────────────
# T3: DISEÑO ESTRUCTURAL DE ZAPATA + DIBUJADOR 3000 (con biaxialidad)
# ─────────────────────────────────────────────
with st.expander(_t(" 3. Diseño Estructural de Zapata Prismática y Dibujador 3000", " 3. Footing Structural Design & DXF Drafter"), expanded=True):
    st.markdown(f"**Norma Estructural activa:** `{norma_sel}`")

    # ─── SELECTOR DE TIPO DE ZAPATA (Opción B) ───────────────────────────────
    _TIPOS_ZAP = [
        "1. Aislada Céntrica",
        "2. Medianera (Lindero)",
        "3. Esquina (Dos linderos)",
        "4. Con Viga de Amarre / Strap Beam",
    ]
    tipo_zap = st.selectbox(
        _t(" Tipo de Zapata:", " Footing Type:"),
        _TIPOS_ZAP,
        index=st.session_state.get("z_tipo_idx", 0),
        key="z_tipo_zap",
        help=_t("Selecciona el tipo de zapata para activar el flujo de cálculo correspondiente.",
                "Select the footing type to activate the corresponding calculation flow.")
    )
    st.session_state["z_tipo_idx"] = _TIPOS_ZAP.index(tipo_zap)

    # Derivar los flags de modo
    _modo_aislada   = ("1." in tipo_zap)
    _modo_medianera = ("2." in tipo_zap)
    _modo_esquina   = ("3." in tipo_zap)
    _modo_strap     = ("4." in tipo_zap or _modo_medianera or _modo_esquina)

    # ─── TIPO 2, 3, 4: Redirigir a render_medianera() ────────────────────────
    if not _modo_aislada:
        render_medianera(norma_sel, fc_basico, fy_basico, REBAR_DICT, def_idx, phi_v, phi_f, tipo_zap)
        # Los tipos 2/3/4 tienen su propio flujo completo, no continúan el bloque T3
    else:
        # ─── TIPO 1: Flujo original de zapata aislada céntrica ────────────────
        st.info(_t(" **Modo: Zapata Aislada Céntrica** — Ingresa las Cargas de Servicio (para dimensionar BxL) y Últimas (para diseñar espesor y acero).",
                   " **Mode: Isolated Centered Footing** — Enter Service Loads (BxL sizing) and Ultimate Loads (thickness and steel)."))

    colA, colB, colC = st.columns(3)
    with colA:
        st.write("#### Cargas (Servicio y Últimas)")
        P_svc = st.number_input("Carga Axial de Servicio Ps [kN]", value=800.0, step=50.0)
        M_svc_B = st.number_input("Momento de Servicio Ms (dir. B) [kN·m]", value=0.0, step=10.0)
        M_svc_L = st.number_input("Momento de Servicio Ms (dir. L) [kN·m]", value=0.0, step=10.0)
        P_ult = st.number_input("Carga Axial Factorizada Pu [kN]", value=1120.0, step=50.0)
        M_ult_B = st.number_input("Momento Factorizado Mu (dir. B) [kN·m]", value=0.0, step=10.0)
        M_ult_L = st.number_input("Momento Factorizado Mu (dir. L) [kN·m]", value=0.0, step=10.0)
        
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

        # Mostrar equivalencias en formato adaptable (evita que se corte la métrica en pantallas reducidas)
        st.info(f" **Equivalencia:** `{q_adm_z:.1f} kPa` | `{q_adm_z/9.80665:.2f} ton/m²` | `{q_adm_z/98.0665:.3f} kg/cm²` | `{q_adm_z/1000:.4f} MPa`")

        c1_col = st.number_input(_t("Dim. Columna c1 (dir. B) [cm]", "Column dim. c1 (B dir.) [cm]"), min_value=5.0, value=40.0, step=5.0)
        c2_col = st.number_input(_t("Dim. Columna c2 (dir. L) [cm]", "Column dim. c2 (L dir.) [cm]"), min_value=5.0, value=40.0, step=5.0)
        pos_col_iso = st.selectbox("Posición de la columna", ["Interior", "Borde (eje X)", "Borde (eje Y)", "Esquina"], key="pos_col_iso")
        gamma_prom = st.number_input(_t("γ_promedio (suelo+concreto) [kN/m³]", "γ_avg (soil+concrete) [kN/m³]"), value=20.0)
        Df_z = st.number_input(_t("Desplante Df [m]", "Footing Depth Df [m]"), value=1.0, step=0.1)

    with colC:
        st.write("#### Diseño Estructural")
        H_zap = st.number_input("Espesor H propuesto [cm]", value=50.0, step=5.0)
        recub_z = st.number_input("Recubrimiento al suelo [cm]", value=7.5, step=0.5)
        bar_z = st.selectbox("Varilla a utilizar:", list(REBAR_DICT.keys()), index=def_idx)
        A_bar_z = REBAR_DICT[bar_z]["area"] * 100 # mm2
        db_bar_z = REBAR_DICT[bar_z]["db"] # mm
        
    # ─── Validaciones robustas ──────────────────────────────────────────────
    if c1_col <= 0 or c2_col <= 0:
        st.error(" Las dimensiones de la columna (c1, c2) deben ser mayores a 0 cm.")
        st.stop()
    # Verificar espesor mínimo
    d_min = recub_z + db_bar_z/10.0 + 2  # cm
    if H_zap < d_min:
        st.warning(f"⚠ El espesor H={H_zap} cm es menor que el mínimo recomendado (recubrimiento + db/10 + 2 cm = {d_min:.1f} cm). Aumente H.")
    # Verificar q_net positivo
    q_net = q_adm_z - gamma_prom * Df_z
    if q_net <= 0:
        st.error(f" El esfuerzo neto disponible q_net = {q_net:.2f} kPa es negativo o nulo. Reduzca Df o aumente q_adm.")
        st.stop()

    # Paso 1: Dimensionamiento en planta (considerando excentricidades)
    # Para momento combinado, la presión máxima se da por flexión biaxial:
    # q_max = P/A ± (Mx * y / Ix) ± (My * x / Iy)
    # Primero obtenemos dimensiones mínimas basadas en q_net (sin momento)
    Area_req = P_svc / q_net
    # Proponemos zapata cuadrada si los momentos son bajos
    L_req = math.sqrt(Area_req * (c2_col/c1_col) if c1_col>0 else Area_req)
    B_req = Area_req / L_req if L_req > 0 else 0
    B_zap = math.ceil(B_req * 20) / 50.0
    L_zap = math.ceil(L_req * 20) / 50.0
    st.markdown(f"**Dimensiones mínimas sin excentricidad:** B = {B_zap:.2f} m, L = {L_zap:.2f} m")
    
    cB, cL = st.columns(2)
    B_use = cB.number_input("B usado para cálculo [m]", value=max(2.0, B_zap), step=0.1)
    L_use = cL.number_input("L usado para cálculo [m]", value=max(2.0, L_zap), step=0.1)

    # ─── Presión de contacto con flexión biaxial ─────────────────────────────
    A_use = B_use * L_use
    
    A_req = getattr(st.session_state, 'z_A_req_cache', max(B_zap * L_zap, 0.1)) # fallback safely
    try: A_req = P_svc / q_adm_z if q_adm_z > 0 else 0.1
    except: pass
    if B_use * L_use < A_req:
        st.error(
            f" **ÁREA INSUFICIENTE** — Se requieren {A_req:.2f} m² "
            f"pero se proveen {B_use*L_use:.2f} m². "
            f"Aumenta B o L."
        )
    
    Ix = (B_use * L_use**3) / 12   # momento de inercia respecto al eje X (paralelo a B)
    Iy = (L_use * B_use**3) / 12   # momento de inercia respecto al eje Y (paralelo a L)
    # Coordenadas de las esquinas (x,y) con origen en el centro de la zapata
    corners = [(-B_use/2, -L_use/2), ( B_use/2, -L_use/2),
               ( B_use/2,  L_use/2), (-B_use/2,  L_use/2)]
    q_corners = []
    for x, y in corners:
        q = P_ult/A_use + (M_ult_L * x / Iy) + (M_ult_B * y / Ix)
        q_corners.append(q)
    qu_max = max(q_corners)
    qu_min = min(q_corners)
    # Presión promedio sobre el área crítica (se usa el promedio de las máximas y la presión en la zona de cortante)
    # Para simplificar, usamos el promedio de qu_max y max(qu_min,0)
    qu_avg = (qu_max + max(qu_min, 0)) / 2.0

    # ─── B4: ÁREA EFECTIVA MEYERHOF (cuando qu_min < 0) ────────────────────
    # Si hay zona en tensión, la superposición simple sobreestima la presión
    # real. Se aplica el método de área efectiva: B' = B-2eB, L' = L-2eL
    _ecc_B = abs(M_svc_L / P_svc) if P_svc > 0 else 0.0   # excentricidad dir.B [m]
    _ecc_L = abs(M_svc_B / P_svc) if P_svc > 0 else 0.0   # excentricidad dir.L [m]
    _usar_meyerhof = qu_min < 0 and P_ult > 0
    if _usar_meyerhof:
        _B_prima = max(0.1, B_use - 2 * _ecc_B)
        _L_prima = max(0.1, L_use - 2 * _ecc_L)
        _A_prima = _B_prima * _L_prima
        qu_avg = P_ult / _A_prima        # QA-1: qu_avg mutado antes de usarse en punzonamiento y cortante
        qu_max = qu_avg * 1.25           # distribución trapezoidal aproximada
        qu_min = 0.0                     # por definición en el área efectiva
        _meyerhof_info = (f"⚠ **Área Efectiva Meyerhof aplicada** — qu_min < 0 → "
                          f"eB={_ecc_B:.2f} m, eL={_ecc_L:.2f} m | "
                          f"B'={_B_prima:.2f} m, L'={_L_prima:.2f} m | "
                          f"A'={_A_prima:.2f} m² | qu_eff={qu_avg:.1f} kPa")
    else:
        _meyerhof_info = None

    # Peralte efectivo
    d_z = H_zap - recub_z - (db_bar_z/10.0)
    if d_z <= 0:
        st.error(f" EC-3: Peralte efectivo d_z = {d_z:.2f} cm ≤ 0. Aumente H o reduzca recub. / diámetro.")
        st.stop()
    d_z_m = d_z / 100.0

    # ─── CORTANTE UNIDIRECCIONAL (Viga) con integración exacta de presión ───
    lv_b = (B_use - c1_col/100.0) / 2.0
    lv_l = (L_use - c2_col/100.0) / 2.0

    def q_at(x, y):
        return P_ult/A_use + (M_ult_L * x / Iy) + (M_ult_B * y / Ix)

    # Cortante en dirección B
    x_corte_b = lv_b - d_z_m
    Vu_1way_B = 0.0
    if x_corte_b > 0:
        y_vals = np.linspace(-L_use/2, L_use/2, 50)
        x_vals = np.linspace(x_corte_b, lv_b, 50)
        dx = (lv_b - x_corte_b) / 50
        dy = L_use / 50
        for xi in x_vals:
            for yi in y_vals:
                q_xy = q_at(xi, yi)
                if q_xy > 0: Vu_1way_B += q_xy * dx * dy

    phi_Vc_1way_B = phi_v * 0.17 * 1.0 * math.sqrt(fc_basico) * (L_use * 1000) * (d_z * 10) / 1000.0  # kN
    ok_1way_B = phi_Vc_1way_B >= Vu_1way_B

    # Cortante en dirección L
    y_corte_l = lv_l - d_z_m
    Vu_1way_L = 0.0
    if y_corte_l > 0:
        x_vals = np.linspace(-B_use/2, B_use/2, 50)
        y_vals = np.linspace(y_corte_l, lv_l, 50)
        dx = B_use / 50
        dy = (lv_l - y_corte_l) / 50
        for xi in x_vals:
            for yi in y_vals:
                q_xy = q_at(xi, yi)
                if q_xy > 0: Vu_1way_L += q_xy * dx * dy

    phi_Vc_1way_L = phi_v * 0.17 * 1.0 * math.sqrt(fc_basico) * (B_use * 1000) * (d_z * 10) / 1000.0  # kN
    ok_1way_L = phi_Vc_1way_L >= Vu_1way_L

    # ─── PUNZONAMIENTO (bidireccional) con presión promedio ─────────────────
    bo_1 = c1_col/100.0 + d_z_m
    bo_2 = c2_col/100.0 + d_z_m
    if pos_col_iso == "Interior":
        bo_perim = 2 * (bo_1 + bo_2)
        alpha_s = 40
    elif pos_col_iso == "Borde (eje X)":
        bo_perim = 2*bo_1 + (c2_col/100.0 + d_z_m/2.0)
        alpha_s = 30
    elif pos_col_iso == "Borde (eje Y)":
        bo_perim = 2*bo_2 + (c1_col/100.0 + d_z_m/2.0)
        alpha_s = 30
    else: # Esquina
        bo_perim = (c1_col/100.0 + d_z_m/2.0) + (c2_col/100.0 + d_z_m/2.0)
        alpha_s = 20
    Area_punz = bo_1 * bo_2
    # Presión promedio en el área crítica (se usa qu_avg)
    Vu_punz = P_ult - qu_avg * Area_punz

    _min_col = min(c1_col, c2_col)
    beta_c = max(c1_col, c2_col) / _min_col if _min_col > 0 else 1.0
    try:
        Vc1 = 0.33 * math.sqrt(fc_basico)
        Vc2 = 0.17 * (1 + 2/beta_c) * math.sqrt(fc_basico)
        Vc3 = 0.083 * (2 + alpha_s * (d_z*10) / (bo_perim*1000)) * math.sqrt(fc_basico)
        vc_min_MPa = min(Vc1, Vc2, Vc3)
    except ZeroDivisionError:
        vc_min_MPa = 0.0
        st.warning("⚠ División por cero al calcular resistencia a punzonamiento — revise dimensiones.")
    phi_Vc_punz = phi_v * vc_min_MPa * (bo_perim * 1000) * (d_z * 10) / 1000.0  # kN
    ok_punz = phi_Vc_punz >= Vu_punz

    # ─── FLEXIÓN (momentos con integración exacta) ───────────────────────────
    # Momento en dirección B (respecto al eje paralelo a L)
    # Se integra presión * brazo a lo largo del voladizo
    # Para simplificar, integramos numéricamente
    def momento_dir_B():
        # Integrar (q(x,y) * (distancia desde la cara de la columna)) sobre el área del voladizo
        # La distancia desde la cara de la columna es (x + lv_b) con x desde -lv_b a 0 (coordenada local)
        # Usamos coordenadas globales: x desde -B_use/2 hasta -B_use/2 + lv_b ? Mejor usar x desde -lv_b a 0 con origen en cara
        # pero la presión es función de x e y globales.
        # La distancia desde la cara es (x_cara) que es lv_b - (x_global + B_use/2)? Mejor usar integración directa.
        # Usamos un método numérico: sobre el voladizo en dirección B, x_global desde -B_use/2 hasta -B_use/2+lv_b (lado izquierdo)
        # y_global desde -L_use/2 hasta L_use/2. El brazo de momento es la distancia desde la cara de la columna:
        # brazo = (x_global + B_use/2) ? No, la cara de la columna está a -B_use/2 + c1_col/200? Confuso.
        # Para simplificar, usamos la fórmula clásica con presión promedio, pero mejoramos con distribución lineal.
        # Dado que ya tenemos presión variable, podemos usar una integración numérica simple.
        # Tomamos puntos en el voladizo.
        x_min = -B_use/2
        x_cara_col = -c1_col/200.0  # coordenada de la cara de la columna (lado izquierdo)
        # El voladizo izquierdo va desde x_cara_col hasta x_min? No, el voladizo es desde x_cara_col hasta -B_use/2? Revisar.
        # En realidad la columna está centrada, entonces la cara izquierda está en -c1_col/200.
        # El voladizo izquierdo va desde x = -B_use/2 hasta x = -c1_col/200.
        x_left = -B_use/2
        x_right_face = -c1_col/200.0
        if x_right_face <= x_left:
            return 0.0
        n_x = 20
        n_y = 20
        x_vals = np.linspace(x_left, x_right_face, n_x)
        y_vals = np.linspace(-L_use/2, L_use/2, n_y)
        dx = (x_right_face - x_left) / n_x
        dy = L_use / n_y
        Mu_B = 0.0
        for xi in x_vals:
            # brazo desde la cara de la columna
            lever = x_right_face - xi
            for yi in y_vals:
                q_xy = q_at(xi, yi)
                if q_xy > 0:
                    Mu_B += q_xy * lever * dx * dy
        return Mu_B

    Mu_flex_B = momento_dir_B()
    # Similar para dirección L (voladizo en Y)
    def momento_dir_L():
        y_bot = -L_use/2
        y_face = -c2_col/200.0
        if y_face <= y_bot:
            return 0.0
        n_x = 20
        n_y = 20
        x_vals = np.linspace(-B_use/2, B_use/2, n_x)
        y_vals = np.linspace(y_bot, y_face, n_y)
        dx = B_use / n_x
        dy = (y_face - y_bot) / n_y
        Mu_L = 0.0
        for yi in y_vals:
            lever = y_face - yi
            for xi in x_vals:
                q_xy = q_at(xi, yi)
                if q_xy > 0:
                    Mu_L += q_xy * lever * dx * dy
        return Mu_L

    Mu_flex_L = momento_dir_L()

    # Diseño a flexión para dirección B
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
    sep_B = (L_use*100 - 2*recub_z) / max(1, n_barras_B - 1)  # Acero Dir.B se distribuye a lo largo de L

    # Diseño a flexión para dirección L
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
    sep_L = (B_use*100 - 2*recub_z) / max(1, n_barras_L - 1)  # Acero Dir.L se distribuye a lo largo de B

    # Para compatibilidad con el resto del código
    Mu_flex = Mu_flex_B
    disc_z = disc_B
    As_req_total = As_req_B
    n_barras_Z = n_barras_B
    separacion_S = sep_B

    # --- CÁLCULO DE GANCHOS Y DOBLECES (NSR-10 / ACI 318) ---
    # Diámetro mínimo de doblez (D_doblez)
    db_mm = db_bar_z
    if db_mm <= 25.4: # Hasta #8 (1")
        D_doblez_mm = 6 * db_mm
    elif db_mm <= 35.8: # #9 a #11
        D_doblez_mm = 8 * db_mm
    else: # #14 a #18
        D_doblez_mm = 10 * db_mm
    D_doblez_cm = D_doblez_mm / 10.0

    # Longitud de extensión del gancho a 90° (L_ext)
    # Norma ACI/NSR-10: max(12*db, 150mm) usualmente para estribos, pero para anclaje en tracción (gancho estándar 90°) es 12*db
    L_ext_gancho_mm = 12 * db_mm
    L_ext_gancho_cm = L_ext_gancho_mm / 10.0
    
    # Radios para dibujo
    radio_doblez_cm = D_doblez_cm / 2.0
    
    # Longitudes de desarrollo disponibles
    ldh_disp_B = (B_use*100 - c1_col)/2 - recub_z
    ldh_disp_L = (L_use*100 - c2_col)/2 - recub_z
    
    # Altura disponible para el gancho
    h_gancho_disp = H_zap - 2*recub_z
    L_gancho_real_cm = min(h_gancho_disp, L_ext_gancho_cm + radio_doblez_cm + db_mm/10.0) # Lo que cabe en la zapata


    tab_res, tab_dwg, tab_apu = st.tabs([" Resultados del Diseño", " Plano 3000 (DXF)", " Cantidades APU"])
    
    with tab_res:
        st.markdown(f"**Revisión Estructural: f'c = {fc_basico} MPa | fy = {fy_basico} MPa**")
        
        # ─── RECOMENDACIÓN DE ACERO Y ALERTA ───
        sep_max = min(3 * H_zap, 45.0)
        warning_bar = []
        if sep_B > sep_max or sep_L > sep_max:
            warning_bar.append(f"⚠ La separación ({max(sep_B, sep_L):.1f} cm) excede la máxima permitida normativa ({sep_max} cm). ¡Usa una varilla más pequeña (ej. #4 o #5)!")
        if sep_B < 10.0 or sep_L < 10.0:
            warning_bar.append(f"⚠ La separación ({min(sep_B, sep_L):.1f} cm) es muy estrecha para fundir bien (< 10 cm). Considera usar una varilla de mayor diámetro.")
        if warning_bar:
            st.error("\n\n".join(warning_bar))
            
        c2d1, c2d2 = st.columns([1, 1])
        with c2d1:
            st.markdown(r"**1. Cortante 1D Dir. B:** $\phi V_c \ge V_u$")
            if ok_1way_B:
                st.success(f" OK Dir B: $\\phi V_c = {phi_Vc_1way_B:.1f}$ $\\ge {Vu_1way_B:.1f}$ kN")
            else:
                st.error(f" FALLA Dir B: $\\phi V_c = {phi_Vc_1way_B:.1f}$ $< {Vu_1way_B:.1f}$ kN")
                
            st.markdown(r"**1b. Cortante 1D Dir. L:** $\phi V_c \ge V_u$")
            if ok_1way_L:
                st.success(f" OK Dir L: $\\phi V_c = {phi_Vc_1way_L:.1f}$ $\\ge {Vu_1way_L:.1f}$ kN")
            else:
                st.error(f" FALLA Dir L: $\\phi V_c = {phi_Vc_1way_L:.1f}$ $< {Vu_1way_L:.1f}$ kN $\\rightarrow$ **Aumentar H**")

        with c2d2:
            st.markdown(r"**2. Punzonamiento:** $\phi V_c \ge V_{up}$")
            if ok_punz:
                st.success(f" OK Punzonamiento: $\\phi V_c = {phi_Vc_punz:.1f}$ $\\ge {Vu_punz:.1f}$ kN")
            else:
                st.error(f" FALLA Punzonamiento: $\\phi V_c = {phi_Vc_punz:.1f}$ $< {Vu_punz:.1f}$ kN $\\rightarrow$ **Aumentar H o Columna**")
        
        st.markdown("---")
        
        estado_tension = " Compresión Total (e ≤ B/6)" if qu_min >= 0 else "⚠ Levantamiento"
        
        # Cálculo de longitud de desarrollo l_dh (NSR-10 C.12.5) para gancho 90°
        # l_dh = (0.24 * fy / sqrt(f'c)) * db_mm  [resultado en mm]
        ldh_req_mm = (0.24 * fy_basico / math.sqrt(fc_basico)) * db_bar_z
        ldh_req_cm = max(15.0, 8 * (db_bar_z/10.0), ldh_req_mm / 10.0)
        # Longitud disponible en la zapata desde la cara de la columna (en la dirección más crítica)
        L_disp_B_cm = ((B_use - c1_col/100.0) / 2.0) * 100.0 - recub_z
        L_disp_L_cm = ((L_use - c2_col/100.0) / 2.0) * 100.0 - recub_z
        L_disp_min_cm = min(L_disp_B_cm, L_disp_L_cm)
        ok_ldh = L_disp_min_cm >= ldh_req_cm

        data_res = [
            {"Revisión": "Geometría Propuesta", "Solicitado": f"Area Req = {Area_req:.2f} m²", "Capacidad/Provisto": f"Area Prov. = {A_use:.2f} m²", "Estado": " OK" if A_use>=Area_req else "⚠ Subdimensionado"},
            {"Revisión": "Pres. Contacto qu", "Solicitado": f"Max: {qu_max:.2f} kPa", "Capacidad/Provisto": f"Min: {qu_min:.2f} kPa", "Estado": estado_tension},
            {"Revisión": "Flexión Dir. B", "Solicitado": f"Mu_B = {Mu_flex_B:.1f} kN-m", "Capacidad/Provisto": f"As_B = {As_req_B:.1f} cm² → {n_barras_B} {bar_z} c/{sep_B:.1f}cm", "Estado": " OK" if disc_B>0 else " Rompe en compresión"},
            {"Revisión": "Flexión Dir. L", "Solicitado": f"Mu_L = {Mu_flex_L:.1f} kN-m", "Capacidad/Provisto": f"As_L = {As_req_L:.1f} cm² → {n_barras_L} {bar_z} c/{sep_L:.1f}cm", "Estado": " OK" if disc_L>0 else " Rompe en compresión"},
            {"Revisión": "Anclaje Gancho 90° (C.12)", "Solicitado": f"ldh req: {ldh_req_cm:.1f} cm", "Capacidad/Provisto": f"L_disp zapata: {L_disp_min_cm:.1f} cm", "Estado": " OK" if ok_ldh else " Aumentar B o L"},
        ]
        st.table(pd.DataFrame(data_res))

        area_ok = A_use >= Area_req
        if not area_ok:
            st.error(
                f" **ÁREA INSUFICIENTE** — Requerida: {Area_req:.2f} m² | "
                f"Provista: {A_use:.2f} m². Aumenta B o L."
            )

        # B4 aviso si se activó el área efectiva Meyerhof
        if _meyerhof_info:
            st.warning(_meyerhof_info)

        # ═══════════════════════════════════════════════════════════════════
        # A1 — FS VOLCAMIENTO Y DESLIZAMIENTO (NSR-10 H.4)
        # ═══════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("###  Estabilidad Global — Volcamiento y Deslizamiento (NSR-10 H.4)")
        with st.expander(" Parámetros de estabilidad", expanded=True):
            _c_fs1, _c_fs2, _c_fs3 = st.columns(3)
            H_horiz = _c_fs1.number_input("Carga horizontal H [kN]", 0.0, 5000.0,
                                          st.session_state.get("z_Hhoriz", 0.0), 10.0, key="z_Hhoriz")
            delta_ang = _c_fs2.number_input("Ángulo fricción cimentación δ [°] (≈ ²⁄₃φ)",
                                            0.0, 45.0, st.session_state.get("z_delta", phi_ang*2/3), 1.0, key="z_delta")
            # [fix_z_delta] eliminado: st.session_state["z_delta"] = delta_ang  (el widget key='z_delta' ya gestiona session_state)
            Pp_pasivo = _c_fs3.number_input("Empuje pasivo Ep [kN] (si hay muro adyacente)", 0.0, 5000.0, 0.0, 10.0)

        # Carga vertical total de servicio (peso zapata + suelo + carga)
        W_total = P_svc + (B_use * L_use * Df_z * gamma_prom)   # kN (usa gamma_prom del panel)

        # --- FS VOLCAMIENTO (referencia al borde de la zapata) ---
        # Momento estabilizador = P_svc * B/2  (carga vertical actúa en el centro)
        # Momento volcador     = H_horiz * (Df_z + H_zap/100)
        M_estab = W_total * (B_use / 2.0)                  # kN·m (respecto al borde más comprometido)
        arm_volc = Df_z + H_zap / 100.0                    # m  (brazo desde el punto de giro)
        M_volc   = H_horiz * arm_volc if H_horiz > 0 else 0.0
        FS_volc  = M_estab / M_volc if M_volc > 0 else 999.0
        ok_volc  = FS_volc >= 1.5

        # --- FS DESLIZAMIENTO ---
        delta_rad = math.radians(delta_ang)
        FR        = W_total * math.tan(delta_rad) + Pp_pasivo  # kN (fuerza resistente)
        FS_desl   = FR / H_horiz if H_horiz > 0 else 999.0
        ok_desl   = FS_desl >= 1.5

        _col_v, _col_d = st.columns(2)
        with _col_v:
            st.markdown("**Volcamiento:**")
            fs_v_disp = "∞" if M_volc == 0 else f"{FS_volc:.2f}"
            st.metric("FS Volcamiento", fs_v_disp, delta=f"Req. ≥ 1.50",
                      delta_color="normal" if ok_volc else "inverse")
            if ok_volc:
                st.success(f" FSv = {fs_v_disp} ≥ 1.50  —  M_estab={M_estab:.1f} / M_volc={M_volc:.1f} kN·m")
            else:
                st.error(f" FSv = {fs_v_disp} < 1.50  —  Aumentar B o Df, o reducir H_horiz")
        with _col_d:
            st.markdown("**Deslizamiento:**")
            fs_d_disp = "∞" if H_horiz == 0 else f"{FS_desl:.2f}"
            st.metric("FS Deslizamiento", fs_d_disp, delta=f"Req. ≥ 1.50",
                      delta_color="normal" if ok_desl else "inverse")
            if ok_desl:
                st.success(f" FSd = {fs_d_disp} ≥ 1.50  —  FR={FR:.1f} / H={H_horiz:.1f} kN")
            elif H_horiz == 0:
                st.info("ℹ Ingresa H horizontal > 0 para calcular deslizamiento")
            else:
                st.error(f" FSd = {fs_d_disp} < 1.50  —  Considerar llave de corte o aumentar Df")

        # Actualizar data_res con estabilidad
        st.caption(f"δ = {delta_ang:.1f}° | W_total = {W_total:.1f} kN | b. estabilizador = {B_use/2.0:.2f} m | brazo volcador(H) = {arm_volc:.2f} m")

        # ═══════════════════════════════════════════════════════════════════
        # A2 — MAPA DE CALOR PLOTLY 3D — qu(x,y)
        # ═══════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("###  Distribución de Presiones bajo la Zapata — qu(x,y)")
        with st.expander(" Mapa de calor 3D de esfuerzos de contacto", expanded=True):
            _nx, _ny = 30, 30
            _x_grid = np.linspace(-B_use/2, B_use/2, _nx)
            _y_grid = np.linspace(-L_use/2, L_use/2, _ny)
            _Xm, _Ym = np.meshgrid(_x_grid, _y_grid)
            _Qm = P_ult / A_use + (M_ult_L * _Xm / Iy) + (M_ult_B * _Ym / Ix)

            # Si hay zona negativa → zona de levantamiento (clip a 0 para representación)
            _tiene_tension = bool(np.any(_Qm < 0))
            _Qm_plot = np.where(_Qm < 0, 0, _Qm)   # clip visual

            _fig_heat = go.Figure()

            # Superficie 3D
            _r2 = max(float(np.max(_Qm_plot)) - (float(np.min(_Qm_plot[_Qm_plot > 0])) if np.any(_Qm_plot > 0) else 0), 1.0)
            _cmin2 = max(0.0, float(np.max(_Qm_plot)) - _r2 * 4)
            if _r2 < 5.0:
                _cmin2 = 0.0

            _fig_heat.add_trace(go.Surface(
                x=_x_grid, y=_y_grid, z=_Qm_plot,
                colorscale="RdYlGn_r",
                cmin=_cmin2, cmax=float(np.max(_Qm_plot)) * 1.02,
                colorbar=dict(title=dict(text="qu [kPa]", font=dict(color="white")),
                              tickfont=dict(color="white")),
                opacity=0.9,
                name="qu(x,y)"
            ))

            # Punto qu_max
            rango_real_iso = float(np.max(_Qm_plot)) - float(np.min(_Qm_plot[_Qm_plot > 0])) if np.any(_Qm_plot > 0) else 0
            if rango_real_iso > 1.0:
                _imax = np.unravel_index(np.argmax(_Qm), _Qm.shape)
                _fig_heat.add_trace(go.Scatter3d(
                    x=[_x_grid[_imax[1]]], y=[_y_grid[_imax[0]]], z=[float(_Qm[_imax])],
                    mode="markers+text",
                    marker=dict(color="#ff4444", size=8, symbol="diamond"),
                    text=[f"qu_max={qu_max:.1f} kPa"],
                    textfont=dict(color="white"),
                    name=f"qu_max = {qu_max:.1f} kPa"
                ))

            # Columna proyectada
            _c1m = c1_col / 100.0; _c2m = c2_col / 100.0
            _cx = [-_c1m/2, _c1m/2, _c1m/2, -_c1m/2, -_c1m/2]
            _cy = [-_c2m/2, -_c2m/2, _c2m/2, _c2m/2, -_c2m/2]
            _i_col2 = np.argmin(np.abs(_x_grid - 0))
            _j_col2 = np.argmin(np.abs(_y_grid - 0))
            _z_col = [float(_Qm_plot[_j_col2, _i_col2]) * 1.005] * 5
            _fig_heat.add_trace(go.Scatter3d(
                x=_cx, y=_cy, z=_z_col,
                mode="lines",
                line=dict(color="white", width=4),
                name="Columna"
            ))

            _fig_heat.update_layout(
                scene=dict(
                    xaxis_title="B [m]", yaxis_title="L [m]", zaxis_title="qu [kPa]",
                    bgcolor="#0f1117",
                    xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
                    zaxis=dict(gridcolor="#333"),
                    camera=dict(eye=dict(x=1.8, y=1.8, z=1.6))
                ),
                paper_bgcolor="#0f1117", font=dict(color="white"),
                margin=dict(l=0, r=0, b=0, t=40), height=500,
                title=dict(text=f"qu(x,y) — qu_max={qu_max:.1f} kPa | qu_min={qu_min:.1f} kPa"
                               + (" | ⚠ ZONA EN LEVANTAMIENTO" if _tiene_tension else " |  Compresión total"),
                           font=dict(color="#ffdd44" if _tiene_tension else "#44ff88")),
                showlegend=True,
            )
            st.plotly_chart(_fig_heat, use_container_width=True)
            if abs(qu_max - qu_min) < 1.0:
                st.info(
                    " **Distribución uniforme** — qu = "
                    f"{qu_max:.1f} kPa constante en toda la huella. "
                    "El gráfico 3D cobra valor cuando ingresas momentos Mu ≠ 0 "
                    "para ver la variación de presiones."
                )
            else:
                if not _tiene_tension:
                    st.warning(
                        f"⚠ **Distribución trapezoidal** — "
                        f"qu_max = {qu_max:.1f} kPa | qu_min = {qu_min:.1f} kPa. "
                        f"Excentricidad activa en la zapata."
                    )
                else:
                    st.error(
                        f" **Levantamiento parcial** — qu_min = {qu_min:.1f} kPa < 0. "
                        "Parte de la zapata no está en contacto con el suelo. Considere aumentar dimensiones "
                        "o activar el método de Área Efectiva Meyerhof (Bloque B4 disponible abajo)."
                    )

        # ═══════════════════════════════════════════════════════════════════
        # A3 — DISEÑO AUTOMÁTICO ITERATIVO DE H
        # ═══════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("### ⚙ Optimizador de Espesor H (Diseño Automático Iterativo)")
        with st.expander(" Encontrar H mínimo que cumple cortante y punzonamiento", expanded=False):
            st.info("El optimizador busca el menor H [cm] (en pasos de 5 cm) que satisface simultáneamente "
                    "Cortante 1D (Dir.B), Cortante 1D (Dir.L) y Punzonamiento, con los materiales y cargas actuales.")
            _H_min_check = st.number_input("H mínimo a considerar [cm]", 20.0, 80.0, 20.0, 5.0, key="z_opt_hmin")
            _H_max_check = st.number_input("H máximo a considerar [cm]", 50.0, 200.0, 120.0, 5.0, key="z_opt_hmax")

            if st.button("▶ Ejecutar optimizador de H", type="primary"):
                _H_vals   = np.arange(_H_min_check, _H_max_check + 5, 5)
                _res_iter = []
                _H_optimo = None

                for _Hi in _H_vals:
                    _di  = _Hi - recub_z - (db_bar_z / 10.0)          # peralte efectivo cm
                    _dim = _di / 100.0                                   # en metros
                    if _di <= 0:
                        continue

                    # Cortante 1D Dir.B
                    _xc_b = lv_b - _dim
                    _Vu_b = 0.0
                    if _xc_b > 0:
                        _yv = np.linspace(-L_use/2, L_use/2, 50)
                        _xv = np.linspace(_xc_b, lv_b, 50)
                        _dx = (lv_b - _xc_b) / 50; _dy = L_use / 50
                        for _xi in _xv:
                            for _yi in _yv:
                                _qxy = q_at(_xi, _yi)
                                if _qxy > 0: _Vu_b += _qxy * _dx * _dy
                    _phiVc_b = phi_v * 0.17 * math.sqrt(fc_basico) * (L_use*1000) * (_di*10) / 1000.0

                    # Cortante 1D Dir.L
                    _yc_l = lv_l - _dim
                    _Vu_l = 0.0
                    if _yc_l > 0:
                        _xv2 = np.linspace(-B_use/2, B_use/2, 50)
                        _yv2 = np.linspace(_yc_l, lv_l, 50)
                        _dx2 = B_use / 50; _dy2 = (_yc_l and (lv_l - _yc_l) / 50)
                        for _xi in _xv2:
                            for _yi in _yv2:
                                _qxy = q_at(_xi, _yi)
                                if _qxy > 0: _Vu_l += _qxy * _dx2 * _dy2
                    _phiVc_l = phi_v * 0.17 * math.sqrt(fc_basico) * (B_use*1000) * (_di*10) / 1000.0

                    # Punzonamiento
                    _bo1 = c1_col/100.0 + _dim; _bo2 = c2_col/100.0 + _dim
                    if pos_col_iso == "Interior":
                        _bo = 2*(_bo1 + _bo2); _alphas = 40
                    elif pos_col_iso == "Borde (eje X)":
                        _bo = 2*_bo1 + _bo2 - _dim/2.0; _alphas = 30
                    elif pos_col_iso == "Borde (eje Y)":
                        _bo = 2*_bo2 + _bo1 - _dim/2.0; _alphas = 30
                    else: # Esquina
                        _bo = _bo1 - _dim/2.0 + _bo2 - _dim/2.0; _alphas = 20
                    _Ap  = _bo1 * _bo2
                    _Vup = P_ult - qu_avg * _Ap
                    _betac = max(c1_col, c2_col) / max(min(c1_col, c2_col), 1e-3)
                    _Vc3p = 0.083*(2 + _alphas*(_di*10)/(_bo*1000))*math.sqrt(fc_basico)
                    _vc_p = min(0.33*math.sqrt(fc_basico), 0.17*(1+2/_betac)*math.sqrt(fc_basico), _Vc3p)
                    _phiVc_p = phi_v * _vc_p * (_bo*1000) * (_di*10) / 1000.0

                    _ok_b = _phiVc_b >= _Vu_b
                    _ok_l = _phiVc_l >= _Vu_l
                    _ok_p = _phiVc_p >= _Vup
                    _cumple = _ok_b and _ok_l and _ok_p

                    _res_iter.append({
                        "H [cm]": int(_Hi), "d [cm]": f"{_di:.1f}",
                        "φVc_1B [kN]": f"{_phiVc_b:.1f}", "Vu_1B [kN]": f"{_Vu_b:.1f}",
                        "φVc_1L [kN]": f"{_phiVc_l:.1f}", "Vu_1L [kN]": f"{_Vu_l:.1f}",
                        "φVc_P [kN]": f"{_phiVc_p:.1f}", "Vu_P [kN]": f"{_Vup:.1f}",
                        "Estado": " CUMPLE" if _cumple else " FALLA"
                    })
                    if _cumple and _H_optimo is None:
                        _H_optimo = _Hi

                st.dataframe(pd.DataFrame(_res_iter), use_container_width=True, hide_index=True)

                if _H_optimo:
                    st.success(f" **H óptimo = {_H_optimo:.0f} cm** — Es el menor espesor que cumple todos los criterios "
                               f"estructurales con los materiales y cargas actuales.")
                    st.info(f" Ahora puede escribir **H = {_H_optimo:.0f} cm** en el input del panel principal y recalcular.")
                else:
                    st.error(f" Ningún H en el rango [{_H_min_check:.0f}–{_H_max_check:.0f}] cm cumple todos los criterios. "
                             f"Considere aumentar B×L o f'c.")

        # Grafico 2D esquemático
        with st.expander(" Ver Esquema de Armado 2D", expanded=False):
            fig_2d, ax_2d = plt.subplots(figsize=(5,5))
            fig_2d.patch.set_facecolor("#0f1117"); ax_2d.set_facecolor("#161b22")
            zap_rect = plt.Rectangle((-B_use/2, -L_use/2), B_use, L_use, fill=True, color="#2c3e50", ec="#3498db", lw=2)
            ax_2d.add_patch(zap_rect)
            col_rect = plt.Rectangle((-c1_col/200, -c2_col/200), c1_col/100, c2_col/100, fill=True, color="#7f8c8d", ec="white")
            ax_2d.add_patch(col_rect)
            # Acero dir B (paralelo a L)
            for r_b in np.linspace(-B_use/2 + recub_z/100, B_use/2 - recub_z/100, int(n_barras_B)):
                ax_2d.plot([r_b, r_b], [-L_use/2+0.05, L_use/2-0.05], color="#e74c3c", alpha=0.5, lw=1)
            # Acero dir L (paralelo a B)
            for r_l in np.linspace(-L_use/2 + recub_z/100, L_use/2 - recub_z/100, int(n_barras_L)):
                ax_2d.plot([-B_use/2+0.05, B_use/2-0.05], [r_l, r_l], color="#f1c40f", alpha=0.5, lw=1)
                
            ax_2d.set_xlim(-B_use/2 - 0.5, B_use/2 + 0.5)
            ax_2d.set_ylim(-L_use/2 - 0.5, L_use/2 + 0.5)
            ax_2d.set_aspect('equal')
            ax_2d.axis('off')
            ax_2d.set_title(f"Armadura Inferior\n{int(n_barras_B)} {bar_z} (B) / {int(n_barras_L)} {bar_z} (L)", color="white", fontsize=10)
            st.pyplot(fig_2d)
        
        # ── MEMORIA DE CÁLCULO COMPLETA ────────────────────────────────────
        doc_zap = Document()
        doc_zap.add_heading(f"MEMORIA DE CÁLCULO — ZAPATA {B_use:.2f}x{L_use:.2f} m", 0)
        doc_zap.add_paragraph(f"Fecha: {_dt.datetime.now().strftime('%d/%m/%Y %H:%M')}")
        doc_zap.add_paragraph(f"Norma Estructural: {norma_sel}")
        doc_zap.add_paragraph(f"Elaborado con: StructuroPro — Módulo Zapatas NSR-10/ACI-318/Multi-Norma")
        doc_zap.add_heading("1. MATERIALES", level=1)
        doc_zap.add_paragraph(f"  f'c = {fc_basico} MPa  |  fy = {fy_basico} MPa  |  Recubrimiento = {recub_z} cm")
        doc_zap.add_paragraph(f"  Varilla seleccionada: {bar_z}  |  Área unitaria = {REBAR_DICT[bar_z]['area']:.3f} cm²  |  db = {REBAR_DICT[bar_z]['db']:.1f} mm")
        doc_zap.add_heading("2. CARGAS APLICADAS", level=1)
        doc_zap.add_paragraph(f"  Servicio: Ps = {P_svc:.1f} kN, Ms_B = {M_svc_B:.1f} kN·m, Ms_L = {M_svc_L:.1f} kN·m")
        doc_zap.add_paragraph(f"  Últimas: Pu = {P_ult:.1f} kN, Mu_B = {M_ult_B:.1f} kN·m, Mu_L = {M_ult_L:.1f} kN·m")
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
        doc_zap.add_paragraph(f"  CORTANTE UNIDIRECCIONAL (Viga) — Dir B:")
        doc_zap.add_paragraph(f"    φVc = {phi_Vc_1way_B:.1f} kN  {'≥' if ok_1way_B else '<'}  Vu = {Vu_1way_B:.1f} kN  → {' OK' if ok_1way_B else ' Aumentar H'}")
        doc_zap.add_paragraph(f"  CORTANTE UNIDIRECCIONAL (Viga) — Dir L:")
        doc_zap.add_paragraph(f"    φVc = {phi_Vc_1way_L:.1f} kN  {'≥' if ok_1way_L else '<'}  Vu = {Vu_1way_L:.1f} kN  → {' OK' if ok_1way_L else ' Aumentar H'}")
        doc_zap.add_paragraph(f"  PUNZONAMIENTO (Bidireccional):")
        doc_zap.add_paragraph(f"    bo = {bo_perim:.3f} m  |  φVc = {phi_Vc_punz:.1f} kN  {'≥' if ok_punz else '<'}  Vup = {Vu_punz:.1f} kN  → {' OK' if ok_punz else ' Aumentar H'}")
        doc_zap.add_heading("6. DISEÑO A FLEXIÓN — ACERO DE REFUERZO", level=1)
        doc_zap.add_paragraph(f"  DIR. B (malla sobre el ancho L={L_use:.2f}m):")
        doc_zap.add_paragraph(f"    Mu_B = {Mu_flex_B:.1f} kN·m  |  As_B = {As_req_B:.2f} cm²  |  ρ_B = {rho_use_B:.4f}")
        doc_zap.add_paragraph(f"    Arreglo: {n_barras_B} varillas {bar_z}  c/ {sep_B:.1f} cm  {' OK' if disc_B>0 else ' Aumentar H'}")
        doc_zap.add_paragraph(f"  DIR. L (malla sobre el ancho B={B_use:.2f}m):")
        doc_zap.add_paragraph(f"    Mu_L = {Mu_flex_L:.1f} kN·m  |  As_L = {As_req_L:.2f} cm²  |  ρ_L = {rho_use_L:.4f}")
        doc_zap.add_paragraph(f"    Arreglo: {n_barras_L} varillas {bar_z}  c/ {sep_L:.1f} cm  {' OK' if disc_L>0 else ' Aumentar H'}")
        doc_zap.add_paragraph(f"  DETALLES DE DOBLADO (Gancho 90° estándar ACI/NSR-10):")
        doc_zap.add_paragraph(f"    Diámetro mín. de doblez = {D_doblez_cm:.1f} cm")
        doc_zap.add_paragraph(f"    Extensión recta después de la curva = {L_ext_gancho_cm:.1f} cm")
        doc_zap.add_paragraph(f"    Altura del gancho ajustada a zapata = {L_gancho_real_cm:.1f} cm")
        doc_zap.add_heading("7. CANTIDADES DE MATERIALES (APU)", level=1)
        _area_m2_doc = REBAR_DICT[bar_z]["area"] * 1e-4
        # Longitud exacta considerando tramo recto, curva y extensión
        # Tramo recto + 2 * (desarrollo curva + extension)
        _long_gancho_m = ( (math.pi * radio_doblez_cm / 2) + L_ext_gancho_cm ) / 100.0
        _long_var_B = L_use - 2*(recub_z/100.0) + 2*_long_gancho_m
        _long_var_L = B_use - 2*(recub_z/100.0) + 2*_long_gancho_m
        _pe_B = n_barras_B * _long_var_B * _area_m2_doc * 7850
        _pe_L = n_barras_L * _long_var_L * _area_m2_doc * 7850
        _pe_tot = _pe_B + _pe_L
        _vol_exc = (B_use + 0.5) * (L_use + 0.5) * Df_z
        _vol_conc = B_use * L_use * (H_zap/100.0)
        doc_zap.add_paragraph(f"  Excavación = {_vol_exc:.2f} m³")
        doc_zap.add_paragraph(f"  Concreto   = {_vol_conc:.2f} m³")
        doc_zap.add_paragraph(f"  Acero Dir.B = {_pe_B:.1f} kg  |  Acero Dir.L = {_pe_L:.1f} kg  |  Total = {_pe_tot:.1f} kg")
        doc_zap.add_paragraph(f"  Cuantía = {(_pe_tot/_vol_conc) if _vol_conc>0 else 0:.1f} kg/m³")

        # Integrar Costos APU al Reporte
        _apu_doc = st.session_state.get("apu_config", {})
        _mon_d = _apu_doc.get("moneda", "COP")
        _p_cem_d = _apu_doc.get("cemento", 32000.0)
        _p_ace_d = _apu_doc.get("acero",   4500.0)
        _p_are_d = _apu_doc.get("arena",   85000.0)
        _p_gra_d = _apu_doc.get("grava",   95000.0)
        _p_exc_d = _apu_doc.get("costo_excav_m3", 25000.0)
        
        _bultos_d = _vol_conc * 350 / 50.0
        _vol_are_d = _vol_conc * 0.55
        _vol_gra_d = _vol_conc * 0.80
        
        _c_exc_d = _vol_exc * _p_exc_d
        _c_cem_d = _bultos_d * _p_cem_d
        _c_are_d = _vol_are_d * _p_are_d
        _c_gra_d = _vol_gra_d * _p_gra_d
        _c_ace_d = _pe_tot * _p_ace_d
        _c_tot_doc = _c_exc_d + _c_cem_d + _c_are_d + _c_gra_d + _c_ace_d
        
        doc_zap.add_heading("8. PRESUPUESTO ESTIMADO (APU) — DESGLOSE COMPLETO", level=1)
        doc_zap.add_paragraph(f"  Moneda Base: {_mon_d}\n")
        doc_zap.add_paragraph(f"  A. MATERIALES DIRECTOS:")
        doc_zap.add_paragraph(f"     - Excavación:      {_vol_exc:.2f} m³   × {_p_exc_d:,.0f}/m³  = {_c_exc_d:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"     - Cemento:         {_bultos_d:.1f} blt  × {_p_cem_d:,.0f}/blt = {_c_cem_d:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"     - Arena:           {_vol_are_d:.2f} m³   × {_p_are_d:,.0f}/m³  = {_c_are_d:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"     - Gravilla:        {_vol_gra_d:.2f} m³   × {_p_gra_d:,.0f}/m³  = {_c_gra_d:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"     - Acero Refuerzo:  {_pe_tot:.1f} kg   × {_p_ace_d:,.0f}/kg  = {_c_ace_d:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"  ─────────────────────────────────────────────────")
        doc_zap.add_paragraph(f"  SUBTOTAL MATERIALES DIRECTOS = {_c_tot_doc:,.0f} {_mon_d}")

        # Calcular Mano de Obra y demás con valores del APU si están disponibles
        _apu_doc_cfg = st.session_state.get("apu_config", {})
        _pct_he_doc  = _apu_doc_cfg.get("pct_herramienta", 0.05)
        _pct_aiu_doc = _apu_doc_cfg.get("pct_aui", 0.30)
        _pct_uti_doc = _apu_doc_cfg.get("pct_util", 0.05)
        _pct_iva_doc = _apu_doc_cfg.get("iva", 0.19)
        _dia_mo_doc  = _apu_doc_cfg.get("costo_dia_mo", 69333.33)
        _vol_conc_doc = B_use * L_use * (H_zap / 100.0)
        _vol_exc_doc2 = (B_use + 0.5) * (L_use + 0.5) * Df_z
        _dias_mo_doc = (_pe_tot * 0.04) + (_vol_conc_doc * 0.4) + (_vol_exc_doc2 * 0.3)
        _c_mo_doc    = _dias_mo_doc * _dia_mo_doc
        _cd_doc      = _c_tot_doc + _c_mo_doc
        _herr_doc    = _c_mo_doc * _pct_he_doc
        _aiu_doc_val = _cd_doc * _pct_aiu_doc
        _util_doc    = _cd_doc * _pct_uti_doc
        _iva_doc_val = _util_doc * _pct_iva_doc
        _gran_total_doc = _cd_doc + _herr_doc + _aiu_doc_val + _iva_doc_val

        doc_zap.add_paragraph(f"")
        doc_zap.add_paragraph(f"  B. MANO DE OBRA:")
        doc_zap.add_paragraph(f"     {_dias_mo_doc:.2f} días-obra × {_dia_mo_doc:,.0f} {_mon_d}/día = {_c_mo_doc:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"  ─────────────────────────────────────────────────")
        doc_zap.add_paragraph(f"  COSTO DIRECTO (CD) = Mat. + MO = {_cd_doc:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"")
        doc_zap.add_paragraph(f"  C. CARGAS INDIRECTAS:")
        doc_zap.add_paragraph(f"     - Herramienta Menor ({_pct_he_doc*100:.1f}% MO): {_herr_doc:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"     - A.I.U. ({_pct_aiu_doc*100:.0f}% CD):         {_aiu_doc_val:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"     - IVA s/ Utilidad ({_pct_iva_doc*100:.0f}% × Util.): {_iva_doc_val:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"  ═════════════════════════════════════════════════")
        doc_zap.add_paragraph(f"  GRAN TOTAL DEL PROYECTO = {_gran_total_doc:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"  (Diferencia Gran Total vs Materiales = {_gran_total_doc - _c_tot_doc:,.0f} {_mon_d}")
        doc_zap.add_paragraph(f"   = MO + Herramienta + AIU + IVA)")

        # FI-6: ESTABILIDAD GLOBAL — VOLCAMIENTO Y DESLIZAMIENTO ─────────────
        # Variables FS_volc / FS_desl calculadas en el bloque A1 (L1616-1668)
        doc_zap.add_heading("8a. ESTABILIDAD GLOBAL — VOLCAMIENTO Y DESLIZAMIENTO (NSR-10 H.4)", level=1)
        try:
            doc_zap.add_paragraph(
                f"  Carga horizontal H = {H_horiz:.1f} kN  |  "
                f"Angulo friccion cimentacion delta = {delta_ang:.1f} deg  |  "
                f"Peso total W = {W_total:.1f} kN"
            )
            doc_zap.add_paragraph(
                f"  FS Volcamiento  = {FS_volc:.2f}  "
                f"{'[OK] Cumple' if ok_volc else '[X] No cumple'} (req. >= 1.50)  |  "
                f"M_estabilizador = {M_estab:.1f} kN·m  |  M_volcador = {M_volc:.1f} kN·m"
            )
            doc_zap.add_paragraph(
                f"  FS Deslizamiento = {FS_desl:.2f}  "
                f"{'[OK] Cumple' if ok_desl else '[X] No cumple'} (req. >= 1.50)  |  "
                f"FR = {FR:.1f} kN  |  H_horiz = {H_horiz:.1f} kN"
            )
            if Pp_pasivo > 0:
                doc_zap.add_paragraph(f"  Empuje pasivo considerado: Ep = {Pp_pasivo:.1f} kN")
        except Exception:
            doc_zap.add_paragraph("  [Estabilidad no calculada — ingrese H horizontal en el panel de estabilidad]")
        # ───────────────────────────────────────────────────────────────────────

        # Si hay asentamiento guardado, agregarlo
        if "asentamiento" in st.session_state:
            doc_zap.add_heading("8b. ASENTAMIENTO ELÁSTICO ESTIMADO", level=1)
            doc_zap.add_paragraph(f"  Asentamiento inmediato (estimado) = {st.session_state.asentamiento:.1f} mm")

            
        doc_zap.add_heading("9. ANEXO GRÁFICO (ESQUEMAS GENERADOS)", level=1)
        # Función auxiliar para incrustar figuras
        def _add_plt_to_doc(fig_obj, width_in=6.0):
            img_io = io.BytesIO()
            fig_obj.savefig(img_io, format='png', bbox_inches='tight', facecolor=fig_obj.get_facecolor())
            img_io.seek(0)
            doc_zap.add_picture(img_io, width=Inches(width_in))
            
        doc_zap.add_paragraph("Anexo A. Distribución Boussinesq (Perfil Vertical y Perfiles Horizontales):")
        try: _add_plt_to_doc(fig_b)
        except NameError: pass
        
        doc_zap.add_paragraph("\nAnexo B. Mecanismo de Falla (Terzaghi/Meyerhof) y Bulbo de Presiones:")
        try: _add_plt_to_doc(fig_tb)
        except NameError: pass
        
        doc_zap.add_paragraph("\nAnexo C. Profundidad de Exploración Normativa (NSR-10, criterio 10% q_0):")
        try: _add_plt_to_doc(fig_ex)
        except NameError: pass
        
        doc_zap.add_paragraph("\nAnexo D. Esquema 2D de Acero de Refuerzo en Planta:")
        try: _add_plt_to_doc(fig_2d, width_in=4.5)
        except NameError: pass

        f_zap_io = io.BytesIO()
        doc_zap.save(f_zap_io)
        f_zap_io.seek(0)
        # ── EXPORTACIÓN DXF ────────────────────────────────────────────────
        import datetime as _dt_dxf
        doc_dxf = ezdxf.new('R2010')
        doc_dxf.units = ezdxf.units.CM
        
        ESCALA = 20
        doc_dxf.header['$DIMSCALE'] = ESCALA
        doc_dxf.header['$LTSCALE'] = 0.02
        doc_dxf.header['$TEXTSIZE'] = 0.08 * ESCALA
        doc_dxf.header['$DIMTXT'] = 0.06 * ESCALA
        TH = 0.06 * ESCALA
        TH_TITLE = 0.1 * ESCALA
        
        msp = doc_dxf.modelspace()
        
        _layers = [
            ('CONCRETO', 7), ('ACERO_B', 1), ('ACERO_L', 3),
            ('TEXTO', 2), ('EJES', 8), ('COTAS', 4),
            ('ROTULO', 4), ('HATCH', 254),
        ]
        for _ln, _lc in _layers:
            if _ln not in doc_dxf.layers: doc_dxf.layers.add(_ln, color=_lc)
        
        B_cm = B_use * 100; L_cm = L_use * 100; Hc = H_zap; rec = recub_z
        db_cm = db_bar_z / 10.0; radio_dob = D_doblez_cm / 2.0; L_ext = L_ext_gancho_cm
        c1c = c1_col; c2c = c2_col
        
        def _rect(ox, oy, w, h, lay):
            msp.add_lwpolyline([(ox,oy),(ox+w,oy),(ox+w,oy+h),(ox,oy+h)], close=True, dxfattribs={'layer': lay})
        
        def _text(x, y, txt, lay, h=None, ha='left'):
            msp.add_text(txt, dxfattribs={'layer': lay, 'height': h or TH, 'halign': {'left':0,'center':4,'right':2}[ha], 'insert': (x, y)})
            
        def _dim_horiz(x1, x2, y_dim, txt, lay='COTAS'):
            ans = TH * 0.5
            for _x in (x1, x2):
                msp.add_line((_x, y_dim - ans), (_x, y_dim + ans), dxfattribs={'layer': lay})
                msp.add_line((_x, y_dim), (_x, y_dim - TH*2), dxfattribs={'layer': lay, 'color': 8})
            msp.add_line((x1, y_dim), (x2, y_dim), dxfattribs={'layer': lay})
            _text((x1+x2)/2, y_dim + TH*0.5, txt, lay, ha='center')
            
        def _dim_vert(x_dim, y1, y2, txt, lay='COTAS'):
            ans = TH * 0.5
            for _y in (y1, y2):
                msp.add_line((x_dim - ans, _y), (x_dim + ans, _y), dxfattribs={'layer': lay})
                msp.add_line((x_dim, _y), (x_dim + TH*2, _y), dxfattribs={'layer': lay, 'color': 8})
            msp.add_line((x_dim, y1), (x_dim, y2), dxfattribs={'layer': lay})
            _text(x_dim - TH*0.5, (y1+y2)/2, txt, lay, ha='right')
            
        def _hook_arc(ox, oy, side, lay):
            r = radio_dob
            if side == 'left':
                msp.add_arc((ox + r, oy + r), r, start_angle=180, end_angle=270, dxfattribs={'layer': lay})
                msp.add_line((ox, oy + r), (ox, oy + r + L_ext), dxfattribs={'layer': lay})
            else:
                msp.add_arc((ox - r, oy + r), r, start_angle=270, end_angle=0, dxfattribs={'layer': lay})
                msp.add_line((ox, oy + r), (ox, oy + r + L_ext), dxfattribs={'layer': lay})
        
        ex_A = 0; ey_A = 0
        _rect(ex_A, ey_A, B_cm, Hc, 'CONCRETO')
        _rect(ex_A + (B_cm - c1c) / 2, ey_A + Hc, c1c, 50, 'CONCRETO')
        y_bar_A = ey_A + rec + db_cm/2
        for j in range(int(n_barras_L)): msp.add_circle((ex_A + rec + j * sep_L, y_bar_A), db_cm/2, dxfattribs={'layer':'ACERO_L'})
        msp.add_line((ex_A + rec + radio_dob, y_bar_A), (ex_A + B_cm - rec - radio_dob, y_bar_A), dxfattribs={'layer':'ACERO_B'})
        _hook_arc(ex_A + rec, y_bar_A, 'left', 'ACERO_B'); _hook_arc(ex_A + B_cm - rec, y_bar_A, 'right', 'ACERO_B')
        
        ex_B = B_cm + 60; ey_B = 0
        _rect(ex_B, ey_B, L_cm, Hc, 'CONCRETO')
        _rect(ex_B + (L_cm - c2c) / 2, ey_B + Hc, c2c, 50, 'CONCRETO')
        y_bar_B = ey_B + rec + db_cm/2
        for i in range(int(n_barras_B)): msp.add_circle((ex_B + rec + i * sep_B, y_bar_B), db_cm/2, dxfattribs={'layer':'ACERO_B'})
        y_bar_L = y_bar_B + db_cm
        msp.add_line((ex_B + rec + radio_dob, y_bar_L), (ex_B + L_cm - rec - radio_dob, y_bar_L), dxfattribs={'layer':'ACERO_L'})
        _hook_arc(ex_B + rec, y_bar_L, 'left', 'ACERO_L'); _hook_arc(ex_B + L_cm - rec, y_bar_L, 'right', 'ACERO_L')
        
        px = 0; py = Hc + 80
        _rect(px, py, B_cm, L_cm, 'CONCRETO')
        _rect(px + (B_cm - c1c)/2, py + (L_cm - c2c)/2, c1c, c2c, 'CONCRETO')
        for i in range(int(n_barras_B)):
            yi = py + rec + i * sep_B
            msp.add_line((px + rec, yi), (px + B_cm - rec, yi), dxfattribs={'layer':'ACERO_B'})
        for j in range(int(n_barras_L)):
            xj = px + rec + j * sep_L
            msp.add_line((xj, py + rec), (xj, py + L_cm - rec), dxfattribs={'layer':'ACERO_L'})
        
        rot_w = 180; rot_h = 60; row_h = rot_h / 8; rot_x = max(B_cm + 60 + L_cm, B_cm) + 60; rot_y = -rot_h - 20
        _rect(rot_x, rot_y, rot_w, rot_h, 'ROTULO')
        msp.add_line((rot_x + 55, rot_y), (rot_x + 55, rot_y + rot_h), dxfattribs={'layer':'ROTULO'})
        _rotulo_filas = [
            ("PROYECTO", f"Zapata Aislada {B_use:.2f}×{L_use:.2f}m — H={H_zap:.0f}cm"),
            ("EMPRESA", "Konte Ingeniería"), ("DISEÑÓ", "StructuroPro"), ("NORMA", "NSR-10 / ACI 318-19"),
            ("ESCALA", f"1:{ESCALA}"), ("FECHA", _dt_dxf.date.today().strftime('%d/%m/%Y')),
            ("PLANO N°", "ZAP-001"), ("REVISIÓN", "R0")
        ]
        for i, (c, v) in enumerate(_rotulo_filas):
            yr = rot_y + rot_h - (i + 1) * row_h
            if i > 0: msp.add_line((rot_x, yr + row_h), (rot_x + rot_w, yr + row_h), dxfattribs={'layer':'ROTULO'})
            _text(rot_x + 2, yr + row_h*0.3, c, 'ROTULO', TH * 0.7); _text(rot_x + 57, yr + row_h*0.3, v, 'ROTULO', TH)
        
        # RÓTULO PERIMETRAL ICONTEC
        min_x_plano = -40; min_y_plano = min(rot_y - 10, -TH*25 - 20)
        max_x_plano = rot_x + rot_w + 20; max_y_plano = py + L_cm + 120
        _rect(min_x_plano, min_y_plano, max_x_plano - min_x_plano, max_y_plano - min_y_plano, 'ROTULO')
        _rect(min_x_plano+1, min_y_plano+1, max_x_plano - min_x_plano - 2, max_y_plano - min_y_plano - 2, 'ROTULO')
        
        _dxf_text = io.StringIO()
        doc_dxf.write(_dxf_text)
        _dxf_bytes = _dxf_text.getvalue().encode("utf-8")

        # ── EXPORTACIÓN IFC ────────────────────────────────────────────────
        if not _IFC_AVAILABLE:
            st.warning("⚠ ifcopenshell no instalado — ejecuta: `pip install ifcopenshell`")
        else:
            try:
                buf_ifc = ifc_export.ifc_zapata(
                    B_use*100, L_use*100, H_zap, fc_basico, fy_basico,
                    bar_z, db_bar_z, int(n_barras_B), bar_z, db_bar_z, int(n_barras_L),
                    recub_z, P_ult, norma_sel, "Proyecto NSR-10"
                )
            except Exception:
                buf_ifc = None

        # ── BOTONES INTELIGENTES (3 COLUMNAS) ──────────────────────────────
        st.markdown("---")
        st.write("####  Entregables")
        
        if not area_ok:
            st.warning("⚠ **Área insuficiente.** Corrige las dimensiones de la zapata para habilitar la exportación.")
            
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.download_button(" Memoria DOCX", data=f_zap_io,
                               file_name=f"Memoria_Zapata_{B_use:.1f}x{L_use:.1f}m.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True, disabled=not area_ok)
        with col_m2:
            st.download_button(" Plano DXF (ICONTEC)", data=_dxf_bytes,
                               file_name=f"Zapata_Aislada_{B_use:.1f}x{L_use:.1f}m.dxf",
                               mime="application/dxf",
                               use_container_width=True, disabled=not area_ok)
        with col_m3:
            if buf_ifc:
                st.download_button(" Modelo BIM (IFC)", data=buf_ifc,
                                   file_name=f"Zapata_Aislada_{B_use:.1f}x{L_use:.1f}m.ifc",
                                   mime="application/x-step",
                                   use_container_width=True, disabled=not area_ok)
    with tab_dwg:
        st.subheader(" Visualización 3D de la Fundación con Acero de Refuerzo")
        fig3d = go.Figure()

        Hz_m  = H_zap / 100.0
        rec_m = recub_z / 100.0
        db_m  = db_bar_z / 1000.0
        z_bar = rec_m + db_m / 2

        # Zapata
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

        # Medidas para ganchos en 3D
        _r_m = radio_doblez_cm / 100.0          # radio de curva en metros
        _ext_m = L_ext_gancho_cm / 100.0         # extensión recta en metros
        _hook_h = (math.pi * _r_m / 2) + _ext_m  # altura total del gancho (arco + recta)

        # Varillas Dir. B (barras corren en X=dirección B, se distribuyen en Y=dirección L)
        _ys_barB = np.linspace(-L_use/2 + rec_m, L_use/2 - rec_m, n_barras_B)
        _show_B = True
        _show_Bh = True
        for yi in _ys_barB:
            # Tramo recto horizontal
            fig3d.add_trace(go.Scatter3d(
                x=[-B_use/2 + rec_m, B_use/2 - rec_m], y=[yi, yi], z=[z_bar, z_bar],
                mode='lines', line=dict(color='#ff6b35', width=5),
                name='Acero Dir.B' if _show_B else None, showlegend=_show_B, legendgroup='aB'))
            _show_B = False
            # Gancho extremo -X (sube verticalmente)
            fig3d.add_trace(go.Scatter3d(
                x=[-B_use/2 + rec_m, -B_use/2 + rec_m], y=[yi, yi],
                z=[z_bar, z_bar + _hook_h],
                mode='lines', line=dict(color='#ff9a6c', width=3, dash='dot'),
                name='Ganchos Dir.B' if _show_Bh else None, showlegend=_show_Bh, legendgroup='aBh'))
            # Gancho extremo +X
            fig3d.add_trace(go.Scatter3d(
                x=[B_use/2 - rec_m, B_use/2 - rec_m], y=[yi, yi],
                z=[z_bar, z_bar + _hook_h],
                mode='lines', line=dict(color='#ff9a6c', width=3, dash='dot'),
                name=None, showlegend=False, legendgroup='aBh'))
            _show_Bh = False

        # Varillas Dir. L (barras corren en Y=dirección L, se distribuyen en X=dirección B)
        _xs_barL = np.linspace(-B_use/2 + rec_m, B_use/2 - rec_m, n_barras_L)
        _z_barL  = z_bar + db_m
        _hook_h_L = _hook_h + db_m   # ligeramente más alto porque van encima
        _show_L = True
        _show_Lh = True
        for xi in _xs_barL:
            # Tramo recto horizontal
            fig3d.add_trace(go.Scatter3d(
                x=[xi, xi], y=[-L_use/2 + rec_m, L_use/2 - rec_m], z=[_z_barL, _z_barL],
                mode='lines', line=dict(color='#ffd54f', width=5),
                name='Acero Dir.L' if _show_L else None, showlegend=_show_L, legendgroup='aL'))
            _show_L = False
            # Gancho extremo -Y (sube verticalmente)
            fig3d.add_trace(go.Scatter3d(
                x=[xi, xi], y=[-L_use/2 + rec_m, -L_use/2 + rec_m],
                z=[_z_barL, _z_barL + _hook_h_L],
                mode='lines', line=dict(color='#ffe57f', width=3, dash='dot'),
                name='Ganchos Dir.L' if _show_Lh else None, showlegend=_show_Lh, legendgroup='aLh'))
            # Gancho extremo +Y
            fig3d.add_trace(go.Scatter3d(
                x=[xi, xi], y=[L_use/2 - rec_m, L_use/2 - rec_m],
                z=[_z_barL, _z_barL + _hook_h_L],
                mode='lines', line=dict(color='#ffe57f', width=3, dash='dot'),
                name=None, showlegend=False, legendgroup='aLh'))
            _show_Lh = False

        fig3d.update_layout(
            scene=dict(aspectmode='data', xaxis_title='B (m)', yaxis_title='L (m)', zaxis_title='Z (m)',
                       bgcolor='#0f1117',
                       xaxis=dict(showgrid=True, gridcolor='#333'),
                       yaxis=dict(showgrid=True, gridcolor='#333'),
                       zaxis=dict(showgrid=True, gridcolor='#333')),
            margin=dict(l=0, r=0, b=0, t=30), height=550,
            showlegend=True, dragmode='turntable', paper_bgcolor='#0f1117', font=dict(color='white'),
            title=dict(text=f"Zapata {B_use:.2f}x{L_use:.2f}m | H={H_zap:.0f}cm | "
                           f"Dir.B: {n_barras_B}×{bar_z} c/{sep_B:.1f}cm | Dir.L: {n_barras_L}×{bar_z} c/{sep_L:.1f}cm",
                       font=dict(color='white')))
        st.plotly_chart(fig3d, use_container_width=True)
        
        st.markdown("---")
        st.write("#### Geometría de Zapata 2D")
        fig_z, ax_z = plt.subplots(figsize=(6, 4))
        ax_z.set_facecolor('#1a1a2e'); fig_z.patch.set_facecolor('#1a1a2e')
        ax_z.add_patch(patches.Rectangle((0,0), B_use*100, H_zap, linewidth=2, edgecolor='darkgray', facecolor='#4a4a6a'))
        pos_x_col = (B_use*100 - c1_col) / 2
        ax_z.add_patch(patches.Rectangle((pos_x_col, H_zap), c1_col, 50, linewidth=2, edgecolor='white', facecolor='#6a6a8a'))
        for i in range(n_barras_Z):
            xi = recub_z + i * separacion_S
            ax_z.add_patch(plt.Circle((xi, recub_z), db_bar_z/10, color='#ff6b35', zorder=5))
        # Dibujar perfil del doblez para la varilla principal (Dir B)
        # Tramo horizontal inferior
        _x_start = recub_z + radio_doblez_cm
        _x_end = B_use*100 - recub_z - radio_doblez_cm
        _y_bar = recub_z
        ax_z.add_patch(patches.Rectangle((_x_start, _y_bar - db_bar_z/20.0), _x_end - _x_start, db_bar_z/10.0, color='#ffd54f', zorder=4))
        
        # Gancho Izquierdo
        arc_izq = patches.Arc((_x_start, _y_bar + radio_doblez_cm), D_doblez_cm, D_doblez_cm, angle=180, theta1=90, theta2=180, color='#ffd54f', lw=3, zorder=4)
        ax_z.add_patch(arc_izq)
        ax_z.plot([recub_z, recub_z], [_y_bar + radio_doblez_cm, _y_bar + radio_doblez_cm + L_ext_gancho_cm], color='#ffd54f', lw=3, zorder=4)
        
        # Gancho Derecho
        arc_der = patches.Arc((_x_end, _y_bar + radio_doblez_cm), D_doblez_cm, D_doblez_cm, angle=270, theta1=90, theta2=180, color='#ffd54f', lw=3, zorder=4)
        ax_z.add_patch(arc_der)
        ax_z.plot([B_use*100 - recub_z, B_use*100 - recub_z], [_y_bar + radio_doblez_cm, _y_bar + radio_doblez_cm + L_ext_gancho_cm], color='#ffd54f', lw=3, zorder=4)
        
        # Cota del doblez
        ax_z.annotate(f"{L_ext_gancho_cm:.1f}cm", xy=(recub_z, _y_bar + radio_doblez_cm + L_ext_gancho_cm/2), xytext=(-15, _y_bar + radio_doblez_cm + L_ext_gancho_cm/2), arrowprops=dict(arrowstyle="->", color='yellow'), color='yellow', fontsize=8, va='center')

        ax_z.text(B_use*100/2, H_zap/2, f"{n_barras_Z} varillas {bar_z} L={L_use}m\nSep:{separacion_S:.1f}cm\nGancho: 90°", color='white', ha='center', va='center')
        ax_z.set_xlim(-20, B_use*100+20)
        ax_z.set_ylim(-10, H_zap+70)
        ax_z.axis('off')
        st.pyplot(fig_z)
        
        st.markdown("---")
        st.write("####  Vista 3D Nativa (Volumen de Concreto)")
        fig_vol = go.Figure()
        # Base zapata (prisma rectangular)
        bx = B_use; ly = L_use; hz = H_zap / 100.0
        # Definir los 8 vertices
        vx = [-bx/2, bx/2, bx/2, -bx/2, -bx/2, bx/2, bx/2, -bx/2]
        vy = [-ly/2, -ly/2, ly/2, ly/2, -ly/2, -ly/2, ly/2, ly/2]
        vz = [0, 0, 0, 0, hz, hz, hz, hz]
        fig_vol.add_trace(go.Mesh3d(x=vx, y=vy, z=vz, alphahull=0, opacity=0.75, color='#a8e6cf', name='Zapata'))
        
        # Extrusión central (columna)
        c1 = c1_col / 100.0; c2 = c2_col / 100.0; hc = 1.0 # 1m de pedestal
        cx = [-c1/2, c1/2, c1/2, -c1/2, -c1/2, c1/2, c1/2, -c1/2]
        cy = [-c2/2, -c2/2, c2/2, c2/2, -c2/2, -c2/2, c2/2, c2/2]
        cz = [hz, hz, hz, hz, hz+hc, hz+hc, hz+hc, hz+hc]
        fig_vol.add_trace(go.Mesh3d(x=cx, y=cy, z=cz, alphahull=0, opacity=0.9, color='lightgray', name='Columna'))
        
        fig_vol.update_layout(scene=dict(aspectmode='data',
                                         xaxis=dict(showgrid=True, gridcolor='#333'),
                                         yaxis=dict(showgrid=True, gridcolor='#333'),
                                         zaxis=dict(showgrid=True, gridcolor='#333')),
                              paper_bgcolor='#0f1117', margin=dict(l=0,r=0,b=0,t=0), height=400)
        st.plotly_chart(fig_vol, use_container_width=True)


    with tab_apu:
        # ─── Cantidades base ────────────────────────────────────────────────
        vol_excavacion   = (B_use + 0.5) * (L_use + 0.5) * Df_z
        vol_concreto_zap = B_use * L_use * (H_zap / 100.0)

        # Longitud de varilla con gancho real (arco + extensión)
        _area_m2  = REBAR_DICT[bar_z]["area"] * 1e-4
        _long_gancho_m  = ((math.pi * radio_doblez_cm / 2) + L_ext_gancho_cm) / 100.0
        _long_var_B = L_use - 2*(recub_z/100.0) + 2*_long_gancho_m
        _long_var_L = B_use - 2*(recub_z/100.0) + 2*_long_gancho_m
        _kg_por_m   = REBAR_DICT[bar_z]["area"] * 1e-4 * 7850          # kg/m por varilla
        peso_barras_B_apu = n_barras_B * _long_var_B * _kg_por_m
        peso_barras_L_apu = n_barras_L * _long_var_L * _kg_por_m
        peso_total_acero_zap = peso_barras_B_apu + peso_barras_L_apu

        # Proporciones concreto (ACI 211 aprox. para fc 21 MPa)
        pct_arena_apu = 0.55; pct_grava_apu = 0.80
        bultos_zap    = vol_concreto_zap * 350 / 50.0               # bultos de 50 kg
        vol_arena_z   = vol_concreto_zap * pct_arena_apu             # m³
        vol_grava_z   = vol_concreto_zap * pct_grava_apu             # m³
        litros_agua   = vol_concreto_zap * 185.0                     # l/m³  (rel a/c ≈0.53)

        # ─── SECCIÓN 1: Resumen de materiales ──────────────────────────────
        st.markdown("###  Resumen de Materiales — Quantiy Take-Off")
        cols_m = st.columns(4)
        cols_m[0].metric("⛏ Excavación", f"{vol_excavacion:.2f} m³")
        cols_m[1].metric(" Vol. Concreto", f"{vol_concreto_zap:.2f} m³")
        cols_m[2].metric(" Acero Total", f"{peso_total_acero_zap:.1f} kg")
        cols_m[3].metric(" Cuantía", f"{peso_total_acero_zap/vol_concreto_zap:.1f} kg/m³")

        st.markdown("####  Ingredientes de Concreto")
        df_mat = pd.DataFrame([
            {"Material": " Cemento",        "Cantidad": f"{bultos_zap:.1f}",    "Unidad": "bultos (50 kg)"},
            {"Material": " Arena",          "Cantidad": f"{vol_arena_z:.3f}",   "Unidad": "m³"},
            {"Material": " Gravilla",        "Cantidad": f"{vol_grava_z:.3f}",   "Unidad": "m³"},
            {"Material": " Agua",            "Cantidad": f"{litros_agua:.0f}",   "Unidad": "litros"},
            {"Material": " Acero refuerzo",  "Cantidad": f"{peso_total_acero_zap:.1f}", "Unidad": "kg"},
        ])
        # Integrar precios guardados en base global o usar defaults directos si no se ha visitado el APU Mercado
        _apu = st.session_state.get("apu_config", {})
        _mon = _apu.get("moneda", "COP")
        _p_cem = _apu.get("cemento", 32000.0)
        _p_ace = _apu.get("acero",   4500.0)
        _p_are = _apu.get("arena",   85000.0)
        _p_gra = _apu.get("grava",   95000.0)
        c_excav_u = _apu.get("costo_excav_m3", 25000.0)
        _has_prices = True  # Siempre mostrar precios con los valores por defecto si no hay base

        _c_cem  = bultos_zap * _p_cem
        _c_ace  = peso_total_acero_zap * _p_ace
        _c_are  = vol_arena_z * _p_are
        _c_gra  = vol_grava_z * _p_gra
        _c_exc  = vol_excavacion * c_excav_u if _has_prices else 0.0
        
        _total_mat = _c_exc + _c_cem + _c_are + _c_gra + _c_ace

        # Calcular Gran Total si hay precios
        _gran_total = 0.0
        if _has_prices:
            total_dias_mo = (peso_total_acero_zap * 0.04) + (vol_concreto_zap * 0.4) + (vol_excavacion * 0.3)
            costo_mo = total_dias_mo * _apu.get("costo_dia_mo", 69333.33)
            costo_directo = _total_mat + costo_mo
            herramienta = costo_mo * _apu.get("pct_herramienta", 0.05)
            aiu = costo_directo * _apu.get("pct_aui", 0.30)
            utilidad = costo_directo * _apu.get("pct_util", 0.05)
            iva = utilidad * _apu.get("iva", 0.19)
            _gran_total = costo_directo + herramienta + aiu + iva

            col_msg, col_metric = st.columns([2, 1])
            col_msg.success(f" Precios actualizados del scraping — {_mon}")
            col_metric.metric(f" Gran Total Proyecto [{_mon}]", f"{_gran_total:,.0f}")
            
            # ─── DESGLOSE TRANSPARENTE DEL GRAN TOTAL ───────────────────────
            st.markdown("####  Desglose del Presupuesto")
            _pct_he  = _apu.get('pct_herramienta', 0.05)*100
            _pct_aiu = _apu.get('pct_aui', 0.30)*100
            _pct_uti = _apu.get('pct_util', 0.05)*100
            _pct_iva = _apu.get('iva', 0.19)*100
            _desglose = [
                {"Concepto": "① Materiales Directos",  "Base de cálculo": "Excavación + Concreto + Acero", "Importe": f"{_total_mat:,.0f} {_mon}"},
                {"Concepto": "② Mano de Obra",         "Base de cálculo": f"{total_dias_mo:.2f} días × {_apu.get('costo_dia_mo',69333.33):,.0f}/día", "Importe": f"{costo_mo:,.0f} {_mon}"},
                {"Concepto": "━ COSTO DIRECTO (CD)",   "Base de cálculo": "① + ②",                         "Importe": f"{costo_directo:,.0f} {_mon}"},
                {"Concepto": f"③ Herramienta Menor",   "Base de cálculo": f"{_pct_he:.1f}% × MO",          "Importe": f"{herramienta:,.0f} {_mon}"},
                {"Concepto": f"④ A.I.U. ({_pct_aiu:.0f}%)", "Base de cálculo": f"{_pct_aiu:.1f}% × CD",   "Importe": f"{aiu:,.0f} {_mon}"},
                {"Concepto": f"⑤ IVA s/ Utilidad",    "Base de cálculo": f"{_pct_iva:.1f}% × Utilidad ({_pct_uti:.1f}% CD)", "Importe": f"{iva:,.0f} {_mon}"},
                {"Concepto": "━ GRAN TOTAL",           "Base de cálculo": "CD + ③ + ④ + ⑤",                "Importe": f"**{_gran_total:,.0f} {_mon}**"},
            ]
            st.dataframe(pd.DataFrame(_desglose), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ Ve a **APU Mercado** para descargar los costos en tiempo real aquí mismo.")



        # TABLA: Materiales con costos
        _mat_rows = [
            {"Material": "⛏ Excavación",    "Cantidad": f"{vol_excavacion:.2f}", "Unidad": "m³",           "Precio Unit.": f"{c_excav_u:,.0f} {_mon}" if _has_prices else "—", "Subtotal": f"{_c_exc:,.0f} {_mon}" if _has_prices else "—"},
            {"Material": " Cemento",        "Cantidad": f"{bultos_zap:.1f}",    "Unidad": "bultos (50kg)", "Precio Unit.": f"{_p_cem:,.0f} {_mon}" if _has_prices else "—",   "Subtotal": f"{_c_cem:,.0f} {_mon}" if _has_prices else "—"},
            {"Material": " Arena",          "Cantidad": f"{vol_arena_z:.3f}",   "Unidad": "m³",           "Precio Unit.": f"{_p_are:,.0f} {_mon}" if _has_prices else "—",   "Subtotal": f"{_c_are:,.0f} {_mon}" if _has_prices else "—"},
            {"Material": " Gravilla",        "Cantidad": f"{vol_grava_z:.3f}",   "Unidad": "m³",           "Precio Unit.": f"{_p_gra:,.0f} {_mon}" if _has_prices else "—",   "Subtotal": f"{_c_gra:,.0f} {_mon}" if _has_prices else "—"},
            {"Material": " Agua",            "Cantidad": f"{litros_agua:.0f}",   "Unidad": "litros",       "Precio Unit.": "—", "Subtotal": "—"},
            {"Material": " Acero refuerzo",  "Cantidad": f"{peso_total_acero_zap:.1f}", "Unidad": "kg",  "Precio Unit.": f"{_p_ace:,.0f} {_mon}" if _has_prices else "—",   "Subtotal": f"{_c_ace:,.0f} {_mon}" if _has_prices else "—"},
        ]
        st.dataframe(pd.DataFrame(_mat_rows), use_container_width=True, hide_index=True)

        if _has_prices:
            _total_mat = _c_exc + _c_cem + _c_are + _c_gra + _c_ace
            st.metric(f" Total Materiales [{_mon}]", f"{_total_mat:,.0f}")

        # ─── SECCIÓN 2: Despiece de Acero con costos ─────────────────────────
        st.markdown("####  Despiece de Acero de Refuerzo")
        db_mm_apu    = REBAR_DICT[bar_z]["db"]
        area_cm2_apu = REBAR_DICT[bar_z]["area"]
        _c_ace_B = peso_barras_B_apu * _p_ace
        _c_ace_L = peso_barras_L_apu * _p_ace

        _row_B = {
            "Dir.": "B  (⟵ sobre L →)",
            "Varilla": bar_z, "db [mm]": f"{db_mm_apu:.1f}",
            "N° Barras": n_barras_B, "Sep. [cm]": f"{sep_B:.1f}",
            "L gancho [cm]": f"{L_ext_gancho_cm:.1f}",
            "L total [m]": f"{_long_var_B:.3f}",
            "kg/m": f"{_kg_por_m:.3f}", "Peso [kg]": f"{peso_barras_B_apu:.2f}",
        }
        _row_L = {
            "Dir.": "L  (⟵ sobre B →)",
            "Varilla": bar_z, "db [mm]": f"{db_mm_apu:.1f}",
            "N° Barras": n_barras_L, "Sep. [cm]": f"{sep_L:.1f}",
            "L gancho [cm]": f"{L_ext_gancho_cm:.1f}",
            "L total [m]": f"{_long_var_L:.3f}",
            "kg/m": f"{_kg_por_m:.3f}", "Peso [kg]": f"{peso_barras_L_apu:.2f}",
        }
        _row_tot = {
            "Dir.": "━━ TOTAL ━━",
            "Varilla": "", "db [mm]": "",
            "N° Barras": n_barras_B + n_barras_L, "Sep. [cm]": "",
            "L gancho [cm]": "",
            "L total [m]": f"{n_barras_B*_long_var_B + n_barras_L*_long_var_L:.2f}",
            "kg/m": "", "Peso [kg]": f"{peso_total_acero_zap:.2f}",
        }
        if _has_prices:
            _row_B[f"Costo [{_mon}]"] = f"{_c_ace_B:,.0f}"
            _row_L[f"Costo [{_mon}]"] = f"{_c_ace_L:,.0f}"
            _row_tot[f"Costo [{_mon}]"] = f"{(_c_ace_B+_c_ace_L):,.0f}"

        st.dataframe(pd.DataFrame([_row_B, _row_L, _row_tot]), use_container_width=True, hide_index=True)
        st.caption(f"Gancho 90° ACI/NSR-10: D_doblez mín = {radio_doblez_cm*2:.1f} cm | ext. = {L_ext_gancho_cm:.1f} cm")

        # ─── GRÁFICO: Despiece visual ────────────────────────────────────────
        st.markdown("####  Diagrama de Despiece")
        _items_g   = ["Excavación", "Cemento", "Arena", "Gravilla", "Acero Dir.B", "Acero Dir.L"]
        _qty_g     = [vol_excavacion, bultos_zap, vol_arena_z, vol_grava_z, peso_barras_B_apu, peso_barras_L_apu]
        _units_g   = ["m³", "bultos", "m³", "m³", "kg", "kg"]
        _colors_g  = ["#5c8a5a","#e8c07d","#c2a06b","#9b7b5c","#ff6b35","#ffd54f"]

        
        if _has_prices:
            _cost_g = [_c_exc, _c_cem, _c_are, _c_gra, _c_ace_B, _c_ace_L]
            datos = list(zip(_cost_g, _qty_g, _items_g, _colors_g, _units_g))
            datos.sort(reverse=True)
            _cost_g, _qty_g, _items_g, _colors_g, _units_g = zip(*datos)
        else:
            datos = list(zip(_qty_g, _items_g, _colors_g, _units_g))
            datos.sort(reverse=True)
            _qty_g, _items_g, _colors_g, _units_g = zip(*datos)

        _fig_desp = go.Figure()
        _fig_desp.add_trace(go.Bar(
            x=_items_g, y=_qty_g,
            marker_color=_colors_g,
            text=[f"{q:.2f} {u}" for q, u in zip(_qty_g, _units_g)],
            textposition="outside",
            name="Cantidad"
        ))

        if _has_prices:
            _fig_desp.add_trace(go.Bar(
                x=_items_g, y=_cost_g,
                marker_color=_colors_g, opacity=0.5,
                text=[f"{v:,.0f} {_mon}" for v in _cost_g],
                textposition="outside",
                name=f"Costo [{_mon}]",
                yaxis="y2"
            ))
            _fig_desp.update_layout(yaxis2=dict(title=f"Costo [{_mon}]", overlaying="y", side="right", showgrid=False, tickfont=dict(color="#aaa")))

        _fig_desp.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
            font=dict(color="white"), barmode="overlay",
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Cantidad", showgrid=True, gridcolor="#222"),
            legend=dict(bgcolor="#111", font=dict(color="white")),
            margin=dict(l=20, r=20, t=30, b=20), height=380,
            title=dict(text=f"Despiece Zapata {B_use:.2f}x{L_use:.2f}m — {bar_z}", font=dict(color="white"))
        )
        st.plotly_chart(_fig_desp, use_container_width=True)



        if "apu_config" in st.session_state:
            st.markdown("---")
            st.markdown("###  Presupuesto Estimado (Promedio de Fuentes Regionales)")
            apu = st.session_state.apu_config
            mon = apu["moneda"]
            c_excav = vol_excavacion * 25000
            
            bultos_zap  = vol_concreto_zap * 350 / 50.0
            pct_arena = apu.get("pct_arena_mezcla", 0.55)
            pct_grava = apu.get("pct_grava_mezcla", 0.80)
            vol_arena_z = vol_concreto_zap * pct_arena
            vol_grava_z = vol_concreto_zap * pct_grava

            c_cem = bultos_zap * apu["cemento"]
            c_ace = peso_total_acero_zap * apu["acero"]
            c_are = vol_arena_z * apu["arena"]
            c_gra = vol_grava_z * apu["grava"]
            total_mat = c_cem + c_ace + c_are + c_gra + c_excav
            
            total_dias_mo = (peso_total_acero_zap * 0.04) + (vol_concreto_zap * 0.4) + (vol_excavacion * 0.3)
            costo_mo = total_dias_mo * apu.get("costo_dia_mo", 69333.33)
            
            costo_directo = total_mat + costo_mo
            herramienta = costo_mo * apu.get("pct_herramienta", 0.05)
            aiu = costo_directo * apu.get("pct_aui", 0.30)
            utilidad = costo_directo * apu.get("pct_util", 0.05)
            iva = utilidad * apu.get("iva", 0.19)
            total_proyecto = costo_directo + herramienta + aiu + iva
            
            data_zap_apu = {
                "Concepto": [
                    "① Excavación", "② Cemento", "③ Acero Refuerzo", "④ Arena", "⑤ Grava",
                    "━━ SUBTOTAL MATERIALES DIRECTOS",
                    "⑥ Mano de Obra",
                    "━━ COSTO DIRECTO (CD)",
                    f"⑦ Herramienta Menor ({apu.get('pct_herramienta', 0.05)*100:.1f}%)",
                    f"⑧ A.I.U. ({apu.get('pct_aui', 0.30)*100:.0f}%)",
                    f"⑨ IVA s/ Utilidad ({apu.get('iva', 0.19)*100:.0f}%)",
                    "━━ GRAN TOTAL DEL PROYECTO",
                ],
                "Base de cálculo": [
                    f"{vol_excavacion:.2f} m³ × 25,000/m³",
                    f"{bultos_zap:.1f} blt × {apu['cemento']:,.0f}/blt",
                    f"{peso_total_acero_zap:.1f} kg × {apu['acero']:,.0f}/kg",
                    f"{vol_arena_z:.2f} m³ × {apu['arena']:,.0f}/m³",
                    f"{vol_grava_z:.2f} m³ × {apu['grava']:,.0f}/m³",
                    "① + ② + ③ + ④ + ⑤",
                    f"{total_dias_mo:.2f} días × {apu.get('costo_dia_mo', 69333.33):,.0f}/día",
                    "Mat. + MO",
                    f"{apu.get('pct_herramienta', 0.05)*100:.1f}% × Mano de Obra",
                    f"{apu.get('pct_aui', 0.30)*100:.0f}% × Costo Directo",
                    f"{apu.get('iva', 0.19)*100:.0f}% × Utilidad ({apu.get('pct_util', 0.05)*100:.0f}% CD)",
                    "CD + ⑦ + ⑧ + ⑨",
                ],
                f"Importe [{mon}]": [
                    f"{c_excav:,.0f}", f"{c_cem:,.0f}", f"{c_ace:,.0f}", f"{c_are:,.0f}", f"{c_gra:,.0f}",
                    f"{total_mat:,.0f}",
                    f"{costo_mo:,.0f}",
                    f"{costo_directo:,.0f}",
                    f"{herramienta:,.0f}",
                    f"{aiu:,.0f}",
                    f"{iva:,.0f}",
                    f"{total_proyecto:,.0f}",
                ]
            }
            st.dataframe(pd.DataFrame(data_zap_apu), use_container_width=True, hide_index=True)
            st.info(f" **Diferencia Gran Total vs Materiales:** {total_proyecto - total_mat:,.0f} {mon} = Mano de Obra ({costo_mo:,.0f}) + Herramienta ({herramienta:,.0f}) + AIU ({aiu:,.0f}) + IVA ({iva:,.0f})")

            
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
                _row_util = row - 1
                worksheet.write_formula(row, 3, f'=D{_row_util}*{apu.get("iva", 0.19)}', money_fmt)
                row += 1
                worksheet.write(row, 0, "TOTAL PRESUPUESTO", bold)
                worksheet.write_formula(row, 3, f'=D{row-3}+D{row-2}+D{row-1}+D{row}', money_fmt)
                
            output_excel.seek(0)
            st.download_button(label=" Descargar Presupuesto Excel (.xlsx)", data=output_excel, 
                               file_name=f"APU_Zapata_{B_use}x{L_use}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info(" Ve a la página 'APU Mercado' para cargar los costos base de agregados, acero y cemento y que tu presupuesto se genere automáticamente.")

    # ═══════════════════════════════════════════════════════════════════════════
    # B5 — CUADRO DE MANDO MULTI-ZAPATA + C6 ASENTAMIENTO DIFERENCIAL
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    
    # ── FI-2: Factor de Interacción Biaxial (IFC) ───────────────────────────
    st.write("#### Factor de Interacción (Carga y Momento)")
    # FI-2 φPn corregido: columna (no zapata) — NSR-10 C.10 / ACI 318 §22.4.2
    _Ag_col_mm2 = (c1_col * 10) * (c2_col * 10)     # área bruta columna en mm²
    _As_col_tot = max(0.01 * _Ag_col_mm2, 400)       # cuantía mín. 1% → mm²
    phi_Pn = 0.65 * 0.80 * (0.85 * fc_basico * (_Ag_col_mm2 - _As_col_tot)
             + fy_basico * _As_col_tot) / 1000.0     # kN
    phi_Mnx = phi_f * As_req_B * 1e-4 * fy_basico * d_z_m * 1000
    phi_Mny = phi_f * As_req_L * 1e-4 * fy_basico * d_z_m * 1000
    
    ifc = (P_ult/max(phi_Pn,1)) + (abs(M_ult_B)/max(phi_Mnx,1)) + (abs(M_ult_L)/max(phi_Mny,1))
    
    _col_ifc1, _col_ifc2 = st.columns(2)
    _col_ifc1.metric("IFC (P + Mx + My)", f"{ifc:.3f}", delta="≤ 1.0", delta_color="inverse")
    if ifc > 1.0:
        _col_ifc2.error(f" IFC = {ifc:.3f} > 1.0 — Diseño INSEGURO para compresión biaxial.")
    else:
        _col_ifc2.success(f" IFC = {ifc:.3f} ≤ 1.0")

    st.markdown("##  Cuadro de Mando del Proyecto — Registro de Zapatas")
    st.caption("Registra varias zapatas del proyecto para comparación y verificación de asentamiento diferencial.")

    # ── Inicializar lista en SessionState ───────────────────────────────────
    if "zapatas_proyecto" not in st.session_state:
        st.session_state["zapatas_proyecto"] = []

    # ── Botón para agregar la zapata actual ──────────────────────────────────
    _nombre_zap = st.text_input("Nombre / Etiqueta de esta zapata (ej. Z-1, Eje A-3)",
                                value=f"Z-{len(st.session_state['zapatas_proyecto'])+1}",
                                key="z_nombre_registro")
    _col_btn1, _col_btn2 = st.columns([1, 3])
    if _col_btn1.button(" Agregar al proyecto", type="primary"):
        # FI-5 y FI-1: Actualización con nuevos campos
        _is_ok = (ok_1way_B and ok_1way_L and ok_punz and disc_B > 0 and disc_L > 0 and ifc <= 1.0)
        _entrada = {
            "Nombre":     _nombre_zap,
            "Tipo":       "Aislada",
            "Pos. Col.":  pos_col_iso if 'pos_col_iso' in dir() else "—",
            "B [m]":      round(B_use, 2),
            "L [m]":      round(L_use, 2),
            "H [cm]":     int(H_zap),
            "Pu [kN]":    round(P_ult, 1),
            "IFC":        round(ifc, 3) if 'ifc' in dir() else 0.0,
            "DCR_pun":    round(Vu_punz/phi_Vc_punz, 3) if 'phi_Vc_punz' in dir() and phi_Vc_punz > 0 else 9.99,
            "q_adm [kPa]":round(q_adm_z, 1),
            "qu_max [kPa]":round(qu_max, 2),
            "qu_min [kPa]":round(qu_min, 2),
            "FSv":        round(FS_volc, 2) if 'FS_volc' in dir() else "—",
            "FSd":        round(FS_desl, 2) if 'FS_desl' in dir() else "—",
            "As_B [cm²]": round(As_req_B, 1),
            "As_L [cm²]": round(As_req_L, 1),
            "Estado": " OK" if _is_ok else "⚠ Revisar",
        }
        # evitar duplicado por nombre
        _nombres_existentes = [z["Nombre"] for z in st.session_state["zapatas_proyecto"]]
        if _nombre_zap in _nombres_existentes:
            _idx = _nombres_existentes.index(_nombre_zap)
            st.session_state["zapatas_proyecto"][_idx] = _entrada
            st.success(f" Zapata **{_nombre_zap}** actualizada en el registro.")
        else:
            st.session_state["zapatas_proyecto"].append(_entrada)
            st.success(f" Zapata **{_nombre_zap}** agregada al proyecto ({len(st.session_state['zapatas_proyecto'])} total).")

    if _col_btn2.button(" Limpiar registro"):
        st.session_state["zapatas_proyecto"] = []
        st.info("Registro limpiado.")

    # ── Tabla comparativa ────────────────────────────────────────────────────
    if st.session_state["zapatas_proyecto"]:
        _df_proy = pd.DataFrame(st.session_state["zapatas_proyecto"])
        st.markdown("###  Comparativo de Zapatas del Proyecto")
        st.dataframe(_df_proy, use_container_width=True, hide_index=True)

        # Exportar a Excel
        _buf_proy = io.BytesIO()
        with pd.ExcelWriter(_buf_proy, engine="xlsxwriter") as _wr:
            _df_proy.to_excel(_wr, index=False, sheet_name="Zapatas")
            _wb2 = _wr.book
            _ws2 = _wr.sheets["Zapatas"]
            _hdr_fmt = _wb2.add_format({"bold": True, "bg_color": "#1a3a5c", "font_color": "white"})
            for _ci, _col in enumerate(_df_proy.columns):
                _ws2.write(0, _ci, _col, _hdr_fmt)
                _ws2.set_column(_ci, _ci, max(12, len(str(_col))+2))
        _buf_proy.seek(0)
        st.download_button(" Exportar tabla de proyecto a Excel",
                           data=_buf_proy,
                           file_name="Cuadro_Mando_Zapatas.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # ── C6 — ASENTAMIENTO DIFERENCIAL ──────────────────────────────────
        if len(st.session_state["zapatas_proyecto"]) >= 2:
            st.markdown("---")
            st.markdown("###  C6 — Verificación de Asentamiento Diferencial (NSR-10 H.3)")
            _asen_vals = [z["Asentam. [mm]"] for z in st.session_state["zapatas_proyecto"]]
            _noms_vals = [z["Nombre"]        for z in st.session_state["zapatas_proyecto"]]

            # Separación entre zapatas (para calcular límite angular)
            _sep_viga = st.number_input("Separación entre zapatas adyacentes L_viga [m] (luz entre ejes)",
                                        1.0, 30.0, 6.0, 0.5, key="z_sep_viga")
            _delta_adm = _sep_viga * 1000 / 300.0   # mm  (NSR-10 H.3: δ ≤ L/300)

            _filas_d = []
            for _i in range(len(_asen_vals) - 1):
                _delta_s = abs(_asen_vals[_i+1] - _asen_vals[_i])
                _ok_d    = _delta_s <= _delta_adm
                _filas_d.append({
                    "Par": f"{_noms_vals[_i]} — {_noms_vals[_i+1]}",
                    "s₁ [mm]": f"{_asen_vals[_i]:.1f}",
                    "s₂ [mm]": f"{_asen_vals[_i+1]:.1f}",
                    "Δs [mm]": f"{_delta_s:.1f}",
                    f"Máx. NSR-10 [mm] (L/{300})": f"{_delta_adm:.1f}",
                    "Estado": " OK" if _ok_d else f" Excede ({_delta_s:.1f} > {_delta_adm:.1f})"
                })

            st.dataframe(pd.DataFrame(_filas_d), use_container_width=True, hide_index=True)

            _max_delta = max(abs(_asen_vals[i+1] - _asen_vals[i]) for i in range(len(_asen_vals)-1))
            if _max_delta <= _delta_adm:
                st.success(f" **Asentamiento diferencial máximo = {_max_delta:.1f} mm ≤ {_delta_adm:.1f} mm** (L_viga/{300}) — NSR-10 H.3 satisfecho.")
            else:
                st.error(f" **Δs_max = {_max_delta:.1f} mm > {_delta_adm:.1f} mm** — El asentamiento diferencial excede el límite NSR-10 H.3. "
                         "Considere zapatas más rígidas, aumentar B×L o usar vigas de cimentación.")
            st.caption(f"Nota: los asentamientos se leen del campo 'Asentam. [mm]' registrado para cada zapata. "
                       "Si el valor es 0, calcule el asentamiento en la pestaña de Geotecnia antes de agregar la zapata al registro.")
    else:
        st.info("ℹ Agrega al menos una zapata con el botón ** Agregar al proyecto** para activar el cuadro de mando.")


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL: render_medianera()
# Tipos 2 (Medianera/Lindero), 3 (Esquina) y 4 (Con Viga de Amarre)
# ══════════════════════════════════════════════════════════════════════════════
def render_medianera(norma, fc, fy, rebar_dict, def_idx, phi_v, phi_f, tipo_zap):
    """Flujo completo de diseño para zapata medianera, de esquina y con viga de amarre."""
    sn = _get_strap_norm(norma)
    _es_medianera = "2." in tipo_zap
    _es_esquina   = "3." in tipo_zap
    _es_strap     = "4." in tipo_zap or _es_medianera or _es_esquina

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a2a4a,#0d1b35);border-radius:10px;
    padding:16px 20px;margin-bottom:16px;border-left:4px solid #4db8ff;">
    <h4 style="color:#4db8ff;margin:0 0 6px 0;"> {tipo_zap}</h4>
    <p style="color:#aad4ff;margin:0;font-size:13px;">
    Norma activa: <strong>{norma}</strong> — {sn['nombre']} ({sn['art']})
    </p>
    </div>
    """, unsafe_allow_html=True)

    # ─── TABS DE TRABAJO ──────────────────────────────────────────────────────
    tab_geo, tab_viga, tab_3d, tab_dxf, tab_docx = st.tabs([
        " Geometría y Presiones",
        f" {sn['nombre']}",
        " Vista 3D",
        " DXF",
        " Memoria",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: GEOMETRÍA Y DISTRIBUCIÓN DE PRESIONES
    # ══════════════════════════════════════════════════════════════════════════
    with tab_geo:
        st.subheader(" Geometría y Cargas")
        cA, cB, cC = st.columns(3)
        with cA:
            st.markdown("##### Zapata Exterior (lindero)")
            Be = st.number_input("Ancho B_ext [m]", 0.5, 10.0,
                                 st.session_state.get("zm_Be", 2.0), 0.1, key="zm_Be")
            Le = st.number_input("Largo L_ext [m]", 0.5, 10.0,
                                 st.session_state.get("zm_Le", 2.0), 0.1, key="zm_Le")
            He = st.number_input("Espesor H_ext [cm]", 20.0, 120.0,
                                 st.session_state.get("zm_He", 50.0), 5.0, key="zm_He")
            c1e = st.number_input("Col. c1_ext [cm]", 15.0, 80.0, 40.0, 5.0, key="zm_c1e")
            c2e = st.number_input("Col. c2_ext [cm]", 15.0, 80.0, 40.0, 5.0, key="zm_c2e")
            Pe  = st.number_input("Carga Axial P_ext [kN]", 50.0, 5000.0, 500.0, 50.0, key="zm_Pe")
            Me_B = st.number_input("Momento M_ext dir.B [kN·m]", 0.0, 1000.0, 0.0, 10.0, key="zm_MeB")
            Me_L = st.number_input("Momento M_ext dir.L [kN·m]", 0.0, 1000.0, 0.0, 10.0, key="zm_MeL")

        with cB:
            st.markdown("##### Zapata Interior (campo libre)")
            Bi = st.number_input("Ancho B_int [m]", 0.5, 10.0,
                                 st.session_state.get("zm_Bi", 2.0), 0.1, key="zm_Bi")
            Li = st.number_input("Largo L_int [m]", 0.5, 10.0,
                                 st.session_state.get("zm_Li", 2.0), 0.1, key="zm_Li")
            Hi = st.number_input("Espesor H_int [cm]", 20.0, 120.0,
                                 st.session_state.get("zm_Hi", 50.0), 5.0, key="zm_Hi")
            c1i = st.number_input("Col. c1_int [cm]", 15.0, 80.0, 40.0, 5.0, key="zm_c1i")
            c2i = st.number_input("Col. c2_int [cm]", 15.0, 80.0, 40.0, 5.0, key="zm_c2i")
            Pi  = st.number_input("Carga Axial P_int [kN]", 50.0, 5000.0, 700.0, 50.0, key="zm_Pi")
            Mi_B = st.number_input("Momento M_int dir.B [kN·m]", 0.0, 1000.0, 0.0, 10.0, key="zm_MiB")
            Mi_L = st.number_input("Momento M_int dir.L [kN·m]", 0.0, 1000.0, 0.0, 10.0, key="zm_MiL")

        with cC:
            st.markdown("##### Sistema y Suelo")
            q_adm_m = st.number_input("q_adm [kPa]", 50.0, 600.0, 150.0, 10.0, key="zm_qadm")
            L_libre = st.number_input("Distancia libre entre zapatas [m]", 1.0, 20.0,
                                      st.session_state.get("zm_Llibre", 4.0), 0.5, key="zm_Llibre")
            dist_lindero = st.number_input("Dist. borde col. ext → lindero [cm]", 0.0, 200.0, 0.0, 5.0,
                                           key="zm_distlind",
                                           help="Si = 0: la columna coincide con el lindero. "
                                                "La excentricidad se calculará automáticamente.")
            gamma_c_m = st.number_input("γ_concreto [kN/m³]", 22.0, 26.0, 24.0, 0.5, key="zm_gam")

        with st.expander(" Optimizador automático B×L (Medianera)", expanded=False):
            st.caption("Busca la combinación mínima Be×Le / Bi×Li que cumpla q_adm con carga dada.")
            _q_adm_opt = st.number_input("q_adm objetivo [kPa]", 50.0, 600.0,
                                         st.session_state.get("zm_qadm", 150.0), 10.0, key="opt_qadm_zm")
            _Pe_opt = st.number_input("Carga exterior P_ext [kN]", 50.0, 5000.0, 500.0, 50.0, key="opt_Pe_zm")
            _Pi_opt = st.number_input("Carga interior P_int [kN]", 50.0, 5000.0, 700.0, 50.0, key="opt_Pi_zm")
            _paso   = st.selectbox("Paso de búsqueda [m]", [0.05, 0.10, 0.25], index=1, key="opt_paso_zm")
            if st.button(" Optimizar dimensiones", key="opt_btn_zm"):
                import itertools as _it
                import numpy as _np_opt
                _dims = _np_opt.arange(0.5, 6.0 + _paso, _paso)
                _best = None
                for _b, _l in _it.product(_dims, _dims):
                    _qu = _Pe_opt / (_b * _l)
                    if _qu <= _q_adm_opt:
                        _area = _b * _l
                        if _best is None or _area < _best[2]:
                            _best = (_b, _l, _area, _qu)
                if _best:
                    st.success(f" Dimensión óptima exterior: B = **{_best[0]:.2f} m** × L = **{_best[1]:.2f} m**")
                    st.metric("q_neto", f"{_best[3]:.1f} kPa", delta=f"{_q_adm_opt - _best[3]:.1f} kPa de reserva")
                    _b2, _l2 = _best[0], _best[1]
                    _qu2 = _Pi_opt / (_b2 * _l2)
                    _ok2 = _qu2 <= _q_adm_opt
                    st.info(f"Interior (misma dimensión {_b2:.2f}×{_l2:.2f}m): qu = {_qu2:.1f} kPa  {'' if _ok2 else ' aumentar'}")
                else:
                    st.error(" No se encontró dimensión dentro del rango 0.5–6.0 m. Revisa q_adm o las cargas.")

        st.divider()
        # ─── CÁLCULO DISTRIBUCIONES DE PRESIONES ──────────────────────────────
        st.subheader(" Distribución de Presiones")
        col_pe, col_pi = st.columns(2)

        def _mostrar_presiones(label, P, M_B, M_L, B, L, c1_cm, c2_cm, prefix, q_adm):
            qu_max, qu_min, tipo_dist, e_B, e_L, Ix, Iy, A = calcular_distribucion_presiones(
                P, M_B, M_L, B, L)
            meyerhof_data = None
            if qu_min < 0:
                B_p, L_p, A_p = calcular_area_efectiva_meyerhof(B, L, e_B, e_L)
                qu_eff = P / A_p
                meyerhof_data = {"B_prima": B_p, "L_prima": L_p, "qu_eff": qu_eff}
                st.warning(f"⚠ **{label}**: qu_min = {qu_min:.1f} kPa < 0 — "
                           f"Área Efectiva Meyerhof → B'={B_p:.2f}m × L'={L_p:.2f}m → **qu_eff = {qu_eff:.1f} kPa**")
                qu_avg_uso = qu_eff
            elif tipo_dist == "triangular":
                # EM-2 CORREGIDO: para distribución triangular el valor representativo
                # es qu_max * (2/3), no el promedio aritmético (que subestima la carga)
                # Referencia: Bowles (1996) §8.4 — área del triángulo de presiones
                qu_avg_uso = qu_max * (2.0 / 3.0)
            else:
                qu_avg_uso = (qu_max + qu_min) / 2

            ok_q = qu_avg_uso <= q_adm
            semaf = "" if ok_q else ""
            _d_lbl = {"trapezoidal":"Trapezoidal","triangular":"Triangular (parcial levant.)","con_tension":"Con tensión"}
            st.markdown(f"""
| Parámetro | Valor |
|---|---|
| **qu_max** | `{qu_max:.1f} kPa` |
| **qu_min** | `{qu_min:.1f} kPa` |
| **Distribución** | {_d_lbl.get(tipo_dist, tipo_dist)} |
| **e_B** | `{e_B:.3f} m` |
| **e_L** | `{e_L:.3f} m` |
| **q_adm** | `{q_adm:.1f} kPa` |
| **Verificación** | {semaf} `qu_avg={qu_avg_uso:.1f}` ≤ `{q_adm:.1f}` kPa |
""")
            # Mapa de calor
            fig_hm, _ten = render_mapa_calor_presiones(B, L, P, M_B, M_L, Ix, Iy, A,
                                                       qu_max, qu_min, c1_cm, c2_cm,
                                                       titulo=f"qu(x,y) — {label}", q_adm=q_adm)
            st.plotly_chart(fig_hm, use_container_width=True)
        if abs(qu_max_z - qu_min_z) < 1.0:
            st.info(
                " **Distribución uniforme** — qu = "
                f"{qu_max_z:.1f} kPa constante en toda la huella. "
                "El gráfico 3D cobra valor cuando ingresas momentos Mu ≠ 0 "
                "para ver la variación de presiones."
            )
        else:
            if qu_min_z >= 0:
                st.warning(
                    f"⚠ **Distribución trapezoidal** — "
                    f"qu_max = {qu_max_z:.1f} kPa | qu_min = {qu_min_z:.1f} kPa. "
                    f"Excentricidad activa en la zapata."
                )
            else:
                st.error(
                    f" **Levantamiento parcial** — qu_min = {qu_min_z:.1f} kPa < 0. "
                    "Parte de la zapata no está en contacto con el suelo."
                )
            return {"qu_max": qu_max, "qu_min": qu_min, "tipo": tipo_dist,
                    "e_B": e_B, "e_L": e_L, "Ix": Ix, "Iy": Iy, "A": A,
                    "qu_avg": qu_avg_uso, "meyerhof": meyerhof_data}

        with col_pe:
            st.markdown("**Zapata Exterior**")
            dist_e = _mostrar_presiones("Zapata Exterior", Pe, Me_B, Me_L,
                                        Be, Le, c1e, c2e, "ext", q_adm_m)
        with col_pi:
            st.markdown("**Zapata Interior**")
            dist_i = _mostrar_presiones("Zapata Interior", Pi, Mi_B, Mi_L,
                                        Bi, Li, c1i, c2i, "int", q_adm_m)

        # Excentricidad y reacción de la viga de amarre
        # R_strap = M_exc / L_centro_a_centro (equilibrio de momentos)
        # Para medianera: la excentricidad es e_B respecto al centroide de la zapata
        e_exc = dist_e["e_B"] + (Be/2 - c1e/200)  # excentricidad total desde col al centroide
        R_strap_kN = Pe * e_exc / L_libre if L_libre > 0 else 0.0
        st.info(f"**Reacción en viga de amarre:** R_strap = Pe × e / L_libre = "
                f"{Pe:.1f} × {e_exc:.3f} / {L_libre:.1f} = **{R_strap_kN:.2f} kN**")

        # Guardar datos de estado para otras tabs
        st.session_state["zm_dist_e"] = dist_e
        st.session_state["zm_dist_i"] = dist_i
        st.session_state["zm_R_strap"] = R_strap_kN

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: DISEÑO DE LA VIGA DE AMARRE
    # ══════════════════════════════════════════════════════════════════════════
    with tab_viga:
        st.subheader(f" Diseño de {sn['nombre']} — {norma}")
        st.markdown(f"> Artículo de referencia: **{sn['art']}** | "
                    f"Dimensión mínima: L / {sn['h_factor']} | "
                    f"Fuerza axial sísmica: {sn['F_ax_pct']*100:.1f}% × ΣP")

        cV1, cV2, cV3 = st.columns(3)
        with cV1:
            bv = st.number_input(f"Ancho {sn['nombre']} b [cm]", 20.0, 60.0, 30.0, 5.0, key="zm_bv")
            hv = st.number_input(f"Alto {sn['nombre']} h [cm]", 30.0, 120.0, 50.0, 5.0, key="zm_hv")
            recub_v = st.number_input("Recubrimiento [cm]", 2.5, 8.0, 4.0, 0.5, key="zm_recubv")
        with cV2:
            bar_long_v = st.selectbox("Varilla longitudinal:", list(rebar_dict.keys()),
                                      index=min(def_idx+1, len(rebar_dict)-1), key="zm_bar_long_v")
            bar_est_v  = st.selectbox("Varilla estribo:", list(rebar_dict.keys()),
                                      index=0, key="zm_bar_est_v")
        with cV3:
            # MC-1 CORREGIDO: R_strap se propaga automáticamente desde la pestaña Geom.
            _R_auto = float(st.session_state.get("zm_R_strap", 50.0))
            st.metric("R_strap calculado [kN]", f"{_R_auto:.2f}",
                      help="Calculado automáticamente en 'Geometría y Presiones'. "
                           "Si cambias los inputs, recalculará al volver a esa pestaña.")
            R_strap_kN_ui = st.number_input(
                "Sobreescribir R_strap [kN] (opcional):",
                0.1, 3000.0, _R_auto, 10.0, key="zm_R_strap_ui",
                help="Deja el valor calculado o ajusta manualmente si es necesario.")
            P_total_kN = st.number_input("ΣP columnas (para F_ax sísmica) [kN]:",
                                          100.0, 10000.0,
                                          float(Pe if 'Pe' in dir() else 1000.0),
                                          100.0, key="zm_Ptotal")

        # Calcular V(x) y M(x) — EC-2: ahora retorna 8 valores (incluye _adv_Rint)
        x_arr, V_arr, M_arr, M_max, V_max, pp_viga, R_int, _adv_Rint = calcular_viga_amarre(
            R_strap_kN_ui, L_libre, bv, hv, gamma_c_m)
        # EC-2: mostrar advertencia de levantamiento si R_int < 0
        if _adv_Rint:
            st.error(
                f"⚠ **Levantamiento en zapata interior: R_int = {R_int:.2f} kN < 0** — "
                "El peso propio de la viga supera la reacción de amarre. "
                "Aumento de R_strap o reducción de L_libre requeridos."
            )
        # MC-4: aviso diferenciado para NTC-EM (México) con F_ax = 5%
        if "NTC" in norma:
            st.info("🇲🇽 **NTC-EM México:** La fuerza axial sísmica requerida es **F_ax = 5% × ΣP**, "
                    "el doble del estándar ACI/NSR-10 (2.5%). Revisar el diseño.")
        F_ax_sism = sn["F_ax_pct"] * P_total_kN

        # Diseñar la viga — EC-3: capturar dict de error si d_v <= 0
        dis = disenar_viga_amarre(
            M_max, V_max, F_ax_sism, bv, hv, fc, fy, L_libre, P_total_kN, norma,
            recub_v=recub_v, bar_long=bar_long_v, bar_est=bar_est_v, rebar_dict=rebar_dict)
        if dis.get("_error"):
            st.error(dis["_msg"])
            st.stop()

        # Tabla de verificaciones — semáforo
        st.subheader(" /  Tabla de Verificaciones")
        _v_rows = [
            ("Dimensión mínima h", f"{hv:.0f} cm", f"L/{sn['h_factor']} = {dis['h_min_cm']:.1f} cm", dis["ok_hmin"]),
            ("Flexión sup. φMn+", f"{dis['phi_Mn_sup']:.1f} kN·m", f"M_max = {M_max:.2f} kN·m", dis["ok_flex"]),
            ("Cortante φVc", f"{dis['phi_Vc']:.1f} kN", f"V_max = {V_max:.2f} kN", dis["ok_cort"]),
            ("F. axial sísmica (req.)", f"{F_ax_sism:.1f} kN", f"{sn['F_ax_pct']*100:.1f}% × ΣP = {dis['F_ax_req']:.1f} kN", dis["ok_Fax"]),
        ]
        _cols = st.columns([2.5, 2, 2.5, 0.8])
        _cols[0].markdown("**Verificación**"); _cols[1].markdown("**Calculado**")
        _cols[2].markdown("**Límite**"); _cols[3].markdown("**OK**")
        for _vr, _vc, _vl, _vo in _v_rows:
            _c = st.columns([2.5, 2, 2.5, 0.8])
            _ic = "" if _vo else ""
            _c[0].markdown(_vr); _c[1].markdown(f"`{_vc}`")
            _c[2].markdown(f"`{_vl}`"); _c[3].markdown(f"**{_ic}**")

        st.divider()
        # Tabla de armado
        st.subheader(f" Armado de {sn['nombre']}")
        _a_col1, _a_col2 = st.columns(2)
        with _a_col1:
            st.markdown(f"""
| Elemento | Resultado |
|---|---|
| **Barras superiores** | **{dis['n_sup']} × {dis['bar_long']}** = {dis['As_sup']:.2f} cm² |
| **Barras inferiores** | **{dis['n_inf']} × {dis['bar_long']}** = {dis['As_inf']:.2f} cm² |
| **d efectivo** | {dis['d_v']:.1f} cm |
| **Estribos** | {dis['bar_est']} **@ {dis['s_crit_cm']:.0f} cm** (zona crít. {dis['L_crit_cm']:.0f} cm) |
| **Estribos (resto)** | {dis['bar_est']} **@ {dis['s_est_cm']:.0f} cm** |
""")
        with _a_col2:
            st.markdown(f"""
| Referencia Normativa | |
|---|---|
| **Norma** | {norma} |
| **Artículo** | {sn['art']} |
| **h_min** | L/{sn['h_factor']} = {dis['h_min_cm']:.1f} cm |
| **F_ax mínima** | {sn['F_ax_pct']*100:.1f}% × ΣP = {dis['F_ax_req']:.1f} kN |
""")

        # Diagrama V(x) / M(x)
        st.subheader(" Diagrama de Esfuerzos Internos")
        fig_vm = render_diagrama_VM(x_arr, V_arr, M_arr,
                                    R_strap_kN_ui, R_int, pp_viga, L_libre)
        st.plotly_chart(fig_vm, use_container_width=True)

        # Guardar resultados intermedios en sesión
        st.session_state["zm_dis"] = dis
        st.session_state["zm_fig_vm"] = fig_vm
        st.session_state["zm_viga_d"] = {
            "b_cm": bv, "h_cm": hv, "b": bv, "h": hv, "L_libre_m": L_libre,
            "recub_cm": recub_v, "recub": recub_v, "fc": fc, "fy": fy,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: VISTA 3D PLOTLY
    # ══════════════════════════════════════════════════════════════════════════
    with tab_3d:
        st.subheader(" Vista 3D del Sistema")
        dis_3d  = st.session_state.get("zm_dis")
        viga_3d = st.session_state.get("zm_viga_d")
        if dis_3d and viga_3d:
            zap_ext_3d = {"x0": 0.0, "y0": 0.0, "B": Be, "L": Le, "H": He, "c1": c1e, "c2": c2e}
            zap_int_3d = {"x0": Be + L_libre, "y0": 0.0, "B": Bi, "L": Li, "H": Hi, "c1": c1i, "c2": c2i}
            fig_3d = render_3d_sistema(zap_ext_3d, zap_int_3d, viga_3d, dis_3d)
            st.plotly_chart(fig_3d, use_container_width=True)
            st.caption(" Arrastra para rotar • Doble clic para resetear vista • Rueda para zoom")
        else:
            st.info("ℹ Completa primero la pestaña **'Geometría y Presiones'** y el **'Diseño de Viga'** para generar la vista 3D.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: EXPORTACIÓN DXF
    # ══════════════════════════════════════════════════════════════════════════
    with tab_dxf:
        st.subheader(" Planos DXF (3 Vistas + Rótulo)")
        dis_dxf  = st.session_state.get("zm_dis")
        viga_dxf = st.session_state.get("zm_viga_d")
        dist_e_dxf = st.session_state.get("zm_dist_e")
        dist_i_dxf = st.session_state.get("zm_dist_i")
        if dis_dxf and viga_dxf:
            zap_ext_dxf = {"B_cm": Be*100, "L_cm": Le*100, "H_cm": He}
            zap_int_dxf = {"B_cm": Bi*100, "L_cm": Li*100, "H_cm": Hi}
            if st.button(" Generar DXF del Sistema", key="zm_gen_dxf", type="primary"):
                with st.spinner("Generando planos DXF..."):
                    try:
                        doc_dxf = generar_dxf_sistema(zap_ext_dxf, zap_int_dxf, viga_dxf, dis_dxf, norma, fc, fy)
                        _buf_dxf = io.BytesIO()
                        doc_dxf.write(_buf_dxf)
                        _buf_dxf.seek(0)
                        st.download_button(
                            f"⬇ Descargar DXF — {sn['nombre']}",
                            data=_buf_dxf.getvalue(),
                            file_name=f"zapata_{sn['nombre'].replace(' ','_').lower()}.dxf",
                            mime="application/dxf",
                            key="zm_dl_dxf"
                        )
                        st.success(" DXF generado con: Planta general, Corte A-A longitudinal, Corte B-B transversal y Rótulo normativo.")
                        st.markdown(f"""
**Layers incluidos:**
- `ZAPATA_EXT` (amarillo) — Zapata en lindero
- `ZAPATA_INT` (verde) — Zapata interior
- `VIGA_STRAP` (rojo) — {sn['nombre']}
- `ACERO_LONG` (cian) — Barras longitudinales
- `ACERO_EST` (blanco) — Estribos
- `COTAS` (gris) — Dimensiones
- `ROTULO` (magenta) — Rótulo normativo con norma {norma}
""")
                    except Exception as _e_dxf:
                        st.error(f"Error generando DXF: {_e_dxf}")
        else:
            st.warning("⚠ Completa primero la pestaña **Geometría y Presiones** y el diseño de la viga.")
        # FI-2: EXPORTACIÓN IFC (SISTEMA ZAPATA MEDIANERA / STRAP BEAM) ────────
        st.markdown("---")
        st.markdown("####  Exportar Modelo BIM (.ifc)")
        st.caption("Requiere `ifcopenshell`. Si no está instalado, genera un IFC simplificado en texto plano.")
        _c_ifc1, _c_ifc2 = st.columns(2)
        _proyecto_ifc = _c_ifc1.text_input("Nombre del proyecto IFC", value="Proyecto NSR-10", key="zm_ifc_proy")
        _edificio_ifc = _c_ifc2.text_input("Elemento (ej. Zapata Medianera Z-M1)", value=f"ZAP-M-{tipo_zap[:1]}", key="zm_ifc_elem")
        if st.button(" Generar IFC del sistema", key="zm_btn_ifc"):
            try:
                import ifc_export as _ifc_mod
                # Usar la función ifc_zapata para la zapata exterior + viga como IfcBeam
                _viga_d_ifc = st.session_state.get("zm_viga_d", {})
                _be_ifc = st.session_state.get("zm_Be", 2.0) * 100  # m → cm
                _le_ifc = st.session_state.get("zm_Le", 2.0) * 100
                _he_ifc = st.session_state.get("zm_He", 50.0)
                _buf_ifc = _ifc_mod.ifc_zapata(
                    _be_ifc, _le_ifc, _he_ifc,
                    fc, fy,
                    "Ø16", 16.0, 4,
                    "Ø16", 16.0, 4,
                    4.0, 0.0, norma, _proyecto_ifc
                )
                st.download_button(
                    " Descargar Modelo BIM (IFC)",
                    data=_buf_ifc,
                    file_name=f"zapata_medianera_{norma.replace(' ','_')}.ifc",
                    mime="application/x-step",
                    key="zm_dl_ifc"
                )
                st.success(" IFC generado: IfcFooting (zapata ext.) + datos del sistema.")
            except ImportError:
                # Fallback: IFC texto plano mínimo si ifcopenshell no está disponible
                st.warning("⚠ `ifc_export` no disponible — generando IFC mínimo en texto plano.")
                _vd = st.session_state.get("zm_viga_d", {})
                _dd = st.session_state.get("zm_dis", {})
                _ifc_txt = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('StructuroPro — Zapata {tipo_zap}'),'2;1');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
/* Sistema: {tipo_zap} | Norma: {norma} */
/* Zapata ext: B={st.session_state.get('zm_Be',2.0):.2f}m x L={st.session_state.get('zm_Le',2.0):.2f}m x H={st.session_state.get('zm_He',50.0):.0f}cm */
/* Zapata int: B={st.session_state.get('zm_Bi',2.0):.2f}m x L={st.session_state.get('zm_Li',2.0):.2f}m x H={st.session_state.get('zm_Hi',50.0):.0f}cm */
/* Viga: {_vd.get('b_cm',30):.0f}cm x {_vd.get('h_cm',50):.0f}cm | f'c={fc}MPa | fy={fy}MPa */
/* As_sup={_dd.get('As_sup',0):.2f}cm2 | As_inf={_dd.get('As_inf',0):.2f}cm2 */
ENDSEC;
END-ISO-10303-21;
"""
                st.download_button(
                    " Descargar IFC mínimo (texto plano)",
                    data=_ifc_txt.encode("utf-8"),
                    file_name=f"zapata_medianera_{norma.replace(' ','_')}.ifc",
                    mime="application/x-step",
                    key="zm_dl_ifc_txt"
                )
        st.caption(" Para IFC completo con geometría 3D, instala: `pip install ifcopenshell`")
        # ────────────────────────────────────────────────────────────────────────


    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5: MEMORIA DOCX
    # ══════════════════════════════════════════════════════════════════════════
    with tab_docx:
        st.subheader(f" Memoria de Cálculo — {sn['nombre']}")
        dis_doc  = st.session_state.get("zm_dis")
        viga_doc = st.session_state.get("zm_viga_d")
        dist_e_doc = st.session_state.get("zm_dist_e", {})
        dist_i_doc = st.session_state.get("zm_dist_i", {})
        fig_vm_doc = st.session_state.get("zm_fig_vm")
        if dis_doc and viga_doc:
            zap_ext_doc = {"B_cm": Be*100, "L_cm": Le*100, "H_cm": He}
            zap_int_doc = {"B_cm": Bi*100, "L_cm": Li*100, "H_cm": Hi}
            dist_d = {
                "qu_max": dist_e_doc.get("qu_max", 0),
                "qu_min": dist_e_doc.get("qu_min", 0),
                "tipo": dist_e_doc.get("tipo", "—"),
                "e_B": dist_e_doc.get("e_B", 0),
                "e_L": dist_e_doc.get("e_L", 0),
                "meyerhof": dist_e_doc.get("meyerhof"),
            }
            if st.button(" Generar Memoria DOCX", key="zm_gen_docx", type="primary"):
                with st.spinner("Generando memoria de cálculo..."):
                    try:
                        doc_word = generar_docx_ampliado(
                            zap_ext_doc, zap_int_doc, viga_doc, dis_doc, dist_d, norma, fig_vm_doc)
                        _buf_docx = io.BytesIO()
                        doc_word.save(_buf_docx)
                        _buf_docx.seek(0)
                        st.download_button(
                            f"⬇ Descargar Memoria — {sn['nombre']}",
                            data=_buf_docx.getvalue(),
                            file_name=f"memoria_{sn['nombre'].replace(' ','_').lower()}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="zm_dl_docx"
                        )
                        st.success(" Memoria generada: 4 secciones (Datos, Presiones, Diseño, Diagramas V/M)")
                    except Exception as _e_doc:
                        st.error(f"Error generando DOCX: {_e_doc}")

            # Preview de armado en pantalla
            if dis_doc:
                st.divider()
                st.subheader(" Resumen de Diseño")
                st.markdown(f"""
| Elemento | Especificación |
|---|---|
| **{sn['nombre']}** | **{viga_doc['b_cm']:.0f} × {viga_doc['h_cm']:.0f} cm** |
| **Acero superior** | {dis_doc['n_sup']} × {dis_doc['bar_long']} (As = {dis_doc['As_sup']:.2f} cm²) |
| **Acero inferior** | {dis_doc['n_inf']} × {dis_doc['bar_long']} (As = {dis_doc['As_inf']:.2f} cm²) |
| **Estribos** | {dis_doc['bar_est']} @ {dis_doc['s_crit_cm']:.0f} cm (zona crít.) / {dis_doc['s_est_cm']:.0f} cm (resto) |
| **Norma** | {norma} — Art. {sn['art']} |
| **h_min normativo** | L/{sn['h_factor']} = {dis_doc['h_min_cm']:.1f} cm {'' if dis_doc['ok_hmin'] else ''} |
| **F. axial sísmica** | {sn['F_ax_pct']*100:.1f}% × ΣP = {dis_doc['F_ax_req']:.1f} kN {'' if dis_doc['ok_Fax'] else ''} |
""")
        else:
            st.info("ℹ Completa las pestañas anteriores para activar la memoria de cálculo.")

    # ═══════════════════════════════════════════════════════════════════════════
    # APU — CANTIDADES VIGA DE AMARRE (expander fuera de tabs)
    # ═══════════════════════════════════════════════════════════════════════════
    # Crear APU dinámicamente añadido a continuación del flujo de trabajo
    st.divider()
    with st.expander(" APU — Cantidades y Presupuesto del Sistema (Viga de Amarre)", expanded=False):
        _vd_a = st.session_state.get("zm_viga_d", {})
        _dd_a = st.session_state.get("zm_dis",    {})
        if _vd_a and _dd_a:
            import math as _math_apu
            _gc_a   = 24.0                      # kN/m³
            _gc_kg  = 2400.0                    # kg/m³
            _Be_a   = st.session_state.get("zm_Be", 2.0)
            _Le_a   = st.session_state.get("zm_Le", 2.0)
            _He_a   = st.session_state.get("zm_He", 50.0) / 100.0
            _Bi_a   = st.session_state.get("zm_Bi", 2.0)
            _Li_a   = st.session_state.get("zm_Li", 2.0)
            _Hi_a   = st.session_state.get("zm_Hi", 50.0) / 100.0
            _bv_a   = _vd_a.get("b_cm", 30) / 100.0
            _hv_a   = _vd_a.get("h_cm", 50) / 100.0
            _Lv_a   = _vd_a.get("L_libre_m", 4.0)
            _Df_a   = 1.5  # profundidad desplante aprox

            # Volúmenes de concreto
            _vol_ze   = _Be_a * _Le_a * _He_a
            _vol_zi   = _Bi_a * _Li_a * _Hi_a
            _vol_viga = _bv_a * _hv_a * _Lv_a
            _vol_tot  = _vol_ze + _vol_zi + _vol_viga

            # Excavación
            _vol_exc_ze  = (_Be_a + 0.5) * (_Le_a + 0.5) * _Df_a
            _vol_exc_zi  = (_Bi_a + 0.5) * (_Li_a + 0.5) * _Df_a
            _vol_exc_v   = (_bv_a + 0.30) * _Lv_a * _Df_a
            _vol_exc_tot = _vol_exc_ze + _vol_exc_zi + _vol_exc_v

            # Acero — barras viga
            _db_mm_a = REBAR_DICT.get(_dd_a.get("bar_long","#6"), {}).get("db", 19.05)
            _area_a  = REBAR_DICT.get(_dd_a.get("bar_long","#6"), {}).get("area", 2.85)  # cm²
            _kg_m_a  = _area_a * 1e-4 * 7850       # kg/m
            _n_sup   = _dd_a.get("n_sup", 2)
            _n_inf   = _dd_a.get("n_inf", 2)
            _L_bar   = _Lv_a + 2*(30/100.0)        # con gancho aprox 30cm c/u
            _kg_long = (_n_sup + _n_inf) * _L_bar * _kg_m_a

            # Estribos
            _db_est_mm = REBAR_DICT.get(_dd_a.get("bar_est","#3"), {}).get("db", 9.525)
            _area_est  = REBAR_DICT.get(_dd_a.get("bar_est","#3"), {}).get("area", 0.71)
            _kg_m_est  = _area_est * 1e-4 * 7850
            _s_crit    = _dd_a.get("s_crit_cm", 15.0) / 100.0
            _s_est     = _dd_a.get("s_est_cm",  25.0) / 100.0
            _L_crit    = 2 * _hv_a                  # zona crítica = 2d aprox
            _n_est_crit = max(1, int(_L_crit / _s_crit))
            _n_est_cent = max(1, int((_Lv_a - 2*_L_crit) / _s_est))
            _n_est_tot  = 2 * _n_est_crit + _n_est_cent
            _L_est_1    = 2 * (_bv_a + _hv_a) - 4*0.03 + 0.30  # perímetro - rec + gancho
            _kg_est     = _n_est_tot * _L_est_1 * _kg_m_est

            _kg_tot_a  = _kg_long + _kg_est

            # Cemento/arena/grava
            _bultos_tot = _vol_tot * 350 / 50.0
            _arena_tot  = _vol_tot * 0.55
            _grava_tot  = _vol_tot * 0.80

            # Precios
            _apu_a  = st.session_state.get("apu_config", {})
            _mon_a  = _apu_a.get("moneda", "COP")
            _p_cem  = _apu_a.get("cemento",  32000.0)
            _p_ace  = _apu_a.get("acero",     4500.0)
            _p_are  = _apu_a.get("arena",    85000.0)
            _p_gra  = _apu_a.get("grava",    95000.0)
            _p_exc  = _apu_a.get("costo_excav_m3", 25000.0)
            _p_dia  = _apu_a.get("costo_dia_mo",   69333.33)

            # ── MÉTRICAS ──
            st.markdown("####  Resumen de Cantidades — Sistema Viga de Amarre")
            _cols = st.columns(4)
            _cols[0].metric("⛏ Excavación", f"{_vol_exc_tot:.2f} m³")
            _cols[1].metric(" Concreto Total", f"{_vol_tot:.3f} m³")
            _cols[2].metric(" Acero Total", f"{_kg_tot_a:.1f} kg")
            _cols[3].metric(" Cuantía", f"{_kg_tot_a/_vol_tot:.1f} kg/m³")

            # ── TABLA DESGLOSE ──
            _c_exc_a  = _vol_exc_tot * _p_exc
            _c_cem_a  = _bultos_tot  * _p_cem
            _c_are_a  = _arena_tot   * _p_are
            _c_gra_a  = _grava_tot   * _p_gra
            _c_ace_a  = _kg_tot_a    * _p_ace
            _mat_tot  = _c_exc_a + _c_cem_a + _c_are_a + _c_gra_a + _c_ace_a

            _t_dias = (_kg_tot_a * 0.04) + (_vol_tot * 0.4) + (_vol_exc_tot * 0.3)
            _c_mo   = _t_dias * _p_dia
            _cd     = _mat_tot + _c_mo
            _herra  = _c_mo * _apu_a.get("pct_herramienta", 0.05)
            _aiu    = _cd  * _apu_a.get("pct_aui",         0.30)
            _util   = _cd  * _apu_a.get("pct_util",        0.05)
            _iva    = _util * _apu_a.get("iva",            0.19)
            _gran   = _cd + _herra + _aiu + _iva

            st.markdown("####  Presupuesto Detallado")
            _rows_apu = [
                {"Concepto": "① Excavación total",
                 "Cant.": f"{_vol_exc_tot:.2f} m³",
                 "P.Unit.": f"{_p_exc:,.0f} {_mon_a}/m³",
                 "Subtotal": f"{_c_exc_a:,.0f} {_mon_a}"},
                {"Concepto": "② Cemento",
                 "Cant.": f"{_bultos_tot:.1f} blt",
                 "P.Unit.": f"{_p_cem:,.0f} {_mon_a}/blt",
                 "Subtotal": f"{_c_cem_a:,.0f} {_mon_a}"},
                {"Concepto": "③ Arena",
                 "Cant.": f"{_arena_tot:.3f} m³",
                 "P.Unit.": f"{_p_are:,.0f} {_mon_a}/m³",
                 "Subtotal": f"{_c_are_a:,.0f} {_mon_a}"},
                {"Concepto": "④ Grava",
                 "Cant.": f"{_grava_tot:.3f} m³",
                 "P.Unit.": f"{_p_gra:,.0f} {_mon_a}/m³",
                 "Subtotal": f"{_c_gra_a:,.0f} {_mon_a}"},
                {"Concepto": f"⑤ Acero ({_dd_a.get('bar_long','#?')} long + {_dd_a.get('bar_est','#?')} estr.)",
                 "Cant.": f"{_kg_tot_a:.1f} kg",
                 "P.Unit.": f"{_p_ace:,.0f} {_mon_a}/kg",
                 "Subtotal": f"{_c_ace_a:,.0f} {_mon_a}"},
                {"Concepto": "━━ MATERIALES DIRECTOS",
                 "Cant.": "", "P.Unit.": "",
                 "Subtotal": f"{_mat_tot:,.0f} {_mon_a}"},
                {"Concepto": f"⑥ Mano de Obra ({_t_dias:.1f} días)",
                 "Cant.": f"{_t_dias:.2f} días",
                 "P.Unit.": f"{_p_dia:,.0f} {_mon_a}/día",
                 "Subtotal": f"{_c_mo:,.0f} {_mon_a}"},
                {"Concepto": "━━ COSTO DIRECTO",
                 "Cant.": "", "P.Unit.": "",
                 "Subtotal": f"{_cd:,.0f} {_mon_a}"},
                {"Concepto": f"⑦ Herramienta ({_apu_a.get('pct_herramienta',0.05)*100:.1f}% MO)",
                 "Cant.": "", "P.Unit.": "",
                 "Subtotal": f"{_herra:,.0f} {_mon_a}"},
                {"Concepto": f"⑧ A.I.U. ({_apu_a.get('pct_aui',0.30)*100:.0f}% CD)",
                 "Cant.": "", "P.Unit.": "",
                 "Subtotal": f"{_aiu:,.0f} {_mon_a}"},
                {"Concepto": f"⑨ IVA ({_apu_a.get('iva',0.19)*100:.0f}% Util.)",
                 "Cant.": "", "P.Unit.": "",
                 "Subtotal": f"{_iva:,.0f} {_mon_a}"},
                {"Concepto": "━━ GRAN TOTAL",
                 "Cant.": "", "P.Unit.": "",
                 "Subtotal": f"**{_gran:,.0f} {_mon_a}**"},
            ]
            st.dataframe(pd.DataFrame(_rows_apu), use_container_width=True, hide_index=True)
            st.metric(f" Gran Total Sistema [{_mon_a}]", f"{_gran:,.0f}")

            # Despiece de acero
            st.markdown("####  Despiece de Acero — Viga de Amarre")
            _rows_ace = [
                {"Barra": f"{_dd_a.get('bar_long','#?')} longitudinal superior",
                 "N°": _n_sup, "L [m]": f"{_L_bar:.3f}",
                 "kg/m": f"{_kg_m_a:.3f}", "Peso [kg]": f"{_n_sup*_L_bar*_kg_m_a:.2f}"},
                {"Barra": f"{_dd_a.get('bar_long','#?')} longitudinal inferior",
                 "N°": _n_inf, "L [m]": f"{_L_bar:.3f}",
                 "kg/m": f"{_kg_m_a:.3f}", "Peso [kg]": f"{_n_inf*_L_bar*_kg_m_a:.2f}"},
                {"Barra": f"{_dd_a.get('bar_est','#?')} estribos",
                 "N°": _n_est_tot, "L [m]": f"{_L_est_1:.3f}",
                 "kg/m": f"{_kg_m_est:.3f}", "Peso [kg]": f"{_kg_est:.2f}"},
                {"Barra": "━━ TOTAL",
                 "N°": "", "L [m]": "",
                 "kg/m": "", "Peso [kg]": f"{_kg_tot_a:.2f}"},
            ]
            st.dataframe(pd.DataFrame(_rows_ace), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ Completa las pestañas **Geometría** y **Viga de Amarre** para ver el presupuesto.")

    # ═══════════════════════════════════════════════════════════════════════════
    # FI-5 — REGISTRAR EN CUADRO DE MANDO (Tipos 2/3/4)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("##  Registrar en Cuadro de Mando del Proyecto")
    st.caption("Agrega este sistema al registro multi-zapata para comparación y exportación.")

    if "zapatas_proyecto" not in st.session_state:
        st.session_state["zapatas_proyecto"] = []

    _dis_fi5  = st.session_state.get("zm_dis", {})
    _dist_fi5 = st.session_state.get("zm_dist_e", {})

    _nom_zm = st.text_input(
        "Nombre / Etiqueta (ej. Z-MA-1, Zapata Medianera Eje A)",
        value=f"Z-M{len(st.session_state['zapatas_proyecto'])+1}",
        key="zm_nombre_registro"
    )
    _ca, _cb = st.columns([1, 3])
    if _ca.button(" Agregar al proyecto", type="primary", key="zm_btn_agregar"):
        _entrada_m = {
            "Nombre":         _nom_zm,
            "Tipo":           tipo_zap,
            "B_ext [m]":      round(st.session_state.get("zm_Be", 0.0), 2),
            "L_ext [m]":      round(st.session_state.get("zm_Le", 0.0), 2),
            "H_ext [cm]":     int(st.session_state.get("zm_He", 0)),
            "B_int [m]":      round(st.session_state.get("zm_Bi", 0.0), 2),
            "L_int [m]":      round(st.session_state.get("zm_Li", 0.0), 2),
            "q_adm [kPa]":    round(st.session_state.get("zm_qadm", 0.0), 1),
            "qu_max [kPa]":   round(_dist_fi5.get("qu_max", 0.0), 2),
            "Asentam. [mm]":  0,
            "Norma":          norma,
        }
        if _dis_fi5:
            _entrada_m["h_viga [cm]"]  = _dis_fi5.get("h_cm", "—")
            _entrada_m["As_sup [cm²]"] = round(_dis_fi5.get("As_sup", 0.0), 2)
            _entrada_m["ok_hmin"]      = "" if _dis_fi5.get("ok_hmin") else ""
            _entrada_m["ok_cort"]      = "" if _dis_fi5.get("ok_cort") else ""
        st.session_state["zapatas_proyecto"].append(_entrada_m)
        st.success(
            f" **{_nom_zm}** registrada — "
            f"Total acumulado: **{len(st.session_state['zapatas_proyecto'])}** zapata(s)."
        )

    _n_proy = len(st.session_state.get("zapatas_proyecto", []))
    if _n_proy > 0:
        st.info(
            f" **{_n_proy}** zapata(s) en el proyecto.  "
            "Ve a **Zapata Tipo 1** para ver el cuadro de mando y exportar a Excel."
        )
