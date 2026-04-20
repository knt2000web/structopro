import streamlit as st
import json
import pandas as pd
import datetime

from auth import sign_up_user, sign_in_user, sign_out_user, get_current_user, save_project_to_db, get_projects_from_db, DummyUser
from streamlit_cookies_controller import CookieController
from utils.icons import GLOBAL_CSS

st.set_page_config(
    page_title="StructoPro — Suite Estructural",
    page_icon="SP",
    layout="wide",
)

# CSS Global mejorado: jerarquía visual, sidebar ordenado, panel de veredicto
GLOBAL_UX_CSS = """
<style>
/* ── Sidebar mejorado ─────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
}
section[data-testid="stSidebar"] .stExpander {
    border: 1px solid #21262d;
    border-radius: 8px;
    margin-bottom: 6px;
    background: #161b22;
}
section[data-testid="stSidebar"] .stExpander details summary {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: .04em;
    text-transform: uppercase;
    color: #8b949e;
    padding: 8px 12px;
}
section[data-testid="stSidebar"] .stExpander details[open] summary {
    color: #3fb950;
}

/* ── Nav category headers ────────────────────────────────────── */
.nav-category {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #8b949e;
    padding: 10px 4px 4px;
    margin-top: 6px;
}
.nav-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 7px 10px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: #c9d1d9;
    font-size: 13px;
    cursor: pointer;
    text-align: left;
    margin-bottom: 2px;
    transition: background 150ms;
}
.nav-btn:hover { background: #21262d; }
.nav-btn.active { background: rgba(63,185,80,.15); color: #3fb950; font-weight: 600; }

/* ── Panel de Veredicto Global ──────────────────────────────── */
.verdict-panel {
    display: grid;
    grid-template-columns: auto 1fr 1fr 1fr;
    gap: 0;
    border: 1px solid #30363d;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 24px;
    font-family: 'Satoshi', system-ui, sans-serif;
}
.verdict-semaforo {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px 20px;
    font-size: 2rem;
    background: #161b22;
    border-right: 1px solid #30363d;
}
.verdict-kpi {
    padding: 12px 16px;
    background: #161b22;
    border-right: 1px solid #30363d;
}
.verdict-kpi:last-child { border-right: none; }
.verdict-kpi .label { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: #8b949e; }
.verdict-kpi .value { font-size: 1.25rem; font-weight: 700; color: #e6edf3; line-height: 1.2; }
.verdict-kpi .ref   { font-size: 11px; color: #8b949e; }
.verdict-ok  .value { color: #3fb950; }
.verdict-bad .value { color: #da3633; }

/* ── Ocultar header Streamlit ───────────────────────────────── */
header[data-testid="stHeader"] { background: transparent; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
st.markdown(GLOBAL_UX_CSS, unsafe_allow_html=True)

try:
    cookie_controller = CookieController()
except Exception:
    cookie_controller = None

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if st.session_state.auth_user is None and cookie_controller:
    saved_email = cookie_controller.get('session_email')
    saved_id = cookie_controller.get('session_user_id')
    saved_token = cookie_controller.get('session_token')
    if saved_email and saved_id:
        st.session_state.auth_user = DummyUser(email=saved_email, id=saved_id, access_token=saved_token)

if "cv_s_diseno" not in st.session_state:
    st.session_state["cv_s_diseno"] = 15.0

if "historial_disenos" not in st.session_state:
    st.session_state.historial_disenos = []

def login_view():
    st.title("StructoPro")
    st.subheader("Acceso a la plataforma")
    tab1, tab2 = st.tabs(["Iniciar sesión", "Registrarse"])
    with tab1:
        email_login = st.text_input("Correo electrónico", key="login_email")
        password_login = st.text_input("Contraseña", type="password", key="login_password")
        if st.button("Ingresar", use_container_width=True):
            try:
                response = sign_in_user(email_login, password_login)
                if response.user:
                    st.session_state.auth_user = response.user
                    if cookie_controller:
                        cookie_controller.set('session_email', response.user.email)
                        cookie_controller.set('session_user_id', response.user.id)
                        if hasattr(response.user, 'access_token'):
                            cookie_controller.set('session_token', response.user.access_token)
                    st.success("Inicio de sesión correcto")
                    from time import sleep
                    sleep(0.5)
                    st.rerun()
                else:
                    st.error("No se pudo iniciar sesión")
            except Exception as e:
                st.error(f"Error de acceso: {e}")
    with tab2:
        email_register = st.text_input("Correo electrónico", key="register_email")
        password_register = st.text_input("Contraseña", type="password", key="register_password")
        password_confirm = st.text_input("Confirmar contraseña", type="password", key="register_password_confirm")
        if st.button("Crear cuenta", use_container_width=True):
            if password_register != password_confirm:
                st.warning("Las contraseñas no coinciden")
            elif len(password_register) < 6:
                st.warning("La contraseña debe tener al menos 6 caracteres")
            else:
                try:
                    response = sign_up_user(email_register, password_register)
                    if response.user:
                        st.success("Cuenta creada correctamente.")
                    else:
                        st.error("No se pudo crear la cuenta")
                except Exception as e:
                    st.error(f"Error de registro: {e}")

def logout_button():
    if st.sidebar.button(" Cerrar sesión", use_container_width=True):
        try:
            sign_out_user()
        except:
            pass
        st.session_state.auth_user = None
        if cookie_controller:
            try:
                cookie_controller.remove('session_email')
                cookie_controller.remove('session_user_id')
                cookie_controller.remove('session_token')
            except Exception:
                pass
        st.rerun()

try:
    current_user = get_current_user()
    if current_user and getattr(current_user, "user", None):
        st.session_state.auth_user = current_user.user
except:
    pass

# Damos a conocer las páginas a Streamlit para que sobrescriba el sidebar por defecto
def run_home():
    import datetime as _dt
    st.markdown("""
<style>
@import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&f[]=cabinet-grotesk@700,800&display=swap');
:root{--bg:#0d1117;--surface:#161b22;--surface2:#21262d;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--primary:#2ea043;--primary-h:#3fb950;--accent:#1f6feb;--warn:#d29922;--error:#da3633}
*{box-sizing:border-box;margin:0;padding:0}
.hero{display:flex;flex-direction:column;align-items:flex-start;padding:48px 0 36px;border-bottom:1px solid var(--border);margin-bottom:40px}
.hero-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(46,160,67,0.12);border:1px solid rgba(46,160,67,0.3);border-radius:20px;padding:4px 14px;font-size:12px;font-weight:600;color:var(--primary-h);letter-spacing:.04em;text-transform:uppercase;margin-bottom:20px;font-family:'Satoshi',system-ui,sans-serif}
.hero-title{font-family:'Cabinet Grotesk','Satoshi',sans-serif;font-size:clamp(1.9rem,4vw,3rem);font-weight:800;color:var(--text);line-height:1.15;letter-spacing:-.02em;margin-bottom:16px}
.hero-title span{color:var(--primary-h)}
.hero-desc{font-size:1rem;color:var(--muted);font-family:'Satoshi',system-ui,sans-serif;max-width:640px;line-height:1.75;margin-bottom:28px}
.hero-pills{display:flex;flex-wrap:wrap;gap:8px}
.pill{display:inline-flex;align-items:center;gap:6px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:5px 12px;font-size:12px;color:var(--muted);font-weight:500;font-family:'Satoshi',system-ui,sans-serif}
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:48px}
.stat-cell{background:var(--surface);padding:20px 24px}
.stat-num{font-size:1.7rem;font-weight:700;color:var(--text);font-family:'Cabinet Grotesk',sans-serif;line-height:1}
.stat-num span{color:var(--primary-h)}
.stat-label{font-size:12px;color:var(--muted);margin-top:4px;font-family:'Satoshi',sans-serif}
.section-title{font-size:.72rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.09em;margin-bottom:16px;font-family:'Satoshi',sans-serif}
.modules-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px;margin-bottom:48px}
.module-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px 22px;transition:border-color 200ms ease,background 200ms ease;position:relative;overflow:hidden;font-family:'Satoshi',system-ui,sans-serif}
.module-card:hover{border-color:rgba(63,185,80,.45);background:#1a2620}
.module-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--card-accent,#2ea043);opacity:0;transition:opacity 200ms ease}
.module-card:hover::before{opacity:1}
.card-header{display:flex;align-items:flex-start;gap:14px;margin-bottom:12px}
.card-icon{width:40px;height:40px;flex-shrink:0;background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;display:flex;align-items:center;justify-content:center}
.card-title{font-size:.93rem;font-weight:700;color:var(--text);line-height:1.3}
.card-sub{font-size:.76rem;color:var(--muted);margin-top:3px}
.card-desc{font-size:.82rem;color:var(--muted);line-height:1.65;margin-bottom:14px}
.tag-row{display:flex;flex-wrap:wrap;gap:5px}
.tag{font-size:11px;font-weight:500;padding:3px 9px;border-radius:4px;border:1px solid var(--border);color:var(--muted);background:var(--surface2)}
.tag.g{color:#3fb950;border-color:rgba(63,185,80,.3);background:rgba(63,185,80,.08)}
.tag.b{color:#79c0ff;border-color:rgba(121,192,255,.3);background:rgba(121,192,255,.08)}
.tag.o{color:#ffa657;border-color:rgba(255,166,87,.3);background:rgba(255,166,87,.08)}
.tag.p{color:#d2a8ff;border-color:rgba(210,168,255,.3);background:rgba(210,168,255,.08)}
.tag.r{color:#ff7b72;border-color:rgba(255,123,114,.3);background:rgba(255,123,114,.08)}
.hs-divider{height:1px;background:var(--border);margin:40px 0}
.footer{border-top:1px solid var(--border);padding:28px 0 8px;display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:16px;font-family:'Satoshi',sans-serif}
.footer-logo{display:flex;align-items:center;gap:10px}
.footer-name{font-size:.85rem;font-weight:700;color:var(--text)}
.footer-copy{font-size:.72rem;color:var(--muted);margin-top:2px}
.footer-note{font-size:.72rem;color:var(--muted);max-width:440px;line-height:1.6}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="hero">
  <div class="hero-badge">
    <svg width="8" height="8" viewBox="0 0 8 8" fill="#3fb950"><circle cx="4" cy="4" r="4"/></svg>
    v2.0 &nbsp;·&nbsp; Multi-Norma &nbsp;·&nbsp; 2026
  </div>
  <h1 class="hero-title">Suite de Diseño —<br><span>Hormigón Armado</span></h1>
  <p class="hero-desc">
    Plataforma profesional de cálculo estructural para ingenieros civiles.
    Diseño completo de columnas, vigas, losas, cimentaciones y muros con
    10 normativas latinoamericanas, exportación BIM/DXF/DOCX y presupuesto APU en tiempo real.
  </p>
  <div class="hero-pills">
    <span class="pill">Calculo en tiempo real</span>
    <span class="pill">Exportacion IFC / BIM</span>
    <span class="pill">Memorias DOCX / DXF</span>
    <span class="pill"> 10 normativas</span>
    <span class="pill">Supabase Cloud</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="stats-row">
  <div class="stat-cell"><div class="stat-num">10<span>+</span></div><div class="stat-label">Normativas soportadas</div></div>
  <div class="stat-cell"><div class="stat-num">18<span>+</span></div><div class="stat-label">Módulos de cálculo</div></div>
  <div class="stat-cell"><div class="stat-num">6<span>+</span></div><div class="stat-label">Formatos de exportación</div></div>
  <div class="stat-cell"><div class="stat-num">3D<span> / 2D</span></div><div class="stat-label">Visualización interactiva</div></div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<p class="section-title">Módulos de cálculo disponibles</p>', unsafe_allow_html=True)
    # --- Tarjetas Maestras Detalladas ---
    st.markdown("""
<div class="modules-grid">
  <div class="module-card" style="--card-accent:#3fb950">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="1.8"><rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="18" rx="1"/></svg></div>
      <div><div class="card-title">Columnas — Diagrama P-M Biaxial</div><div class="card-sub">Módulo › Columnas_PM</div></div>
    </div>
    <p class="card-desc">Genera diagramas de interacción P-M en 3D (Superficie de Bresler). Verificación de esbeltez NSR-10, diseño de estribos sísmicos, magnificación de momentos, exportación IFC-BIM.</p>
    <div class="tag-row"><span class="tag g">Bresler 3D</span><span class="tag b">Esbeltez kL/r</span><span class="tag b">Estribos sísmicos</span><span class="tag o">IFC / DXF / DOCX</span></div>
  </div>

  <div class="module-card" style="--card-accent:#79c0ff">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#79c0ff" stroke-width="1.8"><rect x="2" y="9" width="20" height="6" rx="1"/></svg></div>
      <div><div class="card-title">Vigas y Losas — Diseño Completo</div><div class="card-sub">Módulo › Vigas_Losas</div></div>
    </div>
    <p class="card-desc">Diseño a flexión (rectangular y Viga T), cortante sísmico Vp, deflexiones Branson, losa en una dirección, punzonamiento NSR-10 C.11.11, longitudes de desarrollo.</p>
    <div class="tag-row"><span class="tag b">Viga Rectangular / T</span><span class="tag r">Cortante Vp sísmico</span><span class="tag b">Deflexión Branson</span><span class="tag o">Punzonamiento</span></div>
  </div>

  <div class="module-card" style="--card-accent:#d2a8ff">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d2a8ff" stroke-width="1.8"><rect x="2" y="15" width="20" height="6" rx="1"/><line x1="7" y1="15" x2="7" y2="4"/><line x1="12" y1="15" x2="12" y2="4"/><line x1="17" y1="15" x2="17" y2="4"/><line x1="4" y1="4" x2="20" y2="4"/></svg></div>
      <div><div class="card-title">Cimentaciones y Zapatas</div><div class="card-sub">Zapatas · Pilotes · Encepados</div></div>
    </div>
    <p class="card-desc">Diseño de zapatas aisladas, pilotes y cabezales. Muros en voladizo — estabilidad al deslizamiento, volcamiento y presiones netas. DXF rótulo ICONTEC.</p>
    <div class="tag-row"><span class="tag p">Zapatas</span><span class="tag p">Pilotes</span><span class="tag g">Estabilidad</span><span class="tag o">DXF ICONTEC</span></div>
  </div>

  <div class="module-card" style="--card-accent:#d29922">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d29922" stroke-width="1.8"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg></div>
      <div><div class="card-title">Presupuesto APU Mercado</div><div class="card-sub">Análisis de Precios Unitarios en vivo</div></div>
    </div>
    <p class="card-desc">Cotización de materiales con precios configurables. Calcula costo directo, A.I.U., utilidad e IVA. Multi-moneda. Exporta presupuesto en Excel.</p>
    <div class="tag-row"><span class="tag o">Precios configurables</span><span class="tag o">A.I.U. + IVA</span><span class="tag g">Excel .xlsx</span></div>
  </div>

  <div class="module-card" style="--card-accent:#ff7b72">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff7b72" stroke-width="1.8"><path d="M4 22h14a2 2 0 0 0 2-2V7.5L14.5 2H6a2 2 0 0 0-2 2v4"/><polyline points="14 2 14 8 20 8"/><path d="M2 15h10"/><path d="M5 12l2 3-2 3"/></svg></div>
      <div><div class="card-title">Predimensionamiento Maestro</div><div class="card-sub">Módulo › Predimensionamiento</div></div>
    </div>
    <p class="card-desc">Calculadora inicial rápida para dimensionar perfiles de vigas, pre-medidas de columnas y grosores de losas aligeradas/macizas de acuerdo con las limitantes de cuantías y longitudes.</p>
    <div class="tag-row"><span class="tag r">Rapido y Practico</span><span class="tag g">Reglas NSR-10</span></div>
  </div>

  <div class="module-card" style="--card-accent:#ffa657">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffa657" stroke-width="1.8"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/><line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22 8.5 12 15.5 2 8.5"/><polyline points="2 15.5 12 8.5 22 15.5"/><line x1="12" y1="2" x2="12" y2="8.5"/></svg></div>
      <div><div class="card-title">Generador Estructural 3D</div><div class="card-sub">Módulo › Generador_Maestro_3D</div></div>
    </div>
    <p class="card-desc">Generador interactivo de pórticos espaciales 3D. Define mallas de nodos de forma paramétrica, asigna secciones, tipos de material y exporta la matriz de conectividad para análisis.</p>
    <div class="tag-row"><span class="tag o">Paramétrico</span><span class="tag b">Analisis matricial</span></div>
  </div>

  <div class="module-card" style="--card-accent:#33b3ae">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#33b3ae" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg></div>
      <div><div class="card-title">Mampostería y Kontewall</div><div class="card-sub">Mamposteria · Morteros · Placa Fácil</div></div>
    </div>
    <p class="card-desc">Cálculo de muros en bloque estructural, diseño a corte, flexo-compresión, módulos Placa Fácil Bloquelón, Kontewall y dosificación de morteros estándar de construcción.</p>
    <div class="tag-row"><span class="tag b">Mamposteria</span><span class="tag p">Placa Facil</span><span class="tag g">Kontewall</span></div>
  </div>

  <div class="module-card" style="--card-accent:#8957e5">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8957e5" stroke-width="1.8"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg></div>
      <div><div class="card-title">Diseño Sísmico y Viento</div><div class="card-sub">Módulo › Espectro y Fuerzas</div></div>
    </div>
    <p class="card-desc">Generación del espectro elástico de diseño, cálculo de periodo fundamental, fuerza horizontal equivalente FHE y evaluación interactiva de carga de viento simplificada en cubiertas.</p>
    <div class="tag-row"><span class="tag g">Espectro</span><span class="tag b">FHE</span><span class="tag o">Viento</span><span class="tag r">Irregularidades</span></div>
  </div>
</div>
""", unsafe_allow_html=True)
    with c2s:
        st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px;font-family:'Satoshi',sans-serif;">
            <div style="width:28px;height:28px;border-radius:50%;background:#1f6feb;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:white;margin-bottom:12px">2</div>
            <div style="font-size:.88rem;font-weight:700;color:#e6edf3;margin-bottom:8px">Seleccionar módulo</div>
            <p style="font-size:.8rem;color:#8b949e;line-height:1.65">Usa las secciones categorizadas del menú lateral. Cada módulo tiene su flujo de datos, resultados y exportación.</p>
        </div>""", unsafe_allow_html=True)
    with c3s:
        st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px;font-family:'Satoshi',sans-serif;">
            <div style="width:28px;height:28px;border-radius:50%;background:#d29922;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:white;margin-bottom:12px">3</div>
            <div style="font-size:.88rem;font-weight:700;color:#e6edf3;margin-bottom:8px">Guardar y exportar</div>
            <p style="font-size:.8rem;color:#8b949e;line-height:1.65">Guarda en Supabase Cloud. Genera memoria DOCX, plano DXF o modelo IFC-BIM desde la pestaña de exportación.</p>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="hs-divider"></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Cuadro de mando — Sesión actual</p>', unsafe_allow_html=True)
    if st.session_state.historial_disenos:
        df_hist = pd.DataFrame(st.session_state.historial_disenos)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        if st.button("Limpiar Historial", key="btn_limpiar_home"):
            st.session_state.historial_disenos = []
            st.rerun()
    else:
        st.markdown("""<div style="background:#161b22;border:1px dashed #30363d;border-radius:8px;padding:24px 20px;text-align:center;color:#8b949e;font-family:'Satoshi',sans-serif;font-size:.85rem">
        No hay diseños en esta sesión. Navega a cualquier módulo para comenzar.
        </div>""", unsafe_allow_html=True)

    year = _dt.datetime.now().year
    st.markdown(f"""
<div class="hs-divider"></div>
<div class="footer">
  <div class="footer-logo">
    <div style="font-size:.85rem;font-weight:700;color:#e6edf3">StructoPro</div>
    <div style="font-size:.72rem;color:#8b949e;margin-top:2px">{year} — Todos los derechos reservados</div>
  </div>
  <div style="font-size:.72rem;color:#8b949e;max-width:440px;line-height:1.6">Herramienta de apoyo profesional al diseño estructural. Los resultados son responsabilidad exclusiva del ingeniero diseñador.</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PÁGINAS
# ─────────────────────────────────────────────
home    = st.Page(run_home, title="Inicio", icon=":material/home:", default=True)

# Hormigón
p_col   = st.Page("pages/01_Columnas_PM.py",          title="Columnas PM",           icon=":material/domain:")
p_ccirc = st.Page("pages/07_Columnas_Circulares.py",  title="Columnas Circulares",   icon=":material/lens:")
p_vig   = st.Page("pages/02_Vigas_Losas.py",          title="Vigas y Losas",         icon=":material/horizontal_rule:")
p_otras = st.Page("pages/03_Otras_Estructuras.py",    title="Otras Estructuras",     icon=":material/extension:")
p_pred  = st.Page("pages/04_Predimensionamiento.py",  title="Predimensionamiento",   icon=":material/straighten:")

# Cimentaciones
p_zap   = st.Page("pages/09_Zapatas.py",              title="Zapatas",               icon=":material/layers:")
p_pil   = st.Page("pages/10_Pilotes.py",              title="Pilotes",               icon=":material/format_align_center:")
p_dad   = st.Page("pages/11_Dados_Encepados.py",      title="Dados y Cabezales",     icon=":material/view_module:")
p_mcont = st.Page("pages/12_Muros_Contencion.py",     title="Muros Contención",      icon=":material/view_stream:")

# Sismo & Viento
p_sismo  = st.Page("pages/15_Diseño_Sismico.py",     title="Diseño Sísmico",        icon=":material/public:")
p_viento = st.Page("pages/16_viento simplificado.py",title="Viento Simplificado",   icon=":material/air:")
p_irreg  = st.Page("pages/17_Irregularidades.py",    title="Irregularidades",        icon=":material/architecture:")

# Mampostería & Alt
p_mamp_e = st.Page("pages/24_Mamposteria_Estructural.py", title="Mampostería Estructural", icon=":material/grid_on:")
p_mamp_m = st.Page("pages/13_Mamposteria_Morteros.py",    title="Mampostería Morteros",    icon=":material/apps:")
p_placa  = st.Page("pages/08_Placa facil.py",             title="Placa fácil",             icon=":material/view_module:")
p_konte  = st.Page("pages/11_Kontewall.py",               title="Kontewall",               icon=":material/view_compact:")
p_mad    = st.Page("pages/14_Madera_Estructuras.py",      title="Madera Estructuras",      icon=":material/forest:")
p_metal  = st.Page("pages/18_Estructuras_Metalicas.py",   title="Estructuras Metálicas",   icon=":material/build:")

# Presupuesto
p_calc  = st.Page("pages/06_Calculadora_de_Materiales.py", title="Calculadora Materiales", icon=":material/calculate:")
p_apu   = st.Page("pages/05_APU_Mercado.py",               title="APU Mercado",            icon=":material/payments:")

# Análisis
p_a2d   = st.Page("pages/21_Analisis_Estructural_2D.py", title="Análisis 2D",         icon=":material/polyline:")
p_a3d   = st.Page("pages/22_Analisis_Estructural_3D.py", title="Análisis 3D",         icon=":material/view_in_ar:")
p_gen3d = st.Page("pages/23_Generador_Maestro_3D.py",    title="Generador 3D",         icon=":material/polyline:")
p_res   = st.Page("pages/19_Resistencia_Materiales.py",  title="Resistencia Materiales",icon=":material/science:")
p_util  = st.Page("pages/20_Utilidades_Comunes.py",      title="Utilidades Comunes",    icon=":material/widgets:")

all_pages = [
    home,
    p_col, p_ccirc, p_vig, p_otras, p_pred,
    p_zap, p_pil, p_dad, p_mcont,
    p_sismo, p_viento, p_irreg,
    p_mamp_e, p_mamp_m, p_placa, p_konte, p_mad, p_metal,
    p_calc, p_apu,
    p_a2d, p_a3d, p_gen3d, p_res, p_util,
]

curr_page = st.navigation(all_pages, position="hidden")


# --- AUTENTICACIÓN ---
if not st.session_state.auth_user:
    login_view()
    st.stop()

# ─────────────────────────────────────────────
# SIDEBAR — USUARIO Y NORMA
# ─────────────────────────────────────────────
with st.sidebar:
    # Cabecera usuario
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;padding:12px 0 8px;border-bottom:1px solid #21262d;margin-bottom:12px">
        <div style="width:32px;height:32px;border-radius:50%;background:#21262d;display:flex;align-items:center;justify-content:center;font-size:14px"><span style="font-size:11px;color:#aaa">USR</span></div>
        <div style="flex:1;min-width:0">
            <div style="font-size:12px;color:#8b949e">Sesión activa</div>
            <div style="font-size:12px;font-weight:600;color:#e6edf3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{st.session_state.auth_user.email}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    logout_button()

    # ── NORMA ACTIVA ──────────────────────────────────────────────
    NORMAS_DISPONIBLES = [
        "NSR-10 (Colombia)", "ACI 318-25 (EE.UU.)", "ACI 318-19 (EE.UU.)",
        "ACI 318-14 (EE.UU.)", "NEC-SE-HM (Ecuador)", "E.060 (Perú)",
        "NTC-EM (México)", "COVENIN 1753-2006 (Venezuela)",
        "NB 1225001-2020 (Bolivia)", "CIRSOC 201-2025 (Argentina)",
    ]
    if "norma_sel" not in st.session_state or st.session_state.norma_sel not in NORMAS_DISPONIBLES:
        st.session_state.norma_sel = NORMAS_DISPONIBLES[0]

    with st.expander("Norma y Sismo", expanded=True):
        _NORMA_FLAG_URL = {
            "NSR-10 (Colombia)":             "https://flagpedia.net/data/flags/mini/co.png",
            "ACI 318-25 (EE.UU.)":           "https://flagpedia.net/data/flags/mini/us.png",
            "ACI 318-19 (EE.UU.)":           "https://flagpedia.net/data/flags/mini/us.png",
            "ACI 318-14 (EE.UU.)":           "https://flagpedia.net/data/flags/mini/us.png",
            "NEC-SE-HM (Ecuador)":           "https://flagpedia.net/data/flags/mini/ec.png",
            "E.060 (Perú)":                  "https://flagpedia.net/data/flags/mini/pe.png",
            "NTC-EM (México)":               "https://flagpedia.net/data/flags/mini/mx.png",
            "COVENIN 1753-2006 (Venezuela)": "https://flagpedia.net/data/flags/mini/ve.png",
            "NB 1225001-2020 (Bolivia)":     "https://flagpedia.net/data/flags/mini/bo.png",
            "CIRSOC 201-2025 (Argentina)":   "https://flagpedia.net/data/flags/mini/ar.png",
        }
        st.selectbox(
            "Normativa:",
            options=NORMAS_DISPONIBLES,
            index=NORMAS_DISPONIBLES.index(st.session_state.get("norma_sel", NORMAS_DISPONIBLES[0])),
            key="norma_sel"
        )
        flag_url = _NORMA_FLAG_URL.get(st.session_state.norma_sel, "https://flagpedia.net/data/flags/mini/un.png")
        st.session_state.norma_flag_url = flag_url
        st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;padding:6px 0">
            <img src="{flag_url}" style="height:18px;border-radius:2px;"> 
            <span style="font-size:12px;color:#3fb950;font-weight:600">{st.session_state.norma_sel}</span>
        </div>""", unsafe_allow_html=True)
        if "idioma" not in st.session_state:
            st.session_state.idioma = "Español"
        if "ACI 318" in st.session_state.norma_sel:
            st.session_state.idioma = st.radio("Idioma:", ["Español", "English"], horizontal=True,
                index=0 if st.session_state.idioma == "Español" else 1)
        else:
            st.session_state.idioma = "Español"

    # ── NAVEGACIÓN CATEGORIZADA ───────────────────────────────────
    st.markdown('<div class="nav-category">Modulos de Diseno</div>', unsafe_allow_html=True)

    with st.expander("Hormigon — Secciones", expanded=False):
        st.markdown("Columnas y vigas de sección")
        menu_container_rc = st.container()

    with st.expander("Cimentaciones", expanded=False):
        menu_container_found = st.container()

    with st.expander("Sismo & Viento", expanded=False):
        menu_container_seismic = st.container()

    with st.expander("Mamposteria & Alternativos", expanded=False):
        menu_container_mamp = st.container()

    with st.expander("Presupuesto & Materiales", expanded=False):
        menu_container_budget = st.container()

    with st.expander("Analisis & Utilidades", expanded=False):
        menu_container_analysis = st.container()

    # ── PROYECTO ──────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("Proyecto y Guardado", expanded=False):
        project_name    = st.text_input("Nombre del Proyecto:", value=st.session_state.get("project_name",  "Mi_Edificio"), key="project_name")
        project_owner   = st.text_input("Propietario:",         value=st.session_state.get("project_owner", ""),           key="project_owner")
        project_address = st.text_input("Dirección:",           value=st.session_state.get("project_address",""),          key="project_address")
        project_phone   = st.text_input("Teléfono:",            value=st.session_state.get("project_phone",  ""),          key="project_phone")

        def serialize_state_dict():
            state_dict = {}
            for k, v in st.session_state.items():
                if k == "auth_user": continue
                if isinstance(v, pd.DataFrame):
                    state_dict[k] = {"__type__": "dataframe", "data": v.to_dict(orient="records")}
                elif isinstance(v, (int, float, str, bool, list, dict)):
                    state_dict[k] = v
            return state_dict

        if project_name and project_owner and project_address and project_phone:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(" Nube", use_container_width=True):
                    try:
                        save_project_to_db(st.session_state.auth_user, project_name, project_owner,
                                           project_address, project_phone, serialize_state_dict())
                        st.success("¡Guardado en nube!")
                    except Exception as e:
                        st.error(f"Error: {e}")
            with col2:
                st.download_button(label="Guardar local",
                    data=json.dumps(serialize_state_dict(), indent=4),
                    file_name=f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json", use_container_width=True)
        else:
            st.caption("Completa los datos para habilitar el guardado.")

        # Cargar desde nube
        st.markdown("**Cargar proyecto:**")
        if st.button("↻ Ver proyectos en nube", use_container_width=True):
            try:
                if st.session_state.get("auth_user"):
                    proyectos_cloud = get_projects_from_db(st.session_state.auth_user)
                    if proyectos_cloud:
                        for p in proyectos_cloud:
                            col_p1, col_p2 = st.columns([3, 1])
                            col_p1.markdown(f"**{p['nombre_proyecto']}**  \n{p['created_at'][:10]}")
                            if col_p2.button("", key=f"load_{p['id']}"):
                                project_data = p.get('estado_json', {})
                                if isinstance(project_data, str):
                                    project_data = json.loads(project_data)
                                for k, v in project_data.items():
                                    st.session_state[k] = pd.DataFrame(v["data"]) if isinstance(v, dict) and v.get("__type__") == "dataframe" else v
                                st.success(f" {p['nombre_proyecto']} cargado.")
                    else:
                        st.info("Sin proyectos en nube.")
            except Exception as e:
                st.error(f"Error nube: {e}")

        uploaded_project = st.file_uploader("Cargar JSON local:", type=['json'])
        if uploaded_project is not None:
            try:
                project_data = json.load(uploaded_project)
                for k, v in project_data.items():
                    st.session_state[k] = pd.DataFrame(v["data"]) if isinstance(v, dict) and v.get("__type__") == "dataframe" else v
                st.success("Archivo cargado ")
            except Exception as e:
                st.error(f"Error: {e}")

    # ── PIE SIDEBAR ──────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;color:#484f58;font-size:10px;padding:12px 0 4px">
        StructoPro v2.0 &nbsp;·&nbsp; © 2026<br>
        <i>Herramienta de apoyo profesional</i>
    </div>""", unsafe_allow_html=True)

# Inicializar APU global
if "apu_config" not in st.session_state:
    st.session_state.apu_config = {
        "moneda": "COP$", "cemento": 32000.0, "acero": 4500.0,
        "arena": 70000.0, "grava": 80000.0, "costo_dia_mo": 69333.33,
        "pct_herramienta": 0.05, "pct_aui": 0.30, "iva": 0.19, "pct_util": 0.05
    }

# ─────────────────────────────────────────────
# PÁGINAS Y NAVEGACIÓN CATEGORIZADA
# ─────────────────────────────────────────────
# ── MENÚS CATEGORIZADOS (se inyectan en los contenedores del sidebar) ──
def _nav_btn(page, container, curr_page):
    """Botón de navegación que hace switch_page."""
    is_active = page.url_path == curr_page.url_path
    with container:
        label = ("▶ " if is_active else "   ") + page.title
        if st.button(label, key=f"nav_{page.url_path}", use_container_width=True):
            st.switch_page(page)

with menu_container_rc:
    for p in [p_col, p_ccirc, p_vig, p_otras, p_pred]:
        _nav_btn(p, menu_container_rc, curr_page)

with menu_container_found:
    for p in [p_zap, p_pil, p_dad, p_mcont]:
        _nav_btn(p, menu_container_found, curr_page)

with menu_container_seismic:
    for p in [p_sismo, p_viento, p_irreg]:
        _nav_btn(p, menu_container_seismic, curr_page)

with menu_container_mamp:
    for p in [p_mamp_e, p_mamp_m, p_placa, p_konte, p_mad, p_metal]:
        _nav_btn(p, menu_container_mamp, curr_page)

with menu_container_budget:
    for p in [p_calc, p_apu]:
        _nav_btn(p, menu_container_budget, curr_page)

with menu_container_analysis:
    for p in [p_a2d, p_a3d, p_gen3d, p_res, p_util]:
        _nav_btn(p, menu_container_analysis, curr_page)


curr_page.run()
