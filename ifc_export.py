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



def _apply_color(ifc, element, rgb_tuple):

    # rgb_tuple is (r, g, b) between 0.0 and 1.0

    color = ifc.createIfcColourRgb(None, *rgb_tuple)

    surface_style = ifc.createIfcSurfaceStyleRendering(color, 0.0, None, None, None, None, None, None, 'NOTDEFINED')

    style = ifc.createIfcSurfaceStyle(None, 'BOTH', [surface_style])

    presentation_assignment = ifc.createIfcPresentationStyleAssignment([style])

    # For IFC4, we use RelAssociatesMaterial? No, we use StyledItem for representation

    # The actual representation items are inside the Representation context.

    # It's better to assign the style to the shape representation items directly.

    rep = element.Representation.Representations[0]

    for item in rep.Items:

        ifc.createIfcStyledItem(item, [presentation_assignment], None)



def _get_rebar_color(db_mm):

    # Color mapping based on nominal diameter

    if db_mm < 7.0: return (0.8, 0.8, 0.0)    # #2 1/4"  - Yellow

    elif db_mm < 10.0: return (0.6, 0.2, 0.8) # #3 3/8"  - Purple

    elif db_mm < 14.0: return (0.0, 0.5, 1.0) # #4 1/2"  - Blue

    elif db_mm < 17.0: return (0.0, 0.8, 0.0) # #5 5/8"  - Green

    elif db_mm < 20.0: return (1.0, 0.5, 0.0) # #6 3/4"  - Orange

    elif db_mm < 24.0: return (0.0, 1.0, 1.0) # #7 7/8"  - Cyan

    else: return (1.0, 0.0, 0.0)              # #8+ 1"+  - Red





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











def _placement_local(ifc, x=0., y=0., z=0., eje_x=None, eje_z=None, rel_to=None):



    """Genera un IfcLocalPlacement en la posición (x,y,z)."""



    ejeZ = ifc.createIfcDirection(eje_z if eje_z else (0., 0., 1.))



    ejeX = ifc.createIfcDirection(eje_x if eje_x else (1., 0., 0.))



    ax   = ifc.createIfcAxis2Placement3D(_punto(ifc, x, y, z), ejeZ, ejeX)



    return ifc.createIfcLocalPlacement(rel_to, ax)











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



    db_est_mm: float = 9.5,



    sep_est_mm: float = 150.,



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



        place_r = _placement_local(ifc, 0., 0., 0., rel_to=place_viga)







        rebar = ifc.createIfcReinforcingBar(



            ifcopenshell.guid.new(), None,



            f"Bar_{idx+1}",



            f"Ø{db:.0f}mm | {bar_name}",



            None, place_r, prod_r, None,



            "420MPa", db / 2.,      # NominalDiameter



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








    # ── Color barras longitudinales ──────────────────────────────────────────
    _rgb_long = _get_rebar_color(db_mm)
    for _rb in rebars:
        try: _apply_color(ifc, _rb, _rgb_long)
        except Exception: pass

    # ── Estribos rectangulares (flejes) ─────────────────────────────────────
    _r_est = db_est_mm / 2.
    _xi = -b / 2. + rec + db_est_mm / 2.
    _xf =  b / 2. - rec - db_est_mm / 2.
    _yi = -h / 2. + rec + db_est_mm / 2.
    _yf =  h / 2. - rec - db_est_mm / 2.
    _sides_tmpl = [
        ((_xi,_yi),(_xf,_yi)), ((_xf,_yi),(_xf,_yf)),
        ((_xf,_yf),(_xi,_yf)), ((_xi,_yf),(_xi,_yi))
    ]

    def _estribo_segs(z_mm):
        segs = []
        for (x1,y1),(x2,y2) in _sides_tmpl:
            dx = x2-x1; dy = y2-y1; L_seg = math.sqrt(dx**2+dy**2)
            if L_seg < 1e-6: continue
            ax2e = ifc.createIfcAxis2Placement2D(ifc.createIfcCartesianPoint((0.,0.)), None)
            pfe  = ifc.createIfcCircleProfileDef("AREA", None, ax2e, _r_est)
            orig = ifc.createIfcCartesianPoint((x1, y1, z_mm))
            dz   = ifc.createIfcDirection((dx/L_seg, dy/L_seg, 0.))
            dxr  = ifc.createIfcDirection((-dy/L_seg, dx/L_seg, 0.))
            ax3e = ifc.createIfcAxis2Placement3D(orig, dz, dxr)
            sol  = ifc.createIfcExtrudedAreaSolid(pfe, ax3e, ifc.createIfcDirection((0.,0.,1.)), L_seg)
            segs.append(sol)
        return segs

    _all_est_solids = []
    _z = sep_est_mm / 2.
    while _z <= L:
        _all_est_solids.extend(_estribo_segs(_z))
        _z += sep_est_mm

    _est_list_vr = []
    if _all_est_solids:
        _rep_e = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", _all_est_solids)
        _prod_e = ifc.createIfcProductDefinitionShape(None, None, [_rep_e])
        _place_e = _placement_local(ifc, 0., 0., 0., rel_to=place_viga)
        _est_bar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, "Estribos",
            f"O{db_est_mm:.0f}mm Flejes@{sep_est_mm:.0f}mm",
            None, _place_e, _prod_e, None,
            f"fy={fy:.0f}MPa", _r_est, math.pi*_r_est**2/100., None, "LIGATURE", None)
        _material(ifc, _est_bar, f"Acero fy={fy:.0f}MPa")
        try: _apply_color(ifc, _est_bar, _get_rebar_color(db_est_mm))
        except Exception: pass
        _est_list_vr.append(_est_bar)
        ifc.createIfcRelAggregates(ifcopenshell.guid.new(), None, None, None, viga, _est_list_vr)

    # ── Rotulo ICONTEC como PropertySet ─────────────────────────────────────
    _pset_diseno(ifc, viga, {
        "Empresa": "Ingenieria Estructural",
        "Proyecto": nombre_proyecto,
        "Norma": norma,
        "N_Plano": "VIG-001",
        "Escala": "1:20",
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "Elaboro": "Ing. Disenador",
        "Reviso": "Ing. Revisor",
        "Aprobo": "Ing. Aprobador",
        "Revision": "0",
        "Hoja": "1/1",
        "Vol_concreto_m3": round((b_cm*h_cm/10000.)*L_m, 4),
        "As_long_cm2": round(As_cm2, 2),
        "db_long_mm": db_mm,
        "db_est_mm": db_est_mm,
        "n_barras": n_bars,
        "Recub_cm": recub_cm,
    }, nombre="Pset_Rotulo_ICONTEC")
    _contener_en_planta(ifc, planta, [viga] + rebars + _est_list_vr)



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



    db_est_mm: float = 9.5,



    sep_est_mm: float = 150.,



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



        place_r = _placement_local(ifc, 0., 0., 0., rel_to=place_viga)







        rebar = ifc.createIfcReinforcingBar(



            ifcopenshell.guid.new(), None, f"Bar_{idx+1}",



            f"Ø{db:.0f}mm | {bar_name}", None, place_r, prod_r, None,



            "420MPa", db / 2., math.pi * (db / 2.) ** 2 / 100., L, "MAIN", None)



        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")



        rebars.append(rebar)







    if rebars:



        ifc.createIfcRelAggregates(



            ifcopenshell.guid.new(), None, None, None, viga, rebars)








    # ── Color barras longitudinales ──────────────────────────────────────────
    _rgb_long = _get_rebar_color(db_mm)
    for _rb in rebars:
        try: _apply_color(ifc, _rb, _rgb_long)
        except Exception: pass

    # ── Estribos rectangulares en el alma (flejes) ──────────────────
    _r_est = db_est_mm / 2.
    _xi = -bw / 2. + rec + db_est_mm / 2.
    _xf =  bw / 2. - rec - db_est_mm / 2.
    # Typically T-beam origin is mid-height of total h or at bottom.
    # In ifc_export.py: IfcTShapeProfileDef is centered on the CG depending on standard, 
    # but let's assume we do the same y positions as rectangular for simplicity if origin is center.
    # Actually IfcTShapeProfileDef origin is at the intersection of web and flange usually, 
    # but let's assume standard from bottom to top. 
    # Wait, the rebars are placed at y = rec + db/2, so bottom is y = 0 or -h/2?
    # the code says: origin_r = _punto(ifc, xb, yb - h/2., 0.)
    # So bottom of beam is -h/2.
    _yi = -h / 2. + rec + db_est_mm / 2.
    _yf =  h / 2. - rec - db_est_mm / 2.
    _sides_tmpl = [
        ((_xi,_yi),(_xf,_yi)), ((_xf,_yi),(_xf,_yf)),
        ((_xf,_yf),(_xi,_yf)), ((_xi,_yf),(_xi,_yi))
    ]

    def _estribo_segs_t(z_mm):
        segs = []
        for (x1,y1),(x2,y2) in _sides_tmpl:
            dx = x2-x1; dy = y2-y1; L_seg = math.sqrt(dx**2+dy**2)
            if L_seg < 1e-6: continue
            ax2e = ifc.createIfcAxis2Placement2D(ifc.createIfcCartesianPoint((0.,0.)), None)
            pfe  = ifc.createIfcCircleProfileDef("AREA", None, ax2e, _r_est)
            orig = ifc.createIfcCartesianPoint((x1, y1, z_mm))
            dz   = ifc.createIfcDirection((dx/L_seg, dy/L_seg, 0.))
            dxr  = ifc.createIfcDirection((-dy/L_seg, dx/L_seg, 0.))
            ax3e = ifc.createIfcAxis2Placement3D(orig, dz, dxr)
            sol  = ifc.createIfcExtrudedAreaSolid(pfe, ax3e, ifc.createIfcDirection((0.,0.,1.)), L_seg)
            segs.append(sol)
        return segs

    _all_est_solids_t = []
    _z = sep_est_mm / 2.
    while _z <= L:
        _all_est_solids_t.extend(_estribo_segs_t(_z))
        _z += sep_est_mm

    _est_list_vt = []
    if _all_est_solids_t:
        _rep_e = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", _all_est_solids_t)
        _prod_e = ifc.createIfcProductDefinitionShape(None, None, [_rep_e])
        _place_e = _placement_local(ifc, 0., 0., 0., rel_to=place_viga)
        _est_bar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, "Estribos",
            f"O{db_est_mm:.0f}mm Flejes@{sep_est_mm:.0f}mm",
            None, _place_e, _prod_e, None,
            f"fy={fy:.0f}MPa", _r_est, math.pi*_r_est**2/100., None, "LIGATURE", None)
        _material(ifc, _est_bar, f"Acero fy={fy:.0f}MPa")
        try: _apply_color(ifc, _est_bar, _get_rebar_color(db_est_mm))
        except Exception: pass
        _est_list_vt.append(_est_bar)
        ifc.createIfcRelAggregates(ifcopenshell.guid.new(), None, None, None, viga, _est_list_vt)

    # ── Rotulo ICONTEC como PropertySet ─────────────────────────────────────
    _pset_diseno(ifc, viga, {
        "Empresa": "Ingenieria Estructural",
        "Proyecto": nombre_proyecto,
        "Norma": norma,
        "N_Plano": "VIG-002",
        "Escala": "1:20",
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "Elaboro": "Ing. Disenador",
        "Reviso": "Ing. Revisor",
        "Aprobo": "Ing. Aprobador",
        "Revision": "0",
        "Hoja": "1/1",
        "Vol_concreto_m3": round((bf_cm*hf_cm + bw_cm*(h_cm-hf_cm))/10000.*L_m, 4),
        "As_long_cm2": round(As_cm2, 2),
        "db_long_mm": db_mm,
        "db_est_mm": db_est_mm,
        "n_barras": n_bars,
        "Recub_cm": recub_cm,
    }, nombre="Pset_Rotulo_ICONTEC")
    _contener_en_planta(ifc, planta, [viga] + rebars + _est_list_vt)



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



    db_est_mm: float = 9.5,



    sep_est_mm: float = 150.,



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



        place_r = _placement_local(ifc, 0., 0., 0., rel_to=place_losa)







        rebar = ifc.createIfcReinforcingBar(



            ifcopenshell.guid.new(), None, f"Bar_Princ_{i+1}",



            f"Ø{db:.0f}mm s={s_cm:.0f}cm", None, place_r, prod_r, None,



            "420MPa", db / 2., math.pi * (db / 2.) ** 2 / 100., L, "MAIN", None)



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



        place_r = _placement_local(ifc, 0., 0., 0., rel_to=place_col)







        rebar = ifc.createIfcReinforcingBar(



            ifcopenshell.guid.new(), None, f"Bar_{idx+1}",



            f"Ø{db:.0f}mm | {bar_name}", None, place_r, prod_r, None,



            "420MPa", db / 2., math.pi * (db / 2.) ** 2 / 100., L, "USERDEFINED", None)



        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")



        rebars.append(rebar)







    if rebars:



        ifc.createIfcRelAggregates(



            ifcopenshell.guid.new(), None, None, None, col, rebars)








    # ── Color barras longitudinales por diámetro ─────────────────────────────
    _rgb_long = _get_rebar_color(db_mm)
    for _rb in rebars:
        try:
            _apply_color(ifc, _rb, _rgb_long)
        except Exception:
            pass

    # ── Estribos rectangulares (flejes) ─────────────────────────────────────
    _Lo_mm = max(L * 0.167, max(b, h), 450.)
    _s_conf_mm = max(min(db_est_mm * 4., 100.), 50.)
    _s_cen_mm  = min(150., (b + h) / 4.)
    _r_est = db_est_mm / 2.
    _xi = -b / 2. + rec + db_est_mm / 2.
    _xf =  b / 2. - rec - db_est_mm / 2.
    _yi = -h / 2. + rec + db_est_mm / 2.
    _yf =  h / 2. - rec - db_est_mm / 2.
    _sides_tmpl = [
        ((_xi,_yi),(_xf,_yi)), ((_xf,_yi),(_xf,_yf)),
        ((_xf,_yf),(_xi,_yf)), ((_xi,_yf),(_xi,_yi))
    ]

    def _estribo_segs(z_mm):
        segs = []
        for (x1,y1),(x2,y2) in _sides_tmpl:
            dx = x2-x1; dy = y2-y1; L_seg = math.sqrt(dx**2+dy**2)
            if L_seg < 1e-6: continue
            ax2e = ifc.createIfcAxis2Placement2D(ifc.createIfcCartesianPoint((0.,0.)), None)
            pfe  = ifc.createIfcCircleProfileDef("AREA", None, ax2e, _r_est)
            orig = ifc.createIfcCartesianPoint((x1, y1, z_mm))
            dz   = ifc.createIfcDirection((dx/L_seg, dy/L_seg, 0.))
            dxr  = ifc.createIfcDirection((-dy/L_seg, dx/L_seg, 0.))
            ax3e = ifc.createIfcAxis2Placement3D(orig, dz, dxr)
            sol  = ifc.createIfcExtrudedAreaSolid(pfe, ax3e, ifc.createIfcDirection((0.,0.,1.)), L_seg)
            segs.append(sol)
        return segs

    _all_est_solids = []
    _z = _s_conf_mm / 2.
    while _z <= _Lo_mm and _z < L:
        _all_est_solids.extend(_estribo_segs(_z)); _z += _s_conf_mm
    while _z <= L - _Lo_mm:
        _all_est_solids.extend(_estribo_segs(_z)); _z += _s_cen_mm
    while _z <= L - _s_conf_mm/2. and _z < L:
        _all_est_solids.extend(_estribo_segs(_z)); _z += _s_conf_mm

    _est_list = []
    if _all_est_solids:
        _rep_e = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", _all_est_solids)
        _prod_e = ifc.createIfcProductDefinitionShape(None, None, [_rep_e])
        _place_e = _placement_local(ifc, 0., 0., 0., rel_to=place_col)
        _est_bar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, "Estribos",
            f"O{db_est_mm:.0f}mm Flejes@{_s_conf_mm:.0f}/{_s_cen_mm:.0f}mm",
            None, _place_e, _prod_e, None,
            f"fy={fy:.0f}MPa", _r_est, math.pi*_r_est**2/100., None, "LIGATURE", None)
        _material(ifc, _est_bar, f"Acero fy={fy:.0f}MPa")
        try: _apply_color(ifc, _est_bar, _get_rebar_color(db_est_mm))
        except Exception: pass
        _est_list.append(_est_bar)
        ifc.createIfcRelAggregates(ifcopenshell.guid.new(), None, None, None, col, _est_list)

    # ── Rotulo ICONTEC como PropertySet ─────────────────────────────────────
    _pset_diseno(ifc, col, {
        "Empresa": "Ingenieria Estructural",
        "Proyecto": nombre_proyecto,
        "Norma": norma,
        "N_Plano": "COL-001",
        "Escala": "1:20",
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "Elaboro": "Ing. Disenador",
        "Reviso": "Ing. Revisor",
        "Aprobo": "Ing. Aprobador",
        "Revision": "0",
        "Hoja": "1/1",
        "Vol_concreto_m3": round((b_cm*h_cm/10000.)*L_m, 4),
        "As_long_cm2": round(As_total_cm2, 2),
        "Cuantia_pct": round(As_total_cm2/(b_cm*h_cm)*100., 3),
        "db_long_mm": db_mm,
        "db_est_mm": db_est_mm,
        "n_barras": n_bars,
        "Recub_cm": recub_cm,
    }, nombre="Pset_Rotulo_ICONTEC")

    _contener_en_planta(ifc, planta, [col] + rebars + _est_list)



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



    db_est_mm: float = 9.5,



    sep_est_mm: float = 150.,



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



        place_r = _placement_local(ifc, 0., 0., 0., rel_to=place_z)



        rebar = ifc.createIfcReinforcingBar(



            ifcopenshell.guid.new(), None, f"BarX_{i+1}",



            f"Ø{db_x_mm:.0f}mm-X | {bar_name_x}", None, place_r, prod_r, None,



            "420MPa", db_x_mm / 2., math.pi * (db_x_mm / 2.) ** 2 / 100., Bx, "MAIN", None)



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



        place_r = _placement_local(ifc, 0., 0., 0., rel_to=place_z)



        rebar = ifc.createIfcReinforcingBar(



            ifcopenshell.guid.new(), None, f"BarY_{i+1}",



            f"Ø{db_y_mm:.0f}mm-Y | {bar_name_y}", None, place_r, prod_r, None,



            "420MPa", db_y_mm / 2., math.pi * (db_y_mm / 2.) ** 2 / 100., By, "MAIN", None)



        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")



        rebars.append(rebar)







    if rebars:



        ifc.createIfcRelAggregates(



            ifcopenshell.guid.new(), None, None, None, zapata, rebars)








    # ── Color de malla inferior ──────────────────────────────────────────────
    _rgb_x = _get_rebar_color(db_x_mm)
    for _rb in rebars_x:
        try: _apply_color(ifc, _rb, _rgb_x)
        except Exception: pass
        
    _rgb_y = _get_rebar_color(db_y_mm)
    for _rb in rebars_y:
        try: _apply_color(ifc, _rb, _rgb_y)
        except Exception: pass

    # ── Rotulo ICONTEC como PropertySet ─────────────────────────────────────
    _pset_diseno(ifc, zapata, {
        "Empresa": "Ingenieria Estructural",
        "Proyecto": nombre_proyecto,
        "Norma": norma,
        "N_Plano": "CIM-001",
        "Escala": "1:20",
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "Elaboro": "Ing. Disenador",
        "Reviso": "Ing. Revisor",
        "Aprobo": "Ing. Aprobador",
        "Revision": "0",
        "Hoja": "1/1",
        "Vol_concreto_m3": round((Bx_cm*By_cm*hz_cm)/1000000., 4),
        "db_x_mm": db_x_mm, "n_bars_x": n_bars_x,
        "db_y_mm": db_y_mm, "n_bars_y": n_bars_y,
        "Recub_cm": recub_cm,
    }, nombre="Pset_Rotulo_ICONTEC")
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



        place_r = _placement_local(ifc, 0., 0., 0., rel_to=place_col)







        rebar = ifc.createIfcReinforcingBar(



            ifcopenshell.guid.new(), None, f"Bar_{i+1}",



            f"Ø{db:.0f}mm | {bar_name}", None, place_r, prod_r, None,



            "420MPa", db / 2., math.pi * (db / 2.) ** 2 / 100., L, "USERDEFINED", None)



        _material(ifc, rebar, f"Acero fy={fy:.0f}MPa")



        rebars.append(rebar)







    if rebars:



        ifc.createIfcRelAggregates(



            ifcopenshell.guid.new(), None, None, None, col, rebars)








    # ── Color barras longitudinales ──────────────────────────────────────────
    _rgb_long = _get_rebar_color(db_mm)
    for _rb in rebars:
        try: _apply_color(ifc, _rb, _rgb_long)
        except Exception: pass

    # ── Estribos circulares (espiral aproximada a aros concéntricos) ────────
    _Lo_mm = max(L * 0.167, D, 450.)
    _s_conf_mm = max(min(db_est_mm * 4., 100.), 50.)
    _s_cen_mm  = min(150., D / 4.)
    _R_est_center = D / 2. - rec - db_est_mm / 2.
    _r_est = db_est_mm / 2.

    def _est_circ_segs(z_mm):
        # Aproximación poligonal de 16 segmentos
        n_segs = 16
        pts = [( _R_est_center * math.cos(2*math.pi*i/n_segs),
                 _R_est_center * math.sin(2*math.pi*i/n_segs) ) for i in range(n_segs+1)]
        segs = []
        for i in range(n_segs):
            x1, y1 = pts[i]; x2, y2 = pts[i+1]
            dx = x2-x1; dy = y2-y1; L_seg = math.sqrt(dx**2+dy**2)
            if L_seg < 1e-6: continue
            ax2e = ifc.createIfcAxis2Placement2D(ifc.createIfcCartesianPoint((0.,0.)), None)
            pfe  = ifc.createIfcCircleProfileDef("AREA", None, ax2e, _r_est)
            orig = ifc.createIfcCartesianPoint((x1, y1, z_mm))
            dz   = ifc.createIfcDirection((dx/L_seg, dy/L_seg, 0.))
            dxr  = ifc.createIfcDirection((-dy/L_seg, dx/L_seg, 0.))
            ax3e = ifc.createIfcAxis2Placement3D(orig, dz, dxr)
            sol  = ifc.createIfcExtrudedAreaSolid(pfe, ax3e, ifc.createIfcDirection((0.,0.,1.)), L_seg)
            segs.append(sol)
        return segs

    _all_est_circ_solids = []
    _z = _s_conf_mm / 2.
    while _z <= _Lo_mm and _z < L:
        _all_est_circ_solids.extend(_est_circ_segs(_z)); _z += _s_conf_mm
    while _z <= L - _Lo_mm:
        _all_est_circ_solids.extend(_est_circ_segs(_z)); _z += _s_cen_mm
    while _z <= L - _s_conf_mm/2. and _z < L:
        _all_est_circ_solids.extend(_est_circ_segs(_z)); _z += _s_conf_mm

    _est_list_circ = []
    if _all_est_circ_solids:
        _rep_e = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", _all_est_circ_solids)
        _prod_e = ifc.createIfcProductDefinitionShape(None, None, [_rep_e])
        _place_e = _placement_local(ifc, 0., 0., 0., rel_to=place_col)
        _est_bar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, "Espiral_Estribos",
            f"O{db_est_mm:.0f}mm Espiral@{_s_conf_mm:.0f}/{_s_cen_mm:.0f}mm",
            None, _place_e, _prod_e, None,
            f"fy={fy:.0f}MPa", _r_est, math.pi*_r_est**2/100., None, "LIGATURE", None)
        _material(ifc, _est_bar, f"Acero fy={fy:.0f}MPa")
        try: _apply_color(ifc, _est_bar, _get_rebar_color(db_est_mm))
        except Exception: pass
        _est_list_circ.append(_est_bar)
        ifc.createIfcRelAggregates(ifcopenshell.guid.new(), None, None, None, col, _est_list_circ)

    # ── Rotulo ICONTEC como PropertySet ─────────────────────────────────────
    _pset_diseno(ifc, col, {
        "Empresa": "Ingenieria Estructural",
        "Proyecto": nombre_proyecto,
        "Norma": norma,
        "N_Plano": "COL-002",
        "Escala": "1:20",
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "Elaboro": "Ing. Disenador",
        "Reviso": "Ing. Revisor",
        "Aprobo": "Ing. Aprobador",
        "Revision": "0",
        "Hoja": "1/1",
        "Vol_concreto_m3": round((math.pi * (D_cm/2.0)**2 / 10000.)*L_m, 4),
        "As_long_cm2": round(As_total_cm2, 2),
        "Cuantia_pct": round(As_total_cm2/(math.pi * (D_cm/2.0)**2)*100., 3),
        "db_long_mm": db_mm,
        "db_est_mm": db_est_mm,
        "n_barras": n_bars,
        "Recub_cm": recub_cm,
    }, nombre="Pset_Rotulo_ICONTEC")

    _contener_en_planta(ifc, planta, [col] + rebars + _est_list_circ)



    return _guardar_a_bytesio(ifc)















# ══════════════════════════════════════════════════════════════════════════════



# 7. GRUPO DE PILOTES Y ENCEPADO



# ══════════════════════════════════════════════════════════════════════════════







def ifc_grupo_pilotes(



    B_dado_m: float, L_dado_m: float, H_dado_m: float,



    tipo_seccion: str, D_pilote_m: float, L_pilote_m: float,



    m_filas: int, n_cols: int, S_metros: float,



    fc_dado: float, fc_pilote: float,



    nombre_proyecto: str = "Cimentacion Profunda",



    n_barras_p: int = 0, db_long_mm: float = 0.0, s_trans_mm: float = 0.0, db_est_mm: float = 9.5) -> "io.BytesIO":



    """Exporta un encepado genérico con su grupo de pilotes. Enfoque canónico IFC4."""



    if not IFC_DISPONIBLE:



        raise ImportError("ifcopenshell no disponible.")







    ifc = ifcopenshell.file(schema="IFC4")



    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)







    # Conversión a local mm



    Bd = B_dado_m * 1000.



    Ld = L_dado_m * 1000.



    Hd = H_dado_m * 1000.



    Dp = D_pilote_m * 1000.



    Lp = L_pilote_m * 1000.



    Sm = S_metros * 1000.







    elementos = []







    # Helpers



    def _pt2(x, y): return ifc.createIfcCartesianPoint((float(x), float(y)))



    def _pt3(x, y, z): return ifc.createIfcCartesianPoint((float(x), float(y), float(z)))



    def _dir3(x, y, z): return ifc.createIfcDirection((float(x), float(y), float(z)))



    def _ax3(ox=0., oy=0., oz=0., zx=0., zy=0., zz=1., xx=1., xy=0., xz=0.):



        return ifc.createIfcAxis2Placement3D(_pt3(ox, oy, oz), _dir3(zx, zy, zz), _dir3(xx, xy, xz))



    def _local_plac(ox=0., oy=0., oz=0.):



        return ifc.createIfcLocalPlacement(None, _ax3(ox, oy, oz))



    def _rect_solid(w, h, depth):



        prof = ifc.createIfcRectangleProfileDef("AREA", None, ifc.createIfcAxis2Placement2D(_pt2(0,0), None), float(w), float(h))



        return ifc.createIfcExtrudedAreaSolid(prof, _ax3(), _dir3(0,0,1), float(depth))



    def _cyl_local(rad, depth):



        prof = ifc.createIfcCircleProfileDef("AREA", None, ifc.createIfcAxis2Placement2D(_pt2(0,0), None), float(rad))



        return ifc.createIfcExtrudedAreaSolid(prof, _ax3(), _dir3(0,0,1), float(depth))



    def _shape_solid(solid):



        rep = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid])



        return ifc.createIfcProductDefinitionShape(None, None, [rep])







    # 1. Encepado en (-Bd/2, -Ld/2, -Hd) hasta 0



    dado = ifc.createIfcFooting(



        ifcopenshell.guid.new(), None, "Encepado", "PAD_FOOTING", None,



        _local_plac(-Bd/2, -Ld/2, -Hd), _shape_solid(_rect_solid(Bd, Ld, Hd)),



        None, "PAD_FOOTING")



    _material(ifc, dado, f"Concreto f'c={fc_dado}MPa")



    elementos.append(dado)







    # 2. Pilotes hacia abajo (desde z_top = -(Hd - 100mm embebido))



    z_top = -(Hd - 100.)



    z_bot = z_top - Lp



    



    offset_x = (n_cols - 1) * Sm / 2.0



    offset_y = (m_filas - 1) * Sm / 2.0



    



    num_p = 1



    



    rec_p = 50.0  # 50mm recubrimiento



    import math



def _apply_color(ifc, element, rgb_tuple):

    # rgb_tuple is (r, g, b) between 0.0 and 1.0

    color = ifc.createIfcColourRgb(None, *rgb_tuple)

    surface_style = ifc.createIfcSurfaceStyleRendering(color, 0.0, None, None, None, None, None, None, 'NOTDEFINED')

    style = ifc.createIfcSurfaceStyle(None, 'BOTH', [surface_style])

    presentation_assignment = ifc.createIfcPresentationStyleAssignment([style])

    # For IFC4, we use RelAssociatesMaterial? No, we use StyledItem for representation

    # The actual representation items are inside the Representation context.

    # It's better to assign the style to the shape representation items directly.

    rep = element.Representation.Representations[0]

    for item in rep.Items:

        ifc.createIfcStyledItem(item, [presentation_assignment], None)



def _get_rebar_color(db_mm):

    # Color mapping based on nominal diameter

    if db_mm < 7.0: return (0.8, 0.8, 0.0)    # #2 1/4"  - Yellow

    elif db_mm < 10.0: return (0.6, 0.2, 0.8) # #3 3/8"  - Purple

    elif db_mm < 14.0: return (0.0, 0.5, 1.0) # #4 1/2"  - Blue

    elif db_mm < 17.0: return (0.0, 0.8, 0.0) # #5 5/8"  - Green

    elif db_mm < 20.0: return (1.0, 0.5, 0.0) # #6 3/4"  - Orange

    elif db_mm < 24.0: return (0.0, 1.0, 1.0) # #7 7/8"  - Cyan

    else: return (1.0, 0.0, 0.0)              # #8+ 1"+  - Red









    for i in range(n_cols):



        for j in range(m_filas):



            cx = -offset_x + i * Sm



            cy = -offset_y + j * Sm



            



            p_plac = _local_plac(cx, cy, z_bot) # Centroide



            if tipo_seccion == "Circular":



                p_sol = _cyl_local(Dp/2, Lp)



                p_plac_corner = _local_plac(cx - Dp/2, cy - Dp/2, z_bot)



            else:



                p_sol = _rect_solid(Dp, Dp, Lp)



                p_plac_corner = _local_plac(cx - Dp/2, cy - Dp/2, z_bot)



                



            pilote = ifc.createIfcPile(



                ifcopenshell.guid.new(), None, f"Pilote-{num_p}", "Pilote", None,



                p_plac_corner if tipo_seccion != "Circular" else _local_plac(cx, cy, z_bot), 



                _shape_solid(p_sol if tipo_seccion != "Circular" else _cyl_local(Dp/2, Lp)), 



                None, "BORED", None)



            _material(ifc, pilote, f"Concreto f'c={fc_pilote}MPa")



            elementos.append(pilote)



            



            # Rebar (Longitudinal)



            if n_barras_p > 0 and db_long_mm > 0:



                rad_l = db_long_mm / 2.0



                r_armado = Dp/2 - rec_p - rad_l if tipo_seccion == "Circular" else Dp/2 - rec_p - rad_l



                



                # Barras long



                for b_i in range(n_barras_p):



                    if tipo_seccion == "Circular":



                        ang = 2.0 * math.pi * b_i / n_barras_p



                        lx = cx + r_armado * math.cos(ang)



                        ly = cy + r_armado * math.sin(ang)



                    else:



                        per_face = max(1, n_barras_p // 4)



                        # Rectangular logic approximation



                        ang = 2.0 * math.pi * b_i / n_barras_p



                        lx = cx + r_armado * math.cos(ang) * 1.15



                        ly = cy + r_armado * math.sin(ang) * 1.15



                        



                    # Extruded cylinder for the straight bar



                    bar_plac = _local_plac(lx, ly, z_bot)



                    bar_sol = _cyl_local(rad_l, Lp)



                    r_bar = ifc.createIfcReinforcingBar(



                        ifcopenshell.guid.new(), None, f"Barra_Long_{num_p}_{b_i+1}",



                        None, None, bar_plac, _shape_solid(bar_sol),



                        None, None, float(db_long_mm),



                        float(math.pi*rad_l**2), float(Lp),



                        "MAIN", "TEXTURED")



                    _material(ifc, r_bar, "Acero fy=420MPa")



                    elementos.append(r_bar)



                    



            num_p += 1




    # ── Generar Refuerzos dentro de Pilotes ──────────────────────────────
    if n_barras_p > 1 and db_long_mm > 0:
        _R_bar = Dp/2. - 50. - db_est_mm/2. - db_long_mm/2.
        _r_est = db_est_mm / 2.
        _rgb_long = _get_rebar_color(db_long_mm)
        _rgb_est  = _get_rebar_color(db_est_mm)
        _s_esp = max(50., s_trans_mm) if s_trans_mm > 0 else 100.
        
        rebars_pilotes = []
        for i in range(m_filas):
            for j in range(n_cols):
                pt_x = -offset_x + j * Sm
                pt_y = -offset_y + i * Sm
                place_p_base = _local_plac(pt_x, pt_y, z_bot)
                
                # Barras long
                for b_idx in range(n_barras_p):
                    ang = 2 * math.pi * b_idx / n_barras_p
                    xb = _R_bar * math.cos(ang)
                    yb = _R_bar * math.sin(ang)
                    ax2d_r = ifc.createIfcAxis2Placement2D(_pt2(0., 0.), None)
                    perf_r = ifc.createIfcCircleProfileDef("AREA", None, ax2d_r, db_long_mm / 2.)
                    orig_r = _pt3(xb, yb, 0.)
                    ax3d_r = ifc.createIfcAxis2Placement3D(orig_r, _dir3(0., 0., 1.), _dir3(1., 0., 0.))
                    solid_r = ifc.createIfcExtrudedAreaSolid(perf_r, ax3d_r, _dir3(0.,0.,1.), Lp)
                    rep_r = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid_r])
                    prod_r = ifc.createIfcProductDefinitionShape(None, None, [rep_r])
                    
                    rebar = ifc.createIfcReinforcingBar(
                        ifcopenshell.guid.new(), None, f"Bar_P{i}{j}_{b_idx+1}",
                        f"Ø{db_long_mm:.0f}mm", None, place_p_base, prod_r, None,
                        f"fy={fc_pilote:.0f}MPa", db_long_mm/2., math.pi*(db_long_mm/2.)**2/100., Lp, "USERDEFINED", None)
                    _material(ifc, rebar, f"Acero fy=420MPa")
                    try: _apply_color(ifc, rebar, _rgb_long)
                    except Exception: pass
                    rebars_pilotes.append(rebar)
                    
                # Espiral
                def _est_circ_segs_p(z_mm):
                    n_segs = 16
                    _R_est_center = Dp/2. - 50. - db_est_mm/2.
                    pts = [( _R_est_center * math.cos(2*math.pi*k/n_segs),
                             _R_est_center * math.sin(2*math.pi*k/n_segs) ) for k in range(n_segs+1)]
                    segs = []
                    for k in range(n_segs):
                        x1, y1 = pts[k]; x2, y2 = pts[k+1]
                        dx = x2-x1; dy = y2-y1; L_seg = math.sqrt(dx**2+dy**2)
                        if L_seg < 1e-6: continue
                        ax2e = ifc.createIfcAxis2Placement2D(_pt2(0.,0.), None)
                        pfe  = ifc.createIfcCircleProfileDef("AREA", None, ax2e, _r_est)
                        orig = _pt3(x1, y1, z_mm)
                        dz   = _dir3(dx/L_seg, dy/L_seg, 0.)
                        dxr  = _dir3(-dy/L_seg, dx/L_seg, 0.)
                        ax3e = ifc.createIfcAxis2Placement3D(orig, dz, dxr)
                        sol  = ifc.createIfcExtrudedAreaSolid(pfe, ax3e, _dir3(0.,0.,1.), L_seg)
                        segs.append(sol)
                    return segs

                _all_est_circ = []
                _z = 25.
                while _z <= Lp:
                    _all_est_circ.extend(_est_circ_segs_p(_z)); _z += _s_esp
                
                if _all_est_circ:
                    _rep_e = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", _all_est_circ)
                    _prod_e = ifc.createIfcProductDefinitionShape(None, None, [_rep_e])
                    _est_bar = ifc.createIfcReinforcingBar(
                        ifcopenshell.guid.new(), None, f"Espiral_P{i}{j}",
                        f"O{db_est_mm:.0f}mm Espiral@{_s_esp:.0f}mm",
                        None, place_p_base, _prod_e, None,
                        f"fy=420MPa", _r_est, math.pi*_r_est**2/100., None, "LIGATURE", None)
                    _material(ifc, _est_bar, "Acero fy=420MPa")
                    try: _apply_color(ifc, _est_bar, _rgb_est)
                    except Exception: pass
                    rebars_pilotes.append(_est_bar)
                    
        # Agrupar TODO
        elementos.extend(rebars_pilotes)

    # ── Rotulo ICONTEC como PropertySet ─────────────────────────────────────
    _pset_diseno(ifc, dado, {
        "Empresa": "Ingenieria Estructural",
        "Proyecto": nombre_proyecto,
        "N_Plano": "PIL-001",
        "Escala": "1:20",
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "Elaboro": "Ing. Disenador",
        "Reviso": "Ing. Revisor",
        "Aprobo": "Ing. Aprobador",
        "Revision": "0",
        "Hoja": "1/1",
        "Vol_Concreto_Dado_m3": round((Bd*Ld*Hd)/1000000000., 4),
        "Vol_Concreto_Pilotes_m3": round((m_filas*n_cols * math.pi*(Dp/2)**2 * Lp)/1000000000., 4),
        "N_Pilotes": int(m_filas * n_cols),
    }, nombre="Pset_Rotulo_ICONTEC")
    ifc.createIfcRelContainedInSpatialStructure(ifcopenshell.guid.new(), None, None, None, elementos, planta)







    import io, tempfile, os



    bio = io.BytesIO()



    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f: tmp = f.name



    ifc.write(tmp)



    with open(tmp, "rb") as f: bio.write(f.read())



    os.unlink(tmp)



    bio.seek(0)



    return bio







def ifc_dado_parametrico(
    B_dado_m: float, L_dado_m: float, H_dado_m: float,
    df_pilotes, D_pilote_m: float, embeb_m: float,
    fc_dado: float, c1_cm: float, c2_cm: float,
    As_x_cm2: float = 0.0, As_y_cm2: float = 0.0,
    db_mm: float = 16.0, recub_cm: float = 7.5,
    sep_x_cm: float = 20.0, sep_y_cm: float = 20.0,
    nombre_proyecto: str = "Encepado Parametrico"
) -> "io.BytesIO":
    import math, io, tempfile, os
    import ifcopenshell
    
    if not IFC_DISPONIBLE:
        raise ImportError("ifcopenshell no disponible.")

    ifc = ifcopenshell.file(schema="IFC4")
    planta, ctx = _nueva_jerarquia(ifc, nombre_proyecto)

    Bd   = B_dado_m   * 1000.
    Ld   = L_dado_m   * 1000.
    Hd   = H_dado_m   * 1000.
    Dp   = D_pilote_m * 1000.
    emb  = embeb_m    * 1000.
    rec  = recub_cm   * 10.
    db   = db_mm
    r    = db / 2.
    lh   = max(150., 12. * db)
    sep_x = sep_x_cm * 10.
    sep_y = sep_y_cm * 10.

    elementos = []

    def _pt2(x, y):
        return ifc.createIfcCartesianPoint((float(x), float(y)))
    def _pt3(x, y, z):
        return ifc.createIfcCartesianPoint((float(x), float(y), float(z)))
    def _dir3(x, y, z):
        return ifc.createIfcDirection((float(x), float(y), float(z)))
    def _ax3(ox=0., oy=0., oz=0., zx=0., zy=0., zz=1., xx=1., xy=0., xz=0.):
        return ifc.createIfcAxis2Placement3D(_pt3(ox, oy, oz), _dir3(zx, zy, zz), _dir3(xx, xy, xz))
    def _local_plac(ox=0., oy=0., oz=0.):
        return ifc.createIfcLocalPlacement(None, _ax3(ox, oy, oz))
    def _rect_solid(w, h, depth):
        ax2 = ifc.createIfcAxis2Placement2D(_pt2(0., 0.), None)
        prof = ifc.createIfcRectangleProfileDef("AREA", None, ax2, float(w), float(h))
        return ifc.createIfcExtrudedAreaSolid(prof, _ax3(), _dir3(0.,0.,1.), float(depth))
    def _cyl_local(rad, depth):
        ax2 = ifc.createIfcAxis2Placement2D(_pt2(0., 0.), None)
        prof = ifc.createIfcCircleProfileDef("AREA", None, ax2, float(rad))
        return ifc.createIfcExtrudedAreaSolid(prof, _ax3(), _dir3(0.,0.,1.), float(depth))
    def _swept_bar(pts_3d, radius):
        ifc_pts = [_pt3(*p) for p in pts_3d]
        polyline = ifc.createIfcPolyline(ifc_pts)
        return ifc.createIfcSweptDiskSolid(polyline, float(radius), None, 0., 1.)
    def _shape_swept(solid):
        rep = ifc.createIfcShapeRepresentation(ctx, "Body", "AdvancedSweptSolid", [solid])
        return ifc.createIfcProductDefinitionShape(None, None, [rep])
    def _shape_solid(solid):
        rep = ifc.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid])
        return ifc.createIfcProductDefinitionShape(None, None, [rep])

    dado = ifc.createIfcFooting(
        ifcopenshell.guid.new(), None,
        f"Encepado {B_dado_m:.1f}x{L_dado_m:.1f}m",
        "PAD_FOOTING", None,
        _local_plac(-Bd/2., -Ld/2., -Hd),
        _shape_solid(_rect_solid(Bd, Ld, Hd)),
        None, "PAD_FOOTING")
    _material(ifc, dado, f"Concreto f'c={fc_dado:.0f}MPa")
    elementos.append(dado)

    col = ifc.createIfcColumn(
        ifcopenshell.guid.new(), None,
        f"Col {c1_cm:.0f}x{c2_cm:.0f}cm", None, None,
        _local_plac(-c1_cm*5., -c2_cm*5., 0.),
        _shape_solid(_rect_solid(c1_cm*10., c2_cm*10., 1000.)),
        None, None)
    elementos.append(col)

    z_top_pil = -(Hd - emb)
    L_pil = 3000.
    for i_p, row in df_pilotes.iterrows():
        px = row["X [m]"] * 1000.
        py = row["Y [m]"] * 1000.
        pil = ifc.createIfcPile(
            ifcopenshell.guid.new(), None,
            str(row["ID"]), "Pilote", None,
            _local_plac(px - Dp/2., py - Dp/2., z_top_pil - L_pil),
            _shape_solid(_cyl_local(Dp/2., L_pil)),
            None, "BORED", None)
        _material(ifc, pil, "Concreto Pilote")
        elementos.append(pil)

    z_inf = -(Hd - emb - 30.)
    bar_len_x = Bd - 2. * rec
    def _hook_path_x(bar_len, hook_len):
        return [(0.,0.,hook_len), (0.,0.,0.), (bar_len,0.,0.), (bar_len,0.,hook_len)]

    y_cur = -Ld/2. + rec
    bix = 0
    while y_cur <= Ld/2. - rec + 1.:
        plac_bx = _local_plac(-Bd/2. + rec, y_cur, z_inf)
        pts = _hook_path_x(bar_len_x, lh)
        sol_bx = _swept_bar(pts, r)
        pds_bx = _shape_swept(sol_bx)
        rebar = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, f"BX-{bix+1}",
            None, None, plac_bx, pds_bx,
            f"BX{bix+1}", None, float(db),
            float(math.pi * r * r), float(bar_len_x + 2*lh),
            "MAIN", "TEXTURED")
        _material(ifc, rebar, "Acero fy=420MPa")
        elementos.append(rebar)
        y_cur += sep_y
        bix += 1

    z_inf_y = z_inf + db + 5.
    bar_len_y = Ld - 2. * rec
    def _hook_path_y(bar_len, hook_len):
        return [(0.,0.,hook_len), (0.,0.,0.), (0.,bar_len,0.), (0.,bar_len,hook_len)]

    x_cur = -Bd/2. + rec
    biy = 0
    while x_cur <= Bd/2. - rec + 1.:
        plac_by = _local_plac(x_cur, -Ld/2. + rec, z_inf_y)
        pts_y = _hook_path_y(bar_len_y, lh)
        sol_by = _swept_bar(pts_y, r)
        pds_by = _shape_swept(sol_by)
        rebar_y = ifc.createIfcReinforcingBar(
            ifcopenshell.guid.new(), None, f"BY-{biy+1}",
            None, None, plac_by, pds_by,
            f"BY{biy+1}", None, float(db),
            float(math.pi * r * r), float(bar_len_y + 2*lh),
            "MAIN", "TEXTURED")
        _material(ifc, rebar_y, "Acero fy=420MPa")
        elementos.append(rebar_y)
        x_cur += sep_x
        biy += 1

    if Hd > 600.:
        n_capas = int((Hd - 200.) / 300.)
        db_piel = 9.5
        r_piel  = db_piel / 2.
        for ci in range(1, n_capas + 1):
            z_piel = -Hd + 100. + ci * 300.
            _piel_corners = [
                ((-Bd/2 + rec*1.5, -Ld/2 + rec*1.5, z_piel), ( Bd/2 - rec*1.5, -Ld/2 + rec*1.5, z_piel)),
                (( Bd/2 - rec*1.5, -Ld/2 + rec*1.5, z_piel), ( Bd/2 - rec*1.5,  Ld/2 - rec*1.5, z_piel)),
                (( Bd/2 - rec*1.5,  Ld/2 - rec*1.5, z_piel), (-Bd/2 + rec*1.5,  Ld/2 - rec*1.5, z_piel)),
                ((-Bd/2 + rec*1.5,  Ld/2 - rec*1.5, z_piel), (-Bd/2 + rec*1.5, -Ld/2 + rec*1.5, z_piel)),
            ]
            for (x0,y0,z0),(x1,y1,z1) in _piel_corners:
                seg = [(0.,0.,0.), (x1-x0, y1-y0, z1-z0)]
                sol_sk = _swept_bar(seg, r_piel)
                pds_sk = _shape_swept(sol_sk)
                sk_bar = ifc.createIfcReinforcingBar(
                    ifcopenshell.guid.new(), None, f"Piel-c{ci}",
                    None, None, _local_plac(x0, y0, z0), pds_sk,
                    None, None, float(db_piel),
                    float(math.pi*r_piel*r_piel), float(math.sqrt((x1-x0)**2+(y1-y0)**2)),
                    "LIGATURE", "PLAIN")
                elementos.append(sk_bar)

    ifc.createIfcRelContainedInSpatialStructure(ifcopenshell.guid.new(), None, None, None, elementos, planta)

    return _guardar_a_bytesio(ifc)
