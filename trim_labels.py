"""
trim_labels.py — Limpia espacios iniciales sobrantes en strings de Streamlit
  Resultado del emoji-removal: "📝 Memoria" → " Memoria" → "Memoria"
Uso:
    python trim_labels.py --dry-run
    python trim_labels.py
"""
import re
import sys
from pathlib import Path

# Captura el espacio inicial dentro de strings de llamadas a st.*()
# Solo afecta el PRIMER espacio sobrante dentro de literales string
LEADING_SPACE_RE = re.compile(
    r'''(st\.\w+\([^)]*?['"]) +([\w\u00C0-\u024F\*\#])''',
    re.UNICODE,
)

# También aplica para f-strings en labels directos
# Patrón más general: cualquier string literal  que empiece con espacio
# dentro de argumentos posicionales de st.*
ST_ARG_RE = re.compile(
    r'''(?<=[("',\[]) ([\w\u00C0-\u024F\*\#\-])''',
    re.UNICODE,
)

def clean_leading_spaces(line: str) -> str:
    """Elimina espacios iniciales sobrantes en llamadas st.xxx()."""
    # Patrón: st.xxx("  texto", ...) o st.xxx(' texto', ...)
    # Limita a strings que empiecen con espacio dentro de st.*()
    cleaned = re.sub(
        r"""(st\.\w+\s*\([^)]{0,200}?['"]\s{1,3})([\w\u00C0-\u024F\*\#])""",
        lambda m: m.group(1).rstrip() + m.group(2),
        line
    )
    return cleaned


def process_file(path: Path, dry_run: bool = False):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    changes = []
    new_lines = []

    for i, line in enumerate(lines, start=1):
        cleaned = clean_leading_spaces(line)
        if cleaned != line:
            changes.append((i, line.rstrip(), cleaned.rstrip()))
        new_lines.append(cleaned)

    if not dry_run and changes:
        path.write_text("".join(new_lines), encoding="utf-8")

    return changes


def main():
    dry_run = "--dry-run" in sys.argv
    root = Path(__file__).parent

    targets = sorted(
        list((root / "pages").glob("*.py")) +
        [root / "Inicio_App.py"]
    )

    total = 0
    for path in targets:
        changes = process_file(path, dry_run=dry_run)
        if changes:
            total += len(changes)
            mode = "[DRY]" if dry_run else "[OK]"
            print(f"{mode} {path.name} — {len(changes)} ajustes")
            for ln, orig, clean in changes[:10]:
                print(f"  L{ln:4d}  - {orig[:70].encode('ascii','replace').decode()}")
                print(f"         + {clean[:70].encode('ascii','replace').decode()}")
            if len(changes) > 10:
                print(f"  ... y {len(changes)-10} mas")

    print(f"\n{'[DRY-RUN]' if dry_run else 'APLICADO'}: {total} ajustes totales")


if __name__ == "__main__":
    main()
