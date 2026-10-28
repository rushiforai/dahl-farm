@echo off
chcp 65001 >nul
title Dahl Farm - Auto Farm (Proxy Required)
cd /d "%~dp0"

REM If called with arguments (for example: run.bat 5), run gachafarm immediately
if not "%~1"=="" (
    python dahl_farm.py gachafarm %*
    goto selesai
)

:menu
cls
echo ============================================================
echo      DAHL GLOBAL FARM (ALWAYS USE PROXY)
echo ============================================================
echo.
echo  [1] Farm Accounts (Requires Proxy - Anti 429 and Auto 9Router)
echo  [2] Filter / Find New Active Proxy (filter_proxies.bat)
echo  [3] Re-Inject All Saved Keys into 9Router
echo  [4] View the List of Accounts Already Collected
echo  [5] Check / Verify API Key Token
echo  [0] Exit
echo.
echo ============================================================
set /p OPT="Select menu [1-5, 0]: "

if "%OPT%"=="1" goto opt_farm
if "%OPT%"=="2" goto opt_filter
if "%OPT%"=="3" goto opt_inject
if "%OPT%"=="4" goto opt_list
if "%OPT%"=="5" goto opt_check
if "%OPT%"=="0" exit /b
goto menu

:opt_farm
echo.
set /p JML="How many accounts do you want to farm? [Default: 1]: "
if "%JML%"=="" set JML=1
echo.
echo [*] Running farm for %JML% accounts with proxy rotation...
python dahl_farm.py gachafarm %JML%
echo.
pause
goto menu

:opt_filter
echo.
call filter_proxies.bat
goto menu

:opt_inject
echo.
python dahl_farm.py inject9
echo.
pause
goto menu

:opt_list
echo.
python dahl_farm.py list
echo.
pause
goto menu

:opt_check
echo.
set /p TOK="Enter Dahl Token (example: dahl_xxxx): "
if not "%TOK%"=="" (
    echo.
    python dahl_farm.py check %TOK%
)
echo.
pause
goto menu

:selesai
echo.
pause
