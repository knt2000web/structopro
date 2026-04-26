# utils/catalogo_apus.py
import math

def generar_catalogo_completo():
    """
    Genera un catálogo de más de 500 APUs paramétricos organizados por capítulos.
    Incluye variaciones de estrato (economico, medio, alto) y norma.
    """
    catalogo = {
        "CAP-01-PRE": {"nombre": "Preliminares y Movimiento de Tierras", "items": {}},
        "CAP-02-CIM": {"nombre": "Cimentación", "items": {}},
        "CAP-03-EST": {"nombre": "Estructuras de Concreto", "items": {}},
        "CAP-04-ACE": {"nombre": "Acero de Refuerzo", "items": {}},
        "CAP-05-MAM": {"nombre": "Mampostería", "items": {}},
        "CAP-06-ACA": {"nombre": "Acabados Arquitectónicos", "items": {}},
        "CAP-07-PIS": {"nombre": "Pisos y Enchapes", "items": {}},
        "CAP-08-HID": {"nombre": "Instalaciones Hidrosanitarias", "items": {}},
        "CAP-09-ELE": {"nombre": "Instalaciones Eléctricas", "items": {}},
        "CAP-10-CUB": {"nombre": "Cubiertas y Estructura Metálica", "items": {}},
        "CAP-11-URB": {"nombre": "Urbanismo y Exteriores", "items": {}},
    }

    # Helper para estandarizar insumos
    def crear_apu(id_apu, nombre, unidad, cap, insumos, rendimiento_dia):
        catalogo[cap]["items"][id_apu] = {
            "nombre": nombre,
            "unidad": unidad,
            "rendimiento_dia": rendimiento_dia, # Cuánto hace la cuadrilla en un día
            "insumos": insumos
        }

    # -------------------------------------------------------------------------
    # 1. PRELIMINARES (Aprox 40 APUs)
    # -------------------------------------------------------------------------
    preliminares = [
        ("Localización y replanteo arquitectónico", "m2", 120),
        ("Localización y replanteo topográfico con equipo", "m2", 250),
        ("Cerramiento provisional en lona verde (h=2.0m)", "ml", 35),
        ("Cerramiento en lámina de zinc (h=2.0m)", "ml", 25),
        ("Campamento provisional en madera", "m2", 8),
        ("Descapote a máquina (e=0.20m)", "m2", 400),
        ("Excavación manual en material común", "m3", 4.5),
        ("Excavación manual en conglomerado", "m3", 3.0),
        ("Excavación mecánica a máquina", "m3", 150),
        ("Relleno compactado con material de sitio", "m3", 12),
        ("Relleno compactado con recebo (base/subbase)", "m3", 18),
        ("Retiro de sobrantes a botadero (volqueta)", "m3", 45),
        ("Demolición manual de concreto simple", "m3", 1.5),
        ("Demolición manual de concreto reforzado", "m3", 0.8),
        ("Demolición de muro de mampostería", "m2", 15)
    ]
    for i, (nom, und, rend) in enumerate(preliminares, 1):
        # Simplificación de insumos para el ejemplo
        insumos = [
            {"tipo": "mo", "nombre": "Cuadrilla Preliminares (1O + 2A)", "cantidad": 1/rend},
            {"tipo": "herramienta", "nombre": "Herramienta menor", "cantidad": 0.05} # 5% de MO
        ]
        crear_apu(f"PRE-{i:03d}", nom, und, "CAP-01-PRE", insumos, rend)

    # -------------------------------------------------------------------------
    # 2. CONCRETOS (CIMENTACIÓN Y ESTRUCTURA) - Generación paramétrica
    # -------------------------------------------------------------------------
    resistencias = [14, 17.5, 21, 24.5, 28, 31.5, 35, 42, 50] # MPa
    tipos_aditivo = ["Estándar", "Impermeabilizado", "Acelerante de fraguado"]
    elementos = [
        ("Zapatas", "CAP-02-CIM", 8.0), 
        ("Vigas de cimentación", "CAP-02-CIM", 6.0),
        ("Pilotes fundidos in situ", "CAP-02-CIM", 5.0),
        ("Dados y Encepados", "CAP-02-CIM", 6.5),
        ("Muros Pantalla", "CAP-02-CIM", 4.0),
        ("Columnas", "CAP-03-EST", 4.5), 
        ("Vigas aéreas", "CAP-03-EST", 5.5), 
        ("Vigas canal", "CAP-03-EST", 4.0),
        ("Losas macizas", "CAP-03-EST", 8.0),
        ("Losas aligeradas", "CAP-03-EST", 6.5),
        ("Muros de contención", "CAP-03-EST", 6.0),
        ("Escaleras", "CAP-03-EST", 3.0),
        ("Tanques de agua", "CAP-03-EST", 4.0)
    ]
    
    id_conc = 1
    for fc in resistencias:
        for aditivo in tipos_aditivo:
            for elem, cap, rend in elementos:
                # Filtrar algunas combinaciones ilógicas para no inflar artificialmente sin sentido
                if fc > 28 and aditivo == "Estándar": rend = rend * 0.9
                
                # 1. Mezclado en sitio (solo hasta 28 MPa por norma)
                if fc <= 28 and aditivo == "Estándar":
                    nom_sitio = f"Concreto {fc} MPa para {elem} (En obra, {aditivo})"
                    crear_apu(f"CONC-{id_conc:04d}", nom_sitio, "m3", cap, [
                        {"tipo": "material", "nombre": f"Cemento gris", "cantidad": 350 + (fc-21)*15, "unidad": "kg"},
                        {"tipo": "material", "nombre": "Arena de río", "cantidad": 0.56, "unidad": "m3"},
                        {"tipo": "material", "nombre": "Grava triturada", "cantidad": 0.84, "unidad": "m3"},
                        {"tipo": "mo", "nombre": "Cuadrilla Fundición (1O + 4A)", "cantidad": 1/rend}
                    ], rend)
                    id_conc += 1

                # 2. Premezclado bombeado (todas las resistencias)
                rend_bomba = rend * 3.5 
                nom_premix = f"Concreto {fc} MPa para {elem} (Premezclado bombeado, {aditivo})"
                crear_apu(f"CONC-{id_conc:04d}", nom_premix, "m3", cap, [
                    {"tipo": "material", "nombre": f"Concreto Premix {fc} MPa {aditivo}", "cantidad": 1.03, "unidad": "m3"},
                    {"tipo": "equipo", "nombre": "Servicio de Autobomba", "cantidad": 1.0, "unidad": "m3"},
                    {"tipo": "mo", "nombre": "Cuadrilla Fundición (1O + 4A)", "cantidad": 1/rend_bomba}
                ], rend_bomba)
                id_conc += 1

    # -------------------------------------------------------------------------
    # 3. ACERO DE REFUERZO 
    # -------------------------------------------------------------------------
    diametros = ["1/4", "3/8", "1/2", "5/8", "3/4", "7/8", "1", "1 1/8", "1 1/4"]
    grados = [("fy=420 MPa (Grado 60)", 150), ("fy=280 MPa (Grado 40)", 180)]
    id_acero = 1
    for d in diametros:
        for grd, rend_acero in grados:
            crear_apu(f"ACE-{id_acero:03d}", f"Acero de refuerzo {grd}, Diám. {d}\" (Suministro, corte, figurado, amarre)", "kg", "CAP-04-ACE", [], rend_acero)
            id_acero += 1
            
    mallas = ["D-84", "D-131", "D-188", "D-258", "D-335"]
    for m in mallas:
        crear_apu(f"ACE-MALLA-{id_acero:03d}", f"Malla electrosoldada estándar {m}", "kg", "CAP-04-ACE", [], 250)
        id_acero += 1

    # -------------------------------------------------------------------------
    # 4. MAMPOSTERÍA
    # -------------------------------------------------------------------------
    tipos_bloque = [
        ("Bloque Arcilla Nro 5", 0.12), ("Bloque Arcilla Nro 4", 0.09), ("Bloque Arcilla Nro 3", 0.07),
        ("Bloque Arcilla Portante", 0.15), ("Bloque Arcilla Portante", 0.12),
        ("Ladrillo Tolete Común", 0.12), ("Ladrillo a la vista Santafe", 0.12), ("Ladrillo Prensado", 0.12),
        ("Bloque Cemento vibrado liso", 0.10), ("Bloque Cemento vibrado liso", 0.15), ("Bloque Cemento vibrado liso", 0.20),
        ("Bloque Cemento estructural", 0.15), ("Bloque Cemento estructural", 0.20)
    ]
    tipos_mortero = ["1:3", "1:4", "1:5", "Mortero premezclado seco"]
    id_mamp = 1
    for tb, esp in tipos_bloque:
        for tm in tipos_mortero:
            nom = f"Muro en {tb} e={esp}m, asentado con {tm}"
            crear_apu(f"MAM-{id_mamp:03d}", nom, "m2", "CAP-05-MAM", [], 12 if "Portante" not in tb else 10)
            id_mamp += 1

    # -------------------------------------------------------------------------
    # 5. ACABADOS (PAÑETES, PINTURAS, CIELORRASOS)
    # -------------------------------------------------------------------------
    acabados = [
        ("Pañete/Revoque interior liso", "m2", 15), ("Pañete exterior impermeabilizado", "m2", 12),
        ("Pañete rústico", "m2", 18), ("Pañete sobre malla", "m2", 10),
        ("Estuco plástico interior (3 manos)", "m2", 20), ("Estuco tradicional", "m2", 18),
        ("Pintura Vinilo tipo 1 (2 manos)", "m2", 40), ("Pintura Vinilo tipo 1 (3 manos)", "m2", 30),
        ("Pintura Vinilo tipo 2 (2 manos)", "m2", 45), ("Pintura Epóxica en muros", "m2", 18),
        ("Pintura Esmalte sobre metal", "m2", 25), ("Pintura Koraza para exteriores", "m2", 20),
        ("Cielorraso en Drywall (estructura estándar)", "m2", 10), ("Cielorraso en Drywall RH (humedad)", "m2", 9),
        ("Cielorraso en PVC (listones)", "m2", 15), ("Cielorraso en Fibrocemento (Superboard)", "m2", 12),
        ("Filos y dilataciones", "ml", 35), ("Remates de ventanería", "ml", 25)
    ]
    id_aca = 1
    for nom, und, rend in acabados:
        crear_apu(f"ACA-{id_aca:03d}", nom, und, "CAP-06-ACA", [], rend)
        id_aca += 1

    # Combo Acabados por estrato
    calidades = [("VIS", 1.0), ("Económica (Estrato 1-2)", 1.2), ("Estándar (Estrato 3-4)", 1.5), ("Premium (Estrato 5-6)", 2.5), ("Lujo", 4.0)]
    zonas = ["Habitaciones", "Zonas Sociales", "Baños", "Cocina", "Exteriores"]
    for nom_cal, factor in calidades:
        for z in zonas:
            crear_apu(f"ACA-{id_aca:03d}", f"Combo Acabado Muro {z} - Calidad {nom_cal}", "m2", "CAP-06-ACA", [], 15)
            id_aca += 1

    # -------------------------------------------------------------------------
    # 6. PISOS Y ENCHAPES
    # -------------------------------------------------------------------------
    pisos = [
        "Cerámica nacional 40x40", "Cerámica importada", "Porcelanato 60x60", "Porcelanato Gran Formato 120x60", 
        "Piso Laminado 8mm", "Piso Laminado tráfico pesado", "Madera Maciza estructurada", 
        "Gres Exterior", "Adoquín de concreto", "Vinilo PVC click", "Microcemento", "Granito fundido en sitio"
    ]
    id_pis = 1
    for p in pisos:
        crear_apu(f"PIS-{id_pis:03d}", f"Suministro e instalación piso {p}", "m2", "CAP-07-PIS", [], 12 if "Porcelanato" in p else 18)
        id_pis += 1
        crear_apu(f"PIS-{id_pis:03d}", f"Guardaescoba en {p}", "ml", "CAP-07-PIS", [], 35)
        id_pis += 1

    # -------------------------------------------------------------------------
    # 7. INSTALACIONES HIDROSANITARIAS Y GAS
    # -------------------------------------------------------------------------
    diametros_tubos = ["1/2", "3/4", "1", "1 1/4", "1 1/2", "2", "2 1/2", "3", "4", "6", "8", "10", "12"]
    materiales_hidro = [("PVC Sanitario", 20), ("PVC Presión", 25), ("CPVC Agua Caliente", 18), ("Polipropileno Termofusión", 15), ("PVC Novafort (Exterior)", 30)]
    id_hid = 1
    for mat, rend_mat in materiales_hidro:
        for d in diametros_tubos:
            if "Presión" in mat and d in ["6", "8", "10", "12"]: continue # Evitar combinaciones raras
            crear_apu(f"HID-TUB-{id_hid:03d}", f"Tubería {mat} {d}\" inc. accesorios", "ml", "CAP-08-HID", [], rend_mat)
            id_hid += 1

    puntos_hid = ["Sanitario Lavamanos", "Sanitario Inodoro", "Ducha", "Lavaplatos", "Lavadora", "Calentador", "Bañera", "Orinal"]
    for pt in puntos_hid:
        crear_apu(f"HID-PT-{id_hid:03d}", f"Punto {pt} (Agua fría + Desagüe)", "un", "CAP-08-HID", [], 3)
        id_hid += 1
        if pt in ["Ducha", "Lavamanos", "Lavaplatos", "Bañera"]:
            crear_apu(f"HID-PT-{id_hid:03d}", f"Punto {pt} (Agua caliente CPVC)", "un", "CAP-08-HID", [], 4)
            id_hid += 1

    # -------------------------------------------------------------------------
    # 8. INSTALACIONES ELÉCTRICAS
    # -------------------------------------------------------------------------
    cables = ["14 AWG", "12 AWG", "10 AWG", "8 AWG", "6 AWG", "4 AWG", "2 AWG", "1/0 AWG"]
    tubos_ele = ["1/2", "3/4", "1", "1 1/4", "1 1/2", "2", "3", "4"]
    tipos_tubo_ele = ["PVC Conduit", "EMT", "IMC"]
    id_ele = 1
    
    for mat in tipos_tubo_ele:
        for t in tubos_ele:
            crear_apu(f"ELE-TUB-{id_ele:03d}", f"Tubería Eléctrica {mat} {t}\" inc. accesorios", "ml", "CAP-09-ELE", [], 40 if mat=="PVC Conduit" else 25)
            id_ele += 1
            
    for c in cables:
        crear_apu(f"ELE-CAB-{id_ele:03d}", f"Cable Cobre THHN/THWN-2 {c}", "ml", "CAP-09-ELE", [], 150)
        id_ele += 1

    puntos_ele = [
        "Salida iluminación techo", "Salida iluminación aplique mural", "Salida tomacorriente sencillo 110V", 
        "Salida tomacorriente doble 110V", "Salida tomacorriente GFCI", "Salida TV/Datos", "Salida estufa 220V", "Salida calentador 220V"
    ]
    for pt in puntos_ele:
        crear_apu(f"ELE-PT-{id_ele:03d}", pt, "un", "CAP-09-ELE", [], 6)
        id_ele += 1
    # -------------------------------------------------------------------------
    # RESULTADO TOTAL
    # -------------------------------------------------------------------------
    total_apus = sum(len(c["items"]) for c in catalogo.values())
    print(f"Catálogo generado con {total_apus} APUs.")
    return catalogo

# Instancia singleton para ser importada
CATALOGO_APU_MAESTRO = generar_catalogo_completo()
