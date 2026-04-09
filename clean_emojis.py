"""
clean_emojis.py — Elimina emojis de archivos .py de Streamlit
Uso:
    python clean_emojis.py --dry-run          # solo muestra cambios
    python clean_emojis.py                    # aplica cambios
    python clean_emojis.py --file pages/01_Columnas_PM.py  # archivo específico
"""

import re
import sys
import os
from pathlib import Path

# ─── Regex que captura caracteres emoji ─────────────────────────────────────
# Solo captura emojis visuales — excluye símbolos técnicos/matemáticos
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"   # Misc Symbols, Emoticons, Pictographs
    "\U0001FA00-\U0001FAFF"   # Extended Symbols-A
    "\U00002702-\U000027B0"   # Dingbats (tijeras, lapices, etc)
    "\U0000FE0F"              # Variation selector-16 (modifica emoji previo)
    "\U0000200D"              # Zero Width Joiner
    "]+",
    flags=re.UNICODE,
)

# ─── Limpieza simple: compacta espacios dobles dejados tras el emoji ─────────
DOUBLE_SPACE_RE = re.compile(r"  +")


def clean_line(line: str) -> str:
    """Elimina emojis de la línea, preservando indentación y espaciado."""
    return EMOJI_RE.sub("", line)


def process_file(path: Path, dry_run: bool = False) -> list[tuple[int, str, str]]:
    """
    Procesa un archivo .py y retorna lista de (line_num, original, cleaned).
    Si dry_run=False, escribe los cambios al disco.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    changes = []

    new_lines = []
    for i, line in enumerate(lines, start=1):
        cleaned = clean_line(line)
        if cleaned != line:
            changes.append((i, line.rstrip(), cleaned.rstrip()))
        new_lines.append(cleaned)

    if not dry_run and changes:
        path.write_text("".join(new_lines), encoding="utf-8")

    return changes


def main():
    dry_run = "--dry-run" in sys.argv
    specific_file = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            specific_file = arg

    root = Path(__file__).parent

    if specific_file:
        targets = [root / specific_file]
    else:
        targets = sorted(
            list((root / "pages").glob("*.py")) +
            [root / "Inicio_App.py"] +
            ([root / "auth.py"] if (root / "auth.py").exists() else [])
        )

    total_changes = 0
    total_files = 0

    for path in targets:
        if not path.exists():
            print(f"  [skip] {path.name} — no encontrado")
            continue

        changes = process_file(path, dry_run=dry_run)

        if changes:
            total_files += 1
            total_changes += len(changes)
            mode = "[DRY-RUN]" if dry_run else "[MODIFICADO]"
            print(f"\n{mode} {path.relative_to(root)} — {len(changes)} línea(s):")
            for lineno, original, cleaned in changes[:20]:   # máx 20 por archivo
                orig_preview  = original[:80].replace('\n', '').encode('ascii', 'replace').decode('ascii')
                clean_preview = cleaned[:80].replace('\n', '').encode('ascii', 'replace').decode('ascii')
                print(f"  L{lineno:4d}  -  {orig_preview}")
                print(f"         +  {clean_preview}")
            if len(changes) > 20:
                print(f"  ... y {len(changes)-20} líneas más")
        else:
            print(f"  [limpio]  {path.relative_to(root)}")

    print("\n" + "-"*60)
    mode_label = "DRY-RUN -- ningun archivo modificado" if dry_run else "CAMBIOS APLICADOS"
    print(f"{mode_label}: {total_changes} lineas en {total_files} archivos")

    if dry_run and total_changes:
        print("\nEjecuta sin --dry-run para aplicar los cambios:")
        print("  python clean_emojis.py")


if __name__ == "__main__":
    main()
