import os
import re

directory = r"C:\Users\cagch\Desktop\Diagrama_NSR10\pages"
archivos = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.py')]
archivos.append(r"C:\Users\cagch\Desktop\Diagrama_NSR10\new_export.py")

patron_block = re.compile(
    r"(\s*)([A-Za-z0-9_]+)\s*=\s*io\.StringIO\(\)(?:;|(?:\s*\n\s*))([A-Za-z0-9_]+)\.write\(\2\)(?:;|\s*\n)(.*?)(st\.download_button\s*\([^)]*data\s*=\s*)\2\.getvalue\(\)(?:\.encode\(['\"]utf-8['\"]\))?(.*?\))",
    re.DOTALL
)

for arc in archivos:
    if os.path.isfile(arc):
        with open(arc, 'r', encoding='utf-8') as f:
            content = f.read()
        
        matches = patron_block.findall(content)
        if matches:
            print(f"Buscando en {os.path.basename(arc)}: Encontrados {len(matches)} matches")
            def replacer(m):
                indent = m.group(1)
                buf_name = m.group(2)
                doc_name = m.group(3)
                between_code = m.group(4)
                down_start = m.group(5)
                down_end = m.group(6)
                
                # Reemplazamos el "mime" application/dxf que estorba
                # pero mantenemos la parte vital
                down_end_cleaned = re.sub(r",\s*mime\s*=\s*['\"]application/dxf['\"]", "", down_end)
                
                new_block = (
                    f"{indent}import tempfile, os{indent}"
                    f"with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_{buf_name}:{indent}"
                    f"    tmp_path_{buf_name} = tmp_{buf_name}.name{indent}"
                    f"{doc_name}.saveas(tmp_path_{buf_name}){indent}"
                    f"with open(tmp_path_{buf_name}, 'rb') as f_{buf_name}:{indent}"
                    f"    bytes_{buf_name} = f_{buf_name}.read(){indent}"
                    f"os.unlink(tmp_path_{buf_name}){between_code}"
                    f"{down_start}bytes_{buf_name}{down_end_cleaned}"
                )
                return new_block
                
            new_content = patron_block.sub(replacer, content)
            
            if new_content != content:
                with open(arc, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Modificado: {os.path.basename(arc)}")
