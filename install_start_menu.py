#!/usr/bin/env python3
"""
Installe DCIM Sorter dans le menu Démarrer de Windows 11.
À lancer une seule fois : python install_start_menu.py
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path

# ── Locate files ───────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent.resolve()
SCRIPT_PATH = SCRIPT_DIR / "photo_organiser.py"
ICON_PATH   = SCRIPT_DIR / "photo_organiser.ico"
START_MENU  = (Path(os.environ['APPDATA'])
               / "Microsoft" / "Windows" / "Start Menu" / "Programs")
SHORTCUT    = START_MENU / "DCIM Sorter.lnk"

# ── Pythonw (no console window) ────────────────────────────────────────────
PYTHONW = Path(sys.executable).parent / "pythonw.exe"
if not PYTHONW.exists():
    PYTHONW = Path(sys.executable)   # fallback to python.exe


def export_icon() -> Path | None:
    """Export the app icon to a .ico file via PyQt6."""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)

        sys.path.insert(0, str(SCRIPT_DIR))
        from photo_organiser import create_app_icon

        pix = create_app_icon().pixmap(256, 256)
        if pix.save(str(ICON_PATH)):
            return ICON_PATH
        # Fallback: PNG (shortcut won't show custom icon but still works)
        png = SCRIPT_DIR / "photo_organiser.png"
        if pix.save(str(png)):
            return png
    except Exception as e:
        print(f"  Avertissement : icône non exportée ({e})")
    return None


def create_shortcut(icon: Path | None):
    """Create the Start Menu shortcut via a temporary PowerShell script."""
    icon_line = (f"$s.IconLocation     = '{icon}'"
                 if icon else "# no custom icon")

    ps = f"""
$ws = New-Object -ComObject WScript.Shell
$s  = $ws.CreateShortcut('{SHORTCUT}')
$s.TargetPath       = '{PYTHONW}'
$s.Arguments        = '"{SCRIPT_PATH}"'
$s.WorkingDirectory = '{SCRIPT_DIR}'
{icon_line}
$s.Description      = 'DCIM Sorter — Organisation de photos par jour'
$s.Save()
Write-Host 'DONE'
"""

    with tempfile.NamedTemporaryFile(
            mode='w', suffix='.ps1', delete=False, encoding='utf-8') as f:
        f.write(ps)
        tmp = f.name

    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', tmp],
            capture_output=True, text=True
        )
        return 'DONE' in r.stdout, r.stderr.strip()
    finally:
        os.unlink(tmp)


def main():
    print()
    print("  ── Installation DCIM Sorter ──")
    print()

    if not SCRIPT_PATH.exists():
        print(f"  Erreur : photo_organiser.py introuvable dans {SCRIPT_DIR}")
        sys.exit(1)

    print("  Export de l'icône…")
    icon = export_icon()
    if icon:
        print(f"  Icône : {icon.name}")

    print("  Création du raccourci dans le menu Démarrer…")
    ok, err = create_shortcut(icon)

    if ok:
        print()
        print("  ✓  DCIM Sorter est maintenant dans le menu Démarrer !")
        print(f"     Raccourci : {SHORTCUT}")
        print()
        print("  Tapez « Photo » dans la barre de recherche Windows pour le trouver.")
        print()
    else:
        print(f"  ✗  Échec : {err or 'erreur inconnue'}")
        sys.exit(1)


if __name__ == '__main__':
    main()
