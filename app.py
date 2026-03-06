import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

st.set_page_config(page_title="Diagrama Interacción Columna NSR-10", layout="wide")

st.title("Diagrama de Interacción de Columna (NSR-10)")
st.markdown("Generación del diagrama de interacción **P–M** para columnas de concreto reforzadas según la normativa colombiana NSR-10.")

# --- DICCIONARIOS DE ACERO ---
REBAR_US = {
    "#3 (3/8\")": 0.71,
    "#4 (1/2\")": 1.29,
    "#5 (5/8\")": 1.99,
    "#6 (3/4\")": 2.84,
    "#7 (7/8\")": 3.87,
    "#8 (1\")": 5.10,
    "#9 (1 1/8\")": 6.45,
    "#10 (1 1/4\")": 7.92
}

REBAR_MM = {
    "10 mm": 0.785,
    "12 mm": 1.131,
    "14 mm": 1.539,
    "16 mm": 2.011,
    "18 mm": 2.545,
    "20 mm": 3.142,
    "22 mm": 3.801,
    "25 mm": 4.909,
    "28 mm": 6.158,
    "32 mm": 8.042
}

# --- SIDEBAR (INPUTS) ---
st.sidebar.header("1. Materiales")
fc_unit = st.sidebar.radio("Unidad de f'c:", ["MPa", "PSI", "kg/cm²"], horizontal=True)

if fc_unit == "PSI":
    psi_options = {
        "2500 PSI (≈ 17.2 MPa)": 2500,
        "3000 PSI (≈ 20.7 MPa)": 3000,
        "3500 PSI (≈ 24.1 MPa)": 3500,
        "4000 PSI (≈ 27.6 MPa)": 4000,
        "4500 PSI (≈ 31.0 MPa)": 4500,
        "5000 PSI (≈ 34.5 MPa)": 5000,
        "Personalizado": None
    }
    psi_choice = st.sidebar.selectbox("Resistencia f'c [PSI]", list(psi_options.keys()), index=1)
    if psi_options[psi_choice] is not None:
        fc_psi = float(psi_options[psi_choice])
    else:
        fc_psi = st.sidebar.number_input("f'c personalizado [PSI]", min_value=2000.0, max_value=12000.0, value=3000.0, step=100.0)
    fc = fc_psi * 0.00689476  # PSI → MPa
    st.sidebar.info(f"f'c = {fc_psi:.0f} PSI → **{fc:.2f} MPa**")

elif fc_unit == "kg/cm²":
    # Valores típicos en Colombia en kg/cm²
    kgcm2_options = {
        "175 kg/cm² (≈ 17.2 MPa)": 175,
        "210 kg/cm² (≈ 20.6 MPa)": 210,
        "250 kg/cm² (≈ 24.5 MPa)": 250,
        "280 kg/cm² (≈ 27.5 MPa)": 280,
        "350 kg/cm² (≈ 34.3 MPa)": 350,
        "420 kg/cm² (≈ 41.2 MPa)": 420,
        "Personalizado": None
    }
    kgcm2_choice = st.sidebar.selectbox("Resistencia f'c [kg/cm²]", list(kgcm2_options.keys()), index=1)
    if kgcm2_options[kgcm2_choice] is not None:
        fc_kgcm2 = float(kgcm2_options[kgcm2_choice])
    else:
        fc_kgcm2 = st.sidebar.number_input("f'c personalizado [kg/cm²]", min_value=100.0, max_value=1200.0, value=210.0, step=10.0)
    fc = fc_kgcm2 / 10.1972  # kg/cm² → MPa
    st.sidebar.info(f"f'c = {fc_kgcm2:.0f} kg/cm² → **{fc:.2f} MPa**")

else:
    fc = st.sidebar.number_input("Resistencia del Concreto (f'c) [MPa]", min_value=15.0, max_value=80.0, value=21.0, step=1.0)

fy = st.sidebar.number_input("Fluencia del Acero (fy) [MPa]", min_value=240.0, max_value=500.0, value=420.0, step=10.0)
Es = 200000.0 # MPa

st.sidebar.header("2. Geometría de la Sección")
b = st.sidebar.number_input("Base (b) [cm]", min_value=15.0, value=30.0, step=5.0)
h = st.sidebar.number_input("Altura (h) [cm]", min_value=15.0, value=40.0, step=5.0)
d_prime = st.sidebar.number_input("Recubrimiento al centroide (d') [cm]", min_value=2.0, value=5.0, step=0.5)

st.sidebar.header("3. Refuerzo Longitudinal")
unit_system = st.sidebar.radio("Sistema de Unidades de las Varillas:", ["Pulgadas (US)", "Milímetros (SI)"])

if unit_system == "Pulgadas (US)":
    rebar_dict = REBAR_US
    default_rebar = "#5 (5/8\")"
else:
    rebar_dict = REBAR_MM
    default_rebar = "16 mm"

rebar_type = st.sidebar.selectbox("Diámetro de las Varillas", list(rebar_dict.keys()), index=list(rebar_dict.keys()).index(default_rebar))
rebar_area = rebar_dict[rebar_type] # cm^2

num_filas_h = st.sidebar.number_input("# de filas Acero Horiz (Superior e Inferior)", min_value=2, max_value=15, value=2, step=1)
num_filas_v = st.sidebar.number_input("# de filas Acero Vert (Laterales)", min_value=2, max_value=15, value=2, step=1)

# Procesar la distribución a "Capas" para el cálculo del motor
# En una columna rectangular:
# Las varillas de las "filas horizontales" se ubican en la primera y la última capa (caras superior e inferior en el dibujo transversal)
# Las "filas verticales" menos 2 (las esquinas ya contadas) se distribuyen en capas intermedias.
layers = []

# La capa 1 está a profundidad d' (cara en compresión)
# Contiene 'num_filas_h' varillas
layers.append({'d': d_prime, 'As': num_filas_h * rebar_area})

# Si hay filas verticales intermedias (num_filas_v > 2)
num_capas_intermedias = num_filas_v - 2
if num_capas_intermedias > 0:
    # La distancia disponible para las capas intermedias es desde d' hasta (h - d')
    espacio_h = (h - 2*d_prime) / (num_capas_intermedias + 1)
    
    for i in range(1, num_capas_intermedias + 1):
        profundidad = d_prime + i * espacio_h
        # Cada capa intermedia transversalmente tiene 2 varillas (una a cada lado, es decir, filas verticales)
        layers.append({'d': profundidad, 'As': 2 * rebar_area})
        
# La última capa está a profundidad h - d' (cara en tracción)
layers.append({'d': h - d_prime, 'As': num_filas_h * rebar_area})

st.sidebar.markdown(f"**Total capas calculadas:** {len(layers)}")
st.sidebar.markdown(f"**Total varillas:** {num_filas_h * 2 + num_capas_intermedias * 2}")

st.sidebar.header("4. Factores de Referencia")
col_type = st.sidebar.selectbox("Tipo de Columna", ["Estribos (Tied)", "Espiral (Spiral)"])
if col_type == "Estribos (Tied)":
    phi_c_max = 0.65
    p_max_factor = 0.80
else:
    phi_c_max = 0.75
    p_max_factor = 0.85

st.sidebar.header("5. Verificación de Diseño")
# Agrega un selector de unidades globales de salida
unidades_salida = st.sidebar.radio("Unidades del Diagrama (Resultados):", ["KiloNewtons (kN, kN-m)", "Toneladas Fuerza (tonf, tonf-m)"])

# Conversion factors (1 kN ~ 0.10197 tonf)
if unidades_salida == "Toneladas Fuerza (tonf, tonf-m)":
    factor_fuerza = 0.1019716
    unidad_fuerza = "tonf"
    unidad_mom = "tonf-m"
else:
    factor_fuerza = 1.0
    unidad_fuerza = "kN"
    unidad_mom = "kN-m"

st.sidebar.markdown(f"Ingrese las cargas últimas (mayoradas) en **{unidad_fuerza}** y **{unidad_mom}** para verificar si caen dentro del diagrama.")
M_u_input = st.sidebar.number_input(f"Momento Último (Mu) [{unidad_mom}]", value=round(45.0 * factor_fuerza, 2), step=round(10.0 * factor_fuerza, 2))
P_u_input = st.sidebar.number_input(f"Carga Axial Última (Pu) [{unidad_fuerza}]", value=round(2700.0 * factor_fuerza, 2), step=round(50.0 * factor_fuerza, 2))

# --- CÁLCULOS (MOTOR) ---
eps_cu = 0.003
eps_y = fy / Es

# Calcula beta_1 (NSR-10 C.10.2.7.3)
if fc <= 28:
    beta_1 = 0.85
elif fc < 55:
    beta_1 = 0.85 - 0.05 * (fc - 28) / 7.0
else:
    beta_1 = 0.65
beta_1 = max(beta_1, 0.65) # Límite inferior general

Ag = b * h
Ast = sum([layer['As'] for layer in layers]) # cm^2

# Generar rango de eje neutro c
# Para cubrir tracción pura, c se acerca a cero
# Para cubrir compresión pura, c va a infinito
c_vals = np.concatenate([
    np.linspace(1e-5, h, 100),
    np.linspace(h, h*10, 50)
])

P_n_list = []
M_n_list = []
phi_P_n_list = []
phi_M_n_list = []

Po = (0.85 * fc * (Ag - Ast) + fy * Ast) / 10.0 # Po in toneladas (aprox dividing by 10/1000 cm to kN etc? Let's use kN)
# Unit conversions: 
# fc (MPa) -> N/mm^2 = 10 \approx kgf/cm^2. Mpa is N/mm^2.
# Dimensions in cm -> convert to mm for calculations to get Newtons, then to kN (divide by 1000).
b_mm = b * 10
h_mm = h * 10

Po_kN = (0.85 * fc * (Ag * 100 - Ast * 100) + fy * Ast * 100) / 1000.0

for c_cm in c_vals:
    c_mm = c_cm * 10
    a_mm = beta_1 * c_mm
    
    # Fuerzas del concreto
    # El bloque equivalente solo puede ser tan grande como la sección
    a_eff = min(a_mm, h_mm) 
    if c_mm > 0:
        Cc = 0.85 * fc * a_eff * b_mm # Newtons
    else:
        Cc = 0
        
    Mc = Cc * (h_mm / 2.0 - a_eff / 2.0) # N-mm
    
    Ps = 0
    Ms = 0
    eps_t = 0 # Deformación de la capa más traccionada
    
    for layer in layers:
        d_i_mm = layer['d'] * 10
        As_i = layer['As'] * 100 # mm^2
        
        # Deformación del acero (Compatibility)
        eps_s = eps_cu * (c_mm - d_i_mm) / c_mm
        
        if d_i_mm >= max([l['d']*10 for l in layers]):
            eps_t = eps_s # capa extrema en tracción
            
        # Esfuerzo en el acero
        fs = Es * eps_s
        if fs > fy:
            fs = fy
        elif fs < -fy:
            fs = -fy
            
        # Descontar el volumen de concreto geométricamente si la varilla está en compresión
        if a_eff > d_i_mm and fs > 0:
            fs = fs - 0.85 * fc
            
        F_si = As_i * fs # Newtons
        M_si = F_si * (h_mm / 2.0 - d_i_mm) # N-mm
        
        Ps += F_si
        Ms += M_si
        
    # Capacidad Nominal
    Pn = (Cc + Ps) / 1000.0 # kN
    Mn = (Mc + Ms) / 1000000.0 # kN-m
    
    # Calcular Factor phi 
    # eps_t es negativo en tracción bajo nuestra convención (c_mm - d_i_mm < 0)
    eps_t_tens = -eps_t 
    
    if eps_t_tens <= eps_y:
        phi = phi_c_max
    elif eps_t_tens >= 0.005:
        phi = 0.90
    else:
        # Interpolación lineal NSR-10
        phi = phi_c_max + (0.90 - phi_c_max) * (eps_t_tens - eps_y) / (0.005 - eps_y)
        
    # Capacidad de Diseño
    phi_Pn = phi * Pn
    phi_Mn = phi * Mn
    
    # Limitar por compresión máxima Pn,max (NSR-10)
    Pn_max = p_max_factor * Po_kN
    phi_Pn_max = phi_c_max * Pn_max
    
    if Pn > Pn_max:
        # En la gráfica nominal truncamos al máximo Pn
        Pn = Pn_max
        # No truncamos el momento para simplificar la vertical en el límite, calculamos un Mn asociado a Pn_max en grafica
    if phi_Pn > phi_Pn_max:
        phi_Pn = phi_Pn_max
        
    P_n_list.append(Pn)
    M_n_list.append(Mn)
    phi_P_n_list.append(phi_Pn)
    phi_M_n_list.append(phi_Mn)

# --- TRATAMIENTO DE LA GRÁFICA (TRUNCADO CUALITATIVO COMO NSR-10) ---
# En NSR-10, la parte superior de la gráfica presenta un "corte" horizontal.
P_n_arr = np.array(P_n_list) * factor_fuerza
M_n_arr = np.array(M_n_list) * factor_fuerza
phi_P_n_arr = np.array(phi_P_n_list) * factor_fuerza
phi_M_n_arr = np.array(phi_M_n_list) * factor_fuerza

# Punto de tracción pura (aproximado)
Pt = -fy * Ast * 100 / 1000.0 * factor_fuerza

# Variables con unidades ajustadas
Pn_max = Pn_max * factor_fuerza
phi_Pn_max = phi_Pn_max * factor_fuerza

# --- GRAFICAR ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Gráfica P–M")
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Identificar puntos máximos
    P_nominal_max = Pn_max
    P_diseno_max = phi_Pn_max
    
    idx_M_nom_max = np.argmax(M_n_arr)
    M_nominal_max = M_n_arr[idx_M_nom_max]
    P_M_nom_max = P_n_arr[idx_M_nom_max]
    
    idx_M_dis_max = np.argmax(phi_M_n_arr)
    M_diseno_max = phi_M_n_arr[idx_M_dis_max]
    P_M_dis_max = phi_P_n_arr[idx_M_dis_max]
    
    # Curva Nominal
    ax.plot(M_n_arr, P_n_arr, label=r"Resistencia Nominal ($P_n, M_n$)", color="blue", linestyle="--")
    # Curva Diseño
    ax.plot(phi_M_n_arr, phi_P_n_arr, label=r"Resistencia de Diseño ($\phi P_n, \phi M_n$)", color="red", linewidth=2)
    
    # Anotaciones en los Ejes de valores máximos (Estilo de la imagen)
    # Pmax Nominal
    ax.annotate(f"{P_nominal_max:.2f} [{unidad_fuerza}]", xy=(0, P_nominal_max), xytext=(5, 5), textcoords="offset points", ha='left', va='bottom', fontsize=8, color='blue')
    # Pmax Diseño
    ax.annotate(f"{P_diseno_max:.2f} [{unidad_fuerza}]", xy=(0, P_diseno_max), xytext=(5, -5), textcoords="offset points", ha='left', va='top', fontsize=8, color='red')
    
    # Líneas límite para Momento Máximo (Nominal)
    ax.plot([M_nominal_max, M_nominal_max], [0, P_M_nom_max], color='gray', linestyle='--', alpha=0.5)
    ax.annotate(f"{M_nominal_max:.2f} [{unidad_mom}]", xy=(M_nominal_max, 0), xytext=(0, -15), textcoords="offset points", ha='center', va='top', fontsize=8)
    
    # Líneas límite para Momento Máximo (Diseño)
    ax.plot([M_diseno_max, M_diseno_max], [0, P_M_dis_max], color='gray', linestyle='--', alpha=0.5)
    ax.annotate(f"{M_diseno_max:.2f} [{unidad_mom}]", xy=(M_diseno_max, 0), xytext=(0, -15), textcoords="offset points", ha='center', va='top', fontsize=8)
    
    # Anotaciones de Tracción pura
    ax.annotate(f"{Pt:.2f} [{unidad_fuerza}]", xy=(0, Pt), xytext=(5, -5), textcoords="offset points", ha='left', va='top', fontsize=8, color='blue')
    
    # \phi_t = 0.9 for pure tension
    ax.annotate(f"{0.9*Pt:.2f} [{unidad_fuerza}]", xy=(0, 0.9*Pt), xytext=(5, 5), textcoords="offset points", ha='left', va='bottom', fontsize=8, color='red')
    
    # Eje horizontal en y=0
    ax.axhline(0, color='black', linewidth=1)
    
    # Punto de verificación de diseño (siempre se dibuja)
    ax.plot(M_u_input, P_u_input, marker='o', markersize=8, color='green', label=f"Punto de Diseño", markeredgecolor='black', zorder=5)
    
    # Líneas punteadas hacia los ejes
    ax.plot([M_u_input, M_u_input], [0, P_u_input], color='green', linestyle=':', alpha=0.7)
    ax.plot([0, M_u_input], [P_u_input, P_u_input], color='green', linestyle=':', alpha=0.7)
    
    ax.annotate(f"[{M_u_input:g}{unidad_mom} : {P_u_input:g}{unidad_fuerza}]", 
                xy=(M_u_input, P_u_input), 
                xytext=(5, 5), textcoords="offset points", 
                fontsize=9, weight='bold', color='darkgreen')
    
    ax.set_xlabel(f"Momento Flector $M$ [{unidad_mom}]")
    ax.set_ylabel(f"Carga Axial $P$ [{unidad_fuerza}]")
    ax.set_xlim(left=0) # El eje Y parte desde cero
    ax.set_title(f"Diagrama de Interacción NSR-10\nColumna {b}x{h}cm, f'c={fc} MPa, fy={fy} MPa")
    ax.grid(True, linestyle=":", alpha=0.7)
    ax.legend(loc="upper right")
    
    st.pyplot(fig)

with col2:
    st.subheader("Resumen de Resultados")
    n_barras_total = num_filas_h * 2 + (num_filas_v - 2) * 2
    cuantia = Ast / Ag * 100

    st.markdown("### Verificación de Cuantía (NSR-10 C.10.9)")
    
    data_cuantia = {
        "Parámetro": [
            "Base (b)",
            "Altura (h)",
            "Área Bruta: Ag = b × h",
            f"# Varillas Horiz. (2 filas × {num_filas_h})",
            f"# Varillas Vert. intermedias ({num_filas_v-2} × 2)",
            "Total varillas (n)",
            f"Área por varilla (Ab) — {rebar_type}",
            "Área Acero: Ast = n × Ab",
            "Cuantía: ρ = (Ast / Ag) × 100%",
            "Límite mínimo NSR-10 C.10.9.1",
            "Límite máximo NSR-10 C.10.9.1",
        ],
        "Valor": [
            f"{b:.1f} cm",
            f"{h:.1f} cm",
            f"{Ag:.1f} cm²",
            f"{num_filas_h * 2} barras",
            f"{(num_filas_v - 2) * 2} barras",
            f"{n_barras_total} barras",
            f"{rebar_area:.3f} cm²",
            f"{Ast:.3f} cm²",
            f"{cuantia:.4f}%",
            "1.00%",
            "4.00%",
        ],
        "Estado": [
            "—","—","—","—","—","—","—","—",
            "✅ CUMPLE" if 1.0 <= cuantia <= 4.0 else ("⚠️ ALTA" if 4.0 < cuantia <= 8.0 else "❌ NO CUMPLE"),
            "—","—"
        ]
    }
    st.dataframe(pd.DataFrame(data_cuantia), use_container_width=True, hide_index=True)

    if 1.0 <= cuantia <= 4.0:
        st.success(f"✅ Cuantía ρ = {cuantia:.2f}% — Cumple NSR-10 C.10.9 (1% a 4%)")
    elif 4.0 < cuantia <= 8.0:
        st.warning(f"⚠️ Cuantía ρ = {cuantia:.2f}% — Alta, límite NSR-10 es 4%")
    else:
        st.error(f"❌ Cuantía ρ = {cuantia:.2f}% — No cumple, mínimo 1% según NSR-10 C.10.9.1")

    st.markdown("---")
    st.markdown("### Puntos Clave de Diseño")
    data_puntos = {
        "Descripción": [
            "Capacidad axial bruta (Po)",
            f"Pn,máx nominal ({p_max_factor:.0%} × Po)",
            f"φPn,máx de diseño (φ={phi_c_max} × Pn,máx)",
            "Tracción pura nominal (Pt = −fy × Ast)",
            "φTracción pura diseño (φt = 0.9 × Pt)",
        ],
        f"Valor [{unidad_fuerza}]": [
            f"{(Pn_max / p_max_factor):.1f}",
            f"{Pn_max:.1f}",
            f"{phi_Pn_max:.1f}",
            f"{Pt:.1f}",
            f"{0.9*Pt:.1f}",
        ]
    }
    st.dataframe(pd.DataFrame(data_puntos), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("Desarrollado de acuerdo con los lineamientos de diseño de la norma **NSR-10 (C.10)**.")

