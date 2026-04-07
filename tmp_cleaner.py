import sys
import os

filepath = "C:/Users/cagch/Desktop/Diagrama_NSR10/pages/01_Columnas_PM.py"
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Las lineas que mostraron error residual iban de 1669 a 1738 (índices 1668 a 1737).
# Para seguridad, buscaremos el marcador exacto de inicio y fin.

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "texto_dx_armadura = (" in line and start_idx == -1 and i > 1600:
        start_idx = i
        # Verificamos si es el bloque residual (anidado)
        if line.startswith("                texto_dx_armadura"):
            start_idx = i
            break

for i in range(start_idx, len(lines)):
    if 'mime="application/dxf"' in lines[i]:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    del lines[start_idx:end_idx+1]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"Borradas líneas {start_idx+1} a {end_idx+1}")
else:
    print(f"No se encontraron límites: {start_idx}, {end_idx}")
