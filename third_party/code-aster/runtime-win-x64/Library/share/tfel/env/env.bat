@ECHO OFF
for %%i in ("%~dp0.\..\..\..") do set "TFELHOME=%%~fi"
set PATH=%TFELHOME%\bin;%PATH%
set PYTHONPATH=%TFELHOME%\C:/Users/hongm/AppData/Local/Temp/tensora-native-aster-1791e4fa018e4d268dfebc7ebca338e7/env\Lib\site-packages;%PYTHONPATH%
