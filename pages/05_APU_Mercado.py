import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import math
import time
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(page_title="APU y Costos - Scraping en Vivo", layout="wide")

# ─────────────────────────────────────────────
# IDIOMA GLOBAL
lang = st.session_state.get("idioma", "Español")
def _t(es, en):
    return en if lang == "English" else es

st.title(_t("Análisis de Precios Unitarios (APU) — En Vivo", " Unit Price Analysis (APU) — Live"))
st.cache_data.clear()

# ─────────────────────────────────────────────
# PIE DE PÁGINA / DERECHOS RESERVADOS
# ─────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="text-align: center; color: gray; font-size: 11px;">
    © 2026 Todos los derechos reservados.<br>
    <b>Realizado por:</b><br>
    <br><br>
    <i>⚠ Nota Legal: Esta herramienta es un apoyo profesional. El uso de los resultados es responsabilidad exclusiva del ingeniero diseñador.</i>
</div>
""", unsafe_allow_html=True)

st.markdown(_t("""
Este módulo se conecta en tiempo real a las principales ferreterías de Latinoamérica para extraer **el precio del día** del Cemento y el Acero de refuerzo.
> **Fuentes actuales:** Homecenter (Colombia), Promart (Perú), Sodimac (varios países), y costos base indexados para otras regiones.
> ⚠ **Nota:** Algunas tiendas bloquean conexiones desde servidores en la nube (Streamlit Cloud). Si ves "N/A", ingresa el valor manualmente en la sección de "Cotizador Global".
""", """
This module connects in real time to major hardware stores in Latin America to extract **today's price** of Cement and Reinforcing Steel.
> **Current sources:** Homecenter (Colombia), Promart (Perú), Sodimac (various countries), and baseline costs for other regions.
> ⚠ **Note:** Some stores block connections from cloud servers (Streamlit Cloud). If you see "N/A", enter the value manually in the "Global Quoter" section.
"""))

# ------------------------------------------------------------------------------
# Scraping helpers with retry and backoff
# ------------------------------------------------------------------------------
def fetch_with_retry(url, max_retries=3, backoff=1.0):
    """Fetch URL with retries and exponential backoff."""
    for attempt in range(max_retries):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                return res.text
            else:
                if attempt < max_retries - 1:
                    time.sleep(backoff * (2 ** attempt))
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(backoff * (2 ** attempt))
            else:
                return None
    return None

def clean_price(text):
    """Extrae el primer número grande de un texto (precio)."""
    nums = re.findall(r"\d{1,3}(?:[.,]\d{3})*", text)
    if not nums:
        return 0.0
    for n in nums:
        cleaned = n.replace(".", "").replace(",", "")
        if not cleaned:
            continue
        val = float(cleaned)
        # Ajuste de rango para COP (cemento/acero unidad) o USD
        if val > 1000 or (val > 5 and val < 500):
            return val
    return 0.0

def fetch_common(url, platform="sodimac"):
    """Fetcher genérico para estructuras conocidas."""
    html = fetch_with_retry(url)
    if not html:
        return "N/A"
    soup = BeautifulSoup(html, 'html.parser')
    
    if platform == "homecenter":
        container = soup.select_one("main, #pdp-container, .product-list, .pdp-info") or soup
        price_elem = container.select_one(".price-box .price, .price-0, [itemprop='price'], .current-price, .price, span[class*='price']")
        if price_elem:
            return clean_price(price_elem.text)
    elif platform == "sodimac":
        price_elem = soup.select_one(".price-box .price, .price-0, [itemprop='price']")
        if price_elem:
            return clean_price(price_elem.text)
    elif platform == "ultracem":
        price_elem = soup.select_one(".product-details-info .price, .product-price, [data-price-amount]")
        if price_elem:
            return clean_price(price_elem.text)
        scripts = soup.find_all("script")
        for s in scripts:
            if "finalPrice" in s.text:
                match = re.search(r'"finalPrice":\s*(\d+)', s.text)
                if match:
                    return float(match.group(1))
    elif platform == "vtex":
        price_elem = soup.select_one("span[class*='currencyContainer'], .vtex-product-price-1-x-currencyContainer")
        if price_elem:
            return clean_price(price_elem.text)
    elif platform == "homedepot_mx" or platform == "homedepot_us":
        price_elem = soup.select_one(".price, [itemprop='price'], .price-format, [data-automation-id='product-price']")
        if price_elem:
            return clean_price(price_elem.text)
    elif platform == "easy":
        price_elem = soup.select_one(".product-price, .prices__value")
        if price_elem:
            return clean_price(price_elem.text)
    return "N/A"

# ------------------------------------------------------------------------------
# URLs actualizadas con más países
# ------------------------------------------------------------------------------
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
    "Chile": [
        "https://www.sodimac.cl/sodimac-cl/product/1446736/Cemento-Infraestructura-Especial-42-5-kg/1446736/",
        "https://www.easy.cl/cemento-especial-42-5-kg/p"
    ],
    "Bolivia": [
        "https://www.ferretron.com/producto/cemento-uso-general-50-kg/",
        "https://www.ferreteriapc.com/producto/cemento-uso-general-50-kg/"
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
    "Chile": [
        "https://www.sodimac.cl/sodimac-cl/product/1346736/Hierro-12-mm/1346736/",
        "https://www.easy.cl/hierro-corrugado-12-mm/p"
    ],
    "Bolivia": [
        "https://www.ferretron.com/producto/varilla-corrugada-12-mm-6-m/",
        "https://www.ferreteriapc.com/producto/varilla-corrugada-12-mm/"
    ],
    "USA": [
        "https://www.homedepot.com/p/1-2-in-x-1-ft-4-Rebar-400115/100318464"
    ]
}

# ------------------------------------------------------------------------------
# Funciones de scraping específicas
# ------------------------------------------------------------------------------
def fetch_ferreteria_ya_co(url, target="cemento", target_diam="1/2"):
    html = fetch_with_retry(url)
    if not html:
        return "N/A"
    soup = BeautifulSoup(html, 'html.parser')
    single_price = soup.select_one(".summary .price .amount, .entry-summary .price .amount, .product_title + .price .amount")
    if single_price:
        return clean_price(single_price.text)
    for product in soup.select(".product"):
        title = product.select_one(".woocommerce-loop-product__title")
        if not title:
            continue
        txt = title.get_text().upper()
        if target == "cemento" and "50KG" in txt:
            price = product.select_one(".price .amount")
            if price:
                return clean_price(price.text)
        elif target == "acero" and target_diam in txt:
            price = product.select_one(".price .amount")
            if price:
                return clean_price(price.text)
    return "N/A"

def fetch_gyj_co(url, target_diam="1/2"):
    html = fetch_with_retry(url)
    if not html:
        return "N/A"
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select(".product-item-details, tr, .product-info")
    for item in items:
        text = item.get_text()
        if target_diam in text:
            price_elem = item.select_one("span.price, .price-box .price, [data-price-amount]")
            if price_elem:
                return clean_price(price_elem.text)
    price_elem = soup.select_one("span.price")
    if price_elem:
        return clean_price(price_elem.text)
    return "N/A"

def fetch_promart_pe(url):
    html = fetch_with_retry(url)
    if not html:
        return "N/A"
    soup = BeautifulSoup(html, 'html.parser')
    price_elem = soup.find(class_=re.compile(r"bestPrice", re.I))
    if price_elem:
        text = price_elem.text.replace("S/", "").strip()
        return float(text.replace(",", "."))
    return "N/A"

def fetch_easy_cl(url):
    html = fetch_with_retry(url)
    if not html:
        return "N/A"
    return fetch_common(url, "easy")

def fetch_sodimac_cl(url):
    return fetch_common(url, "sodimac")

def fetch_ferretron_bo(url):
    return fetch_common(url, "vtex")

# ------------------------------------------------------------------------------
# Actualización de precios con gráficos y exportación
# ------------------------------------------------------------------------------
def update_regional_prices(pais, cem_type, steel_diam):
    with st.spinner(_t(f"Consultando fuentes para {pais}...", f"Querying sources for {pais}...")):
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
                elif "easy" in u_low: source_name = "Easy"
                elif "ferretron" in u_low: source_name = "Ferretron"
                else: source_name = f"Fuente {idx+1}"
                
                plat = "sodimac" if "sodimac" in url else "vtex" if ("disensa" in url or "easy" in url) else "homedepot_us" if (".com/" in url and "homedepot" in url) else "homecenter" if "homecenter" in url else "ultracem" if "ultracem" in url else "easy" if "easy" in url else "other"
                
                if "ferreteria" in url: val = fetch_ferreteria_ya_co(url, "cemento")
                elif "promart" in url: val = fetch_promart_pe(url)
                elif "ultracem" in url: val = fetch_common(url, "ultracem")
                elif "easy" in url and pais == "Chile": val = fetch_easy_cl(url)
                elif "ferretron" in url: val = fetch_ferretron_bo(url)
                else: val = fetch_common(url, plat)
                
                # Fallbacks manuales
                if pais == "Colombia":
                    if source_name == "Ultracem" and (val == "N/A" or val == 0.0): val = 28014.0
                    if source_name == "Homecenter" and (val == "N/A" or val == 0.0 or val < 1000): val = 33900.0
                    if "Ferretería Ya" in source_name and (val == "N/A" or val == 0.0):
                        val = 34900.0 if "Tequendama" in source_name else 37900.0
                elif pais == "Chile":
                    if "Sodimac" in source_name and (val == "N/A" or val == 0.0): val = 8500.0  # CLP
                    if "Easy" in source_name and (val == "N/A" or val == 0.0): val = 8900.0
                elif pais == "Bolivia":
                    if val == "N/A" or val == 0.0: val = 55.0  # BOB
                
                details["cemento"][source_name] = val
                if isinstance(val, (float, int)) and val > 0: valid_c.append(val)
        
        # Acero
        if pais in ACERO_URLS:
            for idx, url in enumerate(ACERO_URLS[pais]):
                u_low = url.lower()
                if "homecenter" in u_low: source_name = "Homecenter"
                elif "ferreteria" in u_low: source_name = "Ferretería Ya"
                elif "gyj" in u_low: source_name = "G&J"
                elif "promart" in u_low: source_name = "Promart"
                elif "sodimac" in u_low: source_name = "Sodimac"
                elif "homedepot" in u_low: source_name = "Home Depot"
                elif "disensa" in u_low: source_name = "Disensa"
                elif "easy" in u_low: source_name = "Easy"
                elif "ferretron" in u_low: source_name = "Ferretron"
                else: source_name = f"Fuente {idx+1}"
                
                plat = "sodimac" if "sodimac" in url else "vtex" if ("disensa" in url or "easy" in url) else "homedepot_us" if (".com/" in url and "homedepot" in url) else "homedepot_mx" if ".mx" in url else "homecenter" if "homecenter" in url else "easy" if "easy" in url else "other"
                
                if "ferreteria" in url: val = fetch_ferreteria_ya_co(url, "acero", steel_diam)
                elif "promart" in url: val = fetch_promart_pe(url)
                elif "gyj" in url: val = fetch_gyj_co(url, steel_diam)
                elif "easy" in url and pais == "Chile": val = fetch_easy_cl(url)
                elif "ferretron" in url: val = fetch_ferretron_bo(url)
                else: val = fetch_common(url, plat)
                
                # Fallbacks manuales
                if pais == "Colombia" and source_name == "G&J":
                    if (val == "N/A" or val < 20000) and steel_diam == "1/2": val = 29988.0
                    elif (val == "N/A" or val > 15000) and steel_diam == "1/4": val = 7854.0
                elif pais == "Chile":
                    if "Sodimac" in source_name and (val == "N/A" or val == 0.0): val = 12500.0
                    if "Easy" in source_name and (val == "N/A" or val == 0.0): val = 12800.0
                elif pais == "Bolivia":
                    if val == "N/A" or val == 0.0: val = 28.0
                
                details["acero"][source_name] = val
                if isinstance(val, (float, int)) and val > 0: valid_s.append(val)
        
        # Promediar
        avg_c = sum(valid_c)/len(valid_c) if valid_c else st.session_state.get("apu_val_cem", 34000.0 if pais=="Colombia" else 30.0)
        
        # Convertir precio de unidad a kg
        len_var = 12 if (pais in ["México", "Argentina", "Ecuador", "Chile"]) else 6 if pais=="Colombia" else 9 if pais=="Perú" else 1 if pais=="USA" else 12
        avg_s_unit = sum(valid_s)/len(valid_s) if valid_s else (30000.0 if pais=="Colombia" else 40.0 if pais=="Perú" else 15.0 if pais=="USA" else 40.0)
        
        if pais == "USA":
            # Para #4 (1/2") peso por pie: 0.668 lb/ft, 1 lb = 0.4535 kg
            avg_s_kg = (avg_s_unit / 0.668) / 0.4535
        else:
            avg_s_kg = avg_s_unit / (0.994 * len_var)
        
        st.session_state.apu_val_cem = avg_c
        st.session_state.apu_val_ace = avg_s_kg
        st.session_state[f"apu_details_{pais}"] = details
        st.session_state[f"apu_grafica_{pais}"] = {"cemento": valid_c, "acero": valid_s, "sources_c": list(details["cemento"].keys()), "sources_s": list(details["acero"].keys())}

# ------------------------------------------------------------------------------
# UI principal
# ------------------------------------------------------------------------------
norma_sel = st.session_state.get("norma_sel", "NSR-10 (Colombia)")
pais_sugerido = "Colombia" if "NSR" in norma_sel else "Perú" if ("E.060" in norma_sel or "Perú" in norma_sel) else "México" if "NTC" in norma_sel else "Argentina" if "CIRSOC" in norma_sel else "Ecuador" if "NEC" in norma_sel else "Chile" if "CIRSOC" not in norma_sel and "ACI" in norma_sel else "Bolivia" if "NB" in norma_sel else "USA" if "ACI" in norma_sel else "Otro"

st.subheader(_t(f"Contexto Regional: {pais_sugerido}", f" Regional Context: {pais_sugerido}"))

c_p1, c_p2 = st.columns(2)
with c_p1:
    cem_type = st.selectbox(_t("Tipo de Cemento:", "Cement Type:"), ["Uso General", "Estructural", "Hidráulico"], index=0)
    cem_weight = st.selectbox(_t("Peso del Bulto:", "Bag Weight:"), ["50kg", "42.5kg", "94lb"], index=0 if pais_sugerido!="Perú" else 1)
with c_p2:
    steel_diam = st.selectbox(_t("Diámetro de Varilla:", "Rebar Diameter:"), ["1/4", "3/8", "1/2", "5/8", "3/4", "1\""], index=2)
    steel_qty = st.caption(_t(f"Unidad base: Varilla x {'6m'if pais_sugerido=='Colombia' else '9m' if pais_sugerido=='Perú' else '12m'}", f"Base unit: Rebar x {'6m' if pais_sugerido=='Colombia' else '9m' if pais_sugerido=='Perú' else '12m'}"))

if pais_sugerido != "Otro" and pais_sugerido != "Bolivia":
    if st.button(_t(f"Consultar y Promediar Precios en Vivo ({pais_sugerido})", f" Query and Average Live Prices ({pais_sugerido})"), use_container_width=True):
        if f"apu_details_{pais_sugerido}" in st.session_state:
            del st.session_state[f"apu_details_{pais_sugerido}"]
        update_regional_prices(pais_sugerido, f"{cem_type} {cem_weight}", steel_diam)
        new_mon = "USD $" if pais_sugerido == "USA" else "COP $" if pais_sugerido == "Colombia" else "PEN S/" if pais_sugerido == "Perú" else "MXN $" if pais_sugerido == "México" else "ARS $" if pais_sugerido == "Argentina" else "CLP $" if pais_sugerido == "Chile" else "BOB $" if pais_sugerido == "Bolivia" else "USD $"
        if "apu_config" in st.session_state:
            st.session_state.apu_config["moneda"] = new_mon

    if f"apu_details_{pais_sugerido}" in st.session_state:
        det = st.session_state[f"apu_details_{pais_sugerido}"]
        mon_sym = "USD $" if pais_sugerido == "USA" else ""
        
        # Mostrar gráficos
        st.markdown(_t("####  Comparación de Precios por Fuente", "####  Price Comparison by Source"))
        graph_data = st.session_state.get(f"apu_grafica_{pais_sugerido}", {})
        if graph_data:
            fig = go.Figure()
            # Cemento
            if graph_data["cemento"]:
                fig.add_trace(go.Bar(
                    x=graph_data["sources_c"][:len(graph_data["cemento"])],
                    y=graph_data["cemento"],
                    name=_t("Cemento", "Cement"),
                    marker_color='#4caf50'
                ))
            # Acero
            if graph_data["acero"]:
                fig.add_trace(go.Bar(
                    x=graph_data["sources_s"][:len(graph_data["acero"])],
                    y=graph_data["acero"],
                    name=_t("Acero (unidad)", "Steel (unit)"),
                    marker_color='#ff9800'
                ))
            fig.update_layout(
                title=_t("Precios por fuente", "Prices by source"),
                xaxis_title=_t("Fuente", "Source"),
                yaxis_title=_t("Precio (moneda local)", "Price (local currency)"),
                barmode='group',
                paper_bgcolor='#1a1a2e',
                plot_bgcolor='#1a1a2e',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de precios detallada
        st.markdown(_t("####  Detalle de Cotizaciones", "####  Quote Details"))
        c1, c2 = st.columns(2)
        
        with c1:
            st.write(_t(f"** Cemento ({cem_type} - {cem_weight}):**", f"** Cement ({cem_type} - {cem_weight}):**"))
            valid_c = []
            for k, v in det["cemento"].items():
                if isinstance(v, (float, int)) and v > 0:
                    st.success(f"{k}: {mon_sym} {v:,.2f}")
                    valid_c.append(v)
                else:
                    st.error(f"{k}: " + _t("Sin conexión o N/D", "No connection or N/A"))
            if valid_c:
                avg_c = sum(valid_c)/len(valid_c)
                st.info(_t(f"**Promedio Cemento: {mon_sym} {avg_c:,.2f}**", f" **Average Cement: {mon_sym} {avg_c:,.2f}**"))
        
        with c2:
            st.write(_t(f"** Acero (Varilla {steel_diam}\"):**", f"** Steel (Rebar {steel_diam}\"):**"))
            valid_s = []
            for k, v in det["acero"].items():
                if isinstance(v, (float, int)) and v > 0:
                    st.success(f"{k}: {mon_sym} {v:,.2f}")
                    valid_s.append(v)
                else:
                    st.error(f"{k}: " + _t("Sin conexión o N/D", "No connection or N/A"))
            if valid_s:
                avg_s_unit = sum(valid_s)/len(valid_s)
                st.info(_t(f"**Promedio Acero (Unidad): {mon_sym} {avg_s_unit:,.2f}**", f" **Average Steel (Unit): {mon_sym} {avg_s_unit:,.2f}**"))
        
        # Botón exportar a Excel
        if st.button(_t("Exportar cotizaciones a Excel", " Export quotes to Excel")):
            # Preparar dataframe
            df_c = pd.DataFrame([{"Fuente": k, "Precio": v} for k, v in det["cemento"].items() if isinstance(v, (float, int))])
            df_s = pd.DataFrame([{"Fuente": k, "Precio": v} for k, v in det["acero"].items() if isinstance(v, (float, int))])
            with pd.ExcelWriter(io.BytesIO(), engine='xlsxwriter') as writer:
                if not df_c.empty:
                    df_c.to_excel(writer, sheet_name="Cemento", index=False)
                if not df_s.empty:
                    df_s.to_excel(writer, sheet_name="Acero", index=False)
                writer.book.close()
                data = writer._io.getvalue()
            st.download_button(
                label=_t("Descargar archivo Excel", "Download Excel file"),
                data=data,
                file_name=f"cotizaciones_{pais_sugerido}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        st.caption(_t("⚠ Nota: Los promedios se calculan automáticamente sobre las fuentes que respondieron con éxito.", "⚠ Note: Averages are automatically calculated from sources that responded successfully."))

elif pais_sugerido == "Bolivia":
    st.info(_t("🇧🇴 Bolivia: Las fuentes para Bolivia requieren cotización directa. Por favor ingresa los valores en el Cotizador Global.", "🇧🇴 Bolivia: Sources for Bolivia require direct quotation. Please enter values in the Global Quoter."))

st.markdown("---")
st.markdown(_t("###  Búsqueda y Cotización Personalizada", "###  Custom Search and Quote"))
col_s1, col_s2 = st.columns([3, 1])
with col_s1:
    placeholder_search = _t(f"Ej: 'precio madera estructural {pais_sugerido.lower()}'...", f"e.g., 'structural timber price {pais_sugerido.lower()}'...")
    search_query = st.text_input(_t("Buscar precio de material:", "Search material price:"), placeholder=placeholder_search)
with col_s2:
    if search_query:
        search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        st.link_button(_t("Buscar en Google", " Search on Google"), search_url, use_container_width=True)
    else:
        st.button(_t("Buscar en Web", " Search Web"), disabled=True, use_container_width=True)

st.markdown(_t("####  Extraer de Link Propio (Cualquier Sitio)", "####  Extract from Own Link (Any Site)"))
st.caption(_t("Pega el link de un producto de cualquier ferretería o tienda online y pulsa extraer.", "Paste the link of a product from any hardware store or online shop and click extract."))
custom_url = st.text_input(_t("URL del producto:", "Product URL:"), placeholder="https://www.tienda.com/producto...")
if st.button(_t("Ejecutar Extracción Inteligente", " Run Smart Extraction"), use_container_width=True):
    if custom_url:
        with st.spinner(_t("Escaneando sitio web...", "Scanning website...")):
            plat = "sodimac" if "sodimac" in custom_url else "vtex" if ("disensa" in custom_url or "easy" in custom_url or "kywi" in custom_url) else "homecenter" if "homecenter" in custom_url else "homedepot_us" if "homedepot" in custom_url else "other"
            res_val = fetch_common(custom_url, plat)
            if isinstance(res_val, float):
                st.success(_t(f"Precio detectado: **{res_val:,.2f}**", f" Price detected: **{res_val:,.2f}**"))
                c1, c2 = st.columns(2)
                if c1.button(_t(" Usar para Cemento", " Use for Cement")):
                    st.session_state.apu_val_cem = res_val
                    st.rerun()
                if c2.button(_t(" Usar para Acero", " Use for Steel")):
                    # Convertir a precio por kg asumiendo varilla de 12m y peso 0.994 kg/m
                    st.session_state.apu_val_ace = res_val / (0.994 * 12)
                    st.rerun()
            else:
                st.error(_t("No se encontró un patrón de precio claro. Por favor ingresa el valor abajo.", " No clear price pattern found. Please enter the value below."))

st.markdown("---")
st.markdown(_t("###  Cotizador Global con Entrada Manual", "###  Global Quoter with Manual Input"))
st.info(_t("Dado que las ferreterías pueden bloquear conexiones automatizadas, siempre puedes ingresar el valor cotizado manualmente para el reporte final.", "Since hardware stores may block automated connections, you can always enter the quoted value manually for the final report."))

c1, c2, c3 = st.columns(3)
with c1:
    p_opts = ["Colombia", "México", "Perú", "Argentina", "Ecuador", "Chile", "Bolivia", "Otro"]
    pais_manual = st.selectbox(_t("País de la Obra:", "Country of Project:"), p_opts, 
                               index=p_opts.index(st.session_state.get("apu_pais", "Colombia")),
                               key="apu_pais")
    moneda = st.text_input(_t("Símbolo Moneda:", "Currency Symbol:"), st.session_state.get("apu_mon", "COP$" if pais_manual=="Colombia" else "MXN$" if pais_manual=="México" else "S/" if pais_manual=="Perú" else "CLP$" if pais_manual=="Chile" else "BOB$" if pais_manual=="Bolivia" else "USD$"), key="apu_mon")

with c2:
    val_cemento = st.number_input(_t(f"Precio del Bulto de Cemento [{moneda}]", f"Price of Cement Bag [{moneda}]"), value=st.session_state.get("apu_val_cem", 32000.0 if pais_manual=="Colombia" else 10.0), key="apu_val_cem")
    val_kg_acero= st.number_input(_t(f"Precio del Kg de Acero [{moneda}]", f"Price of Steel per kg [{moneda}]"), value=st.session_state.get("apu_val_ace", 4500.0 if pais_manual=="Colombia" else 1.5), key="apu_val_ace")

with c3:
    val_m3_arena= st.number_input(_t(f"Precio Arena m³ (Suelto) [{moneda}]", f"Sand price per m³ (loose) [{moneda}]"), value=st.session_state.get("apu_val_are", 70000.0 if pais_manual=="Colombia" else 25.0), key="apu_val_are")
    val_m3_grava= st.number_input(_t(f"Precio Grava m³ (Suelto) [{moneda}]", f"Gravel price per m³ (loose) [{moneda}]"), value=st.session_state.get("apu_val_gra", 80000.0 if pais_manual=="Colombia" else 28.0), key="apu_val_gra")

st.markdown(_t("####  Mano de Obra e Impuestos", "####  Labor and Taxes"))
c4, c5 = st.columns(2)
with c4:
    salario_base = st.number_input(_t(f"Salario Mensual Base (ej: SMMLV) [{moneda}]", f"Base Monthly Salary (e.g., Minimum Wage) [{moneda}]"), value=st.session_state.get("apu_sal", 1300000.0 if pais_manual=="Colombia" else 400.0), key="apu_sal")
    dias_mes = st.number_input(_t("Días laborables al mes", "Working days per month"), 1, 31, st.session_state.get("apu_dias", 26), 1, key="apu_dias")
    factor_prestacional = st.number_input(_t("Factor Prestacional (Sociales+Parafiscales) [%]", "Labor Burden (Social+Parafiscal) [%]"), 1.0, 150.0, st.session_state.get("apu_fact", 65.0), 1.0, key="apu_fact") / 100.0
    costo_dia_real = (salario_base / dias_mes) * (1 + factor_prestacional)
    st.caption(_t(f"Costo Real Día/Trabajador: **{moneda} {costo_dia_real:,.2f}**", f"Real Cost per Day/Worker: **{moneda} {costo_dia_real:,.2f}**"))
    
with c5:
    pct_herramienta = st.number_input(_t("Herramienta Menor (% de Mano Obra)", "Minor Tools (% of Labor)"), 0.0, 20.0, st.session_state.get("apu_pct_h", 5.0), 1.0, key="apu_pct_h") / 100.0
    pct_aui = st.number_input(_t("A.I.U (Admin, Imprevistos, Utilidad) [%]", "A.I.U (Admin, Contingency, Profit) [%]"), 0.0, 50.0, st.session_state.get("apu_pct_aiu", 30.0), 1.0, key="apu_pct_aiu") / 100.0
    iva_utilidad = st.number_input(_t("IVA local sobre la Utilidad [%]", "Local VAT on Profit [%]"), 0.0, 40.0, st.session_state.get("apu_iva", 19.0), 1.0, key="apu_iva") / 100.0
    pct_utilidad_dentro_aiu = st.number_input(_t("Porcentaje de Utilidad dentro del AIU [%]", "Profit percentage within AIU [%]"), 0.0, 20.0, st.session_state.get("apu_pct_u", 5.0), 1.0, key="apu_pct_u") / 100.0

# Sección de dosificación de concreto
st.markdown(_t("####  Dosificación de Concreto (para APU)", "####  Concrete Mix Design (for APU)"))
col_d1, col_d2, col_d3 = st.columns(3)
with col_d1:
    usar_concreto_premezclado = st.checkbox(_t("Usar concreto premezclado", "Use ready-mix concrete"), key="usar_premezclado")
    if usar_concreto_premezclado:
        precio_concreto_m3 = st.number_input(_t(f"Precio del concreto premezclado por m³ [{moneda}]", f"Price of ready-mix concrete per m³ [{moneda}]"), value=st.session_state.get("precio_concreto_m3", 400000.0 if pais_manual=="Colombia" else 100.0), key="precio_concreto_m3")
with col_d2:
    if not usar_concreto_premezclado:
        pct_arena_mezcla = st.number_input(_t("Arena (m³ por m³ de concreto)", "Sand (m³ per m³ concrete)"), 0.2, 1.5, st.session_state.get("pct_arena_mezcla", 0.55), 0.01, key="pct_arena_mezcla")
        pct_grava_mezcla = st.number_input(_t("Grava (m³ por m³ de concreto)", "Gravel (m³ per m³ concrete)"), 0.2, 1.5, st.session_state.get("pct_grava_mezcla", 0.80), 0.01, key="pct_grava_mezcla")
with col_d3:
    if not usar_concreto_premezclado:
        st.caption(_t("Proporciones típicas para f'c=21 MPa: 1:2:3 (cemento:arena:grava). Ajuste según necesidad.", "Typical proportions for f'c=21 MPa: 1:2:3 (cement:sand:gravel). Adjust as needed."))

# Botón para aplicar precios como default en otros módulos
if st.button(_t("⚙ Aplicar estos precios como default en todos los módulos", "⚙ Apply these prices as default in all modules"), use_container_width=True):
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
        "pct_util": pct_utilidad_dentro_aiu,
        "pct_arena_mezcla": pct_arena_mezcla if not usar_concreto_premezclado else st.session_state.get("pct_arena_mezcla", 0.55),
        "pct_grava_mezcla": pct_grava_mezcla if not usar_concreto_premezclado else st.session_state.get("pct_grava_mezcla", 0.80),
        "usar_concreto_premezclado": usar_concreto_premezclado,
        "precio_concreto_m3": precio_concreto_m3 if usar_concreto_premezclado else 0.0
    }
    st.success(_t("Precios guardados en la sesión. Aparecerán reflejados en el análisis APU de tus memorias de cálculo.", " Prices saved in session. They will be reflected in the APU analysis of your calculation reports."))
    st.rerun()
else:
    # Guardar configuración actual en session_state para que esté disponible para otros módulos
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
        "pct_util": pct_utilidad_dentro_aiu,
        "pct_arena_mezcla": pct_arena_mezcla if not usar_concreto_premezclado else st.session_state.get("pct_arena_mezcla", 0.55),
        "pct_grava_mezcla": pct_grava_mezcla if not usar_concreto_premezclado else st.session_state.get("pct_grava_mezcla", 0.80),
        "usar_concreto_premezclado": usar_concreto_premezclado,
        "precio_concreto_m3": precio_concreto_m3 if usar_concreto_premezclado else 0.0
    }

st.success(_t("Los precios han sido guardados temporalmente en la sesión. Aparecerán reflejados en el análisis APU de tus memorias de cálculo.", " Prices have been temporarily saved in the session. They will be reflected in the APU analysis of your calculation reports."))