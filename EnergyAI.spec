# PyInstaller build specification
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("uvicorn")
a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[("app/static", "app/static")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="EnergyAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
