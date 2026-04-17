"""
normas_referencias.py — StructoPro / Diagrama NSR10
=====================================================
Módulo centralizado de referencias normativas.
Cada entrada REFERENCIAS[norma][modulo] contiene los artículos/capítulos
aplicados en ese módulo, con descripción breve y URL directa al PDF.

Uso en cualquier módulo:
    from normas_referencias import mostrar_referencias_norma
    mostrar_referencias_norma(norma_sel, "columnas_pm")
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# URLs OFICIALES POR NORMA
# ─────────────────────────────────────────────────────────────────────────────
NORMA_DOC_URLS = {
    "NSR-10 (Colombia)": {
        "url":   "https://camacol.co/sites/default/files/descargables/T%C3%ADtulo%20C%20NSR-10%20del%20Decreto%20926%20del%2019032010_0.pdf",
        "label": "NSR-10 Título C — Concreto Estructural (PDF oficial Camacol)",
    },
    "ACI 318-25 (EE.UU.)": {
        "url":   "https://www.concrete.org/store/productdetail.aspx?ItemID=318U25&Language=English",
        "label": "ACI 318-25 — Portal oficial (concrete.org)",
    },
    "ACI 318-19 (EE.UU.)": {
        "url":   "https://www.usb.ac.ir/FileStaff/5526_2020-1-25-11-12-7.pdf",
        "label": "ACI 318-19 — PDF descarga directa",
    },
    "ACI 318-14 (EE.UU.)": {
        "url":   "https://www.concrete.org/store/productdetail.aspx?ItemID=318U14",
        "label": "ACI 318-14 — Portal oficial (concrete.org)",
    },
    "NEC-SE-HM (Ecuador)": {
        "url":   "https://www.habitatyvivienda.gob.ec/wp-content/uploads/2023/01/NEC-SE-HM_2023.pdf",
        "label": "NEC-SE-HM 2023 — Estructuras de Hormigón Armado (MIDUVI)",
    },
    "E.060 (Perú)": {
        "url":   "https://www.sencico.gob.pe/descargar.php?idFile=190",
        "label": "E.060 Concreto Armado — SENCICO PDF oficial",
    },
    "NTC-EM (México)": {
        "url":   "https://transparencia.cdmx.gob.mx/storage/app/uploads/public/5e4/3b6/8ff/5e43b68ffa1c5264001413.pdf",
        "label": "NTC-EM 2017 CDMX — Estructuras de Concreto (PDF oficial)",
    },
    "COVENIN 1753-2006 (Venezuela)": {
        "url":   "https://es.scribd.com/document/338820636/Covenin-1753-2006",
        "label": "COVENIN 1753-2006 — Estructuras de Concreto Armado",
    },
    "NB 1225001-2020 (Bolivia)": {
        "url":   "https://www.ibnorca.org",
        "label": "NB 1225001-2020 — IBNORCA (portal oficial)",
    },
    "CIRSOC 201-2025 (Argentina)": {
        "url":   "https://es.scribd.com/document/cirsoc-201-2025",
        "label": "CIRSOC 201-2025 — Reglamento Argentino de Estructuras de Hormigón",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# REFERENCIAS POR MÓDULO
# Estructura: { norma: { modulo: [ {articulo, tema, descripcion, url} ] } }
# ─────────────────────────────────────────────────────────────────────────────

REFERENCIAS = {}

# ══════════════════════════════════════════════════════════════════════════════
# NSR-10 (Colombia)
# ══════════════════════════════════════════════════════════════════════════════
_base_nsr = "https://camacol.co/sites/default/files/descargables/T%C3%ADtulo%20C%20NSR-10%20del%20Decreto%20926%20del%2019032010_0.pdf"

REFERENCIAS["NSR-10 (Colombia)"] = {

    "columnas_pm": [
        {"articulo": "C.9.3.2.2",  "tema": "φPn,máx (estribos / spiral)",    "descripcion": "φPn ≤ 0.65×0.80×Po (estribos) ó 0.75×0.85×Po (espiral)", "url": _base_nsr},
        {"articulo": "C.10.3",     "tema": "Hipótesis de diseño",             "descripcion": "Compatibilidad de deformaciones, εcu = 0.003, bloque rectangular Whitney", "url": _base_nsr},
        {"articulo": "C.10.9.1",   "tema": "Cuantía longitudinal ρ",          "descripcion": "0.01 ≤ Ast/Ag ≤ 0.08 (DMI) / 0.04 (DMO/DES)", "url": _base_nsr},
        {"articulo": "C.10.10",    "tema": "Esbeltez — magnificación momentos","descripcion": "δns = Cm / (1 - Pu/0.75Pc), EI = 0.4EcIg/(1+βdns)", "url": _base_nsr},
        {"articulo": "C.10.10.6",  "tema": "Factor βdns cargas sostenidas",   "descripcion": "βdns = Msc/M2 para carga de larga duración", "url": _base_nsr},
        {"articulo": "C.21.3.5.4", "tema": "Ash confinamiento sísmico",       "descripcion": "Ash ≥ max[0.3·s·bc·fc/fyt·(Ag/Ach−1), 0.09·s·bc·fc/fyt]", "url": _base_nsr},
        {"articulo": "C.21.3.5.2", "tema": "Zona de confinamiento Lo",        "descripcion": "Lo ≥ max(h, Lcol/6, 45 cm) desde cara de nudo", "url": _base_nsr},
        {"articulo": "C.7.10.5",   "tema": "Espaciado máximo estribos",       "descripcion": "s ≤ min(16db, 48de, menor dimensión sección)", "url": _base_nsr},
        {"articulo": "C.25.5.2",   "tema": "Longitud de desarrollo ld",       "descripcion": "ld = (3fy/40√fc)·(ψt·ψe·ψs·ψg/cb+Ktr)·db", "url": _base_nsr},
        {"articulo": "C.7.7.1",    "tema": "Recubrimiento mínimo columnas",   "descripcion": "Recubrimiento ≥ 40 mm (expuesto) ó 38 mm ambiente normal", "url": _base_nsr},
    ],

    "columnas_circulares": [
        {"articulo": "C.9.3.2.2",  "tema": "φPn,máx espiral",                "descripcion": "φPn ≤ 0.75×0.85×Po para columnas con refuerzo en espiral", "url": _base_nsr},
        {"articulo": "C.10.9.3",   "tema": "Refuerzo en espiral ρs",          "descripcion": "ρs ≥ 0.45(Ag/Ach−1)·fc/fyt", "url": _base_nsr},
        {"articulo": "C.10.9.4",   "tema": "Paso de espiral",                 "descripcion": "25 mm ≤ paso ≤ 75 mm, diámetro espiral ≥ 9.5 mm", "url": _base_nsr},
        {"articulo": "C.10.10",    "tema": "Esbeltez circular",               "descripcion": "r = 0.25D para sección circular", "url": _base_nsr},
        {"articulo": "C.21.3.5.4", "tema": "Ash confinamiento circular",      "descripcion": "Ash aplicado sobre número de ramas = 2 para espiral", "url": _base_nsr},
    ],

    "vigas_losas": [
        {"articulo": "C.9.2",      "tema": "Combinations de carga LRFD",      "descripcion": "U = 1.2D + 1.6L + ... (NSR-10 B.10.2)", "url": _base_nsr},
        {"articulo": "C.9.3.2.1",  "tema": "φ para flexión",                  "descripcion": "φ = 0.90 para elementos controlados por tensión", "url": _base_nsr},
        {"articulo": "C.10.5.1",   "tema": "ρ mínimo vigas",                  "descripcion": "As,min = max(0.25√fc/fy, 1.4/fy)·bw·d", "url": _base_nsr},
        {"articulo": "C.11",       "tema": "Diseño a cortante Vc",            "descripcion": "Vc = 0.17√fc·bw·d, Vs = Av·fy·d/s", "url": _base_nsr},
        {"articulo": "C.11.4.7",   "tema": "Espaciado máximo estribos viga",  "descripcion": "s ≤ d/2 zona general, s ≤ d/4 zona sísmica", "url": _base_nsr},
        {"articulo": "C.9.5",      "tema": "Deflexiones instantáneas",        "descripcion": "Ie = Icr + (Ig−Icr)·(Mcr/Ma)³", "url": _base_nsr},
        {"articulo": "C.9.5.2.5",  "tema": "Deflexiones diferidas λΔ",        "descripcion": "λΔ = ξ/(1+50ρ'), ξ = 2.0 (5 años)", "url": _base_nsr},
        {"articulo": "C.8.10",     "tema": "Losa colaborante / viga T",       "descripcion": "Ancho efectivo de ala: be = bw + min(ln/8, sw/2, hf×8)", "url": _base_nsr},
    ],

    "zapatas": [
        {"articulo": "C.15.2",     "tema": "Tensión neta del suelo",          "descripcion": "q_neta = P/Af ± M·c/I ≤ qa admisible", "url": _base_nsr},
        {"articulo": "C.15.4.2",   "tema": "Cortante por punzonamiento",      "descripcion": "Vc ≤ φ·Vc donde bo = perímetro a d/2 de la columna", "url": _base_nsr},
        {"articulo": "C.15.4.3",   "tema": "Cortante unidireccional",         "descripcion": "Vc = 0.17√fc·b·d", "url": _base_nsr},
        {"articulo": "C.15.5",     "tema": "Flexión en zapata",               "descripcion": "Mu en sección crítica al borde de la columna", "url": _base_nsr},
        {"articulo": "C.15.8",     "tema": "Transferencia de fuerzas",        "descripcion": "Longitud de empotramiento ≥ ld, dowels ≥ 0.5% de Ag", "url": _base_nsr},
        {"articulo": "C.7.7.1",    "tema": "Recubrimiento zapatas",           "descripcion": "Recubrimiento ≥ 75 mm (en contacto con suelo)", "url": _base_nsr},
    ],

    "pilotes": [
        {"articulo": "C.15.8",     "tema": "Transferencia columna–pilote",    "descripcion": "Transferencia mediante dowels y longitud de desarrollo", "url": _base_nsr},
        {"articulo": "C.21.10",    "tema": "Pilotes en zona sísmica",         "descripcion": "Confinamiento mínimo en Los 3 primeros diámetros", "url": _base_nsr},
        {"articulo": "C.7.10.5",   "tema": "Refuerzo transversal pilote",     "descripcion": "Espiral o estribos cerrados, paso ≤ menor dimensión/4", "url": _base_nsr},
        {"articulo": "C.10.9.1",   "tema": "Cuantía longitudinal pilote",     "descripcion": "ρ ≥ 1% Ag para pilotes con cargas sísmicas", "url": _base_nsr},
    ],

    "dados_encepados": [
        {"articulo": "C.15.4.2",   "tema": "Punzonamiento encepado",          "descripcion": "Verificación a 45° desde cara del pilote", "url": _base_nsr},
        {"articulo": "C.12.11",    "tema": "Anclaje longitudinal",            "descripcion": "Longitud de anclaje ≥ ld para barras en tracción", "url": _base_nsr},
        {"articulo": "C.7.7.1",    "tema": "Recubrimiento encepados",         "descripcion": "≥ 75 mm en contacto con suelo", "url": _base_nsr},
    ],

    "calculadora_materiales": [
        {"articulo": "NSR-10 A.2.6","tema": "Resistencia especificada f'c",   "descripcion": "f'c ≥ 17 MPa para elementos estructurales sismo-resistentes", "url": _base_nsr},
        {"articulo": "NSR-10 C.5.4","tema": "Relación agua/cemento",          "descripcion": "a/c ≤ 0.45 para ambiente agresivo, ≤ 0.50 general", "url": _base_nsr},
        {"articulo": "NSR-10 C.3.1","tema": "Materiales — especificaciones",  "descripcion": "Cemento, áridos y agua deben cumplir normas NTC", "url": _base_nsr},
    ],

    "predimensionamiento": [
        {"articulo": "C.9.5.2",    "tema": "Peralte mínimo vigas",            "descripcion": "h_min = L/16 (apoyada simple) a L/21 (doble empotr.)", "url": _base_nsr},
        {"articulo": "C.10.9.1",   "tema": "Cuantía inicial columnas",        "descripcion": "Predim. con ρ = 2-3% → Ag = Pu/(φ·0.80·[0.85fc+ρ(fy-0.85fc)])", "url": _base_nsr},
        {"articulo": "C.15.1",     "tema": "Dimensiones mínimas zapatas",     "descripcion": "Af ≥ (D+L)/qa, esbeltez ≤ 1.5", "url": _base_nsr},
    ],

    "diseno_sismico": [
        {"articulo": "A.2.4",      "tema": "Zonificación sísmica",            "descripcion": "Aa, Av, Ac según municipio y suelo de fundación", "url": "https://www.scg.org.co/Titulo-A-NSR-10-Decreto%20Final-2010-01-13.pdf"},
        {"articulo": "A.3",        "tema": "Espectro de diseño NSR",          "descripcion": "Sa(T) para amortiguamiento 5% y perfil de suelo", "url": "https://www.scg.org.co/Titulo-A-NSR-10-Decreto%20Final-2010-01-13.pdf"},
        {"articulo": "A.6",        "tema": "Sistema estructural y Ro",        "descripcion": "Factor de capacidad de disipación Ro según sistema", "url": "https://www.scg.org.co/Titulo-A-NSR-10-Decreto%20Final-2010-01-13.pdf"},
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# ACI 318-19 (EE.UU.)
# ══════════════════════════════════════════════════════════════════════════════
_base_aci19 = "https://www.usb.ac.ir/FileStaff/5526_2020-1-25-11-12-7.pdf"

REFERENCIAS["ACI 318-19 (EE.UU.)"] = {

    "columnas_pm": [
        {"articulo": "22.4.2",     "tema": "φPn,máx",                        "descripcion": "Pn,max = 0.80[0.85fc(Ag−Ast)+fyAst] (tied), 0.85 (spiral)", "url": _base_aci19},
        {"articulo": "22.2",       "tema": "Hipótesis de resistencia",        "descripcion": "εcu = 0.003, bloque rectangular β1, compatibilidad deform.", "url": _base_aci19},
        {"articulo": "10.6.1",     "tema": "Límites de refuerzo longitudinal","descripcion": "0.01 ≤ Ast/Ag ≤ 0.08", "url": _base_aci19},
        {"articulo": "6.6.4",      "tema": "Magnificación de momentos",       "descripcion": "δns = Cm/(1−Pu/0.75Pc), EI = 0.4EcIg/(1+βdns)", "url": _base_aci19},
        {"articulo": "18.7.5.4",   "tema": "Ash confinamiento SMF",           "descripcion": "Ash ≥ max[0.3·s·bc·fc/fyt·(Ag/Ach−1); 0.09·s·bc·fc/fyt]", "url": _base_aci19},
        {"articulo": "25.5.2",     "tema": "Longitud de desarrollo",          "descripcion": "Misma fórmula con factores ψt, ψe, ψs, ψg, cb, Ktr", "url": _base_aci19},
        {"articulo": "20.6.1.3",   "tema": "Recubrimiento mínimo",           "descripcion": "40 mm columnas expuestas, 38 mm interior", "url": _base_aci19},
    ],

    "columnas_circulares": [
        {"articulo": "22.4.2",     "tema": "φPn,máx espiral",                "descripcion": "Factor 0.85 para columnas en espiral continua", "url": _base_aci19},
        {"articulo": "25.7.3",     "tema": "Refuerzo en espiral",             "descripcion": "ρs ≥ 0.45(Ag/Ach−1)·fc/fyt, paso 25–75 mm", "url": _base_aci19},
        {"articulo": "10.6.1",     "tema": "Cuantía circular",               "descripcion": "1% ≤ ρ ≤ 8% de Ag (hasta 8% en SMF)", "url": _base_aci19},
    ],

    "vigas_losas": [
        {"articulo": "9.3.3",      "tema": "As,mín vigas",                   "descripcion": "As,min = max(0.25√fc/fy, 1.4/fy)·bw·d", "url": _base_aci19},
        {"articulo": "22.5",       "tema": "Cortante Vc",                    "descripcion": "Vc = 0.17λ√fc·bw·d (simplified)", "url": _base_aci19},
        {"articulo": "24.2",       "tema": "Deflexiones",                    "descripcion": "Ie = Icr + (Ig−Icr)·(Mcr/Ma)³ ≤ Ig", "url": _base_aci19},
        {"articulo": "6.3.2",      "tema": "Ancho efectivo viga T",          "descripcion": "be = bw + 2·min(sw/2, 8hf, ln/8)", "url": _base_aci19},
    ],

    "zapatas": [
        {"articulo": "13.3.1",     "tema": "Presión neta de diseño",         "descripcion": "qu = Pu/Af para zapatas centradas bajo carga axial", "url": _base_aci19},
        {"articulo": "22.6",       "tema": "Punzonamiento",                  "descripcion": "bo a d/2 del perímetro de la columna", "url": _base_aci19},
        {"articulo": "13.2.7",     "tema": "Transferencia de fuerzas",       "descripcion": "Dowels ≥ 0.5% Ag, ld ≥ ldcomp", "url": _base_aci19},
    ],

    "pilotes": [
        {"articulo": "18.13",      "tema": "Pilotes en SDC C/D/E/F",         "descripcion": "Confinamiento longitudinal en primera región bajo vitola", "url": _base_aci19},
        {"articulo": "26.6.2",     "tema": "Recubrimiento pilotes",          "descripcion": "≥ 75 mm para pilotes en suelo o agua", "url": _base_aci19},
    ],

    "dados_encepados": [
        {"articulo": "13.3.2",     "tema": "Cortante en encepados",          "descripcion": "Verificación unidireccional y por punzonamiento", "url": _base_aci19},
        {"articulo": "25.4",       "tema": "Anclaje barras",                 "descripcion": "ld tensión / compresión para barras en encepado", "url": _base_aci19},
    ],

    "calculadora_materiales": [
        {"articulo": "26.4.3",     "tema": "Resistencia requerida f'cr",     "descripcion": "f'cr = f'c + 1.34s (historial) ó f'c + 2.33s − 3.45 MPa", "url": _base_aci19},
        {"articulo": "26.4.1",     "tema": "Relación agua/cemento",          "descripcion": "a/c ≤ 0.45 ambiente agresivo, ≤ 0.50 exposición moderada", "url": _base_aci19},
    ],

    "predimensionamiento": [
        {"articulo": "9.3.1",      "tema": "Peralte mínimo vigas",           "descripcion": "h_min según Table 9.3.1.1 (L/16 a L/21)", "url": _base_aci19},
        {"articulo": "10.6.1",     "tema": "Cuantía inicial columnas",       "descripcion": "ρ = 0.01–0.03 para predimensionamiento", "url": _base_aci19},
    ],

    "diseno_sismico": [
        {"articulo": "18.2",       "tema": "Requisitos generales SDC",       "descripcion": "Aplicabilidad de capítulo 18 según SDC (A-F)", "url": _base_aci19},
        {"articulo": "18.7",       "tema": "Columnas SMF",                   "descripcion": "Confinamiento, empalmes, anclaje en zona sísmica especial", "url": _base_aci19},
        {"articulo": "18.6",       "tema": "Vigas SMF",                      "descripcion": "ρmín, estribos cerrados, longitud zona confinada", "url": _base_aci19},
    ],
}

# ACI 318-25 y ACI 318-14 heredan de ACI 318-19 con ajustes menores
REFERENCIAS["ACI 318-25 (EE.UU.)"] = {k: v for k, v in REFERENCIAS["ACI 318-19 (EE.UU.)"].items()}
REFERENCIAS["ACI 318-14 (EE.UU.)"] = {k: v for k, v in REFERENCIAS["ACI 318-19 (EE.UU.)"].items()}

# ══════════════════════════════════════════════════════════════════════════════
# NEC-SE-HM (Ecuador)
# ══════════════════════════════════════════════════════════════════════════════
_base_nec = "https://www.habitatyvivienda.gob.ec/wp-content/uploads/2023/01/NEC-SE-HM_2023.pdf"

REFERENCIAS["NEC-SE-HM (Ecuador)"] = {
    "columnas_pm": [
        {"articulo": "NEC §4.2",   "tema": "Resistencia de diseño φPn",      "descripcion": "φ = 0.65 estribos, 0.75 espiral — igual a ACI 318", "url": _base_nec},
        {"articulo": "NEC §4.4",   "tema": "Cuantía longitudinal",           "descripcion": "0.01 ≤ ρ ≤ 0.06 (zonas de alta sismicidad)", "url": _base_nec},
        {"articulo": "NEC §4.6",   "tema": "Confinamiento sísmico",          "descripcion": "Ash según fórmula ACI 318, Lo ≥ mayor(h, Lcol/6, 50cm)", "url": _base_nec},
        {"articulo": "NEC §7.3",   "tema": "Empalmes y anclaje",             "descripcion": "ld y empalmes según NEC-SE-HM §7 y ACI 25", "url": _base_nec},
    ],
    "vigas_losas": [
        {"articulo": "NEC §3.4",   "tema": "As mínimo vigas",                "descripcion": "As,min = 0.25√fc/fy·bw·d ≥ 1.4/fy·bw·d", "url": _base_nec},
        {"articulo": "NEC §3.6",   "tema": "Cortante Vc",                    "descripcion": "Vc = 0.17√fc·bw·d", "url": _base_nec},
    ],
    "zapatas": [
        {"articulo": "NEC §6.2",   "tema": "Diseño de cimentaciones",        "descripcion": "Capacidad portante, revisión de presiones", "url": _base_nec},
    ],
    "calculadora_materiales": [
        {"articulo": "NEC §1.4",   "tema": "Materiales — resistencias",      "descripcion": "f'c mínimo 21 MPa para elementos estructurales", "url": _base_nec},
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# E.060 (Perú)
# ══════════════════════════════════════════════════════════════════════════════
_base_e60 = "https://www.sencico.gob.pe/descargar.php?idFile=190"

REFERENCIAS["E.060 (Perú)"] = {
    "columnas_pm": [
        {"articulo": "E.060 §10.3", "tema": "Hipótesis de resistencia",      "descripcion": "εcu = 0.003, compatibilidad, bloque rectangular β1", "url": _base_e60},
        {"articulo": "E.060 §21.6", "tema": "Columnas en pórticos especiales","descripcion": "Confinamiento, Ash mínimo, zona Lo", "url": _base_e60},
        {"articulo": "E.060 §10.9", "tema": "Límites de refuerzo",           "descripcion": "1% ≤ ρ ≤ 6% (PE) / 5% (PM)", "url": _base_e60},
    ],
    "vigas_losas": [
        {"articulo": "E.060 §9.5",  "tema": "Deflexiones",                   "descripcion": "Ie = Icr + (Ig−Icr)·(Mcr/Ma)³", "url": _base_e60},
        {"articulo": "E.060 §11",   "tema": "Cortante",                      "descripcion": "Vc = 0.17√fc·bw·d (convertido a kgf/cm²)", "url": _base_e60},
    ],
    "zapatas": [
        {"articulo": "E.060 §15",   "tema": "Zapatas — diseño general",      "descripcion": "Presión neta, cortante, flexión y transferencia de cargas", "url": _base_e60},
    ],
    "calculadora_materiales": [
        {"articulo": "E.060 §5.4",  "tema": "Relación agua/cemento",         "descripcion": "a/c máxima según clase de exposición ambiental", "url": _base_e60},
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# NTC-EM (México)
# ══════════════════════════════════════════════════════════════════════════════
_base_ntc = "https://transparencia.cdmx.gob.mx/storage/app/uploads/public/5e4/3b6/8ff/5e43b68ffa1c5264001413.pdf"

REFERENCIAS["NTC-EM (México)"] = {
    "columnas_pm": [
        {"articulo": "NTC §2.1",    "tema": "Resistencia de diseño",         "descripcion": "FR = 0.70 estribos, 0.80 espiral", "url": _base_ntc},
        {"articulo": "NTC §2.3.2",  "tema": "Columnas — esbeltez",           "descripcion": "Magnificación de momentos por efectos de segundo orden", "url": _base_ntc},
        {"articulo": "NTC §7.3",    "tema": "Detalles sísmicos",             "descripcion": "Confinamiento en zona crítica, Ash mínimo", "url": _base_ntc},
    ],
    "vigas_losas": [
        {"articulo": "NTC §4.1",    "tema": "Flexión — resistencia",         "descripcion": "FR·Mn ≥ Mu con bloque rectangular de compresión", "url": _base_ntc},
        {"articulo": "NTC §4.2",    "tema": "Cortante",                      "descripcion": "FR·Vn = FR·(Vc+Vs) ≥ Vu", "url": _base_ntc},
    ],
    "zapatas": [
        {"articulo": "NTC §8",      "tema": "Cimentaciones",                 "descripcion": "Diseño de zapatas y tensiones admisibles del suelo", "url": _base_ntc},
    ],
    "calculadora_materiales": [
        {"articulo": "NTC §1.3",    "tema": "Materiales",                    "descripcion": "Concreto f'c ≥ 20 MPa para estructuras habitacionales", "url": _base_ntc},
    ],
}

# Normas con menos detalle académico disponible — referencias generales
for norma in ["COVENIN 1753-2006 (Venezuela)", "NB 1225001-2020 (Bolivia)", "CIRSOC 201-2025 (Argentina)"]:
    url = NORMA_DOC_URLS.get(norma, {}).get("url", "#")
    REFERENCIAS[norma] = {
        "columnas_pm": [
            {"articulo": "Cap.10",  "tema": "Diseño de columnas — φPn,máx",  "descripcion": "Factor φ y Pn,max según nivel de ductilidad de la norma", "url": url},
            {"articulo": "Cap.10",  "tema": "Cuantía longitudinal ρ",         "descripcion": "1% ≤ ρ ≤ 6% según nivel de ductilidad", "url": url},
            {"articulo": "Cap.21",  "tema": "Confinamiento sísmico",          "descripcion": "Ash mínimo y zona de confinamiento Lo", "url": url},
        ],
        "columnas_circulares": [
            {"articulo": "Cap.10",  "tema": "Espiral — ρs mínimo",            "descripcion": "ρs ≥ 0.45(Ag/Ach−1)·f'c/fyt", "url": url},
        ],
        "vigas_losas": [
            {"articulo": "Cap.9",   "tema": "Flexión y cortante vigas",       "descripcion": "φMn ≥ Mu, φVn ≥ Vu según la norma local", "url": url},
        ],
        "zapatas": [
            {"articulo": "Cap.15",  "tema": "Zapatas — diseño general",       "descripcion": "Presión neta, punzonamiento y flexión", "url": url},
        ],
        "calculadora_materiales": [
            {"articulo": "Cap.5",   "tema": "Especificación de materiales",   "descripcion": "Resistencia mínima f'c y relación a/c según exposición", "url": url},
        ],
    }

# ─────────────────────────────────────────────────────────────────────────────
# MÓDULOS ADICIONALES — NSR-10
# ─────────────────────────────────────────────────────────────────────────────
_base_nsr_a = "https://www.scg.org.co/Titulo-A-NSR-10-Decreto%20Final-2010-01-13.pdf"
_base_nsr_b = "https://www.invias.gov.co/index.php/archivo-y-biblioteca-e-informacion-tecnica/documento-tecnico/NSR-10-TITULO-B.pdf"

REFERENCIAS["NSR-10 (Colombia)"].update({

    "otras_estructuras": [
        {"articulo": "C.10.9.1",  "tema": "Cuantía longitudinal",         "descripcion": "1% ≤ ρ ≤ 8% para elementos en compresión y flexo-compresión", "url": _base_nsr},
        {"articulo": "C.11",      "tema": "Diseño a cortante general",    "descripcion": "Vc = 0.17√f'c·bw·d, Vs = Av·fy·d/s", "url": _base_nsr},
        {"articulo": "C.14",      "tema": "Muros estructurales",          "descripcion": "Cuantía mínima muros: ρh ≥ 0.0025, ρv ≥ 0.0025", "url": _base_nsr},
    ],

    "apu_mercado": [
        {"articulo": "NSR-10 Gral","tema": "Especificación de materiales","descripcion": "Los materiales deben cumplir los requisitos del Título C NSR-10", "url": _base_nsr},
    ],

    "placa_facil": [
        {"articulo": "C.9.5.3",   "tema": "Espesor mínimo losas",        "descripcion": "h ≥ L/33 (sin vigas), h ≥ L/36 con vigas perimetrales", "url": _base_nsr},
        {"articulo": "C.13",      "tema": "Losas sin vigas (planas)",    "descripcion": "Diseño por coeficientes, franjas de columna y campo", "url": _base_nsr},
        {"articulo": "C.13.6",    "tema": "Método de marcos equivalentes","descripcion": "Distribución momentos en franjas de columna y losa", "url": _base_nsr},
        {"articulo": "C.13.5.3",  "tema": "Refuerzo temperatura y retracción","descripcion": "ρ ≥ 0.0018 para acero fy = 420 MPa", "url": _base_nsr},
    ],

    "kontewall": [
        {"articulo": "H.5",       "tema": "Mampostería estructural confinada","descripcion": "Requisitos de refuerzo vertical y confinantes", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloH.pdf"},
        {"articulo": "H.6",       "tema": "Refuerzo horizontal continuo","descripcion": "Diafragma de amarre y vigas de carga", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloH.pdf"},
    ],

    "muros_contencion": [
        {"articulo": "C.14",      "tema": "Muros de concreto",           "descripcion": "ρ mínimo vertical y horizontal, espesor mínimo", "url": _base_nsr},
        {"articulo": "C.15.2",    "tema": "Presión lateral suelo",       "descripcion": "Empuje activo de tierra Ka, presión hidrostática", "url": _base_nsr},
        {"articulo": "C.15.4",    "tema": "Cortante y flexión en muro",  "descripcion": "Verificación cortante base y momento volcamiento", "url": _base_nsr},
    ],

    "mamposteria": [
        {"articulo": "D.1",       "tema": "Morteros de pega",            "descripcion": "Tipos M, S, N según resistencia a compresión requerida", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloD.pdf"},
        {"articulo": "D.3",       "tema": "Mezclas y dosificación",      "descripcion": "Proporciones en volumen para morteros de mampostería", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloD.pdf"},
        {"articulo": "H.2",       "tema": "Bloque de mampostería",       "descripcion": "Resistencia mínima f'm ≥ 4 MPa en unidades de concreto", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloH.pdf"},
    ],

    "madera": [
        {"articulo": "G.1",       "tema": "Clasificación visual madera", "descripcion": "Selección de especie y clasificación por visual o mecánica", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloG.pdf"},
        {"articulo": "G.3",       "tema": "Flexión — vigas de madera",  "descripcion": "σ_flex = M/S ≤ Fb·CD·CM·Ct·CL·CF", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloG.pdf"},
        {"articulo": "G.5",       "tema": "Columnas de madera",         "descripcion": "Fc* ajustado, Cp factor de columna, λc = esbeltez", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloG.pdf"},
        {"articulo": "G.7",       "tema": "Conexiones",                 "descripcion": "Diseño de uniones con clavos, tornillos y tirafondos", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloG.pdf"},
    ],

    "viento": [
        {"articulo": "B.6",       "tema": "Viento mínimo de diseño",    "descripcion": "V diseño según mapa de velocidades NSR-10 Título B", "url": _base_nsr_b},
        {"articulo": "B.6.3",     "tema": "Presión de viento",          "descripcion": "p = qz·G·Cp, qz = 0.613·Kz·Kzt·Kd·V²", "url": _base_nsr_b},
        {"articulo": "B.6.4",     "tema": "Categoría de exposición",    "descripcion": "A, B, C, D según rugosidad del terreno", "url": _base_nsr_b},
    ],

    "irregularidades": [
        {"articulo": "A.3.3.4",   "tema": "Irregularidades en planta",  "descripcion": "Entrante, diafragma, torsional, esquinas reentrantes", "url": _base_nsr_a},
        {"articulo": "A.3.3.3",   "tema": "Irregularidades en altura",  "descripcion": "Pisos blandos, peso, geometría, resistencia", "url": _base_nsr_a},
        {"articulo": "A.3.3.5",   "tema": "Penalización ΩR",           "descripcion": "Reducción de capacidad por irregularidades combinadas", "url": _base_nsr_a},
    ],

    "estructuras_metalicas": [
        {"articulo": "F.2",       "tema": "Perfiles de acero estructural","descripcion": "ASTM A36, A572 Gr.50, A992 — fy y fu mínimos", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloF.pdf"},
        {"articulo": "F.3",       "tema": "Flexión en perfiles metálicos","descripcion": "φbMp = φb·Zx·fy, clasificación de sección", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloF.pdf"},
        {"articulo": "F.5",       "tema": "Conexiones soldadas",         "descripcion": "Resistencia garganta = 0.60·FEXX·Throat", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloF.pdf"},
        {"articulo": "F.6",       "tema": "Pandeo lateral torsional",   "descripcion": "Lb ≤ Lp = 1.76·ry·√(E/fy)", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloF.pdf"},
    ],

    "resistencia_materiales": [
        {"articulo": "C.8",       "tema": "Análisis de elementos",      "descripcion": "Hipótesis generales: secciones planas permanecen planas", "url": _base_nsr},
        {"articulo": "C.10.3",    "tema": "Resistencia de diseño",      "descripcion": "φ·Mn ≥ Mu, φ·Vn ≥ Vu para todos los estados límite", "url": _base_nsr},
    ],

    "utilidades": [
        {"articulo": "NSR-10 Gral","tema": "Bases de diseño",            "descripcion": "Todos los módulos de utilidades deben cumplir los títulos aplicables", "url": _base_nsr},
    ],

    "analisis_2d": [
        {"articulo": "B.2",       "tema": "Método de análisis elástico","descripcion": "Análisis lineal estático: K·u = F", "url": _base_nsr_b},
        {"articulo": "A.6",       "tema": "Sistemas estructurales",     "descripcion": "Marco de momento (DMO/DES), muros estructurales, dual", "url": _base_nsr_a},
        {"articulo": "A.3.5",     "tema": "Período fundamental T",      "descripcion": "Ta método A = Ct·hn^x, método B análisis modal", "url": _base_nsr_a},
    ],

    "analisis_3d": [
        {"articulo": "B.3",       "tema": "Análisis modal espectral",   "descripcion": "Combinación CQC o SRSS, modos con ≥90% masa participante", "url": _base_nsr_b},
        {"articulo": "A.5.4",     "tema": "Derivas de piso",            "descripcion": "Δa/hsx ≤ 1.0% (uso IV) a 2.0% (uso I) según NSR-10 Tabla A.6-1", "url": _base_nsr_a},
    ],

    "generador_3d": [
        {"articulo": "A.3",       "tema": "Espectro de diseño",         "descripcion": "Espectro elástico con amortiguamiento 5%", "url": _base_nsr_a},
        {"articulo": "C.10",      "tema": "Columnas en edificio 3D",    "descripcion": "Verificar P-Delta y esbeltez en modelos 3D", "url": _base_nsr},
    ],

    "mamposteria_estructural": [
        {"articulo": "H.4",       "tema": "Resistencia mampostería",    "descripcion": "f'm = resistencia prisma, mínimo 4 MPa para unidades", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloH.pdf"},
        {"articulo": "H.11",      "tema": "Diseño sísmico mampostería", "descripcion": "Cuantías mínimas en muros sismo-resistentes", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloH.pdf"},
        {"articulo": "H.6",       "tema": "Refuerzo horizontal",        "descripcion": "Ρh ≥ 0.0007, barras continuas a lo largo de todo el muro", "url": "https://www.minvivienda.gov.co/sites/default/files/reglamentos/NSR10-TituloH.pdf"},
    ],
})

# Propagar módulos nuevos a las otras normas con referencias genéricas
_NUEVOS_MODULOS = [
    "otras_estructuras", "apu_mercado", "placa_facil", "kontewall",
    "muros_contencion", "mamposteria", "madera", "viento",
    "irregularidades", "estructuras_metalicas", "resistencia_materiales",
    "utilidades", "analisis_2d", "analisis_3d", "generador_3d",
    "mamposteria_estructural",
]

_NORMAS_OTRAS = [
    "ACI 318-19 (EE.UU.)", "ACI 318-25 (EE.UU.)", "ACI 318-14 (EE.UU.)",
    "NEC-SE-HM (Ecuador)", "E.060 (Perú)", "NTC-EM (México)",
    "COVENIN 1753-2006 (Venezuela)", "NB 1225001-2020 (Bolivia)",
    "CIRSOC 201-2025 (Argentina)",
]

_NOMBRES_MODULO_DISPLAY = {
    "otras_estructuras":     "Otras Estructuras",
    "apu_mercado":           "APU / Mercado",
    "placa_facil":           "Placa Fácil (Losa sin vigas)",
    "kontewall":             "KonteWall",
    "muros_contencion":      "Muros de Contención",
    "mamposteria":           "Mampostería y Morteros",
    "madera":                "Estructuras de Madera",
    "viento":                "Viento Simplificado",
    "irregularidades":       "Irregularidades Sísmicas",
    "estructuras_metalicas": "Estructuras Metálicas",
    "resistencia_materiales":"Resistencia de Materiales",
    "utilidades":            "Utilidades Comunes",
    "analisis_2d":           "Análisis Estructural 2D",
    "analisis_3d":           "Análisis Estructural 3D",
    "generador_3d":          "Generador Maestro 3D",
    "mamposteria_estructural":"Mampostería Estructural",
}

for _norma in _NORMAS_OTRAS:
    _url = NORMA_DOC_URLS.get(_norma, {}).get("url", "#")
    if _norma not in REFERENCIAS:
        REFERENCIAS[_norma] = {}
    for _mk in _NUEVOS_MODULOS:
        if _mk not in REFERENCIAS[_norma]:
            REFERENCIAS[_norma][_mk] = [
                {"articulo": "General",
                 "tema": f"{_NOMBRES_MODULO_DISPLAY[_mk]} — {_norma}",
                 "descripcion": f"Consulte el capítulo correspondiente de {_norma} para este módulo",
                 "url": _url}
            ]

# ─────────────────────────────────────────────────────────────────────────────
# NOMBRES DISPLAY POR MÓDULO (actualizado con todos los módulos)
# ─────────────────────────────────────────────────────────────────────────────
MODULO_NOMBRES = {
    "columnas_pm":             "📐 Columnas P-M (Rect./Cuad.)",
    "columnas_circulares":     "⭕ Columnas Circulares",
    "vigas_losas":             "🏢 Vigas y Losas",
    "zapatas":                 "🏗️ Zapatas",
    "pilotes":                 "🔩 Pilotes",
    "dados_encepados":         "🧱 Dados y Encepados",
    "calculadora_materiales":  "🧮 Calculadora de Materiales",
    "predimensionamiento":     "📏 Predimensionamiento",
    "diseno_sismico":          "🌍 Diseño Sísmico",
    "otras_estructuras":       "🏛️ Otras Estructuras",
    "apu_mercado":             "💰 APU / Mercado",
    "placa_facil":             "🟦 Placa Fácil",
    "kontewall":               "🧱 KonteWall",
    "muros_contencion":        "🪨 Muros de Contención",
    "mamposteria":             "🧱 Mampostería y Morteros",
    "madera":                  "🏢 Estructuras de Madera",
    "viento":                  "💨 Viento Simplificado",
    "irregularidades":         "📊 Irregularidades Sísmicas",
    "estructuras_metalicas":   "⚙️ Estructuras Metálicas",
    "resistencia_materiales":  "🔬 Resistencia de Materiales",
    "utilidades":              "🛠️ Utilidades Comunes",
    "analisis_2d":             "📐 Análisis 2D",
    "analisis_3d":             "🏗️ Análisis 3D",
    "generador_3d":            "🌐 Generador 3D",
    "mamposteria_estructural": "🧱 Mampostería Estructural",
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL DE RENDERIZADO
# ─────────────────────────────────────────────────────────────────────────────
def mostrar_referencias_norma(norma_sel: str, modulo_key: str):
    """
    Muestra un expander con los artículos normativos aplicados.

    Args:
        norma_sel:  String de la norma seleccionada (key del selectbox)
        modulo_key: Clave del módulo (ej: "columnas_pm", "vigas_losas", etc.)

    Uso en cualquier módulo nuevo:
        from normas_referencias import mostrar_referencias_norma
        mostrar_referencias_norma(norma_sel, "clave_modulo")
    """
    refs      = REFERENCIAS.get(norma_sel, {}).get(modulo_key, [])
    doc       = NORMA_DOC_URLS.get(norma_sel, {})
    nombre_mod = MODULO_NOMBRES.get(modulo_key, modulo_key)
    label     = f"📋 Referencias Normativas — {norma_sel} | {nombre_mod}"

    with st.expander(label, expanded=False):
        if not refs:
            st.info(f"No hay referencias configuradas para **{norma_sel}** en este módulo.")
            return

        tabla = "| Artículo | Tema | Descripción | Enlace |\n"
        tabla += "|----------|------|-------------|--------|\n"
        for r in refs:
            enlace = f"[Ver ↗]({r['url']})" if r.get("url") and r["url"] != "#" else "—"
            desc = r["descripcion"][:80] + "..." if len(r["descripcion"]) > 80 else r["descripcion"]
            tabla += f"| `{r['articulo']}` | **{r['tema']}** | {desc} | {enlace} |\n"

        st.markdown(tabla)

        if doc.get("url"):
            st.markdown(f"🔗 **Documento oficial:** [{doc['label']}]({doc['url']})")

        st.caption(f"Referencias orientativas. Verifique con la versión vigente de {norma_sel}.")
