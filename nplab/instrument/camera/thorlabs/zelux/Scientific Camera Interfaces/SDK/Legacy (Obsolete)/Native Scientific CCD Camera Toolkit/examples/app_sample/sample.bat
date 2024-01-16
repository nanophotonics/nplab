@echo off
echo ========================================================================
del tsi_sample.txt
del tsi_sample_small.txt

set CAMERA_NUMBER=0

if "%1"=="" goto DEFAULT
if "%1"=="help" goto HELP
if "%1"=="help" goto HELP
if "%1"=="?" goto HELP
if "%1"=="reset" goto RESET
if "%1"=="RESET" goto RESET
if "%1"=="center" goto CENTER
if "%1"=="CENTER" goto CENTER
if "%1"=="top" goto TOP
if "%1"=="TOP" goto TOP
if "%1"=="s20" goto SPEED_20
if "%1"=="S20" goto SPEED_20
if "%1"=="s40" goto SPEED_40
if "%1"=="S40" goto SPEED_40
if "%1"=="-script" goto DO_SCRIPT
if "%1"=="-SCRIPT" goto DO_SCRIPT
if "%1"=="dbg" goto DO_DBG
if "%1"=="DBG" goto DO_DBG
if "%2"=="" goto DEFAULT
goto SUBREGION

:HELP
echo disp                             - Uses default (full frame, etc.) settings
echo disp reset                       - Resets camera cache, then uses default (full frame, etc.) settings
echo disp center                      - Uses subregion settings that should return the center 128 lines of the CCD
echo disp top                         - Uses subregion settings that should return the top 128 lines of the CCD
echo disp s20                         - Sets digitization rate to 20Mhz, then uses default (full frame, etc.) settings
echo disp s40                         - Sets digitization rate to 40Mhz, then uses default (full frame, etc.) settings
echo disp {XBIN} {YBIN}               - then uses default (full frame, etc.) settings
goto EXIT

:RESET
if "%2"=="ALL" goto RESETALL
if "%2"=="all" goto RESETALL
del C:\Users\ghavenga\AppData\Roaming\TSI\API\TSI1500*.dat
del C:\Users\ghavenga\AppData\Roaming\TSI\API\TL1500*.dat
goto DEFAULT

:RESETALL
del C:\Users\ghavenga\AppData\Roaming\TSI\API\*.dat
goto DEFAULT

:DEFAULT
@echo tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040 
tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040
goto EXIT

:SUBREGION
:BIN
@echo tsi_sample %CAMERA_NUMBER% 50 10000 %1 %2 0 0 1392 1040
tsi_sample %CAMERA_NUMBER% 50 10000 %1 %2 0 0 1392 1040
goto EXIT

:CENTER
@echo tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 496 1392 128 
tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 496 1392 128
goto EXIT

:TOP
@echo tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 128
tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 128
goto EXIT

:SPEED_20
@echo tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040 0
tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040 0
goto EXIT

:SPEED_40
@echo tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040 1
tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040 1
goto EXIT

:DO_SCRIPT
@echo tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040 -script %2
tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040 -script %2
goto EXIT

:DO_DBG
@echo tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1040
 "C:\Program Files\Debugging Tools for Windows (x86)\windbg.exe" tsi_sample %CAMERA_NUMBER% 50 10000 1 1 0 0 1392 1039
goto EXIT

:EXIT
echo ========================================================================
echo -
@echo dir /b /s %APPDATA%"\TSI\API\*.dat"
echo -
dir /b /s %APPDATA%"\TSI\API\*.dat"
echo ========================================================================
