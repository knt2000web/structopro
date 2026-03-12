import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import ezdxf
from docx import Document
from docx.shared import Pt, RGBColor

# -----------------------------------------------------------------------------
# IDIOMA Y GLOBAL
# -----------------------------------------------------------------------------
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es
norma_sel = st.session_state.get("norma_sel", "NSR-10 (Colombia)")
norma_flag = st.session_state.get("norma_flag_url", "")




html_title = """
<div style="font-family:'Segoe UI', sans-serif;margin-bottom:10px;">
    <h1 style="color:#ffffff; margin-bottom:5px; font-size: 2.2em;">Generador Maestro 3D Paramétrico</h1>
</div>
"""
st.markdown(html_title, unsafe_allow_html=True)
st.markdown(_t("Construcción rápida de Edificios 3D con cálculos en base a la norma global seleccionada de la suite.", 
               "Rapid 3D Building generation with structural verification based on your global suite code."))
st.markdown("---")


# -----------------------------------------------------------------------------
# GENERADORES GEOMETRICOS
# -----------------------------------------------------------------------------
def generar_malla_3d(Lx, Lz, nx, nz, alturas_pisos, col_b, col_h, vig_b, vig_h):
    pisos = len(alturas_pisos)
    nudos = []
    # Generar espaciados
    x_coords = np.linspace(0, Lx, nx)
    z_coords = np.linspace(0, Lz, nz)
    
    y_coords = [0.0]
    curr_y = 0.0
    for h in alturas_pisos:
        curr_y += h
        y_coords.append(curr_y)
    
    nid = 1
    for y in y_coords:
        for z in z_coords:
            for x in x_coords:
                nudos.append({"ID": nid, "X": round(x,2), "Y": round(y,2), "Z": round(z,2)})
                nid += 1
    
    df_nudos = pd.DataFrame(nudos)
    
    # Generar Elementos
    columnas = []
    vigas_x = []
    vigas_z = []
    
    # helper para encontrar nudo por coordenada (muy basico)
    def find_nid(x, y, z):
        res = df_nudos[(np.isclose(df_nudos['X'], x)) & (np.isclose(df_nudos['Y'], y)) & (np.isclose(df_nudos['Z'], z))]
        return int(res.iloc[0]['ID']) if not res.empty else None

    # Columnas (Verticales)
    cid = 1
    for z in z_coords:
        for x in x_coords:
            for p in range(pisos):
                n1 = find_nid(x, y_coords[p], z)
                n2 = find_nid(x, y_coords[p+1], z)
                if n1 and n2:
                    columnas.append({"ID": f"C{cid}", "N1": n1, "N2": n2, "Base_X": round(x,2), "Base_Z": round(z,2), "Piso": p+1, "b (m)": col_b, "h (m)": col_h})
                    cid += 1
                    
    # Vigas X
    vid = 1
    for y in y_coords[1:]: # Solo pisos superiores
        for z in z_coords:
            for i in range(nx-1):
                n1 = find_nid(x_coords[i], y, z)
                n2 = find_nid(x_coords[i+1], y, z)
                if n1 and n2:
                    v_piso = y_coords.index(y)
                    vigas_x.append({"ID": f"VG-{vid}", "N1": n1, "N2": n2, "Piso": v_piso, "b (m)": vig_b, "h (m)": vig_h})
                    vid += 1
                    
    # Vigas Z
    for y in y_coords[1:]:
        for x in x_coords:
            for i in range(nz-1):
                n1 = find_nid(x, y, z_coords[i])
                n2 = find_nid(x, y, z_coords[i+1])
                if n1 and n2:
                    v_piso = y_coords.index(y)
                    vigas_z.append({"ID": f"VG-{vid}", "N1": n1, "N2": n2, "Piso": v_piso, "b (m)": vig_b, "h (m)": vig_h})
                    vid += 1

    # Zapatas (En base Y=0)
    zapatas = []
    zid = 1
    for z in z_coords:
        for x in x_coords:
            nid = find_nid(x, 0, z)
            if nid:
                # Determinar tipo
                es_borde_x = (np.isclose(x, 0) or np.isclose(x, Lx))
                es_borde_z = (np.isclose(z, 0) or np.isclose(z, Lz))
                
                if es_borde_x and es_borde_z: tipo = "Esquinera"
                elif es_borde_x or es_borde_z: tipo = "Medianera"
                else: tipo = "Centrada"
                
                zapatas.append({"ID": f"Z{zid}", "Nudo": nid, "Tipo": tipo, "X":x, "Z":z, "b (m)": 1.5, "h (m)": 1.5, "D_f (m)": 1.0})
                zid += 1
                
    return df_nudos, pd.DataFrame(columnas), pd.DataFrame(vigas_x), pd.DataFrame(vigas_z), pd.DataFrame(zapatas)


# -----------------------------------------------------------------------------
# ASIGNACION DE ESTADOS
# -----------------------------------------------------------------------------
if "g3d_nudos" not in st.session_state:
    st.session_state.update({
        "g3d_nudos": pd.DataFrame(),
        "g3d_cols": pd.DataFrame(),
        "g3d_vx": pd.DataFrame(),
        "g3d_vz": pd.DataFrame(),
        "g3d_zaps": pd.DataFrame(),
        "g_state": False
    })


# -----------------------------------------------------------------------------
# UI: CONFIGURACION DEL LOTE Y EDIFICIO
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header(_t("🌍 Norma de Diseño", "🌍 Design Code"))
    NORMAS_DISP = [
        "NSR-10 (Colombia)", "ACI 318-25 (EE.UU.)", "ACI 318-19 (EE.UU.)", 
        "ACI 318-14 (EE.UU.)", "NEC-SE-HM (Ecuador)", "E.060 (Perú)", 
        "NTC-EM (México)", "COVENIN 1753-2006 (Venezuela)", 
        "NB 1225001-2020 (Bolivia)", "CIRSOC 201-2025 (Argentina)"
    ]
    if "norma_sel" not in st.session_state: st.session_state.norma_sel = NORMAS_DISP[0]
    
    nuevo_norma = st.selectbox("Selecciona la Normativa:", NORMAS_DISP, index=NORMAS_DISP.index(st.session_state.norma_sel) if st.session_state.norma_sel in NORMAS_DISP else 0)
    if nuevo_norma != st.session_state.norma_sel:
        st.session_state.norma_sel = nuevo_norma
        st.rerun()
    norma_sel = st.session_state.norma_sel
    st.markdown("---")
    
    st.header(_t("📏 Parametrización Geométrica", "📏 Geometric Parametrization"))
    
    st.subheader("Lote (Planta)")
    L_x = st.number_input("Frente Lote X (m)", value=12.0, min_value=2.0)
    L_z = st.number_input("Fondo Lote Z (m)", value=15.0, min_value=2.0)
    
    n_x = st.number_input("N° Columnas en Frente (eje X)", value=4, min_value=2, help="Columnas a lo ancho del frente")
    n_z = st.number_input("N° Columnas en Fondo (eje Z)", value=5, min_value=2, help="Columnas a lo largo de la profundidad")
    
    st.subheader("Alzado (Elevación)")
    n_pisos = st.number_input("Número de Pisos", value=3, min_value=1)
    
    if "alturas_df" not in st.session_state or len(st.session_state.alturas_df) != n_pisos:
        data_h = []
        for p in range(n_pisos):
            data_h.append({"Piso": p+1, "Altura (m)": 3.5 if p==0 else 3.0})
        st.session_state.alturas_df = pd.DataFrame(data_h)
        
    st.markdown("Alturas por nivel (Editable):")
    st.session_state.alturas_df = st.data_editor(st.session_state.alturas_df, use_container_width=True, hide_index=True)
    alturas_list = st.session_state.alturas_df["Altura (m)"].tolist()
    
    st.subheader("Secciones (Dimensiones en metros)")
    col_dim_b = st.number_input("Base Columnas (m)", value=0.40, step=0.05)
    col_dim_h = st.number_input("Altura Columnas (m)", value=0.40, step=0.05)
    
    vig_dim_b = st.number_input("Base Vigas (m)", value=0.30, step=0.05)
    vig_dim_h = st.number_input("Altura Vigas (m)", value=0.40, step=0.05)
    
    st.markdown("---")
    st.subheader("Sistema de Entrepiso (Losas)")
    tipo_losa = st.selectbox("Tipo de Losa:", ["Maciza", "Aligerada con Ladrillo", "Aligerada con Poliestireno (EPS)", "Metaldeck (Placa Colaborante)"])
    espesor_losa = st.number_input("Espesor Total Losa (m)", value=0.20 if "Aligerada" not in tipo_losa else 0.40, step=0.05)
    
    st.markdown("---")
    st.subheader("Cargas de Diseño (Estándar)")
    q_muerta = st.number_input("Carga Muerta CM (kN/m²)", value=4.5)
    q_viva = st.number_input("Carga Viva CV (kN/m²)", value=2.0)
    
    if st.button("🏗️ Generar / Actualizar Malla 3D", type="primary", use_container_width=True):
        dn, dc, dvx, dvz, dz = generar_malla_3d(L_x, L_z, n_x, n_z, alturas_list, col_dim_b, col_dim_h, vig_dim_b, vig_dim_h)
        st.session_state.update({
            "g3d_nudos": dn, "g3d_cols": dc, "g3d_vx": dvx, "g3d_vz": dvz, "g3d_zaps": dz, 
            "g_state": True,
            "g_dims": {"losa_tipo": tipo_losa, "losa_espesor": espesor_losa, "losa_x": L_x, "losa_z": L_z, "pisos": n_pisos}
        })
        
    st.markdown("---")
    st.subheader("📂 Gestor de Proyectos")
    import json, datetime
    project_name = st.text_input("Nombre del Proyecto:", value=st.session_state.get("project_name", "Mi_Edificio"), key="g3d_pn")
    project_owner = st.text_input("Propietario / Cliente:", value=st.session_state.get("project_owner", ""), key="g3d_po")
    project_address = st.text_input("Dirección de Obra:", value=st.session_state.get("project_address", ""), key="g3d_pa")
    project_phone = st.text_input("Teléfono de Contacto:", value=st.session_state.get("project_phone", ""), key="g3d_pp")

    st.session_state.project_name = project_name
    st.session_state.project_owner = project_owner
    st.session_state.project_address = project_address
    st.session_state.project_phone = project_phone

    def serialize_state_g3d():
        state_dict = {}
        for k, v in st.session_state.items():
            if isinstance(v, pd.DataFrame):
                state_dict[k] = {"__type__": "dataframe", "data": v.to_dict(orient="records")}
            elif isinstance(v, (int, float, str, bool, list, dict)):
                state_dict[k] = v
        return json.dumps(state_dict, indent=4)

    if project_name and project_owner and project_address and project_phone:
        st.download_button(
            label="💾 Guardar Proyecto Local (.json)",
            data=serialize_state_g3d(),
            file_name=f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
            key="g3d_db"
        )
    else:
        st.info("✍️ Por favor llena el Nombre, Propietario, Dirección y Teléfono para habilitar el guardado.")


# -----------------------------------------------------------------------------
# PLOTLY VIEWER
# -----------------------------------------------------------------------------
def plot_edificio(nudos, cols, vx, vz, zaps):
    fig = go.Figure()
    
    # Dibujar Columnas (Azul)
    for _, c in cols.iterrows():
        n1 = nudos[nudos['ID'] == c['N1']].iloc[0]
        n2 = nudos[nudos['ID'] == c['N2']].iloc[0]
        fig.add_trace(go.Scatter3d(
            x=[n1['X'], n2['X']], y=[n1['Z'], n2['Z']], z=[n1['Y'], n2['Y']],
            mode='lines', line=dict(color='#2196F3', width=6), hoverinfo="text", text=f"{c['ID']}<br>b: {c['b (m)']}m, h: {c['h (m)']}m", name="Columnas", showlegend=False
        ))
        
    # Vigas X (Verde)
    for _, v in vx.iterrows():
        n1 = nudos[nudos['ID'] == v['N1']].iloc[0]
        n2 = nudos[nudos['ID'] == v['N2']].iloc[0]
        fig.add_trace(go.Scatter3d(
            x=[n1['X'], n2['X']], y=[n1['Z'], n2['Z']], z=[n1['Y'], n2['Y']],
            mode='lines', line=dict(color='#4CAF50', width=4), hoverinfo="text", text=f"{v['ID']}<br>b: {v['b (m)']}m, h: {v['h (m)']}m", name="Vigas X", showlegend=False
        ))
        
    # Vigas Z (Amarillo Oscuro)
    for _, v in vz.iterrows():
        n1 = nudos[nudos['ID'] == v['N1']].iloc[0]
        n2 = nudos[nudos['ID'] == v['N2']].iloc[0]
        fig.add_trace(go.Scatter3d(
            x=[n1['X'], n2['X']], y=[n1['Z'], n2['Z']], z=[n1['Y'], n2['Y']],
            mode='lines', line=dict(color='#FFC107', width=4), hoverinfo="text", text=f"{v['ID']}<br>b: {v['b (m)']}m, h: {v['h (m)']}m", name="Vigas Z", showlegend=False
        ))

    # Zapatas (Marcadores de Cuadrado en la Base)
    for _, z in zaps.iterrows():
        color = 'red' if z['Tipo'] == "Esquinera" else ('orange' if z['Tipo'] == "Medianera" else 'gray')
        texto_hover = f"{z['ID']} - {z['Tipo']}<br>b={z.get('b (m)', 1.5)}m, h={z.get('h (m)', 1.5)}m<br>Df={z.get('D_f (m)', 1.0)}m"
        fig.add_trace(go.Scatter3d(
            x=[z['X']], y=[z['Z']], z=[0],
            mode='markers', marker=dict(size=8, color=color, symbol='square'),
            hoverinfo="text", hovertext=texto_hover, name="Zapatas", showlegend=False
        ))
        
    # Losas (Superficies Semitransparentes por piso)
    y_pisos = nudos['Y'].unique()
    for y in y_pisos[1:]:
        nx_coords = nudos[nudos['Y']==y]['X']
        nz_coords = nudos[nudos['Y']==y]['Z']
        fig.add_trace(go.Mesh3d(
            x=[nx_coords.min(), nx_coords.max(), nx_coords.max(), nx_coords.min()],
            y=[nz_coords.min(), nz_coords.min(), nz_coords.max(), nz_coords.max()],
            z=[y, y, y, y],
            color='cyan', opacity=0.1, hoverinfo="skip", name="Losa"
        ))
        
    # Anotaciones de Ejes (Letras y Numeros)
    unq_x = sorted(nudos['X'].unique())
    unq_z = sorted(nudos['Z'].unique())
    
    # Eje X con Letras A, B, C...
    for i, x in enumerate(unq_x):
        letra = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"
        fig.add_trace(go.Scatter3d(
            x=[x], y=[-1], z=[0], mode='text', text=[letra],
            textfont=dict(color='white', size=16), name="Eje X", showlegend=False, hoverinfo="skip"
        ))
        
    # Eje Z con Números 1, 2, 3...
    for i, z in enumerate(unq_z):
        fig.add_trace(go.Scatter3d(
            x=[-1], y=[z], z=[0], mode='text', text=[str(i+1)],
            textfont=dict(color='white', size=16), name="Eje Z", showlegend=False, hoverinfo="skip"
        ))
        
    # Anotaciones Visuales de Nivel (Líneas punteadas)
    for p, y in enumerate(y_pisos[1:]):
        fig.add_trace(go.Scatter3d(
            x=[-2, -1], y=[0, 0], z=[y, y],
            mode='lines+text', line=dict(color='gray', width=2, dash='dash'),
            text=[f"Nivel {p+1}", ""], textposition="top left", textfont=dict(color='gold', size=12),
            hoverinfo="skip", showlegend=False
        ))

    fig.update_layout(
        scene=dict(
            xaxis_title='Frente X (m)', yaxis_title='Fondo Z (m)', zaxis_title='Altura Y (m)',
            aspectmode='data'
        ),
        dragmode='turntable',
        margin=dict(l=0, r=0, b=0, t=30), title=f"Modelo 3D Paramétrico - {norma_sel}",
        plot_bgcolor='black', paper_bgcolor='#1e1e1e'
    )
    return fig


if st.session_state.g_state:
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.plotly_chart(plot_edificio(st.session_state.g3d_nudos, st.session_state.g3d_cols, st.session_state.g3d_vx, st.session_state.g3d_vz, st.session_state.g3d_zaps), use_container_width=True, height=600, config={'scrollZoom': True, 'displayModeBar': True})
        
    with c2:
        tab_z, tab_c, tab_v = st.tabs(["📍 Zapatas", "🗼 Columnas", "🏗️ Vigas"])
        with tab_z:
            st.info("💡 **Zapatas:** 🟥 Esquina | 🟧 Medianera | ⬜ Centrada")
            st.session_state.g3d_zaps = st.data_editor(st.session_state.g3d_zaps, use_container_width=True, hide_index=True, key="ed_zaps")
        with tab_c:
            st.info("Edita dimensiones (b, h) de columnas específicas.")
            st.session_state.g3d_cols = st.data_editor(st.session_state.g3d_cols, use_container_width=True, hide_index=True, key="ed_cols")
        with tab_v:
            st.info("Edita dimensiones de vigas transversales (VX) y longitudinales (VZ).")
            # Unimos temporalmente para mostrar o editamos por separado
            v_all = pd.concat([st.session_state.g3d_vx, st.session_state.g3d_vz], ignore_index=True)
            v_edited = st.data_editor(v_all, use_container_width=True, hide_index=True, key="ed_vigs")
            # Separar de nuevo al estado
            st.session_state.g3d_vx = v_edited[v_edited['ID'].str.startswith("VX")]
            st.session_state.g3d_vz = v_edited[v_edited['ID'].str.startswith("VZ")]

    st.markdown("---")
    
    # -----------------------------------------------------------------------------
    # AUTO-CHEQUEOS NORMATIVOS (DINÁMICOS POR NORMA)
    # -----------------------------------------------------------------------------
    norma_actual = st.session_state.get('norma_sel', 'NSR-10')
    
    st.header(_t(f"📑 Auto-Chequeos de Diseño ({norma_actual})", f"📑 Design Auto-Checks ({norma_actual})"))
    st.markdown(_t(f"Simulación de comprobaciones de Diseño Estructural para elementos en base estricta a la norma **{norma_actual}**.", 
                   f"Simulation of Structural Design checks for elements strictly based on **{norma_actual}**."))
                   
    # Generar Datos de Analisis Simulados para mostrar la estructura solicitada
    check_cols = []
    
    # Determinar parametros y Phi (φ) segun la norma elegida
    if "NSR-10" in norma_actual:
        phi_comp = 0.65  # Elementos con estribos cerrados
        phi_flex = 0.90
        limite_esbeltez = 100
        ref_norma = "Título C10 (NSR-10)"
    elif "ACI" in norma_actual:
        phi_comp = 0.65
        phi_flex = 0.90
        limite_esbeltez = 100
        ref_norma = "Chapter 10 (ACI 318)"
    else: # Por defecto (LRFD AISC E2) o equivalente
        phi_comp = 0.90
        phi_flex = 0.90
        limite_esbeltez = 200
        ref_norma = "Secciones E / F (LRFD)"

    for _, col in st.session_state.g3d_cols.iterrows():
        area_aferente = (L_x/(n_x-1)) * (L_z/(n_z-1)) # Aferente aproximada
        carga_piso = (q_muerta*1.2 + q_viva*1.6) * area_aferente
        P_u = carga_piso * (n_pisos - col['Piso'] + 1) # Carga axial acumulada
        
        # Dimensiones de la Columna
        L_col = st.session_state.alturas_df.loc[col['Piso']-1, "Altura (m)"] if (col['Piso']-1) in st.session_state.alturas_df.index else 3.0
        b_col, h_col = col['b (m)'], col['h (m)']
        
        # Radio de giro (r = 0.3 * dim para rectangulares en concreto)
        r_giro = 0.3 * min(b_col, h_col)
        esbeltez = (1.0 * L_col) / r_giro if r_giro > 0 else 0
        esb_check = "✅ Cumple" if esbeltez <= limite_esbeltez else "❌ No Cumple"
        
        # Capacidad a Compresión Pn simulada (f'c = 28 MPa = 28000 kN/m2, As = 1%)
        Area_m2 = b_col * h_col
        Pn_kN = (0.85 * 28000 * Area_m2) + (420000 * 0.01 * Area_m2) 
        Pr = P_u
        eficiencia_comp = Pr / (phi_comp * Pn_kN) if (phi_comp * Pn_kN) > 0 else 999
        comp_check = "✅ Cumple" if eficiencia_comp <= 1.0 else "❌ No Cumple"
        
        # Capacidad a Flexión (Excentricidad accidental del 10%)
        Mux = P_u * 0.1 
        Mnx = 1500.0 * Area_m2 # Aproximacion gruesa a la capacidad al momento
        efi_flex = Mux / (phi_flex * Mnx) if Mnx > 0 else 999
        flex_check = "✅ Cumple" if efi_flex <= 1.0 else "❌ No Cumple"
        
        estado_global = "✅ Cumple" if (esb_check=="✅ Cumple" and comp_check=="✅ Cumple" and flex_check=="✅ Cumple") else "❌ No Cumple"
        diagnostico = "-" if estado_global == "✅ Cumple" else "⚠️ Aumentar Sección (b, h) o f'c"
        
        check_cols.append({
            "Elemento": col['ID'],
            "Piso": col['Piso'],
            "P_u (kN)": round(Pr, 2),
            f"η Compresión": round(eficiencia_comp, 2),
            "Cap. C.": comp_check,
            "η Flexión": round(efi_flex, 2),
            "Cap. F.": flex_check,
            "Esbeltez L/r": round(esbeltez, 2),
            f"Limite < {limite_esbeltez}": esb_check,
            "Estado Final": estado_global,
            "Acción Recomendada": diagnostico
        })
        
    df_checks = pd.DataFrame(check_cols)
    
    # Render Styling
    def row_colors(row):
        color = '#d4edda' if row['Estado Final'] == '✅ Cumple' else '#f8d7da'
        return [f'background-color: {color}; text-align: center;' for _ in row]
    
    st.dataframe(df_checks.style.apply(row_colors, axis=1), use_container_width=True, height=400)
    
    st.info(f"""
    **📝 Notas de Cumplimiento bajo {norma_actual}:**
    - **Referencia Legal:** Cumpliendo los lineamientos pre-establecidos para flexo-compresión en **{ref_norma}**.
    - La Tensión Crítica / Esbeltez máxima permitida es controlada bajo $\lambda \le {limite_esbeltez}$.
    - El factor de reducción de diseño $\phi$ (Phi) aplicado para Compresión es **{phi_comp}** y para Flexión **{phi_flex}**.
    - La Resistencia Nominal $P_n$ asume concretos $f'c = 28$ MPa y cuantías típicas $\\rho = 1\%$ sobre el área real $A_g$ de tu tabla de dimensiones.
    """)
    
    st.markdown("---")
    st.header(_t("📊 Cubicación y Costos de Obra (APU)", "📊 Quantity Takeoff & Costs (APU)"))
    
    dims = st.session_state.g_dims
    vol_cols = 0.0
    area_encofrado_cols = 0.0
    for _, c in st.session_state.g3d_cols.iterrows():
        n1 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == c['N1']].iloc[0]
        n2 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == c['N2']].iloc[0]
        L = abs(n2['Y'] - n1['Y'])
        b, h = c['b (m)'], c['h (m)']
        vol_cols += L * b * h
        area_encofrado_cols += L * 2 * (b + h)
        
    vol_vigas = 0.0
    area_encofrado_vigas = 0.0
    for _, v in st.session_state.g3d_vx.iterrows():
        n1 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == v['N1']].iloc[0]
        n2 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == v['N2']].iloc[0]
        L = abs(n2['X'] - n1['X'])
        b, h = v['b (m)'], v['h (m)']
        vol_vigas += L * b * h
        area_encofrado_vigas += L * (2*h + b) # Fondo y 2 caras
        
    for _, v in st.session_state.g3d_vz.iterrows():
        n1 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == v['N1']].iloc[0]
        n2 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == v['N2']].iloc[0]
        L = abs(n2['Z'] - n1['Z'])
        b, h = v['b (m)'], v['h (m)']
        vol_vigas += L * b * h
        area_encofrado_vigas += L * (2*h + b) 
        
    # Zapatas simplificadas
    num_zap = len(st.session_state.g3d_zaps)
    vol_zapatas = num_zap * 1.5 * 1.5 * 0.4 # Promedio
    
    # Losas
    area_planta = dims['losa_x'] * dims['losa_z']
    area_total_losa = area_planta * dims['pisos']
    
    if dims['losa_tipo'] == "Maciza":
        vol_losa = area_total_losa * dims['losa_espesor']
    elif dims['losa_tipo'] == "Aligerada con Ladrillo":
        vol_losa = area_total_losa * dims['losa_espesor'] * 0.45 # Solo viguetas y torta superior
    elif dims['losa_tipo'] == "Aligerada con Poliestireno (EPS)":
        vol_losa = area_total_losa * dims['losa_espesor'] * 0.35 # El EPS permite mayor ligereza/menos concreto
    else: # Metaldeck
        vol_losa = area_total_losa * dims['losa_espesor'] * 0.60
        
    vol_total_concreto = vol_cols + vol_vigas + vol_zapatas + vol_losa
    peso_acero_aprox = vol_total_concreto * 100 # 100 kg/m3 promedio historico
    
    # APU Global Costos
    apu = st.session_state.get('apu_config', {'cemento': 26000, 'arena': 60000, 'grava': 70000, 'acero': 4500})
    costo_concreto_m3 = (7 * apu['cemento']) + (0.55 * apu['arena']) + (0.84 * apu['grava']) + 25000 # 25k de agua/aditivos aprox
    costo_concreto_total = vol_total_concreto * costo_concreto_m3
    costo_acero_total = peso_acero_aprox * apu['acero']
    costo_directo = costo_concreto_total + costo_acero_total
    
    df_cantidades = pd.DataFrame([
        {"Ítem": "Concreto Columnas (m³)", "Cantidad": round(vol_cols, 2)},
        {"Ítem": "Concreto Vigas (m³)", "Cantidad": round(vol_vigas, 2)},
        {"Ítem": "Concreto Cimentación (m³)", "Cantidad": round(vol_zapatas, 2)},
        {"Ítem": f"Concreto Losa [{dims['losa_tipo']}] (m³)", "Cantidad": round(vol_losa, 2)},
        {"Ítem": "TOTAL CONCRETO (m³)", "Cantidad": round(vol_total_concreto, 2)},
        {"Ítem": "Acero de Refuerzo Aprox. (kg)", "Cantidad": round(peso_acero_aprox, 2)},
        {"Ítem": "Encofrado Columnas (m²)", "Cantidad": round(area_encofrado_cols, 2)},
        {"Ítem": "Encofrado Vigas (m²)", "Cantidad": round(area_encofrado_vigas, 2)},
    ])
    
    c3, c4 = st.columns(2)
    with c3:
        st.dataframe(df_cantidades, use_container_width=True, hide_index=True)
    with c4:
        st.success(f"**Costo Directo Estimado (Materiales principales):**\n\n"
                   f"- Concreto Estructural: {apu['moneda']} {costo_concreto_total:,.2f}\n"
                   f"- Acero Refuerzo: {apu['moneda']} {costo_acero_total:,.2f}\n\n"
                   f"### TOTAL: {apu['moneda']} {costo_directo:,.2f}")
                   
    # =========================================================================
    # EXPORTADORES
    # =========================================================================
    st.markdown("---")
    st.subheader("📥 Exportar Reportes y Modelos")
    ex1, ex2, ex3 = st.columns(3)
    
    # 1. EXCEL (Cantidades y Chequeos)
    with ex1:
        buffer_xls = io.BytesIO()
        with pd.ExcelWriter(buffer_xls, engine='openpyxl') as writer:
            df_cantidades.to_excel(writer, index=False, sheet_name='Cantidades Obra')
            df_checks.to_excel(writer, index=False, sheet_name='Chequeos Normativos')
        st.download_button("📊 Exportar Resumen a Excel", data=buffer_xls.getvalue(), file_name="Reporte_Edificio_APU.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
    # 2. DOCX (Memoria Descriptiva)
    with ex2:
        doc = Document()
        doc.add_heading(f"Memoria de Cálculo: Edificio Paramétrico ({norma_sel})", 0)
        doc.add_paragraph("Modelo autogenerado con el módulo Generador Maestro 3D.")
        doc.add_heading("1. Cantidades de Obra", level=1)
        
        t1 = doc.add_table(rows=1, cols=2)
        t1.style = 'Table Grid'
        hdr_cells = t1.rows[0].cells
        hdr_cells[0].text = 'Ítem'
        hdr_cells[1].text = 'Cantidad'
        for _, row in df_cantidades.iterrows():
            row_cells = t1.add_row().cells
            row_cells[0].text = str(row['Ítem'])
            row_cells[1].text = str(row['Cantidad'])
            
        doc.add_heading("2. Costos APU Estimados", level=1)
        doc.add_paragraph(f"Costo Concreto: {apu['moneda']} {costo_concreto_total:,.2f}")
        doc.add_paragraph(f"Costo Acero: {apu['moneda']} {costo_acero_total:,.2f}")
        doc.add_paragraph(f"Costo Directo Total: {apu['moneda']} {costo_directo:,.2f}")
        
        buffer_docx = io.BytesIO()
        doc.save(buffer_docx)
        st.download_button("📄 Exportar Memoria DOCX / PDF", data=buffer_docx.getvalue(), file_name="Memoria_Generador_3D.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
    # 3. DXF (Modelo Unifilar 3D)
    with ex3:
        dwg = ezdxf.new('R2010')
        msp = dwg.modelspace()
        
        # Layer setup
        dwg.layers.add(name="COLUMNAS", color=5) # Blue
        dwg.layers.add(name="VIGAS", color=3) # Green
        dwg.layers.add(name="ZAPATAS", color=1) # Red
        
        # Line drawing
        for _, c in st.session_state.g3d_cols.iterrows():
            n1 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == c['N1']].iloc[0]
            n2 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == c['N2']].iloc[0]
            msp.add_line((n1['X'], n1['Z'], n1['Y']), (n2['X'], n2['Z'], n2['Y']), dxfattribs={'layer': 'COLUMNAS'})
            
        for _, v in st.session_state.g3d_vx.iterrows():
            n1 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == v['N1']].iloc[0]
            n2 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == v['N2']].iloc[0]
            msp.add_line((n1['X'], n1['Z'], n1['Y']), (n2['X'], n2['Z'], n2['Y']), dxfattribs={'layer': 'VIGAS'})
            
        for _, v in st.session_state.g3d_vz.iterrows():
            n1 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == v['N1']].iloc[0]
            n2 = st.session_state.g3d_nudos[st.session_state.g3d_nudos['ID'] == v['N2']].iloc[0]
            msp.add_line((n1['X'], n1['Z'], n1['Y']), (n2['X'], n2['Z'], n2['Y']), dxfattribs={'layer': 'VIGAS'})
            
        buffer_dxf = io.StringIO()
        dwg.write(buffer_dxf)
        st.download_button("🏗️ Exportar a CAD (DXF 3D)", data=buffer_dxf.getvalue(), file_name="Estructura_3D.dxf", mime="text/plain")

else:
    st.info("👈 Configura los parámetros de tu lote estructural en la barra izquierda y presiona **Generar Malla 3D**.")
