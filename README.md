# Diagrama de Interacción de Columna NSR-10

Aplicación web interactiva para generar el diagrama de interacción **P-M** (Carga Axial vs. Momento Flector) de columnas de concreto reforzado según la normativa colombiana **NSR-10 (Título C)**.

## 🚀 Demo en línea

*(Próximamente en Streamlit Cloud)*

## ✨ Características

- 📐 **Geometría flexible**: columnas rectangulares con cualquier dimensión
- 🔩 **Acero**: varillas en pulgadas (US) o milímetros (SI)
- 🧱 **Concreto en múltiples unidades**: MPa, PSI o kg/cm² (con valores típicos colombianos: 210, 280, 3000 PSI, etc.)
- 📊 **Curvas nominal y de diseño** (φPn, φMn) según NSR-10 C.10
- 🎯 **Punto de verificación** (Mu, Pu) con líneas punteadas a los ejes
- 📋 **Tabla de cuantía** paso a paso: Ag, Ast, ρ con verificación NSR-10 C.10.9
- ⚖️ **Conversión de unidades**: resultados en kN/kN-m o tonf/tonf-m en tiempo real
- 🏗️ **Tipo de columna**: Estribos (φ=0.65) o Espiral (φ=0.75)

## 🛠️ Instalación local

```bash
git clone https://github.com/TU_USUARIO/diagrama-nsr10.git
cd diagrama-nsr10
pip install -r requirements.txt
streamlit run app.py
```

## 📋 Requisitos

- Python 3.9+
- Ver `requirements.txt`

## 📖 Base normativa

- **NSR-10 Título C** – Concreto estructural
  - C.10.2.7 – Factor β₁
  - C.10.3.5 – Límite de compresión pura (Pn,max)
  - C.10.9 – Cuantía de refuerzo longitudinal (1% ≤ ρ ≤ 4%)
  - C.9.3 – Factores de reducción φ

## 📷 Captura

*(agregar screenshot del diagrama aquí)*

## 👤 Autor

Desarrollado para uso en ingeniería estructural colombiana.

---
*Desarrollado con ❤️ usando Python + Streamlit*
