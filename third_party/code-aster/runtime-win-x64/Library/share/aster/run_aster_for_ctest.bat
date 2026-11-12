echo OFF
rem setlocal
rem set PYTHONIOENCODING=UTF-8
rem chcp 65001

rem Wrapper of run_aster internally used within run_ctest

set export=%1

for /F %%i in ("%export%") do set base=%%~ni

set RUNASTER_ROOT=%~dp0..\..

if not defined MESS_EXT (
    set MESS_EXT=mess
)

cmd /c %RUNASTER_ROOT%\bin\run_aster.bat --ctest %export% > %base%.%MESS_EXT% 2>&1
set iret=%ERRORLEVEL%

if %iret%==0 (
  if "%ASTER_ONLY_FAILED_RESULTS%"=="1" (
    if exist %base%.%MESS_EXT% del %base%.%MESS_EXT%
    if exist %base%.code del %base%.code
  )
)

exit %iret%
