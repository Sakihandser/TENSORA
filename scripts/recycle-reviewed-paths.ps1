param([Parameter(Mandatory=$true)][string]$Manifest)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName Microsoft.VisualBasic
$taskManifestPath=[IO.Path]::GetFullPath($Manifest)
$taskPlan=Get-Content -LiteralPath $taskManifestPath -Raw | ConvertFrom-Json
$taskWorkspace=[IO.Path]::GetFullPath($taskPlan.workspace).TrimEnd('\','/')
$taskRepository=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\','/')
$taskProtected=@((Join-Path $taskRepository '.git'),(Join-Path $taskRepository '.tools'),(Join-Path $taskRepository 'output'),(Join-Path $taskRepository 'third_party'),(Split-Path -Parent $taskManifestPath))
# Validate the complete reviewed list before moving any item.
foreach($taskItem in $taskPlan.items){
  $taskTarget=[IO.Path]::GetFullPath($taskItem.path).TrimEnd('\','/')
  if(!$taskTarget.StartsWith($taskWorkspace+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Refusing path outside workspace: $taskTarget"}
  foreach($taskKeep in $taskProtected){if($taskTarget.Equals($taskKeep,[StringComparison]::OrdinalIgnoreCase) -or $taskTarget.StartsWith($taskKeep+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Refusing protected path: $taskTarget"}}
  if($taskTarget.StartsWith($taskRepository+'\',[StringComparison]::OrdinalIgnoreCase)){
    $taskRelative=$taskTarget.Substring($taskRepository.Length+1)
    if($taskRelative -like '论文-*.json'){throw "Refusing current paper model: $taskTarget"}
    $taskTracked=& git -C $taskRepository ls-files -- $taskRelative
    if($LASTEXITCODE -ne 0 -or $taskTracked){throw "Refusing tracked source or tracked files below directory: $taskTarget"}
  }
  if(Test-Path -LiteralPath $taskTarget){$taskEntry=Get-Item -LiteralPath $taskTarget -Force;if($taskEntry.LinkType -in @('SymbolicLink','Junction')){throw "Refusing linked target: $taskTarget"}}
}
foreach($taskItem in $taskPlan.items){
  $taskTarget=[IO.Path]::GetFullPath($taskItem.path)
  $taskStatus='already_absent';$taskFailure=$null
  try{
    if(Test-Path -LiteralPath $taskTarget){
      if((Get-Item -LiteralPath $taskTarget -Force).PSIsContainer){
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($taskTarget,[Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,[Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin,[Microsoft.VisualBasic.FileIO.UICancelOption]::ThrowException)
      }else{
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($taskTarget,[Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,[Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin,[Microsoft.VisualBasic.FileIO.UICancelOption]::ThrowException)
      }
      if(Test-Path -LiteralPath $taskTarget){throw 'Item remains at its original path after recycling.'}
      $taskStatus='recycled'
    }
  }catch{$taskStatus='failed';$taskFailure=$_.Exception.Message}
  $taskItem | Add-Member -NotePropertyName status -NotePropertyValue $taskStatus -Force
  $taskItem | Add-Member -NotePropertyName error -NotePropertyValue $taskFailure -Force
  $taskItem | Add-Member -NotePropertyName processedAt -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
  $taskPlan | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $taskManifestPath -Encoding utf8
  Write-Output "$taskStatus : $taskTarget"
}
$taskFailed=@($taskPlan.items | Where-Object status -eq 'failed')
Write-Output "Recycled $(@($taskPlan.items | Where-Object status -eq 'recycled').Count) items; failed $($taskFailed.Count)."
if($taskFailed.Count){exit 1}
