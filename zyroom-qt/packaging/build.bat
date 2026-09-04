@echo off
rem Construit ZyRoom-Qt en dossier autonome, puis en archive ZIP.
rem
rem Depuis la racine du projet, dans une invite de commandes :
rem     packaging\build.bat
rem
rem Prealable, une seule fois :
rem     python -m venv .venv
rem     .venv\Scripts\pip install PySide6-Essentials pyinstaller
rem
rem Le resultat : dist\ZyRoom-Qt\ et l'archive dist\ZyRoom-Qt-<version>-windows.zip

setlocal
cd /d "%~dp0.."

set PYTHON=.venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo Environnement virtuel introuvable. Voir le README.
    exit /b 1
)

echo == Icones ==
"%PYTHON%" packaging\icone.py || exit /b 1

echo == Traductions ==
if exist build_i18n.py "%PYTHON%" build_i18n.py

echo == PyInstaller ==
if exist build rmdir /s /q build
if exist dist.windows rmdir /s /q dist.windows
if exist build.windows rmdir /s /q build.windows
rem Cette construction ecrit chez elle : dist\ ne garde que les archives,
rem et aucune plateforme n'efface le paquet de l'autre.
"%PYTHON%" -m PyInstaller --noconfirm --clean ^
    --distpath dist.windows --workpath build.windows ^
    packaging\zyroom-qt.spec || exit /b 1

rem Le chemin va sans guillemets : `for /f` passe sa commande a `cmd /c`,
rem qui prend le premier et le dernier guillemet de la ligne pour les siens
rem -- la commande partait en morceaux, VERSION restait vide, et l'archive
rem sortait sous le nom ZyRoom-Qt--windows.zip.
set VERSION=
for /f %%v in ('%PYTHON% -c "import zyroom; print(zyroom.__version__)"') do set VERSION=%%v
if "%VERSION%"=="" (
    echo Numero de version introuvable -- construction interrompue.
    exit /b 1
)

echo == Installateur ==
rem Le fichier qui cree les raccourcis, a cote de l'executable.
copy /y data\lanceurs\Installer.bat dist.windows\ZyRoom-Qt\ >nul

echo == Archive ==
rem tar est livre avec Windows 10 et 11 ; -a demande le format ZIP.
if not exist dist mkdir dist
del /q "dist\ZyRoom-Qt-%VERSION%-windows.zip" 2>nul
tar -a -c -f "dist\ZyRoom-Qt-%VERSION%-windows.zip" -C dist.windows ZyRoom-Qt

echo.
echo Dossier : dist.windows\ZyRoom-Qt\ZyRoom-Qt.exe
echo Archive : dist\ZyRoom-Qt-%VERSION%-windows.zip
endlocal
