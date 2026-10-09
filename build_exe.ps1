# Construit l'exécutable autonome dist\DCIM-Sorter.exe (aucun Python requis
# chez l'utilisateur final). Usage :  powershell -File build_exe.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install --quiet --upgrade pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name "DCIM-Sorter" `
    --icon photo_organiser.ico `
    photo_organiser.py

if (Test-Path "dist\DCIM-Sorter.exe") {
    $size = [math]::Round((Get-Item "dist\DCIM-Sorter.exe").Length / 1MB, 1)
    Write-Host "OK -> dist\DCIM-Sorter.exe ($size Mo)"
} else {
    Write-Host "ECHEC : exe non produit"
    exit 1
}
