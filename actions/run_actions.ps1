<#
.SYNOPSIS
  Windows 11 kit: the same 30 scripted actions as actions/run_actions.py, written
  to truth.csv in UTC. Run inside a test VM only, on a dedicated volume.

.EXAMPLE
  # in the VM, as an administrator, after setting the zone with tzutil:
  tzutil /s "GMT Standard Time"
  powershell -ExecutionPolicy Bypass -File run_actions.ps1 -Root E:\ -Out C:\truth -Spacing 12
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,     # e.g. E:\ (a separate NTFS/exFAT/FAT32 volume)
  [Parameter(Mandatory = $true)][string]$Out,      # where truth.csv goes (NOT on $Root)
  [double]$Spacing = 12
)
$ErrorActionPreference = 'Stop'
$Root = $Root.TrimEnd('\')

# id, type, path, source  (identical to actions/run_actions.py)
$Actions = @(
  @(1,'mkdir','/docs',''), @(2,'mkdir','/archive',''), @(3,'create','/docs/report.txt',''),
  @(4,'modify','/docs/report.txt',''), @(5,'create','/docs/notes.txt',''),
  @(6,'copy','/docs/notes_copy.txt','/docs/notes.txt'), @(7,'rename','/docs/notes_v2.txt','/docs/notes_copy.txt'),
  @(8,'move','/archive/notes_v2.txt','/docs/notes_v2.txt'), @(9,'modify','/docs/report.txt',''),
  @(10,'create','/docs/budget.csv',''), @(11,'zip','/archive/budget.zip','/docs/budget.csv'),
  @(12,'delete','/docs/budget.csv',''), @(13,'mkdir','/restored',''),
  @(14,'unzip','/restored/budget.csv','/archive/budget.zip'), @(15,'create','/docs/run.cmd',''),
  @(16,'access','/docs/run.cmd',''), @(17,'mkdir','/photos',''), @(18,'create','/photos/img001.jpg',''),
  @(19,'create','/photos/img002.jpg',''), @(20,'rename','/photos/holiday.jpg','/photos/img002.jpg'),
  @(21,'delete','/photos/img001.jpg',''), @(22,'modify','/docs/notes.txt',''),
  @(23,'copy','/archive/report_backup.txt','/docs/report.txt'), @(24,'move','/restored/notes.txt','/docs/notes.txt'),
  @(25,'create','/docs/final.txt',''), @(26,'modify','/docs/final.txt',''),
  @(27,'rename','/docs/final_v2.txt','/docs/final.txt'), @(28,'access','/archive/report_backup.txt',''),
  @(29,'delete','/archive/budget.zip',''), @(30,'create','/done.txt','')
)
function P($rel) { return $Root + ($rel -replace '/', '\') }
Add-Type -AssemblyName System.IO.Compression.FileSystem

New-Item -ItemType Directory -Force -Path $Out | Out-Null
$truth = Join-Path $Out 'truth.csv'
'action_id,utc_time,host_utc_time,type,path,check_path,source' | Set-Content -Encoding ascii $truth
$first = $true
foreach ($a in $Actions) {
  $id, $kind, $path, $src = $a
  if (-not $first) { Start-Sleep -Milliseconds ([int]($Spacing * 1000)) }
  $first = $false
  $t = [DateTime]::UtcNow
  switch ($kind) {
    'mkdir'  { New-Item -ItemType Directory -Path (P $path) | Out-Null }
    'create' { if ($path -like '*.cmd') { Set-Content -Path (P $path) -Value '@echo timetruth' }
               else { Set-Content -Path (P $path) -Value "created $path" } }
    'modify' { Add-Content -Path (P $path) -Value 'modified' }
    'copy'   { [IO.File]::WriteAllBytes((P $path), [IO.File]::ReadAllBytes((P $src))) }  # content only
    'rename' { Rename-Item -Path (P $src) -NewName (Split-Path -Leaf (P $path)) }
    'move'   { Move-Item -Path (P $src) -Destination (P $path) }
    'delete' { Remove-Item -Path (P $path) }
    'zip'    { $z = [IO.Compression.ZipFile]::Open((P $path), 'Create')
               [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z, (P $src), (Split-Path -Leaf (P $src)))
               $z.Dispose() }
    'unzip'  { $z = [IO.Compression.ZipFile]::OpenRead((P $src))
               $e = $z.GetEntry((Split-Path -Leaf (P $path)))
               $s = $e.Open(); $f = [IO.File]::Create((P $path)); $s.CopyTo($f); $f.Dispose(); $s.Dispose(); $z.Dispose() }
    'access' { if ($path -like '*.cmd') { & cmd.exe /c (P $path) | Out-Null }   # "run a program": Prefetch-visible
               else { [void][IO.File]::ReadAllBytes((P $path)) } }
  }
  $check = $path
  if ($kind -eq 'delete') { $check = $path.Substring(0, $path.LastIndexOf('/')); if ($check -eq '') { $check = '/' } }
  $iso = $t.ToString('yyyy-MM-ddTHH:mm:ss.ffffff') + '+00:00'
  "$id,$iso,$iso,$kind,$path,$check,$src" | Add-Content -Encoding ascii $truth
}
Write-Host "wrote $truth"
