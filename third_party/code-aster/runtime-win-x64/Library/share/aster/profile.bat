:: created by waf using data/wscript
@echo off

if defined CONDA_PREFIX (
    set "ASTER_ROOT=%CONDA_PREFIX%"
    set "RUNASTER_ROOT=%CONDA_PREFIX%\Library"

) else (
    echo CONDA_PREFIX is not defined
)

echo ASTER_ROOT is set to %ASTER_ROOT%
REM Choose library directory: prefer subdir 'aster' if it exists, else plain 'lib'
if exist "%ASTER_ROOT%\Library\lib\aster" (
    set "_ASTER_LIB_SUBDIR=%ASTER_ROOT%\Library\lib\aster"
) else (
    set "_ASTER_LIB_SUBDIR=%ASTER_ROOT%\Library\lib"
)
REM Update PYTHONPATH using selected lib directory
REM The trailing "." matches profile.sh.tmpl: testcases import helper modules
REM copied next to the command file in the working directory.
set "PYTHONPATH=%_ASTER_LIB_SUBDIR%;%ASTER_ROOT%\lib\site-packages;%PYTHONPATH%;."

set "ASTER_DATADIR=%ASTER_ROOT%\Library\share\aster"
set "ASTER_LIBDIR=%_ASTER_LIB_SUBDIR%"
set "ASTER_LOCALEDIR=%ASTER_ROOT%\Library\share\locale\aster"
set "ASTER_ELEMENTSDIR=%_ASTER_LIB_SUBDIR%"
