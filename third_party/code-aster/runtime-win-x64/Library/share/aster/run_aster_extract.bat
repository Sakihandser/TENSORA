echo OFF
setlocal
set PYTHONIOENCODING=UTF-8
chcp 65001
set RUNASTER_ROOT=%~dp0..\..
set PYTHONHOME=%RUNASTER_ROOT%\Python37
set PYTHONPATH=%RUNASTER_ROOT%\lib\python3.7\site-packages;%RUNASTER_ROOT%\lib\aster
set PATH=%PYTHONHOME%;%RUNASTER_ROOT%\tools;%PATH%

call "%RUNASTER_ROOT%\share\aster\profile.bat

python -m run_aster.run_aster_extract_main %*
