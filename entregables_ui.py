import streamlit as st
import io

try:
    from normas_referencias import mostrar_referencias_norma
except ImportError:
    def mostrar_referencias_norma(*args, **kwargs):
        st.info("Módulo de referencias normativas no encontrado.")

def mostrar_entregables(
    norma_sel: str,
    modulo_key: str,
    docx_buf: io.BytesIO = None,
    excel_buf: io.BytesIO = None,
    dxf_buf: io.BytesIO = None,
    ifc_buf: io.BytesIO = None,
    titulo: str = "Proyecto Sin Título",
    docx_name: str = "Memoria_Calculo.docx",
    excel_name: str = "Resultados.xlsx",
    dxf_name: str = "Planos.dxf",
    ifc_name: str = "Modelo_BIM.ifc"
):
    """
    Renderiza un panel unificado y estandarizado al final de la página para la descarga de entregables.
    Agrupa Memoria DOCX, Excel, DXF, IFC y las Referencias Normativas en un solo contenedor premium.
    
    Args:
        norma_sel: Norma activa seleccionada en el módulo.
        modulo_key: Identificador del módulo para cargar las referencias pertinentes.
        docx_buf, excel_buf, dxf_buf, ifc_buf: Buffers de memoria con los archivos a descargar. Se ocultan si son None.
        titulo: Nombre base para mostrar en la interfaz.
        *_name: Nombres propuestos para la descarga de los archivos.
    """
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    
    #  CONTENEDOR PREMIUM DE ENTREGABLES 
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1e2530 0%, #151a22 100%);
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        ">
            <h3 style="color: #58a6ff; margin-top: 0; font-weight: 500; font-size: 1.3rem;">
                 Centro de Entregables — {titulo}
            </h3>
            <p style="color: #8b949e; font-size: 0.9rem; margin-bottom: 15px;">
                Descargue la memoria técnica de cálculo, hojas de resumen de cantidades, planos cad paramétricos y modelos BIM generados durante el análisis.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    #  BOTONES DE DESCARGA ESTRUCTURADOS 
    # Distribuir dinámicamente columnas dependiendo de cuántos archivos existan
    archivos = []
    if docx_buf: archivos.append((" Memoria DOCX", docx_buf, docx_name, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "primary"))
    if excel_buf: archivos.append((" Resumen Excel / CSV", excel_buf, excel_name, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "secondary"))
    if dxf_buf: archivos.append((" Planos de Dibujo DXF", dxf_buf, dxf_name, "application/dxf", "secondary"))
    if ifc_buf: archivos.append((" Modelo BIM IFC", ifc_buf, ifc_name, "application/octet-stream", "secondary"))
    
    if not archivos:
        st.info(" Aún no se han transferido archivos. Haga clic en los botones superiores de **Generar Memoria** o **Exportar DXF / IFC** dentro de cada pestaña para depositar los entregables en esta bandeja unificada.")
    else:
        cols = st.columns(len(archivos))
        for i, (label, buf, name, mime, tipo) in enumerate(archivos):
            with cols[i]:
                st.download_button(
                    label=label,
                    data=buf.getvalue() if isinstance(buf, io.BytesIO) else buf,
                    file_name=name,
                    mime=mime,
                    type=tipo,
                    use_container_width=True
                )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    #  PANEL NORMATIVO INCRUSTADO AUTOMÁTICAMENTE 
    mostrar_referencias_norma(norma_sel, modulo_key)
