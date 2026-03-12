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
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es

st.set_page_config(page_title=_t("Diseño Sísmico", "Seismic Design"), layout="wide")
st.image(r"C:\Users\cagch\.gemini\antigravity\brain\d408b5ad-3eb5-4039-b011-4650dd509d7e\seismic_header_1773257220819.png", use_container_width=True)
st.title(_t("Diseño Sísmico y Espectros", "Seismic Design and Spectra"))
st.markdown(_t("Análisis dinámico simplificado (frecuencia natural 1 GDL) y Generación de Espectros de Respuesta de Diseño para diversas normativas de América (NSR, E.030, NB 1225001, ASCE 7, etc).", 
               "Simplified dynamic analysis (1 DOF natural frequency) and Design Response Spectrum Generation for various American codes (NSR, E.030, NB 1225001, ASCE 7, etc)."))

# ─────────────────────────────────────────────
# CONFIGURACIÓN LATERAL
norma_sel = st.session_state.get("norma_sel", "NSR-10 (Colombia)")
_PAIS_ISO = {"NSR-10 (Colombia)":"co","ACI 318-25 (EE.UU.)":"us","ACI 318-19 (EE.UU.)":"us","ACI 318-14 (EE.UU.)":"us","NEC-SE-HM (Ecuador)":"ec","E.060 (Perú)":"pe","NTC-EM (México)":"mx","COVENIN 1753-2006 (Venezuela)":"ve","NB 1225001-2020 (Bolivia)":"bo","CIRSOC 201-2025 (Argentina)":"ar"}
_iso = _PAIS_ISO.get(norma_sel, "un")
st.sidebar.markdown(f'<div style="background:#1e3a1e;border-radius:6px;padding:8px;margin-bottom:10px;"><img src="https://flagcdn.com/24x18/{_iso}.png" style="vertical-align:middle;margin-right:8px;"><span style="color:#7ec87e;font-weight:600;">{_t("Normativa Activa:","Code:")} {norma_sel}</span></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SEC 1: 1-DOF FREQUENCY CALCULATOR
# ─────────────────────────────────────────────
with st.expander(_t("⏱️ 1. Frecuencia Natural de Vibración (1 GDL)", "⏱️ 1. Natural Frequency of Vibration (1 DOF)"), expanded=False):
    st.info(_t("Calcula las propiedades dinámicas básicas de una estructura simplificada a un solo grado de libertad (Masa-Resorte).", 
               "Calculates the basic dynamic properties of a structure simplified to a single degree of freedom (Mass-Spring)."))
    f1, f2, f3 = st.columns([1,1,2])
    with f1:
        peso_W = st.number_input(_t("Peso de la estructura W [kN]", "Structure Weight W [kN]"), 10.0, 50000.0, 1000.0, 10.0)
        masa_m = peso_W / 9.81 # ton
        st.write(f"Masa $m$: **{masa_m:.2f} t**")
    with f2:
        rigidez_k = st.number_input(_t("Rigidez Lateral k [kN/m]", "Lateral Stiffness k [kN/m]"), 100.0, 500000.0, 15000.0, 100.0)
    
    omega_n = math.sqrt(rigidez_k / masa_m)
    freq_n = omega_n / (2*math.pi)
    period_T = 1.0 / freq_n if freq_n != 0 else 0
    
    with f3:
        st.metric(_t("Frecuencia Angular (ω_n)", "Angular Frequency (ω_n)"), f"{omega_n:.2f} rad/s")
        c11, c22 = st.columns(2)
        c11.metric(_t("Frecuencia Cíclica (f_n)", "Cyclic Frequency (f_n)"), f"{freq_n:.3f} Hz")
        c22.metric(_t("Período Natural (T)", "Natural Period (T)"), f"{period_T:.3f} s")
        
        # Simple illustration
        fig_1dof, ax_1dof = plt.subplots(figsize=(5,1))
        ax_1dof.plot([0, 0], [-1, 1], 'k-', lw=3)
        # Spring
        xs = np.linspace(0, 3, 50); ys = 0.5 * np.sin(xs * 10)
        ax_1dof.plot(xs, ys, 'b-', lw=2)
        # Mass
        ax_1dof.add_patch(patches.Rectangle((3, -0.5), 1, 1, facecolor='gray', edgecolor='k'))
        ax_1dof.text(3.5, 0, f"m={masa_m:.0f}t", ha='center', va='center', color='white')
        ax_1dof.text(1.5, 0.7, f"k={rigidez_k:.0f}kN/m", ha='center', color='blue')
        ax_1dof.text(4.5, 0, f"T = {period_T:.2f} s", ha='left', va='center', fontweight='bold', color='red')
        ax_1dof.set_xlim(-0.5, 6); ax_1dof.set_ylim(-1.5, 1.5); ax_1dof.axis('off')
        st.pyplot(fig_1dof)

# ─────────────────────────────────────────────
# SEC 2: SEISMIC RESPONSE SPECTRUM GENERATOR
# ─────────────────────────────────────────────
st.header(_t("📊 2. Espectro Sísmico de Diseño", "📊 2. Seismic Design Response Spectrum"))

s1, s2 = st.columns([1, 2])

# Initialization of Spectrum Variables
T_domain = np.linspace(0.01, 5.0, 500)
Sa_vals = np.zeros_like(T_domain)
params_texto = []

with s1:
    st.subheader(_t("Parámetros", "Parameters"))
    
    # ─── LOGIC PER COUNTRY ───
    if "NSR" in norma_sel:
        st.write("**Norma: NSR-10 (Colombia)**")
        ciudad = st.selectbox("Ciudad Principal:", ["Bogotá", "Medellín", "Cali", "Barranquilla", "Bucaramanga", "Otra / Custom"])
        if ciudad == "Bogotá": Aa_def=0.15; Av_def=0.20
        elif ciudad == "Medellín": Aa_def=0.15; Av_def=0.20
        elif ciudad == "Cali": Aa_def=0.25; Av_def=0.25
        elif ciudad == "Barranquilla": Aa_def=0.10; Av_def=0.10
        elif ciudad == "Bucaramanga": Aa_def=0.25; Av_def=0.25
        else: Aa_def=0.20; Av_def=0.20
        
        Aa = st.number_input("Aa (Aceleración pico efectiva)", 0.05, 0.50, Aa_def, 0.05)
        Av = st.number_input("Av (Velocidad pico efectiva)", 0.05, 0.50, Av_def, 0.05)
        
        perfil = st.selectbox("Perfil de Suelo (NSR-10)", ["A", "B", "C", "D", "E"], index=3)
        # Simplified Fa/Fv logic for app
        Fa_vals = {"A":0.8, "B":1.0, "C":1.2, "D":1.4, "E":2.5}
        Fv_vals = {"A":0.8, "B":1.0, "C":1.6, "D":2.0, "E":3.2}
        Fa = Fa_vals[perfil]; Fv = Fv_vals[perfil]
        st.write(f"Coeficientes de sitio: $F_a={Fa}$, $F_v={Fv}$")
        
        I_group = st.selectbox("Grupo de Uso (Importancia I)", [1.0, 1.1, 1.25, 1.5], index=0)
        
        Tc = 0.48 * (Av * Fv) / (Aa * Fa)
        T0 = 0.1 * Tc
        TL = 2.4 * Fv # Approx
        
        for i, t in enumerate(T_domain):
            if t < T0: sa = Aa * Fa * (1.0 + (t/T0)*(2.5 - 1.0))
            elif t <= Tc: sa = 2.5 * Aa * Fa
            elif t <= TL: sa = 1.2 * Av * Fv / t
            else: sa = 1.2 * Av * Fv * TL / (t**2)
            Sa_vals[i] = sa * I_group
            
        params_texto = [f"País: Colombia (NSR-10)", f"Aa = {Aa}, Av = {Av}", f"Suelo tipo {perfil} -> Fa={Fa}, Fv={Fv}", f"I = {I_group}", f"Tc = {Tc:.3f} s"]

    elif "E.060" in norma_sel or "Perú" in norma_sel:
        st.write("**Norma: E.030 (Perú)**")
        ciudad = st.selectbox("Zona / Ciudad:", ["Zona 4 (Lima, Costa)", "Zona 3 (Arequipa)", "Zona 2 (Cusco)", "Zona 1 (Selva)"])
        if "4" in ciudad: Z = 0.45
        elif "3" in ciudad: Z = 0.35
        elif "2" in ciudad: Z = 0.25
        else: Z = 0.10
        st.write(f"Factor de Zona $Z$ = {Z}")
        
        suelo = st.selectbox("Perfil de Suelo (S0, S1, S2, S3)", ["S0", "S1", "S2", "S3"], index=2)
        S_dict = {"S0": 0.8, "S1": 1.0, "S2": 1.15, "S3": 1.4}
        Tp_dict = {"S0": 0.3, "S1": 0.4, "S2": 0.6, "S3": 1.0}
        Tl_dict = {"S0": 3.0, "S1": 2.5, "S2": 2.0, "S3": 1.6}
        S = S_dict[suelo]; Tp = Tp_dict[suelo]; Tl = Tl_dict[suelo]
        
        U = st.selectbox("Uso o Importancia U (A=1.5, B=1.3, C=1.0)", [1.5, 1.3, 1.0], index=2)
        R = st.number_input("Coeficiente R (Reducción sísmica) [Usa 1.0 para Elástico]", 1.0, 10.0, 1.0, 0.5)
        
        for i, t in enumerate(T_domain):
            if t < 0.2*Tp: C = 1 + 1.5 * (t / (0.2*Tp)) # Pseudo rama ascendente para dibujo claro
            elif t <= Tp: C = 2.5
            elif t <= Tl: C = 2.5 * (Tp / t)
            else: C = 2.5 * ((Tp * Tl) / (t**2))
            
            Sa_vals[i] = (Z * U * C * S) / R
            
        params_texto = [f"País: Perú (Norme E.030)", f"Zona Z = {Z}", f"Suelo {suelo} -> S={S}, Tp={Tp}, Tl={Tl}", f"Uso U = {U}", f"R = {R}"]

    elif "1225001" in norma_sel or "Bolivia" in norma_sel:
        st.write("**Norma: GBDS NB 1225001-2020 (Bolivia)**")
        zona = st.selectbox("Zona Sísmica:", ["1 (Baja)", "2 (Media - ej. La Paz)", "3 (Alta)", "4 (Muy Alta)", "5 (Severa)"], index=1)
        # Aproximación de A0 (aceleración referencial %g):
        Z_vals = {0: 0.05, 1: 0.10, 2: 0.15, 3: 0.20, 4: 0.25}
        Z = Z_vals.get(int(zona.split(" ")[0]) - 1, 0.15)
        st.write(f"Z_0 = {Z}g")
        
        suelo = st.selectbox("Clase de Sitio", ["A (Roca dura)", "B (Roca)", "C (Suelo Muy Denso)", "D (Suelo Rígido)", "E (Suelo Blando)"], index=3)
        # Factor S simplificado para Bolivia 
        F_a = 1.2 # Asumption basica para suelo D
        F_v = 1.4
        
        Tc = 0.5 # Aprox general
        for i, t in enumerate(T_domain):
            if t <= Tc: sa = 2.5 * Z * F_a
            else: sa = 2.5 * Z * F_a * (Tc / t)
            Sa_vals[i] = sa
            
        params_texto = [f"País: Bolivia (GBDS 2020)", f"Zona = {zona} (Z={Z})", f"Suelo tipo {suelo[0]}", f"Tc estimado = {Tc}"]

    else:
        st.write("**Norma General / ACI 318 / ASCE 7 (EE.UU.)**")
        Ss = st.number_input("S_S (Short Period Acc)", 0.1, 3.0, 1.0, 0.1)
        S1 = st.number_input("S_1 (1-sec Period Acc)", 0.05, 1.5, 0.4, 0.1)
        Fa = st.number_input("F_a (Corto Periodo)", 0.5, 3.0, 1.1, 0.1)
        Fv = st.number_input("F_v (Largo Periodo)", 0.5, 3.5, 1.6, 0.1)
        
        S_DS = (2.0/3.0) * Ss * Fa
        S_D1 = (2.0/3.0) * S1 * Fv
        
        T0 = 0.2 * (S_D1 / S_DS)
        Ts = S_D1 / S_DS
        TL = 4.0
        
        st.write(f"$S_{{DS}}$ = {S_DS:.3f} g,  $S_{{D1}}$ = {S_D1:.3f} g")
        
        for i, t in enumerate(T_domain):
            if t < T0: sa = S_DS * (0.4 + 0.6*(t/T0))
            elif t <= Ts: sa = S_DS
            elif t <= TL: sa = S_D1 / t
            else: sa = (S_D1 * TL) / (t**2)
            Sa_vals[i] = sa
            
        params_texto = [f"Norma: {norma_sel}", f"Ss = {Ss}, S1 = {S1}", f"S_DS = {S_DS:.3f}, S_D1 = {S_D1:.3f}"]

with s2:
    # ─── PLOTLY SPECTRUM GRAPH ───
    fig_spec = go.Figure()
    fig_spec.add_trace(go.Scatter(x=T_domain, y=Sa_vals, mode='lines', name='Espectro Sa', line=dict(color='red', width=3)))
    
    # Optional overlay of Natural Period
    fig_spec.add_trace(go.Scatter(x=[period_T, period_T], y=[0, max(Sa_vals)*1.1], mode='lines', 
                                  name='T_Estructura (1 GDL)', line=dict(color='blue', width=2, dash='dash')))
    
    fig_spec.update_layout(
        title=_t("Espectro Georreferenciado", "Georeferenced Response Spectrum"),
        xaxis_title=_t("Período T (s)", "Period T (s)"),
        yaxis_title=_t("Pseudo-Aceleración Sa (g)", "Pseudo-Acceleration Sa (g)"),
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    st.plotly_chart(fig_spec, use_container_width=True)

# ─────────────────────────────────────────────
# EXPORTACIONES GLOBALES (DXF / DOC / APU)
# ─────────────────────────────────────────────
st.markdown("---")
st.subheader("💾 Exportación Integral (Sísmica)")

tab_dxf, tab_doc, tab_xls = st.tabs(["📐 " + _t("Exportar Gráfico a DXF", "Export Graph to DXF"), 
                                     "📄 " + _t("Memoria DOCX", "DOCX Report"), 
                                     "💰 " + _t("Curva XLSX / Presupuesto APU", "XLSX Curve / APU Budget")])

with tab_dxf:
    col_dxf1, col_dxf2 = st.columns([1,3])
    with col_dxf1:
        st.write(_t("Geometría generada en líneas 2D simulando el espectro para cajetines estructurales Autocad.",
                    "2D line geometry simulating the spectrum for Autocad structural title blocks."))
        doc_s = ezdxf.new('R2010'); msp_s = doc_s.modelspace()
        
        max_sa = max(Sa_vals) if max(Sa_vals)>0 else 1
        # Ejes
        msp_s.add_lwpolyline([(0,0), (5,0)], dxfattribs={'layer': 'EJE_T', 'color': 7})
        msp_s.add_lwpolyline([(0,0), (0,max_sa*1.2)], dxfattribs={'layer': 'EJE_SA', 'color': 7})
        # Curva
        points = [(T_domain[i], Sa_vals[i]) for i in range(len(T_domain))]
        msp_s.add_lwpolyline(points, dxfattribs={'layer': 'ESPECTRO', 'color': 1})
        
        out_s = io.StringIO(); doc_s.write(out_s)
        st.download_button("📥 Descargar Espectro.dxf", data=out_s.getvalue(), file_name=f"Espectro_{norma_sel[:5]}.dxf", mime="application/dxf")

with tab_doc:
    st.write(_t("Generar memoria rápida de la definición del espectro elástico.", "Generate rapid design spectrum report."))
    doc_m = Document()
    doc_m.add_heading(f"Definición de Amenaza Sísmica ({norma_sel})", 0)
    
    doc_m.add_heading("1. Parámetros Adoptados", level=1)
    for pt in params_texto:
        doc_m.add_paragraph(pt)
        
    doc_m.add_heading("2. Aceleraciones Clave", level=1)
    doc_m.add_paragraph(f"Aceleración Pico Sa_max = {max(Sa_vals):.3f} g")
    doc_m.add_paragraph(f"Aceleración para T=1.0s = {Sa_vals[int(1.0/(T_domain[1]-T_domain[0]))]:.3f} g")
    
    doc_m.add_heading("3. Propiedad de Prueba (1 GDL)", level=1)
    doc_m.add_paragraph(f"Período evaluado: {period_T:.3f} s  -->  Sa correspondiente: {np.interp(period_T, T_domain, Sa_vals):.3f} g")
    
    f_doc = io.BytesIO(); doc_m.save(f_doc); f_doc.seek(0)
    st.download_button("📥 Descargar Memoria DOCX", data=f_doc, file_name="Sismica_Reporte.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with tab_xls:
    st.write(_t("1. Matriz de Coordenadas (T vs Sa) para importar en ETABS/SAP2000.", "1. Coordinate Matrix (T vs Sa) to import into ETABS/SAP2000."))
    st.write(_t("2. Presupuesto Base APU - Honorarios de Asesoría Sísmica.", "2. Base APU Budget - Seismic Consulting Fees."))
    
    if "apu_config" in st.session_state:
        apu = st.session_state.apu_config
        mon = apu["moneda"]
        honorarios = st.number_input(f"Honorarios Globales por Estudio Sísmico [{mon}]", 500.0, 50000.0, 1500.0, 100.0)
        
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            # Hoja 1: Coordenadas del Espectro
            df_coords = pd.DataFrame({"Periodo_T_seg": T_domain, "Aceleracion_Sa_g": Sa_vals})
            df_coords.to_excel(writer, index=False, sheet_name='ETABS_Puntos_Espectro')
            
            # Hoja 2: APU
            df_export = pd.DataFrame({
                "Item": ["Estudio de Vulnerabilidad Sísmica y Espectro", "AIU / Gastos Admn."],
                "Cantidad": [1, 1],
                "Unidad/Costo": [honorarios, honorarios*apu.get("pct_aui", 0.30)]
            })
            df_export["Subtotal"] = df_export["Cantidad"] * df_export["Unidad/Costo"]
            df_export.to_excel(writer, index=False, sheet_name='APU Sismica')
            
        output_excel.seek(0)
        st.download_button("📥 Descargar Datos de Espectro y Presupuesto (.xlsx)", data=output_excel, file_name="Espectro_Vulnerabilidad.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else: st.warning(_t("Carga APU en la pestaña principal de Mercado.", "Load APU details on the Market page."))
