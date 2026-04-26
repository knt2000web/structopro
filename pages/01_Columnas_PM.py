import streamlit as st
from normas_referencias import mostrar_referencias_norma
st.set_page_config(
    page_title="StructoPro — Columnas P-M",
    page_icon=None,
    layout="wide"
)

#  Utilidad: Color AutoCAD segun # de cuartos de pulgada 
def _color_acero_dxf(db_mm: float) -> int:
    """Diferenciación visual por diámetro — colores AutoCAD estándar.
    En papel/ploteo usar pluma Color 7. En pantalla diferencia diámetros.
    NSR-10 / práctica colombiana de talleres."""
    if db_mm <= 9.5:   return 3   # Verde  → No.3 (3/8")
    elif db_mm <= 12.7: return 2  # Amarillo → No.4 (1/2")
    elif db_mm <= 15.9: return 1  # Rojo   → No.5 (5/8")
    elif db_mm <= 19.1: return 5  # Azul   → No.6 (3/4")
    elif db_mm <= 22.2: return 6  # Magenta → No.7 (7/8")
    else:               return 4  # Cian   → No.8+ (1"+)
# 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import math
import io
# ── Imports protegidos (Prompt Maestro UX v6.0) ──────────────────────────────
try:
    import ezdxf
    DXFEXT = True
except ImportError:
    ezdxf = None
    DXFEXT = False

try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCXOK = True
except ImportError:
    DOCXOK = False
# ─────────────────────────────────────────────────────────────────────────────
try:
    import requests
    REQOK = True
except ImportError:
    REQOK = False

import plotly.graph_objects as go
import json
import datetime
try:
    import ifc_export
except ImportError:
    ifc_export = None
import os
from pathlib import Path
try:
    import qrcode
    from PIL import Image
    HAS_QR = True
except ImportError:
    HAS_QR = False
import tempfile

# 
# IDIOMA GLOBAL
lang = st.session_state["idioma"] if "idioma" in st.session_state else "Español"
def _t(es, en):
    return en if lang == "English" else es
# 


# 
# PERSISTENCIA SUPABASE
# 
import requests


# =============================================================================
# FEATURE D — Tabla de combinaciones de carga (Diagrama P-M multi-punto)
# =============================================================================
def parse_combo_table(df_combos, factor_fuerza):
    puntos = []
    for i, row in df_combos.iterrows():
        try:
            pu  = float(row.get('Pu',  row.get('pu',  0))) / factor_fuerza
            mux = float(row.get('Mux', row.get('mux', 0))) / factor_fuerza
            muy = float(row.get('Muy', row.get('muy', 0))) / factor_fuerza
            lbl = str(row.get('Combinacion', row.get('combo', f'C{i+1}')))
            puntos.append((pu, mux, muy, lbl))
        except Exception:
            pass
    return puntos


def plot_pm_combos(cap_x, Pu_single, Mux_single, puntos_combo,
                   factor_fuerza, unidad_fuerza, unidad_mom):
    COLORS = ['#f87171','#fb923c','#facc15','#4ade80','#34d399',
              '#60a5fa','#a78bfa','#f472b6','#e879f9','#94a3b8']
    fig, ax = plt.subplots(figsize=(7, 8))
    fig.patch.set_facecolor('#1e1e2e'); ax.set_facecolor('#14142a')
    ax.tick_params(colors='#cdd6f4', labelsize=8)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    for sp in ['bottom','left']: ax.spines[sp].set_color('#555')
    ax.xaxis.label.set_color('#cdd6f4'); ax.yaxis.label.set_color('#cdd6f4')
    Mn_c = [v*factor_fuerza for v in cap_x['phi_Mn']]
    Pn_c = [v*factor_fuerza for v in cap_x['phi_Pn']]
    ax.plot(Mn_c, Pn_c, color='#60a5fa', lw=2.5, label='Diagrama \u03c6P-\u03c6M')
    ax.fill_betweenx(Pn_c, 0, Mn_c, alpha=0.08, color='#60a5fa')
    ax.plot(abs(Mux_single)*factor_fuerza, Pu_single*factor_fuerza,
            'D', ms=9, color='#facc15', zorder=8,
            markeredgecolor='white', markeredgewidth=0.8,
            label=f'Punto actual Pu={Pu_single*factor_fuerza:.1f} {unidad_fuerza}')
    for i, (pu, mux, muy, lbl) in enumerate(puntos_combo):
        c = COLORS[i % len(COLORS)]
        ax.plot(abs(mux)*factor_fuerza, pu*factor_fuerza, 'o', ms=7, color=c, zorder=7,
                markeredgecolor='white', markeredgewidth=0.5,
                label=f'{lbl}: ({abs(mux)*factor_fuerza:.1f}, {pu*factor_fuerza:.1f})')
    ax.axhline(0, color='#555', lw=0.8); ax.axvline(0, color='#555', lw=0.8)
    ax.set_xlabel(f'Momento M [{unidad_mom}]', fontsize=9)
    ax.set_ylabel(f'Carga Axial P [{unidad_fuerza}]', fontsize=9)
    ax.set_title('Diagrama P-M \u2014 Todas las Combinaciones de Carga',
                 color='white', fontsize=10, fontweight='bold')
    ax.legend(loc='upper right', fontsize=6.5, framealpha=0.3,
              facecolor='#1e1e2e', edgecolor='#555', labelcolor='#cdd6f4', ncol=1)
    ax.grid(True, linestyle=':', alpha=0.2, color='#888'); fig.tight_layout()
    return fig


# =============================================================================
# FEATURE E — Alzado 2D de Confinamiento
# =============================================================================
def plot_alzado_confinamiento(L_col_cm, Lo_cm, s_conf_cm, s_centro_cm,
                               b_cm, h_cm, es_circular,
                               rebar_diam_mm, stirrup_diam_mm, norma_sel, coderef):
    from matplotlib.lines import Line2D
    W = h_cm; L = L_col_cm; Lo = Lo_cm; s1 = s_conf_cm; s2 = s_centro_cm; cov = 3.8
    fig, ax = plt.subplots(figsize=(5, 10))
    fig.patch.set_facecolor('#1e1e2e'); ax.set_facecolor('#14142a')
    ax.tick_params(colors='#cdd6f4', labelsize=7)
    for sp in ax.spines.values(): sp.set_color('#555')
    ax.xaxis.label.set_color('#cdd6f4'); ax.yaxis.label.set_color('#cdd6f4')
    ax.add_patch(plt.Rectangle((0, 0), W, L, lw=2, edgecolor='#94a3b8', facecolor='#2d3748', zorder=1))
    for y0 in [0, L-Lo]:
        ax.add_patch(plt.Rectangle((cov, y0), W-2*cov, Lo, lw=0, facecolor='#f9731620', zorder=2))
        ax.add_patch(plt.Rectangle((cov, y0), W-2*cov, Lo, lw=1.5, edgecolor='#f97316',
                                    facecolor='none', linestyle='--', zorder=3))
    # estribos zona Lo inf
    y = s1
    while y <= Lo - s1*0.5:
        ax.plot([cov, W-cov], [y, y], color='#f97316', lw=1.2, zorder=4); y += s1
    # estribos zona central
    y = Lo + s2
    while y <= L - Lo - s2*0.5:
        ax.plot([cov, W-cov], [y, y], color='#60a5fa', lw=1.0, linestyle='--', zorder=4); y += s2
    # estribos zona Lo sup
    y = L - Lo + s1
    while y <= L - s1*0.5:
        ax.plot([cov, W-cov], [y, y], color='#f97316', lw=1.2, zorder=4); y += s1
    # barras longitudinales
    for xb in [cov + rebar_diam_mm/20, W - cov - rebar_diam_mm/20]:
        ax.plot([xb, xb], [cov, L-cov], color='#ff6b35', lw=2.5, zorder=5)
    # cotas
    def cota(y1, y2, texto, lado='r'):
        xc = W+6 if lado=='r' else -6; dx=3
        for y in [y1,y2]: ax.plot([xc-dx, xc+dx], [y,y], color='#a3e635', lw=0.8)
        ax.annotate('', xy=(xc,y2), xytext=(xc,y1),
                    arrowprops=dict(arrowstyle='<->', color='#a3e635', lw=0.9))
        ax.text(xc+dx+1, (y1+y2)/2, texto, color='#a3e635', fontsize=7, va='center')
    cota(0, Lo,   f'Lo={Lo:.0f} cm\ns\u2081={s1:.0f} cm')
    cota(Lo, L-Lo, f'Libre\ns\u2082={s2:.0f} cm')
    cota(L-Lo, L, f'Lo={Lo:.0f} cm\ns\u2081={s1:.0f} cm')
    cota(0, L,    f'L={L:.0f} cm', lado='l')
    ax.text(W/2, Lo/2, 'ZONA\nCONFINADA', color='#f97316', fontsize=7, ha='center', va='center', fontweight='bold', zorder=6)
    ax.text(W/2, L-Lo/2, 'ZONA\nCONFINADA', color='#f97316', fontsize=7, ha='center', va='center', fontweight='bold', zorder=6)
    ax.text(W/2, L/2, 'ZONA\nCENTRAL', color='#60a5fa', fontsize=7, ha='center', va='center', zorder=6)
    leg = [Line2D([0],[0], color='#f97316', lw=1.5, label=f'Estribos s\u2081={s1:.0f} cm (confinamiento)'),
           Line2D([0],[0], color='#60a5fa', lw=1.0, linestyle='--', label=f'Estribos s\u2082={s2:.0f} cm (zona libre)'),
           Line2D([0],[0], color='#ff6b35', lw=2.5, label='Barras longitudinales')]
    ax.legend(handles=leg, loc='upper center', bbox_to_anchor=(0.5,-0.04), fontsize=7,
              framealpha=0.3, facecolor='#1e1e2e', edgecolor='#555', labelcolor='#cdd6f4', ncol=1)
    sec = f"Circular D={h_cm:.0f} cm" if es_circular else f"Rectangular {b_cm:.0f}\xd7{h_cm:.0f} cm"
    ax.set_title(f'Alzado Confinamiento \u2014 {sec}\n{norma_sel}', color='white', fontsize=9, fontweight='bold')
    ax.set_xlim(-10, W+22); ax.set_ylim(-10, L+10); ax.set_aspect('equal'); ax.axis('off')
    fig.tight_layout()
    return fig

def get_supabase_rest_info():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return url, key
    except Exception as e:
        return None, None

def guardar_proyecto_supabase(nombre, estado_dict):
    url, key = get_supabase_rest_info()
    if not url or not key:
        try:
            import os
            db_path = "db_proyectos_columnas.json"
            db = {}
            if os.path.exists(db_path):
                with open(db_path, "r", encoding="utf-8") as f: db = json.load(f)
            db[f"[COLUMNAS] {nombre}"] = {"nombre_proyecto": f"[COLUMNAS] {nombre}", "estado_json": json.dumps(estado_dict)}
            with open(db_path, "w", encoding="utf-8") as f: json.dump(db, f)
            return True, " Proyecto guardado (Local)"
        except Exception as e:
            return False, f" Error guardado local: {e}"
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    payload = {
        "nombre_proyecto": nombre,
        "user_id": st.session_state.get("user_id", "anonimo"),
        "estado_json": json.dumps(estado_dict),
    }
    
    try:
        endpoint = f"{url}/rest/v1/proyectos?on_conflict=nombre_proyecto"
        res = requests.post(endpoint, headers=headers, json=payload)
        if res.status_code in [200, 201, 204]:
            return True, " Proyecto guardado en la nube"
        else:
            return False, f" Error API: {res.text}"
    except Exception as e:
        return False, f" Error al guardar: {e}"

def cargar_proyecto_supabase(nombre):
    url, key = get_supabase_rest_info()
    if not url or not key:
        try:
            import os
            db_path = "db_proyectos_columnas.json"
            if os.path.exists(db_path):
                with open(db_path, "r", encoding="utf-8") as f: db = json.load(f)
                match = db.get(f"[COLUMNAS] {nombre}") or db.get(nombre)
                if match:
                    estado = json.loads(match["estado_json"])
                    for k, v in estado.items(): st.session_state[k] = v
                    return True, f" Proyecto '{nombre}' cargado (Local)"
            return False, f" No se encontró el proyecto '{nombre}' localmente"
        except Exception as e:
            return False, f" Excepción al cargar local: {e}"
        
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json"
    }
    
    try:
        endpoint = f"{url}/rest/v1/proyectos?nombre_proyecto=eq.{nombre}&select=*"
        res = requests.get(endpoint, headers=headers)
        
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                estado = json.loads(data[0]["estado_json"])
                for k, v in estado.items():
                    st.session_state[k] = v
                return True, f" Proyecto '{nombre}' cargado"
            else:
                return False, f" No se encontró el proyecto '{nombre}'"
        else:
            return False, f" Error al cargar (API): {res.text}"
    except Exception as e:
        return False, f" Excepción al cargar: {e}"

def listar_proyectos_supabase():
    url, key = get_supabase_rest_info()
    if not url or not key:
        try:
            import os
            db_path = "db_proyectos_columnas.json"
            if os.path.exists(db_path):
                with open(db_path, "r", encoding="utf-8") as f: db = json.load(f)
                return sorted([k.replace("[COLUMNAS] ", "") for k in db.keys()])
            return []
        except Exception:
            return []
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json"
    }
    
    try:
        endpoint = f"{url}/rest/v1/proyectos?select=nombre_proyecto"
        res = requests.get(endpoint, headers=headers)
        if res.status_code == 200:
            data = res.json()
            nombres = [item["nombre_proyecto"] for item in data if "nombre_proyecto" in item]
            return sorted(nombres)
        return []
    except Exception:
        return []

# 
# PANEL DE BIENVENIDA — info normativa visible siempre en cada módulo
# 
def _panel_normativo(titulo, descripcion, inputs_requeridos, fc, fy,
                     rhomin, rhomax, phif, phiv, normasel, nivelsis, coderef):
    st.markdown(
        f"""<div style="background:#1a2a1a;border-left:4px solid #4caf50;
        border-radius:8px;padding:14px 18px;margin-bottom:16px;">
        <span style="color:#81c784;font-weight:700;font-size:15px;"> {titulo}</span><br>
        <span style="color:#aaa;font-size:13px;">{descripcion}</span>
        </div>""",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("φ flexión/axial", f"{phif:.2f}/{phiv:.2f}", help=coderef)
    c2.metric("φ cortante", "0.75", help=coderef)
    c3.metric("ρ mín", f"{rhomin:.4f}", help="Cuantía mínima longitudinal")
    c4.metric("ρ máx", f"{rhomax:.4f}", help="Cuantía máxima")
    c5.metric("fc / fy", f"{fc:.0f} / {fy:.0f} MPa", help="Materiales activos")
    st.caption(f" Norma: **{norma_sel}** | Nivel sísmico: **{nivelsis}** | Ref: {coderef}")
    if inputs_requeridos:
        with st.expander(" Datos requeridos para este módulo", expanded=False):
            for item in inputs_requeridos:
                st.markdown(f"- {item}")
    st.markdown("---")


def capturar_estado_actual():
    claves = [
        "c_pm_norma", "c_pm_nivel_sismico", "c_pm_fc_unit", "c_pm_fc_mpa", "c_pm_psichoice", "c_pm_kgcm2choice",
        "c_pm_fy", "c_pm_seccion_type", "c_pm_b", "c_pm_h", "c_pm_D",
        "c_pm_d_prime", "c_pm_L", "c_pm_unit_system", "c_pm_rebar_type",
        "c_pm_num_h", "c_pm_num_v", "c_pm_n_barras_circ",
        "c_pm_col_type", "c_pm_stirrup_type", "c_pm_paso_circ", "c_pm_paso_rect",
        "c_pm_mux", "c_pm_muy", "c_pm_pu",
        "c_pm_output_units", "c_pm_k",
        # Factor k de esbeltez
        "c_pm_k", "c_pm_beta_dns",
        # APU concreto premezclado
        "col_apu_premix", "col_apu_premix_p",
        "col_apu_moneda", "col_apu_cemento", "col_apu_acero", "col_apu_arena", "col_apu_grava", "col_apu_mo", "col_apu_aui",
        # Rótulo ICONTEC para DXF
        "dxf_empresa", "dxf_proyecto", "dxf_plano", "dxf_elaboro", "dxf_reviso", "dxf_aprobo",
        "qr_url",
        "cpm_empresa","cpm_proyecto_nombre","cpm_ingeniero",
    ]
    return {k: st.session_state[k] for k in claves if k in st.session_state}

# 
# FIX BUG #4: Manejo seguro de BASE_DIR para Streamlit Cloud
# 
st.markdown("""<div style="width:100%;overflow:hidden;border-radius:14px;margin-bottom:20px;box-shadow:0 4px 32px #0008;">
<svg viewBox="0 0 1100 220" xmlns="http://www.w3.org/2000/svg" style="width:100%;display:block;background:linear-gradient(135deg,#07091a 0%,#0d1b3e 100%);">
  <!-- Grid lines -->
  <g opacity="0.07" stroke="#60a5fa" stroke-width="0.5">
    <line x1="0" y1="55" x2="1100" y2="55"/><line x1="0" y1="110" x2="1100" y2="110"/>
    <line x1="0" y1="165" x2="1100" y2="165"/>
    <line x1="220" y1="0" x2="220" y2="220"/><line x1="440" y1="0" x2="440" y2="220"/>
    <line x1="660" y1="0" x2="660" y2="220"/>
  </g>
  <!-- Top accent bar -->
  <rect x="0" y="0" width="1100" height="3" fill="#3b82f6" opacity="0.9"/>
  <!-- Bottom accent bar -->
  <rect x="0" y="217" width="1100" height="3" fill="#8b5cf6" opacity="0.7"/>

  <!--  SECTION RECTANGULAR  -->
  <g transform="translate(45,25)">
    <text x="35" y="-6" text-anchor="middle" font-family="monospace" font-size="9" fill="#6b7280" letter-spacing="1.5">SECCION RECT.</text>
    <rect x="0" y="0" width="70" height="165" rx="2" fill="#2d3748" stroke="#718096" stroke-width="1.5"/>
    <rect x="8" y="8" width="54" height="149" rx="1" fill="none" stroke="#00d4ff" stroke-width="2" stroke-dasharray="none" opacity="0.85"/>
    <!-- Bars -->
    <circle cx="12" cy="12" r="5.5" fill="#e8a838"/><circle cx="35" cy="12" r="5.5" fill="#e8a838"/>
    <circle cx="58" cy="12" r="5.5" fill="#e8a838"/><circle cx="12" cy="84" r="5.5" fill="#e8a838"/>
    <circle cx="58" cy="84" r="5.5" fill="#e8a838"/><circle cx="12" cy="153" r="5.5" fill="#e8a838"/>
    <circle cx="35" cy="153" r="5.5" fill="#e8a838"/><circle cx="58" cy="153" r="5.5" fill="#e8a838"/>
    <!-- Stirrups -->
    <rect x="8" y="38" width="54" height="0" fill="none" stroke="#00d4ff" stroke-width="0.8" opacity="0.5"/>
    <rect x="8" y="68" width="54" height="0" fill="none" stroke="#00d4ff" stroke-width="0.8" opacity="0.5"/>
    <rect x="8" y="98" width="54" height="0" fill="none" stroke="#00d4ff" stroke-width="0.8" opacity="0.5"/>
    <rect x="8" y="128" width="54" height="0" fill="none" stroke="#00d4ff" stroke-width="0.8" opacity="0.5"/>
    <!-- Dim b -->
    <line x1="0" y1="178" x2="70" y2="178" stroke="#60a5fa" stroke-width="0.8"/>
    <text x="35" y="190" text-anchor="middle" font-family="monospace" font-size="10" fill="#93c5fd">b = 40 cm</text>
    <!-- Dim h -->
    <line x1="78" y1="0" x2="78" y2="165" stroke="#60a5fa" stroke-width="0.8"/>
    <text x="88" y="86" font-family="monospace" font-size="10" fill="#93c5fd">h=60</text>
  </g>

  <!--  SECTION CIRCULAR  -->
  <g transform="translate(200,35)">
    <text x="52" y="-6" text-anchor="middle" font-family="monospace" font-size="9" fill="#6b7280" letter-spacing="1.5">SECCION CIRC.</text>
    <circle cx="52" cy="60" r="52" fill="#2d3748" stroke="#718096" stroke-width="1.5"/>
    <circle cx="52" cy="60" r="45" fill="none" stroke="#00d4ff" stroke-width="2" opacity="0.85"/>
    <circle cx="52" cy="15" r="5.5" fill="#e8a838"/><circle cx="89" cy="33" r="5.5" fill="#e8a838"/>
    <circle cx="97" cy="72" r="5.5" fill="#e8a838"/><circle cx="77" cy="104" r="5.5" fill="#e8a838"/>
    <circle cx="52" cy="107" r="5.5" fill="#e8a838"/><circle cx="27" cy="104" r="5.5" fill="#e8a838"/>
    <circle cx="7" cy="72" r="5.5" fill="#e8a838"/><circle cx="15" cy="33" r="5.5" fill="#e8a838"/>
    <text x="52" y="135" text-anchor="middle" font-family="monospace" font-size="10" fill="#93c5fd">D = 60 cm</text>
  </g>

  <!--  P-M DIAGRAM  -->
  <g transform="translate(360,18)">
    <text x="95" y="-4" text-anchor="middle" font-family="monospace" font-size="9" fill="#6b7280" letter-spacing="1.5">DIAGRAMA P-M (NSR-10 C.10)</text>
    <line x1="18" y1="185" x2="18" y2="8" stroke="#60a5fa" stroke-width="1.2"/>
    <line x1="18" y1="185" x2="195" y2="185" stroke="#60a5fa" stroke-width="1.2"/>
    <polygon points="18,4 14,13 22,13" fill="#60a5fa"/>
    <polygon points="199,185 190,181 190,189" fill="#60a5fa"/>
    <text x="9" y="10" font-family="monospace" font-size="11" fill="#60a5fa">P</text>
    <text x="200" y="189" font-family="monospace" font-size="11" fill="#60a5fa">M</text>
    <path d="M18,22 C18,22 38,26 75,48 C115,72 158,130 168,158 C176,178 162,185 152,185 L18,185 Z"
          fill="none" stroke="#3b82f6" stroke-width="2.2"/>
    <path d="M18,38 C18,38 34,43 67,63 C103,85 143,140 152,164 C159,182 148,185 139,185 L18,185 Z"
          fill="#3b82f615" stroke="#8b5cf6" stroke-width="1.4" stroke-dasharray="5,3"/>
    <circle cx="128" cy="144" r="5" fill="#f59e0b"/>
    <line x1="128" y1="144" x2="128" y2="185" stroke="#f59e0b" stroke-width="0.8" stroke-dasharray="3,3"/>
    <line x1="18" y1="144" x2="128" y2="144" stroke="#f59e0b" stroke-width="0.8" stroke-dasharray="3,3"/>
    <text x="130" y="140" font-family="monospace" font-size="8" fill="#fbbf24">Bal.</text>
    <line x1="22" y1="200" x2="50" y2="200" stroke="#3b82f6" stroke-width="2"/>
    <text x="53" y="204" font-family="monospace" font-size="9" fill="#93c5fd">Nominal</text>
    <line x1="100" y1="200" x2="128" y2="200" stroke="#8b5cf6" stroke-width="1.4" stroke-dasharray="5,3"/>
    <text x="131" y="204" font-family="monospace" font-size="9" fill="#a78bfa">Reducido</text>
  </g>

  <!--  TEXT BLOCK  -->
  <g transform="translate(622,0)">
    <rect x="0" y="28" width="4" height="165" rx="2" fill="#3b82f6"/>
    <text x="18" y="68" font-family="Arial,sans-serif" font-size="34" font-weight="bold" fill="#ffffff">COLUMNAS</text>
    <text x="18" y="96" font-family="Arial,sans-serif" font-size="18" font-weight="300" fill="#93c5fd" letter-spacing="2">DIAGRAMAS P-M BIAXIAL</text>
    <rect x="18" y="104" width="440" height="1" fill="#3b82f6" opacity="0.5"/>
    <!-- Tags -->
    <rect x="18" y="115" width="108" height="22" rx="11" fill="#1e3a5f" stroke="#3b82f6" stroke-width="1"/>
    <text x="72" y="130" text-anchor="middle" font-family="Arial,sans-serif" font-size="9" font-weight="bold" fill="#60a5fa">NSR-10 / ACI 318</text>
    <rect x="132" y="115" width="112" height="22" rx="11" fill="#2d1f4e" stroke="#8b5cf6" stroke-width="1"/>
    <text x="188" y="130" text-anchor="middle" font-family="Arial,sans-serif" font-size="9" font-weight="bold" fill="#a78bfa">CONFINAMIENTO DMO</text>
    <rect x="250" y="115" width="98" height="22" rx="11" fill="#1a3a2a" stroke="#10b981" stroke-width="1"/>
    <text x="299" y="130" text-anchor="middle" font-family="Arial,sans-serif" font-size="9" font-weight="bold" fill="#34d399">IFC / DXF ICONTEC</text>
    <rect x="354" y="115" width="88" height="22" rx="11" fill="#3a1a1a" stroke="#ef4444" stroke-width="1"/>
    <text x="398" y="130" text-anchor="middle" font-family="Arial,sans-serif" font-size="9" font-weight="bold" fill="#f87171">ESPIRAL / ESTRIBO</text>
    <!-- Description -->
    <text x="18" y="158" font-family="Arial,sans-serif" font-size="11" fill="#64748b">Verificacion de capacidad a flexocompresion biaxial segun</text>
    <text x="18" y="174" font-family="Arial,sans-serif" font-size="11" fill="#64748b">NSR-10 C.10 / ACI 318-19 Cap. 10 — Planos ICONTEC en</text>
    <text x="18" y="190" font-family="Arial,sans-serif" font-size="11" fill="#64748b">formatos Carta, Oficio, Medio Pliego y Pliego. BIM IFC4.</text>
  </g>
</svg></div>""", unsafe_allow_html=True)


st.title(_t("Diagrama de Interacción P–M (Biaxial) y Diseño de Estribos", " P-M (Biaxial) Interaction Diagram & Tie Design"))
st.markdown(_t(
    "Generador interactivo de capacidad a flexocompresión **biaxial** para **Columnas Cuadradas, Rectangulares y Circulares**.",
    "Interactive **biaxial** flexure-compression capacity generator for **Square, Rectangular and Circular Columns**."
))

with st.expander(" ¿Cómo usar este módulo? — Guía Profesional", expanded=False):
    st.markdown("""
    ### Metodología y Flujo de Diseño (Flexocompresión Biaxial)
    Este módulo evalúa la capacidad resistente de columnas (Cuadradas, Rectangulares y Circulares) modelando la topología tridimensional del acero bajo las prescripciones normativas NSR-10 y ACI-318.
    
    ####  1. Geometría y Cuantías Base
    - Determina las dimensiones de la sección transversal ($b$, $h$ o $D$) en función del predimensionamiento.
    - Distribuye el acero longitudinal perimetralmente (Caras X, Y o contorno circular).
    - **Criterio Normativo:** Asegure que la cuantía $\\rho$ se ubique entre el $1\%$ mínimo y el límite sísmico según su grado de disipación de energía ($4\%$ a $6\%$).
    
    ####  2. Demanda Biaxial LRFD
    - Ingrese los esfuerzos últimos factorados: Carga Axial ($P_{u}$), Momento $X$ ($M_{ux}$) y Momento $Y$ ($M_{uy}$).
    - Evalúe efectos de esbeltez global ajustando el factor $k_{u}$ y luz libre $L_{c}$ si su estructura es desplazable.
    
    ####  3. Evaluación de Capacidad e Interacción (DCR)
    - El módulo traza las gráficas de interacción Uniaxiales puras (Planos $P-M_x$ y $P-M_y$).
    - Ejecuta el criterio de la **Superficie de Carga Biaxial** ($1/\\phi P_{ni} = 1/\\phi P_{nx} + 1/\\phi P_{ny} - 1/\\phi P_0$) para certificar si el punto de solicitación tridimensional queda dentro de la cebolla de falla.
    - **Índice de Capacidad (IFC):** Busque mantener un $DCR$ (Demanda/Capacidad) $\\leq 1.0$.
    
    ####  4. Diseño Transversal C.21
    - En base al Nivel de Amenaza Sísmica (DES, DMO, DMI), genere el despiece preciso para Estribos Cerrados, Ganchos C a 135° o Zunchos en espiral continua en las zonas confinadas ($l_o$).
    - Exporte Memorias DOCX y modelos IFC de alto LOD (Nivel de Desarrollo).
    """)

# 
# DICCIONARIOS DE BARRAS
# 
REBAR_US = {
    "#3 (3/8\")": {"area": 0.71, "diam_mm": 9.53},
    "#4 (1/2\")": {"area": 1.29, "diam_mm": 12.70},
    "#5 (5/8\")": {"area": 1.99, "diam_mm": 15.88},
    "#6 (3/4\")": {"area": 2.84, "diam_mm": 19.05},
    "#7 (7/8\")": {"area": 3.87, "diam_mm": 22.23},
    "#8 (1\")":   {"area": 5.10, "diam_mm": 25.40},
    "#9 (1 1/8\")": {"area": 6.45, "diam_mm": 28.65},
    "#10 (1 1/4\")": {"area": 7.92, "diam_mm": 32.26},
}

REBAR_MM = {
    "10 mm": {"area": 0.785, "diam_mm": 10.0},
    "12 mm": {"area": 1.131, "diam_mm": 12.0},
    "14 mm": {"area": 1.539, "diam_mm": 14.0},
    "16 mm": {"area": 2.011, "diam_mm": 16.0},
    "18 mm": {"area": 2.545, "diam_mm": 18.0},
    "20 mm": {"area": 3.142, "diam_mm": 20.0},
    "22 mm": {"area": 3.801, "diam_mm": 22.0},
    "25 mm": {"area": 4.909, "diam_mm": 25.0},
    "28 mm": {"area": 6.158, "diam_mm": 28.0},
    "32 mm": {"area": 8.042, "diam_mm": 32.0},
}

STIRRUP_US = {
    "#2 (1/4\")": {"area": 0.32, "diam_mm": 6.35},
    "#3 (3/8\")": {"area": 0.71, "diam_mm": 9.53},
    "#4 (1/2\")": {"area": 1.29, "diam_mm": 12.70},
}

STIRRUP_MM = {
    "6 mm":  {"area": 0.283, "diam_mm": 6.0},
    "8 mm":  {"area": 0.503, "diam_mm": 8.0},
    "10 mm": {"area": 0.785, "diam_mm": 10.0},
    "12 mm": {"area": 1.131, "diam_mm": 12.0},
}

# 
# FUNCIONES DE DIBUJO PARA FIGURADO
# 
_MM_TO_BAR = {
    6.0:  "#2 (1/4\")",  6.35: "#2 (1/4\")",
    8.0:  "#2.5 (5/16\")",
    9.53: "#3 (3/8\")",  10.0: "#3 (3/8\")",
    12.0: "#4 (1/2\")",  12.70: "#4 (1/2\")",
    14.0: "#4.5 (9/16\")",
    15.88: "#5 (5/8\")", 16.0: "#5 (5/8\")",
    18.0: "#5.7 (11/16\")",
    19.05: "#6 (3/4\")", 20.0: "#6 (3/4\")",
    22.0: "#7 (7/8\")",  22.23: "#7 (7/8\")",
    25.0: "#8 (1\")",    25.40: "#8 (1\")",
    28.0: "#9 (1 1/8\")",28.65: "#9 (1 1/8\")",
    32.0: "#10 (1 1/4\")",32.26: "#10 (1 1/4\")",
}

def _bar_label(diam_mm):
    """Retorna la designación colombiana NSR-10: #N (fracción") — Ø mm"""
    best = min(_MM_TO_BAR.keys(), key=lambda k: abs(k - diam_mm))
    if abs(best - diam_mm) <= 2.0:
        return f"{_MM_TO_BAR[best]}  Ø{diam_mm:.1f} mm"
    return f"Ø{diam_mm:.1f} mm"

def _bar_label_short(diam_mm):
    """Retorna solo la designación colombiana: #N (fracción"), sin mm — para títulos y gráficos."""
    best = min(_MM_TO_BAR.keys(), key=lambda k: abs(k - diam_mm))
    if abs(best - diam_mm) <= 2.0:
        return _MM_TO_BAR[best]
    return f"Ø{diam_mm:.1f} mm"

def configurar_pdf_comercial(fig):
    fig.patch.set_facecolor('white')
    for _ax in fig.get_axes():
        _ax.set_facecolor('white')
        _ax.tick_params(colors='black')
        for spine in _ax.spines.values():
            spine.set_edgecolor('black')
            spine.set_linewidth(1.5)
        _ax.xaxis.label.set_color('black')
        _ax.yaxis.label.set_color('black')
        if _ax.get_title(): _ax.title.set_color('black')

def draw_longitudinal_bar(total_len_cm, straight_len_cm, hook_len_cm, bar_diam_mm, bar_name=None):
    label = bar_name if bar_name else _bar_label(bar_diam_mm)
    fig, ax = plt.subplots(figsize=(max(6, total_len_cm/20), 2))
    fig.patch.set_facecolor('#1e1e2e')
    for _ax in fig.get_axes(): _ax.set_facecolor('#14142a'); _ax.tick_params(colors='#cdd6f4'); _ax.xaxis.label.set_color('#cdd6f4'); _ax.yaxis.label.set_color('#cdd6f4')
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
    ax.set_title(f"Varilla L1 — {label} — Longitud total {total_len_cm:.0f} cm", fontsize=9, fontweight='bold')
    return fig

def draw_stirrup(b_cm, h_cm, hook_len_cm, bar_diam_mm, bar_name=None):
    import math as _math
    import numpy as _np
    label = bar_name if bar_name else _bar_label(bar_diam_mm)
    fig, ax = plt.subplots(figsize=(max(5, b_cm/12), max(4, h_cm/12)))
    fig.patch.set_facecolor('#1e1e2e')
    for _ax in fig.get_axes():
        _ax.set_facecolor('#14142a')
        _ax.tick_params(colors='#cdd6f4')
        _ax.xaxis.label.set_color('#cdd6f4')
        _ax.yaxis.label.set_color('#cdd6f4')
    ax.set_aspect('equal')

    x0, y0 = 0.0, 0.0
    # Radio doblez 3db (NSR-10 C.7.2), mínimo 0.3 cm
    r = max(min(bar_diam_mm / 10.0 * 3.0, b_cm * 0.08, h_cm * 0.08), 0.3)

    def _arc(cx, cy, rad, a0, a1, n=10):
        angs = _np.linspace(_math.radians(a0), _math.radians(a1), n)
        return [(cx + rad*_math.cos(a), cy + rad*_math.sin(a)) for a in angs]

    # ── Perímetro con 4 esquinas redondeadas ─────────────────────────────
    # Arranca desde (x0, y0+h_cm-r) = pie del arco sup-izq, lado izquierdo
    # Sentido: baja por izq → inf-izq → inf → inf-der → sube por der → sup-der → sup → arco sup-izq
    pts = []
    pts.append((x0, y0 + h_cm - r))           # inicio lado izq (donde nace gancho 1)
    pts += _arc(x0+r, y0+r,       r, 180, 270) # esquina inf-izq
    pts.append((x0+b_cm-r, y0))               # lado inferior
    pts += _arc(x0+b_cm-r, y0+r,  r, 270, 360) # esquina inf-der
    pts.append((x0+b_cm, y0+h_cm-r))          # lado der
    pts += _arc(x0+b_cm-r, y0+h_cm-r, r, 0, 90)  # esquina sup-der
    pts.append((x0+r, y0+h_cm))               # lado sup (desde donde nace gancho 2)
    pts += _arc(x0+r, y0+h_cm-r,  r, 90, 180) # arco sup-izq
    pts.append((x0, y0+h_cm-r))               # cierra en el mismo punto de inicio

    ax.plot([p[0] for p in pts], [p[1] for p in pts], color='white', linewidth=2.5)

    # ── Dos ganchos 135° — ambos salen de esquina SUP-IZQ hacia NÚCLEO (+X, -Y)
    vis = min(hook_len_cm, b_cm*0.32, h_cm*0.32)
    dx =  vis * _math.cos(_math.radians(45))   # +X  (hacia interior)
    dy = -vis * _math.sin(_math.radians(45))   # -Y  (hacia interior)

    # Gancho 1: desde pie del arco sup-izq en el lado IZQUIERDO
    ax.plot([x0,     x0+dx],            [y0+h_cm-r, y0+h_cm-r+dy], color='white', linewidth=2.5)
    ax.plot(x0+dx, y0+h_cm-r+dy, 'o',  color='#ff4444', markersize=5, zorder=5)

    # Gancho 2: desde inicio del lado SUPERIOR (derecha → izquierda)
    ax.plot([x0+r,   x0+r+dx],          [y0+h_cm,   y0+h_cm+dy],   color='white', linewidth=2.5)
    ax.plot(x0+r+dx, y0+h_cm+dy, 'o',  color='#ff4444', markersize=5, zorder=5)

    ax.annotate(f"{b_cm:.0f} cm", xy=(b_cm/2, y0-0.8),
                ha='center', fontsize=9, fontweight='bold', color='#cdd6f4')
    ax.annotate(f"{h_cm:.0f} cm", xy=(x0-0.8, h_cm/2),
                ha='right', va='center', fontsize=9, fontweight='bold', color='#cdd6f4')
    ax.annotate(f"Gancho 135\u00b0\next.=6d\u1d49={6*bar_diam_mm/10:.1f}cm | r=2d\u1d49={2*bar_diam_mm/10:.1f}cm",
                xy=(x0+dx+0.2, y0+h_cm-r+dy-0.1), fontsize=7.5, color='#ff9999',
                va='top', ha='left')
    ax.annotate("alterna estribo\na estribo",
                xy=(x0+r+dx*0.5, y0+h_cm+dy*0.5), fontsize=6.5, color='#888',
                va='center', ha='left', style='italic')
    ax.set_xlim(x0 - hook_len_cm*0.3, b_cm + hook_len_cm*0.6)
    ax.set_ylim(y0 - hook_len_cm*0.5, h_cm + hook_len_cm*1.1)
    ax.axis('off')
    ax.set_title(f"Estribo E1 \u2014 {label} \u2014 Per\u00edmetro {2*(b_cm+h_cm):.0f} cm",
                 fontsize=9, fontweight='bold', color='white')
    return fig

def draw_crosstie(len_cm, hook_len_cm, bar_diam_mm, bar_name=None):
    label = bar_name if bar_name else _bar_label(bar_diam_mm)
    fig, ax = plt.subplots(figsize=(max(6, len_cm/15), 2))
    fig.patch.set_facecolor('#1e1e2e')
    for _ax in fig.get_axes(): _ax.set_facecolor('#14142a'); _ax.tick_params(colors='#cdd6f4'); _ax.xaxis.label.set_color('#cdd6f4'); _ax.yaxis.label.set_color('#cdd6f4')
    ax.set_aspect('equal')
    ax.plot([0, len_cm], [0, 0], 'k-', linewidth=2)
    ax.plot([0, -hook_len_cm*0.7], [0, -hook_len_cm*0.7], 'k-', linewidth=2)
    ax.plot([len_cm, len_cm + hook_len_cm*0.7], [0, -hook_len_cm*0.7], 'k-', linewidth=2)
    ax.annotate(f"{len_cm:.0f} cm", xy=(len_cm/2, 0.3), ha='center', fontsize=8)
    ax.annotate(f"Gancho 135°", xy=(0, -hook_len_cm*0.5), ha='right', fontsize=8)
    ax.annotate(f"Gancho 135°", xy=(len_cm, -hook_len_cm*0.5), ha='left', fontsize=8)
    ax.set_xlim(-hook_len_cm*1.2, len_cm + hook_len_cm*1.2)
    ax.set_ylim(-hook_len_cm*1.5, hook_len_cm*0.5)
    ax.axis('off')
    ax.set_title(f"Crosstie C1 — {label} — Longitud {len_cm:.0f} cm", fontsize=9, fontweight='bold')
    return fig

def draw_spiral(D_cm, paso_cm, bar_diam_mm, bar_name=None):
    """Dibujo esquemático de espiral para columnas circulares"""
    label = bar_name if bar_name else _bar_label(bar_diam_mm)
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('#1e1e2e')
    for _ax in fig.get_axes(): _ax.set_facecolor('#14142a'); _ax.tick_params(colors='#cdd6f4'); _ax.xaxis.label.set_color('#cdd6f4'); _ax.yaxis.label.set_color('#cdd6f4')
    ax.set_aspect('equal')
    circle = plt.Circle((0, 0), D_cm/2, fill=False, edgecolor='black', linewidth=2)
    ax.add_patch(circle)
    theta = np.linspace(0, 4*np.pi, 200)
    r = D_cm/2 - bar_diam_mm/10
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    ax.plot(x, y, 'k-', linewidth=1.5)
    ax.annotate(f"Espiral {label}", xy=(0, D_cm/2 + 2), ha='center', fontsize=9)
    ax.annotate(f"Paso = {paso_cm:.1f} cm", xy=(0, -D_cm/2 - 3), ha='center', fontsize=8)
    ax.set_xlim(-D_cm/2 - 5, D_cm/2 + 5)
    ax.set_ylim(-D_cm/2 - 8, D_cm/2 + 5)
    ax.axis('off')
    ax.set_title(f"Espiral — {label}", fontsize=9, fontweight='bold')
    return fig

# 
# PARÁMETROS POR NORMA (con límites por nivel sísmico)
# 
CODES = {
    "NSR-10 (Colombia)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 6.0, "rho_max_dmo": 4.0, "rho_max_des": 4.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["DMI — Disipación Mínima", "DMO — Disipación Moderada", "DES — Disipación Especial"],
        "ref": "NSR-10 Título C",
    },
    "ACI 318-25 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary", "IMF — Intermediate", "SMF — Special"],
        "ref": "ACI 318-25",
    },
    "ACI 318-19 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary", "IMF — Intermediate", "SMF — Special"],
        "ref": "ACI 318-19",
    },
    "ACI 318-14 (EE.UU.)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["OMF — Ordinary", "IMF — Intermediate", "SMF — Special"],
        "ref": "ACI 318-14",
    },
    "NEC-SE-HM (Ecuador)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["GS — Grado Reducido", "GM — Grado Moderado", "GA — Grado Alto"],
        "ref": "NEC-SE-HM",
    },
    "E.060 (Perú)": {
        "phi_tied": 0.70, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 6.0, "rho_max_dmo": 5.0, "rho_max_des": 5.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["PO — Pórtico Ordinario", "PM — Pórtico Moderado", "PE — Pórtico Especial"],
        "ref": "E.060 Perú",
    },
    "NTC-EM (México)": {
        "phi_tied": 0.70, "phi_spiral": 0.80, "phi_tension": 0.85,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 6.0, "rho_max_dmo": 5.0, "rho_max_des": 5.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["MDL — Ductilidad Limitada", "MROD — Ductilidad Ordinaria", "MRLE — Ductilidad Alta"],
        "ref": "NTC-EM México",
    },
    "COVENIN 1753-2006 (Venezuela)": {
        "phi_tied": 0.70, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 6.0, "rho_max_dmo": 5.0, "rho_max_des": 5.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["PO — Pórtico Ordinario", "PM — Pórtico Moderado", "PE — Pórtico Especial"],
        "ref": "COVENIN 1753",
    },
    "NB 1225001-2020 (Bolivia)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["DO — Diseño Ordinario", "DM — Ductilidad Moderada", "DE — Diseño Especial"],
        "ref": "NB 1225001",
    },
    "CIRSOC 201-2025 (Argentina)": {
        "phi_tied": 0.65, "phi_spiral": 0.75, "phi_tension": 0.90,
        "pmax_tied": 0.80, "pmax_spiral": 0.85,
        "rho_min": 1.0, "rho_max_dmi": 8.0, "rho_max_dmo": 6.0, "rho_max_des": 6.0,
        "eps_tension_full": 0.005,
        "seismic_levels": ["GE — Grado Estándar", "GM — Ductilidad Moderada", "GA — Ductilidad Alta"],
        "ref": "CIRSOC 201",
    },
}

# =============================================================================
# RECUBRIMIENTO MÍNIMO EN COLUMNAS POR NORMA (cm)
# =============================================================================
COVER_MIN_COL = {
    "NSR-10 (Colombia)":              3.8,   # NSR-10 C.7.7.1
    "ACI 318-25 (EE.UU.)":            3.8,   # ACI 318-25 §26.4.1.1
    "ACI 318-19 (EE.UU.)":            3.8,   # ACI 318-19 §26.4.1.1
    "ACI 318-14 (EE.UU.)":            3.8,   # ACI 318-14 §7.7.1
    "NEC-SE-HM (Ecuador)":            3.8,   # NEC-SE-HM §7.7
    "E.060 (Perú)":                   4.0,   # E.060 Art. 7.7
    "NTC-EM (México)":                3.5,   # NTC-EM §2.1.4
    "COVENIN 1753-2006 (Venezuela)":  3.8,   # COVENIN 1753
    "NB 1225001-2020 (Bolivia)":      3.8,   # NB 1225001
    "CIRSOC 201-2025 (Argentina)":    3.8,   # CIRSOC 201
}
COVER_REF_COL = {
    "NSR-10 (Colombia)":              "NSR-10 C.7.7.1",
    "ACI 318-25 (EE.UU.)":            "ACI 318-25 §26.4.1.1",
    "ACI 318-19 (EE.UU.)":            "ACI 318-19 §26.4.1.1",
    "ACI 318-14 (EE.UU.)":            "ACI 318-14 §7.7.1",
    "NEC-SE-HM (Ecuador)":            "NEC-SE-HM §7.7",
    "E.060 (Perú)":                   "E.060 Art. 7.7",
    "NTC-EM (México)":                "NTC-EM §2.1.4",
    "COVENIN 1753-2006 (Venezuela)":  "COVENIN 1753 §7.7",
    "NB 1225001-2020 (Bolivia)":      "NB 1225001 §7.7",
    "CIRSOC 201-2025 (Argentina)":    "CIRSOC 201 §7.7",
}

# 
# PRESENTACIONES DE CEMENTO POR PAÍS
# 
CEMENT_BAGS = {
    "NSR-10 (Colombia)": [{"label": "Cemento gris (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "ACI 318-25 (EE.UU.)": [{"label": "Type I/II (94 lb / 42.6 kg)", "kg": 42.6}, {"label": "Type III (47 lb / 21.3 kg)", "kg": 21.3}],
    "ACI 318-19 (EE.UU.)": [{"label": "Type I/II (94 lb / 42.6 kg)", "kg": 42.6}, {"label": "Type III (47 lb / 21.3 kg)", "kg": 21.3}],
    "ACI 318-14 (EE.UU.)": [{"label": "Type I/II (94 lb / 42.6 kg)", "kg": 42.6}, {"label": "Type III (47 lb / 21.3 kg)", "kg": 21.3}],
    "NEC-SE-HM (Ecuador)": [{"label": "Cemento Holcim (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "E.060 (Perú)": [{"label": "Cemento Andino (42.5 kg)", "kg": 42.5}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "NTC-EM (México)": [{"label": "Cemento Cemex (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "COVENIN 1753-2006 (Venezuela)": [{"label": "Cemento (42.5 kg)", "kg": 42.5}],
    "NB 1225001-2020 (Bolivia)": [{"label": "Cemento (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
    "CIRSOC 201-2025 (Argentina)": [{"label": "Cemento (50 kg)", "kg": 50.0}, {"label": "Bolsa pequeña (25 kg)", "kg": 25.0}],
}

# 
# TABLA DE DOSIFICACIÓN ACI 211
# 
MIX_DESIGNS = [
    {"fc_mpa": 14.0, "cem": 250, "agua": 205, "arena": 810, "grava": 1060, "wc": 0.82},
    {"fc_mpa": 17.0, "cem": 290, "agua": 200, "arena": 780, "grava": 1060, "wc": 0.69},
    {"fc_mpa": 21.0, "cem": 350, "agua": 193, "arena": 720, "grava": 1060, "wc": 0.55},
    {"fc_mpa": 25.0, "cem": 395, "agua": 193, "arena": 680, "grava": 1020, "wc": 0.49},
    {"fc_mpa": 28.0, "cem": 430, "agua": 190, "arena": 640, "grava": 1000, "wc": 0.44},
    {"fc_mpa": 35.0, "cem": 530, "agua": 185, "arena": 580, "grava":  960, "wc": 0.35},
    {"fc_mpa": 42.0, "cem": 620, "agua": 180, "arena": 520, "grava":  910, "wc": 0.29},
    {"fc_mpa": 56.0, "cem": 740, "agua": 175, "arena": 450, "grava":  850, "wc": 0.24},
]

def get_mix_for_fc(fc_mpa):
    if fc_mpa <= MIX_DESIGNS[0]["fc_mpa"]: return MIX_DESIGNS[0]
    if fc_mpa >= MIX_DESIGNS[-1]["fc_mpa"]: return MIX_DESIGNS[-1]
    for i in range(len(MIX_DESIGNS)-1):
        lo, hi = MIX_DESIGNS[i], MIX_DESIGNS[i+1]
        if lo["fc_mpa"] <= fc_mpa <= hi["fc_mpa"]:
            t = (fc_mpa - lo["fc_mpa"]) / (hi["fc_mpa"] - lo["fc_mpa"])
            return {k: lo[k] + t*(hi[k]-lo[k]) for k in ("cem", "agua", "arena", "grava", "wc")}
    return MIX_DESIGNS[-1]

def get_beta1(fc):
    if fc <= 28: return 0.85
    return max(0.85 - 0.05*(fc-28)/7.0, 0.65)

def get_development_length(db_mm, fy, fc, lambda_=1.0, psi_t=1.0, psi_e=1.0, psi_s=1.0, psi_g=1.0, cb_ktr=2.5):
    if db_mm <= 0: return 0
    ld = (3/40) * (fy / (lambda_ * math.sqrt(fc))) * (psi_t * psi_e * psi_s * psi_g / cb_ktr) * db_mm
    return max(ld, 300)

# 
# FUNCIONES PARA CÁLCULO DE CAPACIDAD UNIAXIAL
# 
def compute_uniaxial_capacity(b, h, d_prime, layers, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza):
    eps_cu = 0.003
    eps_y = fy / Es
    beta_1 = get_beta1(fc)
    
    Ag = b * h
    Ast = sum([layer['As'] for layer in layers])
    Po_kN = (0.85 * fc * (Ag * 100 - Ast * 100) + fy * Ast * 100) / 1000.0
    
    c_vals = np.concatenate([np.linspace(1e-5, h, 120), np.linspace(h, h * 12, 60)])
    P_n_list = []; M_n_list = []; phi_P_n_list = []; phi_M_n_list = []
    eps_t_vals = []
    
    b_mm = b * 10
    h_mm = h * 10
    
    for c_cm in c_vals:
        c_mm = c_cm * 10
        a_mm = min(beta_1 * c_mm, h_mm)
        Cc = 0.85 * fc * a_mm * b_mm
        Mc = Cc * (h_mm / 2.0 - a_mm / 2.0)
        
        Ps = 0.0; Ms = 0.0; eps_t = 0.0
        for layer in layers:
            d_i_mm = layer['d'] * 10
            As_i = layer['As'] * 100
            eps_s = eps_cu * (c_mm - d_i_mm) / c_mm
            if d_i_mm >= max(l['d'] * 10 for l in layers):
                eps_t = eps_s
            fs = max(-fy, min(fy, Es * eps_s))
            if a_mm > d_i_mm and fs > 0:
                fs -= 0.85 * fc
            Ps += As_i * fs
            Ms += As_i * fs * (h_mm / 2.0 - d_i_mm)
        
        Pn = (Cc + Ps) / 1000.0
        Mn = abs((Mc + Ms) / 1_000_000.0)
        eps_t_tens = -eps_t
        
        if eps_t_tens <= eps_y:
            phi = phi_c_max
        elif eps_t_tens >= eps_full:
            phi = phi_tension
        else:
            phi = phi_c_max + (phi_tension - phi_c_max) * (eps_t_tens - eps_y) / (eps_full - eps_y)
        
        Pn_max_val = p_max_factor * Po_kN
        phi_Pn_max_val = min(phi_c_max*Pn_max_val, 0.80*phi_c_max*Po_kN)  # ACI 318-19 §22.4.2.1
        
        Pn = min(Pn, Pn_max_val)
        phi_Pn = min(phi * Pn, phi_Pn_max_val)
        phi_Mn = phi * Mn
        
        P_n_list.append(Pn)
        M_n_list.append(Mn)
        phi_P_n_list.append(phi_Pn)
        phi_M_n_list.append(phi_Mn)
        eps_t_vals.append(eps_t_tens)
    
    c_balance = None
    P_balance = None
    M_balance = None
    for i, eps in enumerate(eps_t_vals):
        if abs(eps - eps_y) < 0.0001 or (i > 0 and eps_t_vals[i-1] <= eps_y <= eps):
            idx = i if abs(eps - eps_y) < 0.0001 else i-1
            c_balance = c_vals[idx]
            P_balance = P_n_list[idx] * factor_fuerza
            M_balance = M_n_list[idx] * factor_fuerza
            break
    
    return {
        'M_n': np.array(M_n_list) * factor_fuerza,
        'P_n': np.array(P_n_list) * factor_fuerza,
        'phi_M_n': np.array(phi_M_n_list) * factor_fuerza,
        'phi_P_n': np.array(phi_P_n_list) * factor_fuerza,
        'Po': Po_kN * factor_fuerza,
        'Pn_max': p_max_factor * Po_kN * factor_fuerza,
        'phi_Pn_max': phi_c_max * p_max_factor * Po_kN * factor_fuerza,
        'c_balance': c_balance,
        'P_balance': P_balance,
        'M_balance': M_balance,
    }

def compute_uniaxial_capacity_circular(D, d_prime, layers, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza):
    """Para sección circular"""
    eps_cu = 0.003
    eps_y = fy / Es
    beta_1 = get_beta1(fc)
    
    r = D / 2
    Ag = math.pi * r**2
    Ast = sum([layer['As'] for layer in layers])
    Po_kN = (0.85 * fc * (Ag * 100 - Ast * 100) + fy * Ast * 100) / 1000.0
    
    c_vals = np.concatenate([
        np.linspace(1e-5, D * 0.1, 40),
        np.linspace(D * 0.1, D * 0.5, 80),
        np.linspace(D * 0.5, D, 60),
        np.linspace(D, D * 12, 40)
    ])
    P_n_list = []; M_n_list = []; phi_P_n_list = []; phi_M_n_list = []
    eps_t_vals = []
    
    for c_cm in c_vals:
        c_mm = c_cm * 10
        if c_mm >= D * 10:
            a_mm = D * 10
        else:
            a_mm = beta_1 * c_mm
        a_cm = a_mm / 10
        if a_cm >= D:
            Ac_comp = Ag
        else:
            h_seg = a_cm
            _arg_ac = np.clip((r - h_seg) / r, -1.0, 1.0)
            Ac_comp = r**2 * math.acos(_arg_ac) - (r - h_seg) * math.sqrt(max(0.0, 2*r*h_seg - h_seg**2))
        
        Cc = 0.85 * fc * Ac_comp * 100
        if a_cm >= D:
            y_cent = r
        else:
            _arg_yc = np.clip((r - a_cm) / r, -1.0, 1.0)
            _angle = math.acos(_arg_yc)
            y_cent = (4*r * math.sin(_angle / 2)**3) / (3 * (_angle - math.sin(_angle) * math.cos(_angle)))
        Mc = Cc * (r * 10 - y_cent * 10)
        
        Ps = 0.0; Ms = 0.0; eps_t = 0.0
        for layer in layers:
            d_i_mm = layer['d'] * 10
            As_i = layer['As'] * 100
            eps_s = eps_cu * (c_mm - d_i_mm) / c_mm
            if d_i_mm >= max(l['d'] * 10 for l in layers):
                eps_t = eps_s
            fs = max(-fy, min(fy, Es * eps_s))
            Ps += As_i * fs
            Ms += As_i * fs * (r * 10 - d_i_mm)
        
        Pn = (Cc + Ps) / 1000.0
        Mn = abs((Mc + Ms) / 1000000.0)
        eps_t_tens = -eps_t
        
        if eps_t_tens <= eps_y:
            phi = phi_c_max
        elif eps_t_tens >= eps_full:
            phi = phi_tension
        else:
            phi = phi_c_max + (phi_tension - phi_c_max) * (eps_t_tens - eps_y) / (eps_full - eps_y)
        
        Pn_max_val = p_max_factor * Po_kN
        phi_Pn_max_val = min(phi_c_max*Pn_max_val, 0.80*phi_c_max*Po_kN)  # ACI 318-19 §22.4.2.1
        
        Pn = min(Pn, Pn_max_val)
        phi_Pn = min(phi * Pn, phi_Pn_max_val)
        phi_Mn = phi * Mn
        
        P_n_list.append(Pn)
        M_n_list.append(Mn)
        phi_P_n_list.append(phi_Pn)
        phi_M_n_list.append(phi_Mn)
        eps_t_vals.append(eps_t_tens)
    
    c_balance = None
    P_balance = None
    M_balance = None
    for i, eps in enumerate(eps_t_vals):
        if abs(eps - eps_y) < 0.0001 or (i > 0 and eps_t_vals[i-1] <= eps_y <= eps):
            idx = i if abs(eps - eps_y) < 0.0001 else i-1
            c_balance = c_vals[idx]
            P_balance = P_n_list[idx] * factor_fuerza
            M_balance = M_n_list[idx] * factor_fuerza
            break
    
    return {
        'M_n': np.array(M_n_list) * factor_fuerza,
        'P_n': np.array(P_n_list) * factor_fuerza,
        'phi_M_n': np.array(phi_M_n_list) * factor_fuerza,
        'phi_P_n': np.array(phi_P_n_list) * factor_fuerza,
        'Po': Po_kN * factor_fuerza,
        'Pn_max': p_max_factor * Po_kN * factor_fuerza,
        'phi_Pn_max': phi_c_max * p_max_factor * Po_kN * factor_fuerza,
        'c_balance': c_balance,
        'P_balance': P_balance,
        'M_balance': M_balance,
    }

# 
# FUNCIÓN PARA VERIFICACIÓN BIAXIAL (BRESLER)
# 
def interp_pm_curve(M_query, phi_Mn_arr, phi_Pn_arr):
    """
    Interpola φPn dado φMn en la curva P-M NO monótona.
    La curva tiene dos ramas: compresión (M creciente) y tensión (M decreciente).
    Separamos ambas ramas e interpolamos en cada una, retornando el MAYOR φPn
    (el de la rama de compresión, que es el correcto para Bresler).
    """
    phi_Mn_arr = np.array(phi_Mn_arr)
    phi_Pn_arr = np.array(phi_Pn_arr)
    
    if len(phi_Mn_arr) == 0:
        return 0.0
    
    M_max = np.max(phi_Mn_arr)
    
    # Si M=0 → capacidad axial pura (Po)
    if M_query <= 0:
        return float(phi_Pn_arr[np.argmax(phi_Pn_arr)])
    
    # Si el momento pedido supera el máximo → sentinel -1.0 (distinguible de Pn=0 real)
    if M_query > M_max:
        return -1.0  # sentinel: M excede el diagrama en este eje
    
    # Índice del punto de balance (donde φMn es máximo)
    idx_bal = int(np.argmax(phi_Mn_arr))
    
    #  Rama COMPRESIÓN: Po → Balance (M creciente, P decreciente) 
    Mc = phi_Mn_arr[:idx_bal + 1]
    Pc = phi_Pn_arr[:idx_bal + 1]
    
    #  Rama TENSIÓN: Balance → Tracción pura (M decreciente, P→0) 
    Mt = phi_Mn_arr[idx_bal:]
    Pt = phi_Pn_arr[idx_bal:]
    
    # Ordenar cada rama para np.interp (requiere x creciente)
    sc = np.argsort(Mc)
    st = np.argsort(Mt)
    
    P_comp = float(np.interp(M_query, Mc[sc], Pc[sc],
                              left=float(Pc[sc[0]]), right=0.0))
    P_tens = float(np.interp(M_query, Mt[st], Pt[st],
                              left=0.0, right=0.0))
    
    # Retornar el MAYOR (rama de compresión es siempre mayor)
    return max(P_comp, P_tens)


def biaxial_bresler(Pu, Mux, Muy, cap_x, cap_y, Po, phi_factor):
    phi_Pnx, phi_Pny, phi_P0 = None, None, None
    phi_Pnx = interp_pm_curve(abs(Mux), np.array(cap_x['phi_M_n']), np.array(cap_x['phi_P_n']))
    phi_Pny = interp_pm_curve(abs(Muy), np.array(cap_y['phi_M_n']), np.array(cap_y['phi_P_n']))
    phi_P0  = phi_factor * Po

    if phi_Pnx is None or phi_Pny is None:
        return {
            'phi_Pnx': 0.0,
            'phi_Pny': 0.0,
            'phi_P0':  phi_P0,
            'phi_Pni': 0.0,
            'ratio':   float('inf'),
            'ok':      False
        }

    # Detectar sentinel -1.0: el momento supera el diagrama en ese eje
    eje_excedido = []
    if phi_Pnx < 0:
        eje_excedido.append("X")
    if phi_Pny < 0:
        eje_excedido.append("Y")

    if eje_excedido:
        msg = f"Mux/Muy excede el diagrama P-M en eje {'&'.join(eje_excedido)}: aumentar sección o acero"
        return {
            'phi_Pnx': max(phi_Pnx, 0.0),
            'phi_Pny': max(phi_Pny, 0.0),
            'phi_P0':  phi_P0,
            'phi_Pni': 0.0,
            'ratio':   float('inf'),
            'ok':      False,
            'msg_exceso': msg,
        }

    if phi_Pnx > 0 and phi_Pny > 0 and phi_P0 > 0:
        inv = 1/phi_Pnx + 1/phi_Pny - 1/phi_P0
        phi_Pni = 1/inv if inv > 0 else 0.0
    else:
        phi_Pni = 0.0

    ratio = Pu / phi_Pni if phi_Pni > 0 else float('inf')
    ok    = Pu <= phi_Pni

    return {
        'phi_Pnx': phi_Pnx,
        'phi_Pny': phi_Pny,
        'phi_P0':  phi_P0,
        'phi_Pni': phi_Pni,
        'ratio':   ratio,
        'ok':      ok,
        'msg_exceso': None,
    }

# 
# FUNCIÓN PARA ESBELTEZ (NSR-10 C.10.10 / ACI 6.6)
# 
def check_slenderness(L, b, h, k, beta_dns, Pu, M1, M2, fc, fy, Es, factor_fuerza, es_circular=False):
    r = 0.25 * b if es_circular else min(b, h) / math.sqrt(12)
    kl = k * L
    kl_r = kl / r if r > 0 else 999
    
    if kl_r <= 22:
        slender = False
        classification = "Columna corta (sin efectos de segundo orden)"
        delta_ns = 1.0
    elif kl_r <= 100:
        slender = True
        classification = "Columna esbelta (requiere magnificación de momentos)"
        Ec = 4700 * math.sqrt(fc)
        # Bug Fix: para sección circular usar Ig = π*D⁴/64, no b*h³/12
        if es_circular:
            Ig = math.pi * b**4 / 64   # b == D cuando se llama para circular
        else:
            Ig = b * h**3 / 12
        Ig_mm4 = Ig * 1e4
        EI = 0.4 * Ec * Ig_mm4 / (1 + beta_dns)
        Pc = math.pi**2 * EI / (kl * 1000)**2
        Pc = Pc / 1000
        Cm = 0.6 + 0.4 * (M1/M2) if abs(M2) > 0 else 1.0
        Cm = max(0.4, Cm)
        # Bug Fix N3: Prevenir división por cero si Pu se acerca a la carga crítica (Pandeo)
        denom = 1 - Pu / (0.75 * Pc)
        if denom <= 0.01:
            denom = 0.01
        delta_ns = Cm / denom
        delta_ns = max(delta_ns, 1.0)
    else:
        slender = True
        classification = "Columna muy esbelta (kl/r > 100) — requiere análisis no lineal según NSR-10 C.10.10.7"
        delta_ns = 1.0
    
    return {
        'kl_r': kl_r,
        'slender': slender,
        'classification': classification,
        'delta_ns': delta_ns,
        'r': r,
        'kl': kl
    }

# =============================================================================
# SIDEBAR - ENTRADAS DEL USUARIO
# =============================================================================


# =============================================================================
# PERSISTENCIA LOCAL — Columnas PM
# =============================================================================
import base64 as _b64, json as _json, os as _os

_COL_PERSIST_KEYS = [
    "cpm_empresa","cpm_proyecto_nombre","cpm_ingeniero","cpm_elaboro","cpm_reviso","cpm_aprobo",
    "cpm_plano_num","cpm_escala","col_logo_bytes","user_role","nombre_proyecto_actual",
    "c_pm_norma","c_pm_nivel_sismico","c_pm_fc_unit","c_pm_fc_mpa","c_pm_fy",
    "c_pm_seccion_type","c_pm_b","c_pm_h","c_pm_D","c_pm_dprime","c_pm_L",
    "c_pm_unit_system","c_pm_rebar_type","c_pm_num_h","c_pm_num_v","c_pm_n_barras_circ",
    "c_pm_col_type","c_pm_stirrup_type","c_pm_spiral_type","c_pm_paso_circ","c_pm_paso_rect",
    "c_pm_output_units","c_pm_mux","c_pm_muy","c_pm_pu","c_pm_cm_chk","c_pm_m1x","c_pm_m1y",
    "c_pm_beta_dns","c_pm_k_sel",
]

def save_state_col():
    snap = {}
    for k in _COL_PERSIST_KEYS:
        val = st.session_state.get(k)
        if k == "col_logo_bytes" and isinstance(val, (bytes, bytearray)):
            snap[k] = {"type": "bytes_b64", "data": _b64.b64encode(val).decode()}
        elif val is not None:
            try:    snap[k] = val
            except: snap[k] = str(val)
    try:
        with open("col_state.json", "w", encoding="utf-8") as f:
            _json.dump(snap, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_state_col():
    if not _os.path.exists("col_state.json"):
        return
    try:
        with open("col_state.json", "r", encoding="utf-8") as f:
            data = _json.load(f)
        for k, v in data.items():
            if k not in st.session_state:
                if isinstance(v, dict) and v.get("type") == "bytes_b64":
                    st.session_state[k] = _b64.b64decode(v["data"])
                else:
                    st.session_state[k] = v
    except Exception:
        pass

if "col_state_loaded" not in st.session_state:
    load_state_col()
    st.session_state["col_state_loaded"] = True


# =============================================================================
# PASO 1 — SIDEBAR: Identidad, logo, norma, rol, plano, guardar/cargar
#           NO contiene inputs de calculo. Solo identidad y configuracion global.
# =============================================================================

with st.sidebar.expander("Identidad del Proyecto", expanded=False):
    st.session_state["cpm_empresa"]         = st.text_input("Empresa / Firma",
        value=st.session_state.get("cpm_empresa",""), key="_wb_e")
    st.session_state["cpm_proyecto_nombre"] = st.text_input("Nombre del Proyecto",
        value=st.session_state.get("cpm_proyecto_nombre",""), key="_wb_p")
    st.session_state["cpm_ingeniero"]       = st.text_input("Ingeniero Responsable",
        value=st.session_state.get("cpm_ingeniero",""), key="_wb_i")
    _c1s, _c2s = st.columns(2)
    st.session_state["cpm_elaboro"] = _c1s.text_input("Elaboro",
        value=st.session_state.get("cpm_elaboro",""), key="_wb_elab")
    st.session_state["cpm_reviso"]  = _c2s.text_input("Reviso",
        value=st.session_state.get("cpm_reviso",""),  key="_wb_rev")
    st.session_state["cpm_aprobo"]  = st.text_input("Aprobo",
        value=st.session_state.get("cpm_aprobo",""), key="_wb_apr")
    if st.button("Guardar identidad", key="btn_id_col", use_container_width=True):
        save_state_col()
        st.success("Identidad guardada")

st.sidebar.markdown("**Logo de empresa**")
st.sidebar.caption("Aparece en portada de DOCX y PDF. PNG/JPG, fondo blanco recomendado.")
_logo_file = st.sidebar.file_uploader("Subir logo", type=["png","jpg","jpeg"], key="col_logo_upload")
if _logo_file is not None:
    _raw = _logo_file.read()
    if _raw:
        st.session_state["col_logo_bytes"] = _raw
        save_state_col()
        st.sidebar.success("Logo cargado")
if st.session_state.get("col_logo_bytes"):
    try:
        st.sidebar.image(st.session_state["col_logo_bytes"], width=140, caption="Logo activo")
    except Exception:
        st.sidebar.caption("Logo cargado (no previsualizable)")
    _la, _lb = st.sidebar.columns(2)
    if _la.button("Quitar logo", key="col_rm_logo", use_container_width=True):
        st.session_state.pop("col_logo_bytes", None)
        save_state_col(); st.rerun()
    _lb.download_button("Descargar", data=st.session_state["col_logo_bytes"],
                        file_name="logo.png", mime="image/png",
                        use_container_width=True, key="col_dl_logo")
else:
    st.sidebar.caption("Sin logo — documentos solo texto.")

st.sidebar.markdown("---")

st.sidebar.header("0. Norma de Diseno")
norma_options = list(CODES.keys())
norma_sel = st.sidebar.selectbox("Norma", norma_options, key="c_pm_norma")
mostrar_referencias_norma(norma_sel, "columnas_pm")
code = CODES[norma_sel]

nivel_sismico = st.sidebar.selectbox(
    "Nivel Sismico / Ductilidad:",
    code["seismic_levels"],
    key="c_pm_nivel_sismico"
)
nivel_lower = nivel_sismico.lower()
es_des = any(k in nivel_lower for k in ["des","disipacion especial","smf","special","ga","ductilidad alta","pe","portico especial","de","diseno especial","mrle","alta"])
es_dmo = any(k in nivel_lower for k in ["dmo","imf","intermediate","gm","moderada","pm","mrod","media","moderado"]) and not es_des
es_dmi = not (es_des or es_dmo)

if es_des:   rho_max = code["rho_max_des"]
elif es_dmo: rho_max = code["rho_max_dmo"]
else:        rho_max = code["rho_max_dmi"]
rho_min = code["rho_min"]

st.sidebar.caption(f"Referencia: {code['ref']}")
st.sidebar.caption(f"rho max segun nivel: {rho_max}% | rho min: {rho_min}%")

with st.sidebar.expander("Rol de Usuario", expanded=False):
    _roles    = ["free", "pro", "admin"]
    _rol_idx  = _roles.index(st.session_state.get("user_role","free"))
    _rol_nuevo = st.radio("Selecciona tu rol", _roles, index=_rol_idx, key="col_rol_radio",
                          help="free: calculos y CSV.  pro: todos los entregables.  admin: acceso total.")
    if _rol_nuevo != st.session_state.get("user_role","free"):
        st.session_state["user_role"] = _rol_nuevo
        save_state_col(); st.rerun()
    _crol = {"admin":"#1b5e20","pro":"#0d47a1","free":"#b71c1c"}
    st.markdown(
        f'<div style="background:{_crol[_rol_nuevo]};color:white;border-radius:6px;'
        f'padding:5px 10px;font-size:12px;text-align:center;font-weight:600;margin-top:6px">'
        f'Rol activo: {_rol_nuevo.upper()}</div>', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.header("Datos del Plano")
_plano_num    = st.sidebar.text_input("Numero de plano",
    value=st.session_state.get("cpm_plano_num","COL-001"), key="cpm_plano_inp")
_escala_plano = st.sidebar.text_input("Escala",
    value=st.session_state.get("cpm_escala","1:50"), key="cpm_escala_inp")
st.session_state["cpm_plano_num"] = _plano_num
st.session_state["cpm_escala"]    = _escala_plano

st.sidebar.markdown("---")
st.sidebar.subheader("Guardar / Cargar Proyecto")
_nombre_producido    = st.session_state.get("nombre_proyecto_actual","")
_nombre_proy_guardar = st.sidebar.text_input("Nombre para guardar",
    value=_nombre_producido, key="col_input_proy")
if st.sidebar.button("Guardar Proyecto", use_container_width=True):
    if _nombre_proy_guardar:
        _ok, _msg = guardar_proyecto_supabase(_nombre_proy_guardar, capturar_estado_actual())
        if _ok:
            st.session_state["nombre_proyecto_actual"] = _nombre_proy_guardar
            st.sidebar.success(_msg); st.rerun()
        else:
            st.sidebar.error(_msg)
    else:
        st.sidebar.warning("Escribe un nombre de proyecto")

st.sidebar.markdown("**Cargar Proyecto Existente**")
_lista_proy = listar_proyectos_supabase()
if _lista_proy:
    _idx_def = 0
    if _nombre_producido in _lista_proy:
        _idx_def = _lista_proy.index(_nombre_producido)
    _nombre_proy_cargar = st.sidebar.selectbox("Selecciona un proyecto",
        _lista_proy, index=_idx_def, key="col_sel_proy")
    def _on_cargar_col():
        _p = st.session_state["col_sel_proy"]
        if _p:
            _ok2, _msg2 = cargar_proyecto_supabase(_p)
            if _ok2:
                st.session_state["nombre_proyecto_actual"] = _p
                st.session_state["__msg_cargar_col"] = (True, _msg2)
            else:
                st.session_state["__msg_cargar_col"] = (False, _msg2)
    st.sidebar.button("Cargar", on_click=_on_cargar_col, use_container_width=True)
    if "__msg_cargar_col" in st.session_state:
        _ok3, _msg3 = st.session_state.pop("__msg_cargar_col")
        if _ok3: st.sidebar.success(_msg3)
        else:    st.sidebar.error(_msg3)
else:
    st.sidebar.info("No hay proyectos guardados.")

st.sidebar.markdown("---")
_emp_foot = st.session_state.get("cpm_empresa","") or "StructoPro"
st.sidebar.markdown(
    f'<div style="text-align:center;color:gray;font-size:10px">'
    f'&copy; 2026 {_emp_foot}<br>Uso profesional exclusivo</div>',
    unsafe_allow_html=True)


# =============================================================================
# PASO 2 — Leer variables desde session_state con defaults
#           SIN crear widgets. Los widgets se crean en render_config_tab()
# =============================================================================

fc_unit     = st.session_state.get("c_pm_fc_unit", "MPa")
if fc_unit == "PSI":
    _fc_psi = float(st.session_state.get("c_pm_fc_psi_val", 3000.0))
    fc      = _fc_psi * 0.00689476
elif fc_unit == "kg/cm2":
    _fc_kg  = float(st.session_state.get("c_pm_fc_kgcm2_val", 210.0))
    fc      = _fc_kg / 10.1972
else:
    fc      = float(st.session_state.get("c_pm_fc_mpa", 21.0))

fy          = float(st.session_state.get("c_pm_fy", 420.0))
Es          = 200000.0

seccion_type = st.session_state.get("c_pm_seccion_type", "Rectangular / Cuadrada")
es_circular  = "Circular" in seccion_type
D            = float(st.session_state.get("c_pm_D", 40.0))
b            = float(st.session_state.get("c_pm_b", 30.0))
h            = float(st.session_state.get("c_pm_h", 40.0))
if es_circular:
    b = D; h = D
d_prime      = float(st.session_state.get("c_pm_dprime", 5.0))
L_col        = float(st.session_state.get("c_pm_L", 300.0))

limite_d = D/2 if es_circular else min(b/2, h/2)
if d_prime >= limite_d:
    st.error(
        f"Recubrimiento d' ({d_prime:.1f} cm) supera el nucleo de la seccion "
        f"(limite: {limite_d:.1f} cm). Corrija en la pestana Configuracion."
    )
    st.stop()

unit_system  = st.session_state.get("c_pm_unit_system", "Milimetros (SI)")
_usar_us     = "Pulgadas" in unit_system or "Inches" in unit_system
rebar_dict   = REBAR_US if _usar_us else REBAR_MM
rebar_type   = st.session_state.get("c_pm_rebar_type", list(rebar_dict.keys())[2])
if rebar_type not in rebar_dict:
    rebar_type = list(rebar_dict.keys())[2]
rebar_area   = rebar_dict[rebar_type]["area"]
rebar_diam   = rebar_dict[rebar_type]["diam_mm"]

if es_circular:
    n_barras     = int(st.session_state.get("c_pm_n_barras_circ", 8))
    Ast          = n_barras * rebar_area
    layers       = []
    angulos      = np.linspace(0, 2*np.pi, n_barras, endpoint=False)
    radio_centro = D/2 - d_prime
    for i, ang in enumerate(angulos):
        x_pos = radio_centro * math.cos(ang)
        y_pos = radio_centro * math.sin(ang)
        layers.append({"d": D/2 + y_pos, "As": rebar_area, "x": x_pos, "y": y_pos})
    num_filas_h = n_barras
    num_filas_v = n_barras
else:
    num_filas_h = int(st.session_state.get("c_pm_num_h", 2))
    num_filas_v = int(st.session_state.get("c_pm_num_v", 2))
    layers      = []
    layers.append({"d": d_prime, "As": num_filas_h * rebar_area})
    _num_int    = num_filas_v - 2
    num_capas_intermedias = _num_int  # alias para compatibilidad con tabs
    if _num_int > 0:
        _esp_h  = (h - 2 * d_prime) / (_num_int + 1)
        for i in range(1, _num_int + 1):
            layers.append({"d": d_prime + i * _esp_h, "As": 2 * rebar_area})
    layers.append({"d": h - d_prime, "As": num_filas_h * rebar_area})
    n_barras_total = num_filas_h * 2 + (num_filas_v - 2) * 2
    n_barras       = n_barras_total
    Ast            = sum([l["As"] for l in layers])

Ag      = (math.pi * (D/2)**2) if es_circular else (b * h)
cuantia = Ast / Ag * 100

if es_circular:
    col_type     = "Espiral (Spiral)"
    stirrup_dict = STIRRUP_US if _usar_us else STIRRUP_MM
    spiral_type  = st.session_state.get("c_pm_spiral_type", list(stirrup_dict.keys())[0])
    if spiral_type not in stirrup_dict: spiral_type = list(stirrup_dict.keys())[0]
    stirrup_area = stirrup_dict[spiral_type]["area"]
    stirrup_diam = stirrup_dict[spiral_type]["diam_mm"]
    paso_espiral = float(st.session_state.get("c_pm_paso_circ", 7.5))
else:
    col_type     = st.session_state.get("c_pm_col_type", "Estribos (Tied)")
    stirrup_dict = STIRRUP_US if _usar_us else STIRRUP_MM
    stirrup_type = st.session_state.get("c_pm_stirrup_type", list(stirrup_dict.keys())[0])
    if stirrup_type not in stirrup_dict: stirrup_type = list(stirrup_dict.keys())[0]
    stirrup_area = stirrup_dict[stirrup_type]["area"]
    stirrup_diam = stirrup_dict[stirrup_type]["diam_mm"]
    if stirrup_diam < 9.5: stirrup_diam = 9.53
    paso_espiral = float(st.session_state.get("c_pm_paso_rect", 7.5))

if "Espiral" in col_type or es_circular:
    phi_c_max    = code["phi_spiral"]
    p_max_factor = code["pmax_spiral"]
else:
    phi_c_max    = code["phi_tied"]
    p_max_factor = code["pmax_tied"]
phi_tension  = code["phi_tension"]
eps_full     = code["eps_tension_full"]

unidades_salida = st.session_state.get("c_pm_output_units", "KiloNewtons (kN, kN-m)")
if "Toneladas" in unidades_salida or "tonf" in unidades_salida:
    factor_fuerza = 0.1019716; unidad_fuerza = "tonf"; unidad_mom = "tonf-m"
else:
    factor_fuerza = 1.0; unidad_fuerza = "kN"; unidad_mom = "kN-m"

Mux_input  = float(st.session_state.get("c_pm_mux",  round(45.0   * factor_fuerza, 2)))
Muy_input  = float(st.session_state.get("c_pm_muy",  round(25.0   * factor_fuerza, 2)))
Pu_input   = float(st.session_state.get("c_pm_pu",   round(2700.0 * factor_fuerza, 2)))
aplicar_cm = bool(st.session_state.get("c_pm_cm_chk", False))
if aplicar_cm:
    M1x_input = float(st.session_state.get("c_pm_m1x", 0.0))
    M1y_input = float(st.session_state.get("c_pm_m1y", 0.0))
else:
    M1x_input = Mux_input
    M1y_input = Muy_input

_dim_x_emin = h if not es_circular else D
_dim_y_emin = b if not es_circular else D
e_min_x_cm  = max(0.10 * _dim_x_emin, 1.5)
e_min_y_cm  = max(0.10 * _dim_y_emin, 1.5)
_Mux_emin   = Pu_input * e_min_x_cm / 100.0
_Muy_emin   = Pu_input * e_min_y_cm / 100.0
_Mux_safe   = Mux_input if abs(Mux_input) >= _Mux_emin else (math.copysign(_Mux_emin, Mux_input) if Mux_input != 0 else _Mux_emin)
_Muy_safe   = Muy_input if abs(Muy_input) >= _Muy_emin else (math.copysign(_Muy_emin, Muy_input) if Muy_input != 0 else _Muy_emin)
_Mux_safe   = _Mux_safe if abs(_Mux_safe) > 1e-9 else _Mux_emin
_Muy_safe   = _Muy_safe if abs(_Muy_safe) > 1e-9 else _Muy_emin
Mux_plot    = _Mux_safe
Muy_plot    = _Muy_safe

beta_dns = float(st.session_state.get("c_pm_beta_dns", 0.6))
_k_options = {
    "Ambos extremos articulados":               1.0,
    "Un extremo articulado, otro empotrado":     0.7,
    "Ambos extremos empotrados":                0.5,
    "Voladizo (base empotrada, libre arriba)":  2.0,
}
_k_sel   = st.session_state.get("c_pm_k_sel", "Ambos extremos articulados")
if _k_sel not in _k_options: _k_sel = "Ambos extremos articulados"
k_factor = _k_options[_k_sel]

# =============================================================================
# CÁLCULOS DE CAPACIDAD UNIAXIAL (X y Y)
# =============================================================================
layers_y = []
if es_circular:
    cap_x = compute_uniaxial_capacity_circular(D, d_prime, layers, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza)
    cap_y = cap_x
else:
    # Eje X: flexión sobre eje X, peralte = h, ancho = b
    cap_x = compute_uniaxial_capacity(b, h, d_prime, layers, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza)
    # Eje Y: flexión sobre eje Y, peralte = b, ancho = h
    # Extremos (caras paralelas a h, separadas en dirección b): num_filas_v barras
    layers_y.append({'d': d_prime, 'As': num_filas_v * rebar_area})
    # Laterales (caras a lo largo de h): num_filas_h barras totales menos las 2 esquinas
    num_capas_intermedias_y = num_filas_h - 2
    if num_capas_intermedias_y > 0:
        espacio_y = (b - 2 * d_prime) / (num_capas_intermedias_y + 1)
        for i in range(1, num_capas_intermedias_y + 1):
            layers_y.append({'d': d_prime + i * espacio_y, 'As': 2 * rebar_area})
    layers_y.append({'d': b - d_prime, 'As': num_filas_v * rebar_area})
    cap_y = compute_uniaxial_capacity(h, b, d_prime, layers_y, fc, fy, Es, phi_c_max, phi_tension, eps_full, p_max_factor, factor_fuerza)

# 2) Siempre conservador en Bresler Biaxial, usando phi_c_max
phi_factor = phi_c_max
bresler = biaxial_bresler(Pu_input, Mux_input, Muy_input, cap_x, cap_y, cap_x['Po'], phi_factor)

# 
# BLOQUE: COMPRESIÓN AXIAL PURA — Verificación paso a paso
# 
with st.expander("Compresión Axial Pura — Verificación Paso a Paso (NSR-10 C.9.3.2.2)", expanded=False):

    # Cálculo desglosado
    Ag_cm2  = Ag              # Ag ya está en cm²
    Ast_cm2 = Ast             # Ast ya está en cm²
    Anc_cm2 = Ag_cm2 - Ast_cm2

    Po_kN       = (0.85 * fc * Anc_cm2 + fy * Ast_cm2) / 10.0
    Pn_max_kN   = p_max_factor * Po_kN
    phi_Pn_max_kN = phi_c_max * Pn_max_kN

    Po_out     = Po_kN        * factor_fuerza
    Pn_max_out = Pn_max_kN    * factor_fuerza
    phi_Pn_out = phi_Pn_max_kN * factor_fuerza

    # Panel visual estilo consola
    st.markdown(f"""
    <div style="background:#1c2e1c;border-radius:10px;padding:14px 18px;
                font-family:monospace;font-size:13px;color:#e8f5e9;line-height:2.1">
    <b style="font-size:15px;color:#81c784"> Resistencia máxima a compresión axial pura:</b><br><br>
    <span style="color:#aaa">Po = [0.85·f'c·(Ag − Ast) + fy·Ast] / 1000</span><br>
    <span style="color:#aaa">Pn,máx = {p_max_factor:.2f} × Po &nbsp;&nbsp;|&nbsp;&nbsp; φPn,máx = φ × Pn,máx</span><br><br>
    <b>Ag</b> (área bruta)         = <b>{Ag_cm2:.2f} cm²</b><br>
    <b>Ast</b> (área acero)        = <b>{Ast_cm2:.2f} cm²</b><br>
    <b>Ag − Ast</b> (concreto neto) = <b>{Anc_cm2:.2f} cm²</b><br>
    <span style="color:#aaa"></span><br>
    <b>Po</b>     = [0.85 × {fc:.1f} × {Anc_cm2:.2f} + {fy:.0f} × {Ast_cm2:.2f}] / 1000
             = <b>{Po_out:.1f} {unidad_fuerza}</b><br>
    <b>Pn,máx</b> = {p_max_factor:.2f} × {Po_out:.1f}
             = <b>{Pn_max_out:.1f} {unidad_fuerza}</b>
    <span style="color:#aaa;font-size:11px">
        {'→ Estribos: 0.80' if p_max_factor == 0.80 else '→ Espiral: 0.85'}  —  {code['ref']} C.9.3.2.2
    </span><br>
    <b style="color:#81c784">φPn,máx</b> = {phi_c_max:.2f} × {Pn_max_out:.1f}
             = <b style="color:#a5d6a7;font-size:16px">{phi_Pn_out:.1f} {unidad_fuerza}</b>
    <span style="color:#aaa;font-size:11px">
        {'→ φ = 0.65 estribos' if phi_c_max == 0.65 else '→ φ = 0.75 espiral'}
    </span><br>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Métricas visuales
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Po — Resistencia bruta",
                f"{Po_out:.1f} {unidad_fuerza}",
                help="Capacidad axial sin factores de reducción")
    col2.metric(f"Pn,máx  (×{p_max_factor:.2f})",
                f"{Pn_max_out:.1f} {unidad_fuerza}",
                help=f"Límite por excentricidad accidental — {code['ref']} C.9.3.2.2")
    col3.metric(f"φPn,máx  (φ={phi_c_max:.2f})",
                f"{phi_Pn_out:.1f} {unidad_fuerza}",
                delta="↑ Punto superior del diagrama P-M",
                help="Resistencia de diseño — punto (M=0, P=φPn,máx)")
    col4.metric("Utilización Pu / φPn,máx",
                f"{Pu_input / phi_Pn_max_kN * factor_fuerza / factor_fuerza * 100:.1f} %"
                if phi_Pn_max_kN > 0 else "—",
                help="Porcentaje de uso de la capacidad axial máxima")

    # Nota normativa
    tipo_col = "espiral" if (es_circular or ("Espiral" in col_type if not es_circular else True)) else "estribos"
    st.caption(
        f" **{code['ref']} C.9.3.2.2** — Para columnas con **{tipo_col}**, "
        f"la resistencia axial máxima se limita a **{p_max_factor:.0%}·Po** "
        f"para considerar excentricidades mínimas accidentales. "
        f"φ = **{phi_c_max:.2f}** para compresión con {tipo_col}."
    )

    # Semáforo Pu vs φPn,máx
    Pu_kN_check = Pu_input / factor_fuerza
    if Pu_kN_check > phi_Pn_max_kN:
        st.error(
            f" **Pu = {Pu_input:.1f} {unidad_fuerza}** supera **φPn,máx = {phi_Pn_out:.1f} {unidad_fuerza}**. "
            f"La columna NO puede soportar esta carga. Aumente la sección o el acero."
        )
    elif Pu_kN_check > 0.90 * phi_Pn_max_kN:
        st.warning(
            f" Pu representa el **{Pu_kN_check / phi_Pn_max_kN * 100:.1f}%** de φPn,máx. "
            f"Zona muy próxima al límite de capacidad axial."
        )
    else:
        st.success(
            f" Pu = {Pu_input:.1f} {unidad_fuerza} → **{Pu_kN_check / phi_Pn_max_kN * 100:.1f}%** "
            f"de φPn,máx = {phi_Pn_out:.1f} {unidad_fuerza}. Capacidad axial suficiente."
        )
# 

if es_circular:
    slender_x = check_slenderness(L_col, D, D, k_factor, beta_dns, Pu_input, M1x_input, Mux_input, fc, fy, Es, factor_fuerza, es_circular=True)
    slender_y = check_slenderness(L_col, D, D, k_factor, beta_dns, Pu_input, M1y_input, Muy_input, fc, fy, Es, factor_fuerza, es_circular=True)
else:
    slender_x = check_slenderness(L_col, h, b, k_factor, beta_dns, Pu_input, M1x_input, Mux_input, fc, fy, Es, factor_fuerza)
    slender_y = check_slenderness(L_col, b, h, k_factor, beta_dns, Pu_input, M1y_input, Muy_input, fc, fy, Es, factor_fuerza)

slenderness = slender_x if slender_x['kl_r'] >= slender_y['kl_r'] else slender_y
Mux_magnified = Mux_input * slender_x['delta_ns']
Muy_magnified = Muy_input * slender_y['delta_ns']

# =============================================================================
# CÁLCULO DE ESTRIBOS Y VERIFICACIÓN Ash
# =============================================================================
if not es_circular:
    recub_cm = max(d_prime - rebar_diam / 20.0, 2.5)
    # Recubrimiento mínimo dinámico por norma
    _recub_min_nsr = COVER_MIN_COL.get(norma_sel, 3.8)
    _cover_ref_nsr = COVER_REF_COL.get(norma_sel, "C.7.7.1")
    if recub_cm < _recub_min_nsr:
        st.sidebar.warning(f"⚠️ {_cover_ref_nsr}: Recubrimiento calculado ({recub_cm:.1f} cm) < mínimo de {_recub_min_nsr} cm para columnas según {norma_sel}. Verifique d'.")
    bc = b - 2 * recub_cm
    hc = h - 2 * recub_cm
    Ach = bc * hc
    
    claro_libre_x = (b - 2 * d_prime) / (num_filas_h - 1) - rebar_diam / 10 if num_filas_h > 1 else 0
    claro_libre_y = (h - 2 * d_prime) / (num_filas_v - 1) - rebar_diam / 10 if num_filas_v > 1 else 0
    
    num_flejes_y = max(0, math.ceil((b - 2 * d_prime - 15) / 15)) if claro_libre_x > 15.0 else 0
    num_flejes_x = max(0, math.ceil((h - 2 * d_prime - 15) / 15)) if claro_libre_y > 15.0 else 0
    
    ramas_x = 2 + num_flejes_y
    ramas_y = 2 + num_flejes_x

    Ash_prov_x = ramas_x * stirrup_area
    Ash_prov_y = ramas_y * stirrup_area
    Ash_prov = min(Ash_prov_x, Ash_prov_y)

    s1 = 16 * rebar_diam / 10
    s2 = 48 * stirrup_diam / 10
    s3 = min(b, h)
    s3_db = 6*rebar_diam/10  # cm NSR-10 C.21.6.4.3
    s_basico = min(s1, s2, s3)
    
    Lo_conf = max(max(b, h), L_col / 6.0, 45.0)
    
    if es_des:
        s_conf = min(8*rebar_diam/10, 24*stirrup_diam/10, min(b,h)/3, 15.0, s3_db)
        s_centro = min(6*rebar_diam/10, s_basico)
        s_centro = max(s_centro, s_conf)
    else:
        # DMO y DMI
        s_conf = min(8*rebar_diam/10, 24*stirrup_diam/10, min(b,h)/3, 15.0, s3_db)
        s_centro = s_basico
    
    fyt = fy
    
    Ash_req_1 = 0.3 * s_conf * bc * fc / fyt * (Ag / Ach - 1)
    Ash_req_2 = 0.09 * s_conf * bc * fc / fyt
    Ash_req = max(Ash_req_1, Ash_req_2)

    ash_ok = Ash_prov >= Ash_req
    
    n_est_por_Lo = math.ceil(Lo_conf / s_conf)
    n_estribos_zona = n_est_por_Lo * 2
    longitud_zona_libre = max(0, L_col - 2 * Lo_conf)
    n_estribos_centro = max(0, math.ceil(longitud_zona_libre / s_centro) - 1) if longitud_zona_libre > 0 else 0
    n_estribos_total = n_estribos_zona + n_estribos_centro + 1
    
    ld_mm = get_development_length(rebar_diam, fy, fc)
    splice_length_cm = 1.3 * (ld_mm / 10.0)
    splice_zone_height = splice_length_cm
    splice_start = max(L_col / 3, 0)
    splice_end = splice_start + splice_zone_height
    if splice_end > L_col:
        splice_end = L_col
        splice_start = max(0, L_col - splice_zone_height)
    
    # Para usar en despiece
    perim_estribo = 2 * (b - 2 * recub_cm) + 2 * (h - 2 * recub_cm) + 12 * stirrup_diam / 10
    long_fleje_x = h - 2 * recub_cm + 2 * 6 * stirrup_diam / 10
    long_fleje_y = b - 2 * recub_cm + 2 * 6 * stirrup_diam / 10
    perim_estribo += (num_flejes_x * long_fleje_x + num_flejes_y * long_fleje_y)
else:
    recub_cm = max(d_prime - rebar_diam / 20.0, 2.5)
    _recub_min_nsr = COVER_MIN_COL.get(norma_sel, 3.8)
    _cover_ref_nsr = COVER_REF_COL.get(norma_sel, "C.7.7.1")
    if recub_cm < _recub_min_nsr:
        st.sidebar.warning(f"⚠️ {_cover_ref_nsr}: Recubrimiento calculado ({recub_cm:.1f} cm) < mínimo de {_recub_min_nsr} cm según {norma_sel}.")
    dc = D - 2 * recub_cm
    Ach = math.pi * (dc/2)**2
    Ag_circ = math.pi * (D/2)**2
    
    rho_s_req = 0.45 * (Ag_circ / Ach - 1) * fc / fy
    rho_s_req = max(rho_s_req, 0.12 * fc / fy)
    
    area_spiral = stirrup_area
    rho_s_prov = (4 * area_spiral) / (dc * paso_espiral)
    ash_ok = rho_s_prov >= rho_s_req
    n_estribos_total = math.ceil(L_col / paso_espiral) + 1
    
    ld_mm = get_development_length(rebar_diam, fy, fc)
    splice_length_cm = 1.3 * (ld_mm / 10.0)
    splice_zone_height = splice_length_cm
    splice_start = max(L_col / 3, 0)
    splice_end = splice_start + splice_zone_height
    if splice_end > L_col:
        splice_end = L_col
        splice_start = max(0, L_col - splice_zone_height)
    
    # Para usar en despiece circular
    long_espiral_vuelta = math.sqrt((math.pi * dc)**2 + paso_espiral**2)
    long_espiral_total = long_espiral_vuelta * (L_col / paso_espiral)

# =============================================================================
# CANTIDADES DE MATERIALES
# =============================================================================
vol_concreto_m3 = (Ag / 10000) * (L_col / 100) if not es_circular else (math.pi * (D/2)**2 / 10000) * (L_col / 100)
peso_acero_long_kg = Ast * (L_col * 10) * 7.85e-3

if not es_circular:
    peso_unit_estribo = (perim_estribo / 100.0) * (stirrup_area * 100) * 7.85e-3
    peso_total_estribos_kg = n_estribos_total * peso_unit_estribo
else:
    peso_total_estribos_kg = long_espiral_total / 100 * (stirrup_area * 100) * 7.85e-3

peso_total_acero_kg = peso_acero_long_kg + peso_total_estribos_kg

# =============================================================================
# GRÁFICO 3D BIAXIAL
# =============================================================================
def create_biaxial_3d_plot(cap_x, cap_y, Pu, Mux, Muy, phi_factor_eval):
    Mx_vals = np.linspace(0, max(cap_x['phi_M_n']) * 1.1, 30)
    My_vals = np.linspace(0, max(cap_y['phi_M_n']) * 1.1, 30)
    Mx_grid, My_grid = np.meshgrid(Mx_vals, My_vals)
    P_grid = np.zeros_like(Mx_grid)
    
    for i in range(len(Mx_vals)):
        for j in range(len(My_vals)):
            res = biaxial_bresler(Pu, Mx_grid[i,j], My_grid[i,j], cap_x, cap_y, cap_x['Po'], phi_factor_eval)
            P_grid[i,j] = res['phi_Pni'] if res['phi_Pni'] > 0 else 0
    
    fig = go.Figure()
    fig.add_trace(go.Surface(x=Mx_grid, y=My_grid, z=P_grid, colorscale='Viridis', opacity=0.85,
                             name='Superficie de Interacción', showscale=True,
                             colorbar=dict(title=f"φPn [{unidad_fuerza}]")))
    fig.add_trace(go.Scatter3d(x=[Mux], y=[Muy], z=[Pu], mode='markers',
                               marker=dict(size=8, color='red', symbol='circle'),
                               name=f'Punto de Diseño (Mux={Mux:.1f}, Muy={Muy:.1f}, Pu={Pu:.1f})'))
    fig.update_layout(title=_t("Superficie de Interacción Biaxial (Método de Bresler)", "Biaxial Interaction Surface (Bresler Method)"),
                      scene=dict(xaxis_title=f"Mux [{unidad_mom}]", yaxis_title=f"Muy [{unidad_mom}]",
                                 zaxis_title=f"φPn [{unidad_fuerza}]", aspectmode='manual', aspectratio=dict(x=1, y=1, z=0.8)),
                      height=600, margin=dict(l=0, r=0, b=0, t=40))
    return fig

def create_pm_2d_plot(cap_x, Pu, Mu, unidad_mom, unidad_fuerza):
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor('#1e1e2e')
    for _ax in fig.get_axes(): _ax.set_facecolor('#14142a'); _ax.tick_params(colors='#cdd6f4'); _ax.xaxis.label.set_color('#cdd6f4'); _ax.yaxis.label.set_color('#cdd6f4')
    ax.plot(cap_x['M_n'], cap_x['P_n'], 'b--', linewidth=1.5, label=r"Resistencia Nominal ($P_n, M_n$)")
    ax.plot(cap_x['phi_M_n'], cap_x['phi_P_n'], 'r-', linewidth=2.5, label=r"Resistencia de Diseño ($\phi P_n, \phi M_n$)")
    
    P_bal = cap_x.get('P_balance', None)
    P_ten = cap_x.get('P_tension', None)
    
    # Rellenar zonas de compresión, transición y tracción
    if P_bal is not None:
        ax.plot(cap_x['M_balance'], cap_x['P_balance'], 'ro', markersize=6, markeredgecolor='black', label=f"Falla Balanceada ($ε_t = ε_y$)")
        ax.axhline(P_bal, color='orange', linestyle='--', alpha=0.5)
    if P_ten is not None:
        ax.plot(cap_x['M_tension'], cap_x['P_tension'], 'go', markersize=6, markeredgecolor='black', label=f"Control a Tracción ($ε_t = 0.005$)")
        ax.axhline(P_ten, color='green', linestyle='--', alpha=0.5)
    
    ymax = max(cap_x['P_n']) * 1.05
    ymin = min(cap_x['P_n']) * 1.05
    xmax = max(cap_x['M_n']) * 1.15
    if P_bal is not None and P_ten is not None:
        ax.fill_between([0, xmax], P_bal, ymax, color='orange', alpha=0.07, label='Interacción Compresión')
        ax.fill_between([0, xmax], P_ten, P_bal, color='yellow', alpha=0.1, label='Transición')
        ax.fill_between([0, xmax], ymin, P_ten, color='green', alpha=0.07, label='Interacción Tracción')

    ax.plot(Mu, Pu, 'o', markersize=9, color='lime', markeredgecolor='black', zorder=6,
            label=f"Punto de Diseño (Mu={Mu:.1f}, Pu={Pu:.1f})")
    ax.axhline(y=0, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlabel(f"Momento Flector M [{unidad_mom}]")
    ax.set_ylabel(f"Carga Axial P [{unidad_fuerza}]")
    ax.set_title(f"Diagrama de Interacción P-M — {norma_sel}\n" +
                 f"Columna {b:.0f}×{h:.0f} cm | f'c={fc:.1f} MPa | fy={fy:.0f} MPa")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=8)
    return fig

fig_pm_2d = create_pm_2d_plot(cap_x, Pu_input, Mux_input, unidad_mom, unidad_fuerza)
pm_2d_img = io.BytesIO()
fig_pm_2d.savefig(pm_2d_img, facecolor='white', edgecolor='none', format='png', dpi=150, bbox_inches='tight')
pm_2d_img.seek(0)
fig_3d = create_biaxial_3d_plot(cap_x, cap_y, Pu_input, Mux_input, Muy_input, phi_factor)

try:
    pm_3d_img = io.BytesIO()
    fig_3d.write_image(pm_3d_img, format="png")
    pm_3d_img.seek(0)
    has_3d_img = True
except Exception:
    has_3d_img = False

# =============================================================================
# TABS PRINCIPALES
# =============================================================================

# =============================================================================
# PASO 4 — def render_config_tab()
#           Todos los widgets de calculo van aqui. Se llama SOLO desde tab0.
# =============================================================================
def render_config_tab():
    st.markdown("### Parametros de Diseno")
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("1. Materiales")
        _fc_unit_w = st.radio("Unidad de f'c:", ["MPa", "PSI", "kg/cm2"],
                              horizontal=True, key="c_pm_fc_unit")
        if _fc_unit_w == "PSI":
            _psi_opts = {
                "2500 PSI (17.2 MPa)": 2500.0, "3000 PSI (20.7 MPa)": 3000.0,
                "3500 PSI (24.1 MPa)": 3500.0, "4000 PSI (27.6 MPa)": 4000.0,
                "4500 PSI (31.0 MPa)": 4500.0, "5000 PSI (34.5 MPa)": 5000.0,
                "Personalizado": None
            }
            _psi_ch = st.selectbox("Resistencia f'c [PSI]", list(_psi_opts.keys()), key="c_pm_psi_choice")
            if _psi_opts[_psi_ch] is not None:
                st.session_state["c_pm_fc_psi_val"] = _psi_opts[_psi_ch]
                st.caption(f"fc = {_psi_opts[_psi_ch] * 0.00689476:.2f} MPa")
            else:
                _pv = st.number_input("f'c personalizado [PSI]", 2000.0, 12000.0, 3000.0, 100.0, key="c_pm_fc_psi_custom")
                st.session_state["c_pm_fc_psi_val"] = _pv
        elif _fc_unit_w == "kg/cm2":
            _kg_opts = {
                "175 kg/cm2 (17.2 MPa)": 175.0, "210 kg/cm2 (20.6 MPa)": 210.0,
                "250 kg/cm2 (24.5 MPa)": 250.0, "280 kg/cm2 (27.5 MPa)": 280.0,
                "350 kg/cm2 (34.3 MPa)": 350.0, "420 kg/cm2 (41.2 MPa)": 420.0,
                "Personalizado": None
            }
            _kg_ch = st.selectbox("Resistencia f'c [kg/cm2]", list(_kg_opts.keys()), key="c_pm_kgcm2_choice")
            if _kg_opts[_kg_ch] is not None:
                st.session_state["c_pm_fc_kgcm2_val"] = _kg_opts[_kg_ch]
                st.caption(f"fc = {_kg_opts[_kg_ch] / 10.1972:.2f} MPa")
            else:
                _kv = st.number_input("f'c personalizado [kg/cm2]", 100.0, 1200.0, 210.0, 10.0, key="c_pm_fc_kgcm2_custom")
                st.session_state["c_pm_fc_kgcm2_val"] = _kv
        else:
            st.number_input("Resistencia del Concreto f'c [MPa]", 15.0, 80.0, 21.0, 1.0, key="c_pm_fc_mpa")
        st.number_input("Fluencia del Acero fy [MPa]", 240.0, 500.0, 420.0, 10.0, key="c_pm_fy")

        st.markdown("---")
        st.subheader("2. Geometria de la Seccion")
        st.selectbox("Tipo de seccion",
                     ["Rectangular / Cuadrada", "Circular (con espiral)"],
                     key="c_pm_seccion_type")
        _es_circ_cfg = "Circular" in st.session_state.get("c_pm_seccion_type", "Rectangular / Cuadrada")
        if _es_circ_cfg:
            st.number_input("Diametro D [cm]", 15.0, 150.0, 40.0, 5.0, key="c_pm_D")
            st.caption("Para pilares circulares de gran diametro (puentes, silos) use el modulo Pilares Circulares.")
        else:
            _ca, _cb = st.columns(2)
            _ca.number_input("Base b [cm]",   15.0, 150.0, 30.0, 5.0, key="c_pm_b")
            _cb.number_input("Altura h [cm]", 15.0, 150.0, 40.0, 5.0, key="c_pm_h")
        st.number_input("Recubrimiento al centroide d' [cm]", 2.0, 15.0, 5.0, 0.5, key="c_pm_dprime")
        st.number_input("Altura libre de la columna L [cm]", 50.0, 1000.0, 300.0, 25.0, key="c_pm_L")

        st.markdown("---")
        st.subheader("6. Esbeltez")
        st.number_input("Factor de carga sostenida (beta dns)", 0.0, 1.0, 0.6, 0.1,
                        help="Relacion M_sostenido / M_total. Default 0.6", key="c_pm_beta_dns")
        st.selectbox("Factor de longitud efectiva k",
                     ["Ambos extremos articulados",
                      "Un extremo articulado, otro empotrado",
                      "Ambos extremos empotrados",
                      "Voladizo (base empotrada, libre arriba)"],
                     key="c_pm_k_sel")

    with col_der:
        st.subheader("3. Refuerzo Longitudinal")
        st.radio("Sistema de unidades de varillas:",
                 ["Milimetros (SI)", "Pulgadas (EE. UU.)"],
                 horizontal=True, key="c_pm_unit_system")
        _rbd_cfg  = REBAR_US if ("Pulgadas" in st.session_state.get("c_pm_unit_system","") or
                                  "Inches"  in st.session_state.get("c_pm_unit_system","")) else REBAR_MM
        _rb_keys  = list(_rbd_cfg.keys())
        _rb_def   = st.session_state.get("c_pm_rebar_type", _rb_keys[2] if len(_rb_keys) > 2 else _rb_keys[0])
        if _rb_def not in _rb_keys: _rb_def = _rb_keys[0]
        st.selectbox("Diametro de las varillas", _rb_keys,
                     index=_rb_keys.index(_rb_def), key="c_pm_rebar_type")

        _es_circ_rb = "Circular" in st.session_state.get("c_pm_seccion_type","")
        if _es_circ_rb:
            st.number_input("Numero de varillas longitudinales", 4, 20, 8, 2, key="c_pm_n_barras_circ")
        else:
            _cr1, _cr2 = st.columns(2)
            _cr1.number_input("Filas horizontales (sup e inf)", 2, 15, 2, 1, key="c_pm_num_h")
            _cr2.number_input("Filas verticales (laterales)",   2, 15, 2, 1, key="c_pm_num_v")

        st.markdown("---")
        st.subheader("4. Refuerzo Transversal")
        _strd_cfg = STIRRUP_US if ("Pulgadas" in st.session_state.get("c_pm_unit_system","") or
                                    "Inches"  in st.session_state.get("c_pm_unit_system","")) else STIRRUP_MM
        if _es_circ_rb:
            _sp_keys = list(_strd_cfg.keys())
            _sp_def  = st.session_state.get("c_pm_spiral_type", _sp_keys[0])
            if _sp_def not in _sp_keys: _sp_def = _sp_keys[0]
            st.selectbox("Diametro de la espiral", _sp_keys,
                         index=_sp_keys.index(_sp_def), key="c_pm_spiral_type")
            st.number_input("Paso de la espiral s [cm]", 2.0, 20.0, 7.5, 0.5, key="c_pm_paso_circ")
        else:
            st.selectbox("Tipo de columna",
                         ["Estribos (Tied)", "Espiral (Spiral)"], key="c_pm_col_type")
            _st_keys = list(_strd_cfg.keys())
            _st_def  = st.session_state.get("c_pm_stirrup_type", _st_keys[0])
            if _st_def not in _st_keys: _st_def = _st_keys[0]
            st.selectbox("Diametro del estribo", _st_keys,
                         index=_st_keys.index(_st_def), key="c_pm_stirrup_type")

        st.markdown("---")
        st.subheader("5. Solicitaciones Biaxiales")
        st.radio("Unidades del diagrama:",
                 ["KiloNewtons (kN, kN-m)", "Toneladas Fuerza (tonf, tonf-m)"],
                 horizontal=True, key="c_pm_output_units")
        _ff_w = 0.1019716 if "Toneladas" in st.session_state.get("c_pm_output_units","") else 1.0
        _uf_w = "tonf"   if "Toneladas" in st.session_state.get("c_pm_output_units","") else "kN"
        _um_w = "tonf-m" if "Toneladas" in st.session_state.get("c_pm_output_units","") else "kN-m"
        _cs1, _cs2, _cs3 = st.columns(3)
        _cs1.number_input(f"Pu [{_uf_w}]",  value=round(2700.0*_ff_w,2), step=round(50.0*_ff_w,2),  key="c_pm_pu")
        _cs2.number_input(f"Mux [{_um_w}]", value=round(45.0*_ff_w,2),   step=round(10.0*_ff_w,2),  key="c_pm_mux")
        _cs3.number_input(f"Muy [{_um_w}]", value=round(25.0*_ff_w,2),   step=round(10.0*_ff_w,2),  key="c_pm_muy")
        st.checkbox("Especificar Curvatura Simple M1/M2", value=False,
                    help="Permite calcular Cm diferente a 1.0", key="c_pm_cm_chk")
        if st.session_state.get("c_pm_cm_chk"):
            _cm1, _cm2 = st.columns(2)
            _cm1.number_input(f"Momento menor M1x [{_um_w}]", value=0.0, step=round(10.0*_ff_w,2), key="c_pm_m1x")
            _cm2.number_input(f"Momento menor M1y [{_um_w}]", value=0.0, step=round(10.0*_ff_w,2), key="c_pm_m1y")

        st.markdown("---")
        st.subheader("Resumen de la Seccion")
        st.info(
            f"f'c = {st.session_state.get('c_pm_fc_mpa', 21.0)} MPa  |  "
            f"fy = {st.session_state.get('c_pm_fy', 420.0)} MPa  |  "
            f"Norma: {norma_sel}  |  Nivel: {nivel_sismico}  |  "
            f"rho min: {rho_min}%  |  rho max: {rho_max}%"
        )


# =============================================================================
# PASO 5 — HEADER BANNER + METRICAS SUPERIORES
# =============================================================================

_emp_hdr  = st.session_state.get("cpm_empresa","") or "StructoPro"
_proy_hdr = st.session_state.get("cpm_proyecto_nombre","") or "Diseno de Columnas P-M"

st.markdown(
    f"""<div style="background:linear-gradient(135deg,#0d1b2a 0%,#1e3a5f 60%,#2e6da4 100%);
    padding:20px 32px;border-radius:12px;margin-bottom:14px">
    <div style="display:flex;align-items:center;gap:16px">
    <div style="background:rgba(255,255,255,0.1);border-radius:8px;padding:8px">
    <span style="font-size:30px;line-height:1">&#9632;</span></div>
    <div>
    <h1 style="color:white;margin:0;font-size:1.8rem;font-weight:800">{_emp_hdr} &mdash; Columnas P-M</h1>
    <p style="color:#90caf9;margin:4px 0 0;font-size:0.9rem">
    Proyecto: {_proy_hdr} &nbsp;|&nbsp; {norma_sel} &nbsp;|&nbsp; {nivel_sismico}
    </p></div></div></div>""",
    unsafe_allow_html=True
)

if abs(Mux_input) < _Mux_emin or abs(Muy_input) < _Muy_emin:
    st.info(
        f"Excentricidad minima NSR-10 C.10.3.6: "
        f"ex={e_min_x_cm:.2f} cm -> Mux >= {_Mux_emin:.2f} {unidad_mom}  |  "
        f"ey={e_min_y_cm:.2f} cm -> Muy >= {_Muy_emin:.2f} {unidad_mom}"
    )

_ratio_ok = bresler["ok"]
_cur_ok   = (rho_min <= cuantia <= rho_max)
_slend_ok = slenderness["kl_r"] <= 100

_m1, _m2, _m3, _m4, _m5 = st.columns(5)
_m1.metric("Pu", f"{Pu_input:.1f} {unidad_fuerza}")
_m2.metric("phi·Pni (Bresler)", f"{bresler['phi_Pni']:.1f} {unidad_fuerza}",
           delta="CUMPLE" if _ratio_ok else "NO CUMPLE",
           delta_color="normal" if _ratio_ok else "inverse")
_m3.metric("Ratio Pu / phi·Pni", f"{bresler['ratio']:.3f}",
           delta_color="normal" if _ratio_ok else "inverse")
_m4.metric("Cuantia rho", f"{cuantia:.2f}%",
           delta="OK" if _cur_ok else "FUERA DE LIMITES",
           delta_color="normal" if _cur_ok else "inverse")
_m5.metric("Esbeltez kL/r", f"{slenderness['kl_r']:.1f}",
           delta="Corta" if slenderness["kl_r"] <= 22 else (
               "Esbelta" if slenderness["kl_r"] <= 100 else "Muy esbelta"),
           delta_color="normal" if _slend_ok else "inverse")

st.markdown("---")

# =============================================================================
# PASO 6 — TABS PRINCIPALES
# =============================================================================
tab0, tab1, tab2, tab2b, tab3, tab4 = st.tabs([
    "Configuracion",
    "Diagrama P-M Biaxial",
    "Seccion y Estribos 3D",
    "Alzado y Combos de Carga",
    "Cantidades y APU",
    "Memoria de Calculo",
])

with tab0:
    render_config_tab()

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(_t("Diagrama P-M 2D (Eje X)", " P-M 2D Diagram (X-Axis)"))
        configurar_pdf_comercial(fig_pm_2d)
        st.pyplot(fig_pm_2d)
        st.subheader(_t("Superficie de Interacción Biaxial 3D", "Biaxial Interaction Surface 3D"))
        st.plotly_chart(fig_3d, use_container_width=True)
    with col2:
        st.subheader(_t("Verificación Biaxial (Bresler)", " Biaxial Verification (Bresler)"))
        st.markdown(f"""
        | Parámetro | Valor |
        |-----------|-------|
        | **φPnx** (para Mux={Mux_input:.1f}) | {bresler['phi_Pnx']:.2f} {unidad_fuerza} |
        | **φPny** (para Muy={Muy_input:.1f}) | {bresler['phi_Pny']:.2f} {unidad_fuerza} |
        | **φP0** (axial pura) | {bresler['phi_P0']:.2f} {unidad_fuerza} |
        | **φPni** (Bresler) | {bresler['phi_Pni']:.2f} {unidad_fuerza} |
        | **Pu** solicitante | {Pu_input:.2f} {unidad_fuerza} |
        | **Relación Pu/φPni** | {bresler['ratio']:.3f} |
        """)
        if bresler['ok']:
            st.success(f"**VERIFICACIÓN BIAXIAL CUMPLE**\n\nPu ({Pu_input:.1f}) ≤ φPni ({bresler['phi_Pni']:.1f})")
        else:
            st.error(f"**VERIFICACIÓN BIAXIAL NO CUMPLE**\n\nPu ({Pu_input:.1f}) > φPni ({bresler['phi_Pni']:.1f})")
            ratio = bresler['ratio']
            deficit = Pu_input - bresler['phi_Pni']
            st.markdown("** Recomendaciones para cumplir:**")
            recomendaciones = []
            if ratio > 1.5 and math.isfinite(ratio):
                pct = math.ceil((ratio**0.5 - 1) * 100)
                recomendaciones.append(f" **Aumentar sección:** La columna necesita ~{pct}% más de área — aumentar b y/o h en el sidebar.")
            if ratio <= 3:
                rho_obj = min(rho_max, cuantia * ratio**0.5)
                recomendaciones.append(f" **Aumentar acero longitudinal:** Añadir varillas o usar diámetro mayor — apuntar a ρ ≥ {rho_obj:.1f}%.")
            if ratio > 2:
                recomendaciones.append(f" **Reducir Pu:** La carga axial ({Pu_input:.0f} {unidad_fuerza}) supera {ratio:.1f}x la capacidad — revisar predimensionamiento.")
            if Mux_input > 0 or Muy_input > 0:
                recomendaciones.append(" **Reducir momentos Mux/Muy:** Considerar arriostrar la estructura o reducir excentricidades.")
            for rec in recomendaciones:
                st.markdown(f"- {rec}")
            st.markdown(f"""
| | |
|---|---|
| **Capacidad requerida** | φPni ≥ {Pu_input:.1f} {unidad_fuerza} |
| **Capacidad actual** | φPni = {bresler['phi_Pni']:.1f} {unidad_fuerza} |
| **Déficit** | {deficit:.1f} {unidad_fuerza} ({(ratio-1)*100:.0f}% sobre la capacidad) |
""")
            if ratio > 5:
                st.error(" **Relación > 5x:** La sección es muy insuficiente. Se recomienda rediseñar completamente la geometría.")
        st.markdown("---")
        st.subheader(_t("Verificación de Esbeltez", "Slenderness Verification"))
        st.markdown(f"""
        | Parámetro | Valor | Estado |
        |-----------|-------|--------|
        | **kl/r** | {slenderness['kl_r']:.1f} | |
        | **Clasificación** | {slenderness['classification']} | |
        | **δns (magnificación)** | {slenderness['delta_ns']:.3f} | |
        | **Mux magnificado** | {Mux_magnified:.2f} {unidad_mom} | |
        | **Muy magnificado** | {Muy_magnified:.2f} {unidad_mom} | |
        """)
        if slenderness['kl_r'] > 100:
            st.warning(f"⚠️ **kl/r > 100** — Se requiere análisis no lineal de segundo orden según {norma_sel}.")
        elif slenderness['kl_r'] > 22:
            st.info(
                f"ℹ️ **Método no-sway aplicado (δns = {slenderness['delta_ns']:.3f}).** "
                f"Si la estructura es **desplazable** (pórtico sin arriostramiento lateral), "
                f"calcule δs mediante análisis P-Δ directo según {norma_sel} e ingrese los momentos "
                f"amplificados como Mux / Muy antes de ejecutar el diagrama."
            )
        st.markdown("---")
        st.subheader(_t("Verificación de Estribos / Espiral", "Tie / Spiral Verification"))
        if not es_circular:
            req_1_str = f"0.3 \\times {s_conf:.1f} \\times {bc:.1f} \\times ({fc:.1f}/{fyt:.0f}) \\times ({Ag:.1f}/{Ach:.1f} - 1) = {Ash_req_1:.2f} \\text{{ cm}}^2"
            req_2_str = f"0.09 \\times {s_conf:.1f} \\times {bc:.1f} \\times ({fc:.1f}/{fyt:.0f}) = {Ash_req_2:.2f} \\text{{ cm}}^2"
            
            st.markdown(f"**Cálculo de Ash requerido (NSR-10 C.21.3.5.4):**")
            st.latex(r"(a) \quad A_{sh} = " + req_1_str)
            st.latex(r"(b) \quad A_{sh} = " + req_2_str)
            st.markdown(f"**→ Rige: {Ash_req:.2f} cm²**")

            st.markdown(f"""
            | Parámetro | Valor | Requerido | Estado |
            |-----------|-------|-----------|--------|
            | **Claro Libre (Cx, Cy)** | {claro_libre_x:.1f} cm, {claro_libre_y:.1f} cm | ≤ 15 cm | {'' if claro_libre_x<=15 and claro_libre_y<=15 else ' Crossties Requeridos'} |
            | **Apoyo lateral (Crossties)** | {num_flejes_x} en X, {num_flejes_y} en Y | NSR-10 C.7.10.5 | |
            | **Ramas Efectivas** | {ramas_x} ramas en X, {ramas_y} ramas en Y | | |
            | **Ash provisto** | {Ash_prov:.3f} cm² | ≥ {Ash_req:.2f} | {'' if ash_ok else ''} |
            | **s_conf** | {s_conf:.1f} cm | {'≤ 15' if es_des else '≤ 20' if es_dmo else '≤ min(b,h)'} | |
            | **Lo_conf** | {Lo_conf:.1f} cm | ≥ max(b,h,L/6,45) | {''} |
            | **N° estribos + Crossties** | {n_estribos_total} juegos de ramas | C.21.3.5 | |
            """)

            if not ash_ok:
                ratio_ash = Ash_prov / Ash_req if Ash_req > 0 else 1.0
                s_req1 = Ash_prov / (0.3 * bc * fc / fyt * (Ag/Ach - 1)) if (Ag/Ach - 1) > 0 else 999
                s_req2 = Ash_prov * fyt / (0.09 * bc * fc)
                s_correcto = min(s_req1, s_req2)
                
                if ratio_ash < 0.5:
                    st.error(f" **Déficit crítico de estribos.** Para cumplir con las estribos actuales, usar separación $s \\le {s_correcto:.1f}$ cm o proponer más ramas.")
                else:
                    st.warning(f"Para cumplir Ash con los estribos actuales → reducir separación a $s \\le {s_correcto:.1f}$ cm.")
        else:
            st.markdown(f"""
            | Parámetro | Valor | Requerido | Estado |
            |-----------|-------|-----------|--------|
            | **ρs requerido** | {rho_s_req:.4f} | | |
            | **ρs provisto** | {rho_s_prov:.4f} | ≥ {rho_s_req:.4f} | {'' if ash_ok else ''} |
            | **Paso espiral** | {paso_espiral:.1f} cm | ≤ min(D/5, 8 cm) | {'' if paso_espiral <= min(D/5, 8) else ''} |
            | **N° vueltas** | {n_estribos_total} | | |
            """)
        st.caption(f"Ref: {code['ref']} | Nivel Sísmico: {nivel_sismico}")

# =============================================================================
# TAB 2: SECCIÓN Y ESTRIBOS (con DXF y RÓTULO ICONTEC)
# =============================================================================
with tab2:
    st.subheader(_t("Visualización 3D de la Columna", "3D Column Visualization"))
    fig3d_col = go.Figure()
    if es_circular:
        theta = np.linspace(0, 2*np.pi, 50)
        z = np.linspace(0, L_col, 20)
        theta_grid, z_grid = np.meshgrid(theta, z)
        x_grid = (D/2) * np.cos(theta_grid)
        y_grid = (D/2) * np.sin(theta_grid)
        fig3d_col.add_trace(go.Surface(x=x_grid, y=y_grid, z=z_grid, opacity=0.3, colorscale='Greys', showscale=False))
    else:
        x_c = [-b/2, b/2, b/2, -b/2, -b/2, b/2, b/2, -b/2]
        y_c = [-h/2, -h/2, h/2, h/2, -h/2, -h/2, h/2, h/2]
        z_c = [0, 0, 0, 0, L_col, L_col, L_col, L_col]
        fig3d_col.add_trace(go.Mesh3d(x=x_c, y=y_c, z=z_c, alphahull=0, opacity=0.15, color='gray', name='Concreto'))
        
    #  BARRAS LONGITUDINALES 3D 
    z_barras = [0, L_col]
    if es_circular:
        radio_c = D/2 - d_prime
        for layer in layers:
            xb = layer.get('x', 0)
            yb = layer.get('y', 0)
            fig3d_col.add_trace(go.Scatter3d(
                x=[xb, xb], y=[yb, yb], z=z_barras,
                mode='lines',
                line=dict(color='#ff6b35', width=4),
                showlegend=False, name='Barra long.'
            ))
    else:
        r_bar3d = rebar_diam / 20.0
        xs3d = np.linspace(d_prime - b/2, b/2 - d_prime, num_filas_h) if num_filas_h > 1 else [0.0]
        ys3d_bot = -(h/2 - d_prime)
        ys3d_top =   h/2 - d_prime
        for x3 in xs3d:
            for y3 in [ys3d_bot, ys3d_top]:
                fig3d_col.add_trace(go.Scatter3d(
                    x=[x3, x3], y=[y3, y3], z=z_barras,
                    mode='lines',
                    line=dict(color='#ff6b35', width=4),
                    showlegend=False, name='Barra long.'
                ))
        if num_capas_intermedias > 0:
            esp3d = (h - 2*d_prime) / (num_capas_intermedias + 1)
            for ci in range(1, num_capas_intermedias + 1):
                yi = -(h/2) + d_prime + ci * esp3d
                for xi in [-(b/2 - d_prime), b/2 - d_prime]:
                    fig3d_col.add_trace(go.Scatter3d(
                        x=[xi, xi], y=[yi, yi], z=z_barras,
                        mode='lines',
                        line=dict(color='#ff6b35', width=4),
                        showlegend=False, name='Barra lat.'
                    ))

    #  ESTRIBOS 3D 
    if not es_circular:
        paso_3d = s_conf if (es_des or es_dmo) else s_basico
        z_est = np.arange(0, L_col + paso_3d, paso_3d)
        bw = b/2 - recub_cm
        hw = h/2 - recub_cm
        estr_x = [-bw, bw, bw, -bw, -bw]
        estr_y = [-hw, -hw, hw, hw, -hw]
        for ze in z_est:
            fig3d_col.add_trace(go.Scatter3d(
                x=estr_x, y=estr_y,
                z=[ze]*5,
                mode='lines',
                line=dict(color='#00d4ff', width=2),
                showlegend=False, name='Estribo'
            ))
    else:
        rc_sp = D/2 - recub_cm
        theta_sp = np.linspace(0, 2*np.pi, 36)
        z_sp = np.arange(0, L_col + paso_espiral, paso_espiral)
        for ze in z_sp:
            fig3d_col.add_trace(go.Scatter3d(
                x=rc_sp * np.cos(theta_sp),
                y=rc_sp * np.sin(theta_sp),
                z=[ze]*len(theta_sp),
                mode='lines',
                line=dict(color='#00d4ff', width=2),
                showlegend=False, name='Espiral'
            ))

    # Ajustar aspecto para que no se deforme la seccion real (b vs h)
    # Correct proportional 3D aspect: scale b,h,L to each other so section looks real
    _dim_max = max(b if not es_circular else D, h if not es_circular else D, L_col)
    ar_x = (D / _dim_max) if es_circular else (b / _dim_max)
    ar_y = (D / _dim_max) if es_circular else (h / _dim_max)
    ar_z = L_col / _dim_max
    fig3d_col.update_layout(
        scene=dict(
            aspectmode='manual',
            aspectratio=dict(x=ar_x, y=ar_y, z=ar_z),
            xaxis_title='b (cm)', yaxis_title='h (cm)', zaxis_title='L (cm)',
            xaxis=dict(range=[-b/2-5, b/2+5] if not es_circular else [-D/2-5, D/2+5]),
            yaxis=dict(range=[-h/2-5, h/2+5] if not es_circular else [-D/2-5, D/2+5]),
        ),
        height=500, margin=dict(l=0, r=0, b=0, t=30),
        title=dict(text="Visualizacion 3D de la Columna — Proporciones Reales", font=dict(size=13))
    )
    st.plotly_chart(fig3d_col, use_container_width=True)
    st.markdown("---")
    st.subheader(_t("Sección Transversal", "Cross Section"))
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        fig_sec, ax_s = plt.subplots(figsize=(5, 5))
        fig_sec.patch.set_facecolor('#1e1e2e')
        for _ax in fig_sec.get_axes(): _ax.set_facecolor('#14142a'); _ax.tick_params(colors='#cdd6f4'); _ax.xaxis.label.set_color('#cdd6f4'); _ax.yaxis.label.set_color('#cdd6f4')
        ax_s.set_aspect('equal')
        ax_s.set_facecolor('#1a1a2e')
        fig_sec.patch.set_facecolor('#1a1a2e')
        if es_circular:
            circle = plt.Circle((0, 0), D/2, linewidth=2, edgecolor='white', facecolor='#4a4a6a', fill=True)
            ax_s.add_patch(circle)
            circle_rec = plt.Circle((0, 0), D/2 - recub_cm, linewidth=1.5, edgecolor='#00d4ff', facecolor='none', linestyle='--')
            ax_s.add_patch(circle_rec)
            radio_centro = D/2 - d_prime
            for layer in layers:
                x_pos = layer.get('x', 0)
                y_pos = layer.get('y', 0)
                ax_s.add_patch(plt.Circle((x_pos, y_pos), rebar_diam/20, color='#ff6b35', zorder=5))
            ax_s.set_xlim(-D/2 - 5, D/2 + 5)
            ax_s.set_ylim(-D/2 - 5, D/2 + 5)
        else:
            ax_s.add_patch(patches.Rectangle((0, 0), b, h, linewidth=2, edgecolor='white', facecolor='#4a4a6a'))
            ax_s.add_patch(patches.Rectangle((recub_cm, recub_cm), b-2*recub_cm, h-2*recub_cm,
                linewidth=1.5, edgecolor='#00d4ff', facecolor='none', linestyle='--'))
            r_bar = rebar_diam / 20.0
            xs = np.linspace(d_prime, b - d_prime, num_filas_h) if num_filas_h > 1 else [b/2]
            for x in xs:
                ax_s.add_patch(plt.Circle((x, h - d_prime), r_bar, color='#ff6b35', zorder=5))
                ax_s.add_patch(plt.Circle((x, d_prime), r_bar, color='#ff6b35', zorder=5))
            if num_capas_intermedias > 0:
                esp = (h - 2*d_prime) / (num_capas_intermedias + 1)
                for i in range(1, num_capas_intermedias + 1):
                    y_int = d_prime + i * esp
                    ax_s.add_patch(plt.Circle((d_prime, y_int), r_bar, color='#ff6b35', zorder=5))
                    ax_s.add_patch(plt.Circle((b - d_prime, y_int), r_bar, color='#ff6b35', zorder=5))
            ax_s.set_xlim(-5, b + 5)
            ax_s.set_ylim(-5, h + 5)
        ax_s.axis('off')
        ax_s.set_title(f"Sección {'Circular' if es_circular else 'Rectangular'} — {n_barras} varillas {_bar_label_short(rebar_diam)}", color='white', fontsize=9)
        configurar_pdf_comercial(fig_sec)
        st.pyplot(fig_sec)
    with col_s2:
        st.subheader(_t("Resumen de Verificaciones", "Verification Summary"))
        checks_data = {
            "Verificación": ["Cuantía longitudinal", "Verificación biaxial", "Esbeltez (kl/r ≤ 22)",
                             f"Ash {'espiral' if es_circular else 'estribos'}", "Longitud confinamiento Lo", "Separación máxima"],
            "Estado": ["" if rho_min <= cuantia <= rho_max else "", "" if bresler['ok'] else "",
                       "" if slenderness['kl_r'] <= 22 else "", "" if ash_ok else "",
                       "",
                       "" if (es_des and s_conf <= 15) or (es_dmo and s_conf <= 20) or es_dmi else ""]
        }
        st.dataframe(pd.DataFrame(checks_data), use_container_width=True, hide_index=True)
        st.markdown("---")
        st.subheader(_t("Exportar Plano DXF (ICONTEC)", "Export DXF (ICONTEC)"))

        # ── CONFIGURACION DEL PLANO ─────────────────────────────────────────
        with st.expander(_t("Configurar Plano y Rotulo", "Configure Plot & Title Block"), expanded=True):
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                dxf_empresa  = st.text_input("Empresa",  "INGENIERIA ESTRUCTURAL SAS", key="col_dxf_emp")
                dxf_proyecto = st.text_input("Proyecto", "Proyecto Estructural",        key="col_dxf_proy")
                dxf_plano    = st.text_input("N Plano",  "COL-001",                     key="col_dxf_num")
                dxf_elaboro  = st.text_input("Elaboro",  "Ing. Disenador",              key="col_dxf_elab")
            with col_cfg2:
                dxf_reviso   = st.text_input("Reviso",   "Ing. Revisor",                key="col_dxf_rev")
                dxf_aprobo   = st.text_input("Aprobo",   "Ing. Aprobador",              key="col_dxf_apr")
                # Selector de tamanio de papel colombiano (ICONTEC)
                papel_opciones = {
                    "Carta  (216 x 279 mm)":     (21.6,  27.9,  "CARTA"),
                    "Oficio (216 x 330 mm)":     (21.6,  33.0,  "OFICIO"),
                    "Medio Pliego (500 x 707 mm)":(50.0,  70.7,  "MEDIO PLIEGO"),
                    "Pliego       (707 x 1000 mm)":(70.7, 100.0, "PLIEGO"),
                }
                papel_sel = st.selectbox("Tamano de Papel (ICONTEC)", list(papel_opciones.keys()), index=0, key="col_dxf_papel")
                ANCHO_PLANO, ALTO_PLANO, PAPEL_LABEL = papel_opciones[papel_sel]

        # ── GENERACION DXF ──────────────────────────────────────────────────
        if st.button(_t("Generar Plano DXF ICONTEC", "Generate DXF ICONTEC"), key="col_btn_dxf"):
            try:
                from ezdxf.enums import TextEntityAlignment
                doc_dxf = ezdxf.new('R2010', setup=True)
                # 1. Configurar unidades a milímetros estrictos
                doc_dxf.header['$INSUNITS'] = 5 # units.CM (Critico para que no desparezca el corte)

                # Lineweights ICONTEC (en mm x 100 para ezdxf)
                # ICONTEC NTC 1033 / ISO 128: 0.18, 0.25, 0.35, 0.50, 0.70 mm
                LW = {
                    'CONCRETO':    50,   # 0.50 mm  contorno exterior
                    'ACERO_LONG':  35,   # 0.35 mm  barras longitudinales
                    'ACERO_TRANS': 25,   # 0.25 mm  estribos / flejes
                    'DOBLEZ':      25,   # 0.25 mm  diagramas de doblez
                    'COTAS':       18,   # 0.18 mm  lineas de cota
                    'TEXTO':       18,   # 0.18 mm  anotaciones
                    'EJES':        13,   # 0.13 mm  ejes de simetria
                    'ROTULO':      35,   # 0.35 mm  cuadro del rotulo
                    'MARGEN':      50,   # 0.50 mm  marco exterior
                }
                COLORES = {
                    'CONCRETO': 7,   # blanco
                    'ACERO_LONG': 7,   # rojo
                    'ACERO_TRANS': 7,   # cian
                    'DOBLEZ': 7,   # magenta
                    'COTAS': 7,   # amarillo
                    'TEXTO': 7,   # blanco
                    'EJES': 7,   # gris
                    'ROTULO': 7,   # gris
                    'MARGEN': 7,   # blanco
                }
                # Forzar TODO a Color 7 (Blanco en CAD / Negro en Papel)
                capas = {
                    'MARCO': {'color': 7, 'lw': 50},
                    'TEXTO': {'color': 7, 'lw': 18},
                    'ACERO_LONG': {'color': 7, 'lw': 35},  # ICONTEC: Color 7
                    'ACERO_TRANS': {'color': 7, 'lw': 25},  # ICONTEC: Color 7
                    'COTAS': {'color': 7, 'lw': 13},
                    'CONCRETO': {'color': 7, 'lw': 50},
                    'DOBLEZ': {'color': 7, 'lw': 25},
                    'EJES': {'color': 7, 'lw': 13, 'linetype': 'DASHDOT'},
                    'ROTULO': {'color': 7, 'lw': 35},
                    'MARGEN': {'color': 7, 'lw': 50}
                }

                def _color_acero_dxf_col(d_mm):
                    if d_mm <= 8.0: return 5   # azul 
                    if d_mm <= 10.0: return 4  # cyan 
                    if d_mm <= 12.0: return 3  # verde 
                    if d_mm <= 16.0: return 2  # amarillo 
                    if d_mm <= 20.0: return 1  # rojo
                    if d_mm <= 25.0: return 6  # magenta
                    return 1 # por defecto
                    

                for nombre, props in capas.items():
                    if nombre not in doc_dxf.layers:
                        doc_dxf.layers.new(nombre, dxfattribs={'color': props['color'], 'lineweight': props['lw']})

                msp = doc_dxf.modelspace()

                # Estilo texto
                if 'ROMANS' not in doc_dxf.styles:
                    try:    doc_dxf.styles.new('ROMANS', dxfattribs={'font':'romans.shx'})
                    except: doc_dxf.styles.new('ROMANS', dxfattribs={'font':'txt.shx'})

                # ── ESCALAS DISPONIBLES (serie normalizada ICONTEC) ─────────
                ESCALAS = [200, 100, 50, 25, 20, 10]

                # Margen y rotulo
                MARGEN   = 1.0       # cm
                ROT_H    = 4.0       # altura rotulo
                ROT_W    = ANCHO_PLANO - 2 * MARGEN
                AREA_W   = ANCHO_PLANO - 2 * MARGEN
                AREA_H   = ALTO_PLANO  - 2 * MARGEN - ROT_H - 0.5  # area util dibujo

                # FACTOR DE ESCALA PARA TEXTOS Y TABLAS SEGÚN EL PAPEL
                K_DXF = min(1.0, ANCHO_PLANO / 50.0)

                # ── ZONA ALZADO (left 45% del area) ─────────────────────────
                ALZ_W = AREA_W * 0.35
                ALZ_H = AREA_H

                # Calcular escala automatica para el alzado
                escala_den = 200  # empezar por la mas pequena
                for den in reversed(ESCALAS):
                    drawn_h = (L_col / den)        # en cm de plano
                    drawn_w = ((D if es_circular else max(b, h)) / den)
                    if drawn_h <= ALZ_H - 2.5 and drawn_w <= ALZ_W - 2.5:
                        escala_den = den
                        break
                ESCALA = 1.0 / escala_den
                ESCALA_LABEL = f"1:{escala_den}"

                # Ejes del alzado
                AX0 = MARGEN + (ALZ_W - (D if es_circular else b) * ESCALA) / 2
                AY0 = MARGEN + ROT_H + 0.8
                ALZ_WDRAW = (D if es_circular else b) * ESCALA
                ALZ_HDRAW = L_col * ESCALA

                # Marco exterior
                msp.add_lwpolyline(
                    [(MARGEN, MARGEN), (ANCHO_PLANO-MARGEN, MARGEN),
                     (ANCHO_PLANO-MARGEN, ALTO_PLANO-MARGEN),
                     (MARGEN, ALTO_PLANO-MARGEN), (MARGEN, MARGEN)],
                    dxfattribs={'layer': 'MARGEN'})

                # Eje vertical central de la columna (linetype CENTER)
                cx_alz = AX0 + ALZ_WDRAW / 2
                msp.add_line(
                    (cx_alz, AY0 - 0.5),
                    (cx_alz, AY0 + ALZ_HDRAW + 0.5),
                    dxfattribs={'layer': 'EJES', 'linetype': 'DASHDOT'})

                # Contorno columna alzado
                if es_circular:
                    msp.add_lwpolyline(
                        [(AX0, AY0), (AX0 + ALZ_WDRAW, AY0),
                         (AX0 + ALZ_WDRAW, AY0 + ALZ_HDRAW),
                         (AX0, AY0 + ALZ_HDRAW), (AX0, AY0)],
                        dxfattribs={'layer': 'CONCRETO'})
                else:
                    msp.add_lwpolyline(
                        [(AX0, AY0), (AX0 + ALZ_WDRAW, AY0),
                         (AX0 + ALZ_WDRAW, AY0 + ALZ_HDRAW),
                         (AX0, AY0 + ALZ_HDRAW), (AX0, AY0)],
                        dxfattribs={'layer': 'CONCRETO'})

                # Lineas de corte en nodos
                ext = 0.5
                msp.add_line((AX0 - ext, AY0), (AX0 + ALZ_WDRAW + ext, AY0), dxfattribs={'layer': 'CONCRETO'})
                msp.add_line((AX0 - ext, AY0 + ALZ_HDRAW), (AX0 + ALZ_WDRAW + ext, AY0 + ALZ_HDRAW), dxfattribs={'layer': 'CONCRETO'})

                # Barras longitudinales (alzado) - una por cara visible
                rec_s = recub_cm * ESCALA
                db_s  = rebar_diam * ESCALA / 20  # radio barra en plano
                for xb in [AX0 + rec_s, AX0 + ALZ_WDRAW - rec_s]:
                    msp.add_line(
                        (xb, AY0),
                        (xb, AY0 + ALZ_HDRAW),
                        dxfattribs={'layer': 'ACERO_LONG', 'color': _color_acero_dxf_col(rebar_diam)})

                # Estribos (alzado) - distribucion real
                y_curr = 5.0
                while y_curr <= L_col - 5.0:
                    in_conf = (y_curr <= Lo_conf) or (y_curr >= L_col - Lo_conf)
                    sep = s_conf if in_conf else s_basico
                    ye = AY0 + y_curr * ESCALA
                    lw_estribo = 35 if in_conf else 25
                    msp.add_line(
                        (AX0 + rec_s, ye),
                        (AX0 + ALZ_WDRAW - rec_s, ye),
                        dxfattribs={'layer': 'ACERO_TRANS', 'color': _color_acero_dxf_col(stirrup_diam)})
                    y_curr += sep

                # Cotas alzado - L total
                cx_cota = AX0 - 1.4
                msp.add_line((cx_cota, AY0), (cx_cota, AY0 + ALZ_HDRAW), dxfattribs={'layer': 'COTAS'})
                for yy in [AY0, AY0 + ALZ_HDRAW]:
                    msp.add_line((AX0, yy), (cx_cota - 0.2, yy), dxfattribs={'layer': 'COTAS'})
                msp.add_text(f"L = {L_col:.0f} cm",
                    dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.22,
                                'insert': (cx_cota - 0.15, AY0 + ALZ_HDRAW / 2),
                                'align_point': (cx_cota - 0.15, AY0 + ALZ_HDRAW / 2),
                                'halign': 1, 'valign': 2, 'rotation': 90})

                # Cota zona confinamiento
                if Lo_conf > 0:
                    cxr = AX0 + ALZ_WDRAW + 1.2
                    for (y_ini, y_fin, txt) in [
                        (AY0, AY0 + Lo_conf * ESCALA, f"Lo={Lo_conf:.0f}cm"),
                        (AY0 + (L_col - Lo_conf) * ESCALA, AY0 + ALZ_HDRAW, f"Lo={Lo_conf:.0f}cm")
                    ]:
                        msp.add_line((cxr, y_ini), (cxr, y_fin), dxfattribs={'layer': 'COTAS'})
                        for yy in [y_ini, y_fin]:
                            msp.add_line((AX0 + ALZ_WDRAW, yy), (cxr + 0.2, yy), dxfattribs={'layer': 'COTAS'})
                        msp.add_text(txt,
                            dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF),
                                        'insert': (cxr + 0.15, (y_ini + y_fin) / 2),
                                        'align_point': (cxr + 0.15, (y_ini + y_fin) / 2),
                                        'halign': 1, 'valign': 2, 'rotation': -90})

                # Etiqueta zona conf / zona basica
                yz_mid = AY0 + Lo_conf * ESCALA + (L_col * ESCALA - 2 * Lo_conf * ESCALA) / 2
                msp.add_text(f"s={s_basico:.0f}cm",
                    dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.22,
                                'insert': (AX0 + ALZ_WDRAW / 2, yz_mid)})

                # ── ZONA SECCION TRANSVERSAL (centro) ───────────────────────
                SEC_X0 = MARGEN + ALZ_W + 0.5
                SEC_Y0 = AY0
                SEC_AVAILABLE_W = AREA_W * 0.30
                SEC_AVAILABLE_H = AREA_H * 0.55

                dim_b = D if es_circular else b
                dim_h = D if es_circular else h
                # Escala correcta para que la seccion entre en SEC_AVAILABLE
                escala_sec = min((SEC_AVAILABLE_W - 1.0) / dim_b, (SEC_AVAILABLE_H - 2.0) / dim_h)
                escala_sec = min(escala_sec, 1.0 / 5)  # max 1:5
                escala_sec_int = max(5, int(round(1/escala_sec)))
                sec_w = dim_b * escala_sec
                sec_h = dim_h * escala_sec
                # Centrado dentro de la zona asignada a la seccion
                ox = SEC_X0 + (SEC_AVAILABLE_W - sec_w) / 2
                oy = SEC_Y0 + (SEC_AVAILABLE_H - sec_h) / 2

                # Titulo seccion
                msp.add_text("SECCION TRANSVERSAL",
                    dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.28 * max(0.6, K_DXF),
                                'insert': (ox + sec_w / 2, oy + sec_h + 1.0),
                                'align_point': (ox + sec_w / 2, oy + sec_h + 1.0),
                                'halign': 1, 'valign': 2})
                msp.add_text(f"(ESCALA 1: {escala_sec_int})",
                    dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.22,
                                'insert': (ox + sec_w / 2, oy + sec_h + 0.65),
                                'align_point': (ox + sec_w / 2, oy + sec_h + 0.65),
                                'halign': 1, 'valign': 2})

                if es_circular:
                    cxc = ox + sec_w / 2
                    cyc = oy + sec_h / 2
                    msp.add_circle((cxc, cyc), D / 2 * escala_sec, dxfattribs={'layer': 'CONCRETO'})
                    r_esp = (D / 2 - recub_cm) * escala_sec
                    msp.add_circle((cxc, cyc), r_esp, dxfattribs={'layer': 'ACERO_TRANS', 'color': _color_acero_dxf_col(stirrup_diam)})
                    r_bar = rebar_diam / 20 * escala_sec
                    for ang in np.linspace(0, 2 * math.pi, n_barras, endpoint=False):
                        xb_c = cxc + (D / 2 - d_prime) * escala_sec * math.cos(ang)
                        yb_c = cyc + (D / 2 - d_prime) * escala_sec * math.sin(ang)
                        # HATCH sólido NSR-10 / ICONTEC (no círculo vacío)
                        _hatch_c = msp.add_hatch(color=_color_acero_dxf_col(rebar_diam), dxfattribs={'layer': 'ACERO_LONG'})
                        _hatch_c.set_solid_fill()
                        _ep_c = _hatch_c.paths.add_edge_path()
                        _ep_c.add_arc((xb_c, yb_c), r_bar, 0, 360)
                        hatch = msp.add_hatch(color=_color_acero_dxf_col(rebar_diam))
                        hatch.paths.add_edge_path().add_ellipse((xb_c, yb_c), major_axis=(r_bar, 0), ratio=1.0)
                else:
                    # Contorno seccion
                    msp.add_lwpolyline(
                        [(ox, oy), (ox + sec_w, oy), (ox + sec_w, oy + sec_h), (ox, oy + sec_h), (ox, oy)],
                        dxfattribs={'layer': 'CONCRETO'})

                    # Estribo con esquinas redondeadas y dos ganchos 135° en esquina SUP-IZQ
                    # NSR-10 C.7.1.4 / ACI 318-19 25.3.4 — gancho sísmico 135°, ext. 6db al núcleo
                    re_s  = recub_cm * escala_sec
                    r_bar = rebar_diam / 20 * escala_sec
                    dp_s  = d_prime * escala_sec
                    xm, xM = ox + re_s, ox + sec_w - re_s
                    ym, yM = oy + re_s, oy + sec_h - re_s
                    bw_e  = xM - xm    # ancho estribo escalado
                    hw_e  = yM - ym    # alto estribo escalado
                    # Radio doblez = 3db (NSR-10 C.7.2)
                    _rd = max(min(3.0*stirrup_diam/10.0*escala_sec, bw_e*0.12, hw_e*0.12), 0.03)
                    # Longitud gancho: 6db (NSR-10 C.7.1.4 sismo)
                    L_gancho = max(6.0*stirrup_diam/10.0*escala_sec, _rd*1.2)
                    _n = 8  # puntos por arco de 90°

                    def _adxf(cx, cy, rad, a0, a1):
                        return [(cx+rad*math.cos(math.radians(a0+(a1-a0)*_ii/_n)),
                                 cy+rad*math.sin(math.radians(a0+(a1-a0)*_ii/_n)))
                                for _ii in range(_n+1)]

                    # Perímetro: arranca en (xm, yM-_rd) = pie del arco sup-izq
                    _pe = []
                    _pe.append((xm, yM-_rd))                          # inicio lado izq
                    _pe += _adxf(xm+_rd, ym+_rd, _rd, 180, 270)      # arco inf-izq
                    _pe.append((xM-_rd, ym))                          # lado inf
                    _pe += _adxf(xM-_rd, ym+_rd, _rd, 270, 360)      # arco inf-der
                    _pe.append((xM, yM-_rd))                          # lado der
                    _pe += _adxf(xM-_rd, yM-_rd, _rd, 0,   90)       # arco sup-der
                    _pe.append((xm+_rd, yM))                          # lado sup
                    _pe += _adxf(xm+_rd, yM-_rd, _rd, 90, 180)       # arco sup-izq
                    _pe.append((xm, yM-_rd))                          # cierra
                    msp.add_lwpolyline(_pe, dxfattribs={'layer': 'ACERO_TRANS',
                                       'color': _color_acero_dxf_col(stirrup_diam)})

                    # Ganchos 135°: dirección (+X, -Y) = hacia núcleo desde esquina sup-izq
                    _dk = L_gancho * math.cos(math.radians(45))       # componente = mismo en X e Y
                    # Gancho 1: desde (xm, yM-_rd) — pie del arco sup-izq en lado IZQUIERDO
                    msp.add_line((xm, yM-_rd), (xm+_dk, yM-_rd-_dk),
                                 dxfattribs={'layer':'ACERO_TRANS','color':_color_acero_dxf_col(stirrup_diam)})
                    # Gancho 2: desde (xm+_rd, yM) — inicio del lado SUPERIOR
                    msp.add_line((xm+_rd, yM), (xm+_rd+_dk, yM-_dk),
                                 dxfattribs={'layer':'ACERO_TRANS','color':_color_acero_dxf_col(stirrup_diam)})

                    # Barras en esquinas y caras
                    cxm, cxM = ox + dp_s, ox + sec_w - dp_s
                    cym, cyM = oy + dp_s, oy + sec_h - dp_s
                    xs_bar = np.linspace(cxm, cxM, num_filas_h) if num_filas_h > 1 else [ox + sec_w / 2]
                    ys_bar = np.linspace(cym, cyM, num_filas_v) if num_filas_v > 1 else [oy + sec_h / 2]
                    for xb in xs_bar:
                        for yb in [cym, cyM]:
                            # HATCH sólido Color 7 — ICONTEC 2289 (sin círculo vacío)
                            _h1 = msp.add_hatch(color=_color_acero_dxf_col(rebar_diam), dxfattribs={'layer': 'ACERO_LONG'})
                            _h1.set_solid_fill()
                            _h1.paths.add_edge_path().add_ellipse((xb, yb), major_axis=(r_bar, 0), ratio=1.0)
                    for yb in ys_bar[1:-1]:
                        for xb in [cxm, cxM]:
                            # HATCH sólido Color 7 — ICONTEC 2289
                            _h2 = msp.add_hatch(color=_color_acero_dxf_col(rebar_diam), dxfattribs={'layer': 'ACERO_LONG'})
                            _h2.set_solid_fill()
                            _h2.paths.add_edge_path().add_ellipse((xb, yb), major_axis=(r_bar, 0), ratio=1.0)

                    # Grapas interiores si > 2 filas
                    if num_filas_h > 2:
                        for xb in xs_bar[1:-1]:
                            pts_g = [(xb - L_gancho * 0.5, yM - L_gancho * 0.5), (xb, yM), (xb, ym), (xb + L_gancho * 0.5, ym + L_gancho * 0.5)]
                            msp.add_lwpolyline(pts_g, dxfattribs={'layer': 'ACERO_TRANS', 'color': _color_acero_dxf_col(stirrup_diam)})

                    # Cotas seccion
                    yc_dim = oy - 0.7
                    msp.add_line((ox, yc_dim), (ox + sec_w, yc_dim), dxfattribs={'layer': 'COTAS'})
                    for xx in [ox, ox + sec_w]:
                        msp.add_line((xx, oy), (xx, yc_dim - 0.2), dxfattribs={'layer': 'COTAS'})
                    msp.add_text(f"b = {b:.0f} cm",
                        dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.22,
                                    'insert': (ox + sec_w / 2, yc_dim - 0.25),
                                    'align_point': (ox + sec_w / 2, yc_dim - 0.25),
                                    'halign': 1, 'valign': 2})

                    xc_dim = ox + sec_w + 0.7
                    msp.add_line((xc_dim, oy), (xc_dim, oy + sec_h), dxfattribs={'layer': 'COTAS'})
                    for yy in [oy, oy + sec_h]:
                        msp.add_line((ox + sec_w, yy), (xc_dim + 0.2, yy), dxfattribs={'layer': 'COTAS'})
                    msp.add_text(f"h = {h:.0f} cm",
                        dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.22,
                                    'insert': (xc_dim + 0.15, oy + sec_h / 2),
                                    'align_point': (xc_dim + 0.15, oy + sec_h / 2),
                                    'halign': 1, 'valign': 2, 'rotation': 90})

                    # Recubrimiento con flecha
                    # Texto recubrimiento FUERA de la sección (abajo-izquierda con offset)
                    _txt_h_rec = 0.18 * max(0.5, K_DXF)
                    msp.add_text(f"rec. = {recub_cm:.0f} cm",
                        dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': _txt_h_rec,
                                    'insert': (ox + re_s, oy - _txt_h_rec * 3.0)})

                # ── TABLA DE DESPIECE (zona derecha DENTRO de Carta) ─────────────
                # Carta: 21.6cm ancho. Margen derecho: 20.6cm. Alzado+Sec ocupa ~13cm.
                TAB_X0 = SEC_X0 + SEC_AVAILABLE_W + 0.3
                # Clamp: si la tabla no cabe a la derecha, colocar debajo de la sección
                TAB_MAX_W = (ANCHO_PLANO - MARGEN - TAB_X0)
                if TAB_MAX_W < 4.0:  # mínimo 4cm para tabla legible
                    TAB_X0 = MARGEN
                    TAB_Y0_OVERRIDE = oy - 2.0  # debajo del alzado
                    TAB_MAX_W = ANCHO_PLANO - 2 * MARGEN
                else:
                    TAB_Y0_OVERRIDE = None
                # Columnas: Marca(1.4) Diam(1.6) Cant(0.9) L(1.0) Forma(2.0) Peso(1.1) = 8.0cm
                # Ajustar proporcionalmente si no caben
                _cws_base = [1.4, 1.6, 0.9, 1.0, 2.0, 1.1]
                _scale_w = min(1.0, TAB_MAX_W / sum(_cws_base))
                COL_WS = [w * _scale_w for w in _cws_base]
                TAB_TW = sum(COL_WS)  # Ancho total de la tabla
                ROW_H  = 0.42
                K_DXF = min(1.0, ANCHO_PLANO / 50.0)  # Restaurar escala real
                # Tabla empieza en la parte superior de la zona de dibujo
                TAB_Y0 = AY0 + AREA_H - 0.5
                HEADERS = ["MARCA", "DIAMETRO", "CANT.", "L (m)", "FORMA", "PESO kg"]

                # Calcular datos barras
                if es_circular:
                    _lb  = (L_col + 2 * (ld_mm / 10) + 2 * (12 * rebar_diam / 10)) / 100
                    _pw  = n_barras * _lb * (rebar_area * 100) * 7.85e-3
                    _lt  = long_espiral_total / 100
                    _pt  = peso_total_estribos_kg
                    barras_despiece = [
                        ("L1 - Long.", _bar_label(rebar_diam), str(n_barras),
                         f"{_lb:.2f}", "Recta + gancho sup.", f"{_pw:.1f}"),
                        ("E1 - Espiral", _bar_label(stirrup_diam), "1 esp.",
                         f"{_lt:.2f}", "Espiral continuaa", f"{_pt:.1f}"),
                    ]
                else:
                    _lb  = (L_col + 2 * (ld_mm / 10) + 2 * (12 * rebar_diam / 10)) / 100
                    _pw  = n_barras_total * _lb * (rebar_area * 100) * 7.85e-3
                    _le  = perim_estribo / 100 + 2 * (13 * stirrup_diam / 10) / 100  # incluye ganchos 135
                    _pt  = peso_total_estribos_kg
                    barras_despiece = [
                        ("L1 - Long.", _bar_label(rebar_diam), str(n_barras_total),
                         f"{_lb:.2f}", "Recta + gan.180 inf.", f"{_pw:.1f}"),
                        ("E1 - Estribo", _bar_label(stirrup_diam), str(n_estribos_total),
                         f"{_le:.2f}", "Cerrado 135 (sism.)", f"{_pt:.1f}"),
                    ]

                def draw_despiece_table(x0, y_top):
                    TH = 0.16  # Altura texto tabla (pequeño para no desbordarse)
                    # Titulo
                    msp.add_text("DESPIECE DE ACERO - ICONTEC 2289",
                        dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.22,
                                    'insert': (x0 + TAB_TW / 2, y_top + 0.25),
                                    'align_point': (x0 + TAB_TW / 2, y_top + 0.25),
                                    'halign': 1, 'valign': 2})
                    # Header row
                    y = y_top
                    cx = x0
                    for hdr, cw in zip(HEADERS, COL_WS):
                        msp.add_lwpolyline(
                            [(cx, y - ROW_H), (cx + cw, y - ROW_H),
                             (cx + cw, y), (cx, y), (cx, y - ROW_H)],
                            dxfattribs={'layer': 'ROTULO'})
                        msp.add_text(hdr,
                            dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': TH,
                                        'insert': (cx + cw / 2, y - ROW_H / 2),
                                        'align_point': (cx + cw / 2, y - ROW_H / 2),
                                        'halign': 1, 'valign': 2})
                        cx += cw
                    y -= ROW_H
                    # Data rows
                    for row in barras_despiece:
                        cx = x0
                        for val, cw in zip(row, COL_WS):
                            msp.add_lwpolyline(
                                [(cx, y - ROW_H), (cx + cw, y - ROW_H),
                                 (cx + cw, y), (cx, y), (cx, y - ROW_H)],
                                dxfattribs={'layer': 'ROTULO'})
                            # Truncar texto al ancho de columna (aprox 8 chars por cm)
                            max_chars = max(4, int(cw * 7))
                            txt_disp = str(val)[:max_chars]
                            msp.add_text(txt_disp,
                                dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': TH,
                                            'insert': (cx + 0.05, y - ROW_H / 2),
                                            'align_point': (cx + 0.05, y - ROW_H / 2),
                                            'halign': 0, 'valign': 2})
                            cx += cw
                        y -= ROW_H
                    # Totales
                    _tot_acero = _pw + _pt
                    cx = x0
                    totales = [("TOTAL ACERO", "", "", "", "", f"{_tot_acero:.1f} kg"),
                               ("CONCRETO", f"f'c={fc:.0f}MPa", f"{vol_concreto_m3:.3f}m3", "", "", "")]
                    for tot in totales:
                        for val, cw in zip(tot, COL_WS):
                            msp.add_lwpolyline(
                                [(cx, y - ROW_H), (cx + cw, y - ROW_H),
                                 (cx + cw, y), (cx, y), (cx, y - ROW_H)],
                                dxfattribs={'layer': 'ROTULO'})
                            msp.add_text(str(val)[:max(4,int(cw*7))],
                                dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': TH,
                                            'insert': (cx + 0.05, y - ROW_H / 2),
                                            'align_point': (cx + 0.05, y - ROW_H / 2),
                                            'halign': 0, 'valign': 2})
                            cx += cw
                        cx = x0
                        y -= ROW_H
                    return y  # y final de la tabla
                    # Totales
                    _tot_acero = _pw + _pt
                    cx = x0
                    totales = [("TOTAL ACERO", "", "", "", "", f"{_tot_acero:.1f} kg"),
                               ("CONCRETO", f"f'c={fc:.0f}MPa", f"{vol_concreto_m3:.3f}m3", "", "", "")]
                    for tot in totales:
                        for val, cw in zip(tot, COL_WS):
                            msp.add_lwpolyline(
                                [(cx, y - ROW_H), (cx + cw, y - ROW_H),
                                 (cx + cw, y), (cx, y), (cx, y - ROW_H)],
                                dxfattribs={'layer': 'ROTULO'})
                            msp.add_text(val,
                                dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF),
                                            'insert': (cx + cw / 2, y - ROW_H / 2),
                                            'align_point': (cx + cw / 2, y - ROW_H / 2),
                                            'halign': 1, 'valign': 2})
                            cx += cw
                        cx = x0
                        y -= ROW_H
                    return y  # y final de la tabla

                y_after_table = draw_despiece_table(TAB_X0, TAB_Y0)

                # ── DIAGRAMA DE GANCHOS (DOBLECES) ──────────────────────────
                # Dibuja el esquema de cada tipo de gancho a escala 1:5
                ESCALA_DOBL = 1 / 5
                DOBL_X = TAB_X0
                DOBL_Y = y_after_table - 1.5
                db_dobl = stirrup_diam  # mm

                # Gancho 135 grados (sismico - estribo)
                r_dobl = 3 * db_dobl / 10 * ESCALA_DOBL  # radio doblez = 3db (no confinado)
                ext_gancho = 6 * db_dobl / 10 * ESCALA_DOBL  # extension libre 6db
                msp.add_text("Gancho 135 sismic. (estrib.)",
                    dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF),
                                'insert': (DOBL_X, DOBL_Y)})
                # Trazo simplificado del gancho 135
                pts_g135 = [
                    (DOBL_X + 0.2, DOBL_Y - 0.5),
                    (DOBL_X + 0.2, DOBL_Y - 1.2),
                    (DOBL_X + 0.2 + ext_gancho * 1.4, DOBL_Y - 1.2 + ext_gancho * 1.4)
                ]
                msp.add_lwpolyline(pts_g135, dxfattribs={'layer': 'DOBLEZ'})
                msp.add_text(f"ext.={6*stirrup_diam:.0f}mm (6db)",
                    dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.18,
                                'insert': (DOBL_X + 0.8, DOBL_Y - 0.7)})

                DOBL_X2 = DOBL_X + TAB_TW * 0.5
                # --- NUEVA TABLA EMPALMES Y MATERIALES (DXF) ---
                Y_MAT = DOBL_Y - 2.5
                msp.add_text("TABLA DE EMPALMES (A TENSION) Ld", dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.25 * max(0.6, K_DXF), 'insert': (DOBL_X, Y_MAT)})
                _ld_cm = (1.3 * 0.02 * 420) / (21**0.5) * rebar_diam / 10
                msp.add_text(f"Varilla principal ({_bar_label(rebar_diam)}): Ld = {_ld_cm:.0f} cm", dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF), 'insert': (DOBL_X, Y_MAT - 0.4)})
                
                Y_MAT -= 1.2
                msp.add_text(f"DOSIFICACION m3 CONCRETO (f'c={fc:.0f}MPa)", dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.25 * max(0.6, K_DXF), 'insert': (DOBL_X, Y_MAT)})
                if fc >= 21:
                    _cem, _are, _gra, _agu = 350, 0.56, 0.84, 180
                    _txt_mat = f"Cemento: {_cem} kg (7 sacos) | Arena: {_are} m3 | Grava: {_gra} m3 | Agua: {_agu} L"
                    msp.add_text(_txt_mat, dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF), 'insert': (DOBL_X, Y_MAT - 0.4)})
                    
                    Y_MAT -= 0.8
                    msp.add_text(f"TOTALES PARA ESTA COLUMNA ({vol_concreto_m3:.2f} m3):", dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF), 'insert': (DOBL_X, Y_MAT)})
                    _txt_tot = f"Cemento: {_cem*vol_concreto_m3:.0f}kg | Are: {_are*vol_concreto_m3:.2f}m3 | Gra: {_gra*vol_concreto_m3:.2f}m3 | Ag: {_agu*vol_concreto_m3:.0f}L"
                    msp.add_text(_txt_tot, dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF), 'insert': (DOBL_X, Y_MAT - 0.3)})
                else:
                    msp.add_text("Requiere diseno de mezcla.", dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF), 'insert': (DOBL_X, Y_MAT - 0.4)})

                # Gancho 180 (barra longitudinal)
                db_long = rebar_diam
                msp.add_text("Gancho 180 (barra long.)",
                    dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF),
                                'insert': (DOBL_X2, DOBL_Y)})
                pts_g180 = [
                    (DOBL_X2 + 0.2, DOBL_Y - 0.3),
                    (DOBL_X2 + 0.2, DOBL_Y - 1.0),
                    (DOBL_X2 + 0.2 + 4 * db_long / 10 * ESCALA_DOBL, DOBL_Y - 1.0),
                    (DOBL_X2 + 0.2 + 4 * db_long / 10 * ESCALA_DOBL, DOBL_Y - 0.7)
                ]
                msp.add_lwpolyline(pts_g180, dxfattribs={'layer': 'DOBLEZ'})
                msp.add_text(f"ext.={4*rebar_diam:.0f}mm (4db)",
                    dxfattribs={'layer': 'COTAS', 'style': 'ROMANS', 'height': 0.18,
                                'insert': (DOBL_X2 + 0.5, DOBL_Y - 0.7)})

                # ── CUADRO VERIFICACIONES (debajo del dibujo alzado) ───────
                # ── CUADRO VERIFICACIONES (debajo de la seccion, zona derecha) ──
                VER_X = TAB_X0  # Mismo X que la tabla de despiece
                # Posicionar BAJO el cuadro de doblez/dosificacion
                VER_Y = AY0 + (AREA_H * 0.35)  # en la zona media-inferior del papel
                ver_rows = []
                if not es_circular:
                    ver_rows = [
                        ("Seccion", f"{b:.0f} x {h:.0f} cm", 7),
                        (f"f'c / fy", f"{fc:.0f} / {fy:.0f} MPa", 7),
                        ("Armado", f"{n_barras_total} {_bar_label(rebar_diam)}", 7),
                        ("Ast / rho", f"{Ast:.2f} cm2 / {cuantia:.2f}%", 7),
                        ("Estribo", f"{_bar_label(stirrup_diam)} c/{s_conf:.0f}cm conf.", 7),
                        ("",        f"c/{s_basico:.0f}cm zona media", 7),
                        ("Ash req/prov", f"{Ash_req:.2f}/{Ash_prov:.2f} cm2", 3 if ash_ok else 1),
                        ("Ash",     "CUMPLE" if ash_ok else "NO CUMPLE", 3 if ash_ok else 1),
                        ("Biaxial Pu/Pni", f"{bresler['ratio']:.3f}", 3 if bresler['ok'] else 1),
                        ("Verificacion", "CUMPLE" if bresler['ok'] else "NO CUMPLE", 3 if bresler['ok'] else 1),
                    ]
                else:
                    ver_rows = [
                        ("Seccion", f"Circ. D={D:.0f} cm", 7),
                        (f"f'c / fy", f"{fc:.0f} / {fy:.0f} MPa", 7),
                        ("Armado", f"{n_barras} {_bar_label(rebar_diam)}", 7),
                        ("Ast / rho", f"{Ast:.2f} cm2 / {cuantia:.2f}%", 7),
                        ("Espiral", f"{_bar_label(stirrup_diam)} paso={paso_espiral:.0f}cm", 7),
                        ("rho_s req/prov", f"{rho_s_req:.4f}/{rho_s_prov:.4f}", 3 if ash_ok else 1),
                        ("Espiral", "CUMPLE" if ash_ok else "NO CUMPLE", 3 if ash_ok else 1),
                        ("Biaxial Pu/Pni", f"{bresler['ratio']:.3f}", 3 if bresler['ok'] else 1),
                        ("Verificacion", "CUMPLE" if bresler['ok'] else "NO CUMPLE", 3 if bresler['ok'] else 1),
                    ]

                msp.add_text("VERIFICACIONES NSR-10 / ACI 318",
                    dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.26,
                                'insert': (VER_X, VER_Y), 'color': 7})
                for i, (lbl, val, col) in enumerate(ver_rows):
                    y_row = VER_Y - 0.5 - i * 0.48
                    if lbl:
                        msp.add_text(f"{lbl}:",
                            dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.20 * max(0.6, K_DXF),
                                        'insert': (VER_X, y_row), 'color': 7})
                    msp.add_text(val,
                        dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.20,
                                    'insert': (VER_X + TAB_TW * 0.42, y_row), 'color': col})

                # ── ROTULO ICONTEC (inferior) ────────────────────────────────
                ROT_X = MARGEN
                ROT_Y = MARGEN
                # Marco exterior rotulo
                msp.add_lwpolyline(
                    [(ROT_X, ROT_Y), (ROT_X + ROT_W, ROT_Y),
                     (ROT_X + ROT_W, ROT_Y + ROT_H),
                     (ROT_X, ROT_Y + ROT_H), (ROT_X, ROT_Y)],
                    dxfattribs={'layer': 'ROTULO'})

                # Definicion de celdas del rotulo
                _sello_sismico = "DISIPACIÓN: " + nivel_sismico
                celdas_rot = [
                    # (etiqueta, valor, x_rel, y_rel, cw, ch)
                    ("EMPRESA",  dxf_empresa,  0.0,   2.5, ROT_W * 0.48, 1.0),
                    ("SISMO",    _sello_sismico, 0.0, 3.5, ROT_W, 0.5), # Sello visual superpuesto superior
                    ("PROYECTO", dxf_proyecto, 0.0,   1.5, ROT_W * 0.48, 1.0),
                    ("CONTENIDO", f"Columna {'Circ.' if es_circular else 'Rect.'} — Despiece", 0.0, 0.5, ROT_W * 0.48, 1.0),
                    ("N. PLANO",  dxf_plano,   ROT_W * 0.48, 2.5, ROT_W * 0.18, 1.0),
                    ("ESCALA",   ESCALA_LABEL, ROT_W * 0.48, 1.5, ROT_W * 0.18, 1.0),
                    ("FECHA",    datetime.datetime.now().strftime("%d/%m/%Y"), ROT_W * 0.48, 0.5, ROT_W * 0.18, 1.0),
                    ("REVISION", "0",          ROT_W * 0.66, 2.5, ROT_W * 0.12, 1.0),
                    ("HOJA",     "1/1",        ROT_W * 0.66, 1.5, ROT_W * 0.12, 1.0),
                    ("PAPEL",    PAPEL_LABEL,  ROT_W * 0.66, 0.5, ROT_W * 0.12, 1.0),
                    ("ELABORO",  dxf_elaboro,  ROT_W * 0.78, 2.5, ROT_W * 0.073, 1.0),
                    ("REVISO",   dxf_reviso,   ROT_W * 0.853, 2.5, ROT_W * 0.073, 1.0),
                    ("APROBO",   dxf_aprobo,   ROT_W * 0.927, 2.5, ROT_W * 0.073, 1.0),
                    ("ACERO kg", f"{peso_total_acero_kg:.1f}", ROT_W * 0.78, 1.0, ROT_W * 0.11, 1.5),
                    ("CONC. m3", f"{vol_concreto_m3:.3f}",    ROT_W * 0.89, 1.0, ROT_W * 0.11, 1.5),
                ]
                for etiq, valor, xr, yr, cw, ch in celdas_rot:
                    cx2 = ROT_X + xr
                    cy2 = ROT_Y + yr
                    msp.add_lwpolyline(
                        [(cx2, cy2), (cx2 + cw, cy2), (cx2 + cw, cy2 + ch),
                         (cx2, cy2 + ch), (cx2, cy2)],
                        dxfattribs={'layer': 'ROTULO'})
                    msp.add_text(etiq,
                        dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS', 'height': 0.14,
                                    'insert': (cx2 + 0.08, cy2 + ch - 0.18), 'color': 7})
                    msp.add_text(valor,
                        dxfattribs={'layer': 'TEXTO', 'style': 'ROMANS',
                                    'height': 0.30 if etiq in ("EMPRESA", "PROYECTO") else 0.22,
                                    'insert': (cx2 + cw / 2, cy2 + ch / 2 - 0.1),
                                    'align_point': (cx2 + cw / 2, cy2 + ch / 2 - 0.1),
                                    'halign': 1, 'valign': 2})

                # Linea divisoria sobre el rotulo
                msp.add_line(
                    (MARGEN, ROT_H + MARGEN),
                    (ANCHO_PLANO - MARGEN, ROT_H + MARGEN),
                    dxfattribs={'layer': 'MARGEN'})

                # ── EXPORTAR DXF ────────────────────────────────────────────
                import tempfile, os as _os
                with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp:
                    tmp_path = tmp.name
                doc_dxf.saveas(tmp_path)
                with open(tmp_path, 'rb') as f_tmp:
                    dxf_bytes = f_tmp.read()
                _os.unlink(tmp_path)

                nombre_dxf = f"Columna_{'Circ' if es_circular else f'{b:.0f}x{h:.0f}'}_{PAPEL_LABEL.replace(' ','_')}.dxf"
                st.download_button(
                    label=_t("Descargar DXF ICONTEC", "Download DXF ICONTEC"),
                    data=dxf_bytes,
                    file_name=nombre_dxf,
                    mime="application/dxf",
                    key="col_dxf_dl")

                # ── EXPORTAR PDF (renderizado) ───────────────────────────────
                try:
                    import matplotlib
                    matplotlib.use('Agg')
                    import matplotlib.pyplot as _mpdf
                    from ezdxf.addons.drawing import RenderContext, Frontend
                    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
                    # Tamano en pulgadas (1 cm = 0.3937 inch)
                    fig_w = ANCHO_PLANO * 0.3937
                    fig_h = ALTO_PLANO  * 0.3937
                    fig_pdf, ax_pdf = _mpdf.subplots(figsize=(fig_w, fig_h))
                    fig_pdf.patch.set_facecolor('white')
                    ax_pdf.set_facecolor('white')
                    _ctx     = RenderContext(doc_dxf)
                    _backend = MatplotlibBackend(ax_pdf)
                    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
                    _config = Configuration.defaults().with_changes(background_policy=BackgroundPolicy.WHITE)
                    Frontend(_ctx, _backend, config=_config).draw_layout(msp, finalize=True)
                    ax_pdf.set_aspect('equal')
                    ax_pdf.axis('off')
                    # Límites reales del DXF: la hoja Carta está centrada en (108, 140)
                    _cx = ANCHO_PLANO / 2  # = 108.0 para Carta
                    _cy = ALTO_PLANO  / 2  # = 140.0 para Carta
                    ax_pdf.set_xlim(_cx - ANCHO_PLANO/2 - 0.5, _cx + ANCHO_PLANO/2 + 0.5)
                    ax_pdf.set_ylim(_cy - ALTO_PLANO /2 - 0.5, _cy + ALTO_PLANO /2 + 0.5)
                    bio_pdf_col = io.BytesIO()
                    fig_pdf.savefig(bio_pdf_col, format='pdf', bbox_inches='tight',dpi=200, facecolor='white', pad_inches=0.05)
                    bio_pdf_col.seek(0)
                    _mpdf.close(fig_pdf)
                    nombre_pdf = nombre_dxf.replace('.dxf', '.pdf')
                    st.download_button(
                        label=_t("Descargar PDF Imprimible", "Download Printable PDF"),
                        data=bio_pdf_col.getvalue(),
                        file_name=nombre_pdf,
                        mime="application/pdf",
                        key="col_pdf_dl")
                    st.success(_t(
                        f"Plano generado | Papel: {PAPEL_LABEL} | Escala: {ESCALA_LABEL} | Lineweights ICONTEC aplicados",
                        f"Plot generated | Paper: {PAPEL_LABEL} | Scale: {ESCALA_LABEL} | ICONTEC lineweights applied"))
                except Exception as e_pdf:
                    st.warning(f"PDF no disponible (instalar ezdxf[draw]): {e_pdf}")

            except Exception as e:
                import traceback
                st.error(f"Error al generar DXF: {e}")
                st.code(traceback.format_exc(), language='python')
                st.info("Asegurate de tener instalado ezdxf: pip install ezdxf")








# =============================================================================
# =============================================================================
# TAB 3: CANTIDADES, DESPIECE Y APU
# =============================================================================
# =============================================================================
# TAB 2B: ALZADO DE CONFINAMIENTO + TABLA DE COMBINACIONES DE CARGA
# =============================================================================
with tab2b:
    col_alz, col_combo = st.columns([1, 1], gap="large")

    # ── ALZADO 2D DE CONFINAMIENTO ────────────────────────────────────────────
    with col_alz:
        st.subheader(_t("📐 Alzado de Confinamiento", "📐 Confinement Elevation"))
        s_centro_alz = st.number_input(
            _t("Separación zona central s₂ (cm)", "Central zone spacing s₂ (cm)"),
            5.0, 50.0, float(min(s_conf * 2.0, 30.0)), 1.0, key="s2_alz_col")
        fig_alz = plot_alzado_confinamiento(
            L_col_cm=L_col, Lo_cm=Lo_conf, s_conf_cm=s_conf, s_centro_cm=s_centro_alz,
            b_cm=b if not es_circular else D, h_cm=h if not es_circular else D,
            es_circular=es_circular,
            rebar_diam_mm=rebar_diam, stirrup_diam_mm=stirrup_diam,
            norma_sel=norma_sel, coderef="C.7.7.1")
        st.pyplot(fig_alz); plt.close(fig_alz)
        st.caption(
            f"Lo = {Lo_conf:.0f} cm | s₁ = {s_conf:.0f} cm (confinamiento) | "
            f"s₂ = {s_centro_alz:.0f} cm (zona libre) | Ref: {norma_sel}")

    # ── TABLA DE COMBINACIONES DE CARGA ──────────────────────────────────────
    with col_combo:
        st.subheader(_t("📊 Combinaciones P-M", "📊 P-M Load Combos"))
        st.caption(_t("Ingrese sus combinaciones — el diagrama grafica todos los puntos simultáneamente.",
                      "Enter load combinations — the P-M diagram plots all points simultaneously."))
        _combos_def = pd.DataFrame({
            "Combinacion": ["1.4D", "1.2D+1.6L", "1.2D+1.0L+1.0E", "0.9D+1.0E", "1.2D+1.6L+0.5Lr"],
            "Pu":  [round(Pu_input*0.70,1), round(Pu_input,1), round(Pu_input*0.85,1), round(Pu_input*0.50,1), round(Pu_input*0.95,1)],
            "Mux": [round(abs(Mux_input)*0.50,1), round(abs(Mux_input),1), round(abs(Mux_input)*1.20,1), round(abs(Mux_input)*0.80,1), round(abs(Mux_input)*0.90,1)],
            "Muy": [round(abs(Muy_input)*0.50,1), round(abs(Muy_input),1), round(abs(Muy_input)*1.20,1), round(abs(Muy_input)*0.80,1), round(abs(Muy_input)*0.90,1)],
        })
        df_combos = st.data_editor(
            _combos_def, num_rows="dynamic", use_container_width=True, key="col_combos_pm",
            column_config={
                "Combinacion": st.column_config.TextColumn("Combinación", width="medium"),
                "Pu":  st.column_config.NumberColumn(f"Pu [{unidad_fuerza}]",  min_value=0),
                "Mux": st.column_config.NumberColumn(f"Mux [{unidad_mom}]", min_value=0),
                "Muy": st.column_config.NumberColumn(f"Muy [{unidad_mom}]", min_value=0),
            })
        puntos_combo = parse_combo_table(df_combos, factor_fuerza)
        if puntos_combo and len(cap_x.get('phi_Mn', [])) > 0:
            fig_pm_c = plot_pm_combos(cap_x, Pu_col, Mux_col, puntos_combo,
                                      factor_fuerza, unidad_fuerza, unidad_mom)
            st.pyplot(fig_pm_c); plt.close(fig_pm_c)
            # Tabla de estado por combinación
            try:
                from scipy.interpolate import interp1d as _i1d
                _fi = _i1d(cap_x['phi_Pn'], cap_x['phi_Mn'], kind='linear', fill_value='extrapolate')
                rows_ok = []
                for (pu, mux, muy, lbl) in puntos_combo:
                    phi_at = float(_fi(pu))
                    dentro = abs(mux) <= phi_at
                    rows_ok.append({"Combo": lbl,
                                    f"Pu [{unidad_fuerza}]": f"{pu*factor_fuerza:.1f}",
                                    f"Mux [{unidad_mom}]": f"{abs(mux)*factor_fuerza:.1f}",
                                    "Estado": "✅ Dentro" if dentro else "❌ Fuera"})
                st.dataframe(pd.DataFrame(rows_ok), use_container_width=True, hide_index=True)
                ratios = [(abs(mux)/float(_fi(pu)) if float(_fi(pu))>0 else 999, lbl) for pu,mux,muy,lbl in puntos_combo]
                critica = max(ratios, key=lambda r: r[0])
                msg = f"✅ Todas dentro — combo crítica: `{critica[1]}` (M/φM={critica[0]:.3f})" if critica[0]<=1 else f"⚠️ Combo fuera del diagrama: `{critica[1]}` (M/φM={critica[0]:.3f})"
                (st.success if critica[0]<=1 else st.warning)(msg)
            except Exception:
                pass
        else:
            st.info(_t("Complete la tabla para ver los puntos en el diagrama P-M.",
                       "Fill the table to plot points on the P-M diagram."))

with tab3:
    st.subheader(f"Cantidades de Materiales — {'Circular'if es_circular else 'Rectangular'}, L={L_col:.0f} cm")
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric(_t("Concreto", "Concrete"), f"{vol_concreto_m3:.4f} m³")
    col_c2.metric(_t("Acero Total", "Total Steel"), f"{peso_total_acero_kg:.2f} kg")
    col_c3.metric(_t("Acero Longitudinal", "Long. Steel"), f"{peso_acero_long_kg:.2f} kg")
    col_c4.metric(_t("Acero Estribos", "Tie Steel"), f"{peso_total_estribos_kg:.2f} kg")
    # P-3 Encofrado / P-1 Agua / P-4 Cuantía
    _dim_b = D if es_circular else b
    _dim_h = D if es_circular else h
    _area_enc = (3.14159 * _dim_b / 100) * (L_col / 100) if es_circular else (2 * (_dim_b + _dim_h) / 100) * (L_col / 100)
    _mix_c = get_mix_for_fc(fc)
    _litros_agua = _mix_c.get("agua", 180) * vol_concreto_m3
    _col_e1, _col_e2, _col_e3 = st.columns(3)
    _col_e1.metric(_t("Encofrado", "Formwork"), f"{_area_enc:.2f} m²")
    _col_e2.metric(_t("Agua concreto", "Mixing water"), f"{_litros_agua:.0f} L")
    _col_e3.metric(_t("Cuantía ρ", "Steel ratio ρ"), f"{cuantia:.2f}%")
    st.markdown("---")
    st.subheader(_t("Despiece de Acero", "Bar Bending Schedule"))
    
    if es_circular:
        long_bar = (L_col + 2 * (ld_mm/10) + 2 * (12*rebar_diam/10)) / 100
        peso_long = n_barras * long_bar * (rebar_area * 100) * 7.85e-3
        
        despiece_data = {
            "Marca": ["L1", "E1 (Espiral)"],
            "Cantidad": [n_barras, 1],
            "Diámetro": [_bar_label(rebar_diam), _bar_label(stirrup_diam)],
            "Longitud (m)": [long_bar, long_espiral_total/100],
            "Longitud Total (m)": [n_barras * long_bar, long_espiral_total/100],
            "Peso (kg)": [peso_long, peso_total_estribos_kg]
        }
        long_bar_m = long_bar
    else:
        _tiene_empalme = st.checkbox(_t("Incluir empalme inferior (arranque desde cimentación)", "Include lap splice at base"), value=False, key="col_empalme")
        _long_empalme = (1.3 * ld_mm/10) / 100 if _tiene_empalme else 0.0
        long_bar_m = (L_col + 2 * (ld_mm/10) + 2 * (12*rebar_diam/10)) / 100
        long_bar_arranque = long_bar_m + _long_empalme
        peso_long_total = n_barras_total * long_bar_m * (rebar_area * 100) * 7.85e-3
        
        despiece_data = {
            "Marca": ["L1 (cuerpo)", "L1A (arranque)" , "E1"] if _tiene_empalme else ["L1", "E1"],
            "Cantidad": [n_barras_total, n_estribos_total],
            "Diámetro": [_bar_label(rebar_diam), _bar_label(stirrup_diam)],
            "Longitud (m)": [long_bar_m, perim_estribo/100],
            "Longitud Total (m)": [n_barras_total * long_bar_m, n_estribos_total * perim_estribo/100],
            "Peso (kg)": [peso_long_total, peso_total_estribos_kg]
        }
    
    df_despiece = pd.DataFrame(despiece_data)
    st.dataframe(df_despiece.style.format({"Longitud (m)": "{:.2f}", "Longitud Total (m)": "{:.2f}", "Peso (kg)": "{:.1f}"}), 
                 use_container_width=True)
    
    fig_bars, ax_bars = plt.subplots(figsize=(6, 4))
    fig_bars.patch.set_facecolor('#1e1e2e')
    for _ax in fig_bars.get_axes(): _ax.set_facecolor('#14142a'); _ax.tick_params(colors='#cdd6f4'); _ax.xaxis.label.set_color('#cdd6f4'); _ax.yaxis.label.set_color('#cdd6f4')
    ax_bars.bar(df_despiece["Marca"], df_despiece["Peso (kg)"], color=['#ff6b35', '#4caf50'])
    ax_bars.set_xlabel(_t("Elemento", "Element"))
    ax_bars.set_ylabel(_t("Peso (kg)", "Weight (kg)"))
    ax_bars.set_title(_t("Distribución de pesos", "Weight distribution"))
    ax_bars.grid(True, alpha=0.3)
    st.pyplot(fig_bars)
    
    with st.expander(_t("Dibujo de Figurado para Taller", "Shop Drawing Details"), expanded=False):
        st.markdown(_t("Formas reales de las barras con ganchos y dimensiones.", "Actual bar shapes with hooks and dimensions."))
        hook_len_cm = 12 * rebar_diam / 10
        if es_circular:
            straight_len_cm = long_bar_m * 100 - 2 * hook_len_cm
            fig_l1 = draw_longitudinal_bar(long_bar_m*100, straight_len_cm, hook_len_cm, rebar_diam, _bar_label(rebar_diam))
            st.pyplot(fig_l1)
            fig_spiral = draw_spiral(D, paso_espiral, stirrup_diam, _bar_label(stirrup_diam))
            st.pyplot(fig_spiral)
        else:
            straight_len_cm = long_bar_m * 100 - 2 * hook_len_cm
            fig_l1 = draw_longitudinal_bar(long_bar_m*100, straight_len_cm, hook_len_cm, rebar_diam, _bar_label(rebar_diam))
            st.pyplot(fig_l1)
            inside_b = b - 2 * recub_cm
            inside_h = h - 2 * recub_cm
            hook_len_est = 12 * stirrup_diam / 10
            fig_e1 = draw_stirrup(inside_b, inside_h, hook_len_est, stirrup_diam, _bar_label(stirrup_diam))
            st.pyplot(fig_e1)
    
    with st.expander(_t("Presupuesto APU", "APU Budget"), expanded=False):
        st.markdown(_t("Ingrese precios unitarios para calcular el costo total.", "Enter unit prices to calculate total cost."))
        with st.form(key="col_apu_form"):
            if "col_apu_moneda" not in st.session_state: st.session_state["col_apu_moneda"] = "COP"
            moneda = st.text_input(_t("Moneda", "Currency"), value=st.session_state["col_apu_moneda"])
            col_apu1, col_apu2 = st.columns(2)
            with col_apu1:
                if "col_apu_cemento" not in st.session_state: st.session_state["col_apu_cemento"] = 28000.0
                if "col_apu_acero" not in st.session_state: st.session_state["col_apu_acero"] = 7500.0
                if "col_apu_arena" not in st.session_state: st.session_state["col_apu_arena"] = 120000.0
                if "col_apu_grava" not in st.session_state: st.session_state["col_apu_grava"] = 130000.0
                
                precio_cemento = st.number_input(_t("Precio por bulto cemento", "Price per cement bag"), value=st.session_state["col_apu_cemento"], step=1000.0)
                precio_acero = st.number_input(_t("Precio por kg acero", "Price per kg steel"), value=st.session_state["col_apu_acero"], step=100.0)
                precio_arena = st.number_input(_t("Precio por m³ arena", "Price per m³ sand"), value=st.session_state["col_apu_arena"], step=5000.0)
                precio_grava = st.number_input(_t("Precio por m³ grava", "Price per m³ gravel"), value=st.session_state["col_apu_grava"], step=5000.0)
                if "col_apu_agua" not in st.session_state: st.session_state["col_apu_agua"] = 3500.0
                if "col_apu_encofrado" not in st.session_state: st.session_state["col_apu_encofrado"] = 45000.0
                precio_agua = st.number_input(_t("Precio agua (m³)", "Water price /m³"), value=st.session_state["col_apu_agua"], step=500.0)
                precio_encofrado = st.number_input(_t("Precio encofrado (m²)", "Formwork price /m²"), value=st.session_state["col_apu_encofrado"], step=2000.0)
            with col_apu2:
                if "col_apu_mo" not in st.session_state: st.session_state["col_apu_mo"] = 70000.0
                if "col_apu_aui" not in st.session_state: st.session_state["col_apu_aui"] = 30.0
                
                precio_mo = st.number_input(_t("Costo mano de obra (día)", "Labor cost per day"), value=st.session_state["col_apu_mo"], step=5000.0)
                pct_aui = st.number_input(_t("% A.I.U.", "% A.I.U."), value=st.session_state["col_apu_aui"], step=5.0) / 100.0
            st.markdown("---")
            usar_premezclado = st.checkbox(
                _t("Usar concreto premezclado (omite cemento/arena/grava)", "Use ready-mix concrete (skips cement/sand/gravel)"),
                value=st.session_state.get("col_apu_premix", False), key="col_apu_premix"
            )
            precio_premix_m3 = 0.0
            if usar_premezclado:
                precio_premix_m3 = st.number_input(
                    _t("Precio concreto premezclado / m³", "Ready-mix concrete price / m³"),
                    value=st.session_state.get("col_apu_premix_p", 420000.0),
                    step=10000.0, key="col_apu_premix_p"
                )
            submitted = st.form_submit_button(_t("Calcular Presupuesto", "Calculate Budget"))
            if submitted:
                st.session_state.apu_config = {"moneda": moneda, "cemento": precio_cemento, "acero": precio_acero,
                    "arena": precio_arena, "grava": precio_grava, "costo_dia_mo": precio_mo, "pct_aui": pct_aui,
                    "premix": usar_premezclado, "precio_premix_m3": precio_premix_m3,
                    "agua": precio_agua, "encofrado": precio_encofrado}
                st.success(_t("Precios guardados.", "Prices saved."))
                st.rerun()
        if "col_apu_config" in st.session_state:
            apu = st.session_state.apu_config
            mix = get_mix_for_fc(fc)
            bag_kg = CEMENT_BAGS.get(norma_sel, CEMENT_BAGS["NSR-10 (Colombia)"])[0]["kg"]
            bultos_col = vol_concreto_m3 * mix["cem"] / bag_kg
            _usar_premix = apu.get("premix", False)
            _precio_premix_m3 = apu.get("precio_premix_m3", 0.0)
            if _usar_premix:
                costo_cemento = 0.0
                costo_arena   = 0.0
                costo_grava   = 0.0
                costo_conc_premix = vol_concreto_m3 * _precio_premix_m3
            else:
                costo_cemento = bultos_col * apu["cemento"]
                costo_arena   = (mix["arena"] * vol_concreto_m3 / 1500) * apu["arena"]
                costo_grava   = (mix["grava"] * vol_concreto_m3 / 1600) * apu["grava"]
                costo_conc_premix = 0.0
            costo_acero = peso_total_acero_kg * apu["acero"]
            costo_mo = (peso_total_acero_kg * 0.04 + vol_concreto_m3 * 0.4) * apu["costo_dia_mo"]
            # P-1 Agua
            _mix_apu = get_mix_for_fc(fc)
            _litros_apu = _mix_apu.get("agua", 180) * vol_concreto_m3
            costo_agua = (_litros_apu / 1000) * apu.get("agua", 3500)
            # P-3 Encofrado
            _dim_enc_b = D if es_circular else b
            _dim_enc_h = D if es_circular else h
            _area_enc_apu = (3.14159 * _dim_enc_b / 100) * (L_col / 100) if es_circular else (2 * (_dim_enc_b + _dim_enc_h) / 100) * (L_col / 100)
            costo_encofrado = _area_enc_apu * apu.get("encofrado", 45000)
            costo_directo = costo_cemento + costo_acero + costo_arena + costo_grava + costo_conc_premix + costo_mo + costo_agua + costo_encofrado
            aiu = costo_directo * apu["pct_aui"]
            total = costo_directo + aiu
            #  Métricas cards 
            _c1, _c2, _c3 = st.columns(3)
            _c1.metric(_t(" Total Proyecto", " Total Project"), f"{total:,.0f} {apu['moneda']}")
            _c2.metric(_t(" Costo Directo", "Direct Cost"), f"{costo_directo:,.0f} {apu['moneda']}")
            _c3.metric(_t(" Mano de Obra", "Labor"), f"{costo_mo:,.0f} {apu['moneda']}")

            #  Gráfica Plotly — Desglose de costos 
            import plotly.graph_objects as _go
            _items_label = (
                [_t("Concreto PM", "Ready-mix"), _t("Acero", "Steel"), _t("M.O.", "Labor"), _t("Agua","Water"), _t("Encofrado","Formwork"), "A.I.U."]
                if _usar_premix else
                [_t("Cemento", "Cement"), _t("Acero", "Steel"), _t("Arena", "Sand"),
                 _t("Grava", "Gravel"), _t("M.O.", "Labor"), _t("Agua","Water"), _t("Encofrado","Formwork"), "A.I.U."]
            )
            _items_val = (
                [costo_conc_premix, costo_acero, costo_mo, costo_agua, costo_encofrado, aiu]
                if _usar_premix else
                [costo_cemento, costo_acero, costo_arena, costo_grava, costo_mo, costo_agua, costo_encofrado, aiu]
            )
            _colors = ["#3fb950", "#79c0ff", "#ffa657", "#d2a8ff", "#58a6ff", "#f0883e"][:len(_items_label)]
            _fig_apu = _go.Figure(_go.Bar(
                x=_items_label, y=_items_val,
                marker_color=_colors,
                text=[f"{v:,.0f}" for v in _items_val],
                textposition='outside',
                textfont=dict(size=11, color='white')
            ))
            _fig_apu.update_layout(
                title=_t("Desglose de Costos — Columna", "Cost Breakdown — Column"),
                paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
                font=dict(color='#cdd6f4'),
                xaxis=dict(gridcolor='#30363d'),
                yaxis=dict(gridcolor='#30363d', tickformat=',.0f'),
                margin=dict(t=40, b=20, l=20, r=20),
                height=320
            )
            st.plotly_chart(_fig_apu, use_container_width=True)
            if _usar_premix:
                st.info(_t(
                    f" Concreto premezclado: {vol_concreto_m3:.3f} m³ × {_precio_premix_m3:,.0f} {apu['moneda']}/m³ = {costo_conc_premix:,.0f} {apu['moneda']}",
                    f" Ready-mix concrete: {vol_concreto_m3:.3f} m³ × {_precio_premix_m3:,.0f} {apu['moneda']}/m³ = {costo_conc_premix:,.0f} {apu['moneda']}"
                ))

            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                if _usar_premix:
                    df_apu = pd.DataFrame({
                        "Item":     ["Concreto Premezclado", "Acero", "Mano de Obra", "Agua", "Encofrado", "A.I.U.", "TOTAL"],
                        "Cantidad": [vol_concreto_m3, peso_total_acero_kg,
                                     peso_total_acero_kg * 0.04 + vol_concreto_m3 * 0.4,
                                     round(_litros_apu, 0), round(_area_enc_apu, 2), "", ""],
                        "Unidad":   ["m³", "kg", "días", "litros", "m²", f"{apu['pct_aui']*100:.0f}%", ""],
                        "Subtotal": [costo_conc_premix, costo_acero, costo_mo, costo_agua, costo_encofrado, aiu, total]
                    })
                else:
                    df_apu = pd.DataFrame({
                        "Item":     ["Cemento", "Acero", "Arena", "Grava", "Mano de Obra", "Agua", "Encofrado", "A.I.U.", "TOTAL"],
                        "Cantidad": [bultos_col, peso_total_acero_kg, mix["arena"]*vol_concreto_m3/1500,
                                     mix["grava"]*vol_concreto_m3/1600,
                                     peso_total_acero_kg*0.04 + vol_concreto_m3*0.4,
                                     round(_litros_apu, 0), round(_area_enc_apu, 2), "", ""],
                        "Unidad":   [f"bultos ({bag_kg}kg)", "kg", "m³", "m³", "días", "litros", "m²",
                                     f"{apu['pct_aui']*100:.0f}%", ""],
                        "Subtotal": [costo_cemento, costo_acero, costo_arena, costo_grava, costo_mo, costo_agua, costo_encofrado, aiu, total]
                    })
                df_apu.to_excel(writer, index=False, sheet_name='APU')
                workbook = writer.book
                worksheet = writer.sheets['APU']
                money_fmt = workbook.add_format({'num_format': '#,##0.00'})
                worksheet.set_column('D:D', 15, money_fmt)
            output_excel.seek(0)
            st.download_button(_t("Descargar Presupuesto Excel", "Download Budget Excel"), 
                               data=output_excel, file_name=f"APU_Columna_{b:.0f}x{h:.0f}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============================================================================
# TAB 4: MEMORIA DE CÁLCULO COMPLETA
# =============================================================================
with tab4:
    st.subheader(_t("Generar Memoria de Cálculo Completa", "Generate Complete Calculation Report"))
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        btn_docx_col = st.button(_t("Generar Memoria DOCX", "Generate DOCX Report"), type="primary")
    with col_d2:
        try:
            import numpy as _np_ifc
            if tuple(int(x) for x in _np_ifc.__version__.split(".")[:2]) >= (2,0):
                st.warning("IFC requiere numpy<2.0 para compatibilidad. Instale: pip install 'numpy<2.0'")
            import ifcopenshell
            import ifcopenshell.api
            import ifcopenshell.guid
            import uuid, time

            def _make_ifc_columna(b_cm, h_cm, D_cm, L_cm, es_circ,
                                  fc_mpa, fy_mpa, n_bars, db_mm, dst_mm,
                                  n_long_total, As_cm2, rho_pct, recub,
                                  s_conf_cm, s_bas_cm, Lo_cm,
                                  n_estrib, Pu_kN, phiPn_kN, bresler_ratio, bresler_ok,
                                  ash_ok_flag, vol_m3, peso_kg,
                                  empresa, proyecto, norma, nivel_sis):
                """Genera un IFC4 con IfcColumn + barras longitudinales + estribos + Pset_NSR10."""
                O = ifcopenshell.file(schema="IFC4")
                # ── Cabecera de proyecto ────────────────────────────────────


                # ── Proyecto / Sitio / Edificio / Piso ─────────────────────
                project  = ifcopenshell.api.run("root.create_entity",    O, ifc_class="IfcProject",  name=proyecto)

                # ── Contexto geométrico ─────────────────────────────────────
                context = ifcopenshell.api.run("context.add_context", O, context_type="Model")
                body    = ifcopenshell.api.run("context.add_context", O,
                    context_type="Model", context_identifier="Body",
                    target_view="MODEL_VIEW", parent=context)

                site     = ifcopenshell.api.run("root.create_entity",    O, ifc_class="IfcSite",     name="Sitio")
                building = ifcopenshell.api.run("root.create_entity",    O, ifc_class="IfcBuilding", name="Edificio")
                storey   = ifcopenshell.api.run("root.create_entity",    O, ifc_class="IfcBuildingStorey", name="Piso 1")
                _u = ifcopenshell.api.run("unit.add_si_unit", O, unit_type="LENGTHUNIT"); ifcopenshell.api.run("unit.assign_unit", O, units=[_u])
                ifcopenshell.api.run("aggregate.assign_object", O, relating_object=project, products=[site])
                ifcopenshell.api.run("aggregate.assign_object", O, relating_object=site, products=[building])
                ifcopenshell.api.run("aggregate.assign_object", O, relating_object=building, products=[storey])

                L_m = L_cm / 100.0;  b_m = b_cm / 100.0;  h_m = h_cm / 100.0
                D_m = D_cm / 100.0;  r_m = recub / 100.0

                # ── Materiales ──────────────────────────────────────────────
                mat_conc = ifcopenshell.api.run("material.add_material", O, name=f"CONCRETO_fc{fc_mpa:.0f}MPa")
                mat_acero = ifcopenshell.api.run("material.add_material", O, name=f"ACERO_fy{fy_mpa:.0f}MPa")

                # ── IfcColumn (geometría extrusión) ─────────────────────────
                column = ifcopenshell.api.run("root.create_entity", O,
                    ifc_class="IfcColumn", name=f"COL-{'CIRC' if es_circ else f'{b_cm:.0f}x{h_cm:.0f}'}")
                column.PredefinedType = "COLUMN"

                # Perfil de la sección según tipo
                import math as _m
                if es_circ:
                    profile = O.createIfcCircleProfileDef(
                        ProfileType="AREA", ProfileName=f"D{D_cm:.0f}",
                        Radius=D_m / 2)
                else:
                    profile = O.createIfcRectangleProfileDef(
                        ProfileType="AREA", ProfileName=f"{b_cm:.0f}x{h_cm:.0f}",
                        XDim=b_m, YDim=h_m)

                # Ubicación y dirección
                origin = O.createIfcCartesianPoint([0.0, 0.0, 0.0])
                z_dir  = O.createIfcDirection([0.0, 0.0, 1.0])
                x_dir  = O.createIfcDirection([1.0, 0.0, 0.0])
                placement = O.createIfcAxis2Placement3D(Location=origin, Axis=z_dir, RefDirection=x_dir)
                solid = O.createIfcExtrudedAreaSolid(
                    SweptArea=profile,
                    Position=placement,
                    ExtrudedDirection=O.createIfcDirection([0.0, 0.0, 1.0]),
                    Depth=L_m)
                shape_rep = O.createIfcShapeRepresentation(
                    ContextOfItems=body, RepresentationIdentifier="Body",
                    RepresentationType="SweptSolid", Items=[solid])
                ifcopenshell.api.run("geometry.assign_representation", O, product=column, representation=shape_rep)
                ifcopenshell.api.run("geometry.edit_object_placement", O, product=column)

                # Asignar al piso
                ifcopenshell.api.run("spatial.assign_container", O,
                    relating_structure=storey, products=[column])
                # Asignar material al concreto
                ifcopenshell.api.run("material.assign_material", O, products=[column], material=mat_conc)

                # ── Barras Longitudinales (IfcReinforcingBar) ───────────────
                import math as _m
                db_m = db_mm / 1000.0

                def _color_by_diam(db):
                    """Mapa diámetro (mm) → RGB IFC [0-1]"""
                    c = {8:(0.8,0.9,1.0), 10:(0.4,0.8,1.0), 12:(0.1,0.7,0.2),
                         16:(1.0,0.8,0.0), 19:(1.0,0.5,0.0), 20:(1.0,0.5,0.0),
                         22:(1.0,0.2,0.2), 25:(0.9,0.0,0.0), 32:(0.6,0.0,0.6)}
                    key = min(c.keys(), key=lambda k: abs(k - db))
                    return c[key]

                rebar_color = _color_by_diam(db_mm)

                if es_circ:
                    R_bar = (D_m / 2) - r_m  # radio del eje de la barra
                    bar_positions = [
                        (_m.cos(2*_m.pi*i/n_bars)*R_bar,
                         _m.sin(2*_m.pi*i/n_bars)*R_bar)
                        for i in range(n_bars)
                    ]
                else:
                    # Distribución perimetral rectangular
                    nx = max(2, int(_m.ceil(b_cm / 15)))   # barras por cara b
                    ny = max(2, int(_m.ceil(h_cm / 15)))   # barras por cara h
                    # Eje varilla = recub + dst_completo + radio_varilla (Prompt Maestro v2)
                    _rv = r_m + dst_mm / 1000.0 + db_mm / 2000.0
                    xs = [_rv + (b_m - 2*_rv)*i/(nx-1) - b_m/2 for i in range(nx)] if nx > 1 else [0.0]
                    ys = [_rv + (h_m - 2*_rv)*i/(ny-1) - h_m/2 for i in range(ny)] if ny > 1 else [0.0]
                    bar_positions = (
                        [(x, -h_m/2 + _rv) for x in xs] +
                        [(x,  h_m/2 - _rv) for x in xs] +
                        [(-b_m/2 + _rv, y) for y in ys[1:-1]] +
                        [( b_m/2 - _rv, y) for y in ys[1:-1]]
                    )

                long_bars = []
                for i, (bx, by) in enumerate(bar_positions):
                    bar = ifcopenshell.api.run("root.create_entity", O,
                        ifc_class="IfcReinforcingBar", name=f"L{i+1}")
                    bar.NominalDiameter = db_m
                    bar.SteelGrade      = f"fy={fy_mpa:.0f}MPa"
                    bar.BarSurface      = "TEXTURED"
                    bar.PredefinedType  = "MAIN"

                    # Geometría: línea vertical (poly-line extruida)
                    p0 = O.createIfcCartesianPoint([bx, by, 0.0])
                    p1 = O.createIfcCartesianPoint([bx, by, L_m])
                    polyline = O.createIfcPolyline(Points=[p0, p1])
                    bar_profile = O.createIfcCircleProfileDef(
                        ProfileType="AREA", Radius=db_m/2)
                    bar_place = O.createIfcAxis2Placement3D(
                        Location=O.createIfcCartesianPoint([bx, by, 0.0]),
                        Axis=O.createIfcDirection([0.0, 0.0, 1.0]),
                        RefDirection=O.createIfcDirection([1.0, 0.0, 0.0]))
                    bar_solid = O.createIfcExtrudedAreaSolid(
                        SweptArea=bar_profile, Position=bar_place,
                        ExtrudedDirection=O.createIfcDirection([0.0, 0.0, 1.0]),
                        Depth=L_m)
                    style = O.createIfcSurfaceStyleRendering(
                        SurfaceColour=O.createIfcColourRgb(Red=rebar_color[0], Green=rebar_color[1], Blue=rebar_color[2]),
                        ReflectanceMethod="FLAT")
                    surface_style = O.createIfcSurfaceStyle(
                        Name=f"AceroLong_{db_mm:.0f}mm", Side="BOTH", Styles=[style])
                    O.createIfcStyledItem(Item=bar_solid, Styles=[surface_style])
                    bar_rep = O.createIfcShapeRepresentation(
                        ContextOfItems=body, RepresentationIdentifier="Body",
                        RepresentationType="SweptSolid", Items=[bar_solid])
                    ifcopenshell.api.run("geometry.assign_representation", O, product=bar, representation=bar_rep)
                    ifcopenshell.api.run("geometry.edit_object_placement", O, product=bar)

                    ifcopenshell.api.run("spatial.assign_container", O,
                        relating_structure=storey, products=[bar])
                    ifcopenshell.api.run("material.assign_material", O, products=[bar], material=mat_acero)
                    long_bars.append(bar)

                # ── Estribos / Espiral (IfcReinforcingBar cerrado) ──────────
                dst_m = dst_mm / 1000.0
                stirrup_color = _color_by_diam(dst_mm)
                stirrup_bars = []

                # Generar posiciones verticales de cada estribo
                y_positions = []
                y_curr = 5.0  # cm
                while y_curr <= L_cm - 5.0:
                    in_conf = (y_curr <= Lo_cm) or (y_curr >= L_cm - Lo_cm)
                    sep = s_conf_cm if in_conf else s_bas_cm
                    y_positions.append(y_curr / 100.0)  # a metros
                    y_curr += sep

                for j, y_z in enumerate(y_positions):
                    st_bar = ifcopenshell.api.run("root.create_entity", O,
                        ifc_class="IfcReinforcingBar", name=f"E{j+1}")
                    st_bar.NominalDiameter = dst_m
                    st_bar.SteelGrade      = f"fy={fy_mpa:.0f}MPa"
                    st_bar.BarSurface      = "TEXTURED"
                    st_bar.PredefinedType  = "MAIN"

                    # Polilínea cerrada del estribo
                    if es_circ:
                        R_e = (D_m / 2) - r_m
                        n_pts = 16
                        pts_est = [O.createIfcCartesianPoint([
                            _m.cos(2*_m.pi*k/n_pts)*R_e,
                            _m.sin(2*_m.pi*k/n_pts)*R_e, y_z])
                            for k in range(n_pts + 1)]
                    else:
                        # ── Prompt Maestro v2 — NSR-10 C.21.5.3.3 ─────────────
                        bx2  = b_m / 2.0 - r_m          # eje estribo semiancho
                        hy2  = h_m / 2.0 - r_m          # eje estribo semialto
                        X_c  = -bx2
                        Y_c  =  hy2
                        # Regla 1: radio y gancho NORMATIVOS (sin factores inventados)
                        _R   = max(3.0 * dst_m, 0.012)
                        _hk  = max(6.0 * db_mm/1000.0, 0.075)
                        Cx   = X_c + _R
                        Cy   = Y_c - _R
                        _z1  = y_z + dst_m              # z_top espiral +1 diámetro
                        _na  = 8                         # segmentos por arco

                        # Arco: z fijo, NA+1 puntos
                        def _arc(cx, cy, r, a0, a1, z_c):
                            return [O.createIfcCartesianPoint([
                                cx + r*_m.cos(_m.radians(a0+(a1-a0)*_ii/_na)),
                                cy + r*_m.sin(_m.radians(a0+(a1-a0)*_ii/_na)),
                                z_c]) for _ii in range(_na+1)]

                        def _pt(x, y, z_c):
                            return O.createIfcCartesianPoint([x, y, z_c])

                        # Pie del arco G1 (225°) y G2 (45°)
                        _pie1x = Cx + _R*_m.cos(_m.radians(225))
                        _pie1y = Cy + _R*_m.sin(_m.radians(225))
                        _pie2x = Cx + _R*_m.cos(_m.radians(45))
                        _pie2y = Cy + _R*_m.sin(_m.radians(45))
                        _dk    = _hk * 0.7071            # componente 45°

                        pts_est = []
                        # [1] Cola 1 punta → pie G1  (dirección +X,-Y = núcleo)
                        pts_est.append(_pt(_pie1x + _dk, _pie1y - _dk, _z1))
                        pts_est.append(_pt(_pie1x,       _pie1y,       _z1))
                        # [2] Arco G1 CCW 225°→90°  Z=z_top
                        pts_est += _arc(Cx, Cy, _R, 225, 90, _z1)
                        # Tangencia fin G1 = (Cx, Y_c) = inicio tramo superior
                        # [3] Tramo SUP (Cx,Y_c)→(bx2-_R,Y_c)  Z baja→z_base
                        _nT = _na
                        pts_est += [_pt(Cx+(bx2-_R-Cx)*_ii/_nT,
                                        Y_c,
                                        _z1+(y_z-_z1)*_ii/_nT)
                                    for _ii in range(_nT+1)]
                        # [4] Arco SUP-DER CW 90°→0°  Z=z_base
                        pts_est += _arc(bx2-_R, Y_c-_R, _R, 90, 0, y_z)
                        # [5] Tramo DER  Z=z_base  (tangencia a tangencia)
                        pts_est += [_pt(bx2, Y_c-_R+(-(Y_c-_R)-(Y_c-_R))*_ii/_nT, y_z)
                                    for _ii in range(_nT+1)]
                        # [6] Arco INF-DER CW 0°→-90°  Z=z_base
                        pts_est += _arc(bx2-_R, -(Y_c-_R), _R, 0, -90, y_z)
                        # [7] Tramo INF  Z=z_base
                        pts_est += [_pt(bx2-_R+(-(bx2-_R)-(bx2-_R))*_ii/_nT, -Y_c, y_z)
                                    for _ii in range(_nT+1)]
                        # [8] Arco INF-IZQ CW -90°→-180°  Z=z_base
                        pts_est += _arc(-(bx2-_R), -(Y_c-_R), _R, -90, -180, y_z)
                        # [9] Tramo IZQ (-bx2,-(Y_c-_R))→(X_c,Cy)  Z sube→z_top
                        pts_est += [_pt(X_c,
                                        -(Y_c-_R)+(Cy-(-(Y_c-_R)))*_ii/_nT,
                                        y_z+(_z1-y_z)*_ii/_nT)
                                    for _ii in range(_nT+1)]
                        # [10] Arco G2 CW 180°→45°  Z=z_top
                        pts_est += _arc(Cx, Cy, _R, 180, 45, _z1)
                        # [11] Pie G2 → Cola 2 punta  (misma dirección +X,-Y)
                        pts_est.append(_pt(_pie2x,       _pie2y,       _z1))
                        pts_est.append(_pt(_pie2x + _dk, _pie2y - _dk, _z1))

                        # Alternancia sísmica NSR-10 C.21.5.3.3
                        if j % 2 != 0:
                            pts_est = [O.createIfcCartesianPoint(
                                [-p.Coordinates[0], -p.Coordinates[1], p.Coordinates[2]])
                                for p in pts_est]

                    polyline_st = O.createIfcPolyline(Points=pts_est)

                    # Volumen físico para que Revit lo reconozca como Armadura
                    st_swept = O.createIfcSweptDiskSolid(Directrix=polyline_st, Radius=dst_m/2)
                    
                    st_style_rend = O.createIfcSurfaceStyleRendering(
                        SurfaceColour=O.createIfcColourRgb(Red=stirrup_color[0], Green=stirrup_color[1], Blue=stirrup_color[2]),
                        ReflectanceMethod="FLAT")
                    st_surface_style = O.createIfcSurfaceStyle(
                        Name=f"Estribo_{dst_mm:.0f}mm", Side="BOTH", Styles=[st_style_rend])
                    O.createIfcStyledItem(Item=st_swept, Styles=[st_surface_style])

                    st_rep = O.createIfcShapeRepresentation(
                        ContextOfItems=body, RepresentationIdentifier="Body",
                        RepresentationType="AdvancedSweptSolid", Items=[st_swept])

                    ifcopenshell.api.run("geometry.assign_representation", O, product=st_bar, representation=st_rep)
                    ifcopenshell.api.run("geometry.edit_object_placement", O, product=st_bar)

                    ifcopenshell.api.run("spatial.assign_container", O,
                        relating_structure=storey, products=[st_bar])
                    ifcopenshell.api.run("material.assign_material", O, products=[st_bar], material=mat_acero)
                    stirrup_bars.append(st_bar)

                # ── Pset_NSR10 y Pset_ColGeometry ──────────────────────────
                psets_data = {
                    "Pset_ConcreteElementGeneral": {
                        "ConstructionMethod":      "CastInPlace",
                        "StructuralClass":         "Column",
                        "StrengthClass":           f"f'c {fc_mpa:.1f} MPa",
                        "ReinforcementVolumeRatio": float(rho_pct) / 100.0,
                        "ReinforcementAreaRatio":   float(As_cm2)
                    },
                    f"Pset_{norma_sel.split('(')[0].strip().replace('-','_').replace(' ','_')}": {
                        "Norma":                norma,
                        "Nivel_Sismico":        nivel_sis,
                        "fc_MPa":               float(fc_mpa),
                        "fy_MPa":               float(fy_mpa),
                        "As_cm2":               float(As_cm2),
                        "Rho_pct":              float(rho_pct),
                        "n_barras_long":        int(n_long_total),
                        "diametro_barra_mm":    float(db_mm),
                        "diametro_estribo_mm":  float(dst_mm),
                        "sep_estrib_conf_cm":   float(s_conf_cm),
                        "sep_estrib_basica_cm": float(s_bas_cm),
                        "Lo_conf_cm":           float(Lo_cm),
                        "n_estribos_total":     int(n_estrib),
                        "Pu_kN":                float(Pu_kN),
                        "phi_Pni_kN":           float(phiPn_kN),
                        "Bresler_ratio":        float(bresler_ratio),
                        "Bresler_CUMPLE":       "SI" if bresler_ok else "NO",
                        "Ash_CUMPLE":           "SI" if ash_ok_flag else "NO",
                        "Vol_concreto_m3":      float(vol_m3),
                        "Peso_acero_kg":        float(peso_kg),
                    },
                    "Pset_ColGeom": {
                        "Tipo":       "Circular" if es_circ else "Rectangular",
                        "b_cm":       float(b_cm),
                        "h_cm":       float(h_cm),
                        "D_cm":       float(D_cm) if es_circ else 0.0,
                        "L_cm":       float(L_cm),
                        "Recub_cm":   float(recub),
                    },
                }

                for pset_name, props_dict in psets_data.items():
                    pset = ifcopenshell.api.run("pset.add_pset", O,
                        product=column, name=pset_name)
                    ifcopenshell.api.run("pset.edit_pset", O,
                        pset=pset, properties=props_dict)

                # ── Guardar en buffer ───────────────────────────────────────
                import tempfile, os as _os
                with tempfile.NamedTemporaryFile(suffix='.ifc', delete=False) as tmp:
                    tmp_path = tmp.name
                O.write(tmp_path)
                with open(tmp_path, 'rb') as f_ifc:
                    buf = f_ifc.read()
                _os.unlink(tmp_path)
                return buf

            # Botón para generar — solo ejecuta la función al hacer clic
            if st.button("⬇️ " + _t("Generar y Exportar IFC4 (BIM completo)", "Generate & Export IFC4 (full BIM)"), key="col_btn_ifc"):
                phiPn_max = cap_x.get('phi_Pn_max', 0) if 'cap_x' in locals() and cap_x else 0
                buf_ifc_col = _make_ifc_columna(
                    b_cm        = b   if not es_circular else 0,
                    h_cm        = h   if not es_circular else 0,
                    D_cm        = D   if es_circular     else 0,
                    L_cm        = L_col,
                    es_circ     = es_circular,
                    fc_mpa      = fc, fy_mpa = fy,
                    n_bars      = n_barras if es_circular else n_barras_total,
                    db_mm       = rebar_diam, dst_mm = stirrup_diam,
                    n_long_total= n_barras if es_circular else n_barras_total,
                    As_cm2      = Ast, rho_pct = cuantia,
                    recub       = recub_cm,
                    s_conf_cm   = s_conf  if not es_circular else paso_espiral,
                    s_bas_cm    = s_basico if not es_circular else paso_espiral,
                    Lo_cm       = Lo_conf,
                    n_estrib    = n_estribos_total if not es_circular else 1,
                    Pu_kN       = Pu_input * factor_fuerza,
                    phiPn_kN    = phiPn_max * factor_fuerza,
                    bresler_ratio = bresler['ratio'],
                    bresler_ok  = bresler['ok'],
                    ash_ok_flag = ash_ok,
                    vol_m3      = vol_concreto_m3,
                    peso_kg     = peso_total_acero_kg,
                    empresa     = st.session_state.get("cpm_empresa","________________"),
                    proyecto    = st.session_state.get("cpm_proyecto_nombre","________________"),
                    norma       = norma_sel,
                    nivel_sis   = nivel_sismico,
                )
                if buf_ifc_col:
                    _ifc_fname = f"Columna_{'Circ_D'+str(int(D)) if es_circular else str(int(b))+'x'+str(int(h))}_IFC4.ifc"
                    st.success(_t("IFC4 generado correctamente.", "IFC4 generated successfully."))
                    st.download_button(
                        label=_t("⬇️ Descargar IFC4", "⬇️ Download IFC4"),
                        data=buf_ifc_col,
                        file_name=_ifc_fname,
                        mime="application/x-step",
                        key="col_ifc_dl")
                    st.caption(_t(
                        f"IFC4: IfcColumn + barras long. + estribos 3D + Pset_{norma_sel.split('(')[0].strip()}",
                        f"IFC4: IfcColumn + longitudinal bars + 3D stirrups + Pset_{norma_sel.split('(')[0].strip()}"))


        except ImportError as e_imp:
            import sys as _sys_ifc
            import importlib
            importlib.invalidate_caches()
            _pyver = f"{_sys_ifc.version_info.major}.{_sys_ifc.version_info.minor}"
            _pyexe = _sys_ifc.executable
            st.error(
                f"⚠️ Error cargando **IfcOpenShell** en este entorno Python.\n\n"
                f"**Python activo:** `{_pyexe}` (versión {_pyver})\n\n"
                f"**Detalle del error (ImportError):** `{str(e_imp)}`\n\n"
                f"**Solución 1:** Si acabas de instalar mediante pip, **REINICIA EL SERVIDOR DE STREAMLIT** (`Ctrl+C` y luego `streamlit run app.py`).\n\n"
                f"**Solución 2:** Si el error persiste, verifica la instalación en una terminal.\n"
                f"```bash\n{_pyexe} -m pip install ifcopenshell\n```"
            )
        except Exception as e_ifc:
            import traceback
            st.error(f"Error IFC: {e_ifc}")
            st.code(traceback.format_exc(), language='python')
            st.info("Asegurate de que ifcopenshell este disponible en el entorno de ejecucion.")
    if btn_docx_col:
        try:
            from utils_docx import fig_to_docx_white
        except ImportError:
            # Fallback robusto: siempre retorna io.BytesIO
            import io as _io_fbk
            def fig_to_docx_white(fig):
                """Modo claro para DOCX. Restaura colores pantalla."""
                import io as _iow
                if not fig.get_axes():
                    b=_iow.BytesIO(); b.seek(0); return b
                _ofc=fig.get_facecolor()
                _oax=[(ax,ax.get_facecolor(),ax.xaxis.label.get_color(),
                       ax.yaxis.label.get_color(),ax.title.get_color() if ax.get_title() else None,
                       {sp:ax.spines[sp].get_edgecolor() for sp in ax.spines})
                      for ax in fig.get_axes()]
                fig.patch.set_facecolor('white'); fig.patch.set_alpha(1.0)
                for ax in fig.get_axes():
                    ax.set_facecolor('#f8f9fa')
                    ax.tick_params(colors='#1a1a1a')
                    ax.xaxis.label.set_color('#1a1a1a')
                    ax.yaxis.label.set_color('#1a1a1a')
                    if ax.get_title(): ax.title.set_color('#1a1a1a')
                    for sp in ax.spines.values():
                        sp.set_edgecolor('#cccccc'); sp.set_linewidth(0.8)
                buf=_iow.BytesIO()
                fig.savefig(buf,format='png',dpi=200,bbox_inches='tight',facecolor='white',transparent=False)
                buf.seek(0)
                fig.patch.set_facecolor(_ofc)
                for ax,ofc,oxl,oyl,otit,osps in _oax:
                    ax.set_facecolor(ofc); ax.xaxis.label.set_color(oxl); ax.yaxis.label.set_color(oyl)
                    if otit: ax.title.set_color(otit)
                    for sn,sc in osps.items(): ax.spines[sn].set_edgecolor(sc)
                return buf

        doc = Document()
        doc.add_heading(f"MEMORIA ESTRUCTURAL — COLUMNA {'CIRCULAR' if es_circular else 'RECTANGULAR'} ({norma_sel})", 0)
        
        # 0. Portada dinámica — marca blanca
        _emp  = st.session_state.get("cpm_empresa","________________")
        _proy = st.session_state.get("cpm_proyecto_nombre","________________")
        _ing  = st.session_state.get("cpm_ingeniero","________________")
        p0 = doc.add_paragraph()
        p0.add_run(f"EMPRESA: {_emp}\n").bold = True
        p0.add_run(f"PROYECTO: {_proy}\n").bold = True
        p0.add_run(f"INGENIERO RESPONSABLE: {_ing}\n").bold = True
        p0.add_run(f"ELEMENTO: Columna {'Circular' if es_circular else 'Rectangular'} | NORMA: {norma_sel} | SÍSMICO: {nivel_sismico}\n")
        p0.add_run(f"MATERIALES: f'c={fc:.1f} MPa, fy={fy:.1f} MPa | FECHA: {datetime.datetime.now().strftime('%d/%m/%Y')}")
        
        # 1. Parámetros de Diseño
        doc.add_heading("1. PARÁMETROS GEOMÉTRICOS Y SOLICITACIONES", level=1)
        doc.add_paragraph(f"Geometría: {'D' if es_circular else 'b'} = {D if es_circular else b:.0f} cm, {'h = '+str(h)+' cm, ' if not es_circular else ''}L = {L_col:.0f} cm\nRecubrimiento libre: {recub_cm} cm\nCargas de diseño aplicadas:\n  Pu = {Pu_input:.1f} {unidad_fuerza}\n  Mux = {Mux_input:.1f} {unidad_mom}\n  Muy = {Muy_input:.1f} {unidad_mom}")
        
        # 2. Esbeltez
        doc.add_heading("2. PRE-DIMENSIONAMIENTO Y EFECTOS DE ESBELTEZ (NSR-10 C.10.10)", level=1)
        doc.add_paragraph(f"Relación de esbeltez (kL/r): {slenderness['kl_r']:.2f}")
        if slenderness['kl_r'] > 100:
            p_esb = doc.add_paragraph("[ADVERTENCIA] Columna MUY esbelta (kL/r > 100). Las ecuaciones estándar pierden validez, requiere análisis P-delta riguroso.")
            p_esb.bold = True
        elif slenderness['kl_r'] > 22:
            doc.add_paragraph(f"Columna Esbelta — δns = {slenderness['delta_ns']:.3f} ({coderef}, método no-sway). Si estructura desplazable: aplicar P-Δ e ingresar Mux/Muy amplificados.").runs[0].bold=True
            if 'Pc' in dir(): doc.add_paragraph(f"Carga crítica Euler (Pc) = {Pc:.1f} kN")
            doc.add_paragraph(f"Momento magnificado Mux* = {Mux_input*slenderness['delta_ns']:.2f} {unidad_mom}")
            _r_min = (h if not es_circular else D)*0.289
            _b_min = round(k_factor*L_col/(22*0.289)*10)/10 if 'k_factor' in dir() else round(L_col/6.4,1)
            doc.add_paragraph(f"⚠️ Sección mínima recomendada para kL/r≤22: b_min ≥ {_b_min:.1f} cm (NSR-10 C.10.10.1)").runs[0].bold=True
        else:
            doc.add_paragraph("Columna Corta — No requiere magnificación de momentos por esbeltez.")
            
        # 3. Diseño a Flexo-compresión
        doc.add_heading("3. CAPACIDAD A FLEXO-COMPRESIÓN BIAXIAL", level=1)
        doc.add_heading("3.1 Detallado de Capas Longitudinales", level=2)
        
        Ast_total = Ast
        doc.add_paragraph(f"Área Bruta (Ag): {Ag:.2f} cm² | Área de Acero Total (Ast): {Ast_total:.2f} cm²")
        # Sustitución numérica paso a paso
        _Po_calc=(0.85*fc*(Ag-Ast_total)+fy*Ast_total)/10.0  # kN
        _Pnmax_calc=0.80*_Po_calc  # estribos
        _phi_c=0.65 if not es_circular else 0.75
        _phiPnmax=_phi_c*_Pnmax_calc
        doc.add_paragraph(f"Po = 0.85·f'c·(Ag−Ast) + fy·Ast = 0.85×{fc:.1f}×({Ag:.2f}−{Ast_total:.2f}) + {fy:.1f}×{Ast_total:.2f} = {_Po_calc:.1f} kN  [NSR-10 C.10.3.6]")
        doc.add_paragraph(f"Pn,máx = 0.80×Po = 0.80×{_Po_calc:.1f} = {_Pnmax_calc:.1f} kN  (estribos rect. ACI §22.4.2.1)")
        doc.add_paragraph(f"φPn,máx = φ×Pn,máx = {_phi_c:.2f}×{_Pnmax_calc:.1f} = {_phiPnmax:.1f} kN")
        
        tb_lay = doc.add_table(rows=1, cols=5)
        tb_lay.style = 'Light Grid'
        tb_lay.rows[0].cells[0].text = 'Capa de Acero'
        tb_lay.rows[0].cells[1].text = "d' (cm)"
        tb_lay.rows[0].cells[2].text = 'As (cm²)'
        tb_lay.rows[0].cells[3].text = 'fs (MPa)'
        tb_lay.rows[0].cells[4].text = 'εs'
        
        # Estado de limit balanceado (solo como referencia estatica aprox)
        h_eff = D if es_circular else h
        cb = h_eff * 0.003 / (0.003 + fy/200000)
        
        for i, lay in enumerate(layers if not es_circular else area_capas_mock):
            rc = tb_lay.add_row().cells
            rc[0].text = f"Capa {i+1}"
            try:
                di = lay['d'] if isinstance(lay, dict) else (D/2)
                As_i = lay['As'] if isinstance(lay, dict) else lay
                es_i = 0.003 * ((cb - di) / cb) if cb>0 else 0
                fs_i = max(-fy, min(fy, es_i * 200000))
                rc[1].text = f"{di:.1f}"
                rc[2].text = f"{As_i:.2f}"
                rc[3].text = f"{fs_i:.0f} (Bal)"
                rc[4].text = f"{es_i:.4f} (Bal)"
            except: pass
            
        doc.add_heading("3.2 Verificación Biaxial (Bresler)", level=2)
        Po_calc = (0.85 * fc * (Ag/10000 - Ast_total/10000) + fy * (Ast_total/10000)) * 1000 
        doc.add_paragraph(f"Resistencia teórica pura (Po) = {Po_calc:.1f} kN")
        doc.add_paragraph(f"Método de Bresler Biaxial: {'CUMPLE' if bresler['ok'] else 'NO CUMPLE'} (Ratio = {bresler['ratio']:.3f})")
        if not bresler['ok']:
            doc.add_paragraph(f"[ADVERTENCIA] Se requiere aumentar sección o cuantía.").bold = True
            
        doc.add_heading("3.3 Envolvente P-M de Capacidad Real", level=2)
        try:
            import io as _io_pm
            buf_pm = _io_pm.BytesIO()
            # Forzar fondo blanco antes de capturar
            _orig_fc = fig_pm_2d.get_facecolor()
            fig_pm_2d.patch.set_facecolor('white')
            fig_pm_2d.patch.set_alpha(1.0)
            for _ax in fig_pm_2d.get_axes():
                _ax.set_facecolor('white')
                _ax.tick_params(colors='#1a1a1a')
                _ax.xaxis.label.set_color('#1a1a1a')
                _ax.yaxis.label.set_color('#1a1a1a')
            fig_pm_2d.savefig(buf_pm, facecolor='white', edgecolor='none', format='png', dpi=200,
                              bbox_inches='tight', transparent=False)
            buf_pm.seek(0)
            fig_pm_2d.patch.set_facecolor(_orig_fc)  # restaurar modo oscuro
            doc.add_picture(buf_pm, width=Inches(6.0))
            buf_pm.close()
        except Exception: pass
        
        doc.add_heading("3.4 Superficie de Interacción 3D Biaxial", level=2)
        try:
            import plotly.io as pio
            # N4 – Inyectar el modelo 3D con layout blanco + paneles blancos
            fig_3d.update_layout(
                template="plotly_white",
                scene=dict(
                    xaxis=dict(backgroundcolor='white', gridcolor='#cccccc', showbackground=True),
                    yaxis=dict(backgroundcolor='white', gridcolor='#cccccc', showbackground=True),
                    zaxis=dict(backgroundcolor='white', gridcolor='#cccccc', showbackground=True),
                    bgcolor='white'
                ),
                paper_bgcolor='white', plot_bgcolor='white'
            )
            buf_3d = io.BytesIO()
            pio.write_image(fig_3d, buf_3d, format="png", width=600, height=450, scale=1.5)
            buf_3d.seek(0)
            doc.add_picture(buf_3d, width=Inches(5.0))
        except Exception as e: pass
            
        # 4. Diseño a Cortante
        doc.add_heading("4. DISEÑO A CORTANTE Y CONFINAMIENTO SÍSMICO", level=1)
        doc.add_paragraph("El detallado de estribos se rige por las especificaciones de grado de disipación de energía de la NSR-10.")
        
        if not es_circular:
            doc.add_paragraph(f"Ash Requerido de control: {Ash_req:.3f} cm²/sentido  |  Ash Provisto: {Ash_prov:.3f} cm²")
        else:
            doc.add_paragraph(f"Espiral requerida mínima: {rho_s_req:.4f}  |  Espiral provista: {rho_s_prov:.4f}")
        
        sconf_saf = locals().get('sconf', locals().get('s_conf', st.session_state.get('col_sconf', 0.0)))
        Lo_conf_saf = locals().get('Lo_conf', st.session_state.get('col_Loconf', 0.0))
        stirrupdiam_saf = locals().get('stirrupdiam', locals().get('stirrup_diam', st.session_state.get('col_stirrupdiam', 0)))
        s_bas_saf = locals().get('s_bas_cm', locals().get('s_bas', 0.0))
        
        doc.add_heading("4.1 Justificación de Espaciamiento", level=2)
        doc.add_paragraph(f"Longitudes límite Lo = {Lo_conf_saf:.1f} cm")
        doc.add_paragraph(f"s1 (Separación confinada): Estribos {stirrupdiam_saf}mm @ {sconf_saf:.0f} cm")
        doc.add_paragraph(f"s2 (Separación centro): Estribos {stirrupdiam_saf}mm @ {s_bas_saf:.0f} cm")

        # 5. Verificaciones Normativas
        doc.add_heading(f"5. VERIFICACIONES NORMATIVAS — {norma_sel}", level=1)
        table5 = doc.add_table(rows=1, cols=5)
        table5.style = 'Table Grid'
        _hc5 = table5.rows[0].cells
        _hc5[0].text="Parámetro"; _hc5[1].text="Artículo NSR-10"
        _hc5[2].text="Valor Calculado"; _hc5[3].text="Límite Normativo"; _hc5[4].text="Estado"
        from docx.oxml.ns import qn as _qn5
        from docx.oxml import OxmlElement as _OE5
        def _shade5(cell, color):
            s=_OE5("w:shd"); s.set(_qn5("w:fill"),color)
            cell._tc.get_or_add_tcPr().append(s)
        def _add_row5(param, art, val, lim, ok):
            rc=table5.add_row().cells
            rc[0].text=str(param); rc[1].text=str(art)
            rc[2].text=str(val);   rc[3].text=str(lim)
            rc[4].text="CUMPLE" if ok else "NO CUMPLE"
            _shade5(rc[4],"C6EFCE" if ok else "FFC7CE")
        _art_conf='C.21.6.4' if 'DES' in nivel_sismico else ('C.21.3.5' if 'DMO' in nivel_sismico else 'C.11.4.1')
        _s_lim=10.0 if 'DES' in nivel_sismico else 15.0
        _add_row5("Cuantía ρ","C.10.9.1 / C.21.6.3",f"ρ={cuantia:.3f}%",f"{rho_min}%–{rho_max}%",(rho_min<=cuantia<=rho_max))
        _add_row5("Biaxial Bresler","C.10.3.6 / ACI §22.4",f"Ratio={bresler['ratio']:.3f}","≤ 1.0",bresler['ok'])
        _add_row5("Ash confinamiento",f"{_art_conf}.4","Ash_prov ≥ Ash_req","Ash_req según fórmula",ash_ok)
        _add_row5(f"Sep. conf. zona ({nivel_sismico})",_art_conf,f"s={sconf_saf:.1f} cm",f"≤ {_s_lim:.0f} cm",sconf_saf<=_s_lim)
        _add_row5("Esbeltez kL/r","C.10.10.1",f"kL/r={slenderness['kl_r']:.1f}","≤ 22 sin magnificar",slenderness['kl_r']<=100)
        _add_row5("Diam. mín. estribo","C.21.6.4.2",f"Ø{stirrupdiam_saf:.1f} mm","≥ Ø9.53mm (No.3)",stirrupdiam_saf>=9.53)
        if not es_circular:
            _Lo_min=max(h,b,L_col/6.0,45.0)
            _add_row5("Long. confinamiento Lo","C.21.6.4.1",f"Lo={Lo_conf_saf:.1f} cm",f"≥ {_Lo_min:.1f} cm",Lo_conf_saf>=_Lo_min)
        if not bresler['ok']:
            doc.add_paragraph(f"⚠️ NO CUMPLE Biaxial: ratio={bresler['ratio']:.3f}. Aumente sección o cuantía.").runs[0].bold=True
        if not (rho_min<=cuantia<=rho_max):
            doc.add_paragraph(f"⚠️ NO CUMPLE Cuantía ρ={cuantia:.3f}%. Ajuste barras longitudinales.").runs[0].bold=True
                # 6. Cuantificación y Dosificación
        doc.add_heading("6. CANTIDADES DE OBRA, DOSIFICACIONES Y DESPIECE", level=1)
        doc.add_paragraph(f"Volumen total de concreto: {vol_concreto_m3:.4f} m³")
        doc.add_paragraph(f"Peso total Acero: {peso_total_acero_kg:.1f} kg (Cuantía volc: {peso_total_acero_kg/vol_concreto_m3:.1f} kg/m³)")
        
        # 2. Dosificación aproximada por m3
        p_dosif = doc.add_paragraph(f"\nDOSIFICACIÓN RECOMENDADA EN OBRA PARA f'c={fc:.1f} MPa (Aproximación por m3):\n")
        p_dosif.runs[0].bold = True
        if fc >= 21:
            cemento_kg = 350 * vol_concreto_m3
            arena_m3 = 0.56 * vol_concreto_m3
            grava_m3 = 0.84 * vol_concreto_m3
            agua_lt = 180 * vol_concreto_m3
            sacos = cemento_kg / 50
            doc.add_paragraph(f"• Cemento (50kg): {cemento_kg:.1f} kg (~{sacos:.1f} sacos)")
            doc.add_paragraph(f"• Arena: {arena_m3:.2f} m³")
            doc.add_paragraph(f"• Triturado/Gravilla: {grava_m3:.2f} m³")
            doc.add_paragraph(f"• Agua: {agua_lt:.1f} Litros")
        else:
            doc.add_paragraph("Requiere diseño de mezcla especializado por debajo de 21 MPa.")
        
        # Gráfica de costos APU en modo claro
        try:
            import matplotlib.pyplot as _plt_apu, io as _io_apu
            _cats=["Concreto","Acero Long.","Estribos","Total Acero"]
            _vals_apu=[
                vol_concreto_m3*st.session_state.get("col_apu_premix_p",350000) if st.session_state.get("col_apu_premix",False) else vol_concreto_m3*250000,
                peso_acero_long_kg*st.session_state.get("col_apu_acero",4200),
                peso_total_estribos_kg*st.session_state.get("col_apu_acero",4200),
                peso_total_acero_kg*st.session_state.get("col_apu_acero",4200),
            ]
            _mon=st.session_state.get("col_apu_moneda","COP $")
            _fig_apu,_ax_apu=_plt_apu.subplots(figsize=(6,3))
            _fig_apu.patch.set_facecolor('white'); _ax_apu.set_facecolor('#f8f9fa')
            _bars=_ax_apu.bar(_cats,_vals_apu,color=['#1565C0','#C62828','#EF6C00','#2E7D32'],edgecolor='white',width=0.55)
            _ax_apu.set_title(f"Desglose de Costos APU ({_mon})",color='#1a1a1a',fontsize=10,fontweight='bold')
            _ax_apu.tick_params(colors='#1a1a1a',labelsize=8)
            for sp in _ax_apu.spines.values(): sp.set_edgecolor('#cccccc')
            for _b in _bars:
                _ax_apu.text(_b.get_x()+_b.get_width()/2.,_b.get_height()*1.01,
                    f"{_b.get_height():,.0f}",ha='center',va='bottom',fontsize=7,color='#1a1a1a')
            _buf_apu=_io_apu.BytesIO()
            _fig_apu.savefig(_buf_apu,format='png',dpi=180,bbox_inches='tight',facecolor='white',transparent=False)
            _buf_apu.seek(0); _plt_apu.close(_fig_apu)
            doc.add_picture(_buf_apu,width=Inches(5.5))
        except Exception as _e_apu:
            doc.add_paragraph(f"(Gráfica APU no disponible: {_e_apu})")
        doc.add_paragraph(f"\n3. TABLA DE FIGURADOS Y EMPALMES:\n").runs[0].bold = True
        ld_mm = lambda d: (1.3 * 0.02 * 420) / (math.sqrt(21)) * d
        doc.add_paragraph(f"• Ld/Traslapo Barra Principal (Ø{rebar_diam:.1f}mm): {ld_mm(rebar_diam)/10:.0f} cm (Tracción A)")
        doc.add_paragraph(f"• Gancho Sísmico Estribo (Ø{stirrupdiam_saf:.1f}mm): A 135°, Extensión libre 6db={max(80.0, 6.0*stirrupdiam_saf)/10:.1f} cm")

        
        # 7. Detalles Generales (Imágenes DOCX)
        doc.add_heading("7. PLANOS Y DETALLES CONSTRUCTIVOS", level=1)
        if 'fig_sec' in locals():
            try:
                import io as _io_sec
                buf_sec = _io_sec.BytesIO()
                _orig_sec = fig_sec.get_facecolor()
                fig_sec.patch.set_facecolor('white')
                fig_sec.patch.set_alpha(1.0)
                for _ax in fig_sec.get_axes():
                    _ax.set_facecolor('white')
                fig_sec.savefig(buf_sec, facecolor='white', edgecolor='none', format='png', dpi=200,
                                bbox_inches='tight', transparent=False)
                buf_sec.seek(0)
                fig_sec.patch.set_facecolor(_orig_sec)
                doc.add_picture(buf_sec, width=Inches(4.5))
                buf_sec.close()
            except Exception: pass
                
        try:
            import io as _io_l1
            hook_len_cm = 12 * rebar_diam / 10
            straight_len_cm = long_bar_m * 100 - 2 * hook_len_cm
            fig_l1_mem = draw_longitudinal_bar(long_bar_m*100, straight_len_cm,
                                               hook_len_cm, rebar_diam, _bar_label(rebar_diam))
            configurar_pdf_comercial(fig_l1_mem)
            buf_l1 = _io_l1.BytesIO()
            fig_l1_mem.savefig(buf_l1, facecolor='white', format='png', dpi=200,
                               bbox_inches='tight', transparent=False)
            buf_l1.seek(0)   # <-- seek obligatorio para que DOCX lo lea
            plt.close(fig_l1_mem)
            doc.add_picture(buf_l1, width=Inches(5))
            buf_l1.close()
        except Exception as _e_l1:
            doc.add_paragraph(f'[Barra longitudinal: {_e_l1}]')

        if not es_circular:
            try:
                import io as _io_e1
                inside_b = b - 2 * recub_cm
                inside_h = h - 2 * recub_cm
                hook_len_est = 12 * stirrupdiam_saf / 10
                fig_e1_mem = draw_stirrup(inside_b, inside_h, hook_len_est,
                                          stirrupdiam_saf, _bar_label(stirrupdiam_saf))
                configurar_pdf_comercial(fig_e1_mem)
                buf_e1 = _io_e1.BytesIO()
                fig_e1_mem.savefig(buf_e1, facecolor='white', format='png', dpi=200,
                                   bbox_inches='tight', transparent=False)
                buf_e1.seek(0)   # <-- seek obligatorio
                plt.close(fig_e1_mem)
                doc.add_picture(buf_e1, width=Inches(3.5))
                buf_e1.close()
            except Exception as _e_e1:
                doc.add_paragraph(f'[Estribo: {_e_e1}]')
            
        doc.add_heading("8. REFERENCIAS NORMATIVAS", level=1)
        _refs = [
            (f"{coderef} — Flexocompresión",   "Hipótesis de diseño — distribución lineal de deformaciones"),
            (f"{coderef} — Cuantías",           "Límites de cuantía: ρ_min=1%, ρ_max según nivel sísmico y norma activa"),
            (f"{coderef} — Esbeltez",           "Efectos de esbeltez — método de magnificación de momentos δns (no-sway)"),
            (f"{coderef} — Factor δns",         "Factor δns = Cm/(1 − Pu/0.75Pc) ≥ 1.0  |  Para sway: usar análisis P-Δ directo"),
            ("NSR-10 C.21.6.3",  "Cuantía máxima zona de rótula plástica — DES: ρ ≤ 4%"),
            ("NSR-10 C.21.6.4",  "Confinamiento en columnas — zona de rótula plástica"),
            ("NSR-10 C.21.6.4.1","Lo_min = max(h, b, Lu/6, 45 cm)"),
            ("NSR-10 C.21.6.4.2","Diámetro mínimo estribo: No. 3 (Ø9.53 mm)"),
            ("NSR-10 C.21.6.4.3","Separación zona confinada: min(8db, 24dst, b/3, 15cm, 6db)"),
            ("NSR-10 C.21.6.4.4","Área mínima estribos Ash — Ec. C.21-4 y C.21-5"),
            ("ACI 318-19 §22.4.2.1","Pn,max = 0.80·Po (estribos rectangulares)"),
            ("ACI 318-19 §22.4.2.2","Pn,max = 0.85·Po (espiral continua)"),
            ("ACI 318-19 §25.7.2","Cálculo Ash para confinamiento con hoop ties"),
            ("ACI 318-19 §25.7.3","Requisitos para refuerzo en espiral continua"),
            ("Bresler (1960)",    "Método recíproco biaxial: 1/Pni = 1/Pnx + 1/Pny − 1/Po"),
            ("ICONTEC NTC 2289", "Dibujo técnico — plumas, escalas y rótulos para planos de construcción"),
        ]
        for _art, _desc in _refs:
            _p = doc.add_paragraph(style='List Bullet')
            _p.add_run(f"{_art}: ").bold = True
            _p.add_run(_desc)

        doc_mem = io.BytesIO()
        doc.save(doc_mem)
        doc_mem.seek(0)

        st.success(_t("Memoria Generada (Estándar N4 Light-Mode)", "Report generated successfully."))
        st.download_button(label=_t("Descargar Memoria DOCX", "Download DOCX Report"),
                           data=doc_mem, file_name=f"Memoria_Columna_{b:.0f}x{h:.0f}_N4.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    st.markdown("---")
    st.subheader(_t("Exportar Verificaciones a Excel", "Export Verifications to Excel"))
    if st.button(_t("Exportar a Excel", "Export to Excel")):
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df_verif = pd.DataFrame({
                "Verificación": ["Cuantía", "Biaxial", "Esbeltez", "Ash", "Lo_conf", "Separación"],
                "Valor": [f"{cuantia:.2f}%", f"{bresler['ratio']:.3f}", f"{slenderness['kl_r']:.1f}", 
                          f"{Ash_prov:.3f}/{Ash_req:.3f}" if not es_circular else f"{rho_s_prov:.4f}/{rho_s_req:.4f}",
                          f"{Lo_conf:.1f} cm requerido" if not es_circular else "N/A", f"{s_conf:.1f}" if not es_circular else f"{paso_espiral:.1f}"],
                "Límite": [f"{rho_min}% - {rho_max}%", "≤ 1.0", "≤ 22", "≥ 1.0", "≥ max(b,h,L/6,45)", "≤ 15/20"],
                "Cumple": ["SÍ" if rho_min <= cuantia <= rho_max else "NO",
                           "SÍ" if bresler['ok'] else "NO",
                           "SÍ" if slenderness['kl_r'] <= 22 else "NO",
                           "SÍ" if ash_ok else "NO",
                           "SÍ (por diseño)" if not es_circular else "SÍ",
                           "SÍ" if s_conf <= 15.0 or (es_dmo and s_conf <= 15.0) else "NO"]
            })
            df_verif.to_excel(writer, sheet_name='Verificaciones', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Verificaciones']
            green_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
            red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            for row, val in enumerate(df_verif["Cumple"], start=2):
                cell = f"D{row}"
                if val == "SÍ":
                    worksheet.write(cell, val, green_format)
                else:
                    worksheet.write(cell, val, red_format)
            df_despiece.to_excel(writer, sheet_name='Despiece', index=False)
            df_cant = pd.DataFrame({
                "Material": ["Concreto", "Acero Longitudinal", "Acero Estribos", "Acero Total"],
                "Cantidad": [vol_concreto_m3, peso_acero_long_kg, peso_total_estribos_kg, peso_total_acero_kg],
                "Unidad": ["m³", "kg", "kg", "kg"]
            })
            df_cant.to_excel(writer, sheet_name='Cantidades', index=False)
        excel_buffer.seek(0)
        st.download_button(label=_t("Descargar Excel", "Download Excel"),
                           data=excel_buffer, file_name=f"Verificaciones_Columna_{b:.0f}x{h:.0f}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                           
    st.markdown("---")
    st.subheader("Transferir al Presupuesto WBS")
    st.caption("Envia el volumen de concreto y el acero calculado directamente al arbol WBS de la Calculadora de Materiales.")
    
    _wbs_list = st.session_state.get("presupuesto_wbs", [])
    _apus_dict = st.session_state.get("catalogo_apus", {})
    lista_caps = [c["Capitulo"] for c in _wbs_list]
    
    if not lista_caps:
        st.warning("Aun no hay capitulos en el Presupuesto WBS. Ve a la pagina 'Calculadora de Materiales' -> Tab '1. Presupuesto (WBS)' y crea un capitulo primero.")
    elif not _apus_dict:
        st.warning("El catalogo de APUs esta vacio. Ve a 'Calculadora de Materiales' -> Tab '3. Gestor de APUs'.")
    else:
        col_wbs1, col_wbs2 = st.columns([1, 1])
        
        with col_wbs1:
            st.markdown("**1. Enviar Volumen de Concreto**")
            st.metric("Volumen calculado", f"{vol_concreto_m3:.3f} m³")
            dest_cap_c = st.selectbox("Capitulo destino", lista_caps, key="wbs_cap_col_c")
            dest_apu_c = st.selectbox("APU a aplicar", list(_apus_dict.keys()),
                                       format_func=lambda x: _apus_dict[x]["Nombre"], key="wbs_apu_col_c")
            btn_wbs_c = st.button("Enviar Concreto al WBS", type="primary", use_container_width=True, key="btn_send_conc_col")

        with col_wbs2:
            st.markdown("**2. Enviar Acero de Refuerzo**")
            st.metric("Acero total calculado", f"{peso_total_acero_kg:.1f} kg")
            dest_cap_s = st.selectbox("Capitulo destino", lista_caps, key="wbs_cap_col_s")
            dest_apu_s = st.selectbox("APU a aplicar", list(_apus_dict.keys()),
                                       format_func=lambda x: _apus_dict[x]["Nombre"], key="wbs_apu_col_s")
            btn_wbs_s = st.button("Enviar Acero al WBS", type="primary", use_container_width=True, key="btn_send_acero_col")

        if btn_wbs_c:
            _transferido = False
            for cap in st.session_state["presupuesto_wbs"]:
                if cap["Capitulo"] == dest_cap_c:
                    nid = f"{len(cap['Items'])+1:03d}"
                    cap["Items"].append({"ID_Item": nid, "ID_APU": dest_apu_c,
                                         "Cantidad": float(vol_concreto_m3), "Predecesora": ""})
                    _transferido = True
                    break
            if _transferido:
                st.success(f"Concreto ({vol_concreto_m3:.3f} m3) enviado al capitulo '{dest_cap_c}'. Ve a la Calculadora de Materiales -> Tab WBS para verlo.")
            else:
                st.error("No se encontro el capitulo seleccionado en session_state.")

        if btn_wbs_s:
            _transferido = False
            for cap in st.session_state["presupuesto_wbs"]:
                if cap["Capitulo"] == dest_cap_s:
                    nid = f"{len(cap['Items'])+1:03d}"
                    cap["Items"].append({"ID_Item": nid, "ID_APU": dest_apu_s,
                                         "Cantidad": float(peso_total_acero_kg), "Predecesora": ""})
                    _transferido = True
                    break
            if _transferido:
                st.success(f"Acero ({peso_total_acero_kg:.1f} kg) enviado al capitulo '{dest_cap_s}'. Ve a la Calculadora de Materiales -> Tab WBS para verlo.")
            else:
                st.error("No se encontro el capitulo seleccionado en session_state.")

