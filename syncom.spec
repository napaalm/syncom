# -*- mode: python ; coding: utf-8 -*-
import subprocess
from PyInstaller.compat import is_linux, is_win

# determine os
if is_linux:
    os = "linux"
    # get version from git
    version = subprocess.check_output(["git", "describe", "--always", "--dirty", "--tags"]).strip().decode()
elif is_win:
    os = "windows"
    # when building for windows the program version is determined outside wine
    version = open("/tmp/version", "r").read().strip()

# generate name
name = f"syncom-{version}-{os}-x86_64"

# write version initialization runtime hook
with open("/tmp/version.py", "w") as version_script:
    version_script.write(f"__version__ = '{version}'\n")

block_cipher = None

a = Analysis(['syncom.py'],
             pathex=['/src'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             # version hook written above
             runtime_hooks=['/tmp/version.py'],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name=name,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
