# PyInstaller spec for the Tkinter desktop game.
# Build with: pyinstaller --clean mahjong_card_reader.spec
from pathlib import Path
ROOT = Path(SPECPATH)
datas = []

a = Analysis(
    [str(ROOT / "desktop_ui.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="MahjongCardReader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
