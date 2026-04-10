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

st.title(_t("Diseño de Dados (Encepados) - ACI 318 / NSR-10", "Pile Cap Design - ACI 318 / NSR-10"))
st.markdown(_t(
    "<p style='margin:0; padding:0; color:#aaa; font-size:14px;'>Módulo integral ACI-318 (Flexión, Punzonamiento Columna, Punzonamiento Pilote, Bielas y Tirantes).</p><hr>",
    "<p style='margin:0; padding:0; color:#aaa; font-size:14px;'>Comprehensive ACI-318 module (Flexure, Column Punching, Pile Punching, Strut and Tie).</p><hr>"
), unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header(_t("Configuración Global", "Global Settings"))
    
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
    st.subheader(_t("Análisis ACI 318 Seccional (Cortante y Flexión)", "ACI 318 Sectional Analysis (Shear and Flexure)"))
    
    d_m = H_dado - 0.10 # Asumiendo ~10cm al baricentro inferior del acero
    c1_m = c1_col / 100.0
    c2_m = c2_col / 100.0
    
    c_des1, c_des2, c_des3 = st.columns(3)
    
    # ─── 1. PUNZONAMIENTO COLUMNA CENTRAL ──────────────────────────
    b_o = 2 * ((c1_m + d_m) + (c2_m + d_m))
    Vu_punz = Pu
    # Reducción por pilotes dentro del perímetro crítico
    for idx, r in df_pilotes.iterrows():
        if abs(r["X [m]"]) <= (c1_m/2 + d_m/2) and abs(r["Y [m]"]) <= (c2_m/2 + d_m/2):
            Vu_punz -= r["Carga Axial P_ui [kN]"]
            
    beta_c = max(c1_col, c2_col) / max(min(c1_col, c2_col), 1)
    alpha_s = 40 # Columna Interior
    vc1 = 0.33 * math.sqrt(fc_dado)
    vc2 = 0.17 * (1 + 2/beta_c) * math.sqrt(fc_dado)
    vc3 = 0.083 * (2 + alpha_s * d_m / b_o) * math.sqrt(fc_dado)
    
    phiVc_punz = 0.75 * min(vc1, vc2, vc3) * 1000 * b_o * d_m
    ok_punz = phiVc_punz >= Vu_punz
    
    with c_des1:
        st.write("### Punzonamiento Columna")
        st.metric("Vu actuante", f"{Vu_punz:.1f} kN")
        st.metric("φVc resistente", f"{phiVc_punz:.1f} kN")
        if ok_punz: st.success("CUMPLE (Vu ≤ φVc)")
        else: st.error("FALLA EL PERALTE")
        
    # ─── 2. CORTANTE UNIDIRECCIONAL (VIGA) ─────────────────────────
    Vu_vx = 0; Vu_vy = 0
    for idx, r in df_pilotes.iterrows():
        # Pilotes ubicados a una distancia mayor a "d" desde la cara de la columna
        if r["X [m]"] > (c1_m/2 + d_m): Vu_vx += r["Carga Axial P_ui [kN]"]
        if r["Y [m]"] > (c2_m/2 + d_m): Vu_vy += r["Carga Axial P_ui [kN]"]
        
    phiVc_vx = 0.75 * 0.17 * math.sqrt(fc_dado) * 1000 * L_sugerido * d_m
    phiVc_vy = 0.75 * 0.17 * math.sqrt(fc_dado) * 1000 * B_sugerido * d_m
    ok_vx = phiVc_vx >= Vu_vx
    ok_vy = phiVc_vy >= Vu_vy
    
    with c_des2:
        st.write("### Cortante Unidireccional")
        st.metric("Vu (Cara X) a distr. d", f"{Vu_vx:.1f} kN")
        st.write(f"φVc Resistencia = {phiVc_vx:.1f} kN {'✅' if ok_vx else '❌'}")
        st.metric("Vu (Cara Y) a distr. d", f"{Vu_vy:.1f} kN")
        st.write(f"φVc Resistencia = {phiVc_vy:.1f} kN {'✅' if ok_vy else '❌'}")

    # ─── 3. FLEXIÓN Y ACERO DE REFUERZO ────────────────────────────
    Mu_flex_x = 0; Mu_flex_y = 0
    for idx, r in df_pilotes.iterrows():
        # Extremos en X e Y evaluados en la cara de la columna
        if r["X [m]"] > c1_m/2: Mu_flex_x += r["Carga Axial P_ui [kN]"] * (r["X [m]"] - c1_m/2)
        if r["Y [m]"] > c2_m/2: Mu_flex_y += r["Carga Axial P_ui [kN]"] * (r["Y [m]"] - c2_m/2)
        
    def req_as(Mu_kNm, b_m, d_mf):
        if Mu_kNm <= 0: return 0.0
        Mn = Mu_kNm / 0.90
        R = Mn / (b_m * d_mf**2 * 1000)
        val = 1 - 2*R/(0.85*fc_dado)
        if val < 0: return 9999.9 # Compresión falla
        rho = (0.85 * fc_dado / fy_acero) * (1 - math.sqrt(val))
        rho_min = max(0.25*math.sqrt(fc_dado)/fy_acero, 1.4/fy_acero)
        rho_use = max(rho, rho_min)
        return rho_use * (b_m*100) * (d_mf*100)
        
    As_x = req_as(Mu_flex_x, L_sugerido, d_m)
    As_y = req_as(Mu_flex_y, B_sugerido, d_m)
    
    with c_des3:
        st.write("### Flexión y Acero (As)")
        st.metric("Momento Mu,x (Cara Y)", f"{Mu_flex_x:.1f} kN.m")
        st.write(f"**As Requerido en X:** {As_x:.1f} cm²")
        st.metric("Momento Mu,y (Cara X)", f"{Mu_flex_y:.1f} kN.m")
        st.write(f"**As Requerido en Y:** {As_y:.1f} cm²")
        
    # Método Puntal y Tensor (Alerta)
    st.markdown("---")
    st.write("#### ⚠️ Revisión Básica de Bielas y Tirantes (STM - ACI 318 Cap 23)")
    # Si la relación entre la distancia eje-pilar y peralte es menor a 2, rige STM
    max_dist = max([math.sqrt(r["X [m]"]**2 + r["Y [m]"]**2) for _, r in df_pilotes.iterrows()]) if n_pil > 0 else 0
    if max_dist < 2 * d_m:
        st.warning("La distancia desde los pilotes a la columna es menor a 2d. Este dado es rígido/profundo. ACI 318 exige diseño predominante usando **Bielas y Tirantes (STM)** en lugar de flexión plana clásica.")
    else:
        st.success("La distancia supera los 2d. El diseño convencional de vigas/losas (Flexión/Cortante) rige de manera precisa.")

with tab_bim:
    st.subheader(_t("Integración BIM 3D", "BIM 3D Integration"))
    
    if _PLOTLY_AVAILABLE:
        fig3d = go.Figure()
        
        # 1. Dado (Pile Cap) - Caja Semitransparente
        Bx2 = B_sugerido / 2
        Ly2 = L_sugerido / 2
        hd = H_dado
        
        x_dado = [-Bx2, Bx2, Bx2, -Bx2, -Bx2, Bx2, Bx2, -Bx2]
        y_dado = [-Ly2, -Ly2, Ly2, Ly2, -Ly2, -Ly2, Ly2, Ly2]
        z_dado = [0, 0, 0, 0, -hd, -hd, -hd, -hd]
        
        fig3d.add_trace(go.Mesh3d(
            x=x_dado, y=y_dado, z=z_dado,
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color='lightblue', opacity=0.3, name='Concreto Encepado'
        ))
        
        # 2. Columna
        c1x = c1_m / 2; c2y = c2_m / 2; hc = 1.0
        x_col = [-c1x, c1x, c1x, -c1x, -c1x, c1x, c1x, -c1x]
        y_col = [-c2y, -c2y, c2y, c2y, -c2y, -c2y, c2y, c2y]
        z_col = [hc, hc, hc, hc, 0, 0, 0, 0]
        fig3d.add_trace(go.Mesh3d(
            x=x_col, y=y_col, z=z_col,
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color='gray', opacity=1.0, name='Columna'
        ))
        
        # 3. Pilotes
        L_render = 3.0 # Longitud visual demostrativa
        for idx, r in df_pilotes.iterrows():
            px = r["X [m]"]
            py = r["Y [m]"]
            z_top_pil = -(H_dado - embeb_pilote)
            
            theta = np.linspace(0, 2*np.pi, 16)
            z_cil = np.linspace(z_top_pil, z_top_pil - L_render, 2)
            Tc, Zc = np.meshgrid(theta, z_cil)
            Xc = px + (D_pilote/2) * np.cos(Tc)
            Yc = py + (D_pilote/2) * np.sin(Tc)
            
            fig3d.add_trace(go.Surface(
                x=Xc, y=Yc, z=Zc, 
                colorscale=[[0, '#8d6e63'], [1, '#8d6e63']], 
                showscale=False, opacity=0.9, name=f'Pilote {r["ID"]}'
            ))
            
        # 4. Canasta de Acero (Parrilla Inferior y Superior realistas)
        z_inf = -H_dado + embeb_pilote + 0.03  # Se sienta 3cm sobre las cabezas de los pilotes
        z_sup = -0.07  # Recubrimiento superior de 7cm
        
        espacio_barras = 0.25  # Simulando barras principales cada 25cm
        color_acero = '#b0bec5' # Gris acero en lugar de naranja chillón
        
        y_bars = np.arange(-Ly2 + 0.15, Ly2 - 0.15 + espacio_barras, espacio_barras)
        x_bars = np.arange(-Bx2 + 0.15, Bx2 - 0.15 + espacio_barras, espacio_barras)
        
        # --- Parrilla Inferior ---
        for yp in y_bars:
            fig3d.add_trace(go.Scatter3d(x=[-Bx2+0.1, Bx2-0.1], y=[yp, yp], z=[z_inf, z_inf], mode='lines', line=dict(color=color_acero, width=3), showlegend=False))
        for xp in x_bars:
            # En la vida real cruzan una sobre otra
            fig3d.add_trace(go.Scatter3d(x=[xp, xp], y=[-Ly2+0.1, Ly2-0.1], z=[z_inf + 0.02, z_inf + 0.02], mode='lines', line=dict(color=color_acero, width=3), showlegend=False))
            
        # --- Parrilla Superior ---
        for yp in y_bars:
            fig3d.add_trace(go.Scatter3d(x=[-Bx2+0.1, Bx2-0.1], y=[yp, yp], z=[z_sup, z_sup], mode='lines', line=dict(color=color_acero, width=3), showlegend=False))
        for xp in x_bars:
            fig3d.add_trace(go.Scatter3d(x=[xp, xp], y=[-Ly2+0.1, Ly2-0.1], z=[z_sup - 0.02, z_sup - 0.02], mode='lines', line=dict(color=color_acero, width=3), showlegend=False))
            
        fig3d.update_layout(
            scene=dict(
                xaxis=dict(title="X [m]", range=[-B_sugerido*1.2, B_sugerido*1.2]),
                yaxis=dict(title="Y [m]", range=[-L_sugerido*1.2, L_sugerido*1.2]),
                zaxis=dict(title="Z [m]"),
                aspectmode='data'
            ),
            height=600, margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="#1e2530", font=dict(color="white")
        )
        st.plotly_chart(fig3d, use_container_width=True)
        
    else:
        st.error("Plotly no disponible.")
