#Requires -Version 5.1
# Forwards hogwarts-input/1 lines from agent stdin to \\.\pipe\<name> via .NET.
# Supported fallback when native kind=pipe fails on a host.
param([string]$PipeName = "hogwarts-input")
$ErrorActionPreference = "Stop"
function Connect-Pipe {
  $c = New-Object System.IO.Pipes.NamedPipeClientStream(".", $PipeName, [IO.Pipes.PipeDirection]::Out)
  $c.Connect(8000)
  return $c
}
$pipe = $null
$writer = $null
function Ensure-Writer {
  if ($script:writer -ne $null -and $script:pipe -ne $null -and $script:pipe.IsConnected) { return }
  if ($script:writer) { try { $script:writer.Dispose() } catch {} }
  if ($script:pipe) { try { $script:pipe.Dispose() } catch {} }
  $script:pipe = Connect-Pipe
  $script:writer = New-Object System.IO.StreamWriter($script:pipe, [Text.Encoding]::UTF8, 4096, $true)
  $script:writer.AutoFlush = $true
  [Console]::Error.WriteLine("[pipe-bridge] connected to \\.\pipe\$PipeName")
}
try {
  Ensure-Writer
  while ($true) {
    $line = [Console]::In.ReadLine()
    if ($null -eq $line) { break }
    try {
      Ensure-Writer
      $script:writer.WriteLine($line)
    } catch {
      [Console]::Error.WriteLine("[pipe-bridge] write failed: $($_.Exception.Message)")
      $script:writer = $null
      $script:pipe = $null
      Start-Sleep -Milliseconds 200
      try {
        Ensure-Writer
        $script:writer.WriteLine($line)
      } catch {
        [Console]::Error.WriteLine("[pipe-bridge] retry failed: $($_.Exception.Message)")
      }
    }
  }
} finally {
  if ($writer) { try { $writer.Dispose() } catch {} }
  if ($pipe) { try { $pipe.Dispose() } catch {} }
}
