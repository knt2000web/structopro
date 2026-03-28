"""
dxf_helpers.py -- Utilidades DXF compartidas para todos los modulos del suite.
Genera planos ejecutables: rotulo, layers, cotas y escala correcta.
Solo importa ezdxf y datetime -- NO importar streamlit aqui.
"""
import datetime as _dt

# ---------------------------------------------------------------------------
# LAYERS ESTANDAR
# ---------------------------------------------------------------------------
BASE_LAYERS = [
    ("CONCRETO",  7),     # blanco/negro  - contorno concreto
    ("ACERO",     1),     # rojo          - acero generico
    ("ACERO_B",   1),     # rojo          - acero Dir. B / T
    ("ACERO_L",   3),     # verde         - acero Dir. L / Long.
    ("ACERO_SUP", 1),     # rojo          - acero superior vigas/losas
    ("ACERO_INF", 3),     # verde         - acero inferior
    ("ESTRIBOS",  4),     # cyan          - estribos / zunchos
    ("VARILLAS",  1),     # rojo          - varillas (uso generico)
    ("EMPALME",   6),     # magenta       - zona de empalme
    ("COTAS",     4),     # cyan          - lineas de cota
    ("TEXTO",     2),     # amarillo      - anotaciones
    ("EJES",      8),     # gris          - ejes y marcas de corte
    ("ROTULO",    6),     # magenta       - cuadro de rotulo
    ("SUELO",     2),     # amarillo      - perfil de suelo
    ("PERFIL",    5),     # azul          - perfiles metalicos
    ("SOLDADURA", 1),     # rojo          - soldaduras
    ("NODO",      4),     # cyan          - nodos analisis
    ("BARRA",     1),     # rojo          - barras analisis
    ("CARGA",     3),     # verde         - cargas y reacciones
    ("HATCH",   254),     # gris oscuro   - rellenos
]

# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------
def dxf_setup(doc_dxf, escala=20):
    """Configura $DIMSCALE, $LTSCALE y $TEXTSIZE. Llamar justo despues de ezdxf.new()."""
    doc_dxf.header["$DIMSCALE"] = float(escala)
    doc_dxf.header["$LTSCALE"]  = 1.0 / escala
    doc_dxf.header["$TEXTSIZE"] = 0.025 * escala
    doc_dxf.header["$DIMTXT"]   = 0.020 * escala
    return escala


def dxf_add_layers(doc_dxf, extra_layers=None):
    """
    Crea layers estandar + layers adicionales opcionales.
    extra_layers: lista de ('NOMBRE', color_aci)
    """
    todos = BASE_LAYERS + (extra_layers or [])
    for nombre, color in todos:
        if nombre not in doc_dxf.layers:
            doc_dxf.layers.add(nombre, color=color)


# ---------------------------------------------------------------------------
# HELPERS DE ALTURA DE TEXTO
# ---------------------------------------------------------------------------
def _th(escala=20):
    """Altura de texto principal en unidades del modelo."""
    return 0.025 * escala

def _th_title(escala=20):
    """Altura de texto titulo."""
    return 0.040 * escala


# ---------------------------------------------------------------------------
# TEXTO
# ---------------------------------------------------------------------------
def dxf_text(msp, x, y, txt, lay, h=None, ha="left", escala=20):
    """Agrega texto al modelspace."""
    _h = h if h is not None else _th(escala)
    HA_MAP = {"left": 0, "center": 4, "right": 2}
    msp.add_text(str(txt), dxfattribs={
        "layer": lay,
        "height": _h,
        "halign": HA_MAP.get(ha, 0),
        "insert": (float(x), float(y)),
    })


# ---------------------------------------------------------------------------
# COTAS
# ---------------------------------------------------------------------------
def dxf_dim_horiz(msp, x1, x2, y_dim, txt, escala=20, lay="COTAS"):
    """Cota horizontal entre x1 y x2 a altura y_dim."""
    TH = _th(escala)
    arrow = TH * 0.6
    msp.add_line((x1, y_dim), (x2, y_dim), dxfattribs={"layer": lay})
    for xi in (x1, x2):
        msp.add_line((xi, y_dim - arrow), (xi, y_dim + arrow), dxfattribs={"layer": lay})
    msp.add_line((x1, y_dim), (x1, y_dim - TH * 2), dxfattribs={"layer": lay, "color": 8})
    msp.add_line((x2, y_dim), (x2, y_dim - TH * 2), dxfattribs={"layer": lay, "color": 8})
    dxf_text(msp, (x1 + x2) / 2, y_dim + TH * 0.4, txt, lay, TH * 0.9, "center", escala)


def dxf_dim_vert(msp, x_dim, y1, y2, txt, escala=20, lay="COTAS"):
    """Cota vertical entre y1 e y2 a posicion x_dim."""
    TH = _th(escala)
    arrow = TH * 0.6
    msp.add_line((x_dim, y1), (x_dim, y2), dxfattribs={"layer": lay})
    for yi in (y1, y2):
        msp.add_line((x_dim - arrow, yi), (x_dim + arrow, yi), dxfattribs={"layer": lay})
    msp.add_line((x_dim, y1), (x_dim + TH * 2, y1), dxfattribs={"layer": lay, "color": 8})
    msp.add_line((x_dim, y2), (x_dim + TH * 2, y2), dxfattribs={"layer": lay, "color": 8})
    dxf_text(msp, x_dim - TH * 0.4, (y1 + y2) / 2, txt, lay, TH * 0.9, "right", escala)


# ---------------------------------------------------------------------------
# ROTULO
# ---------------------------------------------------------------------------
def dxf_rotulo(msp, campos, ox, oy, rot_w=180, rot_h=60, escala=20):
    """
    Dibuja el cuadro de rotulo estandar.

    campos: dict con claves PROYECTO, EMPRESA, DISENO, NORMA, ESCALA, FECHA, PLANO, REVISION
    ox, oy: origen (esquina inferior izquierda)
    rot_w, rot_h: ancho y alto en unidades del modelo
    """
    TH  = _th(escala)
    lay = "ROTULO"
    filas = [
        ("PROYECTO",  campos.get("PROYECTO",  "Sin Nombre")),
        ("EMPRESA",   campos.get("EMPRESA",   "Konte Ingenieria")),
        ("DISENO",    campos.get("DISENO",    "StructuroPro")),
        ("NORMA",     campos.get("NORMA",     "NSR-10 / ACI 318")),
        ("ESCALA",    campos.get("ESCALA",    f"1:{escala}")),
        ("FECHA",     campos.get("FECHA",     _dt.date.today().strftime("%d/%m/%Y"))),
        ("PLANO N.",  campos.get("PLANO",     "PLN-001")),
        ("REVISION",  campos.get("REVISION",  "R0")),
    ]
    n = len(filas)
    row_h = rot_h / n
    sep_x = rot_w * 0.30

    # Borde exterior doble
    for delta in (0, -2):
        msp.add_lwpolyline(
            [(ox + delta, oy + delta),
             (ox + rot_w - delta, oy + delta),
             (ox + rot_w - delta, oy + rot_h - delta),
             (ox + delta, oy + rot_h - delta)],
            close=True, dxfattribs={"layer": lay})

    # Separador etiqueta / valor
    msp.add_line((ox + sep_x, oy), (ox + sep_x, oy + rot_h), dxfattribs={"layer": lay})

    for i, (etiq, valor) in enumerate(filas):
        y_row = oy + rot_h - (i + 1) * row_h
        if i > 0:
            msp.add_line((ox, y_row + row_h), (ox + rot_w, y_row + row_h),
                         dxfattribs={"layer": lay})
        dxf_text(msp, ox + 2,        y_row + row_h * 0.25, etiq,  lay, TH * 0.75, "left", escala)
        dxf_text(msp, ox + sep_x + 2, y_row + row_h * 0.25, valor, lay, TH,       "left", escala)


# ---------------------------------------------------------------------------
# LEYENDA
# ---------------------------------------------------------------------------
def dxf_leyenda(msp, ley_x, ley_y, filas, escala=20):
    """
    Dibuja leyenda de layers.
    filas: [(lay_name, descripcion), ...]
    """
    TH  = _th(escala)
    TH2 = _th_title(escala)
    dxf_text(msp, ley_x, ley_y + TH2 * 1.5, "LEYENDA:", "TEXTO", TH2, "left", escala)
    for i, (lay_name, desc) in enumerate(filas):
        yi = ley_y - i * TH * 2.5
        msp.add_line((ley_x, yi + TH * 0.5), (ley_x + TH * 4, yi + TH * 0.5),
                     dxfattribs={"layer": lay_name})
        dxf_text(msp, ley_x + TH * 5, yi, desc, "TEXTO", TH, "left", escala)


# ---------------------------------------------------------------------------
# FACTORY DE CAMPOS DEL ROTULO
# ---------------------------------------------------------------------------
def dxf_rotulo_campos(elemento, norma, plano_num="001"):
    """
    Genera dict de campos con valores por defecto para dxf_rotulo().
    elemento: nombre del elemento disenado (ej. 'Columna 30x40cm')
    norma:    norma activa (ej. 'NSR-10 (Colombia)')
    """
    abrevs = {
        "columna": "COL", "zapata": "ZAP", "muro": "MUR",
        "viga": "VIG",    "losa":   "LOS", "albanil": "ALB",
        "predimen": "PRE","seccion":"SEC", "madera": "MAD",
        "espectro": "ESP","perfil": "PER", "analisis":"ANL",
        "corbel":   "COR",
    }
    abrev = "PLN"
    for key, ab in abrevs.items():
        if key in elemento.lower():
            abrev = ab
            break
    return {
        "PROYECTO":  elemento,
        "EMPRESA":   "Konte Ingenieria",
        "DISENO":    "StructuroPro",
        "NORMA":     norma,
        "ESCALA":    "1:20",
        "FECHA":     _dt.date.today().strftime("%d/%m/%Y"),
        "PLANO":     f"{abrev}-{plano_num}",
        "REVISION":  "R0",
    }
