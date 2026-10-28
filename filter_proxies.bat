@echo off
chcp 65001 >nul
title Dahl Farm - Filter Proxy
cd /d "%~dp0"

echo ============================================================
echo        FILTER PROXY FOR DAHL FARM
echo ============================================================
echo  Checking live proxies that can reach inference.dahl.global
echo  Good proxies are saved directly to: proxies_good.txt
echo ============================================================
echo.

if "%~1"=="" (
    set /p COUNT="How many good proxies do you want to collect? [Default: 20]: "
) else (
    set COUNT=%1
)

if "%COUNT%"=="" set COUNT=20

echo.
echo [*] Starting search for %COUNT% active proxies...
echo.
python filter_proxies.py %COUNT%
echo.
pause
