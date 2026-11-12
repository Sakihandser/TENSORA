@echo off
title Create testing link
mode con: cols=90 lines=30
Color 0F
cls
set aster_lib=%~dp0..\..\lib\aster
for %%A IN (aster,aster_core,aster_fonctions,libaster) do (
    if exist "%aster_lib%\%%A.pyd" (
        del "%aster_lib%\%%A.pyd"
    )
    mklink /h "%aster_lib%\%%A.pyd" "%aster_lib%\aster.dll"
)
if exist "%aster_lib%\libAsterGC.pyd" (
    del "%aster_lib%\libAsterGC.pyd"
)
mklink /h "%aster_lib%\libAsterGC.pyd" "%aster_lib%\aster.dll"

exit
