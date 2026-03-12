import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math
import io

# ─────────────────────────────────────────────
# IDIOMA GLOBAL Y NORMA
lang = st.session_state.get("idioma", "Español")
def _t(es, en): return en if lang == "English" else es
norma_sel = st.session_state.get("norma_sel", "NSR-10 (Colombia)")


st.title(_t("StructMaster 3D - Análisis Matricial Espacial", "StructMaster 3D - Spatial Matrix Analysis"))
st.markdown(_t("Entorno Tridimensional Interactivo para Pórticos y Armaduras Espaciales (6 GDL por Nudo).", 
               "Interactive 3D Environment for Space Frames and Trusses (6 DOF per Node)."))

# ─────────────────────────────────────────────
# INIT DATAFRAMES 3D
if "nudos3d_df" not in st.session_state:
    st.session_state.nudos3d_df = pd.DataFrame([
        {"ID":1,"X":0.0,"Y":0.0,"Z":0.0}, {"ID":2,"X":4.0,"Y":0.0,"Z":0.0},
        {"ID":3,"X":4.0,"Y":0.0,"Z":3.0}, {"ID":4,"X":0.0,"Y":0.0,"Z":3.0},
        {"ID":5,"X":0.0,"Y":3.0,"Z":0.0}, {"ID":6,"X":4.0,"Y":3.0,"Z":0.0},
        {"ID":7,"X":4.0,"Y":3.0,"Z":3.0}, {"ID":8,"X":0.0,"Y":3.0,"Z":3.0}
    ])
if "barras3d_df" not in st.session_state:
    st.session_state.barras3d_df = pd.DataFrame([
        # Base
        {"N I":1, "N J":2, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":50, "J (cm⁴)":100, "Iy (cm⁴)":800, "Iz (cm⁴)":2000},
        {"N I":2, "N J":3, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":50, "J (cm⁴)":100, "Iy (cm⁴)":800, "Iz (cm⁴)":2000},
        {"N I":3, "N J":4, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":50, "J (cm⁴)":100, "Iy (cm⁴)":800, "Iz (cm⁴)":2000},
        {"N I":4, "N J":1, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":50, "J (cm⁴)":100, "Iy (cm⁴)":800, "Iz (cm⁴)":2000},
        # Columnas
        {"N I":1, "N J":5, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":80, "J (cm⁴)":150, "Iy (cm⁴)":3000, "Iz (cm⁴)":3000},
        {"N I":2, "N J":6, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":80, "J (cm⁴)":150, "Iy (cm⁴)":3000, "Iz (cm⁴)":3000},
        {"N I":3, "N J":7, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":80, "J (cm⁴)":150, "Iy (cm⁴)":3000, "Iz (cm⁴)":3000},
        {"N I":4, "N J":8, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":80, "J (cm⁴)":150, "Iy (cm⁴)":3000, "Iz (cm⁴)":3000},
        # Techo
        {"N I":5, "N J":6, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":50, "J (cm⁴)":100, "Iy (cm⁴)":800, "Iz (cm⁴)":2000},
        {"N I":6, "N J":7, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":50, "J (cm⁴)":100, "Iy (cm⁴)":800, "Iz (cm⁴)":2000},
        {"N I":7, "N J":8, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":50, "J (cm⁴)":100, "Iy (cm⁴)":800, "Iz (cm⁴)":2000},
        {"N I":8, "N J":5, "E (MPa)":2e5, "G (MPa)":7.7e4, "A (cm²)":50, "J (cm⁴)":100, "Iy (cm⁴)":800, "Iz (cm⁴)":2000}
    ])
if "apoyos3d_df" not in st.session_state:
    st.session_state.apoyos3d_df = pd.DataFrame([
        {"Nudo":1,"Fx":True,"Fy":True,"Fz":True,"Mx":True,"My":True,"Mz":True},
        {"Nudo":2,"Fx":True,"Fy":True,"Fz":True,"Mx":False,"My":False,"Mz":False},
        {"Nudo":3,"Fx":True,"Fy":True,"Fz":True,"Mx":False,"My":False,"Mz":False},
        {"Nudo":4,"Fx":True,"Fy":True,"Fz":True,"Mx":False,"My":False,"Mz":False}
    ])
if "cargas3d_df" not in st.session_state:
    st.session_state.cargas3d_df = pd.DataFrame([
        {"Nudo":6, "FX (kN)":20.0, "FY (kN)":0.0, "FZ (kN)":0.0, "MX":0.0, "MY":0.0, "MZ":0.0},
        {"Nudo":7, "FX (kN)":20.0, "FY (kN)":0.0, "FZ (kN)":0.0, "MX":0.0, "MY":0.0, "MZ":0.0}
    ])

# ─────────────────────────────────────────────
# GRAFICADOR 3D INTERACTIVO
def plot_frame_3d(df_n, df_b, df_sup, df_load):
    fig = go.Figure()
    
    # Dibujar Nudos
    fig.add_trace(go.Scatter3d(
        x=df_n['X'], y=df_n['Z'], z=df_n['Y'], # Convention: Z is depth, Y is elevation vertical
        mode='markers+text', text=df_n['ID'], textposition="top center",
        marker=dict(size=6, color='blue', symbol='circle'), name="Nudos"
    ))
    
    # Dibujar Barras
    for idx, b in df_b.iterrows():
        try:
            ni = df_n[df_n['ID'] == b['N I']].iloc[0]
            nj = df_n[df_n['ID'] == b['N J']].iloc[0]
            fig.add_trace(go.Scatter3d(
                x=[ni['X'], nj['X']], y=[ni['Z'], nj['Z']], z=[ni['Y'], nj['Y']],
                mode='lines', line=dict(color='silver', width=4), name=f"B{idx+1}", hoverinfo="text", text=f"Barra {idx+1}: {b['N I']}-{b['N J']}"
            ))
        except: pass

    # Dibujar Apoyos (Conos Rojos Base)
    for idx, s in df_sup.iterrows():
        try:
            n = df_n[df_n['ID'] == s['Nudo']].iloc[0]
            info = "Empotrado" if s['Fx'] and s['Fy'] and s['Fz'] and s['Mx'] and s['My'] and s['Mz'] else "Apoyado"
            fig.add_trace(go.Scatter3d(
                x=[n['X']], y=[n['Z']], z=[n['Y']], mode='markers',
                marker=dict(size=8, color='red', symbol='diamond'), name="Apoyo", hovertext=info
            ))
        except: pass

    # Cargas (Vectores Verdes) - Plotted as lines with conical heads theoretically, here simplified to distinct markers and text
    for idx, c in df_load.iterrows():
        try:
            n = df_n[df_n['ID'] == c['Nudo']].iloc[0]
            txt_c = ""
            if c['FX (kN)'] != 0: txt_c += f" FX={c['FX (kN)']}"
            if c['FY (kN)'] != 0: txt_c += f" FY={c['FY (kN)']}"
            if c['FZ (kN)'] != 0: txt_c += f" FZ={c['FZ (kN)']}"
            if txt_c != "":
                fig.add_trace(go.Scatter3d(
                    x=[n['X']], y=[n['Z']], z=[n['Y']], mode='markers+text', text=[txt_c], textposition="bottom center",
                    textfont=dict(color="green", size=10), marker=dict(size=12, color='green', symbol='x'), name="Carga"
                ))
        except: pass

    # View layout (Z up in engineering => Y in plotly)
    fig.update_layout(
        scene=dict(
            xaxis_title='X (m)', yaxis_title='Z Profundidad (m)', zaxis_title='Y Elevación (m)',
            xaxis=dict(showgrid=True, gridcolor='gray'), yaxis=dict(showgrid=True, gridcolor='gray'), zaxis=dict(showgrid=True, gridcolor='gray'),
            aspectmode='data'
        ),
        margin=dict(r=10, l=10, b=10, t=30), title="Visualizador 3D Espacial (Live)",
        plot_bgcolor='black', paper_bgcolor='#1e1e1e'
    )
    return fig

# ─────────────────────────────────────────────
# UI PRINCIPAL
# ─────────────────────────────────────────────
st.info("💡 **Tip Interactividad:** Todos los cambios numéricos se reflejan geométricamente en **Tiempo Real** a la derecha.")
c_ui1, c_ui2 = st.columns([1, 1.2])

with c_ui1:
    st.subheader("1. Coordenadas Espaciales Nodos (X, Y, Z)")
    st.session_state.nudos3d_df = st.data_editor(st.session_state.nudos3d_df, num_rows="dynamic", use_container_width=True, height=200)
    
    st.subheader("2. Conectividad y Secciones de Barras")
    st.session_state.barras3d_df = st.data_editor(st.session_state.barras3d_df, num_rows="dynamic", use_container_width=True, height=200)
    
    st.subheader("3. Condiciones de Frontera (Apoyos Ceros)")
    st.session_state.apoyos3d_df = st.data_editor(st.session_state.apoyos3d_df, num_rows="dynamic", use_container_width=True, height=150)
    
    st.subheader("4. Fuerzas Externas Aplicadas (Nodales)")
    st.session_state.cargas3d_df = st.data_editor(st.session_state.cargas3d_df, num_rows="dynamic", use_container_width=True, height=150)

with c_ui2:
    st.plotly_chart(plot_frame_3d(st.session_state.nudos3d_df, st.session_state.barras3d_df, st.session_state.apoyos3d_df, st.session_state.cargas3d_df), use_container_width=True, height=800)

st.markdown("---")
# ─────────────────────────────────────────────
# CALCULO ENGINE (3D Frame)
# ─────────────────────────────────────────────
st.header(_t("⚡ Solver Matricial 3D (6 GDL por Nodo)", "⚡ 3D Matrix Solver (6 DOF per Node)"))

if st.button("▶️ Ejecutar Análisis Espacial 3D", type="primary"):
    with st.spinner("Ensamblando Matriz de Rigidez Espacial [K]..."):
        nodes = st.session_state.nudos3d_df.copy().dropna()
        elements = st.session_state.barras3d_df.copy().dropna()
        supports = st.session_state.apoyos3d_df.copy().dropna()
        loads = st.session_state.cargas3d_df.copy().dropna()
        
        num_nudos = len(nodes)
        num_gdl = num_nudos * 6 # ux, uy, uz, rx, ry, rz
        node_ids = nodes['ID'].tolist()
        id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
        
        F = np.zeros(num_gdl)
        for idx, c in loads.iterrows():
            if c['Nudo'] in id_to_idx:
                n_idx = id_to_idx[c['Nudo']]
                F[n_idx*6 + 0] += c.get('FX (kN)', 0.0)
                F[n_idx*6 + 1] += c.get('FY (kN)', 0.0) # Elevation
                F[n_idx*6 + 2] += c.get('FZ (kN)', 0.0) # Depth
                F[n_idx*6 + 3] += c.get('MX', 0.0)
                F[n_idx*6 + 4] += c.get('MY', 0.0)
                F[n_idx*6 + 5] += c.get('MZ', 0.0)
                
        K = np.zeros((num_gdl, num_gdl))
        element_dofs = []
        
        for idx, e in elements.iterrows():
            if e['N I'] not in id_to_idx or e['N J'] not in id_to_idx: continue
            i_idx = id_to_idx[e['N I']]; j_idx = id_to_idx[e['N J']]
            
            xi = nodes.loc[nodes['ID']==e['N I'], 'X'].values[0]
            yi = nodes.loc[nodes['ID']==e['N I'], 'Y'].values[0]
            zi = nodes.loc[nodes['ID']==e['N I'], 'Z'].values[0]
            xj = nodes.loc[nodes['ID']==e['N J'], 'X'].values[0]
            yj = nodes.loc[nodes['ID']==e['N J'], 'Y'].values[0]
            zj = nodes.loc[nodes['ID']==e['N J'], 'Z'].values[0]
            
            dx = xj - xi; dy = yj - yi; dz = zj - zi
            L = math.sqrt(dx**2 + dy**2 + dz**2)
            if L == 0: continue
            
            E = e['E (MPa)'] * 1e3 # kN/m2
            G = e['G (MPa)'] * 1e3
            A = e['A (cm²)'] / 1e4 # m2
            J = e['J (cm⁴)'] / 1e8 # m4
            Iy = e['Iy (cm⁴)'] / 1e8
            Iz = e['Iz (cm⁴)'] / 1e8
            
            # Local Stiffness Matrix 12x12
            k_local = np.zeros((12,12))
            
            a = E*A/L; b = 12*E*Iz/(L**3); c = 6*E*Iz/(L**2); d = 4*E*Iz/L; e_v = 2*E*Iz/L
            f = 12*E*Iy/(L**3); g = 6*E*Iy/(L**2); h = 4*E*Iy/L; i = 2*E*Iy/L; j = G*J/L
            
            k_local[0,0] = a; k_local[0,6] = -a
            k_local[6,0] = -a; k_local[6,6] = a
            
            k_local[1,1] = b; k_local[1,5] = c; k_local[1,7] = -b; k_local[1,11] = c
            k_local[5,1] = c; k_local[5,5] = d; k_local[5,7] = -c; k_local[5,11] = e_v
            k_local[7,1] = -b; k_local[7,5] = -c; k_local[7,7] = b; k_local[7,11] = -c
            k_local[11,1] = c; k_local[11,5] = e_v; k_local[11,7] = -c; k_local[11,11] = d
            
            k_local[2,2] = f; k_local[2,4] = -g; k_local[2,8] = -f; k_local[2,10] = -g
            k_local[4,2] = -g; k_local[4,4] = h; k_local[4,8] = g; k_local[4,10] = i
            k_local[8,2] = -f; k_local[8,4] = g; k_local[8,8] = f; k_local[8,10] = g
            k_local[10,2] = -g; k_local[10,4] = i; k_local[10,8] = g; k_local[10,10] = h
            
            k_local[3,3] = j; k_local[3,9] = -j
            k_local[9,3] = -j; k_local[9,9] = j
            
            # Transformation Matrix 3D
            cx = dx/L; cy = dy/L; cz = dz/L
            Lambda = np.zeros((3,3))
            
            # Handling vertical members
            if math.isclose(cx, 0.0, abs_tol=1e-5) and math.isclose(cz, 0.0, abs_tol=1e-5):
                Lambda[0,1] = cy; Lambda[1,0] = -cy; Lambda[2,2] = 1.0
            else:
                cxz = math.sqrt(cx**2 + cz**2)
                Lambda[0,0] = cx; Lambda[0,1] = cy; Lambda[0,2] = cz
                Lambda[1,0] = -cx*cy/cxz; Lambda[1,1] = cxz; Lambda[1,2] = -cy*cz/cxz
                Lambda[2,0] = -cz/cxz; Lambda[2,1] = 0; Lambda[2,2] = cx/cxz
                
            T = np.zeros((12,12))
            T[0:3, 0:3] = Lambda; T[3:6, 3:6] = Lambda
            T[6:9, 6:9] = Lambda; T[9:12, 9:12] = Lambda
            
            k_glob = T.T @ k_local @ T
            
            dofs = [
                i_idx*6, i_idx*6+1, i_idx*6+2, i_idx*6+3, i_idx*6+4, i_idx*6+5,
                j_idx*6, j_idx*6+1, j_idx*6+2, j_idx*6+3, j_idx*6+4, j_idx*6+5
            ]
            for r in range(12):
                for col in range(12):
                    K[dofs[r], dofs[col]] += k_glob[r,col]
            element_dofs.append(dofs)
            
        K_solve = np.copy(K)
        penalty = 1e12
        for idx, s in supports.iterrows():
            if s['Nudo'] in id_to_idx:
                n_idx = id_to_idx[s['Nudo']]
                if s.get('Fx', False): K_solve[n_idx*6+0, n_idx*6+0] += penalty
                if s.get('Fy', False): K_solve[n_idx*6+1, n_idx*6+1] += penalty
                if s.get('Fz', False): K_solve[n_idx*6+2, n_idx*6+2] += penalty
                if s.get('Mx', False): K_solve[n_idx*6+3, n_idx*6+3] += penalty
                if s.get('My', False): K_solve[n_idx*6+4, n_idx*6+4] += penalty
                if s.get('Mz', False): K_solve[n_idx*6+5, n_idx*6+5] += penalty
                
        try:
            U = np.linalg.solve(K_solve, F)
            R = K @ U
            st.success("✅ Sistema Matricial 3D de {}x{} Resuelto Exitosamente.".format(num_gdl, num_gdl))
            
            df_desp = []
            for nid in node_ids:
                n_idx = id_to_idx[nid]
                df_desp.append({
                    "Nudo": nid, "Dx (mm)": U[n_idx*6+0]*1000, "Dy (mm)": U[n_idx*6+1]*1000, "Dz (mm)": U[n_idx*6+2]*1000,
                    "Rx (rad)": U[n_idx*6+3], "Ry (rad)": U[n_idx*6+4], "Rz (rad)": U[n_idx*6+5]
                })
            
            df_reac = []
            for idx, s in supports.iterrows():
                n_idx = id_to_idx[s['Nudo']]
                df_reac.append({
                    "Nudo Apoyo": s['Nudo'], 
                    "Rx (kN)": R[n_idx*6+0] if s.get('Fx') else 0.0,
                    "Ry Elev (kN)": R[n_idx*6+1] if s.get('Fy') else 0.0,
                    "Rz Prof (kN)": R[n_idx*6+2] if s.get('Fz') else 0.0,
                    "Mx": R[n_idx*6+3] if s.get('Mx') else 0.0,
                    "My": R[n_idx*6+4] if s.get('My') else 0.0,
                    "Mz": R[n_idx*6+5] if s.get('Mz') else 0.0
                })
                
            res_c1, res_c2 = st.columns(2)
            res_c1.subheader("Desplazamientos Globales (U)")
            res_c1.dataframe(pd.DataFrame(df_desp).style.format("{:.5f}"), use_container_width=True)
            res_c2.subheader("Reacciones Neta en Apoyos (R)")
            res_c2.dataframe(pd.DataFrame(df_reac).style.format("{:.3f}"), use_container_width=True)
            
            # Deformada 3D
            st.subheader("💡 Vista Amplificada Deformada 3D")
            fig_def = plot_frame_3d(nodes, elements, supports, pd.DataFrame()) # Base clean
            amp = 20.0
            # Redraw with amplification
            for i, e in elements.iterrows():
                ni = nodes[nodes['ID'] == e['N I']].iloc[0]
                nj = nodes[nodes['ID'] == e['N J']].iloc[0]
                i_idx = id_to_idx[e['N I']]; j_idx = id_to_idx[e['N J']]
                
                xi_def = ni['X'] + U[i_idx*6+0]*amp
                yi_def = ni['Y'] + U[i_idx*6+1]*amp
                zi_def = ni['Z'] + U[i_idx*6+2]*amp
                
                xj_def = nj['X'] + U[j_idx*6+0]*amp
                yj_def = nj['Y'] + U[j_idx*6+1]*amp
                zj_def = nj['Z'] + U[j_idx*6+2]*amp
                
                fig_def.add_trace(go.Scatter3d(
                    x=[xi_def, xj_def], y=[zi_def, zj_def], z=[yi_def, yj_def],
                    mode='lines+markers', line=dict(color='magenta', width=5), marker=dict(size=4, color='white'), name=f"Def {e['N I']}-{e['N J']}", showlegend=False
                ))
            fig_def.update_layout(title="Deformada 3D (Escalax20)")
            st.plotly_chart(fig_def, use_container_width=True, height=600)
            
        except np.linalg.LinAlgError:
            st.error("Error: Matriz Singular. Te faltan ecuaciones de restricción geométrica o barras desconectadas.")
