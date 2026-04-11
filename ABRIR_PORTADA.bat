@echo off
:: Fuerza a situarse en la carpeta donde esta el .bat
cd /d "%~dp0"

:: Lanza el script usando el nombre exacto con guion bajo
start pythonw "mi_portada.py"

:: Cierra la ventana negra de inmediato
exit