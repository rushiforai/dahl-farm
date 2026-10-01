@echo off
chcp 65001 >nul
title Dahl Farm - Auto Farm (Proxy Required)
cd /d "%~dp0"

REM Jika dipanggil dengan argumen (misal: run.bat 5), langsung jalankan gachafarm
if not "%~1"=="" (
    python dahl_farm.py gachafarm %*
    goto selesai
)

:menu
cls
echo ============================================================
echo      DAHL GLOBAL FARM (PASTI MENGGUNAKAN PROXY)
echo ============================================================
echo.
echo  [1] Farm Akun (Wajib Pakai Proxy - Anti 429 dan Auto 9Router)
echo  [2] Filter / Cari Proxy Aktif Baru (filter_proxies.bat)
echo  [3] Inject Ulang Semua Key Tersimpan ke 9Router
echo  [4] Lihat Daftar Akun yang Sudah Terkumpul
echo  [5] Cek / Verifikasi Token API Key
echo  [0] Keluar
echo.
echo ============================================================
set /p OPT="Pilih menu [1-5, 0]: "

if "%OPT%"=="1" goto opt_farm
if "%OPT%"=="2" goto opt_filter
if "%OPT%"=="3" goto opt_inject
if "%OPT%"=="4" goto opt_list
if "%OPT%"=="5" goto opt_check
if "%OPT%"=="0" exit /b
goto menu

:opt_farm
echo.
set /p JML="Berapa banyak akun yang ingin di-farm? [Default: 1]: "
if "%JML%"=="" set JML=1
echo.
echo [*] Menjalankan farm %JML% akun dengan rotasi proxy...
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
set /p TOK="Masukkan Token Dahl (contoh: dahl_xxxx): "
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
