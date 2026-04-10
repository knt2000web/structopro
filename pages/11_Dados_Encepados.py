import streamlit as st
import pandas as pd
import numpy as np
import math
import io
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Plotly
try:
    import plotly.graph_objects as go
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False

# Librerías opcionales
try:
    from docx import Document
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

try:
    import ezdxf
    _DXF_AVAILABLE = True
except ImportError:
    _DXF_AVAILABLE = False

try:
    import ifcopenshell
    _IFC_AVAILABLE = True
except ImportError:
    _IFC_AVAILABLE = False

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es
# ─────────────────────────────────────────────

st.set_page_config(page_title=_t("Dados de Pilotes (Encepados)", "Pile Caps"), layout="wide")

st.title(_t("🏗️ Diseño de Dados (Encepados) - ACI 318 / NSR-10", "🏗️ Pile Cap Design - ACI 318 / NSR-10"))
st.markdown(_t(
    "<p style='margin:0; padding:0; color:#aaa; font-size:14px;'>Módulo integral ACI-318 (Flexión, Punzonamiento Columna, Punzonamiento Pilote, Bielas y Tirantes).</p><hr>",
    "<p style='margin:0; padding:0; color:#aaa; font-size:14px;'>Comprehensive ACI-318 module (Flexure, Column Punching, Pile Punching, Strut and Tie).</p><hr>"
), unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header(_t("⚙️ Configuración Global", "⚙️ Global Settings"))
    
    # 1. Configuración de Materiales
    with st.expander(_t("1. Materiales", "1. Materials"), expanded=True):
        fc_dado = st.number_input(_t("f'c Concreto Dado (MPa)", "f'c Cap Concrete (MPa)"), min_value=21.0, value=28.0, step=1.0)
        fy_acero = st.number_input(_t("fy Acero (MPa)", "fy Steel (MPa)"), min_value=240.0, value=420.0, step=10.0)
        peso_conc = st.number_input(_t("Peso Concreto (kN/m³)", "Concrete Weight (kN/m³)"), min_value=20.0, value=24.0, step=0.5)

    # 2. Geometría de Pilotes Internos
    with st.expander(_t("2. Pilotes Relacionados", "2. Related Piles"), expanded=True):
        D_pilote = st.number_input(_t("Diámetro del Pilote (m)", "Pile Diameter (m)"), min_value=0.20, value=0.60, step=0.05)
        Q_adm_pilote = st.number_input(_t("Q_adm Pilote Existente (kN)", "Existing Pile Q_adm (kN)"), min_value=100.0, value=1500.0, step=100.0)
        embeb_pilote = st.number_input(_t("Embebido Pilote en Dado (m)", "Pile Embedment (m)"), min_value=0.05, value=0.10, step=0.05)

    # 3. Geometría de la Columna
    with st.expander(_t("3. Geometría Columna", "3. Column Geometry"), expanded=True):
        c1_col = st.number_input(_t("Dimensión Cx (cm)", "Dimension Cx (cm)"), min_value=20.0, value=50.0, step=5.0)
        c2_col = st.number_input(_t("Dimensión Cy (cm)", "Dimension Cy (cm)"), min_value=20.0, value=50.0, step=5.0)
    
    # 4. Solicitaciones (Cargas en Base de Columna)
    with st.expander(_t("4. Solicitaciones (Diseño)", "4. Loads (Design)"), expanded=True):
        st.markdown(_t("*Cargas Últimas Mayoradas*", "*Factored Ultimate Loads*"))
        Pu = st.number_input(_t("Carga Axial Pu (kN)", "Axial Load Pu (kN)"), min_value=0.0, value=4500.0, step=100.0)
        Mux = st.number_input(_t("Momento Mux (kN.m)", "Moment Mux (kN.m)"), value=250.0, step=50.0)
        Muy = st.number_input(_t("Momento Muy (kN.m)", "Moment Muy (kN.m)"), value=150.0, step=50.0)

# ─────────────────────────────────────────────
# CUERPO PRINCIPAL (TABS)
# ─────────────────────────────────────────────
tab_geo, tab_des, tab_bim = st.tabs([
    _t("1. Configuración de Grupo", "1. Group Configuration"),
    _t("2. Punzonamiento y Flexión", "2. Punching & Flexure"),
    _t("3. Planos y BIM", "3. Drawings & BIM")
])

with tab_geo:
    st.subheader(_t("1.1 Parámetros del Encepado", "1.1 Pile Cap Parameters"))
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        plantilla = st.selectbox(_t("Disposición Paramétrica", "Parametric Layout"), [
            "2 Pilotes (Rectangular)", 
            "3 Pilotes (Triangular)", 
            "4 Pilotes (Cuadrícula)",
            "5 Pilotes (Dado + Central)",
            "6 Pilotes (Rectangular 3x2)"
        ], index=2)
        S_pilote = st.number_input(_t("Separación entre centros S (m)", "Center Spacing S (m)"), min_value=D_pilote*2, value=max(D_pilote*3, 1.0), step=0.1)

    with col_d2:
        H_dado = st.number_input(_t("Espesor del Dado H (m)", "Cap Thickness H (m)"), min_value=0.4, value=1.0, step=0.1)
        # B y L dependerán de la plantilla + voladizo
        voladizo = st.number_input(_t("Voladizo del Borde a centro de Pilote (m)", "Edge Overhang from Pile center (m)"), min_value=0.3, value=max(0.5, D_pilote/2 + 0.15), step=0.05)
    
    tipo_dado = plantilla.split(" ")[0]
    
    pilotes = []
    if tipo_dado == "2":
        pilotes = [(-S_pilote/2, 0), (S_pilote/2, 0)]
    elif tipo_dado == "3":
        R = S_pilote / math.sqrt(3)
        h_ap = R / 2
        pilotes = [(0, R), (-S_pilote/2, -h_ap), (S_pilote/2, -h_ap)]
    elif tipo_dado == "4":
        pilotes = [(-S_pilote/2, S_pilote/2), (S_pilote/2, S_pilote/2), (-S_pilote/2, -S_pilote/2), (S_pilote/2, -S_pilote/2)]
    elif tipo_dado == "5":
        pilotes = [(-S_pilote/2, S_pilote/2), (S_pilote/2, S_pilote/2), (-S_pilote/2, -S_pilote/2), (S_pilote/2, -S_pilote/2), (0, 0)]
    elif tipo_dado == "6":
        pilotes = [
            (-S_pilote, S_pilote/2), (0, S_pilote/2), (S_pilote, S_pilote/2),
            (-S_pilote, -S_pilote/2), (0, -S_pilote/2), (S_pilote, -S_pilote/2)
        ]
        
    n_pil = len(pilotes)
    xs = [p[0] for p in pilotes]
    ys = [p[1] for p in pilotes]
    
    B_sugerido = (max(xs) - min(xs)) + 2 * voladizo
    L_sugerido = (max(ys) - min(ys)) + 2 * voladizo
    
    st.markdown("---")
    st.subheader(_t("1.2 Cinemática Rígida y Geometría Generada", "1.2 Rigid Kinematics and Generated Geometry"))
    
    # Cinemática: Pi = P/n ± My*x / sum(x^2) ± Mx*y / sum(y^2)
    sum_x2 = sum(x**2 for x in xs)
    sum_y2 = sum(y**2 for y in ys)
    
    P_unit = Pu / n_pil
    
    res_pilotes = []
    max_pu_pilote = 0.0
    for i, (x, y) in enumerate(pilotes):
        P_my = (Muy * x / sum_x2) if sum_x2 > 0 else 0
        P_mx = (Mux * y / sum_y2) if sum_y2 > 0 else 0
        Pi = P_unit + P_my + P_mx
        
        max_pu_pilote = max(max_pu_pilote, Pi)
        estado = "✅ OK" if Pi <= Q_adm_pilote else "❌ EXCESO"
        res_pilotes.append({
            "ID": f"P{i+1}", 
            "X [m]": round(x, 2), 
            "Y [m]": round(y, 2), 
            "Carga Axial P_ui [kN]": round(Pi, 1), 
            "Estado": estado
        })
    
    df_pilotes = pd.DataFrame(res_pilotes)
    
    c_g1, c_g2 = st.columns([1.5, 2])
    with c_g1:
        st.write(f"**Dimensiones Encepado:** Ancho B={B_sugerido:.2f}m | Largo L={L_sugerido:.2f}m")
        st.write(f"**Reacción Máxima por Pilote:** {max_pu_pilote:.1f} kN (Límite: {Q_adm_pilote} kN)")
        st.dataframe(df_pilotes, use_container_width=True)
        if max_pu_pilote > Q_adm_pilote:
            st.error(_t(f"¡PELIGRO! La carga de {max_pu_pilote:.1f} kN excede la Capacidad Admisible Geotécnica. Aumente la separación del grupo o dimensiones.", f"DANGER! The load of {max_pu_pilote:.1f} kN exceeds Geotechnical Bearing Capacity."))
            
    with c_g2:
        if _PLOTLY_AVAILABLE:
            fig_geo = go.Figure()
            # Bounding box del dado
            fig_geo.add_shape(type="rect", x0=min(xs)-voladizo, y0=min(ys)-voladizo, x1=max(xs)+voladizo, y1=max(ys)+voladizo, line=dict(color="cyan", width=2))
            # Columna
            fig_geo.add_shape(type="rect", x0=-c1_col/200, y0=-c2_col/200, x1=c1_col/200, y1=c2_col/200, line=dict(color="orange", width=2), fillcolor="orange", opacity=0.5)
            
            # Pilotes
            for idx, r in df_pilotes.iterrows():
                color_p = "green" if "OK" in r["Estado"] else "red"
                fig_geo.add_shape(type="circle", x0=r["X [m]"]-D_pilote/2, y0=r["Y [m]"]-D_pilote/2, x1=r["X [m]"]+D_pilote/2, y1=r["Y [m]"]+D_pilote/2, line=dict(color=color_p, width=2), fillcolor=color_p, opacity=0.3)
                fig_geo.add_annotation(x=r["X [m]"], y=r["Y [m]"], text=f"<b>{r['ID']}</b><br>{r['Carga Axial P_ui [kN]']} kN", showarrow=False, font=dict(color="white", size=10))
            
            fig_geo.update_layout(title="Distribución Cinemática en Planta", xaxis=dict(scaleanchor="y", scaleratio=1, title="X [m]"), yaxis=dict(title="Y [m]"), height=450, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="#1e2530", plot_bgcolor="#1e2530", font=dict(color="white"))
            st.plotly_chart(fig_geo, use_container_width=True)

with tab_des:
    st.subheader(_t("Análisis ACI 318 Seccional", "ACI 318 Sectional Analysis"))
    st.info(_t("Próximamente: Chequeos de Punzonamiento de Columna, Punzonamiento de Pilote y Momentos de Flexión...", "Coming soon: Column Punching, Pile Punching, and Bending Moments..."))

with tab_bim:
    st.subheader(_t("Salidas Gráficas y BIM", "Graphical and BIM Outputs"))
    st.info(_t("Próximamente: DXF y visor 3D paramétrico.", "Coming soon: DXF and parametric 3D viewer."))
