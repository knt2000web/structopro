---
description: Protocolo Estricto de Verificación QA para Módulos Estructurales
---
# Protocolo de Calidad (QA) Estructural

Para evitar la repetición de los fallos encontrados en la Viga T y Rectangular, todo asistente y desarrollador deberá ejecutar obligatoriamente esta lista de chequeo antes de dar por completado un módulo estructural de este proyecto:

## 1. Validación de Variables Recalculadas en Tablas y Métricas
- **Error Histórico:** Mostrar el peralte inicial `d_input` en lugar del peralte efectivo `d_eff` real tras una redistribución de acero en 2 o más filas.
- **Protocolo:** Rastrear cada variable de entrada (e.g. `b`, `h`, `d`, `bf`) para ver si sufre alguna alteración normativa o por disposición de acero a lo largo del flujo. Asegurar que las variables pasadas a los bloques finales de pintado (`st.dataframe`, `st.metric`) o exportación siempre sean referenciadas con la variable ya mutada/corregida (ej. `d_eff`, `kw_min_req`).

## 2. Consistencia en los Límites del Estado de Sesión (Session State)
- **Error Histórico:** Sobrescribir en memoria el `bf` (Ancho del ala) que digita el usuario, ignorando que supera el límite de C.8.10.2, permitiendo propagar sobre-resistencias a los demás módulos.
- **Protocolo:** Antes de hacer `.update()` en diccionarios inter-módulo, interceptar los _inputs_. Las geometrías que la norma obliga a limitar deben forzar su propia restricción *antes* de propagarse a los buses de datos.

## 3. Correspondencia Biunívoca en Funciones de Carga y Guardado
- **Error Histórico:** Definir un input de usuario como `key="cv_mu_izq"` pero capturarlo en estado como `vcmuizq`, provocando amnesia de estado al recargar los proyectos.
- **Protocolo:** Al añadir un nuevo contenedor (`st.number_input` etc), realizar siempre una triple revisión del nombre de la variable elegida contra: 1) El objeto `SessionState` que inicializa los predeterminados, y 2) Las listas que ejecutan retorno de estado en `capturar_estado()`. Deben escribirse idénticos. Uso obligatorio de la terminal para hacer un `grep` comprobando cruce de nombres.

## 4. Trigonometría Analítica Real (Nada de aproximaciones)
- **Error Histórico:** Usar `hook_len * cos(75)` aleatoriamente desde la esquina 0,0 para obligar visualmente al cruce de figurado en estribos, dibujando un gancho estructuralmente irreal.
- **Protocolo:** Al ilustrar ganchos o estribos, utilizar trigonometría vectorial `math.cos(rad)` calculando siempre el origen del vector desde la verdadera esquina física. Todo ángulo de armado requerido por las normas (Ej 135°, 90°, 180°) debe convertirse de grados base a radianes sin usar "engaños visuales".

## 5. Control de Dominio en Funciones Matemáticas
- **Error Histórico:** `math.acos(variable)` deteniendo el flujo web por un `ValueError` si `variable > 1.0` debido a imprecisiones de coma flotante en límites de circunferencia.
- **Protocolo:** Cualquier argumento que provenga de una división entre dos floats y entre a una función trigonométrica inversa (`acos`, `asin`) debe ser sanitizado preventivamente con `np.clip(argumento, -1.0, 1.0)`.

## 6. Verificación de Inversos Modulares (Ej. Unidades Compuestas o Mezclas)
- **Error Histórico:** Multiplicar volumen por mil seiscientos `v * 1600` para conseguir un ratio, en vez de dividir, tergiversando los m3 frente a los kg para los APU de agregados.
- **Protocolo:** Identificar el tipo de unidad final. Al crear nuevas tablas de Anális de Precios Unitarios (APUs) o cuantificaciones, insertar un comentario con el análisis dimensional del multiplicador. Confirmar explícitamente: "kg_total / kg/m3 = m3" -> Por lo tanto es división.

> **Uso de este workflow:** Si surge la duda al crear un nuevo módulo, puedes ejecutar internamente una revisión contra cada uno de estos 6 pasos.
