$env:TFELHOME=(Split-Path(Split-Path (Split-Path $PSScriptRoot)))
$env:PATH=$env:TFELHOME+'\bin;'+$env:PATH
$env:PYTHONPATH=$env:TFELHOME+'\C:/Users/hongm/AppData/Local/Temp/tensora-native-aster-1791e4fa018e4d268dfebc7ebca338e7/env\Lib\site-packages;'+$env:PYTHONPATH
