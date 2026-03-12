import streamlit as st
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es

st.set_page_config(page_title=_t("Resistencia de Materiales", "Strength of Materials"), layout="wide")
st.title(_t("🏗️ Resistencia de Materiales", "🏗️ Mechanics of Materials"))
st.markdown(_t("Análisis de Esfuerzos Secundarios y Propiedades Geométricas Universales.", 
               "Secondary Stress Analysis and Universal Geometric Properties."))

tab_mohr, tab_centroide = st.tabs([
    _t("⭕ 1. Círculo de Mohr (Transf. Esfuerzos)", "⭕ 1. Mohr's Circle (Stress Transf.)"),
    _t("📐 2. Centroides e Inercias (Secc. Compuestas)", "📐 2. Centroids & Inertias (Composite Sections)")
])

# ─────────────────────────────────────────────
# TAB 1: CÍRCULO DE MOHR
# ─────────────────────────────────────────────
with tab_mohr:
    st.header(_t("Círculo de Mohr para Estado Plano de Esfuerzos", "Mohr's Circle for Plane Stress State"))
    
    col_m1, col_m2, col_m3 = st.columns([1, 1, 1.5])
    with col_m1:
        st.subheader(_t("Esfuerzos Iniciales", "Initial Stresses"))
        sig_x = st.number_input(r"$\sigma_x$ (tracción +, comp -)", -1000.0, 1000.0, 50.0)
        sig_y = st.number_input(r"$\sigma_y$ (tracción +, comp -)", -1000.0, 1000.0, -10.0)
        tau_xy = st.number_input(r"$\tau_{xy}$ (corte)", -1000.0, 1000.0, 40.0)
        unidades_m = st.selectbox(_t("Unidades", "Units"), ["MPa", "psi", "ksi", "kgf/cm²"])
        
    # Calculos Mohr
    sig_avg = (sig_x + sig_y) / 2.0
    R = np.sqrt(((sig_x - sig_y)/2.0)**2 + tau_xy**2)
    sig_1 = sig_avg + R
    sig_2 = sig_avg - R
    tau_max = R
    
    if (sig_x - sig_y) != 0: theta_p1_rad = np.arctan2(2*tau_xy, (sig_x - sig_y)) / 2.0
    else: theta_p1_rad = np.pi/4 if tau_xy > 0 else -np.pi/4
    
    theta_p1_deg = np.degrees(theta_p1_rad)
    theta_p2_deg = theta_p1_deg + 90.0
    theta_s_deg = theta_p1_deg - 45.0
    
    with col_m2:
        st.subheader(_t("Esfuerzos Principales", "Principal Stresses"))
        st.markdown(f"**$\sigma_1$ (Máximo):** {sig_1:.2f} {unidades_m}")
        st.markdown(f"**$\sigma_2$ (Mínimo):** {sig_2:.2f} {unidades_m}")
        st.markdown(f"**$\tau_{{max}}$ (Corte Máx):** {tau_max:.2f} {unidades_m}")
        st.markdown(f"**Centro ($\sigma_{{avg}}$):** {sig_avg:.2f} {unidades_m}")
        st.markdown(f"**$\theta_{{p1}}$ (Plano Ppal 1):** {theta_p1_deg:.2f}°")
        st.markdown(f"**$\theta_{{p2}}$ (Plano Ppal 2):** {theta_p2_deg:.2f}°")
        st.markdown(f"**$\theta_{{s}}$ (Corte Máx):** {theta_s_deg:.2f}°")
        
    with col_m3:
        # Gráfica Plotly
        theta = np.linspace(0, 2*np.pi, 200)
        x_circle = sig_avg + R * np.cos(theta)
        y_circle = R * np.sin(theta)
        
        fig_mohr = go.Figure()
        # El circulo
        fig_mohr.add_trace(go.Scatter(x=x_circle, y=y_circle, mode='lines', name=_t('Círculo Mohr', 'Mohr Circle'), line=dict(color='blue')))
        # Eje Sigma (x) y Tau (y)
        fig_mohr.add_hline(y=0, line_color="black", line_width=1)
        fig_mohr.add_vline(x=0, line_color="black", line_width=1)
        # Puntos clave
        fig_mohr.add_trace(go.Scatter(x=[sig_x, sig_y], y=[-tau_xy, tau_xy], mode='markers+lines', name=_t('Estado Inicial', 'Initial State'), marker=dict(size=10, color='red'), line=dict(dash='dash', color='red')))
        fig_mohr.add_trace(go.Scatter(x=[sig_avg], y=[0], mode='markers', name=_t('Centro', 'Center'), marker=dict(size=8, color='black')))
        fig_mohr.add_trace(go.Scatter(x=[sig_1, sig_2], y=[0, 0], mode='markers', name=_t('Esf. Principales', 'Principal Stresses'), marker=dict(size=10, color='green')))
        fig_mohr.add_trace(go.Scatter(x=[sig_avg, sig_avg], y=[tau_max, -tau_max], mode='markers', name=_t('Tau Max', 'Max Tau'), marker=dict(size=10, color='purple')))
        
        fig_mohr.update_layout(title=_t("Círculo de Mohr Interactivo", "Interactive Mohr's Circle"), 
                               xaxis_title=rf"$\sigma$ Normal [{unidades_m}]", 
                               yaxis_title=rf"$\tau$ Cortante [{unidades_m}] (Abajo + según convención)",
                               yaxis=dict(autorange="reversed"), # Convención clásica: tau positivo hacia abajo en Mohrr
                               plot_bgcolor='white', hovermode="x")
        st.plotly_chart(fig_mohr, use_container_width=True)

# ─────────────────────────────────────────────
# TAB 2: CENTROIDES E INERCIAS
# ─────────────────────────────────────────────
with tab_centroide:
    st.header(_t("Cálculo de Propiedades de Secciones Compuestas", "Composite Section Properties Calculation"))
    st.write(_t("Utilice el sistema global de coordenadas. Añada figuras simples para ensamblar su sección (puede usar anchos o altos negativos para restar áreas vacías).", 
                "Use the global coordinate system. Add simple primitive shapes to build your section (use negative width/height to subtract voids)."))
                
    if "shapes_list" not in st.session_state:
        st.session_state.shapes_list = []
        
    col_s1, col_s2 = st.columns([1.5, 2])
    
    with col_s1:
        st.subheader(_t("Agregar Figura", "Add Shape"))
        s_tipo = st.selectbox(_t("Forma", "Shape"), ["Rectángulo", "Círculo", "Triángulo Rectángulo"])
        s_x = st.number_input("Posición origen local X_0", -1000.0, 1000.0, 0.0, 1.0)
        s_y = st.number_input("Posición origen local Y_0", -1000.0, 1000.0, 0.0, 1.0)
        
        if s_tipo == "Rectángulo":
            s_b = st.number_input("Base b (+ sólido, - hueco)", -1000.0, 1000.0, 10.0, 1.0)
            s_h = st.number_input("Altura h (+ sólido, - hueco)", -1000.0, 1000.0, 20.0, 1.0)
            s_prop = {"tipo": "Rect", "x": s_x, "y": s_y, "b": s_b, "h": s_h}
        elif s_tipo == "Círculo":
            s_r = st.number_input("Radio r (+ sólido, - radio hueco genera área negativa)", -1000.0, 1000.0, 10.0, 1.0)
            s_prop = {"tipo": "Circ", "x": s_x, "y": s_y, "r": s_r}
        else:
            s_b = st.number_input("Base Triángulo b", -1000.0, 1000.0, 10.0, 1.0)
            s_h = st.number_input("Altura Triángulo h", -1000.0, 1000.0, 10.0, 1.0)
            s_prop = {"tipo": "Triang", "x": s_x, "y": s_y, "b": s_b, "h": s_h}
            
        if st.button(_t("➕ Añadir Figura", "➕ Add Shape")):
            st.session_state.shapes_list.append(s_prop)
            st.rerun()
            
        if st.button(_t("🗑️ Limpiar Todo", "🗑️ Clear All")):
            st.session_state.shapes_list = []
            st.rerun()
            
    with col_s2:
        st.subheader(_t("Conjunto y Resultados", "Assembly and Results"))
        if not st.session_state.shapes_list:
            st.info(_t("Añade figuras a la lista para comenzar a calcular.", "Add shapes to the list to start calculations."))
        else:
            df_shapes = []
            sum_A = 0.0
            sum_Ax = 0.0
            sum_Ay = 0.0
            
            for idx, s in enumerate(st.session_state.shapes_list):
                if s["tipo"] == "Rect":
                    A = s["b"] * s["h"]
                    xc = s["x"] + s["b"]/2.0
                    yc = s["y"] + s["h"]/2.0
                    ixc = (s["b"] * s["h"]**3)/12.0
                    iyc = (s["h"] * s["b"]**3)/12.0
                elif s["tipo"] == "Circ":
                    r = s["r"]
                    A = np.pi * r**2 * (1 if r>0 else -1)
                    r_abs = abs(r)
                    xc = s["x"]
                    yc = s["y"]
                    ixc = (np.pi * r_abs**4)/4.0 * (1 if r>0 else -1)
                    iyc = ixc
                elif s["tipo"] == "Triang": # Rectangular triangle anchored at 90 deg corner (x,y)
                    A = 0.5 * s["b"] * s["h"]
                    xc = s["x"] + s["b"]/3.0
                    yc = s["y"] + s["h"]/3.0
                    ixc = (s["b"] * s["h"]**3)/36.0
                    iyc = (s["h"] * s["b"]**3)/36.0
                    
                sum_A += A; sum_Ax += A*xc; sum_Ay += A*yc
                df_shapes.append({"Fig": f"F{idx+1}-"+s["tipo"], "A": A, "xc": xc, "yc": yc, "Ixc": ixc, "Iyc": iyc})
                
            y_bar = sum_Ay / sum_A if sum_A != 0 else 0
            x_bar = sum_Ax / sum_A if sum_A != 0 else 0
            
            # Teorema Ejes Paralelos (Steiner)
            Ix_total = 0.0
            Iy_total = 0.0
            for d in df_shapes:
                dy = d["yc"] - y_bar
                dx = d["xc"] - x_bar
                Ix_total += d["Ixc"] + d["A"]*dy**2
                Iy_total += d["Iyc"] + d["A"]*dx**2
                
            st.dataframe(pd.DataFrame(df_shapes))
            
            st.markdown(f"**Área Total ($A$):** {sum_A:.2f}")
            st.markdown(f"**Centroide Global ($\bar{{x}}$):** {x_bar:.2f}")
            st.markdown(f"**Centroide Global ($\bar{{y}}$):** {y_bar:.2f}")
            st.markdown(f"**Inercia Eje Centroide X ($I_{{xx}}$):** {Ix_total:.2f}")
            st.markdown(f"**Inercia Eje Centroide Y ($I_{{yy}}$):** {Iy_total:.2f}")
            
            # Plot
            fig_c, ax_c = plt.subplots(figsize=(6,6))
            ax_c.axhline(0, color='black', lw=1); ax_c.axvline(0, color='black', lw=1)
            for s in st.session_state.shapes_list:
                if s["tipo"] == "Rect":
                    ax_c.add_patch(patches.Rectangle((s["x"], s["y"]), s["b"], s["h"], alpha=0.5, edgecolor='blue', facecolor='cyan' if s["b"]*s["h"]>0 else 'white', hatch='//' if s["b"]*s["h"]>0 else ''))
                elif s["tipo"] == "Circ":
                    ax_c.add_patch(patches.Circle((s["x"], s["y"]), abs(s["r"]), alpha=0.5, edgecolor='green', facecolor='lightgreen' if s["r"]>0 else 'white'))
                elif s["tipo"] == "Triang":
                    pts = np.array([[s["x"], s["y"]], [s["x"]+s["b"], s["y"]], [s["x"], s["y"]+s["h"]]])
                    ax_c.add_patch(patches.Polygon(pts, alpha=0.5, edgecolor='red', facecolor='salmon' if s["b"]*s["h"]>0 else 'white'))
                    
            ax_c.plot(x_bar, y_bar, 'r+', markersize=12, markeredgewidth=2, label='Centroide')
            ax_c.axhline(y_bar, color='red', linestyle='--', alpha=0.5)
            ax_c.axvline(x_bar, color='red', linestyle='--', alpha=0.5)
            ax_c.legend()
            ax_c.autoscale_view(); ax_c.set_aspect('equal', 'box')
            st.pyplot(fig_c)
