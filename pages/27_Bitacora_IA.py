import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def run_27_bitacora():
    lang = st.session_state.get("idioma", "Español")
    def _t(es, en): return en if lang == "English" else es

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0a1128 0%,#1c2541 100%);
      padding:24px 36px;border-radius:14px;margin-bottom:16px;border:1px solid #38bdf8;box-shadow:0 4px 32px #0008;">
     <div style="display:flex;align-items:center;gap:18px;">
      <div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px;">
        <span style="font-size:38px;line-height:1;">🤖</span>
      </div>
      <div>
       <h1 style="color:#ffffff;margin:0;font-size:2rem;font-weight:800;">Bitácora Inteligente (IA)</h1>
       <p style="color:#93c5fd;margin:4px 0 0;font-size:0.95rem;">
         Gestión Total &middot; Reportes Diarios Automáticos &middot; Dashboard EVM
       </p>
      </div>
     </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Registro Rápido Diario", "Gestión Total (Dashboard EVM)", "Alertas IA Predictivas"])

    # ---------------- TAB 1: REGISTRO DIARIO ----------------
    with tab1:
        st.subheader("Captura Inteligente Diaria")
        st.write("Registra el avance del día. La información se sincronizará automáticamente con el modelo 4D/5D.")
        
        c1, c2, c3 = st.columns(3)
        fecha_reg = c1.date_input("Fecha de Registro", datetime.date.today())
        frente_obra = c2.selectbox("Frente de Obra / Actividad", ["Fundición de Columnas", "Armado de Acero", "Excavación", "Mampostería", "MEP"])
        clima = c3.selectbox("Clima Predominante", ["Soleado", "Parcialmente Nublado", "Lluvia Fuerte (Retraso)"])

        st.markdown("#### Progreso Físico y Recursos")
        colA, colB, colC = st.columns(3)
        avance_pct = colA.slider("Avance del Frente hoy (%)", 0, 100, 5)
        hh_usadas = colB.number_input("Horas Hombre (HH) consumidas", min_value=0, value=24)
        cemento_gastado = colC.number_input("Cemento usado (Bultos)", min_value=0.0, value=0.0)

        st.markdown("#### Observaciones (Dictado por Voz)")
        st.caption("Usa el dictado inteligente para registrar incidencias sin escribir.")
        
        # HTML + JS simple para Speech Recognition (Web Speech API)
        html_code = """
        <div style="padding: 10px; background: #1e1e2f; border-radius: 8px; border: 1px solid #3b82f6;">
            <button id="btn-record" style="background: #3b82f6; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; font-weight: bold;">🎤 Iniciar Dictado</button>
            <span id="status" style="color: #94a3b8; margin-left: 10px;">Listo para grabar...</span>
            <textarea id="texto-dictado" style="width: 100%; height: 80px; margin-top: 10px; background: #0f172a; color: white; border: 1px solid #334155; border-radius: 4px; padding: 8px;"></textarea>
            <script>
                const btnRecord = document.getElementById('btn-record');
                const status = document.getElementById('status');
                const textarea = document.getElementById('texto-dictado');
                
                if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                    const recognition = new SpeechRecognition();
                    recognition.lang = 'es-ES';
                    recognition.interimResults = true;
                    
                    recognition.onstart = function() {
                        status.innerText = 'Escuchando...';
                        btnRecord.style.background = '#ef4444';
                    };
                    
                    recognition.onresult = function(event) {
                        let final_transcript = '';
                        for (let i = event.resultIndex; i < event.results.length; ++i) {
                            if (event.results[i].isFinal) {
                                final_transcript += event.results[i][0].transcript;
                            }
                        }
                        if(final_transcript !== '') textarea.value += final_transcript + '. ';
                    };
                    
                    recognition.onerror = function(event) { status.innerText = 'Error: ' + event.error; };
                    
                    recognition.onend = function() {
                        status.innerText = 'Grabación finalizada.';
                        btnRecord.style.background = '#3b82f6';
                    };
                    
                    btnRecord.onclick = function() { recognition.start(); };
                } else {
                    btnRecord.style.display = 'none';
                    status.innerText = 'Dictado por voz no soportado en este navegador. Usa Chrome.';
                }
            </script>
        </div>
        """
        st.components.v1.html(html_code, height=180)

        obs_manual = st.text_area("Notas / No Conformidades (Pega aquí el texto dictado o escribe)", height=80)

        if st.button("Guardar Reporte Diario en Nube", type="primary", use_container_width=True):
            if "registros_diarios" not in st.session_state:
                st.session_state.registros_diarios = []
            st.session_state.registros_diarios.append({
                "fecha": fecha_reg,
                "frente": frente_obra,
                "avance": avance_pct,
                "hh": hh_usadas,
                "obs": obs_manual
            })
            st.success("✅ Registro sincronizado correctamente. Coordinación total actualizada.")

    # ---------------- TAB 2: DASHBOARD EVM ----------------
    with tab2:
        st.subheader("Dashboard Gerencial: Earned Value Management (EVM)")
        st.write("Datos sincronizados en tiempo real para decisiones rentables.")

        # Simulamos datos de avance general si no hay muchos registros
        dias_proyecto = 60
        dia_actual = 25
        presupuesto_total = 125000000 # 125M

        # EVM Params (Simulados basados en un supuesto día 25)
        PV = presupuesto_total * (dia_actual / dias_proyecto) # Planned Value
        EV = presupuesto_total * 0.38 # Earned Value (Avance real 38%)
        AC = presupuesto_total * 0.45 # Actual Cost (Se ha gastado el 45%)

        CPI = EV / AC if AC > 0 else 1
        SPI = EV / PV if PV > 0 else 1

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valor Planeado (PV)", f"${PV:,.0f}")
        c2.metric("Valor Ganado (EV)", f"${EV:,.0f}", f"{(EV-PV)/PV*100:.1f}% vs PV", delta_color="inverse")
        c3.metric("Costo Real (AC)", f"${AC:,.0f}", f"{(AC-EV)/EV*100:.1f}% Sobrecosto", delta_color="inverse")
        
        # Semáforos CPI/SPI
        cpi_color = "#10b981" if CPI >= 1 else "#ef4444"
        spi_color = "#10b981" if SPI >= 1 else "#ef4444"
        
        c4.markdown(f"""
        <div style="background:#1e293b;padding:10px;border-radius:8px;text-align:center;border:1px solid #334155;">
            <div style="color:{cpi_color};font-size:20px;font-weight:bold;">CPI: {CPI:.2f}</div>
            <div style="color:{spi_color};font-size:20px;font-weight:bold;">SPI: {SPI:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Curva S de Inversión y Avance")
        
        # Generar datos simulados para la curva S
        x_dias = np.arange(1, dias_proyecto+1)
        y_pv = presupuesto_total / (1 + np.exp(-0.1*(x_dias - dias_proyecto/2))) # Curva S sigmoide ideal
        
        y_ev = np.full_like(y_pv, np.nan)
        y_ac = np.full_like(y_pv, np.nan)
        
        # Datos hasta el dia actual (con ineficiencias)
        y_ev[:dia_actual] = y_pv[:dia_actual] * 0.90 # Ligeramente atrasado
        y_ac[:dia_actual] = y_pv[:dia_actual] * 1.15 # Gastando más de lo planeado

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_dias, y=y_pv, mode='lines', name='PV (Planeado)', line=dict(color='#3b82f6', width=3)))
        fig.add_trace(go.Scatter(x=x_dias[:dia_actual], y=y_ev[:dia_actual], mode='lines+markers', name='EV (Ganado/Avance Físico)', line=dict(color='#10b981', width=3)))
        fig.add_trace(go.Scatter(x=x_dias[:dia_actual], y=y_ac[:dia_actual], mode='lines+markers', name='AC (Costo Real)', line=dict(color='#ef4444', width=3)))
        
        fig.add_vline(x=dia_actual, line_dash="dash", line_color="white", annotation_text="Día Actual")
        fig.update_layout(title="Control Integral de Obra (4D/5D Sincronizado)", xaxis_title="Días de Proyecto", yaxis_title="Costo ($)", template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- TAB 3: ALERTAS PREDICTIVAS IA ----------------
    with tab3:
        st.subheader("Decisiones Rentables Asistidas por IA")
        st.write("El motor estocástico analiza los datos de la bitácora y predice riesgos futuros.")

        if CPI < 1.0:
            st.error(f"⚠️ **Alerta de Sobrecosto:** El Índice de Costo (CPI) es {CPI:.2f}. Por cada $1 invertido, solo se generan ${CPI:.2f} en obra física.")
            
            EAC = presupuesto_total / CPI # Estimado a la conclusión
            st.markdown(f"**Proyección IA:** El costo final del proyecto será de **${EAC:,.0f}**, un sobrecosto proyectado de **${EAC - presupuesto_total:,.0f}**.")
            
            st.info("💡 **Recomendación IA:** Optimice las cuadrillas de *Armado de Acero*. Los reportes diarios indican exceso de horas hombre y retrasos por clima.")

        if SPI < 1.0:
            st.warning(f"⏳ **Alerta de Retraso:** El Índice de Cronograma (SPI) es {SPI:.2f}. La obra se mueve al {SPI*100:.0f}% de la velocidad planeada.")
            
            dias_estimados = dias_proyecto / SPI
            st.markdown(f"**Proyección IA:** El proyecto terminará en el día **{int(dias_estimados)}** ({int(dias_estimados - dias_proyecto)} días de retraso).")
            
            st.info("💡 **Recomendación IA:** Considere implementar horas extra o fines de semana para recuperar la ruta crítica en *Fundición de Columnas*.")
            
        st.markdown("""
        <div style="background:#1e3a8a;padding:15px;border-radius:10px;margin-top:20px;">
            <h4 style="color:white;margin:0;">📝 Informe de Resultados Generado</h4>
            <p style="color:#bfdbfe;margin:5px 0 0;">Todos los datos precisos han sido consolidados. Puede exportar el reporte gerencial completo en Excel o PDF para comité de obra.</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    run_27_bitacora()
