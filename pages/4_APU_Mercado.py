import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import math
import time


st.title("💸 Análisis de Precios Unitarios (APU) — En Vivo")

st.markdown("""
Este módulo se conecta en tiempo real a las principales ferreterías de Latinoamérica para extraer **el precio del día** del Cemento y el Acero de refuerzo.
> **Fuentes actuales:** Homecenter (Colombia), Promart (Perú), y costos base indexados para otras regiones.
""")

CEMENTO_URLS = {
    "Colombia": "https://www.homecenter.com.co/homecenter-co/product/14294/cemento-gris-uso-general-50-kg/14294/",
    "Perú": "https://www.promart.pe/cemento-sol-portland-tipo-1-42.5-kg-12821/p"
}

ACERO_URLS = {
    "Colombia": "https://www.homecenter.com.co/homecenter-co/product/115431/varilla-corrugada-12-x-6-m-pdr-60/115431/",
    "Perú": "https://www.promart.pe/fierro-corrugado-1-2-x-9-m-12995/p"
}

def clean_price(text):
    """Extrae el primer número grande de un texto (precio)."""
    # Buscar numeros con puntos o comas
    nums = re.findall(r"\d{1,3}(?:[.,]\d{3})*", text)
    if not nums: return 0.0
    for n in nums:
        val = float(n.replace(".", "").replace(",", ""))
        if val > 1000: # Asumir que el precio es mayor a 1000 en COP/PEN 
            return val
    return 0.0

@st.cache_data(ttl=3600*24) # Caché de 24 horas para no saturar tiendas
def fetch_homecenter_co(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Buscar clases de precios comunes
        price_elem = soup.find(class_=re.compile(r"price", re.I))
        if price_elem:
            return clean_price(price_elem.text)
        else:
            # Fallback en meta-tags
            meta_p = soup.find("meta", itemprop="price")
            if meta_p: return float(meta_p["content"])
        return "N/A"
    except Exception as e:
        return f"Error: {e}"

@st.cache_data(ttl=3600*24)
def fetch_promart_pe(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        price_elem = soup.find(class_=re.compile(r"bestPrice", re.I))
        if price_elem:
            text = price_elem.text.replace("S/", "").strip()
            return float(text.replace(",","."))
        return "N/A"
    except Exception as e:
        return f"Error: {e}"

# UI 
b1, b2 = st.columns(2)
with b1:
    st.subheader("🇨🇴 Mercado Colombiano (COP$)")
    if st.button("Buscar en Homecenter CO"):
        with st.spinner("Consultando precio del Cemento (50kg)..."):
            p_cem_co = fetch_homecenter_co(CEMENTO_URLS["Colombia"])
        with st.spinner("Consultando precio del Acero (1/2\")..."):
            p_acero_co = fetch_homecenter_co(ACERO_URLS["Colombia"])
        
        st.metric("Cemento 50kg (Argos/Cemex)", f"$ {p_cem_co:,.0f} COP" if isinstance(p_cem_co, float) else p_cem_co)
        st.metric("Varilla Acero 1/2\" (6m)", f"$ {p_acero_co:,.0f} COP" if isinstance(p_acero_co, float) else p_acero_co)
        st.caption("Fuente: homecenter.com.co")

with b2:
    st.subheader("🇵🇪 Mercado Peruano (PEN S/)")
    if st.button("Buscar en Promart PE"):
        with st.spinner("Consultando Cemento (42.5kg)..."):
            p_cem_pe = fetch_promart_pe(CEMENTO_URLS["Perú"])
        with st.spinner("Consultando Acero (1/2\")..."):
            p_acero_pe = fetch_promart_pe(ACERO_URLS["Perú"])
            
        st.metric("Cemento Sol Tipo I (42.5kg)", f"S/ {p_cem_pe:,.2f}" if isinstance(p_cem_pe, float) else p_cem_pe)
        st.metric("Fierro Corrugado 1/2\" (9m)", f"S/ {p_acero_pe:,.2f}" if isinstance(p_acero_pe, float) else p_acero_pe)
        st.caption("Fuente: promart.pe")

st.markdown("---")
st.markdown("### 🛒 Cotizador Global con Entrada Manual")
st.info("Dado que las ferreterías pueden bloquear conexiones automatizadas, siempre puedes ingresar el valor cotizado manualmente para el reporte final.")

c1, c2, c3 = st.columns(3)
with c1:
    pais_manual = st.selectbox("País de la Obra:", ["Colombia", "México", "Perú", "Argentina", "Ecuador", "Bolivia", "Chile", "Otro"])
    moneda = st.text_input("Símbolo Moneda:", "COP$" if pais_manual=="Colombia" else "MXN$" if pais_manual=="México" else "S/" if pais_manual=="Perú" else "USD$")

with c2:
    val_cemento = st.number_input(f"Precio del Bulto de Cemento [{moneda}]", value=32000.0 if pais_manual=="Colombia" else 10.0)
    val_kg_acero= st.number_input(f"Precio del Kg de Acero [{moneda}]", value=4500.0 if pais_manual=="Colombia" else 1.5)

with c3:
    val_m3_arena= st.number_input(f"Precio Arena m³ (Suelto) [{moneda}]", value=70000.0 if pais_manual=="Colombia" else 25.0)
    val_m3_grava= st.number_input(f"Precio Grava m³ (Suelto) [{moneda}]", value=80000.0 if pais_manual=="Colombia" else 28.0)

st.markdown("#### 👷 Mano de Obra e Impuestos")
c4, c5 = st.columns(2)
with c4:
    salario_base = st.number_input(f"Salario Mensual Base (ej: SMMLV) [{moneda}]", value=1300000.0 if pais_manual=="Colombia" else 400.0)
    dias_mes = 30
    factor_prestacional = st.number_input("Factor Prestacional (Sociales+Parafiscales) [%]", 1.0, 100.0, 65.0, 1.0) / 100.0
    costo_dia_real = (salario_base / dias_mes) * (1 + factor_prestacional)
    st.caption(f"Costo Real Día/Trabajador: **{moneda} {costo_dia_real:,.2f}**")
    
with c5:
    pct_herramienta = st.number_input("Herramienta Menor (% de Mano Obra)", 0.0, 20.0, 5.0, 1.0) / 100.0
    pct_aui = st.number_input("A.I.U (Admin, Imprevistos, Utilidad) [%]", 0.0, 50.0, 30.0, 1.0) / 100.0
    iva_utilidad = st.number_input("IVA local sobre la Utilidad [%]", 0.0, 40.0, 19.0, 1.0) / 100.0
    pct_utilidad_dentro_aiu = st.number_input("Porcentaje de Utilidad dentro del AIU [%]", 0.0, 20.0, 5.0, 1.0) / 100.0

st.session_state.apu_config = {
    "moneda": moneda,
    "cemento": val_cemento,
    "acero": val_kg_acero,
    "arena": val_m3_arena,
    "grava": val_m3_grava,
    "costo_dia_mo": costo_dia_real,
    "pct_herramienta": pct_herramienta,
    "pct_aui": pct_aui,
    "iva": iva_utilidad,
    "pct_util": pct_utilidad_dentro_aiu
}

st.success("✅ Los precios han sido guardados temporalmente en la sesión. Aparecerán reflejados en el análisis APU de tus memorias de cálculo.")

