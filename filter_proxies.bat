@echo off
chcp 65001 >nul
title Dahl Farm - Filter Proxy
cd /d "%~dp0"

echo ============================================================
echo        FILTER PROXY UNTUK DAHL FARM
echo ============================================================
echo  Mengecek proxy yang aktif dan bisa akses inference.dahl.global
echo  Hasil proxy bagus langsung disimpan ke: proxies_good.txt
echo ============================================================
echo.

if "%~1"=="" (
    set /p COUNT="Berapa target proxy bagus yang ingin dikumpulkan? [Default: 20]: "
) else (
    set COUNT=%1
)

if "%COUNT%"=="" set COUNT=20

echo.
echo [*] Memulai pencarian %COUNT% proxy aktif...
echo.
python filter_proxies.py %COUNT%
echo.
pause
