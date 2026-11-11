"""Erzeugt die Versionsressource für kimbaview.exe (Rechtsklick → Eigenschaften → Details).

Aufruf (macht build.ps1 automatisch):  python make_version_info.py <ausgabedatei>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from kimbaview import __version__  # noqa: E402

PUBLISHER = "revlat"
parts = [int(p) for p in __version__.split(".")[:4]]
parts += [0] * (4 - len(parts))
nums = ", ".join(str(p) for p in parts)

TEMPLATE = f"""# automatisch erzeugt von make_version_info.py
VSVersionInfo(
  ffi=FixedFileInfo(filevers=({nums}), prodvers=({nums}), mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{PUBLISHER}'),
      StringStruct('FileDescription', 'kimbaview – Markdown and MediaWiki viewer'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', 'kimbaview'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 {PUBLISHER} – MIT License'),
      StringStruct('OriginalFilename', 'kimbaview.exe'),
      StringStruct('ProductName', 'kimbaview'),
      StringStruct('ProductVersion', '{__version__}')])]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
  ]
)
"""

Path(sys.argv[1]).write_text(TEMPLATE, encoding="utf-8")
print(f"Versionsressource {__version__} -> {sys.argv[1]}")
