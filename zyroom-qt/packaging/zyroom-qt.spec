# -*- mode: python ; coding: utf-8 -*-
"""Recette PyInstaller de ZyRoom-Qt, commune a Linux et Windows.

Se lance depuis la racine du projet :

    .venv/bin/pyinstaller packaging/zyroom-qt.spec        (Linux)
    .venv\\Scripts\\pyinstaller packaging\\zyroom-qt.spec   (Windows)

**En dossier, pas en fichier unique.** Un executable unique doit se
decompresser en entier a chaque lancement -- avec Qt, cela fait une centaine
de megaoctets et deux a trois secondes d'attente avant que la fenetre
apparaisse. Le dossier demarre aussitot, et il se distribue tres bien dans une
archive.

**Les donnees gardent leur arborescence.** `config.py`, `i18n.py` et
`polices/__init__.py` cherchent leurs fichiers a cote d'eux, par
`os.path.dirname(__file__)`. En les rangeant sous `zyroom/`, ce calcul tombe
juste dans le bundle comme dans les sources : aucun code a adapter pour
l'empaquetage.
"""
import os
import sys

RACINE = os.path.abspath(os.getcwd())
PACKAGING = os.path.join(RACINE, "packaging")

# Ce qui n'est pas du code : les tables de correspondance, les traductions
# compilees, les fonds de carte, les symboles et la police embarquee.
donnees = [
    (os.path.join(RACINE, "zyroom", "data"), "zyroom/data"),
    (os.path.join(RACINE, "zyroom", "locale"), "zyroom/locale"),
    (os.path.join(RACINE, "zyroom", "cartes"), "zyroom/cartes"),
    (os.path.join(RACINE, "zyroom", "symboles"), "zyroom/symboles"),
    (os.path.join(RACINE, "zyroom", "polices", "pirata_one.ttf"),
     "zyroom/polices"),
    (os.path.join(RACINE, "zyroom", "polices", "OFL-PirataOne.txt"),
     "zyroom/polices"),
    (os.path.join(RACINE, "LICENSE.md"), "."),
]

# Les lanceurs de la variante du chef de guilde, poses a cote de
# l'executable et non dans _internal : c'est sur eux qu'on clique.
# Les modules Qt dont l'application ne se sert pas. Sans cette liste, le
# bundle emporte le moteur QML, la 3D et le multimedia -- des dizaines de
# megaoctets pour une application qui n'affiche que des widgets.
sans = [
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2", "PySide6.Qt3DCore", "PySide6.Qt3DRender",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtPositioning",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtSerialPort",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner",
    "PySide6.QtHelp", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    # Rien ici ne trace de courbe ni ne calcule de tableau : ces trois-la
    # arrivent par des imports optionnels d'autres bibliotheques.
    "tkinter", "matplotlib", "numpy", "PIL",
]

analyse = Analysis(
    [os.path.join(RACINE, "run.py")],
    pathex=[RACINE],
    binaries=[],
    datas=donnees,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=sans,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analyse.pure)

# L'icone : un .ico sous Windows, un .png ailleurs. Les deux sont fabriques
# par `packaging/icone.py` a partir du SVG, avant la construction.
icone = os.path.join(PACKAGING,
                     "zyroom-qt.ico" if sys.platform == "win32"
                     else "zyroom-qt.png")

exe = EXE(
    pyz,
    analyse.scripts,
    [],
    exclude_binaries=True,
    name="ZyRoom-Qt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Sans console sous Windows : sans cela, une fenetre noire s'ouvre
    # derriere l'application et ne se ferme jamais.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icone if os.path.isfile(icone) else None,
)

COLLECT(
    exe,
    analyse.binaries,
    analyse.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ZyRoom-Qt",
)
