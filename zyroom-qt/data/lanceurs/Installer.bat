@echo off
rem
rem Pose ZyRoom-Qt dans le menu Demarrer et sur le Bureau.
rem
rem   Installer.bat              cree les raccourcis
rem   Installer.bat /retirer     les enleve
rem
rem Le paquet ne s'installe pas : il se decompresse ou l'on veut, et les
rem raccourcis pointent la ou il se trouve. Deplacer le dossier les casse --
rem relancez ce fichier depuis le nouvel emplacement.
setlocal

rem %~dp0 se termine deja par un antislash, d'ou le nom colle juste apres.
set "ZQ_ICI=%~dp0"
set "ZQ_EXE=%~dp0ZyRoom-Qt.exe"
set "ZQ_NOM=ZyRoom-Qt"

rem La variante du chef de guilde ne se lance pas par l'executable mais par
rem son fichier de commandes, qui pose la variable devoilant les coffres
rem reserves. Viser l'executable donnerait au chef un raccourci vers
rem l'application ordinaire -- sans le coffre pour lequel il a cette version.
if exist "%~dp0ZyRoom-Qt-dev.bat" (
    set "ZQ_CIBLE=%~dp0ZyRoom-Qt-dev.bat"
    set "ZQ_NOM=ZyRoom-Qt (chef)"
) else (
    set "ZQ_CIBLE=%~dp0ZyRoom-Qt.exe"
)

set "ZQ_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%ZQ_NOM%.lnk"
set "ZQ_BUREAU=%USERPROFILE%\Desktop\%ZQ_NOM%.lnk"

if /i "%~1"=="/retirer" (
    del "%ZQ_MENU%" 2>nul
    del "%ZQ_BUREAU%" 2>nul
    echo Raccourcis retires. Le dossier de l'application reste ou il est.
    pause
    exit /b 0
)

if not exist "%ZQ_EXE%" (
    echo Erreur : ZyRoom-Qt.exe introuvable a cote de ce fichier.
    echo Gardez le dossier entier tel qu'il sort de l'archive.
    pause
    exit /b 1
)

rem Un raccourci .lnk est un format binaire : seul WScript.Shell sait
rem l'ecrire, et PowerShell est le seul moyen de l'appeler depuis un .bat.
rem
rem Les chemins voyagent par l'environnement plutot que colles dans la
rem commande : un dossier peut contenir une apostrophe ou un accent, qui
rem couperait la chaine PowerShell en deux. $env: les lit tels quels.
rem L'icone vient de l'executable, qui la porte deja.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$w = New-Object -ComObject WScript.Shell;" ^
  "foreach ($c in @($env:ZQ_MENU, $env:ZQ_BUREAU)) {" ^
  "  $r = $w.CreateShortcut($c);" ^
  "  $r.TargetPath = $env:ZQ_CIBLE;" ^
  "  $r.WorkingDirectory = $env:ZQ_ICI;" ^
  "  $r.IconLocation = $env:ZQ_EXE + ',0';" ^
  "  $r.WindowStyle = 7;" ^
  "  $r.Description = 'Vos inventaires Ryzom et les coffres de la guilde';" ^
  "  $r.Save() }"

rem On regarde le resultat, pas le code de retour : powershell rend zero
rem meme quand il manque a l'appel, et le script annoncait alors une
rem installation qui n'avait pas eu lieu.
if not exist "%ZQ_MENU%" goto :rate
if not exist "%ZQ_BUREAU%" goto :rate

echo %ZQ_NOM% est dans le menu Demarrer et sur le Bureau.
echo Pour les enlever : Installer.bat /retirer
pause
exit /b 0

:rate
echo Les raccourcis n'ont pas pu etre crees.
echo.
echo Windows 10 et 11 fournissent PowerShell, dont ce script se sert ; s'il
echo a ete desactive, creez le raccourci a la main : clic droit sur
echo ZyRoom-Qt.exe, "Envoyer vers", "Bureau (creer un raccourci)".
pause
exit /b 1
