"""
smlmv_colombia.py
=================
Consulta el Salario Minimo Legal Vigente (SMLMV) de Colombia
desde fuentes oficiales y calcula jornales de construccion
incluyendo el factor prestacional para todos los cargos de obra.

Cargos soportados:
  Obra: ayudante, oficial, maestro, residente_obra
  Profesionales: ingeniero_civil, arquitecto, director_obra

Fuentes (orden de prioridad):
  1. API JSON de datos.gov.co (Banco de la Republica)
  2. Pagina del Ministerio de Trabajo (mintrabajo.gov.co)
  3. Tabla interna historica (fallback garantizado)

Cuadrillas estandar (metodologia IDU/INVIAS):
  - Vaciado de concreto: 1 Maestro + 2 Oficiales + 4 Ayudantes
  - Armado de acero:     1 Oficial + 3 Ayudantes
  - Encofrado:          1 Oficial + 2 Ayudantes
  - Excavacion:         1 Maestro + 6 Ayudantes
"""

import requests
import datetime
import re
import streamlit as st

# ─── FALLBACKS HISTORICOS (actualizados manualmente cada anio) ────────────────
SMLMV_HISTORICO = {
    2022: 1_000_000,
    2023: 1_160_000,
    2024: 1_300_000,
    2025: 1_423_500,   # Decreto 2657 de 2024
    2026: 1_750_905,   # Decreto 2673 de 2025
}

# Factor prestacional construccion Colombia
# Prima(8.33%) + Cesantias(8.33%) + Int.Ces.(1%) + Vacaciones(4.17%)
# + Salud(8.5%) + Pension(12%) + ARL clase V(6.96%) + SENA+ICBF+CCF(9%) = ~58%
# APU civil usa comunmente 52%
FACTOR_PRESTACIONAL_OBRERO      = 1.52  # Obreros (ayudante, oficial, maestro)
FACTOR_PRESTACIONAL_PROFESIONAL = 1.45  # Profesionales (ing., arq.) - ARL clase II

DIAS_LABORABLES_MES = 26  # Promedio descontando domingos y festivos

# ─── ESCALA SALARIAL POR CARGO (multiplos de SMLMV) ─────────────────────────
# Fuente: Camacol, Construdata, mercado 2026
ESCALAS_CARGO = {
    # ── Personal de obra ──────────────────────────────────────────────────────
    "ayudante": {
        "escala": 1.00,
        "factor": FACTOR_PRESTACIONAL_OBRERO,
        "descripcion": "Ayudante de construccion",
        "categoria": "Obra",
        "arl_clase": "V",
    },
    "oficial": {
        "escala": 1.45,
        "factor": FACTOR_PRESTACIONAL_OBRERO,
        "descripcion": "Oficial (estructuras, concreto, acero)",
        "categoria": "Obra",
        "arl_clase": "V",
    },
    "maestro": {
        "escala": 1.90,
        "factor": FACTOR_PRESTACIONAL_OBRERO,
        "descripcion": "Maestro de obra general",
        "categoria": "Obra",
        "arl_clase": "V",
    },
    "residente_obra": {
        "escala": 3.50,
        "factor": FACTOR_PRESTACIONAL_PROFESIONAL,
        "descripcion": "Residente de obra (tecnologo/tecnico)",
        "categoria": "Supervision",
        "arl_clase": "II",
    },
    # ── Personal profesional ──────────────────────────────────────────────────
    "ingeniero_civil": {
        "escala": 6.00,
        "factor": FACTOR_PRESTACIONAL_PROFESIONAL,
        "descripcion": "Ingeniero Civil (director / residente)",
        "categoria": "Profesional",
        "arl_clase": "II",
    },
    "arquitecto": {
        "escala": 5.50,
        "factor": FACTOR_PRESTACIONAL_PROFESIONAL,
        "descripcion": "Arquitecto (diseno / coordinacion)",
        "categoria": "Profesional",
        "arl_clase": "II",
    },
    "director_obra": {
        "escala": 10.00,
        "factor": FACTOR_PRESTACIONAL_PROFESIONAL,
        "descripcion": "Director de Obra (especialista senior)",
        "categoria": "Profesional",
        "arl_clase": "II",
    },
}

# ─── CUADRILLAS ESTANDAR (composicion tipica) ────────────────────────────────
# Fuente: Metodologia IDU Bogota / INVIAS
CUADRILLAS_ESTANDAR = {
    "vaciado_concreto": {
        "nombre": "Vaciado y vibrado de concreto",
        "composicion": {"maestro": 1, "oficial": 2, "ayudante": 4},
        "unidad": "m3",
        "rendimiento_dia": 6.0,   # m3/dia por cuadrilla
        "nota": "Para concreto en sitio con vibrador",
    },
    "armado_acero": {
        "nombre": "Armado y figurado de acero",
        "composicion": {"oficial": 1, "ayudante": 3},
        "unidad": "kg",
        "rendimiento_dia": 250.0,  # kg/dia por cuadrilla
        "nota": "Incluye corte, doblado y amarre",
    },
    "encofrado": {
        "nombre": "Instalacion de encofrado (madera/metalico)",
        "composicion": {"oficial": 1, "ayudante": 2},
        "unidad": "m2",
        "rendimiento_dia": 12.0,  # m2/dia por cuadrilla
        "nota": "Refente Bogota; ajustar por tipo de encofrado",
    },
    "excavacion_manual": {
        "nombre": "Excavacion manual en tierra",
        "composicion": {"maestro": 1, "ayudante": 6},
        "unidad": "m3",
        "rendimiento_dia": 8.0,
        "nota": "Tierra suelta; reducir en arcilla o roca",
    },
    "obra_mediana": {
        "nombre": "Obra mediana (edificio 3-6 pisos)",
        "composicion": {
            "director_obra": 0.1,         # 1 dia de director cada 10 dias
            "ingeniero_civil": 0.25,       # residente permanente 25% del tiempo
            "residente_obra": 1,
            "maestro": 1,
            "oficial": 3,
            "ayudante": 8,
        },
        "unidad": "dia_obra",
        "rendimiento_dia": 1.0,
        "nota": "Composicion tipica para edificacion de mediana escala",
    },
    "obra_grande": {
        "nombre": "Obra grande (edificio 7+ pisos / industrial)",
        "composicion": {
            "director_obra": 0.25,
            "ingeniero_civil": 1,
            "arquitecto": 0.5,
            "residente_obra": 2,
            "maestro": 2,
            "oficial": 6,
            "ayudante": 16,
        },
        "unidad": "dia_obra",
        "rendimiento_dia": 1.0,
        "nota": "Composicion tipica para obra de gran escala",
    },
}


# ─── FUNCIONES DE CONSULTA SMLMV ─────────────────────────────────────────────

def _fetch_smlmv_banrep() -> float | None:
    try:
        anio = datetime.date.today().year
        url = (
            "https://www.datos.gov.co/resource/hczt-hw84.json"
            f"?$where=anio={anio}&$limit=1&$order=anio DESC"
        )
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            datos = resp.json()
            if datos and "valor" in datos[0]:
                return float(datos[0]["valor"])
    except Exception:
        pass
    return None


def _fetch_smlmv_mintrabajo() -> float | None:
    try:
        url = "https://www.mintrabajo.gov.co/empleo-y-pensiones/empleo/salario-minimo"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; StructoPro/1.0)"}
        resp = requests.get(url, timeout=8, headers=headers)
        if resp.status_code == 200:
            matches = re.findall(r'[\$]?\s*(1[\.,]\d{3}[\.,]\d{3})', resp.text)
            if matches:
                raw = matches[0].replace('.', '').replace(',', '')
                val = float(raw)
                if 1_000_000 < val < 5_000_000:
                    return val
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def obtener_smlmv() -> dict:
    """Obtiene el SMLMV actual desde fuentes oficiales con fallback."""
    anio_actual = datetime.date.today().year
    fecha_hoy   = datetime.date.today().isoformat()

    valor = _fetch_smlmv_banrep()
    if valor:
        return {"valor": valor, "anio": anio_actual,
                "fuente": "datos.gov.co / Banco Republica", "fecha_consulta": fecha_hoy}

    valor = _fetch_smlmv_mintrabajo()
    if valor:
        return {"valor": valor, "anio": anio_actual,
                "fuente": "Ministerio de Trabajo", "fecha_consulta": fecha_hoy}

    valor = SMLMV_HISTORICO.get(anio_actual,
            SMLMV_HISTORICO[max(SMLMV_HISTORICO.keys())])
    return {"valor": valor, "anio": anio_actual,
            "fuente": f"Tabla interna StructoPro (Decreto {anio_actual-1})",
            "fecha_consulta": fecha_hoy}


def calcular_jornales_todos() -> dict:
    """
    Calcula el jornal diario de TODOS los cargos con su factor prestacional.

    Returns:
        dict{cargo -> {salario_mensual, jornal_base, jornal_con_prestaciones,
                       descripcion, categoria, escala_smlmv}}
    """
    smlmv_info = obtener_smlmv()
    smlmv = smlmv_info["valor"]

    resultado = {}
    for cargo, cfg in ESCALAS_CARGO.items():
        sal_mes    = smlmv * cfg["escala"]
        j_base     = sal_mes / DIAS_LABORABLES_MES
        j_total    = j_base * cfg["factor"]
        resultado[cargo] = {
            "salario_mensual":         round(sal_mes, 0),
            "jornal_base":             round(j_base, 0),
            "jornal_con_prestaciones": round(j_total, 0),
            "descripcion":             cfg["descripcion"],
            "categoria":               cfg["categoria"],
            "escala_smlmv":            cfg["escala"],
            "factor_prestacional":     cfg["factor"],
        }

    return resultado


def calcular_costo_cuadrilla(
    composicion: dict,
    jornales: dict = None
) -> dict:
    """
    Calcula el costo diario de una cuadrilla personalizada.

    Args:
        composicion: {nombre_cargo: cantidad} ej. {"maestro": 1, "oficial": 2, "ayudante": 4}
        jornales: resultado de calcular_jornales_todos() (si ya fue calculado)

    Returns:
        dict con costo_dia_total, detalle por cargo, y costo por persona
    """
    if jornales is None:
        jornales = calcular_jornales_todos()

    costo_total = 0.0
    detalle = []
    personas_total = 0

    for cargo, cantidad in composicion.items():
        if cargo not in jornales:
            continue
        jornal = jornales[cargo]["jornal_con_prestaciones"]
        subtotal = jornal * cantidad
        costo_total += subtotal
        personas_total += cantidad
        detalle.append({
            "cargo":       cargo,
            "descripcion": jornales[cargo]["descripcion"],
            "cantidad":    cantidad,
            "jornal":      jornal,
            "subtotal":    subtotal,
        })

    return {
        "costo_dia_total":  round(costo_total, 0),
        "personas_total":   personas_total,
        "jornal_promedio":  round(costo_total / personas_total, 0) if personas_total > 0 else 0,
        "detalle":          detalle,
    }


def obtener_jornal_construccion(
    cargo: str = "oficial",
    factor_prestacional: float = None
) -> dict:
    """
    Interfaz de compatibilidad con la version anterior.
    Retorna info de un cargo especifico mas tabla completa.
    """
    jornales = calcular_jornales_todos()
    smlmv_info = obtener_smlmv()

    cargo_sel = cargo.lower() if cargo.lower() in jornales else "oficial"
    j = jornales[cargo_sel]

    return {
        "jornal_base_dia":     j["jornal_base"],
        "jornal_oficial":      j["jornal_con_prestaciones"],
        "smlmv":               smlmv_info["valor"],
        "anio":                smlmv_info["anio"],
        "fuente":              smlmv_info["fuente"],
        "fecha_consulta":      smlmv_info["fecha_consulta"],
        "factor_prestacional": j["factor_prestacional"],
        "cargo":               cargo_sel,
        "cargos":              jornales,          # tabla completa
        "cuadrillas":          CUADRILLAS_ESTANDAR,
    }


if __name__ == "__main__":
    jornales = calcular_jornales_todos()
    smlmv = obtener_smlmv()
    print(f"SMLMV {smlmv['anio']}: ${smlmv['valor']:,.0f}  |  Fuente: {smlmv['fuente']}")
    print()

    categorias = {}
    for cargo, d in jornales.items():
        cat = d["categoria"]
        categorias.setdefault(cat, []).append((cargo, d))

    for cat, items in categorias.items():
        print(f"--- {cat} ---")
        for cargo, d in items:
            print(f"  {d['descripcion']:<45s}  "
                  f"Base: ${d['jornal_base']:>8,.0f}/dia  "
                  f"Con prest.: ${d['jornal_con_prestaciones']:>10,.0f}/dia")
        print()

    print("--- Cuadrilla: Vaciado de concreto ---")
    cq = calcular_costo_cuadrilla(
        CUADRILLAS_ESTANDAR["vaciado_concreto"]["composicion"], jornales)
    for item in cq["detalle"]:
        print(f"  {item['cantidad']} x {item['cargo']:<12s}  ${item['jornal']:,.0f}/dia  = ${item['subtotal']:,.0f}")
    print(f"  TOTAL cuadrilla/dia: ${cq['costo_dia_total']:,.0f}  |  "
          f"Rendimiento: {CUADRILLAS_ESTANDAR['vaciado_concreto']['rendimiento_dia']} m3/dia  |  "
          f"Costo MO/m3: ${cq['costo_dia_total']/CUADRILLAS_ESTANDAR['vaciado_concreto']['rendimiento_dia']:,.0f}")
