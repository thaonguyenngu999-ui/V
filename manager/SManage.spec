# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('F:\\ChromiumSoncuto\\manager\\profiles.py', '.'), ('F:\\ChromiumSoncuto\\manager\\fingerprint.py', '.'), ('F:\\ChromiumSoncuto\\manager\\fingerprint_utils.py', '.'), ('F:\\ChromiumSoncuto\\manager\\browser_launcher.py', '.'), ('F:\\ChromiumSoncuto\\manager\\playwright_attach.py', '.'), ('F:\\ChromiumSoncuto\\manager\\runtime_manager.py', '.'), ('F:\\ChromiumSoncuto\\manager\\app_meta.py', '.')]
binaries = []
hiddenimports = ['customtkinter', 'PIL', 'app_meta', 'fingerprint_utils', 'playwright_attach', 'runtime_manager']
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['F:\\ChromiumSoncuto\\manager\\gui_v3.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SManage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SManage',
)
