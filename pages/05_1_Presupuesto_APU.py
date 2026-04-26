import streamlit as st
import pandas as pd
import io
import sys
import os

# Asegurar que utils está en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))
try:
    from catalogo_apus import CATALOGO_APU_MAESTRO
except ImportError:
    CATALOGO_APU_MAESTRO = {}

st.set_page_config(page_title="Presupuesto APU Pro", page_icon="🏢", layout="wide")

# ─── IDIOMA ────────────────────────────────────────────────────────────────
lang = st.session_state.get("idioma", "Español")
def _t(es, en):
    return en if lang == "English" else es

st.title(_t("🏢 Presupuesto Avanzado (APU Normativo)", "🏢 Advanced Budgeting (Normative APU)"))

# ─── INICIALIZAR ESTADO DEL PRESUPUESTO ────────────────────────────────────
if "presupuesto_actual" not in st.session_state:
    st.session_state.presupuesto_actual = []

# ─── CONFIGURACION GLOBAL ──────────────────────────────────────────────────
_cfg = st.session_state.get("apu_config", {})
if not _cfg:
    st.warning(_t(
        "⚠️ No has configurado los precios base globales. Ve a 'APU Mercado' primero para establecer precios de cemento, acero y mano de obra.",
        "⚠️ Base prices not configured. Go to 'APU Market' first to set cement, steel and labor prices."
    ))

moneda = _cfg.get("moneda", "COP")
mo_dia = _cfg.get("costo_dia_mo", 100000.0)
aiu = _cfg.get("pct_aui", 0.30)

st.markdown("---")

col_cat, col_pres = st.columns([1, 1.5])

# =============================================================================
# PANEL IZQUIERDO: CATÁLOGO DE APUs
# =============================================================================
with col_cat:
    st.subheader(_t("📚 Catálogo Maestro", "📚 Master Catalog"))
    st.caption(f"Total ítems disponibles: {sum(len(c['items']) for c in CATALOGO_APU_MAESTRO.values())}")
    
    capitulos = {k: v["nombre"] for k, v in CATALOGO_APU_MAESTRO.items()}
    cap_sel = st.selectbox(_t("Seleccionar Capítulo", "Select Chapter"), list(capitulos.keys()), format_func=lambda x: f"{x} - {capitulos[x]}")
    
    st.markdown("##### Ítems del capítulo")
    items_cap = CATALOGO_APU_MAESTRO[cap_sel]["items"]
    
    # Buscador interno
    search = st.text_input(_t("🔍 Buscar ítem", "🔍 Search item"), "").lower()
    
    for id_apu, data in items_cap.items():
        if search and search not in data["nombre"].lower() and search not in id_apu.lower():
            continue
            
        with st.expander(f"{id_apu} | {data['nombre']} ({data['unidad']})"):
            st.markdown(f"**Rendimiento:** {data['rendimiento_dia']} {data['unidad']}/día")
            
            # Estimación rápida de costo base usando la configuración global
            # Costo MO estimado: (costo cuadrilla / rendimiento)
            costo_mo_estimado = mo_dia / data['rendimiento_dia'] if data['rendimiento_dia'] > 0 else 0
            
            st.caption(f"Costo MO ref: ${costo_mo_estimado:,.0f} {moneda}/{data['unidad']}")
            
            with st.form(key=f"add_{id_apu}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    cant = st.number_input("Cantidad", min_value=0.1, value=1.0, step=1.0, key=f"q_{id_apu}")
                with c2:
                    # Permitir override del precio unitario (para materiales que no están en config global)
                    precio_unit = st.number_input("Precio Unit. Total", value=costo_mo_estimado*2.5, step=1000.0, key=f"p_{id_apu}") # X2.5 como estimación rápida de material
                
                if st.form_submit_button(_t("➕ Agregar al Presupuesto", "➕ Add to Budget")):
                    st.session_state.presupuesto_actual.append({
                        "Capítulo": capitulos[cap_sel],
                        "ID": id_apu,
                        "Descripción": data["nombre"],
                        "Unidad": data["unidad"],
                        "Cantidad": cant,
                        "Vr. Unitario": precio_unit,
                        "Subtotal": cant * precio_unit
                    })
                    st.rerun()

# =============================================================================
# PANEL DERECHO: PRESUPUESTO ACTUAL
# =============================================================================
with col_pres:
    st.subheader(_t("📊 Presupuesto del Proyecto", "📊 Project Budget"))
    
    if not st.session_state.presupuesto_actual:
        st.info("El presupuesto está vacío. Agrega ítems desde el catálogo.")
    else:
        df_pres = pd.DataFrame(st.session_state.presupuesto_actual)
        
        # Agrupar por capítulo para mostrar
        total_directo = df_pres["Subtotal"].sum()
        vr_aiu = total_directo * aiu
        total_proyecto = total_directo + vr_aiu
        
        # Editor interactivo: Permite editar cantidades y eliminar filas (usando el icono de basura a la izquierda)
        st.markdown("*(Puedes editar la **Cantidad**, el **Vr. Unitario**, o seleccionar una fila y presionar la tecla **Suprimir / Delete** para borrarla)*")
        
        column_config = {
            "Subtotal": st.column_config.NumberColumn("Subtotal", format="$%d", disabled=True),
            "Vr. Unitario": st.column_config.NumberColumn("Vr. Unitario", format="$%d"),
            "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.2f"),
            "Capítulo": st.column_config.TextColumn("Capítulo", disabled=True),
            "ID": st.column_config.TextColumn("ID", disabled=True),
            "Descripción": st.column_config.TextColumn("Descripción", disabled=True),
            "Unidad": st.column_config.TextColumn("Unidad", disabled=True)
        }
        
        edited_df = st.data_editor(
            df_pres[["Capítulo", "ID", "Descripción", "Unidad", "Cantidad", "Vr. Unitario", "Subtotal"]],
            use_container_width=True,
            hide_index=False,
            num_rows="dynamic",
            column_config=column_config,
            key="presupuesto_editor"
        )
        
        # Sincronizar cambios en el editor con la sesión (si eliminan o editan)
        edited_df["Subtotal"] = edited_df["Cantidad"] * edited_df["Vr. Unitario"]
        st.session_state.presupuesto_actual = edited_df.to_dict('records')
        
        # --- CONTROLES ADICIONALES (AIU Y GUARDADO) ---
        st.markdown("---")
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1:
            st.write("⚙️ **Ajuste Local de A.I.U.**")
            aiu_local = st.number_input("Porcentaje A.I.U. (%)", min_value=0.0, max_value=100.0, value=float(aiu*100), step=1.0)
            aiu = aiu_local / 100.0
        with col_ctrl2:
            st.write("💾 **Guardar Progreso**")
            import json
            btn_save = st.download_button("Descargar Presupuesto (JSON)", data=json.dumps(st.session_state.presupuesto_actual), file_name="mi_presupuesto.json", mime="application/json", use_container_width=True)
        with col_ctrl3:
            st.write("📂 **Cargar Progreso**")
            uploaded_file = st.file_uploader("Subir archivo .json", type="json", label_visibility="collapsed")
            if uploaded_file is not None:
                st.session_state.presupuesto_actual = json.load(uploaded_file)
                st.rerun()

        # Recalcular totales con el df editado y el nuevo AIU
        total_directo = edited_df["Subtotal"].sum()
        vr_aiu = total_directo * aiu
        total_proyecto = total_directo + vr_aiu
        
        # Mostrar panel de totales con HTML/CSS responsivo
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; text-align: center; background-color: #1e293b; padding: 15px 10px; border-radius: 8px; margin-top: 15px; border: 1px solid #334155;">
            <div style="flex: 1; border-right: 1px solid #334155;">
                <p style="margin: 0; color: #94a3b8; font-size: 13px;">Costo Directo</p>
                <h4 style="margin: 5px 0 0 0; color: #38bdf8; font-size: 20px; font-weight: 600;">${total_directo:,.0f}</h4>
            </div>
            <div style="flex: 1; border-right: 1px solid #334155;">
                <p style="margin: 0; color: #94a3b8; font-size: 13px;">A.I.U. ({aiu*100:.0f}%)</p>
                <h4 style="margin: 5px 0 0 0; color: #facc15; font-size: 20px; font-weight: 600;">${vr_aiu:,.0f}</h4>
            </div>
            <div style="flex: 1;">
                <p style="margin: 0; color: #94a3b8; font-size: 13px;">Total Proyecto</p>
                <h4 style="margin: 5px 0 0 0; color: #10b981; font-size: 22px; font-weight: bold;">${total_proyecto:,.0f} <span style="font-size:14px;color:#64748b;">{moneda}</span></h4>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🗑️ Vaciar Presupuesto Completo", type="secondary"):
                st.session_state.presupuesto_actual = []
                st.rerun()
                
        with col_btn2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                worksheet = writer.sheets.setdefault('Presupuesto_Pro', workbook.add_worksheet('Presupuesto_Pro'))
                
                # Definir formatos profesionales
                title_fmt = workbook.add_format({
                    'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
                    'fg_color': '#16365C', 'font_color': 'white', 'border': 1
                })
                subtitle_fmt = workbook.add_format({
                    'bold': True, 'font_size': 11, 'align': 'right', 'fg_color': '#DCE6F1', 'border': 1
                })
                value_fmt = workbook.add_format({
                    'font_size': 11, 'align': 'left', 'border': 1
                })
                header_fmt = workbook.add_format({
                    'bold': True, 'text_wrap': True, 'valign': 'vcenter', 
                    'fg_color': '#16365C', 'font_color': 'white', 
                    'border': 1, 'align': 'center', 'font_size': 10
                })
                capitulo_fmt = workbook.add_format({
                    'bold': True, 'fg_color': '#B8CCE4', 'border': 1, 'font_size': 11, 'valign': 'vcenter'
                })
                money_fmt = workbook.add_format({'num_format': '"$"#,##0.00', 'border': 1, 'font_size': 10, 'valign': 'vcenter'})
                num_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'center', 'border': 1, 'font_size': 10, 'valign': 'vcenter'})
                text_fmt = workbook.add_format({'border': 1, 'font_size': 10, 'valign': 'vcenter', 'text_wrap': True})
                text_center_fmt = workbook.add_format({'border': 1, 'font_size': 10, 'valign': 'vcenter', 'align': 'center'})
                total_fmt = workbook.add_format({
                    'bold': True, 'bg_color': '#DCE6F1', 'num_format': '"$"#,##0.00', 'border': 1, 'font_size': 11
                })
                gran_total_fmt = workbook.add_format({
                    'bold': True, 'bg_color': '#16365C', 'font_color': 'white', 'num_format': '"$"#,##0.00', 'border': 1, 'font_size': 12
                })
                logo_fmt = workbook.add_format({
                    'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_color': '#aaaaaa'
                })

                # Datos del Proyecto (desde el sidebar)
                p_nombre = st.session_state.get("project_name", "Proyecto Sin Nombre")
                p_propietario = st.session_state.get("project_owner", "Cliente No Especificado")
                p_direccion = st.session_state.get("project_address", "Dirección No Especificada")
                import datetime
                fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")

                # Membrete Superior con Espacio para Logos
                worksheet.set_row(0, 30)
                worksheet.set_row(1, 30)
                worksheet.set_row(2, 30)
                worksheet.merge_range('A1:B3', _t('[ LOGO CLIENTE ]', '[ CLIENT LOGO ]'), logo_fmt)
                worksheet.merge_range('C1:E1', _t('FORMATO', 'FORMAT'), title_fmt)
                worksheet.merge_range('C2:E3', _t('PRESUPUESTO GENERAL', 'GENERAL BUDGET'), title_fmt)
                worksheet.merge_range('F1:G3', _t('[ LOGO EMPRESA CONTRATISTA ]', '[ CONTRACTOR LOGO ]'), logo_fmt)
                
                # Bloque de información
                worksheet.write('A4', _t('PROYECTO:', 'PROJECT:'), subtitle_fmt)
                worksheet.merge_range('B4:G4', p_nombre, value_fmt)
                
                worksheet.write('A5', _t('CONTRATANTE:', 'CLIENT:'), subtitle_fmt)
                worksheet.merge_range('B5:D5', p_propietario, value_fmt)
                
                worksheet.write('E5', _t('FECHA:', 'DATE:'), subtitle_fmt)
                worksheet.merge_range('F5:G5', fecha_hoy, value_fmt)
                
                worksheet.write('A6', _t('CONTRATISTA:', 'CONTRACTOR:'), subtitle_fmt)
                worksheet.merge_range('B6:D6', '', value_fmt)
                
                worksheet.write('E6', _t('MONEDA:', 'CURRENCY:'), subtitle_fmt)
                worksheet.merge_range('F6:G6', moneda, value_fmt)

                # Ajustar anchos de columna
                worksheet.set_column('A:A', 14) # ID
                worksheet.set_column('B:B', 50) # Descripcion
                worksheet.set_column('C:C', 8)  # Unidad
                worksheet.set_column('D:D', 12) # Cantidad
                worksheet.set_column('E:E', 18) # Precio Unit
                worksheet.set_column('F:F', 20) # Valor Total
                worksheet.set_column('G:G', 12) # Incidencia

                # Escribir Cabeceras de Tabla
                headers = [
                    _t('ÍTEM / CÓDIGO', 'ITEM / CODE'), 
                    _t('DESCRIPCIÓN DE LA ACTIVIDAD', 'ACTIVITY DESCRIPTION'), 
                    _t('UND', 'UNIT'), 
                    _t('CANTIDAD', 'QUANTITY'), 
                    _t('VR. UNITARIO', 'UNIT PRICE'), 
                    _t('VR. TOTAL', 'TOTAL VALUE'), 
                    _t('INCIDENCIA', 'INCIDENCE')
                ]
                for col_num, value in enumerate(headers):
                    worksheet.write(8, col_num, value, header_fmt)
                worksheet.set_row(8, 30) # Fila más alta para los títulos

                # Agrupar por capítulos y escribir
                row = 9
                capitulos_agrupados = df_pres.groupby('Capítulo')
                
                for nombre_cap, items_cap in capitulos_agrupados:
                    # Fila del capítulo (Fondo gris/azul)
                    worksheet.merge_range(row, 0, row, 6, f'CAPÍTULO: {nombre_cap.upper()}', capitulo_fmt)
                    worksheet.set_row(row, 22)
                    row += 1
                    
                    subtotal_cap = 0
                    for _, fila in items_cap.iterrows():
                        worksheet.write(row, 0, fila['ID'], text_center_fmt)
                        worksheet.write(row, 1, fila['Descripción'], text_fmt)
                        worksheet.write(row, 2, fila['Unidad'], text_center_fmt)
                        worksheet.write_number(row, 3, float(fila['Cantidad']), num_fmt)
                        worksheet.write_number(row, 4, float(fila['Vr. Unitario']), money_fmt)
                        worksheet.write_number(row, 5, float(fila['Subtotal']), money_fmt)
                        
                        # Incidencia % respecto al total directo
                        incidencia = float(fila['Subtotal']) / total_directo if total_directo > 0 else 0
                        worksheet.write_number(row, 6, incidencia, workbook.add_format({'num_format': '0.00%', 'border': 1, 'align': 'center'}))
                        
                        subtotal_cap += fila['Subtotal']
                        row += 1
                        
                    # Subtotal del capítulo
                    worksheet.merge_range(row, 0, row, 4, f'SUBTOTAL {nombre_cap.upper()}', total_fmt)
                    worksheet.write_number(row, 5, subtotal_cap, total_fmt)
                    worksheet.write_string(row, 6, '', total_fmt)
                    row += 2 # Espacio en blanco antes del siguiente cap

                # Escribir Totales Finales (Costo Directo, AIU, Total)
                row += 1
                worksheet.write_string(row, 3, _t('COSTO DIRECTO', 'DIRECT COST'), total_fmt)
                worksheet.merge_range(row, 3, row, 4, _t('COSTO DIRECTO', 'DIRECT COST'), total_fmt)
                worksheet.write_number(row, 5, total_directo, total_fmt)
                worksheet.write_string(row, 6, '', total_fmt)
                row += 1
                
                # Desglose AIU (Administración, Imprevistos, Utilidad en renglones separados pero resumidos)
                worksheet.merge_range(row, 3, row, 4, _t(f'A.I.U. GLOBAL ({aiu*100:.0f}%)', f'GLOBAL A.I.U. ({aiu*100:.0f}%)'), total_fmt)
                worksheet.write_number(row, 5, vr_aiu, total_fmt)
                worksheet.write_string(row, 6, '', total_fmt)
                row += 1
                
                # Total Proyecto
                worksheet.merge_range(row, 3, row, 4, _t('VALOR TOTAL DEL PROYECTO', 'TOTAL PROJECT VALUE'), gran_total_fmt)
                worksheet.write_number(row, 5, total_proyecto, gran_total_fmt)
                worksheet.write_string(row, 6, '', gran_total_fmt)
                row += 1
                
                # --- HOJAS INDIVIDUALES DE APU ---
                apu_header_fmt = workbook.add_format({
                    'bold': True, 'align': 'center', 'valign': 'vcenter', 'fg_color': '#16365C', 'font_color': 'white', 'border': 1
                })
                apu_sub_fmt = workbook.add_format({
                    'bold': True, 'bg_color': '#DCE6F1', 'border': 1, 'align': 'left'
                })
                apu_col_fmt = workbook.add_format({
                    'bold': True, 'bg_color': '#B8CCE4', 'border': 1, 'align': 'center', 'font_size': 9
                })
                
                # Cargar configuración global para cálculos
                cfg = st.session_state.get("apu_config", {})
                costo_dia_mo = cfg.get("costo_dia_mo", 82500)
                herramienta_pct = cfg.get("pct_herramienta", 0.05)
                
                for _, fila in df_pres.iterrows():
                    item_id = str(fila['ID'])
                    # Evitar nombres de hoja duplicados o inválidos
                    sheet_name = item_id[:31].replace(':', '').replace('/', '').replace('\\', '').replace('?', '').replace('*', '').replace('[', '').replace(']', '')
                    ws = writer.sheets.setdefault(sheet_name, workbook.add_worksheet(sheet_name))
                    
                    ws.set_column('A:A', 55) # Descripción
                    ws.set_column('B:B', 10) # Unidad
                    ws.set_column('C:C', 12) # Rend/Cant
                    ws.set_column('D:D', 15) # Vr. Unitario
                    ws.set_column('E:E', 15) # Vr. Parcial
                    
                    # Membrete Superior con Espacio para Logos
                    ws.set_row(0, 30)
                    ws.set_row(1, 30)
                    ws.set_row(2, 30)
                    ws.merge_range('A1:A3', _t('[ LOGO CLIENTE ]', '[ CLIENT LOGO ]'), logo_fmt)
                    ws.merge_range('B1:D1', _t('FORMATO', 'FORMAT'), title_fmt)
                    ws.merge_range('B2:D3', _t('ANÁLISIS DE PRECIOS UNITARIOS', 'UNIT PRICE ANALYSIS'), title_fmt)
                    ws.write('E1', _t('[ LOGO EMPRESA ]', '[ COMPANY LOGO ]'), logo_fmt)
                    ws.merge_range('E2:E3', _t(f"FECHA:\n{fecha_hoy}", f"DATE:\n{fecha_hoy}"), header_fmt)
                    
                    ws.write('A4', _t('PROYECTO DE CONTRATO:', 'CONTRACT PROJECT:'), apu_sub_fmt)
                    ws.merge_range('B4:E4', p_nombre, value_fmt)
                    
                    ws.write('A5', _t('CAPÍTULO:', 'CHAPTER:'), apu_sub_fmt)
                    ws.merge_range('B5:D5', fila['Capítulo'], value_fmt)
                    ws.write('E5', _t('UNIDAD', 'UNIT'), text_center_fmt)
                    
                    ws.write('A6', _t('ÍTEM:', 'ITEM:'), apu_sub_fmt)
                    ws.write('B6', fila['ID'], text_center_fmt)
                    ws.merge_range('C6:D6', fila['Descripción'], value_fmt)
                    ws.write('E6', fila['Unidad'], text_center_fmt)
                    
                    # Simulación de rendimiento basado en el costo
                    vr_unit = float(fila['Vr. Unitario'])
                    mo_total = costo_dia_mo
                    rendimiento = mo_total / (vr_unit * 0.30) if vr_unit > 0 else 1
                    if rendimiento < 0.1: rendimiento = 1
                    
                    vr_mo = mo_total / rendimiento
                    vr_herr = vr_mo * herramienta_pct
                    vr_mat = vr_unit - vr_mo - vr_herr
                    if vr_mat < 0: vr_mat = 0
                    
                    r = 8
                    # 1. EQUIPOS
                    ws.merge_range(r, 0, r, 4, _t('1. EQUIPOS', '1. EQUIPMENT'), apu_sub_fmt)
                    r+=1
                    ws.write_row(r, 0, [_t('DESCRIPCION', 'DESCRIPTION'), _t('UNIDAD', 'UNIT'), _t('VALOR UNITARIO', 'UNIT PRICE'), _t('CANTIDAD', 'QUANTITY'), _t('VALOR PARCIAL', 'PARTIAL VALUE')], apu_col_fmt)
                    r+=1
                    ws.write(r, 0, _t('Herramienta y equipo menor', 'Minor tools and equipment'), text_fmt)
                    ws.write(r, 1, '%', text_center_fmt)
                    ws.write_number(r, 2, vr_mo, money_fmt)
                    ws.write_number(r, 3, herramienta_pct, num_fmt)
                    ws.write_number(r, 4, vr_herr, money_fmt)
                    r+=1
                    ws.write(r, 3, _t('SUBTOTAL $', 'SUBTOTAL $'), apu_sub_fmt)
                    ws.write_number(r, 4, vr_herr, total_fmt)
                    
                    # 2. MATERIALES
                    r+=2
                    ws.merge_range(r, 0, r, 4, _t('2. MATERIALES', '2. MATERIALS'), apu_sub_fmt)
                    r+=1
                    ws.write_row(r, 0, [_t('DESCRIPCION', 'DESCRIPTION'), _t('UNIDAD', 'UNIT'), _t('VALOR UNITARIO', 'UNIT PRICE'), _t('CANTIDAD', 'QUANTITY'), _t('VALOR PARCIAL', 'PARTIAL VALUE')], apu_col_fmt)
                    r+=1
                    ws.write(r, 0, _t('Insumos y Materiales Base', 'Base Materials and Supplies'), text_fmt)
                    ws.write(r, 1, _t('UND', 'UND'), text_center_fmt)
                    ws.write_number(r, 2, vr_mat, money_fmt)
                    ws.write_number(r, 3, 1.0, num_fmt)
                    ws.write_number(r, 4, vr_mat, money_fmt)
                    r+=1
                    ws.write(r, 3, _t('SUBTOTAL $', 'SUBTOTAL $'), apu_sub_fmt)
                    ws.write_number(r, 4, vr_mat, total_fmt)
                    
                    # 3. MANO DE OBRA
                    r+=2
                    ws.merge_range(r, 0, r, 4, _t('3. MANO DE OBRA', '3. LABOR'), apu_sub_fmt)
                    r+=1
                    ws.write_row(r, 0, [_t('TRABAJADOR', 'WORKER'), _t('JORNAL', 'WAGE'), _t('FACTOR PRESTACIONAL', 'BENEFITS FACTOR'), _t('RENDIMIENTO', 'PERFORMANCE'), _t('VALOR PARCIAL', 'PARTIAL VALUE')], apu_col_fmt)
                    r+=1
                    ws.write(r, 0, _t('Cuadrilla de Trabajo Estándar', 'Standard Work Crew'), text_fmt)
                    ws.write_number(r, 1, mo_total, money_fmt)
                    ws.write(r, 2, _t('Incluido', 'Included'), text_center_fmt)
                    ws.write_number(r, 3, rendimiento, num_fmt)
                    ws.write_number(r, 4, vr_mo, money_fmt)
                    r+=1
                    ws.write(r, 3, _t('SUBTOTAL $', 'SUBTOTAL $'), apu_sub_fmt)
                    ws.write_number(r, 4, vr_mo, total_fmt)
                    
                    # 5. OTROS (Como en la foto)
                    r+=2
                    ws.merge_range(r, 0, r, 4, _t('5. OTROS', '5. OTHERS'), apu_sub_fmt)
                    r+=1
                    ws.write_row(r, 0, [_t('DESCRIPCION', 'DESCRIPTION'), _t('UNIDAD', 'UNIT'), _t('VALOR UNITARIO', 'UNIT PRICE'), _t('CANTIDAD', 'QUANTITY'), _t('VALOR PARCIAL', 'PARTIAL VALUE')], apu_col_fmt)
                    r+=1
                    ws.write(r, 3, _t('SUBTOTAL $', 'SUBTOTAL $'), apu_sub_fmt)
                    ws.write_number(r, 4, 0, total_fmt)

                    # TOTALES DEL APU
                    r+=2
                    ws.write(r, 3, _t('COSTO DIRECTO: $', 'DIRECT COST: $'), subtitle_fmt)
                    ws.write_number(r, 4, vr_unit, value_fmt)
                    r+=1
                    ws.write(r, 3, _t('FACTOR DE INCREMENTO:', 'INCREMENT FACTOR:'), subtitle_fmt)
                    ws.write_number(r, 4, 0, value_fmt)
                    r+=1
                    ws.write(r, 3, _t('COSTO TOTAL:', 'TOTAL COST:'), gran_total_fmt)
                    ws.write_number(r, 4, vr_unit, gran_total_fmt)
                    
                    # BLOQUE DE FIRMAS Y CONTROL
                    r+=2
                    ws.write(r, 0, '', text_fmt)
                    ws.write(r, 1, _t('Elaboró', 'Prepared by'), text_fmt)
                    ws.merge_range(r, 2, r, 3, _t('Aprobó', 'Approved by'), text_fmt)
                    ws.write(r, 4, _t('Visto bueno', 'Reviewed by'), text_fmt)
                    r+=1
                    ws.write(r, 0, _t('Nombre', 'Name'), text_fmt)
                    ws.write(r, 1, _t('ING. DE COSTOS', 'COST ENGINEER'), text_fmt)
                    ws.merge_range(r, 2, r, 3, '', text_fmt)
                    ws.write(r, 4, '', text_fmt)
                    r+=1
                    ws.write(r, 0, _t('Cargo', 'Position'), text_fmt)
                    ws.write(r, 1, _t('Especialista', 'Specialist'), text_fmt)
                    ws.merge_range(r, 2, r, 3, '', text_fmt)
                    ws.write(r, 4, '', text_fmt)
                    r+=1
                    ws.write(r, 0, _t('Firma', 'Signature'), text_fmt)
                    ws.write(r, 1, '', text_fmt)
                    ws.merge_range(r, 2, r, 3, '', text_fmt)
                    ws.write(r, 4, '', text_fmt)
                    ws.set_row(r, 30) # Espacio grande para la firma

            output.seek(0)
            st.download_button(
                _t("📥 Exportar Presupuesto y APUs (Excel)", "📥 Export Budget & APUs (Excel)"),
                data=output,
                file_name=f"Presupuesto_APU_{p_nombre.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
