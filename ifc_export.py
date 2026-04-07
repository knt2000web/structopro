"""
ifc_export.py — Módulo de exportación IFC (BIM) para el Suite de Diseño NSR-10
Genera archivos IFC4 válidos con geometría extruida, barras de refuerzo
como IfcReinforcingBar y propiedades de diseño estructural.

Compatible con: FreeCAD, Revit, Navisworks, BIMcollab Zoom, Tekla.

Uso:
    from ifc_export import ifc_viga_rectangular, ifc_viga_t, ifc_losa, ifc_columna

Cada función retorna un BytesIO listo para st.download_button.
"""

import io
import math
import tempfile
import os
from datetime import datetime

# ─── Import condicional: ifcopenshell puede no estar instalado ─────────────────
try:
    import ifcopenshell
    import ifcopenshell.guid
    IFC_DISPONIBLE = True
except ImportError:
    IFC_DISPONIBLE = False


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════════════════

def _nueva_jerarquia(ifc, nombre_proyecto: str):
    """Crea Proyecto > Sitio > Edificio > Planta y el contexto geométrico."""
    proyecto = ifc.createIfcProject(
        ifcopenshell.guid.new(), None, nombre_proyecto,
        None, None, None, None, None, None
    )
    # Unidades del modelo: milímetros (estándar IFC)
    unit_mm = ifc.createIfcSIUnit(None, "LENGTHUNIT", "MILLI", "METRE")
    unit_m2 = ifc.createIfcSIUnit(None, "AREAUNIT", None, "SQUARE_METRE")
    unit_m3 = ifc.createIfcSIUnit(None, "VOLUMEUNIT", None, "CUBIC_METRE")
    units = ifc.createIfcUnitAssignment([unit_mm, unit_m2, unit_m3])
    proyecto.UnitsInContext = units

    sitio     = ifc.createIfcSite(ifcopenshell.guid.new(), None, "Sitio")
    edificio  = ifc.createIfcBuilding(ifcopenshell.guid.new(), None, "Edificio")
    planta    = ifc.createIfcBuildingStorey(ifcopenshell.guid.new(), None, "Nivel 0")

    # Relaciones de agregación
    ifc.createIfcRelAggregates(
        ifcopenshell.guid.new(), None, None, None, proyecto, [sitio])
    ifc.createIfcRelAggregates(
        ifcopenshell.guid.new(), None, None, None, sitio, [edificio])
    ifc.createIfcRelAggregates(
        ifcopenshell.guid.new(), None, None, None, edificio, [planta])

    # Contexto geométrico 3D
    origen = ifc.createIfcCartesianPoint((0., 0., 0.))
    eje_z  = ifc.createIfcDirection((0., 0., 1.))
    eje_x  = ifc.createIfcDirection((1., 0., 0.))
    placement3d = ifc.createIfcAxis2Placement3D(origen, eje_z, eje_x)
    ctx = ifc.createIfcGeometricRepresentationContext(
        None, "Model", 3, 1e-5, placement3d, None)
    sub_ctx = ifc.createIfcGeometricRepresentationSubContext(
        "Body", "Model", None, None, None, None, ctx, None, "MODEL_VIEW", None)

    return planta, sub_ctx


def _punto(ifc, x, y, z=0.):
    return ifc.createIfcCartesianPoint((float(x), float(y), float(z)))


def _placement_local(ifc, x=0., y=0., z=0., eje_x=None, eje_z=None):
    """Genera un IfcLocalPlacement en la posición (x,y,z)."""
    ejeZ = ifc.createIfcDirection(eje_z if eje_z else (0., 0., 1.))
    ejeX = ifc.createIfcDirection(eje_x if eje_x else (1., 0., 0.))
    ax   = ifc.createIfcAxis2Placement3D(_punto(ifc, x, y, z), ejeZ, ejeX)
    return ifc.createIfcLocalPlacement(None, ax)


def _pset_diseno(ifc, elemento, propiedades: dict, nombre: str = "Pset_StructuralDesign"):
    """Crea un PropertySet y lo asocia al elemento IFC."""
    props = []
    for clave, valor in propiedades.items():
        if isinstance(valor, (int, float)):
            val_ifc = ifc.createIfcReal(float(valor))
        else:
            val_ifc = ifc.createIfcLabel(str(valor))
        props.append(ifc.createIfcPropertySingleValue(clave, None, val_ifc, None))

    pset = ifc.createIfcPropertySet(
        ifcopenshell.guid.new(), None, nombre, None, props)
    ifc.createIfcRelDefinesByProperties(
        ifcopenshell.guid.new(), None, None, None, [elemento], pset)


def _material(ifc, elemento, nombre_material: str):
    mat = ifc.createIfcMaterial(nombre_material)
    ifc.createIfcRelAssociatesMaterial(
        ifcopenshell.guid.new(), None, None, None, [elemento], mat)


def _contener_en_planta(ifc, planta, elementos: list):
    ifc.createIfcRelContainedInSpatialStructure(
        ifcopenshell.guid.new(), None, None, None, elementos, planta)


def _guardar_a_bytesio(ifc) -> io.BytesIO:
    """Escribe el modelo IFC a un archivo temporal y lo lee como BytesIO."""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        ifc.write(tmp_path)
        with open(tmp_path, "rb") as f:
            buf = io.BytesIO(f.read())
        buf.seek(0)
        return buf
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# 1. VIGA RECTANGULAR
# ══════════════════════════════════════════════════════════════════════════════

def ifc_viga_rectangular(
    b_cm: float, h_cm: float, L_m: float,
    fc: float, fy: float,
    n_bars: int, bar_name: str, As_cm2: float,
    db_mm: float,        # diámetro nominal de la barra en mm
    d_eff_cm: float,     # peralte efectivo real
    recub_cm: float,     # recubrimiento libre lateral
    Mu_kNm: float = 0., phi_Mn_kNm: float = 0.,
    dos_filas: bool = False,
    n_f1: int = 0, n_f2: int = 0,
    sep_filas_mm: float = 25.,
    norma: str = "NSR-10",
    nombre_proyecto: str = "Proyecto NSR-10",
) -> io.BytesIO:
    """Exporta una Viga Rectangular con refuerzo longitudinal como IFC4."""
    if not IFC_DISPONIBLE:
        raise ImportError("ifcopenshell no está instalado. Ejecuta: pip install ifcopenshell")

    ifc = ifcopenshell.file(schema="IFC4")
    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)

    # Dimensiones en mm
    b = b_cm * 10.
    h = h_cm * 10.
    L = L_m * 1000.
    rec = recub_cm * 10.         # mm
    db = db_mm                    # mm
    d_eff = d_eff_cm * 10.       # mm

    # ─── Cuerpo de la viga ────────────────────────────────────────────────────
    axis2d = ifc.createIfcAxis2Placement2D(
        ifc.createIfcCartesianPoint((0., 0.)), None)
    perfil = ifc.createIfcRectangleProfileDef("AREA", "SeccionViga", axis2d, b, h)
    dir_extr = ifc.createIfcDirection((0., 0., 1.))
    solido = ifc.createIfcExtrudedAreaSolid(perfil, None, dir_extr, L)

    rep_cuerpo = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solido])
    prod_rep = ifc.createIfcProductDefinitionShape(None, None, [rep_cuerpo])
    place_viga = _placement_local(ifc, 0., 0., 0.)

    viga = ifc.createIfcBeam(
        ifcopenshell.guid.new(), None,
        f"Viga {b_cm:.0f}×{h_cm:.0f} cm",
        f"b={b_cm:.0f}cm h={h_cm:.0f}cm L={L_m:.2f}m",
        None, place_viga, prod_rep, None
    )
    _material(ifc, viga, f"Concreto f'c={fc:.0f}MPa")
    _pset_diseno(ifc, viga, {
        "fc_MPa": fc, "fy_MPa": fy,
        "b_cm": b_cm, "h_cm": h_cm, "L_m": L_m,
        "d_efectivo_cm": d_eff_cm,
        "As_cm2": As_cm2,
        "Barras": f"{n_bars} barras {bar_name}",
        "Mu_kNm": Mu_kNm, "φMn_kNm": phi_Mn_kNm,
        "Norma": norma,
        "FechaDiseno": datetime.now().strftime("%Y-%m-%d"),
    })

    # ─── Barras de refuerzo ────────────────────────────────────────────────────
    rebars = []
    n1 = n_f1 if dos_filas else n_bars
    n2 = n_f2 if dos_filas else 0

    # Posiciones X de las barras en fila 1 (eje Y = rec + db/2 desde abajo)
    y_f1 = rec + db / 2.
    if n1 > 1:
        xs_f1 = [rec + db / 2. + i * (b - 2 * rec - db) / (n1 - 1) for i in range(n1)]
    else:
        xs_f1 = [b / 2.]

    # Posiciones X de las barras en fila 2
    y_f2 = y_f1 + db + sep_filas_mm
    if n2 > 1:
        xs_f2 = [rec + db / 2. + i * (b - 2 * rec - db) / (n2 - 1) for i in range(n2)]
    elif n2 == 1:
        xs_f2 = [b / 2.]
    else:
        xs_f2 = []

    todas_barras = [(x, y_f1) for x in xs_f1] + [(x, y_f2) for x in xs_f2]

    for idx, (xb, yb) in enumerate(todas_barras):
        # Perfil circular (sección transversal de la barra)
        ax2d_r = ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint((0., 0.)), None)
        perf_r = ifc.createIfcCircleProfileDef("AREA", None, ax2d_r, db / 2.)

        # La barra corre a lo largo del eje Z de la viga (local = eje longitudinal)
        # Placement de la barra en el espacio de la viga
        origin_r = _punto(ifc, xb - b / 2., yb - h / 2., 0.)
        ax3d_r = ifc.createIfcAxis2Placement3D(
            origin_r, ifc.createIfcDirection((0., 0., 1.)),
            ifc.createIfcDirection((1., 0., 0.)))
        solid_r = ifc.createIfcExtrudedAreaSolid(
            perf_r, ax3d_r, ifc.createIfcDirection((0., 0., 1.)), L)

        rep_r = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid_r])
        prod_r = ifc.createIfcProductDefinitionShape(None, None, [rep_r])
        place_r = _placement_local(ifc, 0., 0., 0.)

        rebar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None,
            f"Bar_{idx+1}",
            f"Ø{db:.0f}mm | {bar_name}",
            None, place_r, prod_r, None,
            db / 2.,      # NominalDiameter
            math.pi * (db / 2.) ** 2 / 100.,  # CrossSectionArea en cm²
            L,            # BarLength
            "MAIN",       # BarRole
            None          # BarSurface
        )
        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")
        rebars.append(rebar)

    # Agrupar barra dentro de la viga (IfcRelAggregates)
    if rebars:
        ifc.createIfcRelAggregates(
            ifcopenshell.guid.new(), None, None, None, viga, rebars)

    _contener_en_planta(ifc, planta, [viga] + rebars)
    return _guardar_a_bytesio(ifc)


# ══════════════════════════════════════════════════════════════════════════════
# 2. VIGA T
# ══════════════════════════════════════════════════════════════════════════════

def ifc_viga_t(
    bf_cm: float, bw_cm: float, hf_cm: float, h_cm: float, L_m: float,
    fc: float, fy: float,
    n_bars: int, bar_name: str, db_mm: float,
    As_cm2: float, d_cm: float, recub_cm: float,
    Mu: float = 0., phi_Mn: float = 0.,
    norma: str = "NSR-10",
    nombre_proyecto: str = "Proyecto NSR-10",
) -> io.BytesIO:
    """Exporta una Viga T con refuerzo longitudinal como IFC4."""
    if not IFC_DISPONIBLE:
        raise ImportError("ifcopenshell no está instalado.")

    ifc = ifcopenshell.file(schema="IFC4")
    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)

    bf = bf_cm * 10.; bw = bw_cm * 10.
    hf = hf_cm * 10.; h  = h_cm  * 10.
    L  = L_m * 1000.;  db = db_mm
    rec = recub_cm * 10.

    # ─── Perfil T mediante IfcArbitraryClosedProfileDef ─────────────────────
    # Coordenadas del polígono T (sentido antihorario, origen en centro del alma base)
    # El alma va de x = -bw/2 a +bw/2
    # El ala va de y = h - hf a h, y de x = -bf/2 a +bf/2
    pts_poligono_t = [
        (-bw/2., 0.),               # 1. Base izq
        (bw/2.,  0.),               # 2. Base der
        (bw/2.,  h - hf),           # 3. Cuello der
        (bf/2.,  h - hf),           # 4. Ala inf der
        (bf/2.,  h),                # 5. Ala sup der
        (-bf/2., h),                # 6. Ala sup izq
        (-bf/2., h - hf),           # 7. Ala inf izq
        (-bw/2., h - hf)            # 8. Cuello izq
    ]
    pnts_ifc = [ifc.createIfcCartesianPoint(p) for p in pts_poligono_t]
    # Cerrar el polígono iterando el primero al final
    polyline = ifc.createIfcPolyline(pnts_ifc + [pnts_ifc[0]])
    perfil_t = ifc.createIfcArbitraryClosedProfileDef("AREA", "SeccionVigaT", polyline)

    dir_extr = ifc.createIfcDirection((0., 0., 1.))
    solido = ifc.createIfcExtrudedAreaSolid(perfil_t, None, dir_extr, L)
    rep_cuerpo = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solido])
    prod_rep = ifc.createIfcProductDefinitionShape(None, None, [rep_cuerpo])
    place_viga = _placement_local(ifc, 0., 0., 0.)

    viga = ifc.createIfcBeam(
        ifcopenshell.guid.new(), None,
        f"Viga T bf={bf_cm:.0f}×bw={bw_cm:.0f} h={h_cm:.0f}cm",
        f"bf={bf_cm:.0f} bw={bw_cm:.0f} hf={hf_cm:.0f} h={h_cm:.0f} L={L_m:.2f}m",
        None, place_viga, prod_rep, None
    )
    _material(ifc, viga, f"Concreto f'c={fc:.0f}MPa")
    _pset_diseno(ifc, viga, {
        "fc_MPa": fc, "fy_MPa": fy,
        "bf_cm": bf_cm, "bw_cm": bw_cm, "hf_cm": hf_cm, "h_cm": h_cm, "L_m": L_m,
        "d_cm": d_cm, "As_cm2": As_cm2,
        "Barras": f"{n_bars} barras {bar_name}",
        "Mu": Mu, "φMn": phi_Mn,
        "Norma": norma,
        "FechaDiseno": datetime.now().strftime("%Y-%m-%d"),
    })

    # ─── Barras de refuerzo (en alma, zona inferior = tracción) ──────────────
    rebars = []
    y_bar = -(h / 2.) + rec + db / 2.
    if n_bars > 1:
        xs = [-(bw / 2.) + rec + db / 2. + i * (bw - 2 * rec - db) / (n_bars - 1)
              for i in range(n_bars)]
    else:
        xs = [0.]

    for idx, xb in enumerate(xs):
        ax2d_r = ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint((0., 0.)), None)
        perf_r = ifc.createIfcCircleProfileDef("AREA", None, ax2d_r, db / 2.)
        origin_r = _punto(ifc, xb, y_bar, 0.)
        ax3d_r = ifc.createIfcAxis2Placement3D(
            origin_r, ifc.createIfcDirection((0., 0., 1.)),
            ifc.createIfcDirection((1., 0., 0.)))
        solid_r = ifc.createIfcExtrudedAreaSolid(
            perf_r, ax3d_r, ifc.createIfcDirection((0., 0., 1.)), L)
        rep_r = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid_r])
        prod_r = ifc.createIfcProductDefinitionShape(None, None, [rep_r])
        place_r = _placement_local(ifc, 0., 0., 0.)

        rebar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, f"Bar_{idx+1}",
            f"Ø{db:.0f}mm | {bar_name}", None, place_r, prod_r, None,
            db / 2., math.pi * (db / 2.) ** 2 / 100., L, "MAIN", None)
        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")
        rebars.append(rebar)

    if rebars:
        ifc.createIfcRelAggregates(
            ifcopenshell.guid.new(), None, None, None, viga, rebars)

    _contener_en_planta(ifc, planta, [viga] + rebars)
    return _guardar_a_bytesio(ifc)


# ══════════════════════════════════════════════════════════════════════════════
# 3. LOSA EN UNA DIRECCIÓN
# ══════════════════════════════════════════════════════════════════════════════

def ifc_losa(
    h_cm: float, ln_m: float, ancho_m: float = 1.0,
    fc: float = 21., fy: float = 420.,
    bar_name: str = "Ø12mm", db_mm: float = 12., As_cm2m: float = 0.,
    s_cm: float = 20., recub_cm: float = 2.5,
    norma: str = "NSR-10",
    nombre_proyecto: str = "Proyecto NSR-10",
) -> io.BytesIO:
    """Exporta una franja de losa en una dirección como IfcSlab con barras."""
    if not IFC_DISPONIBLE:
        raise ImportError("ifcopenshell no está instalado.")

    ifc = ifcopenshell.file(schema="IFC4")
    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)

    h = h_cm * 10.
    L = ln_m * 1000.
    W = ancho_m * 1000.   # franja de análisis en mm
    rec = recub_cm * 10.
    db  = db_mm
    sep = s_cm * 10.      # separación entre barras en mm

    # ─── Sólido de la losa ────────────────────────────────────────────────────
    axis2d = ifc.createIfcAxis2Placement2D(
        ifc.createIfcCartesianPoint((0., 0.)), None)
    perfil = ifc.createIfcRectangleProfileDef("AREA", "SeccionLosa", axis2d, W, h)
    dir_extr = ifc.createIfcDirection((0., 0., 1.))
    solido = ifc.createIfcExtrudedAreaSolid(perfil, None, dir_extr, L)
    rep = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solido])
    prod_rep = ifc.createIfcProductDefinitionShape(None, None, [rep])
    place_losa = _placement_local(ifc, 0., 0., 0.)

    losa = ifc.createIfcSlab(
        ifcopenshell.guid.new(), None,
        f"Losa h={h_cm:.0f}cm ln={ln_m:.2f}m",
        f"h={h_cm:.0f}cm As={As_cm2m:.2f}cm²/m s={s_cm:.0f}cm {bar_name}",
        None, place_losa, prod_rep, None, "FLOOR"
    )
    _material(ifc, losa, f"Concreto f'c={fc:.0f}MPa")
    _pset_diseno(ifc, losa, {
        "fc_MPa": fc, "fy_MPa": fy,
        "h_cm": h_cm, "ln_m": ln_m,
        "As_cm2_por_m": As_cm2m,
        "Separacion_cm": s_cm,
        "Bar_name": bar_name,
        "Norma": norma,
        "FechaDiseno": datetime.now().strftime("%Y-%m-%d"),
    })

    # ─── Barras de refuerzo principal (a lo largo de la luz) ─────────────────
    rebars = []
    n_barras_franja = max(1, int(W / sep))
    y_bar = -(h / 2.) + rec + db / 2.

    for i in range(n_barras_franja):
        xb = -(W / 2.) + rec + db / 2. + i * sep
        if xb > (W / 2.) - rec - db / 2.:
            break
        ax2d_r = ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint((0., 0.)), None)
        perf_r = ifc.createIfcCircleProfileDef("AREA", None, ax2d_r, db / 2.)
        origin_r = _punto(ifc, xb, y_bar, 0.)
        ax3d_r = ifc.createIfcAxis2Placement3D(
            origin_r, ifc.createIfcDirection((0., 0., 1.)),
            ifc.createIfcDirection((1., 0., 0.)))
        solid_r = ifc.createIfcExtrudedAreaSolid(
            perf_r, ax3d_r, ifc.createIfcDirection((0., 0., 1.)), L)
        rep_r = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid_r])
        prod_r = ifc.createIfcProductDefinitionShape(None, None, [rep_r])
        place_r = _placement_local(ifc, 0., 0., 0.)

        rebar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, f"Bar_Princ_{i+1}",
            f"Ø{db:.0f}mm s={s_cm:.0f}cm", None, place_r, prod_r, None,
            db / 2., math.pi * (db / 2.) ** 2 / 100., L, "MAIN", None)
        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")
        rebars.append(rebar)

    if rebars:
        ifc.createIfcRelAggregates(
            ifcopenshell.guid.new(), None, None, None, losa, rebars)

    _contener_en_planta(ifc, planta, [losa] + rebars)
    return _guardar_a_bytesio(ifc)


# ══════════════════════════════════════════════════════════════════════════════
# 4. COLUMNA RECTANGULAR
# ══════════════════════════════════════════════════════════════════════════════

def ifc_columna(
    b_cm: float, h_cm: float, L_m: float,
    fc: float, fy: float,
    n_bars: int, bar_name: str, db_mm: float, db_est_mm: float,
    As_total_cm2: float, recub_cm: float,
    Pu_kN: float = 0., Mu_kNm: float = 0., phi_Pn_kN: float = 0.,
    norma: str = "NSR-10",
    nombre_proyecto: str = "Proyecto NSR-10",
) -> io.BytesIO:
    """Exporta una Columna Rectangular como IfcColumn con barras longitudinales."""
    if not IFC_DISPONIBLE:
        raise ImportError("ifcopenshell no está instalado.")

    ifc = ifcopenshell.file(schema="IFC4")
    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)

    b = b_cm * 10.;  h = h_cm * 10.
    L = L_m * 1000.; db = db_mm;  rec = recub_cm * 10.

    # ─── Cuerpo de la columna ─────────────────────────────────────────────────
    axis2d = ifc.createIfcAxis2Placement2D(
        ifc.createIfcCartesianPoint((0., 0.)), None)
    perfil = ifc.createIfcRectangleProfileDef("AREA", "SeccionColumna", axis2d, b, h)
    dir_extr = ifc.createIfcDirection((0., 0., 1.))
    solido = ifc.createIfcExtrudedAreaSolid(perfil, None, dir_extr, L)
    rep = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solido])
    prod_rep = ifc.createIfcProductDefinitionShape(None, None, [rep])
    place_col = _placement_local(ifc, 0., 0., 0.)

    col = ifc.createIfcColumn(
        ifcopenshell.guid.new(), None,
        f"Columna {b_cm:.0f}×{h_cm:.0f} cm",
        f"b={b_cm:.0f}cm h={h_cm:.0f}cm L={L_m:.2f}m",
        None, place_col, prod_rep, None
    )
    _material(ifc, col, f"Concreto f'c={fc:.0f}MPa")
    rho = As_total_cm2 / (b_cm * h_cm) * 100.
    _pset_diseno(ifc, col, {
        "fc_MPa": fc, "fy_MPa": fy,
        "b_cm": b_cm, "h_cm": h_cm, "L_m": L_m,
        "As_total_cm2": As_total_cm2,
        "Cuantia_pct": round(rho, 3),
        "Barras": f"{n_bars} barras {bar_name}",
        "Pu_kN": Pu_kN, "Mu_kNm": Mu_kNm, "φPn_kN": phi_Pn_kN,
        "Norma": norma,
        "FechaDiseno": datetime.now().strftime("%Y-%m-%d"),
    })

    # ─── Barras longitudinales ────────────────────────────────────────────────
    # Distribución perimetral: esquinas + barras intermedias
    rebars = []
    rec_eje = rec + db_est_mm + db / 2.    # distancia al eje de la barra

    # Posiciones estándar: 4 esquinas + intermedias en lados
    pos = []
    xL = -b / 2. + rec_eje;  xR = b / 2. - rec_eje
    yB = -h / 2. + rec_eje;  yT = h / 2. - rec_eje

    # Esquinas siempre
    pos = [(xL, yB), (xR, yB), (xR, yT), (xL, yT)]

    # Barras extra distribuidas (si n_bars > 4)
    extra = n_bars - 4
    if extra > 0:
        # Repartir en los 4 lados uniformemente
        por_lado = extra // 4
        paso_x = (xR - xL) / (por_lado + 1)
        paso_y = (yT - yB) / (por_lado + 1)
        for i in range(1, por_lado + 1):
            pos.append((xL + i * paso_x, yB))   # inferior
            pos.append((xL + i * paso_x, yT))   # superior
            pos.append((xL, yB + i * paso_y))   # izquierdo
            pos.append((xR, yB + i * paso_y))   # derecho

    # Limitar al número de barras indicado
    pos = pos[:n_bars]

    for idx, (xb, yb) in enumerate(pos):
        ax2d_r = ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint((0., 0.)), None)
        perf_r = ifc.createIfcCircleProfileDef("AREA", None, ax2d_r, db / 2.)
        origin_r = _punto(ifc, xb, yb, 0.)
        ax3d_r = ifc.createIfcAxis2Placement3D(
            origin_r, ifc.createIfcDirection((0., 0., 1.)),
            ifc.createIfcDirection((1., 0., 0.)))
        solid_r = ifc.createIfcExtrudedAreaSolid(
            perf_r, ax3d_r, ifc.createIfcDirection((0., 0., 1.)), L)
        rep_r = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid_r])
        prod_r = ifc.createIfcProductDefinitionShape(None, None, [rep_r])
        place_r = _placement_local(ifc, 0., 0., 0.)

        rebar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, f"Bar_{idx+1}",
            f"Ø{db:.0f}mm | {bar_name}", None, place_r, prod_r, None,
            db / 2., math.pi * (db / 2.) ** 2 / 100., L, "LONGITUDINAL", None)
        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")
        rebars.append(rebar)

    if rebars:
        ifc.createIfcRelAggregates(
            ifcopenshell.guid.new(), None, None, None, col, rebars)

    _contener_en_planta(ifc, planta, [col] + rebars)
    return _guardar_a_bytesio(ifc)


# ══════════════════════════════════════════════════════════════════════════════
# 5. ZAPATA RECTANGULAR (opcional, módulo 09)
# ══════════════════════════════════════════════════════════════════════════════

def ifc_zapata(
    Bx_cm: float, By_cm: float, hz_cm: float,
    fc: float, fy: float,
    bar_name_x: str, db_x_mm: float, n_bars_x: int,
    bar_name_y: str, db_y_mm: float, n_bars_y: int,
    recub_cm: float = 7.5,
    Pu_kN: float = 0., norma: str = "NSR-10",
    nombre_proyecto: str = "Proyecto NSR-10",
) -> io.BytesIO:
    """Exporta una zapata rectangular como IfcFooting con malla de refuerzo."""
    if not IFC_DISPONIBLE:
        raise ImportError("ifcopenshell no está instalado.")

    ifc = ifcopenshell.file(schema="IFC4")
    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)

    Bx = Bx_cm * 10.; By = By_cm * 10.; hz = hz_cm * 10.
    rec = recub_cm * 10.

    # ─── Cuerpo de la zapata ──────────────────────────────────────────────────
    axis2d = ifc.createIfcAxis2Placement2D(
        ifc.createIfcCartesianPoint((0., 0.)), None)
    perfil = ifc.createIfcRectangleProfileDef("AREA", "SeccionZapata", axis2d, Bx, By)
    dir_extr = ifc.createIfcDirection((0., 0., 1.))
    solido = ifc.createIfcExtrudedAreaSolid(perfil, None, dir_extr, hz)
    rep = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solido])
    prod_rep = ifc.createIfcProductDefinitionShape(None, None, [rep])
    place_z = _placement_local(ifc, 0., 0., 0.)

    zapata = ifc.createIfcFooting(
        ifcopenshell.guid.new(), None,
        f"Zapata {Bx_cm:.0f}×{By_cm:.0f}cm h={hz_cm:.0f}cm",
        f"Bx={Bx_cm:.0f} By={By_cm:.0f} hz={hz_cm:.0f}",
        None, place_z, prod_rep, None, "PAD_FOOTING"
    )
    _material(ifc, zapata, f"Concreto f'c={fc:.0f}MPa")
    _pset_diseno(ifc, zapata, {
        "fc_MPa": fc, "fy_MPa": fy,
        "Bx_cm": Bx_cm, "By_cm": By_cm, "hz_cm": hz_cm,
        "As_X": f"{n_bars_x} {bar_name_x}",
        "As_Y": f"{n_bars_y} {bar_name_y}",
        "Pu_kN": Pu_kN, "Norma": norma,
        "FechaDiseno": datetime.now().strftime("%Y-%m-%d"),
    })

    # ─── Malla de refuerzo ────────────────────────────────────────────────────
    rebars = []
    # Barras en X (corren a lo largo de Bx, distribuidas en Y)
    z_bar = rec + db_x_mm / 2.
    sep_y = (By - 2 * rec) / max(n_bars_x - 1, 1)
    for i in range(n_bars_x):
        yb = -By / 2. + rec + i * sep_y
        ax2d_r = ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint((0., 0.)), None)
        perf_r = ifc.createIfcCircleProfileDef("AREA", None, ax2d_r, db_x_mm / 2.)
        origin_r = _punto(ifc, -Bx / 2., yb, z_bar)
        # Barras en dirección X → eje extrusion (1,0,0)
        ax3d_r = ifc.createIfcAxis2Placement3D(
            origin_r, ifc.createIfcDirection((1., 0., 0.)),
            ifc.createIfcDirection((0., 0., 1.)))
        solid_r = ifc.createIfcExtrudedAreaSolid(
            perf_r, ax3d_r, ifc.createIfcDirection((0., 0., 1.)), Bx)
        rep_r = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid_r])
        prod_r = ifc.createIfcProductDefinitionShape(None, None, [rep_r])
        place_r = _placement_local(ifc, 0., 0., 0.)
        rebar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, f"BarX_{i+1}",
            f"Ø{db_x_mm:.0f}mm-X | {bar_name_x}", None, place_r, prod_r, None,
            db_x_mm / 2., math.pi * (db_x_mm / 2.) ** 2 / 100., Bx, "MAIN", None)
        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")
        rebars.append(rebar)

    # Barras en Y (sobre las de X, corren en Y)
    z_bar_y = rec + db_x_mm + db_y_mm / 2.
    sep_x = (Bx - 2 * rec) / max(n_bars_y - 1, 1)
    for i in range(n_bars_y):
        xb = -Bx / 2. + rec + i * sep_x
        ax2d_r = ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint((0., 0.)), None)
        perf_r = ifc.createIfcCircleProfileDef("AREA", None, ax2d_r, db_y_mm / 2.)
        origin_r = _punto(ifc, xb, -By / 2., z_bar_y)
        ax3d_r = ifc.createIfcAxis2Placement3D(
            origin_r, ifc.createIfcDirection((0., 1., 0.)),
            ifc.createIfcDirection((0., 0., 1.)))
        solid_r = ifc.createIfcExtrudedAreaSolid(
            perf_r, ax3d_r, ifc.createIfcDirection((0., 0., 1.)), By)
        rep_r = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid_r])
        prod_r = ifc.createIfcProductDefinitionShape(None, None, [rep_r])
        place_r = _placement_local(ifc, 0., 0., 0.)
        rebar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, f"BarY_{i+1}",
            f"Ø{db_y_mm:.0f}mm-Y | {bar_name_y}", None, place_r, prod_r, None,
            db_y_mm / 2., math.pi * (db_y_mm / 2.) ** 2 / 100., By, "MAIN", None)
        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")
        rebars.append(rebar)

    if rebars:
        ifc.createIfcRelAggregates(
            ifcopenshell.guid.new(), None, None, None, zapata, rebars)

    _contener_en_planta(ifc, planta, [zapata] + rebars)
    return _guardar_a_bytesio(ifc)


# ══════════════════════════════════════════════════════════════════════════════
# 6. COLUMNA CIRCULAR
# ══════════════════════════════════════════════════════════════════════════════

def ifc_columna_circular(
    D_cm: float, L_m: float,
    fc: float, fy: float,
    n_bars: int, bar_name: str, db_mm: float, db_est_mm: float,
    As_total_cm2: float, recub_cm: float,
    Pu_kN: float = 0., Mu_kNm: float = 0., phi_Pn_kN: float = 0.,
    norma: str = "NSR-10",
    nombre_proyecto: str = "Proyecto NSR-10",
) -> io.BytesIO:
    """Exporta una Columna Circular como IfcColumn con barras longitudinales distribuidas radialmente."""
    if not IFC_DISPONIBLE:
        raise ImportError("ifcopenshell no está instalado.")

    ifc = ifcopenshell.file(schema="IFC4")
    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)

    D = D_cm * 10.
    L = L_m * 1000.
    db = db_mm
    rec = recub_cm * 10.

    # ─── Cuerpo de la columna ─────────────────────────────────────────────────
    axis2d = ifc.createIfcAxis2Placement2D(
        ifc.createIfcCartesianPoint((0., 0.)), None)
    # IMPORTANTE: IfcCircleProfileDef for true cylindrical shape!
    perfil = ifc.createIfcCircleProfileDef("AREA", "SeccionColumnaCirc", axis2d, D / 2.)
    dir_extr = ifc.createIfcDirection((0., 0., 1.))
    solido = ifc.createIfcExtrudedAreaSolid(perfil, None, dir_extr, L)
    rep = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solido])
    prod_rep = ifc.createIfcProductDefinitionShape(None, None, [rep])
    place_col = _placement_local(ifc, 0., 0., 0.)

    col = ifc.createIfcColumn(
        ifcopenshell.guid.new(), None,
        f"Columna Circular Ø{D_cm:.0f} cm",
        f"D={D_cm:.0f}cm L={L_m:.2f}m",
        None, place_col, prod_rep, None
    )
    _material(ifc, col, f"Concreto f'c={fc:.0f}MPa")
    rho = As_total_cm2 / (math.pi * (D_cm / 2.) ** 2) * 100.
    _pset_diseno(ifc, col, {
        "fc_MPa": fc, "fy_MPa": fy,
        "D_cm": D_cm, "L_m": L_m,
        "As_total_cm2": As_total_cm2,
        "Cuantia_pct": round(rho, 3),
        "Barras": f"{n_bars} barras {bar_name}",
        "Pu_kN": Pu_kN, "Mu_kNm": Mu_kNm, "φPn_kN": phi_Pn_kN,
        "Norma": norma,
        "FechaDiseno": datetime.now().strftime("%Y-%m-%d"),
    })

    # ─── Barras longitudinales en arreglo radial ──────────────────────────────
    rebars = []
    # Radio hasta el centro de las barras
    R_bar = D / 2. - rec - db_est_mm - db / 2.
    
    for i in range(n_bars):
        angle = 2 * math.pi * i / n_bars
        xb = R_bar * math.cos(angle)
        yb = R_bar * math.sin(angle)
        
        ax2d_r = ifc.createIfcAxis2Placement2D(
            ifc.createIfcCartesianPoint((0., 0.)), None)
        perf_r = ifc.createIfcCircleProfileDef("AREA", None, ax2d_r, db / 2.)
        origin_r = _punto(ifc, xb, yb, 0.)
        ax3d_r = ifc.createIfcAxis2Placement3D(
            origin_r, ifc.createIfcDirection((0., 0., 1.)),
            ifc.createIfcDirection((1., 0., 0.)))
        solid_r = ifc.createIfcExtrudedAreaSolid(
            perf_r, ax3d_r, ifc.createIfcDirection((0., 0., 1.)), L)
        rep_r = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid_r])
        prod_r = ifc.createIfcProductDefinitionShape(None, None, [rep_r])
        place_r = _placement_local(ifc, 0., 0., 0.)

        rebar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, f"Bar_{i+1}",
            f"Ø{db:.0f}mm | {bar_name}", None, place_r, prod_r, None,
            db / 2., math.pi * (db / 2.) ** 2 / 100., L, "LONGITUDINAL", None)
        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")
        rebars.append(rebar)

    if rebars:
        ifc.createIfcRelAggregates(
            ifcopenshell.guid.new(), None, None, None, col, rebars)

    _contener_en_planta(ifc, planta, [col] + rebars)
    return _guardar_a_bytesio(ifc)



# ══════════════════════════════════════════════════════════════════════════════
# 7. GRUPO DE PILOTES Y ENCEPADO
# ══════════════════════════════════════════════════════════════════════════════

def ifc_grupo_pilotes(
    B_dado_m: float, L_dado_m: float, H_dado_m: float,
    tipo_seccion: str, D_pilote_m: float, L_pilote_m: float,
    m_filas: int, n_cols: int, S_metros: float,
    fc_dado: float, fc_pilote: float,
    nombre_proyecto: str = "Cimentación Profunda"
) -> io.BytesIO:
    """Exporta un encepado con su grupo de pilotes inferior."""
    if not IFC_DISPONIBLE:
        raise ImportError("ifcopenshell no está instalado.")

    ifc = ifcopenshell.file(schema="IFC4")
    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)

    # Convertir a mm
    Bd = B_dado_m * 1000.
    Ld = L_dado_m * 1000.
    Hd = H_dado_m * 1000.
    
    Dp = D_pilote_m * 1000.
    Lp = L_pilote_m * 1000.
    Sm = S_metros * 1000.

    elementos_bim = []

    # 1. Crear el Encepado (Dado) centríco en Z=0 (hacia abajo -Hd) o Z=+Hd
    # Mejor que el dado empiece en Z=0 hacia abajo, y pilotes desde Z=-Hd hacia abajo
    axis2d_dado = ifc.createIfcAxis2Placement2D(ifc.createIfcCartesianPoint((0., 0.)), None)
    perf_dado = ifc.createIfcRectangleProfileDef("AREA", "Dado", axis2d_dado, Bd, Ld)
    dir_extr = ifc.createIfcDirection((0., 0., -1.))
    sol_dado = ifc.createIfcExtrudedAreaSolid(perf_dado, None, dir_extr, Hd)
    
    rep_dado = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [sol_dado])
    prod_rep_d = ifc.createIfcProductDefinitionShape(None, None, [rep_dado])
    place_dado = _placement_local(ifc, 0., 0., 0.)

    dado = ifc.createIfcFooting(
        ifcopenshell.guid.new(), None,
        f"Encepado {B_dado_m}x{L_dado_m}x{H_dado_m}m",
        "Dado de pilotes", None, place_dado, prod_rep_d, None, "PAD_FOOTING"
    )
    _material(ifc, dado, f"Concreto Encepado f'c={fc_dado:.0f}MPa")
    elementos_bim.append(dado)

    # 2. Crear los Pilotes
    offset_x = (n_cols - 1) * Sm / 2.0
    offset_y = (m_filas - 1) * Sm / 2.0

    # Perfil del pilote
    axis2d_p = ifc.createIfcAxis2Placement2D(ifc.createIfcCartesianPoint((0., 0.)), None)
    if tipo_seccion == "Circular":
        perf_pilote = ifc.createIfcCircleProfileDef("AREA", "PiloteCirc", axis2d_p, Dp / 2.)
    else:
        perf_pilote = ifc.createIfcRectangleProfileDef("AREA", "PiloteCuad", axis2d_p, Dp, Dp)

    for i in range(n_cols):
        for j in range(m_filas):
            cx = -offset_x + i * Sm
            cy = -offset_y + j * Sm
            # Extrusión hacia abajo desde la base del dado (Z = -Hd)
            dir_extr_p = ifc.createIfcDirection((0., 0., -1.))
            sol_p = ifc.createIfcExtrudedAreaSolid(perf_pilote, None, dir_extr_p, Lp)
            
            rep_p = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [sol_p])
            prod_rep_p = ifc.createIfcProductDefinitionShape(None, None, [rep_p])
            place_p = _placement_local(ifc, cx, cy, -Hd)

            # Usamos IfcPile directamente
            pilote = ifc.createIfcPile(
                ifcopenshell.guid.new(), None,
                f"Pilote {i}-{j}",
                f"Pilote {tipo_seccion} L={L_pilote_m}m", 
                None, place_p, prod_rep_p, None, None, None
            )
            _material(ifc, pilote, f"Concreto Pilote f'c={fc_pilote:.0f}MPa")
            elementos_bim.append(pilote)

            # Agrupar pilote al dado para indicar que es un assembly
            ifc.createIfcRelAggregates(
                ifcopenshell.guid.new(), None, None, None, dado, [pilote])

    _contener_en_planta(ifc, planta, elementos_bim)
    return _guardar_a_bytesio(ifc)
