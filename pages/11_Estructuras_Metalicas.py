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

# ─────────────────────────────────────────────
# IDIOMA Y TERMINOLOGÍA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es

norma_sel = st.session_state.get("norma_sel", "NSR-10 (Colombia)")

# Diccionario de Términos Regionales
if "NTC-EM" in norma_sel or "México" in norma_sel:
    term_W = "Viga IPR"
    term_Col = "Castillo / Columna"
    term_C = "Polín / Perfil C"
    term_Tubo = "HSS / PTR"
elif "CIRSOC 201" in norma_sel or "CIRSOC 301" in norma_sel or "Argentina" in norma_sel or "Bolivia" in norma_sel:
    term_W = "Perfil Doble T"
    term_Col = "Columna"
    term_C = "Costanera"
    term_Tubo = "Tubo Estructural"
elif "Perú" in norma_sel or "Ecuador" in norma_sel:
    term_W = "Viga Tipo I / H"
    term_Col = "Columna"
    term_C = "Correa / Perfil C"
    term_Tubo = "Tubo LAF"
else:
    term_W = "Perfil W / Tipo I"
    term_Col = "Columna / Poste"
    term_C = "Perfil C"
    term_Tubo = "Perfil Tubular Rect."

st.set_page_config(page_title=_t("Estructuras Metálicas", "Steel Structures"), layout="wide")
st.image(r"assets/steel_header_1773257206595.png", use_container_width=True)
st.title(_t("Diseño de Estructuras Metálicas", "Steel Structure Design"))
st.markdown(_t(f"Cálculo de Propiedades, Compresión y Flexión de Perfiles Laminados en Caliente y Conformados en Frío. Adaptado a la terminología de **{norma_sel}**.", 
               "Properties, Compression, and Flexure computation for Hot-Rolled and Cold-Formed Steel Sections."))

# ─────────────────────────────────────────────
# CONFIGURACIÓN MATERIAL
st.sidebar.header(_t("⚙️ Materiales", "⚙️ Materials"))
Fy_adm = st.sidebar.number_input(_t("Esfuerzo de Fluencia Fy [MPa]", "Yield Stress Fy [MPa]"), 100.0, 500.0, st.session_state.get("st_fy", 250.0), 10.0, key="st_fy")
Fu_adm = st.sidebar.number_input(_t("Esfuerzo Último Fu [MPa]", "Ultimate Stress Fu [MPa]"), 300.0, 600.0, st.session_state.get("st_fu", 400.0), 10.0, key="st_fu")
E_steel = st.sidebar.number_input(_t("Módulo Elasticidad E [MPa]", "Modulus of Elasticity E [MPa]"), 100000.0, 250000.0, st.session_state.get("st_E", 200000.0), 1000.0, key="st_E")
G_steel = E_steel / (2 * (1 + 0.3)) # Shear modulus approx

peso_esp_acero = 7850.0 # kg/m3

# Pestañas principales
tab_P, tab_C, tab_F, tab_CF, tab_E = st.tabs([
    _t(f"1. Propiedades {term_W}", "1. W-Shape Properties"), 
    _t("2. LAMINADOS: Compresión", "2. HOT-ROLLED: Compression"), 
    _t(f"3. LAMINADOS: Flexión ({term_W})", "3. HOT-ROLLED: Flexure"),
    _t("4. CONFORMADOS EN FRÍO", "4. COLD-FORMED"), 
    _t("💾 Exportaciones Globales", "💾 Global Exports")
])

# Funciones Auxiliares de Dibujo
def plot_W(d, bf, tw, tf):
    fig, ax = plt.subplots(figsize=(3, 3))
    # Top flange
    ax.add_patch(patches.Rectangle((-bf/2,  d/2 - tf), bf, tf, facecolor='steelblue', edgecolor='black'))
    # Bottom flange
    ax.add_patch(patches.Rectangle((-bf/2, -d/2),      bf, tf, facecolor='steelblue', edgecolor='black'))
    # Web
    ax.add_patch(patches.Rectangle((-tw/2, -d/2 + tf), tw, d - 2*tf, facecolor='steelblue', edgecolor='black'))
    ax.set_xlim(-bf, bf); ax.set_ylim(-d, d)
    ax.axis('off'); return fig

def plot_T(d, bf, tw, tf):
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.add_patch(patches.Rectangle((-bf/2,  d - tf), bf, tf, facecolor='steelblue', edgecolor='black'))
    ax.add_patch(patches.Rectangle((-tw/2, 0), tw, d - tf, facecolor='steelblue', edgecolor='black'))
    ax.set_xlim(-bf, bf); ax.set_ylim(-d/2, d*1.2)
    ax.axis('off'); return fig

def plot_L(h, b, t):
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.add_patch(patches.Rectangle((0, 0), t, h, facecolor='steelblue', edgecolor='black'))
    ax.add_patch(patches.Rectangle((t, 0), b-t, t, facecolor='steelblue', edgecolor='black'))
    ax.set_xlim(-10, max(b,h)+10); ax.set_ylim(-10, max(b,h)+10)
    ax.axis('off'); return fig

def plot_C(h, b, d_lip, t):
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.add_patch(patches.Rectangle((0, 0), t, h, facecolor='darkgray', edgecolor='black'))
    ax.add_patch(patches.Rectangle((0, h-t), b, t, facecolor='darkgray', edgecolor='black'))
    ax.add_patch(patches.Rectangle((0, 0), b, t, facecolor='darkgray', edgecolor='black'))
    if d_lip > 0:
        ax.add_patch(patches.Rectangle((b-t, h-d_lip), t, d_lip, facecolor='darkgray', edgecolor='black'))
        ax.add_patch(patches.Rectangle((b-t, 0), t, d_lip, facecolor='darkgray', edgecolor='black'))
    ax.set_xlim(-b*0.5, b*1.5); ax.set_ylim(-h*0.2, h*1.2)
    ax.axis('off'); return fig

def plot_Tubo(h, b, t):
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.add_patch(patches.Rectangle((0, 0), b, h, facecolor='none', edgecolor='black', lw=3))
    ax.add_patch(patches.Rectangle((t, t), b-2*t, h-2*t, facecolor='white', edgecolor='black', lw=2))
    ax.add_patch(patches.Rectangle((0, 0), b, h, facecolor='darkgray', alpha=0.5))
    ax.set_xlim(-b*0.2, b*1.2); ax.set_ylim(-h*0.2, h*1.2)
    ax.axis('off'); return fig

# Variables globales para DOCX/APU
global_resumen = []
global_costo = 0.0

# ─────────────────────────────────────────────
# TAB 1: PROPIEDADES PERFIL W
# ─────────────────────────────────────────────
with tab_P:
    st.header(_t(f"Propiedades de Sección - {term_W}", f"Section Properties - {term_W}"))
    p1, p2, p3 = st.columns([1,2,1])
    with p1:
        st.subheader("Dimensiones [mm]")
        dw = st.number_input("Peralte total (d) [mm]", 50.0, 1500.0, st.session_state.get("st_p_d", 300.0), 1.0, key="st_p_d")
        bfw = st.number_input("Ancho patín (bf) [mm]", 50.0, 800.0, st.session_state.get("st_p_bf", 150.0), 1.0, key="st_p_bf")
        tfw = st.number_input("Espesor patín (tf) [mm]", 2.0, 100.0, st.session_state.get("st_p_tf", 10.0), 0.5, key="st_p_tf")
        tww = st.number_input("Espesor alma (tw) [mm]", 2.0, 100.0, st.session_state.get("st_p_tw", 6.0), 0.5, key="st_p_tw")
        
    with p2:
        # Calculos basicos
        A_w = 2 * (bfw * tfw) + (dw - 2*tfw)*tww
        Ix_w = (tww*(dw - 2*tfw)**3)/12.0 + 2 * ((bfw*tfw**3)/12.0 + (bfw*tfw)*(dw/2.0 - tfw/2.0)**2)
        Iy_w = 2*((tfw*bfw**3)/12.0) + ((dw-2*tfw)*tww**3)/12.0
        rx_w = math.sqrt(Ix_w / A_w)
        ry_w = math.sqrt(Iy_w / A_w)
        Sx_w = Ix_w / (dw/2.0)
        Zy_w = (bfw**2 * tfw)/2.0 + ((dw-2*tfw)*tww**2)/4.0 # Plastico y
        Zx_w = bfw*tfw*(dw-tfw) + (tww*(dw-2*tfw)**2)/4.0 # Plastico x
        
        peso_lin = (A_w / 1e6) * peso_esp_acero
        
        st.write(f"**Área (A):** {A_w:.2f} mm² ($= {A_w/100:.2f} cm^2$)")
        st.write(f"**Momento Inercia Eje Fuerte (Ix):** {Ix_w/1e4:.2f} cm⁴")
        st.write(f"**Momento Inercia Eje Débil (Iy):** {Iy_w/1e4:.2f} cm⁴")
        st.write(f"**Radio de Giro (rx):** {rx_w/10:.2f} cm  |  **(ry):** {ry_w/10:.2f} cm")
        st.write(f"**Módulo Plástico Fuerte (Zx):** {Zx_w/1e3:.2f} cm³")
        st.write(f"⚖️ **Peso Lineal Estimado:** {peso_lin:.2f} kg/m")
        
    with p3: st.pyplot(plot_W(dw, bfw, tww, tfw))

# ─────────────────────────────────────────────
# TAB 2: LAMINADOS - COMPRESIÓN
# ─────────────────────────────────────────────
with tab_C:
    st.header(_t(f"Resistencia a Compresión Axial", f"Axial Compression Resistance"))
    
    comp_opts = [term_W, "Perfil T", "Perfil L (Angular)"]
    tipo_comp = st.selectbox("Seleccione Perfil Laminado en Caliente a evaluar:", comp_opts, 
                             index=comp_opts.index(st.session_state.get("st_c_tipo", comp_opts[0])),
                             key="st_c_tipo")
    
    col_c1, col_c2, col_c3 = st.columns([1,1.5,1.5])
    with col_c1:
        st.subheader("Datos Compresión")
        L_c_m = st.number_input("Longitud No Arriostrada (Lc) [m]", 0.5, 20.0, st.session_state.get("st_c_L", 3.0), 0.5, key="st_c_L")
        P_u = st.number_input("Carga Axial Requerida Pu [kN]", 10.0, 10000.0, st.session_state.get("st_c_Pu", 500.0), 10.0, key="st_c_Pu")
        
    with col_c2:
        if tipo_comp == term_W:
            d_c = st.number_input(f"{tipo_comp} - Peralte d [mm]", 50.0, 1000.0, st.session_state.get("st_cw_d", 300.0), key="st_cw_d")
            bf_c = st.number_input(f"{tipo_comp} - Ancho bf [mm]", 50.0, 500.0, st.session_state.get("st_cw_bf", 150.0), key="st_cw_bf")
            tf_c = st.number_input(f"{tipo_comp} - tf [mm]", 2.0, 50.0, st.session_state.get("st_cw_tf", 10.0), key="st_cw_tf")
            tw_c = st.number_input(f"{tipo_comp} - tw [mm]", 2.0, 50.0, st.session_state.get("st_cw_tw", 6.0), key="st_cw_tw")
            A_c = 2 * (bf_c * tf_c) + (d_c - 2*tf_c)*tw_c
            Iy_c = 2*((tf_c*bf_c**3)/12.0) + ((d_c-2*tf_c)*tw_c**3)/12.0 # Minimum inertia usually Iy
            r_c = math.sqrt(Iy_c / A_c)
            fig_c = plot_W(d_c, bf_c, tw_c, tf_c)
            
        elif tipo_comp == "Perfil T":
            d_c = st.number_input("Perfil T - Peralte d [mm]", 50.0, 500.0, st.session_state.get("st_ct_d", 150.0), key="st_ct_d")
            bf_c = st.number_input("Perfil T - Ancho bf [mm]", 50.0, 500.0, st.session_state.get("st_ct_bf", 150.0), key="st_ct_bf")
            tf_c = st.number_input("Perfil T - tf [mm]", 2.0, 50.0, st.session_state.get("st_ct_tf", 10.0), key="st_ct_tf")
            tw_c = st.number_input("Perfil T - tw [mm]", 2.0, 50.0, st.session_state.get("st_ct_tw", 8.0), key="st_ct_tw")
            A_c = (bf_c * tf_c) + (d_c - tf_c)*tw_c
            Iy_c = ((tf_c*bf_c**3)/12.0) + ((d_c-tf_c)*tw_c**3)/12.0
            r_c = math.sqrt(Iy_c / A_c)
            fig_c = plot_T(d_c, bf_c, tw_c, tf_c)
            
        else: # Perfil L
            b_c = st.number_input("Perfil L - Altura/Base b [mm]", 20.0, 300.0, st.session_state.get("st_cl_b", 100.0), key="st_cl_b")
            t_c = st.number_input("Perfil L - Espesor t [mm]", 2.0, 30.0, st.session_state.get("st_cl_t", 10.0), key="st_cl_t")
            A_c = (2 * b_c - t_c) * t_c
            # Approx minimal radius of gyration rz para angulos lados iguales is ~ 0.2*b
            r_c = 0.2 * b_c
            fig_c = plot_L(b_c, b_c, t_c)

    with col_c3:
        # Pandeo por flexión (Flexural Buckling AISC E3)
        Lc_mm = L_c_m * 1000.0
        esbeltez = Lc_mm / r_c
        
        Fe = (math.pi**2 * E_steel) / (esbeltez**2)
        if esbeltez <= 4.71 * math.sqrt(E_steel/Fy_adm):
            Fcr = (0.658**(Fy_adm/Fe)) * Fy_adm
        else:
            Fcr = 0.877 * Fe
            
        Pn = Fcr * A_c / 1000.0 # kN
        phi_Pn = 0.90 * Pn # LRFD
        
        st.markdown(f"**Relación de Esbeltez L/r_min:** {esbeltez:.2f} (Límite ≈ 200)")
        st.markdown(f"**Esfuerzo Crítico (Fcr):** {Fcr:.2f} MPa")
        st.markdown(f"**Resistencia Axial de Diseño ($\phi P_n$):** <span style='color:blue;font-size:22px'>{phi_Pn:.1f} kN</span>", unsafe_allow_html=True)
        
        if P_u <= phi_Pn: st.success(f"✅ ¡Aprobado! (FS = {phi_Pn/P_u:.2f})")
        else: st.error("❌ No Aprobado por Compresión Axial / Pandeo.")
        st.pyplot(fig_c)
        global_resumen.append(f"Compresión Laminados: {tipo_comp}. Lc={L_c_m}m. φPn={phi_Pn:.1f} kN vs Pu={P_u} kN. -> {'OK' if P_u<=phi_Pn else 'FALLA'}")
        peso_lin_c = (A_c / 1e6) * peso_esp_acero
        global_costo += peso_lin_c * L_c_m

# ─────────────────────────────────────────────
# TAB 3: LAMINADOS - FLEXIÓN (PERFIL W)
# ─────────────────────────────────────────────
with tab_F:
    st.header(_t(f"Resistencia a Flexión - {term_W}", f"Flexural Resistance - {term_W}"))
    st.write(_t("Evaluación del momento flector considerando Pandeo Lateral Torsional (LTB).", "Bending moment evaluation considering Lateral Torsional Buckling (LTB)."))
    
    f_c1, f_c2, f_c3 = st.columns(3)
    with f_c1:
        Mu = st.number_input("Momento Último Solicitante Mu [kN-m]", 10.0, 5000.0, st.session_state.get("st_f_Mu", 150.0), 10.0, key="st_f_Mu")
        Lb_m = st.number_input("Longitud No Arriostrada Lateramente Lb [m]", 0.5, 20.0, st.session_state.get("st_f_Lb", 2.0), 0.5, key="st_f_Lb")
        Cb = st.number_input("Coeficiente de Momento (Cb)", 1.0, 3.0, st.session_state.get("st_f_Cb", 1.0), 0.1, key="st_f_Cb")
    
    with f_c2:
        d_f = st.number_input(f"Peralte d [mm]", 100.0, 1500.0, st.session_state.get("st_fw_d", 300.0), 1.0, key="st_fw_d")
        bf_f = st.number_input(f"Ancho bf [mm]", 50.0, 800.0, st.session_state.get("st_fw_bf", 150.0), 1.0, key="st_fw_bf")
        tf_f = st.number_input(f"Espesor tf [mm]", 2.0, 50.0, st.session_state.get("st_fw_tf", 10.0), 0.5, key="st_fw_tf")
        tw_f = st.number_input(f"Espesor tw [mm]", 2.0, 50.0, st.session_state.get("st_fw_tw", 6.0), 0.5, key="st_fw_tw")
    
    with f_c3:
        # Properties for LTB
        h0 = d_f - tf_f
        cw = ((h0**2)*tf_f*bf_f**3)/24.0
        Iy_f = 2*((tf_f*bf_f**3)/12.0) + ((d_f-2*tf_f)*tw_f**3)/12.0
        J_tor = (2*bf_f*tf_f**3 + (d_f-tf_f)*tw_f**3)/3.0
        r_ts = math.sqrt(math.sqrt(Iy_f*cw) / (2*(bf_f*tf_f*(d_f-tf_f)/2 + tw_f*(d_f-2*tf_f)**2/4))) # Approx rts
        r_ts = bf_f / min(math.sqrt(12*(1+(1/6)*(d_f*tw_f)/(bf_f*tf_f))), 1000) # simpler rts approx
        
        Zx_f = bf_f*tf_f*(d_f-tf_f) + (tw_f*(d_f-2*tf_f)**2)/4.0 
        Sx_f = (2 * ((bf_f*tf_f**3)/12.0 + (bf_f*tf_f)*(d_f/2.0 - tf_f/2.0)**2) + (tw_f*(d_f - 2*tf_f)**3)/12.0) / (d_f/2.0)
        
        Lp = 1.76 * r_ts * math.sqrt(E_steel/Fy_adm) / 1000.0 # m
        c_factor = 1.0 # Doubly symmetric
        Lr = np.pi * r_ts * math.sqrt(E_steel/(0.7*Fy_adm)) / 1000.0 # Simplified Lr m
        
        Mp = Fy_adm * Zx_f / 1e6 # kN-m
        
        st.write(f"**Límite Fluencia (Lp):** {Lp:.2f} m")
        st.write(f"**Límite Pandeo (Lr):** {Lr:.2f} m")
        st.write(f"**Momento Plástico (Mp):** {Mp:.1f} kN-m")
        
        Lbmm = Lb_m*1000.0; Lrmm = Lr*1000.0; Lpmm = Lp*1000.0
        
        # AISC F2
        if Lb_m <= Lp:
            Mn = Mp
            estado = "Fluencia (Zona Plastica)"
        elif Lb_m <= Lr:
            Mn = Cb * (Mp - (Mp - 0.7*Fy_adm*Sx_f/1e6) * ((Lb_m - Lp)/(Lr - Lp)))
            Mn = min(Mn, Mp)
            estado = "LTB Inelástico"
        else:
            Fcr_ltb = (Cb * np.pi**2 * E_steel / (Lbmm/r_ts)**2) * math.sqrt(1 + 0.078*(J_tor/Sx_f)*(Lbmm/r_ts)**2) # Approx
            Mn = Fcr_ltb * Sx_f / 1e6
            Mn = min(Mn, Mp)
            estado = "LTB Elástico"
            
        phi_Mn = 0.90 * Mn
        
        st.markdown(f"**Zona Comportamiento:** {estado}")
        st.markdown(f"**Capacidad Momento ($\phi M_n$):** <span style='color:blue;font-size:22px'>{phi_Mn:.1f} kN-m</span>", unsafe_allow_html=True)
        if Mu <= phi_Mn: st.success(f"✅ ¡Viga Cumple a Flexión! (FS={phi_Mn/Mu:.2f})")
        else: st.error("❌ Viga falla por Flexión / LTB.")
        global_resumen.append(f"Flexión Laminados: Lb={Lb_m}m. φMn={phi_Mn:.1f} kN-m vs Mu={Mu} kN-m. -> {'OK' if Mu<=phi_Mn else 'FALLA'}")


# ─────────────────────────────────────────────
# TAB 4: CONFORMADOS EN FRÍO (Cold-Formed)
# ─────────────────────────────────────────────
with tab_CF:
    st.header(_t("Perfiles Conformados en Frío (Cold-Formed)", "Cold-Formed Sections"))
    
    cf_opts = [f"{term_C} con labios (rígido)", f"{term_C} sin labios (U)", term_Tubo]
    tipo_cf = st.selectbox("Seleccione Perfil Conformado en Frío:", cf_opts, 
                             index=cf_opts.index(st.session_state.get("st_cf_tipo", cf_opts[0])),
                             key="st_cf_tipo")
    
    col_cf1, col_cf2 = st.columns([1,2])
    
    with col_cf1:
        h_cf = st.number_input("Altura total h [mm]", 20.0, 400.0, st.session_state.get("st_cf_h", 150.0), 1.0, key="st_cf_h")
        b_cf = st.number_input("Ancho base b [mm]", 20.0, 200.0, st.session_state.get("st_cf_b", 50.0), 1.0, key="st_cf_b")
        t_cf = st.number_input("Espesor de lámina t [mm]", 0.5, 10.0, st.session_state.get("st_cf_t", 2.0), 0.1, key="st_cf_t")
        
        if "labios" in tipo_cf:
            d_lip = st.number_input("Pestaña/Labio d [mm]", 0.0, 50.0, st.session_state.get("st_cf_l", 15.0), key="st_cf_l")
            A_cf = (h_cf + 2*b_cf + 2*d_lip - 4*t_cf) * t_cf
            fig_cf = plot_C(h_cf, b_cf, d_lip, t_cf)
        elif tipo_cf == term_Tubo:
            d_lip = 0
            A_cf = 2*(h_cf + b_cf - 2*t_cf) * t_cf
            fig_cf = plot_Tubo(h_cf, b_cf, t_cf)
        else:
            d_lip = 0
            A_cf = (h_cf + 2*b_cf - 2*t_cf) * t_cf
            fig_cf = plot_C(h_cf, b_cf, 0, t_cf)
            
        peso_lin_cf = (A_cf / 1e6) * peso_esp_acero
        st.write(f"**Área Bruta (A):** {A_cf:.2f} mm²")
        st.write(f"⚖️ **Peso Lineal Estimado:** {peso_lin_cf:.2f} kg/m")
        
    with col_cf2:
        st.subheader("Verificación de Compresión")
        L_cf = st.number_input("Longitud No Arriostrada [m]", 0.5, 10.0, st.session_state.get("st_cf_L", 2.0), key="st_cf_L")
        Pu_cf = st.number_input("Carga Axial Pu [kN]", 5.0, 500.0, st.session_state.get("st_cf_Pu", 50.0), key="st_cf_Pu")
        
        # Simple AISI approximation for Cold-Formed (using unreduced Area for a very conservative check, or Q factor)
        # Real AISI requires effective width calculations for localized buckling.
        # Marcelo Pardo simplified: Area efectiva Ae ~ 0.8 A_cf if elements are slender.
        w_t_ratio = max(h_cf/t_cf, b_cf/t_cf)
        
        if w_t_ratio > 200:
            st.warning("⚠️ Relación ancho/espesor > 200. Riesgo de pandeo local muy severo.")
            Ae = 0.5 * A_cf
        elif w_t_ratio > 50:
            Ae = 0.8 * A_cf # Simplified Q
        else:
            Ae = A_cf
            
        st.write(f"**Área Efectiva por Pandeo Local (Ae):** aprox {Ae:.2f} mm² (basado en esbeltez elemento)")
        
        # Flexural buckling radius of gyration approx
        if tipo_cf == term_Tubo: r_cf = b_cf * 0.38
        else: r_cf = b_cf * 0.30 # Approximate weak axis for C-shape
        
        esbeltez_cf = (L_cf*1000.0) / r_cf
        st.write(f"**Relación Esbeltez Global L/r:** {esbeltez_cf:.2f}")
        
        Fe_cf = (math.pi**2 * E_steel) / (max(esbeltez_cf, 1)**2)
        if esbeltez_cf <= 4.71 * math.sqrt(E_steel/Fy_adm): Fcr_cf = (0.658**(Fy_adm/Fe_cf)) * Fy_adm
        else: Fcr_cf = 0.877 * Fe_cf
        
        Pn_cf = (Ae * Fcr_cf) / 1000.0 # kN
        phi_Pn_cf = 0.85 * Pn_cf # AISI phi is usually 0.85 for compression
        
        st.markdown(f"**Resistencia Axial Compresión ($\phi P_n$):** <span style='color:blue;font-size:22px'>{phi_Pn_cf:.1f} kN</span>", unsafe_allow_html=True)
        if Pu_cf <= phi_Pn_cf: st.success("✅ ¡El perfil conformado en frío CUMPLE!")
        else: st.error("❌ El perfil falla por compresión / pandeo global o local.")
        
        c0, c1 = st.columns(2)
        c0.pyplot(fig_cf)
        global_resumen.append(f"Compresión Laminados en Frío: {tipo_cf}. Lc={L_cf}m. φPn={phi_Pn_cf:.1f} kN vs Pu={Pu_cf} kN. -> {'OK' if Pu_cf<=phi_Pn_cf else 'FALLA'}")
        global_costo += peso_lin_cf * L_cf


# ─────────────────────────────────────────────
# TAB 5: EXPORTACIONES
# ─────────────────────────────────────────────
with tab_E:
    st.header(_t("💾 Exportaciones Globales", "💾 Global Exports"))
    
    c_dxf, c_doc, c_apu = st.columns(3)
    
    with c_dxf:
        st.subheader("DXF Section Profile")
        st.write("Dibuja el Perfil W actual en un archivo Autocad DXF.")
        # Generar DXF W
        try:
            doc_dxf = ezdxf.new('R2010'); msp = doc_dxf.modelspace()
            p1=(-bfw/2, dw/2)
            msp.add_lwpolyline([(-bfw/2, dw/2), (bfw/2, dw/2), (bfw/2, dw/2-tfw), (tww/2, dw/2-tfw), (tww/2, -dw/2+tfw), (bfw/2, -dw/2+tfw), (bfw/2, -dw/2), (-bfw/2, -dw/2), (-bfw/2, -dw/2+tfw), (-tww/2, -dw/2+tfw), (-tww/2, dw/2-tfw), (-bfw/2, dw/2-tfw), (-bfw/2, dw/2)], dxfattribs={'layer': 'PERFIL_W', 'color': 5, 'closed': True})
            out_dxf = io.StringIO(); doc_dxf.write(out_dxf)
            st.download_button("📥 Descargar Perfil_W.dxf", data=out_dxf.getvalue(), file_name=f"Perfil_W_{dw}x{bfw}.dxf", mime="application/dxf")
        except: pass
        
    with c_doc:
        st.subheader("DOCX Memoria")
        doc_m = Document()
        doc_m.add_heading(f"Memoria de Estructuras Metálicas - {norma_sel}", 0)
        doc_m.add_heading("Materiales", level=1)
        doc_m.add_paragraph(f"Acero Fy = {Fy_adm} MPa, Fu = {Fu_adm} MPa, E = {E_steel} MPa.")
        doc_m.add_heading("Resultados", level=1)
        for rez in global_resumen: doc_m.add_paragraph(rez)
        f_doc = io.BytesIO(); doc_m.save(f_doc); f_doc.seek(0)
        st.download_button("📥 Descargar Memoria.docx", data=f_doc, file_name="Metalias_Acero_Reporte.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
    with c_apu:
        st.subheader("Presupuesto de Acero (APU)")
        if "apu_config" in st.session_state:
            apu = st.session_state.apu_config
            mon = apu["moneda"]
            precio_kg = st.number_input(f"Costo por Kg de Acero Estructural Suministrado y Armado [{mon}/kg]", 1.0, 100000.0, st.session_state.get("st_price_kg", 8000.0 if mon=="COP$" else 4.0), key="st_price_kg")
            
            st.write(f"Total Kilogramos de perfileria analizada: **{global_costo:.2f} kg**")
            costo_directo = global_costo * precio_kg
            aiu = costo_directo * apu.get("pct_aui", 0.3)
            
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                df_export = pd.DataFrame({
                    "Item": ["Acero Estructural (Suministro y Montaje)", "AIU"],
                    "Cantidad (kg)": [global_costo, 1],
                    "Costo Unitario": [precio_kg, aiu]
                })
                df_export["Subtotal"] = df_export["Cantidad (kg)"] * df_export["Costo Unitario"]
                df_export.to_excel(writer, index=False, sheet_name='APU Acero')
            output_excel.seek(0)
            st.download_button("📥 Descargar APU en Excel", data=output_excel, file_name="APU_Acero.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("El APU requiere configuración en la pestaña principal de Presupuestos (4_APU_Mercado).")
