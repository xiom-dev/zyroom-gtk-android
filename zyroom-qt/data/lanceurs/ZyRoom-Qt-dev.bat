@echo off
rem ZyRoom-Qt, variante du chef de guilde.
rem
rem Elle montre les coffres que la version ordinaire masque -- le petit coffre
rem de Nizy. C'est la seule difference : meme application, memes reglages,
rem seul le masque tombe.
rem
rem Lancez ce fichier au lieu de ZyRoom-Qt.exe.
setlocal
set ZYROOM_SHOW_ALL_CHESTS=1
start "" "%~dp0ZyRoom-Qt.exe" %*
