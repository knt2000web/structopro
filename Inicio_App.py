import streamlit as st
import json
import pandas as pd
import datetime

from auth import sign_up_user, sign_in_user, sign_out_user, get_current_user, save_project_to_db, get_projects_from_db, DummyUser
from streamlit_cookies_controller import CookieController
from utils.icons import GLOBAL_CSS

st.set_page_config(
    page_title="Reinforced Concrete Suite",
    page_icon="",
    layout="wide",
)

# Inyectar CSS global de íconos SVG una sola vez
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

try:
    cookie_controller = CookieController()
except Exception:
    cookie_controller = None

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

# Recuperar sesión desde cookies
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
                    sleep(0.5) # Pequeña espera para que las cookies se fijen antes del rerun
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
                        st.success("Cuenta creada correctamente. Revisa tu correo para confirmar el registro si Supabase lo solicita.")
                    else:
                        st.error("No se pudo crear la cuenta")
                except Exception as e:
                    st.error(f"Error de registro: {e}")

def logout_button():
    if st.sidebar.button("Cerrar sesión"):
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

if not st.session_state.auth_user:
    login_view()
    st.stop()

st.sidebar.success(f"Sesión iniciada: {st.session_state.auth_user.email}")
logout_button()

# st.sidebar debe iniciar con el selector de modulos para que esté lo mas arriba posible
st.sidebar.markdown("###  Navegador de Módulos")
# Se instancia al final, pero reservamos el contenedor arriba
menu_container = st.sidebar.container()

st.sidebar.info(" Servidor ejecutándose desde: C:\\Users\\cagch\\Desktop\\Diagrama_NSR10")

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
.norms-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:8px;margin-bottom:48px}
.norm-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px 14px;display:flex;align-items:center;gap:12px;font-family:'Satoshi',sans-serif}
.norm-name{font-size:.8rem;font-weight:700;color:var(--text)}
.norm-country{font-size:.7rem;color:var(--muted);margin-top:1px}
.exports-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:48px}
.export-chip{display:inline-flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 16px;font-size:.82rem;color:var(--text);font-weight:500;font-family:'Satoshi',sans-serif}
.step-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px;font-family:'Satoshi',sans-serif;height:100%}
.step-num{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:white;margin-bottom:12px}
.step-title{font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:8px}
.step-desc{font-size:.8rem;color:var(--muted);line-height:1.65}
.hs-divider{height:1px;background:var(--border);margin:40px 0}
.footer{border-top:1px solid var(--border);padding:28px 0 8px;display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:16px;font-family:'Satoshi',sans-serif}
.footer-logo{display:flex;align-items:center;gap:10px}
.footer-name{font-size:.85rem;font-weight:700;color:var(--text)}
.footer-copy{font-size:.72rem;color:var(--muted);margin-top:2px}
.footer-note{font-size:.72rem;color:var(--muted);max-width:440px;line-height:1.6}
/* Ocultar toolbar de Streamlit en modo limpio */
header[data-testid="stHeader"]{background:transparent}
</style>
""", unsafe_allow_html=True)

    # ── HERO ──────────────────────────────────────────────────────────────────
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
    <span class="pill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>Cálculo en tiempo real</span>
    <span class="pill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>Exportación IFC / BIM</span>
    <span class="pill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>Memorias DOCX / DXF</span>
    <span class="pill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>10 normativas</span>
    <span class="pill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>Supabase Cloud</span>
    <span class="pill"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6M9 12h6M9 15h4"/></svg>Código LaTeX normativo</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── STATS ─────────────────────────────────────────────────────────────────
    st.markdown("""
<div class="stats-row">
  <div class="stat-cell"><div class="stat-num">10<span>+</span></div><div class="stat-label">Normativas soportadas</div></div>
  <div class="stat-cell"><div class="stat-num">18<span>+</span></div><div class="stat-label">Módulos de cálculo</div></div>
  <div class="stat-cell"><div class="stat-num">6<span>+</span></div><div class="stat-label">Formatos de exportación</div></div>
  <div class="stat-cell"><div class="stat-num">3D<span> / 2D</span></div><div class="stat-label">Visualización interactiva</div></div>
</div>
""", unsafe_allow_html=True)

    # ── MÓDULOS ───────────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">Módulos de cálculo disponibles</p>', unsafe_allow_html=True)
    st.markdown("""
<div class="modules-grid">
  <div class="module-card" style="--card-accent:#3fb950">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="1.8"><rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="18" rx="1"/></svg></div>
      <div><div class="card-title">Columnas — Diagrama P-M Biaxial</div><div class="card-sub">Módulo › Columnas_PM</div></div>
    </div>
    <p class="card-desc">Genera diagramas de interacción P-M en 3D (Superficie de Bresler) para secciones cuadradas, rectangulares y circulares. Verificación de esbeltez NSR-10 C.10.10, diseño de estribos y espiral sísmicos, magnificación de momentos, verificación φPn,máx y exportación IFC-BIM.</p>
    <div class="tag-row"><span class="tag g">Bresler 3D</span><span class="tag b">Esbeltez kL/r</span><span class="tag b">Estribos sísmicos</span><span class="tag o">IFC / DXF / DOCX</span><span class="tag p">Circular / Rectangular</span></div>
  </div>
  <div class="module-card" style="--card-accent:#79c0ff">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#79c0ff" stroke-width="1.8"><rect x="2" y="9" width="20" height="6" rx="1"/><line x1="2" y1="12" x2="22" y2="12" stroke-dasharray="3 2"/></svg></div>
      <div><div class="card-title">Vigas y Losas — Diseño Completo</div><div class="card-sub">Módulo › Vigas_Losas</div></div>
    </div>
    <p class="card-desc">Diseño a flexión (sección rectangular y Viga T), cortante sísmico Vp = (Mpr,i + Mpr,d)/Ln + WuLn/2 (DMO/DES), deflexiones Branson, losa en una dirección, punzonamiento bidireccional NSR-10 C.11.11, longitudes de desarrollo y empalme. Wu automático NSR-10 C.8.3.3.</p>
    <div class="tag-row"><span class="tag b">Viga Rectangular / T</span><span class="tag r">Cortante Vp sísmico</span><span class="tag b">Deflexión Branson</span><span class="tag o">Punzonamiento bo</span><span class="tag g">ld / Empalmes</span></div>
  </div>
  <div class="module-card" style="--card-accent:#ffa657">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffa657" stroke-width="1.8"><polygon points="12 2 22 20 2 20"/><line x1="12" y1="9" x2="12" y2="15"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
      <div><div class="card-title">Otras Estructuras</div><div class="card-sub">Ménsulas · Axial · Cortante dist. x · Losa 2D</div></div>
    </div>
    <p class="card-desc">Ménsulas cortas (a/d &lt; 1.0) con acero de fricción, verificación de capacidad axial corta en columnas, cortante a distancia x en vigas, tabla de secciones de refuerzo US y SI, y diseño de losa bidireccional 2D.</p>
    <div class="tag-row"><span class="tag o">Ménsulas cortas</span><span class="tag b">Cortante a dist. x</span><span class="tag g">Tabla barras US/SI</span><span class="tag p">Losa 2D</span></div>
  </div>
  <div class="module-card" style="--card-accent:#d2a8ff">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d2a8ff" stroke-width="1.8"><rect x="2" y="15" width="20" height="6" rx="1"/><line x1="7" y1="15" x2="7" y2="4"/><line x1="12" y1="15" x2="12" y2="4"/><line x1="17" y1="15" x2="17" y2="4"/><line x1="4" y1="4" x2="20" y2="4"/></svg></div>
      <div><div class="card-title">Cimentaciones y Muros</div><div class="card-sub">Zapatas aisladas · Muros de contención</div></div>
    </div>
    <p class="card-desc">Diseño de zapatas aisladas con presiones de contacto, cortante unidireccional y punzonamiento. Muros en voladizo: estabilidad al deslizamiento, volcamiento y presiones netas. Exportación DXF con rótulo ICONTEC y presupuesto APU integrado.</p>
    <div class="tag-row"><span class="tag p">Zapatas aisladas</span><span class="tag p">Muros contención</span><span class="tag g">Estabilidad vuelco</span><span class="tag o">DXF ICONTEC</span></div>
  </div>
  <div class="module-card" style="--card-accent:#d29922">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d29922" stroke-width="1.8"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg></div>
      <div><div class="card-title">Presupuesto APU Mercado</div><div class="card-sub">Análisis de Precios Unitarios en vivo</div></div>
    </div>
    <p class="card-desc">Cotización de materiales (cemento, acero, áridos) con precios configurables por norma. Calcula costo directo, A.I.U., utilidad e IVA para cada elemento. Compatible con COP, USD y cualquier moneda. Exporta presupuesto en Excel con desglose por actividad.</p>
    <div class="tag-row"><span class="tag o">Precios configurables</span><span class="tag o">A.I.U. + IVA</span><span class="tag g">Excel .xlsx</span><span class="tag b">Multi-moneda</span></div>
  </div>
  <div class="module-card" style="--card-accent:#da3633">
    <div class="card-header">
      <div class="card-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#da3633" stroke-width="1.8"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></div>
      <div><div class="card-title">Diseño Sísmico Integral — Viga</div><div class="card-sub">Flujo guiado DMO / DES · NSR-10 C.21</div></div>
    </div>
    <p class="card-desc">Flujo completo para vigas en zonas sísmicas DMO y DES. Envolvente de momentos negativos/positivos, cortante de capacidad Vp, armado en nudos izquierdo/derecho/centro, zona de confinamiento Lo y plano DXF automatizado con detallado de estribos a escala.</p>
    <div class="tag-row"><span class="tag r">NSR-10 C.21</span><span class="tag r">Envolvente Vp</span><span class="tag b">Plano DXF auto</span><span class="tag g">Confinamiento Lo</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── NORMATIVAS ────────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">Normativas soportadas</p>', unsafe_allow_html=True)
    st.markdown("""
<div class="norms-grid">
  <div class="norm-card"><svg width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="20" rx="2" fill="#FCD116"/><rect y="10" width="28" height="5" fill="#003893"/><rect y="15" width="28" height="5" fill="#CE1126"/></svg><div><div class="norm-name">NSR-10</div><div class="norm-country">Colombia — Título C</div></div></div>
  <div class="norm-card"><svg width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="20" rx="2" fill="#B22234"/><rect y="2.5" width="28" height="2.2" fill="white"/><rect y="7.5" width="28" height="2.2" fill="white"/><rect y="12.5" width="28" height="2.2" fill="white"/><rect y="17.5" width="28" height="2.2" fill="white"/><rect width="12" height="10" fill="#3C3B6E"/></svg><div><div class="norm-name">ACI 318-25 / 19 / 14</div><div class="norm-country">Estados Unidos</div></div></div>
  <div class="norm-card"><svg width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="20" rx="2" fill="#FFD100"/><rect y="10" width="28" height="5" fill="#003893"/><rect y="15" width="28" height="5" fill="#CE1126"/></svg><div><div class="norm-name">NEC-SE-HM</div><div class="norm-country">Ecuador</div></div></div>
  <div class="norm-card"><svg width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="20" rx="2" fill="#D91023"/><rect width="9.3" height="20" fill="#D91023"/><rect x="9.3" width="9.4" height="20" fill="white"/><rect x="18.7" width="9.3" height="20" fill="#D91023"/></svg><div><div class="norm-name">E.060</div><div class="norm-country">Perú</div></div></div>
  <div class="norm-card"><svg width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="20" rx="2" fill="#006847"/><rect width="9.3" height="20" fill="#006847"/><rect x="9.3" width="9.4" height="20" fill="white"/><rect x="18.7" width="9.3" height="20" fill="#CE1126"/></svg><div><div class="norm-name">NTC-EM</div><div class="norm-country">México — RCDF 2017</div></div></div>
  <div class="norm-card"><svg width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="20" rx="2" fill="#CF142B"/><rect y="0" width="28" height="6.7" fill="#FFD200"/><rect y="6.7" width="28" height="6.7" fill="#00247D"/></svg><div><div class="norm-name">COVENIN 1753</div><div class="norm-country">Venezuela — 2006</div></div></div>
  <div class="norm-card"><svg width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="20" rx="2" fill="#D52B1E"/><rect y="6.6" width="28" height="6.8" fill="#FFD100"/><rect y="13.4" width="28" height="6.6" fill="#007A3D"/></svg><div><div class="norm-name">NB 1225001</div><div class="norm-country">Bolivia — 2020</div></div></div>
  <div class="norm-card"><svg width="28" height="20" viewBox="0 0 28 20" xmlns="http://www.w3.org/2000/svg"><rect width="28" height="20" rx="2" fill="#74ACDF"/><rect y="6.5" width="28" height="7" fill="white"/></svg><div><div class="norm-name">CIRSOC 201</div><div class="norm-country">Argentina — 2025</div></div></div>
</div>
""", unsafe_allow_html=True)

    # ── EXPORTACIONES ─────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">Formatos de exportación</p>', unsafe_allow_html=True)
    st.markdown("""
<div class="exports-row">
  <div class="export-chip"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>Memoria técnica DOCX</div>
  <div class="export-chip"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>Planos DXF — AutoCAD</div>
  <div class="export-chip"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="1.8"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" y1="22" x2="12" y2="12"/></svg>IFC 2x3 — BIM</div>
  <div class="export-chip"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/></svg>Presupuesto Excel .xlsx</div>
  <div class="export-chip"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>Secciones y diagramas PNG</div>
  <div class="export-chip"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>Proyectos en nube — Supabase</div>
</div>
""", unsafe_allow_html=True)

    # ── CÓMO COMENZAR ─────────────────────────────────────────────────────────
    st.markdown('<div class="hs-divider"></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Cómo comenzar</p>', unsafe_allow_html=True)
    c1s, c2s, c3s = st.columns(3)
    with c1s:
        st.markdown("""<div class="step-card"><div class="step-num"style="background:#2ea043">1</div><div class="step-title">Configurar norma global</div><p class="step-desc">En la barra lateral selecciona la normativa y el nivel sísmico. Todos los módulos leen esta configuración automáticamente — fc, fy, factores φ y referencias normativas se actualizan al instante.</p></div>""", unsafe_allow_html=True)
    with c2s:
        st.markdown("""<div class="step-card"><div class="step-num"style="background:#1f6feb">2</div><div class="step-title">Seleccionar módulo</div><p class="step-desc">Usa el menú desplegable en la parte superior de la barra lateral. Cada módulo tiene su propio flujo de ingreso de datos, pestañas de resultados, sección 2D/3D y generación de memoria técnica.</p></div>""", unsafe_allow_html=True)
    with c3s:
        st.markdown("""<div class="step-card"><div class="step-num"style="background:#d29922">3</div><div class="step-title">Guardar y exportar</div><p class="step-desc">Guarda el proyecto en Supabase Cloud con nombre personalizado. Genera la memoria DOCX, plano DXF o modelo IFC-BIM desde la pestaña de exportación de cada módulo. Los datos persisten entre sesiones.</p></div>""", unsafe_allow_html=True)

    # ── CUADRO DE MANDO (historial sesión) ────────────────────────────────────
    st.markdown('<div class="hs-divider"></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-title">Cuadro de mando — Sesión actual</p>', unsafe_allow_html=True)
    if st.session_state.historial_disenos:
        df_hist = pd.DataFrame(st.session_state.historial_disenos)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        if st.button("Limpiar Historial", key="btn_limpiar_home"):
            st.session_state.historial_disenos = []
            st.rerun()
    else:
        st.markdown("""<div style="background:#161b22;border:1px dashed #30363d;border-radius:8px;padding:24px 20px;text-align:center;color:#8b949e;font-family:'Satoshi',sans-serif;font-size:.85rem">No hay diseños en esta sesión. Navega a cualquier módulo, completa un diseño y aparecerá aquí automáticamente.</div>""", unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    year = _dt.datetime.now().year
    st.markdown(f"""
<div class="hs-divider"></div>
<div class="footer">
  <div class="footer-logo">
    <svg width="34" height="34" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="34" height="34" rx="7" fill="#161b22"/>
      <rect x="0.5" y="0.5" width="33" height="33" rx="6.5" stroke="#30363d"/>
      <rect x="8" y="8" width="5" height="18" rx="1" fill="#2ea043"/>
      <rect x="21" y="8" width="5" height="18" rx="1" fill="#2ea043"/>
      <rect x="13" y="15" width="8" height="2.5" rx="0.5" fill="#3fb950"/>
    </svg>
    <div><div class="footer-name">Reinforced Concrete Suite</div><div class="footer-copy">{year} — Todos los derechos reservados</div></div>
  </div>
  <div class="footer-note">Herramienta de apoyo profesional al diseño estructural. Los resultados son responsabilidad exclusiva del ingeniero diseñador. Verifique siempre con la norma vigente en su jurisdicción.</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ESTADO GLOBAL (SESIÓN)
# ─────────────────────────────────────────────
st.sidebar.header(" Configuración Global del Proyecto")

# IMPORTANTE: Las llaves deben coincidir EXACTAMENTE con los diccionarios CODES de cada página
# No incluir emojis de banderas en las llaves — se muestran solo en la UI
NORMAS_DISPONIBLES = [
    "NSR-10 (Colombia)",
    "ACI 318-25 (EE.UU.)",
    "ACI 318-19 (EE.UU.)",
    "ACI 318-14 (EE.UU.)",
    "NEC-SE-HM (Ecuador)",
    "E.060 (Perú)",
    "NTC-EM (México)",
    "COVENIN 1753-2006 (Venezuela)",
    "NB 1225001-2020 (Bolivia)",
    "CIRSOC 201-2025 (Argentina)",
]

# Mapa visual limpio para el selectbox
NORMA_DISPLAY = {
    "NSR-10 (Colombia)":           "NSR-10 (Colombia)",
    "ACI 318-25 (EE.UU.)":         "ACI 318-25 (EE.UU.)",
    "ACI 318-19 (EE.UU.)":         "ACI 318-19 (EE.UU.)",
    "ACI 318-14 (EE.UU.)":         "ACI 318-14 (EE.UU.)",
    "NEC-SE-HM (Ecuador)":         "NEC-SE-HM (Ecuador)",
    "E.060 (Perú)":                "E.060 (Perú)",
    "NTC-EM (México)":             "NTC-EM (México)",
    "COVENIN 1753-2006 (Venezuela)": "COVENIN 1753-2006 (Venezuela)",
    "NB 1225001-2020 (Bolivia)":   "NB 1225001-2020 (Bolivia)",
    "CIRSOC 201-2025 (Argentina)": "CIRSOC 201-2025 (Argentina)",
}

if "norma_sel" not in st.session_state or st.session_state.norma_sel not in NORMAS_DISPONIBLES:
    st.session_state.norma_sel = NORMAS_DISPONIBLES[0]

# Mostrar limpio en UI
_norm_displayed = st.sidebar.selectbox(
    "Selecciona la Normativa de Diseño:",
    options=NORMAS_DISPONIBLES,
    format_func=lambda k: NORMA_DISPLAY.get(k, k),
    index=NORMAS_DISPONIBLES.index(st.session_state.get("norma_sel", NORMAS_DISPONIBLES[0])),
    key="norma_sel"
)

# Guardar la bandera (Imagen HD) en session_state para que la usen todas las páginas
_NORMA_FLAG_URL = {
    "NSR-10 (Colombia)":           "https://flagpedia.net/data/flags/mini/co.png",
    "ACI 318-25 (EE.UU.)":         "https://flagpedia.net/data/flags/mini/us.png",
    "ACI 318-19 (EE.UU.)":         "https://flagpedia.net/data/flags/mini/us.png",
    "ACI 318-14 (EE.UU.)":         "https://flagpedia.net/data/flags/mini/us.png",
    "NEC-SE-HM (Ecuador)":         "https://flagpedia.net/data/flags/mini/ec.png",
    "E.060 (Perú)":                "https://flagpedia.net/data/flags/mini/pe.png",
    "NTC-EM (México)":             "https://flagpedia.net/data/flags/mini/mx.png",
    "COVENIN 1753-2006 (Venezuela)": "https://flagpedia.net/data/flags/mini/ve.png",
    "NB 1225001-2020 (Bolivia)":   "https://flagpedia.net/data/flags/mini/bo.png",
    "CIRSOC 201-2025 (Argentina)": "https://flagpedia.net/data/flags/mini/ar.png",
}

st.session_state.norma_flag_url = _NORMA_FLAG_URL.get(st.session_state.norma_sel, "https://flagpedia.net/data/flags/mini/un.png")

# Mostrar cuadro de exito con imagen HTML
html_flag = f"""
<div style="display: flex; align-items: center; background-color: #1e1e1e; padding: 10px; border-radius: 5px; border-left: 5px solid #4CAF50;">
    <img src="{st.session_state.norma_flag_url}" style="height:32px;width:auto;margin-right:15px;vertical-align:middle;border-radius:3px;">
    <div>
        <span style="font-size: 12px; color: gray;">Norma Activa:</span><br>
        <strong style="color: white; font-size: 16px;">{st.session_state.norma_sel}</strong>
    </div>
</div>
<br>
"""
st.sidebar.markdown(html_flag, unsafe_allow_html=True)

if "idioma" not in st.session_state:
    st.session_state.idioma = "Español"

if "ACI 318" in st.session_state.norma_sel:
    st.session_state.idioma = st.sidebar.radio(
        " Idioma / Language:",
        ["Español", "English"],
        index=0 if st.session_state.idioma == "Español" else 1,
        horizontal=True
    )
else:
    st.session_state.idioma = "Español" # Forzar español para otras normas si no es ACI

# -----------------------------------------------------------------------------
# GESTOR GLOBAL DE PROYECTOS (NUBE / LOCAL)
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("☁ Menú Mis Proyectos")

with st.sidebar.expander(" Cargar de la Nube", expanded=False):
    st.write("Selecciona tus cálculos previos:")
    if st.button("↻ Refrescar Lista", use_container_width=True):
        st.rerun()
        
    try:
        if st.session_state.get("auth_user"):
            proyectos_cloud = get_projects_from_db(st.session_state.auth_user)
            if proyectos_cloud:
                for p in proyectos_cloud:
                    with st.container():
                        st.markdown(f"**{p['nombre_proyecto']}**")
                        st.caption(f"{p['created_at'][:10]} | Resp: {p.get('propietario', '')}")
                        if st.button("Cargar ⬇", key=f"load_{p['id']}", use_container_width=True):
                            project_data = p.get('estado_json', {})
                            if isinstance(project_data, str):
                                project_data = json.loads(project_data)
                            for k, v in project_data.items():
                                if isinstance(v, dict) and v.get("__type__") == "dataframe":
                                    st.session_state[k] = pd.DataFrame(v["data"])
                                else:
                                    st.session_state[k] = v
                            st.success(f"¡{p['nombre_proyecto']} Cargado Exitósamente!")
                    st.divider()
            else:
                st.info("No tienes proyectos en la nube.")
    except Exception as e:
        err_str = str(e)
        if "404" in err_str and "proyectos" in err_str:
            st.error("La tabla 'proyectos'no existe en tu base de datos de Supabase.")
            with st.expander(" ¿Cómo solucionar este error?"):
                st.markdown("Ve a tu panel de **Supabase**, entra a **SQL Editor**, copia y ejecuta este código para crear la tabla necesaria:")
                st.code('''CREATE TABLE proyectos (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references auth.users not null,
  nombre_proyecto text not null,
  propietario text,
  direccion text,
  telefono text,
  estado_json jsonb,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Configura RLS (Row Level Security) para que cada usuario vea sólo lo suyo
alter table proyectos enable row level security;

create policy "Usuarios ven sus propios proyectos"
on proyectos for select
using ( auth.uid() = user_id );

create policy "Usuarios insertan sus proyectos"
on proyectos for insert
with check ( auth.uid() = user_id );

create policy "Usuarios actualizan sus proyectos"
on proyectos for update
using ( auth.uid() = user_id );''', language='sql')
        else:
            st.error(f"Error nube: {e}")

st.sidebar.subheader(" Guardar Estado Actual")

project_name = st.sidebar.text_input("Nombre del Proyecto:", value=st.session_state.get("project_name", "Mi_Edificio"), key="project_name")
project_owner = st.sidebar.text_input("Propietario / Cliente:", value=st.session_state.get("project_owner", ""), key="project_owner")
project_address = st.sidebar.text_input("Dirección de Obra:", value=st.session_state.get("project_address", ""), key="project_address")
project_phone = st.sidebar.text_input("Teléfono de Contacto:", value=st.session_state.get("project_phone", ""), key="project_phone")

def serialize_state_dict():
    state_dict = {}
    for k, v in st.session_state.items():
        if k in ["auth_user"]: # Omitir el usuario autenticado para no sobreescribir tokens
            continue
        if isinstance(v, pd.DataFrame):
            state_dict[k] = {"__type__": "dataframe", "data": v.to_dict(orient="records")}
        elif isinstance(v, (int, float, str, bool, list, dict)):
            state_dict[k] = v
    return state_dict

if project_name and project_owner and project_address and project_phone:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("☁ Nube", help="Guardar en Supabase", use_container_width=True):
            try:
                save_project_to_db(
                    st.session_state.auth_user,
                    project_name, project_owner, project_address, project_phone,
                    serialize_state_dict()
                )
                st.success("¡Guardado Correcto en DB!")
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    with col2:
        st.download_button(
            label=" Local",
            data=json.dumps(serialize_state_dict(), indent=4),
            file_name=f"{project_name}_{datetime.datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
            help="Descargar archivo JSON a tu Equipo"
        )
else:
    st.sidebar.info(" Llena los datos arriba para habilitar el guardado.")

uploaded_project = st.sidebar.file_uploader(" Cargar Archivo Local (.json)", type=['json'])
if uploaded_project is not None:
    try:
        project_data = json.load(uploaded_project)
        for k, v in project_data.items():
            if isinstance(v, dict) and v.get("__type__") == "dataframe":
                st.session_state[k] = pd.DataFrame(v["data"])
            else:
                st.session_state[k] = v
        st.sidebar.success(f"Archivo Local Cargado ")
    except Exception as e:
        st.sidebar.error(f"Error al cargar: {e}")


# Inicializar APU global por si entran directo a otra pagina
if "apu_config" not in st.session_state:
    st.session_state.apu_config = {
        "moneda": "COP$",
        "cemento": 32000.0,
        "acero": 4500.0,
        "arena": 70000.0,
        "grava": 80000.0,
        "costo_dia_mo": 69333.33, # asumiendo smmlv+prestaciones basico
        "pct_herramienta": 0.05,
        "pct_aui": 0.30,
        "iva": 0.19,
        "pct_util": 0.05
    }


# ─────────────────────────────────────────────
# PIE DE PÁGINA / DERECHOS RESERVADOS
# ─────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: gray; font-size: 11px;">
    © 2026 Todos los derechos reservados.<br>
    <b>Realizado por:</b><br>
    <br><br>
    <i>⚠ Nota Legal: Herramienta de apoyo profesional.</i>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ST.NAVIGATION APP ROUTER (OCULTO + SELECTBOX)
# ─────────────────────────────────────────────
home      = st.Page(run_home, title="Inicio App", icon=":material/home:", default=True)

# Estructuras Principales
p_col     = st.Page("pages/01_Columnas_PM.py", title="Columnas PM", icon=":material/domain:")
p_vig     = st.Page("pages/02_Vigas_Losas.py", title="Vigas Losas", icon=":material/horizontal_rule:")
p_zap     = st.Page("pages/09_Zapatas.py", title="Zapatas", icon=":material/layers:")
p_mcont   = st.Page("pages/12_Muros_Contencion.py", title="Muros Contención", icon=":material/view_stream:")
p_ccirc   = st.Page("pages/07_Columnas_Circulares.py", title="Columnas Circulares", icon=":material/lens:")
p_pred    = st.Page("pages/04_Predimensionamiento.py", title="Predimensionamiento", icon=":material/straighten:")

# Sismo & Viento
p_sismo   = st.Page("pages/15_Diseño_Sismico.py", title="Diseño Sísmico", icon=":material/public:")
p_viento  = st.Page("pages/16_viento simplificado.py", title="Viento Simplificado", icon=":material/air:")
p_irreg   = st.Page("pages/17_Irregularidades.py", title="Irregularidades", icon=":material/architecture:")

# Mampostería y Alternativos
p_mamp_e  = st.Page("pages/24_Mamposteria_Estructural.py", title="Mampostería Estructural", icon=":material/grid_on:")
p_mamp_m  = st.Page("pages/13_Mamposteria_Morteros.py", title="Mampostería Morteros", icon=":material/apps:")
p_placa   = st.Page("pages/08_Placa facil.py", title="Placa fácil", icon=":material/view_module:")
p_konte   = st.Page("pages/11_Kontewall.py", title="Kontewall", icon=":material/view_compact:")
p_mad     = st.Page("pages/14_Madera_Estructuras.py", title="Madera Estructuras", icon=":material/forest:")
p_metal   = st.Page("pages/18_Estructuras_Metalicas.py", title="Estructuras Metálicas", icon=":material/build:")

# Presupuesto y Materiales
p_calc    = st.Page("pages/06_Calculadora de Materiales.py", title="Calculadora Materiales", icon=":material/calculate:")
p_apu     = st.Page("pages/05_APU_Mercado.py", title="APU Mercado", icon=":material/payments:")

# Análisis y Utilidades
p_a2d     = st.Page("pages/21_Analisis_Estructural_2D.py", title="Análisis Estructural 2D", icon=":material/polyline:")
p_a3d     = st.Page("pages/22_Analisis_Estructural_3D.py", title="Análisis Estructural 3D", icon=":material/view_in_ar:")
p_gen3d   = st.Page("pages/23_Generador_Maestro_3D.py", title="Generador Maestro 3D", icon=":material/polyline:")
p_otras   = st.Page("pages/03_Otras_Estructuras.py", title="Otras Estructuras", icon=":material/extension:")
p_res     = st.Page("pages/19_Resistencia_Materiales.py", title="Resistencia Materiales", icon=":material/science:")
p_util    = st.Page("pages/20_Utilidades_Comunes.py", title="Utilidades Comunes", icon=":material/widgets:")

all_pages = [
    home, p_col, p_vig, p_zap, p_mcont, p_ccirc, p_pred,
    p_sismo, p_viento, p_irreg,
    p_mamp_e, p_mamp_m, p_placa, p_konte, p_mad, p_metal,
    p_calc, p_apu,
    p_a2d, p_a3d, p_gen3d, p_otras, p_res, p_util
]

# Inicializamos la navegación oculta
curr_page = st.navigation(all_pages, position="hidden")

# Lógica del Selectbox para Navegación Global
with menu_container:
    # Se busca el index de la página actual para que el selectbox inicie en el lugar correcto
    try:
        current_index = all_pages.index(curr_page)
    except ValueError:
        current_index = 0

    selected_page = st.selectbox(
        "Seleccione el Módulo:",
        options=all_pages,
        format_func=lambda page: page.title,
        index=current_index,
        key="nav_selectbox"
    )

    if selected_page.url_path != curr_page.url_path:
        st.switch_page(selected_page)

curr_page.run()

