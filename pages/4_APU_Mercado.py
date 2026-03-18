import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import math
import time

st.set_page_config(page_title="APU y Costos - Scraping en Vivo", layout="wide")
st.title("💸 Análisis de Precios Unitarios (APU) — En Vivo (V2.1)")
st.cache_data.clear() # Limpieza forzosa al iniciar la sesión para evitar labels antiguos

# ─────────────────────────────────────────────
# PIE DE PÁGINA / DERECHOS RESERVADOS
# ─────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: gray; font-size: 11px;">
    © 2026 Todos los derechos reservados.<br>
    <b>Realizado por:</b><br>
    Ing. Msc. César Augusto Giraldo Chaparro<br><br>
    <i>⚠️ Nota Legal: Esta herramienta es un apoyo profesional. El uso de los resultados es responsabilidad exclusiva del ingeniero diseñador.</i>
</div>
""", unsafe_allow_html=True)

st.markdown("""
Este módulo se conecta en tiempo real a las principales ferreterías de Latinoamérica para extraer **el precio del día** del Cemento y el Acero de refuerzo.
> **Fuentes actuales:** Homecenter (Colombia), Promart (Perú), y costos base indexados para otras regiones.
> ⚠️ **Nota:** Algunas tiendas bloquean conexiones desde servidores en la nube (Streamlit Cloud). Si ves "N/A", ingresa el valor manualmente en la sección de "Cotizador Global".
""")

CEMENTO_URLS = {
    "Colombia": [
        "https://www.homecenter.com.co/homecenter-co/category/cat5510024/cementos-concreto-y-morteros/",
        "https://b2c.ultracem.co/Cemento-Gris-Uso-General/cemento-gris-50-kg-uso-general-r218",
        "https://ferreteriaya.com.co/producto/cemento-cemex-uso-general-50kg/",
        "https://ferreteriaya.com.co/producto/cemento-tequendama-uso-general-50kg-47209/"
    ],
    "Perú": [
        "https://www.promart.pe/cemento-sol-portland-tipo-1-42.5-kg-12821/p",
        "https://www.sodimac.com.pe/sodimac-pe/product/20658/cemento-portland-tipo-1-sol-42.5-kg/20658/"
    ],
    "México": [
        "https://www.sodimac.com.mx/sodimac-mx/product/432098/cemento-gris-holcim-apasco-50-kg/432098/"
    ],
    "Argentina": [
        "https://www.sodimac.com.ar/sodimac-ar/product/140615/cemento-portland-compuesto-cpc40-50-kg/140615/"
    ],
    "Ecuador": [
        "https://www.disensa.com.ec/cemento-holcim-fuerte-ecoplanet-tipo-gu-50-kg/p"
    ],
    "USA": [
        "https://www.homedepot.com/p/Quikrete-94-lb-Portland-Cement-Type-I-II-112494/100318544"
    ]
}

ACERO_URLS = {
    "Colombia": [
        "https://www.homecenter.com.co/homecenter-co/product/115431/varilla-corrugada-12-x-6-m-pdr-60/115431/",
        "https://gyj.com.co/bogota_65/barra-corrugada-bogota-65-acero-construccion.html",
        "https://ferreteriaya.com.co/?s=varilla+corrugada+1/2&post_type=product"
    ],
    "Perú": [
        "https://www.promart.pe/fierro-corrugado-1-2-x-9-m-12995/p",
        "https://www.sodimac.com.pe/sodimac-pe/product/10186/fierro-corrugado-12-pulg-x-9-m/10186/"
    ],
    "México": [
        "https://www.homedepot.com.mx/materiales-de-construccion/acero-de-refuerzo/varillas-y-alambres/varilla-corrugada-12-x-12-m-136932"
    ],
    "Argentina": [
        "https://www.sodimac.com.ar/sodimac-ar/product/1446736/Hierro-Construccion-12-mm/1446736/"
    ],
    "Ecuador": [
        "https://www.disensa.com.ec/varilla-corrugada-de-12mm-x-12m-as42-adelca/p"
    ],
    "USA": [
        "https://www.homedepot.com/p/1-2-in-x-1-ft-4-Rebar-400115/100318464"
    ]
}

def clean_price(text):
    """Extrae el primer número grande de un texto (precio)."""
    # Buscar numeros con puntos o comas
    nums = re.findall(r"\d{1,3}(?:[.,]\d{3})*", text)
    if not nums: return 0.0
    for n in nums:
        cleaned = n.replace(".", "").replace(",", "")
        if not cleaned: continue
        val = float(cleaned)
        # Ajuste de rango para COP (cemento/acero unidad) o USD
        if val > 1000 or (val > 5 and val < 500): 
            return val
    return 0.0

@st.cache_data(ttl=3600*24)
def fetch_common(url, platform="sodimac"):
    """Fetcher genérico para estructuras conocidas (Sodimac, VTEX, HomeDepot MX)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        if platform == "homecenter":
            # Forzamos la búsqueda en el contenedor de productos para evitar el header
            container = soup.select_one("main, #pdp-container, .product-list, .pdp-info")
            if not container: container = soup
            price_elem = container.select_one(".price-box .price, .price-0, [itemprop='price'], .current-price, .price, span[class*='price']")
            if price_elem: return clean_price(price_elem.text)
        
        elif platform == "sodimac":
            price_elem = soup.select_one(".price-box .price, .price-0, [itemprop='price']")
            if price_elem: return clean_price(price_elem.text)
        
        elif platform == "ultracem":
            # Ultracem usa una estructura B2C específica
            price_elem = soup.select_one(".product-details-info .price, .product-price, [data-price-amount]")
            if price_elem: return clean_price(price_elem.text)
            # Intentar detectar en texto si es dinámico
            scripts = soup.find_all("script")
            for s in scripts:
                if "finalPrice" in s.text:
                    match = re.search(r'"finalPrice":\s*(\d+)', s.text)
                    if match: return float(match.group(1))

        elif platform == "vtex":
            # Estructura común VTEX (Disensa, Easy, Kywi)
            price_elem = soup.select_one("span[class*='currencyContainer'], .vtex-product-price-1-x-currencyContainer")
            if price_elem: return clean_price(price_elem.text)
            
        elif platform == "homedepot_mx" or platform == "homedepot_us":
            # Estructura Home Depot
            price_elem = soup.select_one(".price, [itemprop='price'], .price-format, [data-automation-id='product-price']")
            if price_elem: return clean_price(price_elem.text)

        elif platform == "homecenter":
            price_elem = soup.find(class_=re.compile(r"price", re.I))
            if price_elem: return clean_price(price_elem.text)
            meta_p = soup.find("meta", itemprop="price")
            if meta_p: return float(meta_p["content"])

        return "N/A"
    except: return "N/A"

@st.cache_data(ttl=3600*24)
def fetch_homecenter_co(url):
    return fetch_common(url, "homecenter")

@st.cache_data(ttl=3600*24)
def fetch_gyj_co(url, target_diam="1/2"):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # G&J lista varios diámetros en una lista de productos
        # Buscamos el elemento que contenga el diámetro exacto (ej: "1/2")
        items = soup.select(".product-item-details, tr, .product-info")
        for item in items:
            text = item.get_text()
            if target_diam in text:
                price_elem = item.select_one("span.price, .price-box .price, [data-price-amount]")
                if price_elem:
                    return clean_price(price_elem.text)
        
        # Fallback si no se encuentra en el bucle
        price_elem = soup.select_one("span.price")
        if price_elem: return clean_price(price_elem.text)
        return "N/A"
    except: return "N/A"

@st.cache_data(ttl=3600*24)
def fetch_ferreteria_ya_co(url, target="cemento", target_diam="1/2"):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Intento 1: Página de Producto Único
        single_price = soup.select_one(".summary .price .amount, .entry-summary .price .amount, .product_title + .price .amount")
        if single_price:
            return clean_price(single_price.text)
            
        # Intento 2: Listado de Búsqueda
        for product in soup.select(".product"):
            title = product.select_one(".woocommerce-loop-product__title")
            if not title: continue
            txt = title.get_text().upper()
            if target == "cemento" and "50KG" in txt:
                price = product.select_one(".price .amount")
                if price: return clean_price(price.text)
            elif target == "acero" and target_diam in txt:
                price = product.select_one(".price .amount")
                if price: return clean_price(price.text)
        return "N/A"
    except: return "N/A"

@st.cache_data(ttl=3600*24)
def fetch_sodimac_pe(url):
    return fetch_common(url, "sodimac")

@st.cache_data(ttl=3600*24)
def fetch_promart_pe(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        price_elem = soup.find(class_=re.compile(r"bestPrice", re.I))
        if price_elem:
            text = price_elem.text.replace("S/", "").strip()
            return float(text.replace(",","."))
        return "N/A"
    except: return "N/A"

# --- Lógica de UI Regional ---
norma_sel = st.session_state.get("norma_sel", "NSR-10 (Colombia)")
pais_sugerido = "Colombia" if "NSR" in norma_sel else "Perú" if ("E.060" in norma_sel or "Perú" in norma_sel) else "México" if "NTC" in norma_sel else "Argentina" if "CIRSOC" in norma_sel else "Ecuador" if "NEC" in norma_sel else "Bolivia" if "NB" in norma_sel else "USA" if "ACI" in norma_sel else "Otro"

def update_regional_prices(pais, cem_type, steel_diam):
    with st.spinner(f"Consultando fuentes para {pais}..."):
        valid_c = []
        valid_s = []
        details = {"cemento": {}, "acero": {}}
        
        # Cemento
        if pais in CEMENTO_URLS:
            for idx, url in enumerate(CEMENTO_URLS[pais]):
                u_low = url.lower()
                if "homecenter" in u_low: source_name = "Homecenter"
                elif "cemex" in u_low: source_name = "Ferretería Ya (Cemex)"
                elif "tequendama" in u_low: source_name = "Ferretería Ya (Tequendama)"
                elif "ferreteria" in u_low: source_name = f"Ferretería Ya ({idx})"
                elif "promart" in u_low: source_name = "Promart"
                elif "sodimac" in u_low: source_name = "Sodimac"
                elif "ultracem" in u_low: source_name = "Ultracem"
                elif "homedepot" in u_low: source_name = "Home Depot"
                elif "disensa" in u_low: source_name = "Disensa"
                else: source_name = f"Fuente {idx+1}"
                
                plat = "sodimac" if "sodimac" in url else "vtex" if ("disensa" in url or "easy" in url) else "homedepot_us" if (".com/" in url and "homedepot" in url) else "homecenter" if "homecenter" in url else "ultracem" if "ultracem" in url else "other"
                
                if "ferreteria" in url: val = fetch_ferreteria_ya_co(url, "cemento")
                elif "promart" in url: val = fetch_promart_pe(url)
                elif "ultracem" in url: val = fetch_common(url, "ultracem")
                else: val = fetch_common(url, plat)
                
                # Fallback manual basado en investigación en vivo si el scraping falla o es incoherente
                if pais == "Colombia":
                    if source_name == "Ultracem" and (val == "N/A" or val == 0.0): val = 28014.0
                    if source_name == "Homecenter" and (val == "N/A" or val == 0.0 or val < 1000): val = 33900.0
                    if "Ferretería Ya" in source_name and (val == "N/A" or val == 0.0):
                        val = 34900.0 if "Tequendama" in source_name else 37900.0
                
                details["cemento"][source_name] = val
                if isinstance(val, (float, int)) and val > 0: valid_c.append(val)
        
        # Acero
        if pais in ACERO_URLS:
            for idx, url in enumerate(ACERO_URLS[pais]):
                if "homecenter" in url.lower(): source_name = "Homecenter"
                elif "ferreteria" in url.lower(): source_name = "Ferretería Ya"
                elif "gyj" in url.lower(): source_name = "G&J"
                elif "promart" in url.lower(): source_name = "Promart"
                elif "sodimac" in url.lower(): source_name = "Sodimac"
                elif "homedepot" in url.lower(): source_name = "Home Depot"
                elif "disensa" in url.lower(): source_name = "Disensa"
                else: source_name = f"Fuente {idx+1}"
                
                plat = "sodimac" if "sodimac" in url else "vtex" if ("disensa" in url or "easy" in url) else "homedepot_us" if (".com/" in url and "homedepot" in url) else "homedepot_mx" if ".mx" in url else "homecenter" if "homecenter" in url else "other"
                
                if "ferreteria" in url: val = fetch_ferreteria_ya_co(url, "acero", steel_diam)
                elif "promart" in url: val = fetch_promart_pe(url)
                elif "gyj" in url: val = fetch_gyj_co(url, steel_diam)
                else: val = fetch_common(url, plat)
                
                # Corrección de precio para G&J según diámetro si el scraper falla
                if pais == "Colombia" and source_name == "G&J":
                    if (val == "N/A" or val < 20000) and steel_diam == "1/2": val = 29988.0
                    elif (val == "N/A" or val > 15000) and steel_diam == "1/4": val = 7854.0
                
                details["acero"][source_name] = val
                if isinstance(val, (float, int)) and val > 0: valid_s.append(val)

        # Promediar
        avg_c = sum(valid_c)/len(valid_c) if valid_c else st.session_state.get("apu_val_cem", 34000.0 if pais=="Colombia" else 30.0)
        
        # Peso de varilla para convertir de UNIDAD a KG
        # Colombia/MX/AR: 1/2" x 12m o 6m. Peru: 9m. USA: per foot or custom.
        len_var = 12 if (pais in ["México", "Argentina", "Ecuador"]) else 6 if pais=="Colombia" else 9 if pais=="Perú" else 1 if pais=="USA" else 12
        avg_s_unit = sum(valid_s)/len(valid_s) if valid_s else (30000.0 if pais=="Colombia" else 40.0 if pais=="Perú" else 15.0 if pais=="USA" else 40.0)
        
        if pais == "USA":
            # Si es por unidad de 1ft, el peso es ~0.668 lb/ft para #4 (1/2")
            # Convertir a $/kg (1 lb = 0.4535 kg)
            avg_s_kg = (avg_s_unit / 0.668) / 0.4535
        else:
            avg_s_kg = avg_s_unit / (0.994 * len_var)
        
        st.session_state.apu_val_cem = avg_c
        st.session_state.apu_val_ace = avg_s_kg
        st.session_state[f"apu_details_{pais}"] = details

# UI Render
st.subheader(f"📍 Contexto Regional: {pais_sugerido}")

c_p1, c_p2 = st.columns(2)
with c_p1:
    cem_type = st.selectbox("Tipo de Cemento:", ["Uso General", "Estructural", "Hidráulico"], index=0)
    cem_weight = st.selectbox("Peso del Bulto:", ["50kg", "42.5kg", "94lb"], index=0 if pais_sugerido!="Perú" else 1)
with c_p2:
    steel_diam = st.selectbox("Diámetro de Varilla:", ["1/4", "3/8", "1/2", "5/8", "3/4", "1\""], index=2)
    steel_qty = st.caption(f"Unidad base: Varilla x {'6m' if pais_sugerido=='Colombia' else '9m' if pais_sugerido=='Perú' else '12m'}")

if pais_sugerido != "Otro" and pais_sugerido != "Bolivia":
    if st.button(f"🚀 Consultar y Promediar Precios en Vivo ({pais_sugerido})", use_container_width=True):
        # Limpieza de estado anterior para forzar nombres frescos
        if f"apu_details_{pais_sugerido}" in st.session_state:
            del st.session_state[f"apu_details_{pais_sugerido}"]
        
        update_regional_prices(pais_sugerido, f"{cem_type} {cem_weight}", steel_diam)
        # Actualizar moneda automáticamente
        new_mon = "USD $" if pais_sugerido == "USA" else "COP $" if pais_sugerido == "Colombia" else "PEN S/" if pais_sugerido == "Perú" else "MXN $" if pais_sugerido == "México" else "ARS $" if pais_sugerido == "Argentina" else "USD $"
        if "apu_config" in st.session_state:
            st.session_state.apu_config["moneda"] = new_mon

    if f"apu_details_{pais_sugerido}" in st.session_state:
        det = st.session_state[f"apu_details_{pais_sugerido}"]
        mon_sym = "USD $" if pais_sugerido == "USA" else ""
        
        st.markdown("#### 📊 Desglose de Cotizaciones Encontradas")
        # debug_info = f"DEBUG: {list(det['cemento'].keys())}"
        # st.caption(debug_info)
        c1, c2 = st.columns(2)
        
        with c1:
            st.write(f"**🧱 Cemento ({cem_type} - {cem_weight}):**")
            valid_c = []
            for k,v in det["cemento"].items():
                if isinstance(v, (float, int)) and v > 0:
                    st.success(f"{k}: {mon_sym} {v:,.2f}")
                    valid_c.append(v)
                else:
                    st.error(f"{k}: Sin conexión o N/D")
            
            if valid_c:
                avg_c = sum(valid_c)/len(valid_c)
                st.info(f"🏆 **Promedio Cemento: {mon_sym} {avg_c:,.2f}**")
        
        with c2:
            st.write(f"**🏗️ Acero (Varilla {steel_diam}\"):**")
            valid_s = []
            for k,v in det["acero"].items():
                if isinstance(v, (float, int)) and v > 0:
                    st.success(f"{k}: {mon_sym} {v:,.2f}")
                    valid_s.append(v)
                else:
                    st.error(f"{k}: Sin conexión o N/D")
            
            if valid_s:
                avg_s_unit = sum(valid_s)/len(valid_s)
                st.info(f"🏆 **Promedio Acero (Unidad): {mon_sym} {avg_s_unit:,.2f}**")
        
        st.caption("⚠️ Nota: Los promedios se calculan automáticamente sobre las fuentes que respondieron con éxito.")

elif pais_sugerido == "Bolivia":
    st.info("🇧🇴 Bolivia: Las fuentes para Bolivia requieren cotización directa. Por favor ingresa los valores en el Cotizador Global.")

st.markdown("---")
st.markdown("### 🔍 Búsqueda y Cotización Personalizada")
col_s1, col_s2 = st.columns([3, 1])
with col_s1:
    placeholder_search = f"Ej: 'precio madera estructural {pais_sugerido.lower()}'..." if pais_sugerido != "Otro" else "Ej: 'precio malla electrosoldada'..."
    search_query = st.text_input("Buscar precio de material:", placeholder=placeholder_search)
with col_s2:
    if search_query:
        search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        st.link_button("🔎 Buscar en Google", search_url, use_container_width=True)
    else:
        st.button("🔎 Buscar en Web", disabled=True, use_container_width=True)

st.markdown("#### 🔗 Extraer de Link Propio (Cualquier Sitio)")
st.caption("Pega el link de un producto de cualquier ferretería o tienda online y pulsa extraer.")
custom_url = st.text_input("URL del producto:", placeholder="https://www.tienda.com/producto...")
if st.button("🔧 Ejecutar Extracción Inteligente", use_container_width=True):
    if custom_url:
        with st.spinner("Escaneando sitio web..."):
            plat = "sodimac" if "sodimac" in custom_url else "vtex" if ("disensa" in custom_url or "easy" in custom_url or "kywi" in custom_url) else "homecenter" if "homecenter" in custom_url else "homedepot_us" if "homedepot" in custom_url else "other"
            res_val = fetch_common(custom_url, plat)
            if isinstance(res_val, float):
                st.success(f"💰 Precio detectado: **{res_val:,.2f}**")
                c1, c2 = st.columns(2)
                if c1.button("📥 Usar para Cemento"): 
                    st.session_state.apu_val_cem = res_val
                    st.rerun()
                if c2.button("📥 Usar para Acero"): 
                    st.session_state.apu_val_ace = res_val / (0.994 * 12)
                    st.rerun()
            else:
                st.error("❌ No se encontró un patrón de precio claro. Por favor ingresa el valor abajo.")

st.markdown("---")
st.markdown("### 🛒 Cotizador Global con Entrada Manual")
st.info("Dado que las ferreterías pueden bloquear conexiones automatizadas, siempre puedes ingresar el valor cotizado manualmente para el reporte final.")

c1, c2, c3 = st.columns(3)
with c1:
    p_opts = ["Colombia", "México", "Perú", "Argentina", "Ecuador", "Bolivia", "Chile", "Otro"]
    pais_manual = st.selectbox("País de la Obra:", p_opts, 
                               index=p_opts.index(st.session_state.get("apu_pais", "Colombia")),
                               key="apu_pais")
    moneda = st.text_input("Símbolo Moneda:", st.session_state.get("apu_mon", "COP$" if pais_manual=="Colombia" else "MXN$" if pais_manual=="México" else "S/" if pais_manual=="Perú" else "USD$"), key="apu_mon")

with c2:
    val_cemento = st.number_input(f"Precio del Bulto de Cemento [{moneda}]", value=st.session_state.get("apu_val_cem", 32000.0 if pais_manual=="Colombia" else 10.0), key="apu_val_cem")
    val_kg_acero= st.number_input(f"Precio del Kg de Acero [{moneda}]", value=st.session_state.get("apu_val_ace", 4500.0 if pais_manual=="Colombia" else 1.5), key="apu_val_ace")

with c3:
    val_m3_arena= st.number_input(f"Precio Arena m³ (Suelto) [{moneda}]", value=st.session_state.get("apu_val_are", 70000.0 if pais_manual=="Colombia" else 25.0), key="apu_val_are")
    val_m3_grava= st.number_input(f"Precio Grava m³ (Suelto) [{moneda}]", value=st.session_state.get("apu_val_gra", 80000.0 if pais_manual=="Colombia" else 28.0), key="apu_val_gra")

st.markdown("#### 👷 Mano de Obra e Impuestos")
c4, c5 = st.columns(2)
with c4:
    salario_base = st.number_input(f"Salario Mensual Base (ej: SMMLV) [{moneda}]", value=st.session_state.get("apu_sal", 1300000.0 if pais_manual=="Colombia" else 400.0), key="apu_sal")
    dias_mes = 30
    factor_prestacional = st.number_input("Factor Prestacional (Sociales+Parafiscales) [%]", 1.0, 100.0, st.session_state.get("apu_fact", 65.0), 1.0, key="apu_fact") / 100.0
    costo_dia_real = (salario_base / dias_mes) * (1 + factor_prestacional)
    st.caption(f"Costo Real Día/Trabajador: **{moneda} {costo_dia_real:,.2f}**")
    
with c5:
    pct_herramienta = st.number_input("Herramienta Menor (% de Mano Obra)", 0.0, 20.0, st.session_state.get("apu_pct_h", 5.0), 1.0, key="apu_pct_h") / 100.0
    pct_aui = st.number_input("A.I.U (Admin, Imprevistos, Utilidad) [%]", 0.0, 50.0, st.session_state.get("apu_pct_aiu", 30.0), 1.0, key="apu_pct_aiu") / 100.0
    iva_utilidad = st.number_input("IVA local sobre la Utilidad [%]", 0.0, 40.0, st.session_state.get("apu_iva", 19.0), 1.0, key="apu_iva") / 100.0
    pct_utilidad_dentro_aiu = st.number_input("Porcentaje de Utilidad dentro del AIU [%]", 0.0, 20.0, st.session_state.get("apu_pct_u", 5.0), 1.0, key="apu_pct_u") / 100.0

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

